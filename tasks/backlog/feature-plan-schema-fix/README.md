# Feature: Fix /feature-plan Schema Mismatch

## Problem

The `/feature-build` CLI command fails because `/feature-plan` generates YAML in a format that `FeatureLoader` doesn't understand. This causes:

1. `KeyError: 'file_path'` - Task entries missing required field
2. "Tasks not in orchestration" - Wrong parallel groups format
3. "invalid reference: main" - Fresh repos not handled

## Solution

Update `/feature-plan` to generate the correct schema format that `FeatureLoader` expects, rather than modifying the loader.

## Tasks

| ID | Title | Complexity | Wave | Mode |
|----|-------|------------|------|------|
| TASK-FP-001 | Update feature-plan.md schema documentation | 4 | 1 | task-work |
| TASK-FP-002 | Update generate-feature-yaml script output | 5 | 1 | task-work |
| TASK-FP-003 | Add repository state check to worktree manager | 3 | 2 | task-work |
| TASK-FP-004 | Improve FeatureLoader error messages | 2 | 2 | direct |
| TASK-FP-005 | Add unit tests for schema parsing edge cases | 4 | 3 | task-work |

## Execution Strategy

```
Wave 1: TASK-FP-001, TASK-FP-002 (parallel)
Wave 2: TASK-FP-003, TASK-FP-004 (parallel)
Wave 3: TASK-FP-005 (sequential, after waves 1-2)
```

**Total Estimated Duration**: 5-7 hours

## Quick Start

```bash
# Start Wave 1 (parallel)
/task-work TASK-FP-001
/task-work TASK-FP-002

# After Wave 1 completes, start Wave 2
/task-work TASK-FP-003
/task-work TASK-FP-004

# After Wave 2 completes, run tests
/task-work TASK-FP-005
```

## Success Criteria

- [ ] `/feature-plan` generates FeatureLoader-compatible YAML
- [ ] `/feature-build` runs without schema errors
- [ ] Fresh repositories get helpful error messages
- [ ] Unit test coverage ≥80% for feature_loader.py

## Related

- **Review Task**: TASK-REV-66B4
- **Review Report**: [.claude/reviews/TASK-REV-66B4-review-report.md](../../.claude/reviews/TASK-REV-66B4-review-report.md)
- **Error Log**: [docs/reviews/feature-build/feature-build-output.md](../../../docs/reviews/feature-build/feature-build-output.md)
