---
id: TASK-FP002-008
title: 'Documentation: Two-Phase Workflow Guide'
task_type: documentation
parent_review: TASK-REV-FP002
feature_id: FEAT-FP-002
wave: 4
implementation_mode: task-work
complexity: 4
complexity_score: 4
type: documentation
domain_tags:
- documentation
- two-phase-workflow
- guides
files_to_create:
- docs/guides/two-phase-workflow.md
files_to_modify: []
files_not_to_touch:
- guardkit/
- tests/
dependencies:
- TASK-FP002-007
relevant_decisions:
- D1
- D2
- D6
- D7
- D8
turn_budget:
  expected: 2
  max: 4
graphiti_context_budget: 4000
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 25
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-FP-002
  base_branch: main
  started_at: '2026-02-10T18:18:02.200586'
  last_updated: '2026-02-10T18:23:25.240570'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-10T18:18:02.200586'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# TASK-FP002-008: Documentation — Two-Phase Workflow Guide

## Description

Create comprehensive documentation explaining the two-phase workflow model: Phase 1 (research & planning on MacBook with frontier model) → Phase 2 (autonomous implementation on Dell ProMax with local model). This is the primary user-facing guide for the new feature.

## Acceptance Criteria (Machine-Verifiable)

- [ ] File exists: `docs/guides/two-phase-workflow.md`
- [ ] Document contains sections: Overview, Phase 1 (Research & Planning), Phase 2 (Implementation), Research Template Guide, Feature-Plan Flags Reference, Graphiti Seeding, Troubleshooting
- [ ] Contains at least 2 complete command examples showing the full workflow
- [ ] References `/feature-plan --from-spec` and `--target local-model` flags
- [ ] References `scripts/seed-FEAT-XXX.sh` and `guardkit feature-build`
- [ ] Contains ASCII diagram showing the two-phase data flow
- [ ] Word count > 1500 (comprehensive guide, not a stub)

## Coach Validation Commands

```bash
python -c "
from pathlib import Path
content = Path('docs/guides/two-phase-workflow.md').read_text()
assert len(content.split()) > 1500, f'Too short: {len(content.split())} words'
for section in ['Phase 1', 'Phase 2', '--from-spec', '--target', 'seed-FEAT', 'feature-build']:
    assert section in content, f'Missing section/reference: {section}'
print('Documentation validation OK')
"
```

## Player Constraints

- Create files ONLY in `docs/guides/`
- Do NOT create or modify any code files
- Use Markdown with MkDocs-compatible formatting (admonitions, code blocks with language tags)
- Reference existing documentation pages by relative link, not absolute URL
