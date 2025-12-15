---
id: TASK-FIX-a1b2
title: Fix settings.json to use ~ instead of hardcoded user path
status: completed
created: 2025-12-15T12:30:00Z
updated: 2025-12-15T13:15:00Z
completed: 2025-12-15T13:15:00Z
priority: medium
tags: [bug, installer, portability]
complexity: 2
---

# Task: Fix settings.json to use ~ instead of hardcoded user path

## Description

When running `guardkit init <template>`, the generated `.claude/settings.json` writes an absolute path with the current user's home directory instead of using `~` for portability.

**Current behavior:**
```json
{
  "extends": "/Users/richardwoollcott/.agentecflow/templates/fastapi-python"
}
```

**Expected behavior:**
```json
{
  "extends": "~/.agentecflow/templates/fastapi-python"
}
```

## Problem

Hardcoded paths cause issues when:
- Sharing projects between users
- Publishing demo repositories (like guardkit-examples)
- Working across different machines

## Acceptance Criteria

- [x] `guardkit init` writes `~/.agentecflow/...` in settings.json
- [x] Existing projects with hardcoded paths still work (backwards compatible)
- [x] Test with `guardkit init fastapi-python` on fresh directory

## Implementation

**File Modified**: `installer/scripts/init-project.sh`

**Change**: In the `create_config()` function, changed from using `$AGENTECFLOW_HOME` directly (which expands to absolute path) to using a literal `~/.agentecflow` string for portability.

**Before** (line 315):
```bash
"extends": "$AGENTECFLOW_HOME/templates/$TEMPLATE",
```

**After**:
```bash
# Use ~ for portability instead of absolute path
local extends_path="~/.agentecflow/templates/$TEMPLATE"
...
"extends": "$extends_path",
```

## Backwards Compatibility

Existing projects with hardcoded absolute paths will continue to work because:
- The `extends` field is informational metadata
- Actual template resolution uses the live `$AGENTECFLOW_HOME` environment variable
- No code currently parses and expands the `extends` field for file operations

## Test Plan

```bash
# Create temp directory
mkdir /tmp/test-init && cd /tmp/test-init

# Run init
guardkit init fastapi-python

# Verify settings.json uses ~
cat .claude/settings.json | grep extends
# Should show: "extends": "~/.agentecflow/templates/fastapi-python"
```

## Completion Notes

- Fix implemented in `installer/scripts/init-project.sh`
- Also updated guardkit-examples repo branches (00-starter, 02-auth-task-implemented) to use portable paths
- Squashed fix commit into original 00-starter branch for clean history
