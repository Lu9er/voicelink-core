#!/usr/bin/env python3
"""
Module 1: The Archive Ingester

Recursively scans a local directory for MP3 files, computes SHA256 hashes,
extracts duration via ffprobe, uploads to GCS, and upserts metadata into
Supabase with status='raw_uploaded'.

Usage:
    python ingest_archives.py /path/to/mp3/folder

Environment variables (via .env):
    SUPABASE_URL            - Supabase project URL
    SUPABASE_SERVICE_KEY    - Supabase service role key
    GCS_BUCKET_NAME         - Google Cloud Storage bucket name
    GOOGLE_APPLICATION_CREDENTIALS - Path to GCP service account JSON key
"""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from dotenv import load_dotenv
from google.cloud import storage
from supabase import create_client
from tqdm import tqdm

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("archive_ingester")

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"],
)
gcs_client = storage.Client()
bucket = gcs_client.bucket(os.environ["GCS_BUCKET_NAME"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def sha256_of_file(filepath: Path) -> str:
    """Return the hex SHA-256 digest of a file, reading in 64 KB chunks."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65_536), b""):
            h.update(chunk)
    return h.hexdigest()


def get_duration_seconds(filepath: Path) -> float:
    """Use ffprobe to extract the duration in seconds."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_entries", "format=duration",
            str(filepath),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])


def fetch_existing_hashes() -> set[str]:
    """Pre-fetch all archive external_call_ids already in Supabase.

    This lets us skip hashing → uploading for files we've already ingested
    on a previous run, without making per-file API calls.
    """
    hashes: set[str] = set()
    page_size = 1000
    offset = 0
    while True:
        resp = (
            supabase.table("recordings")
            .select("external_call_id")
            .eq("source_type", "archive")
            .range(offset, offset + page_size - 1)
            .execute()
        )
        if not resp.data:
            break
        for row in resp.data:
            hashes.add(row["external_call_id"])
        if len(resp.data) < page_size:
            break
        offset += page_size
    return hashes


def upload_to_gcs(filepath: Path, gcs_path: str) -> None:
    """Upload a local file to GCS. Overwrites if the blob already exists."""
    blob = bucket.blob(gcs_path)
    blob.upload_from_filename(str(filepath))


def upsert_recording(file_hash: str, duration: float, gcs_path: str) -> None:
    """Upsert a row into the recordings table, keyed on external_call_id."""
    supabase.table("recordings").upsert(
        {
            "external_call_id": file_hash,
            "source_type": "archive",
            "source_id": file_hash,
            "duration_seconds": duration,
            "gcs_path": gcs_path,
            "status": "raw_uploaded",
        },
        on_conflict="external_call_id",
    ).execute()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="VoiceLink Archive Ingester — Module 1",
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Root directory containing MP3 files to ingest",
    )
    args = parser.parse_args()

    archive_dir: Path = args.directory.resolve()
    if not archive_dir.is_dir():
        log.error(f"Directory not found: {archive_dir}")
        sys.exit(1)

    # Discover MP3 files
    mp3_files = sorted(archive_dir.rglob("*.mp3"))
    log.info(f"Found {len(mp3_files):,} MP3 files in {archive_dir}")
    if not mp3_files:
        return

    # Pre-fetch already-ingested hashes so we can skip them cheaply
    log.info("Fetching already-ingested hashes from Supabase...")
    existing_hashes = fetch_existing_hashes()
    log.info(f"{len(existing_hashes):,} recordings already ingested — will skip those")

    stats = {"uploaded": 0, "skipped": 0, "failed": 0}

    for filepath in tqdm(mp3_files, desc="Ingesting", unit="file"):
        try:
            # 1. Hash
            file_hash = sha256_of_file(filepath)

            # 2. Skip if already ingested
            if file_hash in existing_hashes:
                stats["skipped"] += 1
                continue

            # 3. Duration via ffprobe
            duration = get_duration_seconds(filepath)

            # 4. Upload to GCS
            gcs_path = f"raw_archives/{file_hash}.mp3"
            upload_to_gcs(filepath, gcs_path)

            # 5. Upsert into Supabase
            upsert_recording(file_hash, duration, gcs_path)

            # Track in local set so duplicate files within the same run are skipped
            existing_hashes.add(file_hash)
            stats["uploaded"] += 1
            log.info(f"OK  {filepath.name} ({duration:.1f}s) -> {gcs_path}")

        except Exception as e:
            stats["failed"] += 1
            log.error(f"FAIL {filepath.name}: {e}")

    # Summary
    log.info("=" * 50)
    log.info("Ingestion complete")
    log.info(f"  Uploaded : {stats['uploaded']:,}")
    log.info(f"  Skipped  : {stats['skipped']:,}")
    log.info(f"  Failed   : {stats['failed']:,}")
    log.info(f"  Total    : {len(mp3_files):,}")
    log.info("=" * 50)


if __name__ == "__main__":
    main()
