"""Tests for FalkorDB decorator workaround (TASK-FKDB-32D9).

Tests the monkey-patch that fixes the @handle_multiple_group_ids decorator
in graphiti-core to support single group_id searches on FalkorDB.
"""

import asyncio
import functools
import importlib
import sys
from unittest.mock import MagicMock, AsyncMock, patch
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_workaround_state():
    """Reset workaround state between tests."""
    from guardkit.knowledge.falkordb_workaround import remove_workaround
    remove_workaround()
    yield
    remove_workaround()


# ---------------------------------------------------------------------------
# Test: apply_falkordb_workaround()
# ---------------------------------------------------------------------------

class TestApplyWorkaround:
    """Tests for apply_falkordb_workaround()."""

    def test_returns_true_when_graphiti_available(self):
        """Workaround applies successfully when graphiti-core is installed."""
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        result = apply_falkordb_workaround()
        assert result is True

    def test_idempotent_multiple_calls(self):
        """Calling apply multiple times is safe and returns True."""
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        assert apply_falkordb_workaround() is True
        assert apply_falkordb_workaround() is True

    def test_returns_false_when_graphiti_not_installed(self):
        """Returns False when graphiti-core is not available."""
        from guardkit.knowledge.falkordb_workaround import (
            apply_falkordb_workaround,
            remove_workaround,
        )
        remove_workaround()

        with patch.dict(sys.modules, {"graphiti_core.decorators": None}):
            # Need fresh import to trigger the ImportError path
            import guardkit.knowledge.falkordb_workaround as mod
            importlib.reload(mod)
            mod.remove_workaround()
            result = mod.apply_falkordb_workaround()
            assert result is False

        # Restore module
        importlib.reload(mod)

    def test_patches_decorator_module(self):
        """Workaround replaces the decorator function in graphiti_core.decorators."""
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        import graphiti_core.decorators as decorators_module

        original = decorators_module.handle_multiple_group_ids
        apply_falkordb_workaround()
        patched = decorators_module.handle_multiple_group_ids

        # The function should have been replaced
        assert patched is not original

    def test_is_workaround_applied_tracks_state(self):
        """is_workaround_applied() correctly tracks whether patch was applied."""
        from guardkit.knowledge.falkordb_workaround import (
            apply_falkordb_workaround,
            is_workaround_applied,
        )
        assert is_workaround_applied() is False
        apply_falkordb_workaround()
        assert is_workaround_applied() is True

    def test_remove_workaround_resets_state(self):
        """remove_workaround() resets the applied flag."""
        from guardkit.knowledge.falkordb_workaround import (
            apply_falkordb_workaround,
            is_workaround_applied,
            remove_workaround,
        )
        apply_falkordb_workaround()
        assert is_workaround_applied() is True
        remove_workaround()
        assert is_workaround_applied() is False


# ---------------------------------------------------------------------------
# Test: Patched decorator behavior
# ---------------------------------------------------------------------------

class TestPatchedDecoratorBehavior:
    """Tests that the patched decorator correctly handles single group_ids."""

    def _make_mock_graphiti(self, provider_name="FALKORDB"):
        """Create a mock Graphiti instance with FalkorDB provider."""
        from graphiti_core.driver.driver import GraphProvider

        mock = MagicMock()
        mock.clients = MagicMock()
        mock.clients.driver = MagicMock()
        mock.clients.driver.provider = (
            GraphProvider.FALKORDB if provider_name == "FALKORDB"
            else GraphProvider.NEO4J
        )
        mock.clients.driver.clone = MagicMock(return_value=MagicMock())
        mock.max_coroutines = None
        return mock

    def test_single_group_id_triggers_clone(self):
        """Single group_id should trigger driver clone after patch."""
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        apply_falkordb_workaround()

        import graphiti_core.decorators as decorators_module

        # Create a test function decorated with the patched decorator
        @decorators_module.handle_multiple_group_ids
        async def test_search(self, query, group_ids=None, driver=None):
            return [f"result_from_{driver}"]

        mock_self = self._make_mock_graphiti("FALKORDB")
        mock_self.clients.driver.clone.return_value = MagicMock(name="cloned_driver")

        # Run with single group_id
        result = asyncio.run(test_search(mock_self, "test query", group_ids=["group_a"]))

        # Should have cloned the driver for group_a
        mock_self.clients.driver.clone.assert_called_once_with(database="group_a")

    def test_multiple_group_ids_still_works(self):
        """Multiple group_ids should continue to work."""
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        apply_falkordb_workaround()

        import graphiti_core.decorators as decorators_module

        @decorators_module.handle_multiple_group_ids
        async def test_search(self, query, group_ids=None, driver=None):
            return [f"result"]

        mock_self = self._make_mock_graphiti("FALKORDB")
        mock_self.clients.driver.clone.return_value = MagicMock()

        result = asyncio.run(test_search(mock_self, "test", group_ids=["a", "b"]))

        # Should have cloned for both groups
        assert mock_self.clients.driver.clone.call_count == 2

    def test_neo4j_provider_not_affected(self):
        """Neo4j provider should not be affected by the patch."""
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        apply_falkordb_workaround()

        import graphiti_core.decorators as decorators_module

        call_count = 0

        @decorators_module.handle_multiple_group_ids
        async def test_search(self, query, group_ids=None, driver=None):
            nonlocal call_count
            call_count += 1
            return ["direct_result"]

        mock_self = self._make_mock_graphiti("NEO4J")

        result = asyncio.run(test_search(mock_self, "test", group_ids=["group_a"]))

        # Neo4j should NOT trigger the FalkorDB clone path
        mock_self.clients.driver.clone.assert_not_called()
        assert call_count == 1

    def test_no_group_ids_falls_through(self):
        """No group_ids should fall through to normal execution."""
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        apply_falkordb_workaround()

        import graphiti_core.decorators as decorators_module

        call_count = 0

        @decorators_module.handle_multiple_group_ids
        async def test_search(self, query, group_ids=None, driver=None):
            nonlocal call_count
            call_count += 1
            return ["direct_result"]

        mock_self = self._make_mock_graphiti("FALKORDB")

        result = asyncio.run(test_search(mock_self, "test"))

        # Should fall through without cloning
        mock_self.clients.driver.clone.assert_not_called()
        assert call_count == 1

    def test_empty_group_ids_falls_through(self):
        """Empty group_ids list should fall through to normal execution."""
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        apply_falkordb_workaround()

        import graphiti_core.decorators as decorators_module

        call_count = 0

        @decorators_module.handle_multiple_group_ids
        async def test_search(self, query, group_ids=None, driver=None):
            nonlocal call_count
            call_count += 1
            return ["direct_result"]

        mock_self = self._make_mock_graphiti("FALKORDB")

        result = asyncio.run(test_search(mock_self, "test", group_ids=[]))

        mock_self.clients.driver.clone.assert_not_called()
        assert call_count == 1


# ---------------------------------------------------------------------------
# Test: Fulltext query sanitization (TASK-REV-661E)
# ---------------------------------------------------------------------------

class TestFulltextQuerySanitization:
    """Tests that build_fulltext_query_fixed pre-sanitizes characters missed by upstream."""

    def _get_patched_build(self):
        """Apply workaround and return the patched build_fulltext_query."""
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        apply_falkordb_workaround()
        from graphiti_core.driver.falkordb_driver import FalkorDriver
        driver = FalkorDriver.__new__(FalkorDriver)
        return driver.build_fulltext_query

    def test_backticks_stripped(self):
        """Backticks in query text should be replaced with spaces."""
        build = self._get_patched_build()
        from graphiti_core.driver.falkordb_driver import FalkorDriver
        driver = FalkorDriver.__new__(FalkorDriver)
        result = driver.build_fulltext_query("`smoke` `regression`")
        assert '`' not in result
        # smoke and regression should still appear as search terms
        assert 'smoke' in result
        assert 'regression' in result

    def test_forward_slashes_stripped(self):
        """Forward slashes in query text should be replaced with spaces."""
        from graphiti_core.driver.falkordb_driver import FalkorDriver
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        apply_falkordb_workaround()
        driver = FalkorDriver.__new__(FalkorDriver)
        result = driver.build_fulltext_query("claude/commands/feature")
        assert '/' not in result
        assert 'claude' in result
        assert 'commands' in result
        assert 'feature' in result

    def test_pipes_stripped(self):
        """Pipe characters in query text should be replaced with spaces."""
        from graphiti_core.driver.falkordb_driver import FalkorDriver
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        apply_falkordb_workaround()
        driver = FalkorDriver.__new__(FalkorDriver)
        result = driver.build_fulltext_query("word1|word2")
        # The pipe is stripped to space, so both words should survive
        # (they become separate tokens joined by ' | ' in the query)
        assert 'word1' in result
        assert 'word2' in result

    def test_backslashes_stripped(self):
        """Backslashes in query text should be replaced with spaces."""
        from graphiti_core.driver.falkordb_driver import FalkorDriver
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        apply_falkordb_workaround()
        driver = FalkorDriver.__new__(FalkorDriver)
        result = driver.build_fulltext_query("path\\to\\file")
        assert '\\' not in result
        assert 'path' in result
        assert 'file' in result

    def test_real_failing_query_from_seed_log(self):
        """Reproduce the exact failing query from the TASK-REV-661E seed log."""
        from graphiti_core.driver.falkordb_driver import FalkorDriver
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        apply_falkordb_workaround()
        driver = FalkorDriver.__new__(FalkorDriver)
        # This is the entity name that caused the first RediSearch error
        result = driver.build_fulltext_query("Slash command `claude/commands/feature spec md`")
        assert '`' not in result
        assert '/' not in result
        # Should produce a valid RediSearch query (no syntax-breaking chars)
        assert 'Slash' in result or 'slash' in result.lower()

    def test_empty_after_sanitization_returns_star(self):
        """Query that becomes empty after sanitization should return '*'."""
        from graphiti_core.driver.falkordb_driver import FalkorDriver
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        apply_falkordb_workaround()
        driver = FalkorDriver.__new__(FalkorDriver)
        # All characters are special + stopwords
        result = driver.build_fulltext_query("`/|\\`")
        assert result == '*'


# ---------------------------------------------------------------------------
# Test: Integration with _check_graphiti_core()
# ---------------------------------------------------------------------------

class TestCheckGraphitiCoreIntegration:
    """Tests that the workaround is applied when _check_graphiti_core() runs."""

    def test_check_graphiti_core_applies_workaround(self):
        """_check_graphiti_core() should apply the FalkorDB workaround."""
        from guardkit.knowledge.falkordb_workaround import is_workaround_applied, remove_workaround
        remove_workaround()

        # Reset the _graphiti_core_available flag to force re-check
        import guardkit.knowledge.graphiti_client as gc_module
        gc_module._graphiti_core_available = None

        gc_module._check_graphiti_core()

        assert is_workaround_applied() is True

        # Restore
        gc_module._graphiti_core_available = None


# ---------------------------------------------------------------------------
# Test: Upstream fix detection
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Test: Re-decoration of already-bound Graphiti methods
# ---------------------------------------------------------------------------

class TestMethodRedecoration:
    """Tests that the workaround re-decorates already-bound Graphiti methods."""

    def test_graphiti_search_is_redecorated(self):
        """Graphiti.search should be re-decorated with the fixed decorator."""
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        from graphiti_core import Graphiti

        original_search = Graphiti.search
        apply_falkordb_workaround()
        patched_search = Graphiti.search

        # The method should have been replaced
        assert patched_search is not original_search

    def test_all_decorated_methods_are_redecorated(self):
        """All 4 decorated methods should be re-decorated."""
        from guardkit.knowledge.falkordb_workaround import (
            apply_falkordb_workaround,
            _DECORATED_METHODS,
        )
        from graphiti_core import Graphiti

        originals = {}
        for name in _DECORATED_METHODS:
            originals[name] = getattr(Graphiti, name)

        apply_falkordb_workaround()

        for name in _DECORATED_METHODS:
            patched = getattr(Graphiti, name)
            assert patched is not originals[name], f"{name} was not re-decorated"

    def test_remove_workaround_restores_original_methods(self):
        """remove_workaround() should restore the original methods on Graphiti."""
        from guardkit.knowledge.falkordb_workaround import (
            apply_falkordb_workaround,
            remove_workaround,
            _DECORATED_METHODS,
        )
        from graphiti_core import Graphiti

        originals = {}
        for name in _DECORATED_METHODS:
            originals[name] = getattr(Graphiti, name)

        apply_falkordb_workaround()
        remove_workaround()

        for name in _DECORATED_METHODS:
            restored = getattr(Graphiti, name)
            assert restored is originals[name], f"{name} was not restored"

    def test_redecorated_search_has_wrapped(self):
        """Re-decorated search should still have __wrapped__ attribute."""
        from guardkit.knowledge.falkordb_workaround import apply_falkordb_workaround
        from graphiti_core import Graphiti

        apply_falkordb_workaround()
        assert hasattr(Graphiti.search, "__wrapped__")


# ---------------------------------------------------------------------------
# Test: Upstream fix detection
# ---------------------------------------------------------------------------

class TestUpstreamFixDetection:
    """Tests that the workaround detects when upstream fix is already applied."""

    def test_skips_when_already_fixed_upstream(self):
        """Workaround should skip if upstream source already has >= 1."""
        from guardkit.knowledge.falkordb_workaround import (
            apply_falkordb_workaround,
            remove_workaround,
        )
        remove_workaround()

        # Mock the source to simulate upstream fix
        fixed_source = '''
def handle_multiple_group_ids(func):
    async def wrapper(self, *args, **kwargs):
        if len(group_ids) >= 1:
            pass
    return wrapper
'''
        with patch("inspect.getsource", return_value=fixed_source):
            result = apply_falkordb_workaround()
            assert result is True

    def test_warns_on_unexpected_source_change(self):
        """Workaround should warn if source changed unexpectedly."""
        from guardkit.knowledge.falkordb_workaround import (
            apply_falkordb_workaround,
            remove_workaround,
        )
        remove_workaround()

        # Mock source with neither > 1 nor >= 1
        unexpected_source = '''
def handle_multiple_group_ids(func):
    async def wrapper(self, *args, **kwargs):
        if completely_different_logic:
            pass
    return wrapper
'''
        with patch("inspect.getsource", return_value=unexpected_source):
            result = apply_falkordb_workaround()
            assert result is False
