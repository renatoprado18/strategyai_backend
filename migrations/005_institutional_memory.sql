-- Migration: Institutional Memory & Caching System
-- Date: 2025-10-26
-- Purpose: Store and reuse key findings across analyses to reduce costs

-- Create institutional_memory table
CREATE TABLE IF NOT EXISTS institutional_memory (
    id BIGSERIAL PRIMARY KEY,
    entity_type TEXT NOT NULL,  -- 'company', 'competitor_map', 'industry_trends', 'market_data'
    entity_id TEXT NOT NULL,  -- Company name, industry name, etc. (lowercase, trimmed)
    cache_key TEXT NOT NULL UNIQUE,  -- '{entity_type}:{entity_id}'
    content_hash TEXT NOT NULL,  -- SHA256 hash for deduplication
    data JSONB NOT NULL,  -- The actual cached data
    source TEXT NOT NULL,  -- Where this came from ('analysis', 'apify', 'perplexity')
    confidence REAL DEFAULT 0.8,  -- Confidence score 0-1
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW(),
    access_count INTEGER DEFAULT 1
);

-- Create indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_memory_cache_key ON institutional_memory(cache_key);
CREATE INDEX IF NOT EXISTS idx_memory_entity_type ON institutional_memory(entity_type);
CREATE INDEX IF NOT EXISTS idx_memory_entity_id ON institutional_memory(entity_id);
CREATE INDEX IF NOT EXISTS idx_memory_last_accessed ON institutional_memory(last_accessed_at DESC);
CREATE INDEX IF NOT EXISTS idx_memory_access_count ON institutional_memory(access_count DESC);
CREATE INDEX IF NOT EXISTS idx_memory_content_hash ON institutional_memory(content_hash);

-- GIN index for JSON querying
CREATE INDEX IF NOT EXISTS idx_memory_data ON institutional_memory USING gin (data jsonb_path_ops);

-- Add comments
COMMENT ON TABLE institutional_memory IS 'Stores institutional knowledge from analyses for reuse across submissions';
COMMENT ON COLUMN institutional_memory.entity_type IS 'Type of cached entity: company, competitor_map, industry_trends, market_data';
COMMENT ON COLUMN institutional_memory.cache_key IS 'Unique cache key: {entity_type}:{entity_id}';
COMMENT ON COLUMN institutional_memory.content_hash IS 'SHA256 hash of data for deduplication';
COMMENT ON COLUMN institutional_memory.confidence IS 'Confidence score 0-1 for data quality';
COMMENT ON COLUMN institutional_memory.access_count IS 'Number of times this cache entry was accessed';

-- Example data structure:
-- {
--   "company": "Nubank",
--   "industry": "Tecnologia",
--   "company_facts": {...},
--   "key_metrics": {...},
--   "cached_at": "2025-10-26T12:00:00Z"
-- }

-- Automatic cleanup: Delete entries older than 90 days with low access count
-- Run this periodically via cron or manually
-- DELETE FROM institutional_memory
-- WHERE last_accessed_at < NOW() - INTERVAL '90 days'
-- AND access_count < 3;
