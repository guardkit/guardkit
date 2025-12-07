---
id: TASK-DOC-18F9
title: Add troubleshooting sections consistently to all extended agent files
status: blocked
created: 2025-12-07T11:45:00Z
updated: 2025-12-07T12:30:00Z
priority: low
tags: [documentation, troubleshooting, agent-enhance]
complexity: 3
related_tasks: [TASK-REV-7C49]
previous_state: in_progress
blocked_reason: "Source files no longer exist - template directory deleted"
blocked_at: 2025-12-07T12:30:00Z
---

# Task: Add Troubleshooting Sections Consistently

## BLOCKED: Source Files Deleted

**Blocked At**: 2025-12-07T12:30:00Z
**Blocked By**: Automatic detection during /task-work execution

### Problem

The source files referenced in this task no longer exist:

1. `docs/reviews/progressive-disclosure/javascript-standard-structure-template/` - **Directory deleted**
2. The following agent files were supposed to be improved:
   - `firebase-firestore-specialist-ext.md` - **File deleted**
   - `svelte5-component-specialist-ext.md` - **File deleted**
   - `smui-material-ui-specialist-ext.md` - **File deleted**

### Evidence

Git status shows these files as deleted:
```
D docs/reviews/progressive-disclosure/javascript-standard-structure-template/agents/firebase-firestore-specialist.md
D docs/reviews/progressive-disclosure/javascript-standard-structure-template/agents/svelte5-component-specialist.md
...
```

The `agent-ehance-output/` directory exists but contains only empty placeholder files (0-1 bytes each).

### Resolution Options

1. **Cancel Task**: If the progressive disclosure review files are no longer needed
2. **Regenerate Files**: Re-run `/template-create` on the original source project to regenerate the template files
3. **Apply to Different Files**: Update this task to target different agent -ext.md files that do exist (e.g., in `installer/global/agents/` or template directories)

### Recommended Action

**Cancel this task** - The progressive disclosure review was a one-time activity. The template output files are no longer needed and have been cleaned up.

If troubleshooting sections need to be added to actual production agent files, create a new task targeting the existing files in:
- `installer/global/agents/*-ext.md`
- `installer/global/templates/*/agents/*-ext.md`

---

## Original Task Description

Some extended agent files have minimal or missing troubleshooting sections. Add consistent troubleshooting content to all extended files.

**Source**: Review finding from TASK-REV-7C49

## Original Current State

| Agent Extended File | Troubleshooting | Status |
|---------------------|-----------------|--------|
| external-api-integration-specialist-ext.md | ✅ Detailed | Good |
| alasql-in-memory-db-specialist-ext.md | ✅ Present | Good |
| pwa-vite-specialist.md | ✅ Present | Good |
| firebase-firestore-specialist-ext.md | ⚠️ Minimal | Needs improvement |
| svelte5-component-specialist-ext.md | ⚠️ Limited | Needs improvement |
| smui-material-ui-specialist-ext.md | ⚠️ Limited | Needs improvement |

## Target State

All extended files should have a "Troubleshooting" section with:
1. 3-5 common issues
2. Symptoms for each issue
3. Causes explained
4. Solutions with code examples

## Acceptance Criteria

- [ ] `firebase-firestore-specialist-ext.md` troubleshooting expanded
- [ ] `svelte5-component-specialist-ext.md` troubleshooting expanded
- [ ] `smui-material-ui-specialist-ext.md` troubleshooting expanded
- [ ] Consistent format across all troubleshooting sections
- [ ] Issues derived from actual codebase patterns

## Template

Use this format for troubleshooting sections:

```markdown
## Troubleshooting

### Issue: [Problem Description]

**Symptom**: [What the user sees]
**Cause**: [Why it happens]
**Solution**:
\`\`\`javascript
// Fix code here
\`\`\`
```

## Estimated Effort

Simple (1-3 complexity) - Documentation addition.
