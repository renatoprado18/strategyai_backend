"""
Submission Repository
Domain-specific repository for managing submission records
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging

from app.repositories.supabase_repository import SupabaseRepository
from app.core.exceptions import DatabaseError, ResourceNotFound

logger = logging.getLogger(__name__)


class SubmissionRepository(SupabaseRepository):
    """
    Repository for submissions table

    Provides domain-specific queries and operations for submissions.
    Extends base Supabase repository with business logic methods.
    """

    def __init__(self):
        super().__init__("submissions")

    async def get_by_email(self, email: str) -> List[Dict[str, Any]]:
        """
        Get all submissions for a specific email

        Args:
            email: User email

        Returns:
            List of submissions

        Raises:
            DatabaseError: If query fails
        """
        try:
            return await self.find({"email": email})
        except DatabaseError:
            raise

    async def get_by_status(
        self,
        status: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get submissions by status

        Args:
            status: Submission status (pending, processing, completed, failed)
            limit: Maximum records to return

        Returns:
            List of submissions

        Raises:
            DatabaseError: If query fails
        """
        try:
            query = self.client.table(self.table_name).select("*").eq("status", status)

            if limit:
                query = query.limit(limit)

            query = query.order("created_at", desc=True)

            response = query.execute()
            self._log_operation("get_by_status", True)

            return response.data if response.data else []

        except Exception as e:
            self._log_operation("get_by_status", False, error=e)
            raise DatabaseError(f"Failed to get submissions by status: {str(e)}")

    async def get_pending_submissions(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all pending submissions for processing

        Args:
            limit: Maximum records to return

        Returns:
            List of pending submissions

        Raises:
            DatabaseError: If query fails
        """
        return await self.get_by_status("pending", limit=limit)

    async def get_recent_by_ip(
        self,
        ip_address: str,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get recent submissions from an IP address

        Useful for rate limiting and abuse detection.

        Args:
            ip_address: IP address
            hours: Look back period in hours

        Returns:
            List of recent submissions

        Raises:
            DatabaseError: If query fails
        """
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
            cutoff_str = cutoff_time.isoformat()

            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("ip_address", ip_address)
                .gte("created_at", cutoff_str)
                .order("created_at", desc=True)
                .execute()
            )

            self._log_operation("get_recent_by_ip", True)

            return response.data if response.data else []

        except Exception as e:
            self._log_operation("get_recent_by_ip", False, error=e)
            raise DatabaseError(f"Failed to get recent submissions by IP: {str(e)}")

    async def update_status(
        self,
        submission_id: str,
        status: str,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update submission status

        Args:
            submission_id: Submission ID
            status: New status
            error_message: Optional error message for failed status

        Returns:
            Updated submission

        Raises:
            ResourceNotFound: If submission not found
            DatabaseError: If update fails
        """
        update_data = {"status": status}

        if error_message:
            update_data["error"] = error_message

        if status == "completed":
            update_data["completed_at"] = datetime.utcnow().isoformat()
        elif status == "failed":
            update_data["failed_at"] = datetime.utcnow().isoformat()

        return await self.update(submission_id, update_data)

    async def update_report(
        self,
        submission_id: str,
        report_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update submission report data

        Args:
            submission_id: Submission ID
            report_data: Complete report data

        Returns:
            Updated submission

        Raises:
            ResourceNotFound: If submission not found
            DatabaseError: If update fails
        """
        return await self.update(submission_id, {"report": report_data})

    async def update_confidence_score(
        self,
        submission_id: str,
        confidence_score: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update submission confidence score

        Args:
            submission_id: Submission ID
            confidence_score: Confidence score data

        Returns:
            Updated submission

        Raises:
            ResourceNotFound: If submission not found
            DatabaseError: If update fails
        """
        return await self.update(
            submission_id,
            {"confidence_score": confidence_score}
        )

    async def mark_as_archived(self, submission_id: str) -> Dict[str, Any]:
        """
        Mark submission as archived

        Args:
            submission_id: Submission ID

        Returns:
            Updated submission

        Raises:
            ResourceNotFound: If submission not found
            DatabaseError: If update fails
        """
        return await self.update(
            submission_id,
            {
                "archived": True,
                "archived_at": datetime.utcnow().isoformat()
            }
        )

    async def mark_as_unarchived(self, submission_id: str) -> Dict[str, Any]:
        """
        Mark submission as unarchived

        Args:
            submission_id: Submission ID

        Returns:
            Updated submission

        Raises:
            ResourceNotFound: If submission not found
            DatabaseError: If update fails
        """
        return await self.update(
            submission_id,
            {
                "archived": False,
                "archived_at": None
            }
        )

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get submission statistics

        Returns:
            Dictionary with statistics:
            - total: Total submissions
            - by_status: Count by status
            - by_date: Submissions in last 7 days

        Raises:
            DatabaseError: If query fails
        """
        try:
            # Get total count
            total = await self.count()

            # Get count by status
            statuses = ["pending", "processing", "completed", "failed"]
            by_status = {}

            for status in statuses:
                count = await self.count({"status": status})
                by_status[status] = count

            # Get submissions from last 7 days
            cutoff = datetime.utcnow() - timedelta(days=7)
            cutoff_str = cutoff.isoformat()

            response = (
                self.client.table(self.table_name)
                .select("*", count="exact")
                .gte("created_at", cutoff_str)
                .execute()
            )

            last_7_days = response.count if response.count is not None else 0

            self._log_operation("get_statistics", True)

            return {
                "total": total,
                "by_status": by_status,
                "last_7_days": last_7_days,
                "archived": await self.count({"archived": True}),
                "active": total - await self.count({"archived": True})
            }

        except Exception as e:
            self._log_operation("get_statistics", False, error=e)
            raise DatabaseError(f"Failed to get submission statistics: {str(e)}")

    async def search(
        self,
        query: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search submissions by company name or industry

        Args:
            query: Search query
            limit: Maximum records to return

        Returns:
            List of matching submissions

        Raises:
            DatabaseError: If query fails
        """
        try:
            # Supabase text search (requires full-text search index)
            response = (
                self.client.table(self.table_name)
                .select("*")
                .or_(f"company.ilike.%{query}%,industry.ilike.%{query}%")
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            self._log_operation("search", True)

            return response.data if response.data else []

        except Exception as e:
            self._log_operation("search", False, error=e)
            raise DatabaseError(f"Failed to search submissions: {str(e)}")

    async def get_failed_submissions(
        self,
        since_hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get failed submissions within time period

        Useful for retry logic and error monitoring.

        Args:
            since_hours: Look back period in hours
            limit: Maximum records to return

        Returns:
            List of failed submissions

        Raises:
            DatabaseError: If query fails
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=since_hours)
            cutoff_str = cutoff.isoformat()

            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("status", "failed")
                .gte("created_at", cutoff_str)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            self._log_operation("get_failed_submissions", True)

            return response.data if response.data else []

        except Exception as e:
            self._log_operation("get_failed_submissions", False, error=e)
            raise DatabaseError(f"Failed to get failed submissions: {str(e)}")

    async def bulk_update_status(
        self,
        submission_ids: List[str],
        status: str
    ) -> int:
        """
        Update status for multiple submissions

        Args:
            submission_ids: List of submission IDs
            status: New status to apply

        Returns:
            Number of updated records

        Raises:
            DatabaseError: If update fails
        """
        try:
            count = 0

            for submission_id in submission_ids:
                try:
                    await self.update_status(submission_id, status)
                    count += 1
                except ResourceNotFound:
                    logger.warning(f"Submission {submission_id} not found, skipping")
                    continue

            self._log_operation("bulk_update_status", True)

            return count

        except Exception as e:
            self._log_operation("bulk_update_status", False, error=e)
            raise DatabaseError(f"Failed to bulk update submissions: {str(e)}")


# Singleton instance for dependency injection
submission_repository = SubmissionRepository()


def get_submission_repository() -> SubmissionRepository:
    """
    Get submission repository instance

    For use with FastAPI dependency injection:
        @app.get("/submissions/{id}")
        async def get_submission(
            id: str,
            repo: SubmissionRepository = Depends(get_submission_repository)
        ):
            return await repo.get_by_id(id)
    """
    return submission_repository
