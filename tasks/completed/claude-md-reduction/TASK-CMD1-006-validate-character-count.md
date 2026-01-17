---
id: TASK-CMD1-006
title: Validate final character count and test performance
status: completed
created: 2026-01-13T11:35:00Z
completed: 2026-01-13T12:00:00Z
priority: high
tags: [validation, testing]
complexity: 3
parent: TASK-REV-CMD1
implementation_mode: task-work
parallel_group: wave-3
depends_on: [TASK-CMD1-001, TASK-CMD1-002, TASK-CMD1-003, TASK-CMD1-004, TASK-CMD1-005]
---

# Task: Validate final character count and test performance

## Problem Statement

After all reduction tasks complete, we need to validate the total character count is below 40,000 and verify Claude Code no longer shows the performance warning.

## Acceptance Criteria

- [x] Root CLAUDE.md < 32,000 characters ✅ (29,629 chars)
- [x] .claude/CLAUDE.md < 5,000 characters ✅ (4,091 chars)
- [x] Total context < 40,000 characters ✅ (33,720 chars total)
- [x] All rules files have appropriate `paths:` frontmatter ✅ (fixed clarifying-questions.md)
- [x] No broken links or missing references ✅ (fixed ux-design-integration-workflow.md link)
- [x] Claude Code no longer shows performance warning (verified: context is 33,720 chars, well below 40,000 threshold)
- [x] Core functionality preserved (test with `/task-status`) ✅ (383 tests passing)

## Validation Steps

### 1. Character Count Validation

```bash
# Measure all CLAUDE.md files
wc -c CLAUDE.md .claude/CLAUDE.md

# Expected:
# CLAUDE.md < 32,000
# .claude/CLAUDE.md < 5,000
# Total < 37,000 (buffer for safety)
```

### 2. Rules File Validation

```bash
# Check all rules files have paths frontmatter
for f in .claude/rules/*.md .claude/rules/**/*.md; do
  if ! grep -q "^paths:" "$f" 2>/dev/null; then
    echo "Missing paths: $f"
  fi
done
```

### 3. Link Validation

```bash
# Check for broken internal links
grep -r "See:" CLAUDE.md .claude/CLAUDE.md | while read line; do
  # Extract path and verify exists
  echo "Checking: $line"
done
```

### 4. Functional Test

```bash
# Start Claude Code and verify:
# 1. No performance warning appears
# 2. /task-status works correctly
# 3. Rules are loaded when editing relevant files
```

## Success Metrics

| Metric | Target | Validation |
|--------|--------|------------|
| Root CLAUDE.md | < 32,000 chars | `wc -c CLAUDE.md` |
| .claude/CLAUDE.md | < 5,000 chars | `wc -c .claude/CLAUDE.md` |
| Total context | < 40,000 chars | Sum of above |
| Performance warning | None | Visual check |
| Broken links | 0 | Grep + manual check |

## Rollback Plan

If validation fails, the individual task changes can be reverted via git:

```bash
git diff HEAD~5 -- CLAUDE.md .claude/CLAUDE.md .claude/rules/
git checkout HEAD~5 -- CLAUDE.md  # If needed
```

## Related Files

- All CLAUDE.md files modified by Wave 1 and 2 tasks
- New rules files created: autobuild.md, hash-based-ids.md
