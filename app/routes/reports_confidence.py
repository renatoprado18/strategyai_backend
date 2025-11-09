"""
Report Confidence Scoring Routes

This module contains routes for:
- Calculating confidence scores for reports
- Providing detailed score breakdowns
- Updating submission metadata with confidence metrics
"""
from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
import json

# Import database functions
from app.core.database import get_submission, update_submission_status

# Import auth dependency
from app.routes.auth import RequireAuth

# Import services
from app.services.analysis.confidence_scorer import calculate_confidence_score

# Initialize router
router = APIRouter()


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
