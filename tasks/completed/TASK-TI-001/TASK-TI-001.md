---
id: TASK-TI-001
title: Add rules structure flags to template-init command
status: completed
created: 2025-12-12T10:45:00Z
updated: 2025-12-12T12:00:00Z
completed: 2025-12-12T12:05:00Z
priority: high
tags: [template-init, rules-structure, documentation, flags]
complexity: 3
implementation_method: direct
wave: 1
conductor_workspace: null
parent_feature: template-init-rules-structure
completed_location: tasks/completed/TASK-TI-001/
---

# Task: Add Rules Structure Flags to template-init Command

## Description

Add command-line flags to `/template-init` for controlling rules structure generation, matching the flags available in `/template-create`.

## Implementation Method

**Direct** (Claude Code) - Documentation-only change, no Python code required.

## What to Do

Edit `installer/core/commands/template-init.md` to add:

### 1. Add to Options Table

```markdown
| `--use-rules-structure` | flag | true | Generate modular .claude/rules/ structure |
| `--no-rules-structure` | flag | false | Use single CLAUDE.md instead of rules/ |
| `--claude-md-size-limit` | SIZE | 50KB | Maximum size for core CLAUDE.md content |
```

### 2. Add Flag Descriptions

Add after existing options (around line 34):

```markdown
--use-rules-structure    Generate modular .claude/rules/ structure (default: enabled)
                         Default: true

                         By default:
                         - Creates .claude/rules/ directory
                         - Generates rule files with path frontmatter
                         - Groups patterns and agents in subdirectories
                         - Core CLAUDE.md reduced to ~5KB
                         - 60-70% context window reduction

                         Benefits:
                         - Better organization for complex templates
                         - Path-specific rule loading
                         - Improved maintainability

--no-rules-structure     Use single CLAUDE.md + progressive disclosure instead
                         of modular rules/ directory structure

                         Use when:
                         - Simple templates (<15KB)
                         - Universal rules only (no path-specific patterns)
                         - Backward compatibility needed

--claude-md-size-limit SIZE  Maximum size for core CLAUDE.md content
                             Format: NUMBER[KB|MB] (e.g., 100KB, 1MB)
                             Default: 50KB
                             Use for complex codebases that exceed default limit
```

### 3. Add Examples

Add example showing rules structure output:

```markdown
### Rules Structure Output (Default)
```bash
/template-init

# Default behavior generates modular .claude/rules/ structure

✅ Template Package Created Successfully!

📁 Location: ~/.agentecflow/templates/my-template/
  ├── manifest.json
  ├── settings.json
  ├── .claude/
  │   ├── CLAUDE.md (core, ~5KB)
  │   └── rules/
  │       ├── code-style.md
  │       ├── testing.md
  │       ├── patterns/
  │       └── guidance/
  ├── templates/
  └── agents/
```

### Opt-Out Example
```bash
/template-init --no-rules-structure

# Uses single CLAUDE.md without rules/ directory
```
```

### 4. Update Feature Comparison Table

Update the comparison table (around line 534) to add:

```markdown
| **Rules Structure** | ✅ Default | ✅ Default |
| **Progressive Disclosure** | ✅ Yes | ✅ Yes |
| **Agent Split Files** | ✅ Yes | ✅ Yes |
```

## Acceptance Criteria

- [x] `--use-rules-structure` flag documented with description
- [x] `--no-rules-structure` flag documented with description
- [x] `--claude-md-size-limit` flag documented with description
- [x] Examples updated to show rules structure output
- [x] Feature comparison table updated
- [x] Documentation consistent with `/template-create`

## Files to Modify

- `installer/core/commands/template-init.md`

## Notes

This task is documentation-only. The actual flag implementation will be done in TASK-TI-002 when the rules structure generation code is added.

## Related Tasks

- TASK-TI-002: Generate rules structure (implements these flags)
- TASK-REV-TI01: Source review task
