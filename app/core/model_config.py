"""
Smart Model Selection Configuration
Uses the RIGHT model for each job - premium for client-facing, budget for backend
Based on comprehensive OpenRouter model analysis (Q4 2025)
"""
from typing import Dict, Any, Literal
from enum import Enum


class TaskType(Enum):
    """Classification of tasks by importance and visibility"""
    CLIENT_FACING = "client_facing"  # Direct client deliverable - use best models
    STRATEGIC = "strategic"  # Important analysis requiring reasoning - use premium
    RESEARCH = "research"  # Data aggregation, synthesis - use mid-tier
    BACKEND = "backend"  # Internal processing, extraction - use budget
    ADMIN = "admin"  # Admin dashboards, internal summaries - use budget


class ModelTier(Enum):
    """Model quality tiers"""
    FLAGSHIP = "flagship"  # GPT-5, Claude Opus - absolute best
    PREMIUM = "premium"  # GPT-4o, Claude Sonnet, Gemini Pro - excellent
    MID_TIER = "mid_tier"  # Gemini Flash, Claude Haiku - good quality, lower cost
    BUDGET = "budget"  # Llama, DeepSeek - adequate for backend


# Model Selection Matrix
# Format: {stage_name: {"task_type": TaskType, "model": "model_id", "reason": "why"}}

MODEL_SELECTION: Dict[str, Dict[str, Any]] = {
    # Stage 1: Data Extraction (Backend task)
    "extraction": {
        "task_type": TaskType.BACKEND,
        "model_tier": ModelTier.BUDGET,
        "primary_model": "google/gemini-2.5-flash-preview-09-2025",
        "fallback_model": "meta-llama/llama-4-scout:free",
        "reason": "Simple extraction task - Gemini Flash is fast, cheap, excellent at structured data",
        "context_window": "256k",
        "cost_per_m": {"input": 0.075, "output": 0.30}
    },

    # Stage 2: Gap Analysis (Backend task)
    "gap_analysis": {
        "task_type": TaskType.BACKEND,
        "model_tier": ModelTier.BUDGET,
        "primary_model": "google/gemini-2.5-flash-preview-09-2025",
        "fallback_model": "meta-llama/llama-4-scout:free",
        "reason": "Identifies missing data points - Flash handles logic well, ultra-cheap",
        "context_window": "256k",
        "cost_per_m": {"input": 0.075, "output": 0.30}
    },

    # Stage 3: Strategic Analysis (CLIENT-FACING - CRITICAL!)
    "strategy": {
        "task_type": TaskType.CLIENT_FACING,
        "model_tier": ModelTier.PREMIUM,
        "primary_model": "google/gemini-2.5-pro-preview",
        "fallback_model": "anthropic/claude-3.5-sonnet",
        "reason": "CLIENT DELIVERABLE - Applies Porter, SWOT, BCG frameworks. Gemini Pro avoids GPT-4o content policy issues.",
        "context_window": "1M",
        "cost_per_m": {"input": 1.25, "output": 5.00},
        "quality_critical": True
    },

    # Stage 4: Competitive Intelligence (Important research)
    "competitive": {
        "task_type": TaskType.RESEARCH,
        "model_tier": ModelTier.PREMIUM,
        "primary_model": "google/gemini-2.5-pro-preview",
        "fallback_model": "anthropic/claude-3.5-sonnet",
        "reason": "Competitive analysis matters to clients - Gemini Pro excellent at structured comparison matrices",
        "context_window": "1M",
        "cost_per_m": {"input": 1.25, "output": 5.00},
        "quality_critical": True
    },

    # Stage 5: Risk Scoring (Strategic reasoning)
    "risk_scoring": {
        "task_type": TaskType.STRATEGIC,
        "model_tier": ModelTier.PREMIUM,
        "primary_model": "anthropic/claude-3.5-sonnet",
        "fallback_model": "openai/gpt-4o",
        "reason": "Risk assessment requires deep reasoning - Claude excels at logical chaining and probability assessment",
        "context_window": "200k",
        "cost_per_m": {"input": 3.00, "output": 15.00},
        "quality_critical": True
    },

    # Stage 6: Executive Polish (CLIENT-FACING)
    "polish": {
        "task_type": TaskType.CLIENT_FACING,
        "model_tier": ModelTier.PREMIUM,
        "primary_model": "anthropic/claude-3.5-sonnet",
        "fallback_model": "openai/gpt-4o",
        "reason": "Final client deliverable - Claude Sonnet writes beautifully, maintains professional tone",
        "context_window": "200k",
        "cost_per_m": {"input": 3.00, "output": 15.00},
        "quality_critical": True
    },

    # Special: Admin Dashboard Intelligence (Internal only)
    "admin_intelligence": {
        "task_type": TaskType.ADMIN,
        "model_tier": ModelTier.MID_TIER,
        "primary_model": "google/gemini-2.5-flash-preview-09-2025",
        "fallback_model": "meta-llama/llama-4-scout:free",
        "reason": "Internal admin dashboard - Flash is fast and cheap, good enough for internal use",
        "context_window": "256k",
        "cost_per_m": {"input": 0.075, "output": 0.30}
    },

    # Special: Chat with Reports (Mid-tier - semi-client-facing)
    "chat": {
        "task_type": TaskType.RESEARCH,
        "model_tier": ModelTier.MID_TIER,
        "primary_model": "anthropic/claude-haiku-4.5",
        "fallback_model": "google/gemini-2.5-flash-preview-09-2025",
        "reason": "Q&A on reports - Haiku is fast, cheap, conversational. Not final deliverable.",
        "context_window": "128k",
        "cost_per_m": {"input": 0.25, "output": 1.25}
    },

    # Special: Report Editing (CLIENT-FACING)
    "editing": {
        "task_type": TaskType.CLIENT_FACING,
        "model_tier": ModelTier.PREMIUM,
        "primary_model": "anthropic/claude-3.5-sonnet",
        "fallback_model": "openai/gpt-4o",
        "reason": "Edits go to client - Claude Sonnet maintains quality and tone",
        "context_window": "200k",
        "cost_per_m": {"input": 3.00, "output": 15.00},
        "quality_critical": True
    }
}


# Alternative Models for Different Use Cases
ALTERNATIVE_MODELS: Dict[str, Dict[str, Any]] = {
    # If GPT-5 becomes available, use for strategy
    "gpt5": {
        "id": "openai/gpt-5",
        "use_for": ["strategy", "polish"],
        "reason": "Absolute best for client-facing strategic analysis",
        "cost_per_m": {"input": 5.00, "output": 15.00}  # Estimated
    },

    # Grok for massive context needs
    "grok_reasoning": {
        "id": "xai/grok-4-reasoning",
        "use_for": ["competitive", "research"],
        "reason": "2M context window for huge data synthesis",
        "cost_per_m": {"input": 2.00, "output": 10.00}  # Estimated
    },

    # Perplexity for live research
    "perplexity": {
        "id": "perplexity/pplx-70b",
        "use_for": ["gap_analysis", "research"],
        "reason": "Live web data, great for latest market research",
        "cost_per_m": {"input": 1.00, "output": 3.00}  # Estimated
    },

    # DeepSeek for mass backend jobs
    "deepseek": {
        "id": "deepseek-ai/deepseek-llm-r1",
        "use_for": ["extraction", "admin_intelligence"],
        "reason": "Ultra-cheap for non-critical backend tasks",
        "cost_per_m": {"input": 0.01, "output": 0.03}  # Very cheap
    }
}


def get_model_for_stage(stage_name: str, use_premium: bool = True) -> str:
    """
    Get the appropriate model for a given stage

    Args:
        stage_name: Name of the pipeline stage
        use_premium: If False, downgrade to budget models (for cost-sensitive operations)

    Returns:
        Model ID string for OpenRouter API
    """
    stage_config = MODEL_SELECTION.get(stage_name)

    if not stage_config:
        # Default to Gemini Flash for unknown stages
        return "google/gemini-2.5-flash-preview-09-2025"

    # If premium disabled and not quality-critical, use budget
    if not use_premium and not stage_config.get("quality_critical"):
        return stage_config.get("fallback_model", stage_config["primary_model"])

    return stage_config["primary_model"]


def get_stage_config(stage_name: str) -> Dict[str, Any]:
    """Get full configuration for a stage"""
    return MODEL_SELECTION.get(stage_name, {})


def get_estimated_cost(stage_name: str, input_tokens: int, output_tokens: int) -> float:
    """
    Estimate cost for a stage given token counts

    Args:
        stage_name: Pipeline stage
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Estimated cost in USD
    """
    config = MODEL_SELECTION.get(stage_name)
    if not config or "cost_per_m" not in config:
        return 0.0

    cost_config = config["cost_per_m"]
    input_cost = (input_tokens / 1_000_000) * cost_config["input"]
    output_cost = (output_tokens / 1_000_000) * cost_config["output"]

    return input_cost + output_cost


def calculate_pipeline_cost_estimate() -> Dict[str, Any]:
    """
    Calculate estimated cost for full pipeline

    Assumes typical token usage:
    - Backend stages: 20K in, 3K out
    - Strategic stages: 30K in, 4K out
    """
    costs = {}
    total_cost = 0.0

    # Typical token usage per stage type
    token_usage = {
        TaskType.BACKEND: {"input": 20_000, "output": 3_000},
        TaskType.RESEARCH: {"input": 25_000, "output": 3_500},
        TaskType.STRATEGIC: {"input": 30_000, "output": 4_000},
        TaskType.CLIENT_FACING: {"input": 30_000, "output": 4_000}
    }

    for stage_name, config in MODEL_SELECTION.items():
        if stage_name in ["admin_intelligence", "chat", "editing"]:
            continue  # Skip special stages

        task_type = config["task_type"]
        tokens = token_usage[task_type]

        cost = get_estimated_cost(stage_name, tokens["input"], tokens["output"])
        costs[stage_name] = {
            "model": config["primary_model"],
            "task_type": task_type.value,
            "estimated_cost": round(cost, 4)
        }
        total_cost += cost

    return {
        "stages": costs,
        "total_cost": round(total_cost, 4),
        "breakdown": {
            "backend": sum(c["estimated_cost"] for c in costs.values() if c["task_type"] == "backend"),
            "research": sum(c["estimated_cost"] for c in costs.values() if c["task_type"] == "research"),
            "strategic": sum(c["estimated_cost"] for c in costs.values() if c["task_type"] == "strategic"),
            "client_facing": sum(c["estimated_cost"] for c in costs.values() if c["task_type"] == "client_facing")
        }
    }


# Print cost estimate on import (for dev reference)
if __name__ == "__main__":
    import json
    estimate = calculate_pipeline_cost_estimate()
    print("\n=== PIPELINE COST ESTIMATE ===")
    print(json.dumps(estimate, indent=2))
    print(f"\nTotal estimated cost per analysis: ${estimate['total_cost']}")
    print("\nBreakdown by type:")
    for task_type, cost in estimate['breakdown'].items():
        print(f"  {task_type}: ${cost:.4f}")
