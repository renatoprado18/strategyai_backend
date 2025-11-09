# 🔐 Environment Variables Configuration

Complete guide for configuring environment variables for Railway (backend) and Vercel (frontend).

---

## 🚂 Railway (Backend - FastAPI)

### Required Environment Variables

```bash
# ============================================================================
# DATABASE & AUTHENTICATION
# ============================================================================

# Supabase PostgreSQL Database
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...  # Service role key (bypasses RLS)
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...      # Anon key (respects RLS)

# JWT Authentication
JWT_SECRET=your-super-secret-jwt-key-min-32-characters-long-random-string

# Upstash Redis (Caching & Rate Limiting)
UPSTASH_REDIS_URL=https://your-redis.upstash.io
UPSTASH_REDIS_TOKEN=AYC1AAIjcDE...

# ============================================================================
# AI SERVICES (Progressive Enrichment)
# ============================================================================

# OpenRouter (GPT-4o-mini for AI inference) - NEW! REQUIRED FOR PROGRESSIVE FORM
OPENROUTER_API_KEY=sk-or-v1-...
# Cost: $0.15 per 1M tokens
# Used for: Industry classification, field suggestions, data validation
# Get key at: https://openrouter.ai/

# Perplexity (Market Research) - Optional
PERPLEXITY_API_KEY=pplx-...
# Used for: Market intelligence and competitive analysis

# ============================================================================
# DATA ENRICHMENT SOURCES
# ============================================================================

# Clearbit (Company Data) - REQUIRED FOR PROGRESSIVE FORM
CLEARBIT_API_KEY=sk_...
# Cost: $0.10 per call
# Used for: Employee count, revenue, founded year, company details
# Get key at: https://dashboard.clearbit.com/

# Google Places (Location Verification) - REQUIRED FOR PROGRESSIVE FORM
GOOGLE_PLACES_API_KEY=AIza...
# Cost: $0.02 per call
# Used for: Verified address, phone, ratings, business hours
# Get key at: https://console.cloud.google.com/

# Proxycurl (LinkedIn Data) - OPTIONAL (Layer 3 enrichment)
PROXYCURL_API_KEY=...
# Cost: $0.03 per call
# Used for: LinkedIn company data, follower count, profile info
# Get key at: https://nubela.co/proxycurl/

# ============================================================================
# DATA COLLECTION
# ============================================================================

# Apify (Web Scraping) - Optional
APIFY_API_TOKEN=apify_api_...
# Used for: Advanced web scraping and data extraction

# ============================================================================
# OPTIONAL SERVICES
# ============================================================================

# Sentry (Error Tracking) - Optional but recommended
SENTRY_DSN=https://...@sentry.io/...
# Used for: Error monitoring and performance tracking

# CORS Origins (Allowed Frontend URLs)
ALLOWED_ORIGINS=https://your-frontend.vercel.app,http://localhost:3000

# Environment
ENVIRONMENT=production  # or development/staging
```

### 📝 Notes for Railway Configuration:

1. **Go to Railway Dashboard** → Your Project → Variables
2. **Add all variables above** (at minimum: SUPABASE, JWT, REDIS, OPENROUTER, CLEARBIT, GOOGLE_PLACES)
3. **Deployment will auto-restart** when variables are added
4. **Verify deployment** by checking logs for successful startup

### ⚠️ Critical Environment Variables (Must Have):
- `SUPABASE_URL` ✅
- `SUPABASE_SERVICE_KEY` ✅
- `SUPABASE_ANON_KEY` ✅
- `JWT_SECRET` ✅
- `UPSTASH_REDIS_URL` ✅
- `UPSTASH_REDIS_TOKEN` ✅
- `OPENROUTER_API_KEY` ✅ **NEW - For progressive form AI**
- `CLEARBIT_API_KEY` ✅ **NEW - For company enrichment**
- `GOOGLE_PLACES_API_KEY` ✅ **NEW - For location verification**

### 🆓 Optional (Graceful Degradation):
- `PROXYCURL_API_KEY` - Progressive form works without (skips LinkedIn enrichment)
- `PERPLEXITY_API_KEY` - Market research still works with fallbacks
- `APIFY_API_TOKEN` - Web scraping uses alternative methods
- `SENTRY_DSN` - Errors still logged to console

---

## ▲ Vercel (Frontend - Next.js)

### Required Environment Variables

```bash
# ============================================================================
# BACKEND API
# ============================================================================

# Backend API URL (Railway deployment URL)
NEXT_PUBLIC_API_URL=https://your-backend.up.railway.app

# Example:
# NEXT_PUBLIC_API_URL=https://strategy-ai-backend-production.up.railway.app
```

### 📝 Notes for Vercel Configuration:

1. **Go to Vercel Dashboard** → Your Project → Settings → Environment Variables
2. **Add variable**:
   - Key: `NEXT_PUBLIC_API_URL`
   - Value: `https://your-backend.up.railway.app`
   - Environments: ✅ Production, ✅ Preview, ✅ Development
3. **Redeploy** the project to apply changes
4. **Verify** by checking browser console that API calls go to correct URL

### ⚠️ Important:
- The `NEXT_PUBLIC_` prefix makes it available in browser
- Must be set BEFORE build time (not runtime)
- Railway URL format: `https://{project-name}.up.railway.app`
- Find Railway URL in: Railway Dashboard → Your Project → Settings → Domains

---

## 🧪 Local Development (.env Files)

### Backend (.env)
Create `C:\Users\pradord\Documents\Projects\strategy-ai-backend\.env`:

```bash
# Copy all Railway variables here for local dev
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
SUPABASE_ANON_KEY=eyJ...
JWT_SECRET=local-dev-secret-key-at-least-32-characters
UPSTASH_REDIS_URL=https://your-redis.upstash.io
UPSTASH_REDIS_TOKEN=AYC...
OPENROUTER_API_KEY=sk-or-v1-...
CLEARBIT_API_KEY=sk_...
GOOGLE_PLACES_API_KEY=AIza...
PROXYCURL_API_KEY=...  # Optional
PERPLEXITY_API_KEY=...  # Optional
ALLOWED_ORIGINS=http://localhost:3000
ENVIRONMENT=development
```

### Frontend (.env.local)
Create `C:\Users\pradord\Documents\Projects\rfap_landing\.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

## 🔑 How to Get API Keys

### OpenRouter (GPT-4o-mini) - **NEW & REQUIRED**
1. Visit: https://openrouter.ai/
2. Sign up / Log in
3. Go to: Keys → Create Key
4. Copy key (starts with `sk-or-v1-...`)
5. **Cost**: $0.15 per 1M tokens (~$0.001 per enrichment)

### Clearbit (Company Data) - **NEW & REQUIRED**
1. Visit: https://clearbit.com/
2. Sign up for free trial or paid plan
3. Go to: Dashboard → API Keys
4. Copy secret key (starts with `sk_...`)
5. **Cost**: $0.10 per enrichment call

### Google Places API - **NEW & REQUIRED**
1. Visit: https://console.cloud.google.com/
2. Create new project or select existing
3. Enable "Places API"
4. Go to: Credentials → Create Credentials → API Key
5. Restrict key to Places API for security
6. **Cost**: $0.02 per call

### Proxycurl (LinkedIn) - **OPTIONAL**
1. Visit: https://nubela.co/proxycurl/
2. Sign up for free tier (1000 credits)
3. Copy API key from dashboard
4. **Cost**: $0.03 per call

### Upstash Redis - **REQUIRED**
1. Visit: https://upstash.com/
2. Create free database
3. Copy REST URL and TOKEN
4. **Cost**: Free tier (10K requests/day)

### Supabase - **REQUIRED**
1. Visit: https://supabase.com/
2. Create project
3. Copy URL and keys from: Settings → API
4. **Cost**: Free tier (500MB database)

---

## 💰 Cost Estimates

### Per Progressive Enrichment (Fresh):
- OpenRouter (AI): ~$0.001
- Clearbit: $0.10
- Google Places: $0.02
- Proxycurl: $0.03 (optional)
- **Total**: ~$0.15 per enrichment

### With 60% Cache Hit Rate:
- 40 fresh × $0.15 = $6.00
- 60 cached × $0.00 = $0.00
- **Monthly (100 enrichments)**: $6.00
- **Annual**: $72.00

### Free Services:
- Metadata scraping: $0.00
- IP geolocation: $0.00
- ReceitaWS (Brazilian CNPJ): $0.00
- Upstash Redis (free tier): $0.00
- Supabase (free tier): $0.00

---

## ✅ Verification Checklist

### After Setting Railway Variables:
- [ ] Backend deployment succeeded (check Railway logs)
- [ ] No error about missing env vars in logs
- [ ] Health check returns 200 OK: `GET https://your-backend.up.railway.app/health`
- [ ] OpenAPI docs accessible: `GET https://your-backend.up.railway.app/docs`

### After Setting Vercel Variables:
- [ ] Frontend deployment succeeded (check Vercel logs)
- [ ] Browser console shows correct API URL
- [ ] No CORS errors in browser console
- [ ] Forms can connect to backend API

### Test Progressive Enrichment:
1. Open frontend: `https://your-frontend.vercel.app`
2. Enter website URL: `techstart.com.br`
3. Wait 2-3 seconds
4. Verify fields auto-fill with green shimmer
5. Check confidence badges appear
6. Verify Layer 2 and Layer 3 complete

---

## 🐛 Troubleshooting

### Backend Won't Start:
- Check Railway logs for missing env vars
- Ensure all REQUIRED variables are set
- Verify Supabase credentials are correct
- Check Redis URL format (must include https://)

### Frontend Can't Reach Backend:
- Verify `NEXT_PUBLIC_API_URL` is correct Railway URL
- Check CORS origins in backend include Vercel URL
- Verify Railway app is running (check Railway dashboard)
- Test backend directly: `curl https://your-backend.up.railway.app/health`

### Progressive Enrichment Not Working:
- Check browser console for errors
- Verify OpenRouter API key is set in Railway
- Check Clearbit/Google Places keys are valid
- Test with simple website first (e.g., `google.com`)

### Costs Too High:
- Check cache hit rate in admin dashboard
- Verify 30-day cache TTL is working
- Consider disabling Proxycurl (optional)
- Use free sources only for testing

---

## 📞 Support

If you encounter issues:
1. Check Railway logs: Railway Dashboard → Deployments → View Logs
2. Check Vercel logs: Vercel Dashboard → Deployments → Function Logs
3. Verify all environment variables are set correctly
4. Test each API key individually (curl/Postman)

---

**Last Updated**: 2025-11-09
**Version**: 1.0 (Progressive Enrichment Launch)
