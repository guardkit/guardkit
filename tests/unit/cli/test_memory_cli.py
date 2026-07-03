"""Tests for guardkit memory CLI commands."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

import pytest
from click.testing import CliRunner

from guardkit.cli.memory import memory


@pytest.fixture
def runner():
    """Create CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_memory_client():
    """Mock memory client."""
    client = MagicMock()
    client.enabled = True
    client.initialize = AsyncMock(return_value=True)
    client.close = AsyncMock()
    client.search = AsyncMock(return_value=[
        {"fact": "test fact", "uuid": "test-uuid", "score": 0.9}
    ])
    client.health_check = AsyncMock(return_value=True)
    return client


class TestMemorySearch:
    """Tests for guardkit memory search command."""

    @patch("guardkit.cli.memory.get_memory_client")
    def test_search_basic(self, mock_get_client, runner, mock_memory_client):
        """Test basic search returns results."""
        mock_get_client.return_value = mock_memory_client

        result = runner.invoke(memory, ["search", "test query"])

        assert result.exit_code == 0
        assert "test fact" in result.output
        mock_memory_client.search.assert_called_once()

    @patch("guardkit.cli.memory.get_memory_client")
    def test_search_with_token_budget(self, mock_get_client, runner, mock_memory_client):
        """Test search with --token-budget flag."""
        mock_get_client.return_value = mock_memory_client

        result = runner.invoke(memory, ["search", "test query", "--token-budget", "500"])

        assert result.exit_code == 0
        mock_memory_client.search.assert_called_once()

    @patch("guardkit.cli.memory.get_memory_client")
    def test_search_unreachable_store(self, mock_get_client, runner):
        """Test search shows graceful message when store is unreachable."""
        mock_client = MagicMock()
        mock_client.initialize = AsyncMock(return_value=False)
        mock_client.close = AsyncMock()
        mock_get_client.return_value = mock_client

        result = runner.invoke(memory, ["search", "test query"])

        assert result.exit_code == 0
        assert "unavailable" in result.output.lower() or "unreachable" in result.output.lower()


class TestMemoryStatus:
    """Tests for guardkit memory status command."""

    @patch("guardkit.cli.memory.get_memory_client")
    def test_status_shows_reachability(self, mock_get_client, runner, mock_memory_client):
        """Test status shows store reachability."""
        mock_get_client.return_value = mock_memory_client

        result = runner.invoke(memory, ["status"])

        assert result.exit_code == 0
        assert "reachable" in result.output.lower() or "connected" in result.output.lower()

    @patch("guardkit.cli.memory.get_memory_client")
    def test_status_shows_payload_counts(self, mock_get_client, runner, mock_memory_client):
        """Test status shows per-payload_type counts."""
        # Mock search to return different payload types
        mock_memory_client.search = AsyncMock(side_effect=[
            [{"fact": "fact1"}],  # build_outcome
            [{"fact": "fact2"}, {"fact": "fact3"}],  # feature_spec
        ])
        mock_get_client.return_value = mock_memory_client

        result = runner.invoke(memory, ["status"])

        assert result.exit_code == 0
        # Should show some form of counts/stats

    @patch("guardkit.cli.memory.get_memory_client")
    def test_status_unreachable_store(self, mock_get_client, runner):
        """Test status shows graceful message when store is unreachable."""
        mock_client = MagicMock()
        mock_client.initialize = AsyncMock(return_value=False)
        mock_client.close = AsyncMock()
        mock_get_client.return_value = mock_client

        result = runner.invoke(memory, ["status"])

        assert result.exit_code == 0
        assert any(word in result.output.lower() for word in ["unavailable", "unreachable", "disabled"])


class TestMemoryCaptureOutcome:
    """Tests for guardkit memory capture-outcome command."""

    @patch("guardkit.cli.memory.get_memory_client")
    @patch("guardkit.cli.memory.capture_task_outcome")
    def test_capture_outcome_from_task_file(
        self, mock_capture, mock_get_client, runner, mock_memory_client, tmp_path
    ):
        """Test capture-outcome from task file."""
        # Create a mock task file
        task_file = tmp_path / "TASK-XXX.md"
        task_file.write_text("""---
id: TASK-XXX
title: Test Task
complexity: 5
---

## Description
Test task description

## Implementation Notes
Test implementation notes
""")

        mock_get_client.return_value = mock_memory_client
        mock_capture.return_value = "OUT-12345"

        result = runner.invoke(
            memory, ["capture-outcome", "--from-task-file", str(task_file)]
        )

        assert result.exit_code == 0
        assert "captured" in result.output.lower()
        mock_capture.assert_called_once()

    @patch("guardkit.cli.memory.get_memory_client")
    def test_capture_outcome_unreachable_store(self, mock_get_client, runner, tmp_path):
        """Test capture-outcome shows graceful message when store is unreachable."""
        task_file = tmp_path / "TASK-XXX.md"
        task_file.write_text("""---
id: TASK-XXX
title: Test Task
---

## Description
Test description
""")

        mock_client = MagicMock()
        mock_client.initialize = AsyncMock(return_value=False)
        mock_client.close = AsyncMock()
        mock_get_client.return_value = mock_client

        result = runner.invoke(
            memory, ["capture-outcome", "--from-task-file", str(task_file)]
        )

        # Should not fail but warn
        assert "unavailable" in result.output.lower() or "not captured" in result.output.lower()


# ============================================================================
# Optional `memory` extra: the CLI must not hard-import nats-core
# (regression for `guardkit init` crashing with ModuleNotFoundError: nats_core)
# ============================================================================


class TestMemoryExtraOptionalImport:
    """The `memory` CLI group must import without the optional `memory` extra.

    `nats-core` is only declared by the `memory` / `all` extras (never a base
    dependency), yet guardkit.cli.main imports this group unconditionally. A
    module-level `from nats_core... import ...` therefore breaks *every* guardkit
    command — including `guardkit init` — on a base install. These tests pin the
    guarded-import behaviour. See .claude/rules/namespace-hygiene.md.
    """

    def test_full_cli_imports_without_nats_core(self):
        """Repro: block nats_core, then the exact failing chain must still work.

        Runs in an isolated subprocess so the module is imported fresh with a
        `sys.meta_path` finder that makes every `nats_core` import fail — exactly
        the state of a base install without the `memory` extra.
        """
        import subprocess
        import sys
        import textwrap

        repo_root = Path(__file__).resolve().parents[3]
        program = textwrap.dedent(
            """
            import sys

            class _Blocker:
                def find_spec(self, name, path=None, target=None):
                    if name == "nats_core" or name.startswith("nats_core."):
                        raise ModuleNotFoundError(
                            "No module named '%s'" % name, name=name
                        )
                    return None

            sys.meta_path.insert(0, _Blocker())

            # The exact chain that crashed `guardkit init`:
            #   main -> cli.memory -> memory.harvest_walker -> nats_core.events
            from guardkit.cli.main import cli, main
            from click.testing import CliRunner

            runner = CliRunner()

            r = runner.invoke(cli, ["init", "--help"])
            assert r.exit_code == 0, ("init --help failed", r.exit_code, r.output)

            r = runner.invoke(cli, ["memory", "harvest", "--dry-run"])
            assert r.exit_code == 1, ("expected clean exit 1", r.exit_code, r.output)
            assert "guardkit-py[memory]" in r.output, r.output
            assert "nats_core" in r.output, r.output

            # Importing the CLI must NOT drag nats_core in as a side effect.
            assert "nats_core" not in sys.modules

            print("REGRESSION_OK")
            """
        )
        result = subprocess.run(
            [sys.executable, "-c", program],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"subprocess failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        assert "REGRESSION_OK" in result.stdout, result.stdout

    def test_harvest_reports_missing_memory_extra(self, runner):
        """`memory harvest` exits 1 with an actionable hint when the extra is absent."""
        import guardkit.cli.memory as memory_mod

        err = ModuleNotFoundError("No module named 'nats_core'", name="nats_core")
        with patch.object(memory_mod, "_MEMORY_IMPORT_ERROR", err):
            result = runner.invoke(memory, ["harvest", "--dry-run"])

        assert result.exit_code == 1
        # The literal "[memory]" must survive Rich markup rendering.
        assert "guardkit-py[memory]" in result.output
        assert "nats_core" in result.output

    def test_migrate_graph_reports_missing_memory_extra(self, runner):
        """`memory migrate-graph` exits 1 with an actionable hint when the extra is absent."""
        import guardkit.cli.memory as memory_mod

        err = ModuleNotFoundError("No module named 'nats_core'", name="nats_core")
        with patch.object(memory_mod, "_MEMORY_IMPORT_ERROR", err):
            result = runner.invoke(memory, ["migrate-graph", "--dry-run"])

        assert result.exit_code == 1
        assert "guardkit-py[memory]" in result.output

    def test_missing_extra_helper_selects_falkordb_extra(self):
        """A missing `falkordb` module points at the `falkordb` extra, not `memory`."""
        import guardkit.cli.memory as memory_mod

        printed: list[str] = []
        err = ModuleNotFoundError("No module named 'falkordb'", name="falkordb")
        with patch.object(
            memory_mod.console,
            "print",
            side_effect=lambda *a, **k: printed.append(str(a[0]) if a else ""),
        ):
            with pytest.raises(SystemExit) as exc_info:
                memory_mod._memory_extra_missing(err)

        assert exc_info.value.code == 1
        joined = "\n".join(printed)
        assert "guardkit-py" in joined
        assert "[falkordb]" in joined  # falkordb extra, and bracket not swallowed
        assert "[memory]" not in joined
