---
id: TASK-daab
title: Selective rule loading for AutoBuild worktrees
status: completed
created: 2026-03-06T15:00:00Z
updated: 2026-03-06T16:15:00Z
completed: 2026-03-06T16:15:00Z
completed_location: tasks/completed/TASK-daab/
priority: high
task_type: implementation
complexity: 4
parent_review: TASK-REV-acbc
feature_id: FEAT-context-reduction
tags: [autobuild, performance, context-reduction, local-llm, rules]
wave: 1
implementation_mode: task-work
---

# Selective Rule Loading for AutoBuild Worktrees

## Problem

AutoBuild loads ALL `.claude/rules/` files (~63 KB, ~16K tokens) into every Player/Coach turn via the Claude Agent SDK's `setting_sources=["project"]`. On local LLMs (Qwen/DeepSeek 32B with 32K context), this leaves almost no room for task context and model reasoning.

Only ~17 KB of rules are actually needed for AutoBuild. The remaining ~46 KB includes patterns, guidance, and interactive-only rules irrelevant to autonomous code generation.

## Solution

After AutoBuild worktree creation, remove non-essential rules from the worktree's `.claude/rules/` directory so the SDK only loads what AutoBuild actually needs.

## Essential Rules (Keep — ~17 KB)

- `autobuild.md` (5.9 KB) — AutoBuild workflow guidance
- `anti-stub.md` (6.0 KB) — quality gate for stub detection
- `hash-based-ids.md` (1.4 KB) — task ID format
- `testing.md` (4.0 KB) — test execution guidance

## Non-Essential Rules (Remove from worktree — ~46 KB)

- `patterns/` directory (23.3 KB) — orchestrators.md, pydantic-models.md, dataclasses.md, template.md
- `guidance/` directory (4.3 KB) — agent-development.md
- `clarifying-questions.md` (4.1 KB) — interactive Q&A only
- `graphiti-knowledge.md` (4.4 KB) — handled by Python code, not needed in prompt
- `feature-build-invariants.md` (1.9 KB) — feature-build specific
- `python-library.md` (3.7 KB) — general Python guidance
- `task-workflow.md` (4.2 KB) — task file format reference

## Implementation

### Where to Add Filtering

In `AutoBuildOrchestrator._setup_phase()` (guardkit/orchestrator/autobuild.py, ~line 1083), after `self._worktree_manager.create()` returns, add a method to prune non-essential rules from the worktree.

### Approach

```python
AUTOBUILD_ESSENTIAL_RULES = {
    "autobuild.md",
    "anti-stub.md",
    "hash-based-ids.md",
    "testing.md",
}

def _prune_worktree_rules(self, worktree_path: Path) -> None:
    """Remove non-essential rules from AutoBuild worktree."""
    rules_dir = worktree_path / ".claude" / "rules"
    if not rules_dir.is_dir():
        return

    for item in rules_dir.iterdir():
        if item.is_dir():
            # Remove entire subdirectories (patterns/, guidance/)
            shutil.rmtree(item)
        elif item.name not in AUTOBUILD_ESSENTIAL_RULES:
            item.unlink()
```

### Files to Change

1. `guardkit/orchestrator/autobuild.py` — add `_prune_worktree_rules()` call after worktree creation

### Expected Impact

- Context per turn: ~116 KB → ~70 KB (40% reduction)
- Tokens freed: ~11.5K per turn
- For 32K context models: reasoning budget increases from ~3K to ~14.5K tokens

## Acceptance Criteria

- [x] AutoBuild worktrees contain only essential rules after creation
- [x] Non-essential rules (patterns/, guidance/, etc.) are removed from worktree
- [x] Interactive sessions (non-worktree) are unaffected — full rules remain
- [x] Essential rules list is configurable (constant, easy to modify)
- [x] Existing tests pass
- [x] New test verifying rule pruning works correctly

## Notes

- Git worktrees share the `.git` directory but have independent working trees, so removing files from the worktree does NOT affect the main branch
- The CLAUDE.md files should NOT be pruned (they contain essential project context)
- If feature-build mode is detected, `feature-build-invariants.md` should be kept
