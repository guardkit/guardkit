---
complexity: 4
conductor_workspace: graphiti-enhancements-wave1-4
created_at: 2026-01-29 00:00:00+00:00
dependencies: []
estimated_minutes: 90
feature_id: FEAT-GE
id: TASK-GE-007
implementation_mode: task-work
parent_review: TASK-REV-7549
priority: 1
status: design_approved
tags:
- graphiti
- adr
- seeding
- critical-path
task_type: feature
title: Immediate ADR Seeding (FB-001/002/003)
wave: 1
---

# TASK-GE-007: Immediate ADR Seeding (FB-001/002/003)

## Overview

**Priority**: Critical (Immediate value)
**Dependencies**: None (uses existing Graphiti infrastructure)

## Problem Statement

From TASK-REV-7549 analysis: Three critical architecture decisions were repeatedly violated because they weren't captured in Graphiti:

1. **ADR-FB-001**: Use SDK query(), not subprocess
2. **ADR-FB-002**: Use FEAT-XXX paths, not TASK-XXX
3. **ADR-FB-003**: Pre-loop must invoke real task-work

These three decisions alone could have prevented 60% of the documented failures.

## Goals

1. Create ADR entities for FB-001, FB-002, and FB-003
2. Seed them into Graphiti with full context
3. Include violation symptoms for detection
4. Link to related failure patterns

## Technical Approach

### ADR Content

```python
# guardkit/knowledge/seed_feature_build_adrs.py

from datetime import datetime

FEATURE_BUILD_ADRS = [
    {
        "id": "ADR-FB-001",
        "title": "Use SDK query() for task-work invocation, NOT subprocess",
        "status": "ACCEPTED",
        "context": "feature-build needs to invoke task-work for each task in a feature",
        "decision": "Use Claude Agents SDK query() method to invoke '/task-work TASK-XXX' as a subagent",
        "rationale": [
            "task-work is a Claude Code slash command, not a CLI command",
            "Subagents share context window efficiently",
            "No CLI parsing overhead",
            "Native async/await flow",
            "Better error handling with structured responses"
        ],
        "rejected_alternatives": [
            "subprocess.run('guardkit task-work ...')",
            "os.system() calls",
            "Direct function calls (breaks agent isolation)"
        ],
        "violation_symptoms": [
            "subprocess.CalledProcessError",
            "Command 'guardkit task-work' not found",
            "No module named guardkit.commands.task_work"
        ],
        "related_failures": ["FAIL-SUBPROCESS"],
        "decided_at": "2025-01-15T00:00:00Z",
        "decided_by": "feature-build development",
        "group_id": "architecture_decisions"
    },

    {
        "id": "ADR-FB-002",
        "title": "In feature mode, paths use FEAT-XXX worktree ID, NOT individual TASK-XXX IDs",
        "status": "ACCEPTED",
        "context": "feature-build uses a single worktree for all tasks in a feature",
        "decision": "Construct all worktree paths using FEAT-XXX ID: .guardkit/worktrees/FEAT-XXX/",
        "rationale": [
            "Feature worktree is shared across all tasks",
            "TASK-XXX IDs are for task management, not filesystem",
            "Results and plans are organized by task ID WITHIN feature worktree",
            "Prevents path collision between tasks"
        ],
        "rejected_alternatives": [
            "Separate worktree per task (.guardkit/worktrees/TASK-XXX/)",
            "Nested worktrees",
            "Dynamic path construction"
        ],
        "violation_symptoms": [
            "FileNotFoundError at .guardkit/worktrees/TASK-XXX/",
            "Directory not found: TASK-",
            "No such file or directory: .guardkit/worktrees/TASK"
        ],
        "related_failures": ["FAIL-TASK-PATH"],
        "decided_at": "2025-01-15T00:00:00Z",
        "decided_by": "feature-build development",
        "group_id": "architecture_decisions"
    },

    {
        "id": "ADR-FB-003",
        "title": "Pre-loop phase MUST invoke /task-work --design-only, NOT return mock data",
        "status": "ACCEPTED",
        "context": "Before Player-Coach loop, task needs implementation plan and complexity assessment",
        "decision": "Pre-loop invokes SDK query('/task-work TASK-XXX --design-only') to generate real plan",
        "rationale": [
            "Implementation plan must exist for Player to read",
            "Complexity assessment affects quality gate thresholds",
            "Real invocation ensures consistent format",
            "Plan stored at .claude/task-plans/TASK-XXX-implementation-plan.md"
        ],
        "rejected_alternatives": [
            "Stub implementation returning hardcoded values",
            "Skipping pre-loop entirely",
            "Generating plan within orchestrator"
        ],
        "violation_symptoms": [
            "Implementation plan not found at .claude/task-plans/",
            "Pre-loop returns suspiciously round numbers (complexity=5, arch_score=80)",
            "Player fails with 'no implementation plan'"
        ],
        "related_failures": ["FAIL-MOCK-PRELOOP"],
        "decided_at": "2025-01-15T00:00:00Z",
        "decided_by": "feature-build development",
        "group_id": "architecture_decisions"
    }
]


async def seed_feature_build_adrs(graphiti):
    """Seed critical feature-build ADRs into Graphiti."""

    for adr in FEATURE_BUILD_ADRS:
        await graphiti.add_episode(
            name=f"adr_{adr['id'].lower().replace('-', '_')}",
            episode_body=json.dumps({
                "entity_type": "architecture_decision",
                **adr
            }),
            group_id=adr['group_id']
        )

    print(f"Seeded {len(FEATURE_BUILD_ADRS)} feature-build ADRs")
```

### CLI Command

```python
# Add to guardkit/cli.py

@graphiti_group.command("seed-adrs")
@click.option("--force", is_flag=True, help="Force re-seed even if already done")
def seed_adrs(force: bool):
    """Seed critical feature-build ADRs into Graphiti."""

    async def _seed():
        await init_graphiti()
        graphiti = get_graphiti()

        if not graphiti.enabled:
            click.echo("Graphiti not enabled")
            return

        await seed_feature_build_adrs(graphiti)
        click.echo("Feature-build ADRs seeded successfully")

    asyncio.run(_seed())
```

### Integration with Context Loading

```python
# Ensure ADRs appear in pre-feature-build context

async def load_critical_adrs(context: str = "feature-build") -> List[dict]:
    """Load critical ADRs for context."""

    graphiti = get_graphiti()
    if not graphiti.enabled:
        return []

    results = await graphiti.search(
        query=f"architecture_decision {context}",
        group_ids=["architecture_decisions"],
        num_results=10
    )

    return [
        {
            "id": r['body'].get('id'),
            "title": r['body'].get('title'),
            "decision": r['body'].get('decision'),
            "violation_symptoms": r['body'].get('violation_symptoms', [])
        }
        for r in results
    ]
```

## Acceptance Criteria

- [ ] ADR-FB-001, ADR-FB-002, ADR-FB-003 defined with full context
- [ ] All three ADRs seeded into Graphiti
- [ ] Violation symptoms included for detection
- [ ] Related failure patterns linked
- [ ] CLI command `guardkit graphiti seed-adrs` works
- [ ] ADRs appear in pre-feature-build context loading
- [ ] Unit tests for ADR content and seeding

## Files to Create/Modify

### New Files
- `guardkit/knowledge/seed_feature_build_adrs.py`
- `tests/knowledge/test_feature_build_adrs.py`

### Modified Files
- `guardkit/cli.py` (add seed-adrs command)
- `guardkit/knowledge/context_loader.py` (add ADR loading)

## Testing Strategy

1. **Unit tests**: Verify ADR content is complete and valid
2. **Integration test**: Seed ADRs, query for violation symptoms
3. **E2E test**: Run feature-build, verify ADRs appear in context