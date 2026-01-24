---
id: TASK-BRF-002
title: Add Worktree State Checkpoint and Rollback Mechanism
status: backlog
task_type: implementation
created: 2026-01-24T16:30:00Z
updated: 2026-01-24T16:30:00Z
priority: high
tags: [autobuild, context-pollution, block-research, worktree]
complexity: 7
parent_review: TASK-REV-BLOC
feature_id: FEAT-BRF
wave: 1
implementation_mode: task-work
conductor_workspace: block-research-fidelity-wave1-2
dependencies: []
---

# Task: Add Worktree State Checkpoint and Rollback Mechanism

## Description

Implement a checkpoint/rollback mechanism for worktree state to mitigate context pollution from accumulated failed code across turns.

**Problem**: The current implementation uses the same worktree across all turns. If turn 1 creates broken code, turn 2 inherits that state, potentially polluting subsequent attempts. Block research emphasizes isolated context windows.

**Solution**: Add optional worktree checkpointing that creates git commits at turn boundaries, allowing rollback when accumulated state is causing problems.

## Acceptance Criteria

- [ ] AC-001: Implement `_checkpoint_worktree(worktree, turn)` to create named checkpoint commit
- [ ] AC-002: Implement `_rollback_to_checkpoint(worktree, checkpoint_turn)` to restore state
- [ ] AC-003: Add `--enable-checkpoints` CLI flag (default: enabled)
- [ ] AC-004: Automatically rollback if same test fails 2+ turns in a row (context pollution indicator)
- [ ] AC-005: Create checkpoint commits with message format: `[guardkit-checkpoint] Turn {N} complete`
- [ ] AC-006: Preserve checkpoint history in `.guardkit/autobuild/{task_id}/checkpoints.json`
- [ ] AC-007: Add `--rollback-on-pollution` flag to control auto-rollback behavior
- [ ] AC-008: Unit and integration tests with ≥80% coverage

## Technical Approach

### Location
- Primary: `guardkit/orchestrator/autobuild.py`
- New module: `guardkit/orchestrator/worktree_checkpoints.py`
- Tests: `tests/unit/test_worktree_checkpoints.py`

### Implementation

```python
# New module: worktree_checkpoints.py
from dataclasses import dataclass
from pathlib import Path
import subprocess
import json

@dataclass
class Checkpoint:
    turn: int
    commit_hash: str
    timestamp: str
    test_status: bool

class WorktreeCheckpointManager:
    def __init__(self, worktree_path: Path, task_id: str):
        self.worktree_path = worktree_path
        self.task_id = task_id
        self.checkpoints: List[Checkpoint] = []
        self._checkpoints_file = worktree_path / ".guardkit" / "autobuild" / task_id / "checkpoints.json"

    def create_checkpoint(self, turn: int, test_status: bool) -> Checkpoint:
        """Create a checkpoint commit at current state."""
        # Stage all changes
        subprocess.run(["git", "add", "-A"], cwd=self.worktree_path, check=True)

        # Create checkpoint commit
        message = f"[guardkit-checkpoint] Turn {turn} complete (tests: {'pass' if test_status else 'fail'})"
        result = subprocess.run(
            ["git", "commit", "-m", message, "--allow-empty"],
            cwd=self.worktree_path,
            capture_output=True,
            text=True,
        )

        # Get commit hash
        commit_hash = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=self.worktree_path,
            capture_output=True,
            text=True,
        ).stdout.strip()

        checkpoint = Checkpoint(
            turn=turn,
            commit_hash=commit_hash,
            timestamp=datetime.now().isoformat(),
            test_status=test_status,
        )
        self.checkpoints.append(checkpoint)
        self._save_checkpoints()
        return checkpoint

    def rollback_to(self, turn: int) -> bool:
        """Rollback worktree to checkpoint at specified turn."""
        checkpoint = next((c for c in self.checkpoints if c.turn == turn), None)
        if not checkpoint:
            return False

        subprocess.run(
            ["git", "reset", "--hard", checkpoint.commit_hash],
            cwd=self.worktree_path,
            check=True,
        )
        logger.info(f"Rolled back to turn {turn} checkpoint: {checkpoint.commit_hash[:8]}")
        return True

    def detect_pollution(self) -> Optional[int]:
        """Detect context pollution and return turn to rollback to."""
        if len(self.checkpoints) < 2:
            return None

        # Check for repeated test failures on same tests
        recent = self.checkpoints[-2:]
        if not recent[0].test_status and not recent[1].test_status:
            # Two consecutive failures - rollback to last passing
            for cp in reversed(self.checkpoints[:-2]):
                if cp.test_status:
                    return cp.turn
        return None
```

### Integration in AutoBuildOrchestrator

```python
# In _loop_phase, after each turn:
if self.enable_checkpoints:
    self._checkpoint_manager.create_checkpoint(turn, turn_record.coach_result.report.get("tests_passed", False))

    if self.rollback_on_pollution:
        rollback_turn = self._checkpoint_manager.detect_pollution()
        if rollback_turn:
            logger.warning(f"Context pollution detected, rolling back to turn {rollback_turn}")
            self._checkpoint_manager.rollback_to(rollback_turn)
```

## Related Files

- `guardkit/orchestrator/autobuild.py` - Integration
- `guardkit/orchestrator/worktree_checkpoints.py` - New module
- `guardkit/cli/autobuild.py` - CLI flags
- `tests/unit/test_worktree_checkpoints.py` - Tests

## Notes

This addresses the "Context Pollution" gap (70/100 score) identified in TASK-REV-BLOC review. Block research emphasizes isolated context windows; this provides a recovery mechanism when pollution occurs.
