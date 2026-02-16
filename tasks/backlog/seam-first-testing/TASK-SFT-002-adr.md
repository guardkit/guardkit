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
  current_turn: 2
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AC1A
  base_branch: main
  started_at: '2026-02-15T21:00:00.355893'
  last_updated: '2026-02-15T21:22:23.956369'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Not all acceptance criteria met:\n  \u2022 Decision captures:\n \
      \ \u2022 Consequences list includes: new `tests/seam/` directory, quality gate\
      \ updates, template guidance upd"
    timestamp: '2026-02-15T21:00:00.355893'
    player_summary: 'Created comprehensive ADR-SP-009 documenting the Honeycomb testing
      model decision for GuardKit platform testing (seam-first approach) and Trophy
      model for client app templates (feature-first approach). The ADR follows the
      established format from ADR-SP-001 through ADR-SP-008 with Date, Status, Context,
      Decision, and Consequences sections. Context explains historical failure patterns
      at technology seams (FP-002: system_plan stub, FP-003: acceptance criteria wiring,
      FP-006: files_created empty). D'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-02-15T21:21:23.536477'
    player_summary: No code changes needed in Turn 2. The ADR created in Turn 1 already
      satisfies ALL acceptance criteria, including AC-005 (Decision captures all required
      points) and AC-006 (Consequences lists all required implementation changes).
      This turn provides explicit completion promises for AC-005 and AC-006 that were
      missing from Turn 1 report.
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
