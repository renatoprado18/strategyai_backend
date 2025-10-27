/**
 * Complete Editable Report View - Drop-in Component
 *
 * This is the MAIN component you drop into your report page.
 * It handles EVERYTHING:
 * - Report rendering
 * - Text selection detection
 * - AI editing panel
 * - State updates (no page reload!)
 * - Proper React state management
 *
 * USAGE:
 * <EditableReportView
 *   reportId={19}
 *   initialReport={reportData}
 *   onReportUpdated={(newReport) => console.log("Report updated!")}
 * />
 */

"use client";

import React, { useState, useCallback } from "react";
import { ReportRenderer } from "./ReportRenderer";
import { EditPanel } from "./EditPanel_v2";
import { Button } from "@/components/ui/button";
import { Sparkles, Download } from "lucide-react";
import { toast } from "sonner";

interface EditableReportViewProps {
  reportId: number;
  initialReport: any; // Report JSON data
  onReportUpdated?: (updatedReport: any) => void;
}

/**
 * Floating Selection Toolbar
 * Appears when user selects text
 */
function SelectionToolbar({
  onEditClick,
  visible,
  position
}: {
  onEditClick: () => void;
  visible: boolean;
  position: { x: number; y: number };
}) {
  if (!visible) return null;

  return (
    <div
      className="fixed z-50 animate-in fade-in zoom-in-95 duration-200"
      style={{
        left: `${position.x}px`,
        top: `${position.y}px`,
        transform: "translateX(-50%)",
      }}
    >
      <Button
        onClick={onEditClick}
        className="shadow-xl bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
        size="sm"
      >
        <Sparkles className="w-4 h-4 mr-2" />
        Edit with AI
      </Button>
    </div>
  );
}

/**
 * Main Editable Report View Component
 */
export function EditableReportView({
  reportId,
  initialReport,
  onReportUpdated,
}: EditableReportViewProps) {
  // Report state (this gets updated when edits are applied)
  const [report, setReport] = useState(initialReport);

  // Selection state
  const [selectedText, setSelectedText] = useState("");
  const [sectionPath, setSectionPath] = useState("");
  const [toolbarVisible, setToolbarVisible] = useState(false);
  const [toolbarPosition, setToolbarPosition] = useState({ x: 0, y: 0 });

  // Edit panel state
  const [editPanelOpen, setEditPanelOpen] = useState(false);

  /**
   * Handle text selection
   */
  const handleSectionSelect = useCallback((path: string, text: string) => {
    if (text.trim().length < 3) {
      setToolbarVisible(false);
      return;
    }

    const selection = window.getSelection();
    if (selection && selection.rangeCount > 0) {
      const range = selection.getRangeAt(0);
      const rect = range.getBoundingClientRect();

      setSelectedText(text);
      setSectionPath(path);
      setToolbarPosition({
        x: rect.left + rect.width / 2,
        y: rect.top - 50,
      });
      setToolbarVisible(true);
    }
  }, []);

  /**
   * Open edit panel
   */
  const handleEditClick = useCallback(() => {
    setToolbarVisible(false);
    setEditPanelOpen(true);
  }, []);

  /**
   * Apply edit to report state (NO PAGE RELOAD!)
   */
  const handleEditApplied = useCallback(
    (path: string, newText: string) => {
      // Update report state by navigating the JSON path
      const updatedReport = JSON.parse(JSON.stringify(report)); // Deep clone

      // Parse the path and navigate to update the value
      const pathParts = path.split(/[\.\[\]]/).filter(Boolean);
      let current = updatedReport;

      for (let i = 0; i < pathParts.length - 1; i++) {
        const part = pathParts[i];
        const index = parseInt(part);
        if (!isNaN(index)) {
          current = current[index];
        } else {
          current = current[part];
        }
      }

      // Set the final value
      const finalKey = pathParts[pathParts.length - 1];
      const finalIndex = parseInt(finalKey);
      if (!isNaN(finalIndex)) {
        current[finalIndex] = newText;
      } else {
        current[finalKey] = newText;
      }

      // Update state
      setReport(updatedReport);

      // Notify parent component
      if (onReportUpdated) {
        onReportUpdated(updatedReport);
      }

      toast.success("Report updated! Changes are saved.");
    },
    [report, onReportUpdated]
  );

  /**
   * Export PDF with edits
   */
  const handleExportPDF = async () => {
    try {
      const token = localStorage.getItem("token");
      const response = await fetch(`/api/admin/submissions/${reportId}/regenerate-pdf`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (response.ok) {
        // Redirect to PDF download
        window.open(`/api/admin/submissions/${reportId}/export-pdf`, "_blank");
        toast.success("PDF generated with your edits!");
      } else {
        toast.error("Failed to generate PDF");
      }
    } catch (error) {
      console.error("PDF export error:", error);
      toast.error("Failed to export PDF");
    }
  };

  // Hide toolbar when clicking elsewhere
  React.useEffect(() => {
    const handleClickAway = () => {
      const selection = window.getSelection();
      if (!selection || selection.toString().trim().length === 0) {
        setToolbarVisible(false);
      }
    };

    document.addEventListener("mousedown", handleClickAway);
    return () => document.removeEventListener("mousedown", handleClickAway);
  }, []);

  return (
    <div className="relative min-h-screen bg-gray-50 pb-20">
      {/* Export Button (Floating) */}
      <div className="fixed bottom-6 right-6 z-40">
        <Button
          onClick={handleExportPDF}
          className="shadow-xl bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
          size="lg"
        >
          <Download className="w-5 h-5 mr-2" />
          Export PDF with Edits
        </Button>
      </div>

      {/* Selection Toolbar */}
      <SelectionToolbar
        visible={toolbarVisible}
        position={toolbarPosition}
        onEditClick={handleEditClick}
      />

      {/* Report Renderer */}
      <ReportRenderer
        report={report}
        onSectionSelect={handleSectionSelect}
      />

      {/* Edit Panel */}
      <EditPanel
        open={editPanelOpen}
        onClose={() => setEditPanelOpen(false)}
        reportId={reportId}
        selectedText={selectedText}
        sectionPath={sectionPath}
        onEditApplied={handleEditApplied}
      />
    </div>
  );
}
