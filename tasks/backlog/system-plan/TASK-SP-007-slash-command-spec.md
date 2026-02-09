---
id: TASK-SP-007
title: "Create /system-plan slash command specification"
status: pending
task_type: feature
parent_review: TASK-REV-DBBC
feature_id: FEAT-SP-001
wave: 3
implementation_mode: task-work
complexity: 5
dependencies:
  - TASK-SP-003
  - TASK-SP-004
  - TASK-SP-005
tags: [system-plan, slash-command, spec]
---

# Task: Create /system-plan Slash Command Specification

## Description

Create the `.claude/commands/system-plan.md` specification that defines the `/system-plan` slash command for Claude Code. This is the spec-driven skill that Claude interprets and executes — it orchestrates the interactive flow, question presentation, entity creation, and file output.

## Acceptance Criteria

- [ ] `.claude/commands/system-plan.md` created with full command specification
- [ ] Command syntax documented: `/system-plan "description" [--mode=MODE] [--focus=FOCUS] [--no-questions]`
- [ ] Setup mode flow: 6 category question sequence with per-category checkpoints
- [ ] Refine mode flow: shows current state, targeted refinement
- [ ] Review mode flow: impact analysis against existing architecture
- [ ] ADR capture integrated at every checkpoint (`[A]DR?` option)
- [ ] Decision checkpoints: `[C]ontinue / [R]evise / [S]kip / [A]DR?` after each category
- [ ] Methodology selection: Modular/Layered/DDD/Event-Driven/Not sure
- [ ] DDD-specific questions gated behind DDD methodology selection
- [ ] Output artefacts: system-context.md, components/bounded-contexts.md, crosscutting-concerns.md, ADRs, ARCHITECTURE.md
- [ ] Graphiti persistence: entities upserted after each category (not batched at end)
- [ ] Integration with `/feature-plan`: review mode `[F]eature-plan` option chains to feature planning
- [ ] `--no-questions` and `--defaults` flag handling documented
- [ ] Error handling: graceful messages for Graphiti unavailable, empty answers, cancelled sessions
- [ ] Examples: simple project (modular), complex project (DDD), review mode

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
