---
complexity: 4
conductor_workspace: gr-mvp-wave7-seeding
created: 2026-01-30 00:00:00+00:00
depends_on:
- TASK-GR-001-D
- TASK-GR-001-E
- TASK-GR-001-F
- TASK-GR-001-G
feature_id: FEAT-GR-MVP
id: TASK-GR-001-H
implementation_mode: task-work
parent_review: TASK-REV-1505
priority: high
status: in_review
tags:
- graphiti
- project-seeding
- init
- mvp-phase-2
task_type: feature
title: Add project seeding to guardkit init
updated: 2026-02-01 00:00:00+00:00
wave: 7
---

# Task: Add project seeding to guardkit init

## Description

Integrate Graphiti project seeding into the `guardkit init` command so that project knowledge is automatically seeded when a new project is initialized.

## Acceptance Criteria

- [x] `guardkit init` seeds project knowledge to Graphiti
- [x] Seeds: project overview (from CLAUDE.md/README.md)
- [x] Seeds: role constraints (defaults)
- [x] Seeds: quality gate configs (defaults)
- [x] Seeds: implementation modes (defaults)
- [x] Graceful degradation if Graphiti unavailable
- [x] --skip-graphiti flag to skip seeding

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

### Files Modified

- `guardkit/cli/init.py` - New CLI command with --skip-graphiti flag
- `guardkit/cli/main.py` - Registered init command
- `guardkit/knowledge/project_seeding.py` - Project seeding orchestrator

## Test Requirements

- [x] Integration test for init with Graphiti
- [x] Test --skip-graphiti flag
- [x] Test graceful degradation

## Implementation Summary

**Files Created:**
- `guardkit/cli/init.py` (181 lines) - Click CLI command
- `guardkit/knowledge/project_seeding.py` (367 lines) - Seeding orchestrator
- `tests/cli/test_init.py` (443 lines, 17 tests) - Comprehensive test suite

**Files Modified:**
- `guardkit/cli/main.py` - Added init command registration

**Test Results:** 44/44 tests passed (17 new + 27 existing CLI tests)

**Code Review:** Approved (91/100 SOLID, 92/100 Code Quality)

## Notes

Core integration point - connects init workflow to Graphiti.

## References

- [FEAT-GR-001 Design](../../../../docs/research/graphiti-refinement/FEAT-GR-001-project-knowledge-seeding.md)
