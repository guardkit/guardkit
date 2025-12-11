---
id: TASK-CRS-011
title: Create Rules Structure Quick-Start Guide
status: in_review
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T18:45:00Z
priority: medium
tags: [documentation, quick-start, rules-structure]
complexity: 4
parent_feature: claude-rules-structure
wave: 5
implementation_mode: direct
conductor_workspace: claude-rules-wave5-1
estimated_hours: 4-6
dependencies:
  - TASK-CRS-003
---

# Task: Create Rules Structure Quick-Start Guide

## Description

Create a comprehensive quick-start guide for the Claude Code rules structure feature in `docs/guides/rules-structure-guide.md`.

## File to Create

`docs/guides/rules-structure-guide.md`

## Content Outline

```markdown
# Claude Code Rules Structure Guide

## Overview

Claude Code supports a modular rules structure that enables path-specific loading
of project instructions, reducing context window usage by 60-70%.

## When to Use Rules Structure

**Use Rules Structure When:**
- CLAUDE.md exceeds 15KB
- Template has multiple specialized agents
- Different patterns apply to different file types
- Context window optimization is critical

**Use Single CLAUDE.md When:**
- Simple projects (<10KB documentation)
- All rules apply universally
- No path-specific patterns needed

## Quick Start

### 1. Generate Rules Structure

```bash
/template-create --use-rules-structure
```

### 2. Structure Overview

```
.claude/
├── CLAUDE.md                # Core documentation (~5KB)
└── rules/
    ├── code-style.md        # paths: **/*.{ext}
    ├── testing.md           # paths: **/*.test.*, **/tests/**
    ├── patterns/
    │   └── {pattern}.md
    └── agents/
        └── {agent}.md       # paths: **/relevant/**
```

### 3. Path Patterns Reference

| Pattern | Matches |
|---------|---------|
| `**/*.ts` | All TypeScript files |
| `src/**/*` | All files under src/ |
| `**/tests/**` | Any tests/ directory |
| `{src,lib}/**/*.ts` | TypeScript in src/ or lib/ |
| `**/*query*, **/*api*` | Files containing query or api |

### 4. Creating Rule Files

```markdown
---
paths: src/api/**/*.ts, **/router*.py
---

# API Development Rules

- Validate all inputs
- Use consistent error responses
- Document with OpenAPI
```

## Converting Existing Templates

### Step 1: Identify Content Categories

Analyze your CLAUDE.md for:
- Code style (→ rules/code-style.md)
- Testing patterns (→ rules/testing.md)
- Architecture patterns (→ rules/patterns/)
- Agent guidance (→ rules/agents/)

### Step 2: Extract and Split

For each category:
1. Create rule file in appropriate directory
2. Add `paths:` frontmatter
3. Move relevant content
4. Verify paths match intended files

### Step 3: Verify Core CLAUDE.md

Core should contain:
- Project overview
- Technology stack summary
- Quick start commands
- Links to rules/ for details

Target size: ~5KB

## Best Practices

### Rule File Organization
- One topic per file
- Descriptive filenames
- Group related rules in subdirectories

### Path Pattern Tips
- Be specific to reduce false matches
- Test patterns with actual files
- Use negation (!) sparingly

### Agent Rules
- Include ALWAYS/NEVER/ASK boundaries
- Use paths for relevant file types
- Keep guidance focused

## Troubleshooting

### Rules Not Loading
- Check paths: frontmatter syntax
- Verify file extensions match
- Test with `/memory` command

### Too Many Rules Loading
- Make paths more specific
- Use subdirectories for organization
- Split overly broad patterns

## Examples

See template examples:
- [fastapi-python](../templates/fastapi-python/.claude/rules/)
- [react-typescript](../templates/react-typescript/.claude/rules/)
- [nextjs-fullstack](../templates/nextjs-fullstack/.claude/rules/)
```

## Acceptance Criteria

- [x] Guide created at `docs/guides/rules-structure-guide.md`
- [x] Overview explains what rules structure is
- [x] When-to-use decision guidance provided
- [x] Quick start with commands
- [x] Path patterns reference table
- [x] Conversion workflow documented
- [x] Best practices included
- [x] Troubleshooting section
- [x] Links to template examples

## Notes

- This is Wave 5 (documentation)
- Direct implementation
- Parallel with other documentation tasks
