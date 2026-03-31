---
id: TASK-CR-006-FIX
title: Wire seed_pattern_examples.py into CLI and verify retrieval fidelity
status: completed
completion_note: "Completed as investigation task. Wiring works correctly but revealed Graphiti code retrieval fidelity issue. Findings documented in docs/reviews/graphiti_enhancement/graphiti_code_retrieval_fidelity.md"
created: 2026-02-05T20:05:00+00:00
updated: 2026-02-05T20:50:00+00:00
priority: high
tags:
- context-optimization
- graphiti
- seeding
parent_review: TASK-REV-5F19
feature_id: FEAT-CR01
implementation_mode: direct
wave: 2
complexity: 2
task_type: feature
depends_on: []
---

# Task: Wire seed_pattern_examples.py into CLI and Verify Retrieval Fidelity

## Background

TASK-CR-006 created `guardkit/knowledge/seed_pattern_examples.py` with 17 pattern episodes (5 dataclass, 5 Pydantic, 7 orchestrator) but the module was never wired into the CLI. The pattern examples exist but were never actually seeded to Graphiti.

**Root Cause**: The AutoBuild Player created the module and Coach approved it, but neither verified that the seeding function was actually invoked or wired into `guardkit graphiti seed`.

## Description

Wire `seed_pattern_examples.py` into the Graphiti CLI seeding workflow and verify that pattern code examples can be retrieved with acceptable fidelity (>0.6 relevance).

## Acceptance Criteria

- [ ] Add `seed_pattern_examples_wrapper` to `seeding.py` categories list
- [ ] Add wrapper function in `seeding.py` that calls `seed_pattern_examples()`
- [ ] Export `seed_pattern_examples` from `guardkit/knowledge/__init__.py`
- [ ] Run `guardkit graphiti seed --force` successfully
- [ ] Verify retrieval with: `guardkit graphiti search "dataclass JSON serialization" --group patterns`
- [ ] Verify relevance score >0.6 for at least one pattern query
- [ ] Document any fidelity issues found

## Implementation Steps

### 1. Add wrapper to seeding.py

```python
# In seeding.py, add after seed_failed_approaches_wrapper:

async def seed_pattern_examples_wrapper(client) -> None:
    """Seed pattern code examples from TASK-CR-006.

    This wraps the seed_pattern_examples function to match the signature
    expected by the seed_all_system_context orchestrator.

    Args:
        client: GraphitiClient instance
    """
    if not client or not client.enabled:
        return

    from guardkit.knowledge.seed_pattern_examples import seed_pattern_examples
    await seed_pattern_examples(client)
```

### 2. Add to categories list in seed_all_system_context()

```python
categories = [
    # ... existing categories ...
    ("pattern_examples", "seed_pattern_examples_wrapper"),  # TASK-CR-006-FIX
]
```

### 3. Add export to __init__.py

```python
from guardkit.knowledge.seed_pattern_examples import seed_pattern_examples
```

### 4. Test seeding and retrieval

```bash
# Re-seed with new patterns
guardkit graphiti seed --force

# Verify retrieval
guardkit graphiti search "dataclass JSON serialization" --group patterns --limit 5
guardkit graphiti search "Pydantic field definitions" --group patterns --limit 5
guardkit graphiti search "pipeline step execution" --group patterns --limit 5
```

## Fidelity Acceptance Threshold

For TASK-CR-007 and TASK-CR-008 to proceed:
- At least 3 of 5 test queries must return >0.6 relevance
- Code formatting must be preserved (indentation, newlines)
- Pattern names must be recognizable in search results

If fidelity is poor (<0.6 for most queries), document findings and mark TASK-CR-007/CR-008 as CANCELLED with reason "Graphiti code retrieval fidelity insufficient".

## Related Tasks

- **Unblocks**: TASK-CR-007, TASK-CR-008
- **Supersedes**: TASK-CR-006 (which created the module but didn't wire it)
