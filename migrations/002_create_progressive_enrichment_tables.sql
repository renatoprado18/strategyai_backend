-- ============================================================================
-- PROGRESSIVE ENRICHMENT SYSTEM - DATABASE SCHEMA
-- ============================================================================
-- Migration: 002_create_progressive_enrichment_tables.sql
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
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes for fast lookups
    INDEX idx_session_id (session_id),
    INDEX idx_website_url (website_url),
    INDEX idx_user_email (user_email),
    INDEX idx_status (status),
    INDEX idx_created_at (created_at DESC)
);

-- Add comment
COMMENT ON TABLE progressive_enrichment_sessions IS
'Tracks progressive enrichment sessions with 3-layer execution (Layer 1: instant, Layer 2: structured, Layer 3: AI)';


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

    -- Indexes
    UNIQUE (platform, handle),
    INDEX idx_platform_handle (platform, handle),
    INDEX idx_expires_at (expires_at)
);

-- Add comment
COMMENT ON TABLE social_media_cache IS
'Caches social media handle validation results (24-hour TTL) to avoid repeated validation';


-- ============================================================================
-- 3. FIELD VALIDATION HISTORY TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS field_validation_history (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES progressive_enrichment_sessions(session_id),
    field_name VARCHAR(100) NOT NULL,
    field_value TEXT,

    -- Validation result
    is_valid BOOLEAN NOT NULL,
    formatted_value TEXT,
    error_message TEXT,
    confidence DECIMAL(5, 2),  -- 0.00 to 100.00

    -- Metadata
    validated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Indexes
    INDEX idx_session_id (session_id),
    INDEX idx_field_name (field_name),
    INDEX idx_validated_at (validated_at DESC)
);

-- Add comment
COMMENT ON TABLE field_validation_history IS
'Tracks all field validation attempts for analytics and debugging';


-- ============================================================================
-- 4. AUTO-FILL SUGGESTIONS TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS auto_fill_suggestions (
    id SERIAL PRIMARY KEY,
    session_id UUID REFERENCES progressive_enrichment_sessions(session_id),
    field_name VARCHAR(100) NOT NULL,
    suggested_value TEXT,

    -- Suggestion metadata
    confidence DECIMAL(5, 2) NOT NULL,  -- 0.00 to 100.00
    source VARCHAR(255),  -- e.g., "Clearbit", "AI inference", "Metadata scraping"
    layer_number INTEGER,  -- 1, 2, or 3
    should_auto_fill BOOLEAN DEFAULT FALSE,  -- True if confidence > 85%

    -- User interaction
    was_accepted BOOLEAN,  -- Did user keep the suggestion?
    was_edited BOOLEAN,    -- Did user edit the suggestion?
    final_value TEXT,      -- Final value user submitted

    -- Metadata
    suggested_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_action_at TIMESTAMP WITH TIME ZONE,

    -- Indexes
    INDEX idx_session_id (session_id),
    INDEX idx_field_name (field_name),
    INDEX idx_confidence (confidence DESC),
    INDEX idx_layer_number (layer_number)
);

-- Add comment
COMMENT ON TABLE auto_fill_suggestions IS
'Tracks all auto-fill suggestions to measure accuracy and user acceptance';


-- ============================================================================
-- 5. ENRICHMENT SOURCE PERFORMANCE TABLE
-- ============================================================================

CREATE TABLE IF NOT EXISTS enrichment_source_performance (
    id SERIAL PRIMARY KEY,
    source_name VARCHAR(100) NOT NULL,
    layer_number INTEGER NOT NULL,  -- 1, 2, or 3

    -- Performance metrics
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    total_duration_ms BIGINT DEFAULT 0,
    total_cost_usd DECIMAL(10, 6) DEFAULT 0.0,

    -- Data quality metrics
    avg_confidence DECIMAL(5, 2),
    fields_populated_count INTEGER DEFAULT 0,

    -- Time window
    date DATE NOT NULL,

    -- Indexes
    UNIQUE (source_name, layer_number, date),
    INDEX idx_source_name (source_name),
    INDEX idx_layer_number (layer_number),
    INDEX idx_date (date DESC)
);

-- Add comment
COMMENT ON TABLE enrichment_source_performance IS
'Daily aggregated performance metrics for each enrichment source';


-- ============================================================================
-- 6. CREATE UPDATED_AT TRIGGER
-- ============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply trigger to progressive_enrichment_sessions
CREATE TRIGGER update_progressive_enrichment_sessions_updated_at
    BEFORE UPDATE ON progressive_enrichment_sessions
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();


-- ============================================================================
-- 7. CREATE CACHE CLEANUP FUNCTIONS
-- ============================================================================

-- Function to clean up expired social media cache
CREATE OR REPLACE FUNCTION cleanup_expired_social_media_cache()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM social_media_cache
    WHERE expires_at < NOW();

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Function to clean up old enrichment sessions (> 90 days)
CREATE OR REPLACE FUNCTION cleanup_old_enrichment_sessions()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM progressive_enrichment_sessions
    WHERE created_at < (NOW() - INTERVAL '90 days');

    GET DIAGNOSTICS deleted_count = ROW_COUNT;

    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;


-- ============================================================================
-- 8. CREATE VIEWS FOR ANALYTICS
-- ============================================================================

-- View: Enrichment success rate by layer
CREATE OR REPLACE VIEW enrichment_success_rate_by_layer AS
SELECT
    layer_number,
    COUNT(*) as total_attempts,
    SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) as successful,
    ROUND(
        100.0 * SUM(CASE WHEN status = 'complete' THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) as success_rate_pct,
    AVG(total_duration_ms) as avg_duration_ms,
    AVG(total_cost_usd) as avg_cost_usd
FROM (
    SELECT
        CASE
            WHEN status = 'layer1_complete' THEN 1
            WHEN status = 'layer2_complete' THEN 2
            WHEN status = 'complete' THEN 3
            ELSE 0
        END as layer_number,
        status,
        total_duration_ms,
        total_cost_usd
    FROM progressive_enrichment_sessions
    WHERE created_at > (NOW() - INTERVAL '30 days')
) AS layer_stats
WHERE layer_number > 0
GROUP BY layer_number
ORDER BY layer_number;

-- View: Auto-fill acceptance rate
CREATE OR REPLACE VIEW auto_fill_acceptance_rate AS
SELECT
    field_name,
    COUNT(*) as total_suggestions,
    SUM(CASE WHEN was_accepted THEN 1 ELSE 0 END) as accepted,
    SUM(CASE WHEN was_edited THEN 1 ELSE 0 END) as edited,
    ROUND(
        100.0 * SUM(CASE WHEN was_accepted THEN 1 ELSE 0 END) / COUNT(*),
        2
    ) as acceptance_rate_pct,
    AVG(confidence) as avg_confidence
FROM auto_fill_suggestions
WHERE suggested_at > (NOW() - INTERVAL '30 days')
GROUP BY field_name
ORDER BY acceptance_rate_pct DESC;


-- ============================================================================
-- 9. GRANT PERMISSIONS (adjust as needed)
-- ============================================================================

-- Grant access to application role (replace 'app_role' with your actual role)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_role;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_role;
-- GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO app_role;


-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================

-- Log migration
DO $$
BEGIN
    RAISE NOTICE 'Migration 002: Progressive enrichment tables created successfully';
    RAISE NOTICE 'Tables: progressive_enrichment_sessions, social_media_cache, field_validation_history, auto_fill_suggestions, enrichment_source_performance';
    RAISE NOTICE 'Views: enrichment_success_rate_by_layer, auto_fill_acceptance_rate';
END $$;
