"""
FREE Dashboard Intelligence using DeepSeek R1 or Llama-4 Scout
Admin-only AI-powered insights, trends, and recommendations

Cost: $0.00 (uses free models)
Use Case: Executive dashboard summaries, quality monitoring, trend analysis
"""

import json
import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# FREE models for dashboard intelligence
MODEL_FREE_DEEPSEEK = "deepseek/deepseek-r1:free"  # FREE - Good reasoning
MODEL_FREE_GEMINI = "google/gemini-2.0-flash-exp:free"  # FREE - Fast, reliable
MODEL_FREE_QWEN = "qwen/qwen-2.5-72b-instruct:free"  # FREE - Multilingual

# Use Gemini Flash as default (most reliable free model)
DEFAULT_MODEL = MODEL_FREE_GEMINI

TIMEOUT = 60.0  # Shorter timeout for dashboard queries


async def call_free_llm(
    prompt: str,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.5,
    max_tokens: int = 2000
) -> str:
    """Call free LLM for dashboard intelligence"""

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://strategy-ai.com",
        "X-Title": "Strategy AI - Dashboard Intelligence",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an executive dashboard analyst. Provide concise, actionable insights from data. Always output valid JSON when requested."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            logger.info(f"[DASHBOARD AI] Calling {model} (FREE)")

            response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"].strip()

                # Clean markdown code blocks
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                logger.info(f"[DASHBOARD AI] Response received ({len(content)} chars)")
                return content
            else:
                raise Exception(f"Unexpected API response: {data}")

    except httpx.HTTPStatusError as e:
        logger.error(f"[DASHBOARD AI] Call failed: {str(e)}")

        # Try fallback model if primary fails
        if model == MODEL_FREE_GEMINI:
            logger.warning("[DASHBOARD AI] Gemini failed, trying DeepSeek R1...")
            return await call_free_llm(prompt, model=MODEL_FREE_DEEPSEEK, temperature=temperature, max_tokens=max_tokens)
        elif model == MODEL_FREE_DEEPSEEK:
            logger.warning("[DASHBOARD AI] DeepSeek failed, trying Qwen...")
            return await call_free_llm(prompt, model=MODEL_FREE_QWEN, temperature=temperature, max_tokens=max_tokens)
        else:
            # All fallbacks exhausted
            raise
    except Exception as e:
        logger.error(f"[DASHBOARD AI] Call failed: {str(e)}")
        raise


# ============================================================================
# DASHBOARD INTELLIGENCE FUNCTIONS
# ============================================================================

async def generate_executive_summary(
    submissions: List[Dict[str, Any]],
    timeframe: str = "this week"
) -> str:
    """
    Generate executive summary of all submissions in timeframe

    Args:
        submissions: List of submission objects
        timeframe: "this week", "this month", etc.

    Returns:
        Executive summary text
    """

    logger.info(f"[DASHBOARD AI] Generating executive summary for {len(submissions)} submissions ({timeframe})")

    # Prepare summary data
    summary_data = {
        "total_submissions": len(submissions),
        "industries": {},
        "quality_distribution": {},
        "challenges": [],
        "avg_sources": 0
    }

    for sub in submissions:
        # Count by industry
        industry = sub.get("industry", "Unknown")
        summary_data["industries"][industry] = summary_data["industries"].get(industry, 0) + 1

        # Count by quality tier
        if sub.get("data_quality_json"):
            try:
                quality = json.loads(sub["data_quality_json"])
                tier = quality.get("quality_tier", "unknown")
                summary_data["quality_distribution"][tier] = summary_data["quality_distribution"].get(tier, 0) + 1
                summary_data["avg_sources"] += quality.get("sources_succeeded", 0)
            except:
                pass

        # Collect challenges
        if sub.get("challenge"):
            summary_data["challenges"].append({
                "company": sub.get("company"),
                "industry": industry,
                "challenge": sub.get("challenge")
            })

    if len(submissions) > 0:
        summary_data["avg_sources"] = summary_data["avg_sources"] / len(submissions)

    prompt = f"""Analyze this data and create a concise executive summary (3-4 sentences):

{json.dumps(summary_data, indent=2, ensure_ascii=False)}

Focus on:
1. Overall quality trend (is it improving?)
2. Most common industries and challenges
3. Any notable patterns or concerns
4. One actionable recommendation

Return plain text (not JSON). Be direct and executive-friendly.
"""

    summary = await call_free_llm(prompt, temperature=0.3, max_tokens=500)
    return summary


async def identify_quality_trends(
    current_submissions: List[Dict[str, Any]],
    previous_submissions: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Compare quality trends: current period vs previous period

    Returns:
        Trend analysis with insights
    """

    logger.info(f"[DASHBOARD AI] Analyzing quality trends...")

    def calc_quality_stats(submissions):
        stats = {"legendary": 0, "full": 0, "good": 0, "partial": 0, "minimal": 0, "total": 0}
        for sub in submissions:
            if sub.get("data_quality_json"):
                try:
                    quality = json.loads(sub["data_quality_json"])
                    tier = quality.get("quality_tier", "unknown")
                    stats[tier] = stats.get(tier, 0) + 1
                    stats["total"] += 1
                except:
                    pass
        return stats

    current_stats = calc_quality_stats(current_submissions)
    previous_stats = calc_quality_stats(previous_submissions)

    # Calculate percentages
    current_pct = {
        tier: (count / current_stats["total"] * 100) if current_stats["total"] > 0 else 0
        for tier, count in current_stats.items() if tier != "total"
    }

    previous_pct = {
        tier: (count / previous_stats["total"] * 100) if previous_stats["total"] > 0 else 0
        for tier, count in previous_stats.items() if tier != "total"
    }

    prompt = f"""Analyze quality trends and provide insights:

Current Period: {json.dumps(current_stats, indent=2)}
Current %: {json.dumps(current_pct, indent=2)}

Previous Period: {json.dumps(previous_stats, indent=2)}
Previous %: {json.dumps(previous_pct, indent=2)}

Return JSON with this structure:

{{
  "trend_direction": "IMPROVING / STABLE / DECLINING",
  "key_insights": [
    "Insight 1 (with specific % change)",
    "Insight 2",
    "Insight 3"
  ],
  "root_causes": [
    "Possible cause 1",
    "Possible cause 2"
  ],
  "recommendations": [
    "Action 1 to improve quality",
    "Action 2"
  ]
}}

Be specific with numbers and percentages.
"""

    response = await call_free_llm(prompt, temperature=0.3, max_tokens=1000)

    try:
        trend_analysis = json.loads(response)
        trend_analysis["current_stats"] = current_stats
        trend_analysis["previous_stats"] = previous_stats
        return trend_analysis
    except json.JSONDecodeError:
        logger.error("[DASHBOARD AI] Failed to parse trend analysis JSON")
        return {
            "trend_direction": "UNKNOWN",
            "key_insights": ["Unable to analyze trends"],
            "current_stats": current_stats,
            "previous_stats": previous_stats
        }


async def identify_common_challenges(
    submissions: List[Dict[str, Any]],
    top_n: int = 5
) -> Dict[str, Any]:
    """
    Identify most common business challenges across submissions

    Returns:
        Challenge clustering with recommended solutions
    """

    logger.info(f"[DASHBOARD AI] Clustering common challenges...")

    challenges = []
    for sub in submissions:
        if sub.get("challenge") and sub.get("challenge").strip():
            challenges.append({
                "company": sub.get("company"),
                "industry": sub.get("industry"),
                "challenge": sub.get("challenge")
            })

    if len(challenges) == 0:
        return {"common_challenges": [], "message": "No challenges to analyze"}

    prompt = f"""Analyze these business challenges and group them into common themes:

{json.dumps(challenges[:50], indent=2, ensure_ascii=False)}  # Limit to 50 for token efficiency

Return JSON with this structure:

{{
  "common_challenges": [
    {{
      "theme": "Challenge theme (e.g., 'Customer Acquisition')",
      "frequency": 10,
      "industries": ["Tecnologia", "Saúde"],
      "examples": ["Example challenge 1", "Example challenge 2"],
      "recommended_solution": "1-2 sentence actionable recommendation"
    }}
  ]
}}

Group into top {top_n} themes. Be specific and actionable.
"""

    response = await call_free_llm(prompt, temperature=0.4, max_tokens=1500)

    try:
        challenge_analysis = json.loads(response)
        return challenge_analysis
    except json.JSONDecodeError:
        logger.error("[DASHBOARD AI] Failed to parse challenge analysis JSON")
        return {"common_challenges": [], "message": "Parse error"}


async def identify_high_risk_submissions(
    submissions: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Identify submissions with high-risk indicators requiring urgent follow-up

    Returns:
        List of high-risk submissions with risk factors
    """

    logger.info(f"[DASHBOARD AI] Identifying high-risk submissions...")

    # Extract relevant data for risk assessment
    risk_data = []
    for sub in submissions:
        data_quality = None
        if sub.get("data_quality_json"):
            try:
                data_quality = json.loads(sub["data_quality_json"])
            except:
                pass

        report = None
        if sub.get("report_json"):
            try:
                report = json.loads(sub["report_json"])
            except:
                pass

        risk_data.append({
            "id": sub.get("id"),
            "company": sub.get("company"),
            "industry": sub.get("industry"),
            "challenge": sub.get("challenge"),
            "quality_tier": data_quality.get("quality_tier") if data_quality else None,
            "sources_succeeded": data_quality.get("sources_succeeded") if data_quality else 0,
            "has_error": sub.get("error_message") is not None,
            "created_at": sub.get("created_at")
        })

    prompt = f"""Identify high-risk submissions requiring urgent follow-up:

{json.dumps(risk_data, indent=2, ensure_ascii=False)}

Risk indicators:
- Low quality tier (partial, minimal)
- Few sources succeeded (<5)
- Errors during processing
- Challenges indicating urgent business problems

Return JSON:

{{
  "high_risk_submissions": [
    {{
      "id": 123,
      "company": "Company Name",
      "risk_level": "HIGH / MEDIUM",
      "risk_factors": ["Factor 1", "Factor 2"],
      "recommended_action": "Specific action to take"
    }}
  ]
}}

Only flag truly high-risk cases (not just low quality).
"""

    response = await call_free_llm(prompt, temperature=0.3, max_tokens=1500)

    try:
        risk_analysis = json.loads(response)
        return risk_analysis.get("high_risk_submissions", [])
    except json.JSONDecodeError:
        logger.error("[DASHBOARD AI] Failed to parse risk analysis JSON")
        return []


async def generate_system_improvement_recommendations(
    submissions: List[Dict[str, Any]],
    quality_trends: Dict[str, Any]
) -> List[str]:
    """
    Generate recommendations to improve the analysis system itself

    Returns:
        List of improvement recommendations
    """

    logger.info(f"[DASHBOARD AI] Generating system improvement recommendations...")

    # Analyze failure patterns
    failure_patterns = {
        "apify_failures": {},
        "perplexity_failures": 0,
        "ai_refusals": 0,
        "total_errors": 0
    }

    for sub in submissions:
        if sub.get("data_quality_json"):
            try:
                quality = json.loads(sub["data_quality_json"])
                failed_sources = quality.get("failed_sources", [])
                for source in failed_sources:
                    failure_patterns["apify_failures"][source] = failure_patterns["apify_failures"].get(source, 0) + 1

                if quality.get("perplexity_sources", 5) == 0:
                    failure_patterns["perplexity_failures"] += 1
            except:
                pass

        if sub.get("error_message") and "refused" in sub.get("error_message", "").lower():
            failure_patterns["ai_refusals"] += 1

        if sub.get("status") == "failed":
            failure_patterns["total_errors"] += 1

    prompt = f"""Based on failure patterns and quality trends, recommend system improvements:

Failure Patterns:
{json.dumps(failure_patterns, indent=2)}

Quality Trends:
{json.dumps(quality_trends, indent=2)}

Return JSON:

{{
  "improvement_recommendations": [
    "Specific improvement 1 with expected impact",
    "Specific improvement 2",
    "..."
  ],
  "priority_order": [1, 2, 3]
}}

Focus on high-ROI improvements (low effort, high impact).
"""

    response = await call_free_llm(prompt, temperature=0.4, max_tokens=1000)

    try:
        improvements = json.loads(response)
        return improvements.get("improvement_recommendations", [])
    except json.JSONDecodeError:
        logger.error("[DASHBOARD AI] Failed to parse improvement recommendations JSON")
        return ["Unable to generate recommendations"]


# ============================================================================
# MAIN DASHBOARD INTELLIGENCE GENERATOR
# ============================================================================

async def generate_dashboard_intelligence(
    current_submissions: List[Dict[str, Any]],
    previous_submissions: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Generate comprehensive dashboard intelligence using FREE models

    Args:
        current_submissions: Submissions from current period
        previous_submissions: Submissions from previous period (for trend analysis)

    Returns:
        Complete dashboard intelligence JSON
    """

    logger.info(f"[DASHBOARD AI] Generating dashboard intelligence for {len(current_submissions)} submissions")

    try:
        # Generate executive summary
        exec_summary = await generate_executive_summary(current_submissions, "this week")

        # Quality trends (if we have previous data)
        quality_trends = None
        if previous_submissions and len(previous_submissions) > 0:
            quality_trends = await identify_quality_trends(current_submissions, previous_submissions)

        # Common challenges
        common_challenges = await identify_common_challenges(current_submissions)

        # High-risk submissions
        high_risk = await identify_high_risk_submissions(current_submissions)

        # System improvements (if we have trends)
        improvements = []
        if quality_trends:
            improvements = await generate_system_improvement_recommendations(
                current_submissions, quality_trends
            )

        dashboard_data = {
            "generated_at": datetime.now().isoformat(),
            "period": "last_7_days",
            "total_submissions": len(current_submissions),

            "executive_summary": exec_summary,

            "quality_trends": quality_trends,

            "common_challenges": common_challenges.get("common_challenges", []),

            "high_risk_submissions": high_risk,

            "system_improvement_recommendations": improvements,

            "metadata": {
                "model_used": DEFAULT_MODEL,
                "cost": "$0.00 (FREE)",
                "processing_time": "Generated in <60s"
            }
        }

        logger.info(f"[DASHBOARD AI] ✅ Dashboard intelligence generated successfully")
        return dashboard_data

    except Exception as e:
        logger.error(f"[DASHBOARD AI] Failed to generate intelligence: {str(e)}")
        return {
            "error": str(e),
            "generated_at": datetime.now().isoformat()
        }


# Test function
async def test_dashboard_intelligence():
    """Test dashboard intelligence generation"""
    import asyncio

    # Mock submissions
    mock_submissions = [
        {
            "id": 1,
            "company": "TechCorp",
            "industry": "Tecnologia",
            "challenge": "Precisamos escalar de 100 para 500 clientes",
            "data_quality_json": json.dumps({"quality_tier": "legendary", "sources_succeeded": 12}),
            "status": "completed"
        },
        {
            "id": 2,
            "company": "HealthCo",
            "industry": "Saúde",
            "challenge": "Melhorar satisfação do paciente",
            "data_quality_json": json.dumps({"quality_tier": "good", "sources_succeeded": 7}),
            "status": "completed"
        },
        {
            "id": 3,
            "company": "RetailX",
            "industry": "Varejo",
            "challenge": "Precisamos escalar vendas online",
            "data_quality_json": json.dumps({"quality_tier": "full", "sources_succeeded": 9}),
            "status": "completed"
        }
    ]

    result = await generate_dashboard_intelligence(mock_submissions)

    print("[OK] Dashboard intelligence generated!")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    import asyncio
    asyncio.run(test_dashboard_intelligence())
