---
id: TASK-HMIG-013
title: Stage 1 — Swap Coach to gemma4:26b on existing single GB10 to close F17 substrate gap
status: completed
resolution: superseded
superseded_by: TASK-OPS-COACHMOE01
completed_location: tasks/completed/autobuild-harness-migration/
relocated: 2026-06-18  # file moved backlog/ -> completed/ to match its completed status (gemma4:26b coach is in production use)
task_type: bug
created: 2026-06-06T11:00:00Z
updated: 2026-06-11T17:35:00Z
priority: critical
complexity: 4
deadline: 2026-06-15
parent_review: TASK-REV-HMIG
parent_task: TASK-HMIG-010
feature_id: FEAT-HMIG
parent_feature: autobuild-harness-migration
wave: 3
implementation_mode: task-work
intensity: standard
effort_hours: 2
blocks:
  - TASK-HMIG-011  # cutover ceremony — must work before this fires on 2026-06-15
falsifier: "After landing, run N of `guardkit autobuild feature FEAT-AOF --fresh` (with Coach routed to gemma4:26b via llama-swap, Player still on qwen36-workhorse): Coach verdict-emission rate ≥95% across 6+ Coach turns. The substrate F17 finding moves from 'load-bearing constraint' to 'no longer fires' or 'fires <5% of turns'. Wave 1 IA03 completes within 50-min task budget."
tags:
  - autobuild
  - langgraph-migration
  - substrate-quality
  - coach
  - cutover-prerequisite
---

# Task: Stage 1 — swap Coach to gemma4:26b on existing GB10

> **SUPERSEDED 2026-06-11 by TASK-OPS-COACHMOE01** (evidence:
> [`docs/state/TASK-OPS-COACHMOE01/README.md`](../../../docs/state/TASK-OPS-COACHMOE01/README.md)).
> This task was written 2026-06-06 against the **pre-COACHSPLIT tool-bound Coach
> loop** (the F17 substrate gap). TASK-ARCH-COACHSPLIT (D-3) then removed the
> tool-bound loop from the verdict path, so the original framing no longer
> applies. COACHMOE01 evaluated gemma4:26b as Coach on the shipped **B-min
> toolless+grammar** path and delivered this task's unrun AC-006 live smoke:
> a FEAT-AOF `--fresh` run with Coach=gemma4:26b approved **3/3** with honest,
> substantive verdicts and caught real Player dishonesty.
>
> **Falsifier outcome (honest):** the strict "≥95% verdict-emission across 6+
> Coach turns" bar was **not cleanly met** — **5/6 turns emitted a natural valid
> verdict (83%); 1 (GD02 t1) was malformed and recovered by the COACHSF01 safety
> net** (100% effective emission). IA03 took 3 turns / ~58 min (exceeding the
> 50-min single-turn budget) due to **Player** honesty drift + a `test-orchestrator`
> SPECHANG, not the Coach. Net: gemma4:26b is a **viable B-min Coach** (substrate
> question answered), but the production-default-swap / cutover decision
> (TASK-HMIG-011) should weigh the 1/6 GBNF-emission caveat — keep g31 as the
> higher-reliability fallback. Full evidence + decision:
> [`docs/state/TASK-OPS-COACHMOE01/README.md`](../../../docs/state/TASK-OPS-COACHMOE01/README.md).

## Why this task exists

Runs 1-6 of FEAT-AOF empirically demonstrated that:

- **Migration mechanics: COMPLETE** — every F1-F19 finding closed and validated
- **Substrate quality: LOAD-BEARING CONSTRAINT** — qwen36-workhorse Coach verdict-emission ~67% reliable per run-5 sample; even with COACHOUT01 Shape A's simpler fenced-JSON contract (run 6), Coach still produced 602 chars of prose without the JSON block on turn 1
- **Hard cutover deadline**: 2026-06-15 (Anthropic Agent SDK subscription access ends)
- **No API budget**: pay-per-token cloud APIs (Sonnet, GPT, etc.) are not viable
- **Local-only substrate**: must run on operator's own hardware

The 2× DGX Spark + ConnectX-7 setup is incoming but invoice-pending. We **cannot wait** for that hardware to ship the cutover. The mechanical migration is done; we need a substrate that actually works on the existing single GB10 before 2026-06-15.

The Exxact DGX Spark benchmark ([source](https://www.exxactcorp.com/blog/benchmarks/benchmarking-local-ai-agents-on-nvidia-dgx-spark)) tested gemma4:26b at:

- **17/17 perfect agentic score** (T1-T17 structured tests including JSON discipline, tool calling, argument validation)
- **52.7 tokens/sec** (3× faster than qwen36-workhorse on equivalent reasoning load)
- **4-hop chain depth** (sufficient for Player↔Coach turn convergence)
- **26B MoE — single-GB10 deployable** (no hardware change needed)

The Exxact benchmark's load-bearing observation:

> *"The fastest models were not automatically the best agent models. Smaller, faster variants showed benchmark inconsistencies, while larger models demonstrated superior multi-hop stability."*

This **directly matches** our F17 symptom. qwen36-workhorse (~35B class) is fast but variance-prone; gemma4:26b scored perfectly on the exact JSON-emission tests we've been failing.

## Scope

**Route only Coach to gemma4:26b**. Keep Player on qwen36-workhorse where run 4 proved it works (14/14 doc-level exclusion tests passing on turn 1). This is the cheapest, most surgical experiment — if it works, F17 closes immediately.

If gemma4:26b proves insufficient for Coach reliability, the Wave-2 fallback is `nemotron-3-super:120b-a12b` (17/17 + 6-hop depth, 16.4 tok/s — slower but more reliable for long agent loops).

## Acceptance Criteria

- [x] **AC-001: COMPLETE 2026-06-06.** `gemma4-coach` registered on llama-swap at alias `gemma4:26b`. Cold-loaded in ~31s on `localhost:5801`. Alias routing verified — `model="gemma4:26b"` resolves to `gemma4-coach` (server echoes `"model": "gemma4-coach"`). Memory-neutral rotation: architect-agent → gemma4-coach in preload, `arch` matrix.set added for on-demand `/system-arch` flows. Critical config: `--reasoning off` is load-bearing (without it, base Gemma 4 IT routes generation to `reasoning_content` instead of `content` — same disease as F17, different drug). See `docs/research/dgx-spark/AUTOBUILD-ON-LLAMA-SWAP-findings.md` §9.13 for the full operational record.
- [x] **AC-002 (preliminary): COMPLETE 2026-06-06.** 5/5 fenced-JSON emission on short Coach-shape prompts via alias `gemma4:26b`. `finish_reason: stop`, `reasoning_content` empty, content contains fenced JSON block, ~34 completion_tokens each. Posture exactly matches the Exxact benchmark's 17/17 prediction. **NOTE**: Full AC-002 (run-6 turn-1 Coach prompt replay — longer + more complex context) is operator-driven follow-on; the substrate posture is correct, the full replay is recommended as a final gate before AC-006 live smoke.
- [ ] **AC-003**: Extend `MODEL_CONTEXT_WINDOWS` registry in guardkitfactory's `model_config.py` to include `"gemma4:26b": 65536` (the ctx-size configured on the llama-swap side; matches the new gemma4-coach `--ctx-size 65536`). Sibling of qwen36-workhorse entry from TASK-HMIG-002R-MODEL-PROFILE.
- [ ] **AC-004**: Wire per-role model selection. Two-part cross-repo work:
  - **guardkitfactory**: Extend `LangGraphHarness._resolve_model_for_invoke` to accept a per-role override map. When `role='coach'` AND a `coach_model` was supplied, route to it; otherwise fall through to existing default.
  - **guardkit**: Add `--coach-model` Click option to `guardkit autobuild feature` subcommand (and `task`). Mirrors `--model` pattern from TASK-FIX-LGFM (commit `683823cc`). Thread through `FeatureOrchestrator → AutoBuildOrchestrator → AgentInvoker._coach_model_name`. `AgentInvoker.invoke_coach` passes `coach_model_name` (with fallback to `_model_name`).
- [ ] **AC-005**: Regression test: assert that when CLI is invoked with `--model qwen36-workhorse --coach-model gemma4:26b`, `role='coach'` and `role='coach_test'` invocations resolve to `gemma4:26b` while `role='player'` and specialist invocations resolve to `qwen36-workhorse`. Pin both SDK harness and LangGraph harness paths.
- [ ] **AC-006**: Live smoke (HMIG-010 run N): `guardkit autobuild feature FEAT-AOF --fresh --model qwen36-workhorse --coach-model gemma4:26b` under `GUARDKIT_HARNESS=langgraph`:
  - Coach verdict-emission rate ≥95% across 6+ Coach turns (the falsifier from this task)
  - At least one Wave 1 task reaches APPROVED state
  - F17 either does not fire OR fires <5% of turns (COACHSF01 safety net remains as defence-in-depth)
- [ ] **AC-007**: If AC-006 passes: update TASK-HMIG-010 verdict to GO and unblock TASK-HMIG-011. If AC-006 fails: re-run with `--coach-model nemotron-3-super:120b-a12b` as fallback (requires registering `nemotron-3-super:120b-a12b` on llama-swap first, sibling of §9.13 pattern). If that also fails: file substrate escalation to TASK-HMIG-012 (Stage 2 with new hardware).

## Implementation Notes

- The per-role model routing is the load-bearing change. `MODEL_CONTEXT_WINDOWS` already supports per-model entries from 002R-MODEL-PROFILE; this extends with per-role overrides at invocation time.
- Coach invocations identify themselves via `role='coach'` or `role='coach_test'` at `_invoke_with_role` call sites (see `agent_invoker.py:2855` and `coach_validator.py` test execution path).
- COACHOUT01's Shape A parser is substrate-agnostic by ADR FB-004 — gemma4:26b will work with the existing parser without modification. The benefit of swapping models is fewer F17 events for COACHSF01 to handle.
- Operator may want to also try Player on `nemotron-3-super:120b-a12b` if multi-turn iteration drift (F6) persists. Out of scope for this task — file separately if needed.

## References

- Exxact benchmark (load-bearing evidence for the model choice): [Exxact DGX Spark benchmark — NemoTron, Qwen 3.5, Gemma4](https://www.exxactcorp.com/blog/benchmarks/benchmarking-local-ai-agents-on-nvidia-dgx-spark)
- Spark Arena LLM leaderboard: [spark-arena.com](https://spark-arena.com/)
- NVIDIA DGX Spark / GB10 forum: [forums.developer.nvidia.com](https://forums.developer.nvidia.com/c/accelerated-computing/dgx-spark-gb10/719)
- F17 root cause: [`docs/state/TASK-REV-HMIG/feature-run-incidents.md`](../../../docs/state/TASK-REV-HMIG/feature-run-incidents.md) I-007
- Run-6 evidence (Shape A confirmed working, substrate still F17): [`docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-6.md`](../../../docs/reviews/autobuild-migration/autobuild-FEAT-AOF-run-6.md)
- MODEL_CONTEXT_WINDOWS precedent: TASK-HMIG-002R-MODEL-PROFILE (guardkitfactory)
- Stage 2 follow-on: [TASK-HMIG-012](TASK-HMIG-012-substrate-investigation-2x-spark.md)
- Blocked task: [TASK-HMIG-011](TASK-HMIG-011-cutover-ceremony-flip-default-harness.md) (cutover ceremony)

## Notes

- This task is the **cheapest path to a working cutover before 2026-06-15**. No hardware change. Single config edit + harness routing + regression test. ~2h.
- If gemma4:26b works for Coach, the cutover ships on schedule with autobuild functional. Stage 2 (TASK-HMIG-012) becomes optimization rather than necessity.
- If gemma4:26b doesn't work, we still have ~9 days to escalate to nemotron-3-super:120b-a12b on single GB10 or wait for the 2× Spark hardware for Stage 2 candidates.
- COACHOUT01's Shape A architecture is preserved — this task doesn't change Coach contracts, just changes which model the Coach role routes to. The ADR FB-004 invariant (Coach is read-only-for-code; orchestrator parses verdict from fenced JSON) is unchanged.
