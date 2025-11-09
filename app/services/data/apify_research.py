"""
Market research and analysis functions for Apify.

This module provides research functionality for competitors, industry trends,
company enrichment, news search, and social media presence.
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
import asyncio
# Note: ApifyClientError removed in apify-client 2.2.1, using generic Exception
from app.core.exceptions import ApifyError
from app.services.data.apify_client import (
    get_apify_client,
    WEB_SEARCH_ACTOR,
    SCRAPER_TIMEOUT_SECONDS,
    ENRICHMENT_TIMEOUT_SECONDS,
    RETRY_ATTEMPTS,
    RETRY_MIN_WAIT,
    RETRY_MAX_WAIT
)
from app.services.data.apify_cache import _cached_apify_call
from app.services.data.apify_scrapers import (
    scrape_company_website,
    scrape_linkedin_company,
    scrape_linkedin_founder
)

logger = logging.getLogger(__name__)


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
        logger.error(f"[APIFY ERROR] Apify API error in competitor research: {str(e)}", exc_info=True)
        return {
            "error": f"Apify API error: {str(e)}",
            "competitors_found": 0,
            "researched_successfully": False
        }
    except (KeyError, ValueError) as e:
        logger.error(f"[APIFY ERROR] Invalid response format in competitor research: {str(e)}", exc_info=True)
        return {
            "error": f"Invalid API response: {str(e)}",
            "competitors_found": 0,
            "researched_successfully": False
        }
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"[APIFY ERROR] Unexpected error in competitor research: {str(e)}")
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
        logger.error(f"[APIFY ERROR] Apify API error in industry trends: {str(e)}", exc_info=True)
        return {
            "error": f"Apify API error: {str(e)}",
            "researched_successfully": False
        }
    except (KeyError, ValueError) as e:
        logger.error(f"[APIFY ERROR] Invalid response format in industry trends: {str(e)}", exc_info=True)
        return {
            "error": f"Invalid API response: {str(e)}",
            "researched_successfully": False
        }
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"[APIFY ERROR] Unexpected error in industry trends: {str(e)}")
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
        logger.error(f"[APIFY ERROR] Apify API error in company enrichment: {str(e)}", exc_info=True)
        return {
            "error": f"Apify API error: {str(e)}",
            "enriched_successfully": False
        }
    except (KeyError, ValueError) as e:
        logger.error(f"[APIFY ERROR] Invalid response format in company enrichment: {str(e)}", exc_info=True)
        return {
            "error": f"Invalid API response: {str(e)}",
            "enriched_successfully": False
        }
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"[APIFY ERROR] Unexpected error in company enrichment: {str(e)}")
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
        logger.error(f"[APIFY ERROR] Apify API error in company news search: {str(e)}", exc_info=True)
        return {
            "error": f"Apify API error: {str(e)}",
            "researched_successfully": False
        }
    except (KeyError, ValueError) as e:
        logger.error(f"[APIFY ERROR] Invalid response format in company news: {str(e)}", exc_info=True)
        return {
            "error": f"Invalid API response: {str(e)}",
            "researched_successfully": False
        }
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"[APIFY ERROR] Unexpected error in company news search: {str(e)}")
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
        logger.error(f"[APIFY ERROR] Apify API error in social media search: {str(e)}", exc_info=True)
        return {
            "error": f"Apify API error: {str(e)}",
            "researched_successfully": False
        }
    except (KeyError, ValueError) as e:
        logger.error(f"[APIFY ERROR] Invalid response format in social media search: {str(e)}", exc_info=True)
        return {
            "error": f"Invalid API response: {str(e)}",
            "researched_successfully": False
        }
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"[APIFY ERROR] Unexpected error in social media search: {str(e)}")
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
