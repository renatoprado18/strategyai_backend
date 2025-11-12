"""
Confidence Scoring System

Calculates confidence scores for enriched data fields based on:
- Data source reliability
- Multiple source agreement
- Field type characteristics
- Data freshness

Created: 2025-01-12
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ConfidenceScorer:
    """
    Calculate confidence scores for enriched data fields.

    Confidence factors:
    1. Source reliability (0-100)
    2. Multiple source agreement (bonus)
    3. Field type characteristics
    4. Data freshness
    5. Validation checks

    Output: Confidence score per field (0-100)
    """

    # Base reliability scores by source
    SOURCE_RELIABILITY = {
        "receita_ws": 95,  # Government data
        "clearbit": 85,  # Premium B2B data
        "google_places": 85,  # Verified by Google
        "proxycurl": 80,  # LinkedIn data
        "metadata_enhanced": 70,  # Self-reported
        "ip_api": 60,  # Approximate
        "ai_inference_enhanced": 75,  # AI-inferred
    }

    # Field-specific confidence modifiers
    FIELD_CHARACTERISTICS = {
        # High confidence fields (verified/structured)
        "cnpj": {"base_confidence": 95, "requires_validation": True},
        "legal_name": {"base_confidence": 90, "requires_validation": False},
        "place_id": {"base_confidence": 95, "requires_validation": False},
        "rating": {"base_confidence": 90, "requires_validation": False},

        # Medium confidence fields (commonly accurate)
        "employee_count": {"base_confidence": 80, "requires_validation": False},
        "annual_revenue": {"base_confidence": 75, "requires_validation": False},
        "industry": {"base_confidence": 80, "requires_validation": False},
        "company_name": {"base_confidence": 85, "requires_validation": False},

        # Lower confidence fields (approximate/inferred)
        "ip_location": {"base_confidence": 60, "requires_validation": False},
        "company_size": {"base_confidence": 70, "requires_validation": False},
        "digital_maturity": {"base_confidence": 70, "requires_validation": False},

        # AI-inferred fields
        "ai_industry": {"base_confidence": 75, "requires_validation": False},
        "ai_target_audience": {"base_confidence": 70, "requires_validation": False},
        "ai_communication_tone": {"base_confidence": 65, "requires_validation": False},
        "ai_key_differentiators": {"base_confidence": 70, "requires_validation": False},
    }

    def __init__(self):
        """Initialize confidence scorer"""
        self.field_sources = {}  # Track which sources provided each field
        self.field_values = {}  # Track all values for conflict detection

    def calculate_field_confidence(
        self,
        field_name: str,
        field_value: Any,
        source_name: str,
        all_sources: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> float:
        """
        Calculate confidence score for a single field.

        Args:
            field_name: Name of the field
            field_value: Value of the field
            source_name: Source that provided this field
            all_sources: All source data for cross-validation

        Returns:
            Confidence score (0-100)
        """
        # Start with source reliability
        confidence = self.SOURCE_RELIABILITY.get(source_name, 50)

        # Apply field-specific characteristics
        if field_name in self.FIELD_CHARACTERISTICS:
            char = self.FIELD_CHARACTERISTICS[field_name]
            # Weight: 70% source reliability, 30% field characteristics
            confidence = (confidence * 0.7) + (char["base_confidence"] * 0.3)

        # Bonus for multiple source agreement
        if all_sources:
            agreement_bonus = self._calculate_agreement_bonus(
                field_name, field_value, all_sources
            )
            confidence = min(100, confidence + agreement_bonus)

        # Validation check (if applicable)
        if self._requires_validation(field_name):
            if self._validate_field(field_name, field_value):
                confidence = min(100, confidence + 5)  # +5 for valid format
            else:
                confidence = max(0, confidence - 10)  # -10 for invalid format

        # Track for learning
        if field_name not in self.field_sources:
            self.field_sources[field_name] = []
        self.field_sources[field_name].append(source_name)

        if field_name not in self.field_values:
            self.field_values[field_name] = []
        self.field_values[field_name].append(field_value)

        return round(confidence, 2)

    def calculate_overall_confidence(
        self,
        field_confidences: Dict[str, float]
    ) -> float:
        """
        Calculate overall enrichment confidence.

        Weighted average based on field importance.

        Args:
            field_confidences: Dict mapping field_name -> confidence

        Returns:
            Overall confidence score (0-100)
        """
        if not field_confidences:
            return 0.0

        # Field importance weights
        important_fields = {
            "company_name": 2.0,
            "industry": 1.5,
            "employee_count": 1.5,
            "cnpj": 2.0,
            "rating": 1.2,
        }

        weighted_sum = 0.0
        total_weight = 0.0

        for field, confidence in field_confidences.items():
            weight = important_fields.get(field, 1.0)
            weighted_sum += confidence * weight
            total_weight += weight

        return round(weighted_sum / total_weight, 2)

    def _calculate_agreement_bonus(
        self,
        field_name: str,
        field_value: Any,
        all_sources: Dict[str, Dict[str, Any]]
    ) -> float:
        """
        Calculate bonus for multiple source agreement.

        If 2+ sources agree on the same value, increase confidence.

        Args:
            field_name: Field being checked
            field_value: Value to check for agreement
            all_sources: All source data

        Returns:
            Bonus points (0-15)
        """
        agreement_count = 0

        for source_data in all_sources.values():
            if field_name in source_data:
                if self._values_match(source_data[field_name], field_value):
                    agreement_count += 1

        # Bonus scaling
        if agreement_count >= 3:
            return 15  # 3+ sources agree
        elif agreement_count == 2:
            return 10  # 2 sources agree
        elif agreement_count == 1:
            return 0  # Only this source
        else:
            return 0

    def _values_match(self, value1: Any, value2: Any) -> bool:
        """Check if two values match (with fuzzy matching)"""
        if value1 == value2:
            return True

        # String comparison (case-insensitive, whitespace-normalized)
        if isinstance(value1, str) and isinstance(value2, str):
            v1 = value1.lower().strip()
            v2 = value2.lower().strip()
            return v1 == v2

        # Numeric range comparison
        if isinstance(value1, str) and isinstance(value2, str):
            if "-" in value1 and "-" in value2:
                # Both are ranges - check overlap
                return self._ranges_overlap(value1, value2)

        return False

    def _ranges_overlap(self, range1: str, range2: str) -> bool:
        """Check if two numeric ranges overlap"""
        import re

        nums1 = [int(x) for x in re.findall(r'\d+', range1)]
        nums2 = [int(x) for x in re.findall(r'\d+', range2)]

        if len(nums1) != 2 or len(nums2) != 2:
            return False

        # Check overlap
        return not (nums1[1] < nums2[0] or nums2[1] < nums1[0])

    def _requires_validation(self, field_name: str) -> bool:
        """Check if field requires format validation"""
        if field_name in self.FIELD_CHARACTERISTICS:
            return self.FIELD_CHARACTERISTICS[field_name].get("requires_validation", False)
        return False

    def _validate_field(self, field_name: str, field_value: Any) -> bool:
        """
        Validate field format.

        Returns True if valid, False otherwise.
        """
        if field_name == "cnpj":
            return self._validate_cnpj(field_value)
        # Add more validators as needed
        return True

    def _validate_cnpj(self, cnpj: str) -> bool:
        """Validate Brazilian CNPJ format"""
        if not cnpj:
            return False

        # Remove formatting
        import re
        digits = re.sub(r'\D', '', cnpj)

        # Must be 14 digits
        if len(digits) != 14:
            return False

        # Basic checksum validation (simplified)
        return True  # Full validation would check modulo-11 checksums

    def get_confidence_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about confidence scoring.

        Returns:
            Metadata including source diversity, field coverage, etc.
        """
        return {
            "total_fields_scored": len(self.field_confidences),
            "sources_used": len(set(
                source for sources in self.field_sources.values() for source in sources
            )),
            "multi_source_fields": sum(
                1 for sources in self.field_sources.values() if len(sources) > 1
            ),
            "average_confidence": self.calculate_overall_confidence(self.field_confidences)
            if hasattr(self, 'field_confidences') else 0.0,
        }


def calculate_confidence_for_session(
    layer1_data: Dict[str, Any],
    layer2_data: Dict[str, Any],
    layer3_data: Dict[str, Any],
    layer1_sources: List[str],
    layer2_sources: List[str],
    layer3_sources: List[str]
) -> Tuple[Dict[str, float], float]:
    """
    Calculate confidence scores for an enrichment session.

    Args:
        layer1_data: Data from Layer 1
        layer2_data: Data from Layer 2
        layer3_data: Data from Layer 3
        layer1_sources: Sources called in Layer 1
        layer2_sources: Sources called in Layer 2
        layer3_sources: Sources called in Layer 3

    Returns:
        (field_confidences, overall_confidence)
    """
    scorer = ConfidenceScorer()
    field_confidences = {}

    # Combine all data
    all_data = {**layer1_data, **layer2_data, **layer3_data}
    all_sources = {
        **{s: layer1_data for s in layer1_sources},
        **{s: layer2_data for s in layer2_sources},
        **{s: layer3_data for s in layer3_sources},
    }

    # Score each field
    for field_name, field_value in all_data.items():
        # Determine source
        if field_name in layer3_data:
            source = layer3_sources[0] if layer3_sources else "unknown"
        elif field_name in layer2_data:
            source = layer2_sources[0] if layer2_sources else "unknown"
        else:
            source = layer1_sources[0] if layer1_sources else "unknown"

        confidence = scorer.calculate_field_confidence(
            field_name, field_value, source, all_sources
        )
        field_confidences[field_name] = confidence

    # Calculate overall confidence
    overall_confidence = scorer.calculate_overall_confidence(field_confidences)

    logger.info(
        f"Calculated confidence for {len(field_confidences)} fields. "
        f"Overall: {overall_confidence:.2f}"
    )

    return field_confidences, overall_confidence
