---
id: TASK-FW-009
title: Update documentation (CLAUDE.md, task-review.md, feature-plan.md)
status: backlog
created: 2025-12-04T11:00:00Z
updated: 2025-12-04T11:00:00Z
priority: medium
tags: [feature-workflow, documentation]
complexity: 3
implementation_mode: direct
parallel_group: null
conductor_workspace: null
parent_review: TASK-REV-FW01
dependencies: [TASK-FW-008]
---

# Update Documentation

## Description

Update all relevant documentation to reflect the new `/feature-plan` command and enhanced [I]mplement functionality.

## Acceptance Criteria

- [ ] Update CLAUDE.md with `/feature-plan` command section
- [ ] Update task-review.md with enhanced [I]mplement documentation
- [ ] Complete feature-plan.md command documentation
- [ ] Add examples and usage patterns
- [ ] Update workflow diagrams if present
- [ ] Add to command index/reference

## Documentation Updates

### 1. CLAUDE.md Updates

Add to "Essential Commands" section:
```markdown
### Feature Planning Workflow
\`\`\`bash
/feature-plan "feature description"  # Single command to plan feature
\`\`\`
```

Add new section "Feature Planning Workflow":
```markdown
## Feature Planning Workflow

The `/feature-plan` command provides a streamlined, single-command
experience for planning new features.

### Usage
\`\`\`bash
/feature-plan "implement dark mode"
\`\`\`

### What Happens
1. Creates review task with correct flags
2. Executes `/task-review --mode=decision`
3. On [I]mplement: Auto-creates subfolder structure

### Auto-Generated Artifacts
- `tasks/backlog/{feature-slug}/` subfolder
- README.md with feature documentation
- IMPLEMENTATION-GUIDE.md with wave breakdown
- All subtasks with implementation mode tagging

### Example Flow
\`\`\`bash
$ /feature-plan "implement dark mode"

✅ Auto-detected:
   Feature slug: dark-mode
   Subtasks: 7 (from recommendations)
   Parallel groups: 3 waves

Creating tasks/backlog/dark-mode/
  ├── README.md
  ├── IMPLEMENTATION-GUIDE.md
  ├── TASK-DM-001-add-css-variables.md (direct, wave 1)
  ...

Next: Review IMPLEMENTATION-GUIDE.md and start with Wave 1
\`\`\`
```

### 2. task-review.md Updates

Update [I]mplement section:
```markdown
### [I]mplement Option (Enhanced)

When you choose [I]mplement, the system now automatically:

1. **Auto-detects feature slug** from review title
2. **Auto-detects subtasks** from recommendations
3. **Assigns implementation modes** (task-work/direct/manual)
4. **Groups parallel-safe tasks** into waves
5. **Creates subfolder** with all artifacts

No manual prompts required - everything is auto-detected!
```

### 3. feature-plan.md Completion

Ensure the command file created in FW-001 is complete with:
- Full usage examples
- Error handling documentation
- Integration with task-review
- Troubleshooting section

### 4. Index Updates

Update any command indexes or references:
- `docs/commands.md` if exists
- README.md command reference
- Any CLI help text

## Files to Modify

- `CLAUDE.md`
- `installer/global/commands/task-review.md`
- `installer/global/commands/feature-plan.md`
- `README.md` (if command reference exists)

## Test Plan

1. Verify CLAUDE.md examples are accurate
2. Verify task-review.md reflects actual behavior
3. Verify feature-plan.md is complete and correct
4. Check for broken links

## Dependencies

Must complete after FW-008 (orchestration) so documentation reflects actual behavior.

## Notes

Low complexity (3) - documentation updates only.
Should be done last (Wave 4) to document final behavior.
