-- ============================================================================
-- Enhanced Caching System - Supabase SQL Schema
-- Run this SQL in your Supabase SQL Editor to create cache tables
-- ============================================================================

-- 1. Analysis Cache Table (stores complete analysis results)
-- This is THE most important cache - saves $15-25 per hit!
CREATE TABLE IF NOT EXISTS analysis_cache (
    id BIGSERIAL PRIMARY KEY,
    cache_key TEXT NOT NULL UNIQUE,
    company TEXT NOT NULL,
    industry TEXT NOT NULL,
    challenge_snippet TEXT,
    content_hash TEXT NOT NULL,
    analysis_json TEXT NOT NULL,  -- Complete analysis JSON
    cost_saved DECIMAL(10, 4) DEFAULT 0,  -- Cost saved per hit
    processing_time_seconds DECIMAL(10, 2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    hit_count INTEGER DEFAULT 0,

    -- Indexes for fast lookup
    CONSTRAINT unique_cache_key UNIQUE (cache_key)
);

CREATE INDEX IF NOT EXISTS idx_analysis_cache_company ON analysis_cache(company);
CREATE INDEX IF NOT EXISTS idx_analysis_cache_industry ON analysis_cache(industry);
CREATE INDEX IF NOT EXISTS idx_analysis_cache_accessed ON analysis_cache(last_accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_analysis_cache_key ON analysis_cache(cache_key);

-- 2. Stage Cache Table (stores individual pipeline stage results)
CREATE TABLE IF NOT EXISTS stage_cache (
    id BIGSERIAL PRIMARY KEY,
    cache_key TEXT NOT NULL UNIQUE,
    stage_name TEXT NOT NULL,
    company TEXT NOT NULL,
    industry TEXT NOT NULL,
    input_hash TEXT NOT NULL,
    result_json TEXT NOT NULL,  -- Stage result JSON
    cost_saved DECIMAL(10, 4) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    hit_count INTEGER DEFAULT 0,

    CONSTRAINT unique_stage_cache_key UNIQUE (cache_key)
);

CREATE INDEX IF NOT EXISTS idx_stage_cache_stage ON stage_cache(stage_name);
CREATE INDEX IF NOT EXISTS idx_stage_cache_company ON stage_cache(company);
CREATE INDEX IF NOT EXISTS idx_stage_cache_accessed ON stage_cache(last_accessed_at DESC);

-- 3. PDF Cache Table (stores PDF generation metadata)
-- Note: For production, consider using Supabase Storage for actual PDF files
CREATE TABLE IF NOT EXISTS pdf_cache (
    id BIGSERIAL PRIMARY KEY,
    cache_key TEXT NOT NULL UNIQUE,
    submission_id BIGINT,
    content_hash TEXT NOT NULL,
    file_size_bytes BIGINT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    hit_count INTEGER DEFAULT 0,

    CONSTRAINT unique_pdf_cache_key UNIQUE (cache_key)
);

CREATE INDEX IF NOT EXISTS idx_pdf_cache_submission ON pdf_cache(submission_id);
CREATE INDEX IF NOT EXISTS idx_pdf_cache_accessed ON pdf_cache(last_accessed_at DESC);

-- 4. Stats Cache Table (stores dashboard statistics with short TTL)
CREATE TABLE IF NOT EXISTS stats_cache (
    id BIGSERIAL PRIMARY KEY,
    cache_key TEXT NOT NULL UNIQUE,
    stats_json TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT unique_stats_cache_key UNIQUE (cache_key)
);

CREATE INDEX IF NOT EXISTS idx_stats_cache_expires ON stats_cache(expires_at DESC);

-- ============================================================================
-- Row Level Security (RLS) Policies
-- ============================================================================

-- Enable RLS on all cache tables
ALTER TABLE analysis_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE stage_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE pdf_cache ENABLE ROW LEVEL SECURITY;
ALTER TABLE stats_cache ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read cache (admins + service role)
CREATE POLICY "Authenticated users can read analysis_cache"
    ON analysis_cache FOR SELECT
    USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Authenticated users can read stage_cache"
    ON stage_cache FOR SELECT
    USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Authenticated users can read pdf_cache"
    ON pdf_cache FOR SELECT
    USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

CREATE POLICY "Authenticated users can read stats_cache"
    ON stats_cache FOR SELECT
    USING (auth.role() = 'authenticated' OR auth.role() = 'service_role');

-- Allow service role to insert/update/delete cache
CREATE POLICY "Service role can insert analysis_cache"
    ON analysis_cache FOR INSERT
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role can update analysis_cache"
    ON analysis_cache FOR UPDATE
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can delete analysis_cache"
    ON analysis_cache FOR DELETE
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can insert stage_cache"
    ON stage_cache FOR INSERT
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role can update stage_cache"
    ON stage_cache FOR UPDATE
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can delete stage_cache"
    ON stage_cache FOR DELETE
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can insert pdf_cache"
    ON pdf_cache FOR INSERT
    WITH CHECK (auth.role() = 'service_role');

CREATE POLICY "Service role can update pdf_cache"
    ON pdf_cache FOR UPDATE
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can delete pdf_cache"
    ON pdf_cache FOR DELETE
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage stats_cache"
    ON stats_cache FOR ALL
    USING (auth.role() = 'service_role');

-- ============================================================================
-- Utility Functions
-- ============================================================================

-- Function to get cache hit rate
CREATE OR REPLACE FUNCTION get_cache_hit_rate()
RETURNS TABLE (
    cache_type TEXT,
    total_records BIGINT,
    total_hits BIGINT,
    hit_rate DECIMAL,
    total_cost_saved DECIMAL
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        'analysis'::TEXT as cache_type,
        COUNT(*)::BIGINT as total_records,
        SUM(hit_count)::BIGINT as total_hits,
        CASE
            WHEN COUNT(*) > 0 THEN ROUND((SUM(hit_count)::DECIMAL / COUNT(*)) * 100, 2)
            ELSE 0
        END as hit_rate,
        ROUND(SUM(cost_saved * hit_count), 2) as total_cost_saved
    FROM analysis_cache

    UNION ALL

    SELECT
        'stage'::TEXT,
        COUNT(*)::BIGINT,
        SUM(hit_count)::BIGINT,
        CASE
            WHEN COUNT(*) > 0 THEN ROUND((SUM(hit_count)::DECIMAL / COUNT(*)) * 100, 2)
            ELSE 0
        END,
        ROUND(SUM(cost_saved * hit_count), 2)
    FROM stage_cache

    UNION ALL

    SELECT
        'pdf'::TEXT,
        COUNT(*)::BIGINT,
        SUM(hit_count)::BIGINT,
        CASE
            WHEN COUNT(*) > 0 THEN ROUND((SUM(hit_count)::DECIMAL / COUNT(*) * 100), 2)
            ELSE 0
        END,
        0  -- PDFs save time, not money
    FROM pdf_cache;
END;
$$ LANGUAGE plpgsql;

-- Function to clear old cache entries (run periodically)
CREATE OR REPLACE FUNCTION clear_old_cache()
RETURNS TABLE (
    table_name TEXT,
    records_deleted BIGINT
) AS $$
DECLARE
    analysis_deleted BIGINT;
    stage_deleted BIGINT;
    pdf_deleted BIGINT;
    stats_deleted BIGINT;
BEGIN
    -- Delete old analysis cache (30 days)
    DELETE FROM analysis_cache
    WHERE last_accessed_at < NOW() - INTERVAL '30 days';
    GET DIAGNOSTICS analysis_deleted = ROW_COUNT;

    -- Delete old stage cache (7 days)
    DELETE FROM stage_cache
    WHERE last_accessed_at < NOW() - INTERVAL '7 days';
    GET DIAGNOSTICS stage_deleted = ROW_COUNT;

    -- Delete old PDF cache (90 days)
    DELETE FROM pdf_cache
    WHERE last_accessed_at < NOW() - INTERVAL '90 days';
    GET DIAGNOSTICS pdf_deleted = ROW_COUNT;

    -- Delete expired stats cache
    DELETE FROM stats_cache
    WHERE expires_at < NOW();
    GET DIAGNOSTICS stats_deleted = ROW_COUNT;

    RETURN QUERY
    SELECT 'analysis_cache'::TEXT, analysis_deleted
    UNION ALL
    SELECT 'stage_cache'::TEXT, stage_deleted
    UNION ALL
    SELECT 'pdf_cache'::TEXT, pdf_deleted
    UNION ALL
    SELECT 'stats_cache'::TEXT, stats_deleted;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Comments for Documentation
-- ============================================================================

COMMENT ON TABLE analysis_cache IS 'Stores complete AI analysis results to avoid expensive re-computation ($15-25 saved per hit)';
COMMENT ON TABLE stage_cache IS 'Stores individual pipeline stage results for partial cache hits';
COMMENT ON TABLE pdf_cache IS 'Stores PDF generation metadata to avoid re-rendering (stores metadata only, files on disk/storage)';
COMMENT ON TABLE stats_cache IS 'Stores dashboard statistics with short TTL (5 minutes) for high-frequency requests';

COMMENT ON FUNCTION get_cache_hit_rate() IS 'Returns cache hit statistics and cost savings across all cache types';
COMMENT ON FUNCTION clear_old_cache() IS 'Clears expired cache entries based on TTL. Run this periodically (e.g., daily cron job)';

-- ============================================================================
-- Initial Setup Complete!
-- ============================================================================

-- Query to verify tables created successfully
SELECT
    tablename,
    schemaname
FROM pg_tables
WHERE tablename IN ('analysis_cache', 'stage_cache', 'pdf_cache', 'stats_cache')
ORDER BY tablename;

-- Query to check cache hit rates (run after system has been running)
-- SELECT * FROM get_cache_hit_rate();

-- Query to clear old cache (run periodically)
-- SELECT * FROM clear_old_cache();
