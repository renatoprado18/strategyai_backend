"""
Receita Federal (ReceitaWS) Source for IMENSIAH Enrichment

Queries Brazilian CNPJ (company registration) data from ReceitaWS public API.

Provides:
- Legal company name (razão social)
- CNPJ number
- CNAE code (industry classification)
- Legal nature
- Registration status and date
- Full address
- Capital social

This is a FREE source but can be slow (2-3s).
Used in DEEP enrichment phase.

Created: 2025-01-09
Version: 1.0.0
"""

import time
import logging
import re
from typing import Optional
import httpx
from .base import EnrichmentSource, SourceResult

logger = logging.getLogger(__name__)


class ReceitaWSSource(EnrichmentSource):
    """
    Extract Brazilian company data from CNPJ registry.

    Uses ReceitaWS public API (free, no authentication required).

    Capabilities:
    - Search by company name to find CNPJ
    - Query CNPJ for complete registration data
    - Extract legal name, CNAE, address, status

    Performance: ~2-3 seconds (can be slow)
    Cost: $0.00 (free)
    Rate Limit: Conservative (respect public API)

    Usage:
        source = ReceitaWSSource()
        result = await source.enrich("TechStart", company_name="TechStart Innovations")
        print(result.data)
        # {
        #     "cnpj": "12.345.678/0001-99",
        #     "legal_name": "TECHSTART INNOVATIONS LTDA",
        #     "cnae": "6201-5/00",
        #     "legal_nature": "LTDA",
        #     "registration_status": "ATIVA"
        # }
    """

    # ReceitaWS API endpoints
    SEARCH_URL = "https://receitaws.com.br/v1/nome/{name}"
    CNPJ_URL = "https://receitaws.com.br/v1/cnpj/{cnpj}"

    def __init__(self):
        """Initialize ReceitaWS source (free, moderate speed)"""
        super().__init__(name="receita_ws", cost_per_call=0.0)
        self.timeout = 15.0  # 15 second timeout (API can be slow)

    async def enrich(self, domain: str, **kwargs) -> SourceResult:
        """
        Get Brazilian CNPJ data.

        Args:
            domain: Domain (used for logging only)
            **kwargs: Must contain either 'company_name' or 'cnpj'
                - company_name: Search for CNPJ by company name
                - cnpj: Direct CNPJ lookup

        Returns:
            SourceResult with CNPJ data
        """
        start_time = time.time()

        try:
            company_name = kwargs.get("company_name")
            cnpj = kwargs.get("cnpj")

            if not company_name and not cnpj:
                raise ValueError(
                    "Must provide either 'company_name' or 'cnpj' parameter"
                )

            # If only company name, search for CNPJ first
            if company_name and not cnpj:
                cnpj = await self._search_cnpj(company_name)
                if not cnpj:
                    raise Exception(
                        f"No CNPJ found for company name: {company_name}"
                    )

            # Clean CNPJ (remove formatting)
            cnpj_clean = re.sub(r"[^\d]", "", cnpj)
            if len(cnpj_clean) != 14:
                raise ValueError(
                    f"Invalid CNPJ format: {cnpj} (must be 14 digits)"
                )

            # Query CNPJ data
            cnpj_data = await self._query_cnpj(cnpj_clean)

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"[ReceitaWS] CNPJ data retrieved for {cnpj_clean}: "
                f"{cnpj_data.get('legal_name', 'Unknown')} in {duration_ms}ms",
                extra={
                    "component": "receita_ws",
                    "domain": domain,
                    "cnpj": cnpj_clean,
                    "company": cnpj_data.get("legal_name"),
                    "duration_ms": duration_ms,
                },
            )

            return SourceResult(
                source_name=self.name,
                success=True,
                data=cnpj_data,
                duration_ms=duration_ms,
                cost_usd=0.0,
            )

        except httpx.TimeoutException:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.warning(
                f"[ReceitaWS] Request timeout after {duration_ms}ms",
                extra={"component": "receita_ws", "duration_ms": duration_ms}
            )
            raise Exception(f"Request timeout after {self.timeout}s")

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[ReceitaWS] Unexpected error: {str(e)}",
                exc_info=True,
                extra={"component": "receita_ws", "duration_ms": duration_ms, "error_type": type(e).__name__}
            )
            raise

    async def _search_cnpj(self, company_name: str) -> Optional[str]:
        """
        Search for CNPJ by company name.

        Args:
            company_name: Company name to search

        Returns:
            CNPJ number (formatted) or None if not found
        """
        try:
            # Clean company name for search
            search_name = company_name.strip().upper()

            # Query ReceitaWS search API
            url = self.SEARCH_URL.format(name=search_name)
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                response.raise_for_status()
                data = response.json()

            # ReceitaWS returns array of matches
            if isinstance(data, list) and len(data) > 0:
                # Return first match's CNPJ
                first_match = data[0]
                cnpj = first_match.get("cnpj")
                logger.debug(
                    f"[ReceitaWS] Found CNPJ {cnpj} for company '{company_name}'",
                    extra={"component": "receita_ws", "company_name": company_name, "cnpj": cnpj},
                )
                return cnpj

            logger.info(
                f"[ReceitaWS] No CNPJ found for company: {company_name}",
                extra={"component": "receita_ws", "company_name": company_name}
            )
            return None

        except Exception as e:
            logger.warning(
                f"[ReceitaWS] CNPJ search failed for '{company_name}': {str(e)}",
                extra={"component": "receita_ws", "company_name": company_name, "error_type": type(e).__name__}
            )
            return None

    async def _query_cnpj(self, cnpj: str) -> dict:
        """
        Query full CNPJ data.

        Args:
            cnpj: CNPJ number (digits only, 14 chars)

        Returns:
            Dict with CNPJ data

        Raises:
            Exception if CNPJ not found or API error
        """
        url = self.CNPJ_URL.format(cnpj=cnpj)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

        # Check for API error
        if data.get("status") == "ERROR":
            error_msg = data.get("message", "Unknown error")
            raise Exception(f"ReceitaWS error: {error_msg}")

        # Parse and normalize data
        enriched_data = {
            "cnpj": data.get("cnpj"),  # Formatted CNPJ
            "legal_name": data.get("nome"),  # Razão social
            "trade_name": data.get("fantasia"),  # Nome fantasia
            "cnae": data.get("atividade_principal", [{}])[0].get(
                "code"
            ),  # Main CNAE code
            "cnae_description": data.get("atividade_principal", [{}])[0].get(
                "text"
            ),
            "legal_nature": data.get("natureza_juridica"),
            "registration_date": data.get("abertura"),  # Opening date
            "registration_status": data.get(
                "situacao"
            ),  # ATIVA, BAIXADA, etc.
            "capital_social": data.get("capital_social"),  # Share capital
        }

        # Parse address
        address_parts = []
        if data.get("logradouro"):
            street = data["logradouro"]
            if data.get("numero"):
                street += f", {data['numero']}"
            address_parts.append(street)

        if data.get("bairro"):
            address_parts.append(data["bairro"])

        if data.get("municipio") and data.get("uf"):
            address_parts.append(f"{data['municipio']} - {data['uf']}")

        if address_parts:
            enriched_data["address"] = ", ".join(address_parts)

        if data.get("cep"):
            enriched_data["postal_code"] = data["cep"]

        if data.get("telefone"):
            enriched_data["phone"] = data["telefone"]

        if data.get("email"):
            enriched_data["email"] = data["email"]

        # Location data
        if data.get("municipio"):
            enriched_data["city"] = data["municipio"]

        if data.get("uf"):
            enriched_data["state"] = data["uf"]
            # Create location string
            if data.get("municipio"):
                enriched_data["location"] = (
                    f"{data['municipio']}, {data['uf']}"
                )

        # Remove None values
        enriched_data = {
            k: v for k, v in enriched_data.items() if v is not None
        }

        return enriched_data
