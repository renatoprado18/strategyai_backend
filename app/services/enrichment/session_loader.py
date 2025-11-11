"""
Session Loader - Phase 2 Cache Reuse
====================================

Loads cached enrichment data from Phase 1 (form enrichment) for use in Phase 2 (strategic analysis).

This eliminates duplicate API calls and scraping by reusing the data that was collected
during form auto-fill.

Architecture:
- Phase 1: User enters website → Form enrichment API collects data → Session cached
- Phase 2: User submits form → Load session → Skip re-scraping → Generate analysis

Author: Claude Code + Claude Flow Agents
Date: 2025-01-10
"""

from typing import Dict, Any, Optional
from datetime import datetime
import logging

from app.core.supabase import supabase_service

logger = logging.getLogger(__name__)


async def load_enrichment_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Load cached enrichment session from Supabase with expiration check.

    Args:
        session_id: The session ID from Phase 1 form enrichment

    Returns:
        Dict containing enrichment data, or None if session not found/expired

    Session data structure:
    {
        "domain": "google.com",
        "email": "user@example.com",
        "layer1_data": {...},  # Metadata + geolocation
        "layer2_data": {...},  # Paid APIs (Clearbit, ReceitaWS, etc.)
        "layer3_data": {...},  # AI inference + LinkedIn
        "fields_auto_filled": [...],  # List of auto-filled field names
        "confidence_scores": {...},  # Field confidence scores
        "created_at": "2025-01-10T12:00:00Z",
        "expires_at": "2025-02-09T12:00:00Z"
    }
    """
    # Check if Supabase is available
    if supabase_service is None:
        logger.warning(
            "[SessionLoader] Supabase not configured - cannot load session",
            extra={"component": "session_loader", "session_id": session_id}
        )
        return None

    try:
        logger.info(
            f"[SessionLoader] Loading enrichment session",
            extra={
                "component": "session_loader",
                "session_id": session_id
            }
        )

        # Query Supabase for session
        result = await supabase_service.table("enrichment_sessions") \
            .select("*") \
            .eq("session_id", session_id) \
            .single() \
            .execute()

        if not result.data:
            logger.warning(
                f"[SessionLoader] Session not found",
                extra={
                    "component": "session_loader",
                    "session_id": session_id
                }
            )
            return None

        session_data = result.data

        # Check expiration (30-day TTL)
        expires_at = datetime.fromisoformat(session_data["expires_at"].replace("Z", "+00:00"))
        now = datetime.now(expires_at.tzinfo)

        if now > expires_at:
            logger.warning(
                f"[SessionLoader] Session expired",
                extra={
                    "component": "session_loader",
                    "session_id": session_id,
                    "expired_at": expires_at.isoformat()
                }
            )
            return None

        enrichment_data = session_data.get("session_data", {})

        logger.info(
            f"[SessionLoader] Session loaded successfully",
            extra={
                "component": "session_loader",
                "session_id": session_id,
                "fields_count": len(enrichment_data.get("fields_auto_filled", [])),
                "has_layer1": bool(enrichment_data.get("layer1_data")),
                "has_layer2": bool(enrichment_data.get("layer2_data")),
                "has_layer3": bool(enrichment_data.get("layer3_data"))
            }
        )

        return enrichment_data

    except Exception as e:
        logger.error(
            f"[SessionLoader] Failed to load enrichment session: {str(e)}",
            extra={
                "component": "session_loader",
                "session_id": session_id,
                "error": str(e)
            },
            exc_info=True
        )
        return None


async def validate_enrichment_data(enrichment_data: Dict[str, Any]) -> bool:
    """
    Validate that enrichment data contains required fields.

    Args:
        enrichment_data: The cached enrichment data

    Returns:
        True if data is valid and usable, False otherwise
    """
    try:
        # Check for required keys
        required_keys = ["domain", "layer1_data"]
        for key in required_keys:
            if key not in enrichment_data:
                logger.warning(
                    f"[SessionLoader] Missing required key: {key}",
                    extra={"component": "session_loader", "missing_key": key}
                )
                return False

        # Check that at least Layer 1 has data
        layer1_data = enrichment_data.get("layer1_data", {})
        if not layer1_data or len(layer1_data) == 0:
            logger.warning(
                "[SessionLoader] Layer 1 data is empty",
                extra={"component": "session_loader"}
            )
            return False

        logger.info(
            "[SessionLoader] Enrichment data validated successfully",
            extra={
                "component": "session_loader",
                "layer1_fields": len(layer1_data),
                "layer2_fields": len(enrichment_data.get("layer2_data", {})),
                "layer3_fields": len(enrichment_data.get("layer3_data", {}))
            }
        )

        return True

    except Exception as e:
        logger.error(
            f"[SessionLoader] Validation failed: {str(e)}",
            extra={"component": "session_loader", "error": str(e)},
            exc_info=True
        )
        return False


def merge_enrichment_with_submission(
    enrichment_data: Dict[str, Any],
    submission_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge cached enrichment data with user-submitted form data.

    User may have edited auto-filled fields, so submission data takes precedence.

    Args:
        enrichment_data: Cached data from Phase 1
        submission_data: User-edited form data from submission

    Returns:
        Merged data dictionary with user edits applied
    """
    try:
        # Start with enrichment data
        merged = {
            "layer1_data": enrichment_data.get("layer1_data", {}),
            "layer2_data": enrichment_data.get("layer2_data", {}),
            "layer3_data": enrichment_data.get("layer3_data", {}),
        }

        # Apply user edits from submission
        # User's form data should override auto-filled data
        user_overrides = {}

        # Map submission fields to enrichment fields
        field_mapping = {
            "name": "company_name",
            "company": "company_name",
            "website": "website_url",
            "industry": "industry",
            "challenge": "description",
            "linkedin_company": "linkedin_url",
            "linkedin_founder": "linkedin_founder_url"
        }

        for submit_field, enrich_field in field_mapping.items():
            if submit_field in submission_data and submission_data[submit_field]:
                user_overrides[enrich_field] = submission_data[submit_field]

        # Add user overrides to merged data
        merged["user_edits"] = user_overrides

        logger.info(
            "[SessionLoader] Merged enrichment data with submission",
            extra={
                "component": "session_loader",
                "user_edits_count": len(user_overrides),
                "user_edit_fields": list(user_overrides.keys())
            }
        )

        return merged

    except Exception as e:
        logger.error(
            f"[SessionLoader] Merge failed: {str(e)}",
            extra={"component": "session_loader", "error": str(e)},
            exc_info=True
        )
        # Return enrichment data as fallback
        return enrichment_data
