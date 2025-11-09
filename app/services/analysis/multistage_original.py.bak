"""
Multi-Stage Analysis Pipeline with Specialized Models
Cost-optimized + Quality-maximized architecture

Stage 1: Data Extraction (Gemini Flash - CHEAP)
Stage 2: Gap Analysis + Follow-Up Research (Gemini Flash + Perplexity)
Stage 3: Strategic Frameworks (GPT-4o - EXPENSIVE but worth it)
Stage 4: Competitive Matrix (Gemini Pro - Good at structured data)
Stage 5: Risk Scoring + Priority (Claude 3.5 Sonnet - Best reasoning)
Stage 6: Executive Polish (Claude Haiku - Cheap + good writing)
"""

import json
import httpx
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import os
from dotenv import load_dotenv

# Production-grade validation utilities
from app.utils.validation import (
    enforce_portuguese_output,
    CostTracker,
    assess_data_quality,
    detect_english_leakage
)

# Import prompt injection sanitization
from app.core.security.prompt_sanitizer import sanitize_dict_recursive, sanitize_for_prompt

# Import caching system
from app.core.cache import (
    cache_stage_result,
    get_cached_stage_result,
    generate_content_hash
)

logger = logging.getLogger(__name__)
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Smart Model Selection - Use the RIGHT model for each job!
# Client-facing stages use PREMIUM models (quality matters!)
# Backend stages use BUDGET models (cost-effective)
from app.core.model_config import get_model_for_stage, MODEL_SELECTION, get_stage_config, get_estimated_cost
from app.utils.logger import AnalysisLogger, log_model_selection
import time

# Load models from smart configuration
MODEL_EXTRACTION = get_model_for_stage("extraction")  # Budget: Gemini Flash
MODEL_GAP_ANALYSIS = get_model_for_stage("gap_analysis")  # Budget: Gemini Flash
MODEL_STRATEGY = get_model_for_stage("strategy")  # PREMIUM: GPT-4o (CLIENT-FACING!)
MODEL_COMPETITIVE = get_model_for_stage("competitive")  # PREMIUM: Gemini Pro (important!)
MODEL_RISK_SCORING = get_model_for_stage("risk_scoring")  # PREMIUM: Claude Sonnet (reasoning!)
MODEL_POLISH = get_model_for_stage("polish")  # PREMIUM: Claude Sonnet (CLIENT-FACING!)

# Log model selections on import
for stage in ["extraction", "gap_analysis", "strategy", "competitive", "risk_scoring", "polish"]:
    config = get_stage_config(stage)
    log_model_selection(
        stage=stage,
        task=config.get("task_type", "unknown").value if hasattr(config.get("task_type"), "value") else str(config.get("task_type")),
        model=config.get("primary_model", "unknown"),
        reason=config.get("reason", "")
    )

TIMEOUT = 120.0
MAX_RETRIES = 3  # Maximum retry attempts per stage


async def call_llm_with_retry(
    stage_name: str,
    model: str,
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4000,
    max_retries: int = MAX_RETRIES,
    cost_tracker: Optional[CostTracker] = None
) -> tuple[str, dict]:
    """
    Call LLM with automatic retry logic and progressive temperature reduction

    Args:
        stage_name: Name of the stage for logging
        model: Model to use
        prompt: User prompt
        system_prompt: System prompt
        temperature: Initial temperature (will be reduced on retries)
        max_tokens: Max tokens
        max_retries: Maximum retry attempts
        cost_tracker: Optional CostTracker instance

    Returns:
        (valid_json_string, usage_stats)
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            # Reduce temperature on retries for more deterministic output
            current_temp = temperature * (0.7 ** attempt)

            # Make prompt stricter on retries
            if attempt > 0:
                strict_prompt = f"{prompt}\n\n**CRITICAL: Output ONLY valid JSON. No markdown, no code blocks, no explanations. Start with {{ and end with }}.**"
                logger.warning(f"[{stage_name}] Retry {attempt + 1}/{max_retries} with temperature {current_temp:.2f}")
            else:
                strict_prompt = prompt

            response, usage_stats = await call_llm(
                model=model,
                prompt=strict_prompt,
                system_prompt=system_prompt or "Output JSON ONLY. No markdown. No explanations.",
                temperature=current_temp,
                max_tokens=max_tokens
            )

            # Check for content policy refusals BEFORE validating JSON
            refusal_patterns = [
                "i'm sorry, i can't assist",
                "i cannot assist",
                "i can't help with that",
                "i cannot help with that",
                "desculpe, não posso ajudar",
                "não posso ajudar com isso"
            ]
            if any(refusal in response.lower() for refusal in refusal_patterns):
                logger.warning(f"[{stage_name}] Content policy refusal detected: {response[:100]}")
                raise ValueError(f"Content policy refusal: {response[:100]}")

            # Validate JSON
            json.loads(response)  # Will raise JSONDecodeError if invalid

            # Log usage to cost tracker
            if cost_tracker:
                cost_tracker.log_usage(
                    stage_name,
                    model,
                    usage_stats["input_tokens"],
                    usage_stats["output_tokens"]
                )

            logger.info(f"[{stage_name}] ✅ Valid JSON received (attempt {attempt + 1})")
            return response, usage_stats

        except json.JSONDecodeError as e:
            last_error = e
            logger.error(f"[{stage_name}] JSON parse error on attempt {attempt + 1}: {e}")
            logger.error(f"[{stage_name}] Response preview: {response[:1000] if 'response' in locals() else 'No response'}")

            if attempt == max_retries - 1:
                # Last attempt - log full response
                logger.error(f"[{stage_name}] All {max_retries} attempts failed!")
                logger.error(f"[{stage_name}] Full response: {response if 'response' in locals() else 'No response'}")
                raise Exception(f"{stage_name} failed after {max_retries} attempts: {e}")

        except ValueError as e:
            # Content policy refusal - preserve ValueError type for fallback handling
            last_error = e
            logger.error(f"[{stage_name}] LLM call failed on attempt {attempt + 1}: {str(e)}")

            if attempt == max_retries - 1:
                # Re-raise as ValueError so fallback logic can catch it
                raise ValueError(f"{stage_name} failed after {max_retries} attempts: {str(e)}")

        except Exception as e:
            last_error = e
            logger.error(f"[{stage_name}] LLM call failed on attempt {attempt + 1}: {str(e)}")

            if attempt == max_retries - 1:
                raise Exception(f"{stage_name} failed after {max_retries} attempts: {str(e)}")

    # Should never reach here, but just in case
    raise Exception(f"{stage_name} failed: {last_error}")


async def call_llm(
    model: str,
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4000,
    response_format: str = "json"
) -> tuple[str, dict]:
    """
    Generic LLM caller for any OpenRouter model

    Returns:
        (content, usage_stats) where usage_stats = {"input_tokens": int, "output_tokens": int}
    """

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://strategy-ai.com",
        "X-Title": "Strategy AI - Multi-Stage Analysis",
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            logger.info(f"[LLM] Calling {model} (prompt: {len(prompt)} chars)")

            response = await client.post(OPENROUTER_URL, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"].strip()

                # Clean markdown code blocks if JSON expected
                if response_format == "json":
                    # Handle markdown code blocks
                    if "```json" in content:
                        # Extract content between ```json and ```
                        start = content.find("```json") + 7
                        end = content.find("```", start)
                        if end != -1:
                            content = content[start:end].strip()
                    elif "```" in content:
                        # Extract content between ``` and ```
                        start = content.find("```") + 3
                        end = content.find("```", start)
                        if end != -1:
                            content = content[start:end].strip()

                    # Try to find JSON object if embedded in text
                    if not content.startswith("{") and "{" in content:
                        json_start = content.find("{")
                        content = content[json_start:]

                    # Find matching closing brace
                    if content.startswith("{"):
                        brace_count = 0
                        for i, char in enumerate(content):
                            if char == "{":
                                brace_count += 1
                            elif char == "}":
                                brace_count -= 1
                                if brace_count == 0:
                                    content = content[:i+1]
                                    break

                # Extract usage stats
                usage = data.get("usage", {})
                usage_stats = {
                    "input_tokens": usage.get("prompt_tokens", 0),
                    "output_tokens": usage.get("completion_tokens", 0)
                }

                logger.info(f"[LLM] {model} responded ({len(content)} chars, {usage_stats['input_tokens']} in, {usage_stats['output_tokens']} out)")
                return content, usage_stats
            else:
                raise Exception(f"Unexpected API response: {data}")

    except httpx.TimeoutException:
        raise Exception(f"LLM call to {model} timed out after {TIMEOUT}s")
    except httpx.HTTPStatusError as e:
        raise Exception(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"LLM call failed: {str(e)}")


# ============================================================================
# CACHE-AWARE STAGE WRAPPER
# ============================================================================

async def run_stage_with_cache(
    stage_name: str,
    stage_function: callable,
    company: str,
    industry: str,
    input_data: Dict[str, Any],
    estimated_cost: float,
    **stage_kwargs
) -> Dict[str, Any]:
    """
    Execute a stage with automatic caching

    Args:
        stage_name: Name of the stage (e.g., "extraction", "strategy")
        stage_function: The async function to call if cache miss
        company: Company name (for cache key)
        industry: Industry (for cache key)
        input_data: Input data to hash for cache key
        estimated_cost: Estimated cost of running this stage (for cache metrics)
        **stage_kwargs: Additional kwargs to pass to stage_function

    Returns:
        Stage result dict (from cache or fresh execution)
    """
    try:
        # Check cache first
        cached_result = await get_cached_stage_result(
            stage_name=stage_name,
            company=company,
            industry=industry,
            input_data=input_data
        )

        if cached_result:
            logger.info(f"[CACHE HIT] ✅ Stage '{stage_name}' loaded from cache (saves ${estimated_cost:.4f})")
            # Ensure cached results have _usage_stats (set to 0 for cache hits)
            if "_usage_stats" not in cached_result:
                cached_result["_usage_stats"] = {"input_tokens": 0, "output_tokens": 0}
            return cached_result

        # Cache miss - execute stage
        logger.info(f"[CACHE MISS] Stage '{stage_name}' - executing fresh...")
        result = await stage_function(**stage_kwargs)

        # Cache the result (async, non-blocking)
        try:
            await cache_stage_result(
                stage_name=stage_name,
                company=company,
                industry=industry,
                input_data=input_data,
                stage_result=result,
                cost=estimated_cost
            )
        except Exception as cache_error:
            # Don't fail the stage if caching fails
            logger.warning(f"[CACHE] Failed to cache stage '{stage_name}': {cache_error}")

        return result

    except Exception as e:
        # If anything goes wrong with caching, just run the stage
        logger.warning(f"[CACHE] Error in cache wrapper for '{stage_name}': {e}")
        # CRITICAL FIX: Include company and industry in fallback call
        return await stage_function(company=company, industry=industry, **stage_kwargs)


# ============================================================================
# STAGE 1: DATA EXTRACTION & STRUCTURING (Gemini Flash - CHEAP)
# ============================================================================

async def stage1_extract_data(
    company: str,
    industry: str,
    website: Optional[str],
    challenge: Optional[str],
    apify_data: Optional[Dict[str, Any]],
    perplexity_data: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 1: Extract structured facts from all data sources
    Model: Gemini Flash (ultra-cheap, good at extraction)
    Cost: ~$0.002 per call
    """

    logger.info("[STAGE 1] Extracting structured data...")

    # Sanitize all external data before injection
    safe_apify_data = sanitize_dict_recursive(apify_data, max_length=3000) if apify_data else None
    safe_perplexity_data = sanitize_dict_recursive(perplexity_data, max_length=3000) if perplexity_data else None

    logger.info(f"[STAGE 1] Data sanitized for prompt injection")

    # Build context with sanitized data
    data_context = f"""# RAW DATA SOURCES

## Company Information
- Name: {company}
- Industry: {industry}
- Website: {website or 'N/A'}
- Challenge: {challenge or 'N/A'}

## Apify Data (Web Scraping) - SANITIZED
{json.dumps(safe_apify_data, indent=2, ensure_ascii=False) if safe_apify_data else 'No Apify data'}

## Perplexity Data (Real-Time Research) - SANITIZED
{json.dumps(safe_perplexity_data, indent=2, ensure_ascii=False) if safe_perplexity_data else 'No Perplexity data'}
"""

    prompt = f"""{data_context}

# YOUR TASK

Extract and structure ALL key facts from the data above into clean JSON.

**What to extract:**
1. Company facts (size, location, team, products, revenue if mentioned)
2. Competitor names and key data points (pricing, features, market share)
3. Market size numbers (TAM, SAM, SOM if mentioned)
4. Industry trends (specific trends with dates and data)
5. Quantitative metrics (growth rates, percentages, dollar amounts)
6. News and recent developments (with dates)
7. Customer/user sentiment
8. Technology stack or business model details

**CRITICAL - SOURCE ATTRIBUTION:**
- For ALL quantitative claims (currency amounts, percentages, market share, etc.), include the source
- Format: "R$ X milhões (fonte: Website da empresa)" or "15% crescimento (fonte: Relatório Perplexity)"
- If no concrete source: Use "Estimativa baseada em [contexto]" or "N/A - dados insuficientes"
- NEVER fabricate specific numbers without a source

**What to SKIP:**
- Marketing fluff without substance
- Vague statements ("growing rapidly" without numbers)
- Duplicate information

**Data Gaps Identification:**
List any critical missing information that would help strategic analysis:
- Missing competitor data
- Missing market sizing
- Missing financial metrics
- Missing customer feedback
- Missing industry benchmarks

**Output Format (JSON ONLY):**

```json
{{
  "company_facts": {{
    "name": "{company}",
    "industry": "{industry}",
    "description": "Brief 1-2 sentence description",
    "founded": "Year or N/A",
    "location": "City/Region or N/A",
    "team_size": "Number or N/A",
    "revenue": "Estimated or N/A",
    "business_model": "B2B/B2C/Marketplace etc.",
    "products_services": ["Product 1", "Product 2"],
    "key_metrics": {{
      "customers": "Number or N/A",
      "growth_rate": "% or N/A",
      "funding": "Amount or N/A"
    }}
  }},

  "competitors": [
    {{
      "name": "Competitor Name",
      "positioning": "Premium/Mid-market/Budget",
      "market_share": "% or N/A",
      "pricing": "$ or N/A",
      "strengths": ["Strength 1", "Strength 2"],
      "weaknesses": ["Weakness 1"],
      "recent_news": "Latest development with date"
    }}
  ],

  "market_intelligence": {{
    "tam_total_market": "R$ X billion - description",
    "sam_available_market": "R$ Y million - description",
    "som_obtainable_market": "R$ Z million - description",
    "market_growth_rate": "% YoY",
    "market_maturity": "Emerging/Growing/Mature/Declining"
  }},

  "industry_trends": [
    {{
      "trend": "Trend name",
      "description": "1-2 sentences",
      "impact": "High/Medium/Low",
      "timeline": "When it's happening",
      "data_points": ["Specific stat 1", "Specific stat 2"]
    }}
  ],

  "news_and_developments": [
    {{
      "date": "YYYY-MM-DD or Month YYYY",
      "headline": "What happened",
      "impact": "Why it matters for {company}",
      "source": "Source if available"
    }}
  ],

  "customer_intelligence": {{
    "sentiment": "Positive/Neutral/Negative",
    "common_praise": ["Point 1", "Point 2"],
    "common_complaints": ["Point 1", "Point 2"],
    "nps_or_rating": "Score or N/A"
  }},

  "data_gaps": [
    "Missing: Exact market share of competitors",
    "Missing: Customer acquisition cost benchmarks",
    "Missing: Technology stack details"
  ]
}}
```

**IMPORTANT:** Return ONLY valid JSON. No markdown, no explanations.
"""

    system_prompt = "You are a data extraction specialist. Extract facts, skip fluff. Output JSON only."

    response, usage_stats = await call_llm_with_retry(
        stage_name="STAGE 1",
        model=MODEL_EXTRACTION,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.3,  # Lower temp for factual extraction
        max_tokens=4000
    )

    extracted_data = json.loads(response)
    logger.info(f"[STAGE 1] ✅ Extracted {len(extracted_data.get('competitors', []))} competitors, "
               f"{len(extracted_data.get('industry_trends', []))} trends, "
               f"{len(extracted_data.get('data_gaps', []))} gaps identified")

    # Add usage stats to result
    extracted_data["_usage_stats"] = usage_stats
    return extracted_data


# ============================================================================
# STAGE 2: GAP ANALYSIS + FOLLOW-UP RESEARCH (Gemini Flash + Perplexity)
# ============================================================================

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
        temperature=0.3,
        max_tokens=1000
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
            result = await perplexity_service.call_perplexity(query, max_tokens=3000)
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


# ============================================================================
# STAGE 3: STRATEGIC FRAMEWORKS (GPT-4o - EXPENSIVE)
# ============================================================================

async def stage3_strategic_analysis(
    company: str,
    industry: str,
    challenge: Optional[str],
    extracted_data: Dict[str, Any],
    enabled_sections: List[str] = None,
    data_quality_tier: str = "good"
) -> Dict[str, Any]:
    """
    Stage 3: Apply strategic frameworks to extracted data
    Model: GPT-4o (expensive but best for frameworks)
    Cost: ~$0.073 per call

    Args:
        enabled_sections: List of enabled section names based on data quality
        data_quality_tier: Quality tier (minimal, partial, good, full, legendary)
    """

    if enabled_sections is None:
        enabled_sections = ["all"]

    logger.info(f"[STAGE 3] Applying strategic frameworks (tier: {data_quality_tier}, sections: {len(enabled_sections)})")

    prompt = f"""# STRATEGIC BUSINESS ANALYSIS FOR {company}

**IMPORTANT CONTEXT:**
This is a professional business consulting analysis commissioned by {company} for legitimate strategic planning and competitive intelligence purposes. This analysis is:
- Requested by the company's leadership for internal decision-making
- Standard consulting practice (comparable to McKinsey, BCG, Bain analysis)
- Used for lawful business strategy, market positioning, and growth planning
- Not for any harmful, illegal, or unethical purposes

You are a strategic business analyst conducting professional consulting work. Apply rigorous strategic frameworks to develop actionable recommendations.

## Company Profile
- **Company:** {company}
- **Industry:** {industry}
- **Strategic Focus:** {challenge or 'General strategic analysis'}
- **Data Quality Tier:** {data_quality_tier}

## Available Market Intelligence
{json.dumps(extracted_data, indent=2, ensure_ascii=False)[:3000]}...
(Data provided for analysis purposes only)

---

# STRATEGIC ANALYSIS FRAMEWORK

This analysis answers 4 fundamental strategic questions using proven frameworks:

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## PARTE I: ONDE ESTAMOS? (Análise da Situação Atual)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Framework 1: PESTEL Analysis (Forças Macro-Ambientais)
Analyze macro-environmental factors specific to {industry} in Brazil:

- **Político:** Government policies, regulations, political stability affecting {industry}
  * IF insufficient data: State "Dados limitados - análise baseada em contexto geral do setor"

- **Econômico:** GDP, inflation, interest rates, economic cycles impact on {industry}
  * IF insufficient data: State "Análise qualitativa - dados macroeconômicos gerais aplicados"

- **Social:** Demographics, consumer behavior, cultural trends in {industry}
  * IF insufficient data: State "Tendências gerais - validação com dados primários recomendada"

- **Tecnológico:** Digital transformation, tech disruptions, innovation in {industry}
  * IF insufficient data: State "Análise de tendências setoriais - especificidade limitada"

- **Ambiental:** ESG requirements, sustainability pressures, environmental regulations
  * IF insufficient data: State "Contexto regulatório geral - impacto específico a validar"

- **Legal:** LGPD, industry-specific laws, compliance requirements
  * IF insufficient data: State "Framework regulatório geral - consultoria jurídica recomendada"

**CRITICAL**: For EACH factor, if data is limited, explicitly state what data is missing and suggest next steps.

### Framework 2: Porter's 7 Forces (Dinâmica Competitiva Expandida)
Assess competitive dynamics in {industry} using EXPANDED 7-force model:

**TRADITIONAL FORCES:**
1. **Ameaça de Novos Entrantes** (barriers to entry, capital requirements, regulation)
   * Rating: Low/Medium/High + specific justification with data
   * IF insufficient data: State "Avaliação qualitativa - dados de investimento setorial necessários"

2. **Poder de Barganha dos Fornecedores** (supplier concentration, switching costs)
   * Rating: Low/Medium/High + specific justification
   * IF insufficient data: State "Análise preliminar - mapeamento completo de cadeia recomendado"

3. **Poder de Barganha dos Compradores** (buyer concentration, price sensitivity)
   * Rating: Low/Medium/High + specific justification
   * IF insufficient data: State "Estimativa baseada em padrões setoriais - pesquisa com clientes recomendada"

4. **Ameaça de Produtos Substitutos** (alternative solutions, price-performance)
   * Rating: Low/Medium/High + specific justification
   * IF insufficient data: State "Mapeamento inicial - análise profunda de substitutos pendente"

5. **Rivalidade entre Concorrentes** (market concentration, growth rate, differentiation)
   * Rating: Low/Medium/High + specific justification
   * IF insufficient data: State "Análise baseada em concorrentes identificados - mercado completo a mapear"

**MODERN FORCES (Critical for 2025+):**
6. **Poder de Parcerias & Ecossistemas** (platform dynamics, ecosystem lock-in, network effects)
   * How do partnerships/platforms/ecosystems affect competitive position?
   * Are there dominant platforms in {industry}? (e.g., marketplaces, SaaS platforms)
   * Rating: Low/Medium/High + specific examples
   * IF insufficient data: State "Ecossistema digital a mapear - parcerias estratégicas a identificar"

7. **Disrupção por Inovação/Dados/IA** (AI adoption, data moats, automation threats)
   * How is AI/automation changing {industry}?
   * What data advantages exist? Who has data moats?
   * What innovations threaten traditional players?
   * Rating: Low/Medium/High + specific technologies
   * IF insufficient data: State "Mapeamento tecnológico preliminar - auditoria de IA/dados recomendada"

**CRITICAL**: Rate each force AND explain data confidence level (high/medium/low).

### Framework 3: SWOT Analysis (Capacidades Internas vs Ambiente Externo)
Based on available data, identify:

**STRENGTHS (Forças):** 4-6 specific strengths
- Each strength must include:
  * Description with specific evidence
  * Confidence level: "Alta (fonte primária)" / "Média (estimativa)" / "Baixa (dados limitados)"
  * Competitive impact: Alto/Médio/Baixo
  * IF no data: State "Força potencial - validação interna necessária"

**WEAKNESSES (Fraquezas):** 4-6 specific weaknesses
- Each weakness must include:
  * Description with impact assessment
  * Confidence level: "Alta/Média/Baixa"
  * Criticality: Crítica/Importante/Menor
  * IF no data: State "Área de atenção - auditoria interna recomendada"

**OPPORTUNITIES (Oportunidades):** 4-6 opportunities
- Each opportunity must include:
  * Description with market size/growth data IF AVAILABLE
  * Confidence level based on data quality
  * Timeframe: Curto prazo (0-6m) / Médio (6-18m) / Longo (18m+)
  * IF no data: State "Oportunidade identificada - dimensionamento pendente"

**THREATS (Ameaças):** 4-6 threats
- Each threat must include:
  * Description with probability assessment
  * Confidence level based on data
  * Mitigation strategy
  * IF no data: State "Risco potencial - monitoramento recomendado"

**CRITICAL**: Every SWOT item must show its data confidence level.

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## PARTE II: PARA ONDE QUEREMOS IR? (Posicionamento Estratégico)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Framework 4: Blue Ocean Strategy (Espaços de Mercado Não Contestados)
Identify how {company} can create uncontested market space:

- **Eliminar:** What factors the industry takes for granted that should be eliminated?
  * IF insufficient competitive data: State "Mapeamento de mercado limitado - benchmarking profundo recomendado"

- **Reduzir:** What factors should be reduced well below industry standard?
  * IF no cost/feature data: State "Análise de custos/features necessária para decisões precisas"

- **Elevar:** What factors should be raised well above industry standard?
  * IF limited differentiation data: State "Pesquisa de valor percebido pelo cliente recomendada"

- **Criar:** What factors should be created that the industry has never offered?
  * IF no innovation data: State "Workshops de inovação e pesquisa de necessidades não atendidas recomendados"

**CRITICAL**: If data for Blue Ocean is limited, provide qualitative framework but state "Validação com clientes e análise competitiva profunda necessária".

### Framework 5: Competitive Positioning (Posicionamento no Mercado)
Market landscape analysis:
- **Competitor mapping** (premium, mid-market, budget, niche positioning)
  * IF limited competitor data: State "Lista de concorrentes identificados limitada - mapeamento completo pendente"

- **Key differentiators** in the market
  * IF no feature comparison: State "Matriz comparativa detalhada recomendada"

- **Market share trends** (if available)
  * IF no market share data: State "Dados de market share indisponíveis - pesquisa setorial ou estimativas baseadas em receita necessárias"

- **Pricing strategies** comparison
  * IF no pricing data: State "Mystery shopping ou pesquisa de preços recomendada"

- **{company}'s unique value proposition**
  * Based on available data, define positioning
  * IF positioning unclear: State "Definição de posicionamento requer workshop estratégico com liderança"

### Framework 6: TAM/SAM/SOM (Dimensionamento de Mercado)
- **TAM:** Total addressable market in R$ (with source/calculation)
  * IF no market data: Return "dados_insuficientes" format with recommendations
- **SAM:** Serviceable available market (realistic segment)
  * IF insufficient segmentation data: State "Segmentação de mercado requer pesquisa adicional"
- **SOM:** Serviceable obtainable market (18-month target)
  * IF no company revenue/capacity data: State "Projeção requer dados financeiros da empresa"

### Framework 7: Balanced Scorecard (Objetivos Estratégicos Organizados)
Organize strategic objectives across 4 perspectives:
- **Financial:** Revenue, margins, ROI targets
  * IF no financial data: State "Objetivos financeiros requerem demonstrações e metas da empresa"
- **Customer:** NPS, retention, acquisition goals
  * IF no customer data: State "Métricas de cliente requerem dados de CRM e pesquisas"
- **Internal Processes:** Efficiency, quality, speed improvements
  * IF limited process data: State "Auditoria de processos recomendada para objetivos específicos"
- **Learning & Growth:** Training, culture, technology initiatives
  * IF no org data: State "Avaliação organizacional necessária para metas de desenvolvimento"

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## PARTE III: COMO CHEGAR LÁ? (Planejamento Estratégico)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Framework 8: OKRs - Objectives & Key Results (Execução em 3 Trimestres)
For Q1, Q2, Q3 2025, create ambitious but achievable OKRs:
- **Objective:** Qualitative, aspirational goal
- **Key Results:** 3-5 MEASURABLE outcomes with specific numbers
- **KPIs:** Metrics to track progress (with targets)
- **Owner:** Suggested role (CEO, CMO, CTO, etc.)
- **Investment:** Estimated cost in R$
  * IF no budget data: State "Estimativa baseada em benchmarks setoriais - validação com CFO necessária"

### Framework 9: Implementation Roadmap (Plano de Ação Tático)
Break down execution into phases:
- **Primeiros 30 dias:** Quick wins, low-hanging fruit
  * IF unclear priorities: State "Priorização requer workshop com equipe de liderança"
- **60-90 dias:** Medium-term initiatives, foundational work
- **6 meses:** Strategic initiatives, transformational projects
  * IF no resource data: State "Roadmap detalhado requer mapeamento de capacidades internas"

### Framework 10: Growth Hacking Loops (Loops de Crescimento Viral)
Design VIRAL GROWTH LOOPS para acelerar crescimento não-linear:

**LEAP Loop (Acquisition):**
- **Land:** Como novos usuários chegam? (canais, iscas, lead magnets)
- **Engage:** Qual é o momento "Aha!"? (primeira value delivery)
- **Activate:** O que faz alguém virar usuário ativo?
- **Propagate:** Como usuários trazem novos usuários? (viral loop, referral, network effects)

**SCALE Loop (Retention & Monetization):**
- **Satisfy:** Como entregar valor contínuo? (features que criam hábito)
- **Convert:** Quando/como usuário se torna pagante?
- **Amplify:** Como aumentar LTV? (upsell, cross-sell, expansion)
- **Loop back:** Como pagantes trazem mais pagantes? (case studies, advocacy)
- **Expand:** Quando entra in novo segmento/geografia?

**FOR EACH LOOP:**
- Identify current metrics (conversion rates at each stage)
  * IF no data: State "Implementação de analytics necessária para medir loops"
- Bottlenecks: Where is the biggest drop-off?
- Growth lever: What 10% improvement would yield biggest impact?
- Experiment ideas: 2-3 testable hypotheses to improve loop
  * IF unclear: State "Testes A/B e experimentação rápida recomendados"

**CRITICAL**: Applicable mainly for digital/platform/SaaS businesses. For traditional businesses, adapt loops to sales/distribution cycles.

## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
## PARTE IV: O QUE FAZER AGORA? (Ações Prioritárias & Riscos)
## ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

### Framework 11: Scenario Planning (Planejamento de Cenários 12-18 meses) + Probabilistic Modeling
Create 3 plausible futures with QUANTITATIVE probability modeling:

**FOR EACH SCENARIO:**
- **Probabilidade base:** X% (sum must equal 100%)
- **Triggers/gatilhos:** What events must occur for this scenario?
- **Impacto receita:** Range (min-max) not single number
  * Example: "Receita entre R$ 5-8 mi (cenário otimista)" not "Receita de R$ 6.5 mi"
  * IF no financial data: "Projeção qualitativa - dados financeiros necessários"
- **Variáveis-chave:** What variables drive this scenario?
- **Sensibilidade:** How sensitive is this scenario to key variables?
- **Ações requeridas:** What actions enable/respond to this scenario?

**PROBABILISTIC ENHANCEMENTS (when data available):**
1. **Identify 3-5 key variables** with uncertainty:
   - Example: "Taxa de conversão: 2-5% (distribuição normal, média 3.5%)"
   - Example: "CAC: R$ 80-150 (distribuição uniforme)"
   - IF no data: "Variáveis a calibrar com dados históricos"

2. **Monte Carlo simulation concept** (simplified):
   - "Se rodarmos 1000 simulações variando [var1] e [var2], temos:"
   - "70% de chance de receita entre R$ X-Y"
   - "20% de chance de receita > R$ Z"
   - "10% de chance de receita < R$ W"
   - IF can't model: "Modelagem estocástica recomendada para quantificar incerteza"

3. **Sensitivity tornado chart (verbal):**
   - Rank variables by impact: "Variável mais crítica: taxa de conversão (impacto 40%) > CAC (30%) > churn (20%) > pricing (10%)"
   - IF insufficient data: "Análise de sensibilidade pendente - requer calibração de modelo"

**3 SCENARIOS:**
- **Cenário Otimista (20-25%):** Best case
- **Cenário Realista (50-60%):** Most likely (ALWAYS provide)
- **Cenário Pessimista (15-20%):** Worst case

### Framework 12: Priority Recommendations (Top 3-5 Ações Estratégicas)
Recommend 3-5 HIGH-IMPACT actions specific to {company}:
- Each must be SPECIFIC to {company} (not generic consulting advice)
- Include: WHY (justification), HOW (implementation steps), WHEN (timeline)
- Show expected ROI or impact
  * IF ROI uncertain: State "ROI estimado - piloto recomendado para validação"
- Identify risks and mitigation strategies
  * IF risk assessment limited: State "Análise de riscos detalhada pendente"

### Framework 13: Multi-Criteria Decision Matrix (Para Decisões Complexas: M&A, Parcerias, Investimentos)
**WHEN TO USE:** When {company} faces a major strategic decision between 2-4 clear options (e.g., "Should we acquire Competitor X?", "Enter market Y or Z?", "Build, buy, or partner?")

**IF NO MAJOR DECISION IDENTIFIED:** State "Nenhuma decisão multi-critério crítica identificada no momento. Framework disponível para futuras decisões estratégicas."

**IF DECISION EXISTS:** Apply AHP (Analytical Hierarchy Process) + TOPSIS methodology:

**1. Define Decision:** What are we deciding? (e.g., "Qual acquisition target priorizar?")

**2. Alternative Options:** List 2-4 concrete alternatives (e.g., "Adquirir Empresa A", "Adquirir Empresa B", "Crescimento orgânico")

**3. Evaluation Criteria (5-7 criteria):**
Common criteria for strategic decisions:
- **Strategic Fit:** Alignment with vision/mission (weight: usually 20-25%)
- **Financial Viability:** NPV, payback period, ROI (weight: 20-25%)
- **Risk Level:** Execution risk, market risk, integration risk (weight: 15-20%)
- **Time to Value:** How fast will it deliver results? (weight: 10-15%)
- **Capability Gap:** Does it fill a critical gap? (weight: 10-15%)
- **Market Opportunity:** TAM, growth potential (weight: 10-15%)
- **Feasibility:** Do we have resources/expertise to execute? (weight: 5-10%)

**4. Scoring Matrix:**
For EACH option, score 0-10 on each criterion
  * IF insufficient data: State "Análise aprofundada de [criterion] necessária para pontuação precisa"

**5. Weighted Score:**
Calculate weighted total for each option (score × weight)

**6. Sensitivity Analysis:**
"Se aumentarmos peso de [criterion] para X%, a decisão muda?"
Identify which criteria are decision-drivers

**7. Recommendation:**
Recommend highest-scoring option WITH confidence level
  * IF scores are close (< 10% difference): "Decisão marginal - due diligence aprofundada recomendada"
  * IF clear winner (> 25% difference): "Opção [X] claramente superior - prosseguir com confiança"

**CRITICAL:** This framework is overkill for small decisions. Use ONLY for decisions > R$ 500k investment OR strategic inflection points.

---

# OUTPUT FORMAT (JSON ONLY)

```json
{{
  "sumario_executivo": "3-4 paragraphs: (1) Current situation with data quality note, (2) Key findings across 4 questions, (3) Priority recommendations with expected impact",

  "parte_1_onde_estamos": {{
    "analise_pestel": {{
      "politico": "2-3 paragraphs with specific examples OR 'Dados limitados - análise baseada em contexto geral'",
      "economico": "2-3 paragraphs with data OR 'Análise qualitativa - dados macroeconômicos gerais aplicados'",
      "social": "2-3 paragraphs with trends OR 'Tendências gerais - validação recomendada'",
      "tecnologico": "2-3 paragraphs with innovations OR 'Análise de tendências setoriais'",
      "ambiental": "2 paragraphs with ESG OR 'Contexto regulatório geral'",
      "legal": "2 paragraphs with regulations OR 'Framework regulatório geral'",
      "confianca_dados": "Alta/Média/Baixa based on data availability",
      "metodologia_prompt": {{
        "framework": "PESTEL (Political, Economic, Social, Technological, Environmental, Legal)",
        "modelo_prompt": "SCAN (Situação, Contexto, Análise, Next steps) - análise macro-ambiental",
        "fontes_dados": ["Website da empresa", "Notícias do setor via Perplexity", "Dados macroeconômicos públicos (IBGE, Banco Central)"],
        "como_melhorar": "Para aprofundar: (1) Relatórios setoriais específicos, (2) Consultoria regulatória, (3) Pesquisa primária com stakeholders",
        "replicar_analise": "Use SCAN framework: mapear Situação atual → Contexto regulatório → Análise de impacto → Próximos passos estratégicos"
      }}
    }},

    "sete_forcas_porter": {{
      "forcas_tradicionais": {{
        "ameaca_novos_entrantes": {{
          "analise": "2-3 paragraphs",
          "intensidade": "Low/Medium/High",
          "justificativa": "Specific reasoning",
          "confianca_dados": "Alta/Média/Baixa"
        }},
        "poder_fornecedores": {{
          "analise": "...",
          "intensidade": "Low/Medium/High",
          "justificativa": "...",
          "confianca_dados": "Alta/Média/Baixa"
        }},
        "poder_compradores": {{
          "analise": "...",
          "intensidade": "Low/Medium/High",
          "justificativa": "...",
          "confianca_dados": "Alta/Média/Baixa"
        }},
        "ameaca_substitutos": {{
          "analise": "...",
          "intensidade": "Low/Medium/High",
          "justificativa": "...",
          "confianca_dados": "Alta/Média/Baixa"
        }},
        "rivalidade_concorrentes": {{
          "analise": "...",
          "intensidade": "Low/Medium/High",
          "justificativa": "...",
          "confianca_dados": "Alta/Média/Baixa"
        }}
      }},
      "forcas_modernas": {{
        "poder_parcerias_ecossistemas": {{
          "analise": "How do platforms/partnerships affect competitive position?",
          "intensidade": "Low/Medium/High",
          "exemplos": ["Marketplace X", "Platform Y"],
          "confianca_dados": "Alta/Média/Baixa"
        }},
        "disrupcao_ia_dados": {{
          "analise": "How is AI/data changing the industry?",
          "intensidade": "Low/Medium/High",
          "tecnologias": ["AI tech 1", "Automation 2"],
          "confianca_dados": "Alta/Média/Baixa"
        }}
      }},
      "metodologia_prompt": {{
        "framework": "Porter's 7 Forces (5 forças tradicionais + 2 forças modernas 2025+)",
        "modelo_prompt": "RACE (Reunir dados, Analisar intensidade, Comparar concorrentes, Estimar impacto) - dinâmica competitiva",
        "fontes_dados": ["Scraping de competitors via Apify", "Análise de mercado via Perplexity", "Website e LinkedIn da empresa"],
        "como_melhorar": "Para aprofundar: (1) Análise completa de cadeia de valor, (2) Mapeamento de ecossistemas digitais, (3) Auditoria tecnológica (IA/dados)",
        "replicar_analise": "Use RACE framework: Reunir dados de concorrentes → Analisar cada força (1-7) → Comparar com indústria → Estimar impacto competitivo total"
      }}
    }},

    "analise_swot": {{
      "forcas": [
        {{
          "forca": "Specific strength",
          "evidencia": "Evidence/source",
          "confianca": "Alta (fonte primária) / Média (estimativa) / Baixa (dados limitados)",
          "impacto_competitivo": "Alto/Médio/Baixo"
        }}
      ],
      "fraquezas": [
        {{
          "fraqueza": "Specific weakness",
          "impacto": "Description",
          "confianca": "Alta/Média/Baixa",
          "criticidade": "Crítica/Importante/Menor"
        }}
      ],
      "oportunidades": [
        {{
          "oportunidade": "Specific opportunity",
          "dimensionamento": "Market size/growth if available OR 'Dimensionamento pendente'",
          "confianca": "Alta/Média/Baixa",
          "prazo": "Curto (0-6m) / Médio (6-18m) / Longo (18m+)"
        }}
      ],
      "ameacas": [
        {{
          "ameaca": "Specific threat",
          "probabilidade": "Assessment",
          "confianca": "Alta/Média/Baixa",
          "mitigacao": "Strategy"
        }}
      ],
      "metodologia_prompt": {{
        "framework": "SWOT Analysis com níveis de confiança",
        "modelo_prompt": "TRACE (Triangular dados, Reconhecer padrões, Avaliar confiança, Cruzar insights, Estabelecer prioridades)",
        "fontes_dados": ["Website e materiais da empresa", "Análise de concorrentes", "Tendências de mercado", "LinkedIn profiles"],
        "como_melhorar": "Para aprofundar: (1) Entrevistas internas (forças/fraquezas reais), (2) Pesquisa de mercado (oportunidades), (3) Análise de riscos quantitativa (ameaças)",
        "replicar_analise": "Use TRACE framework: Triangular dados de múltiplas fontes → Reconhecer padrões S/W/O/T → Avaliar confiança de cada insight → Cruzar com objetivos estratégicos → Estabelecer prioridades de ação"
      }}
    }}
  }},

  "parte_2_onde_queremos_ir": {{
    "estrategia_oceano_azul": {{
      "eliminar": ["Factor 1", "Factor 2"] OR ["Mapeamento limitado - benchmarking recomendado"],
      "reduzir": ["Factor 1"] OR ["Análise de custos necessária"],
      "elevar": ["Factor 1"] OR ["Pesquisa de valor percebido recomendada"],
      "criar": ["Factor 1"] OR ["Workshops de inovação recomendados"],
      "confianca_dados": "Alta/Média/Baixa",
      "metodologia_prompt": {{
        "framework": "Blue Ocean Strategy (Eliminar-Reduzir-Elevar-Criar)",
        "modelo_prompt": "CREATE (Comparar indústria, Reconstruir fronteiras, Eliminar/Reduzir fatores, Avaliar valor percebido, Testar hipóteses, Executar piloto)",
        "fontes_dados": ["Análise competitiva", "Pesquisa de valor percebido (quando disponível)", "Tendências de inovação setorial"],
        "como_melhorar": "Para aprofundar: (1) Workshops com clientes (valor percebido), (2) Benchmarking cross-industry, (3) Prototipagem rápida de novos fatores",
        "replicar_analise": "Use CREATE framework: Comparar canvas competitivo → Reconstruir fronteiras de mercado → Eliminar/Reduzir fatores que não agregam valor → Avaliar o que elevar → Testar novos fatores a criar → Executar MVP"
      }}
    }},

    "posicionamento_competitivo": {{
      "principais_concorrentes": [
        {{
          "nome": "Competitor A",
          "posicionamento": "Premium / Mid-market / Budget / Niche",
          "vantagens": "Specific advantages",
          "fraquezas": "Exploitable weaknesses",
          "share_estimado": "% or 'Indisponível'"
        }}
      ],
      "diferencial_unico": "{company}'s unique value proposition OR 'Definição requer workshop estratégico'",
      "matriz_posicionamento": "Where {company} sits vs competitors",
      "confianca_dados": "Alta/Média/Baixa",
      "metodologia_prompt": {{
        "framework": "Competitive Positioning Matrix",
        "modelo_prompt": "PAR (Posicionar no mercado, Analisar concorrentes, Recomendar diferenciação)",
        "fontes_dados": ["Scraping de competitors via Apify", "Análise de market share (quando disponível)", "Posicionamento via website/LinkedIn"],
        "como_melhorar": "Para aprofundar: (1) Pesquisa de percepção de marca, (2) Mystery shopping de concorrentes, (3) Análise detalhada de pricing",
        "replicar_analise": "Use PAR framework: Posicionar empresa em eixos relevantes (preço/qualidade, nicho/massa, etc.) → Analisar posicionamento dos concorrentes → Recomendar diferenciação estratégica"
      }}
    }},
"""

    # Conditional TAM/SAM/SOM section based on data quality
    tam_sam_som_enabled = "all" in enabled_sections or "tam_sam_som" in enabled_sections

    if not tam_sam_som_enabled or data_quality_tier in ["minimal", "partial"]:
        # Skip TAM/SAM/SOM for low quality data
        prompt += """
    "tam_sam_som": {{
      "status": "dados_insuficientes",
      "mensagem": "Análise TAM/SAM/SOM requer dados adicionais para evitar estimativas imprecisas",
      "o_que_fornecer": [
        "Demonstrações financeiras (últimos 2 anos)",
        "Faturamento atual da empresa",
        "Relatórios de mercado ou pesquisa setorial específica"
      ],
      "contexto_qualitativo": "Breve descrição do mercado sem números específicos",
      "proximos_passos": "Forneça dados financeiros para análise quantitativa precisa de mercado acessível.",
      "metodologia_prompt": {{
        "framework": "TAM/SAM/SOM Market Sizing",
        "modelo_prompt": "LIFT (Localizar dados de mercado, Inferir com sanity checks, Fundamentar premissas, Triangular fontes)",
        "nota_dados_insuficientes": "Análise quantitativa não realizada por falta de dados primários. Contexto qualitativo fornecido.",
        "como_melhorar": "Fornecer: (1) Faturamento atual da empresa, (2) Relatórios setoriais específicos, (3) Dados de market share"
      }}
    }},

    "balanced_scorecard": {{
      "perspectiva_financeira": ["Goal 1 with metric OR 'Requer demonstrações financeiras'", "..."],
      "perspectiva_cliente": ["Goal 1 OR 'Requer dados de CRM'", "..."],
      "perspectiva_processos": ["Goal 1 OR 'Requer auditoria de processos'", "..."],
      "perspectiva_aprendizado": ["Goal 1 OR 'Requer avaliação organizacional'", "..."],
      "confianca_dados": "Alta/Média/Baixa",
      "metodologia_prompt": {{
        "framework": "Balanced Scorecard (4 perspectivas equilibradas)",
        "modelo_prompt": "FOCUS (Financeiro, Operações, Clientes, Upskilling, Sincronizar métricas)",
        "fontes_dados": ["Objetivos estratégicos identificados", "KPIs típicos da indústria", "Dados da empresa (quando disponíveis)"],
        "como_melhorar": "Para aprofundar: (1) Definir KPIs específicos com metas numéricas, (2) Mapear relações causa-efeito entre perspectivas, (3) Alinhar com estratégia corporativa",
        "replicar_analise": "Use FOCUS framework: Definir metas Financeiras → Mapear processos/Operações críticos → Identificar drivers de satisfação de Clientes → Planejar Upskilling da equipe → Sincronizar métricas entre 4 perspectivas"
      }}
    }}
  }},"""
    else:
        # Full TAM/SAM/SOM when data is sufficient
        prompt += """
    "tam_sam_som": {{
      "tam_total_market": {{
        "valor": "R$ X bilhões (ex: R$ 50 bi)",
        "descricao": "Total market size for {industry} in Brazil/LATAM",
        "fonte": "CITE SOURCE (ex: 'IBGE 2024', 'Relatório Associação X', 'Website da empresa') OR mark as 'ESTIMATIVA baseada em [premissa específica]'",
        "ano_referencia": "2024",
        "confianca_dados": "Alta/Média/Baixa"
      }},
      "sam_available_market": {{
        "valor": "R$ Y bilhões (SAM ≤ TAM)",
        "descricao": "Addressable market for {company} (geographic/segment filters applied)",
        "premissas": ["Assumption 1", "Assumption 2"],
        "fonte": "Source OR 'ESTIMATIVA'",
        "confianca_dados": "Alta/Média/Baixa"
      }},
      "som_obtainable_market": {{
        "valor": "R$ Z milhões (SOM ≤ SAM)",
        "descricao": "Realistically obtainable market share in 3-5 years",
        "percentual_tam": "X.XX% do TAM",
        "premissas": [
          "Current market share or revenue",
          "Growth rate assumptions",
          "Competitive positioning factors"
        ],
        "validacao_sanity_check": "For small/new company: SOM should be 0.01-0.5% of TAM. For medium: 0.5-2%. For large: 2-10%. Explain if exceeds these ranges.",
        "fonte": "Source OR 'ESTIMATIVA'",
        "confianca_dados": "Alta/Média/Baixa"
      }},
      "crescimento_mercado": {{
        "taxa_anual": "X% CAGR (2024-2029)",
        "drivers": ["Key growth driver 1", "Driver 2"],
        "fonte": "Source OR 'Análise de tendências'",
        "confianca_dados": "Alta/Média/Baixa"
      }},
      "metodologia_prompt": {{
        "framework": "TAM/SAM/SOM Market Sizing",
        "modelo_prompt": "LIFT (Localizar dados de mercado, Inferir com sanity checks, Fundamentar premissas, Triangular fontes)",
        "fontes_dados": ["Relatórios setoriais (IBGE, associações)", "Perplexity market research", "Dados financeiros da empresa (quando disponíveis)"],
        "como_melhorar": "Para aprofundar: (1) Relatórios pagos de mercado (Gartner, IDC), (2) Demonstrações financeiras auditadas, (3) Pesquisa primária de market share",
        "replicar_analise": "Use LIFT framework: Localizar dados de TAM total → Inferir SAM (filtros geográficos/segmento) → Fundamentar SOM com premissas realistas → Triangular múltiplas fontes e validar sanity checks"
      }}
    }},

    "balanced_scorecard": {{
      "perspectiva_financeira": ["Goal 1 with metric OR 'Requer demonstrações financeiras'", "..."],
      "perspectiva_cliente": ["Goal 1 OR 'Requer dados de CRM'", "..."],
      "perspectiva_processos": ["Goal 1 OR 'Requer auditoria de processos'", "..."],
      "perspectiva_aprendizado": ["Goal 1 OR 'Requer avaliação organizacional'", "..."],
      "confianca_dados": "Alta/Média/Baixa",
      "metodologia_prompt": {{
        "framework": "Balanced Scorecard (4 perspectivas equilibradas)",
        "modelo_prompt": "FOCUS (Financeiro, Operações, Clientes, Upskilling, Sincronizar métricas)",
        "fontes_dados": ["Objetivos estratégicos identificados", "KPIs típicos da indústria", "Dados da empresa (quando disponíveis)"],
        "como_melhorar": "Para aprofundar: (1) Definir KPIs específicos com metas numéricas, (2) Mapear relações causa-efeito entre perspectivas, (3) Alinhar com estratégia corporativa",
        "replicar_analise": "Use FOCUS framework: Definir metas Financeiras → Mapear processos/Operações críticos → Identificar drivers de satisfação de Clientes → Planejar Upskilling da equipe → Sincronizar métricas entre 4 perspectivas"
      }}
    }}
  }},"""

    prompt += """
  "parte_3_como_chegar_la": {{
    "okrs_propostos": [
      {{
        "trimestre": "Q1 2025",
        "objetivo": "Ambitious qualitative goal",
        "resultados_chave": [
          "KR1: Measurable result with number",
          "KR2: ...",
          "KR3: ..."
        ],
        "metricas_kpi": ["KPI 1", "KPI 2", "..."],
        "responsavel_sugerido": "CEO / CMO / CTO / etc.",
        "investimento_estimado": "R$ X mil OR 'Estimativa - validação com CFO necessária'",
        "confianca_dados": "Alta/Média/Baixa"
      }},
      {{"trimestre": "Q2 2025", "...": "..."}},
      {{"trimestre": "Q3 2025", "...": "..."}}
    ],

    "roadmap_implementacao": {{
      "primeiros_30_dias": ["Quick win 1", "Quick win 2", "..."] OR ["Priorização requer workshop"],
      "60_90_dias": ["Initiative 1", "..."],
      "6_meses": ["Strategic initiative 1", "..."] OR ["Roadmap requer mapeamento de capacidades"],
      "confianca_dados": "Alta/Média/Baixa"
    }},

    "growth_hacking_loops": {{
      "aplicabilidade": "Alto/Médio/Baixo - Explain if applicable to {company}'s business model (digital/platform/SaaS vs traditional)",
      "leap_loop_acquisition": {{
        "land": "How users discover {company}? Current channels OR 'Definir estratégia de aquisição'",
        "engage": "What's the Aha! moment? OR 'Identificar value prop principal'",
        "activate": "What makes someone an active user? OR 'Definir critérios de ativação'",
        "propagate": "How do users bring new users? Viral coefficient OR 'Implementar programa de referral'",
        "metricas_atuais": "CAC, conversion rates (if available) OR 'Analytics a implementar'",
        "gargalo_principal": "Where's the biggest drop-off? OR 'Análise de funil necessária'",
        "alavanca_crescimento": "What 10% improvement would yield biggest impact?",
        "experimentos": ["Test 1", "Test 2"] OR ["Estruturar programa de growth experiments"]
      }},
      "scale_loop_monetizacao": {{
        "satisfy": "How to deliver continuous value? Features that create habit OR 'Product-market fit a validar'",
        "convert": "When/how do users become paying? Pricing strategy OR 'Modelo de monetização a definir'",
        "amplify": "How to increase LTV? Upsell/cross-sell opportunities OR 'Expansão de receita a mapear'",
        "loop_back": "How do paying customers bring more? Advocacy program OR 'Programa de advocacy a criar'",
        "expand": "When to enter new segment/geo? Expansion criteria OR 'Roadmap de expansão a desenvolver'",
        "metricas_atuais": "LTV, churn, expansion revenue (if available) OR 'Tracking financeiro a estruturar'",
        "gargalo_principal": "Where's retention/monetization failing?",
        "alavanca_crescimento": "What would double LTV?",
        "experimentos": ["Test 1", "Test 2"] OR ["Testes de pricing/packaging recomendados"]
      }},
      "confianca_dados": "Alta/Média/Baixa",
      "nota_aplicabilidade": "IF traditional business: 'Loops adaptados para ciclo de vendas B2B/distribuição física - foco em referrals e partnerships'"
    }},

    "metodologia_prompt_parte_3": {{
      "frameworks": "OKRs (Objectives & Key Results) + Roadmap de Implementação + Growth Hacking Loops",
      "modelo_prompt_okrs": "GROW (Goal setting, Reality check, Options exploration, Will to act) - definição de objetivos ambiciosos",
      "modelo_prompt_roadmap": "SHIFT (Short-term wins, High-impact initiatives, Future planning, Timelines realistas)",
      "modelo_prompt_growth": "LEAP + SCALE (loops de aquisição e monetização viral) - aplicável para negócios digitais/SaaS",
      "fontes_dados": ["Objetivos estratégicos das partes 1-2", "Capacidades da empresa (quando conhecidas)", "Benchmarks da indústria", "Métricas de produto (quando disponíveis)"],
      "como_melhorar": "Para aprofundar: (1) Workshop de OKRs com liderança, (2) Mapeamento de capacidades organizacionais, (3) Definir ownership e budgets específicos, (4) Implementar analytics para medir loops de crescimento",
      "replicar_analise": "Use GROW + SHIFT + LEAP/SCALE: Definir Goals ambiciosos → Reality check de viabilidade → Explorar Options de execução → Comprometer Will/ownership → Priorizar Short-wins → Identificar High-impact → Planejar Future → Definir Timelines → Desenhar loops virais (se aplicável)"
    }}
  }},

  "parte_4_o_que_fazer_agora": {{
    "planejamento_cenarios": {{
      "variaveis_chave_incerteza": [
        {{
          "variavel": "Taxa de conversão",
          "faixa": "2-5%",
          "distribuicao": "Normal (média 3.5%) OR 'Calibrar com dados históricos'",
          "impacto_relativo": "40% (mais crítica)"
        }},
        {{
          "variavel": "CAC (Custo Aquisição Cliente)",
          "faixa": "R$ 80-150",
          "distribuicao": "Uniforme OR 'Histórico necessário'",
          "impacto_relativo": "30%"
        }}
      ],
      "modelagem_probabilistica": {{
        "metodologia": "Monte Carlo simplificado (1000 simulações) OR 'Modelagem estocástica recomendada quando dados disponíveis'",
        "resultado_simulacao": "70% de chance de receita entre R$ X-Y; 20% > R$ Z; 10% < R$ W OR 'Quantificação pendente'",
        "analise_sensibilidade_tornado": "Ranking de impacto: [variável 1] (40%) > [variável 2] (30%) > [variável 3] (20%) OR 'Análise de sensibilidade a calibrar'",
        "confianca_modelo": "Alta/Média/Baixa - explain why"
      }},
      "cenario_otimista": {{
        "descricao": "What happens in best case",
        "probabilidade": "20-25%",
        "impacto_receita_range": "R$ MIN - R$ MAX (range, not single number) OR 'Projeção requer dados financeiros'",
        "gatilhos": ["Trigger 1", "Trigger 2"],
        "variaveis_assumidas": ["Variable 1 = upper bound", "Variable 2 = favorable"],
        "acoes_requeridas": ["Action 1", "Action 2"],
        "confianca_dados": "Alta/Média/Baixa"
      }},
      "cenario_realista": {{
        "descricao": "Most likely scenario (ALWAYS provide)",
        "probabilidade": "50-60%",
        "impacto_receita_range": "R$ MIN - R$ MAX",
        "gatilhos": ["..."],
        "variaveis_assumidas": ["Variable 1 = expected value", "..."],
        "acoes_requeridas": ["..."],
        "confianca_dados": "Alta/Média/Baixa"
      }},
      "cenario_pessimista": {{
        "descricao": "Worst case",
        "probabilidade": "15-20%",
        "impacto_receita_range": "R$ MIN - R$ MAX",
        "ameacas": ["Threat 1", "..."],
        "variaveis_assumidas": ["Variable 1 = lower bound", "..."],
        "estrategias_sobrevivencia": ["Strategy 1", "..."] OR ["Análise de riscos recomendada"],
        "confianca_dados": "Alta/Média/Baixa"
      }}
    }},

    "recomendacoes_prioritarias": [
    {{
      "prioridade": 1,
      "titulo": "Título conciso e ESPECÍFICO para {company} (NÃO genérico)",
      "recomendacao": "O QUE fazer - descrição detalhada ESPECÍFICA para o contexto de {company}. EVITE recomendações genéricas que poderiam aplicar a qualquer empresa.",
      "justificativa": "POR QUE - fundamentação baseada em dados específicos de {company} e seu mercado",
      "porque_especifico_para_empresa": "Explique por que esta recomendação é única para {company} e NÃO seria aplicável a todos os concorrentes",
      "como_implementar": ["Passo 1 específico", "Passo 2 específico", "Passo 3 específico"],
      "prazo": "Prazo realista",
      "investimento_estimado": "R$ X (com fonte ou marcado como 'Estimativa')",
      "retorno_esperado": "R$ Y em Z meses (com premissas ou marcado como 'Projeção')",
      "metricas_sucesso": ["Métrica 1 mensurável", "Métrica 2 mensurável"],
      "riscos_mitigacao": ["Risco 1 + mitigação", "Risco 2 + mitigação"]
    }},
    {{"prioridade": 2, "...": "..."}},
    {{"prioridade": 3, "...": "..."}}
  ],

    "matriz_decisao_multicriterio": {{
      "aplicavel": "Sim/Não - Is there a major strategic decision (> R$ 500k or strategic inflection point)?",
      "decisao": "What is being decided? (e.g., 'Qual acquisition target priorizar?') OR 'Nenhuma decisão multi-critério crítica identificada'",
      "opcoes_alternativas": [
        {{
          "opcao": "Option A (e.g., 'Adquirir Empresa X')",
          "descricao_breve": "Brief description"
        }},
        {{
          "opcao": "Option B (e.g., 'Adquirir Empresa Y')",
          "descricao_breve": "Brief description"
        }},
        {{
          "opcao": "Option C (e.g., 'Crescimento orgânico')",
          "descricao_breve": "Brief description"
        }}
      ],
      "criterios_avaliacao": [
        {{
          "criterio": "Strategic Fit",
          "peso": "25%",
          "justificativa_peso": "Why this weight? OR 'Definir pesos com stakeholders'"
        }},
        {{
          "criterio": "Financial Viability",
          "peso": "25%",
          "justificativa_peso": "..."
        }},
        {{
          "criterio": "Risk Level",
          "peso": "20%",
          "justificativa_peso": "..."
        }},
        {{
          "criterio": "Time to Value",
          "peso": "15%",
          "justificativa_peso": "..."
        }},
        {{
          "criterio": "Feasibility",
          "peso": "15%",
          "justificativa_peso": "..."
        }}
      ],
      "matriz_pontuacao": [
        {{
          "opcao": "Option A",
          "scores": {{
            "Strategic Fit": "8/10 - justification OR 'Análise necessária'",
            "Financial Viability": "7/10 - justification OR 'Due diligence financeira pendente'",
            "Risk Level": "6/10 - ...",
            "Time to Value": "9/10 - ...",
            "Feasibility": "7/10 - ..."
          }},
          "score_ponderado": "7.5/10 (weighted average)"
        }}
      ],
      "analise_sensibilidade": "If we increase weight of [criterion] to X%, does the decision change? Which criteria are decision-drivers? OR 'Modelagem quantitativa recomendada'",
      "recomendacao_final": {{
        "opcao_recomendada": "Option X",
        "score_final": "X.X/10",
        "margem_vitoria": "X% ahead of second option - 'Decisão clara' OR 'Decisão marginal'",
        "nivel_confianca": "Alto/Médio/Baixo",
        "proximos_passos": "Due diligence specific to this decision OR 'Workshop de decisão com board'"
      }},
      "confianca_dados": "Alta/Média/Baixa",
      "nota": "Framework aplicável apenas para decisões estratégicas complexas. Para decisões menores, seguir recomendações prioritárias."
    }},

    "metodologia_prompt_parte_4": {{
      "frameworks": "Planejamento de Cenários + Recomendações Prioritárias + Matriz de Decisão Multi-Critério",
      "modelo_prompt_cenarios": "LEAP (Listar variáveis-chave, Explorar cenários alternativos, Avaliar probabilidades, Preparar planos de ação)",
      "modelo_prompt_recomendacoes": "SCALE (Específico para empresa, Contexto claro, Acionável, Lógica fundamentada, Evidências/ROI)",
      "modelo_prompt_decisao": "AHP + TOPSIS (matriz multi-critério para decisões complexas > R$ 500k) - aplicável apenas quando há decisão estratégica clara",
      "fontes_dados": ["Análise completa das partes 1-3", "Variáveis de risco identificadas", "Tendências de mercado", "Opções estratégicas identificadas"],
      "como_melhorar": "Para aprofundar: (1) Modelagem quantitativa de cenários (Monte Carlo), (2) Workshops de war-gaming, (3) Planos de contingência detalhados, (4) Due diligence para decisões multi-critério",
      "replicar_analise": "Use LEAP + SCALE + AHP/TOPSIS: Listar variáveis críticas → Explorar 3 cenários → Avaliar probabilidades → Preparar ações → Recomendar iniciativas Específicas, com Contexto, Acionáveis, Lógica clara, Evidências de ROI → Se decisão complexa: aplicar matriz multi-critério"
    }}
  }},

  "ciclo_revisao": {{
    "recomendacao_frequencia": "Trimestral/Semestral/Anual (escolher baseado em volatilidade do setor)",
    "justificativa": "Explicar por que essa frequência (ex: 'Trimestral devido a rápida evolução tecnológica em {industry}')",
    "gatilhos_revisao_extraordinaria": [
      "Mudança regulatória significativa",
      "Entrada de novo concorrente disruptivo",
      "Fusão/aquisição no setor",
      "Mudança drástica em métricas-chave (>30%)",
      "Evento macroeconômico (crise, mudança cambial significativa)"
    ],
    "metricas_monitorar": [
      "Métrica crítica 1 (ex: NPS, CAC, LTV, market share)",
      "Métrica crítica 2",
      "Métrica crítica 3"
    ],
    "responsavel_revisao": "CEO + equipe estratégica (especificar se possível)",
    "formato_revisao": "Workshop estratégico de 4h com stakeholders-chave OR 'Definir governança'"
  }},

  "mapa_integracao_frameworks": {{
    "titulo": "Como os Frameworks se Conectam em Cenários Reais",
    "explicacao": "Esta análise não é uma lista isolada de frameworks, mas um sistema integrado. Veja como os insights fluem:",
    "fluxos_integracao": [
      {{
        "cenario": "Expansão de Mercado",
        "fluxo": "PESTEL (identificar oportunidade regulatória) → Porter 7 (avaliar barreiras de entrada) → TAM/SAM/SOM (quantificar oportunidade) → Blue Ocean (diferenciar posicionamento) → OKRs (definir metas de penetração) → Roadmap (implementar em fases)",
        "exemplo_aplicacao": "Ex: PESTEL identificou nova regulação favorável → Porter mostrou baixa rivalidade → TAM de R$ 5 bi confirmado → Blue Ocean sugeriu criar novo canal → OKR: penetrar 2% em Q3 → Roadmap: piloto em 30 dias"
      }},
      {{
        "cenario": "Resposta a Concorrente Disruptivo",
        "fluxo": "Porter 7 (detectar ameaça de disrupção IA) → SWOT (avaliar capacidades internas) → Posicionamento (analisar gap competitivo) → Cenários (modelar impacto 3-5 anos) → Recomendações (definir contra-ataque) → OKRs (implementar resposta rápida)",
        "exemplo_aplicacao": "Ex: Porter identificou startup com IA disruptiva → SWOT mostrou fraqueza em dados → Posicionamento confirmou perda de share → Cenário pessimista: -15% receita → Recomendação: M&A da startup → OKR: fechar aquisição em Q2"
      }},
      {{
        "cenario": "Otimização de Operações",
        "fluxo": "SWOT (identificar fraquezas operacionais) → BSC (mapear métricas de processos) → OKRs (definir metas de eficiência) → Roadmap (implementar melhorias) → Cenários (projetar impacto no EBITDA)",
        "exemplo_aplicacao": "Ex: SWOT identificou alto CAC → BSC mapeou funil de vendas → OKR: reduzir CAC 30% → Roadmap: automação de marketing em 60 dias → Cenário: EBITDA +5pp"
      }}
    ],
    "princípios_integracao": [
      "Análise externa (PESTEL, Porter) informa estratégia de posicionamento (Blue Ocean, TAM/SAM/SOM)",
      "Capacidades internas (SWOT) limitam ou habilitam execução (OKRs, Roadmap)",
      "Cenários futuros (Planejamento) validam ou refutam decisões estratégicas (Recomendações)",
      "Métricas (BSC) fecham o ciclo de feedback para revisão contínua (Ciclo Revisão)"
    ],
    "nota_importante": "Use este mapa para entender COMO e QUANDO aplicar cada framework na prática, não apenas O QUE cada um diz isoladamente."
  }},

  "referencias_casos_brasileiros": {{
    "titulo": "Casos de Sucesso Brasileiros para Inspiração",
    "explicacao": "Empresas brasileiras que aplicaram estratégias similares com sucesso. Use como benchmarks e aprendizado, NÃO como receita de bolo.",
    "casos_relevantes": [
      {{
        "empresa": "Nome da empresa (ex: Nubank, Stone, RaiaDrogasil, Magazine Luiza, Mercado Livre)",
        "setor": "Fintech / Varejo / Logística / etc.",
        "relevancia_para_caso": "Por que este caso é relevante para {company}? (indústria similar, desafio similar, escala similar)",
        "estrategia_aplicada": "Qual framework/estratégia usaram? (ex: Blue Ocean, Growth Hacking, M&A)",
        "resultado_mensuravel": "Impacto quantificado (ex: '300% crescimento em 3 anos', 'R$ 1 bi→ R$ 5 bi em valuation')",
        "licao_aplicavel": "O QUE {company} pode aprender? Ação específica a replicar",
        "diferenca_contexto": "O QUE é diferente? Por que não é cópia direta (escala, timing, mercado, recursos)",
        "fonte": "Onde encontrar mais? (ex: 'Case HBS 2023', 'Relatório anual Stone 2024', 'Entrevista Estadão Jan/2024')"
      }},
      {{
        "empresa": "Caso 2 (relevante se houver)",
        "...": "..."
      }}
    ],
    "anti_casos_evitar": [
      {{
        "empresa": "Empresa que falhou (ex: Americanas, Grupo X)",
        "erro_estrategico": "O que deu errado? (ex: 'Expansão agressiva sem controles', 'Ignorou disrupção digital')",
        "licao_para_evitar": "O QUE {company} NÃO deve fazer",
        "relevancia": "Por que mencionar este caso?"
      }}
    ],
    "nota_uso_casos": "Casos são para INSPIRAÇÃO e APRENDIZADO, não para CÓPIA. Adapte ao contexto único de {company}. Cada empresa tem timing, recursos e contexto competitivo distintos.",
    "confianca_dados": "Alta (casos públicos documentados) / Média (referências indiretas) / Baixa (analogias distantes)"
  }}
}}
```

**REQUIREMENTS CRÍTICOS:**

0. **HONESTIDADE ACIMA DE TUDO (REGRA ABSOLUTA):**
   - Se NÃO tem dados concretos → escreva "Dados insuficientes para análise quantitativa"
   - NUNCA invente números específicos sem fonte clara ou premissas explícitas
   - Prefira análise qualitativa a números fabricados
   - É MELHOR admitir falta de dados do que alucinar informações
   - Quando em dúvida: qualitativo > quantitativo inventado

1. **SANITY CHECKS OBRIGATÓRIOS (Validação de Realidade):**
   - **TAM/SAM/SOM:**
     * SOM para empresa PEQUENA: 0.01-0.5% do TAM (ex: TAM de R$ 100 bi → SOM de R$ 10-500 milhões)
     * SOM para empresa MÉDIA: 0.5-2% do TAM
     * SOM para empresa GRANDE: 2-10% do TAM
     * SOM > R$ 10 bilhões = improvável para maioria das empresas (apenas gigantes)
     * Hierarquia: SOM ≤ SAM ≤ TAM (sempre)
   - **Market Share:** Empresas novas/pequenas raramente > 5% do mercado total
   - **Crescimento:** Projeções > 100% ao ano exigem justificativa extraordinária

2. **FONTE DE DADOS:** Para TAM/SAM/SOM e números específicos:
   - SE houver fonte (website, documento, IBGE), cite explicitamente: "Segundo IBGE 2024" ou "Baseado em relatório X"
   - SE NÃO houver dados suficientes, use formato alternativo de "dados_insuficientes" (ver exemplo no JSON)
   - Se fizer estimativa, marque claramente: "ESTIMATIVA baseada em [premissa específica]"
   - NUNCA invente números sem indicar fonte ou premissa

3. **RECOMENDAÇÕES ESPECÍFICAS (NÃO GENÉRICAS):**
   - Cada recomendação deve ser única para {company}
   - Explique por que NÃO aplicaria a todos os concorrentes
   - Use contexto específico (produto, mercado, challenge fornecido)
   - EVITE: "expandir serviços", "inovar", "melhorar eficiência" (muito genérico)
   - PREFIRA: Ações específicas baseadas no contexto único de {company}

4. **QUALIDADE:**
   - Use números específicos (não "muitos", "alguns", "crescendo")
   - Baseie análise em fatos dos dados extraídos
   - Seja acionável (não acadêmico)
   - Português brasileiro profissional
   - Somente JSON válido, sem markdown

**SE DADOS INSUFICIENTES:** Seja honesto. Escreva "Análise limitada por falta de dados X, Y, Z" ao invés de inventar.
"""

    system_prompt = "You are a professional strategic business consultant (like McKinsey, BCG, Bain) helping companies develop legitimate competitive strategies for lawful business purposes. This is standard consulting work commissioned by the company's leadership. Apply strategic frameworks rigorously using available market data. Be specific, data-driven, and actionable. Output in Brazilian Portuguese (JSON only)."

    # Try GPT-4o first, fallback to Gemini Pro if content policy refusal
    usage_stats = {}
    try:
        response, usage_stats = await call_llm_with_retry(
            stage_name="STAGE 3",
            model=MODEL_STRATEGY,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.8,  # Higher for creative strategic thinking
            max_tokens=32000  # Increased from 16000 to prevent JSON truncation
        )

        # Refusal patterns are now checked inside call_llm_with_retry
        strategic_analysis = json.loads(response)

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"[STAGE 3] Primary model failed (likely content policy refusal or rate limit), falling back to paid fallback...")
        logger.warning(f"[STAGE 3] Original error: {str(e)}")

        try:
            # Fallback 1: Try paid fallback (Claude Sonnet)
            stage_config = get_stage_config("strategy")
            fallback_model = stage_config.get("fallback_model", MODEL_COMPETITIVE)

            response, usage_stats = await call_llm_with_retry(
                stage_name="STAGE 3 (FALLBACK 1)",
                model=fallback_model,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.8,
                max_tokens=32000  # Increased from 16000 to prevent JSON truncation
            )
            strategic_analysis = json.loads(response)

        except Exception as e2:
            logger.warning(f"[STAGE 3] Paid fallback failed, trying FREE fallback model...")
            logger.warning(f"[STAGE 3] Fallback 1 error: {str(e2)}")

            # Fallback 2: Use free model (Gemini Flash Free)
            free_fallback = stage_config.get("free_fallback_model", "google/gemini-2.0-flash-exp:free")

            response, usage_stats = await call_llm_with_retry(
                stage_name="STAGE 3 (FREE FALLBACK)",
                model=free_fallback,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=0.8,
                max_tokens=32000  # Increased from 16000 to prevent JSON truncation
            )
            strategic_analysis = json.loads(response)

    # ========================================================================
    # HALLUCINATION DETECTION & AUTO-FIX
    # ========================================================================
    from app.core.security.hallucination_detector import validate_market_sizing, detect_company_size, validate_numeric_claims
    from app.utils.validation import validate_source_attribution_strict

    # Detect company size for validation
    company_size = detect_company_size(extracted_data.get('company_info', {}))
    logger.info(f"[STAGE 3] Detected company size: {company_size}")

    # Validate TAM/SAM/SOM if present (handle new nested structure)
    if 'parte_2_onde_queremos_ir' in strategic_analysis and 'tam_sam_som' in strategic_analysis['parte_2_onde_queremos_ir']:
        tam_sam_som = strategic_analysis['parte_2_onde_queremos_ir']['tam_sam_som']

        # Only validate if it has numeric values (not the "dados_insuficientes" format)
        if not isinstance(tam_sam_som, dict) or tam_sam_som.get('status') != 'dados_insuficientes':
            # Extract nested values for new structure
            tam_value = tam_sam_som.get('tam_total_market', {})
            sam_value = tam_sam_som.get('sam_available_market', {})
            som_value = tam_sam_som.get('som_obtainable_market', {})

            # Handle both dict and string formats
            tam_str = tam_value.get('valor', '') if isinstance(tam_value, dict) else str(tam_value)
            sam_str = sam_value.get('valor', '') if isinstance(sam_value, dict) else str(sam_value)
            som_str = som_value.get('valor', '') if isinstance(som_value, dict) else str(som_value)

            validation = validate_market_sizing(
                tam=tam_str,
                sam=sam_str,
                som=som_str,
                company_size=company_size,
                company_name=company
            )

            if not validation['is_valid']:
                logger.error(f"[HALLUCINATION DETECTED] TAM/SAM/SOM validation failed:")
                logger.error(f"[HALLUCINATION] Severity: {validation['severity']}")
                for issue in validation['issues']:
                    logger.error(f"[HALLUCINATION] - {issue}")

                # Auto-fix by replacing with "dados_insuficientes" format
                if validation['auto_fix']:
                    logger.warning(f"[AUTO-FIX] Replacing TAM/SAM/SOM with 'dados_insuficientes' format")
                    strategic_analysis['parte_2_onde_queremos_ir']['tam_sam_som'] = validation['auto_fix']
    # Fallback: check old structure for backward compatibility
    elif 'tam_sam_som' in strategic_analysis:
        tam_sam_som = strategic_analysis['tam_sam_som']

        # Only validate if it has numeric values (not the "dados_insuficientes" format)
        if not isinstance(tam_sam_som, dict) or tam_sam_som.get('status') != 'dados_insuficientes':
            validation = validate_market_sizing(
                tam=tam_sam_som.get('tam_total_market', ''),
                sam=tam_sam_som.get('sam_available_market', ''),
                som=tam_sam_som.get('som_obtainable_market', ''),
                company_size=company_size,
                company_name=company
            )

            if not validation['is_valid']:
                logger.error(f"[HALLUCINATION DETECTED] TAM/SAM/SOM validation failed:")
                logger.error(f"[HALLUCINATION] Severity: {validation['severity']}")
                for issue in validation['issues']:
                    logger.error(f"[HALLUCINATION] - {issue}")

                # Auto-fix by replacing with "dados_insuficientes" format
                if validation['auto_fix']:
                    logger.warning(f"[AUTO-FIX] Replacing TAM/SAM/SOM with 'dados_insuficientes' format")
                    strategic_analysis['tam_sam_som'] = validation['auto_fix']

    # Validate other numeric claims
    numeric_validation = validate_numeric_claims(strategic_analysis)
    if not numeric_validation['is_valid']:
        logger.warning(f"[HALLUCINATION] Found {len(numeric_validation['violations'])} numeric claim violations:")
        for violation in numeric_validation['violations'][:5]:  # Log first 5
            logger.warning(f"[HALLUCINATION] - {violation}")

    # Strict source attribution validation
    source_validation = validate_source_attribution_strict(strategic_analysis)
    if not source_validation['is_valid']:
        logger.warning(f"[SOURCE ATTRIBUTION] Validation failed:")
        logger.warning(f"[SOURCE ATTRIBUTION] Severity: {source_validation['severity']}")
        logger.warning(f"[SOURCE ATTRIBUTION] Critical: {source_validation['critical_count']}, Warnings: {source_validation['warning_count']}")
        # Log violations but don't auto-fix (might be too aggressive)

    # Log success (handle new nested structure)
    okrs_count = 0
    if 'parte_3_como_chegar_la' in strategic_analysis and 'okrs_propostos' in strategic_analysis['parte_3_como_chegar_la']:
        okrs_count = len(strategic_analysis['parte_3_como_chegar_la']['okrs_propostos'])
    elif 'okrs_propostos' in strategic_analysis:  # Fallback for old structure
        okrs_count = len(strategic_analysis.get('okrs_propostos', []))

    logger.info(f"[STAGE 3] ✅ Generated strategic analysis with {okrs_count} OKRs (4-part structure)")

    # Add usage stats to result
    strategic_analysis["_usage_stats"] = usage_stats
    return strategic_analysis


# ============================================================================
# STAGE 6: EXECUTIVE POLISH (Claude Haiku - CHEAP)
# ============================================================================

async def stage6_executive_polish(
    company: str,
    industry: str,
    strategic_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Stage 6: Polish report for executive readability
    Model: Claude Haiku (cheap but good writing)
    Cost: ~$0.015 per call

    Args:
        company: Company name
        industry: Industry sector (for context, though not heavily used in this stage)
        strategic_analysis: Output from stage 3
    """

    logger.info("[STAGE 6] Polishing report for executive readability...")

    prompt = f"""# EXECUTIVE POLISH TASK

You are an executive communications specialist. Polish this strategic analysis for C-level readability.

## Current Analysis (Generated by Strategy Team)
{json.dumps(strategic_analysis, indent=2, ensure_ascii=False)}

---

# YOUR TASKS

## 1. Enhance Executive Summary
Make it compelling, concise, impactful:
- Start with a powerful opening (current situation in 1 sentence)
- Highlight TOP 3 most important insights
- State TOP 3 priority actions with expected impact
- Keep to 3-4 paragraphs max

## 2. Improve Readability
- Fix any awkward phrasing
- Ensure consistent tone (executive, direct, confident)
- Remove jargon unless industry-standard
- Add clarity where ambiguous

## 3. Enhance Recommendations
For each recommendation:
- Make title punchy and clear
- Ensure "como_implementar" steps are specific and actionable
- Verify investment and ROI numbers are realistic
- Add urgency indicators (quick win vs long-term)

## 4. Improve Scenario Planning
Make scenarios vivid and memorable:
- Add specific trigger dates/events
- Make actions concrete
- Quantify impacts clearly

## 5. Quality Check
- Remove any placeholder text
- Ensure all numbers are realistic (not "R$ 0" or "100%")
- Check that OKRs are truly measurable
- Verify Brazilian Portuguese is natural and professional

## 6. **CRITICAL - Preserve Source Attribution**
- **NEVER remove source markers** from quantitative claims
- Keep all "(fonte: X)", "(baseado em Y)", "(estimativa Z)" markers INTACT
- If text says "R$ 100 milhões (fonte: Website)", DO NOT change it to "R$ 100 milhões"
- Source attribution is MANDATORY for credibility - preserve it at all costs

---

# OUTPUT FORMAT (JSON ONLY)

Return the SAME JSON structure as input, but with polished text.

**DO NOT:**
- Change the structure or remove keys
- Add new sections
- Alter numbers/data significantly
- Make it longer (aim for clarity, not verbosity)
- **REMOVE SOURCE ATTRIBUTION** - Keep all "(fonte: X)" markers

**DO:**
- Improve clarity and flow
- Make language more executive-friendly
- Ensure actionability
- Fix any errors or awkwardness
- **Preserve all source markers and attributions**

Return JSON only. No markdown, no explanations.
"""

    system_prompt = "You are an expert at executive communications. Polish for clarity and impact. Preserve structure and data."

    usage_stats = {}
    try:
        response, usage_stats = await call_llm_with_retry(
            stage_name="STAGE 6",
            model=MODEL_POLISH,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,  # Moderate creativity
            max_tokens=10000
        )
        polished_analysis = json.loads(response)

    except Exception as e:
        logger.warning(f"[STAGE 6] Primary model failed, trying FREE fallback model...")
        logger.warning(f"[STAGE 6] Error: {str(e)}")

        # Fallback: Use free model (Gemini Flash Free)
        stage_config = get_stage_config("polish")
        free_fallback = stage_config.get("free_fallback_model", "google/gemini-2.0-flash-exp:free")

        response, usage_stats = await call_llm_with_retry(
            stage_name="STAGE 6 (FREE FALLBACK)",
            model=free_fallback,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=10000
        )
        polished_analysis = json.loads(response)

    logger.info(f"[STAGE 6] ✅ Report polished for executive readability")

    # Add usage stats to result
    polished_analysis["_usage_stats"] = usage_stats
    return polished_analysis


# ============================================================================
# STAGE 4: COMPETITIVE INTELLIGENCE MATRIX (Gemini Pro)
# ============================================================================

async def stage4_competitive_matrix(
    company: str,
    industry: str,
    extracted_data: Dict[str, Any],
    strategic_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Stage 4: Generate structured competitive intelligence matrix
    Model: Gemini Pro (great at structured data)
    Cost: ~$0.05 per call
    """

    logger.info("[STAGE 4] Generating competitive intelligence matrix...")

    competitors_data = extracted_data.get("competitors", [])
    positioning = strategic_analysis.get("posicionamento_competitivo", {})

    prompt = f"""**TAREFA:** Gere uma matriz de inteligência competitiva COMPLETA para {company} no setor de {industry} no Brasil.

**REQUISITO CRÍTICO: LISTE TODOS OS CONCORRENTES RELEVANTES (mínimo 5-7 empresas, incluindo grandes, médios e emergentes).**

Dados de Concorrentes Disponíveis:
{json.dumps(competitors_data, indent=2, ensure_ascii=False)}

Análise de Posicionamento:
{json.dumps(positioning, indent=2, ensure_ascii=False)}

**INSTRUÇÃO:** Baseie-se nos dados fornecidos, MAS também liste concorrentes conhecidos do mercado brasileiro de {industry} que NÃO estão nos dados (ex: se for pagamentos, inclua Cielo, PagSeguro, GetNet, Mercado Pago, SumUp, Rede, SafraPay, etc).

Para concorrentes NÃO presentes nos dados fornecidos, marque campos como "Estimativa baseada em conhecimento do mercado" ou "N/A - dados não disponíveis".

Retorne JSON em PORTUGUÊS BRASILEIRO:

{{
  "analise_competitiva_detalhada": [
    {{
      "empresa": "{company}",
      "posicionamento": "Mid-market / Premium / Budget",
      "market_share_estimado": "X% (fonte: relatório Y ou 'Estimativa de mercado')",
      "pontos_fortes": ["Ponto forte 1 específico", "Ponto forte 2"],
      "pontos_fracos": ["Ponto fraco 1", "Ponto fraco 2"],
      "preco_medio": "R$ X/mês ou taxa Y% (ou 'N/A')",
      "tecnologia_destaque": "Descrição da tech stack ou inovação",
      "crescimento_anual": "X% ao ano (fonte ou 'Estimativa')",
      "fonte_dados": "Dados fornecidos / Conhecimento de mercado / Estimativa"
    }},
    {{
      "empresa": "Cielo",
      "posicionamento": "...",
      "...": "..."
    }},
    {{
      "empresa": "PagSeguro",
      "...": "..."
    }},
    {{
      "empresa": "GetNet",
      "...": "..."
    }},
    {{
      "empresa": "Mercado Pago",
      "...": "..."
    }},
    {{
      "empresa": "SumUp",
      "...": "..."
    }},
    {{
      "empresa": "Rede",
      "...": "..."
    }},
    "...pelo menos 5-7 concorrentes REAIS do mercado brasileiro"
  ],

  "mapa_posicionamento": {{
    "eixo_x": "Preço (Baixo → Alto)",
    "eixo_y": "Recursos/Funcionalidades (Básico → Avançado)",
    "posicoes": [
      {{"empresa": "{company}", "x": 5, "y": 7}},
      {{"empresa": "Cielo", "x": 8, "y": 8}},
      {{"empresa": "PagSeguro", "x": 5, "y": 6}}
    ],
    "quadrantes": {{
      "preco_baixo_basico": ["Empresas neste quadrante"],
      "preco_baixo_avancado": ["Empresas neste quadrante"],
      "preco_alto_basico": ["Empresas neste quadrante"],
      "preco_alto_avancado": ["Empresas neste quadrante"]
    }}
  }},

  "swot_por_concorrente": [
    {{
      "empresa": "Concorrente A",
      "forcas": ["Força 1", "Força 2"],
      "fraquezas": ["Fraqueza 1"],
      "oportunidades": ["Oportunidade para eles"],
      "ameacas": ["Ameaça que enfrentam"]
    }}
  ],

  "gaps_competitivos": [
    {{
      "gap": "Descrição da lacuna de mercado",
      "oportunidade_para_empresa": "Como {company} pode explorar isso",
      "tamanho_mercado_estimado": "R$ X milhões (fonte ou 'Estimativa')",
      "dificuldade": "Baixa/Média/Alta"
    }}
  ],

  "ameacas_competitivas": [
    {{
      "ameaca": "Descrição da ameaça",
      "origem": "Qual concorrente",
      "prazo": "Quando está chegando",
      "impacto": "Alto/Médio/Baixo",
      "mitigacao": "Como se defender"
    }}
  ]
}}

**REQUISITOS CRÍTICOS:**
1. **MÍNIMO 5-7 CONCORRENTES** - Liste TODOS os players relevantes do mercado brasileiro
2. **FONTE DE DADOS OBRIGATÓRIA** - SEMPRE indique a fonte:
   - "Dados fornecidos (Apify/Perplexity)"
   - "Conhecimento de mercado brasileiro"
   - "Estimativa baseada em análise setorial"
   - "N/A - dados insuficientes"
3. **ATRIBUIÇÃO QUANTITATIVA** - Para números específicos (market share, crescimento, preços):
   - SEMPRE inclua fonte: "15% (fonte: Relatório XYZ)" ou "R$ 50/mês (fonte: Website oficial)"
   - Se estimativa: "~10% (estimativa baseada em market share aproximado)"
   - Se desconhecido: "N/A - dados não disponíveis"
4. **HONESTIDADE** - NUNCA fabrique números sem base. Prefira "N/A" a inventar dados
5. **PORTUGUÊS** - TODO o output em português brasileiro
6. **ESPECÍFICO** - Seja específico e acionável, não genérico
7. **JSON VÁLIDO** - NUNCA use aspas duplas (") dentro de strings. Use aspas simples (') ou parênteses ao invés.
   - ERRADO: "Metodologia "própria" da empresa"
   - CORRETO: "Metodologia (própria) da empresa" ou "Metodologia 'própria' da empresa"
"""

    system_prompt = "Você é um analista de inteligência competitiva brasileira. Crie matrizes estruturadas baseadas em dados. Liste TODOS os concorrentes relevantes do mercado (mínimo 5-7). Output somente JSON em português."

    usage_stats = {}
    try:
        response, usage_stats = await call_llm_with_retry(
            stage_name="STAGE 4",
            model=MODEL_COMPETITIVE,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.4,
            max_tokens=4000
        )
        competitive_intel = json.loads(response)

    except Exception as e:
        logger.warning(f"[STAGE 4] Primary model failed, trying FREE fallback model...")
        logger.warning(f"[STAGE 4] Error: {str(e)}")

        # Fallback: Use free model (Gemini Flash Free)
        stage_config = get_stage_config("competitive")
        free_fallback = stage_config.get("free_fallback_model", "google/gemini-2.0-flash-exp:free")

        response, usage_stats = await call_llm_with_retry(
            stage_name="STAGE 4 (FREE FALLBACK)",
            model=free_fallback,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.4,
            max_tokens=4000
        )
        competitive_intel = json.loads(response)

    num_competitors = len(competitive_intel.get('analise_competitiva_detalhada', []))
    logger.info(f"[STAGE 4] ✅ Generated competitive matrix with {num_competitors} competitors")

    # Add usage stats to result
    competitive_intel["_usage_stats"] = usage_stats
    return competitive_intel


# ============================================================================
# STAGE 5: RISK QUANTIFICATION + PRIORITY SCORING (Claude 3.5 Sonnet)
# ============================================================================

async def stage5_risk_and_priority(
    company: str,
    industry: str,
    strategic_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Stage 5: Quantify risks and score recommendations by priority
    Model: Claude 3.5 Sonnet (best reasoning)
    Cost: ~$0.08 per call

    Args:
        company: Company name
        industry: Industry sector (for context, though not heavily used in this stage)
        strategic_analysis: Output from stage 3
    """

    logger.info("[STAGE 5] Quantifying risks and scoring recommendations...")

    recommendations = strategic_analysis.get("recomendacoes_prioritarias", [])
    swot = strategic_analysis.get("analise_swot", {})
    scenarios = strategic_analysis.get("planejamento_cenarios", {})

    prompt = f"""**ATENÇÃO CRÍTICA: TODO O OUTPUT DEVE ESTAR EM PORTUGUÊS BRASILEIRO (pt-BR) ABSOLUTAMENTE PERFEITO E PROFISSIONAL.**

**NÃO USE INGLÊS EM HIPÓTESE ALGUMA. RESPOSTAS EM INGLÊS OU COM TERMOS EM INGLÊS SERÃO REJEITADAS.**

---

Para {company}, quantifique riscos e pontue recomendações por prioridade, com base nos dados fornecidos.

Recomendações Estratégicas:
{json.dumps(recommendations, indent=2, ensure_ascii=False)}

Análise SWOT:
{json.dumps(swot, indent=2, ensure_ascii=False)}

Cenários de Planejamento:
{json.dumps(scenarios, indent=2, ensure_ascii=False)}

---

Retorne JSON SOMENTE EM PORTUGUÊS BRASILEIRO:

{{
  "risk_analysis": [
    {{
      "risk": "Descrição do risco em português claro e específico",
      "category": "Competitivo/Mercado/Operacional/Financeiro/Tecnológico",
      "probability": 0.7,
      "impact": 8,
      "risk_score": 5.6,
      "severity": "ALTO/MÉDIO/BAIXO",
      "timeframe": "3-6 meses",
      "indicators": ["Sinal de alerta precoce 1", "Sinal de alerta precoce 2"],
      "mitigation_cost": "R$ 50 mil",
      "mitigation_strategies": [
        "Ação específica 1 com prazo em português",
        "Ação específica 2 em português",
        "Plano de contingência em português"
      ]
    }}
  ],

  "recommendation_scoring": [
    {{
      "recommendation": "Título da recomendação (do input)",
      "effort_score": 3,
      "impact_score": 9,
      "efficiency_ratio": 3.0,
      "priority_tier": "🔥 MUITO ALTO / ⚡ ALTO / ✓ MÉDIO / ○ BAIXO",
      "roi_calculation": {{
        "investment": "R$ 50 mil",
        "expected_return_12m": "R$ 360 mil",
        "roi_percentage": 620,
        "payback_period_days": 45,
        "risk_adjusted_return": {{
          "best_case": "R$ 900 mil (25% probabilidade)",
          "expected_case": "R$ 360 mil (50% probabilidade)",
          "worst_case": "R$ 120 mil (25% probabilidade)"
        }}
      }},
      "dependencies": ["O que deve acontecer primeiro (em português)"],
      "blockers": ["Obstáculos potenciais (em português)"]
    }}
  ],

  "priority_matrix": {{
    "quick_wins": [
      {{
        "action": "Ação de baixo esforço e alto impacto em português",
        "effort": 2,
        "impact": 8,
        "timeline": "0-30 dias"
      }}
    ],
    "strategic_investments": [
      {{
        "action": "Ação de alto esforço e alto impacto em português",
        "effort": 8,
        "impact": 9,
        "timeline": "3-6 meses"
      }}
    ],
    "fill_ins": [
      {{
        "action": "Ação de baixo esforço e impacto médio em português",
        "effort": 2,
        "impact": 5,
        "timeline": "Conforme recursos permitirem"
      }}
    ],
    "avoid": [
      {{
        "action": "Ação de alto esforço e baixo impacto - evitar (em português)",
        "effort": 7,
        "impact": 3,
        "reason": "Por que evitar (em português)"
      }}
    ]
  }},

  "critical_path": [
    {{
      "month": 1,
      "milestone": "Nome do marco (em português)",
      "actions": ["Ação 1 em português", "Ação 2 em português"],
      "success_criteria": "Como medir sucesso (em português)",
      "risks": ["Risco durante este mês (em português)"]
    }}
  ]
}}

**REGRAS OBRIGATÓRIAS:**
1. TODO o texto deve estar em português brasileiro profissional
2. NÃO traduza literalmente termos técnicos - use equivalentes naturais em português
3. NÃO inclua UMA ÚNICA palavra em inglês
4. Seja específico, quantitativo e acionável
5. **ATRIBUIÇÃO DE FONTE OBRIGATÓRIA:**
   - Para números específicos (custos, retornos, probabilidades): SEMPRE cite a base
   - Formato: "R$ 50 mil (baseado em análise SWOT)" ou "45 dias (estimativa baseada em projetos similares)"
   - Se estimativa: Seja explícito - "Estimativa baseada em análise de cenários"
   - Se desconhecido: Use "N/A - requer dados adicionais" ao invés de inventar
   - NUNCA fabrique números específicos sem base clara nos dados fornecidos

**ESCALA DE PONTUAÇÃO:**
- Probabilidade: 0.0-1.0 (0% a 100%)
- Impacto: 1-10 (1=mínimo, 10=catastrófico)
- Esforço: 1-10 (1=trivial, 10=massivo)
- Score de Risco = Probabilidade × Impacto

**VALIDAÇÃO FINAL:** No final da sua resposta JSON, adicione mentalmente: "Idioma conferido: 100% português brasileiro"

**SE QUALQUER PARTE ESTIVER EM INGLÊS, A RESPOSTA É INVÁLIDA.**
"""

    system_prompt = """Você é um analista estratégico de riscos brasileiro. Sua especialidade é quantificar riscos, calcular ROI e priorizar ações estratégicas.

REGRA ABSOLUTA: TODO output deve estar em português brasileiro (pt-BR) profissional e correto. NUNCA use inglês. Output somente JSON válido.

Seja específico, quantitativo e acionável. Use português natural e profissional."""

    usage_stats = {}
    try:
        response, usage_stats = await call_llm_with_retry(
            stage_name="STAGE 5",
            model=MODEL_RISK_SCORING,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=6000
        )
        risk_priority = json.loads(response)

    except Exception as e:
        logger.warning(f"[STAGE 5] Primary model failed, trying FREE fallback model...")
        logger.warning(f"[STAGE 5] Error: {str(e)}")

        # Fallback: Use free model (Gemini Flash Free)
        stage_config = get_stage_config("risk_scoring")
        free_fallback = stage_config.get("free_fallback_model", "google/gemini-2.0-flash-exp:free")

        response, usage_stats = await call_llm_with_retry(
            stage_name="STAGE 5 (FREE FALLBACK)",
            model=free_fallback,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=0.5,
            max_tokens=6000
        )
        risk_priority = json.loads(response)

    logger.info(f"[STAGE 5] ✅ Scored {len(risk_priority.get('risk_analysis', []))} risks, "
               f"{len(risk_priority.get('recommendation_scoring', []))} recommendations")

    # Add usage stats to result
    risk_priority["_usage_stats"] = usage_stats
    return risk_priority


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

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


# Test function
async def test_multistage():
    """Test the multi-stage pipeline"""
    import asyncio

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
