---
id: TASK-FIX-RWOP1.2
title: Fold /feature-plan Step 10.6 (BDD oracle nudge) + Step 10.7 (smoke-gates nudge) into generate_feature_yaml.py — TASK-FIX-3C9D pattern
status: completed
task_type: implementation
created: 2026-04-22T00:00:00Z
updated: 2026-04-22T00:00:00Z
completed: 2026-04-22T00:00:00Z
previous_state: in_review
state_transition_reason: "task-complete: 6/6 AC met, 34/34 tests green, verification transcript captured"
priority: high
complexity: 3
tags: [runner-without-producer, bdd-oracle-nudge, smoke-gates-nudge, feature-plan, r2, r3, cohort-blocker, rwop1]
parent_review: TASK-REV-RWOP1
related_to: TASK-REV-RWOP1
related_tasks:
  - TASK-REV-RWOP1
  - TASK-FIX-3C9D
  - TASK-FIX-RWOP1.1
  - TASK-FP-NDG1
  - TASK-FP-NDG2
  - TASK-COH-RUN1
feature_id: FEAT-R2GP
implementation_mode: task-work
wave: 4
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-22T00:00:00Z
  suites:
    - name: tests/unit/commands/test_bdd_oracle_nudge.py
      passed: 10
    - name: tests/unit/commands/test_smoke_gates_nudge.py
      passed: 14
    - name: tests/integration/feature_plan/test_generate_feature_yaml_linter.py
      passed: 4
    - name: tests/integration/feature_plan/test_generate_feature_yaml_nudges.py
      passed: 6
verification_transcript: .claude/reviews/TASK-FIX-RWOP1.2-nudges-verification.md
---

# Task: Fold Step 10.6 + 10.7 nudges into generate_feature_yaml.py — TASK-FIX-3C9D pattern

## Problem Statement

[TASK-REV-RWOP1](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
Findings #2 and #3 identified that **Step 10.6 (BDD oracle activation
nudge) and Step 10.7 (R3 smoke-gates activation nudge) of
[installer/core/commands/feature-plan.md](../../../installer/core/commands/feature-plan.md)**
are exact twins of the R1 runner-without-producer orphan that
TASK-FIX-3C9D remediated:

| Step | Producer helper | Caller found | Test coverage |
|---|---|---|---|
| 10.6 | `installer/core/commands/lib/bdd_oracle_nudge.py:check_bdd_oracle_activation` | **zero non-test callers** | 10+ tests in `tests/unit/commands/test_bdd_oracle_nudge.py` (all green) |
| 10.7 | `installer/core/commands/lib/smoke_gates_nudge.py:check_smoke_gates_activation` | **zero non-test callers** | 14 tests in `tests/unit/commands/test_smoke_gates_nudge.py` (all green) |

Both helpers are unit-tested to prove the banner fires under the
right conditions. Neither is invoked from any production Python file.
The spec prose instructs Claude to "call
`check_bdd_oracle_activation(project_root, quiet=...)` after Step
10.5 and print the notice verbatim" — but `/feature-plan` is a
slash-command, not a Python runtime.

Both nudges are cohort-adjacent: Step 10.6 is the fallback signal
that TASK-FIX-RWOP1.1's Step 11 linking worked (if scenarios are
tagged, the banner is quiet; if scenarios lack tags, the banner
warns). Step 10.7 is the same signal for R3 smoke-gate configuration.
With both silent, cohort users have no visible indication that R2/R3
are configured or activated.

This task blocks [TASK-COH-RUN1](TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md).

## Scope

### In-Scope

Apply the TASK-FIX-3C9D pattern exactly: fold both imperative calls
into the existing producer script
[installer/core/commands/lib/generate_feature_yaml.py](../../../installer/core/commands/lib/generate_feature_yaml.py),
immediately after the existing AC-linter invocation at lines
710-713. This is mechanically ~10 lines of code.

1. In `generate_feature_yaml.py` `main()`, after the existing
   `format_warning_summary(warnings)` print block, add:
   ```python
   # R2 BDD oracle activation nudge (TASK-FIX-RWOP1.2)
   if not args.quiet:
       from installer.core.commands.lib.bdd_oracle_nudge import (
           check_bdd_oracle_activation,
       )
       bdd_oracle_notice = check_bdd_oracle_activation(
           project_root=Path.cwd(),
           quiet=args.quiet,
       )
       if bdd_oracle_notice:
           print(bdd_oracle_notice)

   # R3 smoke-gates activation nudge (TASK-FIX-RWOP1.2)
   if not args.quiet:
       from installer.core.commands.lib.smoke_gates_nudge import (
           check_smoke_gates_activation,
       )
       smoke_gates_notice = check_smoke_gates_activation(
           feature_yaml_path=output_path,
           quiet=args.quiet,
       )
       if smoke_gates_notice:
           print(smoke_gates_notice)
   ```
   (Adjust parameter names and return-type handling to match the
   actual signatures in `bdd_oracle_nudge.py` and
   `smoke_gates_nudge.py`; the snippet above is a template.)
2. Rewrite Step 10.6 prose in `feature-plan.md` (lines 2313-2356) to
   match the shape Step 10.5 now has: drop the "call
   `check_bdd_oracle_activation(...)`" narrative, replace with:
   *"**No separate step here.** The R2 BDD-oracle activation nudge
   fires transitively via Step 8 — see
   `installer/core/commands/lib/generate_feature_yaml.py` for the
   imperative callsite. Honours `--quiet` as `quiet=True`."*
3. Rewrite Step 10.7 prose in `feature-plan.md` (lines 2358-2405)
   with the same shape.
4. Update the Flag-Only and Structured execution traces in
   `feature-plan.md` (around lines 2424 and 2478-2481) to note that
   Step 8's script **also** runs the R2 nudge (Step 10.6) and R3
   nudge (Step 10.7) transitively — same sentence pattern used for
   Step 10.5 post-TASK-FIX-3C9D.
5. Add an end-to-end test at
   `tests/integration/feature_plan/test_generate_feature_yaml_nudges.py`
   that drives `generate_feature_yaml.py` via subprocess against a
   fixture workspace with (a) `.feature` files missing `@task:` tags
   and (b) a feature YAML missing `smoke_gates:`, and asserts both
   nudge banners appear in stdout. Also confirm both banners are
   suppressed in `--quiet` mode.

### Out-of-Scope

- Changes to the internal logic of `check_bdd_oracle_activation` or
  `check_smoke_gates_activation` (they work; they just need a caller).
- The upstream/downstream orphan in Step 11 — that's
  [TASK-FIX-RWOP1.1](TASK-FIX-RWOP1.1-wire-feature-plan-step-11-bdd-linking.md).
- Retroactive nudge-wiring in cohort features (forge, study-tutor) —
  that's TASK-COH-RUN1's pre-flight.
- Unit-test rewrites — the 24 existing unit tests remain valid.

## Acceptance Criteria

- [ ] `check_bdd_oracle_activation` has at least one non-test
      caller — verifiable with
      `grep -rn "check_bdd_oracle_activation\|check_smoke_gates_activation" --include="*.py" | grep -v "test_\|/tests/\|bdd_oracle_nudge.py:\|smoke_gates_nudge.py:"`
      returning **two** non-test matches (one for each helper) inside
      `installer/core/commands/lib/generate_feature_yaml.py`.
- [ ] Step 10.6 and Step 10.7 prose in `feature-plan.md` is rewritten
      to the "runs transitively via Step 8" pattern, with the original
      implementation guidance and prose preserved as documentation of
      what the script does. Match the exact tone/shape Step 10.5 uses
      post-TASK-FIX-3C9D.
- [ ] Both Flag-Only and Structured execution traces in
      `feature-plan.md` explicitly name Steps 10.6 and 10.7 inside
      Step 8's block ("Script transitively runs the BDD-oracle nudge
      (Step 10.6) and smoke-gates nudge (Step 10.7): prints banners
      to stdout in non-quiet mode (warn-only, non-blocking)").
- [ ] Dynamic verification: run the new E2E test +
      `/feature-plan` (or equivalent) against a fixture workspace
      missing `@task:` tags AND `smoke_gates:` and confirm both
      banners appear in captured stdout. Capture the transcript at
      `.claude/reviews/TASK-FIX-RWOP1.2-nudges-verification.md`.
- [ ] `--quiet` flag suppresses both banners (verified via E2E test).
- [ ] Existing 24 unit tests still green (`test_bdd_oracle_nudge.py`,
      `test_smoke_gates_nudge.py`).

## Implementation Notes

- This is deliberately scoped as a single task because the two
  nudges are mechanically identical twins and mutually-backstopping.
  Splitting them would double the ceremony for zero design benefit.
- The code sketch above imports inside the `if not args.quiet:` block
  to keep the import graph shallow. Adjust to match the rest of
  `generate_feature_yaml.py` style (which does top-of-file imports
  with `try: ... except ImportError: _NUDGE_AVAILABLE = False`
  pattern for the AC linter — copy that shape if preferred).
- The `feature_yaml_path` parameter for `check_smoke_gates_activation`
  needs to be `output_path` — the same variable the AC linter writes
  to at `generate_feature_yaml.py:700`. Make sure `output_path` is in
  scope where the nudge call lands.
- Update `bin-entries.txt`? **No** — `generate-feature-yaml` is
  already exposed by TASK-FIX-B1E4. No new bin entries needed.
- **Cohort dependency update**: after this task lands, add
  `TASK-FIX-RWOP1.2` to TASK-COH-RUN1's `depends_on` (RWOP1 review
  already notes this but the file edit is part of this task's
  closeout).

## Related

- Parent review:
  [docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md](../../../docs/reviews/TASK-REV-RWOP1-runner-without-producer-orphan-sweep.md)
  §Findings #2 and #3
- Canonical fix shape (R1 precedent):
  [tasks/completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md](../../completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md)
- Upstream orphan (Step 11 tagging) — must land alongside:
  [TASK-FIX-RWOP1.1-wire-feature-plan-step-11-bdd-linking.md](TASK-FIX-RWOP1.1-wire-feature-plan-step-11-bdd-linking.md)
- Cohort run gated on this:
  [TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md](TASK-COH-RUN1-forge-and-study-tutor-cohort-run.md)
- Nudge helper delivery:
  [tasks/completed/TASK-FP-NDG1/TASK-FP-NDG1.md](../../completed/TASK-FP-NDG1/TASK-FP-NDG1.md) (R2 nudge)
  and TASK-FP-NDG2 (R3 nudge, most recent commit)
- Design-rule candidate (Graphiti): *"runner without producer
  anti-pattern"* — uuid
  `184731b0-3cb6-4eb2-a310-883421767dbf`
