-- Migration: Add Social Media and Contact Fields
-- Version: 010
-- Date: 2025-01-12
-- Description: Add phone, whatsapp, instagram, tiktok fields to submissions table
-- Safe: All fields are nullable and optional

-- Add new columns (safe - all nullable)
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS phone TEXT,
ADD COLUMN IF NOT EXISTS whatsapp TEXT,
ADD COLUMN IF NOT EXISTS instagram TEXT,
ADD COLUMN IF NOT EXISTS tiktok TEXT;

-- Add indexes for faster lookups (only on non-null values)
CREATE INDEX IF NOT EXISTS idx_submissions_phone
ON submissions(phone)
WHERE phone IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_submissions_whatsapp
ON submissions(whatsapp)
WHERE whatsapp IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_submissions_instagram
ON submissions(instagram)
WHERE instagram IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_submissions_tiktok
ON submissions(tiktok)
WHERE tiktok IS NOT NULL;

-- Add column comments for documentation
COMMENT ON COLUMN submissions.phone IS 'Contact phone number (formatted, optional)';
COMMENT ON COLUMN submissions.whatsapp IS 'WhatsApp number (formatted, optional)';
COMMENT ON COLUMN submissions.instagram IS 'Instagram profile URL or handle (optional)';
COMMENT ON COLUMN submissions.tiktok IS 'TikTok profile URL or handle (optional)';

-- Verification query (optional - shows new columns)
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'submissions'
-- AND column_name IN ('phone', 'whatsapp', 'instagram', 'tiktok');
