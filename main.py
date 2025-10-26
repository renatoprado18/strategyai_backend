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
from analysis_enhanced import generate_enhanced_analysis, validate_enhanced_analysis
from auth import authenticate_user, get_current_user, RequireAuth
from rate_limiter import check_rate_limit
from apify_service import gather_all_apify_data
from perplexity_service import comprehensive_market_research

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

        # Step 1: Gather Apify data (web scraping, competitor research, trends, LinkedIn, news, social media)
        print(f"[APIFY] Gathering enrichment data for {submission['company']}...")
        apify_data = None
        data_quality = {
            "website_scraped": False,
            "competitors_found": 0,
            "trends_researched": False,
            "company_enriched": False,
            "linkedin_company_found": False,
            "linkedin_founder_found": False,
            "news_found": False,
            "social_media_found": False,
            "sources_succeeded": 0,
            "sources_failed": 0,
            "failed_sources": [],
            "quality_tier": "minimal"
        }

        try:
            apify_data = await gather_all_apify_data(
                company=submission["company"],
                industry=submission["industry"],
                website=submission.get("website"),
                linkedin_company=submission.get("linkedin_company"),
                linkedin_founder=submission.get("linkedin_founder"),
                challenge=submission.get("challenge"),
            )
            print(f"[APIFY] Data gathering completed for submission {submission_id}")

            # LOG: Detailed breakdown of what each source returned
            print(f"[APIFY RESULTS] ===== DATA SOURCES BREAKDOWN =====")
            print(f"[APIFY RESULTS] Website Data: {'✅ SUCCESS' if apify_data.get('website_data', {}).get('scraped_successfully') else '❌ FAILED'}")
            print(f"[APIFY RESULTS] Competitors: {apify_data.get('competitor_data', {}).get('competitors_found', 0)} found")
            print(f"[APIFY RESULTS] Industry Trends: {'✅ SUCCESS' if apify_data.get('industry_trends', {}).get('researched_successfully') else '❌ FAILED'}")
            print(f"[APIFY RESULTS] Company Enrichment: {'✅ SUCCESS' if apify_data.get('company_enrichment', {}).get('enriched_successfully') else '❌ FAILED'}")
            print(f"[APIFY RESULTS] LinkedIn Company: {'✅ SUCCESS' if apify_data.get('linkedin_company_data', {}).get('scraped_successfully') else '❌ FAILED'}")
            print(f"[APIFY RESULTS] LinkedIn Founder: {'✅ SUCCESS' if apify_data.get('linkedin_founder_data', {}).get('scraped_successfully') else '❌ FAILED'}")
            print(f"[APIFY RESULTS] News Articles: {'✅ SUCCESS' if apify_data.get('news_data', {}).get('researched_successfully') else '❌ FAILED'}")
            print(f"[APIFY RESULTS] Social Media: {'✅ SUCCESS' if apify_data.get('social_media_data', {}).get('researched_successfully') else '❌ FAILED'}")
            print(f"[APIFY RESULTS] =====================================")

            # Extract data quality metrics (now includes 8 data sources)
            if apify_data:
                # Core sources (original 4)
                data_quality["website_scraped"] = apify_data.get("website_data", {}).get("scraped_successfully", False)
                data_quality["competitors_found"] = apify_data.get("competitor_data", {}).get("competitors_found", 0)
                data_quality["trends_researched"] = apify_data.get("industry_trends", {}).get("researched_successfully", False)
                data_quality["company_enriched"] = apify_data.get("company_enrichment", {}).get("enriched_successfully", False)

                # NEW: LinkedIn sources
                data_quality["linkedin_company_found"] = apify_data.get("linkedin_company_data", {}).get("scraped_successfully", False)
                data_quality["linkedin_founder_found"] = apify_data.get("linkedin_founder_data", {}).get("scraped_successfully", False)

                # NEW: Public data sources
                data_quality["news_found"] = apify_data.get("news_data", {}).get("researched_successfully", False)
                data_quality["social_media_found"] = apify_data.get("social_media_data", {}).get("researched_successfully", False)

                # Count successes from all 8 sources
                successes = sum([
                    data_quality["website_scraped"],
                    data_quality["competitors_found"] > 0,
                    data_quality["trends_researched"],
                    data_quality["company_enriched"],
                    data_quality["linkedin_company_found"],
                    data_quality["linkedin_founder_found"],
                    data_quality["news_found"],
                    data_quality["social_media_found"]
                ])
                data_quality["sources_succeeded"] = successes
                data_quality["sources_failed"] = 8 - successes

                # Track failed sources
                if not data_quality["website_scraped"] and submission.get("website"):
                    data_quality["failed_sources"].append("website_scraping")
                if data_quality["competitors_found"] == 0:
                    data_quality["failed_sources"].append("competitor_research")
                if not data_quality["trends_researched"]:
                    data_quality["failed_sources"].append("industry_trends")
                if not data_quality["company_enriched"]:
                    data_quality["failed_sources"].append("company_enrichment")
                if not data_quality["linkedin_company_found"]:
                    data_quality["failed_sources"].append("linkedin_company")
                if not data_quality["linkedin_founder_found"] and submission.get("linkedin_founder"):
                    data_quality["failed_sources"].append("linkedin_founder")
                if not data_quality["news_found"]:
                    data_quality["failed_sources"].append("news_articles")
                if not data_quality["social_media_found"]:
                    data_quality["failed_sources"].append("social_media")

                # Calculate quality tier (8 sources total, more granular tiers)
                completion_rate = successes / 8
                if completion_rate >= 0.75:  # 6-8 sources = 75-100%
                    data_quality["quality_tier"] = "full"
                elif completion_rate >= 0.5:  # 4-5 sources = 50-74%
                    data_quality["quality_tier"] = "good"
                elif completion_rate >= 0.25:  # 2-3 sources = 25-49%
                    data_quality["quality_tier"] = "partial"
                else:  # 0-1 sources = 0-24%
                    data_quality["quality_tier"] = "minimal"

                data_quality["data_completeness"] = f"{int(completion_rate * 100)}%"

                # LOG: Final quality summary
                print(f"[DATA QUALITY] ===== FINAL SUMMARY =====")
                print(f"[DATA QUALITY] Sources Succeeded: {successes}/8")
                print(f"[DATA QUALITY] Quality Tier: {data_quality['quality_tier'].upper()}")
                print(f"[DATA QUALITY] Data Completeness: {data_quality['data_completeness']}")
                if data_quality["failed_sources"]:
                    print(f"[DATA QUALITY] Failed Sources: {', '.join(data_quality['failed_sources'])}")
                print(f"[DATA QUALITY] =====================================")

        except Exception as e:
            print(f"[WARNING] Apify enrichment failed: {str(e)}. Continuing with basic analysis...")
            apify_data = None
            data_quality["sources_failed"] = 8
            data_quality["failed_sources"] = ["all_sources_failed"]

        # Step 1.5: PERPLEXITY DEEP RESEARCH (LEGENDARY UPGRADE!)
        print(f"[PERPLEXITY] Starting comprehensive market research for {submission['company']}...")
        perplexity_data = None
        perplexity_success = False

        try:
            perplexity_data = await comprehensive_market_research(
                company=submission["company"],
                industry=submission["industry"],
                challenge=submission.get("challenge", "Expandir mercado e aumentar receita"),
                region="Brasil",
                specific_segment=None
            )

            perplexity_success = perplexity_data.get("research_completed", False)

            if perplexity_success:
                print(f"[PERPLEXITY] ✅ Comprehensive research completed!")
                print(f"[PERPLEXITY] Success Rate: {perplexity_data.get('success_rate', 'N/A')}")

                # Add Perplexity as additional data sources to quality tracking
                perplexity_sources = perplexity_data.get('success_rate', '0/5').split('/')[0]
                data_quality["perplexity_sources"] = int(perplexity_sources)
                data_quality["sources_succeeded"] += int(perplexity_sources)

                # Update quality tier with Perplexity boost (now 8 Apify + 5 Perplexity = 13 total)
                total_sources = 13
                total_succeeded = data_quality["sources_succeeded"]
                completion_rate = total_succeeded / total_sources

                if completion_rate >= 0.75:  # 10-13 sources = 75-100%
                    data_quality["quality_tier"] = "legendary"  # NEW TIER!
                elif completion_rate >= 0.60:  # 8-9 sources = 60-74%
                    data_quality["quality_tier"] = "full"
                elif completion_rate >= 0.40:  # 5-7 sources = 40-59%
                    data_quality["quality_tier"] = "good"
                elif completion_rate >= 0.20:  # 3-4 sources = 20-39%
                    data_quality["quality_tier"] = "partial"
                else:  # 0-2 sources = 0-19%
                    data_quality["quality_tier"] = "minimal"

                data_quality["data_completeness"] = f"{int(completion_rate * 100)}%"

                print(f"[PERPLEXITY] 🚀 UPGRADED Quality Tier: {data_quality['quality_tier'].upper()}")
                print(f"[PERPLEXITY] Total Sources: {total_succeeded}/{total_sources} ({data_quality['data_completeness']})")
            else:
                print(f"[PERPLEXITY] ⚠️ Research partially completed or failed")

        except Exception as e:
            print(f"[WARNING] Perplexity research failed: {str(e)}. Continuing with Apify data only...")
            perplexity_data = None

        # Step 2: Generate enhanced AI analysis with 10XMentorAI frameworks
        print(f"[AI] Generating premium strategic analysis for submission {submission_id}...")
        import time
        start_time = time.time()

        analysis = await generate_enhanced_analysis(
            company=submission["company"],
            industry=submission["industry"],
            website=submission.get("website"),
            challenge=submission.get("challenge"),
            apify_data=apify_data,
            perplexity_data=perplexity_data,  # LEGENDARY: Real-time web research
            use_multi_model=True,  # Enable multi-model orchestration
        )

        processing_time = time.time() - start_time

        # Validate structure
        if not await validate_enhanced_analysis(analysis):
            raise Exception("Enhanced analysis validation failed - invalid structure")

        # Add data disclaimer to metadata if data is incomplete
        if data_quality["quality_tier"] in ["partial", "minimal"]:
            disclaimer = f"Este relatório foi gerado com {data_quality['data_completeness']} dos dados disponíveis. "
            if data_quality["failed_sources"]:
                disclaimer += f"Fontes indisponíveis: {', '.join(data_quality['failed_sources'])}. "
            disclaimer += "A análise foi feita com base nas informações públicas disponíveis."
            analysis["_metadata"]["data_disclaimer"] = disclaimer

        # Extract processing metadata
        processing_meta = {
            "model": analysis.get("_metadata", {}).get("model_used", "gpt-4o"),
            "framework_version": analysis.get("_metadata", {}).get("framework_version", "10XMentorAI v2.0"),
            "processing_time_seconds": round(processing_time, 2),
            "generated_at": datetime.utcnow().isoformat(),
            "data_quality_tier": data_quality["quality_tier"],
            # Store ALL scraped data for dashboard preview
            "apify_data": apify_data,
            "perplexity_research": perplexity_data if perplexity_success else None,
        }

        # Convert to JSON strings
        report_json = json.dumps(analysis, ensure_ascii=False)
        data_quality_json = json.dumps(data_quality, ensure_ascii=False)
        processing_metadata_json = json.dumps(processing_meta, ensure_ascii=False)

        # Update submission with success
        await update_submission_status(
            submission_id=submission_id,
            status="completed",
            report_json=report_json,
            data_quality_json=data_quality_json,
            processing_metadata=processing_metadata_json,
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
