"""Async queue processor for executing pending operations."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from src.etsy_api import EtsyAPI
from src.operation_registry import REGISTRY
from src.operation_store import OperationStore
from src.operations import OperationRequest, OperationStatus


UTC = timezone.utc
logger = logging.getLogger(__name__)


class OperationQueue:
    """Async queue for executing operations."""

    def __init__(
        self,
        store: OperationStore,
        etsy: EtsyAPI,
        config: Any,
    ) -> None:
        """Initialize queue processor."""
        self.store = store
        self.etsy = etsy
        self.config = config
        self._running = False
        self._task: asyncio.Task[Any] | None = None

    async def start(self) -> None:
        """Start queue processor (background task)."""
        if self._running:
            logger.warning("Queue processor already running")
            return

        self._running = True
        logger.info("Starting operation queue processor")

        try:
            while self._running:
                await self._process_batch()
                await asyncio.sleep(self.config.queue_poll_interval_seconds)
        except asyncio.CancelledError:
            logger.info("Queue processor cancelled")
        except Exception as e:
            logger.exception(f"Queue processor error: {e}")
            self._running = False
            raise

    async def stop(self) -> None:
        """Stop queue processor gracefully."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Queue processor stopped")

    async def _process_batch(self) -> None:
        """Process batch of pending operations."""
        pending = self.store.list_pending_operations(limit=10)

        for op_req in pending:
            try:
                await self._execute_operation(op_req)
            except Exception as e:
                logger.exception(f"Error executing operation {op_req.id}: {e}")

    async def _execute_operation(self, op_req: OperationRequest) -> None:
        """Execute single operation with retry logic."""
        op_def = REGISTRY.get(op_req.operation_name)
        if not op_def:
            error_msg = f"Unknown operation: {op_req.operation_name}"
            self.store.update_operation_status(
                op_req.id, OperationStatus.FAILED, error=error_msg
            )
            logger.error(error_msg)
            return

        try:
            # Mark as executing
            self.store.update_operation_status(op_req.id, OperationStatus.EXECUTING)
            logger.info(f"Executing operation {op_req.id} ({op_req.operation_name})")

            # Execute with timeout
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(
                        op_def.execute, self.etsy, op_req.arguments
                    ),
                    timeout=300,  # 5 minute timeout
                )
            except asyncio.TimeoutError:
                raise TimeoutError(f"Operation {op_req.id} exceeded timeout")

            # Mark as completed
            self.store.update_operation_status(
                op_req.id, OperationStatus.COMPLETED, result=result
            )
            logger.info(f"Completed operation {op_req.id}")

        except Exception as e:
            # Retry logic
            retry_count = op_req.get_metadata("retry_count", 0)
            max_retries = self.config.queue_retry_max_attempts

            if retry_count < max_retries:
                # Calculate exponential backoff
                backoff_secs = 2 ** retry_count * self.config.queue_retry_backoff_multiplier
                retry_count += 1
                op_req.set_metadata("retry_count", retry_count)
                op_req.set_metadata("last_error", str(e))
                op_req.set_metadata("next_retry_at", (
                    datetime.now(UTC).timestamp() + backoff_secs
                ))

                logger.warning(
                    f"Operation {op_req.id} failed (attempt {retry_count}/{max_retries}), "
                    f"retrying in {backoff_secs}s: {e}"
                )

                # Reset to pending for retry
                self.store.update_operation_status(
                    op_req.id, OperationStatus.PENDING, metadata=op_req._metadata
                )
            else:
                # Max retries exceeded
                error_msg = f"Operation failed after {max_retries} attempts: {e}"
                self.store.update_operation_status(
                    op_req.id, OperationStatus.FAILED, error=error_msg
                )
                logger.error(error_msg)


class QueueBackgroundTask:
    """Manage queue processor as background task."""

    def __init__(self, queue: OperationQueue) -> None:
        """Initialize background task manager."""
        self.queue = queue
        self._task: asyncio.Task[Any] | None = None

    async def start(self) -> None:
        """Start queue processor in background."""
        if self._task is not None and not self._task.done():
            logger.warning("Background task already running")
            return

        self._task = asyncio.create_task(self.queue.start())
        logger.info("Queue background task started")

    async def stop(self) -> None:
        """Stop queue processor gracefully."""
        await self.queue.stop()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Queue background task stopped")

    def is_running(self) -> bool:
        """Check if background task is running."""
        return self._task is not None and not self._task.done()
