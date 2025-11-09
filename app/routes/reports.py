"""
Report Management Routes - Main Router

This is the main router that orchestrates all report-related functionality by
including specialized sub-routers for different concerns:

- Submission listing and viewing (this file)
- PDF and markdown export (reports_export.py)
- Markdown import and parsing (reports_import.py)
- AI-powered editing (reports_editing.py)
- Confidence scoring (reports_confidence.py)

All routes are protected by authentication and require admin access.
"""
from fastapi import APIRouter, Response
from datetime import datetime

# Import schemas
from app.models.schemas import Submission

# Import database functions
from app.core.database import get_all_submissions

# Import auth dependency
from app.routes.auth import RequireAuth

# Import sub-routers
from app.routes import (
import logging

logger = logging.getLogger(__name__)
    reports_export,
    reports_import,
    reports_editing,
    reports_confidence,
)

# Initialize main router with prefix
router = APIRouter(prefix="/api/admin")


# ============================================================================
# SUBMISSION LISTING & VIEWING
# ============================================================================

@router.get("/submissions",
    summary="List All Submissions",
    description="""
    Retrieve all submissions with comprehensive details (Admin only).

    **Features:**
    - Returns all submissions ordered by creation date (newest first)
    - Includes full submission data and analysis status
    - Multi-layer caching for optimal performance
    - Automatic cache invalidation on updates

    **Caching Strategy:**
    - **L1 Cache:** HTTP client cache (30 seconds)
    - **L2 Cache:** Redis dashboard cache (5 minutes)
    - Cache automatically invalidated on:
      - New submissions
      - Status updates
      - Report edits
      - Manual cache clear

    **Response Fields:**
    - `id`: Unique submission identifier
    - `name`: Lead contact name
    - `email`: Lead contact email
    - `company`: Company name
    - `website`: Company website URL
    - `industry`: Industry sector
    - `challenge`: Business challenge description
    - `status`: Current workflow status (pending/processing/completed/ready_to_send/sent/failed)
    - `report_json`: Complete AI analysis report (JSON string)
    - `error_message`: Error details if status is "failed"
    - `created_at`: Submission timestamp (ISO 8601)
    - `updated_at`: Last update timestamp (ISO 8601)

    **Status Workflow:**
    1. **pending**: Awaiting processing
    2. **processing**: AI analysis in progress
    3. **completed**: Analysis finished, needs QA review
    4. **ready_to_send**: QA approved, ready for delivery
    5. **sent**: Report delivered to client
    6. **failed**: Processing error occurred

    **Authentication:**
    - Requires valid JWT token in Authorization header
    - Admin privileges required

    **Performance:**
    - Typical response time: < 50ms (cached)
    - Cache miss response time: < 200ms
    - Automatic cache warming on startup

    **Example:**
    ```bash
    curl -X GET https://api.example.com/api/admin/submissions \\
      -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    ```
    """,
    responses={
        200: {
            "description": "Submissions retrieved successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "data": [
                            {
                                "id": 42,
                                "name": "João Silva",
                                "email": "joao@techcorp.com.br",
                                "company": "TechCorp Solutions",
                                "website": "https://techcorp.com.br",
                                "industry": "Tecnologia",
                                "challenge": "Expandir base B2B",
                                "status": "completed",
                                "report_json": "{...}",
                                "error_message": None,
                                "created_at": "2025-01-26T10:00:00Z",
                                "updated_at": "2025-01-26T10:05:00Z"
                            }
                        ]
                    }
                }
            }
        }
    })
async def get_submissions(current_user: dict = RequireAuth, response: Response = None):
    """List all submissions - admin endpoint with multi-layer caching"""
    try:
        logger.info(f"[AUTH] User {current_user['email']} accessing submissions")

        # Check cache first for dashboard stats (5 min TTL)
        from app.core.cache import get_cached_dashboard_stats, cache_dashboard_stats

        cached_stats = await get_cached_dashboard_stats()

        if cached_stats:
            logger.info(f"[CACHE] 🎯 Dashboard stats cache hit!")
            submissions = cached_stats.get("submissions", [])
            submission_list = [Submission(**sub) for sub in submissions]
        else:
            logger.info(f"[CACHE] ❌ Dashboard stats cache miss - fetching from database")
            submissions = await get_all_submissions()

            # Convert to Pydantic models
            submission_list = [Submission(**sub) for sub in submissions]

            # Cache for 5 minutes
            await cache_dashboard_stats({
                "submissions": submissions,
                "cached_at": datetime.utcnow().isoformat()
            })

        # Add caching headers (30 second cache)
        if response:
            response.headers["Cache-Control"] = "private, max-age=30, must-revalidate"

        return {
            "success": True,
            "data": submission_list,
        }

    except json.JSONDecodeError as e:
        logger.error(f"[ERROR] Invalid JSON in cached stats: {e}", exc_info=True)
        return {
            "success": False,
            "error": "Invalid cached data format",
        }
    except Exception as e:
        # Catch-all for database errors or unexpected issues
        logger.exception(f"[ERROR] Get submissions error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# INCLUDE SUB-ROUTERS
# ============================================================================

# Include export routes (PDF, markdown export, instructions)
router.include_router(
    reports_export.router,
    tags=["reports-export"]
)

# Include import routes (markdown import and parsing)
router.include_router(
    reports_import.router,
    tags=["reports-import"]
)

# Include editing routes (AI-powered editing, apply edits, PDF regeneration)
router.include_router(
    reports_editing.router,
    tags=["reports-editing"]
)

# Include confidence scoring routes
router.include_router(
    reports_confidence.router,
    tags=["reports-confidence"]
)
