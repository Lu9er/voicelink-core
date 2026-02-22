#!/usr/bin/env python3
"""
VoiceLink Sandbox Profiler — Process 10 recordings for decision-grade metrics.

Reads recording IDs from --ids-file (default: sandbox/ids.txt).
Downloads from GCS, normalizes, runs Silero VAD, generates clips,
encodes MP3 copies for size measurement.

Output: ~/Desktop/voicelink_sandbox_clips/<recording_id>/clip_###.wav
        ~/Desktop/voicelink_sandbox_clips/<recording_id>/clip_###.mp3
        ~/Desktop/voicelink_sandbox_clips/<recording_id>/report.json

NO writes to Supabase. NO writes to GCS. Local output only.
"""

import argparse
import json
import logging
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from dotenv import load_dotenv
from google.cloud import storage as gcs_lib
from supabase import create_client

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
SAMPLE_RATE = 16000
MIN_CLIP_SEC = 3.0
MAX_CLIP_SEC = 15.0
GAP_MERGE_SEC = 0.300
PAD_SEC = 0.200
MP3_BITRATE = "64k"

OUTPUT_ROOT = Path.home() / "Desktop" / "voicelink_sandbox_clips"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("profiler")


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

def load_env():
    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY")
    bucket = os.getenv("GCS_BUCKET_NAME")
    missing = []
    if not url:
        missing.append("SUPABASE_URL")
    if not key:
        missing.append("SUPABASE_SERVICE_KEY")
    if not bucket:
        missing.append("GCS_BUCKET_NAME")
    if missing:
        log.error("Missing env vars: %s", ", ".join(missing))
        sys.exit(1)
    return url, key, bucket


def read_ids_file(path):
    p = Path(path)
    if not p.exists():
        log.error("IDs file not found: %s", p)
        sys.exit(1)
    ids = [line.strip() for line in p.read_text().splitlines() if line.strip()]
    if not ids:
        log.error("IDs file is empty: %s", p)
        sys.exit(1)
    log.info("Read %d IDs from %s", len(ids), p)
    return ids


# ---------------------------------------------------------------------------
# Supabase + GCS
# ---------------------------------------------------------------------------

def fetch_recordings(supabase_url, supabase_key, ids):
    sb = create_client(supabase_url, supabase_key)
    resp = sb.table("recordings").select("id, gcs_path").in_("id", ids).execute()
    rows = resp.data
    if not rows:
        log.warning("No recordings found in Supabase for given IDs.")
    else:
        log.info("Fetched %d recording(s) from Supabase.", len(rows))
    # Build lookup; preserve order from ids file
    by_id = {r["id"]: r for r in rows}
    return by_id


def download_from_gcs(bucket_name, gcs_path, dest_path):
    client = gcs_lib.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(gcs_path)
    blob.download_to_filename(dest_path)


# ---------------------------------------------------------------------------
# Audio processing
# ---------------------------------------------------------------------------

def normalize_audio(input_path, output_wav):
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-ar", str(SAMPLE_RATE), "-ac", "1", "-sample_fmt", "s16",
        str(output_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg: {result.stderr[:300]}")


def encode_mp3(wav_path, mp3_path):
    cmd = [
        "ffmpeg", "-y", "-i", str(wav_path),
        "-codec:a", "libmp3lame", "-b:a", MP3_BITRATE,
        str(mp3_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg mp3: {result.stderr[:300]}")


def load_silero_vad():
    """Load Silero VAD model. Prefer local cached repo to avoid network."""
    cache_dir = Path.home() / ".cache" / "torch" / "hub"
    local_repos = sorted(cache_dir.glob("snakers4_silero-vad*")) if cache_dir.exists() else []

    if local_repos:
        repo_dir = str(local_repos[-1])
        log.info("Using cached Silero VAD: %s", repo_dir)
        model, utils = torch.hub.load(
            repo_or_dir=repo_dir,
            model="silero_vad",
            source="local",
            onnx=False,
        )
    else:
        log.info("Downloading Silero VAD from GitHub...")
        model, utils = torch.hub.load(
            repo_or_dir="snakers4/silero-vad",
            model="silero_vad",
            force_reload=False,
            onnx=False,
        )
    return model, utils[0]


def run_vad(model, get_ts, wav_path):
    audio, sr = sf.read(wav_path, dtype="float32")
    if sr != SAMPLE_RATE:
        raise ValueError(f"Expected {SAMPLE_RATE}Hz, got {sr}Hz")
    tensor = torch.from_numpy(audio)
    stamps = get_ts(tensor, model, sampling_rate=SAMPLE_RATE)
    segments = [(s["start"], s["end"]) for s in stamps]
    return segments, audio


def merge_segments(segments, gap_samples):
    if not segments:
        return []
    merged = [list(segments[0])]
    for start, end in segments[1:]:
        if start - merged[-1][1] < gap_samples:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return [tuple(s) for s in merged]


def extract_clips(audio, segments, total_samples):
    pad = int(PAD_SEC * SAMPLE_RATE)
    min_s = int(MIN_CLIP_SEC * SAMPLE_RATE)
    max_s = int(MAX_CLIP_SEC * SAMPLE_RATE)
    clips = []
    for seg_start, seg_end in segments:
        ps = max(0, seg_start - pad)
        pe = min(total_samples, seg_end + pad)
        length = pe - ps
        if length < min_s:
            continue
        if length <= max_s:
            clips.append(audio[ps:pe])
        else:
            pos = ps
            while pos < pe:
                chunk_end = min(pos + max_s, pe)
                chunk = audio[pos:chunk_end]
                if len(chunk) >= min_s:
                    clips.append(chunk)
                pos = chunk_end
    return clips


# ---------------------------------------------------------------------------
# Per-recording processing
# ---------------------------------------------------------------------------

def process_one(rec_id, gcs_path, bucket_name, vad_model, get_ts):
    t0 = time.time()

    out_dir = OUTPUT_ROOT / str(rec_id)
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    with tempfile.TemporaryDirectory(prefix="vl_prof_") as tmpdir:
        tmpdir = Path(tmpdir)
        ext = Path(gcs_path).suffix or ".mp3"
        raw_path = tmpdir / f"raw{ext}"
        wav_path = tmpdir / "normalized.wav"

        # Download
        try:
            download_from_gcs(bucket_name, gcs_path, str(raw_path))
        except Exception as e:
            runtime = time.time() - t0
            print(f"[FAIL_DOWNLOAD] {rec_id} — {e}")
            return {"id": rec_id, "status": "FAIL_DOWNLOAD", "error": str(e)}

        # Normalize
        try:
            normalize_audio(raw_path, wav_path)
        except Exception as e:
            runtime = time.time() - t0
            print(f"[FAIL_FFMPEG] {rec_id} — {e}")
            return {"id": rec_id, "status": "FAIL_FFMPEG", "error": str(e)}

        # VAD
        try:
            segments, audio = run_vad(vad_model, get_ts, str(wav_path))
        except Exception as e:
            runtime = time.time() - t0
            print(f"[FAIL_VAD] {rec_id} — {e}")
            return {"id": rec_id, "status": "FAIL_VAD", "error": str(e)}

    total_samples = len(audio)
    input_seconds = total_samples / SAMPLE_RATE

    # Merge + extract
    gap_samples = int(GAP_MERGE_SEC * SAMPLE_RATE)
    merged = merge_segments(segments, gap_samples)
    clips = extract_clips(audio, merged, total_samples)

    if not clips:
        runtime = time.time() - t0
        report = {
            "input_seconds": round(input_seconds, 2),
            "speech_seconds_kept": 0.0,
            "clips_saved": 0,
            "pct_clips_le_15s": 100.0,
            "mp3_size_bytes_min": 0,
            "mp3_size_bytes_median": 0,
            "mp3_size_bytes_max": 0,
            "runtime_seconds": round(runtime, 2),
        }
        (out_dir / "report.json").write_text(json.dumps(report, indent=2))
        print(f"[NO_SPEECH] {rec_id} — {input_seconds:.1f}s input, 0 clips")
        return {"id": rec_id, "status": "NO_SPEECH", "report": report}

    # Save WAV clips + encode MP3 copies
    mp3_sizes = []
    for i, clip in enumerate(clips):
        wav_out = out_dir / f"clip_{i+1:03d}.wav"
        mp3_out = out_dir / f"clip_{i+1:03d}.mp3"
        sf.write(str(wav_out), clip, SAMPLE_RATE, subtype="PCM_16")
        try:
            encode_mp3(wav_out, mp3_out)
            mp3_sizes.append(mp3_out.stat().st_size)
        except Exception:
            mp3_sizes.append(0)

    speech_seconds = sum(len(c) for c in clips) / SAMPLE_RATE
    clip_durations = [len(c) / SAMPLE_RATE for c in clips]
    pct_le_15 = 100.0 * sum(1 for d in clip_durations if d <= 15.0) / len(clips)

    runtime = time.time() - t0
    report = {
        "input_seconds": round(input_seconds, 2),
        "speech_seconds_kept": round(speech_seconds, 2),
        "clips_saved": len(clips),
        "pct_clips_le_15s": round(pct_le_15, 1),
        "mp3_size_bytes_min": min(mp3_sizes) if mp3_sizes else 0,
        "mp3_size_bytes_median": int(statistics.median(mp3_sizes)) if mp3_sizes else 0,
        "mp3_size_bytes_max": max(mp3_sizes) if mp3_sizes else 0,
        "runtime_seconds": round(runtime, 2),
    }
    (out_dir / "report.json").write_text(json.dumps(report, indent=2))

    print(
        f"[OK] {rec_id} — {len(clips)} clips, "
        f"{speech_seconds:.1f}s speech from {input_seconds:.1f}s input, "
        f"MP3 median {report['mp3_size_bytes_median']}B, "
        f"{runtime:.1f}s"
    )
    return {"id": rec_id, "status": "OK", "report": report}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="VoiceLink Sandbox Profiler")
    parser.add_argument(
        "--ids-file",
        type=str,
        default="sandbox/ids.txt",
        help="Path to file with one recording ID per line (default: sandbox/ids.txt)",
    )
    args = parser.parse_args()

    supabase_url, supabase_key, bucket_name = load_env()
    ids = read_ids_file(args.ids_file)

    by_id = fetch_recordings(supabase_url, supabase_key, ids)

    log.info("Loading Silero VAD model...")
    vad_model, get_ts = load_silero_vad()
    log.info("VAD model loaded.")

    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    results = []
    for rec_id in ids:
        if rec_id not in by_id:
            print(f"[FAIL_DOWNLOAD] {rec_id} — not found in Supabase")
            results.append({"id": rec_id, "status": "FAIL_DOWNLOAD", "error": "not in DB"})
            continue
        rec = by_id[rec_id]
        r = process_one(rec_id, rec["gcs_path"], bucket_name, vad_model, get_ts)
        results.append(r)

    # Summary
    print("\n" + "=" * 70)
    print("SANDBOX PROFILER SUMMARY")
    print("=" * 70)
    ok = [r for r in results if r["status"] == "OK"]
    no_speech = [r for r in results if r["status"] == "NO_SPEECH"]
    failed = [r for r in results if r["status"].startswith("FAIL")]
    print(f"  Total:      {len(results)}")
    print(f"  OK:         {len(ok)}")
    print(f"  NO_SPEECH:  {len(no_speech)}")
    print(f"  FAILED:     {len(failed)}")
    if ok:
        all_clips = sum(r["report"]["clips_saved"] for r in ok)
        all_speech = sum(r["report"]["speech_seconds_kept"] for r in ok)
        all_input = sum(r["report"]["input_seconds"] for r in ok)
        median_mp3 = statistics.median(
            r["report"]["mp3_size_bytes_median"] for r in ok
        )
        print(f"  Total clips:     {all_clips}")
        print(f"  Total speech:    {all_speech:.1f}s from {all_input:.1f}s input")
        print(f"  Median MP3 size: {int(median_mp3)} bytes")
    print(f"\n  Output: {OUTPUT_ROOT}")
    print("=" * 70)


if __name__ == "__main__":
    main()
