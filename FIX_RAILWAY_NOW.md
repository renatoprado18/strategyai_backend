# 🚨 URGENT: Fix Railway Backend NOW

Your backend is using OLD SQLite code instead of Supabase. Follow these steps **in order**.

---

## ⚡ Quick Fix (10 minutes)

### Step 1: Delete Old Database Variable

1. Go to: https://railway.app → Your project → `web` service
2. Click **Variables** tab
3. Find this variable:
   ```
   DATABASE_URL = sqlite:///./database.db
   ```
4. Click the **⋮** icon on the right → **Delete**
5. Confirm deletion

✅ **Why:** This forces the backend to use Supabase instead of SQLite

---

### Step 2: Connect Redis to Web Service

Your Railway project has a Redis service but it's not connected to the web service.

**Option A: If Using Railway's Redis Plugin**

1. Go to Railway → Your Redis service
2. Look for connection variables (usually shown automatically)
3. Copy the **Redis URL** (format: `redis://default:xxx@xxx.railway.app:6379`)

**Option B: If Using Upstash Cloud** (Recommended)

1. Go to: https://console.upstash.com
2. Select your Redis database
3. Click **REST API** section
4. Copy:
   - **UPSTASH_REST_URL** (looks like: `https://xxx.upstash.io`)
   - **UPSTASH_REST_TOKEN** (long string)

**Add to Railway Web Service:**

1. Railway → `web` service → **Variables** tab
2. Click **New Variable**
3. Add these TWO variables:

```
Variable Name: UPSTASH_REDIS_URL
Value: <paste the REST URL here>

Variable Name: UPSTASH_REDIS_TOKEN
Value: <paste the REST token here>
```

4. Click **Add** for each

✅ **Why:** Enables rate limiting to prevent spam submissions

---

### Step 3: Verify All Environment Variables

Your Railway `web` service **Variables** tab should now have:

**✅ Required Variables (Must Have):**
- `SUPABASE_URL` = https://clltdyxxkzblznwzsxbn.supabase.co
- `SUPABASE_ANON_KEY` = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
- `SUPABASE_SERVICE_KEY` = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
- `JWT_SECRET` = (your long random string)
- `JWT_ALGORITHM` = HS256
- `OPENROUTER_API_KEY` = sk-or-v1-...
- `APIFY_API_TOKEN` = apify_api_...
- `ALLOWED_ORIGINS` = http://localhost:3000,https://strategyai-landing.vercel.app
- `UPSTASH_REDIS_URL` = (just added)
- `UPSTASH_REDIS_TOKEN` = (just added)

**❌ Should NOT Have:**
- ~~`DATABASE_URL`~~ (DELETE THIS - you just did in Step 1)

---

### Step 4: Force Redeploy

Railway should automatically redeploy when you change env vars, but let's force it:

**Method 1: Via Railway Dashboard**
1. Railway → `web` service → **Deployments** tab
2. Click on the latest deployment
3. Click **Redeploy** button (top right)

**Method 2: Via Git Push** (if Method 1 doesn't work)
1. Wait for me to push a trigger commit
2. Railway will auto-deploy from GitHub

---

### Step 5: Watch Deployment Logs

1. Railway → `web` service → **Deployments** tab
2. Click on the new deployment (status: Building/Deploying)
3. Watch the logs in real-time

**Look for this at the end:**
```
[STARTUP] Starting Strategy AI Backend with Supabase + Apify + Auth...
[OK] Database connection established
```

✅ If you see this → Backend is running new code!
❌ If you see errors → Take screenshot and send to me

---

## 🧪 Test It Works

### Test 1: Submit Form (1 minute)

1. Go to: https://strategyai-landing.vercel.app
2. Fill out the form:
   - Name: Test User
   - Email: test@yourdomain.com
   - Company: Test Company
   - Website: https://example.com
   - Industry: Technology
   - Challenge: Testing if backend works
3. Click Submit
4. Should see "Thank You" page

### Test 2: Check Railway Logs (immediate)

1. Railway → `web` service → **Deployments** → Click latest
2. **Look for these log messages:**

```
✅ GOOD SIGNS:
[OK] New submission created: ID=1, Company=Test Company
[PROCESSING] Processing analysis for submission 1...
[APIFY] Gathering enrichment data for Test Company...

❌ BAD SIGNS:
[ERROR] Failed to create submission: ...
[ERROR] Analysis failed: ...
```

### Test 3: Check Supabase Database (immediate)

1. Go to: https://clltdyxxkzblznwzsxbn.supabase.co
2. Click **SQL Editor** in left sidebar
3. Click **New Query**
4. Paste this query:

```sql
SELECT
    id,
    name,
    email,
    company,
    status,
    created_at
FROM submissions
ORDER BY created_at DESC
LIMIT 5;
```

5. Click **Run** (or press Ctrl+Enter)

**Expected Result:**
```
id | name      | email              | company      | status  | created_at
---|-----------|-------------------|--------------|---------|------------------
 1 | Test User | test@yourdomain.com| Test Company | pending | 2025-01-26 ...
```

✅ **If you see data:** Backend is working! Submissions are being saved!
❌ **If no data (0 rows):** Backend still broken - send me Railway logs

### Test 4: Wait for AI Report (60-90 seconds)

After 1-2 minutes, run this query in Supabase SQL Editor:

```sql
SELECT
    id,
    company,
    status,
    LENGTH(report_json) as report_size_bytes,
    error_message
FROM submissions
WHERE id = 1;  -- Replace with your actual submission ID
```

**Expected Result:**
```
id | company      | status    | report_size_bytes | error_message
---|--------------|-----------|-------------------|---------------
 1 | Test Company | completed | 15234             | null
```

✅ **If `status='completed'` and `report_size_bytes > 0`:** AI report generated successfully!
❌ **If `status='failed'`:** Check `error_message` column
⏳ **If `status='pending'`:** Still processing, wait another minute

---

## 🎯 Expected Timeline

| Time | What Should Happen |
|------|-------------------|
| 0:00 | You delete DATABASE_URL, add Redis vars, click Redeploy |
| 0:30 | Railway finishes building |
| 1:00 | Railway deployment live |
| 1:10 | You submit test form |
| 1:11 | Submission appears in Supabase with `status='pending'` |
| 1:15 | Railway logs show `[APIFY] Gathering enrichment data...` |
| 1:45 | Railway logs show `[AI] Generating strategic analysis...` |
| 2:30 | Railway logs show `[OK] Analysis completed` |
| 2:31 | Supabase shows `status='completed'` with full report |

**Total time:** ~2-3 minutes from form submit to completed AI report

---

## 📞 If It Still Doesn't Work

Take screenshots of:
1. Railway Variables tab (showing all env vars - you can blur sensitive values)
2. Railway deployment logs (especially any errors)
3. Supabase SQL Editor query result for `SELECT * FROM submissions`

Then I'll help debug further.

---

## ✅ Success Criteria

You know it's working when:

1. ✅ Form submission creates row in Supabase immediately
2. ✅ Railway logs show processing messages (`[APIFY]`, `[AI]`)
3. ✅ Supabase shows `status='completed'` after 1-2 minutes
4. ✅ `report_json` field contains AI-generated report (5KB-20KB)
5. ✅ Admin dashboard shows submission with full report

**Once all 5 work → System is ready for your dad to use!**

---

**Next Steps After This Works:**
1. Grant your dad admin access in Supabase
2. Show him how to login at `/admin/login`
3. Show him how to view reports in dashboard
4. He can manually copy reports and email to clients

---

**Last Updated:** January 2025
**Status:** CRITICAL FIX REQUIRED
