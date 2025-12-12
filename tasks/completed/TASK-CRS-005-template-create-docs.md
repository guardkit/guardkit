---
id: TASK-CRS-005
title: Update template-create Documentation
status: completed
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T16:45:00Z
completed: 2025-12-11T16:45:00Z
priority: medium
tags: [documentation, template-create, rules-structure]
complexity: 2
parent_feature: claude-rules-structure
wave: 3
implementation_mode: direct
conductor_workspace: claude-rules-wave3-3
estimated_hours: 1-2
actual_hours: 0.5
dependencies:
  - TASK-CRS-003
---

# Task: Update template-create Documentation

## Description

Update the `/template-create` command documentation to include the new `--use-rules-structure` flag and explain the rules structure output.

## File to Modify

`installer/core/commands/template-create.md`

## Changes Required

### 1. Add Flag to Usage Section

```markdown
## Usage

```bash
# Generate rules structure (experimental)
/template-create --use-rules-structure

# Combined with validation
/template-create --use-rules-structure --validate

# Custom name with rules structure
/template-create --name my-template --use-rules-structure
```

### 2. Add Rules Structure Output Section

```markdown
### Rules Structure Output (--use-rules-structure)

When using `--use-rules-structure`, the command generates a modular `.claude/rules/` directory:

```
~/.agentecflow/templates/{template_name}/
├── .claude/
│   ├── CLAUDE.md                    # Core documentation (~5KB)
│   └── rules/
│       ├── code-style.md            # paths: **/*.{ext}
│       ├── testing.md               # paths: **/*.test.*, **/tests/**
│       ├── patterns/
│       │   ├── repository.md
│       │   └── service-layer.md
│       └── agents/
│           ├── specialist-a.md      # paths: **/relevant/**
│           └── specialist-b.md
├── templates/
└── agents/                          # (legacy location, also generated)
```

**Benefits:**
- Path-specific loading: Rules only load when touching relevant files
- Reduced context window: 60-70% reduction vs single file
- Better organization: Related rules grouped in subdirectories
- Conditional agents: Agent guidance loads only when relevant

**Path Frontmatter:**

Rules files can include `paths:` frontmatter for conditional loading:

```markdown
---
paths: src/api/**/*.ts, **/router*.py
---

# API Development Rules

These rules apply only when editing API-related files.
```

**When to Use:**
- Large templates (>20KB CLAUDE.md)
- Complex multi-technology stacks
- Templates with many specialized agents
- Performance-critical workflows
```

### 3. Add Flag to Complete Workflow Section

Add to Phase 6 or create new phase:

```markdown
Phase 6: CLAUDE.md Generation (TASK-007)
├─ Template documentation
├─ Usage instructions
├─ Best practices
├─ Agent integration guide
└─ **[NEW] Rules structure generation (if --use-rules-structure)**
    ├─ Core CLAUDE.md (~5KB)
    ├─ rules/code-style.md
    ├─ rules/testing.md
    ├─ rules/patterns/*.md
    └─ rules/agents/*.md (with paths: frontmatter)
```

### 4. Add to Flags Reference

```markdown
## Flags Reference

| Flag | Default | Description |
|------|---------|-------------|
| `--use-rules-structure` | `false` | Generate modular .claude/rules/ structure (experimental) |
```

## Acceptance Criteria

- [x] Usage examples include `--use-rules-structure`
- [x] Output structure documented with directory tree
- [x] Path frontmatter syntax explained
- [x] Benefits listed (context reduction, organization)
- [x] When-to-use guidance provided
- [x] Workflow phase updated
- [x] Flag added to reference table

## Notes

- This is Wave 3 (parallel with CLI flag)
- Direct implementation (documentation only)
- Keep experimental label until Wave 4 complete

## Implementation Summary

Successfully updated the `/template-create` command documentation to support the new rules structure feature:

### Changes Made

1. **Usage Section** (lines 39-46)
   - Added 3 usage examples demonstrating `--use-rules-structure` flag
   - Shows standalone, combined with validation, and with custom name

2. **Rules Structure Output Section** (lines 236-281)
   - Comprehensive documentation of `.claude/rules/` directory structure
   - Visual directory tree showing organization
   - Benefits section highlighting 60-70% context reduction
   - Path frontmatter syntax explanation with example
   - When-to-use guidance for different use cases

3. **Workflow Phases** (lines 124-129)
   - Updated Phase 6 to include optional rules structure generation
   - Shows nested structure of generated files
   - Marked as [OPTIONAL] to indicate conditional behavior

4. **Command Options** (lines 369-383)
   - Added `--use-rules-structure` flag with detailed description
   - Includes default value, benefits, and use cases
   - Maintains experimental label as requested

### Files Modified

- `installer/core/commands/template-create.md` (+79 lines)

### Verification

All acceptance criteria met:
- ✅ Usage examples added (3 variations)
- ✅ Directory tree documented
- ✅ Path frontmatter explained with example
- ✅ Benefits clearly listed
- ✅ When-to-use guidance provided
- ✅ Phase 6 workflow updated
- ✅ Flag added to options section

### Git Commit

```
aa46008 Update template-create documentation with rules structure support
```
