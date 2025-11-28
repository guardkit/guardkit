# Add Spec-Oriented Development (SOD) Positioning to MkDocs

**Priority**: Critical
**Category**: Documentation Gap - Core Philosophy
**Estimated Effort**: 2-3 hours

## Problem

The README.md introduces Spec-Oriented Development (SOD) as the core philosophy and differentiator (lines 14-39), but the MkDocs site does not position Taskwright this way.

## Current State

**README.md includes**:
- SOD as core philosophy
- Contrast with Spec-Driven Development (SDD)
- Upgrade path to RequireKit
- Comparison table (SOD vs SDD)
- Migration path guidance

**MkDocs site**: Does not lead with SOD positioning

## Acceptance Criteria

1. Update homepage (`docs/index.md`) to lead with SOD positioning
2. Create new page: `docs/concepts/spec-oriented-development.md`
3. Add to MkDocs navigation under "Core Concepts"
4. Content must include:
   - What is SOD vs SDD
   - Taskwright's position on the formality spectrum
   - When to use task descriptions vs formal specs
   - Upgrade path to RequireKit for SDD
   - Comparison table
5. Update site tagline/subtitle if needed

## Implementation Notes

- Extract from README.md lines 14-39
- Emphasize "right amount of process" philosophy
- Show migration path: SOD → SOD+Conductor → SDD
- Link to RequireKit documentation

## References

- README.md lines 14-39
- README.md lines 223-234 (audience table)
