"""
Stage 5: Risk Quantification + Priority Scoring
Model: Claude 3.5 Sonnet (best reasoning)
Cost: ~$0.08 per call
"""

import json
import logging
from typing import Dict, Any

from app.services.analysis.llm_client import call_llm_with_retry
from app.core.model_config import get_model_for_stage, get_stage_config

logger = logging.getLogger(__name__)

MODEL_RISK_SCORING = get_model_for_stage("risk_scoring")


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
