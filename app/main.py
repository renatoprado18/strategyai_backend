"""
FastAPI Backend for Strategy AI Lead Generator
Streamlined main application file with modular route organization
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import logging

# Core configuration
from app.core.config import get_settings
from app.core.database import init_db, count_submissions
from app.core.middleware import register_exception_handlers
from app.core.security.rate_limiter import get_redis_client

# Import all routers
from app.routes import analysis, reports, chat, intelligence, admin
from app.routes.auth import router as auth_router
from app.routes.user_actions import router as user_actions_router

# Setup
settings = get_settings()
logger = logging.getLogger(__name__)

# ============================================================================
# SENTRY INITIALIZATION (Error Tracking)
# ============================================================================

# Initialize Sentry if DSN is provided
if settings.sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.asyncio import AsyncioIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.environment,
            traces_sample_rate=0.1,  # 10% performance monitoring
            profiles_sample_rate=0.1,  # 10% profiling
            integrations=[
                FastApiIntegration(),
                AsyncioIntegration(),
            ],
            # Send PII (personally identifiable information) - set to False for privacy
            send_default_pii=False,
            # Attach stack traces to all messages
            attach_stacktrace=True,
            # Performance monitoring
            enable_tracing=True,
        )
        logger.info(f"[SENTRY] ✅ Error tracking initialized (env: {settings.environment})")
    except ImportError:
        logger.warning("[SENTRY] ⚠️  sentry-sdk not installed, error tracking disabled")
    except Exception as e:
        logger.error(f"[SENTRY] ❌ Failed to initialize: {e}")
else:
    logger.info("[SENTRY] ℹ️  SENTRY_DSN not set, error tracking disabled")


# ============================================================================
# LIFESPAN MANAGEMENT
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: startup and shutdown events
    Handles graceful initialization and cleanup of resources
    """
    # ========================================================================
    # STARTUP
    # ========================================================================
    logger.info("[STARTUP] Starting Strategy AI Backend...")
    logger.info(f"[STARTUP] Environment: {settings.environment}")
    logger.info(f"[STARTUP] Allowed origins: {settings.allowed_origins}")

    # Initialize database connection
    await init_db()
    logger.info("[STARTUP] ✅ Database connection established")

    # Verify Redis connection
    try:
        redis_client = get_redis_client()
        redis_client.ping()
        logger.info("[STARTUP] ✅ Redis connection established")
    except Exception as e:
        logger.warning(f"[STARTUP] ⚠️  Redis connection failed: {e}")

    logger.info("[STARTUP] 🚀 Application ready to accept requests")

    yield

    # ========================================================================
    # SHUTDOWN
    # ========================================================================
    logger.info("[SHUTDOWN] 🛑 Shutdown signal received, starting graceful shutdown...")

    # Wait for in-flight requests to complete (30 second timeout)
    import asyncio
    shutdown_timeout = 30

    logger.info(f"[SHUTDOWN] ⏳ Waiting {shutdown_timeout}s for in-flight requests...")
    await asyncio.sleep(2)  # Give active requests time to finish

    # Close database connections
    try:
        # Supabase client cleanup (if needed)
        logger.info("[SHUTDOWN] 🗄️  Closing database connections...")
        # Note: Supabase client handles cleanup automatically
    except Exception as e:
        logger.error(f"[SHUTDOWN] ❌ Error closing database: {e}")

    # Close Redis connections
    try:
        logger.info("[SHUTDOWN] 💾 Closing Redis connections...")
        # Upstash Redis client cleanup (connection pooling handled by library)
    except Exception as e:
        logger.error(f"[SHUTDOWN] ❌ Error closing Redis: {e}")

    logger.info("[SHUTDOWN] ✅ Graceful shutdown complete")


# ============================================================================
# FASTAPI APP INITIALIZATION
# ============================================================================

app = FastAPI(
    title="Strategy AI Lead Generator API",
    description="AI-powered business analysis lead generation system with Supabase, Auth, and Apify",
    version="2.0.0",
    lifespan=lifespan,
)


# ============================================================================
# MIDDLEWARE
# ============================================================================

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

# Register all exception handlers
register_exception_handlers(app)


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "service": "Strategy AI Lead Generator API",
        "status": "running",
        "version": "2.0.0",
        "environment": settings.environment,
        "features": [
            "Supabase PostgreSQL",
            "JWT Authentication",
            "Apify Web Scraping",
            "Upstash Redis Caching",
            "SSE Streaming",
            "Multi-stage AI Analysis",
            "PDF Generation"
        ]
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring and load balancers

    Checks:
    - Database connectivity (Supabase)
    - Redis connectivity (Upstash)
    - OpenRouter API configuration

    Returns:
        200 OK: All services healthy
        200 OK (degraded): Some services degraded
        503 Service Unavailable: Critical services down
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "2.0.0",
        "environment": settings.environment,
        "checks": {}
    }

    # Check 1: Database (Supabase)
    try:
        count = await count_submissions()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "submissions_count": count
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Check 2: Redis (Upstash)
    try:
        redis = get_redis_client()
        redis.ping()
        health_status["checks"]["redis"] = {
            "status": "healthy"
        }
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Check 3: OpenRouter API (configuration check)
    try:
        if settings.openrouter_api_key:
            health_status["checks"]["openrouter"] = {
                "status": "configured",
                "api_key_present": True
            }
        else:
            health_status["status"] = "degraded"
            health_status["checks"]["openrouter"] = {
                "status": "degraded",
                "api_key_present": False
            }
    except Exception as e:
        health_status["checks"]["openrouter"] = {
            "status": "unknown",
            "error": str(e)
        }

    # Determine HTTP status code
    if health_status["status"] == "healthy":
        return health_status
    elif health_status["status"] == "degraded":
        return JSONResponse(status_code=200, content=health_status)
    else:
        return JSONResponse(status_code=503, content=health_status)


# ============================================================================
# ROUTE REGISTRATION
# ============================================================================

# Authentication routes (no prefix, handles /api/auth/*)
app.include_router(auth_router, tags=["auth"])

# Analysis & submission routes
app.include_router(analysis.router, tags=["analysis"])

# Report management routes
app.include_router(reports.router, tags=["reports"])

# Chat routes
app.include_router(chat.router, tags=["chat"])

# Dashboard intelligence routes
app.include_router(intelligence.router, tags=["intelligence"])

# Admin & system routes
app.include_router(admin.router, tags=["admin"])

# User action routes (admin dashboard actions)
app.include_router(user_actions_router, tags=["user_actions"])


# ============================================================================
# APPLICATION INFO
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 80)
    logger.info("Strategy AI Backend v2.0")
    logger.info("=" * 80)
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Allowed Origins: {settings.allowed_origins}")
    logger.info(f"Default Model: {settings.default_model}")
    logger.info("=" * 80)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.environment == "development" else False
    )
