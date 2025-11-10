"""
Background Task Processing & Progress Tracking
Handles asynchronous analysis processing with real-time progress updates
"""
import asyncio
import json
import logging
import time
from typing import Dict, List
from datetime import datetime

from app.core.database import (
    get_submission,
    update_submission_status,
    update_submission_processing_state,
)
from app.services.analysis.multistage import generate_multistage_analysis
from app.services.analysis.enhanced import validate_enhanced_analysis
from app.services.analysis.confidence_scorer import calculate_confidence_score
from app.services.data.apify import gather_all_apify_data
from app.services.data.perplexity import comprehensive_market_research
import app.services.data.perplexity as perplexity_service
from app.core.cache import get_cached_analysis, cache_analysis_result

logger = logging.getLogger(__name__)


# ============================================================================
# PROGRESS TRACKING FOR SSE STREAMING
# ============================================================================

# In-memory progress tracker (maps submission_id -> progress updates)
_progress_tracker: Dict[int, List[Dict]] = {}


def emit_progress(submission_id: int, stage: str, message: str, progress: int):
    """
    Emit progress update for SSE streaming

    Args:
        submission_id: The submission being processed
        stage: Current stage (e.g., "data_gathering", "ai_analysis", "completed")
        message: Human-readable progress message
        progress: Progress percentage (0-100)
    """
    if submission_id not in _progress_tracker:
        _progress_tracker[submission_id] = []

    update = {
        "stage": stage,
        "message": message,
        "progress": progress,
        "timestamp": datetime.utcnow().isoformat()
    }

    _progress_tracker[submission_id].append(update)
    logger.info(f"[PROGRESS] Submission {submission_id}: {progress}% - {message}")


def get_progress_updates(submission_id: int) -> List[Dict]:
    """Get all progress updates for a submission"""
    return _progress_tracker.get(submission_id, [])


def clear_progress(submission_id: int):
    """Clear progress tracking for a submission (after completion)"""
    if submission_id in _progress_tracker:
        del _progress_tracker[submission_id]


# ============================================================================
# BACKGROUND TASK: Process AI Analysis with Progress Tracking
# ============================================================================

async def process_analysis_task(
    submission_id: int,
    force_regenerate: bool = False,
    enrichment_data: dict = None
):
    """
    Background task to generate AI analysis with Apify enrichment

    Args:
        submission_id: ID of the submission to process
        force_regenerate: If True, bypass analysis cache and force fresh AI generation
                         (still uses institutional memory cache for external data)
        enrichment_data: Optional cached data from Phase 1 (form enrichment).
                        If provided, skip re-scraping and use this data instead.
    """
    try:
        # Get submission details
        submission = await get_submission(submission_id)
        if not submission:
            logger.error(f"[ERROR] Submission {submission_id} not found")
            return

        # Log whether we're reusing Phase 1 data
        if enrichment_data:
            logger.info(
                f"[PROCESSING] Processing analysis for submission {submission_id} (REUSING Phase 1 data)",
                extra={
                    "component": "background_tasks",
                    "submission_id": submission_id,
                    "reusing_enrichment": True,
                    "has_layer1": bool(enrichment_data.get("layer1_data")),
                    "has_layer2": bool(enrichment_data.get("layer2_data")),
                    "has_layer3": bool(enrichment_data.get("layer3_data"))
                }
            )
        else:
            logger.info(f"[PROCESSING] Processing analysis for submission {submission_id}...")

        # Progress: Start - Update to 'queued' state
        await update_submission_processing_state(
            submission_id=submission_id,
            processing_state='queued'
        )
        emit_progress(submission_id, "initializing", f"Iniciando análise para {submission['company']}", 0)

        # Step 1: Apify data gathering DISABLED (too slow, Perplexity covers 90% of use cases)
        # TODO: Re-enable when we have parallel execution or faster scraping
        logger.info(f"[APIFY] DISABLED - Skipping Apify data gathering (using Perplexity only)")
        await update_submission_processing_state(
            submission_id=submission_id,
            processing_state='data_gathering'
        )
        emit_progress(submission_id, "data_gathering", "Preparando análise com pesquisa avançada de mercado", 10)
        apify_data = None
        data_quality = {
            "website_scraped": False,
            "competitors_found": 0,
            "trends_researched": False,
            "company_enriched": False,
            "linkedin_company_found": False,
            "linkedin_founder_found": False,
            "news_found": False,
            "social_media_found": False,
            "sources_succeeded": 0,
            "sources_failed": 8,
            "failed_sources": ["apify_disabled"],
            "quality_tier": "minimal",
            "apify_disabled": True
        }

        # Progress: Skipped Apify
        emit_progress(submission_id, "data_gathering", "Apify desabilitado - usando Perplexity para pesquisa de mercado", 30)

        # Step 1.5: Perplexity Deep Research
        logger.info(f"[PERPLEXITY] Starting comprehensive market research for {submission['company']}...")
        # deep_research also maps to 'data_gathering' state
        await update_submission_processing_state(
            submission_id=submission_id,
            processing_state='data_gathering'
        )
        emit_progress(submission_id, "deep_research", "Iniciando pesquisa avançada de mercado com IA (Perplexity)", 40)
        perplexity_data = None
        perplexity_success = False

        try:
            perplexity_data = await comprehensive_market_research(
                company=submission["company"],
                industry=submission["industry"],
                challenge=submission.get("challenge", "Expandir mercado e aumentar receita"),
                region="Brasil",
                specific_segment=None
            )

            perplexity_success = perplexity_data.get("research_completed", False)

            if perplexity_success:
                logger.info(f"[PERPLEXITY] ✅ Comprehensive research completed!")
                perplexity_sources = int(perplexity_data.get('success_rate', '0/5').split('/')[0])
                data_quality["perplexity_sources"] = perplexity_sources
                data_quality["sources_succeeded"] = perplexity_sources  # Only Perplexity now

                # Update quality tier - Perplexity only (5 sources)
                total_sources = 5  # 5 Perplexity sources (Apify disabled)
                total_succeeded = perplexity_sources
                completion_rate = total_succeeded / total_sources

                # Adjusted tiers for Perplexity-only analysis
                if completion_rate >= 0.80:  # 4-5 sources
                    data_quality["quality_tier"] = "legendary"
                elif completion_rate >= 0.60:  # 3 sources
                    data_quality["quality_tier"] = "full"
                elif completion_rate >= 0.40:  # 2 sources
                    data_quality["quality_tier"] = "good"
                elif completion_rate >= 0.20:  # 1 source
                    data_quality["quality_tier"] = "partial"
                else:
                    data_quality["quality_tier"] = "minimal"

                data_quality["data_completeness"] = f"{int(completion_rate * 100)}% (Perplexity only)"

        except Exception as e:
            logger.warning(f"[WARNING] Perplexity research failed: {str(e)}. Continuing with Apify data only...")
            perplexity_data = None

        # Progress: Deep research complete
        emit_progress(submission_id, "deep_research", "Pesquisa de mercado concluída! Iniciando geração de análise estratégica", 50)

        # Step 2: Check cache
        cached_analysis_result = None
        if not force_regenerate:
            logger.info(f"[CACHE] 🔍 Checking analysis cache for {submission['company']}...")
            cached_analysis_result = await get_cached_analysis(
                company=submission["company"],
                industry=submission["industry"],
                challenge=submission.get("challenge"),
                website=submission.get("website")
            )
        else:
            logger.info(f"[REGENERATE] 🔄 Force regenerate - bypassing analysis cache")

        if cached_analysis_result and cached_analysis_result.get("cache_hit") and not force_regenerate:
            # CACHE HIT
            analysis = cached_analysis_result["analysis"]
            processing_time = 0.1
            cost_saved = cached_analysis_result.get("cost_saved", 20)
            cache_age_hours = cached_analysis_result.get("cache_age_hours", 0)

            logger.info(f"[CACHE] 🎯💰 CACHE HIT! Saved ${cost_saved:.2f} (age: {cache_age_hours:.1f}h)")
            await update_submission_processing_state(
                submission_id=submission_id,
                processing_state='ai_analyzing'
            )
            emit_progress(submission_id, "ai_analysis", f"✨ Análise recuperada do cache (economia de ${cost_saved:.2f}!)", 60)

        else:
            # CACHE MISS - Generate new analysis
            if force_regenerate:
                logger.info(f"[REGENERATE] Generating fresh AI analysis")
            else:
                logger.info(f"[CACHE] ❌ Cache miss - generating new analysis")
            logger.info(f"[AI] 🚀 Generating strategic analysis for submission {submission_id}...")
            await update_submission_processing_state(
                submission_id=submission_id,
                processing_state='ai_analyzing'
            )
            emit_progress(submission_id, "ai_analysis", "Gerando análise estratégica com IA (pipeline de 6 etapas)", 60)

            start_time = time.time()

            # Generate analysis
            # If enrichment_data provided (Phase 1 cache), pass it along to avoid re-scraping
            analysis = await generate_multistage_analysis(
                company=submission["company"],
                industry=submission["industry"],
                website=submission.get("website"),
                challenge=submission.get("challenge"),
                apify_data=apify_data,
                perplexity_data=perplexity_data,
                enrichment_data=enrichment_data,  # NEW: Reuse Phase 1 data if available
                run_all_stages=True,
                perplexity_service=perplexity_service,
                submission_id=submission_id  # Pass submission ID for comprehensive logging
            )

            processing_time = time.time() - start_time

            # Get ACTUAL cost from analysis metadata (comprehensive logging tracks real token usage)
            # Smart 6-stage pipeline: Premium models for client work, budget for backend
            # - Stages 1-2 (backend): Gemini Flash (~$0.005)
            # - Stages 3-6 (client-facing): GPT-4o, Gemini Pro, Claude Sonnet (~$0.40)
            # Total: ~$0.41-0.47 per analysis - WORTH IT for quality client deliverables!
            actual_cost = analysis.get("_metadata", {}).get("total_cost_actual_usd", 0.41)
            estimated_cost = actual_cost  # Use actual cost for accurate tracking
            await cache_analysis_result(
                company=submission["company"],
                industry=submission["industry"],
                challenge=submission.get("challenge"),
                website=submission.get("website"),
                analysis_result=analysis,
                cost=estimated_cost,
                processing_time=processing_time
            )
            logger.info(f"[CACHE] ✅ Analysis cached - will save ${estimated_cost:.2f} on next request")

        # Add data disclaimer if needed
        if data_quality["quality_tier"] in ["partial", "minimal"]:
            disclaimer = f"Este relatório foi gerado com {data_quality['data_completeness']} dos dados disponíveis. "
            if data_quality["failed_sources"]:
                disclaimer += f"Fontes indisponíveis: {', '.join(data_quality['failed_sources'])}. "
            disclaimer += "A análise foi feita com base nas informações públicas disponíveis."
            if "_metadata" not in analysis:
                analysis["_metadata"] = {}
            analysis["_metadata"]["data_disclaimer"] = disclaimer

        # Extract processing metadata
        processing_meta = {
            "model": analysis.get("_metadata", {}).get("model_used", "gpt-4o"),
            "framework_version": analysis.get("_metadata", {}).get("framework_version", "10XMentorAI v2.0"),
            "processing_time_seconds": round(processing_time, 2),
            "generated_at": datetime.utcnow().isoformat(),
            "data_quality_tier": data_quality["quality_tier"],
            "apify_data": apify_data,
            "perplexity_research": perplexity_data if perplexity_success else None,
        }

        # Progress: AI analysis complete
        emit_progress(submission_id, "ai_analysis", f"Análise gerada! Processamento concluído em {processing_time:.1f}s", 90)

        # Convert to JSON strings
        report_json = json.dumps(analysis, ensure_ascii=False)
        data_quality_json = json.dumps(data_quality, ensure_ascii=False)
        processing_metadata_json = json.dumps(processing_meta, ensure_ascii=False)

        # Progress: Saving to database
        await update_submission_processing_state(
            submission_id=submission_id,
            processing_state='finalizing'
        )
        emit_progress(submission_id, "finalizing", "Salvando relatório no banco de dados", 95)

        # Update submission - now with completed state
        await update_submission_processing_state(
            submission_id=submission_id,
            processing_state='completed',
            user_status='ready',
            report_json=report_json,
            data_quality_json=data_quality_json,
            processing_metadata=processing_metadata_json,
            error_message=None,
        )

        logger.info(f"[OK] Analysis completed for submission {submission_id}")

        # Calculate confidence score
        try:
            logger.info(f"[CONFIDENCE] Calculating confidence score for submission {submission_id}...")
            submission_data = await get_submission(submission_id)
            confidence_score, confidence_breakdown = calculate_confidence_score(
                submission_data=submission_data,
                report_json=report_json,
                data_quality_json=data_quality_json,
                processing_metadata=processing_metadata_json,
            )

            # Add timestamp
            from datetime import timezone
            confidence_breakdown["calculated_at"] = datetime.now(timezone.utc).isoformat()

            # Update processing metadata with confidence
            processing_meta_with_confidence = json.loads(processing_metadata_json)
            processing_meta_with_confidence["confidence_score"] = confidence_score
            processing_meta_with_confidence["confidence_breakdown"] = confidence_breakdown

            # Save confidence (maintain completed state)
            await update_submission_processing_state(
                submission_id=submission_id,
                processing_state='completed',
                user_status='ready',
                report_json=report_json,
                data_quality_json=data_quality_json,
                processing_metadata=json.dumps(processing_meta_with_confidence, ensure_ascii=False),
            )

            logger.info(f"[CONFIDENCE] ✅ Confidence score: {confidence_score}/100")
        except Exception as conf_error:
            logger.warning(f"[WARNING] Confidence calculation failed: {conf_error}")

        # Progress: Complete
        emit_progress(submission_id, "completed", f"✅ Relatório concluído! Qualidade: {data_quality['quality_tier'].upper()}", 100)

    except Exception as e:
        error_message = str(e)
        logger.error(f"[ERROR] Analysis failed for submission {submission_id}: {error_message}", exc_info=True)

        # Progress: Error
        emit_progress(submission_id, "failed", f"❌ Erro: {error_message[:100]}", 0)

        # Update submission with failure
        await update_submission_processing_state(
            submission_id=submission_id,
            processing_state='failed',
            user_status='submitted',
            error_message=error_message,
        )


# ============================================================================
# PDF GENERATION BACKGROUND TASK
# ============================================================================

def generate_pdf_background(submission_id: int, submission_data: dict, report_json: dict):
    """
    Background task to generate PDF (synchronous function called from background_tasks.add_task)

    Args:
        submission_id: Submission ID
        submission_data: Submission data from database
        report_json: Report JSON to generate PDF from
    """
    from app.services.pdf_generator import generate_pdf_from_report
    import io

    try:
        logger.info(f"[PDF] Generating PDF for submission {submission_id}...")

        # Generate PDF
        pdf_stream = io.BytesIO()
        generate_pdf_from_report(
            submission_data=submission_data,
            report_json=report_json,
            output_stream=pdf_stream
        )

        logger.info(f"[PDF] PDF generated successfully for submission {submission_id}")
        return pdf_stream

    except Exception as e:
        logger.error(f"[ERROR] PDF generation failed for submission {submission_id}: {e}", exc_info=True)
        raise


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def normalize_website_url(url: str) -> str:
    """Ensure website URL has https:// prefix"""
    if not url:
        return url

    url = url.strip()

    # If URL already has a protocol, return as-is
    if url.startswith('http://') or url.startswith('https://'):
        return url

    # Add https:// prefix
    return f'https://{url}'
