"""
Edit Tracker - Track user edits to auto-filled fields for learning
"""
from datetime import datetime
from typing import Optional, Dict, Any, List
import logging
from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

logger = logging.getLogger(__name__)


class EditTracker:
    """
    Tracks user edits to auto-filled fields and stores them for learning.

    Key Functions:
    - Store edit events with original/edited values
    - Mark suggestions as edited in database
    - Update field validation history
    - Provide edit analytics per source/field combination
    """

    def __init__(self, db_session: Optional[AsyncSession] = None):
        """Initialize edit tracker with optional database session."""
        self.db_session = db_session

    async def track_edit(
        self,
        session_id: str,
        field_name: str,
        original_value: str,
        edited_value: str,
        source: str,
        original_confidence: float,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Track a user edit to an auto-filled field.

        Args:
            session_id: Enrichment session identifier
            field_name: Name of the field that was edited
            original_value: Original auto-filled value
            edited_value: User's edited value
            source: Data source that provided original value
            original_confidence: Original confidence score
            user_id: Optional user identifier

        Returns:
            Dict containing edit record details
        """
        try:
            logger.info(
                f"Tracking edit for session {session_id}, field {field_name}, "
                f"source {source}"
            )

            # Get database session
            db = self.db_session or next(get_db())

            # 1. Mark suggestion as edited in auto_fill_suggestions table
            await self._mark_suggestion_edited(
                db=db,
                session_id=session_id,
                field_name=field_name,
                edited_value=edited_value,
                source=source
            )

            # 2. Update field validation history
            edit_record = await self._update_validation_history(
                db=db,
                session_id=session_id,
                field_name=field_name,
                original_value=original_value,
                edited_value=edited_value,
                source=source,
                original_confidence=original_confidence,
                user_id=user_id
            )

            # 3. Trigger learning update asynchronously
            await self._trigger_learning_update(
                field_name=field_name,
                source=source
            )

            logger.info(f"Edit tracked successfully for {field_name} from {source}")

            return {
                "success": True,
                "edit_record": edit_record,
                "session_id": session_id,
                "field_name": field_name,
                "source": source
            }

        except Exception as e:
            logger.error(f"Error tracking edit: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }

    async def _mark_suggestion_edited(
        self,
        db: AsyncSession,
        session_id: str,
        field_name: str,
        edited_value: str,
        source: str
    ):
        """Mark suggestion as edited in auto_fill_suggestions table."""
        try:
            query = """
                UPDATE auto_fill_suggestions
                SET was_edited = TRUE,
                    final_value = $1,
                    edited_at = $2
                WHERE session_id = $3
                    AND field_name = $4
                    AND source = $5
                    AND was_edited = FALSE
            """

            await db.execute(
                query,
                edited_value,
                datetime.utcnow(),
                session_id,
                field_name,
                source
            )
            await db.commit()

            logger.debug(
                f"Marked suggestion as edited: {field_name} from {source}"
            )

        except Exception as e:
            logger.error(f"Error marking suggestion as edited: {str(e)}")
            await db.rollback()
            raise

    async def _update_validation_history(
        self,
        db: AsyncSession,
        session_id: str,
        field_name: str,
        original_value: str,
        edited_value: str,
        source: str,
        original_confidence: float,
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """Update field validation history with edit event."""
        try:
            edit_record = {
                "session_id": session_id,
                "field_name": field_name,
                "original_value": original_value,
                "edited_value": edited_value,
                "source": source,
                "original_confidence": original_confidence,
                "edit_distance": self._calculate_edit_distance(
                    original_value,
                    edited_value
                ),
                "edit_type": self._classify_edit_type(
                    original_value,
                    edited_value
                ),
                "user_id": user_id,
                "created_at": datetime.utcnow()
            }

            query = """
                INSERT INTO field_validation_history (
                    session_id,
                    field_name,
                    original_value,
                    edited_value,
                    source,
                    original_confidence,
                    edit_distance,
                    edit_type,
                    user_id,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id
            """

            result = await db.execute(
                query,
                session_id,
                field_name,
                original_value,
                edited_value,
                source,
                original_confidence,
                edit_record["edit_distance"],
                edit_record["edit_type"],
                user_id,
                edit_record["created_at"]
            )

            edit_record["id"] = result.fetchone()[0]
            await db.commit()

            logger.debug(f"Created validation history record: {edit_record['id']}")

            return edit_record

        except Exception as e:
            logger.error(f"Error updating validation history: {str(e)}")
            await db.rollback()
            raise

    async def _trigger_learning_update(
        self,
        field_name: str,
        source: str
    ):
        """Trigger asynchronous learning update for field/source combination."""
        try:
            # Import here to avoid circular dependencies
            from app.services.enrichment.confidence_learner import ConfidenceLearner

            learner = ConfidenceLearner()
            await learner.update_confidence_for_source(
                field_name=field_name,
                source=source
            )

            logger.debug(
                f"Triggered learning update for {field_name} from {source}"
            )

        except Exception as e:
            logger.warning(
                f"Could not trigger learning update: {str(e)}. "
                "This will be updated in next batch run."
            )

    def _calculate_edit_distance(
        self,
        original: str,
        edited: str
    ) -> int:
        """
        Calculate Levenshtein distance between original and edited values.

        Returns:
            Edit distance as integer
        """
        if original == edited:
            return 0

        # Simple Levenshtein distance implementation
        if len(original) < len(edited):
            return self._calculate_edit_distance(edited, original)

        if len(edited) == 0:
            return len(original)

        previous_row = range(len(edited) + 1)
        for i, c1 in enumerate(original):
            current_row = [i + 1]
            for j, c2 in enumerate(edited):
                # j+1 instead of j since previous_row and current_row are one character longer
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    def _classify_edit_type(
        self,
        original: str,
        edited: str
    ) -> str:
        """
        Classify the type of edit made.

        Returns:
            Edit type: 'minor', 'major', 'complete_rewrite', 'correction'
        """
        if not original or not edited:
            return "complete_rewrite"

        edit_distance = self._calculate_edit_distance(original, edited)
        max_length = max(len(original), len(edited))

        if edit_distance == 0:
            return "no_change"

        # Calculate similarity ratio
        similarity = 1 - (edit_distance / max_length)

        if similarity > 0.9:
            return "minor"  # Typo correction, small tweak
        elif similarity > 0.7:
            return "correction"  # Moderate changes
        elif similarity > 0.4:
            return "major"  # Significant changes
        else:
            return "complete_rewrite"  # Completely different value

    async def get_edit_statistics(
        self,
        field_name: Optional[str] = None,
        source: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get edit statistics for analysis.

        Args:
            field_name: Optional field name filter
            source: Optional source filter
            days: Number of days to analyze (default 30)

        Returns:
            Dictionary containing edit statistics
        """
        try:
            db = self.db_session or next(get_db())

            # Build query with filters
            conditions = ["created_at >= NOW() - INTERVAL '%s days'" % days]
            params = []

            if field_name:
                conditions.append("field_name = $%d" % (len(params) + 1))
                params.append(field_name)

            if source:
                conditions.append("source = $%d" % (len(params) + 1))
                params.append(source)

            where_clause = " AND ".join(conditions)

            query = f"""
                SELECT
                    COUNT(*) as total_edits,
                    COUNT(DISTINCT session_id) as sessions_with_edits,
                    AVG(edit_distance) as avg_edit_distance,
                    COUNT(CASE WHEN edit_type = 'minor' THEN 1 END) as minor_edits,
                    COUNT(CASE WHEN edit_type = 'correction' THEN 1 END) as corrections,
                    COUNT(CASE WHEN edit_type = 'major' THEN 1 END) as major_edits,
                    COUNT(CASE WHEN edit_type = 'complete_rewrite' THEN 1 END) as complete_rewrites,
                    AVG(original_confidence) as avg_original_confidence
                FROM field_validation_history
                WHERE {where_clause}
            """

            result = await db.execute(query, *params)
            row = result.fetchone()

            return {
                "total_edits": row[0] or 0,
                "sessions_with_edits": row[1] or 0,
                "avg_edit_distance": float(row[2] or 0),
                "minor_edits": row[3] or 0,
                "corrections": row[4] or 0,
                "major_edits": row[5] or 0,
                "complete_rewrites": row[6] or 0,
                "avg_original_confidence": float(row[7] or 0),
                "field_name": field_name,
                "source": source,
                "days_analyzed": days
            }

        except Exception as e:
            logger.error(f"Error getting edit statistics: {str(e)}")
            return {
                "error": str(e),
                "total_edits": 0
            }

    async def get_most_edited_fields(
        self,
        limit: int = 10,
        days: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get fields with highest edit rates.

        Args:
            limit: Maximum number of fields to return
            days: Number of days to analyze

        Returns:
            List of fields sorted by edit rate
        """
        try:
            db = self.db_session or next(get_db())

            query = """
                SELECT
                    field_name,
                    source,
                    COUNT(*) as edit_count,
                    AVG(edit_distance) as avg_edit_distance,
                    AVG(original_confidence) as avg_original_confidence,
                    COUNT(CASE WHEN edit_type IN ('major', 'complete_rewrite') THEN 1 END) as significant_edits
                FROM field_validation_history
                WHERE created_at >= NOW() - INTERVAL '%s days'
                GROUP BY field_name, source
                ORDER BY edit_count DESC
                LIMIT $1
            """ % days

            result = await db.execute(query, limit)
            rows = result.fetchall()

            return [
                {
                    "field_name": row[0],
                    "source": row[1],
                    "edit_count": row[2],
                    "avg_edit_distance": float(row[3]),
                    "avg_original_confidence": float(row[4]),
                    "significant_edits": row[5],
                    "edit_rate_severity": "high" if row[5] > row[2] * 0.5 else "medium"
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting most edited fields: {str(e)}")
            return []
