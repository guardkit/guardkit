# Implementation Guide: Seed Feature-Spec & Coach Updates (FEAT-SFC)

**Parent Review**: TASK-REV-5FA4
**Feature ID**: FEAT-SFC
**Total Tasks**: 6
**Estimated Effort**: ~4-5 hours (all changes)

## Problem Statement

The Graphiti seed function has significant gaps: the `/feature-spec` command is completely absent, and the Coach's new capabilities (Promise Verification, Honesty Verification, `criteria_verification`) are not reflected in any seed module. The Assumptions Manifest workflow is not captured anywhere. This means any Graphiti-powered context retrieval for these features returns no results.

## Solution Approach

Update 6 existing seed modules to add the missing `/feature-spec` command episode, update Coach-related episodes with new verification capabilities, and add the Assumptions Manifest pipeline as a new episode. Bump the seeding version to trigger re-seed.

## Execution Strategy

### Wave 1: Core Changes (3 tasks, parallel-safe)

These tasks modify different files with no overlapping changes:

| Task | File(s) | Description | Mode |
|------|---------|-------------|------|
| TASK-SFC-001 | `seed_command_workflows.py` | Add `/feature-spec` episode, update workflow episodes | task-work |
| TASK-SFC-002 | `seed_feature_build_architecture.py` | Update Coach episode, add Assumptions Manifest episode | task-work |
| TASK-SFC-003 | `seed_agents.py`, `seed_patterns.py` | Update Coach capabilities and Player-Coach pattern | task-work |

**Parallel execution recommended** — no file conflicts between Wave 1 tasks.

### Wave 2: Supplementary Changes (3 tasks, parallel-safe)

| Task | File(s) | Description | Mode | Dependencies |
|------|---------|-------------|------|--------------|
| TASK-SFC-004 | `seed_integration_points.py` | Add feature-spec integration point | task-work | SFC-001 |
| TASK-SFC-005 | `facts/role_constraint.py` | Update COACH_CONSTRAINTS must_do list | task-work | SFC-002 |
| TASK-SFC-006 | `seed_helpers.py` | Bump SEEDING_VERSION | task-work | All Wave 1+2 |

**Note**: TASK-SFC-006 should be the last task executed, after all other changes are merged.

## Validation

After all tasks complete:

```bash
# Lint all modified files
ruff check guardkit/knowledge/seed_command_workflows.py \
          guardkit/knowledge/seed_feature_build_architecture.py \
          guardkit/knowledge/seed_agents.py \
          guardkit/knowledge/seed_patterns.py \
          guardkit/knowledge/seed_integration_points.py \
          guardkit/knowledge/facts/role_constraint.py \
          guardkit/knowledge/seed_helpers.py

# Run seed-related tests
pytest tests/ -k "seed" -v

# Verify seeding works end-to-end (if Graphiti available)
guardkit graphiti seed --force
guardkit graphiti verify --verbose
```

## Sources of Truth

| Topic | File |
|-------|------|
| `/feature-spec` command definition | `installer/core/commands/feature-spec.md` |
| `/feature-spec` feature research | `docs/research/feature-spec/FEATURE-SPEC-feature-spec-command-v2.md` |
| `/feature-spec` user docs | `docs/commands/feature-spec.md` |
| Coach agent definition | `.claude/agents/autobuild-coach.md` |
| Review report | `.claude/reviews/TASK-REV-5FA4-review-report.md` |
