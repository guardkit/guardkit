# vLLM Run 6 Fixes (FEAT-81DD)

Fixes identified from TASK-REV-35DC analysis of vLLM AutoBuild Run 6.

**Status**: 0/4 tasks complete

## Summary

Run 6 succeeded (7/7, 285m) but exposed structural issues: budget starvation from wave co-location, SDK turn inflation from slim protocol, and incorrect previous review data. These tasks fix the root causes and prevent recurrence.

## Tasks

| Wave | Task | Status | Priority | Effort | Mode |
|------|------|--------|----------|--------|------|
| 1 | [TASK-VR6-3B1F](TASK-VR6-3B1F-wave-separation-feat1637.md) | backlog | high | 15min | direct |
| 1 | [TASK-VR6-DAF4](TASK-VR6-DAF4-feature-plan-wave-isolation.md) | backlog | high | 2-3h | task-work |
| 1 | [TASK-VR6-5497](TASK-VR6-5497-correct-rev-5e1f-report.md) | backlog | low | 15min | direct |
| 2 | [TASK-VR6-65A0](TASK-VR6-65A0-slim-protocol-investigation.md) | backlog | medium | 1-2h | direct (review) |

## Source

- **Review**: [TASK-REV-35DC](.claude/reviews/TASK-REV-35DC-review-report.md)
- **Compatibility**: Verified against commit `821dfda5` (no conflicts)
