-- Migration: Add data quality and processing metadata tracking
-- Date: 2025-10-26
-- Purpose: Track Apify data quality and AI processing metadata for transparency

-- Add new columns to submissions table
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS data_quality_json TEXT,
ADD COLUMN IF NOT EXISTS processing_metadata TEXT;

-- Add indexes for querying by data quality
CREATE INDEX IF NOT EXISTS idx_data_quality ON submissions USING gin (data_quality_json jsonb_path_ops);
CREATE INDEX IF NOT EXISTS idx_processing_metadata ON submissions USING gin (processing_metadata jsonb_path_ops);

-- Add comment explaining the columns
COMMENT ON COLUMN submissions.data_quality_json IS 'Stores Apify data quality metrics: which sources succeeded/failed, data completeness percentage';
COMMENT ON COLUMN submissions.processing_metadata IS 'Stores AI processing metadata: model used, tokens consumed, processing time, framework version';

-- Example data_quality_json structure:
-- {
--   "website_scraped": true,
--   "competitors_found": 12,
--   "trends_researched": true,
--   "company_enriched": false,
--   "data_completeness": "75%",
--   "sources_succeeded": 3,
--   "sources_failed": 1,
--   "failed_sources": ["company_enrichment"],
--   "quality_tier": "good"
-- }

-- Example processing_metadata structure:
-- {
--   "model": "openai/gpt-4o",
--   "framework_version": "10XMentorAI v2.0",
--   "tokens_used": 6500,
--   "processing_time_seconds": 45,
--   "apify_time_seconds": 23,
--   "generated_at": "2025-10-26T12:34:56Z"
-- }
