-- Migration 003: Module 4 — Review + CV submission support
-- Run in Supabase SQL Editor.  Safe to re-run (all guards are IF NOT EXISTS).

-- ---------------------------------------------------------------
-- Compatibility fix: rename gcs_path -> gcs_clip_url if migration 002
-- was applied before the column rename.
-- ---------------------------------------------------------------
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clips' AND column_name = 'gcs_path'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'clips' AND column_name = 'gcs_clip_url'
  ) THEN
    ALTER TABLE clips RENAME COLUMN gcs_path TO gcs_clip_url;
  END IF;
END$$;

-- Ensure transcript and status columns exist (additive)
ALTER TABLE clips ADD COLUMN IF NOT EXISTS transcript TEXT;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'pending_review';
CREATE INDEX IF NOT EXISTS idx_clips_status ON clips(status);

-- ---------------------------------------------------------------
-- clips.rejection_reason — stores why a reviewer rejected a clip
-- ---------------------------------------------------------------
ALTER TABLE clips ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- ---------------------------------------------------------------
-- cv_submissions — tracks each attempt to submit a clip to Common Voice
-- ---------------------------------------------------------------
CREATE TABLE IF NOT EXISTS cv_submissions (
  id               UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  clip_id          UUID NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
  attempted_at     TIMESTAMPTZ DEFAULT now(),
  cv_resource_type TEXT,
  http_status      INTEGER,
  success          BOOLEAN NOT NULL DEFAULT false,
  error_message    TEXT
);

CREATE INDEX IF NOT EXISTS idx_cv_submissions_clip_id ON cv_submissions(clip_id);
CREATE INDEX IF NOT EXISTS idx_cv_submissions_success ON cv_submissions(success);
