---
id: TASK-ROT-008
title: Add DeepAgents-specific pattern rules to .claude/rules/patterns/
status: completed
created: 2026-04-02T00:00:00Z
updated: 2026-04-02T00:00:00Z
completed: 2026-04-02T00:00:00Z
priority: low
tags: [template, rules, patterns, deepagents]
parent_review: TASK-REV-TI25
feature_id: FEAT-ROT
implementation_mode: task-work
wave: 4
complexity: 3
depends_on:
  - TASK-ROT-003
completed_location: tasks/completed/TASK-ROT-008/
---

# Task: Add DeepAgents-specific pattern rules

## Description

The current `.claude/rules/patterns/` directory contains generic Standard Structure patterns (builder.md, engine.md, factory.md, etc.) inherited from the `/template-create` auto-detection. These should be supplemented with DeepAgents-specific patterns that match what the orchestrator template actually does.

## Patterns to Add

### 1. `two-model-orchestration.md`
The core pattern: reasoning model drives decisions, implementation model executes. Covers model selection, prompt routing, and evaluation flow.

### 2. `subagent-composition.md`
SubAgent/AsyncSubAgent TypedDict factory functions for hierarchical graph composition. Covers the SubAgent wiring pattern used in `agents.py.template`.

### 3. `domain-prompt-injection.md`
Runtime domain context injection via `domains/{domain}/DOMAIN.md` files with defensive fallback chains.

### 4. `safe-argument-parsing.md`
`parse_known_args()` pattern for LangGraph server compatibility (avoids crashing on injected argv).

## Patterns to Review/Remove

The generic patterns (builder.md, engine.md, entity.md, handler.md, model.md, service-layer.md, validator.md) should be reviewed — keep any that are genuinely used by the template, remove those that are noise from the Standard Structure auto-detection.

## Acceptance Criteria

- [x] At least 3 DeepAgents-specific pattern files added
- [x] Generic patterns reviewed and pruned if not relevant
- [x] Pattern files follow the format of existing patterns in the base template

## Completion Notes

### Added (4 pattern files)
- `two-model-orchestration.md` — Reasoning vs implementation model separation, YAML config, fallback behaviour
- `subagent-composition.md` — SubAgent/AsyncSubAgent TypedDict factories, wiring into create_deep_agent()
- `domain-prompt-injection.md` — Runtime domains/{domain}/DOMAIN.md loading with defensive fallback chain
- `safe-argument-parsing.md` — parse_known_args() for LangGraph server argv compatibility

### Removed (8 generic patterns)
All were empty auto-detected boilerplate with "No examples found in codebase":
- builder.md, engine.md, entity.md, factory.md, handler.md, model.md, service-layer.md, validator.md

### Format
All new patterns include `paths:` frontmatter for conditional loading, real code examples from the template source files, and When to Use / Best Practices sections.
