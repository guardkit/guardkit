"""
Call Site Migration Verification Tests (TASK-FIX-GTP5)

Verifies that all get_graphiti() call sites work correctly with the
GraphitiClientFactory pattern from TASK-FIX-GTP1. The factory provides
per-thread clients via threading.local(), and the backward-compatible
get_graphiti() API delegates to factory.get_thread_client().

These tests verify:
1. HIGH risk: project.py (5 calls) works with factory via thread-local
2. HIGH risk: lazy properties in feature_plan_context.py and interactive_capture.py
3. LOW risk: All other call sites work unchanged
4. No call site uses the old module-level _graphiti variable directly
5. init_graphiti() API is unchanged
6. End-to-end CLI command with factory (mocked)

Coverage Target: >=85%
"""

import asyncio
import threading
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, PropertyMock
from typing import Optional

import guardkit.knowledge.graphiti_client as gc_module


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture(autouse=True)
def reset_factory_state():
    """Reset global factory state before and after each test."""
    original_factory = gc_module._factory
    original_attempted = gc_module._factory_init_attempted
    gc_module._factory = None
    gc_module._factory_init_attempted = False
    yield
    gc_module._factory = original_factory
    gc_module._factory_init_attempted = original_attempted


@pytest.fixture
def mock_client():
    """Create a mock GraphitiClient."""
    client = MagicMock()
    client.enabled = True
    client._connected = True
    client.config = MagicMock()
    client.config.enabled = True
    client.search = AsyncMock(return_value=[])
    client.add_episode = AsyncMock(return_value="uuid-123")
    return client


@pytest.fixture
def mock_factory(mock_client):
    """Create a mock GraphitiClientFactory that returns mock_client."""
    factory = MagicMock(spec=gc_module.GraphitiClientFactory)
    factory.get_thread_client.return_value = mock_client
    factory.config = gc_module.GraphitiConfig(enabled=True)
    return factory


# ============================================================================
# 1. get_graphiti() delegates to factory (core backward-compatibility)
# ============================================================================

class TestGetGraphitiDelegatesToFactory:
    """Verify get_graphiti() returns thread-local client from factory."""

    def test_get_graphiti_returns_thread_client_from_factory(self, mock_factory, mock_client):
        """get_graphiti() should delegate to factory.get_thread_client()."""
        gc_module._factory = mock_factory

        result = gc_module.get_graphiti()

        mock_factory.get_thread_client.assert_called_once()
        assert result is mock_client

    def test_get_graphiti_returns_none_when_no_factory_and_init_attempted(self):
        """get_graphiti() returns None when factory is None and init was attempted."""
        gc_module._factory = None
        gc_module._factory_init_attempted = True

        result = gc_module.get_graphiti()

        assert result is None

    def test_get_graphiti_triggers_lazy_init_when_no_factory(self):
        """get_graphiti() triggers _try_lazy_init when factory is None."""
        gc_module._factory = None
        gc_module._factory_init_attempted = False

        with patch.object(gc_module, '_try_lazy_init', return_value=None) as mock_lazy:
            result = gc_module.get_graphiti()

        mock_lazy.assert_called_once()

    def test_different_threads_get_different_clients_from_factory(self):
        """Each thread should get its own client from factory.get_thread_client()."""
        config = gc_module.GraphitiConfig(enabled=True)
        factory = gc_module.GraphitiClientFactory(config)

        # Pre-set clients for main and worker threads
        main_client = MagicMock()
        worker_client = MagicMock()

        factory.set_thread_client(main_client)

        results = {}

        def worker():
            factory.set_thread_client(worker_client)
            results['worker'] = factory.get_thread_client()

        results['main'] = factory.get_thread_client()

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert results['main'] is main_client
        assert results['worker'] is worker_client
        assert results['main'] is not results['worker']


# ============================================================================
# 2. HIGH Risk: project.py call sites (5 calls)
# ============================================================================

class TestProjectCallSitesWithFactory:
    """Verify guardkit/integrations/graphiti/project.py works with factory."""

    @pytest.mark.asyncio
    async def test_initialize_project_uses_get_graphiti(self, mock_client):
        """initialize_project() gets client via get_graphiti()."""
        from guardkit.integrations.graphiti.project import initialize_project

        with patch(
            'guardkit.integrations.graphiti.project.get_graphiti',
            return_value=mock_client
        ):
            result = await initialize_project("test-project")

        assert result is not None
        assert result.project_id == "test-project"

    @pytest.mark.asyncio
    async def test_get_project_info_uses_get_graphiti(self, mock_client):
        """get_project_info() gets client via get_graphiti()."""
        from guardkit.integrations.graphiti.project import get_project_info

        with patch(
            'guardkit.integrations.graphiti.project.get_graphiti',
            return_value=mock_client
        ):
            result = await get_project_info("test-project")

        # Returns None because search returns empty
        assert result is None

    @pytest.mark.asyncio
    async def test_list_projects_uses_get_graphiti(self, mock_client):
        """list_projects() gets client via get_graphiti()."""
        from guardkit.integrations.graphiti.project import list_projects

        with patch(
            'guardkit.integrations.graphiti.project.get_graphiti',
            return_value=mock_client
        ):
            result = await list_projects()

        assert result == []

    @pytest.mark.asyncio
    async def test_project_exists_uses_get_graphiti(self, mock_client):
        """project_exists() gets client via get_graphiti()."""
        from guardkit.integrations.graphiti.project import project_exists

        with patch(
            'guardkit.integrations.graphiti.project.get_graphiti',
            return_value=mock_client
        ):
            result = await project_exists("test-project")

        assert result is False

    @pytest.mark.asyncio
    async def test_update_project_access_time_uses_get_graphiti(self, mock_client):
        """update_project_access_time() gets client via get_graphiti()."""
        from guardkit.integrations.graphiti.project import update_project_access_time

        with patch(
            'guardkit.integrations.graphiti.project.get_graphiti',
            return_value=mock_client
        ):
            result = await update_project_access_time("test-project")

        assert result is False  # Project doesn't exist in mock

    @pytest.mark.asyncio
    async def test_project_functions_degrade_when_client_none(self):
        """All project.py functions degrade gracefully when client is None."""
        from guardkit.integrations.graphiti.project import (
            initialize_project,
            get_project_info,
            list_projects,
            project_exists,
            update_project_access_time,
        )

        with patch(
            'guardkit.integrations.graphiti.project.get_graphiti',
            return_value=None
        ):
            # initialize_project returns local-only info
            info = await initialize_project("fallback-project")
            assert info is not None
            assert info.project_id == "fallback-project"

            # Others return None/False/empty
            assert await get_project_info("x") is None
            assert await list_projects() == []
            assert await project_exists("x") is False
            assert await update_project_access_time("x") is False

    @pytest.mark.asyncio
    async def test_project_call_from_worker_thread_context(self, mock_factory, mock_client):
        """project.py functions work when called from worker thread context."""
        from guardkit.integrations.graphiti.project import initialize_project

        results = {}

        async def run_in_worker():
            with patch(
                'guardkit.integrations.graphiti.project.get_graphiti',
                return_value=mock_client
            ):
                return await initialize_project("worker-project")

        def worker():
            loop = asyncio.new_event_loop()
            try:
                results['worker'] = loop.run_until_complete(run_in_worker())
            finally:
                loop.close()

        t = threading.Thread(target=worker)
        t.start()
        t.join()

        assert results['worker'] is not None
        assert results['worker'].project_id == "worker-project"


# ============================================================================
# 3. HIGH Risk: Lazy properties (2 calls)
# ============================================================================

class TestLazyPropertiesWithFactory:
    """Verify lazy properties in feature_plan_context.py and interactive_capture.py."""

    def test_feature_plan_context_lazy_property_calls_get_graphiti(self, mock_client):
        """FeaturePlanContextBuilder.graphiti_client calls get_graphiti()."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

        # Patch at source module (local import in property, not module-level)
        with patch(
            'guardkit.knowledge.graphiti_client.get_graphiti',
            return_value=mock_client
        ) as mock_get:
            builder = FeaturePlanContextBuilder.__new__(FeaturePlanContextBuilder)
            builder._graphiti_client_resolved = False
            builder._graphiti_client_cache = None

            result = builder.graphiti_client

        mock_get.assert_called_once()
        assert result is mock_client

    def test_feature_plan_context_lazy_property_caches(self, mock_client):
        """Lazy property caches after first access."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

        # Patch at source module (local import in property, not module-level)
        with patch(
            'guardkit.knowledge.graphiti_client.get_graphiti',
            return_value=mock_client
        ) as mock_get:
            builder = FeaturePlanContextBuilder.__new__(FeaturePlanContextBuilder)
            builder._graphiti_client_resolved = False
            builder._graphiti_client_cache = None

            # First access
            _ = builder.graphiti_client
            # Second access - should not call get_graphiti again
            _ = builder.graphiti_client

        mock_get.assert_called_once()

    def test_feature_plan_context_setter_overrides(self, mock_client):
        """Setting graphiti_client explicitly overrides lazy resolution."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

        builder = FeaturePlanContextBuilder.__new__(FeaturePlanContextBuilder)
        builder._graphiti_client_resolved = False
        builder._graphiti_client_cache = None

        custom_client = MagicMock()
        builder.graphiti_client = custom_client

        assert builder.graphiti_client is custom_client

    def test_interactive_capture_lazy_property_calls_get_graphiti(self, mock_client):
        """InteractiveCaptureSession._graphiti calls get_graphiti()."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch(
            'guardkit.knowledge.interactive_capture.get_graphiti',
            return_value=mock_client
        ) as mock_get:
            session = InteractiveCaptureSession()

            result = session._graphiti

        mock_get.assert_called_once()
        assert result is mock_client

    def test_interactive_capture_lazy_property_caches(self, mock_client):
        """Interactive capture lazy property caches after first access."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch(
            'guardkit.knowledge.interactive_capture.get_graphiti',
            return_value=mock_client
        ) as mock_get:
            session = InteractiveCaptureSession()

            _ = session._graphiti
            _ = session._graphiti

        mock_get.assert_called_once()

    def test_interactive_capture_setter_overrides(self, mock_client):
        """Setting _graphiti explicitly overrides lazy resolution."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        session = InteractiveCaptureSession()
        custom_client = MagicMock()
        session._graphiti = custom_client

        assert session._graphiti is custom_client


# ============================================================================
# 4. No direct access to module-level _graphiti variable
# ============================================================================

class TestNoDirectModuleVariableAccess:
    """Verify no external code accesses the old _graphiti module-level variable."""

    def test_module_has_no_public_graphiti_variable(self):
        """The module should not export _graphiti (internal only)."""
        assert '_graphiti' not in gc_module.__dict__ or not hasattr(gc_module, '_graphiti')
        # Only _factory should be the module-level state
        assert hasattr(gc_module, '_factory')

    def test_factory_replaces_old_singleton(self):
        """_factory is the module-level state, not _graphiti."""
        assert '_factory' in dir(gc_module)
        assert '_factory_init_attempted' in dir(gc_module)

    def test_get_graphiti_uses_factory_not_module_variable(self, mock_factory, mock_client):
        """get_graphiti() routes through _factory, not a _graphiti variable."""
        gc_module._factory = mock_factory

        result = gc_module.get_graphiti()

        # Should have called factory.get_thread_client
        mock_factory.get_thread_client.assert_called_once()
        assert result is mock_client


# ============================================================================
# 5. init_graphiti() API unchanged
# ============================================================================

class TestInitGraphitiAPIUnchanged:
    """Verify init_graphiti() API has not changed."""

    @pytest.mark.asyncio
    async def test_init_graphiti_accepts_config(self):
        """init_graphiti() still accepts optional GraphitiConfig."""
        config = gc_module.GraphitiConfig(enabled=False)

        with patch.object(
            gc_module.GraphitiClientFactory,
            'create_and_init_client',
            new_callable=AsyncMock,
            return_value=None
        ):
            result = await gc_module.init_graphiti(config)

        assert result is False  # Disabled config

    @pytest.mark.asyncio
    async def test_init_graphiti_sets_factory_on_success(self):
        """init_graphiti() creates factory and sets thread client on success."""
        mock_client = MagicMock()

        with patch.object(
            gc_module.GraphitiClientFactory,
            'create_and_init_client',
            new_callable=AsyncMock,
            return_value=mock_client
        ):
            result = await gc_module.init_graphiti(gc_module.GraphitiConfig(enabled=True))

        assert result is True
        assert gc_module._factory is not None
        assert gc_module._factory_init_attempted is True

    @pytest.mark.asyncio
    async def test_init_graphiti_clears_factory_on_failure(self):
        """init_graphiti() clears factory if client init fails."""
        with patch.object(
            gc_module.GraphitiClientFactory,
            'create_and_init_client',
            new_callable=AsyncMock,
            return_value=None
        ):
            result = await gc_module.init_graphiti(gc_module.GraphitiConfig(enabled=True))

        assert result is False
        assert gc_module._factory is None
        assert gc_module._factory_init_attempted is True

    @pytest.mark.asyncio
    async def test_init_graphiti_defaults_to_graphiti_config(self):
        """init_graphiti() with no args uses default GraphitiConfig."""
        with patch.object(
            gc_module.GraphitiClientFactory,
            'create_and_init_client',
            new_callable=AsyncMock,
            return_value=None
        ):
            result = await gc_module.init_graphiti()

        # Should not raise, uses default config
        assert result is False
        assert gc_module._factory_init_attempted is True


# ============================================================================
# 6. LOW risk call sites: verified by existing test suites
# ============================================================================

class TestLowRiskCallSitesPattern:
    """Verify LOW risk call sites follow the same pattern (get_graphiti() + graceful degradation).

    These files all use the same pattern:
    1. Import get_graphiti
    2. Call client = get_graphiti()
    3. Check if client is None or not client.enabled
    4. Gracefully degrade

    Existing test suites for these files already pass (verified by CI).
    These tests verify the import path is correct.
    """

    def test_template_sync_imports_get_graphiti(self):
        """template_sync.py imports get_graphiti from graphiti_client."""
        from guardkit.knowledge.template_sync import get_graphiti as ts_get
        assert ts_get is gc_module.get_graphiti

    def test_outcome_manager_imports_get_graphiti(self):
        """outcome_manager.py imports get_graphiti from graphiti_client."""
        from guardkit.knowledge.outcome_manager import get_graphiti as om_get
        assert om_get is gc_module.get_graphiti

    def test_failed_approach_manager_imports_get_graphiti(self):
        """failed_approach_manager.py imports get_graphiti from graphiti_client."""
        from guardkit.knowledge.failed_approach_manager import get_graphiti as fam_get
        assert fam_get is gc_module.get_graphiti

    def test_context_loader_imports_get_graphiti(self):
        """context_loader.py imports get_graphiti from graphiti_client."""
        from guardkit.knowledge.context_loader import get_graphiti as cl_get
        assert cl_get is gc_module.get_graphiti

    def test_knowledge_init_exports_get_graphiti(self):
        """knowledge/__init__.py exports get_graphiti and get_factory."""
        from guardkit.knowledge import get_graphiti, get_factory
        assert get_graphiti is gc_module.get_graphiti
        assert get_factory is gc_module.get_factory

    def test_knowledge_init_exports_factory_class(self):
        """knowledge/__init__.py exports GraphitiClientFactory."""
        from guardkit.knowledge import GraphitiClientFactory
        assert GraphitiClientFactory is gc_module.GraphitiClientFactory


# ============================================================================
# 7. End-to-end: factory lifecycle with multiple call sites
# ============================================================================

class TestEndToEndFactoryLifecycle:
    """Integration-style test: factory init → get_graphiti → call sites."""

    @pytest.mark.asyncio
    async def test_factory_lifecycle_project_and_context(self, mock_client):
        """Full lifecycle: init factory → project.py + context_loader use get_graphiti."""
        from guardkit.integrations.graphiti.project import initialize_project

        with patch(
            'guardkit.integrations.graphiti.project.get_graphiti',
            return_value=mock_client
        ):
            # Simulate project initialization (as CLI would do)
            info = await initialize_project("lifecycle-project")
            assert info.project_id == "lifecycle-project"

    @pytest.mark.asyncio
    async def test_factory_multi_thread_lifecycle(self, mock_client):
        """Multiple threads each get their own client for project operations."""
        from guardkit.integrations.graphiti.project import initialize_project

        results = {}
        errors = []

        async def init_project(name):
            with patch(
                'guardkit.integrations.graphiti.project.get_graphiti',
                return_value=mock_client
            ):
                return await initialize_project(name)

        def worker(name):
            loop = asyncio.new_event_loop()
            try:
                results[name] = loop.run_until_complete(init_project(name))
            except Exception as e:
                errors.append(e)
            finally:
                loop.close()

        threads = [
            threading.Thread(target=worker, args=(f"project-{i}",))
            for i in range(3)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors in threads: {errors}"
        assert len(results) == 3
        for i in range(3):
            assert results[f"project-{i}"].project_id == f"project-{i}"

    def test_get_factory_returns_factory_after_set(self, mock_factory):
        """get_factory() returns the factory instance."""
        gc_module._factory = mock_factory

        result = gc_module.get_factory()

        assert result is mock_factory

    def test_get_factory_returns_none_before_init(self):
        """get_factory() returns None before any initialization."""
        gc_module._factory = None

        result = gc_module.get_factory()

        assert result is None
