# Phase 7 Architecture: A/B Testing & Recommendations Engine

## Executive Summary

**Phase 7** introduces intelligent optimization to the IMENSIAH enrichment system through A/B testing and automated recommendations. The system tests different enrichment source combinations to discover the optimal cost-quality balance, then recommends strategies based on user constraints.

**Key Capabilities**:
- Test 3+ enrichment strategies simultaneously (full/free/hybrid)
- Track 8+ performance metrics per variant
- Recommend optimal source combinations based on budget and quality requirements
- Predict costs and quality before enrichment
- Automatic winner declaration based on statistical significance

---

## Business Value

### For Data-Driven Decision Making
- **Cost Optimization**: Discover which paid sources provide the best ROI
- **Quality Assurance**: Test whether free sources meet quality requirements
- **Risk Mitigation**: Validate new sources before full rollout
- **Budget Flexibility**: Adapt enrichment strategy to changing budgets

### ROI Example
**Scenario**: 1,000 enrichments/month

| Strategy | Cost/Enrichment | Monthly Cost | Avg Completeness | Recommendation |
|----------|-----------------|--------------|------------------|----------------|
| Full Stack | $0.15 | $150 | 94% | High-value leads only |
| Hybrid | $0.05 | $50 | 78% | Best balance ✓ |
| Free Only | $0.00 | $0 | 52% | Budget-constrained |

**Insight**: Hybrid saves $100/month (67% cost reduction) with only 16% quality drop.

---

## System Architecture

### High-Level Data Flow

```
User Request → Variant Assignment → Enrichment → Metrics Collection → Analysis → Recommendation
     ↓               ↓                    ↓              ↓                ↓            ↓
  Session ID    Hash % 3 = 0,1,2    Sources Config   Track Cost     Statistical   Optimal
                A/B/C Variant        Execute          Track Quality   Analysis     Strategy
```

### Component Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    PHASE 7: A/B TESTING LAYER                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────┐    ┌──────────────────┐   ┌──────────────┐ │
│  │ Variant        │────│ Metrics          │───│ Recommender  │ │
│  │ Assigner       │    │ Collector        │   │ Engine       │ │
│  └────────────────┘    └──────────────────┘   └──────────────┘ │
│          ↓                      ↓                      ↓         │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │              A/B Test Database Tables                      │ │
│  │  • ab_test_variants                                        │ │
│  │  • ab_test_assignments                                     │ │
│  │  • ab_test_results (aggregated metrics)                    │ │
│  │  • recommendations_history                                 │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
└──────────────────────────┬───────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────────────┐
│              EXISTING: ENRICHMENT ORCHESTRATOR                   │
│                                                                  │
│  Variant A: Full Stack   │  Variant B: Free Only  │  Variant C  │
│  • Clearbit              │  • Metadata            │  • Metadata │
│  • Google Places         │  • IP API              │  • IP API   │
│  • Proxycurl             │                        │  • OpenRouter│
│  • ReceitaWS             │                        │             │
│  • Metadata              │                        │             │
│  • IP API                │                        │             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Database Schema Design

### Migration 009: A/B Testing Tables

**File**: `migrations/009_ab_testing_and_recommendations.sql`

```sql
-- =============================================================================
-- PHASE 7: A/B Testing & Recommendations Engine
-- Purpose: Test enrichment strategies and recommend optimal configurations
-- Created: 2025-01-09
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
```

---

## API Design

### Public Endpoints (Modified)

#### POST `/api/enrichment/submit`
**Enhancement**: Now includes A/B test variant assignment

**Request** (unchanged):
```json
{
  "email": "contato@techstart.com.br",
  "company_website": "https://techstart.com.br"
}
```

**Response** (with A/B test info):
```json
{
  "success": true,
  "enrichment_id": 123,
  "ab_test_variant": "hybrid",
  "data": { /* quick enrichment data */ },
  "completeness_score": 78.0,
  "confidence_score": 82.0,
  "quality_tier": "high",
  "cost_usd": 0.05,
  "message": "Quick enrichment complete! (Using hybrid strategy)"
}
```

### Admin Endpoints (New)

#### GET `/api/admin/ab-tests/dashboard`
Get A/B test dashboard overview

**Response**:
```json
{
  "success": true,
  "data": {
    "active_variants": [
      {
        "variant_key": "full_stack",
        "variant_name": "Full Stack (High Quality)",
        "sample_size": 145,
        "avg_cost": 0.15,
        "avg_completeness": 94.2,
        "avg_confidence": 89.5,
        "quality_per_dollar": 628.0
      },
      {
        "variant_key": "hybrid",
        "variant_name": "Hybrid (Balanced)",
        "sample_size": 152,
        "avg_cost": 0.05,
        "avg_completeness": 78.1,
        "avg_confidence": 82.3,
        "quality_per_dollar": 1562.0  // WINNER: Best ROI
      },
      {
        "variant_key": "free_only",
        "variant_name": "Free Only (Zero Cost)",
        "sample_size": 148,
        "avg_cost": 0.00,
        "avg_completeness": 51.7,
        "avg_confidence": 68.2,
        "quality_per_dollar": null  // Division by zero
      }
    ],
    "total_enrichments": 445,
    "test_start_date": "2025-01-09T10:00:00Z",
    "test_duration_hours": 48
  }
}
```

#### POST `/api/admin/ab-tests/variants`
Create new A/B test variant

**Request**:
```json
{
  "variant_key": "premium_linkedin",
  "variant_name": "Premium LinkedIn Focus",
  "description": "Use Proxycurl for deep LinkedIn data + free sources",
  "sources_config": ["proxycurl", "metadata", "ip_api"],
  "expected_cost_usd": 0.03,
  "expected_completeness": 72.0,
  "traffic_allocation": 25.0
}
```

#### POST `/api/admin/ab-tests/declare-winner`
Declare winning variant and deactivate others

**Request**:
```json
{
  "variant_id": 2,
  "rationale": "Hybrid variant achieves best quality-per-dollar ratio (1562 vs 628 for full_stack)"
}
```

#### GET `/api/admin/ab-tests/metrics/{variant_id}`
Get detailed metrics for specific variant

**Response**:
```json
{
  "success": true,
  "variant_key": "hybrid",
  "metrics": {
    "cost_per_enrichment": {
      "value": 0.05,
      "std_dev": 0.002,
      "confidence_interval": [0.048, 0.052],
      "sample_size": 152
    },
    "avg_completeness": {
      "value": 78.1,
      "std_dev": 8.3,
      "confidence_interval": [76.8, 79.4],
      "sample_size": 152
    },
    "user_edit_rate": {
      "value": 23.5,
      "sample_size": 152,
      "description": "23.5% of users edited auto-filled data"
    },
    "form_completion_rate": {
      "value": 94.7,
      "sample_size": 152,
      "description": "94.7% completed form after enrichment"
    },
    "avg_time_to_autofill_ms": {
      "value": 2850,
      "std_dev": 420,
      "description": "Average 2.85s to display enriched data"
    }
  }
}
```

#### POST `/api/admin/recommendations/generate`
Generate recommendation based on constraints

**Request**:
```json
{
  "budget_per_enrichment": 0.10,
  "min_confidence": 80.0,
  "min_completeness": 70.0,
  "expected_volume_per_month": 1000
}
```

**Response**:
```json
{
  "success": true,
  "recommendation": {
    "recommended_variant": "hybrid",
    "recommended_sources": ["metadata", "ip_api", "openrouter"],
    "predicted_cost": 0.05,
    "predicted_completeness": 78.1,
    "predicted_confidence": 82.3,
    "prediction_confidence_interval": {
      "completeness_lower": 76.8,
      "completeness_upper": 79.4
    },
    "monthly_cost_projection": 50.00,
    "cost_vs_budget": -50.00,  // $50 under budget
    "rationale": "Hybrid strategy meets all quality requirements while saving $50/month (50% cost reduction) compared to budget. Based on 152 historical enrichments with 95% confidence.",
    "alternative_strategies": [
      {
        "variant": "full_stack",
        "cost": 0.15,
        "completeness": 94.2,
        "note": "Higher quality but exceeds budget by $50/month"
      }
    ]
  }
}
```

#### GET `/api/admin/recommendations/history`
View recommendation history with actual performance

**Response**:
```json
{
  "success": true,
  "recommendations": [
    {
      "id": 5,
      "recommended_at": "2025-01-07T10:00:00Z",
      "recommended_variant": "hybrid",
      "predicted_cost": 0.05,
      "predicted_completeness": 78.0,
      "actual_cost": 0.05,
      "actual_completeness": 78.1,
      "prediction_accuracy": 99.87,
      "is_implemented": true,
      "sample_size": 152
    }
  ]
}
```

---

## Implementation Plan

### Phase 7.1: Database & Core Infrastructure (Week 1)

**Tasks**:
1. Create migration `009_ab_testing_and_recommendations.sql`
2. Run migration in Supabase
3. Verify tables, indexes, views created successfully
4. Test database functions (`assign_ab_test_variant`, `calculate_ab_test_metrics`)

**Deliverables**:
- Migration file
- Database verification script
- Sample data insertion for 3 default variants

---

### Phase 7.2: Variant Assignment Logic (Week 1-2)

**Tasks**:
1. Create `app/services/ab_testing/assigner.py`
   ```python
   class VariantAssigner:
       async def assign_variant(
           self,
           session_id: str,
           enrichment_id: int
       ) -> str:
           """Assign A/B test variant based on session_id hash"""
           # Use database function: assign_ab_test_variant()
           pass

       async def get_variant_config(
           self,
           variant_key: str
       ) -> List[str]:
           """Get sources_config for variant"""
           pass
   ```

2. Modify `EnrichmentOrchestrator` to accept `sources_filter`
   ```python
   async def enrich_deep(
       self,
       website: str,
       sources_filter: Optional[List[str]] = None,  # NEW
       ...
   ):
       # Filter self.deep_sources by sources_filter
       # Only call sources in filter
       pass
   ```

3. Update `/api/enrichment/submit` route
   ```python
   @router.post("/submit")
   async def submit_enrichment(...):
       # 1. Create enrichment record
       enrichment_id = await db.create_enrichment(...)

       # 2. Assign A/B test variant
       assigner = VariantAssigner()
       variant_key = await assigner.assign_variant(session_id, enrichment_id)
       sources = await assigner.get_variant_config(variant_key)

       # 3. Run enrichment with filtered sources
       quick_data = await orchestrator.enrich_quick(website)

       # 4. Trigger deep enrichment with sources filter
       background_tasks.add_task(
           orchestrator.enrich_deep,
           website,
           sources_filter=sources  # Pass variant sources
       )

       return {
           "ab_test_variant": variant_key,
           ...
       }
   ```

**Deliverables**:
- `VariantAssigner` class
- Modified orchestrator with source filtering
- Updated submit endpoint with A/B assignment
- Unit tests for variant assignment consistency

---

### Phase 7.3: Metrics Collection (Week 2)

**Tasks**:
1. Create `app/services/ab_testing/metrics.py`
   ```python
   class MetricsCollector:
       async def record_event(
           self,
           enrichment_id: int,
           variant_id: int,
           event_type: str,
           event_value: Optional[float] = None,
           event_metadata: Optional[Dict] = None
       ):
           """Record A/B test event"""
           pass

       async def aggregate_metrics(
           self,
           variant_id: int,
           time_window_hours: int = 24
       ):
           """Calculate aggregated metrics for variant"""
           # Calls database function: calculate_ab_test_metrics()
           pass
   ```

2. Add event tracking to enrichment flow
   - Track `time_to_autofill` when quick enrichment completes
   - Track `form_completed` when user submits form
   - Track `user_edited` when user modifies enriched data
   - Track `data_accepted` when user proceeds without edits

3. Schedule metrics aggregation (cron job)
   ```python
   # Run every 6 hours
   async def aggregate_all_variants():
       variants = await db.get_active_variants()
       for variant in variants:
           await metrics_collector.aggregate_metrics(variant.id)
   ```

**Deliverables**:
- `MetricsCollector` class
- Event tracking in enrichment routes
- Cron job for metrics aggregation
- Dashboard query functions

---

### Phase 7.4: Recommendations Engine (Week 3)

**Tasks**:
1. Create `app/services/ab_testing/recommender.py`
   ```python
   from typing import List
   from pydantic import BaseModel

   class RecommendationStrategy(BaseModel):
       variant_key: str
       sources: List[str]
       predicted_cost: float
       predicted_completeness: float
       predicted_confidence: float
       confidence_interval: Dict[str, float]
       rationale: str

   class EnrichmentRecommender:
       async def recommend_strategy(
           self,
           budget_per_enrichment: float,
           min_confidence: float,
           min_completeness: float,
           historical_lookback_days: int = 30
       ) -> RecommendationStrategy:
           """
           Pareto optimization: Maximize quality, minimize cost

           Algorithm:
           1. Fetch all variants with metrics from last N days
           2. Filter variants meeting min_confidence and min_completeness
           3. Calculate quality_per_dollar = completeness / cost
           4. Rank by quality_per_dollar descending
           5. Return top variant within budget
           6. If no variant within budget, return cheapest that meets quality
           """

           # Get historical data
           variants = await self._get_variant_metrics(historical_lookback_days)

           # Filter by quality constraints
           candidates = [
               v for v in variants
               if v.avg_confidence >= min_confidence
               and v.avg_completeness >= min_completeness
           ]

           # Pareto optimization
           if candidates:
               # Calculate ROI
               for c in candidates:
                   c.roi = c.avg_completeness / max(c.avg_cost, 0.001)

               # Sort by ROI descending
               candidates.sort(key=lambda x: x.roi, reverse=True)

               # Find best within budget
               within_budget = [c for c in candidates if c.avg_cost <= budget_per_enrichment]

               recommended = within_budget[0] if within_budget else candidates[-1]  # Cheapest

               return RecommendationStrategy(
                   variant_key=recommended.variant_key,
                   sources=recommended.sources_config,
                   predicted_cost=recommended.avg_cost,
                   predicted_completeness=recommended.avg_completeness,
                   predicted_confidence=recommended.avg_confidence,
                   confidence_interval={
                       "lower": recommended.avg_completeness - (1.96 * recommended.std_dev),
                       "upper": recommended.avg_completeness + (1.96 * recommended.std_dev)
                   },
                   rationale=self._generate_rationale(recommended, budget_per_enrichment)
               )

           # Fallback: No variants meet quality requirements
           return self._fallback_recommendation()
   ```

2. Implement prediction accuracy tracking
   ```python
   async def track_recommendation_performance(
       recommendation_id: int
   ):
       """
       After recommendation is implemented, track actual vs predicted
       """
       rec = await db.get_recommendation(recommendation_id)

       # Get actual metrics from last 30 days
       actual_metrics = await db.get_variant_metrics(
           rec.recommended_variant_id,
           days=30
       )

       # Update recommendations_history
       await db.update_recommendation_performance(
           recommendation_id,
           actual_cost=actual_metrics.avg_cost,
           actual_completeness=actual_metrics.avg_completeness,
           actual_confidence=actual_metrics.avg_confidence
       )
   ```

**Deliverables**:
- `EnrichmentRecommender` class with Pareto optimization
- Recommendation API endpoints
- Prediction accuracy tracking
- Alternative strategies generator

---

### Phase 7.5: Admin Dashboard UI (Week 3-4)

**Tasks**:
1. Create A/B test dashboard page `/admin/ab-tests`
   - Real-time variant comparison table
   - Charts: Cost vs Quality scatter plot
   - Charts: Completeness distribution by variant
   - Charts: Time-series metrics (daily avg cost, completeness)
   - Winner declaration button

2. Create recommendations page `/admin/recommendations`
   - Input form: Budget, min confidence, min completeness
   - Generate recommendation button
   - Display recommended strategy with rationale
   - Show alternative strategies
   - Implement recommendation button

3. Create variant management page `/admin/ab-tests/variants`
   - List all variants
   - Create new variant form
   - Edit variant (sources, traffic allocation)
   - Activate/deactivate variants
   - View detailed metrics per variant

**Deliverables**:
- React components for A/B test dashboard
- Recharts visualizations
- Variant CRUD interface
- Recommendation generator UI

---

### Phase 7.6: Testing & Validation (Week 4)

**Tasks**:
1. Unit tests
   - Test variant assignment consistency (same session_id → same variant)
   - Test source filtering in orchestrator
   - Test metrics aggregation functions
   - Test recommendation algorithm edge cases

2. Integration tests
   - Test full enrichment flow with A/B variants
   - Test metrics collection during enrichment
   - Test recommendation generation with real data
   - Test winner declaration workflow

3. Load testing
   - Simulate 1000 enrichments across 3 variants
   - Verify metrics accuracy
   - Test dashboard query performance

4. Validation
   - Verify statistical significance calculations
   - Validate prediction accuracy (predicted vs actual)
   - Test edge cases (zero-cost variants, high-cost variants)

**Deliverables**:
- Test suite with 50+ test cases
- Load test results
- Validation report
- Performance benchmarks

---

## Success Metrics

### Technical Metrics
- ✅ Variant assignment consistency: 100% (same session → same variant)
- ✅ Metrics aggregation latency: < 5 seconds
- ✅ Dashboard query performance: < 2 seconds
- ✅ Recommendation generation time: < 1 second

### Business Metrics
- ✅ Minimum sample size for statistical significance: 100 per variant
- ✅ Prediction accuracy (actual vs predicted completeness): ±5%
- ✅ Cost optimization: Identify 20%+ cost reduction opportunities
- ✅ Quality maintenance: Recommended variants maintain 70%+ completeness

### User Experience
- ✅ Dashboard load time: < 3 seconds
- ✅ Real-time metrics update: Every 6 hours
- ✅ Clear winner determination: Statistical confidence > 95%
- ✅ Actionable recommendations: Include rationale and alternatives

---

## Cost-Benefit Analysis

### Investment
- **Development**: 4 weeks (Phase 7.1 - 7.6)
- **Database**: 4 new tables, 2 views, 2 functions
- **Infrastructure**: Minimal (uses existing enrichment system)

### Returns

**Scenario 1: Discover Free-Only Is Sufficient**
- Current: $0.15 × 1,000 = $150/month
- After test: $0.00 × 1,000 = $0/month
- **Savings**: $150/month = $1,800/year

**Scenario 2: Optimize to Hybrid**
- Current: $0.15 × 1,000 = $150/month
- After test: $0.05 × 1,000 = $50/month
- **Savings**: $100/month = $1,200/year

**Scenario 3: Justify Full Stack**
- Current: Using free-only (poor quality)
- After test: $0.15 × 1,000 = $150/month
- **Value**: +40% completeness = better lead conversion

**ROI**: Payback period < 1 month at 1,000 enrichments/month

---

## Risk Mitigation

### Risk 1: Sample Size Too Small
**Mitigation**: Wait for minimum 100 enrichments per variant before making decisions

### Risk 2: External Factors (Source API Changes)
**Mitigation**: Track source-level metrics separately, re-run tests if sources change

### Risk 3: Seasonal Variations
**Mitigation**: Run tests for minimum 30 days to capture weekly patterns

### Risk 4: User Behavior Changes
**Mitigation**: Continuously monitor user_edit_rate and form_completion_rate metrics

---

## Future Enhancements (Phase 8+)

1. **Multi-Armed Bandit**: Dynamic traffic allocation based on real-time performance
2. **Personalized Recommendations**: Recommend different strategies per industry/company size
3. **Auto-Optimization**: Automatically switch to winning variant after statistical significance
4. **Cost Forecasting**: Predict monthly costs based on traffic projections
5. **Quality Alerts**: Notify admins when quality drops below threshold
6. **Source Contribution Analysis**: Which individual sources provide most value?

---

## Appendix A: Metrics Definitions

| Metric | Formula | Purpose |
|--------|---------|---------|
| **cost_per_enrichment** | AVG(total_cost_usd) | Track average cost per variant |
| **avg_completeness** | AVG(completeness_score) | Measure data quality |
| **avg_confidence** | AVG(confidence_score) | Measure data reliability |
| **user_edit_rate** | COUNT(user_edited) / COUNT(*) × 100 | How often users correct data |
| **form_completion_rate** | COUNT(form_completed) / COUNT(*) × 100 | User satisfaction proxy |
| **time_to_autofill** | AVG(quick_duration_ms) | User experience metric |
| **quality_per_dollar** | completeness / cost | ROI metric |
| **std_dev** | STDDEV(metric_value) | Variance/consistency |

---

## Appendix B: Statistical Significance Testing

### T-Test for Variant Comparison

**Hypothesis**: Variant A completeness > Variant B completeness

```python
from scipy import stats

def is_statistically_significant(
    variant_a_data: List[float],
    variant_b_data: List[float],
    alpha: float = 0.05
) -> bool:
    """
    Perform two-sample t-test

    Returns True if variant_a is significantly better than variant_b
    """
    t_stat, p_value = stats.ttest_ind(variant_a_data, variant_b_data)

    return p_value < alpha and t_stat > 0
```

**Required Sample Size** (95% confidence, 80% power):
- Minimum: 100 per variant
- Recommended: 200+ per variant for detecting 10% difference

---

## Appendix C: Sample Dashboard Queries

### Query 1: Variant Comparison Table
```sql
SELECT * FROM ab_test_variant_performance
ORDER BY quality_per_dollar DESC NULLS LAST;
```

### Query 2: Winner Determination
```sql
SELECT * FROM ab_test_winner_analysis
WHERE sample_size_a >= 100 AND sample_size_b >= 100
ORDER BY ABS(roi_a - roi_b) DESC;
```

### Query 3: Recommendation Input Data
```sql
SELECT
    variant_key,
    AVG(total_cost_usd) as avg_cost,
    AVG(completeness_score) as avg_completeness,
    AVG(confidence_score) as avg_confidence,
    STDDEV(completeness_score) as completeness_std_dev,
    COUNT(*) as sample_size
FROM ab_test_variants v
JOIN ab_test_assignments a ON v.id = a.variant_id
JOIN enrichment_results e ON a.enrichment_id = e.id
WHERE v.is_active = true
  AND a.assigned_at >= NOW() - INTERVAL '30 days'
GROUP BY variant_key;
```

---

**Document Version**: 1.0.0
**Created**: 2025-01-09
**Last Updated**: 2025-01-09
**Status**: Ready for Implementation
