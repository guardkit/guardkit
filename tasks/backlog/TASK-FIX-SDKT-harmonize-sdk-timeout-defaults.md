---
id: TASK-FIX-SDKT
title: Harmonize SDK timeout defaults to 900s across codebase
status: backlog
task_type: implementation
created: 2026-01-24T11:00:00Z
updated: 2026-01-24T11:00:00Z
priority: medium
tags: [feature-build, sdk-timeout, configuration, consistency]
complexity: 2
parent_review: TASK-REV-FB01
---

# Task: Harmonize SDK timeout defaults to 900s across codebase

## Description

Fix inconsistent SDK timeout defaults across the GuardKit codebase. Currently there are 4 different "default" values documented/configured in different locations, causing user confusion.

## Background

From TASK-REV-FB01 review findings:
- CLI help text says 600s (outdated)
- Orchestrators use 900s
- AgentInvoker has 1800s fallback
- Users expect one consistent default

## Changes Required

### 1. Fix CLI help text (2 locations)

**File**: `guardkit/cli/autobuild.py`

**Line ~158** (task command):
```python
# FROM:
help="SDK timeout in seconds (60-3600). Defaults to task frontmatter autobuild.sdk_timeout or 600",

# TO:
help="SDK timeout in seconds (60-3600). Defaults to task frontmatter autobuild.sdk_timeout or 900",
```

**Line ~450** (feature command):
```python
# FROM:
help="SDK timeout in seconds (60-3600). Defaults to feature YAML autobuild.sdk_timeout or 600",

# TO:
help="SDK timeout in seconds (60-3600). Defaults to feature YAML autobuild.sdk_timeout or 900",
```

### 2. Fix AgentInvoker default

**File**: `guardkit/orchestrator/agent_invoker.py`

**Line ~97**:
```python
# FROM:
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "1800"))

# TO:
DEFAULT_SDK_TIMEOUT = int(os.environ.get("GUARDKIT_SDK_TIMEOUT", "900"))
```

### 3. Fix docstring

**File**: `guardkit/orchestrator/agent_invoker.py`

**Line ~444** (in `__init__` docstring):
```python
# FROM:
sdk_timeout_seconds: Timeout for SDK invocations (default: 600s)

# TO:
sdk_timeout_seconds: Timeout for SDK invocations (default: 900s)
```

## Acceptance Criteria

- [ ] All 4 locations updated to reference 900s as default
- [ ] `guardkit autobuild task --help` shows 900s
- [ ] `guardkit autobuild feature --help` shows 900s
- [ ] Test run without `--sdk-timeout` flag shows `SDK timeout: 900s` in logs
- [ ] Existing tests pass

## Test Plan

1. Run existing test suite: `pytest tests/ -v`
2. Manual verification:
   ```bash
   guardkit autobuild task --help | grep timeout
   guardkit autobuild feature --help | grep timeout
   ```
3. Run a test task and verify log output shows 900s

## Notes

- This is a documentation/consistency fix, not a behavioral change
- The orchestrators already default to 900s, so actual runtime behavior is unchanged
- Future consideration: If timeouts remain frequent, TASK-REV-FB01 recommends increasing to 1200s
