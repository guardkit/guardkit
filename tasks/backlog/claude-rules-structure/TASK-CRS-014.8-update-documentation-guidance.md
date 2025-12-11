---
id: TASK-CRS-014.8
title: Update documentation for rules/guidance/ naming
status: backlog
task_type: implementation
created: 2025-12-11T15:00:00Z
updated: 2025-12-11T15:00:00Z
priority: medium
tags: [rules-structure, naming, documentation]
complexity: 2
parent_task: TASK-CRS-014
implementation_mode: direct
estimated_hours: 0.5
---

# Task: Update documentation for rules/guidance/ naming

## Background

Documentation needs updating to reflect the `rules/agents/` → `rules/guidance/` rename and clarify the distinction between:
- `agents/` - Full specialist agent definitions (for Task tool and /agent-enhance)
- `rules/guidance/` - Path-based contextual guidance (static, loaded by Claude Code)

## Changes Required

### 1. Root CLAUDE.md

Search and update any references to `rules/agents`:
```bash
grep -n "rules/agents" CLAUDE.md
```

Add clarification about the two "agent" concepts if needed.

### 2. Feature README

Update `tasks/backlog/claude-rules-structure/README.md`:
- Update directory structure examples
- Clarify naming rationale

### 3. Implementation Guide

Update `tasks/backlog/claude-rules-structure/IMPLEMENTATION-GUIDE.md`:
- Update target structure examples
- Update any code snippets

### 4. Progressive Disclosure Guide

Check `docs/guides/progressive-disclosure.md` for any `rules/agents` references.

### 5. Rules Structure Guide (if exists)

Check for any dedicated guide about rules structure.

## Search Command

```bash
grep -r "rules/agents" \
  CLAUDE.md \
  .claude/CLAUDE.md \
  docs/ \
  tasks/backlog/claude-rules-structure/ \
  installer/core/commands/*.md \
  2>/dev/null
```

## Acceptance Criteria

- [ ] All documentation references updated to `rules/guidance/`
- [ ] Clear explanation of `agents/` vs `rules/guidance/` distinction
- [ ] No orphaned `rules/agents` references in docs

## Documentation Clarification to Add

```markdown
## Directory Structure Clarification

GuardKit uses two different "agent" concepts:

### `agents/` Directory
Full specialist agent definitions used by:
- `/agent-enhance` command for enhancement
- Task tool for invoking specialists
- Agent discovery system

These are rich, AI-enhanced specifications with:
- Full YAML frontmatter (name, tools, model, capabilities)
- Detailed examples and boundaries
- Progressive disclosure split (-ext.md files)

### `rules/guidance/` Directory
Path-based contextual guidance loaded automatically by Claude Code when editing specific files.

These are lightweight, static rules with:
- `paths:` frontmatter for conditional loading
- Concise ALWAYS/NEVER/ASK rules
- Links to full agent docs for detailed reference

**Key distinction**: `agents/` are invokable specialists; `rules/guidance/` are passive context.
```

## Verification

```bash
# Verify no orphaned references
grep -r "rules/agents" . --include="*.md" | grep -v ".git" | grep -v "node_modules"
```

## Notes

- This is a documentation task only, no code changes
- Can be done in parallel with other subtasks
- Should be completed after code changes so docs reflect final state
