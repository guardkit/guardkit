#!/usr/bin/env python3
"""Canary validation runner for TASK-HMIG-009.

Drives the 18 autobuild runs (3 canary tasks × 2 harnesses × 3 reps) that
implement TASK-HMIG-009 AC-002 through AC-005, and aggregates per-run
records into ``.guardkit/autobuild/TASK-REV-HMIG-canary-results.json``.

Scaffolding produced by ``/task-work TASK-HMIG-009`` (2026-05-21). The
runner itself is **operator-driven** — it does not start until the
operator runs it, because each invocation costs real LLM tokens and
~10-30 minutes of wall-clock per run.

Inputs
------

* ``.guardkit/autobuild/TASK-REV-HMIG-canary-set.json`` — the canary set
  with per-harness env + model config. Operator may edit task picks.
* The `guardkit autobuild task` CLI must be on PATH (`pip install -e .`).
* For ``GUARDKIT_HARNESS=langgraph``: ``pip install -e ../guardkitfactory``
  must be active and ``http://promaxgb10-41b1:8000/v1`` must be reachable.

Outputs
-------

* ``.guardkit/autobuild/TASK-REV-HMIG-canary-results.json`` — appended-to
  after every run; tolerates resume (skips runs that are already
  recorded).
* ``.guardkit/autobuild/TASK-REV-HMIG-canary/<harness>/<task_id>/run_<n>/``
  — per-run artefacts: stdout, stderr, copy of ``player_turn_*.json`` and
  ``coach_turn_*.json``.

Usage
-----

.. code-block:: shell

    # Dry-run: print the run plan, do nothing.
    python scripts/canary_validation_runner.py --dry-run

    # Execute all 18 runs sequentially. Resumable if interrupted.
    python scripts/canary_validation_runner.py

    # Restrict to one harness or one task (useful for incremental testing).
    python scripts/canary_validation_runner.py --harness langgraph
    python scripts/canary_validation_runner.py --task TASK-FIX-A7D3
    python scripts/canary_validation_runner.py --task TASK-FIX-A7D3 --harness sdk

    # Limit reps (e.g. quick smoke before committing to 18 full runs).
    python scripts/canary_validation_runner.py --reps 1

    # TASK-HMIG-009A partial canary: 2 backlog tasks (drops TASK-GLI-004),
    # 12 runs, written to a dedicated TASK-HMIG-009A-canary namespace so
    # they never conflate with the full 009 results.
    python scripts/canary_validation_runner.py --variant 009a --dry-run
    python scripts/canary_validation_runner.py --variant 009a
    python scripts/canary_validation_runner.py --variant 009a --aggregate

    # Ad-hoc scope narrowing without a named variant:
    python scripts/canary_validation_runner.py --exclude-task TASK-GLI-004

After all runs complete, run the aggregator at the bottom of this
file to produce ``<namespace>-comparison.md``:

.. code-block:: shell

    python scripts/canary_validation_runner.py --aggregate            # full 009
    python scripts/canary_validation_runner.py --variant 009a --aggregate

Non-goals
---------

* This script does NOT decide the falsifier verdict — the operator
  reads the aggregate first-pass-success rate from the comparison doc
  and updates TASK-HMIG-009 AC-007 manually.
* This script does NOT run autobuild in parallel. Sequential keeps
  resource contention predictable and avoids cross-run worktree
  collisions.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Paths (resolved from repo root — assumes the runner is invoked from the
# repo root, which is the GuardKit convention for scripts/).
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
AUTOBUILD_DIR = REPO_ROOT / ".guardkit" / "autobuild"
CANARY_SET_PATH = AUTOBUILD_DIR / "TASK-REV-HMIG-canary-set.json"

# Default output namespace = the full TASK-HMIG-009 canary (18 runs, 3 tasks).
_DEFAULT_NAMESPACE = "TASK-REV-HMIG-canary"


@dataclass
class OutputPaths:
    """Output targets for one canary scope. Each scope variant writes to its
    own namespace so its runs never conflate with another variant's results.
    """

    results_path: Path
    comparison_path: Path
    artefact_root: Path

    @classmethod
    def for_namespace(cls, namespace: str) -> "OutputPaths":
        return cls(
            results_path=AUTOBUILD_DIR / f"{namespace}-results.json",
            comparison_path=AUTOBUILD_DIR / f"{namespace}-comparison.md",
            artefact_root=AUTOBUILD_DIR / namespace,
        )


# Scope variants narrow the canary to a task allowlist and redirect output
# to a dedicated namespace. Default (no --variant) preserves the original
# TASK-HMIG-009 full-canary behaviour.
#
# TASK-HMIG-009A: partial canary — 2 backlog tasks that do NOT need
# fixture-branch isolation (so TASK-FIX-WTBC / F4 is off the critical path).
# Drops TASK-GLI-004 (needs fixture isolation → 009B only). 2 tasks × 2
# harnesses × 3 reps = 12 runs.
VARIANTS: dict[str, dict[str, Any]] = {
    "009a": {
        "namespace": "TASK-HMIG-009A-canary",
        "include_tasks": ["TASK-FIX-A7D3", "TASK-DOC-267D"],
        "central_falsifier": (
            "LangGraph first-pass-success rate is computable across >=6 "
            "LangGraph runs (2 tasks x 3 reps) and meets either (a) >=75% "
            "(cutover proceeds on schedule) or (b) <75% with classified "
            "failure modes (cutover decision reconsidered with evidence). "
            "A null result (no comparison computable) is the only failure. "
            "(TASK-HMIG-009A)"
        ),
    },
}

DEFAULT_PATHS = OutputPaths.for_namespace(_DEFAULT_NAMESPACE)

# Backwards-compatible module-level aliases (referenced by external tooling
# and the docstring). Variant runs thread an OutputPaths instance instead.
RESULTS_PATH = DEFAULT_PATHS.results_path
COMPARISON_PATH = DEFAULT_PATHS.comparison_path
ARTEFACT_ROOT = DEFAULT_PATHS.artefact_root


@dataclass
class RunRecord:
    """A single canary run's outcome — matches TASK-HMIG-009 AC-004."""

    task_id: str
    harness: str
    run_index: int
    started_at: str
    finished_at: str
    wall_clock_seconds: float
    turns_used: int
    coach_decision: str  # "approve" | "feedback" | "error" | "unknown"
    acceptance_criteria_passed: int
    acceptance_criteria_failed: int
    model_used: str
    exit_code: int
    notes: str = ""
    # Optional forensic-recovery hooks (review §11 implementation notes).
    langsmith_trace_id: str | None = None
    artefact_dir: str = ""


@dataclass
class RunPlan:
    task_id: str
    harness: str
    run_index: int
    env: dict[str, str] = field(default_factory=dict)
    model: str = ""
    # Optional pre-fix-baseline replay (TASK-GLI-004 in particular).
    # If set, runner ensures `fixture_branch_name` exists at this commit,
    # then temporarily rewrites the task file's autobuild base_branch to
    # that branch for the duration of the run.
    fixture_baseline_commit: str | None = None
    fixture_branch_name: str | None = None
    # If False, pass --no-pre-loop to autobuild. Default True preserves
    # historical autobuild-task behavior; canary-set.json may override.
    pre_loop: bool = True


def load_canary_set() -> dict[str, Any]:
    if not CANARY_SET_PATH.exists():
        sys.exit(
            f"ERROR: {CANARY_SET_PATH} not found. "
            "This runner depends on the canary set; either run "
            "`/task-work TASK-HMIG-009` to scaffold it, or author it manually."
        )
    return json.loads(CANARY_SET_PATH.read_text())


def load_existing_results(paths: OutputPaths = DEFAULT_PATHS) -> list[dict[str, Any]]:
    if not paths.results_path.exists():
        return []
    try:
        return json.loads(paths.results_path.read_text()).get("runs", [])
    except json.JSONDecodeError:
        # Corrupted; back it up and start fresh so a partial run doesn't
        # block the whole batch forever.
        backup = paths.results_path.with_suffix(".json.corrupt." + str(int(time.time())))
        shutil.copy(paths.results_path, backup)
        print(f"WARNING: {paths.results_path} was unparseable; backed up to {backup}")
        return []


def build_run_plans(
    canary: dict[str, Any],
    reps: int,
    task_filter: str | None,
    harness_filter: str | None,
    include_tasks: list[str] | None = None,
    exclude_tasks: list[str] | None = None,
) -> list[RunPlan]:
    plans: list[RunPlan] = []
    pre_loop = canary.get("pre_loop", True)  # default ON to preserve historical behavior
    include_set = set(include_tasks) if include_tasks else None
    exclude_set = set(exclude_tasks) if exclude_tasks else set()
    for harness in canary["harnesses"]:
        if harness_filter and harness["name"] != harness_filter:
            continue
        for task in canary["canary_tasks"]:
            tid = task["task_id"]
            if task_filter and tid != task_filter:
                continue
            if include_set is not None and tid not in include_set:
                continue
            if tid in exclude_set:
                continue
            for rep in range(1, reps + 1):
                plans.append(
                    RunPlan(
                        task_id=task["task_id"],
                        harness=harness["name"],
                        run_index=rep,
                        env=dict(harness["env"]),
                        model=harness["model"],
                        fixture_baseline_commit=task.get("fixture_baseline_commit"),
                        fixture_branch_name=task.get("fixture_branch_name"),
                        pre_loop=pre_loop,
                    )
                )
    return plans


# ---------------------------------------------------------------------------
# Fixture-branch handling for already-completed canary tasks (TASK-GLI-004).
#
# autobuild reads its base_branch from `git rev-parse --abbrev-ref HEAD`
# in the cwd it's launched from (guardkit/cli/autobuild.py:1190-1199),
# NOT from task frontmatter. So we apply the fixture baseline by
# launching autobuild from a temporary git-worktree checked out at the
# fixture branch.
#
# Layout:
#   <repo>/.guardkit/canary-worktrees/<task_id>/          ← fixture-branch worktree
#       ↳ autobuild creates ITS OWN nested worktree:
#         <canary-worktree>/.guardkit/worktrees/<task_id>/
# ---------------------------------------------------------------------------


def ensure_fixture_branch(branch_name: str, baseline_commit: str) -> None:
    """Create local branch ``branch_name`` at ``baseline_commit`` if absent."""
    rc = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"],
        cwd=REPO_ROOT,
    ).returncode
    if rc == 0:
        return  # branch already exists
    print(f"  Creating fixture branch {branch_name} at {baseline_commit[:12]}...")
    subprocess.run(
        ["git", "branch", branch_name, baseline_commit],
        cwd=REPO_ROOT, check=True, capture_output=True,
    )


def setup_canary_worktree(task_id: str, fixture_branch: str) -> Path:
    """Create or reuse a git worktree at ``fixture_branch`` for canary isolation."""
    canary_root = REPO_ROOT / ".guardkit" / "canary-worktrees" / task_id
    if canary_root.exists():
        existing = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=canary_root, capture_output=True, text=True,
        ).stdout.strip()
        if existing == fixture_branch:
            return canary_root
        # Different branch — tear down and re-create.
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(canary_root)],
            cwd=REPO_ROOT, capture_output=True,
        )
    canary_root.parent.mkdir(parents=True, exist_ok=True)
    print(f"  Creating canary worktree at {canary_root.relative_to(REPO_ROOT)} (branch={fixture_branch})...")
    subprocess.run(
        ["git", "worktree", "add", str(canary_root), fixture_branch],
        cwd=REPO_ROOT, check=True, capture_output=True,
    )
    return canary_root


def cleanup_canary_worktree(task_id: str) -> None:
    """Tear down canary worktree + prune any autobuild-side leftovers.

    autobuild's WorktreeManager creates ``autobuild/<task_id>`` branches
    in the parent repo's branch list. When the canary worktree is removed
    (which contained the inner autobuild worktree), the branch ref
    remains and blocks re-creation on the next rep. We force-delete it.
    """
    canary_root = REPO_ROOT / ".guardkit" / "canary-worktrees" / task_id
    if canary_root.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", str(canary_root)],
            cwd=REPO_ROOT, capture_output=True,
        )
    # Always prune + delete the autobuild branch, even if the canary
    # worktree dir was already gone (the branch may persist independently).
    subprocess.run(["git", "worktree", "prune"], cwd=REPO_ROOT, capture_output=True)
    subprocess.run(
        ["git", "branch", "-D", f"autobuild/{task_id}"],
        cwd=REPO_ROOT, capture_output=True,
    )


def is_already_run(plan: RunPlan, existing: list[dict[str, Any]]) -> bool:
    return any(
        r["task_id"] == plan.task_id
        and r["harness"] == plan.harness
        and r["run_index"] == plan.run_index
        for r in existing
    )


def clean_worktree_state(task_id: str, run_cwd: Path) -> None:
    """Remove prior worktree + autobuild state for a clean re-run.

    The inner worktree autobuild creates lives at
    ``<run_cwd>/.guardkit/worktrees/<task_id>/``; state at
    ``<run_cwd>/.guardkit/autobuild/<task_id>/``. The canary artefacts
    under ``.guardkit/autobuild/TASK-REV-HMIG-canary/`` are NOT touched.
    """
    worktree = run_cwd / ".guardkit" / "worktrees" / task_id
    autobuild_state = run_cwd / ".guardkit" / "autobuild" / task_id
    for path in (worktree, autobuild_state):
        if not path.exists():
            continue
        if path.name == task_id and (path / ".git").exists():
            # Use git worktree remove for the inner worktree. Run it from
            # the canary worktree (run_cwd) since that's the parent
            # working tree that owns the inner worktree.
            rc = subprocess.run(
                ["git", "worktree", "remove", "--force", str(path)],
                cwd=run_cwd,
                capture_output=True,
            ).returncode
            if rc != 0 and path.exists():
                shutil.rmtree(path)
        else:
            shutil.rmtree(path)


def harvest_run_artefacts(task_id: str, dest: Path, run_cwd: Path = REPO_ROOT) -> dict[str, Any]:
    """Copy ``.guardkit/autobuild/<task_id>/`` artefacts into ``dest`` and
    extract aggregate metrics for the run record.

    Harvests from ``run_cwd/.guardkit/autobuild/<task_id>/`` to support the
    canary-worktree wrapper (where state lives under the temp worktree,
    not the repo root). Copies player_turn_*.json + coach_turn_*.json
    flat into ``dest``, and the full sdk_debug/ tree (turn-level
    JSONL streams + system_prompt + sdk_options) into ``dest/sdk_debug/``.
    """
    dest.mkdir(parents=True, exist_ok=True)
    state_dir = run_cwd / ".guardkit" / "autobuild" / task_id

    coach_turns: list[Path] = []
    player_turns: list[Path] = []
    if state_dir.exists():
        for f in sorted(state_dir.glob("coach_turn_*.json")):
            shutil.copy(f, dest / f.name)
            coach_turns.append(f)
        for f in sorted(state_dir.glob("player_turn_*.json")):
            shutil.copy(f, dest / f.name)
            player_turns.append(f)
        # Copy the full sdk_debug/ tree if preservation was enabled.
        sdk_debug_src = state_dir / "sdk_debug"
        if sdk_debug_src.exists():
            sdk_debug_dest = dest / "sdk_debug"
            if sdk_debug_dest.exists():
                shutil.rmtree(sdk_debug_dest)
            shutil.copytree(sdk_debug_src, sdk_debug_dest)
        # task_work_results.json (Player report) — useful for diagnosis.
        twr = state_dir / "task_work_results.json"
        if twr.exists():
            shutil.copy(twr, dest / "task_work_results.json")

    metrics: dict[str, Any] = {
        "turns_used": len(coach_turns),
        "coach_decision": "unknown",
        "acceptance_criteria_passed": 0,
        "acceptance_criteria_failed": 0,
    }

    # Final-turn coach decision + AC summary.
    if coach_turns:
        try:
            last = json.loads(coach_turns[-1].read_text())
            metrics["coach_decision"] = last.get("decision", "unknown")
            # Defensive parsing — different historical schemas have used
            # criteria_verification[] (list of {criterion, status}) and
            # acceptance_criteria_summary {passed_count, failed_count}.
            ac = last.get("criteria_verification")
            if isinstance(ac, list):
                metrics["acceptance_criteria_passed"] = sum(
                    1 for c in ac if str(c.get("status", "")).lower() in {"passed", "verified", "pass"}
                )
                metrics["acceptance_criteria_failed"] = sum(
                    1 for c in ac if str(c.get("status", "")).lower() in {"failed", "not_verified", "fail"}
                )
            else:
                summary = last.get("acceptance_criteria_summary", {})
                metrics["acceptance_criteria_passed"] = summary.get("passed_count", 0)
                metrics["acceptance_criteria_failed"] = summary.get("failed_count", 0)
        except (json.JSONDecodeError, OSError) as e:
            metrics["coach_decision"] = f"parse_error: {e}"

    return metrics


def execute_run(
    plan: RunPlan,
    max_turns: int,
    sdk_timeout: int,
    verbose: bool,
    paths: OutputPaths = DEFAULT_PATHS,
) -> RunRecord:
    """Execute one autobuild invocation and return its record.

    Workflow:
    1. If the plan has a fixture_baseline_commit, ensure a canary worktree
       exists at the fixture branch and use it as run_cwd. Otherwise use
       the repo root.
    2. Clean any prior autobuild state in run_cwd.
    3. Invoke `guardkit autobuild task <id>` from run_cwd with the
       harness env vars + GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1.
    4. Harvest player_turn_*.json, coach_turn_*.json, and the sdk_debug/
       tree into the canary artefact directory.
    """
    artefact_dir = paths.artefact_root / plan.harness / plan.task_id / f"run_{plan.run_index}"
    artefact_dir.mkdir(parents=True, exist_ok=True)

    # Decide run_cwd: canary worktree if fixture-branch, else repo root.
    # Per-rep teardown of the canary worktree for stronger isolation
    # (user pref 2026-05-27): each rep starts from a freshly-checked-out
    # fixture-branch tree.
    if plan.fixture_baseline_commit and plan.fixture_branch_name:
        ensure_fixture_branch(plan.fixture_branch_name, plan.fixture_baseline_commit)
        cleanup_canary_worktree(plan.task_id)
        run_cwd = setup_canary_worktree(plan.task_id, plan.fixture_branch_name)
    else:
        run_cwd = REPO_ROOT
        # Still clean any stale inner worktree from a prior rep.
        clean_worktree_state(plan.task_id, run_cwd)

    cmd = [
        "guardkit",
        "autobuild",
        "task",
        plan.task_id,
        "--max-turns",
        str(max_turns),
        "--sdk-timeout",
        str(sdk_timeout),
    ]
    if plan.model:
        cmd.extend(["--model", plan.model])
    if verbose:
        cmd.append("--verbose")
    if not plan.pre_loop:
        cmd.append("--no-pre-loop")

    env = os.environ.copy()
    env.update(plan.env)
    # Enable SDK debug preservation so the model's assistant messages,
    # tool calls, and full SDK options are captured to disk.
    env["GUARDKIT_AUTOBUILD_PRESERVE_DEBUG"] = "1"

    started_at = datetime.now(timezone.utc).isoformat()
    t0 = time.monotonic()

    stdout_path = artefact_dir / "stdout.log"
    stderr_path = artefact_dir / "stderr.log"
    with stdout_path.open("w") as out, stderr_path.open("w") as err:
        proc = subprocess.run(
            cmd, cwd=run_cwd, env=env, stdout=out, stderr=err
        )

    elapsed = time.monotonic() - t0
    finished_at = datetime.now(timezone.utc).isoformat()

    metrics = harvest_run_artefacts(plan.task_id, artefact_dir, run_cwd=run_cwd)

    notes_parts = [f"see {artefact_dir.relative_to(REPO_ROOT)}/stdout.log"]
    if plan.fixture_baseline_commit:
        notes_parts.append(
            f"canary worktree on {plan.fixture_branch_name}@{plan.fixture_baseline_commit[:12]}"
        )

    return RunRecord(
        task_id=plan.task_id,
        harness=plan.harness,
        run_index=plan.run_index,
        started_at=started_at,
        finished_at=finished_at,
        wall_clock_seconds=round(elapsed, 1),
        turns_used=metrics["turns_used"],
        coach_decision=metrics["coach_decision"],
        acceptance_criteria_passed=metrics["acceptance_criteria_passed"],
        acceptance_criteria_failed=metrics["acceptance_criteria_failed"],
        model_used=plan.model,
        exit_code=proc.returncode,
        notes="; ".join(notes_parts),
        artefact_dir=str(artefact_dir.relative_to(REPO_ROOT)),
    )


def append_result(
    record: RunRecord,
    canary: dict[str, Any],
    existing: list[dict[str, Any]],
    paths: OutputPaths = DEFAULT_PATHS,
    parent_task: str = "TASK-HMIG-009",
    falsifier: str | None = None,
) -> None:
    payload = {
        "schema_version": "1.0.0",
        "parent_task": parent_task,
        "central_falsifier": falsifier or canary["central_falsifier"],
        "updated": datetime.now(timezone.utc).isoformat(),
        "runs": existing + [record.__dict__],
    }
    paths.results_path.write_text(json.dumps(payload, indent=2) + "\n")


# ---------------------------------------------------------------------------
# Aggregation — produces TASK-REV-HMIG-canary-comparison.md from the
# results JSON. Operator runs this with --aggregate after all 18 runs.
# ---------------------------------------------------------------------------


def aggregate(paths: OutputPaths = DEFAULT_PATHS) -> None:
    if not paths.results_path.exists():
        sys.exit(f"ERROR: {paths.results_path} not found. Run the canary runs first.")
    payload = json.loads(paths.results_path.read_text())
    runs: list[dict[str, Any]] = payload.get("runs", [])
    if not runs:
        sys.exit("ERROR: no runs recorded. Nothing to aggregate.")

    by_harness: dict[str, list[dict[str, Any]]] = {"sdk": [], "langgraph": []}
    for r in runs:
        by_harness.setdefault(r["harness"], []).append(r)

    def first_pass_success_rate(rs: list[dict[str, Any]]) -> tuple[int, int, float]:
        first_pass = [r for r in rs if r["coach_decision"] == "approve" and r["turns_used"] == 1]
        total = len(rs)
        rate = (len(first_pass) / total * 100) if total else 0.0
        return len(first_pass), total, rate

    def mean(rs: list[dict[str, Any]], key: str) -> float:
        vals = [r[key] for r in rs if isinstance(r.get(key), (int, float))]
        return round(sum(vals) / len(vals), 2) if vals else 0.0

    sdk_runs = by_harness["sdk"]
    lg_runs = by_harness["langgraph"]
    sdk_fp, sdk_total, sdk_rate = first_pass_success_rate(sdk_runs)
    lg_fp, lg_total, lg_rate = first_pass_success_rate(lg_runs)

    # Falsifier verdict per TASK-HMIG-009 AC-007.
    if lg_rate >= 85:
        verdict = "**STRONGLY CONFIRMED** — proceed at full pace to TASK-HMIG-010."
    elif lg_rate >= 75:
        verdict = (
            "**WEAKLY CONFIRMED** — proceed with elevated risk weighting on R-02 and "
            "R-06; flag at the Wave 4 cutover decision."
        )
    else:
        verdict = (
            "**FALSIFIED per review §11** — HALT Wave 4 cutover. Escalate to operator. "
            "Open follow-up task to decide between (a) extending validation window, "
            "(b) reverting to SDK + Anthropic API-key-redirect lifetime negotiation, "
            "(c) pivoting to a third option."
        )

    md = [
        "# Canary validation comparison — TASK-REV-HMIG",
        "",
        f"> Generated by `scripts/canary_validation_runner.py --aggregate` at "
        f"{datetime.now(timezone.utc).isoformat()} from "
        f"`.guardkit/autobuild/TASK-REV-HMIG-canary-results.json` "
        f"({len(runs)} runs recorded).",
        "",
        "## 1. Aggregate first-pass-success rate (the central falsifier)",
        "",
        f"- **LangGraph**: {lg_fp}/{lg_total} = **{lg_rate:.1f}%**",
        f"- **SDK**: {sdk_fp}/{sdk_total} = **{sdk_rate:.1f}%**",
        "",
        f"### Verdict: {verdict}",
        "",
        "## 2. Per-harness aggregate metrics",
        "",
        "| Metric | SDK | LangGraph |",
        "|---|---|---|",
        f"| First-pass success | {sdk_fp}/{sdk_total} ({sdk_rate:.1f}%) | {lg_fp}/{lg_total} ({lg_rate:.1f}%) |",
        f"| Mean turns used | {mean(sdk_runs, 'turns_used')} | {mean(lg_runs, 'turns_used')} |",
        f"| Mean wall-clock (s) | {mean(sdk_runs, 'wall_clock_seconds')} | {mean(lg_runs, 'wall_clock_seconds')} |",
        f"| Mean ACs passed | {mean(sdk_runs, 'acceptance_criteria_passed')} | {mean(lg_runs, 'acceptance_criteria_passed')} |",
        f"| Mean ACs failed | {mean(sdk_runs, 'acceptance_criteria_failed')} | {mean(lg_runs, 'acceptance_criteria_failed')} |",
        "",
        "## 3. Per-task per-run summary",
        "",
        "| Task | Harness | Run | Turns | Coach | ACs ✓ | ACs ✗ | Wall-clock (s) | Notes |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in sorted(runs, key=lambda x: (x["task_id"], x["harness"], x["run_index"])):
        md.append(
            f"| {r['task_id']} | {r['harness']} | {r['run_index']} | "
            f"{r['turns_used']} | {r['coach_decision']} | "
            f"{r['acceptance_criteria_passed']} | {r['acceptance_criteria_failed']} | "
            f"{r['wall_clock_seconds']} | {r.get('notes', '')} |"
        )
    md.extend([
        "",
        "## 4. Per-task AC equivalence",
        "",
        "_(Manual fill-in: for each canary task, list ACs where SDK and LangGraph agreed (both passed or both failed across all 3 reps) vs disagreed. Use the per-run `coach_turn_N.json` artefacts under `.guardkit/autobuild/TASK-REV-HMIG-canary/` to populate.)_",
        "",
        "## 5. References",
        "",
        "- Canary set: [.guardkit/autobuild/TASK-REV-HMIG-canary-set.json](TASK-REV-HMIG-canary-set.json)",
        "- Raw run records: [.guardkit/autobuild/TASK-REV-HMIG-canary-results.json](TASK-REV-HMIG-canary-results.json)",
        "- Audit analysis: [docs/state/TASK-REV-HMIG/canary-analysis.md](../../docs/state/TASK-REV-HMIG/canary-analysis.md)",
        "- Parent review: [.claude/reviews/TASK-REV-HMIG-review-report.md](../../.claude/reviews/TASK-REV-HMIG-review-report.md)",
        "",
    ])

    paths.comparison_path.write_text("\n".join(md))
    print(f"Wrote {paths.comparison_path.relative_to(REPO_ROOT)}")
    print(f"LangGraph rate: {lg_rate:.1f}% — {verdict.split('—')[0].strip()}")


# ---------------------------------------------------------------------------
# CLI entry point.
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="Print plan; do not run.")
    parser.add_argument(
        "--aggregate",
        action="store_true",
        help="Skip runs; just regenerate TASK-REV-HMIG-canary-comparison.md from existing results.",
    )
    parser.add_argument("--harness", choices=["sdk", "langgraph"], help="Restrict to one harness.")
    parser.add_argument("--task", help="Restrict to one canary task ID.")
    parser.add_argument(
        "--variant",
        choices=sorted(VARIANTS),
        help=(
            "Scope variant. '009a' = partial canary (TASK-FIX-A7D3 + "
            "TASK-DOC-267D, drops TASK-GLI-004) writing to its own "
            "TASK-HMIG-009A-canary namespace. Omit for the full TASK-HMIG-009 "
            "18-run canary."
        ),
    )
    parser.add_argument(
        "--exclude-task",
        action="append",
        default=[],
        metavar="TASK-ID",
        help="Drop a canary task ID from the run (repeatable). Applied after --variant.",
    )
    parser.add_argument("--reps", type=int, default=3, help="Reps per (task, harness). Spec mandates 3.")
    parser.add_argument("--max-turns", type=int, default=5, help="Passed through to `guardkit autobuild task`.")
    parser.add_argument("--sdk-timeout", type=int, default=1200, help="Passed through to `guardkit autobuild task`.")
    parser.add_argument("--verbose", action="store_true", help="Pass `--verbose` to autobuild.")
    args = parser.parse_args()

    # Resolve scope variant → output namespace, task allowlist, falsifier.
    variant = VARIANTS.get(args.variant) if args.variant else None
    if variant:
        paths = OutputPaths.for_namespace(variant["namespace"])
        include_tasks = variant.get("include_tasks")
        parent_task = "TASK-HMIG-009A" if args.variant == "009a" else "TASK-HMIG-009"
        falsifier = variant.get("central_falsifier")
    else:
        paths = DEFAULT_PATHS
        include_tasks = None
        parent_task = "TASK-HMIG-009"
        falsifier = None

    if args.aggregate:
        aggregate(paths)
        return

    canary = load_canary_set()
    existing = load_existing_results(paths)
    plans = build_run_plans(
        canary, args.reps, args.task, args.harness,
        include_tasks=include_tasks, exclude_tasks=args.exclude_task,
    )

    if args.dry_run:
        scope = f"variant={args.variant}" if args.variant else "full canary"
        print(f"Run plan ({scope}, {len(plans)} runs, {len(existing)} already recorded):")
        print(f"  results → {paths.results_path.relative_to(REPO_ROOT)}")
        print(f"  artefacts → {paths.artefact_root.relative_to(REPO_ROOT)}/")
        for p in plans:
            status = "DONE" if is_already_run(p, existing) else "TODO"
            print(f"  [{status}] {p.harness:10s}  {p.task_id:20s}  rep {p.run_index}  model={p.model}")
        return

    todo = [p for p in plans if not is_already_run(p, existing)]
    if not todo:
        print(f"All {len(plans)} runs already complete. Run --aggregate to refresh the comparison doc.")
        return

    print(f"Executing {len(todo)} runs ({len(existing)} already complete, {len(plans) - len(todo) - len(existing)} skipped via filters)...")
    for i, plan in enumerate(todo, 1):
        print(f"\n[{i}/{len(todo)}] {plan.harness}  {plan.task_id}  rep {plan.run_index}")
        record = execute_run(plan, args.max_turns, args.sdk_timeout, args.verbose, paths)
        existing.append(record.__dict__)
        append_result(
            record, canary, [e for e in existing if e is not record.__dict__],
            paths=paths, parent_task=parent_task, falsifier=falsifier,
        )
        print(
            f"  → exit={record.exit_code}  turns={record.turns_used}  "
            f"decision={record.coach_decision}  wall={record.wall_clock_seconds}s"
        )

    print("\nAll runs complete. Re-invoke with --aggregate to refresh the comparison doc:")
    print("  python scripts/canary_validation_runner.py --aggregate")


if __name__ == "__main__":
    main()
