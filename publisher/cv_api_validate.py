#!/usr/bin/env python3
"""
VoiceLink — Common Voice Public API v0.2.0 Access Validator

Validates that CV API credentials work by:
  1. POST /auth/token → acquire JWT (never prints token)
  2. GET dataset codes (tries both known paths) → print count
  3. GET /text/sentences → tries multiple dataset codes until one succeeds

Does NOT attempt POST /audio (spontaneous radio clips are out of scope).
Does NOT write to any database.
Does NOT print secrets or response bodies that may contain them.
"""

import logging
import os
import sys

import requests
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cv_validate")

CV_BASE = "https://api.commonvoice.mozilla.org"


def load_env():
    load_dotenv()
    client_id = os.getenv("CV_CLIENT_ID")
    client_secret = os.getenv("CV_CLIENT_SECRET")
    missing = []
    if not client_id:
        missing.append("CV_CLIENT_ID")
    if not client_secret:
        missing.append("CV_CLIENT_SECRET")
    if missing:
        log.error("Missing env vars: %s", ", ".join(missing))
        sys.exit(1)
    return client_id, client_secret


def _error_detail(resp):
    """Extract short error message from API error response. Never returns body."""
    try:
        j = resp.json()
        return j.get("detail") or j.get("message") or j.get("title") or "(no detail)"
    except Exception:
        return "(non-JSON error)"


# ---------------------------------------------------------------------------
# Step 1: Acquire token
# ---------------------------------------------------------------------------

def acquire_token(client_id, client_secret):
    url = f"{CV_BASE}/auth/token"
    log.info("Step 1: POST %s", url)
    resp = requests.post(
        url,
        json={"clientId": client_id, "clientSecret": client_secret},
        timeout=30,
    )
    if resp.status_code not in (200, 201):
        print(f"Token request failed ({resp.status_code})")
        sys.exit(1)
    data = resp.json()
    token = data.get("token")
    if not token:
        print("Token response missing 'token' field.")
        sys.exit(1)
    print("[PASS] token acquired")
    return token


# ---------------------------------------------------------------------------
# Step 2: List dataset codes — try both known paths
# ---------------------------------------------------------------------------

def get_dataset_codes(headers):
    paths = [
        "/audio/datasets/codes",
        "/datasets/codes",
    ]
    params = {"service": "audio", "resource": "scripted"}

    for path in paths:
        url = CV_BASE + path
        log.info("Step 2: trying GET %s?service=audio&resource=scripted", url)
        resp = requests.get(url, params=params, headers=headers, timeout=30)
        if resp.status_code in (200, 201):
            data = resp.json()
            codes = data if isinstance(data, list) else data.get("data", [])
            log.info("Step 2: succeeded via %s", path)
            print(f"[PASS] dataset codes returned: {len(codes)} (via {path})")
            return codes
        log.info("Step 2: %s returned %d, trying next...", path, resp.status_code)

    print(f"Dataset codes failed on all paths.")
    sys.exit(1)


def pick_candidate_codes(codes):
    """Extract code strings. Return preferred-first ordering for sentence probing."""
    all_codes = []
    for entry in codes:
        c = entry.get("code") if isinstance(entry, dict) else str(entry)
        if c:
            all_codes.append(c)

    code_set = set(all_codes)
    # Preferred first: cy (doc example), en (largest), then first 5 from the list
    preferred = [c for c in ("cy", "en") if c in code_set]
    others = [c for c in all_codes if c not in preferred][:5]
    return preferred + others


# ---------------------------------------------------------------------------
# Step 3: Fetch sentences — probe multiple codes until one works
# ---------------------------------------------------------------------------

def try_sentences(headers, candidates):
    log.info("Step 3: probing /text/sentences with %d candidate codes", len(candidates))

    for code in candidates:
        url = f"{CV_BASE}/text/sentences"
        params = {"datasetCode": code, "limit": 1}
        log.info("  trying datasetCode=%s", code)
        resp = requests.get(url, params=params, headers=headers, timeout=30)

        if resp.status_code in (200, 201):
            data = resp.json()
            items = data.get("data", data) if isinstance(data, dict) else data
            count = len(items) if isinstance(items, list) else "?"
            print(f"[PASS] sentence fetch OK (datasetCode={code}, {count} returned)")
            return True

        detail = _error_detail(resp)
        log.info("  datasetCode=%s → HTTP %d: %s", code, resp.status_code, detail)

    print(f"[WARN] sentence fetch failed for all {len(candidates)} codes tried")
    # Print the last error for debugging
    print(f"       last error: HTTP {resp.status_code}: {detail}")
    return False


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 60)
    print("Common Voice Public API v0.2.0 — Access Validator")
    print("=" * 60)

    client_id, client_secret = load_env()
    log.info("Credentials loaded (not printing values).")

    # Step 1: Token
    token = acquire_token(client_id, client_secret)
    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Dataset codes
    codes = get_dataset_codes(headers)

    # Step 3: Sentences — probe until one works
    candidates = pick_candidate_codes(codes)
    if candidates:
        try_sentences(headers, candidates)
    else:
        log.info("No dataset codes to probe; skipping sentence fetch.")

    print("\n" + "=" * 60)
    print("VALIDATION COMPLETE")
    print("=" * 60)
    print("  POST /audio is NOT attempted this sprint.")
    print("  Radio call-in clips are spontaneous, not scripted readings.")
    print("  Coordinate with Mozilla on resource type before uploading.")
    print("=" * 60)


if __name__ == "__main__":
    main()
