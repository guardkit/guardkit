# FEAT-INFRA: Infrastructure-Aware AutoBuild

**Parent Review**: TASK-REV-BA4B
**Problem**: AutoBuild stalls on tasks requiring external infrastructure (PostgreSQL, Redis) because the Coach's independent test verification always fails in the SDK subprocess environment.

## Solution: Two-Layer Strategy

1. **Primary (Docker Test Fixtures)**: Both Player and Coach spin up Docker containers as test fixtures when `requires_infrastructure` is declared. Tests run against real infrastructure.

2. **Fallback (Conditional Approval)**: When Docker is unavailable, the Coach conditionally approves if the failure is high-confidence infrastructure and the task explicitly declares its dependencies.

## Tasks

| Wave | Task | Description | Complexity | Depends On |
|------|------|-------------|-----------|------------|
| 1 | TASK-INFR-6D4F | `requires_infrastructure` field + propagation | 3 | -- |
| 1 | TASK-INFR-1670 | Tiered classification patterns + precedence rule | 3 | -- |
| 2 | TASK-INFR-5922 | Docker test fixtures (primary path) | 4 | TASK-INFR-6D4F |
| 2 | TASK-INFR-24DB | Conditional approval fallback | 4 | TASK-INFR-6D4F, TASK-INFR-1670 |

## Execution Strategy

**Wave 1** (parallel): TASK-INFR-6D4F + TASK-INFR-1670 -- no dependencies between them
**Wave 2** (parallel): TASK-INFR-5922 + TASK-INFR-24DB -- both depend on Wave 1

## Key Design Decisions

- **`requires_infrastructure` lives in both** feature YAML and task frontmatter, with frontmatter taking precedence
- **Classification has two tiers**: high-confidence (connection errors) and ambiguous (import errors); only high-confidence qualifies for conditional approval
- **Docker is the primary path** because it actually tests against real infrastructure; conditional approval is the fallback
- **Dual-signal safety** for conditional approval: declared (YAML) + detected (runtime) must agree
