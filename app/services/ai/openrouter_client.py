"""
OpenRouter AI Client for Intelligent Field Inference

Provides GPT-4o-mini integration for smart form field suggestions,
industry classification, and data validation.

Cost: $0.15 per 1M tokens (extremely cost-effective)
"""

import logging
import json
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.core.exceptions import ExternalServiceError

logger = logging.getLogger(__name__)

settings = get_settings()


# Check if OpenRouter is configured
OPENROUTER_AVAILABLE = bool(settings.openrouter_api_key)
if not OPENROUTER_AVAILABLE:
    logger.warning("OpenRouter API key not configured - AI inference features will be disabled")


# ============================================================================
# RESPONSE MODELS
# ============================================================================


class IndustryInference(BaseModel):
    """Industry classification result"""

    industry: str
    confidence: float  # 0-100
    reasoning: str
    alternatives: List[str] = []


class CompanyInfoExtraction(BaseModel):
    """Extracted company information"""

    industry: Optional[str] = None
    company_size: Optional[str] = None  # Micro/Pequena/Média/Grande
    digital_maturity: Optional[str] = None  # Baixa/Média/Alta
    target_audience: Optional[str] = None  # B2B/B2C/Both
    key_differentiators: List[str] = []
    confidence_scores: Dict[str, float] = {}


class FieldSuggestion(BaseModel):
    """AI-powered field suggestion"""

    field_name: str
    suggested_value: Any
    confidence: float  # 0-100
    source: str  # e.g., "AI inference from metadata"
    should_auto_fill: bool  # True if confidence > 85%


# ============================================================================
# OPENROUTER CLIENT
# ============================================================================


class OpenRouterClient:
    """
    OpenRouter API client for GPT-4o-mini inference

    Features:
    - Industry classification
    - Company info extraction
    - Field value suggestions
    - Social media validation
    - Cost tracking
    """

    BASE_URL = "https://openrouter.ai/api/v1"
    MODEL = "openai/gpt-4o-mini"  # $0.15/1M tokens

    def __init__(self):
        self.api_key = settings.openrouter_api_key

        # Graceful degradation if no API key
        if not self.api_key:
            logger.warning("OpenRouter API key not configured - creating disabled client")
            self.client = None
            self.total_tokens_used = 0
            self.total_cost_usd = 0.0
            return

        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "HTTP-Referer": "https://imensiah.com",  # Optional
                "X-Title": "IMENSIAH Form Intelligence"  # Optional
            },
            timeout=30.0
        )

        self.total_tokens_used = 0
        self.total_cost_usd = 0.0

    async def close(self):
        """Close HTTP client"""
        if self.client:
            await self.client.aclose()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    async def _make_request(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.3
    ) -> Dict[str, Any]:
        """
        Make request to OpenRouter API

        Args:
            messages: Conversation messages
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (0-1, lower = more deterministic)

        Returns:
            API response with completion

        Raises:
            ExternalServiceError: If API call fails
        """
        # Graceful failure if client not initialized
        if not self.client:
            logger.error("OpenRouter client not initialized (missing API key)")
            raise ExternalServiceError(
                "OpenRouter",
                "API key not configured - AI inference unavailable"
            )

        try:
            response = await self.client.post(
                "/chat/completions",
                json={
                    "model": self.MODEL,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "response_format": {"type": "json_object"}
                }
            )

            response.raise_for_status()
            data = response.json()

            # Track usage
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            self.total_tokens_used += tokens

            # Calculate cost: $0.15 per 1M tokens
            cost = (tokens / 1_000_000) * 0.15
            self.total_cost_usd += cost

            logger.info(
                f"OpenRouter API call: {tokens} tokens, ${cost:.6f}, "
                f"total: {self.total_tokens_used} tokens, ${self.total_cost_usd:.4f}"
            )

            return data

        except httpx.HTTPStatusError as e:
            logger.error(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
            raise ExternalServiceError("OpenRouter", f"HTTP {e.response.status_code}")

        except Exception as e:
            logger.error(f"OpenRouter request failed: {str(e)}")
            raise ExternalServiceError("OpenRouter", str(e))

    # ========================================================================
    # INDUSTRY CLASSIFICATION
    # ========================================================================

    async def infer_industry_from_description(
        self,
        description: str,
        website_metadata: Optional[Dict[str, Any]] = None
    ) -> IndustryInference:
        """
        Classify company industry from user description and website metadata

        Args:
            description: User's business description
            website_metadata: Optional scraped metadata

        Returns:
            Industry classification with confidence
        """
        # Available industry options (matching frontend)
        industries = [
            "Tecnologia",
            "Saúde",
            "Educação",
            "Varejo",
            "Serviços",
            "Indústria",
            "Outro"
        ]

        # Build context
        context = f"Descrição do negócio: {description}\n"

        if website_metadata:
            if website_metadata.get("meta_description"):
                context += f"Descrição do site: {website_metadata['meta_description']}\n"
            if website_metadata.get("meta_keywords"):
                context += f"Palavras-chave: {', '.join(website_metadata['meta_keywords'])}\n"

        prompt = f"""Você é um especialista em classificação de empresas brasileiras.

{context}

Classifique esta empresa em UMA das seguintes categorias:
{', '.join(industries)}

Responda em JSON com o formato exato:
{{
    "industry": "nome_da_categoria_escolhida",
    "confidence": número_de_0_a_100,
    "reasoning": "breve explicação da escolha",
    "alternatives": ["outras_categorias_possíveis"]
}}

Seja preciso e baseie-se apenas nas informações fornecidas."""

        messages = [
            {"role": "system", "content": "Você é um assistente de classificação de empresas."},
            {"role": "user", "content": prompt}
        ]

        response = await self._make_request(messages, max_tokens=300)

        # Parse response
        import json
        content = response["choices"][0]["message"]["content"]
        result = json.loads(content)

        return IndustryInference(**result)

    # ========================================================================
    # COMPANY INFO EXTRACTION
    # ========================================================================

    async def extract_company_info_from_text(
        self,
        website_url: str,
        scraped_metadata: Dict[str, Any],
        user_description: Optional[str] = None
    ) -> CompanyInfoExtraction:
        """
        Extract comprehensive company information from website and description

        Args:
            website_url: Company website
            scraped_metadata: Metadata from website scraping
            user_description: Optional user-provided description

        Returns:
            Extracted company information with confidence scores
        """
        prompt = f"""Analise esta empresa brasileira e extraia informações estruturadas.

Website: {website_url}
Título: {scraped_metadata.get('company_name', 'N/A')}
Descrição: {scraped_metadata.get('meta_description', 'N/A')}
Tecnologias: {', '.join(scraped_metadata.get('website_tech', []))}
"""

        if user_description:
            prompt += f"Descrição do usuário: {user_description}\n"

        prompt += """
Extraia e infira as seguintes informações em JSON:

{{
    "industry": "Tecnologia|Saúde|Educação|Varejo|Serviços|Indústria|Outro",
    "company_size": "Micro|Pequena|Média|Grande",
    "digital_maturity": "Baixa|Média|Alta",
    "target_audience": "B2B|B2C|Both",
    "key_differentiators": ["diferencial_1", "diferencial_2", "diferencial_3"],
    "confidence_scores": {{
        "industry": 0-100,
        "company_size": 0-100,
        "digital_maturity": 0-100,
        "target_audience": 0-100
    }}
}}

Baseie-se APENAS nas informações fornecidas. Se não tiver certeza, use confidence baixo."""

        messages = [
            {"role": "system", "content": "Você é um analista de empresas especializado."},
            {"role": "user", "content": prompt}
        ]

        response = await self._make_request(messages, max_tokens=500)

        # Parse response
        import json
        content = response["choices"][0]["message"]["content"]
        result = json.loads(content)

        return CompanyInfoExtraction(**result)

    # ========================================================================
    # SOCIAL MEDIA VALIDATION
    # ========================================================================

    async def validate_social_media_handle(
        self,
        platform: str,
        handle: str
    ) -> Dict[str, Any]:
        """
        Validate and suggest corrections for social media handles

        Args:
            platform: instagram, tiktok, linkedin
            handle: User's input

        Returns:
            Validation result with suggestions
        """
        prompt = f"""Valide este handle de rede social:

Plataforma: {platform}
Handle digitado: {handle}

Retorne em JSON:
{{
    "is_valid": true|false,
    "corrected_handle": "handle_corrigido_sem_@",
    "formatted_url": "https://...",
    "suggestions": ["sugestões de correção se aplicável"],
    "confidence": 0-100
}}

Regras:
- Instagram: só letras, números, pontos e underscores
- TikTok: só letras, números, pontos e underscores
- LinkedIn: formato /company/nome ou /in/nome"""

        messages = [
            {"role": "system", "content": "Você valida handles de redes sociais."},
            {"role": "user", "content": prompt}
        ]

        response = await self._make_request(messages, max_tokens=200)

        # Parse response
        import json
        content = response["choices"][0]["message"]["content"]
        return json.loads(content)

    # ========================================================================
    # FIELD SUGGESTIONS
    # ========================================================================

    async def suggest_missing_fields(
        self,
        known_data: Dict[str, Any],
        missing_fields: List[str]
    ) -> List[FieldSuggestion]:
        """
        Suggest values for missing form fields based on known data

        Args:
            known_data: Data already collected
            missing_fields: Fields that need suggestions

        Returns:
            List of field suggestions with confidence
        """
        prompt = f"""Com base nos dados conhecidos sobre esta empresa, sugira valores para os campos faltantes.

Dados conhecidos:
{json.dumps(known_data, indent=2, ensure_ascii=False)}

Campos faltantes: {', '.join(missing_fields)}

Retorne em JSON (array):
[
    {{
        "field_name": "nome_do_campo",
        "suggested_value": "valor_sugerido",
        "confidence": 0-100,
        "source": "explicação_da_inferência",
        "should_auto_fill": true|false
    }}
]

Regras:
- should_auto_fill = true APENAS se confidence > 85
- Se não tiver dados suficientes, use confidence < 60
- Seja conservador nas sugestões"""

        messages = [
            {"role": "system", "content": "Você sugere valores para campos de formulário."},
            {"role": "user", "content": prompt}
        ]

        response = await self._make_request(messages, max_tokens=600)

        # Parse response
        import json
        content = response["choices"][0]["message"]["content"]
        suggestions_data = json.loads(content)

        return [FieldSuggestion(**s) for s in suggestions_data]


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_openrouter_client: Optional[OpenRouterClient] = None


async def get_openrouter_client() -> OpenRouterClient:
    """Get singleton OpenRouter client instance"""
    global _openrouter_client

    if _openrouter_client is None:
        _openrouter_client = OpenRouterClient()

    return _openrouter_client


async def close_openrouter_client():
    """Close OpenRouter client"""
    global _openrouter_client

    if _openrouter_client is not None:
        await _openrouter_client.close()
        _openrouter_client = None
