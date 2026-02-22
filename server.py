"""
Module 2: The Live Ingester — FastAPI server for Twilio webhooks.

Endpoints:
    POST /api/twilio/webhook
        Receives Twilio recording-status callbacks. Verifies signature,
        upserts metadata with status='download_queued', enqueues a Cloud
        Task, and returns 200 OK immediately. Zero audio I/O in this path.

    POST /api/worker/process-recording
        Called by Cloud Tasks (or BackgroundTasks locally). Downloads audio
        from Twilio via streaming, uploads to GCS, updates Supabase to
        status='raw_uploaded'.

Usage:
    uvicorn server:app --host 0.0.0.0 --port 8080

Environment variables (via .env):
    SUPABASE_URL                   - Supabase project URL
    SUPABASE_SERVICE_KEY           - Supabase service role key
    GCS_BUCKET_NAME                - GCS bucket name
    TWILIO_AUTH_TOKEN              - Twilio auth token (signature verification)
    TWILIO_ACCOUNT_SID             - Twilio account SID (recording download)
    GOOGLE_APPLICATION_CREDENTIALS - Path to GCP service account JSON key

    # Cloud Tasks (production) — omit all three for local BackgroundTasks fallback
    CLOUD_TASKS_QUEUE_PATH         - e.g. projects/my-proj/locations/us-central1/queues/voicelink
    WORKER_BASE_URL                - e.g. https://voicelink-xxxxx.run.app
    CLOUD_TASKS_SERVICE_ACCOUNT    - e.g. worker@my-proj.iam.gserviceaccount.com
"""

import json
import logging
import os
import subprocess
import tempfile
import time

import httpx
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from google.cloud import storage
from pydantic import BaseModel
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

# Cloud Tasks config (optional — falls back to BackgroundTasks when unset)
CLOUD_TASKS_QUEUE_PATH = os.environ.get("CLOUD_TASKS_QUEUE_PATH")
WORKER_BASE_URL = os.environ.get("WORKER_BASE_URL", "")
CLOUD_TASKS_SERVICE_ACCOUNT = os.environ.get("CLOUD_TASKS_SERVICE_ACCOUNT", "")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="VoiceLink Live Ingester")


# ---------------------------------------------------------------------------
# Patch 4 — Normalise RecordingUrl so we never get ".wav.wav"
# ---------------------------------------------------------------------------
def _normalize_recording_url(url: str) -> str:
    """Ensure the URL ends with exactly one .wav extension."""
    return url if url.endswith(".wav") else f"{url}.wav"


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------
@app.post("/api/twilio/webhook")
async def twilio_webhook(request: Request, background_tasks: BackgroundTasks):
    """Receive a Twilio recording-status callback.

    1. Verify the Twilio request signature.
    2. Upsert a row with status='download_queued'.
    3. Enqueue a Cloud Task (or BackgroundTask fallback).
    4. Return 200 immediately.
    """
    # --- Parse form body ----------------------------------------------------
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

    recording_url = _normalize_recording_url(recording_url)

    log.info(f"Webhook received: CallSid={call_sid} RecordingSid={recording_sid}")

    # --- Upsert metadata (fast — no audio I/O) ------------------------------
    # Patch 2: status starts as 'download_queued' (not 'webhook_received')
    # Patch 3: store Twilio identifiers explicitly for audit/debug
    row = {
        "external_call_id": recording_sid,
        "source_type": "twilio",
        "source_id": call_sid,
        "twilio_call_sid": call_sid,
        "twilio_recording_sid": recording_sid,
        "status": "download_queued",
        "raw_url": recording_url,
    }
    resp = (
        supabase.table("recordings")
        .upsert(row, on_conflict="external_call_id")
        .execute()
    )
    recording_id = resp.data[0]["id"]

    # --- Enqueue processing -------------------------------------------------
    # Patch 1: prefer Cloud Tasks for durable execution on Cloud Run.
    #          Falls back to in-process BackgroundTasks for local dev only.
    if CLOUD_TASKS_QUEUE_PATH:
        _enqueue_cloud_task(recording_id, recording_sid, recording_url)
    else:
        log.warning(
            "CLOUD_TASKS_QUEUE_PATH not set — using in-process "
            "BackgroundTasks (NOT durable; local dev only)"
        )
        background_tasks.add_task(
            do_process_recording, recording_id, recording_sid, recording_url
        )

    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Cloud Tasks enqueue (Patch 1)
# ---------------------------------------------------------------------------
def _enqueue_cloud_task(
    recording_id: str, recording_sid: str, recording_url: str
) -> None:
    """Create a Cloud Task targeting the worker endpoint.

    Uses the RecordingSid in the task name for deduplication — if Twilio
    retries the webhook, Cloud Tasks rejects the duplicate task.
    """
    from google.api_core.exceptions import AlreadyExists
    from google.cloud import tasks_v2

    client = tasks_v2.CloudTasksClient()
    task = {
        "name": f"{CLOUD_TASKS_QUEUE_PATH}/tasks/dl-{recording_sid}",
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{WORKER_BASE_URL}/api/worker/process-recording",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "recording_id": recording_id,
                "recording_sid": recording_sid,
                "recording_url": recording_url,
            }).encode(),
            "oidc_token": {
                "service_account_email": CLOUD_TASKS_SERVICE_ACCOUNT,
            },
        },
    }
    try:
        client.create_task(parent=CLOUD_TASKS_QUEUE_PATH, task=task)
        log.info(f"Cloud Task enqueued for {recording_sid}")
    except AlreadyExists:
        log.info(
            f"Cloud Task already exists for {recording_sid} — "
            "skipping (idempotent)"
        )


# ---------------------------------------------------------------------------
# Worker endpoint (called by Cloud Tasks, or by BackgroundTasks locally)
# ---------------------------------------------------------------------------
class ProcessRecordingPayload(BaseModel):
    recording_id: str
    recording_sid: str
    recording_url: str


@app.post("/api/worker/process-recording")
def process_recording_endpoint(payload: ProcessRecordingPayload):
    """Worker endpoint invoked by Cloud Tasks."""
    do_process_recording(
        payload.recording_id, payload.recording_sid, payload.recording_url
    )
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Core processing logic
# ---------------------------------------------------------------------------
def do_process_recording(
    recording_id: str, recording_sid: str, recording_url: str
) -> None:
    """Download audio from Twilio, upload to GCS, update Supabase.

    Patch 2: Atomic status lock prevents duplicate workers.
    Patch 5: Streams audio to a temp file (never holds full WAV in memory).
    Patch 6: Retry + backoff with separate connect / read timeouts.
    """
    log.info(f"Processing {recording_sid}")

    # --- Patch 2: Atomic lock — download_queued → downloading ---------------
    # If the row is NOT in 'download_queued', another worker already claimed
    # it (or it's already processed). Exit cleanly.
    lock_resp = (
        supabase.table("recordings")
        .update({"status": "downloading"})
        .eq("id", recording_id)
        .eq("status", "download_queued")
        .execute()
    )
    if not lock_resp.data:
        log.info(
            f"Skipping {recording_sid} — not in 'download_queued' state "
            "(duplicate worker or already processed)"
        )
        return

    tmp_path: str | None = None
    try:
        # 1. Stream-download from Twilio → temp file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
        _download_with_retry(
            url=recording_url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            dest_path=tmp_path,
        )

        # 2. Duration via ffprobe
        duration = _get_duration_seconds(tmp_path)

        # 3. Upload to GCS
        gcs_path = f"raw_live/{recording_sid}.wav"
        blob = bucket.blob(gcs_path)
        blob.upload_from_filename(tmp_path)

        # 4. Update Supabase → raw_uploaded
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
            log.error(
                f"Could not write failure to DB for {recording_sid}: {db_err}"
            )

    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
DOWNLOAD_MAX_RETRIES = 2
DOWNLOAD_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0)


def _download_with_retry(
    url: str, auth: tuple[str, str], dest_path: str
) -> None:
    """Stream-download a URL to disk with retry + exponential backoff.

    Patch 5: Streams in 64 KB chunks — never buffers full audio in memory.
    Patch 6: connect=10s, read=120s, up to 2 retries (waits 2s then 4s).
    """
    for attempt in range(DOWNLOAD_MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=DOWNLOAD_TIMEOUT) as client:
                with client.stream(
                    "GET", url, auth=auth, follow_redirects=True
                ) as resp:
                    resp.raise_for_status()
                    with open(dest_path, "wb") as f:
                        for chunk in resp.iter_bytes(chunk_size=65_536):
                            f.write(chunk)
            return  # success
        except (httpx.TransportError, httpx.HTTPStatusError) as e:
            if attempt < DOWNLOAD_MAX_RETRIES:
                wait = 2 ** (attempt + 1)  # 2s, 4s
                log.warning(
                    f"Download attempt {attempt + 1} failed: {e}. "
                    f"Retrying in {wait}s..."
                )
                time.sleep(wait)
            else:
                raise


# ---------------------------------------------------------------------------
# Module 3 — process-audio endpoint
# ---------------------------------------------------------------------------
class ProcessAudioPayload(BaseModel):
    recording_id: str


@app.post("/api/worker/process-audio")
def process_audio_endpoint(payload: ProcessAudioPayload):
    """Worker endpoint for Module 3 audio processing.

    Called by Cloud Tasks (or manually) after a recording reaches
    status='raw_uploaded'.  Delegates to worker.process_audio.process_one().
    """
    from worker.process_audio import process_one

    result = process_one(payload.recording_id)
    status = "error" if result == "failed" else "ok"
    return {
        "status": status,
        "recording_id": payload.recording_id,
        "result": result,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
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
