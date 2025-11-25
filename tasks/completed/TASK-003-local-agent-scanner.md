---
id: TASK-003
title: Local Agent Scanner
status: backlog
created: 2025-11-01T20:30:00Z
priority: medium
complexity: 4
estimated_hours: 4
tags: [agent-discovery, local-agents]
epic: EPIC-001
feature: agent-discovery
dependencies: []
blocks: [TASK-009]
---

# TASK-003: Local Agent Scanner

## Objective

Scan `installer/global/agents/` directory to discover existing taskwright agents (architectural-reviewer, code-reviewer, test-orchestrator, etc.) for inclusion in templates.

**Note**: Kept from original approach - implementation is sound and valuable.

## Acceptance Criteria

- [ ] Scan `installer/global/agents/` directory
- [ ] Parse agent markdown files
- [ ] Extract metadata: name, description, tools, technologies, specializations
- [ ] Discover 15+ existing agents
- [ ] Caching with 5-minute TTL
- [ ] Support for custom local agent directories
- [ ] Unit tests passing

## Implementation

**Reference**: See archived `tasks/archive/epic-001-algorithmic-approach/TASK-048B-local-agent-scanner.md` for full implementation details.

Key components:
- `LocalAgentScanner` class
- Markdown parsing for agent metadata
- Technology/specialization tagging
- Caching mechanism

## Definition of Done

- [ ] Scanner discovers 15+ agents from `installer/global/agents/`
- [ ] Metadata extraction working
- [ ] Caching implemented
- [ ] Unit tests passing
- [ ] Integration with TASK-009

**Estimated Time**: 4 hours | **Complexity**: 4/10 | **Priority**: MEDIUM
