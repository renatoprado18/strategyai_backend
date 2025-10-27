"""
AI Confidence Scorer

Calculates a 0-100 confidence score based on data quality and analysis completeness.
Helps admin quickly assess if a report is ready to send to client.

Score Breakdown:
- Data Completeness (0-30 points): How much data was gathered
- Source Success Rate (0-25 points): How many data sources succeeded
- Market Research Depth (0-20 points): Quality of competitor/trend analysis
- Analysis Comprehensiveness (0-15 points): Coverage of all frameworks
- TAM/SAM/SOM Availability (0-10 points): Market sizing quality

Score Interpretation:
- 90-100: High Confidence ✓ (Ready to send)
- 75-89: Good Quality (Minor review recommended)
- 60-74: Review Recommended (Check weak areas)
- Below 60: Manual Review Required (Significant gaps)
"""

import json
from typing import Dict, Any, Optional, Tuple


def calculate_confidence_score(
    submission_data: Dict[str, Any],
    report_json: Optional[str] = None,
    data_quality_json: Optional[str] = None,
    processing_metadata: Optional[str] = None,
) -> Tuple[float, Dict[str, Any]]:
    """
    Calculate confidence score for a strategic analysis report

    Args:
        submission_data: Raw submission data from database
        report_json: Generated analysis report (JSON string)
        data_quality_json: Data quality metadata (JSON string)
        processing_metadata: Processing metadata (JSON string)

    Returns:
        Tuple of (score: float, breakdown: dict)
    """

    # Parse JSON fields
    report = None
    if report_json:
        try:
            report = json.loads(report_json)
        except:
            report = None

    data_quality = None
    if data_quality_json:
        try:
            data_quality = json.loads(data_quality_json)
        except:
            data_quality = None

    metadata = None
    if processing_metadata:
        try:
            metadata = json.loads(processing_metadata)
        except:
            metadata = None

    # Initialize score components
    scores = {
        "data_completeness": 0.0,
        "source_success_rate": 0.0,
        "market_research_depth": 0.0,
        "analysis_comprehensiveness": 0.0,
        "tam_sam_som_availability": 0.0,
    }

    max_scores = {
        "data_completeness": 30,
        "source_success_rate": 25,
        "market_research_depth": 20,
        "analysis_comprehensiveness": 15,
        "tam_sam_som_availability": 10,
    }

    # ========================================================================
    # SCORE 1: Data Completeness (0-30 points)
    # ========================================================================
    if data_quality:
        tier = data_quality.get("tier", "minimal")
        completeness_pct = data_quality.get("completeness_percentage", 0)

        # Base score from completeness percentage (0-20 points)
        scores["data_completeness"] += (completeness_pct / 100) * 20

        # Bonus points for tier (0-10 points)
        tier_bonuses = {
            "legendary": 10,
            "full": 8,
            "good": 6,
            "partial": 3,
            "minimal": 0,
        }
        scores["data_completeness"] += tier_bonuses.get(tier, 0)

        # Cap at max
        scores["data_completeness"] = min(scores["data_completeness"], max_scores["data_completeness"])

    # ========================================================================
    # SCORE 2: Source Success Rate (0-25 points)
    # ========================================================================
    if data_quality:
        sources = data_quality.get("sources", {})
        succeeded = sources.get("succeeded", 0)
        total = sources.get("total", 1)

        if total > 0:
            success_rate = succeeded / total
            scores["source_success_rate"] = success_rate * max_scores["source_success_rate"]

    # ========================================================================
    # SCORE 3: Market Research Depth (0-20 points)
    # ========================================================================
    if data_quality:
        competitors_found = data_quality.get("competitors_found", 0)
        trends_researched = data_quality.get("trends_researched", False)
        website_scraped = data_quality.get("website_scraped", False)

        # Competitors found (0-10 points)
        if competitors_found >= 5:
            scores["market_research_depth"] += 10
        elif competitors_found >= 3:
            scores["market_research_depth"] += 7
        elif competitors_found >= 1:
            scores["market_research_depth"] += 4

        # Trends research (0-5 points)
        if trends_researched:
            scores["market_research_depth"] += 5

        # Website scraped (0-5 points)
        if website_scraped:
            scores["market_research_depth"] += 5

    # ========================================================================
    # SCORE 4: Analysis Comprehensiveness (0-15 points)
    # ========================================================================
    if report:
        # Check for presence of key frameworks
        frameworks_present = 0

        # SWOT Analysis
        if report.get("analise_swot") or (
            report.get("parte_1_onde_estamos", {}).get("analise_swot")
        ):
            frameworks_present += 1

        # PESTEL Analysis
        if report.get("analise_pestel") or (
            report.get("parte_1_onde_estamos", {}).get("analise_pestel")
        ):
            frameworks_present += 1

        # Porter's Forces
        if report.get("sete_forcas_porter") or (
            report.get("parte_1_onde_estamos", {}).get("sete_forcas_porter")
        ):
            frameworks_present += 1

        # Blue Ocean
        if report.get("estrategia_oceano_azul") or (
            report.get("parte_2_onde_queremos_ir", {}).get("estrategia_oceano_azul")
        ):
            frameworks_present += 1

        # OKRs
        if report.get("okrs_propostos") or (
            report.get("parte_3_como_chegar_la", {}).get("okrs_propostos")
        ):
            frameworks_present += 1

        # Recommendations
        if report.get("recomendacoes_prioritarias") or (
            report.get("parte_4_o_que_fazer_agora", {}).get("recomendacoes_prioritarias")
        ):
            frameworks_present += 1

        # Score: 2.5 points per framework (6 frameworks = 15 points)
        scores["analysis_comprehensiveness"] = min(frameworks_present * 2.5, max_scores["analysis_comprehensiveness"])

    # ========================================================================
    # SCORE 5: TAM/SAM/SOM Availability (0-10 points)
    # ========================================================================
    if report:
        tam_sam_som = None

        # Check both old and new structure
        if report.get("tam_sam_som"):
            tam_sam_som = report["tam_sam_som"]
        elif report.get("parte_2_onde_queremos_ir", {}).get("tam_sam_som"):
            tam_sam_som = report["parte_2_onde_queremos_ir"]["tam_sam_som"]

        if tam_sam_som:
            # Check if TAM/SAM/SOM have actual values (not "Dados insuficientes")
            tam = tam_sam_som.get("tam_total_market", "")
            sam = tam_sam_som.get("sam_available_market", "")
            som = tam_sam_som.get("som_obtainable_market", "")

            has_tam = tam and "insuficiente" not in tam.lower() and tam != "N/A"
            has_sam = sam and "insuficiente" not in sam.lower() and sam != "N/A"
            has_som = som and "insuficiente" not in som.lower() and som != "N/A"

            if has_tam and has_sam and has_som:
                scores["tam_sam_som_availability"] = 10  # All three present
            elif has_tam and has_sam:
                scores["tam_sam_som_availability"] = 7  # TAM and SAM
            elif has_tam:
                scores["tam_sam_som_availability"] = 4  # TAM only

    # ========================================================================
    # Calculate Total Score and Build Breakdown
    # ========================================================================

    total_score = sum(scores.values())
    total_score = round(total_score, 1)

    breakdown = {
        "total_score": total_score,
        "max_possible": 100,
        "components": {
            "data_completeness": {
                "score": round(scores["data_completeness"], 1),
                "max": max_scores["data_completeness"],
                "percentage": round((scores["data_completeness"] / max_scores["data_completeness"]) * 100, 1) if max_scores["data_completeness"] > 0 else 0,
            },
            "source_success_rate": {
                "score": round(scores["source_success_rate"], 1),
                "max": max_scores["source_success_rate"],
                "percentage": round((scores["source_success_rate"] / max_scores["source_success_rate"]) * 100, 1) if max_scores["source_success_rate"] > 0 else 0,
            },
            "market_research_depth": {
                "score": round(scores["market_research_depth"], 1),
                "max": max_scores["market_research_depth"],
                "percentage": round((scores["market_research_depth"] / max_scores["market_research_depth"]) * 100, 1) if max_scores["market_research_depth"] > 0 else 0,
            },
            "analysis_comprehensiveness": {
                "score": round(scores["analysis_comprehensiveness"], 1),
                "max": max_scores["analysis_comprehensiveness"],
                "percentage": round((scores["analysis_comprehensiveness"] / max_scores["analysis_comprehensiveness"]) * 100, 1) if max_scores["analysis_comprehensiveness"] > 0 else 0,
            },
            "tam_sam_som_availability": {
                "score": round(scores["tam_sam_som_availability"], 1),
                "max": max_scores["tam_sam_som_availability"],
                "percentage": round((scores["tam_sam_som_availability"] / max_scores["tam_sam_som_availability"]) * 100, 1) if max_scores["tam_sam_som_availability"] > 0 else 0,
            },
        },
        "interpretation": _get_interpretation(total_score),
        "calculated_at": None,  # Will be set by caller
    }

    return total_score, breakdown


def _get_interpretation(score: float) -> Dict[str, str]:
    """Get human-readable interpretation of confidence score"""
    if score >= 90:
        return {
            "level": "high",
            "label": "High Confidence ✓",
            "description": "Excellent data quality. Ready to send to client.",
            "action": "Minimal review needed. Safe to send.",
        }
    elif score >= 75:
        return {
            "level": "good",
            "label": "Good Quality",
            "description": "Solid analysis with good data coverage.",
            "action": "Quick review recommended before sending.",
        }
    elif score >= 60:
        return {
            "level": "medium",
            "label": "Review Recommended",
            "description": "Adequate analysis but some weak areas.",
            "action": "Review weak components before sending.",
        }
    else:
        return {
            "level": "low",
            "label": "Manual Review Required",
            "description": "Limited data or incomplete analysis.",
            "action": "Significant review and potential regeneration needed.",
        }


def get_confidence_color(score: float) -> str:
    """Get color code for confidence score badge"""
    if score >= 90:
        return "green"  # High confidence
    elif score >= 75:
        return "blue"  # Good
    elif score >= 60:
        return "yellow"  # Review needed
    else:
        return "red"  # Manual review required


# Example usage
if __name__ == "__main__":
    # Test with sample data
    test_submission = {
        "id": 1,
        "company": "Test Corp",
        "status": "completed",
    }

    test_data_quality = json.dumps({
        "tier": "good",
        "completeness_percentage": 75,
        "sources": {"succeeded": 3, "total": 4},
        "competitors_found": 4,
        "trends_researched": True,
        "website_scraped": True,
    })

    test_report = json.dumps({
        "analise_swot": {"forças": ["F1"], "fraquezas": [], "oportunidades": [], "ameaças": []},
        "analise_pestel": {},
        "okrs_propostos": [],
        "tam_sam_som": {
            "tam_total_market": "R$ 10B",
            "sam_available_market": "R$ 2B",
            "som_obtainable_market": "R$ 200M",
        },
    })

    score, breakdown = calculate_confidence_score(
        test_submission,
        report_json=test_report,
        data_quality_json=test_data_quality,
    )

    print(f"Confidence Score: {score}/100")
    print(f"Interpretation: {breakdown['interpretation']['label']}")
    print(f"Action: {breakdown['interpretation']['action']}")
    print(f"\nBreakdown:")
    for component, details in breakdown["components"].items():
        print(f"  {component}: {details['score']}/{details['max']} ({details['percentage']}%)")
