"""
Supabase client initialization and configuration.
"""
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Don't fail on import if missing - let individual operations fail gracefully
# This allows FastAPI routes to still register even if Supabase isn't configured
import logging
logger = logging.getLogger(__name__)

if not SUPABASE_URL:
    logger.warning("[SUPABASE] SUPABASE_URL not configured - Supabase features will be disabled")

def get_supabase_client(use_service_key: bool = False) -> Client:
    """
    Get Supabase client instance.

    Args:
        use_service_key: If True, uses service key (bypasses RLS).
                        If False, uses anon key (respects RLS).

    Returns:
        Supabase client instance

    Raises:
        ValueError: If Supabase is not configured
    """
    if not SUPABASE_URL:
        raise ValueError("SUPABASE_URL not configured - Supabase features disabled")

    key = SUPABASE_SERVICE_KEY if use_service_key else SUPABASE_ANON_KEY

    if not key:
        key_type = "SUPABASE_SERVICE_KEY" if use_service_key else "SUPABASE_ANON_KEY"
        raise ValueError(f"{key_type} environment variable is required")

    return create_client(SUPABASE_URL, key)

# Global client instances - initialize as None if Supabase not configured
supabase_service = None
supabase_anon = None

try:
    supabase_service = get_supabase_client(use_service_key=True)  # For admin operations
    supabase_anon = get_supabase_client(use_service_key=False)     # For public operations
    logger.info("[SUPABASE] ✅ Supabase client initialized successfully")
except ValueError as e:
    logger.warning(f"[SUPABASE] ⚠️ Supabase not initialized: {e}")
