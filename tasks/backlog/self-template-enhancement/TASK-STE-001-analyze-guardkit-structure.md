---
id: TASK-STE-001
title: Run template-create --dry-run analysis on GuardKit
status: backlog
created: 2025-12-13T13:00:00Z
priority: high
tags: [analysis, template-create, dry-run, guardkit]
parent_task: TASK-REV-1DDD
implementation_mode: direct
wave: 1
conductor_workspace: self-template-wave1-guardkit
complexity: 3
---

# Task: Run template-create --dry-run analysis on GuardKit

## Description

Run `/template-create --dry-run` on the GuardKit repository to understand what improvements would be generated. This is reference-only analysis - no files will be modified.

## Objective

Generate analysis output showing:
- Quality scores for existing agents
- Gaps in agent content
- Suggested rules structure
- Enhancement opportunities

## Commands

```bash
cd /Users/richardwoollcott/Projects/appmilla_github/guardkit
/template-create --name guardkit-analysis --dry-run --save-analysis
```

## Expected Output

1. Analysis JSON file with:
   - Agent quality scores
   - Placeholder detection
   - Rules structure recommendations
   - Content gaps

2. Summary report showing:
   - Which agents need enhancement
   - Which rules would be created
   - Overall quality assessment

## Acceptance Criteria

- [ ] Analysis command executed successfully
- [ ] Output saved for review
- [ ] Key findings documented
- [ ] Recommendations identified for Wave 2/3 tasks

## Notes

- This is a direct execution task (no /task-work needed)
- Can run in parallel with TASK-STE-002
- Output informs Wave 2 agent enhancement tasks
