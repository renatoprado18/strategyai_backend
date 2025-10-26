"""
FastAPI Backend for Strategy AI Lead Generator
"""
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from typing import Dict, List
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv

# Import local modules
from models import (
    SubmissionCreate,
    SubmissionResponse,
    Submission,
    SubmissionsListResponse,
    ReprocessResponse,
    ErrorResponse,
)
from database import (
    init_db,
    create_submission,
    get_submission,
    get_all_submissions,
    update_submission_status,
)
from analysis import generate_analysis, validate_analysis_structure

load_dotenv()

# Configuration
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001"
).split(",")
MAX_SUBMISSIONS_PER_IP_PER_DAY = int(os.getenv("MAX_SUBMISSIONS_PER_IP_PER_DAY", "3"))

# In-memory rate limiting (for MVP - use Redis in production)
rate_limit_store: Dict[str, List[datetime]] = {}


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[STARTUP] Starting Strategy AI Backend...")
    await init_db()
    print("[OK] Database initialized")
    yield
    # Shutdown
    print("[SHUTDOWN] Shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="Strategy AI Lead Generator API",
    description="AI-powered business analysis lead generation system",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate Limiting Helper
def check_rate_limit(ip_address: str) -> bool:
    """Check if IP has exceeded rate limit"""
    now = datetime.now()
    cutoff = now - timedelta(days=1)

    # Clean old entries
    if ip_address in rate_limit_store:
        rate_limit_store[ip_address] = [
            ts for ts in rate_limit_store[ip_address] if ts > cutoff
        ]

    # Check limit
    if ip_address in rate_limit_store:
        if len(rate_limit_store[ip_address]) >= MAX_SUBMISSIONS_PER_IP_PER_DAY:
            return False

    return True


def record_submission(ip_address: str):
    """Record a submission for rate limiting"""
    if ip_address not in rate_limit_store:
        rate_limit_store[ip_address] = []
    rate_limit_store[ip_address].append(datetime.now())


# Background Task: Process AI Analysis
async def process_analysis_task(submission_id: int):
    """Background task to generate AI analysis"""
    try:
        # Get submission details
        submission = await get_submission(submission_id)
        if not submission:
            print(f"[ERROR] Submission {submission_id} not found")
            return

        print(f"[PROCESSING] Processing analysis for submission {submission_id}...")

        # Generate analysis
        analysis = await generate_analysis(
            company=submission["company"],
            industry=submission["industry"],
            website=submission.get("website"),
            challenge=submission.get("challenge"),
        )

        # Validate structure
        if not await validate_analysis_structure(analysis):
            raise Exception("Analysis validation failed - invalid structure")

        # Convert to JSON string
        report_json = json.dumps(analysis, ensure_ascii=False)

        # Update submission with success
        await update_submission_status(
            submission_id=submission_id,
            status="completed",
            report_json=report_json,
        )

        print(f"[OK] Analysis completed for submission {submission_id}")

    except Exception as e:
        error_message = str(e)
        print(f"[ERROR] Analysis failed for submission {submission_id}: {error_message}")

        # Update submission with failure
        await update_submission_status(
            submission_id=submission_id,
            status="failed",
            error_message=error_message,
        )


# API Endpoints

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Strategy AI Lead Generator API",
        "status": "running",
        "version": "1.0.0",
    }


@app.post("/api/submit", response_model=SubmissionResponse)
async def submit_lead(
    submission: SubmissionCreate,
    background_tasks: BackgroundTasks,
    request: Request,
):
    """
    Submit a new lead form

    - Validates input data
    - Checks rate limiting
    - Creates submission in database
    - Triggers background AI analysis
    """
    try:
        # Get client IP for rate limiting
        client_ip = request.client.host

        # Check rate limit
        if not check_rate_limit(client_ip):
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {MAX_SUBMISSIONS_PER_IP_PER_DAY} submissions per day."
            )

        # Create submission in database
        submission_id = await create_submission(
            name=submission.name,
            email=submission.email,
            company=submission.company,
            website=submission.website,
            industry=submission.industry.value,
            challenge=submission.challenge,
        )

        # Record submission for rate limiting
        record_submission(client_ip)

        # Trigger background analysis
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


@app.get("/api/admin/submissions")
async def get_submissions():
    """
    Get all submissions (Admin endpoint)

    Returns list of all submissions ordered by created_at DESC
    """
    try:
        submissions = await get_all_submissions()

        # Convert to Pydantic models
        submission_list = [Submission(**sub) for sub in submissions]

        return {
            "success": True,
            "data": submission_list,
        }

    except Exception as e:
        print(f"[ERROR] Get submissions error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


@app.post("/api/admin/reprocess/{submission_id}", response_model=ReprocessResponse)
async def reprocess_submission(
    submission_id: int,
    background_tasks: BackgroundTasks,
):
    """
    Reprocess a failed submission (Admin endpoint)

    Triggers a new background analysis task
    """
    try:
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

        # Trigger new analysis
        background_tasks.add_task(process_analysis_task, submission_id)

        print(f"[OK] Reprocessing submission {submission_id}")

        return ReprocessResponse(success=True)

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Reprocess error: {e}")
        return ReprocessResponse(success=False, error=str(e))


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "error": exc.detail}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    print(f"[ERROR] Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"success": False, "error": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
