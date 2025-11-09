"""
Admin-related endpoints for cache management and system administration.
"""
from fastapi import APIRouter, Depends
from typing import Dict, Any
from app.routes.auth import RequireAuth
from app.core.cache import get_cache_statistics, clear_expired_cache

# Create router with admin prefix
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/cache/statistics",
    summary="Get Cache Statistics",
    description="""
    Retrieve comprehensive cache performance metrics and cost savings (Admin only).

    **Metrics Provided:**

    1. **Enhanced Cache Statistics:**
       - Analysis cache (full reports - 30 day TTL)
       - Stage cache (individual stages - 7 day TTL)
       - PDF cache (generated PDFs - 90 day TTL)
       - Dashboard stats cache (5 minute TTL)

    2. **Institutional Memory:**
       - Apify web scraping results
       - Perplexity market research
       - LinkedIn profile data
       - Competitor intelligence

    3. **Performance Metrics:**
       - Cache hit rates by type
       - Total cost savings (USD)
       - Cache size statistics
       - Most accessed entries

    4. **Cost Analysis:**
       - **Analysis cache hit**: Saves $15-25 per hit
       - **Stage cache hit**: Saves $0.10-3 per stage
       - **PDF cache**: Time savings (instant regeneration)
       - **Institutional memory**: Saves Apify/Perplexity API costs

    **Use Cases:**
    - Monitor cache effectiveness
    - Calculate ROI of caching strategy
    - Identify optimization opportunities
    - Plan cache TTL adjustments
    - Budget API cost savings

    **Response Structure:**
    ```json
    {
      "success": true,
      "data": {
        "enhanced_cache": {
          "analysis_cache": {
            "total_records": 150,
            "hit_rate": "65%",
            "cost_saved_usd": 2475.00
          },
          "stage_cache": {...},
          "pdf_cache": {...}
        },
        "institutional_memory": {
          "total_records": 300,
          "apify_cache_hits": 120,
          "perplexity_cache_hits": 85
        },
        "summary": {
          "total_cost_saved_usd": 3250.00,
          "total_records": 450
        },
        "recommendations": [
          "Analysis cache saved $3,250.00 total",
          "Consider running clear_expired_cache() daily",
          "High cache hit rate = significant cost savings"
        ]
      }
    }
    ```

    **Monitoring Recommendations:**
    - Check daily for cost optimization
    - Run `clear_expired_cache()` periodically
    - Monitor hit rates for TTL tuning
    - Track trends over time

    **Authentication:**
    - Requires valid JWT token in Authorization header
    - Admin privileges required

    **Example:**
    ```bash
    curl -X GET https://api.example.com/api/admin/cache/statistics \\
      -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    ```
    """,
    responses={
        200: {
            "description": "Cache statistics retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": {
                            "summary": {
                                "total_cost_saved_usd": 3250.00,
                                "total_records": 450
                            }
                        }
                    }
                }
            }
        }
    })
async def get_cache_statistics_endpoint(current_user: dict = RequireAuth):
    """Get cache statistics - comprehensive performance metrics and cost savings"""
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
