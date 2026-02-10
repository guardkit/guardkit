---
complexity: 3
complexity_score: 3
dependencies:
- TASK-FP002-001
domain_tags:
- documentation
- research-template
- guides
feature_id: FEAT-FP-002
files_not_to_touch:
- guardkit/
- tests/
files_to_create:
- docs/guides/research-template.md
- docs/templates/research-to-implementation-template.md
files_to_modify: []
graphiti_context_budget: 2000
id: TASK-FP002-010
implementation_mode: task-work
parent_review: TASK-REV-FP002
relevant_decisions:
- D6
- D8
status: in_review
task_type: documentation
title: 'Documentation: Research Template Guide'
turn_budget:
  expected: 1
  max: 3
type: documentation
wave: 2
---

# TASK-FP002-010: Documentation — Research Template Guide

## Description

Create the guide for using the Research-to-Implementation Template with GuardKit, plus a canonical copy of the template itself. Explains what each of the 11 sections is for and tips for writing specs that local models execute well.

## Acceptance Criteria (Machine-Verifiable)

- [ ] File exists: `docs/guides/research-template.md`
- [ ] File exists: `docs/templates/research-to-implementation-template.md`
- [ ] Guide explains all 11 template sections with examples
- [ ] Guide includes "Tips for Local Model Execution" section
- [ ] Template file is a clean, fillable version (no example data except placeholders)
- [ ] Template contains all 11 sections: Problem Statement, Decision Log, Architecture, API Contracts, Implementation Tasks, Test Strategy, Dependencies & Setup, File Tree, Out of Scope, Open Questions, Graphiti ADR Seeding

## Coach Validation Commands

```bash
python -c "
from pathlib import Path
assert Path('docs/guides/research-template.md').exists()
assert Path('docs/templates/research-to-implementation-template.md').exists()
template = Path('docs/templates/research-to-implementation-template.md').read_text()
for section in ['Problem Statement', 'Decision Log', 'Architecture', 'Implementation Tasks', 'Graphiti ADR Seeding']:
    assert section in template, f'Missing section: {section}'
print('Template validation OK')
"
```

## Player Constraints

- Create files ONLY in `docs/guides/` and `docs/templates/`
- Do NOT modify any code files
- The template copy must be identical in structure to `docs/research/system-level-understanding/research-to-implementation-template.md` with placeholder text
- Use MkDocs-compatible formatting