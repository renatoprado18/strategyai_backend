"""
Stage 3: Strategic Frameworks
Model: GPT-4o (expensive but best for frameworks)
Cost: ~$0.073 per call
"""

import json
import logging
from typing import Dict, Any, Optional, List

from app.services.analysis.llm_client import call_llm_with_retry
from app.core.model_config import get_model_for_stage, get_stage_config

logger = logging.getLogger(__name__)

MODEL_STRATEGY = get_model_for_stage("strategy")
MODEL_COMPETITIVE = get_model_for_stage("competitive")


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
