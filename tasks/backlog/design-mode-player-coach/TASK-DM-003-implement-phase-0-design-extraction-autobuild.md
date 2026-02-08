---
id: TASK-DM-003
title: Implement Phase 0 design extraction in autobuild
status: in_review
created: 2026-02-07 10:00:00+00:00
updated: 2026-02-07 10:00:00+00:00
priority: high
task_type: feature
parent_review: TASK-REV-D3E0
feature_id: FEAT-D4CE
wave: 2
implementation_mode: task-work
complexity: 7
dependencies:
- TASK-DM-001
- TASK-DM-002
tags:
- design-mode
- autobuild
- orchestrator
- phase-0
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 25
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-D4CE
  base_branch: main
  started_at: '2026-02-08T11:27:50.914745'
  last_updated: '2026-02-08T11:35:05.978020'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-02-08T11:27:50.914745'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# Implement Phase 0 Design Extraction in AutoBuild

## Description

Add Phase 0 (Design Extraction) to the AutoBuild orchestrator. When a task has a `design_url` in frontmatter, Phase 0 runs before the existing pre-loop phase, extracting design data via the MCP facade and making it available as context for the Player-Coach loop.

## Requirements

1. In `guardkit/orchestrator/autobuild.py`, add `_extract_design_phase()`:
   - Check if task has `design_url` in frontmatter
   - If no design URL, skip Phase 0 entirely (backward compatible)
   - If design URL present:
     - Phase 0.1: Verify required MCP tools available (fail fast)
     - Phase 0.2: Extract design data via `DesignExtractor`
     - Phase 0.3: Store extraction metadata (timestamp, hash) in task frontmatter
     - Phase 0.4: Return `DesignContext` for downstream use

2. Integration point: Insert before `_execute_pre_loop_phase()` call

3. `DesignContext` dataclass:
   ```python
   @dataclass
   class DesignContext:
       elements: List[Dict[str, Any]]  # What's in the design
       tokens: Dict[str, Any]          # colors, spacing, typography
       constraints: Dict[str, bool]    # Prohibition checklist (12 categories)
       visual_reference: Optional[str] # Path to reference screenshot
       summary: str                     # ~3K token summary for agent context
       source: str                      # "figma" | "zeplin"
       metadata: Dict[str, Any]        # file_key, node_id, etc.
   ```

4. Extend `_loop_phase()` return Literal to include `"design_extraction_failed"`

5. Update `OrchestrationResult.final_decision` Literal to match

6. Update `FinalStatus` in `progress.py` to match

7. Non-design tasks must be completely unaffected.

## Acceptance Criteria

- [ ] Phase 0 runs before pre-loop phase when `design_url` present
- [ ] Phase 0 skipped entirely for tasks without `design_url`
- [ ] MCP verification fails fast if required tools unavailable
- [ ] Design data extracted and summarised into `DesignContext`
- [ ] Extraction metadata (timestamp, hash) written to task frontmatter
- [ ] `"design_extraction_failed"` added to loop exit Literal
- [ ] `OrchestrationResult.final_decision` updated with new status
- [ ] `FinalStatus` in progress.py updated with new status
- [ ] `_finalize_phase`, `_build_summary_details`, `_build_error_message` handle new status
- [ ] Existing non-design tests pass unchanged
- [ ] Unit tests for Phase 0 with mocked DesignExtractor

## Technical Notes

- See memory: exit status updates require changes in 3 locations (loop return type, OrchestrationResult, FinalStatus)
- See FEAT-DESIGN-MODE-spec.md §4 (Design Extraction Phase)
- Follow PreLoopQualityGates pattern for phase structure
- `DesignContext.summary` is what gets passed to Player/Coach — not raw MCP data
