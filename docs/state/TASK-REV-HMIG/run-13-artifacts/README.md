# Run-13 autobuild artifacts snapshot

> **Purpose**: snapshot the `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`
> artifacts from run 13 to a tracked path so the GB10 Claude session can
> pick them up for diagnosis. The worktree path itself is `.gitignore`-d
> (per the `.guardkit/worktrees/` rule); this directory is its tracked
> twin for this specific diagnostic.
>
> **Source**: live worktree artifacts copied 2026-06-08T13:48Z from
> `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`.
> **Run log**: [`autobuild-FEAT-AOF-run-13.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-13.md)
> (already committed as `d0eaeb9d next run`).

## ⚠️ There is NO `coach_turn_*.json` artifact

Coach was **SDK-cancelled at 2340s** (the per-invocation SDK timeout)
before emitting any verdict file. See [run-13 log line 325](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-13.md#L325):

```
Coach failed
Error: SDK timeout after 2340s: Agent invocation exceeded 2340s timeout
```

The Coach LLM made successful HTTP 200s throughout (lines 288-318
visible at sample points 1410s, 1440s, 2160s, 2190s elapsed — the
substrate held up), but never converged on a verdict that satisfied the
grammar constraint AND fit within the SDK timeout. Total Coach LLM
wall: ~39 minutes (09:53:47 → 10:32:49).

This is **not the same failure shape as run 12** (which hit
`Coach decision invalid` and `Coach decision not found` via COACHSF01
synthetic-feedback recovery). The grammar enforcement (TASK-OPS-COACHGRAMMAR
commit `ea37e112`) appears to have shifted the failure mode from
"emit-something-bad-then-retry" to "reason-forever-trying-to-emit-valid".

## What's in this snapshot

| File | Size | What | Useful for |
|---|---:|---|---|
| `player_turn_1.json` | 7633 B | Player's enriched output → Coach's input | Understand what Coach was asked to validate |
| `task_work_results.json` | 10312 B | Player's task-work output incl. specialists | Same as above; richer detail |
| `specialist_results.json` | 539 B | test-orchestrator specialist (hit SPECHANG, contained) | Confirms specialist failure mode (graceful) |
| `turn_state_turn_1.json` | 5366 B | Orchestrator's post-turn snapshot | Final orchestrator-side state record (Coach result = `error`) |
| `turn_context.json` | 763 B | Per-thread context loader state | Graphiti / loader inspection |
| `state_transitions.json` | 340 B | state_bridge mutations log | Ghost-path filter / state-bridge inspection |

## Diagnostic hypotheses for the GB10 session

1. **Grammar over-constrains generation**: gemma4 can't satisfy the
   schema at the conversation's complexity / size, so it explores
   forever. Try loosening the grammar (more permissive `optional-fields`,
   allow looser whitespace, etc.) and re-run.
2. **Grammar conflict with `--reasoning auto`**: with reasoning enabled
   the model wants to think extensively in `reasoning_content` before
   committing to the fenced JSON; the grammar applies to `content` only
   (or both, depending on llama.cpp version), so the model never gets
   "permission" to terminate.
3. **SDK timeout too short for grammar-constrained generation**: 2340s
   per-invocation timeout was tuned for unconstrained generation; under
   grammar enforcement Coach needs more time. Raise the SDK timeout
   (env-tunable per other recent fixes) AND see if Coach converges.
4. **Coach prompt complexity**: turn-1 input is much bigger than the
   smoke prompt that passed AC-4 of TASK-OPS-COACHGRAMMAR; the model
   that emits 5/5 valid on a short prompt may struggle on the full
   Coach prompt. Compare token counts.

## What's NOT in this snapshot

- Coach verdict file (`coach_turn_1.json`) — doesn't exist, see above.
- `phase_4_summary.json` — present in some past runs, absent here
  because Coach didn't complete.
- `coach_feedback_for_turn_2.json` — would only exist if COACHSF01 fired.
- `checkpoints.json` — would only exist after Coach completion.
- The full Coach LLM stream (would be massive; the orchestrator
  doesn't persist intermediate LLM events by design).

If the GB10 session needs the full Coach LLM stream/messages, those
are NOT available from the orchestrator's persisted state — the only
record of what gemma4-coach was producing is in the llama-swap /
llama.cpp server logs on `promaxgb10-41b1` itself (which the GB10
session has direct access to).
