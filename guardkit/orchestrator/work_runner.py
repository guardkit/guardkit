"""Headless work leg — the engine behind ``guardkit task-work``.

The pipeline's conductor spawns ``guardkit task-work …`` as a subprocess once a
review leg has produced fix tasks. This module is the body of that subcommand.

**Delegation, never a second distillation** (stage-2 design §2). The review leg
composes its own model call over ``run_specialist``; the work leg does the
opposite and hands the whole job to the *existing* ``AutoBuildOrchestrator``.
The decisive fact is where the three producer-side honesty gates live: the
plan-audit override, the agent-invocation validator and the assumption-
confidence check are all folded into ``AgentInvoker._write_task_work_results``
(``agent_invoker.py`` ~11495/11507/11517). A leg that delegates into the
orchestrator inherits all three for free; a leg composed like the review leg
inherits none. So this module is a *thin adapter*, and every line of it that
looks like configuration is load-bearing:

* ``existing_worktree=`` pointing at ``Path.cwd()`` — **the switch the whole
  design turns on**. Without it the orchestrator mints a nested worktree under
  ``.guardkit/worktrees/``, which is invisible to all three pipeline readers
  (the gates reader, the mode-C commit probe and the receipts exporter). The
  leg's work would then exist and be unfindable.
* ``enable_checkpoints=False`` — the cwd is the CONDUCTOR's tree. Checkpointing
  would rewrite the pipeline's own git state turn by turn.
* ``rollback_on_pollution=False`` — same reason: a rollback here resets somebody
  else's HEAD.
* ``enable_pre_loop=False`` — the pre-loop gates shell out to the attended
  ``/task-work`` design phase; the leg's dispositions (below) declare them
  absent rather than pretending they ran.
* ``skip_arch_review=True`` — a fix task is a *fix*, not an architecture.

Exit semantics belong to the CLI (:mod:`guardkit.cli.task_work`); this module
returns a typed outcome and never calls :func:`sys.exit`. It never raises.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from guardkit.orchestrator.m0_fence import (
    last_verdict as last_m0_verdict,
    receipt_line_when_chokepoint_did_not_run,
)
from guardkit.orchestrator.review_runner import (
    ContextPayload,
    anchored_findings,
    load_context_payloads,
)
from guardkit.orchestrator.worktree_checkpoints import (
    # The junk law, stated ONCE. ``_CHECKPOINT_ADD_ARGV`` is the full
    # ``git add -A -- .`` prefix plus every ``:(exclude,glob)**/…`` pathspec in
    # the 706589f7 fully-wildcarded form. Reused, never restated: a second copy
    # of this list is exactly the drift 706589f7 had to fix in two places.
    _CHECKPOINT_ADD_ARGV,
    SubprocessGitExecutor,
)
from guardkit.tasks.task_loader import TaskLoader, TaskNotFoundError, TaskParseError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Contract constants
# ---------------------------------------------------------------------------

#: The leg's own loop-level clock, in seconds. **Inner-under-outer** (the same
#: discipline as the review leg's 480 < 600): the pipeline's per-stage tripwire
#: for the work stage is 1800 s, so the leg budgets 1620 and fails *honestly*
#: with a written receipt instead of being SIGKILLed mid-turn. On an outer
#: timeout ``forge``'s parser discards even a perfect marker block
#: (``adapters/guardkit/parser.py:110-126``) and the fix dies silently.
DEFAULT_LEG_BUDGET_SECONDS = 1620

#: Per-invocation model budget. Several invocations fit inside one leg budget.
DEFAULT_SDK_TIMEOUT_SECONDS = 420

#: Player↔Coach turns. Two, not five: a work leg is one fix task, and the
#: journey's own cap (``max_review_cycles``) is what bounds the *journey*.
DEFAULT_MAX_TURNS = 2

#: ``final_decision`` value that means the Coach approved.
APPROVED_DECISION = "approved"


# ---------------------------------------------------------------------------
# §c.2 dispositions — every checkpoint of the attended /task-work, named
# ---------------------------------------------------------------------------

#: The verbatim relocation sentence for Phase 6. It is quoted exactly (design
#: §2, "including, verbatim") because the merge word is Rich's and a paraphrase
#: of whose word it is would be the beginning of losing it.
PHASE_6_RELOCATION = (
    "Phase 6 completion → RELOCATED to the pipeline's merge gate (Rich's word)"
)

PHASES_NOT_RUN: Tuple[Dict[str, str], ...] = (
    {
        "checkpoint": "Phase 1.4 — state-transition [Y/n]",
        "spec_pin": "task-work-phases-plan-ext.md:155-158",
        "disposition": "AUTO-ANSWERED",
        "answer_used": "yes (the prompt's own 5s default)",
        "detail": (
            "Safe as-is on the attended path; the delegated inline protocol "
            "never reaches the prompt at all."
        ),
    },
    {
        "checkpoint": "Phase 1.6 — clarifying questions",
        "spec_pin": "task-work-phases-plan-ext.md:642-763",
        "disposition": "DECLARED-ABSENT",
        "detail": (
            "Pre-loop is disabled for this leg. Named honestly because "
            "complexity 5+ is a HARD blocking wait with no timeout "
            "(plan-ext:761-763) — the one checkpoint that would hang a "
            "dispatch forever if it were left live."
        ),
    },
    {
        "checkpoint": "Phase 2 / 2.5 / 2.7 — planning, pattern suggestions, "
        "complexity evaluation",
        "spec_pin": "AutoBuildOrchestrator pre-loop quality gates",
        "disposition": "DECLARED-ABSENT",
        "detail": "enable_pre_loop=False. The leg implements a fix task, it does not re-plan it.",
    },
    {
        "checkpoint": "Phase 2.6 — human checkpoint [A]/[R]/[V]/[C]/[D]",
        "spec_pin": "task-work-phases-plan-ext.md:1339-1376",
        "disposition": "DECLARED-ABSENT",
        "detail": "Not run on the inline-protocol path.",
    },
    {
        "checkpoint": "Phase 2.8 — plan checkpoint [A]/[M]/[V]/[C]",
        "spec_pin": "task-work-phases-plan-ext.md:1464-1743",
        "disposition": "AUTO-ANSWERED",
        "answer_used": "approve (--auto-approve-checkpoint semantics)",
        "detail": (
            "FULL_REQUIRED at complexity 7-10 is otherwise blocking. Moot here "
            "while pre-loop is disabled; recorded so a future leg that enables "
            "pre-loop inherits the declared answer rather than a surprise."
        ),
    },
    {
        "checkpoint": "Phase 2.5B — architectural review (SOLID/DRY/YAGNI)",
        "spec_pin": "AutoBuildOrchestrator(skip_arch_review=…)",
        "disposition": "DECLARED-ABSENT",
        "detail": "skip_arch_review=True — a fix task is a fix, not an architecture.",
    },
    {
        "checkpoint": "Phase 5.5 — plan audit [A]/[R]/[E]/[C]",
        "spec_pin": "installer/core/commands/lib/phase_execution.py:45 "
        "(execute_phase_5_5_plan_audit, non_interactive=True)",
        "disposition": "KEPT AND ARMED",
        "detail": (
            "An honesty gate, inherited for free by delegating: the "
            "deterministic auditor OVERRIDES the Player's self-reported "
            "plan_audit block before the Coach reads it. Its verdict is lifted "
            "into this receipt."
        ),
    },
    {
        "checkpoint": "Step 6.5 — agent-invocation validator",
        # HEADING-TEXT anchor, never a line number: PB-12 bans
        # ``task-work.md:NNN`` in guardkit/ code because those anchors rot
        # silently (tests/unit/test_command_anchor_hygiene.py enforces it).
        "spec_pin": 'task-work.md § "Step 6.5: Validate Agent Invocations"; '
        "installer/core/commands/lib/agent_invocation_validator.py",
        "disposition": "KEPT AND ARMED",
        "detail": (
            "Deterministic anti-false-reporting check, also inherited by "
            "delegating. Its verdict is lifted into this receipt."
        ),
    },
    {
        "checkpoint": "Phase 6 — completion",
        "spec_pin": 'task-work.md § "Phase 6: Finalize (Completion — DF-018)"',
        "disposition": "RELOCATED",
        "relocated_to": PHASE_6_RELOCATION,
        "detail": (
            "The leg never calls completion, and the machinery already refuses: "
            "complete_task(refuse_autobuild=True) raises (cli/task.py:306-312) "
            "and auto-merge is env-gated OFF. The leg reports; the merge word "
            "stays Rich's."
        ),
    },
)

#: The artefacts note the work leg prints. The work leg **consumes** fix tasks;
#: it must never mint one. Any printed path whose stem matches the fix-task
#: regex is harvested by ``default_fix_tasks_extractor`` and fans out ANOTHER
#: work dispatch (``forge/src/forge/cli/_serve_deps_stage_log.py:431-440``), so
#: the section carries this placeholder unconditionally — on every exit path,
#: approved or not.
EMPTY_ARTEFACTS_NOTE = (
    "_(no artefacts — a work leg consumes fix tasks and never mints them; "
    "see the leg receipt)_"
)


# ---------------------------------------------------------------------------
# Typed result
# ---------------------------------------------------------------------------


@dataclass
class WorkLegOutcome:
    """Everything the CLI needs to print markers, write a receipt and exit."""

    task_id: str
    status: str  # "approved" | "not-approved" | "refused" | "failed"
    exit_code: int
    duration_seconds: float
    model: Optional[str]
    seat: Optional[str]
    final_decision: Optional[str] = None
    turns: int = 0
    findings: List[Dict[str, Any]] = field(default_factory=list)
    requirements_source: Dict[str, str] = field(default_factory=dict)
    worktree_path: Optional[str] = None
    branch: Optional[str] = None
    commit: Dict[str, Any] = field(default_factory=dict)
    plan_audit: Optional[Dict[str, Any]] = None
    agent_invocations_validation: Optional[Dict[str, Any]] = None
    task_work_results_path: Optional[str] = None
    context_payloads: List[ContextPayload] = field(default_factory=list)
    fix_task: Dict[str, Any] = field(default_factory=dict)
    # Accepted-and-recorded, not consumed. Named in the receipt rather than
    # swallowed: a flag the leg takes and quietly ignores is the kind of
    # silence this whole design exists to remove.
    feature_yaml: Optional[str] = None
    mode: Optional[str] = None
    max_turns: int = DEFAULT_MAX_TURNS
    sdk_timeout_seconds: int = DEFAULT_SDK_TIMEOUT_SECONDS
    leg_budget_seconds: int = DEFAULT_LEG_BUDGET_SECONDS
    budget_expired: bool = False
    error: Optional[str] = None

    @property
    def approved(self) -> bool:
        return self.exit_code == 0


# ---------------------------------------------------------------------------
# §2d — requirements threading
# ---------------------------------------------------------------------------


def extract_markdown_section(content: str, heading: str) -> Optional[str]:
    """Return the body of ``## <heading>`` from ``content``, or ``None``.

    Case- and whitespace-tolerant on the heading line; stops at the next
    ``##``-level heading. Returns ``None`` when the section is absent and when
    it is present but empty — an empty section is no better a brief than a
    missing one.
    """
    if not content:
        return None
    wanted = f"## {heading}".strip().lower()
    collected: List[str] = []
    inside = False
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.lower() == wanted:
            inside = True
            continue
        if inside:
            if stripped.startswith("## "):
                break
            collected.append(line)
    body = "\n".join(collected).strip()
    return body or None


def _acceptance_lines(section: str) -> List[str]:
    """Top-level bullet/checkbox items of an acceptance-criteria section."""
    items: List[str] = []
    for line in section.splitlines():
        if not line.startswith(("- [ ] ", "- [x] ", "- [X] ", "- ", "* ")):
            continue
        text = line.lstrip("*- ").strip()
        if text.startswith("[ ]") or text.lower().startswith("[x]"):
            text = text[3:].strip()
        if text:
            items.append(text)
    return items


def thread_requirements(task: Dict[str, Any]) -> Tuple[str, List[str], Dict[str, str]]:
    """Build ``(requirements, acceptance_criteria, provenance)`` for the Player.

    Producer-minted fix tasks carry ``## Description`` and
    ``## Acceptance Criteria`` and **no** ``## Requirements`` section
    (``installer/core/lib/implement_orchestrator.py`` ~303-311). ``TaskLoader``
    looks for ``## Requirements`` and otherwise falls back to the first
    paragraph of the body — which on a fix task is the ``# Title`` heading
    (``task_loader.py:242-271``). Briefing a Player with a heading is how a work
    leg does nothing and reports success, so the leg reads the fix task's own
    sections and passes those.

    Provenance for each half is recorded, so the receipt says which brief the
    Player actually got.
    """
    content = str(task.get("content") or "")
    provenance: Dict[str, str] = {}

    description = extract_markdown_section(content, "Description")
    if description:
        requirements = description
        provenance["requirements"] = "fix-task ## Description"
    else:
        requirements = str(task.get("requirements") or "").strip()
        provenance["requirements"] = "TaskLoader fallback (no ## Description section)"

    acceptance_section = extract_markdown_section(content, "Acceptance Criteria")
    acceptance = _acceptance_lines(acceptance_section) if acceptance_section else []
    if acceptance:
        provenance["acceptance_criteria"] = "fix-task ## Acceptance Criteria"
    else:
        loaded = task.get("acceptance_criteria") or []
        acceptance = [str(item) for item in loaded if str(item).strip()]
        provenance["acceptance_criteria"] = (
            "TaskLoader fallback (no ## Acceptance Criteria items)"
        )

    return requirements, acceptance, provenance


# ---------------------------------------------------------------------------
# §2b — the load-bearing worktree switch
# ---------------------------------------------------------------------------


def detect_head_branch(repo_root: Path, default: str = "main") -> str:
    """The cwd's current branch, via the CLI's existing detector.

    Imported lazily and by name rather than restated: ``_detect_base_branch``
    already encodes the detached-HEAD and git-failure fallbacks
    (``cli/autobuild.py:131``).
    """
    try:
        from guardkit.cli.autobuild import _detect_base_branch  # noqa: PLC0415

        return _detect_base_branch(default=default, cwd=repo_root)
    except Exception as exc:  # noqa: BLE001 — a branch read must never kill a leg
        logger.warning("branch detection failed for %s: %s", repo_root, exc)
        return default


def build_outer_worktree(task_id: str, repo_root: Path, branch: str):
    """Describe the CONDUCTOR's tree as a :class:`Worktree`, touching no git.

    ``Worktree`` is a frozen dataclass of four fields
    (``worktrees/manager.py:123-137``) — constructing one creates nothing. It is
    injected as ``existing_worktree=``, which ``_setup_phase`` consumes
    (``autobuild.py`` ~2426-2445) *instead of* creating a nested worktree.
    """
    from guardkit.worktrees.manager import Worktree  # noqa: PLC0415

    return Worktree(
        task_id=task_id,
        branch_name=branch,
        path=repo_root,
        base_branch=branch,
    )


# ---------------------------------------------------------------------------
# §2e — commit evidence on the OUTER tree
# ---------------------------------------------------------------------------


def commit_outer_tree(
    *,
    repo_root: Path,
    fix_task_id: str,
    title: str,
    git_executor: Optional[Any] = None,
) -> Dict[str, Any]:
    """Commit the leg's work on the outer HEAD, junk excluded. Never raises.

    **Why this exists at all.** The fix journey's only commit evidence is
    ``git rev-list main..HEAD`` on the OUTER tree
    (``forge/src/forge/pipeline/mode_c_commit_probe.py:145-220``). No commits →
    the journey ends ``CLEAN_REVIEW`` with no card *even when the fix
    happened*. Since ``enable_checkpoints=False`` (the cwd is the conductor's
    tree), nothing else commits.

    The staging argv is ``worktree_checkpoints._CHECKPOINT_ADD_ARGV`` — the
    checkpoint junk law, reused whole. If the orchestrator (or the Player)
    already committed, the index comes up empty and this is a no-op.
    """
    executor = git_executor or SubprocessGitExecutor()
    info: Dict[str, Any] = {"attempted": True, "committed": False}

    def _run(args: List[str], check: bool = True):
        return executor.execute(args, cwd=repo_root, check=check)

    try:
        before = _run(["git", "rev-parse", "HEAD"], check=False)
        info["head_before"] = (getattr(before, "stdout", "") or "").strip() or None

        _run(list(_CHECKPOINT_ADD_ARGV))

        staged = _run(["git", "diff", "--cached", "--quiet"], check=False)
        if getattr(staged, "returncode", 0) == 0:
            info["reason"] = (
                "nothing to commit after junk-excluded staging — either the "
                "orchestrator already committed or the leg changed nothing"
            )
            return info

        message = f"fix({fix_task_id}): {title}".strip()
        _run(["git", "commit", "-m", message])
        after = _run(["git", "rev-parse", "HEAD"], check=False)
        info["committed"] = True
        info["message"] = message
        info["head_after"] = (getattr(after, "stdout", "") or "").strip() or None
    except Exception as exc:  # noqa: BLE001 — commit failure must not kill the leg
        info["error"] = f"{type(exc).__name__}: {exc}"
        logger.warning("outer-tree commit failed in %s: %s", repo_root, exc)
    return info


# ---------------------------------------------------------------------------
# The residual channel + the gate blocks
# ---------------------------------------------------------------------------


def residual_findings(
    *,
    approved: bool,
    final_decision: Optional[str],
    turn_history: Sequence[Any],
    error: Optional[str],
) -> List[Dict[str, Any]]:
    """``## Detection Findings`` for a work leg — the residual channel.

    Empty on approval, by rule: an approved leg has no unresolved must-fix
    item, and inventing one would be a fabricated gate in the other direction.
    On a non-approved exit the channel carries what is still unfixed — the last
    Coach feedback if there is one, otherwise the failure itself.

    ``forge`` drops this block for the work stage today; it is printed for the
    receipt's human reader, and it is the block GA3's ``anchor`` field attaches
    to — via :func:`review_runner.anchored_findings`, the ONE place the anchor
    rule is stated. A residual names no file, so its anchor's file half is the
    honest ``(no file)`` sentinel rather than an invented path.
    """
    if approved:
        return []

    findings: List[Dict[str, Any]] = []
    last_feedback: Optional[str] = None
    last_turn: Optional[int] = None
    for record in turn_history or ():
        feedback = getattr(record, "feedback", None)
        if feedback:
            last_feedback = str(feedback)
            last_turn = getattr(record, "turn", None)

    if last_feedback:
        findings.append(
            {
                "severity": "must_fix",
                "title": "unresolved Coach feedback at leg exit",
                "detail": last_feedback[:4000],
                "turn": last_turn,
                "final_decision": final_decision,
                "source": "task-work leg residual",
            }
        )
    else:
        findings.append(
            {
                "severity": "must_fix",
                "title": (
                    f"the work leg did not reach approval "
                    f"({final_decision or 'no decision recorded'})"
                ),
                "detail": (error or "no Coach feedback was recorded")[:4000],
                "turn": last_turn,
                "final_decision": final_decision,
                "source": "task-work leg residual",
            }
        )
    return anchored_findings(findings)


def task_work_results_path(repo_root: Path, task_id: str) -> Path:
    """``AgentInvoker``'s own gate evidence — read, never written, by this leg."""
    return repo_root / ".guardkit" / "autobuild" / task_id / "task_work_results.json"


def lift_gate_blocks(
    repo_root: Path, task_id: str
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str]]:
    """Lift ``plan_audit`` + ``agent_invocations_validation`` out of the gates file.

    Returns ``(plan_audit, agent_invocations_validation, path_or_None)``. Both
    blocks are *copied*, never recomputed: they are the producer-side honesty
    gates the delegation exists to inherit, and a second derivation here would
    be a second statement of the same rule.
    """
    path = task_work_results_path(repo_root, task_id)
    if not path.is_file():
        return None, None, None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        logger.warning("could not read %s: %s", path, exc)
        return None, None, str(path)
    if not isinstance(payload, dict):
        return None, None, str(path)
    plan_audit = payload.get("plan_audit")
    validation = payload.get("agent_invocations_validation")
    return (
        plan_audit if isinstance(plan_audit, dict) else None,
        validation if isinstance(validation, dict) else None,
        str(path),
    )


# ---------------------------------------------------------------------------
# Receipt (M5)
# ---------------------------------------------------------------------------


def receipt_path_for(repo_root: Path, task_id: str) -> Path:
    """``.guardkit/autobuild/{task_id}/task_work_leg_results.json``.

    A **distinct** name, deliberately. ``task_work_results.json`` is
    ``AgentInvoker``'s file — written on success (``agent_invoker.py`` ~11536)
    and on every failure path (~11541). Overwriting it would destroy the gate
    evidence this delegation exists to produce. Same family directory, so the
    receipt rides the pipeline's existing stage export with zero new export
    code (``forge/src/forge/pipeline/fix_journey_receipts.py:390-464`` walks the
    OUTER tree's four families — which is exactly where this lands).
    """
    return (
        repo_root / ".guardkit" / "autobuild" / task_id / "task_work_leg_results.json"
    )


def _m0_fence_receipt_line(outcome: "WorkLegOutcome") -> str:
    """The receipt's ``m0_fence`` value — the CHOKEPOINT's verdict when it ran.

    Identical rule to the review leg's (design §3.3): the fence at
    ``select_harness`` is the chokepoint every real model call passes through,
    so when it ran its verdict IS the answer and the receipt REPORTS it. It is
    never re-derived here, and a silence is never read as a pass. The
    no-chokepoint wording is :func:`m0_fence.receipt_line_when_chokepoint_did_not_run`
    — one sentence, one home, shared with the review leg.
    """
    verdict = last_m0_verdict()
    if verdict is not None:
        return verdict.as_receipt_line()
    return receipt_line_when_chokepoint_did_not_run(outcome.model)


def build_receipt(
    outcome: WorkLegOutcome,
    *,
    build_id: Optional[str],
    correlation_id: Optional[str],
) -> Dict[str, Any]:
    """Assemble the per-leg receipt payload."""
    return {
        "leg": "task-work",
        "task_id": outcome.task_id,
        "fix_task": outcome.fix_task,
        "build_id": build_id,
        "correlation_id": correlation_id,
        "status": outcome.status,
        "exit_code": outcome.exit_code,
        "model": outcome.model,
        "m0_fence": _m0_fence_receipt_line(outcome),
        "seat": outcome.seat,
        "duration_seconds": round(outcome.duration_seconds, 3),
        "leg_budget_seconds": outcome.leg_budget_seconds,
        "sdk_timeout_seconds": outcome.sdk_timeout_seconds,
        "max_turns": outcome.max_turns,
        # Accepted for caller compatibility; consumed by nothing in this leg.
        # Recorded so the receipt's reader can see they were supplied and had
        # no effect, rather than assuming they did.
        "accepted_not_consumed": {
            "feature_yaml": outcome.feature_yaml,
            "mode": outcome.mode,
            # ``--context`` belongs on THIS list too, and saying so is the whole
            # point of the list. The payloads are read (and echoed under
            # "context" below, so the reader can see what arrived), but nothing
            # in the work leg feeds them to the Player: the REVIEW leg renders
            # them into its prompt (review_runner.py:361-410), whereas the work
            # leg delegates to the orchestrator, which briefs the Player from
            # the fix task's own Description + Acceptance Criteria (§2d). A
            # receipt that presents "context" first-class while the leg ignores
            # it is exactly the over-claim this section exists to prevent.
            "context": (
                f"{len(outcome.context_payloads)} payload(s) loaded and echoed "
                "under 'context', none fed to the Player"
            ),
        },
        "budget_expired": outcome.budget_expired,
        "turns": outcome.turns,
        "final_decision": outcome.final_decision,
        "worktree_path": outcome.worktree_path,
        "branch": outcome.branch,
        "requirements_source": outcome.requirements_source,
        "commit": outcome.commit,
        "plan_audit": outcome.plan_audit,
        "agent_invocations_validation": outcome.agent_invocations_validation,
        "task_work_results_path": outcome.task_work_results_path,
        "detection_findings": list(outcome.findings),
        "phases_not_run": [dict(phase) for phase in PHASES_NOT_RUN],
        "context": [p.as_receipt_entry() for p in outcome.context_payloads],
        "error": outcome.error,
    }


def write_receipt(
    outcome: WorkLegOutcome,
    *,
    repo_root: Path,
    build_id: Optional[str],
    correlation_id: Optional[str],
) -> Optional[Path]:
    """Write the receipt; never raises (a receipt failure must not fail a leg)."""
    path = receipt_path_for(repo_root, outcome.task_id)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                build_receipt(
                    outcome, build_id=build_id, correlation_id=correlation_id
                ),
                indent=2,
                default=str,
            ),
            encoding="utf-8",
        )
        return path
    except OSError as exc:  # pragma: no cover — defensive
        logger.warning("could not write work-leg receipt %s: %s", path, exc)
        return None


# ---------------------------------------------------------------------------
# The leg
# ---------------------------------------------------------------------------


def _load_fix_task_payload(fix_task: Optional[str]) -> Dict[str, Any]:
    """Record what ``--fix-task`` carried, without ever failing on it.

    The forward-context builder's first entry is
    ``ContextEntry(flag='--fix-task', kind='text')``
    (``forge/.../forward_context_builder.py:617-669`` →
    ``subprocess.py:378-379``), so the flag is on every real dispatch. Its
    payload is recorded for the receipt; it is never a source of truth about
    the task, because the task file on disk is.
    """
    if not fix_task:
        return {"supplied": False}
    entry: Dict[str, Any] = {"supplied": True, "raw": str(fix_task)[:2000]}
    try:
        parsed = json.loads(fix_task)
    except (ValueError, TypeError):
        entry["kind"] = "text"
        return entry
    entry["kind"] = "json"
    if isinstance(parsed, dict):
        entry["keys"] = sorted(str(k) for k in parsed)
    return entry


def _build_orchestrator(
    *,
    repo_root: Path,
    worktree,
    max_turns: int,
    sdk_timeout: int,
    leg_budget: int,
    timeout_event: threading.Event,
    model: Optional[str],
):
    """Construct the orchestrator with the §2c configuration, verbatim.

    Imported lazily so ``guardkit --help`` does not pay for the orchestrator's
    import graph.
    """
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator  # noqa: PLC0415

    return AutoBuildOrchestrator(
        repo_root=repo_root,
        existing_worktree=worktree,
        enable_pre_loop=False,
        enable_checkpoints=False,
        rollback_on_pollution=False,
        max_turns=max_turns,
        sdk_timeout=sdk_timeout,
        task_timeout=leg_budget,
        timeout_event=timeout_event,
        skip_arch_review=True,
        model=model,
    )


def run_work_leg(
    *,
    task_id: str,
    repo_root: Path,
    context: Sequence[str] = (),
    fix_task: Optional[str] = None,
    feature_yaml: Optional[str] = None,
    mode: Optional[str] = None,
    max_turns: int = DEFAULT_MAX_TURNS,
    model: Optional[str] = None,
    sdk_timeout: int = DEFAULT_SDK_TIMEOUT_SECONDS,
    leg_budget: int = DEFAULT_LEG_BUDGET_SECONDS,
    orchestrator_factory: Optional[Any] = None,
    git_executor: Optional[Any] = None,
) -> WorkLegOutcome:
    """Run the headless work leg end to end. Never raises; never exits.

    ``orchestrator_factory`` and ``git_executor`` are seams for tests only —
    production passes neither.
    """
    started = time.monotonic()
    seat = os.environ.get("OPENAI_BASE_URL")
    payloads = load_context_payloads(context, repo_root=repo_root)
    fix_task_info = _load_fix_task_payload(fix_task)

    def _outcome(status: str, exit_code: int, **kwargs: Any) -> WorkLegOutcome:
        kwargs.setdefault("context_payloads", payloads)
        kwargs.setdefault("fix_task", fix_task_info)
        return WorkLegOutcome(
            task_id=task_id,
            status=status,
            exit_code=exit_code,
            duration_seconds=time.monotonic() - started,
            model=model,
            seat=seat,
            feature_yaml=feature_yaml,
            mode=mode,
            max_turns=max_turns,
            sdk_timeout_seconds=sdk_timeout,
            leg_budget_seconds=leg_budget,
            **kwargs,
        )

    # --- §2a. Phase-0 REFUSED: id-form only, no ad-hoc creation. ------------
    try:
        task = TaskLoader.load_task(task_id, repo_root=repo_root)
    except (TaskNotFoundError, TaskParseError) as exc:
        return _outcome(
            "refused",
            2,
            error=(
                f"REFUSED (Phase 0, ad-hoc task creation): the work leg is "
                f"id-form only and no fix-task file exists for {task_id}. {exc}"
            ),
        )

    title = str(task.get("frontmatter", {}).get("title") or task_id)
    requirements, acceptance, provenance = thread_requirements(task)

    # --- §2b. The load-bearing switch. --------------------------------------
    branch = detect_head_branch(repo_root)
    try:
        worktree = build_outer_worktree(task_id, repo_root, branch)
    except Exception as exc:  # noqa: BLE001
        return _outcome(
            "failed",
            2,
            branch=branch,
            error=(
                "could not describe the conductor's tree as a worktree "
                f"({type(exc).__name__}: {exc}) — refusing to run, because "
                "without existing_worktree the orchestrator would nest a "
                "worktree the pipeline's readers cannot see"
            ),
            requirements_source=provenance,
        )

    # --- §2c. Delegate. -----------------------------------------------------
    timeout_event = threading.Event()
    timer = threading.Timer(leg_budget, timeout_event.set)
    timer.daemon = True
    timer.start()

    factory = orchestrator_factory or _build_orchestrator
    result: Any = None
    orchestration_error: Optional[str] = None
    try:
        orchestrator = factory(
            repo_root=repo_root,
            worktree=worktree,
            max_turns=max_turns,
            sdk_timeout=sdk_timeout,
            leg_budget=leg_budget,
            timeout_event=timeout_event,
            model=model,
        )
        result = orchestrator.orchestrate(
            task_id=task_id,
            requirements=requirements,
            acceptance_criteria=acceptance,
            base_branch=branch,
            task_file_path=task.get("file_path"),
        )
    except Exception as exc:  # noqa: BLE001 — the leg must never traceback out
        orchestration_error = f"{type(exc).__name__}: {exc}"
        logger.warning("work leg orchestration raised: %s", orchestration_error)
    finally:
        timer.cancel()

    budget_expired = timeout_event.is_set()
    plan_audit, validation, results_path = lift_gate_blocks(repo_root, task_id)

    if result is None:
        findings = residual_findings(
            approved=False,
            final_decision=None,
            turn_history=(),
            error=orchestration_error,
        )
        return _outcome(
            "failed",
            2,
            branch=branch,
            worktree_path=str(repo_root),
            error=(
                f"the work leg's orchestration failed: {orchestration_error}"
                if orchestration_error
                else "the work leg's orchestration returned no result"
            ),
            findings=findings,
            requirements_source=provenance,
            plan_audit=plan_audit,
            agent_invocations_validation=validation,
            task_work_results_path=results_path,
            budget_expired=budget_expired,
        )

    final_decision = getattr(result, "final_decision", None)
    success = bool(getattr(result, "success", False))
    turn_history = list(getattr(result, "turn_history", ()) or ())
    turns = int(getattr(result, "total_turns", len(turn_history)) or 0)
    result_error = getattr(result, "error", None)

    # --- §2e. Commit evidence, only once the Coach approved. ----------------
    commit_info: Dict[str, Any] = {"attempted": False}
    if success:
        commit_info = commit_outer_tree(
            repo_root=repo_root,
            fix_task_id=task_id,
            title=title,
            git_executor=git_executor,
        )

    findings = residual_findings(
        approved=success,
        final_decision=final_decision,
        turn_history=turn_history,
        error=result_error,
    )

    # --- §2f. Map the result. ----------------------------------------------
    if success:
        return _outcome(
            "approved",
            0,
            final_decision=final_decision or APPROVED_DECISION,
            turns=turns,
            branch=branch,
            worktree_path=str(repo_root),
            requirements_source=provenance,
            commit=commit_info,
            plan_audit=plan_audit,
            agent_invocations_validation=validation,
            task_work_results_path=results_path,
            findings=findings,
            budget_expired=budget_expired,
        )

    return _outcome(
        "not-approved",
        2,
        final_decision=final_decision,
        turns=turns,
        branch=branch,
        worktree_path=str(repo_root),
        requirements_source=provenance,
        commit=commit_info,
        plan_audit=plan_audit,
        agent_invocations_validation=validation,
        task_work_results_path=results_path,
        findings=findings,
        budget_expired=budget_expired,
        error=(
            f"the work leg ended without Coach approval "
            f"(final_decision={final_decision!r}"
            + (f", {turns} turn(s)" if turns else "")
            + (f"): {result_error}" if result_error else ")")
        ),
    )


__all__ = [
    "APPROVED_DECISION",
    "DEFAULT_LEG_BUDGET_SECONDS",
    "DEFAULT_MAX_TURNS",
    "DEFAULT_SDK_TIMEOUT_SECONDS",
    "EMPTY_ARTEFACTS_NOTE",
    "PHASE_6_RELOCATION",
    "PHASES_NOT_RUN",
    "WorkLegOutcome",
    "build_outer_worktree",
    "build_receipt",
    "commit_outer_tree",
    "detect_head_branch",
    "extract_markdown_section",
    "lift_gate_blocks",
    "receipt_path_for",
    "residual_findings",
    "run_work_leg",
    "task_work_results_path",
    "thread_requirements",
    "write_receipt",
]
