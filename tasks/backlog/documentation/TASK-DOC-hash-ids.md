# Add Hash-Based Task IDs Documentation to MkDocs

**Priority**: Critical
**Category**: Documentation Gap
**Estimated Effort**: 2-3 hours

## Problem

The README.md has extensive coverage of hash-based task IDs (lines 42-144), but the MkDocs site has no mention of this critical feature.

## Current State

**README.md includes**:
- Hash-based ID format (`TASK-{hash}`, `TASK-{prefix}-{hash}`)
- Benefits (zero duplicates, concurrent creation, Conductor.build compatible)
- PM tool integration (JIRA, Azure DevOps, Linear, GitHub)
- Common prefixes (E{number}, DOC, FIX, TEST)
- Examples and migration guide

**MkDocs site**: Missing entirely

## Acceptance Criteria

1. Create new page: `docs/concepts/hash-based-task-ids.md`
2. Add to MkDocs navigation under "Core Concepts"
3. Content must include:
   - Format explanation with examples
   - Benefits for parallel development
   - PM tool integration details
   - Common prefix patterns
   - Migration from sequential IDs
4. Cross-reference from Getting Started guide
5. Add code examples showing real usage

## Implementation Notes

- Extract content from README.md lines 42-144
- Adapt for documentation site format
- Add visual diagrams if helpful
- Include migration script reference

## References

- README.md lines 42-144
- docs/guides/hash-id-parallel-development.md
- docs/guides/hash-id-pm-tools.md
