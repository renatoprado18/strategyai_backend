"""
Data Source Clients for IMENSIAH Enrichment System

Each source implements the EnrichmentSource abstract base class and provides
standardized enrichment data through the SourceResult model.

Data Sources:
-----------

FREE SOURCES (Quick Enrichment):
- MetadataSource: Website metadata, tech stack, description
- IpApiSource: IP geolocation, location data

FREE SOURCES (Deep Enrichment):
- ReceitaWSSource: Brazilian CNPJ lookup, company registration data

PAID SOURCES (Deep Enrichment):
- ClearbitSource: Company enrichment, employee count, industry
- GooglePlacesSource: Location verification, business details
- ProxycurlSource: LinkedIn data extraction

Architecture Pattern:
--------------------
All sources follow the same interface:

    class MySource(EnrichmentSource):
        async def enrich(self, domain: str, **kwargs) -> SourceResult:
            # Fetch data from API
            # Return standardized SourceResult

        # Inherited from base class:
        # - enrich_with_monitoring(): Adds timing, errors, circuit breaker
        # - circuit_breaker: Prevents cascading failures
        # - cost_per_call: Cost tracking

Usage:
------
    from app.services.enrichment.sources import MetadataSource

    source = MetadataSource()
    result = await source.enrich_with_monitoring("techstart.com")

    print(f"Success: {result.success}")
    print(f"Data: {result.data}")
    print(f"Cost: ${result.cost_usd}")
    print(f"Duration: {result.duration_ms}ms")

Created: 2025-01-09
Version: 1.0.0
"""

from .base import EnrichmentSource, SourceResult
from .metadata import MetadataSource
from .ip_api import IpApiSource
from .receita_ws import ReceitaWSSource
from .clearbit import ClearbitSource
from .google_places import GooglePlacesSource
from .proxycurl import ProxycurlSource

__all__ = [
    # Base classes
    "EnrichmentSource",
    "SourceResult",
    # Free sources
    "MetadataSource",
    "IpApiSource",
    "ReceitaWSSource",
    # Paid sources
    "ClearbitSource",
    "GooglePlacesSource",
    "ProxycurlSource",
]
