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

---

## Developer Validation Tools

Minimal tools for validating the audio processing pipeline locally
and testing Common Voice Public API v0.2.0 integration.

### Creating Common Voice API Credentials

1. Go to <https://commonvoice.mozilla.org/?feature=papi-credentials>
   (the `?feature=papi-credentials` feature flag enables the credentials UI)
2. Log in to your Mozilla / Common Voice account
3. Navigate to your **profile settings**
4. Find the **API** tab (visible only with the feature flag active)
5. Click **Create Credentials** to generate a `clientId` / `clientSecret` pair
6. Copy both values into your `.env` as `CV_CLIENT_ID` and `CV_CLIENT_SECRET`

> **Important**: Keep your `clientSecret` private. Never commit `.env` to version control.

---

### Sandbox Profiler (`sandbox/sandbox_profile_10.py`)

Processes recordings from GCS through the full pipeline and produces
decision-grade metrics: clip counts, speech ratios, MP3 sizes.

Pipeline: GCS download → ffmpeg 16kHz mono → Silero VAD → merge gaps
→ pad → extract 3–15s clips → WAV + MP3 export → report.json

#### Setup: Add recording IDs

Copy the example file and add real recording IDs (one per line):

```bash
cp sandbox/ids.example.txt sandbox/ids.txt
```

IDs must match the `id` column in the Supabase `recordings` table.

#### Run

```bash
source .venv/bin/activate
python sandbox/sandbox_profile_10.py --ids-file sandbox/ids.txt
```

#### Expected console output

```
10:00:01 Read 10 IDs from sandbox/ids.txt
10:00:02 Fetched 10 recording(s) from Supabase.
10:00:02 Loading Silero VAD model...
10:00:04 VAD model loaded.
[OK] abc-123 — 5 clips, 32.4s speech from 180.2s input, MP3 median 4820B, 3.1s
[NO_SPEECH] ghi-789 — 90.3s input, 0 clips
...

======================================================================
SANDBOX PROFILER SUMMARY
======================================================================
  Total:      10
  OK:         8
  NO_SPEECH:  1
  FAILED:     1
  Total clips:     42
  Total speech:    215.3s from 1520.0s input
  Median MP3 size: 4500 bytes

  Output: ~/Desktop/voicelink_sandbox_clips
======================================================================
```

#### Console prefix meanings

| Prefix | Meaning |
|--------|---------|
| `[OK]` | Clips generated successfully |
| `[NO_SPEECH]` | VAD found no usable speech segments |
| `[FAIL_DOWNLOAD]` | GCS download failed (missing blob or auth) |
| `[FAIL_FFMPEG]` | ffmpeg normalization failed (corrupt file) |
| `[FAIL_VAD]` | Silero VAD threw an error |

#### Output structure

```
~/Desktop/voicelink_sandbox_clips/
  <recording_id>/
    clip_001.wav    # 16kHz mono PCM, 3–15 seconds
    clip_001.mp3    # 64kbps MP3 (for size measurement)
    report.json
```

#### What this script does NOT do

- Does not modify Supabase (read-only queries only)
- Does not write to GCS
- Does not run Whisper or any transcription
- Does not call Common Voice, OpenAI, or Twilio APIs

---

### CV API Access Validator (`publisher/cv_api_validate.py`)

Validates Common Voice Public API v0.2.0 credentials without uploading audio.

Steps performed:
1. `POST /auth/token` — acquire JWT (never prints the token)
2. `GET /datasets/codes?service=audio&resource=scripted` — prints dataset code count
3. `GET /text/sentences?datasetCode=<code>` — probes multiple codes until one succeeds

#### Run

```bash
source .venv/bin/activate
python publisher/cv_api_validate.py
```

#### What "pass" looks like

All three `[PASS]` lines must appear:

```
[PASS] token acquired
[PASS] dataset codes returned: <N>
[PASS] sentence fetch OK (datasetCode=<code>, <N> returned)
```

If any step fails, the script exits with an error message and non-zero status.

#### What this script does NOT do

- Does not attempt `POST /audio` (radio clips are spontaneous, not scripted)
- Does not write to any database
- Does not print tokens or secrets
- Does not upload any audio files

---

## Troubleshooting

**`ffmpeg: command not found`**
Install ffmpeg: `brew install ffmpeg` (macOS) or `sudo apt-get install ffmpeg` (Linux)

**`google.auth.exceptions.DefaultCredentialsError`**
Run: `gcloud auth application-default login`

**Silero VAD download hangs**
The model is downloaded from GitHub on first run (~3MB). Ensure internet access.
After first run, cached at `~/.cache/torch/hub/snakers4_silero-vad_master/`.

**No clips generated for a recording**
Check `report.json` — `speech_seconds_kept: 0` confirms no speech was detected.

**CV API validator says "Token request failed (401)"**
Verify your `CV_CLIENT_ID` and `CV_CLIENT_SECRET` in `.env`.
Regenerate credentials at `https://commonvoice.mozilla.org/?feature=papi-credentials`.

**CV API validator says "Dataset codes failed on all paths"**
The `service=audio&resource=scripted` parameters are co-dependent.
Both must be present. This is per the v0.2.0 spec.
