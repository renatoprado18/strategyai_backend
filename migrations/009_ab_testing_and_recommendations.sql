-- =============================================================================
-- PHASE 7: A/B Testing & Recommendations Engine
-- Purpose: Test enrichment strategies and recommend optimal configurations
-- Created: 2025-01-09
-- Version: 1.0.0
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Table: ab_test_variants
-- Purpose: Define enrichment source combinations to test
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ab_test_variants (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Variant identification
    variant_key TEXT UNIQUE NOT NULL,  -- e.g., "full_stack", "free_only", "hybrid"
    variant_name TEXT NOT NULL,        -- e.g., "Full Stack (All Sources)"
    description TEXT,

    -- Sources configuration
    -- JSON array of source names to use
    -- Example: ["clearbit", "google_places", "proxycurl", "receita_ws", "metadata", "ip_api"]
    sources_config JSONB NOT NULL,

    -- Expected metrics (for comparison)
    expected_cost_usd DECIMAL(10,4),
    expected_completeness FLOAT CHECK (expected_completeness >= 0 AND expected_completeness <= 100),

    -- Test control
    is_active BOOLEAN DEFAULT true,
    traffic_allocation FLOAT DEFAULT 33.33 CHECK (traffic_allocation >= 0 AND traffic_allocation <= 100),

    -- Metadata
    created_by TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Sample variants
INSERT INTO ab_test_variants (variant_key, variant_name, description, sources_config, expected_cost_usd, expected_completeness)
VALUES
    (
        'full_stack',
        'Full Stack (High Quality)',
        'All sources: Clearbit + Google Places + Proxycurl + ReceitaWS + Metadata + IP API',
        '["clearbit", "google_places", "proxycurl", "receita_ws", "metadata", "ip_api"]'::jsonb,
        0.15,
        94.0
    ),
    (
        'free_only',
        'Free Only (Zero Cost)',
        'Only free sources: Metadata + IP API',
        '["metadata", "ip_api"]'::jsonb,
        0.00,
        45.0
    ),
    (
        'hybrid',
        'Hybrid (Balanced)',
        'Free sources + OpenRouter LLM enrichment: Metadata + IP API + OpenRouter',
        '["metadata", "ip_api", "openrouter"]'::jsonb,
        0.05,
        78.0
    )
ON CONFLICT (variant_key) DO NOTHING;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ab_variants_active ON ab_test_variants(is_active) WHERE is_active = true;

-- Comments
COMMENT ON TABLE ab_test_variants IS 'A/B test variant definitions with source configurations';
COMMENT ON COLUMN ab_test_variants.sources_config IS 'JSON array of data source names to use for this variant';
COMMENT ON COLUMN ab_test_variants.traffic_allocation IS 'Percentage of traffic to assign to this variant';

-- -----------------------------------------------------------------------------
-- Table: ab_test_assignments
-- Purpose: Track which variant each session/enrichment was assigned
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ab_test_assignments (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Assignment
    session_id TEXT NOT NULL,           -- From user session or generated
    enrichment_id BIGINT REFERENCES enrichment_results(id) ON DELETE CASCADE,
    variant_id BIGINT NOT NULL REFERENCES ab_test_variants(id) ON DELETE CASCADE,

    -- Timing
    assigned_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraint: One assignment per enrichment
    CONSTRAINT unique_enrichment_assignment UNIQUE (enrichment_id)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ab_assignments_session ON ab_test_assignments(session_id);
CREATE INDEX IF NOT EXISTS idx_ab_assignments_variant ON ab_test_assignments(variant_id);
CREATE INDEX IF NOT EXISTS idx_ab_assignments_enrichment ON ab_test_assignments(enrichment_id);
CREATE INDEX IF NOT EXISTS idx_ab_assignments_timestamp ON ab_test_assignments(assigned_at DESC);

-- Comments
COMMENT ON TABLE ab_test_assignments IS 'Tracks which A/B test variant each enrichment was assigned to';
COMMENT ON COLUMN ab_test_assignments.session_id IS 'Session identifier for consistent variant assignment';

-- -----------------------------------------------------------------------------
-- Table: ab_test_results
-- Purpose: Aggregated metrics per variant for fast dashboard queries
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ab_test_results (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Variant reference
    variant_id BIGINT NOT NULL REFERENCES ab_test_variants(id) ON DELETE CASCADE,

    -- Metrics tracking
    metric_name TEXT NOT NULL,  -- "cost_per_enrichment", "avg_completeness", "avg_confidence", etc.
    metric_value NUMERIC NOT NULL,

    -- Statistical data
    sample_size INTEGER NOT NULL CHECK (sample_size >= 0),
    std_dev NUMERIC,            -- Standard deviation
    confidence_interval_lower NUMERIC,
    confidence_interval_upper NUMERIC,

    -- Time window
    time_window_start TIMESTAMPTZ NOT NULL,
    time_window_end TIMESTAMPTZ NOT NULL,

    -- Timestamps
    calculated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,

    -- Constraint: One metric per variant per time window
    CONSTRAINT unique_variant_metric_window
        UNIQUE (variant_id, metric_name, time_window_start, time_window_end)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ab_results_variant ON ab_test_results(variant_id);
CREATE INDEX IF NOT EXISTS idx_ab_results_metric ON ab_test_results(metric_name);
CREATE INDEX IF NOT EXISTS idx_ab_results_timestamp ON ab_test_results(calculated_at DESC);

-- Comments
COMMENT ON TABLE ab_test_results IS 'Aggregated A/B test metrics per variant for dashboard visualization';
COMMENT ON COLUMN ab_test_results.metric_name IS 'Name of metric: cost_per_enrichment, avg_completeness, avg_confidence, user_edit_rate, etc.';
COMMENT ON COLUMN ab_test_results.sample_size IS 'Number of enrichments included in this metric calculation';

-- -----------------------------------------------------------------------------
-- Table: recommendations_history
-- Purpose: Track recommended strategies and their actual performance
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS recommendations_history (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Input constraints
    budget_per_enrichment DECIMAL(10,4) NOT NULL,
    min_confidence_required FLOAT CHECK (min_confidence_required >= 0 AND min_confidence_required <= 100),
    min_completeness_required FLOAT CHECK (min_completeness_required >= 0 AND min_completeness_required <= 100),

    -- Recommendation
    recommended_variant_id BIGINT REFERENCES ab_test_variants(id),
    recommended_sources JSONB NOT NULL,

    -- Predictions
    predicted_cost DECIMAL(10,4),
    predicted_completeness FLOAT,
    predicted_confidence FLOAT,
    prediction_confidence_interval JSONB,  -- {"lower": 0.7, "upper": 0.9}

    -- Actual performance (NULL until test completes)
    actual_cost DECIMAL(10,4),
    actual_completeness FLOAT,
    actual_confidence FLOAT,
    actual_sample_size INTEGER,

    -- Recommendation metadata
    recommendation_algorithm TEXT,  -- "pareto_optimization", "cost_minimization", "quality_maximization"
    recommendation_rationale TEXT,

    -- Timestamps
    recommended_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    performance_measured_at TIMESTAMPTZ,

    -- Status
    is_implemented BOOLEAN DEFAULT false,
    implementation_notes TEXT
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_recommendations_variant ON recommendations_history(recommended_variant_id);
CREATE INDEX IF NOT EXISTS idx_recommendations_timestamp ON recommendations_history(recommended_at DESC);
CREATE INDEX IF NOT EXISTS idx_recommendations_implemented ON recommendations_history(is_implemented);

-- Comments
COMMENT ON TABLE recommendations_history IS 'History of strategy recommendations with predicted vs actual performance';
COMMENT ON COLUMN recommendations_history.recommendation_algorithm IS 'Algorithm used: pareto_optimization, cost_minimization, or quality_maximization';
COMMENT ON COLUMN recommendations_history.prediction_confidence_interval IS 'JSON with lower and upper bounds for prediction accuracy';

-- -----------------------------------------------------------------------------
-- Table: ab_test_events
-- Purpose: Track user interactions and behavior per variant
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS ab_test_events (
    -- Primary key
    id BIGSERIAL PRIMARY KEY,

    -- Event tracking
    enrichment_id BIGINT NOT NULL REFERENCES enrichment_results(id) ON DELETE CASCADE,
    variant_id BIGINT NOT NULL REFERENCES ab_test_variants(id) ON DELETE CASCADE,

    -- Event type
    event_type TEXT NOT NULL,  -- "form_completed", "user_edited", "data_accepted", "time_to_autofill"
    event_value NUMERIC,       -- Generic numeric value (e.g., seconds for timing, 1/0 for boolean)
    event_metadata JSONB,      -- Additional event data

    -- Timestamp
    occurred_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ab_events_enrichment ON ab_test_events(enrichment_id);
CREATE INDEX IF NOT EXISTS idx_ab_events_variant ON ab_test_events(variant_id);
CREATE INDEX IF NOT EXISTS idx_ab_events_type ON ab_test_events(event_type);
CREATE INDEX IF NOT EXISTS idx_ab_events_timestamp ON ab_test_events(occurred_at DESC);

-- Comments
COMMENT ON TABLE ab_test_events IS 'Tracks user behavior events for A/B test analysis';
COMMENT ON COLUMN ab_test_events.event_type IS 'Type of event: form_completed, user_edited, data_accepted, time_to_autofill';

-- -----------------------------------------------------------------------------
-- Views: Analytics for A/B Test Dashboard
-- -----------------------------------------------------------------------------

-- View: Variant performance comparison
CREATE OR REPLACE VIEW ab_test_variant_performance AS
SELECT
    v.id as variant_id,
    v.variant_key,
    v.variant_name,
    v.sources_config,
    v.expected_cost_usd,
    v.expected_completeness,

    -- Sample size
    COUNT(DISTINCT a.enrichment_id) as sample_size,

    -- Cost metrics
    AVG(e.total_cost_usd) as avg_cost_per_enrichment,
    SUM(e.total_cost_usd) as total_cost,
    STDDEV(e.total_cost_usd) as cost_std_dev,

    -- Quality metrics
    AVG(e.completeness_score) as avg_completeness,
    AVG(e.confidence_score) as avg_confidence,
    STDDEV(e.completeness_score) as completeness_std_dev,

    -- Quality tier distribution
    COUNT(*) FILTER (WHERE e.data_quality_tier = 'excellent') as excellent_count,
    COUNT(*) FILTER (WHERE e.data_quality_tier = 'high') as high_count,
    COUNT(*) FILTER (WHERE e.data_quality_tier = 'moderate') as moderate_count,
    COUNT(*) FILTER (WHERE e.data_quality_tier = 'minimal') as minimal_count,

    -- Performance metrics
    AVG(e.deep_duration_ms) as avg_duration_ms,

    -- User interaction metrics (from events)
    (SELECT COUNT(*) FROM ab_test_events evt
     WHERE evt.variant_id = v.id AND evt.event_type = 'user_edited') as user_edit_count,
    (SELECT AVG(event_value) FROM ab_test_events evt
     WHERE evt.variant_id = v.id AND evt.event_type = 'time_to_autofill') as avg_time_to_autofill_ms,
    (SELECT COUNT(*) FROM ab_test_events evt
     WHERE evt.variant_id = v.id AND evt.event_type = 'form_completed') as form_completion_count,

    -- Calculated metrics
    ROUND(
        100.0 * (AVG(e.completeness_score) / NULLIF(AVG(e.total_cost_usd), 0)),
        2
    ) as quality_per_dollar,

    -- Timestamps
    MIN(a.assigned_at) as first_assignment,
    MAX(a.assigned_at) as last_assignment

FROM ab_test_variants v
LEFT JOIN ab_test_assignments a ON v.id = a.variant_id
LEFT JOIN enrichment_results e ON a.enrichment_id = e.id
WHERE v.is_active = true
GROUP BY v.id, v.variant_key, v.variant_name, v.sources_config, v.expected_cost_usd, v.expected_completeness;

COMMENT ON VIEW ab_test_variant_performance IS 'Real-time A/B test variant performance comparison for dashboard';

-- View: Test winner determination (statistical significance)
CREATE OR REPLACE VIEW ab_test_winner_analysis AS
SELECT
    v1.variant_key as variant_a,
    v2.variant_key as variant_b,

    -- Completeness comparison
    AVG(e1.completeness_score) as avg_completeness_a,
    AVG(e2.completeness_score) as avg_completeness_b,
    AVG(e1.completeness_score) - AVG(e2.completeness_score) as completeness_diff,

    -- Cost comparison
    AVG(e1.total_cost_usd) as avg_cost_a,
    AVG(e2.total_cost_usd) as avg_cost_b,
    AVG(e1.total_cost_usd) - AVG(e2.total_cost_usd) as cost_diff,

    -- Sample sizes
    COUNT(DISTINCT e1.id) as sample_size_a,
    COUNT(DISTINCT e2.id) as sample_size_b,

    -- ROI metric (quality per dollar)
    (AVG(e1.completeness_score) / NULLIF(AVG(e1.total_cost_usd), 0)) as roi_a,
    (AVG(e2.completeness_score) / NULLIF(AVG(e2.total_cost_usd), 0)) as roi_b

FROM ab_test_variants v1
CROSS JOIN ab_test_variants v2
LEFT JOIN ab_test_assignments a1 ON v1.id = a1.variant_id
LEFT JOIN ab_test_assignments a2 ON v2.id = a2.variant_id
LEFT JOIN enrichment_results e1 ON a1.enrichment_id = e1.id
LEFT JOIN enrichment_results e2 ON a2.enrichment_id = e2.id
WHERE v1.id < v2.id  -- Avoid duplicate comparisons
  AND v1.is_active = true
  AND v2.is_active = true
GROUP BY v1.variant_key, v2.variant_key;

COMMENT ON VIEW ab_test_winner_analysis IS 'Pairwise variant comparison for statistical significance testing';

-- -----------------------------------------------------------------------------
-- Functions: Helper functions for A/B testing
-- -----------------------------------------------------------------------------

-- Function: Assign variant based on session_id hash
CREATE OR REPLACE FUNCTION assign_ab_test_variant(
    p_session_id TEXT,
    p_enrichment_id BIGINT
) RETURNS TEXT AS $$
DECLARE
    v_variant_id BIGINT;
    v_variant_key TEXT;
    v_active_variants BIGINT[];
    v_hash_value INTEGER;
    v_variant_index INTEGER;
BEGIN
    -- Get all active variants
    SELECT ARRAY_AGG(id) INTO v_active_variants
    FROM ab_test_variants
    WHERE is_active = true
    ORDER BY id;

    -- If no active variants, return NULL
    IF v_active_variants IS NULL OR array_length(v_active_variants, 1) = 0 THEN
        RETURN NULL;
    END IF;

    -- Hash session_id to get consistent assignment
    v_hash_value := ABS(hashtext(p_session_id));
    v_variant_index := (v_hash_value % array_length(v_active_variants, 1)) + 1;

    -- Get variant_id
    v_variant_id := v_active_variants[v_variant_index];

    -- Insert assignment
    INSERT INTO ab_test_assignments (session_id, enrichment_id, variant_id)
    VALUES (p_session_id, p_enrichment_id, v_variant_id)
    ON CONFLICT (enrichment_id) DO NOTHING;

    -- Get variant key
    SELECT variant_key INTO v_variant_key
    FROM ab_test_variants
    WHERE id = v_variant_id;

    RETURN v_variant_key;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION assign_ab_test_variant IS 'Consistently assigns A/B test variant based on session_id hash';

-- Function: Calculate aggregated metrics for time window
CREATE OR REPLACE FUNCTION calculate_ab_test_metrics(
    p_variant_id BIGINT,
    p_time_window_start TIMESTAMPTZ,
    p_time_window_end TIMESTAMPTZ
) RETURNS void AS $$
DECLARE
    v_metric RECORD;
BEGIN
    -- Cost per enrichment
    INSERT INTO ab_test_results (variant_id, metric_name, metric_value, sample_size, std_dev, time_window_start, time_window_end)
    SELECT
        p_variant_id,
        'cost_per_enrichment',
        AVG(e.total_cost_usd),
        COUNT(*),
        STDDEV(e.total_cost_usd),
        p_time_window_start,
        p_time_window_end
    FROM ab_test_assignments a
    JOIN enrichment_results e ON a.enrichment_id = e.id
    WHERE a.variant_id = p_variant_id
      AND a.assigned_at >= p_time_window_start
      AND a.assigned_at < p_time_window_end
    ON CONFLICT (variant_id, metric_name, time_window_start, time_window_end)
    DO UPDATE SET
        metric_value = EXCLUDED.metric_value,
        sample_size = EXCLUDED.sample_size,
        std_dev = EXCLUDED.std_dev,
        calculated_at = NOW();

    -- Average completeness
    INSERT INTO ab_test_results (variant_id, metric_name, metric_value, sample_size, std_dev, time_window_start, time_window_end)
    SELECT
        p_variant_id,
        'avg_completeness',
        AVG(e.completeness_score),
        COUNT(*),
        STDDEV(e.completeness_score),
        p_time_window_start,
        p_time_window_end
    FROM ab_test_assignments a
    JOIN enrichment_results e ON a.enrichment_id = e.id
    WHERE a.variant_id = p_variant_id
      AND a.assigned_at >= p_time_window_start
      AND a.assigned_at < p_time_window_end
    ON CONFLICT (variant_id, metric_name, time_window_start, time_window_end)
    DO UPDATE SET
        metric_value = EXCLUDED.metric_value,
        sample_size = EXCLUDED.sample_size,
        std_dev = EXCLUDED.std_dev,
        calculated_at = NOW();

    -- Average confidence
    INSERT INTO ab_test_results (variant_id, metric_name, metric_value, sample_size, std_dev, time_window_start, time_window_end)
    SELECT
        p_variant_id,
        'avg_confidence',
        AVG(e.confidence_score),
        COUNT(*),
        STDDEV(e.confidence_score),
        p_time_window_start,
        p_time_window_end
    FROM ab_test_assignments a
    JOIN enrichment_results e ON a.enrichment_id = e.id
    WHERE a.variant_id = p_variant_id
      AND a.assigned_at >= p_time_window_start
      AND a.assigned_at < p_time_window_end
    ON CONFLICT (variant_id, metric_name, time_window_start, time_window_end)
    DO UPDATE SET
        metric_value = EXCLUDED.metric_value,
        sample_size = EXCLUDED.sample_size,
        std_dev = EXCLUDED.std_dev,
        calculated_at = NOW();

    -- User edit rate
    INSERT INTO ab_test_results (variant_id, metric_name, metric_value, sample_size, time_window_start, time_window_end)
    SELECT
        p_variant_id,
        'user_edit_rate',
        100.0 * COUNT(*) FILTER (WHERE evt.event_type = 'user_edited') / NULLIF(COUNT(DISTINCT a.enrichment_id), 0),
        COUNT(DISTINCT a.enrichment_id),
        p_time_window_start,
        p_time_window_end
    FROM ab_test_assignments a
    LEFT JOIN ab_test_events evt ON a.enrichment_id = evt.enrichment_id
    WHERE a.variant_id = p_variant_id
      AND a.assigned_at >= p_time_window_start
      AND a.assigned_at < p_time_window_end
    ON CONFLICT (variant_id, metric_name, time_window_start, time_window_end)
    DO UPDATE SET
        metric_value = EXCLUDED.metric_value,
        sample_size = EXCLUDED.sample_size,
        calculated_at = NOW();

END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_ab_test_metrics IS 'Calculates and stores aggregated A/B test metrics for a variant and time window';

-- -----------------------------------------------------------------------------
-- Triggers: Auto-update timestamps
-- -----------------------------------------------------------------------------

CREATE TRIGGER update_ab_variants_updated_at
    BEFORE UPDATE ON ab_test_variants
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- End of Migration 009
-- =============================================================================
