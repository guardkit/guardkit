---
id: TASK-REV-DBBC
title: "Plan: Build /system-plan command"
status: review_complete
created: 2026-02-09T10:00:00Z
updated: 2026-02-09T10:00:00Z
priority: high
task_type: review
tags: [system-plan, architecture, graphiti, planning]
complexity: 8
---

# Task: Plan /system-plan Command

## Description

Plan the implementation of the `/system-plan` command based on feature spec FEAT-SP-001. This command provides interactive architecture planning that establishes and maintains system-level context in Graphiti, completing the command hierarchy alongside `/task-review` (code level) and `/feature-plan` (feature level).

## Feature Spec

See: `docs/research/system-level-understanding/specs/FEAT-SP-001-system-plan-command.md`

## Key Requirements

- Interactive architecture planning with 3 modes (setup/refine/review)
- Mode auto-detection from Graphiti state
- Adaptive question flow based on selected methodology (Modular/Layered/DDD/Event-Driven)
- Architecture entity definitions with Graphiti integration
- Markdown output artefacts (system-context.md, components.md, ADRs, etc.)
- Integration with /feature-plan for architecture-aware task decomposition
- Integration with AutoBuild coach for architecture context in validation
- Complexity gating for architecture context loading
- Integration and end-to-end tests at technology seams

## Special Testing Focus

Include integration and end-to-end tests to reduce errors at technology seams:
- Entity serialization (to_episode_body() correctness)
- Async/sync boundaries (CLI → async Graphiti operations)
- Group ID prefixing (client.get_group_id() usage)
- Upsert idempotency (running setup twice)
- Search result shape (semantic facts vs structured objects)
- Graceful degradation (Graphiti unavailable/disabled)
- Template rendering (Jinja2 → markdown output)
- CLI command registration and flag parsing
- Coach context assembly (architecture context in prompts)

## Review Decision

**Decision**: Accept (Option 1: Full-Stack Vertical Build)
**Date**: 2026-02-09

### Approach Summary

Build all layers in dependency order across 4 waves with integration tests at every technology seam:

- **Wave 1**: Entity definitions (ComponentDef, SystemContextDef, CrosscuttingConcernDef, ArchitectureDecision, ArchitectureContext) + complexity gating constants
- **Wave 2**: SystemPlanGraphiti operations + SetupQuestionAdapter + ArchitectureWriter (Jinja2 templates)
- **Wave 3**: CLI `guardkit system-plan` command + `.claude/commands/system-plan.md` slash command + integration tests
- **Wave 4**: End-to-end seam tests covering all 9 identified technology seam points

### Key Seam Tests

1. Entity serialization: `to_episode_body()` → `json.dumps()` → `upsert_episode()`
2. Async boundary: `get_graphiti()` sync → `asyncio.run()` → async Graphiti ops
3. Group ID: `client.get_group_id("project_architecture")` → correct prefix
4. Idempotency: Setup run twice → no duplicate episodes
5. Graceful degradation: Graphiti disabled → all paths return None/[]
6. Template rendering: Jinja2 → valid markdown output
7. CLI registration: Click CLI → argument parsing → orchestration
8. Context assembly: `ArchitectureContext.format_for_prompt()` → coach prompt
9. Feature-plan integration: `load_architecture_context()` → enriched planning
