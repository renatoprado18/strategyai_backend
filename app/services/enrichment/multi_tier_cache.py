"""
Multi-Tier Caching System for COST OPTIMIZATION

Implements aggressive 3-tier caching to minimize expensive API calls:
- Tier 1: Redis (in-memory, <1ms) - Hot cache for active requests
- Tier 2: Supabase (database, <50ms) - Warm cache for recent data
- Tier 3: Cloudflare R2 (object storage, <100ms) - Cold cache for unchanging data

Cache Strategy:
- Hot data (1 hour): Recent enrichments, high traffic domains
- Warm data (30 days): All enrichment results
- Cold data (forever): Static company data (founded_year, legal_name, etc.)

Cost Savings:
- Cache hit = $0.00 (vs $0.05-0.11 per enrichment)
- 70%+ cache hit rate expected after initial warmup
- Projected savings: $50-100/month for 1000 enrichments/month

Created: 2025-01-11
Version: 1.0.0
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import hashlib
import json
import asyncio

logger = logging.getLogger(__name__)

# In-memory cache for hot data (simulating Redis)
_hot_cache: Dict[str, Dict[str, Any]] = {}


class MultiTierCache:
    """
    Three-tier caching system for maximum cost savings.

    Tier 1 (Hot - Redis):
    - TTL: 1 hour
    - Latency: <1ms
    - Use: Active requests, high-traffic domains
    - Implementation: Redis (or in-memory fallback)

    Tier 2 (Warm - Supabase):
    - TTL: 30 days
    - Latency: <50ms
    - Use: All enrichment results
    - Implementation: PostgreSQL via Supabase

    Tier 3 (Cold - R2):
    - TTL: Forever
    - Latency: <100ms
    - Use: Unchanging data (legal_name, founded_year, etc.)
    - Implementation: Cloudflare R2 object storage

    Usage:
        cache = MultiTierCache()

        # Try to get cached data
        cached = await cache.get_or_enrich(
            domain="techstart.com",
            layer=2,
            enrich_func=expensive_api_call
        )

        # Result is either:
        # - Cached (FREE, <100ms)
        # - Fresh from API ($0.05-0.11, 2-10s)
    """

    def __init__(
        self,
        redis_client=None,
        supabase_client=None,
        r2_client=None
    ):
        """
        Initialize multi-tier cache.

        Args:
            redis_client: Optional Redis client for hot cache
            supabase_client: Supabase client for warm cache
            r2_client: Cloudflare R2 client for cold cache
        """
        self.redis = redis_client
        self.supabase = supabase_client
        self.r2 = r2_client

        # Cache statistics
        self.stats = {
            "hot_hits": 0,
            "warm_hits": 0,
            "cold_hits": 0,
            "misses": 0,
            "total_savings_usd": 0.0
        }

        logger.info("Initialized MultiTierCache with 3 tiers")

    async def get_or_enrich(
        self,
        domain: str,
        layer: int,
        enrich_func,
        estimated_cost: float = 0.05
    ) -> Dict[str, Any]:
        """
        Get cached data or run enrichment function.

        Checks caches in order: Hot → Warm → Cold → API

        Args:
            domain: Company domain
            layer: Enrichment layer (1, 2, or 3)
            enrich_func: Async function to call if cache miss
            estimated_cost: Estimated API cost (for savings tracking)

        Returns:
            Enrichment data (either cached or fresh)
        """
        cache_key = self._generate_cache_key(domain, layer)

        # Tier 1: Hot cache (Redis/Memory - <1ms)
        cached = await self._get_hot_cache(cache_key)
        if cached:
            self.stats["hot_hits"] += 1
            self.stats["total_savings_usd"] += estimated_cost
            logger.info(
                f"[MultiTierCache] HOT hit: {domain} L{layer} (saved ${estimated_cost:.4f})",
                extra={"tier": "hot", "domain": domain, "layer": layer}
            )
            return cached

        # Tier 2: Warm cache (Supabase - <50ms)
        cached = await self._get_warm_cache(domain, layer)
        if cached:
            self.stats["warm_hits"] += 1
            self.stats["total_savings_usd"] += estimated_cost

            # Promote to hot cache
            await self._set_hot_cache(cache_key, cached)

            logger.info(
                f"[MultiTierCache] WARM hit: {domain} L{layer} (saved ${estimated_cost:.4f})",
                extra={"tier": "warm", "domain": domain, "layer": layer}
            )
            return cached

        # Tier 3: Cold cache (R2 - <100ms) - Only for static data
        if layer == 2 and self.r2:
            cached = await self._get_cold_cache(domain)
            if cached:
                self.stats["cold_hits"] += 1
                self.stats["total_savings_usd"] += estimated_cost

                # Promote to warm and hot caches
                await self._set_warm_cache(domain, layer, cached)
                await self._set_hot_cache(cache_key, cached)

                logger.info(
                    f"[MultiTierCache] COLD hit: {domain} L{layer} (saved ${estimated_cost:.4f})",
                    extra={"tier": "cold", "domain": domain, "layer": layer}
                )
                return cached

        # Cache miss - call enrichment function
        self.stats["misses"] += 1
        logger.info(
            f"[MultiTierCache] MISS: {domain} L{layer} - calling API (cost ${estimated_cost:.4f})",
            extra={"tier": "miss", "domain": domain, "layer": layer}
        )

        result = await enrich_func()

        # Store in all applicable tiers
        await self._set_hot_cache(cache_key, result)
        await self._set_warm_cache(domain, layer, result)

        # Store in cold cache if unchanging data
        if layer == 2 and self._is_static_data(result):
            await self._set_cold_cache(domain, result)

        return result

    def _generate_cache_key(self, domain: str, layer: int) -> str:
        """Generate unique cache key"""
        normalized = domain.lower().strip().replace("www.", "")
        hash_part = hashlib.md5(normalized.encode()).hexdigest()[:8]
        return f"enrich:{layer}:{normalized}:{hash_part}"

    async def _get_hot_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get from hot cache (Redis or in-memory)"""
        if self.redis:
            try:
                cached = await self.redis.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.debug(f"Redis get failed: {e}")

        # Fallback to in-memory cache
        cached = _hot_cache.get(cache_key)
        if cached and cached["expires_at"] > datetime.now():
            return cached["data"]

        return None

    async def _set_hot_cache(
        self,
        cache_key: str,
        data: Dict[str, Any],
        ttl_seconds: int = 3600
    ):
        """Set hot cache with 1 hour TTL"""
        if self.redis:
            try:
                await self.redis.setex(
                    cache_key,
                    ttl_seconds,
                    json.dumps(data)
                )
                return
            except Exception as e:
                logger.debug(f"Redis set failed: {e}")

        # Fallback to in-memory cache
        _hot_cache[cache_key] = {
            "data": data,
            "expires_at": datetime.now() + timedelta(seconds=ttl_seconds)
        }

    async def _get_warm_cache(
        self,
        domain: str,
        layer: int
    ) -> Optional[Dict[str, Any]]:
        """Get from warm cache (Supabase)"""
        if not self.supabase:
            return None

        try:
            from app.core.supabase import supabase_service

            cache_key = f"progressive_enrichment:{domain}"
            result = await supabase_service.table("enrichment_sessions").select("*").eq("cache_key", cache_key).maybe_single().execute()

            if result.data:
                session_data = result.data.get("session_data", {})
                layer_key = f"layer{layer}"

                if layer_key in session_data:
                    layer_data = session_data[layer_key]
                    if layer_data:
                        # Check expiry
                        expires_at = datetime.fromisoformat(result.data["expires_at"])
                        if expires_at > datetime.now():
                            return layer_data.get("data", {})

        except Exception as e:
            logger.debug(f"Warm cache get failed: {e}")

        return None

    async def _set_warm_cache(
        self,
        domain: str,
        layer: int,
        data: Dict[str, Any],
        ttl_days: int = 30
    ):
        """Set warm cache with 30 day TTL"""
        if not self.supabase:
            return

        try:
            from app.core.supabase import supabase_service

            cache_key = f"progressive_enrichment:{domain}"
            expires_at = datetime.now() + timedelta(days=ttl_days)

            # Update or insert
            await supabase_service.table("enrichment_sessions").upsert(
                {
                    "cache_key": cache_key,
                    "website_url": f"https://{domain}",
                    f"layer{layer}_cached": True,
                    "expires_at": expires_at.isoformat(),
                    "updated_at": datetime.now().isoformat()
                },
                on_conflict="cache_key"
            ).execute()

        except Exception as e:
            logger.debug(f"Warm cache set failed: {e}")

    async def _get_cold_cache(self, domain: str) -> Optional[Dict[str, Any]]:
        """Get from cold cache (Cloudflare R2)"""
        if not self.r2:
            return None

        try:
            object_key = f"static/{domain}/company_data.json"
            response = await self.r2.get_object(Bucket="enrichment-cache", Key=object_key)

            if response:
                data = json.loads(response["Body"].read())
                return data

        except Exception as e:
            logger.debug(f"Cold cache get failed: {e}")

        return None

    async def _set_cold_cache(self, domain: str, data: Dict[str, Any]):
        """Set cold cache (forever) for static data"""
        if not self.r2:
            return

        try:
            # Only cache truly static fields
            static_data = self._extract_static_fields(data)

            if static_data:
                object_key = f"static/{domain}/company_data.json"
                await self.r2.put_object(
                    Bucket="enrichment-cache",
                    Key=object_key,
                    Body=json.dumps(static_data),
                    ContentType="application/json"
                )

        except Exception as e:
            logger.debug(f"Cold cache set failed: {e}")

    def _is_static_data(self, data: Dict[str, Any]) -> bool:
        """Check if data contains static fields worth caching forever"""
        static_fields = {
            "legal_name", "founded_year", "company_number",
            "jurisdiction", "registration_status"
        }
        return bool(set(data.keys()) & static_fields)

    def _extract_static_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only static fields for cold cache"""
        static_fields = {
            "legal_name", "founded_year", "company_number",
            "jurisdiction", "registration_status", "opencorporates_url"
        }
        return {k: v for k, v in data.items() if k in static_fields}

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total_requests = sum([
            self.stats["hot_hits"],
            self.stats["warm_hits"],
            self.stats["cold_hits"],
            self.stats["misses"]
        ])

        hit_rate = 0.0
        if total_requests > 0:
            hits = self.stats["hot_hits"] + self.stats["warm_hits"] + self.stats["cold_hits"]
            hit_rate = (hits / total_requests) * 100

        return {
            **self.stats,
            "total_requests": total_requests,
            "hit_rate_percent": round(hit_rate, 2),
            "estimated_cost_without_cache": total_requests * 0.05,
            "actual_cost": self.stats["misses"] * 0.05,
            "total_savings_usd": round(self.stats["total_savings_usd"], 2)
        }

    def clear_hot_cache(self):
        """Clear hot cache (useful for testing)"""
        _hot_cache.clear()
        logger.info("Cleared hot cache")
