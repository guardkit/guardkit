# Implementation Guide: Graphiti Project-Specific Seeding

**Feature**: FEAT-GPS1
**Parent Review**: TASK-REV-5B3A
**Created**: 2026-03-17

## Wave 1 (All tasks — no dependencies between them)

All 3 tasks can execute in parallel:

| Task | Mode | Priority | Est. Time |
|------|------|----------|-----------|
| TASK-GPS-003 | Manual | High | 5 min |
| TASK-GPS-001 | Direct | Low | 10 min |
| TASK-GPS-002 | task-work | Medium | 2-4 hours |

### TASK-GPS-003: Seed agentic-dataset-factory artefacts (Manual)

**Do first** — this is the immediate remediation.

```bash
cd ~/Projects/appmilla_github/agentic-dataset-factory
guardkit graphiti add-context docs/architecture/ --pattern "**/*.md"
guardkit graphiti add-context docs/architecture/assumptions.yaml
```

Verify:
```bash
guardkit graphiti search "architecture" --limit 5
```

### TASK-GPS-001: Fix post-seed ADR path hint (Direct)

Quick code change in `guardkit/cli/graphiti.py` lines 256-257.

```bash
# No /task-work needed — direct edit
```

### TASK-GPS-002: Auto-seed prompt after /system-arch (task-work)

Larger change requiring design. Use:
```bash
/task-work TASK-GPS-002
```

## Completion Criteria

- All 14 agentic-dataset-factory artefacts queryable in Graphiti
- Post-seed hint shows correct/generic ADR path
- `/system-arch` offers to seed output when Graphiti is available
