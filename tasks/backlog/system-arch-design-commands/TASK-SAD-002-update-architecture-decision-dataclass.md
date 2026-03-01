---
id: TASK-SAD-002
title: Update ArchitectureDecision dataclass with superseding and alternatives fields
task_type: feature
parent_review: TASK-REV-AEE1
feature_id: FEAT-SAD
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
status: blocked
autobuild_state:
  current_turn: 1
  max_turns: 30
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-E4F5
  base_branch: main
  started_at: '2026-03-01T17:38:40.215227'
  last_updated: '2026-03-01T18:35:24.149489'
  turns:
  - turn: 1
    decision: error
    feedback: null
    timestamp: '2026-03-01T17:38:40.215227'
    player_summary: '[RECOVERED via player_report] Original error: SDK timeout after
      2340s: task-work execution exceeded 2340s timeout'
    player_success: true
    coach_success: false
---

# Task: Update ArchitectureDecision dataclass with superseding and alternatives fields

## Description

Extend the existing `ArchitectureDecision` dataclass in `guardkit/knowledge/entities/architecture_context.py` with three new fields required by `/system-arch` and the refinement commands. Also parametrise the ADR prefix to support different prefixes per command.

## Acceptance Criteria

- [ ] Add `alternatives_considered: List[str] = field(default_factory=list)` field
- [ ] Add `superseded_by: Optional[str] = None` field
- [ ] Add `supersedes: Optional[str] = None` field
- [ ] Parametrise prefix: `prefix: str = "SP"` with `entity_id` property using `f"ADR-{self.prefix}-{self.number:03d}"`
- [ ] Update `to_episode_body()` to include new fields (conditional: only include if non-empty)
- [ ] All existing tests pass (backwards compatible — default prefix remains "SP")
- [ ] Unit tests for new fields and prefix parametrisation

## Implementation Notes

- File: `guardkit/knowledge/entities/architecture_context.py`
- Existing entity_id: `ADR-SP-{NNN:03d}` — this stays as default
- `/system-arch` will use `prefix="ARCH"` → `ADR-ARCH-001`
- `/feature-spec` uses `prefix="FS"` → `ADR-FS-001` (already exists)
- Ensure `to_episode_body()` remains backwards compatible with existing seeded data
