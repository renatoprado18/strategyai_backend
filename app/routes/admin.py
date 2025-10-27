"""
Admin-related endpoints for cache management and system administration.
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.routes.auth import RequireAuth
from app.core.cache import get_cache_statistics, clear_expired_cache

# Create router with admin prefix
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/cache/statistics")
async def get_cache_statistics_endpoint(current_user: dict = RequireAuth):
    """
    Get comprehensive cache statistics (Protected Admin endpoint)

    Returns cache performance metrics including:
    - Cache hit rates
    - Total cost savings
    - Cache sizes
    - Most accessed entries

    Requires valid JWT token in Authorization header
    """
    try:
        print(f"[AUTH] User {current_user['email']} accessing cache statistics")

        from app.services.intelligence.memory import get_cache_stats as get_institutional_stats

        # Get all cache statistics
        enhanced_stats = await get_cache_statistics()
        institutional_stats = await get_institutional_stats()

        # Calculate overall statistics
        total_cost_saved = enhanced_stats.get("total_cost_saved", 0)

        return {
            "success": True,
            "data": {
                "enhanced_cache": enhanced_stats,
                "institutional_memory": institutional_stats,
                "summary": {
                    "total_cost_saved_usd": total_cost_saved,
                    "total_records": (
                        enhanced_stats.get("analysis_cache", {}).get("total_records", 0) +
                        enhanced_stats.get("stage_cache", {}).get("total_records", 0) +
                        enhanced_stats.get("pdf_cache", {}).get("total_records", 0) +
                        institutional_stats.get("total_records", 0)
                    ),
                    "analysis_cache_hit_rate": "High value cache - saves $15-25 per hit",
                    "stage_cache_hit_rate": "Partial savings - saves $0.10-3 per stage",
                    "pdf_cache": "Time savings - instant PDF regeneration",
                },
                "recommendations": [
                    f"✅ Analysis cache saved ${total_cost_saved:.2f} total",
                    "💡 Consider running clear_expired_cache() periodically (daily cron)",
                    "📊 Monitor cache hit rates to optimize TTL values",
                    "🚀 High cache hit rate = significant cost savings"
                ]
            }
        }

    except Exception as e:
        print(f"[ERROR] Cache statistics error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/cache/clear-expired")
async def clear_expired_cache_endpoint(current_user: dict = RequireAuth):
    """
    Clear expired cache entries (Protected Admin endpoint)

    Removes old cache entries based on TTL:
    - Analysis cache: 30 days
    - Stage cache: 7 days
    - PDF cache: 90 days
    - Stats cache: 5 minutes

    Requires valid JWT token in Authorization header
    """
    try:
        print(f"[AUTH] User {current_user['email']} clearing expired cache")

        cleared = await clear_expired_cache()

        total_cleared = sum(cleared.values())

        return {
            "success": True,
            "data": {
                "cleared": cleared,
                "total_cleared": total_cleared,
                "message": f"Cleared {total_cleared} expired cache entries"
            }
        }

    except Exception as e:
        print(f"[ERROR] Clear cache error: {e}")
        return {
            "success": False,
            "error": str(e)
        }
