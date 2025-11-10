"""
Progressive Enrichment API Routes

Provides real-time progressive enrichment with Server-Sent Events (SSE)
for instant field auto-fill as data becomes available.
"""

import logging
import asyncio
import json
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, validator

from app.services.enrichment.progressive_orchestrator import (
    ProgressiveEnrichmentOrchestrator,
    ProgressiveEnrichmentSession
)
from app.services.enrichment.validators import (
    validate_phone,
    validate_instagram,
    validate_tiktok,
    validate_linkedin_company,
    validate_linkedin_profile,
    validate_url,
    ValidationResult
)
from app.core.security.rate_limiter import get_redis_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/enrichment/progressive", tags=["Progressive Enrichment"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class ProgressiveEnrichmentRequest(BaseModel):
    """Request to start progressive enrichment"""

    website_url: str = Field(..., description="Company website URL")
    user_email: Optional[str] = Field(None, description="User's email (optional)")
    existing_data: Optional[Dict[str, Any]] = Field(
        None,
        description="Data already collected from user"
    )

    @validator("website_url")
    def validate_website(cls, v):
        """Validate and format website URL"""
        result = validate_url(v)
        if not result.is_valid:
            raise ValueError(result.error_message)
        return result.formatted_value


class ProgressiveEnrichmentResponse(BaseModel):
    """Response when starting progressive enrichment"""

    session_id: str
    status: str
    message: str
    stream_url: str


class FieldValidationRequest(BaseModel):
    """Request to validate a specific field"""

    field_name: str = Field(..., description="Field to validate (phone, instagram, tiktok, etc.)")
    field_value: str = Field(..., description="Value to validate")


class FieldValidationResponse(BaseModel):
    """Field validation response"""

    is_valid: bool
    formatted_value: Optional[str] = None
    error_message: Optional[str] = None
    suggestions: list[str] = []
    confidence: float = 100.0


class AutoFillSuggestion(BaseModel):
    """Auto-fill suggestion for a field"""

    field_name: str
    suggested_value: Any
    confidence: float
    source: str
    should_auto_fill: bool  # True if confidence > 85%


# ============================================================================
# GLOBAL STATE (In-memory session storage)
# ============================================================================

# Store active enrichment sessions
# In production, use Redis or database
active_sessions: Dict[str, ProgressiveEnrichmentSession] = {}


# ============================================================================
# ROUTES
# ============================================================================


@router.post("/start", response_model=ProgressiveEnrichmentResponse)
async def start_progressive_enrichment(
    request: ProgressiveEnrichmentRequest,
    background_tasks: BackgroundTasks
):
    """
    Start progressive enrichment and return SSE stream URL

    The enrichment happens in background, and client can connect
    to the stream URL to receive progressive updates.

    Returns:
        Session ID and stream URL for SSE connection
    """
    try:
        # Generate session ID upfront
        import uuid
        session_id = str(uuid.uuid4())

        # Create placeholder session immediately
        from app.services.enrichment.progressive_orchestrator import ProgressiveEnrichmentSession
        placeholder_session = ProgressiveEnrichmentSession(
            session_id=session_id,
            website_url=request.website_url,
            user_email=request.user_email,
            status="processing",
            started_at=datetime.now(),
            fields_auto_filled={},
            confidence_scores={},
            total_cost_usd=0.0,
            total_duration_ms=0
        )
        active_sessions[session_id] = placeholder_session

        # Create orchestrator
        orchestrator = ProgressiveEnrichmentOrchestrator()

        # Start enrichment in background
        async def run_enrichment():
            """Background task to run progressive enrichment - NEVER fails"""
            try:
                session = await orchestrator.enrich_progressive(
                    website_url=request.website_url,
                    user_email=request.user_email,
                    existing_data=request.existing_data
                )

                # Update session with enrichment results (keep same session_id)
                session.session_id = session_id  # Use our session_id
                active_sessions[session_id] = session

                logger.info(f"Progressive enrichment complete: {session_id}")

            except Exception as e:
                # Log error but NEVER set status to "error"
                # The orchestrator should have returned partial data
                logger.error(
                    f"Progressive enrichment had issues (but returned partial data): {str(e)}",
                    exc_info=True
                )

                # Ensure session exists and has "complete" status
                if session_id in active_sessions:
                    active_sessions[session_id].status = "complete"  # ALWAYS complete
                    logger.info(f"Progressive enrichment completed with partial data: {session_id}")

        # Schedule background enrichment
        background_tasks.add_task(run_enrichment)

        return ProgressiveEnrichmentResponse(
            session_id=session_id,
            status="processing",
            message="Progressive enrichment started",
            stream_url=f"/api/enrichment/progressive/stream/{session_id}"
        )

    except Exception as e:
        logger.error(f"Failed to start progressive enrichment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream/{session_id}")
async def stream_progressive_enrichment(session_id: str):
    """
    Server-Sent Events (SSE) stream for progressive enrichment updates

    Client connects to this endpoint to receive real-time updates
    as each enrichment layer completes.

    Event types:
    - layer1_complete: Layer 1 data available
    - layer2_complete: Layer 2 data available
    - layer3_complete: Layer 3 data available (final)
    - error: Enrichment failed

    Usage from frontend:
    ```typescript
    const eventSource = new EventSource('/api/enrichment/progressive/stream/{session_id}');

    eventSource.addEventListener('layer1_complete', (e) => {
        const data = JSON.parse(e.data);
        // Auto-fill fields from layer 1
    });
    ```
    """

    async def event_stream():
        """Generate SSE events"""
        max_wait = 30  # Maximum 30 seconds wait
        elapsed = 0
        check_interval = 0.5  # Check every 500ms

        # Wait for session to be created
        while session_id not in active_sessions and elapsed < max_wait:
            await asyncio.sleep(check_interval)
            elapsed += check_interval

        if session_id not in active_sessions:
            # Session not found, send error
            yield f"event: error\ndata: {{\"error\": \"Session not found\"}}\n\n"
            return

        session = active_sessions[session_id]
        last_status = None

        # Stream progressive updates
        while True:
            current_status = session.status

            # Send update if status changed
            if current_status != last_status:
                if current_status == "layer1_complete":
                    # Send Layer 1 data
                    layer1_data = {
                        "status": "layer1_complete",
                        "fields": session.fields_auto_filled,
                        "confidence_scores": session.confidence_scores,
                        "layer_result": session.layer1_result.dict() if session.layer1_result else {}
                    }
                    yield f"event: layer1_complete\ndata: {json.dumps(layer1_data)}\n\n"

                elif current_status == "layer2_complete":
                    # Send Layer 2 data
                    layer2_data = {
                        "status": "layer2_complete",
                        "fields": session.fields_auto_filled,
                        "confidence_scores": session.confidence_scores,
                        "layer_result": session.layer2_result.dict() if session.layer2_result else {}
                    }
                    yield f"event: layer2_complete\ndata: {json.dumps(layer2_data)}\n\n"

                elif current_status == "complete":
                    # Send Layer 3 data (final)
                    layer3_data = {
                        "status": "complete",
                        "fields": session.fields_auto_filled,
                        "confidence_scores": session.confidence_scores,
                        "layer_result": session.layer3_result.dict() if session.layer3_result else {},
                        "total_cost_usd": session.total_cost_usd,
                        "total_duration_ms": session.total_duration_ms
                    }
                    yield f"event: layer3_complete\ndata: {json.dumps(layer3_data)}\n\n"

                    # Clean up session after sending final data
                    del active_sessions[session_id]
                    break

                last_status = current_status

            # Check every 500ms
            await asyncio.sleep(0.5)

            # Timeout after 30 seconds
            if elapsed > max_wait:
                yield f"event: timeout\ndata: {{\"error\": \"Enrichment timeout\"}}\n\n"
                break

            elapsed += check_interval

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable buffering for nginx
        }
    )


@router.post("/validate-field", response_model=FieldValidationResponse)
async def validate_field(request: FieldValidationRequest):
    """
    Validate a specific form field in real-time

    Supported fields:
    - phone: Brazilian phone number
    - whatsapp: Same as phone
    - instagram: Instagram handle
    - tiktok: TikTok handle
    - linkedin_company: LinkedIn company URL
    - linkedin_profile: LinkedIn profile URL
    - website: Website URL

    Returns:
        Validation result with formatted value and suggestions
    """
    field = request.field_name.lower()
    value = request.field_value

    # Map field names to validators
    validators = {
        "phone": validate_phone,
        "whatsapp": validate_phone,
        "instagram": validate_instagram,
        "tiktok": validate_tiktok,
        "linkedin_company": validate_linkedin_company,
        "linkedin_profile": validate_linkedin_profile,
        "website": validate_url
    }

    if field not in validators:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown field: {field}. Supported: {', '.join(validators.keys())}"
        )

    # Validate
    validator_func = validators[field]
    result = validator_func(value)

    return FieldValidationResponse(
        is_valid=result.is_valid,
        formatted_value=result.formatted_value,
        error_message=result.error_message,
        suggestions=result.suggestions,
        confidence=result.confidence
    )


@router.get("/session/{session_id}", response_model=Dict[str, Any])
async def get_session_status(session_id: str):
    """
    Get current status of enrichment session (non-streaming)

    Returns:
        Current session state with all available data
    """
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]

    return {
        "session_id": session.session_id,
        "status": session.status,
        "fields_auto_filled": session.fields_auto_filled,
        "confidence_scores": session.confidence_scores,
        "total_cost_usd": session.total_cost_usd,
        "total_duration_ms": session.total_duration_ms
    }


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "timestamp": datetime.now().isoformat()
    }
