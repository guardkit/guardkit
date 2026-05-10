# Autobuild BDD-oracle infrastructure fix (FEAT-AB-FIX) — guardkit slice

> Three guardkit-side fixes that, together with two fleet-gateway tasks, unblock the
> FEAT-FG-001 autobuild stall.

**Parent review:** [TASK-REV-8413](../../../../../fleet-gateway/tasks/backlog/TASK-REV-8413-analyse-autobuild-feat-fg-001-stall.md) (in the fleet-gateway repo)
**Findings:** [docs/history/autobuild-FEAT-FG-001-review.md](../../../../../fleet-gateway/docs/history/autobuild-FEAT-FG-001-review.md) (in the fleet-gateway repo)
**Sibling slice:** [`fleet-gateway/tasks/backlog/autobuild-bdd-oracle-fix/`](../../../../../fleet-gateway/tasks/backlog/autobuild-bdd-oracle-fix/) — owns
TASK-AB-002 (pytest-bdd dev dep) and TASK-AB-005 (resume + verify).

## Why This Exists

A diagnostic review of FEAT-FG-001's `unrecoverable_stall` (in the fleet-gateway repo)
concluded that the implementation was correct but the BDD oracle infrastructure had four
defects, three of which live here in guardkit:

1. The orchestrator does not pass `python_executable` to `bdd_runner.run_bdd_for_task`,
   so the BDD subprocess uses system pytest and cannot import worktree-local packages.
2. `BDDFailure.reason` for collection errors carries only the literal string
   `"collection failure"` — the actual junit `<error>` message (e.g. the Python
   `ModuleNotFoundError`) is dropped, so Coach feedback to the Player is non-actionable.
3. Parallel tasks within a wave race on a single shared `test_<slug>.py`. The bdd_runner
   has no concept of per-task glue modules.

The four-task-set spent 5 turns each chasing nonexistent implementation bugs because the
Coach told them *"Implementation does not satisfy the Gherkin specification"* — when in
reality the test module wouldn't even import.

## Subtask Summary (guardkit slice)

| Task | Wave | Mode | Complexity | Estimate | Summary |
|------|-----:|------|-----------:|---------:|---------|
| [TASK-AB-001](TASK-AB-001-pass-python-executable-to-bdd-runner.md) | 1 | task-work | 3 | 30m | Resolve `<worktree>/.venv/bin/python3` and pass it as `python_executable` to `run_bdd_for_task`. |
| [TASK-AB-003](TASK-AB-003-surface-junit-error-in-coach-feedback.md) | 1 | task-work | 4 | 60m | Parse junit `<error>` payload into `BDDFailure.reason`; have the feedback summariser pass it through verbatim. |
| [TASK-AB-004](TASK-AB-004-per-task-bdd-test-modules.md) | 1 | task-work | 6 | 120m | bdd_runner sets `GUARDKIT_BDD_TASK_ID=<id>`; conftest collection bridge prefers `test_<slug>__<TASK-ID>.py` over `test_<slug>.py`. Includes follow-up edit to fleet-gateway's `features/conftest.py`. |

**Total guardkit work:** 3 tasks · ~3.5h focused work, all parallel-safe.

## Wave Layout

All three guardkit tasks are Wave 1 in the larger feature plan and share no files / no
logical dependency:

- AB-001 edits the orchestrator caller of `run_bdd_for_task`.
- AB-003 edits `bdd_runner.py`'s junit parser + the orchestrator's feedback summariser.
- AB-004 edits `bdd_runner.py`'s subprocess argv assembly + the project template
  `features/conftest.py`.

There is no overlap, so they can land in any order or in parallel. Wave 2 (TASK-AB-005,
the autobuild resume) lives in the fleet-gateway repo and depends on all three of these
plus AB-002.

## How to Run

```bash
cd ~/Projects/appmilla_github/guardkit
/task-work TASK-AB-001
/task-work TASK-AB-003
/task-work TASK-AB-004
```

Or if your autobuild orchestrator is happy with cross-repo `working_dir`, run from
fleet-gateway:

```bash
cd ~/Projects/appmilla_github/fleet-gateway
guardkit autobuild feature FEAT-AB-FIX
```

## What Stays Untouched (in fleet-gateway)

- `common/jarvis_client.py`, `common/graphiti_client.py`, and the existing BDD test
  module in `.guardkit/worktrees/FEAT-FG-001/` are correct and must not be regenerated.
  TASK-AB-005 only renames the test module; it does not re-author it.

## See Also

- [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) — guardkit-slice walkthrough.
- [Sibling fleet-gateway slice README](../../../../../fleet-gateway/tasks/backlog/autobuild-bdd-oracle-fix/README.md) — TASK-AB-002 and TASK-AB-005.
- [Parent review report](../../../../../fleet-gateway/docs/history/autobuild-FEAT-FG-001-review.md) — full diagnostic findings.
- [Original failure log](../../../../../fleet-gateway/docs/history/autobuild-FEAT-FG-001-fail-run-1.md).
