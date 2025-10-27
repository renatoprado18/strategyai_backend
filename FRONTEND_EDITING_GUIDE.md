# Frontend Implementation Guide: AI-Powered Inline Report Editing

## Overview

This guide shows how to implement the intuitive inline editing UI for the rfap_landing Next.js frontend.

**Backend Ready** ✅ All API endpoints are deployed and tested.

---

## API Endpoints (Already Deployed)

### 1. Get Edit Suggestion
**`POST /api/admin/submissions/{submission_id}/edit`**

```typescript
// Request
{
  "selected_text": "A empresa precisa expandir rapidamente",
  "section_path": "sumario_executivo",
  "instruction": "make more professional",
  "complexity": null  // Auto-detect, or force "simple"/"complex"
}

// Response
{
  "success": true,
  "suggested_edit": "A empresa deve expandir de forma estratégica",
  "original_text": "A empresa precisa expandir rapidamente",
  "reasoning": "Changed 'precisa' to 'deve' for more professional tone...",
  "model_used": "google/gemini-2.5-flash-preview-09-2025",
  "complexity": "simple",
  "cost_estimate": 0.000842
}
```

### 2. Apply Edit
**`POST /api/admin/submissions/{submission_id}/apply-edit`**

```typescript
// Request
{
  "section_path": "sumario_executivo",
  "new_text": "A empresa deve expandir de forma estratégica"
}

// Response
{
  "success": true,
  "updated_report": { /* Full updated report JSON */ },
  "edit_count": 1
}
```

### 3. Regenerate PDF
**`POST /api/admin/submissions/{submission_id}/regenerate-pdf`**

```typescript
// Response
{
  "success": true,
  "pdf_url": "/api/admin/submissions/{id}/export-pdf"
}
```

---

## Frontend Implementation

### File Structure (rfap_landing)

```
src/
├── components/
│   ├── report/
│   │   ├── ReportView.tsx          # Main report display
│   │   ├── SelectionToolbar.tsx    # Floating "Edit with AI" button
│   │   ├── EditPanel.tsx           # Slide-in editing panel
│   │   ├── DiffViewer.tsx          # Before/after highlighting
│   │   └── ChatHistory.tsx         # Edit conversation history
│   └── ui/
│       └── ... (Shadcn components)
└── hooks/
    └── useReportEditor.ts          # AI editor logic
```

---

## Component 1: SelectionToolbar

**Purpose:** Floating toolbar that appears when user selects text.

```tsx
// components/report/SelectionToolbar.tsx
"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Sparkles } from "lucide-react";

interface SelectionToolbarProps {
  onEditClick: (selectedText: string, selection: Selection) => void;
}

export function SelectionToolbar({ onEditClick }: SelectionToolbarProps) {
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [visible, setVisible] = useState(false);
  const [selectedText, setSelectedText] = useState("");
  const [selection, setSelection] = useState<Selection | null>(null);

  useEffect(() => {
    const handleSelection = () => {
      const sel = window.getSelection();
      if (sel && sel.toString().trim().length > 0) {
        const range = sel.getRangeAt(0);
        const rect = range.getBoundingClientRect();

        setPosition({
          x: rect.left + rect.width / 2,
          y: rect.top - 50, // Above selection
        });
        setSelectedText(sel.toString());
        setSelection(sel);
        setVisible(true);
      } else {
        setVisible(false);
      }
    };

    document.addEventListener("selectionchange", handleSelection);
    document.addEventListener("mouseup", handleSelection);

    return () => {
      document.removeEventListener("selectionchange", handleSelection);
      document.removeEventListener("mouseup", handleSelection);
    };
  }, []);

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
        onClick={() => {
          if (selection) {
            onEditClick(selectedText, selection);
          }
        }}
        className="shadow-lg bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
        size="sm"
      >
        <Sparkles className="w-4 h-4 mr-2" />
        Edit with AI
      </Button>
    </div>
  );
}
```

---

## Component 2: EditPanel

**Purpose:** Slide-in panel for chat-based editing.

```tsx
// components/report/EditPanel.tsx
"use client";

import { useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DiffViewer } from "./DiffViewer";
import { Check, X, RefreshCw, Send, Sparkles } from "lucide-react";
import { useReportEditor } from "@/hooks/useReportEditor";

interface EditPanelProps {
  open: boolean;
  onClose: () => void;
  reportId: number;
  selectedText: string;
  sectionPath: string;
}

export function EditPanel({
  open,
  onClose,
  reportId,
  selectedText,
  sectionPath,
}: EditPanelProps) {
  const [instruction, setInstruction] = useState("");
  const {
    suggestion,
    isLoading,
    getEditSuggestion,
    applyEdit,
    isApplying,
  } = useReportEditor(reportId);

  const handleSend = async () => {
    if (!instruction.trim()) return;
    await getEditSuggestion(selectedText, sectionPath, instruction);
  };

  const handleAccept = async () => {
    if (suggestion) {
      await applyEdit(sectionPath, suggestion.suggested_edit);
      onClose();
    }
  };

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-[450px] overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-600" />
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
              <p className="text-sm text-gray-900 line-clamp-3">
                {selectedText}
              </p>
            </div>
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
                onKeyPress={(e) => e.key === "Enter" && handleSend()}
                disabled={isLoading}
              />
              <Button
                onClick={handleSend}
                disabled={isLoading || !instruction.trim()}
                size="icon"
                className="bg-gradient-to-r from-purple-600 to-blue-600"
              >
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center gap-2 text-sm text-purple-600">
              <Sparkles className="w-4 h-4 animate-pulse" />
              AI is thinking...
            </div>
          )}

          {/* Suggestion */}
          {suggestion && !isLoading && (
            <div className="space-y-4">
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
                <div className="p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <p className="text-sm text-blue-900">
                    <span className="font-medium">Why:</span> {suggestion.reasoning}
                  </p>
                </div>
              )}

              {/* Action Buttons */}
              <div className="flex gap-2">
                <Button
                  onClick={handleAccept}
                  disabled={isApplying}
                  className="flex-1 bg-green-600 hover:bg-green-700"
                >
                  <Check className="w-4 h-4 mr-2" />
                  Accept
                </Button>
                <Button
                  onClick={onClose}
                  variant="outline"
                  className="flex-1"
                >
                  <X className="w-4 h-4 mr-2" />
                  Reject
                </Button>
                <Button
                  onClick={() => setInstruction("Refine this further")}
                  variant="outline"
                  size="icon"
                >
                  <RefreshCw className="w-4 h-4" />
                </Button>
              </div>

              {/* Metadata */}
              <div className="text-xs text-gray-500 flex justify-between">
                <span>Model: {suggestion.complexity}</span>
                <span>Cost: ${suggestion.cost_estimate?.toFixed(6)}</span>
              </div>
            </div>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
```

---

## Component 3: DiffViewer

**Purpose:** Show before/after changes with highlighting.

```tsx
// components/report/DiffViewer.tsx
"use client";

import { diffWords } from "diff";

interface DiffViewerProps {
  original: string;
  edited: string;
}

export function DiffViewer({ original, edited }: DiffViewerProps) {
  const diff = diffWords(original, edited);

  return (
    <div className="p-4 bg-gray-50 rounded-lg border border-gray-200 space-y-2">
      <div className="text-xs font-medium text-gray-500 uppercase">Before</div>
      <div className="text-sm">
        {diff.map((part, index) => (
          <span
            key={index}
            className={
              part.removed
                ? "bg-red-100 text-red-900 line-through"
                : part.added
                ? ""
                : "text-gray-700"
            }
          >
            {part.removed && part.value}
          </span>
        ))}
      </div>

      <div className="border-t border-gray-300 my-2"></div>

      <div className="text-xs font-medium text-gray-500 uppercase">After</div>
      <div className="text-sm">
        {diff.map((part, index) => (
          <span
            key={index}
            className={
              part.added
                ? "bg-green-100 text-green-900 font-medium"
                : part.removed
                ? ""
                : "text-gray-900"
            }
          >
            {!part.removed && part.value}
          </span>
        ))}
      </div>
    </div>
  );
}
```

---

## Hook: useReportEditor

**Purpose:** API integration logic.

```tsx
// hooks/useReportEditor.ts
"use client";

import { useState } from "react";
import { toast } from "sonner";

interface EditSuggestion {
  success: boolean;
  suggested_edit: string;
  original_text: string;
  reasoning: string;
  model_used: string;
  complexity: string;
  cost_estimate: number;
}

export function useReportEditor(reportId: number) {
  const [suggestion, setSuggestion] = useState<EditSuggestion | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isApplying, setIsApplying] = useState(false);

  const getEditSuggestion = async (
    selectedText: string,
    sectionPath: string,
    instruction: string
  ) => {
    setIsLoading(true);
    setSuggestion(null);

    try {
      const response = await fetch(`/api/admin/submissions/${reportId}/edit`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${localStorage.getItem("token")}`,
        },
        body: JSON.stringify({
          selected_text: selectedText,
          section_path: sectionPath,
          instruction,
        }),
      });

      const data = await response.json();

      if (data.success) {
        setSuggestion(data);
        toast.success("Edit suggestion ready!");
      } else {
        toast.error(data.error || "Failed to generate edit");
      }
    } catch (error) {
      toast.error("Failed to connect to AI editor");
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const applyEdit = async (sectionPath: string, newText: string) => {
    setIsApplying(true);

    try {
      const response = await fetch(
        `/api/admin/submissions/${reportId}/apply-edit`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${localStorage.getItem("token")}`,
          },
          body: JSON.stringify({
            section_path: sectionPath,
            new_text: newText,
          }),
        }
      );

      const data = await response.json();

      if (data.success) {
        toast.success("Edit applied successfully!");
        // Trigger re-render of report view
        window.location.reload();  // Or use React state update
      } else {
        toast.error(data.error || "Failed to apply edit");
      }
    } catch (error) {
      toast.error("Failed to apply edit");
      console.error(error);
    } finally {
      setIsApplying(false);
    }
  };

  return {
    suggestion,
    isLoading,
    isApplying,
    getEditSuggestion,
    applyEdit,
  };
}
```

---

## Integration in ReportView

```tsx
// components/report/ReportView.tsx
"use client";

import { useState } from "react";
import { SelectionToolbar } from "./SelectionToolbar";
import { EditPanel } from "./EditPanel";

export function ReportView({ reportId, report }) {
  const [editPanelOpen, setEditPanelOpen] = useState(false);
  const [selectedText, setSelectedText] = useState("");
  const [sectionPath, setSectionPath] = useState("");

  const handleEditClick = (text: string, selection: Selection) => {
    // Detect section path from selection
    // You can add data-section-path to report elements
    const element = selection.anchorNode?.parentElement;
    const path = element?.getAttribute("data-section-path") || "unknown";

    setSelectedText(text);
    setSectionPath(path);
    setEditPanelOpen(true);
  };

  return (
    <div className="relative">
      <SelectionToolbar onEditClick={handleEditClick} />

      <div className="report-content">
        {/* Render report with data-section-path attributes */}
        <div data-section-path="sumario_executivo">
          <h2>Sumário Executivo</h2>
          <p>{report.sumario_executivo}</p>
        </div>

        {/* ... other sections ... */}
      </div>

      <EditPanel
        open={editPanelOpen}
        onClose={() => setEditPanelOpen(false)}
        reportId={reportId}
        selectedText={selectedText}
        sectionPath={sectionPath}
      />
    </div>
  );
}
```

---

## Required Dependencies

```bash
# Install in rfap_landing frontend
npm install diff
npm install sonner  # For toast notifications
npm install lucide-react  # Icons
```

---

## Database Migration

Run this in Supabase SQL Editor (already created in `migrations/add_editing_columns.sql`):

```sql
ALTER TABLE submissions
ADD COLUMN IF NOT EXISTS edited_json JSONB,
ADD COLUMN IF NOT EXISTS last_edited_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS edit_count INTEGER DEFAULT 0;
```

---

## Testing the Feature

1. **Deploy backend** (already done ✅)
2. **Run database migration** in Supabase SQL Editor
3. **Implement frontend components** in rfap_landing
4. **Test flow:**
   - View a completed report
   - Select text
   - Click "Edit with AI"
   - Type instruction: "make more professional"
   - See suggestion
   - Click "Accept"
   - See updated report
   - Export PDF with edits

---

## Cost Estimates

- **Simple edit** (Gemini Flash): ~$0.0008 per edit
- **Complex edit** (Claude Haiku): ~$0.003 per edit
- **100 edits**: ~$0.11 (11 cents)
- **1,000 edits**: ~$1.10

**Extremely cost-effective!** 🎉

---

## Next Steps

1. ✅ Backend deployed
2. ⏳ Run database migration
3. ⏳ Implement frontend components
4. ⏳ Test with real reports
5. ⏳ Polish UI/UX
6. ⏳ Add keyboard shortcuts (Cmd+E to edit selection)
7. ⏳ Add "Export edited PDF" button

---

Questions? The backend is ready and waiting! 🚀
