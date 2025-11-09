"""
Enrichment Caching Layer for IMENSIAH System

Implements aggressive 30-day caching with multi-layer strategy:
1. In-memory cache (fastest)
2. Database cache (persistent)

Provides massive cost savings by avoiding redundant API calls
to expensive data sources like Clearbit, Google Places, and Proxycurl.

Created: 2025-01-09
Version: 1.0.0
"""

from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import logging
from .models import QuickEnrichmentData, DeepEnrichmentData
from app.core.supabase import supabase_service

logger = logging.getLogger(__name__)

# In-memory cache (cleared on server restart)
_in_memory_cache: Dict[str, Dict[str, Any]] = {}


class EnrichmentCache:
    """
    30-day TTL cache for enrichment results.

    Implements two-layer caching:
    1. In-memory: Fastest, but cleared on restart
    2. Database: Persistent, survives restarts

    Cache hits provide massive cost savings:
    - Quick enrichment: $0.00 saved (free sources)
    - Deep enrichment: $0.10-0.15 saved per hit

    Usage:
        cache = EnrichmentCache(ttl_days=30)

        # Check cache
        cached = await cache.get_quick("techstart.com")
        if cached:
            return cached  # Cache hit - free!

        # Run expensive enrichment
        result = await expensive_enrichment()

        # Store for future
        await cache.set_quick("techstart.com", result)
    """

    def __init__(self, ttl_days: int = 30):
        """
        Initialize enrichment cache.

        Args:
            ttl_days: Cache time-to-live in days (default 30)
        """
        self.ttl_days = ttl_days
        logger.info(f"Initialized EnrichmentCache with {ttl_days}-day TTL")

    def _generate_cache_key(self, domain: str, enrichment_type: str) -> str:
        """
        Generate unique cache key for a domain and enrichment type.

        Args:
            domain: Domain name (e.g., "techstart.com")
            enrichment_type: "quick" or "deep"

        Returns:
            Cache key in format: "enrichment:{type}:{domain}:{hash}"
        """
        # Normalize domain (lowercase, strip whitespace)
        normalized = domain.lower().strip().replace("www.", "")

        # Create hash for uniqueness
        hash_part = hashlib.md5(normalized.encode()).hexdigest()[:12]

        # Format: enrichment:quick:techstart.com:a3f2b1c4d5e6
        cache_key = f"enrichment:{enrichment_type}:{normalized}:{hash_part}"

        return cache_key

    async def get_quick(
        self, domain: str
    ) -> Optional[QuickEnrichmentData]:
        """
        Get quick enrichment from cache.

        Checks in-memory cache first (fast), then database (persistent).

        Args:
            domain: Domain to look up

        Returns:
            QuickEnrichmentData if found and not expired, None otherwise
        """
        cache_key = self._generate_cache_key(domain, "quick")

        # Check in-memory cache first (fastest)
        cached = _in_memory_cache.get(cache_key)
        if cached and cached["expires_at"] > datetime.now():
            logger.info(
                f"Quick enrichment cache HIT (in-memory): {domain}",
                extra={"cache_key": cache_key, "source": "memory"},
            )
            return QuickEnrichmentData(**cached["data"])

        # Check database cache (persistent)
        try:
            result = (
                await supabase_service.table("enrichment_results")
                .select("*")
                .eq("cache_key", cache_key)
                .not_.is_("quick_data", "null")
                .maybe_single()
                .execute()
            )

            if (
                result.data
                and datetime.fromisoformat(result.data["expires_at"])
                > datetime.now()
            ):
                logger.info(
                    f"Quick enrichment cache HIT (database): {domain}",
                    extra={
                        "cache_key": cache_key,
                        "source": "database",
                        "enrichment_id": result.data["id"],
                    },
                )

                # Store in memory for next time
                _in_memory_cache[cache_key] = {
                    "data": result.data["quick_data"],
                    "expires_at": datetime.fromisoformat(
                        result.data["expires_at"]
                    ),
                }

                # Increment hit counter
                await supabase_service.table("enrichment_results").update(
                    {
                        "cache_hits": result.data["cache_hits"] + 1,
                        "cache_savings_usd": result.data["cache_savings_usd"]
                        + result.data["total_cost_usd"],
                        "updated_at": datetime.now().isoformat(),
                    }
                ).eq("id", result.data["id"]).execute()

                return QuickEnrichmentData(**result.data["quick_data"])

        except Exception as e:
            logger.error(
                f"Error checking database cache for {domain}: {e}",
                exc_info=True,
            )

        logger.info(
            f"Quick enrichment cache MISS: {domain}",
            extra={"cache_key": cache_key},
        )
        return None

    async def set_quick(
        self, domain: str, data: QuickEnrichmentData
    ) -> None:
        """
        Store quick enrichment in cache.

        Args:
            domain: Domain that was enriched
            data: Quick enrichment data to cache
        """
        cache_key = self._generate_cache_key(domain, "quick")
        expires_at = datetime.now() + timedelta(days=self.ttl_days)

        try:
            # Store in database
            await supabase_service.table("enrichment_results").upsert(
                {
                    "cache_key": cache_key,
                    "website": data.website,
                    "domain": domain,
                    "quick_data": data.dict(exclude_none=True),
                    "quick_completed_at": datetime.now().isoformat(),
                    "quick_duration_ms": data.quick_duration_ms,
                    "source_attribution": data.source_attribution,
                    "completeness_score": data.completeness_score,
                    "confidence_score": data.confidence_score,
                    "data_quality_tier": data.data_quality_tier,
                    "total_cost_usd": data.total_cost_usd,
                    "sources_called": [s.dict() for s in data.sources_called],
                    "cache_hits": 0,
                    "cache_savings_usd": 0.0,
                    "expires_at": expires_at.isoformat(),
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                },
                on_conflict="cache_key",
            ).execute()

            # Store in memory
            _in_memory_cache[cache_key] = {
                "data": data.dict(exclude_none=True),
                "expires_at": expires_at,
            }

            logger.info(
                f"Quick enrichment cached: {domain} (expires: {expires_at})",
                extra={
                    "cache_key": cache_key,
                    "ttl_days": self.ttl_days,
                    "cost": data.total_cost_usd,
                },
            )

        except Exception as e:
            logger.error(
                f"Error caching quick enrichment for {domain}: {e}",
                exc_info=True,
            )

    async def get_deep(
        self, domain: str
    ) -> Optional[DeepEnrichmentData]:
        """
        Get deep enrichment from cache.

        Args:
            domain: Domain to look up

        Returns:
            DeepEnrichmentData if found and not expired, None otherwise
        """
        cache_key = self._generate_cache_key(domain, "deep")

        # Check in-memory cache first
        cached = _in_memory_cache.get(cache_key)
        if cached and cached["expires_at"] > datetime.now():
            logger.info(
                f"Deep enrichment cache HIT (in-memory): {domain}",
                extra={"cache_key": cache_key, "source": "memory"},
            )
            return DeepEnrichmentData(**cached["data"])

        # Check database cache
        try:
            result = (
                await supabase_service.table("enrichment_results")
                .select("*")
                .eq("cache_key", cache_key)
                .not_.is_("deep_data", "null")
                .maybe_single()
                .execute()
            )

            if (
                result.data
                and datetime.fromisoformat(result.data["expires_at"])
                > datetime.now()
            ):
                logger.info(
                    f"Deep enrichment cache HIT (database): {domain}",
                    extra={
                        "cache_key": cache_key,
                        "source": "database",
                        "enrichment_id": result.data["id"],
                        "cost_saved": result.data["total_cost_usd"],
                    },
                )

                # Merge quick + deep data
                merged_data = {
                    **(result.data.get("quick_data") or {}),
                    **(result.data["deep_data"]),
                }

                # Store in memory
                _in_memory_cache[cache_key] = {
                    "data": merged_data,
                    "expires_at": datetime.fromisoformat(
                        result.data["expires_at"]
                    ),
                }

                # Increment hit counter
                await supabase_service.table("enrichment_results").update(
                    {
                        "cache_hits": result.data["cache_hits"] + 1,
                        "cache_savings_usd": result.data["cache_savings_usd"]
                        + result.data["total_cost_usd"],
                        "updated_at": datetime.now().isoformat(),
                    }
                ).eq("id", result.data["id"]).execute()

                return DeepEnrichmentData(**merged_data)

        except Exception as e:
            logger.error(
                f"Error checking database cache for {domain}: {e}",
                exc_info=True,
            )

        logger.info(
            f"Deep enrichment cache MISS: {domain}",
            extra={"cache_key": cache_key},
        )
        return None

    async def set_deep(
        self, domain: str, data: DeepEnrichmentData
    ) -> int:
        """
        Store deep enrichment in cache.

        Args:
            domain: Domain that was enriched
            data: Deep enrichment data to cache

        Returns:
            Enrichment ID from database
        """
        cache_key = self._generate_cache_key(domain, "deep")
        expires_at = datetime.now() + timedelta(days=self.ttl_days)

        try:
            # Store in database
            result = await supabase_service.table("enrichment_results").upsert(
                {
                    "cache_key": cache_key,
                    "website": data.website,
                    "domain": domain,
                    "deep_data": data.dict(exclude_none=True),
                    "deep_completed_at": datetime.now().isoformat(),
                    "deep_duration_ms": data.deep_duration_ms,
                    "source_attribution": data.source_attribution,
                    "completeness_score": data.completeness_score,
                    "confidence_score": data.confidence_score,
                    "data_quality_tier": data.data_quality_tier,
                    "total_cost_usd": data.total_cost_usd,
                    "sources_called": [s.dict() for s in data.sources_called],
                    "cache_hits": 0,
                    "cache_savings_usd": 0.0,
                    "expires_at": expires_at.isoformat(),
                    "updated_at": datetime.now().isoformat(),
                },
                on_conflict="cache_key",
            ).execute()

            # Store in memory
            _in_memory_cache[cache_key] = {
                "data": data.dict(exclude_none=True),
                "expires_at": expires_at,
            }

            enrichment_id = result.data[0]["id"] if result.data else None

            logger.info(
                f"Deep enrichment cached: {domain} (expires: {expires_at})",
                extra={
                    "cache_key": cache_key,
                    "enrichment_id": enrichment_id,
                    "ttl_days": self.ttl_days,
                    "cost": data.total_cost_usd,
                },
            )

            return enrichment_id

        except Exception as e:
            logger.error(
                f"Error caching deep enrichment for {domain}: {e}",
                exc_info=True,
            )
            return None

    async def clear_expired(self) -> int:
        """
        Clear expired cache entries from database.

        Returns:
            Number of entries deleted
        """
        try:
            result = (
                await supabase_service.table("enrichment_results")
                .delete()
                .lt("expires_at", datetime.now().isoformat())
                .execute()
            )

            count = len(result.data) if result.data else 0

            logger.info(
                f"Cleared {count} expired enrichment cache entries",
                extra={"deleted_count": count},
            )

            return count

        except Exception as e:
            logger.error(f"Error clearing expired cache: {e}", exc_info=True)
            return 0

    def clear_memory_cache(self) -> None:
        """Clear in-memory cache (useful for testing)"""
        _in_memory_cache.clear()
        logger.info("Cleared in-memory enrichment cache")
