"""
Perplexity AI Research Service via OpenRouter
Uses Perplexity's Sonar models for real-time web research with citations
"""

import os
import httpx
import logging
import re
from typing import Dict, Any, List, Optional
from datetime import datetime

# Import comprehensive prompt injection sanitization
from prompt_injection_sanitizer import sanitize_for_prompt, neutralize_injection_patterns

logger = logging.getLogger(__name__)


def sanitize_research_data(data: str, max_length: int = 3000) -> str:
    """
    Sanitize Perplexity research data with comprehensive injection prevention

    Args:
        data: Raw research text from Perplexity
        max_length: Maximum character length

    Returns:
        Cleaned, truncated text safe for AI prompts
    """
    if not data:
        return ""

    # Use comprehensive sanitization (includes HTML stripping, code block removal,
    # injection pattern detection, URL removal, and special character escaping)
    sanitized = sanitize_for_prompt(
        data,
        max_length=max_length,
        remove_urls_flag=True,
        strict_mode=True  # Neutralize injection patterns
    )

    logger.info(f"[PERPLEXITY] Sanitized: {len(data)} → {len(sanitized)} chars")

    return sanitized

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Using Perplexity Sonar Pro for deep research with citations
PERPLEXITY_MODEL = "perplexity/sonar-pro"

# Fallback to standard model if pro not available
PERPLEXITY_MODEL_FALLBACK = "perplexity/sonar"


async def call_perplexity(
    prompt: str,
    max_tokens: int = 4000,
    temperature: float = 0.7,
    use_pro: bool = True
) -> Optional[str]:
    """
    Call Perplexity via OpenRouter for real-time web research

    Args:
        prompt: Research query/prompt
        max_tokens: Maximum tokens in response
        temperature: Sampling temperature (0-1)
        use_pro: Use Sonar Pro model (recommended for deep research)

    Returns:
        Research results as string, or None on error
    """
    if not OPENROUTER_API_KEY:
        logger.error("OPENROUTER_API_KEY not configured")
        return None

    model = PERPLEXITY_MODEL if use_pro else PERPLEXITY_MODEL_FALLBACK

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://strategy-ai.app",  # Optional but recommended
        "X-Title": "Strategy AI - Market Research",  # Optional but recommended
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.info(f"[PERPLEXITY] Calling {model} for research...")

            response = await client.post(
                f"{OPENROUTER_BASE_URL}/chat/completions",
                headers=headers,
                json=payload
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                logger.info(f"[PERPLEXITY] Research completed successfully ({len(content)} chars)")

                # Sanitize to prevent content filter triggers
                sanitized = sanitize_research_data(content, max_length=3000)
                logger.info(f"[PERPLEXITY] Sanitized: {len(content)} → {len(sanitized)} chars")

                return sanitized
            else:
                logger.error(f"[PERPLEXITY] API error: {response.status_code} - {response.text}")

                # Try fallback model if pro failed
                if use_pro:
                    logger.info("[PERPLEXITY] Retrying with standard model...")
                    return await call_perplexity(prompt, max_tokens, temperature, use_pro=False)

                return None

    except Exception as e:
        logger.error(f"[PERPLEXITY] Exception during API call: {str(e)}")
        return None


async def research_competitors(
    company: str,
    industry: str,
    region: str = "Brasil"
) -> Dict[str, Any]:
    """
    Deep competitor analysis with real market data

    Returns structured competitor intelligence with metrics, news, and positioning
    """
    prompt = f"""Analyze the competitive landscape for {company} in the {industry} industry in {region}.

Provide comprehensive competitor analysis including:

1. TOP 5-7 DIRECT COMPETITORS:
   - Company name and market position
   - Estimated market share (%)
   - Recent revenue figures (if public)
   - Key strengths and competitive advantages
   - Key weaknesses or vulnerabilities
   - Recent news or strategic moves (last 3-6 months)
   - Customer satisfaction scores or ratings

2. COMPETITIVE POSITIONING:
   - How does {company} compare to competitors?
   - Market gaps or opportunities
   - Competitive threats

3. MARKET LEADERS:
   - Who dominates this market?
   - What makes them successful?

Please provide specific numbers, percentages, and recent data where available.
Include sources and dates for all information."""

    result = await call_perplexity(prompt, max_tokens=6000)

    return {
        "query": f"Competitors of {company} in {industry}",
        "research_date": datetime.now().isoformat(),
        "competitor_analysis": result,
        "data_source": "Perplexity Sonar Pro (Real-time Web)"
    }


async def research_market_sizing(
    industry: str,
    specific_segment: Optional[str] = None,
    region: str = "Brasil"
) -> Dict[str, Any]:
    """
    Market sizing research with TAM, SAM, SOM

    Returns market size data with growth rates and trends
    """
    segment_info = f" specifically for {specific_segment}" if specific_segment else ""

    prompt = f"""Provide comprehensive market sizing analysis for the {industry} industry in {region}{segment_info}.

Include:

1. TAM (Total Addressable Market):
   - Total market size in local currency (R$ for Brazil)
   - Total market size in USD
   - Year-over-year growth rate
   - 5-year CAGR projection

2. SAM (Serviceable Addressable Market):
   - Realistically serviceable segment
   - Size and growth rate
   - Key market segments breakdown

3. SOM (Serviceable Obtainable Market):
   - Initial target market opportunity
   - Entry barriers and challenges

4. MARKET TRENDS:
   - Current growth drivers
   - Market maturity stage
   - Future projections (3-5 years)

5. KEY MARKET SEGMENTS:
   - Breakdown by customer type, size, or vertical
   - Growth rates by segment

Please provide specific numbers with currency and dates.
Cite sources for all data points."""

    result = await call_perplexity(prompt, max_tokens=5000)

    return {
        "query": f"Market sizing for {industry} in {region}",
        "research_date": datetime.now().isoformat(),
        "market_sizing": result,
        "data_source": "Perplexity Sonar Pro (Real-time Web)"
    }


async def research_industry_trends(
    industry: str,
    region: str = "Brasil",
    timeframe: str = "2024-2025"
) -> Dict[str, Any]:
    """
    Industry trends and insights with recent developments

    Returns trend analysis with specific dates and examples
    """
    prompt = f"""Analyze key trends and developments in the {industry} industry in {region} for {timeframe}.

Provide detailed analysis including:

1. MAJOR TRENDS (Top 5-7):
   - Trend name and description
   - Adoption rate or growth metrics
   - Timeline and maturity
   - Impact on market (high/medium/low)
   - Key companies leading this trend

2. REGULATORY CHANGES:
   - Recent or upcoming regulations
   - Impact on industry
   - Compliance requirements

3. TECHNOLOGY SHIFTS:
   - New technologies gaining adoption
   - Disruption potential
   - Investment trends

4. CONSUMER BEHAVIOR CHANGES:
   - Shifting preferences
   - New customer expectations
   - Demographic trends

5. ECONOMIC FACTORS:
   - Macro trends affecting industry
   - Investment climate
   - Market sentiment

Include specific examples, company names, dates, and quantitative data where available.
Focus on actionable insights."""

    result = await call_perplexity(prompt, max_tokens=5000)

    return {
        "query": f"Industry trends for {industry} in {region}",
        "research_date": datetime.now().isoformat(),
        "trend_analysis": result,
        "data_source": "Perplexity Sonar Pro (Real-time Web)"
    }


async def research_company_intelligence(
    company: str,
    industry: str,
    timeframe_days: int = 90
) -> Dict[str, Any]:
    """
    Company-specific intelligence with recent news and developments

    Returns recent company activity, strategic moves, and market perception
    """
    prompt = f"""Provide comprehensive intelligence on {company} in the {industry} industry for the last {timeframe_days} days.

Include:

1. RECENT NEWS & DEVELOPMENTS:
   - Major announcements (product launches, funding, partnerships)
   - Strategic initiatives or pivots
   - Leadership changes
   - Market reactions

2. FINANCIAL PERFORMANCE (if available):
   - Recent revenue/earnings reports
   - Funding rounds or valuation changes
   - Stock performance (if public)
   - Financial health indicators

3. PRODUCT & SERVICE UPDATES:
   - New offerings or features
   - Market reception
   - Customer feedback

4. STRATEGIC POSITIONING:
   - Current strategy and focus areas
   - Market expansion plans
   - Competitive moves

5. PUBLIC PERCEPTION:
   - Media sentiment
   - Customer reviews and ratings
   - Industry analyst opinions
   - Social media sentiment

6. LEADERSHIP INSIGHTS:
   - CEO/Founder recent statements
   - Company vision and goals
   - Strategic priorities

Include specific dates, sources, and quantitative metrics.
Focus on information from the last {timeframe_days} days."""

    result = await call_perplexity(prompt, max_tokens=5000)

    return {
        "query": f"Company intelligence for {company}",
        "research_date": datetime.now().isoformat(),
        "timeframe_days": timeframe_days,
        "company_intelligence": result,
        "data_source": "Perplexity Sonar Pro (Real-time Web)"
    }


async def research_solution_strategies(
    challenge: str,
    industry: str,
    company_context: Optional[str] = None
) -> Dict[str, Any]:
    """
    Research best practices and strategies for specific business challenges

    Returns case studies, frameworks, and actionable recommendations
    """
    context_info = f"\n\nCompany context: {company_context}" if company_context else ""

    prompt = f"""Research best practices, strategies, and solutions for the following business challenge in the {industry} industry:

CHALLENGE: {challenge}{context_info}

Provide comprehensive analysis including:

1. SUCCESSFUL CASE STUDIES:
   - Company examples that solved similar challenges
   - Specific approaches and tactics used
   - Results and metrics achieved
   - Timeline and resources required

2. PROVEN FRAMEWORKS & METHODOLOGIES:
   - Industry-standard approaches
   - Expert-recommended frameworks
   - Step-by-step implementation strategies

3. BEST PRACTICES:
   - What works well in this industry
   - Common pitfalls to avoid
   - Success factors

4. INNOVATIVE APPROACHES:
   - New or emerging solutions
   - Technology-enabled strategies
   - Disruptive approaches

5. EXPERT INSIGHTS:
   - Industry expert opinions
   - Consultant recommendations
   - Academic research findings

6. METRICS & BENCHMARKS:
   - KPIs to track
   - Industry benchmarks
   - Success indicators

Include specific company names, metrics, dates, and quantitative results.
Focus on actionable, implementable strategies."""

    result = await call_perplexity(prompt, max_tokens=6000)

    return {
        "query": f"Solution strategies for: {challenge}",
        "research_date": datetime.now().isoformat(),
        "solution_research": result,
        "data_source": "Perplexity Sonar Pro (Real-time Web)"
    }


async def comprehensive_market_research(
    company: str,
    industry: str,
    challenge: str,
    region: str = "Brasil",
    specific_segment: Optional[str] = None
) -> Dict[str, Any]:
    """
    Run all research functions in parallel for comprehensive market intelligence

    This is the main function to call for full legendary analysis
    """
    logger.info(f"[PERPLEXITY] Starting comprehensive research for {company}")

    try:
        # Run all research queries in parallel (much faster than sequential)
        import asyncio

        results = await asyncio.gather(
            research_competitors(company, industry, region),
            research_market_sizing(industry, specific_segment, region),
            research_industry_trends(industry, region),
            research_company_intelligence(company, industry),
            research_solution_strategies(challenge, industry, f"{company} in {industry}"),
            return_exceptions=True
        )

        # Process results
        competitor_data = results[0] if not isinstance(results[0], Exception) else None
        market_sizing = results[1] if not isinstance(results[1], Exception) else None
        trend_data = results[2] if not isinstance(results[2], Exception) else None
        company_intel = results[3] if not isinstance(results[3], Exception) else None
        solution_data = results[4] if not isinstance(results[4], Exception) else None

        success_count = sum(1 for r in results if not isinstance(r, Exception))

        logger.info(f"[PERPLEXITY] Research complete: {success_count}/5 queries successful")

        return {
            "research_completed": True,
            "research_date": datetime.now().isoformat(),
            "success_rate": f"{success_count}/5",
            "competitors": competitor_data,
            "market_sizing": market_sizing,
            "industry_trends": trend_data,
            "company_intelligence": company_intel,
            "solution_strategies": solution_data,
            "metadata": {
                "model_used": PERPLEXITY_MODEL,
                "research_depth": "comprehensive",
                "data_freshness": "real-time"
            }
        }

    except Exception as e:
        logger.error(f"[PERPLEXITY] Comprehensive research failed: {str(e)}")
        return {
            "research_completed": False,
            "error": str(e),
            "research_date": datetime.now().isoformat()
        }


# Quick test function
async def test_perplexity_connection():
    """Test Perplexity API connection via OpenRouter"""
    test_prompt = "What is the current market size of fintech in Brazil? Provide a brief answer with a specific number."

    logger.info("[PERPLEXITY] Testing API connection...")
    result = await call_perplexity(test_prompt, max_tokens=500)

    if result:
        logger.info(f"[PERPLEXITY] ✅ Connection successful!")
        logger.info(f"[PERPLEXITY] Test response: {result[:200]}...")
        return True
    else:
        logger.error("[PERPLEXITY] ❌ Connection failed")
        return False
