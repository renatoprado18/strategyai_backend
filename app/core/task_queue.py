"""
Task Queue System for Background Job Processing
Provides async task execution with Redis backend
"""

import json
import logging
import asyncio
from typing import Callable, Any, Dict, Optional, List
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
import traceback

from app.core.security.rate_limiter import get_redis_client
from app.core.exceptions import TaskQueueError

logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY = "retry"


class TaskPriority(Enum):
    """Task priority levels"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


@dataclass
class Task:
    """
    Task representation

    Attributes:
        id: Unique task ID
        name: Task function name
        args: Positional arguments
        kwargs: Keyword arguments
        status: Current status
        priority: Priority level
        retries: Number of retry attempts remaining
        max_retries: Maximum retry attempts
        created_at: Creation timestamp
        started_at: Start timestamp
        completed_at: Completion timestamp
        result: Task result (if completed)
        error: Error message (if failed)
    """
    id: str
    name: str
    args: tuple
    kwargs: dict
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.NORMAL
    retries: int = 0
    max_retries: int = 3
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert task to dictionary for storage"""
        data = asdict(self)
        data["status"] = self.status.value
        data["priority"] = self.priority.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Task":
        """Create task from dictionary"""
        data["status"] = TaskStatus(data["status"])
        data["priority"] = TaskPriority(data["priority"])
        return cls(**data)


class TaskQueue:
    """
    Redis-backed task queue for background job processing

    Features:
    - Priority-based task execution
    - Automatic retries with exponential backoff
    - Task status tracking
    - Dead letter queue for failed tasks
    - Task result storage
    - Distributed worker support

    Example:
        queue = TaskQueue()

        # Enqueue a task
        task_id = await queue.enqueue(
            process_submission,
            args=(submission_id,),
            priority=TaskPriority.HIGH
        )

        # Check status
        status = await queue.get_task_status(task_id)

        # Get result
        result = await queue.get_task_result(task_id)
    """

    def __init__(
        self,
        redis_client=None,
        queue_prefix: str = "task_queue",
        result_ttl: int = 3600  # 1 hour
    ):
        """
        Initialize task queue

        Args:
            redis_client: Redis client instance
            queue_prefix: Prefix for Redis keys
            result_ttl: TTL for task results in seconds
        """
        self.redis = redis_client or get_redis_client()
        self.prefix = queue_prefix
        self.result_ttl = result_ttl

        # Queue keys
        self.pending_key = f"{self.prefix}:pending"
        self.running_key = f"{self.prefix}:running"
        self.completed_key = f"{self.prefix}:completed"
        self.failed_key = f"{self.prefix}:failed"
        self.dlq_key = f"{self.prefix}:dlq"  # Dead letter queue

        # Registered task functions
        self.tasks: Dict[str, Callable] = {}

    def register_task(self, name: str, func: Callable):
        """
        Register a task function

        Args:
            name: Task name
            func: Task function
        """
        self.tasks[name] = func
        logger.info(f"[TASK QUEUE] Registered task: {name}")

    def task(self, name: str):
        """
        Decorator to register task functions

        Example:
            queue = TaskQueue()

            @queue.task("process_submission")
            async def process_submission(submission_id: str):
                # Process submission
                return result
        """
        def decorator(func: Callable):
            self.register_task(name, func)
            return func
        return decorator

    async def enqueue(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        max_retries: int = 3,
        task_id: Optional[str] = None
    ) -> str:
        """
        Enqueue a task for execution

        Args:
            func: Task function (must be registered)
            args: Positional arguments
            kwargs: Keyword arguments
            priority: Task priority
            max_retries: Maximum retry attempts
            task_id: Optional custom task ID

        Returns:
            Task ID

        Raises:
            TaskQueueError: If task enqueueing fails
        """
        try:
            # Generate task ID
            if task_id is None:
                import uuid
                task_id = str(uuid.uuid4())

            # Get function name
            func_name = func.__name__

            # Ensure function is registered
            if func_name not in self.tasks:
                self.register_task(func_name, func)

            # Create task
            task = Task(
                id=task_id,
                name=func_name,
                args=args,
                kwargs=kwargs or {},
                priority=priority,
                max_retries=max_retries,
                created_at=datetime.utcnow().isoformat()
            )

            # Store task data
            task_key = f"{self.prefix}:task:{task_id}"
            self.redis.set(task_key, json.dumps(task.to_dict()))

            # Add to priority queue
            # Higher priority = higher score
            score = priority.value * 1000000 + int(datetime.utcnow().timestamp())
            self.redis.zadd(self.pending_key, {task_id: score})

            logger.info(
                f"[TASK QUEUE] Enqueued task: {task_id} ({func_name}) "
                f"with priority {priority.name}"
            )

            return task_id

        except Exception as e:
            logger.error(f"[TASK QUEUE] Failed to enqueue task: {e}", exc_info=True)
            raise TaskQueueError(f"Failed to enqueue task: {str(e)}")

    async def dequeue(self, timeout: int = 0) -> Optional[Task]:
        """
        Dequeue next task for processing

        Args:
            timeout: Block timeout in seconds (0 = non-blocking)

        Returns:
            Task if available, None otherwise

        Raises:
            TaskQueueError: If dequeueing fails
        """
        try:
            # Get highest priority task (highest score)
            result = self.redis.zpopmax(self.pending_key)

            if not result:
                return None

            task_id, score = result[0]

            # Load task data
            task_key = f"{self.prefix}:task:{task_id}"
            task_data = self.redis.get(task_key)

            if not task_data:
                logger.warning(f"[TASK QUEUE] Task {task_id} data not found")
                return None

            task = Task.from_dict(json.loads(task_data))

            # Move to running queue
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow().isoformat()

            self.redis.set(task_key, json.dumps(task.to_dict()))
            self.redis.sadd(self.running_key, task_id)

            logger.info(f"[TASK QUEUE] Dequeued task: {task_id} ({task.name})")

            return task

        except Exception as e:
            logger.error(f"[TASK QUEUE] Failed to dequeue task: {e}", exc_info=True)
            raise TaskQueueError(f"Failed to dequeue task: {str(e)}")

    async def execute_task(self, task: Task) -> Any:
        """
        Execute a task

        Args:
            task: Task to execute

        Returns:
            Task result

        Raises:
            Exception: If task execution fails
        """
        if task.name not in self.tasks:
            raise TaskQueueError(f"Task function '{task.name}' not registered")

        func = self.tasks[task.name]

        # Execute function
        if asyncio.iscoroutinefunction(func):
            result = await func(*task.args, **task.kwargs)
        else:
            result = func(*task.args, **task.kwargs)

        return result

    async def mark_completed(self, task: Task, result: Any):
        """
        Mark task as completed

        Args:
            task: Completed task
            result: Task result
        """
        try:
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow().isoformat()
            task.result = result

            task_key = f"{self.prefix}:task:{task.id}"
            self.redis.set(task_key, json.dumps(task.to_dict()), ex=self.result_ttl)

            # Move from running to completed
            self.redis.srem(self.running_key, task.id)
            self.redis.sadd(self.completed_key, task.id)

            logger.info(f"[TASK QUEUE] Task completed: {task.id}")

        except Exception as e:
            logger.error(f"[TASK QUEUE] Failed to mark task as completed: {e}")

    async def mark_failed(self, task: Task, error: Exception):
        """
        Mark task as failed and optionally retry

        Args:
            task: Failed task
            error: Exception that occurred
        """
        try:
            task.retries += 1
            task.error = str(error)

            # Check if we should retry
            if task.retries < task.max_retries:
                task.status = TaskStatus.RETRY
                logger.warning(
                    f"[TASK QUEUE] Task failed, retrying: {task.id} "
                    f"(attempt {task.retries}/{task.max_retries})"
                )

                # Re-enqueue with exponential backoff
                backoff = 2 ** task.retries  # 2, 4, 8 seconds
                await asyncio.sleep(backoff)

                await self.enqueue(
                    self.tasks[task.name],
                    args=task.args,
                    kwargs=task.kwargs,
                    priority=task.priority,
                    max_retries=task.max_retries,
                    task_id=task.id
                )
            else:
                # Max retries exceeded - move to DLQ
                task.status = TaskStatus.FAILED
                task.completed_at = datetime.utcnow().isoformat()

                task_key = f"{self.prefix}:task:{task.id}"
                self.redis.set(task_key, json.dumps(task.to_dict()), ex=self.result_ttl * 24)  # Keep failed tasks longer

                self.redis.srem(self.running_key, task.id)
                self.redis.sadd(self.dlq_key, task.id)

                logger.error(
                    f"[TASK QUEUE] Task failed permanently: {task.id} - {error}",
                    exc_info=True
                )

        except Exception as e:
            logger.error(f"[TASK QUEUE] Failed to mark task as failed: {e}")

    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        Get task status

        Args:
            task_id: Task ID

        Returns:
            Task status if found, None otherwise
        """
        try:
            task_key = f"{self.prefix}:task:{task_id}"
            task_data = self.redis.get(task_key)

            if not task_data:
                return None

            task = Task.from_dict(json.loads(task_data))
            return task.status

        except Exception as e:
            logger.error(f"[TASK QUEUE] Failed to get task status: {e}")
            return None

    async def get_task_result(self, task_id: str) -> Optional[Any]:
        """
        Get task result

        Args:
            task_id: Task ID

        Returns:
            Task result if completed, None otherwise
        """
        try:
            task_key = f"{self.prefix}:task:{task_id}"
            task_data = self.redis.get(task_key)

            if not task_data:
                return None

            task = Task.from_dict(json.loads(task_data))

            if task.status == TaskStatus.COMPLETED:
                return task.result

            return None

        except Exception as e:
            logger.error(f"[TASK QUEUE] Failed to get task result: {e}")
            return None

    async def get_queue_stats(self) -> Dict[str, int]:
        """
        Get queue statistics

        Returns:
            Dictionary with queue counts
        """
        try:
            return {
                "pending": self.redis.zcard(self.pending_key),
                "running": self.redis.scard(self.running_key),
                "completed": self.redis.scard(self.completed_key),
                "failed": self.redis.scard(self.dlq_key),
            }
        except Exception as e:
            logger.error(f"[TASK QUEUE] Failed to get queue stats: {e}")
            return {"pending": 0, "running": 0, "completed": 0, "failed": 0}

    async def clear_completed(self, older_than_hours: int = 24):
        """
        Clear completed tasks older than specified hours

        Args:
            older_than_hours: Clear tasks older than this many hours
        """
        try:
            cutoff = datetime.utcnow() - timedelta(hours=older_than_hours)

            # Get all completed task IDs
            task_ids = self.redis.smembers(self.completed_key)

            cleared = 0
            for task_id in task_ids:
                task_key = f"{self.prefix}:task:{task_id}"
                task_data = self.redis.get(task_key)

                if task_data:
                    task = Task.from_dict(json.loads(task_data))

                    if task.completed_at:
                        completed_at = datetime.fromisoformat(task.completed_at)
                        if completed_at < cutoff:
                            self.redis.delete(task_key)
                            self.redis.srem(self.completed_key, task_id)
                            cleared += 1

            logger.info(f"[TASK QUEUE] Cleared {cleared} completed tasks")

        except Exception as e:
            logger.error(f"[TASK QUEUE] Failed to clear completed tasks: {e}")


# Global task queue instance
task_queue = TaskQueue()


def get_task_queue() -> TaskQueue:
    """
    Get global task queue instance

    For dependency injection:
        async def endpoint(queue: TaskQueue = Depends(get_task_queue)):
            await queue.enqueue(my_task, args=(arg1,))
    """
    return task_queue
