---
id: TASK-BRF-003
title: Raise Default Architectural Review Threshold
status: backlog
task_type: implementation
created: 2026-01-24T16:30:00Z
updated: 2026-01-24T16:30:00Z
priority: medium
tags: [autobuild, quality-gates, block-research, configuration]
complexity: 2
parent_review: TASK-REV-BLOC
feature_id: FEAT-BRF
wave: 2
implementation_mode: direct
conductor_workspace: block-research-fidelity-wave2-1
dependencies: [TASK-BRF-001, TASK-BRF-002]
---

# Task: Raise Default Architectural Review Threshold

## Description

Increase the default architectural review threshold from 60 to 75 to better align with Block research quality requirements for effective adversarial cooperation.

**Problem**: Current threshold of 60 is lenient and may allow lower-quality code through the quality gates. Block research emphasizes high-quality standards for adversarial cooperation effectiveness.

**Solution**: Raise the default to 75 while keeping it configurable for backward compatibility.

## Acceptance Criteria

- [ ] AC-001: Change default `code_review.score` threshold from 60 to 75
- [ ] AC-002: Add `--arch-threshold` CLI flag to allow override (range: 50-100)
- [ ] AC-003: Update documentation to reflect new default
- [ ] AC-004: Add migration note in CHANGELOG for users who depend on 60 threshold
- [ ] AC-005: Update Coach agent to reference the configurable threshold

## Technical Approach

### Files to Modify

1. **`guardkit/orchestrator/quality_gates/coach_validator.py`**
```python
# Change from:
ARCH_REVIEW_THRESHOLD = 60

# To:
ARCH_REVIEW_THRESHOLD = 75
```

2. **`guardkit/cli/autobuild.py`**
```python
@click.option(
    "--arch-threshold",
    type=click.IntRange(50, 100),
    default=75,
    help="Minimum architectural review score (default: 75)",
)
```

3. **`.claude/agents/autobuild-coach.md`**
```markdown
# Update line referencing the threshold
- `code_review.score >= 60`
+ `code_review.score >= 75` (or value from --arch-threshold)
```

4. **`docs/guides/autobuild-workflow.md`**
- Document the new default and how to override

## Related Files

- `guardkit/orchestrator/quality_gates/coach_validator.py`
- `guardkit/cli/autobuild.py`
- `.claude/agents/autobuild-coach.md`
- `docs/guides/autobuild-workflow.md`

## Notes

Simple configuration change. Block research suggests higher quality bars improve adversarial cooperation outcomes.
