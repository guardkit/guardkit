---
id: TASK-VOPT-001
title: Context reduction - slim task-work protocol for local backends
status: completed
task_type: implementation
priority: high
tags: [vllm, performance, context-reduction, protocol]
complexity: 4
parent_review: TASK-REV-CB30
feature_id: FEAT-VOPT
wave: 1
implementation_mode: task-work
created: 2026-03-08T00:00:00Z
completed: 2026-03-08T00:00:00Z
test_results:
  status: passed
  coverage: null
  last_run: 2026-03-08T00:00:00Z
---

# Task: Context Reduction for Local Backends

## Problem

The task-work protocol injects ~19KB of system prompt per SDK invocation. For Qwen3 at ~20s/turn on GB10, prompt processing is a significant fraction of per-turn latency. Reducing context size could yield 1.1-1.3x per-turn improvement.

Additionally, Qwen3 may respond better to simpler, more direct instructions compared to the detailed protocol designed for Claude.

## Approach

Create a "slim" variant of the task-work inline protocol that is used when `timeout_multiplier > 1.0` (local backend detection). The slim protocol should:

1. Remove verbose explanations and examples (keep only directives)
2. Remove phase descriptions that Qwen3 doesn't follow anyway
3. Consolidate redundant instructions
4. Keep critical quality gates and acceptance criteria

**Target**: Reduce from ~19KB to ~10-12KB (40-50% reduction).

## Implementation

### File: `guardkit/orchestrator/agent_invoker.py`

Find the method that generates the inline task-work protocol (search for "Inline protocol" or the 19KB protocol string). Add a conditional path:

```python
if self.timeout_multiplier > 1.0:
    protocol = self._build_slim_protocol(task_context)
else:
    protocol = self._build_full_protocol(task_context)
```

### Slim Protocol Guidelines

- Keep: acceptance criteria, file paths, test commands, quality gates
- Remove: detailed phase explanations, examples of good/bad code, verbose formatting instructions
- Simplify: "Implement the task. Run tests. Commit." instead of multi-paragraph explanations
- Keep: TDD/BDD mode-specific instructions (but condensed)

## Acceptance Criteria

- [x] AC-001: Local backends use slim protocol (~4.4KB vs ~18.3KB — 75.8% reduction, exceeds target)
- [x] AC-002: Anthropic API backends continue using full protocol
- [x] AC-003: Protocol size logged at startup for both paths (variant=slim/full, multiplier=Xx)
- [x] AC-004: Existing tests pass (531 passed, 1 pre-existing unrelated failure)
- [x] AC-005: Slim protocol includes all acceptance criteria from task file (via requirements section)

## Risks

- Qwen3 may perform worse with less context (need Run 4 to validate)
- Slim protocol may miss critical instructions — verify against FBP task requirements

## References

- Review: `.claude/reviews/TASK-REV-CB30-vllm-viability-review-report.md` (Objective 2)
- Run 2 log: "Inline protocol size: 19196 bytes" (line 91)

## Completion Notes

### Changes Made

1. **New file**: `guardkit/orchestrator/prompts/autobuild_execution_protocol_slim.md` (3,822 bytes)
   - Condensed protocol keeping: quality gates, test commands, fix loop, player report schema, output markers
   - Removed: verbose SOLID/DRY/YAGNI descriptions, anti-stub examples, stack-specific patterns detail

2. **Modified**: `guardkit/orchestrator/agent_invoker.py`
   - `_build_autobuild_implementation_prompt()`: Routes to slim protocol when `self.timeout_multiplier > 1.0`
   - `_invoke_task_work_implement()`: Enhanced logging with protocol variant and multiplier

3. **Modified**: `tests/unit/test_autobuild_prompt_builders.py`
   - Added `TestSlimProtocolRouting` class with 9 tests

### Size Comparison

| Metric | Full | Slim | Reduction |
|--------|------|------|-----------|
| Protocol file | 18,014 bytes | 3,822 bytes | 78.8% |
| Total prompt | 18,695 bytes (18.3 KB) | 4,530 bytes (4.4 KB) | 75.8% |
