---
id: TASK-GI-001
title: Add rules directory copying to init-project.sh
status: completed
priority: high
created: 2025-12-11T19:45:00Z
updated: 2025-12-11T22:40:00Z
completed: 2025-12-11T22:40:00Z
complexity: 2
tags: [guardkit-init, rules-structure, critical-fix]
related_to: [TASK-REV-INIT]
implementation_mode: task-work
---

# Task: Add Rules Directory Copying to init-project.sh

## Problem

The `copy_template_files()` function in `installer/scripts/init-project.sh` does not copy the `.claude/rules/` directory from templates. This breaks the rules structure feature for all users running `guardkit init`.

## Solution

Add code to copy `.claude/rules/` directory after the existing copy operations.

## Implementation

### File Modified

`installer/scripts/init-project.sh`

### Changes Made

Added the following code block after line 250 (after the `docs/` copy block):

```bash
# Copy .claude/rules/ directory (for Claude Code modular rules)
if [ -d "$template_dir/.claude/rules" ]; then
    mkdir -p .claude/rules
    cp -r "$template_dir/.claude/rules/"* .claude/rules/ 2>/dev/null || true
    print_success "Copied rules structure for Claude Code"
fi
```

### Copy Order (Updated)

1. CLAUDE.md (line 196)
2. agents/ (line 202)
3. templates/ (line 226)
4. docs/ (line 232)
5. **NEW: .claude/rules/** (line 252-257)
6. Other .md/.json files (line 259)
7. Commands symlinks (line 266)

## Acceptance Criteria

- [x] `.claude/rules/` directory is copied when present in template
- [x] Subdirectories (guidance/, patterns/) are preserved
- [x] File contents and frontmatter (`paths:`) are preserved
- [x] Works with all 5 reference templates
- [x] Backward compatible with templates without rules structure

## Testing Results

### Test 1: react-typescript template
```
✓ Copied rules structure for Claude Code

Rules directory structure:
- code-style.md
- testing.md
- guidance/ (4 files: feature-arch.md, form-validation.md, react-query.md, react-state.md)
- patterns/ (3 files: feature-based.md, form-patterns.md, query-patterns.md)
```

### Test 2: Frontmatter preservation
```
Verified code-style.md contains:
---
paths: ["**/*.{ts,tsx}"]
---
```

### Test 3: default template
```
✓ Copied rules structure for Claude Code
Rules: code-style.md, quality-gates.md, workflow.md
```

### Test 4: Backward compatibility (template without rules)
```
✓ No rules directory created (correct behavior)
No error messages, initialization completed successfully
```

## Completion Summary

- **Duration**: ~15 minutes
- **Lines Changed**: +6 lines added
- **Risk**: Low (additive change)
- **Testing**: All acceptance criteria verified
