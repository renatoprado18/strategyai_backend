"""
Enrichment Edit Tracking API - Phase 6 User Learning

This module provides endpoints for tracking user edits and learning patterns:
- Track when user edits auto-filled fields
- Get learning insights from user behavior
- Adjust confidence scores based on edit frequency
- Identify fields needing improvement

Combines admin endpoints (learning patterns) and public endpoints (edit tracking).

Created: 2025-01-09
Version: 1.0.0
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime
import logging

from app.routes.auth import RequireAuth
from app.repositories import progressive_enrichment_repository as repo

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/enrichment", tags=["enrichment-learning"])


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class EditTrackingRequest(BaseModel):
    """User edit tracking request"""
    field_name: str
    original_value: Optional[str] = None
    edited_value: str
    confidence: Optional[float] = None

    class Config:
        json_schema_extra = {
            "example": {
                "field_name": "company_name",
                "original_value": "TechStart Inc",
                "edited_value": "TechStart Innovations",
                "confidence": 92.5
            }
        }


class EditTrackingResponse(BaseModel):
    """Edit tracking response"""
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]


class LearningPatternsResponse(BaseModel):
    """Learning patterns response"""
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]


# ============================================================================
# PUBLIC ENDPOINTS (No Auth Required)
# ============================================================================

@router.post("/sessions/{session_id}/edit", response_model=EditTrackingResponse,
    summary="Track User Edit",
    description="""
    Track when a user edits an auto-filled field.

    **Request Body:**
    - `field_name`: Name of the edited field
    - `original_value`: Original auto-filled value (optional)
    - `edited_value`: User's edited value
    - `confidence`: Original confidence score (optional)

    **Response:**
    - Success status
    - Confidence adjustment recommendation
    - Message

    **Use Cases:**
    - Learn from user behavior
    - Improve auto-fill accuracy
    - Adjust confidence thresholds
    - Quality feedback loop

    **Authentication:** None required (public endpoint)
    """)
async def track_edit(
    session_id: str,
    edit: EditTrackingRequest
):
    """Track user edit of auto-filled field"""
    start_time = datetime.now()

    try:
        logger.info(
            f"Tracking edit for session {session_id}, field {edit.field_name}",
            extra={
                "session_id": session_id,
                "field_name": edit.field_name,
                "had_original": edit.original_value is not None
            }
        )

        # Track the edit
        result = await repo.track_user_edit(
            session_id=session_id,
            field_name=edit.field_name,
            original_value=edit.original_value,
            edited_value=edit.edited_value,
            confidence=edit.confidence
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Failed to track edit")
            )

        query_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return EditTrackingResponse(
            success=True,
            data=result,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "query_time_ms": query_time_ms
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to track edit: {str(e)}",
            exc_info=True,
            extra={"session_id": session_id, "field_name": edit.field_name}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to track edit: {str(e)}"
        )


# ============================================================================
# ADMIN ENDPOINTS (Auth Required)
# ============================================================================

@router.get("/learning/patterns", response_model=LearningPatternsResponse,
    summary="Get Learning Insights",
    description="""
    Get learning insights from user edits (Admin only).

    **Insights Per Field:**
    - Total user interactions
    - Edit rate (%)
    - Accept rate (%)
    - Average confidence score
    - High-confidence edits (problematic)
    - Recommended confidence threshold
    - Needs improvement flag

    **Query Parameters:**
    - `days`: Number of days to analyze (default: 30)

    **Use Cases:**
    - Identify underperforming fields
    - Tune confidence thresholds
    - Improve data quality
    - Machine learning feedback

    **Response Sorted By:**
    Edit rate (highest first = needs most attention)

    **Authentication:** Admin token required
    """)
async def get_learning_patterns(
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    current_user: dict = RequireAuth
):
    """Get learning insights from user edits"""
    start_time = datetime.now()

    try:
        logger.info(
            f"User {current_user['email']} requesting learning patterns ({days} days)",
            extra={"user": current_user["email"], "days": days}
        )

        # Get learning patterns
        data = await repo.get_learning_patterns(days=days)

        if "error" in data:
            raise HTTPException(
                status_code=500,
                detail=data["error"]
            )

        query_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return LearningPatternsResponse(
            success=True,
            data=data,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "query_time_ms": query_time_ms
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get learning patterns: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get learning patterns: {str(e)}"
        )
