"""
Base Classes for IMENSIAH Data Enrichment Sources

Provides:
- SourceResult: Standardized result model for all data sources
- EnrichmentSource: Abstract base class that all sources inherit from

All data sources must implement the `enrich()` method and will automatically
get monitoring, circuit breaking, and audit logging through `enrich_with_monitoring()`.

Created: 2025-01-09
Version: 1.0.0
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
import time
import logging
from app.core.circuit_breaker import CircuitBreaker

logger = logging.getLogger(__name__)


class SourceResult(BaseModel):
    """
    Standardized result from any enrichment source.

    All data sources return this model to ensure consistency
    across the system and enable transparent audit logging.

    Attributes:
        source_name: Identifier for the data source (e.g., "clearbit", "receita_ws")
        success: Whether the enrichment call succeeded
        data: Enriched data fields (None if failed)
        error_message: Human-readable error message (None if successful)
        error_type: Error classification (None if successful)
        duration_ms: Time taken for the call in milliseconds
        cost_usd: Cost of this API call in USD
        cached: Whether this result came from cache
    """

    source_name: str = Field(..., description="Name of the data source")
    success: bool = Field(..., description="Whether the call succeeded")
    data: Optional[Dict[str, Any]] = Field(
        None, description="Enriched data fields"
    )
    error_message: Optional[str] = Field(
        None, description="Error message if failed"
    )
    error_type: Optional[str] = Field(
        None, description="Error type classification"
    )
    duration_ms: int = Field(..., description="Duration in milliseconds", ge=0)
    cost_usd: float = Field(0.0, description="Cost in USD", ge=0)
    cached: bool = Field(False, description="Whether from cache")

    class Config:
        json_schema_extra = {
            "example": {
                "source_name": "clearbit",
                "success": True,
                "data": {
                    "company_name": "TechStart Innovations",
                    "employee_count": "25-50",
                    "industry": "Technology",
                },
                "error_message": None,
                "error_type": None,
                "duration_ms": 1200,
                "cost_usd": 0.10,
                "cached": False,
            }
        }


class EnrichmentSource(ABC):
    """
    Abstract base class for all enrichment data sources.

    Provides:
    - Circuit breaker for reliability
    - Monitoring and timing
    - Cost tracking
    - Standardized error handling

    Subclasses must implement:
    - enrich(domain, **kwargs) -> SourceResult

    Usage:
        class MySource(EnrichmentSource):
            def __init__(self):
                super().__init__(name="my_source", cost_per_call=0.05)

            async def enrich(self, domain: str, **kwargs) -> SourceResult:
                # Fetch data from API
                data = await self._fetch_from_api(domain)
                return SourceResult(
                    source_name=self.name,
                    success=True,
                    data=data,
                    duration_ms=int((time.time() - start) * 1000),
                    cost_usd=self.cost_per_call
                )

        # Use it:
        source = MySource()
        result = await source.enrich_with_monitoring("techstart.com")
    """

    def __init__(self, name: str, cost_per_call: float = 0.0):
        """
        Initialize enrichment source.

        Args:
            name: Unique identifier for this source (e.g., "clearbit")
            cost_per_call: Cost per API call in USD (default 0 for free sources)
        """
        self.name = name
        self.cost_per_call = cost_per_call
        self.circuit_breaker = CircuitBreaker(name=f"enrichment_{name}")

        logger.info(
            f"Initialized enrichment source: {name} "
            f"(cost: ${cost_per_call:.4f})"
        )

    @abstractmethod
    async def enrich(self, domain: str, **kwargs) -> SourceResult:
        """
        Fetch enrichment data for a domain.

        This is the core method that subclasses must implement.
        It should:
        1. Fetch data from the external source
        2. Parse and normalize the response
        3. Return a SourceResult with the enriched data

        Args:
            domain: Domain to enrich (e.g., "techstart.com")
            **kwargs: Additional parameters specific to this source

        Returns:
            SourceResult with enriched data or error information

        Raises:
            Exception: Any errors should be raised and will be caught
                      by enrich_with_monitoring()
        """
        pass

    async def enrich_with_monitoring(
        self, domain: str, **kwargs
    ) -> SourceResult:
        """
        Wrapper around enrich() that adds:
        - Timing measurement
        - Circuit breaker protection
        - Error handling and logging
        - Audit trail preparation

        This method should be called by consumers instead of enrich() directly.

        Args:
            domain: Domain to enrich
            **kwargs: Additional parameters to pass to enrich()

        Returns:
            SourceResult with complete monitoring data
        """
        start_time = time.time()

        # Check circuit breaker state
        if self.circuit_breaker.state == "open":
            logger.warning(
                f"Circuit breaker OPEN for {self.name} - failing fast"
            )
            return SourceResult(
                source_name=self.name,
                success=False,
                error_message="Circuit breaker open - service unavailable",
                error_type="circuit_breaker",
                duration_ms=0,
                cost_usd=0.0,
            )

        try:
            # Log enrichment attempt
            logger.info(
                f"Enriching domain '{domain}' with source '{self.name}'"
            )

            # Call the actual enrichment method
            result = await self.enrich(domain, **kwargs)

            # Record success in circuit breaker
            self.circuit_breaker.record_success()

            # Log success
            logger.info(
                f"Successfully enriched '{domain}' with '{self.name}' "
                f"in {result.duration_ms}ms (cost: ${result.cost_usd:.4f})"
            )

            return result

        except Exception as e:
            # Record failure in circuit breaker
            self.circuit_breaker.record_failure()

            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)

            # Determine error type
            error_type = type(e).__name__

            # Log error with full context
            logger.error(
                f"Failed to enrich '{domain}' with '{self.name}': "
                f"{error_type} - {str(e)}",
                exc_info=True,
                extra={
                    "domain": domain,
                    "source": self.name,
                    "error_type": error_type,
                    "duration_ms": duration_ms,
                },
            )

            # Return failure result
            return SourceResult(
                source_name=self.name,
                success=False,
                error_message=str(e),
                error_type=error_type,
                duration_ms=duration_ms,
                cost_usd=0.0,  # No cost on failure
            )

    def __repr__(self) -> str:
        """String representation for logging and debugging."""
        return (
            f"EnrichmentSource(name='{self.name}', "
            f"cost=${self.cost_per_call:.4f}, "
            f"circuit_state='{self.circuit_breaker.state}')"
        )
