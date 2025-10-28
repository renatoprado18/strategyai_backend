# LinkedIn & Website Scraping - Future Implementation Plan

**Status:** Disabled (2025-10-28)
**Reason:** Apify taking 2-4 minutes blocking pipeline, Perplexity covers 90% of use cases
**Re-enable when:** We have parallel execution OR faster scraping solution

---

## Current State (Disabled)

### What We Lost by Disabling Apify

1. **Direct Website Scraping** (30-60 seconds)
   - Company description from website
   - Product/service listings
   - Content summary from homepage
   - **Impact:** Minor - Perplexity can research company websites

2. **LinkedIn Profile Search** (30-60 seconds)
   - Google search results for LinkedIn company pages
   - Google search results for founder profiles
   - Basic LinkedIn snippets from search results
   - **Impact:** Low - Perplexity finds similar intel, user can provide LinkedIn URLs

3. **Competitor Research** (45-90 seconds)
   - Google search for competitors
   - Basic competitor listings
   - **Impact:** Minimal - Perplexity provides better competitive analysis

4. **Industry Trends** (45-90 seconds)
   - Google searches for industry trends
   - News article snippets
   - **Impact:** None - Perplexity is superior for trend analysis

5. **News & Social Media** (30-60 seconds each)
   - Google searches for recent news
   - Google searches for social profiles
   - **Impact:** Minimal - Perplexity covers news, social not critical

**Total time saved:** 2-4 minutes per analysis
**Quality loss:** ~5-10% (mostly missing direct website content)

---

## Future Implementation Options

### Option 1: Parallel Execution (RECOMMENDED)

**Concept:** Run Apify in background while AI analysis proceeds with Perplexity data

**Implementation:**
```python
# Start Apify as background task (non-blocking)
apify_task = asyncio.create_task(gather_all_apify_data(...))

# Immediately start Perplexity research
perplexity_data = await comprehensive_market_research(...)

# Generate initial analysis with Perplexity only
analysis = await generate_multistage_analysis(
    apify_data=None,  # Start without Apify
    perplexity_data=perplexity_data
)

# Check if Apify finished, enrich if available
if apify_task.done():
    apify_data = await apify_task
    # Optionally: Re-run Stage 1 extraction to incorporate Apify data
    # Or: Append Apify insights as supplementary section
```

**Pros:**
- Best of both worlds - speed + comprehensive data
- User gets initial results in 2-3 minutes
- Apify enriches report if it finishes in time
- No perceived blocking

**Cons:**
- More complex implementation
- Need to handle partial data states
- Potential race conditions

**Estimated effort:** 2-3 hours

---

### Option 2: Faster Scraping with Alternative Tools

Replace slow Apify actors with faster alternatives:

#### 2A: Use Apify Playwright Actor (Faster)
```python
# Current: "apify/website-content-crawler" (slow, Cheerio-based)
WEBSITE_SCRAPER_ACTOR = "apify/web-scraper"  # Faster but less reliable

# Or use Playwright for speed
WEBSITE_SCRAPER_ACTOR = "apify/playwright-scraper"
```

**Pros:** 2-3x faster, still uses Apify infrastructure
**Cons:** Less reliable, may break on dynamic sites
**Estimated speedup:** 2-4 min → 60-90 seconds

#### 2B: Direct HTTP Requests (Fastest)
```python
import httpx
from bs4 import BeautifulSoup

async def fast_website_scrape(url: str) -> Dict[str, Any]:
    """Ultra-fast website scraping with direct HTTP"""
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        return {
            "title": soup.find('title').text if soup.find('title') else "",
            "description": soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else "",
            "content": ' '.join([p.text for p in soup.find_all('p')[:10]])
        }
```

**Pros:** 5-10 seconds total, no API costs
**Cons:** Fails on JavaScript-heavy sites, requires maintenance
**Estimated speedup:** 2-4 min → 10-20 seconds

#### 2C: Firecrawl API (Balanced)
```python
# Modern web scraping API - fast + reliable
# https://firecrawl.dev/

import requests

FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")

async def scrape_with_firecrawl(url: str) -> Dict[str, Any]:
    response = requests.post(
        "https://api.firecrawl.dev/v0/scrape",
        headers={"Authorization": f"Bearer {FIRECRAWL_API_KEY}"},
        json={"url": url, "formats": ["markdown", "html"]}
    )
    return response.json()
```

**Pros:** 10-15 seconds, reliable, handles JS
**Cons:** Additional API cost (~$0.01-0.02 per scrape)
**Estimated speedup:** 2-4 min → 30-45 seconds

---

### Option 3: LinkedIn Official API (Premium)

**Best solution for LinkedIn data** - requires LinkedIn partnership or Rapid API

#### 3A: RapidAPI LinkedIn Scraper
```python
# https://rapidapi.com/linkedin-scraper-api/api/linkedin-data-scraper

import requests

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

async def get_linkedin_profile(profile_url: str) -> Dict[str, Any]:
    url = "https://linkedin-data-scraper.p.rapidapi.com/person"

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "linkedin-data-scraper.p.rapidapi.com"
    }

    response = requests.get(url, headers=headers, params={"url": profile_url})
    return response.json()
```

**Cost:** $0.01-0.05 per profile lookup
**Speed:** 5-10 seconds
**Reliability:** High (maintained API)

#### 3B: ProxyCurl API (Professional)
```python
# https://nubela.co/proxycurl/

import requests

PROXYCURL_API_KEY = os.getenv("PROXYCURL_API_KEY")

async def get_linkedin_profile_proxycurl(linkedin_url: str) -> Dict[str, Any]:
    api_endpoint = 'https://nubela.co/proxycurl/api/v2/linkedin'

    response = requests.get(
        api_endpoint,
        params={'url': linkedin_url},
        headers={'Authorization': f'Bearer {PROXYCURL_API_KEY}'}
    )
    return response.json()
```

**Cost:** $0.01-0.10 per lookup (tiered pricing)
**Speed:** 3-5 seconds
**Reliability:** Excellent (enterprise-grade)
**Features:** Company + person data, historical data

---

### Option 4: User-Provided Data

**Simplest solution** - ask user for LinkedIn URLs and key website content

**Implementation:**
```python
# In submission form, add fields:
{
    "linkedin_company_url": "https://linkedin.com/company/...",
    "linkedin_founder_url": "https://linkedin.com/in/...",
    "company_description": "Optional: paste company description",
    "key_products": "Optional: list key products/services"
}
```

**Pros:**
- Zero cost, zero latency
- Most accurate data (from source)
- No scraping/API issues

**Cons:**
- Requires user effort
- May reduce conversion

**Best for:** Premium tier or detailed analyses

---

## Recommended Implementation Roadmap

### Phase 1: Immediate (Current)
- ✅ Disable Apify completely
- ✅ Rely on Perplexity for all research
- ✅ Dashboard loads in 2-3 minutes

### Phase 2: Quick Win (1-2 hours)
- Add optional user-provided fields for LinkedIn URLs
- Add optional company description textarea
- Use user data when available, Perplexity when not

### Phase 3: Parallel Execution (2-3 hours)
- Implement background Apify task
- Generate initial analysis without waiting
- Enrich report if Apify finishes
- Best of both worlds

### Phase 4: Premium Upgrade (4-6 hours)
- Add Firecrawl for fast website scraping (10-15s)
- Add ProxyCurl for LinkedIn data (3-5s per profile)
- Total overhead: 20-30 seconds for premium data
- Only for paid plans to justify API costs

---

## Cost Analysis

### Current (Disabled Apify)
- **Perplexity:** 5 queries × $0.005 = $0.025 per analysis
- **AI Analysis:** $0.30-0.40 per analysis
- **Total:** ~$0.33-0.43 per analysis

### Option 2B: Direct HTTP Scraping
- **Perplexity:** $0.025
- **Scraping:** $0.00 (free)
- **AI Analysis:** $0.30-0.40
- **Total:** ~$0.33-0.43 per analysis (no change)

### Option 2C: Firecrawl
- **Perplexity:** $0.025
- **Firecrawl:** 1 scrape × $0.015 = $0.015
- **AI Analysis:** $0.30-0.40
- **Total:** ~$0.37-0.46 per analysis (+$0.02)

### Option 3B: ProxyCurl Premium
- **Perplexity:** $0.025
- **Firecrawl:** $0.015
- **ProxyCurl:** 2 lookups × $0.05 = $0.10
- **AI Analysis:** $0.30-0.40
- **Total:** ~$0.54-0.64 per analysis (+$0.23)

**Recommendation:** Offer as premium tier at 2-3x price ($2-3 per analysis) for comprehensive data

---

## Technical Notes

### Caching Strategy (Institutional Memory)

All external data should be cached to avoid redundant API calls:

```python
# Already implemented in app/services/intelligence/memory.py
async def _cached_scraping_call(
    cache_entity_type: str,  # "website", "linkedin_company", "linkedin_person"
    cache_entity_id: str,    # URL or unique identifier
    scraping_func,           # Function to call on cache miss
    *args,
    **kwargs
) -> Dict[str, Any]:
    """Check cache, call scraper on miss, store result"""

    # Check institutional_memory table
    cached_data = await retrieve_memory(
        entity_type=cache_entity_type,
        entity_id=cache_entity_id,
        max_age_hours=168  # 7 days cache
    )

    if cached_data:
        return cached_data

    # Cache miss - call scraper
    result = await scraping_func(*args, **kwargs)

    # Store in institutional_memory
    await store_memory(
        entity_type=cache_entity_type,
        entity_id=cache_entity_id,
        data=result,
        source="scraping",
        confidence=0.9
    )

    return result
```

**Benefits:**
- 7-day cache = most companies only scraped once
- Drastically reduces API costs
- Faster analysis for repeat customers

---

## Decision Matrix

| Option | Speed | Cost | Reliability | Effort | Recommended For |
|--------|-------|------|-------------|--------|----------------|
| **Current (Perplexity only)** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Done | All users (current) |
| **User-provided data** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐ | Premium users |
| **Parallel Apify** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ | Power users |
| **Direct HTTP scraping** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐ | Budget option |
| **Firecrawl API** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | **BEST BALANCE** |
| **ProxyCurl Premium** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | Enterprise tier |

---

## Implementation Priority

**Short-term (Next sprint):**
1. ✅ Keep Apify disabled
2. ⚡ Add optional user fields for LinkedIn URLs + description (1-2 hours)
3. ⚡ Test Firecrawl API for website scraping (1 hour)

**Medium-term (1-2 weeks):**
1. Implement parallel execution for Apify (2-3 hours)
2. Add Firecrawl as premium feature (2 hours)
3. A/B test: Perplexity-only vs Perplexity + Firecrawl

**Long-term (1-2 months):**
1. Launch premium tier with ProxyCurl LinkedIn data
2. Optimize caching strategy
3. Build admin dashboard to monitor scraping costs/quality

---

## Success Metrics

Track these to decide if/when to re-enable:

- **Analysis completion time:** Target < 3 minutes (current: 2-3 min ✅)
- **User satisfaction:** Survey feedback on report quality
- **Data quality tier distribution:** % legendary vs full vs good
- **Conversion rate:** Do users value comprehensive data enough to wait longer?
- **Cost per analysis:** Keep under $0.50 for standard tier

**Current status:** ✅ Fast, ✅ Cheap, ⚠️ Slightly less comprehensive (but still high quality)

---

## Conclusion

**Current approach (Perplexity-only) is optimal for:**
- Speed-conscious users (95% of users)
- Cost-effective scaling
- Avoiding API rate limits

**Re-enable scraping when:**
- User feedback requests more website/LinkedIn detail
- We implement parallel execution (no perceived delay)
- Premium tier launches (can justify API costs)

**Next step:** Add user-provided LinkedIn fields (1-2 hour task, zero cost, immediate value)
