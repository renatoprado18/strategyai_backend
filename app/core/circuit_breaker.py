"""
Circuit Breaker Pattern Implementation for External API Resilience
Prevents cascading failures by failing fast when external services are down
"""

import time
import logging
from enum import Enum
from typing import Callable, Any, Optional
from datetime import datetime, timedelta
from functools import wraps
from dataclasses import dataclass, field

from app.core.exceptions import ExternalServiceError, CircuitBreakerOpenError
from app.core.constants import (
    CIRCUIT_BREAKER_FAILURE_THRESHOLD_DEFAULT,
    CIRCUIT_BREAKER_FAILURE_THRESHOLD_APIFY,
    CIRCUIT_BREAKER_FAILURE_THRESHOLD_SUPABASE,
    CIRCUIT_BREAKER_SUCCESS_THRESHOLD,
    CIRCUIT_BREAKER_TIMEOUT_DEFAULT,
    CIRCUIT_BREAKER_TIMEOUT_APIFY,
    CIRCUIT_BREAKER_TIMEOUT_SUPABASE
)

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"       # Normal operation
    OPEN = "open"          # Failing, rejecting requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior"""
    failure_threshold: int = CIRCUIT_BREAKER_FAILURE_THRESHOLD_DEFAULT  # Failures before opening circuit
    success_threshold: int = CIRCUIT_BREAKER_SUCCESS_THRESHOLD  # Successes in half-open before closing
    timeout: int = CIRCUIT_BREAKER_TIMEOUT_DEFAULT  # Seconds before trying again (half-open)
    expected_exceptions: tuple = (ExternalServiceError,)  # Exceptions that count as failures


@dataclass
class CircuitBreakerStats:
    """Statistics for monitoring circuit breaker health"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0  # Calls rejected when circuit open
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None


class CircuitBreaker:
    """
    Circuit Breaker implementation for external service calls

    States:
    - CLOSED: Normal operation, calls pass through
    - OPEN: Circuit tripped, calls fail fast without hitting service
    - HALF_OPEN: Testing if service recovered, limited calls pass through

    Example:
        breaker = CircuitBreaker(
            name="OpenRouter API",
            failure_threshold=5,
            timeout=60
        )

        @breaker.protect
        async def call_api():
            return await client.post(...)
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        success_threshold: int = 2,
        timeout: int = 60,
        expected_exceptions: tuple = (ExternalServiceError,)
    ):
        self.name = name
        self.config = CircuitBreakerConfig(
            failure_threshold=failure_threshold,
            success_threshold=success_threshold,
            timeout=timeout,
            expected_exceptions=expected_exceptions
        )

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[float] = None
        self._stats = CircuitBreakerStats()

        logger.info(
            f"[CIRCUIT BREAKER] Initialized for '{name}' "
            f"(threshold: {failure_threshold}, timeout: {timeout}s)"
        )

    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        # Check if we should transition from OPEN to HALF_OPEN
        if (
            self._state == CircuitState.OPEN
            and self._last_failure_time
            and (time.time() - self._last_failure_time) >= self.config.timeout
        ):
            logger.info(f"[CIRCUIT BREAKER] '{self.name}' transitioning to HALF_OPEN")
            self._state = CircuitState.HALF_OPEN
            self._success_count = 0  # Reset success counter

        return self._state

    @property
    def stats(self) -> CircuitBreakerStats:
        """Get circuit breaker statistics"""
        return self._stats

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection (sync)

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        current_state = self.state

        # Reject if circuit is OPEN
        if current_state == CircuitState.OPEN:
            self._stats.rejected_calls += 1
            logger.warning(
                f"[CIRCUIT BREAKER] '{self.name}' is OPEN, rejecting call "
                f"(rejections: {self._stats.rejected_calls})"
            )
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN. Service unavailable.",
                service_name=self.name
            )

        # Try the call
        self._stats.total_calls += 1
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result

        except self.config.expected_exceptions as e:
            self._on_failure()
            raise

        except Exception as e:
            # Unexpected exceptions don't count toward circuit breaker
            logger.error(
                f"[CIRCUIT BREAKER] '{self.name}' unexpected error: {e}",
                exc_info=True
            )
            raise

    async def call_async(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute async function with circuit breaker protection

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        current_state = self.state

        # Reject if circuit is OPEN
        if current_state == CircuitState.OPEN:
            self._stats.rejected_calls += 1
            logger.warning(
                f"[CIRCUIT BREAKER] '{self.name}' is OPEN, rejecting call "
                f"(rejections: {self._stats.rejected_calls})"
            )
            raise CircuitBreakerOpenError(
                f"Circuit breaker '{self.name}' is OPEN. Service unavailable.",
                service_name=self.name
            )

        # Try the call
        self._stats.total_calls += 1
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except self.config.expected_exceptions as e:
            self._on_failure()
            raise

        except Exception as e:
            # Unexpected exceptions don't count toward circuit breaker
            logger.error(
                f"[CIRCUIT BREAKER] '{self.name}' unexpected error: {e}",
                exc_info=True
            )
            raise

    def protect(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with circuit breaker (works with sync and async)

        Example:
            @breaker.protect
            async def call_api():
                return await client.post(...)
        """
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await self.call_async(func, *args, **kwargs)

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return self.call(func, *args, **kwargs)

        # Return appropriate wrapper based on function type
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    def _on_success(self):
        """Handle successful call"""
        self._stats.successful_calls += 1
        self._stats.last_success_time = datetime.utcnow()

        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1
            logger.info(
                f"[CIRCUIT BREAKER] '{self.name}' success in HALF_OPEN "
                f"({self._success_count}/{self.config.success_threshold})"
            )

            # Close circuit if enough successes
            if self._success_count >= self.config.success_threshold:
                logger.info(f"[CIRCUIT BREAKER] '{self.name}' transitioning to CLOSED")
                self._state = CircuitState.CLOSED
                self._failure_count = 0
                self._success_count = 0

        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            if self._failure_count > 0:
                logger.debug(f"[CIRCUIT BREAKER] '{self.name}' resetting failure count")
                self._failure_count = 0

    def _on_failure(self):
        """Handle failed call"""
        self._stats.failed_calls += 1
        self._stats.last_failure_time = datetime.utcnow()
        self._failure_count += 1
        self._last_failure_time = time.time()

        logger.warning(
            f"[CIRCUIT BREAKER] '{self.name}' failure "
            f"({self._failure_count}/{self.config.failure_threshold})"
        )

        # Open circuit if threshold reached
        if self._failure_count >= self.config.failure_threshold:
            logger.error(
                f"[CIRCUIT BREAKER] '{self.name}' threshold reached, "
                f"transitioning to OPEN"
            )
            self._state = CircuitState.OPEN

        # In HALF_OPEN, any failure immediately opens circuit
        elif self._state == CircuitState.HALF_OPEN:
            logger.warning(
                f"[CIRCUIT BREAKER] '{self.name}' failed in HALF_OPEN, "
                f"reopening circuit"
            )
            self._state = CircuitState.OPEN

    def reset(self):
        """Manually reset circuit breaker to CLOSED state"""
        logger.info(f"[CIRCUIT BREAKER] '{self.name}' manually reset to CLOSED")
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = None

    def get_health_status(self) -> dict:
        """
        Get health status for monitoring

        Returns:
            Dict with state, stats, and health indicators
        """
        success_rate = (
            (self._stats.successful_calls / self._stats.total_calls * 100)
            if self._stats.total_calls > 0
            else 0.0
        )

        return {
            "name": self.name,
            "state": self.state.value,
            "is_healthy": self.state == CircuitState.CLOSED,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "success_threshold": self.config.success_threshold,
                "timeout_seconds": self.config.timeout,
            },
            "stats": {
                "total_calls": self._stats.total_calls,
                "successful_calls": self._stats.successful_calls,
                "failed_calls": self._stats.failed_calls,
                "rejected_calls": self._stats.rejected_calls,
                "success_rate_percent": round(success_rate, 2),
                "last_failure": (
                    self._stats.last_failure_time.isoformat()
                    if self._stats.last_failure_time
                    else None
                ),
                "last_success": (
                    self._stats.last_success_time.isoformat()
                    if self._stats.last_success_time
                    else None
                ),
            },
        }


# ============================================================================
# Global Circuit Breaker Instances for Common Services
# ============================================================================

# OpenRouter API (LLM calls)
openrouter_breaker = CircuitBreaker(
    name="OpenRouter API",
    failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD_DEFAULT,
    success_threshold=CIRCUIT_BREAKER_SUCCESS_THRESHOLD,
    timeout=CIRCUIT_BREAKER_TIMEOUT_DEFAULT,
    expected_exceptions=(ExternalServiceError,)
)

# Apify API (Web scraping)
apify_breaker = CircuitBreaker(
    name="Apify API",
    failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD_APIFY,
    success_threshold=CIRCUIT_BREAKER_SUCCESS_THRESHOLD,
    timeout=CIRCUIT_BREAKER_TIMEOUT_APIFY,
    expected_exceptions=(ExternalServiceError,)
)

# Perplexity API (Research)
perplexity_breaker = CircuitBreaker(
    name="Perplexity API",
    failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD_DEFAULT,
    success_threshold=CIRCUIT_BREAKER_SUCCESS_THRESHOLD,
    timeout=CIRCUIT_BREAKER_TIMEOUT_DEFAULT,
    expected_exceptions=(ExternalServiceError,)
)

# Supabase Database
supabase_breaker = CircuitBreaker(
    name="Supabase Database",
    failure_threshold=CIRCUIT_BREAKER_FAILURE_THRESHOLD_SUPABASE,
    success_threshold=CIRCUIT_BREAKER_SUCCESS_THRESHOLD,
    timeout=CIRCUIT_BREAKER_TIMEOUT_SUPABASE,
    expected_exceptions=(ExternalServiceError,)
)


def get_all_circuit_breakers() -> list[CircuitBreaker]:
    """Get all registered circuit breakers for monitoring"""
    return [
        openrouter_breaker,
        apify_breaker,
        perplexity_breaker,
        supabase_breaker,
    ]


def get_circuit_breaker_health() -> dict:
    """
    Get health status of all circuit breakers

    Returns:
        Dict with overall health and individual breaker statuses
    """
    breakers = get_all_circuit_breakers()
    statuses = [breaker.get_health_status() for breaker in breakers]

    all_healthy = all(status["is_healthy"] for status in statuses)

    return {
        "overall_healthy": all_healthy,
        "breakers": statuses,
        "summary": {
            "total_breakers": len(breakers),
            "healthy_breakers": sum(1 for s in statuses if s["is_healthy"]),
            "open_breakers": sum(1 for s in statuses if s["state"] == "open"),
        },
    }
