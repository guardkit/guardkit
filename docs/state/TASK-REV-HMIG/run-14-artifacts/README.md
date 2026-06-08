# Run-14 autobuild artifacts snapshot

> **Purpose**: snapshot the `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`
> artifacts from run 14 to a tracked path so the GB10 Claude session can
> pick them up for diagnosis. Same pattern as
> [`../run-13-artifacts/`](../run-13-artifacts/) — tracked twin of the
> normally-gitignored `.guardkit/worktrees/` source.
>
> **Source**: live worktree artifacts copied 2026-06-08T16:06Z from
> `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`.
> **Run log**: [`autobuild-FEAT-AOF-run-14.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-14.md)
> (committed in the same change as this snapshot).

## TL;DR — Path 1B (prompt-tightening) did NOT solve F24

Run 14 was the first run with **TASK-FIX-COACHSCHEMA (Path 1B)** landed
(commit `78fde34e fix(TASK-FIX-COACHSCHEMA): add Coach decisiveness +
self-check prompt block`) and **grammar enforcement reverted** (commit
`3f389429`, per the run-13 GB10 finding that route-level `--grammar-file`
is a no-op for tool-bound Coach agents).

The new failure surface is **F24 with two turns of synthetic-feedback
recovery before budget exhaustion**:

| Turn | Player | Coach content | Coach reasoning | Fenced JSON? | COACHSF01? | Wall |
|---:|---|---:|---:|---|---|---:|
| 1 | ✓ 29 created, 2 modified (7m 29s) | **328 chars** | **49,720 chars** | NO | ✓ synthetic feedback | Coach ~45 min |
| 2 | ✓ 0 created, 67 modified (3m 32s) | 1155 chars | 1347 chars | NO | ✓ synthetic feedback | Coach ~18 min |

Both `coach_turn_*.json` files have `coach_primary_synthetic_feedback: true`
and `category: "coach_primary_exception"`. The orchestrator emitted them;
gemma4-coach did NOT emit fenced JSON in either channel on either turn.

Wave ended with **`Status: TIMEOUT_BUDGET_EXHAUSTED`** at line 1130 —
new status shape, signals budget arithmetic exhausted after the
synthetic-feedback cascade rather than an SDK timeout.

Total run wall: **74m 9s**, 0/3 tasks completed.

## The headline observation — turn 1 reasoning_content went to 49,720 chars

That is **9× larger than run-12 turn-2** (5438 chars) and is approaching
the upper end of what `--reasoning auto` typically produces. gemma4 was
clearly trying *something* on turn 1; whether that's:

- **(H-A) Following the new self-check prompt rigorously** — re-reading
  its work multiple times in reasoning_content, never committing to a
  terminal fenced block in `content`
- **(H-B) Reasoning loop** — exploring the schema-emission decision
  without converging
- **(H-C) Toolling thrash** — the agentic loop calling tools repeatedly
  and reasoning between calls

…is what the GB10 diagnosis needs to discriminate. The orchestrator
captures it only as the COACHSF01 message ("328 chars content + 49720
chars reasoning_content"); the full content/reasoning is in the
llama-swap / llama.cpp logs on `promaxgb10-41b1`.

Notably **turn 2** dropped from 49,720 → 1347 chars reasoning, suggesting
either (a) the synthetic-feedback turn-1→turn-2 context steered Coach
toward terser output, or (b) gemma4 just gave up on extensive reasoning
the second time. Either way, no fenced JSON in either channel.

## Diagnostic hypotheses for the GB10 session

1. **The COACHSCHEMA prompt is not being routed to gemma4-coach in the way intended.**
   Verify the rendered Coach prompt actually includes the new
   decisiveness + self-check block. Check
   [`guardkit/orchestrator/agent_invoker.py`](../../../../guardkit/orchestrator/agent_invoker.py)
   for the Coach prompt construction path; cross-check what the
   harness sends to llama-swap for the Coach role.

2. **The self-check loop is what's driving the 49,720 char reasoning explosion.**
   If the prompt says "re-read your fenced JSON and verify N things",
   gemma4 may be doing N rounds of inner-monologue self-review without
   ever committing to a terminal block. The cure may be worse than the
   disease — consider whether COACHSCHEMA needs a "DO NOT re-verify
   more than once" clamp, or whether the schema example needs to be
   tightened to discourage exploration.

3. **The Coach is still a tool-using agentic Coach (per the run-13 finding).**
   The GB10 already established that `deepagents.create_deep_agent`
   sends tools on every `/v1/responses` call. Path 1B's prompt
   modification is being applied to a tool-using Coach. gemma4 may be
   spending reasoning_content on tool-result interpretation, not on
   verdict-emission. Consider whether the **fundamental fix** isn't
   prompt-shaping but factoring the Coach into:
   - **Tool-using investigation phase** (gemma4 as agent, gathers evidence)
   - **Toolless verdict-synthesis phase** (gemma4 with `--grammar-file`,
     given the evidence, must emit fenced JSON)
   This is the architectural pivot Path 1A's run-13 finding pointed to.

4. **Independent-test environment / specialist failures eating the budget.**
   `specialist_results.json` (540 B) is small — confirms test-orchestrator
   hit SPECHANG, contained by SPECCOCH01. Worth checking
   `task_work_results.json` (12,371 B) for whether the
   `validation=violation` injection had downstream effect on Coach
   reasoning ("Coach saw specialist failed → reasoned about it
   extensively → never produced a verdict").

## What's in this snapshot

| File | Size | What | Useful for |
|---|---:|---|---|
| `coach_turn_1.json` | 1248 B | Synthetic feedback (COACHSF01-emitted) | Confirms turn-1 failure shape + chars-by-channel |
| `coach_turn_2.json` | 1248 B | Synthetic feedback (COACHSF01-emitted) | Confirms turn-2 failure shape + chars-by-channel |
| `coach_feedback_for_turn_2.json` | 744 B | Coach feedback bundled for turn-2 Player | What turn-2 Player saw as input |
| `player_turn_1.json` | 6694 B | Coach input — turn-1 Player output | What Coach was asked to validate (turn 1) |
| `player_turn_2.json` | 9846 B | Coach input — turn-2 Player output | What Coach was asked to validate (turn 2) |
| `turn_state_turn_1.json` | 3936 B | Orchestrator's post-turn-1 snapshot | State record incl. Coach result |
| `turn_state_turn_2.json` | 7070 B | Orchestrator's post-turn-2 snapshot | State record incl. Coach result |
| `task_work_results.json` | 12371 B | Player's enriched task-work output | Specialist + Player full state |
| `specialist_results.json` | 540 B | test-orchestrator SPECHANG (contained) | Specialist failure mode |
| `checkpoints.json` | 699 B | Per-turn checkpoint pointers | Recovery lineage |
| `turn_context.json` | 763 B | Per-thread context loader state | Graphiti / loader inspection |
| `state_transitions.json` | 708 B | state_bridge mutations log | Ghost-path filter / state-bridge inspection |

## What's NOT in this snapshot

- The full Coach LLM stream / message bodies. The orchestrator records
  the **char counts** of `content` and `reasoning_content` in the
  COACHSF01 message but not the bodies themselves. The full Coach
  responses (especially the 49,720-char turn-1 reasoning) are only in
  the **llama-swap / llama.cpp logs on `promaxgb10-41b1`** which the
  GB10 session has direct access to.
- `phase_4_summary.json` — absent (Coach didn't reach phase 4 on either
  turn; both Coach turns failed verdict-emission).
- Test/coverage reports — Player created 29+0 files, modified 2+67, no
  tests passing in either turn (per the run log progress lines).

If the GB10 needs the full Coach LLM bodies, **grab them from
llama.cpp logs around these timestamps**:

| Window | UTC start | UTC end | Coach call |
|---|---|---|---|
| Turn 1 Coach | 2026-06-08T13:43:52 | 2026-06-08T14:28:39 | Produced 328+49720 chars, no fence |
| Turn 2 Coach | 2026-06-08T14:32:12 | 2026-06-08T14:50:32 | Produced 1155+1347 chars, no fence |

## Cross-reference

- **Run-13 grammar no-op finding** (the architecturally-load-bearing
  prior insight):
  [`../run-13-artifacts/README.md`](../run-13-artifacts/README.md) §
  "RESOLVED on the GB10 (2026-06-08)" + commit `3f389429`.
- **TASK-FIX-COACHSCHEMA (Path 1B)** that landed for this run: commit
  `78fde34e`. Task file:
  [`../../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-COACHSCHEMA-tighten-coach-prompt-schema-emission.md`](../../../../tasks/backlog/autobuild-harness-migration/TASK-FIX-COACHSCHEMA-tighten-coach-prompt-schema-emission.md).
- **F24 paragraph** in
  [`../feature-run-analysis.md`](../feature-run-analysis.md) §6 — the
  load-bearing substrate-quality constraint this run was meant to
  evaluate.
- **TASK-HMIG-013 AC-007 (escalation path)** — `nemotron-3-super:120b-a12b`
  on 2nd GB10 + ConnectX-7, gated on hardware ETA. If Path 1B is
  conclusively insufficient (which run-14 evidence suggests), this
  becomes the cutover surface.
