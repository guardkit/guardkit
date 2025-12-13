# Feature: Self-Template Enhancement

## Problem Statement

GuardKit has comprehensive Python/FastAPI resources but they need in-place enhancement using progressive disclosure and rules structure techniques. The review (TASK-REV-1DDD) identified that:

1. Python resources exist but may not be loading optimally into context
2. Rules structure is missing from templates (no conditional loading)
3. Some agents could benefit from content enhancement
4. The Hybrid Workflow approach should be used (modify in place, don't generate templates)

## Solution Approach

Apply the **Hybrid Workflow** from the review:
1. Use `/template-create --dry-run` as a reference to understand ideal structure
2. Use `/agent-enhance` directly on existing agents
3. Add rules structure to templates for conditional loading
4. Keep repository as source of truth (no circular dependency)

## Subtasks

| ID | Title | Mode | Wave | Status |
|----|-------|------|------|--------|
| TASK-STE-001 | Run template-create --dry-run analysis on GuardKit | direct | 1 | pending |
| TASK-STE-002 | Run template-create --dry-run analysis on fastapi-python | direct | 1 | pending |
| TASK-STE-003 | Enhance fastapi-specialist agent | task-work | 2 | pending |
| TASK-STE-004 | Enhance fastapi-testing-specialist agent | task-work | 2 | pending |
| TASK-STE-005 | Enhance fastapi-database-specialist agent | task-work | 2 | pending |
| TASK-STE-006 | Add rules structure to fastapi-python template | task-work | 3 | pending |
| TASK-STE-007 | Add rules structure to GuardKit .claude/ | task-work | 3 | pending |
| TASK-STE-008 | Validate improvements with Python test task | task-work | 4 | pending |

## Related Tasks

- TASK-REV-1DDD: Original review task (parent)
- TASK-REV-PD01: Progressive disclosure review
- TASK-TC-DEFAULT-FLAGS: Template create default flags

## Success Criteria

- [ ] Analysis complete for GuardKit and fastapi-python
- [ ] FastAPI agents enhanced with better examples and boundaries
- [ ] Rules structure added to fastapi-python template
- [ ] Rules structure added to GuardKit .claude/ (selective)
- [ ] Python workflow validated with test task
