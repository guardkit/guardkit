---
id: TASK-GR-PRE-000-C
title: Add tests and documentation for seeding update
status: backlog
created: 2026-01-30T00:00:00Z
updated: 2026-01-30T00:00:00Z
priority: medium
tags: [graphiti, testing, documentation, mvp-phase-0]
task_type: testing
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: direct
wave: 2
conductor_workspace: gr-mvp-wave2-tests
complexity: 2
depends_on:
  - TASK-GR-PRE-000-A
  - TASK-GR-PRE-000-B
---

# Task: Add tests and documentation for seeding update

## Description

Create comprehensive tests and documentation for the seeding metadata update (PRE-000-A) and clear command (PRE-000-B).

## Acceptance Criteria

- [ ] Unit tests for metadata schema validation
- [ ] Unit tests for clear command logic
- [ ] Integration tests for seeding with metadata
- [ ] Integration tests for clear command
- [ ] Documentation for `guardkit graphiti clear` command
- [ ] Update existing Graphiti documentation with metadata info

## Implementation Notes

### Test Files

- `tests/unit/integrations/graphiti/test_seeding_metadata.py`
- `tests/unit/cli/test_graphiti_clear.py`
- `tests/integration/graphiti/test_seeding_integration.py`
- `tests/integration/graphiti/test_clear_integration.py`

### Documentation Files

- `docs/guides/graphiti-commands.md` - Add clear command section
- `docs/deep-dives/graphiti/episode-metadata.md` - New file

### Test Coverage Requirements

- 80%+ coverage for new code
- All edge cases for clear command tested
- Metadata schema validation complete

## Test Requirements

- [ ] pytest tests pass
- [ ] Integration tests with Neo4j (can use docker fixture)
- [ ] Coverage report shows 80%+ for new code

## Notes

This is a quick task (direct mode) focused on testing and documentation only.

## References

- [Feature Specification](../../../../docs/research/graphiti-refinement/FEATURE-SPEC-graphiti-refinement-mvp.md)
