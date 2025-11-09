"""
Progressive Enrichment Repository - Database queries for 3-layer enrichment system

This module provides database access layer for:
- Progressive enrichment sessions (3-layer tracking)
- Auto-fill suggestions tracking
- Field validation history
- Source performance metrics
- Analytics queries for admin dashboard

Created: 2025-01-09
Version: 1.0.0
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from uuid import UUID

from app.core.supabase import supabase_service

logger = logging.getLogger(__name__)


# ============================================================================
# SESSION QUERIES
# ============================================================================

async def get_session_by_id(session_id: str) -> Optional[Dict[str, Any]]:
    """Get enrichment session by session_id"""
    try:
        response = supabase_service.table("progressive_enrichment_sessions") \
            .select("*") \
            .eq("session_id", session_id) \
            .single() \
            .execute()

        return response.data if response.data else None
    except Exception as e:
        logger.error(f"Failed to get session {session_id}: {str(e)}", exc_info=True)
        return None


async def get_all_sessions(
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get all enrichment sessions with pagination"""
    try:
        query = supabase_service.table("progressive_enrichment_sessions") \
            .select("*") \
            .order("created_at", desc=True) \
            .limit(limit) \
            .offset(offset)

        if status:
            query = query.eq("status", status)

        response = query.execute()
        return response.data if response.data else []
    except Exception as e:
        logger.error(f"Failed to get all sessions: {str(e)}", exc_info=True)
        return []


async def count_sessions(status: Optional[str] = None) -> int:
    """Count total sessions, optionally filtered by status"""
    try:
        query = supabase_service.table("progressive_enrichment_sessions") \
            .select("id", count="exact")

        if status:
            query = query.eq("status", status)

        response = query.execute()
        return response.count if hasattr(response, 'count') else 0
    except Exception as e:
        logger.error(f"Failed to count sessions: {str(e)}", exc_info=True)
        return 0


async def get_session_attribution(session_id: str) -> Dict[str, Any]:
    """Get field-by-field source attribution for a session"""
    try:
        # Get session data
        session = await get_session_by_id(session_id)
        if not session:
            return {"error": "Session not found"}

        # Get auto-fill suggestions to see which source provided each field
        response = supabase_service.table("auto_fill_suggestions") \
            .select("*") \
            .eq("session_id", session_id) \
            .execute()

        suggestions = response.data if response.data else []

        # Build attribution map
        attribution = {}
        for suggestion in suggestions:
            field_name = suggestion.get("field_name")
            source = suggestion.get("source")
            layer = suggestion.get("layer_number")
            confidence = suggestion.get("confidence")

            attribution[field_name] = {
                "source": source,
                "layer": layer,
                "confidence": confidence,
                "was_accepted": suggestion.get("was_accepted"),
                "was_edited": suggestion.get("was_edited")
            }

        return {
            "session_id": session_id,
            "attribution": attribution,
            "total_fields": len(attribution)
        }
    except Exception as e:
        logger.error(f"Failed to get session attribution: {str(e)}", exc_info=True)
        return {"error": str(e)}


# ============================================================================
# ANALYTICS QUERIES
# ============================================================================

async def get_overview_analytics(days: int = 30) -> Dict[str, Any]:
    """Get dashboard overview analytics for last N days"""
    try:
        start_date = datetime.now() - timedelta(days=days)

        # Get session count
        session_count_response = supabase_service.table("progressive_enrichment_sessions") \
            .select("id", count="exact") \
            .gte("created_at", start_date.isoformat()) \
            .execute()

        total_sessions = session_count_response.count if hasattr(session_count_response, 'count') else 0

        # Get sessions with full data for metrics
        sessions_response = supabase_service.table("progressive_enrichment_sessions") \
            .select("*") \
            .gte("created_at", start_date.isoformat()) \
            .execute()

        sessions = sessions_response.data if sessions_response.data else []

        # Calculate metrics
        total_cost = sum(float(s.get("total_cost_usd", 0)) for s in sessions)
        avg_duration = sum(s.get("total_duration_ms", 0) for s in sessions) / len(sessions) if sessions else 0

        # Count by status
        status_counts = {}
        for session in sessions:
            status = session.get("status", "unknown")
            status_counts[status] = status_counts.get(status, 0) + 1

        # Layer completion rates
        layer1_complete = sum(1 for s in sessions if s.get("layer1_completed_at"))
        layer2_complete = sum(1 for s in sessions if s.get("layer2_completed_at"))
        layer3_complete = sum(1 for s in sessions if s.get("layer3_completed_at"))

        return {
            "period_days": days,
            "total_sessions": total_sessions,
            "total_cost_usd": round(total_cost, 2),
            "avg_duration_ms": round(avg_duration, 0),
            "status_distribution": status_counts,
            "layer_completion": {
                "layer1": layer1_complete,
                "layer2": layer2_complete,
                "layer3": layer3_complete
            },
            "completion_rates": {
                "layer1_pct": round(100 * layer1_complete / total_sessions, 1) if total_sessions > 0 else 0,
                "layer2_pct": round(100 * layer2_complete / total_sessions, 1) if total_sessions > 0 else 0,
                "layer3_pct": round(100 * layer3_complete / total_sessions, 1) if total_sessions > 0 else 0
            }
        }
    except Exception as e:
        logger.error(f"Failed to get overview analytics: {str(e)}", exc_info=True)
        return {"error": str(e)}


async def get_cost_analytics(days: int = 30) -> Dict[str, Any]:
    """Get cost trends and breakdown by source"""
    try:
        start_date = datetime.now() - timedelta(days=days)

        # Get daily cost from source performance table
        response = supabase_service.table("enrichment_source_performance") \
            .select("*") \
            .gte("date", start_date.date().isoformat()) \
            .order("date", desc=False) \
            .execute()

        performance_data = response.data if response.data else []

        # Aggregate by date
        daily_costs = {}
        source_totals = {}

        for record in performance_data:
            date_str = record.get("date")
            source = record.get("source_name")
            cost = float(record.get("total_cost_usd", 0))

            # Daily totals
            if date_str not in daily_costs:
                daily_costs[date_str] = 0
            daily_costs[date_str] += cost

            # Source totals
            if source not in source_totals:
                source_totals[source] = 0
            source_totals[source] += cost

        # Convert to sorted list
        daily_trend = [
            {"date": date, "cost_usd": round(cost, 4)}
            for date, cost in sorted(daily_costs.items())
        ]

        # Source breakdown
        source_breakdown = [
            {"source": source, "total_cost_usd": round(cost, 4)}
            for source, cost in sorted(source_totals.items(), key=lambda x: x[1], reverse=True)
        ]

        total_cost = sum(daily_costs.values())
        avg_daily_cost = total_cost / days if days > 0 else 0

        return {
            "period_days": days,
            "total_cost_usd": round(total_cost, 4),
            "avg_daily_cost_usd": round(avg_daily_cost, 4),
            "daily_trend": daily_trend,
            "source_breakdown": source_breakdown
        }
    except Exception as e:
        logger.error(f"Failed to get cost analytics: {str(e)}", exc_info=True)
        return {"error": str(e)}


async def get_performance_analytics(days: int = 30) -> Dict[str, Any]:
    """Get layer performance metrics"""
    try:
        start_date = datetime.now() - timedelta(days=days)

        # Get sessions
        response = supabase_service.table("progressive_enrichment_sessions") \
            .select("*") \
            .gte("created_at", start_date.isoformat()) \
            .execute()

        sessions = response.data if response.data else []

        # Calculate per-layer metrics
        layer_metrics = {}
        for layer_num in [1, 2, 3]:
            layer_key = f"layer{layer_num}"
            durations = [s.get(f"{layer_key}_duration_ms") for s in sessions if s.get(f"{layer_key}_duration_ms")]
            costs = [float(s.get(f"{layer_key}_cost_usd", 0)) for s in sessions if s.get(f"{layer_key}_cost_usd")]
            completed = [s for s in sessions if s.get(f"{layer_key}_completed_at")]

            layer_metrics[f"layer{layer_num}"] = {
                "avg_duration_ms": round(sum(durations) / len(durations), 0) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
                "avg_cost_usd": round(sum(costs) / len(costs), 6) if costs else 0,
                "completion_count": len(completed),
                "completion_rate_pct": round(100 * len(completed) / len(sessions), 1) if sessions else 0
            }

        return {
            "period_days": days,
            "total_sessions": len(sessions),
            "layer_metrics": layer_metrics
        }
    except Exception as e:
        logger.error(f"Failed to get performance analytics: {str(e)}", exc_info=True)
        return {"error": str(e)}


async def get_field_analytics(days: int = 30) -> Dict[str, Any]:
    """Get field auto-fill success rates"""
    try:
        start_date = datetime.now() - timedelta(days=days)

        # Get auto-fill suggestions
        response = supabase_service.table("auto_fill_suggestions") \
            .select("*") \
            .gte("suggested_at", start_date.isoformat()) \
            .execute()

        suggestions = response.data if response.data else []

        # Aggregate by field
        field_stats = {}
        for suggestion in suggestions:
            field_name = suggestion.get("field_name")
            if field_name not in field_stats:
                field_stats[field_name] = {
                    "total": 0,
                    "accepted": 0,
                    "edited": 0,
                    "auto_filled": 0,
                    "confidences": []
                }

            stats = field_stats[field_name]
            stats["total"] += 1
            if suggestion.get("was_accepted"):
                stats["accepted"] += 1
            if suggestion.get("was_edited"):
                stats["edited"] += 1
            if suggestion.get("should_auto_fill"):
                stats["auto_filled"] += 1
            if suggestion.get("confidence"):
                stats["confidences"].append(float(suggestion.get("confidence")))

        # Calculate percentages
        field_results = []
        for field_name, stats in field_stats.items():
            total = stats["total"]
            field_results.append({
                "field_name": field_name,
                "total_suggestions": total,
                "accepted_count": stats["accepted"],
                "edited_count": stats["edited"],
                "auto_filled_count": stats["auto_filled"],
                "acceptance_rate_pct": round(100 * stats["accepted"] / total, 1) if total > 0 else 0,
                "edit_rate_pct": round(100 * stats["edited"] / total, 1) if total > 0 else 0,
                "auto_fill_rate_pct": round(100 * stats["auto_filled"] / total, 1) if total > 0 else 0,
                "avg_confidence": round(sum(stats["confidences"]) / len(stats["confidences"]), 1) if stats["confidences"] else 0
            })

        # Sort by acceptance rate
        field_results.sort(key=lambda x: x["acceptance_rate_pct"], reverse=True)

        return {
            "period_days": days,
            "total_fields": len(field_results),
            "fields": field_results
        }
    except Exception as e:
        logger.error(f"Failed to get field analytics: {str(e)}", exc_info=True)
        return {"error": str(e)}


async def get_cache_analytics(days: int = 30) -> Dict[str, Any]:
    """Get cache hit rates and effectiveness"""
    try:
        start_date = datetime.now() - timedelta(days=days)

        # Get social media cache stats
        cache_response = supabase_service.table("social_media_cache") \
            .select("*") \
            .gte("validated_at", start_date.isoformat()) \
            .execute()

        cache_entries = cache_response.data if cache_response.data else []

        # Calculate cache metrics
        total_entries = len(cache_entries)
        valid_entries = sum(1 for e in cache_entries if e.get("is_valid"))

        # Count by platform
        platform_stats = {}
        for entry in cache_entries:
            platform = entry.get("platform")
            if platform not in platform_stats:
                platform_stats[platform] = {"total": 0, "valid": 0}
            platform_stats[platform]["total"] += 1
            if entry.get("is_valid"):
                platform_stats[platform]["valid"] += 1

        # Calculate validation success rate by platform
        platform_results = [
            {
                "platform": platform,
                "total_validations": stats["total"],
                "valid_count": stats["valid"],
                "validation_rate_pct": round(100 * stats["valid"] / stats["total"], 1) if stats["total"] > 0 else 0
            }
            for platform, stats in platform_stats.items()
        ]

        return {
            "period_days": days,
            "total_cache_entries": total_entries,
            "valid_entries": valid_entries,
            "validation_rate_pct": round(100 * valid_entries / total_entries, 1) if total_entries > 0 else 0,
            "platform_stats": platform_results
        }
    except Exception as e:
        logger.error(f"Failed to get cache analytics: {str(e)}", exc_info=True)
        return {"error": str(e)}


# ============================================================================
# USER EDIT TRACKING
# ============================================================================

async def track_user_edit(
    session_id: str,
    field_name: str,
    original_value: Optional[str],
    edited_value: str,
    confidence: Optional[float]
) -> Dict[str, Any]:
    """Track when user edits an auto-filled field"""
    try:
        # Find the suggestion for this field
        response = supabase_service.table("auto_fill_suggestions") \
            .select("*") \
            .eq("session_id", session_id) \
            .eq("field_name", field_name) \
            .order("suggested_at", desc=True) \
            .limit(1) \
            .execute()

        if response.data and len(response.data) > 0:
            suggestion = response.data[0]

            # Update the suggestion with user action
            update_response = supabase_service.table("auto_fill_suggestions") \
                .update({
                    "was_edited": True,
                    "final_value": edited_value,
                    "user_action_at": datetime.now().isoformat()
                }) \
                .eq("id", suggestion["id"]) \
                .execute()

            # Update session user_edits field
            session = await get_session_by_id(session_id)
            user_edits = session.get("user_edits", {}) if session else {}
            user_edits[field_name] = {
                "original": original_value,
                "edited": edited_value,
                "timestamp": datetime.now().isoformat()
            }

            supabase_service.table("progressive_enrichment_sessions") \
                .update({"user_edits": user_edits}) \
                .eq("session_id", session_id) \
                .execute()

            return {
                "success": True,
                "message": "Edit tracked successfully",
                "field_name": field_name,
                "confidence_adjustment": -5.0  # Reduce confidence for this field type
            }

        return {
            "success": False,
            "message": "No suggestion found for this field"
        }
    except Exception as e:
        logger.error(f"Failed to track user edit: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


async def get_learning_patterns(days: int = 30) -> Dict[str, Any]:
    """Get learning insights from user edits"""
    try:
        start_date = datetime.now() - timedelta(days=days)

        # Get all suggestions with user actions
        response = supabase_service.table("auto_fill_suggestions") \
            .select("*") \
            .gte("suggested_at", start_date.isoformat()) \
            .not_.is_("user_action_at", "null") \
            .execute()

        suggestions = response.data if response.data else []

        # Analyze patterns
        field_patterns = {}
        for suggestion in suggestions:
            field_name = suggestion.get("field_name")
            if field_name not in field_patterns:
                field_patterns[field_name] = {
                    "total_interactions": 0,
                    "edits": 0,
                    "accepts": 0,
                    "high_confidence_edits": 0,  # Edits where confidence was > 85%
                    "confidences": []
                }

            pattern = field_patterns[field_name]
            pattern["total_interactions"] += 1

            if suggestion.get("was_edited"):
                pattern["edits"] += 1
                if float(suggestion.get("confidence", 0)) > 85:
                    pattern["high_confidence_edits"] += 1
            elif suggestion.get("was_accepted"):
                pattern["accepts"] += 1

            pattern["confidences"].append(float(suggestion.get("confidence", 0)))

        # Calculate insights
        insights = []
        for field_name, pattern in field_patterns.items():
            total = pattern["total_interactions"]
            avg_conf = sum(pattern["confidences"]) / len(pattern["confidences"]) if pattern["confidences"] else 0

            insights.append({
                "field_name": field_name,
                "total_interactions": total,
                "edit_rate_pct": round(100 * pattern["edits"] / total, 1) if total > 0 else 0,
                "accept_rate_pct": round(100 * pattern["accepts"] / total, 1) if total > 0 else 0,
                "avg_confidence": round(avg_conf, 1),
                "high_confidence_edits": pattern["high_confidence_edits"],
                "recommended_confidence_threshold": max(70, round(avg_conf - 10, 0)),  # Lower threshold if users are editing
                "needs_improvement": pattern["high_confidence_edits"] > (pattern["edits"] * 0.3)  # >30% of edits were high confidence
            })

        # Sort by edit rate (highest first = needs most attention)
        insights.sort(key=lambda x: x["edit_rate_pct"], reverse=True)

        return {
            "period_days": days,
            "total_fields_analyzed": len(insights),
            "insights": insights
        }
    except Exception as e:
        logger.error(f"Failed to get learning patterns: {str(e)}", exc_info=True)
        return {"error": str(e)}
