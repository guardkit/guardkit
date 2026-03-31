# Implementation Guide: Graphiti Command Availability Fix (FEAT-CD64)

**Parent Review**: REV-SD-001
**Feature ID**: FEAT-CD64
**Commands Affected**: 8 (`/system-design`, `/system-arch`, `/system-plan`, `/system-overview`, `/impact-analysis`, `/arch-refine`, `/design-refine`, `/context-switch`)

## Wave Breakdown

### Wave 1: Foundation (2 tasks, parallel)

| Task | Title | Mode | Est. Complexity |
|------|-------|------|-----------------|
| TASK-GCA-001 | Create shared Graphiti preamble | task-work | 3 |
| TASK-GCA-007 | Document group ID strategy | direct | 2 |

**No dependencies** — these can execute in parallel.

**TASK-GCA-001** is the critical path item. All Wave 2 tasks depend on the preamble it creates.

### Wave 2: Apply Across Commands (5 tasks, parallel)

| Task | Title | Mode | Est. Complexity | Commands |
|------|-------|------|-----------------|----------|
| TASK-GCA-002 | Fix /system-design | task-work | 5 | system-design |
| TASK-GCA-003 | Fix /system-arch | task-work | 5 | system-arch |
| TASK-GCA-004 | Fix /system-plan | task-work | 4 | system-plan |
| TASK-GCA-005 | Fix overview/impact/context | task-work | 4 | system-overview, impact-analysis, context-switch |
| TASK-GCA-006 | Fix refine commands | task-work | 5 | arch-refine, design-refine |

**All depend on TASK-GCA-001**. Independent of each other — can run in 5 parallel Conductor workspaces.

## Key Pattern: Before and After

### Before (Broken — Python pseudocode)

```python
from guardkit.knowledge.graphiti_client import get_graphiti
client = get_graphiti()  # LLM cannot execute this
if client:
    sp = SystemDesignGraphiti(client, project_id="current_project")
    # ... Graphiti operations (never reached)
else:
    print("Graphiti unavailable")  # Always reached
```

### After (Fixed — Tool-native instructions)

```markdown
### Graphiti Availability Check

Use the Read tool to read `.guardkit/graphiti.yaml`.

**IF** the file exists AND contains `enabled: true`:
  - SET graphiti_available = true
  - Note the connection details (host, port) and group_ids

**IF** the file does not exist OR `enabled:` is false/missing:
  - SET graphiti_available = false
  - DISPLAY the GRAPHITI_UNAVAILABLE_MESSAGE

**See**: `installer/core/commands/lib/graphiti-preamble.md` for full check pattern
```

### After (Fixed — Seeding)

```markdown
### Graphiti Seeding

**IF graphiti_available**, display seeding commands for generated artefacts:

```bash
# Seed API contracts
guardkit graphiti add-context docs/design/contracts/order-management-api.yaml --group project_design

# Seed data models
guardkit graphiti add-context docs/design/models/order-management-models.md --group project_design

# Seed design decisions
guardkit graphiti add-context docs/design/decisions/DDR-001.md --group architecture_decisions
```

Ask: "Execute seeding commands now? [Y/n]"
If yes, run each via Bash tool.
```

## Verification

After implementation, verify by:

1. Running `/system-design` in a project with `.guardkit/graphiti.yaml` (`enabled: true`)
2. Confirming the command detects Graphiti as available
3. Confirming seeding commands are generated (not Python pseudocode)
4. Running `/system-design` in a project WITHOUT `.guardkit/graphiti.yaml`
5. Confirming the "Graphiti unavailable" fallback is triggered correctly

## Risks

- **Installed copy sync**: Changes to `installer/core/commands/*.md` need to be re-installed to `~/.agentecflow/commands/` (via `guardkit init` or manual copy)
- **Seeding API compatibility**: `guardkit graphiti add-context` may not support all entity types that `SystemDesignGraphiti.upsert_*` methods handle — verify CLI capabilities
- **PATH for graphiti-check**: The Tier 2 check (CLI) requires `~/.agentecflow/bin/graphiti-check` to be accessible — use absolute path in instructions
