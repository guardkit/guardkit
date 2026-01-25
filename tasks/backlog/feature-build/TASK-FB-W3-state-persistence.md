---
id: TASK-FB-W3
title: "Wave 3: State Persistence and Resume Capability"
status: completed
task_type: implementation
created: 2025-12-24T00:00:00Z
updated: 2025-12-24T00:00:00Z
completed: 2025-12-24T00:00:00Z
priority: high
tags: [feature-build, state, persistence, resume, worktree, wave-3]
complexity: 5
parent_feature: feature-build
wave: 3
estimated_hours: 2-3
dependencies: [TASK-FB-W2]
---

# Wave 3: State Persistence and Resume Capability

## Overview

Implement state persistence in task frontmatter and worktree integration for the feature-build command.

## Requirements

### Functional Requirements

1. **FR-1**: Worktree integration
   - Create worktree via WorktreeManager
   - Work in isolated worktree
   - Preserve worktree on failure

2. **FR-2**: State persistence
   - Store state in task frontmatter
   - Track turn history
   - Enable resume from last turn

3. **FR-3**: Resume capability
   - `--resume` flag to continue interrupted execution
   - Load previous state from frontmatter
   - Continue from last turn

## Files to Modify

### 1. `guardkit/orchestrator/sdk_orchestrator.py` (MODIFY)

Add worktree and state management:

```python
from pathlib import Path
from datetime import datetime
import yaml

from orchestrator.worktrees import WorktreeManager, Worktree


class DialecticalOrchestrator:
    """Orchestrates Player-Coach dialectical loop using Claude Agent SDK."""

    def __init__(
        self,
        task_id: str,
        max_turns: int = 5,
        model: str = "claude-sonnet-4-5",
        verbose: bool = False,
        resume: bool = False,
    ):
        self.task_id = task_id
        self.max_turns = max_turns
        self.model = model
        self.verbose = verbose
        self.resume = resume
        self.worktree: Optional[Worktree] = None
        self.worktree_manager = WorktreeManager(repo_root=Path.cwd())
        self.turn_history: list[dict] = []

    async def orchestrate(
        self,
        requirements: str,
        acceptance_criteria: list[str],
        task_file_path: Path = None,
    ) -> OrchestrationResult:
        """Run the full dialectical loop."""

        # Setup or resume worktree
        if self.resume:
            self._load_state(task_file_path)
            start_turn = len(self.turn_history) + 1
        else:
            self.worktree = self.worktree_manager.create(
                task_id=self.task_id,
                branch_name=f"feature-build/{self.task_id}",
            )
            start_turn = 1
            self._save_state(task_file_path, status="in_progress")

        feedback = self._get_last_feedback() if self.resume else None

        for turn in range(start_turn, self.max_turns + 1):
            # PLAYER TURN
            player_result = await self._player_turn(
                requirements=requirements,
                acceptance_criteria=acceptance_criteria,
                feedback=feedback,
                turn=turn,
            )

            # COACH TURN
            coach_result = await self._coach_turn(
                requirements=requirements,
                acceptance_criteria=acceptance_criteria,
                player_output=player_result,
                turn=turn,
            )

            # Record turn
            self.turn_history.append({
                "turn": turn,
                "player_summary": player_result.output[:500],
                "coach_decision": coach_result.decision,
                "feedback": coach_result.feedback,
                "timestamp": datetime.now().isoformat(),
            })

            # Persist state after each turn
            self._save_state(task_file_path, status="in_progress")

            if coach_result.decision == "approve":
                self._save_state(task_file_path, status="in_review")
                return OrchestrationResult(
                    success=True,
                    turns=turn,
                    worktree_path=self.worktree.path,
                    final_decision="approve",
                )

            feedback = coach_result.feedback

        # Max turns exceeded
        self._save_state(task_file_path, status="blocked")
        return OrchestrationResult(
            success=False,
            turns=self.max_turns,
            worktree_path=self.worktree.path,
            final_decision="max_turns_exceeded",
            reason=f"Coach did not approve after {self.max_turns} turns",
        )

    def _load_state(self, task_file_path: Path) -> None:
        """Load state from task frontmatter."""
        with open(task_file_path, "r") as f:
            content = f.read()

        # Parse YAML frontmatter
        if content.startswith("---"):
            _, frontmatter, _ = content.split("---", 2)
            data = yaml.safe_load(frontmatter)

            fb_state = data.get("feature_build", {})
            self.turn_history = fb_state.get("turns", [])
            worktree_path = fb_state.get("worktree_path")

            if worktree_path:
                self.worktree = Worktree(
                    task_id=self.task_id,
                    branch_name=f"feature-build/{self.task_id}",
                    path=Path(worktree_path),
                    base_branch="main",
                )

    def _save_state(self, task_file_path: Path, status: str) -> None:
        """Save state to task frontmatter."""
        if not task_file_path:
            return

        with open(task_file_path, "r") as f:
            content = f.read()

        # Parse and update frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            frontmatter = yaml.safe_load(parts[1])
            body = parts[2] if len(parts) > 2 else ""

            frontmatter["status"] = status
            frontmatter["feature_build"] = {
                "current_turn": len(self.turn_history),
                "max_turns": self.max_turns,
                "worktree_path": str(self.worktree.path) if self.worktree else None,
                "started_at": self.turn_history[0]["timestamp"] if self.turn_history else datetime.now().isoformat(),
                "turns": self.turn_history,
            }

            # Write back
            with open(task_file_path, "w") as f:
                f.write("---\n")
                f.write(yaml.dump(frontmatter, default_flow_style=False))
                f.write("---")
                f.write(body)

    def _get_last_feedback(self) -> Optional[str]:
        """Get feedback from last turn."""
        if self.turn_history:
            return self.turn_history[-1].get("feedback")
        return None
```

### 2. `guardkit/cli/feature_build.py` (MODIFY)

Add `--resume` flag:

```python
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from last saved state",
)
def feature_build(
    ctx,
    task_id: str,
    max_turns: int,
    model: str,
    verbose: bool,
    resume: bool,
):
    # ...

    orchestrator = DialecticalOrchestrator(
        task_id=task_id,
        max_turns=max_turns,
        model=model,
        verbose=verbose,
        resume=resume,
    )

    result = asyncio.run(
        orchestrator.orchestrate(
            requirements=task_data["requirements"],
            acceptance_criteria=task_data["acceptance_criteria"],
            task_file_path=task_data["file_path"],
        )
    )
```

## State Format in Task Frontmatter

```yaml
---
id: TASK-XXX
status: in_progress  # or blocked, in_review
feature_build:
  current_turn: 2
  max_turns: 5
  worktree_path: .guardkit/worktrees/TASK-XXX
  started_at: 2025-12-24T10:00:00Z
  turns:
    - turn: 1
      player_summary: "Implemented OAuth flow with tests..."
      coach_decision: feedback
      feedback: "Missing token refresh edge case"
      timestamp: 2025-12-24T10:05:00Z
    - turn: 2
      player_summary: "Added refresh token handling..."
      coach_decision: approve
      feedback: null
      timestamp: 2025-12-24T10:12:00Z
---
```

## Acceptance Criteria

- [ ] Worktree created via WorktreeManager
- [ ] State persisted to task frontmatter after each turn
- [ ] Turn history recorded with timestamps
- [ ] `--resume` flag loads previous state
- [ ] Resume continues from correct turn
- [ ] Worktree preserved on failure (status=blocked)
- [ ] Status updated on success (status=in_review)

## Testing

```bash
# Start orchestration
guardkit feature-build TASK-TEST-001

# Interrupt (Ctrl+C)
# Check state in task file

# Resume
guardkit feature-build TASK-TEST-001 --resume
```

## Dependencies

- Wave 2: CLI command
- Existing `WorktreeManager`
- `pyyaml` for frontmatter parsing
