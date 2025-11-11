"""
Form Enrichment Cache Service

Stores form enrichment session data for later reuse in strategic analysis.

Purpose:
- Cache enrichment results from Phase 1 (form auto-fill)
- Reuse cached data in Phase 2 (strategic analysis)
- Avoid re-scraping same company data
- Save API costs and processing time

Storage:
- Supabase table: enrichment_sessions (already exists)
- TTL: 30 days (auto-cleanup)
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from app.core.supabase import supabase_service

logger = logging.getLogger(__name__)


class FormEnrichmentCache:
    """
    Cache manager for form enrichment sessions.

    Stores progressive enrichment data in Supabase for reuse in strategic analysis.
    """

    def __init__(self, ttl_days: int = 30):
        """
        Initialize cache with TTL.

        Args:
            ttl_days: Time-to-live in days (default: 30)
        """
        self.ttl_days = ttl_days

    async def save_session(
        self,
        session_id: str,
        website_url: str,
        user_email: str,
        enrichment_data: Dict[str, Any]
    ) -> bool:
        """
        Save form enrichment session to Supabase.

        Args:
            session_id: Unique session identifier
            website_url: Company website URL
            user_email: User's email address
            enrichment_data: Complete enrichment session data from progressive orchestrator

        Returns:
            True if saved successfully, False otherwise
        """
        # Check if Supabase is available
        if supabase_service is None:
            logger.warning(
                "[FormEnrichmentCache] Supabase not configured - session caching disabled",
                extra={"component": "form_enrichment_cache", "session_id": session_id}
            )
            return False

        try:
            expires_at = datetime.now() + timedelta(days=self.ttl_days)

            # Prepare session data for storage
            session_record = {
                "cache_key": f"form_enrichment:{session_id}",
                "session_id": session_id,
                "website_url": website_url,
                "user_email": user_email,
                "session_data": enrichment_data,
                "total_cost_usd": enrichment_data.get("total_cost_usd", 0.0),
                "total_duration_ms": enrichment_data.get("total_duration_ms", 0),
                "status": "complete",
                "expires_at": expires_at.isoformat(),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }

            # Upsert to database (insert or update if exists)
            result = await supabase_service.table("enrichment_sessions").upsert(
                session_record,
                on_conflict="session_id"
            ).execute()

            logger.info(
                f"[CACHE] Saved form enrichment session: {session_id}",
                extra={
                    "session_id": session_id,
                    "website": website_url,
                    "cost": enrichment_data.get("total_cost_usd", 0.0),
                    "duration_ms": enrichment_data.get("total_duration_ms", 0),
                    "expires_at": expires_at.isoformat()
                }
            )

            return True

        except Exception as e:
            logger.error(
                f"[CACHE] Failed to save form enrichment session: {str(e)}",
                exc_info=True,
                extra={"session_id": session_id, "website": website_url}
            )
            return False

    async def load_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Load form enrichment session from Supabase.

        Args:
            session_id: Session identifier from Phase 1

        Returns:
            Enrichment data if found and not expired, None otherwise
        """
        # Check if Supabase is available
        if supabase_service is None:
            logger.warning(
                "[FormEnrichmentCache] Supabase not configured - cannot load session",
                extra={"component": "form_enrichment_cache", "session_id": session_id}
            )
            return None

        try:
            # Query database for session
            result = await supabase_service.table("enrichment_sessions").select("*").eq(
                "session_id", session_id
            ).execute()

            if not result.data or len(result.data) == 0:
                logger.warning(f"[CACHE] Session not found: {session_id}")
                return None

            session_record = result.data[0]

            # Check if expired
            expires_at = datetime.fromisoformat(session_record["expires_at"])
            if datetime.now() > expires_at:
                logger.warning(
                    f"[CACHE] Session expired: {session_id}",
                    extra={"expired_at": expires_at.isoformat()}
                )
                # Clean up expired session
                await self._delete_session(session_id)
                return None

            logger.info(
                f"[CACHE] Loaded form enrichment session: {session_id}",
                extra={
                    "session_id": session_id,
                    "website": session_record.get("website_url"),
                    "age_days": (datetime.now() - datetime.fromisoformat(session_record["created_at"])).days
                }
            )

            return session_record.get("session_data")

        except Exception as e:
            logger.error(
                f"[CACHE] Failed to load form enrichment session: {str(e)}",
                exc_info=True,
                extra={"session_id": session_id}
            )
            return None

    async def _delete_session(self, session_id: str):
        """
        Delete expired session from database.

        Args:
            session_id: Session to delete
        """
        try:
            await supabase_service.table("enrichment_sessions").delete().eq(
                "session_id", session_id
            ).execute()

            logger.info(f"[CACHE] Deleted expired session: {session_id}")

        except Exception as e:
            logger.error(
                f"[CACHE] Failed to delete expired session: {str(e)}",
                extra={"session_id": session_id}
            )

    async def cleanup_expired(self) -> int:
        """
        Clean up all expired sessions from database.

        Returns:
            Number of sessions deleted
        """
        try:
            now = datetime.now().isoformat()

            # Delete all sessions where expires_at < now
            result = await supabase_service.table("enrichment_sessions").delete().lt(
                "expires_at", now
            ).execute()

            deleted_count = len(result.data) if result.data else 0

            logger.info(
                f"[CACHE] Cleaned up {deleted_count} expired form enrichment sessions"
            )

            return deleted_count

        except Exception as e:
            logger.error(
                f"[CACHE] Failed to cleanup expired sessions: {str(e)}",
                exc_info=True
            )
            return 0

    async def get_session_stats(self) -> Dict[str, Any]:
        """
        Get statistics about cached sessions.

        Returns:
            Dict with total sessions, total cost, avg duration, etc.
        """
        try:
            # Query all non-expired sessions
            now = datetime.now().isoformat()
            result = await supabase_service.table("enrichment_sessions").select("*").gt(
                "expires_at", now
            ).execute()

            sessions = result.data if result.data else []

            if not sessions:
                return {
                    "total_sessions": 0,
                    "total_cost_usd": 0.0,
                    "avg_duration_ms": 0,
                    "oldest_session": None,
                    "newest_session": None
                }

            # Calculate stats
            total_cost = sum(s.get("total_cost_usd", 0.0) for s in sessions)
            total_duration = sum(s.get("total_duration_ms", 0) for s in sessions)
            avg_duration = total_duration / len(sessions) if sessions else 0

            # Find oldest and newest
            sorted_by_date = sorted(
                sessions,
                key=lambda s: s.get("created_at", ""),
            )

            return {
                "total_sessions": len(sessions),
                "total_cost_usd": round(total_cost, 4),
                "avg_duration_ms": int(avg_duration),
                "oldest_session": sorted_by_date[0].get("created_at") if sorted_by_date else None,
                "newest_session": sorted_by_date[-1].get("created_at") if sorted_by_date else None,
            }

        except Exception as e:
            logger.error(
                f"[CACHE] Failed to get session stats: {str(e)}",
                exc_info=True
            )
            return {
                "error": str(e),
                "total_sessions": 0
            }
