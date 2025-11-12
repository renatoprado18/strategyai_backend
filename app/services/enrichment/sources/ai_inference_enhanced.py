"""
Enhanced AI Inference Source

Structured AI extraction for Layer 3 enrichment.
Uses GPT-4o-mini with structured prompts to extract:
- Industry classification
- Digital maturity assessment
- Communication tone analysis
- Key differentiators
- Strategic opportunities

Layer: 3 (AI, 6-10s)
Cost: ~$0.001-0.01 per call
"""

import logging
import time
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from app.services.ai.openrouter_client import get_openrouter_client
from .base import EnrichmentSource, SourceResult

logger = logging.getLogger(__name__)


class StrategicInsights(BaseModel):
    """Structured AI insights output"""
    industry: Optional[str] = None
    target_audience: Optional[str] = None
    company_size: Optional[str] = None
    digital_maturity: Optional[str] = None
    communication_tone: Optional[str] = None
    key_differentiators: List[str] = []
    strategic_focus: Optional[str] = None
    opportunities: List[str] = []


class EnhancedAIInferenceSource(EnrichmentSource):
    """
    Enhanced AI inference with structured extraction.

    Uses GPT-4o-mini to analyze website content and infer:
    - Industry and market positioning
    - Target audience (B2B/B2C)
    - Company size category
    - Digital maturity level
    - Communication tone
    - Key differentiators (competitive advantages)
    - Strategic focus areas
    - Growth opportunities

    Performance: 2-4 seconds
    Cost: ~$0.001-0.01 per call (GPT-4o-mini)

    Confidence: 70-80% (AI-inferred)
    """

    def __init__(self):
        """Initialize AI inference source"""
        super().__init__(name="ai_inference_enhanced", cost_per_call=0.005)

    async def enrich(
        self,
        domain: str,
        website_url: Optional[str] = None,
        scraped_metadata: Optional[Dict[str, Any]] = None,
        layer1_data: Optional[Dict[str, Any]] = None,
        layer2_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> SourceResult:
        """
        Extract strategic insights using AI.

        Args:
            domain: Company domain
            website_url: Full website URL
            scraped_metadata: Metadata from Layer 1
            layer1_data: Complete Layer 1 data
            layer2_data: Complete Layer 2 data

        Returns:
            SourceResult with AI-inferred insights
        """
        start_time = time.time()

        try:
            # Get AI client
            ai_client = await get_openrouter_client()

            if not ai_client or not ai_client.client:
                raise Exception("OpenRouter client not available")

            # Combine all available context
            context = self._build_context(
                domain=domain,
                website_url=website_url or f"https://{domain}",
                metadata=scraped_metadata or {},
                layer1=layer1_data or {},
                layer2=layer2_data or {}
            )

            # Structured prompt for GPT-4o-mini
            prompt = self._build_structured_prompt(context)

            # Make AI inference
            messages = [
                {
                    "role": "system",
                    "content": "You are a strategic business analyst specializing in company intelligence."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]

            response = await ai_client._make_request(
                messages=messages,
                max_tokens=800,
                temperature=0.3  # Low temperature for consistency
            )

            # Parse structured output
            import json
            content = response["choices"][0]["message"]["content"]
            result_data = json.loads(content)

            # Validate and structure
            insights = StrategicInsights(**result_data)

            # Convert to flat dict with ai_ prefix
            data = {
                "ai_industry": insights.industry,
                "ai_target_audience": insights.target_audience,
                "ai_company_size": insights.company_size,
                "ai_digital_maturity": insights.digital_maturity,
                "ai_communication_tone": insights.communication_tone,
                "ai_key_differentiators": insights.key_differentiators,
                "ai_strategic_focus": insights.strategic_focus,
                "ai_opportunities": insights.opportunities,
            }

            # Remove None values
            data = {k: v for k, v in data.items() if v is not None and v != [] and v != ""}

            duration_ms = int((time.time() - start_time) * 1000)

            logger.info(
                f"[AI Inference Enhanced] Extracted {len(data)} insights for {domain} in {duration_ms}ms",
                extra={
                    "component": "ai_inference_enhanced",
                    "domain": domain,
                    "cost": ai_client.total_cost_usd,
                }
            )

            return SourceResult(
                source_name=self.name,
                success=True,
                data=data,
                duration_ms=duration_ms,
                cost_usd=ai_client.total_cost_usd,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"[AI Inference Enhanced] Failed for {domain}: {e}",
                exc_info=True
            )
            raise

    def _build_context(
        self,
        domain: str,
        website_url: str,
        metadata: Dict[str, Any],
        layer1: Dict[str, Any],
        layer2: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build comprehensive context for AI analysis"""
        return {
            "domain": domain,
            "website_url": website_url,
            "company_name": metadata.get("company_name") or layer1.get("company_name") or layer2.get("company_name"),
            "description": metadata.get("description") or metadata.get("meta_description"),
            "technologies": metadata.get("website_tech", []),
            "social_media": metadata.get("social_media", {}),
            "employee_count": layer2.get("employee_count"),
            "location": layer1.get("location") or layer2.get("location"),
            "industry_hint": layer2.get("industry"),
        }

    def _build_structured_prompt(self, context: Dict[str, Any]) -> str:
        """Build structured prompt for GPT-4o-mini"""
        prompt = f"""Analyze this Brazilian company and extract strategic insights.

COMPANY DATA:
Website: {context.get('website_url')}
Name: {context.get('company_name', 'Unknown')}
Description: {context.get('description', 'Not available')}
Technologies: {', '.join(context.get('technologies', [])) or 'Not detected'}
Location: {context.get('location', 'Not available')}
Employee Count: {context.get('employee_count', 'Unknown')}
Social Media: {', '.join(context.get('social_media', {}).keys()) or 'None detected'}

TASK: Extract and infer strategic insights in JSON format.

OUTPUT (JSON):
{{
  "industry": "Exact industry category from: Tecnologia|Saúde|Educação|Varejo|Serviços|Indústria|Outro",
  "target_audience": "B2B|B2C|Both",
  "company_size": "Micro|Pequena|Média|Grande (based on all signals)",
  "digital_maturity": "Baixa|Média|Alta (based on tech stack and online presence)",
  "communication_tone": "Professional|Casual|Technical|Friendly|Corporate",
  "key_differentiators": ["differentiator_1", "differentiator_2", "differentiator_3"],
  "strategic_focus": "One-sentence summary of strategic positioning",
  "opportunities": ["opportunity_1", "opportunity_2", "opportunity_3"]
}}

RULES:
1. Base analysis ONLY on provided data
2. Use Brazilian Portuguese for categorical values
3. Key differentiators: max 3 items, competitive advantages
4. Opportunities: max 3 items, growth recommendations
5. If insufficient data for a field, use "Unknown" or empty array
6. Be specific and actionable

Respond with ONLY the JSON object, no additional text."""

        return prompt
