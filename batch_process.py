#!/usr/bin/env python3
"""
Batch Processor — Process recordings in resilient chunks.

Runs Module 3 (process_audio) on raw_uploaded recordings in small chunks.
Progress is saved after every file to reports/batch_progress.json, so the
process can be restarted and will pick up where it left off.

Usage:
    python batch_process.py                          # process 10 files (default)
    python batch_process.py --total 200              # 200 files, 10 per chunk
    python batch_process.py --total 200 --chunk 20   # 200 files, 20 per chunk
    python batch_process.py --reset-progress --total 200  # fresh start

Each chunk fetches raw_uploaded rows, processes them, and saves progress.
Already-processed files are skipped via Module 3's atomic claim mechanism.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.expanduser("~/voicelink/gcs-key.json"),
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("batch")

from supabase import create_client

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

REPORTS_DIR = Path("reports")
PROGRESS_FILE = REPORTS_DIR / "batch_progress.json"


def load_progress() -> dict:
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {
        "started_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "total_attempted": 0,
        "total_processed": 0,
        "total_failed": 0,
        "total_skipped": 0,
        "total_clips": 0,
        "total_speech_seconds": 0.0,
        "chunks_completed": 0,
        "results": [],
    }


def save_progress(progress: dict) -> None:
    REPORTS_DIR.mkdir(exist_ok=True)
    progress["last_updated"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)


def fetch_batch(limit: int) -> list[dict]:
    """Get the next batch of raw_uploaded recordings."""
    r = (
        sb.table("recordings")
        .select("id, gcs_path, duration_seconds")
        .eq("status", "raw_uploaded")
        .limit(limit)
        .execute()
    )
    return r.data


def process_chunk(chunk: list[dict], progress: dict) -> None:
    """Process a chunk of recordings through Module 3."""
    from worker.process_audio import process_one, ProcessorConfig

    cfg = ProcessorConfig.from_env()

    for rec in chunk:
        rid = rec["id"]
        t0 = time.time()

        log.info(
            f"[{progress['total_attempted'] + 1}] "
            f"Processing {rid[:8]}... ({rec.get('duration_seconds', 0):.0f}s)"
        )

        max_retries = 2
        for attempt in range(max_retries + 1):
            try:
                result = process_one(rid, cfg)
                break
            except Exception as e:
                if attempt < max_retries:
                    wait = 2 ** (attempt + 1)
                    log.warning(f"  Attempt {attempt + 1} failed: {e}. Retrying in {wait}s...")
                    time.sleep(wait)
                else:
                    result = "failed"
                    log.error(f"  Unhandled error after {max_retries + 1} attempts: {e}")

        elapsed = round(time.time() - t0, 1)
        progress["total_attempted"] += 1

        if result == "processed":
            # Fetch metrics from DB
            r = (
                sb.table("recordings")
                .select("clip_count, speech_seconds, speech_yield")
                .eq("id", rid)
                .execute()
            )
            metrics = r.data[0] if r.data else {}
            clips = metrics.get("clip_count", 0)
            speech = metrics.get("speech_seconds", 0)
            syield = metrics.get("speech_yield", 0)

            progress["total_processed"] += 1
            progress["total_clips"] += clips
            progress["total_speech_seconds"] += speech

            if syield > 0.50:
                band = "high"
            elif syield >= 0.20:
                band = "medium"
            else:
                band = "low"

            log.info(
                f"  -> OK: {clips} clips, {speech:.0f}s speech, "
                f"yield={syield:.1%}, band={band}, {elapsed:.0f}s"
            )

            progress["results"].append({
                "id": rid,
                "result": "processed",
                "clips": clips,
                "speech_seconds": round(speech, 1),
                "yield": round(syield, 4),
                "band": band,
                "runtime_s": elapsed,
            })

        elif result == "skipped":
            progress["total_skipped"] += 1
            log.info(f"  -> SKIPPED (already claimed)")
            progress["results"].append({
                "id": rid, "result": "skipped", "runtime_s": elapsed,
            })

        elif result == "failed":
            progress["total_failed"] += 1
            log.info(f"  -> FAILED ({elapsed:.0f}s)")
            progress["results"].append({
                "id": rid, "result": "failed", "runtime_s": elapsed,
            })

        # Save progress after every file
        save_progress(progress)


def print_summary(progress: dict) -> None:
    p = progress
    speech_h = p["total_speech_seconds"] / 3600

    ok_results = [r for r in p["results"] if r["result"] == "processed"]
    yields = sorted([r["yield"] for r in ok_results])

    high = sum(1 for y in yields if y > 0.50)
    medium = sum(1 for y in yields if 0.20 <= y <= 0.50)
    low = sum(1 for y in yields if y < 0.20)
    median = yields[len(yields) // 2] if yields else 0
    avg_yield = sum(yields) / len(yields) if yields else 0

    total_runtime = sum(r.get("runtime_s", 0) for r in p["results"])
    avg_runtime = total_runtime / len(p["results"]) if p["results"] else 0

    print()
    print("=" * 60)
    print("  BATCH PROCESSING SUMMARY")
    print("=" * 60)
    print(f"  Attempted:         {p['total_attempted']}")
    print(f"  Processed:         {p['total_processed']}")
    print(f"  Failed:            {p['total_failed']}")
    print(f"  Skipped:           {p['total_skipped']}")
    print()
    print(f"  Total clips:       {p['total_clips']:,}")
    print(f"  Speech hours:      {speech_h:.2f}")
    print(f"  Avg yield:         {avg_yield:.1%}")
    print(f"  Median yield:      {median:.1%}")
    print()
    print(f"  YIELD BANDS")
    print(f"    High  (>50%):    {high}")
    print(f"    Medium (20-50%): {medium}")
    print(f"    Low   (<20%):    {low}")
    print()
    print(f"  Avg runtime/file:  {avg_runtime:.0f}s")
    print(f"  Total runtime:     {total_runtime / 60:.1f} min")
    print(f"  Chunks completed:  {p['chunks_completed']}")
    print()

    if p["total_processed"] > 0:
        scale = 1919 / p["total_processed"]
        print(f"  PROJECTION TO 1,919 FILES")
        print(f"    Est. speech hours:    ~{speech_h * scale:.0f}")
        print(f"    Est. total clips:     ~{p['total_clips'] * scale:,.0f}")
        print(f"    Est. processing time: ~{avg_runtime * 1919 / 3600:.1f} hours")

    print()
    print(f"  Progress file: {PROGRESS_FILE}")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="VoiceLink Batch Processor")
    parser.add_argument("--total", type=int, default=10, help="Total files to process")
    parser.add_argument("--chunk", type=int, default=10, help="Files per chunk")
    parser.add_argument(
        "--reset-progress", action="store_true",
        help="Clear previous progress file and start fresh",
    )
    args = parser.parse_args()

    REPORTS_DIR.mkdir(exist_ok=True)

    if args.reset_progress and PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        log.info("Progress file reset")

    progress = load_progress()
    target = args.total
    already = progress["total_attempted"]

    if already >= target:
        log.info(f"Already attempted {already} >= target {target}. Use --reset-progress to start over.")
        print_summary(progress)
        return

    remaining = target - already
    log.info(
        f"Batch processor: target={target}, already={already}, "
        f"remaining={remaining}, chunk={args.chunk}"
    )

    while remaining > 0:
        chunk_size = min(args.chunk, remaining)
        batch = fetch_batch(chunk_size)

        if not batch:
            log.info("No more raw_uploaded recordings. Done.")
            break

        log.info(f"--- Chunk {progress['chunks_completed'] + 1}: {len(batch)} files ---")
        process_chunk(batch, progress)
        progress["chunks_completed"] += 1
        save_progress(progress)

        remaining = target - progress["total_attempted"]

        log.info(
            f"Chunk done. {progress['total_processed']} processed, "
            f"{progress['total_failed']} failed, "
            f"{progress['total_clips']} clips, "
            f"{remaining} remaining"
        )

    print_summary(progress)


if __name__ == "__main__":
    main()
