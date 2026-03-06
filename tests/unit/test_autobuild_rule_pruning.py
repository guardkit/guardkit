"""Tests for AutoBuild worktree rule pruning (TASK-daab).

Verifies that non-essential rules are removed from worktrees
after creation, while essential rules are preserved.

Coverage Target: >=85%
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

import sys

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    AUTOBUILD_ESSENTIAL_RULES,
    FEATURE_BUILD_EXTRA_RULES,
)
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def rules_dir(tmp_path):
    """Create a .claude/rules/ directory with realistic rule files."""
    rules = tmp_path / ".claude" / "rules"
    rules.mkdir(parents=True)

    # Essential rules
    for name in AUTOBUILD_ESSENTIAL_RULES:
        (rules / name).write_text(f"# {name} content")

    # Non-essential rules
    non_essential = [
        "clarifying-questions.md",
        "graphiti-knowledge.md",
        "feature-build-invariants.md",
        "python-library.md",
        "task-workflow.md",
    ]
    for name in non_essential:
        (rules / name).write_text(f"# {name} content")

    # Subdirectories
    patterns_dir = rules / "patterns"
    patterns_dir.mkdir()
    (patterns_dir / "orchestrators.md").write_text("# orchestrators")
    (patterns_dir / "pydantic-models.md").write_text("# pydantic")
    (patterns_dir / "dataclasses.md").write_text("# dataclasses")

    guidance_dir = rules / "guidance"
    guidance_dir.mkdir()
    (guidance_dir / "agent-development.md").write_text("# guidance")

    return rules


@pytest.fixture
def orchestrator():
    """Create an AutoBuildOrchestrator with mocked dependencies."""
    mock_manager = Mock()
    mock_manager.worktrees_dir = Path("/tmp/worktrees")

    orch = AutoBuildOrchestrator(
        repo_root=Path("/tmp/repo"),
        worktree_manager=mock_manager,
    )
    return orch


# ============================================================================
# Tests: _prune_worktree_rules
# ============================================================================


class TestPruneWorktreeRules:
    """Tests for the _prune_worktree_rules method."""

    def test_essential_rules_preserved(self, orchestrator, rules_dir, tmp_path):
        """Essential rules remain after pruning."""
        orchestrator._prune_worktree_rules(tmp_path)

        for name in AUTOBUILD_ESSENTIAL_RULES:
            assert (rules_dir / name).exists(), f"{name} should be preserved"

    def test_non_essential_rules_removed(self, orchestrator, rules_dir, tmp_path):
        """Non-essential rule files are removed."""
        orchestrator._prune_worktree_rules(tmp_path)

        assert not (rules_dir / "clarifying-questions.md").exists()
        assert not (rules_dir / "graphiti-knowledge.md").exists()
        assert not (rules_dir / "python-library.md").exists()
        assert not (rules_dir / "task-workflow.md").exists()

    def test_subdirectories_removed(self, orchestrator, rules_dir, tmp_path):
        """Rule subdirectories (patterns/, guidance/) are removed entirely."""
        orchestrator._prune_worktree_rules(tmp_path)

        assert not (rules_dir / "patterns").exists()
        assert not (rules_dir / "guidance").exists()

    def test_no_rules_dir_is_noop(self, orchestrator, tmp_path):
        """Gracefully handles missing .claude/rules/ directory."""
        # No .claude/rules/ directory at all
        orchestrator._prune_worktree_rules(tmp_path)
        # Should not raise

    def test_empty_rules_dir_is_noop(self, orchestrator, tmp_path):
        """Gracefully handles empty .claude/rules/ directory."""
        (tmp_path / ".claude" / "rules").mkdir(parents=True)
        orchestrator._prune_worktree_rules(tmp_path)
        # Should not raise

    def test_feature_mode_keeps_feature_build_invariants(
        self, rules_dir, tmp_path
    ):
        """Feature-build mode preserves feature-build-invariants.md."""
        mock_manager = Mock()
        mock_manager.worktrees_dir = Path("/tmp/worktrees")

        # Simulate feature mode by setting _existing_worktree
        mock_worktree = Mock(spec=Worktree)
        mock_worktree.path = tmp_path

        orch = AutoBuildOrchestrator(
            repo_root=Path("/tmp/repo"),
            worktree_manager=mock_manager,
            existing_worktree=mock_worktree,
        )
        orch._prune_worktree_rules(tmp_path)

        assert (rules_dir / "feature-build-invariants.md").exists()

    def test_non_feature_mode_removes_feature_build_invariants(
        self, orchestrator, rules_dir, tmp_path
    ):
        """Non-feature mode removes feature-build-invariants.md."""
        orchestrator._prune_worktree_rules(tmp_path)

        assert not (rules_dir / "feature-build-invariants.md").exists()

    def test_only_essential_files_remain(self, orchestrator, rules_dir, tmp_path):
        """After pruning, only essential files remain (no extras)."""
        orchestrator._prune_worktree_rules(tmp_path)

        remaining = {f.name for f in rules_dir.iterdir() if f.is_file()}
        assert remaining == set(AUTOBUILD_ESSENTIAL_RULES)

    def test_no_directories_remain(self, orchestrator, rules_dir, tmp_path):
        """After pruning, no subdirectories remain."""
        orchestrator._prune_worktree_rules(tmp_path)

        dirs = [d for d in rules_dir.iterdir() if d.is_dir()]
        assert dirs == []

    def test_claude_md_not_affected(self, orchestrator, tmp_path):
        """CLAUDE.md files outside rules/ are not touched."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir(parents=True)
        (claude_dir / "CLAUDE.md").write_text("# Project context")
        rules = claude_dir / "rules"
        rules.mkdir()
        (rules / "autobuild.md").write_text("# autobuild")
        (rules / "extra.md").write_text("# extra")

        orchestrator._prune_worktree_rules(tmp_path)

        assert (claude_dir / "CLAUDE.md").exists()
        assert (rules / "autobuild.md").exists()
        assert not (rules / "extra.md").exists()


# ============================================================================
# Tests: Constants
# ============================================================================


class TestConstants:
    """Tests for AUTOBUILD_ESSENTIAL_RULES and FEATURE_BUILD_EXTRA_RULES."""

    def test_essential_rules_is_frozenset(self):
        """Essential rules constant is immutable."""
        assert isinstance(AUTOBUILD_ESSENTIAL_RULES, frozenset)

    def test_essential_rules_contains_expected(self):
        """Essential rules contains the four expected files."""
        expected = {"autobuild.md", "anti-stub.md", "hash-based-ids.md", "testing.md"}
        assert AUTOBUILD_ESSENTIAL_RULES == expected

    def test_feature_build_extra_rules_is_frozenset(self):
        """Feature build extra rules constant is immutable."""
        assert isinstance(FEATURE_BUILD_EXTRA_RULES, frozenset)

    def test_feature_build_extra_contains_invariants(self):
        """Feature build extra rules contains feature-build-invariants.md."""
        assert "feature-build-invariants.md" in FEATURE_BUILD_EXTRA_RULES


# ============================================================================
# Tests: Integration with _setup_phase
# ============================================================================


class TestSetupPhaseIntegration:
    """Verify _prune_worktree_rules is called during _setup_phase."""

    def test_setup_phase_calls_prune(self, tmp_path):
        """_setup_phase calls _prune_worktree_rules after worktree creation."""
        mock_worktree = Mock(spec=Worktree)
        mock_worktree.path = tmp_path
        mock_worktree.task_id = "TASK-daab"
        mock_worktree.branch_name = "autobuild/TASK-daab"
        mock_worktree.base_branch = "main"

        mock_manager = Mock()
        mock_manager.create.return_value = mock_worktree
        mock_manager.worktrees_dir = tmp_path

        orch = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_manager,
        )

        with patch.object(orch, "_prune_worktree_rules") as mock_prune:
            orch._setup_phase("TASK-daab", "main")
            mock_prune.assert_called_once_with(tmp_path)

    def test_setup_phase_skips_prune_for_existing_worktree(self, tmp_path):
        """_setup_phase does NOT call _prune_worktree_rules for existing worktrees.

        Existing worktrees (feature mode) may have already been pruned or
        may need their full rule set.  Pruning is only for newly created worktrees.
        """
        mock_worktree = Mock(spec=Worktree)
        mock_worktree.path = tmp_path
        mock_worktree.task_id = "TASK-daab"

        mock_manager = Mock()
        mock_manager.worktrees_dir = tmp_path

        orch = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_manager,
            existing_worktree=mock_worktree,
        )

        with patch.object(orch, "_prune_worktree_rules") as mock_prune:
            orch._setup_phase("TASK-daab", "main")
            mock_prune.assert_not_called()
