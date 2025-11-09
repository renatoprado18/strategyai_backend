"""
Centralized Configuration Management
Type-safe, validated settings using Pydantic
"""
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
from functools import lru_cache
from typing import List
import os


class Settings(BaseSettings):
    """
    Application settings with validation and type safety
    All environment variables are loaded and validated at startup
    """

    # ============================================================================
    # ENVIRONMENT
    # ============================================================================
    environment: str = Field(default="production", description="Environment: development, staging, production")

    # ============================================================================
    # API CONFIGURATION
    # ============================================================================
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:3001",
        description="Comma-separated list of allowed CORS origins"
    )

    @field_validator("allowed_origins")
    @classmethod
    def parse_origins(cls, v: str) -> List[str]:
        """Parse comma-separated origins into list"""
        return [origin.strip() for origin in v.split(",") if origin.strip()]

    # ============================================================================
    # DATABASE (SUPABASE)
    # ============================================================================
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_service_key: str = Field(..., description="Supabase service role key (admin)")
    supabase_anon_key: str = Field(..., description="Supabase anon/public key")
    database_url: str = Field(default="", description="Direct PostgreSQL connection URL (optional)")

    # ============================================================================
    # AUTHENTICATION & SECURITY
    # ============================================================================
    jwt_secret: str = Field(..., description="Secret key for JWT signing")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_expiration_minutes: int = Field(default=10080, description="JWT expiration (default: 7 days)")

    # ============================================================================
    # AI SERVICES
    # ============================================================================
    openrouter_api_key: str = Field(default="", description="OpenRouter API key for GPT-4o-mini (progressive enrichment)")
    perplexity_api_key: str = Field(default="", description="Perplexity API key for market research")

    # ============================================================================
    # DATA COLLECTION
    # ============================================================================
    apify_api_token: str = Field(default="", description="Apify API token for web scraping")

    # ============================================================================
    # DATA ENRICHMENT (IMENSIAH)
    # ============================================================================
    clearbit_api_key: str = Field(default="", description="Clearbit API key for company enrichment ($0.10/call)")
    google_places_api_key: str = Field(default="", description="Google Places API key for location data ($0.02/call)")
    proxycurl_api_key: str = Field(default="", description="Proxycurl API key for LinkedIn data ($0.03/call)")

    # ============================================================================
    # CACHING & RATE LIMITING (UPSTASH REDIS)
    # ============================================================================
    upstash_redis_url: str = Field(..., description="Upstash Redis REST URL")
    upstash_redis_token: str = Field(..., description="Upstash Redis REST token")

    # ============================================================================
    # RATE LIMITING
    # ============================================================================
    max_submissions_per_ip_per_day: int = Field(
        default=3,
        description="Maximum submissions per IP address per day"
    )
    rate_limit_ttl_seconds: int = Field(
        default=86400,
        description="Rate limit TTL in seconds (default: 24 hours)"
    )

    # ============================================================================
    # CACHE TTL SETTINGS
    # ============================================================================
    cache_ttl_dashboard: int = Field(default=300, description="Dashboard cache TTL (5 minutes)")
    cache_ttl_reports: int = Field(default=1800, description="Reports cache TTL (30 minutes)")
    cache_ttl_enrichment: int = Field(default=86400, description="Enrichment cache TTL (24 hours)")

    # ============================================================================
    # MONITORING & ERROR TRACKING
    # ============================================================================
    sentry_dsn: str = Field(default="", description="Sentry DSN for error tracking (optional)")

    # ============================================================================
    # ANALYSIS CONFIGURATION
    # ============================================================================
    analysis_timeout_seconds: int = Field(default=300, description="Max analysis time (5 minutes)")
    max_concurrent_analyses: int = Field(default=10, description="Max concurrent analysis tasks")

    # ============================================================================
    # MODEL CONFIGURATION
    # ============================================================================
    default_model: str = Field(
        default="google/gemini-2.0-flash-exp:free",
        description="Default LLM model for analysis"
    )
    fallback_model: str = Field(
        default="openai/gpt-4o-mini",
        description="Fallback model if primary fails"
    )

    # ============================================================================
    # PYDANTIC CONFIG
    # ============================================================================
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Ignore extra env vars


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance (singleton pattern)

    Returns:
        Settings: Validated application settings

    Raises:
        ValidationError: If required environment variables are missing
    """
    return Settings()


# Convenience function for backwards compatibility
def get_env(key: str, default: str = "") -> str:
    """
    Get environment variable (backwards compatibility helper)

    Args:
        key: Environment variable name
        default: Default value if not found

    Returns:
        str: Environment variable value
    """
    return os.getenv(key, default)


# ============================================================================
# NOTE ON SETTINGS INITIALIZATION
# ============================================================================
# Settings are loaded lazily via get_settings() (cached with @lru_cache)
# This allows the module to be imported without requiring .env file
# Settings validation happens when get_settings() is first called
#
# For convenience, you can use either:
# - settings = get_settings()  # Recommended: explicit and clear
# - from app.core.config import get_settings; settings = get_settings()
# ============================================================================
