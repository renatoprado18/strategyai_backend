"""
Analysis Routes - Submission Processing and Status Management

This module contains routes for:
- Submitting new analysis requests (public)
- Streaming analysis progress via SSE (public)
- Reprocessing failed analyses (admin)
- Regenerating completed analyses (admin)
- Updating submission status (admin)
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from typing import AsyncIterator, Dict, List
from datetime import datetime
import json
import logging
import asyncio

from app.core.exceptions import (
    RateLimitExceeded,
    ValidationError,
    ResourceNotFound
)

logger = logging.getLogger(__name__)

# Import schemas
from app.models.schemas import (
    SubmissionCreate,
    SubmissionResponse,
    ReprocessResponse,
    UpdateStatusRequest,
    UpdateStatusResponse,
)

# Import database functions
from app.core.database import (
    create_submission,
    get_submission,
    update_submission_status,
)

# Import auth dependency
from app.routes.auth import RequireAuth

# Import security
from app.core.security.rate_limiter import check_rate_limit

# Import background task utilities
from app.utils.background_tasks import (
    normalize_website_url,
    process_analysis_task,
    emit_progress,
    get_progress_updates,
    clear_progress,
)

# Initialize router with prefix
router = APIRouter(prefix="/api")


# ============================================================================
# PUBLIC ENDPOINTS
# ============================================================================

@router.post("/submit", response_model=SubmissionResponse,
    summary="Submit Lead Form",
    description="""
    Submit a new business analysis lead form (Public endpoint - no authentication required).

    **Process Flow:**
    1. **Validation:** Validates all input fields (email, URLs, text length)
    2. **Rate Limiting:** Checks IP-based rate limit (3 submissions per day)
    3. **Database:** Creates submission record in Supabase
    4. **Background Processing:** Triggers async AI analysis pipeline:
       - Stage 1: Data Extraction (Apify + web scraping)
       - Stage 2: Gap Analysis
       - Stage 3: Strategic Analysis
       - Stage 4: Competitive Intelligence
       - Stage 5: Risk & Priority Assessment
       - Stage 6: Polish & Quality Check

    **Data Enrichment:**
    - Website content scraping via Apify
    - LinkedIn company profile extraction
    - LinkedIn founder profile analysis
    - Competitor research and market intelligence

    **Rate Limiting:**
    - **Limit:** 3 submissions per IP per 24 hours
    - **Reset:** 24 hours from first submission
    - **Bypass:** Not available (security measure)

    **Processing Time:**
    - Initial response: Immediate (< 100ms)
    - Full analysis: 2-5 minutes
    - Monitor progress via SSE endpoint: `/api/submissions/{id}/stream`

    **Input Validation:**
    - Name: Minimum 2 characters
    - Email: Must be corporate (not gmail/hotmail/etc)
    - Company: Minimum 2 characters
    - Website: Valid URL with https:// (auto-added if missing)
    - LinkedIn URLs: Valid LinkedIn profile/company URLs
    - Challenge: Maximum 200 characters, XSS protection enabled

    **Example Request:**
    ```bash
    curl -X POST https://api.example.com/api/submit \\
      -H "Content-Type: application/json" \\
      -d '{
        "name": "João Silva",
        "email": "joao@techcorp.com.br",
        "company": "TechCorp Solutions",
        "website": "https://techcorp.com.br",
        "linkedin_company": "https://linkedin.com/company/techcorp",
        "linkedin_founder": "https://linkedin.com/in/joao-silva",
        "industry": "Tecnologia",
        "challenge": "Expandir base de clientes B2B"
      }'
    ```
    """,
    responses={
        200: {
            "description": "Submission accepted and processing started",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "submission_id": 42
                    }
                }
            }
        },
        400: {
            "description": "Validation error",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_email": {
                            "summary": "Personal email not allowed",
                            "value": {
                                "detail": [{
                                    "loc": ["body", "email"],
                                    "msg": "Please use a corporate email address",
                                    "type": "value_error"
                                }]
                            }
                        },
                        "challenge_too_long": {
                            "summary": "Challenge text too long",
                            "value": {
                                "detail": [{
                                    "loc": ["body", "challenge"],
                                    "msg": "Challenge must be maximum 200 characters",
                                    "type": "value_error"
                                }]
                            }
                        }
                    }
                }
            }
        },
        429: {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Rate limit exceeded. Maximum 3 submissions per day.",
                        "retry_after": 43200
                    }
                }
            }
        }
    })
async def submit_lead(
    submission: SubmissionCreate,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """Submit new lead form - public endpoint with rate limiting and background AI analysis"""
    try:
        # Get client IP for rate limiting
        client_ip = request.client.host

        # Check rate limit using Upstash Redis
        await check_rate_limit(client_ip)

        # Normalize website URL (add https:// if missing)
        normalized_website = normalize_website_url(submission.website) if submission.website else None

        # Create submission in database
        submission_id = await create_submission(
            name=submission.name,
            email=submission.email,
            company=submission.company,
            website=normalized_website,
            linkedin_company=submission.linkedin_company,
            linkedin_founder=submission.linkedin_founder,
            industry=submission.industry.value,
            challenge=submission.challenge,
        )

        # Trigger background analysis with Apify enrichment
        background_tasks.add_task(process_analysis_task, submission_id)

        logger.info(f"[OK] New submission created: ID={submission_id}, Company={submission.company}")

        return SubmissionResponse(
            success=True,
            submission_id=submission_id,
        )

    except HTTPException:
        # Let HTTPException (like rate limits) pass through
        raise
    except ValidationError as e:
        logger.error(f"[ERROR] Validation error in submission: {e}", exc_info=True)
        return SubmissionResponse(
            success=False,
            error=str(e),
        )
    except Exception as e:
        # Catch-all for database errors or unexpected issues
        logger.exception(f"[ERROR] Submit error: {e}")
        return SubmissionResponse(
            success=False,
            error=str(e),
        )


@router.get("/submissions/{submission_id}/stream",
    summary="Stream Analysis Progress (SSE)",
    description="""
    Server-Sent Events (SSE) endpoint for real-time analysis progress updates.

    **Connection Details:**
    - **Protocol:** Server-Sent Events (text/event-stream)
    - **Timeout:** 3 minutes (180 seconds)
    - **Polling Interval:** 1 second
    - **Auto-close:** When analysis completes or fails

    **Event Format:**
    Each event contains a JSON object with:
    - `stage`: Current stage identifier (e.g., "data_gathering", "ai_analysis")
    - `message`: Human-readable progress message (Portuguese)
    - `progress`: Progress percentage (0-100)
    - `timestamp`: ISO 8601 timestamp

    **Stage Flow:**
    1. **initialization** (0-10%): Starting analysis
    2. **data_gathering** (10-30%): Scraping websites, LinkedIn profiles
    3. **ai_analysis** (30-90%): Running 6-stage AI pipeline
    4. **finalization** (90-95%): Generating PDF report
    5. **completed** (100%): Analysis finished
    6. **failed** (0%): Error occurred

    **JavaScript Example:**
    ```javascript
    const eventSource = new EventSource(
      `/api/submissions/${submissionId}/stream`
    );

    eventSource.onmessage = (event) => {
      const progress = JSON.parse(event.data);
      console.log(`[${progress.stage}] ${progress.progress}%: ${progress.message}`);

      if (progress.stage === 'completed') {
        eventSource.close();
        // Fetch final report
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
    };
    ```

    **Python Example:**
    ```python
    import requests
    import json

    response = requests.get(
        f"https://api.example.com/api/submissions/{submission_id}/stream",
        stream=True
    )

    for line in response.iter_lines():
        if line.startswith(b'data: '):
            data = json.loads(line[6:])
            print(f"{data['progress']}%: {data['message']}")
            if data['stage'] in ['completed', 'failed']:
                break
    ```

    **Notes:**
    - Keep connection alive throughout analysis (2-5 minutes)
    - Reconnection not supported - start new stream if disconnected
    - Progress history cleared after successful stream completion
    - No authentication required (use submission_id as access token)
    """,
    responses={
        200: {
            "description": "SSE stream of progress updates",
            "content": {
                "text/event-stream": {
                    "example": "data: {\"stage\": \"data_gathering\", \"message\": \"Coletando dados...\", \"progress\": 30, \"timestamp\": \"2025-01-26T10:30:00Z\"}\n\n"
                }
            }
        },
        404: {
            "description": "Submission not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Submission not found"}
                }
            }
        }
    })
async def stream_analysis_progress(submission_id: int):
    """SSE endpoint for real-time analysis progress - streams progress updates until completion"""
    async def event_generator() -> AsyncIterator[str]:
        """Generate SSE events for progress updates"""
        last_sent_count = 0
        timeout_seconds = 180  # 3 minutes timeout
        start_time = asyncio.get_event_loop().time()

        try:
            while True:
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout_seconds:
                    yield f"data: {json.dumps({'stage': 'timeout', 'message': 'Stream timeout', 'progress': 0})}\n\n"
                    break

                # Get new progress updates
                all_updates = get_progress_updates(submission_id)

                # Send new updates since last check
                for update in all_updates[last_sent_count:]:
                    yield f"data: {json.dumps(update)}\n\n"
                    last_sent_count += 1

                    # If completed or failed, close stream after sending
                    if update.get("stage") in ["completed", "failed"]:
                        yield f"data: {json.dumps({'stage': 'end', 'message': 'Stream closing', 'progress': 100})}\n\n"
                        # Clear progress after successful stream
                        await asyncio.sleep(1)  # Give client time to receive final message
                        clear_progress(submission_id)
                        return

                # Wait before checking again (polling interval)
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            # Client disconnected - clean up
            logger.info(f"[SSE] Client disconnected from submission {submission_id} stream")
            clear_progress(submission_id)
            raise

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# ============================================================================
# PROTECTED ADMIN ENDPOINTS
# ============================================================================

@router.post("/admin/reprocess/{submission_id}", response_model=ReprocessResponse,
    summary="Reprocess Failed Submission",
    description="""
    Reprocess a failed or incomplete submission (Admin only).

    **Use Cases:**
    - Retry after temporary API failures (Apify, OpenRouter, etc.)
    - Reprocess after fixing data quality issues
    - Retry after rate limit errors
    - Force fresh analysis of old submission

    **Process:**
    1. Resets submission status to "pending"
    2. Clears previous error messages
    3. Keeps original submission data
    4. Triggers new background analysis with full pipeline
    5. May use cached external data if still valid (TTL-based)

    **Authentication:**
    - Requires valid JWT token in Authorization header
    - Admin privileges required
    - Token format: `Bearer <access_token>`

    **Example:**
    ```bash
    curl -X POST https://api.example.com/api/admin/reprocess/42 \\
      -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    ```
    """,
    responses={
        200: {
            "description": "Reprocessing started successfully",
            "content": {
                "application/json": {
                    "example": {"success": True}
                }
            }
        },
        404: {
            "description": "Submission not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Submission not found"}
                }
            }
        }
    },
    tags=["admin"])
async def reprocess_submission(
    submission_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = RequireAuth,
):
    """Reprocess failed submission - admin endpoint to retry analysis with full pipeline"""
    try:
        logger.info(f"[AUTH] User {current_user['email']} reprocessing submission {submission_id}")

        # Check if submission exists
        submission = await get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Reset to pending status
        await update_submission_status(
            submission_id=submission_id,
            status="pending",
            report_json=None,
            error_message=None,
        )

        # Trigger new analysis with Apify enrichment
        background_tasks.add_task(process_analysis_task, submission_id)

        logger.info(f"[OK] Reprocessing submission {submission_id}")

        return ReprocessResponse(success=True)

    except HTTPException:
        raise
    except Exception as e:
        # Catch-all for database errors or unexpected issues
        logger.exception(f"[ERROR] Reprocess error: {e}")
        return ReprocessResponse(success=False, error=str(e))


@router.post("/admin/submissions/{submission_id}/regenerate", response_model=ReprocessResponse,
    summary="Regenerate Completed Analysis",
    description="""
    Force regeneration of AI analysis for a completed submission (Admin only).

    **Key Difference from Reprocess:**
    - **Reprocess:** For failed submissions, runs full pipeline with fresh data
    - **Regenerate:** For completed submissions, forces new AI analysis while reusing cached external data

    **Use Cases:**
    - Get different AI perspective on same company data
    - Regenerate after prompt engineering improvements
    - Retry after AI model updates (Gemini 2.0, GPT-4o, etc.)
    - Test analysis quality with different parameters

    **Data Reuse:**
    - ✅ Reuses cached Apify data (if within TTL)
    - ✅ Reuses cached Perplexity research (if within TTL)
    - ✅ Reuses institutional memory insights
    - ❌ Forces new AI analysis (bypasses analysis cache)

    **Process:**
    1. Sets status to "pending" (keeps existing report as backup)
    2. Triggers new AI analysis with `force_regenerate=True`
    3. Skips data gathering if cache valid (saves time & cost)
    4. Runs fresh 6-stage AI pipeline
    5. Replaces old report on success

    **Cost Savings:**
    - Data gathering: $0 (cached)
    - AI analysis: $15-25 (fresh)
    - Total time: 1-2 minutes (vs 2-5 minutes)

    **Authentication:**
    - Requires valid JWT token in Authorization header
    - Admin privileges required

    **Example:**
    ```bash
    curl -X POST https://api.example.com/api/admin/submissions/42/regenerate \\
      -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    ```
    """,
    responses={
        200: {
            "description": "Regeneration started successfully",
            "content": {
                "application/json": {
                    "example": {"success": True}
                }
            }
        },
        404: {
            "description": "Submission not found",
            "content": {
                "application/json": {
                    "example": {"detail": "Submission not found"}
                }
            }
        }
    },
    tags=["admin"])
async def regenerate_analysis(
    submission_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = RequireAuth,
):
    """Regenerate analysis for completed submission - forces fresh AI analysis while reusing cached data"""
    try:
        logger.info(f"[AUTH] User {current_user['email']} regenerating analysis for submission {submission_id}")

        # Check if submission exists
        submission = await get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Set to pending status (keep existing data in case of failure)
        await update_submission_status(
            submission_id=submission_id,
            status="pending",
            error_message=None,
            # Note: Don't clear report_json - we'll replace it on success
        )

        # Trigger new analysis with force_regenerate=True
        # This bypasses analysis cache but uses institutional memory for external data
        background_tasks.add_task(process_analysis_task, submission_id, True)

        logger.info(f"[OK] Regenerating analysis for submission {submission_id} (force=True)")

        return ReprocessResponse(success=True)

    except HTTPException:
        raise
    except Exception as e:
        # Catch-all for database errors or unexpected issues
        logger.exception(f"[ERROR] Regenerate error: {e}")
        return ReprocessResponse(success=False, error=str(e))


@router.patch("/admin/submissions/{submission_id}/status", response_model=UpdateStatusResponse)
async def update_status(
    submission_id: int,
    request: UpdateStatusRequest,
    current_user: dict = RequireAuth,
):
    """
    Update submission status (Protected Admin endpoint)

    Workflow stages:
    - pending: Initial state, waiting to process
    - processing: Analysis in progress
    - completed: Analysis done, needs review
    - ready_to_send: QA passed, ready to send to client
    - sent: Delivered to client
    - failed: Processing error

    Requires valid JWT token in Authorization header
    """
    try:
        logger.info(f"[AUTH] User {current_user['email']} updating status for submission {submission_id} to {request.status}")

        # Check if submission exists
        submission = await get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Update status in database
        await update_submission_status(
            submission_id=submission_id,
            status=request.status.value,
        )

        logger.info(f"[OK] Updated submission {submission_id} status to {request.status}")

        return UpdateStatusResponse(success=True, new_status=request.status.value)

    except HTTPException:
        raise
    except Exception as e:
        # Catch-all for database errors or unexpected issues
        logger.exception(f"[ERROR] Status update error: {e}")
        return UpdateStatusResponse(success=False, error=str(e))
