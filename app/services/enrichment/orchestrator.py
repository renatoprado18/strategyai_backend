"""
Enrichment Orchestrator for IMENSIAH System

Coordinates multi-source data enrichment with hybrid sync/async pattern:
- Quick enrichment (sync - 2-3s): Fast sources for immediate response
- Deep enrichment (async - 30s+): All sources for comprehensive data

Responsibilities:
- Execute enrichment workflow
- Merge results from multiple sources
- Calculate quality metrics
- Manage caching
- Log audit trail
- Handle errors gracefully

Created: 2025-01-09
Version: 1.0.0
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlparse

from .models import (
    QuickEnrichmentData,
    DeepEnrichmentData,
    SourceCallInfo,
    DataQualityTier,
)
from .cache import EnrichmentCache
from .analytics import EnrichmentAnalytics
from .sources import (
    MetadataSource,
    IpApiSource,
    ReceitaWSSource,
    ClearbitSource,
    GooglePlacesSource,
    ProxycurlSource,
)

logger = logging.getLogger(__name__)


class EnrichmentOrchestrator:
    """
    Orchestrates multi-source data enrichment with hybrid sync/async flow.

    Architecture:
    ------------
    QUICK ENRICHMENT (Sync - 2-3s):
    └─> Metadata + IP API (free, fast) → Immediate response

    DEEP ENRICHMENT (Async - 30s+):
    └─> All sources in parallel → Complete enrichment

    Quality Scoring:
    ---------------
    - Completeness: % of fields populated
    - Confidence: Weighted by source reliability
    - Quality Tier: minimal/moderate/high/excellent

    Usage:
    ------
        orchestrator = EnrichmentOrchestrator()

        # Quick enrichment (returns immediately)
        quick_data = await orchestrator.enrich_quick("https://techstart.com")

        # Deep enrichment (background processing)
        deep_data = await orchestrator.enrich_deep(
            "https://techstart.com",
            enrichment_id=123
        )
    """

    # Source reliability weights (for confidence scoring)
    SOURCE_WEIGHTS = {
        "clearbit": 0.95,  # Very reliable
        "google_places": 0.90,  # Verified by Google
        "receita_ws": 0.95,  # Official government data
        "proxycurl": 0.85,  # LinkedIn data (good)
        "metadata": 0.70,  # Self-reported
        "ip_api": 0.60,  # IP-based guess
    }

    def __init__(self):
        """Initialize enrichment orchestrator with all data sources"""
        # Initialize cache and analytics
        self.cache = EnrichmentCache(ttl_days=30)
        self.analytics = EnrichmentAnalytics()

        # Initialize quick sources (free, fast)
        self.quick_sources = [
            MetadataSource(),  # ~400ms
            IpApiSource(),  # ~150ms
        ]

        # Initialize deep sources (paid/slow, comprehensive)
        self.deep_sources = [
            ClearbitSource(),  # ~1.5s, $0.10
            GooglePlacesSource(),  # ~1.5s, $0.02
            ProxycurlSource(),  # ~4s, $0.03
            ReceitaWSSource(),  # ~2.5s, free
        ]

        logger.info(
            f"EnrichmentOrchestrator initialized: "
            f"{len(self.quick_sources)} quick sources, "
            f"{len(self.deep_sources)} deep sources"
        )

    async def enrich_quick(
        self, website: str
    ) -> QuickEnrichmentData:
        """
        SYNC quick enrichment (2-3 seconds).

        Uses only fast/free sources for immediate "wow" moment.

        Args:
            website: Company website URL

        Returns:
            QuickEnrichmentData with basic company info

        Raises:
            Exception: If enrichment fails completely
        """
        start_time = time.time()
        domain = self._extract_domain(website)

        logger.info(
            f"Starting QUICK enrichment for: {domain}",
            extra={"domain": domain, "website": website},
        )

        # Check cache first
        cached = await self.cache.get_quick(domain)
        if cached:
            await self.analytics.record_cache_hit("quick", cached.total_cost_usd)
            logger.info(
                f"Quick enrichment cache HIT for {domain} "
                f"(saved ${cached.total_cost_usd:.4f})",
                extra={"domain": domain, "cache_hit": True},
            )
            return cached

        # Run quick sources in parallel
        logger.debug(
            f"Running {len(self.quick_sources)} quick sources in parallel",
            extra={"domain": domain, "sources": len(self.quick_sources)},
        )

        results = await asyncio.gather(*[
            source.enrich_with_monitoring(domain)
            for source in self.quick_sources
        ], return_exceptions=True)

        # Filter out exceptions (log but don't fail)
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                source_name = self.quick_sources[i].name
                logger.warning(
                    f"Quick source '{source_name}' failed: {result}",
                    extra={"domain": domain, "source": source_name},
                )
            else:
                valid_results.append(result)

        # Merge results
        enriched_data = self._merge_quick_results(
            valid_results, website, domain
        )

        # Calculate quality metrics
        enriched_data.completeness_score = self._calculate_completeness(
            enriched_data.dict(exclude_none=True)
        )
        enriched_data.confidence_score = self._calculate_confidence(
            valid_results
        )
        enriched_data.data_quality_tier = self._determine_quality_tier(
            enriched_data.completeness_score
        )

        # Set timing
        duration_ms = int((time.time() - start_time) * 1000)
        enriched_data.quick_completed_at = datetime.now()
        enriched_data.quick_duration_ms = duration_ms

        # Cache result
        await self.cache.set_quick(domain, enriched_data)

        logger.info(
            f"Quick enrichment complete for {domain}: "
            f"{enriched_data.completeness_score:.1f}% complete "
            f"in {duration_ms}ms (cost: ${enriched_data.total_cost_usd:.4f})",
            extra={
                "domain": domain,
                "duration_ms": duration_ms,
                "completeness": enriched_data.completeness_score,
                "cost": enriched_data.total_cost_usd,
            },
        )

        return enriched_data

    async def enrich_deep(
        self,
        website: str,
        enrichment_id: Optional[int] = None,
        company_name: Optional[str] = None,
        city: Optional[str] = None,
    ) -> DeepEnrichmentData:
        """
        ASYNC deep enrichment (30+ seconds).

        Uses all sources (free + paid) for comprehensive data.

        Args:
            website: Company website URL
            enrichment_id: Enrichment record ID (for updates)
            company_name: Company name (helps with Google Places, Proxycurl)
            city: City name (helps with Google Places)

        Returns:
            DeepEnrichmentData with comprehensive company info

        Raises:
            Exception: If enrichment fails completely
        """
        start_time = time.time()
        domain = self._extract_domain(website)

        logger.info(
            f"Starting DEEP enrichment for: {domain}",
            extra={
                "domain": domain,
                "enrichment_id": enrichment_id,
                "company_name": company_name,
            },
        )

        # Check cache first
        cached = await self.cache.get_deep(domain)
        if cached:
            await self.analytics.record_cache_hit("deep", cached.total_cost_usd)
            logger.info(
                f"Deep enrichment cache HIT for {domain} "
                f"(saved ${cached.total_cost_usd:.4f})",
                extra={"domain": domain, "cache_hit": True},
            )
            return cached

        # Get quick data (from cache or run it)
        quick_data = await self.cache.get_quick(domain)
        if not quick_data:
            quick_data = await self.enrich_quick(website)

        # Prepare kwargs for sources that need extra params
        source_kwargs = {
            "company_name": company_name or quick_data.company_name,
            "city": city,
            "linkedin_url": None,  # TODO: Extract from quick_data if available
            "cnpj": None,  # TODO: Check if we have it
        }

        # Run deep sources in parallel
        logger.debug(
            f"Running {len(self.deep_sources)} deep sources in parallel",
            extra={
                "domain": domain,
                "sources": len(self.deep_sources),
                "company_name": source_kwargs["company_name"],
            },
        )

        tasks = []
        for source in self.deep_sources:
            # Pass relevant kwargs to each source
            if source.name == "google_places":
                task = source.enrich_with_monitoring(
                    domain,
                    company_name=source_kwargs["company_name"],
                    city=source_kwargs["city"],
                )
            elif source.name == "proxycurl":
                task = source.enrich_with_monitoring(
                    domain,
                    company_name=source_kwargs["company_name"],
                    linkedin_url=source_kwargs["linkedin_url"],
                )
            elif source.name == "receita_ws":
                task = source.enrich_with_monitoring(
                    domain,
                    company_name=source_kwargs["company_name"],
                    cnpj=source_kwargs["cnpj"],
                )
            else:
                task = source.enrich_with_monitoring(domain)

            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions
        valid_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                source_name = self.deep_sources[i].name
                logger.warning(
                    f"Deep source '{source_name}' failed: {result}",
                    extra={"domain": domain, "source": source_name},
                )
            else:
                valid_results.append(result)

        # Merge results (include quick data)
        all_results = valid_results + [
            source_call_to_result(call, quick_data.source_attribution)
            for call in quick_data.sources_called
        ]

        enriched_data = self._merge_deep_results(
            all_results, quick_data, website, domain
        )

        # Calculate quality metrics
        enriched_data.completeness_score = self._calculate_completeness(
            enriched_data.dict(exclude_none=True)
        )
        enriched_data.confidence_score = self._calculate_confidence(
            all_results
        )
        enriched_data.data_quality_tier = self._determine_quality_tier(
            enriched_data.completeness_score
        )

        # Set timing
        duration_ms = int((time.time() - start_time) * 1000)
        enriched_data.deep_completed_at = datetime.now()
        enriched_data.deep_duration_ms = duration_ms

        # Copy quick timing
        enriched_data.quick_completed_at = quick_data.quick_completed_at
        enriched_data.quick_duration_ms = quick_data.quick_duration_ms

        # Cache result
        enrichment_id = await self.cache.set_deep(domain, enriched_data)

        logger.info(
            f"Deep enrichment complete for {domain}: "
            f"{enriched_data.completeness_score:.1f}% complete "
            f"in {duration_ms}ms (cost: ${enriched_data.total_cost_usd:.4f})",
            extra={
                "domain": domain,
                "enrichment_id": enrichment_id,
                "duration_ms": duration_ms,
                "completeness": enriched_data.completeness_score,
                "cost": enriched_data.total_cost_usd,
            },
        )

        return enriched_data

    def _extract_domain(self, website: str) -> str:
        """
        Extract clean domain from website URL.

        Args:
            website: Full URL or domain

        Returns:
            Clean domain (e.g., "techstart.com")
        """
        # Add protocol if missing
        if not website.startswith(("http://", "https://")):
            website = f"https://{website}"

        # Parse URL
        parsed = urlparse(website)
        domain = parsed.netloc or parsed.path

        # Remove www.
        domain = domain.replace("www.", "")

        return domain.lower().strip()

    def _merge_quick_results(
        self,
        results: List[Any],
        website: str,
        domain: str,
    ) -> QuickEnrichmentData:
        """Merge results from quick sources"""
        merged = QuickEnrichmentData(
            website=website,
            domain=domain,
        )
        source_attribution = {}

        # Merge data from each source
        for result in results:
            if result.success and result.data:
                for field, value in result.data.items():
                    # Only set if not already set (first source wins)
                    if value and not getattr(merged, field, None):
                        try:
                            setattr(merged, field, value)
                            source_attribution[field] = result.source_name
                        except AttributeError:
                            # Field not in model, skip
                            logger.debug(
                                f"Skipping unknown field '{field}' from {result.source_name}"
                            )
                            pass

        merged.source_attribution = source_attribution
        merged.total_cost_usd = sum(r.cost_usd for r in results)
        merged.sources_called = [
            SourceCallInfo(
                name=r.source_name,
                success=r.success,
                cost=r.cost_usd,
                duration_ms=r.duration_ms,
                cached=r.cached,
                error_type=r.error_type,
            )
            for r in results
        ]

        return merged

    def _merge_deep_results(
        self,
        results: List[Any],
        quick_data: QuickEnrichmentData,
        website: str,
        domain: str,
    ) -> DeepEnrichmentData:
        """Merge results from all sources (quick + deep)"""
        # Start with quick data as base
        merged_dict = quick_data.dict(exclude_none=True)
        merged = DeepEnrichmentData(**merged_dict)

        # Update with deep source data
        for result in results:
            if result.success and result.data:
                for field, value in result.data.items():
                    # Deep sources can override quick sources
                    if value:
                        try:
                            setattr(merged, field, value)
                            merged.source_attribution[field] = result.source_name
                        except AttributeError:
                            pass

        # Update cost and sources
        merged.total_cost_usd = sum(r.cost_usd for r in results)
        merged.sources_called = [
            SourceCallInfo(
                name=r.source_name,
                success=r.success,
                cost=r.cost_usd,
                duration_ms=r.duration_ms,
                cached=r.cached,
                error_type=r.error_type,
            )
            for r in results
        ]

        return merged

    def _calculate_completeness(self, data: Dict[str, Any]) -> float:
        """
        Calculate completeness score (0-100%).

        Based on how many optional fields are populated.
        """
        # Count populated fields (exclude meta fields)
        exclude_fields = {
            "source_attribution",
            "sources_called",
            "total_cost_usd",
            "completeness_score",
            "confidence_score",
            "data_quality_tier",
            "quick_completed_at",
            "deep_completed_at",
            "quick_duration_ms",
            "deep_duration_ms",
            "website",
            "domain",
        }

        populated = sum(
            1
            for k, v in data.items()
            if k not in exclude_fields and v is not None
        )

        # Total possible fields (approximate)
        total_fields = 40  # Based on DeepEnrichmentData model

        score = (populated / total_fields) * 100
        return min(100.0, score)  # Cap at 100%

    def _calculate_confidence(self, results: List[Any]) -> float:
        """
        Calculate confidence score (0-100%).

        Weighted average based on source reliability.
        """
        if not results:
            return 0.0

        weighted_sum = 0.0
        weight_total = 0.0

        for result in results:
            if result.success:
                weight = self.SOURCE_WEIGHTS.get(result.source_name, 0.5)
                weighted_sum += weight
                weight_total += 1.0

        if weight_total == 0:
            return 0.0

        # Average weighted by number of successful sources
        confidence = (weighted_sum / weight_total) * 100
        return min(100.0, confidence)

    def _determine_quality_tier(
        self, completeness_score: float
    ) -> DataQualityTier:
        """Determine quality tier from completeness score"""
        if completeness_score >= 90:
            return DataQualityTier.EXCELLENT
        elif completeness_score >= 70:
            return DataQualityTier.HIGH
        elif completeness_score >= 40:
            return DataQualityTier.MODERATE
        else:
            return DataQualityTier.MINIMAL


def source_call_to_result(call: SourceCallInfo, attribution: Dict[str, str]):
    """Convert SourceCallInfo back to result-like object"""
    class FakeResult:
        def __init__(self, call):
            self.source_name = call.name
            self.success = call.success
            self.cost_usd = call.cost
            self.duration_ms = call.duration_ms
            self.cached = call.cached
            self.error_type = call.error_type
            self.data = {}

    return FakeResult(call)
