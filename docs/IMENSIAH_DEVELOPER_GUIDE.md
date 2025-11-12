# IMENSIAH Developer Guide

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [3-Layer Enrichment System](#3-layer-enrichment-system)
3. [API Endpoints](#api-endpoints)
4. [Data Models](#data-models)
5. [Configuration](#configuration)
6. [Data Sources](#data-sources)
7. [Adding New Sources](#adding-new-sources)
8. [Troubleshooting](#troubleshooting)
9. [Performance Optimization](#performance-optimization)
10. [Testing](#testing)

---

## Architecture Overview

IMENSIAH follows a **progressive enrichment architecture** with Server-Sent Events (SSE) for real-time updates.

### High-Level Architecture

```
┌─────────────┐
│   Browser   │
│  (Frontend) │
└──────┬──────┘
       │ POST /api/form/enrich
       ↓
┌──────────────────────┐
│  FastAPI Backend     │
│  ┌────────────────┐  │
│  │ Form Routes    │  │
│  │ (SSE Stream)   │  │
│  └────────┬───────┘  │
│           ↓          │
│  ┌────────────────┐  │
│  │ Progressive    │  │
│  │ Orchestrator   │  │
│  └────────┬───────┘  │
│           │          │
│  ┌────────┴────────────────┐
│  │                         │
│  ↓         ↓         ↓     │
│ Layer 1  Layer 2  Layer 3 │
│ (<2s)    (3-6s)   (6-10s) │
└──────────────────────────┘
       │
       ↓
┌──────────────┐
│   Supabase   │
│   (Cache)    │
└──────────────┘
```

### Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **Form Routes** | HTTP endpoints, SSE streaming, session management |
| **Progressive Orchestrator** | Coordinates 3-layer parallel enrichment |
| **Data Sources** | Individual API clients (Clearbit, Google, etc.) |
| **Cache Layer** | Supabase storage for 30-day session persistence |
| **Circuit Breakers** | Fault tolerance and graceful degradation |

---

## 3-Layer Enrichment System

IMENSIAH uses a **progressive 3-layer approach** to balance speed and depth:

### Layer 1: Fast & Free (< 2 seconds)

**Purpose:** Instant feedback, "wow" moment

**Sources:**
- Metadata scraping (HTML parsing)
- IP geolocation (IP-API)

**Data Returned:**
- Company name
- Description
- Location (approximate)
- Website technologies
- Logo URL

**Implementation:**
```python
# Execute Layer 1 sources in parallel
layer1_tasks = [
    self.metadata_source.enrich(domain),
    self.ip_api_source.enrich(domain)
]
layer1_results = await asyncio.gather(*layer1_tasks)
```

### Layer 2: Detailed & Paid (3-6 seconds)

**Purpose:** High-quality structured business data

**Sources:**
- Clearbit Company API (~$0.10/call)
- ReceitaWS (Brazilian CNPJ - free)
- Google Places API (~$0.02/call)

**Data Returned:**
- Employee count
- Annual revenue
- Legal name
- CNPJ (Brazil)
- Address and phone
- Google rating

**Implementation:**
```python
# Parallel execution with context from Layer 1
company_name = layer1_data.get("company_name")
layer2_tasks = [
    self.clearbit_source.enrich(domain),
    self.receita_ws_source.enrich(domain, company_name=company_name),
    self.google_places_source.enrich(domain, company_name=company_name)
]
layer2_results = await asyncio.gather(*layer2_tasks)
```

### Layer 3: AI & Professional (6-10 seconds)

**Purpose:** Strategic insights and professional network data

**Sources:**
- OpenRouter GPT-4o-mini (~$0.001/call)
- Proxycurl LinkedIn API (~$0.02/call)

**Data Returned:**
- Industry classification (AI)
- Company size category (AI)
- Digital maturity (AI)
- Target audience (AI)
- Key differentiators (AI)
- LinkedIn followers

**Implementation:**
```python
# AI inference + LinkedIn data
all_data = {**layer1_data, **layer2_data, **existing_data}

layer3_tasks = [
    ai_client.extract_company_info_from_text(
        website_url=website_url,
        scraped_metadata=layer1_data,
        user_description=existing_data.get("description")
    ),
    self.proxycurl_source.enrich(domain, company_name=company_name)
]
layer3_results = await asyncio.gather(*layer3_tasks)
```

---

## API Endpoints

### POST /api/form/enrich

**Fast form enrichment with progressive SSE streaming**

#### Request

```http
POST /api/form/enrich HTTP/1.1
Content-Type: application/json

{
  "website": "techstart.com",
  "email": "founder@techstart.com"
}
```

**Request Schema:**
```python
class FormEnrichmentRequest(BaseModel):
    website: Optional[str]  # Can also use "url" field
    url: Optional[str]      # Alias for "website"
    email: str              # Required
```

#### Response (SSE Stream)

```
event: layer1_complete
data: {"status":"layer1_complete","fields":{"name":"TechStart","city":"São Paulo"},"duration_ms":1850,"sources":["metadata","ip_api"]}

event: layer2_complete
data: {"status":"layer2_complete","fields":{"name":"TechStart","employeeCount":"25-50","industry":"Technology"},"duration_ms":4200,"sources":["clearbit","receita_ws"]}

event: layer3_complete
data: {"status":"layer3_complete","fields":{"digitalMaturity":"High","companySize":"Small"},"duration_ms":8500,"sources":["OpenRouter GPT-4o-mini"]}

event: complete
data: {"status":"complete","session_id":"abc-123-def-456","total_duration_ms":8500,"total_cost_usd":0.12}
```

#### Response Events

| Event | Timing | Description |
|-------|--------|-------------|
| `layer1_complete` | < 2s | Basic metadata available |
| `layer2_complete` | 3-6s | Structured business data |
| `layer3_complete` | 6-10s | AI insights complete |
| `complete` | Final | All enrichment finished |
| `error` | On failure | Error details |

#### Frontend Integration

```typescript
const eventSource = new EventSource('/api/form/enrich');

eventSource.addEventListener('layer1_complete', (e) => {
  const data = JSON.parse(e.data);
  updateFormFields(data.fields);  // Progressive update
});

eventSource.addEventListener('layer2_complete', (e) => {
  const data = JSON.parse(e.data);
  updateFormFields(data.fields);  // More fields added
});

eventSource.addEventListener('layer3_complete', (e) => {
  const data = JSON.parse(e.data);
  updateFormFields(data.fields);  // Final fields
});

eventSource.addEventListener('complete', (e) => {
  const data = JSON.parse(e.data);
  setSessionId(data.session_id);  // Save for Phase 2
  eventSource.close();
});

eventSource.addEventListener('error', (e) => {
  const data = JSON.parse(e.data);
  handleError(data.message);
  eventSource.close();
});
```

---

### GET /api/form/session/{session_id}

**Retrieve cached enrichment session**

#### Request

```http
GET /api/form/session/abc-123-def-456 HTTP/1.1
```

#### Response

```json
{
  "session_id": "abc-123-def-456",
  "website_url": "https://techstart.com",
  "user_email": "founder@techstart.com",
  "enrichment_data": {
    "layer1_result": { ... },
    "layer2_result": { ... },
    "layer3_result": { ... },
    "fields_auto_filled": { ... },
    "confidence_scores": { ... }
  },
  "created_at": "2025-01-09T14:23:45Z",
  "expires_at": "2025-02-08T14:23:45Z"
}
```

**Use Case:** Load cached data in Phase 2 (strategic analysis) to avoid re-scraping.

---

### GET /api/form/health

**Health check endpoint**

#### Response

```json
{
  "status": "healthy",
  "service": "form-enrichment",
  "active_sessions": 42,
  "timestamp": "2025-01-09T14:30:00Z"
}
```

---

## Data Models

### ProgressiveEnrichmentSession

**Complete session tracking**

```python
class ProgressiveEnrichmentSession(BaseModel):
    session_id: str
    website_url: str
    user_email: Optional[str]

    # Layer results
    layer1_result: Optional[LayerResult]
    layer2_result: Optional[LayerResult]
    layer3_result: Optional[LayerResult]

    # Aggregated data
    total_duration_ms: int
    total_cost_usd: float
    fields_auto_filled: Dict[str, Any]
    confidence_scores: Dict[str, float]

    # Status tracking
    status: str  # "pending" | "layer1_complete" | "layer2_complete" | "complete"
    started_at: Optional[datetime]
```

### LayerResult

**Individual layer completion**

```python
class LayerResult(BaseModel):
    layer_number: int  # 1, 2, or 3
    completed_at: datetime
    duration_ms: int
    fields_populated: List[str]
    data: Dict[str, Any]
    sources_called: List[str]
    cost_usd: float
    confidence_avg: float
```

### SourceResult

**Individual data source result**

```python
class SourceResult(BaseModel):
    source_name: str
    success: bool
    data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    error_type: Optional[str]
    duration_ms: int
    cost_usd: float
    cached: bool
```

---

## Configuration

### Environment Variables

```bash
# API Keys
CLEARBIT_API_KEY=sk_xxxxxxxxxxxx
GOOGLE_PLACES_API_KEY=AIzaxxxxxxxxxxxx
PROXYCURL_API_KEY=xxxxxxxxxxxx
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxx

# Supabase (for caching)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxxxxxxxxxx

# Application Settings
ENRICHMENT_CACHE_TTL_DAYS=30
ENRICHMENT_TIMEOUT_SECONDS=15
CIRCUIT_BREAKER_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT_SECONDS=60
```

### Settings Class

```python
# app/core/config.py
class Settings(BaseSettings):
    # API Keys
    clearbit_api_key: Optional[str] = None
    google_places_api_key: Optional[str] = None
    proxycurl_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    # Supabase
    supabase_url: str
    supabase_key: str

    # Enrichment
    enrichment_cache_ttl_days: int = 30
    enrichment_timeout_seconds: int = 15

    class Config:
        env_file = ".env"
```

---

## Data Sources

### Metadata Source (Free)

**File:** `app/services/enrichment/sources/metadata.py`

**What it does:** Scrapes website HTML for company information

**Data extracted:**
- Company name (title, og:site_name)
- Description (meta description, og:description)
- Logo (og:image, favicon)
- Technologies (React, Next.js, WordPress, etc.)
- Social media links

**Performance:** 300-500ms

**Cost:** $0.00

**Usage:**
```python
source = MetadataSource()
result = await source.enrich("techstart.com")
print(result.data["company_name"])  # "TechStart"
```

---

### IP API Source (Free)

**File:** `app/services/enrichment/sources/ip_api.py`

**What it does:** Geolocation from domain IP address

**Data extracted:**
- City and region
- Country
- Timezone
- Approximate coordinates

**Performance:** 100-200ms

**Cost:** $0.00

**Limitations:** Approximate location (not building-level)

---

### Clearbit Source (Paid)

**File:** `app/services/enrichment/sources/clearbit.py`

**What it does:** Comprehensive company intelligence

**Data extracted:**
- Legal name
- Employee count (range)
- Annual revenue (estimate)
- Founded year
- Industry and sector
- Company type (public/private)
- Logo and social media

**Performance:** 1-2 seconds

**Cost:** ~$0.10 per lookup

**API:** https://company.clearbit.com/v2/companies/find

**Rate Limits:** 600 requests/minute (plan dependent)

---

### ReceitaWS Source (Free)

**File:** `app/services/enrichment/sources/receita_ws.py`

**What it does:** Brazilian CNPJ government registry lookup

**Data extracted:**
- CNPJ (formatted)
- Legal name
- CNAE code (industry)
- Legal nature (LTDA, SA, etc.)
- Registration status
- Registration date

**Performance:** 2-3 seconds

**Cost:** $0.00 (government API)

**API:** https://www.receitaws.com.br/v1/cnpj/

**Note:** Only works for Brazilian companies with CNPJ

---

### Google Places Source (Paid)

**File:** `app/services/enrichment/sources/google_places.py`

**What it does:** Location verification and ratings

**Data extracted:**
- Full address
- Phone number
- Place ID
- Google rating (0-5)
- Reviews count
- Verified location

**Performance:** 1-2 seconds

**Cost:** ~$0.02 per lookup

**API:** Google Places API (Text Search + Place Details)

**Rate Limits:** Depends on billing plan

---

### Proxycurl Source (Paid)

**File:** `app/services/enrichment/sources/proxycurl.py`

**What it does:** LinkedIn company data

**Data extracted:**
- LinkedIn URL
- Follower count
- Company description
- Specialties
- Industry tags

**Performance:** 2-3 seconds

**Cost:** ~$0.02 per lookup

**API:** https://nubela.co/proxycurl/

**Note:** Requires LinkedIn company page to exist

---

### OpenRouter AI Source (Paid)

**File:** `app/services/ai/openrouter_client.py`

**What it does:** AI inference for strategic insights

**Data extracted:**
- Industry classification
- Company size category
- Digital maturity level
- Target audience
- Key differentiators

**Model:** GPT-4o-mini (fast, cost-effective)

**Performance:** 3-5 seconds

**Cost:** ~$0.001 per extraction

**API:** https://openrouter.ai/api/v1/chat/completions

---

## Adding New Sources

### Step 1: Create Source Class

Create a new file in `app/services/enrichment/sources/`:

```python
# app/services/enrichment/sources/my_source.py
from .base import EnrichmentSource, SourceResult
import httpx
import time

class MySource(EnrichmentSource):
    """
    Fetch data from MyAPI.

    Provides:
    - Field 1
    - Field 2
    - Field 3

    Cost: $X per call
    Performance: Ys
    """

    def __init__(self):
        super().__init__(name="my_source", cost_per_call=0.05)
        self.api_url = "https://api.example.com/v1/enrich"
        self.api_key = get_settings().my_api_key

    async def enrich(self, domain: str, **kwargs) -> SourceResult:
        """Fetch data from MyAPI"""
        start_time = time.time()

        try:
            # Make API call
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.api_url,
                    params={"domain": domain},
                    headers={"Authorization": f"Bearer {self.api_key}"}
                )
                response.raise_for_status()
                data = response.json()

            # Extract and normalize
            enriched_data = {
                "field1": data.get("field1"),
                "field2": data.get("field2"),
                "field3": data.get("field3"),
            }

            # Remove None values
            enriched_data = {k: v for k, v in enriched_data.items() if v}

            duration_ms = int((time.time() - start_time) * 1000)

            return SourceResult(
                source_name=self.name,
                success=True,
                data=enriched_data,
                duration_ms=duration_ms,
                cost_usd=self.cost_per_call
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            raise Exception(f"MyAPI error: {str(e)}")
```

### Step 2: Add to Orchestrator

```python
# app/services/enrichment/progressive_orchestrator.py

class ProgressiveEnrichmentOrchestrator:
    def __init__(self):
        # ... existing sources ...

        # Add your source to appropriate layer
        self.my_source = MySource()

    async def enrich_progressive(self, ...):
        # Add to layer tasks
        layer2_tasks = [
            # ... existing sources ...
            self.my_source.enrich(domain),
        ]
```

### Step 3: Add Environment Variable

```bash
# .env
MY_API_KEY=xxxxxxxxxxxx
```

```python
# app/core/config.py
class Settings(BaseSettings):
    my_api_key: Optional[str] = None
```

### Step 4: Test Your Source

```python
# tests/integration/test_my_source.py
import pytest
from app.services.enrichment.sources.my_source import MySource

@pytest.mark.asyncio
async def test_my_source():
    source = MySource()
    result = await source.enrich("techstart.com")

    assert result.success
    assert result.data is not None
    assert "field1" in result.data
    assert result.duration_ms > 0
```

---

## Troubleshooting

### Common Issues

#### 1. SSE Stream Not Connecting

**Symptom:** Frontend doesn't receive events

**Causes:**
- CORS issues
- Nginx buffering
- Firewall blocking SSE

**Solution:**
```python
# Ensure headers are set
return StreamingResponse(
    event_stream(),
    media_type="text/event-stream",
    headers={
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",  # Disable nginx buffering
    }
)
```

#### 2. Circuit Breaker Opens Frequently

**Symptom:** Sources failing with "circuit breaker open"

**Causes:**
- API rate limits
- Network instability
- Invalid API keys

**Solution:**
```python
# Check circuit breaker state
if source.circuit_breaker.state == "open":
    logger.warning(f"Circuit breaker open for {source.name}")
    # Wait for reset or check API status

# Adjust thresholds
circuit_breaker = CircuitBreaker(
    failure_threshold=10,  # Increase tolerance
    timeout_duration=120   # Longer reset time
)
```

#### 3. Enrichment Timeout

**Symptom:** Enrichment never completes

**Causes:**
- Slow API responses
- Network issues
- Large HTML pages

**Solution:**
```python
# Increase timeout
source.timeout = 15.0  # seconds

# Add overall orchestrator timeout
async with asyncio.timeout(30):  # 30 second max
    session = await orchestrator.enrich_progressive(...)
```

#### 4. Cache Misses

**Symptom:** Session not found in cache

**Causes:**
- Expired sessions (> 30 days)
- Database connection issues
- Session ID mismatch

**Solution:**
```python
# Check both memory and database
if session_id in active_enrichment_sessions:
    return active_enrichment_sessions[session_id]

# Fallback to database
enrichment_data = await cache.load_session(session_id)
if not enrichment_data:
    raise HTTPException(404, "Session not found or expired")
```

---

## Performance Optimization

### 1. Parallel Execution

**Always use `asyncio.gather()` for parallel API calls:**

```python
# Good: Parallel execution (fast)
results = await asyncio.gather(
    source1.enrich(domain),
    source2.enrich(domain),
    source3.enrich(domain)
)

# Bad: Sequential execution (slow)
result1 = await source1.enrich(domain)
result2 = await source2.enrich(domain)
result3 = await source3.enrich(domain)
```

### 2. Caching Strategy

**Cache at multiple levels:**

```python
# 1. In-memory cache (fastest)
active_enrichment_sessions[session_id] = session_data

# 2. Database cache (persistent)
await cache.save_session(session_id, enrichment_data)

# 3. HTTP caching (CDN)
response.headers["Cache-Control"] = "public, max-age=3600"
```

### 3. Graceful Degradation

**Never fail completely - return partial data:**

```python
try:
    result = await expensive_source.enrich(domain)
except Exception as e:
    logger.warning(f"Source failed: {e}")
    # Continue with other sources
    # Return partial data to user
```

### 4. Connection Pooling

**Reuse HTTP connections:**

```python
# Use single client instance
async with httpx.AsyncClient(
    timeout=10.0,
    limits=httpx.Limits(max_connections=100)
) as client:
    # Make multiple requests with same client
    response1 = await client.get(url1)
    response2 = await client.get(url2)
```

### 5. Rate Limit Management

**Implement exponential backoff:**

```python
async def enrich_with_retry(source, domain, max_retries=3):
    for attempt in range(max_retries):
        try:
            return await source.enrich(domain)
        except RateLimitError:
            wait_time = 2 ** attempt  # Exponential backoff
            await asyncio.sleep(wait_time)
    raise Exception("Max retries exceeded")
```

---

## Testing

### Unit Tests

```python
# tests/unit/test_metadata_source.py
import pytest
from app.services.enrichment.sources.metadata import MetadataSource

@pytest.mark.asyncio
async def test_metadata_extraction():
    source = MetadataSource()
    result = await source.enrich("example.com")

    assert result.success
    assert "company_name" in result.data
    assert result.cost_usd == 0.0
```

### Integration Tests

```python
# tests/integration/test_progressive_enrichment.py
import pytest
from app.services.enrichment.progressive_orchestrator import ProgressiveEnrichmentOrchestrator

@pytest.mark.asyncio
async def test_full_enrichment():
    orchestrator = ProgressiveEnrichmentOrchestrator()
    session = await orchestrator.enrich_progressive(
        website_url="https://techstart.com",
        user_email="test@test.com"
    )

    assert session.layer1_result is not None
    assert session.layer2_result is not None
    assert session.layer3_result is not None
    assert session.status == "complete"
    assert session.total_duration_ms > 0
```

### E2E Tests

```python
# tests/e2e/test_form_enrichment_flow.py
import pytest
from fastapi.testclient import TestClient

def test_sse_enrichment_flow(client: TestClient):
    with client.stream("POST", "/api/form/enrich", json={
        "website": "techstart.com",
        "email": "test@test.com"
    }) as response:
        events = []
        for line in response.iter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line[5:]))

        # Verify event sequence
        assert events[0]["status"] == "layer1_complete"
        assert events[1]["status"] == "layer2_complete"
        assert events[2]["status"] == "layer3_complete"
        assert events[3]["status"] == "complete"
        assert "session_id" in events[3]
```

---

## API Documentation

See [IMENSIAH_API_REFERENCE.md](./IMENSIAH_API_REFERENCE.md) for complete OpenAPI specification.

---

*Last Updated: January 2025*
*Version: 1.0.0*
