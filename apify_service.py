"""
Apify integration for web scraping, competitor research, and data enrichment.
Includes intelligent caching via institutional_memory to reduce costs and improve speed.
"""
import os
from typing import Dict, Any, Optional, List
from apify_client import ApifyClient
from dotenv import load_dotenv
import asyncio
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging
from institutional_memory import store_memory, retrieve_memory

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

# Cache configuration
APIFY_CACHE_TTL_HOURS = 24 * 7  # 7 days cache for Apify data


# ============================================================================
# CACHING HELPERS
# ============================================================================

async def _cached_apify_call(
    cache_entity_type: str,
    cache_entity_id: str,
    apify_func,
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

    except Exception as e:
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
async def research_competitors(company: str, industry: str) -> Dict[str, Any]:
    """
    Research competitors in the same industry.

    Args:
        company: Company name
        industry: Industry sector

    Returns:
        Dictionary with competitor information
    """
    try:
        client = get_apify_client()

        # Search for competitors
        search_query = f"{industry} empresas Brasil competitors {company}"
        print(f"[APIFY] Searching competitors with query: {search_query}")

        run_input = {
            "queries": search_query,
            "maxPagesPerQuery": 3,
            "resultsPerPage": 10,
            "countryCode": "br",
            "languageCode": "pt-BR"
        }

        run = client.actor(WEB_SEARCH_ACTOR).call(
            run_input=run_input,
            timeout_secs=SCRAPER_TIMEOUT_SECONDS
        )

        # Fetch results
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)

        print(f"[APIFY] Competitor search found {len(results)} results")

        if not results:
            return {
                "error": "No competitor data found",
                "competitors_found": 0,
                "researched_successfully": False
            }

        # Structure competitor insights
        competitors_data = {
            "search_query": search_query,
            "competitors_found": len(results),
            "top_results": [
                {
                    "title": r.get("title", ""),
                    "description": r.get("description", ""),
                    "url": r.get("url", "")
                }
                for r in results[:5]
            ],
            "market_insights": " ".join([r.get("description", "") for r in results[:3]]),
            "researched_successfully": True
        }

        return competitors_data

    except Exception as e:
        print(f"[APIFY ERROR] Competitor research failed: {str(e)}")
        return {
            "error": f"Failed to research competitors: {str(e)}",
            "competitors_found": 0,
            "researched_successfully": False
        }


@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def research_industry_trends(industry: str) -> Dict[str, Any]:
    """
    Research current industry trends and news.

    Args:
        industry: Industry sector

    Returns:
        Dictionary with industry trends and insights
    """
    try:
        client = get_apify_client()

        # Search for industry trends
        search_queries = [
            f"{industry} tendências 2025 Brasil",
            f"{industry} inovação tecnologia Brasil",
            f"{industry} mercado perspectivas Brasil"
        ]

        all_results = []

        for query in search_queries:
            run_input = {
                "queries": query,
                "maxPagesPerQuery": 2,
                "resultsPerPage": 5,
                "countryCode": "br",
                "languageCode": "pt-BR"
            }

            run = client.actor(WEB_SEARCH_ACTOR).call(
                run_input=run_input,
                timeout_secs=SCRAPER_TIMEOUT_SECONDS
            )

            # Fetch results for this query
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                all_results.append(item)

        if not all_results:
            return {"error": "No industry trends found"}

        # Structure trends data
        trends_data = {
            "industry": industry,
            "trends_found": len(all_results),
            "key_insights": [
                {
                    "title": r.get("title", ""),
                    "description": r.get("description", ""),
                    "url": r.get("url", "")
                }
                for r in all_results[:10]
            ],
            "summary": " ".join([r.get("description", "") for r in all_results[:5]]),
            "researched_successfully": True
        }

        return trends_data

    except Exception as e:
        return {
            "error": f"Failed to research industry trends: {str(e)}",
            "researched_successfully": False
        }


@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def enrich_company_data(company: str, website: Optional[str] = None) -> Dict[str, Any]:
    """
    Enrich company data with additional information.

    Args:
        company: Company name
        website: Company website (optional)

    Returns:
        Dictionary with enriched company data
    """
    try:
        client = get_apify_client()

        # Search for company information
        search_query = f"{company} empresa Brasil informações"
        if website:
            search_query += f" site:{website}"

        run_input = {
            "queries": search_query,
            "maxPagesPerQuery": 2,
            "resultsPerPage": 10,
            "countryCode": "br",
            "languageCode": "pt-BR"
        }

        run = client.actor(WEB_SEARCH_ACTOR).call(
            run_input=run_input,
            timeout_secs=ENRICHMENT_TIMEOUT_SECONDS
        )

        # Fetch results
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)

        if not results:
            return {"error": "No enrichment data found"}

        # Structure enriched data
        enrichment_data = {
            "company": company,
            "enrichment_sources": len(results),
            "company_info": [
                {
                    "title": r.get("title", ""),
                    "description": r.get("description", ""),
                    "url": r.get("url", "")
                }
                for r in results[:5]
            ],
            "summary": " ".join([r.get("description", "") for r in results[:3]]),
            "enriched_successfully": True
        }

        return enrichment_data

    except Exception as e:
        return {
            "error": f"Failed to enrich company data: {str(e)}",
            "enriched_successfully": False
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

    except Exception as e:
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

    except Exception as e:
        return {
            "error": f"Failed to scrape LinkedIn founder: {str(e)}",
            "scraped_successfully": False
        }


@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def search_company_news(company: str, industry: str) -> Dict[str, Any]:
    """
    Search for recent news articles about the company.

    Args:
        company: Company name
        industry: Industry sector

    Returns:
        Dictionary with news articles and insights
    """
    try:
        client = get_apify_client()

        # Search for recent news
        search_queries = [
            f'"{company}" notícias 2024 2025',
            f'"{company}" {industry} Brasil news',
        ]

        all_results = []

        for query in search_queries:
            run_input = {
                "queries": [query],
                "maxPagesPerQuery": 2,
                "resultsPerPage": 10,
                "countryCode": "br",
                "languageCode": "pt-BR"
            }

            run = client.actor(WEB_SEARCH_ACTOR).call(
                run_input=run_input,
                timeout_secs=SCRAPER_TIMEOUT_SECONDS
            )

            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                all_results.append(item)

        if not all_results:
            return {
                "error": "No news articles found",
                "researched_successfully": False
            }

        news_data = {
            "company": company,
            "articles_found": len(all_results),
            "recent_news": [
                {
                    "title": r.get("title", ""),
                    "description": r.get("description", ""),
                    "url": r.get("url", "")
                }
                for r in all_results[:10]
            ],
            "news_summary": " ".join([r.get("description", "") for r in all_results[:5]]),
            "researched_successfully": True
        }

        return news_data

    except Exception as e:
        return {
            "error": f"Failed to search company news: {str(e)}",
            "researched_successfully": False
        }


@retry(
    stop=stop_after_attempt(RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=RETRY_MIN_WAIT, max=RETRY_MAX_WAIT),
    retry=retry_if_exception_type(Exception),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True
)
async def search_social_media_presence(company: str, website: Optional[str] = None) -> Dict[str, Any]:
    """
    Search for company's social media presence and public mentions.

    Args:
        company: Company name
        website: Company website for validation (optional)

    Returns:
        Dictionary with social media presence data
    """
    try:
        client = get_apify_client()

        # Search for social media profiles
        search_queries = [
            f'"{company}" Instagram Facebook Twitter social media',
            f'"{company}" avaliações reviews clientes',
        ]

        if website:
            search_queries.append(f'site:instagram.com OR site:facebook.com OR site:twitter.com "{company}"')

        all_results = []

        for query in search_queries:
            run_input = {
                "queries": [query],
                "maxPagesPerQuery": 2,
                "resultsPerPage": 10,
                "countryCode": "br",
                "languageCode": "pt-BR"
            }

            run = client.actor(WEB_SEARCH_ACTOR).call(
                run_input=run_input,
                timeout_secs=SCRAPER_TIMEOUT_SECONDS
            )

            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                all_results.append(item)

        if not all_results:
            return {
                "error": "No social media presence found",
                "researched_successfully": False
            }

        social_data = {
            "company": company,
            "mentions_found": len(all_results),
            "social_profiles": [
                {
                    "title": r.get("title", ""),
                    "description": r.get("description", ""),
                    "url": r.get("url", "")
                }
                for r in all_results[:10]
            ],
            "public_sentiment": " ".join([r.get("description", "") for r in all_results[:5]]),
            "researched_successfully": True
        }

        return social_data

    except Exception as e:
        return {
            "error": f"Failed to search social media: {str(e)}",
            "researched_successfully": False
        }

async def gather_all_apify_data(
    company: str,
    industry: str,
    website: Optional[str] = None,
    linkedin_company: Optional[str] = None,
    linkedin_founder: Optional[str] = None,
    challenge: Optional[str] = None
) -> Dict[str, Any]:
    """
    Gather all Apify data in parallel for comprehensive analysis.
    Now includes LinkedIn profiles, news, and social media data.

    Args:
        company: Company name
        industry: Industry sector
        website: Company website URL (optional)
        linkedin_company: LinkedIn company page URL (optional)
        linkedin_founder: LinkedIn founder profile URL (optional)
        challenge: Business challenge (optional)

    Returns:
        Dictionary with all gathered data
    """
    print(f"[APIFY] gather_all_apify_data called with website={website}, linkedin_company={linkedin_company}, linkedin_founder={linkedin_founder}")

    # Run all Apify tasks in parallel with caching
    tasks = []

    # Website scraping (if URL provided) - CACHED
    if website and website.strip():
        print(f"[APIFY] Adding website scraping task for: {website}")
        tasks.append(("website_data", _cached_apify_call(
            "apify_website",
            website.lower().strip(),
            scrape_company_website,
            website
        )))
    else:
        print(f"[APIFY] No website provided, skipping website scraping")

    # Core data gathering (always run) - ALL CACHED
    tasks.append(("competitor_data", _cached_apify_call(
        "apify_competitors",
        f"{company}:{industry}".lower(),
        research_competitors,
        company,
        industry
    )))

    tasks.append(("industry_trends", _cached_apify_call(
        "apify_trends",
        industry.lower(),
        research_industry_trends,
        industry
    )))

    tasks.append(("company_enrichment", _cached_apify_call(
        "apify_enrichment",
        company.lower(),
        enrich_company_data,
        company,
        website
    )))

    # NEW: LinkedIn data gathering - CACHED
    if linkedin_company or True:  # Always try to find LinkedIn company
        print(f"[APIFY] Adding LinkedIn company scraping task")
        linkedin_id = linkedin_company.lower() if linkedin_company else company.lower()
        tasks.append(("linkedin_company_data", _cached_apify_call(
            "apify_linkedin_company",
            linkedin_id,
            scrape_linkedin_company,
            linkedin_company,
            company
        )))

    if linkedin_founder:
        print(f"[APIFY] Adding LinkedIn founder scraping task")
        tasks.append(("linkedin_founder_data", _cached_apify_call(
            "apify_linkedin_founder",
            linkedin_founder.lower(),
            scrape_linkedin_founder,
            linkedin_founder
        )))

    # NEW: Public data gathering (news and social media) - CACHED
    print(f"[APIFY] Adding news and social media scraping tasks")
    tasks.append(("news_data", _cached_apify_call(
        "apify_news",
        f"{company}:{industry}".lower(),
        search_company_news,
        company,
        industry
    )))

    tasks.append(("social_media_data", _cached_apify_call(
        "apify_social",
        company.lower(),
        search_social_media_presence,
        company,
        website
    )))

    # Execute all tasks concurrently
    results = {}
    task_dict = dict(tasks)

    try:
        # Run with extended timeout for more data sources
        gathered = await asyncio.wait_for(
            asyncio.gather(*task_dict.values(), return_exceptions=True),
            timeout=120  # 120 second overall timeout (extended for more sources)
        )

        # Map results back to keys
        for (key, _), result in zip(tasks, gathered):
            if isinstance(result, Exception):
                results[key] = {"error": str(result)}
            else:
                results[key] = result

    except asyncio.TimeoutError:
        results["error"] = "Apify data gathering timed out"

    # Add metadata
    results["apify_enabled"] = True
    results["timestamp"] = asyncio.get_event_loop().time()

    return results
