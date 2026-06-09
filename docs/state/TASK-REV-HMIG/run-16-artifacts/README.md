# Run-16 autobuild artifacts snapshot

> **Purpose**: snapshot the `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`
> artifacts from run 16 to a tracked path so the GB10 Claude session can
> pick them up for diagnosis. Same pattern as
> [`../run-13-artifacts/`](../run-13-artifacts/),
> [`../run-14-artifacts/`](../run-14-artifacts/),
> [`../run-15-artifacts/`](../run-15-artifacts/).
>
> **Source**: live worktree artifacts copied 2026-06-08T21:57Z from
> `.guardkit/worktrees/FEAT-AOF/.guardkit/autobuild/TASK-FIX-IA03/`.
> **Run log**: [`autobuild-FEAT-AOF-run-16.md`](../../../reviews/autobuild-migration/autobuild-FEAT-AOF-run-16.md)
> (committed in the same change as this snapshot).

## TL;DR — F23A (OOM) reproduced on turn 1 with bigger Player payload

Run 16 is the second observation of **F23A** (global OOM on gemma4:31b,
diagnosed by the GB10 session in commit `1ee4baab`). Where run 15 hit
F23A on **turn 2** (after a successful turn-1 Coach verdict), run 16
hit it on **turn 1** — because Player created **71 files** this time
(vs 30 in run 15). The bigger Player payload → bigger Coach prompt →
exhausted GB10 RAM/VRAM envelope → llama-server crash → HTTP 502 →
Connection error.

**Zero Coach verdicts emitted this run.** No `coach_turn_1.json` in
the artifacts.

| Run | Player turn-1 files | F23A hit on | Coach turn-1 outcome | Coach turn-2 outcome |
|---:|---:|---|---|---|
| 15 | 30 created | turn 2 | ✓ real verdict (caught Player lie) | ✗ 502 Connection error |
| 16 | **71 created** | **turn 1** | ✗ 502 Connection error | n/a (didn't get there) |

The data is now consistent with the GB10's F23A diagnosis: **31b weights
+ growing Coach prompt = OOM threshold reached earlier on bigger payloads**.

## Run progression at a glance

| Phase | Time | Result |
|---|---|---|
| Wave 1 / IA03 start | 20:37:21 | task budget 4800s (per-task frontmatter override) |
| **Turn 1 Player** | → 20:41:56 (~275s) | ✓ **71 created**, 1 modified |
| Turn 1 test-orchestrator | SPECHANG 150s, contained by SPECCOCH01 | ✓ as designed |
| Coach context load | 1.1s (Graphiti up, 7 categories, 3210/5200 tokens) | ✓ |
| Coach independent tests | SDK path, 99.1s | ✓ |
| **Turn 1 Coach LLM start** | 20:44:26 | — |
| Coach LLM progress | ~25 successful HTTP 200s over ~690s | LLM was actively reasoning |
| **HTTP 502 / Connection error** | ~690-720s elapsed (~20:56) | F23A — OOM crash on llama-server |
| OpenAI retries | 2 attempts (lines 286-287), both fail | substrate didn't recover |
| **Coach failed** | 20:57:45 | Connection error |
| FEATURE | FAILED | total **20m 25s** |

Coach made roughly 25 successful HTTP calls (Player evidence-gathering
tool calls under the agentic loop) over ~690s before the substrate
crashed. This is **further along than run 13** (Coach reasoned forever,
SDK-cancelled at 2340s) and **roughly the same shape as run 15 turn-2**
(which made ~similar HTTP count before 502). Consistent with F23A:
gemma4:31b is *capable* of substantial Coach work but runs out of
memory headroom under the prompt sizes this codebase produces.

## What's in this snapshot

| File | Size | What | Useful for |
|---|---:|---|---|
| `player_turn_1.json` | 10753 B | Coach input — what the bigger Player payload looked like | Why F23A fired earlier this run |
| `task_work_results.json` | 13423 B | Player's enriched task-work output | Specialist + Player full state |
| `turn_state_turn_1.json` | 7943 B | Orchestrator's post-turn-1 snapshot | State record incl. Coach `error` result |
| `specialist_results.json` | 540 B | test-orchestrator SPECHANG (contained) | Specialist failure mode (graceful) |
| `turn_context.json` | 763 B | Per-thread context loader state | Graphiti / loader inspection |
| `state_transitions.json` | 340 B | state_bridge mutations log | Ghost-path filter / state-bridge inspection |

## What's NOT in this snapshot

- **`coach_turn_1.json`** — doesn't exist. Coach hit Connection error
  before emitting. Same shape as run-13 (SDK timeout pre-emission) but
  driven by F23A OOM not SDK budget.
- **`coach_feedback_for_turn_2.json`** — n/a, didn't get to turn 2.
- **`player_turn_2.json`** + **`turn_state_turn_2.json`** + **`checkpoints.json`**
  — n/a, didn't get to turn 2.
- The full Coach LLM stream (the ~25 successful HTTP 200s the Coach made
  before the crash) — only in **llama-swap / llama.cpp logs on
  `promaxgb10-41b1`**. Window: **2026-06-08T20:44:26 → 20:57:45 UTC**.
- The crash itself (`dmesg`, `journalctl -u llama-swap`, kernel OOM
  killer messages). Same forensic recipe as
  [`../run-11-f23-forensics-handoff.md`](../run-11-f23-forensics-handoff.md) §3
  but the discriminator is already known — F23A. The interesting
  GB10-side question is now **what's the OOM threshold**, not which
  class.

## Diagnostic hypotheses for the GB10 session

1. **F23A confirmed via run-16 reproduction** (sibling-to-run-15 turn-2,
   identical failure shape, earlier turn). The 71-file Player payload
   pushed it past the threshold; the 30-file payload in run 15 turn 1
   stayed under it. Run-15 turn 2 (after the synthetic-feedback recovery
   added more context) hit it too.

2. **Operationally, the question is OOM headroom**, not whether F23A
   exists. Per the run-11 F23 forensics handoff §4 decision matrix:
   - **F23A path**: reduce gemma4:31b `n_ctx` OR accept the upper Coach
     payload as the gemma4:31b envelope OR escalate to AC-007
     (nemotron-3-super:120b-a12b on 2nd GB10).
   - The run-15 + run-16 evidence suggests **the F23A envelope is small
     enough that any non-trivial Coach turn risks it**. 30 files OK, 71
     files NOT OK. This codebase's IA03 task is on the edge.

3. **AC-006 / AC-009 cutover decision is now substrate-shaped, not
   schema-shaped.** Architecture works (15 runs of empirical evidence).
   Path 1A (grammar) was a no-op for tool-bound Coach (run 13). Path 1B
   (prompt) on gemma4:26b was insufficient (run 14). gemma4:31b + Path 1B
   produces real verdicts when it can run (run 15 turn 1) but OOMs on
   bigger payloads (run 15 turn 2, run 16 turn 1). Operator decision:
   - **(D-1) Accept 31b + sizing-constrained cutover**: file an
     operator policy that limits Player turn-N payload size such that
     the Coach prompt stays under the F23A threshold. Risk: most real
     codebases produce bigger payloads than IA03 does, so cutover may
     succeed on this feature but fail on the next.
   - **(D-2) Wait for 2nd GB10 + nemotron-3-super (AC-007 escalation)**:
     larger memory envelope solves F23A; better structured-output
     reliability solves F24's residual. Schedule-dependent on hardware ETA.
   - **(D-3) Smaller Coach model with tighter envelope**: try
     gemma4:26b again but with Path 1B + the grammar-via-toolless
     factor (the architectural pivot from run-13's grammar-no-op
     finding). This is a code change in
     [`guardkit/orchestrator/agent_invoker.py`](../../../../guardkit/orchestrator/agent_invoker.py)
     — split Coach into evidence-gathering (tool-using) phase and
     verdict-synthesis (toolless, grammar-enforced) phase. ~1-2 day fix.

## Cross-reference

- **F23A diagnosis** (run-15 GB10 commit): `1ee4baab docs(TASK-OPS-COACH31B): run-15 AC-3 — F24 broken, turn-2 502 discriminated to F23A (global OOM)`
- **TASK-OPS-COACH31B** (the 31B QAT Coach setup): commit `8ed242ae`
- **Original F23 forensics recipe** (still usable for confirming
  same-class on run 16): [`../run-11-f23-forensics-handoff.md`](../run-11-f23-forensics-handoff.md) §3 with time window 20:44:26 → 20:57:45 UTC
- **F24 status update**: this run does NOT add new F24 evidence —
  Coach never got to emit, so the structured-output question is moot
  for this run. F24 is the same shape as last described in
  [`../feature-run-analysis.md`](../feature-run-analysis.md) §6.
- **Run-15 README** (sibling F23A observation):
  [`../run-15-artifacts/README.md`](../run-15-artifacts/README.md) — the
  "breakthrough" Coach verdict + the same F23A failure on turn 2.

## ✅ RESOLVED on the GB10 (2026-06-08) — run-16 OOM is **GPU/unified-memory exhaustion**, ctx + GUI-quiesce were the wrong levers

The GB10 session (TASK-OPS-COACH31B) confirmed run-16 is the same **F23A class**
as run-15, but the forensics **correct two assumptions** about the fix:

**1. It OOM'd at only ~41 GB of process RSS — because the binding constraint is
GPU/unified memory, not CPU RAM.** Kernel (21:59:20 BST):
```
oom-kill: ... global_oom ... task=llama-server,pid=3178822
Out of memory: Killed process 3178822 (llama-server)
   total-vm:118850572kB, anon-rss:36907076kB   ← gemma4-31b
NVRM: ... Out of memory [NV_ERR_NO_MEMORY]
```
Summing **every** process in the OOM table = **41.4 GB anon-rss total** on a
121 GB box. A global OOM at 41 GB RSS is only possible because the model
weights + KV live in **GPU/unified memory** (`-ngl 999`), which is the *same
physical pool* but is **not** counted as process anon-rss. `nvidia-smi` confirms
the real consumers — single llama-server processes holding **27.9 GB and 25.6 GB
of GPU memory** (fleet weights + KV). g31's `total-vm` was 118 GB (its CUDA
mappings) vs anon-rss 36.9 GB — the gap is the GPU-resident portion.

**2. Therefore the two levers tried did NOT address the constraint:**
- **GUI quiescing** (Firefox + GitKraken + extra VS Code were shut for run-16)
  freed **CPU RAM (~3 GB)** — but CPU RAM was never the binding constraint, so
  it could not have helped. (Confirmed: non-model RSS at the OOM was ~3 GB.)
- **g31 `--ctx-size 98304 → 65536`** bounds only g31's *maximum* KV; it does not
  bound (a) the *whole coach31 fleet's* GPU footprint, nor (b) the *actual* KV
  for a given prompt, which scales with the real token count. Run-16's 71-file
  Player payload made the turn-1 Coach prompt large → g31's actual KV grew →
  tipped the unified pool over (g31 anon-rss was 36.9 GB, *larger* than run-15's
  28.7 GB despite the *smaller* ctx cap — proof the driver is payload, not cap).

**The real GPU consumers (coach31 set = qw & g31 & qg & ne):**
| model | ctx | note |
|---|---:|---|
| qwen36-workhorse (Player) | **131072** | huge KV reservation — the largest cheap lever |
| gemma4-31b (Coach) | 65536 | 17.65 GB weights + KV that grows with the prompt |
| qwen-graphiti | 65536 | orchestrator context-loading |
| nomic-embed | 8192 | small |

### Corrected fix levers (cheapest first; supersedes "the envelope is too small")
The 31B *can* fit and converge (run-15 turn-1 proved verdict quality); the
problem is **co-resident GPU headroom on a large Coach prompt**. Effective levers:

- **(A) Smaller Coach: 12B dense QAT** — ~7 GB weights (vs 17.65) + a smaller
  per-token KV → frees ~10 GB *and* is far more payload-tolerant, while still
  12B active (3× the original MoE's 3.8B, so it should keep the F24 fix). The
  highest-value cheap experiment; the task already lists it as the fallback.
- **(B) Trim the Player's ctx for the run** — qw at 131072 is the single biggest
  KV reservation; the IA03-class tasks don't need 131 K. Dropping qw to e.g.
  65536 frees GPU headroom (shared-model caveat: affects other qw users).
- **(C) Cap the Coach prompt** — truncate/budget the player report fed to the
  Coach so a 71-file payload doesn't produce a giant prompt (orchestrator code
  change; overlaps the author's D-3 but cheaper than the full split).

Maps to the operator decisions: **(A)/(C) are cheaper than D-2 (2nd GB10 +
nemotron)**; D-3 (tool-using + toolless-grammar Coach split) remains the
robust-for-real-codebases option but is the heaviest. Recommendation: try **(A)
the 12B dense QAT** as run-17 before escalating to D-2/D-3 — it directly attacks
both the weight footprint and the payload-driven KV that actually caused F23A.

> Note: the original run-16 recipe's "quiesce the GB10 (close GUI apps)" guidance
> was aimed at CPU RAM and is now known to be largely beside the point for this
> failure. The effective "quiesce" target is **GPU/unified memory** — shrink the
> co-resident model fleet / KV, not the desktop.
