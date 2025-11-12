# Optimization Roadmap - IMENSIAH System

**Date:** 2025-01-11
**Status:** Actionable Implementation Plan
**Focus:** Priority matrix with cost savings projections

---

## Executive Summary

**Current State:**
- Cost: $0.03-0.15 per enrichment
- Speed: 6-10 seconds
- Reliability: 95% uptime
- Maintainability: 657-line god class
- Cache disabled in production (💰 burning money)

**Target State (After All Optimizations):**
- Cost: $0.001-0.03 per enrichment (80-95% reduction)
- Speed: 4-6 seconds (40% faster)
- Reliability: 99.5% uptime
- Maintainability: 5 focused classes <150 lines each
- Smart caching enabled (80-90% cache hit rate)

**ROI at Scale:**
- 10,000 enrichments/month: Save $200-1,200/month
- 100,000 enrichments/month: Save $1,500-13,500/month

---

## Priority Matrix

### Impact vs Effort Quadrants

```
        High Impact
            │
    P0      │      P1
  ──────────┼──────────
    P2      │      P3
            │
        Low Impact
```

**P0 (Do Today):** High impact, low effort
**P1 (This Week):** High impact, medium effort
**P2 (Next Week):** Medium impact, medium effort
**P3 (Future):** High impact, high effort OR low impact

---

## Phase 1: Quick Wins (1 Day) - Save 40-60%

### P0-1: Re-Enable Caching with Smart TTL
**Effort:** 2 hours
**Impact:** 💰💰💰💰💰 (80-90% cost reduction on cache hits)
**Savings:** $0.03-0.12 per cached enrichment

**Implementation:**
```python
# File: app/services/enrichment/progressive_orchestrator.py
# Line 186-189 (currently disabled)

async def enrich_progressive(self, website_url: str, ...):
    # STEP 1: Check cache (re-enable)
    cache_key = f"progressive:{domain}:v1"
    cached = await self.cache.get_progressive(cache_key)

    if cached and self._is_cache_fresh(cached):
        logger.info(f"Cache HIT for {domain} - returning cached data")
        return self._hydrate_session_from_cache(cached)

    # STEP 2: Run enrichment (cache miss)
    session = await self._do_enrichment(website_url, ...)

    # STEP 3: Cache with smart TTL
    await self.cache.set_progressive(
        cache_key,
        session,
        ttl_strategy={
            "layer1": 90,   # Layer 1: Cache 90 days
            "layer2": 30,   # Layer 2: Cache 30 days
            "layer3": 7     # Layer 3: Cache 7 days (AI can vary)
        }
    )

    return session
```

**Testing:**
```bash
# Test 1: Cold start (cache miss)
curl -X POST https://api.imensiah.com/enrichment/progressive -d '{"url":"techstart.com"}'
# Should cost $0.15

# Test 2: Warm start (cache hit)
curl -X POST https://api.imensiah.com/enrichment/progressive -d '{"url":"techstart.com"}'
# Should cost $0.00 (cached)
```

**Success Criteria:**
- Cache hit rate > 70% after 1 week
- Average cost drops from $0.15 to $0.03-0.05

---

### P0-2: Smart Source Skipping
**Effort:** 3 hours
**Impact:** 💰💰💰💰 (30-50% Layer 2 cost reduction)
**Savings:** $0.01-0.05 per enrichment

**Implementation:**
```python
# File: app/services/enrichment/progressive_orchestrator.py
# Add to Layer 2 orchestration (line ~260)

async def _run_layer2(self, domain: str, layer1_data: dict):
    layer2_sources = []

    # Smart skip: If we have high-confidence address from Layer 1, skip Google Places
    if layer1_data.get("address") and layer1_data.get("address_confidence", 0) > 80:
        logger.info(f"Skipping Google Places - already have address with {layer1_data['address_confidence']}% confidence")
    else:
        layer2_sources.append(self.google_places_source)

    # Smart skip: If ReceitaWS returned CNPJ data (Brazil), skip Clearbit
    if layer1_data.get("cnpj") and layer1_data.get("country") == "BR":
        logger.info("Skipping Clearbit - ReceitaWS already returned government data")
    else:
        layer2_sources.append(self.clearbit_source)

    # Always call ReceitaWS (free)
    layer2_sources.append(self.receita_ws_source)

    # Execute remaining sources
    results = await asyncio.gather(*[
        source.enrich(domain, **context) for source in layer2_sources
    ], return_exceptions=True)

    return self._aggregate_results(results)
```

**Testing:**
```bash
# Test with Brazilian company (should skip Clearbit)
curl -X POST /enrichment/progressive -d '{"url":"nubank.com.br"}'
# Check logs for "Skipping Clearbit"

# Test with US company (should call Clearbit)
curl -X POST /enrichment/progressive -d '{"url":"stripe.com"}'
# Check logs for Clearbit API call
```

**Success Criteria:**
- 30-50% reduction in Clearbit API calls
- No quality degradation (confidence scores unchanged)

---

### P0-3: Replace GPT-4o-mini with Groq
**Effort:** 3 hours
**Impact:** 💰💰💰 (100% AI cost reduction)
**Savings:** $0.005 per enrichment

**Implementation:**
```python
# File: app/services/enrichment/sources/ai_inference_enhanced.py

class EnhancedAIInferenceSource(EnrichmentSource):
    def __init__(self):
        super().__init__(name="ai_inference_enhanced", cost_per_call=0.00)  # Free
        self.groq_client = GroqClient(api_key=settings.groq_api_key)
        self.claude_client = ClaudeClient(api_key=settings.anthropic_api_key)  # Fallback

    async def enrich(self, domain: str, **kwargs) -> SourceResult:
        # Try Groq first (free, fast)
        try:
            result = await self.groq_client.infer(
                model="llama-3.1-8b-instant",
                messages=self._build_messages(domain, kwargs),
                max_tokens=800,
                temperature=0.3
            )
            return self._parse_structured_output(result, cost_usd=0.00)

        except RateLimitError as e:
            logger.warning(f"Groq rate limited - falling back to Claude Haiku")

            # Fallback to Claude Haiku ($0.00025 vs GPT $0.005)
            result = await self.claude_client.infer(
                model="claude-3-haiku-20240307",
                messages=self._build_messages(domain, kwargs),
                max_tokens=800
            )
            return self._parse_structured_output(result, cost_usd=0.00025)

        except Exception as e:
            logger.error(f"AI inference failed: {e}")
            # Return empty result (don't fail entire enrichment)
            return SourceResult(
                source_name=self.name,
                success=False,
                data={},
                cost_usd=0.00,
                error_message=str(e)
            )
```

**Setup:**
```bash
# Add Groq API key to .env
echo "GROQ_API_KEY=gsk_..." >> .env

# Install Groq SDK
pip install groq
```

**Testing:**
```python
# Test Groq inference
response = await groq_client.infer(
    model="llama-3.1-8b-instant",
    messages=[
        {"role": "system", "content": "You are a business analyst."},
        {"role": "user", "content": "Classify this company: techstart.com"}
    ]
)
print(response)  # Should return structured JSON
```

**Success Criteria:**
- AI inference cost drops to $0.00
- Quality comparable (85% vs 90% for classification)
- Speed improves (0.5s vs 2s)

---

### P0-4: Add Circuit Breakers
**Effort:** 4 hours
**Impact:** 💪💪💪💪 (Prevent cascading failures)
**Savings:** Prevent $100-1000 wasted on failing APIs

**Implementation:**
```python
# File: app/core/circuit_breaker.py

from enum import Enum
from datetime import datetime, timedelta

class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"      # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered

class CircuitBreaker:
    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time = None

    def record_success(self):
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.success_threshold:
                self._close()

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = datetime.now()

        if self.failures >= self.failure_threshold:
            self._open()

    def _open(self):
        self.state = CircuitState.OPEN
        logger.warning(f"Circuit breaker OPEN for {self.name}")

    def _close(self):
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        logger.info(f"Circuit breaker CLOSED for {self.name}")

    def can_execute(self) -> bool:
        if self.state == CircuitState.CLOSED:
            return True

        if self.state == CircuitState.OPEN:
            # Check if timeout expired
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = CircuitState.HALF_OPEN
                self.successes = 0
                return True
            return False

        return True  # HALF_OPEN: allow requests

# Usage in sources
clearbit_breaker = CircuitBreaker(name="clearbit", failure_threshold=5, timeout=60)

async def enrich(self, domain: str):
    if not clearbit_breaker.can_execute():
        logger.warning("Circuit breaker OPEN - skipping Clearbit")
        return self._get_empty_result()

    try:
        result = await self._call_clearbit_api(domain)
        clearbit_breaker.record_success()
        return result
    except Exception as e:
        clearbit_breaker.record_failure()
        raise
```

**Testing:**
```python
# Simulate API failures
for i in range(10):
    try:
        await clearbit_source.enrich("test.com")
    except Exception:
        pass

# Circuit should be OPEN
assert clearbit_breaker.state == CircuitState.OPEN

# Wait for timeout
await asyncio.sleep(61)

# Circuit should be HALF_OPEN (testing)
assert clearbit_breaker.state == CircuitState.HALF_OPEN
```

**Success Criteria:**
- No cascading failures when Clearbit goes down
- API errors contained (don't affect entire enrichment)
- Automatic recovery after timeout

---

### P0-5: Add Rate Limiting
**Effort:** 3 hours
**Impact:** 💪💪💪 (Prevent API bans)
**Savings:** Avoid $1000+ account bans

**Implementation:**
```python
# File: app/services/enrichment/sources/base.py

from asyncio import Semaphore
import time

class RateLimitedSource(EnrichmentSource):
    def __init__(
        self,
        name: str,
        cost_per_call: float,
        max_concurrent: int = 5,
        min_delay_ms: int = 200
    ):
        super().__init__(name, cost_per_call)
        self.semaphore = Semaphore(max_concurrent)
        self.min_delay = min_delay_ms / 1000
        self.last_call_time = 0

    async def enrich(self, *args, **kwargs):
        # Limit concurrent requests
        async with self.semaphore:
            # Enforce minimum delay between requests
            time_since_last = time.time() - self.last_call_time
            if time_since_last < self.min_delay:
                await asyncio.sleep(self.min_delay - time_since_last)

            self.last_call_time = time.time()

            # Call actual enrichment
            return await self._do_enrich(*args, **kwargs)

    async def _do_enrich(self, *args, **kwargs):
        raise NotImplementedError

# Apply to expensive sources
class ClearbitSource(RateLimitedSource):
    def __init__(self):
        super().__init__(
            name="clearbit",
            cost_per_call=0.05,
            max_concurrent=10,  # Max 10 concurrent requests
            min_delay_ms=100    # Min 100ms between requests
        )
```

**Testing:**
```python
# Test concurrent limiting
import time
start = time.time()

# Launch 20 concurrent requests
tasks = [clearbit_source.enrich(f"company{i}.com") for i in range(20)]
results = await asyncio.gather(*tasks)

elapsed = time.time() - start

# Should take ~2 seconds (20 requests / 10 concurrent * 100ms delay)
assert elapsed >= 2.0
```

**Success Criteria:**
- No API rate limit errors (429)
- Smooth request distribution (no bursts)
- Max 10 concurrent requests per source

---

## Phase 2: API Replacements (3 Days) - Save 60-80%

### P1-1: Replace Clearbit with OpenCorporates
**Effort:** 1 day
**Impact:** 💰💰💰💰💰 (94% cost reduction)
**Savings:** $0.047 per enrichment

**Implementation:**
```python
# File: app/services/enrichment/sources/opencorporates.py

class OpenCorporatesSource(EnrichmentSource):
    API_URL = "https://api.opencorporates.com/v0.4"

    def __init__(self):
        super().__init__(name="opencorporates", cost_per_call=0.003)
        self.api_key = settings.opencorporates_api_key

    async def enrich(self, domain: str, company_name: Optional[str] = None):
        # Search by company name
        search_url = f"{self.API_URL}/companies/search"
        params = {
            "q": company_name or domain,
            "api_token": self.api_key
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(search_url, params=params)
            data = response.json()

        if not data.get("results", {}).get("companies"):
            return self._empty_result()

        # Get first result
        company = data["results"]["companies"][0]["company"]

        return SourceResult(
            source_name=self.name,
            success=True,
            data={
                "legal_name": company.get("name"),
                "founded_year": company.get("incorporation_date")[:4] if company.get("incorporation_date") else None,
                "company_status": company.get("current_status"),
                "jurisdiction": company.get("jurisdiction_code"),
                "company_number": company.get("company_number")
            },
            cost_usd=self.cost_per_call,
            duration_ms=int(response.elapsed.total_seconds() * 1000)
        )

# Update progressive orchestrator
class ProgressiveEnrichmentOrchestrator:
    def __init__(self):
        self.opencorporates_source = OpenCorporatesSource()
        self.clearbit_source = ClearbitSource()  # Keep as fallback

    async def _run_layer2(self, domain: str, context: dict):
        # Try OpenCorporates first (cheap)
        opencorporates_result = await self.opencorporates_source.enrich(domain, **context)

        if opencorporates_result.success and len(opencorporates_result.data) > 3:
            # OpenCorporates returned good data, skip Clearbit
            logger.info(f"Using OpenCorporates data - skipping Clearbit (saved $0.047)")
            return [opencorporates_result]

        # Fallback to Clearbit if OpenCorporates failed
        logger.warning("OpenCorporates failed - falling back to Clearbit")
        clearbit_result = await self.clearbit_source.enrich(domain)
        return [opencorporates_result, clearbit_result]
```

**Setup:**
```bash
# Get API key: https://opencorporates.com/api_accounts/new
echo "OPENCORPORATES_API_KEY=..." >> .env
```

**Testing:**
```bash
# Test with known company
curl "https://api.opencorporates.com/v0.4/companies/search?q=Apple Inc"

# Should return legal name, status, jurisdiction
```

**Success Criteria:**
- 70-80% of enrichments use OpenCorporates (not Clearbit)
- Cost per enrichment drops from $0.15 to $0.05-0.08
- Data quality maintained (confidence scores similar)

---

### P1-2: Replace Google Places with Mapbox
**Effort:** 4 hours
**Impact:** 💰💰💰 (100% cost reduction within free tier)
**Savings:** $0.017 per enrichment

**Implementation:**
```python
# File: app/services/enrichment/sources/mapbox.py

class MapboxSource(EnrichmentSource):
    API_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places"

    def __init__(self):
        super().__init__(name="mapbox", cost_per_call=0.00)  # Free tier
        self.api_key = settings.mapbox_api_key

    async def enrich(self, company_name: str, city: Optional[str] = None):
        # Build search query
        query = company_name
        if city:
            query += f", {city}"

        url = f"{self.API_URL}/{query}.json"
        params = {"access_token": self.api_key}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()

        if not data.get("features"):
            return self._empty_result()

        # Get first result
        feature = data["features"][0]

        return SourceResult(
            source_name=self.name,
            success=True,
            data={
                "address": feature.get("place_name"),
                "latitude": feature["center"][1],
                "longitude": feature["center"][0],
                "city": feature.get("context", [{}])[0].get("text"),
                "country": feature.get("context", [{}])[-1].get("text")
            },
            cost_usd=self.cost_per_call,
            duration_ms=int(response.elapsed.total_seconds() * 1000)
        )
```

**Setup:**
```bash
# Get API key: https://account.mapbox.com/access-tokens/
echo "MAPBOX_API_KEY=pk...." >> .env
```

**Success Criteria:**
- 100% of address lookups use Mapbox (free tier)
- Google Places only called if need reviews/hours/phone

---

### P1-3: Implement Request Deduplication
**Effort:** 4 hours
**Impact:** 💰💰💰 (Eliminate duplicate API calls)
**Savings:** 10-20% of API costs

**Implementation:**
```python
# File: app/services/enrichment/progressive_orchestrator.py

from asyncio import Lock

class ProgressiveEnrichmentOrchestrator:
    def __init__(self):
        self._in_progress: Dict[str, Lock] = {}

    async def enrich_progressive(self, website_url: str, ...):
        cache_key = f"enrichment:{website_url}"

        # Check if already in progress
        if cache_key in self._in_progress:
            logger.info(f"Enrichment already in progress for {website_url} - waiting")
            async with self._in_progress[cache_key]:
                # Wait for existing enrichment to complete
                return await self.cache.get(cache_key)

        # Lock this enrichment
        lock = Lock()
        self._in_progress[cache_key] = lock

        try:
            async with lock:
                # Check cache again (might have been populated while waiting)
                cached = await self.cache.get(cache_key)
                if cached:
                    return cached

                # Do enrichment
                session = await self._do_enrichment(website_url, ...)

                # Cache result
                await self.cache.set(cache_key, session)

                return session
        finally:
            # Release lock
            del self._in_progress[cache_key]
```

**Testing:**
```python
# Launch 10 concurrent enrichments for same URL
tasks = [orchestrator.enrich_progressive("techstart.com") for _ in range(10)]
results = await asyncio.gather(*tasks)

# Should only make 1 API call (not 10)
assert total_api_calls == 1
```

**Success Criteria:**
- Duplicate concurrent requests eliminated
- 10-20% reduction in API costs during busy periods

---

## Phase 3: Advanced Optimizations (1 Week) - Save 80-95%

### P2-1: Implement Cost Budgeting
**Effort:** 1 day
**Impact:** 💰💰💰 (Prevent cost overruns)
**Savings:** Control maximum spend per enrichment

**Implementation:**
```python
# File: app/services/enrichment/progressive_orchestrator.py

class ProgressiveEnrichmentOrchestrator:
    def __init__(self, max_cost_per_enrichment: float = 0.05):
        self.max_cost = max_cost_per_enrichment

    async def _should_call_source(self, source: EnrichmentSource, current_cost: float) -> bool:
        if current_cost + source.cost_per_call > self.max_cost:
            logger.warning(
                f"Skipping {source.name} - would exceed budget "
                f"({current_cost + source.cost_per_call} > {self.max_cost})"
            )
            return False
        return True

    async def _run_layer2(self, domain: str, context: dict):
        current_cost = 0.0
        results = []

        # Call sources in order of cost efficiency (cheap first)
        sources_by_cost = sorted(
            [self.opencorporates_source, self.mapbox_source, self.clearbit_source],
            key=lambda s: s.cost_per_call
        )

        for source in sources_by_cost:
            if await self._should_call_source(source, current_cost):
                result = await source.enrich(domain, **context)
                results.append(result)
                current_cost += result.cost_usd

        return results
```

**Success Criteria:**
- No enrichment exceeds $0.05 budget
- Average cost drops to $0.01-0.03

---

### P2-2: ML-Based Source Selection
**Effort:** 1 week
**Impact:** 💰💰💰💰 (30-50% smarter spending)
**Savings:** Only call sources that provide value

**Implementation:**
```python
# File: app/services/enrichment/intelligent_orchestrator.py

class IntelligentSourceOrchestrator:
    def __init__(self):
        self.model = self._load_trained_model()

    async def select_sources(
        self,
        domain: str,
        industry: Optional[str],
        budget: float
    ) -> List[EnrichmentSource]:
        # Predict which sources will provide value
        features = self._extract_features(domain, industry)
        predictions = self.model.predict(features)

        # Rank sources by predicted value
        source_scores = {
            "opencorporates": predictions["opencorporates_value"],
            "clearbit": predictions["clearbit_value"],
            "google_places": predictions["google_places_value"]
        }

        # Select top sources within budget
        selected = []
        cost = 0.0

        for source_name, score in sorted(source_scores.items(), key=lambda x: x[1], reverse=True):
            source = self._get_source(source_name)
            if cost + source.cost_per_call <= budget:
                selected.append(source)
                cost += source.cost_per_call

        return selected

# Training data
# - Tech companies: OpenCorporates + Wappalyzer (skip Clearbit)
# - Healthcare: Clearbit required (regulatory data)
# - Retail: Google Places critical (store locations)
```

**Success Criteria:**
- 30-50% reduction in unnecessary API calls
- Smart spending based on learned patterns

---

### P3-1: Self-Hosted Company Database
**Effort:** 1 week
**Impact:** 💰💰💰💰💰 (Eliminate costs for common companies)
**Savings:** $0.15 per pre-scraped company

**Implementation:**
```python
# File: scripts/scrape_companies.py

import asyncio
from app.services.data.apify_client import ApifyClient

async def scrape_top_companies():
    client = ApifyClient(api_key=settings.apify_api_token)

    # Scrape top Brazilian companies
    companies = await client.run_actor(
        "apify/google-search-scraper",
        run_input={
            "queries": ["top companies in Brazil", "largest startups in Brazil"],
            "maxResultsPerQuery": 1000
        }
    )

    # Extract company data
    for company in companies:
        data = {
            "domain": extract_domain(company["url"]),
            "name": company["name"],
            "description": company["description"],
            "address": company.get("address"),
            "phone": company.get("phone"),
            "scraped_at": datetime.now()
        }

        # Store in database
        await supabase_service.table("pre_scraped_companies").upsert(data)

# Schedule monthly
# - Scrape top 10,000 companies
# - Store in Supabase
# - Enrich from local DB first (free)
```

**Success Criteria:**
- 80% of enrichments served from pre-scraped DB
- Cost drops to near-zero for common companies

---

## Cost Savings Summary

### Phase 1 (1 Day):
- Re-enable caching: **Save $0.03-0.12 per cached enrichment** (80-90% cache hit rate)
- Smart source skipping: **Save $0.01-0.05 per enrichment** (30-50% Layer 2 reduction)
- Replace GPT with Groq: **Save $0.005 per enrichment** (100% AI cost elimination)
- **Total Phase 1 Savings: 40-60%** → $0.02-0.09 per enrichment

### Phase 2 (3 Days):
- Replace Clearbit: **Save $0.047 per enrichment** (94% reduction)
- Replace Google Places: **Save $0.017 per enrichment** (100% reduction within free tier)
- Request deduplication: **Save 10-20% during busy periods**
- **Total Phase 2 Savings: 60-80%** → $0.003-0.06 per enrichment

### Phase 3 (1 Week):
- Cost budgeting: **Control maximum spend**
- ML source selection: **Save 30-50% on unnecessary calls**
- Pre-scraped DB: **Save $0.15 per common company** (80% of lookups)
- **Total Phase 3 Savings: 80-95%** → $0.001-0.03 per enrichment

---

## Implementation Timeline

### Week 1: Phase 1 (Quick Wins)
**Monday:**
- Morning: Re-enable caching (P0-1)
- Afternoon: Smart source skipping (P0-2)

**Tuesday:**
- Morning: Replace GPT with Groq (P0-3)
- Afternoon: Testing and validation

**Wednesday:**
- Morning: Circuit breakers (P0-4)
- Afternoon: Rate limiting (P0-5)

**Thursday-Friday:**
- Deploy to staging
- Monitor metrics (cache hit rate, cost per enrichment)
- Deploy to production

**Expected Result:**
- Cost: $0.15 → $0.02-0.09 (40-60% reduction)
- Reliability: Circuit breakers prevent cascades

---

### Week 2: Phase 2 (API Replacements)
**Monday-Tuesday:**
- Integrate OpenCorporates (P1-1)
- Test with 100 domains
- Validate data quality

**Wednesday:**
- Integrate Mapbox (P1-2)
- Implement request deduplication (P1-3)

**Thursday-Friday:**
- End-to-end testing
- Deploy to production
- Monitor cost savings

**Expected Result:**
- Cost: $0.02-0.09 → $0.003-0.06 (60-80% total reduction)

---

### Week 3: Phase 3 (Advanced)
**Monday-Tuesday:**
- Implement cost budgeting (P2-1)

**Wednesday-Thursday:**
- ML source selection training (P2-2)

**Friday:**
- Set up pre-scraping infrastructure (P3-1)

**Expected Result:**
- Cost: $0.003-0.06 → $0.001-0.03 (80-95% total reduction)

---

## Success Metrics

### Cost Metrics:
- **Average cost per enrichment:** Track daily
  - Baseline: $0.15
  - Phase 1 target: $0.02-0.09
  - Phase 2 target: $0.003-0.06
  - Phase 3 target: $0.001-0.03

- **Monthly API spend:** Track weekly
  - 10K enrichments: $1,500 → $300 → $60 → $10-30
  - 100K enrichments: $15,000 → $3,000 → $600 → $100-300

### Performance Metrics:
- **Cache hit rate:** Target 70-90%
- **Average enrichment time:** Target 4-6 seconds (was 6-10s)
- **API error rate:** Target <1% (with circuit breakers)
- **Uptime:** Target 99.5% (was 95%)

### Quality Metrics:
- **Confidence scores:** Maintain >80% average
- **Data completeness:** Maintain >70% fields filled
- **User satisfaction:** Track via feedback

---

## Monitoring Dashboard

### Grafana Panels:

1. **Cost Overview**
   - Total spend this month
   - Cost per enrichment (P50, P95)
   - Cost by source (pie chart)

2. **Performance**
   - Enrichments per minute
   - Average duration (P50, P95, P99)
   - Cache hit rate

3. **Quality**
   - Average confidence score
   - Fields filled per enrichment
   - Error rate by source

4. **Alerts**
   - Cost per enrichment > $0.10
   - Cache hit rate < 50%
   - API error rate > 5%
   - Circuit breaker opened

---

## Conclusion

**Timeline:** 3 weeks
**Total Investment:** 10-15 development days
**Expected ROI:** 80-95% cost reduction
**Payback Period:** Immediate (start saving on Day 1)

**At Scale:**
- 10K enrichments/month: Save **$200-1,200/month**
- 100K enrichments/month: Save **$1,500-13,500/month**
- 1M enrichments/month: Save **$15,000-135,000/month**

**Next Steps:**
1. Review and approve roadmap
2. Start Phase 1 implementations (1 day to complete)
3. Monitor metrics and iterate
4. Proceed to Phase 2 after validating Phase 1 results

**Risk Mitigation:**
- Test thoroughly in staging before production
- Deploy incrementally (one optimization at a time)
- Monitor quality metrics (confidence scores)
- Rollback plan for each phase
- Keep Clearbit/Google Places as fallbacks during transition
