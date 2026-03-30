---
id: TASK-TI-012
title: GOAL.md domain configuration with evaluation criteria schema
status: completed
created: 2026-03-27T22:00:00Z
updated: 2026-03-29T00:00:00Z
completed: 2026-03-29T00:00:00Z
completed_location: tasks/completed/TASK-TI-012/
priority: p3
tags: [template, adversarial, domain-config]
complexity: 5
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: [TASK-TI-005, TASK-TI-009]
previous_state: in_review
state_transition_reason: "All acceptance criteria met, 110/110 tests passing"
test_results:
  status: passed
  total: 110
  passed: 110
  failed: 0
  coverage: null
  last_run: 2026-03-29T00:00:00Z
organized_files:
  - TASK-TI-012.md
---

# Task: GOAL.md Domain Configuration with Evaluation Criteria Schema

## Description

Create the GOAL.md-equivalent domain configuration system for the adversarial template. This defines what the Player generates, what the Coach evaluates against, and how metadata fields are validated — incorporating all lessons from the domain parser bugs (TRF-004, TRF-028).

## What to Build

### 1. GOAL.md Template
```markdown
# Domain: {{domain_name}}

## Generation Target
{{description of what the Player should generate}}

## Metadata Schema
| Field | Type | Valid Values | Required | Description |
|-------|------|-------------|----------|-------------|
| topic | string | enum: [list] | yes | ... |
| difficulty | integer | range: 1-5 | yes | ... |
| tags | array | enum: [list] | no | ... |
| turns | integer | range: 1+ | yes | ... |

## Evaluation Criteria
| Criterion | Weight | Description | Score Range |
|-----------|--------|-------------|-------------|
| accuracy | 0.3 | Factual correctness | 1-5 |
| pedagogy | 0.3 | Teaching effectiveness | 1-5 |
| format | 0.2 | Structural compliance | 1-5 |
| engagement | 0.2 | Student engagement | 1-5 |

## Quality Thresholds
- minimum_weighted_score: 3.5
- required_fields: [topic, difficulty]
- format_requirements: [think_blocks, json_structure]
```

### 2. Schema Parser
- Parse metadata fields with type awareness (string, integer, array)
- Distinguish enum vs range valid_values (TRF-028 lesson)
- Parse evaluation criteria with weights (must sum to 1.0)
- Parse quality thresholds for Coach verdict logic

### 3. Evaluation Criteria Injection
- Generate Coach prompt section from criteria table
- Include weights, descriptions, and score ranges
- Generate acceptance threshold logic

## Acceptance Criteria

- [x] GOAL.md template with metadata schema, evaluation criteria, and quality thresholds
- [x] Parser handles enum, range, and array field types
- [x] Evaluation criteria weights validated (sum to 1.0)
- [x] Coach prompt section auto-generated from criteria
- [x] Regression tests: range notation `1+` and `1-5` parsed correctly
- [x] Regression test: array field validated with set membership

## Effort Estimate

1-2 days

## Implementation Summary

### Files Created/Modified

| File | Action | Description |
|------|--------|-------------|
| `installer/core/templates/langchain-deepagents-weighted-evaluation/scaffold/goal_schema.py.j2` | Modified | Added MetadataFieldSchema, QualityThresholds, parse_goal_md(), build_coach_criteria_section() |
| `installer/core/templates/langchain-deepagents-weighted-evaluation/templates/goal.md.j2` | Created | Jinja2 GOAL.md template with 4 sections |
| `installer/core/templates/langchain-deepagents-weighted-evaluation/tests/test_goal_schema.py` | Created | 39 tests across 11 classes |

### Key Additions

- **MetadataFieldSchema** dataclass — parsed metadata field definitions from GOAL.md tables
- **QualityThresholds** dataclass — minimum_weighted_score, required_fields, format_requirements
- **parse_goal_md()** — full GOAL.md markdown → GoalSchema round-trip parser
- **build_coach_criteria_section()** — generates Coach prompt with score ranges + thresholds
- **EvaluationCriterion.score_range** — new field (default "0.0-1.0")
- **_parse_markdown_table()** — generic markdown table parser for reuse
- **_parse_list_value()** — bracket/bare comma list parser

### Regression Coverage

- TRF-028: Range notation `1-5` and `1+` parsed correctly (2 dedicated tests)
- FRF-002: Array field type mapped correctly (1 dedicated test)
- Backward compatibility: All 71 existing scaffold tests still pass
