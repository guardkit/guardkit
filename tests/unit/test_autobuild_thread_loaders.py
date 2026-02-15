"""
Unit Tests for AutoBuild Thread Loader Storage (TASK-ACR-005)

Tests the storage of event loop references alongside thread loaders in
AutoBuildOrchestrator._thread_loaders dictionary. Verifies that each thread's
loader is stored with the correct event loop for proper cleanup.

Coverage Target: >=80%
Test Organization:
    - Test loader storage with event loop
    - Test cache hit returns correct loader
    - Test None case still stores loop
    - Test cleanup uses stored loop

References:
    - TASK-ACR-005: Store event loop reference with thread loaders
    - TASK-FIX-GTP2: Per-thread Graphiti client storage
"""

import asyncio
import pytest
import sys
import threading
from pathlib import Path
from unittest.mock import Mock, AsyncMock, MagicMock, patch

# Add guardkit to path
_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_graphiti_client():
    """Create a mock GraphitiClient."""
    client = MagicMock()

    # Make initialize return True asynchronously
    async def mock_initialize():
        return True

    client.initialize = AsyncMock(side_effect=mock_initialize)
    client.close = AsyncMock()
    client.enabled = True

    return client


@pytest.fixture
def mock_graphiti_client_failed():
    """Create a mock GraphitiClient that fails initialization."""
    client = MagicMock()

    # Make initialize return False
    async def mock_initialize():
        return False

    client.initialize = AsyncMock(side_effect=mock_initialize)
    client.enabled = True

    return client


@pytest.fixture
def mock_factory(mock_graphiti_client):
    """Create a mock GraphitiClientFactory."""
    factory = Mock()
    factory.create_client.return_value = mock_graphiti_client
    return factory


@pytest.fixture
def mock_factory_failed(mock_graphiti_client_failed):
    """Create a mock GraphitiClientFactory that creates failing clients."""
    factory = Mock()
    factory.create_client.return_value = mock_graphiti_client_failed
    return factory


@pytest.fixture
def mock_worktree():
    """Create a mock Worktree."""
    worktree = Mock()
    worktree.path = Path("/tmp/mock-worktree")
    worktree.branch = "autobuild/TASK-ACR-005"
    return worktree


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    """Create a mock WorktreeManager."""
    manager = Mock()
    manager.create.return_value = mock_worktree
    return manager


@pytest.fixture
def mock_agent_invoker():
    """Create a mock AgentInvoker."""
    invoker = Mock()
    return invoker


@pytest.fixture
def mock_progress_display():
    """Create a mock ProgressDisplay."""
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=None)
    return display


# ============================================================================
# Test: Loader Storage with Event Loop (AC-001, AC-002)
# ============================================================================


class TestLoaderStorageWithEventLoop:
    """Tests for storing loader with event loop reference."""

    def test_get_thread_local_loader_stores_loop_with_loader(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_factory,
    ):
        """
        Given AutoBuildOrchestrator with enable_context=True
        When _get_thread_local_loader is called with an event loop
        Then _thread_loaders stores tuple of (loader, loop)

        Acceptance Criteria: AC-001, AC-002
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        # Set the factory
        orchestrator._factory = mock_factory

        # Create a known event loop
        loop = asyncio.new_event_loop()

        try:
            # Call _get_thread_local_loader with the loop
            loader = orchestrator._get_thread_local_loader(loop)

            # Verify storage format
            thread_id = threading.get_ident()
            assert thread_id in orchestrator._thread_loaders, \
                "Thread ID should be in _thread_loaders"

            entry = orchestrator._thread_loaders[thread_id]
            assert isinstance(entry, tuple), \
                "_thread_loaders entry should be a tuple"
            assert len(entry) == 2, \
                "_thread_loaders entry should have exactly 2 elements"

            stored_loader, stored_loop = entry
            assert stored_loader is loader, \
                "Stored loader should match returned loader"
            assert stored_loop is loop, \
                "Stored loop should match the loop passed in"
        finally:
            loop.close()

    def test_get_thread_local_loader_returns_correct_loader(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_factory,
    ):
        """
        Given AutoBuildOrchestrator with a cached loader
        When _get_thread_local_loader is called again
        Then the cached loader is returned (not the tuple)

        Acceptance Criteria: AC-003
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        orchestrator._factory = mock_factory
        loop = asyncio.new_event_loop()

        try:
            # First call to create and cache
            loader1 = orchestrator._get_thread_local_loader(loop)

            # Second call should return cached loader (not tuple)
            loader2 = orchestrator._get_thread_local_loader(loop)

            assert loader2 is loader1, \
                "Cache hit should return the same loader instance"
            assert loader2 is not None, \
                "Cached loader should not be None"
        finally:
            loop.close()


# ============================================================================
# Test: None Case Stores Loop (AC-002)
# ============================================================================


class TestNoneCaseStoresLoop:
    """Tests for None loader case still storing loop."""

    def test_failed_init_stores_none_with_loop(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_factory_failed,
    ):
        """
        Given AutoBuildOrchestrator with a factory that creates failing clients
        When _get_thread_local_loader is called
        Then _thread_loaders stores (None, loop)

        Acceptance Criteria: AC-002
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        orchestrator._factory = mock_factory_failed
        loop = asyncio.new_event_loop()

        try:
            # Call with failing factory
            loader = orchestrator._get_thread_local_loader(loop)

            # Verify None is returned
            assert loader is None, \
                "Failed init should return None"

            # Verify storage still contains loop
            thread_id = threading.get_ident()
            entry = orchestrator._thread_loaders[thread_id]
            stored_loader, stored_loop = entry

            assert stored_loader is None, \
                "Stored loader should be None after failed init"
            assert stored_loop is loop, \
                "Stored loop should still be the event loop"
        finally:
            loop.close()

    def test_exception_stores_none_with_loop(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given AutoBuildOrchestrator with a factory that raises exception
        When _get_thread_local_loader is called
        Then _thread_loaders stores (None, loop)

        Acceptance Criteria: AC-002
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        # Set factory that raises exception
        factory = Mock()
        factory.create_client.side_effect = RuntimeError("Test error")
        orchestrator._factory = factory

        loop = asyncio.new_event_loop()

        try:
            # Call with failing factory
            loader = orchestrator._get_thread_local_loader(loop)

            # Verify None is returned
            assert loader is None, \
                "Exception should result in None loader"

            # Verify storage still contains loop
            thread_id = threading.get_ident()
            entry = orchestrator._thread_loaders[thread_id]
            stored_loader, stored_loop = entry

            assert stored_loader is None, \
                "Stored loader should be None after exception"
            assert stored_loop is loop, \
                "Stored loop should still be the event loop"
        finally:
            loop.close()


# ============================================================================
# Test: Cleanup Uses Stored Loop (AC-005)
# ============================================================================


class TestCleanupUsesStoredLoop:
    """Tests for cleanup using stored event loop."""

    def test_cleanup_uses_stored_loop_not_new_loop(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_factory,
        mock_graphiti_client,
    ):
        """
        Given AutoBuildOrchestrator with a cached loader
        When _cleanup_thread_loaders is called
        Then close() is run on the stored event loop

        Acceptance Criteria: AC-005
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        orchestrator._factory = mock_factory
        loop = asyncio.new_event_loop()

        try:
            # Create a loader (stores loader + loop)
            loader = orchestrator._get_thread_local_loader(loop)

            # Verify loader has graphiti client
            assert loader is not None
            assert loader.graphiti is mock_graphiti_client

            # Spy on loop.run_until_complete
            original_run = loop.run_until_complete
            run_calls = []

            def spy_run(coro):
                run_calls.append(coro)
                return original_run(coro)

            loop.run_until_complete = spy_run

            # Call cleanup
            orchestrator._cleanup_thread_loaders()

            # Verify close was called via the stored loop
            assert mock_graphiti_client.close.called, \
                "Graphiti client close should be called"
            assert len(run_calls) == 1, \
                "run_until_complete should be called exactly once"

            # Verify _thread_loaders was cleared
            assert len(orchestrator._thread_loaders) == 0, \
                "_thread_loaders should be empty after cleanup"
        finally:
            loop.close()

    def test_cleanup_handles_none_loader_gracefully(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
        mock_factory_failed,
    ):
        """
        Given AutoBuildOrchestrator with None loader (failed init)
        When _cleanup_thread_loaders is called
        Then cleanup completes without error

        Acceptance Criteria: AC-005
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        orchestrator._factory = mock_factory_failed
        loop = asyncio.new_event_loop()

        try:
            # Create a None loader (failed init)
            loader = orchestrator._get_thread_local_loader(loop)
            assert loader is None

            # Call cleanup (should not raise)
            orchestrator._cleanup_thread_loaders()

            # Verify cleanup completed
            assert len(orchestrator._thread_loaders) == 0, \
                "_thread_loaders should be empty after cleanup"
        finally:
            loop.close()


# ============================================================================
# Test: Thread Lock Protection (AC-004)
# ============================================================================


class TestThreadLockProtection:
    """Tests for thread safety of _thread_loaders access."""

    def test_concurrent_access_does_not_corrupt_dict(
        self,
        mock_worktree_manager,
        mock_agent_invoker,
        mock_progress_display,
    ):
        """
        Given AutoBuildOrchestrator accessed by multiple threads
        When each thread calls _get_thread_local_loader
        Then each thread gets its own loader-loop tuple without corruption

        Acceptance Criteria: AC-004
        Note: GIL provides sufficient protection for dict operations in CPython
        """
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
        import concurrent.futures

        orchestrator = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            max_turns=3,
            enable_context=True,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
        )

        # Use a barrier to ensure all threads start simultaneously
        # and each factory call returns a distinct client
        barrier = threading.Barrier(3)

        def make_client():
            client = MagicMock()
            async def mock_init():
                return True
            client.initialize = AsyncMock(side_effect=mock_init)
            client.close = AsyncMock()
            client.enabled = True
            return client

        factory = Mock()
        factory.create_client.side_effect = lambda: make_client()
        orchestrator._factory = factory

        # Function to run in each thread
        def worker_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                barrier.wait(timeout=5)
                loader = orchestrator._get_thread_local_loader(loop)
                thread_id = threading.get_ident()

                # Verify this thread's entry exists and is a tuple
                entry = orchestrator._thread_loaders.get(thread_id)
                assert entry is not None, \
                    "Thread should have its own entry"
                assert isinstance(entry, tuple) and len(entry) == 2, \
                    "Entry should be a (loader, loop) tuple"

                stored_loader, stored_loop = entry
                assert stored_loader is loader, \
                    "Thread's stored loader should match returned loader"

                return thread_id
            finally:
                loop.close()

        # Run in multiple threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(worker_thread) for _ in range(3)]
            results = [f.result() for f in futures]

        # Verify each thread got unique entry
        assert len(set(results)) == 3, \
            "Each thread should have unique thread ID"

        # Verify all entries were stored and are tuples
        assert len(orchestrator._thread_loaders) == 3, \
            "All three thread entries should be stored"
        for tid, entry in orchestrator._thread_loaders.items():
            assert isinstance(entry, tuple) and len(entry) == 2, \
                f"Entry for thread {tid} should be a (loader, loop) tuple"
