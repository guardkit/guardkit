---
id: TASK-BI-008
title: Update documentation for Beads integration
status: backlog
priority: 2
created_at: 2025-12-13T00:00:00Z
parent_id: TASK-REV-BEADS
implementation_mode: direct
wave: 4
conductor_workspace: wave4-2
complexity: 3
estimated_hours: 2-3
tags:
  - documentation
  - phase-4
blocking_ids:
  - TASK-BI-006
---

# Update Documentation for Beads Integration

## Objective

Update CLAUDE.md, README, and related documentation to cover Beads integration, backend selection, and migration procedures.

## Context

Users need clear documentation on:
1. What Beads integration provides
2. How to enable/configure it
3. When to use each backend
4. Migration procedures

## Implementation Details

### Files to Update

1. **CLAUDE.md** (root)
   - Add "Task Backend Configuration" section
   - Document Beads benefits
   - Add migration instructions

2. **docs/guides/beads-integration-guide.md** (new)
   - Installation instructions
   - Configuration options
   - Workflow differences
   - Troubleshooting

3. **README.md** (if exists)
   - Mention Beads as optional integration

### CLAUDE.md Updates

Add new section after "Installation & Setup":

```markdown
## Task Backend Configuration

GuardKit supports multiple task storage backends:

### Markdown Backend (Default)
- Zero external dependencies
- Works standalone on any machine
- Task files stored in `tasks/` directory
- Best for: Single developers, simple projects

### Beads Backend (Optional)
- Requires Beads CLI (`bd`): `brew install bd`
- Provides cross-session memory for AI agents
- Full dependency graphs (4 relationship types)
- Git-synced distributed state
- `bd ready` for automatic work selection
- Best for: Multi-agent workflows, long-horizon tasks, teams

### Configuring Backend

```bash
# Auto-detect (default) - uses Beads if available
guardkit config set backend auto

# Explicitly use Beads
guardkit config set backend beads

# Force markdown only
guardkit config set backend markdown

# Check current backend
guardkit status
```

### Migrating to Beads

```bash
# Install Beads
brew install bd

# Preview migration
python3 scripts/migrate-tasks.py --to beads --dry-run

# Execute migration
python3 scripts/migrate-tasks.py --to beads

# Rollback if needed
guardkit config set backend markdown
```

### When to Use Each Backend

| Scenario | Recommended Backend |
|----------|---------------------|
| Solo developer, simple project | Markdown (default) |
| Multi-agent workflows | Beads |
| Tasks spanning multiple sessions | Beads |
| Complex dependency graphs | Beads |
| Non-technical stakeholders need visibility | Backlog.md (future) |
| Team needs Kanban board | Backlog.md (future) |
```

### New Guide: docs/guides/beads-integration-guide.md

```markdown
# Beads Integration Guide

## Overview

Beads provides "a memory upgrade for your coding agent" through git-based
persistent storage, dependency tracking, and cross-session context.

## Installation

### macOS
```bash
brew tap steveyegge/beads
brew install bd
```

### Linux
```bash
curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
```

### Verify Installation
```bash
bd --version
# Expected: bd version 0.20.1 or higher
```

## Quick Start

```bash
# Initialize Beads in your project
bd init --quiet

# Configure GuardKit to use Beads
guardkit config set backend beads

# Create your first Beads-backed task
/task-create "My first Beads task"

# See what's ready to work on
bd ready
```

## Key Differences from Markdown Backend

| Aspect | Markdown | Beads |
|--------|----------|-------|
| Task IDs | TASK-A1B2 | bd-a1b2 |
| Dependencies | Basic (blocking_ids) | Full graph (4 types) |
| Ready queue | Manual filter | `bd ready` automatic |
| Cross-session | Limited | Full memory |
| Distributed | No | Yes (git-synced) |

## Dependency Types

Beads supports 4 dependency relationships:

1. **blocks** - Task A must complete before Task B can start
2. **related** - Tasks are related but can proceed independently
3. **parent-child** - Hierarchical relationship (epic → task)
4. **discovered-from** - Task B was discovered while working on Task A

## Best Practices

### Session Start
```bash
# Always check what's ready
bd ready

# Review current context
bd show <task-id>
```

### Session End
```bash
# File any discovered work
/task-create "Discovered issue" --discovered-from <current-task>

# Sync state
bd sync
```

### Multi-Agent Workflows
- Each agent can work independently
- Git sync keeps everyone aligned
- No server required
- Merge conflicts prevented by hash-based IDs

## Troubleshooting

### "bd: command not found"
Beads not installed. See Installation section.

### "Failed to create task"
Check Beads initialization: `bd init --quiet`

### Tasks not syncing
Run manual sync: `bd sync`

### ID conflicts
Upgrade to Beads 0.20.1+ for hash-based IDs.

## Further Reading

- [Beads Documentation](https://github.com/steveyegge/beads)
- [Unified Integration Architecture](../proposals/integrations/unified-integration-architecture.md)
```

## Acceptance Criteria

- [ ] CLAUDE.md updated with backend configuration section
- [ ] New guide: docs/guides/beads-integration-guide.md
- [ ] Installation instructions for all platforms
- [ ] Migration procedures documented
- [ ] Troubleshooting section
- [ ] Links to Beads official docs

## Testing

- Manual review of documentation clarity
- Verify all code examples work
- Check links are valid

## Dependencies

- TASK-BI-006 (CLI updates complete for accurate docs)

## Notes

- Keep docs concise, link to Beads official docs for details
- Include decision tree for backend selection
- Document Backlog.md as "coming soon" for future-proofing
