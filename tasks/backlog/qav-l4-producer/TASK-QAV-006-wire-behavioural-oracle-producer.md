---
id: TASK-QAV-006
title: Wire the L4 behavioural-oracle PRODUCER into gather_evidence (discovery, independence,
  execution, population)
task_type: feature
parent_review: TASK-REV-QAVG
feature_id: FEAT-0E6D
wave: 1
implementation_mode: task-work
complexity: 6
dependencies: []
priority: critical
status: in_review
autobuild_state:
  current_turn: 4
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-0E6D
  base_branch: main
  started_at: '2026-07-04T23:08:12.960501'
  last_updated: '2026-07-05T00:22:42.692730'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- The file 'tests/acceptance/x_roundtrip.py' required by AC-001 is\
      \ missing from the disk, as identified by the plan_audit violation.: Ensure\
      \ the failing oracle file 'tests/acceptance/x_roundtrip.py' is created and present\
      \ in the repository to allow for end-to-end verification of the red $\to$ green\
      \ cycle."
    timestamp: '2026-07-04T23:08:12.960501'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: "- Deterministic honesty record (claim_audit_unmodified, severity=should_fix):\
      \ Player claim: Player claimed file conversation_history/session_0ef47dea.md.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- Deterministic honesty record (claim_audit_unmodified,\
      \ severity=should_fix): Player claim: Player claimed file conversation_history/session_5036aca9.md.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- Deterministic honesty record (claim_audit_unmodified,\
      \ severity=should_fix): Player claim: Player claimed file conversation_history/session_bca36ccf.md.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n... and 4 more issues"
    timestamp: '2026-07-04T23:32:55.868817'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- Coach verdict-emission failed: Coach decision not found: no assistant
      text in harness events for TASK-QAV-006 turn 3 (0 AssistantMessageEvent). Likely
      substrate limitation (qwen36-workhorse F2 at Coach level). Player should retry
      on turn 4 with this feedback.'
    timestamp: '2026-07-04T23:51:54.798241'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 4
    decision: approve
    feedback: null
    timestamp: '2026-07-05T00:11:52.774687'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
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
