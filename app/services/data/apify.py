"""
Apify integration for web scraping, competitor research, and data enrichment.
Includes intelligent caching via institutional_memory to reduce costs and improve speed.

This module serves as a compatibility wrapper that re-exports all functions
from the modularized apify submodules for backward compatibility.
"""

# Re-export client configuration and utilities
from app.services.data.apify_client import (
    get_apify_client,
    APIFY_API_TOKEN,
    WEBSITE_SCRAPER_ACTOR,
    WEB_SEARCH_ACTOR,
    COMPANY_ENRICHMENT_ACTOR,
    SCRAPER_TIMEOUT_SECONDS,
    ENRICHMENT_TIMEOUT_SECONDS,
    RETRY_ATTEMPTS,
    RETRY_MIN_WAIT,
    RETRY_MAX_WAIT,
)

# Re-export cache functionality
from app.services.data.apify_cache import (
    _cached_apify_call,
    APIFY_CACHE_TTL_HOURS,
)

# Re-export scraper functions
from app.services.data.apify_scrapers import (
    scrape_company_website,
    scrape_linkedin_company,
    scrape_linkedin_founder,
)

# Re-export research functions
from app.services.data.apify_research import (
    research_competitors,
    research_industry_trends,
    enrich_company_data,
    search_company_news,
    search_social_media_presence,
    gather_all_apify_data,
)

__all__ = [
    # Client
    'get_apify_client',
    'APIFY_API_TOKEN',
    'WEBSITE_SCRAPER_ACTOR',
    'WEB_SEARCH_ACTOR',
    'COMPANY_ENRICHMENT_ACTOR',
    'SCRAPER_TIMEOUT_SECONDS',
    'ENRICHMENT_TIMEOUT_SECONDS',
    'RETRY_ATTEMPTS',
    'RETRY_MIN_WAIT',
    'RETRY_MAX_WAIT',
    # Cache
    '_cached_apify_call',
    'APIFY_CACHE_TTL_HOURS',
    # Scrapers
    'scrape_company_website',
    'scrape_linkedin_company',
    'scrape_linkedin_founder',
    # Research
    'research_competitors',
    'research_industry_trends',
    'enrich_company_data',
    'search_company_news',
    'search_social_media_presence',
    'gather_all_apify_data',
]
