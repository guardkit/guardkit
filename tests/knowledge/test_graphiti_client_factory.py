"""
Tests for GraphitiClientFactory thread-safety (TASK-FIX-GTP1, TASK-AQG-004).

Tests the thread-safe factory pattern that replaces the module-level
singleton. Each thread gets its own GraphitiClient with its own
Neo4j driver bound to that thread's event loop.

Also tests httpx cleanup error suppression (TASK-AQG-004) which prevents
harmless ``RuntimeError('Event loop is closed')`` from httpx
``AsyncClient.aclose()`` from producing noisy ERROR log lines.

Coverage Target: >=85%
Test Count: 21 tests
"""

import asyncio
import pytest
import threading
import concurrent.futures
from unittest.mock import MagicMock, AsyncMock, patch

import guardkit.knowledge.graphiti_client as graphiti_module
from guardkit.knowledge.graphiti_client import (
    GraphitiConfig,
    GraphitiClient,
    GraphitiClientFactory,
    get_graphiti,
    get_factory,
    _suppress_httpx_cleanup_errors,
)


@pytest.fixture(autouse=True)
def reset_factory():
    """Reset module-level factory before/after each test."""
    graphiti_module._factory = None
    graphiti_module._factory_init_attempted = False
    yield
    graphiti_module._factory = None
    graphiti_module._factory_init_attempted = False


# ============================================================================
# 1. Factory Creation Tests (3 tests)
# ============================================================================


class TestFactoryCreation:
    """Tests for GraphitiClientFactory construction and config."""

    def test_factory_stores_config(self):
        """Factory stores the provided config."""
        config = GraphitiConfig(
            enabled=True,
            neo4j_uri="bolt://test:7687",
        )
        factory = GraphitiClientFactory(config)
        assert factory.config is config

    def test_factory_config_is_readonly(self):
        """Config property returns the same frozen config."""
        config = GraphitiConfig(enabled=False)
        factory = GraphitiClientFactory(config)
        assert factory.config.enabled is False
        # Config is frozen — cannot be changed
        with pytest.raises(AttributeError):
            factory.config.enabled = True

    def test_create_client_returns_new_instance_each_time(self):
        """create_client() always returns a fresh GraphitiClient."""
        config = GraphitiConfig(enabled=False)
        factory = GraphitiClientFactory(config)
        c1 = factory.create_client()
        c2 = factory.create_client()
        assert c1 is not c2
        assert isinstance(c1, GraphitiClient)
        assert isinstance(c2, GraphitiClient)


# ============================================================================
# 2. Thread-Local Client Tests (5 tests)
# ============================================================================


class TestThreadLocalClient:
    """Tests for per-thread client storage."""

    def test_get_thread_client_disabled_config_returns_none(self):
        """get_thread_client returns None when config disabled."""
        config = GraphitiConfig(enabled=False)
        factory = GraphitiClientFactory(config)
        assert factory.get_thread_client() is None

    def test_set_thread_client_and_retrieve(self):
        """set_thread_client stores client for current thread."""
        config = GraphitiConfig(enabled=False)
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        factory.set_thread_client(mock_client)

        assert factory.get_thread_client() is mock_client

    def test_same_thread_gets_same_client(self):
        """Same thread gets same client on repeated calls."""
        config = GraphitiConfig(enabled=False)
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        factory.set_thread_client(mock_client)

        c1 = factory.get_thread_client()
        c2 = factory.get_thread_client()
        assert c1 is c2 is mock_client

    def test_set_thread_client_none_clears(self):
        """set_thread_client(None) clears the thread-local client."""
        config = GraphitiConfig(enabled=False)
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        factory.set_thread_client(mock_client)
        assert factory.get_thread_client() is mock_client

        # Clear by setting None — but init_attempted stays True
        factory.set_thread_client(None)
        # Returns None because init_attempted is True and client is None
        assert factory.get_thread_client() is None

    def test_init_attempted_once_per_thread(self):
        """get_thread_client only attempts init once per thread."""
        config = GraphitiConfig(enabled=True)
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=False)

        with patch.object(factory, 'create_client', return_value=mock_client):
            r1 = factory.get_thread_client()  # Attempts init, fails
            r2 = factory.get_thread_client()  # Skips, returns None

        assert r1 is None
        assert r2 is None


# ============================================================================
# 3. Multi-Thread Isolation Tests (4 tests)
# ============================================================================


class TestMultiThreadIsolation:
    """Tests for thread isolation — different threads get different clients."""

    def test_different_threads_get_different_clients(self):
        """Different threads get independent client instances."""
        config = GraphitiConfig(enabled=False)
        factory = GraphitiClientFactory(config)

        clients = {}
        barrier = threading.Barrier(2)

        def worker(thread_name):
            mock = MagicMock(spec=GraphitiClient)
            factory.set_thread_client(mock)
            barrier.wait()
            clients[thread_name] = factory.get_thread_client()

        t1 = threading.Thread(target=worker, args=("t1",))
        t2 = threading.Thread(target=worker, args=("t2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert clients["t1"] is not clients["t2"]

    def test_concurrent_get_thread_client_no_race(self):
        """Concurrent access from multiple threads does not raise."""
        config = GraphitiConfig(enabled=False)
        factory = GraphitiClientFactory(config)
        errors = []

        def worker():
            try:
                result = factory.get_thread_client()
                assert result is None  # Disabled config
            except Exception as e:
                errors.append(e)

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(20)]
            concurrent.futures.wait(futures)

        assert len(errors) == 0

    def test_main_thread_client_not_visible_to_worker(self):
        """Client set in main thread is not visible to worker threads."""
        config = GraphitiConfig(enabled=False)
        factory = GraphitiClientFactory(config)

        main_client = MagicMock(spec=GraphitiClient)
        factory.set_thread_client(main_client)

        worker_result = [None]

        def worker():
            worker_result[0] = factory.get_thread_client()

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        # Main thread has its client
        assert factory.get_thread_client() is main_client
        # Worker thread did NOT see main thread's client
        assert worker_result[0] is None  # Disabled config → None

    def test_worker_thread_client_not_visible_to_main(self):
        """Client set in worker thread is not visible to main thread."""
        config = GraphitiConfig(enabled=False)
        factory = GraphitiClientFactory(config)

        worker_client = MagicMock(spec=GraphitiClient)

        def worker():
            factory.set_thread_client(worker_client)

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        # Main thread should NOT see worker's client
        assert factory.get_thread_client() is None  # Disabled → None


# ============================================================================
# 4. Async Init Tests (2 tests)
# ============================================================================


class TestAsyncInit:
    """Tests for create_and_init_client async method."""

    @pytest.mark.asyncio
    async def test_create_and_init_client_success(self):
        """create_and_init_client returns initialized client."""
        config = GraphitiConfig(enabled=True)
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=True)

        with patch.object(factory, 'create_client', return_value=mock_client):
            client = await factory.create_and_init_client()

        assert client is mock_client
        mock_client.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_and_init_client_failure_returns_none(self):
        """create_and_init_client returns None on init failure."""
        config = GraphitiConfig(enabled=True)
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=False)

        with patch.object(factory, 'create_client', return_value=mock_client):
            client = await factory.create_and_init_client()

        assert client is None


# ============================================================================
# 5. Module-Level get_factory() Tests (1 test)
# ============================================================================


class TestGetFactory:
    """Tests for get_factory() module-level function."""

    def test_get_factory_returns_none_before_init(self):
        """get_factory returns None when no factory initialized."""
        assert get_factory() is None

    def test_get_factory_returns_factory_after_init(self):
        """get_factory returns factory after initialization."""
        config = GraphitiConfig(enabled=False)
        factory = GraphitiClientFactory(config)
        graphiti_module._factory = factory

        assert get_factory() is factory


# ============================================================================
# 6. Unawaited Coroutine Warning Fix Tests (TASK-FIX-FD04)
# ============================================================================


class TestUnawaitedCoroutineWarningFix:
    """Tests for coro.close() in get_thread_client error path.

    When new_event_loop + run_until_complete fails (e.g., FD exhaustion
    causing OSError during event loop creation), the coroutine object
    must be explicitly closed to suppress RuntimeWarning.
    """

    def test_no_runtime_warning_when_new_event_loop_raises_os_error(self):
        """No RuntimeWarning emitted when new_event_loop raises OSError (FD exhaustion)."""
        import warnings

        config = GraphitiConfig(enabled=True)
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        async def mock_init():
            return True

        mock_client.initialize = mock_init

        with patch.object(factory, 'create_client', return_value=mock_client), \
             patch('asyncio.get_running_loop', side_effect=RuntimeError), \
             patch('asyncio.new_event_loop', side_effect=OSError("[Errno 24] Too many open files")):

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = factory.get_thread_client()

            assert result is None
            runtime_warnings = [x for x in w if issubclass(x.category, RuntimeWarning)]
            assert len(runtime_warnings) == 0

    def test_no_runtime_warning_when_run_until_complete_raises(self):
        """No RuntimeWarning emitted on Exception from run_until_complete."""
        import warnings

        config = GraphitiConfig(enabled=True)
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        async def mock_init():
            return True

        mock_client.initialize = mock_init

        mock_loop = MagicMock()
        mock_loop.run_until_complete.side_effect = RuntimeError("connection refused")

        with patch.object(factory, 'create_client', return_value=mock_client), \
             patch('asyncio.get_running_loop', side_effect=RuntimeError), \
             patch('asyncio.new_event_loop', return_value=mock_loop):

            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = factory.get_thread_client()

            assert result is None
            runtime_warnings = [x for x in w if issubclass(x.category, RuntimeWarning)]
            assert len(runtime_warnings) == 0
            # Loop should be closed even on error
            mock_loop.close.assert_called_once()

    def test_successful_init_with_new_event_loop(self):
        """Successful init with new_event_loop + run_until_complete works."""
        config = GraphitiConfig(enabled=True)
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=True)

        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = True

        with patch.object(factory, 'create_client', return_value=mock_client), \
             patch('asyncio.get_running_loop', side_effect=RuntimeError), \
             patch('asyncio.new_event_loop', return_value=mock_loop):

            result = factory.get_thread_client()

        assert result is mock_client
        mock_loop.close.assert_called_once()

    def test_failed_init_returns_none_with_new_event_loop(self):
        """run_until_complete returning False still returns None correctly."""
        config = GraphitiConfig(enabled=True)
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=False)

        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = False

        with patch.object(factory, 'create_client', return_value=mock_client), \
             patch('asyncio.get_running_loop', side_effect=RuntimeError), \
             patch('asyncio.new_event_loop', return_value=mock_loop):

            result = factory.get_thread_client()

        assert result is None
        mock_loop.close.assert_called_once()

    def test_loop_always_closed_even_on_success(self):
        """Event loop is always closed after run_until_complete (success path)."""
        config = GraphitiConfig(enabled=True)
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = True

        with patch.object(factory, 'create_client', return_value=mock_client), \
             patch('asyncio.get_running_loop', side_effect=RuntimeError), \
             patch('asyncio.new_event_loop', return_value=mock_loop):

            factory.get_thread_client()

        mock_loop.close.assert_called_once()


# ============================================================================
# 7. httpx Cleanup Error Suppression Tests (TASK-AQG-004)
# ============================================================================


class TestHttpxCleanupErrorSuppression:
    """Tests for _suppress_httpx_cleanup_errors handler.

    When asyncio.run() / new_event_loop() creates a temporary loop for
    Graphiti client initialization, httpx AsyncClient objects may schedule
    background aclose() tasks. After the loop closes, those pending tasks
    raise RuntimeError('Event loop is closed'). The handler silences these
    specific errors while letting everything else propagate.
    """

    def test_suppresses_event_loop_closed_error(self):
        """Handler silences RuntimeError('Event loop is closed')."""
        loop = asyncio.new_event_loop()
        _suppress_httpx_cleanup_errors(loop)

        # Should not raise or log — silently suppressed
        context = {
            "exception": RuntimeError("Event loop is closed"),
            "message": "Task exception was never retrieved",
        }
        loop.call_exception_handler(context)
        loop.close()

    def test_propagates_other_runtime_errors(self):
        """Handler propagates RuntimeError with different message."""
        loop = asyncio.new_event_loop()

        # Install a base handler first, then our suppressor on top
        captured = []

        def base_handler(_loop, ctx):
            captured.append(ctx)

        loop.set_exception_handler(base_handler)
        _suppress_httpx_cleanup_errors(loop)

        context = {
            "exception": RuntimeError("Something else went wrong"),
            "message": "unexpected error",
        }
        loop.call_exception_handler(context)

        assert len(captured) == 1
        assert str(captured[0]["exception"]) == "Something else went wrong"
        loop.close()

    def test_propagates_non_runtime_errors(self):
        """Handler propagates non-RuntimeError exceptions."""
        loop = asyncio.new_event_loop()

        captured = []

        def base_handler(_loop, ctx):
            captured.append(ctx)

        loop.set_exception_handler(base_handler)
        _suppress_httpx_cleanup_errors(loop)

        context = {
            "exception": ValueError("bad value"),
            "message": "unexpected error",
        }
        loop.call_exception_handler(context)

        assert len(captured) == 1
        assert isinstance(captured[0]["exception"], ValueError)
        loop.close()

    def test_propagates_context_without_exception(self):
        """Handler propagates contexts that have no 'exception' key."""
        loop = asyncio.new_event_loop()

        captured = []

        def base_handler(_loop, ctx):
            captured.append(ctx)

        loop.set_exception_handler(base_handler)
        _suppress_httpx_cleanup_errors(loop)

        context = {"message": "something happened"}
        loop.call_exception_handler(context)

        assert len(captured) == 1
        loop.close()

    def test_preserves_original_handler(self):
        """Handler delegates to pre-existing custom handler for non-suppressed errors."""
        loop = asyncio.new_event_loop()

        original_calls = []

        def original_handler(_loop, ctx):
            original_calls.append(ctx)

        loop.set_exception_handler(original_handler)
        _suppress_httpx_cleanup_errors(loop)

        # Non-suppressed error should reach original handler
        context = {
            "exception": RuntimeError("other error"),
            "message": "test",
        }
        loop.call_exception_handler(context)

        assert len(original_calls) == 1

        # Suppressed error should NOT reach original handler
        suppressed_context = {
            "exception": RuntimeError("Event loop is closed"),
            "message": "Task exception was never retrieved",
        }
        loop.call_exception_handler(suppressed_context)

        assert len(original_calls) == 1  # Still 1, not 2
        loop.close()

    def test_handler_installed_during_get_thread_client(self):
        """_suppress_httpx_cleanup_errors is called during get_thread_client init."""
        config = GraphitiConfig(enabled=True)
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        mock_loop = MagicMock()
        mock_loop.run_until_complete.return_value = True

        with patch.object(factory, 'create_client', return_value=mock_client), \
             patch('asyncio.get_running_loop', side_effect=RuntimeError), \
             patch('asyncio.new_event_loop', return_value=mock_loop), \
             patch('guardkit.knowledge.graphiti_client._suppress_httpx_cleanup_errors') as mock_suppress:

            factory.get_thread_client()

        mock_suppress.assert_called_once_with(mock_loop)
