"""
Chat Routes for AI-powered report interaction

Provides endpoints for admins to chat with AI about generated reports,
get chat history, and access quick prompt suggestions.
"""

from fastapi import APIRouter, HTTPException, Request, Depends
from datetime import datetime, timezone
import json
from typing import Dict, Any

from app.core.database import (
    get_submission,
    update_submission_status,
)
from app.services.ai.chat import send_chat_message, get_quick_prompts
from app.routes.auth import RequireAuth

# Initialize router with prefix
router = APIRouter(prefix="/api/admin")


@router.post("/submissions/{submission_id}/chat")
async def chat_with_report(
    submission_id: int,
    request: Request,
    current_user: dict = RequireAuth,
):
    """
    Chat with AI about a specific report (Protected Admin endpoint)

    Send a message and get AI response with full context about the analysis.

    Request body:
    {
        "message": str,           # User's question
        "model": str (optional)   # "haiku" (fast) or "sonnet" (quality), default haiku
    }

    Response:
    {
        "success": bool,
        "message": str,           # AI response
        "model_used": str,
        "tokens_used": int,
        "timestamp": str,
        "chat_history": list      # Updated history
    }

    Requires valid JWT token in Authorization header
    """
    try:
        print(f"[AUTH] User {current_user['email']} chatting about submission {submission_id}")

        # Get submission
        submission = await get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        if submission["status"] != "completed":
            raise HTTPException(status_code=400, detail="Can only chat about completed analyses")

        # Parse request body
        body = await request.json()
        user_message = body.get("message", "").strip()
        model_pref = body.get("model", "haiku")

        if not user_message:
            raise HTTPException(status_code=400, detail="Message cannot be empty")

        # Select model
        model_map = {
            "haiku": "claude-3-5-haiku-20241022",
            "sonnet": "claude-3-5-sonnet-20241022"
        }
        model = model_map.get(model_pref, "claude-3-5-haiku-20241022")

        # Parse report and data quality
        try:
            report_data = json.loads(submission.get("report_json", "{}"))
            data_quality = json.loads(submission.get("data_quality_json", "{}")) if submission.get("data_quality_json") else None
        except:
            raise HTTPException(status_code=500, detail="Failed to parse report data")

        # Get existing chat history
        chat_history = []
        try:
            if submission.get("chat_history"):
                stored_history = json.loads(submission["chat_history"])
                # Extract just role and content for API
                chat_history = [{"role": msg["role"], "content": msg["content"]} for msg in stored_history]
        except:
            chat_history = []

        # Send message to AI
        result = await send_chat_message(
            submission_data=submission,
            report_data=report_data,
            data_quality=data_quality,
            chat_history=chat_history,
            user_message=user_message,
            model=model
        )

        if not result.get("success", False):
            raise HTTPException(status_code=500, detail=result.get("error", "AI chat failed"))

        # Build updated chat history
        new_history = chat_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": result["message"]}
        ]

        # Store chat history in database
        await update_submission_status(
            submission_id=submission_id,
            status=submission["status"],  # Keep existing status
            report_json=submission.get("report_json"),  # Keep existing report
            data_quality_json=submission.get("data_quality_json"),  # Keep existing quality
            processing_metadata=json.dumps({
                **(json.loads(submission.get("processing_metadata", "{}")) if submission.get("processing_metadata") else {}),
                "chat_history": new_history,  # Update chat history
                "last_chat_at": datetime.now(timezone.utc).isoformat()
            }),
        )

        print(f"[OK] Chat message processed for submission {submission_id}")

        return {
            "success": True,
            "message": result["message"],
            "model_used": result["model_used"],
            "tokens_used": result["tokens_used"],
            "timestamp": result["timestamp"],
            "chat_history": new_history
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Chat error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/submissions/{submission_id}/chat/history")
async def get_chat_history(
    submission_id: int,
    current_user: dict = RequireAuth,
):
    """
    Get chat history for a submission (Protected Admin endpoint)

    Returns full chat history with timestamps.

    Requires valid JWT token in Authorization header
    """
    try:
        print(f"[AUTH] User {current_user['email']} fetching chat history for submission {submission_id}")

        # Get submission
        submission = await get_submission(submission_id)
        if not submission:
            raise HTTPException(status_code=404, detail="Submission not found")

        # Extract chat history
        chat_history = []
        try:
            if submission.get("chat_history"):
                chat_history = json.loads(submission["chat_history"])
        except:
            chat_history = []

        return {
            "success": True,
            "submission_id": submission_id,
            "chat_history": chat_history
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Get chat history error: {e}")
        return {
            "success": False,
            "error": str(e)
        }


@router.get("/chat/quick-prompts")
async def get_chat_quick_prompts(
    current_user: dict = RequireAuth,
):
    """
    Get quick prompt suggestions for common questions (Protected Admin endpoint)

    Returns list of suggested questions to ask about reports.

    Requires valid JWT token in Authorization header
    """
    return {
        "success": True,
        "prompts": get_quick_prompts()
    }
