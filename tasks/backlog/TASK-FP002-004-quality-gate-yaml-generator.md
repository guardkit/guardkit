---
id: TASK-FP002-004
title: Quality Gate YAML Generator
task_type: feature
parent_review: TASK-REV-FP002
feature_id: FEAT-FP-002
wave: 2
implementation_mode: task-work
complexity: 5
complexity_score: 5
type: implementation
domain_tags:
  - quality-gates
  - yaml-generation
  - coach-validation
files_to_create:
  - guardkit/planning/quality_gate_generator.py
  - tests/unit/test_quality_gate_generator.py
files_to_modify: []
files_not_to_touch:
  - .guardkit/quality-gates/
dependencies:
  - TASK-FP002-001
relevant_decisions:
  - D4
turn_budget:
  expected: 2
  max: 4
graphiti_context_budget: 4000
---

# TASK-FP002-004: Quality Gate YAML Generator

## Description

Create `guardkit/planning/quality_gate_generator.py` that generates per-feature quality gate YAML files from `TaskDefinition` objects. Scans acceptance criteria and Coach validation commands across all tasks to produce a deduplicated set of quality gates.

## Acceptance Criteria (Machine-Verifiable)

- [ ] File exists: `guardkit/planning/quality_gate_generator.py`
- [ ] File exists: `tests/unit/test_quality_gate_generator.py`
- [ ] Function `generate_quality_gates(feature_id, tasks, output_path=None)` returns `Path`
- [ ] Output YAML contains gates: `lint`, `unit_tests` (at minimum)
- [ ] Each gate has: `command` (str), `required` (bool)
- [ ] Integration test gates have `required: false` by default
- [ ] Deduplicates commands across tasks (e.g., multiple tasks with `ruff check src/`)
- [ ] YAML is valid and parseable by pyyaml
- [ ] Default output path: `.guardkit/quality-gates/{feature_id}.yaml`
- [ ] Tests pass: `pytest tests/unit/test_quality_gate_generator.py -v`
- [ ] Lint passes: `ruff check guardkit/planning/quality_gate_generator.py`

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
