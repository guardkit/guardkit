---
id: TASK-FBC-001
title: Add guardkit autobuild feature CLI command
status: completed
created: 2025-12-31T17:00:00Z
updated: 2025-12-31T21:00:00Z
completed: 2025-12-31T21:00:00Z
priority: high
complexity: 7
tags: [cli, autobuild, feature-mode, player-coach]
parent_feature: feature-build-cli-native
source_review: TASK-REV-FB01
implementation_mode: task-work
estimated_hours: 8-12
actual_hours: 6
code_review_score: 8.5
completed_location: tasks/completed/feature-build-cli-native/TASK-FBC-001/
---

# Add `guardkit autobuild feature` CLI Command

## Description

Implement native CLI support for feature-level AutoBuild orchestration. Currently, the CLI only supports single-task mode (`guardkit autobuild task TASK-XXX`). This task adds the `feature` subcommand for multi-task, wave-based execution.

**User Impact**: Eliminates "CLI not available" fallback messages that dent user confidence.

## Requirements

Add `guardkit autobuild feature FEAT-XXX` command with:

1. **Feature YAML Loading**
   - Load feature file from `.guardkit/features/FEAT-XXX.yaml`
   - Parse tasks, dependencies, and parallel_groups
   - Validate all task markdown files exist

2. **Wave Execution**
   - Execute tasks wave by wave
   - Respect parallel_groups from feature YAML
   - Block wave until all tasks complete

3. **Shared Worktree**
   - Create single worktree per feature: `.guardkit/worktrees/FEAT-XXX/`
   - Branch: `autobuild/FEAT-XXX`
   - All tasks work in same worktree

4. **Player-Coach Loop**
   - Use existing `autobuild task` infrastructure
   - Execute Player-Coach loop for each task
   - Update task status in feature YAML after each completion

## Acceptance Criteria

- [x] `guardkit autobuild feature --help` shows usage
- [x] Command loads feature YAML correctly
- [x] Wave execution respects parallel_groups
- [x] Shared worktree created per feature
- [x] Player-Coach loop executes for each task
- [x] Feature YAML updated with task statuses
- [x] Final summary shows all task results
- [x] No "CLI not available" messages when using CLI

## Implementation Notes

### CLI Structure

```python
# guardkit/cli/autobuild.py

@autobuild.command()
@click.argument("feature_id")
@click.option("--max-turns", default=5, help="Max turns per task")
@click.option("--parallel", default=1, help="Max parallel tasks")
@click.option("--stop-on-failure", is_flag=True, default=True)
@click.option("--verbose", is_flag=True)
def feature(feature_id: str, max_turns: int, parallel: int,
            stop_on_failure: bool, verbose: bool):
    """Execute AutoBuild for all tasks in a feature."""
    orchestrator = FeatureOrchestrator(feature_id)
    orchestrator.execute(
        max_turns=max_turns,
        parallel=parallel,
        stop_on_failure=stop_on_failure,
        verbose=verbose
    )
```

### Feature Orchestrator

```python
# guardkit/orchestrator/feature_orchestrator.py

class FeatureOrchestrator:
    def __init__(self, feature_id: str):
        self.feature_id = feature_id
        self.feature = self._load_feature()
        self.worktree_path = None

    def _load_feature(self) -> dict:
        """Load feature YAML from .guardkit/features/"""
        pass

    def _create_worktree(self) -> Path:
        """Create shared worktree for feature"""
        pass

    def execute(self, max_turns: int, parallel: int,
                stop_on_failure: bool, verbose: bool):
        """Execute all tasks wave by wave"""
        self._create_worktree()

        for wave in self.feature["orchestration"]["parallel_groups"]:
            self._execute_wave(wave, max_turns, parallel, verbose)

            if stop_on_failure and self._has_failures(wave):
                break

        self._finalize()
```

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `guardkit/cli/autobuild.py` | Modify | Add `feature` command |
| `guardkit/orchestrator/feature_orchestrator.py` | Create | Feature orchestration logic |
| `guardkit/orchestrator/autobuild.py` | Modify | Refactor for shared use |

## Testing

```bash
# Create test feature
/feature-plan "test feature"

# Run CLI command
guardkit autobuild feature FEAT-XXX --verbose

# Verify no fallback messages
guardkit autobuild feature FEAT-XXX 2>&1 | grep -i "fallback"
# Should return nothing
```

## Dependencies

- Existing `guardkit autobuild task` infrastructure
- Feature YAML schema from `/feature-plan`
- Player-Coach agent definitions

## Notes

This is the highest priority task from TASK-REV-FB01 review. The goal is eliminating user-visible fallback messages to improve confidence in the tool.
