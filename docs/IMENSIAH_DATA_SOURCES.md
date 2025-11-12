# IMENSIAH Data Sources Documentation

Complete reference for all data sources used in the IMENSIAH enrichment system.

---

## Overview

IMENSIAH uses **6 primary data sources** organized into 3 enrichment layers:

| Layer | Timing | Sources | Cost | Purpose |
|-------|--------|---------|------|---------|
| **Layer 1** | < 2s | Metadata, IP-API | Free | Instant feedback |
| **Layer 2** | 3-6s | Clearbit, ReceitaWS, Google Places | ~$0.12 | Structured business data |
| **Layer 3** | 6-10s | OpenRouter AI, Proxycurl | ~$0.02 | Strategic insights |

**Total Cost:** $0.01 - $0.15 per enrichment (average $0.05)

---

## Layer 1: Free & Fast Sources

### 1. Metadata Scraping

**Purpose:** Extract company information from public website

**Implementation:** `app/services/enrichment/sources/metadata.py`

**Technology:** BeautifulSoup4 HTML parsing

**What It Provides:**

| Field | Description | Example |
|-------|-------------|---------|
| `company_name` | From title or og:site_name | "TechStart Innovations" |
| `description` | From meta description | "B2B SaaS platform for enterprise automation" |
| `meta_description` | HTML meta description | "Enterprise automation made simple" |
| `meta_keywords` | HTML meta keywords | ["saas", "automation", "b2b"] |
| `logo_url` | From og:image or favicon | "https://techstart.com/logo.png" |
| `website_tech` | Detected technologies | ["React", "Next.js", "Vercel"] |
| `social_media` | Social media links | {"linkedin": "...", "twitter": "..."} |

**Technology Detection:**

Automatically detects:
- **Frameworks:** React, Next.js, Vue.js, Angular, Django, Flask
- **CMS:** WordPress, Shopify, Wix, Webflow
- **Infrastructure:** Nginx, Apache, Cloudflare, Vercel
- **Libraries:** jQuery, Bootstrap, Tailwind CSS

**Performance:**
- Latency: 300-500ms
- Success Rate: 95%+ (if website is accessible)
- Timeout: 10 seconds

**Cost:** $0.00 (free)

**Reliability:** High (depends on website uptime)

**Setup:**

No API key required. Works out of the box.

**Limitations:**
- Requires publicly accessible website
- Limited by website structure (may miss data)
- No structured business data (employee count, revenue)
- Company name may be title-based (not always legal name)

**Code Example:**

```python
from app.services.enrichment.sources.metadata import MetadataSource

source = MetadataSource()
result = await source.enrich("techstart.com")

print(result.data["company_name"])  # "TechStart"
print(result.data["website_tech"])  # ["React", "Next.js"]
```

---

### 2. IP-API Geolocation

**Purpose:** Approximate geographic location from domain IP address

**Implementation:** `app/services/enrichment/sources/ip_api.py`

**API:** https://ip-api.com/json/{ip}

**What It Provides:**

| Field | Description | Example |
|-------|-------------|---------|
| `ip_location` | City, country | "São Paulo, Brazil" |
| `city` | City name | "São Paulo" |
| `region` | State/region | "SP" |
| `country` | Country name | "Brazil" |
| `country_code` | ISO country code | "BR" |
| `timezone` | IANA timezone | "America/Sao_Paulo" |
| `lat` | Latitude | -23.5505 |
| `lon` | Longitude | -46.6333 |

**How It Works:**

1. Resolves domain to IP address
2. Queries IP-API for geolocation
3. Returns approximate city-level location

**Performance:**
- Latency: 100-200ms
- Success Rate: 90%+ (if domain resolves)
- Timeout: 5 seconds

**Cost:** $0.00 (free tier: 45 requests/minute)

**Reliability:** Medium (IP location is approximate)

**Setup:**

No API key required for free tier.

**Limitations:**
- **Approximate location** (not building-level accuracy)
- May show hosting provider location (not company HQ)
- Limited to 45 requests/minute (free tier)
- Doesn't work for CDN-hosted sites (shows CDN location)

**Code Example:**

```python
from app.services.enrichment.sources.ip_api import IpApiSource

source = IpApiSource()
result = await source.enrich("techstart.com")

print(result.data["ip_location"])  # "São Paulo, Brazil"
print(result.data["timezone"])     # "America/Sao_Paulo"
```

**Upgrade Options:**

- **Pro Plan:** $13/month for 10,000 requests
- **Business Plan:** $49/month for 100,000 requests
- Features: HTTPS, commercial use, higher rate limits

---

## Layer 2: Structured Business Data

### 3. Clearbit Company API

**Purpose:** Comprehensive B2B company intelligence

**Implementation:** `app/services/enrichment/sources/clearbit.py`

**API:** https://company.clearbit.com/v2/companies/find

**What It Provides:**

| Field | Description | Example |
|-------|-------------|---------|
| `company_name` | Legal company name | "TechStart Innovations" |
| `legal_name` | Full legal name | "TechStart Innovations LTDA" |
| `description` | Company description | "B2B SaaS platform..." |
| `industry` | Industry classification | "Technology" |
| `sector` | Business sector | "Information Technology & Services" |
| `tags` | Industry tags | ["SaaS", "Enterprise", "Automation"] |
| `employee_count` | Employee range | "25-50" |
| `employee_count_exact` | Exact count (if known) | 37 |
| `annual_revenue` | Revenue estimate | "$5M-$10M" |
| `company_type` | Public/private/nonprofit | "Private" |
| `founded_year` | Year founded | 2019 |
| `location` | HQ location | "São Paulo, SP, Brazil" |
| `city` | City | "São Paulo" |
| `state` | State/region | "SP" |
| `country` | Country | "Brazil" |
| `logo_url` | Company logo | "https://logo.clearbit.com/..." |
| `social_media` | Social profiles | {"linkedin": "...", "twitter": "..."} |
| `website_tech` | Technology stack | ["React", "PostgreSQL", "AWS"] |

**Data Quality:**

- Excellent for US companies (90%+ coverage)
- Good for EU companies (70%+ coverage)
- Moderate for South America (40%+ coverage)
- Limited for Asia/Africa (<30% coverage)

**Performance:**
- Latency: 1-2 seconds
- Success Rate: 60-80% (depends on region)
- Timeout: 10 seconds

**Cost:**
- **Free Trial:** 50 requests
- **Paid Plan:** ~$0.10 per successful lookup
- **Pricing:** Contact sales for volume discounts

**Reliability:** High (99.9% uptime SLA)

**Setup:**

1. Sign up at https://clearbit.com
2. Get API key from dashboard
3. Set environment variable:

```bash
CLEARBIT_API_KEY=sk_xxxxxxxxxxxx
```

**Rate Limits:**
- **Free:** 50 requests total
- **Paid:** 600 requests/minute (plan dependent)

**Limitations:**
- Paid service (cost per lookup)
- Limited coverage outside US/EU
- May not have data for small/new companies
- Requires active API key

**Error Handling:**

```python
# 404: Company not found
# 402: Credits exhausted (payment required)
# 429: Rate limit exceeded
```

**Code Example:**

```python
from app.services.enrichment.sources.clearbit import ClearbitSource

source = ClearbitSource()
result = await source.enrich("techstart.com")

print(result.data["employee_count"])  # "25-50"
print(result.data["annual_revenue"])  # "$5M-$10M"
```

**Alternatives:**
- **FullContact:** Similar service, different pricing
- **Pipl:** People + company data
- **ZoomInfo:** B2B intelligence (expensive)

---

### 4. ReceitaWS (Brazilian CNPJ Registry)

**Purpose:** Official Brazilian company registration data

**Implementation:** `app/services/enrichment/sources/receita_ws.py`

**API:** https://www.receitaws.com.br/v1/cnpj/{cnpj}

**What It Provides:**

| Field | Description | Example |
|-------|-------------|---------|
| `cnpj` | Formatted CNPJ | "12.345.678/0001-99" |
| `legal_name` | Legal entity name | "TechStart Innovations LTDA" |
| `company_name` | Trade name | "TechStart" |
| `cnae` | Industry code | "6201-5/00" (Software development) |
| `legal_nature` | Legal structure | "LTDA" (Limited liability) |
| `registration_status` | Active/inactive | "ATIVA" |
| `registration_date` | Date registered | "01/03/2019" |
| `address` | Full address | "Av. Paulista, 1000 - Bela Vista" |
| `city` | City | "São Paulo" |
| `state` | State | "SP" |
| `zip_code` | CEP | "01310-100" |
| `phone` | Phone | "(11) 1234-5678" |
| `email` | Email | "contact@techstart.com" |
| `capital_social` | Share capital | "R$ 100.000,00" |

**Data Quality:**

- **Excellent:** Government-verified data
- **Accuracy:** 99%+ (official registry)
- **Coverage:** 100% of registered Brazilian companies

**Performance:**
- Latency: 2-3 seconds
- Success Rate: 95%+ (if CNPJ exists)
- Timeout: 10 seconds

**Cost:** $0.00 (free government API)

**Reliability:** Medium (occasional downtime, rate limits)

**Setup:**

No API key required. Works out of the box.

**Rate Limits:**
- **3 requests per minute** (free tier)
- May be throttled during peak hours

**Limitations:**
- **Brazilian companies only** (requires CNPJ)
- Slower response time (2-3s)
- Occasional API downtime
- Rate limited to 3 req/min
- No international company data

**How CNPJ Lookup Works:**

1. Try to find CNPJ from company name + city
2. Use Serasa/Receita Federal search
3. Query ReceitaWS with found CNPJ
4. Return government-verified data

**Code Example:**

```python
from app.services.enrichment.sources.receita_ws import ReceitaWSSource

source = ReceitaWSSource()
result = await source.enrich(
    domain="techstart.com",
    company_name="TechStart Innovations"
)

print(result.data["cnpj"])           # "12.345.678/0001-99"
print(result.data["legal_nature"])   # "LTDA"
```

**Alternatives:**
- **Serasa Experian API:** Paid, more reliable
- **Receita Federal Direct:** Official source (complex auth)
- **BrasilAPI:** Alternative free CNPJ API

---

### 5. Google Places API

**Purpose:** Location verification and reviews

**Implementation:** `app/services/enrichment/sources/google_places.py`

**APIs Used:**
- **Text Search:** Find place by company name
- **Place Details:** Get comprehensive place data

**What It Provides:**

| Field | Description | Example |
|-------|-------------|---------|
| `place_id` | Google Place ID | "ChIJN1t_tDeuEmsRUsoyG..." |
| `company_name` | Business name | "TechStart Innovations" |
| `address` | Full address | "Av. Paulista, 1000 - Bela Vista, São Paulo - SP, 01310-100" |
| `phone` | Phone number | "+55 11 1234-5678" |
| `website` | Website URL | "https://techstart.com" |
| `rating` | Google rating (0-5) | 4.7 |
| `reviews_count` | Number of reviews | 23 |
| `location` | City, state | "São Paulo, SP" |
| `lat` | Latitude | -23.5505 |
| `lng` | Longitude | -46.6333 |
| `business_status` | Operational status | "OPERATIONAL" |
| `types` | Place types | ["establishment", "point_of_interest"] |

**Data Quality:**

- **Excellent:** User-verified data
- **Accuracy:** 95%+ (for physical locations)
- **Coverage:** Global (best for retail/physical businesses)

**Performance:**
- Latency: 1-2 seconds (2 API calls)
- Success Rate: 60-70% (works best for physical businesses)
- Timeout: 10 seconds

**Cost:**
- **Text Search:** $0.017 per request
- **Place Details:** $0.017 per request
- **Total:** ~$0.034 per enrichment
- **Free Tier:** $200 credit/month (= 5,882 requests)

**Reliability:** High (99.9% uptime SLA)

**Setup:**

1. Enable Google Places API in Google Cloud Console
2. Create API key
3. Set environment variable:

```bash
GOOGLE_PLACES_API_KEY=AIzaxxxxxxxxxxxx
```

**Rate Limits:**
- No strict rate limits
- Priced per request
- Monitor usage in Google Cloud Console

**Limitations:**
- **Paid service** (cost per lookup)
- Works best for physical businesses (stores, restaurants, offices)
- Limited data for fully digital companies
- May not find businesses without Google My Business listing

**Code Example:**

```python
from app.services.enrichment.sources.google_places import GooglePlacesSource

source = GooglePlacesSource()
result = await source.enrich(
    domain="techstart.com",
    company_name="TechStart Innovations",
    city="São Paulo"
)

print(result.data["rating"])         # 4.7
print(result.data["reviews_count"])  # 23
print(result.data["address"])        # Full address
```

**Alternatives:**
- **Yelp Fusion API:** Similar for US businesses
- **Foursquare Places API:** Global places data
- **Here Places API:** Alternative mapping service

---

## Layer 3: AI & Professional Data

### 6. OpenRouter AI (GPT-4o-mini)

**Purpose:** AI-powered strategic insights and inference

**Implementation:** `app/services/ai/openrouter_client.py`

**API:** https://openrouter.ai/api/v1/chat/completions

**Model Used:** `openai/gpt-4o-mini`

**What It Provides:**

| Field | Description | Example |
|-------|-------------|---------|
| `ai_industry` | Industry classification | "Technology / SaaS" |
| `ai_company_size` | Size category | "Small" (1-50), "Medium" (51-500), "Large" (501+) |
| `ai_digital_maturity` | Digital adoption | "Low", "Medium", "High" |
| `ai_target_audience` | Who they serve | "B2B Enterprise" |
| `ai_key_differentiators` | Unique selling points | "AI-powered automation, Real-time analytics" |

**How It Works:**

1. Combines data from Layer 1 + Layer 2
2. Sends structured prompt to GPT-4o-mini
3. Parses JSON response
4. Returns AI-inferred strategic insights

**Prompt Template:**

```python
You are analyzing a company based on the following data:

Website: {website_url}
Metadata: {scraped_metadata}
Description: {user_description}

Extract the following information:
- industry: Industry classification
- company_size: Small/Medium/Large
- digital_maturity: Low/Medium/High
- target_audience: Who does this company serve?
- key_differentiators: What makes them unique?

Respond with valid JSON only.
```

**Data Quality:**

- **Good:** AI inference is intelligent but not perfect
- **Accuracy:** 70-85% (depends on input quality)
- **Confidence:** Medium (should be reviewed by user)

**Performance:**
- Latency: 3-5 seconds
- Success Rate: 95%+ (if API available)
- Timeout: 15 seconds

**Cost:**
- **GPT-4o-mini:** $0.15 / 1M input tokens, $0.60 / 1M output tokens
- **Average:** ~$0.001 per enrichment
- **Very cost-effective!**

**Reliability:** High (99.9% uptime)

**Setup:**

1. Sign up at https://openrouter.ai
2. Get API key
3. Set environment variable:

```bash
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxx
```

**Rate Limits:**
- Depends on OpenRouter plan
- Free tier: Limited tokens
- Paid tier: Generous limits

**Limitations:**
- **AI-inferred data** (not verified)
- Quality depends on input data richness
- May hallucinate if data is sparse
- Requires review by user

**Code Example:**

```python
from app.services.ai.openrouter_client import get_openrouter_client

client = await get_openrouter_client()
result = await client.extract_company_info_from_text(
    website_url="https://techstart.com",
    scraped_metadata={"description": "B2B SaaS platform..."},
    user_description="Enterprise automation software"
)

print(result.industry)              # "Technology / SaaS"
print(result.company_size)          # "Small"
print(result.digital_maturity)      # "High"
```

**Alternatives:**
- **OpenAI GPT-4:** More accurate, more expensive
- **Anthropic Claude:** Similar quality
- **Cohere:** Classification-focused
- **Local LLMs:** Free but requires infrastructure

---

### 7. Proxycurl LinkedIn API

**Purpose:** Professional network data from LinkedIn

**Implementation:** `app/services/enrichment/sources/proxycurl.py`

**API:** https://nubela.co/proxycurl/

**Endpoints Used:**
- **Company Profile:** Get LinkedIn company data

**What It Provides:**

| Field | Description | Example |
|-------|-------------|---------|
| `linkedin_url` | LinkedIn company page | "https://linkedin.com/company/techstart" |
| `linkedin_followers` | Follower count | 1,247 |
| `linkedin_description` | About section | "We empower enterprises with AI-driven automation..." |
| `specialties` | Company specialties | ["Enterprise Automation", "SaaS", "AI"] |
| `employee_count` | Employee count | 37 |
| `founded_year` | Year founded | 2019 |
| `industry` | LinkedIn industry | "Computer Software" |
| `company_size` | Size range | "11-50 employees" |
| `headquarters` | HQ location | "São Paulo, São Paulo, Brazil" |

**Data Quality:**

- **Excellent:** LinkedIn-verified data
- **Accuracy:** 90%+ (self-reported by companies)
- **Coverage:** Global (if company has LinkedIn page)

**Performance:**
- Latency: 2-3 seconds
- Success Rate: 70-80% (if LinkedIn page exists)
- Timeout: 10 seconds

**Cost:**
- **Company Lookup:** $0.02 per request
- **Pricing:** Pay-as-you-go or monthly credits

**Reliability:** High (99.5% uptime)

**Setup:**

1. Sign up at https://nubela.co/proxycurl/
2. Get API key
3. Set environment variable:

```bash
PROXYCURL_API_KEY=xxxxxxxxxxxx
```

**Rate Limits:**
- **300 requests per second** (generous!)
- Priced per request (not rate limited)

**Limitations:**
- **Paid service** (cost per lookup)
- Requires LinkedIn company page
- Not all companies maintain LinkedIn pages
- Data freshness depends on company updates

**Code Example:**

```python
from app.services.enrichment.sources.proxycurl import ProxycurlSource

source = ProxycurlSource()
result = await source.enrich(
    domain="techstart.com",
    company_name="TechStart Innovations",
    linkedin_url="https://linkedin.com/company/techstart"  # Optional
)

print(result.data["linkedin_followers"])  # 1247
print(result.data["specialties"])         # ["AI", "SaaS", ...]
```

**Alternatives:**
- **LinkedIn Official API:** Complex auth, limited access
- **ScraperAPI LinkedIn:** Alternative scraping service
- **Bright Data:** Web scraping platform

---

## Cost Breakdown

### Cost per Enrichment

| Source | Layer | Cost | Required |
|--------|-------|------|----------|
| Metadata | 1 | $0.000 | Yes |
| IP-API | 1 | $0.000 | Yes |
| Clearbit | 2 | $0.100 | If available |
| ReceitaWS | 2 | $0.000 | Brazil only |
| Google Places | 2 | $0.034 | If available |
| OpenRouter AI | 3 | $0.001 | Yes |
| Proxycurl | 3 | $0.020 | If available |

**Average Costs:**
- **Minimum:** $0.001 (no paid APIs available)
- **Typical:** $0.05-$0.10 (Clearbit + Google)
- **Maximum:** $0.155 (all paid APIs)

**Monthly Costs (1,000 enrichments):**
- **Minimum:** $1
- **Typical:** $50-$100
- **Maximum:** $155

---

## Setup Instructions

### 1. Create Accounts

Sign up for these services:

- **Clearbit:** https://clearbit.com
- **Google Cloud:** https://console.cloud.google.com
- **OpenRouter:** https://openrouter.ai
- **Proxycurl:** https://nubela.co/proxycurl

### 2. Get API Keys

Obtain API keys from dashboards.

### 3. Set Environment Variables

Create `.env` file:

```bash
# Clearbit
CLEARBIT_API_KEY=sk_xxxxxxxxxxxx

# Google Places
GOOGLE_PLACES_API_KEY=AIzaxxxxxxxxxxxx

# OpenRouter
OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxx

# Proxycurl
PROXYCURL_API_KEY=xxxxxxxxxxxx

# Supabase (for caching)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxxxxxxxxxx
```

### 4. Verify Setup

Test each source:

```bash
python -m pytest tests/integration/test_data_sources.py
```

---

## Monitoring and Logging

### Track API Costs

```python
logger.info(
    f"Enrichment complete: {session.total_cost_usd:.4f}",
    extra={
        "clearbit_cost": 0.10,
        "google_cost": 0.034,
        "openrouter_cost": 0.001,
        "proxycurl_cost": 0.020
    }
)
```

### Monitor Rate Limits

```python
if source.circuit_breaker.state == "open":
    logger.warning(f"Circuit breaker open for {source.name}")
    # Alert on-call engineer
```

### Track Success Rates

```python
success_rate = successful_calls / total_calls
if success_rate < 0.8:
    logger.error(f"Low success rate: {success_rate:.2%}")
```

---

## Best Practices

### 1. Graceful Degradation

```python
# Always return partial data if some sources fail
layer2_results = await asyncio.gather(*tasks, return_exceptions=True)

for result in layer2_results:
    if isinstance(result, Exception):
        logger.warning(f"Source failed: {result}")
        continue  # Continue with other sources
```

### 2. Cache Aggressively

```python
# Cache for 30 days to reduce API costs
await cache.save_session(
    session_id=session_id,
    enrichment_data=session.dict(),
    ttl_days=30
)
```

### 3. Circuit Breakers

```python
# Automatically fail fast if source is down
source.circuit_breaker.failure_threshold = 5
source.circuit_breaker.timeout_duration = 60  # seconds
```

### 4. Parallel Execution

```python
# Execute all sources in parallel within each layer
layer1_tasks = [source1.enrich(), source2.enrich()]
results = await asyncio.gather(*layer1_tasks)
```

---

*Last Updated: January 2025*
*Version: 1.0.0*
