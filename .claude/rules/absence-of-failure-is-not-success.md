# Absence of failure is not success

> **Source**: Seeded by TASK-AB-FIX-INVAB1 (2026-05-06). Pair with the Graphiti
> design-rule node *"absence-of-failure-is-not-success"* under
> `guardkit__project_decisions`.

## The rule

A Coach gate that interprets a self-reported zero-cardinality oracle result
as a passing verdict, instead of as an absent verdict, is a false-green
generator. When the count of failures is zero **and** the count of attempts
is also zero, "did not fail" is not the same as "passed".

The rule applies to **any** boolean approval gate downstream of a self-reported
counter. Three known instances are documented below; future incidents that
match the same shape should be folded under this rule rather than retried as
ad-hoc fixes.

## Why this rule exists

The class-of-defect recurs:

1. **2026-04-22** — `parse_junit_xml` zero-result false-green
   ([Graphiti uuid `ccd870c5`]). When the JUnit XML produced
   `tests=0, failures=0`, the Coach's `tests_failed == 0` rule fired
   `decision: approve`. The fix added a `tests_run > 0` precondition.

2. **2026-04-22** — BDD-oracle `scenarios_failed == 0` false-green
   ([Graphiti uuids `61164740`, `8f48b537`]). When pytest-bdd skipped a
   scenario whose `Given/When/Then` matched no step definitions,
   `scenarios_failed: 0` reported alongside `scenarios_run: 0`. The Coach
   read `0 failed` and approved. Fix: require `scenarios_run > 0` before
   honouring a green BDD verdict.

3. **2026-05-06 (this defect)** — Player-written `status: "complete"` in
   `completion_promises[*]` was trusted without disk verification because
   the deterministic Coach path (`CoachValidator`) bypassed `CoachVerifier`
   entirely (Option D — TASK-REV-0414, 2025-12-30). Filed as TASK-INV-AB1;
   fix in TASK-AB-FIX-INVAB1.

The unifying observation across all three: a "lightweight" / "deterministic"
validator path was added in parallel to an LLM-with-tools verification path,
and the lightweight path silently dropped the verification step. From
outside, both paths look like they enforce the same contract; from inside,
the lightweight path interprets *absence of evidence* as *evidence of
absence of failure*, which is the false-green generator.

## Symptom

- A Coach gate fires `decision: approve` on a turn where:
  - The relevant counter is zero (`tests_failed: 0`, `scenarios_failed: 0`,
    `discrepancies: []`).
  - The corresponding "ran" / "verified" counter is also zero or missing
    (`tests_run: 0`, `scenarios_run: 0`, no `CoachVerifier` invocation).
- Downstream consumers (Player feedback, completed-task archival,
  feature-build merge eligibility) see "passed" and proceed.
- Manual disk inspection later reveals the AC was not delivered.

## Detection recipe

```bash
# 1. Grep the Coach gate sources for boolean comparisons against zero.
rg "== 0|== False|is False|not\s+\w+" guardkit/orchestrator/quality_gates/

# 2. For each match, find the producer of the operand. If it's a
#    Player-self-reported counter (loaded from task_work_results.json),
#    flag for review.
rg "task_work_results\.get\(" guardkit/orchestrator/quality_gates/

# 3. For each producer, check whether a matching "ran" / "verified"
#    counter is asserted alongside.

# 4. Cross-check against existing instances of this rule:
rg "absence_of_failure" guardkit/

# 5. For honesty wiring specifically, verify that CoachVerifier
#    or its equivalent runs unconditionally on the primary path.
rg "CoachVerifier\b" guardkit/orchestrator/quality_gates/
```

## Remediation recipe

1. **Pair every `count_failed == 0` rule with `count_attempted > 0`**.
   Refuse to approve when the attempted-count is zero or absent. Surface
   "no oracle ran" as a feedback issue, not silent approval.
2. **Wire the existence verifier into the primary Coach path**, not just
   the LLM-Coach fallback. If the verifier exists in the codebase but
   isn't called by the path that actually runs, that's the bug.
3. **Verify on disk, not on Player report**. When the Player claims a
   file exists / a test ran / a scenario passed, re-check against the
   filesystem before honouring the claim. `Path.exists()` is cheap; an
   undetected false-green is expensive.
4. **Test the zero-cardinality case explicitly**. Every gate that reads
   a counter from `task_work_results` should have a regression test
   exercising the zero-and-also-zero case.
5. **Document the new gate's `category`** so consumer-side dashboards
   and stall classifiers can surface it. The honesty gate emits
   `category: "honesty"` (TASK-AB-FIX-INVAB1 AC-002).

## Grep-able signature (for next agent)

```bash
# Active-hazard fingerprint: Coach gate reading Player-self-reported counter
rg "task_work_results\.get\(" guardkit/orchestrator/quality_gates/coach_validator.py

# Verification-was-skipped fingerprint
rg "CoachVerifier|honesty_verification" guardkit/orchestrator/quality_gates/

# Sibling-rule lookup (this rule)
rg "absence-of-failure" .claude/rules/
```

## Meta-frame

This rule and its inverse-shape sibling
[`path-string-mismatch-is-not-dishonesty.md`](path-string-mismatch-is-not-dishonesty.md)
are both instances of the same broader meta-frame: *a binary verdict
from a low-fidelity oracle that cannot distinguish "no signal" from
"positive/negative signal"*. This rule guards against the false-green
direction (oracle reports zero failures because it ran zero attempts;
gate approves). The sibling guards against the false-red direction
(oracle reports a path miss because the orchestrator mutated the
worktree, not because the Player lied; gate rejects). The shared
remediation pattern is the same: pair the boolean verdict with a
positive-evidence precondition (count of attempts > 0; identity-based
resolution before path-equality discrepancy) so "absent oracle output"
is surfaced as feedback, never silently approved or silently
turn-rejecting.

## Prior art

- **Sibling rule (false-red inverse direction)**:
  [`path-string-mismatch-is-not-dishonesty.md`](path-string-mismatch-is-not-dishonesty.md)
  — same shape (symptom + detection recipe + remediation recipe + grep
  signature), opposite verdict direction. Seeded by TASK-DOC-1B4D
  (2026-05-06) after the FEAT-1B452 honesty false-fail incident
  ([TASK-REV-1B452](../reviews/TASK-REV-1B452-review-report.md)).
  Paired in Graphiti via `IS_INVERSE_SHAPE_OF` edge.
- **Sibling rule (meta-class peer)**:
  [`namespace-hygiene.md`](namespace-hygiene.md) — same shape
  (symptom + detection recipe + remediation recipe + grep signature).
  Same meta-class-of-defect (local decisions touching externally-defined
  contracts: PyPI namespaces vs. honesty contracts).
- **Sibling rule (collection-boundary instance)**:
  [`evidence-boundary-narrower-than-write-surface.md`](evidence-boundary-narrower-than-write-surface.md)
  — same meta-frame, but the spurious "no signal" comes from the oracle's
  spatial *collection* aperture being narrower than the task's write surface
  (a declared sibling repo), not from interpreting a present signal. Seeded by
  TASK-AB-XREPOEV01 (2026-06-13); produces both a false-green and a false-red
  from the same too-narrow boundary.
- **Pair fact in Graphiti** (`guardkit__project_decisions`): node
  *"absence-of-failure-is-not-success"* with edges to the three known
  instance uuids enumerated above, and an `IS_INVERSE_SHAPE_OF` edge
  to the *"path-string-mismatch-is-not-dishonesty"* node.
- **Architectural review report**: `.claude/reviews/TASK-INV-AB1-review-report.md`
  contains the C4 component diagram and four sequence diagrams that
  motivate this rule.
- **Origin decision**: `.claude/reviews/TASK-REV-0414-review-report.md`
  documents the Option D delegation pattern that introduced
  `CoachValidator` as a parallel "lightweight" Coach. The original
  report's claim *"Maintains adversarial rigor (Coach still validates
  independently)"* was delivered only when `CoachVerifier` was wired
  into the deterministic path. See AC-014 addendum.

## When this rule triggers

- Before introducing a new Coach gate that reads a Player-self-reported
  counter.
- Before adding a new "lightweight" / "deterministic" validator that
  parallels an LLM-with-tools path.
- During Phase 2.5 architectural review for any task that touches
  `coach_validator.py`, `coach_verification.py`, or `agent_invoker.py`.
- During any diagnostic session investigating a "Coach approved but the
  AC wasn't delivered" report.

## What the rule does NOT cover

- Cases where the Player legitimately reports zero counts because zero
  attempts were appropriate (e.g. a documentation-only task with
  `tests_run: 0, tests_failed: 0`). The pair-with-attempted-count
  remediation is permissive in this case: gate reports "no oracle ran",
  Coach approves on other gates if appropriate.
- Coach-side hallucinations of evidence (the LLM Coach inventing a
  passing verdict despite seeing failure context). That is a different
  meta-defect and is not in scope here.
- Tests that would fail to capture "no oracle ran" because the test
  fixture itself doesn't simulate zero-cardinality. Test fixtures must
  exercise the absent-oracle case explicitly.
