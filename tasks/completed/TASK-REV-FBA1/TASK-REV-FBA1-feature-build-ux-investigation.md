---
id: TASK-REV-FBA1
title: Continue Feature-Build UX Investigation - Core Issues
status: completed
created: 2025-01-31T10:00:00Z
updated: 2025-01-31T16:30:00Z
completed: 2025-01-31T16:30:00Z
priority: critical
tags: [review, investigation, feature-build, ux, feedback]
task_type: review
decision_required: false
related_review: TASK-REV-BAF6
complexity: 6
review_results:
  mode: investigation
  depth: comprehensive
  findings_count: 3
  recommendations_count: 6
  report_path: .claude/reviews/TASK-REV-FBA1-review-report.md
  completed_at: 2025-01-31T15:30:00Z
  decision: implement
  implementation:
    feature_id: FEAT-FB-UX
    feature_path: tasks/backlog/feature-build-ux/
    phase_1_tasks: 6
    phase_2_tasks: 5
    phase_3_tasks: 5
---

# Task: Continue Feature-Build UX Investigation - Core Issues

## Status: COMPLETED

**Decision**: [I]mplement - Created FEAT-FB-UX with phased implementation plan

## Summary

This investigation corrected misunderstandings from TASK-REV-BAF6 and identified the actual root causes of Feature-Build UX issues:

### Key Findings

1. **Buffered Output Problem**: Claude Code's Bash tool buffers stdout - user sees nothing until command completes
2. **TTY Detection**: Rich library progress bars/spinners require TTY; fail silently in non-TTY context
3. **Timeout Confusion**: Bash tool 120s default vs SDK 900s timeout (documentation gap)

### Strategic Vision

Implemented a **three-phase roadmap** toward event-driven agent orchestration (informed by Reachy PA architecture):

- **Phase 1 (Now)**: File polling + TTY fallback (6 tasks)
- **Phase 2 (Q1)**: NATS JetStream integration (5 tasks)
- **Phase 3 (Q2)**: Multi-interface + A2A semantics (5 tasks)

## Outputs Created

### Review Report
- [.claude/reviews/TASK-REV-FBA1-review-report.md](../../../.claude/reviews/TASK-REV-FBA1-review-report.md)

### Feature Implementation Structure
- [tasks/backlog/feature-build-ux/README.md](../backlog/feature-build-ux/README.md) - Feature overview and roadmap
- [tasks/backlog/feature-build-ux/IMPLEMENTATION-GUIDE.md](../backlog/feature-build-ux/IMPLEMENTATION-GUIDE.md) - Wave execution guide

### Phase 1 Tasks (6 tasks)

| ID | Title | Mode | Wave |
|----|-------|------|------|
| TASK-FB-001 | TTY detection in ProgressDisplay | direct | 1 |
| TASK-FB-002 | Simple text output fallback | task-work | 1 |
| TASK-FB-003 | Progress file writer | task-work | 1 |
| TASK-FB-004 | /feature-build polling integration | task-work | 2 |
| TASK-FB-005 | Timeout documentation update | direct | 2 |
| TASK-FB-006 | --timeout flag passthrough | direct | 2 |

## Original Context

This task continues the investigation from TASK-REV-BAF6 (`.claude/reviews/TASK-REV-BAF6-review-report.md`) with a corrected understanding of the core issues.

### User Feedback on Previous Review

The user disagreed with the findings from TASK-REV-BAF6 for the following reasons:

1. **Incorrect Environment Assumption**: The previous review assumed `/feature-build` issues were related to VS Code Claude Code extension, but the user experienced issues running `/feature-build` from **macOS iTerm shell** (zsh), not VS Code. This is a fundamental misunderstanding that must be corrected.

2. **Lack of Progress Feedback**: When running `/feature-build` in Claude Code, there is insufficient progress feedback compared to running from terminal shell. The user needs visibility into what's happening - at minimum turn information, though not the full verbose output seen in terminal logs.

3. **Premature Task Recommendations**: The original review's Option E recommendations should only be considered AFTER addressing these two core issues.

## Acceptance Criteria

- [x] Correctly identify the iTerm/zsh shell issues (not VS Code assumption)
- [x] Document the actual failure modes when running from shell
- [x] Analyze the progress feedback gap between terminal and Claude Code
- [x] Propose solutions for adequate progress feedback in Claude Code
- [x] Create prioritized task list addressing core issues first
- [x] Defer original review recommendations appropriately

## Evidence Files

- Original review: `.claude/reviews/TASK-REV-BAF6-review-report.md`
- Terminal success example: `docs/reviews/feature-build/finally_success.md`
- Feature-build command spec: `installer/core/commands/feature-build.md`
- AutoBuild orchestrator: `guardkit/orchestrator/autobuild.py`
- Agent invoker: `guardkit/orchestrator/agent_invoker.py`

## Next Steps

1. Execute Wave 1 tasks (TASK-FB-001, FB-002, FB-003) in parallel
2. Execute Wave 2 tasks (TASK-FB-004, FB-005, FB-006) after Wave 1 completes
3. Verify Phase 1 success metrics:
   - User sees progress during build: Yes (polled)
   - Time to first feedback: <60s
   - Non-TTY output quality: Acceptable
