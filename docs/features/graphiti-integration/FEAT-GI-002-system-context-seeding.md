# FEAT-GI-002: System Context Seeding

## Overview

**Feature ID**: FEAT-GI-002
**Title**: System Context Seeding
**Priority**: Critical (Required for session context to work)
**Estimated Complexity**: Medium
**Dependencies**: FEAT-GI-001 (Graphiti Core Infrastructure)

## Problem Statement

Claude Code sessions working on GuardKit don't know:
- What GuardKit IS (a quality gate system, not just task management)
- How commands flow together (`/feature-plan` → `/feature-build` → `/task-work`)
- The 5-phase quality gate structure
- Technology decisions (SDK query() not subprocess, worktrees for isolation)
- What's been tried and failed

This causes sessions to make locally-optimal decisions that conflict with overall system design.

## Strategic Context

This feature seeds the "big picture" knowledge that prevents the context loss problem. Once seeded, this knowledge is available for all future sessions to query.

**Key insight**: This is a ONE-TIME operation per Graphiti instance. The seeded knowledge provides the foundation that session context loading (FEAT-GI-003) draws from.

## Goals

1. Seed comprehensive GuardKit system knowledge into Graphiti
2. Organize knowledge into queryable group IDs
3. Provide a CLI command to run/re-run seeding
4. Verify seeding with test queries

## Non-Goals

- Dynamic knowledge updates (that's Episode Capture - FEAT-GI-005)
- User-specific knowledge (this is system-wide)
- External documentation ingestion

## Knowledge Categories to Seed

### Group IDs and Content

| Group ID | Episodes | Content |
|----------|----------|---------|
| `product_knowledge` | 3 | What GuardKit is, philosophy, value prop |
| `command_workflows` | 7 | How commands flow together |
| `quality_gate_phases` | 12 | Full 5-phase structure (1→2→2.5→3→4→4.5→5→5.5) |
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
    
    print("✓ System context seeding complete")
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
        },
        {
            "name": "guardkit_philosophy",
            "body": {
                "entity_type": "philosophy",
                "principles": [
                    "Quality First: Never auto-merge, always human review",
                    "Pragmatic Approach: Start with working code, refactor later",
                    "Zero Ceremony: Minimal process overhead",
                    "Trust But Verify: AI proposes, gates verify, humans approve"
                ]
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
                ],
                "consequences": [
                    "task-work must be invocable as SDK agent",
                    "Cannot use CLI-only features from feature-build"
                ]
            },
            "group_id": "architecture_decisions"
        },
        {
            "name": "decision_worktree_paths",
            "body": {
                "entity_type": "architecture_decision",
                "id": "ADR-002",
                "title": "Use FEAT-XXX worktree paths in feature-build, not TASK-XXX",
                "status": "ACCEPTED",
                "context": "feature-build orchestrates multiple tasks in sequence",
                "decision": "All tasks in a feature-build share the feature worktree (FEAT-XXX)",
                "rationale": [
                    "Tasks build on each other's work",
                    "Single worktree for entire feature",
                    "Simpler merge at end"
                ],
                "rejected_alternatives": [
                    "Separate TASK-XXX worktree per task",
                    "Working in main branch"
                ]
            },
            "group_id": "architecture_decisions"
        }
    ]
```

### CLI Command

```python
# guardkit/commands/graphiti_seed.py

@click.command()
@click.option('--force', is_flag=True, help='Re-seed even if already seeded')
async def seed(force: bool):
    """Seed Graphiti with GuardKit system context."""
    
    # Check if already seeded
    if not force:
        marker = await graphiti.search(
            query="guardkit_seeding_complete",
            group_ids=["system"],
            num_results=1
        )
        if marker:
            click.echo("Already seeded. Use --force to re-seed.")
            return
    
    await seed_all_system_context()
    
    # Add seeding marker
    await graphiti.add_episode(
        name="guardkit_seeding_complete",
        episode_body=json.dumps({
            "seeded_at": datetime.now().isoformat(),
            "version": "1.0.0"
        }),
        group_id="system"
    )
    
    click.echo("✓ Seeding complete")
```

### Verification Queries

```python
async def verify_seeding():
    """Verify seeding with test queries."""
    
    tests = [
        {
            "query": "What is GuardKit?",
            "group_ids": ["product_knowledge"],
            "expected_contains": "quality gate"
        },
        {
            "query": "How should feature-build invoke task-work?",
            "group_ids": ["architecture_decisions"],
            "expected_contains": "SDK query()"
        },
        {
            "query": "What happens in Phase 2.8?",
            "group_ids": ["quality_gate_phases"],
            "expected_contains": "human approval"
        }
    ]
    
    for test in tests:
        results = await graphiti.search(
            query=test["query"],
            group_ids=test["group_ids"],
            num_results=3
        )
        # Verify expected content in results
```

## Acceptance Criteria

1. **Seeding completes successfully**
   - `guardkit graphiti seed` runs without errors
   - All ~67 episodes are created
   - Seeding marker is set

2. **Knowledge is queryable**
   - "What is GuardKit?" returns product knowledge
   - "How to invoke task-work?" returns SDK decision
   - "What are the quality phases?" returns phase structure

3. **Idempotent seeding**
   - Running seed twice doesn't create duplicates
   - `--force` flag allows re-seeding

4. **Template/Agent/Pattern knowledge included**
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
- [Graphiti System Context Seeding](../../research/knowledge-graph-mcp/graphiti-system-context-seeding.md)

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

- [Graphiti System Context Seeding](../../research/knowledge-graph-mcp/graphiti-system-context-seeding.md) - Full episode definitions
- [Unified Data Architecture Decision](../../research/knowledge-graph-mcp/unified-data-architecture-decision.md) - Strategic context
- [FEAT-GI-001: Core Infrastructure](./FEAT-GI-001-core-infrastructure.md) - Dependency
