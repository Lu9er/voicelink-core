#!/usr/bin/env python3
"""
Module 4B — Clip Transcription

Select clips from Supabase, run ASR, and write transcripts back.

Default: transcribe clips where status='approved' AND transcript IS NULL.
Use --include-pending to also transcribe pending_review clips.

Backends (set via TRANSCRIBE_BACKEND env or --backend flag):
    faster_whisper  — local faster-whisper (default, CPU, no API key)
    openai_whisper  — OpenAI Whisper API (requires OPENAI_API_KEY)

Usage:
    python -m transcribe.transcribe_clips
    python -m transcribe.transcribe_clips --include-pending --limit 50
    python -m transcribe.transcribe_clips --backend openai_whisper --force
    DRY_RUN=true python -m transcribe.transcribe_clips --limit 10
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tempfile
import time

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("voicelink.transcribe")

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")

# ---------------------------------------------------------------------------
# Supabase / GCS helpers
# ---------------------------------------------------------------------------


def _make_clients():
    """Return (supabase_client, gcs_bucket) or (None, None) in dry-run."""
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
        print(f"ERROR: Missing env var(s): {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)

    from google.cloud import storage
    from supabase import create_client

    sb = create_client(url, key)
    bucket = storage.Client().bucket(bucket_name)
    return sb, bucket


def _download_clip(bucket, gcs_clip_url: str, dest: str) -> None:
    """Download a clip from GCS with retry."""
    for attempt in range(3):
        try:
            bucket.blob(gcs_clip_url).download_to_filename(dest)
            return
        except Exception as e:
            if attempt < 2:
                wait = 2 ** (attempt + 1)
                log.warning(f"Download retry {attempt + 1}: {e} (wait {wait}s)")
                time.sleep(wait)
            else:
                raise


# ---------------------------------------------------------------------------
# ASR backends
# ---------------------------------------------------------------------------

_fw_model = None


def _transcribe_faster_whisper(audio_path: str, model_size: str = "base") -> str:
    global _fw_model
    if _fw_model is None:
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            log.error(
                "faster-whisper not installed. "
                "Run: pip install faster-whisper"
            )
            sys.exit(1)
        log.info(f"Loading faster-whisper model ({model_size}) …")
        _fw_model = WhisperModel(model_size, device="cpu", compute_type="int8")
    segments, _info = _fw_model.transcribe(audio_path)
    return " ".join(seg.text.strip() for seg in segments).strip()


def _transcribe_openai(audio_path: str) -> str:
    try:
        from openai import OpenAI
    except ImportError:
        log.error("openai not installed. Run: pip install openai")
        sys.exit(1)
    client = OpenAI()  # uses OPENAI_API_KEY
    with open(audio_path, "rb") as f:
        resp = client.audio.transcriptions.create(model="whisper-1", file=f)
    return resp.text.strip()


BACKENDS = {
    "faster_whisper": _transcribe_faster_whisper,
    "openai_whisper": _transcribe_openai,
}


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def select_clips(
    sb,
    include_pending: bool = False,
    force: bool = False,
    limit: int | None = None,
    since: str | None = None,
) -> list[dict]:
    """Query clips eligible for transcription."""
    statuses = ["approved"]
    if include_pending:
        statuses.append("pending_review")

    q = sb.table("clips").select("id, recording_id, gcs_clip_url, duration_seconds, transcript, status")

    if len(statuses) == 1:
        q = q.eq("status", statuses[0])
    else:
        q = q.in_("status", statuses)

    if not force:
        q = q.is_("transcript", "null")

    if since:
        q = q.gte("created_at", since)

    q = q.order("created_at", desc=False)

    if limit:
        q = q.limit(limit)

    return q.execute().data


def transcribe_one(
    clip: dict,
    bucket,
    sb,
    backend_fn,
) -> str:
    """Download, transcribe, and write back. Returns 'ok'|'skip'|'fail'."""
    clip_id = clip["id"]
    gcs_url = clip["gcs_clip_url"]

    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=True) as tmp:
        _download_clip(bucket, gcs_url, tmp.name)
        transcript = backend_fn(tmp.name)

    if not transcript:
        return "fail"

    sb.table("clips").update({"transcript": transcript}).eq("id", clip_id).execute()
    return "ok"


def run(
    backend: str = "faster_whisper",
    include_pending: bool = False,
    force: bool = False,
    limit: int | None = None,
    since: str | None = None,
    model_size: str = "base",
) -> dict:
    """Run transcription pipeline. Returns summary dict."""
    sb, bucket = _make_clients()
    backend_fn = BACKENDS.get(backend)
    if backend_fn is None:
        log.error(f"Unknown backend: {backend}. Choose from: {list(BACKENDS)}")
        sys.exit(1)

    # For faster_whisper, bind the model_size
    if backend == "faster_whisper":
        _orig = backend_fn
        backend_fn = lambda path: _orig(path, model_size=model_size)

    if DRY_RUN:
        log.info(f"DRY_RUN: would select clips (include_pending={include_pending}, force={force}, limit={limit})")
        log.info(f"DRY_RUN: backend={backend}, model_size={model_size}")
        return {"ok": 0, "skip": 0, "fail": 0}

    clips = select_clips(sb, include_pending, force, limit, since)
    log.info(f"Selected {len(clips)} clip(s) for transcription")

    counts = {"ok": 0, "skip": 0, "fail": 0}

    for clip in clips:
        clip_id = clip["id"]
        dur = clip.get("duration_seconds") or 0

        if not force and clip.get("transcript"):
            log.info(f"[SKIP] {clip_id} already has transcript")
            counts["skip"] += 1
            continue

        try:
            result = transcribe_one(clip, bucket, sb, backend_fn)
            counts[result] += 1
            if result == "ok":
                log.info(f"[OK] {clip_id} {dur:.1f}s backend={backend}")
            else:
                log.warning(f"[FAIL] {clip_id} empty transcript")
        except Exception as e:
            log.error(f"[FAIL] {clip_id} {e}")
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
        description="VoiceLink clip transcription",
    )
    parser.add_argument(
        "--backend",
        default=os.environ.get("TRANSCRIBE_BACKEND", "faster_whisper"),
        choices=list(BACKENDS),
        help="ASR backend (default: faster_whisper)",
    )
    parser.add_argument(
        "--model-size",
        default=os.environ.get("WHISPER_MODEL_SIZE", "base"),
        help="Whisper model size for faster_whisper (default: base)",
    )
    parser.add_argument(
        "--include-pending",
        action="store_true",
        help="Also transcribe pending_review clips",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing transcripts",
    )
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--since", default=None, help="Only clips created after this ISO timestamp",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
        global DRY_RUN
        DRY_RUN = True

    counts = run(
        backend=args.backend,
        include_pending=args.include_pending,
        force=args.force,
        limit=args.limit,
        since=args.since,
        model_size=args.model_size,
    )
    sys.exit(1 if counts["fail"] > 0 and counts["ok"] == 0 else 0)


if __name__ == "__main__":
    main()
