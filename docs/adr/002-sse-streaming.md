# ADR 002: Server-Sent Events (SSE) for Real-Time Streaming

## Status

Accepted

## Date

2025-01-09

## Context

Progressive enrichment requires pushing updates to the frontend as data becomes available across 3 layers (2s, 6s, 10s). We need a real-time communication mechanism that:

- Supports server-to-client push (one-way)
- Works with standard HTTP infrastructure
- Handles connection loss gracefully
- Is simple to implement and debug
- Scales to hundreds of concurrent connections

**Requirements:**
- Stream events progressively (layer1_complete, layer2_complete, etc.)
- Maintain connection for 10+ seconds
- Handle network interruptions
- Work with existing HTTP infrastructure
- Low latency (< 100ms event delivery)

## Decision

We will use **Server-Sent Events (SSE)** for streaming enrichment updates from backend to frontend.

### SSE Implementation

#### Backend (FastAPI)

```python
from fastapi.responses import StreamingResponse

async def event_stream():
    # Layer 1
    yield f"event: layer1_complete\n"
    yield f"data: {json.dumps(layer1_data)}\n\n"

    # Layer 2
    yield f"event: layer2_complete\n"
    yield f"data: {json.dumps(layer2_data)}\n\n"

    # Layer 3
    yield f"event: layer3_complete\n"
    yield f"data: {json.dumps(layer3_data)}\n\n"

    # Complete
    yield f"event: complete\n"
    yield f"data: {json.dumps(final_data)}\n\n"

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

#### Frontend (JavaScript)

```javascript
const eventSource = new EventSource('/api/form/enrich');

eventSource.addEventListener('layer1_complete', (e) => {
  const data = JSON.parse(e.data);
  updateFormFields(data.fields);
});

eventSource.addEventListener('complete', (e) => {
  eventSource.close();
});

eventSource.addEventListener('error', (e) => {
  console.error('SSE error:', e);
  eventSource.close();
});
```

### Event Format

```
event: layer1_complete
data: {"status":"layer1_complete","fields":{"name":"Company"}}

event: layer2_complete
data: {"status":"layer2_complete","fields":{"employeeCount":"25-50"}}

event: layer3_complete
data: {"status":"layer3_complete","fields":{"industry":"Technology"}}

event: complete
data: {"status":"complete","session_id":"abc-123"}
```

## Consequences

### Positive

**Simplicity:**
- Built into browsers (native EventSource API)
- Standard HTTP (works with existing infrastructure)
- Simple text protocol (easy to debug)
- No special libraries needed

**Reliability:**
- Automatic reconnection (browser handles it)
- Connection loss detection
- Event IDs for resumption (optional)
- Error handling built-in

**Performance:**
- Low overhead (HTTP/1.1 or HTTP/2)
- Efficient (no polling)
- One-way (perfect for our use case)
- Works with CDNs and proxies

**Developer Experience:**
- Easy to implement
- Easy to debug (curl works!)
- Clear event boundaries
- JSON-compatible

### Negative

**Limitations:**
- One-way only (server → client)
- Text-only (no binary)
- Browser connection limits (6 per domain)
- Some platforms timeout long connections

**Platform Compatibility:**
- Railway: 30s timeout (need workaround)
- Vercel: 10s timeout (problematic)
- Some reverse proxies buffer SSE
- Need X-Accel-Buffering header for nginx

**Debugging:**
- Harder to test than REST API
- Event streaming in tests complex
- Need special test utilities
- Can't use Postman easily

**Mobile:**
- Battery drain on long connections
- Network switching can break connection
- Need reconnection logic
- May need fallback for old browsers

## Implementation Details

### Critical Headers

```python
headers = {
    "Cache-Control": "no-cache",         # Prevent caching
    "Connection": "keep-alive",          # Keep connection open
    "X-Accel-Buffering": "no",           # Disable nginx buffering
    "Content-Type": "text/event-stream", # SSE content type
}
```

### Error Handling

```python
try:
    async for event in event_stream():
        yield event
except Exception as e:
    # Send error event
    error_data = {
        "status": "error",
        "error": type(e).__name__,
        "message": str(e)
    }
    yield f"event: error\n"
    yield f"data: {json.dumps(error_data)}\n\n"
```

### Nginx Configuration

```nginx
location /api/form/enrich {
    proxy_pass http://backend;
    proxy_buffering off;           # Critical!
    proxy_cache off;
    proxy_set_header Connection '';
    proxy_http_version 1.1;
    chunked_transfer_encoding off;
    proxy_read_timeout 300s;       # 5 minute timeout
}
```

### Timeout Handling

```javascript
// Frontend timeout fallback
const timeout = setTimeout(() => {
  console.warn('SSE timeout, closing connection');
  eventSource.close();
  showManualEntryOption();
}, 15000);  // 15 second timeout

eventSource.addEventListener('complete', () => {
  clearTimeout(timeout);
  eventSource.close();
});
```

## Alternatives Considered

### Alternative 1: WebSockets

**Approach:** Full-duplex WebSocket connection

**Pros:**
- Bidirectional communication
- Binary support
- Lower latency
- More flexible

**Cons:**
- Overkill for one-way streaming
- More complex implementation
- Requires WebSocket server
- Harder to debug
- More expensive infrastructure
- Not HTTP (proxy issues)

**Decision:** Rejected - SSE simpler for one-way push

### Alternative 2: Long Polling

**Approach:** Frontend polls endpoint repeatedly

**Pros:**
- Works everywhere (HTTP)
- Simple to implement
- No special server support

**Cons:**
- Inefficient (many requests)
- Higher latency (poll interval)
- Server load (constant polling)
- No real-time updates
- Wastes bandwidth

**Decision:** Rejected - Inefficient

### Alternative 3: HTTP/2 Server Push

**Approach:** Use HTTP/2 server push mechanism

**Pros:**
- Native HTTP/2 feature
- No extra protocol
- Efficient

**Cons:**
- Not widely supported yet
- Complex implementation
- Browser support limited
- Can't push after initial response

**Decision:** Rejected - Limited support

### Alternative 4: GraphQL Subscriptions

**Approach:** Use GraphQL subscription protocol

**Pros:**
- Modern approach
- Typed schema
- GraphQL ecosystem

**Cons:**
- Requires GraphQL server
- More complex setup
- Overkill for simple streaming
- Additional dependencies

**Decision:** Rejected - Too complex

## Testing Strategy

### Unit Test (Mock SSE)

```python
def test_sse_stream():
    with client.stream("POST", "/api/form/enrich", json={...}) as response:
        events = []
        for line in response.iter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line[5:]))

        assert len(events) == 4  # 3 layers + complete
        assert events[0]["status"] == "layer1_complete"
        assert events[-1]["status"] == "complete"
```

### Integration Test (Real Connection)

```javascript
// Playwright E2E test
test('SSE stream receives all events', async () => {
  const events = [];

  const eventSource = new EventSource('/api/form/enrich');

  eventSource.addEventListener('message', (e) => {
    events.push(JSON.parse(e.data));
  });

  await new Promise(resolve => setTimeout(resolve, 15000));

  expect(events).toHaveLength(4);
  expect(events[3].status).toBe('complete');
});
```

## Rollback Plan

If SSE proves problematic:

1. **Fallback to polling:**
   ```javascript
   if (!window.EventSource) {
     // Fallback for old browsers
     pollForResults();
   }
   ```

2. **Hybrid approach:**
   - Use SSE if supported
   - Fall back to long polling if not

3. **Simplify to 2-step:**
   - Quick enrichment (synchronous)
   - Full enrichment (background + polling)

## Monitoring

Track these metrics:

```python
logger.info(
    "SSE stream completed",
    extra={
        "events_sent": 4,
        "duration_ms": 8500,
        "connection_dropped": False
    }
)
```

**Key Metrics:**
- SSE connection success rate (> 95%)
- Average events delivered (should be 4)
- Connection drop rate (< 5%)
- Event delivery latency (< 100ms)

## Related Decisions

- [ADR 001: 3-Layer Progressive Enrichment](./001-progressive-enrichment.md)
- [ADR 003: Confidence Scoring System](./003-confidence-scoring.md)

## References

- [MDN: Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events)
- [SSE Specification](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [FastAPI Streaming Responses](https://fastapi.tiangolo.com/advanced/custom-response/#streamingresponse)

---

*Approved by: Architecture Team*
*Last Updated: January 2025*
