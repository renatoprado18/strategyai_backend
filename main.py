"""
FastAPI Backend for Strategy AI Lead Generator
With Supabase, Authentication, Apify Integration, and Upstash Redis
"""
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request, Depends
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
    LoginRequest,
    LoginResponse,
    TokenResponse,
    UserResponse,
    SignupRequest,
    SignupResponse,
)
from database import (
    init_db,
    create_submission,
    get_submission,
    get_all_submissions,
    update_submission_status,
)
from analysis import generate_analysis, validate_analysis_structure
from auth import authenticate_user, get_current_user, RequireAuth
from rate_limiter import check_rate_limit
from apify_service import gather_all_apify_data

load_dotenv()

# Configuration
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:3001"
).split(",")


# Lifespan context manager for startup/shutdown
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("[STARTUP] Starting Strategy AI Backend with Supabase + Apify + Auth...")
    await init_db()
    print("[OK] Database connection established")
    yield
    # Shutdown
    print("[SHUTDOWN] Shutting down...")


# Initialize FastAPI app
app = FastAPI(
    title="Strategy AI Lead Generator API",
    description="AI-powered business analysis lead generation system with Supabase, Auth, and Apify",
    version="2.0.0",
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


# Background Task: Process AI Analysis with Apify Enrichment
async def process_analysis_task(submission_id: int):
    """Background task to generate AI analysis with Apify enrichment"""
    try:
        # Get submission details
        submission = await get_submission(submission_id)
        if not submission:
            print(f"[ERROR] Submission {submission_id} not found")
            return

        print(f"[PROCESSING] Processing analysis for submission {submission_id}...")

        # Step 1: Gather Apify data (web scraping, competitor research, trends)
        print(f"[APIFY] Gathering enrichment data for {submission['company']}...")
        apify_data = None
        try:
            apify_data = await gather_all_apify_data(
                company=submission["company"],
                industry=submission["industry"],
                website=submission.get("website"),
                challenge=submission.get("challenge"),
            )
            print(f"[APIFY] Data gathering completed for submission {submission_id}")
        except Exception as e:
            print(f"[WARNING] Apify enrichment failed: {str(e)}. Continuing with basic analysis...")
            apify_data = None

        # Step 2: Generate AI analysis (with or without Apify data)
        print(f"[AI] Generating strategic analysis for submission {submission_id}...")
        analysis = await generate_analysis(
            company=submission["company"],
            industry=submission["industry"],
            website=submission.get("website"),
            challenge=submission.get("challenge"),
            apify_data=apify_data,
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
        "version": "2.0.0",
        "features": ["Supabase", "Authentication", "Apify Integration", "Upstash Redis"]
    }


# Authentication Endpoints

@app.post("/api/auth/login", response_model=LoginResponse)
async def login(credentials: LoginRequest):
    """
    Admin login endpoint

    Authenticates user with Supabase Auth and returns JWT token
    """
    try:
        auth_result = await authenticate_user(
            email=credentials.email,
            password=credentials.password
        )

        return LoginResponse(
            success=True,
            data=TokenResponse(
                access_token=auth_result["access_token"],
                token_type=auth_result["token_type"],
                user=UserResponse(
                    id=auth_result["user"]["id"],
                    email=auth_result["user"]["email"]
                )
            )
        )

    except HTTPException as e:
        return LoginResponse(
            success=False,
            error=e.detail
        )
    except Exception as e:
        print(f"[ERROR] Login error: {e}")
        return LoginResponse(
            success=False,
            error="Authentication failed"
        )


@app.post("/api/auth/signup", response_model=SignupResponse)
async def signup(credentials: SignupRequest):
    """
    User signup endpoint

    Creates a new user in Supabase Auth. User will not have admin access until manually granted in Supabase dashboard.
    """
    try:
        from supabase_client import get_supabase_client

        supabase = get_supabase_client(use_service_key=False)

        # Create user in Supabase Auth
        response = supabase.auth.sign_up({
            "email": credentials.email,
            "password": credentials.password
        })

        if response.user:
            return SignupResponse(
                success=True,
                message="Conta criada com sucesso! Você pode fazer login agora. Nota: Acesso administrativo será concedido manualmente."
            )
        else:
            return SignupResponse(
                success=False,
                error="Falha ao criar conta. Por favor, tente novamente."
            )

    except Exception as e:
        error_message = str(e)
        print(f"[ERROR] Signup error: {error_message}")

        # Check for common errors
        if "already registered" in error_message.lower() or "already exists" in error_message.lower():
            return SignupResponse(
                success=False,
                error="Este email já está registrado. Faça login ou use outro email."
            )

        return SignupResponse(
            success=False,
            error="Erro ao criar conta. Por favor, tente novamente."
        )


# Public Endpoints

def normalize_website_url(url: str) -> str:
    """Ensure website URL has https:// prefix"""
    if not url:
        return url

    url = url.strip()

    # If URL already has a protocol, return as-is
    if url.startswith('http://') or url.startswith('https://'):
        return url

    # Add https:// prefix
    return f'https://{url}'


@app.post("/api/submit", response_model=SubmissionResponse)
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


# Protected Admin Endpoints (require authentication)

@app.get("/api/admin/submissions")
async def get_submissions(current_user: dict = RequireAuth):
    """
    Get all submissions (Protected Admin endpoint)

    Requires valid JWT token in Authorization header
    Returns list of all submissions ordered by created_at DESC
    """
    try:
        print(f"[AUTH] User {current_user['email']} accessing submissions")

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
