---
id: TASK-TPL-007
title: 'Documentation: reframe templates/ dirs + AutoBuild guide updates'
task_type: documentation
parent_review: TASK-REV-B3F7
feature_id: FEAT-TPL-PLAYER
wave: 5
implementation_mode: direct
complexity: 3
dependencies:
- TASK-TPL-004
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-4396
  base_branch: main
  started_at: '2026-04-11T17:15:17.514420'
  last_updated: '2026-04-11T17:26:12.090330'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-11T17:15:17.514420'
    player_summary: "Completed all four acceptance criteria for TASK-TPL-007 (Documentation\
      \ updates):\n\n1. AC-001: Added a comprehensive 'Template Pattern Context' section\
      \ to the AutoBuild Instrumentation Guide (docs/guides/autobuild-instrumentation-guide.md).\
      \ The section covers: overview and rationale, complete data flow diagram (manifest\
      \ \u2192 resolver \u2192 selector \u2192 formatter \u2192 injection), key components\
      \ table with file paths, manifest requirement (.claude/manifest.json `name`\
      \ field), pattern selection rules (4-tier pri"
    player_success: true
    coach_success: true
---

# Documentation updates

## Scope

1. **Close TASK-DRF-F4B8** and reframe its narrative: `templates/` subdirectories in builtin templates are **build-time pattern references** consumed by AutoBuild's Player, not "reference material without a consumer". Update the task or write a superseding doc explaining:
   - What the `.template` files are (parameterised scaffold code)
   - When they are consumed (AutoBuild Player context loading at build time)
   - Where the consumer lives (`guardkit/knowledge/template_pattern_loader.py`)
2. **Update AutoBuild guide** (likely `docs/guides/autobuild-*.md` or similar) with a new section "Template Pattern Context":
   - Explains the pipeline (manifest → resolver → selector → context injection)
   - Documents the `.claude/manifest.json` `name` field requirement
   - Documents graceful degradation behaviour
3. **Update CLAUDE.md template section** (if a template-layer section exists) to describe the two-layer model: config-layer (`guardkit init`) vs pattern-layer (build-time injection).
4. **Close TASK-DRF-F4B8b** explicitly — no rename of `templates/` dirs is required (per D6).

## Acceptance Criteria

1. Updates to AutoBuild guide are present and internally consistent with the code shipped in TASK-TPL-004.
2. F4B8a task is either closed with a note pointing at this feature, or rewritten as a doc task that this feature has completed.
3. F4B8b is closed with rationale: "consumer exists, no rename needed".
4. All referenced file paths in docs match reality (no dead links).

## Coach Validation

- Manual doc review; no automated gate.
- Verify all internal links resolve (markdown link checker if configured).
