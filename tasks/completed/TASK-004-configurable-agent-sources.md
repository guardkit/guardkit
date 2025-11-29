---
id: TASK-004
title: Configurable Agent Sources
status: backlog
created: 2025-11-01T20:30:00Z
priority: medium
complexity: 3
estimated_hours: 3
tags: [agent-discovery, configuration]
epic: EPIC-001
feature: agent-discovery
dependencies: [TASK-003]
blocks: [TASK-009]
---

# TASK-004: Configurable Agent Sources

## Objective

JSON-based configuration for agent sources (local, company-internal, etc.) with priority ordering and authentication support.

**Note**: Kept from original approach - enterprise-ready extensibility.

## Acceptance Criteria

- [ ] JSON configuration for agent sources
- [ ] Support for local, GitHub, HTTP sources
- [ ] Priority ordering and bonus scoring
- [ ] Authentication (env variables, tokens)
- [ ] Default config includes local sources
- [ ] CLI commands to manage sources

## Implementation

**Reference**: See archived `tasks/archive/epic-001-algorithmic-approach/TASK-048C-configurable-agent-sources.md`

## Definition of Done

- [ ] Agent source registry implemented
- [ ] Configuration management working
- [ ] Local-first with configurable priorities
- [ ] Unit tests passing

**Estimated Time**: 3 hours | **Complexity**: 3/10 | **Priority**: MEDIUM
