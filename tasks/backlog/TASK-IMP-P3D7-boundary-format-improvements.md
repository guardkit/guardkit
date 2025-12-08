---
id: TASK-IMP-P3D7
title: "Implement boundary format and loading path improvements from TASK-REV-P3D7"
status: backlog
created: 2025-12-08T19:55:00Z
updated: 2025-12-08T19:55:00Z
priority: low
tags: [agent-enhance, progressive-disclosure, formatting]
task_type: implementation
complexity: 3
related_tasks: [TASK-REV-P3D7]
test_results:
  status: pending
  coverage: null
  last_run: null
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

1. `installer/global/agents/agent-content-enhancer.md` - Update boundary generation prompts
2. `installer/global/commands/agent-enhance.md` - Update format specifications
3. Potentially: `installer/global/commands/lib/agent_enhance_orchestrator.py` - If programmatic generation

## Implementation Notes

- These are cosmetic improvements with low impact
- Do not break existing functionality
- Consider adding validation for boundary format during enhancement
- Test with kartlog template to verify format

## Related Documentation

- Review Report: [.claude/reviews/TASK-REV-P3D7-review-report.md](../../.claude/reviews/TASK-REV-P3D7-review-report.md)
- CLAUDE.md Boundary Specification: Section "Agent Enhancement with Boundary Sections"
