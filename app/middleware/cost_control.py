"""
Cost Control Middleware - PREVENT COST EXPLOSIONS

Implements rate limiting and cost tracking to prevent runaway API costs.

Features:
1. Rate limiting per user (prevent abuse)
2. Cost tracking per user/session
3. Daily/monthly cost limits
4. Budget alerts
5. Automatic throttling

Protection Layers:
- Layer 1: Rate limiting (100 enrichments/hour per user)
- Layer 2: Cost limits ($10/day per user)
- Layer 3: Global cost cap ($1000/month total)
- Layer 4: Alert at 80% of limits

Created: 2025-01-11
Version: 1.0.0
"""

import logging
from typing import Optional
from datetime import datetime, timedelta
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
import hashlib

logger = logging.getLogger(__name__)

# In-memory tracking (would use Redis in production)
_rate_limit_tracker = {}
_cost_tracker = {}
_global_costs = {
    "daily": 0.0,
    "monthly": 0.0,
    "last_reset_daily": datetime.now().date(),
    "last_reset_monthly": datetime.now().replace(day=1).date()
}


class CostControlMiddleware:
    """
    Middleware to prevent cost explosions through rate limiting and budget control.

    Configuration:
    - MAX_ENRICHMENTS_PER_HOUR: 100 (default)
    - MAX_COST_PER_DAY: $10 (default)
    - MAX_COST_PER_MONTH: $1000 (global)
    - ALERT_THRESHOLD: 80% of limit

    Usage:
        # In FastAPI app
        from app.middleware.cost_control import CostControlMiddleware

        app.add_middleware(CostControlMiddleware)

        # Or use as dependency
        @app.post("/enrich")
        async def enrich(
            request: Request,
            cost_control: CostControlMiddleware = Depends()
        ):
            # Automatically checked before handler
            ...
    """

    def __init__(
        self,
        max_enrichments_per_hour: int = 100,
        max_cost_per_day: float = 10.0,
        max_cost_per_month: float = 1000.0,
        alert_threshold: float = 0.8
    ):
        """
        Initialize cost control middleware.

        Args:
            max_enrichments_per_hour: Rate limit per user
            max_cost_per_day: Daily cost limit per user ($)
            max_cost_per_month: Global monthly cost limit ($)
            alert_threshold: Alert when reaching X% of limit
        """
        self.max_enrichments_per_hour = max_enrichments_per_hour
        self.max_cost_per_day = max_cost_per_day
        self.max_cost_per_month = max_cost_per_month
        self.alert_threshold = alert_threshold

        logger.info(
            f"[CostControl] Initialized: "
            f"{max_enrichments_per_hour}/hour, "
            f"${max_cost_per_day}/day, "
            f"${max_cost_per_month}/month"
        )

    async def __call__(self, request: Request, call_next):
        """FastAPI middleware handler"""
        # Only check enrichment endpoints
        if "/enrich" in request.url.path:
            try:
                await self.check_limits(request)
            except HTTPException as e:
                return JSONResponse(
                    status_code=e.status_code,
                    content={"detail": e.detail}
                )

        response = await call_next(request)
        return response

    async def check_limits(self, request: Request):
        """
        Check all cost control limits before allowing enrichment.

        Raises:
            HTTPException: If any limit exceeded
        """
        user_id = self._get_user_id(request)

        # Check 1: Rate limiting (enrichments per hour)
        await self._check_rate_limit(user_id)

        # Check 2: Daily cost limit per user
        await self._check_daily_cost_limit(user_id)

        # Check 3: Global monthly cost limit
        await self._check_global_cost_limit()

    async def _check_rate_limit(self, user_id: str):
        """Check hourly rate limit"""
        now = datetime.now()
        hour_key = now.strftime("%Y-%m-%d-%H")
        key = f"rate:{user_id}:{hour_key}"

        # Get current count
        count = _rate_limit_tracker.get(key, 0)

        if count >= self.max_enrichments_per_hour:
            logger.warning(
                f"[CostControl] Rate limit exceeded: {user_id} "
                f"({count}/{self.max_enrichments_per_hour})"
            )
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Maximum {self.max_enrichments_per_hour} "
                       f"enrichments per hour. Try again in "
                       f"{60 - now.minute} minutes."
            )

        # Increment counter
        _rate_limit_tracker[key] = count + 1

        # Alert at 80% threshold
        if count >= self.max_enrichments_per_hour * self.alert_threshold:
            logger.warning(
                f"[CostControl] Rate limit warning: {user_id} "
                f"at {count}/{self.max_enrichments_per_hour} "
                f"({count/self.max_enrichments_per_hour*100:.1f}%)"
            )

    async def _check_daily_cost_limit(self, user_id: str):
        """Check daily cost limit per user"""
        today = datetime.now().date()
        key = f"cost:{user_id}:{today}"

        # Get current cost
        cost = _cost_tracker.get(key, 0.0)

        if cost >= self.max_cost_per_day:
            logger.warning(
                f"[CostControl] Daily cost limit exceeded: {user_id} "
                f"(${cost:.2f}/${self.max_cost_per_day})"
            )
            raise HTTPException(
                status_code=402,
                detail=f"Daily cost limit reached (${self.max_cost_per_day}). "
                       f"Current: ${cost:.2f}. Resets tomorrow."
            )

        # Alert at 80% threshold
        if cost >= self.max_cost_per_day * self.alert_threshold:
            logger.warning(
                f"[CostControl] Daily cost warning: {user_id} "
                f"at ${cost:.2f}/${self.max_cost_per_day} "
                f"({cost/self.max_cost_per_day*100:.1f}%)"
            )

    async def _check_global_cost_limit(self):
        """Check global monthly cost limit"""
        self._reset_global_costs_if_needed()

        monthly_cost = _global_costs["monthly"]

        if monthly_cost >= self.max_cost_per_month:
            logger.error(
                f"[CostControl] GLOBAL monthly cost limit exceeded: "
                f"${monthly_cost:.2f}/${self.max_cost_per_month}"
            )
            raise HTTPException(
                status_code=503,
                detail="Service temporarily unavailable due to budget limits. "
                       "Please contact support."
            )

        # Alert at 80% threshold
        if monthly_cost >= self.max_cost_per_month * self.alert_threshold:
            logger.error(
                f"[CostControl] CRITICAL: Global monthly cost at "
                f"${monthly_cost:.2f}/${self.max_cost_per_month} "
                f"({monthly_cost/self.max_cost_per_month*100:.1f}%)"
            )

    async def track_enrichment_cost(
        self,
        user_id: str,
        cost: float,
        enrichment_type: str = "progressive"
    ):
        """
        Track enrichment cost for user and globally.

        Call this AFTER enrichment completes.

        Args:
            user_id: User identifier
            cost: Cost in USD
            enrichment_type: Type of enrichment
        """
        today = datetime.now().date()

        # Track user daily cost
        user_key = f"cost:{user_id}:{today}"
        _cost_tracker[user_key] = _cost_tracker.get(user_key, 0.0) + cost

        # Track global costs
        self._reset_global_costs_if_needed()
        _global_costs["daily"] += cost
        _global_costs["monthly"] += cost

        logger.info(
            f"[CostControl] Tracked cost: {user_id} "
            f"+${cost:.4f} ({enrichment_type}) "
            f"[daily: ${_cost_tracker[user_key]:.4f}, "
            f"global_monthly: ${_global_costs['monthly']:.2f}]"
        )

    def _reset_global_costs_if_needed(self):
        """Reset daily/monthly costs if period changed"""
        now = datetime.now()
        today = now.date()

        # Reset daily
        if _global_costs["last_reset_daily"] != today:
            logger.info(
                f"[CostControl] Resetting daily costs "
                f"(previous: ${_global_costs['daily']:.2f})"
            )
            _global_costs["daily"] = 0.0
            _global_costs["last_reset_daily"] = today

        # Reset monthly
        first_of_month = today.replace(day=1)
        if _global_costs["last_reset_monthly"] != first_of_month:
            logger.info(
                f"[CostControl] Resetting monthly costs "
                f"(previous: ${_global_costs['monthly']:.2f})"
            )
            _global_costs["monthly"] = 0.0
            _global_costs["last_reset_monthly"] = first_of_month

    def _get_user_id(self, request: Request) -> str:
        """
        Extract user ID from request.

        Uses (in order):
        1. Authenticated user ID
        2. API key
        3. IP address (fallback)
        """
        # Try to get authenticated user
        if hasattr(request.state, "user"):
            return str(request.state.user.id)

        # Try to get API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return hashlib.md5(api_key.encode()).hexdigest()[:12]

        # Fallback to IP address
        client_ip = request.client.host if request.client else "unknown"
        return hashlib.md5(client_ip.encode()).hexdigest()[:12]

    def get_user_stats(self, user_id: str) -> dict:
        """
        Get current cost stats for user.

        Returns:
            Dict with rate limit and cost usage
        """
        now = datetime.now()
        today = now.date()
        hour_key = now.strftime("%Y-%m-%d-%H")

        rate_key = f"rate:{user_id}:{hour_key}"
        cost_key = f"cost:{user_id}:{today}"

        enrichments_this_hour = _rate_limit_tracker.get(rate_key, 0)
        cost_today = _cost_tracker.get(cost_key, 0.0)

        return {
            "user_id": user_id,
            "enrichments_this_hour": enrichments_this_hour,
            "enrichments_remaining_this_hour": max(
                0,
                self.max_enrichments_per_hour - enrichments_this_hour
            ),
            "cost_today": cost_today,
            "cost_remaining_today": max(
                0.0,
                self.max_cost_per_day - cost_today
            ),
            "rate_limit_percent": (
                enrichments_this_hour / self.max_enrichments_per_hour * 100
            ),
            "cost_limit_percent": (cost_today / self.max_cost_per_day * 100),
            "limits": {
                "max_enrichments_per_hour": self.max_enrichments_per_hour,
                "max_cost_per_day": self.max_cost_per_day
            }
        }

    def get_global_stats(self) -> dict:
        """Get global cost statistics"""
        self._reset_global_costs_if_needed()

        return {
            "daily_cost": _global_costs["daily"],
            "monthly_cost": _global_costs["monthly"],
            "daily_limit": self.max_cost_per_day * 100,  # Assume 100 users
            "monthly_limit": self.max_cost_per_month,
            "monthly_percent": (
                _global_costs["monthly"] / self.max_cost_per_month * 100
            ),
            "last_reset_daily": _global_costs["last_reset_daily"].isoformat(),
            "last_reset_monthly": _global_costs["last_reset_monthly"].isoformat()
        }
