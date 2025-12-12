# Implementation Guide: guardkit-init-rules-fix

## Overview

This feature fixes the `guardkit init` command to properly support the rules structure that provides 60-70% context window reduction.

## Wave Breakdown

### Wave 1: Critical Fix (Required)

| Task | Description | Effort | Dependencies |
|------|-------------|--------|--------------|
| TASK-GI-001 | Add .claude/rules/ copying | 30 min | None |

**Execute**: `/task-work TASK-GI-001`

### Wave 2: Improvements (Recommended)

| Task | Description | Effort | Dependencies |
|------|-------------|--------|--------------|
| TASK-GI-002 | Handle both CLAUDE.md locations | 15 min | None |
| TASK-GI-003 | Add post-init verification | 30 min | TASK-GI-001 |

**Execute in parallel or sequentially**:
```bash
/task-work TASK-GI-002
/task-work TASK-GI-003
```

## Estimated Total Effort

- Wave 1: ~30 minutes
- Wave 2: ~45 minutes
- **Total**: ~1.25 hours

## Verification Checklist

After all tasks complete:

```bash
# 1. Create test directory
mkdir -p /tmp/guardkit-init-test && cd /tmp/guardkit-init-test

# 2. Test with react-typescript (has rules structure)
guardkit init react-typescript

# 3. Verify rules structure
echo "=== Verifying rules structure ==="
ls -la .claude/rules/
ls -la .claude/rules/guidance/
ls -la .claude/rules/patterns/

# 4. Verify CLAUDE.md
echo "=== Verifying CLAUDE.md ==="
head -20 .claude/CLAUDE.md

# 5. Check for paths: frontmatter preservation
echo "=== Verifying paths: frontmatter ==="
head -5 .claude/rules/guidance/react-query.md

# 6. Cleanup
cd ~ && rm -rf /tmp/guardkit-init-test
```

## Rollback Plan

If issues arise, the changes are isolated to `installer/scripts/init-project.sh`. Rollback by reverting the file:

```bash
git checkout HEAD~1 -- installer/scripts/init-project.sh
```

## Notes

- All changes are additive and backward compatible
- Templates without rules structure will work unchanged
- The fix benefits all users immediately upon next `guardkit init`
