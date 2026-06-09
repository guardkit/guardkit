# Run-17 autobuild artifacts snapshot

> **Purpose**: snapshot the `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`
> artifacts from run 17 to a tracked path so the GB10 Claude session can
> pick them up for diagnosis. Same pattern as the run-13 through run-16
> snapshots.
>
> **Source**: live worktree artifacts copied 2026-06-09T07:01Z from
> `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`.
> **Run log**: [`autobuild-FEAT-AOF-run-17.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-17.md)
> (committed in the same change as this snapshot).

## TL;DR — F20 RECURRING on gemma4:31b (different failure mode from runs 15/16)

Run 17 changed failure mode. Where runs 15+16 hit **F23A** (OOM →
HTTP 502 → Connection error), run 17 hit the original **F20**
(context-size overflow → HTTP 400):

```
HTTP Request: POST http://promaxgb10-41b1:9000/v1/responses "HTTP/1.1 400 Bad Request"
LangGraphHarnessError: agent.ainvoke failed for role='coach' model='openai:gemma4:31b':
Error code: 400 - {'error': {'code': 400,
  'message': 'request (66687 tokens) exceeds the available context size (65536 tokens), try increasing it',
  'type': 'exceed_context_size_error',
  'n_prompt_tokens': 66687,
  'n_ctx': 65536}}
```

[run-17 log lines 254-257](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-17.md#L254-L257).

**This is the exact same shape as F20 from run 8** — the original
substrate-sizing finding closed in run 9 by the §9.13 `--ctx-size`
bump on `gemma4-coach`. The bump apparently was **not carried over**
to the new `gemma4:31b` llama-swap entry. `n_ctx=65536` is the
llama.cpp default; the §9.13 fix bumped `gemma4-coach` to 98304.

The fix is the same as §9.13: bump `--ctx-size` on the `gemma4:31b`
llama-swap entry to at least 98304 (preferably 131072 given 31b
handles bigger payloads).

## The substrate-envelope picture across recent runs

Three different failure modes have now been seen on gemma4:31b,
depending on which limit hits first:

| Run | Player files | Coach prompt size | Failure | Mode |
|---:|---:|---|---|---|
| 15 | 30 | smaller | Turn 1 ✓ verdict, Turn 2 ✗ HTTP 502 | F23A (OOM on turn-2 prompt growth) |
| 16 | 71 | bigger from start | Turn 1 ✗ HTTP 502 | F23A (OOM on turn-1 big payload) |
| 17 | 41 | mid-size, grew to 66,687 tokens | Turn 1 ✗ HTTP 400 | F20 (ctx overflow, not OOM) |

**Why the difference between run-16 and run-17 (similar payload sizes,
different failures)**: the agentic-loop growth pattern is non-deterministic.
gemma4:31b takes a different number of tool calls before terminating,
and each tool result grows the conversation context. In run 17 the
loop ran long enough (66,687 tokens) to exhaust n_ctx; in run 16 it
exhausted KV-cache RAM first. The two limits sit close to each other
in this substrate envelope.

**Tension between the two fixes**:
- Bumping `--ctx-size` to fix F20 → allocates more KV cache → makes F23A worse
- Lower `--ctx-size` → trips F20 sooner

The right answer is **both** with operator tuning: enough `--ctx-size`
for Coach prompt growth + leave enough host memory headroom that F23A
doesn't fire. Per §9.13, gemma4-coach (26b) at `--ctx-size 98304`
sits at ~111GB used / 128GB total. 31b's weight footprint is larger,
so the workable n_ctx is smaller. The GB10 session needs to measure
the empirical envelope:

1. Set gemma4:31b `--ctx-size` to e.g. 81920 (1.25× current default).
2. Check `free -h` after model load + a representative Coach prompt.
3. If headroom ≥10 GB at peak, bump higher; if approaching OOM, back off.

## Run progression at a glance

| Phase | Time | Result |
|---|---|---|
| Wave 1 / IA03 start | 05:36:53 UTC | task budget 4800s |
| **Turn 1 Player** | → 05:42:54 (~361s) | ✓ **41 created**, 1 modified |
| Turn 1 test-orchestrator | SPECHANG 150s, contained by SPECCOCH01 | ✓ as designed |
| Coach independent tests | ✓ ran | (subprocess fallback or SDK, depending on outcome) |
| **Turn 1 Coach LLM start** | 05:45:24 | — |
| Coach LLM progress | ~25-30 successful HTTP 200s over ~990s | Agentic loop running normally |
| **HTTP 400 exceed_context_size_error** | ~990s elapsed (06:01:45) | F20 — n_ctx exhausted at 66,687 tokens > 65,536 |
| Coach failed | 06:01:45 | Connection error wrapping 400 |
| FEATURE | FAILED | total **24m 52s** |

## What's in this snapshot

| File | Size | What | Useful for |
|---|---:|---|---|
| `player_turn_1.json` | 7872 B | Coach input — turn-1 Player output | The 41-file payload that fed the Coach prompt |
| `task_work_results.json` | 10383 B | Player's enriched task-work output | Specialist + Player full state |
| `turn_state_turn_1.json` | 4838 B | Orchestrator's post-turn-1 snapshot | State record incl. Coach `error` result |
| `specialist_results.json` | 540 B | test-orchestrator SPECHANG (contained) | Specialist failure mode (graceful, F22-SPECCOCH01 working) |
| `turn_context.json` | 763 B | Per-thread context loader state | Graphiti / loader inspection |
| `state_transitions.json` | 340 B | state_bridge mutations log | Ghost-path filter / state-bridge inspection |

## What's NOT in this snapshot

- **`coach_turn_1.json`** — doesn't exist. Coach hit HTTP 400 before
  emitting. Same shape as run 16 in that no verdict landed, but
  different cause (F20 ctx overflow vs F23A OOM).
- **`coach_feedback_for_turn_2.json`**, **`player_turn_2.json`**,
  **`turn_state_turn_2.json`**, **`checkpoints.json`** — all n/a,
  didn't get to turn 2.
- The full Coach LLM stream (the ~25-30 HTTP 200s before the 400).
  Window: **2026-06-09T05:45:24 → 06:01:45 UTC** in llama-swap /
  llama.cpp logs on `promaxgb10-41b1`. The interesting datapoint here
  is **what the conversation history looked like at 66,687 tokens** —
  was it dominated by tool results, by reasoning_content, by Player
  payload echoes?

## Diagnostic hypotheses for the GB10 session

1. **Confirm n_ctx setting on gemma4:31b llama-swap entry.** If it's
   65536 (the llama.cpp default), apply the §9.13 pattern:

   ```yaml
   gemma4:31b:
     cmd: |
       /usr/local/bin/llama-server
         -m /opt/llama-swap/models/gemma4-31b/...gguf
         --port ${PORT}
         --ctx-size 81920   # NEW — bumped from 65536 default
         --reasoning auto
         # ... etc ...
   ```

   Restart llama-swap. Verify with `curl /v1/responses` + check log
   that `n_ctx` is the new value.

2. **Measure the F20-vs-F23A envelope empirically.** For each
   candidate `--ctx-size` value, capture `free -h` after model load +
   a representative Coach prompt. Plot:
   - X-axis: `--ctx-size`
   - Y-axis: peak RAM used during Coach LLM call
   - F20 line: 1.0 (i.e. prompt actually reaches `--ctx-size`)
   - F23A line: 128 GB host limit
   The workable envelope is between them.

3. **Once the envelope is known, decide cutover-shape**:
   - **D-1 (sizing-constrained cutover)**: pick `--ctx-size` at the
     widest safe value; document the Player payload size limit that
     keeps Coach prompt under the envelope. Risk: this codebase's IA03
     produced 30/41/71-file Player turns — three different sizes, all
     borderline. Real cutover workloads may exceed.
   - **D-2 (AC-007 escalation)**: wait for 2nd GB10 + nemotron-3-super:120b-a12b.
     Bigger memory + more reliable structured output. Schedule-dependent.
   - **D-3 (architectural pivot)**: split Coach into tool-using
     evidence-gathering + toolless grammar-enforced verdict-synthesis.
     The toolless phase has small fixed-size context; F20 + F23A both
     close architecturally. This is the convergence of the run-13
     grammar-no-op finding + the F23A envelope-constraint finding.
     ~1-2 day code change in
     [`guardkit/orchestrator/agent_invoker.py`](../../../../guardkit/orchestrator/agent_invoker.py).

4. **Architecture invariants still all working.** SPECCOCH01 contained
   the test-orchestrator SPECHANG; the orchestrator's error path
   classified Coach correctly as `error` (NOT routed through COACHSF01
   per the substrate-vs-decision invariant); CTOUT01 / ghost-path
   filter / MODEL-PROFILE all silent. No code regressions.

## Cross-reference

- **F20 original finding + §9.13 n_ctx bump runbook**:
  [`../../../research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md`](../../../research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md)
  §9.13 (the bump that resolved F20 on gemma4-coach in run 9 — same
  fix applies here for gemma4:31b)
- **F23A diagnosis** (run-15 GB10 commit): `1ee4baab`
- **F22 SPECCOCH01** (still working): confirmed by SPECHANG containment
  this run, no Coach grace-period cascade
- **TASK-OPS-COACH31B** (the 31B QAT Coach setup): commit `8ed242ae`
  — the n_ctx setting for gemma4:31b is what this snapshot needs to
  cross-reference; if 65536 is what TASK-OPS-COACH31B specified, that's
  the file to edit
- **F24 status**: NOT exercised this run — Coach never got to emit, so
  no new evidence on the structured-output question. F24 stays as last
  observed in run 15 turn 1 (real verdict on gemma4:31b is achievable
  when the substrate doesn't crash first)
- **Run-15 README** (first F23A observation):
  [`../run-15-artifacts/README.md`](../run-15-artifacts/README.md)
- **Run-16 README** (second F23A observation, on turn 1):
  [`../run-16-artifacts/README.md`](../run-16-artifacts/README.md)
