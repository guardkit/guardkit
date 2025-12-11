---
id: TASK-GI-003
title: Add post-init verification for rules structure
status: backlog
priority: low
created: 2025-12-11T19:45:00Z
updated: 2025-12-11T19:45:00Z
complexity: 2
tags: [guardkit-init, verification, ux]
related_to: [TASK-REV-INIT, TASK-GI-001]
implementation_mode: direct
---

# Task: Add Post-Init Verification for Rules Structure

## Problem

After running `guardkit init`, there's no verification that the rules structure was copied correctly. If the copy fails silently, users won't know their context optimization isn't working.

## Solution

Add a verification step at the end of initialization that:
1. Checks if the template had rules structure
2. Warns if expected rules weren't copied
3. Shows summary of what was initialized

## Implementation

### File to Modify

`installer/scripts/init-project.sh`

### Location

Add after `copy_template_files()` call in `main()` function, or at the end of `copy_template_files()`:

```bash
# Verify rules structure was copied correctly (if template had it)
verify_rules_structure() {
    local template_dir="$1"

    if [ -d "$template_dir/.claude/rules" ]; then
        if [ -d ".claude/rules" ]; then
            local template_rules=$(find "$template_dir/.claude/rules" -type f -name "*.md" | wc -l)
            local copied_rules=$(find ".claude/rules" -type f -name "*.md" | wc -l)

            if [ "$copied_rules" -ge "$template_rules" ]; then
                print_success "Rules structure verified ($copied_rules rule files)"
            else
                print_warning "Rules structure incomplete: expected $template_rules files, found $copied_rules"
            fi
        else
            print_warning "Rules structure expected but not found - Claude Code context optimization unavailable"
        fi
    fi
}
```

### Call Location

In `main()` after `copy_template_files`:

```bash
copy_template_files
verify_rules_structure "$AGENTECFLOW_HOME/templates/$TEMPLATE"
```

## Acceptance Criteria

- [ ] Verification runs after file copying
- [ ] Success message shows rule file count
- [ ] Warning shown if rules expected but missing
- [ ] Warning shown if rule count mismatch
- [ ] No error if template doesn't have rules (backward compatible)

## Testing

```bash
# Test with rules-enabled template
guardkit init react-typescript
# Should see: "Rules structure verified (X rule files)"

# Test with template without rules (if any exist)
# Should see: No rules-related message
```

## Complexity

- **Effort**: Low (~30 minutes)
- **Risk**: Low (diagnostic only, doesn't affect functionality)
- **Lines**: ~20 new lines
