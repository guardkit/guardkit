# Feature: Wire Disconnected Graphiti Reads (FEAT-GWR)

## Problem Statement

The TASK-REV-GROI review found that GuardKit's Graphiti integration diligently writes data (turn states, task outcomes, coach context) but several read paths are disconnected — data is captured but never read back. Before deciding whether to invest further or deprecate Graphiti, we need to connect these reads and measure actual impact.

## Strategy: Connect, Measure, Then Decide

Rather than deprecating a system that's 80% built, we connect the 3 disconnected read paths, run comparative AutoBuild sessions, and let data drive the keep/deprecate decision.

## Subtasks

| ID | Title | Wave | Complexity | Depends On |
|----|-------|------|------------|------------|
| TASK-GWR-001 | Remove dead quality gate config (PATH 10) | 1 | 3 | None |
| TASK-GWR-002 | Wire coach context into CoachValidator.validate() | 2 | 4 | GWR-001 |
| TASK-GWR-003 | Wire outcome reads and turn continuation into AutoBuild | 2 | 5 | GWR-001 |

## Success Criteria

1. All 3 disconnected reads are wired and observable
2. Structured logging confirms data flows end-to-end
3. Round-trip test: write outcome -> retrieve via JobContextRetriever -> found
4. Before/after comparison: 3-5 AutoBuild runs with Graphiti enabled vs disabled
5. No regressions in existing tests

## Parent Review

- **Review**: TASK-REV-GROI (Graphiti ROI Assessment)
- **Report**: `.claude/reviews/TASK-REV-GROI-review-report.md`
- **Strategy**: Option B — Connect, Measure, Then Decide
