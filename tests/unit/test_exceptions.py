"""
Unit tests for Custom Exceptions
Tests exception classes and error handling patterns
"""

import pytest
from fastapi import HTTPException

from app.core.exceptions import (
    StrategyAIException,
    ValidationError,
    ExternalServiceError,
    RateLimitExceeded,
    ResourceNotFound,
    CircuitBreakerOpenError
)


@pytest.mark.unit
class TestExceptions:
    """Test custom exception classes"""

    def test_base_exception(self):
        """Test base StrategyAIException"""
        exc = StrategyAIException("Test error")

        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"

    def test_validation_error(self):
        """Test ValidationError exception"""
        exc = ValidationError("Invalid input")

        assert str(exc) == "Invalid input"
        assert exc.status_code == 400
        assert exc.error_code == "VALIDATION_ERROR"

    def test_external_service_error(self):
        """Test ExternalServiceError exception"""
        exc = ExternalServiceError(
            "API call failed",
            service_name="OpenRouter"
        )

        assert "API call failed" in str(exc)
        assert exc.service_name == "OpenRouter"
        assert exc.status_code == 502
        assert exc.error_code == "EXTERNAL_SERVICE_ERROR"

    def test_external_service_error_without_service_name(self):
        """Test ExternalServiceError without service name"""
        exc = ExternalServiceError("Service failed")

        assert "Service failed" in str(exc)
        assert exc.service_name == "Unknown"

    def test_rate_limit_exceeded(self):
        """Test RateLimitExceeded exception"""
        exc = RateLimitExceeded(
            limit=10,
            window=60,
            retry_after=30
        )

        assert exc.limit == 10
        assert exc.window == 60
        assert exc.retry_after == 30
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"

    def test_rate_limit_exceeded_message(self):
        """Test RateLimitExceeded error message formatting"""
        exc = RateLimitExceeded(limit=5, window=60)

        assert "5" in str(exc)
        assert "60" in str(exc)

    def test_resource_not_found(self):
        """Test ResourceNotFound exception"""
        exc = ResourceNotFound(
            resource_type="Submission",
            resource_id=123
        )

        assert exc.resource_type == "Submission"
        assert exc.resource_id == 123
        assert exc.status_code == 404
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert "Submission" in str(exc)
        assert "123" in str(exc)

    def test_circuit_breaker_open_error(self):
        """Test CircuitBreakerOpenError exception"""
        exc = CircuitBreakerOpenError(
            "Service unavailable",
            service_name="OpenRouter API"
        )

        assert exc.service_name == "OpenRouter API"
        assert exc.status_code == 503
        assert exc.error_code == "CIRCUIT_BREAKER_OPEN"
        assert "OpenRouter API" in str(exc)

    def test_exception_to_dict(self):
        """Test exception to dictionary conversion"""
        exc = ValidationError("Invalid email format")

        exc_dict = exc.to_dict()

        assert exc_dict["error"] == "Invalid email format"
        assert exc_dict["error_code"] == "VALIDATION_ERROR"
        assert exc_dict["status_code"] == 400

    def test_exception_with_details(self):
        """Test exception with additional details"""
        exc = ValidationError(
            "Invalid input",
            details={"field": "email", "reason": "Not a valid email"}
        )

        exc_dict = exc.to_dict()

        assert exc_dict["details"] == {"field": "email", "reason": "Not a valid email"}

    def test_exception_inheritance(self):
        """Test exception inheritance hierarchy"""
        # All custom exceptions should inherit from StrategyAIException
        assert issubclass(ValidationError, StrategyAIException)
        assert issubclass(ExternalServiceError, StrategyAIException)
        assert issubclass(RateLimitExceeded, StrategyAIException)
        assert issubclass(ResourceNotFound, StrategyAIException)
        assert issubclass(CircuitBreakerOpenError, StrategyAIException)

    def test_exception_can_be_raised_and_caught(self):
        """Test exceptions can be raised and caught properly"""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Test validation error")

        assert exc_info.value.message == "Test validation error"
        assert exc_info.value.status_code == 400

    def test_exception_preserves_original_exception(self):
        """Test exception can wrap original exception"""
        original_error = ValueError("Original error")

        exc = ExternalServiceError(
            "Service failed",
            service_name="TestService",
            original_exception=original_error
        )

        assert exc.original_exception == original_error
