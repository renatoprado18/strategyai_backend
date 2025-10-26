"""
Institutional Memory & Caching System
Store and reuse key findings across analyses to reduce costs and improve quality

Uses Supabase for persistent storage + in-memory caching
"""

import json
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from supabase_client import supabase_service
import logging

logger = logging.getLogger(__name__)

# In-memory cache (resets on restart, but fast)
_memory_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_HOURS = 24 * 7  # 7 days

# Table names (create via Supabase SQL)
MEMORY_TABLE = "institutional_memory"


# ============================================================================
# CACHE KEY GENERATION
# ============================================================================

def generate_cache_key(entity_type: str, entity_id: str) -> str:
    """Generate consistent cache key"""
    return f"{entity_type}:{entity_id.lower().strip()}"


def generate_hash(content: str) -> str:
    """Generate content hash for deduplication"""
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# ============================================================================
# MEMORY STORAGE (Supabase)
# ============================================================================

async def store_memory(
    entity_type: str,  # "company", "competitor", "industry_trends", "market_data"
    entity_id: str,  # Company name, competitor name, industry name
    data: Dict[str, Any],
    source: str = "analysis",  # Where this came from
    confidence: float = 0.8  # How confident are we in this data
) -> bool:
    """
    Store institutional memory in Supabase

    Args:
        entity_type: Type of entity (company, competitor, industry_trends, market_data)
        entity_id: Unique identifier (company name, etc.)
        data: The actual data to store
        source: Where this data came from (analysis, apify, perplexity)
        confidence: Confidence score 0-1
    """
    try:
        cache_key = generate_cache_key(entity_type, entity_id)
        content_hash = generate_hash(json.dumps(data, sort_keys=True))

        # Check if exact same data already exists
        existing = supabase_service.table(MEMORY_TABLE)\
            .select("id, data")\
            .eq("cache_key", cache_key)\
            .eq("content_hash", content_hash)\
            .execute()

        if existing.data and len(existing.data) > 0:
            # Update last_accessed timestamp
            supabase_service.table(MEMORY_TABLE)\
                .update({"last_accessed_at": datetime.utcnow().isoformat()})\
                .eq("id", existing.data[0]["id"])\
                .execute()

            logger.info(f"[MEMORY] Cache hit: {cache_key} (updated timestamp)")
            _memory_cache[cache_key] = existing.data[0]["data"]
            return True

        # Store new memory
        record = {
            "entity_type": entity_type,
            "entity_id": entity_id.lower().strip(),
            "cache_key": cache_key,
            "content_hash": content_hash,
            "data": json.dumps(data, ensure_ascii=False),
            "source": source,
            "confidence": confidence,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed_at": datetime.utcnow().isoformat(),
            "access_count": 1
        }

        result = supabase_service.table(MEMORY_TABLE).insert(record).execute()

        if result.data:
            _memory_cache[cache_key] = data
            logger.info(f"[MEMORY] Stored new memory: {cache_key}")
            return True

        return False

    except Exception as e:
        logger.error(f"[MEMORY] Failed to store memory: {str(e)}")
        return False


async def retrieve_memory(
    entity_type: str,
    entity_id: str,
    max_age_hours: int = CACHE_TTL_HOURS
) -> Optional[Dict[str, Any]]:
    """
    Retrieve institutional memory from cache or Supabase

    Returns cached data if available and fresh, otherwise None
    """
    try:
        cache_key = generate_cache_key(entity_type, entity_id)

        # Check in-memory cache first
        if cache_key in _memory_cache:
            logger.info(f"[MEMORY] In-memory cache hit: {cache_key}")
            return _memory_cache[cache_key]

        # Query Supabase
        cutoff_time = (datetime.utcnow() - timedelta(hours=max_age_hours)).isoformat()

        result = supabase_service.table(MEMORY_TABLE)\
            .select("*")\
            .eq("cache_key", cache_key)\
            .gte("last_accessed_at", cutoff_time)\
            .order("confidence", desc=True)\
            .limit(1)\
            .execute()

        if result.data and len(result.data) > 0:
            record = result.data[0]

            # Update access stats
            supabase_service.table(MEMORY_TABLE)\
                .update({
                    "last_accessed_at": datetime.utcnow().isoformat(),
                    "access_count": record["access_count"] + 1
                })\
                .eq("id", record["id"])\
                .execute()

            # Parse and cache
            data = json.loads(record["data"])
            _memory_cache[cache_key] = data

            logger.info(f"[MEMORY] Database cache hit: {cache_key} (age: {record['created_at']})")
            return data

        logger.info(f"[MEMORY] Cache miss: {cache_key}")
        return None

    except Exception as e:
        logger.error(f"[MEMORY] Failed to retrieve memory: {str(e)}")
        return None


# ============================================================================
# SMART CACHING FOR ANALYSIS
# ============================================================================

async def cache_company_profile(
    company: str,
    industry: str,
    extracted_data: Dict[str, Any],
    source: str = "multistage_analysis"
) -> bool:
    """Cache company profile for future analyses"""

    profile = {
        "company": company,
        "industry": industry,
        "company_facts": extracted_data.get("company_facts", {}),
        "key_metrics": extracted_data.get("key_metrics", {}),
        "products_services": extracted_data.get("products_services", []),
        "cached_at": datetime.utcnow().isoformat()
    }

    return await store_memory(
        entity_type="company",
        entity_id=company,
        data=profile,
        source=source,
        confidence=0.9
    )


async def cache_competitor_data(
    company: str,
    competitors: List[Dict[str, Any]],
    source: str = "competitor_analysis"
) -> bool:
    """Cache competitor data for reuse"""

    competitor_map = {
        "analyzed_for": company,
        "competitors": competitors,
        "cached_at": datetime.utcnow().isoformat()
    }

    # Store as industry-level cache (all companies in same industry can use this)
    return await store_memory(
        entity_type="competitor_map",
        entity_id=company,
        data=competitor_map,
        source=source,
        confidence=0.85
    )


async def cache_industry_insights(
    industry: str,
    trends: List[str],
    market_size: Dict[str, Any],
    source: str = "market_research"
) -> bool:
    """Cache industry-level insights"""

    insights = {
        "industry": industry,
        "trends": trends,
        "market_size": market_size,
        "cached_at": datetime.utcnow().isoformat()
    }

    return await store_memory(
        entity_type="industry_trends",
        entity_id=industry,
        data=insights,
        source=source,
        confidence=0.7  # Trends change, so lower confidence
    )


# ============================================================================
# SMART RETRIEVAL FOR NEW ANALYSES
# ============================================================================

async def get_cached_company_profile(company: str) -> Optional[Dict[str, Any]]:
    """Get cached company profile if available"""
    return await retrieve_memory("company", company, max_age_hours=24 * 30)  # 30 days


async def get_cached_competitor_data(company: str) -> Optional[Dict[str, Any]]:
    """Get cached competitor data"""
    return await retrieve_memory("competitor_map", company, max_age_hours=24 * 7)  # 7 days


async def get_cached_industry_insights(industry: str) -> Optional[Dict[str, Any]]:
    """Get cached industry insights"""
    return await retrieve_memory("industry_trends", industry, max_age_hours=24 * 3)  # 3 days (trends change fast)


# ============================================================================
# CACHE STATISTICS
# ============================================================================

async def get_cache_stats() -> Dict[str, Any]:
    """Get statistics about institutional memory usage"""
    try:
        # Total records
        total_result = supabase_service.table(MEMORY_TABLE).select("id", count="exact").execute()
        total_count = total_result.count if hasattr(total_result, 'count') else 0

        # By entity type
        by_type = supabase_service.table(MEMORY_TABLE)\
            .select("entity_type")\
            .execute()

        type_counts = {}
        if by_type.data:
            for record in by_type.data:
                etype = record["entity_type"]
                type_counts[etype] = type_counts.get(etype, 0) + 1

        # Most accessed
        most_accessed = supabase_service.table(MEMORY_TABLE)\
            .select("entity_id, entity_type, access_count")\
            .order("access_count", desc=True)\
            .limit(10)\
            .execute()

        return {
            "total_records": total_count,
            "by_type": type_counts,
            "most_accessed": most_accessed.data if most_accessed.data else [],
            "in_memory_cache_size": len(_memory_cache)
        }

    except Exception as e:
        logger.error(f"[MEMORY] Failed to get cache stats: {str(e)}")
        return {
            "total_records": 0,
            "by_type": {},
            "most_accessed": [],
            "in_memory_cache_size": len(_memory_cache)
        }
