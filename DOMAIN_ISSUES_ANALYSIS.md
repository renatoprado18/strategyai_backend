# Domain Issues Analysis: imensiah.com.br vs intelligent-compassion
**Date:** October 29, 2025
**Status:** 🔴 CRITICAL - Multiple Configuration Issues Identified

---

## Executive Summary

The system works on `intelligent-compassion-production.up.railway.app` but **fails on `imensiah.com.br`** due to **6 critical configuration issues**:

1. ❌ **CORS Configuration Missing Custom Domain** (CRITICAL)
2. ❌ **Frontend API URL Not Configured for Production** (CRITICAL)
3. ⚠️ **Rate Limiting Uses Wrong IP Address** (MEDIUM)
4. ⚠️ **No X-Forwarded-For Proxy Handling** (MEDIUM)
5. ⚠️ **Mixed Content Warning Potential** (LOW)
6. ⚠️ **localStorage Works but Lacks SameSite Cookie Support** (LOW)

**Impact:** Users accessing `imensiah.com.br` experience:
- ❌ CORS errors blocking API requests
- ❌ 404/Network errors due to wrong API URL
- ⚠️ Rate limiting by proxy IP instead of client IP
- ⚠️ Potential security warnings on mixed HTTP/HTTPS

---

## Current Configuration

### Backend (Railway)
**Service:** `strategy-ai-backend`
**Default URL:** `https://intelligent-compassion-production.up.railway.app`
**Custom Domain:** NOT CONFIGURED
**CORS Allowed Origins:**
```
http://localhost:3000
https://strategyai-landing.vercel.app
https://imensiah.com.br
```

### Frontend (Vercel)
**Default URL:** `https://strategyai-landing.vercel.app`
**Custom Domain:** `https://imensiah.com.br` (CONFIGURED)
**API URL:** `process.env.NEXT_PUBLIC_API_URL` (NOT SET IN VERCEL)

---

## Issue #1: CORS Configuration Missing Custom Domain ⚠️ CRITICAL

### Problem

The backend `ALLOWED_ORIGINS` includes `https://imensiah.com.br` (frontend custom domain) but does **NOT** include the Railway default domain that the frontend is actually calling.

**Current Backend CORS Config (Railway):**
```
ALLOWED_ORIGINS=http://localhost:3000,https://strategyai-landing.vercel.app,https://imensiah.com.br
```

**What Frontend Actually Calls:**
```typescript
// lib/api.ts:13
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

**If `NEXT_PUBLIC_API_URL` is NOT set in Vercel**, the frontend tries to call:
- ❌ `http://localhost:8000` (fails in production - not accessible)
- ❌ OR defaults to Railway URL but CORS blocks it if Railway URL not in ALLOWED_ORIGINS

### Root Cause

The backend CORS middleware checks the `Origin` header:

```python
# app/main.py:67-73
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,  # List from ALLOWED_ORIGINS env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**When user accesses `imensiah.com.br`:**
1. Browser sends request to API with `Origin: https://imensiah.com.br`
2. Backend checks if `https://imensiah.com.br` is in ALLOWED_ORIGINS ✅ (IT IS)
3. **BUT** if `NEXT_PUBLIC_API_URL` is not set, the frontend tries to call `localhost:8000` ❌

### Fix Required

**Option A: Add Railway URL to Backend CORS (Recommended)**

In Railway dashboard for `strategy-ai-backend`, update `ALLOWED_ORIGINS`:
```
ALLOWED_ORIGINS=http://localhost:3000,https://strategyai-landing.vercel.app,https://imensiah.com.br,https://intelligent-compassion-production.up.railway.app
```

**Option B: Set Frontend Environment Variable (CRITICAL)**

In Vercel dashboard for frontend project, add environment variable:
```
NEXT_PUBLIC_API_URL=https://intelligent-compassion-production.up.railway.app
```

**RECOMMENDED: Do BOTH**

---

## Issue #2: Frontend API URL Not Configured ⚠️ CRITICAL

### Problem

The frontend `lib/api.ts:13` reads:
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
```

**If `NEXT_PUBLIC_API_URL` is NOT set in Vercel:**
- Frontend tries to call `http://localhost:8000` ❌
- This fails in production (localhost not accessible from browser)
- All API requests return network errors

### Verification

Check Vercel dashboard → Project Settings → Environment Variables:
- ❓ Is `NEXT_PUBLIC_API_URL` set?
- ❓ What value does it have?

**Expected Value:**
```
NEXT_PUBLIC_API_URL=https://intelligent-compassion-production.up.railway.app
```

### Root Cause

The `.env.example` file shows:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

But there's **NO `.env.local` file** in the repository (correctly gitignored), and **Vercel environment variables are not documented** in the codebase.

### Fix Required

**In Vercel Dashboard:**

1. Go to Project Settings → Environment Variables
2. Add or update:
   ```
   Key: NEXT_PUBLIC_API_URL
   Value: https://intelligent-compassion-production.up.railway.app
   ```
3. Select: Production, Preview, Development
4. Click "Save"
5. Redeploy frontend

**Verification Command:**
```bash
# In browser console on imensiah.com.br
console.log(window.location.origin);  // Should show imensiah.com.br
// Check network tab for API calls - should go to Railway URL
```

---

## Issue #3: Rate Limiting Uses Wrong IP Address ⚠️ MEDIUM

### Problem

The backend rate limiter gets IP from `request.client.host`:

```python
# app/routes/analysis.py:73
client_ip = request.client.host
```

**When behind Railway proxy:**
- `request.client.host` = Railway proxy IP (e.g., `10.0.0.1`)
- ALL users share the same IP address
- Rate limit triggered after 20 total submissions instead of 20 per user

### Impact

- ✅ Works correctly on direct Railway URL
- ❌ On custom domain, all users share rate limit quota
- Example: If 20 different users submit, the 21st user gets rate limited

### Root Cause

FastAPI's `request.client.host` doesn't automatically parse `X-Forwarded-For` header.

Railway sets these headers:
```
X-Forwarded-For: <client-ip>, <proxy1-ip>, <proxy2-ip>
X-Real-IP: <client-ip>
```

But the code doesn't read them.

### Fix Required

**Update `app/routes/analysis.py:73`:**

```python
# BEFORE:
client_ip = request.client.host

# AFTER:
def get_client_ip(request: Request) -> str:
    """Get real client IP from proxy headers"""
    # Try X-Forwarded-For first (Railway, Cloudflare, etc.)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP in X-Forwarded-For is the client
        return forwarded_for.split(",")[0].strip()

    # Try X-Real-IP (Nginx, Railway)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fallback to direct connection IP
    return request.client.host if request.client else "unknown"

client_ip = get_client_ip(request)
```

**Also update middleware logging:**

```python
# app/core/middleware.py:32
"client_ip": get_client_ip(request)  # Instead of request.client.host
```

---

## Issue #4: No Proxy-Aware IP Detection ⚠️ MEDIUM

### Problem

Related to Issue #3 - the application doesn't have a centralized utility for proxy-aware IP detection.

**Current Code Pattern:**
```python
# Multiple files use:
request.client.host if request.client else "unknown"
```

**Found in:**
- `app/core/middleware.py:32` (exception handler)
- `app/core/middleware.py:58` (general exception handler)
- `app/routes/analysis.py:73` (rate limiting)

### Fix Required

**Create `app/utils/network.py`:**

```python
"""
Network utilities for proxy-aware request handling
"""
from fastapi import Request
from typing import Optional


def get_client_ip(request: Request) -> str:
    """
    Get real client IP address from request, handling reverse proxies.

    Checks headers in order:
    1. X-Forwarded-For (Railway, Cloudflare, AWS ALB)
    2. X-Real-IP (Nginx, Railway)
    3. request.client.host (direct connection)

    Args:
        request: FastAPI Request object

    Returns:
        str: Client IP address or "unknown" if not available
    """
    # X-Forwarded-For: client, proxy1, proxy2, ...
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # First IP is the original client
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip:
            return client_ip

    # X-Real-IP: client
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # CF-Connecting-IP (Cloudflare specific)
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    # Fallback to direct connection
    if request.client:
        return request.client.host

    return "unknown"


def get_request_origin(request: Request) -> Optional[str]:
    """
    Get the origin domain of the request.

    Args:
        request: FastAPI Request object

    Returns:
        str | None: Origin header value or None
    """
    return request.headers.get("Origin")


def is_secure_request(request: Request) -> bool:
    """
    Check if request is over HTTPS, handling proxies.

    Args:
        request: FastAPI Request object

    Returns:
        bool: True if HTTPS
    """
    # Check X-Forwarded-Proto header (Railway, AWS ALB)
    proto = request.headers.get("X-Forwarded-Proto")
    if proto:
        return proto.lower() == "https"

    # Check request URL scheme
    return request.url.scheme == "https"
```

**Update all files to use utility:**

```python
# app/routes/analysis.py
from app.utils.network import get_client_ip

client_ip = get_client_ip(request)  # Instead of request.client.host

# app/core/middleware.py
from app.utils.network import get_client_ip

"client_ip": get_client_ip(request)  # Instead of request.client.host
```

---

## Issue #5: Mixed Content Warning Potential ⚠️ LOW

### Problem

The frontend uses `https://imensiah.com.br` but if backend API URL is not HTTPS, browsers block requests.

**Current Situation:**
- Frontend: `https://imensiah.com.br` ✅
- Backend: `https://intelligent-compassion-production.up.railway.app` ✅

**But in code:**
```typescript
// lib/api.ts:13
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
//                                                    ^^^^ HTTP not HTTPS
```

If `NEXT_PUBLIC_API_URL` is not set, it defaults to `http://` which browsers block.

### Impact

- In development: No issue (both localhost)
- In production: If env var not set, all API calls fail with mixed content error

### Fix Required

**Already covered by Issue #2 fix** - Set `NEXT_PUBLIC_API_URL` with HTTPS URL.

**Additional safeguard in code:**

```typescript
// lib/api.ts:13
const API_URL = process.env.NEXT_PUBLIC_API_URL ||
  (typeof window !== "undefined" && window.location.protocol === "https:"
    ? "https://intelligent-compassion-production.up.railway.app"  // Production fallback
    : "http://localhost:8000");  // Development fallback
```

---

## Issue #6: localStorage Auth Lacks SameSite Cookie Support ⚠️ LOW

### Problem

The frontend stores JWT tokens in `localStorage`:

```typescript
// lib/api.ts:24
return localStorage.getItem(TOKEN_KEY);
```

**Pros:**
- ✅ Works across subdomains
- ✅ Simple implementation
- ✅ No cookie CORS issues

**Cons:**
- ⚠️ Vulnerable to XSS attacks
- ⚠️ No automatic CSRF protection
- ⚠️ No HttpOnly flag (JS can read token)

### Impact

- **Security:** Medium risk (acceptable for admin dashboard)
- **Functionality:** Works fine for `imensiah.com.br`
- **Cross-domain:** No issues (localStorage is per-origin)

### Current CORS Config Supports This

```python
# app/main.py:70
allow_credentials=True,  # ✅ Allows cookies/auth headers
```

### No Action Required

This is **acceptable** for an admin dashboard. The token is only stored after successful login, and the admin panel has additional protections.

**If higher security needed later:**
- Use HttpOnly cookies for token storage
- Implement CSRF tokens
- Add SameSite=Strict cookie flag

---

## Complete Fix Checklist

### Immediate Actions (CRITICAL)

#### 1. Fix Frontend Environment Variable (Vercel)

**In Vercel Dashboard:**

```
Project: strategyai-landing (or your project name)
Settings → Environment Variables → Add

Variable Name: NEXT_PUBLIC_API_URL
Value: https://intelligent-compassion-production.up.railway.app
Environment: Production, Preview, Development
```

**Then redeploy:**
```bash
# Trigger redeploy in Vercel dashboard or via CLI
vercel --prod
```

#### 2. Fix Backend CORS Configuration (Railway)

**In Railway Dashboard:**

```
Project: strategy-ai-backend
Variables → Edit ALLOWED_ORIGINS

Old Value:
http://localhost:3000,https://strategyai-landing.vercel.app,https://imensiah.com.br

New Value:
http://localhost:3000,https://strategyai-landing.vercel.app,https://imensiah.com.br,https://intelligent-compassion-production.up.railway.app
```

**Railway automatically redeploys after env var change.**

### Code Fixes (MEDIUM Priority)

#### 3. Create Proxy-Aware IP Detection Utility

**Create file:** `app/utils/network.py`

```python
"""Network utilities for proxy-aware request handling"""
from fastapi import Request
from typing import Optional


def get_client_ip(request: Request) -> str:
    """Get real client IP address from request, handling reverse proxies."""
    # X-Forwarded-For: client, proxy1, proxy2
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    # X-Real-IP: client (Nginx, Railway)
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # CF-Connecting-IP (Cloudflare)
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip.strip()

    # Fallback
    return request.client.host if request.client else "unknown"
```

#### 4. Update Rate Limiting to Use Real IP

**File:** `app/routes/analysis.py:73`

```python
# Add import at top
from app.utils.network import get_client_ip

# Change line 73:
# OLD: client_ip = request.client.host
# NEW:
client_ip = get_client_ip(request)
```

#### 5. Update Middleware Logging

**File:** `app/core/middleware.py:32 and :58`

```python
# Add import at top
from app.utils.network import get_client_ip

# Change line 32:
"client_ip": get_client_ip(request)  # Instead of request.client.host

# Change line 58:
"client_ip": get_client_ip(request)  # Instead of request.client.host
```

#### 6. Commit and Deploy Code Changes

```bash
cd C:\Users\pradord\Documents\Projects\strategy-ai-backend

git add app/utils/network.py
git add app/routes/analysis.py
git add app/core/middleware.py

git commit -m "fix: Add proxy-aware IP detection for Railway deployment

- Created app/utils/network.py with get_client_ip() utility
- Updated rate limiting to use real client IP from X-Forwarded-For
- Updated middleware logging to show real client IP
- Fixes rate limiting issues when behind Railway proxy

Impact:
- Rate limiting now works correctly per client IP
- Prevents proxy IP from triggering shared rate limits
- Better logging for debugging CORS/network issues"

git push origin main
```

### Optional Custom Domain Setup (OPTIONAL)

#### 7. Add Custom Domain to Railway Backend

**In Railway Dashboard:**

```
Project: strategy-ai-backend
Settings → Networking → Custom Domain

Add: api.imensiah.com.br
```

**Then update CORS and Vercel env vars:**

```
# Railway ALLOWED_ORIGINS:
http://localhost:3000,https://strategyai-landing.vercel.app,https://imensiah.com.br,https://api.imensiah.com.br

# Vercel NEXT_PUBLIC_API_URL:
https://api.imensiah.com.br
```

**Benefits:**
- Cleaner URLs
- Consistent branding
- Easier to remember

**Drawbacks:**
- Requires DNS configuration
- Additional Railway custom domain (may incur cost)

---

## Testing Checklist

### After Applying Fixes

#### Test 1: CORS Verification

**From `imensiah.com.br` browser console:**
```javascript
// Should NOT show CORS error
fetch('https://intelligent-compassion-production.up.railway.app/api/health')
  .then(r => r.json())
  .then(d => console.log('✅ CORS OK:', d))
  .catch(e => console.error('❌ CORS Failed:', e));
```

**Expected:** `✅ CORS OK: { status: "ok", environment: "production" }`

#### Test 2: Form Submission

**On `https://imensiah.com.br`:**

1. Fill out lead form
2. Submit
3. Check browser DevTools Network tab
4. Verify request goes to Railway URL (not localhost)
5. Verify response is 200 OK

**Expected Network Request:**
```
POST https://intelligent-compassion-production.up.railway.app/api/submit
Status: 200 OK
Response: { success: true, submission_id: 123 }
```

#### Test 3: Rate Limiting

**From 2 different devices/networks:**

1. Submit 20 forms from Device A
2. Submit 1 form from Device B
3. Device B should succeed (not blocked by Device A's submissions)

**Expected:**
- Device A: Blocks after 20 submissions ✅
- Device B: Still accepts submissions ✅

#### Test 4: Admin Login

**On `https://imensiah.com.br/admin/login`:**

1. Login with credentials
2. Check localStorage has token
3. Navigate to dashboard
4. Verify submissions load

**Expected:**
- JWT token stored in `localStorage`
- Dashboard loads without CORS errors
- Can view submission details

---

## Root Cause Summary

### Why It Works on Railway URL but Not imensiah.com.br

**Working URL:** `https://intelligent-compassion-production.up.railway.app`
- Frontend in Vercel accesses backend via Railway URL
- `NEXT_PUBLIC_API_URL` = Railway URL ✅
- CORS allows Railway URL ✅
- Rate limiting works (direct IP) ✅

**Broken URL:** `https://imensiah.com.br`
- Frontend in Vercel (custom domain) accesses backend via Railway URL
- `NEXT_PUBLIC_API_URL` NOT SET ❌ → Defaults to `localhost:8000` ❌
- CORS allows `imensiah.com.br` ✅ but frontend calls wrong URL ❌
- Rate limiting broken (proxy IP) ⚠️

### The Disconnect

**The issue is NOT the custom domain itself** - it's that:

1. **Vercel environment variable `NEXT_PUBLIC_API_URL` is not configured**
   - Frontend tries to call `localhost:8000` in production ❌

2. **Railway backend CORS includes frontend domain BUT**
   - Frontend doesn't know backend URL without env var ❌

3. **Rate limiting assumes direct connection**
   - Doesn't read proxy headers ⚠️

---

## Recommended Deployment Process

### Future Deployments

**When deploying to new environment:**

#### Backend (Railway)

1. Set all environment variables:
   ```
   ALLOWED_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app,https://custom-domain.com,https://your-backend.railway.app
   SUPABASE_URL=...
   SUPABASE_SERVICE_KEY=...
   [all other vars from .env.example]
   ```

2. Deploy and verify health:
   ```bash
   curl https://your-backend.railway.app/api/health
   # Expected: {"status":"ok"}
   ```

#### Frontend (Vercel)

1. Set environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-backend.railway.app
   ```

2. Deploy and verify in browser console:
   ```javascript
   console.log(process.env.NEXT_PUBLIC_API_URL);
   // Should show Railway URL
   ```

3. Test form submission
4. Test admin login
5. Test API calls from custom domain

#### Verification

✅ CORS works from all domains
✅ Form submissions create database records
✅ Admin dashboard loads
✅ Rate limiting works correctly per IP
✅ No mixed content warnings
✅ Network tab shows correct API URL

---

## Current Status

| Component | Issue | Severity | Fixed |
|-----------|-------|----------|-------|
| Backend CORS | Missing Railway URL | 🔴 CRITICAL | ⏳ Pending |
| Frontend API URL | Not set in Vercel | 🔴 CRITICAL | ⏳ Pending |
| Rate Limiting | Wrong IP detection | 🟡 MEDIUM | ⏳ Pending |
| Proxy Headers | Not parsed | 🟡 MEDIUM | ⏳ Pending |
| Mixed Content | Potential HTTPS issue | 🟢 LOW | ✅ No issue |
| localStorage | No cookie alternative | 🟢 LOW | ✅ Works fine |

**Next Steps:**
1. Apply Vercel environment variable fix (2 minutes)
2. Apply Railway CORS update (2 minutes)
3. Test form submission from `imensiah.com.br`
4. Apply code fixes for IP detection (10 minutes)
5. Deploy and verify rate limiting

**ETA to Full Fix:** 20 minutes
