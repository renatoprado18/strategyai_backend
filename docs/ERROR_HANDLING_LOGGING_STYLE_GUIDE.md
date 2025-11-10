# Error Handling and Logging Style Guide

## Strategy AI Backend - Professional Error Management

Version: 1.0.0
Created: 2025-01-10
Last Updated: 2025-01-10

---

## Table of Contents

1. [Philosophy](#philosophy)
2. [Logging Levels](#logging-levels)
3. [Error Handling Patterns](#error-handling-patterns)
4. [Message Format Standards](#message-format-standards)
5. [Layer-Specific Guidelines](#layer-specific-guidelines)
6. [Anti-Patterns to Avoid](#anti-patterns-to-avoid)
7. [Examples](#examples)

---

## Philosophy

### Core Principles

1. **Clarity Over Brevity**: Error messages should be immediately actionable
2. **Context is King**: Always include relevant context (domain, field, source)
3. **Progressive Disclosure**: Different log levels for different audiences
4. **Graceful Degradation**: Failures should not break the user experience
5. **Production-Ready**: Logs should help debug issues in production

### Audience

- **DEBUG**: Developers debugging locally
- **INFO**: Operations monitoring system health
- **WARNING**: Operations investigating issues
- **ERROR**: Engineers fixing critical bugs

---

## Logging Levels

### DEBUG (Development Only)

Use for detailed information useful during development.

**When to use:**
- API key availability checks
- Cache hits/misses
- Field value transformations
- Internal state changes

**Format:**
```python
logger.debug(f"[{Source}] {What happened}: {Details}")
```

**Examples:**
```python
logger.debug(f"[Clearbit] API key configured: {bool(self.api_key)}")
logger.debug(f"[Cache] Hit for key: progressive_enrichment:example.com")
logger.debug(f"[Translation] Mapped backend field 'company_name' → 'name'")
```

### INFO (Normal Operations)

Use for significant events in normal system operation.

**When to use:**
- Successful enrichment completions
- Layer completion milestones
- Performance metrics
- Data extraction summaries

**Format:**
```python
logger.info(f"[{Layer/Source}] {Action} complete: {Summary} in {duration}ms")
```

**Examples:**
```python
logger.info(f"[Layer 1] Metadata extraction complete: 8 fields in 456ms")
logger.info(f"[Clearbit] Enriched example.com: TechStart Inc in 1234ms")
logger.info(f"[Progressive] Enrichment session complete: 24 fields, $0.15, 8542ms")
```

### WARNING (Expected Failures)

Use for recoverable issues that don't prevent operation.

**When to use:**
- Missing API keys (expected in dev/test)
- API rate limits
- Data not found (404s)
- Partial data available
- Cache failures

**Format:**
```python
logger.warning(f"[{Source}] {Issue} - {Impact} (continuing anyway)")
```

**Examples:**
```python
logger.warning(f"[Clearbit] API key not configured - skipping enrichment")
logger.warning(f"[ReceitaWS] No CNPJ found for 'Acme Corp' - continuing with partial data")
logger.warning(f"[Cache] Failed to store session (non-critical, proceeding)")
logger.warning(f"[Layer 2] Proxycurl rate limit exceeded - returning partial results")
```

### ERROR (Unexpected Failures)

Use for unexpected issues that require investigation.

**When to use:**
- Unexpected exceptions
- Data corruption
- Critical API failures
- System errors

**Format:**
```python
logger.error(f"[{Component}] {Specific Error}: {Details}", exc_info=True)
```

**Examples:**
```python
logger.error(f"[Database] Failed to store enrichment result: {str(e)}", exc_info=True)
logger.error(f"[OpenRouter] AI inference failed unexpectedly: {str(e)}", exc_info=True)
logger.error(f"[Progressive] Session initialization failed: {str(e)}", exc_info=True)
```

---

## Error Handling Patterns

### Pattern 1: Graceful Degradation (Preferred)

**Use when:** Failure should not block other operations

```python
try:
    result = await external_api_call()
    if result.success:
        data.update(result.data)
except Exception as e:
    logger.warning(f"[Source] API call failed - continuing with partial data: {str(e)}")
    # Continue processing with whatever data we have
```

### Pattern 2: Fail Fast with Context

**Use when:** Failure invalidates further processing

```python
try:
    critical_data = await required_operation()
except Exception as e:
    logger.error(f"[Component] Critical operation failed: {str(e)}", exc_info=True)
    raise HTTPException(
        status_code=500,
        detail=f"Failed to process request: {str(e)}"
    )
```

### Pattern 3: Silent Skip (Use Sparingly)

**Use when:** Missing feature should be invisible to user

```python
if not self.api_key:
    logger.debug(f"[Source] API key not configured - skipping")
    return SourceResult(
        source_name=self.name,
        success=False,
        data={},
        cost_usd=0.0,
        duration_ms=0,
        error_message="API key not configured"
    )
```

### Pattern 4: Structured Error Returns

**Use when:** Caller needs to distinguish error types

```python
try:
    data = await fetch_data()
    return SourceResult(success=True, data=data, ...)
except TimeoutException:
    logger.warning(f"[Source] Request timeout after {timeout}s")
    return SourceResult(success=False, error_type="timeout", ...)
except RateLimitException:
    logger.warning(f"[Source] Rate limit exceeded - retry later")
    return SourceResult(success=False, error_type="rate_limit", ...)
```

---

## Message Format Standards

### Component Prefixes

Always prefix log messages with the component name in brackets:

- `[Layer 1]`, `[Layer 2]`, `[Layer 3]` - Enrichment layers
- `[Clearbit]`, `[ReceitaWS]`, `[Google Places]` - External sources
- `[Metadata]`, `[IP API]` - Free sources
- `[OpenRouter]`, `[Proxycurl]` - AI/paid sources
- `[Cache]` - Caching operations
- `[Database]` - Database operations
- `[Translation]` - Field translation
- `[Progressive]` - Orchestrator operations
- `[SSE]` - Server-sent events

### Action Verbs

Use consistent action verbs:

- **Starting**: "Starting", "Initializing", "Beginning"
- **In Progress**: "Processing", "Querying", "Fetching", "Extracting"
- **Success**: "Complete", "Enriched", "Extracted", "Cached", "Stored"
- **Failure**: "Failed", "Skipping", "Missing", "Timeout", "Error"

### Performance Metrics

Always include timing and cost when relevant:

```python
logger.info(
    f"[Clearbit] Enriched example.com: TechStart Inc "
    f"in {duration_ms}ms (cost: ${cost:.4f})"
)
```

### Structured Logging

Use the `extra` parameter for structured data:

```python
logger.info(
    f"[Layer 1] Extraction complete: {field_count} fields in {duration_ms}ms",
    extra={
        "layer": 1,
        "domain": domain,
        "field_count": field_count,
        "duration_ms": duration_ms,
        "sources": ["metadata", "ip_api"]
    }
)
```

---

## Layer-Specific Guidelines

### Layer 1 (Free, Instant <2s)

**Sources:** Metadata, IP API
**Expected behavior:** Should always succeed or fail fast
**Logging:**

```python
# Success
logger.info(f"[Layer 1] Complete: {len(data)} fields in {duration}ms")

# Partial success
logger.warning(f"[Layer 1] Metadata extraction failed - IP data available")

# Complete failure (rare)
logger.error(f"[Layer 1] Complete failure: {str(e)}", exc_info=True)
```

### Layer 2 (Paid, Parallel 3-6s)

**Sources:** Clearbit, ReceitaWS, Google Places
**Expected behavior:** Gracefully handle missing API keys and 404s
**Logging:**

```python
# API key missing (common, expected)
logger.debug(f"[Clearbit] API key not configured - skipping")

# Company not found (expected)
logger.info(f"[Clearbit] Company not found: {domain}")

# API error (needs attention)
logger.warning(f"[Clearbit] HTTP {status_code}: {error} (continuing with partial data)")

# Unexpected error
logger.error(f"[Clearbit] Unexpected error: {str(e)}", exc_info=True)
```

### Layer 3 (AI + LinkedIn 6-10s)

**Sources:** OpenRouter (AI), Proxycurl (LinkedIn)
**Expected behavior:** Gracefully handle AI failures and missing data
**Logging:**

```python
# AI unavailable
logger.warning(f"[OpenRouter] Client not available - skipping AI inference")

# AI success
logger.info(f"[OpenRouter] AI inference complete: {fields_extracted} fields in {duration}ms")

# LinkedIn not found
logger.info(f"[Proxycurl] LinkedIn profile not found for {domain}")

# Rate limit
logger.warning(f"[Proxycurl] Rate limit exceeded - returning partial results")
```

---

## Anti-Patterns to Avoid

### 1. NEVER Use print() Statements

**BAD:**
```python
print("Error:", error)
print(f"Processing {domain}")
```

**GOOD:**
```python
logger.error(f"[Component] Error: {error}")
logger.info(f"[Component] Processing {domain}")
```

### 2. NEVER Log Without Context

**BAD:**
```python
logger.error("Error querying API")
logger.warning("Request failed")
```

**GOOD:**
```python
logger.error(f"[Clearbit] API query failed for domain {domain}: {str(e)}", exc_info=True)
logger.warning(f"[ReceitaWS] CNPJ search request failed - company not found")
```

### 3. NEVER Swallow Exceptions Silently

**BAD:**
```python
try:
    result = await api_call()
except:
    pass  # Silent failure
```

**GOOD:**
```python
try:
    result = await api_call()
except Exception as e:
    logger.warning(f"[Source] API call failed (continuing anyway): {str(e)}")
    result = None  # Explicit handling
```

### 4. NEVER Log Sensitive Data

**BAD:**
```python
logger.info(f"API key: {api_key}")
logger.info(f"User email: {user_email}")
```

**GOOD:**
```python
logger.debug(f"API key configured: {bool(api_key)}")
logger.info(f"Enriching for user: {user_email[:3]}***@{user_email.split('@')[1]}")
```

### 5. NEVER Use Wrong Log Levels

**BAD:**
```python
logger.error("Company not found in Clearbit")  # Expected condition
logger.info("Database write failed!")  # Critical error
logger.warning("Processing complete")  # Normal operation
```

**GOOD:**
```python
logger.info("Company not found in Clearbit")  # Expected, handled
logger.error("Database write failed!", exc_info=True)  # Critical
logger.info("Processing complete")  # Normal
```

### 6. NEVER Log Without Rate Limiting (Loops)

**BAD:**
```python
for item in large_list:
    logger.info(f"Processing {item}")  # Spam!
```

**GOOD:**
```python
logger.info(f"Processing {len(large_list)} items")
for item in large_list:
    logger.debug(f"Processing {item}")  # DEBUG only
logger.info(f"Processed {len(large_list)} items in {duration}ms")
```

---

## Examples

### Example 1: Progressive Enrichment Route

```python
@router.post("/start")
async def start_progressive_enrichment(request: ProgressiveEnrichmentRequest):
    """Start progressive enrichment with proper error handling"""

    try:
        session_id = str(uuid.uuid4())

        logger.info(
            f"[Progressive] Starting enrichment for {request.website_url}",
            extra={"session_id": session_id, "domain": request.website_url}
        )

        # Create orchestrator
        orchestrator = ProgressiveEnrichmentOrchestrator()

        # Start background task
        async def run_enrichment():
            try:
                session = await orchestrator.enrich_progressive(
                    website_url=request.website_url,
                    user_email=request.user_email
                )
                active_sessions[session_id] = session

                logger.info(
                    f"[Progressive] Enrichment complete: {session.total_duration_ms}ms, "
                    f"${session.total_cost_usd:.4f}, {len(session.fields_auto_filled)} fields",
                    extra={
                        "session_id": session_id,
                        "duration_ms": session.total_duration_ms,
                        "cost_usd": session.total_cost_usd,
                        "field_count": len(session.fields_auto_filled)
                    }
                )

            except Exception as e:
                logger.error(
                    f"[Progressive] Enrichment failed for session {session_id}: {str(e)}",
                    exc_info=True,
                    extra={"session_id": session_id}
                )
                # Ensure partial data is still available
                if session_id in active_sessions:
                    active_sessions[session_id].status = "complete"

        background_tasks.add_task(run_enrichment)

        return ProgressiveEnrichmentResponse(
            session_id=session_id,
            status="processing",
            message="Progressive enrichment started",
            stream_url=f"/api/enrichment/progressive/stream/{session_id}"
        )

    except Exception as e:
        logger.error(
            f"[Progressive] Failed to start enrichment: {str(e)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start enrichment: {str(e)}"
        )
```

### Example 2: Layer 2 Source (Clearbit)

```python
async def enrich(self, domain: str, **kwargs) -> SourceResult:
    """Enrich with graceful API key handling"""

    start_time = time.time()

    try:
        # Gracefully handle missing API key
        if not self.api_key:
            logger.debug(f"[Clearbit] API key not configured - skipping enrichment")
            return SourceResult(
                source_name=self.name,
                success=False,
                data={},
                cost_usd=0.0,
                duration_ms=0,
                error_message="API key not configured"
            )

        # Clean domain
        clean_domain = self._clean_domain(domain)

        logger.debug(f"[Clearbit] Querying API for {clean_domain}")

        # Query API
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.API_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"domain": clean_domain}
            )

            if response.status_code == 404:
                logger.info(f"[Clearbit] Company not found: {clean_domain}")
                return SourceResult(
                    source_name=self.name,
                    success=False,
                    data={},
                    cost_usd=0.0,
                    duration_ms=int((time.time() - start_time) * 1000),
                    error_message="Company not found"
                )

            if response.status_code == 402:
                logger.warning(f"[Clearbit] Credits exhausted - payment required")
                raise Exception("Clearbit credits exhausted")

            response.raise_for_status()
            data = response.json()

        # Process data
        enriched_data = self._extract_data(data)
        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"[Clearbit] Enriched {clean_domain}: "
            f"{enriched_data.get('company_name', 'Unknown')} "
            f"in {duration_ms}ms (${self.cost_per_call:.2f})",
            extra={
                "domain": clean_domain,
                "company": enriched_data.get("company_name"),
                "fields": len(enriched_data),
                "duration_ms": duration_ms,
                "cost_usd": self.cost_per_call
            }
        )

        return SourceResult(
            source_name=self.name,
            success=True,
            data=enriched_data,
            duration_ms=duration_ms,
            cost_usd=self.cost_per_call
        )

    except httpx.TimeoutException:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.warning(
            f"[Clearbit] Request timeout after {duration_ms}ms for {domain}"
        )
        raise Exception(f"Request timeout after {self.timeout}s")

    except httpx.HTTPStatusError as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.warning(
            f"[Clearbit] HTTP {e.response.status_code} for {domain} "
            f"after {duration_ms}ms"
        )
        raise

    except Exception as e:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.error(
            f"[Clearbit] Unexpected error for {domain}: {str(e)}",
            exc_info=True,
            extra={"domain": domain, "duration_ms": duration_ms}
        )
        raise
```

### Example 3: Progressive Orchestrator

```python
async def enrich_progressive(
    self,
    website_url: str,
    user_email: Optional[str] = None
) -> ProgressiveEnrichmentSession:
    """Execute progressive enrichment with bulletproof error handling"""

    session_id = str(uuid.uuid4())
    start_time = datetime.now()

    logger.info(
        f"[Progressive] Starting 3-layer enrichment for {website_url}",
        extra={"session_id": session_id, "website_url": website_url}
    )

    # Layer 1: Free sources (always attempt)
    layer1_start = datetime.now()
    layer1_data = {}

    try:
        tasks = [
            self.metadata_source.enrich(domain),
            self.ip_api_source.enrich(domain)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning(
                    f"[Layer 1] Source failed (continuing): {str(result)}"
                )
                continue
            if result.success:
                layer1_data.update(result.data)

        layer1_duration = int((datetime.now() - layer1_start).total_seconds() * 1000)

        logger.info(
            f"[Layer 1] Complete: {len(layer1_data)} fields in {layer1_duration}ms",
            extra={
                "session_id": session_id,
                "field_count": len(layer1_data),
                "duration_ms": layer1_duration
            }
        )

    except Exception as e:
        logger.error(
            f"[Layer 1] Unexpected failure: {str(e)}",
            exc_info=True,
            extra={"session_id": session_id}
        )
        # Continue with empty data

    # Layer 2: Paid sources (graceful degradation)
    # ... similar pattern ...

    # Layer 3: AI sources (graceful degradation)
    # ... similar pattern ...

    logger.info(
        f"[Progressive] Enrichment complete: "
        f"{session.total_duration_ms}ms, ${session.total_cost_usd:.4f}, "
        f"{len(session.fields_auto_filled)} fields auto-filled",
        extra={
            "session_id": session_id,
            "total_duration_ms": session.total_duration_ms,
            "total_cost_usd": session.total_cost_usd,
            "field_count": len(session.fields_auto_filled)
        }
    )

    return session
```

---

## Quick Reference Card

| Situation | Log Level | Format | Example |
|-----------|-----------|--------|---------|
| Normal operation complete | INFO | `[Component] {Action} complete: {summary} in {time}ms` | `[Layer 1] Extraction complete: 8 fields in 456ms` |
| API key missing (dev/test) | DEBUG | `[Source] API key not configured - skipping` | `[Clearbit] API key not configured - skipping` |
| Expected API failure | INFO/WARNING | `[Source] {Resource} not found: {identifier}` | `[Clearbit] Company not found: example.com` |
| Recoverable error | WARNING | `[Source] {Error} - continuing with partial data` | `[ReceitaWS] CNPJ lookup failed - continuing anyway` |
| Unexpected error | ERROR | `[Component] {Error}: {details}` + exc_info | `[Database] Write failed: Connection timeout` |
| Performance metric | INFO | `[Source] {Action}: {result} in {time}ms (${cost})` | `[Clearbit] Enriched: Acme Corp in 1234ms ($0.10)` |

---

## Checklist for Code Review

- [ ] All log messages have component prefix (e.g., `[Clearbit]`)
- [ ] No `print()` statements used
- [ ] Appropriate log level for each message
- [ ] Error messages include context (domain, field, etc.)
- [ ] Performance metrics included where relevant
- [ ] No sensitive data logged (API keys, passwords, PII)
- [ ] Exception info included for ERROR level (`exc_info=True`)
- [ ] Graceful degradation for expected failures
- [ ] Structured logging used for important events (`extra={}`)
- [ ] Messages are actionable and clear

---

## Conclusion

Following these guidelines will ensure:

1. **Production logs are clean and actionable**
2. **Errors are easy to debug**
3. **Operations can monitor system health**
4. **Users get the best experience even during failures**

Remember: **Good logging is not about volume, it's about signal-to-noise ratio.**

---

**Questions or suggestions?** Open an issue or PR with improvements to this guide.
