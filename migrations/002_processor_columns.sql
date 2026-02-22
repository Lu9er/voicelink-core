-- Migration 002: Add columns required by Module 3 (Audio Processor)
-- Run this in Supabase SQL Editor before starting the worker.
--
-- Safe to re-run: every statement uses IF NOT EXISTS / IF EXISTS guards.

-- ---------------------------------------------------------------
-- recordings: source-metadata columns (populated by ffprobe)
-- ---------------------------------------------------------------
ALTER TABLE recordings
  ADD COLUMN IF NOT EXISTS source_sample_rate  INTEGER,
  ADD COLUMN IF NOT EXISTS source_codec        TEXT,
  ADD COLUMN IF NOT EXISTS source_channels     INTEGER;

-- recordings: processing metrics
ALTER TABLE recordings
  ADD COLUMN IF NOT EXISTS clip_count       INTEGER DEFAULT 0,
  ADD COLUMN IF NOT EXISTS speech_seconds   REAL,
  ADD COLUMN IF NOT EXISTS speech_yield     REAL;

-- ---------------------------------------------------------------
-- clips table — one row per 3–15 s segment extracted by the worker
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clips (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  recording_id     UUID NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
  gcs_path         TEXT NOT NULL,
  duration_seconds REAL NOT NULL,
  format           TEXT NOT NULL DEFAULT 'mp3',
  source_quality   TEXT,
  created_at       TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_clips_recording_id ON clips(recording_id);
