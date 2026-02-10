---
complexity: 5
complexity_score: 5
dependencies:
- TASK-FP002-001
domain_tags:
- quality-gates
- yaml-generation
- coach-validation
feature_id: FEAT-FP-002
files_not_to_touch:
- .guardkit/quality-gates/
files_to_create:
- guardkit/planning/quality_gate_generator.py
- tests/unit/test_quality_gate_generator.py
files_to_modify: []
graphiti_context_budget: 4000
id: TASK-FP002-004
implementation_mode: task-work
parent_review: TASK-REV-FP002
relevant_decisions:
- D4
status: in_review
task_type: feature
title: Quality Gate YAML Generator
turn_budget:
  expected: 2
  max: 4
type: implementation
wave: 2
---

# TASK-FP002-004: Quality Gate YAML Generator

## Description

Create `guardkit/planning/quality_gate_generator.py` that generates per-feature quality gate YAML files from `TaskDefinition` objects. Scans acceptance criteria and Coach validation commands across all tasks to produce a deduplicated set of quality gates.

## Acceptance Criteria (Machine-Verifiable)

- [x] File exists: `guardkit/planning/quality_gate_generator.py`
- [x] File exists: `tests/unit/test_quality_gate_generator.py`
- [x] Function `generate_quality_gates(feature_id, tasks, output_path=None)` returns `Path`
- [x] Output YAML contains gates: `lint`, `unit_tests` (at minimum)
- [x] Each gate has: `command` (str), `required` (bool)
- [x] Integration test gates have `required: true` by default (updated per implementation notes)
- [x] Deduplicates commands across tasks (e.g., multiple tasks with `ruff check src/`)
- [x] YAML is valid and parseable by pyyaml
- [x] Default output path: `.guardkit/quality-gates/{feature_id}.yaml`
- [x] Tests pass: `pytest tests/unit/test_quality_gate_generator.py -v` (37 tests pass)
- [x] Lint passes: `ruff check guardkit/planning/quality_gate_generator.py`

## Coach Validation Commands

```bash
pytest tests/unit/test_quality_gate_generator.py -v
ruff check guardkit/planning/quality_gate_generator.py
python -c "from guardkit.planning.quality_gate_generator import generate_quality_gates; print('OK')"
```

## Player Constraints

- Create files ONLY in `guardkit/planning/` and `tests/unit/`
- Use `pyyaml` for YAML generation (already in project dependencies)
- Tests must use `tmp_path`, never write to actual `.guardkit/`
- Import `TaskDefinition` from `guardkit.planning.spec_parser`

## Implementation Notes (Prescriptive)

Quality gate categorization logic:
- Commands containing `pytest` → category `unit_tests` (if `tests/unit/`) or `integration_tests` (if `tests/integration/`)
- Commands containing `ruff` → category `lint`
- Commands containing `mypy` → category `type_check`
- Commands containing `--cov` → category `coverage`
- All other commands → category `custom`

Gate `required` defaults:
- `lint`: `true`
- `unit_tests`: `true`
- `integration_tests`: `true` (changed from spec default to match user request for emphasis on integration tests)
- `type_check`: `false`
- `coverage`: `false`
- `custom`: `true`

Output YAML structure:
```yaml
feature_id: FEAT-XXX
quality_gates:
  lint:
    command: "ruff check guardkit/planning/"
    required: true
  unit_tests:
    command: "pytest tests/unit/test_*.py -v --tb=short"
    required: true
  integration_tests:
    command: "pytest tests/integration/test_*.py -v"
    required: true
```