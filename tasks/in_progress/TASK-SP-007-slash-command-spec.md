---
complexity: 5
dependencies:
- TASK-SP-003
- TASK-SP-004
- TASK-SP-005
feature_id: FEAT-SP-001
id: TASK-SP-007
implementation_mode: task-work
parent_review: TASK-REV-DBBC
status: in_review
tags:
- system-plan
- slash-command
- spec
task_type: feature
title: Create /system-plan slash command specification
wave: 3
implementation_completed: '2026-02-09T15:30:00Z'
quality_gates:
  code_review_score: 92/100
  code_review_status: APPROVED_WITH_RECOMMENDATIONS
---

# Task: Create /system-plan Slash Command Specification

## Description

Create the `.claude/commands/system-plan.md` specification that defines the `/system-plan` slash command for Claude Code. This is the spec-driven skill that Claude interprets and executes — it orchestrates the interactive flow, question presentation, entity creation, and file output.

## Acceptance Criteria

- [x] `.claude/commands/system-plan.md` created with full command specification
- [x] Command syntax documented: `/system-plan "description" [--mode=MODE] [--focus=FOCUS] [--no-questions]`
- [x] Setup mode flow: 6 category question sequence with per-category checkpoints
- [x] Refine mode flow: shows current state, targeted refinement
- [x] Review mode flow: impact analysis against existing architecture
- [x] ADR capture integrated at every checkpoint (`[A]DR?` option)
- [x] Decision checkpoints: `[C]ontinue / [R]evise / [S]kip / [A]DR?` after each category
- [x] Methodology selection: Modular/Layered/DDD/Event-Driven/Not sure
- [x] DDD-specific questions gated behind DDD methodology selection
- [x] Output artefacts: system-context.md, components/bounded-contexts.md, crosscutting-concerns.md, ADRs, ARCHITECTURE.md
- [x] Graphiti persistence: entities upserted after each category (not batched at end)
- [x] Integration with `/feature-plan`: review mode `[F]eature-plan` option chains to feature planning
- [x] `--no-questions` and `--defaults` flag handling documented
- [x] Error handling: graceful messages for Graphiti unavailable, empty answers, cancelled sessions
- [x] Examples: simple project (modular), complex project (DDD), review mode

## Files to Create

- `.claude/commands/system-plan.md` — Slash command specification

## Implementation Notes

- This is a SPEC file, not Python code — it's read by Claude Code as LLM instructions
- Follow pattern from `installer/core/commands/feature-plan.md` for structure
- The spec should reference the Python modules for entity definitions and Graphiti operations
- Include CRITICAL EXECUTION INSTRUCTIONS section (similar to feature-plan.md)
- The spec defines the interactive UX — Claude follows these instructions to run the session
- Graphiti operations should use the Python library via inline code blocks that Claude executes
- Include mode auto-detection logic that the LLM can follow

## Implementation Summary

### Files Created

- `.claude/commands/system-plan.md` — Slash command specification (997 lines)

### Key Features Implemented

1. **Command Structure**: `/system-plan "description" [--mode=MODE] [--focus=FOCUS] [--no-questions] [--defaults] [--context]`
2. **Mode Auto-Detection**: Setup/refine/review based on Graphiti state
3. **Setup Mode Flow**: 6 structured question categories with per-category checkpoints
4. **Methodology Support**: Modular/Layered/DDD/Event-Driven with DDD-specific question gating
5. **ADR Capture**: Integrated at every checkpoint (`[A]DR?` option)
6. **Graphiti Integration**: Uses SystemPlanGraphiti for upsert operations after each category
7. **Markdown Output**: Uses ArchitectureWriter.write_all() for generating docs/architecture/ files
8. **Error Handling**: Graceful degradation for Graphiti unavailable, empty answers, cancelled sessions
9. **Examples**: Simple modular, complex DDD, and review mode examples

### Code Review Summary (Score: 92/100)

**Status**: APPROVED_WITH_RECOMMENDATIONS

**Minor Issues Identified**:
1. Revision flow (`[R]evise`) not fully detailed (non-blocking)
2. Async/sync wrapper comment could be clearer (non-blocking)
3. Invalid checkpoint input handling not shown (non-blocking)

These can be addressed in follow-up refinement.