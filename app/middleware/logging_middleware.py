"""
Structured Logging Middleware with Correlation IDs
Provides request tracing and context propagation throughout the application
"""

import logging
import time
import uuid
from typing import Callable
from contextvars import ContextVar

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

# Context variables for request tracing
correlation_id_var: ContextVar[str] = ContextVar('correlation_id', default=None)
user_id_var: ContextVar[str] = ContextVar('user_id', default=None)
request_path_var: ContextVar[str] = ContextVar('request_path', default=None)

logger = logging.getLogger(__name__)


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds correlation IDs to all requests for distributed tracing

    Features:
    - Generates or extracts correlation ID from headers
    - Adds correlation ID to all log records
    - Includes request/response logging
    - Tracks request duration
    - Captures user context
    """

    def __init__(self, app: ASGIApp, header_name: str = "X-Correlation-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Extract or generate correlation ID
        correlation_id = request.headers.get(self.header_name)
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Set context variables
        correlation_id_var.set(correlation_id)
        request_path_var.set(request.url.path)

        # Extract user ID if authenticated
        user_id = None
        if hasattr(request.state, 'user') and request.state.user:
            user_id = getattr(request.state.user, 'id', None)
            user_id_var.set(str(user_id))

        # Log request start
        start_time = time.time()
        logger.info(
            f"Request started",
            extra={
                "correlation_id": correlation_id,
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "client_host": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            }
        )

        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log unhandled exceptions
            duration = time.time() - start_time
            logger.error(
                f"Request failed with unhandled exception",
                extra={
                    "correlation_id": correlation_id,
                    "user_id": user_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True
            )
            raise

        # Add correlation ID to response headers
        response.headers[self.header_name] = correlation_id

        # Log request completion
        duration = time.time() - start_time
        logger.info(
            f"Request completed",
            extra={
                "correlation_id": correlation_id,
                "user_id": user_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2),
            }
        )

        return response


class StructuredLoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that automatically includes correlation ID and user context

    Usage:
        from app.middleware.logging_middleware import get_logger
        logger = get_logger(__name__)
        logger.info("Processing submission", extra={"submission_id": 123})
    """

    def process(self, msg, kwargs):
        # Get context from ContextVars
        correlation_id = correlation_id_var.get()
        user_id = user_id_var.get()
        request_path = request_path_var.get()

        # Add context to extra
        extra = kwargs.get("extra", {})
        if correlation_id:
            extra["correlation_id"] = correlation_id
        if user_id:
            extra["user_id"] = user_id
        if request_path:
            extra["request_path"] = request_path

        kwargs["extra"] = extra
        return msg, kwargs


def get_logger(name: str) -> StructuredLoggerAdapter:
    """
    Get a structured logger with automatic context propagation

    Args:
        name: Logger name (typically __name__)

    Returns:
        StructuredLoggerAdapter with correlation ID support

    Example:
        logger = get_logger(__name__)
        logger.info("User action", extra={"action": "create_submission"})
    """
    base_logger = logging.getLogger(name)
    return StructuredLoggerAdapter(base_logger, {})


def get_correlation_id() -> str | None:
    """Get the current request's correlation ID"""
    return correlation_id_var.get()


def get_user_id() -> str | None:
    """Get the current request's user ID"""
    return user_id_var.get()


def get_request_path() -> str | None:
    """Get the current request's path"""
    return request_path_var.get()


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging
    Outputs logs in JSON format for easy parsing by log aggregators
    """

    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime

        log_data = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if available
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id

        # Add user ID if available
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id

        # Add request path if available
        if hasattr(record, "request_path"):
            log_data["request_path"] = record.request_path

        # Add any extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def configure_structured_logging(app_name: str = "strategy-ai", json_format: bool = False):
    """
    Configure structured logging for the application

    Args:
        app_name: Application name for logging
        json_format: Use JSON formatter (recommended for production)

    Example:
        # In main.py
        configure_structured_logging(app_name="strategy-ai", json_format=True)
    """
    import logging.config

    if json_format:
        formatter_class = "app.middleware.logging_middleware.JSONFormatter"
        format_string = None
    else:
        formatter_class = "logging.Formatter"
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "[%(correlation_id)s] - %(message)s"
        )

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structured": {
                "()": formatter_class,
            } if json_format else {
                "format": format_string,
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "structured",
                "stream": "ext://sys.stdout",
            }
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
        "loggers": {
            app_name: {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(config)
