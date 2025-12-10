---
id: TASK-IMP-RENAME-INFRA
title: "Update Installer, Marker Files, and CLI Commands for GuardKit"
status: completed
task_type: implementation
created: 2025-12-03T10:35:00Z
updated: 2025-12-03T11:15:00Z
completed: 2025-12-03T11:15:00Z
priority: critical
tags: [rename, infrastructure, installer, cli, guardkit]
complexity: 7
parent: TASK-REV-803B
dependencies: [TASK-IMP-RENAME-PREP]
completed_location: tasks/completed/TASK-IMP-RENAME-INFRA/
organized_files: ["TASK-IMP-RENAME-INFRA.md"]
---

# Implementation Task: Update Core Infrastructure

## Context

Part of the GuardKit → GuardKit rename initiative. This task updates the critical infrastructure files.

**Parent Review**: TASK-REV-803B
**GitHub Rename**: ✅ Complete (https://github.com/guardkit/guardkit)

## Scope

### 1. Update `installer/scripts/install.sh`

**Current References (63 occurrences)**:
- Line 21: `GITHUB_REPO="https://github.com/guardkit/guardkit"`
- Line 42: ASCII art header "GuardKit Installation System"
- Lines 591-860: CLI command creation (`guardkit`, `guardkit-init`)
- Shell integration references

**Changes Required**:
- Update GitHub URL to `https://github.com/guardkit/guardkit`
- Update branding to "GuardKit Installation System"
- Rename CLI commands:
  - `guardkit` → `guardkit`
  - `guardkit-init` → `guardkit-init`
  - `gk` → `gk`
  - `gki` → `gki`
- Update all help text and messages

### 2. Rename Marker Files

| Current | New |
|---------|-----|
| `installer/core/templates/guardkit.marker.json` | `installer/core/templates/guardkit.marker.json` |
| Runtime: `~/.agentecflow/guardkit.marker.json` | Runtime: `~/.agentecflow/guardkit.marker.json` |

**Content Changes**:
```json
{
  "package": "guardkit",  // was "guardkit"
  "homepage": "https://github.com/guardkit/guardkit"
}
```

### 3. Update `installer/scripts/init-project.sh`

- Update all GuardKit references
- Update help text
- Update error messages

### 4. Update Detection Logic

Files with marker detection:
- `installer/core/commands/lib/feature_detection.py`
- `installer/core/commands/lib/distribution_helpers.py`

## Acceptance Criteria

- [x] `install.sh` uses new GitHub URL
- [x] CLI commands renamed to `guardkit`, `guardkit-init`, `gk`, `gki`
- [x] Marker files renamed and content updated
- [x] `init-project.sh` updated with new branding
- [x] Detection logic updated to find `guardkit.marker.json`
- [x] Fresh installation works with new URLs
- [x] No "guardkit" references in installer/* (except historical comments)

## Testing

```bash
# After changes, test fresh install
./installer/scripts/install.sh --test-mode

# Verify CLI commands
guardkit --help
guardkit-init --help
gk --version

# Verify marker file created
cat ~/.agentecflow/guardkit.marker.json
```

## Critical Files

- `installer/scripts/install.sh` (63 occurrences)
- `installer/scripts/init-project.sh` (16 occurrences)
- `installer/core/templates/guardkit.marker.json` → rename
- `installer/core/commands/lib/feature_detection.py`
- `installer/core/commands/lib/distribution_helpers.py`

## Estimated Effort

2-3 hours
