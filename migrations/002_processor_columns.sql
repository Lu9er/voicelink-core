-- Migration 002: Add columns required by Module 3 (Audio Processor)
-- Run this in Supabase SQL Editor before starting processor.py.

-- New source-metadata columns on recordings
ALTER TABLE recordings
  ADD COLUMN IF NOT EXISTS source_sample_rate  INTEGER,
  ADD COLUMN IF NOT EXISTS source_codec        TEXT,
  ADD COLUMN IF NOT EXISTS source_channels     INTEGER,
  ADD COLUMN IF NOT EXISTS source_quality      TEXT,
  ADD COLUMN IF NOT EXISTS music_ratio         REAL,
  ADD COLUMN IF NOT EXISTS clip_count          INTEGER DEFAULT 0;

-- Add 'rejected' to the status lifecycle (music > 40%, no speech, etc.)
-- If status is a TEXT column, this is a no-op; if it's an ENUM, uncomment:
-- ALTER TYPE recording_status ADD VALUE IF NOT EXISTS 'rejected';
-- ALTER TYPE recording_status ADD VALUE IF NOT EXISTS 'processing';

-- Clips table — one row per 3-10 s segment extracted from a recording
CREATE TABLE IF NOT EXISTS clips (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  recording_id     UUID NOT NULL REFERENCES recordings(id) ON DELETE CASCADE,
  clip_index       INTEGER NOT NULL,
  start_time       REAL NOT NULL,
  end_time         REAL NOT NULL,
  duration_seconds REAL NOT NULL,
  gcs_path         TEXT NOT NULL,
  transcript       TEXT,
  source_quality   TEXT,
  created_at       TIMESTAMPTZ DEFAULT now(),

  UNIQUE (recording_id, clip_index)
);

CREATE INDEX IF NOT EXISTS idx_clips_recording_id ON clips(recording_id);
