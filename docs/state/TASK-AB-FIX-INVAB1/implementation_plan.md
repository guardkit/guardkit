# Implementation Plan — TASK-AB-FIX-INVAB1

**Task**: Restore adversarial honesty verification on the deterministic Coach path

**Mode**: TDD (RED → GREEN → REFACTOR), Intensity: STRICT

**Provenance**: TASK-INV-AB1 review report supplies the C4/sequence diagrams and the per-AC code snippets that this plan operationalises. The plan does not invent design — it sequences the work the AC text already specifies.

## Files to modify

1. `guardkit/orchestrator/coach_verification.py` — Extend `CoachVerifier` with `_verify_completion_promises_files_exist`, wire it into `verify_player_report`, update `_count_verifiable_claims` (~30 LOC).
2. `guardkit/orchestrator/quality_gates/coach_validator.py` — Wire `CoachVerifier` into `CoachValidator.validate()` before quality-gate evaluation; extend `to_dict()` to surface `honesty_verification`; tighten `_hybrid_fallback` (AC-004); add AC-cited-test-file existence check near `_detect_test_command` (AC-006) (~80 LOC).
3. `guardkit/orchestrator/agent_invoker.py` — Plan-audit `skipped` escalation when AC-cited paths missing (AC-005) (~40 LOC).

## Files to create

### Test files (RED phase first per TDD)
1. `tests/integration/orchestrator/test_coach_honesty_restoration.py` — AC-007 wiring proof.
2. `tests/integration/orchestrator/test_coach_blocks_promised_missing_files.py` — AC-008 FEAT-6CC5 reproducer + AC-009 backwards-compat + AC-010 idempotency.
3. `tests/unit/orchestrator/quality_gates/test_coach_validator_hybrid_fallback.py` — AC-011 hybrid-fallback regression.
4. `tests/unit/orchestrator/quality_gates/test_coach_validator_plan_audit_escalation.py` — AC-005 plan-audit escalation tests.
5. `tests/unit/orchestrator/quality_gates/test_coach_validator_test_command_honesty.py` — AC-006 test-command honesty tests.
6. `tests/unit/test_coach_verification_promises.py` — AC-001 unit tests for new `_verify_completion_promises_files_exist`.

### Documentation
1. `.claude/rules/absence-of-failure-is-not-success.md` — AC-012 meta-rule.
2. `docs/guides/autobuild-instrumentation-guide.md` — AC-013 interim merge-time check (append, file already exists).
3. `.claude/reviews/TASK-REV-0414-review-report.md` — AC-014 addendum (append note at end).

## Implementation phases

### Phase A — RED (write failing tests)
- Write all unit + integration tests for AC-001/002/003/004/005/006.
- Confirm each test fails (or errors) against current code.

### Phase B — GREEN (architectural restoration)
- AC-001: Add `_verify_completion_promises_files_exist` method to `CoachVerifier`; wire into `verify_player_report`; extend `_count_verifiable_claims`.
- AC-002: Wire `CoachVerifier` into `CoachValidator.validate()` immediately after `task_work_results` are loaded successfully and before the `agent_invocations_validation` advisory block. Translate critical discrepancies into `must_fix` issues with `category="honesty"`. Short-circuit with `decision="feedback"` when honesty issues exist.
- AC-003: Add `honesty_verification` block to `CoachValidationResult` (new dataclass field) and to `to_dict()`.

### Phase C — GREEN (defence-in-depth)
- AC-004: In `_hybrid_fallback`, remove the `or "Promise status: incomplete"` clause and tighten the `"No completion promise"` branch to require any AC-cited file path to exist on disk.
- AC-005: In `agent_invoker._compute_plan_audit_verdict` `result.get("skipped")` branch, scan AC for paths and escalate to `status: "violation"`, `severity: "high"`, `missing_files: [...]` when any AC-named file is absent on disk.
- AC-006: In `CoachValidator._detect_test_command` (or a dedicated pre-check), scan AC for test-file path patterns; emit `must_fix` issue and bypass the existing-test-files run if any AC-cited test path is absent.

### Phase D — REFACTOR + Documentation
- AC-012: Author `.claude/rules/absence-of-failure-is-not-success.md` with three known instances and grep signatures.
- AC-013: Append the post-merge `task_work_results.json` verification script to the autobuild instrumentation guide.
- AC-014: Append addendum to the TASK-REV-0414 review report acknowledging that Option D's adversarial-rigor claim is delivered only when `CoachVerifier` is wired into the deterministic path.

## Risk register

- **R1 — Performance / duplicate pytest runs**: `CoachVerifier.verify_player_report` runs pytest, and `CoachValidator.run_independent_tests` also runs pytest. Mitigation: Pass `tests_run=False` to `CoachVerifier` when the player report doesn't claim a run, OR skip the verifier's `_verify_test_results` when an independent run will follow. Concretely, we'll skip `_verify_test_results` for the deterministic-Coach call site (CoachValidator already runs `run_independent_tests` separately) and only invoke `_verify_files_exist`, `_verify_test_count`, and the new `_verify_completion_promises_files_exist`.
- **R2 — Backwards compat regressions**: Honest player reports must produce zero discrepancies. Covered by AC-009 backwards-compat test.
- **R3 — Hybrid-fallback over-tightening**: Removing the `incomplete` branch could break legitimate "promise written but file later renamed" cases. Mitigation: AC-011 paired test (legitimate "No completion promise" case still upgrades correctly).
- **R4 — Existing CoachValidator tests breaking**: Many existing tests build `task_work_results` with no `files_created`/`files_modified`, expecting `decision=approve`. Wiring honesty into `validate()` could newly reject such tests. Mitigation: When `files_created=[]`, `files_modified=[]`, `tests_written=[]`, `completion_promises=[]`, the verifier produces zero discrepancies (no claims to verify) — so the wire-in is benign for those fixtures.

## Effort estimate

- LOC: ~250 (production), ~600 (tests + docs)
- Duration: 4-6 hours (matches task estimate)
- Complexity: 6/10 (multi-file change in critical adversarial path; well-scoped by review report)

## Test strategy

- All new tests are filesystem-only (no SDK invocations).
- Existing tests in `tests/unit/orchestrator/` and `tests/unit/test_coach_verification.py` must continue to pass (no test modifications).
- Coverage target: ≥85% lines (strict mode requirement).
