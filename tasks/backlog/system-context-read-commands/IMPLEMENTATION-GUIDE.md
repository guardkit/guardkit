# Implementation Guide: FEAT-SC-001 System Context Read Commands

## Architecture Overview

```
guardkit/planning/
├── __init__.py                    # MODIFIED: Add new exports
├── complexity_gating.py           # EXISTING: get_arch_token_budget() (no changes)
├── graphiti_arch.py               # EXISTING: SystemPlanGraphiti (no changes)
├── system_overview.py             # NEW: Overview assembly + condensation
├── impact_analysis.py             # NEW: Risk scoring + multi-depth queries
├── context_switch.py              # NEW: Config management + project switching
└── coach_context_builder.py       # NEW: Budget-gated coach prompt assembly

guardkit/knowledge/
└── graphiti_client.py             # MODIFIED: Add bdd_scenarios to PROJECT_GROUP_NAMES

guardkit/orchestrator/quality_gates/
└── coach_validator.py             # MODIFIED: Add architecture context injection

.claude/commands/                   # NEW: 3 command specs
installer/core/commands/            # NEW: 3 command specs (same content)

docs/guides/                        # NEW: 3 user-facing guides
mkdocs.yml                          # MODIFIED: Add nav entries
CLAUDE.md                           # MODIFIED: Add command references
```

## Dependency Graph

```
TASK-SC-001 (system_overview.py) ──┐
                                    ├─→ TASK-SC-003 (impact_analysis.py)
TASK-SC-002 (context_switch.py) ───┤   TASK-SC-004 (coach_context_builder.py)
                                    │   TASK-SC-005 (command specs)
                                    │
                                    ├─→ TASK-SC-006 (integration: Graphiti seams)
                                    │   TASK-SC-007 (integration: config + coach)
                                    │
                                    ├─→ TASK-SC-008 (E2E: CLI commands)
                                    │   TASK-SC-009 (coach wiring + preflight)
                                    │   TASK-SC-011 (docs site guides)
                                    │
                                    └─→ TASK-SC-010 (exports + acceptance)
                                        TASK-SC-012 (mkdocs + CLAUDE.md)
```

## Wave Execution Strategy

### Wave 1: Foundation (2 tasks, parallel)
- No dependencies, can start immediately
- Establishes core data structures and config management
- **File conflicts**: None (different files)

### Wave 2: Core Commands (3 tasks, parallel)
- Depends on Wave 1 completion
- TASK-SC-003 depends on both SC-001 and SC-002 (uses system_overview + bdd group)
- TASK-SC-004 depends on SC-001 only (uses condense_for_injection)
- TASK-SC-005 depends on SC-001 and SC-002 (references Python functions)
- **File conflicts**: None (different files)

### Wave 3: Integration Tests (2 tasks, parallel)
- Depends on Wave 2 for modules to test against
- TASK-SC-006 tests Graphiti seams (overview + impact)
- TASK-SC-007 tests config + coach seams
- **File conflicts**: Shared `tests/conftest.py` for MockGraphitiClient fixture

### Wave 4: E2E + Docs + Integration (3 tasks, parallel)
- TASK-SC-008 depends on Wave 3 (needs working commands)
- TASK-SC-009 depends on SC-004 + SC-006 (coach builder + integration verified)
- TASK-SC-011 depends on SC-005 (needs command specs for reference)
- **File conflicts**: None (different directories)

### Wave 5: Finalization (2 tasks, parallel)
- TASK-SC-010 depends on everything implementation/test (final sweep)
- TASK-SC-012 depends on SC-011 (needs guides created before updating nav)
- **File conflicts**: None (different files)

## Technology Seam Map

| Seam | Modules Involved | Risk | Test Coverage |
|------|-----------------|------|---------------|
| Graphiti search → fact parsing | system_overview.py, impact_analysis.py | HIGH | SC-006 |
| Group ID prefixing | graphiti_client.py, all query modules | MEDIUM | SC-002, SC-006 |
| Config YAML persistence | context_switch.py | MEDIUM | SC-007 |
| Coach prompt assembly | coach_context_builder.py → coach_validator.py | MEDIUM | SC-007, SC-009 |
| CLI command registration | cli/main.py → Click groups | LOW | SC-008 |
| Token budget enforcement | coach_context_builder.py | LOW | SC-004, SC-007 |
| Async propagation | All async modules | LOW | SC-006 |

## Key Patterns to Follow

### Graceful Degradation
All new modules must handle:
- Graphiti unavailable (client.enabled = False)
- No architecture context (empty search results)
- Partial context (some categories missing)
- Exception in any query (catch and log)

### Logging
Use `[Graphiti]` prefix for all Graphiti-related log messages:
```python
logger.info("[Graphiti] Architecture context loaded: %d facts", len(facts))
logger.warning("[Graphiti] Failed to query project_architecture: %s", e)
```

### Token Budget
Reuse `_estimate_tokens()` across modules (simple heuristic: words * 1.3).
Always respect `get_arch_token_budget()` tiers.

## Testing Strategy

| Level | Files | Purpose | Neo4j Required |
|-------|-------|---------|----------------|
| Unit | `tests/unit/planning/test_*.py` | Individual function correctness | No |
| Integration | `tests/integration/test_*.py` | Cross-module seam verification | No |
| E2E | `tests/e2e/test_*.py` | Full CLI command invocation | No |
| Acceptance | `tests/acceptance/test_*.py` | Feature spec criteria verification | No |

All tests use mocked Graphiti — no running Neo4j instance required.
