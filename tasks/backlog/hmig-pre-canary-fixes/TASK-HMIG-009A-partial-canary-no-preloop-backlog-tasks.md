---
id: TASK-HMIG-009A
title: Partial canary execution — backlog tasks, no pre-loop, no fixture isolation (post-F1)
task_type: validation
status: backlog
created: 2026-05-27T15:30:00Z
updated: 2026-05-27T16:00:00Z
priority: high
complexity: 5
effort_hours: 10    # ~10h GB10 compute (12 runs × ~30-60min each, backlog tasks are smaller than TASK-GLI-004)
parent_task: TASK-HMIG-009
parent_review: TASK-REV-HM09
feature_id: FEAT-HMIG
parent_feature: hmig-pre-canary-fixes
wave: 2
conductor_workspace: hmig-pre-canary-fixes-wave2-1
implementation_mode: manual    # canary execution requires operator monitoring + decision-making
intensity: standard
depends_on:
  - TASK-HMIG-006.4   # Pre-loop adapter migration — required for meaningful SDK-vs-LangGraph comparison
related_tasks:
  - TASK-HMIG-009     # Original spec (this is a scope-narrowed variant)
  - TASK-HMIG-009B    # Full canary (optional polish post-F4)
  - TASK-HMIG-010     # Wave-4 cutover (gated by this task's signal)
tags:
  - canary
  - validation
  - langgraph-migration
  - cutover-decision-input
falsifier: "Aggregate result is interpretable: LangGraph first-pass-success rate is computable across at least 6 LangGraph runs and meets either (a) ≥75% (cutover proceeds on schedule) or (b) <75% with classified failure modes (cutover decision reconsidered with evidence). A null result (no comparison computable, e.g. F1 still bypasses) is the only failure of this task."
---

# Task: Partial canary — backlog tasks, no pre-loop, post-F1

## Description

Scope-narrowed variant of TASK-HMIG-009. Runs as soon as TASK-HMIG-006.4 lands, without waiting on TASK-FIX-WTBC or full F4 closure, to produce comparative SDK-vs-LangGraph signal for the Wave-4 cutover decision.

## Backing model (resolved 2026-05-27)

**Both harnesses use `qwen-coder-next` (Qwen3-Coder-Next FP8)** via llama-swap port 9000 front door — the operator's documented and empirically proven AutoBuild Player model per [`gb10-model-requirements-matrix.md:61`](../../../docs/research/dgx-spark/gb10-model-requirements-matrix.md#L61) (*"Current. Proven with AutoBuild"*) and [`ships-computer-system-arch-intent.md:58, 70, 449`](../../../docs/research/dev-pipeline-system/ships-computer-system-arch-intent.md#L58).

The canary-set.json [(.guardkit/autobuild/TASK-REV-HMIG-canary-set.json)](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) was edited 2026-05-27 to revert the undocumented post-2026-04-29 swap from `qwen-coder-next` to `qwen3-coder-30b`. See `model_choice_correction` block in the canary-set.

**The earlier F2 finding ("local Qwen fails marker contract") is now suspected to be a consequence of running the wrong model**, not a llama-swap parser-config defect. AC-001A below confirms this empirically before committing to the 12-run execution.

## Scope

- **Canary tasks**: 2 backlog tasks that do NOT require fixture-branch isolation (so F4 / TASK-FIX-WTBC is not on the critical path):
  - TASK-FIX-A7D3
  - TASK-DOC-267D
  - Drop TASK-GLI-004 (needs fixture isolation → blocked on TASK-FIX-WTBC; runs only in 009B).
- **Reps per (task, harness)**: 3
- **Total runs**: 2 tasks × 2 harnesses × 3 reps = **12 runs**
- **Pre-loop**: **OFF** (`--no-pre-loop`) — isolates the harness adapter's actual purview (Player-Coach loop).
- **Aggregate metric**: First-pass-success rate per harness, per task, across 3 reps.

## Acceptance Criteria

### Preflight (model + endpoint)

- [ ] **AC-001A** — Confirm `qwen-coder-next` is reachable via the llama-swap front door at `http://promaxgb10-41b1:9000` (SDK path) and `http://promaxgb10-41b1:9000/v1` (LangGraph/OpenAI-compat path). Direct curl smoke against both URLs returns 200 with a non-empty response.
- [ ] **AC-001B** — Replay the design-phase prompt for TASK-FIX-A7D3 directly against the llama-swap `qwen-coder-next` endpoint (no SDK, no orchestrator wrapper). **Observe at least one well-formed `tool_use` block** in the response stream. If observed (expected per prior proof): F2 is confirmed resolved methodologically; proceed to AC-001C. If NOT observed (unexpected, contradicts prior proof): halt this task and file a follow-up parser-config investigation against `qwen-coder-next` specifically.
- [ ] **AC-001C** — End-to-end one-rep smoke under SDK: `guardkit autobuild task TASK-FIX-A7D3 --no-pre-loop` with `GUARDKIT_HARNESS=sdk` reaches at least Coach turn 1 with non-empty `files_modified` in the Player report. If it stalls in the same shape as v2/v3/v5 (zero files, no tool_use), halt and re-investigate.
- [ ] **AC-001D** — End-to-end one-rep smoke under LangGraph: same as AC-001C but with `GUARDKIT_HARNESS=langgraph` (requires TASK-HMIG-006.4 landed and verified per its AC-005).

### Execution

- [ ] **AC-001** — TASK-HMIG-006.4 has landed and merged. Confirmed by running `guardkit autobuild task TASK-FIX-A7D3 --pre-loop` with `GUARDKIT_HARNESS=langgraph` and observing zero `claude_agent_sdk.subprocess_cli` log lines in the design phase (TASK-HMIG-006.4 AC-005).
- [ ] **AC-002** — Canary methodology document updated: [`.guardkit/autobuild/TASK-REV-HMIG-canary-set.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) reflects the 009A scope (2 tasks, 3 reps, 12 runs, `--no-pre-loop`, qwen-coder-next on both harnesses) and notes F4 as out-of-scope for this variant. *(Model swap already applied 2026-05-27 — see `model_choice_correction` block; only scope-narrowing notes need updating.)*
- [ ] **AC-003** — Run the 12 canary executions via [`scripts/canary_validation_runner.py`](../../../scripts/canary_validation_runner.py) (with whatever scope-narrowing flags it needs to accept). Persist artefacts under `.guardkit/autobuild/TASK-HMIG-009A-canary/`.
- [ ] **AC-004** — Compute first-pass-success rate per harness per task per rep. Aggregate metric: LangGraph first-pass-success rate across all 6 LangGraph runs. Document in [`docs/state/TASK-REV-HMIG/canary-analysis.md` §8 (new section)](../../../docs/state/TASK-REV-HMIG/canary-analysis.md).
- [ ] **AC-005** — Decision: does the aggregate metric meet the Wave-4 cutover bar (per TASK-HMIG-009 original AC-007's framing, with F6 caveat applied)? Document the verdict and cite specific evidence.
- [ ] **AC-006** — Cross-link the verdict to TASK-HMIG-010 (cutover task). If verdict is GO, HMIG-010 proceeds on schedule. If NO-GO, escalate to operator for cutover-deadline reconsideration.

### Closing

- [ ] **AC-007** — Document `qwen-coder-next` as the canonical AutoBuild Player model in [`docs/deep-dives/autobuild_local_vllm.md`](../../../docs/deep-dives/) (create if absent) under "Canonical AutoBuild Player model" section, citing `gb10-model-requirements-matrix.md` as source of truth. Explicitly call out that `qwen3-coder-30b` and `qwen36-workhorse` are not AutoBuild Player models.
- [ ] **AC-008** — Capture the model-swap correction in Graphiti (`guardkit__task_outcomes`) so future canary methodology decisions reference Qwen3-Coder-Next by default and the post-2026-04-29 swap is recorded as a non-recurrence target. Cross-reference TASK-REV-HMIG, TASK-REV-HM09, and this task.

## Out of Scope

- **Fixture-branch isolation** — deferred to TASK-HMIG-009B (post-WTBC).
- **TASK-GLI-004 canary task** — needs fixture isolation; runs only in 009B.
- **Pre-loop ON canary** — runs only in 009B once we have data on whether qwen-coder-next satisfies the pre-loop marker contract.
- **Parser-config audit for `qwen3-coder-30b` / `qwen36-workhorse`** — these are not AutoBuild Player models. If a user later wants to add them as additional Player options, file as a separate task; do not bundle here.

## Implementation Notes

The narrowed scope deliberately trades comprehensiveness for unblocked execution. 009A's verdict is the gating input for the cutover decision; 009B is optional polish if 009A's signal is decisive.

The earlier open question ("Sonnet baseline vs local Qwen?") is closed: local Qwen on both sides, because (a) it matches deployed reality, (b) it matches the production architecture's intent, (c) Sonnet baseline historical data is not comparable, and (d) the cutover decision concerns local-substrate behaviour, not Anthropic-API behaviour.

The preflight ACs (001A–001D) are deliberately cheap (<30min total) and front-loaded so that if Qwen3-Coder-Next *also* fails the marker contract (contradicting prior proof), the operator finds out before committing to ~10h of GB10 compute on a doomed run.

## References

- Parent review: [TASK-REV-HM09 review report §6 + §7](../../../.claude/reviews/TASK-REV-HM09-review-report.md#7-ac-007--task-hmig-009-scope-revision-recommendation) (note: §6 has a correction addendum at top of review re: model choice framing)
- Original task: [TASK-HMIG-009 (blocked)](../../blocked/TASK-HMIG-009-canary-validation.md)
- Canary set (post-model-swap): [`.guardkit/autobuild/TASK-REV-HMIG-canary-set.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) — see `model_choice_correction` block
- Source of truth for model choice: [`docs/research/dgx-spark/gb10-model-requirements-matrix.md`](../../../docs/research/dgx-spark/gb10-model-requirements-matrix.md), [`docs/research/dgx-spark/llama-swap-config.yaml`](../../../docs/research/dgx-spark/llama-swap-config.yaml), [`docs/research/dev-pipeline-system/ships-computer-system-arch-intent.md`](../../../docs/research/dev-pipeline-system/ships-computer-system-arch-intent.md)
- Canary runner: [`scripts/canary_validation_runner.py`](../../../scripts/canary_validation_runner.py)
- Pilot analysis (original framing — read with 2026-05-27 correction in mind): [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md)
