"""
Security Middleware - Request size limits and security headers
Protects against common web vulnerabilities and DoS attacks
"""

import logging
from typing import Callable

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.constants import (
    REQUEST_MAX_SIZE_BYTES,
    REQUEST_MAX_SIZE_MB
)

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Adds security headers to all responses

    Headers added:
    - X-Content-Type-Options: nosniff
    - X-Frame-Options: DENY
    - X-XSS-Protection: 1; mode=block
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
    - Content-Security-Policy: default-src 'self'
    - Referrer-Policy: strict-origin-when-cross-origin
    - Permissions-Policy: geolocation=(), microphone=(), camera=()
    """

    def __init__(
        self,
        app: ASGIApp,
        enable_hsts: bool = True,
        enable_csp: bool = False,  # CSP can break frontend, enable carefully
    ):
        super().__init__(app)
        self.enable_hsts = enable_hsts
        self.enable_csp = enable_csp

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # Enable browser XSS protection (legacy but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # HTTP Strict Transport Security (HTTPS only)
        if self.enable_hsts:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        # Content Security Policy (restrictive, test before enabling)
        if self.enable_csp:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )

        # Referrer policy - control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy - restrict browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # Remove server header (security through obscurity)
        response.headers.pop("Server", None)

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """
    Limits request body size to prevent DoS attacks

    Features:
    - Configurable max size per request
    - Different limits for different endpoints (optional)
    - Clear error messages for oversized requests
    """

    def __init__(
        self,
        app: ASGIApp,
        max_request_size: int = REQUEST_MAX_SIZE_BYTES,
    ):
        super().__init__(app)
        self.max_request_size = max_request_size

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Check Content-Length header
        content_length = request.headers.get("content-length")

        if content_length:
            content_length = int(content_length)

            if content_length > self.max_request_size:
                size_mb = content_length / (1024 * 1024)
                max_mb = self.max_request_size / (1024 * 1024)

                logger.warning(
                    f"Request too large: {size_mb:.2f}MB (max: {max_mb:.2f}MB)",
                    extra={
                        "path": request.url.path,
                        "method": request.method,
                        "content_length": content_length,
                        "client_host": request.client.host if request.client else None,
                    }
                )

                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "Request entity too large",
                        "message": f"Request size ({size_mb:.2f}MB) exceeds maximum allowed size ({max_mb:.2f}MB)",
                        "max_size_mb": max_mb,
                        "your_size_mb": round(size_mb, 2),
                    }
                )

        return await call_next(request)


class RateLimitByEndpointMiddleware(BaseHTTPMiddleware):
    """
    Adds rate limit headers to responses
    Actual rate limiting is done by Upstash Redis in routes

    Headers added:
    - X-RateLimit-Limit: Max requests allowed
    - X-RateLimit-Remaining: Remaining requests
    - X-RateLimit-Reset: Timestamp when limit resets
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)

        # Rate limit info can be set by route handlers
        # We just ensure the headers are present for API clients
        if "X-RateLimit-Limit" not in response.headers:
            # Default headers (actual limits enforced in routes)
            response.headers["X-RateLimit-Limit"] = "100"
            response.headers["X-RateLimit-Remaining"] = "99"

        return response


class IPWhitelistMiddleware(BaseHTTPMiddleware):
    """
    Optional: Restrict access to specific IP addresses
    Useful for admin endpoints or internal APIs

    Usage:
        app.add_middleware(
            IPWhitelistMiddleware,
            allowed_ips=["127.0.0.1", "10.0.0.0/8"],
            protected_paths=["/admin", "/api/admin"]
        )
    """

    def __init__(
        self,
        app: ASGIApp,
        allowed_ips: list[str] = None,
        protected_paths: list[str] = None,
    ):
        super().__init__(app)
        self.allowed_ips = allowed_ips or []
        self.protected_paths = protected_paths or []

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip if no restrictions configured
        if not self.allowed_ips or not self.protected_paths:
            return await call_next(request)

        # Check if path is protected
        path = request.url.path
        is_protected = any(path.startswith(protected) for protected in self.protected_paths)

        if is_protected:
            client_ip = request.client.host if request.client else None

            # Check X-Forwarded-For header (for proxies/load balancers)
            forwarded_for = request.headers.get("X-Forwarded-For")
            if forwarded_for:
                # Take the first IP (client IP)
                client_ip = forwarded_for.split(",")[0].strip()

            if client_ip not in self.allowed_ips:
                logger.warning(
                    f"IP {client_ip} attempted to access protected path {path}",
                    extra={
                        "client_ip": client_ip,
                        "path": path,
                        "method": request.method,
                    }
                )

                raise HTTPException(
                    status_code=403,
                    detail="Access denied: IP address not whitelisted"
                )

        return await call_next(request)


# ============================================================================
# SECURITY CONFIGURATION
# ============================================================================

def get_security_config() -> dict:
    """
    Get current security configuration for monitoring

    Returns:
        Dict with security settings and status
    """
    return {
        "request_limits": {
            "max_request_size_bytes": REQUEST_MAX_SIZE_BYTES,
            "max_request_size_mb": REQUEST_MAX_SIZE_MB,
        },
        "security_headers": {
            "x_content_type_options": "nosniff",
            "x_frame_options": "DENY",
            "x_xss_protection": "1; mode=block",
            "hsts": "enabled",
            "referrer_policy": "strict-origin-when-cross-origin",
            "permissions_policy": "restrictive",
        },
        "features": {
            "request_size_limits": True,
            "security_headers": True,
            "rate_limit_headers": True,
            "ip_whitelist": False,  # Disabled by default
        },
    }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def is_safe_redirect_url(url: str, allowed_hosts: list[str]) -> bool:
    """
    Check if a redirect URL is safe (prevents open redirect vulnerabilities)

    Args:
        url: URL to check
        allowed_hosts: List of allowed host domains

    Returns:
        True if URL is safe to redirect to
    """
    from urllib.parse import urlparse

    # Allow relative URLs
    if url.startswith("/"):
        return True

    # Parse absolute URL
    try:
        parsed = urlparse(url)

        # No scheme or host = relative URL
        if not parsed.scheme and not parsed.netloc:
            return True

        # Check if host is in allowed list
        if parsed.netloc in allowed_hosts:
            return True

        return False

    except Exception:
        # If parsing fails, reject
        return False


def sanitize_filename(filename: str) -> str:
    """
    Sanitize uploaded filename to prevent directory traversal

    Args:
        filename: Original filename

    Returns:
        Sanitized filename safe for filesystem
    """
    import os
    import re

    # Remove directory paths
    filename = os.path.basename(filename)

    # Remove non-alphanumeric characters (keep dots, dashes, underscores)
    filename = re.sub(r"[^\w\s\-\.]", "", filename)

    # Remove leading/trailing whitespace and dots
    filename = filename.strip(". ")

    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:250] + ext

    # Fallback if empty
    if not filename:
        filename = "upload.txt"

    return filename


def validate_content_type(
    content_type: str,
    allowed_types: list[str]
) -> bool:
    """
    Validate Content-Type header against allowed types

    Args:
        content_type: Content-Type header value
        allowed_types: List of allowed MIME types

    Returns:
        True if content type is allowed

    Example:
        allowed = ["application/json", "multipart/form-data"]
        is_valid = validate_content_type(request.headers.get("content-type"), allowed)
    """
    if not content_type:
        return False

    # Extract main type (ignore charset and other parameters)
    main_type = content_type.split(";")[0].strip().lower()

    return main_type in allowed_types
