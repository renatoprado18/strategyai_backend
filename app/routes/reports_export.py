"""
Report Export Routes - PDF and Markdown Export

This module contains routes for:
- Exporting reports as PDF
- Exporting reports as Markdown
- Downloading markdown editing instructions
"""
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
from datetime import datetime
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Import database functions
from app.core.database import get_submission

# Import auth dependency
from app.routes.auth import RequireAuth

# Import services
from app.services.pdf_generator import generate_pdf_from_report
from app.services.markdown_generator import generate_markdown_from_report

# Initialize router
router = APIRouter()


# ============================================================================
# PDF EXPORT
# ============================================================================

@router.get("/submissions/{submission_id}/export-pdf",
    summary="Export Report as PDF",
    description="""
    Export completed analysis report as professional PDF document (Admin only).

    **Features:**
    - Production-grade PDF with proper formatting
    - Professional styling with company branding
    - Automatic page breaks and section spacing
    - Embedded fonts for consistent rendering
    - Client-ready output

    **PDF Contents:**
    1. **Executive Summary**
       - Company overview
       - Business challenge
       - Key findings snapshot

    2. **Strategic Diagnosis (SWOT)**
       - Strengths analysis
       - Weaknesses identification
       - Opportunities discovery
       - Threats assessment

    3. **Market Analysis (PESTEL)**
       - Political factors
       - Economic trends
       - Social dynamics
       - Technological landscape
       - Environmental considerations
       - Legal requirements

    4. **Identified Opportunities**
       - Prioritized opportunity list
       - Market positioning insights
       - Growth recommendations

    5. **Priority Recommendations**
       - Actionable strategic recommendations
       - Implementation priority order
       - Expected impact analysis

    6. **Proposed OKRs**
       - Quarterly objectives
       - Key results with metrics
       - Tracking guidelines

    **Version Selection:**
    - Uses `edited_json` if report has been edited
    - Falls back to `report_json` for original analysis
    - Includes edit metadata in document footer

    **File Naming:**
    Format: `relatorio-estrategico-{company}-{date}.pdf`
    Example: `relatorio-estrategico-TechCorp-2025-01-26.pdf`

    **Caching:**
    - Cache-Control: 5 minutes (private)
    - Regenerate only if report edited
    - Instant download from cache

    **Authentication:**
    - Requires valid JWT token in Authorization header
    - Admin privileges required

    **Example:**
    ```bash
    curl -X GET https://api.example.com/api/admin/submissions/42/export-pdf \\
      -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \\
      -o report.pdf
    ```

    **Python Example:**
    ```python
    import requests

    response = requests.get(
        "https://api.example.com/api/admin/submissions/42/export-pdf",
        headers={"Authorization": f"Bearer {token}"}
    )

    with open("report.pdf", "wb") as f:
        f.write(response.content)
    ```
    """,
    responses={
        200: {
            "description": "PDF generated and downloaded successfully",
            "content": {
                "application/pdf": {
                    "example": "Binary PDF content"
                }
            }
        },
        404: {
            "description": "Submission not found or report not generated",
            "content": {
                "application/json": {
                    "examples": {
                        "not_found": {
                            "summary": "Submission not found",
                            "value": {"success": False, "error": "Submission 42 not found"}
                        },
                        "no_report": {
                            "summary": "Report not yet generated",
                            "value": {"success": False, "error": "Report not yet generated"}
                        }
                    }
                }
            }
        }
    })
async def export_submission_pdf(
    submission_id: int,
    current_user: dict = RequireAuth,
):
    """Export report as professional PDF - uses edited version if available"""
    try:
        from fastapi.responses import Response
        from app.services.pdf_generator import generate_pdf_from_report

        logger.info(f"[AUTH] User {current_user['email']} exporting PDF for submission {submission_id}")

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
        logger.info(f"[PDF] Generating PDF for submission {submission_id}...")
        pdf_bytes = generate_pdf_from_report(submission_data, report_json)

        if not pdf_bytes or len(pdf_bytes) == 0:
            logger.error(f"[ERROR] PDF generation returned empty bytes!")
            return {"success": False, "error": "PDF generation failed - empty output"}

        logger.info(f"[PDF] PDF generated successfully ({len(pdf_bytes)} bytes)")

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

    except json.JSONDecodeError as e:
        logger.error(f"[ERROR] Invalid JSON in report data: {e}", exc_info=True)
        return {"success": False, "error": "Invalid report JSON format"}
    except FileNotFoundError as e:
        logger.error(f"[ERROR] Required file not found: {e}", exc_info=True)
        return {"success": False, "error": "Required file not found"}
    except Exception as e:
        # Catch-all for unexpected errors (database, PDF generation, etc.)
        logger.exception(f"[ERROR] PDF export error: {e}")
        return {"success": False, "error": str(e)}


# ============================================================================
# MARKDOWN EXPORT
# ============================================================================

@router.get("/submissions/{submission_id}/export-markdown")
async def export_submission_markdown(
    submission_id: int,
    current_user: dict = RequireAuth,
):
    """
    Export submission report as Markdown (Protected Admin endpoint)

    Generates clean, editable markdown from report JSON.
    Markdown can be edited in any text editor and re-uploaded.

    Requires valid JWT token in Authorization header
    Returns markdown file (.md)
    """
    try:
        logger.info(f"[MARKDOWN] User {current_user['email']} exporting markdown for submission {submission_id}")

        # Get submission
        submission = await get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Use edited_json if available, otherwise report_json
        report_json_str = submission.get('edited_json') or submission.get('report_json')
        if not report_json_str:
            raise HTTPException(status_code=400, detail="Report not yet generated")

        # Parse report JSON
        try:
            report_json = json.loads(report_json_str)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid report JSON")

        # Build submission data for markdown generator
        submission_data = {
            "id": submission_id,
            "company": submission.get("company", ""),
            "industry": submission.get("industry", ""),
            "website": submission.get("website", ""),
            "challenge": submission.get("challenge", ""),
            "name": submission.get("name", ""),
            "updated_at": submission.get("last_edited_at") or submission.get("updated_at", "")
        }

        # Generate markdown
        logger.info(f"[MARKDOWN] Generating markdown for submission {submission_id}...")
        markdown_content = generate_markdown_from_report(submission_data, report_json)

        if not markdown_content:
            raise HTTPException(status_code=500, detail="Markdown generation failed - empty output")

        logger.info(f"[MARKDOWN] Markdown generated successfully ({len(markdown_content)} characters)")

        # Create filename
        company_slug = submission['company'].replace(' ', '-').lower()
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"analise-estrategica-{company_slug}-{date_str}.md"

        # Return markdown file
        return Response(
            content=markdown_content,
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Type": "text/markdown; charset=utf-8",
            }
        )

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        logger.error(f"[ERROR] Invalid JSON in report data: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Invalid report JSON format")
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"[ERROR] Markdown export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-instructions")
async def export_markdown_instructions(current_user: dict = RequireAuth):
    """
    Download markdown editing instructions (Protected Admin endpoint)

    Returns Portuguese instruction file explaining how to edit markdown reports.
    Includes:
    - Markdown syntax guide
    - How to use with ChatGPT
    - Upload instructions
    - Troubleshooting tips

    Requires valid JWT token in Authorization header
    """
    try:
        logger.info(f"[MARKDOWN] User {current_user['email']} downloading instruction guide")

        # Path to instruction file
        instruction_path = Path("app/static/COMO_EDITAR.md")

        if not instruction_path.exists():
            raise HTTPException(status_code=404, detail="Instruction file not found")

        # Return instruction file
        return FileResponse(
            path=str(instruction_path),
            media_type="text/markdown; charset=utf-8",
            headers={
                "Content-Disposition": 'attachment; filename="COMO_EDITAR.md"',
            }
        )

    except HTTPException:
        raise
    except FileNotFoundError as e:
        logger.error(f"[ERROR] Instruction file not found: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail="Instruction file not found")
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"[ERROR] Instructions export error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
