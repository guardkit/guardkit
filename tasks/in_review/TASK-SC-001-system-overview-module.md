---
complexity: 5
created: 2026-02-10 11:20:00+00:00
dependencies: []
feature_id: FEAT-SC-001
id: TASK-SC-001
implementation_mode: task-work
parent_review: TASK-REV-AEA7
priority: high
status: in_review
tags:
- system-overview
- graphiti
- planning
task_type: feature
title: Implement system_overview.py module
updated: 2026-02-10T13:30:00+00:00
wave: 1
implementation:
  mode: tdd
  tests_passed: 44
  tests_total: 44
  line_coverage: 90.73
  branch_coverage: 80.00
  code_quality_score: 92
  files_created:
    - guardkit/planning/system_overview.py
  files_modified:
    - guardkit/planning/__init__.py
  test_files:
    - tests/unit/planning/test_system_overview.py
---

# Task: Implement system_overview.py module

## Description

Create `guardkit/planning/system_overview.py` with the core system overview assembly and condensation logic. This module consumes `SystemPlanGraphiti.get_architecture_summary()` and transforms the raw Graphiti facts into structured sections (components, decisions, concerns, system context).

## Key Implementation Details

### Functions to Implement

1. **`get_system_overview(sp: SystemPlanGraphiti, verbose: bool = False) -> dict`**
   - Calls `sp.get_architecture_summary()` to get raw facts
   - Parses facts into structured sections using `_extract_entity_type()`
   - Returns dict with status, system, components, decisions, concerns
   - Returns `{"status": "no_context"}` when no facts found

2. **`_extract_entity_type(fact: dict) -> str`**
   - Infers entity type from fact name prefix and content keywords
   - Patterns: "Component:" prefix → component, "ADR-" prefix → architecture_decision
   - Keywords: "cross-cutting", "concern" → crosscutting_concern
   - Returns one of: "component", "architecture_decision", "crosscutting_concern", "system_context"

3. **`_parse_component_fact(fact, verbose) -> dict`**
   - Extract name, description from fact text
   - Verbose mode includes full content

4. **`_parse_decision_fact(fact, verbose) -> dict`**
   - Extract ADR ID, title, status (active/superseded)
   - Verbose mode includes context and consequences

5. **`_parse_concern_fact(fact, verbose) -> dict`**
   - Extract concern name and description

6. **`condense_for_injection(overview: dict, max_tokens: int = 800) -> str`**
   - Priority order: methodology + component names → ADR titles → concern names → descriptions
   - Stop when budget exhausted
   - Returns token-budgeted string

7. **`_estimate_tokens(text: str) -> int`**
   - Simple heuristic: `len(text.split()) * 1.3` (words to tokens)

8. **`format_overview_display(overview: dict, section: str = "all", format: str = "display") -> str`**
   - Terminal display format (~40-60 lines default)
   - Markdown format (raw)
   - JSON format (structured)
   - Section filter: components, decisions, crosscutting, stack, all

### Integration Points

- **Input**: `SystemPlanGraphiti` (from `guardkit/planning/graphiti_arch.py`)
- **Output**: Structured dict consumed by display layer and `condense_for_injection()`
- **Dependency**: `graphiti_arch.py` read operations (already exist)

### Graphiti Fact Format (from search results)

Each fact is a dict with: `uuid`, `fact` (text), `name`, `created_at`, `valid_at`, `score`
Entity type is NOT a field — must be inferred from name/content.

## Acceptance Criteria

- [x] `get_system_overview()` assembles structured dict from Graphiti facts
- [x] `_extract_entity_type()` correctly classifies components, decisions, concerns, system context
- [x] `condense_for_injection()` respects token budget with priority ordering
- [x] `format_overview_display()` supports display/markdown/json formats
- [x] Section filtering works for all sections
- [x] Returns `{"status": "no_context"}` when no architecture data exists
- [x] Returns `{"status": "no_context"}` when Graphiti unavailable
- [x] All functions have unit tests with >=80% line coverage (achieved: 90.73%)

## Test Requirements

### Unit Tests (tests/unit/planning/test_system_overview.py)

- `test_get_system_overview_full` — all fact types present
- `test_get_system_overview_no_context` — empty/None summary
- `test_get_system_overview_graphiti_unavailable` — sp._available is False
- `test_extract_entity_type_component` — "Component: X" prefix
- `test_extract_entity_type_adr` — "ADR-001" prefix
- `test_extract_entity_type_concern` — "cross-cutting" keyword
- `test_extract_entity_type_system_context` — "System Context" prefix
- `test_extract_entity_type_unknown` — fallback behavior
- `test_condense_for_injection_within_budget` — output under max_tokens
- `test_condense_for_injection_priority_order` — components before descriptions
- `test_condense_for_injection_empty_overview` — no data returns empty string
- `test_format_display_default` — terminal format
- `test_format_display_json` — structured JSON output
- `test_format_display_section_filter` — single section
- `test_estimate_tokens` — token count heuristic

## Implementation Notes

- Follow `graphiti_arch.py` patterns (graceful degradation, `[Graphiti]` log prefix)
- Use `logging.getLogger(__name__)` for structured logging
- All async functions should handle exceptions with try/except and return defaults