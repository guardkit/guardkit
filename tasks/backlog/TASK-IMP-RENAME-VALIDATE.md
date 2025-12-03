---
id: TASK-IMP-RENAME-VALIDATE
title: "Full Validation and Testing for GuardKit Rename"
status: backlog
task_type: implementation
created: 2025-12-03T10:35:00Z
updated: 2025-12-03T10:35:00Z
priority: high
tags: [rename, testing, validation, guardkit]
complexity: 4
parent: TASK-REV-803B
dependencies: [TASK-IMP-RENAME-DOCS, TASK-IMP-RENAME-CODE]
---

# Implementation Task: Full Validation and Testing

## Context

Part of the Taskwright → GuardKit rename initiative. This is the final validation phase.

**Parent Review**: TASK-REV-803B
**GitHub Rename**: ✅ Complete (https://github.com/guardkit/guardkit)

## Scope

### 1. Reference Validation

Run comprehensive search for remaining "taskwright" references:

```bash
# Critical files (must be zero)
grep -ri "taskwright" CLAUDE.md README.md installer/scripts/install.sh

# All files (review each match)
grep -ri "taskwright" . --include="*.py" --include="*.md" --include="*.sh" --include="*.json" \
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
ls ~/.agentecflow/taskwright.marker.json  # Should fail
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
- Verify no "taskwright" appears in output

## Acceptance Criteria

- [ ] Zero "taskwright" references in critical files
- [ ] Fresh installation works from new GitHub URL
- [ ] All CLI commands work (`guardkit`, `gk`, `guardkit-init`, `gki`)
- [ ] Marker file created correctly
- [ ] All existing tests pass
- [ ] Documentation builds without errors
- [ ] Slash commands work correctly

## Validation Checklist

### Critical Files (Must Pass)
- [ ] `installer/scripts/install.sh` - No taskwright
- [ ] `CLAUDE.md` - No taskwright
- [ ] `README.md` - No taskwright
- [ ] `~/.agentecflow/guardkit.marker.json` - Exists and correct

### Functional Tests (Must Pass)
- [ ] Fresh install works
- [ ] `guardkit doctor` passes
- [ ] `guardkit init` works
- [ ] Python imports work
- [ ] Test suite passes

### Documentation (Should Pass)
- [ ] MkDocs builds
- [ ] No broken links
- [ ] URLs point to guardkit/guardkit

## Post-Validation

After validation passes:
1. Update version to v1.0.0
2. Create GitHub release
3. Update documentation site
4. Archive review task

## Estimated Effort

2-3 hours
