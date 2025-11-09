"""
Audit Repository for IMENSIAH Data Enrichment System

Domain-specific repository for managing enrichment_audit_log records.
Provides comprehensive audit trail tracking for all API calls.

Created: 2025-01-09
Version: 1.0.0
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import logging
import json

from app.repositories.supabase_repository import SupabaseRepository
from app.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class AuditRepository(SupabaseRepository):
    """
    Repository for enrichment_audit_log table

    Manages comprehensive audit trail of all API calls made during
    enrichment workflows. Tracks requests, responses, costs, and errors.

    Key Features:
    - Log every API call with full request/response data
    - Track costs and performance metrics
    - Query audit logs by enrichment, source, or date range
    - Generate audit reports for compliance and debugging

    Usage:
        repo = AuditRepository()

        # Log API call
        audit_id = await repo.log_api_call(
            enrichment_id=123,
            source_name="clearbit",
            request_data={"domain": "techstart.com"},
            response_data={"company_name": "TechStart"},
            success=True,
            cost_usd=0.10,
            duration_ms=1500
        )

        # Get audit trail for enrichment
        logs = await repo.get_by_enrichment(enrichment_id=123)

        # Get failed API calls for monitoring
        failed = await repo.get_failed_calls(hours=24)
    """

    def __init__(self):
        super().__init__("enrichment_audit_log")

    # ========================================================================
    # AUDIT LOGGING OPERATIONS
    # ========================================================================

    async def log_api_call(
        self,
        enrichment_id: Optional[int],
        source_name: str,
        request_data: Dict[str, Any],
        response_data: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        cost_usd: float = 0.0,
        duration_ms: Optional[int] = None,
        circuit_breaker_state: Optional[str] = None,
        cached: bool = False,
    ) -> int:
        """
        Log an API call to the audit trail

        Args:
            enrichment_id: Associated enrichment record ID (optional)
            source_name: Data source name (e.g., "clearbit", "google_places")
            request_data: Request parameters sent to API
            response_data: Response data from API (if successful)
            success: Whether the call succeeded
            error_type: Error category if failed (e.g., "timeout", "http_404")
            error_message: Detailed error message if failed
            cost_usd: API call cost in USD
            duration_ms: Call duration in milliseconds
            circuit_breaker_state: Circuit breaker state (open/half_open/closed)
            cached: Whether result was from cache

        Returns:
            Audit log entry ID

        Raises:
            DatabaseError: If logging fails
        """
        try:
            audit_data = {
                "enrichment_id": enrichment_id,
                "source_name": source_name,
                "request_data": json.dumps(request_data),
                "response_data": json.dumps(response_data) if response_data else None,
                "success": success,
                "error_type": error_type,
                "error_message": error_message,
                "cost_usd": cost_usd,
                "duration_ms": duration_ms,
                "circuit_breaker_state": circuit_breaker_state,
                "cached": cached,
            }

            result = await self.create(audit_data)

            logger.debug(
                f"Logged API call: {source_name} "
                f"(success={success}, cost=${cost_usd:.4f})",
                extra={
                    "audit_id": result["id"],
                    "enrichment_id": enrichment_id,
                    "source": source_name,
                    "success": success,
                    "cost": cost_usd,
                },
            )

            return result["id"]

        except Exception as e:
            # Log but don't fail - audit logging is non-critical
            logger.error(
                f"Failed to log API call to audit: {str(e)}",
                exc_info=True,
                extra={
                    "source": source_name,
                    "enrichment_id": enrichment_id,
                },
            )
            # Don't raise - allow enrichment to continue even if audit fails
            return -1

    async def log_batch_calls(
        self, calls: List[Dict[str, Any]]
    ) -> List[int]:
        """
        Log multiple API calls in batch

        Args:
            calls: List of call data dictionaries (same format as log_api_call)

        Returns:
            List of audit log entry IDs

        Raises:
            DatabaseError: If batch logging fails
        """
        try:
            # Prepare records
            audit_records = []
            for call in calls:
                audit_records.append(
                    {
                        "enrichment_id": call.get("enrichment_id"),
                        "source_name": call.get("source_name"),
                        "request_data": json.dumps(call.get("request_data", {})),
                        "response_data": (
                            json.dumps(call.get("response_data"))
                            if call.get("response_data")
                            else None
                        ),
                        "success": call.get("success", True),
                        "error_type": call.get("error_type"),
                        "error_message": call.get("error_message"),
                        "cost_usd": call.get("cost_usd", 0.0),
                        "duration_ms": call.get("duration_ms"),
                        "circuit_breaker_state": call.get("circuit_breaker_state"),
                        "cached": call.get("cached", False),
                    }
                )

            results = await self.batch_create(audit_records)

            logger.debug(
                f"Logged {len(results)} API calls in batch",
                extra={"count": len(results)},
            )

            return [r["id"] for r in results]

        except Exception as e:
            logger.error(
                f"Failed to log batch API calls: {str(e)}", exc_info=True
            )
            # Don't raise - allow enrichment to continue
            return []

    # ========================================================================
    # QUERY OPERATIONS
    # ========================================================================

    async def get_by_enrichment(
        self, enrichment_id: int
    ) -> List[Dict[str, Any]]:
        """
        Get all audit logs for a specific enrichment

        Args:
            enrichment_id: Enrichment record ID

        Returns:
            List of audit log entries

        Raises:
            DatabaseError: If query fails
        """
        try:
            logs = await self.find({"enrichment_id": enrichment_id})

            # Sort by created_at
            logs.sort(key=lambda x: x.get("created_at", ""), reverse=False)

            logger.debug(
                f"Retrieved {len(logs)} audit logs for enrichment {enrichment_id}",
                extra={"enrichment_id": enrichment_id, "count": len(logs)},
            )

            return logs

        except DatabaseError:
            raise
        except Exception as e:
            logger.error(
                f"Failed to get audit logs for enrichment {enrichment_id}: {str(e)}",
                exc_info=True,
            )
            raise DatabaseError(f"Failed to get audit logs: {str(e)}")

    async def get_by_source(
        self, source_name: str, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent audit logs for a specific data source

        Args:
            source_name: Data source name (e.g., "clearbit")
            limit: Maximum records to return

        Returns:
            List of audit log entries

        Raises:
            DatabaseError: If query fails
        """
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("source_name", source_name)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            logs = response.data if response.data else []

            logger.debug(
                f"Retrieved {len(logs)} audit logs for source {source_name}",
                extra={"source": source_name, "count": len(logs)},
            )

            return logs

        except Exception as e:
            logger.error(
                f"Failed to get audit logs for source {source_name}: {str(e)}",
                exc_info=True,
            )
            raise DatabaseError(f"Failed to get audit logs by source: {str(e)}")

    async def get_by_date_range(
        self, start_date: datetime, end_date: datetime, limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Get audit logs within a date range

        Args:
            start_date: Period start
            end_date: Period end
            limit: Maximum records to return

        Returns:
            List of audit log entries

        Raises:
            DatabaseError: If query fails
        """
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .gte("created_at", start_date.isoformat())
                .lte("created_at", end_date.isoformat())
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            logs = response.data if response.data else []

            logger.debug(
                f"Retrieved {len(logs)} audit logs for date range",
                extra={
                    "start": start_date.isoformat(),
                    "end": end_date.isoformat(),
                    "count": len(logs),
                },
            )

            return logs

        except Exception as e:
            logger.error(
                f"Failed to get audit logs by date range: {str(e)}",
                exc_info=True,
            )
            raise DatabaseError(f"Failed to get audit logs by date: {str(e)}")

    async def get_failed_calls(
        self, hours: int = 24, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get failed API calls within time period

        Useful for monitoring and alerting on API failures.

        Args:
            hours: Look back period in hours
            limit: Maximum records to return

        Returns:
            List of failed audit log entries

        Raises:
            DatabaseError: If query fails
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("success", False)
                .gte("created_at", cutoff.isoformat())
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            logs = response.data if response.data else []

            logger.debug(
                f"Retrieved {len(logs)} failed API calls in last {hours}h",
                extra={"hours": hours, "count": len(logs)},
            )

            return logs

        except Exception as e:
            logger.error(
                f"Failed to get failed API calls: {str(e)}", exc_info=True
            )
            raise DatabaseError(f"Failed to get failed calls: {str(e)}")

    async def get_circuit_breaker_events(
        self, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get circuit breaker state change events

        Args:
            hours: Look back period in hours

        Returns:
            List of audit logs with circuit breaker state changes

        Raises:
            DatabaseError: If query fails
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            response = (
                self.client.table(self.table_name)
                .select("*")
                .neq("circuit_breaker_state", "closed")
                .gte("created_at", cutoff.isoformat())
                .order("created_at", desc=True)
                .execute()
            )

            logs = response.data if response.data else []

            logger.debug(
                f"Retrieved {len(logs)} circuit breaker events in last {hours}h",
                extra={"hours": hours, "count": len(logs)},
            )

            return logs

        except Exception as e:
            logger.error(
                f"Failed to get circuit breaker events: {str(e)}",
                exc_info=True,
            )
            raise DatabaseError(f"Failed to get circuit breaker events: {str(e)}")

    # ========================================================================
    # STATISTICS & ANALYTICS
    # ========================================================================

    async def get_source_statistics(
        self, source_name: str, hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get statistics for a specific data source

        Args:
            source_name: Data source name
            hours: Look back period in hours

        Returns:
            Dictionary with source statistics:
            - total_calls: Total API calls
            - successful_calls: Successful calls
            - failed_calls: Failed calls
            - success_rate: Success rate percentage
            - total_cost: Total cost in USD
            - avg_duration_ms: Average call duration
            - circuit_breaker_trips: Circuit breaker open events

        Raises:
            DatabaseError: If query fails
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours)

            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("source_name", source_name)
                .gte("created_at", cutoff.isoformat())
                .execute()
            )

            logs = response.data if response.data else []

            total_calls = len(logs)
            successful = sum(1 for log in logs if log.get("success", False))
            failed = total_calls - successful
            success_rate = (successful / total_calls * 100) if total_calls > 0 else 0.0

            total_cost = sum(log.get("cost_usd", 0.0) for log in logs)

            durations = [
                log.get("duration_ms", 0) for log in logs if log.get("duration_ms")
            ]
            avg_duration = (
                sum(durations) / len(durations) if durations else 0
            )

            cb_trips = sum(
                1
                for log in logs
                if log.get("circuit_breaker_state") in ["open", "half_open"]
            )

            stats = {
                "source_name": source_name,
                "total_calls": total_calls,
                "successful_calls": successful,
                "failed_calls": failed,
                "success_rate": round(success_rate, 2),
                "total_cost_usd": round(total_cost, 4),
                "avg_duration_ms": round(avg_duration, 0),
                "circuit_breaker_trips": cb_trips,
            }

            logger.debug(
                f"Retrieved statistics for source {source_name}",
                extra=stats,
            )

            return stats

        except Exception as e:
            logger.error(
                f"Failed to get source statistics: {str(e)}", exc_info=True
            )
            raise DatabaseError(f"Failed to get source statistics: {str(e)}")

    async def get_all_source_statistics(
        self, hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Get statistics for all data sources

        Args:
            hours: Look back period in hours

        Returns:
            List of source statistics dictionaries

        Raises:
            DatabaseError: If query fails
        """
        try:
            # Get all unique source names
            response = (
                self.client.table(self.table_name)
                .select("source_name")
                .execute()
            )

            logs = response.data if response.data else []
            unique_sources = set(log.get("source_name") for log in logs)

            # Get statistics for each source
            all_stats = []
            for source_name in unique_sources:
                stats = await self.get_source_statistics(source_name, hours)
                all_stats.append(stats)

            # Sort by total calls descending
            all_stats.sort(key=lambda x: x["total_calls"], reverse=True)

            logger.debug(
                f"Retrieved statistics for {len(all_stats)} sources",
                extra={"count": len(all_stats)},
            )

            return all_stats

        except Exception as e:
            logger.error(
                f"Failed to get all source statistics: {str(e)}",
                exc_info=True,
            )
            raise DatabaseError(f"Failed to get all source statistics: {str(e)}")

    async def get_cost_summary(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        """
        Get cost summary for date range

        Args:
            start_date: Period start
            end_date: Period end

        Returns:
            Dictionary with cost breakdown:
            - total_cost: Total API costs
            - by_source: Cost breakdown by source
            - call_count: Total API calls

        Raises:
            DatabaseError: If query fails
        """
        try:
            logs = await self.get_by_date_range(start_date, end_date, limit=10000)

            total_cost = sum(log.get("cost_usd", 0.0) for log in logs)
            call_count = len(logs)

            # Cost by source
            by_source = {}
            for log in logs:
                source = log.get("source_name", "unknown")
                cost = log.get("cost_usd", 0.0)
                by_source[source] = by_source.get(source, 0.0) + cost

            # Round costs
            by_source = {k: round(v, 4) for k, v in by_source.items()}

            summary = {
                "total_cost_usd": round(total_cost, 4),
                "call_count": call_count,
                "by_source": by_source,
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            }

            logger.debug(
                "Retrieved cost summary",
                extra=summary,
            )

            return summary

        except Exception as e:
            logger.error(
                f"Failed to get cost summary: {str(e)}", exc_info=True
            )
            raise DatabaseError(f"Failed to get cost summary: {str(e)}")


# Singleton instance for dependency injection
audit_repository = AuditRepository()


def get_audit_repository() -> AuditRepository:
    """
    Get audit repository instance

    For use with FastAPI dependency injection:
        @app.get("/audit/enrichment/{enrichment_id}")
        async def get_audit_trail(
            enrichment_id: int,
            repo: AuditRepository = Depends(get_audit_repository)
        ):
            return await repo.get_by_enrichment(enrichment_id)
    """
    return audit_repository
