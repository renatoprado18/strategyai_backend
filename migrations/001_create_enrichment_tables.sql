-- IMENSIAH Data Enrichment System
-- Database Migration: Create enrichment_results and enrichment_audit_log tables
-- Version: 1.0.0
-- Created: 2025-01-09

-- =============================================================================
-- Table: enrichment_results
-- Purpose: Store enrichment results with 30-day TTL and full source attribution
-- =============================================================================

CREATE TABLE IF NOT EXISTS enrichment_results (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Input data
    website TEXT NOT NULL,
    domain TEXT NOT NULL,
    cache_key TEXT UNIQUE NOT NULL,

    -- Quick enrichment (sync - 2-3s)
    quick_data JSONB,
    quick_completed_at TIMESTAMPTZ,
    quick_duration_ms INTEGER,

    -- Deep enrichment (async - 30s+)
    deep_data JSONB,
    deep_completed_at TIMESTAMPTZ,
    deep_duration_ms INTEGER,

    -- Source attribution (field → source mapping)
    -- Example: {"company_name": "clearbit", "cnpj": "receita_ws", "location": "google_places"}
    source_attribution JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Quality metrics
    completeness_score FLOAT CHECK (completeness_score >= 0 AND completeness_score <= 100),
    confidence_score FLOAT CHECK (confidence_score >= 0 AND confidence_score <= 100),
    data_quality_tier TEXT CHECK (data_quality_tier IN ('minimal', 'moderate', 'high', 'excellent')),

    -- Cost tracking
    total_cost_usd DECIMAL(10,4) DEFAULT 0.0 CHECK (total_cost_usd >= 0),
    sources_called JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Example: [{"name": "clearbit", "success": true, "cost": 0.10, "duration_ms": 1200, "cached": false}]

    -- Caching metrics
    cache_hits INTEGER DEFAULT 0 CHECK (cache_hits >= 0),
    cache_savings_usd DECIMAL(10,4) DEFAULT 0.0 CHECK (cache_savings_usd >= 0),
    expires_at TIMESTAMPTZ NOT NULL,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_enrichment_cache_key ON enrichment_results(cache_key);
CREATE INDEX IF NOT EXISTS idx_enrichment_domain ON enrichment_results(domain);
CREATE INDEX IF NOT EXISTS idx_enrichment_expires ON enrichment_results(expires_at);
CREATE INDEX IF NOT EXISTS idx_enrichment_created ON enrichment_results(created_at DESC);

-- Comments for documentation
COMMENT ON TABLE enrichment_results IS 'Stores company enrichment data from multiple sources with 30-day TTL';
COMMENT ON COLUMN enrichment_results.cache_key IS 'Unique cache key generated from domain and enrichment type';
COMMENT ON COLUMN enrichment_results.source_attribution IS 'Maps each enriched field to its data source';
COMMENT ON COLUMN enrichment_results.sources_called IS 'Array of all API calls made during enrichment';
COMMENT ON COLUMN enrichment_results.expires_at IS '30 days from creation - cache TTL';

-- =============================================================================
-- Table: enrichment_audit_log
-- Purpose: Complete audit trail of all API calls for transparency and debugging
-- =============================================================================

CREATE TABLE IF NOT EXISTS enrichment_audit_log (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Foreign key to enrichment result
    enrichment_id BIGINT REFERENCES enrichment_results(id) ON DELETE CASCADE,

    -- Source details
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK (source_type IN ('api', 'cache', 'fallback', 'error')),

    -- Request/response data (for full transparency)
    request_params JSONB,
    response_data JSONB,
    response_status INTEGER,

    -- Timing & cost
    duration_ms INTEGER CHECK (duration_ms >= 0),
    cost_usd DECIMAL(10,4) DEFAULT 0.0 CHECK (cost_usd >= 0),

    -- Error tracking
    success BOOLEAN NOT NULL,
    error_message TEXT,
    error_type TEXT,  -- "timeout", "rate_limit", "auth", "parse", "network"

    -- Circuit breaker state
    circuit_breaker_state TEXT CHECK (circuit_breaker_state IN ('closed', 'open', 'half_open')),

    -- Timestamp
    called_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes for audit trail queries
CREATE INDEX IF NOT EXISTS idx_audit_enrichment ON enrichment_audit_log(enrichment_id);
CREATE INDEX IF NOT EXISTS idx_audit_source ON enrichment_audit_log(source_name);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON enrichment_audit_log(called_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_success ON enrichment_audit_log(success);

-- Comments for documentation
COMMENT ON TABLE enrichment_audit_log IS 'Complete audit trail of all enrichment API calls for transparency';
COMMENT ON COLUMN enrichment_audit_log.response_data IS 'Full API response stored for debugging (can be large)';
COMMENT ON COLUMN enrichment_audit_log.source_type IS 'Whether data came from API call, cache hit, or fallback';

-- =============================================================================
-- Extension: Update submissions table to link to enrichment
-- =============================================================================

-- Add enrichment_id column to submissions table if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'submissions' AND column_name = 'enrichment_id'
    ) THEN
        ALTER TABLE submissions ADD COLUMN enrichment_id BIGINT REFERENCES enrichment_results(id);
    END IF;
END $$;

-- Add enrichment_status column to submissions table if not exists
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'submissions' AND column_name = 'enrichment_status'
    ) THEN
        ALTER TABLE submissions ADD COLUMN enrichment_status TEXT
            CHECK (enrichment_status IN ('pending', 'quick_done', 'deep_done', 'failed'));
    END IF;
END $$;

-- Create index on enrichment_id
CREATE INDEX IF NOT EXISTS idx_submissions_enrichment ON submissions(enrichment_id);

-- =============================================================================
-- Functions: Auto-update timestamps
-- =============================================================================

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for enrichment_results
DROP TRIGGER IF EXISTS update_enrichment_results_updated_at ON enrichment_results;
CREATE TRIGGER update_enrichment_results_updated_at
    BEFORE UPDATE ON enrichment_results
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Views: Useful aggregations for admin dashboard
-- =============================================================================

-- View: Enrichment statistics
CREATE OR REPLACE VIEW enrichment_statistics AS
SELECT
    COUNT(*) as total_enrichments,
    COUNT(*) FILTER (WHERE quick_completed_at IS NOT NULL) as quick_completed,
    COUNT(*) FILTER (WHERE deep_completed_at IS NOT NULL) as deep_completed,
    AVG(completeness_score) as avg_completeness,
    AVG(confidence_score) as avg_confidence,
    AVG(quick_duration_ms) as avg_quick_duration_ms,
    AVG(deep_duration_ms) as avg_deep_duration_ms,
    SUM(total_cost_usd) as total_cost,
    SUM(cache_savings_usd) as total_savings,
    AVG(cache_hits) as avg_cache_hits,
    COUNT(*) FILTER (WHERE expires_at > NOW()) as active_cache_entries,
    COUNT(*) FILTER (WHERE expires_at <= NOW()) as expired_cache_entries
FROM enrichment_results;

COMMENT ON VIEW enrichment_statistics IS 'Aggregated statistics for admin dashboard overview';

-- View: Source health statistics
CREATE OR REPLACE VIEW source_health_statistics AS
SELECT
    source_name,
    COUNT(*) as total_calls,
    COUNT(*) FILTER (WHERE success = true) as successful_calls,
    COUNT(*) FILTER (WHERE success = false) as failed_calls,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE success = true) / NULLIF(COUNT(*), 0),
        2
    ) as success_rate_percent,
    AVG(duration_ms) FILTER (WHERE success = true) as avg_duration_ms,
    SUM(cost_usd) as total_cost_usd,
    MAX(called_at) as last_called_at,
    -- Get most recent circuit breaker state
    (SELECT circuit_breaker_state
     FROM enrichment_audit_log eal2
     WHERE eal2.source_name = eal.source_name
     ORDER BY called_at DESC
     LIMIT 1) as current_circuit_state
FROM enrichment_audit_log eal
GROUP BY source_name
ORDER BY total_calls DESC;

COMMENT ON VIEW source_health_statistics IS 'Per-source health metrics for admin dashboard';

-- =============================================================================
-- Sample data comments and usage notes
-- =============================================================================

/*
USAGE NOTES:

1. Cache Key Generation:
   - Format: "enrichment:{type}:{domain}:{hash}"
   - Example: "enrichment:quick:techstart.com:a3f2b1c4d5e6"

2. Source Attribution Format:
   {
     "company_name": "clearbit",
     "cnpj": "receita_ws",
     "employee_count": "clearbit",
     "location": "google_places",
     "website_tech": "metadata"
   }

3. Sources Called Format:
   [
     {
       "name": "clearbit",
       "success": true,
       "cost": 0.10,
       "duration_ms": 1200,
       "cached": false
     },
     {
       "name": "receita_ws",
       "success": true,
       "cost": 0.00,
       "duration_ms": 2800,
       "cached": false
     }
   ]

4. TTL Management:
   - Default TTL: 30 days from creation
   - Set expires_at = NOW() + INTERVAL '30 days'
   - Cleanup: DELETE FROM enrichment_results WHERE expires_at < NOW()

5. Admin Dashboard Queries:
   - Overview: SELECT * FROM enrichment_statistics;
   - Source Health: SELECT * FROM source_health_statistics;
   - Recent Enrichments:
     SELECT * FROM enrichment_results
     ORDER BY created_at DESC LIMIT 100;
*/
