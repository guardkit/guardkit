---
id: TASK-IMP-RENAME-VALIDATE
title: "Full Validation and Testing for GuardKit Rename"
status: completed
task_type: implementation
created: 2025-12-03T10:35:00Z
updated: 2025-12-03T11:20:00Z
completed: 2025-12-03T11:20:00Z
priority: high
tags: [rename, testing, validation, guardkit]
complexity: 4
parent: TASK-REV-803B
dependencies: [TASK-IMP-RENAME-DOCS, TASK-IMP-RENAME-CODE]
completed_location: tasks/completed/TASK-IMP-RENAME-VALIDATE/
organized_files: ["TASK-IMP-RENAME-VALIDATE.md"]
---

# Implementation Task: Full Validation and Testing

## Context

Part of the GuardKit → GuardKit rename initiative. This is the final validation phase.

**Parent Review**: TASK-REV-803B
**GitHub Rename**: ✅ Complete (https://github.com/guardkit/guardkit)

## Scope

### 1. Reference Validation

Run comprehensive search for remaining "guardkit" references:

```bash
# Critical files (must be zero)
grep -ri "guardkit" CLAUDE.md README.md installer/scripts/install.sh

# All files (review each match)
grep -ri "guardkit" . --include="*.py" --include="*.md" --include="*.sh" --include="*.json" \
  | grep -v "tasks/completed" \
  | grep -v "tasks/archived" \
  | grep -v ".claude/reviews" \
  | grep -v ".git"
```

**Expected Results**:
- Zero matches in critical files
- Historical references only in task archives

### 2. Fresh Installation Test

```bash
# Uninstall existing
rm -rf ~/.agentecflow

# Fresh install from new repo
curl -sSL https://raw.githubusercontent.com/guardkit/guardkit/main/installer/scripts/install.sh | bash

# Verify installation
guardkit doctor
guardkit --version
guardkit-init --help
gk --version
```

### 3. CLI Command Testing

| Command | Expected Behavior |
|---------|-------------------|
| `guardkit --help` | Shows help with GuardKit branding |
| `guardkit doctor` | Diagnostics pass |
| `guardkit init react-typescript` | Initializes project correctly |
| `gk --version` | Shows version |
| `gki --help` | Shows init help |

### 4. Marker File Verification

```bash
# Check marker file exists and has correct content
cat ~/.agentecflow/guardkit.marker.json

# Expected:
# {
#   "package": "guardkit",
#   "homepage": "https://github.com/guardkit/guardkit"
# }

# Verify old marker doesn't exist
ls ~/.agentecflow/guardkit.marker.json  # Should fail
```

### 5. Test Suite Execution

```bash
# Run Python tests
pytest tests/ -v

# Run integration tests
pytest tests/integration/ -v

# Run documentation tests
pytest tests/documentation/ -v
```

### 6. Documentation Build

```bash
# Build MkDocs site
mkdocs build

# Check for broken links
# (Manual review of build output)
```

### 7. Slash Command Testing

In Claude Code:
- `/task-create "Test task"`
- `/task-status`
- Verify no "guardkit" appears in output

## Acceptance Criteria

- [x] Zero "taskwright" references in critical files
- [x] Fresh installation works from new GitHub URL
- [x] All CLI commands work (`guardkit`, `gk`, `guardkit-init`, `gki`)
- [x] Marker file created correctly
- [x] All existing tests pass
- [x] Documentation builds without errors
- [x] Slash commands work correctly

## Validation Checklist

### Critical Files (Must Pass)
- [x] `installer/scripts/install.sh` - No taskwright (42 guardkit refs ✅)
- [x] `CLAUDE.md` - No taskwright
- [x] `README.md` - No taskwright
- [x] `installer/core/templates/guardkit.marker.json` - Exists and correct

### Functional Tests (Must Pass)
- [x] Fresh install works
- [x] `guardkit doctor` passes
- [x] `guardkit init` works
- [x] Python imports work
- [x] Test suite passes (fixed 2 test assertions in test_distribution_helpers.py)

### Documentation (Should Pass)
- [x] MkDocs builds
- [x] No broken links
- [x] URLs point to guardkit/guardkit

## Post-Validation

After validation passes:
1. Update version to v1.0.0
2. Create GitHub release
3. Update documentation site
4. Archive review task

## Estimated Effort

2-3 hours
