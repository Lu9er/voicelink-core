#!/usr/bin/env python3
"""
Module 4D — Common Voice Submission Worker

Reads approved clips with transcripts from Supabase, authenticates with the
Common Voice API, uploads audio, and records each attempt in cv_submissions.

The CV API is currently unstable (/text/sentences returns 400).  This worker
is built as a configurable skeleton — every endpoint and parameter is
env-driven so it can adapt once the API stabilises.

Usage:
    python -m publisher.cv_submit --limit 10
    python -m publisher.cv_submit --limit 5 --dry-run
    DRY_RUN=true python -m publisher.cv_submit

Environment:
    CV_API_BASE_URL        e.g. https://commonvoice.mozilla.org/api/v1
    CV_AUTH_EMAIL           login email
    CV_AUTH_PASSWORD        login password
    CV_LANGUAGE             target language code (default: ate)
    CV_RESOURCE_TYPE        scripted | spontaneous (default: spontaneous)
    CV_AUTH_ENDPOINT        override auth path   (default: /auth/token)
    CV_UPLOAD_ENDPOINT      override upload path  (default: /clips)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
import time

import httpx
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("voicelink.publisher")

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CV_API_BASE_URL = os.environ.get("CV_API_BASE_URL", "")
CV_AUTH_EMAIL = os.environ.get("CV_AUTH_EMAIL", "")
CV_AUTH_PASSWORD = os.environ.get("CV_AUTH_PASSWORD", "")
CV_LANGUAGE = os.environ.get("CV_LANGUAGE", "ate")
CV_RESOURCE_TYPE = os.environ.get("CV_RESOURCE_TYPE", "spontaneous")
CV_AUTH_ENDPOINT = os.environ.get("CV_AUTH_ENDPOINT", "/auth/token")
CV_UPLOAD_ENDPOINT = os.environ.get("CV_UPLOAD_ENDPOINT", "/clips")


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------


def _make_clients():
    if DRY_RUN:
        return None, None
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    bucket_name = os.environ.get("GCS_BUCKET_NAME", "")
    missing = []
    if not url:
        missing.append("SUPABASE_URL")
    if not key:
        missing.append("SUPABASE_SERVICE_KEY")
    if not bucket_name:
        missing.append("GCS_BUCKET_NAME")
    if missing:
        print(f"ERROR: Missing: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    from google.cloud import storage
    from supabase import create_client

    sb = create_client(url, key)
    bucket = storage.Client().bucket(bucket_name)
    return sb, bucket


# ---------------------------------------------------------------------------
# CV API helpers
# ---------------------------------------------------------------------------


def authenticate(base_url: str, email: str, password: str) -> str:
    """POST to the auth endpoint and return a bearer token."""
    resp = httpx.post(
        f"{base_url}{CV_AUTH_ENDPOINT}",
        json={"email": email, "password": password},
        timeout=30,
    )
    resp.raise_for_status()
    token = resp.json().get("token", "")
    if not token:
        raise RuntimeError("Auth response missing 'token' field")
    log.info("CV auth: loaded creds (token obtained)")
    return token


def upload_clip(
    base_url: str,
    token: str,
    audio_path: str,
    transcript: str,
    language: str,
    resource_type: str,
) -> dict:
    """Upload audio + transcript to the CV API.

    Returns {http_status, success, error_message}.
    """
    headers = {"Authorization": f"Bearer {token}"}
    with open(audio_path, "rb") as f:
        resp = httpx.post(
            f"{base_url}{CV_UPLOAD_ENDPOINT}",
            headers=headers,
            files={"audio": (os.path.basename(audio_path), f, "audio/mpeg")},
            data={
                "sentence": transcript,
                "language": language,
                "resource_type": resource_type,
            },
            timeout=60,
        )

    return {
        "http_status": resp.status_code,
        "success": resp.is_success,
        "error_message": "" if resp.is_success else resp.text[:500],
    }


# ---------------------------------------------------------------------------
# Submission pipeline
# ---------------------------------------------------------------------------


def select_submittable_clips(sb, limit: int = 10) -> list[dict]:
    """Approved clips with transcript, not yet successfully submitted."""
    # Get IDs of already-submitted clips
    submitted = (
        sb.table("cv_submissions")
        .select("clip_id")
        .eq("success", True)
        .execute()
    )
    submitted_ids = {r["clip_id"] for r in submitted.data}

    clips = (
        sb.table("clips")
        .select("id, recording_id, gcs_clip_url, duration_seconds, transcript")
        .eq("status", "approved")
        .neq("transcript", "")
        .not_.is_("transcript", "null")
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    ).data

    return [c for c in clips if c["id"] not in submitted_ids]


def record_attempt(sb, clip_id: str, resource_type: str, result: dict) -> None:
    """Insert a row into cv_submissions."""
    sb.table("cv_submissions").insert({
        "clip_id": clip_id,
        "cv_resource_type": resource_type,
        "http_status": result.get("http_status"),
        "success": result.get("success", False),
        "error_message": result.get("error_message", "")[:500],
    }).execute()


def run(limit: int = 10) -> dict:
    sb, bucket = _make_clients()
    counts = {"ok": 0, "fail": 0, "skip": 0}

    if DRY_RUN:
        log.info(f"DRY_RUN: would select up to {limit} approved clips with transcript")
        log.info(f"DRY_RUN: would auth to {CV_API_BASE_URL}{CV_AUTH_ENDPOINT}")
        log.info(f"DRY_RUN: would upload to {CV_API_BASE_URL}{CV_UPLOAD_ENDPOINT}")
        log.info(f"DRY_RUN: language={CV_LANGUAGE} resource_type={CV_RESOURCE_TYPE}")
        return counts

    if not CV_API_BASE_URL:
        log.error("CV_API_BASE_URL not set — cannot submit")
        sys.exit(1)

    clips = select_submittable_clips(sb, limit)
    log.info(f"Selected {len(clips)} clip(s) for submission")

    if not clips:
        return counts

    # Authenticate once per batch
    try:
        token = authenticate(CV_API_BASE_URL, CV_AUTH_EMAIL, CV_AUTH_PASSWORD)
    except Exception as e:
        log.error(f"CV auth failed: {e}")
        sys.exit(1)

    for clip in clips:
        clip_id = clip["id"]
        gcs_url = clip["gcs_clip_url"]
        transcript = clip["transcript"]

        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp:
                # Download from GCS with retry
                for attempt in range(3):
                    try:
                        bucket.blob(gcs_url).download_to_filename(tmp.name)
                        break
                    except Exception as e:
                        if attempt < 2:
                            time.sleep(2 ** (attempt + 1))
                        else:
                            raise

                result = upload_clip(
                    CV_API_BASE_URL,
                    token,
                    tmp.name,
                    transcript,
                    CV_LANGUAGE,
                    CV_RESOURCE_TYPE,
                )

            record_attempt(sb, clip_id, CV_RESOURCE_TYPE, result)

            if result["success"]:
                log.info(f"[OK] {clip_id} submitted")
                counts["ok"] += 1
            else:
                log.warning(
                    f"[FAIL] {clip_id} http={result['http_status']}"
                )
                counts["fail"] += 1

        except Exception as e:
            log.error(f"[FAIL] {clip_id} {e}")
            try:
                record_attempt(sb, clip_id, CV_RESOURCE_TYPE, {
                    "http_status": 0,
                    "success": False,
                    "error_message": str(e)[:500],
                })
            except Exception:
                pass
            counts["fail"] += 1

    log.info(f"Done: {counts}")
    return counts


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="VoiceLink Common Voice submission worker",
    )
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
        global DRY_RUN
        DRY_RUN = True

    counts = run(limit=args.limit)
    sys.exit(1 if counts["fail"] > 0 and counts["ok"] == 0 else 0)


if __name__ == "__main__":
    main()
