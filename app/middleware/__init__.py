"""
Middleware package for Strategy AI
"""

from .logging_middleware import (
    CorrelationIdMiddleware,
    StructuredLoggerAdapter,
    get_logger,
    get_correlation_id,
    get_user_id,
    get_request_path,
    configure_structured_logging,
    JSONFormatter,
)

from .security_middleware import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    RateLimitByEndpointMiddleware,
    IPWhitelistMiddleware,
    get_security_config,
    is_safe_redirect_url,
    sanitize_filename,
    validate_content_type,
)

__all__ = [
    # Logging middleware
    "CorrelationIdMiddleware",
    "StructuredLoggerAdapter",
    "get_logger",
    "get_correlation_id",
    "get_user_id",
    "get_request_path",
    "configure_structured_logging",
    "JSONFormatter",
    # Security middleware
    "SecurityHeadersMiddleware",
    "RequestSizeLimitMiddleware",
    "RateLimitByEndpointMiddleware",
    "IPWhitelistMiddleware",
    "get_security_config",
    "is_safe_redirect_url",
    "sanitize_filename",
    "validate_content_type",
]
