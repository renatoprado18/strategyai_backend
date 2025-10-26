-- ============================================
-- SYSTEM VERIFICATION QUERIES
-- Run these in Supabase SQL Editor to verify everything works
-- ============================================

-- ============================================
-- STEP 1: Check if tables exist
-- ============================================

SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
AND table_name IN ('submissions', 'admin_users')
ORDER BY table_name;

-- Expected result: 2 rows showing both tables exist
-- If 0 rows: Run migrations first!


-- ============================================
-- STEP 2: Check if any submissions exist
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
    created_at,
    updated_at
FROM submissions
ORDER BY created_at DESC
LIMIT 10;

-- Expected after form submission: At least 1 row
-- If 0 rows: Backend not connected to Supabase yet


-- ============================================
-- STEP 3: Check submission status breakdown
-- ============================================

SELECT
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 1) as percentage
FROM submissions
GROUP BY status
ORDER BY count DESC;

-- Expected results:
-- pending: 0-1 (only if currently processing)
-- completed: Most submissions
-- failed: Few or none (< 10%)


-- ============================================
-- STEP 4: Check if reports are being generated
-- ============================================

SELECT
    id,
    company,
    status,
    CASE
        WHEN report_json IS NOT NULL THEN 'Yes (' || LENGTH(report_json) || ' bytes)'
        ELSE 'No'
    END as has_report,
    CASE
        WHEN report_json IS NOT NULL THEN LENGTH(report_json)
        ELSE 0
    END as report_size_bytes,
    error_message,
    EXTRACT(EPOCH FROM (updated_at - created_at)) / 60 as processing_time_minutes
FROM submissions
ORDER BY created_at DESC
LIMIT 10;

-- Expected for completed submissions:
-- status='completed'
-- has_report='Yes (5000-20000 bytes)'
-- report_size_bytes > 0
-- processing_time_minutes: 1-3 minutes


-- ============================================
-- STEP 5: View latest submission details
-- ============================================

SELECT
    id,
    name,
    email,
    company,
    website,
    industry,
    LEFT(challenge, 50) as challenge_preview,
    status,
    CASE
        WHEN report_json IS NOT NULL THEN 'Generated ✅'
        ELSE 'Not yet ⏳'
    END as report_status,
    error_message,
    created_at,
    EXTRACT(EPOCH FROM (NOW() - created_at)) / 60 as minutes_ago
FROM submissions
ORDER BY created_at DESC
LIMIT 1;

-- This shows the most recent submission with human-readable timing


-- ============================================
-- STEP 6: View a completed report (JSON preview)
-- ============================================

SELECT
    id,
    company,
    status,
    LEFT(report_json, 500) as report_preview  -- First 500 characters
FROM submissions
WHERE status = 'completed'
AND report_json IS NOT NULL
ORDER BY created_at DESC
LIMIT 1;

-- Expected: JSON structure with Portuguese text


-- ============================================
-- STEP 7: View full report for specific submission
-- ============================================

-- Replace XXX with actual submission ID
/*
SELECT
    id,
    company,
    report_json
FROM submissions
WHERE id = XXX;
*/

-- Click on the report_json cell to view formatted JSON


-- ============================================
-- STEP 8: Check for failed submissions
-- ============================================

SELECT
    id,
    company,
    status,
    error_message,
    created_at,
    EXTRACT(EPOCH FROM (NOW() - created_at)) / 60 as minutes_ago
FROM submissions
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 10;

-- Expected: Few or no rows
-- If many failed: Check error_message for clues


-- ============================================
-- STEP 9: Check for stuck submissions (pending > 5 min)
-- ============================================

SELECT
    id,
    company,
    status,
    created_at,
    EXTRACT(EPOCH FROM (NOW() - created_at)) / 60 as stuck_for_minutes
FROM submissions
WHERE status = 'pending'
AND created_at < NOW() - INTERVAL '5 minutes'
ORDER BY created_at;

-- Expected: 0 rows
-- If any rows: Background processing is stuck/crashed


-- ============================================
-- STEP 10: System health check summary
-- ============================================

SELECT
    'Total Submissions' as metric,
    COUNT(*)::text as value,
    '✅' as status
FROM submissions

UNION ALL

SELECT
    'Completed',
    COUNT(*)::text,
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '⚠️' END
FROM submissions
WHERE status = 'completed'

UNION ALL

SELECT
    'Failed',
    COUNT(*)::text,
    CASE WHEN COUNT(*) = 0 THEN '✅' ELSE '⚠️' END
FROM submissions
WHERE status = 'failed'

UNION ALL

SELECT
    'Stuck (pending > 5min)',
    COUNT(*)::text,
    CASE WHEN COUNT(*) = 0 THEN '✅' ELSE '❌' END
FROM submissions
WHERE status = 'pending'
AND created_at < NOW() - INTERVAL '5 minutes'

UNION ALL

SELECT
    'With Reports',
    COUNT(*)::text,
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '⚠️' END
FROM submissions
WHERE report_json IS NOT NULL

UNION ALL

SELECT
    'Last Submission',
    TO_CHAR(MAX(created_at), 'YYYY-MM-DD HH24:MI:SS'),
    CASE
        WHEN MAX(created_at) > NOW() - INTERVAL '24 hours' THEN '✅'
        WHEN MAX(created_at) IS NULL THEN '⚠️ No data'
        ELSE '⏰ Old'
    END
FROM submissions

UNION ALL

SELECT
    'Avg Processing Time',
    ROUND(AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) / 60), 1)::text || ' min',
    CASE
        WHEN AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) / 60) < 3 THEN '✅ Fast'
        WHEN AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) / 60) < 5 THEN '⚠️ Slow'
        ELSE '❌ Very Slow'
    END
FROM submissions
WHERE status IN ('completed', 'failed');


-- ============================================
-- STEP 11: Check admin users
-- ============================================

SELECT
    id,
    email,
    is_active,
    granted_at,
    notes
FROM admin_users
WHERE is_active = true
ORDER BY granted_at DESC;

-- Expected: At least 1 row (you or your dad)
-- If 0 rows: Need to grant admin access


-- ============================================
-- STEP 12: Check if specific user is admin
-- ============================================

-- Replace with actual user UUID from auth.users
/*
SELECT is_admin('YOUR-USER-UUID-HERE');
*/

-- Expected: true (if admin access granted)
-- If false: Run grant_admin_access() function


-- ============================================
-- STEP 13: Most recent submission with full details
-- ============================================

WITH latest AS (
    SELECT *
    FROM submissions
    ORDER BY created_at DESC
    LIMIT 1
)
SELECT
    '📊 LATEST SUBMISSION DETAILS' as section,
    json_build_object(
        'ID', id,
        'Company', company,
        'Name', name,
        'Email', email,
        'Status', status,
        'Has Report', (report_json IS NOT NULL),
        'Report Size', LENGTH(report_json),
        'Created', created_at,
        'Processing Time', EXTRACT(EPOCH FROM (updated_at - created_at)) / 60 || ' minutes',
        'Error', error_message
    ) as details
FROM latest;


-- ============================================
-- TROUBLESHOOTING QUERIES
-- ============================================

-- If backend seems broken, run these:

-- Check RLS policies
SELECT
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual
FROM pg_policies
WHERE tablename = 'submissions';

-- Expected: 4 policies (INSERT for all, SELECT/UPDATE/DELETE for authenticated)


-- Check table structure
SELECT
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'submissions'
ORDER BY ordinal_position;

-- Expected: All columns from schema (id, name, email, company, etc.)


-- ============================================
-- QUICK SMOKE TEST
-- ============================================

-- Run this AFTER submitting a test form
-- It should show your test submission

SELECT
    CASE
        WHEN COUNT(*) = 0 THEN '❌ FAILED: No submissions found in database'
        WHEN COUNT(*) > 0 AND COUNT(*) FILTER (WHERE report_json IS NOT NULL) = 0
            THEN '⚠️ WARNING: Submissions found but no reports generated'
        WHEN COUNT(*) > 0 AND COUNT(*) FILTER (WHERE report_json IS NOT NULL) > 0
            THEN '✅ SUCCESS: System is working! Found ' || COUNT(*) || ' submission(s) with ' ||
                 COUNT(*) FILTER (WHERE report_json IS NOT NULL) || ' report(s)'
        ELSE '⚠️ UNKNOWN STATE'
    END as system_status
FROM submissions;


-- ============================================
-- DELETE TEST DATA (Use with caution!)
-- ============================================

-- Uncomment to delete test submissions
-- ONLY use this to clean up test data before going live

/*
DELETE FROM submissions
WHERE company LIKE '%Test%'
OR email LIKE '%test@%'
OR company = 'Acme Test Corp';
*/

-- After deleting, verify:
-- SELECT COUNT(*) FROM submissions;
