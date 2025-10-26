# ⚠️ CRITICAL: Railway CORS Fix Required

## Problem

Frontend at `https://strategyai-landing.vercel.app` is blocked by CORS policy:

```
Access to fetch at 'https://web-production-c5845.up.railway.app/api/admin/submissions'
from origin 'https://strategyai-landing.vercel.app' has been blocked by CORS policy
```

## Root Cause

Railway environment variable `ALLOWED_ORIGINS` does not include the Vercel production domain.

## Solution (MANUAL - Railway Dashboard Required)

### Step 1: Go to Railway Dashboard

1. Open https://railway.app
2. Navigate to your backend project
3. Click **"Variables"** tab

### Step 2: Update ALLOWED_ORIGINS

Find the `ALLOWED_ORIGINS` variable and update it to:

```
https://strategyai-landing.vercel.app,http://localhost:3000,http://localhost:3001
```

**CRITICAL NOTES:**
- ✅ Use commas to separate origins (NO SPACES)
- ✅ Include `https://` prefix for production domain
- ✅ Keep localhost for local development
- ❌ DO NOT add spaces after commas
- ❌ DO NOT add trailing slashes

### Step 3: Redeploy

Railway will automatically redeploy the service when you save the environment variable.

**Wait 2-3 minutes** for the deployment to complete.

## Verification

After Railway redeploys, test the frontend:

1. Open https://strategyai-landing.vercel.app/admin/dashboard-x9k2p
2. Log in with admin credentials
3. Check browser console - CORS errors should be gone
4. Dashboard should load submissions successfully

## Current Code Reference

The CORS configuration is in `main.py:49-52`:

```python
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001"
).split(",")
```

This splits the environment variable by commas and adds all origins to the CORS middleware.

## If Still Not Working

1. **Check Railway logs** - Look for CORS middleware initialization
2. **Verify Vercel domain** - Make sure the domain matches exactly
3. **Hard refresh** - Ctrl+Shift+R in browser to clear cache
4. **Check for typos** - Common mistakes:
   - `http` instead of `https`
   - Trailing slash: `https://strategyai-landing.vercel.app/`
   - Spaces: `https://strategyai-landing.vercel.app, http://localhost:3000`

---

**Status:** ⏳ Waiting for manual Railway dashboard update

**Created:** 2025-10-26
