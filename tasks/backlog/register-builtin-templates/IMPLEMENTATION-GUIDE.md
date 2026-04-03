# Implementation Guide: Register Builtin Templates

## Feature: FEAT-RBT
## Parent Review: TASK-REV-DF07

## Execution Strategy

### Wave 1: Fix Template Metadata (Parallel)

Two independent tasks that can run in parallel:

| Task | Title | Complexity | Method |
|------|-------|-----------|--------|
| TASK-RBT-001 | Fix nats-asyncio-service metadata | 3 | task-work |
| TASK-RBT-002 | Fix python-library template | 6 | task-work |

**TASK-RBT-001** is straightforward metadata fixes (manifest.json, settings.json).

**TASK-RBT-002** is more involved: manifest rewrite, settings rewrite, CLAUDE.md rewrite, JS artifact removal, agent generalization. This is the critical-path task.

### Wave 2: Register as Builtins (Sequential)

| Task | Title | Complexity | Method |
|------|-------|-----------|--------|
| TASK-RBT-003 | Register both templates as builtins | 4 | task-work |

Copy templates, update 4 registration points (init.py, CLAUDE.md, install.sh, help text).

### Wave 3: Post-Registration (Parallel)

| Task | Title | Complexity | Method |
|------|-------|-----------|--------|
| TASK-RBT-004 | Run agent-enhance on both templates | 2 | direct |
| TASK-RBT-005 | Verify guardkit init end-to-end | 2 | direct |

## Dependency Graph

```
TASK-RBT-001 (Wave 1) ──┐
                         ├──> TASK-RBT-003 (Wave 2) ──┬──> TASK-RBT-004 (Wave 3)
TASK-RBT-002 (Wave 1) ──┘                             └──> TASK-RBT-005 (Wave 3)
```

## Key Risks

1. **python-library agent generalization** — Removing source-specific agents may leave the template thin. Consider creating 2-3 generic Python library agents.
2. **Confidence score** — After fixing python-library, the confidence score should be recalculated to reflect accurate metadata.
3. **init.py help text** — Currently stale (missing react-fastapi-monorepo, mcp-typescript, fastmcp-python). Consider a comprehensive update.

## Quick Start

```bash
# Wave 1 (parallel)
/task-work TASK-RBT-001
/task-work TASK-RBT-002

# Wave 2 (after Wave 1 complete)
/task-work TASK-RBT-003

# Wave 3 (after Wave 2 complete)
# TASK-RBT-004 and TASK-RBT-005 are direct tasks
```
