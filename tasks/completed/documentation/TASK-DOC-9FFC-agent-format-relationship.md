---
id: TASK-DOC-9FFC
title: Add Relationship with agent-format section to agent-enhance.md
status: completed
created: 2025-11-27T02:00:00Z
updated: 2025-11-27T07:49:09Z
completed: 2025-11-27T07:49:09Z
priority: high
tags: [documentation, agent-enhance, agent-format]
complexity: 3
related_to: [TASK-DOC-F3BA]
duration_hours: 0.5
---

# Task: Add "Relationship with /agent-format" Section to agent-enhance.md

## Context

Review task TASK-DOC-F3BA identified that agent-enhance.md doesn't explain the relationship between `/agent-format` and `/agent-enhance`, leaving users confused about when to use each command.

The two commands serve different purposes in a two-tier enhancement system:
- **agent-format**: Template-level agent formatting (6/10 quality, fast, generic)
- **agent-enhance**: Project-level agent enhancement (9/10 quality, AI-powered, template-specific)

## Objective

Add a new section to agent-enhance.md explaining the two-tier enhancement system and providing clear guidance on when to use each command.

## Scope

### Files to Update

1. **installer/core/commands/agent-enhance.md**:
   - Add new section "Relationship with /agent-format" after "Enhancement Strategies"
   - Explain two-tier system (template-level vs project-level)
   - Add decision matrix: when to use /agent-format vs /agent-enhance
   - Include quality comparison (6/10 vs 9/10)
   - Cross-reference to template-create.md Phase 5.5

## Acceptance Criteria

- [x] New section "Relationship with /agent-format" added
- [x] Two-tier enhancement system explained (template-level vs project-level)
- [x] Decision matrix table created showing when to use each command
- [x] Quality comparison documented (6/10 format vs 9/10 enhance)
- [x] Duration comparison included (instant vs 2-5 min)
- [x] Use case examples for both commands
- [x] Cross-reference to template-create.md Phase 5.5 added
- [x] Consistent formatting with existing sections

## Implementation Notes

**Suggested Content Structure**:

```markdown
## Relationship with /agent-format

### Two-Tier Enhancement System

Taskwright uses a two-tier approach to agent quality:

1. **Template-Level Formatting** (`/agent-format`)
   - **Quality**: 6/10 (basic structure)
   - **Method**: Structural formatting only (no AI)
   - **Duration**: Instant (<1 second)
   - **Use**: During `/template-create` for consistent agent structure

2. **Project-Level Enhancement** (`/agent-enhance`)
   - **Quality**: 9/10 (AI-powered, template-specific)
   - **Method**: AI-generated content with boundary validation
   - **Duration**: 2-5 minutes per agent
   - **Use**: After `/template-create` for template-specific content

### When to Use Each

| Scenario | Command | Rationale |
|----------|---------|-----------|
| Creating template from codebase | `/agent-format` | Automatic in `/template-create`, ensures consistent structure |
| Enhancing template agents with examples | `/agent-enhance` | Adds code examples, best practices from templates |
| Quick agent structure fixes | `/agent-format` | Fast structural corrections |
| Adding template-specific guidance | `/agent-enhance` | AI analyzes templates for relevant content |

### Workflow Integration

```bash
# Step 1: Create template (uses /agent-format automatically)
/template-create --path ~/my-project

# Step 2: Enhance agents with template-specific content
/agent-enhance my-template/api-specialist --hybrid
/agent-enhance my-template/testing-specialist --hybrid

# Or use tasks (created by --create-agent-tasks)
/task-work TASK-AGENT-XXX
```

### Quality Comparison

- **Format (6/10)**: Consistent structure, generic content, no AI
- **Enhance (9/10)**: Template-specific examples, boundary validation, AI-powered

Both quality levels are intentional:
- Format provides baseline consistency for all templates
- Enhance adds project-specific depth where needed
```

**Cross-references**:
- Link to `template-create.md` Phase 5.5 (agent formatting)
- Link to `template-create.md` Phase 8 (agent enhancement tasks)

## Source

**Review Report**: [TASK-DOC-F3BA Review Report](../../../.claude/task-plans/TASK-DOC-F3BA-review-report.md)
**Priority**: P2 (High)
**Estimated Effort**: 2-3 hours

## Method

**Claude Code Direct** - Documentation update, no testing needed
