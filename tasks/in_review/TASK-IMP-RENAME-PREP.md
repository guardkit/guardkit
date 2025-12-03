---
id: TASK-IMP-RENAME-PREP
title: "Create Migration Scripts and Backup for GuardKit Rename"
status: in_review
task_type: implementation
created: 2025-12-03T10:35:00Z
updated: 2025-12-03T11:30:00Z
priority: critical
tags: [rename, infrastructure, migration, guardkit]
complexity: 5
parent: TASK-REV-803B
dependencies: []
---

# Implementation Task: Create Migration Scripts and Backup

## Context

Part of the Taskwright → GuardKit rename initiative. This task creates the foundation for safe migration.

**Parent Review**: TASK-REV-803B
**GitHub Rename**: ✅ Complete (https://github.com/guardkit/guardkit)

## Scope

Create scripts to automate the bulk rename process safely:

1. **Backup Script** (`scripts/backup-pre-rename.sh`)
   - Create timestamped backup branch
   - Export current state summary

2. **Bulk Rename Script** (`scripts/rename-taskwright-to-guardkit.py`)
   - Search/replace with case handling:
     - `taskwright-dev` → `guardkit`
     - `Taskwright` → `GuardKit`
     - `TASKWRIGHT` → `GUARDKIT`
     - `taskwright` → `guardkit`
     - `tw` (CLI alias) → `gk`
     - `twi` (CLI alias) → `gki`
   - Exclusion list:
     - `tasks/completed/*` (historical)
     - `tasks/archived/*` (historical)
     - `.claude/reviews/*` (historical)
     - `.git/*`
   - Generate change report

3. **Validation Script** (`scripts/validate-rename.sh`)
   - Check no "taskwright" remains in critical files
   - List any remaining references (for review)

## Acceptance Criteria

- [x] Backup script creates branch `backup/pre-guardkit-rename-YYYYMMDD-HHMMSS`
- [x] Rename script handles all case variations
- [x] Rename script excludes historical files
- [x] Rename script generates change report
- [x] Validation script confirms critical files are clean
- [x] All scripts are executable and documented

## Technical Notes

- Use Python for rename script (better regex handling)
- Use bash for backup/validation scripts
- Scripts should be idempotent (safe to run multiple times)

## Files Created

- `scripts/backup-pre-rename.sh` ✅
- `scripts/rename-taskwright-to-guardkit.py` ✅
- `scripts/validate-rename.sh` ✅

## Implementation Summary

### Scripts Created

1. **backup-pre-rename.sh** (127 lines)
   - Creates timestamped backup branch
   - Exports state summary to `.claude/state/`
   - Interactive confirmation for uncommitted changes
   - Clear rollback instructions

2. **rename-taskwright-to-guardkit.py** (350+ lines)
   - Comprehensive replacement patterns with case handling
   - Binary file detection (extension + null byte check)
   - Git-aware file renaming with `git mv`
   - Dry-run mode for safe preview
   - Markdown change report generation

3. **validate-rename.sh** (220+ lines)
   - 5-section validation (critical files, markers, solution files, codebase search, CLI aliases)
   - Exit codes for CI/CD integration (0=pass, 1=critical, 2=warnings)
   - Clear next-steps guidance

### Dry-Run Results

- **Files to modify**: 574
- **Total replacements**: 5,600
- **Files to rename**: 4
- **Errors**: 0

### Code Review Score: 8.5/10

Key strengths:
- Excellent safety mechanisms (backup, dry-run, validation)
- Comprehensive error handling
- Strong user experience (colors, progress, guidance)

## Estimated Effort

2-3 hours

## Next Steps

1. Run backup: `./scripts/backup-pre-rename.sh`
2. Execute rename: `python3 scripts/rename-taskwright-to-guardkit.py`
3. Validate: `./scripts/validate-rename.sh`
4. Review changes: `git diff`
5. Commit: `git add -A && git commit -m "Rename Taskwright to GuardKit"`
