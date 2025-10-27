"""
Production-Grade PDF Report Generator
Uses xhtml2pdf for proper HTML-to-PDF conversion with text rendering
"""

import io
import json
from datetime import datetime
from typing import Dict, Any, Optional
from xhtml2pdf import pisa


def generate_pdf_from_report(
    submission_data: Dict[str, Any],
    report_json: Dict[str, Any]
) -> bytes:
    """
    Generate a production-grade PDF from report JSON

    Returns:
        PDF file content as bytes
    """

    html_content = generate_html_template(submission_data, report_json)

    # Create PDF
    pdf_buffer = io.BytesIO()
    pisa_status = pisa.CreatePDF(
        io.BytesIO(html_content.encode('utf-8')),
        dest=pdf_buffer,
        encoding='utf-8'
    )

    if pisa_status.err:
        raise Exception(f"PDF generation failed with error code {pisa_status.err}")

    pdf_buffer.seek(0)
    return pdf_buffer.getvalue()


def generate_html_template(submission: Dict[str, Any], report: Dict[str, Any]) -> str:
    """
    Generate HTML template with proper CSS for PDF rendering
    """

    company = submission.get('company', '')
    industry = submission.get('industry', '')
    website = submission.get('website', '')
    challenge = submission.get('challenge', '')
    contact_name = submission.get('name', '')

    # Format date
    try:
        updated_at = datetime.fromisoformat(submission.get('updated_at', '').replace('Z', '+00:00'))
        date_str = updated_at.strftime('%d de %B de %Y às %H:%M')
    except:
        date_str = datetime.now().strftime('%d de %B de %Y às %H:%M')

    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Relatório Estratégico - {company}</title>
    <style>
        @page {{
            size: A4;
            margin: 2cm 1.5cm;

            @top-center {{
                content: "Relatório Estratégico - {company}";
                font-size: 9pt;
                color: #666;
                padding-bottom: 0.5cm;
                border-bottom: 1pt solid #e5e7eb;
            }}

            @bottom-right {{
                content: "Página " counter(page) " de " counter(pages);
                font-size: 9pt;
                color: #666;
            }}
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: 'DejaVu Sans', Arial, sans-serif;
            font-size: 10pt;
            line-height: 1.6;
            color: #1f2937;
        }}

        .container {{
            max-width: 100%;
        }}

        /* Typography */
        h1 {{
            font-size: 24pt;
            font-weight: bold;
            color: #1e40af;
            margin-bottom: 0.5cm;
            padding-bottom: 0.3cm;
            border-bottom: 2pt solid #1e40af;
            page-break-after: avoid;
        }}

        h2 {{
            font-size: 16pt;
            font-weight: bold;
            color: #1e40af;
            margin-top: 0.8cm;
            margin-bottom: 0.4cm;
            page-break-after: avoid;
        }}

        h3 {{
            font-size: 13pt;
            font-weight: bold;
            color: #3b82f6;
            margin-top: 0.5cm;
            margin-bottom: 0.3cm;
            page-break-after: avoid;
        }}

        h4 {{
            font-size: 11pt;
            font-weight: bold;
            color: #6b7280;
            margin-top: 0.3cm;
            margin-bottom: 0.2cm;
        }}

        p {{
            margin-bottom: 0.3cm;
            text-align: justify;
            orphans: 3;
            widows: 3;
        }}

        /* Prevent widows and orphans */
        p, li {{
            orphans: 3;
            widows: 3;
        }}

        /* Lists */
        ul, ol {{
            margin-left: 0.8cm;
            margin-bottom: 0.4cm;
        }}

        li {{
            margin-bottom: 0.15cm;
        }}

        /* Tables */
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 0.5cm;
            page-break-inside: avoid;
        }}

        th, td {{
            padding: 0.3cm;
            text-align: left;
            border-bottom: 1pt solid #e5e7eb;
        }}

        th {{
            background-color: #f3f4f6;
            font-weight: bold;
            color: #1f2937;
        }}

        /* Cards/Boxes */
        .info-box {{
            background-color: #f8fafc;
            border-left: 4pt solid #1e40af;
            padding: 0.4cm;
            margin-bottom: 0.5cm;
            page-break-inside: avoid;
        }}

        .summary-box {{
            background: linear-gradient(to right, #eff6ff, #dbeafe);
            border: 1pt solid #93c5fd;
            padding: 0.5cm;
            margin-bottom: 0.6cm;
            border-radius: 4pt;
            page-break-inside: avoid;
        }}

        .grid-2col {{
            display: table;
            width: 100%;
            margin-bottom: 0.5cm;
        }}

        .grid-2col > div {{
            display: table-cell;
            width: 50%;
            padding: 0.3cm;
            vertical-align: top;
        }}

        .swot-box {{
            border: 1pt solid #e5e7eb;
            padding: 0.4cm;
            margin-bottom: 0.3cm;
            page-break-inside: avoid;
        }}

        .swot-strengths {{ background-color: #f0fdf4; border-left: 4pt solid #16a34a; }}
        .swot-weaknesses {{ background-color: #fef2f2; border-left: 4pt solid #dc2626; }}
        .swot-opportunities {{ background-color: #eff6ff; border-left: 4pt solid #2563eb; }}
        .swot-threats {{ background-color: #fefce8; border-left: 4pt solid #ca8a04; }}

        .scenario-box {{
            border-left: 4pt solid;
            padding: 0.4cm;
            margin-bottom: 0.4cm;
            page-break-inside: avoid;
        }}

        .scenario-optimistic {{ background-color: #f0fdf4; border-color: #16a34a; }}
        .scenario-realistic {{ background-color: #eff6ff; border-color: #2563eb; }}
        .scenario-pessimistic {{ background-color: #fef2f2; border-color: #dc2626; }}

        .recommendation {{
            border: 1pt solid #e5e7eb;
            border-left: 4pt solid #1e40af;
            padding: 0.4cm;
            margin-bottom: 0.4cm;
            background-color: #f8fafc;
            page-break-inside: avoid;
        }}

        .recommendation-header {{
            font-weight: bold;
            font-size: 11pt;
            margin-bottom: 0.2cm;
            color: #1e40af;
        }}

        .badge {{
            display: inline-block;
            padding: 0.1cm 0.3cm;
            background-color: #1e40af;
            color: white;
            font-size: 8pt;
            font-weight: bold;
            border-radius: 3pt;
            margin-right: 0.2cm;
        }}

        .metadata {{
            font-size: 8pt;
            color: #6b7280;
            margin-top: 0.2cm;
        }}

        /* Page breaks */
        .page-break {{
            page-break-before: always;
        }}

        .no-break {{
            page-break-inside: avoid;
        }}

        /* Header section */
        .report-header {{
            margin-bottom: 0.8cm;
            padding-bottom: 0.5cm;
            border-bottom: 2pt solid #1e40af;
        }}

        .company-info {{
            background-color: #f8fafc;
            padding: 0.5cm;
            margin-bottom: 0.5cm;
            border-radius: 4pt;
        }}

        .company-info table {{
            margin-bottom: 0;
        }}

        .company-info th, .company-info td {{
            border-bottom: none;
            padding: 0.2cm;
        }}

        /* Footer */
        .report-footer {{
            margin-top: 1cm;
            padding-top: 0.5cm;
            border-top: 1pt solid #e5e7eb;
            text-align: center;
            font-size: 9pt;
            color: #6b7280;
        }}
    </style>
</head>
<body>
    <div class="container">
"""

    # Header
    html += f"""
        <div class="report-header">
            <h1>Relatório Estratégico</h1>
            <p style="font-size: 11pt; color: #6b7280;">
                Gerado em {date_str}
            </p>
        </div>

        <div class="company-info no-break">
            <h3>Informações da Empresa</h3>
            <table>
                <tr>
                    <th style="width: 30%;">Empresa:</th>
                    <td><strong>{company}</strong></td>
                </tr>
                <tr>
                    <th>Setor:</th>
                    <td><strong>{industry}</strong></td>
                </tr>
"""

    if website:
        html += f"""
                <tr>
                    <th>Website:</th>
                    <td><a href="{website}" style="color: #1e40af;">{website}</a></td>
                </tr>
"""

    if contact_name:
        html += f"""
                <tr>
                    <th>Contato:</th>
                    <td>{contact_name}</td>
                </tr>
"""

    html += """
            </table>
"""

    if challenge:
        html += f"""
            <div style="margin-top: 0.4cm;">
                <strong>Desafio Identificado:</strong><br/>
                {challenge}
            </div>
"""

    html += """
        </div>
"""

    # Executive Summary
    if report.get('sumario_executivo'):
        html += f"""
        <div class="page-break"></div>
        <div class="summary-box no-break">
            <h2>Sumário Executivo</h2>
            <p>{report['sumario_executivo']}</p>
        </div>
"""

    # SWOT Analysis
    if report.get('analise_swot') or report.get('diagnostico_estrategico'):
        swot = report.get('analise_swot') or report.get('diagnostico_estrategico', {})
        html += """
        <div class="no-break">
            <h2>Análise SWOT</h2>
            <div class="grid-2col">
"""

        if swot.get('forcas') or swot.get('forças'):
            forcas = swot.get('forcas') or swot.get('forças', [])
            html += """
                <div>
                    <div class="swot-box swot-strengths">
                        <h4 style="color: #16a34a;">Forças</h4>
                        <ul>
"""
            for item in forcas:
                html += f"<li>{item}</li>\n"
            html += """
                        </ul>
                    </div>
                </div>
"""

        if swot.get('fraquezas'):
            html += """
                <div>
                    <div class="swot-box swot-weaknesses">
                        <h4 style="color: #dc2626;">Fraquezas</h4>
                        <ul>
"""
            for item in swot['fraquezas']:
                html += f"<li>{item}</li>\n"
            html += """
                        </ul>
                    </div>
                </div>
"""

        html += """
            </div>
            <div class="grid-2col">
"""

        if swot.get('oportunidades'):
            html += """
                <div>
                    <div class="swot-box swot-opportunities">
                        <h4 style="color: #2563eb;">Oportunidades</h4>
                        <ul>
"""
            for item in swot['oportunidades']:
                html += f"<li>{item}</li>\n"
            html += """
                        </ul>
                    </div>
                </div>
"""

        if swot.get('ameacas') or swot.get('ameaças'):
            ameacas = swot.get('ameacas') or swot.get('ameaças', [])
            html += """
                <div>
                    <div class="swot-box swot-threats">
                        <h4 style="color: #ca8a04;">Ameaças</h4>
                        <ul>
"""
            for item in ameacas:
                html += f"<li>{item}</li>\n"
            html += """
                        </ul>
                    </div>
                </div>
"""

        html += """
            </div>
        </div>
"""

    # TAM/SAM/SOM
    if report.get('tam_sam_som'):
        tam_sam_som = report['tam_sam_som']
        html += """
        <div class="no-break">
            <h2>Análise de Mercado (TAM-SAM-SOM)</h2>
            <table>
                <tr>
                    <th style="width: 30%; background-color: #dbeafe;">TAM (Total Addressable Market)</th>
                    <td><strong>{}</strong></td>
                </tr>
                <tr>
                    <th style="background-color: #d1fae5;">SAM (Serviceable Available Market)</th>
                    <td><strong>{}</strong></td>
                </tr>
                <tr>
                    <th style="background-color: #e9d5ff;">SOM (Serviceable Obtainable Market)</th>
                    <td><strong>{}</strong></td>
                </tr>
            </table>
            <p style="margin-top: 0.3cm;"><strong>Justificativa:</strong> {}</p>
        </div>
""".format(
            tam_sam_som.get('tam_total_market', 'N/A'),
            tam_sam_som.get('sam_available_market', 'N/A'),
            tam_sam_som.get('som_obtainable_market', 'N/A'),
            tam_sam_som.get('justificativa', '')
        )

    # Priority Recommendations
    if report.get('recomendacoes_prioritarias'):
        html += """
        <div class="page-break"></div>
        <h2>Recomendações Prioritárias</h2>
"""
        for idx, rec in enumerate(report['recomendacoes_prioritarias'], 1):
            if isinstance(rec, dict):
                html += f"""
        <div class="recommendation">
            <div class="recommendation-header">
                <span class="badge">#{rec.get('prioridade', idx)}</span>
                {rec.get('titulo', f'Recomendação {idx}')}
            </div>
"""
                if rec.get('recomendacao'):
                    html += f"<p>{rec['recomendacao']}</p>"

                if rec.get('justificativa'):
                    html += f"<p class='metadata'><strong>Por quê:</strong> {rec['justificativa']}</p>"

                if rec.get('como_implementar'):
                    html += "<p><strong>Como implementar:</strong></p><ul>"
                    for step in rec['como_implementar']:
                        html += f"<li>{step}</li>"
                    html += "</ul>"

                if rec.get('prazo'):
                    html += f"<p class='metadata'>⏱ <strong>Prazo:</strong> {rec['prazo']}"
                    if rec.get('investimento_estimado'):
                        html += f" | 💰 <strong>Investimento:</strong> {rec['investimento_estimado']}"
                    if rec.get('retorno_esperado'):
                        html += f" | 📈 <strong>Retorno:</strong> {rec['retorno_esperado']}"
                    html += "</p>"

                html += "</div>"
            else:
                html += f"<div class='recommendation'><p>{rec}</p></div>"

    # Scenario Planning
    if report.get('planejamento_cenarios'):
        cenarios = report['planejamento_cenarios']
        html += """
        <div class="page-break"></div>
        <h2>Planejamento de Cenários</h2>
"""

        if cenarios.get('cenario_otimista'):
            cen = cenarios['cenario_otimista']
            html += f"""
        <div class="scenario-box scenario-optimistic">
            <h4 style="color: #16a34a;">Cenário Otimista ({cen.get('probabilidade', '20-25%')})</h4>
            <p><strong>Impacto:</strong> {cen.get('impacto_receita', 'N/A')}</p>
            <p><strong>Ações:</strong> {cen.get('acoes_requeridas', 'N/A')}</p>
        </div>
"""

        if cenarios.get('cenario_realista'):
            cen = cenarios['cenario_realista']
            html += f"""
        <div class="scenario-box scenario-realistic">
            <h4 style="color: #2563eb;">Cenário Realista ({cen.get('probabilidade', '50-60%')})</h4>
            <p><strong>Impacto:</strong> {cen.get('impacto_receita', 'N/A')}</p>
            <p><strong>Ações:</strong> {cen.get('acoes_requeridas', 'N/A')}</p>
        </div>
"""

        if cenarios.get('cenario_pessimista'):
            cen = cenarios['cenario_pessimista']
            html += f"""
        <div class="scenario-box scenario-pessimistic">
            <h4 style="color: #dc2626;">Cenário Pessimista ({cen.get('probabilidade', '15-20%')})</h4>
            <p><strong>Impacto:</strong> {cen.get('impacto_receita', 'N/A')}</p>
            <p><strong>Ações:</strong> {cen.get('acoes_requeridas', 'N/A')}</p>
        </div>
"""

    # OKRs
    if report.get('okrs_propostos'):
        html += """
        <div class="page-break"></div>
        <h2>OKRs Propostos</h2>
"""
        for okr in report['okrs_propostos']:
            html += f"""
        <div class="info-box">
            <h4>{okr.get('trimestre', 'Q1')} 2025: {okr.get('objetivo', '')}</h4>
            <p><strong>Resultados-Chave:</strong></p>
            <ul>
"""
            for kr in okr.get('resultados_chave', []):
                html += f"<li>{kr}</li>"
            html += "</ul>"

            if okr.get('investimento_estimado'):
                html += f"<p class='metadata'>💰 <strong>Investimento:</strong> {okr['investimento_estimado']}</p>"

            html += "</div>"

    # Footer
    html += f"""
        <div class="report-footer">
            <p><strong>Relatório gerado por Strategy AI</strong></p>
            <p style="font-size: 8pt;">Powered by IA • {datetime.now().strftime('%d de %B de %Y')}</p>
        </div>
    </div>
</body>
</html>
"""

    return html
