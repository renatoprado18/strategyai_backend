"""
Form Enrichment API Routes

Fast, lightweight form auto-fill endpoint that completes in 5-10 seconds.
Uses progressive 3-layer enrichment WITHOUT strategic analysis.

Purpose: Pre-fill company data before user submits full form.
Workflow: Form enrichment (Phase 1) → Strategic analysis (Phase 2)
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict, Any
from urllib.parse import urlparse
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator

from app.services.enrichment.progressive_orchestrator import (
    ProgressiveEnrichmentOrchestrator,
)
from app.services.enrichment.validators import validate_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/form", tags=["Form Enrichment"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class FormEnrichmentRequest(BaseModel):
    """Request to enrich form with company data"""

    website: Optional[str] = Field(
        None,
        description="Company website URL (with or without https://)",
        example="google.com"
    )
    url: Optional[str] = Field(
        None,
        description="Company website URL (alias for 'website')",
        example="google.com"
    )
    email: str = Field(
        ...,
        description="User's email address",
        example="jeff@google.com"
    )

    @validator("website", pre=True, always=True)
    def normalize_website(cls, v, values):
        """Accept both 'website' and 'url' fields"""
        # If website not provided, try url field
        if not v and 'url' in values:
            v = values.get('url')

        if not v:
            raise ValueError("Either 'website' or 'url' field is required")

        # Add https:// if missing
        if not v.startswith(("http://", "https://")):
            v = f"https://{v}"

        result = validate_url(v)
        if not result.is_valid:
            raise ValueError(result.error_message or "Invalid website URL")
        return result.formatted_value or v

    @validator("email")
    def validate_email(cls, v):
        """Basic email validation"""
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email address")
        return v.lower().strip()


# ============================================================================
# FIELD TRANSLATION (Backend → Frontend Form Fields)
# ============================================================================


def translate_to_form_fields(backend_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Translate enrichment data to form field names.

    Maps backend field names from enrichment sources to the
    expected form field names in the frontend.

    Args:
        backend_data: Data from progressive enrichment layers

    Returns:
        Translated field data matching frontend form expectations
    """
    translation_map = {
        # Core company info
        "company_name": "name",
        "description": "description",
        "website": "website",

        # Location fields
        "city": "city",
        "region": "state",
        "country_name": "country",
        "ip_location": "location",

        # Contact info
        "phone": "phone",
        "email": "email",

        # Company details
        "employee_count": "employeeCount",
        "annual_revenue": "annualRevenue",
        "founded_year": "foundedYear",
        "legal_name": "legalName",

        # AI-inferred fields (remove ai_ prefix)
        "ai_industry": "industry",
        "ai_company_size": "companySize",
        "ai_digital_maturity": "digitalMaturity",
        "ai_target_audience": "targetAudience",
        "ai_key_differentiators": "keyDifferentiators",

        # Additional metadata
        "logo_url": "logoUrl",
        "meta_description": "metaDescription",
        "cnpj": "cnpj",
        "rating": "rating",
        "reviews_count": "reviewsCount",
    }

    # Apply translation
    form_data = {}
    for backend_key, value in backend_data.items():
        if value is not None and value != "":
            # Use translated name if available, otherwise keep original
            form_key = translation_map.get(backend_key, backend_key)
            form_data[form_key] = value

    return form_data


# ============================================================================
# ACTIVE SESSIONS (In-memory storage)
# ============================================================================

# Store active enrichment sessions
# In production with multiple workers, use Redis
active_enrichment_sessions: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# ROUTES
# ============================================================================


@router.post("/enrich",
    summary="Fast Form Auto-Fill",
    description="""
    **FAST** form enrichment endpoint that returns company data in 5-10 seconds.

    **Purpose:**
    - Pre-fill form fields before user submission
    - Provide instant company data without full strategic analysis
    - Cache results for later use in strategic analysis (Phase 2)

    **Process Flow:**
    1. User enters website + email
    2. Backend enriches with 3-layer progressive enrichment:
       - **Layer 1 (<2s)**: Metadata scraping + IP geolocation (free)
       - **Layer 2 (3-6s)**: Clearbit + ReceitaWS + Google Places (paid)
       - **Layer 3 (6-10s)**: GPT-4o-mini inference + Proxycurl (AI)
    3. Returns SSE stream with progressive field updates
    4. Caches session for Phase 2 (strategic analysis)

    **What This Does:**
    - ✅ Fast form auto-fill (5-10 seconds)
    - ✅ Progressive SSE streaming
    - ✅ Session caching for reuse
    - ❌ NO strategic analysis (use /api/submit for that)

    **SSE Event Types:**
    - `layer1_complete`: Basic metadata available
    - `layer2_complete`: Structured data available
    - `layer3_complete`: AI inference complete
    - `complete`: All enrichment finished (includes session_id)

    **Example Request:**
    ```bash
    curl -X POST http://localhost:8000/api/form/enrich \\
      -H "Content-Type: application/json" \\
      -d '{
        "website": "google.com",
        "email": "test@test.com"
      }'
    ```

    **Example Response (SSE Stream):**
    ```
    event: layer1_complete
    data: {"status":"layer1_complete","fields":{"name":"Google","city":"Mountain View"}}

    event: layer2_complete
    data: {"status":"layer2_complete","fields":{"employeeCount":"10000+","industry":"Technology"}}

    event: layer3_complete
    data: {"status":"layer3_complete","fields":{"digitalMaturity":"High","companySize":"Large"}}

    event: complete
    data: {"status":"complete","session_id":"abc-123","total_duration_ms":8500}
    ```

    **Frontend Usage:**
    ```typescript
    const eventSource = new EventSource('/api/form/enrich');

    eventSource.addEventListener('layer1_complete', (e) => {
      const data = JSON.parse(e.data);
      // Auto-fill form fields progressively
      updateFormFields(data.fields);
    });

    eventSource.addEventListener('complete', (e) => {
      const data = JSON.parse(e.data);
      // Save session_id for Phase 2 submission
      setSessionId(data.session_id);
      eventSource.close();
    });
    ```

    **Caching:**
    - Results cached for 30 days in Supabase
    - Phase 2 (strategic analysis) can reuse cached data
    - Saves time and API costs on full submission

    **Performance:**
    - Target: < 10 seconds total
    - Layer 1: < 2 seconds (free sources)
    - Layer 2: 3-6 seconds (paid APIs)
    - Layer 3: 6-10 seconds (AI inference)

    **Cost:**
    - Layer 1: $0 (free)
    - Layer 2: ~$0.01-0.05 (Clearbit, Google Places)
    - Layer 3: ~$0.001-0.01 (GPT-4o-mini inference)
    - Total: ~$0.01-0.06 per enrichment
    """,
    responses={
        200: {
            "description": "SSE stream of progressive enrichment updates",
            "content": {
                "text/event-stream": {
                    "example": "event: layer1_complete\\ndata: {\\\"status\\\":\\\"layer1_complete\\\",\\\"fields\\\":{\\\"name\\\":\\\"Google\\\"}}\\n\\n"
                }
            }
        },
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "example": {"detail": "Invalid website URL"}
                }
            }
        }
    })
async def enrich_form(request: FormEnrichmentRequest):
    """
    Fast form enrichment - returns company data in 5-10 seconds via SSE stream.

    Uses 3-layer progressive enrichment:
    - Layer 1: Free sources (metadata, IP location)
    - Layer 2: Paid APIs (Clearbit, ReceitaWS, Google Places)
    - Layer 3: AI inference (GPT-4o-mini)

    Returns SSE stream with progressive field updates.
    """

    async def event_stream():
        """Generate SSE events for progressive enrichment"""
        import uuid
        session_id = str(uuid.uuid4())
        start_time = datetime.now()

        try:
            logger.info(f"[FORM ENRICHMENT] Starting: website={request.website}, email={request.email}")

            # Create orchestrator
            orchestrator = ProgressiveEnrichmentOrchestrator()

            # Start enrichment
            session = await orchestrator.enrich_progressive(
                website_url=request.website,
                user_email=request.email,
                existing_data={"email": request.email}
            )

            # Override session_id with our own
            session.session_id = session_id

            # ================================================================
            # LAYER 1 COMPLETE
            # ================================================================
            if session.layer1_result:
                layer1_fields = translate_to_form_fields(session.layer1_result.data)

                event_data = {
                    "status": "layer1_complete",
                    "fields": layer1_fields,
                    "duration_ms": session.layer1_result.duration_ms,
                    "sources": session.layer1_result.sources_called,
                }

                yield f"event: layer1_complete\n"
                yield f"data: {json.dumps(event_data)}\n\n"

                logger.info(f"[FORM ENRICHMENT] Layer 1 complete: {len(layer1_fields)} fields")

            # ================================================================
            # LAYER 2 COMPLETE
            # ================================================================
            if session.layer2_result:
                # Combine Layer 1 + Layer 2 data
                combined_data = {}
                if session.layer1_result:
                    combined_data.update(session.layer1_result.data)
                combined_data.update(session.layer2_result.data)

                layer2_fields = translate_to_form_fields(combined_data)

                event_data = {
                    "status": "layer2_complete",
                    "fields": layer2_fields,
                    "duration_ms": session.layer2_result.duration_ms,
                    "sources": session.layer2_result.sources_called,
                }

                yield f"event: layer2_complete\n"
                yield f"data: {json.dumps(event_data)}\n\n"

                logger.info(f"[FORM ENRICHMENT] Layer 2 complete: {len(layer2_fields)} fields")

            # ================================================================
            # LAYER 3 COMPLETE (FINAL)
            # ================================================================
            if session.layer3_result:
                # Combine all layers
                combined_data = {}
                if session.layer1_result:
                    combined_data.update(session.layer1_result.data)
                if session.layer2_result:
                    combined_data.update(session.layer2_result.data)
                combined_data.update(session.layer3_result.data)

                layer3_fields = translate_to_form_fields(combined_data)

                event_data = {
                    "status": "layer3_complete",
                    "fields": layer3_fields,
                    "duration_ms": session.layer3_result.duration_ms,
                    "sources": session.layer3_result.sources_called,
                }

                yield f"event: layer3_complete\n"
                yield f"data: {json.dumps(event_data)}\n\n"

                logger.info(f"[FORM ENRICHMENT] Layer 3 complete: {len(layer3_fields)} fields")

            # ================================================================
            # COMPLETE (Save session for Phase 2)
            # ================================================================

            total_duration = int((datetime.now() - start_time).total_seconds() * 1000)

            # Store session in memory for immediate access (Phase 2 reuse)
            from datetime import timedelta
            active_enrichment_sessions[session_id] = {
                "session_id": session_id,
                "website_url": request.website,
                "user_email": request.email,
                "enrichment_data": session.dict(),
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
            }

            # Also save to database for persistence (async, non-blocking)
            try:
                from app.services.enrichment.form_enrichment_cache import FormEnrichmentCache
                cache = FormEnrichmentCache()
                await cache.save_session(
                    session_id=session_id,
                    website_url=request.website,
                    user_email=request.email,
                    enrichment_data=session.dict()
                )
            except Exception as cache_error:
                # Log but don't fail the request
                logger.warning(f"[FORM ENRICHMENT] Failed to save to database: {cache_error}")

            complete_data = {
                "status": "complete",
                "session_id": session_id,
                "total_duration_ms": total_duration,
                "total_cost_usd": session.total_cost_usd,
                "message": "Form enrichment complete. Use session_id for Phase 2 submission."
            }

            yield f"event: complete\n"
            yield f"data: {json.dumps(complete_data)}\n\n"

            logger.info(
                f"[FORM ENRICHMENT] Complete: session_id={session_id}, "
                f"duration={total_duration}ms, cost=${session.total_cost_usd:.4f}"
            )

        except Exception as e:
            # Send error event but don't crash
            logger.error(f"[FORM ENRICHMENT] Error: {str(e)}", exc_info=True)

            error_data = {
                "status": "error",
                "error": str(e),
                "message": "Enrichment failed. Please try again."
            }

            yield f"event: error\n"
            yield f"data: {json.dumps(error_data)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


@router.get("/session/{session_id}",
    summary="Get Cached Form Enrichment Session",
    description="""
    Retrieve cached form enrichment session for Phase 2 submission.

    **Purpose:**
    - Load enrichment data from Phase 1 (form auto-fill)
    - Reuse data in Phase 2 (strategic analysis)
    - Avoid re-scraping same company data

    **Workflow:**
    1. User completes form with auto-filled data
    2. User clicks "Submit" → sends `session_id` from Phase 1
    3. Backend loads cached enrichment data
    4. Backend runs strategic analysis using cached data
    5. Saves time and API costs

    **Returns:**
    - Full enrichment session with all layer data
    - Field translations for form compatibility
    - Cost and duration metrics

    **Example:**
    ```bash
    curl http://localhost:8000/api/form/session/abc-123
    ```
    """,
    responses={
        200: {
            "description": "Cached enrichment session",
            "content": {
                "application/json": {
                    "example": {
                        "session_id": "abc-123",
                        "enrichment_data": {
                            "fields": {"name": "Google", "city": "Mountain View"},
                            "cost": 0.05,
                            "duration_ms": 8500
                        }
                    }
                }
            }
        },
        404: {
            "description": "Session not found or expired",
            "content": {
                "application/json": {
                    "example": {"detail": "Session not found"}
                }
            }
        }
    })
async def get_cached_session(session_id: str):
    """
    Get cached form enrichment session for reuse in strategic analysis.

    Returns full enrichment data to avoid re-scraping.
    """
    # Check in-memory cache first (fast)
    if session_id in active_enrichment_sessions:
        logger.info(f"[FORM ENRICHMENT] Session retrieved from memory: {session_id}")
        return active_enrichment_sessions[session_id]

    # Fallback to database (slower but persistent)
    try:
        from app.services.enrichment.form_enrichment_cache import FormEnrichmentCache
        cache = FormEnrichmentCache()
        enrichment_data = await cache.load_session(session_id)

        if enrichment_data:
            # Reconstruct session format
            session_data = {
                "session_id": session_id,
                "enrichment_data": enrichment_data,
                "created_at": datetime.now().isoformat(),
            }
            # Cache in memory for subsequent requests
            active_enrichment_sessions[session_id] = session_data

            logger.info(f"[FORM ENRICHMENT] Session retrieved from database: {session_id}")
            return session_data
    except Exception as e:
        logger.error(f"[FORM ENRICHMENT] Database lookup failed: {e}", exc_info=True)

    # Session not found in either memory or database
    raise HTTPException(
        status_code=404,
        detail="Session not found or expired. Please re-enrich."
    )


@router.get("/health",
    summary="Form Enrichment Health Check",
    description="Check if form enrichment service is operational")
async def health_check():
    """Health check for form enrichment service"""
    return {
        "status": "healthy",
        "service": "form-enrichment",
        "active_sessions": len(active_enrichment_sessions),
        "timestamp": datetime.now().isoformat()
    }
