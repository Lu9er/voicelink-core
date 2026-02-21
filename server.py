"""
Module 2: The Live Ingester — FastAPI server for Twilio webhooks.

Endpoints:
    POST /api/twilio/webhook  — Receives Twilio recording status callbacks.
                                 Verifies signature, upserts metadata, returns
                                 200 OK immediately. Audio download happens in
                                 a background task.

Usage:
    uvicorn server:app --host 0.0.0.0 --port 8080

Environment variables (via .env):
    SUPABASE_URL             - Supabase project URL
    SUPABASE_SERVICE_KEY     - Supabase service role key
    GCS_BUCKET_NAME          - Google Cloud Storage bucket name
    TWILIO_AUTH_TOKEN        - Twilio auth token (for signature verification)
    TWILIO_ACCOUNT_SID       - Twilio account SID (for downloading recordings)
    GOOGLE_APPLICATION_CREDENTIALS - Path to GCP service account JSON key
"""

import json
import logging
import os
import subprocess
import tempfile

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from google.cloud import storage
from supabase import create_client
from twilio.request_validator import RequestValidator

load_dotenv()

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("live_ingester")

# ---------------------------------------------------------------------------
# Clients (initialised once at import time)
# ---------------------------------------------------------------------------
supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_SERVICE_KEY"],
)
gcs_client = storage.Client()
bucket = gcs_client.bucket(os.environ["GCS_BUCKET_NAME"])

TWILIO_AUTH_TOKEN = os.environ["TWILIO_AUTH_TOKEN"]
TWILIO_ACCOUNT_SID = os.environ["TWILIO_ACCOUNT_SID"]
twilio_validator = RequestValidator(TWILIO_AUTH_TOKEN)

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="VoiceLink Live Ingester")


@app.post("/api/twilio/webhook")
async def twilio_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive a Twilio recording status callback.

    1. Verify the Twilio request signature.
    2. Upsert a row with status='webhook_received'.
    3. Enqueue a background task to download + upload the audio.
    4. Return 200 immediately.
    """
    # --- Parse the form body ------------------------------------------------
    form_data = await request.form()
    params = dict(form_data)

    # --- Verify Twilio signature --------------------------------------------
    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    if not twilio_validator.validate(url, params, signature):
        log.warning("Invalid Twilio signature — rejecting request")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    # --- Extract fields -----------------------------------------------------
    call_sid = params.get("CallSid", "")
    recording_sid = params.get("RecordingSid", "")
    recording_url = params.get("RecordingUrl", "")

    if not recording_sid or not recording_url:
        log.warning(f"Missing RecordingSid or RecordingUrl: {params}")
        raise HTTPException(status_code=400, detail="Missing required fields")

    log.info(f"Webhook received: CallSid={call_sid} RecordingSid={recording_sid}")

    # --- Upsert metadata (fast — no audio download) -------------------------
    row = {
        "external_call_id": recording_sid,
        "source_type": "twilio",
        "source_id": call_sid,
        "status": "webhook_received",
        "raw_url": recording_url,
    }
    resp = (
        supabase.table("recordings")
        .upsert(row, on_conflict="external_call_id")
        .execute()
    )
    recording_id = resp.data[0]["id"]

    # --- Enqueue background work (Rule 2: never block the webhook) ----------
    background_tasks.add_task(process_recording, recording_id, recording_sid, recording_url)

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Background worker
# ---------------------------------------------------------------------------
async def process_recording(recording_id: str, recording_sid: str, recording_url: str) -> None:
    """Download audio from Twilio, upload to GCS, update Supabase.

    Runs as a FastAPI BackgroundTask — after the 200 has already been sent.
    On any failure, sets status='failed' with failure_reason.
    """
    log.info(f"Background: processing {recording_sid}")

    try:
        # 1. Download from Twilio (basic auth with AccountSid + AuthToken)
        download_url = f"{recording_url}.wav"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                download_url,
                auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
                follow_redirects=True,
                timeout=120.0,
            )
            resp.raise_for_status()
            audio_bytes = resp.content

        # 2. Write to a temp file so ffprobe can read it
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # 3. Extract duration via ffprobe
        duration = _get_duration_seconds(tmp_path)

        # 4. Upload to GCS
        gcs_path = f"raw_live/{recording_sid}.wav"
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(tmp_path)

        # 5. Update Supabase → status='raw_uploaded'
        supabase.table("recordings").update({
            "status": "raw_uploaded",
            "gcs_path": gcs_path,
            "duration_seconds": duration,
        }).eq("id", recording_id).execute()

        log.info(f"OK  {recording_sid} ({duration:.1f}s) -> {gcs_path}")

    except Exception as e:
        log.error(f"FAIL {recording_sid}: {e}")
        try:
            supabase.table("recordings").update({
                "status": "failed",
                "failure_reason": str(e)[:500],
            }).eq("id", recording_id).execute()
        except Exception as db_err:
            log.error(f"Could not write failure to DB for {recording_sid}: {db_err}")

    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except (OSError, UnboundLocalError):
            pass


def _get_duration_seconds(filepath: str) -> float:
    """Use ffprobe to extract the duration in seconds."""
    result = subprocess.run(
        [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_entries", "format=duration",
            filepath,
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr.strip()}")
    data = json.loads(result.stdout)
    return float(data["format"]["duration"])
