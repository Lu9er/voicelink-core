#!/usr/bin/env python3
"""
Reconciliation Script — Classify and reconcile Supabase recordings against GCS blobs.

Answers:
    1. Which DB rows have real blobs behind them? (valid)
    2. Which DB rows point to missing blobs? (phantom)
    3. Which GCS blobs have no DB row? (orphan)
    4. Which clips rows have real blobs? (valid_clips / phantom_clips)

Outputs:
    reports/reconciliation_summary.json   — counts and breakdown
    reports/valid_recordings.csv          — DB rows with confirmed blobs
    reports/phantom_recordings.csv        — DB rows with missing blobs
    reports/orphan_blobs.csv              — GCS blobs with no DB row
    reports/clips_audit.csv               — clips with blob existence check

Usage:
    python reconcile.py                   # report only (dry run)
    python reconcile.py --mark-phantoms   # also update phantom rows to 'missing_blob'
"""

import argparse
import csv
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("reconcile")

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
gcs_client = storage.Client()
bucket = gcs_client.bucket(os.environ["GCS_BUCKET_NAME"])

REPORTS_DIR = Path("reports")


# ---------------------------------------------------------------------------
# Data fetchers
# ---------------------------------------------------------------------------
def fetch_all_recordings() -> list[dict]:
    """Paginate through all recordings rows."""
    rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            sb.table("recordings")
            .select(
                "id, external_call_id, source_type, status, gcs_path, "
                "duration_seconds, created_at, clip_count, speech_seconds, "
                "speech_yield, failure_reason"
            )
            .range(offset, offset + page_size - 1)
            .execute()
        )
        if not resp.data:
            break
        rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return rows


def fetch_all_clips() -> list[dict]:
    """Paginate through all clips rows."""
    rows = []
    page_size = 1000
    offset = 0
    while True:
        resp = (
            sb.table("clips")
            .select(
                "id, recording_id, gcs_clip_url, duration_seconds, "
                "status, transcript, created_at"
            )
            .range(offset, offset + page_size - 1)
            .execute()
        )
        if not resp.data:
            break
        rows.extend(resp.data)
        if len(resp.data) < page_size:
            break
        offset += page_size
    return rows


def list_gcs_blobs(prefix: str) -> set[str]:
    """List all blob names under a prefix."""
    return {b.name for b in bucket.list_blobs(prefix=prefix)}


# ---------------------------------------------------------------------------
# Corpus classification
# ---------------------------------------------------------------------------
def classify_batch(created_at: str) -> str:
    """Classify a recording into a corpus batch by created_at timestamp.

    Feb 2026 = Ateso/early batch
    Apr 2026 = Luganda CBS batch
    """
    if not created_at:
        return "unknown"
    month = created_at[:7]  # YYYY-MM
    if month <= "2026-02":
        return "ateso_early"
    elif month >= "2026-04":
        return "luganda_cbs"
    else:
        return "other"


# ---------------------------------------------------------------------------
# Main reconciliation
# ---------------------------------------------------------------------------
def reconcile(mark_phantoms: bool = False, clean_phantom_clips: bool = False) -> dict:
    REPORTS_DIR.mkdir(exist_ok=True)

    # ---- Step 1: Fetch everything -------------------------------------------
    log.info("Fetching all recordings from Supabase...")
    recordings = fetch_all_recordings()
    log.info(f"  {len(recordings):,} recording rows")

    log.info("Fetching all clips from Supabase...")
    clips = fetch_all_clips()
    log.info(f"  {len(clips):,} clip rows")

    log.info("Listing GCS blobs in raw_archives/...")
    raw_blobs = list_gcs_blobs("raw_archives/")
    log.info(f"  {len(raw_blobs):,} blobs in raw_archives/")

    log.info("Listing GCS blobs in clips/...")
    clip_blobs = list_gcs_blobs("clips/")
    log.info(f"  {len(clip_blobs):,} blobs in clips/")

    # ---- Step 2: Classify recordings ----------------------------------------
    db_paths = {}  # gcs_path -> recording row
    valid = []
    phantom = []

    for rec in recordings:
        gcs_path = rec.get("gcs_path") or ""
        rec["batch"] = classify_batch(rec.get("created_at", ""))
        db_paths[gcs_path] = rec

        if gcs_path in raw_blobs:
            rec["blob_exists"] = True
            valid.append(rec)
        else:
            rec["blob_exists"] = False
            phantom.append(rec)

    # Orphan blobs: in GCS but not in any DB row's gcs_path
    all_db_paths = set(db_paths.keys())
    orphan_blob_names = raw_blobs - all_db_paths

    # ---- Step 3: Classify clips ---------------------------------------------
    valid_clips = []
    phantom_clips = []
    for clip in clips:
        clip_path = clip.get("gcs_clip_url") or ""
        if clip_path in clip_blobs:
            clip["blob_exists"] = True
            valid_clips.append(clip)
        else:
            clip["blob_exists"] = False
            phantom_clips.append(clip)

    # ---- Step 4: Build summary ----------------------------------------------
    from collections import Counter

    batch_counts = Counter(r["batch"] for r in recordings)
    valid_batch = Counter(r["batch"] for r in valid)
    phantom_batch = Counter(r["batch"] for r in phantom)

    summary = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "recordings": {
            "total_db_rows": len(recordings),
            "valid": len(valid),
            "phantom": len(phantom),
            "orphan_blobs": len(orphan_blob_names),
            "by_batch": {
                batch: {
                    "total": batch_counts.get(batch, 0),
                    "valid": valid_batch.get(batch, 0),
                    "phantom": phantom_batch.get(batch, 0),
                }
                for batch in sorted(batch_counts.keys())
            },
            "by_status": dict(Counter(r["status"] for r in recordings)),
        },
        "clips": {
            "total_db_rows": len(clips),
            "valid": len(valid_clips),
            "phantom": len(phantom_clips),
            "total_clip_blobs": len(clip_blobs),
        },
        "gcs": {
            "raw_archive_blobs": len(raw_blobs),
            "clip_blobs": len(clip_blobs),
        },
        "phantoms_marked": False,
    }

    # ---- Step 5: Write reports -----------------------------------------------
    # Summary JSON
    summary_path = REPORTS_DIR / "reconciliation_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    log.info(f"Written: {summary_path}")

    # Valid recordings CSV
    _write_csv(
        REPORTS_DIR / "valid_recordings.csv",
        valid,
        ["id", "external_call_id", "batch", "status", "gcs_path",
         "duration_seconds", "created_at"],
    )

    # Phantom recordings CSV
    _write_csv(
        REPORTS_DIR / "phantom_recordings.csv",
        phantom,
        ["id", "external_call_id", "batch", "status", "gcs_path",
         "duration_seconds", "created_at"],
    )

    # Orphan blobs CSV
    orphan_rows = [{"gcs_path": name} for name in sorted(orphan_blob_names)]
    _write_csv(REPORTS_DIR / "orphan_blobs.csv", orphan_rows, ["gcs_path"])

    # Clips audit CSV
    all_clips_audit = valid_clips + phantom_clips
    _write_csv(
        REPORTS_DIR / "clips_audit.csv",
        all_clips_audit,
        ["id", "recording_id", "gcs_clip_url", "duration_seconds",
         "status", "blob_exists", "created_at"],
    )

    # ---- Step 6: Optionally mark phantom rows --------------------------------
    if mark_phantoms and phantom:
        # Enum only allows: raw_uploaded, download_queued, downloading,
        # processing, processed, failed. Use 'failed' with a distinct reason.
        PHANTOM_STATUS = "failed"
        PHANTOM_REASON = "phantom: ateso batch, no GCS blob exists"
        log.info(
            f"Marking {len(phantom):,} phantom rows as "
            f"'{PHANTOM_STATUS}' (reason: {PHANTOM_REASON})..."
        )
        marked = 0
        errors = 0
        for rec in phantom:
            try:
                sb.table("recordings").update(
                    {"status": PHANTOM_STATUS, "failure_reason": PHANTOM_REASON}
                ).eq("id", rec["id"]).eq("status", "raw_uploaded").execute()
                marked += 1
                if marked % 500 == 0:
                    log.info(f"  ...{marked:,} marked")
            except Exception as e:
                errors += 1
                if errors <= 3:
                    log.warning(f"  Error marking {rec['id']}: {e}")
        log.info(f"  Marked {marked:,} rows as '{PHANTOM_STATUS}' ({errors} errors)")
        summary["phantoms_marked"] = True
        summary["phantom_status_used"] = PHANTOM_STATUS
        # Rewrite summary with updated flag
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)

    # ---- Step 6b: Optionally delete phantom clip rows -------------------------
    if clean_phantom_clips and phantom_clips:
        log.info(f"Deleting {len(phantom_clips):,} phantom clip rows...")
        deleted = 0
        for clip in phantom_clips:
            try:
                sb.table("clips").delete().eq("id", clip["id"]).execute()
                deleted += 1
            except Exception as e:
                log.warning(f"  Error deleting clip {clip['id']}: {e}")
        log.info(f"  Deleted {deleted:,} phantom clip rows")
        summary["clips"]["phantom_clips_deleted"] = deleted

    # ---- Step 7: Print summary to console ------------------------------------
    print()
    print("=" * 60)
    print("  RECONCILIATION SUMMARY")
    print("=" * 60)
    print()
    print("  RECORDINGS")
    print(f"    DB rows:         {len(recordings):>7,}")
    print(f"    GCS blobs:       {len(raw_blobs):>7,}")
    print(f"    Valid (match):   {len(valid):>7,}")
    print(f"    Phantom (no blob): {len(phantom):>7,}")
    print(f"    Orphan blobs:    {len(orphan_blob_names):>7,}")
    print()
    print("  BY BATCH")
    for batch in sorted(batch_counts.keys()):
        v = valid_batch.get(batch, 0)
        p = phantom_batch.get(batch, 0)
        t = batch_counts[batch]
        print(f"    {batch:20s}  total={t:>6,}  valid={v:>6,}  phantom={p:>6,}")
    print()
    print("  CLIPS")
    print(f"    DB rows:         {len(clips):>7,}")
    print(f"    GCS blobs:       {len(clip_blobs):>7,}")
    print(f"    Valid (match):   {len(valid_clips):>7,}")
    print(f"    Phantom (no blob): {len(phantom_clips):>7,}")
    print()
    if mark_phantoms:
        print(f"  Phantom rows marked as 'missing_blob': YES")
    else:
        print(f"  Phantom rows NOT marked (use --mark-phantoms to update)")
    print()
    print(f"  Reports written to: {REPORTS_DIR.resolve()}")
    print("=" * 60)

    return summary


def _write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    log.info(f"Written: {path} ({len(rows):,} rows)")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="VoiceLink Reconciliation — classify and audit recordings vs GCS",
    )
    parser.add_argument(
        "--mark-phantoms",
        action="store_true",
        help="Update phantom recording rows to status='archived' with reason tag",
    )
    parser.add_argument(
        "--clean-phantom-clips",
        action="store_true",
        help="Delete clip rows whose GCS blobs are missing",
    )
    args = parser.parse_args()
    reconcile(
        mark_phantoms=args.mark_phantoms,
        clean_phantom_clips=args.clean_phantom_clips,
    )
