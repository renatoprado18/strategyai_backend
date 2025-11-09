"""
Website and LinkedIn scraping functions for Apify.

This module provides scraping functionality for company websites,
LinkedIn company pages, and LinkedIn founder profiles.
"""
from typing import Dict, Any, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging
from apify_client import ApifyClientError
from app.core.exceptions import ApifyError
from app.services.data.apify_client import (
    get_apify_client,
    WEBSITE_SCRAPER_ACTOR,
    WEB_SEARCH_ACTOR,
    SCRAPER_TIMEOUT_SECONDS,
    RETRY_ATTEMPTS,
    RETRY_MIN_WAIT,
    RETRY_MAX_WAIT
)

logger = logging.getLogger(__name__)


@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def scrape_company_website(website_url: str) -> Dict[str, Any]:
    """
    Scrape company website to extract key information.

    Args:
        website_url: Company website URL

    Returns:
        Dictionary with scraped data including:
        - description: Company description/about text
        - services: List of products/services mentioned
        - tech_stack: Technologies detected
        - content_summary: Summary of main content
    """
    if not website_url or website_url.strip() == "":
        return {
            "error": "No website URL provided",
            "scraped_successfully": False
        }

    # Validate and clean URL
    url = website_url.strip()
    if not url.startswith('http'):
        url = f'https://{url}'

    print(f"[APIFY DEBUG] Scraping website: {url}")

    try:
        client = get_apify_client()

        # Run the website content crawler with validated URL
        run_input = {
            "startUrls": [{"url": url}],
            "maxCrawlDepth": 2,
            "maxCrawlPages": 5,
            "crawlerType": "cheerio",
        }

        run = client.actor(WEBSITE_SCRAPER_ACTOR).call(
            run_input=run_input,
            timeout_secs=SCRAPER_TIMEOUT_SECONDS
        )

        # Fetch results
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)

        if not results:
            return {"error": "No data scraped from website"}

        # Extract and structure key information
        website_data = {
            "url": website_url,
            "title": results[0].get("title", ""),
            "description": results[0].get("description", ""),
            "content_summary": " ".join([r.get("text", "")[:500] for r in results[:3]]),
            "links_count": len(results),
            "scraped_successfully": True
        }

        return website_data

    except ApifyClientError as e:
        logger.error(f"[APIFY ERROR] Apify API error scraping website {website_url}: {str(e)}", exc_info=True)
        return {
            "error": f"Apify API error: {str(e)}",
            "scraped_successfully": False
        }
    except (KeyError, ValueError) as e:
        logger.error(f"[APIFY ERROR] Invalid response format from website scraper: {str(e)}", exc_info=True)
        return {
            "error": f"Invalid API response: {str(e)}",
            "scraped_successfully": False
        }
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"[APIFY ERROR] Unexpected error scraping website: {str(e)}")
        return {
            "error": f"Failed to scrape website: {str(e)}",
            "scraped_successfully": False
        }


@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def scrape_linkedin_company(linkedin_url: Optional[str], company_name: str) -> Dict[str, Any]:
    """
    Extract information about company from LinkedIn or search results.

    Args:
        linkedin_url: LinkedIn company page URL (optional)
        company_name: Company name for fallback search

    Returns:
        Dictionary with LinkedIn company data
    """
    try:
        client = get_apify_client()

        # If LinkedIn URL provided, search for it; otherwise search for company
        if linkedin_url and linkedin_url.strip():
            search_query = f'site:linkedin.com/company {linkedin_url}'
        else:
            search_query = f'site:linkedin.com/company "{company_name}"'

        run_input = {
            "queries": search_query,
            "maxPagesPerQuery": 1,
            "resultsPerPage": 5,
            "countryCode": "br",
            "languageCode": "pt-BR"
        }

        run = client.actor(WEB_SEARCH_ACTOR).call(
            run_input=run_input,
            timeout_secs=SCRAPER_TIMEOUT_SECONDS
        )

        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)

        if not results:
            return {
                "error": "No LinkedIn company data found",
                "scraped_successfully": False
            }

        linkedin_data = {
            "linkedin_url": linkedin_url or results[0].get("url", ""),
            "company_description": results[0].get("description", ""),
            "insights": " ".join([r.get("description", "") for r in results[:3]]),
            "scraped_successfully": True
        }

        return linkedin_data

    except ApifyClientError as e:
        logger.error(f"[APIFY ERROR] Apify API error scraping LinkedIn company: {str(e)}", exc_info=True)
        return {
            "error": f"Apify API error: {str(e)}",
            "scraped_successfully": False
        }
    except (KeyError, ValueError) as e:
        logger.error(f"[APIFY ERROR] Invalid response format from LinkedIn company scraper: {str(e)}", exc_info=True)
        return {
            "error": f"Invalid API response: {str(e)}",
            "scraped_successfully": False
        }
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"[APIFY ERROR] Unexpected error scraping LinkedIn company: {str(e)}")
        return {
            "error": f"Failed to scrape LinkedIn company: {str(e)}",
            "scraped_successfully": False
        }


@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def scrape_linkedin_founder(linkedin_url: Optional[str], founder_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract information about founder/CEO from LinkedIn.

    Args:
        linkedin_url: LinkedIn founder profile URL (optional)
        founder_name: Founder name for fallback search (optional)

    Returns:
        Dictionary with LinkedIn founder data
    """
    if not linkedin_url and not founder_name:
        return {
            "error": "No founder LinkedIn URL or name provided",
            "scraped_successfully": False
        }

    try:
        client = get_apify_client()

        # Search for founder profile
        if linkedin_url and linkedin_url.strip():
            search_query = f'site:linkedin.com/in {linkedin_url}'
        else:
            search_query = f'site:linkedin.com/in "{founder_name}" CEO founder'

        run_input = {
            "queries": search_query,
            "maxPagesPerQuery": 1,
            "resultsPerPage": 5,
            "countryCode": "br",
            "languageCode": "pt-BR"
        }

        run = client.actor(WEB_SEARCH_ACTOR).call(
            run_input=run_input,
            timeout_secs=SCRAPER_TIMEOUT_SECONDS
        )

        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)

        if not results:
            return {
                "error": "No LinkedIn founder data found",
                "scraped_successfully": False
            }

        founder_data = {
            "linkedin_url": linkedin_url or results[0].get("url", ""),
            "profile_description": results[0].get("description", ""),
            "insights": " ".join([r.get("description", "") for r in results[:3]]),
            "scraped_successfully": True
        }

        return founder_data

    except ApifyClientError as e:
        logger.error(f"[APIFY ERROR] Apify API error scraping LinkedIn founder: {str(e)}", exc_info=True)
        return {
            "error": f"Apify API error: {str(e)}",
            "scraped_successfully": False
        }
    except (KeyError, ValueError) as e:
        logger.error(f"[APIFY ERROR] Invalid response format from LinkedIn founder scraper: {str(e)}", exc_info=True)
        return {
            "error": f"Invalid API response: {str(e)}",
            "scraped_successfully": False
        }
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"[APIFY ERROR] Unexpected error scraping LinkedIn founder: {str(e)}")
        return {
            "error": f"Failed to scrape LinkedIn founder: {str(e)}",
            "scraped_successfully": False
        }
