---
id: TASK-VER-004
title: Run Tier 2 Live Integration Tests for FEAT-0F4A
status: backlog
created: 2026-02-01T20:00:00Z
updated: 2026-02-01T20:00:00Z
priority: high
complexity: 4
implementation_mode: task-work
wave: 2
parallel_group: wave2
parent_review: TASK-REV-0F4A
feature_id: FEAT-VER-0F4A
tags: [verification, testing, live-tests, graphiti, neo4j]
estimated_minutes: 60
dependencies:
  - TASK-VER-001
  - TASK-VER-002
  - TASK-VER-003
---

# Task: Run Tier 2 Live Integration Tests for FEAT-0F4A

## Description

Execute Tier 2 live integration tests with actual Neo4j/Graphiti backend to validate real-world behavior, query performance, and data integrity.

## Prerequisites

- Neo4j running locally (bolt://localhost:7687)
- OpenAI API key configured for embeddings
- Tier 1 tests passing

## Acceptance Criteria

- [ ] All live integration tests pass
- [ ] Query latency < 2s (95th percentile)
- [ ] Seeding completes successfully
- [ ] Verify command returns valid results
- [ ] Search queries return relevant results

## Implementation Steps

1. Start Neo4j (if not running):
   ```bash
   docker-compose up -d neo4j
   # OR
   neo4j start
   ```

2. Navigate to worktree:
   ```bash
   cd .guardkit/worktrees/FEAT-0F4A
   ```

3. Clear and seed test data:
   ```bash
   guardkit graphiti clear --confirm --force 2>/dev/null || true
   guardkit graphiti seed --force
   ```

4. Run live integration tests:
   ```bash
   pytest tests/integration/graphiti/ -v -m "live" --durations=10
   ```

5. Verify query performance:
   ```bash
   guardkit graphiti verify
   ```

6. Check latency requirements:
   - Each query should complete < 2s
   - Total verify should complete < 30s

7. Document results with timing data

## Expected Results

Based on MVP verification:
- 5 live tests should pass (previously skipped)
- Verify command shows 5/5 passed
- Query latency ~100-500ms per query

## Verification Commands

```bash
# Start Neo4j
docker-compose up -d neo4j

# Seed and verify
cd .guardkit/worktrees/FEAT-0F4A
guardkit graphiti seed --force
guardkit graphiti verify

# Run live tests
pytest tests/integration/graphiti/ -v -m "live" --durations=10
```

## Performance Targets

| Operation | Target | Acceptable |
|-----------|--------|------------|
| Single query | < 500ms | < 1000ms |
| Verify (5 queries) | < 5s | < 10s |
| Context loading | < 2s | < 3s |
| Seeding | < 60s | < 120s |

## References

- Review Report: `.claude/reviews/TASK-REV-0F4A-review-report.md`
- MVP Verification: `docs/reviews/graphiti_enhancement/mvp_verification.md`
