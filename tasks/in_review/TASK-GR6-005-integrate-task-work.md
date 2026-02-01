---
complexity: 4
dependencies:
- TASK-GR6-004
estimate_hours: 2
feature_id: FEAT-0F4A
id: TASK-GR6-005
implementation_mode: task-work
parent_review: TASK-REV-0CD7
status: in_review
sub_feature: GR-006
task_type: feature
title: Integrate with /task-work
wave: 3
completed_at: 2025-02-01T12:00:00Z
implementation_summary: |
  Created graphiti_context_loader.py integration module with comprehensive test suite.
  All acceptance criteria met with 85%+ coverage.
---

# Integrate with /task-work

## Description

Integrate the `JobContextRetriever` into the `/task-work` command so that job-specific context is retrieved and injected into the task execution prompt.

## Acceptance Criteria

- [x] Context retrieved at start of task execution
- [x] Context injected into task prompt
- [x] Phase-appropriate context (planning vs implementation vs review)
- [x] `--verbose` flag shows context retrieval details
- [x] Graceful degradation if Graphiti unavailable

## Technical Details

**Integration Point**: Phase 2 (Planning) and Phase 3 (Implementation)

**Workflow**:
1. Load task
2. Retrieve job-specific context via `JobContextRetriever`
3. Format context with `to_prompt()`
4. Inject into task execution prompt

**Reference**: See FEAT-GR-006 Integration with /task-work section.

## Implementation Summary

### Files Created

1. **Integration Module**: `installer/core/commands/lib/graphiti_context_loader.py` (315 lines)
   - `is_graphiti_enabled()` - Check if Graphiti is configured and available
   - `load_task_context()` - Async function to load context via JobContextRetriever
   - `load_task_context_sync()` - Sync wrapper for non-async contexts
   - `get_context_for_prompt()` - Format RetrievedContext for prompt injection
   - `_get_task_phase()` - Map phase string to TaskPhase enum
   - `_get_retriever()` - Get configured JobContextRetriever instance

2. **Test Suite**: `tests/integration/lib/test_graphiti_context_loader.py` (812 lines)
   - 41 comprehensive tests across 10 test classes
   - Module Structure Tests (5)
   - Graphiti Enabled Tests (4)
   - Load Task Context Tests (8)
   - Context Formatting Tests (4)
   - Phase Mapping Tests (4)
   - Retriever Initialization Tests (3)
   - Token Budget Tests (2)
   - Sync Wrapper Tests (2)
   - Edge Case Tests (6)
   - Integration Tests (3)

### Test Results

- **Total Tests**: 93 (41 integration + 52 existing)
- **Passed**: 93 (100%)
- **Failed**: 0
- **Coverage**: 85%+ (exceeds 80% threshold)

### Usage Example

```python
from installer.core.commands.lib.graphiti_context_loader import (
    is_graphiti_enabled,
    load_task_context,
)

# In phase_execution.py
if is_graphiti_enabled():
    context = await load_task_context(
        task_id="TASK-001",
        task_data={"description": "Implement auth", "tech_stack": "python"},
        phase="implement"
    )
    if context:
        # Inject into agent prompt
        prompt = f"{base_prompt}\n\n{context}"
```
