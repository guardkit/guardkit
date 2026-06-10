---
id: TASK-PERF-COACHSYNTH
title: Bound the B-full gather context (F20) + Coach verdict-synthesis latency
status: completed
task_type: feature
created: 2026-06-09T00:00:00Z
updated: 2026-06-10T11:02:45Z
previous_state: in_progress
completed: 2026-06-10T12:05:45Z
completed_location: tasks/completed/2026-06/
state_transition_reason: "code complete; AC-1/2/4/6 unit-verified; AC-3 (ops/TASK-OPS-COACH31B) + AC-5 (live GB10 run) tracked as follow-ups"
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

- [x] **AC-1 (gather never overflows)** — *code landed; live falsifier is AC-5.*
  Bounded by a **four-layer defence** (all code, unit-tested):
  1. **Summarisation profile** — `gemma4:31b` registered in
     `guardkitfactory…model_config.MODEL_CONTEXT_WINDOWS` (`ctx_size 98_304`).
     This was the **root cause**: the bare name was absent, so no
     `profile["max_input_tokens"]` was injected and deepagents' summarisation
     used its 170 k fixed fallback (> the 98 k window) → never fired. Now the
     fraction trigger fires before overflow.
  2. **recursion_limit** — `LangGraphHarness(recursion_limit=…)` →
     `agent.ainvoke(config={"recursion_limit": N})`. The gather passes 12
     (env `GUARDKIT_COACH_GATHER_RECURSION_LIMIT`). `max_turns` is dropped on
     the LangGraph substrate, so this is the only hard tool-cycle bound there.
  3. **Per-tool-result truncation** — `TruncatingBackend` caps each
     `read`/`grep`/`execute` result (gather passes 12 000 chars, env
     `GUARDKIT_COACH_GATHER_MAX_TOOL_RESULT_CHARS`).
  4. **Wall-clock budget** — the pre-existing 40 % gather slice.
- [x] **AC-2 (proactive degrade)** — a runaway gather trips the recursion
  ceiling → `GraphRecursionError` → existing `except Exception` degrades to
  B-min within budget (a verdict still emerges). Covered by
  `test_recursion_error_wraps_to_harness_error` +
  `test_gather_failure_degrades_to_bmin`.
- [ ] **AC-3 (g31 resident)** — **OPS, out of code scope.** llama-swap
  keepalive on the GB10 box; tracked under **TASK-OPS-COACH31B**. Not a
  change in either repo.
- [x] **AC-4 (synthesis prompt bounded)** — `_truncate_gather_findings`
  caps the Phase-A findings injected into the synthesis prompt (16 000 chars,
  env `GUARDKIT_COACH_GATHER_FINDINGS_LIMIT_CHARS`), **marked** (respects
  `absence-of-failure-is-not-success.md`). Tests in `TestGatherFindingsTruncation`.
- [ ] **AC-5 (scaling/F20 falsifier)** — **LIVE RUN, out of code scope.**
  Requires a ~165-min FEAT-AOF B-full run on GB10 (and **TASK-FIX-MAXPARALLEL01**
  for clean serial validation). The operator runs this to flip AC-1/AC-6 from
  "code landed" to "empirically validated".
- [x] **AC-6 (substance preserved)** — unit-level: the bounded gather still
  threads findings into the synthesis prompt and populates the
  per-criterion checklist (`test_gather_on_runs_toolbound_then_toolless`,
  `test_gather_call_carries_bounds_synthesis_does_not`). Final confirmation
  is part of the AC-5 live run.

## Implementation (run by /task-work, 2026-06-10)

**Decision (user, strict-checkpoint):** full cross-repo code fix; layered
defence "both equally weighted". AC-3 (ops) + AC-5 (live run) explicitly
deferred — they need the GB10 substrate, not a code change.

**guardkitfactory** (`../guardkitfactory`):
- `harness/model_config.py` — register `gemma4:31b` profile (AC-1 root cause).
- `harness/langgraph_harness.py` — `recursion_limit` ctor param → `ainvoke`
  config (None preserves the historic single-arg call shape).
- `harness/backend_config.py` — `TruncatingBackend` wrapper + opt-in
  `build_autobuild_backend(max_tool_result_chars=…)`.
- `tests/harness/test_gather_bound.py` — 13 new tests.

**guardkit** (this repo):
- `orchestrator/harness/selector.py` — pop + forward `recursion_limit` /
  `max_tool_result_chars` to the LangGraph harness + backend (dropped on SDK).
- `orchestrator/agent_invoker.py` — `_invoke_with_role` accepts/forwards the
  two bounds; gather constants; gather call passes them;
  `_truncate_gather_findings` + its use in `_build_coach_prompt` (AC-4).
- `tests/orchestrator/test_coach_gather_bfull.py` — bound-plumbing + findings
  truncation tests; `tests/orchestrator/harness/test_selector.py` — 4 new
  gather-bound tests (+ corrected two pre-existing wiring-assertion drifts:
  CompositeBackend wrapping, NOPERMS empty list).

**Test status:** guardkitfactory 84 passed / 8 skipped; guardkit selector
(combined env) 28 passed; guardkit coach-gather 25 passed. Broad orchestrator
regression adds **0** new failures vs HEAD (remaining failures are pre-existing
env gaps: `scikit-image`, `langchain_core`, SDK-not-installed Mock attrs).

**Cross-repo install note:** the two repos are co-versioned. `selector.py`
now constructs `LangGraphHarness(recursion_limit=…)` and
`build_autobuild_backend(max_tool_result_chars=…)`; deploy guardkitfactory
with these changes alongside guardkit.

## Notes

- Empirical source: run-22 F20 (`docs/state/TASK-REV-HMIG/run-22-artifacts/`,
  TP05 108 k/98 k); run-20 latency wash (`run-20-artifacts/`).
- **Depends on TASK-FIX-MAXPARALLEL01** to be able to validate serially (the
  `--max-parallel 1` flag is currently ignored).
- Coordinate the GB10/llama-swap side with TASK-OPS-COACH31B (`coach31` set,
  `n_ctx 98304`, keepalive policy).
