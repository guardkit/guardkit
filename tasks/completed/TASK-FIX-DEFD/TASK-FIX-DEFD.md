---
id: TASK-FIX-DEFD
title: Treat status=deferred as satisfied in FeatureOrchestrator dependency resolver
status: completed
task_type: fix
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
completed: 2026-05-09T00:00:00Z
completed_location: tasks/completed/TASK-FIX-DEFD/
previous_state: in_review
state_transition_reason: "All ACs passing, 8 new tests pass, regression-clean, ruff/mypy clean (no new warnings)"
test_results:
  status: passed
  passed: 11
  failed: 0
  last_run: 2026-05-09
priority: high
tags: [orchestrator, dependency-resolver, operator-handoff, deferred, FPTC-003-followup]
complexity: 2
estimated_effort_days: 0.25
parent_review: TASK-REV-D509
related_reviews:
  - TASK-REV-D509  # study-tutor repo: FEAT-39E1 autobuild run-2 post-mortem that surfaced this gap
related_features:
  - FEAT-39E1  # study-tutor's NATS Fleet Integration; the failure that surfaced this bug
related_tasks:
  - TASK-FPTC-003  # introduced status=deferred without extending the predicate
implementation_mode: task-work
---

# Task: Treat `status=deferred` as a satisfied dependency in `FeatureOrchestrator`

## Description

The orchestrator has internally inconsistent semantics for `status="deferred"`:

- **Writer path** (`feature_orchestrator.py:3461-3466`) treats `deferred` as
  terminal-but-not-failed, preserving the status explicitly and storing the
  `deferred_reason`. Introduced by TASK-FPTC-003 for `task_type: operator_handoff` skips.
- **Predicate path** (`feature_orchestrator.py:3429-3433`) hard-codes
  `dep_task.status != "completed"` as unsatisfied — so any wave with a `deferred`
  predecessor crashes with `DependencyError`.

This task closes the contract gap: **`_dependencies_satisfied` should accept
`status in {"completed", "deferred"}`**, with a `logger.warning(...)` whenever a dependent
proceeds against a `deferred` predecessor (operator's signal that the dependent's premise
should be cross-checked).

## Surfacing incident

Filed by the FEAT-39E1 (study-tutor NATS Fleet Integration) autobuild run-2 post-mortem on
2026-05-08. After 17 of 18 tasks reached terminal state — including `TASK-NATS-PH1-010`
correctly skipped as `operator_handoff` (E2E demo gate, requires GB10 + Open WebUI + manual
runbook) — the wave-8 dispatcher crashed with:

```
DependencyError: Task TASK-NATS-PH2-001 has unsatisfied dependencies: ['TASK-NATS-PH1-010']
```

Even though PH2-001 had no real code dependency on PH1-010 (and PH3-004 in the same wave
was completely independent), the dep predicate's `status != "completed"` check raised before
any wave-8 task dispatched.

Full root-cause analysis and decision matrix:
**study-tutor repo** → `.claude/reviews/TASK-REV-D509-review-report.md` (TASK-REV-D509).

The downstream consumer (study-tutor) sidesteps this by removing the spurious dep edges in
its own feature yaml (TASK-NATS-FIX-003, in study-tutor repo). This upstream task is the
**durable fix** for the next FEAT in this situation.

## Scope

### 1. Predicate change — `guardkit/orchestrator/feature_orchestrator.py`

Add a module-level constant alongside other terminal-state metadata:

```python
# TASK-FIX-DEFD: terminal states that satisfy a dependency edge.
# `deferred` is terminal-but-not-failed (TASK-FPTC-003 contract); dependents may
# proceed but receive a warning so the operator can cross-check the dependent's
# premise still holds.
TERMINAL_SATISFIED: frozenset[str] = frozenset({"completed", "deferred"})
```

Update `_dependencies_satisfied` (currently lines 3409-3433):

```python
def _dependencies_satisfied(
    self,
    task: FeatureTask,
    feature: Feature,
) -> bool:
    """
    Check if all dependencies for a task are satisfied.

    A dependency is satisfied if its terminal status is "completed" or
    "deferred". When a dependent proceeds against a deferred predecessor,
    a WARNING is emitted naming both task IDs and the deferred reason — the
    dependent task is asserting that the deferred predecessor's artefacts
    are not load-bearing for its own scope.
    """
    for dep_id in task.dependencies:
        dep_task = FeatureLoader.find_task(feature, dep_id)
        if dep_task is None:
            continue  # unknown predecessor; existing behaviour
        if dep_task.status not in TERMINAL_SATISFIED:
            return False
        if dep_task.status == "deferred":
            deferred_reason = (
                dep_task.result.deferred_reason
                if dep_task.result is not None
                else None
            )
            logger.warning(
                "[%s] Proceeding against deferred predecessor [%s] "
                "(reason=%r). Dependent task assumes the deferred "
                "predecessor's artefacts are not load-bearing for its "
                "own scope.",
                task.id, dep_id, deferred_reason,
            )
    return True
```

### 2. Tests

Add to whichever test module covers `_dependencies_satisfied` today (look for existing
coverage of this method in `tests/orchestrator/`; if none exists, add to the closest
equivalent module).

Required cases:

- **`completed` predecessor → satisfied, no warning.** Regression guard.
- **`deferred` predecessor → satisfied, WARNING emitted** containing both task IDs and the
  `deferred_reason`. Use `caplog` to assert the warning record.
- **`failed` predecessor → unsatisfied.** Regression guard.
- **`pending` predecessor → unsatisfied.** Regression guard.
- **`in_progress` predecessor → unsatisfied.** Regression guard.
- **Mixed: one `completed` + one `deferred` predecessor → satisfied, exactly one warning.**
- **Unknown predecessor (`find_task` returns None) → satisfied.** Existing behaviour.

### 3. Module docstring (optional but recommended)

Add a short note alongside the existing TASK-FPTC-003 references explaining the
TERMINAL_SATISFIED semantics, so future readers see the contract documented at the file
level rather than only at the predicate.

## Acceptance Criteria

- [x] `_dependencies_satisfied` accepts `status in {"completed", "deferred"}` as satisfied.
- [x] When a dependent proceeds against a `deferred` predecessor, a `logger.warning(...)`
      record is emitted naming both task IDs and the predecessor's `deferred_reason`.
- [x] All test cases above are added and pass.
- [x] Existing test suite continues to pass (regression-clean for `completed`, `failed`,
      `pending`, `in_progress` predecessors).
- [x] No behavioural change for the `_update_feature` writer path or the
      `_maybe_defer_operator_handoff` short-circuit.
- [x] `TERMINAL_SATISFIED` is the single source of truth — no string-literal duplication of
      `"deferred"` inside the predicate.

## Implementation note (deviation from spec)

The task spec showed `dep_task.result.deferred_reason` (attribute access) but
`FeatureTask.result` is `Optional[Dict[str, Any]]` (per `feature_loader.py:240`
and the writer at `feature_orchestrator.py:3472-3477`). Implemented as
`dep_task.result.get("deferred_reason")` with a `None` guard. Behaviour is
equivalent; the spec example had a minor type error.

## Verification

```bash
pytest tests/orchestrator/ -v -k "dependencies_satisfied or _wave_phase or operator_handoff"
ruff check guardkit/orchestrator/feature_orchestrator.py
mypy guardkit/orchestrator/feature_orchestrator.py
```

## Implementation Notes

- TASK-FPTC-003 introduced `status="deferred"` as a terminal-but-not-failed state. This task
  completes the contract that work started by extending the dependency predicate. Reference
  TASK-FPTC-003 in the change rationale and commit message.
- The warning is intentionally non-blocking. The dependent task asserts its own scope does
  not require the deferred predecessor's artefacts. If a real load-bearing case ever
  emerges, the operator must either (a) un-defer the predecessor or (b) re-encode the
  feature spec to omit the dependent until the operator follow-up lands.
- The richer fix — soft-vs-hard dep distinction in the feature yaml schema — was considered
  and rejected as YAGNI in the parent review (TASK-REV-D509 § Decision 1, option (d)).
  Don't add it speculatively here.

## Out of Scope

- Schema migration to add `dependency_type: hard|soft`.
- Changes to `_update_feature` or `_maybe_defer_operator_handoff` behaviour.
- Operator-handoff classification heuristics (frontmatter probe at lines 3303-3340 stays as-is).
- Downstream feature-yaml fixes (those are per-repo decisions; study-tutor handled its own
  via TASK-NATS-FIX-003).

## Cross-references

- Predicate to change: `guardkit/orchestrator/feature_orchestrator.py:3409-3433`.
- Writer path that already treats `deferred` as terminal: `feature_orchestrator.py:3461-3466`.
- Operator-handoff short-circuit (TASK-FPTC-003): `feature_orchestrator.py:3303-3407`.
- Wave dispatch dep check site: `feature_orchestrator.py:2055-2061`.
- Parent review (in study-tutor repo):
  `~/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-D509-review-report.md`.
- Failure log that surfaced this:
  `~/Projects/appmilla_github/study-tutor/docs/history/autobuild-FEAT-39E1-fail-run-2.md`.
