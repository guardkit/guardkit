# Implementation Plan — TASK-FIX-SPECVIOL01

**Intensity**: light (fresh task, complexity 5, no high-risk keywords)
**Date**: 2026-06-12

## Root cause (corrected from task framing)

Forensics on `.guardkit/autobuild/FEAT-C332-run2-artifacts-TASK-QAWE-002/`
show the turn-1 `must_fix` honesty discrepancy did NOT come directly from the
orchestrator-injected `agent_invocations` records (honesty checks never read
that field). It came from the **claim-audit gate**:

- Player promise AC-018 carried
  `test_file: "tests/orchestrator/test_coach_evidence_bundle.py, tests/unit/orchestrator/quality_gates/test_coach_validator.py"`
  — a comma-joined string of two paths the Player **ran** (both exist and are
  tracked in the worktree).
- `CoachVerifier._verify_claims_were_staged` normalises the whole string as
  ONE path → absent from porcelain → `_classify_dropped_path` →
  `Path.exists()` False → `"fabricated"` → `claim_audit` critical →
  always `must_fix` (claim_audit is exempt from the FFC3 demotion) →
  `partial_honesty_abort` → all 9 criteria verifications dropped.

Two compounding semantic bugs:

1. **Comma-joined `test_file`** treated as a single path — guaranteed
   false "fabricated".
2. **`test_file` is a run-claim, not an authored-file claim.** A Player that
   ran an existing tracked test file produces no staged change; auditing it
   against the would-be-staged set misattributes substrate/protocol noise as
   Player dishonesty (the `path-string-mismatch-is-not-dishonesty` meta-class).

Separately, AC-002 needs the substrate failure (specialist hang) surfaced as
an attributed advisory, which today is only visible via the generic
agent-invocations advisory (names missing phases, not the specialist error).

## Changes

### 1. `guardkit/orchestrator/coach_verification.py` — `_verify_claims_were_staged`

- Split `completion_promises[*].test_file` on commas before normalising
  (Players routinely emit a comma-joined list in this free-text field).
- Track test_file-sourced claims separately (`run_claims`). For a dropped
  path that is test_file-sourced and classified `tracked_unmodified`, emit
  **no discrepancy** (running an existing tracked test legitimately produces
  no staged change — zero signal, not noise).
- All other classifications unchanged:
  - test_file path absent from disk → `fabricated` critical (**AC-004**:
    genuine test-claim fabrication still short-circuits).
  - gitignored → `claim_audit_gitignored` should_fix.
  - files_created/files_modified-sourced `tracked_unmodified` →
    `claim_audit_unmodified` should_fix (existing TASK-FIX-PCN behaviour).

### 2. `guardkit/orchestrator/quality_gates/coach_validator.py` — specialist-failure advisory (AC-002)

New helper `_compute_specialist_failure_advisories(task_work_results)`:
scan `agent_invocations` for `source == "orchestrator"` with
`status in {"failed", "skipped"}` and a non-empty `error`; emit a
`should_fix` advisory (`category: "specialist_substrate"`) naming the
specialist, phase, and error. Wire into `gather_evidence`'s
`advisory_issues` (rides along on both the abort path and the normal path)
and into legacy `validate()`'s advisory block.

### 3. Tests

- `tests/unit/test_coach_verification_claim_audit.py` (extend):
  - comma-joined test_file naming two committed files → no discrepancies
    (FEAT-C332 run-2 turn-1 reproducer at verifier layer);
  - single existing tracked test_file → no discrepancy;
  - test_file naming nonexistent path → critical `claim_audit` (AC-004);
- `tests/orchestrator/test_specialist_violation_attribution.py` (new):
  - AC-001/AC-003 regression: synthetic `task_work_results.json` with
    orchestrator-injected `validation=violation` + failed specialist records
    + honest Player claims (incl. the comma-joined run-claim) →
    `gather_evidence` does NOT return `partial_honesty_abort`;
  - AC-002: bundle `advisory_issues` contains a `specialist_substrate`
    advisory naming `test-orchestrator` and the hang error;
  - AC-004: fabricated test_file claim alone → `partial_honesty_abort`
    preserved.

## Estimates

- Files: 2 modified + 1 new test file + 1 extended test file
- LOC: ~180 (including tests)
- Risk: low — narrowing of one discrepancy class + additive advisory
