---
id: TASK-FP002-009
title: "Documentation: Updated Feature-Plan Reference"
task_type: documentation
parent_review: TASK-REV-FP002
feature_id: FEAT-FP-002
wave: 4
implementation_mode: task-work
complexity: 3
complexity_score: 3
type: documentation
domain_tags:
  - documentation
  - command-reference
  - feature-plan
files_to_create:
  - docs/reference/feature-plan.md
files_to_modify: []
files_not_to_touch:
  - guardkit/
  - tests/
  - .claude/commands/
dependencies:
  - TASK-FP002-007
relevant_decisions:
  - D1
  - D8
  - D9
turn_budget:
  expected: 1
  max: 3
graphiti_context_budget: 2000
---

# TASK-FP002-009: Documentation — Updated Feature-Plan Reference

## Description

Create the command reference page for `/feature-plan` documenting all flags (existing + new), output formats, and usage examples. This serves as the canonical reference for the command's behavior.

## Acceptance Criteria (Machine-Verifiable)

- [ ] File exists: `docs/reference/feature-plan.md`
- [ ] Documents all flags: `--from-spec`, `--target`, `--generate-adrs`, `--generate-quality-gates`
- [ ] Documents existing flags: `--context`, `--no-questions`, `--with-questions`, `--defaults`, `--answers`, `--no-structured`
- [ ] Includes usage examples for each new flag
- [ ] Includes output format description for both `interactive` and `local-model` targets
- [ ] Includes table of task metadata fields produced in `local-model` mode

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
