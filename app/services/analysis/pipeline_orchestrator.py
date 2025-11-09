"""
Pipeline Orchestrator - Main Multi-Stage Analysis Coordinator

Coordinates all 6 stages of the analysis pipeline with caching, logging,
and quality assessment.
"""

import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime

from app.services.analysis.cache_wrapper import run_stage_with_cache
from app.services.analysis.stages.stage1_extraction import stage1_extract_data
from app.services.analysis.stages.stage2_gap_analysis import stage2_gap_analysis_and_followup
from app.services.analysis.stages.stage3_strategy import stage3_strategic_analysis
from app.services.analysis.stages.stage4_competitive import stage4_competitive_matrix
from app.services.analysis.stages.stage5_risk_priority import stage5_risk_and_priority
from app.services.analysis.stages.stage6_polish import stage6_executive_polish

from app.core.cache import generate_content_hash
from app.core.model_config import get_model_for_stage, get_estimated_cost
from app.utils.logger import AnalysisLogger
from app.utils.validation import assess_data_quality

logger = logging.getLogger(__name__)

# Load model configurations
MODEL_EXTRACTION = get_model_for_stage("extraction")
MODEL_GAP_ANALYSIS = get_model_for_stage("gap_analysis")
MODEL_STRATEGY = get_model_for_stage("strategy")
MODEL_COMPETITIVE = get_model_for_stage("competitive")
MODEL_RISK_SCORING = get_model_for_stage("risk_scoring")
MODEL_POLISH = get_model_for_stage("polish")


async def generate_multistage_analysis(
    company: str,
    industry: str,
    website: Optional[str],
    challenge: Optional[str],
    apify_data: Optional[Dict[str, Any]] = None,
    perplexity_data: Optional[Dict[str, Any]] = None,
    run_all_stages: bool = True,
    perplexity_service = None,
    submission_id: int = 0
) -> Dict[str, Any]:
    """
    Main orchestrator for multi-stage analysis pipeline

    Args:
        company: Company name
        industry: Industry sector
        website: Company website
        challenge: Business challenge
        apify_data: Web scraping data
        perplexity_data: Initial Perplexity research
        run_all_stages: If True, run all 6 stages. If False, run only core stages (1,3,6)
        perplexity_service: Perplexity service instance for follow-up research
        submission_id: Submission ID for structured logging

    Returns: Complete strategic analysis with metadata
    """

    start_time = datetime.now()
    logger.info(f"[MULTISTAGE] Starting {'FULL' if run_all_stages else 'CORE'} analysis for {company} in {industry}")

    # Create comprehensive logger for this analysis
    analysis_logger = AnalysisLogger(submission_id, company)

    try:
        # ===== STAGE 1: Extract structured data (CHEAP - Gemini Flash) =====
        analysis_logger.log_stage_start("extraction", MODEL_EXTRACTION, "Extract structured data from all sources")
        stage1_start = time.time()

        # Prepare cache input (deterministic hash of all inputs)
        stage1_input = {
            "company": company,
            "industry": industry,
            "website": website,
            "challenge": challenge,
            "apify_hash": generate_content_hash(apify_data) if apify_data else None,
            "perplexity_hash": generate_content_hash(perplexity_data) if perplexity_data else None
        }

        extracted_data = await run_stage_with_cache(
            stage_name="extraction",
            stage_function=stage1_extract_data,
            company=company,
            industry=industry,
            input_data=stage1_input,
            estimated_cost=0.002,  # ~$0.002 per Stage 1 call
            # stage_kwargs:
            website=website,
            challenge=challenge,
            apify_data=apify_data,
            perplexity_data=perplexity_data
        )

        # Log stage completion
        stage1_duration = time.time() - stage1_start
        stage1_usage = extracted_data.get("_usage_stats", {"input_tokens": 0, "output_tokens": 0})
        stage1_cost = get_estimated_cost("extraction", stage1_usage["input_tokens"], stage1_usage["output_tokens"])
        analysis_logger.log_stage_complete(
            "extraction",
            stage1_duration,
            stage1_usage["input_tokens"],
            stage1_usage["output_tokens"],
            stage1_cost,
            success=True
        )

        stages_completed = ["extraction"]
        models_used = {"stage1_extraction": MODEL_EXTRACTION}
        follow_up_data = {}

        # ===== DATA QUALITY ASSESSMENT =====
        tier, tier_label, tier_recommendations = assess_data_quality(
            website=bool(website),
            apify_success=bool(apify_data and apify_data.get('data')),
            perplexity_success=bool(perplexity_data and perplexity_data.get('research_completed')),
            documents_provided=False,  # Could check extracted_data for documents
            financial_data=bool(extracted_data.get('company_info', {}).get('financial_data'))
        )

        logger.info(f"[MULTISTAGE] Data quality tier: {tier_label} ({tier})")
        if tier_recommendations:
            logger.info(f"[MULTISTAGE] Recommendations: {tier_recommendations}")

        # Define enabled sections based on quality tier
        sections_config = {
            "legendary": ["all"],
            "full": ["all"],
            "good": ["pestel", "porter", "swot", "blue_ocean", "positioning", "recommendations", "okrs", "scenarios", "roadmap"],
            "partial": ["pestel", "porter", "swot", "positioning", "recommendations", "roadmap"],  # NO TAM/SAM/SOM, NO OKRs
            "minimal": ["pestel_brief", "swot", "positioning", "recommendations"]  # NO TAM/SAM/SOM, NO DETAILED FRAMEWORKS
        }

        enabled_sections = sections_config.get(tier, sections_config["minimal"])
        logger.info(f"[MULTISTAGE] Enabled sections for {tier}: {enabled_sections}")

        # ===== STAGE 2: Gap analysis + follow-up (OPTIONAL) =====
        if run_all_stages and perplexity_service:
            try:
                analysis_logger.log_stage_start("gap_analysis", MODEL_GAP_ANALYSIS, "Identify data gaps and run follow-up research")
                stage2_start = time.time()

                stage2_input = {
                    "company": company,
                    "industry": industry,
                    "extracted_data_hash": generate_content_hash(extracted_data)
                }

                follow_up_data = await run_stage_with_cache(
                    stage_name="gap_analysis",
                    stage_function=stage2_gap_analysis_and_followup,
                    company=company,
                    industry=industry,
                    input_data=stage2_input,
                    estimated_cost=0.005,  # ~$0.005 per Stage 2 call (includes Perplexity)
                    # stage_kwargs:
                    extracted_data=extracted_data,
                    perplexity_service=perplexity_service
                )

                # Log stage completion
                stage2_duration = time.time() - stage2_start
                stage2_usage = follow_up_data.get("_usage_stats", {"input_tokens": 0, "output_tokens": 0})
                stage2_cost = get_estimated_cost("gap_analysis", stage2_usage["input_tokens"], stage2_usage["output_tokens"])
                analysis_logger.log_stage_complete(
                    "gap_analysis",
                    stage2_duration,
                    stage2_usage["input_tokens"],
                    stage2_usage["output_tokens"],
                    stage2_cost,
                    success=True
                )

                stages_completed.append("gap_analysis_followup")
                models_used["stage2_gap_analysis"] = MODEL_GAP_ANALYSIS
            except Exception as e:
                logger.warning(f"[MULTISTAGE] Stage 2 failed (non-critical): {str(e)}")
                analysis_logger.log_stage_complete("gap_analysis", 0, 0, 0, 0, success=False, error=str(e))
                follow_up_data = {"follow_up_completed": False}

        # ===== STAGE 3: Strategic frameworks (EXPENSIVE - GPT-4o) =====
        analysis_logger.log_stage_start("strategy", MODEL_STRATEGY, "Apply strategic frameworks (Porter, SWOT, BCG, etc.)")
        stage3_start = time.time()

        stage3_input = {
            "company": company,
            "industry": industry,
            "challenge": challenge,
            "extracted_data_hash": generate_content_hash(extracted_data),
            "enabled_sections": enabled_sections,
            "data_quality_tier": tier
        }

        strategic_analysis = await run_stage_with_cache(
            stage_name="strategy",
            stage_function=stage3_strategic_analysis,
            company=company,
            industry=industry,
            input_data=stage3_input,
            estimated_cost=0.15,  # ~$0.15 per Stage 3 call (MOST EXPENSIVE!)
            # stage_kwargs:
            challenge=challenge,
            extracted_data=extracted_data,
            enabled_sections=enabled_sections,
            data_quality_tier=tier
        )

        # Log stage completion
        stage3_duration = time.time() - stage3_start
        stage3_usage = strategic_analysis.get("_usage_stats", {"input_tokens": 0, "output_tokens": 0})
        stage3_cost = get_estimated_cost("strategy", stage3_usage["input_tokens"], stage3_usage["output_tokens"])
        analysis_logger.log_stage_complete(
            "strategy",
            stage3_duration,
            stage3_usage["input_tokens"],
            stage3_usage["output_tokens"],
            stage3_cost,
            success=True
        )

        stages_completed.append("strategic_analysis")
        models_used["stage3_strategy"] = MODEL_STRATEGY

        competitive_intel = {}
        risk_priority = {}

        # ===== STAGE 4: Competitive matrix (OPTIONAL) =====
        if run_all_stages:
            try:
                analysis_logger.log_stage_start("competitive", MODEL_COMPETITIVE, "Generate competitive intelligence matrix")
                stage4_start = time.time()

                stage4_input = {
                    "company": company,
                    "industry": industry,
                    "extracted_data_hash": generate_content_hash(extracted_data),
                    "strategic_analysis_hash": generate_content_hash(strategic_analysis)
                }

                competitive_intel = await run_stage_with_cache(
                    stage_name="competitive",
                    stage_function=stage4_competitive_matrix,
                    company=company,
                    industry=industry,
                    input_data=stage4_input,
                    estimated_cost=0.05,  # ~$0.05 per Stage 4 call
                    # stage_kwargs:
                    extracted_data=extracted_data,
                    strategic_analysis=strategic_analysis
                )

                # Log stage completion
                stage4_duration = time.time() - stage4_start
                stage4_usage = competitive_intel.get("_usage_stats", {"input_tokens": 0, "output_tokens": 0})
                stage4_cost = get_estimated_cost("competitive", stage4_usage["input_tokens"], stage4_usage["output_tokens"])
                analysis_logger.log_stage_complete(
                    "competitive",
                    stage4_duration,
                    stage4_usage["input_tokens"],
                    stage4_usage["output_tokens"],
                    stage4_cost,
                    success=True
                )

                stages_completed.append("competitive_matrix")
                models_used["stage4_competitive"] = MODEL_COMPETITIVE
            except Exception as e:
                logger.warning(f"[MULTISTAGE] Stage 4 failed (non-critical): {str(e)}")
                analysis_logger.log_stage_complete("competitive", 0, 0, 0, 0, success=False, error=str(e))
                competitive_intel = {}

        # ===== STAGE 5: Risk scoring + priority (OPTIONAL) =====
        if run_all_stages:
            try:
                analysis_logger.log_stage_start("risk_scoring", MODEL_RISK_SCORING, "Quantify risks and prioritize recommendations")
                stage5_start = time.time()

                stage5_input = {
                    "company": company,
                    "strategic_analysis_hash": generate_content_hash(strategic_analysis)
                }

                risk_priority = await run_stage_with_cache(
                    stage_name="risk_scoring",
                    stage_function=stage5_risk_and_priority,
                    company=company,
                    industry=industry,
                    input_data=stage5_input,
                    estimated_cost=0.04,  # ~$0.04 per Stage 5 call
                    # stage_kwargs:
                    strategic_analysis=strategic_analysis
                )

                # Log stage completion
                stage5_duration = time.time() - stage5_start
                stage5_usage = risk_priority.get("_usage_stats", {"input_tokens": 0, "output_tokens": 0})
                stage5_cost = get_estimated_cost("risk_scoring", stage5_usage["input_tokens"], stage5_usage["output_tokens"])
                analysis_logger.log_stage_complete(
                    "risk_scoring",
                    stage5_duration,
                    stage5_usage["input_tokens"],
                    stage5_usage["output_tokens"],
                    stage5_cost,
                    success=True
                )

                stages_completed.append("risk_priority_scoring")
                models_used["stage5_risk"] = MODEL_RISK_SCORING
            except Exception as e:
                logger.warning(f"[MULTISTAGE] Stage 5 failed (non-critical): {str(e)}")
                analysis_logger.log_stage_complete("risk_scoring", 0, 0, 0, 0, success=False, error=str(e))
                risk_priority = {}

        # ===== STAGE 6: Executive polish (CHEAP - Claude Haiku) =====
        try:
            analysis_logger.log_stage_start("polish", MODEL_POLISH, "Polish analysis for executive readability")
            stage6_start = time.time()

            stage6_input = {
                "company": company,
                "strategic_analysis_hash": generate_content_hash(strategic_analysis)
            }

            final_analysis = await run_stage_with_cache(
                stage_name="polish",
                stage_function=stage6_executive_polish,
                company=company,
                industry=industry,
                input_data=stage6_input,
                estimated_cost=0.01,  # ~$0.01 per Stage 6 call
                # stage_kwargs:
                strategic_analysis=strategic_analysis
            )

            # Log stage completion
            stage6_duration = time.time() - stage6_start
            stage6_usage = final_analysis.get("_usage_stats", {"input_tokens": 0, "output_tokens": 0})
            stage6_cost = get_estimated_cost("polish", stage6_usage["input_tokens"], stage6_usage["output_tokens"])
            analysis_logger.log_stage_complete(
                "polish",
                stage6_duration,
                stage6_usage["input_tokens"],
                stage6_usage["output_tokens"],
                stage6_cost,
                success=True
            )

            stages_completed.append("executive_polish")
            models_used["stage6_polish"] = MODEL_POLISH
        except Exception as e:
            logger.warning(f"[MULTISTAGE] Stage 6 failed (non-critical): {str(e)}")
            analysis_logger.log_stage_complete("polish", 0, 0, 0, 0, success=False, error=str(e))
            # Use unpolished analysis if polish fails
            final_analysis = strategic_analysis
            logger.info("[MULTISTAGE] Using unpolished strategic analysis as fallback")

        # ===== MERGE ADVANCED ANALYSIS =====
        # Add competitive intel, risk analysis, and follow-up research to final output
        if competitive_intel:
            final_analysis["inteligencia_competitiva"] = competitive_intel

        if risk_priority:
            final_analysis["analise_risco_prioridade"] = risk_priority

        if follow_up_data and follow_up_data.get("follow_up_completed"):
            final_analysis["pesquisa_adicional"] = follow_up_data

        # ===== ADD METADATA =====
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Get comprehensive logging summary
        log_summary = analysis_logger.log_summary()

        final_analysis["_metadata"] = {
            "generated_at": end_time.isoformat(),
            "processing_time_seconds": processing_time,
            "pipeline": "multi-stage-v2-full" if run_all_stages else "multi-stage-v2-core",
            "stages_completed": stages_completed,
            "models_used": models_used,
            "framework_version": "10XMentorAI v2.2 Complete",
            "quality_tier": "LEGENDARY" if run_all_stages else "Professional",
            "used_perplexity": perplexity_data is not None and perplexity_data.get("research_completed", False),
            "data_gaps_identified": len(extracted_data.get("data_gaps", [])),
            "data_gaps_filled": follow_up_data.get("data_gaps_filled", 0) if follow_up_data else 0,
            "total_cost_actual_usd": log_summary["total_cost_usd"],  # ACTUAL cost from logger
            "total_tokens": log_summary["total_tokens"],
            "total_input_tokens": log_summary["total_input_tokens"],
            "total_output_tokens": log_summary["total_output_tokens"],
            "logging_summary": log_summary  # Full structured logging data
        }

        logger.info(f"[MULTISTAGE] ✅ {len(stages_completed)}-stage analysis complete in {processing_time:.1f}s")
        logger.info(f"[MULTISTAGE] ✅ Actual cost: ${log_summary['total_cost_usd']:.4f} ({log_summary['total_tokens']} tokens)")
        return final_analysis

    except Exception as e:
        logger.error(f"[MULTISTAGE] Pipeline failed: {str(e)}")
        raise Exception(f"Multi-stage analysis failed: {str(e)}")

