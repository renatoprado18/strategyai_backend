"""
Enhanced AI Analysis Engine with 10XMentorAI Frameworks
Multi-model orchestration for premium consulting-grade reports
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

# Model selection based on phase
MODEL_RESEARCH = "anthropic/claude-3.5-sonnet"  # Best for research and analysis
MODEL_STRATEGY = "openai/gpt-4o"  # Best for strategic frameworks
MODEL_POLISH = "anthropic/claude-3-opus"  # Best for executive-level writing

TIMEOUT = 120.0  # 2 minutes for complex analysis


def build_enhanced_prompt(
    company: str,
    industry: str,
    website: Optional[str],
    challenge: Optional[str],
    apify_data: Optional[Dict[str, Any]] = None,
) -> str:
    """Build comprehensive 10XMentorAI-based strategic analysis prompt"""

    # Build enrichment context
    enrichment_context = ""
    if apify_data and apify_data.get("apify_enabled"):
        enrichment_context = "\n\n## DADOS DE MERCADO E PESQUISA\n\n"

        if "website_data" in apify_data:
            web = apify_data["website_data"]
            enrichment_context += f"**Website da Empresa:**\n{web.get('content_summary', 'N/A')}\n\n"

        if "competitor_data" in apify_data:
            comp = apify_data["competitor_data"]
            enrichment_context += f"**Análise de Concorrentes:**\n{comp.get('market_insights', 'N/A')}\n\n"

        if "industry_trends" in apify_data:
            trends = apify_data["industry_trends"]
            enrichment_context += f"**Tendências do Setor:**\n{trends.get('summary', 'N/A')}\n\n"

    prompt = f"""# CONTEXTO E MISSÃO

Você é um consultor estratégico sênior da McKinsey com 15+ anos de experiência. Você está preparando uma análise estratégica executiva de nível premium (equivalente a relatórios de US$ 50.000+) para o cliente abaixo.

## INFORMAÇÕES DO CLIENTE

- **Empresa:** {company}
- **Setor/Indústria:** {industry}
- **Website:** {website or 'Não fornecido'}
- **Desafio Principal:** {challenge or 'Não especificado'}{enrichment_context}

---

# FRAMEWORKS ESTRATÉGICOS A APLICAR

Você DEVE aplicar os seguintes frameworks de forma rigorosa e específica:

## 1. Análise PESTEL Completa
Analise fatores macro-ambientais ESPECÍFICOS ao {industry} no Brasil em 2025-2026:
- **Político:** Regulamentações, políticas governamentais, estabilidade política
- **Econômico:** Crescimento do PIB, inflação, taxas de juros, poder de compra
- **Social:** Demografia, mudanças culturais, tendências de consumo
- **Tecnológico:** Inovações disruptivas, transformação digital, automação
- **Ambiental:** Sustentabilidade, ESG, economia circular
- **Legal:** Leis específicas do setor, compliance, proteção de dados (LGPD)

## 2. Cinco Forças de Porter
Avalie a intensidade competitiva no setor {industry}:
- Ameaça de novos entrantes (barreiras de entrada)
- Poder de barganha dos fornecedores
- Poder de barganha dos compradores
- Ameaça de produtos/serviços substitutos
- Rivalidade entre concorrentes existentes

## 3. Análise SWOT Estratégica
NÃO liste características genéricas. CADA item deve:
- Ser específico para {company}
- Ter evidências/justificativa
- Incluir impacto quantificado quando possível

## 4. Estratégia do Oceano Azul
Identifique espaços de mercado não contestados:
- **Eliminar:** Que fatores aceitos pelo setor devem ser eliminados?
- **Reduzir:** Que fatores devem ser reduzidos abaixo do padrão?
- **Elevar:** Que fatores devem ser elevados acima do padrão?
- **Criar:** Que novos fatores devem ser criados?

## 5. Análise de Mercado (TAM-SAM-SOM)
Estime o tamanho do mercado:
- **TAM** (Total Addressable Market): Mercado total em R$
- **SAM** (Serviceable Available Market): Mercado disponível para {company}
- **SOM** (Serviceable Obtainable Market): Mercado realista atingível

## 6. Posicionamento Competitivo
- Identifique TOP 3-5 concorrentes diretos
- Analise vantagens/desvantagens competitivas de cada um
- Defina o diferencial único de {company}
- Mapeie posicionamento (preço vs. qualidade, inovação vs. tradição)

## 7. OKRs com KPIs Reais
Não objetivos genéricos! Cada OKR deve ter:
- **Objetivo:** Ambicioso, qualitativo, inspirador
- **Key Results:** 3-5 resultados MENSURÁVEIS com números específicos
- **KPIs:** Métricas exatas para rastrear progresso
- **Prazo:** Trimestre específico
- **Responsável:** Função sugerida (CEO, CMO, CTO, etc.)

## 8. Balanced Scorecard
Organize objetivos em 4 perspectivas:
- **Financeira:** Receita, margem, ROI, CAC, LTV
- **Cliente:** NPS, satisfação, retenção, aquisição
- **Processos Internos:** Eficiência, qualidade, inovação
- **Aprendizado & Crescimento:** Treinamento, cultura, tecnologia

## 9. Planejamento de Cenários
Crie 3 cenários futuros para 12-18 meses:
- **Otimista:** Melhores condições de mercado (probabilidade ~25%)
- **Realista:** Cenário mais provável (probabilidade ~50%)
- **Pessimista:** Desafios severos (probabilidade ~25%)

Para cada cenário: impacto em receita, ações requeridas, mitigação de riscos

---

# REQUISITOS DE QUALIDADE

## Linguagem e Tom
- **Executivo:** Direto, conciso, sem jargão desnecessário
- **Brasileiro:** Português brasileiro fluente, contexto local
- **Data-Driven:** Use números, percentagens, estatísticas reais
- **Acionável:** Cada recomendação deve ter "O QUE fazer", "COMO fazer", "QUANDO fazer"

## Especificidade
❌ **EVITE:** "A empresa deve melhorar seu marketing digital"
✅ **FAÇA:** "Implementar campanha de Instagram Reels segmentada para profissionais 25-35 anos em SP, orçamento R$ 15k/mês, CAC esperado R$ 45, meta 300 leads qualificados em Q1 2025"

❌ **EVITE:** "Expandir a equipe"
✅ **FAÇA:** "Contratar 2 desenvolvedores seniores (R$ 12k/mês cada) e 1 designer UX (R$ 8k/mês) até março/2025 para lançar MVP do produto B em maio/2025"

## Dados e Evidências
- Cite fontes quando possível (relatórios de mercado, estatísticas do setor)
- Use dados do Apify quando disponíveis
- Estime números quando exatos não disponíveis (mas marque como "estimado")

---

# FORMATO DE SAÍDA JSON

Retorne APENAS JSON válido seguindo esta estrutura EXATA:

```json
{{
  "sumario_executivo": "3-4 parágrafos executivos destacando: (1) Situação atual da empresa, (2) Principais desafios e oportunidades identificados, (3) Recomendações prioritárias com impacto esperado",

  "analise_pestel": {{
    "politico": "2-3 parágrafos específicos sobre fatores políticos impactando {industry} no Brasil em 2025",
    "economico": "2-3 parágrafos sobre tendências econômicas e impacto em {industry}",
    "social": "2-3 parágrafos sobre mudanças sociais e comportamento do consumidor",
    "tecnologico": "2-3 parágrafos sobre inovações tecnológicas e transformação digital",
    "ambiental": "2 parágrafos sobre sustentabilidade, ESG e impacto ambiental",
    "legal": "2 parágrafos sobre regulamentações e compliance (LGPD, etc.)"
  }},

  "cinco_forcas_porter": {{
    "ameaca_novos_entrantes": "Análise das barreiras de entrada: capital, tecnologia, regulação, marca. Classificar intensidade como: Baixa/Média/Alta",
    "poder_fornecedores": "Análise do poder de barganha dos fornecedores. Quantos fornecedores? Concentração? Custo de troca?",
    "poder_compradores": "Análise do poder dos clientes. Concentração de clientes? Sensibilidade a preço? Custo de troca?",
    "ameaca_substitutos": "Produtos/serviços alternativos que podem substituir a oferta. Qual a probabilidade e impacto?",
    "rivalidade_concorrentes": "Intensidade da competição. Quantos players? Diferenciação? Taxa de crescimento do mercado?"
  }},

  "analise_swot": {{
    "forcas": [
      "Força específica com evidência (ex: 'Equipe técnica de 8 desenvolvedores seniores com média 10 anos exp, incluindo ex-Google e ex-Nubank')",
      "... (3-5 forças total)"
    ],
    "fraquezas": [
      "Fraqueza específica com impacto (ex: 'Dependência de 2 clientes que representam 70% da receita, risco de concentração alto')",
      "... (3-5 fraquezas)"
    ],
    "oportunidades": [
      "Oportunidade quantificada (ex: 'Mercado de fintech B2B crescendo 45% aa, TAM estimado R$ 12 bilhões, acesso a apenas 0.5% atualmente')",
      "... (3-5 oportunidades)"
    ],
    "ameacas": [
      "Ameaça com mitigação (ex: 'Entrada de players internacionais (Stripe, Adyen) com capital abundante. Mitigação: focar em nicho regulatório brasileiro e suporte local')",
      "... (3-5 ameaças)"
    ]
  }},

  "tam_sam_som": {{
    "tam_total_market": "R$ X bilhões - Mercado total de {industry} no Brasil",
    "sam_available_market": "R$ Y milhões - Mercado disponível para {company} (ex: apenas segmento PME, apenas região Sudeste)",
    "som_obtainable_market": "R$ Z milhões - Mercado realista atingível nos próximos 12-18 meses",
    "justificativa": "Explicação de como chegou nestes números"
  }},

  "posicionamento_competitivo": {{
    "principais_concorrentes": [
      {{
        "nome": "Concorrente A",
        "posicionamento": "Premium, grandes empresas",
        "vantagens": "Marca estabelecida, capital abundante",
        "fraquezas": "Produto complexo, suporte lento",
        "share_estimado": "30%"
      }},
      {{
        "nome": "Concorrente B",
        "posicionamento": "Low-cost, PMEs",
        "vantagens": "Preço baixo, onboarding rápido",
        "fraquezas": "Features limitadas, suporte ruim",
        "share_estimado": "25%"
      }}
    ],
    "diferencial_unico": "Descrição clara do que faz {company} único. Ex: 'Único player combinando IA avançada + compliance brasileiro + suporte consultivo em português'",
    "matriz_posicionamento": "Descrição de onde {company} se posiciona vs concorrentes (preço vs qualidade, inovação vs tradição, etc.)"
  }},

  "estrategia_oceano_azul": {{
    "eliminar": ["Fator aceito pelo setor que deve ser eliminado", "..."],
    "reduzir": ["Fator a reduzir abaixo do padrão setorial", "..."],
    "elevar": ["Fator a elevar acima do padrão setorial", "..."],
    "criar": ["Novo fator inexistente no setor a criar", "..."]
  }},

  "okrs_propostos": [
    {{
      "trimestre": "Q1 2025",
      "objetivo": "Objetivo ambicioso e qualitativo (ex: 'Tornar-se o líder em fintech B2B para PMEs no Sudeste')",
      "resultados_chave": [
        "KR1: Aumentar MRR de R$ 50k para R$ 150k (crescimento 200%)",
        "KR2: Lançar 3 novas features de compliance validadas por 20+ beta testers",
        "KR3: Alcançar NPS de 50+ com 100+ clientes ativos"
      ],
      "metricas_kpi": [
        "MRR (Monthly Recurring Revenue)",
        "Churn rate (meta < 5%/mês)",
        "CAC (Customer Acquisition Cost - meta < R$ 500)",
        "LTV/CAC ratio (meta > 3:1)"
      ],
      "responsavel_sugerido": "CEO + CMO",
      "investimento_estimado": "R$ 80k (R$ 50k marketing + R$ 30k produto)"
    }},
    {{
      "trimestre": "Q2 2025",
      "objetivo": "Segundo objetivo...",
      "resultados_chave": ["KR1", "KR2", "KR3"],
      "metricas_kpi": ["..."],
      "responsavel_sugerido": "...",
      "investimento_estimado": "R$ ..."
    }}
  ],

  "balanced_scorecard": {{
    "perspectiva_financeira": [
      "Aumentar receita recorrente (MRR) em 30% ao trimestre",
      "Melhorar margem bruta de 45% para 60% através de automação",
      "Reduzir CAC de R$ 800 para R$ 500 otimizando funil de marketing"
    ],
    "perspectiva_cliente": [
      "Elevar NPS de 35 para 50+",
      "Reduzir churn de 8% para < 5% ao mês",
      "Aumentar taxa de ativação de 40% para 70%"
    ],
    "perspectiva_processos": [
      "Reduzir tempo de onboarding de 5 dias para 2 dias",
      "Automatizar 80% dos processos de compliance",
      "Implementar CI/CD para deploys diários sem downtime"
    ],
    "perspectiva_aprendizado": [
      "Treinar 100% do time em metodologia Agile até março/2025",
      "Aumentar employee satisfaction de 70% para 85%",
      "Implementar programa de innovation time (20% do tempo em projetos próprios)"
    ]
  }},

  "planejamento_cenarios": {{
    "cenario_otimista": {{
      "descricao": "Economia cresce 3.5%, regulação favorável aprovada, captação Série A de R$ 5M bem-sucedida",
      "probabilidade": "20-25%",
      "impacto_receita": "MRR cresce para R$ 300k em 12 meses (crescimento 6x)",
      "gatilhos": ["Taxa Selic cai abaixo de 10%", "Lei de fintechs aprovada", "Investidor lead confirmado"],
      "acoes_requeridas": [
        "Acelerar contratações (dobrar time de 10 para 20 pessoas)",
        "Investir pesado em marketing (R$ 100k/mês)",
        "Expandir para Rio de Janeiro e Minas Gerais"
      ]
    }},
    "cenario_realista": {{
      "descricao": "Economia estável, competição aumenta gradualmente, crescimento orgânico constante",
      "probabilidade": "50-60%",
      "impacto_receita": "MRR cresce para R$ 180k em 12 meses (crescimento 3.6x)",
      "gatilhos": ["PIB cresce ~2%", "Churn mantém < 6%", "2 grandes clientes fecham"],
      "acoes_requeridas": [
        "Crescimento controlado do time (15 pessoas)",
        "Marketing moderado (R$ 40k/mês)",
        "Focar em retenção e upsell de base atual"
      ]
    }},
    "cenario_pessimista": {{
      "descricao": "Recessão econômica, competidor internacional entra agressivamente, perda de cliente chave",
      "probabilidade": "15-20%",
      "impacto_receita": "MRR estagna em R$ 60k com churn elevado",
      "gatilhos": ["Recessão com PIB negativo", "Stripe lança produto similar", "Cliente top 3 cancela"],
      "acoes_requeridas": [
        "Cortar custos (reduzir marketing para R$ 15k/mês)",
        "Congelar contratações",
        "Pivotar para nicho defensivo (compliance obrigatório)",
        "Buscar alternativas de funding (venture debt, grants)"
      ]
    }}
  }},

  "recomendacoes_prioritarias": [
    {{
      "prioridade": 1,
      "titulo": "Título conciso da recomendação",
      "recomendacao": "O QUE fazer - descrição detalhada da ação",
      "justificativa": "POR QUÊ - data-driven rationale com números",
      "como_implementar": [
        "Passo 1 específico com responsável e prazo",
        "Passo 2 ...",
        "Passo 3 ..."
      ],
      "prazo": "2-3 meses",
      "investimento_estimado": "R$ X mil",
      "retorno_esperado": "R$ Y mil em 6 meses (ROI de Z%)",
      "metricas_sucesso": [
        "Métrica 1 a acompanhar",
        "Métrica 2 ...",
        "Métrica 3 ..."
      ],
      "riscos_mitigacao": [
        "Risco 1 + como mitigar",
        "Risco 2 + como mitigar"
      ]
    }},
    {{
      "prioridade": 2,
      "titulo": "...",
      "...": "... (estrutura igual)"
    }},
    {{
      "prioridade": 3,
      "titulo": "...",
      "...": "..."
    }}
  ],

  "roadmap_implementacao": {{
    "primeiros_30_dias": [
      "Quick win 1 com impacto imediato",
      "Quick win 2 ...",
      "Foundation setup 1 ..."
    ],
    "60_90_dias": [
      "Initiative 1 de médio prazo",
      "Initiative 2 ...",
      "Milestone para avaliar progresso"
    ],
    "6_meses": [
      "Strategic initiative 1 de longo prazo",
      "Strategic initiative 2 ...",
      "KPIs esperados ao final de 6 meses"
    ]
  }}
}}
```

---

# CHECKLIST FINAL

Antes de retornar a análise, verifique:
- [ ] Todos os números são específicos (não use "muitos", "alguns", "crescente" - use percentagens e valores)
- [ ] Cada recomendação tem prazo e ROI estimado
- [ ] OKRs são mensuráveis (não abstratos)
- [ ] Análise considera contexto brasileiro (regulação, economia, cultura)
- [ ] Linguagem é executiva (não acadêmica)
- [ ] JSON é válido e parse-able
- [ ] Não há platitudes genéricas

IMPORTANTE: Retorne APENAS o JSON. Nenhum texto antes ou depois. JSON puro e válido.
"""

    return prompt


async def generate_enhanced_analysis(
    company: str,
    industry: str,
    website: Optional[str],
    challenge: Optional[str],
    apify_data: Optional[Dict[str, Any]] = None,
    use_multi_model: bool = True,
) -> Dict[str, Any]:
    """
    Generate premium consulting-grade analysis using enhanced prompts

    Args:
        company: Company name
        industry: Industry sector
        website: Company website
        challenge: Business challenge
        apify_data: Enriched market data
        use_multi_model: Use multi-model orchestration (more expensive but better quality)

    Returns:
        Comprehensive strategic analysis
    """

    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not set")

    prompt = build_enhanced_prompt(company, industry, website, challenge, apify_data)

    # Use GPT-4o for comprehensive strategic analysis (best balance of cost/quality)
    model = MODEL_STRATEGY

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://strategy-ai.com",
        "X-Title": "Strategy AI - 10XMentorAI Enhanced Analysis",
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are a world-class strategic consultant with deep expertise in business strategy frameworks. You produce executive-level analyses worth $50,000+. Always respond with valid, well-structured JSON only."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.8,  # Higher for creative strategic thinking
        "max_tokens": 8000,  # Much longer for comprehensive reports
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

            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"]

                # Clean markdown code blocks
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

                    # Add metadata
                    analysis_json["_metadata"] = {
                        "generated_at": datetime.now().isoformat(),
                        "model_used": model,
                        "framework_version": "10XMentorAI v2.0",
                        "quality_tier": "Premium Executive"
                    }

                    return analysis_json

                except json.JSONDecodeError as e:
                    raise Exception(f"Failed to parse AI response as JSON: {e}. Content preview: {content[:500]}")
            else:
                raise Exception(f"Unexpected API response: {data}")

    except httpx.TimeoutException:
        raise Exception("Analysis timed out after 2 minutes. The comprehensive analysis requires significant processing time.")
    except httpx.HTTPStatusError as e:
        raise Exception(f"OpenRouter API error: {e.response.status_code} - {e.response.text}")
    except Exception as e:
        raise Exception(f"Enhanced analysis failed: {str(e)}")


async def validate_enhanced_analysis(analysis: Dict[str, Any]) -> bool:
    """Validate enhanced analysis structure"""
    required_keys = [
        "sumario_executivo",
        "analise_pestel",
        "cinco_forcas_porter",
        "analise_swot",
        "tam_sam_som",
        "posicionamento_competitivo",
        "estrategia_oceano_azul",
        "okrs_propostos",
        "balanced_scorecard",
        "planejamento_cenarios",
        "recomendacoes_prioritarias",
        "roadmap_implementacao"
    ]

    for key in required_keys:
        if key not in analysis:
            print(f"[VALIDATION ERROR] Missing required key: {key}")
            return False

    return True


# Test function
async def test_enhanced_analysis():
    """Test the enhanced analysis generation"""
    try:
        result = await generate_enhanced_analysis(
            company="FinTech Inovadora Brasil",
            industry="Tecnologia Financeira",
            website="https://fintechinov.com.br",
            challenge="Precisamos escalar de R$ 50k MRR para R$ 500k MRR em 12 meses enquanto mantemos churn abaixo de 5%"
        )

        if await validate_enhanced_analysis(result):
            print("[OK] Enhanced analysis generated successfully!")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print("[ERROR] Enhanced analysis validation failed")

    except Exception as e:
        print(f"[ERROR] Test failed: {e}")


if __name__ == "__main__":
    asyncio.run(test_enhanced_analysis())
