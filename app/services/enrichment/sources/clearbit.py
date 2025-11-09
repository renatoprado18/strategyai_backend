"""
Clearbit Company Enrichment Source for IMENSIAH

Queries Clearbit Company API for comprehensive business intelligence.

Provides:
- Legal company name
- Employee count range
- Industry and category
- Founded year
- Company type (public/private)
- Annual revenue estimate
- Tech stack
- Social media profiles

This is a PAID source (~$0.10 per call).
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


class ClearbitSource(EnrichmentSource):
    """
    Extract comprehensive company data from Clearbit.

    Uses Clearbit Company API (paid, requires API key).

    Capabilities:
    - Company name and description
    - Employee count and revenue estimates
    - Industry classification
    - Founded year and location
    - Logo and social media
    - Technology stack

    Performance: ~1-2 seconds
    Cost: ~$0.10 per successful lookup
    Rate Limit: Depends on plan (usually generous)

    Usage:
        source = ClearbitSource()
        result = await source.enrich("techstart.com")
        print(result.data)
        # {
        #     "company_name": "TechStart",
        #     "employee_count": "25-50",
        #     "industry": "Technology",
        #     "founded_year": 2019
        # }
    """

    API_URL = "https://company.clearbit.com/v2/companies/find"

    def __init__(self):
        """Initialize Clearbit source (paid, ~$0.10/call)"""
        super().__init__(name="clearbit", cost_per_call=0.10)
        self.timeout = 10.0  # 10 second timeout
        self.api_key = getattr(settings, "clearbit_api_key", None)

        if not self.api_key:
            logger.warning(
                "Clearbit API key not configured - enrichment will fail"
            )

    async def enrich(self, domain: str, **kwargs) -> SourceResult:
        """
        Get company data from Clearbit.

        Args:
            domain: Domain to enrich (e.g., "techstart.com")
            **kwargs: Additional parameters (unused)

        Returns:
            SourceResult with company data
        """
        start_time = time.time()

        try:
            if not self.api_key:
                raise Exception("Clearbit API key not configured")

            # Clean domain
            clean_domain = (
                domain.replace("https://", "")
                .replace("http://", "")
                .replace("www.", "")
                .split("/")[0]
            )

            # Query Clearbit API
            headers = {"Authorization": f"Bearer {self.api_key}"}
            params = {"domain": clean_domain}

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    self.API_URL, headers=headers, params=params
                )

                # Handle 404 (company not found)
                if response.status_code == 404:
                    raise Exception(
                        f"Company not found in Clearbit: {clean_domain}"
                    )

                # Handle 402 (payment required / credits exhausted)
                if response.status_code == 402:
                    raise Exception(
                        "Clearbit credits exhausted - payment required"
                    )

                response.raise_for_status()
                data = response.json()

            # Extract and normalize data
            enriched_data = {}

            # Basic info
            if data.get("name"):
                enriched_data["company_name"] = data["name"]

            if data.get("legalName"):
                enriched_data["legal_name"] = data["legalName"]

            if data.get("description"):
                enriched_data["description"] = data["description"]

            # Industry classification
            if data.get("category", {}).get("industry"):
                enriched_data["industry"] = data["category"]["industry"]

            if data.get("category", {}).get("sector"):
                enriched_data["sector"] = data["category"]["sector"]

            if data.get("tags"):
                enriched_data["tags"] = data["tags"][:10]  # Limit to 10

            # Size metrics
            if data.get("metrics", {}).get("employeesRange"):
                enriched_data["employee_count"] = data["metrics"][
                    "employeesRange"
                ]

            if data.get("metrics", {}).get("employees"):
                enriched_data["employee_count_exact"] = data["metrics"][
                    "employees"
                ]

            if data.get("metrics", {}).get("estimatedAnnualRevenue"):
                enriched_data["annual_revenue"] = data["metrics"][
                    "estimatedAnnualRevenue"
                ]

            # Company type
            if data.get("type"):
                enriched_data["company_type"] = data["type"]

            # Founded year
            if data.get("foundedYear"):
                enriched_data["founded_year"] = data["foundedYear"]

            # Location
            if data.get("location"):
                location_parts = []
                if data["location"].get("city"):
                    location_parts.append(data["location"]["city"])
                if data["location"].get("state"):
                    location_parts.append(data["location"]["state"])
                if data["location"].get("country"):
                    location_parts.append(data["location"]["country"])

                if location_parts:
                    enriched_data["location"] = ", ".join(location_parts)

                if data["location"].get("city"):
                    enriched_data["city"] = data["location"]["city"]

                if data["location"].get("state"):
                    enriched_data["state"] = data["location"]["state"]

                if data["location"].get("country"):
                    enriched_data["country"] = data["location"]["country"]

            # Logo
            if data.get("logo"):
                enriched_data["logo_url"] = data["logo"]

            # Social media
            social_media = {}
            if data.get("twitter", {}).get("handle"):
                social_media["twitter"] = (
                    f"https://twitter.com/{data['twitter']['handle']}"
                )

            if data.get("facebook", {}).get("handle"):
                social_media["facebook"] = (
                    f"https://facebook.com/{data['facebook']['handle']}"
                )

            if data.get("linkedin", {}).get("handle"):
                social_media["linkedin"] = (
                    f"https://linkedin.com/company/{data['linkedin']['handle']}"
                )

            if social_media:
                enriched_data["social_media"] = social_media

            # Technology stack
            if data.get("tech"):
                enriched_data["website_tech"] = data["tech"][:15]  # Top 15

            # Domain info
            if data.get("domain"):
                enriched_data["domain"] = data["domain"]

            # Remove None values
            enriched_data = {
                k: v for k, v in enriched_data.items() if v is not None
            }

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"Clearbit enriched {clean_domain}: "
                f"{enriched_data.get('company_name', 'Unknown')} in {duration_ms}ms",
                extra={
                    "domain": clean_domain,
                    "company": enriched_data.get("company_name"),
                    "fields": len(enriched_data),
                },
            )

            return SourceResult(
                source_name=self.name,
                success=True,
                data=enriched_data,
                duration_ms=duration_ms,
                cost_usd=self.cost_per_call,
            )

        except httpx.TimeoutException:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"Timeout querying Clearbit for {domain} after {duration_ms}ms"
            )
            raise Exception(f"Request timeout after {self.timeout}s")

        except httpx.HTTPStatusError as e:
            duration_ms = int((time.time() - start_time) * 1000)

            # Don't charge for errors
            cost = 0.0

            if e.response.status_code == 404:
                logger.info(
                    f"Company not found in Clearbit: {domain}",
                    extra={"domain": domain, "status": 404},
                )
            elif e.response.status_code == 402:
                logger.error(
                    "Clearbit credits exhausted - payment required",
                    extra={"status": 402},
                )
            else:
                logger.warning(
                    f"HTTP error {e.response.status_code} from Clearbit for {domain}"
                )

            raise

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Error querying Clearbit for {domain}: {e}",
                exc_info=True,
            )
            raise
