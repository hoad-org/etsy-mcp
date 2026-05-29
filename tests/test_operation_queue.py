"""Tests for OperationQueue async processor."""

import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.base_operation import Operation
from src.operation_queue import OperationQueue, QueueBackgroundTask
from src.operation_store import OperationStore
from src.operations import OperationRequest, OperationStatus


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        yield str(db_path)


@pytest.fixture
def mock_config():
    """Create mock config."""
    config = Mock()
    config.queue_poll_interval_seconds = 0.1
    config.queue_retry_max_attempts = 3
    config.queue_retry_backoff_multiplier = 1
    return config


@pytest.fixture
def mock_etsy():
    """Create mock Etsy API."""
    return Mock()


class TestOperationQueue:
    """Test OperationQueue class."""

    @pytest.mark.asyncio
    async def test_init(self, temp_db, mock_etsy, mock_config):
        """Test OperationQueue initialization."""
        store = OperationStore(temp_db)
        queue = OperationQueue(store, mock_etsy, mock_config)

        assert queue.store == store
        assert queue.etsy == mock_etsy
        assert queue._running is False
        assert queue._task is None

    @pytest.mark.asyncio
    async def test_start_and_stop(self, temp_db, mock_etsy, mock_config):
        """Test starting and stopping queue."""
        store = OperationStore(temp_db)
        queue = OperationQueue(store, mock_etsy, mock_config)

        # Create a task to run start
        task = asyncio.create_task(queue.start())

        # Give it a moment to start
        await asyncio.sleep(0.2)
        assert queue._running is True

        # Stop the queue
        await queue.stop()
        assert queue._running is False

        # Wait for start task to complete (exits cleanly when _running=False)
        await task

    @pytest.mark.asyncio
    async def test_start_already_running(self, temp_db, mock_etsy, mock_config):
        """Test that start doesn't run twice."""
        store = OperationStore(temp_db)
        queue = OperationQueue(store, mock_etsy, mock_config)

        # Set running flag
        queue._running = True

        # Call start - should return early
        await queue.start()

        # Reset for cleanup
        queue._running = False

    @pytest.mark.asyncio
    async def test_process_batch_empty(self, temp_db, mock_etsy, mock_config):
        """Test processing empty batch."""
        store = OperationStore(temp_db)
        queue = OperationQueue(store, mock_etsy, mock_config)

        # Should not raise exception with empty queue
        await queue._process_batch()

    @pytest.mark.asyncio
    async def test_process_batch_unknown_operation(self, temp_db, mock_etsy, mock_config):
        """Test processing batch with unknown operation."""
        store = OperationStore(temp_db)
        queue = OperationQueue(store, mock_etsy, mock_config)

        # Create operation with unknown operation name
        op = OperationRequest("unknown_op", {}, Operation.READ)
        store.create_operation(op)

        # Process batch
        await queue._process_batch()

        # Operation should be marked as failed
        retrieved = store.get_operation(op.id)
        assert retrieved.status == OperationStatus.FAILED
        assert "Unknown operation" in retrieved.error

    @pytest.mark.asyncio
    async def test_execute_operation_success(self, temp_db, mock_etsy, mock_config):
        """Test executing operation successfully."""
        store = OperationStore(temp_db)
        queue = OperationQueue(store, mock_etsy, mock_config)

        # Create a mock operation
        mock_op_def = Mock()
        mock_op_def.execute.return_value = {"status": "success", "data": "result"}

        with patch('src.operation_queue.REGISTRY') as mock_registry:
            mock_registry.get.return_value = mock_op_def

            op = OperationRequest("test_op", {}, Operation.READ)
            store.create_operation(op)

            # Execute operation
            await queue._execute_operation(op)

            # Operation should be marked as completed
            retrieved = store.get_operation(op.id)
            assert retrieved.status == OperationStatus.COMPLETED
            assert retrieved.result == {"status": "success", "data": "result"}

    @pytest.mark.asyncio
    async def test_execute_operation_failure_retry(self, temp_db, mock_etsy, mock_config):
        """Test operation failure with retry."""
        store = OperationStore(temp_db)
        queue = OperationQueue(store, mock_etsy, mock_config)

        # Create a mock operation that fails
        mock_op_def = Mock()
        mock_op_def.execute.side_effect = Exception("Test error")

        with patch('src.operation_queue.REGISTRY') as mock_registry:
            mock_registry.get.return_value = mock_op_def

            op = OperationRequest("test_op", {}, Operation.READ)
            store.create_operation(op)

            # Execute operation
            await queue._execute_operation(op)

            # Operation should be marked as pending for retry
            retrieved = store.get_operation(op.id)
            assert retrieved.status == OperationStatus.PENDING
            assert retrieved._metadata.get("retry_count") == 1

    @pytest.mark.asyncio
    async def test_execute_operation_max_retries_exceeded(self, temp_db, mock_etsy, mock_config):
        """Test operation failure after max retries."""
        store = OperationStore(temp_db)
        mock_config.queue_retry_max_attempts = 2
        queue = OperationQueue(store, mock_etsy, mock_config)

        # Create a mock operation that fails
        mock_op_def = Mock()
        mock_op_def.execute.side_effect = Exception("Test error")

        with patch('src.operation_queue.REGISTRY') as mock_registry:
            mock_registry.get.return_value = mock_op_def

            op = OperationRequest("test_op", {}, Operation.READ)
            op._metadata = {"retry_count": 2}
            store.create_operation(op)

            # Execute operation
            await queue._execute_operation(op)

            # Operation should be marked as failed
            retrieved = store.get_operation(op.id)
            assert retrieved.status == OperationStatus.FAILED
            assert "attempts" in retrieved.error.lower()

    @pytest.mark.asyncio
    async def test_execute_operation_timeout(self, temp_db, mock_etsy, mock_config):
        """Test operation timeout."""
        store = OperationStore(temp_db)
        queue = OperationQueue(store, mock_etsy, mock_config)

        # Create a mock operation that times out
        async def slow_execute(*args, **kwargs):
            await asyncio.sleep(10)

        mock_op_def = Mock()
        mock_op_def.execute = Mock(side_effect=slow_execute)

        with patch('src.operation_queue.REGISTRY') as mock_registry:
            mock_registry.get.return_value = mock_op_def

            op = OperationRequest("test_op", {}, Operation.READ)
            store.create_operation(op)

            # Execute with short timeout
            with patch('src.operation_queue.asyncio.wait_for', side_effect=asyncio.TimeoutError):
                await queue._execute_operation(op)

                # Operation should be marked as pending for retry
                retrieved = store.get_operation(op.id)
                assert retrieved.status == OperationStatus.PENDING


class TestQueueBackgroundTask:
    """Test QueueBackgroundTask class."""

    @pytest.mark.asyncio
    async def test_init(self, temp_db, mock_etsy, mock_config):
        """Test QueueBackgroundTask initialization."""
        store = OperationStore(temp_db)
        queue = OperationQueue(store, mock_etsy, mock_config)
        task_manager = QueueBackgroundTask(queue)

        assert task_manager.queue == queue
        assert task_manager._task is None

    @pytest.mark.asyncio
    async def test_start_and_stop(self, temp_db, mock_etsy, mock_config):
        """Test starting and stopping background task."""
        store = OperationStore(temp_db)
        queue = OperationQueue(store, mock_etsy, mock_config)
        task_manager = QueueBackgroundTask(queue)

        # Start task
        await task_manager.start()
        assert task_manager.is_running() is True

        # Stop task
        await task_manager.stop()
        assert task_manager.is_running() is False

    @pytest.mark.asyncio
    async def test_start_already_running(self, temp_db, mock_etsy, mock_config):
        """Test that start doesn't run twice."""
        store = OperationStore(temp_db)
        queue = OperationQueue(store, mock_etsy, mock_config)
        task_manager = QueueBackgroundTask(queue)

        # Start task
        await task_manager.start()
        assert task_manager.is_running() is True

        # Try to start again - should return early
        await task_manager.start()

        # Should still be running
        assert task_manager.is_running() is True

        # Cleanup
        await task_manager.stop()

    @pytest.mark.asyncio
    async def test_is_running_false_when_not_started(self, temp_db, mock_etsy, mock_config):
        """Test is_running returns False when not started."""
        store = OperationStore(temp_db)
        queue = OperationQueue(store, mock_etsy, mock_config)
        task_manager = QueueBackgroundTask(queue)

        assert task_manager.is_running() is False
