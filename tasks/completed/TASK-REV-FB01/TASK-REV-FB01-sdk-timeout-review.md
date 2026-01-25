---
id: TASK-REV-FB01
title: Review SDK timeout configuration for feature-build
status: completed
task_type: review
created: 2025-01-24T10:00:00Z
updated: 2026-01-24T11:05:00Z
completed: 2026-01-24T11:05:00Z
priority: medium
tags: [feature-build, autobuild, sdk-timeout, performance, configuration]
complexity: 4
decision_required: true
review_results:
  mode: decision
  depth: standard
  recommendation: harmonize_defaults
  decision: implement
  implementation_task: TASK-FIX-SDKT
  report_path: .claude/reviews/TASK-REV-FB01-sdk-timeout-review-report.md
  completed_at: 2026-01-24T11:00:00Z
completed_location: tasks/completed/TASK-REV-FB01/
organized_files:
  - TASK-REV-FB01-sdk-timeout-review.md
  - TASK-REV-FB01-sdk-timeout-review-report.md
---

# Task: Review SDK timeout configuration for feature-build

## Description

Investigate whether the default SDK timeout for `/feature-build` should be increased from 900s (15 minutes) to a higher value. During testing of FEAT-A96D, TASK-FHA-003 timed out at 900s while actively progressing (103 tests passing, 92% coverage, in Phase 5: Code Review). The retry mechanism worked, but the retry overhead is significant.

## Background Evidence

### Observed Timeout Incident
- **Feature**: FEAT-A96D (FastAPI App with Health Endpoint)
- **Task**: TASK-FHA-003 (Create FastAPI app entry point)
- **Timeout**: 900s (15 minutes)
- **State at timeout**: Phase 5 Code Review, 103 tests passing, 92% coverage
- **Resolution**: Automatic retry on turn 2 succeeded
- **Total feature duration**: 37m 55s (with timeout retry) vs 23m 24s (successful run)

### Current Configuration
- Default SDK timeout: 900s (15 minutes)
- CLI flag available: `--sdk-timeout`
- Configured in: `guardkit/orchestrator/agent_invoker.py`

## Review Objectives

1. **Analyze timeout frequency** - How often do tasks timeout at 900s while making progress?
2. **Evaluate retry overhead** - What is the cost of retry vs slightly longer initial timeout?
3. **Consider task-type variations** - Should scaffolding, feature, and testing tasks have different timeouts?
4. **Assess user experience** - What's worse: occasional timeouts with retry, or longer waits when stuck?

## Options to Evaluate

| Option | Default Timeout | Pros | Cons |
|--------|----------------|------|------|
| Keep current | 900s (15 min) | Faster failure detection; retry works | Retry overhead; context re-processing |
| Moderate increase | 1200s (20 min) | ~33% more headroom; reduces retries | Longer wait if genuinely stuck |
| Task-type based | 600-1800s | Optimized per task type | More complexity |
| Configurable default | CLI/config | User control | Adds configuration burden |

## Acceptance Criteria

- [ ] Analyze timeout incidents from test logs
- [ ] Quantify retry overhead (time cost of context re-processing)
- [ ] Document recommendation with justification
- [ ] If change recommended, specify exact values per task type
- [ ] Consider backward compatibility of any changes

## Reference Documents

- [Timeout Discussion](docs/reviews/feature-build/consider_timeout_increase.md)
- [Successful Run Log](docs/reviews/feature-build/finally_success.md)

## Implementation Notes

This is a review/decision task. After analysis, the decision point will determine:
- [A]ccept - Keep current 900s timeout
- [I]mplement - Create implementation task(s) for timeout changes
- [R]evise - Request additional data collection

## Test Execution Log

### Review Executed: 2026-01-24

**Decision**: [I]mplement - Create implementation task for Option B (Harmonize defaults to 900s)

**Findings Summary**:
1. Inconsistent defaults across 4 locations (600s, 900s, 1800s)
2. Only 1 timeout observed in FEAT-A96D testing
3. Retry mechanism successfully recovered
4. Retry overhead: 14.5 minutes (62% increase)

**Implementation Task Created**: TASK-FIX-SDKT
- Harmonize all defaults to 900s
- Fix outdated CLI help text
- Low risk, low effort fix

**Report**: [TASK-REV-FB01-sdk-timeout-review-report.md](.claude/reviews/TASK-REV-FB01-sdk-timeout-review-report.md)
