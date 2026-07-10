"""Tests for flag-gated file_path_hints wiring (PB-7 §3).

The three ``_append_template_patterns`` call sites inside
``AutoBuildContextLoader.get_player_context`` pass real file_path_hints
(derived from the task's planned target files, via
``preflight_ignore_gate.load_planned_targets``) ONLY under
``GUARDKIT_PATTERN_SELECTION_V2`` — wiring the previously-dead parameter is
itself behavioural (v1's hint-matching step has been dormant in production
since every call site passed none).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader


def _write_plan_json(worktree: Path, task_id: str, files_to_create=None, files_to_modify=None) -> None:
    state_dir = worktree / "docs" / "state" / task_id
    state_dir.mkdir(parents=True)
    (state_dir / "implementation_plan.json").write_text(
        json.dumps(
            {
                "plan": {
                    "files_to_create": files_to_create or [],
                    "files_to_modify": files_to_modify or [],
                }
            }
        )
    )


class TestResolveFilePathHints:
    def test_flag_off_returns_none_even_with_a_plan(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_PATTERN_SELECTION_V2", raising=False)
        _write_plan_json(tmp_path, "TASK-001", files_to_create=["src/api/router.py"])

        loader = AutoBuildContextLoader(graphiti=None, worktree_path=tmp_path)
        assert loader._resolve_file_path_hints("TASK-001") is None

    def test_flag_on_no_worktree_path_returns_none(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_PATTERN_SELECTION_V2", "1")
        loader = AutoBuildContextLoader(graphiti=None, worktree_path=None)
        assert loader._resolve_file_path_hints("TASK-001") is None

    def test_flag_on_resolves_real_plan_targets(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_PATTERN_SELECTION_V2", "1")
        _write_plan_json(
            tmp_path,
            "TASK-001",
            files_to_create=["src/api/router.py"],
            files_to_modify=["src/crud/crud.py"],
        )

        loader = AutoBuildContextLoader(graphiti=None, worktree_path=tmp_path)
        hints = loader._resolve_file_path_hints("TASK-001")
        assert hints == ["src/api/router.py", "src/crud/crud.py"]

    def test_flag_on_no_plan_returns_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_PATTERN_SELECTION_V2", "1")
        loader = AutoBuildContextLoader(graphiti=None, worktree_path=tmp_path)
        assert loader._resolve_file_path_hints("TASK-NOPLAN") is None

    def test_never_raises_when_loader_import_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import guardkit.knowledge.autobuild_context_loader as acl_module

        monkeypatch.setenv("GUARDKIT_PATTERN_SELECTION_V2", "1")

        def _boom(*args, **kwargs):
            raise RuntimeError("simulated failure")

        monkeypatch.setattr(
            "guardkit.orchestrator.preflight_ignore_gate.load_planned_targets", _boom
        )
        loader = acl_module.AutoBuildContextLoader(graphiti=None, worktree_path=tmp_path)
        assert loader._resolve_file_path_hints("TASK-001") is None


class TestEndToEndPlayerContextWiring:
    @pytest.mark.asyncio
    async def test_flag_off_prompt_identical_regardless_of_plan_presence(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_PATTERN_SELECTION_V2", raising=False)

        project_root = tmp_path / "project"
        project_root.mkdir()
        claude_dir = project_root / ".claude"
        claude_dir.mkdir()
        (claude_dir / "manifest.json").write_text(json.dumps({"name": "fastapi-python"}))
        _write_plan_json(project_root, "TASK-001", files_to_create=["src/api/router.py"])

        loader = AutoBuildContextLoader(graphiti=None, worktree_path=project_root)
        with_plan = await loader.get_player_context(
            task_id="TASK-001",
            feature_id="FEAT-001",
            turn_number=1,
            description="Test task",
            tech_stack="python",
        )

        no_plan_root = tmp_path / "project2"
        no_plan_root.mkdir()
        (no_plan_root / ".claude").mkdir()
        (no_plan_root / ".claude" / "manifest.json").write_text(
            json.dumps({"name": "fastapi-python"})
        )
        loader2 = AutoBuildContextLoader(graphiti=None, worktree_path=no_plan_root)
        without_plan = await loader2.get_player_context(
            task_id="TASK-002",
            feature_id="FEAT-001",
            turn_number=1,
            description="Test task",
            tech_stack="python",
        )

        assert with_plan.prompt_text == without_plan.prompt_text

    @pytest.mark.asyncio
    async def test_flag_on_uses_plan_hints_to_change_selection(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GUARDKIT_PATTERN_SELECTION_V2", "1")

        project_root = tmp_path / "project"
        project_root.mkdir()
        claude_dir = project_root / ".claude"
        claude_dir.mkdir()
        (claude_dir / "manifest.json").write_text(json.dumps({"name": "fastapi-python"}))
        # A plan pointing squarely at the crud/ layer.
        _write_plan_json(project_root, "TASK-001", files_to_create=["src/crud/orders.py"])

        loader = AutoBuildContextLoader(graphiti=None, worktree_path=project_root)
        result = await loader.get_player_context(
            task_id="TASK-001",
            feature_id="FEAT-001",
            turn_number=1,
            description="Test task",
            tech_stack="python",
        )

        # fastapi-python's real templates/crud/ exemplars should be selected
        # ahead of the tech-stack-fallback default (api/router.py.template).
        assert "crud" in result.prompt_text
