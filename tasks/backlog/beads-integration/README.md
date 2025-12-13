# Beads Integration Feature

## Summary

Integrate [Beads](https://github.com/steveyegge/beads) into GuardKit as an optional task backend, providing persistent cross-session memory, full dependency graphs, and distributed sync capabilities while maintaining standalone markdown functionality.

## Feature Overview

**Beads** is a lightweight, git-based issue tracker designed for AI coding agents. It provides:

- **Cross-session memory** - Tasks and context survive compaction
- **Full dependency graphs** - 4 relationship types (blocks, related, parent-child, discovered-from)
- **Distributed sync** - Git-backed multi-machine coordination
- **Ready work queue** - `bd ready` shows unblocked tasks automatically
- **Hash-based IDs** - Collision-free concurrent task creation

## Architecture

This feature implements a **TaskBackend abstraction** that supports multiple backends:

| Backend | Status | Use Case |
|---------|--------|----------|
| **Markdown** | Default | Standalone, zero dependencies |
| **Beads** | Optional | Multi-agent workflows, long-horizon tasks |
| **Backlog.md** | Future | Visual Kanban, team visibility |

## Tasks (8 total)

### Wave 1: Foundation

| ID | Title | Mode | Est. |
|----|-------|------|------|
| [TASK-BI-001](TASK-BI-001-create-taskbackend-interface.md) | Create TaskBackend interface | task-work | 2-3h |
| [TASK-BI-002](TASK-BI-002-implement-markdown-backend.md) | Implement MarkdownBackend | task-work | 3-4h |

### Wave 2: Beads Backend

| ID | Title | Mode | Est. |
|----|-------|------|------|
| [TASK-BI-003](TASK-BI-003-implement-beads-backend.md) | Implement BeadsBackend | task-work | 4-5h |
| [TASK-BI-004](TASK-BI-004-create-backend-registry.md) | Create backend registry | task-work | 2-3h |

### Wave 3: Integration

| ID | Title | Mode | Est. |
|----|-------|------|------|
| [TASK-BI-005](TASK-BI-005-add-configuration-system.md) | Add configuration system | task-work | 2-3h |
| [TASK-BI-006](TASK-BI-006-update-cli-commands.md) | Update CLI commands | task-work | 3-4h |

### Wave 4: Polish

| ID | Title | Mode | Est. |
|----|-------|------|------|
| [TASK-BI-007](TASK-BI-007-create-migration-tooling.md) | Create migration tooling | task-work | 2-3h |
| [TASK-BI-008](TASK-BI-008-update-documentation.md) | Update documentation | direct | 2-3h |

## Total Effort

- **Sequential:** 20-28 hours
- **With Conductor (parallel waves):** 10-14 hours elapsed

## Key Benefits

### For Users

1. **Persistent memory** - AI agents maintain context across sessions
2. **Automatic work selection** - `bd ready` replaces manual task picking
3. **Multi-machine sync** - Work across devices without conflicts
4. **Rich dependencies** - Track how tasks relate and block each other
5. **Zero lock-in** - Can switch back to markdown anytime

### For Future Development

1. **Clean abstraction** - Same interface for all backends
2. **Backlog.md ready** - Architecture supports future visual task management
3. **Extensible** - Easy to add Linear, Jira, or other backends

## Getting Started

After implementation, users can enable Beads with:

```bash
# Install Beads
brew install bd

# Configure GuardKit
guardkit config set backend beads

# Start using!
/task-create "My first Beads-backed task"
```

## Prior Research

This feature builds on extensive prior analysis:

- [Unified Integration Architecture](../../../docs/proposals/integrations/unified-integration-architecture.md)
- [Beads Integration Specification](../../../docs/proposals/integrations/beads/guardkit-beads-integration.md)
- [Backlog.md Analysis](../../../docs/proposals/integrations/backlog.md/guardkit-backlog-integration-analysis.md)
- [Beads-First Development Plan](../../../docs/proposals/integrations/beads-first-development-implementation-plan.md)

## Related

- **Review Task:** [TASK-REV-BEADS](../TASK-REV-BEADS-integrate-beads-into-guardkit.md)
- **Implementation Guide:** [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)
