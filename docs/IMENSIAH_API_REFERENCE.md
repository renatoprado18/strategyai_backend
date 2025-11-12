# IMENSIAH API Reference

Complete API documentation for the IMENSIAH intelligent form enrichment system.

---

## Base URL

```
Production: https://api.imensiah.com
Development: http://localhost:8000
```

---

## Authentication

Currently, IMENSIAH form enrichment endpoints are **publicly accessible** (no authentication required for form filling).

Future versions may require API keys for programmatic access.

---

## Endpoints

### 1. Progressive Form Enrichment

#### POST /api/form/enrich

Start progressive 3-layer enrichment for a company website. Returns Server-Sent Events (SSE) stream with real-time updates.

**Request:**

```http
POST /api/form/enrich HTTP/1.1
Host: localhost:8000
Content-Type: application/json

{
  "website": "techstart.com",
  "email": "founder@techstart.com"
}
```

**Request Body Schema:**

```typescript
{
  website?: string,  // Company website URL (can also use "url")
  url?: string,      // Alias for "website"
  email: string      // User email (required)
}
```

**Field Validation:**

| Field | Required | Format | Example |
|-------|----------|--------|---------|
| `website` or `url` | Yes (one of) | Domain or full URL | `techstart.com` or `https://techstart.com` |
| `email` | Yes | Valid email | `user@company.com` |

**Notes:**
- Either `website` or `url` field must be provided (not both)
- URL is automatically normalized (adds `https://` if missing)
- Email must be valid format (`@` and `.` required)

---

**Response (SSE Stream):**

The response is a Server-Sent Events stream with the following event types:

#### Event 1: layer1_complete

Sent after Layer 1 enrichment completes (< 2s)

```
event: layer1_complete
data: {
  "status": "layer1_complete",
  "fields": {
    "name": "TechStart Innovations",
    "city": "São Paulo",
    "description": "B2B SaaS platform for enterprise automation",
    "logoUrl": "https://techstart.com/logo.png",
    "website": "https://techstart.com"
  },
  "duration_ms": 1850,
  "sources": ["metadata", "ip_api"]
}
```

**Fields Object:**
- Contains auto-filled form fields
- Uses frontend field names (camelCase)
- Only includes fields with values

#### Event 2: layer2_complete

Sent after Layer 2 enrichment completes (3-6s)

```
event: layer2_complete
data: {
  "status": "layer2_complete",
  "fields": {
    "name": "TechStart Innovations",
    "legalName": "TechStart Innovations LTDA",
    "city": "São Paulo",
    "state": "SP",
    "country": "BR",
    "employeeCount": "25-50",
    "industry": "Technology / SaaS",
    "phone": "+55 11 1234-5678",
    "cnpj": "12.345.678/0001-99",
    "rating": 4.7
  },
  "duration_ms": 4200,
  "sources": ["clearbit", "receita_ws", "google_places"]
}
```

**Note:** Includes all fields from Layer 1 + new Layer 2 fields

#### Event 3: layer3_complete

Sent after Layer 3 enrichment completes (6-10s)

```
event: layer3_complete
data: {
  "status": "layer3_complete",
  "fields": {
    "name": "TechStart Innovations",
    "legalName": "TechStart Innovations LTDA",
    "city": "São Paulo",
    "industry": "Technology / SaaS",
    "companySize": "Small",
    "digitalMaturity": "High",
    "targetAudience": "B2B Enterprise",
    "keyDifferentiators": "AI-powered automation, Real-time analytics"
  },
  "duration_ms": 8500,
  "sources": ["OpenRouter GPT-4o-mini", "Proxycurl"]
}
```

**AI-Inferred Fields:**
- `industry`: Industry classification
- `companySize`: Small/Medium/Large
- `digitalMaturity`: Low/Medium/High
- `targetAudience`: Who the company serves
- `keyDifferentiators`: Unique selling points

#### Event 4: complete

Final event when all enrichment is done

```
event: complete
data: {
  "status": "complete",
  "session_id": "abc-123-def-456-ghi-789",
  "total_duration_ms": 8500,
  "total_cost_usd": 0.12,
  "message": "Form enrichment complete. Use session_id for Phase 2 submission."
}
```

**Important:** Save the `session_id` for Phase 2 (strategic analysis submission)

#### Event: error

Sent if enrichment fails

```
event: error
data: {
  "status": "error",
  "error": "validation_error",
  "message": "Invalid website URL",
  "details": "Domain not found: invalid-domain.xyz"
}
```

**Error Types:**
- `validation_error`: Invalid input (email, URL)
- `internal_error`: Server-side failure
- `timeout_error`: Enrichment took too long
- `rate_limit_error`: Too many requests

---

**Response Headers:**

```http
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

---

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success - SSE stream started |
| 400 | Bad Request - Invalid input |
| 422 | Unprocessable Content - Validation error |
| 500 | Internal Server Error |

---

**cURL Example:**

```bash
curl -N -X POST http://localhost:8000/api/form/enrich \
  -H "Content-Type: application/json" \
  -d '{
    "website": "techstart.com",
    "email": "founder@techstart.com"
  }'
```

**JavaScript Example:**

```javascript
const eventSource = new EventSource('/api/form/enrich', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    website: 'techstart.com',
    email: 'founder@techstart.com'
  })
});

eventSource.addEventListener('layer1_complete', (e) => {
  const data = JSON.parse(e.data);
  console.log('Layer 1:', data.fields);
  updateFormFields(data.fields);
});

eventSource.addEventListener('layer2_complete', (e) => {
  const data = JSON.parse(e.data);
  console.log('Layer 2:', data.fields);
  updateFormFields(data.fields);
});

eventSource.addEventListener('layer3_complete', (e) => {
  const data = JSON.parse(e.data);
  console.log('Layer 3:', data.fields);
  updateFormFields(data.fields);
});

eventSource.addEventListener('complete', (e) => {
  const data = JSON.parse(e.data);
  console.log('Complete! Session ID:', data.session_id);
  localStorage.setItem('sessionId', data.session_id);
  eventSource.close();
});

eventSource.addEventListener('error', (e) => {
  const data = JSON.parse(e.data);
  console.error('Error:', data.message);
  eventSource.close();
});
```

**Python Example:**

```python
import requests
import json

url = "http://localhost:8000/api/form/enrich"
data = {
    "website": "techstart.com",
    "email": "founder@techstart.com"
}

response = requests.post(url, json=data, stream=True)

for line in response.iter_lines():
    if line:
        decoded_line = line.decode('utf-8')
        if decoded_line.startswith('data:'):
            event_data = json.loads(decoded_line[5:])
            print(f"Status: {event_data['status']}")
            if event_data['status'] == 'complete':
                print(f"Session ID: {event_data['session_id']}")
                break
```

---

### 2. Get Cached Session

#### GET /api/form/session/{session_id}

Retrieve cached enrichment session for reuse in strategic analysis (Phase 2).

**Request:**

```http
GET /api/form/session/abc-123-def-456-ghi-789 HTTP/1.1
Host: localhost:8000
```

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | UUID from enrichment complete event |

---

**Response (Success):**

```json
{
  "session_id": "abc-123-def-456-ghi-789",
  "website_url": "https://techstart.com",
  "user_email": "founder@techstart.com",
  "enrichment_data": {
    "session_id": "abc-123-def-456-ghi-789",
    "website_url": "https://techstart.com",
    "user_email": "founder@techstart.com",
    "layer1_result": {
      "layer_number": 1,
      "completed_at": "2025-01-09T14:23:47Z",
      "duration_ms": 1850,
      "fields_populated": ["company_name", "description", "city"],
      "data": {
        "company_name": "TechStart Innovations",
        "description": "B2B SaaS platform",
        "city": "São Paulo"
      },
      "sources_called": ["metadata", "ip_api"],
      "cost_usd": 0.0,
      "confidence_avg": 70.0
    },
    "layer2_result": {
      "layer_number": 2,
      "completed_at": "2025-01-09T14:23:51Z",
      "duration_ms": 4200,
      "fields_populated": ["employee_count", "annual_revenue", "industry"],
      "data": {
        "employee_count": "25-50",
        "annual_revenue": "R$ 5-10M",
        "industry": "Technology"
      },
      "sources_called": ["clearbit", "receita_ws", "google_places"],
      "cost_usd": 0.12,
      "confidence_avg": 85.0
    },
    "layer3_result": {
      "layer_number": 3,
      "completed_at": "2025-01-09T14:23:55Z",
      "duration_ms": 8500,
      "fields_populated": ["ai_industry", "ai_company_size"],
      "data": {
        "ai_industry": "Technology / SaaS",
        "ai_company_size": "Small"
      },
      "sources_called": ["OpenRouter GPT-4o-mini"],
      "cost_usd": 0.001,
      "confidence_avg": 75.0
    },
    "total_duration_ms": 8500,
    "total_cost_usd": 0.121,
    "fields_auto_filled": {
      "company_name": "TechStart Innovations",
      "employee_count": "25-50",
      "industry": "Technology / SaaS"
    },
    "confidence_scores": {
      "company_name": 70.0,
      "employee_count": 85.0,
      "industry": 85.0
    },
    "status": "complete"
  },
  "created_at": "2025-01-09T14:23:45Z",
  "expires_at": "2025-02-08T14:23:45Z"
}
```

---

**Response (Not Found):**

```json
{
  "detail": "Session not found or expired. Please re-enrich."
}
```

---

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Success - Session found |
| 404 | Not Found - Session expired or invalid |
| 500 | Internal Server Error |

---

**cURL Example:**

```bash
curl http://localhost:8000/api/form/session/abc-123-def-456-ghi-789
```

**JavaScript Example:**

```javascript
const sessionId = localStorage.getItem('sessionId');

fetch(`/api/form/session/${sessionId}`)
  .then(response => {
    if (!response.ok) {
      throw new Error('Session not found');
    }
    return response.json();
  })
  .then(data => {
    console.log('Cached enrichment:', data.enrichment_data);
    // Use cached data for Phase 2 submission
  })
  .catch(error => {
    console.error('Failed to load session:', error);
    // Re-run enrichment
  });
```

**Python Example:**

```python
import requests

session_id = "abc-123-def-456-ghi-789"
url = f"http://localhost:8000/api/form/session/{session_id}"

response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    print(f"Enrichment data: {data['enrichment_data']}")
else:
    print(f"Session not found: {response.json()['detail']}")
```

---

### 3. Health Check

#### GET /api/form/health

Check if form enrichment service is operational.

**Request:**

```http
GET /api/form/health HTTP/1.1
Host: localhost:8000
```

---

**Response:**

```json
{
  "status": "healthy",
  "service": "form-enrichment",
  "active_sessions": 42,
  "timestamp": "2025-01-09T14:30:00Z"
}
```

**Fields:**
- `status`: "healthy" or "unhealthy"
- `service`: Service identifier
- `active_sessions`: Number of cached sessions in memory
- `timestamp`: Current server time

---

**Status Codes:**

| Code | Meaning |
|------|---------|
| 200 | Service is healthy |
| 503 | Service unavailable |

---

**cURL Example:**

```bash
curl http://localhost:8000/api/form/health
```

---

## Field Mapping

### Backend → Frontend Translation

The enrichment system returns fields with **backend names**, which are automatically translated to **frontend form field names**:

| Backend Field | Frontend Field | Description |
|---------------|----------------|-------------|
| `company_name` | `name` | Company display name |
| `description` | `description` | Company description |
| `website` | `website` | Website URL |
| `city` | `city` | City name |
| `region` | `state` | State/region |
| `country_name` | `country` | Country name |
| `ip_location` | `location` | Location string |
| `phone` | `phone` | Phone number |
| `email` | `email` | Company email |
| `employee_count` | `employeeCount` | Employee range |
| `annual_revenue` | `annualRevenue` | Revenue estimate |
| `founded_year` | `foundedYear` | Year founded |
| `legal_name` | `legalName` | Legal entity name |
| `ai_industry` | `industry` | Industry (AI) |
| `ai_company_size` | `companySize` | Size (AI) |
| `ai_digital_maturity` | `digitalMaturity` | Maturity (AI) |
| `ai_target_audience` | `targetAudience` | Audience (AI) |
| `ai_key_differentiators` | `keyDifferentiators` | Differentiators (AI) |
| `logo_url` | `logoUrl` | Logo image URL |
| `meta_description` | `metaDescription` | Meta description |
| `cnpj` | `cnpj` | Brazilian CNPJ |
| `rating` | `rating` | Google rating |
| `reviews_count` | `reviewsCount` | Review count |

---

## Data Sources Attribution

Each enrichment layer calls specific data sources:

### Layer 1 (Free, < 2s)

| Source | Cost | What It Provides |
|--------|------|------------------|
| **Metadata** | $0.00 | Company name, description, logo, technologies |
| **IP-API** | $0.00 | Approximate location, timezone |

### Layer 2 (Paid, 3-6s)

| Source | Cost | What It Provides |
|--------|------|------------------|
| **Clearbit** | ~$0.10 | Employee count, revenue, industry, legal name |
| **ReceitaWS** | $0.00 | Brazilian CNPJ, legal status, registration |
| **Google Places** | ~$0.02 | Address, phone, rating, verified location |

### Layer 3 (AI, 6-10s)

| Source | Cost | What It Provides |
|--------|------|------------------|
| **OpenRouter** | ~$0.001 | Industry, size, maturity, audience, differentiators |
| **Proxycurl** | ~$0.02 | LinkedIn followers, description, specialties |

**Total Cost per Enrichment:** ~$0.01 - $0.15 (average $0.05)

---

## Error Handling

### Error Response Format

All errors follow this format:

```json
{
  "status": "error",
  "error": "error_type",
  "message": "Human-readable error message",
  "details": "Additional error context (optional)"
}
```

### Common Errors

#### 422 Unprocessable Content

**Cause:** Invalid input data

```json
{
  "detail": [
    {
      "loc": ["body", "email"],
      "msg": "Invalid email address",
      "type": "value_error"
    }
  ]
}
```

**Solution:** Fix validation errors and retry

---

#### 400 Bad Request

**Cause:** Malformed request

```json
{
  "detail": "Invalid website URL"
}
```

**Solution:** Check URL format and retry

---

#### 404 Not Found

**Cause:** Session not found or expired

```json
{
  "detail": "Session not found or expired. Please re-enrich."
}
```

**Solution:** Run enrichment again to create new session

---

#### 500 Internal Server Error

**Cause:** Server-side failure

```json
{
  "status": "error",
  "error": "internal_error",
  "message": "Enrichment failed. Please try again.",
  "details": "Connection timeout"
}
```

**Solution:** Retry request or contact support

---

## Rate Limiting

Currently, IMENSIAH form enrichment has **no rate limits** for public use.

Future versions may implement:
- **10 requests per minute** per IP address
- **100 requests per hour** per IP address
- **1000 requests per day** per IP address

Rate limit headers will be added:
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1641234567
```

---

## Webhooks (Future)

Future versions will support webhooks for async enrichment completion:

```json
POST https://your-app.com/webhook/enrichment-complete
Content-Type: application/json

{
  "event": "enrichment.completed",
  "session_id": "abc-123",
  "timestamp": "2025-01-09T14:30:00Z",
  "data": {
    "website_url": "https://techstart.com",
    "status": "complete",
    "total_cost_usd": 0.12
  }
}
```

---

## OpenAPI Specification

Download the complete OpenAPI 3.0 specification:

```bash
curl http://localhost:8000/openapi.json > imensiah-api.json
```

Or view interactive docs:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

---

## SDKs and Libraries

### Official SDKs (Planned)

- **JavaScript/TypeScript**: `npm install @imensiah/client`
- **Python**: `pip install imensiah-client`
- **Go**: `go get github.com/imensiah/go-client`

### Community Libraries

Submit your SDK to be listed here!

---

## Changelog

### Version 1.0.0 (January 2025)

**Initial Release:**
- Progressive 3-layer enrichment
- SSE streaming support
- Session caching (30 days)
- 6 data source integrations
- Field translation system
- Circuit breaker protection

---

## Support

**Documentation**: https://docs.imensiah.com
**API Status**: https://status.imensiah.com
**Email Support**: api@imensiah.com

---

*Last Updated: January 2025*
*Version: 1.0.0*
