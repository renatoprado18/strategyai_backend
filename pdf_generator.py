"""
Production-Grade PDF Report Generator using fpdf2
Pure Python implementation - no system dependencies

BACKWARD COMPATIBLE: Handles both old (flat) and new (4-part nested) report structures
"""

from fpdf import FPDF
from datetime import datetime
from typing import Dict, Any, List
from report_adapter import adapt_to_legacy, is_new_structure, get_report_metadata


class ReportPDF(FPDF):
    """Custom PDF class with headers and footers"""

    def __init__(self, company_name: str):
        super().__init__()
        self.company_name = company_name
        self.set_auto_page_break(auto=True, margin=15)

    def header(self):
        """Add header to every page"""
        self.set_font('Arial', 'I', 9)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Relatório Estratégico - {self.company_name}', 0, 0, 'C')
        self.ln(15)

    def footer(self):
        """Add footer to every page"""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, title: str, color=(30, 64, 175)):
        """Add a chapter title"""
        self.set_font('Arial', 'B', 16)
        self.set_text_color(*color)
        self.ln(5)
        self.cell(0, 10, title, 0, 1, 'L')
        self.ln(3)
        self.set_text_color(0, 0, 0)

    def section_title(self, title: str):
        """Add a section title"""
        self.set_font('Arial', 'B', 12)
        self.set_text_color(59, 130, 246)
        self.ln(3)
        self.cell(0, 8, title, 0, 1, 'L')
        self.ln(2)
        self.set_text_color(0, 0, 0)

    def body_text(self, text: str):
        """Add body text with word wrapping"""
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 6, text)
        self.ln(2)

    def bullet_list(self, items: List[str]):
        """Add a bullet list"""
        self.set_font('Arial', '', 10)
        for item in items:
            self.cell(5, 6, '', 0, 0)  # Indent
            self.multi_cell(0, 6, f'• {item}')
        self.ln(2)

    def info_box(self, title: str, content: str, bg_color=(248, 250, 252)):
        """Add an info box"""
        self.set_fill_color(*bg_color)
        self.set_font('Arial', 'B', 11)
        self.cell(0, 8, title, 0, 1, 'L', True)
        self.set_font('Arial', '', 10)
        self.multi_cell(0, 6, content, 0, 'L', True)
        self.ln(3)

    def colored_box(self, title: str, items: List[str], bg_color, title_color):
        """Add a colored box with list"""
        # Box background
        x_start = self.get_x()
        y_start = self.get_y()

        # Calculate height
        self.set_font('Arial', '', 10)
        temp_y = y_start + 8
        for item in items:
            temp_y += 6

        # Draw filled rectangle
        self.set_fill_color(*bg_color)
        self.rect(x_start, y_start, 90, temp_y - y_start + 5, 'F')

        # Title
        self.set_xy(x_start + 2, y_start + 2)
        self.set_font('Arial', 'B', 11)
        self.set_text_color(*title_color)
        self.cell(86, 6, title, 0, 1)

        # Items
        self.set_text_color(0, 0, 0)
        self.set_font('Arial', '', 9)
        for item in items:
            self.set_x(x_start + 4)
            self.multi_cell(86, 5, f'• {item}')

        self.set_y(temp_y + 8)
        self.set_text_color(0, 0, 0)


def generate_pdf_from_report(
    submission_data: Dict[str, Any],
    report_json: Dict[str, Any]
) -> bytes:
    """
    Generate a production-grade PDF from report JSON using fpdf2

    BACKWARD COMPATIBLE: Handles both old (flat) and new (4-part nested) structures

    Returns:
        PDF file content as bytes
    """

    # Adapt report structure if necessary (handles both old and new formats)
    metadata = get_report_metadata(report_json)
    print(f"[PDF Generator] Report structure: {metadata['structure']} ({metadata['version']})")

    # Convert to legacy format for rendering
    report_json = adapt_to_legacy(report_json)

    company = submission_data.get('company', 'Empresa')
    industry = submission_data.get('industry', '')
    website = submission_data.get('website', '')
    challenge = submission_data.get('challenge', '')
    contact_name = submission_data.get('name', '')

    # Initialize PDF
    pdf = ReportPDF(company)
    pdf.add_page()

    # Title Page
    pdf.set_font('Arial', 'B', 24)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(0, 20, 'Relatório Estratégico', 0, 1, 'C')
    pdf.ln(5)

    # Company info
    pdf.set_font('Arial', '', 11)
    pdf.set_text_color(100, 100, 100)
    try:
        updated_at = datetime.fromisoformat(submission_data.get('updated_at', '').replace('Z', '+00:00'))
        date_str = updated_at.strftime('%d de %B de %Y')
    except:
        date_str = datetime.now().strftime('%d de %B de %Y')

    pdf.cell(0, 8, f'Gerado em {date_str}', 0, 1, 'C')
    pdf.ln(10)

    # Company details box
    pdf.set_fill_color(248, 250, 252)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font('Arial', 'B', 12)
    pdf.cell(0, 8, 'Informações da Empresa', 0, 1, 'L', True)
    pdf.set_font('Arial', '', 10)

    info_items = [
        ('Empresa:', company),
        ('Setor:', industry),
    ]
    if website:
        info_items.append(('Website:', website))
    if contact_name:
        info_items.append(('Contato:', contact_name))

    for label, value in info_items:
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(40, 6, label, 0, 0)
        pdf.set_font('Arial', '', 10)
        pdf.cell(0, 6, value, 0, 1)

    if challenge:
        pdf.ln(3)
        pdf.set_font('Arial', 'B', 10)
        pdf.cell(0, 6, 'Desafio Identificado:', 0, 1)
        pdf.set_font('Arial', '', 10)
        pdf.multi_cell(0, 6, challenge)

    pdf.add_page()

    # Executive Summary
    if report_json.get('sumario_executivo'):
        pdf.chapter_title('Sumário Executivo')
        pdf.set_fill_color(239, 246, 255)
        pdf.multi_cell(0, 6, report_json['sumario_executivo'], 0, 'L', True)
        pdf.ln(5)

    # SWOT Analysis
    swot = report_json.get('analise_swot') or report_json.get('diagnostico_estrategico', {})
    if swot:
        pdf.add_page()
        pdf.chapter_title('Análise SWOT')

        # Strengths (left column)
        forcas = swot.get('forcas') or swot.get('forças', [])
        if forcas:
            x_pos = pdf.get_x()
            y_pos = pdf.get_y()
            pdf.colored_box('Forças', forcas[:6], (240, 253, 244), (22, 163, 74))

            # Weaknesses (right column)
            fraquezas = swot.get('fraquezas', [])
            if fraquezas:
                pdf.set_xy(x_pos + 100, y_pos)
                pdf.colored_box('Fraquezas', fraquezas[:6], (254, 242, 242), (220, 38, 38))

            pdf.ln(5)

        # Opportunities (left column)
        oportunidades = swot.get('oportunidades', [])
        if oportunidades:
            x_pos = pdf.get_x()
            y_pos = pdf.get_y()
            pdf.colored_box('Oportunidades', oportunidades[:6], (239, 246, 255), (37, 99, 235))

            # Threats (right column)
            ameacas = swot.get('ameacas') or swot.get('ameaças', [])
            if ameacas:
                pdf.set_xy(x_pos + 100, y_pos)
                pdf.colored_box('Ameaças', ameacas[:6], (254, 252, 232), (202, 138, 4))

            pdf.ln(5)

    # TAM/SAM/SOM
    if report_json.get('tam_sam_som'):
        pdf.add_page()
        pdf.chapter_title('Análise de Mercado (TAM-SAM-SOM)')

        tam_sam_som = report_json['tam_sam_som']

        # Create table
        pdf.set_fill_color(219, 234, 254)
        pdf.set_font('Arial', 'B', 11)
        pdf.cell(60, 8, 'Métrica', 1, 0, 'L', True)
        pdf.cell(0, 8, 'Valor', 1, 1, 'L', True)

        pdf.set_font('Arial', '', 10)
        pdf.set_fill_color(255, 255, 255)

        metrics = [
            ('TAM (Total Addressable Market)', tam_sam_som.get('tam_total_market', 'N/A')),
            ('SAM (Serviceable Available Market)', tam_sam_som.get('sam_available_market', 'N/A')),
            ('SOM (Serviceable Obtainable Market)', tam_sam_som.get('som_obtainable_market', 'N/A')),
        ]

        for label, value in metrics:
            pdf.cell(60, 7, label, 1, 0, 'L')
            pdf.cell(0, 7, value, 1, 1, 'L')

        if tam_sam_som.get('justificativa'):
            pdf.ln(3)
            pdf.set_font('Arial', 'B', 10)
            pdf.cell(0, 6, 'Justificativa:', 0, 1)
            pdf.set_font('Arial', '', 10)
            pdf.multi_cell(0, 6, tam_sam_som['justificativa'])

    # Priority Recommendations
    if report_json.get('recomendacoes_prioritarias'):
        pdf.add_page()
        pdf.chapter_title('Recomendações Prioritárias')

        for idx, rec in enumerate(report_json['recomendacoes_prioritarias'][:5], 1):
            if isinstance(rec, dict):
                # Recommendation box
                pdf.set_fill_color(248, 250, 252)
                pdf.set_font('Arial', 'B', 11)
                pdf.set_text_color(30, 64, 175)

                title = rec.get('titulo', f'Recomendação {idx}')
                pdf.multi_cell(0, 7, f"#{rec.get('prioridade', idx)} - {title}", 0, 'L', True)

                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 10)

                if rec.get('recomendacao'):
                    pdf.multi_cell(0, 6, rec['recomendacao'], 0, 'L', True)

                if rec.get('justificativa'):
                    pdf.set_font('Arial', 'I', 9)
                    pdf.multi_cell(0, 5, f"Por quê: {rec['justificativa']}", 0, 'L', True)
                    pdf.set_font('Arial', '', 10)

                # Metadata
                metadata_parts = []
                if rec.get('prazo'):
                    metadata_parts.append(f"Prazo: {rec['prazo']}")
                if rec.get('investimento_estimado'):
                    metadata_parts.append(f"Investimento: {rec['investimento_estimado']}")
                if rec.get('retorno_esperado'):
                    metadata_parts.append(f"Retorno: {rec['retorno_esperado']}")

                if metadata_parts:
                    pdf.set_font('Arial', 'B', 9)
                    pdf.set_text_color(100, 100, 100)
                    pdf.multi_cell(0, 5, ' | '.join(metadata_parts), 0, 'L', True)
                    pdf.set_text_color(0, 0, 0)

                pdf.ln(5)

    # Scenario Planning
    if report_json.get('planejamento_cenarios'):
        pdf.add_page()
        pdf.chapter_title('Planejamento de Cenários')

        cenarios = report_json['planejamento_cenarios']

        scenarios = [
            ('cenario_otimista', 'Cenário Otimista', (240, 253, 244), (22, 163, 74)),
            ('cenario_realista', 'Cenário Realista', (239, 246, 255), (37, 99, 235)),
            ('cenario_pessimista', 'Cenário Pessimista', (254, 242, 242), (220, 38, 38)),
        ]

        for key, title, bg_color, text_color in scenarios:
            if cenarios.get(key):
                cen = cenarios[key]

                pdf.set_fill_color(*bg_color)
                pdf.set_font('Arial', 'B', 11)
                pdf.set_text_color(*text_color)

                prob = cen.get('probabilidade', '---')
                pdf.cell(0, 7, f"{title} ({prob})", 0, 1, 'L', True)

                pdf.set_text_color(0, 0, 0)
                pdf.set_font('Arial', '', 10)

                if cen.get('impacto_receita'):
                    pdf.multi_cell(0, 6, f"Impacto: {cen['impacto_receita']}", 0, 'L', True)
                if cen.get('acoes_requeridas'):
                    pdf.multi_cell(0, 6, f"Ações: {cen['acoes_requeridas']}", 0, 'L', True)

                pdf.ln(3)

    # OKRs
    if report_json.get('okrs_propostos'):
        pdf.add_page()
        pdf.chapter_title('OKRs Propostos')

        for okr in report_json['okrs_propostos'][:6]:
            pdf.section_title(f"{okr.get('trimestre', 'Q1')} 2025: {okr.get('objetivo', '')}")

            if okr.get('resultados_chave'):
                pdf.set_font('Arial', 'B', 10)
                pdf.cell(0, 6, 'Resultados-Chave:', 0, 1)
                pdf.bullet_list(okr['resultados_chave'][:5])

            if okr.get('investimento_estimado'):
                pdf.set_font('Arial', 'I', 9)
                pdf.set_text_color(100, 100, 100)
                pdf.cell(0, 5, f"Investimento: {okr['investimento_estimado']}", 0, 1)
                pdf.set_text_color(0, 0, 0)

            pdf.ln(3)

    # Footer
    pdf.ln(10)
    pdf.set_font('Arial', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, 'Relatório gerado por Strategy AI • Powered by IA', 0, 1, 'C')

    # Return PDF as bytes
    return bytes(pdf.output())
