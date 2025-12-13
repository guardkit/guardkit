---
id: TASK-STE-002
title: Run template-create --dry-run analysis on fastapi-python template
status: backlog
created: 2025-12-13T13:00:00Z
priority: high
tags: [analysis, template-create, dry-run, fastapi, python]
parent_task: TASK-REV-1DDD
implementation_mode: direct
wave: 1
conductor_workspace: self-template-wave1-fastapi
complexity: 3
---

# Task: Run template-create --dry-run analysis on fastapi-python template

## Description

Run `/template-create --dry-run` on the fastapi-python template to understand what improvements would be generated. This is reference-only analysis - no files will be modified.

## Objective

Generate analysis output showing:
- Quality scores for fastapi-specialist, fastapi-testing-specialist, fastapi-database-specialist
- Content gaps in existing agents
- Suggested rules structure for Python files
- Enhancement opportunities specific to Python/FastAPI

## Commands

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit
/template-create --name fastapi-analysis --dry-run --save-analysis \
  --source installer/core/templates/fastapi-python
```

## Expected Output

1. Analysis JSON file with:
   - Agent quality scores (current: 8.2/10 overall)
   - Code example coverage
   - Boundary definition completeness
   - Discovery metadata validation

2. Summary report showing:
   - Which agents need content enhancement
   - Recommended rules structure for Python
   - Path-specific loading opportunities

## Acceptance Criteria

- [ ] Analysis command executed successfully
- [ ] Output saved for review
- [ ] Key findings documented for each of 3 FastAPI agents
- [ ] Rules structure recommendations captured

## Notes

- This is a direct execution task (no /task-work needed)
- Can run in parallel with TASK-STE-001
- Output directly informs TASK-STE-003, 004, 005, and 006
