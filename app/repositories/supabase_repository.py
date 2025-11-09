"""
Supabase Repository Implementation
Concrete implementation of repository pattern for Supabase PostgreSQL
"""

from typing import Optional, List, Dict, Any, TypeVar
import logging

from app.repositories.base import BaseRepository
from app.core.supabase import get_supabase_client
from app.core.exceptions import DatabaseError, ResourceNotFound

logger = logging.getLogger(__name__)

T = TypeVar('T')


class SupabaseRepository(BaseRepository[T]):
    """
    Supabase-specific repository implementation

    Provides concrete implementation of CRUD operations using Supabase client.
    Handles error translation from Supabase exceptions to application exceptions.
    """

    def __init__(self, table_name: str):
        super().__init__(table_name)
        self.client = get_supabase_client()

    async def create(self, data: Dict[str, Any]) -> T:
        """
        Create a new record in Supabase

        Args:
            data: Record data

        Returns:
            Created record as dictionary

        Raises:
            DatabaseError: If creation fails
        """
        try:
            # Sanitize and add timestamps
            clean_data = self._sanitize_data(data)
            clean_data = self._add_timestamps(clean_data, is_update=False)

            # Insert into Supabase
            response = self.client.table(self.table_name).insert(clean_data).execute()

            if not response.data or len(response.data) == 0:
                raise DatabaseError(f"Failed to create record in {self.table_name}")

            result = response.data[0]
            self._log_operation("create", True, result.get("id"))

            return result

        except Exception as e:
            self._log_operation("create", False, error=e)
            raise DatabaseError(f"Failed to create record in {self.table_name}: {str(e)}")

    async def get_by_id(self, id: str) -> Optional[T]:
        """
        Get a record by ID

        Args:
            id: Record ID

        Returns:
            Record if found, None otherwise

        Raises:
            DatabaseError: If query fails
        """
        try:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("id", id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                self._log_operation("read", True, id)
                return None

            result = response.data[0]
            self._log_operation("read", True, id)

            return result

        except Exception as e:
            self._log_operation("read", False, id, error=e)
            raise DatabaseError(f"Failed to get record from {self.table_name}: {str(e)}")

    async def get_by_id_or_fail(self, id: str) -> T:
        """
        Get a record by ID or raise exception

        Args:
            id: Record ID

        Returns:
            Record

        Raises:
            ResourceNotFound: If record not found
            DatabaseError: If query fails
        """
        result = await self.get_by_id(id)

        if result is None:
            raise ResourceNotFound(f"Record with id={id} not found in {self.table_name}")

        return result

    async def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = True
    ) -> List[T]:
        """
        Get all records with pagination and sorting

        Args:
            limit: Maximum records to return
            offset: Number of records to skip
            order_by: Field to sort by (defaults to "created_at")
            order_desc: Sort descending if True

        Returns:
            List of records

        Raises:
            DatabaseError: If query fails
        """
        try:
            query = self.client.table(self.table_name).select("*")

            # Apply ordering
            order_field = order_by or "created_at"
            if order_desc:
                query = query.order(order_field, desc=True)
            else:
                query = query.order(order_field, desc=False)

            # Apply pagination
            if limit is not None:
                query = query.limit(limit)
            if offset is not None:
                query = query.offset(offset)

            response = query.execute()

            self._log_operation("read_all", True)

            return response.data if response.data else []

        except Exception as e:
            self._log_operation("read_all", False, error=e)
            raise DatabaseError(f"Failed to get records from {self.table_name}: {str(e)}")

    async def update(self, id: str, data: Dict[str, Any]) -> T:
        """
        Update a record by ID

        Args:
            id: Record ID
            data: Fields to update

        Returns:
            Updated record

        Raises:
            ResourceNotFound: If record not found
            DatabaseError: If update fails
        """
        try:
            # Check if record exists
            existing = await self.get_by_id(id)
            if existing is None:
                raise ResourceNotFound(f"Record with id={id} not found in {self.table_name}")

            # Sanitize and add timestamps
            clean_data = self._sanitize_data(data)
            clean_data = self._add_timestamps(clean_data, is_update=True)

            # Update in Supabase
            response = (
                self.client.table(self.table_name)
                .update(clean_data)
                .eq("id", id)
                .execute()
            )

            if not response.data or len(response.data) == 0:
                raise DatabaseError(f"Failed to update record in {self.table_name}")

            result = response.data[0]
            self._log_operation("update", True, id)

            return result

        except ResourceNotFound:
            self._log_operation("update", False, id)
            raise
        except Exception as e:
            self._log_operation("update", False, id, error=e)
            raise DatabaseError(f"Failed to update record in {self.table_name}: {str(e)}")

    async def delete(self, id: str) -> bool:
        """
        Delete a record by ID

        Args:
            id: Record ID

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            # Check if exists first
            existing = await self.get_by_id(id)
            if existing is None:
                self._log_operation("delete", True, id)
                return False

            # Delete from Supabase
            response = (
                self.client.table(self.table_name)
                .delete()
                .eq("id", id)
                .execute()
            )

            self._log_operation("delete", True, id)
            return True

        except Exception as e:
            self._log_operation("delete", False, id, error=e)
            raise DatabaseError(f"Failed to delete record from {self.table_name}: {str(e)}")

    async def exists(self, id: str) -> bool:
        """
        Check if a record exists

        Args:
            id: Record ID

        Returns:
            True if exists, False otherwise

        Raises:
            DatabaseError: If query fails
        """
        try:
            result = await self.get_by_id(id)
            return result is not None
        except DatabaseError:
            raise

    async def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records matching filters

        Args:
            filters: Optional filter conditions

        Returns:
            Number of matching records

        Raises:
            DatabaseError: If query fails
        """
        try:
            query = self.client.table(self.table_name).select("*", count="exact")

            # Apply filters
            if filters:
                for key, value in filters.items():
                    query = query.eq(key, value)

            response = query.execute()

            count = response.count if response.count is not None else 0
            self._log_operation("count", True)

            return count

        except Exception as e:
            self._log_operation("count", False, error=e)
            raise DatabaseError(f"Failed to count records in {self.table_name}: {str(e)}")

    async def find(self, filters: Dict[str, Any]) -> List[T]:
        """
        Find records matching filters

        Args:
            filters: Filter conditions

        Returns:
            List of matching records

        Raises:
            DatabaseError: If query fails
        """
        try:
            query = self.client.table(self.table_name).select("*")

            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)

            response = query.execute()

            self._log_operation("find", True)

            return response.data if response.data else []

        except Exception as e:
            self._log_operation("find", False, error=e)
            raise DatabaseError(f"Failed to find records in {self.table_name}: {str(e)}")

    async def find_one(self, filters: Dict[str, Any]) -> Optional[T]:
        """
        Find first record matching filters

        Args:
            filters: Filter conditions

        Returns:
            First matching record or None

        Raises:
            DatabaseError: If query fails
        """
        try:
            query = self.client.table(self.table_name).select("*").limit(1)

            # Apply filters
            for key, value in filters.items():
                query = query.eq(key, value)

            response = query.execute()

            self._log_operation("find_one", True)

            if response.data and len(response.data) > 0:
                return response.data[0]

            return None

        except Exception as e:
            self._log_operation("find_one", False, error=e)
            raise DatabaseError(f"Failed to find record in {self.table_name}: {str(e)}")

    async def batch_create(self, records: List[Dict[str, Any]]) -> List[T]:
        """
        Create multiple records in a single transaction

        Args:
            records: List of record data

        Returns:
            List of created records

        Raises:
            DatabaseError: If creation fails
        """
        try:
            # Sanitize and add timestamps to all records
            clean_records = [
                self._add_timestamps(self._sanitize_data(record), is_update=False)
                for record in records
            ]

            response = self.client.table(self.table_name).insert(clean_records).execute()

            if not response.data:
                raise DatabaseError(f"Failed to batch create records in {self.table_name}")

            self._log_operation("batch_create", True)

            return response.data

        except Exception as e:
            self._log_operation("batch_create", False, error=e)
            raise DatabaseError(f"Failed to batch create records in {self.table_name}: {str(e)}")

    async def batch_update(self, updates: List[Dict[str, Any]]) -> List[T]:
        """
        Update multiple records (requires id in each update dict)

        Args:
            updates: List of update data (each must include 'id')

        Returns:
            List of updated records

        Raises:
            DatabaseError: If updates fail
        """
        try:
            results = []

            for update in updates:
                if "id" not in update:
                    raise ValueError("Each update must include 'id' field")

                record_id = update.pop("id")
                result = await self.update(record_id, update)
                results.append(result)

            self._log_operation("batch_update", True)

            return results

        except Exception as e:
            self._log_operation("batch_update", False, error=e)
            raise DatabaseError(f"Failed to batch update records in {self.table_name}: {str(e)}")
