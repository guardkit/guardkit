---
id: TASK-GI-002
title: System Context Seeding
status: backlog
priority: 1
task_type: feature
created_at: 2026-01-24T00:00:00Z
parent_review: TASK-REV-GI01
feature_id: FEAT-GI
implementation_mode: task-work
wave: 2
conductor_workspace: wave2-1
complexity: 6
estimated_minutes: 240
dependencies:
  - TASK-GI-001
tags:
  - graphiti
  - seeding
  - knowledge-base
  - critical-path
---

# TASK-GI-002: System Context Seeding

## Overview

**Priority**: Critical (Required for session context to work)
**Dependencies**: TASK-GI-001 (Graphiti Core Infrastructure)

## Problem Statement

Claude Code sessions working on GuardKit don't know:
- What GuardKit IS (a quality gate system, not just task management)
- How commands flow together (`/feature-plan` -> `/feature-build` -> `/task-work`)
- The 5-phase quality gate structure
- Technology decisions (SDK query() not subprocess, worktrees for isolation)
- What's been tried and failed

This causes sessions to make locally-optimal decisions that conflict with overall system design.

## Strategic Context

This feature seeds the "big picture" knowledge that prevents the context loss problem. Once seeded, this knowledge is available for all future sessions to query.

**Key insight**: This is a ONE-TIME operation per Graphiti instance. The seeded knowledge provides the foundation that session context loading (TASK-GI-003) draws from.

## Goals

1. Seed comprehensive GuardKit system knowledge into Graphiti
2. Organize knowledge into queryable group IDs
3. Provide a CLI command to run/re-run seeding
4. Verify seeding with test queries

## Non-Goals

- Dynamic knowledge updates (that's Episode Capture - TASK-GI-005)
- User-specific knowledge (this is system-wide)
- External documentation ingestion

## Knowledge Categories to Seed

### Group IDs and Content

| Group ID | Episodes | Content |
|----------|----------|---------|
| `product_knowledge` | 3 | What GuardKit is, philosophy, value prop |
| `command_workflows` | 7 | How commands flow together |
| `quality_gate_phases` | 12 | Full 5-phase structure (1->2->2.5->3->4->4.5->5->5.5) |
| `technology_stack` | 7 | Python CLI, SDK, subagents, worktrees |
| `feature_build_architecture` | 7 | Player-Coach pattern, delegation, file locations |
| `architecture_decisions` | 3 | Key decisions (SDK vs subprocess, paths, etc.) |
| `failure_patterns` | 4 | Known failures and how to fix them |
| `component_status` | 2 | What's incomplete |
| `integration_points` | 2 | How components connect |
| `templates` | 4+ | Template metadata |
| `agents` | 7+ | Agent capabilities and boundaries |
| `patterns` | 5+ | Design pattern knowledge |
| `rules` | 4+ | Rule applicability and examples |

**Total: ~67+ episodes**

## Technical Approach

### Seeding Script Structure

```python
# guardkit/knowledge/seed_system_context.py

async def seed_all_system_context():
    """Seed all system context into Graphiti."""

    await init_graphiti()
    graphiti = get_graphiti()

    if not graphiti.enabled:
        print("Graphiti not enabled, skipping seeding")
        return

    print("Seeding GuardKit system context...")

    # Core system context
    await seed_product_knowledge(graphiti)
    await seed_command_workflows(graphiti)
    await seed_quality_gate_phases(graphiti)
    await seed_technology_stack(graphiti)
    await seed_feature_build_architecture(graphiti)
    await seed_known_issues(graphiti)

    # Template, agent, pattern, and rule knowledge
    await seed_template_knowledge(graphiti)
    await seed_agent_knowledge(graphiti)
    await seed_pattern_knowledge(graphiti)
    await seed_rule_knowledge(graphiti)

    print("System context seeding complete")
```

### Example Episode Content

```python
async def seed_product_knowledge(graphiti):
    """Seed what GuardKit IS."""

    episodes = [
        {
            "name": "guardkit_identity",
            "body": {
                "entity_type": "product",
                "name": "GuardKit",
                "tagline": "AI-powered development workflow with quality gates",
                "what_it_is": "A quality gate system that wraps AI coding assistants with mandatory checkpoints to prevent broken code from being committed",
                "what_it_is_not": [
                    "NOT just a task management system",
                    "NOT a replacement for human code review",
                    "NOT an autonomous coding bot"
                ],
                "core_value": "AI handles the implementation, humans make approval decisions at gates"
            },
            "group_id": "product_knowledge"
        }
    ]

    for ep in episodes:
        await graphiti.add_episode(
            name=ep["name"],
            episode_body=json.dumps(ep["body"]),
            group_id=ep["group_id"]
        )
```

### Critical Knowledge: Architecture Decisions

```python
async def seed_architecture_decisions(graphiti):
    """Seed CRITICAL decisions that sessions MUST know."""

    episodes = [
        {
            "name": "decision_sdk_not_subprocess",
            "body": {
                "entity_type": "architecture_decision",
                "id": "ADR-001",
                "title": "Use SDK query() for task-work invocation, NOT subprocess",
                "status": "ACCEPTED",
                "context": "feature-build needs to invoke task-work for each task",
                "decision": "Use Claude Agents SDK query() method to invoke task-work as a subagent",
                "rationale": [
                    "Subagents share context window efficiently",
                    "No CLI parsing overhead",
                    "Native async/await flow",
                    "Better error handling"
                ],
                "rejected_alternatives": [
                    "subprocess.run('guardkit task-work ...')",
                    "os.system() calls",
                    "Direct function calls (breaks agent isolation)"
                ]
            },
            "group_id": "architecture_decisions"
        }
    ]
```

## Acceptance Criteria

- [ ] **Seeding completes successfully**
  - `guardkit graphiti seed` runs without errors
  - All ~67 episodes are created
  - Seeding marker is set

- [ ] **Knowledge is queryable**
  - "What is GuardKit?" returns product knowledge
  - "How to invoke task-work?" returns SDK decision
  - "What are the quality phases?" returns phase structure

- [ ] **Idempotent seeding**
  - Running seed twice doesn't create duplicates
  - `--force` flag allows re-seeding

- [ ] **Template/Agent/Pattern knowledge included**
  - Template metadata queryable
  - Agent capabilities queryable
  - Pattern definitions queryable

## Testing Strategy

1. **Unit tests**: Mock Graphiti, verify episode content
2. **Integration tests**: Real Graphiti, verify queries return expected results
3. **Verification script**: Run after seeding to confirm all knowledge accessible

## Files to Create/Modify

### New Files
- `guardkit/knowledge/seed_system_context.py`
- `guardkit/knowledge/seed_templates.py`
- `guardkit/knowledge/seed_agents.py`
- `guardkit/knowledge/seed_patterns.py`
- `guardkit/knowledge/seed_rules.py`
- `guardkit/commands/graphiti_seed.py`
- `tests/knowledge/test_seeding.py`

### Modified Files
- `guardkit/cli.py` (add `graphiti seed` command)

## Content Source

The episode content is defined in detail in:
- [Graphiti System Context Seeding](../../docs/research/knowledge-graph-mcp/graphiti-system-context-seeding.md)

This document contains the full seeding script with all ~67 episodes.

## Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Episode content becomes outdated | Version the seeding, re-seed when GuardKit changes |
| Too much knowledge overwhelms queries | Use group_ids to scope queries |
| Missing critical knowledge | Verification queries catch gaps |

## Open Questions

1. Should seeding auto-run on first Graphiti connection?
2. How do we version the seeded knowledge for updates?
3. Should we support incremental seeding (add new episodes without re-seeding all)?

---

## Related Documents

- [Graphiti System Context Seeding](../../docs/research/knowledge-graph-mcp/graphiti-system-context-seeding.md) - Full episode definitions
- [Unified Data Architecture Decision](../../docs/research/knowledge-graph-mcp/unified-data-architecture-decision.md) - Strategic context
- [TASK-GI-001: Core Infrastructure](./TASK-GI-001-core-infrastructure.md) - Dependency
