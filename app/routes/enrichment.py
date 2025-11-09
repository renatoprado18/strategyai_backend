"""
Enrichment Routes - Public Landing Page Data Enrichment

This module contains routes for the IMENSIAH data enrichment landing page:
- Public enrichment submission (no auth required)
- Enrichment status check
- Quick enrichment results retrieval

The enrichment system uses a hybrid sync/async pattern:
- Quick enrichment: 2-3s sync response with basic data (FREE sources)
- Deep enrichment: 30s+ async background processing (ALL sources)

Created: 2025-01-09
Version: 1.0.0
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel, EmailStr, HttpUrl, field_validator
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from app.core.exceptions import ValidationError, RateLimitExceeded
from app.core.security.rate_limiter import check_rate_limit
from app.services.enrichment import EnrichmentOrchestrator
from app.repositories import enrichment_repository, audit_repository
from app.utils.background_tasks import normalize_website_url

logger = logging.getLogger(__name__)

# Initialize router with prefix
router = APIRouter(prefix="/api/enrichment")


# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class EnrichmentSubmission(BaseModel):
    """
    Landing page enrichment submission request

    User submits minimal information on landing page,
    we enrich it with data from 6 sources.
    """
    email: EmailStr
    company_website: str

    @field_validator("company_website")
    @classmethod
    def normalize_website(cls, v: str) -> str:
        """Normalize and validate website URL"""
        return normalize_website_url(v)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "contato@empresa.com.br",
                "company_website": "https://empresa.com.br"
            }
        }


class QuickEnrichmentResponse(BaseModel):
    """Quick enrichment response (2-3s)"""
    success: bool
    enrichment_id: int
    data: Dict[str, Any]
    completeness_score: float
    confidence_score: float
    quality_tier: str
    cost_usd: float
    duration_ms: int
    message: str

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "enrichment_id": 123,
                "data": {
                    "company_name": "TechStart Innovations",
                    "domain": "techstart.com.br",
                    "description": "Innovative tech solutions for startups",
                    "location": "São Paulo, SP, Brazil",
                    "tech_stack": ["React", "Next.js", "Vercel"]
                },
                "completeness_score": 35.0,
                "confidence_score": 65.0,
                "quality_tier": "moderate",
                "cost_usd": 0.0,
                "duration_ms": 2150,
                "message": "Quick enrichment complete! Deep enrichment processing in background."
            }
        }


class EnrichmentStatusResponse(BaseModel):
    """Enrichment status check response"""
    success: bool
    enrichment_id: int
    status: str  # "quick_complete", "deep_processing", "deep_complete", "failed"
    quick_data: Optional[Dict[str, Any]] = None
    deep_data: Optional[Dict[str, Any]] = None
    completeness_score: Optional[float] = None
    confidence_score: Optional[float] = None
    quality_tier: Optional[str] = None
    total_cost_usd: Optional[float] = None
    quick_duration_ms: Optional[int] = None
    deep_duration_ms: Optional[int] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "enrichment_id": 123,
                "status": "deep_complete",
                "deep_data": {
                    "company_name": "TechStart Innovations",
                    "cnpj": "12.345.678/0001-99",
                    "employee_count": "25-50",
                    "linkedin_followers": 1247,
                    "rating": 4.7
                },
                "completeness_score": 94.0,
                "confidence_score": 89.0,
                "quality_tier": "excellent",
                "total_cost_usd": 0.15,
                "deep_duration_ms": 31400
            }
        }


# ============================================================================
# PUBLIC ENDPOINTS
# ============================================================================

@router.post("/submit", response_model=QuickEnrichmentResponse,
    summary="Submit Landing Page Form for Enrichment",
    description="""
    Submit company website for data enrichment (Public endpoint - no authentication required).

    **Hybrid Enrichment Flow:**
    1. **Quick Enrichment (Sync - 2-3s):**
       - Metadata scraping (company name, description, tech stack)
       - IP geolocation (country, city, timezone)
       - Returns immediately with basic enriched data
       - Cost: $0.00 (free sources only)

    2. **Deep Enrichment (Async - 30s+ background):**
       - Clearbit company intelligence ($0.10)
       - Google Places location verification ($0.02)
       - Proxycurl LinkedIn data ($0.03)
       - ReceitaWS Brazilian CNPJ lookup (free)
       - Returns comprehensive enriched data
       - Total cost: $0.15 per enrichment

    **Rate Limiting:**
    - **Limit:** 5 submissions per IP per 24 hours
    - **Reset:** 24 hours from first submission
    - **Bypass:** Not available (prevents abuse)

    **Caching (30-day TTL):**
    - Same domain enrichments are cached for 30 days
    - Cache hits return instantly and cost $0.00
    - 60% cache hit rate = $1,080/year savings

    **Data Quality Tiers:**
    - **Minimal (< 40%):** Basic information only
    - **Moderate (40-70%):** Good coverage
    - **High (70-90%):** Comprehensive data
    - **Excellent (90%+):** Near-complete profile

    **Example Request:**
    ```bash
    curl -X POST https://api.example.com/api/enrichment/submit \\
      -H "Content-Type: application/json" \\
      -d '{
        "email": "contato@techstart.com.br",
        "company_website": "https://techstart.com.br"
      }'
    ```

    **Example Response (Quick Enrichment):**
    ```json
    {
      "success": true,
      "enrichment_id": 123,
      "data": {
        "company_name": "TechStart",
        "description": "Innovative tech solutions",
        "location": "São Paulo, SP, Brazil",
        "tech_stack": ["React", "Next.js"]
      },
      "completeness_score": 35.0,
      "confidence_score": 65.0,
      "quality_tier": "moderate",
      "cost_usd": 0.0,
      "duration_ms": 2150,
      "message": "Quick enrichment complete! Deep enrichment processing in background."
    }
    ```

    **Process Flow:**
    1. Validate email and website URL
    2. Check rate limit (5 per day per IP)
    3. Run quick enrichment (2-3s)
    4. Return quick results immediately
    5. Trigger deep enrichment in background
    6. Client can poll `/status/{enrichment_id}` for deep results

    **Authentication:** None required (public endpoint)
    """,
    responses={
        200: {
            "description": "Quick enrichment completed successfully",
        },
        400: {
            "description": "Validation error (invalid email or URL)",
        },
        429: {
            "description": "Rate limit exceeded (5 submissions per day)",
        },
        500: {
            "description": "Enrichment failed (check logs for details)",
        }
    },
    tags=["enrichment"])
async def submit_enrichment(
    submission: EnrichmentSubmission,
    background_tasks: BackgroundTasks,
    request: Request
):
    """
    Submit company website for enrichment - hybrid sync/async processing
    """
    try:
        # Get client IP for rate limiting
        client_ip = request.client.host

        # Rate limiting: 5 submissions per IP per 24 hours
        try:
            await check_rate_limit(
                key=f"enrichment:submit:{client_ip}",
                max_requests=5,
                window_seconds=86400  # 24 hours
            )
        except RateLimitExceeded as e:
            logger.warning(
                f"Rate limit exceeded for IP {client_ip}",
                extra={"ip": client_ip, "endpoint": "enrichment_submit"}
            )
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Maximum 5 enrichments per day per IP. Please try again tomorrow."
            )

        logger.info(
            f"Enrichment submission received from {client_ip}",
            extra={
                "ip": client_ip,
                "website": submission.company_website,
                "email": submission.email
            }
        )

        # Initialize orchestrator
        orchestrator = EnrichmentOrchestrator()

        # Execute QUICK enrichment (sync - 2-3s)
        logger.info(f"Starting quick enrichment for {submission.company_website}")
        quick_data = await orchestrator.enrich_quick(submission.company_website)

        # Save quick enrichment to database
        enrichment_id = await enrichment_repository.save_quick_enrichment(
            domain=quick_data.domain,
            data=quick_data,
            ttl_days=30
        )

        logger.info(
            f"Quick enrichment complete for {submission.company_website}",
            extra={
                "enrichment_id": enrichment_id,
                "completeness": quick_data.completeness_score,
                "cost": quick_data.total_cost_usd,
                "duration_ms": quick_data.quick_duration_ms
            }
        )

        # Trigger DEEP enrichment in background (async - 30s+)
        background_tasks.add_task(
            _process_deep_enrichment,
            website=submission.company_website,
            enrichment_id=enrichment_id,
            company_name=quick_data.company_name
        )

        # Return quick enrichment results immediately
        return QuickEnrichmentResponse(
            success=True,
            enrichment_id=enrichment_id,
            data=quick_data.dict(exclude={
                "source_attribution",
                "sources_called",
                "completeness_score",
                "confidence_score",
                "data_quality_tier",
                "total_cost_usd",
                "quick_duration_ms",
                "quick_completed_at"
            }),
            completeness_score=quick_data.completeness_score,
            confidence_score=quick_data.confidence_score,
            quality_tier=quick_data.data_quality_tier.value,
            cost_usd=quick_data.total_cost_usd,
            duration_ms=quick_data.quick_duration_ms,
            message=(
                "Quick enrichment complete! Deep enrichment processing in background. "
                f"Check /api/enrichment/status/{enrichment_id} for complete results."
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Enrichment submission failed: {str(e)}",
            exc_info=True,
            extra={
                "website": submission.company_website,
                "error": str(e)
            }
        )
        raise HTTPException(
            status_code=500,
            detail=f"Enrichment failed: {str(e)}"
        )


@router.get("/status/{enrichment_id}", response_model=EnrichmentStatusResponse,
    summary="Check Enrichment Status",
    description="""
    Check the status of an enrichment request.

    **Enrichment States:**
    - **quick_complete**: Quick enrichment finished, deep enrichment in progress
    - **deep_complete**: Full enrichment complete with all data sources

    **Usage:**
    After submitting an enrichment, poll this endpoint every 5-10 seconds
    to check if deep enrichment has completed.

    **Example Request:**
    ```bash
    curl https://api.example.com/api/enrichment/status/123
    ```

    **Example Response (Deep Complete):**
    ```json
    {
      "success": true,
      "enrichment_id": 123,
      "status": "deep_complete",
      "deep_data": {
        "company_name": "TechStart",
        "cnpj": "12.345.678/0001-99",
        "employee_count": "25-50",
        "linkedin_followers": 1247,
        "rating": 4.7
      },
      "completeness_score": 94.0,
      "confidence_score": 89.0,
      "quality_tier": "excellent",
      "total_cost_usd": 0.15
    }
    ```

    **Authentication:** None required
    """,
    tags=["enrichment"])
async def get_enrichment_status(enrichment_id: int):
    """Get enrichment status and results"""
    try:
        # Get enrichment from database
        enrichment = await enrichment_repository.get_by_id(str(enrichment_id))

        if not enrichment:
            raise HTTPException(
                status_code=404,
                detail=f"Enrichment {enrichment_id} not found"
            )

        # Determine status
        has_deep = enrichment.get("deep_data") is not None
        status = "deep_complete" if has_deep else "quick_complete"

        return EnrichmentStatusResponse(
            success=True,
            enrichment_id=enrichment_id,
            status=status,
            quick_data=enrichment.get("quick_data"),
            deep_data=enrichment.get("deep_data"),
            completeness_score=enrichment.get("completeness_score"),
            confidence_score=enrichment.get("confidence_score"),
            quality_tier=enrichment.get("data_quality_tier"),
            total_cost_usd=enrichment.get("total_cost_usd"),
            quick_duration_ms=enrichment.get("quick_duration_ms"),
            deep_duration_ms=enrichment.get("deep_duration_ms")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Failed to get enrichment status: {str(e)}",
            exc_info=True,
            extra={"enrichment_id": enrichment_id}
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get enrichment status: {str(e)}"
        )


# ============================================================================
# BACKGROUND TASKS
# ============================================================================

async def _process_deep_enrichment(
    website: str,
    enrichment_id: int,
    company_name: Optional[str] = None
):
    """
    Background task to process deep enrichment

    This runs asynchronously after quick enrichment returns.
    """
    try:
        logger.info(
            f"Starting deep enrichment for {website}",
            extra={"enrichment_id": enrichment_id, "website": website}
        )

        # Initialize orchestrator
        orchestrator = EnrichmentOrchestrator()

        # Execute DEEP enrichment (30s+)
        deep_data = await orchestrator.enrich_deep(
            website=website,
            enrichment_id=enrichment_id,
            company_name=company_name
        )

        # Update database with deep enrichment results
        await enrichment_repository.save_deep_enrichment(
            domain=deep_data.domain,
            data=deep_data,
            ttl_days=30
        )

        logger.info(
            f"Deep enrichment complete for {website}",
            extra={
                "enrichment_id": enrichment_id,
                "completeness": deep_data.completeness_score,
                "cost": deep_data.total_cost_usd,
                "duration_ms": deep_data.deep_duration_ms
            }
        )

    except Exception as e:
        logger.error(
            f"Deep enrichment failed for {website}: {str(e)}",
            exc_info=True,
            extra={"enrichment_id": enrichment_id, "website": website}
        )
        # Don't raise - background task failure shouldn't crash app
