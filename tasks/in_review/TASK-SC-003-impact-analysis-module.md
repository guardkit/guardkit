---
complexity: 6
created: 2026-02-10 11:20:00+00:00
dependencies:
- TASK-SC-001
- TASK-SC-002
feature_id: FEAT-SC-001
id: TASK-SC-003
implementation_mode: task-work
parent_review: TASK-REV-AEA7
priority: high
status: in_review
tags:
- impact-analysis
- risk-scoring
- graphiti
task_type: feature
title: Implement impact_analysis.py module
updated: 2026-02-10T14:30:00+00:00
wave: 2
implementation:
  mode: tdd
  tests_passed: 30
  tests_total: 30
  line_coverage: 89.31
  branch_coverage: 75.74
  code_review_score: 94.3
  files_created:
    - guardkit/planning/impact_analysis.py
    - tests/unit/planning/test_impact_analysis.py
---

# Task: Implement impact_analysis.py module

## Description

Create `guardkit/planning/impact_analysis.py` with the impact analysis engine, risk scoring, and multi-depth query logic. This is the most complex module in FEAT-SC-001 due to multi-group Graphiti queries and heuristic risk calculation.

## Key Implementation Details

### Functions to Implement

1. **`run_impact_analysis(sp, client, task_or_topic, depth, include_bdd, include_tasks) -> dict`**
   - Build query from task ID or topic string
   - Query `project_architecture` for affected components
   - Query `project_decisions` for constraining ADRs (via ADRService)
   - Optionally query `bdd_scenarios` (deep mode)
   - Optionally query `feature_specs` for related tasks (deep mode)
   - Calculate risk score
   - Return structured results dict

2. **`_build_query(task_or_topic: str) -> str`**
   - If input matches `TASK-[A-Z0-9-]+` pattern, read task file for title + description
   - Otherwise use topic string directly
   - Enrich with tags if available from task frontmatter

3. **`_calculate_risk(components, adrs, bdd_scenarios) -> dict`**
   - Base score: 1.0
   - +0.5 per affected component beyond first (threshold: score > 0.5)
   - +1.0 per ADR conflict, +0.25 per informational ADR
   - +0.3 per at-risk BDD scenario
   - Clamp to 1-5, round to nearest int
   - Return: `{"score": int, "label": str, "rationale": str}`

4. **`_parse_component_hits(hits) -> list`**
   - Heuristic extraction from Graphiti search fact strings
   - Extract component name, description, relevance score

5. **`_parse_adr_hits(hits) -> list`**
   - Extract ADR ID, title, conflict indicator
   - "conflict" inferred from keywords: "conflicts with", "violates", "superseded by"

6. **`_parse_bdd_hits(hits) -> list`**
   - Extract scenario name, file location, risk indicator

7. **`_derive_implications(component_hits, adr_hits) -> list`**
   - Generate human-readable architectural implication strings

8. **`condense_impact_for_injection(impact: dict, max_tokens: int = 1200) -> str`**
   - Token-budgeted condensation for coach injection
   - Priority: risk score → affected components → ADR constraints

9. **`format_impact_display(impact: dict, depth: str) -> str`**
   - Terminal display with risk bar, sections per depth tier

### Depth Tiers

| Depth | Queries | ~Time |
|-------|---------|-------|
| quick | Components only | ~5s |
| standard | Components + ADRs + implications | ~10s |
| deep | All + BDD + related tasks | ~20s |

### BDD Graceful Degradation

When `bdd_scenarios` group is empty or search returns no results:
- Deep mode silently falls back (no BDD section in output)
- Log: `[Graphiti] No BDD scenarios found, skipping BDD impact section`

## Acceptance Criteria

- [x] Accepts both task IDs (`TASK-XXX`) and free-text topic descriptions
- [x] Task ID mode reads task file for enriched semantic queries
- [x] Quick depth returns components and risk score
- [x] Standard depth includes ADR constraints and implications
- [x] Deep depth includes BDD scenarios and related tasks
- [x] Risk score (1-5) calculated correctly from heuristic
- [x] BDD group missing/empty degrades gracefully to standard
- [x] `condense_impact_for_injection()` respects token budget
- [x] All parse functions handle malformed/empty Graphiti results
- [x] Unit tests with >=80% line coverage (achieved: 89.31%)

## Test Requirements

### Unit Tests (tests/unit/planning/test_impact_analysis.py)

- `test_run_impact_analysis_standard` — mock Graphiti, verify components + ADRs
- `test_run_impact_analysis_quick` — only components queried
- `test_run_impact_analysis_deep_with_bdd` — all groups queried
- `test_run_impact_analysis_deep_no_bdd` — graceful degradation
- `test_calculate_risk_low` — 1 component, no ADR conflicts → 1
- `test_calculate_risk_medium` — 2 components, 1 ADR → 3
- `test_calculate_risk_high` — 3+ components, ADR conflicts, BDD → 5
- `test_calculate_risk_clamping` — extreme values clamp to 1-5
- `test_build_query_from_task_id` — reads task file, extracts query
- `test_build_query_from_topic` — uses topic string directly
- `test_build_query_invalid_task_id` — task file not found, falls back to ID
- `test_parse_component_hits` — heuristic extraction
- `test_parse_adr_hits_conflict` — conflict keyword detection
- `test_parse_adr_hits_informational` — no conflict keywords
- `test_parse_bdd_hits` — scenario extraction
- `test_missing_bdd_group_degrades` — empty results, no error
- `test_condense_impact_within_budget` — token budget respected
- `test_condense_impact_empty` — no data returns empty string
- `test_format_impact_display_standard` — terminal format
- `test_format_impact_display_quick` — abbreviated format

## Implementation Notes

- `ADRService` uses `search_adrs()` which searches "adrs" group (system scope)
- For project-scoped ADR search, use `client.search()` with `project_decisions` group directly
- The spec shows using both `ADRService` and direct `client.search()` — prefer direct search against `project_decisions` group for consistency with `SystemPlanGraphiti`
- Task file reading is sync — use `Path(task_file).read_text()` with error handling