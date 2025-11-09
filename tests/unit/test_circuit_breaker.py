"""
Unit tests for Circuit Breaker
Tests circuit breaker state transitions, failure detection, and recovery
"""

import pytest
import time
from unittest.mock import Mock, AsyncMock
import asyncio

from app.core.circuit_breaker import (
    CircuitBreaker,
    CircuitState,
    CircuitBreakerConfig,
    get_circuit_breaker_health
)
from app.core.exceptions import ExternalServiceError, CircuitBreakerOpenError


@pytest.mark.unit
class TestCircuitBreaker:
    """Test suite for Circuit Breaker"""

    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker instance for testing"""
        return CircuitBreaker(
            name="Test Service",
            failure_threshold=3,
            success_threshold=2,
            timeout=1,  # 1 second for fast tests
            expected_exceptions=(ExternalServiceError,)
        )

    def test_initial_state_is_closed(self, circuit_breaker):
        """Test circuit breaker starts in CLOSED state"""
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_successful_call_sync(self, circuit_breaker):
        """Test successful synchronous call through circuit breaker"""
        def successful_func():
            return "success"

        result = circuit_breaker.call(successful_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.stats.successful_calls == 1

    @pytest.mark.asyncio
    async def test_successful_call_async(self, circuit_breaker):
        """Test successful asynchronous call through circuit breaker"""
        async def successful_func():
            return "success"

        result = await circuit_breaker.call_async(successful_func)
        assert result == "success"
        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker.stats.successful_calls == 1

    def test_failed_call_increments_failure_count(self, circuit_breaker):
        """Test failed call increments failure counter"""
        def failing_func():
            raise ExternalServiceError("Service failed", service_name="Test")

        with pytest.raises(ExternalServiceError):
            circuit_breaker.call(failing_func)

        assert circuit_breaker.stats.failed_calls == 1
        assert circuit_breaker.state == CircuitState.CLOSED  # Still closed (threshold is 3)

    def test_circuit_opens_after_threshold(self, circuit_breaker):
        """Test circuit opens after reaching failure threshold"""
        def failing_func():
            raise ExternalServiceError("Service failed", service_name="Test")

        # Fail 3 times (threshold)
        for _ in range(3):
            with pytest.raises(ExternalServiceError):
                circuit_breaker.call(failing_func)

        # Circuit should now be OPEN
        assert circuit_breaker.state == CircuitState.OPEN
        assert circuit_breaker.stats.failed_calls == 3

    def test_open_circuit_rejects_calls(self, circuit_breaker):
        """Test open circuit rejects calls without executing function"""
        def failing_func():
            raise ExternalServiceError("Service failed", service_name="Test")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ExternalServiceError):
                circuit_breaker.call(failing_func)

        # Now try to call again - should be rejected
        call_executed = [False]

        def check_func():
            call_executed[0] = True
            return "should not execute"

        with pytest.raises(CircuitBreakerOpenError):
            circuit_breaker.call(check_func)

        assert not call_executed[0]  # Function should not have been called
        assert circuit_breaker.stats.rejected_calls == 1

    def test_circuit_transitions_to_half_open_after_timeout(self, circuit_breaker):
        """Test circuit transitions to HALF_OPEN after timeout"""
        def failing_func():
            raise ExternalServiceError("Service failed", service_name="Test")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ExternalServiceError):
                circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # Wait for timeout (1 second in test config)
        time.sleep(1.1)

        # Check state - should transition to HALF_OPEN
        assert circuit_breaker.state == CircuitState.HALF_OPEN

    def test_half_open_closes_after_success_threshold(self, circuit_breaker):
        """Test HALF_OPEN circuit closes after success threshold"""
        def failing_func():
            raise ExternalServiceError("Service failed", service_name="Test")

        def successful_func():
            return "success"

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ExternalServiceError):
                circuit_breaker.call(failing_func)

        # Wait for timeout
        time.sleep(1.1)
        assert circuit_breaker.state == CircuitState.HALF_OPEN

        # Succeed twice (success threshold is 2)
        circuit_breaker.call(successful_func)
        assert circuit_breaker.state == CircuitState.HALF_OPEN

        circuit_breaker.call(successful_func)
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_half_open_reopens_on_failure(self, circuit_breaker):
        """Test HALF_OPEN circuit reopens immediately on failure"""
        def failing_func():
            raise ExternalServiceError("Service failed", service_name="Test")

        def successful_func():
            return "success"

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ExternalServiceError):
                circuit_breaker.call(failing_func)

        # Wait for timeout
        time.sleep(1.1)
        assert circuit_breaker.state == CircuitState.HALF_OPEN

        # Try one successful call
        circuit_breaker.call(successful_func)
        assert circuit_breaker.state == CircuitState.HALF_OPEN

        # Fail once - should immediately reopen
        with pytest.raises(ExternalServiceError):
            circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

    def test_unexpected_exceptions_dont_trip_circuit(self, circuit_breaker):
        """Test unexpected exceptions don't count toward circuit breaker"""
        def unexpected_error():
            raise ValueError("Unexpected error")

        # This should raise the exception but not trip the circuit
        with pytest.raises(ValueError):
            circuit_breaker.call(unexpected_error)

        assert circuit_breaker.stats.failed_calls == 0
        assert circuit_breaker.state == CircuitState.CLOSED

    def test_manual_reset(self, circuit_breaker):
        """Test manual reset of circuit breaker"""
        def failing_func():
            raise ExternalServiceError("Service failed", service_name="Test")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ExternalServiceError):
                circuit_breaker.call(failing_func)

        assert circuit_breaker.state == CircuitState.OPEN

        # Manual reset
        circuit_breaker.reset()

        assert circuit_breaker.state == CircuitState.CLOSED
        assert circuit_breaker._failure_count == 0

    def test_health_status(self, circuit_breaker):
        """Test health status reporting"""
        health = circuit_breaker.get_health_status()

        assert health["name"] == "Test Service"
        assert health["state"] == "closed"
        assert health["is_healthy"] is True
        assert "config" in health
        assert "stats" in health

    def test_health_status_unhealthy_when_open(self, circuit_breaker):
        """Test health status reports unhealthy when circuit is open"""
        def failing_func():
            raise ExternalServiceError("Service failed", service_name="Test")

        # Open the circuit
        for _ in range(3):
            with pytest.raises(ExternalServiceError):
                circuit_breaker.call(failing_func)

        health = circuit_breaker.get_health_status()

        assert health["state"] == "open"
        assert health["is_healthy"] is False

    @pytest.mark.asyncio
    async def test_protect_decorator_async(self):
        """Test protect decorator with async function"""
        breaker = CircuitBreaker(
            name="Test Decorator",
            failure_threshold=2,
            timeout=1
        )

        @breaker.protect
        async def async_func():
            return "success"

        result = await async_func()
        assert result == "success"

    def test_protect_decorator_sync(self):
        """Test protect decorator with sync function"""
        breaker = CircuitBreaker(
            name="Test Decorator",
            failure_threshold=2,
            timeout=1
        )

        @breaker.protect
        def sync_func():
            return "success"

        result = sync_func()
        assert result == "success"

    def test_success_resets_failure_count_in_closed_state(self, circuit_breaker):
        """Test successful call resets failure count in CLOSED state"""
        def failing_func():
            raise ExternalServiceError("Service failed", service_name="Test")

        def successful_func():
            return "success"

        # Fail twice (not enough to open)
        for _ in range(2):
            with pytest.raises(ExternalServiceError):
                circuit_breaker.call(failing_func)

        assert circuit_breaker._failure_count == 2

        # One success should reset failure count
        circuit_breaker.call(successful_func)
        assert circuit_breaker._failure_count == 0

    def test_statistics_tracking(self, circuit_breaker):
        """Test comprehensive statistics tracking"""
        def failing_func():
            raise ExternalServiceError("Service failed", service_name="Test")

        def successful_func():
            return "success"

        # Mix of successful and failed calls
        circuit_breaker.call(successful_func)
        circuit_breaker.call(successful_func)

        try:
            circuit_breaker.call(failing_func)
        except ExternalServiceError:
            pass

        stats = circuit_breaker.stats

        assert stats.total_calls == 3
        assert stats.successful_calls == 2
        assert stats.failed_calls == 1
        assert stats.last_success_time is not None
        assert stats.last_failure_time is not None

    def test_global_circuit_breakers_health(self, reset_circuit_breakers):
        """Test global circuit breaker health check"""
        health = get_circuit_breaker_health()

        assert "overall_healthy" in health
        assert "breakers" in health
        assert "summary" in health

        # Should have multiple breakers (OpenRouter, Apify, Perplexity, Supabase)
        assert health["summary"]["total_breakers"] >= 4

    @pytest.mark.asyncio
    async def test_concurrent_calls_async(self):
        """Test circuit breaker with concurrent async calls"""
        breaker = CircuitBreaker(
            name="Concurrent Test",
            failure_threshold=5,
            timeout=1
        )

        call_count = [0]

        async def concurrent_func():
            call_count[0] += 1
            await asyncio.sleep(0.01)
            return "success"

        # Make 10 concurrent calls
        tasks = [breaker.call_async(concurrent_func) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(r == "success" for r in results)
        assert breaker.stats.successful_calls == 10

    def test_config_parameters(self):
        """Test circuit breaker with custom configuration"""
        breaker = CircuitBreaker(
            name="Custom Config",
            failure_threshold=10,
            success_threshold=5,
            timeout=60,
            expected_exceptions=(ExternalServiceError, ValueError)
        )

        assert breaker.config.failure_threshold == 10
        assert breaker.config.success_threshold == 5
        assert breaker.config.timeout == 60
        assert ValueError in breaker.config.expected_exceptions
