"""
Markdown Report Parser
Converts markdown back to report JSON structure

Features:
- Forgiving parser (handles Word/ChatGPT formatting quirks)
- Fuzzy section matching
- Validates structure but accepts variations
- Returns warnings instead of hard errors
- Supports both old (flat) and new (4-part) structures
"""

import re
import yaml
from typing import Dict, Any, List, Optional, Tuple


class MarkdownParseError(Exception):
    """Raised when markdown cannot be parsed"""
    pass


def _clean_text(text: str) -> str:
    """Clean text from Word/ChatGPT artifacts"""
    if not text:
        return ""

    # Replace smart quotes with regular quotes
    text = text.replace('"', '"').replace('"', '"')
    text = text.replace(''', "'").replace(''', "'")

    # Replace em-dash with regular dash
    text = text.replace('—', '-').replace('–', '-')

    # Strip whitespace
    text = text.strip()

    return text


def _parse_frontmatter(markdown: str) -> Tuple[Dict[str, Any], str]:
    """
    Parse YAML frontmatter from markdown

    Returns:
        Tuple of (metadata_dict, remaining_markdown)
    """
    # Match YAML frontmatter between --- markers
    frontmatter_pattern = r'^---\s*\n(.*?)\n---\s*\n'
    match = re.search(frontmatter_pattern, markdown, re.DOTALL)

    if not match:
        return {}, markdown

    try:
        metadata = yaml.safe_load(match.group(1))
        remaining = markdown[match.end():]
        return metadata or {}, remaining
    except yaml.YAMLError as e:
        # Frontmatter is optional, continue without it
        return {}, markdown


def _parse_list_items(text: str) -> List[str]:
    """
    Parse bullet list items from text

    Handles:
    - Standard markdown bullets (-, *, +)
    - Numbered lists (1., 2., etc.)
    - Nested indentation
    - HTML bullets (• &bull;)
    """
    items = []

    # Split by lines
    lines = text.split('\n')

    for line in lines:
        line = _clean_text(line)
        if not line:
            continue

        # Match bullet patterns
        # - item, * item, + item, 1. item, • item
        match = re.match(r'^[\s]*[-*+•][\s]+(.+)$', line)
        if not match:
            match = re.match(r'^[\s]*\d+\.[\s]+(.+)$', line)

        if match:
            item_text = _clean_text(match.group(1))
            if item_text:
                items.append(item_text)
        elif line and not line.startswith('#') and not line.startswith('**'):
            # Plain text line might be a list item
            items.append(line)

    return items


def _parse_table(text: str) -> List[Dict[str, str]]:
    """
    Parse markdown table to list of dicts

    Example:
    | Header1 | Header2 |
    |---------|---------|
    | Value1  | Value2  |

    Returns: [{'Header1': 'Value1', 'Header2': 'Value2'}]
    """
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    if len(lines) < 2:
        return []

    # Parse header
    header_line = lines[0]
    headers = [h.strip() for h in header_line.split('|') if h.strip()]

    if not headers:
        return []

    # Skip separator line (usually second line)
    data_lines = [line for line in lines[1:] if not re.match(r'^\|[\s\-\|]+\|$', line)]

    # Parse data rows
    rows = []
    for line in data_lines:
        cells = [c.strip() for c in line.split('|') if c.strip()]

        if len(cells) >= len(headers):
            row_dict = {}
            for i, header in enumerate(headers):
                if i < len(cells):
                    # Clean HTML breaks and bullets
                    cell_text = cells[i].replace('<br>', '\n').replace('&bull;', '•')
                    row_dict[header.lower().replace(' ', '_')] = _clean_text(cell_text)
            rows.append(row_dict)

    return rows


def _extract_section(markdown: str, section_pattern: str) -> Optional[str]:
    """
    Extract content under a specific header

    Args:
        markdown: Full markdown text
        section_pattern: Regex pattern for section header

    Returns:
        Content under that section, or None
    """
    # Find section start
    match = re.search(section_pattern, markdown, re.IGNORECASE | re.MULTILINE)
    if not match:
        return None

    start_pos = match.end()

    # Find next section of same or higher level
    level = len(match.group(1))  # Count # characters
    next_section_pattern = r'\n(#{1,' + str(level) + r'})\s+[^\n]+'

    next_match = re.search(next_section_pattern, markdown[start_pos:])

    if next_match:
        end_pos = start_pos + next_match.start()
    else:
        end_pos = len(markdown)

    content = markdown[start_pos:end_pos].strip()
    return content if content else None


def _parse_key_value_blocks(text: str) -> Dict[str, Any]:
    """
    Parse **Key:** value pairs

    Example:
    **Político:** Description here
    **Econômico:** Another description

    Returns: {'politico': 'Description here', 'economico': 'Another description'}
    """
    data = {}

    # Match **Key:** value patterns
    pattern = r'\*\*([^*:]+):\*\*\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)'
    matches = re.findall(pattern, text, re.MULTILINE)

    for key, value in matches:
        key_clean = _clean_text(key).lower().replace(' ', '_')
        value_clean = _clean_text(value)
        if key_clean and value_clean:
            data[key_clean] = value_clean

    return data


def _parse_recommendations(text: str) -> List[Dict[str, Any]]:
    """Parse priority recommendations section"""
    recommendations = []

    # Split by ### headers or --- separators
    sections = re.split(r'(?:^|\n)(?:###\s+#?\d+\s*-|---)', text, flags=re.MULTILINE)

    for section in sections:
        if not section.strip():
            continue

        rec = {}

        # Extract title from first line
        lines = section.split('\n')
        if lines:
            first_line = _clean_text(lines[0])
            if first_line:
                # Extract priority number if present
                priority_match = re.search(r'^(\d+)\s*[-–—]', first_line)
                if priority_match:
                    rec['prioridade'] = int(priority_match.group(1))
                    rec['titulo'] = _clean_text(first_line[priority_match.end():])
                else:
                    rec['titulo'] = first_line

        # Extract content
        content_lines = []
        for line in lines[1:]:
            line = _clean_text(line)
            if not line or line.startswith('**') or line.startswith('---'):
                continue
            content_lines.append(line)

        if content_lines:
            rec['recomendacao'] = '\n'.join(content_lines)

        # Extract key-value metadata
        kv_data = _parse_key_value_blocks(section)

        if kv_data.get('por_que') or kv_data.get('por_quê'):
            rec['justificativa'] = kv_data.get('por_que') or kv_data.get('por_quê')

        if kv_data.get('prazo'):
            rec['prazo'] = kv_data['prazo']

        if kv_data.get('investimento'):
            rec['investimento_estimado'] = kv_data['investimento']

        if kv_data.get('retorno'):
            rec['retorno_esperado'] = kv_data['retorno']

        if rec.get('titulo') or rec.get('recomendacao'):
            recommendations.append(rec)

    return recommendations


def parse_markdown_to_report(markdown: str) -> Tuple[Dict[str, Any], List[str]]:
    """
    Parse markdown to report JSON structure

    Args:
        markdown: Markdown formatted report

    Returns:
        Tuple of (report_json, warnings_list)

    Raises:
        MarkdownParseError: If markdown is fundamentally malformed
    """
    warnings = []

    # Parse frontmatter
    metadata, content = _parse_frontmatter(markdown)

    # Detect structure type
    structure = metadata.get('structure', 'legacy')
    is_new = (structure == 'new')

    # Initialize report
    report = {}

    # Extract executive summary
    sumario_content = _extract_section(content, r'^(##)\s+Sumário Executivo')
    if sumario_content:
        # Remove any sub-headers and get just the text
        sumario_text = re.sub(r'###.*$', '', sumario_content, flags=re.MULTILINE).strip()
        report['sumario_executivo'] = _clean_text(sumario_text)
    else:
        warnings.append("Sumário Executivo não encontrado")

    # Parse based on structure type
    if is_new:
        # NEW STRUCTURE: 4-part format
        _parse_new_structure(content, report, warnings)
    else:
        # OLD STRUCTURE: Flat format
        _parse_legacy_structure(content, report, warnings)

    # Validate we have some content
    if len(report) <= 1:  # Only sumario_executivo or empty
        raise MarkdownParseError("Markdown não contém seções reconhecíveis")

    return report, warnings


def _parse_new_structure(content: str, report: Dict[str, Any], warnings: List[str]):
    """Parse new 4-part structure"""

    # PARTE 1: ONDE ESTAMOS?
    parte_1_content = _extract_section(content, r'^(##)\s+Parte 1:.*Onde Estamos')
    if parte_1_content:
        parte_1 = {}

        # PESTEL
        pestel_content = _extract_section(parte_1_content, r'^(###)\s+Análise PESTEL')
        if pestel_content:
            parte_1['analise_pestel'] = _parse_key_value_blocks(pestel_content)

        # Porter 7 Forces
        porter_content = _extract_section(parte_1_content, r'^(###)\s+Sete Forças')
        if porter_content:
            porter = {}

            trad_content = _extract_section(porter_content, r'\*\*Forças Tradicionais')
            if trad_content:
                porter['forcas_tradicionais'] = _parse_key_value_blocks(trad_content)

            modern_content = _extract_section(porter_content, r'\*\*Forças Modernas')
            if modern_content:
                porter['forcas_modernas'] = _parse_key_value_blocks(modern_content)

            if porter:
                parte_1['sete_forcas_porter'] = porter

        # SWOT
        swot = _parse_swot_section(parte_1_content)
        if swot:
            parte_1['analise_swot'] = swot

        if parte_1:
            report['parte_1_onde_estamos'] = parte_1

    # PARTE 2: ONDE QUEREMOS IR?
    parte_2_content = _extract_section(content, r'^(##)\s+Parte 2:.*Onde Queremos Ir')
    if parte_2_content:
        parte_2 = {}

        # Blue Ocean
        oceano_content = _extract_section(parte_2_content, r'^(###)\s+.*Oceano Azul')
        if oceano_content:
            oceano = {}
            for action in ['eliminar', 'reduzir', 'elevar', 'criar']:
                action_pattern = rf'\*\*{action.title()}:?\*\*\s*\n((?:[\s]*[-*].*\n?)+)'
                match = re.search(action_pattern, oceano_content, re.IGNORECASE)
                if match:
                    oceano[action] = _parse_list_items(match.group(1))

            if oceano:
                parte_2['estrategia_oceano_azul'] = oceano

        # TAM/SAM/SOM
        tam = _parse_tam_sam_som_section(parte_2_content)
        if tam:
            parte_2['tam_sam_som'] = tam

        # Balanced Scorecard
        bsc_content = _extract_section(parte_2_content, r'^(###)\s+Balanced Scorecard')
        if bsc_content:
            parte_2['balanced_scorecard'] = _parse_key_value_blocks(bsc_content)

        if parte_2:
            report['parte_2_onde_queremos_ir'] = parte_2

    # PARTE 3: COMO CHEGAR LÁ?
    parte_3_content = _extract_section(content, r'^(##)\s+Parte 3:.*Como Chegar')
    if parte_3_content:
        parte_3 = {}

        # OKRs
        okrs_content = _extract_section(parte_3_content, r'^(###)\s+OKRs')
        if okrs_content:
            okrs = _parse_okr_table(okrs_content)
            if okrs:
                parte_3['okrs_propostos'] = okrs

        # Growth Hacking
        growth_content = _extract_section(parte_3_content, r'^(###)\s+Growth Hacking')
        if growth_content:
            growth = {}

            leap_pattern = r'\*\*LEAP Loop.*?:?\*\*\s*\n((?:.*?\n)+?)(?=\*\*SCALE|\Z)'
            leap_match = re.search(leap_pattern, growth_content, re.DOTALL)
            if leap_match:
                growth['leap_loop_acquisition'] = _parse_key_value_blocks(leap_match.group(1))

            scale_pattern = r'\*\*SCALE Loop.*?:?\*\*\s*\n((?:.*?\n)+?)(?=\*\*[A-Z]|\Z)'
            scale_match = re.search(scale_pattern, growth_content, re.DOTALL)
            if scale_match:
                growth['scale_loop_monetizacao'] = _parse_key_value_blocks(scale_match.group(1))

            if growth:
                parte_3['growth_hacking_loops'] = growth

        if parte_3:
            report['parte_3_como_chegar_la'] = parte_3

    # PARTE 4: O QUE FAZER AGORA?
    parte_4_content = _extract_section(content, r'^(##)\s+Parte 4:.*Que Fazer Agora')
    if parte_4_content:
        parte_4 = {}

        # Scenario Planning
        scenarios = _parse_scenario_planning(parte_4_content)
        if scenarios:
            parte_4['planejamento_cenarios'] = scenarios

        # Recommendations
        rec_content = _extract_section(parte_4_content, r'^(###)\s+Recomendações Prioritárias')
        if rec_content:
            recs = _parse_recommendations(rec_content)
            if recs:
                parte_4['recomendacoes_prioritarias'] = recs

        # Multi-criteria matrix
        matrix_content = _extract_section(parte_4_content, r'^(###)\s+Matriz.*Decisão')
        if matrix_content:
            parte_4['matriz_decisao_multicriterio'] = _parse_key_value_blocks(matrix_content)

        if parte_4:
            report['parte_4_o_que_fazer_agora'] = parte_4


def _parse_legacy_structure(content: str, report: Dict[str, Any], warnings: List[str]):
    """Parse legacy flat structure"""

    # SWOT
    swot = _parse_swot_section(content)
    if swot:
        report['analise_swot'] = swot
    else:
        warnings.append("Análise SWOT não encontrada")

    # TAM/SAM/SOM
    tam = _parse_tam_sam_som_section(content)
    if tam:
        report['tam_sam_som'] = tam

    # Recommendations
    rec_content = _extract_section(content, r'^(##)\s+Recomendações Prioritárias')
    if rec_content:
        recs = _parse_recommendations(rec_content)
        if recs:
            report['recomendacoes_prioritarias'] = recs

    # Scenario Planning
    scenarios = _parse_scenario_planning(content)
    if scenarios:
        report['planejamento_cenarios'] = scenarios

    # OKRs
    okrs_content = _extract_section(content, r'^(##)\s+OKRs')
    if okrs_content:
        okrs = _parse_okr_table(okrs_content)
        if okrs:
            report['okrs_propostos'] = okrs


def _parse_swot_section(content: str) -> Optional[Dict[str, List[str]]]:
    """Parse SWOT analysis section"""
    swot_content = _extract_section(content, r'^(##)\s+Análise SWOT')
    if not swot_content:
        return None

    swot = {}

    # Parse each quadrant (with or without emoji)
    for key, patterns in [
        ('forcas', [r'###\s*💪?\s*Forças', r'###\s*Forças']),
        ('fraquezas', [r'###\s*⚠️?\s*Fraquezas', r'###\s*Fraquezas']),
        ('oportunidades', [r'###\s*🚀?\s*Oportunidades', r'###\s*Oportunidades']),
        ('ameacas', [r'###\s*🎯?\s*Ameaças', r'###\s*Ameaças']),
    ]:
        for pattern in patterns:
            section = _extract_section(swot_content, pattern)
            if section:
                items = _parse_list_items(section)
                if items:
                    swot[key] = items
                break

    return swot if swot else None


def _parse_tam_sam_som_section(content: str) -> Optional[Dict[str, str]]:
    """Parse TAM/SAM/SOM section"""
    tam_content = _extract_section(content, r'^(##)\s+Análise de Mercado')
    if not tam_content:
        return None

    tam_data = {}

    # Parse table
    table_data = _parse_table(tam_content)
    for row in table_data:
        if 'tam' in row.get('métrica', '').lower():
            tam_data['tam_total_market'] = row.get('valor', '')
        elif 'sam' in row.get('métrica', '').lower():
            tam_data['sam_available_market'] = row.get('valor', '')
        elif 'som' in row.get('métrica', '').lower():
            tam_data['som_obtainable_market'] = row.get('valor', '')

    # Parse justification
    just_pattern = r'\*\*Justificativa:?\*\*\s*([^\n]+(?:\n(?!\*\*)[^\n]+)*)'
    match = re.search(just_pattern, tam_content)
    if match:
        tam_data['justificativa'] = _clean_text(match.group(1))

    return tam_data if tam_data else None


def _parse_okr_table(content: str) -> List[Dict[str, Any]]:
    """Parse OKR table"""
    table_data = _parse_table(content)

    okrs = []
    for row in table_data:
        okr = {}

        if row.get('trimestre'):
            okr['trimestre'] = row['trimestre']

        if row.get('objetivo'):
            okr['objetivo'] = row['objetivo']

        # Parse key results (may have <br> or bullets)
        if row.get('resultados-chave') or row.get('resultados_chave'):
            kr_text = row.get('resultados-chave') or row.get('resultados_chave', '')
            key_results = _parse_list_items(kr_text)
            if key_results:
                okr['resultados_chave'] = key_results

        if row.get('investimento'):
            okr['investimento_estimado'] = row['investimento']

        if okr:
            okrs.append(okr)

    return okrs


def _parse_scenario_planning(content: str) -> Optional[Dict[str, Any]]:
    """Parse scenario planning section"""
    scenario_content = _extract_section(content, r'^(##)\s+Planejamento de Cenários')
    if not scenario_content:
        return None

    scenarios = {}

    # Parse uncertainty variables (new structure)
    var_pattern = r'\*\*Variáveis-Chave.*?:?\*\*\s*\n((?:[\s]*[-*].*\n?)+)'
    var_match = re.search(var_pattern, scenario_content, re.IGNORECASE)
    if var_match:
        scenarios['variaveis_chave_incerteza'] = _parse_list_items(var_match.group(1))

    # Parse each scenario
    for key, patterns in [
        ('cenario_otimista', [r'###\s*📈?\s*Cenário Otimista', r'###\s*Cenário Otimista']),
        ('cenario_realista', [r'###\s*📊?\s*Cenário Realista', r'###\s*Cenário Realista']),
        ('cenario_pessimista', [r'###\s*📉?\s*Cenário Pessimista', r'###\s*Cenário Pessimista']),
    ]:
        for pattern in patterns:
            section = _extract_section(scenario_content, pattern)
            if section:
                scenario_data = _parse_key_value_blocks(section)
                if scenario_data:
                    scenarios[key] = scenario_data
                break

    return scenarios if scenarios else None
