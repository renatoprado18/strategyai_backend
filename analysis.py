"""
AI Analysis Engine using OpenRouter API
"""
import json
import httpx
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Use gpt-4o-mini for cost optimization
MODEL = "openai/gpt-4o-mini"

# 90 second timeout
TIMEOUT = 90.0


def build_analysis_prompt(
    company: str,
    industry: str,
    website: Optional[str],
    challenge: Optional[str],
    apify_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Build the prompt for AI analysis with Apify enrichment"""

    website_instruction = ""
    if website:
        website_instruction = f"\n\nWebsite da empresa: {website}\nPor favor, considere a presença online disponível publicamente ao fazer sua análise."

    challenge_context = ""
    if challenge:
        challenge_context = f"\n\nDesafio atual mencionado pela empresa: \"{challenge}\""

    # Build Apify enrichment context
    apify_context = ""
    if apify_data and apify_data.get("apify_enabled"):
        apify_context = "\n\n**DADOS DE PESQUISA E ENRIQUECIMENTO (use para enriquecer sua análise):**\n"

        # Website data
        if "website_data" in apify_data and apify_data["website_data"].get("scraped_successfully"):
            web_data = apify_data["website_data"]
            apify_context += f"\n• **Website Analisado:** {web_data.get('title', 'N/A')}\n"
            apify_context += f"  Descrição: {web_data.get('description', 'N/A')[:200]}\n"
            apify_context += f"  Resumo do conteúdo: {web_data.get('content_summary', 'N/A')[:300]}\n"

        # Competitor research
        if "competitor_data" in apify_data and apify_data["competitor_data"].get("researched_successfully"):
            comp_data = apify_data["competitor_data"]
            apify_context += f"\n• **Pesquisa de Concorrentes:**\n"
            apify_context += f"  {comp_data.get('competitors_found', 0)} resultados encontrados\n"
            apify_context += f"  Insights: {comp_data.get('market_insights', 'N/A')[:300]}\n"

        # Industry trends
        if "industry_trends" in apify_data and apify_data["industry_trends"].get("researched_successfully"):
            trends = apify_data["industry_trends"]
            apify_context += f"\n• **Tendências do Setor {industry}:**\n"
            apify_context += f"  {trends.get('trends_found', 0)} insights coletados\n"
            apify_context += f"  Resumo: {trends.get('summary', 'N/A')[:400]}\n"

        # Company enrichment
        if "company_enrichment" in apify_data and apify_data["company_enrichment"].get("enriched_successfully"):
            enrichment = apify_data["company_enrichment"]
            apify_context += f"\n• **Informações Adicionais da Empresa:**\n"
            apify_context += f"  {enrichment.get('enrichment_sources', 0)} fontes consultadas\n"
            apify_context += f"  Resumo: {enrichment.get('summary', 'N/A')[:300]}\n"

        apify_context += "\n**Use estes dados reais para tornar sua análise mais precisa e específica.**\n"

    prompt = f"""Você é um consultor estratégico sênior especializado em análise empresarial.

Sua tarefa é gerar uma análise estratégica completa e acionável para a seguinte empresa:

**Nome da Empresa:** {company}
**Setor/Indústria:** {industry}{website_instruction}{challenge_context}{apify_context}

Gere um relatório estruturado em JSON com os seguintes componentes:

1. **Diagnóstico Estratégico (SWOT)**
   - Forças: Liste 3-5 forças principais
   - Fraquezas: Liste 3-5 fraquezas principais
   - Oportunidades: Liste 3-5 oportunidades de mercado
   - Ameaças: Liste 3-5 ameaças externas

2. **Análise de Mercado (PESTEL - Highlights)**
   - Político: Um parágrafo sobre fatores políticos relevantes
   - Econômico: Um parágrafo sobre tendências econômicas
   - Social: Um parágrafo sobre mudanças sociais
   - Tecnológico: Um parágrafo sobre inovações tecnológicas
   - Ambiental: Um parágrafo sobre sustentabilidade
   - Legal: Um parágrafo sobre aspectos regulatórios

3. **Oportunidades Identificadas**
   - Liste 3-5 oportunidades estratégicas específicas e acionáveis

4. **Recomendações Prioritárias**
   - Top 3 ações imediatas que a empresa deve implementar

5. **Proposta de OKRs para Próximo Trimestre**
   - 2-3 OKRs (Objectives and Key Results) com objetivos claros e resultados mensuráveis

**IMPORTANTE:**
- Seja específico e relevante para o setor {industry}
- Use dados e tendências reais de 2025-2026
- Foque em insights acionáveis, não genéricos
- Mantenha linguagem profissional em português brasileiro
- Considere o contexto brasileiro e latino-americano

Retorne APENAS um JSON válido no seguinte formato:

{{
  "diagnostico_estrategico": {{
    "forças": ["força 1", "força 2", "força 3"],
    "fraquezas": ["fraqueza 1", "fraqueza 2", "fraqueza 3"],
    "oportunidades": ["oportunidade 1", "oportunidade 2", "oportunidade 3"],
    "ameaças": ["ameaça 1", "ameaça 2", "ameaça 3"]
  }},
  "analise_mercado": {{
    "político": "texto...",
    "econômico": "texto...",
    "social": "texto...",
    "tecnológico": "texto...",
    "ambiental": "texto...",
    "legal": "texto..."
  }},
  "oportunidades_identificadas": [
    "oportunidade 1",
    "oportunidade 2",
    "oportunidade 3"
  ],
  "recomendacoes_prioritarias": [
    "recomendação 1",
    "recomendação 2",
    "recomendação 3"
  ],
  "proposta_okrs": [
    {{
      "objetivo": "Objetivo 1",
      "resultados_chave": ["KR1", "KR2", "KR3"]
    }},
    {{
      "objetivo": "Objetivo 2",
      "resultados_chave": ["KR1", "KR2", "KR3"]
    }}
  ]
}}"""

    return prompt


async def generate_analysis(
    company: str,
    industry: str,
    website: Optional[str],
    challenge: Optional[str],
    apify_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Generate AI analysis using OpenRouter API with optional Apify enrichment

    Args:
        company: Company name
        industry: Industry sector
        website: Company website URL
        challenge: Business challenge
        apify_data: Optional enriched data from Apify services

    Returns:
        Dict containing the analysis report

    Raises:
        Exception if analysis fails
    """

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set in environment variables")

    prompt = build_analysis_prompt(company, industry, website, challenge, apify_data)

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://strategy-ai.com",  # Update with your domain
        "X-Title": "Strategy AI Lead Generator",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a senior strategic business consultant. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 3000,
    }

    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload
            )
            response.raise_for_status()

            data = response.json()

            # Extract content from OpenAI-style response
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]

                # Clean markdown code blocks if present
                content = content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                content = content.strip()

                # Parse JSON
                try:
                    analysis_json = json.loads(content)
                    return analysis_json
                except json.JSONDecodeError as e:
                    raise Exception(f"Failed to parse AI response as JSON: {e}. Content: {content[:200]}")
            else:
                raise Exception(f"Unexpected API response format: {data}")

    except httpx.TimeoutException:
        raise Exception("AI analysis timed out after 90 seconds")
    except httpx.HTTPStatusError as e:
        raise Exception(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Analysis failed: {str(e)}")


async def validate_analysis_structure(analysis: Dict[str, Any]) -> bool:
    """Validate that analysis has required structure"""
    required_keys = [
        "diagnostico_estrategico",
        "analise_mercado",
        "oportunidades_identificadas",
        "recomendacoes_prioritarias",
        "proposta_okrs"
    ]

    for key in required_keys:
        if key not in analysis:
            return False

    # Validate SWOT structure
    swot = analysis.get("diagnostico_estrategico", {})
    if not all(k in swot for k in ["forças", "fraquezas", "oportunidades", "ameaças"]):
        return False

    # Validate PESTEL structure
    pestel = analysis.get("analise_mercado", {})
    if not all(k in pestel for k in ["político", "econômico", "social", "tecnológico", "ambiental", "legal"]):
        return False

    return True


# Test function
async def test_analysis():
    """Test the analysis generation"""
    try:
        result = await generate_analysis(
            company="Tech Startup Exemplo",
            industry="Tecnologia",
            website="https://exemplo.com.br",
            challenge="Precisamos escalar vendas e melhorar retenção de clientes"
        )

        if await validate_analysis_structure(result):
            print("[OK] Analysis generated successfully!")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("[ERROR] Analysis structure validation failed")

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_analysis())
