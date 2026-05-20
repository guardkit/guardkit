---
id: TASK-HMIG-008R
title: Restore LLM Coach as primary decision-maker + refactor CoachValidator into CoachEvidenceBundle supplier
status: backlog
task_type: refactor
created: 2026-05-19T20:30:00Z
updated: 2026-05-20T10:30:00Z
revision: 3
revision_rationale: "v1/v2 TASK-HMIG-008 preserved the 2025-12-30 Option D regression (deterministic CoachValidator as primary). Operator confirmed the LLM Coach must be restored as primary, per the Block adversarial-cooperation paper. v1/v2 task definition (4h, honesty Layer 1 wiring only) is preserved at the bottom of this file for audit. See main report §14.9 for full rationale."
supersedes: [TASK-HMIG-008]
priority: critical
complexity: 7
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 2
parallel_group: 2C
implementation_mode: task-work
intensity: strict
effort_hours: 12
depends_on:
  - TASK-HMIG-006   # needs HarnessAdapter dispatch path so LLM Coach can go through guardkitfactory
  - TASK-HMIG-007   # needs BDD plugin interface so the evidence bundle has structured BDD output
cross_repo:
  notes: |
    Predominantly guardkit-side work. Touches frozen paths (coach_validator.py, agent_invoker.py, autobuild.py) but
    the changes are pre-authorised by .claude/rules/path-string-mismatch-is-not-dishonesty.md remediation recipe AND
    by the Revision 3 architectural correction (operator-approved 2026-05-20). One guardkitfactory touch: the LLM Coach
    is invoked through guardkitfactory.LangGraphHarness with read-only tools.
falsifier: |
  Composite — three falsifiers, all must pass:
  (1) Per-turn flow: LLM Coach is invoked on EVERY turn (not just on CoachValidator exception);
      the path `autobuild._invoke_coach -> CoachValidator.validate()` for the decision is GONE.
      `GUARDKIT_COACH_LEGACY=1` reactivates the legacy path as emergency revert.
  (2) Evidence bundle: CoachValidator exposes a new `gather_evidence(task_id, turn, task, ...) -> CoachEvidenceBundle`
      method. The bundle is rendered into the LLM Coach prompt as structured evidence (coverage, plan audit,
      BDD plugin output, honesty discrepancies with Layer 1 / Layer 3' identity resolutions).
  (3) Zero-cardinality guard: when the BDD plugin returns scenarios_attempted=0 (Pattern 2 fixture), the
      LLM Coach must NOT approve. Test: run the existing Pattern-3 (FFC3-style state-bridge move) fixture
      AND a Pattern-2 zero-cardinality fixture; assert both produce `feedback` (not `approve`) under
      GUARDKIT_HARNESS=langgraph.
tags:
  - autobuild
  - coach
  - llm-coach-restoration
  - block-adversarial-cooperation
  - langgraph-migration
  - frozen-path-touch
  - architectural-correction
---

# Task: Restore LLM Coach as primary + refactor CoachValidator into CoachEvidenceBundle supplier

## Context

This task corrects the 2025-12-30 architectural regression where the
deterministic `CoachValidator` became the primary Coach path (Option D /
TASK-REV-0414), demoting the LLM Coach to a fallback that runs only when
the deterministic path raises an exception
([`autobuild.py:5281-5355`](../../../guardkit/orchestrator/autobuild.py)).

The original AutoBuild design — per the Block adversarial-cooperation paper
([`block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf`](https://block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf)) —
has the LLM Coach as the primary decision-maker, with deterministic checks
acting as evidence the Coach reads. This task restores that design.

The corrected per-turn flow:

```
1. Player runs (unchanged, DeepAgents via guardkitfactory.LangGraphHarness)
2. Pre-Coach evidence gathering:
   a. CoachVerifier.verify() — honesty checks with Layer 1 / Layer 3' identity resolutions
   b. CoachValidator.gather_evidence() — NEW METHOD; runs existing gate logic but returns
      a structured CoachEvidenceBundle instead of a decision
3. LLM Coach invoked unconditionally via guardkitfactory.LangGraphHarness (read-only tools):
   - Prompt rendered from Player report + CoachEvidenceBundle + explicit absence-of-failure guards
   - Coach reads evidence, optionally runs additional verification via Read/Bash/Grep/Glob
   - Coach writes coach_turn_N.json with approve/feedback decision
4. Decision parsing (unchanged)
```

Emergency-revert: `GUARDKIT_COACH_LEGACY=1` env var falls back to the
current deterministic-primary path.

## Acceptance Criteria

### Part A — Refactor CoachValidator into evidence supplier

- [ ] AC-001: New dataclass `CoachEvidenceBundle` at `guardkit/orchestrator/quality_gates/coach_evidence.py` with fields:
  - `coverage`: structured coverage results (line, branch, file-level breakdowns)
  - `plan_audit`: plan-audit findings (violations, scope-creep warnings)
  - `bdd`: BDDRunResult from the §6 plugin interface (or null if no BDD oracle ran)
  - `honesty`: HonestyVerification including `resolved_paths` annotations (Layer 1 / Layer 3' suppressions visible to the Coach)
  - `arch_review`: SOLID/DRY/YAGNI scores
  - `tests`: test-pass/fail counts, coverage thresholds met, requires-infrastructure status
  - `severity_recommendations`: structured hints ("this single file_existence discrepancy was Layer-1 resolved; treat as should_fix not must_fix") — derived from the existing demotion logic in coach_validator.py
- [ ] AC-002: New method `CoachValidator.gather_evidence(self, task_id, turn, task, ...) -> CoachEvidenceBundle` that runs the existing gate logic (the same logic `validate()` currently runs) but returns the bundle instead of an approve/feedback decision.
- [ ] AC-003: `CoachValidator.validate()` is preserved as a backward-compat shim that calls `gather_evidence()` and then applies the legacy decision logic. Used only when `GUARDKIT_COACH_LEGACY=1` is set, or by direct callers that haven't migrated. Marked deprecated in docstring.
- [ ] AC-004: All existing CoachValidator tests continue to pass when run with `GUARDKIT_COACH_LEGACY=1`.

### Part B — Make LLM Coach the primary path in `autobuild._invoke_coach`

- [ ] AC-005: `autobuild._invoke_coach` flow inverted. Default flow (`GUARDKIT_COACH_LEGACY` unset):
  1. Call `CoachValidator.gather_evidence(...)` to produce the bundle
  2. Call `CoachVerifier.verify(player_report, ...)` to produce honesty result (already exists)
  3. Render both into the LLM Coach prompt via an updated `_build_coach_prompt` (see Part C)
  4. Invoke the LLM Coach via `self._agent_invoker.invoke_coach(...)` (existing) which goes through `HarnessAdapter` (TASK-HMIG-006). Under `GUARDKIT_HARNESS=langgraph`, this routes to `guardkitfactory.LangGraphHarness` with read-only tools.
  5. Decision file `coach_turn_N.json` written by the LLM Coach (unchanged on-disk contract)
- [ ] AC-006: `GUARDKIT_COACH_LEGACY=1` env var triggers the legacy flow (CoachValidator decides; LLM Coach is fallback). Document in `guardkit doctor` and operator notes as emergency-revert.
- [ ] AC-007: Logging clearly indicates which path ran. "Using LLM Coach (primary)" vs "Using CoachValidator (legacy, GUARDKIT_COACH_LEGACY=1)".

### Part C — Coach prompt with evidence bundle + absence-of-failure guards

- [ ] AC-008: `_build_coach_prompt` (in agent_invoker.py) is extended to render the `CoachEvidenceBundle` and `HonestyVerification` as structured prompt sections.
- [ ] AC-009: The prompt includes EXPLICIT absence-of-failure guards (verbatim, paraphrased OK):
  - "If `evidence.bdd.scenarios_attempted == 0`, treat as ABSENT SIGNAL — do NOT approve based on absence of failure. Surface as feedback."
  - "If `evidence.tests.tests_run == 0`, treat as ABSENT SIGNAL — do NOT approve."
  - "If `evidence.honesty.discrepancies` contains entries with `severity=critical` AND `category != file_existence`, you MUST reject the turn (these are sophisticated lies; structural rejection)."
  - "If `evidence.honesty.discrepancies` contains a single `file_existence` discrepancy that was Layer-1-resolved (`resolved_paths` non-empty), demote to `should_fix` and continue evaluation."
- [ ] AC-010: Prompt includes the Player report and the evidence bundle as JSON for unambiguous reading.

### Part D — Honesty Layer 1 / Layer 3' preserved as evidence

- [ ] AC-011: `CoachVerifier._verify_files_exist()` consults `TaskStateBridge.canonical_path_for(task_id)` and records `HonestyVerification.resolved_paths`. (Already done by TASK-FIX-1B4A, 2026-05-06; verify it still fires from the new primary path.)
- [ ] AC-012: `AgentInvoker._create_player_report_from_task_work` continues to subtract orchestrator-induced paths from `files_modified` (Layer 3'). (Already done by TASK-FIX-1B4C, 2026-05-06; verify.)
- [ ] AC-013: Regression test from `.claude/rules/path-string-mismatch-is-not-dishonesty.md` Remediation Recipe: simulate state-bridge move during turn 1, Player report contains pre-move path, LLM Coach is invoked, Coach evaluates the ACs and does not reject on the path-only discrepancy.

### Part E — Falsifiers as concrete tests

- [ ] AC-014: New test `tests/orchestrator/test_coach_evidence_bundle.py`:
  - `CoachValidator.gather_evidence()` returns a populated `CoachEvidenceBundle` for a passing-turn fixture
  - The bundle has Layer-1 resolutions populated when the fixture includes a state-bridge move
- [ ] AC-015: New test `tests/orchestrator/test_llm_coach_primary.py`:
  - Default flow (`GUARDKIT_COACH_LEGACY` unset): LLM Coach is invoked for every turn (assert agent_invoker.invoke_coach was called)
  - Legacy flow (`GUARDKIT_COACH_LEGACY=1`): CoachValidator.validate() is invoked instead
- [ ] AC-016: New test `tests/orchestrator/test_coach_zero_cardinality_guard.py`:
  - Pattern 2 fixture (BDD plugin returns scenarios_attempted=0, scenarios_failed=0): under the new LLM Coach prompt, the Coach returns `feedback` not `approve`
  - This is the Pattern 6 (`absence-of-failure-is-not-success.md`) guard at the LLM layer
- [ ] AC-017: Existing TASK-FIX-1B4A regression test (Pattern 3 / state-bridge move) continues to pass under both default and legacy flows.

## Implementation Notes

- This task touches frozen paths (`coach_validator.py`, `coach_verification.py`, `agent_invoker.py`, `autobuild.py`). The TASK-REV-ABST freeze closed 2026-05-17, so no override is required. The changes are architecturally significant — document the rationale in the commit message and reference review §14.9.
- The new prompt language for AC-009 absence-of-failure guards is the LLM-layer equivalent of the structural guards in [`absence-of-failure-is-not-success.md`](../../.claude/rules/absence-of-failure-is-not-success.md). When in doubt, copy the rule's language verbatim into the prompt.
- The LLM Coach already gets read-only tools (Read, Bash, Grep, Glob) per [`agent_invoker.py:1886`](../../guardkit/orchestrator/agent_invoker.py). No new tool surface needed — the Coach can `cat tests/...` and `pytest tests/...` itself if it wants to verify the evidence.
- The `CoachEvidenceBundle` schema is intentionally close to what `CoachValidator.validate()` already computes internally. The refactor is mostly *exposing* the existing intermediate values, not computing new ones.
- For the LangGraph cross-repo path (`GUARDKIT_HARNESS=langgraph`), the Coach invocation goes through `guardkitfactory.LangGraphHarness.invoke(role="coach", tools=[Read, Bash, Grep, Glob])`. The tool list is the read-only subset; the Coach's `LocalShellBackend` should be configured with the read-only built-in tools surface (`ls`, `read_file`, `glob`, `grep`, `execute`) — write/edit tools are not bound for the Coach role.
- Risk R-13 (LLM Coach approves on zero-cardinality) is the load-bearing migration risk under Revision 3. AC-009 and AC-016 are the two mitigations on the critical path.

## References

### Revision 3 (the architectural correction)
- Parent review **§14.9** Revision 3 log
- Parent review §1.1 condition #1 (revised)
- Parent review §8 D-06 (revised)
- Parent review §9 R-13 (new)
- [`block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf`](https://block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf) — the source paper

### Architectural history
- [TASK-INV-AB1 review report](../../.claude/reviews/TASK-INV-AB1-review-report.md) — investigation that documented the 2025-12-30 regression
- [TASK-REV-0414 review report](../../.claude/reviews/TASK-REV-0414-review-report.md) — the 2025-12-30 Option D decision that introduced the regression
- [TASK-AB-FIX-INVAB1](../../tasks/completed/2026-05/TASK-AB-FIX-INVAB1/) — 2026-05-06 partial fix (wired honesty into deterministic path; did not restore LLM-Coach primacy)

### Rules
- [`.claude/rules/path-string-mismatch-is-not-dishonesty.md`](../../.claude/rules/path-string-mismatch-is-not-dishonesty.md) — Layer 1 / Layer 3' guarantees, preserved as evidence under Revision 3
- [`.claude/rules/absence-of-failure-is-not-success.md`](../../.claude/rules/absence-of-failure-is-not-success.md) — guard the LLM Coach prompt must encode (AC-009)
- [`.claude/rules/feature-build-invariants.md`](../../.claude/rules/feature-build-invariants.md) — "Coach validates, Player implements" invariant (unchanged by Revision 3)

### Code citations
- [`guardkit/orchestrator/autobuild.py:5281-5355`](../../guardkit/orchestrator/autobuild.py) — current Coach routing (the regression)
- [`guardkit/orchestrator/agent_invoker.py:1828-1947`](../../guardkit/orchestrator/agent_invoker.py) — LLM Coach SDK invocation (currently fallback; becomes primary)
- [`guardkit/orchestrator/quality_gates/coach_validator.py`](../../guardkit/orchestrator/quality_gates/coach_validator.py) — CoachValidator (refactored in Part A)
- [`guardkit/orchestrator/coach_verification.py`](../../guardkit/orchestrator/coach_verification.py) — CoachVerifier (preserved; provides honesty for evidence bundle)

## Notes

This is the largest single task in the migration after Revision 3. At ~12h
it consumes most of the slack recovered by Revisions 1 and 2 (47h Revision-1
slack → 33h Revision-3 slack). The trade-off is intentional: the cutover
delivers the architecture the operator wants (Block adversarial-cooperation),
not the regression my v1/v2 plan was inadvertently preserving.

The emergency-revert (`GUARDKIT_COACH_LEGACY=1`) is the cost-controlled
de-risking mechanism. If the LLM Coach proves too lenient in Wave 3 canary
(TASK-HMIG-009), the env var flip falls back to deterministic-primary
without code changes.

---

## v1/v2 task definition preserved for audit

The original (v1/v2) TASK-HMIG-008 was a narrower 4h scope. Preserved here:

> **Title**: Wire CoachVerifier honesty Layer 1 identity-bounded resolution into the LangGraph Coach path
>
> **Description**: The LangGraph Coach path must implement the same identity-bounded honesty resolution that the deterministic SDK Coach got in TASK-FIX-1B4A + TASK-FIX-1B4C (2026-05-06). Without this, the migration inherits Pattern 3 (`honesty-verification-false-fail`) at full severity.
>
> The v1/v2 task assumed the deterministic CoachValidator was the correct primary path and only wired honesty Layer 1 into it. Revision 3 inverts that assumption — Layer 1 is *preserved* (now as evidence on `CoachEvidenceBundle.honesty.resolved_paths`) but the deterministic CoachValidator is no longer the primary decision-maker.

If the operator changes their mind and wants the minimal v1/v2 scope (no LLM-Coach-primary restoration, just honesty wiring), see §14.9.6 in the main review report for the revert path.
