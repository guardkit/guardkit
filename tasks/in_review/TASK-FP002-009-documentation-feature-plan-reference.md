---
complexity: 3
complexity_score: 3
dependencies:
- TASK-FP002-007
domain_tags:
- documentation
- command-reference
- feature-plan
feature_id: FEAT-FP-002
files_not_to_touch:
- guardkit/
- tests/
- .claude/commands/
files_to_create:
- docs/reference/feature-plan.md
files_to_modify: []
graphiti_context_budget: 2000
id: TASK-FP002-009
implementation_mode: task-work
parent_review: TASK-REV-FP002
relevant_decisions:
- D1
- D8
- D9
status: in_review
task_type: documentation
title: 'Documentation: Updated Feature-Plan Reference'
turn_budget:
  expected: 1
  max: 3
type: documentation
wave: 4
---

# TASK-FP002-009: Documentation — Updated Feature-Plan Reference

## Description

Create the command reference page for `/feature-plan` documenting all flags (existing + new), output formats, and usage examples. This serves as the canonical reference for the command's behavior.

## Acceptance Criteria (Machine-Verifiable)

- [x] File exists: `docs/reference/feature-plan.md`
- [x] Documents all flags: `--from-spec`, `--target`, `--generate-adrs`, `--generate-quality-gates`
- [x] Documents existing flags: `--context`, `--no-questions`, `--with-questions`, `--defaults`, `--answers`, `--no-structured`
- [x] Includes usage examples for each new flag
- [x] Includes output format description for both `interactive` and `local-model` targets
- [x] Includes table of task metadata fields produced in `local-model` mode

## Coach Validation Commands

```bash
python -c "
from pathlib import Path
content = Path('docs/reference/feature-plan.md').read_text()
for flag in ['--from-spec', '--target', '--generate-adrs', '--generate-quality-gates']:
    assert flag in content, f'Missing flag: {flag}'
print('Reference doc validation OK')
"
```

## Player Constraints

- Create ONLY `docs/reference/feature-plan.md`
- Follow existing command reference page patterns if available
- Use MkDocs-compatible formatting
- Do NOT create or modify any code files