---
id: TASK-REV-FB15
title: "Root cause analysis: Why task-work full workflow takes so long"
status: review_complete
created: 2026-01-16T10:00:00Z
updated: 2026-01-16T12:30:00Z
priority: high
tags:
  - review
  - performance
  - root-cause-analysis
  - task-work
  - feature-build
task_type: review
complexity: 6
review_mode: decision
review_depth: comprehensive
related_tasks:
  - TASK-REV-FB14
review_results:
  mode: decision
  depth: comprehensive
  findings_count: 3
  recommendations_count: 6
  decision: implement
  report_path: .claude/reviews/TASK-REV-FB15-review-report.md
  implementation_tasks:
    - TASK-TWP-a1b2
    - TASK-TWP-c3d4
    - TASK-TWP-e5f6
  completed_at: 2026-01-16T12:30:00Z
---

# Root Cause Analysis: Why task-work Full Workflow Takes So Long

## Review Objective

Perform detailed root cause analysis of `/task-work` performance bottlenecks, specifically comparing:
- **Full workflow** (slow): MCP design patterns + architectural review + all phases
- **Micro mode** (acceptable): `--micro` flag bypasses heavy phases

The goal is to identify exactly WHERE time is being spent and WHY.

## Background Context

### Observation
User has observed that:
- `/task-work` with full workflow takes excessively long
- `/task-work --micro` is "decently fast enough"
- The difference suggests specific phases are the culprits

### Prior Analysis (TASK-REV-FB14)
Previous review identified three compounding factors:
1. **Serial SDK Subprocess Spawning** (60% of delay) - Each invocation spawns fresh CLI subprocess
2. **Redundant Context Loading** (25% of delay) - ~900KB loaded repeatedly
3. **No Real-Time Progress Visibility** (15% of friction) - Perceived stalling

### Key Evidence Files
1. `/Users/richardwoollcott/Projects/appmilla_github/guardkit/.claude/reviews/TASK-REV-FB14-review-report.md` - Previous performance analysis
2. `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/research/guardkit-agent/Adversarial_Intensity_and_Workflow_Review.md` - Adversarial intensity research
3. `/Users/richardwoollcott/Projects/appmilla_github/guardkit/docs/reviews/feature-build/stand_alone_manual_design.md` - Standalone task-work execution trace (68K tokens of detailed output)

## Analysis Requirements

### 1. Phase-by-Phase Timing Breakdown
For each phase in the full workflow, determine:
- Actual time spent
- Number of tool calls / API round-trips
- Token consumption
- Whether phase adds proportional value

Phases to analyze:
- Phase 1.6: Clarifying Questions
- Phase 2: Implementation Planning (Agent invocations)
- Phase 2.5A: Design Patterns MCP calls
- Phase 2.5B: Architectural Review (SOLID/DRY/YAGNI)
- Phase 2.7: Complexity Evaluation
- Phase 2.8: Human Checkpoint

### 2. MCP Overhead Analysis
Specifically analyze:
- **design-patterns MCP**: How many calls? What's the latency per call?
- **context7 MCP**: When is it invoked? Is it necessary for simple tasks?
- Token cost of MCP responses vs value delivered

### 3. Context Loading Analysis
From TASK-REV-FB14:
```
CLAUDE.md (root):     29,629 bytes
CLAUDE.md (.claude):   4,091 bytes
Agent files:         145,604 bytes (10 files)
Command files:       720,785 bytes (28 files)
Total:              ~900KB per invocation
```

Questions to answer:
- How much of this context is actually needed per phase?
- What's the token cost of loading this repeatedly?
- Can rules-based loading reduce this?

### 4. Compare: Full Workflow vs --micro
Create side-by-side comparison:

| Aspect | Full Workflow | --micro |
|--------|---------------|---------|
| Phases executed | | |
| Approximate duration | | |
| MCP calls | | |
| Agent invocations | | |
| Token consumption | | |

### 5. Standalone task-work Trace Analysis
Analyze the 68K token trace in `stand_alone_manual_design.md`:
- What's the agent doing during the long phases?
- Where are the pauses?
- Are there redundant operations?

## Success Criteria

- [ ] Phase-by-phase timing breakdown with evidence
- [ ] MCP overhead quantified with specific call counts and latencies
- [ ] Context loading overhead quantified
- [ ] Clear identification of top 3 performance bottlenecks
- [ ] Comparison table: full workflow vs --micro
- [ ] Root cause hypothesis with supporting evidence

## Output

Generate report at: `.claude/reviews/TASK-REV-FB15-review-report.md`

The report should enable informed decision-making about which optimizations to prioritize.

## Related Tasks

- **TASK-REV-FB14**: Previous performance analysis (this builds on it)
- **TASK-REV-FB16**: Optimization strategy evaluation (companion task)

## Notes

The user has a positive mental attitude about this being a valuable learning experience. The goal is actionable insights, not just complaints about slowness. We want to understand the system deeply enough to fix it properly.

"I think we are getting close" - the previous fixes have helped, now we need precision targeting of remaining bottlenecks.
