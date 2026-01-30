---
id: TASK-GV-A8F3
title: Analyze Graphiti async event loop issue causing search failures
status: review_complete
task_type: review
review_mode: architectural
review_depth: standard
created: 2026-01-29T12:00:00Z
updated: 2026-01-29T14:30:00Z
priority: high
tags: [graphiti, async, neo4j, debugging, architecture-review]
complexity: 6
decision_required: true
related_tasks:
  - TASK-GC-72AF
review_results:
  mode: architectural
  depth: standard
  score: 35
  findings_count: 3
  recommendations_count: 4
  decision: refactor
  report_path: .claude/reviews/TASK-GV-A8F3-review-report.md
  completed_at: 2026-01-29T14:30:00Z
---

# Task: Analyze Graphiti async event loop issue causing search failures

## Description

After migrating from `zepai/graphiti` Docker REST API to `graphiti-core` Python library (TASK-GC-72AF), the `guardkit graphiti verify` command reveals that all search queries fail with:

```
Task ... got Future <Future pending> attached to a different loop
```

While the infrastructure appears to work (Neo4j connection successful, indices created, OpenAI embeddings return 200 OK), all 5 verification queries return 0 results due to this async event loop mismatch.

## Problem Evidence

From `/docs/reviews/graphiti/graphiti_verify.md`:

| Component | Status |
|-----------|--------|
| Neo4j Connection | WORKING |
| Index Creation | WORKING (all indices exist) |
| OpenAI Embeddings | WORKING (HTTP 200 OK) |
| Search Queries | FAILING |
| Results Returned | 0 results for all 5 queries |

### Root Cause Hypothesis

The `guardkit graphiti verify` command uses `_run_async()` which creates a new event loop with `asyncio.run()`. However, the `graphiti-core` library internally maintains state tied to the event loop where it was initialized. When subsequent searches run, they're in a different event loop context.

## Review Objectives

1. **Root Cause Analysis**: Confirm or refute the event loop mismatch hypothesis
2. **Impact Assessment**: Determine if seeding also failed silently (same async issue)
3. **Solution Evaluation**: Evaluate potential fixes:
   - Single event loop pattern
   - Event loop reuse in `_run_async()`
   - Fresh client per operation
   - `asyncio.get_event_loop()` instead of `asyncio.run()`
4. **Recommendation**: Provide actionable fix recommendation with code approach

## Files to Review

- `guardkit/cli/graphiti.py` - CLI commands with `_run_async()` helper
- `guardkit/knowledge/graphiti_client.py` - Client wrapper
- `guardkit/knowledge/seeding.py` - Seeding logic (may have same issue)
- `docs/reviews/graphiti/graphiti_verify.md` - Full verify output

## Acceptance Criteria

- [ ] Root cause confirmed with evidence
- [ ] Impact on seeding operation documented
- [ ] At least 2 solution approaches evaluated with pros/cons
- [ ] Recommended fix approach selected with justification
- [ ] Implementation task created if fix is approved

## Review Mode

**Mode**: architectural
**Depth**: standard

## Context

This is a follow-up to TASK-GC-72AF (graphiti-core migration). The migration was completed and tests pass, but the async event loop issue was discovered during integration testing with `guardkit graphiti verify`.

## Implementation Notes

### Root Cause Analysis

**CONFIRMED**: The `_run_async()` helper in [graphiti.py:56-70](guardkit/cli/graphiti.py#L56-L70) creates a new event loop via `asyncio.run()` for each call. The `graphiti-core` library's Neo4j driver maintains internal state (Futures, connection pools) tied to the event loop where `Graphiti` was first initialized.

**Error Pattern**:
```
Task <Task pending> got Future <Future pending> attached to a different loop
```

**Sequence**:
1. `_run_async(client.initialize())` creates Loop A
2. `_run_async(client.search(...))` creates Loop B
3. Search fails because Neo4j driver Futures were created in Loop A

### Recommended Fix

**Option 1: Single Event Loop Pattern** (Score: 85/100)

Refactor CLI commands to use a single `asyncio.run()` with all operations in one async function:

```python
async def _cmd_verify(verbose: bool):
    client = GraphitiClient(config)
    try:
        await client.initialize()
        for query in queries:
            results = await client.search(query)
    finally:
        await client.close()

@graphiti.command()
def verify(verbose: bool):
    asyncio.run(_cmd_verify(verbose))
```

### Files Requiring Changes

- `guardkit/cli/graphiti.py` - Refactor all commands (seed, status, verify, seed-adrs)

### Full Report

See: [.claude/reviews/TASK-GV-A8F3-review-report.md](.claude/reviews/TASK-GV-A8F3-review-report.md)

## Decision Checkpoint

After review, choose:
- **[A]ccept** - Findings approved, document and close
- **[I]mplement** - Create implementation task to fix the issue
- **[R]evise** - Need deeper analysis
- **[C]ancel** - Issue not significant enough to fix
