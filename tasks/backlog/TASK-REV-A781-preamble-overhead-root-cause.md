---
id: TASK-REV-A781
title: Root cause analysis of task-work session preamble consuming 1800s
status: review_complete
task_type: review
review_mode: architectural
review_depth: deep
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T14:00:00Z
priority: high
tags: [autobuild, preamble, performance, root-cause-analysis, architecture-review]
complexity: 0
decision_required: true
related_tasks: [TASK-ASF-001, TASK-ASF-008]
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: deep
  findings_count: 4
  recommendations_count: 5
  report_path: .claude/reviews/TASK-REV-A781-review-report.md
  root_causes:
    - "Massive context injection (~1MB per SDK session, 60% of overhead)"
    - "Serial subagent invocations during design phases (25% of overhead)"
    - "Double SDK session initialization (15% of overhead)"
  decision: fix_preamble_phased
---

# Task: Root Cause Analysis - Task-Work Session Preamble Overhead (1800s)

## Source Context

Analysis originated from: `docs/reviews/feature-build/gap_analysis.md`

Key excerpt from gap analysis (Minor Observations):
> The session preamble overhead (F1 root cause) isn't addressed by any task — ASF-001 works around it and ASF-008 increases the timeout, but neither investigates why the task-work session preamble consumes 1800s. For Wave 2 tasks (complexity 4-6) that must use task-work mode, this will recur. Worth noting as a backlog item.

## Problem Statement

During autobuild execution, the `/task-work` session preamble consumes approximately 1800 seconds (30 minutes) before actual implementation work begins. This was identified as the **F1 root cause** in the autobuild stall investigation.

### Current Workarounds (Not Fixes)
- **ASF-001**: Switches SFT-001 to `implementation_mode: direct`, bypassing the task-work preamble entirely
- **ASF-008**: Increases SDK timeout to accommodate the preamble overhead

Neither workaround addresses **why** the preamble takes 1800s. For Wave 2 tasks (complexity 4-6) that must use `task-work` mode, this overhead will recur and potentially cause timeouts or stalls.

## Review Objectives

1. **Identify what happens during the task-work preamble** - Map every operation from session start to first implementation action
2. **Quantify time consumption** - Determine which operations consume the most time
3. **Discover the root cause** - Why does it take 1800s? Is it:
   - Command/skill loading overhead?
   - CLAUDE.md / rules file parsing?
   - Context loading (Graphiti, MCP servers)?
   - Phase 1-2 planning overhead?
   - SDK/model initialization latency?
   - Some combination?
4. **Assess impact on Wave 2 tasks** - Will complexity 4-6 tasks hit the same problem?
5. **Recommend fix approach** - Concrete implementation tasks to reduce preamble to acceptable levels

## Investigation Areas

### Area 1: Task-Work Command Loading
- What files are loaded when `/task-work` is invoked?
- How large is the command specification?
- Are there redundant loads or circular references?

### Area 2: Session Context Initialization
- CLAUDE.md parsing (root + .claude/CLAUDE.md + rules)
- MCP server connections (Context7, design-patterns, Graphiti)
- Template/agent file loading
- How much context is injected before first turn?

### Area 3: Phase 1-2 Execution
- Phase 1 (Load Task Context) - What does it load and how long?
- Phase 1.5 (Library Context) - Context7 resolution timing
- Phase 2 (Implementation Planning) - Planning prompt size and response time
- Phase 2.5 (Architectural Review) - Review overhead

### Area 4: SDK and Model Interaction
- Claude SDK session initialization time
- First-turn prompt size (how many tokens?)
- Model response latency for large context prompts
- Are there unnecessary round-trips?

### Area 5: Comparison with Direct Mode
- Why does direct mode (`_invoke_player_direct()`) avoid this overhead?
- What does direct mode skip vs task-work mode?
- Can task-work mode adopt any direct mode efficiencies?

## Acceptance Criteria

- [ ] Complete timeline of preamble operations with timing data
- [ ] Root cause identified with evidence
- [ ] Impact assessment for Wave 2 tasks documented
- [ ] Concrete recommendations with estimated complexity
- [ ] Decision: Fix preamble vs. optimize task-work vs. expand direct mode coverage

## Related Context

| Resource | Relevance |
|----------|-----------|
| `docs/reviews/feature-build/gap_analysis.md` | Source of this investigation |
| `TASK-ASF-001` | Direct mode workaround |
| `TASK-ASF-008` | Timeout increase workaround |
| `installer/core/commands/task-work.md` | Task-work command specification |
| `.claude/rules/autobuild.md` | Autobuild orchestration rules |
| Feature build orchestrator code | Player/Coach session initialization |

## Review Approach

Recommended: `/task-review TASK-REV-A781 --mode=architectural --depth=deep`

This should trace the full execution path from autobuild invoking `/task-work` through to the first implementation action, identifying every time-consuming operation along the way.
