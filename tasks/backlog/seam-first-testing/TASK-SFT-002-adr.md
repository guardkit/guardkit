---
id: TASK-SFT-002
title: Write ADR-SP-009 Honeycomb Testing Model
task_type: documentation
parent_review: TASK-REV-AC1A
feature_id: FEAT-AC1A
wave: 1
implementation_mode: direct
complexity: 2
dependencies: []
priority: high
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AC1A
  base_branch: main
  started_at: '2026-02-14T09:55:45.175334'
  last_updated: '2026-02-14T09:59:11.505976'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-14T09:55:45.175334'
    player_summary: Created ADR-SP-009 documenting the architectural decision to adopt
      the Honeycomb testing model (60% seam, 30% unit, 10% E2E) for GuardKit platform
      development and the Trophy model (50% feature/integration, 30% unit, 10% E2E,
      10% static) for client app templates. The ADR references historical failure
      patterns (FP-002, FP-003, FP-006) that motivated this decision, explains the
      distinction between platform tools where bugs hide at seams vs client apps where
      bugs hide in business logic, and document
    player_success: true
    coach_success: true
---

# Write ADR-SP-009: Honeycomb Testing Model

## Objective

Document the architectural decision to adopt the Honeycomb testing model (seam-first) for GuardKit and the Trophy model for client app templates.

## Acceptance Criteria

- [ ] `docs/architecture/decisions/ADR-SP-009-honeycomb-testing-model.md` created
- [ ] ADR follows existing format (see ADR-SP-001 through ADR-SP-008)
- [ ] Status: Accepted
- [ ] Context explains historical failure patterns (reference FP-002, FP-003, FP-006)
- [ ] Decision captures:
  - GuardKit uses Honeycomb model (60% seam, 30% unit, 10% E2E)
  - Client app templates use Trophy model (50% feature/integration, 30% unit, 10% E2E, 10% static)
  - Seam tests verify cross-boundary wiring with real implementations on both sides
  - Anti-stub gate: every orchestrator function must have at least one seam test
- [ ] Consequences list includes: new `tests/seam/` directory, quality gate updates, template guidance updates
- [ ] `docs/architecture/ARCHITECTURE.md` updated with ADR-SP-009 row in decisions table

## Implementation Notes

- Reference `docs/research/testing-strategy/testing-strategy-seam-first-analysis.md` as source
- Keep ADR concise (under 150 lines)
