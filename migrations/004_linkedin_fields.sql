-- Migration: Add LinkedIn fields for enhanced analysis
-- Date: 2025-10-26
-- Purpose: Store company and founder LinkedIn URLs for AI enrichment

-- Add LinkedIn columns to submissions table
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS linkedin_company TEXT,
ADD COLUMN IF NOT EXISTS linkedin_founder TEXT;

-- Add indexes for searching by LinkedIn URLs (optional but useful)
CREATE INDEX IF NOT EXISTS idx_linkedin_company ON submissions(linkedin_company) WHERE linkedin_company IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_linkedin_founder ON submissions(linkedin_founder) WHERE linkedin_founder IS NOT NULL;

-- Add comments explaining the columns
COMMENT ON COLUMN submissions.linkedin_company IS 'LinkedIn URL of the company page for AI enrichment and analysis';
COMMENT ON COLUMN submissions.linkedin_founder IS 'LinkedIn URL of the founder/CEO for leadership analysis and company insights';

-- Example data:
-- linkedin_company: "https://www.linkedin.com/company/nubank/"
-- linkedin_founder: "https://www.linkedin.com/in/davidvelez/"
