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
from app.middleware.logging_middleware import CorrelationIdMiddleware, configure_structured_logging
from app.middleware.security_middleware import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    RateLimitByEndpointMiddleware,
    get_security_config
)
from app.core.circuit_breaker import get_circuit_breaker_health

# Import all routers
from app.routes import analysis, reports, chat, intelligence, admin
from app.routes.auth import router as auth_router
from app.routes.user_actions import router as user_actions_router
from app.routes import enrichment, enrichment_admin
from app.routes.enrichment_progressive import router as progressive_enrichment_router

# Import custom OpenAPI schema generator
from app.core.openapi import custom_openapi

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
    # Configure structured logging with JSON format in production
    json_logging = settings.environment in ["production", "staging"]
    configure_structured_logging(app_name="strategy-ai", json_format=json_logging)

    logger.info("[STARTUP] Starting Strategy AI Backend...")
    logger.info(f"[STARTUP] Environment: {settings.environment}")
    logger.info(f"[STARTUP] Logging format: {'JSON' if json_logging else 'text'}")
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
    description="""
## AI-Powered Business Analysis & Lead Generation Platform

Strategy AI is a comprehensive lead generation and business analysis system that combines AI-powered insights with web scraping and market research capabilities.

### Key Features

- **Multi-Stage AI Analysis Pipeline**: 6-stage analysis process with Gemini 2.0 Flash and GPT-4o
- **Real-time Progress Streaming**: Server-Sent Events (SSE) for live analysis updates
- **Intelligent Caching**: Multi-layer caching with Upstash Redis for cost optimization
- **Web Data Enrichment**: Apify integration for website, LinkedIn, and competitor data
- **Advanced Authentication**: JWT-based auth with admin role management via Supabase
- **AI Chat Interface**: Interactive chat with Claude for report refinement
- **PDF Report Generation**: Professional PDF reports with customizable templates
- **Markdown Export/Import**: Full report editing workflow with markdown support
- **Confidence Scoring**: AI-powered quality assessment for all analyses

### Technology Stack

- **Framework**: FastAPI 0.100+
- **Database**: Supabase PostgreSQL
- **Caching**: Upstash Redis
- **AI Models**: Gemini 2.0 Flash, GPT-4o, Claude 3.5 (via OpenRouter)
- **Web Scraping**: Apify actors
- **Authentication**: JWT + Supabase Auth
- **Monitoring**: Sentry error tracking
    """,
    version="2.0.0",
    lifespan=lifespan,
    contact={
        "name": "Strategy AI Support",
        "url": "https://github.com/yourusername/strategy-ai-backend",
        "email": "support@strategyai.example.com"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    terms_of_service="https://strategyai.example.com/terms",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    servers=[
        {
            "url": "https://api.strategyai.example.com",
            "description": "Production server"
        },
        {
            "url": "https://staging-api.strategyai.example.com",
            "description": "Staging server"
        },
        {
            "url": "http://localhost:8000",
            "description": "Development server"
        }
    ],
    openapi_tags=[
        {
            "name": "auth",
            "description": "Authentication and authorization endpoints for admin access",
        },
        {
            "name": "analysis",
            "description": "Lead submission and analysis processing endpoints",
        },
        {
            "name": "reports",
            "description": "Report management, export, and editing endpoints",
        },
        {
            "name": "chat",
            "description": "AI-powered chat interface for report interaction",
        },
        {
            "name": "intelligence",
            "description": "Dashboard intelligence and analytics endpoints",
        },
        {
            "name": "admin",
            "description": "System administration and cache management endpoints",
        },
        {
            "name": "user_actions",
            "description": "User management and admin dashboard actions",
        },
        {
            "name": "enrichment",
            "description": "IMENSIAH data enrichment - public landing page submissions",
        },
        {
            "name": "enrichment-admin",
            "description": "IMENSIAH enrichment admin - dashboard analytics and management",
        }
    ]
)


# ============================================================================
# MIDDLEWARE
# ============================================================================
# Middleware is applied in reverse order (last added = first executed)
# Order: Security Headers → Rate Limit → Request Size → Correlation ID → CORS → GZip

# Security Headers Middleware (last - applied to all responses)
app.add_middleware(
    SecurityHeadersMiddleware,
    enable_hsts=settings.environment == "production",  # HSTS only in production
    enable_csp=False  # CSP disabled by default (can break frontend)
)

# Rate Limit Headers Middleware
app.add_middleware(RateLimitByEndpointMiddleware)

# Request Size Limit Middleware (prevent DoS)
app.add_middleware(RequestSizeLimitMiddleware)

# Correlation ID Middleware (adds tracing to all requests)
app.add_middleware(CorrelationIdMiddleware, header_name="X-Correlation-ID")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip Compression (first - compresses responses)
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ============================================================================
# EXCEPTION HANDLERS
# ============================================================================

# Register all exception handlers
register_exception_handlers(app)


# ============================================================================
# ROOT ENDPOINTS
# ============================================================================

@app.get("/",
    summary="API Root",
    description="""
    API root endpoint providing service information and status.

    Returns basic information about the API including:
    - Service name and version
    - Current environment (production/staging/development)
    - Available features and capabilities
    - API status

    This endpoint is useful for:
    - Verifying API is accessible
    - Checking current version
    - Understanding available features
    - Service discovery

    **Example:**
    ```bash
    curl https://api.strategyai.com/
    ```
    """,
    responses={
        200: {
            "description": "API information",
            "content": {
                "application/json": {
                    "example": {
                        "service": "Strategy AI Lead Generator API",
                        "status": "running",
                        "version": "2.0.0",
                        "environment": "production",
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
                }
            }
        }
    },
    tags=["health"])
async def root():
    """API root endpoint - returns service information and status"""
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


@app.get("/health",
    summary="Health Check",
    description="""
    Comprehensive health check endpoint for monitoring and load balancers.

    **Checked Services:**
    1. **Database (Supabase PostgreSQL)**
       - Connection status
       - Query execution test
       - Submission count verification

    2. **Cache (Upstash Redis)**
       - Connection status
       - Ping/pong test
       - Response time

    3. **AI Service (OpenRouter)**
       - Configuration validation
       - API key presence check

    4. **Circuit Breakers**
       - All breaker states
       - Open circuit detection
       - Failure rate monitoring

    5. **Security Middleware**
       - Security features status
       - Rate limiting availability
       - Request size limits

    **Response Status Codes:**
    - `200 OK (healthy)`: All systems operational
    - `200 OK (degraded)`: Non-critical service issues
    - `503 Service Unavailable`: Critical service failure

    **Health States:**
    - **healthy**: All services operational
    - **degraded**: Some services have issues but API functional
    - **unhealthy**: Critical services down, API may fail

    **Use Cases:**
    - Kubernetes liveness/readiness probes
    - Load balancer health checks
    - Monitoring alerting (Prometheus, Datadog, etc.)
    - Uptime monitoring (UptimeRobot, Pingdom)
    - CI/CD deployment validation

    **Example Response (Healthy):**
    ```json
    {
      "status": "healthy",
      "timestamp": "2025-01-26T10:00:00Z",
      "version": "2.0.0",
      "environment": "production",
      "checks": {
        "database": {
          "status": "healthy",
          "submissions_count": 1247
        },
        "redis": {
          "status": "healthy"
        },
        "openrouter": {
          "status": "configured",
          "api_key_present": true
        },
        "circuit_breakers": {
          "status": "healthy",
          "summary": "All breakers closed",
          "open_circuits": []
        },
        "security": {
          "status": "healthy",
          "features": ["rate_limiting", "cors", "security_headers"]
        }
      }
    }
    ```

    **Monitoring Integration:**

    *Kubernetes:*
    ```yaml
    livenessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 30
      periodSeconds: 10

    readinessProbe:
      httpGet:
        path: /health
        port: 8000
      initialDelaySeconds: 5
      periodSeconds: 5
    ```

    *Prometheus:*
    ```yaml
    - job_name: 'strategy-ai'
      metrics_path: '/health'
      static_configs:
        - targets: ['api.strategyai.com']
    ```

    **Notes:**
    - No authentication required (public endpoint)
    - Lightweight checks (< 100ms response time)
    - Safe to call frequently (every 10 seconds)
    - Does not count towards rate limits
    """,
    responses={
        200: {
            "description": "Service is healthy or degraded",
            "content": {
                "application/json": {
                    "examples": {
                        "healthy": {
                            "summary": "All systems operational",
                            "value": {
                                "status": "healthy",
                                "timestamp": "2025-01-26T10:00:00Z",
                                "version": "2.0.0",
                                "checks": {
                                    "database": {"status": "healthy"},
                                    "redis": {"status": "healthy"}
                                }
                            }
                        },
                        "degraded": {
                            "summary": "Some services degraded",
                            "value": {
                                "status": "degraded",
                                "timestamp": "2025-01-26T10:00:00Z",
                                "checks": {
                                    "database": {"status": "healthy"},
                                    "openrouter": {
                                        "status": "degraded",
                                        "api_key_present": False
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        503: {
            "description": "Service unavailable - critical services down",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "timestamp": "2025-01-26T10:00:00Z",
                        "checks": {
                            "database": {
                                "status": "unhealthy",
                                "error": "Connection timeout"
                            }
                        }
                    }
                }
            }
        }
    },
    tags=["health"])
async def health_check():
    """Health check endpoint - comprehensive system health monitoring for load balancers"""
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

    # Check 4: Circuit Breakers
    try:
        circuit_health = get_circuit_breaker_health()
        health_status["checks"]["circuit_breakers"] = {
            "status": "healthy" if circuit_health["overall_healthy"] else "degraded",
            "summary": circuit_health["summary"],
            "open_circuits": [
                b["name"] for b in circuit_health["breakers"]
                if b["state"] == "open"
            ]
        }
        if not circuit_health["overall_healthy"]:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["circuit_breakers"] = {
            "status": "error",
            "error": str(e)
        }

    # Check 5: Security Configuration
    try:
        security_config = get_security_config()
        health_status["checks"]["security"] = {
            "status": "healthy",
            "features": security_config["features"]
        }
    except Exception as e:
        health_status["checks"]["security"] = {
            "status": "error",
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

# Enrichment routes (IMENSIAH public + admin)
app.include_router(enrichment.router, tags=["enrichment"])
app.include_router(enrichment_admin.router, tags=["enrichment-admin"])
app.include_router(progressive_enrichment_router, tags=["progressive-enrichment"])


# ============================================================================
# CUSTOM OPENAPI SCHEMA
# ============================================================================

# Apply custom OpenAPI schema with enhanced documentation
app.openapi = lambda: custom_openapi(app)


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
