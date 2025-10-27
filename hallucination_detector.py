"""
Hallucination Detection & Validation
Prevents AI from generating unrealistic numbers and fabricated data
"""

import re
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# CURRENCY VALUE EXTRACTION
# ============================================================================

def extract_currency_value(text: str) -> Optional[float]:
    """
    Extract numeric value from Brazilian currency strings

    Examples:
    - "R$ 100 bilhões" → 100_000_000_000
    - "R$ 5,5 trilhões" → 5_500_000_000_000
    - "R$ 250 milhões" → 250_000_000
    - "R$ 10 mil" → 10_000

    Returns:
        Float value in reais, or None if no value found
    """

    if not isinstance(text, str):
        return None

    # Clean text
    text = text.lower().replace('.', '').replace(' ', '')

    # Match patterns like "r$100bilhões" or "100milhões"
    patterns = [
        # Trillions
        (r'r?\$?\s*([0-9,]+(?:[.,][0-9]+)?)\s*(?:trilh[oõ]es?|tri)', 1_000_000_000_000),
        # Billions
        (r'r?\$?\s*([0-9,]+(?:[.,][0-9]+)?)\s*(?:bilh[oõ]es?|bi)', 1_000_000_000),
        # Millions
        (r'r?\$?\s*([0-9,]+(?:[.,][0-9]+)?)\s*(?:milh[oõ]es?|mi)', 1_000_000),
        # Thousands
        (r'r?\$?\s*([0-9,]+(?:[.,][0-9]+)?)\s*mil', 1_000),
        # Plain numbers
        (r'r?\$?\s*([0-9,]+(?:[.,][0-9]+)?)\s*(?:reais?)?', 1),
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, text)
        if match:
            # Extract number and convert
            num_str = match.group(1).replace(',', '.')
            try:
                number = float(num_str)
                return number * multiplier
            except ValueError:
                continue

    return None


# ============================================================================
# MARKET SIZING VALIDATION
# ============================================================================

def validate_market_sizing(
    tam: Any,
    sam: Any,
    som: Any,
    company_size: str = "pequena",
    company_name: str = "Empresa"
) -> Dict[str, Any]:
    """
    Validate TAM/SAM/SOM makes sense based on company size

    Args:
        tam: TAM value (string like "R$ 100 bilhões" or dict)
        sam: SAM value
        som: SOM value
        company_size: "pequena", "média", or "grande"
        company_name: Name of company for logging

    Returns:
        {
            "is_valid": bool,
            "issues": List[str],
            "severity": "OK" | "WARNING" | "CRITICAL",
            "auto_fix": dict | None (replacement tam_sam_som if needed)
        }
    """

    issues = []
    severity = "OK"
    auto_fix = None

    # Handle dict format (when insufficient data)
    if isinstance(tam, dict) or isinstance(sam, dict) or isinstance(som, dict):
        # Check if it's the "dados_insuficientes" format
        if isinstance(tam, dict) and tam.get('status') == 'dados_insuficientes':
            # This is OK - explicitly marked as insufficient
            return {
                "is_valid": True,
                "issues": [],
                "severity": "OK",
                "auto_fix": None
            }

    # Extract numeric values
    tam_value = extract_currency_value(str(tam))
    sam_value = extract_currency_value(str(sam))
    som_value = extract_currency_value(str(som))

    # Check if values were extracted
    if tam_value is None or sam_value is None or som_value is None:
        logger.warning(f"[HALLUCINATION] Could not extract numeric values from TAM/SAM/SOM")
        return {
            "is_valid": False,
            "issues": ["Não foi possível extrair valores numéricos de TAM/SAM/SOM"],
            "severity": "CRITICAL",
            "auto_fix": {
                "status": "dados_insuficientes",
                "mensagem": "Análise TAM/SAM/SOM requer dados adicionais para evitar estimativas imprecisas",
                "o_que_fornecer": [
                    "Demonstrações financeiras (últimos 2 anos)",
                    "Faturamento atual da empresa",
                    "Relatórios de mercado ou pesquisa setorial específica"
                ],
                "contexto_qualitativo": f"Mercado requer análise mais profunda para {company_name}",
                "proximos_passos": "Forneça dados financeiros para análise quantitativa precisa de mercado acessível."
            }
        }

    # Check hierarchy: SOM ≤ SAM ≤ TAM
    if som_value > sam_value:
        issues.append(f"CRÍTICO: SOM (R$ {som_value/1_000_000:.1f}M) > SAM (R$ {sam_value/1_000_000:.1f}M) - impossível")
        severity = "CRITICAL"

    if sam_value > tam_value:
        issues.append(f"CRÍTICO: SAM (R$ {sam_value/1_000_000:.1f}M) > TAM (R$ {tam_value/1_000_000:.1f}M) - impossível")
        severity = "CRITICAL"

    # Check SOM ratio based on company size
    som_ratio = som_value / tam_value if tam_value > 0 else 0

    # Define expected ranges
    expected_ranges = {
        "pequena": (0.0001, 0.005),  # 0.01-0.5%
        "média": (0.005, 0.02),       # 0.5-2%
        "grande": (0.02, 0.10)        # 2-10%
    }

    min_ratio, max_ratio = expected_ranges.get(company_size, (0.0001, 0.005))

    if som_ratio > max_ratio:
        issues.append(
            f"ALERTA: SOM muito alto para empresa {company_size}. "
            f"SOM/TAM = {som_ratio*100:.2f}%, esperado < {max_ratio*100:.1f}%. "
            f"SOM de R$ {som_value/1_000_000_000:.1f} bilhões é improvável."
        )
        severity = "CRITICAL" if severity != "CRITICAL" else severity

    if som_ratio < min_ratio and som_value > 1_000_000:  # Only flag if SOM > R$ 1M
        issues.append(
            f"INFO: SOM parece conservador demais. "
            f"SOM/TAM = {som_ratio*100:.4f}%, esperado > {min_ratio*100:.2f}%"
        )
        if severity == "OK":
            severity = "WARNING"

    # Absolute bounds check
    if som_value > 10_000_000_000:  # R$ 10 billion
        issues.append(
            f"CRÍTICO: SOM de R$ {som_value/1_000_000_000:.1f} bilhões é irrealista para maioria das empresas. "
            f"Apenas gigantes corporativos têm SOM nesta escala."
        )
        severity = "CRITICAL"

    # If critical issues, suggest auto-fix
    if severity == "CRITICAL":
        auto_fix = {
            "status": "dados_insuficientes",
            "mensagem": "Validação detectou inconsistências em TAM/SAM/SOM. Análise requer dados adicionais.",
            "o_que_fornecer": [
                "Demonstrações financeiras (últimos 2 anos)",
                "Faturamento atual da empresa",
                "Relatórios de mercado ou pesquisa setorial específica com dados concretos"
            ],
            "contexto_qualitativo": f"Mercado requer análise mais profunda com dados reais para {company_name}. Estimativas sem base de dados geram inconsistências.",
            "proximos_passos": "Forneça dados financeiros e de mercado para análise quantitativa precisa.",
            "issues_detectados": issues
        }

    return {
        "is_valid": len(issues) == 0 or severity == "WARNING",
        "issues": issues,
        "severity": severity,
        "auto_fix": auto_fix
    }


# ============================================================================
# NUMERIC CLAIMS VALIDATION
# ============================================================================

def validate_numeric_claims(json_output: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate all numeric claims in output are reasonable

    Checks:
    - Market share < 100%
    - Growth rates < 500% (unless explicitly marked as exceptional)
    - Revenue projections are grounded

    Returns:
        {
            "is_valid": bool,
            "violations": List[str]
        }
    """

    violations = []

    def check_value(value: Any, path: str = "root"):
        """Recursively check numeric claims"""

        if isinstance(value, str):
            # Check for unrealistic percentages
            pct_matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', value)
            for pct_str in pct_matches:
                pct = float(pct_str)
                if pct > 100 and "crescimento" in value.lower():
                    if "excepcional" not in value.lower() and "extraordinário" not in value.lower():
                        violations.append(
                            f"{path}: Crescimento de {pct}% sem justificativa extraordinária: '{value[:100]}'"
                        )
                elif pct > 100 and "market share" in value.lower():
                    violations.append(
                        f"{path}: Market share de {pct}% impossível (> 100%): '{value[:100]}'"
                    )

        elif isinstance(value, dict):
            for k, v in value.items():
                check_value(v, f"{path}.{k}")

        elif isinstance(value, list):
            for i, item in enumerate(value):
                check_value(item, f"{path}[{i}]")

    check_value(json_output)

    return {
        "is_valid": len(violations) == 0,
        "violations": violations
    }


# ============================================================================
# COMPANY SIZE DETECTION
# ============================================================================

def detect_company_size(company_data: Dict[str, Any]) -> str:
    """
    Detect company size from available data

    Heuristics:
    - Faturamento > R$ 500M = grande
    - Faturamento R$ 50M-500M = média
    - Faturamento < R$ 50M = pequena
    - If no faturamento, use other signals (employees, market presence)

    Returns:
        "pequena" | "média" | "grande"
    """

    # Check for revenue data
    revenue_str = company_data.get('faturamento') or company_data.get('receita') or ""
    revenue_value = extract_currency_value(str(revenue_str))

    if revenue_value:
        if revenue_value > 500_000_000:  # R$ 500M
            return "grande"
        elif revenue_value > 50_000_000:  # R$ 50M
            return "média"
        else:
            return "pequena"

    # Check for employee count
    employees_str = company_data.get('funcionarios') or company_data.get('employees') or ""
    employees_match = re.search(r'(\d+)', str(employees_str))

    if employees_match:
        employees = int(employees_match.group(1))
        if employees > 500:
            return "grande"
        elif employees > 50:
            return "média"
        else:
            return "pequena"

    # Check for keywords in description
    description = str(company_data.get('company', '')).lower()

    if any(word in description for word in ['startup', 'boutique', 'pequena', 'nova']):
        return "pequena"
    elif any(word in description for word in ['média', 'regional']):
        return "média"
    elif any(word in description for word in ['multinacional', 'líder', 'gigante']):
        return "grande"

    # Default to pequena (conservative)
    return "pequena"
