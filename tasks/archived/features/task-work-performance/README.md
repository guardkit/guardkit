# Feature: task-work Performance Optimization

## Overview

Implementation tasks from TASK-REV-FB15 root cause analysis. These optimizations target the primary bottleneck: Phase 2 excessive documentation generation.

## Problem Statement

Full `/task-work` workflow takes 65+ minutes for simple tasks (complexity 3/10) while `--micro` mode completes in 3-5 minutes. Root cause analysis identified:

1. **Phase 2 generates 117KB of documentation** for a complexity-3 task (89% of time)
2. **No early-exit for simple tasks** - complexity 3 still runs full workflow
3. **Design Patterns MCP returns irrelevant results** for Python tasks

## Subtasks

| Task ID | Title | Mode | Wave | Est. Time |
|---------|-------|------|------|-----------|
| TASK-TWP-a1b2 | Enforce documentation level constraints | task-work | 1 | 2-4 hours |
| TASK-TWP-c3d4 | Lower micro-mode threshold to complexity ≤3 | task-work | 1 | 1-2 hours |
| TASK-TWP-e5f6 | Skip MCP for tasks with known patterns | direct | 2 | 1 hour |

## Expected Impact

After implementing all three tasks:

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Simple task (complexity ≤3) duration | 65+ min | 3-5 min | **95% faster** |
| Phase 2 token consumption | 66k tokens | 10-15k tokens | **80% reduction** |
| MCP irrelevant results | Frequent | Rare | Cleaner execution |

## Dependencies

- None (all tasks modify existing code)

## Related Tasks

- **TASK-REV-FB14**: Prior performance analysis
- **TASK-REV-FB15**: Root cause analysis (source of these tasks)
- **TASK-REV-FB16**: Optimization strategy evaluation

## Success Criteria

- [ ] Simple tasks (complexity ≤3) complete in <10 minutes
- [ ] Documentation level constraints enforced (max 2 files for minimal/standard)
- [ ] Design patterns MCP skipped for simple tasks and known patterns
