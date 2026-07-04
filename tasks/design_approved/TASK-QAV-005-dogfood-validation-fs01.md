---
complexity: 4
dependencies:
- TASK-QAV-003
- TASK-QAV-004
feature_id: FEAT-10AC
id: TASK-QAV-005
implementation_mode: task-work
parent_review: TASK-REV-QAVG
priority: high
status: design_approved
task_type: testing
title: Dogfood validation — fs-01 reproducer + correctly-wired stub go RED end-to-end
wave: 5
---

# Task: Dogfood validation — the new gates catch the class they were built for

## Description

End-to-end validation that the assembled L2+L3+L4 evidence turns RED exactly
the cases the current Coach turns GREEN, per the execution-plan dogfood rule
and the eval frame in the 2 July starter ("Success = the QA Verifier turns
those cases RED where the current Coach turns them GREEN").

Two mandatory validation cases:

1. **The fs-01 class** (`fs-01-coach-false-approval-partial-run`,
   FEAT-MEM-04): a fixture reproducing the shape — green co-generated tests,
   7/7 SUCCESS-style self-report, a real regression only an independent
   behavioural run exposes. The L4 oracle must flip the verdict to feedback.
2. **A deliberate correctly-wired stub** (the class L1 cannot catch): fully
   registered in a composition root, referenced by non-test code, green unit
   tests, body returns plausibly-shaped constants. L2 (stub finding) + L3
   (zero real execution of the logic path) must both flag it; L1 wiring
   evidence alone must NOT (asserting the layer boundary from consolidation
   §2 — "FEAT-C332 does not catch a correctly-wired stub").

## Acceptance Criteria

- [ ] **AC-1 (fs-01 reproducer):** the fixture drives the full Coach evidence
  path with a failing independent round-trip oracle; the persisted verdict is
  `feedback` with the oracle failure in the issues; with the L4 guard disabled
  the same fixture approves (proving the gate is the difference).
- [ ] **AC-2 (correctly-wired stub):** the stub fixture yields ≥1 `stub_scan`
  finding AND ≥1 `coverage` zero-execution finding, while `wiring` reports the
  symbol as WIRED with no finding — pinning the L1/L2 layer boundary.
- [ ] **AC-3 (no false-red sweep):** a genuine, fully-implemented fixture
  (real logic, real execution, passing independent oracle) produces zero
  findings across all three new fields with positive statuses — the clean
  path stays clean.
- [ ] **AC-4 (absent-signal sweep):** for each of the three fields, the
  absent case (probe didn't run) is asserted `None` end-to-end through
  `task_work_results.json` and the checkpoint layer — no coercion to pass or
  fail anywhere (ABFIX-010 regression class).
- [ ] **AC-5 (bundle render):** the assembled bundle with all three fields
  populated renders into the Coach prompt within the truncation rules and is
  parseable as the additive seam shape (forward-compatible for the forge
  consumer).
- [ ] **AC-6:** full guardkit + guardkitfactory suites green; all modified
  files pass project-configured lint/format checks with zero errors.

## Test Requirements

This task is primarily `tests/integration/` fixtures + assertions; it authors
no production logic. The fs-01 fixture shape may be synthesized (a minimal
app with a lifespan/DI-style regression) — it does not need fleet-memory
itself, only the class of defect.

## Implementation Notes

- Keep the two fixture projects small (a handful of files each) and
  self-contained under the integration-test tree.
- The @task-tagged Gherkin scenarios for this feature
  (`features/qav-behavioural-gates/qav-behavioural-gates.feature`) should be
  bound with per-task glue naming (`test_<slug>__TASK_QAV_005.py`) per
  `.claude/rules/bdd-per-task-glue.md` where scenarios map to this task.