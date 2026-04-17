#!/usr/bin/env python3
"""
Luganda Yield Test — Process N recordings and report detailed metrics.

Processes files through Module 3 (VAD segmentation + clipping) and captures:
    - input duration
    - speech seconds retained
    - number of clips produced
    - average clip length
    - speech yield %
    - runtime per file

Saves sample clips locally for manual listening.

Usage:
    python yield_test.py                  # default 10 files
    python yield_test.py --count 50       # test 50 files
    python yield_test.py --ids id1 id2    # test specific recording IDs
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("yield_test")

# Ensure GCS creds
os.environ.setdefault(
    "GOOGLE_APPLICATION_CREDENTIALS",
    os.path.expanduser("~/voicelink/gcs-key.json"),
)

from supabase import create_client
from google.cloud import storage

from worker.process_audio import (
    ProcessorConfig,
    download_from_gcs,
    ffprobe_metadata,
    normalize_to_wav16k_mono,
    run_silero_vad,
    build_clips,
    encode_clip_to_mp3,
)

sb = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])
gcs_client = storage.Client()
bucket = gcs_client.bucket(os.environ["GCS_BUCKET_NAME"])

OUTPUT_DIR = Path("yield_test_output")
REPORTS_DIR = Path("reports")


def fetch_recordings(count: int = 10, ids: list[str] | None = None) -> list[dict]:
    """Get recording rows to test."""
    if ids:
        rows = []
        for rid in ids:
            r = sb.table("recordings").select("*").eq("id", rid).execute()
            if r.data:
                rows.append(r.data[0])
        return rows

    r = (
        sb.table("recordings")
        .select("*")
        .eq("status", "raw_uploaded")
        .limit(count)
        .execute()
    )
    return r.data


def process_one_for_yield(
    rec: dict, cfg: ProcessorConfig, sample_clips_dir: Path
) -> dict:
    """Process a single recording and return metrics (no DB writes)."""
    import tempfile

    recording_id = rec["id"]
    gcs_path = rec["gcs_path"]
    result = {
        "recording_id": recording_id,
        "gcs_path": gcs_path,
        "status": "ok",
    }

    t0 = time.time()

    with tempfile.TemporaryDirectory(prefix="yield_") as work_dir:
        raw_path = os.path.join(work_dir, "raw_audio")
        norm_path = os.path.join(work_dir, "normalized.wav")

        try:
            # Download
            blob = bucket.blob(gcs_path)
            blob.download_to_filename(raw_path)

            # Probe
            meta = ffprobe_metadata(raw_path)
            result["input_duration_s"] = meta["duration"]
            result["codec"] = meta["codec"]
            result["sample_rate"] = meta["sr"]
            result["channels"] = meta["channels"]

            # Normalize
            normalize_to_wav16k_mono(raw_path, norm_path)

            # VAD
            timestamps = run_silero_vad(norm_path)
            result["raw_vad_segments"] = len(timestamps)

            # Build clips
            clips = build_clips(timestamps, norm_path, cfg)
            result["clip_count"] = len(clips)

            if clips:
                durations = [end - start for start, end in clips]
                result["speech_seconds"] = round(sum(durations), 3)
                result["avg_clip_length_s"] = round(
                    sum(durations) / len(durations), 2
                )
                result["min_clip_length_s"] = round(min(durations), 2)
                result["max_clip_length_s"] = round(max(durations), 2)
                result["speech_yield"] = round(
                    result["speech_seconds"] / meta["duration"], 4
                )

                # Save first 5 clips as MP3 samples for listening
                clip_dir = sample_clips_dir / recording_id[:8]
                clip_dir.mkdir(parents=True, exist_ok=True)
                for i, (start, end) in enumerate(clips[:5]):
                    mp3_path = str(clip_dir / f"clip_{i:03d}.mp3")
                    encode_clip_to_mp3(
                        norm_path, start, end, mp3_path, cfg.clip_mp3_bitrate_kbps
                    )
                result["sample_clips_saved"] = min(len(clips), 5)
            else:
                result["speech_seconds"] = 0
                result["avg_clip_length_s"] = 0
                result["min_clip_length_s"] = 0
                result["max_clip_length_s"] = 0
                result["speech_yield"] = 0
                result["sample_clips_saved"] = 0

        except Exception as e:
            result["status"] = "error"
            result["error"] = str(e)[:300]
            log.error(f"[{recording_id[:8]}] FAIL: {e}")

    result["runtime_s"] = round(time.time() - t0, 1)
    return result


def run_yield_test(count: int = 10, ids: list[str] | None = None) -> None:
    cfg = ProcessorConfig.from_env()
    # Don't actually write to DB
    cfg.dry_run = True

    OUTPUT_DIR.mkdir(exist_ok=True)
    REPORTS_DIR.mkdir(exist_ok=True)
    sample_clips_dir = OUTPUT_DIR / "sample_clips"
    sample_clips_dir.mkdir(exist_ok=True)

    log.info(f"Fetching {count} recordings for yield test...")
    recordings = fetch_recordings(count=count, ids=ids)
    log.info(f"Got {len(recordings)} recordings")

    results = []
    for i, rec in enumerate(recordings):
        log.info(
            f"[{i + 1}/{len(recordings)}] Processing {rec['id'][:8]}... "
            f"({rec.get('duration_seconds', '?')}s)"
        )
        r = process_one_for_yield(rec, cfg, sample_clips_dir)
        results.append(r)

        # Print per-file summary
        if r["status"] == "ok":
            log.info(
                f"  -> {r['clip_count']} clips, "
                f"{r.get('speech_seconds', 0):.0f}s speech, "
                f"yield={r.get('speech_yield', 0):.1%}, "
                f"avg={r.get('avg_clip_length_s', 0):.1f}s, "
                f"runtime={r['runtime_s']:.0f}s"
            )
        else:
            log.info(f"  -> ERROR: {r.get('error', 'unknown')[:80]}")

    # Compute aggregate stats
    ok_results = [r for r in results if r["status"] == "ok"]
    if ok_results:
        total_input = sum(r["input_duration_s"] for r in ok_results)
        total_speech = sum(r["speech_seconds"] for r in ok_results)
        total_clips = sum(r["clip_count"] for r in ok_results)
        total_runtime = sum(r["runtime_s"] for r in ok_results)

        # Yield band classification
        yields = [r["speech_yield"] for r in ok_results]
        yields.sort()
        high = [y for y in yields if y > 0.50]
        medium = [y for y in yields if 0.20 <= y <= 0.50]
        low = [y for y in yields if y < 0.20]
        median_yield = yields[len(yields) // 2] if yields else 0

        summary = {
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "files_tested": len(recordings),
            "files_ok": len(ok_results),
            "files_error": len(results) - len(ok_results),
            "total_input_hours": round(total_input / 3600, 2),
            "total_speech_hours": round(total_speech / 3600, 2),
            "total_clips": total_clips,
            "aggregate_yield": round(total_speech / total_input, 4),
            "median_yield": round(median_yield, 4),
            "avg_clips_per_file": round(total_clips / len(ok_results), 1),
            "avg_clip_length_s": round(total_speech / total_clips, 2) if total_clips else 0,
            "avg_runtime_per_file_s": round(total_runtime / len(ok_results), 1),
            "total_runtime_s": round(total_runtime, 1),
            "yield_bands": {
                "high_gt50pct": len(high),
                "medium_20_50pct": len(medium),
                "low_lt20pct": len(low),
            },
            "per_file": results,
        }
    else:
        summary = {
            "test_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "files_tested": len(recordings),
            "files_ok": 0,
            "files_error": len(results),
            "per_file": results,
        }

    # Write report
    report_path = REPORTS_DIR / "yield_test_results.json"
    with open(report_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Print summary
    print()
    print("=" * 65)
    print("  LUGANDA YIELD TEST RESULTS")
    print("=" * 65)
    if ok_results:
        print(f"  Files tested:        {summary['files_tested']}")
        print(f"  Files OK:            {summary['files_ok']}")
        print(f"  Files error:         {summary['files_error']}")
        print()
        print(f"  Total input:         {summary['total_input_hours']:.2f} hours")
        print(f"  Total speech:        {summary['total_speech_hours']:.2f} hours")
        print(f"  Aggregate yield:     {summary['aggregate_yield']:.1%}")
        print()
        print(f"  Total clips:         {summary['total_clips']}")
        print(f"  Avg clips/file:      {summary['avg_clips_per_file']:.0f}")
        print(f"  Avg clip length:     {summary['avg_clip_length_s']:.1f}s")
        print()
        print(f"  Median yield:        {summary['median_yield']:.1%}")
        print()
        bands = summary["yield_bands"]
        print(f"  YIELD BANDS")
        print(f"    High  (>50%):      {bands['high_gt50pct']}")
        print(f"    Medium (20-50%):   {bands['medium_20_50pct']}")
        print(f"    Low   (<20%):      {bands['low_lt20pct']}")
        print()
        print(f"  Avg runtime/file:    {summary['avg_runtime_per_file_s']:.0f}s")
        print(f"  Total runtime:       {summary['total_runtime_s']:.0f}s")
        print()
        print("  PER-FILE BREAKDOWN")
        print("  " + "-" * 63)
        print(
            f"  {'ID':>8}  {'Input':>7}  {'Speech':>7}  "
            f"{'Yield':>6}  {'Clips':>5}  {'AvgLen':>6}  {'Time':>5}"
        )
        print("  " + "-" * 63)
        for r in results:
            rid = r["recording_id"][:8]
            if r["status"] == "ok":
                print(
                    f"  {rid}  "
                    f"{r['input_duration_s']:>6.0f}s  "
                    f"{r['speech_seconds']:>6.0f}s  "
                    f"{r['speech_yield']:>5.1%}  "
                    f"{r['clip_count']:>5}  "
                    f"{r['avg_clip_length_s']:>5.1f}s  "
                    f"{r['runtime_s']:>4.0f}s"
                )
            else:
                print(f"  {rid}  ERROR: {r.get('error', '?')[:40]}")
    print("  " + "-" * 63)
    print()
    print(f"  Sample clips:  {sample_clips_dir.resolve()}")
    print(f"  Full report:   {report_path.resolve()}")
    print("=" * 65)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Luganda Yield Test")
    parser.add_argument("--count", type=int, default=10, help="Number of files to test")
    parser.add_argument("--ids", nargs="+", help="Specific recording IDs to test")
    args = parser.parse_args()
    run_yield_test(count=args.count, ids=args.ids)
