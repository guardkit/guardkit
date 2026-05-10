# Gate-Stack Freeze: 2026-05-11 → 2026-05-17 (inclusive)

> **Status**: ACTIVE
> **Filed by**: TASK-FREEZE-ABST
> **Originating review**: [`.claude/reviews/TASK-REV-ABST-review-report.md`](../reviews/TASK-REV-ABST-review-report.md) §8.1.1
> **End-of-window successor**: TASK-REV-ABST.1 (re-evaluates trajectory on 2026-05-17 and either lifts, holds-narrow, or escalates to Pivot)

## Window

| Field | Value |
|---|---|
| Start (inclusive) | 2026-05-11 |
| End (inclusive) | 2026-05-17 |
| Duration | 7 days |

## Why this freeze exists

TASK-REV-ABST recommended **Narrow** with a 7-day freeze on the autobuild
gate stack to give consumer repos a stable target while the May 6
(1B4A/B/C + 7E3F) and May 10 (AB-001/003/004) fixes bake. New gates landing
mid-bake would muddy the signal and make it impossible to tell whether
the existing fixes are converging or whether a new gate is masking
regressions in the existing stack.

The freeze also predicts the *shape* of any failure that surfaces during
the window: per
[`absence-of-failure-is-not-success.md`](../rules/absence-of-failure-is-not-success.md),
a single-instance "all green from a low-fidelity oracle" report during the
freeze must be treated as **absent verdict**, not validated success — the
oracle paths are deliberately not changing, so any new green from a
previously-red configuration is real signal; any new red is a candidate
escape that the existing stack didn't catch.

## Frozen paths

Any commit touching these paths during the window triggers the guard:

- `guardkit/orchestrator/agent_invoker.py`
- `guardkit/orchestrator/quality_gates/coach_validator.py`
- `guardkit/orchestrator/quality_gates/coach_verification.py`
- `guardkit/orchestrator/quality_gates/bdd_runner.py`
- `guardkit/orchestrator/quality_gates/honesty.py` *(if it exists during the window)*
- `guardkit/tasks/state_bridge.py`
- `installer/core/templates/common/features/conftest.py.template`

## Permitted-during-freeze classes

Commits in any of these classes may land without an override entry:

1. **Reverts** — commit subject begins with `revert(` or `revert:` (case-insensitive).
2. **Single-line defensive guards** on already-landed code:
   - Diff size ≤ 3 lines on the frozen path,
   - AND no new function/class/method introduced.
3. **Documentation-only changes** — touch only `*.md`, `*.rst`, `*.txt`,
   `CHANGELOG`, `README`, or `docs/**`.
4. **Test-only changes** — touch only `tests/**` or files whose names match
   `test_*.py` / `*_test.py` / `*.test.ts` / `*.spec.ts`.
5. **Out-of-scope edits** — any commit whose modified paths do *not*
   intersect the frozen list above.

## Forbidden-during-freeze classes

These require an explicit override entry in this file (see "Exception
protocol" below) before the commit may land:

1. **NEW_GATE** — any commit that introduces a new Coach gate, a new
   Player honesty contract, or a new short-circuit branch in the frozen
   paths (per the bucketing in TASK-REV-ABST §2).
2. **New behavioural surface** in the frozen paths — new function, new
   class, new method, new public symbol, or new mandate in a Player
   prompt.
3. **Re-landing a previously-reverted gate** — for example, the
   TASK-FIX-7A08 Player Task-tool mandate was reverted by TASK-REV-F4A1;
   re-landing the same shape under a new task ID still requires an
   override during the freeze.

## Exception protocol

If a forbidden-class commit must land before 2026-05-17, the operator
records a **one-line override** in the section below *before* merging the
commit. Format:

```
- YYYY-MM-DD: Override granted for TASK-XXX (reason — link)
```

The pytest guard at `tests/rules/test_gate_freeze.py` reads this section
and treats listed tasks as exempted. No override → guard fails the run.

### Granted overrides

*(none yet)*

## Operational notes

- The pytest guard is **skip-on-out-of-window**: outside `[2026-05-11,
  2026-05-17]` it short-circuits with a `pytest.skip(...)`. It only
  evaluates commits whose authored-date falls inside the window.
- The guard does **not** auto-revert offending commits. Auto-revert is a
  destructive default; the guard fails loudly so the operator decides.
- This file is **not** a YAML config. It is markdown for humans. The
  guard parses only the `## Granted overrides` section (lines beginning
  with `- ` followed by `YYYY-MM-DD`) and the frozen-paths list above.
- The CLAUDE.md pointer to this file is removed automatically by
  TASK-REV-ABST.1 on 2026-05-17 when the freeze ends.

## References

- Originating review: [`.claude/reviews/TASK-REV-ABST-review-report.md`](../reviews/TASK-REV-ABST-review-report.md) §8.1.1
- Bucketing definition (NEW_GATE / FIX_FOR_NEW_GATE / REVERT): same review §2
- Sibling rule (predicting future failure-class shapes during the freeze):
  [`.claude/rules/absence-of-failure-is-not-success.md`](../rules/absence-of-failure-is-not-success.md)
- Inverse-shape sibling: [`.claude/rules/path-string-mismatch-is-not-dishonesty.md`](../rules/path-string-mismatch-is-not-dishonesty.md)
