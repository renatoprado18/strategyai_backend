-- ============================================================================
-- Migration 008: Add sent_to_client_name Column
-- Date: 2025-10-28
-- Description: Add missing sent_to_client_name column referenced in user_actions.py
-- ============================================================================

-- Add sent_to_client_name column
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS sent_to_client_name TEXT DEFAULT NULL;

-- Add index for searching by client name (optional but useful for admin dashboard)
CREATE INDEX IF NOT EXISTS idx_submissions_client_name
ON submissions(sent_to_client_name)
WHERE sent_to_client_name IS NOT NULL;

-- Add comment for documentation
COMMENT ON COLUMN submissions.sent_to_client_name IS 'Name of the client recipient when report was sent via email';

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- Verify column exists
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'submissions'
  AND column_name = 'sent_to_client_name';

-- Check all sent_to_client columns together
SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'submissions'
  AND column_name LIKE 'sent_to_client%'
ORDER BY column_name;

-- Expected output:
-- sent_to_client_at     | timestamp with time zone | YES | NULL
-- sent_to_client_email  | text                     | YES | NULL
-- sent_to_client_name   | text                     | YES | NULL
