# Feature: Fix Graphiti Check Python Environment Resolution

**Parent Review**: TASK-REV-4219
**Feature ID**: FEAT-GC42

## Problem

The `graphiti_check.py` script fails to detect Graphiti availability because both invocation paths resolve to system Python, which lacks `graphiti-core`. This causes `/system-arch` and other Graphiti-dependent commands to silently skip knowledge graph persistence.

## Root Cause

1. CLI path: `~/.agentecflow/bin/graphiti-check` symlink uses shebang `#!/usr/bin/env python3` which resolves to system Python
2. Module path: `python -m installer.core.commands.lib.graphiti_check` uses ambient `python` which also resolves to system Python
3. Secondary: symlink target lacks execute permission

## Solution

1. Replace symlink with bash wrapper that explicitly uses guardkit venv Python
2. Update command specs to use wrapper or explicit venv path
3. Harden installer's graphiti-core installation step
4. Fix execute permission on graphiti_check.py

## Subtasks

| Task | Title | Wave | Method | Priority |
|------|-------|------|--------|----------|
| TASK-FIX-GC01 | Wrapper script + chmod | 1 | task-work | P0/P1 |
| TASK-FIX-GC02 | Update command specs | 1 | direct | P1 |
| TASK-FIX-GC03 | Harden installer graphiti-core install | 2 | task-work | P2 |
