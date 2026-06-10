---
id: TASK-PERF-COACHSYNTH
title: Bound the B-full gather context (F20) + Coach verdict-synthesis latency
status: backlog
task_type: feature
created: 2026-06-09T00:00:00Z
updated: 2026-06-10T00:00:00Z
priority: high
complexity: 6
parent_task: TASK-HMIG-010
related: [TASK-ARCH-COACHBFULL, TASK-ARCH-COACHSPLIT, TASK-FIX-COACHTESTTO, TASK-OPS-COACH31B, TASK-FIX-MAXPARALLEL01]
implementation_mode: task-work
intensity: strict
---

# Task: Bound the B-full gather context (F20) + synthesis latency

## Why this task exists (escalated after run-22)

This started as a *latency* task (run-20). Run-21/22 promoted it to a
**correctness/availability** task: the B-full tool-using gather
(TASK-ARCH-COACHBFULL) accumulates context **unboundedly** and **overflows
gemma4:31b's 98,304-token window — F20 returns**, killing the turn.

**Run-22 (FAILED, 2/3, 165 min):** TP05's Coach Phase-A gather ran an agentic
tool-loop for ~19.5 min of successful HTTP 200s, accumulating tool-result
tokens, then:

```
HTTP/1.1 400 Bad Request — request (108094 tokens) exceeds the available
context size (98304 tokens) ... type: exceed_context_size_error
```

COACHBFULL's degrade-to-B-min **fired correctly but too late** — by then the
gather had consumed the 80-min task budget, and CTOUT01 cancelled the B-min
synthesis ~60s in. Net: no verdict, task timeout. (IA03 + GD02 gathers
accumulated less and produced real enriched verdicts — so the failure is
**task-dependent on gather tool-result volume**, not on parallelism.)

This is the **load-bearing B-full failure surface**: every gather tool call
appends tool-result tokens; a long investigation blows the 98 K window. Serial
execution does NOT fix it (the overflow is one request's own context, not
cross-task contention) — it must be bounded **inside** the gather.

The original latency finding still stands as the secondary problem (run-20:
toolless synthesis grew 4m55→7m33→10m05 per task, g31 cold-loading every turn):

| run-20 Coach turn | verdict | synthesis dur |
|---|---|---|
| task 1 | 200, 7954 B | 4m55s |
| task 2 | 200, 9793 B | 7m33s |
| task 3 | 200, 11267 B | 10m05s |

## Levers (Lever A is now the load-bearing one)

- **Lever A — BOUND THE GATHER (primary; fixes F20).** Inside the B-full
  Phase-A gather (`agent_invoker` gather invocation):
  - **Cap tool-cycles** — a hard ceiling on gather round-trips (e.g. ≤3–5).
  - **Cap context growth** — truncate/summarise large tool results before
    they re-enter the prompt (a `read_file` of a 2 k-line file must not dump
    2 k lines of tokens into the running context).
  - **Proactive degrade-to-B-min at a token threshold** — when the gather's
    running context approaches a safe fraction of `n_ctx` (e.g. ~70% =
    ~68 k of 98 k) **OR** a wall-clock budget (e.g. ≤5 min), stop investigating
    and synthesise from what's gathered so far. Degrade **before** F20 fires
    and **before** the task budget is eaten — this is the timing fix for
    COACHBFULL AC-2 (the fallback was correct but late).
- **Lever B — keep g31 resident.** Avoid the per-turn ~50 GB cold-load (between
  Coach turns the Player runs and llama-swap evicts g31). The `coach31` set is
  `qw & g31`; the Player only needs `qw` — pinning g31 across Player turns may
  avoid the switch entirely. Verify the GB10 unified-memory math.
- **Lever C — bound the synthesis prompt.** Extend the existing truncation
  discipline (`_COACH_BDD_DISCOVERIES_LIMIT` etc. in
  `_render_evidence_bundle_section`) to `peer_changed_files`, accumulated
  context, and overall prompt size in `_build_coach_prompt`. Mark truncation
  (respect `absence-of-failure-is-not-success.md`).
- **Lever D — cap generation.** Synthesis-specific `max_tokens` / `reasoning_mode`
  tune if reasoning-content growth (not input) drives the latency.

## Strategic question (worth resolving in design)

A fully-agentic, unbounded tool-loop gather may be **the wrong shape** for a
98 K-context local model. Cheaper shapes that still yielded the IA03/GD02
substance: (a) a **bounded** gather (2–3 *targeted* reads, not an open loop);
(b) run the gather on **qwen36-workhorse (131 K context)** instead of g31;
(c) feed the deterministic bundle + a few targeted snippets to the synthesis
rather than an open investigation. The open question is *how little* gather is
needed to keep `criteria_verification` populated.

## Acceptance criteria

- [ ] **AC-1 (gather never overflows)**: the B-full gather's running context is
  bounded so it **cannot** exceed a safe fraction of `n_ctx`; a gather-heavy,
  F20-prone task (TP05-class) completes with **no `exceed_context_size_error`**.
- [ ] **AC-2 (proactive degrade)**: degrade-to-B-min triggers on a token AND/OR
  wall-clock threshold **before** F20 and **before** task-budget exhaustion —
  verified by a reproducer that drives a runaway gather and asserts the turn
  still produces a verdict within budget. (Closes COACHBFULL AC-2's timing gap.)
- [ ] **AC-3 (g31 resident)**: g31 is not cold-loaded every Coach turn
  (llama-swap log shows no per-turn `evict=[gemma4-31b]` + reload). Report the
  per-turn latency reduction.
- [ ] **AC-4 (synthesis prompt bounded)**: synthesis prompt size is capped,
  truncation marked, per-task verdict latency no longer grows unbounded.
- [ ] **AC-5 (scaling/F20 falsifier)**: a re-run of FEAT-AOF B-full completes
  **3/3** with **no F20** on any task and each gather within budget — the bar
  run-22 (TP05) failed.
- [ ] **AC-6 (substance preserved)**: the bounded gather still produces
  **populated `criteria_verification`** (the run-21/22 IA03/GD02 win must
  survive the bound — don't trade substance for the F20 fix).

## Notes

- Empirical source: run-22 F20 (`docs/state/TASK-REV-HMIG/run-22-artifacts/`,
  TP05 108 k/98 k); run-20 latency wash (`run-20-artifacts/`).
- **Depends on TASK-FIX-MAXPARALLEL01** to be able to validate serially (the
  `--max-parallel 1` flag is currently ignored).
- Coordinate the GB10/llama-swap side with TASK-OPS-COACH31B (`coach31` set,
  `n_ctx 98304`, keepalive policy).
