# Run-24 autobuild artifacts snapshot — 25-second failure from regression in `build_autobuild_backend()` kwarg

> **Purpose**: snapshot the partial FEAT-AOF artifact tree from run 24
> (failed at 25s with a TypeError in the harness selector) so the GB10
> Claude session can confirm the regression diagnosis.
>
> **Source**: live worktree artifacts copied 2026-06-10T19:05Z.
> **Run log**:
> [`autobuild-FEAT-AOF-run-24.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-24.md)
> (committed in the same change as this snapshot).

## TL;DR — code regression in the harness selector, NOT a substrate issue

```
FEATURE RESULT: FAILED
Status: FAILED
Tasks: 0/3 completed (1 failed)
Duration: 25s
```

[`selector.py:256+302`](../../../../guardkit/orchestrator/harness/selector.py)
extracts and passes a `max_tool_result_chars` kwarg, but
`build_autobuild_backend()` in guardkitfactory doesn't accept it:

```
ERROR: SDK invocation failed for player (TypeError):
  build_autobuild_backend() got an unexpected keyword argument 'max_tool_result_chars'

  File "guardkit/orchestrator/harness/selector.py", line 301
    backend=build_autobuild_backend(
              Path(cwd), max_tool_result_chars=max_tool_result_chars
            ),
```

Single-point-of-failure code regression: the selector hits this on
**every** SDK invocation, so Player turn 1 fails immediately and Coach
synthesis fails the same way (line 158 of the run log).

## What introduced it

Commit `f4b6422a feat(autobuild): Lever 3 B-full budget docs +
complete TASK-PERF-COACHTURNBUDGET`. The intent was correct (per the
selector's own comment at line 249-252):

> *"`max_tool_result_chars` — forwarded to `build_autobuild_backend`
> so each gather tool result is truncated before it re-enters context.
> Both default to `None` (unbounded / LangGraph-default) so the Player
> and synthesis paths are unchanged."*

But the guardkitfactory side of the interface (the
`build_autobuild_backend()` function signature) wasn't updated in the
same change. Classic cross-repo coupling miss — the orchestrator
expects a newer guardkitfactory than is installed.

## The fix

One of:

1. **(preferred)** Update `build_autobuild_backend()` in guardkitfactory
   to accept `max_tool_result_chars` (with default `None` so existing
   callers don't change). Land + pin guardkitfactory version
   appropriately.
2. **(defensive)** Have `select_harness` introspect
   `build_autobuild_backend`'s signature with
   `inspect.signature(...).parameters` and only pass the kwarg if it's
   accepted. Backwards-compatible while guardkitfactory catches up.
3. **(quickest)** Operator workaround — pin guardkitfactory to a
   version that accepts `max_tool_result_chars`, OR drop the kwarg
   from the selector temporarily by commenting out line 302's kwarg.

The defensive Shape-2 is the safer landing for guardkit's selector
code — orchestrator-side compatibility check, not a coupled-deploy
requirement.

## What's in this snapshot

### `TASK-FIX-IA03/` — 6 files (Player+Coach both failed pre-emission)

| File | Notes |
|---|---|
| `task_work_results.json` | Player failure payload — the immediate TypeError trace lives here |
| `work_state_turn_1.json` | **State-recovery output** — orchestrator successfully captured 5 git-detected file changes despite the Player crash (architecture win) |
| `turn_state_turn_1.json` | Orchestrator's post-turn-1 snapshot (decision: `error`) |
| `specialist_results.json` | test-orchestrator specialist also TypeError'd (same kwarg bug) |
| `turn_context.json` + `state_transitions.json` | Loader / state-bridge metadata |

No `player_turn_1.json` (Player never emitted), no `coach_turn_1.json`
(Coach also failed via same path), no `phase_4_summary.json` (Coach
didn't reach phase 4), no `checkpoints.json` (no successful turn to
checkpoint).

### TASK-FIX-GD02/ and TASK-FIX-TP05/ — not started

`--stop-on-failure=True` halted execution after Wave 1's IA03 failure.

## ✅ One small architecture win even in this failure

State recovery worked. Even though Player's SDK invocation crashed
with a TypeError, the orchestrator's
`state_detection` + `state_tracker` modules captured the worktree
state via git diff (5 files changed, 4 created, 1 modified) and
generated a synthetic report ([log lines 130-139](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-24.md#L130-L139)).
That's the "recovered=1" cell in the wave summary.

The recovered state then flowed through to Coach, which attempted
its own invocation — which **also** TypeError'd, because Coach
synthesis goes through the same selector path. So state recovery
worked but the regression bit on both sides of the loop.

## Cross-reference

- **Selector buggy call sites**:
  - [`guardkit/orchestrator/harness/selector.py:256`](../../../../guardkit/orchestrator/harness/selector.py) (extract)
  - [`guardkit/orchestrator/harness/selector.py:302`](../../../../guardkit/orchestrator/harness/selector.py) (pass to `build_autobuild_backend`)
- **Originating commit**: `f4b6422a feat(autobuild): Lever 3 B-full
  budget docs + complete TASK-PERF-COACHTURNBUDGET`
- **TASK-PERF-COACHTURNBUDGET task file**: likely in
  `tasks/in_progress/` or `tasks/completed/` — should be reopened
  with this regression evidence
- **Run-23 (last successful)**: 2/3 success + Coach caught real bug —
  the baseline this run regressed against
- **Run-20 (last 3/3 success)**: B-min default posture, cutover-baseline

## Suggested next steps

1. **Land the orchestrator-side defensive fix** (Shape 2 above) so
   the orchestrator works against any guardkitfactory version.
   ~10-line change in `select_harness`.
2. **Update guardkitfactory's `build_autobuild_backend()`** to accept
   `max_tool_result_chars` per the intent in the selector comment.
3. **Re-run run 25** after the fix lands. The B+C posture
   (3 sequential waves, all 3 pending) is still in working tree from
   the run-23/24 reset — should just work.
4. **Reopen TASK-PERF-COACHTURNBUDGET** to track the missing
   guardkitfactory-side change.

## What's NOT a finding

- F20/F23A/F24 substrate envelope: untouched this run (substrate never
  got hit; the regression is purely orchestrator-side)
- Coach quality (verdicts, criteria_verification): untouched (Coach
  never emitted a verdict because the harness selector crashed before
  it could)
- Any of the COACHBFULL / COACHFG01 / COACHSF01 / CTOUT01 invariants:
  not exercised (Coach failed at the harness layer, below where these
  fire)

Cutover-baseline evidence (runs 20 + 23) is unchanged. This run
diagnoses a regression that needs a fix-forward, not new architecture.
