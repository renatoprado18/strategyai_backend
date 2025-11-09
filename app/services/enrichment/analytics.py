"""
Analytics and Cost Tracking for IMENSIAH Enrichment System

Provides comprehensive metrics for the admin dashboard:
- Total enrichments processed
- Cache hit rates and savings
- Cost per source and total spend
- Performance metrics (duration, success rates)
- Source health monitoring

Created: 2025-01-09
Version: 1.0.0
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import logging
from pydantic import BaseModel, Field
from app.core.supabase import supabase_service

logger = logging.getLogger(__name__)


class OverviewStats(BaseModel):
    """Overview statistics for admin dashboard"""

    total_count: int = Field(..., description="Total enrichments processed")
    quick_completed: int = Field(
        ..., description="Enrichments with quick data"
    )
    deep_completed: int = Field(..., description="Enrichments with deep data")
    cache_hit_rate: float = Field(
        ..., description="Cache hit rate percentage", ge=0, le=100
    )
    avg_completeness: float = Field(
        ..., description="Average completeness score", ge=0, le=100
    )
    avg_confidence: float = Field(
        ..., description="Average confidence score", ge=0, le=100
    )
    total_cost_saved: float = Field(
        ..., description="Total cost saved by caching", ge=0
    )
    avg_quick_duration: Optional[float] = Field(
        None, description="Average quick enrichment duration (ms)"
    )
    avg_deep_duration: Optional[float] = Field(
        None, description="Average deep enrichment duration (ms)"
    )
    active_cache_entries: int = Field(
        ..., description="Non-expired cache entries"
    )


class SourceStats(BaseModel):
    """Statistics for a single data source"""

    name: str = Field(..., description="Source name")
    total_calls: int = Field(..., description="Total API calls", ge=0)
    successful_calls: int = Field(..., description="Successful calls", ge=0)
    failed_calls: int = Field(..., description="Failed calls", ge=0)
    success_rate: float = Field(
        ..., description="Success rate percentage", ge=0, le=100
    )
    avg_duration: Optional[float] = Field(
        None, description="Average duration (ms)"
    )
    total_cost: float = Field(..., description="Total cost in USD", ge=0)
    last_called_at: Optional[datetime] = Field(
        None, description="Last API call timestamp"
    )
    current_circuit_state: Optional[str] = Field(
        None, description="Current circuit breaker state"
    )


class EnrichmentAnalytics:
    """
    Analytics and metrics tracking for enrichment system.

    Provides real-time statistics for the admin dashboard,
    enabling transparency and cost optimization.

    Usage:
        analytics = EnrichmentAnalytics()

        # Get overview stats
        stats = await analytics.get_overview_stats()
        print(f"Total enrichments: {stats.total_count}")
        print(f"Cache hit rate: {stats.cache_hit_rate}%")
        print(f"Cost saved: ${stats.total_cost_saved}")

        # Get per-source stats
        source_stats = await analytics.get_all_source_stats()
        for stat in source_stats:
            print(f"{stat.name}: {stat.success_rate}% success")
    """

    async def get_overview_stats(
        self, days: Optional[int] = None
    ) -> OverviewStats:
        """
        Get overview statistics from the enrichment_statistics view.

        Args:
            days: Filter to last N days (None = all time)

        Returns:
            OverviewStats with aggregated metrics
        """
        try:
            # Query the materialized view (or re-compute if needed)
            result = (
                await supabase_service.table("enrichment_results")
                .select("*")
                .execute()
            )

            if not result.data:
                # No data yet, return zeros
                return OverviewStats(
                    total_count=0,
                    quick_completed=0,
                    deep_completed=0,
                    cache_hit_rate=0.0,
                    avg_completeness=0.0,
                    avg_confidence=0.0,
                    total_cost_saved=0.0,
                    avg_quick_duration=None,
                    avg_deep_duration=None,
                    active_cache_entries=0,
                )

            # Calculate statistics
            total_count = len(result.data)
            quick_completed = sum(
                1 for r in result.data if r.get("quick_data")
            )
            deep_completed = sum(1 for r in result.data if r.get("deep_data"))

            # Cache hit rate
            total_hits = sum(r.get("cache_hits", 0) for r in result.data)
            cache_hit_rate = (
                (total_hits / total_count * 100) if total_count > 0 else 0.0
            )

            # Average scores
            completeness_scores = [
                r.get("completeness_score")
                for r in result.data
                if r.get("completeness_score") is not None
            ]
            avg_completeness = (
                sum(completeness_scores) / len(completeness_scores)
                if completeness_scores
                else 0.0
            )

            confidence_scores = [
                r.get("confidence_score")
                for r in result.data
                if r.get("confidence_score") is not None
            ]
            avg_confidence = (
                sum(confidence_scores) / len(confidence_scores)
                if confidence_scores
                else 0.0
            )

            # Cost saved
            total_cost_saved = sum(
                r.get("cache_savings_usd", 0.0) for r in result.data
            )

            # Duration averages
            quick_durations = [
                r.get("quick_duration_ms")
                for r in result.data
                if r.get("quick_duration_ms") is not None
            ]
            avg_quick_duration = (
                sum(quick_durations) / len(quick_durations)
                if quick_durations
                else None
            )

            deep_durations = [
                r.get("deep_duration_ms")
                for r in result.data
                if r.get("deep_duration_ms") is not None
            ]
            avg_deep_duration = (
                sum(deep_durations) / len(deep_durations)
                if deep_durations
                else None
            )

            # Active cache entries
            now = datetime.now()
            active_cache_entries = sum(
                1
                for r in result.data
                if r.get("expires_at")
                and datetime.fromisoformat(r["expires_at"]) > now
            )

            return OverviewStats(
                total_count=total_count,
                quick_completed=quick_completed,
                deep_completed=deep_completed,
                cache_hit_rate=round(cache_hit_rate, 2),
                avg_completeness=round(avg_completeness, 2),
                avg_confidence=round(avg_confidence, 2),
                total_cost_saved=round(total_cost_saved, 4),
                avg_quick_duration=round(avg_quick_duration, 2)
                if avg_quick_duration
                else None,
                avg_deep_duration=round(avg_deep_duration, 2)
                if avg_deep_duration
                else None,
                active_cache_entries=active_cache_entries,
            )

        except Exception as e:
            logger.error(f"Error getting overview stats: {e}", exc_info=True)
            # Return zeros on error
            return OverviewStats(
                total_count=0,
                quick_completed=0,
                deep_completed=0,
                cache_hit_rate=0.0,
                avg_completeness=0.0,
                avg_confidence=0.0,
                total_cost_saved=0.0,
                avg_quick_duration=None,
                avg_deep_duration=None,
                active_cache_entries=0,
            )

    async def get_source_stats(self, source_name: str) -> Optional[SourceStats]:
        """
        Get statistics for a specific data source.

        Args:
            source_name: Name of the source (e.g., "clearbit")

        Returns:
            SourceStats for the source, or None if not found
        """
        try:
            # Query audit log for this source
            result = (
                await supabase_service.table("enrichment_audit_log")
                .select("*")
                .eq("source_name", source_name)
                .execute()
            )

            if not result.data:
                return None

            # Calculate statistics
            total_calls = len(result.data)
            successful_calls = sum(1 for r in result.data if r.get("success"))
            failed_calls = total_calls - successful_calls
            success_rate = (
                (successful_calls / total_calls * 100)
                if total_calls > 0
                else 0.0
            )

            # Average duration (only successful calls)
            durations = [
                r.get("duration_ms")
                for r in result.data
                if r.get("success") and r.get("duration_ms") is not None
            ]
            avg_duration = (
                sum(durations) / len(durations) if durations else None
            )

            # Total cost
            total_cost = sum(r.get("cost_usd", 0.0) for r in result.data)

            # Last called
            sorted_calls = sorted(
                result.data,
                key=lambda x: x.get("called_at", ""),
                reverse=True,
            )
            last_called_at = (
                datetime.fromisoformat(sorted_calls[0]["called_at"])
                if sorted_calls
                else None
            )

            # Current circuit state (most recent)
            current_circuit_state = sorted_calls[0].get(
                "circuit_breaker_state"
            )

            return SourceStats(
                name=source_name,
                total_calls=total_calls,
                successful_calls=successful_calls,
                failed_calls=failed_calls,
                success_rate=round(success_rate, 2),
                avg_duration=round(avg_duration, 2) if avg_duration else None,
                total_cost=round(total_cost, 4),
                last_called_at=last_called_at,
                current_circuit_state=current_circuit_state,
            )

        except Exception as e:
            logger.error(
                f"Error getting stats for source '{source_name}': {e}",
                exc_info=True,
            )
            return None

    async def get_all_source_stats(self) -> List[SourceStats]:
        """
        Get statistics for all data sources.

        Returns:
            List of SourceStats, ordered by total calls descending
        """
        try:
            # Get unique source names from audit log
            result = (
                await supabase_service.table("enrichment_audit_log")
                .select("source_name")
                .execute()
            )

            if not result.data:
                return []

            # Get unique source names
            source_names = list(
                set(r["source_name"] for r in result.data if r.get("source_name"))
            )

            # Get stats for each source
            all_stats = []
            for source_name in source_names:
                stats = await self.get_source_stats(source_name)
                if stats:
                    all_stats.append(stats)

            # Sort by total calls (descending)
            all_stats.sort(key=lambda x: x.total_calls, reverse=True)

            return all_stats

        except Exception as e:
            logger.error(f"Error getting all source stats: {e}", exc_info=True)
            return []

    async def record_cache_hit(
        self, enrichment_type: str, cost_saved: float
    ) -> None:
        """
        Record a cache hit for analytics.

        Args:
            enrichment_type: "quick" or "deep"
            cost_saved: Amount saved by cache hit
        """
        logger.info(
            f"Cache hit recorded: {enrichment_type} (saved ${cost_saved:.4f})",
            extra={
                "enrichment_type": enrichment_type,
                "cost_saved": cost_saved,
            },
        )

    async def get_monthly_cost(self, year: int, month: int) -> float:
        """
        Get total cost for a specific month.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Total cost in USD
        """
        try:
            # Calculate date range
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)

            # Query audit log
            result = (
                await supabase_service.table("enrichment_audit_log")
                .select("cost_usd")
                .gte("called_at", start_date.isoformat())
                .lt("called_at", end_date.isoformat())
                .execute()
            )

            if not result.data:
                return 0.0

            total_cost = sum(r.get("cost_usd", 0.0) for r in result.data)

            return round(total_cost, 4)

        except Exception as e:
            logger.error(
                f"Error getting monthly cost for {year}-{month:02d}: {e}",
                exc_info=True,
            )
            return 0.0

    async def get_cost_by_source(
        self, year: int, month: int
    ) -> Dict[str, float]:
        """
        Get cost breakdown by source for a specific month.

        Args:
            year: Year (e.g., 2025)
            month: Month (1-12)

        Returns:
            Dict mapping source name to cost in USD
        """
        try:
            # Calculate date range
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)

            # Query audit log
            result = (
                await supabase_service.table("enrichment_audit_log")
                .select("source_name, cost_usd")
                .gte("called_at", start_date.isoformat())
                .lt("called_at", end_date.isoformat())
                .execute()
            )

            if not result.data:
                return {}

            # Aggregate by source
            cost_by_source: Dict[str, float] = {}
            for record in result.data:
                source = record.get("source_name", "unknown")
                cost = record.get("cost_usd", 0.0)
                cost_by_source[source] = cost_by_source.get(source, 0.0) + cost

            # Round values
            return {
                k: round(v, 4) for k, v in sorted(
                    cost_by_source.items(),
                    key=lambda x: x[1],
                    reverse=True
                )
            }

        except Exception as e:
            logger.error(
                f"Error getting cost by source for {year}-{month:02d}: {e}",
                exc_info=True,
            )
            return {}
