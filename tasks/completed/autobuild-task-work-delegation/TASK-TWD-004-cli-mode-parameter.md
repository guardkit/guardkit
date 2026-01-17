---
id: TASK-TWD-004
title: Add development mode parameter to AutoBuild CLI
status: completed
completed: 2026-01-02T10:30:00Z
task_type: implementation
created: 2025-12-31T14:00:00Z
priority: medium
tags: [autobuild, cli, configuration, user-experience]
complexity: 3
parent_feature: autobuild-task-work-delegation
wave: 2
implementation_mode: task-work
conductor_workspace: autobuild-twd-wave2-2
source_review: TASK-REV-RW01
depends_on: [TASK-TWD-001]
---

# Task: Add development mode parameter to AutoBuild CLI

## Description

Add a `--mode` parameter to the `guardkit autobuild task` CLI command to allow users to specify the development mode (tdd, standard, bdd) that will be passed through to task-work.

## Current CLI

```bash
guardkit autobuild task TASK-XXX [--max-turns 5] [--model MODEL] [--verbose] [--resume]
```

## Target CLI

```bash
guardkit autobuild task TASK-XXX \
  [--max-turns 5] \
  [--model MODEL] \
  [--mode tdd|standard|bdd] \
  [--verbose] \
  [--resume]
```

## Implementation

### 1. Update CLI command

```python
# guardkit/cli/autobuild.py

@autobuild.command()
@click.argument("task_id")
@click.option(
    "--max-turns",
    default=5,
    type=int,
    help="Maximum adversarial turns (default: 5)",
    show_default=True,
)
@click.option(
    "--model",
    default="claude-sonnet-4-5-20250929",
    help="Claude model to use",
    show_default=True,
)
@click.option(
    "--mode",
    type=click.Choice(["tdd", "standard", "bdd"]),
    default="tdd",
    help="Development mode for task-work (default: tdd)",
    show_default=True,
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed turn-by-turn output",
)
@click.option(
    "--resume",
    is_flag=True,
    help="Resume from last saved state",
)
@click.pass_context
@handle_cli_errors
def task(
    ctx,
    task_id: str,
    max_turns: int,
    model: str,
    mode: str,
    verbose: bool,
    resume: bool,
):
    """Execute AutoBuild orchestration for a task."""
    # ... existing setup ...

    orchestrator = AutoBuildOrchestrator(
        repo_root=Path.cwd(),
        max_turns=max_turns,
        resume=resume,
        development_mode=mode,  # NEW: Pass mode to orchestrator
    )

    result = orchestrator.orchestrate(
        task_id=task_id,
        requirements=task_data["requirements"],
        acceptance_criteria=task_data["acceptance_criteria"],
        task_file_path=task_data.get("file_path"),
    )
```

### 2. Update AutoBuildOrchestrator

```python
# guardkit/orchestrator/autobuild.py

class AutoBuildOrchestrator:
    def __init__(
        self,
        repo_root: Path,
        max_turns: int = 5,
        resume: bool = False,
        development_mode: str = "tdd",  # NEW parameter
    ):
        self.repo_root = repo_root
        self.max_turns = max_turns
        self.resume = resume
        self.development_mode = development_mode
        # ...

    def orchestrate(self, ...):
        # Pass mode to agent_invoker
        self.agent_invoker = AgentInvoker(
            worktree_path=self.worktree.path,
            development_mode=self.development_mode,
            ...
        )
```

### 3. Update AgentInvoker

```python
# guardkit/orchestrator/agent_invoker.py

class AgentInvoker:
    def __init__(
        self,
        worktree_path: Path,
        development_mode: str = "tdd",
        ...
    ):
        self.worktree_path = worktree_path
        self.development_mode = development_mode
        # ...

    async def invoke_player(self, ...) -> AgentInvocationResult:
        result = await self._invoke_task_work_implement(
            task_id=task_id,
            mode=self.development_mode,  # Use configured mode
            ...
        )
```

## Mode Descriptions

| Mode | Description | Use Case |
|------|-------------|----------|
| `tdd` | Test-Driven Development (RED→GREEN→REFACTOR) | Complex logic, algorithms |
| `standard` | Implementation then tests | Simple features, CRUD |
| `bdd` | Behavior-Driven Development | Requires RequireKit, formal specs |

## Display Update

Update the startup banner to show the mode:

```python
console.print(
    Panel(
        f"[bold]AutoBuild Task Orchestration[/bold]\n\n"
        f"Task: [cyan]{task_id}[/cyan]\n"
        f"Max Turns: {max_turns}\n"
        f"Model: {model}\n"
        f"Mode: [green]{mode.upper()}[/green]\n"  # NEW
        f"Status: {mode_text}",
        title="GuardKit AutoBuild",
        border_style="blue",
    )
)
```

## Task Frontmatter Support

Allow mode to be specified in task frontmatter as default:

```yaml
---
id: TASK-XXX
title: Implement feature
autobuild:
  enabled: true
  mode: tdd  # Default mode for this task
  max_turns: 5
---
```

CLI flag overrides frontmatter:

```python
# In task command
mode = mode or task_data.get("autobuild", {}).get("mode", "tdd")
```

## Acceptance Criteria

1. `--mode` option added to `guardkit autobuild task` command
2. Mode passed through orchestrator → agent_invoker → task-work
3. Default mode is `tdd`
4. Mode displayed in startup banner
5. Task frontmatter `autobuild.mode` used as default
6. CLI flag overrides frontmatter setting
7. Invalid mode values rejected with clear error

## Files to Modify

- `guardkit/cli/autobuild.py` - Add CLI option
- `guardkit/orchestrator/autobuild.py` - Accept and pass mode
- `guardkit/orchestrator/agent_invoker.py` - Use mode in task-work call

## Testing

1. Unit test: CLI accepts --mode parameter
2. Unit test: Mode passed through to orchestrator
3. Unit test: Mode used in task-work subprocess call
4. Unit test: Frontmatter mode used as default
5. Unit test: CLI flag overrides frontmatter

## Notes

- Consider adding mode to turn history for audit trail
- BDD mode requires RequireKit - add check and helpful error
- Mode should be preserved in resume state
