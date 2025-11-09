"""
Stage Cache Wrapper - Handles caching for analysis stages
Extracted from multistage.py for better code organization
"""

import logging
from typing import Dict, Any, Callable

from app.core.cache import (
    cache_stage_result,
    get_cached_stage_result,
)
from app.core.exceptions import CacheError

logger = logging.getLogger(__name__)


async def run_stage_with_cache(
    stage_name: str,
    stage_function: Callable,
    company: str,
    industry: str,
    input_data: Dict[str, Any],
    estimated_cost: float,
    **stage_kwargs
) -> Dict[str, Any]:
    """
    Execute a stage with automatic caching

    This wrapper provides transparent caching for expensive LLM operations.
    It checks the cache first, and only executes the stage function on cache miss.

    Args:
        stage_name: Name of the stage (e.g., "extraction", "strategy")
        stage_function: The async function to call if cache miss
        company: Company name (for cache key)
        industry: Industry (for cache key)
        input_data: Input data to hash for cache key
        estimated_cost: Estimated cost of running this stage (for cache metrics)
        **stage_kwargs: Additional kwargs to pass to stage_function

    Returns:
        Stage result dict (from cache or fresh execution)

    Raises:
        Exception: Re-raises any exception from stage_function execution
    """
    try:
        # Check cache first
        cached_result = await get_cached_stage_result(
            stage_name=stage_name,
            company=company,
            industry=industry,
            input_data=input_data
        )

        if cached_result:
            logger.info(
                f"[CACHE HIT] ✅ Stage '{stage_name}' loaded from cache "
                f"(saves ${estimated_cost:.4f})"
            )
            # Ensure cached results have _usage_stats (set to 0 for cache hits)
            if "_usage_stats" not in cached_result:
                cached_result["_usage_stats"] = {
                    "input_tokens": 0,
                    "output_tokens": 0
                }
            return cached_result

        # Cache miss - execute stage
        logger.info(f"[CACHE MISS] Stage '{stage_name}' - executing fresh...")
        result = await stage_function(**stage_kwargs)

        # Cache the result (async, non-blocking)
        try:
            await cache_stage_result(
                stage_name=stage_name,
                company=company,
                industry=industry,
                input_data=input_data,
                stage_result=result,
                cost=estimated_cost
            )
        except Exception as cache_error:
            # Don't fail the stage if caching fails
            logger.warning(
                f"[CACHE] Failed to cache stage '{stage_name}': {cache_error}",
                exc_info=True
            )

        return result

    except CacheError as e:
        # If caching infrastructure fails, execute without cache
        logger.warning(
            f"[CACHE] Cache infrastructure error for '{stage_name}': {e}. "
            "Executing without cache."
        )
        return await stage_function(company=company, industry=industry, **stage_kwargs)

    except Exception as e:
        # If anything else goes wrong with caching, just run the stage
        logger.warning(
            f"[CACHE] Error in cache wrapper for '{stage_name}': {e}. "
            "Falling back to direct execution."
        )
        return await stage_function(company=company, industry=industry, **stage_kwargs)


async def invalidate_stage_cache(
    stage_name: str,
    company: str,
    industry: str,
    input_data: Dict[str, Any]
) -> bool:
    """
    Invalidate cache for a specific stage

    Args:
        stage_name: Name of the stage
        company: Company name
        industry: Industry
        input_data: Input data (to generate cache key)

    Returns:
        True if cache was invalidated, False otherwise
    """
    try:
        from app.core.cache import delete_cached_stage_result

        await delete_cached_stage_result(
            stage_name=stage_name,
            company=company,
            industry=industry,
            input_data=input_data
        )
        logger.info(f"[CACHE] Invalidated cache for stage '{stage_name}'")
        return True
    except Exception as e:
        logger.error(f"[CACHE] Failed to invalidate cache for '{stage_name}': {e}")
        return False


class StageCacheManager:
    """
    Context manager for stage caching operations
    Provides cleaner interface for cache operations
    """

    def __init__(self, stage_name: str, company: str, industry: str):
        self.stage_name = stage_name
        self.company = company
        self.industry = industry

    async def get(self, input_data: Dict[str, Any]) -> Dict[str, Any] | None:
        """Get cached result for stage"""
        return await get_cached_stage_result(
            stage_name=self.stage_name,
            company=self.company,
            industry=self.industry,
            input_data=input_data
        )

    async def set(
        self,
        input_data: Dict[str, Any],
        result: Dict[str, Any],
        cost: float = 0.0
    ) -> None:
        """Cache result for stage"""
        await cache_stage_result(
            stage_name=self.stage_name,
            company=self.company,
            industry=self.industry,
            input_data=input_data,
            stage_result=result,
            cost=cost
        )

    async def invalidate(self, input_data: Dict[str, Any]) -> bool:
        """Invalidate cached result for stage"""
        return await invalidate_stage_cache(
            stage_name=self.stage_name,
            company=self.company,
            industry=self.industry,
            input_data=input_data
        )
