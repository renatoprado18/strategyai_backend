"""
User action endpoints for admin dashboard submission management.

These endpoints allow administrators to update submission statuses through
various user-triggered actions like marking as reviewed, sending to client,
archiving, and restoring submissions.
"""
from fastapi import APIRouter, HTTPException, status
from typing import Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr
from app.routes.auth import RequireAuth
from app.core.database import update_submission_processing_state, get_submission

# Create router with admin prefix
router = APIRouter(prefix="/api/admin", tags=["user_actions"])


# ============================================================================
# REQUEST MODELS
# ============================================================================

class SendToClientRequest(BaseModel):
    """Request model for sending submission to client"""
    client_email: EmailStr
    client_name: Optional[str] = None


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

async def update_submission_with_timestamps(
    submission_id: int,
    user_status: str,
    additional_fields: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Update submission user_status and additional fields with timestamps.

    Args:
        submission_id: ID of the submission to update
        user_status: New user status to set
        additional_fields: Additional fields to update in the database

    Returns:
        Updated submission data

    Raises:
        HTTPException: If submission not found or update fails
    """
    # First check if submission exists
    submission = await get_submission(submission_id)
    if not submission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Submission {submission_id} not found"
        )

    # Prepare update data
    from app.core.supabase import supabase_service

    update_data = {
        "user_status": user_status,
        "updated_at": datetime.utcnow().isoformat()
    }

    # Add any additional fields
    if additional_fields:
        update_data.update(additional_fields)

    try:
        # Update the submission
        response = supabase_service.table("submissions").update(update_data).eq("id", submission_id).execute()

        if not response.data:
            raise Exception(f"Failed to update submission {submission_id}")

        # Also update processing_state for backward compatibility
        # This ensures the old 'status' field is kept in sync
        old_status = submission.get("status", "pending")
        old_user_status = submission.get("user_status", "submitted")

        result = response.data[0] if response.data else None

        # Log the action
        print(f"[USER_ACTION] Submission {submission_id}: "
              f"user_status '{old_user_status}' → '{user_status}', "
              f"old_status='{old_status}'")

        return result

    except Exception as e:
        print(f"[ERROR] Failed to update submission {submission_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update submission: {str(e)}"
        )


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.post("/submissions/{submission_id}/mark-reviewed")
async def mark_submission_reviewed(
    submission_id: int,
    current_user: dict = RequireAuth
) -> Dict[str, Any]:
    """
    Mark a submission as reviewed.

    Updates the user_status to 'reviewed' to indicate an admin has reviewed
    the submission and its generated report.

    Args:
        submission_id: ID of the submission to mark as reviewed
        current_user: Authenticated user (injected by RequireAuth)

    Returns:
        Success response with updated submission data

    Requires:
        Valid JWT token in Authorization header
    """
    try:
        print(f"[AUTH] User {current_user['email']} marking submission {submission_id} as reviewed")

        # Update submission
        updated_submission = await update_submission_with_timestamps(
            submission_id=submission_id,
            user_status="reviewed"
        )

        return {
            "success": True,
            "data": {
                "submission_id": submission_id,
                "user_status": updated_submission.get("user_status"),
                "status": updated_submission.get("status"),  # Backward compatibility
                "updated_at": updated_submission.get("updated_at"),
                "message": "Submission marked as reviewed"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Mark reviewed error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/submissions/{submission_id}/send-to-client")
async def send_submission_to_client(
    submission_id: int,
    request: SendToClientRequest,
    current_user: dict = RequireAuth
) -> Dict[str, Any]:
    """
    Mark a submission as sent to client.

    Updates the user_status to 'sent_to_client' and records the client email
    and timestamp when the report was sent.

    Args:
        submission_id: ID of the submission to mark as sent
        request: Client email and optional name
        current_user: Authenticated user (injected by RequireAuth)

    Returns:
        Success response with updated submission data

    Requires:
        Valid JWT token in Authorization header
    """
    try:
        print(f"[AUTH] User {current_user['email']} sending submission {submission_id} to client {request.client_email}")

        # Prepare additional fields
        additional_fields = {
            "sent_to_client_at": datetime.utcnow().isoformat(),
            "sent_to_client_email": request.client_email
        }

        if request.client_name:
            additional_fields["sent_to_client_name"] = request.client_name

        # Update submission
        updated_submission = await update_submission_with_timestamps(
            submission_id=submission_id,
            user_status="sent_to_client",
            additional_fields=additional_fields
        )

        return {
            "success": True,
            "data": {
                "submission_id": submission_id,
                "user_status": updated_submission.get("user_status"),
                "status": updated_submission.get("status"),  # Backward compatibility
                "sent_to_client_at": updated_submission.get("sent_to_client_at"),
                "sent_to_client_email": updated_submission.get("sent_to_client_email"),
                "sent_to_client_name": updated_submission.get("sent_to_client_name"),
                "updated_at": updated_submission.get("updated_at"),
                "message": f"Submission marked as sent to {request.client_email}"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Send to client error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/submissions/{submission_id}/archive")
async def archive_submission(
    submission_id: int,
    current_user: dict = RequireAuth
) -> Dict[str, Any]:
    """
    Archive a submission.

    Updates the user_status to 'archived' and records the archive timestamp.
    Archived submissions are typically hidden from the main dashboard view.

    Args:
        submission_id: ID of the submission to archive
        current_user: Authenticated user (injected by RequireAuth)

    Returns:
        Success response with updated submission data

    Requires:
        Valid JWT token in Authorization header
    """
    try:
        print(f"[AUTH] User {current_user['email']} archiving submission {submission_id}")

        # Update submission
        updated_submission = await update_submission_with_timestamps(
            submission_id=submission_id,
            user_status="archived",
            additional_fields={
                "archived_at": datetime.utcnow().isoformat()
            }
        )

        return {
            "success": True,
            "data": {
                "submission_id": submission_id,
                "user_status": updated_submission.get("user_status"),
                "status": updated_submission.get("status"),  # Backward compatibility
                "archived_at": updated_submission.get("archived_at"),
                "updated_at": updated_submission.get("updated_at"),
                "message": "Submission archived successfully"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Archive submission error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.post("/submissions/{submission_id}/restore")
async def restore_submission(
    submission_id: int,
    current_user: dict = RequireAuth
) -> Dict[str, Any]:
    """
    Restore an archived submission.

    Updates the user_status back to 'ready' (or previous state before archiving)
    and clears the archived_at timestamp. This makes the submission visible
    in the main dashboard view again.

    Args:
        submission_id: ID of the submission to restore
        current_user: Authenticated user (injected by RequireAuth)

    Returns:
        Success response with updated submission data

    Requires:
        Valid JWT token in Authorization header
    """
    try:
        print(f"[AUTH] User {current_user['email']} restoring submission {submission_id}")

        # Update submission - restore to 'ready' status
        updated_submission = await update_submission_with_timestamps(
            submission_id=submission_id,
            user_status="ready",
            additional_fields={
                "archived_at": None  # Clear archived timestamp
            }
        )

        return {
            "success": True,
            "data": {
                "submission_id": submission_id,
                "user_status": updated_submission.get("user_status"),
                "status": updated_submission.get("status"),  # Backward compatibility
                "archived_at": updated_submission.get("archived_at"),
                "updated_at": updated_submission.get("updated_at"),
                "message": "Submission restored successfully"
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Restore submission error: {e}")
        return {
            "success": False,
            "error": str(e)
        }
