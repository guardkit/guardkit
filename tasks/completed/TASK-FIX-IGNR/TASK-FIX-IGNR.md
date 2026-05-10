---
id: TASK-FIX-IGNR
title: Coach claim-audit should classify gitignored-but-present paths as a non-critical warning, not a critical fabrication
status: completed
task_type: implementation
implementation_mode: task-work
parent_review: TASK-REV-F30A
external_origin: study-tutor/tasks/backlog/TASK-REV-F30A-analyse-feat-39e1-autobuild-run-3-failure.md
priority: medium
created: 2026-05-10T18:00:00Z
updated: 2026-05-10T19:45:00Z
completed: 2026-05-10T19:45:00Z
completed_location: tasks/completed/TASK-FIX-IGNR/
implementation_commit: 5203bc17
previous_state: in_review
state_transition_reason: "All ACs delivered; tests pass; landed before 2026-05-11 freeze"
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

- [x] **AC-1**: in `_verify_claims_were_staged`, before emitting a `Discrepancy`, if the path exists on disk (`(self.worktree_path / path).exists()`), run `git check-ignore -v <path>`. If the path is gitignored (exit 0), emit `Discrepancy(claim_type="claim_audit_gitignored", severity="should_fix", ignore_rule=<rule from -v output>)` instead of critical. Otherwise (exit 1 or path doesn't exist), keep the current `severity="critical"` behaviour.
- [x] **AC-2**: `should_fix`-severity claim-audit discrepancies do NOT count toward `critical_failures` in the honesty score formula at `coach_verification.py:243-244`. They contribute to a new `should_fix_count` field on `HonestyVerification` and surface in the Coach feedback message (so the Player can act on them).
- [x] **AC-3**: `coach_validator.py:865-905` short-circuit logic only fires when `critical_failures > 0`; `should_fix` discrepancies do NOT short-circuit gate evaluation. The orchestrator can therefore approve a turn with gitignored claim-audit warnings if the rest of the gates pass.
- [x] **AC-4**: New unit test `test_claim_audit_gitignored_is_should_fix_not_critical` reproduces the FEAT-39E1 scenario: tmp_path with a .gitignore containing unanchored `adapters/`, a Player report claiming `src/pkg/adapters/foo.py`, the file actually authored on disk. Assert: `HonestyVerification.critical_failures == 0`, `should_fix_count == 1`, `discrepancies[0].severity == "should_fix"`, `discrepancies[0].ignore_rule contains '.gitignore' and 'adapters/'`.
- [x] **AC-5**: New unit test `test_claim_audit_fabricated_path_still_critical` ensures the regression for actual fabrication (path not on disk) keeps `severity="critical"`.
- [x] **AC-6**: Coach feedback message includes a "Hint: rebase the worktree onto main if the .gitignore was fixed there" when `should_fix_count > 0` and at least one matched rule appears in the project root `.gitignore` (a check via `git check-ignore` against the root).
- [x] **AC-7**: All existing `coach_verification` tests continue to pass.

## Implementation Notes

- The classifier change is at most 30 lines of code in `_verify_claims_were_staged` plus the two new tests. Keep the existing `git status --porcelain` invocation as-is; add a *second* `git check-ignore -v --no-index <path>` call per dropped path. The `--no-index` is important — it asks "would this rule match if the path existed?" rather than requiring the path to be tracked.
- `git check-ignore -v` exit codes: `0 = ignored` (with rule on stdout), `1 = not ignored`, `128 = fatal`. Map exit 0 to `should_fix`, exit 1 to `critical` (the original semantics for "tracked-but-unchanged" or "sparse-checkout"), exit 128 to fail-open (don't block, log warning) — same defensive posture as line 463-470.
- This is defence-in-depth, not a blocker for FEAT-39E1 recovery (which is unblocked by TASK-NATS-FIX-004 + TASK-NATS-FIX-005 in the study-tutor repo).

## Implementation Summary

**Approach**: Split `CoachVerifier._verify_claims_were_staged` dropped-path emission by running `git check-ignore -v --no-index` per dropped path. Path absent from disk OR `check-ignore` exit 1 → keeps `severity="critical"` `claim_type="claim_audit"` (fabrication / tracked-but-unchanged). Path on disk AND `check-ignore` exit 0 → new `severity="should_fix"` `claim_type="claim_audit_gitignored"` carrying the matched `<source>:<line>:<pattern>` rule on a new `Discrepancy.ignore_rule` field. Exit 128 / subprocess error → fail-open back to critical so the FEAT-39E1 detection floor stays put on infra failure.

**Wiring**: `HonestyVerification` gains `should_fix_count` for accounting parity with `critical_failures`. `CoachValidator._verify_honesty` propagates the count. `CoachValidator._honesty_issues_from` translates the new should_fix discrepancies into `category="claim_audit"` `severity="should_fix"` issues that ride along to feedback via the existing `honesty_should_fix` channel (no new short-circuit branch). When the matched rule's source is the project-root `.gitignore`, the issue description gains a "rebase the worktree onto main" hint (AC-6).

**Outcome**: All 7 ACs delivered. 12/12 unit + 6/6 integration tests pass on the modified surface. Two pre-existing `TestSdkEnvMerge` failures (Python 3.10 vs `asyncio.timeout`, 3.11+) confirmed unrelated by reproducing on bare main. Landed as commit `5203bc17` on 2026-05-10, before the 2026-05-11 gate-stack freeze begins.

**Lessons**:

- The integration tests `test_claim_audit_short_circuits_gate_evaluation` and `test_single_claim_audit_not_demoted_to_should_fix` previously used a gitignored worktree as a proxy for "any critical claim_audit". After the IGNR demotion, both needed to switch to a pure-fabrication scenario (path absent from disk) to keep their original assertion intent — the gitignored case no longer carries the must_fix critical signal. Renaming considered but kept the test names so reviewers can trace the contract evolution; semantic intent now lives in a new `test_gitignored_claim_audit_does_not_short_circuit` sibling test.
- AC-7's "all existing coach_verification tests continue to pass" is in tension with AC-1's contract change for the gitignored case. Resolved by interpreting AC-7 as the *suite* remaining green: tests that directly encoded the old gitignored-as-critical contract were updated to the new contract; tests that test orthogonal behaviour (zero-cardinality, fail-open, normalisation, etc.) needed no changes.
- `verify_player_report` runs both `_verify_files_exist` and `_verify_claims_were_staged`. For a path that is absent from disk, both gates fire (file_existence critical + claim_audit critical). The AC-5 fabrication test had to filter to claim_audit-family discrepancies rather than asserting `len(discrepancies) == 1` — the file_existence sibling is orthogonal and remains correctly wired.

**Related ADRs**: TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT (introduced the gate). Sibling rules: `.claude/rules/absence-of-failure-is-not-success.md` (this is the *false-red* sibling: a binary verdict from a low-fidelity oracle that cannot distinguish "no signal" from "negative signal"; a single-discrepancy gitignored signal was wrongly turn-rejecting). `.claude/rules/path-string-mismatch-is-not-dishonesty.md` (same meta-frame: identity-aware classification before path-equality verdict).
