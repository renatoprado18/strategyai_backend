-- Migration: Add status workflow and confidence scoring features
-- Date: 2025-01-27
-- Description: Extends status enum, adds confidence scoring, and chat history

-- ============================================================================
-- PART 1: Extend Status Enum
-- ============================================================================

-- Note: In Supabase, you cannot directly alter enum types.
-- Instead, we'll change the column to TEXT with a CHECK constraint.

-- Step 1: Drop existing status constraint if it exists (safe operation)
ALTER TABLE submissions DROP CONSTRAINT IF EXISTS submissions_status_check;

-- Step 2: Ensure status column is TEXT type (it should already be)
-- No need to alter if already TEXT

-- Step 3: Add CHECK constraint with new status values
ALTER TABLE submissions
ADD CONSTRAINT submissions_status_check CHECK (
    status IN (
        'pending',
        'processing',
        'completed',
        'ready_to_send',
        'sent',
        'failed'
    )
);

-- ============================================================================
-- PART 2: Add Confidence Scoring Columns
-- ============================================================================

-- Add confidence_score column (0-100)
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS confidence_score FLOAT DEFAULT NULL;

-- Add confidence_breakdown column (JSON with score breakdown)
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS confidence_breakdown JSONB DEFAULT NULL;

-- Add comment for clarity
COMMENT ON COLUMN submissions.confidence_score IS 'AI confidence score 0-100 based on data quality and analysis completeness';
COMMENT ON COLUMN submissions.confidence_breakdown IS 'JSON breakdown of confidence score factors';

-- ============================================================================
-- PART 3: Add Chat History Column
-- ============================================================================

-- Add chat_history column (JSON array of chat messages)
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS chat_history JSONB DEFAULT '[]'::jsonb;

-- Add comment
COMMENT ON COLUMN submissions.chat_history IS 'Array of chat messages for AI Q&A about the report';

-- ============================================================================
-- PART 4: Create Indexes for Performance
-- ============================================================================

-- Index on confidence_score for filtering
CREATE INDEX IF NOT EXISTS idx_submissions_confidence_score
ON submissions(confidence_score)
WHERE confidence_score IS NOT NULL;

-- Index on status for efficient filtering (rebuild with new values)
DROP INDEX IF EXISTS idx_status;
CREATE INDEX idx_status ON submissions(status);

-- Composite index for status + confidence queries
CREATE INDEX IF NOT EXISTS idx_submissions_status_confidence
ON submissions(status, confidence_score);

-- ============================================================================
-- PART 5: Update Existing Rows (Optional - Set Defaults)
-- ============================================================================

-- Update existing 'completed' rows to have default confidence score of 75 (needs review)
-- This is conservative - admin can recalculate actual scores
UPDATE submissions
SET confidence_score = 75.0,
    confidence_breakdown = jsonb_build_object(
        'calculated', false,
        'default', true,
        'note', 'Legacy report - score not calculated'
    )
WHERE status = 'completed'
  AND confidence_score IS NULL;

-- ============================================================================
-- VERIFICATION QUERIES (Run These After Migration)
-- ============================================================================

-- Check column existence
-- SELECT column_name, data_type, is_nullable
-- FROM information_schema.columns
-- WHERE table_name = 'submissions'
--   AND column_name IN ('confidence_score', 'confidence_breakdown', 'chat_history');

-- Check indexes
-- SELECT indexname, indexdef
-- FROM pg_indexes
-- WHERE tablename = 'submissions';

-- Check status constraint
-- SELECT conname, pg_get_constraintdef(oid)
-- FROM pg_constraint
-- WHERE conname = 'submissions_status_check';

-- ============================================================================
-- ROLLBACK SCRIPT (In Case of Issues)
-- ============================================================================

-- Uncomment and run if you need to roll back changes:

-- -- Drop new columns
-- ALTER TABLE submissions DROP COLUMN IF EXISTS confidence_score;
-- ALTER TABLE submissions DROP COLUMN IF EXISTS confidence_breakdown;
-- ALTER TABLE submissions DROP COLUMN IF EXISTS chat_history;

-- -- Drop new indexes
-- DROP INDEX IF EXISTS idx_submissions_confidence_score;
-- DROP INDEX IF EXISTS idx_submissions_status_confidence;

-- -- Restore original status constraint
-- ALTER TABLE submissions DROP CONSTRAINT IF EXISTS submissions_status_check;
-- ALTER TABLE submissions
-- ADD CONSTRAINT submissions_status_check CHECK (
--     status IN ('pending', 'completed', 'failed')
-- );
