"""
Proxycurl LinkedIn Company Data Source for IMENSIAH Enrichment

Queries Proxycurl API for LinkedIn company profile data.

Provides:
- LinkedIn company URL
- Follower count
- Company description
- Specialties and focus areas
- Employee count on LinkedIn
- Company updates

This is a PAID source (~$0.03 per call).
Used in DEEP enrichment phase.

Created: 2025-01-09
Version: 1.0.0
"""

import time
import logging
from typing import Optional
import httpx
from .base import EnrichmentSource, SourceResult
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ProxycurlSource(EnrichmentSource):
    """
    Extract LinkedIn company data via Proxycurl.

    Uses Proxycurl Company API (paid, requires API key).

    Capabilities:
    - LinkedIn company profile URL
    - Follower count and engagement
    - Company description (LinkedIn about)
    - Specialties and industry tags
    - Employee count (LinkedIn data)
    - Company size and type

    Performance: ~3-5 seconds
    Cost: ~$0.03 per successful lookup
    Rate Limit: Depends on plan

    Usage:
        source = ProxycurlSource()
        result = await source.enrich(
            "techstart.com",
            linkedin_url="https://linkedin.com/company/techstart"
        )
        print(result.data)
        # {
        #     "linkedin_url": "https://linkedin.com/company/techstart",
        #     "linkedin_followers": 1247,
        #     "linkedin_description": "We help...",
        #     "specialties": ["SaaS", "Automation"]
        # }
    """

    COMPANY_URL_ENDPOINT = "https://nubela.co/proxycurl/api/linkedin/company"
    COMPANY_SEARCH_ENDPOINT = (
        "https://nubela.co/proxycurl/api/linkedin/company/resolve"
    )

    def __init__(self):
        """Initialize Proxycurl source (paid, ~$0.03/call)"""
        super().__init__(name="proxycurl", cost_per_call=0.03)
        self.timeout = 15.0  # 15 second timeout (can be slow)
        self.api_key = getattr(settings, "proxycurl_api_key", None)

        if not self.api_key:
            logger.warning(
                "Proxycurl API key not configured - enrichment will fail"
            )

    async def enrich(self, domain: str, **kwargs) -> SourceResult:
        """
        Get LinkedIn company data via Proxycurl.

        Args:
            domain: Company domain
            **kwargs: Optional parameters
                - linkedin_url: Direct LinkedIn company URL (preferred)
                - company_name: Search by name if no URL provided

        Returns:
            SourceResult with LinkedIn data
        """
        start_time = time.time()

        try:
            # Gracefully handle missing API key (return empty result)
            if not self.api_key:
                logger.info("Proxycurl API key not configured - skipping")
                return SourceResult(
                    source_name=self.name,
                    success=False,
                    data={},
                    cost_usd=0.0,
                    duration_ms=0,
                    error_message="Proxycurl API key not configured"
                )

            linkedin_url = kwargs.get("linkedin_url")
            company_name = kwargs.get("company_name")

            # If no LinkedIn URL, try to resolve from domain or company name
            if not linkedin_url:
                linkedin_url = await self._resolve_linkedin_url(
                    domain, company_name
                )
                if not linkedin_url:
                    raise Exception(
                        f"Could not find LinkedIn profile for domain: {domain}"
                    )

            # Fetch company data
            company_data = await self._get_company_data(linkedin_url)

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Proxycurl enriched LinkedIn profile: "
                f"{company_data.get('company_name', 'Unknown')} in {duration_ms}ms",
                extra={
                    "domain": domain,
                    "linkedin_url": linkedin_url,
                    "followers": company_data.get("linkedin_followers"),
                },
            )

            return SourceResult(
                source_name=self.name,
                success=True,
                data=company_data,
                duration_ms=duration_ms,
                cost_usd=self.cost_per_call,
            )

        except httpx.TimeoutException:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"Timeout querying Proxycurl after {duration_ms}ms"
            )
            raise Exception(f"Request timeout after {self.timeout}s")

        except httpx.HTTPStatusError as e:
            duration_ms = int((time.time() - start_time) * 1000)

            if e.response.status_code == 404:
                logger.info(
                    f"LinkedIn profile not found: {linkedin_url}",
                    extra={"linkedin_url": linkedin_url, "status": 404},
                )
            elif e.response.status_code == 429:
                logger.error(
                    "Proxycurl rate limit exceeded",
                    extra={"status": 429},
                )
            else:
                logger.warning(
                    f"HTTP error {e.response.status_code} from Proxycurl"
                )

            raise

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Error querying Proxycurl: {e}",
                exc_info=True,
            )
            raise

    async def _resolve_linkedin_url(
        self, domain: str, company_name: Optional[str] = None
    ) -> Optional[str]:
        """
        Resolve LinkedIn company URL from domain or company name.

        Args:
            domain: Company domain
            company_name: Company name (optional, for better matching)

        Returns:
            LinkedIn company URL or None if not found
        """
        try:
            # Clean domain
            clean_domain = (
                domain.replace("https://", "")
                .replace("http://", "")
                .replace("www.", "")
                .split("/")[0]
            )

            # Use Proxycurl's resolve endpoint
            headers = {"Authorization": f"Bearer {self.api_key}"}
            params = {}

            # Prefer company domain lookup
            if clean_domain:
                params["company_domain"] = clean_domain

            # Fallback to name search if provided
            if not params and company_name:
                params["company_name"] = company_name

            if not params:
                return None

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.COMPANY_SEARCH_ENDPOINT,
                    headers=headers,
                    params=params,
                )

                # 404 means not found - not an error
                if response.status_code == 404:
                    logger.debug(
                        f"No LinkedIn profile found for domain: {clean_domain}"
                    )
                    return None

                response.raise_for_status()
                data = response.json()

            linkedin_url = data.get("url")

            if linkedin_url:
                logger.debug(
                    f"Resolved LinkedIn URL for {clean_domain}: {linkedin_url}",
                    extra={"domain": clean_domain, "linkedin_url": linkedin_url},
                )

            return linkedin_url

        except Exception as e:
            logger.error(
                f"Error resolving LinkedIn URL for {domain}: {e}",
                exc_info=True,
            )
            return None

    async def _get_company_data(self, linkedin_url: str) -> dict:
        """
        Fetch company data from LinkedIn URL.

        Args:
            linkedin_url: LinkedIn company profile URL

        Returns:
            Dict with LinkedIn company data
        """
        headers = {"Authorization": f"Bearer {self.api_key}"}
        params = {"url": linkedin_url}

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.COMPANY_URL_ENDPOINT,
                headers=headers,
                params=params,
            )
            response.raise_for_status()
            data = response.json()

        # Extract and normalize data
        enriched_data = {}

        if data.get("name"):
            enriched_data["company_name"] = data["name"]

        if data.get("description"):
            enriched_data["linkedin_description"] = data["description"]

        if data.get("follower_count"):
            enriched_data["linkedin_followers"] = data["follower_count"]

        if data.get("linkedin_internal_id"):
            enriched_data["linkedin_id"] = data["linkedin_internal_id"]

        # LinkedIn URL (canonical)
        if linkedin_url:
            enriched_data["linkedin_url"] = linkedin_url

        # Company size
        if data.get("company_size"):
            enriched_data["employee_count_linkedin"] = data["company_size"]

        if data.get("company_type"):
            enriched_data["company_type"] = data["company_type"]

        # Industry and specialties
        if data.get("industry"):
            enriched_data["industry"] = data["industry"]

        if data.get("specialities"):
            # Proxycurl returns comma-separated string
            specialties = [
                s.strip() for s in data["specialities"].split(",") if s.strip()
            ]
            enriched_data["specialties"] = specialties[:10]  # Limit to 10

        # Location
        if data.get("locations"):
            # Get headquarter location
            hq_locations = [
                loc
                for loc in data["locations"]
                if loc.get("is_hq", False)
            ]
            if hq_locations:
                hq = hq_locations[0]
                location_parts = []

                if hq.get("city"):
                    location_parts.append(hq["city"])
                if hq.get("state"):
                    location_parts.append(hq["state"])
                if hq.get("country"):
                    location_parts.append(hq["country"])

                if location_parts:
                    enriched_data["location"] = ", ".join(location_parts)

        # Founded year
        if data.get("founded_year"):
            enriched_data["founded_year"] = data["founded_year"]

        # Website
        if data.get("website"):
            enriched_data["website"] = data["website"]

        # Logo
        if data.get("logo_url"):
            enriched_data["logo_url"] = data["logo_url"]

        # Remove None values
        enriched_data = {
            k: v for k, v in enriched_data.items() if v is not None
        }

        return enriched_data
