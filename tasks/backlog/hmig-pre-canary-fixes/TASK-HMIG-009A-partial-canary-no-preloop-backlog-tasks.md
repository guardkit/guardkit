---
id: TASK-HMIG-009A
title: Partial canary execution — backlog tasks, no pre-loop, no fixture isolation (post-F1)
task_type: validation
status: blocked
previous_state: backlog
state_transition_reason: "AC-001A preflight BLOCKER — qwen-coder-next not deployed on live GB10 llama-swap (config drift). Engineering prep (AC-002/003-runner/004-scaffold/007/008) complete; the 12-run batch + GO/NO-GO are gated on the operator deploying the model. See Status section."
created: 2026-05-27T15:30:00Z
updated: 2026-05-27T17:30:00Z
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

- [x] **AC-001A** — ⛔ **EXECUTED → FAIL (BLOCKER).** `qwen-coder-next` is **NOT** reachable via the live llama-swap front door. `GET :9000/v1/models` omits the alias; a completion returns "could not find suitable inference handler"; port 8002 refuses connection (`qwen3-coder-30b` answers fine). The model exists only in the HISTORICAL `llama-swap-config.yaml`, not in the live source-of-truth runbook. See canary-set `preflight_findings` + canary-analysis §8.3. Halts AC-001B→D and AC-003 until the operator deploys the model on the GB10.
- [ ] **AC-001B** — ⏸️ Blocked on AC-001A (cannot replay against a 404 endpoint). Per this AC's own halt clause, stop until the model is exercisable. Replay the design-phase prompt for TASK-FIX-A7D3 directly against the llama-swap `qwen-coder-next` endpoint (no SDK, no orchestrator wrapper). **Observe at least one well-formed `tool_use` block** in the response stream. If observed: F2 confirmed resolved methodologically; proceed to AC-001C. If NOT observed: halt and file a follow-up parser-config investigation against `qwen-coder-next` specifically.
- [ ] **AC-001C** — ⏸️ Blocked on AC-001A. End-to-end one-rep smoke under SDK: `guardkit autobuild task TASK-FIX-A7D3 --no-pre-loop` with `GUARDKIT_HARNESS=sdk` reaches at least Coach turn 1 with non-empty `files_modified` in the Player report. If it stalls in the same shape as v2/v3/v5 (zero files, no tool_use), halt and re-investigate.
- [ ] **AC-001D** — ⏸️ Blocked on AC-001A. End-to-end one-rep smoke under LangGraph: same as AC-001C but with `GUARDKIT_HARNESS=langgraph` (requires TASK-HMIG-006.4 landed and verified per its AC-005).

### Execution

- [x] **AC-001** — TASK-HMIG-006.4 has landed and merged (commit `f2c240a7`). Routing confirmed at code level (`task_work_interface._execute_via_sdk` routes through `select_harness()`, zero direct `claude_agent_sdk` imports) and via its CI falsifier test `test_langgraph_design_phase_never_calls_sdk` (99 passed). The **live** pre-loop langgraph smoke (zero `claude_agent_sdk.subprocess_cli` lines) is deferred behind the AC-001A model blocker (it would 404 before producing signal); the CI test already asserts the same falsifier deterministically.
- [x] **AC-002** — ✅ Canary set updated: [`.guardkit/autobuild/TASK-REV-HMIG-canary-set.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) gained a `task_hmig_009a_scope` block (2 tasks, 3 reps, 12 runs, `--no-pre-loop`, F4 out-of-scope, qwen-coder-next on both harnesses) and a `preflight_findings` block recording the AC-001A blocker. GLI-004 retained in `canary_tasks[]` (009 spec AC-001) but excluded from the 009A allowlist.
- [ ] **AC-003** — 🟡 **Runner prepped; batch BLOCKED on AC-001A.** [`scripts/canary_validation_runner.py`](../../../scripts/canary_validation_runner.py) gained `--variant 009a` (2-task allowlist, 12-run plan, dedicated `TASK-HMIG-009A-canary` output namespace) + a generic `--exclude-task`. Dry-run verified (12 runs, correct namespace). Operator runs `python scripts/canary_validation_runner.py --variant 009a` **once the model is deployed**. Artefacts persist under `.guardkit/autobuild/TASK-HMIG-009A-canary/`.
- [ ] **AC-004** — 🟡 §8 scaffolded in [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md) (scope, dependency status, AC-001A blocker, results/verdict placeholders). Metrics auto-populate via `--variant 009a --aggregate` after the batch runs.
- [ ] **AC-005** — ⏸️ Decision pending data (blocked on AC-001A → AC-003). Framing recorded in §8.6.
- [ ] **AC-006** — ⏸️ Cross-link pending verdict (blocked). Framing recorded in §8.7. As of 2026-05-27, TASK-HMIG-010 has no 009A signal yet.

### Closing

- [x] **AC-007** — ✅ Created [`docs/deep-dives/autobuild_local_vllm.md`](../../../docs/deep-dives/autobuild_local_vllm.md) with "Canonical AutoBuild Player model" section citing `gb10-model-requirements-matrix.md`; explicitly calls out `qwen3-coder-30b` and `qwen36-workhorse` as **not** AutoBuild Player models; includes a "Live deployment status (2026-05-27)" caveat documenting the config drift.
- [x] **AC-008** — ✅ Captured in Graphiti (`guardkit__task_outcomes`): canonical model = qwen-coder-next, post-2026-04-29 swap recorded as non-recurrence target, plus the live-deployment-gap finding. Cross-references TASK-REV-HMIG, TASK-REV-HM09, TASK-HMIG-009A, -006.4, -009B, -010.

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

## Status (2026-05-27)

**BLOCKED at AC-001A** — `qwen-coder-next` is not deployed on the live GB10 llama-swap. All engineering/documentation prep that is invariant to the model is complete; the compute batch and the GO/NO-GO decision are gated on the operator clearing the substrate blocker.

### ✅ Done (substrate-independent)

- **AC-002** — canary-set scope + preflight-findings blocks.
- **AC-003 (runner)** — `--variant 009a` + `--exclude-task` flags; dedicated `TASK-HMIG-009A-canary` output namespace; dry-run verified (12 runs). Runner compiles; legacy 18-run behaviour preserved.
- **AC-004 (scaffold)** — canary-analysis §8.
- **AC-007** — `docs/deep-dives/autobuild_local_vllm.md`.
- **AC-008** — Graphiti capture.
- **AC-001 (code/CI half)** — 006.4 routing confirmed; falsifier test green.

### ⛔ Operator action required to unblock

1. **Deploy `qwen-coder-next` on the GB10** (GB10-shell): add the builders-group entry to `/opt/llama-swap/config/config.yaml` per the historical `llama-swap-config.yaml:72-90` block, stage the GGUF at `/opt/llama-swap/models/qwen3-coder-next/Qwen3-Coder-Next-FP8.gguf`, reload llama-swap, and reconverge `RUNBOOK-v3-production-deployment.md` §5.2 so documented and live configs match. _Alternatively_ decide `qwen3-coder-30b` (live) is the validation substrate and revise the `model_choice_correction` — but this re-opens the F2/F6 marker-contract question.
2. **Re-run AC-001A** until `:9000/v1/models` lists `qwen-coder-next` and a completion returns 200 + non-empty.
3. **Run preflight AC-001B/C/D**, then the batch: `python scripts/canary_validation_runner.py --variant 009a` (~10h, monitor). Then `--variant 009a --aggregate`.
4. **Fill AC-004 §8.5 results, AC-005 verdict, AC-006 cross-link** from the aggregated comparison doc.
