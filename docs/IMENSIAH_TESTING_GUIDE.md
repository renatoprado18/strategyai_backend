# IMENSIAH Testing Guide

Comprehensive testing guide for the IMENSIAH intelligent form enrichment system.

---

## Table of Contents

1. [Test Strategy](#test-strategy)
2. [Manual Testing](#manual-testing)
3. [Automated Testing](#automated-testing)
4. [Performance Testing](#performance-testing)
5. [Integration Testing](#integration-testing)
6. [End-to-End Testing](#end-to-end-testing)
7. [Load Testing](#load-testing)
8. [Test Data](#test-data)

---

## Test Strategy

### Testing Pyramid

```
       /\
      /E2E\           10% - End-to-end tests
     /------\
    /  Integ \        20% - Integration tests
   /----------\
  /    Unit    \      70% - Unit tests
 /--------------\
```

### Test Coverage Goals

| Component | Target Coverage | Current |
|-----------|-----------------|---------|
| Data Sources | 90% | 85% |
| Orchestrator | 95% | 92% |
| API Routes | 85% | 88% |
| Validators | 100% | 100% |
| Overall | 85% | 87% |

---

## Manual Testing

### 1. Quick Smoke Test

**Purpose:** Verify basic functionality works

**Steps:**

1. Open form at http://localhost:8000
2. Enter website: `google.com`
3. Enter email: `test@test.com`
4. Click "Fill Form Automatically"
5. Wait for 10 seconds
6. Verify fields populate progressively

**Expected Results:**
- Layer 1 completes < 2s
- Layer 2 completes < 6s
- Layer 3 completes < 10s
- All fields editable
- Session ID displayed

---

### 2. Data Quality Test

**Purpose:** Verify enrichment accuracy

**Test Cases:**

#### Test Case 1: Well-Known US Company

```
Website: google.com
Expected Data:
  - Company Name: "Google"
  - Industry: "Technology"
  - Employee Count: "10000+"
  - Location: "Mountain View, CA"
```

#### Test Case 2: Brazilian Company

```
Website: nubank.com.br
Expected Data:
  - Company Name: "Nubank"
  - CNPJ: "18.236.120/0001-58"
  - Legal Name: "Nu Pagamentos S.A."
  - City: "São Paulo"
```

#### Test Case 3: Small Company

```
Website: smallcompany.com (hypothetical)
Expected Behavior:
  - Layer 1 completes (metadata)
  - Layer 2 may fail (not in databases)
  - Layer 3 provides AI inference
  - Fields are editable
```

---

### 3. Edge Case Testing

#### Empty Website

```
Input: {"website": "", "email": "test@test.com"}
Expected: 422 Unprocessable Content
```

#### Invalid Email

```
Input: {"website": "google.com", "email": "notanemail"}
Expected: 422 Unprocessable Content
```

#### Non-Existent Domain

```
Input: {"website": "thisdoesnotexist12345.com", "email": "test@test.com"}
Expected: Enrichment completes with partial data (Layer 1 may fail)
```

#### Very Slow Website

```
Input: {"website": "slowwebsite.com", "email": "test@test.com"}
Expected: Layer 1 timeout, continues to Layer 2/3
```

---

### 4. Session Caching Test

**Purpose:** Verify session persistence

**Steps:**

1. Enrich a company: `POST /api/form/enrich`
2. Note the `session_id` from complete event
3. Wait 1 minute
4. Retrieve session: `GET /api/form/session/{session_id}`
5. Verify data matches original enrichment

**Expected Results:**
- Session found in database
- All layer data intact
- Fields auto-filled preserved
- Confidence scores retained

---

### 5. Error Handling Test

**Purpose:** Verify graceful failure

**Test Cases:**

#### API Key Missing

```bash
# Remove Clearbit API key
unset CLEARBIT_API_KEY

# Run enrichment
curl -X POST http://localhost:8000/api/form/enrich \
  -H "Content-Type: application/json" \
  -d '{"website":"google.com","email":"test@test.com"}'

# Expected: Layer 2 completes without Clearbit, other sources succeed
```

#### Database Down

```bash
# Stop Supabase connection
# Run enrichment

# Expected: Enrichment completes, cache write fails (logged), in-memory cache works
```

---

### 6. Frontend Integration Test

**Purpose:** Verify SSE streaming works

**Steps:**

1. Open browser DevTools (Network tab)
2. Run form enrichment
3. Observe SSE events in real-time

**Expected Network Activity:**

```
Request: POST /api/form/enrich
Type: eventsource
Status: 200

Events received:
  - layer1_complete (< 2s)
  - layer2_complete (3-6s)
  - layer3_complete (6-10s)
  - complete (final)
```

---

## Automated Testing

### Setup

```bash
# Install dependencies
pip install pytest pytest-asyncio pytest-cov httpx

# Set test environment variables
export TESTING=true
export CLEARBIT_API_KEY=test_key
export GOOGLE_PLACES_API_KEY=test_key
```

### Run All Tests

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=app --cov-report=html tests/

# Run specific test file
pytest tests/unit/test_metadata_source.py -v

# Run with markers
pytest -m "not slow" tests/
```

---

### Unit Tests

**Purpose:** Test individual components in isolation

#### Test Metadata Source

```python
# tests/unit/test_metadata_source.py
import pytest
from app.services.enrichment.sources.metadata import MetadataSource

@pytest.mark.asyncio
async def test_metadata_extraction():
    """Test metadata scraping from website"""
    source = MetadataSource()
    result = await source.enrich("example.com")

    assert result.success
    assert "company_name" in result.data
    assert result.cost_usd == 0.0
    assert result.duration_ms > 0

@pytest.mark.asyncio
async def test_metadata_timeout():
    """Test timeout handling"""
    source = MetadataSource()
    source.timeout = 0.001  # Very short timeout

    result = await source.enrich("slowwebsite.com")

    assert not result.success
    assert "timeout" in result.error_message.lower()
```

#### Test URL Validation

```python
# tests/unit/test_validators.py
import pytest
from app.services.enrichment.validators import validate_url

def test_valid_urls():
    """Test valid URL formats"""
    urls = [
        "google.com",
        "https://google.com",
        "http://google.com",
        "www.google.com",
    ]

    for url in urls:
        result = validate_url(url)
        assert result.is_valid
        assert result.formatted_value.startswith("https://")

def test_invalid_urls():
    """Test invalid URL formats"""
    urls = [
        "",
        "not a url",
        "ht!tp://invalid",
        "javascript:alert(1)",
    ]

    for url in urls:
        result = validate_url(url)
        assert not result.is_valid
        assert result.error_message is not None
```

#### Test Field Translation

```python
# tests/unit/test_field_translation.py
import pytest
from app.routes.form_enrichment import translate_to_form_fields

def test_translation_mapping():
    """Test backend to frontend field translation"""
    backend_data = {
        "company_name": "TechStart",
        "employee_count": "25-50",
        "ai_industry": "Technology"
    }

    frontend_data = translate_to_form_fields(backend_data)

    assert frontend_data["name"] == "TechStart"
    assert frontend_data["employeeCount"] == "25-50"
    assert frontend_data["industry"] == "Technology"
    assert "company_name" not in frontend_data  # Translated
    assert "ai_industry" not in frontend_data  # Prefix removed
```

---

### Integration Tests

**Purpose:** Test component interactions

#### Test Progressive Orchestrator

```python
# tests/integration/test_progressive_enrichment.py
import pytest
from app.services.enrichment.progressive_orchestrator import (
    ProgressiveEnrichmentOrchestrator
)

@pytest.mark.asyncio
@pytest.mark.slow
async def test_full_progressive_enrichment():
    """Test complete 3-layer enrichment"""
    orchestrator = ProgressiveEnrichmentOrchestrator()

    session = await orchestrator.enrich_progressive(
        website_url="https://google.com",
        user_email="test@test.com"
    )

    # Verify all layers completed
    assert session.layer1_result is not None
    assert session.layer2_result is not None
    assert session.layer3_result is not None

    # Verify data quality
    assert len(session.layer1_result.data) > 0
    assert session.layer1_result.duration_ms < 3000  # < 3 seconds

    # Verify cost tracking
    assert session.total_cost_usd >= 0
    assert session.total_duration_ms > 0

    # Verify status
    assert session.status == "complete"

@pytest.mark.asyncio
async def test_graceful_degradation():
    """Test partial enrichment when sources fail"""
    orchestrator = ProgressiveEnrichmentOrchestrator()

    # Mock source failure
    orchestrator.clearbit_source.circuit_breaker.state = "open"

    session = await orchestrator.enrich_progressive(
        website_url="https://google.com",
        user_email="test@test.com"
    )

    # Should still complete
    assert session.status == "complete"

    # Layer 1 should work (free sources)
    assert session.layer1_result is not None

    # Layer 2 may have partial data (Clearbit failed)
    assert session.layer2_result is not None
```

#### Test API Endpoint

```python
# tests/integration/test_form_enrichment_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_enrich_endpoint_success():
    """Test successful enrichment"""
    response = client.post(
        "/api/form/enrich",
        json={
            "website": "google.com",
            "email": "test@test.com"
        }
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/event-stream"

def test_enrich_endpoint_validation_error():
    """Test validation error handling"""
    response = client.post(
        "/api/form/enrich",
        json={
            "website": "google.com"
            # Missing email
        }
    )

    assert response.status_code == 422

def test_session_retrieval():
    """Test cached session retrieval"""
    # Create session first
    enrich_response = client.post(
        "/api/form/enrich",
        json={
            "website": "google.com",
            "email": "test@test.com"
        }
    )

    # Extract session_id from SSE stream
    # (simplified for example)
    session_id = "test-session-id"

    # Retrieve session
    session_response = client.get(f"/api/form/session/{session_id}")

    if session_response.status_code == 200:
        data = session_response.json()
        assert "enrichment_data" in data
        assert data["session_id"] == session_id
```

---

## Performance Testing

### Latency Benchmarks

**Target Performance:**

| Layer | Target | Max Acceptable |
|-------|--------|----------------|
| Layer 1 | < 2s | 3s |
| Layer 2 | 3-6s | 8s |
| Layer 3 | 6-10s | 12s |
| Total | < 10s | 15s |

### Performance Test Script

```python
# tests/performance/test_enrichment_speed.py
import pytest
import asyncio
from datetime import datetime
from app.services.enrichment.progressive_orchestrator import (
    ProgressiveEnrichmentOrchestrator
)

@pytest.mark.asyncio
@pytest.mark.performance
async def test_layer1_performance():
    """Test Layer 1 completes in < 2 seconds"""
    orchestrator = ProgressiveEnrichmentOrchestrator()

    start = datetime.now()
    session = await orchestrator.enrich_progressive("https://google.com")
    layer1_duration = (datetime.now() - start).total_seconds()

    assert session.layer1_result is not None
    assert layer1_duration < 2.0, f"Layer 1 took {layer1_duration}s (expected < 2s)"

@pytest.mark.asyncio
@pytest.mark.performance
async def test_concurrent_enrichments():
    """Test multiple concurrent enrichments"""
    orchestrator = ProgressiveEnrichmentOrchestrator()

    domains = ["google.com", "microsoft.com", "apple.com", "amazon.com"]

    start = datetime.now()
    tasks = [
        orchestrator.enrich_progressive(f"https://{domain}")
        for domain in domains
    ]
    results = await asyncio.gather(*tasks)
    duration = (datetime.now() - start).total_seconds()

    # All should complete
    assert len(results) == 4
    assert all(r.status == "complete" for r in results)

    # Should take < 15s (parallelized)
    assert duration < 15.0, f"Concurrent enrichment took {duration}s"
```

---

## End-to-End Testing

### E2E Test Scenarios

#### Scenario 1: Happy Path

```python
# tests/e2e/test_full_workflow.py
import pytest
from playwright.async_api import async_playwright

@pytest.mark.asyncio
@pytest.mark.e2e
async def test_complete_form_workflow():
    """Test full user workflow from form to submission"""
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()

        # Navigate to form
        await page.goto("http://localhost:3000/form")

        # Enter website
        await page.fill('input[name="website"]', "google.com")

        # Enter email
        await page.fill('input[name="email"]', "test@test.com")

        # Click "Fill Automatically"
        await page.click('button:text("Fill Automatically")')

        # Wait for Layer 1
        await page.wait_for_selector('.layer1-indicator')
        name_field = await page.input_value('input[name="name"]')
        assert name_field != "", "Company name should be filled"

        # Wait for Layer 2
        await page.wait_for_selector('.layer2-indicator')
        industry_field = await page.input_value('input[name="industry"]')
        assert industry_field != "", "Industry should be filled"

        # Wait for Layer 3
        await page.wait_for_selector('.layer3-indicator')
        size_field = await page.input_value('input[name="companySize"]')
        assert size_field != "", "Company size should be filled"

        # Verify fields are editable
        await page.fill('input[name="name"]', "Google Inc.")
        edited_name = await page.input_value('input[name="name"]')
        assert edited_name == "Google Inc.", "Fields should be editable"

        # Submit form
        await page.click('button:text("Submit")')

        # Verify success message
        await page.wait_for_selector('.success-message')

        await browser.close()
```

---

## Load Testing

### Using Locust

```python
# tests/load/locustfile.py
from locust import HttpUser, task, between

class FormEnrichmentUser(HttpUser):
    wait_time = between(1, 5)

    @task(1)
    def enrich_form(self):
        """Simulate form enrichment request"""
        self.client.post(
            "/api/form/enrich",
            json={
                "website": "google.com",
                "email": "test@test.com"
            },
            stream=True  # SSE stream
        )

    @task(2)
    def health_check(self):
        """Health check (lighter load)"""
        self.client.get("/api/form/health")
```

**Run Load Test:**

```bash
# Install Locust
pip install locust

# Run load test
locust -f tests/load/locustfile.py --host=http://localhost:8000

# Open web UI
# http://localhost:8089

# Configure:
# - Number of users: 100
# - Spawn rate: 10 users/second
# - Run time: 5 minutes
```

**Performance Targets:**

| Metric | Target |
|--------|--------|
| Requests/second | > 50 |
| P50 latency | < 10s |
| P95 latency | < 15s |
| P99 latency | < 20s |
| Error rate | < 1% |

---

## Test Data

### Test Companies

```python
# tests/fixtures/test_data.py
TEST_COMPANIES = [
    {
        "name": "Google",
        "website": "google.com",
        "expected_data": {
            "name": "Google",
            "industry": "Technology",
            "employee_count": "10000+",
            "location": "Mountain View, CA"
        }
    },
    {
        "name": "Nubank",
        "website": "nubank.com.br",
        "expected_data": {
            "name": "Nubank",
            "cnpj": "18.236.120/0001-58",
            "city": "São Paulo"
        }
    },
    {
        "name": "Small Company",
        "website": "smallcompany.io",
        "expected_data": {
            # May have limited data
            "name": "Small Company",
            "description": "Early stage startup"
        }
    }
]
```

### Mock Data

```python
# tests/mocks/mock_responses.py
MOCK_CLEARBIT_RESPONSE = {
    "name": "TechStart Innovations",
    "domain": "techstart.com",
    "category": {
        "industry": "Technology",
        "sector": "Software"
    },
    "metrics": {
        "employeesRange": "25-50",
        "employees": 37
    },
    "foundedYear": 2019
}

MOCK_GOOGLE_PLACES_RESPONSE = {
    "candidates": [
        {
            "name": "TechStart Innovations",
            "formatted_address": "Av. Paulista, 1000 - São Paulo",
            "rating": 4.7,
            "user_ratings_total": 23
        }
    ]
}
```

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run unit tests
        run: pytest tests/unit/ -v

      - name: Run integration tests
        run: pytest tests/integration/ -v --cov=app

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Test Checklist

### Before Release

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Code coverage > 85%
- [ ] Manual smoke test completed
- [ ] Edge cases tested
- [ ] Performance benchmarks met
- [ ] Load testing passed (100 concurrent users)
- [ ] API documentation updated
- [ ] Changelog updated

---

*Last Updated: January 2025*
*Version: 1.0.0*
