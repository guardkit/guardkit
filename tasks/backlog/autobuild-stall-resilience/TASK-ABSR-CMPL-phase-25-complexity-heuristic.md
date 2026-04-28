---
id: TASK-ABSR-CMPL
title: Phase-2.5 complexity heuristic — factor AC count, dep count, consumer count
status: backlog
created: 2026-04-28T00:00:00Z
updated: 2026-04-28T00:00:00Z
priority: medium
tags: [phase-2.5, complexity-evaluation, planning, FEAT-ABSR-9C6E, R6.a]
parent_review: TASK-REV-9D13
feature_id: FEAT-ABSR-9C6E
implementation_mode: task-work
task_type: feature
wave: 3
historical_wave: 5
complexity: 5
depends_on:
  - TASK-ABSR-MAXT
test_results:
  status: pending
  coverage: null
  last_run: null
---

# TASK-ABSR-CMPL — Phase-2.5 complexity heuristic enhancement

## Description

Phase 2.5 / Phase 2.7 complexity scoring currently uses a single `complexity` value from frontmatter. TASK-J004-013 was scored `complexity=6` but had 10 ACs, 7 dependencies, and 3 consumer-context interfaces — structurally a complexity-8+ task. The current scoring did not flag it for Phase-2.8 split-or-checkpoint review.

Add a heuristic that estimates effective SDK turns from these structural signals and flags tasks above a threshold for split. Tasks scored as effective complexity 8+ should require human checkpoint at Phase 2.8.

Also: ensure Phase 2.5 runs for `/feature-plan`-generated tasks (TASK-J004-013 may have skipped Phase 2.5 because it was generated rather than human-authored).

**Targets**: Bug G in TASK-REV-9D13 v2 §0. **MED priority — improves task-shaping, reduces large-task failure rate.**

## Acceptance Criteria

- [ ] AC-001: New helper in `installer/core/commands/lib/complexity_*.py` (or appropriate file): `def estimate_effective_complexity(complexity: int, ac_count: int, dep_count: int, consumer_count: int) -> Tuple[int, str]` returning (effective_complexity, rationale_string). Formula derived from FEAT-J004-702C run-2 data:
  - base = complexity
  - ac_load = max(0, (ac_count - 5) // 2)
  - dep_load = max(0, (dep_count - 2) // 2)
  - consumer_load = consumer_count
  - effective = min(10, base + ac_load + dep_load + consumer_load)
- [ ] AC-002: Phase 2.5 / Phase 2.7 entry point reads task frontmatter for `complexity`, parses ACs from the `## Acceptance Criteria` section, reads `dependencies` field, reads `consumer_context` field. Calls `estimate_effective_complexity` and substitutes the result for routing decisions (AUTO_PROCEED / QUICK_OPTIONAL / FULL_REQUIRED).
- [ ] AC-003: Tasks with effective_complexity ≥ 7 trigger Phase 2.8 human checkpoint as per the existing `complexity-management-workflow.md` documentation. The checkpoint message should display both the raw complexity score and the effective complexity, with the rationale.
- [ ] AC-004: Phase 2.5 must run for tasks generated via `/feature-plan` (which sets `parent_review` in frontmatter). Currently complexity evaluation may be skipped for generated tasks; correct that.
- [ ] AC-005: Apply heuristic to TASK-J004-013 retroactively (test fixture): given complexity=6, ac_count=10, dep_count=7, consumer_count=3 → effective_complexity = 6 + 2 + 2 + 3 = 13 → clamp to 10. Triggers FULL_REQUIRED + Phase 2.8 checkpoint. Verify in test.
- [ ] AC-006: Apply heuristic to TASK-J004-006 (complexity=4, low AC count, 1 consumer) → effective_complexity ≈ 4-5. Stays in QUICK_OPTIONAL. Verify in test.
- [ ] AC-007: New tests in `tests/unit/commands/test_complexity_evaluation.py` (or appropriate file) covering: `test_effective_complexity_baseline` (no extra structural load → returns base), `test_effective_complexity_high_ac_count`, `test_effective_complexity_high_dep_count`, `test_effective_complexity_consumer_load`, `test_effective_complexity_clamp_at_10`, `test_effective_complexity_triggers_phase_28_checkpoint`.
- [ ] AC-008: Existing complexity-evaluation tests continue to pass without modification.
- [ ] AC-009: Documentation: update [docs/workflows/complexity-management-workflow.md](../../../docs/workflows/complexity-management-workflow.md) to document the new effective-complexity formula and the structural signals (AC / dep / consumer count) it incorporates.
- [ ] AC-010: `pytest tests/unit/commands/test_complexity_evaluation.py -v` passes.
- [ ] AC-011: Lint/format pass.

## Implementation Notes

This is a behaviour-change to the planning pipeline. Larger blast radius than R1-R5. Recommended **defer to post-DDD-SouthWest-talk** unless the talk demo specifically benefits from improved task-shaping.

**Why depend on R4 (TASK-ABSR-MAXT)**: The heuristic and the SDK-turn scaling should be co-designed — the heuristic's threshold for "split" should align with `TASK_WORK_SDK_MAX_TURNS` headroom. Land R4 first to stabilise the SDK-turn budget; then R6.a tunes the upstream split threshold.

**Regression risk**: More tasks flagged for Phase 2.8 checkpoint. User may experience "more friction" on planning. Opt-out via existing `--no-questions` flag on `/task-work`. Keep raw `complexity` field as the primary score for users who don't want effective scaling.

**Coordination**: Wave 5 (post-talk preferred). Independent of CEIL/WALL/FRSH/DIAG/MTBC.
