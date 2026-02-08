---
id: TASK-DM-001
title: Extend task frontmatter for design URLs
status: in_review
created: 2026-02-07 10:00:00+00:00
updated: 2026-02-07 10:00:00+00:00
priority: high
task_type: scaffolding
parent_review: TASK-REV-D3E0
feature_id: FEAT-D4CE
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
tags:
- design-mode
- frontmatter
- task-create
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-D4CE
  base_branch: main
  started_at: '2026-02-07T21:29:48.103070'
  last_updated: '2026-02-07T22:26:14.694563'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-07T21:29:48.103070'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Extend Task Frontmatter for Design URLs

## Description

Add `design_url`, `design_source`, and `design_metadata` fields to the task frontmatter schema. Enable `/task-create` to accept a `design:URL` parameter that auto-detects the design source (Figma or Zeplin), extracts metadata (file_key, node_id), and stores it in the task file.

## Requirements

1. Accept `design:URL` parameter on `/task-create`:
   ```bash
   /task-create "Login form" design:https://figma.com/design/abc?node-id=2-2
   ```

2. Auto-detect design source from URL:
   - `figma.com` → `figma`
   - `zeplin.io` or `app.zeplin.io` → `zeplin`
   - Anything else → error with helpful message

3. Extract metadata from URL:
   - Figma: `file_key` from path, `node_id` from query param (convert `2-2` → `"2:2"`)
   - Zeplin: `project_id`, `screen_id`, `component_id` from path segments

4. Store in frontmatter:
   ```yaml
   design_url: https://figma.com/design/abc?node-id=2-2
   design_source: figma
   design_metadata:
     file_key: abc123
     node_id: "2:2"
     extracted_at: null
     extraction_hash: null
     visual_reference: null
   ```

5. Backward compatible — tasks without `design_url` continue working unchanged.

## Acceptance Criteria

- [ ] `/task-create` accepts `design:URL` parameter
- [ ] Design URL stored in task frontmatter under `design_url`
- [ ] Design source auto-detected (figma/zeplin)
- [ ] Figma node IDs converted from hyphen to colon format
- [ ] Zeplin project/screen/component IDs extracted
- [ ] Invalid URL produces clear error with supported formats
- [ ] Tasks without design URL unaffected (backward compatible)
- [ ] Unit tests for URL parsing and metadata extraction

## Technical Notes

- See FEAT-DESIGN-MODE-spec.md §1 (Task Frontmatter Extension)
- See TASK-UX-7F1E for original design URL parameter design
- Node ID conversion is the #1 cause of MCP failures — get this right
