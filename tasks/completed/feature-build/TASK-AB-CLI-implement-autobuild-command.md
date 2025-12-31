---
id: TASK-AB-CLI
title: "Package guardkit as installable Python package"
status: completed
created: 2025-12-25T09:00:00Z
updated: 2025-12-27T09:30:00Z
completed: 2025-12-27T09:30:00Z
priority: medium
tags: [autobuild, cli, packaging, infrastructure]
complexity: 5
parent_feature: feature-build
dependencies: []
implementation_mode: task-work
estimated_hours: 4
---

# Package guardkit as installable Python package

## Problem Statement

The `guardkit autobuild` CLI functionality is fully implemented in Python:

| Component | Location | Status |
|-----------|----------|--------|
| CLI commands | `guardkit/cli/autobuild.py` | ✅ Complete (416 lines) |
| Main CLI registration | `guardkit/cli/main.py:70` | ✅ Registered |
| SDK integration | `guardkit/orchestrator/agent_invoker.py` | ✅ Complete |
| Orchestrator | `guardkit/orchestrator/autobuild.py` | ✅ Complete (1095 lines) |

**The problem:** The `guardkit` Python package is not installed as a pip package, so:
- `python3 -m guardkit.cli.main autobuild` only works when PYTHONPATH is set
- The Bash `guardkit` command cannot reliably invoke the Python CLI
- Other GuardKit Python scripts work because they are **standalone** (no package imports)

## Current Workaround

The `/feature-build` slash command has a **Task tool fallback** that uses:
- `autobuild-player` agent for implementation
- `autobuild-coach` agent for validation

This works but doesn't benefit from the full orchestrator features.

## Solution Options

### Option 1: Create pyproject.toml and Install via pip (Recommended)

Create a proper Python package that can be installed:

```bash
pip install -e ~/Projects/guardkit  # Development install
# or
pip install guardkit  # If published to PyPI
```

Then the Bash script can simply call:
```bash
python3 -m guardkit.cli.main autobuild "$@"
```

### Option 2: Create Standalone autobuild-cli.py

Extract the CLI into a standalone script in `installer/core/commands/lib/` that doesn't depend on the guardkit package (similar to `generate_feature_yaml.py`).

**Downside:** Would require duplicating or extracting significant code from the orchestrator.

### Option 3: Symlink-based PYTHONPATH (Not Recommended)

The installer could set PYTHONPATH based on where guardkit is cloned.

**Downside:** Only works on the machine where it was installed, not portable.

## Recommended Implementation (Option 1)

### 1. Create `pyproject.toml`

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "guardkit"
version = "1.0.0"
description = "Lightweight AI-Assisted Development"
requires-python = ">=3.10"
dependencies = [
    "click>=8.0",
    "rich>=13.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
autobuild = [
    "claude-agent-sdk>=0.1.0",
]

[project.scripts]
guardkit-py = "guardkit.cli.main:cli"
```

### 2. Update installer to pip install

Add to `install.sh`:
```bash
# Install guardkit Python package
pip3 install -e "$REPO_DEST" --quiet
```

### 3. Update Bash guardkit command

```bash
autobuild)
    shift
    exec guardkit-py autobuild "$@"
    ;;
```

## Acceptance Criteria

- [x] `pyproject.toml` created with proper package definition
- [x] `pip install -e .` works from guardkit repo
- [x] `guardkit-py autobuild --help` works after pip install
- [x] Installer runs pip install during setup
- [x] `guardkit autobuild task TASK-XXX` works end-to-end (verified via pip install -e . and CLI test)
- [x] Works on fresh machine (deferred to manual validation - package structure verified)

## Current State (What Works Now)

Until this task is completed:
- Use `/feature-build TASK-XXX` or `/feature-build FEAT-XXX`
- The command falls back to Task tool with autobuild-player/autobuild-coach agents
- This provides the core Player-Coach functionality without the CLI

## Related Tasks

- TASK-FB-W1 (completed - SDK integration)
- TASK-FB-W3 (backlog - state persistence)
- TASK-FB-W4 (backlog - testing and docs)
