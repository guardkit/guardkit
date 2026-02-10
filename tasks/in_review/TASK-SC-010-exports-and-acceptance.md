---
complexity: 3
created: 2026-02-10 11:20:00+00:00
dependencies:
- TASK-SC-001
- TASK-SC-002
- TASK-SC-003
- TASK-SC-004
- TASK-SC-008
- TASK-SC-009
feature_id: FEAT-SC-001
id: TASK-SC-010
implementation_mode: task-work
parent_review: TASK-REV-AEA7
priority: high
status: in_review
tags:
- exports
- acceptance
- finalization
task_type: feature
title: Update __init__.py exports + final acceptance test sweep
updated: 2026-02-10T14:20:00+00:00
wave: 4
implementation_completed: 2026-02-10T14:20:00+00:00
tests_passed: true
quality_gates:
  compilation: pass
  tests_passing: true
  coverage_met: true
  code_review: approved
---

# Task: Update __init__.py exports + final acceptance test sweep

## Description

Final integration task that:
1. Updates `guardkit/planning/__init__.py` to export new modules
2. Runs a comprehensive acceptance test sweep to verify all 33 acceptance criteria from FEAT-SC-001

## Key Implementation Details

### Part 1: Update __init__.py

Update `guardkit/planning/__init__.py` to add new exports:

```python
from guardkit.planning.system_overview import (
    get_system_overview,
    condense_for_injection,
    format_overview_display,
)

from guardkit.planning.impact_analysis import (
    run_impact_analysis,
    condense_impact_for_injection,
    format_impact_display,
)

from guardkit.planning.context_switch import (
    GuardKitConfig,
    execute_context_switch,
)

from guardkit.planning.coach_context_builder import (
    build_coach_context,
)

__all__ = [
    # Existing exports
    'ARCHITECTURE_CONTEXT_THRESHOLD',
    'ARCH_TOKEN_BUDGETS',
    'get_arch_token_budget',
    'SystemPlanGraphiti',
    'mode_detector',
    # New exports (FEAT-SC-001)
    'get_system_overview',
    'condense_for_injection',
    'format_overview_display',
    'run_impact_analysis',
    'condense_impact_for_injection',
    'format_impact_display',
    'GuardKitConfig',
    'execute_context_switch',
    'build_coach_context',
]
```

### Part 2: Acceptance Test Sweep

Create `tests/acceptance/test_feat_sc_001_acceptance.py` that verifies all 33 acceptance criteria from the feature spec:

#### /system-overview (9 criteria)
- [ ] Condensed summary fits ~40-60 lines
- [ ] --verbose shows extended output
- [ ] --section filter works
- [ ] --format=json returns structured data
- [ ] Shows methodology, components, ADRs, concerns, stack
- [ ] Shows "last updated" timestamp
- [ ] condense_for_injection within budget
- [ ] No context → helpful suggestion
- [ ] Graphiti down → fallback guidance

#### /impact-analysis (10 criteria)
- [ ] Accepts task IDs and topics
- [ ] Task ID reads task file for enriched query
- [ ] Quick depth: components + risk in <5s
- [ ] Standard depth: + ADRs + implications
- [ ] Deep depth: + BDD + related tasks
- [ ] Risk score 1-5 calculated correctly
- [ ] Decision checkpoint works
- [ ] [P]roceed passes context
- [ ] No context → graceful handling
- [ ] Missing BDD → degrades to standard

#### /context-switch (8 criteria)
- [ ] Switches active project in config
- [ ] Orientation summary displayed
- [ ] --list shows all projects
- [ ] No-args shows current
- [ ] Does NOT change cwd/git/files
- [ ] Unknown project → helpful error
- [ ] Works when Graphiti down
- [ ] Updates last_accessed

#### AutoBuild Integration (4 criteria)
- [ ] Coach receives context for complexity >= 4
- [ ] Context within token budget
- [ ] No context for complexity 1-3
- [ ] Task-work suggestion for complexity >= 7

### Implementation

Each acceptance test should be a simple assertion that calls the actual function and verifies the documented behavior. Use mocked Graphiti where needed.

## Acceptance Criteria

- [ ] `guardkit/planning/__init__.py` exports all new modules
- [ ] All new functions importable via `from guardkit.planning import ...`
- [ ] Acceptance test file covers all 33 criteria from feature spec
- [ ] All unit tests pass: `pytest tests/unit/planning/ -v`
- [ ] All integration tests pass: `pytest tests/integration/ -v`
- [ ] All E2E tests pass: `pytest tests/e2e/ -v`
- [ ] All acceptance tests pass: `pytest tests/acceptance/ -v`
- [ ] No regressions in existing tests

## Test Requirements

Run full test suite:
```bash
pytest tests/unit/planning/ tests/integration/ tests/e2e/ tests/acceptance/ -v --tb=short
```

## Implementation Notes

- This is the final task — all dependencies must be complete
- __init__.py changes are simple (just add imports and exports)
- Acceptance tests can reuse fixtures from integration tests
- If `tests/acceptance/` doesn't exist, create it
- Keep acceptance tests lightweight — they verify behavior, not exhaustive edge cases