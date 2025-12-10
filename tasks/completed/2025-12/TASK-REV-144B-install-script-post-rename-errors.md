---
id: TASK-REV-144B
title: Diagnose Install Script Errors After Global→Core Rename
status: completed
task_type: review
created: 2025-12-10T18:15:00Z
updated: 2025-12-10T18:50:00Z
completed: 2025-12-10T18:50:00Z
priority: critical
tags: [installation, debugging, rename-impact, blocking]
complexity: 5
review_mode: decision
review_depth: standard
parent_task: TASK-RENAME-GLOBAL
review_results:
  mode: decision
  depth: standard
  findings_count: 4
  recommendations_count: 2
  decision: implement
  report_path: .claude/reviews/TASK-REV-144B-review-report.md
  fix_applied: true
  fix_summary: "Replaced 26 occurrences of /global/ with /core/ in install.sh"
---

# Diagnose Install Script Errors After Global→Core Rename

## Problem Statement

After renaming `installer/global/` to `installer/core/`, the installation script (`install.sh`) fails with multiple errors:

1. **No agents found**: `⚠ No agents found to install`
2. **No Python scripts found**: `⚠ No Python command scripts found`
3. **Python import validation failed**: `❌ ERROR: Python import validation failed - No module named 'lib'`

## Error Log

```
ℹ Installing global AI agents...
⚠ No agents found to install
ℹ Creating placeholder agents...
✓ Created core placeholder agents

ℹ Setting up Python command script symlinks...
⚠ No Python command scripts found

ℹ Validating installation...
❌ ERROR: Python import validation failed
   No module named 'lib'

   This is a bug in the installation script.
   Please report this issue with the error message above.
```

## Scope of Review

### 1. Identify Path References in install.sh

The script likely still references `installer/global/` paths that need updating to `installer/core/`:

- Agent installation paths
- Python script symlink paths
- Import validation test paths

### 2. Identify Import Validation Issue

The `No module named 'lib'` error suggests:
- The validation script tries to import from a path that no longer exists
- OR the PYTHONPATH isn't set correctly for the new directory structure

### 3. Check All install.sh Path Variables

Variables to audit:
- `GLOBAL_DIR` or similar
- Agent source directory
- Command source directory
- Python lib source directory

## Files to Investigate

1. **Primary**: `installer/scripts/install.sh`
2. **Secondary**: Any validation scripts called by install.sh
3. **Related**: `installer/core/` directory structure (verify rename completed)

## Acceptance Criteria

- [ ] All `installer/global` references in install.sh identified
- [ ] Root cause of "No agents found" determined
- [ ] Root cause of "No Python command scripts found" determined
- [ ] Root cause of "No module named 'lib'" determined
- [ ] Fix recommendations documented with specific line numbers
- [ ] Impact on TASK-RENAME-GLOBAL assessed (may need to be updated)

## Review Questions

1. Was the rename from `installer/global` to `installer/core` pushed to the remote repository?
2. Are there hardcoded paths in install.sh that weren't updated?
3. Is the Python validation using a relative import that assumes old structure?
4. Should TASK-RENAME-GLOBAL be updated to include install.sh modifications?

## Execution

```bash
/task-review TASK-REV-144B --mode=decision --depth=standard
```

## Notes

- This is a **blocking issue** - installation is broken for new users
- The rename may have been done locally but install.sh wasn't updated
- Need to check if `installer/core/` exists on the remote (cloned repo)
