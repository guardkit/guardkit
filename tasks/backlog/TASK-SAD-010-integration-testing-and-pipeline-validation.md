---
id: TASK-SAD-010
title: "Integration testing and full pipeline validation"
task_type: testing
parent_review: TASK-REV-AEE1
feature_id: FEAT-SAD
wave: 4
implementation_mode: task-work
complexity: 5
dependencies:
  - TASK-SAD-006
  - TASK-SAD-007
  - TASK-SAD-008
  - TASK-SAD-009
---

# Task: Integration testing and full pipeline validation

## Description

Validate the complete command pipeline end-to-end: `/system-arch` -> `/system-design` -> `/system-plan` -> `/feature-spec`. Verify Graphiti seeding, prerequisite gates, graceful degradation, and diagram review gates.

## Acceptance Criteria

- [ ] Pipeline ordering test: `/system-design` without `/system-arch` shows correct error and offers to chain
- [ ] Graphiti seeding flow: `/system-arch` output is readable by `/system-plan` without re-explaining architecture
- [ ] `/system-plan` references bounded contexts and ADRs from `/system-arch` output
- [ ] `/feature-spec` references real domain entities and API contracts from `/system-design` output
- [ ] C4 mandatory review gate: commands pause and require explicit diagram approval
- [ ] Graceful degradation test: Graphiti unavailable → markdown artefacts still generated, warning shown
- [ ] Partial session test: skip categories mid-session → completed categories persisted, skipped ones noted
- [ ] ADR numbering continuity: new ADRs continue from existing highest number
- [ ] DDR numbering: new DDRs start from 001 (or continue from existing)
- [ ] Concurrent session test: two sessions on same project → last-write-wins, no corruption
- [ ] Temporal superseding test: `/arch-refine` supersedes ADR → both old and new queryable
- [ ] Feature spec staleness test: `/design-refine` changes contract → affected feature specs flagged
- [ ] Security test: adversarial content in ADR rationale → stored safely, retrievable intact
- [ ] Document test results in test report

## Implementation Notes

- Tests should cover the 33 BDD scenarios from `features/system-arch-design-commands/system-arch-design-commands.feature`
- Focus on integration boundaries, not unit-level testing (unit tests covered in individual tasks)
- Use a test project fixture (not the GuardKit project itself)
- Graceful degradation test: mock Graphiti client to simulate unavailability
- Concurrent session test: can be simulated with sequential runs using different session IDs
