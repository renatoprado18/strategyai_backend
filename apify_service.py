"""
Apify integration for web scraping, competitor research, and data enrichment.
"""
import os
from typing import Dict, Any, Optional, List
from apify_client import ApifyClient
from dotenv import load_dotenv
import asyncio

load_dotenv()

# Apify configuration
APIFY_API_TOKEN = os.getenv("APIFY_API_TOKEN")

# Actor IDs for different tasks (you'll need to configure these in .env)
WEBSITE_SCRAPER_ACTOR = os.getenv("APIFY_WEBSITE_SCRAPER_ACTOR", "apify/website-content-crawler")
WEB_SEARCH_ACTOR = os.getenv("APIFY_WEB_SEARCH_ACTOR", "apify/google-search-scraper")
COMPANY_ENRICHMENT_ACTOR = os.getenv("APIFY_COMPANY_ENRICHMENT_ACTOR", "apify/web-scraper")

# Timeout settings
SCRAPER_TIMEOUT_SECONDS = 30
ENRICHMENT_TIMEOUT_SECONDS = 45

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
    if not website_url:
        return {"error": "No website URL provided"}

    try:
        client = get_apify_client()

        # Run the website content crawler
        run_input = {
            "startUrls": [{"url": website_url}],
            "maxCrawlDepth": 2,
            "maxCrawlPages": 5,
            "crawler": "cheerio",
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

        run_input = {
            "queries": [search_query],
            "maxPagesPerQuery": 3,
            "resultsPerPage": 10,
            "countryCode": "br",
            "languageCode": "pt"
        }

        run = client.actor(WEB_SEARCH_ACTOR).call(
            run_input=run_input,
            timeout_secs=SCRAPER_TIMEOUT_SECONDS
        )

        # Fetch results
        results = []
        for item in client.dataset(run["defaultDatasetId"]).iterate_items():
            results.append(item)

        if not results:
            return {"error": "No competitor data found"}

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
        return {
            "error": f"Failed to research competitors: {str(e)}",
            "researched_successfully": False
        }

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
                "queries": [query],
                "maxPagesPerQuery": 2,
                "resultsPerPage": 5,
                "countryCode": "br",
                "languageCode": "pt"
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
            "queries": [search_query],
            "maxPagesPerQuery": 2,
            "resultsPerPage": 10,
            "countryCode": "br",
            "languageCode": "pt"
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

async def gather_all_apify_data(
    company: str,
    industry: str,
    website: Optional[str] = None,
    challenge: Optional[str] = None
) -> Dict[str, Any]:
    """
    Gather all Apify data in parallel for comprehensive analysis.

    Args:
        company: Company name
        industry: Industry sector
        website: Company website URL (optional)
        challenge: Business challenge (optional)

    Returns:
        Dictionary with all gathered data
    """
    # Run all Apify tasks in parallel
    tasks = []

    # Website scraping (if URL provided)
    if website:
        tasks.append(("website_data", scrape_company_website(website)))

    # Always run these
    tasks.append(("competitor_data", research_competitors(company, industry)))
    tasks.append(("industry_trends", research_industry_trends(industry)))
    tasks.append(("company_enrichment", enrich_company_data(company, website)))

    # Execute all tasks concurrently
    results = {}
    task_dict = dict(tasks)

    try:
        # Run with overall timeout
        gathered = await asyncio.wait_for(
            asyncio.gather(*task_dict.values(), return_exceptions=True),
            timeout=90  # 90 second overall timeout
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
