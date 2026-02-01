---
id: TASK-VER-001
title: Run Tier 1 Unit Tests for FEAT-0F4A
status: backlog
created: 2026-02-01T20:00:00Z
updated: 2026-02-01T20:00:00Z
priority: high
complexity: 2
implementation_mode: direct
wave: 1
parallel_group: wave1
parent_review: TASK-REV-0F4A
feature_id: FEAT-VER-0F4A
tags: [verification, testing, unit-tests, graphiti]
estimated_minutes: 30
---

# Task: Run Tier 1 Unit Tests for FEAT-0F4A

## Description

Execute the Tier 1 unit tests in the FEAT-0F4A worktree to verify all knowledge module implementations work correctly with mocked dependencies.

## Acceptance Criteria

- [ ] All unit tests in `tests/unit/knowledge/` pass
- [ ] All unit tests in `tests/cli/test_graphiti*.py` pass (excluding live markers)
- [ ] Coverage for `guardkit/knowledge/` is ≥ 70%
- [ ] No new lint warnings introduced
- [ ] Test execution time < 3 minutes

## Implementation Steps

1. Navigate to worktree:
   ```bash
   cd .guardkit/worktrees/FEAT-0F4A
   ```

2. Run unit tests with coverage:
   ```bash
   pytest tests/unit/knowledge/ tests/cli/test_graphiti*.py \
     -v -m "not live" \
     --cov=guardkit/knowledge \
     --cov-report=term \
     --cov-report=json \
     --tb=short
   ```

3. Verify coverage threshold:
   ```bash
   # Check coverage.json for >= 70% on knowledge modules
   ```

4. Fix any failing tests (if needed)

5. Document results in verification report

## Expected Results

Based on the review analysis:
- ~255 tests should pass
- 1 known mock issue in `test_status_shows_seeding_state`
- Coverage should be ~65-70%

## Verification Command

```bash
cd .guardkit/worktrees/FEAT-0F4A && \
pytest tests/unit/knowledge/ tests/cli/test_graphiti*.py \
  -v -m "not live" \
  --cov=guardkit/knowledge \
  --tb=short 2>&1 | tail -30
```

## References

- Review Report: `.claude/reviews/TASK-REV-0F4A-review-report.md`
- MVP Verification: `docs/reviews/graphiti_enhancement/mvp_verification.md`
