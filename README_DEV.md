# VoiceLink — Developer Guide

## Modules

| Module | File(s) | Purpose |
|--------|---------|---------|
| 1 — Archive Ingester | `ingest_archives.py` | Bulk-import MP3 archives to GCS + Supabase |
| 2 — Live Ingester | `server.py` | Twilio webhook → download → GCS → `raw_uploaded` |
| 3 — Audio Processor | `worker/process_audio.py` | VAD → clip → MP3 → upload → `processed` |

## Environment variables

### Required (all modules)

| Variable | Description |
|----------|-------------|
| `SUPABASE_URL` | Supabase project URL |
| `SUPABASE_SERVICE_KEY` | Supabase service-role key |
| `GCS_BUCKET_NAME` | GCS bucket for audio storage |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to GCP service-account JSON (optional on Cloud Run) |

### Module 2 only

| Variable | Description |
|----------|-------------|
| `TWILIO_ACCOUNT_SID` | Twilio account SID |
| `TWILIO_AUTH_TOKEN` | Twilio auth token |
| `CLOUD_TASKS_QUEUE_PATH` | Cloud Tasks queue (omit for local BackgroundTasks) |
| `WORKER_BASE_URL` | Public URL of this service (for Cloud Tasks callbacks) |
| `CLOUD_TASKS_SERVICE_ACCOUNT` | SA email for OIDC tokens on tasks |

### Module 3 tunables (all optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `CLIP_MP3_BITRATE_KBPS` | `64` | MP3 encoding bitrate |
| `CLIP_MIN_SECONDS` | `3` | Minimum clip duration |
| `CLIP_MAX_SECONDS` | `15` | Maximum clip duration |
| `VAD_MERGE_GAP_SECONDS` | `0.5` | Merge speech segments closer than this |
| `SPEECH_YIELD_GATE` | `0.01` | Reject recordings with < 1 % speech yield |
| `DRY_RUN` | `false` | Skip all external writes; log intended actions |

## Prerequisites

```bash
# System dependencies
sudo apt-get install ffmpeg   # provides ffmpeg + ffprobe

# Python dependencies
pip install -r requirements.txt
```

## Running locally

### Module 3 — process a single recording (dry-run, no creds)

```bash
DRY_RUN=true python -m worker.process_audio \
    --recording-id 00000000-0000-0000-0000-000000000000
```

### Module 3 — process with real credentials

```bash
# Ensure .env is populated (SUPABASE_URL, SUPABASE_SERVICE_KEY, GCS_BUCKET_NAME)
python -m worker.process_audio --recording-id <uuid>
```

### Module 3 — via the API endpoint

```bash
# Start the server
uvicorn server:app --host 0.0.0.0 --port 8080

# Trigger processing
curl -X POST http://localhost:8080/api/worker/process-audio \
    -H 'Content-Type: application/json' \
    -d '{"recording_id":"<uuid>"}'
```

### Expected output (successful processing)

```
12:00:01 [INFO] [abc-123] CLAIMED
12:00:02 [INFO] [abc-123] DOWNLOADED raw_live/RE123.wav
12:00:02 [INFO] [abc-123] PROBED codec=pcm_s16le sr=8000 ch=1 dur=180.5s
12:00:03 [INFO] [abc-123] NORMALIZED 16kHz mono WAV
12:00:06 [INFO] [abc-123] VAD_DONE 42 raw segment(s)
12:00:06 [INFO] [abc-123] CLIPS_BUILT count=18 speech=132.5s yield=73.4%
12:00:08 [INFO] [abc-123] UPLOADED 18 clip(s)
12:00:08 [INFO] [abc-123] DB_UPDATED processed
```

### Expected output (low-speech gated)

```
12:00:01 [INFO] [abc-456] CLAIMED
12:00:02 [INFO] [abc-456] DOWNLOADED raw_archives/sha256.mp3
12:00:02 [INFO] [abc-456] PROBED codec=mp3 sr=44100 ch=2 dur=240.0s
12:00:03 [INFO] [abc-456] NORMALIZED 16kHz mono WAV
12:00:05 [INFO] [abc-456] VAD_DONE 3 raw segment(s)
12:00:05 [INFO] [abc-456] CLIPS_BUILT count=0 speech=1.2s yield=0.5%
12:00:05 [INFO] [abc-456] GATED_LOW_SPEECH yield=0.5% < gate=1%
12:00:05 [INFO] [abc-456] DB_UPDATED processed_low_speech
```

## Database migrations

Run `migrations/002_processor_columns.sql` in Supabase SQL Editor before
starting Module 3.  The migration is idempotent (safe to re-run).

## Cloud Run deployment

### Recommended settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| Memory | >= 4 GiB | silero-vad + torch model in RAM |
| CPU | 1–2 | VAD is CPU-only; single recording at a time |
| Concurrency | 1 | Each request processes one full recording |
| Timeout | >= 1800 s | Long recordings may take minutes to clip |
| Min instances | 0 | Scale to zero when idle |

### Build and deploy

```bash
gcloud run deploy voicelink-worker \
    --source . \
    --memory 4Gi \
    --cpu 2 \
    --concurrency 1 \
    --timeout 1800 \
    --set-env-vars "SUPABASE_URL=$SUPABASE_URL,SUPABASE_SERVICE_KEY=$SUPABASE_SERVICE_KEY,GCS_BUCKET_NAME=$GCS_BUCKET_NAME"
```

### Triggering via Cloud Tasks

After Module 2 sets a recording to `raw_uploaded`, enqueue a Cloud Task
targeting:

```
POST https://<service-url>/api/worker/process-audio
Body: {"recording_id":"<uuid>"}
```

## Status machine

```
raw_uploaded ──→ processing ──→ processed
                      │              (clips uploaded)
                      │
                      ├──→ processed_low_speech
                      │       (yield < 1 %, no clips)
                      │
                      └──→ failed
                              (failure_reason written)
```
