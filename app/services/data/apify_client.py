"""
Apify client initialization, configuration, and base utilities.

This module provides the core Apify client setup and configuration
for all scraping operations.
"""
import os
from typing import Dict, Any
from apify_client import ApifyClient
from dotenv import load_dotenv
import logging

load_dotenv()

logger = logging.getLogger(__name__)

# Apify configuration
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# Actor IDs for different tasks (you'll need to configure these in .env)
WEBSITE_SCRAPER_ACTOR = os.getenv("APIFY_WEBSITE_SCRAPER_ACTOR", "apify/website-content-crawler")
WEB_SEARCH_ACTOR = os.getenv("APIFY_WEB_SEARCH_ACTOR", "apify/google-search-scraper")
COMPANY_ENRICHMENT_ACTOR = os.getenv("APIFY_COMPANY_ENRICHMENT_ACTOR", "apify/web-scraper")

# Timeout settings
SCRAPER_TIMEOUT_SECONDS = 30
ENRICHMENT_TIMEOUT_SECONDS = 45

# Retry configuration (exponential backoff: 2s, 4s, 8s)
RETRY_ATTEMPTS = 3
RETRY_MIN_WAIT = 2
RETRY_MAX_WAIT = 10


def get_apify_client() -> ApifyClient:
    """
    Get Apify client instance.

    Returns:
        Apify client

    Raises:
        ValueError: If API token is missing
    """
    if not APIFY_API_TOKEN:
        raise ValueError("APIFY_API_TOKEN environment variable is required")

    return ApifyClient(APIFY_API_TOKEN)
