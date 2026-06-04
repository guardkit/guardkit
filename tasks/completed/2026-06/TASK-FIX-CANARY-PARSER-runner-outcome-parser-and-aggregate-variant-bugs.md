---
id: TASK-FIX-CANARY-PARSER
title: canary_validation_runner.py reports decision=unknown for all reps; --aggregate ignores --variant default
task_type: bug-fix
status: completed
created: 2026-06-04T05:45:00Z
updated: 2026-06-04T13:00:00Z
completed: 2026-06-04T13:00:00Z
completed_location: tasks/completed/2026-06/
previous_state: in_review
state_transition_reason: "All 5 ACs satisfied; falsifier passes (5/6+5/6=83.3% appears in comparison doc); smoke tests all pass; kanban move only."
priority: medium   # Not blocking cutover (real outcomes are in per-rep stdout.log); polish for future canary runs
complexity: 2
effort_hours: 2
parent_review: TASK-REV-HM09
parent_task: TASK-HMIG-009A
parent_feature: autobuild-harness-migration
related_tasks:
  - TASK-HMIG-009A   # The batch this surfaced from
  - TASK-FIX-SPECHANG
tags:
  - bug-fix
  - canary-runner
  - reporting
  - batch-finding
falsifier: "After fix: re-running `python scripts/canary_validation_runner.py --variant 009a --aggregate` against the existing TASK-HMIG-009A-canary-results.json produces a comparison doc reporting 5/6 SDK + 5/6 LangGraph = 83.3% (matching the hand-compiled §8.5 of canary-analysis.md), not 0/0 = 0%. New canary batches record per-rep coach_decision (approved | feedback | error | unrecoverable_stall) + turns_used > 0 + AC-pass counts."
---

# Task: canary runner has two reporting bugs

## Surfaced by TASK-HMIG-009A AC-003 batch (2026-06-03 → 2026-06-04)

Both bugs are in `scripts/canary_validation_runner.py`. **Neither blocks the cutover decision** because the per-rep `stdout.log` files preserve the real outcomes — but both make the runner's auto-generated reports misleading.

## Bug 1: Outcome parser returns `unknown` for every rep

**Evidence**: `TASK-HMIG-009A-canary-results.json` records this for ALL 12 reps:

```json
{
  "harness": "sdk",
  "task_id": "TASK-FIX-A7D3",
  "run_index": 2,
  "exit_code": 0,
  "coach_decision": "unknown",     // ← should be "approved"
  "turns_used": 0,                 // ← should be 2
  "acceptance_criteria_passed": 0, // ← should be > 0
  "wall_clock_seconds": 2270.7
}
```

But the per-rep `stdout.log` clearly contains:

```
│ 2      │ Coach Validation          │ ✓ success    │ Coach approved - ready for human review │
│ Status: APPROVED                                                                              │
│ Coach approved implementation after 2 turn(s).                                                │
```

So the runner can parse `exit_code` and `wall_clock_seconds` correctly but not the orchestration outcome from stdout. The fix is to grep/parse the stdout.log for the markers:

- `Status: APPROVED` / `Status: ERROR` / `Status: FAILED`
- `Coach approved implementation after N turn(s)`
- `Reason: unrecoverable_stall`
- `Total turns: N`

And populate `coach_decision`, `turns_used`, `acceptance_criteria_*` accordingly.

## Bug 2: `--aggregate` without `--variant` reads wrong file

**Evidence**: operator ran `python scripts/canary_validation_runner.py --aggregate` (no variant flag) after the 12-run 009a batch. The runner read `.guardkit/autobuild/TASK-REV-HMIG-canary-results.json` (the OLD full-009 results file with 1 run from yesterday's pilot) instead of `.guardkit/autobuild/TASK-HMIG-009A-canary-results.json` (the 12-run 009a file). Comparison doc reported `0/0 = 0% FALSIFIED` — wildly wrong.

Workaround: always pass `--variant 009a --aggregate` together. But this is footgun-shaped — the help text + the run command's success message should prompt the right aggregate command:

```python
# In the runner's final success message:
if variant:
    print(f"Re-invoke with --variant {variant} --aggregate to refresh the comparison doc:")
    print(f"  python scripts/canary_validation_runner.py --variant {variant} --aggregate")
else:
    print(f"Re-invoke with --aggregate to refresh the comparison doc:")
    print(f"  python scripts/canary_validation_runner.py --aggregate")
```

## Acceptance Criteria

- [x] **AC-001** — `canary_validation_runner.py` outcome parser extracts `coach_decision` (approved | feedback | error | unrecoverable_stall), `turns_used`, `acceptance_criteria_passed`, `acceptance_criteria_failed` from the per-rep `stdout.log` after each rep completes. Populated correctly in `TASK-HMIG-009A-canary-results.json` (and the equivalent full-009 file).
- [x] **AC-002** — Re-running the parser against the existing 12-run results (without re-executing the orchestration) produces correct values. Either via a helper sub-command (e.g. `--reparse-stdout`) or by deleting `TASK-HMIG-009A-canary-results.json`'s 12 entries and letting the runner re-detect them via the per-rep `stdout.log` files.
- [x] **AC-003** — `--aggregate` without `--variant` flag: either errors out asking the operator to specify a variant, OR detects the most recent variant from the most-recently-modified results file. Document the chosen behaviour.
- [x] **AC-004** — Runner's final success message includes the correct `--aggregate` command with the variant flag when one was used for the batch.
- [x] **AC-005** — Falsifier: re-running `python scripts/canary_validation_runner.py --variant 009a --aggregate` against the existing results produces a comparison doc matching the hand-compiled §8.5 of `canary-analysis.md` (5/6 SDK + 5/6 LangGraph = 83.3%).

## Completion notes (2026-06-04)

**AC-001** — `parse_stdout_outcome()` added in [scripts/canary_validation_runner.py:380-440](scripts/canary_validation_runner.py#L380-L440). Maps stdout `Status: <X>` (rendered by `progress.py:render_summary`) → canonical `coach_decision` (`approve` / `feedback` / `unrecoverable_stall` / `error`), reads `Total turns: N` for `turns_used`. Wired into `harvest_run_artefacts` as a fallback (when `coach_turn_*.json` harvesting yields `unknown` or `turns_used=0`). **AC counts intentionally left at 0 per the task's "Out of scope" note** — stdout doesn't surface AC details and the per-rep `stderr.log` / `coach_turn_*.json` are out of scope. Verified against all four observed status types (APPROVED/turns=1, APPROVED/turns=2, ERROR/turns=2, UNRECOVERABLE_STALL/turns=3) — all parse correctly.

**AC-002** — `--reparse-stdout` subcommand added. Walks the run records in `<namespace>-results.json`, reads each rep's `stdout.log`, and refreshes `coach_decision` + `turns_used` in place. Non-destructive (never overwrites a known value with `unknown`/0), idempotent (second run reports `Updated: 0`). Verified by running it twice against the 12-rep 009a batch: first run updated all 12, second run reported `Updated: 0, Unchanged: 12`.

**AC-003** — Chose **error-and-list-variants** (per operator decision 2026-06-04). When `--aggregate` or `--reparse-stdout` runs without `--variant`, the runner exits with a list of every `*-canary-results.json` file under `.guardkit/autobuild/`, each annotated with the `--variant <name>` flag (or `(no registered variant)` for the legacy default). This eliminates the silent fall-through to the wrong file that caused the TASK-HMIG-009A misleading 0/0 verdict.

**AC-004** — Final success message in `main()` now reads the variant flag from `args` and prints the matching `--aggregate` invocation. Was: `python scripts/canary_validation_runner.py --aggregate` (no variant). Now: `python scripts/canary_validation_runner.py --variant <variant> --aggregate` when the batch was run with `--variant`.

**AC-005 (falsifier)** — Verified end-to-end. Ran `--variant 009a --reparse-stdout` (12 records updated from `unknown`/0 to the right decisions + turn counts), then `--variant 009a --aggregate`. The regenerated `TASK-HMIG-009A-canary-comparison.md` now reports:
- `Approve rate (any turns) | 5/6 (83.3%) | 5/6 (83.3%)` — matches the task falsifier's "5/6 SDK + 5/6 LangGraph = 83.3%" expectation exactly
- `First-pass success (turns=1) | 4/6 (66.7%) | 4/6 (66.7%)` — preserved as the strict cutover-bar metric (two of the approves needed 2 turns)
- Title now reads `TASK-HMIG-009A` (was hardcoded `TASK-REV-HMIG`)
- Results-file reference now reads `TASK-HMIG-009A-canary-results.json` (was hardcoded `TASK-REV-HMIG-canary-results.json`)
- §4 artefact reference now reads `.guardkit/autobuild/TASK-HMIG-009A-canary/` (was hardcoded `.guardkit/autobuild/TASK-REV-HMIG-canary/`)

The Wave-4 cutover bar in `aggregate()` (`lg_rate >= 75` → GO) remains unchanged — it still uses first-pass strict per existing convention. Adding the approve-rate column gives the operator both numbers without touching cutover semantics.

**Out of scope, not addressed**:
- The third runner gap (`coach_turn_*.json` not being harvested into the canary artefact dirs — root cause of why the parser returns `unknown` in the first place). The stdout-fallback fix here is the right backstop, but the artefact-harvesting gap is filed as `TASK-FIX-CANARY-ARTEFACTS` if it surfaces again.
- AC counts in records re-parsed from stdout (stay at 0 — the task's "Out of scope" note says don't try to parse honesty scores or AC details from stdout).

**Smoke tests passed**:
- `python -c "import ast; ast.parse(...)"` — syntax OK
- `--aggregate` without `--variant` — exits 1 with helpful error
- `--reparse-stdout` without `--variant` — exits 1 with helpful error
- `--variant 009a --reparse-stdout` (twice) — first run updates 12, second is no-op
- `--variant 009a --aggregate` — comparison doc shows 5/6+5/6=83.3% approve, correct title, correct paths
- `--variant 009a --dry-run` — still lists the 12-run plan correctly (no regression)
- `--variant bogus --aggregate` — argparse rejects with valid-choices list (no regression)
- `parse_stdout_outcome()` unit-style test against 4 real stdout.log files + 1 nonexistent path — all 5 cases match expected decision + turns

## Out of scope

- The third runner gap surfaced earlier (per-rep artefacts like `player_turn_*.json` not being copied) — file as `TASK-FIX-CANARY-ARTEFACTS` if it bites again. Not in this task's scope.
- Improving the runner's failure-classification beyond what stdout markers expose. Don't try to parse honesty scores or AC details from stdout; the per-rep stderr.log has those if needed.

## Why this matters

Future canary batches need to be trustworthy without operator-side hand-compilation. The TASK-HMIG-009A batch's verdict was salvageable because we could read 12 stdout.log files individually; the next batch should produce a correct auto-generated comparison doc.

## References

- **Real outcomes table**: [`docs/state/TASK-REV-HMIG/canary-analysis.md` §8.5](../../../docs/state/TASK-REV-HMIG/canary-analysis.md)
- **Wrong runner-generated comparison doc**: [`.guardkit/autobuild/TASK-REV-HMIG-canary-comparison.md`](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-comparison.md)
- **Wrong results JSON**: [`.guardkit/autobuild/TASK-HMIG-009A-canary-results.json`](../../../.guardkit/autobuild/TASK-HMIG-009A-canary-results.json)
- **Runner source**: [`scripts/canary_validation_runner.py`](../../../scripts/canary_validation_runner.py)
- **Per-rep stdout.log files** (the ground truth): under `.guardkit/autobuild/TASK-HMIG-009A-canary/{sdk,langgraph}/TASK-*/run_N/stdout.log`
