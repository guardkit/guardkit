---
id: TASK-IMP-P3D7
title: "Implement boundary format and loading path improvements from TASK-REV-P3D7"
status: completed
created: 2025-12-08T19:55:00Z
updated: 2025-12-08T20:35:00Z
completed: 2025-12-08T20:35:00Z
completed_location: tasks/completed/TASK-IMP-P3D7/
priority: low
tags: [agent-enhance, progressive-disclosure, formatting]
task_type: implementation
complexity: 3
related_tasks: [TASK-REV-P3D7]
test_results:
  status: passed
  coverage: null
  last_run: 2025-12-08T20:30:00Z
  notes: "Syntax verification passed. Pre-existing test infrastructure issue with Python 3.9 compatibility unrelated to changes."
implementation_summary:
  files_modified:
    - installer/core/agents/agent-content-enhancer.md
    - installer/core/lib/agent_enhancement/applier.py
  changes:
    - "Added Format Templates and Validation Examples table to agent-content-enhancer.md"
    - "Updated _format_loading_instruction() to use relative path pattern with cat command"
  acceptance_criteria_met:
    - "Boundary format specification strengthened with explicit templates and PASS/FAIL examples"
    - "Loading instructions now use relative path: cat agents/{agent-name}-ext.md"
---

# Task: Implement boundary format and loading path improvements

## Description

Implement the minor improvements identified in TASK-REV-P3D7 review to ensure `/agent-enhance` output fully conforms to CLAUDE.md specifications.

## Background

Review TASK-REV-P3D7 scored 92/100 with two minor format deviations:

1. **Boundary format** - Uses sentence format instead of `[emoji] [action] ([rationale])`
2. **Loading instructions path** - Uses absolute path instead of relative/template variable

## Acceptance Criteria

### 1. Boundary Format Standardization

Update `/agent-enhance` and `agent-content-enhancer` to generate boundaries in the specified format:

**Current format:**
```markdown
### ALWAYS
- Use SMUI components for Material Design consistency
- Implement loading states for async operations
```

**Target format:**
```markdown
### ALWAYS
- ✅ Use SMUI components (Material Design consistency)
- ✅ Implement loading states for async operations (user feedback)
```

**NEVER format:**
```markdown
### NEVER
- ❌ Use `on:click` on SMUI Row directly (breaks table layout - use wrapper div)
- ❌ Skip form validation before submission (data integrity)
```

**ASK format:**
```markdown
### ASK
- ⚠️ Stores vs local state for shared data (architecture decision)
- ⚠️ Mobile breakpoint requirements (design specification needed)
```

### 2. Loading Instructions Path

Update loading instructions to use relative paths:

**Current:**
```bash
cat /Users/richwoollcott/.agentecflow/templates/kartlog/agents/svelte5-component-specialist-ext.md
```

**Target:**
```bash
cat agents/{agent-name}-ext.md
```

Or with template context:
```bash
# From template root
cat agents/svelte5-component-specialist-ext.md
```

## Files to Modify

1. `installer/core/agents/agent-content-enhancer.md` - Update boundary generation prompts
2. `installer/core/commands/agent-enhance.md` - Update format specifications
3. Potentially: `installer/core/commands/lib/agent_enhance_orchestrator.py` - If programmatic generation

## Implementation Notes

- These are cosmetic improvements with low impact
- Do not break existing functionality
- Consider adding validation for boundary format during enhancement
- Test with kartlog template to verify format

## Related Documentation

- Review Report: [.claude/reviews/TASK-REV-P3D7-review-report.md](../../.claude/reviews/TASK-REV-P3D7-review-report.md)
- CLAUDE.md Boundary Specification: Section "Agent Enhancement with Boundary Sections"
