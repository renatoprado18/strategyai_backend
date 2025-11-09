"""
Enrichment Repository for IMENSIAH Data Enrichment System

Domain-specific repository for managing enrichment_results records.
Provides comprehensive data access methods for enrichment workflows.

Created: 2025-01-09
Version: 1.0.0
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import json

from app.repositories.supabase_repository import SupabaseRepository
from app.core.exceptions import DatabaseError, ResourceNotFound
from app.services.enrichment.models import (
    QuickEnrichmentData,
    DeepEnrichmentData,
    DataQualityTier,
)

logger = logging.getLogger(__name__)


class EnrichmentRepository(SupabaseRepository):
    """
    Repository for enrichment_results table

    Manages enrichment data with 30-day cache TTL and comprehensive
    tracking of API costs, source attribution, and quality metrics.

    Key Features:
    - Save/retrieve quick and deep enrichment results
    - Cache management with automatic expiration
    - Cost and quality tracking
    - Domain-based lookups
    - Statistics for admin dashboard

    Usage:
        repo = EnrichmentRepository()

        # Save quick enrichment
        enrichment_id = await repo.save_quick_enrichment(
            domain="techstart.com",
            data=quick_data
        )

        # Get by domain
        result = await repo.get_by_domain("techstart.com")

        # Clear expired cache
        await repo.clear_expired_cache()
    """

    def __init__(self):
        super().__init__("enrichment_results")

    # ========================================================================
    # ENRICHMENT CRUD OPERATIONS
    # ========================================================================

    async def save_quick_enrichment(
        self,
        domain: str,
        data: QuickEnrichmentData,
        ttl_days: int = 30,
    ) -> int:
        """
        Save quick enrichment result with cache TTL

        Args:
            domain: Company domain (cache key)
            data: Quick enrichment data
            ttl_days: Cache time-to-live in days (default: 30)

        Returns:
            Enrichment record ID

        Raises:
            DatabaseError: If save fails
        """
        try:
            cache_key = f"quick:{domain}"
            expires_at = datetime.utcnow() + timedelta(days=ttl_days)

            record_data = {
                "domain": domain,
                "cache_key": cache_key,
                "enrichment_type": "quick",
                "quick_data": json.dumps(data.dict()),
                "source_attribution": data.source_attribution,
                "completeness_score": data.completeness_score,
                "confidence_score": data.confidence_score,
                "data_quality_tier": data.data_quality_tier.value,
                "total_cost_usd": data.total_cost_usd,
                "quick_duration_ms": data.quick_duration_ms,
                "cache_hits": 0,
                "cache_savings_usd": 0.0,
                "expires_at": expires_at.isoformat(),
            }

            result = await self.create(record_data)

            logger.info(
                f"Saved quick enrichment for {domain}",
                extra={
                    "domain": domain,
                    "enrichment_id": result["id"],
                    "completeness": data.completeness_score,
                    "cost": data.total_cost_usd,
                },
            )

            return result["id"]

        except Exception as e:
            logger.error(
                f"Failed to save quick enrichment for {domain}: {str(e)}",
                exc_info=True,
            )
            raise DatabaseError(f"Failed to save quick enrichment: {str(e)}")

    async def save_deep_enrichment(
        self,
        domain: str,
        data: DeepEnrichmentData,
        ttl_days: int = 30,
    ) -> int:
        """
        Save deep enrichment result with cache TTL

        Args:
            domain: Company domain (cache key)
            data: Deep enrichment data
            ttl_days: Cache time-to-live in days (default: 30)

        Returns:
            Enrichment record ID

        Raises:
            DatabaseError: If save fails
        """
        try:
            cache_key = f"deep:{domain}"
            expires_at = datetime.utcnow() + timedelta(days=ttl_days)

            record_data = {
                "domain": domain,
                "cache_key": cache_key,
                "enrichment_type": "deep",
                "deep_data": json.dumps(data.dict()),
                "source_attribution": data.source_attribution,
                "completeness_score": data.completeness_score,
                "confidence_score": data.confidence_score,
                "data_quality_tier": data.data_quality_tier.value,
                "total_cost_usd": data.total_cost_usd,
                "quick_duration_ms": data.quick_duration_ms,
                "deep_duration_ms": data.deep_duration_ms,
                "cache_hits": 0,
                "cache_savings_usd": 0.0,
                "expires_at": expires_at.isoformat(),
            }

            result = await self.create(record_data)

            logger.info(
                f"Saved deep enrichment for {domain}",
                extra={
                    "domain": domain,
                    "enrichment_id": result["id"],
                    "completeness": data.completeness_score,
                    "cost": data.total_cost_usd,
                },
            )

            return result["id"]

        except Exception as e:
            logger.error(
                f"Failed to save deep enrichment for {domain}: {str(e)}",
                exc_info=True,
            )
            raise DatabaseError(f"Failed to save deep enrichment: {str(e)}")

    async def update_enrichment(
        self,
        enrichment_id: int,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Update enrichment record

        Args:
            enrichment_id: Enrichment record ID
            data: Fields to update

        Returns:
            Updated enrichment record

        Raises:
            ResourceNotFound: If enrichment not found
            DatabaseError: If update fails
        """
        try:
            result = await self.update(str(enrichment_id), data)

            logger.debug(
                f"Updated enrichment {enrichment_id}",
                extra={"enrichment_id": enrichment_id},
            )

            return result

        except ResourceNotFound:
            raise
        except Exception as e:
            logger.error(
                f"Failed to update enrichment {enrichment_id}: {str(e)}",
                exc_info=True,
            )
            raise DatabaseError(f"Failed to update enrichment: {str(e)}")

    # ========================================================================
    # CACHE OPERATIONS
    # ========================================================================

    async def get_by_domain(
        self, domain: str, enrichment_type: str = "deep"
    ) -> Optional[Dict[str, Any]]:
        """
        Get enrichment by domain (cache lookup)

        Args:
            domain: Company domain
            enrichment_type: "quick" or "deep"

        Returns:
            Enrichment record if found and not expired, None otherwise

        Raises:
            DatabaseError: If query fails
        """
        try:
            cache_key = f"{enrichment_type}:{domain}"

            # Find by cache_key and check expiration
            records = await self.find({"cache_key": cache_key})

            if not records:
                return None

            record = records[0]

            # Check if expired
            expires_at = datetime.fromisoformat(record["expires_at"])
            if expires_at < datetime.utcnow():
                logger.debug(
                    f"Cache expired for {domain}",
                    extra={"domain": domain, "expires_at": expires_at},
                )
                return None

            # Increment cache hit counter
            await self._increment_cache_hit(record["id"], record["total_cost_usd"])

            logger.debug(
                f"Cache hit for {domain}",
                extra={
                    "domain": domain,
                    "enrichment_id": record["id"],
                    "type": enrichment_type,
                },
            )

            return record

        except Exception as e:
            logger.error(
                f"Failed to get enrichment by domain {domain}: {str(e)}",
                exc_info=True,
            )
            raise DatabaseError(f"Failed to get enrichment by domain: {str(e)}")

    async def get_by_cache_key(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get enrichment by cache key

        Args:
            cache_key: Cache key (e.g., "quick:techstart.com")

        Returns:
            Enrichment record if found and not expired, None otherwise

        Raises:
            DatabaseError: If query fails
        """
        try:
            record = await self.find_one({"cache_key": cache_key})

            if not record:
                return None

            # Check if expired
            expires_at = datetime.fromisoformat(record["expires_at"])
            if expires_at < datetime.utcnow():
                return None

            # Increment cache hit counter
            await self._increment_cache_hit(record["id"], record["total_cost_usd"])

            return record

        except Exception as e:
            logger.error(
                f"Failed to get enrichment by cache key {cache_key}: {str(e)}",
                exc_info=True,
            )
            raise DatabaseError(f"Failed to get enrichment by cache key: {str(e)}")

    async def _increment_cache_hit(
        self, enrichment_id: int, cost_saved: float
    ) -> None:
        """
        Increment cache hit counter and savings

        Args:
            enrichment_id: Enrichment record ID
            cost_saved: Cost saved by cache hit
        """
        try:
            # Use Supabase RPC or raw SQL to increment atomically
            response = (
                self.client.table(self.table_name)
                .update(
                    {
                        "cache_hits": self.client.rpc(
                            "increment", {"table": self.table_name, "id": enrichment_id}
                        ),
                        "cache_savings_usd": cost_saved,  # Will be summed in view
                    }
                )
                .eq("id", enrichment_id)
                .execute()
            )

            logger.debug(
                f"Incremented cache hit for enrichment {enrichment_id}",
                extra={"enrichment_id": enrichment_id, "cost_saved": cost_saved},
            )

        except Exception as e:
            # Log but don't fail - cache hit tracking is non-critical
            logger.warning(
                f"Failed to increment cache hit: {str(e)}",
                extra={"enrichment_id": enrichment_id},
            )

    async def clear_expired_cache(self) -> int:
        """
        Delete expired enrichment cache entries

        Returns:
            Number of records deleted

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            now = datetime.utcnow().isoformat()

            # Delete records where expires_at < now
            response = (
                self.client.table(self.table_name)
                .delete()
                .lt("expires_at", now)
                .execute()
            )

            count = len(response.data) if response.data else 0

            logger.info(
                f"Cleared {count} expired enrichment cache entries",
                extra={"count": count},
            )

            return count

        except Exception as e:
            logger.error(
                f"Failed to clear expired cache: {str(e)}", exc_info=True
            )
            raise DatabaseError(f"Failed to clear expired cache: {str(e)}")

    # ========================================================================
    # STATISTICS & ANALYTICS
    # ========================================================================

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get enrichment statistics for admin dashboard

        Returns:
            Dictionary with comprehensive statistics:
            - total_enrichments: Total enrichment count
            - cache_hit_rate: Percentage of cache hits
            - total_cost: Total API costs spent
            - total_savings: Total cost saved by caching
            - avg_completeness: Average completeness score
            - avg_confidence: Average confidence score
            - by_quality_tier: Count by quality tier
            - by_type: Count by enrichment type

        Raises:
            DatabaseError: If query fails
        """
        try:
            # Get total count
            total = await self.count()

            # Get cache statistics
            all_records = await self.get_all(limit=10000)  # Adjust if needed

            total_hits = sum(r.get("cache_hits", 0) for r in all_records)
            total_calls = total + total_hits
            cache_hit_rate = (total_hits / total_calls * 100) if total_calls > 0 else 0.0

            total_cost = sum(r.get("total_cost_usd", 0.0) for r in all_records)
            total_savings = sum(r.get("cache_savings_usd", 0.0) for r in all_records)

            # Calculate averages
            completeness_scores = [
                r.get("completeness_score", 0.0)
                for r in all_records
                if r.get("completeness_score") is not None
            ]
            avg_completeness = (
                sum(completeness_scores) / len(completeness_scores)
                if completeness_scores
                else 0.0
            )

            confidence_scores = [
                r.get("confidence_score", 0.0)
                for r in all_records
                if r.get("confidence_score") is not None
            ]
            avg_confidence = (
                sum(confidence_scores) / len(confidence_scores)
                if confidence_scores
                else 0.0
            )

            # Count by quality tier
            by_quality_tier = {}
            for tier in DataQualityTier:
                count = await self.count({"data_quality_tier": tier.value})
                by_quality_tier[tier.value] = count

            # Count by type
            quick_count = await self.count({"enrichment_type": "quick"})
            deep_count = await self.count({"enrichment_type": "deep"})

            stats = {
                "total_enrichments": total,
                "cache_hit_rate": round(cache_hit_rate, 2),
                "total_cost_usd": round(total_cost, 2),
                "total_savings_usd": round(total_savings, 2),
                "avg_completeness": round(avg_completeness, 1),
                "avg_confidence": round(avg_confidence, 1),
                "by_quality_tier": by_quality_tier,
                "by_type": {
                    "quick": quick_count,
                    "deep": deep_count,
                },
            }

            logger.debug("Retrieved enrichment statistics", extra=stats)

            return stats

        except Exception as e:
            logger.error(
                f"Failed to get enrichment statistics: {str(e)}", exc_info=True
            )
            raise DatabaseError(f"Failed to get enrichment statistics: {str(e)}")

    async def get_recent_enrichments(
        self, limit: int = 20, enrichment_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent enrichments

        Args:
            limit: Maximum records to return
            enrichment_type: Optional filter by type ("quick" or "deep")

        Returns:
            List of recent enrichment records

        Raises:
            DatabaseError: If query fails
        """
        try:
            if enrichment_type:
                query = (
                    self.client.table(self.table_name)
                    .select("*")
                    .eq("enrichment_type", enrichment_type)
                    .order("created_at", desc=True)
                    .limit(limit)
                )
            else:
                query = (
                    self.client.table(self.table_name)
                    .select("*")
                    .order("created_at", desc=True)
                    .limit(limit)
                )

            response = query.execute()

            return response.data if response.data else []

        except Exception as e:
            logger.error(
                f"Failed to get recent enrichments: {str(e)}", exc_info=True
            )
            raise DatabaseError(f"Failed to get recent enrichments: {str(e)}")

    async def get_cost_by_period(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, float]:
        """
        Get total cost for a date range

        Args:
            start_date: Period start
            end_date: Period end

        Returns:
            Dictionary with cost breakdown:
            - total_cost: Total API costs
            - total_savings: Total saved by caching
            - net_cost: Total cost minus savings

        Raises:
            DatabaseError: If query fails
        """
        try:
            response = (
                self.client.table(self.table_name)
                .select("total_cost_usd, cache_savings_usd")
                .gte("created_at", start_date.isoformat())
                .lte("created_at", end_date.isoformat())
                .execute()
            )

            records = response.data if response.data else []

            total_cost = sum(r.get("total_cost_usd", 0.0) for r in records)
            total_savings = sum(r.get("cache_savings_usd", 0.0) for r in records)

            return {
                "total_cost": round(total_cost, 2),
                "total_savings": round(total_savings, 2),
                "net_cost": round(total_cost - total_savings, 2),
            }

        except Exception as e:
            logger.error(
                f"Failed to get cost by period: {str(e)}", exc_info=True
            )
            raise DatabaseError(f"Failed to get cost by period: {str(e)}")

    # ========================================================================
    # SEARCH & FILTERING
    # ========================================================================

    async def search_by_domain(
        self, query: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search enrichments by domain pattern

        Args:
            query: Search query (will match domain with ILIKE)
            limit: Maximum records to return

        Returns:
            List of matching enrichment records

        Raises:
            DatabaseError: If query fails
        """
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .ilike("domain", f"%{query}%")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            return response.data if response.data else []

        except Exception as e:
            logger.error(
                f"Failed to search enrichments by domain: {str(e)}", exc_info=True
            )
            raise DatabaseError(f"Failed to search enrichments: {str(e)}")


# Singleton instance for dependency injection
enrichment_repository = EnrichmentRepository()


def get_enrichment_repository() -> EnrichmentRepository:
    """
    Get enrichment repository instance

    For use with FastAPI dependency injection:
        @app.get("/enrichments/{domain}")
        async def get_enrichment(
            domain: str,
            repo: EnrichmentRepository = Depends(get_enrichment_repository)
        ):
            return await repo.get_by_domain(domain)
    """
    return enrichment_repository
