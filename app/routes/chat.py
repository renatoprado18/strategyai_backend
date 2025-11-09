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


@router.post("/submissions/{submission_id}/chat",
    summary="Chat with AI about Report",
    description="""
    Interactive AI chat interface for report analysis and refinement (Admin only).

    **Features:**
    - Context-aware AI chat with full report knowledge
    - Persistent chat history stored per submission
    - Model selection (fast or quality)
    - Token usage tracking
    - Instant responses

    **Available Models:**
    - **haiku** (default): Claude 3.5 Haiku - Fast responses (< 2s), lower cost
    - **sonnet**: Claude 3.5 Sonnet - High quality, deeper analysis (3-5s)

    **Use Cases:**
    - Ask clarifying questions about analysis
    - Request additional insights
    - Explore specific report sections
    - Get recommendations refinement
    - Understand data quality concerns

    **Context Provided to AI:**
    - Complete analysis report
    - Data quality metrics
    - Submission details (company, industry, challenge)
    - Previous chat history
    - Source data references

    **Request Body:**
    ```json
    {
      "message": "What are the main competitive threats identified?",
      "model": "haiku"  // Optional: "haiku" or "sonnet"
    }
    ```

    **Response Format:**
    ```json
    {
      "success": true,
      "message": "Based on the analysis, I identified 3 main competitive threats...",
      "model_used": "claude-3-5-haiku-20241022",
      "tokens_used": 542,
      "timestamp": "2025-01-26T10:35:00Z",
      "chat_history": [...]
    }
    ```

    **Chat History:**
    - Automatically persisted in database
    - Included in all subsequent requests for context
    - Viewable via `/chat/history` endpoint
    - Cleared when submission is reprocessed

    **Cost Estimation:**
    - Haiku: ~$0.001 per message
    - Sonnet: ~$0.005 per message
    - Token usage varies by message length

    **Example Questions:**
    - "Summarize the top 3 opportunities"
    - "What are the risk mitigation strategies?"
    - "How reliable is the competitive intelligence?"
    - "Explain the PESTEL analysis in simple terms"
    - "What OKRs should we prioritize first?"

    **Authentication:**
    - Requires valid JWT token in Authorization header
    - Admin privileges required

    **Example:**
    ```bash
    curl -X POST https://api.example.com/api/admin/submissions/42/chat \\
      -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \\
      -H "Content-Type: application/json" \\
      -d '{
        "message": "What are the key findings?",
        "model": "haiku"
      }'
    ```
    """,
    responses={
        200: {
            "description": "Chat message processed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "message": "Based on the analysis, the key findings include...",
                        "model_used": "claude-3-5-haiku-20241022",
                        "tokens_used": 542,
                        "timestamp": "2025-01-26T10:35:00Z",
                        "chat_history": [
                            {"role": "user", "content": "What are the key findings?"},
                            {"role": "assistant", "content": "Based on the analysis..."}
                        ]
                    }
                }
            }
        },
        400: {
            "description": "Invalid request",
            "content": {
                "application/json": {
                    "examples": {
                        "empty_message": {
                            "summary": "Empty message",
                            "value": {"detail": "Message cannot be empty"}
                        },
                        "incomplete_analysis": {
                            "summary": "Analysis not completed",
                            "value": {"detail": "Can only chat about completed analyses"}
                        }
                    }
                }
            }
        }
    })
async def chat_with_report(
    submission_id: int,
    request: Request,
    current_user: dict = RequireAuth,
):
    """Chat with AI about report - context-aware chat with persistent history"""
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
