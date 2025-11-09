"""
Background Task Worker
Processes tasks from the task queue
"""

import asyncio
import logging
import signal
import sys
from typing import Optional

from app.core.task_queue import task_queue, TaskStatus
from app.middleware import get_logger

logger = get_logger(__name__)


class Worker:
    """
    Background worker for processing queued tasks

    Features:
    - Graceful shutdown handling
    - Automatic task retry
    - Health monitoring
    - Concurrent task processing

    Usage:
        python worker.py
    """

    def __init__(self, concurrency: int = 4):
        """
        Initialize worker

        Args:
            concurrency: Number of concurrent tasks to process
        """
        self.concurrency = concurrency
        self.running = False
        self.tasks = []

    async def process_task_loop(self, worker_id: int):
        """
        Main task processing loop for a worker

        Args:
            worker_id: Worker ID for logging
        """
        logger.info(f"[WORKER {worker_id}] Started task processing loop")

        while self.running:
            try:
                # Dequeue next task
                task = await task_queue.dequeue()

                if task is None:
                    # No tasks available, wait before checking again
                    await asyncio.sleep(1)
                    continue

                logger.info(
                    f"[WORKER {worker_id}] Processing task: {task.id} ({task.name})"
                )

                try:
                    # Execute task
                    result = await task_queue.execute_task(task)

                    # Mark as completed
                    await task_queue.mark_completed(task, result)

                    logger.info(
                        f"[WORKER {worker_id}] Task completed: {task.id}",
                        extra={"task_id": task.id, "task_name": task.name}
                    )

                except Exception as e:
                    # Mark as failed (will retry if retries remaining)
                    await task_queue.mark_failed(task, e)

                    logger.error(
                        f"[WORKER {worker_id}] Task failed: {task.id} - {e}",
                        extra={"task_id": task.id, "task_name": task.name, "error": str(e)},
                        exc_info=True
                    )

            except Exception as e:
                logger.error(f"[WORKER {worker_id}] Error in processing loop: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying

        logger.info(f"[WORKER {worker_id}] Stopped task processing loop")

    async def start(self):
        """Start the worker"""
        self.running = True

        logger.info(f"[WORKER] Starting {self.concurrency} worker processes")

        # Start concurrent worker tasks
        self.tasks = [
            asyncio.create_task(self.process_task_loop(i))
            for i in range(self.concurrency)
        ]

        # Wait for all tasks
        await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info("[WORKER] All worker processes stopped")

    async def stop(self):
        """Stop the worker gracefully"""
        logger.info("[WORKER] Stopping worker...")

        self.running = False

        # Cancel all worker tasks
        for task in self.tasks:
            task.cancel()

        # Wait for cancellations
        await asyncio.gather(*self.tasks, return_exceptions=True)

        logger.info("[WORKER] Worker stopped")

    def handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"[WORKER] Received signal {signum}, shutting down gracefully...")

        # Create task to stop worker
        asyncio.create_task(self.stop())


async def main():
    """
    Main worker entrypoint

    Registers tasks and starts worker
    """
    logger.info("=" * 80)
    logger.info("Strategy AI Background Worker")
    logger.info("=" * 80)

    # Register tasks
    from app.utils.background_tasks import (
        process_submission_background
    )

    # Register with task queue
    task_queue.register_task("process_submission", process_submission_background)

    logger.info("[WORKER] Registered tasks:")
    for task_name in task_queue.tasks.keys():
        logger.info(f"  - {task_name}")

    # Get queue stats
    stats = await task_queue.get_queue_stats()
    logger.info(f"[WORKER] Queue statistics:")
    logger.info(f"  - Pending: {stats['pending']}")
    logger.info(f"  - Running: {stats['running']}")
    logger.info(f"  - Completed: {stats['completed']}")
    logger.info(f"  - Failed: {stats['failed']}")

    # Create worker
    worker = Worker(concurrency=4)

    # Setup signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, worker.handle_shutdown)
    signal.signal(signal.SIGTERM, worker.handle_shutdown)

    logger.info("[WORKER] Worker ready, waiting for tasks...")
    logger.info("[WORKER] Press Ctrl+C to stop")

    # Start worker
    try:
        await worker.start()
    except KeyboardInterrupt:
        logger.info("[WORKER] Keyboard interrupt received")
        await worker.stop()
    except Exception as e:
        logger.error(f"[WORKER] Fatal error: {e}", exc_info=True)
        await worker.stop()
        sys.exit(1)

    logger.info("[WORKER] Worker shutdown complete")


if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Run worker
    asyncio.run(main())
