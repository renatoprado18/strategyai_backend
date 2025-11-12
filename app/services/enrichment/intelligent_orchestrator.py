"""
Intelligent Source Orchestrator

Smart data source selection and reconciliation system.
Implements Layer 2 intelligence:
- Geographic-based source selection
- Multi-source data reconciliation
- Conflict resolution
- Confidence scoring

Created: 2025-01-12
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


class IntelligentSourceOrchestrator:
    """
    Intelligent source selection and data reconciliation.

    Features:
    - Smart source selection based on domain/country
    - Multi-source data reconciliation
    - Conflict resolution with confidence weighting
    - Data quality scoring
    """

    # Source priority by country
    SOURCE_PRIORITY = {
        "BR": ["receita_ws", "clearbit", "google_places", "proxycurl"],
        "US": ["clearbit", "google_places", "proxycurl"],
        "default": ["clearbit", "google_places", "proxycurl"],
    }

    # Field-specific source trust scores (0-100)
    SOURCE_TRUST_SCORES = {
        "receita_ws": {
            "cnpj": 100,  # Government data
            "legal_name": 95,
            "legal_nature": 95,
            "registration_status": 95,
            "cnae": 90,
        },
        "clearbit": {
            "employee_count": 90,  # High-quality B2B data
            "annual_revenue": 85,
            "founded_year": 90,
            "company_type": 85,
            "industry": 80,
        },
        "google_places": {
            "rating": 95,  # Verified data
            "reviews_count": 95,
            "phone": 90,
            "address": 90,
            "place_id": 100,
        },
        "proxycurl": {
            "linkedin_url": 95,  # LinkedIn data
            "linkedin_followers": 85,
            "specialties": 80,
        },
        "metadata_enhanced": {
            "company_name": 70,  # Self-reported
            "description": 65,
            "website_tech": 80,
            "social_media": 75,
        },
        "ip_api": {
            "ip_location": 60,  # Approximate
            "timezone": 70,
        },
    }

    def __init__(self):
        """Initialize intelligent orchestrator"""
        self.source_calls = {}  # Track which sources were called
        self.reconciliation_log = []  # Log reconciliation decisions

    def select_sources_for_domain(
        self,
        domain: str,
        country: Optional[str] = None,
        budget_usd: float = 1.0
    ) -> List[str]:
        """
        Smart source selection based on domain characteristics.

        Args:
            domain: Company domain
            country: Detected country code (BR, US, etc)
            budget_usd: Available budget for paid APIs

        Returns:
            List of source names to call in priority order
        """
        # Detect country from domain if not provided
        if not country:
            country = self._detect_country_from_domain(domain)

        # Get country-specific sources
        sources = self.SOURCE_PRIORITY.get(
            country,
            self.SOURCE_PRIORITY["default"]
        ).copy()

        # Filter by budget
        if budget_usd <= 0:
            # Only free sources
            sources = ["metadata_enhanced", "ip_api"]
        elif budget_usd < 0.10:
            # Cheap sources only
            sources = [s for s in sources if s not in ["proxycurl"]]

        logger.info(
            f"Selected sources for {domain} (country={country}, budget=${budget_usd:.2f}): {sources}"
        )

        return sources

    def _detect_country_from_domain(self, domain: str) -> str:
        """Detect country from TLD"""
        tld = domain.split(".")[-1].lower()

        tld_map = {
            "br": "BR",
            "com.br": "BR",
            "us": "US",
            "uk": "UK",
            "co.uk": "UK",
            "de": "DE",
            "fr": "FR",
            "jp": "JP",
            "cn": "CN",
            "in": "IN",
        }

        return tld_map.get(tld, "default")

    def reconcile_data(
        self,
        source_results: Dict[str, Dict[str, Any]]
    ) -> Tuple[Dict[str, Any], Dict[str, float]]:
        """
        Reconcile data from multiple sources with conflict resolution.

        Strategy:
        1. For each field, collect values from all sources
        2. If single value: use it
        3. If multiple values: use highest confidence source
        4. Calculate confidence score per field

        Args:
            source_results: Dict mapping source_name -> data

        Returns:
            (reconciled_data, confidence_scores)
        """
        reconciled = {}
        confidences = {}
        field_sources = {}  # Track which source provided each field

        # Collect all fields from all sources
        all_fields = set()
        for source_data in source_results.values():
            all_fields.update(source_data.keys())

        # Reconcile each field
        for field in all_fields:
            values = []

            # Collect values from each source
            for source_name, source_data in source_results.items():
                if field in source_data and source_data[field] is not None:
                    trust_score = self._get_source_trust_score(source_name, field)
                    values.append({
                        "value": source_data[field],
                        "source": source_name,
                        "trust": trust_score
                    })

            if not values:
                continue

            # Single value - use it
            if len(values) == 1:
                reconciled[field] = values[0]["value"]
                confidences[field] = values[0]["trust"]
                field_sources[field] = values[0]["source"]

            # Multiple values - reconcile
            else:
                winner = self._resolve_conflict(field, values)
                reconciled[field] = winner["value"]
                confidences[field] = winner["confidence"]
                field_sources[field] = winner["source"]

                # Log reconciliation
                self.reconciliation_log.append({
                    "field": field,
                    "values": [v["value"] for v in values],
                    "sources": [v["source"] for v in values],
                    "winner": winner["source"],
                    "confidence": winner["confidence"]
                })

        logger.info(
            f"Reconciled {len(reconciled)} fields from {len(source_results)} sources. "
            f"Conflicts resolved: {len(self.reconciliation_log)}"
        )

        return reconciled, confidences

    def _resolve_conflict(
        self,
        field: str,
        values: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Resolve conflicting values for a field.

        Strategy:
        1. Numeric fields: Average if similar, highest trust if different
        2. String fields: Longest/most detailed from highest trust source
        3. Lists: Merge unique values

        Args:
            field: Field name
            values: List of {value, source, trust}

        Returns:
            {value, source, confidence}
        """
        # Sort by trust score (highest first)
        values = sorted(values, key=lambda x: x["trust"], reverse=True)

        # Handle numeric fields (employee_count, annual_revenue)
        if field in ["employee_count", "annual_revenue"]:
            return self._reconcile_numeric_range(field, values)

        # Handle list fields (specialties, key_differentiators)
        if isinstance(values[0]["value"], list):
            return self._reconcile_lists(field, values)

        # Handle string fields - use highest trust source
        winner = values[0]
        return {
            "value": winner["value"],
            "source": winner["source"],
            "confidence": winner["trust"]
        }

    def _reconcile_numeric_range(
        self,
        field: str,
        values: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Reconcile numeric range fields (e.g., "25-50", "R$ 5-10M").

        If ranges overlap, merge them.
        Otherwise, use highest trust source.
        """
        # For now, use highest trust source
        # TODO: Implement range overlap detection
        winner = values[0]
        return {
            "value": winner["value"],
            "source": winner["source"],
            "confidence": winner["trust"]
        }

    def _reconcile_lists(
        self,
        field: str,
        values: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Reconcile list fields by merging unique values.

        Takes top 5 items by frequency across sources.
        """
        all_items = []
        sources = []

        for v in values:
            all_items.extend(v["value"])
            sources.append(v["source"])

        # Get unique items (preserve order)
        seen = set()
        unique_items = []
        for item in all_items:
            if item not in seen:
                seen.add(item)
                unique_items.append(item)

        # Take top 5
        merged = unique_items[:5]

        # Calculate confidence (average trust of contributing sources)
        avg_trust = sum(v["trust"] for v in values) / len(values)

        return {
            "value": merged,
            "source": ", ".join(sources),
            "confidence": avg_trust
        }

    def _get_source_trust_score(self, source_name: str, field: str) -> float:
        """
        Get trust score for a source's field.

        Returns:
            Trust score (0-100)
        """
        if source_name in self.SOURCE_TRUST_SCORES:
            field_scores = self.SOURCE_TRUST_SCORES[source_name]
            if field in field_scores:
                return field_scores[field]

        # Default trust score by source type
        default_scores = {
            "receita_ws": 90,  # Government data
            "clearbit": 85,  # High-quality B2B
            "google_places": 85,  # Verified data
            "proxycurl": 80,  # LinkedIn data
            "metadata_enhanced": 70,  # Self-reported
            "ip_api": 60,  # Approximate
        }

        return default_scores.get(source_name, 50)

    def infer_missing_fields(
        self,
        reconciled_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Infer missing fields from available data.

        Examples:
        - Estimate revenue from employee_count + industry
        - Infer company_size from employee_count
        - Detect B2B/B2C from website content
        """
        inferences = {}

        # Infer company_size from employee_count
        if "employee_count" in reconciled_data and "company_size" not in reconciled_data:
            emp_count = reconciled_data["employee_count"]
            inferences["company_size"] = self._infer_company_size(emp_count)

        # Infer digital_maturity from website_tech
        if "website_tech" in reconciled_data and "digital_maturity" not in reconciled_data:
            tech = reconciled_data["website_tech"]
            inferences["digital_maturity"] = self._infer_digital_maturity(tech)

        if inferences:
            logger.info(f"Inferred {len(inferences)} missing fields: {list(inferences.keys())}")

        return inferences

    def _infer_company_size(self, employee_count_str: str) -> str:
        """
        Infer company size category from employee count.

        Brazilian classification:
        - Micro: 0-9
        - Pequena: 10-49
        - Média: 50-249
        - Grande: 250+
        """
        # Extract number from range (e.g., "25-50" -> 37.5)
        import re
        numbers = re.findall(r'\d+', employee_count_str)

        if not numbers:
            return "Pequena"  # Default

        if len(numbers) == 1:
            count = int(numbers[0])
        else:
            # Average of range
            count = (int(numbers[0]) + int(numbers[1])) / 2

        if count < 10:
            return "Micro"
        elif count < 50:
            return "Pequena"
        elif count < 250:
            return "Média"
        else:
            return "Grande"

    def _infer_digital_maturity(self, technologies: List[str]) -> str:
        """
        Infer digital maturity from technology stack.

        High: Modern stack (React, Next.js, Vercel, etc)
        Medium: Standard stack (WordPress, PHP, etc)
        Low: Minimal tech or old stack
        """
        modern_tech = {
            "React", "Next.js", "Vue.js", "Angular", "Vercel",
            "Tailwind", "GraphQL", "Node.js"
        }

        if not technologies:
            return "Baixa"

        # Count modern technologies
        modern_count = sum(1 for tech in technologies if tech in modern_tech)

        if modern_count >= 3:
            return "Alta"
        elif modern_count >= 1:
            return "Média"
        else:
            return "Baixa"
