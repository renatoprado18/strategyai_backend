# Advanced Features Deployment Guide

## 🚀 NEW: Institutional Memory & Adaptive Model Routing

Two powerful features to make analyses **cheaper** and **smarter** over time.

---

## ✅ DEPLOYED FIXES (2025-10-26)

### 1. Stage 3 JSON Parsing Fix
- **Problem:** `Stage 3 failed to parse JSON: Expecting value: line 1 column 1`
- **Solution:** Enhanced JSON extraction from LLM responses + automatic retry
- **Status:** ✅ Deployed to Railway

### 2. Dashboard Intelligence Token Fix
- **Problem:** `Invalid or expired token` error on admin dashboard
- **Solution:** Fixed token key mismatch, added `getDashboardIntelligence()` to API client
- **Status:** ✅ Deployed to Vercel

### 3. Dashboard Intelligence Datetime Fix
- **Problem:** `can't compare offset-naive and offset-aware datetimes`
- **Solution:** Use timezone-aware datetimes consistently
- **Status:** ✅ Deployed to Railway

---

## 🎯 Feature 1: Institutional Memory

### What It Does
Stores and reuses findings across analyses:
- **Company profiles** → Cached for 30 days
- **Competitor data** → Cached for 7 days
- **Industry insights** → Cached for 3 days

### Benefits
- **Cost Savings:** Repeat analyses 30-50% cheaper
- **Quality Improvement:** Builds knowledge over time
- **Faster Processing:** Reuses expensive research

### How It Works
```python
# When processing a new analysis:
1. Check cache for existing company profile
2. If found (and fresh), reuse it
3. If not found, generate new analysis
4. Store results for future reuse
```

### Database Setup Required

**Run this in Supabase SQL Editor:**

```sql
-- Copy entire contents of migrations/005_institutional_memory.sql
-- This creates the institutional_memory table with indexes
```

**Migration file:** `migrations/005_institutional_memory.sql`

### Usage Example

```python
from institutional_memory import (
    cache_company_profile,
    get_cached_company_profile,
    cache_competitor_data,
    get_cache_stats
)

# Store company profile
await cache_company_profile(
    company="Nubank",
    industry="Tecnologia",
    extracted_data={...},
    source="multistage_analysis"
)

# Retrieve cached profile
profile = await get_cached_company_profile("Nubank")
if profile:
    print(f"Using cached data from {profile['cached_at']}")
```

### Cache Statistics

```python
stats = await get_cache_stats()
print(f"Total cached records: {stats['total_records']}")
print(f"By type: {stats['by_type']}")
print(f"Most accessed: {stats['most_accessed']}")
```

---

## 🧠 Feature 2: Adaptive Model Routing

### What It Does
Automatically selects the best AI model based on task complexity:
- **Simple tasks** → Gemini Flash ($0.30/M tokens)
- **Mid complexity** → Gemini Pro ($7.50/M tokens)
- **Complex strategy** → GPT-4o ($10/M tokens)
- **Deep reasoning** → Claude 3.5 Sonnet ($15/M tokens)

### Benefits
- **Cost Optimization:** Use cheap models when possible
- **Quality Preservation:** Use premium models when needed
- **Automatic:** No manual configuration required

### How It Works

```python
from adaptive_routing import (
    score_complexity,
    select_model_for_task,
    get_routing_recommendation
)

# Score task complexity
complexity = score_complexity(
    task_type="strategic_planning",
    data_available=50,
    requires_reasoning=True,
    requires_creativity=True
)
# Returns: 0.95 (very complex)

# Select model
model_config = select_model_for_task(
    task_type="strategic_planning",
    complexity_score=complexity
)
print(model_config)
# {
#   "model": "openai/gpt-4o",
#   "tier": "premium",
#   "cost_per_1m_tokens": 10.00,
#   "best_for": ["strategic frameworks", "creative thinking"]
# }
```

### Model Tiers

| Tier | Model | Cost/M Tokens | Best For |
|------|-------|---------------|----------|
| **ultra_cheap** | Gemini Flash | $0.30 | Extraction, formatting |
| **cheap** | Claude Haiku | $1.25 | Polish, basic analysis |
| **mid** | Gemini Pro | $7.50 | Structured data, tables |
| **premium** | GPT-4o | $10.00 | Strategy, creativity |
| **reasoning** | Claude 3.5 Sonnet | $15.00 | Risk assessment, deep reasoning |

### Stage-Specific Routing

```python
# Get recommendations for all stages
routing = get_routing_recommendation(extracted_data)
print(routing)
# {
#   "stage1": "google/gemini-2.5-flash-preview-09-2025",
#   "stage3": "openai/gpt-4o",
#   "stage4": "google/gemini-2.5-pro-preview",
#   "stage5": "anthropic/claude-3.5-sonnet",
#   "stage6": "anthropic/claude-haiku-4.5"
# }
```

---

## 📊 Integration (Optional - Not Yet Activated)

To activate these features in the analysis pipeline, you would:

### Option 1: Full Integration

```python
# In analysis_multistage.py
from institutional_memory import (
    get_cached_company_profile,
    cache_company_profile,
    cache_competitor_data,
    cache_industry_insights
)
from adaptive_routing import get_routing_recommendation, select_model_for_task

async def generate_multistage_analysis(...):
    # 1. Check cache first
    cached_profile = await get_cached_company_profile(company)
    if cached_profile:
        logger.info(f"[CACHE] Using cached profile (saved ~$0.15)")
        # Use cached data to skip Stage 1

    # 2. Get routing recommendations
    routing = get_routing_recommendation(extracted_data)

    # 3. Use recommended models for each stage
    MODEL_EXTRACTION = routing["stage1"]
    MODEL_STRATEGY = routing["stage3"]
    # etc...

    # 4. Cache results for future use
    await cache_company_profile(company, industry, extracted_data)
    await cache_competitor_data(company, competitors)
```

### Option 2: Gradual Rollout

Currently **NOT integrated** into main pipeline. Deployed as standalone modules for:
- Testing
- Manual usage
- Future activation

---

## 🔍 Testing

### Test Institutional Memory

```python
# Run this in Python console connected to Railway
import asyncio
from institutional_memory import store_memory, retrieve_memory, get_cache_stats

async def test():
    # Store test data
    await store_memory(
        entity_type="company",
        entity_id="Test Company",
        data={"test": "data"},
        source="manual_test"
    )

    # Retrieve it
    result = await retrieve_memory("company", "Test Company")
    print(f"Retrieved: {result}")

    # Get stats
    stats = await get_cache_stats()
    print(f"Stats: {stats}")

asyncio.run(test())
```

### Test Adaptive Routing

```python
from adaptive_routing import score_complexity, select_model_for_task

# Test complexity scoring
complexity = score_complexity(
    task_type="strategic_planning",
    data_available=100,
    requires_reasoning=True
)
print(f"Complexity: {complexity}")

# Test model selection
model = select_model_for_task("strategic_planning", complexity)
print(f"Selected: {model}")
```

---

## 📈 Expected Impact

### Cost Savings
- **First analysis:** $0.85 (LEGENDARY tier with all stages)
- **Repeat analysis (with cache):** $0.40-0.60 (50-70% cheaper)
- **Simple analysis (adaptive routing):** $0.15-0.30 (cheaper model selection)

### Quality Improvements
- **Knowledge accumulation:** Better insights over time
- **Consistency:** Reused data ensures consistent facts
- **Speed:** Cached data = faster processing

---

## ⚠️ Important Notes

1. **Database Migration Required:**
   - Must run `migrations/005_institutional_memory.sql` in Supabase
   - Creates `institutional_memory` table

2. **Optional Activation:**
   - Features are deployed but NOT yet integrated into main pipeline
   - Can be activated later with minimal code changes
   - Currently available for testing and manual usage

3. **Cache Cleanup:**
   - Automatic: Entries older than TTL are ignored
   - Manual: Run cleanup query in migration file (commented)

4. **No Breaking Changes:**
   - Fully backward compatible
   - Existing analyses work exactly as before
   - New features are additive

---

## 🎉 Summary

**What's Live:**
✅ All critical bug fixes deployed
✅ Institutional memory module ready
✅ Adaptive routing module ready
✅ Database migration available
⏳ Integration pending (optional activation)

**Next Steps:**
1. Run database migration (5 minutes)
2. Test features manually (optional)
3. Activate in main pipeline when ready (optional)
4. Monitor cache hit rates and cost savings

**Impact:**
- 🐛 Fixes 3 critical bugs immediately
- 💰 Enables 30-70% cost reduction potential
- 🧠 Builds institutional knowledge over time
- 🚀 Zero breaking changes, full backward compatibility
