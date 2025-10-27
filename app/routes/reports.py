"""
Report Management Routes - PDF Export, Confidence Scoring, and AI Editing

This module contains routes for:
- Listing all submissions (admin)
- Exporting reports as PDF (admin)
- Calculating confidence scores (admin)
- AI-powered report editing (admin)
- Applying edits to reports (admin)
- Regenerating PDFs with edits (admin)
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException, Response
from fastapi.responses import StreamingResponse
from datetime import datetime, timezone
import json

# Import schemas
from app.models.schemas import (
    Submission,
    SubmissionsListResponse,
    EditRequest,
    EditResponse,
    ApplyEditRequest,
    ApplyEditResponse,
    RegeneratePDFResponse,
)

# Import database functions
from app.core.database import (
    get_submission,
    get_all_submissions,
    update_submission_status,
)

# Import auth dependency
from app.routes.auth import RequireAuth

# Import services
from app.services.pdf_generator import generate_pdf_from_report
from app.services.analysis.confidence_scorer import calculate_confidence_score
from app.services.ai.editor import (
    generate_edit_suggestion,
    apply_edit_to_json_path,
    extract_section_context,
)

# Initialize router with prefix
router = APIRouter(prefix="/api/admin")


# ============================================================================
# SUBMISSION LISTING & VIEWING
# ============================================================================

@router.get("/submissions")
async def get_submissions(current_user: dict = RequireAuth, response: Response = None):
    """
    Get all submissions (Protected Admin endpoint)

    Requires valid JWT token in Authorization header
    Returns list of all submissions ordered by created_at DESC

    Cache-Control: 30 seconds (for faster dashboard refreshes)
    NOW WITH DASHBOARD STATS CACHING (5 min TTL)
    """
    try:
        print(f"[AUTH] User {current_user['email']} accessing submissions")

        # Check cache first for dashboard stats (5 min TTL)
        from app.core.cache import get_cached_dashboard_stats, cache_dashboard_stats

        cached_stats = await get_cached_dashboard_stats()

        if cached_stats:
            print(f"[CACHE] 🎯 Dashboard stats cache hit!")
            submissions = cached_stats.get("submissions", [])
            submission_list = [Submission(**sub) for sub in submissions]
        else:
            print(f"[CACHE] ❌ Dashboard stats cache miss - fetching from database")
            submissions = await get_all_submissions()

            # Convert to Pydantic models
            submission_list = [Submission(**sub) for sub in submissions]

            # Cache for 5 minutes
            await cache_dashboard_stats({
                "submissions": submissions,
                "cached_at": datetime.utcnow().isoformat()
            })

        # Add caching headers (30 second cache)
        if response:
            response.headers["Cache-Control"] = "private, max-age=30, must-revalidate"

        return {
            "success": True,
            "data": submission_list,
        }

    except Exception as e:
        print(f"[ERROR] Get submissions error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# PDF EXPORT
# ============================================================================

@router.get("/submissions/{submission_id}/export-pdf")
async def export_submission_pdf(
    submission_id: int,
    current_user: dict = RequireAuth,
):
    """
    Export submission report as production-grade PDF (Protected Admin endpoint)

    Requires valid JWT token in Authorization header
    Returns PDF file with proper text rendering, spacing, and page breaks
    """
    try:
        from fastapi.responses import Response
        from app.services.pdf_generator import generate_pdf_from_report

        print(f"[AUTH] User {current_user['email']} exporting PDF for submission {submission_id}")

        # Get submission
        submission = await get_submission(submission_id)
        if not submission:
            return {"success": False, "error": f"Submission {submission_id} not found"}

        # Use edited_json if available (has edits), otherwise fallback to report_json
        report_json_str = submission.get('edited_json') or submission.get('report_json')
        if not report_json_str:
            return {"success": False, "error": "Report not yet generated"}

        # Parse report JSON
        try:
            report_json = json.loads(report_json_str)
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid report JSON"}

        # Build submission data for PDF generator (consistent format)
        submission_data = {
            "company": submission.get("company", ""),
            "industry": submission.get("industry", ""),
            "website": submission.get("website", ""),
            "challenge": submission.get("challenge", ""),
            "name": submission.get("name", ""),
            "updated_at": submission.get("last_edited_at") or submission.get("updated_at", "")
        }

        # Generate PDF
        print(f"[PDF] Generating PDF for submission {submission_id}...")
        pdf_bytes = generate_pdf_from_report(submission_data, report_json)

        if not pdf_bytes or len(pdf_bytes) == 0:
            print(f"[ERROR] PDF generation returned empty bytes!")
            return {"success": False, "error": "PDF generation failed - empty output"}

        print(f"[PDF] PDF generated successfully ({len(pdf_bytes)} bytes)")

        # Return PDF file
        has_edits = submission.get('edited_json') is not None
        filename = f"relatorio-estrategico-{submission['company'].replace(' ', '-')}-{datetime.now().strftime('%Y-%m-%d')}.pdf"

        # Add cache headers (5 min cache - PDFs don't change unless edited)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
                "Cache-Control": "private, max-age=300",  # 5 minute cache
                "ETag": f'"{submission_id}-v{submission.get("last_edited_at", submission.get("updated_at"))}"'
            }
        )

    except Exception as e:
        print(f"[ERROR] PDF export error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# ============================================================================
# CONFIDENCE SCORING
# ============================================================================

@router.get("/submissions/{submission_id}/confidence")
async def calculate_submission_confidence(
    submission_id: int,
    current_user: dict = RequireAuth,
):
    """
    Calculate or recalculate confidence score for a submission (Protected Admin endpoint)

    Returns confidence score (0-100) with detailed breakdown.

    Score components:
    - Data Completeness (0-30): How much data was gathered
    - Source Success Rate (0-25): How many data sources succeeded
    - Market Research Depth (0-20): Quality of competitor/trend analysis
    - Analysis Comprehensiveness (0-15): Coverage of all frameworks
    - TAM/SAM/SOM Availability (0-10): Market sizing quality

    Requires valid JWT token in Authorization header
    """
    try:
        print(f"[AUTH] User {current_user['email']} calculating confidence for submission {submission_id}")

        # Get submission
        submission = await get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Calculate confidence score
        score, breakdown = calculate_confidence_score(
            submission_data=submission,
            report_json=submission.get("report_json"),
            data_quality_json=submission.get("data_quality_json"),
            processing_metadata=submission.get("processing_metadata"),
        )

        # Add timestamp
        from datetime import datetime, timezone
        breakdown["calculated_at"] = datetime.now(timezone.utc).isoformat()

        # Update database with new score
        await update_submission_status(
            submission_id=submission_id,
            status=submission["status"],  # Keep existing status
            report_json=submission.get("report_json"),  # Keep existing report
            data_quality_json=submission.get("data_quality_json"),  # Keep existing data quality
            processing_metadata=json.dumps({
                **(json.loads(submission.get("processing_metadata", "{}")) if submission.get("processing_metadata") else {}),
                "confidence_score": score,
                "confidence_breakdown": breakdown,
            }),
        )

        print(f"[OK] Calculated confidence score {score}/100 for submission {submission_id}")

        return {
            "success": True,
            "submission_id": submission_id,
            "confidence_score": score,
            "breakdown": breakdown,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Confidence calculation error: {e}")
        return {
            "success": False,
            "error": str(e),
        }


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
        print(f"[AI EDITOR] User {current_user['email']} editing submission {submission_id}")
        print(f"[AI EDITOR] Section: {edit_request.section_path}, Instruction: {edit_request.instruction}")

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

        print(f"[AI EDITOR] ✅ Edit suggestion generated (model: {result['model_used']}, cost: ${result['cost_estimate']:.6f})")

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
    except Exception as e:
        print(f"[ERROR] Edit generation error: {e}")
        import traceback
        traceback.print_exc()
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
        print(f"[AI EDITOR] User {current_user['email']} applying edit to submission {submission_id}")
        print(f"[AI EDITOR] Section: {apply_request.section_path}")

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

        print(f"[AI EDITOR] ✅ Edit applied successfully (total edits: {edit_count})")

        return ApplyEditResponse(
            success=True,
            updated_report=updated_report,
            edit_count=edit_count
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Apply edit error: {e}")
        import traceback
        traceback.print_exc()
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
        print(f"[PDF BACKGROUND] Starting PDF generation for submission {submission_id}")

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

        print(f"[PDF BACKGROUND] ✅ PDF generated successfully: {pdf_filename}")

    except Exception as e:
        print(f"[PDF BACKGROUND] ❌ PDF generation failed: {e}")
        import traceback
        traceback.print_exc()


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
        print(f"[AI EDITOR] User {current_user['email']} requesting PDF regeneration for submission {submission_id}")

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

        print(f"[AI EDITOR] ✅ PDF generation queued (background task)")

        return RegeneratePDFResponse(
            success=True,
            pdf_url=f"/api/admin/submissions/{submission_id}/export-pdf",
            message="PDF generation started in background. Use the export URL to download when ready."
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] PDF regeneration error: {e}")
        import traceback
        traceback.print_exc()
        return RegeneratePDFResponse(success=False, error=str(e))
