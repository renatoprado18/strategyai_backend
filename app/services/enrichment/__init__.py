"""
IMENSIAH Data Enrichment System

This module provides comprehensive company data enrichment by aggregating
information from multiple public and paid data sources.

Architecture:
- Hybrid sync/async processing (quick 2-3s, deep 30s+)
- 30-day aggressive caching for cost optimization
- Full transparency with field-level source attribution
- Complete audit trail of all API calls
- Circuit breakers for reliability

Components:
- orchestrator.py: Main enrichment workflow coordinator
- cache.py: Multi-layer caching with 30-day TTL
- analytics.py: Cost and performance tracking
- models.py: Pydantic data models
- sources/: Individual data source clients

Usage:
    from app.services.enrichment import EnrichmentOrchestrator

    orchestrator = EnrichmentOrchestrator()

    # Quick enrichment (sync - 2-3s)
    quick_data = await orchestrator.enrich_quick("https://company.com")

    # Deep enrichment (async - 30s+)
    deep_data = await orchestrator.enrich_deep("https://company.com", enrichment_id=123)

Created: 2025-01-09
Version: 1.0.0
"""

from .orchestrator import EnrichmentOrchestrator
from .cache import EnrichmentCache
from .analytics import EnrichmentAnalytics
from .models import (
    EnrichmentData,
    QuickEnrichmentData,
    DeepEnrichmentData,
)
from .sources.base import SourceResult

__all__ = [
    "EnrichmentOrchestrator",
    "EnrichmentCache",
    "EnrichmentAnalytics",
    "EnrichmentData",
    "QuickEnrichmentData",
    "DeepEnrichmentData",
    "SourceResult",
]

__version__ = "1.0.0"
