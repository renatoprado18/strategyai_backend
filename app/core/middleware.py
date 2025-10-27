"""
Middleware for FastAPI Application
Exception handlers and request/response middleware
"""
import logging
from fastapi import Request
from fastapi.responses import JSONResponse
from app.core.exceptions import AppException
from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle all custom application exceptions

    Args:
        request: FastAPI request object
        exc: Custom application exception

    Returns:
        JSONResponse with appropriate status code and error details
    """
    logger.error(
        f"AppException: {exc.message}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "status_code": exc.status_code,
            "details": exc.details,
            "client_ip": request.client.host if request.client else "unknown"
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Handle all uncaught exceptions

    Args:
        request: FastAPI request object
        exc: Uncaught exception

    Returns:
        JSONResponse with 500 status code
    """
    logger.error(
        f"Uncaught exception on {request.method} {request.url.path}: {str(exc)}",
        extra={
            "path": request.url.path,
            "method": request.method,
            "client_ip": request.client.host if request.client else "unknown"
        },
        exc_info=True
    )

    # Include exception details only in development
    error_details = {}
    try:
        settings = get_settings()
        if settings.environment == "development":
            error_details = {
                "type": type(exc).__name__,
                "message": str(exc)
            }
    except:
        # If settings can't be loaded, don't include details (fail safe)
        pass

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal server error",
            "details": error_details
        }
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(AppException, app_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    logger.info("[MIDDLEWARE] ✅ Exception handlers registered")
