"""
Enrichment Analytics API - Phase 5 Progressive Enrichment

This module provides analytics endpoints for the progressive enrichment system:
- Dashboard overview metrics (last 30 days)
- Cost trends and breakdown by source
- Layer performance metrics
- Field auto-fill success rates
- Cache hit rates and effectiveness

All endpoints require admin authentication.

Created: 2025-01-09
Version: 1.0.0
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime
import logging

from app.routes.auth import RequireAuth
from app.repositories import progressive_enrichment_repository as repo

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/enrichment/analytics", tags=["enrichment-analytics"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class AnalyticsResponse(BaseModel):
    """Standard analytics response"""
    success: bool
    data: Dict[str, Any]
    metadata: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"metric": "value"},
                "metadata": {
                    "timestamp": "2025-01-09T10:00:00Z",
                    "query_time_ms": 123
                }
            }
        }


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@router.get("/overview", response_model=AnalyticsResponse,
    summary="Get Analytics Dashboard Overview",
    description="""
    Get comprehensive dashboard metrics for the last 30 days.

    **Metrics Provided:**
    - Total enrichment sessions
    - Total cost spent (USD)
    - Average processing duration
    - Status distribution (pending/complete/error)
    - Layer completion rates (Layer 1, 2, 3)

    **Use Cases:**
    - Admin dashboard overview
    - System health monitoring
    - Usage trend analysis

    **Authentication:** Admin token required
    """)
async def get_overview_analytics(
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    current_user: dict = RequireAuth
):
    """Get dashboard overview analytics"""
    start_time = datetime.now()

    try:
        logger.info(
            f"User {current_user['email']} requesting overview analytics ({days} days)",
            extra={"user": current_user["email"], "days": days}
        )

        # Get overview analytics
        data = await repo.get_overview_analytics(days=days)

        query_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return AnalyticsResponse(
            success=True,
            data=data,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "query_time_ms": query_time_ms
            }
        )

    except Exception as e:
        logger.error(
            f"Failed to get overview analytics: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get overview analytics: {str(e)}"
        )


@router.get("/costs", response_model=AnalyticsResponse,
    summary="Get Cost Trends and Breakdown",
    description="""
    Get cost analytics including trends and source breakdown.

    **Metrics Provided:**
    - Total cost (USD) for period
    - Average daily cost
    - Daily cost trend (time series)
    - Cost breakdown by data source

    **Use Cases:**
    - Budget tracking
    - Cost optimization
    - Source cost analysis
    - Financial reporting

    **Authentication:** Admin token required
    """)
async def get_cost_analytics(
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    current_user: dict = RequireAuth
):
    """Get cost trends and breakdown"""
    start_time = datetime.now()

    try:
        logger.info(
            f"User {current_user['email']} requesting cost analytics ({days} days)",
            extra={"user": current_user["email"], "days": days}
        )

        # Get cost analytics
        data = await repo.get_cost_analytics(days=days)

        query_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return AnalyticsResponse(
            success=True,
            data=data,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "query_time_ms": query_time_ms
            }
        )

    except Exception as e:
        logger.error(
            f"Failed to get cost analytics: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cost analytics: {str(e)}"
        )


@router.get("/performance", response_model=AnalyticsResponse,
    summary="Get Layer Performance Metrics",
    description="""
    Get performance metrics for each enrichment layer (1, 2, 3).

    **Metrics Per Layer:**
    - Average duration (ms)
    - Min/max duration
    - Average cost (USD)
    - Completion count
    - Completion rate (%)

    **Use Cases:**
    - Performance optimization
    - Bottleneck identification
    - SLA monitoring
    - Layer comparison

    **Authentication:** Admin token required
    """)
async def get_performance_analytics(
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    current_user: dict = RequireAuth
):
    """Get layer performance metrics"""
    start_time = datetime.now()

    try:
        logger.info(
            f"User {current_user['email']} requesting performance analytics ({days} days)",
            extra={"user": current_user["email"], "days": days}
        )

        # Get performance analytics
        data = await repo.get_performance_analytics(days=days)

        query_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return AnalyticsResponse(
            success=True,
            data=data,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "query_time_ms": query_time_ms
            }
        )

    except Exception as e:
        logger.error(
            f"Failed to get performance analytics: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get performance analytics: {str(e)}"
        )


@router.get("/fields", response_model=AnalyticsResponse,
    summary="Get Field Auto-Fill Success Rates",
    description="""
    Get success rates for auto-filled form fields.

    **Metrics Per Field:**
    - Total suggestions made
    - Acceptance count and rate (%)
    - Edit count and rate (%)
    - Auto-fill count and rate (%)
    - Average confidence score

    **Use Cases:**
    - Field optimization
    - Confidence threshold tuning
    - User experience improvement
    - Form design insights

    **Authentication:** Admin token required
    """)
async def get_field_analytics(
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    current_user: dict = RequireAuth
):
    """Get field auto-fill success rates"""
    start_time = datetime.now()

    try:
        logger.info(
            f"User {current_user['email']} requesting field analytics ({days} days)",
            extra={"user": current_user["email"], "days": days}
        )

        # Get field analytics
        data = await repo.get_field_analytics(days=days)

        query_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return AnalyticsResponse(
            success=True,
            data=data,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "query_time_ms": query_time_ms
            }
        )

    except Exception as e:
        logger.error(
            f"Failed to get field analytics: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get field analytics: {str(e)}"
        )


@router.get("/cache", response_model=AnalyticsResponse,
    summary="Get Cache Hit Rates and Effectiveness",
    description="""
    Get cache performance metrics for social media validation.

    **Metrics Provided:**
    - Total cache entries
    - Valid entries count
    - Validation rate (%)
    - Per-platform statistics (Instagram, TikTok, LinkedIn)

    **Use Cases:**
    - Cache effectiveness monitoring
    - Platform-specific performance
    - Validation quality tracking
    - TTL optimization

    **Authentication:** Admin token required
    """)
async def get_cache_analytics(
    days: int = Query(30, ge=1, le=90, description="Number of days to analyze"),
    current_user: dict = RequireAuth
):
    """Get cache hit rates and effectiveness"""
    start_time = datetime.now()

    try:
        logger.info(
            f"User {current_user['email']} requesting cache analytics ({days} days)",
            extra={"user": current_user["email"], "days": days}
        )

        # Get cache analytics
        data = await repo.get_cache_analytics(days=days)

        query_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        return AnalyticsResponse(
            success=True,
            data=data,
            metadata={
                "timestamp": datetime.now().isoformat(),
                "query_time_ms": query_time_ms
            }
        )

    except Exception as e:
        logger.error(
            f"Failed to get cache analytics: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache analytics: {str(e)}"
        )
