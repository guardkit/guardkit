---
id: TASK-TC-DEFAULT-FLAGS
title: Change /template-create default flags to include --use-rules-structure and --claude-md-size-limit 50KB
status: completed
task_type: implementation
created: 2025-12-11T17:45:00Z
updated: 2025-12-11T18:30:00Z
completed: 2025-12-11T18:30:00Z
priority: high
tags: [template-create, defaults, rules-structure, progressive-disclosure]
complexity: 3
related_to: [TASK-REV-CB0F]
---

# Task: Change /template-create Default Flags

## Background

Review TASK-REV-CB0F identified that:
1. CLAUDE.md generation fails with default 10KB limit on complex templates
2. Rules structure provides better organization and 60-70% context reduction
3. Users must manually specify `--use-rules-structure --claude-md-size-limit 50KB` for best results

## Problem Statement

Current defaults:
- `--claude-md-size-limit`: 10KB (too small for real-world templates)
- `--use-rules-structure`: false (opt-in)

This causes:
- CLAUDE.md generation failures on complex templates
- Users don't benefit from rules structure unless they know to enable it
- Suboptimal first-run experience

## Proposed Changes

### Change 1: Default `--claude-md-size-limit` to 50KB

**File**: `installer/core/commands/lib/template_create_orchestrator.py`

```python
# Before
parser.add_argument('--claude-md-size-limit', type=str, default='10KB')

# After
parser.add_argument('--claude-md-size-limit', type=str, default='50KB')
```

**Rationale**: 50KB accommodates most real-world templates while still encouraging progressive disclosure. Users can still override with `--claude-md-size-limit 10KB` if they want stricter limits.

### Change 2: Default `--use-rules-structure` to True

**File**: `installer/core/commands/lib/template_create_orchestrator.py`

```python
# Before
parser.add_argument('--use-rules-structure', action='store_true', default=False)

# After
parser.add_argument('--use-rules-structure', action='store_true', default=True)
parser.add_argument('--no-rules-structure', action='store_true', default=False,
                    help='Disable rules structure, use single CLAUDE.md instead')
```

**Rationale**: Rules structure is the recommended approach per CLAUDE.md and provides significant benefits. Backward compatibility maintained via `--no-rules-structure` opt-out.

### Change 3: Update Command Documentation

**File**: `installer/core/commands/template-create.md`

Update the flags section to reflect new defaults and add `--no-rules-structure` documentation.

### Change 4: Update CLAUDE.md

**File**: `CLAUDE.md` (root)

Update the Template Creation section to reflect new defaults:

```markdown
### Output Options

| Flag | Default | Description |
|------|---------|-------------|
| `--claude-md-size-limit` | 50KB | Maximum size for CLAUDE.md |
| `--use-rules-structure` | true | Use rules/ directory structure |
| `--no-rules-structure` | false | Opt-out of rules structure |
```

## Acceptance Criteria

- [x] `--claude-md-size-limit` defaults to 50KB
- [x] `--use-rules-structure` defaults to true
- [x] `--no-rules-structure` flag added for opt-out
- [x] Command documentation updated
- [x] CLAUDE.md updated with new defaults
- [x] Existing tests pass (21/21)
- [x] New tests added for opt-out behavior (4 new tests)

## Testing

```bash
# Test new defaults (should produce rules structure)
/template-create --name test-template

# Test opt-out (should produce single CLAUDE.md)
/template-create --name test-template --no-rules-structure

# Test size limit override
/template-create --name test-template --claude-md-size-limit 10KB
```

## Migration Notes

- Existing templates are not affected
- Users with scripts using `--use-rules-structure` explicitly will continue to work
- Users wanting single-file output should use `--no-rules-structure`
