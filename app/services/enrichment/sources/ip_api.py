"""
IP Geolocation Source for IMENSIAH Enrichment

Resolves domain to IP and extracts location data using ip-api.com (free).

Provides:
- Country and city from IP
- Timezone
- ISP information

This is a FREE source with very fast response time (<200ms).
Used in QUICK enrichment phase.

Created: 2025-01-09
Version: 1.0.0
"""

import time
import logging
import socket
from typing import Optional
import httpx
from .base import EnrichmentSource, SourceResult

logger = logging.getLogger(__name__)


class IpApiSource(EnrichmentSource):
    """
    Extract geolocation data from domain IP address.

    Uses ip-api.com (free tier: 45 requests/minute).

    Capabilities:
    - Resolve domain to IP
    - Get country, region, city
    - Get timezone
    - Get ISP information

    Performance: ~100-200ms
    Cost: $0.00 (free)
    Rate Limit: 45 requests/minute

    Usage:
        source = IpApiSource()
        result = await source.enrich("techstart.com")
        print(result.data)
        # {
        #     "country": "BR",
        #     "city": "São Paulo",
        #     "timezone": "America/Sao_Paulo",
        #     "ip_location": "São Paulo, Brazil"
        # }
    """

    API_URL = "http://ip-api.com/json/{ip}?fields=status,message,country,countryCode,region,regionName,city,timezone,isp,query"

    def __init__(self):
        """Initialize IP API source (free, very fast)"""
        super().__init__(name="ip_api", cost_per_call=0.0)
        self.timeout = 5.0  # 5 second timeout

    async def enrich(self, domain: str, **kwargs) -> SourceResult:
        """
        Get geolocation data from domain IP.

        Args:
            domain: Domain to resolve (e.g., "techstart.com")
            **kwargs: Additional parameters (unused)

        Returns:
            SourceResult with location data
        """
        start_time = time.time()

        try:
            # Clean domain (remove protocol, www, path)
            clean_domain = (
                domain.replace("https://", "")
                .replace("http://", "")
                .replace("www.", "")
                .split("/")[0]
            )

            # Resolve domain to IP
            try:
                ip_address = socket.gethostbyname(clean_domain)
                logger.debug(
                    f"[IP API] Resolved {clean_domain} to IP: {ip_address}",
                    extra={"component": "ip_api", "domain": clean_domain, "ip": ip_address},
                )
            except socket.gaierror as e:
                raise Exception(f"Could not resolve domain to IP: {e}")

            # Query ip-api.com
            url = self.API_URL.format(ip=ip_address)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            # Check if request was successful
            if data.get("status") != "success":
                error_msg = data.get("message", "Unknown error")
                raise Exception(f"ip-api.com error: {error_msg}")

            # Extract and normalize data
            enriched_data = {
                "country": data.get("countryCode"),  # "BR"
                "country_name": data.get("country"),  # "Brazil"
                "region": data.get("regionName"),  # "São Paulo"
                "city": data.get("city"),  # "São Paulo"
                "timezone": data.get("timezone"),  # "America/Sao_Paulo"
                "isp": data.get("isp"),  # Internet provider
                "ip_address": data.get("query"),  # IP address
            }

            # Create formatted location string
            location_parts = []
            if enriched_data.get("city"):
                location_parts.append(enriched_data["city"])
            if enriched_data.get("region") and enriched_data.get(
                "region"
            ) != enriched_data.get("city"):
                location_parts.append(enriched_data["region"])
            if enriched_data.get("country_name"):
                location_parts.append(enriched_data["country_name"])

            if location_parts:
                enriched_data["ip_location"] = ", ".join(location_parts)

            # Remove None values
            enriched_data = {
                k: v for k, v in enriched_data.items() if v is not None
            }

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"[IP API] Location resolved for {domain}: "
                f"{enriched_data.get('ip_location', 'Unknown')} in {duration_ms}ms",
                extra={
                    "component": "ip_api",
                    "domain": domain,
                    "ip": ip_address,
                    "location": enriched_data.get("ip_location"),
                    "duration_ms": duration_ms,
                },
            )

            return SourceResult(
                source_name=self.name,
                success=True,
                data=enriched_data,
                duration_ms=duration_ms,
                cost_usd=0.0,
            )

        except httpx.TimeoutException:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"[IP API] Request timeout for {domain} after {duration_ms}ms",
                extra={"component": "ip_api", "domain": domain, "duration_ms": duration_ms}
            )
            raise Exception(f"Request timeout after {self.timeout}s")

        except httpx.HTTPStatusError as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"[IP API] HTTP {e.response.status_code} error for {domain}",
                extra={"component": "ip_api", "domain": domain, "status": e.response.status_code, "duration_ms": duration_ms}
            )
            raise Exception(f"HTTP {e.response.status_code}: {e.response.reason_phrase}")

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[IP API] Unexpected error for {domain}: {str(e)}",
                exc_info=True,
                extra={"component": "ip_api", "domain": domain, "duration_ms": duration_ms, "error_type": type(e).__name__}
            )
            raise
