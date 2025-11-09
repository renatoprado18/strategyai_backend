"""
Caching wrapper logic for Apify operations.

This module provides intelligent caching via institutional_memory
to reduce costs and improve speed of Apify operations.
"""
from typing import Dict, Any, Callable
import logging
from app.services.intelligence.memory import store_memory, retrieve_memory

logger = logging.getLogger(__name__)

# Cache configuration
APIFY_CACHE_TTL_HOURS = 24 * 7  # 7 days cache for Apify data


async def _cached_apify_call(
    cache_entity_type: str,
    cache_entity_id: str,
    apify_func: Callable,
    *args,
    **kwargs
) -> Dict[str, Any]:
    """
    Wrapper to check cache before calling Apify, store on success

    Args:
        cache_entity_type: Type for institutional memory (e.g., "apify_website")
        cache_entity_id: Unique ID for cache key (e.g., website URL)
        apify_func: The async Apify function to call
        *args, **kwargs: Arguments to pass to the function

    Returns:
        Cached or fresh Apify data
    """
    # Check cache first
    cached_data = await retrieve_memory(
        entity_type=cache_entity_type,
        entity_id=cache_entity_id,
        max_age_hours=APIFY_CACHE_TTL_HOURS
    )

    if cached_data:
        logger.info(f"[APIFY CACHE] ✅ HIT: {cache_entity_type}:{cache_entity_id}")
        return cached_data

    logger.info(f"[APIFY CACHE] ❌ MISS: {cache_entity_type}:{cache_entity_id} - calling Apify...")

    # Cache miss - call the actual Apify function
    result = await apify_func(*args, **kwargs)

    # Store in cache if successful (no error field or error is None)
    if not result.get("error"):
        await store_memory(
            entity_type=cache_entity_type,
            entity_id=cache_entity_id,
            data=result,
            source="apify",
            confidence=0.9  # High confidence for direct Apify data
        )
        logger.info(f"[APIFY CACHE] 💾 STORED: {cache_entity_type}:{cache_entity_id}")

    return result
