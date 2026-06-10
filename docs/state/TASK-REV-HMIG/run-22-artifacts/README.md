# Run-22 autobuild artifacts snapshot — 2/3 success; new findings: `--max-parallel 1` broken + F20 returns on gemma4:31b

> **Purpose**: snapshot the FEAT-AOF artifact tree from run 22 (second
> attempt — see run-22 log for the first attempt's worktree-cleanup
> failure, and run-21 README for the original parallel-substrate
> diagnostic chain). Same handoff pattern as runs 13-21.
>
> **Source**: live worktree artifacts copied 2026-06-10T10:50Z.
> **Run log**:
> [`autobuild-FEAT-AOF-run-22-attempt-2.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-22-attempt-2.md)
> (committed in the same change as this snapshot).

## TL;DR — 2/3 success but two new findings surface

```
FEATURE RESULT: FAILED
Status: FAILED
Tasks: 2/3 completed (1 failed)
Duration: 165m 27s
```

| Task | Wave | Mode | Outcome | Notes |
|---|---|---|---|---|
| TASK-FIX-IA03 | 1 (sequential) | B-full → toolless synthesis | ✓ approve, 5/5 ACs, 29 tests, **populated criteria_verification (5 entries)** | Same shape as run 21 IA03 ✓ |
| TASK-FIX-GD02 | 2 (parallel with TP05) | B-full → toolless synthesis | ✓ approve, 7/7 ACs, 10 tests, **populated criteria_verification (7 entries)** | **Succeeded despite running parallel with TP05's F20 grind** |
| TASK-FIX-TP05 | 2 (parallel with GD02) | B-full Phase-A → F20 ctx overflow → degraded to B-min → task-timeout cancel | ✗ timeout (no Coach verdict) | New F20 ctx overflow at 108,094 / 98,304 tokens |

### 🆕 Finding 1: `--max-parallel 1` is silently ignored by Wave-level execution

The CLI was invoked with `--max-parallel 1` specifically to avoid the
run-21 parallel-substrate crash. The orchestrator's log
([line 286](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-22-attempt-2.md#L286))
contradicts the flag:

```
[2026-06-10T07:30:11.500Z] Wave 2/2: TASK-FIX-GD02, TASK-FIX-TP05 (parallel: 2)
```

Wave 2 ran both tasks in parallel anyway. Note the curious next two lines
([293-294](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-22-attempt-2.md#L293-L294)):

```
INFO:guardkit.orchestrator.parallel_strategy:Wave 2: max_parallel=1 (static)
INFO:guardkit.orchestrator.feature_orchestrator:Starting parallel gather for wave 2:
  tasks=['TASK-FIX-GD02', 'TASK-FIX-TP05'], task_timeout=4800s ...
```

The `parallel_strategy` module reports `max_parallel=1` correctly, but
the `feature_orchestrator`'s parallel-gather call ignores that decision
and launches both tasks via `asyncio.gather`. This is a **decision-vs-execution
disconnect**: the strategy is computed but never enforced.

Likely fix: `feature_orchestrator._execute_wave_parallel` (or whichever
function dispatches the wave) needs to consume `max_parallel` from the
strategy and use either `asyncio.Semaphore(n)` or sequential await
instead of unbounded `gather`. Worth filing as
**TASK-FIX-MAXPARALLEL01** — sibling-of-FRESHRESET01 / FEATYAMLPATH01
/ WTCLEANUP01 in the orchestrator-state-management cleanup cluster.

### 🆕 Finding 2: F20 (ctx overflow) returns on gemma4:31b at 98,304 n_ctx

TP05's Coach Phase-A (B-full investigation, agentic tool-use loop)
ran for ~1170s producing successful HTTP 200s, then hit
([log:937-938](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-22-attempt-2.md#L937-L938)):

```
HTTP/1.1 400 Bad Request
Error code: 400 - {'error': {'code': 400,
  'message': 'request (108094 tokens) exceeds the available context size (98304 tokens), try increasing it',
  'type': 'exceed_context_size_error',
  'n_prompt_tokens': 108094, 'n_ctx': 98304}}
```

This is **F20 from run-17 recurring**. The n_ctx is now **98,304** (the
GB10 had bumped it from 65,536 at some point post-run-17), but B-full's
agentic tool-use loop grew TP05's context past that. The Phase-A
investigation Coach is the load-bearing F20 surface for the gemma4:31b
substrate — every tool call adds tool-result tokens that accumulate.

**COACHBFULL's graceful-degradation fired correctly** — fell back to
B-min synthesis ([line 938](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-22-attempt-2.md#L938)).
But by then the task budget (4800s = 80 min) had been consumed by the
Phase-A grind, and CTOUT01 cancelled the B-min synthesis ~60s into its
attempt ([log:944-947](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-22-attempt-2.md#L944-L947)).

### ✅ Win 1: Wave 1 + Wave 2 GD02 both produced B-full enriched verdicts

Both successful Coach verdicts contain **populated `criteria_verification`
arrays** with per-AC `verified` notes citing concrete code/test evidence —
the run-19 caveat #2 closure replicates across two more tasks:

- IA03: 5 verified entries, 29 tests in `test_doc_level_constraint.py`
- GD02: 7 verified entries, 10 tests in `test_per_task_git_delta.py`

### ✅ Win 2: substrate held under parallel load (different shape from run 21)

Compare to run 21 Wave 2 where **both** parallel Coach calls hit HTTP 502
simultaneously and the substrate crashed (F23A class). Run 22 Wave 2 ran
the same parallel shape (GD02 + TP05) — GD02 completed normally (Coach
approved at 08:26:44), only TP05 hit the F20 ctx overflow.

This is a positive substrate-stability signal: gemma4:31b can now serve
one healthy Coach call while another is grinding through tool-use loops
without the whole substrate falling over. Whatever changed between
runs 21 and 22 (n_ctx bump from ?→98,304; possibly memory tuning)
moved the failure envelope from "both crash together" to "one fails
single-call ctx, other completes fine".

### ✅ Win 3: COACHBFULL graceful-degradation + CTOUT01 both worked exactly as designed

- COACHBFULL Phase-A→B-min handler fired correctly on the F20
- CTOUT01 cancellation cancelled the B-min synthesis cleanly when task
  timeout fired
- COACHSF01 NOT routed for the substrate F20 error (correct per the
  substrate-vs-decision invariant)

Architecture remains solid. The new findings are bug-class
(`--max-parallel`) and substrate-envelope (`n_ctx` for B-full),
not architectural regressions.

## Run progression at a glance

| Phase | Time | Result |
|---|---|---|
| Feature start | 07:01:14 UTC | task budget 4800s × 3, `--max-parallel 1` requested |
| Wave 1 / IA03 Player | → 07:06:03 (~5m) | ✓ 41 created |
| Wave 1 / IA03 Coach (B-full) | → 07:30:11 (~24m) | ✓ APPROVE, populated criteria_verification |
| Wave 2 starts | 07:30:11 | both GD02 + TP05 launched in parallel (flag ignored) |
| Wave 2 / GD02 Player + B-full Coach | → 08:26:44 (~57m) | ✓ APPROVE, populated criteria_verification |
| Wave 2 / TP05 Player | → 07:37:17 (~7m) | ✓ 2 created, 1 modified |
| Wave 2 / TP05 B-full Phase-A | running ~1170s | growing context via tool-use |
| **TP05 HTTP 400 ctx overflow** | ~09:23 | F20: 108,094 > 98,304 |
| TP05 COACHBFULL degrade to B-min synthesis | ~09:23 | correct fallback |
| TP05 B-min synthesis cancelled by task timeout | 09:46:44 | CTOUT01 fired correctly |
| FEATURE | FAILED | total 165m 27s |

## What's in this snapshot

### `TASK-FIX-IA03/` — 8 files (full set, Coach approved)

The headline verdict file
[`coach_turn_1.json`](TASK-FIX-IA03/coach_turn_1.json):

```json
{
  "task_id": "TASK-FIX-IA03",
  "turn": 1,
  "decision": "approve",
  "validation_results": {
    "requirements_met": ["AC-001","AC-002","AC-003","AC-004","AC-005"],
    "tests_run": true, "tests_passed": true,
    "test_output_summary": "29 passed, 2 warnings in 3.38s",
    ...
  },
  "criteria_verification": [ ...5 verified entries with code-citation notes... ]
}
```

### `TASK-FIX-GD02/` — 9 files (full set, Coach approved, **including `phase_4_summary.json`**)

Same shape as IA03 plus the rare `phase_4_summary.json`. 7/7 ACs, 10
tests passed in `test_per_task_git_delta.py`. The verdict was produced
while TP05 was grinding through Phase-A ctx overflow — substrate
served this in parallel without issue.

### `TASK-FIX-TP05/` — 6 files (no coach_turn_1.json, no turn_state, no checkpoints)

Coach failed to emit. Phase-4 summary IS present
([`phase_4_summary.json`](TASK-FIX-TP05/phase_4_summary.json)) — indicates
the COACHTESTTO bypass-LLM independent test execution completed
successfully before the Phase-A LLM call ran into F20. The Player work
itself was substantive (`player_turn_1.json` + `task_work_results.json`
show what TP05 produced).

## What's NOT in this snapshot

- TP05's `coach_turn_1.json` — F20 ctx overflow + task-timeout
  cancellation pre-empted verdict emission
- The full Coach LLM streams (especially the ~1170s of growing TP05
  Phase-A context). The interesting GB10 diagnostic question is:
  **what was in the conversation history at 108,094 tokens?** —
  tool results, agent self-reasoning, Player payload echoes? That
  answer is in llama.cpp logs on `promaxgb10-41b1`. Time window:
  **2026-06-10T08:34 → 09:46 UTC** for TP05's Coach.

## Diagnostic hypotheses for the GB10 session

1. **F20 is the load-bearing constraint for B-full at scale.** B-min
   (toolless synthesis only) doesn't hit it because the synthesis
   prompt is small and fixed. B-full's Phase-A investigation grows
   context proportional to the agentic depth needed to validate the
   work. As Player work gets bigger (TP05 created 1 file, modified 2;
   GD02 created 4, modified 3 — similar sizes) the agent's tool-use
   pattern may dominate. Worth confirming on the GB10 logs whether
   TP05 had any specific characteristic (specialist outputs, file
   contents) that drove the agent's loop deeper than GD02's.

2. **Wave-2 parallel concurrency may have amplified TP05's path.** If
   both parallel agents are competing for the same llama-server's KV
   cache, TP05's slower loop may have been further slowed by GD02
   sharing the bandwidth, growing its context further before reaching
   any termination point.

3. **The `--max-parallel 1` bug means we couldn't actually test that
   hypothesis cleanly.** Until TASK-FIX-MAXPARALLEL01 lands, the
   workaround is the per-feature.yaml `parallel_groups` shape — split
   GD02 and TP05 into separate waves (`- - GD02 \n - - TP05`) to
   force serialization at the YAML level. Cheap operator fix.

4. **Substrate envelope decision**: bump gemma4:31b `--ctx-size`
   above 98,304 (next jump per llama.cpp is usually 131,072 or
   262,144). Risk: re-introduces F23A territory under parallel-Coach
   load if RAM headroom doesn't widen.

## Cross-reference

- **F20 original finding + §9.13 n_ctx bump runbook**: F20 closed on
  gemma4-coach (26b) at 98,304 in run 9; recurring now on gemma4:31b
  with a bigger B-full payload
- **F23A diagnosis** (run-15 GB10 commit `1ee4baab`): the older
  shape that's NOT firing this run — substrate held up
- **Run-21 README**: the parallel-Wave-2 substrate-crash run that
  motivated `--max-parallel 1` (which then didn't work)
- **Run-20 README**: the last successful 3/3 run on B-min default
- **COACHFG01** (`ae2e1404`): fail-closed on absent oracle —
  presumably not exercised this run because the failure was a
  substrate error, not an oracle-absent verdict

## Suggested next steps

1. **File TASK-FIX-MAXPARALLEL01**: small ~10-line fix in
   `feature_orchestrator` to actually consume the strategy's
   max_parallel decision (semaphore or sequential await).
2. **Operator workaround for the next run**: edit FEAT-AOF.yaml's
   `orchestration.parallel_groups` to split Wave 2 into two
   single-task waves. Forces serialization without code change. Or,
   if you'd rather run with parallelism: bump gemma4:31b n_ctx to
   131,072 on llama-swap and watch `free -h` during the run.
3. **Run TASK-HMIG-011 (cutover) now** — run-20's B-min default
   posture is still the validated cutover baseline. B-full is opt-in
   enrichment that can mature on its own timeline.
4. **Audit-trail cleanup**: F20 needs a status update — *resolved on
   26b at 98,304 (run 9); recurring on 31b under B-full's agentic
   tool-use load*.
