# FEAT-GCF: Graphiti Context Fixes

## Summary

Fix 5 independent root causes preventing Graphiti knowledge graph from providing context to AutoBuild tasks on vLLM/Qwen3 runs.

## Root Causes

| # | Root Cause | Fix |
|---|-----------|-----|
| RC1 | `seed-system` never run | Run `guardkit graphiti seed-system --force` |
| RC2 | `patterns` vs `patterns_python` group ID mismatch | Code fix in `job_context_retriever.py` |
| RC3 | Dynamic groups empty on fresh runs | By design — accumulates over time |
| RC4 | Project knowledge not seeded | Run `guardkit graphiti seed-project` |
| RC5 | Silent exception swallowing in queries | Add `logger.warning()` |

## Subtasks

| Task | Title | Wave | Mode | Priority |
|------|-------|------|------|----------|
| TASK-GCF-001 | Fix patterns group ID mismatch | 1 | task-work | High |
| TASK-GCF-002 | Add query category logging | 1 | direct | High |
| TASK-GCF-003 | Add missing groups to _group_defs.py | 1 | direct | Medium |
| TASK-GCF-004 | Run seed-system and seed-project | 2 | manual | High |
| TASK-GCF-005 | Validate context in Run 5 | 3 | manual | Medium |

## Parent Review

[TASK-REV-982B Review Report](../../../.claude/reviews/TASK-REV-982B-review-report.md)
