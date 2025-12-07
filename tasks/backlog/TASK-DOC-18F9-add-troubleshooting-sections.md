---
id: TASK-DOC-18F9
title: Add troubleshooting sections consistently to all extended agent files
status: backlog
created: 2025-12-07T11:45:00Z
updated: 2025-12-07T11:45:00Z
priority: low
tags: [documentation, troubleshooting, agent-enhance]
complexity: 3
related_tasks: [TASK-REV-7C49]
---

# Task: Add Troubleshooting Sections Consistently

## Description

Some extended agent files have minimal or missing troubleshooting sections. Add consistent troubleshooting content to all extended files.

**Source**: Review finding from TASK-REV-7C49

## Current State

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
