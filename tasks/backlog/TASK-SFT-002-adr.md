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
  current_turn: 3
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AC1A
  base_branch: main
  started_at: '2026-02-15T20:25:16.326960'
  last_updated: '2026-02-15T20:34:23.268794'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Not all acceptance criteria met:\n  \u2022 `docs/architecture/ARCHITECTURE.md`\
      \ updated with ADR-SP-009 row in decisions table"
    timestamp: '2026-02-15T20:25:16.326960'
    player_summary: Created ADR-SP-009 documenting the Honeycomb testing model for
      GuardKit platform (60% seam, 30% unit, 10% E2E) and Trophy model for client
      app templates (50% feature/integration, 30% unit, 10% E2E, 10% static). The
      ADR explains the context of historical failures at technology seams (FP-002,
      FP-003, FP-006), defines seam tests as cross-boundary verification with real
      implementations on both sides, and introduces the anti-stub gate requirement
      that every orchestrator function must have at least on
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: "- Not all acceptance criteria met:\n  \u2022 `docs/architecture/decisions/ADR-SP-009-honeycomb-testing-model.md`\
      \ created\n  \u2022 ADR follows existing format (see ADR-SP-001 through ADR-SP-008)\n\
      \  \u2022 Status: Accepted\n  \u2022 Context explains historical failure patterns\
      \ (reference FP-002, FP-003, FP-006)\n  \u2022 Decision captures:\n  (5 more)"
    timestamp: '2026-02-15T20:29:38.491406'
    player_summary: 'The Coach feedback identified AC-011 as missing, but upon investigation,
      the work was already completed in Turn 1. The ARCHITECTURE.md file contains
      the ADR-SP-009 row at line 34: ''| [ADR-SP-009](decisions/ADR-SP-009-honeycomb-testing-model.md)
      | Honeycomb Testing Model for Seam-First Testing | Accepted |''. The test test_architecture_md_has_adr_sp_009_row
      validates this criterion. The only issue was that I failed to provide a completion_promise
      for AC-011 in my Turn 1 report - I mistakenly combi'
    player_success: true
    coach_success: true
  - turn: 3
    decision: approve
    feedback: null
    timestamp: '2026-02-15T20:31:22.419287'
    player_summary: No implementation changes needed in Turn 3. All work was completed
      in Turn 1 (ADR-SP-009 file creation, ARCHITECTURE.md update, comprehensive test
      suite). Turn 2 addressed AC-11 completion promise reporting. This turn provides
      complete reporting with all 11 completion promises (AC-001 through AC-011) as
      required by the Coach.
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
