"""
Enrichment Admin Routes - Dashboard and Management Endpoints

This module contains admin-only routes for the IMENSIAH enrichment system:
- Dashboard statistics and analytics
- Enrichment history and search
- Cost tracking and optimization metrics
- Audit trail viewing
- Source performance monitoring
- Cache management

All endpoints require admin authentication via JWT token.

Created: 2025-01-09
Version: 1.0.0
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from app.routes.auth import RequireAuth
from app.repositories import enrichment_repository, audit_repository
from app.services.enrichment import EnrichmentAnalytics

logger = logging.getLogger(__name__)

# Create router with admin prefix
router = APIRouter(prefix="/api/admin/enrichment", tags=["enrichment-admin"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class DashboardStatsResponse(BaseModel):
    """Dashboard overview statistics"""
    success: bool
    data: Dict[str, Any]

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "total_enrichments": 1247,
                    "cache_hit_rate": 62.5,
                    "total_cost_usd": 720.00,
                    "total_savings_usd": 1080.00,
                    "avg_completeness": 87.3,
                    "avg_confidence": 84.1,
                    "by_quality_tier": {
                        "excellent": 543,
                        "high": 412,
                        "moderate": 234,
                        "minimal": 58
                    },
                    "by_type": {
                        "quick": 1247,
                        "deep": 1247
                    }
                }
            }
        }


class EnrichmentListResponse(BaseModel):
    """List of enrichments"""
    success: bool
    data: List[Dict[str, Any]]
    total: int


class AuditTrailResponse(BaseModel):
    """Audit trail for enrichment"""
    success: bool
    data: Dict[str, Any]


# ============================================================================
# DASHBOARD ENDPOINTS
# ============================================================================

@router.get("/dashboard/stats", response_model=DashboardStatsResponse,
    summary="Get Enrichment Dashboard Statistics",
    description="""
    Retrieve comprehensive enrichment statistics for the admin dashboard (Admin only).

    **Metrics Provided:**

    1. **Overview Statistics:**
       - Total enrichments performed
       - Cache hit rate (percentage)
       - Total cost spent (USD)
       - Total cost saved by caching (USD)
       - Average completeness score
       - Average confidence score

    2. **Quality Distribution:**
       - Count by quality tier (minimal/moderate/high/excellent)
       - Helps identify data quality trends

    3. **Enrichment Types:**
       - Quick enrichments (free, 2-3s)
       - Deep enrichments (paid, 30s+)

    4. **Cost Analysis:**
       - Total API costs ($0.15 per deep enrichment)
       - Cache savings (60% hit rate = $1,080/year saved)
       - ROI of caching strategy

    **Use Cases:**
    - Monitor enrichment effectiveness
    - Track API cost spending
    - Calculate ROI of caching
    - Identify quality improvement opportunities
    - Budget planning and forecasting

    **Response Structure:**
    ```json
    {
      "success": true,
      "data": {
        "total_enrichments": 1247,
        "cache_hit_rate": 62.5,
        "total_cost_usd": 720.00,
        "total_savings_usd": 1080.00,
        "avg_completeness": 87.3,
        "avg_confidence": 84.1,
        "by_quality_tier": {
          "excellent": 543,
          "high": 412,
          "moderate": 234,
          "minimal": 58
        }
      }
    }
    ```

    **Authentication:**
    - Requires valid JWT token in Authorization header
    - Admin privileges required

    **Example:**
    ```bash
    curl -X GET https://api.example.com/api/admin/enrichment/dashboard/stats \\
      -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    ```
    """,
    responses={
        200: {
            "description": "Dashboard statistics retrieved successfully",
        },
        401: {
            "description": "Unauthorized - invalid or missing token",
        },
        403: {
            "description": "Forbidden - admin privileges required",
        }
    })
async def get_dashboard_stats(current_user: dict = RequireAuth):
    """Get enrichment dashboard statistics"""
    try:
        logger.info(
            f"User {current_user['email']} accessing enrichment dashboard stats",
            extra={"user_id": current_user["sub"], "email": current_user["email"]}
        )

        # Get statistics from repository
        stats = await enrichment_repository.get_statistics()

        return DashboardStatsResponse(
            success=True,
            data=stats
        )

    except Exception as e:
        logger.error(
            f"Failed to get dashboard stats: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get dashboard statistics: {str(e)}"
        )


@router.get("/dashboard/analytics", response_model=DashboardStatsResponse,
    summary="Get Advanced Analytics",
    description="""
    Get advanced analytics including source-level performance metrics (Admin only).

    **Metrics Provided:**

    1. **Source Performance:**
       - Success rate per source
       - Average duration per source
       - Cost breakdown by source
       - Circuit breaker status

    2. **Monthly Cost Tracking:**
       - Cost per month for last 12 months
       - Cost trends and projections

    3. **Cache Performance:**
       - Hit rate by source type
       - Cache effectiveness score
       - Savings calculation

    **Authentication:** Requires admin token
    """)
async def get_advanced_analytics(current_user: dict = RequireAuth):
    """Get advanced enrichment analytics"""
    try:
        logger.info(
            f"User {current_user['email']} accessing enrichment analytics",
            extra={"user": current_user["email"]}
        )

        # Initialize analytics
        analytics = EnrichmentAnalytics()

        # Get all source statistics
        all_source_stats = await analytics.get_all_source_stats()

        # Get monthly cost for last 12 months
        monthly_costs = []
        for i in range(12):
            start = datetime.now() - timedelta(days=30 * (i + 1))
            end = datetime.now() - timedelta(days=30 * i)
            cost_data = await analytics.get_monthly_cost(start.month, start.year)
            monthly_costs.append({
                "month": start.strftime("%Y-%m"),
                "cost_usd": cost_data.total_cost_usd,
                "enrichments": cost_data.total_enrichments
            })

        return DashboardStatsResponse(
            success=True,
            data={
                "source_performance": all_source_stats,
                "monthly_costs": monthly_costs,
                "summary": {
                    "total_sources": len(all_source_stats),
                    "healthy_sources": sum(
                        1 for s in all_source_stats
                        if s.get("success_rate", 0) > 0.95
                    )
                }
            }
        )

    except Exception as e:
        logger.error(
            f"Failed to get analytics: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get analytics: {str(e)}"
        )


# ============================================================================
# ENRICHMENT MANAGEMENT
# ============================================================================

@router.get("/list", response_model=EnrichmentListResponse,
    summary="List Recent Enrichments",
    description="""
    Get list of recent enrichments with filtering options (Admin only).

    **Query Parameters:**
    - `limit`: Maximum records to return (default: 20, max: 100)
    - `enrichment_type`: Filter by type ("quick" or "deep")

    **Response Fields:**
    - Domain
    - Completeness score
    - Quality tier
    - Cost
    - Cache hits
    - Created timestamp

    **Authentication:** Requires admin token
    """)
async def list_enrichments(
    limit: int = Query(20, ge=1, le=100, description="Maximum records to return"),
    enrichment_type: Optional[str] = Query(None, description="Filter by type"),
    current_user: dict = RequireAuth
):
    """Get list of recent enrichments"""
    try:
        logger.info(
            f"User {current_user['email']} listing enrichments",
            extra={"user": current_user["email"], "limit": limit}
        )

        # Get recent enrichments
        enrichments = await enrichment_repository.get_recent_enrichments(
            limit=limit,
            enrichment_type=enrichment_type
        )

        return EnrichmentListResponse(
            success=True,
            data=enrichments,
            total=len(enrichments)
        )

    except Exception as e:
        logger.error(
            f"Failed to list enrichments: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list enrichments: {str(e)}"
        )


@router.get("/search", response_model=EnrichmentListResponse,
    summary="Search Enrichments by Domain",
    description="""
    Search enrichments by domain pattern (Admin only).

    **Query Parameters:**
    - `query`: Search query (domain pattern)
    - `limit`: Maximum records to return (default: 20)

    **Examples:**
    - `query=techstart` - Find all domains containing "techstart"
    - `query=.com.br` - Find all Brazilian domains

    **Authentication:** Requires admin token
    """)
async def search_enrichments(
    query: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    current_user: dict = RequireAuth
):
    """Search enrichments by domain"""
    try:
        logger.info(
            f"User {current_user['email']} searching enrichments: {query}",
            extra={"user": current_user["email"], "query": query}
        )

        # Search by domain
        enrichments = await enrichment_repository.search_by_domain(
            query=query,
            limit=limit
        )

        return EnrichmentListResponse(
            success=True,
            data=enrichments,
            total=len(enrichments)
        )

    except Exception as e:
        logger.error(
            f"Failed to search enrichments: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"], "query": query}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search enrichments: {str(e)}"
        )


@router.get("/{enrichment_id}", response_model=DashboardStatsResponse,
    summary="Get Enrichment Detail",
    description="""
    Get detailed information for a specific enrichment (Admin only).

    **Response Includes:**
    - Full enrichment data (quick + deep)
    - Source attribution (which source provided each field)
    - Quality metrics (completeness, confidence, tier)
    - Cost breakdown by source
    - Duration metrics
    - Cache information

    **Use Cases:**
    - Debugging enrichment issues
    - Verifying data quality
    - Understanding source attribution
    - Cost analysis per enrichment

    **Authentication:** Requires admin token
    """)
async def get_enrichment_detail(
    enrichment_id: int,
    current_user: dict = RequireAuth
):
    """Get detailed enrichment information"""
    try:
        logger.info(
            f"User {current_user['email']} viewing enrichment {enrichment_id}",
            extra={"user": current_user["email"], "enrichment_id": enrichment_id}
        )

        # Get enrichment
        enrichment = await enrichment_repository.get_by_id(str(enrichment_id))

        if not enrichment:
            raise HTTPException(
                status_code=404,
                detail=f"Enrichment {enrichment_id} not found"
            )

        return DashboardStatsResponse(
            success=True,
            data=enrichment
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get enrichment detail: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"], "enrichment_id": enrichment_id}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get enrichment detail: {str(e)}"
        )


# ============================================================================
# AUDIT TRAIL
# ============================================================================

@router.get("/{enrichment_id}/audit", response_model=AuditTrailResponse,
    summary="Get Enrichment Audit Trail",
    description="""
    Get complete audit trail for a specific enrichment (Admin only).

    **Audit Trail Includes:**
    - All API calls made during enrichment
    - Request parameters sent to each source
    - Response data from each source
    - Success/failure status
    - Error messages and types
    - Duration and cost per call
    - Circuit breaker states

    **Use Cases:**
    - Debugging failed enrichments
    - Understanding which sources were called
    - Verifying data source accuracy
    - Cost breakdown per API call
    - Compliance and transparency

    **Authentication:** Requires admin token
    """)
async def get_enrichment_audit_trail(
    enrichment_id: int,
    current_user: dict = RequireAuth
):
    """Get audit trail for enrichment"""
    try:
        logger.info(
            f"User {current_user['email']} viewing audit trail for {enrichment_id}",
            extra={"user": current_user["email"], "enrichment_id": enrichment_id}
        )

        # Get audit logs
        audit_logs = await audit_repository.get_by_enrichment(enrichment_id)

        # Calculate summary statistics
        total_calls = len(audit_logs)
        successful_calls = sum(1 for log in audit_logs if log.get("success", False))
        total_cost = sum(log.get("cost_usd", 0.0) for log in audit_logs)
        total_duration = sum(log.get("duration_ms", 0) for log in audit_logs)

        return AuditTrailResponse(
            success=True,
            data={
                "enrichment_id": enrichment_id,
                "audit_logs": audit_logs,
                "summary": {
                    "total_calls": total_calls,
                    "successful_calls": successful_calls,
                    "failed_calls": total_calls - successful_calls,
                    "total_cost_usd": round(total_cost, 4),
                    "total_duration_ms": total_duration,
                    "avg_duration_ms": round(total_duration / total_calls, 0) if total_calls > 0 else 0
                }
            }
        )

    except Exception as e:
        logger.error(
            f"Failed to get audit trail: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"], "enrichment_id": enrichment_id}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get audit trail: {str(e)}"
        )


@router.get("/audit/source/{source_name}", response_model=AuditTrailResponse,
    summary="Get Source Audit Logs",
    description="""
    Get recent audit logs for a specific data source (Admin only).

    **Use Cases:**
    - Monitor source health
    - Identify failing API calls
    - Track source usage
    - Debug source-specific issues

    **Authentication:** Requires admin token
    """)
async def get_source_audit_logs(
    source_name: str,
    limit: int = Query(100, ge=1, le=1000),
    current_user: dict = RequireAuth
):
    """Get audit logs for specific source"""
    try:
        logger.info(
            f"User {current_user['email']} viewing audit logs for source {source_name}",
            extra={"user": current_user["email"], "source": source_name}
        )

        # Get audit logs
        audit_logs = await audit_repository.get_by_source(
            source_name=source_name,
            limit=limit
        )

        return AuditTrailResponse(
            success=True,
            data={
                "source_name": source_name,
                "audit_logs": audit_logs,
                "total_logs": len(audit_logs)
            }
        )

    except Exception as e:
        logger.error(
            f"Failed to get source audit logs: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"], "source": source_name}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get source audit logs: {str(e)}"
        )


# ============================================================================
# CACHE MANAGEMENT
# ============================================================================

@router.post("/cache/clear-expired", response_model=DashboardStatsResponse,
    summary="Clear Expired Cache Entries",
    description="""
    Clear expired enrichment cache entries (Admin only).

    **Process:**
    - Deletes enrichments where expires_at < now
    - 30-day TTL for enrichments
    - Returns count of deleted entries

    **Recommended:**
    - Run daily via cron job
    - Prevents database bloat
    - Maintains cache freshness

    **Authentication:** Requires admin token
    """)
async def clear_expired_cache(current_user: dict = RequireAuth):
    """Clear expired cache entries"""
    try:
        logger.info(
            f"User {current_user['email']} clearing expired cache",
            extra={"user": current_user["email"]}
        )

        # Clear expired cache
        deleted_count = await enrichment_repository.clear_expired_cache()

        return DashboardStatsResponse(
            success=True,
            data={
                "deleted_count": deleted_count,
                "message": f"Cleared {deleted_count} expired cache entries"
            }
        )

    except Exception as e:
        logger.error(
            f"Failed to clear expired cache: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear expired cache: {str(e)}"
        )


# ============================================================================
# SOURCE MONITORING
# ============================================================================

@router.get("/monitoring/sources", response_model=DashboardStatsResponse,
    summary="Get Data Source Health Monitoring",
    description="""
    Get health monitoring data for all data sources (Admin only).

    **Metrics Per Source:**
    - Total calls (last 24 hours)
    - Success rate percentage
    - Average duration
    - Total cost
    - Circuit breaker status
    - Recent errors

    **Use Cases:**
    - Identify failing sources
    - Monitor API performance
    - Track circuit breaker events
    - Plan source optimization

    **Authentication:** Requires admin token
    """)
async def get_source_monitoring(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    current_user: dict = RequireAuth
):
    """Get source health monitoring data"""
    try:
        logger.info(
            f"User {current_user['email']} viewing source monitoring",
            extra={"user": current_user["email"], "hours": hours}
        )

        # Get all source statistics
        all_stats = await audit_repository.get_all_source_statistics(hours=hours)

        # Add health status indicators
        for stat in all_stats:
            success_rate = stat.get("success_rate", 0)
            if success_rate >= 95:
                stat["health"] = "healthy"
            elif success_rate >= 80:
                stat["health"] = "degraded"
            else:
                stat["health"] = "unhealthy"

        return DashboardStatsResponse(
            success=True,
            data={
                "sources": all_stats,
                "period_hours": hours,
                "summary": {
                    "total_sources": len(all_stats),
                    "healthy": sum(1 for s in all_stats if s.get("health") == "healthy"),
                    "degraded": sum(1 for s in all_stats if s.get("health") == "degraded"),
                    "unhealthy": sum(1 for s in all_stats if s.get("health") == "unhealthy")
                }
            }
        )

    except Exception as e:
        logger.error(
            f"Failed to get source monitoring: {str(e)}",
            exc_info=True,
            extra={"user": current_user["email"]}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get source monitoring: {str(e)}"
        )
