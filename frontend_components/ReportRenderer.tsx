/**
 * Complete Report Renderer with Automatic Section Path Tracking
 * Drop-in component for rendering Strategy AI reports with AI editing support
 *
 * Features:
 * - Automatic section path attribution
 * - Handles all report sections (SWOT, OKRs, TAM/SAM/SOM, etc.)
 * - Beautiful typography and layout
 * - Ready for SelectionToolbar integration
 */

"use client";

import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

interface ReportData {
  sumario_executivo?: string;
  analise_swot?: {
    forcas?: string[];
    fraquezas?: string[];
    oportunidades?: string[];
    ameacas?: string[];
  };
  tam_sam_som?: {
    tam_total_market?: string;
    sam_available_market?: string;
    som_obtainable_market?: string;
    justificativa?: string;
    status?: string;
    mensagem?: string;
  };
  recomendacoes_prioritarias?: Array<{
    prioridade?: number;
    titulo?: string;
    recomendacao?: string;
    justificativa?: string;
    prazo?: string;
    investimento_estimado?: string;
    retorno_esperado?: string;
  }>;
  okrs_propostos?: Array<{
    trimestre?: string;
    objetivo?: string;
    resultados_chave?: string[];
    investimento_estimado?: string;
  }>;
  planejamento_cenarios?: {
    cenario_otimista?: any;
    cenario_realista?: any;
    cenario_pessimista?: any;
  };
  posicionamento_competitivo?: {
    principais_concorrentes?: any[];
    diferenciais?: string[];
  };
  [key: string]: any;
}

interface ReportRendererProps {
  report: ReportData;
  onSectionSelect?: (sectionPath: string, selectedText: string) => void;
}

/**
 * Editable Text Component
 * Wraps text with section path for AI editing
 */
const EditableText: React.FC<{
  path: string;
  children: React.ReactNode;
  className?: string;
}> = ({ path, children, className = "" }) => {
  return (
    <span
      data-section-path={path}
      className={`editable-content ${className}`}
    >
      {children}
    </span>
  );
};

/**
 * Main Report Renderer Component
 */
export function ReportRenderer({ report, onSectionSelect }: ReportRendererProps) {
  // Handle selection events
  React.useEffect(() => {
    const handleSelection = () => {
      const selection = window.getSelection();
      if (!selection || selection.toString().trim().length === 0) return;

      // Find the closest element with data-section-path
      let element = selection.anchorNode as Node | null;
      while (element && element.nodeType !== Node.ELEMENT_NODE) {
        element = element.parentNode;
      }

      if (element) {
        const pathElement = (element as Element).closest("[data-section-path]");
        if (pathElement) {
          const sectionPath = pathElement.getAttribute("data-section-path");
          if (sectionPath && onSectionSelect) {
            onSectionSelect(sectionPath, selection.toString());
          }
        }
      }
    };

    document.addEventListener("selectionchange", handleSelection);
    return () => document.removeEventListener("selectionchange", handleSelection);
  }, [onSectionSelect]);

  return (
    <div className="space-y-8 max-w-5xl mx-auto p-6">
      {/* Executive Summary */}
      {report.sumario_executivo && (
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">📋 Sumário Executivo</CardTitle>
          </CardHeader>
          <CardContent>
            <EditableText path="sumario_executivo" className="text-lg leading-relaxed">
              {report.sumario_executivo}
            </EditableText>
          </CardContent>
        </Card>
      )}

      {/* SWOT Analysis */}
      {report.analise_swot && (
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">🎯 Análise SWOT</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Strengths */}
              {report.analise_swot.forcas && report.analise_swot.forcas.length > 0 && (
                <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                  <h3 className="font-semibold text-green-900 mb-3 flex items-center gap-2">
                    💪 Forças
                  </h3>
                  <ul className="space-y-2">
                    {report.analise_swot.forcas.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-green-600 mt-1">•</span>
                        <EditableText
                          path={`analise_swot.forcas[${idx}]`}
                          className="text-sm text-green-900"
                        >
                          {item}
                        </EditableText>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Weaknesses */}
              {report.analise_swot.fraquezas && report.analise_swot.fraquezas.length > 0 && (
                <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                  <h3 className="font-semibold text-red-900 mb-3 flex items-center gap-2">
                    ⚠️ Fraquezas
                  </h3>
                  <ul className="space-y-2">
                    {report.analise_swot.fraquezas.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-red-600 mt-1">•</span>
                        <EditableText
                          path={`analise_swot.fraquezas[${idx}]`}
                          className="text-sm text-red-900"
                        >
                          {item}
                        </EditableText>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Opportunities */}
              {report.analise_swot.oportunidades && report.analise_swot.oportunidades.length > 0 && (
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <h3 className="font-semibold text-blue-900 mb-3 flex items-center gap-2">
                    🚀 Oportunidades
                  </h3>
                  <ul className="space-y-2">
                    {report.analise_swot.oportunidades.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-blue-600 mt-1">•</span>
                        <EditableText
                          path={`analise_swot.oportunidades[${idx}]`}
                          className="text-sm text-blue-900"
                        >
                          {item}
                        </EditableText>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Threats */}
              {report.analise_swot.ameacas && report.analise_swot.ameacas.length > 0 && (
                <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                  <h3 className="font-semibold text-yellow-900 mb-3 flex items-center gap-2">
                    ⚡ Ameaças
                  </h3>
                  <ul className="space-y-2">
                    {report.analise_swot.ameacas.map((item, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-yellow-600 mt-1">•</span>
                        <EditableText
                          path={`analise_swot.ameacas[${idx}]`}
                          className="text-sm text-yellow-900"
                        >
                          {item}
                        </EditableText>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* TAM/SAM/SOM */}
      {report.tam_sam_som && (
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">📊 Análise de Mercado (TAM-SAM-SOM)</CardTitle>
          </CardHeader>
          <CardContent>
            {report.tam_sam_som.status === "dados_insuficientes" ? (
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-6">
                <h3 className="font-semibold text-amber-900 mb-2">
                  ⚠️ Dados Insuficientes
                </h3>
                <EditableText
                  path="tam_sam_som.mensagem"
                  className="text-sm text-amber-800"
                >
                  {report.tam_sam_som.mensagem}
                </EditableText>
                {report.tam_sam_som.o_que_fornecer && (
                  <div className="mt-4">
                    <p className="text-sm font-medium text-amber-900 mb-2">
                      Para análise completa, forneça:
                    </p>
                    <ul className="space-y-1">
                      {(report.tam_sam_som.o_que_fornecer as string[]).map((item, idx) => (
                        <li key={idx} className="text-sm text-amber-800 flex items-start gap-2">
                          <span>•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <div className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {report.tam_sam_som.tam_total_market && (
                    <div className="bg-blue-50 p-4 rounded-lg">
                      <h4 className="text-sm font-semibold text-blue-900 mb-2">
                        TAM (Total Addressable Market)
                      </h4>
                      <EditableText
                        path="tam_sam_som.tam_total_market"
                        className="text-lg font-bold text-blue-700"
                      >
                        {report.tam_sam_som.tam_total_market}
                      </EditableText>
                    </div>
                  )}
                  {report.tam_sam_som.sam_available_market && (
                    <div className="bg-purple-50 p-4 rounded-lg">
                      <h4 className="text-sm font-semibold text-purple-900 mb-2">
                        SAM (Serviceable Available Market)
                      </h4>
                      <EditableText
                        path="tam_sam_som.sam_available_market"
                        className="text-lg font-bold text-purple-700"
                      >
                        {report.tam_sam_som.sam_available_market}
                      </EditableText>
                    </div>
                  )}
                  {report.tam_sam_som.som_obtainable_market && (
                    <div className="bg-green-50 p-4 rounded-lg">
                      <h4 className="text-sm font-semibold text-green-900 mb-2">
                        SOM (Serviceable Obtainable Market)
                      </h4>
                      <EditableText
                        path="tam_sam_som.som_obtainable_market"
                        className="text-lg font-bold text-green-700"
                      >
                        {report.tam_sam_som.som_obtainable_market}
                      </EditableText>
                    </div>
                  )}
                </div>
                {report.tam_sam_som.justificativa && (
                  <div className="bg-gray-50 p-4 rounded-lg">
                    <h4 className="text-sm font-semibold text-gray-900 mb-2">
                      Justificativa
                    </h4>
                    <EditableText
                      path="tam_sam_som.justificativa"
                      className="text-sm text-gray-700"
                    >
                      {report.tam_sam_som.justificativa}
                    </EditableText>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Priority Recommendations */}
      {report.recomendacoes_prioritarias && report.recomendacoes_prioritarias.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">⭐ Recomendações Prioritárias</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {report.recomendacoes_prioritarias.map((rec, idx) => (
              <div
                key={idx}
                className="border border-gray-200 rounded-lg p-4 hover:border-purple-300 transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <h3 className="font-semibold text-lg flex items-center gap-2">
                    <Badge variant="secondary">#{rec.prioridade || idx + 1}</Badge>
                    <EditableText
                      path={`recomendacoes_prioritarias[${idx}].titulo`}
                      className="text-gray-900"
                    >
                      {rec.titulo || `Recomendação ${idx + 1}`}
                    </EditableText>
                  </h3>
                </div>
                {rec.recomendacao && (
                  <EditableText
                    path={`recomendacoes_prioritarias[${idx}].recomendacao`}
                    className="text-sm text-gray-700 mb-3 block"
                  >
                    {rec.recomendacao}
                  </EditableText>
                )}
                {rec.justificativa && (
                  <div className="bg-blue-50 p-3 rounded mb-3">
                    <p className="text-xs font-medium text-blue-900 mb-1">Por quê:</p>
                    <EditableText
                      path={`recomendacoes_prioritarias[${idx}].justificativa`}
                      className="text-sm text-blue-800"
                    >
                      {rec.justificativa}
                    </EditableText>
                  </div>
                )}
                <div className="flex flex-wrap gap-3 text-xs text-gray-600">
                  {rec.prazo && (
                    <span className="flex items-center gap-1">
                      <span className="font-medium">Prazo:</span>
                      <EditableText path={`recomendacoes_prioritarias[${idx}].prazo`}>
                        {rec.prazo}
                      </EditableText>
                    </span>
                  )}
                  {rec.investimento_estimado && (
                    <span className="flex items-center gap-1">
                      <span className="font-medium">Investimento:</span>
                      <EditableText path={`recomendacoes_prioritarias[${idx}].investimento_estimado`}>
                        {rec.investimento_estimado}
                      </EditableText>
                    </span>
                  )}
                  {rec.retorno_esperado && (
                    <span className="flex items-center gap-1">
                      <span className="font-medium">Retorno:</span>
                      <EditableText path={`recomendacoes_prioritarias[${idx}].retorno_esperado`}>
                        {rec.retorno_esperado}
                      </EditableText>
                    </span>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* OKRs */}
      {report.okrs_propostos && report.okrs_propostos.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-2xl">🎯 OKRs Propostos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {report.okrs_propostos.map((okr, idx) => (
              <div key={idx} className="border-l-4 border-purple-500 pl-4">
                <div className="flex items-center gap-2 mb-2">
                  <Badge className="bg-purple-100 text-purple-800">
                    {okr.trimestre || `Q${idx + 1}`}
                  </Badge>
                  <EditableText
                    path={`okrs_propostos[${idx}].objetivo`}
                    className="font-semibold text-lg"
                  >
                    {okr.objetivo}
                  </EditableText>
                </div>
                {okr.resultados_chave && okr.resultados_chave.length > 0 && (
                  <div className="mt-3">
                    <p className="text-sm font-medium text-gray-700 mb-2">
                      Resultados-Chave:
                    </p>
                    <ul className="space-y-1">
                      {okr.resultados_chave.map((kr, krIdx) => (
                        <li key={krIdx} className="flex items-start gap-2 text-sm">
                          <span className="text-purple-600 mt-1">•</span>
                          <EditableText
                            path={`okrs_propostos[${idx}].resultados_chave[${krIdx}]`}
                            className="text-gray-700"
                          >
                            {kr}
                          </EditableText>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {okr.investimento_estimado && (
                  <p className="text-xs text-gray-600 mt-2">
                    Investimento estimado:{" "}
                    <EditableText path={`okrs_propostos[${idx}].investimento_estimado`}>
                      {okr.investimento_estimado}
                    </EditableText>
                  </p>
                )}
              </div>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
