---
id: TASK-GR-REV-002
title: Review implementation_mode design - should 'manual' exist?
status: completed
created: 2026-01-31T15:00:00Z
updated: 2026-01-31T16:45:00Z
completed: 2026-01-31T16:45:00Z
priority: high
tags: [review, architecture, implementation-mode, autobuild, design]
task_type: review
decision_required: true
complexity: 5
parent_review: TASK-GR-REV-001
review_results:
  decision: remove_manual_mode
  implementation_tasks_created: 4
  report_path: .claude/reviews/TASK-GR-REV-002-review-report.md
  completed_at: 2026-01-31T16:30:00Z
completed_location: tasks/completed/TASK-GR-REV-002/
related_artifacts:
  - installer/core/lib/implementation_mode_analyzer.py
  - guardkit/orchestrator/feature_orchestrator.py
  - guardkit/orchestrator/agent_invoker.py
---

# Task: Review implementation_mode Design - Should 'manual' Exist?

## Description

Following TASK-GR-REV-001 (AutoBuild failure analysis), this review examines the fundamental design question:

**Should `implementation_mode: manual` exist in GuardKit's task system?**

The AutoBuild failure in FEAT-GR-MVP exposed that:
1. `manual` mode tasks cannot be executed by AutoBuild
2. Research/documentation tasks were marked as `manual` but could be handled by `/task-work`
3. There's no clear definition of what makes a task truly "manual"

## Context

### Current implementation_mode Values

| Mode | Intent | AutoBuild Support |
|------|--------|-------------------|
| `task-work` | Full quality gates, architectural review | ✅ Fully supported |
| `direct` | Lightweight SDK execution, no plan needed | ✅ Supported |
| `manual` | Human-only execution | ❌ Not supported (fails) |

### What `manual` Was Designed For

From `implementation_mode_analyzer.py`:
```python
MANUAL_KEYWORDS = [
    "run script", "execute script", "bulk operation",
    "migration script", "manual execution", "run command"
]
```

Intent: Tasks requiring human oversight, like migrations or bulk operations.

### The Problem

With AI-assisted development and `/task-work` adaptive workflow:
- AI can research and create documentation
- AI can execute scripts with proper verification
- AI can handle complex tasks (complexity 7-10 with checkpoints)
- `--micro` flag available for very simple changes

**What genuinely requires human-only execution?**

## Review Questions

### Q1: What scenarios genuinely require human-only execution?

Candidates:
- Deploying to production (but GitOps automates this)
- Third-party configuration (but APIs exist)
- Physical actions (printing, hardware)
- Legal/compliance approvals (human-in-the-loop)

### Q2: Can AI handle research/documentation tasks via `/task-work`?

The TASK-GR-PRE-003-A ("Research graphiti-core upsert") was marked manual.
But AI could:
- Read graphiti-core source code
- Analyze API documentation
- Create an ADR with findings
- Propose implementation strategies

### Q3: Should `/feature-build` skip manual tasks or fail on them?

Options:
1. **Skip gracefully** - Return "skipped" result, don't block wave
2. **Fail loudly** - Current behavior, wastes 25 retries
3. **Prompt user** - Interactive mode asks user to complete
4. **Remove manual** - Eliminate the mode entirely

### Q4: If `manual` is removed, what happens to existing tasks?

Migration options:
1. Convert all `manual` to `task-work`
2. Convert to `direct` for simple changes
3. Fail validation for unsupported mode
4. Keep as deprecated, warn on use

## Analysis Areas

### 1. Audit Existing `manual` Tasks

Search codebase for tasks with `implementation_mode: manual` and categorize:
- Research tasks (could be task-work)
- Migration scripts (could be task-work with verification)
- Infrastructure changes (could use IaC tools)
- Truly manual (what's left?)

### 2. Review implementation_mode_analyzer.py

Examine the keyword-based assignment logic:
- Are MANUAL_KEYWORDS appropriate?
- Should "research" trigger manual mode?
- Should any keyword trigger manual mode?

### 3. Examine AutoBuild Behavior

Current: AutoBuild attempts to execute manual tasks, fails on PlanNotFoundError.
Should: Either skip or remove the mode entirely.

### 4. User Expectations

What do users expect when they see `implementation_mode: manual`?
- "I need to do this myself" → Then why is it in AutoBuild?
- "AI can't do this" → But can it, with proper prompting?

## Acceptance Criteria

- [ ] Document scenarios where human-only execution is truly required
- [ ] Analyze if AI can handle "research" and "documentation" task types
- [ ] Recommend: Keep (with fixes) vs Remove `manual` mode
- [ ] If keep: Define clear criteria for when to use it
- [ ] If remove: Provide migration path for existing tasks
- [ ] Create implementation tasks based on decision

## Files to Review

1. `installer/core/lib/implementation_mode_analyzer.py` - Mode assignment logic
2. `guardkit/orchestrator/feature_orchestrator.py` - AutoBuild dispatch (no routing)
3. `guardkit/orchestrator/agent_invoker.py` - Only handles `direct` mode
4. `guardkit/tasks/state_bridge.py` - Stub creation for `task-work` only
5. `installer/core/commands/feature-plan.md` - Mode documentation

## Implementation Notes

This is a **review task** - use `/task-review TASK-GR-REV-002 --mode=decision` to execute.

Expected outcome: Decision checkpoint with options to:
- [A]ccept current design (but add skip logic for manual in AutoBuild)
- [I]mplement removal of manual mode
- [R]evise with deeper investigation of user expectations
- [C]ancel if manual mode is actually needed as-is

## References

- TASK-GR-REV-001: AutoBuild failure analysis (parent review)
- FEAT-GR-MVP: Feature that exposed the issue
- TASK-GR-PRE-003-A: Research task that failed (implementation_mode: manual)
