---
id: TASK-CRS-012
title: Update Root CLAUDE.md for Rules Structure
status: completed
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T12:15:00Z
completed: 2025-12-11T12:30:00Z
priority: medium
tags: [documentation, claude-md, rules-structure]
complexity: 4
parent_feature: claude-rules-structure
wave: 5
implementation_mode: direct
conductor_workspace: claude-rules-wave5-2
estimated_hours: 3-4
dependencies:
  - TASK-CRS-003
---

# Task: Update Root CLAUDE.md for Rules Structure

## Description

Update the root `CLAUDE.md` to document the new rules structure feature and its integration with GuardKit templates.

## File to Modify

`CLAUDE.md` (root)

## Changes Required

### 1. Add Rules Structure Section

Add new section after "Progressive Disclosure" section:

```markdown
## Claude Code Rules Structure

GuardKit templates support Claude Code's modular rules structure for optimized context loading.

### When to Use

| Scenario | Recommendation |
|----------|---------------|
| Simple templates (<15KB) | Single CLAUDE.md with split |
| Complex templates (>15KB) | Rules structure |
| Path-specific patterns | Rules structure |
| Universal rules only | Single CLAUDE.md |

### Structure Overview

```
.claude/
├── CLAUDE.md                    # Core documentation (~5KB)
└── rules/
    ├── code-style.md            # paths: **/*.{ext}
    ├── testing.md               # paths: **/*.test.*
    ├── patterns/
    │   └── {pattern}.md
    └── agents/
        └── {agent}.md           # paths: **/relevant/**
```

### Generating Rules Structure

```bash
# Generate with rules structure
/template-create --use-rules-structure

# Default (single CLAUDE.md with progressive disclosure)
/template-create
```

### Path-Specific Loading

Rules files can include `paths:` frontmatter for conditional loading:

```markdown
---
paths: src/api/**/*.ts, **/router*.py
---

# API Development Rules
...
```

Rules without `paths:` frontmatter load unconditionally.

### Benefits

- **60-70% context reduction** - Rules load only when relevant
- **Better organization** - Related rules grouped in subdirectories
- **Conditional agents** - Agent guidance loads for relevant files only
- **Recursive discovery** - Subdirectories automatically scanned

**See**: [Rules Structure Guide](docs/guides/rules-structure-guide.md)
```

### 2. Update Template Creation Section

Update the `/template-create` command documentation to mention:

```markdown
### Template Creation Commands

```bash
# Default output (progressive disclosure)
/template-create

# With rules structure (experimental)
/template-create --use-rules-structure
```
```

### 3. Update Progressive Disclosure Section

Add note about rules structure:

```markdown
## Progressive Disclosure

GuardKit uses progressive disclosure to optimize context window usage.

### Two Approaches

1. **Split Files** (Default)
   - Core `{name}.md` always loaded
   - Extended `{name}-ext.md` loaded on-demand
   - 55-60% token reduction

2. **Rules Structure** (Optional)
   - Modular `.claude/rules/` directory
   - Path-specific conditional loading
   - 60-70% token reduction
   - Use with `--use-rules-structure` flag

**When to Choose:**
- Use split files for simpler projects
- Use rules structure for complex, multi-technology templates
```

### 4. Update Template Philosophy Section

Add mention of rules structure as alternative:

```markdown
### Output Options

| Flag | Output | Use Case |
|------|--------|----------|
| (default) | CLAUDE.md + ext files | Most templates |
| `--use-rules-structure` | rules/ directory | Large templates, path-specific needs |
```

## Acceptance Criteria

- [x] Rules Structure section added
- [x] Structure overview with directory tree
- [x] Command examples for generation
- [x] Path-specific loading explained
- [x] Benefits listed
- [x] Link to detailed guide
- [x] Progressive Disclosure section updated
- [x] Template Creation section updated

## Notes

- This is Wave 5 (documentation)
- Direct implementation
- Parallel with other documentation tasks
- Keep experimental label until more adoption
