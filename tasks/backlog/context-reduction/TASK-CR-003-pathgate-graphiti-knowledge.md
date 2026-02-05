---
id: TASK-CR-003
title: Add path gate to graphiti-knowledge.md
status: in_review
created: 2026-02-05 14:00:00+00:00
updated: 2026-02-05 14:00:00+00:00
priority: high
tags:
- context-optimization
- token-reduction
- quick-win
parent_review: TASK-REV-5F19
feature_id: FEAT-CR01
implementation_mode: direct
wave: 1
complexity: 1
task_type: scaffolding
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-CR01
  base_branch: main
  started_at: '2026-02-05T17:14:31.105039'
  last_updated: '2026-02-05T17:15:52.875597'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-05T17:14:31.105039'
    player_summary: Added YAML frontmatter with paths gate to .claude/rules/graphiti-knowledge.md.
      The frontmatter includes three path patterns as specified in the acceptance
      criteria. This ensures the file only loads when working on Graphiti-related
      files, saving ~1,508 tokens in non-Graphiti conversations. The implementation
      is a minimal, non-invasive change that adds 3 lines at the top of the file without
      modifying any existing content.
    player_success: true
    coach_success: true
---

# Task: Add Path Gate to graphiti-knowledge.md

## Description

Add `paths:` frontmatter to `rules/graphiti-knowledge.md` so it only loads when working on Graphiti-related files. Currently this 1,508-token file loads in every conversation unconditionally.

## Acceptance Criteria

- [ ] `paths:` frontmatter added to graphiti-knowledge.md
- [ ] Paths include: `config/graphiti.yaml, guardkit/graphiti/**/*.py, docs/**/graphiti*`
- [ ] File no longer loads in non-Graphiti conversations

## Implementation Notes

Single edit: add `paths:` line to the existing frontmatter (file currently has no frontmatter at all).

```yaml
---
paths: config/graphiti.yaml, guardkit/graphiti/**/*.py, docs/**/graphiti*
---
```

Estimated savings: ~1,508 tokens (conditional - saved when not working on Graphiti)
