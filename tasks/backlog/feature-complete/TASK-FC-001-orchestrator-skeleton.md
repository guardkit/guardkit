---
id: TASK-FC-001
title: Create feature-complete orchestrator skeleton
status: backlog
created: 2026-01-24T12:00:00Z
updated: 2026-01-24T12:00:00Z
priority: high
tags: [feature-complete, orchestrator, architecture]
complexity: 3
parent_review: TASK-REV-FC01
feature_id: FEAT-FC-001
implementation_mode: task-work
wave: 1
dependencies: []
estimated_minutes: 45
---

# Task: Create feature-complete orchestrator skeleton

## Description

Create the core `FeatureCompleteOrchestrator` class that coordinates the feature completion workflow. This orchestrator handles the three-phase execution pattern: Validation → Completion → Handoff.

## Requirements

1. Create `guardkit/orchestrator/feature_complete.py` with:
   - `FeatureCompleteOrchestrator` class
   - Three-phase execution: validate, complete tasks, display handoff instructions
   - Integration with `FeatureLoader` for feature YAML operations
   - Integration with `WorktreeManager` for worktree status

2. Add CLI command in `guardkit/cli/autobuild.py`:
   - `guardkit autobuild complete FEAT-XXX` command
   - Basic flags: `--dry-run`, `--force`

3. Follow existing patterns from:
   - `feature_orchestrator.py` (phase pattern)
   - `autobuild.py` (CLI integration)

## Acceptance Criteria

- [ ] `FeatureCompleteOrchestrator` class created with `complete()` method
- [ ] Phase 1 (Validation): Checks feature exists and status is valid
- [ ] Phase 2 (Completion): Placeholder for task completion (implemented in TASK-FC-002)
- [ ] Phase 3 (Handoff): Placeholder for instructions (implemented in TASK-FC-004)
- [ ] CLI command `guardkit autobuild complete FEAT-XXX` works
- [ ] `--dry-run` flag shows what would happen without executing
- [ ] Unit tests for orchestrator skeleton

## Technical Notes

```python
# Skeleton structure
class FeatureCompleteOrchestrator:
    def __init__(self, repo_root: Path, ...):
        self.repo_root = repo_root
        self._feature_loader = FeatureLoader
        self._worktree_manager = WorktreeManager(repo_root)

    def complete(self, feature_id: str, dry_run: bool = False) -> FeatureCompleteResult:
        """Execute feature completion workflow."""
        # Phase 1: Validation
        feature = self._validate_phase(feature_id)

        if dry_run:
            return self._dry_run_result(feature)

        # Phase 2: Task Completion (TASK-FC-002)
        task_results = self._complete_tasks_phase(feature)

        # Phase 3: Archival (TASK-FC-003)
        self._archive_phase(feature)

        # Phase 4: Handoff Instructions (TASK-FC-004)
        self._display_handoff(feature)

        return FeatureCompleteResult(...)
```

## Files to Create/Modify

- **Create**: `guardkit/orchestrator/feature_complete.py`
- **Modify**: `guardkit/cli/autobuild.py` (add `complete` subcommand)
- **Create**: `tests/orchestrator/test_feature_complete.py`
