---
id: TASK-GR-001-H
title: Add project seeding to guardkit init
status: in_review
created: 2026-01-30 00:00:00+00:00
updated: 2026-01-30 00:00:00+00:00
priority: high
tags:
- graphiti
- project-seeding
- init
- mvp-phase-2
task_type: feature
parent_review: TASK-REV-1505
feature_id: FEAT-GR-MVP
implementation_mode: task-work
wave: 7
conductor_workspace: gr-mvp-wave7-seeding
complexity: 4
depends_on:
- TASK-GR-001-D
- TASK-GR-001-E
- TASK-GR-001-F
- TASK-GR-001-G
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GR-MVP
  base_branch: main
  started_at: '2026-02-01T07:39:45.504172'
  last_updated: '2026-02-01T07:51:53.903866'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-01T07:39:45.504172'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Task: Add project seeding to guardkit init

## Description

Integrate Graphiti project seeding into the `guardkit init` command so that project knowledge is automatically seeded when a new project is initialized.

## Acceptance Criteria

- [ ] `guardkit init` seeds project knowledge to Graphiti
- [ ] Seeds: project overview (from CLAUDE.md/README.md)
- [ ] Seeds: role constraints (defaults)
- [ ] Seeds: quality gate configs (defaults)
- [ ] Seeds: implementation modes (defaults)
- [ ] Graceful degradation if Graphiti unavailable
- [ ] --skip-graphiti flag to skip seeding

## Implementation Notes

### Init Flow Integration

```python
async def init_project(
    template: str,
    project_name: str,
    skip_graphiti: bool = False,
    **kwargs
) -> InitResult:
    """Initialize project with template and Graphiti seeding."""

    # 1. Existing init logic (templates, files)
    result = await init_template(template, project_name, **kwargs)

    # 2. Graphiti seeding (new)
    if not skip_graphiti:
        try:
            await seed_project_knowledge(project_name)
        except GraphitiUnavailable:
            logger.warning("Graphiti unavailable, skipping knowledge seeding")

    return result


async def seed_project_knowledge(project_name: str) -> SeedResult:
    """Seed all project knowledge to Graphiti."""

    client = GraphitiClient(project_id=project_name)

    # 1. Parse project docs
    parser = ProjectDocParser()
    doc_content = Path("CLAUDE.md").read_text() if Path("CLAUDE.md").exists() else Path("README.md").read_text()
    parse_result = parser.parse(doc_content)

    # 2. Seed project overview
    overview = ProjectOverviewEpisode(
        project_name=project_name,
        purpose=parse_result.purpose,
        ...
    )
    await client.upsert_episode(
        overview.to_episode_content(),
        "project_overview",
        entity_id=overview.get_entity_id()
    )

    # 3. Seed role constraints (system-level)
    for constraint in [PLAYER_CONSTRAINTS, COACH_CONSTRAINTS]:
        await client.upsert_episode(
            constraint.to_episode_content(),
            "role_constraints",
            entity_id=constraint.get_entity_id(),
            scope="system"
        )

    # 4. Seed quality gate configs (system-level)
    for task_type, config in QUALITY_GATE_DEFAULTS.items():
        await client.upsert_episode(
            config.to_episode_content(),
            "quality_gate_configs",
            entity_id=config.get_entity_id(),
            scope="system"
        )

    # 5. Seed implementation modes (system-level)
    for mode, mode_config in IMPLEMENTATION_MODE_DEFAULTS.items():
        await client.upsert_episode(
            mode_config.to_episode_content(),
            "implementation_modes",
            entity_id=mode_config.get_entity_id(),
            scope="system"
        )

    return SeedResult(success=True)
```

### Files to Modify

- `src/guardkit/cli/commands/init.py` - Add Graphiti seeding

## Test Requirements

- [ ] Integration test for init with Graphiti
- [ ] Test --skip-graphiti flag
- [ ] Test graceful degradation

## Notes

Core integration point - connects init workflow to Graphiti.

## References

- [FEAT-GR-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-001-project-knowledge-seeding.md)
