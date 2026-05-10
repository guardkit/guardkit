---
id: TASK-FIX-IGNR
title: Coach claim-audit should classify gitignored-but-present paths as a non-critical warning, not a critical fabrication
status: in_review
task_type: implementation
implementation_mode: task-work
parent_review: TASK-REV-F30A
external_origin: study-tutor/tasks/backlog/TASK-REV-F30A-analyse-feat-39e1-autobuild-run-3-failure.md
priority: medium
created: 2026-05-10T18:00:00Z
updated: 2026-05-10T19:30:00Z
previous_state: backlog
state_transition_reason: "Quality gates passed; moving to in_review"
complexity: 5
tags: [coach-validator, claim-audit, honesty-verification, defence-in-depth, observability]
related_tasks:
  - TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT
dependencies: []
inputs:
  source_file: guardkit/orchestrator/coach_verification.py
  test_file: tests/unit/test_coach_verification_claim_audit.py
  reference: |
    coach_verification.py:226-234, 362-521
    coach_validator.py:865-905
test_results:
  status: passed
  coverage: null
  last_run: 2026-05-10T19:30:00Z
  summary: "12/12 unit + 6/6 integration tests pass for modified surface; 2 unrelated TestSdkEnvMerge failures (Python 3.10 vs asyncio.timeout) pre-exist on main."
---

# Task: Coach claim-audit should classify gitignored-but-present paths as a non-critical warning

## Description

The Coach claim-audit oracle (`coach_verification.py:_verify_claims_were_staged`, line 362-521) currently emits a single `Discrepancy(claim_type="claim_audit", severity="critical")` for every Player-claimed path missing from `git status --porcelain` output. The audit's own docstring (lines 376-381) and the "actual_value" boilerplate (lines 510-516) explicitly call out that the most common cause is a `.gitignore` rule silently filtering a present file. But the resulting `severity="critical"` makes `coach_validator.py:884-886` short-circuit gate evaluation, fail the turn, and trigger the adversarial-loop dynamics that turned a 3-discrepancy turn-1 into a 200-discrepancy turn-5 in study-tutor FEAT-39E1 run-3 ([TASK-REV-F30A review report](study-tutor/.claude/reviews/TASK-REV-F30A-review-report.md)).

The right semantics are:

| Situation                                                              | Classification              | Effect on gate                                          |
|------------------------------------------------------------------------|-----------------------------|---------------------------------------------------------|
| Path NOT on disk and NOT staged                                        | `severity="critical"`       | Short-circuit (current behaviour, correct: fabrication) |
| Path IS on disk, IS gitignored (matched by `git check-ignore`)         | `severity="should_fix"` warning, with the matched ignore rule reported | Do NOT short-circuit; surface as actionable feedback |
| Path IS on disk, NOT gitignored, but absent from porcelain (e.g. tracked-but-unchanged claim where Player said "modified") | `severity="critical"` (current behaviour) | Short-circuit (correct: Player lying about modifications) |
| Path IS on disk and IS in porcelain output                              | (not flagged)               | OK                                                      |

The new "warning with rule" output is high-value diagnostic — the operator immediately sees `path: matched by '.gitignore:284 adapters/'` and can fix the .gitignore rather than chasing Player honesty across five turns.

## Acceptance Criteria

- [ ] **AC-1**: in `_verify_claims_were_staged`, before emitting a `Discrepancy`, if the path exists on disk (`(self.worktree_path / path).exists()`), run `git check-ignore -v <path>`. If the path is gitignored (exit 0), emit `Discrepancy(claim_type="claim_audit_gitignored", severity="should_fix", ignore_rule=<rule from -v output>)` instead of critical. Otherwise (exit 1 or path doesn't exist), keep the current `severity="critical"` behaviour.
- [ ] **AC-2**: `should_fix`-severity claim-audit discrepancies do NOT count toward `critical_failures` in the honesty score formula at `coach_verification.py:243-244`. They contribute to a new `should_fix_count` field on `HonestyVerification` and surface in the Coach feedback message (so the Player can act on them).
- [ ] **AC-3**: `coach_validator.py:865-905` short-circuit logic only fires when `critical_failures > 0`; `should_fix` discrepancies do NOT short-circuit gate evaluation. The orchestrator can therefore approve a turn with gitignored claim-audit warnings if the rest of the gates pass.
- [ ] **AC-4**: New unit test `test_claim_audit_gitignored_is_should_fix_not_critical` reproduces the FEAT-39E1 scenario: tmp_path with a .gitignore containing unanchored `adapters/`, a Player report claiming `src/pkg/adapters/foo.py`, the file actually authored on disk. Assert: `HonestyVerification.critical_failures == 0`, `should_fix_count == 1`, `discrepancies[0].severity == "should_fix"`, `discrepancies[0].ignore_rule contains '.gitignore' and 'adapters/'`.
- [ ] **AC-5**: New unit test `test_claim_audit_fabricated_path_still_critical` ensures the regression for actual fabrication (path not on disk) keeps `severity="critical"`.
- [ ] **AC-6**: Coach feedback message includes a "Hint: rebase the worktree onto main if the .gitignore was fixed there" when `should_fix_count > 0` and at least one matched rule appears in the project root `.gitignore` (a check via `git check-ignore` against the root).
- [ ] **AC-7**: All existing `coach_verification` tests continue to pass.

## Implementation Notes

- The classifier change is at most 30 lines of code in `_verify_claims_were_staged` plus the two new tests. Keep the existing `git status --porcelain` invocation as-is; add a *second* `git check-ignore -v --no-index <path>` call per dropped path. The `--no-index` is important — it asks "would this rule match if the path existed?" rather than requiring the path to be tracked.
- `git check-ignore -v` exit codes: `0 = ignored` (with rule on stdout), `1 = not ignored`, `128 = fatal`. Map exit 0 to `should_fix`, exit 1 to `critical` (the original semantics for "tracked-but-unchanged" or "sparse-checkout"), exit 128 to fail-open (don't block, log warning) — same defensive posture as line 463-470.
- This is defence-in-depth, not a blocker for FEAT-39E1 recovery (which is unblocked by TASK-NATS-FIX-004 + TASK-NATS-FIX-005 in the study-tutor repo).
