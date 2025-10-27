"""
Production-Grade Validation & Quality Control Utilities
- Language validation (Portuguese enforcement)
- Source attribution checking
- Cost tracking
- Hallucination detection
"""

import re
import json
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# ============================================================================
# LANGUAGE VALIDATION
# ============================================================================

def detect_english_leakage(text: str, threshold: float = 0.05) -> Tuple[bool, List[str]]:
    """
    Detect if text contains significant English content

    Args:
        text: Text to analyze
        threshold: Maximum allowed ratio of English words (default 5%)

    Returns:
        (is_valid, english_phrases_found)
        - is_valid: True if < threshold English detected
        - english_phrases_found: List of detected English phrases
    """

    # Common English words that shouldn't appear in Portuguese business text
    english_indicators = [
        # Business/Strategy terms
        r'\bmarket share\b', r'\bstakeholders?\b', r'\bbottom line\b',
        r'\bcash flow\b', r'\bbreakeven\b', r'\bvalue proposition\b',
        r'\bcustomer acquisition\b', r'\bchurn rate\b',

        # Risk/Analysis terms
        r'\brisk assessment\b', r'\bmitigation strateg(y|ies)\b',
        r'\bcontingency plan\b', r'\bearly warning\b', r'\bbest case\b',
        r'\bworst case\b', r'\bexpected case\b',

        # Common phrases
        r'\bincumbents?\b', r'\bcybersecurity breach\b',
        r'\bprice competition\b', r'\bImplement\b', r'\bDevelop\b',
        r'\bExpand\b', r'\bIncrease\b', r'\bReduce\b',

        # Action verbs
        r'\baction\b', r'\btimeline\b', r'\bmilestone\b',
        r'\bsuccess criteria\b', r'\bdependencies\b', r'\bblockers\b',

        # Common words
        r'\bthe\b', r'\band\b', r'\bfor\b', r'\bwith\b', r'\bfrom\b',
        r'\bthis\b', r'\bthat\b', r'\bhave\b', r'\bwill\b', r'\bshould\b'
    ]

    english_found = []

    for pattern in english_indicators:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            english_found.extend(matches)

    # Calculate ratio
    total_words = len(text.split())
    english_words = len(english_found)

    if total_words == 0:
        return True, []

    ratio = english_words / total_words
    is_valid = ratio < threshold

    if not is_valid:
        logger.warning(f"[LANGUAGE] English detected: {english_words}/{total_words} words ({ratio*100:.1f}%)")
        logger.warning(f"[LANGUAGE] English phrases: {english_found[:10]}")

    return is_valid, english_found


def enforce_portuguese_output(json_output: Dict[str, Any], stage_name: str) -> bool:
    """
    Recursively check JSON output for English leakage

    Returns:
        True if output is valid (all Portuguese)
        False if English detected
    """

    def check_value(value, path="root"):
        if isinstance(value, str):
            is_valid, english_found = detect_english_leakage(value, threshold=0.1)
            if not is_valid:
                logger.error(f"[{stage_name}] English detected in {path}: {english_found[:5]}")
                return False
        elif isinstance(value, dict):
            for k, v in value.items():
                if not check_value(v, f"{path}.{k}"):
                    return False
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if not check_value(item, f"{path}[{i}]"):
                    return False
        return True

    return check_value(json_output)


# ============================================================================
# SOURCE ATTRIBUTION VALIDATION
# ============================================================================

def validate_source_attribution(json_output: Dict[str, Any], required_fields: List[str]) -> Tuple[bool, List[str]]:
    """
    Check if quantitative claims have source attribution

    Args:
        json_output: JSON to validate
        required_fields: Fields that must have sources cited

    Returns:
        (is_valid, missing_sources)
    """

    missing_sources = []

    # Keywords that indicate quantitative claims requiring sources
    quant_indicators = [
        r'R\$\s*[\d,]+\s*(milhões?|bilhões?|mil)',  # Currency
        r'\d+%',  # Percentages
        r'\d+\.\d+\s*(milhões?|bilhões?)',  # Numbers with scale
        r'market share.*\d+',  # Market share claims
        r'\d+\s*clientes',  # Customer counts
    ]

    def check_for_sources(value, path=""):
        if isinstance(value, str):
            # Check if string contains quantitative claim
            has_quant_claim = any(re.search(pattern, value, re.IGNORECASE) for pattern in quant_indicators)

            if has_quant_claim:
                # Check if source is cited
                has_source = any(keyword in value.lower() for keyword in [
                    'fonte:', 'segundo', 'de acordo com', 'baseado em',
                    'estimativa', 'sem dados', 'não disponível', 'projeção'
                ])

                if not has_source:
                    missing_sources.append(f"{path}: {value[:100]}")

        elif isinstance(value, dict):
            for k, v in value.items():
                check_for_sources(v, f"{path}.{k}" if path else k)

        elif isinstance(value, list):
            for i, item in enumerate(value):
                check_for_sources(item, f"{path}[{i}]")

    check_for_sources(json_output)

    is_valid = len(missing_sources) == 0

    if not is_valid:
        logger.warning(f"[SOURCE] {len(missing_sources)} claims without sources")
        for missing in missing_sources[:5]:
            logger.warning(f"[SOURCE] Missing: {missing}")

    return is_valid, missing_sources


def validate_source_attribution_strict(json_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    STRICT source attribution validation - every quantitative claim MUST have source

    Returns:
        {
            "is_valid": bool,
            "violations": List[Dict],
            "severity": "OK" | "WARNING" | "CRITICAL"
        }
    """

    violations = []

    # Extended list of patterns requiring sources
    quant_patterns = [
        (r'R\$\s*[\d,]+\.?\d*\s*(trilh[oõ]es?|bilh[oõ]es?|milh[oõ]es?|mil)', 'currency'),
        (r'\d+\.?\d*\s*%', 'percentage'),
        (r'\d+\.?\d*\s*(trilh[oõ]es?|bilh[oõ]es?|milh[oõ]es?)\s+de\s+reais', 'currency_long'),
        (r'market\s+share.*?\d+', 'market_share'),
        (r'\d+\s+clientes?', 'customer_count'),
        (r'crescimento\s+de\s+\d+', 'growth_rate'),
        (r'receita\s+de\s+R\$\s*[\d,]+', 'revenue'),
    ]

    # Source markers (accepted)
    source_markers = [
        'fonte:', 'segundo', 'de acordo com', 'baseado em', 'conforme',
        'ibge', 'relatório', 'pesquisa', 'estudo',
        'estimativa', 'projeção', 'análise',
        'dados insuficientes', 'sem dados', 'não disponível', 'n/a',
        'conhecimento de mercado', 'contexto qualitativo'
    ]

    def check_value(value: Any, path: str = "root"):
        """Recursively check for unsourced quantitative claims"""

        if isinstance(value, str):
            for pattern, claim_type in quant_patterns:
                matches = re.finditer(pattern, value, re.IGNORECASE)
                for match in matches:
                    matched_text = match.group()

                    # Check if source marker is present in the same string
                    has_source = any(marker in value.lower() for marker in source_markers)

                    if not has_source:
                        violations.append({
                            "path": path,
                            "claim": matched_text,
                            "claim_type": claim_type,
                            "context": value[:150],
                            "severity": "CRITICAL" if claim_type in ['currency', 'revenue', 'market_share'] else "WARNING"
                        })

        elif isinstance(value, dict):
            for k, v in value.items():
                check_value(v, f"{path}.{k}")

        elif isinstance(value, list):
            for i, item in enumerate(value):
                check_value(item, f"{path}[{i}]")

    check_value(json_output)

    # Calculate severity
    critical_count = sum(1 for v in violations if v['severity'] == 'CRITICAL')
    severity = "CRITICAL" if critical_count > 0 else ("WARNING" if len(violations) > 0 else "OK")

    if violations:
        logger.warning(f"[STRICT SOURCE] Found {len(violations)} violations ({critical_count} critical)")
        for violation in violations[:5]:
            logger.warning(f"[STRICT SOURCE] {violation['claim_type']} at {violation['path']}: {violation['claim']}")

    return {
        "is_valid": severity == "OK",
        "violations": violations,
        "severity": severity,
        "critical_count": critical_count,
        "warning_count": len(violations) - critical_count
    }


# ============================================================================
# COST TRACKING
# ============================================================================

class CostTracker:
    """Track LLM API costs across pipeline stages"""

    def __init__(self):
        self.stages = {}
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

        # Pricing per model (per 1M tokens)
        self.pricing = {
            "google/gemini-2.5-flash-preview-09-2025": {"input": 0.075, "output": 0.30},
            "google/gemini-2.5-pro-preview": {"input": 1.25, "output": 5.00},
            "openai/gpt-4o": {"input": 2.50, "output": 10.00},
            "anthropic/claude-3.5-sonnet": {"input": 3.00, "output": 15.00},
            "anthropic/claude-haiku-4.5": {"input": 0.25, "output": 1.25},
        }

    def log_usage(self, stage_name: str, model: str, input_tokens: int, output_tokens: int):
        """Log token usage for a stage"""

        pricing = self.pricing.get(model, {"input": 5.0, "output": 15.0})  # Default to expensive

        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        stage_cost = input_cost + output_cost

        self.stages[stage_name] = {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost": stage_cost
        }

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_cost += stage_cost

        logger.info(f"[COST] {stage_name}: ${stage_cost:.4f} ({input_tokens} in, {output_tokens} out)")

    def get_summary(self) -> Dict[str, Any]:
        """Get cost summary"""
        return {
            "stages": self.stages,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "total_cost_usd": round(self.total_cost, 4),
            "cost_breakdown": {
                stage: f"${data['cost']:.4f}"
                for stage, data in self.stages.items()
            }
        }


# ============================================================================
# HALLUCINATION DETECTION
# ============================================================================

def detect_hallucinated_data(text: str, provided_context: str) -> List[str]:
    """
    Detect potentially hallucinated specific data points

    Returns:
        List of suspicious claims
    """

    suspicious = []

    # Extract specific numeric claims
    numeric_claims = re.findall(
        r'([\d,]+\.?\d*\s*(?:milhões?|bilhões?|%|clientes?|market share))',
        text,
        re.IGNORECASE
    )

    for claim in numeric_claims:
        # Check if this specific number appears in provided context
        # Extract just the number
        number = re.search(r'[\d,]+\.?\d*', claim)
        if number and number.group() not in provided_context:
            suspicious.append(claim)

    if suspicious:
        logger.warning(f"[HALLUCINATION] Potentially fabricated data: {suspicious[:5]}")

    return suspicious


# ============================================================================
# QUALITY TIER ASSESSMENT
# ============================================================================

def assess_data_quality(
    website: bool,
    apify_success: bool,
    perplexity_success: bool,
    documents_provided: bool = False,
    financial_data: bool = False
) -> Tuple[str, str, List[str]]:
    """
    Assess input data quality tier

    Returns:
        (tier, tier_label, recommendations)
    """

    score = 0
    recommendations = []

    if website:
        score += 1
    else:
        recommendations.append("Forneça o website da empresa para melhor análise")

    if apify_success:
        score += 2
    else:
        recommendations.append("Análise web limitada - considere fornecer documentos")

    if perplexity_success:
        score += 2

    if documents_provided:
        score += 3
        recommendations = []  # Documents override other recommendations

    if financial_data:
        score += 2
    else:
        recommendations.append("Forneça demonstrações financeiras para análise mais profunda")

    # Tier assignment
    if score >= 8:
        tier = "legendary"
        tier_label = "LEGENDARY"
    elif score >= 6:
        tier = "full"
        tier_label = "DADOS COMPLETOS"
    elif score >= 4:
        tier = "good"
        tier_label = "BONS DADOS"
    elif score >= 2:
        tier = "partial"
        tier_label = "DADOS PARCIAIS"
    else:
        tier = "minimal"
        tier_label = "DADOS MÍNIMOS"

    return tier, tier_label, recommendations
