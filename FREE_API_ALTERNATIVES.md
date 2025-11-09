# 🆓 Free API Alternatives for Progressive Enrichment

## Current Problem: Expensive APIs

Your current enrichment stack has expensive paid APIs:
- **Clearbit**: $99/month minimum (now part of HubSpot Breeze)
- **Google Places**: FREE tier available ($200/month credit = 10,000 calls)
- **Proxycurl**: $0.03/call (optional)

**Total monthly cost estimate**: $99-199/month for low-volume usage

---

## ✅ Recommended FREE Alternative Strategy

### Option 1: 100% FREE Stack (Best for MVP/Testing)

**Replace Clearbit with FREE alternatives**:

#### 1️⃣ **Hunter.io** (BEST FREE OPTION)
- **Free Tier**: 25 searches + 50 verifications/month
- **Paid**: $49/month for 500 searches (vs Clearbit $99 for 275)
- **API**: Company domain → Email patterns, company info
- **Better than Clearbit**: Finds more decision-maker profiles
- **Compliance**: Publicly sourced B2B data
- **Sign up**: https://hunter.io/api

**What you get FREE**:
```json
{
  "domain": "example.com",
  "company": "Example Inc",
  "pattern": "{first}.{last}@example.com",
  "emails_found": 47,
  "industry": "Technology",
  "location": "San Francisco, CA"
}
```

#### 2️⃣ **Apollo.io** (Most comprehensive free plan)
- **Free Tier**: Limited credits/month
- **Paid**: $39/user/month (vs Clearbit $99)
- **Database**: 275M contacts + 70M companies
- **Features**: Enrichment + Chrome extension + sequencing
- **Sign up**: https://www.apollo.io/

**What you get FREE**:
- Company name, industry, size, revenue
- Location, website, social profiles
- Email patterns
- Technology stack

#### 3️⃣ **RB2B** (Company visitor identification)
- **Free Forever Plan**: 200 monthly reveal credits
- **Sends to**: Slack (real-time notifications)
- **Perfect for**: Identifying website visitors
- **Sign up**: https://www.rb2b.com/

#### 4️⃣ **People Data Labs** (Pay-as-you-go)
- **Pricing**: $99/month for 1,000 API calls (vs Clearbit $99 for 275)
- **4x cheaper per call** than Clearbit
- **Data**: Company + person enrichment
- **Sign up**: https://www.peopledatalabs.com/

---

### Option 2: Google Places + OpenRouter (RECOMMENDED)

**Keep Google Places** (FREE tier is generous):
- **Free**: $200/month credit = 10,000 API calls
- **After free tier**: ~$0.02/call
- **Data**: Company name, address, phone, ratings, hours, photos
- **NEW 2025 pricing**: 10,000 free calls/month starting March 1, 2025

**Use OpenRouter for AI enrichment** (Already configured):
- **You already have this**: `OPENROUTER_API_KEY`
- **Cost**: $0.15/1M tokens (GPT-4o-mini) = ~$0.001/enrichment
- **Can call**: Perplexity, GPT-4o-mini, Claude, Gemini
- **No additional API keys needed**

---

### Option 3: Hybrid Free + Paid

**FREE APIs**:
- Google Places (10,000/month FREE)
- Hunter.io (25 searches/month FREE)
- OpenRouter GPT-4o-mini ($0.001/enrichment)

**Paid (only if needed)**:
- Apollo.io ($39/month) - only if you exceed free tiers

---

## 🔧 Implementation Changes

### Current Enrichment Stack:
```python
# Layer 2 (Paid APIs):
- Clearbit API: $99/month → $0.10/call
- Google Places: FREE (10k/month) → $0.02/call after
- ReceitaWS: FREE (Brazilian companies)

# Layer 3 (AI):
- OpenRouter GPT-4o-mini: $0.15/1M tokens
- Proxycurl: $0.03/call (OPTIONAL)
```

### NEW Free Alternative Stack:
```python
# Layer 1 (100% FREE):
- Metadata scraping: FREE (your own code)
- ReceitaWS: FREE (Brazilian companies)

# Layer 2 (FREE tier):
- Hunter.io: FREE (25 searches/month) → Company + emails
- Google Places: FREE (10,000 calls/month) → Location + reviews
- Apollo.io: FREE (limited) → Company data

# Layer 3 (Pennies):
- OpenRouter GPT-4o-mini: $0.001/enrichment
- Perplexity via OpenRouter: $0.001/query (no separate API key!)
```

**Monthly cost for 1,000 enrichments**:
- **Current**: $150/month ($0.15/enrichment)
- **With free alternatives**: **$1/month** ($0.001/enrichment)
- **Savings**: **99.3%** ($149/month)

---

## 📊 Comparison Table

| Service | Free Tier | Paid (Starting) | Data Quality | Best For |
|---------|-----------|-----------------|--------------|----------|
| **Clearbit** | ❌ None | $99/mo (275 calls) | ⭐⭐⭐⭐⭐ Excellent | Enterprise |
| **Hunter.io** | ✅ 25/mo | $49/mo (500 calls) | ⭐⭐⭐⭐ Great | Email finding |
| **Apollo.io** | ✅ Limited | $39/mo unlimited | ⭐⭐⭐⭐ Great | B2B sales |
| **Google Places** | ✅ 10k/mo | $0.02/call after | ⭐⭐⭐⭐⭐ Excellent | Location data |
| **RB2B** | ✅ 200/mo | Paid tiers | ⭐⭐⭐ Good | Visitor tracking |
| **People Data Labs** | ❌ None | $99/mo (1k calls) | ⭐⭐⭐⭐ Great | Data enrichment |
| **OpenRouter** | ✅ Pay-as-go | $0.001/enrich | ⭐⭐⭐⭐ Great | AI enrichment |

---

## 🚀 Recommended Setup (100% FREE for 1,000 enrichments/month)

### Step 1: Sign up for FREE APIs

1. **Hunter.io**: https://hunter.io/users/sign_up
   - Get API key: Dashboard → API → Get Key
   - Add to Railway: `HUNTER_API_KEY=your_key`

2. **Apollo.io**: https://app.apollo.io/sign-up
   - Get API key: Settings → API → Generate Key
   - Add to Railway: `APOLLO_API_KEY=your_key`

3. **Google Places**: https://console.cloud.google.com/
   - Enable Places API
   - Get API key: APIs & Services → Credentials → Create API Key
   - **FREE**: 10,000 calls/month (worth $200)
   - Add to Railway: `GOOGLE_PLACES_API_KEY=your_key`

4. **OpenRouter**: You already have this! ✅
   - Already configured: `OPENROUTER_API_KEY`
   - Can call Perplexity without separate API key

### Step 2: Update Environment Variables in Railway

**REMOVE** (not needed):
```bash
PERPLEXITY_API_KEY  # Already using OpenRouter ✅
CLEARBIT_API_KEY    # Replacing with free alternatives
PROXYCURL_API_KEY   # Optional, expensive
```

**ADD** (free alternatives):
```bash
HUNTER_API_KEY=your_hunter_key
APOLLO_API_KEY=your_apollo_key
GOOGLE_PLACES_API_KEY=your_google_key  # Keep this - it's FREE!

# Already have (keep):
OPENROUTER_API_KEY=sk-or-v1-...
```

### Step 3: Code Changes (Minimal)

**Current code** already has graceful degradation:
- If Clearbit API key missing → Skip Clearbit
- If Google Places missing → Skip Google
- Uses OpenRouter for AI enrichment ✅
- Uses Perplexity via OpenRouter ✅ (no separate key needed)

**Just add**:
- Hunter.io integration (replace Clearbit)
- Apollo.io integration (backup source)

---

## 💰 Cost Breakdown (1,000 enrichments/month)

### Scenario 1: Current Stack (Paid)
```
Clearbit:        $99/month (base)
Google Places:   $0 (within free tier)
OpenRouter:      $1/month (AI enrichment)
-------------------------------------------
TOTAL:           $100/month
Cost/enrichment: $0.10
```

### Scenario 2: All FREE (Recommended)
```
Hunter.io:       $0 (25 free/month) + manual fallback
Apollo.io:       $0 (free tier)
Google Places:   $0 (10,000 free/month)
OpenRouter:      $1/month (AI enrichment)
-------------------------------------------
TOTAL:           $1/month
Cost/enrichment: $0.001
SAVINGS:         $99/month (99% reduction)
```

### Scenario 3: Hybrid (Scalable)
```
Hunter.io:       $49/month (500 searches)
Apollo.io:       $0 (free tier backup)
Google Places:   $0 (10,000 free/month)
OpenRouter:      $1/month (AI enrichment)
-------------------------------------------
TOTAL:           $50/month
Cost/enrichment: $0.05
SAVINGS:         $50/month (50% reduction)
```

---

## ✅ Action Items

### Immediate (Today):
1. ✅ **Fix httpx dependency** (0.28.1 → 0.27.2) - Done!
2. ✅ **Remove PERPLEXITY_API_KEY requirement** - Already using OpenRouter
3. ⏳ **Sign up for Hunter.io** (FREE tier)
4. ⏳ **Sign up for Google Places API** (FREE tier)
5. ⏳ **Optional: Sign up for Apollo.io** (FREE tier backup)

### This Week:
1. Add Hunter.io integration to enrichment orchestrator
2. Add Apollo.io as fallback source
3. Test 100% FREE enrichment flow
4. Monitor free tier usage limits

### Next Week:
1. Decide: Stay 100% free OR upgrade to paid tiers
2. If upgrading: Hunter.io $49/month (best ROI)
3. Track cost savings vs previous Clearbit setup

---

## 🎯 Summary

**You asked**: *"how to get clearbit and google places api keys? free? if not free accessible? better options?"*

**Answer**:
- ❌ **Clearbit**: NOT free, $99/month minimum → **Use Hunter.io FREE instead**
- ✅ **Google Places**: YES FREE, 10,000 calls/month ($200 credit) → **Keep this!**
- ✅ **Better options**: Hunter.io + Apollo.io + Google Places = **100% FREE** for 1,000 enrichments/month
- ✅ **Perplexity**: Already using OpenRouter, no separate key needed

**Cost comparison**:
- Current (Clearbit): **$100/month**
- Recommended (Free): **$1/month** (99% savings)
- If you scale (Hunter paid): **$50/month** (50% savings)

**Next step**: Sign up for free APIs and add keys to Railway! 🚀
