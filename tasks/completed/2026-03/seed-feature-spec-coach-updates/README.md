# Seed Feature-Spec & Coach Updates (FEAT-SFC)

Update Graphiti seed modules to reflect the new `/feature-spec` command and Coach's Promise/Honesty Verification capabilities.

## Origin

Review: TASK-REV-5FA4 (architectural review, comprehensive depth)
Score: 58/100 (below 60-point threshold)
Findings: 12 (4 CRITICAL, 3 HIGH, 3 MEDIUM, 2 LOW)

## Tasks

| ID | Title | Wave | Priority | Complexity | Status |
|----|-------|------|----------|------------|--------|
| TASK-SFC-001 | Add /feature-spec episode to seed_command_workflows.py | 1 | High | 3 | Backlog |
| TASK-SFC-002 | Update seed_feature_build_architecture.py with Coach changes | 1 | High | 3 | Backlog |
| TASK-SFC-003 | Update seed_agents.py and seed_patterns.py | 1 | High | 2 | Backlog |
| TASK-SFC-004 | Add feature-spec integration point | 2 | Medium | 2 | Backlog |
| TASK-SFC-005 | Update COACH_CONSTRAINTS fact | 2 | Medium | 1 | Backlog |
| TASK-SFC-006 | Bump SEEDING_VERSION | 2 | Medium | 1 | Backlog |

## Quick Start

```bash
# Wave 1 (parallel — different files)
/task-work TASK-SFC-001
/task-work TASK-SFC-002
/task-work TASK-SFC-003

# Wave 2 (after Wave 1 complete)
/task-work TASK-SFC-004
/task-work TASK-SFC-005
/task-work TASK-SFC-006  # last — bumps version
```
