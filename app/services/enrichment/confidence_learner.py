"""
Confidence Learner - Learn from user edits to improve confidence scoring
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import logging
import math
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db

logger = logging.getLogger(__name__)


class ConfidenceLearner:
    """
    Learns from user edit patterns to adjust confidence scores.

    Key Features:
    - Analyze edit rates per source/field combination
    - Apply learned adjustments to confidence scores
    - Update source performance metrics
    - Provide learning insights for analytics

    Algorithm:
    - If edit_rate > 30%: Reduce confidence for that source/field
    - If edit_rate < 5%: Increase confidence for that source/field
    - Formula: adjusted_confidence = base_confidence * (1 - edit_rate) * 1.2
    - Cap at 98% maximum (never 100%)
    """

    # Configuration constants
    HIGH_EDIT_THRESHOLD = 0.30  # 30% edit rate = reduce confidence
    LOW_EDIT_THRESHOLD = 0.05   # 5% edit rate = increase confidence
    MAX_CONFIDENCE = 0.98       # Never exceed 98%
    MIN_CONFIDENCE = 0.10       # Never go below 10%
    BOOST_MULTIPLIER = 1.2      # Boost for reliable sources
    PENALTY_MULTIPLIER = 0.7    # Penalty for unreliable sources
    MIN_SAMPLE_SIZE = 10        # Minimum suggestions needed for learning

    def __init__(self, db_session: Optional[AsyncSession] = None):
        """Initialize confidence learner with optional database session."""
        self.db_session = db_session

    async def update_confidence_for_source(
        self,
        field_name: str,
        source: str,
        lookback_days: int = 30
    ) -> Dict[str, Any]:
        """
        Update confidence score for a specific field/source combination.

        Args:
            field_name: Name of the field
            source: Data source name
            lookback_days: Days to analyze (default 30)

        Returns:
            Dictionary containing update results and insights
        """
        try:
            logger.info(
                f"Updating confidence for {field_name} from {source} "
                f"(lookback: {lookback_days} days)"
            )

            db = self.db_session or next(get_db())

            # 1. Calculate edit rate for this field/source combination
            edit_stats = await self._calculate_edit_rate(
                db=db,
                field_name=field_name,
                source=source,
                lookback_days=lookback_days
            )

            if edit_stats["total_suggestions"] < self.MIN_SAMPLE_SIZE:
                logger.info(
                    f"Insufficient data for {field_name}/{source}: "
                    f"{edit_stats['total_suggestions']} suggestions "
                    f"(need {self.MIN_SAMPLE_SIZE})"
                )
                return {
                    "updated": False,
                    "reason": "insufficient_data",
                    "sample_size": edit_stats["total_suggestions"],
                    "required_size": self.MIN_SAMPLE_SIZE
                }

            # 2. Calculate confidence adjustment
            adjustment = self._calculate_confidence_adjustment(
                edit_rate=edit_stats["edit_rate"],
                avg_edit_distance=edit_stats["avg_edit_distance"],
                significant_edit_rate=edit_stats["significant_edit_rate"]
            )

            # 3. Update enrichment_source_performance table
            update_result = await self._update_source_performance(
                db=db,
                field_name=field_name,
                source=source,
                adjustment=adjustment,
                edit_stats=edit_stats
            )

            # 4. Generate learning insights
            insights = self._generate_insights(
                field_name=field_name,
                source=source,
                edit_stats=edit_stats,
                adjustment=adjustment
            )

            logger.info(
                f"Confidence updated for {field_name}/{source}: "
                f"adjustment={adjustment['multiplier']:.2f}, "
                f"edit_rate={edit_stats['edit_rate']:.1%}"
            )

            return {
                "updated": True,
                "field_name": field_name,
                "source": source,
                "edit_stats": edit_stats,
                "adjustment": adjustment,
                "new_confidence": update_result["new_confidence"],
                "old_confidence": update_result["old_confidence"],
                "insights": insights
            }

        except Exception as e:
            logger.error(
                f"Error updating confidence for {field_name}/{source}: {str(e)}",
                exc_info=True
            )
            return {
                "updated": False,
                "error": str(e)
            }

    async def _calculate_edit_rate(
        self,
        db: AsyncSession,
        field_name: str,
        source: str,
        lookback_days: int
    ) -> Dict[str, Any]:
        """
        Calculate edit rate and statistics for field/source combination.

        Returns:
            Dictionary with edit_rate, total_suggestions, total_edits, etc.
        """
        try:
            # Query auto_fill_suggestions for this field/source
            query = """
                WITH suggestion_stats AS (
                    SELECT
                        COUNT(*) as total_suggestions,
                        COUNT(CASE WHEN was_edited THEN 1 END) as total_edits,
                        COUNT(CASE WHEN was_edited AND confidence_score > 0.8 THEN 1 END) as high_confidence_edits
                    FROM auto_fill_suggestions
                    WHERE field_name = $1
                        AND source = $2
                        AND created_at >= NOW() - INTERVAL '%s days'
                ),
                edit_stats AS (
                    SELECT
                        AVG(edit_distance) as avg_edit_distance,
                        COUNT(CASE WHEN edit_type IN ('major', 'complete_rewrite') THEN 1 END) as significant_edits,
                        COUNT(*) as total_validation_records
                    FROM field_validation_history
                    WHERE field_name = $1
                        AND source = $2
                        AND created_at >= NOW() - INTERVAL '%s days'
                )
                SELECT
                    s.total_suggestions,
                    s.total_edits,
                    s.high_confidence_edits,
                    e.avg_edit_distance,
                    e.significant_edits,
                    e.total_validation_records
                FROM suggestion_stats s
                CROSS JOIN edit_stats e
            """ % (lookback_days, lookback_days)

            result = await db.execute(query, field_name, source)
            row = result.fetchone()

            total_suggestions = row[0] or 0
            total_edits = row[1] or 0
            high_confidence_edits = row[2] or 0
            avg_edit_distance = float(row[3] or 0)
            significant_edits = row[4] or 0

            edit_rate = total_edits / total_suggestions if total_suggestions > 0 else 0
            significant_edit_rate = (
                significant_edits / total_edits if total_edits > 0 else 0
            )

            return {
                "total_suggestions": total_suggestions,
                "total_edits": total_edits,
                "edit_rate": edit_rate,
                "high_confidence_edits": high_confidence_edits,
                "avg_edit_distance": avg_edit_distance,
                "significant_edits": significant_edits,
                "significant_edit_rate": significant_edit_rate,
                "lookback_days": lookback_days
            }

        except Exception as e:
            logger.error(f"Error calculating edit rate: {str(e)}")
            raise

    def _calculate_confidence_adjustment(
        self,
        edit_rate: float,
        avg_edit_distance: float,
        significant_edit_rate: float
    ) -> Dict[str, Any]:
        """
        Calculate confidence adjustment based on edit patterns.

        Args:
            edit_rate: Percentage of suggestions that were edited (0-1)
            avg_edit_distance: Average Levenshtein distance of edits
            significant_edit_rate: Percentage of major/complete rewrites (0-1)

        Returns:
            Dictionary with multiplier, adjustment_type, and reasoning
        """
        # Base multiplier starts at 1.0 (no change)
        multiplier = 1.0
        adjustment_type = "neutral"
        reasoning = []

        # Factor 1: Overall edit rate
        if edit_rate > self.HIGH_EDIT_THRESHOLD:
            # High edit rate = reduce confidence
            penalty = 1 - ((edit_rate - self.HIGH_EDIT_THRESHOLD) / (1 - self.HIGH_EDIT_THRESHOLD))
            multiplier *= max(self.PENALTY_MULTIPLIER, penalty)
            adjustment_type = "penalty"
            reasoning.append(
                f"High edit rate ({edit_rate:.1%}) indicates unreliable data"
            )
        elif edit_rate < self.LOW_EDIT_THRESHOLD:
            # Low edit rate = increase confidence
            multiplier *= self.BOOST_MULTIPLIER
            adjustment_type = "boost"
            reasoning.append(
                f"Low edit rate ({edit_rate:.1%}) indicates reliable data"
            )

        # Factor 2: Significant edit rate (major rewrites)
        if significant_edit_rate > 0.5:
            # More than 50% of edits are major changes
            multiplier *= 0.85  # Additional 15% penalty
            reasoning.append(
                f"High significant edit rate ({significant_edit_rate:.1%}) "
                "indicates poor data quality"
            )

        # Factor 3: Average edit distance
        if avg_edit_distance > 10:
            # Large edits indicate poor initial values
            multiplier *= 0.90  # Additional 10% penalty
            reasoning.append(
                f"Large average edit distance ({avg_edit_distance:.1f}) "
                "indicates inaccurate suggestions"
            )
        elif avg_edit_distance < 2 and edit_rate > 0:
            # Small edits might be minor corrections, less severe
            multiplier *= 1.05  # Small 5% boost
            reasoning.append(
                f"Small average edit distance ({avg_edit_distance:.1f}) "
                "indicates minor corrections only"
            )

        return {
            "multiplier": multiplier,
            "adjustment_type": adjustment_type,
            "reasoning": reasoning,
            "edit_rate": edit_rate,
            "significant_edit_rate": significant_edit_rate,
            "avg_edit_distance": avg_edit_distance
        }

    async def _update_source_performance(
        self,
        db: AsyncSession,
        field_name: str,
        source: str,
        adjustment: Dict[str, Any],
        edit_stats: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update enrichment_source_performance table with learned adjustments.

        Returns:
            Dictionary with old and new confidence scores
        """
        try:
            # Get current confidence for this source/field
            query = """
                SELECT confidence_score, success_rate
                FROM enrichment_source_performance
                WHERE source = $1 AND field_name = $2
            """
            result = await db.execute(query, source, field_name)
            row = result.fetchone()

            if row:
                old_confidence = float(row[0])
                success_rate = float(row[1]) if row[1] else 0.5
            else:
                # No existing record, use defaults
                old_confidence = 0.70
                success_rate = 0.50

            # Apply adjustment with formula:
            # adjusted_confidence = base_confidence * multiplier
            new_confidence = old_confidence * adjustment["multiplier"]

            # Apply caps
            new_confidence = max(self.MIN_CONFIDENCE, min(self.MAX_CONFIDENCE, new_confidence))

            # Update success rate based on edit rate
            new_success_rate = 1 - edit_stats["edit_rate"]

            # Upsert into enrichment_source_performance
            upsert_query = """
                INSERT INTO enrichment_source_performance (
                    source,
                    field_name,
                    confidence_score,
                    success_rate,
                    total_attempts,
                    successful_fills,
                    learned_adjustment,
                    last_updated
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (source, field_name)
                DO UPDATE SET
                    confidence_score = $3,
                    success_rate = $4,
                    total_attempts = enrichment_source_performance.total_attempts + $5,
                    successful_fills = enrichment_source_performance.successful_fills + $6,
                    learned_adjustment = $7,
                    last_updated = $8
            """

            await db.execute(
                upsert_query,
                source,
                field_name,
                new_confidence,
                new_success_rate,
                edit_stats["total_suggestions"],
                edit_stats["total_suggestions"] - edit_stats["total_edits"],
                adjustment["multiplier"],
                datetime.utcnow()
            )
            await db.commit()

            logger.debug(
                f"Updated source performance: {source}/{field_name} "
                f"{old_confidence:.2%} -> {new_confidence:.2%}"
            )

            return {
                "old_confidence": old_confidence,
                "new_confidence": new_confidence,
                "old_success_rate": success_rate,
                "new_success_rate": new_success_rate
            }

        except Exception as e:
            logger.error(f"Error updating source performance: {str(e)}")
            await db.rollback()
            raise

    def _generate_insights(
        self,
        field_name: str,
        source: str,
        edit_stats: Dict[str, Any],
        adjustment: Dict[str, Any]
    ) -> List[str]:
        """
        Generate human-readable insights about learning.

        Returns:
            List of insight strings for analytics dashboard
        """
        insights = []

        # Overall assessment
        if adjustment["adjustment_type"] == "penalty":
            insights.append(
                f"⚠️ {source} {field_name} edited {edit_stats['edit_rate']:.0%} "
                f"→ confidence reduced to {adjustment['multiplier']:.0%}"
            )
        elif adjustment["adjustment_type"] == "boost":
            insights.append(
                f"✅ {source} {field_name} rarely edited ({edit_stats['edit_rate']:.0%}) "
                f"→ confidence increased by {(adjustment['multiplier'] - 1) * 100:.0%}%"
            )
        else:
            insights.append(
                f"ℹ️ {source} {field_name} has moderate edit rate "
                f"({edit_stats['edit_rate']:.0%}) → no adjustment"
            )

        # Specific issues
        if edit_stats["significant_edit_rate"] > 0.5:
            insights.append(
                f"🔴 {edit_stats['significant_edit_rate']:.0%} of edits are major rewrites "
                "- consider alternative data source"
            )

        if edit_stats["avg_edit_distance"] > 10:
            insights.append(
                f"📏 Large edit distance ({edit_stats['avg_edit_distance']:.1f}) "
                "indicates poor initial accuracy"
            )

        # Positive feedback
        if edit_stats["edit_rate"] < 0.05 and edit_stats["total_suggestions"] > 50:
            insights.append(
                f"⭐ Highly reliable source with {edit_stats['total_suggestions']} "
                f"suggestions and only {edit_stats['edit_rate']:.1%} edit rate"
            )

        # Add reasoning from adjustment
        insights.extend(adjustment["reasoning"])

        return insights

    async def batch_update_all_sources(
        self,
        lookback_days: int = 30,
        min_suggestions: int = 10
    ) -> Dict[str, Any]:
        """
        Batch update confidence scores for all field/source combinations.

        Args:
            lookback_days: Days to analyze
            min_suggestions: Minimum suggestions required for update

        Returns:
            Summary of batch update results
        """
        try:
            logger.info(f"Starting batch confidence update (lookback: {lookback_days} days)")

            db = self.db_session or next(get_db())

            # Get all field/source combinations with sufficient data
            query = """
                SELECT field_name, source, COUNT(*) as suggestion_count
                FROM auto_fill_suggestions
                WHERE created_at >= NOW() - INTERVAL '%s days'
                GROUP BY field_name, source
                HAVING COUNT(*) >= $1
                ORDER BY COUNT(*) DESC
            """ % lookback_days

            result = await db.execute(query, min_suggestions)
            combinations = result.fetchall()

            logger.info(f"Found {len(combinations)} field/source combinations to update")

            # Update each combination
            results = []
            for field_name, source, count in combinations:
                update_result = await self.update_confidence_for_source(
                    field_name=field_name,
                    source=source,
                    lookback_days=lookback_days
                )
                results.append(update_result)

            # Summarize results
            updated_count = sum(1 for r in results if r.get("updated"))
            boosted_count = sum(
                1 for r in results
                if r.get("adjustment", {}).get("adjustment_type") == "boost"
            )
            penalized_count = sum(
                1 for r in results
                if r.get("adjustment", {}).get("adjustment_type") == "penalty"
            )

            logger.info(
                f"Batch update complete: {updated_count} updated, "
                f"{boosted_count} boosted, {penalized_count} penalized"
            )

            return {
                "total_combinations": len(combinations),
                "updated_count": updated_count,
                "boosted_count": boosted_count,
                "penalized_count": penalized_count,
                "results": results,
                "lookback_days": lookback_days
            }

        except Exception as e:
            logger.error(f"Error in batch update: {str(e)}", exc_info=True)
            return {
                "error": str(e),
                "updated_count": 0
            }

    async def get_learning_insights_dashboard(
        self,
        days: int = 30,
        limit: int = 20
    ) -> Dict[str, Any]:
        """
        Get comprehensive learning insights for analytics dashboard.

        Returns:
            Dictionary with insights, top performers, problem areas, etc.
        """
        try:
            db = self.db_session or next(get_db())

            # Top performers (lowest edit rate)
            top_performers_query = """
                SELECT
                    s.field_name,
                    s.source,
                    COUNT(*) as suggestions,
                    COUNT(CASE WHEN s.was_edited THEN 1 END) as edits,
                    (COUNT(CASE WHEN s.was_edited THEN 1 END)::float / COUNT(*)) as edit_rate,
                    p.confidence_score
                FROM auto_fill_suggestions s
                LEFT JOIN enrichment_source_performance p
                    ON s.source = p.source AND s.field_name = p.field_name
                WHERE s.created_at >= NOW() - INTERVAL '%s days'
                GROUP BY s.field_name, s.source, p.confidence_score
                HAVING COUNT(*) >= 10
                ORDER BY edit_rate ASC
                LIMIT $1
            """ % days

            result = await db.execute(top_performers_query, limit)
            top_performers = [
                {
                    "field_name": row[0],
                    "source": row[1],
                    "suggestions": row[2],
                    "edits": row[3],
                    "edit_rate": float(row[4]),
                    "confidence": float(row[5]) if row[5] else 0.5
                }
                for row in result.fetchall()
            ]

            # Problem areas (highest edit rate)
            problem_areas_query = """
                SELECT
                    s.field_name,
                    s.source,
                    COUNT(*) as suggestions,
                    COUNT(CASE WHEN s.was_edited THEN 1 END) as edits,
                    (COUNT(CASE WHEN s.was_edited THEN 1 END)::float / COUNT(*)) as edit_rate,
                    p.confidence_score,
                    p.learned_adjustment
                FROM auto_fill_suggestions s
                LEFT JOIN enrichment_source_performance p
                    ON s.source = p.source AND s.field_name = p.field_name
                WHERE s.created_at >= NOW() - INTERVAL '%s days'
                GROUP BY s.field_name, s.source, p.confidence_score, p.learned_adjustment
                HAVING COUNT(*) >= 10
                ORDER BY edit_rate DESC
                LIMIT $1
            """ % days

            result = await db.execute(problem_areas_query, limit)
            problem_areas = [
                {
                    "field_name": row[0],
                    "source": row[1],
                    "suggestions": row[2],
                    "edits": row[3],
                    "edit_rate": float(row[4]),
                    "confidence": float(row[5]) if row[5] else 0.5,
                    "learned_adjustment": float(row[6]) if row[6] else 1.0
                }
                for row in result.fetchall()
            ]

            # Overall statistics
            overall_query = """
                SELECT
                    COUNT(DISTINCT field_name) as total_fields,
                    COUNT(DISTINCT source) as total_sources,
                    COUNT(*) as total_suggestions,
                    COUNT(CASE WHEN was_edited THEN 1 END) as total_edits,
                    AVG(CASE WHEN was_edited THEN 1 ELSE 0 END) as overall_edit_rate
                FROM auto_fill_suggestions
                WHERE created_at >= NOW() - INTERVAL '%s days'
            """ % days

            result = await db.execute(overall_query)
            row = result.fetchone()

            overall_stats = {
                "total_fields": row[0] or 0,
                "total_sources": row[1] or 0,
                "total_suggestions": row[2] or 0,
                "total_edits": row[3] or 0,
                "overall_edit_rate": float(row[4] or 0)
            }

            return {
                "top_performers": top_performers,
                "problem_areas": problem_areas,
                "overall_stats": overall_stats,
                "days_analyzed": days,
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error generating learning insights: {str(e)}")
            return {
                "error": str(e),
                "top_performers": [],
                "problem_areas": []
            }
