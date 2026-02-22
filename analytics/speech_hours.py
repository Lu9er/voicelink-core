#!/usr/bin/env python3
"""
Module 4A — Speech Hours Analytics

Reads processed recordings from Supabase and outputs:
  a) Total speech hours across matching recordings
  b) Ranked table (or CSV) of recordings by speech_seconds

Usage:
    python -m analytics.speech_hours
    python -m analytics.speech_hours --status processed --min-speech-yield 0.10
    python -m analytics.speech_hours --limit 50 --csv report.csv
"""

from __future__ import annotations

import argparse
import csv
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("voicelink.analytics")

FIELDS = [
    "id",
    "duration_seconds",
    "speech_seconds",
    "speech_yield",
    "clip_count",
    "status",
    "created_at",
]


def _make_supabase():
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print(
            "ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY are required.",
            file=sys.stderr,
        )
        sys.exit(1)
    from supabase import create_client

    return create_client(url, key)


def query_recordings(
    sb,
    status: str = "processed",
    min_yield: float | None = None,
    limit: int | None = None,
) -> list[dict]:
    q = sb.table("recordings").select(", ".join(FIELDS)).eq("status", status)
    if min_yield is not None:
        q = q.gte("speech_yield", min_yield)
    q = q.order("speech_seconds", desc=True)
    if limit:
        q = q.limit(limit)
    return q.execute().data


def print_summary(rows: list[dict]) -> None:
    total_dur = sum(r.get("duration_seconds") or 0 for r in rows)
    total_speech = sum(r.get("speech_seconds") or 0 for r in rows)
    total_clips = sum(r.get("clip_count") or 0 for r in rows)
    avg_yield = (total_speech / total_dur) if total_dur > 0 else 0

    print(f"Recordings : {len(rows)}")
    print(f"Total dur  : {total_dur / 3600:.2f} h")
    print(f"Speech     : {total_speech / 3600:.2f} h")
    print(f"Clips      : {total_clips}")
    print(f"Avg yield  : {avg_yield:.1%}")


def print_table(rows: list[dict]) -> None:
    hdr = f"{'ID':>36}  {'Dur(s)':>8}  {'Speech':>8}  {'Yield':>7}  {'Clips':>5}"
    print(f"\n{hdr}")
    print("-" * len(hdr))
    for r in rows:
        dur = r.get("duration_seconds") or 0
        sp = r.get("speech_seconds") or 0
        yld = r.get("speech_yield") or 0
        cc = r.get("clip_count") or 0
        print(f"{r['id']}  {dur:>8.1f}  {sp:>8.1f}  {yld:>6.1%}  {cc:>5}")


def write_csv(rows: list[dict], path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Written to {path}")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="VoiceLink speech-hour analytics",
    )
    parser.add_argument(
        "--status", default="processed", help="Filter by status (default: processed)",
    )
    parser.add_argument(
        "--min-speech-yield", type=float, default=None,
        help="Minimum speech_yield filter (e.g. 0.10 for 10%%)",
    )
    parser.add_argument(
        "--limit", type=int, default=None, help="Max rows to return",
    )
    parser.add_argument(
        "--csv", default=None, metavar="PATH", help="Write results to CSV file",
    )
    args = parser.parse_args()

    sb = _make_supabase()
    rows = query_recordings(sb, args.status, args.min_speech_yield, args.limit)

    if not rows:
        print("No recordings found matching filters.")
        return

    print_summary(rows)

    if args.csv:
        write_csv(rows, args.csv)
    else:
        print_table(rows)


if __name__ == "__main__":
    main()
