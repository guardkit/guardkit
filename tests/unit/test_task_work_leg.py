"""Tests for the headless work leg (``guardkit task-work``).

The delegation seam is faked — ``work_runner._build_orchestrator`` is replaced
by a recording double, exactly as the review-leg suite fakes ``run_specialist``.
A real Player-Coach run on a local seat is the coordinator's replay, not this
suite's job. **Everything else runs for real**: the CLI (through the registered
``cli`` group), the task loader, the requirements threading, the marker
renderer, the receipt writer, and — in the commit tests — real ``git`` against a
real repository on disk.

Covers, per the stage-2 design ``leg-invocation-stage2-design-2026-08-02.md``:

* §2 flag acceptance, including ``--fix-task`` (undeclared = every dispatch dies
  at parse time) and ``--nats``;
* the exit contract: 0 = approved, 2 = everything else, never 1;
* the receipt on EVERY path, under the DISTINCT ``task_work_leg_results.json``
  name, never clobbering ``AgentInvoker``'s ``task_work_results.json``;
* the empty-artefacts law: the section never carries a path, cross-checked
  against a copy of forge's own extractor;
* §2d requirements threading from ``## Description`` / ``## Acceptance
  Criteria``;
* §2b the ``existing_worktree`` switch and §2c the orchestrator configuration;
* §2e the outer-tree commit with the checkpoint junk-law excludes;
* the phases-not-run table, including the verbatim Phase-6 relocation line;
* §e.7 — the ``select_harness`` call in ``task_work_interface`` passes ``cwd``.
"""

from __future__ import annotations

import json
import re
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
from click.testing import CliRunner

from guardkit.cli.main import cli
from guardkit.orchestrator import work_runner
from guardkit.orchestrator.work_runner import (
    DEFAULT_LEG_BUDGET_SECONDS,
    DEFAULT_MAX_TURNS,
    DEFAULT_SDK_TIMEOUT_SECONDS,
    PHASE_6_RELOCATION,
    PHASES_NOT_RUN,
)

# ===========================================================================
# Copies of forge's scrape regexes — the cross-check
# ===========================================================================
# Verbatim from forge/src/forge/adapters/guardkit/parser.py:36-61 and
# forge/src/forge/cli/_serve_deps_stage_log.py:398.

FORGE_ARTEFACTS_SECTION_RE = re.compile(
    r"^##\s+Artefacts\s*$([\s\S]*?)(?=^##\s+|\Z)", re.MULTILINE
)
FORGE_ARTEFACT_LINE_RE = re.compile(r"^\s*-\s+(\S.*?)\s*$", re.MULTILINE)
FORGE_COACH_SCORE_RE = re.compile(
    r"^\s*coach_score\s*:\s*([+-]?\d+(?:\.\d+)?)\s*$", re.MULTILINE
)
FORGE_DETECTION_FINDINGS_SECTION_RE = re.compile(
    r"^##\s+Detection\s+Findings\s*$([\s\S]*?)(?=^##\s+|\Z)", re.MULTILINE
)
FORGE_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.MULTILINE)
FORGE_FIX_TASK_ID_RE = re.compile(r"^TASK-[A-Z0-9]{3,12}(?:-[A-Za-z0-9]+)*$")


def forge_extract_artefacts(stdout: str) -> List[str]:
    section = FORGE_ARTEFACTS_SECTION_RE.search(stdout)
    if section is None:
        return []
    return [m.group(1) for m in FORGE_ARTEFACT_LINE_RE.finditer(section.group(1))]


def forge_extract_fix_tasks(artefact_paths) -> tuple:
    """``default_fix_tasks_extractor`` — stem must match, duplicates dropped."""
    seen: List[str] = []
    for raw in artefact_paths:
        stem = Path(raw).stem
        if FORGE_FIX_TASK_ID_RE.match(stem) and stem not in seen:
            seen.append(stem)
    return tuple(seen)


def forge_extract_findings(stdout: str):
    section = FORGE_DETECTION_FINDINGS_SECTION_RE.search(stdout)
    if section is None:
        return None
    fence = FORGE_JSON_FENCE_RE.search(section.group(1))
    if fence is None:
        return None
    parsed = json.loads(fence.group(1).strip())
    return [i for i in parsed if isinstance(i, dict)] if isinstance(parsed, list) else None


# ===========================================================================
# Fixtures
# ===========================================================================

FIX_TASK_ID = "TASK-FWEX-002-cure-the-silent-swallow"

FIX_TASK_BODY = f"""---
id: {FIX_TASK_ID}
title: Cure the silent swallow in the parser
status: backlog
priority: medium
complexity: 3
parent_review: TASK-REV-abc123
---

# Cure the silent swallow in the parser

## Description

The parser swallows a malformed payload and returns an empty result, so a
broken upstream reads as a clean one. Raise instead, naming the payload.

## Acceptance Criteria

- [ ] AC-1: a malformed payload raises ParseError naming the offending field
- [ ] AC-2: a well-formed payload is byte-identical to today's output

## Files to Modify

- src/parser.py

## Notes

Auto-generated from TASK-REV-abc123 recommendations.
"""


class FakeTurn:
    def __init__(self, turn: int, feedback: Optional[str]) -> None:
        self.turn = turn
        self.feedback = feedback


class FakeResult:
    def __init__(
        self,
        *,
        success: bool,
        final_decision: str,
        total_turns: int = 1,
        turn_history: Optional[List[FakeTurn]] = None,
        error: Optional[str] = None,
    ) -> None:
        self.success = success
        self.final_decision = final_decision
        self.total_turns = total_turns
        self.turn_history = turn_history or []
        self.error = error


class RecordingOrchestrator:
    """Records the kwargs it was built with and what ``orchestrate`` got."""

    def __init__(
        self,
        result: Any,
        *,
        writes: Optional[Dict[str, str]] = None,
        delay: float = 0.0,
    ) -> None:
        self._result = result
        self._writes = writes or {}
        self._delay = delay
        self.orchestrate_kwargs: Dict[str, Any] = {}
        self.cwd: Optional[Path] = None

    def orchestrate(self, **kwargs: Any) -> Any:
        self.orchestrate_kwargs = kwargs
        if self._delay:
            time.sleep(self._delay)
        for rel, content in self._writes.items():
            target = self.cwd / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        if isinstance(self._result, Exception):
            raise self._result
        return self._result


@pytest.fixture
def fake_orchestrator(monkeypatch):
    """Install a recording double at ``work_runner``'s factory seam.

    Returns a callable ``install(result, writes=...)`` -> a holder whose
    ``.factory_kwargs`` and ``.orchestrator`` are populated once the leg runs.
    """

    class Holder:
        factory_kwargs: Dict[str, Any] = {}
        orchestrator: Optional[RecordingOrchestrator] = None

    holder = Holder()

    def install(
        result: Any,
        writes: Optional[Dict[str, str]] = None,
        delay: float = 0.0,
    ):
        def factory(**kwargs: Any) -> RecordingOrchestrator:
            holder.factory_kwargs = kwargs
            orch = RecordingOrchestrator(result, writes=writes, delay=delay)
            orch.cwd = kwargs["repo_root"]
            holder.orchestrator = orch
            return orch

        monkeypatch.setattr(work_runner, "_build_orchestrator", factory)
        return holder

    return install


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repo root carrying the fix task on disk, plus a git repo."""
    task_dir = tmp_path / "tasks" / "backlog" / "fix-journey"
    task_dir.mkdir(parents=True)
    (task_dir / f"{FIX_TASK_ID}.md").write_text(FIX_TASK_BODY, encoding="utf-8")
    # The fix task is COMMITTED in the fixture so "clean tree" means clean.
    # (In production the review leg leaves it untracked and the work leg's
    # commit sweeps it up alongside the fix — which is what the pipeline's
    # commit probe wants to see.)
    _git_init(tmp_path)
    return tmp_path


def _git(args: List[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True, check=True
    )


def _git_init(root: Path) -> None:
    _git(["init", "-b", "main"], root)
    _git(["config", "user.email", "leg@example.test"], root)
    _git(["config", "user.name", "Work Leg"], root)
    (root / "README.md").write_text("seed\n", encoding="utf-8")
    _git(["add", "-A", "."], root)
    _git(["commit", "-m", "seed"], root)


def _run_cli(repo: Path, args: List[str]):
    runner = CliRunner()
    import os

    previous = os.getcwd()
    os.chdir(repo)
    try:
        return runner.invoke(cli, args, catch_exceptions=False)
    finally:
        os.chdir(previous)


def _receipt(repo: Path, task_id: str = FIX_TASK_ID) -> Dict[str, Any]:
    path = repo / ".guardkit" / "autobuild" / task_id / "task_work_leg_results.json"
    assert path.is_file(), f"no receipt at {path}"
    return json.loads(path.read_text(encoding="utf-8"))


APPROVED = FakeResult(success=True, final_decision="approved", total_turns=1)


# ===========================================================================
# Registration + the union flag set
# ===========================================================================


class TestRegistrationAndFlags:
    def test_task_work_is_registered(self):
        assert "task-work" in cli.commands

    def test_help_lists_every_dispatch_flag(self):
        result = CliRunner().invoke(cli, ["task-work", "--help"])
        assert result.exit_code == 0
        for flag in (
            "--task-id",
            "--build-id",
            "--correlation-id",
            "--feature-yaml",
            "--context",
            "--fix-task",
            "--nats",
            "--mode",
            "--max-turns",
            "--model",
            "--sdk-timeout",
            "--leg-budget",
        ):
            assert flag in result.output, f"{flag} missing from the union flag set"

    def test_fix_task_is_accepted_not_a_parse_error(self, repo, fake_orchestrator):
        """``--fix-task`` rides EVERY real argv; undeclared = exit 2 at parse."""
        fake_orchestrator(APPROVED)
        payload = json.dumps({"fix_task_id": FIX_TASK_ID, "build_id": "b-1"})
        result = _run_cli(
            repo,
            ["task-work", "--task-id", FIX_TASK_ID, "--fix-task", payload],
        )
        assert result.exit_code == 0
        assert _receipt(repo)["fix_task"] == {
            "supplied": True,
            "raw": payload,
            "kind": "json",
            "keys": ["build_id", "fix_task_id"],
        }

    def test_nats_is_accepted_and_notices_on_stderr_only(self, repo, fake_orchestrator):
        fake_orchestrator(APPROVED)
        result = _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID, "--nats"])
        assert result.exit_code == 0
        assert "streaming NOT BUILT" in result.stderr
        # stdout is the pipeline's marker scrape — the notice must never land there.
        assert "streaming NOT BUILT" not in result.stdout

    def test_no_nats_flag_prints_no_notice(self, repo, fake_orchestrator):
        fake_orchestrator(APPROVED)
        result = _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert "streaming NOT BUILT" not in result.stderr

    def test_the_full_dispatch_argv_parses(self, repo, fake_orchestrator, tmp_path):
        fake_orchestrator(APPROVED)
        ctx_file = tmp_path / "review-findings.md"
        ctx_file.write_text("# findings\n", encoding="utf-8")
        result = _run_cli(
            repo,
            [
                "task-work",
                "--build-id",
                "build-1",
                "--correlation-id",
                "corr-1",
                "--task-id",
                FIX_TASK_ID,
                "--fix-task",
                '{"fix_task_id": "x"}',
                "--context",
                str(ctx_file),
                "--context",
                '{"failure_pack": {"a": 1}}',
                "--nats",
            ],
        )
        assert result.exit_code == 0
        receipt = _receipt(repo)
        assert receipt["build_id"] == "build-1"
        assert receipt["correlation_id"] == "corr-1"
        assert [entry["kind"] for entry in receipt["context"]] == [
            "file",
            "inline-json",
        ]

    def test_unknown_flag_is_click_exit_2(self, repo):
        result = CliRunner().invoke(
            cli, ["task-work", "--task-id", FIX_TASK_ID, "--nonsense"]
        )
        assert result.exit_code == 2


# ===========================================================================
# The exit contract — 0 and 2 only
# ===========================================================================


class TestExitContract:
    def test_approved_exits_zero(self, repo, fake_orchestrator):
        fake_orchestrator(APPROVED)
        result = _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert result.exit_code == 0

    def test_missing_fix_task_file_exits_two_not_one(self, repo, fake_orchestrator):
        """Phase-0 REFUSED. ``handle_cli_errors`` would map this to 1."""
        fake_orchestrator(APPROVED)
        result = _run_cli(repo, ["task-work", "--task-id", "TASK-NOPE-999-absent"])
        assert result.exit_code == 2
        assert "REFUSED" in result.stderr
        assert "TASK-NOPE-999-absent" in result.stderr
        # a refusal prints no markers at all is NOT the rule here: the leg
        # prints the residual channel on every path. What it must never do is
        # name an artefact.
        assert forge_extract_artefacts(result.stdout) == []

    def test_not_approved_exits_two_naming_final_decision(self, repo, fake_orchestrator):
        fake_orchestrator(
            FakeResult(
                success=False,
                final_decision="max_turns_exceeded",
                total_turns=2,
                turn_history=[FakeTurn(1, "fix the swallow"), FakeTurn(2, "still swallowing")],
            )
        )
        result = _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert result.exit_code == 2
        assert "max_turns_exceeded" in result.stderr

    def test_orchestration_raising_exits_two_never_tracebacks(
        self, repo, fake_orchestrator
    ):
        fake_orchestrator(RuntimeError("the substrate fell over"))
        result = _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert result.exit_code == 2
        assert "the substrate fell over" in result.stderr

    def test_frontier_model_is_refused_by_the_cli_fence(self, repo, fake_orchestrator, monkeypatch):
        fake_orchestrator(APPROVED)
        monkeypatch.delenv("GUARDKIT_ALLOW_FRONTIER", raising=False)
        result = _run_cli(
            repo,
            ["task-work", "--task-id", FIX_TASK_ID, "--model", "anthropic:claude-opus-4"],
        )
        assert result.exit_code == 2
        assert "GUARDKIT_ALLOW_FRONTIER" in result.stderr
        assert "anthropic:claude-opus-4" in result.stderr

    def test_model_default_is_none_never_a_frontier_alias(self):
        """``cli/autobuild.py:208`` defaults to a frontier alias; this must not."""
        param = {p.name: p for p in cli.commands["task-work"].params}["model"]
        assert param.default is None


# ===========================================================================
# The receipt — on every path, under the distinct name
# ===========================================================================


class TestReceipt:
    @pytest.mark.parametrize(
        "result_factory,expected_status",
        [
            (lambda: APPROVED, "approved"),
            (
                lambda: FakeResult(success=False, final_decision="error", error="boom"),
                "not-approved",
            ),
            (lambda: RuntimeError("substrate down"), "failed"),
        ],
    )
    def test_receipt_written_on_every_path(
        self, repo, fake_orchestrator, result_factory, expected_status
    ):
        fake_orchestrator(result_factory())
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert _receipt(repo)["status"] == expected_status

    def test_receipt_written_on_the_phase_0_refusal(self, repo, fake_orchestrator):
        fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", "TASK-GONE-001-absent"])
        receipt = _receipt(repo, "TASK-GONE-001-absent")
        assert receipt["status"] == "refused"
        assert receipt["exit_code"] == 2

    def test_receipt_name_is_the_leg_file_never_the_gate_file(
        self, repo, fake_orchestrator
    ):
        """``task_work_results.json`` is AgentInvoker's gate evidence.

        Clobbering it would destroy exactly the artefact this delegation
        exists to produce.
        """
        gate_file = (
            repo / ".guardkit" / "autobuild" / FIX_TASK_ID / "task_work_results.json"
        )
        gate_file.parent.mkdir(parents=True)
        gate_payload = {
            "status": "success",
            "plan_audit": {"severity": "none", "violations": []},
            "agent_invocations_validation": {"status": "valid"},
        }
        gate_file.write_text(json.dumps(gate_payload), encoding="utf-8")

        fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])

        # untouched, byte for byte
        assert json.loads(gate_file.read_text(encoding="utf-8")) == gate_payload
        # and the leg's own receipt exists beside it
        assert _receipt(repo)["leg"] == "task-work"

    def test_receipt_lifts_the_two_producer_gate_blocks(self, repo, fake_orchestrator):
        gate_file = (
            repo / ".guardkit" / "autobuild" / FIX_TASK_ID / "task_work_results.json"
        )
        gate_file.parent.mkdir(parents=True)
        gate_file.write_text(
            json.dumps(
                {
                    "plan_audit": {"severity": "warning", "violations": ["extra file"]},
                    "agent_invocations_validation": {"status": "violation"},
                }
            ),
            encoding="utf-8",
        )
        fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        receipt = _receipt(repo)
        assert receipt["plan_audit"] == {
            "severity": "warning",
            "violations": ["extra file"],
        }
        assert receipt["agent_invocations_validation"] == {"status": "violation"}

    def test_receipt_carries_the_phases_not_run_table(self, repo, fake_orchestrator):
        fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        phases = _receipt(repo)["phases_not_run"]
        assert len(phases) == len(PHASES_NOT_RUN)
        relocated = [p for p in phases if p["disposition"] == "RELOCATED"]
        assert len(relocated) == 1
        assert relocated[0]["relocated_to"] == PHASE_6_RELOCATION
        assert (
            relocated[0]["relocated_to"]
            == "Phase 6 completion → RELOCATED to the pipeline's merge gate "
            "(Rich's word)"
        )
        # The two producer honesty gates are KEPT, not declared absent — that
        # is the whole reason this leg delegates.
        kept = {p["checkpoint"] for p in phases if p["disposition"] == "KEPT AND ARMED"}
        assert any("5.5" in c for c in kept)
        assert any("6.5" in c for c in kept)

    def test_receipt_records_the_m0_verdict_honestly_when_no_harness_ran(
        self, repo, fake_orchestrator, monkeypatch
    ):
        from guardkit.orchestrator import m0_fence

        monkeypatch.setattr(m0_fence, "_last_verdict", None, raising=False)
        fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert _receipt(repo)["m0_fence"].startswith("NOT-EVALUATED")

    def test_receipt_reports_the_chokepoint_verdict_when_it_ran(
        self, repo, fake_orchestrator
    ):
        from guardkit.orchestrator import m0_fence

        verdict = m0_fence.M0Verdict(
            status="PASSED",
            harness="langgraph",
            effective_model="openai:workhorse",
            detail="routed to a non-vendor OPENAI_BASE_URL",
        )
        m0_fence.record_verdict(verdict)
        try:
            fake_orchestrator(APPROVED)
            _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
            assert _receipt(repo)["m0_fence"] == verdict.as_receipt_line()
        finally:
            m0_fence.reset_verdict()


# ===========================================================================
# The empty-artefacts law
# ===========================================================================


class TestEmptyArtefactsLaw:
    @pytest.mark.parametrize(
        "result_factory",
        [
            lambda: APPROVED,
            lambda: FakeResult(success=False, final_decision="max_turns_exceeded"),
            lambda: RuntimeError("substrate down"),
        ],
    )
    def test_artefacts_section_never_carries_a_path(
        self, repo, fake_orchestrator, result_factory
    ):
        """A work leg CONSUMES fix tasks; a printed path fans out a new one."""
        fake_orchestrator(result_factory())
        result = _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        stdout = result.stdout
        assert "## Artefacts" in stdout
        assert forge_extract_artefacts(stdout) == []
        assert forge_extract_fix_tasks(forge_extract_artefacts(stdout)) == ()

    def test_no_coach_score_marker(self, repo, fake_orchestrator):
        """The Coach contract is binary — a number here is a fabricated gate."""
        fake_orchestrator(APPROVED)
        result = _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert FORGE_COACH_SCORE_RE.search(result.stdout) is None

    def test_findings_are_empty_on_approval(self, repo, fake_orchestrator):
        fake_orchestrator(APPROVED)
        result = _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert forge_extract_findings(result.stdout) == []

    def test_findings_carry_the_residual_on_a_non_approved_exit(
        self, repo, fake_orchestrator
    ):
        fake_orchestrator(
            FakeResult(
                success=False,
                final_decision="max_turns_exceeded",
                total_turns=2,
                turn_history=[
                    FakeTurn(1, "first round feedback"),
                    FakeTurn(2, "AC-2 is still unproven"),
                ],
            )
        )
        result = _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        findings = forge_extract_findings(result.stdout)
        assert findings is not None and len(findings) == 1
        assert findings[0]["severity"] == "must_fix"
        assert findings[0]["detail"] == "AC-2 is still unproven"
        assert findings[0]["turn"] == 2
        assert _receipt(repo)["detection_findings"] == findings

    def test_residual_names_the_failure_when_there_is_no_feedback(self):
        findings = work_runner.residual_findings(
            approved=False,
            final_decision="error",
            turn_history=(),
            error="the substrate fell over",
        )
        assert len(findings) == 1
        assert "the substrate fell over" in findings[0]["detail"]

    def test_the_placeholder_is_not_scraped_as_an_artefact_line(self):
        """Belt: the placeholder must never start with ``-``."""
        from guardkit.orchestrator.review_runner import render_marker_block

        block = render_marker_block(
            fix_task_paths=(),
            findings=(),
            coach_score=None,
            empty_artefacts_note=work_runner.EMPTY_ARTEFACTS_NOTE,
        )
        assert forge_extract_artefacts(block) == []
        assert work_runner.EMPTY_ARTEFACTS_NOTE in block

    def test_review_leg_placeholder_is_byte_unchanged(self):
        """The additive parameter must not move the review leg's wording."""
        from guardkit.orchestrator.review_runner import render_marker_block

        block = render_marker_block(fix_task_paths=(), findings=())
        assert (
            "_(no fix tasks — the review is positively clean; see the report)_"
            in block
        )


# ===========================================================================
# §2d — requirements threading
# ===========================================================================


class TestRequirementsThreading:
    def test_description_and_acceptance_are_read_from_the_fix_task(self, repo):
        from guardkit.tasks.task_loader import TaskLoader

        task = TaskLoader.load_task(FIX_TASK_ID, repo_root=repo)
        requirements, acceptance, provenance = work_runner.thread_requirements(task)

        assert "swallows a malformed payload" in requirements
        assert provenance["requirements"] == "fix-task ## Description"
        assert acceptance == [
            "AC-1: a malformed payload raises ParseError naming the offending field",
            "AC-2: a well-formed payload is byte-identical to today's output",
        ]
        assert provenance["acceptance_criteria"] == "fix-task ## Acceptance Criteria"

    def test_the_player_is_not_briefed_with_a_heading(self, repo):
        """The bug this exists to stop: TaskLoader hands back the TITLE only."""
        from guardkit.tasks.task_loader import TaskLoader

        task = TaskLoader.load_task(FIX_TASK_ID, repo_root=repo)
        # TaskLoader's own fallback really does return the heading …
        assert task["requirements"].strip() == "# Cure the silent swallow in the parser"
        # … and the leg refuses to pass that on.
        requirements, _, _ = work_runner.thread_requirements(task)
        assert requirements != task["requirements"]

    def test_threading_reaches_orchestrate(self, repo, fake_orchestrator):
        holder = fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        kwargs = holder.orchestrator.orchestrate_kwargs
        assert "swallows a malformed payload" in kwargs["requirements"]
        assert len(kwargs["acceptance_criteria"]) == 2
        assert kwargs["task_id"] == FIX_TASK_ID
        assert kwargs["task_file_path"] is not None

    def test_missing_sections_fall_back_and_say_so(self, tmp_path):
        from guardkit.tasks.task_loader import TaskLoader

        task_id = "TASK-BARE-001-no-sections"
        task_dir = tmp_path / "tasks" / "backlog"
        task_dir.mkdir(parents=True)
        (task_dir / f"{task_id}.md").write_text(
            f"---\nid: {task_id}\ntitle: Bare\nstatus: backlog\n---\n\n"
            "# Bare\n\nJust prose, no sections.\n",
            encoding="utf-8",
        )
        task = TaskLoader.load_task(task_id, repo_root=tmp_path)
        _, _, provenance = work_runner.thread_requirements(task)
        assert "TaskLoader fallback" in provenance["requirements"]
        assert "TaskLoader fallback" in provenance["acceptance_criteria"]

    def test_extract_markdown_section_stops_at_the_next_heading(self):
        content = "## Description\n\nfirst\n\n## Acceptance Criteria\n\n- [ ] AC-1: x\n"
        assert work_runner.extract_markdown_section(content, "Description") == "first"
        assert work_runner.extract_markdown_section(content, "Nope") is None


# ===========================================================================
# §2b/§2c — the worktree switch and the orchestrator configuration
# ===========================================================================


class TestDelegationConfiguration:
    def test_existing_worktree_points_at_the_conductors_tree(
        self, repo, fake_orchestrator
    ):
        """Without this the orchestrator nests under .guardkit/worktrees/ —
        invisible to the gates reader, the commit probe and the exporter."""
        holder = fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        worktree = holder.factory_kwargs["worktree"]
        assert worktree.path == repo
        assert worktree.task_id == FIX_TASK_ID
        assert worktree.branch_name == "main"
        assert worktree.base_branch == "main"

    def test_no_nested_worktree_is_created(self, repo, fake_orchestrator):
        fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert not (repo / ".guardkit" / "worktrees").exists()

    def test_the_spec_2c_configuration_verbatim(self, repo, fake_orchestrator):
        holder = fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        kwargs = holder.factory_kwargs
        assert kwargs["repo_root"] == repo
        assert kwargs["max_turns"] == DEFAULT_MAX_TURNS == 2
        assert kwargs["sdk_timeout"] == DEFAULT_SDK_TIMEOUT_SECONDS == 420
        assert kwargs["leg_budget"] == DEFAULT_LEG_BUDGET_SECONDS == 1620
        assert kwargs["model"] is None
        assert isinstance(kwargs["timeout_event"], threading.Event)
        assert not kwargs["timeout_event"].is_set()

    def test_the_real_factory_passes_the_five_switches(self, repo, monkeypatch):
        """Drive ``_build_orchestrator`` itself, capturing the real ctor kwargs."""
        captured: Dict[str, Any] = {}

        class FakeOrchestrator:
            def __init__(self, **kwargs: Any) -> None:
                captured.update(kwargs)

        import guardkit.orchestrator.autobuild as autobuild_mod

        monkeypatch.setattr(autobuild_mod, "AutoBuildOrchestrator", FakeOrchestrator)
        work_runner._build_orchestrator(
            repo_root=repo,
            worktree=work_runner.build_outer_worktree(FIX_TASK_ID, repo, "main"),
            max_turns=2,
            sdk_timeout=420,
            leg_budget=1620,
            timeout_event=threading.Event(),
            model=None,
        )
        assert captured["enable_pre_loop"] is False
        assert captured["enable_checkpoints"] is False
        assert captured["rollback_on_pollution"] is False
        assert captured["skip_arch_review"] is True
        assert captured["task_timeout"] == 1620
        assert captured["sdk_timeout"] == 420
        assert captured["max_turns"] == 2
        assert captured["existing_worktree"].path == repo

    def test_leg_budget_is_under_the_pipelines_work_tripwire(self):
        """Inner-under-outer: on an outer timeout forge discards the markers."""
        assert DEFAULT_LEG_BUDGET_SECONDS < 1800

    def test_leg_budget_flag_threads_through(self, repo, fake_orchestrator):
        holder = fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID, "--leg-budget", "60"])
        assert holder.factory_kwargs["leg_budget"] == 60
        assert _receipt(repo)["leg_budget_seconds"] == 60

    def test_the_budget_timer_is_armed_and_fires(self, repo, fake_orchestrator):
        """A 0s budget must SET the event while the leg is still running."""
        fake_orchestrator(APPROVED, delay=0.4)
        result = _run_cli(
            repo, ["task-work", "--task-id", FIX_TASK_ID, "--leg-budget", "0"]
        )
        assert result.exit_code == 0
        assert _receipt(repo)["budget_expired"] is True

    def test_the_budget_timer_is_cancelled_on_a_prompt_leg(
        self, repo, fake_orchestrator
    ):
        """A leg well inside its budget records no expiry."""
        fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert _receipt(repo)["budget_expired"] is False


# ===========================================================================
# §2e — outer-tree commit evidence, junk excluded
# ===========================================================================


class TestOuterTreeCommit:
    def test_dirty_tree_after_approval_is_committed_on_the_outer_head(
        self, repo, fake_orchestrator
    ):
        fake_orchestrator(APPROVED, writes={"src/parser.py": "raise ParseError\n"})
        before = _git(["rev-parse", "HEAD"], repo).stdout.strip()
        result = _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert result.exit_code == 0
        after = _git(["rev-parse", "HEAD"], repo).stdout.strip()
        assert after != before

        commit = _receipt(repo)["commit"]
        assert commit["committed"] is True
        assert commit["message"].startswith(f"fix({FIX_TASK_ID}): ")
        assert "Cure the silent swallow in the parser" in commit["message"]

        # The mode-C commit probe's own question: does the commit carry work?
        listed = _git(["show", "--name-only", "--format=", "HEAD"], repo).stdout
        assert "src/parser.py" in listed

    def test_machine_local_junk_never_lands(self, repo, fake_orchestrator):
        fake_orchestrator(
            APPROVED,
            writes={
                "src/parser.py": "raise ParseError\n",
                ".cache/pip/wheel": "junk\n",
                "node_modules/left-pad/index.js": "junk\n",
                ".tmp/compile-cache": "junk\n",
                ".npm/_logs/debug.log": "junk\n",
                ".claude/task-plans/plan.md": "junk\n",
                ".guardkit-git.lock": "junk\n",
                ".guardkit/bootstrap_state.json": "{}\n",
                # The PYTHON junk classes (LI stage-2 GA2 coach: 223 junk files
                # on one real drive). Driven at three depths, because these are
                # minted wherever the interpreter happens to import from.
                "__pycache__/sitecustomize.cpython-312.pyc": "junk\n",
                "src/__pycache__/parser.cpython-312.pyc": "junk\n",
                "src/pkg/sub/__pycache__/deep.cpython-312.pyc": "junk\n",
                "src/stray.pyc": "junk\n",
                ".local/lib/python3.12/site-packages/thing/__init__.py": "junk\n",
                ".local/bin/tool": "junk\n",
            },
        )
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        listed = _git(["show", "--name-only", "--format=", "HEAD"], repo).stdout
        assert "src/parser.py" in listed
        for junk in (
            ".cache/",
            "node_modules/",
            ".tmp/",
            ".npm/",
            ".claude/task-plans/",
            ".guardkit-git.lock",
            "bootstrap_state.json",
            "__pycache__",
            ".pyc",
            ".local/",
        ):
            assert junk not in listed, f"junk committed: {junk}"

    def test_the_python_junk_classes_are_on_the_shared_list_not_local(self):
        """Stated ONCE, in the checkpoint law — never restated in work_runner."""
        from guardkit.orchestrator import worktree_checkpoints

        for pathspec in (
            ":(exclude,glob)**/__pycache__/**",
            ":(exclude,glob)**/*.pyc",
            ":(exclude,glob)**/.local/**",
        ):
            assert pathspec in worktree_checkpoints.CHECKPOINT_EXCLUDE_PATHSPECS

    def test_the_exclude_list_is_the_checkpoint_law_not_a_copy(self):
        """One statement of the junk law — reused, never restated."""
        import inspect

        from guardkit.orchestrator import worktree_checkpoints

        source = inspect.getsource(work_runner)
        for pathspec in worktree_checkpoints.CHECKPOINT_EXCLUDE_PATHSPECS:
            assert pathspec not in source, (
                f"work_runner restates the junk-law pathspec {pathspec!r}; it "
                "must reuse worktree_checkpoints._CHECKPOINT_ADD_ARGV"
            )
        assert work_runner._CHECKPOINT_ADD_ARGV is (
            worktree_checkpoints._CHECKPOINT_ADD_ARGV
        )

    def test_clean_tree_is_a_no_op(self, repo, fake_orchestrator):
        fake_orchestrator(APPROVED)
        before = _git(["rev-parse", "HEAD"], repo).stdout.strip()
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        after = _git(["rev-parse", "HEAD"], repo).stdout.strip()
        assert after == before
        commit = _receipt(repo)["commit"]
        assert commit["committed"] is False
        assert "nothing to commit" in commit["reason"]

    def test_no_commit_attempted_when_the_coach_did_not_approve(
        self, repo, fake_orchestrator
    ):
        fake_orchestrator(
            FakeResult(success=False, final_decision="max_turns_exceeded"),
            writes={"src/parser.py": "half a fix\n"},
        )
        before = _git(["rev-parse", "HEAD"], repo).stdout.strip()
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert _git(["rev-parse", "HEAD"], repo).stdout.strip() == before
        assert _receipt(repo)["commit"] == {"attempted": False}

    def test_a_commit_failure_never_kills_the_leg(self, repo):
        class ExplodingGit:
            def execute(self, command, cwd, check=True, timeout=None):
                raise RuntimeError("git is on fire")

        info = work_runner.commit_outer_tree(
            repo_root=repo,
            fix_task_id=FIX_TASK_ID,
            title="t",
            git_executor=ExplodingGit(),
        )
        assert info["committed"] is False
        assert "git is on fire" in info["error"]


# ===========================================================================
# §e.7 — the one-keyword fix, with its regression pin
# ===========================================================================


class TestDesignPhaseHarnessCwd:
    @pytest.mark.asyncio
    async def test_select_harness_receives_cwd(self, tmp_path, monkeypatch):
        """Without ``cwd=`` the langgraph branch raises AgentInvocationError,
        which the caller turns into DesignPhaseError — the design path was
        dead under the DEFAULT harness."""
        from guardkit.orchestrator import harness as harness_pkg
        from guardkit.orchestrator.quality_gates.task_work_interface import (
            TaskWorkInterface,
        )

        captured: Dict[str, Any] = {}

        def fake_select_harness(**kwargs: Any):
            captured.update(kwargs)
            raise RuntimeError("stop here — construction is not under test")

        monkeypatch.setattr(harness_pkg, "select_harness", fake_select_harness)

        interface = TaskWorkInterface(tmp_path)
        with pytest.raises(Exception):
            await interface._execute_via_sdk("TASK-X design prompt")

        assert "cwd" in captured, "select_harness called without cwd= (design §e.7)"
        assert captured["cwd"] == tmp_path

    def test_the_call_site_passes_the_interfaces_own_worktree(self):
        """The assertion is ANCHORED INSIDE the ``select_harness(`` call.

        The naive form — ``"cwd=self.worktree_path" in source`` — was VACUOUS:
        the method contains that exact substring TWICE (the ``select_harness``
        kwarg this test is about, and the ``.invoke()`` argument twelve lines
        below), so deleting the §e.7 fix left the test green. Mutation-proved by
        the GA2 coach. Read the CALL, not the file: the AST names which call
        carries the kwarg, and a comment mentioning ``cwd=`` cannot fool it.
        """
        import ast
        import inspect
        import textwrap

        from guardkit.orchestrator.quality_gates import task_work_interface

        source = inspect.getsource(
            task_work_interface.TaskWorkInterface._execute_via_sdk
        )
        # The pre-condition that made the old assertion vacuous, pinned so the
        # reason this test is written the hard way cannot quietly evaporate.
        assert source.count("cwd=self.worktree_path") == 2

        tree = ast.parse(textwrap.dedent(source))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "select_harness"
        ]
        assert len(calls) == 1, "expected exactly one select_harness call site"

        cwd = next((kw for kw in calls[0].keywords if kw.arg == "cwd"), None)
        assert cwd is not None, (
            "select_harness() is called without cwd= (design §e.7) — the "
            "langgraph branch REQUIRES it to build the LocalShellBackend"
        )
        assert ast.unparse(cwd.value) == "self.worktree_path"


# ===========================================================================
# Accepted-but-not-consumed flags are NAMED, never swallowed
# ===========================================================================


class TestAcceptedNotConsumed:
    def test_feature_yaml_and_mode_are_recorded_as_inert(
        self, repo, fake_orchestrator
    ):
        fake_orchestrator(APPROVED)
        _run_cli(
            repo,
            [
                "task-work",
                "--task-id",
                FIX_TASK_ID,
                "--feature-yaml",
                "/tmp/feature.yaml",
                "--mode",
                "c",
            ],
        )
        receipt = _receipt(repo)
        assert receipt["accepted_not_consumed"]["feature_yaml"] == "/tmp/feature.yaml"
        assert receipt["accepted_not_consumed"]["mode"] == "c"

    def test_context_payloads_are_named_inert_not_presented_as_used(
        self, repo, fake_orchestrator, tmp_path
    ):
        """The receipt presents ``context`` first-class; the leg consumes none.

        The REVIEW leg renders its payloads into the prompt; the work leg
        delegates and briefs the Player from the fix task itself. A receipt that
        showed the payloads and said nothing else invited the reader to assume
        they reached the Player — the same over-claim ``feature_yaml`` and
        ``mode`` are on this list to avoid.
        """
        note = tmp_path / "review-findings.md"
        note.write_text("the review said: fix the swallow\n", encoding="utf-8")

        fake_orchestrator(APPROVED)
        _run_cli(
            repo,
            ["task-work", "--task-id", FIX_TASK_ID, "--context", str(note)],
        )
        receipt = _receipt(repo)

        assert len(receipt["context"]) == 1
        inert = receipt["accepted_not_consumed"]["context"]
        assert "1 payload(s)" in inert
        assert "none fed to the Player" in inert

    def test_the_inert_context_note_counts_what_actually_arrived(
        self, repo, fake_orchestrator
    ):
        fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        assert "0 payload(s)" in _receipt(repo)["accepted_not_consumed"]["context"]

    def test_no_code_path_reads_the_payloads_back(self):
        """Mechanism, not a promise: the payloads are stored and echoed only.

        If a future change starts feeding ``context_payloads`` to the Player,
        this test fails and the receipt's honesty note must be revisited in the
        same change.
        """
        import inspect

        from guardkit.orchestrator import work_runner as module

        source = inspect.getsource(module)
        readers = [
            line.strip()
            for line in source.splitlines()
            if "outcome.context_payloads" in line and not line.strip().startswith("#")
        ]
        # The ONLY two readers are both inside build_receipt: the echo and the
        # count in the inert note. Anything else would mean the leg does consume
        # them, and the honesty note above would have become a lie.
        assert len(readers) == 2, readers
        # And both really are inside build_receipt — proven by walking the AST,
        # not by a substring that can never occur on an expression line.
        import ast

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "build_receipt":
                receipt_src = ast.get_source_segment(source, node)
                break
        else:
            raise AssertionError("build_receipt not found in work_runner")
        assert receipt_src.count("outcome.context_payloads") == 2

    def test_the_budgets_are_on_the_receipt(self, repo, fake_orchestrator):
        fake_orchestrator(APPROVED)
        _run_cli(repo, ["task-work", "--task-id", FIX_TASK_ID])
        receipt = _receipt(repo)
        assert receipt["max_turns"] == DEFAULT_MAX_TURNS
        assert receipt["sdk_timeout_seconds"] == DEFAULT_SDK_TIMEOUT_SECONDS
        assert receipt["leg_budget_seconds"] == DEFAULT_LEG_BUDGET_SECONDS
