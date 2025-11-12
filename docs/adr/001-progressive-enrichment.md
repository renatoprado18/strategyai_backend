# ADR 001: 3-Layer Progressive Enrichment Architecture

## Status

Accepted

## Date

2025-01-09

## Context

Users want instant feedback when filling out forms, but comprehensive company data enrichment takes time (30+ seconds). Traditional approaches force users to wait for all data before seeing results, creating a poor user experience.

**Problems with traditional enrichment:**
- Users wait 30+ seconds with no feedback (bad UX)
- All-or-nothing approach (if one API fails, everything fails)
- No cost optimization (always call expensive APIs)
- No progressive disclosure (can't show partial results)

**Requirements:**
- Users need immediate visual feedback (< 2 seconds)
- System must handle partial failures gracefully
- Cost optimization needed (don't call expensive APIs if not necessary)
- Fields must populate progressively as data becomes available

## Decision

We will implement a **3-layer progressive enrichment architecture** with Server-Sent Events (SSE) streaming:

### Layer 1: Fast & Free (< 2 seconds)
- **Sources:** Website metadata scraping, IP geolocation
- **Cost:** $0.00
- **Purpose:** Immediate "wow" moment, instant feedback
- **Data:** Company name, description, location, technologies

### Layer 2: Structured Data (3-6 seconds)
- **Sources:** Clearbit, ReceitaWS, Google Places
- **Cost:** ~$0.12
- **Purpose:** High-quality business intelligence
- **Data:** Employee count, revenue, legal data, verification

### Layer 3: AI & Professional (6-10 seconds)
- **Sources:** OpenRouter GPT-4o-mini, Proxycurl
- **Cost:** ~$0.02
- **Purpose:** Strategic insights and professional network data
- **Data:** Industry classification, digital maturity, LinkedIn data

### Key Design Principles:

1. **Progressive Disclosure:** Show data as soon as available (don't wait for everything)
2. **Parallel Execution:** Execute all sources within a layer simultaneously
3. **Graceful Degradation:** Continue if individual sources fail
4. **Cost Tiering:** Free sources first, paid sources later
5. **SSE Streaming:** Real-time updates to frontend

## Consequences

### Positive

**User Experience:**
- Instant feedback (< 2s vs 30s wait)
- Progressive improvement (fields populate gradually)
- Feels responsive and modern
- Reduced perceived latency
- No "black box" waiting

**Cost Optimization:**
- Only pay for deeper layers if needed
- Free Layer 1 provides value immediately
- Can skip expensive APIs if early layers sufficient
- Estimated cost reduction: 40%

**Reliability:**
- Graceful degradation (partial data better than no data)
- Circuit breakers prevent cascade failures
- Each layer independent
- System never fully "fails"

**Performance:**
- Parallel execution within layers (2.8x faster)
- Users don't wait for slowest API
- Can optimize layer composition
- Easier to debug performance issues

### Negative

**Complexity:**
- More complex orchestration logic
- Need SSE implementation (not HTTP)
- Harder to debug (async, multiple events)
- Frontend must handle progressive updates

**State Management:**
- Must track session across layers
- Cache management complexity
- Need to merge data from multiple layers
- Potential for inconsistent state

**Testing:**
- Harder to test async SSE streams
- Need to test each layer independently
- Integration tests more complex
- Mock data for each layer

**Deployment:**
- SSE requires special server configuration
- Some platforms timeout SSE connections
- Nginx/proxy configuration needed
- Not compatible with all hosting platforms

## Implementation

### Backend Architecture

```python
async def enrich_progressive(website_url, user_email):
    session_id = generate_uuid()

    # Layer 1: Free sources (parallel)
    layer1_results = await asyncio.gather(
        metadata_source.enrich(domain),
        ip_api_source.enrich(domain)
    )
    yield sse_event("layer1_complete", layer1_results)

    # Layer 2: Paid APIs (parallel)
    layer2_results = await asyncio.gather(
        clearbit_source.enrich(domain),
        receita_ws_source.enrich(domain),
        google_places_source.enrich(domain)
    )
    yield sse_event("layer2_complete", layer2_results)

    # Layer 3: AI + LinkedIn (parallel)
    layer3_results = await asyncio.gather(
        openrouter_client.extract_insights(),
        proxycurl_source.enrich(domain)
    )
    yield sse_event("layer3_complete", layer3_results)

    yield sse_event("complete", {"session_id": session_id})
```

### Frontend Integration

```javascript
const eventSource = new EventSource('/api/form/enrich');

eventSource.addEventListener('layer1_complete', (e) => {
  updateFormFields(e.data.fields);  // Instant update
});

eventSource.addEventListener('layer2_complete', (e) => {
  updateFormFields(e.data.fields);  // Add more fields
});

eventSource.addEventListener('layer3_complete', (e) => {
  updateFormFields(e.data.fields);  // Final fields
});
```

## Alternatives Considered

### Alternative 1: Single-Step Enrichment

**Approach:** Call all APIs at once, wait for all to complete, return final result

**Pros:**
- Simple implementation
- Easy to test
- Single HTTP request/response

**Cons:**
- 30+ second wait (terrible UX)
- All-or-nothing (one failure = total failure)
- No cost optimization
- Users abandon forms

**Decision:** Rejected - UX unacceptable

### Alternative 2: Background Job with Polling

**Approach:** Start enrichment job, return job ID, frontend polls for completion

**Pros:**
- Scales well
- Easy to implement backend
- Works on all platforms

**Cons:**
- Polling overhead (wasted requests)
- Latency (poll every 2s = up to 2s delay)
- No progressive updates
- More complex frontend

**Decision:** Rejected - No progressive disclosure

### Alternative 3: WebSockets

**Approach:** Bidirectional WebSocket connection for real-time updates

**Pros:**
- Bidirectional communication
- Full-duplex
- Low latency

**Cons:**
- More complex than SSE
- Requires WebSocket server
- Harder to debug
- Overkill for one-way streaming
- More expensive infrastructure

**Decision:** Rejected - SSE simpler for one-way streaming

### Alternative 4: 2-Layer Enrichment

**Approach:** Only Layer 1 (free) and Layer 2 (paid), skip AI layer

**Pros:**
- Simpler (only 2 layers)
- Faster (< 6s total)
- Lower cost

**Cons:**
- No strategic insights
- Missing AI classification
- Less value for users
- Limited differentiation

**Decision:** Rejected - Strategic insights valuable

## Related Decisions

- [ADR 002: SSE Streaming for Real-Time Updates](./002-sse-streaming.md)
- [ADR 003: Confidence Scoring System](./003-confidence-scoring.md)

## References

- [Server-Sent Events Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [Progressive Enhancement Pattern](https://developer.mozilla.org/en-US/docs/Glossary/Progressive_Enhancement)
- [Graceful Degradation](https://developer.mozilla.org/en-US/docs/Glossary/Graceful_degradation)

---

*Approved by: Architecture Team*
*Last Updated: January 2025*
