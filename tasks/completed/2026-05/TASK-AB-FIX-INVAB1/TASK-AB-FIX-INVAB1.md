---
id: TASK-AB-FIX-INVAB1
title: "Restore adversarial honesty verification on the deterministic Coach path (wire CoachVerifier into CoachValidator)"
status: completed
created: 2026-05-06T00:00:00Z
updated: 2026-05-06T16:30:00Z
completed: 2026-05-06T16:30:00Z
completed_location: tasks/completed/2026-05/TASK-AB-FIX-INVAB1/
previous_state: in_review
state_transition_reason: "All quality gates passed; ready to commit"
priority: critical
tags: [autobuild, coach-validator, coach-verifier, quality-gate, false-positive-approval, architectural-regression]
task_type: feature
complexity: 4
estimated_minutes: 240
parent_review: TASK-INV-AB1
test_results:
  status: passed
  coverage: null
  last_run: 2026-05-06T16:00:00Z
  passed: 601
  failed: 0
  notes: "601 tests passing across tests/unit/test_coach_validator.py, tests/unit/test_coach_verification.py, tests/unit/test_coach_verification_promises.py, tests/unit/test_synthetic_report.py, tests/unit/orchestrator/, tests/integration/orchestrator/. Pre-existing failure in test_invoke_task_work_implement_mode_passed unrelated to this task."
---

# Task: Restore adversarial honesty verification on the deterministic Coach path

## Provenance

This task was filed from the investigation **TASK-INV-AB1**
(`Investigate autobuild approving zero-implementation turns`). Full
analysis with C4 component diagram and 4 sequence diagrams (including
the architectural-history of how the adversarial property was lost) is
in
[`.claude/reviews/TASK-INV-AB1-review-report.md`](../../.claude/reviews/TASK-INV-AB1-review-report.md).
**Read that report first** — the patch points below assume its findings.

This is the **second revision** of this task after the user noted that
the original Player–Coach adversarial design appears to have been
broken. The investigation confirmed this: the adversarial honesty
verifier (`CoachVerifier`) exists in the codebase and is wired to the
LLM Coach, but Option D (TASK-REV-0414, 2025-12-30) introduced a
parallel deterministic Coach path (`CoachValidator`) that became the
primary path and **silently bypasses honesty verification entirely**.
This is the architectural regression. The user’s expectation that
*“the Coach would have rejected this”* is the **original documented
design**; the fix is to **restore that design on the path that
actually runs**.

## Problem statement

The codebase contains a fully-implemented adversarial honesty
verifier — `CoachVerifier` at
[`guardkit/orchestrator/coach_verification.py:104-285`](../../guardkit/orchestrator/coach_verification.py)
— with three checks:

- `_verify_test_results`: re-run pytest, compare against Player claim
- `_verify_files_exist`: assert `Path(f).exists()` for each Player-claimed file
- `_verify_test_count`: extract count from summary, compare to actual

This verifier is wired only into the LLM Coach fallback path
(`agent_invoker.invoke_coach:1635`). The primary Coach path
(`CoachValidator` at
[`guardkit/orchestrator/quality_gates/coach_validator.py`](../../guardkit/orchestrator/quality_gates/coach_validator.py))
does **not** import or call `CoachVerifier`:

```bash
$ grep -c "CoachVerifier\|_verify_player_claims\|HonestyVerification" \
    guardkit/orchestrator/quality_gates/coach_validator.py
0
```

The LLM Coach is wired only as an exception fallback at
[`autobuild.py:5116`](../../guardkit/orchestrator/autobuild.py#L5116).
For every normal autobuild run — including all of FEAT-6CC5 and
FEAT-FORGE-009 — the LLM Coach (and therefore the honesty verification)
**never fires**. The Coach prompt
([`installer/core/agents/autobuild-coach.md:141-203`](../../installer/core/agents/autobuild-coach.md#L141-L203))
describes the honesty-verification protocol in detail, including
`file_existence` as a "Critical" discrepancy that must produce
`decision: feedback` — but that prompt is dead code in the deterministic
path.

This task **restores documented adversarial behaviour on the path that
actually runs**. The fix is small (~80 lines of new code in 3 files),
additive (no architecture changes), and reuses existing types
(`Discrepancy`, `HonestyVerification`).

## Acceptance criteria

### Primary fix (architectural restoration)

- [ ] **AC-001 — Extend `CoachVerifier` to verify completion_promises**:
  Add a new method
  `CoachVerifier._verify_completion_promises_files_exist` in
  `guardkit/orchestrator/coach_verification.py` that:

  ```python
  def _verify_completion_promises_files_exist(
      self, report: Dict[str, Any]
  ) -> List[Discrepancy]:
      """Verify that files claimed in completion_promises[*].implementation_files
      actually exist on disk.

      Catches FEAT-6CC5-class sophisticated dishonesty: Player keeps
      files_created/files_modified honest (containing only metadata that
      does exist) but lies in completion_promises[*].status='complete'
      with implementation_files referencing source files that don't
      exist.
      """
      discrepancies: List[Discrepancy] = []
      for promise in report.get("completion_promises", []) or []:
          if promise.get("status") != "complete":
              continue
          for impl_file in (promise.get("implementation_files") or []):
              if not (self.worktree_path / impl_file).exists():
                  discrepancies.append(
                      Discrepancy(
                          claim_type="promise_file_existence",
                          player_claim=(
                              f"completion_promises[{promise.get('criterion_id', '?')}]"
                              f".status=complete with implementation_files including {impl_file}"
                          ),
                          actual_value=f"File does not exist at {impl_file}",
                          severity="critical",
                      )
                  )
      return discrepancies
  ```

  Wire it into the existing `verify_player_report` method, immediately
  after `_verify_files_exist`, so that the new check participates in
  the existing honesty score calculation. Update the
  `_count_verifiable_claims` helper to include the new claim category
  for accurate score arithmetic.

- [ ] **AC-002 — Wire `CoachVerifier` into `CoachValidator`**:
  In `guardkit/orchestrator/quality_gates/coach_validator.py`, in
  `CoachValidator.validate(...)`, immediately after the player_report
  is loaded and before quality_gates evaluation, invoke `CoachVerifier`
  and short-circuit on critical discrepancies:

  ```python
  # Restore adversarial honesty verification (was bypassed by Option D
  # — see TASK-INV-AB1 / TASK-AB-FIX-INVAB1 for context).
  from guardkit.orchestrator.coach_verification import CoachVerifier
  verifier = CoachVerifier(self.worktree_path)
  honesty = verifier.verify_player_report(player_report)

  honesty_issues = []
  for d in honesty.discrepancies:
      if d.severity == "critical":
          honesty_issues.append({
              "severity": "must_fix",
              "category": "honesty",
              "description": (
                  f"Honesty verification failed: Player claim disagrees "
                  f"with worktree state. Claim: {d.player_claim}. "
                  f"Actual: {d.actual_value}."
              ),
              "details": {
                  "claim_type": d.claim_type,
                  "player_claim": d.player_claim,
                  "actual_value": d.actual_value,
              },
          })

  if honesty_issues:
      return CoachValidationResult(
          task_id=task_id,
          turn=turn,
          decision="feedback",
          quality_gates=None,
          independent_tests=None,
          requirements=None,
          issues=honesty_issues,
          rationale=(
              f"{len(honesty_issues)} honesty discrepancy/discrepancies. "
              f"Adversarial verification overrode gate evaluation."
          ),
          context_used=context_prompt if context_prompt else None,
      )

  # Otherwise proceed with existing gate evaluation...
  ```

  This places the honesty check **before** any gate evaluation — when
  Player claims disagree with disk state, gates are not consulted at
  all. Player feedback is specific (cites which claim disagreed with
  which actual value) so the next turn can correct course.

- [ ] **AC-003 — Inject honesty score into Coach JSON output**:
  Update `CoachValidationResult.to_dict()` in `coach_validator.py:326`
  to include a `honesty_verification` field with `verified`,
  `honesty_score`, and `discrepancy_count` (mirroring the LLM Coach
  output schema documented in autobuild-coach.md:165-184). This makes
  the honesty verification observable in the per-turn JSON artefact
  for debugging and audit.

### Defence-in-depth fixes (small, additive)

- [ ] **AC-004 — Tighten `_hybrid_fallback`**:
  In
  `guardkit/orchestrator/quality_gates/coach_validator.py:3421-3433`,
  remove the `or "Promise status: incomplete" in promise_cr.evidence`
  clause from the upgrade condition. After AC-001/002 land, an
  `incomplete` promise status reflects the deterministic verifier’s
  ground truth, and text-fallback against Player-self-reported
  `requirements_addressed` must not be allowed to overrule it.

  Keep the `"No completion promise"` branch (handles legitimate
  missing-promise edge cases per TASK-REV-E719) but tighten it: text
  fallback may only verify a criterion if the
  `requirements_addressed` text either does not name a literal file
  path, *or* names a file path that exists on disk under
  `worktree_path`.

- [ ] **AC-005 — Plan-audit `skipped` escalation**:
  In `guardkit/orchestrator/agent_invoker.py:6038-6049`, when
  `result.get("skipped")` is true, scan acceptance criteria for the
  same regex pattern `synthetic_report.py:266` uses
  (`r'[\w./\-]+\.\w{1,5}'`) plus backtick/quoted variants. For any
  matched path that does not exist under `worktree_path`, return
  `status: "violation"`, `severity: "high"`, `violations: <count>`,
  `missing_files: [<paths>]`. The existing
  `coach_validator.py:4969-5019` plan-audit gate emits feedback on
  `severity == "high"` automatically — no further wiring needed.

- [ ] **AC-006 — Independent test command honesty**:
  In `coach_validator.py` near `_detect_test_command (~3589)`, scan
  AC text for patterns matching `tests/[^\s]*\.py` (and equivalents
  per stack: `*_test.go`, `Tests/*.cs`, etc.). If any matched path
  doesn't exist on disk, emit a structured issue of severity
  `must_fix`, category `acceptance_criteria`, with description
  `"AC names test file(s) that don't exist on disk: <missing_paths>"`
  and **bypass** the existing-test-files run. Do not silently run a
  smaller test set and report green.

### Regression tests

- [ ] **AC-007 — Honesty restoration test (proves wiring is live)**:
  Add `tests/integration/orchestrator/test_coach_honesty_restoration.py`.
  Build a synthetic Player report whose `files_created` lists a path
  that doesn’t exist in the test worktree:

  ```python
  player_report = {
      "files_created": ["src/repro/never_created.py"],
      "files_modified": [],
      "tests_written": [],
      "tests_run": True,
      "tests_passed": True,
      "test_output_summary": "1 passed",
      "completion_promises": [],
      "requirements_addressed": [],
  }
  ```

  Assert: `CoachValidator.validate(...)` returns
  `decision == "feedback"` with at least one issue of category
  `"honesty"` whose `details.claim_type == "file_existence"`.

  This proves the wiring from AC-002 is live (CoachVerifier is being
  invoked from CoachValidator) and would have caught simpler dishonest
  reports.

- [ ] **AC-008 — FEAT-6CC5 reproducer test**:
  Add `tests/integration/orchestrator/test_coach_blocks_promised_missing_files.py`.
  Build a sophisticated synthetic Player report mirroring
  TASK-LCA-003 turn 3:

  ```python
  player_report = {
      "files_created": [".guardkit/autobuild/some_metadata.json"],   # exists
      "files_modified": [],
      "tests_written": [],
      "tests_run": True,
      "tests_passed": True,
      "test_output_summary": "29 passed in 0.26s",
      "completion_promises": [
          {
              "criterion_id": "AC-001",
              "criterion_text": "src/repro/missing.py exists",
              "status": "complete",
              "evidence": "Module created and tested.",
              "implementation_files": ["src/repro/missing.py"],   # MISSING
          }
      ],
      "requirements_addressed": ["AC-001 implemented"],
  }
  ```

  Pre-create only the metadata file in the test worktree, leave
  `src/repro/missing.py` absent. Assert: `CoachValidator.validate(...)`
  returns `decision == "feedback"` with at least one issue of category
  `"honesty"` whose `details.claim_type == "promise_file_existence"`
  and whose `details.player_claim` references
  `"src/repro/missing.py"`.

  This is the FEAT-6CC5 reproducer. The test must run without invoking
  the SDK (CoachValidator is deterministic Python; honesty verification
  is filesystem-only) — should complete in <100ms.

- [ ] **AC-009 — Backwards-compatibility test**:
  Add a test fixture where Player report is fully honest:
  `files_created` contains paths that all exist;
  `completion_promises[*].status="complete"` only when
  `implementation_files` are all on disk; `tests_passed` matches
  actual pytest output. Assert: `CoachValidator.validate(...)` produces
  the same result it produces today (no spurious `honesty` issues, gate
  evaluation proceeds normally).

- [ ] **AC-010 — Idempotency test**:
  Run the new merge twice on the same player_report; assert results
  are identical. The `CoachVerifier` checks are stateless except for
  the test-result cache, so this should be trivially true; the test
  documents the expectation and would catch any future regression
  introducing nondeterminism.

- [ ] **AC-011 — Hybrid-fallback regression test (AC-004)**:
  In
  `tests/unit/orchestrator/quality_gates/test_coach_validator_hybrid_fallback.py`,
  construct a `RequirementsValidation` with one criterion having
  `result="rejected"` and evidence `"Promise status: incomplete"`,
  plus a `requirements_addressed` list whose keyword overlap with the
  AC text exceeds 70%. Assert that `_hybrid_fallback` does NOT upgrade
  to verified (post-fix behaviour). Add a paired test for the
  legitimate `"No completion promise"` case with no file path in the
  AC to confirm that branch still upgrades correctly.

### Documentation + meta-rule

- [ ] **AC-012 — Add meta-rule to `.claude/rules/`**:
  Add `.claude/rules/absence-of-failure-is-not-success.md` documenting
  the meta-defect class with three known instances:
  1. parse_junit_xml zero-result false-green
     (Graphiti uuid `ccd870c5`, 2026-04-22)
  2. BDD-oracle `scenarios_failed == 0` false-green
     (Graphiti uuids `61164740`, `8f48b537`, 2026-04-22)
  3. **This defect**: Player-written `status: "complete"` trusted
     without disk verification because the deterministic Coach path
     bypasses `CoachVerifier`. Filed as TASK-INV-AB1; fix in this
     task.

  Cross-reference to a new Graphiti node seed in
  `guardkit__project_decisions`.

- [ ] **AC-013 — Document interim merge-time check**:
  Add the `task_work_results.json` verification script from
  [review report Appendix C](../../.claude/reviews/TASK-INV-AB1-review-report.md#appendix-c-verification-scripts)
  to `docs/guides/autobuild-instrumentation-guide.md` as a
  recommended pre-merge step. Cross-link from
  `.claude/rules/autobuild.md`.

- [ ] **AC-014 — Update Option D architectural justification**:
  Add a note (or follow-on ADR) acknowledging that the TASK-REV-0414
  Option D claim *"Maintains adversarial rigor (Coach still validates
  independently)"* was delivered only when `CoachVerifier` is wired
  into the deterministic path. Place the note as an addendum at the
  end of `.claude/reviews/TASK-REV-0414-review-report.md` or in a new
  short ADR cross-referenced from there. Either form is acceptable;
  the goal is that future readers of TASK-REV-0414 see the post-hoc
  caveat.

## Out of scope

- **LLM Coach prompt redesign**: prompt is correct as-is and is the
  fallback path. No changes needed.
- **task-work prompt redesign to make the Player honest**: separate
  line of work. The fix in this task makes Player honesty *not
  load-bearing* for Coach correctness — the Player can continue to
  lie; the Coach will catch it via `CoachVerifier`. Improving Player
  honesty is desirable but not required for closing this defect.
- **Removing the LLM Coach fallback entirely**: leave it; it's the
  safety net for cases where `CoachValidator` itself errors out
  (autobuild.py:5116).
- **Reconsidering Option D wholesale**: Option D's delegation pattern
  is fine. The bug is that one component (`CoachVerifier`) was left
  disconnected. Don't throw the architecture out — wire the missing
  component in.
- **Re-running FEAT-6CC5 in `study-tutor`**: handled by re-running
  `/feature-build` against the reopened TASK-LCA-001/002/003 in that
  repo separately.
- **forge `FEAT-FORGE-009` confirmed-shipped misses**: a separate
  fix-up PR in the `forge` repo. File a ticket there.
- **Forensic re-audit of every prior autobuild completion**: review
  report §11 R3 records the bounded re-audit recommendation. This
  task is the fix, not the audit.
- **Wave-contention diagnostic-quality**: not implicated; out of scope.

## Implementation notes

### Order of patches

Land AC-001 + AC-002 + AC-003 + AC-007 + AC-008 + AC-009 + AC-010
together — these are the architectural restoration. They share the
existing `Discrepancy` / `HonestyVerification` types so are mutually
consistent.

AC-004, AC-005, AC-006 are independent defence-in-depth fixes — can
land in the same PR or separate PRs. AC-011 is the test for AC-004.

AC-012, AC-013, AC-014 are documentation; can land last (or in
parallel).

### Performance impact

`CoachVerifier.verify_player_report` already runs `pytest`
independently as part of `_verify_test_results`. CoachValidator
*also* runs pytest as part of `independent_tests`. **Avoid duplicate
pytest runs**: either share a cached `TestResult` between the two, or
restructure so honesty verification reuses CoachValidator's
independent-test result. Implementation hint: pass an
`independent_test_result` dict into `verifier.verify_player_report`
so `_verify_test_results` short-circuits using the existing run.

The new `_verify_completion_promises_files_exist` is filesystem-only
(`Path.exists()` per implementation_file); typical task has ≤20
promises × ≤5 files = ≤100 stat calls; <10ms.

The wire-in itself (AC-002) is a small dispatch at the start of
`validate()`; negligible overhead.

### Regression risk assessment

**Low risk**, by construction:

- **No new architecture, no new types**: reuses existing
  `Discrepancy`, `HonestyVerification`, `CoachVerifier` classes.
- **No existing tests should break**: the honesty verifier produces
  zero discrepancies on honest Player reports; AC-009 explicitly
  verifies this with a fixture.
- **Idempotent**: AC-010 verifies this.
- **Filesystem-only new check** (AC-001): trivially deterministic; no
  flakiness risk.
- **Short-circuit semantics**: when honesty verification produces
  critical discrepancies, gate evaluation is skipped — but skipping
  an evaluation that would otherwise return `decision: approve`
  cannot newly approve anything that was previously rejected. Strictly
  stricter than current behaviour.
- **Hybrid-fallback tightening (AC-004)**: only removes a path that
  was actively producing false-greens; cannot newly reject anything
  legitimate.
- **Plan-audit and test-command fixes (AC-005, AC-006)**: only add
  stricter conditions; cannot newly approve.
- **Deliberately does NOT change any BDD oracle code paths** (user
  flagged BDD-related changes have caused pain — this task touches
  zero BDD code).

The user’s concern about regression risk is taken seriously: the fix
restores documented behaviour rather than inventing new behaviour.
Every component being modified or wired in already exists, has
documented contracts, and has Coach-prompt-level acceptance criteria
that future Player turns are already aware of.

### Don’t break

- The `"No completion promise"` upgrade branch in hybrid fallback
  (the part AC-004 does NOT remove) handles a real case where the
  Player wrote no completion_promises at all due to SDK turn
  exhaustion — TASK-REV-E719 Fix 2. Tighten that branch with the
  file-path-on-disk check; do not remove it.
- The synthetic-promise generation when Player provides no promises
  (the existing fallback path at agent_invoker.py:2916) must continue
  to work. AC-001/002 don't touch this path; it remains the
  no-Player-promises branch.
- Existing tests in `tests/integration/orchestrator/`,
  `tests/unit/orchestrator/quality_gates/`,
  `tests/unit/orchestrator/test_synthetic_report.py`,
  `tests/unit/test_coach_verification.py` (if it exists — check) must
  continue to pass. The fix adds new tests; it does not modify
  existing test expectations.

### Coordination with other in-flight tasks

- **TASK-SMK-F703A** (feature-level smoke gates between waves) is
  the *complementary* defence at the wave boundary. This task closes
  the per-task Coach defence. Both should land; neither replaces the
  other.

- **No coordination needed with BDD oracle work**. The BDD oracle
  zero-result false-green is a sibling defect (F6 in the review
  report) — known, has its own ticket, partially mitigated by AC-001
  (Player can no longer get away with lying about scenarios_failed
  while also lying about completion_promises) but not fully closed
  by this task.

## Reference data

- Investigation report: [`.claude/reviews/TASK-INV-AB1-review-report.md`](../../.claude/reviews/TASK-INV-AB1-review-report.md)
- C4 component diagram + 4 sequence diagrams: §§3-6 of the review report
- Architectural-history audit (Option D origin): §2 of the review report
- Verification scripts: Appendix C of the review report
- Suspect code:
  - `guardkit/orchestrator/coach_verification.py:104-285` (CoachVerifier — extend in AC-001)
  - `guardkit/orchestrator/quality_gates/coach_validator.py` (validate() — wire in AC-002; to_dict() — extend in AC-003; _hybrid_fallback() — tighten in AC-004; _detect_test_command() — fix in AC-006)
  - `guardkit/orchestrator/agent_invoker.py:1635, 6038-6049` (LLM Coach honesty wiring already correct; plan_audit escalation in AC-005)
- Coach prompt with documented honesty contract: [`installer/core/agents/autobuild-coach.md:141-203`](../../installer/core/agents/autobuild-coach.md)
- Option D origin: [`.claude/reviews/TASK-REV-0414-review-report.md:535-622`](../../.claude/reviews/TASK-REV-0414-review-report.md)
- Sibling rule (to seed alongside this fix in AC-012): the meta-rule
  *"absence of failure is not success"* — pair with Graphiti node in
  `guardkit__project_decisions`
- Prior instance Graphiti facts (cite in the new rule): uuids
  `61164740`, `8f48b537`, `f4058759`, `ccd870c5`

## Notes

This is a **critical** task. The architectural-regression framing
makes the priority clearer: until this lands, the Player–Coach
adversarial property — the foundational design property of AutoBuild
— is **not delivered** for any normal autobuild run. Every approval
since 2025-12-30 has been on a path that bypassed honesty verification.

**Until R1 lands**:

- Every new autobuild run should be treated as suspect.
- The interim merge-time check from AC-013 should be applied before
  any autobuild merge.
- Communicate to consumer-repo maintainers (study-tutor, forge)
  that files merged via autobuild approval may not actually exist;
  verify with `pytest --collect-only` and `git ls-tree main --
  <ac-cited paths>`.

The fix scope is **smaller** than the v1.1 draft (was: rebuild
promise-merge logic in agent_invoker; now: wire existing
CoachVerifier into existing CoachValidator + one new method on
CoachVerifier). This materially reduces regression risk, which the
user flagged as a concern from prior BDD-related changes. The fix is
**restorative** — it reconnects components that were always intended
to work together — rather than introducing new behaviour. There is
**no BDD-related code in scope** for this task.
