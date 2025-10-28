-- Migration: Separate Backend Processing State from User-Facing Status
-- Date: 2025-10-28
-- Description: Separates internal backend state from user action tracking

-- ============================================================================
-- PART 1: Add New Columns
-- ============================================================================

-- Add processing_state (backend internal state)
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS processing_state TEXT DEFAULT 'queued';

-- Add user_status (frontend/user-facing state)
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS user_status TEXT DEFAULT 'submitted';

-- Add sent_to_client tracking
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS sent_to_client_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS sent_to_client_email TEXT DEFAULT NULL;

-- Add archived_at tracking
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP WITH TIME ZONE DEFAULT NULL;

-- ============================================================================
-- PART 2: Migrate Existing Data
-- ============================================================================

-- Migrate from old 'status' to new 'processing_state' and 'user_status'
UPDATE submissions
SET
    processing_state = CASE
        WHEN status = 'pending' THEN 'queued'
        WHEN status = 'processing' THEN 'ai_analyzing'
        WHEN status = 'completed' THEN 'completed'
        WHEN status = 'failed' THEN 'failed'
        WHEN status = 'ready_to_send' THEN 'completed'
        WHEN status = 'sent' THEN 'completed'
        ELSE 'queued'
    END,
    user_status = CASE
        WHEN status = 'pending' THEN 'submitted'
        WHEN status = 'processing' THEN 'analyzing'
        WHEN status = 'completed' THEN 'ready'
        WHEN status = 'failed' THEN 'submitted'
        WHEN status = 'ready_to_send' THEN 'ready'
        WHEN status = 'sent' THEN 'sent_to_client'
        ELSE 'submitted'
    END;

-- ============================================================================
-- PART 3: Add Constraints
-- ============================================================================

-- Add CHECK constraint for processing_state
ALTER TABLE submissions
ADD CONSTRAINT submissions_processing_state_check CHECK (
    processing_state IN (
        'queued',          -- Waiting in queue
        'data_gathering',  -- Collecting external data (Apify/Perplexity)
        'ai_analyzing',    -- Running AI analysis pipeline
        'finalizing',      -- Saving to database, calculating confidence
        'completed',       -- Successfully finished
        'failed'           -- Error occurred
    )
);

-- Add CHECK constraint for user_status
ALTER TABLE submissions
ADD CONSTRAINT submissions_user_status_check CHECK (
    user_status IN (
        'draft',           -- User still editing form (future use)
        'submitted',       -- User submitted, waiting for analysis
        'analyzing',       -- Analysis in progress (friendly name)
        'ready',           -- Analysis done, ready for user review
        'reviewed',        -- User has reviewed the report
        'sent_to_client',  -- User sent report to their client
        'archived'         -- User archived this submission
    )
);

-- ============================================================================
-- PART 4: Add Indexes
-- ============================================================================

-- Index on processing_state for backend queries
CREATE INDEX IF NOT EXISTS idx_submissions_processing_state
ON submissions(processing_state);

-- Index on user_status for dashboard queries
CREATE INDEX IF NOT EXISTS idx_submissions_user_status
ON submissions(user_status);

-- Composite index for user_status + updated_at (most common dashboard query)
CREATE INDEX IF NOT EXISTS idx_submissions_user_status_updated
ON submissions(user_status, updated_at DESC);

-- Composite index for processing_state + created_at (monitoring)
CREATE INDEX IF NOT EXISTS idx_submissions_processing_state_created
ON submissions(processing_state, created_at DESC);

-- ============================================================================
-- PART 5: Add Comments for Documentation
-- ============================================================================

COMMENT ON COLUMN submissions.processing_state IS 'Backend internal state: Where is the analysis pipeline? (queued, data_gathering, ai_analyzing, finalizing, completed, failed)';

COMMENT ON COLUMN submissions.user_status IS 'User-facing status: What can the user do? (draft, submitted, analyzing, ready, reviewed, sent_to_client, archived)';

COMMENT ON COLUMN submissions.sent_to_client_at IS 'Timestamp when user sent report to their client';

COMMENT ON COLUMN submissions.sent_to_client_email IS 'Email address where report was sent';

COMMENT ON COLUMN submissions.archived_at IS 'Timestamp when user archived this submission';

-- Mark old status column as deprecated
COMMENT ON COLUMN submissions.status IS 'DEPRECATED: Use processing_state (backend) and user_status (frontend) instead. Kept for backward compatibility only.';

-- ============================================================================
-- PART 6: Create View for Backward Compatibility
-- ============================================================================

-- Create view that combines new fields into old status format
-- This allows old code to keep working during migration
CREATE OR REPLACE VIEW submissions_legacy_status AS
SELECT
    *,
    -- Compute legacy status from new fields
    CASE
        WHEN processing_state = 'queued' THEN 'pending'
        WHEN processing_state = 'data_gathering' THEN 'processing'
        WHEN processing_state = 'ai_analyzing' THEN 'processing'
        WHEN processing_state = 'finalizing' THEN 'processing'
        WHEN processing_state = 'failed' THEN 'failed'
        WHEN processing_state = 'completed' AND user_status = 'ready' THEN 'completed'
        WHEN processing_state = 'completed' AND user_status = 'reviewed' THEN 'ready_to_send'
        WHEN processing_state = 'completed' AND user_status = 'sent_to_client' THEN 'sent'
        WHEN processing_state = 'completed' AND user_status = 'archived' THEN 'sent'
        ELSE 'pending'
    END AS legacy_status
FROM submissions;

COMMENT ON VIEW submissions_legacy_status IS 'Backward compatibility view that maps new processing_state + user_status to old status field';

-- ============================================================================
-- PART 7: Create Helper Functions
-- ============================================================================

-- Function to auto-compute user_status from processing_state
CREATE OR REPLACE FUNCTION compute_user_status(p_processing_state TEXT)
RETURNS TEXT AS $$
BEGIN
    RETURN CASE p_processing_state
        WHEN 'queued' THEN 'submitted'
        WHEN 'data_gathering' THEN 'analyzing'
        WHEN 'ai_analyzing' THEN 'analyzing'
        WHEN 'finalizing' THEN 'analyzing'
        WHEN 'completed' THEN 'ready'
        WHEN 'failed' THEN 'submitted'  -- Allow retry
        ELSE 'submitted'
    END;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION compute_user_status IS 'Auto-computes user_status from processing_state';

-- ============================================================================
-- VERIFICATION QUERIES (Run after migration)
-- ============================================================================

-- Check distribution of processing_state
-- SELECT processing_state, COUNT(*) FROM submissions GROUP BY processing_state ORDER BY COUNT(*) DESC;

-- Check distribution of user_status
-- SELECT user_status, COUNT(*) FROM submissions GROUP BY user_status ORDER BY COUNT(*) DESC;

-- Check if any submissions have invalid states (should be 0)
-- SELECT COUNT(*) FROM submissions WHERE processing_state NOT IN ('queued', 'data_gathering', 'ai_analyzing', 'finalizing', 'completed', 'failed');
-- SELECT COUNT(*) FROM submissions WHERE user_status NOT IN ('draft', 'submitted', 'analyzing', 'ready', 'reviewed', 'sent_to_client', 'archived');

-- Compare old vs new status mapping
-- SELECT status, processing_state, user_status, COUNT(*) FROM submissions GROUP BY status, processing_state, user_status ORDER BY COUNT(*) DESC;

-- ============================================================================
-- ROLLBACK PLAN (if needed)
-- ============================================================================

/*
-- To rollback this migration:

-- Drop new indexes
DROP INDEX IF EXISTS idx_submissions_processing_state;
DROP INDEX IF EXISTS idx_submissions_user_status;
DROP INDEX IF EXISTS idx_submissions_user_status_updated;
DROP INDEX IF EXISTS idx_submissions_processing_state_created;

-- Drop constraints
ALTER TABLE submissions DROP CONSTRAINT IF EXISTS submissions_processing_state_check;
ALTER TABLE submissions DROP CONSTRAINT IF EXISTS submissions_user_status_check;

-- Drop helper function
DROP FUNCTION IF EXISTS compute_user_status;

-- Drop view
DROP VIEW IF EXISTS submissions_legacy_status;

-- Drop new columns
ALTER TABLE submissions DROP COLUMN IF EXISTS processing_state;
ALTER TABLE submissions DROP COLUMN IF EXISTS user_status;
ALTER TABLE submissions DROP COLUMN IF EXISTS sent_to_client_at;
ALTER TABLE submissions DROP COLUMN IF EXISTS sent_to_client_email;
ALTER TABLE submissions DROP COLUMN IF EXISTS archived_at;

-- Restore old status comment
COMMENT ON COLUMN submissions.status IS 'Status of the submission: pending, processing, completed, failed, ready_to_send, sent';
*/
