---
id: TASK-FIX-A7B2
title: Tighten conditional-approval rule to distinguish source-file contention from infra contention
status: backlog
task_type: bugfix
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
priority: high
complexity: 6
dependencies: []
external_reference:
  source_repo: appmilla_github/study-tutor
  reports:
    - /home/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-AB7A-report.md
    - /home/richardwoollcott/Projects/appmilla_github/study-tutor/.claude/reviews/TASK-REV-AB7A-addendum-source-traced.md
related_tasks:
  - TASK-ABFIX-005  # Original isolation-snapshot fix; do not regress
related_features: [autobuild, coach-validator]
tags: [autobuild, coach-validator, conditional-approval, parallel-contention, false-positive]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Tighten conditional-approval rule to distinguish source-file contention from infra contention

## Description

`guardkit/orchestrator/quality_gates/coach_validator.py:851-874` — the
`parallel_contention` branch grants conditional approval whenever
`failure_class == "parallel_contention" and gates_status.all_gates_passed`.

By design (per TASK-ABFIX-005), the rule deliberately does **not** check
`requires_infra`, on the assumption that contention is transient
infrastructure contention worth retrying with an isolation snapshot.

In the FEAT-70A4 failure (sibling study-tutor repo), two parallel tasks
(TASK-PRV-002 and TASK-PRV-003) wrote conflicting step definitions to the
same shared BDD glue file `features/<slug>/test_<slug>.py`. The contention
was a real source-file conflict, not a transient infra issue.

The existing TASK-ABFIX-005 isolation snapshot logic in
`coach_validator.py:1700-1750` cannot defend against this case because
both tasks had committed inconsistent state to the same branch **before**
either snapshot was taken — the snapshot is a point-in-time view of the
already-corrupted shared file.

The result: the wave was conditionally approved despite real correctness
damage, and the failure surfaced only at the wave-2 verification step
when the BDD glue collapsed.

## Cross-reference

See §3 of `<sibling>/.claude/reviews/TASK-REV-AB7A-addendum-source-traced.md`
for the C4 sequence diagram showing the failure mode, and §2 of the main
report for the failure timeline.

## Acceptance Criteria

- [ ] AC-001: AutoBuildOrchestrator (or the coach validator's per-feature
      state, whichever is the natural seat) tracks per-task file-edit sets
      across in-flight wave parallel tasks. Likely surface: an existing
      `_changed_files` map keyed by task id, captured between Player
      finish and Coach evaluation.
- [ ] AC-002: When `_classify_test_failure` returns `parallel_contention`
      (in `coach_validator.py:851-874`), the rule checks whether the
      failing test command's collected files overlap with another
      in-flight task's edit set within the same wave.
- [ ] AC-003: If overlap is detected, the verdict is **not** conditional
      approval. Instead, a serialised retry of the failing task only is
      triggered (existing retry machinery — do not invent new control
      flow).
- [ ] AC-004: If no overlap is detected, the existing TASK-ABFIX-005
      conditional-approval path remains intact (no regression on
      genuinely-transient contention).
- [ ] AC-005: Regression test: a synthetic two-task wave where both tasks
      edit `features/foo/test_foo.py` produces a non-conditional-approved
      verdict for the failing task, and a serialised retry runs.
- [ ] AC-006: TASK-ABFIX-005 isolation-snapshot tests continue to pass.

## Files Likely To Change

- `guardkit/orchestrator/quality_gates/coach_validator.py` — the
  `parallel_contention` branch at lines 851-874, plus possibly the
  isolation-snapshot helper at lines 1700-1750 if shared state needs
  threading through.
- `guardkit/orchestrator/feature_orchestrator.py` (or the autobuild
  orchestrator) — exposing the per-task changed-files map to the coach
  validator. Audit how `_changed_files` (or its equivalent) is currently
  populated and scoped.
- `guardkit/orchestrator/quality_gates/__init__.py` or contract types —
  if a new shared dataclass is needed for the wave-level edit map.

## Out Of Scope

- Reworking the wave isolation-snapshot architecture (TASK-ABFIX-005)
  itself. This task narrows the conditional-approval rule; it does not
  replace the snapshot.
- Detecting overlap at plan time — that is TASK-FIX-A7B3 (sibling task
  filed alongside this one). The two tasks are complementary: A7B3
  prevents the conflict from being scheduled; this task ensures that when
  it does happen, the false-conditional-approval doesn't mask it.
