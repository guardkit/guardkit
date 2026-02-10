---
id: TASK-SC-006
title: "Integration tests: Graphiti seams (overview + impact)"
status: backlog
created: 2026-02-10T11:20:00Z
updated: 2026-02-10T11:20:00Z
priority: high
task_type: testing
parent_review: TASK-REV-AEA7
feature_id: FEAT-SC-001
wave: 3
implementation_mode: task-work
complexity: 6
dependencies:
  - TASK-SC-001
  - TASK-SC-003
tags: [integration-tests, graphiti, seams]
---

# Task: Integration tests for Graphiti seams (overview + impact analysis)

## Description

Create integration tests that verify the system_overview and impact_analysis modules work correctly against a mocked but realistic Graphiti client. These tests target the technology seams where GuardKit code interacts with Graphiti's search API — the most common source of errors in past features.

**Why this matters**: Past features (FEAT-6EDD, FEAT-GR-003) showed errors at Graphiti integration points — fact parsing assumptions, group ID prefixing, async context propagation. These tests catch those issues before they reach production.

## Key Implementation Details

### Test Files

1. **`tests/integration/test_system_overview_graphiti.py`**
2. **`tests/integration/test_impact_analysis_graphiti.py`**

### Realistic Graphiti Fixtures

Create fixtures that match actual Graphiti `search()` return format:

```python
@pytest.fixture
def realistic_arch_facts():
    """Facts as returned by GraphitiClient.search() with real data patterns."""
    return [
        {
            "uuid": "fact-001",
            "fact": "Component: Attorney Management handles donor/attorney relationships and LPA lifecycle management",
            "name": "Component: Attorney Management",
            "created_at": "2026-02-07T10:00:00Z",
            "valid_at": "2026-02-07T10:00:00Z",
            "score": 0.92,
        },
        {
            "uuid": "fact-002",
            "fact": "ADR-001: Use anti-corruption layer for Moneyhub API integration to prevent external API changes from propagating into domain model",
            "name": "ADR-001: Anti-corruption layer for Moneyhub",
            "created_at": "2026-02-07T10:00:00Z",
            "valid_at": "2026-02-07T10:00:00Z",
            "score": 0.88,
        },
        {
            "uuid": "fact-003",
            "fact": "Cross-cutting concern: Authentication uses GOV.UK Verify integration with role-based access control",
            "name": "Crosscutting: Authentication",
            "created_at": "2026-02-07T10:00:00Z",
            "valid_at": "2026-02-07T10:00:00Z",
            "score": 0.85,
        },
        {
            "uuid": "fact-004",
            "fact": "System uses Domain-Driven Design methodology with 4 bounded contexts",
            "name": "System Context: Power of Attorney Platform",
            "created_at": "2026-02-07T10:00:00Z",
            "valid_at": "2026-02-07T10:00:00Z",
            "score": 0.95,
        },
    ]
```

### MockGraphitiClient

Create a test-specific mock that accurately simulates `GraphitiClient` behavior:

```python
class MockGraphitiClient:
    """Realistic mock that matches GraphitiClient API surface."""

    def __init__(self, facts=None, enabled=True, project_id="test-project"):
        self._facts = facts or []
        self._enabled = enabled
        self._project_id = project_id

    @property
    def enabled(self):
        return self._enabled

    def get_group_id(self, group_name, scope=None):
        if self._project_id:
            return f"{self._project_id}__{group_name}"
        return group_name

    async def search(self, query, group_ids=None, num_results=10):
        if not self._enabled:
            return []
        # Filter by group_ids if provided
        return self._facts[:num_results]
```

### System Overview Integration Tests

- `test_overview_with_seeded_architecture` — full pipeline: mock client → SystemPlanGraphiti → get_system_overview → verify all sections populated
- `test_overview_empty_project` — no facts → status: "no_context"
- `test_overview_partial_context` — only components, no ADRs → partial display
- `test_overview_condense_roundtrip` — get_system_overview → condense_for_injection → verify within budget
- `test_overview_entity_type_classification` — all 4 entity types correctly classified from realistic facts
- `test_overview_fact_with_unexpected_format` — malformed fact gracefully handled

### Impact Analysis Integration Tests

- `test_impact_with_components_and_adrs` — standard depth, verify components and ADR constraints extracted
- `test_impact_with_bdd_scenarios` — deep depth with BDD facts in mock
- `test_impact_bdd_empty_group` — deep depth, bdd_scenarios returns empty → graceful fallback
- `test_impact_risk_score_calculation` — realistic facts → verify risk score matches heuristic
- `test_impact_task_id_query_enrichment` — task ID → task file read → enriched query string
- `test_impact_condense_roundtrip` — run_impact_analysis → condense_impact_for_injection → verify budget
- `test_impact_multiple_group_queries` — verify correct group IDs used for each query stage
- `test_impact_adr_conflict_detection` — facts with "conflicts with" keyword → conflict=True

### Seam-Specific Tests

These target the exact boundaries where errors have historically occurred:

- `test_group_id_prefixing_consistency` — verify all queries use correctly prefixed group IDs
- `test_search_result_format_handling` — verify _parse_* functions handle actual search() return format
- `test_async_context_propagation` — verify async calls through SystemPlanGraphiti don't lose context
- `test_graphiti_disabled_returns_defaults` — client.enabled=False → all functions return safe defaults

## Acceptance Criteria

- [ ] 2 integration test files created
- [ ] At least 8 system overview integration tests
- [ ] At least 10 impact analysis integration tests
- [ ] Realistic Graphiti fact fixtures matching actual search() format
- [ ] MockGraphitiClient accurately simulates API surface
- [ ] Seam-specific tests cover group ID prefixing, search format, async propagation
- [ ] All tests pass with `pytest tests/integration/ -v`
- [ ] No dependency on running Neo4j (all mocked)

## Test Requirements

This IS the test task. Verify tests pass:
```bash
pytest tests/integration/test_system_overview_graphiti.py tests/integration/test_impact_analysis_graphiti.py -v
```

## Implementation Notes

- Use `pytest.mark.asyncio` for async tests
- Use `AsyncMock` from `unittest.mock` for async method mocking where needed
- Follow existing integration test patterns in `tests/integration/`
- Fixtures should be in conftest.py or inline with tests
- Do NOT require a running Neo4j instance — all Graphiti interactions are mocked
