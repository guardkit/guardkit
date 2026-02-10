# FEAT-SC-001: System Context Read Commands

Three read-only commands that consume architecture knowledge from `/system-plan`, plus AutoBuild coach integration.

## Commands

| Command | Purpose | Complexity |
|---------|---------|------------|
| `/system-overview` | Condensed architecture summary (one-screen) | Read-only |
| `/impact-analysis` | Pre-task validation against architecture | Read + risk scoring |
| `/context-switch` | Multi-project navigation | Config + Graphiti |

## Tasks (12 tasks, 5 waves)

### Wave 1 — Foundation (parallel)
- **TASK-SC-001**: system_overview.py module (complexity: 5)
- **TASK-SC-002**: context_switch.py + bdd_scenarios group (complexity: 5)

### Wave 2 — Core Commands (parallel)
- **TASK-SC-003**: impact_analysis.py module (complexity: 6)
- **TASK-SC-004**: coach_context_builder.py module (complexity: 4)
- **TASK-SC-005**: Command markdown specs (3 commands) (complexity: 4)

### Wave 3 — Integration Tests (parallel)
- **TASK-SC-006**: Integration tests: Graphiti seams (complexity: 6)
- **TASK-SC-007**: Integration tests: config + coach (complexity: 5)

### Wave 4 — E2E + Docs + Integration (parallel)
- **TASK-SC-008**: E2E tests: CLI commands (complexity: 5)
- **TASK-SC-009**: Wire coach integration + task-work preflight (complexity: 5)
- **TASK-SC-011**: Docs site guides for 3 commands (complexity: 4)

### Wave 5 — Finalization (parallel)
- **TASK-SC-010**: Exports + acceptance test sweep (complexity: 3)
- **TASK-SC-012**: Update mkdocs.yml nav + CLAUDE.md references (complexity: 2)

## Feature Spec

`docs/research/system-level-understanding/FEAT-SC-001-system-context-read-commands.md`

## Review Task

`TASK-REV-AEA7`
