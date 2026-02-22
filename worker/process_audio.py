#!/usr/bin/env python3
"""
Module 3 — Audio Processing Worker

Process a single recording end-to-end:
    download → probe → normalize 16 kHz mono → silero-VAD → clip → MP3 →
    upload → insert clips → finalize.

Supports DRY_RUN=true to skip all external writes (Supabase, GCS) and
log intended actions instead.  Useful for local testing without creds.

CLI:
    python -m worker.process_audio --recording-id <uuid>
    python -m worker.process_audio --recording-id <uuid> --dry-run

API:
    POST /api/worker/process-audio  {"recording_id":"<uuid>"}
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
import wave
from dataclasses import dataclass

import torch
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("voicelink.processor")

# ---------------------------------------------------------------------------
# Canonical audio format
# ---------------------------------------------------------------------------
CANONICAL_SR = 16_000  # Hz, mono, s16le PCM


# ===================================================================
# Configuration
# ===================================================================
@dataclass
class ProcessorConfig:
    """All tunables, loaded from environment variables."""

    supabase_url: str = ""
    supabase_key: str = ""
    gcs_bucket: str = ""
    clip_mp3_bitrate_kbps: int = 64
    clip_min_seconds: float = 3.0
    clip_max_seconds: float = 15.0
    vad_merge_gap: float = 0.5
    speech_yield_gate: float = 0.01  # 1 %
    dry_run: bool = False

    @classmethod
    def from_env(cls) -> ProcessorConfig:
        dry = os.environ.get("DRY_RUN", "false").lower() in ("1", "true", "yes")

        missing: list[str] = []
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        bucket = os.environ.get("GCS_BUCKET_NAME", "")

        if not dry:
            if not url:
                missing.append("SUPABASE_URL")
            if not key:
                missing.append("SUPABASE_SERVICE_KEY")
            if not bucket:
                missing.append("GCS_BUCKET_NAME")
            if missing:
                raise EnvironmentError(
                    f"Missing required env var(s): {', '.join(missing)}. "
                    "Set DRY_RUN=true to skip external services."
                )

        return cls(
            supabase_url=url,
            supabase_key=key,
            gcs_bucket=bucket,
            clip_mp3_bitrate_kbps=int(
                os.environ.get("CLIP_MP3_BITRATE_KBPS", "64")
            ),
            clip_min_seconds=float(os.environ.get("CLIP_MIN_SECONDS", "3")),
            clip_max_seconds=float(os.environ.get("CLIP_MAX_SECONDS", "15")),
            vad_merge_gap=float(os.environ.get("VAD_MERGE_GAP_SECONDS", "0.5")),
            speech_yield_gate=float(
                os.environ.get("SPEECH_YIELD_GATE", "0.01")
            ),
            dry_run=dry,
        )


# ===================================================================
# Client factories (lazy; None when dry-run)
# ===================================================================
def _make_supabase(cfg: ProcessorConfig):
    if cfg.dry_run:
        return None
    from supabase import create_client

    return create_client(cfg.supabase_url, cfg.supabase_key)


def _make_bucket(cfg: ProcessorConfig):
    if cfg.dry_run:
        return None
    from google.cloud import storage

    return storage.Client().bucket(cfg.gcs_bucket)


# ===================================================================
# Supabase operations
# ===================================================================
def claim_recording(supabase, recording_id: str) -> dict | None:
    """Atomically move status raw_uploaded → processing.

    Returns the recording row on success, or None if already claimed /
    processed / not found.
    """
    if supabase is None:  # dry-run
        log.info(f"[{recording_id}] DRY_RUN: claim_recording (assumed success)")
        return {
            "id": recording_id,
            "gcs_path": "dry_run/placeholder.wav",
            "duration_seconds": None,
        }

    resp = (
        supabase.table("recordings")
        .update({"status": "processing"})
        .eq("id", recording_id)
        .eq("status", "raw_uploaded")
        .execute()
    )
    if not resp.data:
        return None
    return resp.data[0]


def fetch_recording(supabase, recording_id: str) -> dict | None:
    """Read-only fetch of a recording row (no status change)."""
    if supabase is None:
        return {
            "id": recording_id,
            "gcs_path": "dry_run/placeholder.wav",
            "duration_seconds": None,
        }

    resp = (
        supabase.table("recordings")
        .select("id, gcs_path, duration_seconds")
        .eq("id", recording_id)
        .single()
        .execute()
    )
    return resp.data


def finalize_recording_success(
    supabase,
    recording_id: str,
    status: str,
    metrics: dict,
    dry_run: bool = False,
) -> None:
    """Set recording to a success status with metrics."""
    update = {"status": status, **metrics}
    if dry_run:
        log.info(f"[{recording_id}] DRY_RUN: finalize -> {update}")
        return
    try:
        supabase.table("recordings").update(update).eq(
            "id", recording_id
        ).execute()
    except Exception as e:
        # Optional metric columns may not exist — fall back to status only
        log.warning(
            f"[{recording_id}] Full metric update failed ({e}); "
            "retrying with status-only"
        )
        supabase.table("recordings").update({"status": status}).eq(
            "id", recording_id
        ).execute()


def finalize_recording_failed(
    supabase,
    recording_id: str,
    failure_reason: str,
    dry_run: bool = False,
) -> None:
    """Set recording to failed with a reason string."""
    if dry_run:
        log.info(f"[{recording_id}] DRY_RUN: finalize -> failed: {failure_reason}")
        return
    try:
        supabase.table("recordings").update(
            {"status": "failed", "failure_reason": failure_reason[:500]}
        ).eq("id", recording_id).execute()
    except Exception as e:
        log.error(f"[{recording_id}] Could not write failure to DB: {e}")


def insert_clips(
    supabase, clip_rows: list[dict], dry_run: bool = False
) -> None:
    """Batch-insert clip rows into the clips table."""
    if dry_run:
        log.info(f"DRY_RUN: would insert {len(clip_rows)} clip(s)")
        for r in clip_rows:
            log.info(f"  {r['gcs_clip_url']}  {r['duration_seconds']:.1f}s")
        return
    supabase.table("clips").insert(clip_rows).execute()


# ===================================================================
# GCS operations
# ===================================================================
def download_from_gcs(
    bucket, gcs_path: str, dst_path: str, dry_run: bool = False
) -> None:
    """Stream-download a GCS object to a local file."""
    if dry_run:
        log.info(f"DRY_RUN: would download gs://.../{gcs_path} -> {dst_path}")
        return
    blob = bucket.blob(gcs_path)
    blob.download_to_filename(dst_path)


def upload_clip_to_gcs(
    bucket, local_path: str, dest_path: str, dry_run: bool = False
) -> None:
    """Upload a local file to GCS."""
    if dry_run:
        log.info(f"DRY_RUN: would upload {local_path} -> gs://.../{dest_path}")
        return
    blob = bucket.blob(dest_path)
    blob.upload_from_filename(local_path)


# ===================================================================
# FFprobe / FFmpeg
# ===================================================================
def ffprobe_metadata(path: str) -> dict:
    """Probe an audio file.

    Returns dict with keys: duration (float s), sr (int Hz),
    channels (int), codec (str).
    """
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            path,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")

    data = json.loads(result.stdout)
    audio = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
        None,
    )
    if audio is None:
        raise RuntimeError("No audio stream found in file")

    duration = float(data.get("format", {}).get("duration", 0))
    return {
        "duration": duration,
        "sr": int(audio["sample_rate"]),
        "channels": int(audio["channels"]),
        "codec": audio["codec_name"],
    }


def normalize_to_wav16k_mono(src: str, dst: str) -> None:
    """Convert any audio to 16 kHz mono s16 PCM WAV."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            src,
            "-ar",
            str(CANONICAL_SR),
            "-ac",
            "1",
            "-sample_fmt",
            "s16",
            "-f",
            "wav",
            dst,
        ],
        check=True,
        capture_output=True,
    )


def encode_clip_to_mp3(
    wav_norm: str,
    start_s: float,
    end_s: float,
    out_mp3_path: str,
    bitrate_kbps: int = 64,
) -> None:
    """Extract a time segment from normalised WAV and encode to MP3."""
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            wav_norm,
            "-ss",
            str(start_s),
            "-to",
            str(end_s),
            "-codec:a",
            "libmp3lame",
            "-b:a",
            f"{bitrate_kbps}k",
            "-ar",
            str(CANONICAL_SR),
            "-ac",
            "1",
            "-f",
            "mp3",
            out_mp3_path,
        ],
        check=True,
        capture_output=True,
    )


# ===================================================================
# Silero VAD
# ===================================================================
_vad_cache: tuple | None = None


def _load_vad():
    """Load (and cache) the silero-vad model + helper."""
    global _vad_cache
    if _vad_cache is None:
        log.info("Loading silero-vad model …")
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            trust_repo=True,
        )
        get_speech_ts = utils[0]  # get_speech_timestamps
        _vad_cache = (model, get_speech_ts)
        log.info("silero-vad loaded.")
    return _vad_cache


def _read_wav_tensor(path: str) -> torch.Tensor:
    """Read a 16 kHz mono s16 WAV into a float32 torch tensor.

    Uses only stdlib ``wave`` — no torchaudio dependency.
    """
    with wave.open(path, "rb") as wf:
        frames = wf.readframes(wf.getnframes())
    # int16 little-endian → float32 in [-1, 1]
    return torch.frombuffer(bytearray(frames), dtype=torch.int16).float() / 32768.0


def run_silero_vad(wav_path: str) -> list[dict]:
    """Run silero-vad on a 16 kHz mono WAV.

    Returns list of ``{"start": <samples>, "end": <samples>}`` dicts.
    """
    model, get_speech_ts = _load_vad()
    wav = _read_wav_tensor(wav_path)
    return get_speech_ts(wav, model, sampling_rate=CANONICAL_SR)


# ===================================================================
# Clip building (merge / split)
# ===================================================================
def build_clips(
    timestamps: list[dict],
    wav_path: str,
    cfg: ProcessorConfig,
) -> list[tuple[float, float]]:
    """Merge small gaps, drop < min, split > max.

    *wav_path* is accepted for interface consistency but unused —
    all timing information comes from *timestamps*.

    Returns ``[(start_s, end_s), …]``.
    """
    if not timestamps:
        return []

    # Sample offsets → seconds
    segs = [
        (t["start"] / CANONICAL_SR, t["end"] / CANONICAL_SR) for t in timestamps
    ]

    # --- Merge segments separated by gaps ≤ threshold ---
    merged: list[tuple[float, float]] = [segs[0]]
    for start, end in segs[1:]:
        _, prev_end = merged[-1]
        if start - prev_end <= cfg.vad_merge_gap:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))

    # --- Split long segments, drop short ones ---
    final: list[tuple[float, float]] = []
    for start, end in merged:
        dur = end - start
        if dur < cfg.clip_min_seconds:
            continue
        if dur <= cfg.clip_max_seconds:
            final.append((round(start, 3), round(end, 3)))
        else:
            t = start
            while t + cfg.clip_min_seconds <= end:
                chunk_end = min(t + cfg.clip_max_seconds, end)
                if chunk_end - t >= cfg.clip_min_seconds:
                    final.append((round(t, 3), round(chunk_end, 3)))
                t = chunk_end

    return final


# ===================================================================
# Main orchestrator
# ===================================================================
def process_one(recording_id: str, cfg: ProcessorConfig | None = None) -> str:
    """Process a single recording end-to-end.

    Returns one of:
        ``"processed"``  — clips extracted and uploaded
        ``"processed_low_speech"`` — yield below gate; no clips uploaded
        ``"skipped"``  — recording not in raw_uploaded (already claimed)
        ``"failed"``   — error; failure_reason written to DB
    """
    if cfg is None:
        cfg = ProcessorConfig.from_env()

    sb = _make_supabase(cfg)
    bucket = _make_bucket(cfg)

    # ---- Step 1: Atomic claim ------------------------------------------------
    row = claim_recording(sb, recording_id)
    if row is None:
        log.info(f"[{recording_id}] SKIP_ALREADY_CLAIMED")
        return "skipped"

    log.info(f"[{recording_id}] CLAIMED")
    gcs_path = row["gcs_path"]

    with tempfile.TemporaryDirectory(prefix="voicelink_") as work_dir:
        raw_path = os.path.join(work_dir, "raw_audio")
        norm_path = os.path.join(work_dir, "normalized.wav")
        clips_dir = os.path.join(work_dir, "clips")
        os.makedirs(clips_dir)

        try:
            # ---- Step 2: Download from GCS -----------------------------------
            download_from_gcs(bucket, gcs_path, raw_path, cfg.dry_run)
            log.info(f"[{recording_id}] DOWNLOADED {gcs_path}")

            # ---- Step 3: Probe source metadata -------------------------------
            if cfg.dry_run and not os.path.exists(raw_path):
                # Nothing to probe in pure dry-run (no real file)
                meta = {"duration": 0, "sr": 8000, "channels": 1, "codec": "pcm_s16le"}
                log.info(f"[{recording_id}] PROBED (dry-run defaults)")
            else:
                meta = ffprobe_metadata(raw_path)
                log.info(
                    f"[{recording_id}] PROBED "
                    f"codec={meta['codec']} sr={meta['sr']} "
                    f"ch={meta['channels']} dur={meta['duration']:.1f}s"
                )

            # Persist source metadata (defensive — columns may not exist)
            if sb is not None:
                try:
                    sb.table("recordings").update(
                        {
                            "source_sample_rate": meta["sr"],
                            "source_codec": meta["codec"],
                            "source_channels": meta["channels"],
                        }
                    ).eq("id", recording_id).execute()
                except Exception as e:
                    log.warning(
                        f"[{recording_id}] Source metadata update skipped: {e}"
                    )

            # ---- Step 4: Normalise to 16 kHz mono WAV ------------------------
            if cfg.dry_run and not os.path.exists(raw_path):
                log.info(f"[{recording_id}] NORMALIZED (dry-run skip)")
            else:
                normalize_to_wav16k_mono(raw_path, norm_path)
                log.info(f"[{recording_id}] NORMALIZED 16kHz mono WAV")

            # ---- Step 5: Silero VAD ------------------------------------------
            if cfg.dry_run and not os.path.exists(norm_path):
                timestamps: list[dict] = []
                log.info(f"[{recording_id}] VAD_DONE 0 raw segment(s) (dry-run)")
            else:
                timestamps = run_silero_vad(norm_path)
                log.info(
                    f"[{recording_id}] VAD_DONE "
                    f"{len(timestamps)} raw segment(s)"
                )

            # ---- Step 6: Build clips (merge / split) -------------------------
            clips = build_clips(timestamps, norm_path, cfg)

            # ---- Step 7: Compute metrics -------------------------------------
            speech_seconds = sum(end - start for start, end in clips)
            clip_count = len(clips)
            total_dur = meta["duration"]
            speech_yield = speech_seconds / total_dur if total_dur > 0 else 0.0

            log.info(
                f"[{recording_id}] CLIPS_BUILT "
                f"count={clip_count} "
                f"speech={speech_seconds:.1f}s "
                f"yield={speech_yield:.1%}"
            )

            metrics = {
                "clip_count": clip_count,
                "speech_seconds": round(speech_seconds, 3),
                "speech_yield": round(speech_yield, 4),
            }

            # ---- Step 8: Speech-yield gate -----------------------------------
            if speech_yield < cfg.speech_yield_gate:
                log.info(
                    f"[{recording_id}] GATED_LOW_SPEECH "
                    f"yield={speech_yield:.1%} < "
                    f"gate={cfg.speech_yield_gate:.0%}"
                )
                finalize_recording_success(
                    sb, recording_id, "processed_low_speech", metrics,
                    cfg.dry_run,
                )
                log.info(
                    f"[{recording_id}] DB_UPDATED processed_low_speech"
                )
                return "processed_low_speech"

            # ---- Step 9: Encode, upload, collect clip rows -------------------
            clip_rows: list[dict] = []
            for i, (start, end) in enumerate(clips):
                mp3_path = os.path.join(clips_dir, f"clip_{i:03d}.mp3")
                encode_clip_to_mp3(
                    norm_path, start, end, mp3_path,
                    cfg.clip_mp3_bitrate_kbps,
                )
                dest_gcs = f"clips/{recording_id}/clip_{i:03d}.mp3"
                upload_clip_to_gcs(bucket, mp3_path, dest_gcs, cfg.dry_run)

                clip_rows.append({
                    "recording_id": recording_id,
                    "gcs_clip_url": dest_gcs,
                    "duration_seconds": round(end - start, 3),
                    "transcript": None,
                    "status": "pending_review",
                })

            log.info(f"[{recording_id}] UPLOADED {len(clip_rows)} clip(s)")

            # ---- Step 10: Insert clips + finalise ----------------------------
            insert_clips(sb, clip_rows, cfg.dry_run)
            finalize_recording_success(
                sb, recording_id, "processed", metrics, cfg.dry_run,
            )
            log.info(f"[{recording_id}] DB_UPDATED processed")
            return "processed"

        except Exception as e:
            log.error(f"[{recording_id}] FAIL: {e}", exc_info=True)
            finalize_recording_failed(
                sb, recording_id, str(e)[:500], cfg.dry_run,
            )
            log.info(f"[{recording_id}] DB_UPDATED failed")
            return "failed"


# ===================================================================
# CLI entrypoint
# ===================================================================
def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description="VoiceLink Audio Processor — process one recording",
    )
    parser.add_argument(
        "--recording-id",
        required=True,
        help="UUID of the recording to process",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip external writes (GCS, Supabase); log intended actions",
    )
    args = parser.parse_args()

    if args.dry_run:
        os.environ["DRY_RUN"] = "true"

    cfg = ProcessorConfig.from_env()
    result = process_one(args.recording_id, cfg)
    log.info(f"Result: {result}")
    sys.exit(0 if result != "failed" else 1)


if __name__ == "__main__":
    main()
