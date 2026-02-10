---
id: TASK-SC-012
title: "Update mkdocs.yml nav and CLAUDE.md references"
status: backlog
created: 2026-02-10T11:40:00Z
updated: 2026-02-10T11:40:00Z
priority: medium
task_type: documentation
parent_review: TASK-REV-AEA7
feature_id: FEAT-SC-001
wave: 5
implementation_mode: direct
complexity: 2
dependencies:
  - TASK-SC-011
tags: [documentation, mkdocs, claude-md]
---

# Task: Update mkdocs.yml navigation and CLAUDE.md references

## Description

Wire the new documentation guides into the docs site navigation and update CLAUDE.md to reference the new commands.

## Key Implementation Details

### Part 1: Update mkdocs.yml

Add the 3 new guides to the navigation under a new "System Context" subsection within Guides:

```yaml
- Guides:
    # ... existing guides ...
    - System Context:
        - System Overview: guides/system-overview-guide.md
        - Impact Analysis: guides/impact-analysis-guide.md
        - Context Switch: guides/context-switch-guide.md
```

Or if a flat structure is preferred (matching existing pattern):

```yaml
- Guides:
    # ... existing guides ...
    - System Overview Guide: guides/system-overview-guide.md
    - Impact Analysis Guide: guides/impact-analysis-guide.md
    - Context Switch Guide: guides/context-switch-guide.md
```

### Part 2: Update root CLAUDE.md

Add the new commands to the "Essential Commands" section:

```markdown
### System Context Commands
/system-overview [--verbose] [--section=SECTION] [--format=FORMAT]
/impact-analysis TASK-XXX [--depth=DEPTH] [--include-bdd]
/context-switch [project-name] [--list]
```

Add to the "Key References" table:

```markdown
| System Context Commands | `docs/guides/system-overview-guide.md`, `impact-analysis-guide.md`, `context-switch-guide.md` |
```

### Part 3: Update .claude/CLAUDE.md (if needed)

If the inner CLAUDE.md references available commands, add the 3 new ones there too.

## Acceptance Criteria

- [ ] mkdocs.yml updated with 3 new guide entries in nav
- [ ] Root CLAUDE.md lists new commands in Essential Commands
- [ ] Root CLAUDE.md Key References table updated
- [ ] Docs site builds without errors: `mkdocs build`
- [ ] Navigation renders correctly on docs site

## Test Requirements

```bash
# Verify docs site builds
cd docs && mkdocs build --strict 2>&1 | head -20
```

## Implementation Notes

- Read mkdocs.yml to understand the exact nav structure before modifying
- Keep nav entries consistent with existing naming pattern
- CLAUDE.md changes are small (add 5-10 lines)
- This is the final documentation task — should run after guides are created
