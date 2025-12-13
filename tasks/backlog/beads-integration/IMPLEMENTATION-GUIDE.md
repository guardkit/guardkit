# Beads Integration - Implementation Guide

## Overview

This guide details the implementation strategy for integrating Beads into GuardKit using a pluggable TaskBackend architecture. The design supports future Backlog.md integration via the same abstraction.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     GuardKit Core Layer                          │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────┐   │
│  │   Quality     │  │     Agent     │  │    Task Workflow   │   │
│  │    Gates      │  │ Orchestration │  │   (task-create/    │   │
│  │  (Test/Lint)  │  │  (sub-agents) │  │  work/complete)    │   │
│  └───────────────┘  └───────────────┘  └───────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 TaskBackend Interface                      │  │
│  │  create() | get() | update() | close() | list_ready()     │  │
│  │  add_dependency() | create_child() | sync()               │  │
│  └──────────────────────────────────────────────────────────┘  │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│ MarkdownBackend │  │  BeadsBackend   │  │BacklogMdBackend │
│   (Default)     │  │   (Optional)    │  │    (Future)     │
│                 │  │                 │  │                 │
│  tasks/*.md     │  │   .beads/       │  │   /backlog/     │
│  Zero deps      │  │   bd CLI        │  │   MCP/CLI       │
│  Single machine │  │   Multi-machine │  │   Web UI        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Wave-Based Execution Strategy

Tasks are organized into 4 waves for parallel execution with Conductor.

### Wave 1: Foundation (Can Execute in Parallel)

| Task | Description | Mode | Workspace |
|------|-------------|------|-----------|
| TASK-BI-001 | Create TaskBackend interface | task-work | wave1-1 |
| TASK-BI-002 | Implement MarkdownBackend | task-work | wave1-2 |

**Prerequisites:** None
**Blocking:** Wave 2
**Estimated:** 5-7 hours combined

### Wave 2: Beads Backend (Can Execute in Parallel)

| Task | Description | Mode | Workspace |
|------|-------------|------|-----------|
| TASK-BI-003 | Implement BeadsBackend | task-work | wave2-1 |
| TASK-BI-004 | Create backend registry | task-work | wave2-2 |

**Prerequisites:** Wave 1 complete
**Blocking:** Wave 3
**Estimated:** 6-8 hours combined

### Wave 3: Integration (Can Execute in Parallel)

| Task | Description | Mode | Workspace |
|------|-------------|------|-----------|
| TASK-BI-005 | Add configuration system | task-work | wave3-1 |
| TASK-BI-006 | Update CLI commands | task-work | wave3-2 |

**Prerequisites:** Wave 2 complete
**Blocking:** Wave 4
**Estimated:** 5-7 hours combined

### Wave 4: Polish (Can Execute in Parallel)

| Task | Description | Mode | Workspace |
|------|-------------|------|-----------|
| TASK-BI-007 | Create migration tooling | task-work | wave4-1 |
| TASK-BI-008 | Update documentation | direct | wave4-2 |

**Prerequisites:** Wave 3 complete
**Blocking:** None
**Estimated:** 4-6 hours combined

## Dependency Graph

```
TASK-BI-001 ──┬──> TASK-BI-002 ──┬──> TASK-BI-004 ──┬──> TASK-BI-005 ──┬──> TASK-BI-007
              │                  │                  │                  │
              └──────────────────┴──> TASK-BI-003 ──┘                  ├──> TASK-BI-008
                                                                       │
                                           TASK-BI-006 <───────────────┘
```

## File Structure

After implementation, new files will be:

```
installer/core/
├── backends/
│   ├── __init__.py          # Package exports, registry
│   ├── base.py              # TaskBackend ABC, dataclasses
│   ├── markdown.py          # MarkdownBackend implementation
│   └── beads.py             # BeadsBackend implementation
├── lib/
│   └── config.py            # GuardKitConfig dataclass

scripts/
└── migrate-tasks.py         # Migration tooling

docs/guides/
└── beads-integration-guide.md  # User documentation
```

## Key Design Decisions

### 1. CLI over MCP for Beads Integration

**Decision:** Use `bd` CLI commands via subprocess instead of MCP server.

**Rationale:**
- CLI: 1-2k tokens per operation
- MCP: 10-50k tokens for schema loading
- CLI is simpler and more reliable
- MCP can be added later if needed

### 2. Hash-Based ID Alignment

**Decision:** Leverage existing hash-based ID systems in both tools.

**Rationale:**
- GuardKit: `TASK-A1B2` (hash-based since TASK-ID-HASH migration)
- Beads: `bd-a1b2` (hash-based since v0.20.1)
- Zero friction for ID mapping/migration

### 3. Metadata in Notes Field

**Decision:** Store GuardKit-specific metadata in Beads' notes field.

**Rationale:**
- Beads doesn't have custom fields
- Notes field is free-form markdown
- Structured format allows parsing
- Preserves all GuardKit data

### 4. Auto-Detection with Override

**Decision:** Auto-detect backend but allow explicit configuration.

**Rationale:**
- Beads when: `bd` installed + `.beads` exists
- Markdown when: Beads unavailable or configured off
- Users can override via config

## Testing Strategy

### Unit Tests

Each backend should have isolated unit tests:
- `tests/backends/test_base.py` - Dataclass tests
- `tests/backends/test_markdown.py` - MarkdownBackend tests
- `tests/backends/test_beads.py` - BeadsBackend tests (skip if bd unavailable)
- `tests/backends/test_registry.py` - Registry and detection tests

### Integration Tests

End-to-end tests for full workflows:
- Create task → Get → Update → Close
- Migration: Markdown → Beads → Verify
- CLI command integration

### CI/CD Considerations

```yaml
# In GitHub Actions
- name: Test with Beads
  if: runner.os == 'Linux'
  run: |
    # Install Beads
    curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash
    # Run full test suite
    pytest tests/backends/

- name: Test without Beads
  run: |
    # Skip Beads tests, verify markdown works
    pytest tests/backends/ -k "not beads"
```

## Rollback Strategy

If issues arise after enabling Beads:

1. **Immediate rollback:** `guardkit config set backend markdown`
2. **Original files preserved:** Markdown tasks remain in `tasks/`
3. **ID mapping saved:** `.guardkit/migration-mapping.json`
4. **Full rollback:** Delete `.beads/` directory

## Future: Backlog.md Integration

The TaskBackend abstraction enables future Backlog.md integration:

```python
class BacklogMdBackend(TaskBackend):
    """Future backend for Backlog.md integration."""

    @property
    def backend_name(self) -> str:
        return "backlog.md"

    @property
    def supports_web_ui(self) -> bool:
        return True  # Full Kanban board

    @property
    def supports_mcp(self) -> bool:
        return True  # Native MCP server
```

Estimated additional effort: 4-5 hours once Beads integration complete.

## Success Criteria

Integration is complete when:

- [ ] All 8 tasks marked complete
- [ ] Unit tests passing (with and without Beads)
- [ ] Integration tests for CLI commands
- [ ] Documentation reviewed and merged
- [ ] `/task-create` works with both backends
- [ ] `/task-work` uses `bd ready` when Beads enabled
- [ ] `/task-complete` syncs with Beads when enabled
- [ ] Migration script tested on sample project

## Total Effort Estimate

| Phase | Tasks | Effort |
|-------|-------|--------|
| Wave 1: Foundation | 2 | 5-7 hrs |
| Wave 2: Beads Backend | 2 | 6-8 hrs |
| Wave 3: Integration | 2 | 5-7 hrs |
| Wave 4: Polish | 2 | 4-6 hrs |
| **Total** | **8** | **20-28 hrs** |

With Conductor parallel execution (2 tasks per wave): **10-14 hours elapsed time**

## References

- [Unified Integration Architecture](../../../docs/proposals/integrations/unified-integration-architecture.md)
- [Beads Integration Specification](../../../docs/proposals/integrations/beads/guardkit-beads-integration.md)
- [Beads-First Development Plan](../../../docs/proposals/integrations/beads-first-development-implementation-plan.md)
- [Beads Repository](https://github.com/steveyegge/beads)
