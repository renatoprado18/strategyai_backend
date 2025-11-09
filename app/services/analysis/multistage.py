"""
Multi-Stage Analysis Pipeline - Compatibility Wrapper
Cost-optimized + Quality-maximized architecture

This module provides backward compatibility by importing from the new modular structure.

Stage 1: Data Extraction (Gemini Flash - CHEAP)
Stage 2: Gap Analysis + Follow-Up Research (Gemini Flash + Perplexity)
Stage 3: Strategic Frameworks (GPT-4o - EXPENSIVE but worth it)
Stage 4: Competitive Matrix (Gemini Pro - Good at structured data)
Stage 5: Risk Scoring + Priority (Claude 3.5 Sonnet - Best reasoning)
Stage 6: Executive Polish (Claude Haiku - Cheap + good writing)
"""

# Import all stage functions for backward compatibility
from app.services.analysis.stages.stage1_extraction import stage1_extract_data
from app.services.analysis.stages.stage2_gap_analysis import stage2_gap_analysis_and_followup
from app.services.analysis.stages.stage3_strategy import stage3_strategic_analysis
from app.services.analysis.stages.stage4_competitive import stage4_competitive_matrix
from app.services.analysis.stages.stage5_risk_priority import stage5_risk_and_priority
from app.services.analysis.stages.stage6_polish import stage6_executive_polish

# Import LLM client functions
from app.services.analysis.llm_client import call_llm, call_llm_with_retry

# Import cache wrapper
from app.services.analysis.cache_wrapper import run_stage_with_cache

# Import main orchestrator
from app.services.analysis.pipeline_orchestrator import generate_multistage_analysis

# Import model configurations for backward compatibility
from app.core.model_config import (
    get_model_for_stage,
    MODEL_SELECTION,
    get_stage_config,
    get_estimated_cost
)

# Export all functions for backward compatibility
__all__ = [
    # Stage functions
    'stage1_extract_data',
    'stage2_gap_analysis_and_followup',
    'stage3_strategic_analysis',
    'stage4_competitive_matrix',
    'stage5_risk_and_priority',
    'stage6_executive_polish',
    # LLM functions
    'call_llm',
    'call_llm_with_retry',
    # Cache function
    'run_stage_with_cache',
    # Main orchestrator
    'generate_multistage_analysis',
    # Model config functions
    'get_model_for_stage',
    'MODEL_SELECTION',
    'get_stage_config',
    'get_estimated_cost',
]

# Constants for backward compatibility
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
TIMEOUT = 120.0
MAX_RETRIES = 3

# Load models from smart configuration
MODEL_EXTRACTION = get_model_for_stage("extraction")
MODEL_GAP_ANALYSIS = get_model_for_stage("gap_analysis")
MODEL_STRATEGY = get_model_for_stage("strategy")
MODEL_COMPETITIVE = get_model_for_stage("competitive")
MODEL_RISK_SCORING = get_model_for_stage("risk_scoring")
MODEL_POLISH = get_model_for_stage("polish")

# Test function (kept for backward compatibility)
async def test_multistage():
    """Test the multi-stage pipeline"""
    import asyncio
    import json

    try:
        result = await generate_multistage_analysis(
            company="TechStart Brasil",
            industry="Tecnologia",
            website="https://techstart.com.br",
            challenge="Crescer de R$ 100k MRR para R$ 500k MRR em 12 meses",
            apify_data=None,
            perplexity_data=None
        )

        print("[OK] Multi-stage analysis completed!")
        print(json.dumps(result.get("_metadata", {}), indent=2))

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_multistage())
