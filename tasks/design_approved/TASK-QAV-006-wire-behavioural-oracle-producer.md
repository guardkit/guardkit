---
complexity: 6
dependencies: []
feature_id: FEAT-0E6D
id: TASK-QAV-006
implementation_mode: task-work
parent_review: TASK-REV-QAVG
priority: critical
status: design_approved
task_type: feature
title: Wire the L4 behavioural-oracle PRODUCER into gather_evidence (discovery, independence,
  execution, population)
wave: 1
---

# Task: Wire the L4 behavioural-oracle producer

## Description

FEAT-10AC delivered the L4 **guard** (`_apply_behavioural_oracle_guard`,
`agent_invoker.py` ~L6510, wired at the verdict seam ~L2441, fully unit
tested) but NOT the **producer**: `CoachValidator.gather_evidence` hardcodes
`behavioural_oracle=None` (`coach_validator.py` ~L3581, comment "Wave-4"),
so the guard no-ops forever and the L4 hard gate can never fire. The
TASK-QAV-005 dogfood test was soft-pedaled to match ("documents the L4 field
as None until Wave-4 is wired") — a runner-without-producer instance caught
at merge review, on the very feature built to catch that class.

This task wires the producer, honouring the FEAT-10AC spec exactly
(TASK-QAV-004's original ACs, `features/qav-behavioural-gates/` scenarios
tagged @task:TASK-QAV-004):

1. **Discovery by artefact presence**: oracle file(s) at
   `tests/acceptance/*_roundtrip.py` in the worktree; no opt-in flag
   (`.claude/rules/activate-by-artefact-not-opt-in-flag.md`).
2. **Independence check**: the oracle file must NOT be in the turn's
   authored set (`files_authored` when present, else `files_created ∪
   files_modified`; never the git-enriched set). Player-authored oracle →
   `{status: "not_independent"}` + should_fix warning; never trusted, never
   blocks.
3. **Execution**: run the oracle via the worktree venv interpreter with a
   bounded timeout (default 300s, env `GUARDKIT_ORACLE_TIMEOUT`).
   Outcome policy: ran-and-failed → `{status:"ran", passed:false}` (the
   guard fires); started-then-timed-out → ran-and-failed (COACHRUNPARITY01
   semantics); failed-to-start / no oracle discovered → absent (`None` or
   `{status:"absent"}` per the guard's consumed shape — match what
   `_apply_behavioural_oracle_guard` and its tests already expect).
4. **Population**: on the COMPLETE gather path only, replace the hardcoded
   `behavioural_oracle=None` with the producer result; partial/honesty
   early-returns keep `None`. Absent signals survive serialization
   unchanged.

## Acceptance Criteria

- [ ] **AC-1 (producer wired, red→green):** with an independent failing
  oracle at `tests/acceptance/x_roundtrip.py`, `gather_evidence` populates
  `behavioural_oracle` with a ran-and-failed result and the EXISTING guard
  overrides approve→feedback end-to-end (the FEAT-10AC fs-01 AC, now real).
  Without the producer wiring the same fixture approves (red test).
- [ ] **AC-2 (pass path):** an independent passing oracle populates
  `{status:"ran", passed:true, oracle_path, provenance}`; no override.
- [ ] **AC-3 (independence):** a Player-authored oracle yields
  `not_independent` + warning; neither passes nor blocks.
- [ ] **AC-4 (timeout asymmetry):** started-then-hung → ran-and-failed;
  failed-to-start → absent. Both pinned.
- [ ] **AC-5 (absence discipline):** no oracle file → field stays `None`
  end-to-end through `to_dict()`; never coerced to pass/fail; guard no-ops.
- [ ] **AC-6 (un-soften the dogfood):** rewrite the FEAT-10AC soft-pedaled
  tests: `test_fs01_verdict_is_feedback_with_oracle` must assert the REAL
  verdict flip with a real (not mocked) failing oracle fixture and assert
  `bundle.behavioural_oracle is not None`; remove the "Wave-4 not yet
  wired" notes. `test_fs01_approves_with_l4_disabled` proves the gate is
  the difference.
- [ ] **AC-7:** existing suites green (incl. the 533-line guard suite
  unchanged); all modified files pass project-configured lint/format
  checks with zero errors.

## Implementation Notes

- The guard already defines the consumed dict shape — read
  `_apply_behavioural_oracle_guard` + `tests/orchestrator/test_behavioural_oracle_guard.py`
  FIRST and produce exactly that shape; do not invent a second contract
  (single source of truth).
- Reuse the independent-test execution plumbing (worktree venv resolution,
  subprocess timeout discipline) from the existing gates; do not add a new
  subprocess layer.
- Population point: the complete-path `CoachEvidenceBundle(...)` return in
  `gather_evidence` (beside `stub_scan=`/`coverage=`), mirroring how
  TASK-QAV-003 wired `run_coverage_gate_for_bundle`.