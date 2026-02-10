---
id: TASK-FP002-010
title: 'Documentation: Research Template Guide'
task_type: documentation
parent_review: TASK-REV-FP002
feature_id: FEAT-FP-002
wave: 2
implementation_mode: task-work
complexity: 3
complexity_score: 3
type: documentation
domain_tags:
- documentation
- research-template
- guides
files_to_create:
- docs/guides/research-template.md
- docs/templates/research-to-implementation-template.md
files_to_modify: []
files_not_to_touch:
- guardkit/
- tests/
dependencies:
- TASK-FP002-001
relevant_decisions:
- D6
- D8
turn_budget:
  expected: 1
  max: 3
graphiti_context_budget: 2000
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 25
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-FP-002
  base_branch: main
  started_at: '2026-02-10T17:50:11.817529'
  last_updated: '2026-02-10T17:58:28.830771'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-10T17:50:11.817529'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
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
