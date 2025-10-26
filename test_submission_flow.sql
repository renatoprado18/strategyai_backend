-- Test Submission Flow Query
-- Run this in Supabase SQL Editor to see all submissions and their status

-- ============================================
-- View All Submissions (Most Recent First)
-- ============================================

SELECT
    id,
    name,
    email,
    company,
    website,
    industry,
    challenge,
    status,
    CASE
        WHEN report_json IS NOT NULL THEN 'Yes (' || LENGTH(report_json) || ' bytes)'
        ELSE 'No'
    END as has_report,
    error_message,
    created_at,
    updated_at
FROM submissions
ORDER BY created_at DESC
LIMIT 20;

-- ============================================
-- Submission Status Breakdown
-- ============================================

SELECT
    status,
    COUNT(*) as count,
    MAX(created_at) as most_recent
FROM submissions
GROUP BY status
ORDER BY count DESC;

-- ============================================
-- Recent Submissions (Last 24 hours)
-- ============================================

SELECT
    id,
    company,
    industry,
    status,
    created_at,
    EXTRACT(EPOCH FROM (NOW() - created_at)) / 60 as minutes_ago
FROM submissions
WHERE created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;

-- ============================================
-- Check Specific Submission by ID
-- ============================================

-- Replace XXX with actual submission ID
-- SELECT * FROM submissions WHERE id = XXX;

-- ============================================
-- View Latest Submission's Report (if completed)
-- ============================================

SELECT
    id,
    company,
    status,
    LEFT(report_json, 200) as report_preview
FROM submissions
WHERE status = 'completed'
ORDER BY created_at DESC
LIMIT 1;

-- ============================================
-- Troubleshooting: Find Failed Submissions
-- ============================================

SELECT
    id,
    company,
    status,
    error_message,
    created_at
FROM submissions
WHERE status = 'failed'
ORDER BY created_at DESC;

-- ============================================
-- Submission Processing Time Analysis
-- ============================================

SELECT
    id,
    company,
    status,
    created_at,
    updated_at,
    EXTRACT(EPOCH FROM (updated_at - created_at)) / 60 as processing_time_minutes
FROM submissions
WHERE status IN ('completed', 'failed')
ORDER BY created_at DESC
LIMIT 10;
