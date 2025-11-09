"""
Progressive Enrichment Admin API - Phase 2 Admin Transparency

This module provides admin transparency endpoints for progressive enrichment:
- List all enrichment sessions with pagination
- Get detailed session data with full attribution
- Field-by-field source attribution
- Cost breakdown, confidence scores, cache hit/miss
- Duration metrics per layer

All endpoints require admin authentication.

Created: 2025-01-09
Version: 1.0.0
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from app.routes.auth import RequireAuth
from app.repositories import progressive_enrichment_repository as repo

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/enrichment/admin", tags=["progressive-enrichment-admin"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class SessionListResponse(BaseModel):
    """List of enrichment sessions"""
    success: bool
    data: List[Dict[str, Any]]
    metadata: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": [
                    {
                        "session_id": "123e4567-e89b-12d3-a456-426614174000",
                        "website_url": "https://techstart.com",
                        "status": "complete",
                        "total_cost_usd": 0.25,
                        "total_duration_ms": 5400,
                        "created_at": "2025-01-09T10:00:00Z"
                    }
                ],
                "metadata": {
                    "timestamp": "2025-01-09T11:00:00Z",
                    "query_time_ms": 45,
                    "total_count": 150,
                    "page": 1,
                    "limit": 20
                }
            }
        }


class SessionDetailResponse(BaseModel):
    """Detailed session data"""
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]


class AttributionResponse(BaseModel):
    """Field-by-field source attribution"""
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/sessions", response_model=SessionListResponse,
    summary="List All Enrichment Sessions",
    description="""
    Get paginated list of all enrichment sessions.

    **Query Parameters:**
    - `limit`: Records per page (default: 20, max: 100)
    - `offset`: Pagination offset (default: 0)
    - `status`: Filter by status (optional)

    **Response Includes:**
    - Session ID and website URL
    - Status (pending/layer1_complete/layer2_complete/complete/error)
    - Cost and duration metrics
    - Layer completion timestamps

    **Metadata:**
    - Total count of sessions
    - Current page and limit
    - Query execution time

    **Authentication:** Admin token required
    """)
async def list_sessions(
    limit: int = Query(20, ge=1, le=100, description="Records per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: dict = RequireAuth
):
    """List all enrichment sessions with pagination"""
    start_time = datetime.now()

    try:
        logger.info(
            f"User {current_user['email']} listing enrichment sessions",
            extra={
                "user": current_user["email"],
                "limit": limit,
                "offset": offset,
                "status": status
            }
        )

        # Get sessions
        sessions = await repo.get_all_sessions(
            limit=limit,
            offset=offset,
            status=status
        )

        # Get total count
        total_count = await repo.count_sessions(status=status)

        query_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return SessionListResponse(
            success=True,
            data=sessions,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "query_time_ms": query_time_ms,
                "total_count": total_count,
                "page": (offset // limit) + 1 if limit > 0 else 1,
                "limit": limit
            }
        )

    except Exception as e:
        logger.error(
            f"Failed to list sessions: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sessions: {str(e)}"
        )


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse,
    summary="Get Detailed Session Data",
    description="""
    Get comprehensive session data including all layers and metrics.

    **Response Includes:**
    - Full session metadata
    - Layer 1, 2, 3 enrichment data (JSONB)
    - Performance metrics per layer
    - Cost breakdown per layer
    - Fields auto-filled and confidence scores
    - User edits tracking

    **Use Cases:**
    - Debug enrichment issues
    - Verify data quality
    - Analyze layer performance
    - Cost transparency

    **Authentication:** Admin token required
    """)
async def get_session_detail(
    session_id: str,
    current_user: dict = RequireAuth
):
    """Get detailed session data"""
    start_time = datetime.now()

    try:
        logger.info(
            f"User {current_user['email']} viewing session {session_id}",
            extra={"user": current_user["email"], "session_id": session_id}
        )

        # Get session
        session = await repo.get_session_by_id(session_id)

        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found"
            )

        query_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return SessionDetailResponse(
            success=True,
            data=session,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "query_time_ms": query_time_ms
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get session detail: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"], "session_id": session_id}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session detail: {str(e)}"
        )


@router.get("/sessions/{session_id}/attribution", response_model=AttributionResponse,
    summary="Get Field-by-Field Source Attribution",
    description="""
    Get detailed source attribution for each auto-filled field.

    **Response Includes Per Field:**
    - Source name (e.g., "Clearbit", "LinkedIn", "AI inference")
    - Layer number (1, 2, or 3)
    - Confidence score (0-100)
    - Was accepted by user (boolean)
    - Was edited by user (boolean)

    **Use Cases:**
    - Data transparency
    - Source accuracy tracking
    - Compliance requirements
    - Quality verification

    **Authentication:** Admin token required
    """)
async def get_session_attribution(
    session_id: str,
    current_user: dict = RequireAuth
):
    """Get field-by-field source attribution"""
    start_time = datetime.now()

    try:
        logger.info(
            f"User {current_user['email']} viewing attribution for session {session_id}",
            extra={"user": current_user["email"], "session_id": session_id}
        )

        # Get attribution
        attribution = await repo.get_session_attribution(session_id)

        if "error" in attribution:
            raise HTTPException(
                status_code=404,
                detail=attribution["error"]
            )

        query_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return AttributionResponse(
            success=True,
            data=attribution,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "query_time_ms": query_time_ms
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get session attribution: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"], "session_id": session_id}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get session attribution: {str(e)}"
        )
