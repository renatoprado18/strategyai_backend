"""
Adaptive Model Routing
Automatically selects the best AI model based on content complexity

Routes simple sections to cheap models, complex sections to premium models
"""

import logging
from typing import Dict, Any, Literal

logger = logging.getLogger(__name__)

# Model tiers by cost and capability
MODELS = {
    "ultra_cheap": {
        "model": "google/gemini-2.5-flash-preview-09-2025",
        "cost_per_1m_tokens": 0.30,
        "best_for": ["extraction", "simple summaries", "data formatting"]
    },
    "cheap": {
        "model": "anthropic/claude-haiku-4.5",
        "cost_per_1m_tokens": 1.25,
        "best_for": ["polishing", "formatting", "basic analysis"]
    },
    "mid": {
        "model": "google/gemini-2.5-pro-preview",
        "cost_per_1m_tokens": 7.50,
        "best_for": ["structured data", "competitive matrices", "tables"]
    },
    "premium": {
        "model": "openai/gpt-4o",
        "cost_per_1m_tokens": 10.00,
        "best_for": ["strategic frameworks", "creative thinking", "complex analysis"]
    },
    "reasoning": {
        "model": "anthropic/claude-3.5-sonnet",
        "cost_per_1m_tokens": 15.00,
        "best_for": ["risk assessment", "priority scoring", "deep reasoning"]
    }
}


# ============================================================================
# COMPLEXITY SCORING
# ============================================================================

def score_complexity(
    task_type: str,
    data_available: int,  # Number of data points available
    requires_reasoning: bool = False,
    requires_creativity: bool = False,
    requires_math: bool = False
) -> float:
    """
    Score task complexity from 0 (simple) to 1 (very complex)

    Returns:
        Complexity score 0-1
    """
    complexity = 0.0

    # Task type baseline
    task_complexity = {
        "extraction": 0.1,
        "formatting": 0.2,
        "summary": 0.3,
        "comparison": 0.4,
        "analysis": 0.6,
        "strategic_planning": 0.8,
        "risk_assessment": 0.9
    }
    complexity += task_complexity.get(task_type, 0.5)

    # Data availability (more data = more complex)
    if data_available > 100:
        complexity += 0.2
    elif data_available > 50:
        complexity += 0.1

    # Special requirements
    if requires_reasoning:
        complexity += 0.2
    if requires_creativity:
        complexity += 0.15
    if requires_math:
        complexity += 0.1

    return min(complexity, 1.0)


def select_model_for_task(
    task_type: str,
    complexity_score: float,
    fallback_allowed: bool = True
) -> Dict[str, Any]:
    """
    Select the most cost-effective model for a task

    Args:
        task_type: Type of task (extraction, analysis, etc.)
        complexity_score: Complexity score 0-1
        fallback_allowed: Whether to allow fallback to cheaper model

    Returns:
        Model configuration dict
    """

    # Route based on complexity
    if complexity_score < 0.3:
        tier = "ultra_cheap"
    elif complexity_score < 0.5:
        tier = "cheap"
    elif complexity_score < 0.7:
        tier = "mid"
    elif complexity_score < 0.85:
        tier = "premium"
    else:
        tier = "reasoning"

    # Override for specific task types
    if task_type == "risk_assessment":
        tier = "reasoning"  # Always use best reasoning model
    elif task_type == "strategic_planning":
        tier = "premium"  # Always use strategic model
    elif task_type == "competitive_matrix":
        tier = "mid"  # Gemini Pro is great at structured data
    elif task_type == "extraction" and complexity_score < 0.4:
        tier = "ultra_cheap"  # Simple extraction = ultra cheap

    model_config = MODELS[tier].copy()
    model_config["tier"] = tier
    model_config["fallback_allowed"] = fallback_allowed

    logger.info(f"[ROUTING] Task: {task_type}, Complexity: {complexity_score:.2f} → {tier} ({model_config['model']})")

    return model_config


# ============================================================================
# STAGE-SPECIFIC ROUTING
# ============================================================================

def route_stage1_extraction(data_sources_count: int) -> str:
    """Route Stage 1: Data Extraction"""
    complexity = score_complexity(
        task_type="extraction",
        data_available=data_sources_count * 10,  # Rough estimate
        requires_reasoning=False
    )
    return select_model_for_task("extraction", complexity)["model"]


def route_stage3_strategy(
    has_rich_data: bool,
    industry_complexity: Literal["low", "medium", "high"] = "medium"
) -> str:
    """Route Stage 3: Strategic Analysis"""

    # Always use premium for strategy, but adjust complexity
    base_complexity = 0.75

    if has_rich_data:
        base_complexity += 0.1
    if industry_complexity == "high":
        base_complexity += 0.1

    complexity = min(base_complexity, 1.0)

    return select_model_for_task("strategic_planning", complexity)["model"]


def route_stage4_competitive(competitor_count: int) -> str:
    """Route Stage 4: Competitive Matrix"""
    complexity = score_complexity(
        task_type="competitive_matrix",
        data_available=competitor_count * 5,
        requires_reasoning=False
    )
    return select_model_for_task("competitive_matrix", complexity)["model"]


def route_stage5_risk(recommendation_count: int) -> str:
    """Route Stage 5: Risk Assessment"""
    complexity = score_complexity(
        task_type="risk_assessment",
        data_available=recommendation_count,
        requires_reasoning=True,
        requires_math=True
    )
    return select_model_for_task("risk_assessment", complexity)["model"]


def route_stage6_polish(report_length: int) -> str:
    """Route Stage 6: Executive Polish"""
    complexity = score_complexity(
        task_type="formatting",
        data_available=report_length // 100,  # Rough complexity
        requires_creativity=True
    )
    return select_model_for_task("formatting", complexity)["model"]


# ============================================================================
# COST ESTIMATION
# ============================================================================

def estimate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int
) -> float:
    """
    Estimate cost for a model call

    Returns:
        Estimated cost in USD
    """
    # Find model tier
    model_tier = None
    for tier, config in MODELS.items():
        if config["model"] == model:
            model_tier = config
            break

    if not model_tier:
        logger.warning(f"[ROUTING] Unknown model: {model}, using default cost")
        return (input_tokens + output_tokens) / 1_000_000 * 5.0  # Default estimate

    total_tokens = input_tokens + output_tokens
    cost = (total_tokens / 1_000_000) * model_tier["cost_per_1m_tokens"]

    return cost


def get_routing_recommendation(extracted_data: Dict[str, Any]) -> Dict[str, str]:
    """
    Analyze extracted data and recommend models for each stage

    Returns:
        Dict mapping stage to recommended model
    """
    data_richness = len(str(extracted_data))
    competitor_count = len(extracted_data.get("competitors", []))
    has_financial_data = bool(extracted_data.get("key_metrics", {}).get("revenue"))

    # Determine industry complexity
    industry = extracted_data.get("industry", "").lower()
    high_complexity_industries = ["tecnologia", "saúde", "serviços financeiros"]
    industry_complexity = "high" if industry in high_complexity_industries else "medium"

    routing = {
        "stage1": route_stage1_extraction(data_sources_count=5),  # Assume 5 data sources
        "stage3": route_stage3_strategy(
            has_rich_data=has_financial_data or data_richness > 5000,
            industry_complexity=industry_complexity
        ),
        "stage4": route_stage4_competitive(competitor_count=max(competitor_count, 3)),
        "stage5": route_stage5_risk(recommendation_count=5),  # Assume 5 recommendations
        "stage6": route_stage6_polish(report_length=data_richness)
    }

    logger.info(f"[ROUTING] Recommended models:")
    for stage, model in routing.items():
        logger.info(f"[ROUTING]   {stage}: {model}")

    return routing
