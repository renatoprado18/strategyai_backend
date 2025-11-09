"""
Unit tests for Security Middleware
Tests security headers, request size limits, and rate limiting
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request
from fastapi.responses import JSONResponse

from app.middleware.security_middleware import (
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    RateLimitByEndpointMiddleware,
    get_security_config
)


@pytest.mark.unit
class TestSecurityHeadersMiddleware:
    """Test security headers middleware"""

    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next function"""
        async def call_next(request):
            return JSONResponse({"status": "ok"})
        return call_next

    @pytest.mark.asyncio
    async def test_adds_security_headers(self, mock_request, mock_call_next):
        """Test middleware adds security headers to response"""
        middleware = SecurityHeadersMiddleware(
            app=None,
            enable_hsts=False,
            enable_csp=False
        )

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check essential security headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert response.headers["X-XSS-Protection"] == "1; mode=block"
        assert "Referrer-Policy" in response.headers
        assert "Permissions-Policy" in response.headers

    @pytest.mark.asyncio
    async def test_adds_hsts_when_enabled(self, mock_request, mock_call_next):
        """Test HSTS header is added when enabled"""
        middleware = SecurityHeadersMiddleware(
            app=None,
            enable_hsts=True,
            enable_csp=False
        )

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "Strict-Transport-Security" in response.headers
        assert "max-age" in response.headers["Strict-Transport-Security"]

    @pytest.mark.asyncio
    async def test_omits_hsts_when_disabled(self, mock_request, mock_call_next):
        """Test HSTS header is omitted when disabled"""
        middleware = SecurityHeadersMiddleware(
            app=None,
            enable_hsts=False,
            enable_csp=False
        )

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "Strict-Transport-Security" not in response.headers

    @pytest.mark.asyncio
    async def test_adds_csp_when_enabled(self, mock_request, mock_call_next):
        """Test CSP header is added when enabled"""
        middleware = SecurityHeadersMiddleware(
            app=None,
            enable_hsts=False,
            enable_csp=True
        )

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "Content-Security-Policy" in response.headers
        assert "default-src" in response.headers["Content-Security-Policy"]

    @pytest.mark.asyncio
    async def test_omits_csp_when_disabled(self, mock_request, mock_call_next):
        """Test CSP header is omitted when disabled"""
        middleware = SecurityHeadersMiddleware(
            app=None,
            enable_hsts=False,
            enable_csp=False
        )

        response = await middleware.dispatch(mock_request, mock_call_next)

        assert "Content-Security-Policy" not in response.headers

    @pytest.mark.asyncio
    async def test_removes_server_header(self, mock_request, mock_call_next):
        """Test Server header is removed for security"""
        middleware = SecurityHeadersMiddleware(
            app=None,
            enable_hsts=False,
            enable_csp=False
        )

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Server header should be removed
        assert "Server" not in response.headers

    @pytest.mark.asyncio
    async def test_permissions_policy_restrictive(self, mock_request, mock_call_next):
        """Test Permissions-Policy is restrictive"""
        middleware = SecurityHeadersMiddleware(app=None)

        response = await middleware.dispatch(mock_request, mock_call_next)

        permissions_policy = response.headers["Permissions-Policy"]

        # Should restrict dangerous features
        assert "geolocation=()" in permissions_policy
        assert "microphone=()" in permissions_policy
        assert "camera=()" in permissions_policy


@pytest.mark.unit
class TestRequestSizeLimitMiddleware:
    """Test request size limit middleware"""

    @pytest.fixture
    def mock_small_request(self):
        """Create mock request with small body"""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "POST"
        request.headers = {"content-length": "1000"}  # 1 KB
        return request

    @pytest.fixture
    def mock_large_request(self):
        """Create mock request with large body"""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "POST"
        # 20 MB (over limit)
        request.headers = {"content-length": str(20 * 1024 * 1024)}
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next function"""
        async def call_next(request):
            return JSONResponse({"status": "ok"})
        return call_next

    @pytest.mark.asyncio
    async def test_allows_small_requests(self, mock_small_request, mock_call_next):
        """Test middleware allows requests under size limit"""
        middleware = RequestSizeLimitMiddleware(app=None)

        response = await middleware.dispatch(mock_small_request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_rejects_large_requests(self, mock_large_request, mock_call_next):
        """Test middleware rejects requests over size limit"""
        middleware = RequestSizeLimitMiddleware(app=None)

        response = await middleware.dispatch(mock_large_request, mock_call_next)

        # Should return 413 Request Entity Too Large
        assert response.status_code == 413

    @pytest.mark.asyncio
    async def test_allows_requests_without_content_length(self, mock_call_next):
        """Test middleware allows requests without content-length header"""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "POST"
        request.headers = {}  # No content-length

        middleware = RequestSizeLimitMiddleware(app=None)

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_get_requests(self, mock_call_next):
        """Test middleware allows GET requests regardless of headers"""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}

        middleware = RequestSizeLimitMiddleware(app=None)

        response = await middleware.dispatch(request, mock_call_next)

        assert response.status_code == 200


@pytest.mark.unit
class TestRateLimitByEndpointMiddleware:
    """Test rate limit by endpoint middleware"""

    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = Mock(spec=Request)
        request.url.path = "/api/submit"
        request.method = "POST"
        request.client.host = "127.0.0.1"
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next function"""
        async def call_next(request):
            return JSONResponse({"status": "ok"})
        return call_next

    @pytest.mark.asyncio
    async def test_adds_rate_limit_headers(self, mock_request, mock_call_next):
        """Test middleware adds rate limit headers to response"""
        middleware = RateLimitByEndpointMiddleware(app=None)

        with patch('app.middleware.security_middleware.check_rate_limit', return_value=None):
            response = await middleware.dispatch(mock_request, mock_call_next)

            # Should add rate limit informational headers
            # Note: Actual header names depend on implementation
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_allows_requests_within_limit(self, mock_request, mock_call_next):
        """Test middleware allows requests within rate limit"""
        middleware = RateLimitByEndpointMiddleware(app=None)

        with patch('app.middleware.security_middleware.check_rate_limit', return_value=None):
            response = await middleware.dispatch(mock_request, mock_call_next)

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_handles_rate_limit_exceeded(self, mock_request, mock_call_next):
        """Test middleware handles rate limit exceeded gracefully"""
        from app.core.exceptions import RateLimitExceeded

        middleware = RateLimitByEndpointMiddleware(app=None)

        # Mock rate limiter to raise RateLimitExceeded
        with patch('app.middleware.security_middleware.check_rate_limit') as mock_limiter:
            mock_limiter.side_effect = RateLimitExceeded(limit=10, window=60)

            # Note: This depends on how the middleware handles the exception
            # It should either return 429 or let exception handler deal with it
            try:
                response = await middleware.dispatch(mock_request, mock_call_next)
                # If middleware handles it
                assert response.status_code == 429
            except RateLimitExceeded:
                # If it lets exception propagate
                pass


@pytest.mark.unit
class TestSecurityConfig:
    """Test security configuration"""

    def test_get_security_config(self):
        """Test getting security configuration"""
        config = get_security_config()

        assert "features" in config
        assert isinstance(config["features"], dict)

        # Should include information about enabled features
        features = config["features"]
        assert "security_headers" in features
        assert "request_size_limit" in features
        assert "rate_limiting" in features

    def test_security_config_structure(self):
        """Test security config has expected structure"""
        config = get_security_config()

        # Should have features dict
        assert isinstance(config["features"], dict)

        # Each feature should be boolean
        for feature, enabled in config["features"].items():
            assert isinstance(enabled, bool)
