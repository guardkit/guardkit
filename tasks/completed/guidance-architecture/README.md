# Feature: Guidance Architecture Formalization

## Problem Statement

The architectural review (TASK-REV-ARCH) found that the current guidance file implementation is sound but undocumented. The `rules_structure_generator.py` contains code that would create full duplication if enhanced agents exist, conflicting with the correct slim-summary pattern visible in existing templates.

## Solution Approach

Formalize the "Summary + Reference" pattern (Option B) as the official architecture:
1. Fix generator to extract slim summaries instead of copying full agent content
2. Add size validation to prevent accidental duplication
3. Document the architecture formally in guides

## Subtasks

| ID | Title | Method | Wave |
|----|-------|--------|------|
| TASK-GA-001 | Fix generator to generate slim guidance | task-work | 1 |
| TASK-GA-002 | Add size validation for guidance files | task-work | 1 |
| TASK-GA-003 | Document guidance architecture in rules-structure-guide | direct | 2 |
| TASK-GA-004 | Add source-of-truth documentation to CLAUDE.md | direct | 2 |

## Dependencies

- No external dependencies
- TASK-GA-003 and TASK-GA-004 should wait for TASK-GA-001 completion (generator defines the pattern)

## Success Criteria

- [ ] Generator produces slim guidance files (<3KB) with boundaries and references
- [ ] Size validation flags guidance files >5KB during template creation
- [ ] Documentation clarifies agent vs guidance purposes
- [ ] Existing templates remain unchanged (manual guidance files preserved)

## Related

- Review Task: TASK-REV-ARCH
- Review Report: `.claude/reviews/TASK-REV-ARCH-review-report.md`
