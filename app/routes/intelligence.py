"""
Intelligence Routes for Dashboard AI Intelligence

Provides AI-powered dashboard insights and analytics for admin users.
"""

from fastapi import APIRouter, Depends
from datetime import datetime, timedelta, timezone
import json
from typing import Dict, Any

from app.models.schemas import (
    # Add any specific schemas needed for intelligence responses
)
from app.core.database import (
    get_all_submissions,
)
from app.services.intelligence.dashboard import generate_dashboard_intelligence
from app.routes.auth import RequireAuth
from app.core.cache import (
    get_cached_dashboard_stats,
    cache_dashboard_stats,
)

# Initialize router with prefix
router = APIRouter(prefix="/api/admin")


@router.get("/dashboard/intelligence")
async def get_dashboard_intelligence(
    days: int = 7,
    current_user: dict = RequireAuth,
):
    """
    Get FREE AI-powered dashboard intelligence (Protected Admin endpoint)

    DISABLED: All free models hitting 429 rate limits
    Returns empty response immediately to avoid blocking dashboard
    """
    print(f"[DASHBOARD AI] DISABLED - Returning empty intelligence to avoid 429 rate limits")

    # Return empty intelligence structure immediately
    return {
        "executive_summary": "Dashboard Intelligence temporariamente desabilitado devido a limites de taxa dos modelos gratuitos.",
        "quality_trends": None,
        "common_challenges": [],
        "high_risk_submissions": [],
        "system_recommendations": [],
        "metadata": {
            "days_analyzed": days,
            "cost": 0.0,
            "disabled": True
        }
    }

    # OLD CODE (DISABLED):
    """
    try:
        print(f"[DASHBOARD AI] User {current_user['email']} requesting intelligence (last {days} days)")

        # Get all submissions
        all_submissions = await get_all_submissions()

        # Filter by date range (timezone-aware)
        current_cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        previous_cutoff = datetime.now(timezone.utc) - timedelta(days=days * 2)

        current_submissions = [
            s for s in all_submissions
            if s.get("created_at") and datetime.fromisoformat(s["created_at"].replace("Z", "+00:00")) >= current_cutoff
        ]

        previous_submissions = [
            s for s in all_submissions
            if s.get("created_at") and previous_cutoff <= datetime.fromisoformat(s["created_at"].replace("Z", "+00:00")) < current_cutoff
        ]

        print(f"[DASHBOARD AI] Analyzing {len(current_submissions)} current + {len(previous_submissions)} previous submissions")

        # Generate FREE AI intelligence
        intelligence = await generate_dashboard_intelligence(
            current_submissions=current_submissions,
            previous_submissions=previous_submissions if len(previous_submissions) > 0 else None
        )

        print(f"[DASHBOARD AI] ✅ Intelligence generated (cost: $0.00)")

        return {
            "success": True,
            "data": intelligence
        }

    except Exception as e:
        print(f"[ERROR] Dashboard intelligence error: {e}")
        return {
            "success": False,
            "error": str(e)
        }
    """
