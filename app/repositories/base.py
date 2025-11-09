"""
Base Repository Pattern
Provides abstract base class for all repository implementations
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List, Dict, Any
from datetime import datetime
import logging

from app.core.exceptions import DatabaseError, ResourceNotFound

logger = logging.getLogger(__name__)

# Type variable for model classes
T = TypeVar('T')


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository providing common CRUD operations

    This implements the Repository Pattern, providing a clean abstraction
    layer between business logic and data access logic.

    Benefits:
    - Single Responsibility: Database logic separated from business logic
    - Testability: Easy to mock repositories in tests
    - Maintainability: Database changes isolated to repository layer
    - Flexibility: Easy to switch database implementations

    Type Parameter:
        T: The model type this repository manages
    """

    def __init__(self, table_name: str):
        """
        Initialize repository

        Args:
            table_name: Name of the database table
        """
        self.table_name = table_name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> T:
        """
        Create a new record

        Args:
            data: Dictionary of field values

        Returns:
            Created model instance

        Raises:
            DatabaseError: If creation fails
        """
        pass

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """
        Get a record by ID

        Args:
            id: Record ID

        Returns:
            Model instance if found, None otherwise

        Raises:
            DatabaseError: If query fails
        """
        pass

    @abstractmethod
    async def get_by_id_or_fail(self, id: str) -> T:
        """
        Get a record by ID or raise exception

        Args:
            id: Record ID

        Returns:
            Model instance

        Raises:
            ResourceNotFound: If record not found
            DatabaseError: If query fails
        """
        pass

    @abstractmethod
    async def get_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: Optional[str] = None,
        order_desc: bool = True
    ) -> List[T]:
        """
        Get all records with optional pagination and sorting

        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            order_by: Field to sort by
            order_desc: Sort descending if True, ascending if False

        Returns:
            List of model instances

        Raises:
            DatabaseError: If query fails
        """
        pass

    @abstractmethod
    async def update(self, id: str, data: Dict[str, Any]) -> T:
        """
        Update a record by ID

        Args:
            id: Record ID
            data: Dictionary of fields to update

        Returns:
            Updated model instance

        Raises:
            ResourceNotFound: If record not found
            DatabaseError: If update fails
        """
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
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
        pass

    @abstractmethod
    async def find(self, filters: Dict[str, Any]) -> List[T]:
        """
        Find records matching filters

        Args:
            filters: Filter conditions (field: value)

        Returns:
            List of matching model instances

        Raises:
            DatabaseError: If query fails
        """
        pass

    @abstractmethod
    async def find_one(self, filters: Dict[str, Any]) -> Optional[T]:
        """
        Find first record matching filters

        Args:
            filters: Filter conditions (field: value)

        Returns:
            Model instance if found, None otherwise

        Raises:
            DatabaseError: If query fails
        """
        pass

    def _add_timestamps(self, data: Dict[str, Any], is_update: bool = False) -> Dict[str, Any]:
        """
        Add created_at/updated_at timestamps

        Args:
            data: Record data
            is_update: True if updating, False if creating

        Returns:
            Data with timestamps added
        """
        now = datetime.utcnow().isoformat()

        if not is_update and "created_at" not in data:
            data["created_at"] = now

        data["updated_at"] = now

        return data

    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize data before database operations

        Args:
            data: Raw data

        Returns:
            Sanitized data
        """
        # Remove None values
        sanitized = {k: v for k, v in data.items() if v is not None}

        # Remove internal fields that shouldn't be set directly
        internal_fields = ["id", "created_at"]
        for field in internal_fields:
            sanitized.pop(field, None)

        return sanitized

    def _log_operation(
        self,
        operation: str,
        success: bool,
        record_id: Optional[str] = None,
        error: Optional[Exception] = None
    ):
        """
        Log repository operations for monitoring

        Args:
            operation: Operation name (create, read, update, delete)
            success: Whether operation succeeded
            record_id: Optional record ID
            error: Optional exception if failed
        """
        log_data = {
            "table": self.table_name,
            "operation": operation,
            "success": success,
        }

        if record_id:
            log_data["record_id"] = record_id

        if success:
            self.logger.debug(f"Repository operation successful", extra=log_data)
        else:
            log_data["error"] = str(error) if error else "Unknown error"
            self.logger.error(f"Repository operation failed", extra=log_data)


class ReadOnlyRepository(BaseRepository[T]):
    """
    Read-only repository base class
    Useful for views or read-only data sources
    """

    async def create(self, data: Dict[str, Any]) -> T:
        raise NotImplementedError("Create operation not supported on read-only repository")

    async def update(self, id: str, data: Dict[str, Any]) -> T:
        raise NotImplementedError("Update operation not supported on read-only repository")

    async def delete(self, id: str) -> bool:
        raise NotImplementedError("Delete operation not supported on read-only repository")
