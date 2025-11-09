"""
Report Import Routes - Markdown Import and Parsing

This module contains routes for:
- Importing edited markdown files
- Parsing markdown to JSON
- Generating PDF from imported markdown
"""
from fastapi import APIRouter, HTTPException, Response, UploadFile, File
from datetime import datetime, timezone
import json
import logging

logger = logging.getLogger(__name__)

# Import database functions
from app.core.database import get_submission, update_submission_status

# Import auth dependency
from app.routes.auth import RequireAuth

# Import services
from app.services.pdf_generator import generate_pdf_from_report
from app.services.markdown_parser import parse_markdown_to_report, MarkdownParseError

# Initialize router
router = APIRouter()


# ============================================================================
# MARKDOWN IMPORT
# ============================================================================

@router.post("/submissions/{submission_id}/import-markdown-and-pdf")
async def import_markdown_and_generate_pdf(
    submission_id: int,
    file: UploadFile = File(...),
    current_user: dict = RequireAuth,
):
    """
    Import edited markdown and generate PDF (Protected Admin endpoint)

    Workflow:
    1. Parse uploaded markdown file
    2. Validate structure
    3. Update edited_json in database
    4. Generate PDF from updated JSON
    5. Return PDF for download

    This is the "quick workflow" - user uploads markdown and immediately gets PDF.

    Requires valid JWT token in Authorization header
    Returns PDF file
    """
    try:
        logger.info(f"[MARKDOWN] User {current_user['email']} importing markdown for submission {submission_id}")

        # Validate file type
        if not file.filename.endswith('.md'):
            raise HTTPException(status_code=400, detail="File must be a .md (markdown) file")

        # Read markdown content
        markdown_content = await file.read()
        markdown_text = markdown_content.decode('utf-8')

        logger.info(f"[MARKDOWN] Received markdown file: {file.filename} ({len(markdown_text)} characters)")

        # Parse markdown to JSON
        try:
            report_json, warnings = parse_markdown_to_report(markdown_text)
            logger.info(f"[MARKDOWN] Parsed successfully with {len(warnings)} warnings")

            if warnings:
                for warning in warnings:
                    logger.warning(f"[MARKDOWN WARNING] {warning}")

        except MarkdownParseError as e:
            logger.error(f"[MARKDOWN ERROR] Parse failed: {e}")
            raise HTTPException(status_code=400, detail=f"Markdown parsing failed: {str(e)}")

        # Get submission
        submission = await get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Update edited_json in database
        from app.core.database import update_submission_status

        # Increment edit count
        current_edit_count = submission.get('edit_count', 0)

        await update_submission_status(
            submission_id=submission_id,
            status=submission['status'],  # Keep existing status
            report_json=submission.get('report_json'),  # Keep original
            data_quality_json=submission.get('data_quality_json'),  # Keep existing
            processing_metadata=submission.get('processing_metadata'),  # Keep existing
            edited_json=json.dumps(report_json),  # Update with parsed markdown
            edit_count=current_edit_count + 1,
            last_edited_at=datetime.now(timezone.utc).isoformat()
        )

        logger.info(f"[MARKDOWN] Updated database with parsed report (edit #{current_edit_count + 1})")

        # Build submission data for PDF generation
        submission_data = {
            "id": submission_id,
            "company": submission.get("company", ""),
            "industry": submission.get("industry", ""),
            "website": submission.get("website", ""),
            "challenge": submission.get("challenge", ""),
            "name": submission.get("name", ""),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        # Generate PDF from updated JSON
        logger.info(f"[MARKDOWN] Generating PDF from imported markdown...")
        pdf_bytes = generate_pdf_from_report(submission_data, report_json)

        if not pdf_bytes or len(pdf_bytes) == 0:
            raise HTTPException(status_code=500, detail="PDF generation failed after markdown import")

        logger.info(f"[MARKDOWN] PDF generated successfully ({len(pdf_bytes)} bytes)")

        # Create filename
        company_slug = submission['company'].replace(' ', '-').lower()
        date_str = datetime.now().strftime('%Y-%m-%d')
        filename = f"relatorio-editado-{company_slug}-{date_str}.pdf"

        # Return PDF
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_bytes)),
                "X-Markdown-Warnings": str(len(warnings)),
            }
        )

    except HTTPException:
        raise
    except UnicodeDecodeError as e:
        logger.error(f"[ERROR] Invalid file encoding (must be UTF-8): {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="File must be UTF-8 encoded")
    except json.JSONDecodeError as e:
        logger.error(f"[ERROR] Invalid JSON generated from markdown: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail="Failed to convert markdown to valid JSON")
    except Exception as e:
        # Catch-all for database errors, PDF generation, or unexpected issues
        logger.exception(f"[ERROR] Markdown import error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
