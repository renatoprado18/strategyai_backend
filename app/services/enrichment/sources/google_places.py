"""
Google Places API Source for IMENSIAH Enrichment

Queries Google Places API for location verification and business details.

Provides:
- Verified business address
- Phone number
- Business hours
- Google rating and review count
- Place ID for future lookups
- Photos

This is a PAID source (~$0.02 per call).
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


class GooglePlacesSource(EnrichmentSource):
    """
    Extract location and business data from Google Places.

    Uses Google Places API (paid, requires API key).

    Capabilities:
    - Search for business by name
    - Verify business address
    - Get phone number and hours
    - Fetch Google rating and reviews
    - Retrieve photos and place ID

    Performance: ~1-2 seconds
    Cost: ~$0.02 per successful lookup
    Rate Limit: Depends on billing (usually generous)

    Usage:
        source = GooglePlacesSource()
        result = await source.enrich(
            "techstart.com",
            company_name="TechStart",
            city="São Paulo"
        )
        print(result.data)
        # {
        #     "address": "Av. Paulista, 1000...",
        #     "phone": "+55 11 1234-5678",
        #     "rating": 4.7,
        #     "reviews_count": 23
        # }
    """

    FIND_PLACE_URL = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
    PLACE_DETAILS_URL = (
        "https://maps.googleapis.com/maps/api/place/details/json"
    )

    def __init__(self):
        """Initialize Google Places source (paid, ~$0.02/call)"""
        super().__init__(name="google_places", cost_per_call=0.02)
        self.timeout = 10.0  # 10 second timeout
        self.api_key = getattr(settings, "google_places_api_key", None)

        if not self.api_key:
            logger.debug("[Google Places] API key not configured - will skip enrichment when called")

    async def enrich(self, domain: str, **kwargs) -> SourceResult:
        """
        Get location data from Google Places.

        Args:
            domain: Domain (for logging)
            **kwargs: Must contain 'company_name' and optionally 'city'
                - company_name: Business name to search for
                - city: City to narrow search (recommended)

        Returns:
            SourceResult with location data
        """
        start_time = time.time()

        try:
            # Gracefully handle missing API key (return empty result)
            if not self.api_key:
                logger.info("[Google Places] API key not configured - skipping enrichment")
                return SourceResult(
                    source_name=self.name,
                    success=False,
                    data={},
                    cost_usd=0.0,
                    duration_ms=0,
                    error_message="API key not configured"
                )

            company_name = kwargs.get("company_name")
            if not company_name:
                raise ValueError("Must provide 'company_name' parameter")

            # Build search query
            search_query = company_name
            if kwargs.get("city"):
                search_query += f" {kwargs['city']}"

            # Step 1: Find place by name
            place_id = await self._find_place(search_query)
            if not place_id:
                raise Exception(
                    f"Business not found in Google Places: {company_name}"
                )

            # Step 2: Get place details
            place_data = await self._get_place_details(place_id)

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"[Google Places] Enriched {company_name}: "
                f"{place_data.get('address', 'Unknown')} in {duration_ms}ms",
                extra={
                    "component": "google_places",
                    "domain": domain,
                    "company": company_name,
                    "place_id": place_id,
                    "duration_ms": duration_ms,
                },
            )

            return SourceResult(
                source_name=self.name,
                success=True,
                data=place_data,
                duration_ms=duration_ms,
                cost_usd=self.cost_per_call,
            )

        except httpx.TimeoutException:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"[Google Places] Request timeout after {duration_ms}ms",
                extra={"component": "google_places", "duration_ms": duration_ms}
            )
            raise Exception(f"Request timeout after {self.timeout}s")

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[Google Places] Unexpected error: {str(e)}",
                exc_info=True,
                extra={"component": "google_places", "duration_ms": duration_ms, "error_type": type(e).__name__}
            )
            raise

    async def _find_place(self, query: str) -> Optional[str]:
        """
        Find place ID by search query.

        Args:
            query: Search query (e.g., "TechStart São Paulo")

        Returns:
            Place ID or None if not found
        """
        params = {
            "input": query,
            "inputtype": "textquery",
            "fields": "place_id,name",
            "key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.FIND_PLACE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        if data.get("status") == "ZERO_RESULTS":
            logger.info(
                f"[Google Places] No results found for: {query}",
                extra={"component": "google_places", "query": query},
            )
            return None

        if data.get("status") != "OK":
            error_msg = data.get("error_message", data.get("status"))
            raise Exception(f"Google Places API error: {error_msg}")

        # Get first result's place ID
        candidates = data.get("candidates", [])
        if candidates:
            place_id = candidates[0].get("place_id")
            logger.debug(
                f"[Google Places] Found place ID {place_id} for query: {query}",
                extra={"component": "google_places", "query": query, "place_id": place_id},
            )
            return place_id

        return None

    async def _get_place_details(self, place_id: str) -> dict:
        """
        Get detailed place information.

        Args:
            place_id: Google Place ID

        Returns:
            Dict with place data
        """
        # Request comprehensive fields
        fields = [
            "name",
            "formatted_address",
            "formatted_phone_number",
            "international_phone_number",
            "rating",
            "user_ratings_total",
            "opening_hours",
            "website",
            "place_id",
            "geometry",
            "types",
            "photos",
        ]

        params = {
            "place_id": place_id,
            "fields": ",".join(fields),
            "key": self.api_key,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                self.PLACE_DETAILS_URL, params=params
            )
            response.raise_for_status()
            data = response.json()

        if data.get("status") != "OK":
            error_msg = data.get("error_message", data.get("status"))
            raise Exception(f"Google Places API error: {error_msg}")

        result = data.get("result", {})

        # Extract and normalize data
        enriched_data = {}

        if result.get("name"):
            enriched_data["business_name"] = result["name"]

        if result.get("formatted_address"):
            enriched_data["address"] = result["formatted_address"]

        if result.get("international_phone_number"):
            enriched_data["phone"] = result["international_phone_number"]
        elif result.get("formatted_phone_number"):
            enriched_data["phone"] = result["formatted_phone_number"]

        if result.get("rating"):
            enriched_data["rating"] = result["rating"]

        if result.get("user_ratings_total"):
            enriched_data["reviews_count"] = result["user_ratings_total"]

        if result.get("website"):
            enriched_data["website"] = result["website"]

        if result.get("place_id"):
            enriched_data["place_id"] = result["place_id"]

        # Business hours
        if result.get("opening_hours", {}).get("weekday_text"):
            enriched_data["business_hours"] = result["opening_hours"][
                "weekday_text"
            ]

        # Location coordinates
        if result.get("geometry", {}).get("location"):
            location = result["geometry"]["location"]
            enriched_data["latitude"] = location.get("lat")
            enriched_data["longitude"] = location.get("lng")

        # Business types
        if result.get("types"):
            enriched_data["business_types"] = result["types"][:5]  # Top 5

        # Photos (just count and first photo reference)
        if result.get("photos"):
            enriched_data["photos_count"] = len(result["photos"])
            if len(result["photos"]) > 0:
                first_photo = result["photos"][0]
                if first_photo.get("photo_reference"):
                    enriched_data["photo_reference"] = first_photo[
                        "photo_reference"
                    ]

        # Remove None values
        enriched_data = {
            k: v for k, v in enriched_data.items() if v is not None
        }

        return enriched_data
