---
id: TASK-TI-012
title: GOAL.md domain configuration with evaluation criteria schema
status: backlog
created: 2026-03-27T22:00:00Z
updated: 2026-03-27T22:00:00Z
priority: p3
tags: [template, adversarial, domain-config]
complexity: 5
parent_review: TASK-REV-TRF12
feature_id: FEAT-TI
wave: 4
implementation_mode: task-work
depends_on: [TASK-TI-005, TASK-TI-009]
test_results:
  status: pending
  coverage: null
  last_run: null
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

- [ ] GOAL.md template with metadata schema, evaluation criteria, and quality thresholds
- [ ] Parser handles enum, range, and array field types
- [ ] Evaluation criteria weights validated (sum to 1.0)
- [ ] Coach prompt section auto-generated from criteria
- [ ] Regression tests: range notation `1+` and `1-5` parsed correctly
- [ ] Regression test: array field validated with set membership

## Effort Estimate

1-2 days
