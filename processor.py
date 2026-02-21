#!/usr/bin/env python3
"""
Module 3: The Audio Processor

Polls Supabase for recordings with status='raw_uploaded', then for each:

  1. Downloads raw audio from GCS.
  2. Probes source metadata (sample_rate, codec, channels) via ffprobe.
  3. Tags source_quality (e.g. 'telephony_8k' for 8 kHz Twilio audio).
  4. Normalizes to 16 kHz mono PCM WAV via ffmpeg (upsamples 8 kHz sources).
  5. Runs inaSpeechSegmenter — rejects if music > 40 %.
  6. Runs silero-vad — chunks speech into 3–10 s segments.
  7. Runs Whisper API for transcription of each segment.
  8. Uploads clean clips to GCS and inserts rows into the clips table.
  9. Marks the recording as 'processed'.

Source-agnostic: works identically on archive MP3s and live Twilio WAVs
because both arrive as status='raw_uploaded' with a gcs_path.

Prerequisites:
    - Run migrations/002_processor_columns.sql in Supabase first.
    - ffmpeg + ffprobe must be on PATH.
    - OPENAI_API_KEY must be set for Whisper transcription.

Usage:
    python processor.py                   # continuous polling loop
    python processor.py --once            # process one batch then exit
    python processor.py --batch-size 5    # adjust batch size
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
import time

import torch
from dotenv import load_dotenv
from google.cloud import storage
from inaSpeechSegmenter import Segmenter
from openai import OpenAI
from supabase import create_client

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("audio_processor")

# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"],
)
gcs_client = storage.Client()
bucket = gcs_client.bucket(os.environ["GCS_BUCKET_NAME"])
whisper = OpenAI()  # uses OPENAI_API_KEY

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
CANONICAL_SR = 16_000          # target sample rate for all processing
MUSIC_THRESHOLD = 0.40         # reject if music exceeds 40 %
MIN_CLIP_DURATION = 3.0        # seconds
MAX_CLIP_DURATION = 10.0       # seconds
VAD_MERGE_GAP = 0.5            # merge speech chunks closer than this (s)
DEFAULT_BATCH_SIZE = 10
DEFAULT_POLL_INTERVAL = 30     # seconds


# ===================================================================
# 1. ML model loading (called once at startup)
# ===================================================================
def load_models():
    log.info("Loading silero-vad model...")
    vad_model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        trust_repo=True,
    )
    get_speech_ts = utils[0]   # get_speech_timestamps
    read_audio = utils[2]      # torchaudio-based reader

    log.info("Loading inaSpeechSegmenter...")
    music_seg = Segmenter()

    log.info("All models loaded.")
    return vad_model, get_speech_ts, read_audio, music_seg


# ===================================================================
# 2. Source metadata probing
# ===================================================================
def probe_source_metadata(filepath: str) -> dict:
    """Run ffprobe and return sample_rate, codec, and channel count."""
    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet",
            "-print_format", "json",
            "-show_streams", "-show_format",
            filepath,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")

    data = json.loads(result.stdout)
    audio_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
        None,
    )
    if audio_stream is None:
        raise RuntimeError("No audio stream found in file")

    return {
        "source_sample_rate": int(audio_stream["sample_rate"]),
        "source_codec": audio_stream["codec_name"],
        "source_channels": int(audio_stream["channels"]),
    }


def classify_source_quality(sample_rate: int) -> str:
    """Map source sample rate to a human-readable quality tag."""
    if sample_rate <= 8_000:
        return "telephony_8k"
    if sample_rate <= 16_000:
        return "wideband_16k"
    if sample_rate <= 24_000:
        return "broadcast_24k"
    return "broadcast_hd"


# ===================================================================
# 3. FFmpeg helpers
# ===================================================================
def normalize_audio(input_path: str, output_path: str) -> None:
    """Convert any audio to the canonical 16 kHz mono s16 PCM WAV."""
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", input_path,
            "-ar", str(CANONICAL_SR),
            "-ac", "1",
            "-sample_fmt", "s16",
            "-f", "wav",
            output_path,
        ],
        check=True,
        capture_output=True,
    )


def extract_clip(input_path: str, output_path: str, start: float, end: float) -> None:
    """Extract a time segment from a normalized WAV file.

    Uses -ss after -i for sample-accurate seeking on PCM input.
    """
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", input_path,
            "-ss", str(start),
            "-to", str(end),
            "-f", "wav",
            output_path,
        ],
        check=True,
        capture_output=True,
    )


# ===================================================================
# 4. Music detection
# ===================================================================
def compute_music_ratio(music_seg: Segmenter, filepath: str) -> float:
    """Return the fraction of audio classified as music by inaSpeechSegmenter."""
    segments = music_seg(filepath)
    music_dur = sum(end - start for label, start, end in segments if label == "music")
    total_dur = sum(end - start for _, start, end in segments)
    return music_dur / total_dur if total_dur > 0 else 0.0


# ===================================================================
# 5. VAD segmentation + merge / split
# ===================================================================
def get_speech_segments(
    vad_model,
    get_speech_ts,
    read_audio_fn,
    filepath: str,
) -> list[tuple[float, float]]:
    """Run silero-vad then merge/split to produce 3–10 s clip boundaries."""
    wav = read_audio_fn(filepath, sampling_rate=CANONICAL_SR)
    raw_ts = get_speech_ts(wav, vad_model, sampling_rate=CANONICAL_SR)

    if not raw_ts:
        return []

    # Convert sample offsets → seconds
    segs = [(t["start"] / CANONICAL_SR, t["end"] / CANONICAL_SR) for t in raw_ts]

    # --- Merge segments separated by tiny gaps ---
    merged: list[tuple[float, float]] = [segs[0]]
    for start, end in segs[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end <= VAD_MERGE_GAP:
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))

    # --- Split long segments, drop short ones ---
    final: list[tuple[float, float]] = []
    for start, end in merged:
        dur = end - start
        if dur < MIN_CLIP_DURATION:
            continue
        if dur <= MAX_CLIP_DURATION:
            final.append((round(start, 3), round(end, 3)))
        else:
            # Chop into max-length pieces; keep only those ≥ min length
            t = start
            while t + MIN_CLIP_DURATION <= end:
                chunk_end = min(t + MAX_CLIP_DURATION, end)
                if chunk_end - t >= MIN_CLIP_DURATION:
                    final.append((round(t, 3), round(chunk_end, 3)))
                t = chunk_end

    return final


# ===================================================================
# 6. Whisper transcription
# ===================================================================
def transcribe_clip(clip_path: str) -> str:
    """Send a short WAV clip to the OpenAI Whisper API and return text."""
    with open(clip_path, "rb") as f:
        resp = whisper.audio.transcriptions.create(model="whisper-1", file=f)
    return resp.text


# ===================================================================
# 7. Main per-recording orchestrator
# ===================================================================
def process_recording(
    recording: dict,
    vad_model,
    get_speech_ts,
    read_audio_fn,
    music_seg: Segmenter,
) -> None:
    recording_id = recording["id"]
    gcs_path = recording["gcs_path"]

    log.info(f"=== Recording {recording_id} ({gcs_path}) ===")

    # --- Atomic claim: raw_uploaded → processing ---
    lock = (
        supabase.table("recordings")
        .update({"status": "processing"})
        .eq("id", recording_id)
        .eq("status", "raw_uploaded")
        .execute()
    )
    if not lock.data:
        log.info(f"  Skipping — already claimed by another worker")
        return

    with tempfile.TemporaryDirectory(prefix="voicelink_") as work_dir:
        raw_path = os.path.join(work_dir, "raw_audio")
        norm_path = os.path.join(work_dir, "normalized.wav")
        clips_dir = os.path.join(work_dir, "clips")
        os.makedirs(clips_dir)

        try:
            # ---- Download from GCS ----
            blob = bucket.blob(gcs_path)
            blob.download_to_filename(raw_path)
            log.info(f"  Downloaded {gcs_path}")

            # ---- Probe source metadata ----
            meta = probe_source_metadata(raw_path)
            source_quality = classify_source_quality(meta["source_sample_rate"])
            log.info(
                f"  Source: {meta['source_sample_rate']} Hz "
                f"{meta['source_codec']} {meta['source_channels']}ch "
                f"-> {source_quality}"
            )
            supabase.table("recordings").update({
                "source_sample_rate": meta["source_sample_rate"],
                "source_codec": meta["source_codec"],
                "source_channels": meta["source_channels"],
                "source_quality": source_quality,
            }).eq("id", recording_id).execute()

            # ---- Normalize to 16 kHz mono WAV ----
            normalize_audio(raw_path, norm_path)
            log.info(f"  Normalized to {CANONICAL_SR} Hz mono WAV")

            # ---- Music detection ----
            music_ratio = compute_music_ratio(music_seg, norm_path)
            log.info(f"  Music ratio: {music_ratio:.1%}")

            supabase.table("recordings").update({
                "music_ratio": round(music_ratio, 4),
            }).eq("id", recording_id).execute()

            if music_ratio > MUSIC_THRESHOLD:
                supabase.table("recordings").update({
                    "status": "rejected",
                    "failure_reason": (
                        f"Music ratio {music_ratio:.1%} exceeds "
                        f"{MUSIC_THRESHOLD:.0%} threshold"
                    ),
                }).eq("id", recording_id).execute()
                log.warning(f"  REJECTED — music ratio too high")
                return

            # ---- VAD segmentation ----
            segments = get_speech_segments(
                vad_model, get_speech_ts, read_audio_fn, norm_path
            )
            log.info(f"  VAD found {len(segments)} speech segment(s)")

            if not segments:
                supabase.table("recordings").update({
                    "status": "rejected",
                    "failure_reason": "No speech segments in 3-10 s range",
                }).eq("id", recording_id).execute()
                log.warning(f"  REJECTED — no valid speech segments")
                return

            # ---- Extract, upload, and transcribe each clip ----
            clip_rows = []
            for i, (start, end) in enumerate(segments):
                clip_path = os.path.join(clips_dir, f"{i:04d}.wav")
                extract_clip(norm_path, clip_path, start, end)

                clip_gcs = f"processed_clips/{recording_id}/{i:04d}.wav"
                bucket.blob(clip_gcs).upload_from_filename(clip_path)

                transcript = transcribe_clip(clip_path)

                clip_rows.append({
                    "recording_id": recording_id,
                    "clip_index": i,
                    "start_time": start,
                    "end_time": end,
                    "duration_seconds": round(end - start, 3),
                    "gcs_path": clip_gcs,
                    "transcript": transcript,
                    "source_quality": source_quality,
                })

                preview = (transcript[:60] + "...") if len(transcript) > 60 else transcript
                log.info(
                    f"  Clip {i}: {start:.1f}–{end:.1f}s "
                    f"({end - start:.1f}s) \"{preview}\""
                )

            # ---- Batch-insert clips ----
            supabase.table("clips").insert(clip_rows).execute()

            # ---- Mark recording done ----
            supabase.table("recordings").update({
                "status": "processed",
                "clip_count": len(clip_rows),
            }).eq("id", recording_id).execute()

            log.info(
                f"  DONE — {len(clip_rows)} clip(s) extracted and transcribed"
            )

        except Exception as e:
            log.error(f"  FAIL {recording_id}: {e}")
            try:
                supabase.table("recordings").update({
                    "status": "failed",
                    "failure_reason": str(e)[:500],
                }).eq("id", recording_id).execute()
            except Exception as db_err:
                log.error(f"  Could not write failure to DB: {db_err}")


# ===================================================================
# 8. Polling loop
# ===================================================================
def fetch_pending(batch_size: int) -> list[dict]:
    resp = (
        supabase.table("recordings")
        .select("id, gcs_path, source_type")
        .eq("status", "raw_uploaded")
        .limit(batch_size)
        .execute()
    )
    return resp.data


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VoiceLink Audio Processor — Module 3"
    )
    parser.add_argument(
        "--once", action="store_true",
        help="Process one batch of pending recordings then exit",
    )
    parser.add_argument(
        "--batch-size", type=int, default=DEFAULT_BATCH_SIZE,
        help=f"Recordings per polling cycle (default: {DEFAULT_BATCH_SIZE})",
    )
    parser.add_argument(
        "--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL,
        help=f"Seconds between polls (default: {DEFAULT_POLL_INTERVAL})",
    )
    args = parser.parse_args()

    # Load heavy ML models once
    vad_model, get_speech_ts, read_audio_fn, music_seg = load_models()

    while True:
        recordings = fetch_pending(args.batch_size)

        if recordings:
            log.info(f"Found {len(recordings)} pending recording(s)")
            for rec in recordings:
                process_recording(
                    rec, vad_model, get_speech_ts, read_audio_fn, music_seg
                )
        else:
            log.info("No pending recordings")

        if args.once:
            break

        log.info(f"Sleeping {args.poll_interval}s...")
        time.sleep(args.poll_interval)


if __name__ == "__main__":
    main()
