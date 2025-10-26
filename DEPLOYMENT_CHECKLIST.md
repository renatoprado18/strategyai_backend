# Deployment Checklist

Quick checklist to ensure everything is configured correctly.

---

## ✅ Railway Backend Configuration

### Environment Variables (All Set ✓)

- ✅ `SUPABASE_URL` - Configured
- ✅ `SUPABASE_ANON_KEY` - Configured
- ✅ `SUPABASE_SERVICE_KEY` - Configured
- ✅ `JWT_SECRET` - Configured
- ✅ `JWT_ALGORITHM` - Configured (HS256)
- ✅ `OPENROUTER_API_KEY` - Configured
- ✅ `APIFY_API_TOKEN` - Configured
- ✅ `ALLOWED_ORIGINS` - Configured with Vercel URL ✓

### Variables to REMOVE

- ❌ `DATABASE_URL=sqlite:///./database.db` - **DELETE THIS** (no longer needed, using Supabase)

---

## ✅ Supabase Configuration

### Step 1: Run Database Migrations

**Migration 1: Submissions Table** (Already Done ✓)
- File: `migrations/001_initial_schema.sql` (or `supabase-schema.sql`)
- Creates: `submissions` table with RLS policies

**Migration 2: Admin Users Table** (NEW - MUST RUN)
1. Go to Supabase → **SQL Editor**
2. Open new query
3. Copy and paste: `migrations/002_admin_users.sql`
4. Click **Run**

This creates:
- `admin_users` table
- Helper functions (grant_admin_access, revoke_admin_access, is_admin)
- RLS policies
- Indexes

### Step 2: Create Your First Admin

After running migration, grant yourself admin access:

```sql
-- First, find your User ID:
-- Go to Authentication → Users → Copy your User UID

-- Then grant access:
SELECT grant_admin_access(
    target_user_id := 'PASTE-YOUR-USER-UUID-HERE',
    target_email := 'your-email@example.com',
    admin_notes := 'Initial admin - company owner'
);
```

---

## ✅ Vercel Frontend Configuration

### Environment Variables

Only ONE variable needed:
- ✅ `NEXT_PUBLIC_API_URL=https://web-production-c5845.up.railway.app`

**Your configuration is CORRECT!** ✓

---

## 🧪 Testing Checklist

### Test 1: Public Form Submission (No Auth)

1. Go to: `https://your-vercel-url.vercel.app`
2. Fill out lead form
3. Submit
4. ✅ Should see "Thank You" page
5. ✅ Check Railway logs - should see submission processing

### Test 2: User Signup

1. Go to: `https://your-vercel-url.vercel.app/admin/signup`
2. Create account with email and password
3. ✅ Should see success message
4. ✅ Should redirect to login page

### Test 3: Login Without Admin Access (Should Fail)

1. Go to: `https://your-vercel-url.vercel.app/admin/login`
2. Login with the account you just created
3. ❌ **Expected:** "Access denied. Your account does not have admin privileges."

This is correct behavior! Continue to next step.

### Test 4: Grant Admin Access

1. Go to Supabase → **Authentication** → **Users**
2. Find the user you created
3. Copy their **User UID**
4. Go to **SQL Editor** → New Query
5. Run:

```sql
SELECT grant_admin_access(
    target_user_id := 'paste-user-uid-here',
    target_email := 'the-email-you-signed-up-with',
    admin_notes := 'Test admin account'
);
```

6. ✅ Should return `true`

### Test 5: Login With Admin Access (Should Work)

1. Go to: `https://your-vercel-url.vercel.app/admin/login`
2. Login with same credentials
3. ✅ Should successfully login
4. ✅ Should redirect to admin dashboard
5. ✅ Should see all submissions

---

## 🔍 Troubleshooting

### Issue: "CORS error" in browser console

**Solution:** Verify `ALLOWED_ORIGINS` on Railway includes your Vercel URL

```
ALLOWED_ORIGINS=http://localhost:3000,https://strategyai-landing.vercel.app
```

Make sure to include:
- Your production Vercel URL
- Any preview/branch URLs (e.g., `https://app-git-main-username.vercel.app`)

### Issue: "Network error" on form submission

**Solution:** Verify `NEXT_PUBLIC_API_URL` on Vercel matches your Railway URL

### Issue: Login shows "Access denied"

**Solution:** User needs admin access granted in Supabase

1. Check if user exists in admin_users table:
```sql
SELECT * FROM admin_users WHERE email = 'user@email.com';
```

2. If not found, grant access:
```sql
SELECT grant_admin_access(
    target_user_id := 'user-uuid',
    target_email := 'user@email.com',
    admin_notes := 'Reason for granting'
);
```

### Issue: Backend returns 500 error

**Solution:** Check Railway logs for detailed error message

Common causes:
- Missing environment variables
- Supabase migrations not run
- Invalid API keys

---

## 📋 Final Verification

### Railway Dashboard Should Show:

- ✅ Deployment status: **Successful**
- ✅ All env vars configured (except DATABASE_URL - delete it)
- ✅ Service running with no errors in logs

### Supabase Dashboard Should Show:

- ✅ `submissions` table exists
- ✅ `admin_users` table exists
- ✅ At least one user in **Authentication → Users**
- ✅ At least one admin in `admin_users` table

### Vercel Dashboard Should Show:

- ✅ Deployment status: **Ready**
- ✅ `NEXT_PUBLIC_API_URL` configured
- ✅ No build errors

---

## 🎯 Quick Commands Reference

### Check if user is admin:
```sql
SELECT is_admin('user-uuid');
```

### List all admins:
```sql
SELECT email, granted_at, notes
FROM admin_users
WHERE is_active = true;
```

### Grant admin access:
```sql
SELECT grant_admin_access(
    target_user_id := 'USER_UUID',
    target_email := 'user@email.com',
    admin_notes := 'Reason'
);
```

### Revoke admin access:
```sql
SELECT revoke_admin_access('USER_UUID');
```

---

## 📚 Documentation Files

- `ADMIN_ACCESS_GUIDE.md` - Complete admin access management guide
- `VERCEL_DEPLOYMENT.md` - Vercel deployment instructions (in frontend repo)
- `migrations/002_admin_users.sql` - Admin users table migration

---

**Status:** Ready for Production ✅

**Last Updated:** January 2025
