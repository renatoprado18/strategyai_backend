-- Migration: Add editing support columns to submissions table
-- Run this in Supabase SQL Editor

-- Add new columns for AI-powered editing
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS edited_json JSONB,
ADD COLUMN IF NOT EXISTS last_edited_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS edit_count INTEGER DEFAULT 0;

-- Add index for faster queries on edited reports
CREATE INDEX IF NOT EXISTS idx_last_edited ON submissions(last_edited_at DESC) WHERE last_edited_at IS NOT NULL;

-- Add index for edit_count
CREATE INDEX IF NOT EXISTS idx_edit_count ON submissions(edit_count) WHERE edit_count > 0;

-- Add comment to explain columns
COMMENT ON COLUMN submissions.edited_json IS 'Edited version of report_json after AI-powered inline editing';
COMMENT ON COLUMN submissions.last_edited_at IS 'Timestamp of last edit applied';
COMMENT ON COLUMN submissions.edit_count IS 'Number of AI-powered edits applied to report';
