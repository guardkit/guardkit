---
id: TASK-IMP-RENAME-INFRA
title: "Update Installer, Marker Files, and CLI Commands for GuardKit"
status: backlog
task_type: implementation
created: 2025-12-03T10:35:00Z
updated: 2025-12-03T10:35:00Z
priority: critical
tags: [rename, infrastructure, installer, cli, guardkit]
complexity: 7
parent: TASK-REV-803B
dependencies: [TASK-IMP-RENAME-PREP]
---

# Implementation Task: Update Core Infrastructure

## Context

Part of the Taskwright → GuardKit rename initiative. This task updates the critical infrastructure files.

**Parent Review**: TASK-REV-803B
**GitHub Rename**: ✅ Complete (https://github.com/guardkit/guardkit)

## Scope

### 1. Update `installer/scripts/install.sh`

**Current References (63 occurrences)**:
- Line 21: `GITHUB_REPO="https://github.com/taskwright-dev/taskwright"`
- Line 42: ASCII art header "Taskwright Installation System"
- Lines 591-860: CLI command creation (`taskwright`, `taskwright-init`)
- Shell integration references

**Changes Required**:
- Update GitHub URL to `https://github.com/guardkit/guardkit`
- Update branding to "GuardKit Installation System"
- Rename CLI commands:
  - `taskwright` → `guardkit`
  - `taskwright-init` → `guardkit-init`
  - `tw` → `gk`
  - `twi` → `gki`
- Update all help text and messages

### 2. Rename Marker Files

| Current | New |
|---------|-----|
| `installer/global/templates/taskwright.marker.json` | `installer/global/templates/guardkit.marker.json` |
| Runtime: `~/.agentecflow/taskwright.marker.json` | Runtime: `~/.agentecflow/guardkit.marker.json` |

**Content Changes**:
```json
{
  "package": "guardkit",  // was "taskwright"
  "homepage": "https://github.com/guardkit/guardkit"
}
```

### 3. Update `installer/scripts/init-project.sh`

- Update all Taskwright references
- Update help text
- Update error messages

### 4. Update Detection Logic

Files with marker detection:
- `installer/global/commands/lib/feature_detection.py`
- `installer/global/commands/lib/distribution_helpers.py`

## Acceptance Criteria

- [ ] `install.sh` uses new GitHub URL
- [ ] CLI commands renamed to `guardkit`, `guardkit-init`, `gk`, `gki`
- [ ] Marker files renamed and content updated
- [ ] `init-project.sh` updated with new branding
- [ ] Detection logic updated to find `guardkit.marker.json`
- [ ] Fresh installation works with new URLs
- [ ] No "taskwright" references in installer/* (except historical comments)

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
- `installer/global/templates/taskwright.marker.json` → rename
- `installer/global/commands/lib/feature_detection.py`
- `installer/global/commands/lib/distribution_helpers.py`

## Estimated Effort

2-3 hours
