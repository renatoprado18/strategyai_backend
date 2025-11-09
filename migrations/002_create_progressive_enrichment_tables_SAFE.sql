-- ============================================================================
-- SAFE MIGRATION - Can be run multiple times without errors
-- ============================================================================
-- This version uses IF NOT EXISTS for all CREATE statements
-- Safe to run in Supabase Dashboard → SQL Editor even if partially run before
-- ============================================================================

-- ============================================================================
-- PROGRESSIVE ENRICHMENT SYSTEM - DATABASE SCHEMA
-- ============================================================================
-- Migration: 002_create_progressive_enrichment_tables_SAFE.sql
-- Description: Create tables for progressive enrichment tracking and caching
-- ============================================================================

-- ============================================================================
-- 1. PROGRESSIVE ENRICHMENT SESSIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS progressive_enrichment_sessions (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL UNIQUE,
    website_url TEXT NOT NULL,
    user_email TEXT,

    -- Layer completion timestamps
    layer1_completed_at TIMESTAMP WITH TIME ZONE,
    layer2_completed_at TIMESTAMP WITH TIME ZONE,
    layer3_completed_at TIMESTAMP WITH TIME ZONE,

    -- Performance metrics
    layer1_duration_ms INTEGER,
    layer2_duration_ms INTEGER,
    layer3_duration_ms INTEGER,
    total_duration_ms INTEGER,

    -- Cost tracking
    layer1_cost_usd DECIMAL(10, 6) DEFAULT 0.0,
    layer2_cost_usd DECIMAL(10, 6) DEFAULT 0.0,
    layer3_cost_usd DECIMAL(10, 6) DEFAULT 0.0,
    total_cost_usd DECIMAL(10, 6) DEFAULT 0.0,

    -- Enrichment data (JSONB for flexibility)
    layer1_data JSONB,
    layer2_data JSONB,
    layer3_data JSONB,

    -- Auto-fill tracking
    fields_auto_filled JSONB,  -- { "company_name": "TechStart", "industry": "Technology", ... }
    confidence_scores JSONB,   -- { "company_name": 95.0, "industry": 92.0, ... }
    user_edits JSONB,          -- Track which fields user manually edited

    -- Status tracking
    status VARCHAR(50) DEFAULT 'pending',  -- pending/layer1_complete/layer2_complete/complete/error
    error_message TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add comment
COMMENT ON TABLE progressive_enrichment_sessions IS
'Tracks progressive enrichment sessions with 3-layer execution (Layer 1: instant, Layer 2: structured, Layer 3: AI)';

-- Create indexes separately with IF NOT EXISTS
CREATE INDEX IF NOT EXISTS idx_prog_enrich_session_id ON progressive_enrichment_sessions(session_id);
CREATE INDEX IF NOT EXISTS idx_prog_enrich_website_url ON progressive_enrichment_sessions(website_url);
CREATE INDEX IF NOT EXISTS idx_prog_enrich_user_email ON progressive_enrichment_sessions(user_email);
CREATE INDEX IF NOT EXISTS idx_prog_enrich_status ON progressive_enrichment_sessions(status);
CREATE INDEX IF NOT EXISTS idx_prog_enrich_created_at ON progressive_enrichment_sessions(created_at DESC);


-- ============================================================================
-- 2. SOCIAL MEDIA VALIDATION CACHE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS social_media_cache (
    id SERIAL PRIMARY KEY,
    platform VARCHAR(20) NOT NULL,  -- instagram, tiktok, linkedin
    handle VARCHAR(255) NOT NULL,

    -- Validation result
    is_valid BOOLEAN NOT NULL,
    formatted_url TEXT,
    profile_data JSONB,  -- Additional profile data if available

    -- Cache metadata
    validated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '24 hours'),

    -- Constraints
    UNIQUE (platform, handle)
);

-- Add comment
COMMENT ON TABLE social_media_cache IS
'Caches social media handle validation results (24-hour TTL) to avoid repeated validation';

-- Create indexes separately with IF NOT EXISTS
CREATE INDEX IF NOT EXISTS idx_social_media_platform_handle ON social_media_cache(platform, handle);
CREATE INDEX IF NOT EXISTS idx_social_media_expires_at ON social_media_cache(expires_at);


-- ============================================================================
-- 3. ENRICHMENT FIELD SOURCES TABLE (Phase 3: Source Attribution)
-- ============================================================================

CREATE TABLE IF NOT EXISTS enrichment_field_sources (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES progressive_enrichment_sessions(session_id) ON DELETE CASCADE,

    -- Field identification
    field_name VARCHAR(100) NOT NULL,  -- company_name, industry, revenue, etc.
    field_value TEXT,

    -- Source information
    data_source VARCHAR(100) NOT NULL,  -- clearbit, google_places, gpt4o, metadata_scraping
    source_method VARCHAR(50),  -- api, scraping, ai_inference
    layer INTEGER NOT NULL CHECK (layer IN (1, 2, 3)),

    -- Quality metrics
    confidence_score DECIMAL(5, 2),  -- 0-100
    cost_usd DECIMAL(10, 6) DEFAULT 0.0,

    -- Metadata
    retrieved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add comment
COMMENT ON TABLE enrichment_field_sources IS
'Tracks source attribution for each enriched field (Phase 3: transparency)';

-- Create indexes with IF NOT EXISTS
CREATE INDEX IF NOT EXISTS idx_enrich_field_session_id ON enrichment_field_sources(session_id);
CREATE INDEX IF NOT EXISTS idx_enrich_field_name ON enrichment_field_sources(field_name);
CREATE INDEX IF NOT EXISTS idx_enrich_field_source ON enrichment_field_sources(data_source);
CREATE INDEX IF NOT EXISTS idx_enrich_field_layer ON enrichment_field_sources(layer);


-- ============================================================================
-- 4. ENRICHMENT API CALLS TABLE (Cost & Performance Tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS enrichment_api_calls (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES progressive_enrichment_sessions(session_id) ON DELETE CASCADE,

    -- API identification
    api_name VARCHAR(100) NOT NULL,  -- clearbit, google_places, openrouter, proxycurl
    endpoint VARCHAR(255),
    layer INTEGER CHECK (layer IN (1, 2, 3)),

    -- Request/Response
    request_params JSONB,
    response_data JSONB,
    response_time_ms INTEGER,

    -- Cost tracking
    cost_usd DECIMAL(10, 6) DEFAULT 0.0,
    credits_used INTEGER DEFAULT 0,

    -- Status
    status VARCHAR(50) DEFAULT 'success',  -- success, error, timeout, rate_limited
    error_message TEXT,

    -- Metadata
    called_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Add comment
COMMENT ON TABLE enrichment_api_calls IS
'Logs all external API calls for cost tracking and performance monitoring';

-- Create indexes with IF NOT EXISTS
CREATE INDEX IF NOT EXISTS idx_api_calls_session_id ON enrichment_api_calls(session_id);
CREATE INDEX IF NOT EXISTS idx_api_calls_api_name ON enrichment_api_calls(api_name);
CREATE INDEX IF NOT EXISTS idx_api_calls_layer ON enrichment_api_calls(layer);
CREATE INDEX IF NOT EXISTS idx_api_calls_status ON enrichment_api_calls(status);
CREATE INDEX IF NOT EXISTS idx_api_calls_called_at ON enrichment_api_calls(called_at DESC);


-- ============================================================================
-- 5. USER FIELD EDITS TABLE (Phase 6: ML Learning)
-- ============================================================================

CREATE TABLE IF NOT EXISTS user_field_edits (
    id SERIAL PRIMARY KEY,
    session_id UUID NOT NULL REFERENCES progressive_enrichment_sessions(session_id) ON DELETE CASCADE,

    -- Field identification
    field_name VARCHAR(100) NOT NULL,
    original_value TEXT,
    edited_value TEXT,

    -- Source of original value
    data_source VARCHAR(100),
    original_confidence DECIMAL(5, 2),

    -- Edit analysis
    edit_type VARCHAR(50),  -- correction, addition, removal, refinement
    edit_distance INTEGER,  -- Levenshtein distance
    edit_percentage DECIMAL(5, 2),  -- % change

    -- Metadata
    edited_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id INTEGER  -- Optional: if you want to track which user made edits
);

-- Add comment
COMMENT ON TABLE user_field_edits IS
'Tracks user edits to auto-filled fields for ML learning and confidence adjustment (Phase 6)';

-- Create indexes with IF NOT EXISTS
CREATE INDEX IF NOT EXISTS idx_user_edits_session_id ON user_field_edits(session_id);
CREATE INDEX IF NOT EXISTS idx_user_edits_field_name ON user_field_edits(field_name);
CREATE INDEX IF NOT EXISTS idx_user_edits_data_source ON user_field_edits(data_source);
CREATE INDEX IF NOT EXISTS idx_user_edits_edit_type ON user_field_edits(edit_type);
CREATE INDEX IF NOT EXISTS idx_user_edits_edited_at ON user_field_edits(edited_at DESC);


-- ============================================================================
-- 6. ENRICHMENT CACHE TABLE (30-day TTL)
-- ============================================================================

CREATE TABLE IF NOT EXISTS enrichment_cache (
    id SERIAL PRIMARY KEY,
    cache_key VARCHAR(255) NOT NULL UNIQUE,  -- MD5(website_url + cache_version)

    -- Cached enrichment data
    enrichment_data JSONB NOT NULL,
    confidence_scores JSONB,
    field_sources JSONB,

    -- Cost tracking (from cached result)
    total_cost_usd DECIMAL(10, 6),
    api_calls_count INTEGER,

    -- Cache metadata
    cache_version VARCHAR(50) DEFAULT 'v1',  -- Increment when enrichment logic changes
    hit_count INTEGER DEFAULT 0,  -- How many times this cache was used
    last_hit_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT (NOW() + INTERVAL '30 days')
);

-- Add comment
COMMENT ON TABLE enrichment_cache IS
'Caches enrichment results for 30 days to save costs and improve performance';

-- Create indexes with IF NOT EXISTS
CREATE INDEX IF NOT EXISTS idx_enrichment_cache_key ON enrichment_cache(cache_key);
CREATE INDEX IF NOT EXISTS idx_enrichment_cache_expires_at ON enrichment_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_enrichment_cache_created_at ON enrichment_cache(created_at DESC);


-- ============================================================================
-- 7. ANALYTICS VIEW (Phase 5: Dashboard Metrics)
-- ============================================================================

CREATE OR REPLACE VIEW enrichment_analytics_summary AS
SELECT
    DATE(created_at) as date,
    COUNT(*) as total_enrichments,
    SUM(total_cost_usd) as total_cost,
    AVG(total_duration_ms) as avg_duration_ms,
    COUNT(CASE WHEN status = 'complete' THEN 1 END) as successful_enrichments,
    COUNT(CASE WHEN status = 'error' THEN 1 END) as failed_enrichments,
    SUM(layer1_cost_usd) as layer1_cost,
    SUM(layer2_cost_usd) as layer2_cost,
    SUM(layer3_cost_usd) as layer3_cost
FROM progressive_enrichment_sessions
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

COMMENT ON VIEW enrichment_analytics_summary IS
'Daily enrichment analytics for the last 30 days (Phase 5: Analytics Dashboard)';


-- ============================================================================
-- 8. CACHE HIT RATE VIEW (Phase 5: Performance Metrics)
-- ============================================================================

CREATE OR REPLACE VIEW cache_performance_metrics AS
SELECT
    cache_version,
    COUNT(*) as total_cached_entries,
    SUM(hit_count) as total_cache_hits,
    AVG(hit_count) as avg_hits_per_entry,
    SUM(total_cost_usd) as total_cost_saved,
    COUNT(CASE WHEN expires_at > NOW() THEN 1 END) as active_entries,
    COUNT(CASE WHEN expires_at <= NOW() THEN 1 END) as expired_entries
FROM enrichment_cache
GROUP BY cache_version;

COMMENT ON VIEW cache_performance_metrics IS
'Cache hit rate and cost savings metrics (Phase 5: Analytics)';


-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Log migration completion
DO $$
BEGIN
    RAISE NOTICE 'Migration 002: Progressive Enrichment Tables created successfully!';
    RAISE NOTICE 'Tables: 5 tables + 2 views';
    RAISE NOTICE 'Indexes: 20+ indexes for performance';
    RAISE NOTICE 'Ready for Phases 1-6 of progressive enrichment system';
END $$;
