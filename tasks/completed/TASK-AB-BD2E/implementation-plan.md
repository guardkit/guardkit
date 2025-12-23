# Implementation Plan: TASK-AB-BD2E - CLI Commands for AutoBuild Phase 1a

**Task ID**: TASK-AB-BD2E
**Wave**: 3
**Complexity**: 4/10 (Medium)
**Mode**: task-work (full quality gates)
**Estimated Duration**: 2-3 hours
**Dependencies**: TASK-AB-9869 (AutoBuildOrchestrator) ✅ COMPLETED

---

## 1. Overview

This task implements CLI commands for AutoBuild Phase 1a, providing command-line interfaces to the orchestration system implemented in TASK-AB-9869. The implementation extends the existing bash-based `guardkit` CLI with Python subcommands using Click framework for structured argument parsing and rich terminal output.

**Key Integration Points**:
- Extends existing `~/.agentecflow/bin/guardkit` bash wrapper
- Creates Python CLI module in `guardkit/cli/autobuild.py`
- Integrates with `AutoBuildOrchestrator` from Wave 2
- Uses Click framework for argument parsing (consistent with installer patterns)
- Provides rich terminal output for user feedback

**Architecture Decision**:
Use bash wrapper → Python CLI pattern (same as installer/scripts) for consistency with existing GuardKit CLI infrastructure.

---

## 2. Detailed Implementation Plan

### Phase 1: CLI Module Structure (30 minutes)

**Goal**: Create CLI module with Click command groups and option parsing.

**Steps**:

1. **Create `guardkit/cli/__init__.py`** (if not exists):
   ```python
   """GuardKit CLI package."""
   __version__ = "1.0.0"
   ```

2. **Create `guardkit/cli/main.py`**:
   - Click application entry point
   - Command groups: `autobuild`, `doctor`, `version`
   - Common options: `--verbose`, `--quiet`
   - Error handling and exit codes

3. **Create `guardkit/cli/autobuild.py`**:
   - Click command group for AutoBuild
   - Commands: `task`, `status`
   - Options: `--max-turns`, `--auto-merge`, `--model`
   - Integration with `AutoBuildOrchestrator`

**Deliverables**:
- 3 Python files created
- Click command structure defined
- No implementation logic yet (stubs only)

---

### Phase 2: `autobuild task` Command (60 minutes)

**Goal**: Implement `guardkit autobuild task TASK-XXX` command.

**Command Signature**:
```bash
guardkit autobuild task TASK-XXX [OPTIONS]

Options:
  --max-turns INTEGER     Maximum adversarial turns [default: 5]
  --auto-merge           Auto-merge on approval (REMOVED - worktree preserved)
  --model TEXT           Claude model to use [default: claude-sonnet-4-5-20250929]
  --verbose              Show detailed output
  --help                 Show this message and exit
```

**Implementation Steps**:

1. **Task File Loading** (10 min):
   ```python
   def load_task_file(task_id: str) -> Dict[str, Any]:
       """Load task markdown file from tasks/ directory."""
       task_path = Path("tasks/backlog") / f"{task_id}.md"
       if not task_path.exists():
           task_path = Path("tasks/in_progress") / f"{task_id}.md"
       # Parse frontmatter + content
       # Extract: requirements, acceptance_criteria
   ```

2. **Orchestrator Invocation** (20 min):
   ```python
   @click.command()
   @click.argument("task_id")
   @click.option("--max-turns", default=5, type=int)
   @click.option("--model", default="claude-sonnet-4-5-20250929")
   @click.option("--verbose", is_flag=True)
   def task(task_id: str, max_turns: int, model: str, verbose: bool):
       """Execute AutoBuild for a task."""
       # 1. Load task file
       task_data = load_task_file(task_id)

       # 2. Initialize orchestrator
       orchestrator = AutoBuildOrchestrator(
           repo_root=Path.cwd(),
           max_turns=max_turns,
       )

       # 3. Execute orchestration
       result = orchestrator.orchestrate(
           task_id=task_id,
           requirements=task_data["requirements"],
           acceptance_criteria=task_data["acceptance_criteria"],
       )

       # 4. Display results
       display_result(result, verbose=verbose)
   ```

3. **Result Display** (15 min):
   ```python
   def display_result(result: OrchestrationResult, verbose: bool = False):
       """Display orchestration result with Rich formatting."""
       console = Console()

       if result.success:
           console.print("[green]✅ Task completed successfully[/green]")
           console.print(f"Total turns: {result.total_turns}")
           console.print(f"Worktree: {result.worktree.path}")
       else:
           console.print("[red]❌ Task failed[/red]")
           console.print(f"Reason: {result.final_decision}")
           console.print(f"Error: {result.error}")

       if verbose:
           # Display turn-by-turn breakdown
           for turn in result.turn_history:
               console.print(f"Turn {turn.turn}: {turn.decision}")
   ```

4. **Error Handling** (15 min):
   - Task file not found → Exit code 1
   - Orchestration error → Exit code 2
   - Invalid arguments → Exit code 3
   - Graceful error messages with suggestions

**Deliverables**:
- `autobuild task` command functional
- Task file parsing working
- Orchestrator integration complete
- Rich terminal output
- Error handling comprehensive

---

### Phase 3: `autobuild status` Command (30 minutes)

**Goal**: Implement `guardkit autobuild status TASK-XXX` to show orchestration state.

**Command Signature**:
```bash
guardkit autobuild status TASK-XXX [OPTIONS]

Options:
  --verbose              Show detailed turn history
  --help                 Show this message and exit
```

**Implementation Steps**:

1. **Worktree State Detection** (15 min):
   ```python
   @click.command()
   @click.argument("task_id")
   @click.option("--verbose", is_flag=True)
   def status(task_id: str, verbose: bool):
       """Show AutoBuild status for a task."""
       # 1. Check if worktree exists
       worktree_manager = WorktreeManager(repo_root=Path.cwd())
       worktree = worktree_manager.find_by_task_id(task_id)

       if not worktree:
           console.print(f"[yellow]No AutoBuild worktree found for {task_id}[/yellow]")
           sys.exit(0)

       # 2. Load orchestration state (if saved)
       state = load_orchestration_state(task_id)

       # 3. Display status
       display_status(worktree, state, verbose=verbose)
   ```

2. **Status Display** (15 min):
   ```python
   def display_status(worktree: Worktree, state: Optional[Dict], verbose: bool):
       """Display worktree and orchestration status."""
       console.print(f"Task: {worktree.task_id}")
       console.print(f"Worktree: {worktree.path}")
       console.print(f"Branch: {worktree.branch}")

       if state:
           console.print(f"Status: {state['final_decision']}")
           console.print(f"Turns: {state['total_turns']}")

           if verbose:
               # Show turn history
               for turn in state["turn_history"]:
                   console.print(f"  Turn {turn['turn']}: {turn['decision']}")
   ```

**Deliverables**:
- `autobuild status` command functional
- Worktree detection working
- Status display informative

---

### Phase 4: Bash Wrapper Integration (15 minutes)

**Goal**: Update `~/.agentecflow/bin/guardkit` to support `autobuild` subcommand.

**Implementation**:

1. **Update guardkit bash script**:
   ```bash
   case "$1" in
       init)
           # ... existing init logic ...
           ;;
       autobuild)
           # Delegate to Python CLI
           shift  # Remove 'autobuild' from args
           python3 -m guardkit.cli.main autobuild "$@"
           ;;
       doctor)
           # ... existing doctor logic ...
           ;;
       *)
           print_help
           exit 1
           ;;
   esac
   ```

2. **Python module entry point**:
   - Ensure `guardkit/cli/main.py` has `if __name__ == "__main__":` block
   - Support `python3 -m guardkit.cli.main` invocation

**Deliverables**:
- Bash wrapper delegates to Python CLI
- Commands accessible via `guardkit autobuild task ...`
- Backward compatibility maintained

---

### Phase 5: Testing (45 minutes)

**Goal**: Comprehensive CLI testing with Click's CliRunner.

**Test Structure**:

1. **Unit Tests** (`tests/unit/test_cli_autobuild.py`):
   ```python
   from click.testing import CliRunner
   from guardkit.cli.autobuild import task, status

   def test_task_command_missing_task_id():
       """Test task command without task ID."""
       runner = CliRunner()
       result = runner.invoke(task, [])
       assert result.exit_code == 2  # Click missing argument

   def test_task_command_with_options():
       """Test task command with all options."""
       runner = CliRunner()
       result = runner.invoke(task, [
           "TASK-AB-001",
           "--max-turns", "3",
           "--model", "claude-opus-4-5-20251101",
           "--verbose",
       ])
       # Mock orchestrator to verify options passed

   def test_status_command_no_worktree():
       """Test status when no worktree exists."""
       runner = CliRunner()
       result = runner.invoke(status, ["TASK-AB-999"])
       assert result.exit_code == 0
       assert "No AutoBuild worktree found" in result.output
   ```

2. **Integration Tests** (`tests/integration/test_cli_e2e.py`):
   ```python
   def test_autobuild_task_e2e(tmp_path):
       """End-to-end test of autobuild task command."""
       # Setup: Create task file, mock worktree
       # Execute: Run CLI command
       # Assert: Orchestrator called, result displayed
   ```

3. **Mock Strategy**:
   - Mock `AutoBuildOrchestrator` for fast tests
   - Mock `WorktreeManager` for status tests
   - Use Click's `CliRunner` for isolated CLI testing
   - Verify exit codes, output format, option parsing

**Test Coverage Target**: ≥80% line coverage

**Deliverables**:
- 8-10 unit tests covering all commands and options
- 2-3 integration tests for E2E workflows
- Mock-based testing for fast execution
- Coverage report generated

---

### Phase 6: Documentation & Help Text (15 minutes)

**Goal**: Complete help text, examples, and documentation.

**Implementation**:

1. **Click Help Text**:
   ```python
   @click.command(help="""
   Execute AutoBuild orchestration for a task.

   This command creates an isolated worktree, runs the Player/Coach
   adversarial loop, and preserves the worktree for human review.

   Examples:

     guardkit autobuild task TASK-AB-001
     guardkit autobuild task TASK-AB-001 --max-turns 10 --verbose
   """)
   ```

2. **Error Messages**:
   - Clear, actionable error messages
   - Suggest next steps (e.g., "Run `guardkit autobuild status TASK-XXX` to check worktree")
   - Color-coded output (red for errors, yellow for warnings, green for success)

**Deliverables**:
- Help text for all commands
- Examples in docstrings
- Clear error messages

---

## 3. File Structure

### Files to Create

```
guardkit/
├── cli/
│   ├── __init__.py          # Package marker
│   ├── main.py              # Click application entry point (NEW)
│   └── autobuild.py         # AutoBuild command group (NEW)
└── orchestrator/
    └── autobuild.py         # (Already exists - dependency)

tests/
├── unit/
│   └── test_cli_autobuild.py    # CLI unit tests (NEW)
└── integration/
    └── test_cli_e2e.py          # E2E integration tests (NEW)

~/.agentecflow/bin/
└── guardkit                 # Bash wrapper (MODIFIED)
```

### File Responsibilities

| File | Lines | Responsibility |
|------|-------|----------------|
| `guardkit/cli/main.py` | 50-70 | Click app entry point, command groups |
| `guardkit/cli/autobuild.py` | 150-200 | AutoBuild commands (`task`, `status`) |
| `tests/unit/test_cli_autobuild.py` | 150-200 | CLI unit tests with mocks |
| `tests/integration/test_cli_e2e.py` | 50-80 | E2E integration tests |
| `~/.agentecflow/bin/guardkit` | +10 lines | Bash wrapper delegation |

**Total New Code**: ~400-550 lines
**Total Modified Code**: ~10 lines

---

## 4. Testing Strategy

### 4.1 Unit Testing Approach

**Tool**: Click's `CliRunner` for isolated CLI testing

**Test Categories**:

1. **Argument Parsing** (30% of tests):
   - Missing required arguments
   - Invalid option values
   - Help text display
   - Option combinations

2. **Command Execution** (40% of tests):
   - Task command with mocked orchestrator
   - Status command with mocked worktree manager
   - Verify options passed correctly
   - Error handling paths

3. **Output Formatting** (20% of tests):
   - Success output format
   - Error output format
   - Verbose vs normal output
   - Color-coded messages

4. **Exit Codes** (10% of tests):
   - Exit 0 on success
   - Exit 1 on task not found
   - Exit 2 on orchestration error
   - Exit 3 on invalid arguments

### 4.2 Integration Testing Approach

**Scenarios**:

1. **Happy Path**: `guardkit autobuild task TASK-AB-001` completes successfully
2. **Max Turns**: Task exceeds max turns, worktree preserved
3. **Status Check**: `guardkit autobuild status TASK-AB-001` shows state
4. **Error Path**: Invalid task ID, graceful error

**Mock Strategy**:
- Unit tests: Mock `AutoBuildOrchestrator`, `WorktreeManager`
- Integration tests: Use real components with test fixtures

### 4.3 Coverage Targets

| Component | Target | Rationale |
|-----------|--------|-----------|
| `guardkit/cli/autobuild.py` | 85% | CLI logic, all paths testable |
| `guardkit/cli/main.py` | 80% | Entry point, basic routing |
| Overall | 80% | GuardKit quality gate |

---

## 5. Quality Gates

### 5.1 Compilation Gate
```bash
python3 -m py_compile guardkit/cli/main.py
python3 -m py_compile guardkit/cli/autobuild.py
```
**Threshold**: 100% (must compile)

### 5.2 Test Pass Gate
```bash
pytest tests/unit/test_cli_autobuild.py -v
pytest tests/integration/test_cli_e2e.py -v
```
**Threshold**: 100% pass rate

### 5.3 Coverage Gate
```bash
pytest tests/ --cov=guardkit/cli --cov-report=term --cov-report=json
```
**Threshold**:
- Lines: ≥80%
- Branches: ≥75%

### 5.4 Manual Testing Gate

**Checklist**:
- [ ] `guardkit autobuild task --help` shows correct help text
- [ ] `guardkit autobuild task TASK-AB-001` creates worktree
- [ ] `guardkit autobuild task TASK-AB-001 --max-turns 3` respects option
- [ ] `guardkit autobuild status TASK-AB-001` shows worktree state
- [ ] Error: `guardkit autobuild task TASK-INVALID` shows clear message
- [ ] Exit codes correct (0 success, non-zero failure)

---

## 6. Dependencies & Integration

### 6.1 External Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| `click` | ≥8.0.0 | CLI framework |
| `rich` | ≥13.0.0 | Terminal formatting |
| `pyyaml` | ≥6.0 | Task file parsing |

**Installation**: Already in `pyproject.toml` (verify)

### 6.2 Internal Dependencies

| Component | Source | Status |
|-----------|--------|--------|
| `AutoBuildOrchestrator` | `guardkit/orchestrator/autobuild.py` | ✅ Implemented |
| `WorktreeManager` | `installer/core/lib/orchestrator/worktrees.py` | ✅ Implemented |
| `OrchestrationResult` | `guardkit/orchestrator/autobuild.py` | ✅ Implemented |

### 6.3 Integration Points

```
guardkit (bash)
    ↓
guardkit/cli/main.py (Click app)
    ↓
guardkit/cli/autobuild.py (Commands)
    ↓
guardkit/orchestrator/autobuild.py (Orchestrator)
    ↓
[WorktreeManager, AgentInvoker, ProgressDisplay]
```

---

## 7. Error Handling Strategy

### 7.1 CLI-Specific Errors

| Error | Exit Code | Message | Suggestion |
|-------|-----------|---------|------------|
| Task file not found | 1 | `Task {task_id} not found in tasks/` | `Check task ID and try again` |
| Invalid task ID format | 1 | `Invalid task ID format: {task_id}` | `Use format: TASK-XXX` |
| Orchestration failed | 2 | `AutoBuild failed: {error}` | `Check logs for details` |
| Missing dependencies | 3 | `Missing required package: {package}` | `Run: pip install {package}` |
| Permission error | 4 | `Permission denied: {path}` | `Check file permissions` |

### 7.2 Exception Mapping

```python
try:
    result = orchestrator.orchestrate(...)
except SetupPhaseError as e:
    console.print(f"[red]Setup failed: {e}[/red]")
    sys.exit(2)
except OrchestrationError as e:
    console.print(f"[red]Orchestration failed: {e}[/red]")
    sys.exit(2)
except FileNotFoundError as e:
    console.print(f"[red]Task file not found: {e}[/red]")
    sys.exit(1)
except Exception as e:
    console.print(f"[red]Unexpected error: {e}[/red]")
    sys.exit(3)
```

### 7.3 User-Friendly Messages

**Before** (raw exception):
```
FileNotFoundError: [Errno 2] No such file or directory: 'tasks/backlog/TASK-AB-999.md'
```

**After** (CLI wrapper):
```
❌ Task not found: TASK-AB-999

Searched locations:
  • tasks/backlog/TASK-AB-999.md
  • tasks/in_progress/TASK-AB-999.md

Suggestion: Run `guardkit task-status` to see available tasks
```

---

## 8. Risks & Mitigations

### Risk 1: Click Version Compatibility
**Likelihood**: Low
**Impact**: Medium (CLI may not work on older Click versions)
**Mitigation**: Pin `click>=8.0.0` in `pyproject.toml`, test on multiple versions

### Risk 2: Bash Wrapper Conflicts
**Likelihood**: Medium
**Impact**: Medium (existing `guardkit` commands may break)
**Mitigation**: Extensive testing of existing commands (`init`, `doctor`, `version`)

### Risk 3: Task File Parsing Edge Cases
**Likelihood**: Medium
**Impact**: Low (some tasks may fail to parse)
**Mitigation**: Robust YAML parsing with error handling, test with various task formats

### Risk 4: Exit Code Inconsistency
**Likelihood**: Low
**Impact**: Low (scripts may misinterpret results)
**Mitigation**: Document exit codes, test in CI/CD pipelines

### Risk 5: Rich Terminal Issues (No TTY)
**Likelihood**: Medium
**Impact**: Low (output may be garbled in non-interactive environments)
**Mitigation**: Detect TTY, use plain text output when not available

---

## 9. Success Criteria

### 9.1 Functional Requirements
- ✅ `guardkit autobuild task TASK-XXX` creates worktree and executes orchestration
- ✅ `guardkit autobuild status TASK-XXX` shows worktree state
- ✅ `--max-turns` option respected by orchestrator
- ✅ `--model` option passed to AgentInvoker
- ✅ `--verbose` shows detailed turn-by-turn output

### 9.2 Quality Requirements
- ✅ All tests passing (100% pass rate)
- ✅ Test coverage ≥80% (lines), ≥75% (branches)
- ✅ Help text complete and accurate
- ✅ Error messages clear and actionable

### 9.3 Integration Requirements
- ✅ Bash wrapper delegates correctly
- ✅ AutoBuildOrchestrator invoked with correct parameters
- ✅ OrchestrationResult displayed correctly
- ✅ Exit codes consistent with GuardKit standards

### 9.4 User Experience Requirements
- ✅ Commands intuitive and self-documenting
- ✅ Progress visible during orchestration
- ✅ Errors gracefully handled with suggestions
- ✅ Output formatted for readability (Rich library)

---

## 10. Estimated Timeline

| Phase | Duration | Deliverable |
|-------|----------|-------------|
| Phase 1: CLI Module Structure | 30 min | 3 Python files, Click setup |
| Phase 2: `autobuild task` | 60 min | Command functional, orchestrator integrated |
| Phase 3: `autobuild status` | 30 min | Status command functional |
| Phase 4: Bash Wrapper | 15 min | Wrapper updated, delegation working |
| Phase 5: Testing | 45 min | 8-10 tests, ≥80% coverage |
| Phase 6: Documentation | 15 min | Help text, examples complete |
| **Total** | **2h 45min** | **All Wave 3 acceptance criteria met** |

**Buffer**: +30 minutes for edge cases and manual testing
**Total Estimated**: **3 hours 15 minutes** (within 2-3 hour estimate)

---

## 11. Post-Implementation Validation

### 11.1 Manual Test Scenarios

1. **Simple Task** (1-2 turns):
   ```bash
   guardkit autobuild task TEST-SIMPLE
   # Expected: Completes in 1-2 turns, worktree preserved
   ```

2. **Complex Task** (3+ turns):
   ```bash
   guardkit autobuild task TEST-COMPLEX --max-turns 5
   # Expected: Multiple feedback iterations, approval or max-turns
   ```

3. **Status Check**:
   ```bash
   guardkit autobuild status TEST-SIMPLE
   # Expected: Shows worktree path, turn count, decision
   ```

4. **Error Scenario**:
   ```bash
   guardkit autobuild task TASK-INVALID
   # Expected: Exit 1, clear error message
   ```

### 11.2 Performance Benchmarks

| Scenario | Target | Measurement |
|----------|--------|-------------|
| Command startup | <500ms | Time to display help |
| Task file parse | <100ms | Load + parse task markdown |
| Orchestrator invoke | N/A | Depends on SDK (5-10 min) |
| Status display | <50ms | Query + render status |

### 11.3 Acceptance Signoff

**Wave 3 Complete When**:
- [ ] All functional requirements met
- [ ] All quality gates passed (100% tests, ≥80% coverage)
- [ ] Manual test scenarios passed
- [ ] Help text reviewed and approved
- [ ] Integration with Wave 2 (AutoBuildOrchestrator) verified
- [ ] Documentation updated in CLAUDE.md

---

## 12. Code Snippets

### Example: `guardkit/cli/autobuild.py` Structure

```python
"""AutoBuild CLI commands."""
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator, OrchestrationResult


console = Console()


@click.group()
def autobuild():
    """AutoBuild commands for adversarial task execution."""
    pass


@autobuild.command()
@click.argument("task_id")
@click.option("--max-turns", default=5, type=int, help="Maximum adversarial turns")
@click.option("--model", default="claude-sonnet-4-5-20250929", help="Claude model")
@click.option("--verbose", is_flag=True, help="Show detailed output")
def task(task_id: str, max_turns: int, model: str, verbose: bool):
    """Execute AutoBuild orchestration for a task."""
    try:
        # Load task file
        task_data = _load_task_file(task_id)

        # Initialize orchestrator
        orchestrator = AutoBuildOrchestrator(
            repo_root=Path.cwd(),
            max_turns=max_turns,
        )

        # Execute
        result = orchestrator.orchestrate(
            task_id=task_id,
            requirements=task_data["requirements"],
            acceptance_criteria=task_data["acceptance_criteria"],
        )

        # Display
        _display_result(result, verbose=verbose)
        sys.exit(0 if result.success else 2)

    except FileNotFoundError as e:
        console.print(f"[red]Task not found: {task_id}[/red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(3)


@autobuild.command()
@click.argument("task_id")
@click.option("--verbose", is_flag=True, help="Show detailed turn history")
def status(task_id: str, verbose: bool):
    """Show AutoBuild status for a task."""
    # Implementation here
    pass


def _load_task_file(task_id: str) -> dict:
    """Load and parse task markdown file."""
    # Implementation here
    pass


def _display_result(result: OrchestrationResult, verbose: bool = False):
    """Display orchestration result with Rich formatting."""
    # Implementation here
    pass
```

### Example: Test with Click CliRunner

```python
"""CLI unit tests."""
from click.testing import CliRunner
from guardkit.cli.autobuild import task, status


def test_task_command_success(mocker):
    """Test successful task execution."""
    # Mock orchestrator
    mock_result = mocker.MagicMock()
    mock_result.success = True
    mock_result.total_turns = 2

    mocker.patch("guardkit.cli.autobuild.AutoBuildOrchestrator.orchestrate", return_value=mock_result)
    mocker.patch("guardkit.cli.autobuild._load_task_file", return_value={"requirements": "...", "acceptance_criteria": []})

    # Execute
    runner = CliRunner()
    result = runner.invoke(task, ["TASK-AB-001"])

    # Assert
    assert result.exit_code == 0
    assert "✅" in result.output or "success" in result.output.lower()
```

---

**Plan Created**: 2025-12-23
**Next Steps**: Begin Phase 1 implementation (CLI module structure)
**Estimated Completion**: 3 hours from start
