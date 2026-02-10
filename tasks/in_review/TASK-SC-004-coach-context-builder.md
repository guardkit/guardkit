---
complexity: 4
created: 2026-02-10 11:20:00+00:00
dependencies:
- TASK-SC-001
feature_id: FEAT-SC-001
id: TASK-SC-004
implementation_mode: task-work
parent_review: TASK-REV-AEA7
priority: high
status: in_review
tags:
- coach
- autobuild
- context
- graphiti
task_type: feature
title: Implement coach_context_builder.py module
updated: 2026-02-10T13:45:00+00:00
wave: 2
implementation_complete: true
tests_pass: true
coverage: 80
files_created:
- guardkit/planning/coach_context_builder.py
- tests/unit/planning/test_coach_context_builder.py
---

# Task: Implement coach_context_builder.py module

## Description

Create `guardkit/planning/coach_context_builder.py` with the budget-gated coach prompt assembly function. This module bridges system overview and impact analysis into a single context string for the AutoBuild coach prompt.

## Key Implementation Details

### Functions to Implement

1. **`build_coach_context(task: dict, client: GraphitiClient, project_id: str) -> str`**
   - Get complexity from `task.get("complexity", 5)`
   - Call `get_arch_token_budget(complexity)` for budget
   - If budget == 0, return "" (simple tasks get no architecture context)
   - Create `SystemPlanGraphiti(client, project_id)`
   - Get condensed overview via `condense_for_injection()`
   - If remaining budget > 400, get quick impact analysis via `condense_impact_for_injection()`
   - Return formatted string with "## Architecture Context" and "## Task Impact" sections

2. **`_estimate_tokens(text: str) -> int`**
   - Reuse from `system_overview.py` or shared utility
   - `len(text.split()) * 1.3`

### Complexity Tier Behavior

| Complexity | Budget | Coach Receives |
|------------|--------|----------------|
| 1-3 | 0 | Empty string (no context) |
| 4-6 | 1000 | Condensed overview only |
| 7-8 | 2000 | Overview + quick impact |
| 9-10 | 3000 | Overview + standard impact |

### Graceful Degradation

- Graphiti unavailable → return "" (don't break coach)
- No architecture context → return "" with INFO log
- Impact analysis fails → return overview only with WARNING log

## Acceptance Criteria

- [ ] Returns "" for complexity 1-3 (budget = 0)
- [ ] Returns condensed overview for complexity 4-6
- [ ] Returns overview + impact for complexity 7+
- [ ] Total output respects token budget from `get_arch_token_budget()`
- [ ] Gracefully returns "" when Graphiti unavailable
- [ ] Gracefully returns "" when no architecture context
- [ ] Returns overview-only when impact analysis fails
- [ ] Unit tests with >=80% line coverage

## Test Requirements

### Unit Tests (tests/unit/planning/test_coach_context_builder.py)

- `test_build_coach_context_simple_task` — complexity 2 → empty string
- `test_build_coach_context_medium_complexity` — complexity 5 → overview only
- `test_build_coach_context_high_complexity` — complexity 7 → overview + impact
- `test_build_coach_context_critical_complexity` — complexity 9 → larger budget
- `test_build_coach_context_no_arch` — no architecture → empty string
- `test_build_coach_context_graphiti_unavailable` — client disabled → empty string
- `test_build_coach_context_impact_fails` — impact error → overview only
- `test_build_coach_context_token_budget` — verify output within budget
- `test_build_coach_context_default_complexity` — missing complexity key → default 5

## Implementation Notes

- Import `get_system_overview`, `condense_for_injection` from `system_overview`
- Import `run_impact_analysis`, `condense_impact_for_injection` from `impact_analysis`
- Import `get_arch_token_budget` from `complexity_gating`
- This function is async (calls async Graphiti operations)
- All exceptions caught and logged — never raises to caller