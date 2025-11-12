# IMENSIAH Troubleshooting Guide

Common issues and solutions for the IMENSIAH intelligent form enrichment system.

---

## Table of Contents

1. [API Errors](#api-errors)
2. [Enrichment Issues](#enrichment-issues)
3. [Data Quality Problems](#data-quality-problems)
4. [Performance Issues](#performance-issues)
5. [Caching Problems](#caching-problems)
6. [Source-Specific Issues](#source-specific-issues)
7. [Deployment Issues](#deployment-issues)
8. [Debugging Tools](#debugging-tools)

---

## API Errors

### 422 Unprocessable Content

**Symptom:** HTTP 422 error when calling `/api/form/enrich`

**Error Message:**
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

**Common Causes:**

1. **Missing Email Field**
   ```json
   // Bad
   {"website": "company.com"}

   // Good
   {"website": "company.com", "email": "user@company.com"}
   ```

2. **Invalid URL Format**
   ```json
   // Bad
   {"website": "ht!tp://invalid", "email": "user@company.com"}

   // Good
   {"website": "company.com", "email": "user@company.com"}
   ```

3. **Invalid Email**
   ```json
   // Bad
   {"website": "company.com", "email": "notanemail"}

   // Good
   {"website": "company.com", "email": "user@company.com"}
   ```

4. **Missing Required Fields**
   ```json
   // Bad (missing both website and url)
   {"email": "user@company.com"}

   // Good (at least one URL field)
   {"website": "company.com", "email": "user@company.com"}
   ```

**Solutions:**

1. **Ensure email field is filled:**
   ```javascript
   if (!formData.email) {
     throw new Error("Email is required");
   }
   ```

2. **Validate URL before submission:**
   ```javascript
   function validateURL(url) {
     try {
       new URL(url.startsWith('http') ? url : `https://${url}`);
       return true;
     } catch {
       return false;
     }
   }
   ```

3. **Check frontend validation:**
   ```javascript
   if (!email.includes('@') || !email.includes('.')) {
     throw new Error("Invalid email format");
   }
   ```

---

### 400 Bad Request

**Symptom:** HTTP 400 error with generic message

**Error Message:**
```json
{
  "detail": "Invalid website URL"
}
```

**Common Causes:**

1. Malformed URL with special characters
2. URL with spaces or invalid characters
3. Non-existent domain

**Solutions:**

1. **Sanitize URL input:**
   ```python
   # Backend
   url = url.strip().lower()
   url = url.replace(" ", "")
   if not url.startswith(('http://', 'https://')):
       url = f"https://{url}"
   ```

2. **Frontend validation:**
   ```javascript
   function sanitizeURL(url) {
     return url.trim().toLowerCase().replace(/\s/g, '');
   }
   ```

---

### 404 Not Found - Session

**Symptom:** Cannot load cached session

**Error Message:**
```json
{
  "detail": "Session not found or expired. Please re-enrich."
}
```

**Common Causes:**

1. **Session expired** (> 30 days old)
2. **Invalid session ID**
3. **Session not saved** (cache write failed)
4. **Database connection issue**

**Solutions:**

1. **Check session ID validity:**
   ```javascript
   if (!sessionId || sessionId.length < 10) {
     console.error("Invalid session ID");
     // Re-run enrichment
   }
   ```

2. **Handle expiration gracefully:**
   ```javascript
   fetch(`/api/form/session/${sessionId}`)
     .then(response => {
       if (response.status === 404) {
         console.warn("Session expired, re-enriching...");
         return runEnrichment();
       }
       return response.json();
     });
   ```

3. **Check database logs:**
   ```bash
   grep "Session not found" logs/*.log
   ```

---

### 500 Internal Server Error

**Symptom:** Server crashes during enrichment

**Error Message:**
```json
{
  "detail": "Internal server error"
}
```

**Common Causes:**

1. Database connection lost
2. API key invalid/expired
3. Timeout in data source
4. Memory exhaustion

**Solutions:**

1. **Check logs:**
   ```bash
   tail -f logs/app.log | grep ERROR
   ```

2. **Verify API keys:**
   ```bash
   echo $CLEARBIT_API_KEY
   echo $GOOGLE_PLACES_API_KEY
   # Should not be empty
   ```

3. **Check database connection:**
   ```python
   # Test Supabase connection
   from app.core.supabase import supabase_service
   result = supabase_service.table("enrichment_sessions").select("*").limit(1).execute()
   print(result.data)  # Should not error
   ```

4. **Monitor memory usage:**
   ```bash
   ps aux | grep uvicorn
   # Check memory percentage
   ```

---

## Enrichment Issues

### Enrichment Times Out

**Symptom:** Enrichment never completes, no events received

**Common Causes:**

1. **Slow website response** (Layer 1 timeout)
2. **API rate limits hit** (Layer 2/3)
3. **Network connectivity issues**
4. **Circuit breaker open**

**Solutions:**

1. **Increase timeout:**
   ```python
   # app/core/config.py
   class Settings:
       enrichment_timeout_seconds: int = 30  # Increase from 15
   ```

2. **Check circuit breaker state:**
   ```python
   from app.services.enrichment.sources.clearbit import ClearbitSource

   source = ClearbitSource()
   print(source.circuit_breaker.state)  # "open", "half-open", or "closed"
   ```

3. **Monitor logs:**
   ```bash
   grep "timeout" logs/app.log
   grep "Circuit breaker" logs/app.log
   ```

4. **Fallback to manual entry:**
   ```javascript
   setTimeout(() => {
     if (!enrichmentComplete) {
       console.warn("Enrichment timeout, allowing manual entry");
       enableManualEntry();
     }
   }, 15000);  // 15 second timeout
   ```

---

### SSE Stream Not Connecting

**Symptom:** Frontend doesn't receive events, connection fails

**Common Causes:**

1. **CORS configuration** (cross-origin request blocked)
2. **Nginx buffering** (events not streamed)
3. **Firewall blocking SSE**
4. **Browser compatibility**

**Solutions:**

1. **Check CORS configuration:**
   ```python
   # app/main.py
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["*"],  # Or specific origins
       allow_credentials=True,
       allow_methods=["*"],
       allow_headers=["*"],
   )
   ```

2. **Disable nginx buffering:**
   ```nginx
   # nginx.conf
   location /api/form/enrich {
       proxy_pass http://backend;
       proxy_buffering off;
       proxy_cache off;
       proxy_set_header Connection '';
       proxy_http_version 1.1;
       chunked_transfer_encoding off;
   }
   ```

3. **Add SSE headers:**
   ```python
   return StreamingResponse(
       event_stream(),
       media_type="text/event-stream",
       headers={
           "Cache-Control": "no-cache",
           "Connection": "keep-alive",
           "X-Accel-Buffering": "no",  # Critical!
       }
   )
   ```

4. **Test with cURL:**
   ```bash
   curl -N -X POST http://localhost:8000/api/form/enrich \
     -H "Content-Type: application/json" \
     -d '{"website":"google.com","email":"test@test.com"}'
   ```

---

### Some Layers Don't Complete

**Symptom:** Only Layer 1 completes, Layer 2/3 missing

**Common Causes:**

1. **API key not configured**
2. **Source failing silently**
3. **Circuit breaker open**
4. **Cost limits exceeded**

**Solutions:**

1. **Check API key configuration:**
   ```bash
   # .env file
   CLEARBIT_API_KEY=sk_xxxxxxxxxxxx
   GOOGLE_PLACES_API_KEY=AIzaxxxxxxxxxxxx
   OPENROUTER_API_KEY=sk-or-xxxxxxxxxxxx
   PROXYCURL_API_KEY=xxxxxxxxxxxx
   ```

2. **Check logs for failures:**
   ```bash
   grep "Layer 2" logs/app.log
   grep "Clearbit" logs/app.log
   grep "failed" logs/app.log
   ```

3. **Test sources individually:**
   ```python
   # tests/integration/test_sources.py
   pytest tests/integration/test_clearbit.py -v
   ```

4. **Verify graceful degradation:**
   ```python
   # Should still return partial data
   assert session.layer1_result is not None
   # Layer 2/3 may be None if sources failed
   ```

---

## Data Quality Problems

### Empty Fields

**Symptom:** Form fields remain empty after enrichment

**Common Causes:**

1. **Company not found** in data sources
2. **Website has no metadata**
3. **Translation mapping missing**
4. **Field name mismatch**

**Solutions:**

1. **Check source data:**
   ```bash
   grep "fields_populated" logs/app.log
   # Should show which fields were populated
   ```

2. **Verify translation map:**
   ```python
   # app/routes/form_enrichment.py
   translation_map = {
       "company_name": "name",
       "description": "description",
       # ... ensure all mappings exist
   }
   ```

3. **Test with well-known company:**
   ```bash
   curl -N -X POST http://localhost:8000/api/form/enrich \
     -H "Content-Type: application/json" \
     -d '{"website":"google.com","email":"test@test.com"}'
   # Google should have rich data
   ```

4. **Enable manual entry:**
   ```javascript
   // Always allow user to override empty fields
   formFields.forEach(field => {
     field.disabled = false;  // Keep editable
   });
   ```

---

### Incorrect Data

**Symptom:** Auto-filled data is wrong

**Common Causes:**

1. **AI hallucination** (Layer 3)
2. **Wrong company matched** (similar name)
3. **Outdated data** in API
4. **IP location mismatch** (hosting provider)

**Solutions:**

1. **Check confidence scores:**
   ```javascript
   if (confidenceScore < 70) {
     // Mark field as low confidence
     field.classList.add('low-confidence');
     field.placeholder = "Verify this field";
   }
   ```

2. **Always make fields editable:**
   ```javascript
   // NEVER disable fields - let user override
   formFields.forEach(field => {
     field.readOnly = false;
   });
   ```

3. **Track user edits:**
   ```python
   # Log when users edit AI-suggested fields
   logger.info(
       f"User edited field {field_name}",
       extra={
           "original_value": ai_value,
           "corrected_value": user_value,
           "confidence": confidence_score
       }
   )
   ```

4. **Improve AI prompts:**
   ```python
   # Add more context to AI extraction
   prompt = f"""
   Analyze this company carefully:
   Website: {url}
   Metadata: {metadata}
   User Description: {description}

   Be accurate and conservative. If unsure, return null.
   """
   ```

---

### Field Name Mismatch

**Symptom:** Backend returns data but frontend doesn't display it

**Common Causes:**

1. **Translation map incomplete**
2. **Frontend expects different field name**
3. **CamelCase vs snake_case mismatch**

**Solutions:**

1. **Check translation map:**
   ```python
   # app/routes/form_enrichment.py
   translation_map = {
       # Backend → Frontend
       "employee_count": "employeeCount",  # ← Ensure this exists
       "annual_revenue": "annualRevenue",
       # ... add missing mappings
   }
   ```

2. **Log translated fields:**
   ```python
   logger.info(f"Translated fields: {form_data.keys()}")
   ```

3. **Frontend debugging:**
   ```javascript
   eventSource.addEventListener('layer1_complete', (e) => {
     const data = JSON.parse(e.data);
     console.log("Received fields:", Object.keys(data.fields));
     console.log("Form expects:", expectedFields);
   });
   ```

---

## Performance Issues

### Slow Enrichment (> 15 seconds)

**Symptom:** Enrichment takes longer than expected

**Common Causes:**

1. **Sequential execution** (not parallel)
2. **Slow website response**
3. **API rate limiting**
4. **Network latency**

**Solutions:**

1. **Verify parallel execution:**
   ```python
   # app/services/enrichment/progressive_orchestrator.py

   # Good: Parallel
   layer1_tasks = [source1.enrich(), source2.enrich()]
   results = await asyncio.gather(*layer1_tasks)

   # Bad: Sequential
   result1 = await source1.enrich()
   result2 = await source2.enrich()
   ```

2. **Check layer timings:**
   ```bash
   grep "duration_ms" logs/app.log
   # Layer 1 should be < 2000ms
   # Layer 2 should be < 6000ms
   # Layer 3 should be < 10000ms
   ```

3. **Monitor source latency:**
   ```python
   logger.info(
       f"Source {source_name} completed",
       extra={"duration_ms": duration}
   )
   ```

4. **Add timeout guards:**
   ```python
   async with asyncio.timeout(5):  # 5 second max per source
       result = await source.enrich(domain)
   ```

---

### High Memory Usage

**Symptom:** Server memory grows over time

**Common Causes:**

1. **In-memory session cache grows unbounded**
2. **HTTP connection pooling leaks**
3. **Large HTML pages cached**

**Solutions:**

1. **Limit in-memory cache size:**
   ```python
   # app/routes/form_enrichment.py

   # Add TTL to in-memory cache
   MAX_MEMORY_SESSIONS = 1000

   if len(active_enrichment_sessions) > MAX_MEMORY_SESSIONS:
       # Remove oldest sessions
       oldest_key = min(active_enrichment_sessions.keys())
       del active_enrichment_sessions[oldest_key]
   ```

2. **Close HTTP connections:**
   ```python
   async with httpx.AsyncClient() as client:
       response = await client.get(url)
       # Client auto-closes on exit
   ```

3. **Monitor memory:**
   ```bash
   # Add to monitoring
   ps aux | grep uvicorn | awk '{print $6}'  # Memory in KB
   ```

---

## Caching Problems

### Cache Miss (Session Not Found)

**Symptom:** `GET /api/form/session/{id}` returns 404

**Common Causes:**

1. **Session expired** (> 30 days)
2. **Cache write failed**
3. **Database connection lost**
4. **Session ID typo**

**Solutions:**

1. **Check session creation:**
   ```bash
   grep "Cached progressive enrichment session" logs/app.log
   ```

2. **Verify database write:**
   ```python
   # Test cache write
   from app.services.enrichment.form_enrichment_cache import FormEnrichmentCache

   cache = FormEnrichmentCache()
   await cache.save_session(
       session_id="test-123",
       website_url="https://test.com",
       user_email="test@test.com",
       enrichment_data={}
   )
   # Should not error
   ```

3. **Check Supabase:**
   ```sql
   -- Query Supabase directly
   SELECT * FROM enrichment_sessions
   WHERE session_id = 'abc-123'
   LIMIT 1;
   ```

4. **Fallback to re-enrichment:**
   ```javascript
   if (response.status === 404) {
     console.warn("Cache miss, re-enriching...");
     await startEnrichment(website, email);
   }
   ```

---

### Stale Cache Data

**Symptom:** Old data returned from cache

**Common Causes:**

1. **TTL too long** (30 days)
2. **Cache key collision**
3. **No cache invalidation**

**Solutions:**

1. **Manual cache invalidation:**
   ```python
   # Add endpoint to clear cache
   @router.delete("/session/{session_id}")
   async def delete_session(session_id: str):
       # Remove from memory
       active_enrichment_sessions.pop(session_id, None)

       # Remove from database
       await supabase_service.table("enrichment_sessions").delete().eq("session_id", session_id).execute()
   ```

2. **Shorten TTL:**
   ```python
   # app/core/config.py
   class Settings:
       enrichment_cache_ttl_days: int = 7  # Reduce from 30
   ```

3. **Add force-refresh option:**
   ```python
   @router.post("/enrich")
   async def enrich_form(
       request: FormEnrichmentRequest,
       force_refresh: bool = False
   ):
       if force_refresh:
           # Skip cache lookup
           session = await orchestrator.enrich_progressive(...)
   ```

---

## Source-Specific Issues

### Clearbit: 402 Payment Required

**Symptom:** Clearbit returns 402 status code

**Error:** "Credits exhausted - payment required"

**Solutions:**

1. **Check account credits:**
   - Login to https://dashboard.clearbit.com
   - Check remaining credits

2. **Upgrade plan or add credits:**
   - Purchase more credits
   - Upgrade to higher tier

3. **Disable Clearbit temporarily:**
   ```python
   # app/services/enrichment/progressive_orchestrator.py

   # Comment out Clearbit in Layer 2
   layer2_tasks = [
       # self.clearbit_source.enrich(domain),  # Disabled
       self.receita_ws_source.enrich(domain),
       self.google_places_source.enrich(domain)
   ]
   ```

---

### ReceitaWS: Rate Limited

**Symptom:** ReceitaWS returns 429 Too Many Requests

**Error:** "Rate limit exceeded"

**Solutions:**

1. **Add exponential backoff:**
   ```python
   async def enrich_with_retry(source, domain, max_retries=3):
       for attempt in range(max_retries):
           try:
               return await source.enrich(domain)
           except RateLimitError:
               wait_time = 2 ** attempt  # 1s, 2s, 4s
               await asyncio.sleep(wait_time)
       raise Exception("Max retries exceeded")
   ```

2. **Use paid alternative:**
   - Serasa Experian API
   - Receita Federal Direct API

3. **Cache aggressively:**
   ```python
   # Cache CNPJ lookups for longer
   cache_ttl_days = 90  # Longer for government data
   ```

---

### Google Places: 404 Not Found

**Symptom:** Google Places can't find company

**Error:** "Place not found"

**Solutions:**

1. **Company doesn't have Google My Business:**
   - Digital-first companies may not have physical presence
   - Skip Google Places for these companies

2. **Improve search query:**
   ```python
   # Add city to search
   query = f"{company_name}, {city}"
   ```

3. **Make it optional:**
   ```python
   # Don't fail enrichment if Google Places fails
   try:
       google_result = await google_places_source.enrich(...)
   except Exception as e:
       logger.warning(f"Google Places failed: {e}")
       # Continue with other sources
   ```

---

## Deployment Issues

### Railway/Vercel: SSE Timeout

**Symptom:** SSE stream closes after 30 seconds

**Common Causes:**

1. **Platform timeout** (Railway: 30s, Vercel: 10s)
2. **Load balancer timeout**
3. **Reverse proxy timeout**

**Solutions:**

1. **Railway - Increase timeout:**
   ```bash
   # railway.toml
   [build]
   builder = "nixpacks"

   [deploy]
   healthcheckPath = "/health"
   healthcheckTimeout = 300
   ```

2. **Use Render (better SSE support):**
   - Render supports long-lived connections
   - No 30-second timeout

3. **Split into async job:**
   ```python
   # Alternative: Start enrichment, poll for completion
   @router.post("/enrich/start")
   async def start_enrichment():
       task_id = start_background_task()
       return {"task_id": task_id}

   @router.get("/enrich/status/{task_id}")
   async def check_status(task_id: str):
       return {"status": "complete", "data": {...}}
   ```

---

### Environment Variables Not Loaded

**Symptom:** API keys are None

**Common Causes:**

1. **.env file not committed** (correct behavior)
2. **Platform environment variables not set**
3. **Variable name mismatch**

**Solutions:**

1. **Check environment variables:**
   ```bash
   env | grep API_KEY
   ```

2. **Set in deployment platform:**
   ```bash
   # Railway
   railway variables set CLEARBIT_API_KEY=sk_xxx

   # Render
   # Set in dashboard: Environment > Environment Variables
   ```

3. **Add fallback:**
   ```python
   # app/core/config.py
   class Settings:
       clearbit_api_key: Optional[str] = None

       @property
       def is_clearbit_enabled(self) -> bool:
           return self.clearbit_api_key is not None
   ```

---

## Debugging Tools

### Enable Debug Logging

```python
# app/main.py
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
```

### Monitor API Calls

```bash
# Watch logs in real-time
tail -f logs/app.log | grep "enrichment"
```

### Test Individual Sources

```python
# tests/manual/test_source.py
import asyncio
from app.services.enrichment.sources.clearbit import ClearbitSource

async def test_clearbit():
    source = ClearbitSource()
    result = await source.enrich("google.com")
    print(result.data)

asyncio.run(test_clearbit())
```

### Check Circuit Breaker State

```python
# Debug endpoint
@router.get("/debug/circuit-breakers")
async def get_circuit_breakers():
    orchestrator = ProgressiveEnrichmentOrchestrator()
    return {
        "clearbit": orchestrator.clearbit_source.circuit_breaker.state,
        "google_places": orchestrator.google_places_source.circuit_breaker.state,
        # ... other sources
    }
```

### Profile Performance

```python
import cProfile
import pstats

def profile_enrichment():
    profiler = cProfile.Profile()
    profiler.enable()

    # Run enrichment
    asyncio.run(orchestrator.enrich_progressive(...))

    profiler.disable()
    stats = pstats.Stats(profiler)
    stats.sort_stats('cumtime')
    stats.print_stats(10)  # Top 10 slowest functions
```

---

## Getting Help

### Log Information to Include

When reporting issues, include:

1. **Request details:**
   ```json
   {
     "website": "company.com",
     "email": "user@company.com",
     "timestamp": "2025-01-09T14:30:00Z"
   }
   ```

2. **Error message:**
   ```
   Full error text and stack trace
   ```

3. **Logs:**
   ```bash
   grep "session_id" logs/app.log | tail -20
   ```

4. **Environment:**
   ```
   - OS: Ubuntu 22.04
   - Python: 3.11
   - FastAPI: 0.109.0
   - Deployment: Railway
   ```

### Support Channels

- **Documentation**: https://docs.imensiah.com
- **GitHub Issues**: https://github.com/imensiah/issues
- **Email**: support@imensiah.com
- **Discord**: https://discord.gg/imensiah

---

*Last Updated: January 2025*
*Version: 1.0.0*
