---
id: TASK-ABSR-WTKS
title: Worktree isolation per parallel task — design-first, post-demo
status: design_approved
created: 2026-04-28T12:30:00Z
updated: 2026-04-28T15:30:00Z
previous_state: backlog
state_transition_reason: "Phase 2.8 human checkpoint approved (--design-only)"
priority: medium
tags: [autobuild, worktree-isolation, parallel-contention, FEAT-ABSR-9C6E, design-first, post-demo, structural]
parent_review: TASK-REV-WORS
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
task_type: feature
wave: 4
historical_wave: 7
complexity: 7
depends_on: []
test_results:
  status: pending
  coverage: null
  last_run: null
design:
  status: approved
  approved_at: "2026-04-28T15:30:00Z"
  approved_by: "human"
  implementation_plan: ".claude/task-plans/TASK-ABSR-WTKS-implementation-plan.md"
  implementation_plan_version: "v1"
  architectural_review_score: 76
  architectural_review_breakdown:
    solid: 74
    dry: 82
    yagni: 72
  complexity_score: 7
  recommended_option: "C+A (two-phase: Option C tactical guard, then Option A per-task subworktrees)"
  diverged_from_starting_point: true
  divergence_rationale: "Option E (B+C) rejected — Option B's git stash/reset is worktree-wide, not per-task scopable; macOS lacks overlayfs; bash subprocesses always see shared filesystem."
  estimated_effort_days: "6-8"
  design_notes: "Phase 2.5B review APPROVE WITH RECOMMENDATIONS. M1/M2/M3 corrections applied to design doc before approval."
---

# TASK-ABSR-WTKS — Worktree isolation per parallel task (design-first)

## Status

**DESIGN-FIRST. DEFER POST-DDD-SOUTHWEST.** This task addresses a structural class-of-defect surfaced in [TASK-REV-WORS report v2 §4.3](../../../.claude/reviews/TASK-REV-WORS-report.md#43-the-shared-worktree-poison--file-system-level-view). The tactical unblock (TASK-ABSR-FLOR) addresses the symptoms; this task addresses the structural cause. Schedule for the sprint after the demo.

Use `/task-work TASK-ABSR-WTKS --design-only` to produce the design first; do not run `/task-work` in standard mode until the design is approved.

## Problem

Multiple Players in the same wave (worker_count > 1) currently share the FEAT-XXX worktree filesystem. Their tool calls (Read/Edit/Bash) operate on the *same* working directory. There is no transaction boundary on Player edits — when the SDK terminates a Player mid-task (ceiling hit, timeout), whatever the Player wrote up to that point persists in the worktree.

This created the Wave-4 cascade in run-3:

1. J004-012 hit MAXT ceiling at 141/140 turns mid-Phase-3.
2. Player had already deleted `_REFRESH_OK_MESSAGE` constant from `capabilities.py` but had not yet updated `test_tools_capabilities.py` to remove the reference.
3. SDK terminated; orchestrator R1 CEIL guard correctly skipped Phase 4/5.
4. **The half-edited worktree was preserved.**
5. J004-011 (parallel mate, working on `dispatch.py`) completed cleanly, but its Coach pytest run *imports* the `capabilities` module transitively — fails with `AttributeError: '_REFRESH_OK_MESSAGE'`.
6. Coach correctly classifies this as `parallel_contention`. But the underlying problem is structural — there's no way for J004-011 to *avoid* J004-012's broken state when they share a worktree.

## Solution space (NOT pre-decided)

The right design is unclear and warrants Phase-2.5 architectural review. Options:

### Option A — Worktree-per-task

Each parallel task gets its own worktree, e.g. `.guardkit/worktrees/FEAT-J004-702C-J004-011/` and `.../FEAT-J004-702C-J004-012/`. Wave-end synchronisation merges successful tasks into a "consensus" worktree before the next wave starts.

Pros: complete isolation; no contention.
Cons: disk usage 2× per wave; merge logic is non-trivial when tasks edit overlapping files.

### Option B — Transaction-boundary semantics on Player edits

Player edits are staged in a per-task overlay (e.g. git stash, copy-on-write directory). On successful Player completion, edits are committed to the shared worktree atomically. On ceiling/timeout, edits are rolled back.

Pros: shared worktree preserved; rollback is clean.
Cons: tool-dispatcher integration is invasive (Read/Edit must consult the overlay); Bash subprocesses still see the underlying filesystem unless we use overlayfs.

### Option C — Pre-Phase-4 consistency check

Coach (or a new pre-Phase-4 step) runs a fast consistency check: does the worktree compile? do imports resolve? If no, classify as `worktree_corruption_post_ceiling` and abort the wave; mark all parallel tasks for sequential retry.

Pros: cheap; doesn't restructure storage.
Cons: doesn't *prevent* the corruption; only detects it.

### Option D — Sequential-only execution for waves with high cross-file dependency

A new heuristic at wave-planning time: if Wave N's tasks have overlapping import surfaces (computed via static analysis), reduce worker_count to 1 for that wave.

Pros: prevents the contention class.
Cons: doubles wall time for affected waves; needs static-import-graph tooling.

### Option E (recommended starting point) — Hybrid: B + C

Transaction-boundary on Player edits (rollback on ceiling/timeout) + pre-Phase-4 consistency check as defence-in-depth.

## Acceptance Criteria (design phase)

- [ ] AC-DES-001: Design document at `.claude/task-plans/TASK-ABSR-WTKS-implementation-plan.md` covering all five options with concrete pros/cons informed by the existing GuardKit codebase.
- [ ] AC-DES-002: Decision-matrix scoring options on (a) blast radius of fix, (b) maintenance burden, (c) test surface required, (d) defect-class coverage.
- [ ] AC-DES-003: Recommended option chosen with explicit Phase-2.5 architectural review (architectural-reviewer agent score ≥ 60/100).
- [ ] AC-DES-004: Sequence diagram showing how the chosen option would have prevented the Wave-4 cascade in run-3.
- [ ] AC-DES-005: Test surface plan: which existing tests need updates, which new tests are needed, what's the regression test strategy?
- [ ] AC-DES-006: Effort estimate (hours/days) and dependency analysis (does it block CMPL? FLOR? other backlog items?).

## Implementation acceptance criteria (after design approval)

To be filled in post-design. Initial placeholder:

- [ ] AC-IMP-001: Chosen option implemented per design.
- [ ] AC-IMP-002: Regression test pinning the Wave-4 cascade scenario — a synthetic test where Player A's mid-edit poisons Player B's coach pytest run is provably prevented by the implementation.
- [ ] AC-IMP-003: All existing autobuild integration tests pass.
- [ ] AC-IMP-004: New tests cover the contention scenario.
- [ ] AC-IMP-005: Documentation update in `.claude/rules/autobuild.md` describing the worktree-isolation semantics.

## Why design-first

This is a **complexity-7+ structural change**. Per CLAUDE.md, complexity 7+ tasks require Phase-2.8 human checkpoint. Picking the wrong option could:
- Add significant disk usage / I/O cost
- Introduce subtle merge bugs that surface only under specific cross-file edit patterns
- Conflict with the existing R1 CEIL / R3 FRSH guard semantics

The option matrix matters. Pick wrong, ship a regression. Design first.

## Related

- [TASK-REV-WORS report v2 §3.2 (L2 Container view)](../../../.claude/reviews/TASK-REV-WORS-report.md#32-level-2--container-view-orchestrator-internals) — shared worktree explicitly drawn as the only mutable state shared between parallel Players.
- [TASK-REV-WORS report v2 §4.3 (shared-worktree poison sequence)](../../../.claude/reviews/TASK-REV-WORS-report.md#43-the-shared-worktree-poison--file-system-level-view) — file-system-level view of the cascade.
- [TASK-ABSR-FLOR](TASK-ABSR-FLOR-maxt-floor-and-task-timeout-floor.md) — tactical fix that addresses the symptoms (FLOR ships first; WTKS ships post-demo).
- [TASK-ABSR-CMPL](TASK-ABSR-CMPL-phase-25-complexity-heuristic.md) — strategic fix for complexity heuristic underestimation (independent track from WTKS).

## Out of scope

- Implementing without a design pass.
- Anything that changes the existing R1/R3 guard semantics — those work correctly today; the issue is what happens *after* they fire (a half-edited worktree).
