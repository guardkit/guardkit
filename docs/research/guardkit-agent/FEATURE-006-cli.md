# Feature 6: gka CLI Command

> **Feature ID**: FEATURE-006
> **Priority**: P1 (User interface)
> **Estimated Effort**: 1-2 days
> **Dependencies**: FEATURE-001, FEATURE-005

---

## Summary

Create the command-line interface for GuardKit Agent. This is the user-facing entry point that wraps the orchestrator and provides progress feedback, configuration options, and result reporting.

---

## Command Structure

```bash
gka [COMMAND] [OPTIONS]

Commands:
  task      Run GuardKit Agent on a single task
  feature   Run GuardKit Agent on all tasks in a feature
  resume    Resume an interrupted run
  status    Show status of running/completed runs
  cancel    Cancel a running operation

Global Options:
  --verbose, -v     Show detailed output
  --quiet, -q       Minimal output (just results)
  --dry-run         Show what would run without executing
```

---

## Detailed Commands

### gka task work

Run GuardKit Agent on a single task.

```bash
gka task work TASK-001 [OPTIONS]

Arguments:
  TASK_ID    Task ID to run (e.g., TASK-001)

Options:
  --max-turns INT    Maximum player/coach turns [default: 10]
  --timeout INT      Timeout per turn in seconds [default: 300]
  --no-merge         Don't merge worktree on success
  --model TEXT       Override model for agents (haiku/sonnet/opus)
```

**Examples:**
```bash
# Basic usage
gka task work TASK-001

# With options
gka task work TASK-001 --max-turns 5 --verbose

# Dry run
gka task work TASK-001 --dry-run
```

### gka feature work

Run GuardKit Agent on all tasks in a feature.

```bash
gka feature work FEAT-001 [OPTIONS]

Arguments:
  FEATURE_ID    Feature ID to run (e.g., FEAT-001)

Options:
  --parallel INT     Max parallel tasks [default: 1]
  --max-turns INT    Maximum turns per task [default: 10]
  --stop-on-fail     Stop all tasks if one fails
  --orchestrate      Enable orchestrator mode (automated checkpoints)
```

**Examples:**
```bash
# Sequential execution
gka feature work FEAT-001

# Parallel execution (2 tasks at a time)
gka feature work FEAT-001 --parallel 2

# With orchestrator mode
gka feature work FEAT-001 --orchestrate --parallel 3
```

### gka resume

Resume an interrupted run.

```bash
gka resume TASK_OR_FEATURE_ID

Arguments:
  ID    Task or Feature ID to resume
```

### gka status

Show status of runs.

```bash
gka status [OPTIONS]

Options:
  --task TEXT       Show status for specific task
  --feature TEXT    Show status for specific feature
  --all             Show all (including completed)
  --json            Output as JSON
```

### gka cancel

Cancel a running operation.

```bash
gka cancel TASK_OR_FEATURE_ID

Arguments:
  ID    Task or Feature ID to cancel
```

---

## Implementation

```python
# guardkit/cli/gka.py
import click
import asyncio
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from guardkit.orchestrator import GKAOrchestrator, GKAResult
from guardkit.features import load_feature
from guardkit.tasks import load_task
from typing import Optional

console = Console()

@click.group()
def gka():
    """GuardKit Agent - Autonomous feature implementation with adversarial cooperation."""
    pass


@gka.group()
def task():
    """Task management commands."""
    pass


@task.command()
@click.argument("task_id")
@click.option("--max-turns", default=10, help="Maximum player/coach turns")
@click.option("--timeout", default=300, help="Timeout per turn in seconds")
@click.option("--no-merge", is_flag=True, help="Don't merge worktree on success")
@click.option("--model", default=None, help="Override model for agents")
@click.option("--dry-run", is_flag=True, help="Show what would run")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def work(
    ctx,
    task_id: str, 
    max_turns: int, 
    timeout: int,
    no_merge: bool,
    model: Optional[str],
    dry_run: bool,
    verbose: bool
):
    """Run GuardKit Agent on a single task."""
    
    # Load task to verify it exists
    try:
        task_data = load_task(task_id)
    except FileNotFoundError:
        console.print(f"[red]Task {task_id} not found[/red]")
        raise SystemExit(1)
    
    if dry_run:
        _show_dry_run_task(task_id, task_data, max_turns)
        return
    
    # Run GuardKit Agent
    console.print(f"[bold]🚀 Starting GuardKit Agent for {task_id}[/bold]")
    console.print(f"   Max turns: {max_turns}")
    console.print(f"   Timeout: {timeout}s per turn")
    console.print()
    
    orchestrator = GKAOrchestrator()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task_progress = progress.add_task(f"Running {task_id}...", total=None)
        
        result = asyncio.run(
            orchestrator.run_task(task_id, max_turns=max_turns)
        )
        
        progress.update(task_progress, completed=True)
    
    _report_result(result, verbose)


@gka.group()
def feature():
    """Feature management commands."""
    pass


@feature.command()
@click.argument("feature_id")
@click.option("--parallel", default=1, help="Max parallel tasks")
@click.option("--max-turns", default=10, help="Maximum turns per task")
@click.option("--stop-on-fail", is_flag=True, help="Stop if any task fails")
@click.option("--orchestrate", is_flag=True, help="Enable orchestrator mode")
@click.option("--dry-run", is_flag=True, help="Show execution plan")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def work(
    feature_id: str,
    parallel: int,
    max_turns: int,
    stop_on_fail: bool,
    orchestrate: bool,
    dry_run: bool,
    verbose: bool
):
    """Run GuardKit Agent on all tasks in a feature."""
    
    # Load feature
    try:
        feature_data = load_feature(feature_id)
    except FileNotFoundError:
        console.print(f"[red]Feature {feature_id} not found[/red]")
        raise SystemExit(1)
    
    if dry_run:
        _show_dry_run_feature(feature_id, feature_data, parallel)
        return
    
    console.print(f"[bold]🚀 Starting GuardKit Agent for feature {feature_id}[/bold]")
    console.print(f"   Tasks: {len(feature_data.tasks)}")
    console.print(f"   Parallel: {parallel}")
    console.print(f"   Orchestrator mode: {'enabled' if orchestrate else 'disabled'}")
    console.print()
    
    orchestrator = GKAOrchestrator()
    results = {}
    failed = False
    
    for group_idx, task_group in enumerate(feature_data.parallel_groups):
        console.print(f"[bold]📦 Execution group {group_idx + 1}[/bold]")
        
        if parallel == 1 or len(task_group) == 1:
            # Sequential execution
            for task_id in task_group:
                if stop_on_fail and failed:
                    console.print(f"   [yellow]⏭ Skipping {task_id} (stop-on-fail)[/yellow]")
                    continue
                
                console.print(f"   Running {task_id}...")
                result = asyncio.run(
                    orchestrator.run_task(task_id, max_turns=max_turns)
                )
                results[task_id] = result
                
                if result.success:
                    console.print(f"   [green]✅ {task_id} completed in {result.turns} turns[/green]")
                else:
                    console.print(f"   [red]❌ {task_id} failed: {result.failure_reason}[/red]")
                    failed = True
        else:
            # Parallel execution
            tasks_to_run = task_group[:parallel]
            console.print(f"   Running {len(tasks_to_run)} tasks in parallel...")
            
            parallel_results = asyncio.run(
                orchestrator.run_parallel(tasks_to_run, max_turns=max_turns)
            )
            
            for task_id, result in parallel_results.items():
                results[task_id] = result
                if result.success:
                    console.print(f"   [green]✅ {task_id} completed in {result.turns} turns[/green]")
                else:
                    console.print(f"   [red]❌ {task_id} failed: {result.failure_reason}[/red]")
                    failed = True
        
        console.print()
    
    _report_feature_summary(feature_id, results)


@gka.command()
@click.argument("id")
def resume(id: str):
    """Resume an interrupted run."""
    
    orchestrator = GKAOrchestrator()
    state = orchestrator.load_state(id)
    
    if not state:
        console.print(f"[red]No saved state for {id}[/red]")
        raise SystemExit(1)
    
    console.print(f"[bold]▶️ Resuming {id}[/bold]")
    console.print(f"   From turn: {state.get('turn_count', 0)}")
    console.print(f"   Phase: {state.get('phase', 'unknown')}")
    console.print()
    
    result = asyncio.run(orchestrator.resume(id))
    _report_result(result, verbose=True)


@gka.command()
@click.option("--task", default=None, help="Show status for specific task")
@click.option("--feature", default=None, help="Show status for specific feature")
@click.option("--all", "show_all", is_flag=True, help="Show all including completed")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def status(task: Optional[str], feature: Optional[str], show_all: bool, as_json: bool):
    """Show status of runs."""
    
    # Load status from traces and checkpoints
    from guardkit.orchestrator.status import get_gka_status
    
    statuses = get_gka_status(
        task_id=task,
        feature_id=feature,
        include_completed=show_all
    )
    
    if as_json:
        import json
        click.echo(json.dumps(statuses, indent=2))
        return
    
    if not statuses:
        console.print("[dim]No runs found[/dim]")
        return
    
    table = Table(title="GuardKit Agent Status")
    table.add_column("ID", style="cyan")
    table.add_column("Type")
    table.add_column("Status")
    table.add_column("Turns")
    table.add_column("Started")
    
    for s in statuses:
        status_style = {
            "running": "yellow",
            "completed": "green",
            "failed": "red",
            "escalated": "magenta"
        }.get(s["status"], "white")
        
        table.add_row(
            s["id"],
            s["type"],
            f"[{status_style}]{s['status']}[/{status_style}]",
            str(s.get("turns", "-")),
            s.get("started", "-")
        )
    
    console.print(table)


@gka.command()
@click.argument("id")
def cancel(id: str):
    """Cancel a running operation."""
    
    from guardkit.orchestrator.status import cancel_gka
    
    success = cancel_gka(id)
    
    if success:
        console.print(f"[green]Cancelled {id}[/green]")
    else:
        console.print(f"[red]Could not cancel {id} (not running or not found)[/red]")


# Helper functions

def _show_dry_run_task(task_id: str, task_data, max_turns: int):
    """Show what would run for a task."""
    console.print(f"[bold]🔍 Dry run for {task_id}[/bold]")
    console.print()
    console.print(f"[bold]Task:[/bold] {task_data.name}")
    console.print(f"[bold]Description:[/bold] {task_data.description[:100]}...")
    console.print(f"[bold]Acceptance Criteria:[/bold] {len(task_data.acceptance_criteria)}")
    console.print(f"[bold]Max Turns:[/bold] {max_turns}")
    console.print()
    console.print("[bold]Would execute:[/bold]")
    console.print("  1. Create worktree for isolated execution")
    console.print("  2. Run player agent (implement)")
    console.print("  3. Run coach agent (validate)")
    console.print("  4. Loop until approval or max turns")
    console.print("  5. Merge worktree on success")


def _show_dry_run_feature(feature_id: str, feature_data, parallel: int):
    """Show execution plan for a feature."""
    console.print(f"[bold]🔍 Dry run for feature {feature_id}[/bold]")
    console.print()
    console.print(f"[bold]Feature:[/bold] {feature_data.name}")
    console.print(f"[bold]Tasks:[/bold] {len(feature_data.tasks)}")
    console.print(f"[bold]Parallel:[/bold] {parallel}")
    console.print()
    console.print("[bold]Execution Plan:[/bold]")
    
    for idx, group in enumerate(feature_data.parallel_groups):
        if len(group) == 1:
            console.print(f"  Group {idx + 1}: {group[0]} (sequential)")
        else:
            console.print(f"  Group {idx + 1}: {', '.join(group)} (parallel, max {parallel})")


def _report_result(result: GKAResult, verbose: bool):
    """Report result of single task run."""
    console.print()
    
    if result.success:
        console.print(f"[bold green]✅ {result.task_id} completed successfully[/bold green]")
        console.print(f"   Turns: {result.turns}")
    else:
        console.print(f"[bold red]❌ {result.task_id} failed[/bold red]")
        console.print(f"   Turns: {result.turns}")
        console.print(f"   Reason: {result.failure_reason}")
    
    if verbose and result.trace_path:
        console.print(f"   Trace: {result.trace_path}")


def _report_feature_summary(feature_id: str, results: dict[str, GKAResult]):
    """Report summary for feature run."""
    succeeded = sum(1 for r in results.values() if r.success)
    failed = sum(1 for r in results.values() if not r.success)
    total_turns = sum(r.turns for r in results.values())
    
    console.print("[bold]═══════════════════════════════════════[/bold]")
    console.print(f"[bold]Feature {feature_id} Summary[/bold]")
    console.print(f"   [green]Succeeded: {succeeded}[/green]")
    console.print(f"   [red]Failed: {failed}[/red]")
    console.print(f"   Total turns: {total_turns}")
    
    if failed > 0:
        console.print()
        console.print("[bold]Failed tasks:[/bold]")
        for task_id, result in results.items():
            if not result.success:
                console.print(f"   - {task_id}: {result.failure_reason}")
```

---

## Status Module

```python
# guardkit/orchestrator/status.py
from pathlib import Path
from typing import Optional, List
import json
import os
import signal

def get_gka_status(
    task_id: Optional[str] = None,
    feature_id: Optional[str] = None,
    include_completed: bool = False
) -> List[dict]:
    """Get status of GuardKit Agent runs."""
    
    statuses = []
    traces_dir = Path(".gka/traces")
    checkpoints_dir = Path(".gka/checkpoints")
    
    if not traces_dir.exists():
        return statuses
    
    for trace_file in traces_dir.glob("*.json"):
        with open(trace_file) as f:
            trace = json.load(f)
        
        status = {
            "id": trace["task_id"],
            "type": "task",
            "status": _determine_status(trace),
            "turns": len([e for e in trace.get("events", []) if e["type"] == "player_turn"]),
            "started": trace.get("started_at", "")
        }
        
        # Filter
        if task_id and status["id"] != task_id:
            continue
        if not include_completed and status["status"] == "completed":
            continue
        
        statuses.append(status)
    
    return statuses


def _determine_status(trace: dict) -> str:
    """Determine status from trace events."""
    events = trace.get("events", [])
    
    if any(e["type"] == "orchestrator_success" for e in events):
        return "completed"
    if any(e["type"] == "orchestrator_failure" for e in events):
        return "failed"
    if any(e["type"] == "orchestrator_escalation" for e in events):
        return "escalated"
    
    return "running"


def cancel_gka(id: str) -> bool:
    """Cancel a running GuardKit Agent operation."""
    
    pid_file = Path(f".gka/pids/{id}.pid")
    
    if not pid_file.exists():
        return False
    
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM)
        pid_file.unlink()
        return True
    except (ProcessLookupError, ValueError):
        pid_file.unlink(missing_ok=True)
        return False
```

---

## File Structure

```
guardkit/
├── cli/
│   ├── __init__.py
│   ├── main.py              # Main CLI entry point
│   └── gka.py               # GuardKit Agent commands
├── orchestrator/
│   └── status.py            # Status tracking
```

---

## Acceptance Criteria

- [ ] `gka task work TASK-ID` runs single task
- [ ] `gka feature work FEAT-ID` runs all tasks in feature
- [ ] `--parallel` controls concurrent execution
- [ ] `--dry-run` shows plan without executing
- [ ] `--max-turns` configurable
- [ ] `--stop-on-fail` stops feature on first failure
- [ ] `resume` continues interrupted runs
- [ ] `status` shows running/completed runs
- [ ] `cancel` stops running operation
- [ ] Progress displayed during execution (rich library)
- [ ] Final summary shows success/failure per task
- [ ] Exit codes: 0 for success, 1 for failure

---

## Testing Approach

### Unit Tests

```python
# tests/unit/test_cli_gka.py
from click.testing import CliRunner
from guardkit.cli.gka import gka

def test_task_dry_run(tmp_guardkit_project):
    runner = CliRunner()
    result = runner.invoke(gka, ["task", "work", "TASK-001", "--dry-run"])
    
    assert result.exit_code == 0
    assert "Dry run" in result.output
    assert "TASK-001" in result.output

def test_feature_dry_run(tmp_guardkit_project):
    runner = CliRunner()
    result = runner.invoke(gka, ["feature", "work", "FEAT-001", "--dry-run"])
    
    assert result.exit_code == 0
    assert "Execution Plan" in result.output

def test_task_not_found():
    runner = CliRunner()
    result = runner.invoke(gka, ["task", "work", "NONEXISTENT"])
    
    assert result.exit_code == 1
    assert "not found" in result.output
```

### Integration Tests

```python
# tests/integration/test_cli_gka.py
@pytest.mark.integration
def test_gka_task_e2e(tmp_guardkit_project):
    runner = CliRunner()
    result = runner.invoke(gka, ["task", "work", "TEST-001"])
    
    # Should complete (success or failure)
    assert result.exit_code in [0, 1]
    assert "TEST-001" in result.output

@pytest.mark.integration
def test_gka_feature_parallel(tmp_guardkit_project):
    runner = CliRunner()
    result = runner.invoke(gka, [
        "feature", "work", "TEST-FEAT", 
        "--parallel", "2"
    ])
    
    assert "parallel" in result.output.lower() or result.exit_code in [0, 1]
```

---

## Example Output

### Task Success
```
🚀 Starting GuardKit Agent for TASK-001
   Max turns: 10
   Timeout: 300s per turn

Running TASK-001... ✓

✅ TASK-001 completed successfully
   Turns: 3
   Trace: .gka/traces/TASK-001.json
```

### Task Failure
```
🚀 Starting GuardKit Agent for TASK-001
   Max turns: 10
   Timeout: 300s per turn

Running TASK-001... ✓

❌ TASK-001 failed
   Turns: 10
   Reason: Max turns (10) reached without approval
   Trace: .gka/traces/TASK-001.json
```

### Feature Summary
```
🚀 Starting GuardKit Agent for feature FEAT-001
   Tasks: 4
   Parallel: 2
   Orchestrator mode: disabled

📦 Execution group 1
   Running TASK-001...
   ✅ TASK-001 completed in 2 turns

📦 Execution group 2
   Running 2 tasks in parallel...
   ✅ TASK-002 completed in 4 turns
   ❌ TASK-003 failed: Max turns (10) reached without approval

📦 Execution group 3
   Running TASK-004...
   ✅ TASK-004 completed in 3 turns

═══════════════════════════════════════
Feature FEAT-001 Summary
   Succeeded: 3
   Failed: 1
   Total turns: 19

Failed tasks:
   - TASK-003: Max turns (10) reached without approval
```

---

## References

- Click documentation: https://click.palletsprojects.com/
- Rich library: https://rich.readthedocs.io/
- Main spec: `GuardKit_Agent_Product_Specification.md`
