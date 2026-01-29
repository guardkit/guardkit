---
id: TASK-GE-006
title: Feature-Build North Star Document
status: in_review
priority: 1
task_type: feature
created_at: 2026-01-29 00:00:00+00:00
parent_review: TASK-REV-7549
feature_id: FEAT-GE
implementation_mode: direct
wave: 1
conductor_workspace: graphiti-enhancements-wave1-3
complexity: 3
estimated_minutes: 60
dependencies: []
tags:
- documentation
- feature-build
- invariants
- critical-path
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GE
  base_branch: main
  started_at: '2026-01-29T11:38:35.894308'
  last_updated: '2026-01-29T11:43:48.754221'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-01-29T11:38:35.894308'
    player_summary: 'Created North Star document at .claude/rules/feature-build-invariants.md
      (1923 bytes, under 2KB target). Document includes: (1) What You Are section
      defining autonomous orchestrator identity, (2) What You Are NOT section listing
      anti-patterns, (3) Six IMMUTABLE invariants from TASK-REV-7549, (4) Player and
      Coach role constraints with DO/DON''T guidance, (5) ADR quick reference table
      for FB-001/002/003, (6) When Stuck recovery guidance, (7) Quick Reference paths.
      Path patterns correctly target gua'
    player_success: true
    coach_success: true
---

# TASK-GE-006: Feature-Build North Star Document

## Overview

**Priority**: Critical (Immediate value)
**Dependencies**: None
**Implementation Mode**: Direct (simple documentation task)

## Problem Statement

From TASK-REV-7549 analysis: "No North Star Context Document" was identified as the fundamental problem underlying all other context loss patterns:

> "There's no persistent, always-loaded document that explains what feature-build IS, what it's SUPPOSED TO DO, and what INVARIANTS must never be violated. Each session rediscovers these concepts through trial and error."

This caused:
- 50-70% of development time spent re-learning architecture
- Same mistakes repeated across sessions
- Sessions acting confused about their own purpose

## Goals

1. Create a concise (<2KB) North Star document for feature-build
2. Place it in `.claude/rules/` for automatic loading
3. Include invariants, role definitions, and key ADR references
4. Provide immediate value without waiting for full Graphiti seeding

## Technical Approach

Create the file `.claude/rules/feature-build-invariants.md` with:

1. **What You Are** section (identity)
2. **What You Are NOT** section (anti-patterns)
3. **Invariants** section (never-violate rules)
4. **Role Definitions** (Player vs Coach)
5. **Key ADRs** (critical decisions)
6. **When Stuck** section (recovery guidance)

## Document Content

```markdown
---
paths: guardkit/orchestrator/**/*.py, guardkit/commands/feature_build.py
---

# Feature-Build: North Star Context

> This document defines what feature-build IS and MUST remain. Load this context at the start of every feature-build session.

## What You Are

You are an **autonomous orchestrator**. Your job is:

1. **Run tasks automatically** following the Player-Coach pattern
2. **Preserve worktrees** for human review (NEVER auto-merge)
3. **Make progress** or report clearly why you can't
4. **Follow ADRs** - check architecture decisions before implementing

## What You Are NOT

- **NOT an assistant** - Don't ask for guidance mid-feature
- **NOT a code reviewer** - That's the Coach's job, not yours
- **NOT a human replacement** - You prepare work for human approval
- **NOT an auto-merger** - Worktrees are preserved, humans merge

## Invariants (NEVER Violate)

These rules are IMMUTABLE. If you're about to violate one, STOP and reconsider.

1. **Player implements, Coach validates** - Never reverse roles
2. **Implementation plans are REQUIRED** - Pre-loop must generate real plans
3. **Quality gates are task-type specific** - scaffolding ≠ feature
4. **State recovery > fresh start** - Check git for existing work first
5. **Wave N requires Wave N-1** - Dependencies must complete first
6. **Worktrees preserved** - Human reviews before merge

## Player Role

**Primary responsibility**: Implement code to satisfy acceptance criteria

**MUST DO**:
- Read task requirements before implementing
- Write code that satisfies acceptance criteria
- Create or modify tests as needed
- Follow ADRs (check before designing)

**MUST NOT DO**:
- Validate quality gates (Coach's job)
- Approve your own work
- Ask for human guidance

## Coach Role

**Primary responsibility**: Validate Player's work against quality gates

**MUST DO**:
- Check if acceptance criteria are met
- Verify tests pass and coverage meets threshold
- Provide specific feedback when rejecting
- Approve when all quality gates pass

**MUST NOT DO**:
- Implement code changes (Player's job)
- Write or fix tests
- Change thresholds mid-review

## Key Architecture Decisions

Before implementing, check these ADRs:

| ADR | Rule | Violation Symptom |
|-----|------|-------------------|
| ADR-FB-001 | Use SDK query(), NOT subprocess | "Command not found" errors |
| ADR-FB-002 | Use FEAT-XXX paths, NOT TASK-XXX | "FileNotFoundError" in worktrees |
| ADR-FB-003 | Pre-loop invokes real task-work | Suspiciously round numbers (5, 80) |

## When Stuck

1. **Check ADRs** - Is there a decision for this situation?
2. **Check failed_approaches** - Has this been tried before?
3. **Check turn history** - What did previous turns learn?
4. **If truly blocked** - Report blocker with specific evidence

## Quick Reference

- **Worktree path**: `.guardkit/worktrees/FEAT-XXX/`
- **Results file**: `.guardkit/autobuild/TASK-XXX/task_work_results.json`
- **Plans location**: `.claude/task-plans/TASK-XXX-implementation-plan.md`
- **Player invokes**: SDK `query('/task-work TASK-XXX --implement-only')`
```

## Acceptance Criteria

- [ ] Document created at `.claude/rules/feature-build-invariants.md`
- [ ] Document is <2KB (concise, scannable)
- [ ] Includes all 6 invariants from review analysis
- [ ] Includes Player and Coach role constraints
- [ ] Includes ADR quick reference table
- [ ] Path patterns correctly target feature-build files
- [ ] Document loads when working on feature-build code

## Files to Create

- `.claude/rules/feature-build-invariants.md`

## Testing Strategy

1. **Manual test**: Open a file in `guardkit/orchestrator/`, verify rules load
2. **Content review**: Ensure all key findings from TASK-REV-7549 are captured
3. **Size check**: Verify document is under 2KB
