/**
 * AI-Powered Edit Panel v2 - Production Ready
 * Features:
 * - Real-time AI suggestions
 * - Proper React state management (no window.reload)
 * - Visual diff highlighting
 * - Chat-based refinement
 * - Cost tracking
 */

"use client";

import { useState, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Check, X, RefreshCw, Send, Sparkles, Loader2 } from "lucide-react";
import { toast } from "sonner";

/**
 * Simple Diff Viewer Component
 * Shows before/after with highlighting
 */
function DiffViewer({ original, edited }: { original: string; edited: string }) {
  // Simple word-based diff (you can install 'diff' package for better results)
  const originalWords = original.split(" ");
  const editedWords = edited.split(" ");

  return (
    <div className="space-y-3">
      {/* Before */}
      <div className="bg-red-50 border border-red-200 rounded-lg p-3">
        <p className="text-xs font-medium text-red-700 mb-1">Antes:</p>
        <p className="text-sm text-red-900 line-through">{original}</p>
      </div>

      {/* After */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-3">
        <p className="text-xs font-medium text-green-700 mb-1">Depois:</p>
        <p className="text-sm text-green-900 font-medium">{edited}</p>
      </div>
    </div>
  );
}

interface EditPanelProps {
  open: boolean;
  onClose: () => void;
  reportId: number;
  selectedText: string;
  sectionPath: string;
  onEditApplied: (sectionPath: string, newText: string) => void; // Callback to update report state
}

interface EditSuggestion {
  success: boolean;
  suggested_edit: string;
  original_text: string;
  reasoning: string;
  model_used: string;
  complexity: string;
  cost_estimate: number;
}

export function EditPanel({
  open,
  onClose,
  reportId,
  selectedText,
  sectionPath,
  onEditApplied,
}: EditPanelProps) {
  const [instruction, setInstruction] = useState("");
  const [suggestion, setSuggestion] = useState<EditSuggestion | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [chatHistory, setChatHistory] = useState<Array<{ instruction: string; result: string }>>([]);

  // Reset state when panel opens with new selection
  useEffect(() => {
    if (open) {
      setSuggestion(null);
      setInstruction("");
      setChatHistory([]);
    }
  }, [open, selectedText, sectionPath]);

  const handleGetSuggestion = async () => {
    if (!instruction.trim()) {
      toast.error("Please enter an instruction");
      return;
    }

    setIsLoading(true);
    setSuggestion(null);

    try {
      const token = localStorage.getItem("token");
      if (!token) {
        toast.error("Not authenticated");
        setIsLoading(false);
        return;
      }

      const response = await fetch(`/api/admin/submissions/${reportId}/edit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          selected_text: selectedText,
          section_path: sectionPath,
          instruction: instruction.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to get suggestion");
      }

      if (data.success) {
        setSuggestion(data);
        setChatHistory([...chatHistory, { instruction, result: data.suggested_edit }]);
        toast.success("AI suggestion ready!");
      } else {
        toast.error(data.error || "Failed to generate edit");
      }
    } catch (error) {
      console.error("Edit suggestion error:", error);
      toast.error(error instanceof Error ? error.message : "Failed to connect to AI");
    } finally {
      setIsLoading(false);
    }
  };

  const handleApplyEdit = async () => {
    if (!suggestion) return;

    setIsApplying(true);

    try {
      const token = localStorage.getItem("token");
      if (!token) {
        toast.error("Not authenticated");
        setIsApplying(false);
        return;
      }

      const response = await fetch(`/api/admin/submissions/${reportId}/apply-edit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          section_path: sectionPath,
          new_text: suggestion.suggested_edit,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to apply edit");
      }

      if (data.success) {
        toast.success(`Edit applied! (Total edits: ${data.edit_count})`);

        // Update parent component state (no reload!)
        onEditApplied(sectionPath, suggestion.suggested_edit);

        // Close panel
        onClose();
      } else {
        toast.error(data.error || "Failed to apply edit");
      }
    } catch (error) {
      console.error("Apply edit error:", error);
      toast.error(error instanceof Error ? error.message : "Failed to apply edit");
    } finally {
      setIsApplying(false);
    }
  };

  const handleRefine = () => {
    if (suggestion) {
      setInstruction(`Refine this: ${suggestion.suggested_edit}`);
      setSuggestion(null);
    }
  };

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-[450px] sm:w-[540px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-600 animate-pulse" />
            Editing with AI
          </SheetTitle>
          <SheetDescription>
            Make changes to your report using natural language
          </SheetDescription>
        </SheetHeader>

        <div className="mt-6 space-y-4">
          {/* Selected Text Preview */}
          <div>
            <label className="text-sm font-medium text-gray-700 flex items-center gap-2 mb-2">
              📝 Selected Text
            </label>
            <div className="p-3 bg-gray-50 rounded-lg border border-gray-200">
              <p className="text-sm text-gray-900 line-clamp-4">
                {selectedText}
              </p>
            </div>
            <p className="text-xs text-gray-500 mt-1">
              Section: <code className="bg-gray-100 px-1 rounded">{sectionPath}</code>
            </p>
          </div>

          {/* Instruction Input */}
          <div>
            <label className="text-sm font-medium text-gray-700 flex items-center gap-2 mb-2">
              💬 What would you like to change?
            </label>
            <div className="flex gap-2">
              <Input
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="e.g., Make this more concise"
                onKeyPress={(e) => e.key === "Enter" && !isLoading && handleGetSuggestion()}
                disabled={isLoading}
                className="flex-1"
              />
              <Button
                onClick={handleGetSuggestion}
                disabled={isLoading || !instruction.trim()}
                size="icon"
                className="bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 shrink-0"
              >
                {isLoading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Send className="w-4 h-4" />
                )}
              </Button>
            </div>
          </div>

          {/* Quick Suggestions */}
          {!suggestion && !isLoading && (
            <div className="flex flex-wrap gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setInstruction("Make this more concise")}
                className="text-xs"
              >
                Make shorter
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setInstruction("Make this more professional")}
                className="text-xs"
              >
                More professional
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setInstruction("Add more detail")}
                className="text-xs"
              >
                Add detail
              </Button>
            </div>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-purple-600 bg-purple-50 p-4 rounded-lg border border-purple-200">
              <Sparkles className="w-4 h-4 animate-pulse" />
              <span>AI is thinking...</span>
            </div>
          )}

          {/* Suggestion */}
          {suggestion && !isLoading && (
            <div className="space-y-4 animate-in fade-in duration-300">
              <div>
                <label className="text-sm font-medium text-gray-700 flex items-center gap-2 mb-2">
                  ✅ Suggested Edit
                </label>
                <DiffViewer
                  original={suggestion.original_text}
                  edited={suggestion.suggested_edit}
                />
              </div>

              {/* Reasoning */}
              {suggestion.reasoning && (
                <div className="bg-blue-50 p-3 rounded-lg border border-blue-200">
                  <p className="text-xs font-medium text-blue-900 mb-1">Why this change:</p>
                  <p className="text-sm text-blue-800">{suggestion.reasoning}</p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-2">
                <Button
                  onClick={handleApplyEdit}
                  disabled={isApplying}
                  className="flex-1 bg-green-600 hover:bg-green-700"
                >
                  {isApplying ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Applying...
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4 mr-2" />
                      Accept
                    </>
                  )}
                </Button>
                <Button
                  onClick={onClose}
                  variant="outline"
                  disabled={isApplying}
                  className="flex-1"
                >
                  <X className="w-4 h-4 mr-2" />
                  Reject
                </Button>
                <Button
                  onClick={handleRefine}
                  variant="outline"
                  disabled={isApplying}
                  size="icon"
                  title="Refine this suggestion further"
                >
                  <RefreshCw className="w-4 h-4" />
                </Button>
              </div>

              {/* Metadata */}
              <div className="flex justify-between text-xs text-gray-500 bg-gray-50 p-2 rounded">
                <span className="flex items-center gap-1">
                  <span className="font-medium">Model:</span>
                  <span className="capitalize">{suggestion.complexity}</span>
                  {suggestion.complexity === "simple" ? " ⚡" : " 🧠"}
                </span>
                <span className="flex items-center gap-1">
                  <span className="font-medium">Cost:</span>
                  <span>${suggestion.cost_estimate?.toFixed(6)}</span>
                </span>
              </div>
            </div>
          )}

          {/* Chat History */}
          {chatHistory.length > 0 && !suggestion && (
            <div className="border-t pt-4">
              <p className="text-xs font-medium text-gray-700 mb-2">Recent edits:</p>
              <div className="space-y-2 max-h-40 overflow-y-auto">
                {chatHistory.map((chat, idx) => (
                  <div key={idx} className="text-xs bg-gray-50 p-2 rounded">
                    <p className="font-medium text-gray-700">{chat.instruction}</p>
                    <p className="text-gray-600 truncate">{chat.result}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
