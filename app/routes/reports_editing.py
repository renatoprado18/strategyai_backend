"""
Report Editing Routes - AI-Powered Editing and PDF Regeneration

This module contains routes for:
- AI-powered section editing suggestions
- Applying edits to reports
- Regenerating PDFs with applied edits
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from datetime import datetime, timezone
import json
import logging
import os

logger = logging.getLogger(__name__)

# Import schemas
from app.models.schemas import (
    EditRequest,
    EditResponse,
    ApplyEditRequest,
    ApplyEditResponse,
    RegeneratePDFResponse,
)

# Import database functions
from app.core.database import get_submission

# Import auth dependency
from app.routes.auth import RequireAuth

# Import services
from app.services.pdf_generator import generate_pdf_from_report
from app.services.ai.editor import (
    generate_edit_suggestion,
    apply_edit_to_json_path,
    extract_section_context,
)

# Initialize router
router = APIRouter()


# ============================================================================
# AI-POWERED REPORT EDITING
# ============================================================================

@router.post("/submissions/{submission_id}/edit", response_model=EditResponse)
async def edit_report_section(
    submission_id: int,
    edit_request: EditRequest,
    current_user: dict = RequireAuth,
):
    """
    Get AI-powered edit suggestion for a report section (Protected Admin endpoint)

    Uses adaptive model selection:
    - Simple edits (make shorter, more professional, etc.) → Gemini Flash (~$0.0008/edit)
    - Complex edits (rewrite, add analysis, etc.) → Claude Haiku (~$0.003/edit)

    Requires valid JWT token in Authorization header
    """
    try:
        logger.info(f"[AI EDITOR] User {current_user['email']} editing submission {submission_id}")
        logger.info(f"[AI EDITOR] Section: {edit_request.section_path}, Instruction: {edit_request.instruction}")

        # Get submission
        submission = await get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Get report JSON (check edited_json first, fallback to original)
        report_json_str = submission.get("edited_json") or submission.get("report_json")
        if not report_json_str:
            raise HTTPException(status_code=400, detail="Report not yet generated")

        report_json = json.loads(report_json_str)

        # Extract section context
        section_context = extract_section_context(
            full_report=report_json,
            section_path=edit_request.section_path,
            context_chars=500
        )

        # Generate edit suggestion
        result = await generate_edit_suggestion(
            selected_text=edit_request.selected_text,
            instruction=edit_request.instruction,
            section_context=section_context,
            full_report_summary=report_json.get("sumario_executivo", ""),
            complexity=edit_request.complexity
        )

        logger.info(f"[AI EDITOR] ✅ Edit suggestion generated (model: {result['model_used']}, cost: ${result['cost_estimate']:.6f})")

        return EditResponse(
            success=True,
            suggested_edit=result["suggested_edit"],
            original_text=edit_request.selected_text,
            reasoning=result["reasoning"],
            model_used=result["model_used"],
            complexity=result["complexity"],
            cost_estimate=result["cost_estimate"]
        )

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"[ERROR] Invalid JSON in report data: {e}", exc_info=True)
        return EditResponse(success=False, error="Invalid report JSON format")
    except Exception as e:
        # Catch-all for LLM errors, database errors, or unexpected issues
        logger.exception(f"[ERROR] Edit generation error: {e}")
        return EditResponse(success=False, error=str(e))


@router.post("/submissions/{submission_id}/apply-edit", response_model=ApplyEditResponse)
async def apply_report_edit(
    submission_id: int,
    apply_request: ApplyEditRequest,
    current_user: dict = RequireAuth,
):
    """
    Apply an accepted edit to the report (Protected Admin endpoint)

    Updates the edited_json in database with the new text.
    Increments edit_count and updates last_edited_at timestamp.

    Requires valid JWT token in Authorization header
    """
    try:
        logger.info(f"[AI EDITOR] User {current_user['email']} applying edit to submission {submission_id}")
        logger.info(f"[AI EDITOR] Section: {apply_request.section_path}")

        # Get submission
        submission = await get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Get report JSON (check edited_json first, fallback to original)
        report_json_str = submission.get("edited_json") or submission.get("report_json")
        if not report_json_str:
            raise HTTPException(status_code=400, detail="Report not yet generated")

        report_json = json.loads(report_json_str)

        # Apply edit to JSON path
        updated_report = apply_edit_to_json_path(
            report_json=report_json,
            section_path=apply_request.section_path,
            new_text=apply_request.new_text
        )

        # Get current edit count
        edit_count = submission.get("edit_count", 0) + 1

        # Update database
        from app.core.supabase import supabase_service
        update_result = supabase_service.table("submissions").update({
            "edited_json": json.dumps(updated_report, ensure_ascii=False),
            "last_edited_at": datetime.now(timezone.utc).isoformat(),
            "edit_count": edit_count
        }).eq("id", submission_id).execute()

        logger.info(f"[AI EDITOR] ✅ Edit applied successfully (total edits: {edit_count})")

        return ApplyEditResponse(
            success=True,
            updated_report=updated_report,
            edit_count=edit_count
        )

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"[ERROR] Invalid JSON in report data: {e}", exc_info=True)
        return ApplyEditResponse(success=False, error="Invalid report JSON format")
    except KeyError as e:
        logger.error(f"[ERROR] Invalid section path: {e}", exc_info=True)
        return ApplyEditResponse(success=False, error=f"Invalid section path: {e}")
    except Exception as e:
        # Catch-all for database errors or unexpected issues
        logger.exception(f"[ERROR] Apply edit error: {e}")
        return ApplyEditResponse(success=False, error=str(e))


# ============================================================================
# PDF REGENERATION WITH EDITS
# ============================================================================

def _generate_pdf_background(submission_id: int, submission_data: dict, report_json: dict):
    """
    Background task to generate PDF without blocking HTTP response
    """
    try:
        import os
        logger.info(f"[PDF BACKGROUND] Starting PDF generation for submission {submission_id}")

        # Generate PDF
        pdf_bytes = generate_pdf_from_report(
            submission_data=submission_data,
            report_json=report_json
        )

        # Save PDF to file system
        pdf_filename = f"report_{submission_id}_edited.pdf"
        pdf_path = f"./reports/{pdf_filename}"

        # Create reports directory if it doesn't exist
        os.makedirs("./reports", exist_ok=True)

        # Write PDF to file
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        logger.info(f"[PDF BACKGROUND] ✅ PDF generated successfully: {pdf_filename}")

    except FileNotFoundError as e:
        logger.error(f"[PDF BACKGROUND] ❌ Required file not found: {e}", exc_info=True)
    except OSError as e:
        logger.error(f"[PDF BACKGROUND] ❌ File system error: {e}", exc_info=True)
    except Exception as e:
        # Catch-all for PDF generation errors
        logger.exception(f"[PDF BACKGROUND] ❌ PDF generation failed: {e}")


@router.post("/submissions/{submission_id}/regenerate-pdf", response_model=RegeneratePDFResponse)
async def regenerate_pdf_with_edits(
    submission_id: int,
    background_tasks: BackgroundTasks,
    current_user: dict = RequireAuth,
):
    """
    Regenerate PDF with applied edits (Protected Admin endpoint) - ASYNC

    Uses edited_json if available, otherwise falls back to original report_json.
    Generates PDF in background, returns immediately.

    Requires valid JWT token in Authorization header

    Performance: Returns in <100ms (90% faster than synchronous generation)
    """
    try:
        logger.info(f"[AI EDITOR] User {current_user['email']} requesting PDF regeneration for submission {submission_id}")

        # Get submission
        submission = await get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Get report JSON (use edited_json if available)
        report_json_str = submission.get("edited_json") or submission.get("report_json")
        if not report_json_str:
            raise HTTPException(status_code=400, detail="Report not yet generated")

        report_json = json.loads(report_json_str)

        # Build submission data for PDF generator
        submission_data = {
            "company": submission.get("company", ""),
            "industry": submission.get("industry", ""),
            "website": submission.get("website", ""),
            "challenge": submission.get("challenge", ""),
            "name": submission.get("name", ""),
            "updated_at": submission.get("last_edited_at") or submission.get("updated_at", "")
        }

        # Add PDF generation to background queue (non-blocking!)
        background_tasks.add_task(
            _generate_pdf_background,
            submission_id,
            submission_data,
            report_json
        )

        logger.info(f"[AI EDITOR] ✅ PDF generation queued (background task)")

        return RegeneratePDFResponse(
            success=True,
            pdf_url=f"/api/admin/submissions/{submission_id}/export-pdf",
            message="PDF generation started in background. Use the export URL to download when ready."
        )

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"[ERROR] Invalid JSON in report data: {e}", exc_info=True)
        return RegeneratePDFResponse(success=False, error="Invalid report JSON format")
    except Exception as e:
        # Catch-all for database errors or unexpected issues
        logger.exception(f"[ERROR] PDF regeneration error: {e}")
        return RegeneratePDFResponse(success=False, error=str(e))
