---
id: TASK-FIX-PD06
title: Fix init script to copy docs/ directory from templates
status: completed
created: 2025-12-07T15:00:00Z
updated: 2025-12-07T16:00:00Z
completed: 2025-12-07T16:05:00Z
priority: critical
tags: [template-init, progressive-disclosure, bug-fix]
complexity: 2
related_tasks: [TASK-FIX-PD01]
completed_location: tasks/completed/TASK-FIX-PD06/
test_results:
  status: passed
  coverage: 100
  last_run: 2025-12-07T16:00:00Z
---

# Task: Fix Init Script to Copy docs/ Directory from Templates

## Description

The `guardkit init` command (implemented in `installer/scripts/init-project.sh`) does not copy the `docs/` directory from templates. This breaks progressive disclosure functionality because:

1. `/template-create` generates templates with `docs/patterns/README.md` and `docs/reference/README.md`
2. The generated `CLAUDE.md` references these files (fixed in TASK-FIX-PD01)
3. But `guardkit init` doesn't copy them, so users get broken references

### Current Behavior

```
template/
├── CLAUDE.md              ✅ Copied by init
├── docs/
│   ├── patterns/
│   │   └── README.md      ❌ NOT copied
│   └── reference/
│       └── README.md      ❌ NOT copied
├── agents/                ✅ Copied by init
└── manifest.json          ✅ Copied by init
```

### Expected Behavior

```
template/
├── CLAUDE.md              ✅ Copied by init
├── docs/
│   ├── patterns/
│   │   └── README.md      ✅ Should be copied
│   └── reference/
│       └── README.md      ✅ Should be copied
├── agents/                ✅ Copied by init
└── manifest.json          ✅ Copied by init
```

## Root Cause

The `copy_template_files()` function in `init-project.sh` (lines 169-252) explicitly copies:
- `CLAUDE.md`
- `agents/*`
- `templates/*`
- Other `.md` and `.json` files in root

But it does NOT copy the `docs/` subdirectory.

## Acceptance Criteria

- [x] `guardkit init <template>` copies `docs/patterns/` to project's `docs/patterns/`
- [x] `guardkit init <template>` copies `docs/reference/` to project's `docs/reference/`
- [x] Existing `docs/` content is preserved (merge, don't overwrite)
- [x] Works for all templates that have `docs/` directory
- [x] Success message printed when docs are copied

## Files to Modify

- `installer/scripts/init-project.sh` - Add docs/ directory copy logic to `copy_template_files()` function

## Implementation Notes

Add after line 229 (after templates/ copy):

```bash
# Copy template docs (patterns/reference for progressive disclosure)
if [ -d "$template_dir/docs" ]; then
    # Create docs subdirectories if they don't exist
    mkdir -p docs/patterns docs/reference

    # Copy patterns if exists
    if [ -d "$template_dir/docs/patterns" ]; then
        cp -r "$template_dir/docs/patterns/"* docs/patterns/ 2>/dev/null || true
    fi

    # Copy reference if exists
    if [ -d "$template_dir/docs/reference" ]; then
        cp -r "$template_dir/docs/reference/"* docs/reference/ 2>/dev/null || true
    fi

    print_success "Copied template documentation (patterns/reference)"
fi
```

## Test Plan

1. Create a template with `/template-create` that has docs/ directory
2. Run `guardkit init <template-name>` in a new project
3. Verify `docs/patterns/README.md` exists
4. Verify `docs/reference/README.md` exists
5. Verify CLAUDE.md loading instructions work (files exist at referenced paths)

## Related

- TASK-FIX-PD01: Fixed CLAUDE.md file path references (completed)
- Progressive disclosure feature depends on this fix
