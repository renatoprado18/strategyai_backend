"""
Report Structure Adapter (Python)

Handles both OLD (flat) and NEW (4-part nested) report structures
Ensures backward compatibility with existing analyses

OLD structure: { "analise_swot": {...}, "okrs_propostos": [...], ... }
NEW structure: { "parte_1_onde_estamos": { "analise_swot": {...} }, ... }
"""

from typing import Dict, Any


def is_new_structure(report: Dict[str, Any]) -> bool:
    """Detect if report uses new nested structure"""
    return bool(
        report.get('parte_1_onde_estamos') or
        report.get('parte_2_onde_queremos_ir') or
        report.get('parte_3_como_chegar_la') or
        report.get('parte_4_o_que_fazer_agora')
    )


def adapt_to_legacy(report: Dict[str, Any]) -> Dict[str, Any]:
    """
    Adapt new structure to legacy format for rendering
    This allows old components (PDF, etc) to work with new data
    """
    # If already legacy format, return as-is
    if not is_new_structure(report):
        return report

    legacy_report = {
        # Top-level fields remain the same
        'sumario_executivo': report.get('sumario_executivo'),
    }

    # Parte 1: Onde Estamos
    parte_1 = report.get('parte_1_onde_estamos', {})
    legacy_report['analise_pestel'] = parte_1.get('analise_pestel')
    legacy_report['sete_forcas_porter'] = parte_1.get('sete_forcas_porter')
    legacy_report['analise_swot'] = parte_1.get('analise_swot')

    # Parte 2: Para Onde Queremos Ir
    parte_2 = report.get('parte_2_onde_queremos_ir', {})
    legacy_report['estrategia_oceano_azul'] = parte_2.get('estrategia_oceano_azul')
    legacy_report['posicionamento_competitivo'] = parte_2.get('posicionamento_competitivo')
    legacy_report['tam_sam_som'] = parte_2.get('tam_sam_som')
    legacy_report['balanced_scorecard'] = parte_2.get('balanced_scorecard')

    # Parte 3: Como Chegar Lá
    parte_3 = report.get('parte_3_como_chegar_la', {})
    legacy_report['okrs_propostos'] = parte_3.get('okrs_propostos')
    legacy_report['roadmap_implementacao'] = parte_3.get('roadmap_implementacao')
    legacy_report['growth_hacking_loops'] = parte_3.get('growth_hacking_loops')

    # Parte 4: O Que Fazer Agora
    parte_4 = report.get('parte_4_o_que_fazer_agora', {})
    legacy_report['planejamento_cenarios'] = parte_4.get('planejamento_cenarios')
    legacy_report['recomendacoes_prioritarias'] = parte_4.get('recomendacoes_prioritarias')
    legacy_report['matriz_decisao_multicriterio'] = parte_4.get('matriz_decisao_multicriterio')

    # New sections
    legacy_report['ciclo_revisao'] = report.get('ciclo_revisao')
    legacy_report['mapa_integracao_frameworks'] = report.get('mapa_integracao_frameworks')
    legacy_report['referencias_casos_brasileiros'] = report.get('referencias_casos_brasileiros')

    # Keep any other fields not already handled
    for key, value in report.items():
        if (
            not key.startswith('parte_') and
            key not in ['sumario_executivo', 'ciclo_revisao', 'mapa_integracao_frameworks', 'referencias_casos_brasileiros']
        ):
            legacy_report[key] = value

    return legacy_report


def get_report_metadata(report: Dict[str, Any]) -> Dict[str, Any]:
    """Get report metadata for logging/debugging"""
    is_new = is_new_structure(report)

    has_new_features = False
    if is_new:
        has_new_features = bool(
            report.get('growth_hacking_loops') or
            report.get('matriz_decisao_multicriterio') or
            report.get('ciclo_revisao') or
            report.get('mapa_integracao_frameworks') or
            report.get('referencias_casos_brasileiros')
        )

    return {
        'structure': 'new' if is_new else 'legacy',
        'version': 'v2.0 (4-part)' if is_new else 'v1.0 (flat)',
        'framework_count': 13 if is_new else 11,
        'has_new_features': has_new_features,
    }
