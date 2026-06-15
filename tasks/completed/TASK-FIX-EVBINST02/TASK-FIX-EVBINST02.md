---
id: TASK-FIX-EVBINST02
title: Extend the evidence-boundary filter to large_tool_results/ and .claude/task-plans/ (residual claim_audit noise)
status: completed
task_type: fix
created: 2026-06-14T16:25:00Z
updated: 2026-06-15T00:00:00Z
completed: 2026-06-15T00:00:00Z
previous_state: in_review
state_transition_reason: "task-complete — all acceptance criteria met, quality gates passed"
completed_location: tasks/completed/TASK-FIX-EVBINST02/
commit: bfe4e0fa
priority: low
complexity: 2
related: [TASK-FIX-EVBINST01, TASK-FIX-PCN, FEAT-9DDE]
implementation_mode: task-work
tags: [autobuild, evidence-boundary, claim-audit, orchestrator-managed-paths, noise]
---

# Task: filter residual orchestrator/harness-induced paths from the evidence boundary

## Why this task exists

Follow-up to TASK-FIX-EVBINST01 (which stripped `.local/`/`site-packages/`/
`.venv*/` and dropped run-8's claim_audit noise from 144 → 8 issues). The
remaining residual `claim_audit_unmodified` (should_fix) records observed in
FEAT-9DDE run 8 (coach_turn_2.json) were on **two more orchestrator/harness-
induced namespaces** the filter does not yet cover:

- `large_tool_results/fc_<hash>...` — the harness writes large tool-result
  spillover files here; the post-turn `git diff` sweeps them into
  `files_modified`.
- `.claude/task-plans/TASK-XXX-implementation-plan.md` — the orchestrator
  creates the plan stub; it is not Player work product.

These are `should_fix` (non-blocking) — run 8/9 fed back / failed on real
issues, not this noise — but they still pollute the Player report and the
Coach claim audit, and they are the **same class** as EVBINST01 (orchestrator-
induced paths swept into the evidence boundary;
`evidence-boundary-narrower-than-write-surface.md`, over-wide direction).

## Fix

Extend the existing `_ORCHESTRATOR_MANAGED_PATH_PATTERNS` constant in
`guardkit/orchestrator/agent_invoker.py` (the EVBINST01 site) with two
anchored patterns:

```python
re.compile(r"^large_tool_results/"),     # harness tool-result spillover
re.compile(r"^\.claude/task-plans/"),    # orchestrator-created plan stubs
```

One constant; consumed by both the Player-report writer and the Coach claim
audit (shared `_is_orchestrator_managed_path`), so both are fixed.

## Acceptance Criteria

- [x] `large_tool_results/...` and `.claude/task-plans/...` are stripped from
      `files_modified`/`files_created`/`tests_written` before the report
      reaches the Coach, and generate no `claim_audit_unmodified` records.
      Two anchored patterns added to `_ORCHESTRATOR_MANAGED_PATH_PATTERNS`
      ([agent_invoker.py:209-225](../../../guardkit/orchestrator/agent_invoker.py#L209));
      the constant is shared by the Player-report writer
      (`_strip_orchestrator_managed_paths`) and the Coach claim audit
      ([coach_verification.py:573](../../../guardkit/orchestrator/coach_verification.py#L573)).
- [x] Over-reach guard: real Player paths under `.claude/` other than
      `task-plans/` (if any are legitimately Player-authored) are not
      over-broadened — pattern anchored to `^\.claude/task-plans/`. Verified by
      `TestResidualHarnessNamespaceFilter::test_residual_over_reach_guard`
      (`.claude/agents/`, `.claude/rules/`, `.claude/settings.json`,
      `.claude/task-plans-notes.md` all pass through).
- [x] Regression test in `tests/unit/test_orchestrator_induced_path_filter.py`
      — new `TestResidualHarnessNamespaceFilter` class (match, over-reach
      guard, strip-keeps-real-work) + updated the now-reversed
      `.claude/task-plans/` assertion in `TestInstallArtifactFilter`.

## Outcome

Fix landed in `guardkit/orchestrator/agent_invoker.py`
(`_ORCHESTRATOR_MANAGED_PATH_PATTERNS` gained `^large_tool_results/` and
`^\.claude/task-plans/`). 61/61 tests pass in the path-filter suite;
135 pass across the combined Coach-verification + claim-audit + path-filter
run. Same class as EVBINST01 (orchestrator-induced paths swept into the
evidence boundary, over-wide direction —
`evidence-boundary-narrower-than-write-surface.md`).

## Evidence
- `docs/retro/run8-evidence/coach_turn_2.json` (4 claim_audit records: 2
  `large_tool_results/`, 1 `.claude/task-plans/`, 1 real `tests/` path).
- Sibling fix: TASK-FIX-EVBINST01 (commit `dbed7e3a`).
