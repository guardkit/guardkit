# Autobuild Review Summary: FEAT-9DDE

**Status:** FAILED  
**Generated:** 2026-06-13 10:36 UTC

## Metrics

| Metric | Value |
|--------|-------|
| Total tasks | 2 |
| Total turns | 3 |
| Avg turns/task | 3.00 |
| Waves executed | 1 |
| First-attempt pass rate | 0% |

## Per-Task Outcomes

| Task | Wave | Turns | Outcome | Decision | Notes |
|------|------|-------|---------|----------|-------|
| TASK-TSJ-001 | 1 | 3 | FAILED | unrecoverable_stall | context_pollution_stall_no_checkpoint | Unrecoverable stall detected after 3 turn(s). AutoBuild cannot make forward progress. |

## Quality Metrics

- Task success rate: 0%
- First-turn approvals: 0/1
- SDK ceiling hits: 0

## Turn Efficiency

| Metric | Value |
|--------|-------|
| Avg turns/task | 3.0 |
| Single-turn tasks | 0 |
| Multi-turn tasks | 1 |
| Avg SDK turns/invocation | 0.0 |

## Key Findings

- Tasks required multiple turns before failing: TASK-TSJ-001. Review coach feedback logs for recurring patterns.
