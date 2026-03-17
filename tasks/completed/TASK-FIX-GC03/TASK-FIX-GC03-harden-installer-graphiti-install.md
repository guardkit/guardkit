---
id: TASK-FIX-GC03
title: Harden installer graphiti-core installation step
status: completed
created: 2026-03-17T12:00:00Z
updated: 2026-03-17T17:10:00Z
completed: 2026-03-17T17:10:00Z
completed_location: tasks/completed/TASK-FIX-GC03/
priority: medium
tags: [graphiti, installer, hardening]
parent_review: TASK-REV-4219
feature_id: FEAT-GC42
implementation_mode: task-work
wave: 2
complexity: 3
depends_on:
  - TASK-FIX-GC01
---

# Task: Harden installer graphiti-core installation step

## Description

The installer (`install.sh` lines 355-385) attempts to install `graphiti-core` into system Python with `--break-system-packages` and `--user` fallbacks. This silently fails on PEP 668 managed environments (Python 3.11+).

Improve this section to:
1. Log which Python path is being used
2. Verify the import actually works after installation
3. Provide clear, actionable warning if installation fails
4. Consider whether this system-level install is still needed given the wrapper script fix (TASK-FIX-GC01)

## Files to Modify

- `installer/scripts/install.sh` — lines 355-385 (graphiti-core installation section)

## Acceptance Criteria

- [x] Installer logs the Python path being used for graphiti-core install
- [x] Installer verifies `python3 -c "from graphiti_core import Graphiti"` succeeds after install
- [x] Clear warning with remediation steps if installation fails
- [x] Comment explaining relationship to wrapper script (GC01) — system install is belt-and-suspenders

## Test Execution Log

- **Bash syntax check**: `bash -n install.sh` — PASSED
- **Unit tests**: 154 passed, 0 failed (1.87s)
- **Pre-existing failures** (unrelated): `test_lint_discovery.py` (missing module), `test_graphiti_list.py` (mock issue)
