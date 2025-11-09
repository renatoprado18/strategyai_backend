# 🚀 Deployment Checklist - Progressive Enrichment System

## ✅ Code Pushed to GitHub

### Backend Repository
- ✅ **Commit**: `feat: Add intelligent progressive enrichment system with AI auto-fill`
- ✅ **Files**: 22 files changed, 6,866 lines added
- ✅ **Status**: Pushed to `main` branch
- ✅ **Railway**: Will auto-deploy on push

### Frontend Repository
- ✅ **Commit**: `feat: Add intelligent progressive form with auto-fill animations`
- ✅ **Files**: 4 files changed, 1,143 lines added
- ✅ **Status**: Pushed to `main` branch
- ✅ **Vercel**: Will auto-deploy on push

---

## 🔧 Required Actions (DO THESE NOW)

### 1. Railway Backend Configuration

**Go to**: https://railway.app/ → Your Project → Variables

**Add these NEW environment variables**:

```bash
# Progressive Enrichment (NEW - REQUIRED)
OPENROUTER_API_KEY=sk-or-v1-your-key-here
CLEARBIT_API_KEY=sk_your-key-here
GOOGLE_PLACES_API_KEY=AIza-your-key-here

# Optional (gracefully degrades if missing)
PROXYCURL_API_KEY=your-key-here
```

**How to get keys**: See `ENVIRONMENT_VARIABLES.md` for detailed instructions

### 2. Run Database Migration

**Option A - Supabase Dashboard** (Recommended):
1. Go to: https://supabase.com/dashboard → Your Project → SQL Editor
2. Open file: `migrations/002_create_progressive_enrichment_tables.sql`
3. Copy entire contents
4. Paste into SQL Editor
5. Click "Run"
6. Verify: "Migration 002: Progressive enrichment tables created successfully"

**Option B - Command Line**:
```bash
# Using psql
psql $SUPABASE_URL -f migrations/002_create_progressive_enrichment_tables.sql
```

### 3. Verify Railway Deployment

**Check deployment logs**:
1. Go to Railway Dashboard → Deployments
2. Wait for build to complete (~3-5 minutes)
3. Check logs for:
   - ✅ "Application startup complete"
   - ✅ "Uvicorn running on http://0.0.0.0:8000"
   - ⚠️ NO errors about missing environment variables

**Test health endpoint**:
```bash
curl https://your-backend.up.railway.app/health
# Expected: {"status": "healthy", ...}
```

**Test OpenAPI docs**:
Open browser: `https://your-backend.up.railway.app/docs`
- Should see Swagger UI with all API endpoints
- Look for new `/api/enrichment/progressive/*` endpoints

### 4. Verify Vercel Deployment

**Check build logs**:
1. Go to Vercel Dashboard → Deployments
2. Wait for build to complete (~2-3 minutes)
3. Check build output for:
   - ✅ " ✓ Compiled successfully"
   - ✅ " ✓ Generating static pages"
   - ⚠️ NO TypeScript errors

**Test frontend**:
Open: `https://your-frontend.vercel.app`
- Page should load without errors
- Open browser console (F12)
- Look for console logs about API URL
- Should NOT see CORS errors

---

## 🧪 End-to-End Testing

### Test Progressive Enrichment Flow

1. **Open frontend**: `https://your-frontend.vercel.app`

2. **Enter test company**:
   - Website: `google.com`
   - Email: `test@google.com`

3. **Trigger enrichment** (click out of website field)

4. **Watch for**:
   - ⏱️ "Analisando sua empresa..." toast
   - ⏱️ 2-3 seconds: Company name and location slide in
   - ⏱️ 6-7 seconds: Industry, description, employee count appear
   - ⏱️ 10-11 seconds: "Análise completa!" toast

5. **Verify UI**:
   - ✅ Fields have green shimmer effect
   - ✅ Confidence badges show percentages
   - ✅ Sparkles icon appears in auto-filled fields
   - ✅ Can edit auto-filled values (badge changes to "Editado")

6. **Check browser console**:
   - Should see SSE connection established
   - Should see layer1_complete, layer2_complete events
   - NO errors about API calls

### If Enrichment Fails

**Backend not configured**:
- Error: "OpenRouter API key not configured"
- Solution: Add `OPENROUTER_API_KEY` to Railway

**Clearbit not configured**:
- Symptom: Only Layer 1 completes (basic data only)
- Solution: Add `CLEARBIT_API_KEY` to Railway

**Frontend can't reach backend**:
- Error: "Failed to fetch" or CORS error
- Solution: Verify `NEXT_PUBLIC_API_URL` in Vercel
- Check Railway CORS: `ALLOWED_ORIGINS` includes Vercel URL

---

## 📊 Admin Dashboard (For Your Dad)

### Check Enrichment Transparency

1. **Submit test form** (as above)

2. **Log into admin dashboard**: `https://your-frontend.vercel.app/admin/login`

3. **Go to submissions** (should see test submission)

4. **View enrichment details** (future feature):
   - Field-by-field source attribution
   - Cost breakdown
   - Confidence scores
   - Cache hit/miss status

*Note: Full transparency panel coming in Phase 2*

---

## 💰 Cost Monitoring

### First Week: Monitor Costs

**OpenRouter (AI)**:
- Dashboard: https://openrouter.ai/activity
- Expected: ~$0.001 per enrichment
- Alert if: > $1.00/day

**Clearbit**:
- Dashboard: https://dashboard.clearbit.com/
- Expected: $0.10 per enrichment
- Alert if: > $10.00/day (100 enrichments)

**Google Places**:
- Dashboard: https://console.cloud.google.com/
- Expected: $0.02 per enrichment
- Alert if: > $2.00/day

**Total Expected** (100 enrichments/week):
- Week 1: ~$18.00 (no cache)
- Week 2+: ~$7.00/week (60% cache hit rate)

---

## 🐛 Troubleshooting Guide

### Backend Won't Deploy
```bash
# Check Railway logs
railway logs --tail

# Common issues:
# 1. Missing env var → Add to Railway
# 2. Python syntax error → Check deployment logs
# 3. Import error → Verify all files pushed
```

### Frontend Won't Build
```bash
# Check Vercel logs in dashboard

# Common issues:
# 1. TypeScript error → Check build logs for details
# 2. Missing env var → Add NEXT_PUBLIC_API_URL to Vercel
# 3. Import error → Verify all files pushed
```

### Enrichment Not Auto-Filling
**Symptom**: User types website, nothing happens

**Debug steps**:
1. Open browser console (F12)
2. Look for errors
3. Check Network tab for API calls
4. Verify SSE connection established

**Common causes**:
- Backend API key missing → Check Railway env vars
- CORS error → Check `ALLOWED_ORIGINS` in Railway
- API endpoint 404 → Verify backend deployed correctly

### Database Migration Failed
**Error**: "relation already exists"
- **Cause**: Migration already run
- **Solution**: This is OK, skip migration

**Error**: "syntax error at or near..."
- **Cause**: SQL syntax issue
- **Solution**: Copy migration file exactly as-is

---

## 📋 Post-Deployment Tasks

### Immediate (Next Hour)
- [ ] Add all environment variables to Railway
- [ ] Run database migration (002_create_progressive_enrichment_tables.sql)
- [ ] Verify Railway deployment successful
- [ ] Verify Vercel deployment successful
- [ ] Test enrichment with real company website
- [ ] Check browser console for errors

### This Week
- [ ] Monitor costs daily (OpenRouter, Clearbit, Google Places)
- [ ] Test with 10+ different company websites
- [ ] Gather user feedback on auto-fill experience
- [ ] Check cache hit rate in database

### Next Week (Phase 2)
- [ ] Build admin transparency panel
- [ ] Add field-level source attribution UI
- [ ] Implement cost breakdown visualizations
- [ ] Add enrichment analytics dashboard
- [ ] Optimize cache hit rate to 70%+

---

## 🎯 Success Metrics (Week 1)

### User Experience
- [ ] Time to first auto-fill: < 2 seconds ✅
- [ ] Form completion rate: > 80% (vs ~40% baseline)
- [ ] User edit rate: < 20% of auto-filled fields
- [ ] No user complaints about slow forms

### Technical Performance
- [ ] Layer 1 complete: < 2s ✅
- [ ] Layer 2 complete: < 6s ✅
- [ ] Layer 3 complete: < 10s ✅
- [ ] Zero deployment errors
- [ ] Zero runtime errors in logs

### Business Impact
- [ ] Higher lead quality (more complete data)
- [ ] Faster sales cycles (better qualified leads)
- [ ] Cost per enrichment: < $0.20 ✅
- [ ] Dad can see data transparency

---

## 📞 Emergency Contacts

**If something breaks**:

1. **Check status**:
   - Railway: https://railway.app/status
   - Vercel: https://vercel.com/status
   - Supabase: https://status.supabase.com/

2. **Rollback if needed**:
   ```bash
   # Backend - revert to previous commit
   cd strategy-ai-backend
   git revert HEAD
   git push origin main

   # Frontend - revert to previous commit
   cd rfap_landing
   git revert HEAD
   git push origin main
   ```

3. **Disable progressive enrichment**:
   - Option 1: Remove OpenRouter API key from Railway (falls back to basic form)
   - Option 2: Use old form component (`landing-form.tsx` instead of `progressive-enrichment-form.tsx`)

---

## ✅ Final Checklist

Before marking deployment complete:

- [ ] Backend pushed to GitHub ✅
- [ ] Frontend pushed to GitHub ✅
- [ ] Railway deployment succeeded
- [ ] Vercel deployment succeeded
- [ ] All environment variables added
- [ ] Database migration run successfully
- [ ] Health endpoint returns 200 OK
- [ ] Frontend loads without errors
- [ ] Progressive enrichment works end-to-end
- [ ] Browser console has no errors
- [ ] Tested with real company website
- [ ] Costs monitored in provider dashboards

---

**Status**: 🚀 Ready for deployment
**Next Steps**: Add environment variables → Run migration → Test
**Est. Time**: 30 minutes to full deployment
