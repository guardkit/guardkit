---
id: TASK-HMIG-009B
title: Full canary execution — original TASK-HMIG-009 spec (optional polish, post-009A)
task_type: validation
status: backlog
created: 2026-05-27T15:30:00Z
updated: 2026-05-27T15:30:00Z
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

> **⚠ OPTIONAL**: This task only runs if TASK-HMIG-009A's signal is ambiguous. If 009A's verdict is decisive (clear GO or clear NO-GO for the Wave-4 cutover), skip this task and proceed directly to TASK-HMIG-010.

## Description

Full execution of the original TASK-HMIG-009 canary spec, runnable after F1 (TASK-HMIG-006.4) and F4 (TASK-FIX-WTBC) close and TASK-HMIG-009A has produced its preliminary verdict. Adds the fixture-branch isolated task (TASK-GLI-004) and the pre-loop ON variant back into scope, producing the full 18-rep comparison originally specified.

**Model choice**: same as 009A — both harnesses use `qwen-coder-next` (Qwen3-Coder-Next FP8). F2 (the "local Qwen marker contract failure") was reframed as a model-swap incident on 2026-05-27 and resolved by reverting the canary-set to the proven model; see [.guardkit/autobuild/TASK-REV-HMIG-canary-set.json](../../../.guardkit/autobuild/TASK-REV-HMIG-canary-set.json) `model_choice_correction` block. If 009A's AC-001A-D preflight passes, no separate F2 work is required for 009B either.

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
