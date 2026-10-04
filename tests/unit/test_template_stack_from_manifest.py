"""The template picker takes the project's stack from its manifest (2026-10-04).

Every build used to pass a hard-coded ``tech_stack="python"`` into the memory
and template code. It reached the template picker's stack fallback, which for
a project of another language picked Python-shaped folders. Now the stack is
the manifest's own ``language`` and ``frameworks`` names, and with no
manifest no language is used at all.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader
from guardkit.knowledge.template_pattern_loader import (
    TemplatePatternContext,
    load_template_patterns,
)


def _project(tmp_path: Path, manifest: dict | None) -> Path:
    root = tmp_path / "project"
    (root / ".claude").mkdir(parents=True)
    if manifest is not None:
        (root / ".claude" / "manifest.json").write_text(json.dumps(manifest))
    return root


def test_loader_reads_language_and_framework_names(tmp_path):
    root = _project(
        tmp_path,
        {
            "name": "fastapi-python",
            "language": "Python",
            "frameworks": [{"name": "FastAPI"}, {"name": "SQLAlchemy"}, "pytest", {"x": 1}],
        },
    )
    ctx = load_template_patterns(root / ".claude" / "manifest.json")
    assert ctx.tech_stack == "Python FastAPI SQLAlchemy pytest"


def test_manifest_without_a_language_gives_no_stack(tmp_path):
    root = _project(tmp_path, {"name": "fastapi-python"})
    assert load_template_patterns(root / ".claude" / "manifest.json").tech_stack == ""


def _captured_select(loader_root: Path, manifest_stack: str | None):
    """Run the real player path; capture what reaches select_patterns."""
    seen = {}

    def fake_select(ctx, tech_stack, file_path_hints, **_):
        seen["tech_stack"] = tech_stack
        return ctx

    template_ctx = TemplatePatternContext(
        template_name="demo", template_dir=None, available_files=[],
        tech_stack=manifest_stack or "",
    )
    with patch(
        "guardkit.knowledge.template_pattern_loader.load_template_patterns",
        return_value=template_ctx,
    ), patch(
        "guardkit.knowledge.template_pattern_loader.select_patterns",
        side_effect=fake_select,
    ) as select:
        import asyncio

        asyncio.run(
            AutoBuildContextLoader(graphiti=None, worktree_path=loader_root).get_player_context(
                task_id="TASK-AB12-001", feature_id="FEAT-AB12", turn_number=1,
                description="Add an endpoint",
            )
        )
    return seen, select


def test_the_manifest_stack_reaches_the_template_picker(tmp_path):
    root = _project(tmp_path, {"name": "demo", "language": "C#"})
    seen, _ = _captured_select(root, "C# ASP.NET Core FastEndpoints")
    assert seen["tech_stack"] == "C# ASP.NET Core FastEndpoints"


def test_no_language_in_the_manifest_means_no_language_and_never_python(tmp_path):
    root = _project(tmp_path, {"name": "demo"})
    seen, _ = _captured_select(root, None)
    assert seen["tech_stack"] == ""


def test_without_a_manifest_the_template_picker_is_not_reached(tmp_path):
    root = _project(tmp_path, None)
    _, select = _captured_select(root, None)
    select.assert_not_called()


def test_neither_autobuild_call_site_passes_a_stack(tmp_path):
    """The orchestrator no longer tells the memory code the project is Python."""
    from guardkit.knowledge.autobuild_context_loader import AutoBuildContextResult
    from guardkit.knowledge.job_context_retriever import RetrievedContext
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

    empty = AutoBuildContextResult(
        context=RetrievedContext("TASK-AB12-001", 0, 0, [], [], [], [], [], []),
        prompt_text="", budget_used=0, budget_total=0, categories_populated=[],
    )
    loader = MagicMock()
    loader.get_player_context = AsyncMock(return_value=empty)
    loader.get_coach_context = AsyncMock(return_value=empty)
    invoker = MagicMock()
    invoker.invoke_player = AsyncMock(return_value=MagicMock(success=True, error=None, report={}))
    invoker.invoke_coach = AsyncMock(
        return_value=MagicMock(success=True, error=None, report={"decision": "approve"})
    )
    orchestrator = AutoBuildOrchestrator(
        repo_root=tmp_path, max_turns=2, enable_context=True, context_loader=loader,
        worktree_manager=MagicMock(), agent_invoker=invoker,
        progress_display=MagicMock(), enable_checkpoints=False,
    )
    worktree = MagicMock()
    worktree.path = tmp_path
    orchestrator._invoke_player_safely("TASK-AB12-001", 1, "Add an endpoint", None)
    orchestrator._invoke_coach_safely(
        task_id="TASK-AB12-001", turn=1, requirements="Add an endpoint",
        player_report={}, worktree=worktree,
    )
    for call in (loader.get_player_context.await_args, loader.get_coach_context.await_args):
        assert "tech_stack" not in call.kwargs
        assert "python" not in json.dumps({k: str(v) for k, v in call.kwargs.items()}).lower()
