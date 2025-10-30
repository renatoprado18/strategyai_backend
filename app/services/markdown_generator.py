"""
Markdown Report Generator
Converts strategic analysis reports to clean, editable markdown format

Features:
- Clean, readable in any text editor
- YAML frontmatter for metadata
- Supports both old (flat) and new (4-part) report structures
- Robust formatting that survives Word/ChatGPT copy/paste
- Portuguese section names matching original reports
"""

from datetime import datetime
from typing import Dict, Any, List, Optional
from app.services.report_adapter import adapt_to_legacy, is_new_structure, get_report_metadata


def _escape_markdown(text: str) -> str:
    """Minimal escaping - keep it simple for copy/paste robustness"""
    if not text:
        return ""
    # Only escape pipe characters in tables
    return text.replace("|", "\\|")


def _format_list(items: List[str], indent: int = 0) -> str:
    """Format list items with optional indentation"""
    if not items:
        return ""

    indent_str = "  " * indent
    lines = []
    for item in items:
        if isinstance(item, str):
            # Clean up the item text
            item_text = item.strip()
            if item_text:
                lines.append(f"{indent_str}- {item_text}")

    return "\n".join(lines) if lines else ""


def _format_dict_as_text(data: Dict[str, Any], prefix: str = "**") -> str:
    """Format dictionary as key: value pairs"""
    if not data:
        return ""

    lines = []
    for key, value in data.items():
        if value:
            # Format key as bold
            formatted_key = key.replace("_", " ").title()
            if isinstance(value, list):
                lines.append(f"{prefix}{formatted_key}:{prefix}")
                lines.append(_format_list(value, indent=1))
            elif isinstance(value, dict):
                lines.append(f"{prefix}{formatted_key}:{prefix}")
                lines.append(_format_dict_as_text(value, prefix="**"))
            else:
                lines.append(f"{prefix}{formatted_key}:{prefix} {value}")

    return "\n".join(lines)


def _format_okr_table(okrs: List[Dict[str, Any]]) -> str:
    """Format OKRs as markdown table"""
    if not okrs:
        return ""

    # Table header
    table = "| Trimestre | Objetivo | Resultados-Chave | Investimento |\n"
    table += "|-----------|----------|------------------|-------------|\n"

    # Table rows
    for okr in okrs:
        trimestre = _escape_markdown(str(okr.get('trimestre', 'Q1 2025')))
        objetivo = _escape_markdown(str(okr.get('objetivo', '')))

        # Format key results as bullet list in cell
        resultados = okr.get('resultados_chave', [])
        if isinstance(resultados, list):
            resultados_text = "<br>".join([f"• {_escape_markdown(r)}" for r in resultados[:3]])
        else:
            resultados_text = ""

        investimento = _escape_markdown(str(okr.get('investimento_estimado', 'N/A')))

        table += f"| {trimestre} | {objetivo} | {resultados_text} | {investimento} |\n"

    return table


def _format_recommendation(rec: Dict[str, Any], index: int) -> str:
    """Format a single recommendation"""
    if not isinstance(rec, dict):
        return ""

    lines = []

    # Title
    prioridade = rec.get('prioridade', index)
    titulo = rec.get('titulo', f'Recomendação {index}')
    lines.append(f"### #{prioridade} - {titulo}\n")

    # Content
    if rec.get('recomendacao'):
        lines.append(f"{rec['recomendacao']}\n")

    if rec.get('justificativa'):
        lines.append(f"**Por quê:** {rec['justificativa']}\n")

    # Metadata
    metadata_parts = []
    if rec.get('prazo'):
        metadata_parts.append(f"**Prazo:** {rec['prazo']}")
    if rec.get('investimento_estimado'):
        metadata_parts.append(f"**Investimento:** {rec['investimento_estimado']}")
    if rec.get('retorno_esperado'):
        metadata_parts.append(f"**Retorno:** {rec['retorno_esperado']}")

    if metadata_parts:
        lines.append(" | ".join(metadata_parts))

    lines.append("\n---\n")

    return "\n".join(lines)


def _format_scenario(scenario: Dict[str, Any], title: str, emoji: str) -> str:
    """Format a scenario planning section"""
    if not scenario:
        return ""

    lines = [f"### {emoji} {title}\n"]

    if scenario.get('probabilidade'):
        lines.append(f"**Probabilidade:** {scenario['probabilidade']}\n")

    if scenario.get('impacto_receita'):
        lines.append(f"**Impacto na Receita:** {scenario['impacto_receita']}\n")

    if scenario.get('acoes_requeridas'):
        lines.append(f"**Ações Requeridas:** {scenario['acoes_requeridas']}\n")

    if scenario.get('riscos'):
        lines.append(f"**Riscos:** {scenario['riscos']}\n")

    return "\n".join(lines)


def generate_markdown_from_report(
    submission_data: Dict[str, Any],
    report_json: Dict[str, Any]
) -> str:
    """
    Generate clean markdown from report JSON

    Args:
        submission_data: Submission metadata (company, industry, etc.)
        report_json: Report analysis data

    Returns:
        Markdown formatted string
    """

    # Get metadata
    metadata = get_report_metadata(report_json)
    is_new = is_new_structure(report_json)

    # If new structure, keep it; otherwise use as-is
    # We'll render both structures natively to preserve full data

    # Build markdown
    md_lines = []

    # YAML Frontmatter
    md_lines.append("---")
    md_lines.append(f"report_id: {submission_data.get('id', 'N/A')}")
    md_lines.append(f"company: {submission_data.get('company', 'N/A')}")
    md_lines.append(f"industry: {submission_data.get('industry', 'N/A')}")

    if submission_data.get('website'):
        md_lines.append(f"website: {submission_data['website']}")

    # Parse date
    try:
        updated_at = datetime.fromisoformat(submission_data.get('updated_at', '').replace('Z', '+00:00'))
        date_str = updated_at.strftime('%Y-%m-%d')
    except:
        date_str = datetime.now().strftime('%Y-%m-%d')

    md_lines.append(f"generated_at: {date_str}")
    md_lines.append(f"structure: {metadata['structure']}")
    md_lines.append(f"version: {metadata['version']}")
    md_lines.append("---\n")

    # Title
    company = submission_data.get('company', 'Empresa')
    md_lines.append(f"# Análise Estratégica: {company}\n")

    # Company info section
    md_lines.append("## Informações da Empresa\n")
    md_lines.append(f"**Empresa:** {submission_data.get('company', 'N/A')}")
    md_lines.append(f"**Setor:** {submission_data.get('industry', 'N/A')}")

    if submission_data.get('website'):
        md_lines.append(f"**Website:** {submission_data['website']}")

    if submission_data.get('name'):
        md_lines.append(f"**Contato:** {submission_data['name']}")

    if submission_data.get('challenge'):
        md_lines.append(f"\n**Desafio Identificado:**")
        md_lines.append(f"{submission_data['challenge']}")

    md_lines.append(f"\n**Data de Geração:** {date_str}\n")
    md_lines.append("---\n")

    # Executive Summary (always top-level)
    if report_json.get('sumario_executivo'):
        md_lines.append("## Sumário Executivo\n")
        md_lines.append(f"{report_json['sumario_executivo']}\n")
        md_lines.append("---\n")

    # Handle structure-specific rendering
    if is_new:
        # NEW STRUCTURE: 4-part format
        _render_new_structure(report_json, md_lines)
    else:
        # OLD STRUCTURE: Flat format
        _render_legacy_structure(report_json, md_lines)

    # Footer
    md_lines.append("\n---\n")
    md_lines.append("*Relatório gerado por Strategy AI • Powered by IA*")

    return "\n".join(md_lines)


def _render_new_structure(report: Dict[str, Any], md_lines: List[str]):
    """Render new 4-part report structure"""

    # PARTE 1: ONDE ESTAMOS?
    parte_1 = report.get('parte_1_onde_estamos', {})
    if parte_1:
        md_lines.append("## Parte 1: Onde Estamos?\n")

        # PESTEL Analysis
        if parte_1.get('analise_pestel'):
            md_lines.append("### Análise PESTEL\n")
            pestel = parte_1['analise_pestel']

            for key in ['politico', 'economico', 'social', 'tecnologico', 'ambiental', 'legal']:
                if pestel.get(key):
                    md_lines.append(f"**{key.title()}:** {pestel[key]}\n")

        # 7 Forces Porter
        if parte_1.get('sete_forcas_porter'):
            md_lines.append("### Sete Forças de Porter\n")
            porter = parte_1['sete_forcas_porter']

            # Traditional forces
            if porter.get('forcas_tradicionais'):
                md_lines.append("**Forças Tradicionais:**\n")
                md_lines.append(_format_dict_as_text(porter['forcas_tradicionais']))
                md_lines.append("")

            # Modern forces
            if porter.get('forcas_modernas'):
                md_lines.append("**Forças Modernas:**\n")
                md_lines.append(_format_dict_as_text(porter['forcas_modernas']))
                md_lines.append("")

        # SWOT Analysis
        _render_swot(parte_1.get('analise_swot'), md_lines)

        md_lines.append("---\n")

    # PARTE 2: ONDE QUEREMOS IR?
    parte_2 = report.get('parte_2_onde_queremos_ir', {})
    if parte_2:
        md_lines.append("## Parte 2: Onde Queremos Ir?\n")

        # Blue Ocean Strategy
        if parte_2.get('estrategia_oceano_azul'):
            md_lines.append("### Estratégia Oceano Azul\n")
            oceano = parte_2['estrategia_oceano_azul']

            for action in ['eliminar', 'reduzir', 'elevar', 'criar']:
                if oceano.get(action):
                    md_lines.append(f"**{action.title()}:**")
                    md_lines.append(_format_list(oceano[action]))
                    md_lines.append("")

        # TAM/SAM/SOM
        _render_tam_sam_som(parte_2.get('tam_sam_som'), md_lines)

        # Balanced Scorecard
        if parte_2.get('balanced_scorecard'):
            md_lines.append("### Balanced Scorecard\n")
            bsc = parte_2['balanced_scorecard']

            for perspective in ['financeira', 'clientes', 'processos_internos', 'aprendizado_crescimento']:
                if bsc.get(perspective):
                    md_lines.append(f"**{perspective.replace('_', ' ').title()}:**")
                    if isinstance(bsc[perspective], list):
                        md_lines.append(_format_list(bsc[perspective]))
                    else:
                        md_lines.append(str(bsc[perspective]))
                    md_lines.append("")

        md_lines.append("---\n")

    # PARTE 3: COMO CHEGAR LÁ?
    parte_3 = report.get('parte_3_como_chegar_la', {})
    if parte_3:
        md_lines.append("## Parte 3: Como Chegar Lá?\n")

        # OKRs
        if parte_3.get('okrs_propostos'):
            md_lines.append("### OKRs Propostos\n")
            md_lines.append(_format_okr_table(parte_3['okrs_propostos']))
            md_lines.append("")

        # Roadmap
        if parte_3.get('roadmap_implementacao'):
            md_lines.append("### Roadmap de Implementação\n")
            md_lines.append(_format_dict_as_text(parte_3['roadmap_implementacao']))
            md_lines.append("")

        # Growth Hacking Loops
        if parte_3.get('growth_hacking_loops'):
            md_lines.append("### Growth Hacking Loops\n")
            loops = parte_3['growth_hacking_loops']

            if loops.get('leap_loop_acquisition'):
                md_lines.append("**LEAP Loop (Aquisição):**")
                md_lines.append(_format_dict_as_text(loops['leap_loop_acquisition']))
                md_lines.append("")

            if loops.get('scale_loop_monetizacao'):
                md_lines.append("**SCALE Loop (Monetização):**")
                md_lines.append(_format_dict_as_text(loops['scale_loop_monetizacao']))
                md_lines.append("")

        md_lines.append("---\n")

    # PARTE 4: O QUE FAZER AGORA?
    parte_4 = report.get('parte_4_o_que_fazer_agora', {})
    if parte_4:
        md_lines.append("## Parte 4: O Que Fazer Agora?\n")

        # Scenario Planning
        _render_scenario_planning(parte_4.get('planejamento_cenarios'), md_lines)

        # Priority Recommendations
        if parte_4.get('recomendacoes_prioritarias'):
            md_lines.append("### Recomendações Prioritárias\n")
            for idx, rec in enumerate(parte_4['recomendacoes_prioritarias'], 1):
                md_lines.append(_format_recommendation(rec, idx))

        # Multi-Criteria Decision Matrix
        if parte_4.get('matriz_decisao_multicriterio'):
            md_lines.append("### Matriz de Decisão Multicritério\n")
            md_lines.append(_format_dict_as_text(parte_4['matriz_decisao_multicriterio']))
            md_lines.append("")

        md_lines.append("---\n")

    # Additional sections
    if report.get('mapa_integracao_frameworks'):
        md_lines.append("## Mapa de Integração de Frameworks\n")
        md_lines.append(_format_dict_as_text(report['mapa_integracao_frameworks']))
        md_lines.append("\n---\n")

    if report.get('referencias_casos_brasileiros'):
        md_lines.append("## Referências de Casos Brasileiros\n")
        md_lines.append(_format_list(report['referencias_casos_brasileiros']))
        md_lines.append("\n---\n")

    if report.get('ciclo_revisao'):
        md_lines.append("## Ciclo de Revisão\n")
        md_lines.append(_format_dict_as_text(report['ciclo_revisao']))
        md_lines.append("\n---\n")


def _render_legacy_structure(report: Dict[str, Any], md_lines: List[str]):
    """Render legacy flat report structure"""

    # SWOT Analysis
    _render_swot(report.get('analise_swot'), md_lines)

    # TAM/SAM/SOM
    _render_tam_sam_som(report.get('tam_sam_som'), md_lines)

    # Priority Recommendations
    if report.get('recomendacoes_prioritarias'):
        md_lines.append("## Recomendações Prioritárias\n")
        for idx, rec in enumerate(report['recomendacoes_prioritarias'], 1):
            md_lines.append(_format_recommendation(rec, idx))
        md_lines.append("---\n")

    # Scenario Planning
    _render_scenario_planning(report.get('planejamento_cenarios'), md_lines)

    # OKRs
    if report.get('okrs_propostos'):
        md_lines.append("## OKRs Propostos\n")
        md_lines.append(_format_okr_table(report['okrs_propostos']))
        md_lines.append("\n---\n")


def _render_swot(swot: Optional[Dict[str, Any]], md_lines: List[str]):
    """Render SWOT analysis section"""
    if not swot:
        return

    md_lines.append("## Análise SWOT\n")

    # Strengths
    forcas = swot.get('forcas') or swot.get('forças', [])
    if forcas:
        md_lines.append("### 💪 Forças\n")
        md_lines.append(_format_list(forcas))
        md_lines.append("")

    # Weaknesses
    fraquezas = swot.get('fraquezas', [])
    if fraquezas:
        md_lines.append("### ⚠️ Fraquezas\n")
        md_lines.append(_format_list(fraquezas))
        md_lines.append("")

    # Opportunities
    oportunidades = swot.get('oportunidades', [])
    if oportunidades:
        md_lines.append("### 🚀 Oportunidades\n")
        md_lines.append(_format_list(oportunidades))
        md_lines.append("")

    # Threats
    ameacas = swot.get('ameacas') or swot.get('ameaças', [])
    if ameacas:
        md_lines.append("### 🎯 Ameaças\n")
        md_lines.append(_format_list(ameacas))
        md_lines.append("")

    md_lines.append("---\n")


def _render_tam_sam_som(tam_sam_som: Optional[Dict[str, Any]], md_lines: List[str]):
    """Render TAM/SAM/SOM section"""
    if not tam_sam_som:
        return

    md_lines.append("## Análise de Mercado (TAM-SAM-SOM)\n")

    # Create table
    md_lines.append("| Métrica | Valor |")
    md_lines.append("|---------|-------|")
    md_lines.append(f"| TAM (Total Addressable Market) | {tam_sam_som.get('tam_total_market', 'N/A')} |")
    md_lines.append(f"| SAM (Serviceable Available Market) | {tam_sam_som.get('sam_available_market', 'N/A')} |")
    md_lines.append(f"| SOM (Serviceable Obtainable Market) | {tam_sam_som.get('som_obtainable_market', 'N/A')} |")
    md_lines.append("")

    if tam_sam_som.get('justificativa'):
        md_lines.append(f"**Justificativa:** {tam_sam_som['justificativa']}\n")

    md_lines.append("---\n")


def _render_scenario_planning(cenarios: Optional[Dict[str, Any]], md_lines: List[str]):
    """Render scenario planning section"""
    if not cenarios:
        return

    md_lines.append("## Planejamento de Cenários\n")

    # Key uncertainty variables (if new structure)
    if cenarios.get('variaveis_chave_incerteza'):
        md_lines.append("**Variáveis-Chave de Incerteza:**")
        md_lines.append(_format_list(cenarios['variaveis_chave_incerteza']))
        md_lines.append("")

    # Scenarios
    if cenarios.get('cenario_otimista'):
        md_lines.append(_format_scenario(cenarios['cenario_otimista'], 'Cenário Otimista', '📈'))
        md_lines.append("")

    if cenarios.get('cenario_realista'):
        md_lines.append(_format_scenario(cenarios['cenario_realista'], 'Cenário Realista', '📊'))
        md_lines.append("")

    if cenarios.get('cenario_pessimista'):
        md_lines.append(_format_scenario(cenarios['cenario_pessimista'], 'Cenário Pessimista', '📉'))
        md_lines.append("")

    md_lines.append("---\n")
