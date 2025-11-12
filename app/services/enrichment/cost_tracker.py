"""
Cost Tracker Service - MONITOR AND OPTIMIZE API COSTS

Tracks all enrichment costs in real-time with detailed breakdowns:
- Cost per source (Clearbit, Google Places, etc.)
- Cost per user/session
- Cost trends over time
- Savings from caching
- Cost optimization recommendations

Features:
1. Real-time cost tracking
2. Per-source cost breakdown
3. Cache savings calculation
4. Cost trend analysis
5. Budget forecasting
6. Optimization alerts

Created: 2025-01-11
Version: 1.0.0
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class CostRecord(BaseModel):
    """Single cost tracking record"""
    timestamp: datetime
    user_id: str
    session_id: str
    source_name: str
    cost_usd: float
    duration_ms: int
    cache_hit: bool
    fields_returned: int


class CostTracker:
    """
    Track and analyze enrichment costs in real-time.

    Usage:
        tracker = CostTracker()

        # Track enrichment cost
        await tracker.track(
            user_id="user123",
            session_id="session456",
            source_name="clearbit",
            cost=0.10,
            duration_ms=1500,
            cache_hit=False,
            fields_returned=12
        )

        # Get cost summary
        summary = tracker.get_summary(days=7)
        print(f"Total cost last 7 days: ${summary['total_cost']}")
        print(f"Cache saved: ${summary['cache_savings']}")
    """

    def __init__(self):
        """Initialize cost tracker"""
        self.records: List[CostRecord] = []
        self.source_costs = {
            "clearbit": 0.10,
            "google_places": 0.02,
            "proxycurl": 0.01,
            "openai_gpt": 0.01,
            "free_company_data": 0.0,
            "free_geocoding": 0.0,
            "groq_ai": 0.0,
            "metadata": 0.0,
            "ip_api": 0.0,
            "receita_ws": 0.0
        }

    async def track(
        self,
        user_id: str,
        session_id: str,
        source_name: str,
        cost: float,
        duration_ms: int,
        cache_hit: bool = False,
        fields_returned: int = 0
    ):
        """
        Track a single enrichment cost event.

        Args:
            user_id: User identifier
            session_id: Enrichment session ID
            source_name: Data source name
            cost: Cost in USD
            duration_ms: Duration in milliseconds
            cache_hit: Whether this was a cache hit
            fields_returned: Number of fields returned
        """
        record = CostRecord(
            timestamp=datetime.now(),
            user_id=user_id,
            session_id=session_id,
            source_name=source_name,
            cost_usd=cost if not cache_hit else 0.0,
            duration_ms=duration_ms,
            cache_hit=cache_hit,
            fields_returned=fields_returned
        )

        self.records.append(record)

        # Log if significant cost
        if cost > 0.01 and not cache_hit:
            logger.info(
                f"[CostTracker] {source_name}: ${cost:.4f} "
                f"({fields_returned} fields, {duration_ms}ms)"
            )

    def get_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get cost summary for last N days.

        Returns:
            Dict with comprehensive cost breakdown
        """
        cutoff = datetime.now() - timedelta(days=days)
        recent_records = [r for r in self.records if r.timestamp >= cutoff]

        if not recent_records:
            return {
                "total_cost": 0.0,
                "cache_savings": 0.0,
                "total_requests": 0,
                "cache_hit_rate": 0.0
            }

        # Calculate totals
        total_cost = sum(r.cost_usd for r in recent_records if not r.cache_hit)
        cache_hits = sum(1 for r in recent_records if r.cache_hit)
        total_requests = len(recent_records)

        # Calculate cache savings (what we WOULD have paid)
        cache_savings = sum(
            self.source_costs.get(r.source_name, 0.05)
            for r in recent_records if r.cache_hit
        )

        # Cost per source
        cost_by_source = {}
        for record in recent_records:
            if not record.cache_hit:
                cost_by_source[record.source_name] = (
                    cost_by_source.get(record.source_name, 0.0) + record.cost_usd
                )

        # Most expensive sources
        top_sources = sorted(
            cost_by_source.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "period_days": days,
            "total_cost": round(total_cost, 4),
            "cache_savings": round(cache_savings, 4),
            "cost_without_cache": round(total_cost + cache_savings, 4),
            "total_requests": total_requests,
            "cache_hits": cache_hits,
            "cache_misses": total_requests - cache_hits,
            "cache_hit_rate": round(cache_hits / total_requests * 100, 2) if total_requests > 0 else 0,
            "cost_by_source": cost_by_source,
            "top_expensive_sources": [
                {"source": s, "cost": round(c, 4)}
                for s, c in top_sources
            ],
            "avg_cost_per_request": round(
                total_cost / total_requests, 4
            ) if total_requests > 0 else 0,
            "avg_fields_per_request": round(
                sum(r.fields_returned for r in recent_records) / total_requests, 1
            ) if total_requests > 0 else 0
        }

    def get_optimization_recommendations(self) -> List[Dict[str, str]]:
        """
        Generate cost optimization recommendations based on usage patterns.

        Returns:
            List of actionable recommendations
        """
        summary = self.get_summary(days=30)
        recommendations = []

        # Recommendation 1: Cache hit rate
        if summary["cache_hit_rate"] < 50:
            recommendations.append({
                "priority": "high",
                "type": "caching",
                "message": f"Low cache hit rate ({summary['cache_hit_rate']:.1f}%). "
                          f"Enable aggressive caching to reduce costs by up to 50%.",
                "potential_savings": f"${summary['cost_without_cache'] * 0.5:.2f}/month"
            })

        # Recommendation 2: Expensive sources
        expensive_sources = [
            s for s in summary["top_expensive_sources"]
            if s["cost"] > 5.0  # $5+ spent
        ]
        if expensive_sources:
            for source in expensive_sources[:3]:
                if source["source"] in ["clearbit", "google_places", "proxycurl"]:
                    free_alternative = {
                        "clearbit": "free_company_data",
                        "google_places": "free_geocoding",
                        "proxycurl": "groq_ai + linkedin scraping"
                    }.get(source["source"])

                    recommendations.append({
                        "priority": "high",
                        "type": "source_replacement",
                        "message": f"Replace {source['source']} (${source['cost']:.2f} spent) "
                                  f"with {free_alternative} (free).",
                        "potential_savings": f"${source['cost']:.2f}/month"
                    })

        # Recommendation 3: High request volume
        if summary["total_requests"] > 1000:
            recommendations.append({
                "priority": "medium",
                "type": "rate_limiting",
                "message": f"High request volume ({summary['total_requests']} requests). "
                          f"Consider implementing rate limiting to prevent abuse.",
                "potential_savings": "Prevent cost explosions"
            })

        # Recommendation 4: Poor field efficiency
        if summary["avg_fields_per_request"] < 5:
            recommendations.append({
                "priority": "medium",
                "type": "source_optimization",
                "message": f"Low field return rate ({summary['avg_fields_per_request']:.1f} fields/request). "
                          f"Optimize source selection to get more data per API call.",
                "potential_savings": f"${summary['total_cost'] * 0.3:.2f}/month"
            })

        return recommendations

    def get_daily_trends(self, days: int = 30) -> Dict[str, List[Any]]:
        """
        Get daily cost trends for visualization.

        Returns:
            Dict with daily breakdowns
        """
        cutoff = datetime.now() - timedelta(days=days)
        recent_records = [r for r in self.records if r.timestamp >= cutoff]

        # Group by day
        daily_costs = {}
        for record in recent_records:
            day = record.timestamp.date().isoformat()
            if day not in daily_costs:
                daily_costs[day] = {
                    "cost": 0.0,
                    "requests": 0,
                    "cache_hits": 0
                }

            daily_costs[day]["requests"] += 1
            if record.cache_hit:
                daily_costs[day]["cache_hits"] += 1
            else:
                daily_costs[day]["cost"] += record.cost_usd

        # Format for charts
        dates = sorted(daily_costs.keys())
        return {
            "dates": dates,
            "costs": [daily_costs[d]["cost"] for d in dates],
            "requests": [daily_costs[d]["requests"] for d in dates],
            "cache_hit_rates": [
                (daily_costs[d]["cache_hits"] / daily_costs[d]["requests"] * 100)
                if daily_costs[d]["requests"] > 0 else 0
                for d in dates
            ]
        }

    def forecast_monthly_cost(self) -> Dict[str, Any]:
        """
        Forecast monthly cost based on recent trends.

        Returns:
            Dict with forecast and confidence
        """
        # Use last 7 days to forecast
        summary_7d = self.get_summary(days=7)

        if summary_7d["total_requests"] == 0:
            return {
                "forecast_monthly_cost": 0.0,
                "confidence": "low",
                "message": "Insufficient data for forecast"
            }

        # Calculate average daily cost
        avg_daily_cost = summary_7d["total_cost"] / 7

        # Forecast for 30 days
        forecast = avg_daily_cost * 30

        # Confidence based on data variance
        confidence = "high" if summary_7d["total_requests"] > 100 else "medium"

        return {
            "forecast_monthly_cost": round(forecast, 2),
            "avg_daily_cost": round(avg_daily_cost, 4),
            "confidence": confidence,
            "based_on_days": 7,
            "with_cache_savings": round(
                forecast - (summary_7d["cache_savings"] / 7 * 30), 2
            ),
            "potential_savings": round(summary_7d["cache_savings"] / 7 * 30, 2)
        }
