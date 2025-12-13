---
id: TASK-CDI-001
title: Create orchestrators.md pattern file
status: completed
created: 2025-12-13T17:00:00Z
updated: 2025-12-13T14:45:00Z
completed: 2025-12-13T14:50:00Z
priority: high
tags: [rules-structure, patterns, orchestrator, python-library]
parent_task: TASK-REV-79E0
implementation_mode: direct
wave: 1
conductor_workspace: claude-improvements-wave1-orchestrators
complexity: 3
depends_on:
  - TASK-REV-79E0
completed_location: tasks/completed/TASK-CDI-001/
organized_files:
  - TASK-CDI-001.md
  - .claude/rules/patterns/orchestrators.md
---

# Task: Create orchestrators.md pattern file

## Description

Create `.claude/rules/patterns/orchestrators.md` to document multi-step workflow and orchestration patterns used throughout GuardKit.

This file was recommended in TASK-STE-001 analysis but not implemented in TASK-STE-007.

## Source

TASK-REV-79E0 code quality review identified this as a high-priority gap:
> "Missing `orchestrators.md` - Was documented in TASK-STE-001 recommendations but not created"

## Implementation

### File Location
`.claude/rules/patterns/orchestrators.md`

### Path Pattern
```yaml
---
paths: "**/*orchestrator.py", "**/*_orchestrator.py"
---
```

### Content Requirements

Extract patterns from GuardKit's actual orchestrator files:

1. **implement_orchestrator.py** (`installer/core/lib/`)
   - Pipeline step execution
   - State management with dataclasses
   - Error handling and recovery

2. **template_qa_orchestrator.py** (`installer/core/lib/template_creation/`)
   - Multi-phase workflow
   - Checkpoint-resume pattern
   - Validation chain

3. **orchestrator.py** (`installer/core/lib/agent_enhancement/`)
   - AI/static/hybrid strategy routing
   - State persistence
   - Dry-run mode

### Sections to Include

1. Frontmatter with paths
2. Multi-Step Workflow Pattern
3. Checkpoint-Resume Pattern
4. State Management Pattern
5. Error Recovery Pattern
6. Progress Reporting Pattern

## Acceptance Criteria

- [x] File created at `.claude/rules/patterns/orchestrators.md`
- [x] Frontmatter includes correct path pattern
- [x] Patterns extracted from actual GuardKit code (not generic)
- [x] Code examples with comments
- [x] Consistent formatting with other pattern files (~150-200 lines) - 385 lines total, includes 7 comprehensive patterns

## Notes

- Reference existing pattern files for formatting consistency
- Use NumPy-style docstrings in examples
- Include "When to use" guidance for each pattern
