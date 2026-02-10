---
id: TASK-REV-AEA7
title: "Plan: System Context Read Commands (FEAT-SC-001)"
status: completed
created: 2026-02-10T11:15:00Z
updated: 2026-02-10T11:15:00Z
priority: high
task_type: review
tags: [system-context, architecture, graphiti, planning, commands]
complexity: 7
feature_spec: docs/research/system-level-understanding/FEAT-SC-001-system-context-read-commands.md
---

# Task: Plan System Context Read Commands (FEAT-SC-001)

## Description

Plan the implementation of three read-only commands that consume the architecture knowledge `/system-plan` produces:
- `/system-overview` — condensed architecture summary (one-screen default)
- `/impact-analysis` — pre-task validation against known architecture
- `/context-switch` — multi-project navigation with Graphiti namespace switching

Plus AutoBuild coach integration for architecture-aware code review.

## Feature Spec

See: `docs/research/system-level-understanding/FEAT-SC-001-system-context-read-commands.md`

## Key Requirements

- All commands are read-only (no Graphiti writes needed)
- Build on existing `SystemPlanGraphiti` read operations
- Graceful degradation when Graphiti unavailable or no architecture context
- Token-budgeted injection for coach and feature-plan contexts
- Risk scoring heuristic for impact analysis (1-5 scale)
- Interactive decision checkpoints following established patterns
- Integration and E2E tests at technology seams to reduce build errors

## Acceptance Criteria

See feature spec for detailed acceptance criteria per command.

## Review Focus

- Technical feasibility against existing codebase
- Task breakdown with integration test emphasis
- Dependency ordering and parallel execution groups
- Risk identification at technology seams (Graphiti, CLI, config)
