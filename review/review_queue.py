#!/usr/bin/env python3
"""
Module 4C — Review Queue CLI

Manage the clip review workflow: list, approve, reject, and edit transcripts.

Commands:
    python -m review.review_queue list [--limit N] [--status pending_review]
    python -m review.review_queue approve --clip-id <uuid>
    python -m review.review_queue reject  --clip-id <uuid> --reason "..."
    python -m review.review_queue set-transcript --clip-id <uuid> --text "..."

DRY_RUN=true will log intended changes without writing to Supabase.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("voicelink.review")

DRY_RUN = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")


def _make_supabase():
    if DRY_RUN:
        return None
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_KEY", "")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY required.", file=sys.stderr)
        sys.exit(1)
    from supabase import create_client

    return create_client(url, key)


# ---------------------------------------------------------------------------
# Core operations (importable by API routes)
# ---------------------------------------------------------------------------


def list_clips(sb, status: str = "pending_review", limit: int = 20) -> list[dict]:
    """Return clips matching status, ordered oldest-first."""
    resp = (
        sb.table("clips")
        .select("id, recording_id, gcs_clip_url, duration_seconds, transcript, status, created_at")
        .eq("status", status)
        .order("created_at", desc=False)
        .limit(limit)
        .execute()
    )
    return resp.data


def approve_clip(sb, clip_id: str) -> dict | None:
    """Set clip status to 'approved'. Returns updated row or None."""
    resp = (
        sb.table("clips")
        .update({"status": "approved"})
        .eq("id", clip_id)
        .eq("status", "pending_review")
        .execute()
    )
    return resp.data[0] if resp.data else None


def reject_clip(sb, clip_id: str, reason: str = "") -> dict | None:
    """Set clip status to 'rejected' and optionally store reason."""
    update: dict = {"status": "rejected"}
    if reason:
        update["rejection_reason"] = reason
    resp = (
        sb.table("clips")
        .update(update)
        .eq("id", clip_id)
        .execute()
    )
    return resp.data[0] if resp.data else None


def set_transcript(sb, clip_id: str, text: str) -> dict | None:
    """Write or overwrite a clip transcript."""
    resp = (
        sb.table("clips")
        .update({"transcript": text})
        .eq("id", clip_id)
        .execute()
    )
    return resp.data[0] if resp.data else None


# ---------------------------------------------------------------------------
# CLI handlers
# ---------------------------------------------------------------------------


def _cmd_list(args, sb) -> None:
    if DRY_RUN:
        log.info(f"DRY_RUN: would list clips status={args.status} limit={args.limit}")
        return

    rows = list_clips(sb, args.status, args.limit)
    if not rows:
        print("No clips found.")
        return

    print(f"{'ID':>36}  {'Dur':>6}  {'Status':>15}  GCS path")
    print("-" * 100)
    for r in rows:
        dur = r.get("duration_seconds") or 0
        st = r.get("status", "")
        gcs = r.get("gcs_clip_url", "")
        print(f"{r['id']}  {dur:>5.1f}s  {st:>15}  {gcs}")
    print(f"\n{len(rows)} clip(s)")


def _cmd_approve(args, sb) -> None:
    if DRY_RUN:
        log.info(f"DRY_RUN: would approve clip {args.clip_id}")
        return

    row = approve_clip(sb, args.clip_id)
    if row:
        print(f"[OK] Approved {args.clip_id}")
    else:
        print(f"[SKIP] {args.clip_id} not found or not in pending_review")


def _cmd_reject(args, sb) -> None:
    if DRY_RUN:
        log.info(f"DRY_RUN: would reject clip {args.clip_id} reason={args.reason}")
        return

    row = reject_clip(sb, args.clip_id, args.reason)
    if row:
        print(f"[OK] Rejected {args.clip_id}")
    else:
        print(f"[SKIP] {args.clip_id} not found")


def _cmd_set_transcript(args, sb) -> None:
    if DRY_RUN:
        log.info(f"DRY_RUN: would set transcript on {args.clip_id}")
        return

    row = set_transcript(sb, args.clip_id, args.text)
    if row:
        print(f"[OK] Transcript set on {args.clip_id}")
    else:
        print(f"[SKIP] {args.clip_id} not found")


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="VoiceLink review queue")
    sub = parser.add_subparsers(dest="command", required=True)

    # list
    p_list = sub.add_parser("list", help="List clips by status")
    p_list.add_argument("--status", default="pending_review")
    p_list.add_argument("--limit", type=int, default=20)

    # approve
    p_approve = sub.add_parser("approve", help="Approve a clip")
    p_approve.add_argument("--clip-id", required=True)

    # reject
    p_reject = sub.add_parser("reject", help="Reject a clip")
    p_reject.add_argument("--clip-id", required=True)
    p_reject.add_argument("--reason", default="", help="Rejection reason")

    # set-transcript
    p_tx = sub.add_parser("set-transcript", help="Set/edit a clip transcript")
    p_tx.add_argument("--clip-id", required=True)
    p_tx.add_argument("--text", required=True)

    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"
        global DRY_RUN
        DRY_RUN = True

    sb = _make_supabase()

    handlers = {
        "list": _cmd_list,
        "approve": _cmd_approve,
        "reject": _cmd_reject,
        "set-transcript": _cmd_set_transcript,
    }
    handlers[args.command](args, sb)


if __name__ == "__main__":
    main()
