"""
Enhanced Caching System
Aggressive caching for expensive operations to minimize costs

Cache Strategy:
1. AI Analysis Results - Cache complete analysis by company+industry+challenge (30 days)
2. AI Stage Results - Cache individual pipeline stages (7 days)
3. PDF Generation - Cache PDFs by content hash (90 days)
4. Dashboard Stats - Cache computed stats (5 minutes)
5. Perplexity Queries - Cache all queries aggressively (14 days)

Uses Supabase for persistent storage + in-memory for speed
"""

import json
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from supabase_client import supabase_service

logger = logging.getLogger(__name__)

# In-memory caches (fast but ephemeral)
_analysis_cache: Dict[str, Dict[str, Any]] = {}
_stage_cache: Dict[str, Dict[str, Any]] = {}
_pdf_cache: Dict[str, bytes] = {}
_stats_cache: Dict[str, Any] = {}

# Cache tables
ANALYSIS_CACHE_TABLE = "analysis_cache"
STAGE_CACHE_TABLE = "stage_cache"
PDF_CACHE_TABLE = "pdf_cache"
STATS_CACHE_TABLE = "stats_cache"

# TTLs (in hours)
TTL_ANALYSIS = 24 * 30  # 30 days for complete analysis
TTL_STAGE = 24 * 7  # 7 days for pipeline stages
TTL_PDF = 24 * 90  # 90 days for PDFs (cheap to store)
TTL_STATS = 1/12  # 5 minutes for dashboard stats
TTL_PERPLEXITY = 24 * 14  # 14 days for Perplexity queries


# ============================================================================
# CACHE KEY GENERATION
# ============================================================================

def generate_analysis_cache_key(
    company: str,
    industry: str,
    challenge: Optional[str] = None,
    website: Optional[str] = None
) -> str:
    """
    Generate cache key for complete analysis

    Key includes: company + industry + challenge + website
    This ensures we don't return wrong analysis for different challenges
    """
    components = [
        company.lower().strip(),
        industry.lower().strip(),
        (challenge or "").lower().strip()[:50],  # First 50 chars of challenge
        (website or "").lower().strip()
    ]

    # Create deterministic hash
    key_string = "|".join(components)
    key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

    return f"analysis:{company.lower().strip()}:{key_hash}"


def generate_stage_cache_key(
    stage_name: str,
    company: str,
    industry: str,
    input_hash: str
) -> str:
    """
    Generate cache key for individual pipeline stage

    Allows caching stage results independently
    """
    key_string = f"{stage_name}|{company.lower().strip()}|{industry.lower().strip()}|{input_hash}"
    key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]

    return f"stage:{stage_name}:{key_hash}"


def generate_content_hash(content: Any) -> str:
    """Generate hash of content for cache key"""
    if isinstance(content, dict):
        content = json.dumps(content, sort_keys=True, ensure_ascii=False)
    elif isinstance(content, bytes):
        return hashlib.sha256(content).hexdigest()[:16]

    return hashlib.sha256(str(content).encode()).hexdigest()[:16]


def generate_pdf_cache_key(report_json: Dict[str, Any]) -> str:
    """Generate cache key for PDF based on report content"""
    content_hash = generate_content_hash(report_json)
    return f"pdf:{content_hash}"


# ============================================================================
# ANALYSIS RESULT CACHING (MOST IMPORTANT - SAVES $15-25 PER HIT)
# ============================================================================

async def cache_analysis_result(
    company: str,
    industry: str,
    challenge: Optional[str],
    website: Optional[str],
    analysis_result: Dict[str, Any],
    cost: float,
    processing_time: float
) -> bool:
    """
    Cache complete analysis result

    This is THE most important cache - saves $15-25 per cache hit!
    """
    try:
        cache_key = generate_analysis_cache_key(company, industry, challenge, website)
        content_hash = generate_content_hash(analysis_result)

        # Store in Supabase
        record = {
            "cache_key": cache_key,
            "company": company.lower().strip(),
            "industry": industry.lower().strip(),
            "challenge_snippet": (challenge or "")[:100],
            "content_hash": content_hash,
            "analysis_json": json.dumps(analysis_result, ensure_ascii=False),
            "cost_saved": cost,  # Track how much we save per hit
            "processing_time_seconds": processing_time,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed_at": datetime.utcnow().isoformat(),
            "hit_count": 0
        }

        result = supabase_service.table(ANALYSIS_CACHE_TABLE).insert(record).execute()

        if result.data:
            # Store in memory for fast access
            _analysis_cache[cache_key] = {
                "analysis": analysis_result,
                "cost_saved": cost,
                "cached_at": datetime.utcnow()
            }

            logger.info(f"[CACHE] ✅ Cached analysis: {cache_key} (saves ${cost:.2f} per hit)")
            return True

        return False

    except Exception as e:
        logger.error(f"[CACHE] ❌ Failed to cache analysis: {str(e)}")
        return False


async def get_cached_analysis(
    company: str,
    industry: str,
    challenge: Optional[str],
    website: Optional[str]
) -> Optional[Dict[str, Any]]:
    """
    Retrieve cached analysis if available

    Returns analysis + metadata about cache hit
    """
    try:
        cache_key = generate_analysis_cache_key(company, industry, challenge, website)

        # Check in-memory cache first (fastest)
        if cache_key in _analysis_cache:
            cached = _analysis_cache[cache_key]
            age = (datetime.utcnow() - cached["cached_at"]).total_seconds() / 3600

            if age < TTL_ANALYSIS:
                logger.info(f"[CACHE] 🎯 In-memory analysis hit: {cache_key} (saves ${cached['cost_saved']:.2f})")
                return {
                    "analysis": cached["analysis"],
                    "cache_hit": True,
                    "cache_age_hours": age,
                    "cost_saved": cached["cost_saved"]
                }

        # Check database
        cutoff_time = (datetime.utcnow() - timedelta(hours=TTL_ANALYSIS)).isoformat()

        result = supabase_service.table(ANALYSIS_CACHE_TABLE)\
            .select("*")\
            .eq("cache_key", cache_key)\
            .gte("last_accessed_at", cutoff_time)\
            .limit(1)\
            .execute()

        if result.data and len(result.data) > 0:
            record = result.data[0]

            # Update hit stats
            supabase_service.table(ANALYSIS_CACHE_TABLE)\
                .update({
                    "last_accessed_at": datetime.utcnow().isoformat(),
                    "hit_count": record["hit_count"] + 1
                })\
                .eq("cache_key", cache_key)\
                .execute()

            # Parse and cache in memory
            analysis = json.loads(record["analysis_json"])
            _analysis_cache[cache_key] = {
                "analysis": analysis,
                "cost_saved": record["cost_saved"],
                "cached_at": datetime.fromisoformat(record["created_at"])
            }

            age = (datetime.utcnow() - datetime.fromisoformat(record["created_at"])).total_seconds() / 3600

            logger.info(f"[CACHE] 🎯 Database analysis hit: {cache_key} (saves ${record['cost_saved']:.2f}, age: {age:.1f}h, hits: {record['hit_count']})")

            return {
                "analysis": analysis,
                "cache_hit": True,
                "cache_age_hours": age,
                "cost_saved": record["cost_saved"],
                "hit_count": record["hit_count"] + 1
            }

        logger.info(f"[CACHE] ❌ Analysis cache miss: {cache_key}")
        return None

    except Exception as e:
        logger.error(f"[CACHE] Error retrieving analysis cache: {str(e)}")
        return None


# ============================================================================
# PIPELINE STAGE CACHING (SAVES INDIVIDUAL AI CALLS)
# ============================================================================

async def cache_stage_result(
    stage_name: str,
    company: str,
    industry: str,
    input_data: Dict[str, Any],
    stage_result: Dict[str, Any],
    cost: float
) -> bool:
    """Cache individual pipeline stage result"""
    try:
        input_hash = generate_content_hash(input_data)
        cache_key = generate_stage_cache_key(stage_name, company, industry, input_hash)

        record = {
            "cache_key": cache_key,
            "stage_name": stage_name,
            "company": company.lower().strip(),
            "industry": industry.lower().strip(),
            "input_hash": input_hash,
            "result_json": json.dumps(stage_result, ensure_ascii=False),
            "cost_saved": cost,
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed_at": datetime.utcnow().isoformat(),
            "hit_count": 0
        }

        result = supabase_service.table(STAGE_CACHE_TABLE).insert(record).execute()

        if result.data:
            _stage_cache[cache_key] = {
                "result": stage_result,
                "cached_at": datetime.utcnow()
            }
            logger.info(f"[CACHE] ✅ Cached stage '{stage_name}': {cache_key} (saves ${cost:.2f})")
            return True

        return False

    except Exception as e:
        logger.error(f"[CACHE] Failed to cache stage: {str(e)}")
        return False


async def get_cached_stage_result(
    stage_name: str,
    company: str,
    industry: str,
    input_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Retrieve cached stage result if available"""
    try:
        input_hash = generate_content_hash(input_data)
        cache_key = generate_stage_cache_key(stage_name, company, industry, input_hash)

        # Check in-memory
        if cache_key in _stage_cache:
            cached = _stage_cache[cache_key]
            age = (datetime.utcnow() - cached["cached_at"]).total_seconds() / 3600

            if age < TTL_STAGE:
                logger.info(f"[CACHE] 🎯 In-memory stage hit: {stage_name}")
                return cached["result"]

        # Check database
        cutoff_time = (datetime.utcnow() - timedelta(hours=TTL_STAGE)).isoformat()

        result = supabase_service.table(STAGE_CACHE_TABLE)\
            .select("*")\
            .eq("cache_key", cache_key)\
            .gte("last_accessed_at", cutoff_time)\
            .limit(1)\
            .execute()

        if result.data and len(result.data) > 0:
            record = result.data[0]

            # Update stats
            supabase_service.table(STAGE_CACHE_TABLE)\
                .update({
                    "last_accessed_at": datetime.utcnow().isoformat(),
                    "hit_count": record["hit_count"] + 1
                })\
                .eq("cache_key", cache_key)\
                .execute()

            stage_result = json.loads(record["result_json"])
            _stage_cache[cache_key] = {
                "result": stage_result,
                "cached_at": datetime.utcnow()
            }

            logger.info(f"[CACHE] 🎯 Database stage hit: {stage_name} (saves ${record['cost_saved']:.2f})")
            return stage_result

        return None

    except Exception as e:
        logger.error(f"[CACHE] Error retrieving stage cache: {str(e)}")
        return None


# ============================================================================
# PDF CACHING (SAVES COMPUTATION TIME)
# ============================================================================

async def cache_pdf(
    report_json: Dict[str, Any],
    pdf_bytes: bytes,
    submission_id: int
) -> bool:
    """Cache generated PDF"""
    try:
        cache_key = generate_pdf_cache_key(report_json)

        # Note: Storing large binary data in Supabase can be expensive
        # Consider using Supabase Storage instead for production
        # For now, we'll cache metadata and reference file system

        record = {
            "cache_key": cache_key,
            "submission_id": submission_id,
            "content_hash": generate_content_hash(pdf_bytes),
            "file_size_bytes": len(pdf_bytes),
            "created_at": datetime.utcnow().isoformat(),
            "last_accessed_at": datetime.utcnow().isoformat(),
            "hit_count": 0
        }

        result = supabase_service.table(PDF_CACHE_TABLE).insert(record).execute()

        if result.data:
            # Store in memory (limited size - only recent PDFs)
            if len(_pdf_cache) < 50:  # Keep max 50 PDFs in memory (~100-250MB)
                _pdf_cache[cache_key] = pdf_bytes

            logger.info(f"[CACHE] ✅ Cached PDF: {cache_key} ({len(pdf_bytes)/1024:.1f}KB)")
            return True

        return False

    except Exception as e:
        logger.error(f"[CACHE] Failed to cache PDF: {str(e)}")
        return False


async def get_cached_pdf(report_json: Dict[str, Any]) -> Optional[bytes]:
    """Retrieve cached PDF if available"""
    try:
        cache_key = generate_pdf_cache_key(report_json)

        # Check in-memory
        if cache_key in _pdf_cache:
            logger.info(f"[CACHE] 🎯 In-memory PDF hit: {cache_key}")
            return _pdf_cache[cache_key]

        # For production: retrieve from Supabase Storage or file system
        # For now, we rely on in-memory cache

        return None

    except Exception as e:
        logger.error(f"[CACHE] Error retrieving PDF cache: {str(e)}")
        return None


# ============================================================================
# DASHBOARD STATS CACHING (SHORT TTL, HIGH FREQUENCY)
# ============================================================================

async def cache_dashboard_stats(stats: Dict[str, Any]) -> bool:
    """Cache dashboard statistics (short TTL - 5 minutes)"""
    try:
        cache_key = "dashboard:stats:latest"

        record = {
            "cache_key": cache_key,
            "stats_json": json.dumps(stats, ensure_ascii=False),
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=TTL_STATS)).isoformat()
        }

        # Upsert (update if exists, insert if not)
        supabase_service.table(STATS_CACHE_TABLE)\
            .upsert(record, on_conflict="cache_key")\
            .execute()

        _stats_cache[cache_key] = {
            "stats": stats,
            "cached_at": datetime.utcnow()
        }

        logger.info(f"[CACHE] ✅ Cached dashboard stats (TTL: {TTL_STATS*60:.0f}min)")
        return True

    except Exception as e:
        logger.error(f"[CACHE] Failed to cache stats: {str(e)}")
        return False


async def get_cached_dashboard_stats() -> Optional[Dict[str, Any]]:
    """Retrieve cached dashboard stats if fresh"""
    try:
        cache_key = "dashboard:stats:latest"

        # Check in-memory first
        if cache_key in _stats_cache:
            cached = _stats_cache[cache_key]
            age_seconds = (datetime.utcnow() - cached["cached_at"]).total_seconds()

            if age_seconds < TTL_STATS * 3600:
                logger.info(f"[CACHE] 🎯 In-memory stats hit (age: {age_seconds:.0f}s)")
                return cached["stats"]

        # Check database
        result = supabase_service.table(STATS_CACHE_TABLE)\
            .select("*")\
            .eq("cache_key", cache_key)\
            .gte("expires_at", datetime.utcnow().isoformat())\
            .limit(1)\
            .execute()

        if result.data and len(result.data) > 0:
            record = result.data[0]
            stats = json.loads(record["stats_json"])

            _stats_cache[cache_key] = {
                "stats": stats,
                "cached_at": datetime.utcnow()
            }

            logger.info(f"[CACHE] 🎯 Database stats hit")
            return stats

        return None

    except Exception as e:
        logger.error(f"[CACHE] Error retrieving stats cache: {str(e)}")
        return None


# ============================================================================
# CACHE STATISTICS & MANAGEMENT
# ============================================================================

async def get_cache_statistics() -> Dict[str, Any]:
    """Get comprehensive cache statistics"""
    try:
        stats = {}

        # Analysis cache stats
        analysis_result = supabase_service.table(ANALYSIS_CACHE_TABLE)\
            .select("cost_saved, hit_count", count="exact")\
            .execute()

        if analysis_result.data:
            total_cost_saved = sum(r.get("cost_saved", 0) * r.get("hit_count", 0) for r in analysis_result.data)
            stats["analysis_cache"] = {
                "total_records": len(analysis_result.data),
                "total_cost_saved": round(total_cost_saved, 2),
                "in_memory_size": len(_analysis_cache)
            }

        # Stage cache stats
        stage_result = supabase_service.table(STAGE_CACHE_TABLE)\
            .select("cost_saved, hit_count", count="exact")\
            .execute()

        if stage_result.data:
            total_stage_saved = sum(r.get("cost_saved", 0) * r.get("hit_count", 0) for r in stage_result.data)
            stats["stage_cache"] = {
                "total_records": len(stage_result.data),
                "total_cost_saved": round(total_stage_saved, 2),
                "in_memory_size": len(_stage_cache)
            }

        # PDF cache stats
        pdf_result = supabase_service.table(PDF_CACHE_TABLE)\
            .select("file_size_bytes, hit_count", count="exact")\
            .execute()

        if pdf_result.data:
            total_pdf_size = sum(r.get("file_size_bytes", 0) for r in pdf_result.data)
            stats["pdf_cache"] = {
                "total_records": len(pdf_result.data),
                "total_size_mb": round(total_pdf_size / 1024 / 1024, 2),
                "in_memory_size": len(_pdf_cache)
            }

        # Overall savings
        stats["total_cost_saved"] = round(
            stats.get("analysis_cache", {}).get("total_cost_saved", 0) +
            stats.get("stage_cache", {}).get("total_cost_saved", 0),
            2
        )

        return stats

    except Exception as e:
        logger.error(f"[CACHE] Error getting cache statistics: {str(e)}")
        return {}


async def clear_expired_cache() -> Dict[str, int]:
    """Clear expired cache entries from all tables"""
    try:
        cleared = {}

        # Clear expired analysis cache
        cutoff_analysis = (datetime.utcnow() - timedelta(hours=TTL_ANALYSIS)).isoformat()
        analysis_result = supabase_service.table(ANALYSIS_CACHE_TABLE)\
            .delete()\
            .lt("last_accessed_at", cutoff_analysis)\
            .execute()
        cleared["analysis"] = len(analysis_result.data) if analysis_result.data else 0

        # Clear expired stage cache
        cutoff_stage = (datetime.utcnow() - timedelta(hours=TTL_STAGE)).isoformat()
        stage_result = supabase_service.table(STAGE_CACHE_TABLE)\
            .delete()\
            .lt("last_accessed_at", cutoff_stage)\
            .execute()
        cleared["stages"] = len(stage_result.data) if stage_result.data else 0

        # Clear expired PDF cache
        cutoff_pdf = (datetime.utcnow() - timedelta(hours=TTL_PDF)).isoformat()
        pdf_result = supabase_service.table(PDF_CACHE_TABLE)\
            .delete()\
            .lt("last_accessed_at", cutoff_pdf)\
            .execute()
        cleared["pdfs"] = len(pdf_result.data) if pdf_result.data else 0

        # Clear expired stats cache
        stats_result = supabase_service.table(STATS_CACHE_TABLE)\
            .delete()\
            .lt("expires_at", datetime.utcnow().isoformat())\
            .execute()
        cleared["stats"] = len(stats_result.data) if stats_result.data else 0

        logger.info(f"[CACHE] 🧹 Cleared expired cache: {cleared}")
        return cleared

    except Exception as e:
        logger.error(f"[CACHE] Error clearing expired cache: {str(e)}")
        return {}
