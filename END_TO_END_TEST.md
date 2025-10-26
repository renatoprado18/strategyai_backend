# End-to-End System Test

Complete testing checklist to verify the entire Strategy AI system works correctly.

---

## 📋 Testing Timeline: 30 Minutes

1. **Environment Setup** (10 min) - Fix Railway variables and redeploy
2. **Public Submission Test** (5 min) - Submit form and verify database
3. **AI Report Generation** (10 min) - Wait for and verify AI processing
4. **Admin Dashboard Test** (5 min) - Login and view reports

---

## ✅ Pre-Test Checklist

Before starting tests, verify:

- [ ] Ran both Supabase migrations (`submissions` + `admin_users` tables exist)
- [ ] Deleted `DATABASE_URL` from Railway env vars
- [ ] Added `UPSTASH_REDIS_URL` to Railway env vars
- [ ] Added `UPSTASH_REDIS_TOKEN` to Railway env vars
- [ ] Railway redeployed successfully
- [ ] Railway logs show: `[STARTUP] Starting Strategy AI Backend...`

**If any unchecked → Go to FIX_RAILWAY_NOW.md first**

---

## 🧪 Test 1: Public Form Submission (5 min)

### Test 1.1: Submit Form

1. Open browser
2. Go to: `https://strategyai-landing.vercel.app`
3. Fill out form:
   ```
   Nome: João Silva
   Email: joao.silva@example.com
   Empresa: TechStart Brasil
   Website: https://techstart.example.com
   Setor: Technology
   Desafio: Precisamos aumentar nossa base de clientes e melhorar o posicionamento de marca no mercado brasileiro
   ```
4. Click "Enviar" button

**Expected Result:**
- ✅ Redirects to "Obrigado" (Thank You) page
- ✅ No error messages
- ✅ Page loads within 1-2 seconds

**If fails:**
- Check browser console for errors (F12 → Console tab)
- Verify Vercel env var `NEXT_PUBLIC_API_URL` is correct
- Check CORS settings in Railway

### Test 1.2: Verify in Railway Logs (Immediate)

1. Go to Railway → `web` service → **Deployments**
2. Click latest deployment
3. Look for log messages (should appear within 5 seconds):

**Expected Logs:**
```
[OK] New submission created: ID=1, Company=TechStart Brasil
[PROCESSING] Processing analysis for submission 1...
[APIFY] Gathering enrichment data for TechStart Brasil...
```

✅ **If you see these → Submission successful!**

❌ **If you see errors:**
- Screenshot error message
- Check error indicates (missing API keys, connection issues, etc.)

❌ **If you see nothing:**
- Backend might not be running
- Check Railway deployment status
- Verify env vars are correct

### Test 1.3: Verify in Supabase (Immediate)

1. Go to Supabase SQL Editor
2. Run:

```sql
SELECT
    id,
    name,
    email,
    company,
    status,
    created_at,
    EXTRACT(EPOCH FROM (NOW() - created_at)) / 60 as minutes_ago
FROM submissions
ORDER BY created_at DESC
LIMIT 1;
```

**Expected Result:**
```
id | name        | email                  | company         | status  | created_at          | minutes_ago
---|-------------|------------------------|-----------------|---------|---------------------|------------
 1 | João Silva  | joao.silva@example.com | TechStart Brasil| pending | 2025-01-26 10:30:00 | 0.2
```

✅ **If you see this → Database write successful!**

❌ **If 0 rows:**
- Backend not connected to Supabase
- Check Supabase env vars in Railway
- Check Railway logs for connection errors

---

## 🤖 Test 2: AI Report Generation (10 min)

### Test 2.1: Monitor Background Processing

**Watch Railway logs for these stages:**

**Stage 1: Apify Data Collection (30-60 seconds)**
```
[APIFY] Gathering enrichment data for TechStart Brasil...
[APIFY] Data gathering completed for submission 1
```

**Stage 2: AI Generation (10-30 seconds)**
```
[AI] Generating strategic analysis for submission 1...
```

**Stage 3: Completion (immediate)**
```
[OK] Analysis completed for submission 1
```

**Total expected time: 60-90 seconds**

✅ **If you see all stages → AI processing working!**

⚠️ **If you see warnings:**
```
[WARNING] Apify enrichment failed: <error>. Continuing with basic analysis...
```
This is OK - AI will still generate report, just without Apify data enrichment

❌ **If you see errors:**
```
[ERROR] Analysis failed for submission 1: <error message>
```
- Check error message for clues
- Common issues: Invalid API keys (Apify, OpenRouter)

### Test 2.2: Verify Report in Database (After 2 minutes)

Run in Supabase SQL Editor:

```sql
SELECT
    id,
    company,
    status,
    LENGTH(report_json) as report_size_bytes,
    error_message,
    EXTRACT(EPOCH FROM (updated_at - created_at)) / 60 as processing_time_minutes
FROM submissions
WHERE company = 'TechStart Brasil'
ORDER BY created_at DESC
LIMIT 1;
```

**Expected Result:**
```
id | company          | status    | report_size_bytes | error_message | processing_time_minutes
---|------------------|-----------|-------------------|---------------|------------------------
 1 | TechStart Brasil | completed | 12458             | null          | 1.5
```

✅ **Success Criteria:**
- `status` = 'completed'
- `report_size_bytes` > 5000 (typically 5KB-20KB)
- `error_message` = null
- `processing_time_minutes` < 3 minutes

❌ **If failed:**
- `status` = 'failed' → Check `error_message`
- `status` = 'pending' after 5 minutes → Background task crashed
- `report_size_bytes` = 0 → Report not generated

### Test 2.3: Preview Report Content

Run in Supabase SQL Editor:

```sql
SELECT
    id,
    company,
    LEFT(report_json, 200) as report_preview
FROM submissions
WHERE company = 'TechStart Brasil'
AND status = 'completed'
ORDER BY created_at DESC
LIMIT 1;
```

**Expected: JSON starting with Portuguese text like:**
```json
{"executive_summary": "A TechStart Brasil enfrenta desafios típicos...
```

✅ **If you see Portuguese JSON → AI generated correctly!**

---

## 👨‍💼 Test 3: Admin Dashboard (5 min)

### Test 3.1: Create Admin Account (If Not Done)

1. Go to: `https://strategyai-landing.vercel.app/admin/signup`
2. Create account with your email
3. Should see success message and redirect to login

### Test 3.2: Grant Admin Access (If Not Done)

1. Supabase → Authentication → Users → Copy your User UID
2. Supabase → SQL Editor → Run:

```sql
SELECT grant_admin_access(
    target_user_id := 'YOUR-USER-UUID',
    target_email := 'your@email.com',
    admin_notes := 'Test admin - owner'
);
```

3. Should return `true`

### Test 3.3: Login to Dashboard

1. Go to: `https://strategyai-landing.vercel.app/admin/login`
2. Enter email and password
3. Click "Entrar"

**Expected:**
- ✅ Redirects to `/admin/dashboard-x9k2p`
- ✅ Shows your email in header
- ✅ Shows "Logout" button
- ✅ Shows list of submissions

❌ **If "Access denied":**
- Admin access not granted yet (run Test 3.2 again)
- Wrong email/password
- Check browser console for errors

### Test 3.4: View Submission in Dashboard

**Expected in dashboard:**
- List shows submission for "TechStart Brasil"
- Shows: company name, contact name, email, status
- Status shows: "completed" with green indicator

Click on the submission row.

**Expected:**
- Opens full report view
- Shows report in Portuguese
- Contains sections:
  - Sumário Executivo
  - Análise SWOT
  - Oportunidades Estratégicas
  - Recomendações de Ação

✅ **If all visible → Admin dashboard working!**

### Test 3.5: Test Logout

1. Click "Logout" button
2. Should redirect to `/admin/login`
3. Should NOT be able to access `/admin/dashboard-x9k2p` (redirects to login)

✅ **If logout works → Authentication system working!**

---

## 🔄 Test 4: Rate Limiting (5 min)

### Test 4.1: Test Rate Limit

From the SAME browser (same IP), submit the form 4 times:

**Submissions 1-3:**
- ✅ Should all succeed
- ✅ All get 200 OK
- ✅ All create submissions in database

**Submission 4:**
- ❌ Should fail with 429 error
- ❌ Error message: "Rate limit exceeded. You can submit 3 forms per 24 hours..."

✅ **If limited on 4th submission → Rate limiting working!**

❌ **If NOT limited:**
- Redis not connected correctly
- Check `UPSTASH_REDIS_URL` and `UPSTASH_REDIS_TOKEN` in Railway
- Check Railway logs for Redis connection errors

### Test 4.2: Verify Rate Limit in Upstash

1. Go to Upstash Console → Your Redis database
2. Go to **Data Browser**
3. Look for keys like: `ratelimit:76.35.208.181`
4. Should show count = 3

✅ **If you see the key → Rate limiting storing data correctly!**

---

## 📊 Test 5: System Health Check (2 min)

Run this comprehensive health check in Supabase SQL Editor:

```sql
SELECT
    'Total Submissions' as metric,
    COUNT(*)::text as value,
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END as status
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
    'With Reports',
    COUNT(*)::text,
    CASE WHEN COUNT(*) > 0 THEN '✅' ELSE '❌' END
FROM submissions
WHERE report_json IS NOT NULL

UNION ALL

SELECT
    'Avg Processing Time',
    ROUND(AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) / 60), 1)::text || ' min',
    CASE
        WHEN AVG(EXTRACT(EPOCH FROM (updated_at - created_at)) / 60) < 3 THEN '✅'
        ELSE '⚠️'
    END
FROM submissions
WHERE status IN ('completed', 'failed');
```

**Expected Results:**
```
metric              | value | status
--------------------|-------|-------
Total Submissions   | 3     | ✅
Completed           | 3     | ✅
Failed              | 0     | ✅
With Reports        | 3     | ✅
Avg Processing Time | 1.8   | ✅
```

✅ **All green checkmarks → System fully operational!**

---

## ✅ Final Acceptance Criteria

System is ready for production when ALL of these are true:

- [ ] ✅ Public form submission works
- [ ] ✅ Submissions appear in Supabase immediately
- [ ] ✅ Railway logs show background processing (`[APIFY]`, `[AI]`)
- [ ] ✅ AI reports generated within 2 minutes
- [ ] ✅ Reports are 5KB-20KB in size
- [ ] ✅ Reports contain Portuguese text
- [ ] ✅ Admin signup works
- [ ] ✅ Admin access grant works
- [ ] ✅ Admin login works
- [ ] ✅ Admin dashboard shows all submissions
- [ ] ✅ Admin can view full reports
- [ ] ✅ Rate limiting blocks 4th submission
- [ ] ✅ No failed submissions (or < 10%)
- [ ] ✅ Average processing time < 3 minutes

**Once all checked → Ready to show your dad and go live!**

---

## 🎯 Next Steps After Testing

### 1. Clean Up Test Data
```sql
DELETE FROM submissions
WHERE company IN ('TechStart Brasil', 'Acme Test Corp')
OR email LIKE '%test@%'
OR email LIKE '%example.com';
```

### 2. Grant Your Dad Admin Access
- Follow SETUP_ADMIN_ACCESS.md
- Have him signup at `/admin/signup`
- Grant him admin access via SQL
- Test his login works

### 3. Train Your Dad
Show him how to:
- Login at `/admin/login`
- View submissions in dashboard
- Click on submission to view full report
- Copy report text
- Email report to client manually

### 4. Go Live!
- Share landing page URL with potential clients
- Monitor Railway logs for issues
- Check Supabase daily for new submissions
- Help dad send reports to clients

---

## 🆘 If Tests Fail

**Submission not saving to database:**
→ Check Railway logs for errors
→ Verify Supabase env vars correct
→ Check RLS policies allow INSERT

**AI report not generating:**
→ Check APIFY_API_TOKEN is valid
→ Check OPENROUTER_API_KEY is valid
→ Look for errors in Railway logs

**Admin dashboard not working:**
→ Verify admin access granted in Supabase
→ Check JWT_SECRET is set in Railway
→ Check browser console for errors

**Rate limiting not working:**
→ Verify Redis env vars added to Railway
→ Check Upstash Redis is accessible
→ Look for Redis connection errors in logs

---

**Last Updated:** January 2025
