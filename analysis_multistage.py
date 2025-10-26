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
                    if content.startswith("```json"):
                        content = content[7:]
                    if content.startswith("```"):
                        content = content[3:]
                    if content.endswith("```"):
                        content = content[:-3]
                    content = content.strip()

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

    response = await call_llm(
        model=MODEL_EXTRACTION,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.3,  # Lower temp for factual extraction
        max_tokens=4000
    )

    try:
        extracted_data = json.loads(response)
        logger.info(f"[STAGE 1] ✅ Extracted {len(extracted_data.get('competitors', []))} competitors, "
                   f"{len(extracted_data.get('industry_trends', []))} trends, "
                   f"{len(extracted_data.get('data_gaps', []))} gaps identified")
        return extracted_data
    except json.JSONDecodeError as e:
        logger.error(f"[STAGE 1] JSON parse error: {e}")
        logger.error(f"[STAGE 1] Response preview: {response[:500]}")
        raise Exception(f"Stage 1 failed to parse JSON: {e}")


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

    response = await call_llm(
        model=MODEL_STRATEGY,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.8,  # Higher for creative strategic thinking
        max_tokens=8000
    )

    try:
        strategic_analysis = json.loads(response)
        logger.info(f"[STAGE 3] ✅ Generated strategic analysis with {len(strategic_analysis.get('okrs_propostos', []))} OKRs")
        return strategic_analysis
    except json.JSONDecodeError as e:
        logger.error(f"[STAGE 3] JSON parse error: {e}")
        logger.error(f"[STAGE 3] Response preview: {response[:500]}")
        raise Exception(f"Stage 3 failed to parse JSON: {e}")


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

    response = await call_llm(
        model=MODEL_POLISH,
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.5,  # Moderate creativity
        max_tokens=10000
    )

    try:
        polished_analysis = json.loads(response)
        logger.info(f"[STAGE 6] ✅ Report polished for executive readability")
        return polished_analysis
    except json.JSONDecodeError as e:
        logger.error(f"[STAGE 6] JSON parse error: {e}")
        logger.error(f"[STAGE 6] Response preview: {response[:500]}")
        raise Exception(f"Stage 6 failed to parse JSON: {e}")


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
) -> Dict[str, Any]:
    """
    Main orchestrator for multi-stage analysis pipeline

    Returns: Complete strategic analysis with metadata
    """

    start_time = datetime.now()
    logger.info(f"[MULTISTAGE] Starting analysis for {company} in {industry}")

    try:
        # Stage 1: Extract structured data (CHEAP - Gemini Flash)
        extracted_data = await stage1_extract_data(
            company, industry, website, challenge, apify_data, perplexity_data
        )

        # Stage 3: Strategic frameworks (EXPENSIVE - GPT-4o)
        strategic_analysis = await stage3_strategic_analysis(
            company, industry, challenge, extracted_data
        )

        # Stage 6: Executive polish (CHEAP - Claude Haiku)
        final_analysis = await stage6_executive_polish(
            company, strategic_analysis
        )

        # Add metadata
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        final_analysis["_metadata"] = {
            "generated_at": end_time.isoformat(),
            "processing_time_seconds": processing_time,
            "pipeline": "multi-stage-v1",
            "stages_completed": ["extraction", "strategic_analysis", "executive_polish"],
            "models_used": {
                "stage1_extraction": MODEL_EXTRACTION,
                "stage3_strategy": MODEL_STRATEGY,
                "stage6_polish": MODEL_POLISH
            },
            "framework_version": "10XMentorAI v2.1 Multistage",
            "quality_tier": "Professional",
            "used_perplexity": perplexity_data is not None and perplexity_data.get("research_completed", False),
            "data_gaps_identified": len(extracted_data.get("data_gaps", []))
        }

        logger.info(f"[MULTISTAGE] ✅ Analysis complete in {processing_time:.1f}s")
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
