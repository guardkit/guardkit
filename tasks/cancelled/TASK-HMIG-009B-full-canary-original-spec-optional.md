---
id: TASK-HMIG-009B
title: Full canary execution — original TASK-HMIG-009 spec (optional polish, post-009A)
task_type: validation
status: cancelled
created: 2026-05-27T15:30:00Z
updated: 2026-06-04T13:00:00Z
cancelled: 2026-06-04T13:00:00Z
cancelled_location: tasks/cancelled/
cancellation_reason: "TASK-HMIG-009A produced a decisive GO verdict (5/6 SDK + 5/6 LangGraph = 83.3% approval; LangGraph 4/6 first-pass vs SDK 3/6; LangGraph 34% faster wall-clock). 009B was conditional on 009A being ambiguous — see this task's own 'When to skip' section. Skipped per the documented happy path. Saves ~40h GB10 compute that would not have changed the cutover decision."
previous_state: backlog
priority: medium    # optional — only runs if 009A signal is ambiguous
complexity: 6
effort_hours: 40    # ~40h GB10 compute (18 runs × ~2h each per F8 extrapolation; tighter with backlog tasks)
parent_task: TASK-HMIG-009
parent_review: TASK-REV-HM09
feature_id: FEAT-HMIG
parent_feature: hmig-pre-canary-fixes
wave: 3
conductor_workspace: hmig-pre-canary-fixes-wave3-1
implementation_mode: manual    # canary execution requires operator monitoring
intensity: standard
optional: true    # runs only if TASK-HMIG-009A signal is ambiguous; otherwise skip
depends_on:
  - TASK-HMIG-006.4   # Pre-loop adapter migration
  - TASK-FIX-WTBC     # Fixture-branch isolation (cwd-HEAD honour)
  - TASK-HMIG-009A    # Predecessor; this task runs only if 009A is inconclusive (also confirms qwen-coder-next behaviour empirically)
related_tasks:
  - TASK-HMIG-009     # Original spec (this is the full execution)
  - TASK-HMIG-009A    # Predecessor partial canary
  - TASK-HMIG-010     # Wave-4 cutover
tags:
  - canary
  - validation
  - langgraph-migration
  - optional
falsifier: "Aggregate result strengthens or weakens TASK-HMIG-009A's verdict with empirical evidence from the full 18-rep set including pre-loop ON and fixture-isolated tasks. Decision: if 009A's verdict holds under 009B's stricter conditions, cutover proceeds with high confidence; if 009B contradicts 009A, escalate."
---

# Task: Full canary execution — original TASK-HMIG-009 spec (optional polish)

> **🛑 CANCELLED 2026-06-04** — TASK-HMIG-009A produced a decisive GO verdict
> overnight (per `docs/state/TASK-REV-HMIG/canary-analysis.md` §8.5):
>
> | Metric | SDK | LangGraph |
> |---|---|---|
> | Approval rate | 5/6 (83.3%) | 5/6 (83.3%) |
> | First-pass success | 3/6 (50%) | 4/6 (67%) |
> | Mean wall-clock | ~31 min | ~21 min (34% faster) |
> | Failure mode | 1× unrecoverable_stall (F6) | 1× ERROR (llama-swap 400) |
>
> Both harnesses clear the ≥75% bar at parity; LangGraph is +17 pp on
> first-pass and 34% faster on wall-clock. Cutover decision: **GO**.
>
> Per this task's own "When to skip" section (preserved below), all three
> skip conditions are met:
>
> 1. ✅ 009A produced a decisive GO verdict (≥75% first-pass on LangGraph,
>    classified failure modes — F6 substrate-level not harness-level).
> 2. ✅ Operator (2026-06-04) confirmed 009A scope is sufficient grounds
>    for the cutover decision.
> 3. ✅ 2026-06-15 cutover deadline does not allow the ~40h additional
>    canary compute that 009B would require.
>
> Closing without execution. **Skipped — TASK-HMIG-009A signal was decisive (GO);
> full canary not required for cutover decision.** F6 honesty collapse is filed
> as substrate work (not harness work) and is independent of the cutover.
>
> ---

> **⚠ OPTIONAL** (original framing, preserved for history): This task only runs if TASK-HMIG-009A's signal is ambiguous. If 009A's verdict is decisive (clear GO or clear NO-GO for the Wave-4 cutover), skip this task and proceed directly to TASK-HMIG-010.

## Description

Full execution of the original TASK-HMIG-009 canary spec, runnable after F1 (TASK-HMIG-006.4) and F4 (TASK-FIX-WTBC) close and TASK-HMIG-009A has produced its preliminary verdict. Adds the fixture-branch isolated task (TASK-GLI-004) and the pre-loop ON variant back into scope, producing the full 18-rep comparison originally specified.

**Model choice (revised 2026-06-02)**: same as 009A — both harnesses use `qwen36-workhorse` (Qwen3.6-35B-A3B), the operator's current AutoBuild Player model per `model_choice_correction_v2` in [.guardkit/autobuild/TASK-REV-HMIG-canary-set.json](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json). This supersedes the 2026-05-27 swap to qwen-coder-next (which was documented but not deployed — surfaced by 009A's preflight AC-001A on 2026-05-27). The operator's week of 2026-05-28→2026-06-02 llama-swap reconfiguration work + benchmark/forum research on agentic coding settled on the workhorse as the strongest deployable choice. If 009A's preflight (AC-001A/B against qwen36-workhorse) passes, no separate F2 work is required for 009B either.

## Scope (per TASK-HMIG-009 original spec)

- **Canary tasks**: 3 — TASK-GLI-004 + 2 backlog tasks (per [`.guardkit/autobuild/TASK-REV-HMIG-canary-set.json`](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json)).
- **Reps per (task, harness)**: 3
- **Total runs**: 3 tasks × 2 harnesses × 3 reps = **18 runs**
- **Pre-loop**: ON (default).
- **Fixture isolation**: Via canary-worktree wrapper (requires TASK-FIX-WTBC).
- **Backing models**: Per 009A's resolved methodology (likely local Qwen on both sides).

## Acceptance Criteria

- [ ] **AC-001** — Both code dependencies have landed (TASK-HMIG-006.4 + TASK-FIX-WTBC merged), and TASK-HMIG-009A's preflight (AC-001A-D) has confirmed `qwen-coder-next` produces well-formed tool_use blocks end-to-end on both harnesses.
- [ ] **AC-002** — TASK-HMIG-009A's verdict is documented and the operator has determined that additional evidence is needed (otherwise skip this task).
- [ ] **AC-003** — Run the 18 canary executions via [`scripts/canary_validation_runner.py`](../../../scripts/canary_validation_runner.py). Persist under `.guardkit/autobuild/TASK-HMIG-009B-canary/`.
- [ ] **AC-004** — Compute the full first-pass-success matrix per (harness × task × rep). Aggregate per harness across all 9 runs.
- [ ] **AC-005** — Compare 009B verdict against 009A verdict. Document either (a) verdict reinforced, cutover proceeds with high confidence, or (b) verdict contradicts 009A — escalate with hypothesis for divergence (substrate variance, pre-loop interaction, fixture-isolation effect).
- [ ] **AC-006** — Update [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md) §9 (new section) with the full 18-rep matrix and final verdict.

## When to skip

This task should be **skipped** (closed without execution) if:

- TASK-HMIG-009A produced a decisive GO verdict (LangGraph first-pass-success ≥75% across 6 runs, no classified failure modes), AND
- The operator is satisfied the 009A scope is sufficient grounds for the cutover decision, AND
- The 2026-06-15 cutover deadline does not allow ~40h additional canary compute.

Close with a note: "Skipped — TASK-HMIG-009A signal was decisive ({verdict}); full canary not required for cutover decision."

## References

- Parent review: [TASK-REV-HM09 review report §7](../../../.claude/reviews/TASK-REV-HM09-review-report.md#7-ac-007--task-hmig-009-scope-revision-recommendation)
- Predecessor: TASK-HMIG-009A
- Original spec: [TASK-HMIG-009 (blocked)](../../blocked/TASK-HMIG-009-canary-validation.md)
- Pilot analysis: [`docs/state/TASK-REV-HMIG/canary-analysis.md`](../../../docs/state/TASK-REV-HMIG/canary-analysis.md)
