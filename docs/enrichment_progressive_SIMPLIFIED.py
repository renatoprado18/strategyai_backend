"""
Progressive Enrichment API Routes - SIMPLIFIED VERSION

Provides real-time progressive enrichment with Server-Sent Events (SSE).
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
from app.services.enrichment.validators import validate_url
from app.core.constants import FIELD_TRANSLATION_MAP

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/enrichment/progressive", tags=["Progressive Enrichment"])

# Session storage (use Redis in production)
active_sessions: Dict[str, ProgressiveEnrichmentSession] = {}

# Constants
MAX_WAIT_SECONDS = 30
POLL_INTERVAL = 0.5


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================


class ProgressiveEnrichmentRequest(BaseModel):
    """Request to start progressive enrichment"""
    website_url: str = Field(..., description="Company website URL")
    user_email: Optional[str] = Field(None, description="User's email")
    existing_data: Optional[Dict[str, Any]] = None

    @validator("website_url")
    def validate_website(cls, v):
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


# ============================================================================
# FIELD TRANSLATION
# ============================================================================


def translate_fields_for_frontend(backend_data: Dict[str, Any]) -> Dict[str, Any]:
    """Translate backend snake_case fields to frontend camelCase."""
    return {FIELD_TRANSLATION_MAP.get(k, k): v for k, v in backend_data.items()}


# ============================================================================
# SSE HELPERS
# ============================================================================


def format_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """Format Server-Sent Event message."""
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def wait_for_session(session_id: str, timeout: int) -> Optional[ProgressiveEnrichmentSession]:
    """Wait for session to be created or return None on timeout."""
    elapsed = 0
    while session_id not in active_sessions and elapsed < timeout:
        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL
    return active_sessions.get(session_id)


# ============================================================================
# ROUTES
# ============================================================================


@router.post("/start", response_model=ProgressiveEnrichmentResponse)
async def start_progressive_enrichment(
    request: ProgressiveEnrichmentRequest,
    background_tasks: BackgroundTasks
):
    """Start progressive enrichment and return SSE stream URL."""
    try:
        import uuid
        session_id = str(uuid.uuid4())

        # Create placeholder session
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

        # Start enrichment in background
        async def run_enrichment():
            try:
                orchestrator = ProgressiveEnrichmentOrchestrator()
                session = await orchestrator.enrich_progressive(
                    website_url=request.website_url,
                    user_email=request.user_email,
                    existing_data=request.existing_data
                )
                session.session_id = session_id
                active_sessions[session_id] = session
                logger.info(f"Progressive enrichment complete: {session_id}")

            except Exception as e:
                logger.error(f"Progressive enrichment had issues: {str(e)}", exc_info=True)
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
        logger.error(f"Failed to start progressive enrichment: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stream/{session_id}")
async def stream_progressive_enrichment(session_id: str):
    """Server-Sent Events stream for progressive enrichment updates."""

    async def event_stream():
        # Wait for session creation
        session = await wait_for_session(session_id, MAX_WAIT_SECONDS)
        if not session:
            yield format_sse_event("error", {"error": "Session not found"})
            return

        last_status = None

        # Stream progressive updates
        for _ in range(int(MAX_WAIT_SECONDS / POLL_INTERVAL)):
            current_status = session.status

            # Send update if status changed
            if current_status != last_status:
                if current_status == "layer1_complete":
                    yield format_sse_event("layer1_complete", {
                        "status": "layer1_complete",
                        "fields": translate_fields_for_frontend(session.fields_auto_filled),
                        "confidence_scores": session.confidence_scores,
                        "layer_result": session.layer1_result.dict() if session.layer1_result else {}
                    })

                elif current_status == "layer2_complete":
                    yield format_sse_event("layer2_complete", {
                        "status": "layer2_complete",
                        "fields": translate_fields_for_frontend(session.fields_auto_filled),
                        "confidence_scores": session.confidence_scores,
                        "layer_result": session.layer2_result.dict() if session.layer2_result else {}
                    })

                elif current_status == "complete":
                    yield format_sse_event("layer3_complete", {
                        "status": "complete",
                        "fields": translate_fields_for_frontend(session.fields_auto_filled),
                        "confidence_scores": session.confidence_scores,
                        "layer_result": session.layer3_result.dict() if session.layer3_result else {},
                        "total_cost_usd": session.total_cost_usd,
                        "total_duration_ms": session.total_duration_ms
                    })
                    del active_sessions[session_id]
                    return

                last_status = current_status

            await asyncio.sleep(POLL_INTERVAL)

        yield format_sse_event("timeout", {"error": "Enrichment timeout"})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/session/{session_id}")
async def get_session_status(session_id: str):
    """Get current status of enrichment session (non-streaming)."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = active_sessions[session_id]
    return {
        "session_id": session.session_id,
        "status": session.status,
        "fields_auto_filled": translate_fields_for_frontend(session.fields_auto_filled),
        "confidence_scores": session.confidence_scores,
        "total_cost_usd": session.total_cost_usd,
        "total_duration_ms": session.total_duration_ms
    }


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions),
        "timestamp": datetime.now().isoformat()
    }
