"""
Unit tests for Logging Middleware
Tests correlation ID management, structured logging, and request tracing
"""

import pytest
import uuid
from unittest.mock import Mock, patch, MagicMock
from fastapi import Request, Response
from fastapi.responses import JSONResponse

from app.middleware.logging_middleware import (
    CorrelationIdMiddleware,
    StructuredLoggerAdapter,
    get_logger,
    get_correlation_id,
    get_user_id,
    get_request_path,
    configure_structured_logging,
    JSONFormatter,
    correlation_id_var,
    user_id_var,
    request_path_var
)


@pytest.mark.unit
class TestCorrelationIdMiddleware:
    """Test correlation ID middleware"""

    @pytest.fixture
    def mock_request(self):
        """Create mock request"""
        request = Mock(spec=Request)
        request.url.path = "/api/test"
        request.method = "GET"
        request.headers = {}
        request.client.host = "127.0.0.1"
        request.state = Mock()
        request.state.user = None
        return request

    @pytest.fixture
    def mock_call_next(self):
        """Create mock call_next function"""
        async def call_next(request):
            return JSONResponse({"status": "ok"})
        return call_next

    @pytest.mark.asyncio
    async def test_generates_correlation_id_if_missing(self, mock_request, mock_call_next):
        """Test middleware generates correlation ID if not provided"""
        middleware = CorrelationIdMiddleware(app=None, header_name="X-Correlation-ID")

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Check that correlation ID was added to response
        assert "X-Correlation-ID" in response.headers
        # Verify it's a valid UUID
        correlation_id = response.headers["X-Correlation-ID"]
        uuid.UUID(correlation_id)  # Should not raise

    @pytest.mark.asyncio
    async def test_preserves_existing_correlation_id(self, mock_request, mock_call_next):
        """Test middleware preserves correlation ID from request"""
        existing_id = "test-correlation-id-123"
        mock_request.headers = {"X-Correlation-ID": existing_id}

        middleware = CorrelationIdMiddleware(app=None, header_name="X-Correlation-ID")

        response = await middleware.dispatch(mock_request, mock_call_next)

        # Should use the provided correlation ID
        assert response.headers["X-Correlation-ID"] == existing_id

    @pytest.mark.asyncio
    async def test_sets_context_variables(self, mock_request, mock_call_next):
        """Test middleware sets context variables"""
        middleware = CorrelationIdMiddleware(app=None)

        # Capture context variables during request processing
        captured_correlation_id = None
        captured_path = None

        original_call_next = mock_call_next

        async def capturing_call_next(request):
            nonlocal captured_correlation_id, captured_path
            captured_correlation_id = correlation_id_var.get()
            captured_path = request_path_var.get()
            return await original_call_next(request)

        await middleware.dispatch(mock_request, capturing_call_next)

        # Verify context variables were set
        assert captured_correlation_id is not None
        assert captured_path == "/api/test"

    @pytest.mark.asyncio
    async def test_extracts_user_id_from_authenticated_request(self, mock_request, mock_call_next):
        """Test middleware extracts user ID from authenticated request"""
        mock_user = Mock()
        mock_user.id = "user-123"
        mock_request.state.user = mock_user

        middleware = CorrelationIdMiddleware(app=None)

        captured_user_id = None

        async def capturing_call_next(request):
            nonlocal captured_user_id
            captured_user_id = user_id_var.get()
            return await mock_call_next(request)

        await middleware.dispatch(mock_request, capturing_call_next)

        assert captured_user_id == "user-123"

    @pytest.mark.asyncio
    async def test_logs_request_start_and_completion(self, mock_request, mock_call_next):
        """Test middleware logs request start and completion"""
        middleware = CorrelationIdMiddleware(app=None)

        with patch('app.middleware.logging_middleware.logger') as mock_logger:
            await middleware.dispatch(mock_request, mock_call_next)

            # Should log request started and completed
            assert mock_logger.info.call_count >= 2

            # Check log messages
            calls = [str(call) for call in mock_logger.info.call_args_list]
            assert any("Request started" in str(call) for call in calls)
            assert any("Request completed" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_logs_errors_with_exception_info(self, mock_request):
        """Test middleware logs unhandled exceptions"""
        async def failing_call_next(request):
            raise ValueError("Test error")

        middleware = CorrelationIdMiddleware(app=None)

        with patch('app.middleware.logging_middleware.logger') as mock_logger:
            with pytest.raises(ValueError):
                await middleware.dispatch(mock_request, failing_call_next)

            # Should log error with exception info
            mock_logger.error.assert_called_once()
            call_args = mock_logger.error.call_args
            assert "Request failed" in str(call_args)


@pytest.mark.unit
class TestStructuredLoggerAdapter:
    """Test structured logger adapter"""

    def test_logger_includes_correlation_id(self):
        """Test logger includes correlation ID in extra fields"""
        # Set correlation ID in context
        correlation_id_var.set("test-correlation-123")

        logger = get_logger(__name__)
        assert isinstance(logger, StructuredLoggerAdapter)

        # Process a log message
        msg, kwargs = logger.process("Test message", {})

        # Should include correlation ID in extra
        assert "correlation_id" in kwargs.get("extra", {})
        assert kwargs["extra"]["correlation_id"] == "test-correlation-123"

    def test_logger_includes_user_id(self):
        """Test logger includes user ID in extra fields"""
        # Set user ID in context
        user_id_var.set("user-456")

        logger = get_logger(__name__)

        msg, kwargs = logger.process("Test message", {})

        assert "user_id" in kwargs.get("extra", {})
        assert kwargs["extra"]["user_id"] == "user-456"

    def test_logger_includes_request_path(self):
        """Test logger includes request path in extra fields"""
        # Set request path in context
        request_path_var.set("/api/test/endpoint")

        logger = get_logger(__name__)

        msg, kwargs = logger.process("Test message", {})

        assert "request_path" in kwargs.get("extra", {})
        assert kwargs["extra"]["request_path"] == "/api/test/endpoint"

    def test_logger_preserves_existing_extra(self):
        """Test logger preserves existing extra fields"""
        correlation_id_var.set("test-123")

        logger = get_logger(__name__)

        msg, kwargs = logger.process("Test", {"extra": {"custom": "field"}})

        # Should include both correlation ID and custom field
        assert kwargs["extra"]["correlation_id"] == "test-123"
        assert kwargs["extra"]["custom"] == "field"


@pytest.mark.unit
class TestContextHelpers:
    """Test context helper functions"""

    def test_get_correlation_id(self):
        """Test getting correlation ID from context"""
        correlation_id_var.set("test-corr-123")
        assert get_correlation_id() == "test-corr-123"

    def test_get_user_id(self):
        """Test getting user ID from context"""
        user_id_var.set("user-789")
        assert get_user_id() == "user-789"

    def test_get_request_path(self):
        """Test getting request path from context"""
        request_path_var.set("/api/submissions")
        assert get_request_path() == "/api/submissions"

    def test_context_vars_return_none_when_not_set(self):
        """Test context vars return None when not set"""
        # Reset context
        correlation_id_var.set(None)
        user_id_var.set(None)
        request_path_var.set(None)

        assert get_correlation_id() is None
        assert get_user_id() is None
        assert get_request_path() is None


@pytest.mark.unit
class TestJSONFormatter:
    """Test JSON log formatter"""

    def test_formats_log_as_json(self):
        """Test formatter outputs valid JSON"""
        import logging
        import json

        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )

        formatted = formatter.format(record)

        # Should be valid JSON
        parsed = json.loads(formatted)

        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed
        assert "logger" in parsed

    def test_includes_correlation_id_if_present(self):
        """Test formatter includes correlation ID from record"""
        import logging
        import json

        formatter = JSONFormatter()

        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.correlation_id = "test-123"

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["correlation_id"] == "test-123"

    def test_includes_exception_info(self):
        """Test formatter includes exception info"""
        import logging
        import json

        formatter = JSONFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="test.py",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=exc_info
            )

            formatted = formatter.format(record)
            parsed = json.loads(formatted)

            assert "exception" in parsed
            assert "ValueError" in parsed["exception"]


@pytest.mark.unit
class TestLoggingConfiguration:
    """Test logging configuration"""

    def test_configure_structured_logging_text_format(self):
        """Test configuring logging with text format"""
        configure_structured_logging(app_name="test-app", json_format=False)

        # Should not raise any errors
        import logging
        logger = logging.getLogger("test-app")
        assert logger is not None

    def test_configure_structured_logging_json_format(self):
        """Test configuring logging with JSON format"""
        configure_structured_logging(app_name="test-app", json_format=True)

        # Should not raise any errors
        import logging
        logger = logging.getLogger("test-app")
        assert logger is not None
