---
id: TASK-REV-BEADS
title: "Plan: Integrate Beads into GuardKit with Future Backlog.md Compatibility"
status: completed
task_type: review
priority: 1
created_at: 2025-12-13T00:00:00Z
completed_at: 2025-12-13T00:00:00Z
review_mode: decision
review_depth: comprehensive
decision: implement
labels:
  - integration
  - beads
  - architecture
  - memory
related_docs:
  - docs/proposals/integrations/unified-integration-architecture.md
  - docs/proposals/integrations/beads/guardkit-beads-integration.md
  - docs/proposals/integrations/backlog.md/guardkit-backlog-integration-analysis.md
  - docs/proposals/integrations/beads-first-development-implementation-plan.md
implementation_tasks:
  folder: tasks/backlog/beads-integration/
  count: 8
  waves: 4
  total_effort_hours: 20-28
---

# Plan: Integrate Beads into GuardKit

## Context

Beads (github.com/steveyegge/beads, v0.20.1) is a lightweight, git-based issue tracker designed for AI coding agents. It provides persistent memory across sessions, dependency graphs, and a distributed database architecture through git.

Future iterations will integrate Backlog.md (github.com/MrLesk/Backlog.md, 4.1k stars) for visual task management. The implementation should use an architecture that accommodates both tools via a common abstraction layer.

## Prior Research

Extensive research exists in `docs/proposals/integrations/`:
- **unified-integration-architecture.md**: Defines TaskBackend abstraction
- **guardkit-beads-integration.md**: Detailed Beads backend specification
- **guardkit-backlog-integration-analysis.md**: Backlog.md plugin architecture
- **beads-first-development-implementation-plan.md**: Phased implementation strategy

## Objective

Design and implement Beads integration into GuardKit using a pluggable TaskBackend architecture that:
1. Maintains GuardKit's standalone functionality (Markdown backend default)
2. Enables optional Beads integration for enhanced memory/dependencies
3. Prepares common abstraction for future Backlog.md integration

## Acceptance Criteria

- [ ] TaskBackend abstraction interface defined
- [ ] MarkdownBackend extracted from current implementation
- [ ] BeadsBackend implemented with CLI integration
- [ ] Backend auto-detection and registry
- [ ] Configuration system for backend selection
- [ ] CLI commands updated to use abstraction
- [ ] Migration tooling for existing tasks
- [ ] Documentation updated
