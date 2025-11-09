"""
Stage 1: Data Extraction & Structuring
Model: Gemini Flash (ultra-cheap, good at extraction)
Cost: ~$0.002 per call
"""

import json
import logging
from typing import Dict, Any, Optional

from app.services.analysis.llm_client import call_llm_with_retry
from app.core.security.prompt_sanitizer import sanitize_dict_recursive
from app.core.model_config import get_model_for_stage
from app.core.constants import STAGE1_MAX_TOKENS, TEMPERATURE_FACTUAL

logger = logging.getLogger(__name__)

MODEL_EXTRACTION = get_model_for_stage("extraction")


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
        temperature=TEMPERATURE_FACTUAL,  # Lower temp for factual extraction
        max_tokens=STAGE1_MAX_TOKENS
    )

    extracted_data = json.loads(response)
    logger.info(f"[STAGE 1] ✅ Extracted {len(extracted_data.get('competitors', []))} competitors, "
               f"{len(extracted_data.get('industry_trends', []))} trends, "
               f"{len(extracted_data.get('data_gaps', []))} gaps identified")

    # Add usage stats to result
    extracted_data["_usage_stats"] = usage_stats
    return extracted_data
