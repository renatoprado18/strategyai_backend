"""
Stage 4: Competitive Intelligence Matrix
Model: Gemini Pro (great at structured data)
Cost: ~$0.05 per call
"""

import json
import logging
from typing import Dict, Any

from app.services.analysis.llm_client import call_llm_with_retry
from app.core.model_config import get_model_for_stage, get_stage_config

logger = logging.getLogger(__name__)

MODEL_COMPETITIVE = get_model_for_stage("competitive")


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
