# VoiceLink — Developer Guide

## Modules

| Module | File(s) | Purpose |
|--------|---------|---------|
| 1 — Archive Ingester | `ingest_archives.py` | Bulk-import MP3 archives to GCS + Supabase |
| 2 — Live Ingester | `server.py` | Twilio webhook -> download -> GCS -> `raw_uploaded` |
| 3 — Audio Processor | `worker/process_audio.py` | VAD -> clip -> MP3 -> upload -> `processed` |
| 4A — Analytics | `analytics/speech_hours.py` | Speech-hour metrics and ranked CSV |
| 4B — Transcription | `transcribe/transcribe_clips.py` | ASR on approved clips |
| 4C — Review Queue | `review/review_queue.py` | Approve / reject / edit clips |
| 4D — CV Submission | `publisher/cv_submit.py` | Submit clips to Common Voice API |

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
| `WORKER_BASE_URL` | Public URL of this service |
| `CLOUD_TASKS_SERVICE_ACCOUNT` | SA email for OIDC tokens on tasks |

### Module 3 tunables (all optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `CLIP_MP3_BITRATE_KBPS` | `64` | MP3 encoding bitrate |
| `CLIP_MIN_SECONDS` | `3` | Minimum clip duration |
| `CLIP_MAX_SECONDS` | `15` | Maximum clip duration |
| `VAD_MERGE_GAP_SECONDS` | `0.5` | Merge speech segments closer than this |
| `SPEECH_YIELD_GATE` | `0.01` | Gate recordings with < 1 % speech yield |
| `DRY_RUN` | `false` | Skip all external writes; log intended actions |

### Module 4 — Transcription

| Variable | Default | Description |
|----------|---------|-------------|
| `TRANSCRIBE_BACKEND` | `faster_whisper` | `faster_whisper` or `openai_whisper` |
| `WHISPER_MODEL_SIZE` | `base` | Model size for faster-whisper |
| `OPENAI_API_KEY` | — | Required only for openai_whisper backend |

### Module 4 — Common Voice submission

| Variable | Default | Description |
|----------|---------|-------------|
| `CV_API_BASE_URL` | `https://api.commonvoice.mozilla.org` | Common Voice API root |
| `CV_CLIENT_ID` | — | Same as cv_api_validate (see above) |
| `CV_CLIENT_SECRET` | — | Same as cv_api_validate (see above) |
| `CV_LANGUAGE` | `ate` | Target language code (Ateso) |
| `CV_RESOURCE_TYPE` | `spontaneous` | `scripted` or `spontaneous` |
| `CV_AUTH_ENDPOINT` | `/auth/token` | Override auth path |
| `CV_UPLOAD_ENDPOINT` | `/audio` | Override upload path |

## Prerequisites

```bash
# System dependencies
sudo apt-get install ffmpeg   # provides ffmpeg + ffprobe

# Python dependencies (core)
pip install -r requirements.txt

# Optional: ASR backend (install one)
pip install faster-whisper    # local CPU inference (default)
pip install openai            # OpenAI Whisper API
```

## Running Module 4

### 4A — Compute speech hours

```bash
# All processed recordings
python -m analytics.speech_hours

# Filtered
python -m analytics.speech_hours --min-speech-yield 0.10 --limit 50

# Export CSV
python -m analytics.speech_hours --csv report.csv
```

Expected output:
```
Recordings : 42
Total dur  : 18.50 h
Speech     : 12.34 h
Clips      : 1087
Avg yield  : 66.7%

                                  ID    Dur(s)   Speech    Yield  Clips
----------------------------------------------------------------------
abc12345-...                       1200.0     980.5   81.7%    85
def67890-...                        900.0     650.2   72.2%    62
```

### 4B — Transcribe clips

```bash
# Transcribe approved clips without transcripts (default)
python -m transcribe.transcribe_clips --limit 20

# Also include pending_review clips (draft-first workflow)
python -m transcribe.transcribe_clips --include-pending --limit 50

# Force overwrite existing transcripts
python -m transcribe.transcribe_clips --force --limit 10

# Use OpenAI backend
python -m transcribe.transcribe_clips --backend openai_whisper --limit 10

# Dry-run (no writes)
DRY_RUN=true python -m transcribe.transcribe_clips --limit 10
```

Expected output:
```
10:30:01 [INFO] Selected 20 clip(s) for transcription
10:30:02 [INFO] [OK] abc-001 4.5s backend=faster_whisper
10:30:03 [INFO] [OK] abc-002 7.2s backend=faster_whisper
10:30:03 [INFO] [SKIP] abc-003 already has transcript
10:30:04 [INFO] [FAIL] abc-004 empty transcript
10:30:04 [INFO] Done: {'ok': 18, 'skip': 1, 'fail': 1}
```

### 4C — Review queue

```bash
# List 20 pending clips
python -m review.review_queue list --limit 20

# List approved clips
python -m review.review_queue list --status approved --limit 10

# Approve a clip
python -m review.review_queue approve --clip-id <uuid>

# Reject a clip with reason
python -m review.review_queue reject --clip-id <uuid> --reason "background noise"

# Set or edit transcript
python -m review.review_queue set-transcript --clip-id <uuid> --text "Eyalama noi"
```

Review API endpoints (when server is running):

```bash
# List pending clips
curl http://localhost:8080/api/review/clips?limit=10

# Approve
curl -X POST http://localhost:8080/api/review/approve \
  -H 'Content-Type: application/json' \
  -d '{"clip_id":"<uuid>"}'

# Reject
curl -X POST http://localhost:8080/api/review/reject \
  -H 'Content-Type: application/json' \
  -d '{"clip_id":"<uuid>","reason":"too noisy"}'

# Set transcript
curl -X POST http://localhost:8080/api/review/set-transcript \
  -H 'Content-Type: application/json' \
  -d '{"clip_id":"<uuid>","text":"Eyalama noi"}'
```

### 4D — Common Voice submission (dry-run)

```bash
# Dry-run — logs what would happen
DRY_RUN=true python -m publisher.cv_submit --limit 5

# Real submission (requires CV_API_BASE_URL + auth vars)
python -m publisher.cv_submit --limit 10
```

Expected output:
```
10:40:01 [INFO] CV auth: loaded creds (token obtained)
10:40:01 [INFO] Selected 5 clip(s) for submission
10:40:02 [INFO] [OK] abc-001 submitted
10:40:03 [INFO] [FAIL] abc-002 http=400
10:40:03 [INFO] Done: {'ok': 4, 'fail': 1, 'skip': 0}
```

### Integration walkthrough

```bash
# 1. List 10 pending clips
python -m review.review_queue list --limit 10

# 2. Approve three of them
python -m review.review_queue approve --clip-id <id1>
python -m review.review_queue approve --clip-id <id2>
python -m review.review_queue approve --clip-id <id3>

# 3. Transcribe approved clips
python -m transcribe.transcribe_clips --limit 10

# 4. Verify transcripts
python -m review.review_queue list --status approved --limit 10
```

## Running Module 3

### Process a single recording (dry-run, no creds)

```bash
DRY_RUN=true python -m worker.process_audio \
    --recording-id 00000000-0000-0000-0000-000000000000
```

### Process with real credentials

```bash
python -m worker.process_audio --recording-id <uuid>
```

### Via the API endpoint

```bash
uvicorn server:app --host 0.0.0.0 --port 8080

curl -X POST http://localhost:8080/api/worker/process-audio \
    -H 'Content-Type: application/json' \
    -d '{"recording_id":"<uuid>"}'
```

## Database migrations

Run in order in Supabase SQL Editor:

1. `migrations/002_processor_columns.sql` — recordings metrics + clips table
2. `migrations/003_cv_submissions.sql` — review columns + cv_submissions table

Both are idempotent (safe to re-run).

### Stuck-processing reaper

If a worker crashes mid-processing, recordings may be stuck in `processing`.
Run this manually in Supabase SQL Editor to reset them:

```sql
-- Find stuck recordings (processing for > 30 minutes)
SELECT id, status, created_at
FROM recordings
WHERE status = 'processing'
  AND updated_at < now() - interval '30 minutes';

-- Reset them (after confirming no active worker)
UPDATE recordings
SET status = 'raw_uploaded'
WHERE status = 'processing'
  AND updated_at < now() - interval '30 minutes';
```

## Status machines

### recordings.status

```
raw_uploaded --> processing --> processed
                    |              (clips created, status=pending_review)
                    |
                    +---> failed
                            (failure_reason written)
```

Valid statuses: `raw_uploaded`, `processing`, `processed`, `failed`

### clips.status

```
pending_review --> approved --> (transcribed) --> (submitted to CV)
       |
       +--------> rejected
                    (rejection_reason written)
```

Valid statuses: `pending_review`, `approved`, `rejected`

## Cloud Run deployment

### Recommended settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| Memory | >= 4 GiB | silero-vad + torch model in RAM |
| CPU | 1-2 | VAD is CPU-only; single recording at a time |
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

SANDBOX PROFILER SUMMARY
  Total:      10
  OK:         8
  NO_SPEECH:  1
  FAILED:     1
  Total clips:     42
  Total speech:    215.3s from 1520.0s input
  Median MP3 size: 4500 bytes

  Output: ~/Desktop/voicelink_sandbox_clips
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
