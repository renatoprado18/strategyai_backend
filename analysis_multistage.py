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

logger = logging.getLogger(__name__)
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Model selection for each stage
MODEL_EXTRACTION = "google/gemini-2.5-flash-preview-09-2025"  # CHEAP: $0.075/M in, $0.30/M out
MODEL_GAP_ANALYSIS = "google/gemini-2.5-flash-preview-09-2025"  # CHEAP
MODEL_STRATEGY = "openai/gpt-4o"  # EXPENSIVE: $2.50/M in, $10/M out
MODEL_COMPETITIVE = "google/gemini-2.5-pro-preview"  # MID: Great at structured data
MODEL_RISK_SCORING = "anthropic/claude-3.5-sonnet"  # EXPENSIVE: Best reasoning
MODEL_POLISH = "anthropic/claude-haiku-4.5"  # CHEAP: $0.25/M in, $1.25/M out

TIMEOUT = 120.0
MAX_RETRIES = 3  # Maximum retry attempts per stage


async def call_llm_with_retry(
    stage_name: str,
    model: str,
    prompt: str,
    system_prompt: str = "",
    temperature: float = 0.7,
    max_tokens: int = 4000,
    max_retries: int = MAX_RETRIES
) -> str:
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

    Returns:
        Valid JSON string
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

            response = await call_llm(
                model=model,
                prompt=strict_prompt,
                system_prompt=system_prompt or "Output JSON ONLY. No markdown. No explanations.",
                temperature=current_temp,
                max_tokens=max_tokens
            )

            # Validate JSON
            json.loads(response)  # Will raise JSONDecodeError if invalid

            logger.info(f"[{stage_name}] ✅ Valid JSON received (attempt {attempt + 1})")
            return response

        except json.JSONDecodeError as e:
            last_error = e
            logger.error(f"[{stage_name}] JSON parse error on attempt {attempt + 1}: {e}")
            logger.error(f"[{stage_name}] Response preview: {response[:1000] if 'response' in locals() else 'No response'}")

            if attempt == max_retries - 1:
                # Last attempt - log full response
                logger.error(f"[{stage_name}] All {max_retries} attempts failed!")
                logger.error(f"[{stage_name}] Full response: {response if 'response' in locals() else 'No response'}")
                raise Exception(f"{stage_name} failed after {max_retries} attempts: {e}")

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
) -> str:
    """Generic LLM caller for any OpenRouter model"""

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

                logger.info(f"[LLM] {model} responded ({len(content)} chars)")
                return content
            else:
                raise Exception(f"Unexpected API response: {data}")

    except httpx.TimeoutException:
        raise Exception(f"LLM call to {model} timed out after {TIMEOUT}s")
    except httpx.HTTPStatusError as e:
        raise Exception(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"LLM call failed: {str(e)}")


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

    # Build context
    data_context = f"""# RAW DATA SOURCES

## Company Information
- Name: {company}
- Industry: {industry}
- Website: {website or 'N/A'}
- Challenge: {challenge or 'N/A'}

## Apify Data (Web Scraping)
{json.dumps(apify_data, indent=2, ensure_ascii=False) if apify_data else 'No Apify data'}

## Perplexity Data (Real-Time Research)
{json.dumps(perplexity_data, indent=2, ensure_ascii=False) if perplexity_data else 'No Perplexity data'}
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

    response = await call_llm_with_retry(
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
            "data_gaps_filled": 0
        }

    # Generate targeted follow-up queries
    prompt = f"""Based on these data gaps for {company} in {industry}, generate 2-3 targeted research queries:

Data Gaps Identified:
{json.dumps(data_gaps, indent=2, ensure_ascii=False)}

Current Data:
{json.dumps(extracted_data, indent=2, ensure_ascii=False)[:2000]}

Generate specific, actionable research queries that would fill the most important gaps.

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

    response = await call_llm_with_retry(
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
                "data_gaps_filled": 0
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
            "priority_gaps": gap_analysis.get("priority_gaps", [])
        }

    except json.JSONDecodeError as e:
        logger.error(f"[STAGE 2] JSON parse error: {e}")
        return {
            "follow_up_completed": False,
            "follow_up_research": {},
            "data_gaps_filled": 0
        }


# ============================================================================
# STAGE 3: STRATEGIC FRAMEWORKS (GPT-4o - EXPENSIVE)
# ============================================================================

async def stage3_strategic_analysis(
    company: str,
    industry: str,
    challenge: Optional[str],
    extracted_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Stage 3: Apply strategic frameworks to extracted data
    Model: GPT-4o (expensive but best for frameworks)
    Cost: ~$0.073 per call
    """

    logger.info("[STAGE 3] Applying strategic frameworks...")

    prompt = f"""# STRATEGIC ANALYSIS TASK

You are a senior McKinsey consultant. Apply rigorous strategic frameworks to the data below.

## Company Context
- **Company:** {company}
- **Industry:** {industry}
- **Challenge:** {challenge or 'General strategic analysis'}

## Structured Data (Pre-Extracted)
{json.dumps(extracted_data, indent=2, ensure_ascii=False)}

---

# FRAMEWORKS TO APPLY

## 1. PESTEL Analysis
Analyze macro-environmental factors specific to {industry} in Brazil:
- **Político:** Regulations, government policies affecting {industry}
- **Econômico:** Economic trends (GDP, inflation, interest rates) impact
- **Social:** Demographic shifts, consumer behavior changes
- **Tecnológico:** Tech disruptions, digital transformation in {industry}
- **Ambiental:** ESG factors, sustainability trends
- **Legal:** LGPD, industry-specific laws, compliance requirements

## 2. Porter's Five Forces
Assess competitive intensity in {industry}:
- Threat of new entrants (barriers to entry)
- Bargaining power of suppliers
- Bargaining power of buyers
- Threat of substitutes
- Rivalry among existing competitors

For each force: rate as Low/Medium/High and explain WHY with data.

## 3. SWOT Analysis
Based on extracted data, identify:
- **Strengths:** 4-6 specific strengths with evidence
- **Weaknesses:** 4-6 specific weaknesses with impact assessment
- **Opportunities:** 4-6 opportunities with market size / growth data
- **Threats:** 4-6 threats with probability and mitigation strategies

## 4. Blue Ocean Strategy
Identify uncontested market spaces:
- **Eliminate:** Factors industry accepts that should be removed
- **Reduce:** Factors to reduce below industry standard
- **Elevate:** Factors to raise above industry standard
- **Create:** New factors industry never offered

## 5. Competitive Positioning
Detailed analysis of each competitor:
- Positioning (premium, mid-market, budget, niche)
- Key differentiators
- Market share and growth trajectory
- Pricing strategy
- Strengths vs {company}
- Vulnerabilities {company} can exploit

Define {company}'s unique positioning and differentiation.

## 6. TAM/SAM/SOM with Justification
- **TAM:** Total addressable market in R$ (with source/calculation)
- **SAM:** Serviceable available market (realistic segment)
- **SOM:** Serviceable obtainable market (18-month target)
- **Justification:** Explain assumptions and math

## 7. OKRs (3 quarters)
For Q1, Q2, Q3 2025, create:
- **Objective:** Ambitious, qualitative goal
- **Key Results:** 3-5 MEASURABLE outcomes with specific numbers
- **KPIs:** Metrics to track (with targets)
- **Owner:** Suggested role (CEO, CMO, CTO, etc.)
- **Investment:** Estimated cost in R$

## 8. Balanced Scorecard
Organize objectives across 4 perspectives:
- **Financial:** Revenue, margins, ROI targets
- **Customer:** NPS, retention, acquisition goals
- **Internal Processes:** Efficiency, quality, speed improvements
- **Learning & Growth:** Training, culture, technology initiatives

## 9. Scenario Planning (12-18 months)
Create 3 scenarios:
- **Optimista (20-25% probability):** Best case - What triggers it? Revenue impact? Actions?
- **Realista (50-60% probability):** Most likely - What happens? How to execute?
- **Pessimista (15-20% probability):** Worst case - What threatens? How to survive?

---

# OUTPUT FORMAT (JSON ONLY)

```json
{{
  "sumario_executivo": "3-4 paragraphs: (1) Current situation, (2) Key findings, (3) Priority recommendations with expected impact",

  "analise_pestel": {{
    "politico": "2-3 paragraphs with specific examples",
    "economico": "2-3 paragraphs with data",
    "social": "2-3 paragraphs with trends",
    "tecnologico": "2-3 paragraphs with innovations",
    "ambiental": "2 paragraphs with ESG factors",
    "legal": "2 paragraphs with regulations"
  }},

  "cinco_forcas_porter": {{
    "ameaca_novos_entrantes": "Analysis + rating (Low/Medium/High) + justification",
    "poder_fornecedores": "Analysis + rating + justification",
    "poder_compradores": "Analysis + rating + justification",
    "ameaca_substitutos": "Analysis + rating + justification",
    "rivalidade_concorrentes": "Analysis + rating + justification"
  }},

  "analise_swot": {{
    "forcas": ["Strength 1 with evidence", "Strength 2...", "...4-6 total"],
    "fraquezas": ["Weakness 1 with impact", "...4-6 total"],
    "oportunidades": ["Opportunity 1 with data", "...4-6 total"],
    "ameacas": ["Threat 1 with mitigation", "...4-6 total"]
  }},

  "estrategia_oceano_azul": {{
    "eliminar": ["Factor 1", "Factor 2", "..."],
    "reduzir": ["Factor 1", "..."],
    "elevar": ["Factor 1", "..."],
    "criar": ["Factor 1", "..."]
  }},

  "tam_sam_som": {{
    "tam_total_market": "R$ X billion - description",
    "sam_available_market": "R$ Y million - description",
    "som_obtainable_market": "R$ Z million - description",
    "justificativa": "Explain assumptions and calculations"
  }},

  "posicionamento_competitivo": {{
    "principais_concorrentes": [
      {{
        "nome": "Competitor A",
        "posicionamento": "Premium / Mid-market / Budget / Niche",
        "vantagens": "Specific advantages with data",
        "fraquezas": "Exploitable weaknesses",
        "share_estimado": "% or N/A"
      }}
    ],
    "diferencial_unico": "{company}'s unique value proposition",
    "matriz_posicionamento": "Where {company} sits vs competitors"
  }},

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
      "investimento_estimado": "R$ X mil"
    }},
    {{"trimestre": "Q2 2025", "...": "..."}},
    {{"trimestre": "Q3 2025", "...": "..."}}
  ],

  "balanced_scorecard": {{
    "perspectiva_financeira": ["Goal 1 with metric", "Goal 2", "..."],
    "perspectiva_cliente": ["Goal 1", "..."],
    "perspectiva_processos": ["Goal 1", "..."],
    "perspectiva_aprendizado": ["Goal 1", "..."]
  }},

  "planejamento_cenarios": {{
    "cenario_otimista": {{
      "descricao": "What happens in best case",
      "probabilidade": "20-25%",
      "impacto_receita": "Revenue projection",
      "gatilhos": ["Trigger 1", "Trigger 2"],
      "acoes_requeridas": ["Action 1", "Action 2"]
    }},
    "cenario_realista": {{"...": "..."}},
    "cenario_pessimista": {{"...": "..."}}
  }},

  "recomendacoes_prioritarias": [
    {{
      "prioridade": 1,
      "titulo": "Concise recommendation title",
      "recomendacao": "WHAT to do - detailed description",
      "justificativa": "WHY - data-driven rationale",
      "como_implementar": ["Step 1", "Step 2", "Step 3"],
      "prazo": "Timeline",
      "investimento_estimado": "R$ X",
      "retorno_esperado": "R$ Y in Z months",
      "metricas_sucesso": ["Metric 1", "Metric 2"],
      "riscos_mitigacao": ["Risk 1 + mitigation", "Risk 2 + mitigation"]
    }},
    {{"prioridade": 2, "...": "..."}},
    {{"prioridade": 3, "...": "..."}}
  ],

  "roadmap_implementacao": {{
    "primeiros_30_dias": ["Quick win 1", "Quick win 2", "..."],
    "60_90_dias": ["Initiative 1", "..."],
    "6_meses": ["Strategic initiative 1", "..."]
  }}
}}
```

**REQUIREMENTS:**
- Use specific numbers (not "many", "some", "growing")
- Base analysis on extracted data facts
- Be actionable (not academic)
- Brazilian Portuguese
- JSON only, no markdown
"""

    system_prompt = "You are a world-class strategy consultant. Apply frameworks rigorously. Be specific, data-driven, actionable."

    response = await call_llm_with_retry(
        stage_name="STAGE 3",
        model=MODEL_STRATEGY,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.8,  # Higher for creative strategic thinking
        max_tokens=8000
    )

    strategic_analysis = json.loads(response)
    logger.info(f"[STAGE 3] ✅ Generated strategic analysis with {len(strategic_analysis.get('okrs_propostos', []))} OKRs")
    return strategic_analysis


# ============================================================================
# STAGE 6: EXECUTIVE POLISH (Claude Haiku - CHEAP)
# ============================================================================

async def stage6_executive_polish(
    company: str,
    strategic_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Stage 6: Polish report for executive readability
    Model: Claude Haiku (cheap but good writing)
    Cost: ~$0.015 per call
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

---

# OUTPUT FORMAT (JSON ONLY)

Return the SAME JSON structure as input, but with polished text.

**DO NOT:**
- Change the structure or remove keys
- Add new sections
- Alter numbers/data significantly
- Make it longer (aim for clarity, not verbosity)

**DO:**
- Improve clarity and flow
- Make language more executive-friendly
- Ensure actionability
- Fix any errors or awkwardness

Return JSON only. No markdown, no explanations.
"""

    system_prompt = "You are an expert at executive communications. Polish for clarity and impact. Preserve structure and data."

    response = await call_llm_with_retry(
        stage_name="STAGE 6",
        model=MODEL_POLISH,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.5,  # Moderate creativity
        max_tokens=10000
    )

    polished_analysis = json.loads(response)
    logger.info(f"[STAGE 6] ✅ Report polished for executive readability")
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

    prompt = f"""Generate a structured competitive intelligence matrix for {company} in {industry}.

Competitor Data:
{json.dumps(competitors_data, indent=2, ensure_ascii=False)}

Positioning Analysis:
{json.dumps(positioning, indent=2, ensure_ascii=False)}

Create a comprehensive competitive matrix with:

Return JSON:

{{
  "competitive_matrix": {{
    "competitors": ["{company}", "Competitor A", "Competitor B", "Competitor C"],
    "features": ["Pricing", "Tech Stack", "Market Share", "Strengths", "Weaknesses", "Growth Rate", "Funding"],
    "matrix": [
      ["{company}", "Value", "Value", "Value", "..."],
      ["Competitor A", "Value", "Value", "Value", "..."],
      ["Competitor B", "..."]
    ]
  }},

  "positioning_map": {{
    "x_axis": "Price (Low to High)",
    "y_axis": "Features (Basic to Advanced)",
    "positions": [
      {{"company": "{company}", "x": 5, "y": 7}},
      {{"company": "Competitor A", "x": 7, "y": 8}},
      {{"company": "Competitor B", "x": 3, "y": 5}}
    ],
    "quadrants": {{
      "low_price_basic": ["Companies here"],
      "low_price_advanced": ["Companies here"],
      "high_price_basic": ["Companies here"],
      "high_price_advanced": ["Companies here"]
    }}
  }},

  "swot_per_competitor": [
    {{
      "company": "Competitor A",
      "strengths": ["Strength 1", "Strength 2"],
      "weaknesses": ["Weakness 1"],
      "opportunities": ["Opportunity for them"],
      "threats": ["Threat they face"]
    }}
  ],

  "competitive_gaps": [
    {{
      "gap": "Market gap description",
      "opportunity_for_company": "How {company} can exploit this",
      "estimated_market_size": "R$ X million",
      "difficulty": "Low/Medium/High"
    }}
  ],

  "competitive_threats": [
    {{
      "threat": "Threat description",
      "source": "Which competitor",
      "timeline": "When it's coming",
      "impact": "High/Medium/Low",
      "mitigation": "How to defend"
    }}
  ]
}}

Use real data from extracted data. If data missing, use "N/A" or "Estimated: X".
Be specific and actionable.
"""

    system_prompt = "You are a competitive intelligence analyst. Create structured, data-driven competitive matrices. Output JSON only."

    response = await call_llm_with_retry(
        stage_name="STAGE 4",
        model=MODEL_COMPETITIVE,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.4,
        max_tokens=4000
    )

    competitive_intel = json.loads(response)
    logger.info(f"[STAGE 4] ✅ Generated competitive matrix with {len(competitive_intel.get('competitive_matrix', {}).get('competitors', []))} competitors")
    return competitive_intel


# ============================================================================
# STAGE 5: RISK QUANTIFICATION + PRIORITY SCORING (Claude 3.5 Sonnet)
# ============================================================================

async def stage5_risk_and_priority(
    company: str,
    strategic_analysis: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Stage 5: Quantify risks and score recommendations by priority
    Model: Claude 3.5 Sonnet (best reasoning)
    Cost: ~$0.08 per call
    """

    logger.info("[STAGE 5] Quantifying risks and scoring recommendations...")

    recommendations = strategic_analysis.get("recomendacoes_prioritarias", [])
    swot = strategic_analysis.get("analise_swot", {})
    scenarios = strategic_analysis.get("planejamento_cenarios", {})

    prompt = f"""For {company}, quantify risks and score recommendations by priority.

Recommendations:
{json.dumps(recommendations, indent=2, ensure_ascii=False)}

SWOT Analysis:
{json.dumps(swot, indent=2, ensure_ascii=False)}

Scenarios:
{json.dumps(scenarios, indent=2, ensure_ascii=False)}

Return JSON:

{{
  "risk_analysis": [
    {{
      "risk": "Risk description",
      "category": "Competitive/Market/Operational/Financial/Technology",
      "probability": 0.7,
      "impact": 8,
      "risk_score": 5.6,
      "severity": "HIGH/MEDIUM/LOW",
      "timeframe": "3-6 months",
      "indicators": ["Early warning sign 1", "Early warning sign 2"],
      "mitigation_cost": "R$ 50k",
      "mitigation_strategies": [
        "Specific action 1 with timeline",
        "Specific action 2",
        "Contingency plan"
      ]
    }}
  ],

  "recommendation_scoring": [
    {{
      "recommendation": "Recommendation title from input",
      "effort_score": 3,
      "impact_score": 9,
      "efficiency_ratio": 3.0,
      "priority_tier": "🔥 VERY HIGH / ⚡ HIGH / ✓ MEDIUM / ○ LOW",
      "roi_calculation": {{
        "investment": "R$ 50k",
        "expected_return_12m": "R$ 360k",
        "roi_percentage": 620,
        "payback_period_days": 45,
        "risk_adjusted_return": {{
          "best_case": "R$ 900k (25% probability)",
          "expected_case": "R$ 360k (50% probability)",
          "worst_case": "R$ 120k (25% probability)"
        }}
      }},
      "dependencies": ["What must happen first"],
      "blockers": ["Potential obstacles"]
    }}
  ],

  "priority_matrix": {{
    "quick_wins": [
      {{
        "action": "Low effort, high impact action",
        "effort": 2,
        "impact": 8,
        "timeline": "0-30 days"
      }}
    ],
    "strategic_investments": [
      {{
        "action": "High effort, high impact action",
        "effort": 8,
        "impact": 9,
        "timeline": "3-6 months"
      }}
    ],
    "fill_ins": [
      {{
        "action": "Low effort, medium impact",
        "effort": 2,
        "impact": 5,
        "timeline": "As resources allow"
      }}
    ],
    "avoid": [
      {{
        "action": "High effort, low impact - avoid",
        "effort": 7,
        "impact": 3,
        "reason": "Why to avoid"
      }}
    ]
  }},

  "critical_path": [
    {{
      "month": 1,
      "milestone": "Milestone name",
      "actions": ["Action 1", "Action 2"],
      "success_criteria": "How to measure success",
      "risks": ["Risk during this month"]
    }}
  ]
}}

Scoring scale:
- Probability: 0.0-1.0 (0% to 100%)
- Impact: 1-10 (1=minimal, 10=catastrophic)
- Effort: 1-10 (1=trivial, 10=massive)
- Risk Score = Probability × Impact

Be specific, quantitative, and actionable.
"""

    system_prompt = "You are a strategic risk analyst. Quantify risks, calculate ROI, prioritize ruthlessly. Output JSON only."

    response = await call_llm_with_retry(
        stage_name="STAGE 5",
        model=MODEL_RISK_SCORING,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.5,
        max_tokens=6000
    )

    risk_priority = json.loads(response)
    logger.info(f"[STAGE 5] ✅ Scored {len(risk_priority.get('risk_analysis', []))} risks, "
               f"{len(risk_priority.get('recommendation_scoring', []))} recommendations")
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
    perplexity_service = None
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

    Returns: Complete strategic analysis with metadata
    """

    start_time = datetime.now()
    logger.info(f"[MULTISTAGE] Starting {'FULL' if run_all_stages else 'CORE'} analysis for {company} in {industry}")

    try:
        # ===== STAGE 1: Extract structured data (CHEAP - Gemini Flash) =====
        extracted_data = await stage1_extract_data(
            company, industry, website, challenge, apify_data, perplexity_data
        )

        stages_completed = ["extraction"]
        models_used = {"stage1_extraction": MODEL_EXTRACTION}
        follow_up_data = {}

        # ===== STAGE 2: Gap analysis + follow-up (OPTIONAL) =====
        if run_all_stages and perplexity_service:
            try:
                follow_up_data = await stage2_gap_analysis_and_followup(
                    company, industry, extracted_data, perplexity_service
                )
                stages_completed.append("gap_analysis_followup")
                models_used["stage2_gap_analysis"] = MODEL_GAP_ANALYSIS
            except Exception as e:
                logger.warning(f"[MULTISTAGE] Stage 2 failed (non-critical): {str(e)}")
                follow_up_data = {"follow_up_completed": False}

        # ===== STAGE 3: Strategic frameworks (EXPENSIVE - GPT-4o) =====
        strategic_analysis = await stage3_strategic_analysis(
            company, industry, challenge, extracted_data
        )
        stages_completed.append("strategic_analysis")
        models_used["stage3_strategy"] = MODEL_STRATEGY

        competitive_intel = {}
        risk_priority = {}

        # ===== STAGE 4: Competitive matrix (OPTIONAL) =====
        if run_all_stages:
            try:
                competitive_intel = await stage4_competitive_matrix(
                    company, industry, extracted_data, strategic_analysis
                )
                stages_completed.append("competitive_matrix")
                models_used["stage4_competitive"] = MODEL_COMPETITIVE
            except Exception as e:
                logger.warning(f"[MULTISTAGE] Stage 4 failed (non-critical): {str(e)}")
                competitive_intel = {}

        # ===== STAGE 5: Risk scoring + priority (OPTIONAL) =====
        if run_all_stages:
            try:
                risk_priority = await stage5_risk_and_priority(
                    company, strategic_analysis
                )
                stages_completed.append("risk_priority_scoring")
                models_used["stage5_risk"] = MODEL_RISK_SCORING
            except Exception as e:
                logger.warning(f"[MULTISTAGE] Stage 5 failed (non-critical): {str(e)}")
                risk_priority = {}

        # ===== STAGE 6: Executive polish (CHEAP - Claude Haiku) =====
        try:
            final_analysis = await stage6_executive_polish(
                company, strategic_analysis
            )
            stages_completed.append("executive_polish")
            models_used["stage6_polish"] = MODEL_POLISH
        except Exception as e:
            logger.warning(f"[MULTISTAGE] Stage 6 failed (non-critical): {str(e)}")
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
            "total_cost_estimate_usd": 0.85 if run_all_stages else 0.09
        }

        logger.info(f"[MULTISTAGE] ✅ {len(stages_completed)}-stage analysis complete in {processing_time:.1f}s")
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
