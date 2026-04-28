---
id: TASK-REV-WORS
title: Diagnose Jarvis FEAT-J004-702C run-3 — DOUBLE failure at Wave 4 (regressed worse than run-2)
status: review_complete
task_type: review
review_mode: diagnostic
review_depth: comprehensive
created: 2026-04-28T09:30:00Z
updated: 2026-04-28T12:30:00Z
priority: critical
tags: [autobuild, review, diagnostic, regression, parallel-contention, sdk-ceiling, timeout-budget, FEAT-J004-702C, urgent, ddd-southwest-blocker]
related_reviews:
  - TASK-REV-FA04   # Closed langchain trapdoor (Wave 1-2 of FEAT-ABSR-9C6E)
  - TASK-REV-9D13   # Closed post-Player-specialist-stall (anchored Wave 1 backlog of FEAT-ABSR-9C6E: CEIL/WALL/FRSH/DIAG/MAXT/MTBC/CMPL)
related_features:
  - FEAT-ABSR-9C6E  # autobuild-stall-resilience (DIAG+MTBC+FRSH merged; CEIL+WALL+MAXT+CMPL pending)
complexity: 0
review_results:
  mode: diagnostic
  depth: comprehensive
  revision: v2
  findings_count: 12
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-WORS-report.md
  completed_at: 2026-04-28T12:30:00Z
  v2_additions:
    - "C4 diagrams (System Context, Container, Component) per [R]evise feedback"
    - "Sequence diagrams across system/technology boundaries (4 diagrams: single SDK turn, Wave-4 cascade, shared-worktree poison, MTBC turn-2 abort)"
    - "Ground-truth run-2 SDK turn counts CONFIRMED via autobuild-FEAT-J004-702C-run-2-history.md (91/92, not 116/141 as a parallel agent mistakenly reported from a checkpoint commit)"
    - "SDK max_turns model-visibility CONFIRMED invisible (refutes 'MAXT raise caused longer iteration' theory)"
    - "Per-turn rate analysis corrected: J004-011 +26.5% (15.1->19.1 s/turn), J004-012 -9% (15.3->13.9 s/turn)"
    - "J004-012 schema regression surfaced: emitted 0 completion_promises in run-3 vs 8 in run-2"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# TASK-REV-WORS — Diagnose run-3 DOUBLE Wave-4 failure (regressed worse than run-2)

## ⏱️ Stakes (read first)

**Blocking development. DDD-SouthWest demo in ~20 days. Two consecutive runs failed. Run-3 regressed _further_** — instead of one Wave-5 failure (run-2), we now have two Wave-4 failures, and Wave 5 is never reached. Autobuild builds jarvis/study-tutor/forge for the demo. **This review must produce an actionable next step, not a leisurely diagnosis.** Scope down ruthlessly if a thread becomes a multi-hour rabbit hole.

## TL;DR

Run-3 of `guardkit autobuild feature FEAT-J004-702C` failed at Wave 4 with **both TASK-J004-011 AND TASK-J004-012** hitting `timeout_budget_exhausted`. In run-2 these tasks succeeded in 1 turn each (91/92 SDK turns); in run-3 they took 116 and 141 SDK turns respectively, with J004-011's Player wall reaching 2215 s of the 2400 s task budget. **Mechanism: unknown. Investigate, don't predict.**

The previous drafts of this brief proposed several mechanisms (model swap, partial state-clear, Graphiti contention, orchestrator-overhead from `87c27e60`) — each was either falsified or unverified during the back-and-forth that produced this brief. **None should be assumed in the actual review.** Start from the data.

## What we know (facts, with sources)

### Run outcomes

- Run-2 (2026-04-27 evening) — 12/20 tasks complete, 1 failure (J004-013 at Wave 5, `timeout_budget_exhausted`, ceiling hit). Diagnosed in [TASK-REV-9D13 v2](../../.claude/reviews/TASK-REV-9D13-report.md). All 6 R1-R6 fixes derived from that review.
- Run-3 (2026-04-28 morning) — 12/20 tasks complete, 2 failures (J004-011 + J004-012 at Wave 4, `timeout_budget_exhausted`, J004-012 ceiling hit). Wave 5 (J004-013) never started. First-attempt pass rate: 67% (run-2: 77%).

### Code state during run-3

- All six R1-R6 fixes from TASK-REV-9D13 v2 merged in commit `87c27e60` ("autobuild fixes") at 2026-04-28 06:49 UTC, before run-3 attempt-3 began. 1347 insertions across `agent_invoker.py` (+90), `autobuild.py` (+131), `specialist_invocations.py` (+9), and 681 lines of new tests.
- Per logs, the new code paths fired correctly:
  - R3 (FRSH) post-Player budget guard fired: `Skipping orchestrator Phase 4/5 (post_player_remaining=184.12s < 600s)`.
  - R6.b (DIAG) heartbeat labels are now `specialist:test-orchestrator` / `specialist:code-reviewer` (was `Player invocation` for both before).
  - FA04's TASK-ABSR-2468 conditional approval fired for parallel-contention test failure on J004-011.

### Operator history for run-3 (per user, 2026-04-28)

Run-3 was the **third attempt** on the same wall-clock day:

1. Attempt 1 (~06:50 UTC): started `--fresh` accidentally, cancelled mid-clear. events.jsonl tail: `Player failed: Unexpected error: Task TASK-J004-013 not found in any state`.
2. Attempt 2 (~07:01 UTC): retried `--resume` — failed because state was partially cleared by attempt-1.
3. **Attempt 3** (~07:30 UTC): retried with `--fresh`, fully reset worktree (terminal log shows `Cleaning previous incomplete state / Cleaned up previous worktree / Reset feature state / Created shared worktree`). **This is the run that completed Waves 1-3 and failed at Wave 4 with both J004-011 and J004-012 timing out.**

So the worktree starting state for the failing run was **clean fresh**, equivalent to run-2's starting state. Partial-clear from attempts 1-2 is not a load-bearing variable. The cancellation-time `Task ... not found in any state` error is a likely-separate orchestrator-cancellation bug worth filing as a sidequest, but not the cause of Wave-4.

### Architecture (corrected from earlier brief draft)

- Player and Coach LLMs run on **Anthropic API** (not local). Unchanged across runs.
- Graphiti uses local vLLM/llama.cpp at `promaxgb10-41b1:8000` (entity extractor) and `:8001` (nomic embeddings).
- Recent activity in [`docs/research/dgx-spark/RUNBOOK-v2-all-llamacpp-architecture.md`](../../docs/research/dgx-spark/RUNBOOK-v2-all-llamacpp-architecture.md) is an architecture migration validation (vLLM → llama.cpp + llama-swap, model downloads/builds), not a sustained inference workload.

### Per-task wall-time deltas (from logs)

| Task | Run-2 SDK turns | Run-2 outcome | Run-3 SDK turns | Run-3 wall (where logged) | Run-3 outcome |
|------|-----------------|---------------|------------------|---------------------------|---------------|
| J004-011 | 91 | ✓ approved | 116 | 2215 s (`SDK invocation complete: 2215.0s, 116 SDK turns (19.1s/turn avg)`) | ✗ timeout |
| J004-012 | 92 | ✓ approved | 141 (HIT) | (similar magnitude, not exactly logged in extracts) | ✗ timeout (ceiling) |

Average per-SDK-turn wall: run-2 ≈ 11.5 s/turn (J004-013 baseline), run-3 J004-011 = 19.1 s/turn. **+66% per-turn delta.**

## What we don't know

These are the open questions for the actual review to answer. **Don't pre-commit to which is the cause.**

1. **Where does the per-SDK-turn slowdown actually accumulate?** Anthropic API round-trip? Tool-call execution? Pre-call prompt construction? Post-call message processing? Other?
2. **Did the Anthropic side change in any way?** Different default model version, different region, different time-of-day load profile, new tool-definition payload, etc.
3. **Did the Player's per-SDK-turn workload itself grow?** Larger prompts (rules bundle, system prompt, promise-format reinforcement reminder, Graphiti context injection)? More tool calls per turn?
4. **Did the runbook activity ([`RUNBOOK-v2-all-llamacpp-architecture.md`](../../docs/research/dgx-spark/RUNBOOK-v2-all-llamacpp-architecture.md)) overlap with run-3 attempt-3** in a way that contended for Graphiti's local vLLM backend? Per-Player-invocation Graphiti context loading would be slower if so.
5. **Is the Graphiti graph state itself slower** (more episodes accumulated, FalkorDB RecursionError fallback path firing more often)?
6. **Is there per-SDK-turn overhead from any path in the `87c27e60` bundle that I missed?** R4's `_calculate_sdk_max_turns` calls `TaskLoader.load_task` — does this fire once per Player invocation, or per SDK turn? Other paths similarly.
7. **Is there per-task-shape variance?** Did J004-011's task definition or its dependencies change between runs? Was wave-4 task content modified?
8. **Is Anthropic API throughput in any way contended by the Player phase invoking subagents (Task tool)** that recursively call back to Anthropic? Did that pattern change?
9. **The state-tracking error during attempt-1 cancellation** (`Task TASK-J004-013 not found in any state`) — is this a real orchestrator bug worth filing as a sidequest review?

### Tertiary hypothesis: per-task semantic change

J004-011's task definition or its dependencies may have been edited between run-2 and run-3 (more ACs, more files in scope, etc.). Should be ruled out by `git diff` of the task files between the two run timestamps.

### Quaternary hypothesis: Anthropic API throughput variance

Time-of-day variance in Anthropic API responsiveness could contribute. Run-3 attempt-3 ran 07:30-09:24 UTC (Tuesday Apr 28 morning UK time, 02:30-04:24 ET — typically low-load). Less likely than backend contention but nonzero.

## How to find out (concrete diagnostic actions)

### A. Time decomposition — where does per-SDK-turn time actually go?

Reproduce one failing task in isolation with debug-preserve enabled, then decompose the wall-time per SDK turn:

```bash
GUARDKIT_LOG_LEVEL=DEBUG \
GUARDKIT_AUTOBUILD_PRESERVE_DEBUG=1 \
guardkit autobuild task TASK-J004-011 --verbose
```

The `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG` env var triggers the path at `agent_invoker.py:2214` which writes rendered prompt + SDK events JSONL to `sdk_debug/turn_<n>/`. From those events, derive per-turn breakdown:

- Time between prompt-sent and first-AssistantMessage (Anthropic round-trip)
- Time between AssistantMessage tool-use blocks and corresponding ToolResult (tool execution)
- Time on instrumentation, log writes, prompt-render

Compare against run-2's preserved debug output for the same task if available (likely not, given `GUARDKIT_AUTOBUILD_PRESERVE_DEBUG` may not have been set then; in that case re-run J004-011 in isolation with a known-good GuardKit version pre-`87c27e60` for baseline).

Estimated cost: ~30-60 min wall per replay; ~30 min analysis per replay.

### B. Pre-`87c27e60` baseline check

Bisect on `87c27e60`. Run a single-task replay of TASK-J004-011 with HEAD checked out at the **parent** of `87c27e60` (i.e., before R1-R6 merged). Same env, same backend, same Anthropic key. If per-SDK-turn rate is back to ~11.5 s/turn → orchestrator-overhead from `87c27e60` is confirmed and the next sub-question is _which_ change inside that 1347-insert bundle is responsible. If per-SDK-turn rate is still slow → cause is OUTSIDE GuardKit (Anthropic API, network, Graphiti backend, machine state).

```bash
git checkout 87c27e60^   # parent of the autobuild-fixes commit
guardkit autobuild task TASK-J004-011 --verbose
git checkout main        # restore
```

This is the cleanest single experiment — it isolates the effect of the bundle without speculation. ~30-60 min.

### C. Graphiti backend overlap check

For attempt-3's wall window (~07:30-09:24 UTC), determine whether any concurrent processes were issuing requests to `promaxgb10-41b1:8000` or `:8001`:

```bash
# On the GB10 host, query the vLLM / llama.cpp request logs for that window
# (specific commands depend on whether vLLM containers were running and their log location)
docker logs <vllm-container> --since 2026-04-28T07:30:00Z --until 2026-04-28T09:24:00Z | head -100
```

If concurrent activity is present, Graphiti context loading may have been slowed by contention. Note that Graphiti is loaded once per Player invocation (not per SDK turn), so this would manifest as a fixed-cost spike at invocation start, not a per-SDK-turn rate change.

### D. Anthropic API variance check

Side-channel: was Anthropic experiencing elevated latency on 2026-04-28 morning UTC? Check status.anthropic.com or any internal API-latency metrics. Time-of-day variance is rare but not impossible.

### E. Task semantic diff check

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/jarvis
git log --since=2026-04-27 --until=2026-04-28 -- tasks/  # any task edits between runs?
git diff <run-2-commit> <run-3-commit> -- tasks/  # full diff of task changes
```

If TASK-J004-011's definition or dependencies grew between runs, the Player has more work per turn.

### F. State-tracking sidequest (file separately)

The `Task TASK-J004-013 not found in any state` error during attempt-1 cancellation is likely a separate orchestrator-cancellation bug. File as TASK-REV-* sidequest (similar to TASK-REV-COSE for the Coach SDK opaque-stderr issue). Out of scope for this review.

### Prioritised order

1. **B first** (pre-`87c27e60` baseline) — single experiment that decisively isolates GuardKit-internal vs external causes. Cheapest signal.
2. **A second** (time decomposition) — if B confirms GuardKit-internal cause, A finds which path.
3. **C, D, E in parallel** if B says external — narrows down where externally.
4. **F separately** — file the state-tracking sidequest review.

**Do not propose orchestrator fixes** until at least B has produced data. The fixes should target the actual mechanism, not a guessed one.

## Status of fixes between run-2 and run-3 (corrected via git log)

**ALL six R1-R6 fixes from TASK-REV-9D13 v2 are merged** in commit `87c27e60 autobuild fixes` at **2026-04-28 06:49 UTC** (35 seconds before the first run-3 attempt began at 06:50:08 UTC). The bundle landed 1347 insertions across `agent_invoker.py` (+90), `autobuild.py` (+131), `specialist_invocations.py` (+9), and 681 lines of new test code across 5 test files.

| Remediation | Status | Where in code |
|-------------|--------|---------------|
| TASK-ABSR-CEIL (R1 skip Phase 4/5 on ceiling-hit) | ✓ MERGED 87c27e60 | `autobuild.py` |
| TASK-ABSR-WALL (R2 cap specialist sdk_timeout) | ✓ MERGED 87c27e60 | `autobuild.py` (cap helper) |
| TASK-ABSR-FRSH (R3 post-Player budget refresh) | ✓ MERGED 87c27e60 | `autobuild.py` (log line `post_player_remaining=...` confirms) |
| TASK-ABSR-DIAG (R6.b heartbeat label) | ✓ MERGED | `specialist_invocations.py`, `agent_invoker.py` (heartbeats now `specialist:test-orchestrator` etc.) |
| TASK-ABSR-MAXT (R4 complexity-scale max_turns) | ✓ MERGED 87c27e60 | `agent_invoker.py` |
| TASK-ABSR-MTBC (R5 env-overridable min-turn-budget) | ✓ MERGED | `autobuild.py:183` |
| TASK-ABSR-CMPL (R6.a Phase-2.5 effective-complexity) | ⏳ backlog (intentionally post-talk) | — |

**Implication**: this is **not a "fixes not yet shipped" diagnosis**. The full TASK-REV-9D13 v2 R1-R6 plan is in production. Run-3 still failed. The new failure mode survives all six fixes — it is structurally different.

## Variables that changed between run-2 and run-3 (revised 2026-04-28 with corrected operator context)

| Variable | Status | Likely impact |
|----------|--------|----------------|
| **qwen3.6-27b runbook concurrent with attempt-3** (runbook started 06:17 UTC; can take 1–2+ hours; attempt-3 ran 07:30–09:24 UTC) | **UNVERIFIED — check for runbook process / log timestamps overlapping with attempt-3** | **Primary suspect.** Graphiti context-loads (per Player/Coach turn) share `promaxgb10-41b1:8000` with the runbook. Contention propagates to per-turn wall time even though Player/Coach themselves run on Anthropic API. |
| **All 6 R1-R6 orchestrator changes merged** (`87c27e60` @ 06:49 UTC) | CONFIRMED merged before run-3 began | Bundle worked correctly per logs. Possible secondary contributor (per-turn overhead from new code paths) but unlikely to explain 66%. |
| **Player/Coach LLM** (Anthropic API) | UNCHANGED — Anthropic API for both runs | NOT a variable. Earlier draft of this brief incorrectly hypothesised a local-model swap; the user has clarified Player/Coach run on Anthropic, not the local qwen models. |
| **Worktree starting state** (clean fresh after attempt-3's `--fresh`) | CONFIRMED clean — terminal log shows "Cleaned up previous worktree / Reset feature state / Created shared worktree" | NOT a variable. Same baseline as run-2 (which also started clean post-FA04-merge). |
| **Cancellation chaos** (attempt-1 `--fresh` accident → cancelled, attempt-2 `--resume` failed, attempt-3 `--fresh` succeeded into the actual failing run) | CONFIRMED by user | Side observation. Suggests a separate orchestrator-cancellation hygiene bug worth filing (the `Task TASK-J004-013 not found in any state` error during attempt-1 cancel) but **not the cause of the Wave-4 failure**. |

**Time ordering**:

```
2026-04-28 05:25 UTC  5ca0a8fb  TASK-REV-9D13 v2 + ABSR-* tasks + qwen3.6 runbook docs
2026-04-28 06:17 UTC  4342e80f  ran qwen3.6 runbook (RESULTS file added) — runbook execution
2026-04-28 06:49 UTC  87c27e60  autobuild fixes (R1-R6 bundled)
2026-04-28 06:50 UTC  ── run-3 attempt 1 begins (--fresh, accidental); cancelled mid-clear
                        ── tail event: "Task TASK-J004-013 not found in any state"
2026-04-28 07:01 UTC  ── run-3 attempt 2 begins (--resume); failed (state partially cleared)
2026-04-28 ~07:30 UTC  ── run-3 attempt 3 begins (--fresh, deliberate); fully resets worktree
2026-04-28 08:27 UTC  ── J004-009 starts (Wave 3 of attempt-3) — observed in events.jsonl
2026-04-28 09:24 UTC  ── J004-011, J004-012 timeout_budget_exhausted (Wave 4 fail)
```

**The Wave-4 failure was attempt-3, on a clean fresh worktree.** The partial-clear from attempts 1-2 was fully reset. So the diagnosis must look at variables OTHER than starting state — primarily the live-model question.

**Side observation worth filing**: the attempt-1 cancellation produced `Player failed: Unexpected error: Task TASK-J004-013 not found in any state`. That's a state-tracking error in the cancellation path. Worth a separate review (TASK-REV-* sidequest, similar to TASK-REV-COSE) but not load-bearing for THIS review.

## Run-3 outcome summary

Source: [`jarvis/.guardkit/autobuild/FEAT-J004-702C/review-summary.md`](../../../jarvis/.guardkit/autobuild/FEAT-J004-702C/review-summary.md) and [`autobuild-FEAT-J004-702C-even-worse.md`](../../../jarvis/docs/history/autobuild-FEAT-J004-702C-even-worse.md) (516 KB, 2898 lines).

| Wave | Tasks | Outcome | Notes |
|------|-------|---------|-------|
| 1 | 4 | ✓ all approved | parity with run-2 ✓ |
| 2 | 5 | ✓ all approved (J004-007/-010 in 2 turns) | parity with run-2 ✓ |
| 3 | 1 | ✓ J004-009 approved (1 turn) | parity with run-2 ✓ |
| 4 | 2 | **✗ BOTH FAILED**: J004-011 timeout (116 turns), J004-012 timeout (141 HIT, ceiling) | **regression**; run-2: both passed |
| 5 | 1 | NEVER STARTED | run-2: failed at this wave; run-3: blocked behind Wave 4 |
| 6,7 | — | NEVER STARTED | — |

**12/20 tasks completed in run-3** (same as run-2 by coincidence — but the failure pattern is worse: earlier wave + more tasks failing). First-attempt pass rate: **67%** (run-2: 77%).

## Diff between run-2 and run-3 for the Wave-4 tasks

| Task | run-2 SDK turns | run-2 outcome | run-3 SDK turns | run-3 wall | run-3 outcome |
|------|-----------------|---------------|------------------|------------|---------------|
| J004-011 | 91 | ✓ approved | **116** | **2215.0 s** (19.1s/turn avg) | ✗ timeout |
| J004-012 | 92 | ✓ approved | **141 HIT** | (similar magnitude) | ✗ timeout (ceiling) |

J004-011 used 25 more SDK turns and 1.16x the wall (vs run-2). At 19.1s/turn × 116 turns = 2215s. Compare run-2's 11.5s/turn × 101 turns = 1158s for J004-013. **Run-3's Player is ~1.66x slower per SDK turn than run-2** for the same task.

J004-012 hit the SDK ceiling at 141 turns — but the documented `TASK_WORK_SDK_MAX_TURNS = 100` (`agent_invoker.py:301`) means a 141-turn run should have hit ceiling at 101. So either (a) the ceiling was raised between runs (env override `GUARDKIT_SDK_MAX_TURNS`?), or (b) MAXT was merged un-noticed, or (c) the "141 HIT" notation in the run-3 summary means something different than I'm reading.

## Source artefacts (read these in order)

1. **Run-3 review summary** (canonical outcome): `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/FEAT-J004-702C/review-summary.md`
2. **Run-3 events.jsonl** (canonical timing): `/Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/FEAT-J004-702C/events.jsonl`
3. **Run-3 history** (full log, 516KB / 2898 lines): `/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/history/autobuild-FEAT-J004-702C-even-worse.md`
4. **Per-task artefacts** (under `.guardkit/worktrees/FEAT-J004-702C/.guardkit/autobuild/TASK-J004-011/` and `.../TASK-J004-012/`):
   - `player_turn_1.json` — SDK turns used, ceiling-hit flag, files_modified, completion_promises
   - `coach_turn_1.json` — decision, validation_results (parallel_contention classification), independent_tests
   - `task_work_results.json` — phase completion state, agent_invocations
   - `specialist_results.json` — Phase 4/5 status (likely `skipped: budget exhausted` for J004-011, similar for 012)
   - `turn_state_turn_1.json` — turn-state snapshot
   - `checkpoints.json` — worktree checkpoints
5. **Comparison: run-2 artefacts** (already analysed in TASK-REV-9D13 v2): same paths but in earlier worktree state. Use for J004-011/012 success-vs-failure structural diff.
6. **TASK-REV-9D13 v2 report**: [`.claude/reviews/TASK-REV-9D13-report.md`](../../.claude/reviews/TASK-REV-9D13-report.md) — full prior diagnosis with C4 + 3 sequence diagrams; identifies the post-Player-specialist-stall class of defect anchored on J004-013. **The new failure mode is structurally different** but builds on the same orchestrator subsystem.

## What the run-3 logs already show (do not re-investigate, build on)

Pre-extracted highlights from `autobuild-FEAT-J004-702C-even-worse.md`:

```
[J004-011 SDK invocation complete: 2215.0s, 116 SDK turns (19.1s/turn avg)]
[J004-011] Skipping orchestrator Phase 4/5 (post_player_remaining=184.12484687499818s < 600s)
Independent test verification failed for TASK-J004-011 (classification=parallel_contention, confidence=high)
Conditional approval for TASK-J004-011: parallel contention failure (wave_size=2), all Player gates passed.
Requirements not met for TASK-J004-011: missing ['uv run mypy ... strict-clean.', 'lint/format checks with zero errors.']
Timeout budget exhausted for TASK-J004-011 at turn 2: remaining=164.5s < min=600s
✗ TASK-J004-011: FAILED (1 turn) timeout_budget_exhausted
✗ TASK-J004-012: FAILED (1 turn) timeout_budget_exhausted
```

**Heartbeat labels are now correct** (`specialist:test-orchestrator`, `specialist:code-reviewer`) — confirms TASK-ABSR-DIAG merged.

**TASK-ABSR-2468's conditional approval branch fired** for the parallel_contention test failure — that's _correct behaviour_, not the bug. The bug is upstream: Player wall ate 2215s of 2400s budget.

**Side observation worth surfacing**: an earlier abort attempt (run-3 first try at 06:50:08) failed with `Player failed: Unexpected error: Task TASK-J004-013 not found in any state`. The user re-ran (07:01:46) which then progressed through Waves 1-3 cleanly but failed at Wave 4. **The state-tracking error in the first attempt is a SEPARATE orchestrator bug** worth a tertiary note (potentially a sidequest review like TASK-REV-COSE was for the Coach SDK opaque-stderr).

## Goal — produce a diagnostic report that answers these questions

1. **Why is run-3's Player ~1.66x slower per SDK turn than run-2's?** (19.1 s/turn vs 11.5 s/turn)
   - Local vLLM backend slower under contention?
   - Player doing more work per turn (worktree state accumulation)?
   - Some path slowed down by DIAG/MTBC/FRSH merge (regression)?
   - Network / Tailscale latency to `promaxgb10-41b1` backend?

2. **Why did J004-011 (run-2: 91 turns/success) need 116 turns in run-3?** Did the task semantics change, or is the Player approaching the same problem differently?
   - `git log` of `jarvis/tasks/design_approved/TASK-J004-011-*.md` between runs
   - Compare Player completion_promises run-2 vs run-3 for same AC IDs
   - Check whether J004-011 has had its acceptance criteria expanded between runs

3. **Why did J004-012 reach 141 SDK turns when the documented ceiling is 100?**
   - Env var `GUARDKIT_SDK_MAX_TURNS` set in user environment? (`echo $GUARDKIT_SDK_MAX_TURNS`)
   - MAXT actually merged but not yet flagged in README? (`git log -- guardkit/orchestrator/agent_invoker.py | head -20`)
   - Different code path that bypasses the ceiling?

4. **Is parallel-contention the dominant amplifier?** Wave 4 has worker_count=2; Wave 2 has worker_count=5 (more parallel) but those finished cleanly. What's structurally different between Wave 2 and Wave 4 that makes parallelism kill Wave 4?
   - Hypothesis: Wave 4 tasks J004-011/012 are dispatch.py / capabilities.py work which has high test surface area (1884 tests in run-2 specialists). Each Player invocation may be reading/writing many files concurrently, contending on disk + LLM context.
   - Counter-hypothesis: Wave 2 tasks were simpler in ACs and dependencies; the contention is independent of wave size, more about per-task complexity.

5. **Is the state-tracking error in the first abort attempt** (`TASK-J004-013 not found in any state`) a separate bug worth filing?
   - Likely yes; quick triage to confirm.

6. **Decision: should TASK-ABSR-CEIL and TASK-ABSR-WALL be shipped today as emergency fixes?**
   - They don't target this exact failure mode, but they reduce the surface area for J004-013-style failures (ceiling-hit + uncapped specialist).
   - Risk of shipping them: the regression test surface (35 mocked tests) covers them, low risk.
   - Risk of NOT shipping them: if Wave 4 _does_ get past, Wave 5 will repeat the J004-013 failure.

7. **What additional fix is needed for the Wave 4 parallel-contention timeout?** Candidate options to evaluate:
   - **(a) Reduce `worker_count`** for Wave 4 to 1 (sequential) — simplest; eliminates contention; doubles wall but fits in budget per task.
   - **(b) Backend-aware `task_timeout` scaling** — when local backend + `wave_size > 1`, multiply `task_timeout` by some factor (already 4x for local vs Anthropic; perhaps 5x or 6x when contended).
   - **(c) Per-Wave timeout multiplier** — `task_timeout × wave_parallelism × backend_multiplier`.
   - **(d) Cancel-and-retry-sequential on parallel-contention** — when Coach classifies parallel_contention, cancel the wave's other in-flight tasks, restart the wave with worker_count=1.

Pick the highest-leverage option, scope to GuardKit-only, propose with regression-test surface and env-var circuit breaker.

## Investigation scope

### Primary thread — Wave 4 wall-clock reconstruction

1. Read `events.jsonl` for run-3, tabulate exact start/end timestamps for J004-011 and J004-012.
2. Cross-reference with `task_work_results.json` for each, especially `sdk_turns` (used/max/ceiling_hit), `phase_3.completed`, files_modified diff between run-2 and run-3.
3. Compute per-task wall: was J004-011 actually 2215s (per the log line) or shorter? Was J004-012 similarly stretched?
4. Identify the wall-clock segment that grew between run-2 and run-3.

### Secondary thread — Player-loop turn-rate regression

1. 11.5s/turn (run-2) vs 19.1s/turn (run-3) for J004-011. **66% slowdown per turn.**
2. Hypotheses:
   - Backend latency under contention (parallel_contention failure was classified for tests; could be inference too)
   - Worktree state has accumulated cruft from prior runs that slows file ops
   - Some recently-merged path (DIAG/MTBC/FRSH/2468/etc.) added per-turn overhead
3. Ruling-out test: read the run-2 history at the same J004-011 invocation and compute per-turn s for an apples-to-apples comparison.

### Tertiary thread — what's "141 HIT" actually mean for J004-012?

1. Read `task_work_results.json:sdk_turns` for J004-012 in run-3.
2. If `max_turns: 150`, MAXT was merged. If `max_turns: 100`, then "141 HIT" is misreporting OR an env override.
3. Either way: J004-012 needed 141 turns in run-3 (vs 92 in run-2) — independent confirmation of the per-turn slowdown.

### Quaternary thread — state-tracking bug (`Task TASK-J004-013 not found in any state`)

1. Quick triage to determine the cause. Likely `feature_orchestrator.py` or `state_tracker.py` reads task state, fails to find J004-013 even though it exists.
2. May be a side-effect of running autobuild a second time without cleanup between runs.
3. File as a separate review (TASK-REV-* sidequest) if scope is significant.

## Acceptance criteria

- [ ] Diff between run-2 and run-3 wall times reconstructed for J004-011 and J004-012, with line-level evidence from `events.jsonl` and `even-worse.md` history.
- [ ] Root cause for the per-turn slowdown identified (backend contention vs worktree state vs merge regression vs other), with falsifiable evidence.
- [ ] J004-012's "141 HIT" SDK-turn behaviour explained (env override, code path, or other) with file:line evidence.
- [ ] Decision documented: ship CEIL+WALL today as emergency fixes? Yes/no with rationale.
- [ ] If yes (or in any case), identification of the **single highest-leverage fix** for the new Wave 4 failure mode, with proposed task ID, ~10-line code sketch, regression test surface, and env-var circuit breaker.
- [ ] State-tracking error triaged — separate review filed if real bug, or marked transient if not.
- [ ] Cross-referenced with TASK-REV-9D13 v2's R1-R7 to identify which (if any) need re-prioritisation given run-3 evidence.
- [ ] No changes proposed to the Jarvis repo — fixes must live in GuardKit (same constraint as TASK-REV-FA04 and TASK-REV-9D13).
- [ ] Report saved to `.claude/reviews/TASK-REV-WORS-report.md` (per `/task-review` convention).
- [ ] If a thread becomes a multi-hour rabbit hole (e.g., "is the backend slower under contention" requires running benchmarks), **scope down to actionable subset and file follow-ups**. Do not block on ground-truth experiments.

## Out of scope

- Resuming the Jarvis autobuild — that's a tactical decision once this review identifies the right next step.
- Re-investigating the langchain trapdoor (closed by TASK-REV-FA04 + ADR-ARCH-010-rev2; confirmed working in Waves 1-3 of run-3).
- Re-investigating the J004-013 post-Player-specialist-stall (closed by TASK-REV-9D13 v2; CEIL+WALL still pending merge).
- Implementing fixes — that comes via follow-up `/task-create` + `/task-work` from this review's recommendations. Per the review-task convention, recommendations land in FEAT-ABSR-9C6E or a new feature folder if the new failure mode warrants its own.
- Phase-2.5 complexity heuristic enhancement (TASK-ABSR-CMPL) — already filed; re-evaluate priority based on this review's outcome but don't re-spec.

## Suggested workflow

```bash
/task-review TASK-REV-WORS --mode=diagnostic --depth=comprehensive

# Read order recommended:
# 1. /Users/richardwoollcott/Projects/appmilla_github/jarvis/.guardkit/autobuild/FEAT-J004-702C/events.jsonl  (canonical timing)
# 2. .guardkit/worktrees/.../TASK-J004-011/{player_turn_1, coach_turn_1, task_work_results, specialist_results}.json
# 3. .guardkit/worktrees/.../TASK-J004-012/{... same set ...}.json
# 4. The run-3 history (use grep for specific task IDs / events; do NOT read the whole 2898-line file linearly)
# 5. Cross-reference TASK-REV-9D13 v2 §1.1 wall-clock table for run-2 baseline
#
# Use Grep/Read across guardkit/orchestrator/{autobuild.py, agent_invoker.py, feature_orchestrator.py}
# to verify what's merged vs what's still backlog. Specifically:
#   - Is the post_player_remaining recomputation in autobuild.py? (R3 FRSH check)
#   - Has TASK_WORK_SDK_MAX_TURNS changed? (MAXT check)
#   - Are CEIL+WALL still absent? (R1+R2 check)
#
# Produce the report; surface checkpoint for [A]ccept / [I]mplement / [R]evise.
```

## Notes for the reviewer

- TASK-REV-9D13 v2 went through a v1→v2 revision because v1 had inferential gaps. **Be falsifiable from the start.** Quote file:line evidence; mark each claim CONFIRMED/REFUTED/UNVERIFIED.
- C4 + sequence diagrams (Mermaid) were valuable in TASK-REV-9D13 v2 — replicate the format if it helps disambiguate the new failure shape.
- Graphiti context: the `guardkit__project_decisions` group has the `post-player-specialist-stall` class of defect (anchored by TASK-REV-9D13). The new failure may anchor a sibling class — `parallel-contention-amplified-player-timeout` — or may be a more general parameter-tuning issue.
- This review is `task_type: review` and is expected to take ≤2 hours of focused work. Stakes-aware: the user explicitly said "we can't afford to keep blocking development". **If the answer is "ship CEIL+WALL now and re-run, decide more after data", say that clearly and stop.** Don't over-investigate.
- The user has been chasing this incident class for two consecutive nights. Be empathetic to the framing: "what's the one thing I should do right now?" beats "here's a 7-fix roadmap" if the one thing unblocks the demo.
