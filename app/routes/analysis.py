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
import asyncio

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

@router.post("/submit", response_model=SubmissionResponse)
async def submit_lead(
    submission: SubmissionCreate,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """
    Submit a new lead form (Public endpoint - no auth required)

    - Validates input data
    - Checks rate limiting with Upstash Redis
    - Creates submission in Supabase
    - Triggers background AI analysis with Apify enrichment
    """
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

        print(f"[OK] New submission created: ID={submission_id}, Company={submission.company}")

        return SubmissionResponse(
            success=True,
            submission_id=submission_id,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Submit error: {e}")
        return SubmissionResponse(
            success=False,
            error=str(e),
        )


@router.get("/submissions/{submission_id}/stream")
async def stream_analysis_progress(submission_id: int):
    """
    Server-Sent Events (SSE) endpoint for real-time analysis progress

    Usage (frontend):
    ```javascript
    const eventSource = new EventSource(`/api/submissions/${id}/stream`);
    eventSource.onmessage = (event) => {
        const progress = JSON.parse(event.data);
        console.log(`${progress.progress}%: ${progress.message}`);
    };
    ```

    Returns:
        StreamingResponse with Server-Sent Events

    Event format:
    ```json
    {
        "stage": "data_gathering",
        "message": "Coletando dados...",
        "progress": 30,
        "timestamp": "2025-01-26T10:30:00Z"
    }
    ```
    """
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
            print(f"[SSE] Client disconnected from submission {submission_id} stream")
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

@router.post("/admin/reprocess/{submission_id}", response_model=ReprocessResponse)
async def reprocess_submission(
    submission_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = RequireAuth,
):
    """
    Reprocess a failed submission (Protected Admin endpoint)

    Requires valid JWT token in Authorization header
    Triggers a new background analysis task with Apify enrichment
    """
    try:
        print(f"[AUTH] User {current_user['email']} reprocessing submission {submission_id}")

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

        print(f"[OK] Reprocessing submission {submission_id}")

        return ReprocessResponse(success=True)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Reprocess error: {e}")
        return ReprocessResponse(success=False, error=str(e))


@router.post("/admin/submissions/{submission_id}/regenerate", response_model=ReprocessResponse)
async def regenerate_analysis(
    submission_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = RequireAuth,
):
    """
    Regenerate analysis for a completed submission (Protected Admin endpoint)

    This forces a fresh AI analysis while reusing cached external data (Apify/Perplexity)
    from institutional memory if still fresh (within TTL).

    Use cases:
    - Get a different perspective on the same company data
    - Regenerate after AI model improvements
    - Try again with better prompt engineering

    Requires valid JWT token in Authorization header
    """
    try:
        print(f"[AUTH] User {current_user['email']} regenerating analysis for submission {submission_id}")

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

        print(f"[OK] Regenerating analysis for submission {submission_id} (force=True)")

        return ReprocessResponse(success=True)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Regenerate error: {e}")
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
        print(f"[AUTH] User {current_user['email']} updating status for submission {submission_id} to {request.status}")

        # Check if submission exists
        submission = await get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Update status in database
        await update_submission_status(
            submission_id=submission_id,
            status=request.status.value,
        )

        print(f"[OK] Updated submission {submission_id} status to {request.status}")

        return UpdateStatusResponse(success=True, new_status=request.status.value)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Status update error: {e}")
        return UpdateStatusResponse(success=False, error=str(e))
