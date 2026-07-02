# BDD pending is not failed; the oracle is three-state

> **Source**: Seeded by TASK-BDD-E8954 (2026-04-21, commit `0a5201083`) —
> "BDD oracle wiring: task-work reads task-level `features/*.feature` and writes
> `bdd_results`". Pair with the Graphiti design-rule node *"three-state BDD
> outcome model (passed/failed/pending)"* under `guardkit__project_decisions`.
> A member of the low-fidelity-oracle meta-frame family alongside
> [`absence-of-failure-is-not-success.md`](absence-of-failure-is-not-success.md):
> a `pending` scenario is an **absent** verdict (no step ran), and reading it as
> a `failed` verdict is the false-red direction of that frame.

## The rule

The task-level BDD oracle
(`guardkit.orchestrator.quality_gates.bdd_runner.BDDResult`) reports **three**
outcome states — `scenarios_passed`, `scenarios_failed`, `scenarios_pending` —
and **MUST NOT collapse `pending` into `failed`.**

- **`passed`** — a step ran and its assertion succeeded. Counts toward approval.
- **`failed`** — a step ran and its assertion **failed**. A real Coach-blocking
  bug.
- **`pending`** — the scenario exists in the `.feature` file but its step
  definition is **not yet implemented** (pytest-bdd raises
  `StepDefinitionNotFoundError`). A scaffolding state, **not** a regression.

The Coach approval rule is `bdd_results.scenarios_failed == 0` — **pending is
tolerated.** Pending scenarios still surface in Coach feedback as actionable
`should_fix` work ("implement step X"), just without the red-X treatment that
would reject the turn.

## Why this rule exists

`/feature-spec` commonly ships `.feature` scaffolding *before* the step
definitions are wired up. pytest-bdd surfaces those unwired scenarios as
`StepDefinitionNotFoundError`. If the Coach treated that as a failure, the very
first autobuild run after `/feature-spec` scaffolding would look like "BDD broke
the build" when nothing of the sort happened — the artefact simply exists ahead
of its glue code. A two-state (pass/fail) oracle cannot express "this scenario
was authored but nobody has implemented it yet," so it would falsely reject a
converging task.

The three-state model is load-bearing in three confirmed places:

1. **The counters** — `BDDResult` carries all three as distinct fields
   ([`bdd_runner.py:150-152`](../../guardkit/orchestrator/quality_gates/bdd_runner.py#L150),
   `scenarios_passed` / `scenarios_failed` / `scenarios_pending`), with
   per-scenario detail in `failures: List[FailureDetail]` and
   `pending: List[PendingDetail]`.

2. **The discriminator** — pending is classified text-based on the
   `StepDefinitionNotFoundError` marker
   (`_PENDING_MARKERS`, [`bdd_runner.py:46-49`](../../guardkit/orchestrator/quality_gates/bdd_runner.py#L46)).
   In `parse_junit_xml`
   ([`bdd_runner.py:393`](../../guardkit/orchestrator/quality_gates/bdd_runner.py#L393)),
   a `<testcase>` whose failure message matches the marker is appended to
   `pending`, everything else to `failures` — so an unwired step is never
   counted as a failure.

3. **The gate** — `CoachValidator._check_bdd_results`
   ([`coach_validator.py:7335`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L7335))
   returns a `(blocking, non_blocking)` pair: `scenarios_failed > 0` becomes a
   `must_fix` / `bdd_failure` blocking issue
   ([`:7372`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L7372)),
   while `scenarios_pending > 0` becomes a `should_fix` / `bdd_pending`
   **non-blocking** informational issue
   ([`:7424`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L7424)).
   In `validate()`
   ([`coach_validator.py:2481-2500`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L2481)),
   only `bdd_blocking` rejects the turn; `bdd_non_blocking` (the pending list)
   rides along on the approval path via `all_issues`
   ([`:2542`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L2542)),
   so a pending-only run is approved **with** feedback.

Activation is by artefact presence, not a frontmatter flag: `run_bdd_for_task`
returns `None` (legitimate silent skip) when no `features/*.feature` file carries
the `@task:<TASK-ID>` tag
([`bdd_runner.py:641`, `:674-680`](../../guardkit/orchestrator/quality_gates/bdd_runner.py#L641)),
and the gate is inert when `bdd_results` is absent
([`coach_validator.py:7358-7360`](../../guardkit/orchestrator/quality_gates/coach_validator.py#L7358)).
(Note the *inverse* guard: when tagged feature files DO exist but pytest-bdd is
not importable, the runner synthesises `scenarios_failed=1` rather than skip, so
the `scenarios_failed == 0` rule is never vacuously true — the
`absence-of-failure` precondition applied the other way.)

## Symptom

- The first autobuild turn after `/feature-spec` scaffolding rejects with a BDD
  failure even though no assertion actually failed — the "failure" is really a
  missing step definition (`StepDefinitionNotFoundError`).
- A `.feature` scenario with no implemented step is counted under
  `scenarios_failed` instead of `scenarios_pending`, and the Coach red-X's a
  converging task on scaffolding that is expected to exist ahead of its glue.

## Detection recipe

```bash
# 1. The three distinct counters must exist on BDDResult (never two).
rg -n "scenarios_passed: int|scenarios_failed: int|scenarios_pending: int" \
   guardkit/orchestrator/quality_gates/bdd_runner.py

# 2. The pending-vs-failed discriminator (the marker that prevents the collapse).
rg -n "_PENDING_MARKERS|StepDefinitionNotFoundError" \
   guardkit/orchestrator/quality_gates/bdd_runner.py

# 3. The Coach gate must split blocking (failed) from non-blocking (pending).
rg -n "def _check_bdd_results|scenarios_failed > 0|scenarios_pending > 0" \
   guardkit/orchestrator/quality_gates/coach_validator.py

# 4. In validate(), only bdd_blocking rejects; bdd_non_blocking rides the
#    approval path.
rg -n "bdd_blocking, bdd_non_blocking|if bdd_blocking:|bdd_non_blocking" \
   guardkit/orchestrator/quality_gates/coach_validator.py
```

## Remediation

1. **Keep three counters.** Any parser or reconciler that reduces the BDD
   outcome to a single pass/fail boolean, or that adds `pending` into `failed`,
   re-introduces the false-red. Preserve `scenarios_pending` as its own field
   through every layer that carries `bdd_results`.
2. **Classify by the marker, not by "has a `<failure>` node".** A
   `StepDefinitionNotFoundError` (or the older `"Step definition is not found"`
   prose) is pending; anything else with a failure/error node is a real failure.
   See `_classify_failure_text` / `_PENDING_MARKERS`.
3. **Gate on `scenarios_failed == 0` only.** Pending must never flip the Coach
   decision to feedback on its own; surface it as `should_fix` / `bdd_pending`
   so the Player still sees "implement step X" without a rejected turn.
4. **Guard the vacuous-true edge.** "No result" is not "zero failures." When
   tagged feature files exist but the oracle cannot run (pytest-bdd absent,
   runner error), synthesise a failure rather than return an empty/absent result
   that `scenarios_failed == 0` would silently approve.

## Grep-able signature (for next agent)

```bash
# Three-state fingerprint (MUST MATCH — collapsing to two is the regression):
rg -n "scenarios_passed: int|scenarios_failed: int|scenarios_pending: int" \
   guardkit/orchestrator/quality_gates/bdd_runner.py         # -> 150,151,152

# Non-blocking-pending fingerprint (MUST MATCH):
rg -n "\"category\": \"bdd_pending\"|scenarios_pending > 0" \
   guardkit/orchestrator/quality_gates/coach_validator.py    # -> 7424, 7436

# Only-failed-rejects fingerprint (MUST MATCH):
rg -n "if bdd_blocking:" guardkit/orchestrator/quality_gates/coach_validator.py  # -> 2482

# Regression reproducers:
rg -n "test_pending_step_recorded_distinctly|test_bdd_pending_approves_with_feedback|test_bdd_failure_rejects" \
   tests/unit/orchestrator/quality_gates/

# Sibling-rule lookup:
rg "bdd-pending-is-not-failed|absence-of-failure" .claude/rules/
```

## When this rule triggers

- Before modifying `bdd_runner.py` (`BDDResult`, `parse_junit_xml`,
  `_classify_failure_text`, `_PENDING_MARKERS`) or the BDD gate
  (`CoachValidator._check_bdd_results` / `validate()` BDD block).
- Before adding a non-Python BDD stack (cucumber-js, reqnroll) — the new
  runner must produce the same three-state model and its own pending
  discriminator (per `stack-plugin-architecture.md`), never a two-state
  pass/fail.
- Before adding any reconciliation/serialization layer that carries
  `bdd_results` — `scenarios_pending` must survive it distinctly (the shape of
  [`absence-must-survive-every-reconciliation-layer.md`](absence-must-survive-every-reconciliation-layer.md)).
- During any diagnostic session investigating "BDD broke the build" on a task's
  first run after `/feature-spec` scaffolding.

## What this rule does NOT cover

- **Feature-level (whole-`.feature`, cross-task) BDD.** This runner is
  task-scoped to `@task:<TASK-ID>`-tagged scenarios only; whole-feature smoke is
  TASK-SMK-F703A territory (see also
  [`bdd-per-task-glue.md`](bdd-per-task-glue.md) for per-task glue naming).
- **A genuinely-failed scenario** (`scenarios_failed > 0`). A real assertion
  failure still blocks approval — this rule is permissive only for `pending`.
- **The absent-input case** (no tagged `.feature`). That is a legitimate silent
  skip (`run_bdd_for_task` → `None`); the gate is simply inactive, not
  approving-on-absence.
- **The pytest-bdd-not-importable / runner-error case.** Those synthesise a
  `scenarios_failed=1` blocker on purpose (TASK-FIX-BDDM-1 / F584) so the gate
  cannot be vacuously satisfied — the opposite direction from pending tolerance.
