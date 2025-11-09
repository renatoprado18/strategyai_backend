"""
Stage 2: Gap Analysis + Follow-Up Research
Model: Gemini Flash for analysis, Perplexity for follow-up queries
Cost: ~$0.001 (Gemini) + $0.04 (Perplexity)
"""

import json
import logging
from typing import Dict, Any

from app.services.analysis.llm_client import call_llm_with_retry
from app.core.model_config import get_model_for_stage
from app.core.constants import (
    STAGE2_MAX_TOKENS_ANALYSIS,
    STAGE2_MAX_TOKENS_FOLLOWUP,
    TEMPERATURE_FACTUAL
)

logger = logging.getLogger(__name__)

MODEL_GAP_ANALYSIS = get_model_for_stage("gap_analysis")


async def stage2_gap_analysis_and_followup(
    company: str,
    industry: str,
    extracted_data: Dict[str, Any],
    perplexity_service
) -> Dict[str, Any]:
    """
    Stage 2: Identify data gaps and run targeted follow-up research
    Model: Gemini Flash for analysis, Perplexity for follow-up queries
    Cost: ~$0.001 (Gemini) + $0.04 (Perplexity)
    """

    logger.info("[STAGE 2] Analyzing data gaps and generating follow-up queries...")

    data_gaps = extracted_data.get("data_gaps", [])

    if not data_gaps or len(data_gaps) == 0:
        logger.info("[STAGE 2] No significant data gaps identified, skipping follow-up")
        return {
            "follow_up_completed": False,
            "follow_up_research": {},
            "data_gaps_filled": 0,
            "_usage_stats": {"input_tokens": 0, "output_tokens": 0}
        }

    # Generate targeted follow-up queries
    prompt = f"""Based on these data gaps for {company} in {industry}, generate 2-3 targeted research queries:

Data Gaps Identified:
{json.dumps(data_gaps, indent=2, ensure_ascii=False)}

Current Data:
{json.dumps(extracted_data, indent=2, ensure_ascii=False)[:2000]}

Generate specific, actionable research queries that would fill the most important gaps.

**CRITICAL - SOURCE ATTRIBUTION:**
- All follow-up research findings MUST include sources
- Format quantitative claims as: "R$ X milhões (fonte: Relatório Y)" or "15% (fonte: Perplexity Research)"
- If no concrete data available: Mark as "Dados insuficientes" or "Estimativa baseada em análise de mercado"

Return JSON:

{{
  "follow_up_queries": [
    "Specific query 1 that addresses gap X",
    "Specific query 2 that addresses gap Y",
    "Specific query 3 (if needed)"
  ],
  "priority_gaps": [
    "Most critical gap to fill",
    "Second priority gap"
  ]
}}

Focus on high-impact gaps (competitor data, market sizing, financial metrics).
"""

    system_prompt = "You are a research analyst. Generate targeted queries to fill data gaps. Output JSON only."

    response, usage_stats = await call_llm_with_retry(
        stage_name="STAGE 2",
        model=MODEL_GAP_ANALYSIS,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=TEMPERATURE_FACTUAL,
        max_tokens=STAGE2_MAX_TOKENS_ANALYSIS
    )

    gap_analysis = json.loads(response)
    follow_up_queries = gap_analysis.get("follow_up_queries", [])[:3]  # Max 3 queries

    if len(follow_up_queries) == 0:
        return {
            "follow_up_completed": False,
            "follow_up_research": {},
            "data_gaps_filled": 0,
            "_usage_stats": usage_stats
        }

    # Run follow-up research with Perplexity
    logger.info(f"[STAGE 2] Running {len(follow_up_queries)} follow-up research queries...")

    follow_up_results = {}
    for i, query in enumerate(follow_up_queries):
        try:
            result = await perplexity_service.call_perplexity(query, max_tokens=STAGE2_MAX_TOKENS_FOLLOWUP)
            if result:
                follow_up_results[f"followup_{i+1}"] = {
                    "query": query,
                    "research": result
                }
                logger.info(f"[STAGE 2] ✅ Follow-up {i+1} completed")
        except Exception as e:
            logger.warning(f"[STAGE 2] Follow-up {i+1} failed: {str(e)}")
            continue

    logger.info(f"[STAGE 2] ✅ Completed {len(follow_up_results)}/{len(follow_up_queries)} follow-up queries")

    return {
        "follow_up_completed": True,
        "follow_up_research": follow_up_results,
        "data_gaps_filled": len(follow_up_results),
        "priority_gaps": gap_analysis.get("priority_gaps", []),
        "_usage_stats": usage_stats
    }
