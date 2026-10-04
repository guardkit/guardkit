"""The Coach is given the project's binding documents (project initialisation, 4 October 2026).

Design: ai-transition ``docs/source-material/project-initialisation-2026-10-04/design.md``,
Part 3 "Coach (new, GuardKit)" and the round-1/round-2 dispositions R2 and R7.

What is checked here, each against the real code with fakes only at the model
and validator seams:

* the selector's loader reads the instructions and declared documents in full,
  with hashes, and refuses a missing document, a symbolic link (for the Player
  too), and a total over the 48 KiB budget, naming files and sizes;
* the Coach prompt carries a ``## Project documents`` section beside the
  requirements, and a project with nothing to give gets today's prompt;
* an oversized player report and evidence bundle, forcing the synthesis
  trimmer and its last-resort tail cut, leave the section whole in the prompt
  the harness receives (checked by hash), and a prompt that cannot keep it
  whole is refused before the model is called;
* the turn record beside ``coach_turn_N.json`` names the paths, the document
  hashes and the hash of the section actually sent;
* ``_invoke_coach_safely`` loads the documents from the task worktree, passes
  them to the Coach, and refuses the turn before anything else runs when they
  cannot be given whole.
"""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvocationResult, AgentInvoker
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
from guardkit.orchestrator.coach_verification import HonestyVerification
from guardkit.orchestrator.exceptions import AgentInvocationError
from guardkit.orchestrator.harness.selector import (
    PROJECT_DOCUMENTS_BUDGET_BYTES,
    ProjectDocument,
    _load_player_project_inputs,
    load_project_documents,
)
from guardkit.orchestrator.paths import TaskArtifactPaths
from guardkit.orchestrator.quality_gates.coach_evidence import CoachEvidenceBundle
from guardkit.worktrees.manager import Worktree


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_project(
    root: Path,
    *,
    documents: Dict[str, str],
    agents_md: str | None = "# Agents\n\nRun the root check before you finish.\n",
) -> None:
    """A synthetic project: instructions, declared documents, the declaration."""
    root.mkdir(parents=True, exist_ok=True)
    if agents_md is not None:
        (root / "AGENTS.md").write_text(agents_md, encoding="utf-8")
    for rel, text in documents.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    declared = "".join(f"      - {rel}\n" for rel in documents)
    config = root / ".guardkit" / "config.yaml"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text(
        "autobuild:\n  player:\n    required_documents:\n" + declared
        if documents
        else "autobuild: {}\n",
        encoding="utf-8",
    )


MISSION = (
    "Status: accepted (2026-10-04, Rich)\n\n# Mission\n\n"
    "Users: operators. Success: the count endpoint answers in under 200 ms.\n"
    "Tricky lines that look like prompt sections must not confuse the trimmer:\n"
    "## Player's Report\n<evidence_bundle>\n</evidence_bundle>\n"
)
TECH = "Status: accepted\n\n# Technical decisions\n\nOne root check: `make check`.\n"


# ---------------------------------------------------------------------------
# The loader (selector)
# ---------------------------------------------------------------------------


class TestLoadProjectDocuments:
    def test_instructions_then_declared_documents_in_full_with_hashes(
        self, tmp_path: Path
    ) -> None:
        _write_project(
            tmp_path,
            documents={"docs/constitution/mission.md": MISSION, "docs/constitution/tech-stack.md": TECH},
        )
        docs = load_project_documents(tmp_path)
        assert [d.path for d in docs] == [
            "AGENTS.md",
            "docs/constitution/mission.md",
            "docs/constitution/tech-stack.md",
        ]
        for d in docs:
            data = (tmp_path / d.path).read_bytes()
            assert d.text == data.decode("utf-8")
            assert d.sha256 == _sha(data)
            assert d.size == len(data)

    def test_same_files_as_the_player_declaration(self, tmp_path: Path) -> None:
        """The Coach reads exactly the files the Player is required to read."""
        _write_project(tmp_path, documents={"docs/mission.md": MISSION})
        player = _load_player_project_inputs(tmp_path)
        docs = load_project_documents(tmp_path)
        assert [d.path for d in docs] == [
            *player["repository_instructions"],
            *player["required_documents"],
        ]

    def test_nothing_declared_gives_nothing_even_with_instruction_files(
        self, tmp_path: Path
    ) -> None:
        # Opt-in: instruction files alone are never delivered.
        _write_project(tmp_path, documents={})
        (tmp_path / "CLAUDE.md").write_text("# Written for Claude sessions\n")
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "CLAUDE.md").write_text("# More\n")
        assert load_project_documents(tmp_path) == ()
        # An explicitly empty list is the same as none.
        (tmp_path / ".guardkit" / "config.yaml").write_text(
            "autobuild:\n  player:\n    required_documents: []\n"
        )
        assert load_project_documents(tmp_path) == ()
        # No configuration at all, too.
        assert load_project_documents(tmp_path / "absent") == ()

    def test_missing_declared_document_refused(self, tmp_path: Path) -> None:
        _write_project(tmp_path, documents={"docs/mission.md": MISSION})
        (tmp_path / "docs" / "mission.md").unlink()
        with pytest.raises(AgentInvocationError, match="docs/mission.md"):
            load_project_documents(tmp_path)

    def test_symbolic_link_refused_for_coach_and_player(self, tmp_path: Path) -> None:
        _write_project(tmp_path, documents={"docs/real.md": MISSION})
        (tmp_path / "docs" / "linked.md").symlink_to(tmp_path / "docs" / "real.md")
        (tmp_path / ".guardkit" / "config.yaml").write_text(
            "autobuild:\n  player:\n    required_documents:\n      - docs/linked.md\n",
            encoding="utf-8",
        )
        with pytest.raises(AgentInvocationError, match="symbolic link"):
            load_project_documents(tmp_path)
        # The Player's own loader refuses it too, before guardkitfactory follows it.
        with pytest.raises(AgentInvocationError, match="symbolic link"):
            _load_player_project_inputs(tmp_path)

    def test_document_under_a_linked_folder_refused(self, tmp_path: Path) -> None:
        _write_project(tmp_path, documents={"real/mission.md": MISSION})
        (tmp_path / "docs").symlink_to(tmp_path / "real", target_is_directory=True)
        (tmp_path / ".guardkit" / "config.yaml").write_text(
            "autobuild:\n  player:\n    required_documents:\n      - docs/mission.md\n",
            encoding="utf-8",
        )
        with pytest.raises(AgentInvocationError, match="docs is a symbolic link"):
            load_project_documents(tmp_path)

    def test_over_budget_refused_naming_files_and_sizes(self, tmp_path: Path) -> None:
        big = "x" * (PROJECT_DOCUMENTS_BUDGET_BYTES - 100)
        _write_project(tmp_path, documents={"docs/big.md": big, "docs/tech.md": TECH})
        with pytest.raises(AgentInvocationError) as excinfo:
            load_project_documents(tmp_path)
        message = str(excinfo.value)
        assert str(PROJECT_DOCUMENTS_BUDGET_BYTES) in message
        assert f"docs/big.md ({len(big)} bytes)" in message
        assert "docs/tech.md" in message and "AGENTS.md" in message


# ---------------------------------------------------------------------------
# The prompt
# ---------------------------------------------------------------------------


def _docs(root: Path) -> tuple[ProjectDocument, ...]:
    _write_project(root, documents={"docs/mission.md": MISSION, "docs/tech.md": TECH})
    return load_project_documents(root)


def _bundle(**extra: Any) -> CoachEvidenceBundle:
    return CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="complete",
        **extra,
    )


def _invoker(worktree: Path) -> AgentInvoker:
    invoker = AgentInvoker.__new__(AgentInvoker)
    invoker.worktree_path = worktree
    invoker.sdk_timeout_seconds = 600
    invoker._calculate_sdk_timeout = MagicMock(return_value=600)  # type: ignore[method-assign]
    invoker._verify_player_claims = MagicMock(  # type: ignore[method-assign]
        return_value=SimpleNamespace(verified=True, honesty_score=1.0, discrepancies=[])
    )
    return invoker


_CRITERIA = [{"id": "AC-001", "text": "Count endpoint answers"}]


class TestCoachPrompt:
    def test_section_beside_requirements_with_paths_hashes_and_text(
        self, tmp_path: Path
    ) -> None:
        docs = _docs(tmp_path)
        prompt = _invoker(tmp_path)._build_coach_prompt(
            "TASK-PD-001", 1, "Add the count endpoint.", {"files_modified": []},
            acceptance_criteria=_CRITERIA, evidence_bundle=_bundle(),
            synthesis=True, project_documents=docs,
        )
        criteria = prompt.index("## Acceptance Criteria to Verify")
        section = prompt.index("## Project documents")
        report = prompt.index("## Player's Report")
        assert criteria < section < report
        for d in docs:
            assert f'<project_document path="{d.path}" sha256="{d.sha256}">' in prompt
            assert d.text in prompt

    @pytest.mark.parametrize("synthesis", [True, False])
    def test_nothing_to_give_is_todays_prompt(self, tmp_path: Path, synthesis: bool) -> None:
        invoker = _invoker(tmp_path)
        args = ("TASK-PD-002", 1, "reqs", {"files_modified": []})
        kwargs = dict(
            acceptance_criteria=_CRITERIA,
            evidence_bundle=_bundle() if synthesis else None,
            synthesis=synthesis,
        )
        today = invoker._build_coach_prompt(*args, **kwargs)
        assert invoker._build_coach_prompt(*args, **kwargs, project_documents=()) == today
        assert invoker._build_coach_prompt(*args, **kwargs, project_documents=None) == today
        assert "## Project documents" not in today

    def test_trimmer_without_a_section_is_unchanged(self) -> None:
        prompt = "## Original Requirements\n\n" + "z" * 50
        assert AgentInvoker._trim_synthesis_prompt(prompt) == prompt
        assert AgentInvoker._trim_synthesis_prompt(prompt, protected_section="") == prompt


def _oversized_player_report() -> Dict[str, Any]:
    return {
        "task_id": "TASK-PD-003",
        "turn": 1,
        "completion_promises": [
            {"criterion_id": f"AC-{i:03d}", "evidence": "e" * 400} for i in range(200)
        ],
    }


class TestTrimmerKeepsTheSectionWhole:
    """R2: oversized report and evidence force the trimmer AND its tail cut."""

    def _run(self, tmp_path: Path, docs, coach_context: str):
        invoker = _invoker(tmp_path)
        iwr = AsyncMock(side_effect=RuntimeError("stop-after-capture"))
        bundle = _bundle(
            independent_tests={"tests_passed": True, "raw_output": "R" * 40_000},
            behavioural_oracle={"status": "ran", "passed": True, "output_tail": "T" * 30_000},
        )
        with patch.object(invoker, "_invoke_with_role", iwr):
            result = asyncio.run(
                invoker.invoke_coach(
                    task_id="TASK-PD-003",
                    turn=2,
                    requirements="Add the count endpoint.",
                    player_report=_oversized_player_report(),
                    evidence_bundle=bundle,
                    coach_context=coach_context,
                    acceptance_criteria=_CRITERIA,
                    project_documents=docs,
                )
            )
        return invoker, iwr, result

    def test_section_intact_in_the_prompt_the_harness_receives(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        # Documents near the budget (but under it), plus an untrimmable memory
        # context after them, so the last-resort tail cut must fire.
        docs = list(_docs(tmp_path))
        filler = "Binding rule line.\n" * ((40 * 1024) // 19)
        (tmp_path / "docs" / "rules.md").write_text(filler, encoding="utf-8")
        (tmp_path / ".guardkit" / "config.yaml").write_text(
            "autobuild:\n  player:\n    required_documents:\n"
            "      - docs/mission.md\n      - docs/tech.md\n      - docs/rules.md\n",
            encoding="utf-8",
        )
        docs = load_project_documents(tmp_path)
        assert sum(d.size for d in docs) <= PROJECT_DOCUMENTS_BUDGET_BYTES

        invoker, iwr, _ = self._run(tmp_path, docs, coach_context="M" * 400_000)

        iwr.assert_awaited_once()
        sent = iwr.call_args.kwargs["prompt"]
        assert len(sent) <= AgentInvoker._COACH_SYNTHESIS_MAX_CHARS
        assert "player_report truncated" in sent  # step 1 fired
        assert "evidence_bundle truncated" in sent  # the bundle was cut too
        assert "prompt truncated at" in sent  # the tail cut fired
        section = invoker._render_project_documents_section(docs)
        start = sent.index("## Project documents") - 1
        assert _sha(sent[start:start + len(section)].encode()) == _sha(section.encode())

        record = json.loads(
            TaskArtifactPaths.private_artifact_path(
                "TASK-PD-003", "coach_project_documents_turn_2.json", tmp_path
            ).read_text()
        )
        assert record["section_sha256"] == _sha(section.encode())
        assert record["refused"] is None
        assert [(r["path"], r["sha256"], r["bytes"]) for r in record["documents"]] == [
            (d.path, d.sha256, d.size) for d in docs
        ]

    def test_refused_before_the_model_when_it_cannot_stay_whole(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        docs = _docs(tmp_path)
        invoker = _invoker(tmp_path)
        iwr = AsyncMock(side_effect=RuntimeError("must not be called"))
        # Requirements alone (never trimmed) overflow the prompt limit, so the
        # documents cannot be kept: the turn is refused, not sent cut short.
        with patch.object(invoker, "_invoke_with_role", iwr):
            result = asyncio.run(
                invoker.invoke_coach(
                    task_id="TASK-PD-004",
                    turn=1,
                    requirements="Q" * (AgentInvoker._COACH_SYNTHESIS_MAX_CHARS + 10),
                    player_report={"files_modified": []},
                    evidence_bundle=_bundle(),
                    project_documents=docs,
                )
            )
        iwr.assert_not_awaited()
        assert result.success is False
        assert "could not be kept whole" in result.error
        record = json.loads(
            TaskArtifactPaths.private_artifact_path(
                "TASK-PD-004", "coach_project_documents_turn_1.json", tmp_path
            ).read_text()
        )
        assert record["section_sha256"] is None
        assert "could not be kept whole" in record["refused"]

    def test_over_budget_refused_before_any_model_call(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.setenv("GUARDKIT_COACH_GATHER", "1")  # Phase A would call a model
        big = ProjectDocument(
            path="docs/big.md", sha256="0" * 64, text="x", size=PROJECT_DOCUMENTS_BUDGET_BYTES + 1
        )
        invoker = _invoker(tmp_path)
        iwr = AsyncMock(side_effect=RuntimeError("must not be called"))
        with patch.object(invoker, "_invoke_with_role", iwr):
            result = asyncio.run(
                invoker.invoke_coach(
                    task_id="TASK-PD-005", turn=1, requirements="r",
                    player_report={}, evidence_bundle=_bundle(),
                    project_documents=(big,),
                )
            )
        iwr.assert_not_awaited()
        assert result.success is False
        assert "docs/big.md" in result.error and str(PROJECT_DOCUMENTS_BUDGET_BYTES) in result.error


# ---------------------------------------------------------------------------
# The orchestrator seam (_invoke_coach_safely)
# ---------------------------------------------------------------------------


def _worktree(path: Path) -> Worktree:
    worktree = MagicMock(spec=Worktree)
    worktree.task_id = "TASK-PD-010"
    worktree.path = path
    worktree.branch_name = "autobuild/TASK-PD-010"
    worktree.base_branch = "main"
    return worktree


def _orchestrator(tmp_path: Path, invoke_coach: Any) -> AutoBuildOrchestrator:
    manager = MagicMock()
    manager.worktrees_dir = tmp_path / "worktrees"
    invoker = MagicMock()
    invoker.invoke_coach = invoke_coach
    return AutoBuildOrchestrator(
        repo_root=tmp_path / "repo",
        max_turns=3,
        worktree_manager=manager,
        agent_invoker=invoker,
        progress_display=MagicMock(),
        enable_context=False,
    )


def _real_signature_mock() -> AsyncMock:
    sig = inspect.signature(AgentInvoker.invoke_coach)
    mock = AsyncMock(
        return_value=AgentInvocationResult(
            task_id="TASK-PD-010", turn=1, agent_type="coach", success=True,
            report={"decision": "approve", "rationale": "ok"}, duration_seconds=0.0,
        )
    )
    mock.__signature__ = sig.replace(
        parameters=[p for p in sig.parameters.values() if p.name != "self"]
    )
    return mock


def _call(orch: AutoBuildOrchestrator, worktree: Worktree) -> AgentInvocationResult:
    with patch("guardkit.orchestrator.autobuild.CoachValidator") as validator_class:
        validator = MagicMock()
        validator.gather_evidence.return_value = _bundle()
        validator_class.return_value = validator
        orch._produce_spec_conformance_leg = MagicMock(return_value=None)  # type: ignore[method-assign]
        orch._evidence_repo_gate = MagicMock(return_value=None)  # type: ignore[method-assign]
        orch._direct_mode_evidence_gate = MagicMock(return_value=None)  # type: ignore[method-assign]
        result = orch._invoke_coach_safely(
            task_id="TASK-PD-010", turn=1, requirements="reqs",
            player_report={"files_modified": []}, worktree=worktree,
        )
        result.gather_calls = validator.gather_evidence.call_count  # type: ignore[attr-defined]
        return result


class TestInvokeCoachSafely:
    def test_documents_loaded_from_the_worktree_and_passed(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
        root = tmp_path / "wt"
        _write_project(root, documents={"docs/mission.md": MISSION})
        invoke = _real_signature_mock()
        result = _call(_orchestrator(tmp_path, invoke), _worktree(root))
        assert result.success is True
        passed = invoke.call_args.kwargs["project_documents"]
        assert [d.path for d in passed] == ["AGENTS.md", "docs/mission.md"]
        assert passed[1].sha256 == _sha((root / "docs" / "mission.md").read_bytes())

    @pytest.mark.parametrize("declaration", ["autobuild: {}\n", None,
                                             "autobuild:\n  player:\n    required_documents: []\n"])
    def test_no_declaration_is_todays_turn(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, declaration: Optional[str]
    ) -> None:
        """Opt-in: instruction files present, nothing declared → today's call."""
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
        root = tmp_path / "wt"
        _write_project(root, documents={})  # writes AGENTS.md
        (root / "CLAUDE.md").write_text("# Written for Claude sessions\n")
        config = root / ".guardkit" / "config.yaml"
        if declaration is None:
            config.unlink()
        else:
            config.write_text(declaration)
        invoke = _real_signature_mock()
        _call(_orchestrator(tmp_path, invoke), _worktree(root))
        # Exactly the keyword set the base commit passed.
        assert set(invoke.call_args.kwargs) == {
            "task_id", "turn", "requirements", "player_report", "remaining_budget",
            "evidence_bundle", "behavioural_oracle_declaration",
        }
        assert not list(root.rglob("coach_project_documents_turn_*.json"))

    def test_no_declaration_prompt_is_byte_identical(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The real invoker under the orchestrator, AGENTS.md present, nothing
        declared: the prompt the harness receives equals the one built by a
        direct call that never mentions project documents (today's call)."""
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_SYNTHESIS", raising=False)
        monkeypatch.delenv("GUARDKIT_COACH_GATHER", raising=False)
        root = tmp_path / "wt"
        _write_project(root, documents={})
        invoker = _invoker(root)
        captured: list[str] = []

        async def capture(**kwargs: Any) -> None:
            captured.append(kwargs["prompt"])
            raise RuntimeError("stop-after-capture")

        orch = _orchestrator(tmp_path, invoker.invoke_coach)
        with patch.object(invoker, "_invoke_with_role", side_effect=capture):
            _call(orch, _worktree(root))
            asyncio.run(
                invoker.invoke_coach(
                    task_id="TASK-PD-010", turn=1, requirements="reqs",
                    player_report={"files_modified": []}, evidence_bundle=_bundle(),
                )
            )
        assert len(captured) == 2
        assert captured[0] == captured[1]
        assert "## Project documents" not in captured[0]
        assert "Run the root check" not in captured[0]  # AGENTS.md not delivered
        assert not list(root.rglob("coach_project_documents_turn_*.json"))

    def test_unloadable_documents_refuse_before_anything_runs(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
        root = tmp_path / "wt"
        _write_project(root, documents={"docs/mission.md": MISSION})
        (root / "docs" / "mission.md").unlink()
        invoke = _real_signature_mock()
        result = _call(_orchestrator(tmp_path, invoke), _worktree(root))
        assert result.success is False
        assert "docs/mission.md" in result.error
        assert result.gather_calls == 0  # type: ignore[attr-defined]
        invoke.assert_not_awaited()

    def test_invoker_that_cannot_take_documents_is_refused_not_dropped(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.delenv("GUARDKIT_COACH_LEGACY", raising=False)
        root = tmp_path / "wt"
        _write_project(root, documents={"docs/mission.md": MISSION})

        async def old_invoke_coach(task_id, turn, requirements, player_report, remaining_budget=None):
            raise AssertionError("must not be called")

        result = _call(_orchestrator(tmp_path, old_invoke_coach), _worktree(root))
        assert result.success is False
        assert "never dropped" in result.error
