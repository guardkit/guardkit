---
id: TASK-VR6-MP01
title: Create medium execution protocol variant (~10KB)
status: completed
task_type: feature
created: 2026-03-09T00:00:00Z
updated: 2026-03-09T21:35:00Z
completed: 2026-03-09T21:35:00Z
priority: high
complexity: 4
wave: 3
implementation_mode: task-work
parent_review: TASK-VR6-65A0
feature_id: FEAT-81DD
tags: [autobuild, protocol, vllm, performance]
dependencies: []
---

# Task: Create medium execution protocol variant (~10KB)

## Description

Create a medium-sized execution protocol (`autobuild_execution_protocol_medium.md`) that restores the most impactful sections from the full protocol while keeping the slim structure. This addresses the 24-174% SDK turn inflation observed on the vLLM backend (Runs 5-6) without reverting to the full 19KB protocol.

## Context

Review TASK-VR6-65A0 found that the slim protocol (5.5KB) causes significant turn inflation on complex tasks because it removes anti-stub examples, stack patterns, and error handling guidance that the model needs to produce quality code on the first attempt.

## Implementation Plan

### 1. Create `guardkit/orchestrator/prompts/autobuild_execution_protocol_medium.md`

Start from slim protocol and restore:

**Restore in full** (highest impact):
- Anti-stub rules with REJECTED/ACCEPTED examples (~88 lines from full `## Anti-Stub Rules` section)
- Stack-specific implementation patterns (~47 lines from full `### Stack-Specific Implementation Patterns` section)

**Restore abbreviated** (medium impact):
- Error handling requirements (~20 lines, condensed from full `### Error Handling Requirements`)
- SOLID/DRY/YAGNI with brief explanations (~25 lines, condensed from full `### SOLID Principles Check`, `### DRY Check`, `### YAGNI Check`)

**Keep removed** (low impact):
- Docker setup verbosity (slim version sufficient)
- Report schema lengthy documentation (slim version sufficient)
- Fix loop pseudocode (slim summary sufficient)

Target size: ~10-11KB

### 2. Update protocol selection logic in `agent_invoker.py`

Update the selection logic at line ~4094-4101 to use `autobuild_execution_protocol_medium` for local backends instead of `autobuild_execution_protocol_slim`:

```python
# Current:
if self.timeout_multiplier > 1.0:
    protocol_name = "autobuild_execution_protocol_slim"
# New:
if self.timeout_multiplier > 1.0:
    protocol_name = "autobuild_execution_protocol_medium"
```

Also update the logging at line ~4400:
```python
protocol_variant = "medium" if self.timeout_multiplier > 1.0 else "full"
```

### 3. Keep slim protocol as fallback

Do NOT delete `autobuild_execution_protocol_slim.md` — it may be useful for future experiments or very constrained contexts.

## Acceptance Criteria

- [x] `autobuild_execution_protocol_medium.md` exists and is ~10-11KB (10,210 bytes)
- [x] Medium protocol contains anti-stub rules with REJECTED/ACCEPTED examples
- [x] Medium protocol contains stack-specific implementation patterns (Python, TypeScript, .NET)
- [x] Medium protocol contains abbreviated error handling requirements
- [x] Medium protocol contains SOLID/DRY/YAGNI brief explanations
- [x] `agent_invoker.py` uses medium protocol for local backends (timeout_multiplier > 1.0)
- [x] Slim protocol file preserved (not deleted)
- [x] All existing tests pass (92/92, 1 pre-existing unrelated failure)

## Files to Modify

- `guardkit/orchestrator/prompts/autobuild_execution_protocol_medium.md` (NEW)
- `guardkit/orchestrator/agent_invoker.py` (lines ~4094-4101, ~4400)

## Risk Assessment

- Low risk: additive change (new file + 2-line selection logic change)
- Slim protocol preserved as fallback
- Validated by Run 7 profiling
