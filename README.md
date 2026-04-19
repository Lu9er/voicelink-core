# VoiceLink

An open-source speech data pipeline for low-resource African languages. VoiceLink ingests long-form audio (radio archives, live radio call-ins, community recordings), segments it into short speech clips with voice-activity detection, optionally transcribes the clips, and prepares the result for submission to open datasets such as Mozilla Common Voice.

The first target languages are **Luganda** and **Ateso**, both widely spoken in Uganda and both significantly underrepresented in public speech corpora.

---

## Why this project exists

Modern speech recognition and voice technologies are overwhelmingly trained on a small handful of high-resource languages — English, Mandarin, Spanish, and a few dozen more. Languages with tens of millions of speakers in East Africa (Luganda ~10M, Ateso ~2.5M) have almost no public training data, which keeps commercial speech tools unusable for those communities.

VoiceLink's purpose is to reduce that gap: build a pipeline that can process **donated, consented, broadcast-quality audio** into clean, clip-level datasets, and contribute them to permissive public corpora.

This is a non-commercial research and community-data project. It is run from Uganda by an independent developer. There is no end-user product, no marketing channel, no consumer-facing service.

---

## What it does, step by step

1. **Ingest** — Long-form audio enters the system from one of two sources:
   - **Archive ingestion** (`ingest_archives.py`) — batch upload of existing radio archives (e.g. a Luganda broadcast archive from a partner station, ~6,700 one-hour MP3s). SHA-256 deduplication, ffprobe duration, upload to Google Cloud Storage, row insert in Supabase.
   - **Live ingestion** (`server.py`) — a FastAPI server that receives Twilio recording webhooks from a partner radio station's live call-in line, streams the recording to GCS, and registers it in the database.
2. **Segment** (`worker/process_audio.py`) — Each long recording is downloaded, normalized to 16 kHz mono WAV, run through a Silero voice-activity detector, and cut into 3–15 second speech clips.
3. **Store** — Clips are uploaded to GCS as MP3s. Metadata (duration, speech-yield, source recording) lands in Supabase.
4. **Review** (`review/`) — A human review queue lets a reviewer approve, reject, or transcribe clips.
5. **Transcribe** (`transcribe/`) — Optional ASR pass using Whisper / faster-whisper. For low-resource languages this is a weak first pass used for triage, not final labels.
6. **Submit** (`publisher/`) — Approved clip+transcript pairs can be submitted to Mozilla Common Voice.
7. **Monitor** (`dashboard/`) — A read-only Next.js dashboard over Supabase shows recordings, yield, clip inventory, and live-call status.

---

## Current status

- ~2,000 one-hour Luganda recordings ingested from a partner radio archive.
- Audio segmentation pipeline validated end-to-end on both Ateso and Luganda samples.
- A 600-file batch segmentation run is currently processing.
- A live-ingestion proof-of-concept is being built with Voice of Teso, a community radio station in Soroti, eastern Uganda.

---

## How Twilio is used

VoiceLink uses Twilio **Programmable Voice** for a single, narrow purpose: to receive audio from a partner radio station's live call-in line so that donated call audio can be ingested into the pipeline.

Specifically:

- **Inbound calls only** to a single Twilio-provisioned phone number that is dialed by the radio station's studio operator (via their 3-way call feature) during an active on-air caller segment.
- **Recording** via `<Record>` TwiML with a `recordingStatusCallback`.
- **Webhook events** delivered to `/api/twilio/live-webhook` on our server, which registers the recording in Supabase and uploads the audio to GCS.

VoiceLink does **not** use:
- SMS (no Messaging API usage)
- WhatsApp (no WhatsApp Business API usage)
- Outbound calls or outbound campaigns of any kind
- Marketing messaging of any kind
- Autodialers, voice broadcasts, or IVR-driven outreach

There are no consumer end-users on our side. The only caller population is listeners who have voluntarily called the partner radio station's public call-in line. Their audio is captured via the station's 3-way dial with the station's consent and the caller's on-air disclosure, then processed as above.

---

## Architecture

```
┌─────────────────────┐       ┌─────────────────────┐
│ Archive ingestion   │       │ Live ingestion      │
│ (ingest_archives.py)│       │ (server.py, Twilio) │
└──────────┬──────────┘       └──────────┬──────────┘
           │                             │
           └─────────────┬───────────────┘
                         ▼
               ┌───────────────────┐
               │  raw audio in GCS │
               │  row in Supabase  │
               └──────────┬────────┘
                          ▼
           ┌─────────────────────────────┐
           │ Audio Processor (Module 3)  │
           │ normalize → VAD → clip → MP3│
           └──────────┬──────────────────┘
                      ▼
               ┌───────────────────┐
               │  clips in GCS     │
               │  clips in Supabase│
               └──────────┬────────┘
                          ▼
               ┌─────────┴────────┐
               ▼                  ▼
       ┌──────────────┐   ┌──────────────┐
       │ Review queue │   │ Dashboard    │
       └──────┬───────┘   └──────────────┘
              ▼
       ┌──────────────┐
       │ Transcribe   │
       └──────┬───────┘
              ▼
       ┌──────────────────────┐
       │ Common Voice submit  │
       └──────────────────────┘
```

---

## Stack

- **Python** — FastAPI (ingestion server), Silero VAD, ffmpeg, faster-whisper (ASR)
- **Google Cloud Storage** — raw audio and clip storage
- **Supabase (Postgres)** — recordings, clips, review state
- **Twilio Programmable Voice** — live call-in capture (inbound voice + recording only)
- **Next.js + Cloudflare Workers** — read-only ops dashboard
- **Mozilla Common Voice** — final submission target for approved clip+transcript pairs

---

## Repository layout

| Path                  | Purpose                                                     |
| --------------------- | ----------------------------------------------------------- |
| `ingest_archives.py`  | Module 1 — batch archive ingestion                          |
| `server.py`           | Module 2 — FastAPI live ingester, Twilio webhooks           |
| `worker/`             | Module 3 — VAD segmentation, normalization, clip generation |
| `review/`             | Module 4 — clip review queue                                |
| `transcribe/`         | Module 5 — ASR pass                                         |
| `publisher/`          | Module 6 — Common Voice submission client                   |
| `dashboard/`          | Read-only Next.js dashboard                                 |
| `analytics/`          | Speech-hour counting and reporting                          |
| `migrations/`         | Supabase SQL migrations                                     |
| `docs/`               | Operational runbooks                                        |

---

## Operator

VoiceLink is maintained by Gideon Luper, an independent developer based in Uganda. Contact via the email associated with this GitHub account.

---

## License

Code: MIT (planned).
Audio datasets produced by the pipeline are released under the Creative Commons licenses required by the target dataset (typically CC0 for Mozilla Common Voice submissions).
