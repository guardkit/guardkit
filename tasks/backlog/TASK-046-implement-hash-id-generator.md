---
id: TASK-046
title: Implement core hash-based ID generator
status: backlog
created: 2025-01-08T00:00:00Z
updated: 2025-01-08T00:00:00Z
priority: high
tags: [infrastructure, hash-ids, core]
complexity: 5
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Implement core hash-based ID generator

## Description

Implement the core hash-based task ID generator that eliminates duplicate IDs through cryptographic hashing. This is the foundation for solving the duplicate task ID issue (TASK-003 appears twice in codebase).

The generator will create collision-free IDs using SHA-256 hashing with progressive length scaling based on task count.

## Acceptance Criteria

- [ ] Generator produces 4-character hex IDs for projects with <500 tasks
- [ ] Generator scales to 5-character hex IDs for 500-1,500 tasks
- [ ] Generator scales to 6-character hex IDs for 1,500+ tasks
- [ ] Hash is generated from timestamp + random bytes (SHA-256)
- [ ] Collision detection verifies uniqueness before returning ID
- [ ] Support for optional prefix parameter (e.g., "E01", "DOC", "FIX")
- [ ] Format: `TASK-{hash}` or `TASK-{prefix}-{hash}`
- [ ] Zero collisions in 10,000 generated IDs test
- [ ] Performance: Generate 1,000 IDs in <1 second

## Test Requirements

- [ ] Unit tests for hash generation logic
- [ ] Unit tests for progressive length scaling (4→5→6 chars)
- [ ] Unit tests for prefix support
- [ ] Collision testing (generate 10,000 IDs, verify all unique)
- [ ] Performance testing (1,000 IDs in <1 second)
- [ ] Edge case testing (None prefix, empty string prefix)
- [ ] Test coverage ≥90%

## Implementation Notes

### File Location
Create new file: `installer/global/lib/id_generator.py`

### Key Functions
```python
def generate_task_id(prefix: Optional[str] = None, existing_ids: Set[str] = None) -> str:
    """Generate collision-free hash-based task ID."""

def count_existing_tasks() -> int:
    """Count tasks across all directories for scaling logic."""

def task_exists(task_hash: str, prefix: Optional[str]) -> bool:
    """Check if task ID already exists."""
```

### Algorithm
1. Determine hash length based on task count (4, 5, or 6 chars)
2. Generate seed from `datetime.now(datetime.UTC) + secrets.token_hex(8)`
3. Create SHA-256 hash of seed
4. Extract first N characters of hex digest
5. Check collision against existing IDs
6. If collision (rare), regenerate
7. Return formatted ID: `TASK-{prefix}-{hash}` or `TASK-{hash}`

### References
- POC implementation: `docs/research/task-id-poc.py`
- Full analysis: `docs/research/task-id-strategy-analysis.md`
- Decision guide: `docs/research/task-id-decision-guide.md`

## Dependencies

None (pure Python with stdlib only)

## Related Tasks

- TASK-047: ID validation and duplicate detection
- TASK-048: Update /task-create to use hash generator
- TASK-049: External ID mapper for PM tools

## Test Execution Log

[Automatically populated by /task-work]
