"""
Background Task Processing & Progress Tracking
Handles asynchronous analysis processing with real-time progress updates
"""
import asyncio
import json
import time
from typing import Dict, List
from datetime import datetime

from app.core.database import (
    get_submission,
    update_submission_status,
)
from app.services.analysis.multistage import generate_multistage_analysis
from app.services.analysis.enhanced import validate_enhanced_analysis
from app.services.analysis.confidence_scorer import calculate_confidence_score
from app.services.data.apify import gather_all_apify_data
from app.services.data.perplexity import comprehensive_market_research
import app.services.data.perplexity as perplexity_service
from app.core.cache import get_cached_analysis, cache_analysis_result


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
    print(f"[PROGRESS] Submission {submission_id}: {progress}% - {message}")


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

async def process_analysis_task(submission_id: int, force_regenerate: bool = False):
    """
    Background task to generate AI analysis with Apify enrichment

    Args:
        submission_id: ID of the submission to process
        force_regenerate: If True, bypass analysis cache and force fresh AI generation
                         (still uses institutional memory cache for external data)
    """
    try:
        # Get submission details
        submission = await get_submission(submission_id)
        if not submission:
            print(f"[ERROR] Submission {submission_id} not found")
            return

        print(f"[PROCESSING] Processing analysis for submission {submission_id}...")

        # Progress: Start
        emit_progress(submission_id, "initializing", f"Iniciando análise para {submission['company']}", 0)

        # Step 1: Gather Apify data (web scraping, competitor research, trends, LinkedIn, news, social media)
        print(f"[APIFY] Gathering enrichment data for {submission['company']}...")
        emit_progress(submission_id, "data_gathering", "Coletando dados de 8 fontes (web, competidores, tendências, LinkedIn, notícias, redes sociais)", 10)
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
            "sources_failed": 0,
            "failed_sources": [],
            "quality_tier": "minimal"
        }

        try:
            apify_data = await gather_all_apify_data(
                company=submission["company"],
                industry=submission["industry"],
                website=submission.get("website"),
                linkedin_company=submission.get("linkedin_company"),
                linkedin_founder=submission.get("linkedin_founder"),
                challenge=submission.get("challenge"),
            )
            print(f"[APIFY] Data gathering completed for submission {submission_id}")

            # Extract data quality metrics
            if apify_data:
                # Core sources
                data_quality["website_scraped"] = apify_data.get("website_data", {}).get("scraped_successfully", False)
                data_quality["competitors_found"] = apify_data.get("competitor_data", {}).get("competitors_found", 0)
                data_quality["trends_researched"] = apify_data.get("industry_trends", {}).get("researched_successfully", False)
                data_quality["company_enriched"] = apify_data.get("company_enrichment", {}).get("enriched_successfully", False)

                # LinkedIn sources
                data_quality["linkedin_company_found"] = apify_data.get("linkedin_company_data", {}).get("scraped_successfully", False)
                data_quality["linkedin_founder_found"] = apify_data.get("linkedin_founder_data", {}).get("scraped_successfully", False)

                # Public data sources
                data_quality["news_found"] = apify_data.get("news_data", {}).get("researched_successfully", False)
                data_quality["social_media_found"] = apify_data.get("social_media_data", {}).get("researched_successfully", False)

                # Count successes from all 8 sources
                successes = sum([
                    data_quality["website_scraped"],
                    data_quality["competitors_found"] > 0,
                    data_quality["trends_researched"],
                    data_quality["company_enriched"],
                    data_quality["linkedin_company_found"],
                    data_quality["linkedin_founder_found"],
                    data_quality["news_found"],
                    data_quality["social_media_found"]
                ])
                data_quality["sources_succeeded"] = successes
                data_quality["sources_failed"] = 8 - successes

                # Track failed sources
                if not data_quality["website_scraped"] and submission.get("website"):
                    data_quality["failed_sources"].append("website_scraping")
                if data_quality["competitors_found"] == 0:
                    data_quality["failed_sources"].append("competitor_research")
                if not data_quality["trends_researched"]:
                    data_quality["failed_sources"].append("industry_trends")
                if not data_quality["company_enriched"]:
                    data_quality["failed_sources"].append("company_enrichment")
                if not data_quality["linkedin_company_found"]:
                    data_quality["failed_sources"].append("linkedin_company")
                if not data_quality["linkedin_founder_found"] and submission.get("linkedin_founder"):
                    data_quality["failed_sources"].append("linkedin_founder")
                if not data_quality["news_found"]:
                    data_quality["failed_sources"].append("news_articles")
                if not data_quality["social_media_found"]:
                    data_quality["failed_sources"].append("social_media")

                # Calculate quality tier
                completion_rate = successes / 8
                if completion_rate >= 0.75:
                    data_quality["quality_tier"] = "full"
                elif completion_rate >= 0.5:
                    data_quality["quality_tier"] = "good"
                elif completion_rate >= 0.25:
                    data_quality["quality_tier"] = "partial"
                else:
                    data_quality["quality_tier"] = "minimal"

                data_quality["data_completeness"] = f"{int(completion_rate * 100)}%"

        except Exception as e:
            print(f"[WARNING] Apify enrichment failed: {str(e)}. Continuing with basic analysis...")
            apify_data = None
            data_quality["sources_failed"] = 8
            data_quality["failed_sources"] = ["all_sources_failed"]

        # Progress: Apify complete
        emit_progress(submission_id, "data_gathering", f"Dados coletados! {data_quality['sources_succeeded']}/8 fontes bem-sucedidas", 30)

        # Step 1.5: Perplexity Deep Research
        print(f"[PERPLEXITY] Starting comprehensive market research for {submission['company']}...")
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
                print(f"[PERPLEXITY] ✅ Comprehensive research completed!")
                perplexity_sources = int(perplexity_data.get('success_rate', '0/5').split('/')[0])
                data_quality["perplexity_sources"] = perplexity_sources
                data_quality["sources_succeeded"] += perplexity_sources

                # Update quality tier with Perplexity boost
                total_sources = 13
                total_succeeded = data_quality["sources_succeeded"]
                completion_rate = total_succeeded / total_sources

                if completion_rate >= 0.75:
                    data_quality["quality_tier"] = "legendary"
                elif completion_rate >= 0.60:
                    data_quality["quality_tier"] = "full"
                elif completion_rate >= 0.40:
                    data_quality["quality_tier"] = "good"
                elif completion_rate >= 0.20:
                    data_quality["quality_tier"] = "partial"
                else:
                    data_quality["quality_tier"] = "minimal"

                data_quality["data_completeness"] = f"{int(completion_rate * 100)}%"

        except Exception as e:
            print(f"[WARNING] Perplexity research failed: {str(e)}. Continuing with Apify data only...")
            perplexity_data = None

        # Progress: Deep research complete
        emit_progress(submission_id, "deep_research", "Pesquisa de mercado concluída! Iniciando geração de análise estratégica", 50)

        # Step 2: Check cache
        cached_analysis_result = None
        if not force_regenerate:
            print(f"[CACHE] 🔍 Checking analysis cache for {submission['company']}...")
            cached_analysis_result = await get_cached_analysis(
                company=submission["company"],
                industry=submission["industry"],
                challenge=submission.get("challenge"),
                website=submission.get("website")
            )
        else:
            print(f"[REGENERATE] 🔄 Force regenerate - bypassing analysis cache")

        if cached_analysis_result and cached_analysis_result.get("cache_hit") and not force_regenerate:
            # CACHE HIT
            analysis = cached_analysis_result["analysis"]
            processing_time = 0.1
            cost_saved = cached_analysis_result.get("cost_saved", 20)
            cache_age_hours = cached_analysis_result.get("cache_age_hours", 0)

            print(f"[CACHE] 🎯💰 CACHE HIT! Saved ${cost_saved:.2f} (age: {cache_age_hours:.1f}h)")
            emit_progress(submission_id, "ai_analysis", f"✨ Análise recuperada do cache (economia de ${cost_saved:.2f}!)", 60)

        else:
            # CACHE MISS - Generate new analysis
            if force_regenerate:
                print(f"[REGENERATE] Generating fresh AI analysis")
            else:
                print(f"[CACHE] ❌ Cache miss - generating new analysis")
            print(f"[AI] 🚀 Generating strategic analysis for submission {submission_id}...")
            emit_progress(submission_id, "ai_analysis", "Gerando análise estratégica com IA (pipeline de 6 etapas)", 60)

            start_time = time.time()

            # Generate analysis
            analysis = await generate_multistage_analysis(
                company=submission["company"],
                industry=submission["industry"],
                website=submission.get("website"),
                challenge=submission.get("challenge"),
                apify_data=apify_data,
                perplexity_data=perplexity_data,
                run_all_stages=True,
                perplexity_service=perplexity_service
            )

            processing_time = time.time() - start_time

            # Cache the result (realistic cost based on actual token usage)
            # Optimized 6-stage pipeline: Gemini Flash (5 stages) + GPT-4o-mini (1 stage)
            # Actual cost: ~$0.08 per analysis (73% cheaper than before!)
            estimated_cost = 0.08
            await cache_analysis_result(
                company=submission["company"],
                industry=submission["industry"],
                challenge=submission.get("challenge"),
                website=submission.get("website"),
                analysis_result=analysis,
                cost=estimated_cost,
                processing_time=processing_time
            )
            print(f"[CACHE] ✅ Analysis cached - will save ${estimated_cost:.2f} on next request")

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
        emit_progress(submission_id, "finalizing", "Salvando relatório no banco de dados", 95)

        # Update submission
        await update_submission_status(
            submission_id=submission_id,
            status="completed",
            report_json=report_json,
            data_quality_json=data_quality_json,
            processing_metadata=processing_metadata_json,
            error_message=None,
        )

        print(f"[OK] Analysis completed for submission {submission_id}")

        # Calculate confidence score
        try:
            print(f"[CONFIDENCE] Calculating confidence score for submission {submission_id}...")
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

            # Save confidence
            await update_submission_status(
                submission_id=submission_id,
                status="completed",
                report_json=report_json,
                data_quality_json=data_quality_json,
                processing_metadata=json.dumps(processing_meta_with_confidence, ensure_ascii=False),
            )

            print(f"[CONFIDENCE] ✅ Confidence score: {confidence_score}/100")
        except Exception as conf_error:
            print(f"[WARNING] Confidence calculation failed: {conf_error}")

        # Progress: Complete
        emit_progress(submission_id, "completed", f"✅ Relatório concluído! Qualidade: {data_quality['quality_tier'].upper()}", 100)

    except Exception as e:
        error_message = str(e)
        print(f"[ERROR] Analysis failed for submission {submission_id}: {error_message}")

        # Progress: Error
        emit_progress(submission_id, "failed", f"❌ Erro: {error_message[:100]}", 0)

        # Update submission with failure
        await update_submission_status(
            submission_id=submission_id,
            status="failed",
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
        print(f"[PDF] Generating PDF for submission {submission_id}...")

        # Generate PDF
        pdf_stream = io.BytesIO()
        generate_pdf_from_report(
            submission_data=submission_data,
            report_json=report_json,
            output_stream=pdf_stream
        )

        print(f"[PDF] PDF generated successfully for submission {submission_id}")
        return pdf_stream

    except Exception as e:
        print(f"[ERROR] PDF generation failed for submission {submission_id}: {e}")
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
