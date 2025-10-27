"""
Rate limiting using Upstash Redis with TTL-based tracking.
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from upstash_redis import Redis
from dotenv import load_dotenv

load_dotenv()

# Redis configuration
UPSTASH_REDIS_URL = os.getenv("UPSTASH_REDIS_URL")
UPSTASH_REDIS_TOKEN = os.getenv("UPSTASH_REDIS_TOKEN")
MAX_SUBMISSIONS_PER_IP = int(os.getenv("MAX_SUBMISSIONS_PER_IP_PER_DAY", "3"))
RATE_LIMIT_WINDOW_HOURS = 24

# Initialize Redis client
redis_client: Optional[Redis] = None

def get_redis_client() -> Redis:
    """
    Get or create Redis client instance.

    Returns:
        Redis client

    Raises:
        ValueError: If Redis credentials are missing
    """
    global redis_client

    if redis_client is None:
        if not UPSTASH_REDIS_URL or not UPSTASH_REDIS_TOKEN:
            raise ValueError(
                "UPSTASH_REDIS_URL and UPSTASH_REDIS_TOKEN environment variables are required"
            )

        redis_client = Redis(
            url=UPSTASH_REDIS_URL,
            token=UPSTASH_REDIS_TOKEN
        )

    return redis_client

async def check_rate_limit(ip_address: str) -> bool:
    """
    Check if IP address has exceeded rate limit.

    Args:
        ip_address: Client IP address

    Returns:
        True if within rate limit, False if exceeded

    Raises:
        HTTPException: If rate limit is exceeded
    """
    try:
        redis = get_redis_client()
        key = f"ratelimit:{ip_address}"

        # Get current count
        current_count = redis.get(key)

        if current_count is None:
            # First submission from this IP
            redis.set(key, 1, ex=RATE_LIMIT_WINDOW_HOURS * 3600)  # TTL in seconds
            return True

        # Convert to integer
        count = int(current_count)

        if count >= MAX_SUBMISSIONS_PER_IP:
            # Rate limit exceeded
            ttl = redis.ttl(key)
            hours_remaining = ttl // 3600 if ttl > 0 else 0
            minutes_remaining = (ttl % 3600) // 60 if ttl > 0 else 0

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. You can submit {MAX_SUBMISSIONS_PER_IP} forms per {RATE_LIMIT_WINDOW_HOURS} hours. "
                       f"Try again in {hours_remaining}h {minutes_remaining}m."
            )

        # Increment count
        redis.incr(key)
        return True

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log error but fail open (allow request) to prevent Redis issues from blocking service
        print(f"Rate limit check failed: {str(e)}. Allowing request (fail-open mode).")
        return True

async def reset_rate_limit(ip_address: str) -> bool:
    """
    Reset rate limit for a specific IP address (admin function).

    Args:
        ip_address: Client IP address to reset

    Returns:
        True if reset successful
    """
    try:
        redis = get_redis_client()
        key = f"ratelimit:{ip_address}"
        redis.delete(key)
        return True
    except Exception as e:
        print(f"Failed to reset rate limit for {ip_address}: {str(e)}")
        return False

async def get_rate_limit_status(ip_address: str) -> dict:
    """
    Get current rate limit status for an IP address.

    Args:
        ip_address: Client IP address

    Returns:
        Dictionary with rate limit info
    """
    try:
        redis = get_redis_client()
        key = f"ratelimit:{ip_address}"

        current_count = redis.get(key)
        count = int(current_count) if current_count else 0

        ttl = redis.ttl(key) if current_count else 0
        hours_remaining = ttl // 3600 if ttl > 0 else 0
        minutes_remaining = (ttl % 3600) // 60 if ttl > 0 else 0

        return {
            "ip_address": ip_address,
            "submissions_count": count,
            "max_submissions": MAX_SUBMISSIONS_PER_IP,
            "remaining_submissions": max(0, MAX_SUBMISSIONS_PER_IP - count),
            "reset_in_hours": hours_remaining,
            "reset_in_minutes": minutes_remaining,
            "is_limited": count >= MAX_SUBMISSIONS_PER_IP
        }
    except Exception as e:
        return {
            "ip_address": ip_address,
            "error": str(e)
        }
