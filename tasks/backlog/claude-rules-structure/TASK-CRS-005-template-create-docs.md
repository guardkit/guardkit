---
id: TASK-CRS-005
title: Update template-create Documentation
status: backlog
task_type: implementation
created: 2025-12-11T12:15:00Z
updated: 2025-12-11T12:15:00Z
priority: medium
tags: [documentation, template-create, rules-structure]
complexity: 2
parent_feature: claude-rules-structure
wave: 3
implementation_mode: direct
conductor_workspace: claude-rules-wave3-3
estimated_hours: 1-2
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

- [ ] Usage examples include `--use-rules-structure`
- [ ] Output structure documented with directory tree
- [ ] Path frontmatter syntax explained
- [ ] Benefits listed (context reduction, organization)
- [ ] When-to-use guidance provided
- [ ] Workflow phase updated
- [ ] Flag added to reference table

## Notes

- This is Wave 3 (parallel with CLI flag)
- Direct implementation (documentation only)
- Keep experimental label until Wave 4 complete
