---
id: TASK-FIX-GCI1
title: Wire Graphiti context into standard /task-work
status: completed
task_type: implementation
created: 2026-02-08T23:00:00Z
updated: 2026-02-09T00:00:00Z
completed: 2026-02-09T00:00:00Z
completed_location: tasks/completed/TASK-FIX-GCI1/
priority: high
parent_review: TASK-REV-C7EB
tags: [graphiti, task-work, context-retrieval, FEAT-GR-006]
complexity: 5
wave: 1
dependencies: []
---

# Wire Graphiti Context into Standard /task-work

## Description

The FEAT-GR-006 job-specific context retrieval infrastructure was designed for standard `/task-work` execution, not just AutoBuild. A bridge module (`installer/core/commands/lib/graphiti_context_loader.py`) already exists with `load_task_context()` and `load_task_context_sync()` APIs, but it is **imported nowhere** in the codebase. The `DynamicBudgetCalculator` has a "standard" allocation strategy (6 categories: feature_context, similar_outcomes, relevant_patterns, architecture_context, warnings, domain_knowledge) that is **never invoked**.

This task wires the existing infrastructure into the `/task-work` command so that during implementation planning (Phase 2), the knowledge graph is queried to provide:
- How the task fits into the system (related features, architecture context)
- What similar tasks looked like (outcomes, patterns that worked/failed)
- What to avoid (failed approaches, warnings)
- Domain knowledge (relevant concepts and constraints)

## Reference Architecture

The AutoBuild integration pattern (already working) shows how this should work:

```
AutoBuild: CLI → AutoBuildOrchestrator → AutoBuildContextLoader → JobContextRetriever → Graphiti
Task-work: CLI → phase_execution → GraphitiContextLoader → JobContextRetriever → Graphiti
                                    ^^^^^^^^^^^^^^^^^^^^^^
                                    EXISTS BUT NOT WIRED
```

## Existing Infrastructure (no changes needed)

- `installer/core/commands/lib/graphiti_context_loader.py` - Bridge module with `load_task_context()`, `load_task_context_sync()`, `get_context_for_prompt()`, `is_graphiti_enabled()`
- `guardkit/knowledge/job_context_retriever.py` - Core retrieval engine with caching, early termination
- `guardkit/knowledge/budget_calculator.py` - Dynamic budget with "standard" allocation
- `guardkit/knowledge/task_analyzer.py` - Task classification

## Changes Required

### 1. Wire GraphitiContextLoader into task-work Phase 1/2

In the task-work execution flow, import and call `load_task_context()` during Phase 1 (Load Task Context) or Phase 2 (Implementation Planning):

```python
from installer.core.commands.lib.graphiti_context_loader import (
    is_graphiti_enabled,
    load_task_context_sync,
    get_context_for_prompt,
)

# During Phase 1 or 2:
if is_graphiti_enabled():
    context = load_task_context_sync(
        task_id=task_id,
        task_data={
            "description": description,
            "tech_stack": tech_stack,
            "complexity": complexity,
            "feature_id": feature_id,
        },
        phase="plan"  # or "implement" depending on phase
    )
    if context:
        prompt = f"{base_prompt}\n\n{context}"
```

### 2. Add context display in task-work output

Show context retrieval status to the user:
```
[Graphiti] Context loaded: 4 categories, 2800/4000 tokens
```
Or:
```
[Graphiti] Context: unavailable (continuing without)
```

### 3. Update task-work.md spec

Add Graphiti context loading to Phase 1-2 documentation in `installer/core/commands/task-work.md`.

## Acceptance Criteria

- [ ] `GraphitiContextLoader.load_task_context()` is called during task-work Phase 1 or 2
- [ ] Context is injected into the implementation planning prompt
- [ ] Graceful degradation: task-work works identically when Graphiti is unavailable
- [ ] Context retrieval status is displayed to the user
- [ ] "Standard" allocation strategy in `DynamicBudgetCalculator` is exercised
- [ ] Tests verify context loading with mock Graphiti client
- [ ] Tests verify graceful degradation when Graphiti is None/disabled
- [ ] task-work.md spec updated to document context loading

## CRITICAL: No Stubs Policy

**All code written for this task MUST be fully functional.** No placeholder methods, no empty return values, no TODO comments deferring implementation. Every function must do what its docstring says.

## Graphiti API Reference

### How search() works (the read path this task uses)

The `GraphitiContextLoader` calls `JobContextRetriever.retrieve()` which calls `GraphitiClient.search()`:

```python
# GraphitiClient.search() signature:
async def search(
    self,
    query: str,
    group_ids: Optional[List[str]] = None,
    num_results: int = 10,
    scope: Optional[str] = None
) -> List[Dict[str, Any]]
# Returns: [{"uuid": "...", "fact": "...", "name": "...", "score": 0.85}, ...]
# Returns: [] on error (graceful degradation)
```

### How the retrieval pipeline works

```python
# 1. TaskAnalyzer classifies the task
characteristics = await analyzer.analyze(task_dict, TaskPhase.PLAN)
# Returns: TaskCharacteristics(task_type=IMPLEMENTATION, complexity=6, ...)

# 2. BudgetCalculator allocates tokens
budget = calculator.calculate(characteristics)
# Returns: ContextBudget(total_tokens=4000, feature_context=0.15, ...)
# Standard allocation: feature_context(15%), similar_outcomes(25%),
#   relevant_patterns(20%), architecture_context(20%), warnings(15%), domain_knowledge(5%)

# 3. JobContextRetriever queries Graphiti
context = await retriever.retrieve(task_dict, TaskPhase.PLAN)
# Returns: RetrievedContext with populated lists

# 4. Format as markdown for prompt injection
prompt_text = context.to_prompt()
# Returns: "## Feature Context\n- ...\n## Similar Outcomes\n- ..."
```

### How GraphitiContextLoader bridges this (already exists)

```python
# installer/core/commands/lib/graphiti_context_loader.py
async def load_task_context(
    task_id: str,
    task_data: Dict[str, Any],   # Must include: description, tech_stack, complexity, feature_id
    phase: str                    # "load" | "plan" | "implement" | "test" | "review"
) -> Optional[str]               # Returns formatted markdown or None

def load_task_context_sync(      # Sync wrapper using ThreadPoolExecutor
    task_id: str,
    task_data: Dict[str, Any],
    phase: str
) -> Optional[str]

def is_graphiti_enabled() -> bool  # Checks GRAPHITI_AVAILABLE + config
```

### Graceful degradation pattern (mandatory)

```python
# All Graphiti operations MUST follow this 3-layer pattern:
if client is None:                    # Layer 1: Null check
    return default_value
if not client.enabled:                # Layer 2: Enabled check
    return default_value
try:                                  # Layer 3: Try/except
    result = await client.search(...)
except Exception as e:
    logger.warning(f"Graphiti operation failed: {e}")
    return default_value              # NEVER raise from Graphiti operations
```

## Investigation Notes

The key question to resolve during implementation is: **where exactly in the task-work execution flow should context be loaded?** The task-work command is spec-driven (the spec IS the prompt), so the integration point is likely where the spec gets assembled into a prompt before agent invocation. Look at how the task-work skill loads and assembles the prompt.

## Files to Modify

- Task-work execution/orchestration code (identify exact location during implementation)
- `installer/core/commands/task-work.md` (spec update)
- New test file for task-work context integration

## Files for Reference (do not modify)

- `installer/core/commands/lib/graphiti_context_loader.py` - The bridge (should work as-is)
- `guardkit/knowledge/autobuild_context_loader.py` - Reference for how AutoBuild does it
- `guardkit/knowledge/job_context_retriever.py` - Core engine
- `guardkit/knowledge/budget_calculator.py` - Budget allocation

## Graphiti Documentation Reference

- `docs/reviews/graphiti_baseline/graphiti-technical-reference.md` - Client API reference
- `docs/guides/graphiti-integration-guide.md` - 18 knowledge categories, group IDs
- `docs/architecture/graphiti-architecture.md` - Architecture patterns

## Clarification Note (added by TASK-FIX-GG02)

**This task is correctly completed.** TASK-REV-DE4F flagged that `graphiti_context_loader.py` has zero production Python imports as a potential gap. This is expected because `/task-work` is a Claude Code skill (LLM prompt), not a Python module:

- **AutoBuild path**: Real Python imports (`autobuild.py` → `AutoBuildContextLoader`) — different execution model
- **task-work path**: Spec-driven prompt (`task-work.md` lines 1650-1739 document Phase 1.7) — LLM follows instructions

The spec correctly documents Graphiti context loading (Phase 1.7), context injection into Phase 2 prompts (lines 2214-2221), and graceful degradation. The `graphiti_context_loader.py` bridge module provides the API contract and is fully tested (57 tests).
