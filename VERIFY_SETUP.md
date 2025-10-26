# Setup Verification Guide

Quick checklist to verify your submission flow is working correctly.

---

## ✅ Railway Environment Variables

Based on your screenshot, you have:

### Required Variables (All Present ✓)
- ✅ `SUPABASE_URL` = https://your-project.supabase.co
- ✅ `SUPABASE_ANON_KEY` = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (from Supabase dashboard)
- ✅ `SUPABASE_SERVICE_KEY` = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9... (from Supabase dashboard)
- ✅ `JWT_SECRET` = (your secret key - generate with: openssl rand -base64 64)
- ✅ `JWT_ALGORITHM` = HS256
- ✅ `OPENROUTER_API_KEY` = sk-or-v1-... (from OpenRouter dashboard)
- ✅ `APIFY_API_TOKEN` = apify_api_... (from Apify dashboard)
- ✅ `ALLOWED_ORIGINS` = http://localhost:3000,https://your-app.vercel.app
- ✅ `MAX_SUBMISSIONS_PER_IP_PER_DAY` = 3

### Variables to REMOVE ❌
- ❌ `DATABASE_URL` = sqlite:///./database.db (NOT USED - DELETE THIS)

### Missing Variables (Optional - Add if needed)
You might need these for Upstash Redis rate limiting:
- ⚠️ `UPSTASH_REDIS_URL` = (not shown in screenshot)
- ⚠️ `UPSTASH_REDIS_TOKEN` = (not shown in screenshot)

**Impact if missing:** Rate limiting will fail-open (allows all requests without rate limiting)

---

## 🧪 Test Submission Flow

### Step 1: Submit Test Form

1. Go to: https://strategyai-landing.vercel.app
2. Fill form with test data:
   - Name: Test User
   - Email: test@example.com
   - Company: Test Company
   - Website: https://example.com
   - Industry: Technology
   - Challenge: Test challenge description
3. Submit
4. ✅ Should redirect to "Thank You" page

### Step 2: Check Railway Logs (Immediate)

1. Go to Railway → `web` service → **Deployments**
2. Look for logs like:

```
[OK] New submission created: ID=123, Company=Test Company
[PROCESSING] Processing analysis for submission 123...
```

✅ If you see this, submission was created successfully!

### Step 3: Check Supabase Database (Immediate)

1. Go to Supabase → **SQL Editor**
2. Run:

```sql
SELECT id, company, status, created_at
FROM submissions
ORDER BY created_at DESC
LIMIT 5;
```

✅ You should see your test submission with `status='pending'`

### Step 4: Wait for Background Processing (30-90 seconds)

Watch Railway logs for:

```
[APIFY] Gathering enrichment data for Test Company...
[APIFY] Data gathering completed for submission 123
[AI] Generating strategic analysis for submission 123...
[OK] Analysis completed for submission 123
```

### Step 5: Check Completed Report

1. Go to Supabase → **SQL Editor**
2. Run:

```sql
SELECT id, company, status, LENGTH(report_json) as report_size
FROM submissions
WHERE id = 123;  -- Replace with your submission ID
```

✅ Should show `status='completed'` with `report_size > 0`

### Step 6: View Full Report

```sql
SELECT report_json
FROM submissions
WHERE id = 123;
```

✅ Should show full JSON report with strategic analysis!

---

## 🔍 Troubleshooting

### Issue: "I don't see submission in Supabase Table Editor"

**Cause:** Row Level Security (RLS) blocks SELECT for unauthenticated users

**Solution:** Use SQL Editor instead of Table Editor:
```sql
SELECT * FROM submissions ORDER BY created_at DESC LIMIT 10;
```

### Issue: Submission stuck on "pending" status

**Possible Causes:**
1. Background task crashed (check Railway logs for errors)
2. Apify API token invalid
3. OpenRouter API key invalid
4. Background task still running (wait 2 minutes)

**Check Railway logs for:**
```
[ERROR] Analysis failed for submission 123: <error message>
```

### Issue: Status = "failed"

**Check error message:**
```sql
SELECT id, company, status, error_message
FROM submissions
WHERE status = 'failed'
ORDER BY created_at DESC
LIMIT 5;
```

**Common Errors:**
- "Apify API token invalid" → Fix `APIFY_API_TOKEN` in Railway
- "OpenRouter API error" → Check `OPENROUTER_API_KEY` in Railway
- "Analysis validation failed" → AI returned malformed JSON (rare)

### Issue: Rate limit exceeded

**Error:** 429 Too Many Requests

**Message:** "Rate limit exceeded. You can submit 3 forms per 24 hours."

**Solution (Admin Only):** Reset via SQL:
```sql
-- Note: This requires direct Redis access or custom endpoint
-- Currently can only wait for 24-hour window to expire
```

---

## 📊 Monitoring Queries

### View All Submissions
```sql
SELECT
    id,
    company,
    industry,
    status,
    CASE
        WHEN report_json IS NOT NULL THEN 'Yes'
        ELSE 'No'
    END as has_report,
    created_at
FROM submissions
ORDER BY created_at DESC;
```

### Count by Status
```sql
SELECT status, COUNT(*) as count
FROM submissions
GROUP BY status;
```

### Average Processing Time
```sql
SELECT
    AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) / 60) as avg_minutes
FROM submissions
WHERE status IN ('completed', 'failed');
```

### Success Rate
```sql
SELECT
    status,
    COUNT(*) as count,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) as percentage
FROM submissions
GROUP BY status;
```

---

## 🎯 Expected Results

### Successful Submission Flow:

1. **Immediate (< 1 second):**
   - Frontend: "Thank You" page displayed
   - Backend: Returns `{"success": true, "submission_id": 123}`
   - Database: Row created with `status='pending'`
   - Railway Logs: "[OK] New submission created"

2. **Within 30 seconds:**
   - Railway Logs: "[APIFY] Gathering enrichment data..."
   - Status: Still `pending`

3. **Within 60-90 seconds:**
   - Railway Logs: "[AI] Generating strategic analysis..."
   - Railway Logs: "[OK] Analysis completed"
   - Database: `status='completed'`, `report_json` populated
   - Report size: ~5,000-20,000 bytes

4. **Admin Dashboard:**
   - Submission appears in list
   - Can view full report
   - Can reprocess if failed

---

## 🚦 Health Check

Run this query to verify system health:

```sql
-- System Health Check
SELECT
    'Total Submissions' as metric,
    COUNT(*)::text as value
FROM submissions
UNION ALL
SELECT
    'Completed',
    COUNT(*)::text
FROM submissions
WHERE status = 'completed'
UNION ALL
SELECT
    'Failed',
    COUNT(*)::text
FROM submissions
WHERE status = 'failed'
UNION ALL
SELECT
    'Pending (> 5 min)',
    COUNT(*)::text
FROM submissions
WHERE status = 'pending'
AND created_at < NOW() - INTERVAL '5 minutes'
UNION ALL
SELECT
    'Last Submission',
    MAX(created_at)::text
FROM submissions;
```

**Expected Results:**
- Total Submissions: > 0
- Completed: Most should be completed
- Failed: Should be low (< 10%)
- Pending (> 5 min): Should be 0 (if any, background task crashed)
- Last Submission: Recent timestamp

---

## 📞 Support

If you see persistent issues:

1. **Check Railway Logs** for specific error messages
2. **Verify API Keys** (Apify, OpenRouter) are valid
3. **Check Supabase** connections are working
4. **Review RLS Policies** if data visibility issues

---

**Status:** Ready for Testing ✅

**Last Updated:** January 2025
