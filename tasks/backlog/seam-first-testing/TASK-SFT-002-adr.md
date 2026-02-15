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
  started_at: '2026-02-15T16:17:44.725867'
  last_updated: '2026-02-15T16:25:37.444519'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Player report validation failed:

      Type errors: tests_passed: expected bool, got NoneType'
    timestamp: '2026-02-15T16:17:44.725867'
    player_summary: '[RECOVERED via player_report] Original error: Player report validation
      failed:

      Type errors: tests_passed: expected bool, got NoneType'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: "- Not all acceptance criteria met:\n  \u2022 Decision captures:\n \
      \ \u2022 Seam tests verify cross-boundary wiring with real implementations on\
      \ both sides\n  \u2022 Anti-stub gate: every orchestrator function must have\
      \ at least one seam test\n  \u2022 Consequences list includes: new `tests/seam/`\
      \ directory, quality gate updates, template guidance upd\n  \u2022 `docs/architecture/ARCHITECTURE.md`\
      \ updated with ADR-SP-009 row in decisions table"
    timestamp: '2026-02-15T16:20:21.195380'
    player_summary: Completed ADR-SP-009 documenting the Honeycomb testing model for
      GuardKit platform (60% seam, 30% unit, 10% E2E) and Trophy model for client
      apps (50% feature/integration, 30% unit, 10% E2E, 10% static). Added reference
      to research document testing-strategy-seam-first-analysis.md. Updated ARCHITECTURE.md
      with ADR-SP-009 entry. Created comprehensive validation tests to verify all
      acceptance criteria are met.
    player_success: true
    coach_success: true
  - turn: 3
    decision: approve
    feedback: null
    timestamp: '2026-02-15T16:23:19.335666'
    player_summary: ADR-SP-009 has been completed with all required content. The work
      was already done in previous turns, but the completion promises needed to be
      properly mapped to match the exact acceptance criteria text. All content is
      present in the ADR including the Honeycomb model percentages, Trophy model percentages,
      seam test definition, anti-stub gate requirement, and consequences section.
      ARCHITECTURE.md has been updated with the ADR-SP-009 row in the decisions table.
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
