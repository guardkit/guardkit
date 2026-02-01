---
id: TASK-VER-002
title: Run Tier 1 Integration Tests (Mock) for FEAT-0F4A
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
tags: [verification, testing, integration-tests, graphiti]
estimated_minutes: 30
---

# Task: Run Tier 1 Integration Tests (Mock) for FEAT-0F4A

## Description

Execute the Tier 1 integration tests with mocked Graphiti backend to verify component integration without requiring live Neo4j.

## Acceptance Criteria

- [ ] All integration tests in `tests/integration/graphiti/` pass (excluding live markers)
- [ ] Workflow integration tests pass
- [ ] Graceful degradation tests pass
- [ ] Test execution time < 2 minutes

## Implementation Steps

1. Navigate to worktree:
   ```bash
   cd .guardkit/worktrees/FEAT-0F4A
   ```

2. Run integration tests with mock backend:
   ```bash
   pytest tests/integration/graphiti/ \
     -v -m "integration and not live" \
     --tb=short
   ```

3. Verify all test categories pass:
   - `TestSeedingWorkflow`
   - `TestContextLoadingWorkflow`
   - `TestCLICommandIntegration`
   - `TestGracefulDegradation`
   - `TestWorkflowSequence`
   - `TestClearAndReseed`

4. Document results in verification report

## Expected Results

Based on MVP verification reference:
- 13 tests should pass
- 5 live tests should be skipped
- Execution time ~0.2 seconds

## Verification Command

```bash
cd .guardkit/worktrees/FEAT-0F4A && \
pytest tests/integration/graphiti/test_workflow_integration.py \
  -v -m "integration and not live" --no-cov
```

## Test Categories

| Category | Expected | Description |
|----------|----------|-------------|
| SeedingWorkflow | 2 pass | Metadata episodes, marker creation |
| ContextLoadingWorkflow | 4 pass | Structure, degradation, disabled, feature-build |
| CLICommandIntegration | 2 pass | Status, verify commands |
| GracefulDegradation | 3 pass | No graphiti, errors, disabled |
| WorkflowSequence | 1 pass | Task-work context injection |
| ClearAndReseed | 1 pass | Clear marker allows reseed |

## References

- Review Report: `.claude/reviews/TASK-REV-0F4A-review-report.md`
- MVP Verification: `docs/reviews/graphiti_enhancement/mvp_verification.md`
