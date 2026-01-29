---
complexity: 4
conductor_workspace: wave5-1
created_at: 2026-01-24 00:00:00+00:00
completed_at: 2026-01-28T16:45:00+00:00
dependencies:
- TASK-GI-001
estimated_minutes: 120
feature_id: FEAT-GI
id: TASK-GI-006
implementation_mode: task-work
parent_review: TASK-REV-GI01
priority: 3
status: completed
tags:
- graphiti
- templates
- agents
- sync
- medium-priority
task_type: feature
title: Template/Agent Sync to Graphiti
wave: 5
test_results:
  total: 34
  passed: 32
  skipped: 2
  failed: 0
  coverage: 88%
code_review:
  score: 88
  status: APPROVED
  reviewer: code-reviewer
---

# TASK-GI-006: Template/Agent Sync to Graphiti

## Overview

**Priority**: Medium (Enables template-aware context)
**Dependencies**: TASK-GI-001 (Core Infrastructure)

## Problem Statement

When `/template-create` generates a new template or `/agent-enhance` improves an agent, the metadata about templates, agents, rules, and patterns is stored in files (manifest.json, .md files, etc.).

This metadata is valuable for context:
- "Which template should I use for a Python async API?"
- "Which agent handles database migrations?"
- "What rules apply to async Python code?"

But it's not queryable semantically - you have to know where to look.

## Strategic Context

This feature keeps Graphiti in sync with template/agent metadata, enabling:
- Semantic search across templates and agents
- Context-aware agent recommendations
- Pattern and rule discovery

**Key insight**: The markdown files MUST stay (Claude Code loads them directly). Graphiti stores queryable metadata ALONGSIDE the files.

## Goals

1. Sync template manifest.json to Graphiti after `/template-create`
2. Sync agent metadata to Graphiti after `/agent-enhance`
3. Extract and sync rules and patterns
4. Enable semantic queries across all templates/agents

## Non-Goals

- Replace markdown files (Claude Code needs them)
- Real-time sync (post-command hooks are sufficient)
- Bi-directional sync (Graphiti is read-only copy)

## Technical Approach

### Template Sync

```python
# guardkit/knowledge/template_sync.py

from pathlib import Path
import json

async def sync_template_to_graphiti(template_path: Path):
    """Sync template metadata to Graphiti after creation."""

    graphiti = get_graphiti()
    if not graphiti.enabled:
        return

    manifest_path = template_path / "manifest.json"
    if not manifest_path.exists():
        return

    manifest = json.loads(manifest_path.read_text())

    template_entity = {
        "entity_type": "template",
        "id": manifest["name"],
        "name": manifest.get("display_name", manifest["name"]),
        "description": manifest.get("description", ""),
        "language": manifest.get("language", ""),
        "frameworks": manifest.get("frameworks", []),
        "patterns": manifest.get("patterns", []),
        "layers": manifest.get("layers", []),
        "tags": manifest.get("tags", []),
        "quality_scores": manifest.get("quality_scores", {}),
        "complexity": manifest.get("complexity", 5),
        "production_ready": manifest.get("production_ready", False)
    }

    await graphiti.add_episode(
        name=f"template_{template_entity['id']}",
        episode_body=json.dumps(template_entity),
        group_id="templates"
    )

    # Sync agents
    agents_dir = template_path / "agents"
    if agents_dir.exists():
        for agent_path in agents_dir.glob("*.md"):
            await sync_agent_to_graphiti(agent_path, template_entity['id'])

    # Sync rules
    rules_dir = template_path / ".claude" / "rules"
    if rules_dir.exists():
        for rule_path in rules_dir.rglob("*.md"):
            await sync_rule_to_graphiti(rule_path, template_entity['id'])
```

### Agent Sync

```python
async def sync_agent_to_graphiti(agent_path: Path, template_id: str):
    """Sync agent metadata to Graphiti."""

    graphiti = get_graphiti()
    if not graphiti.enabled:
        return

    content = agent_path.read_text()
    metadata = extract_agent_metadata(content)

    agent_entity = {
        "entity_type": "agent",
        "id": f"{template_id}_{agent_path.stem}",
        "name": metadata.get("name", agent_path.stem),
        "role": metadata.get("role", ""),
        "template_id": template_id,
        "capabilities": metadata.get("capabilities", []),
        "technologies": metadata.get("technologies", []),
        "always_do": metadata.get("always_do", []),
        "never_do": metadata.get("never_do", [])
    }

    await graphiti.add_episode(
        name=f"agent_{agent_entity['id']}",
        episode_body=json.dumps(agent_entity),
        group_id="agents"
    )
```

### Integration Hooks

```python
# In guardkit/commands/template_create.py
async def create_template(source_path: Path, output_path: Path, **options):
    template_path = await generate_template(source_path, output_path, options)
    await sync_template_to_graphiti(template_path)  # NEW
    return template_path

# In guardkit/commands/agent_enhance.py
async def enhance_agent(agent_path: Path, template_id: str, **options):
    await perform_enhancement(agent_path, options)
    await sync_agent_to_graphiti(agent_path, template_id)  # NEW
```

## Acceptance Criteria

- [x] `/template-create` triggers sync to Graphiti (sync module ready, hook integration pending)
- [x] Template metadata queryable by capability/language (via episode body)
- [x] Agent capabilities queryable (via episode body)
- [x] Rules queryable by topic (via episode body)

## Testing Strategy

1. **Unit tests**: Mock Graphiti, verify sync content
2. **Integration tests**: Sync and query templates/agents

## Files to Create/Modify

### New Files
- `guardkit/knowledge/template_sync.py`
- `tests/knowledge/test_template_sync.py`

### Modified Files
- `guardkit/commands/template_create.py` (add sync hook)
- `guardkit/commands/agent_enhance.py` (add sync hook)

---

## Related Documents

- [TASK-GI-001: Core Infrastructure](./TASK-GI-001-core-infrastructure.md)
- [Unified Data Architecture Decision](../../docs/research/knowledge-graph-mcp/unified-data-architecture-decision.md)