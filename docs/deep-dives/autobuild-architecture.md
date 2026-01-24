# AutoBuild Architecture Deep-Dive

**Version**: 1.0.0
**Last Updated**: 2026-01-24
**Audience**: Contributors, advanced users, integrators
**Document Type**: Technical Architecture Reference

---

## Table of Contents

1. [Architectural Overview](#architectural-overview)
2. [Module Structure](#module-structure)
3. [Player-Coach Pattern Implementation](#player-coach-pattern-implementation)
4. [Quality Gate Delegation (Option B)](#quality-gate-delegation-option-b)
5. [State Machine and Transitions](#state-machine-and-transitions)
6. [Escape Hatch Pattern](#escape-hatch-pattern)
7. [Pre-Loop Design Phase](#pre-loop-design-phase)
8. [Feature Orchestration Engine](#feature-orchestration-engine)
9. [Worktree Management](#worktree-management)
10. [Integration Points](#integration-points)

---

## Architectural Overview

AutoBuild implements an **adversarial cooperation** pattern using the Claude Agent SDK, based on [Block AI's "Adversarial Cooperation in Code Synthesis" research](https://block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf) (December 2025). This approach, called **dialectical autocoding**, uses a structured coach-player feedback loop where independent verification prevents the "premature success declaration" failure mode common in single-agent systems.

The architecture separates concerns across three layers:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 1: CLI INTERFACE                                                       │
│ guardkit/cli/autobuild.py                                                    │
│                                                                              │
│ Commands: task, feature, status, complete                                    │
│ Responsibilities: Argument parsing, environment setup, user interaction     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 2: ORCHESTRATION                                                       │
│ guardkit/orchestrator/                                                       │
│                                                                              │
│ Components:                                                                  │
│ - agent_invoker.py: Claude SDK wrapper, agent creation                      │
│ - quality_gates/: Pre-loop, task-work interface, coach validator           │
│ - features/: Feature YAML parsing, wave management                          │
│                                                                              │
│ Responsibilities: Workflow coordination, state management, iteration        │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ LAYER 3: EXECUTION                                                           │
│ Claude Agent SDK                                                             │
│                                                                              │
│ Agents: Player (full tools), Coach (read-only)                              │
│ Responsibilities: LLM interaction, tool execution, file operations          │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Separation of Concerns**: Player implements, Coach validates, neither can do both
2. **Independent Verification**: Coach ignores Player's self-reports and verifies directly (key Block research insight)
3. **Tool Asymmetry**: Different tool permissions enforce role boundaries
4. **Delegation over Duplication**: Reuse task-work quality gates (100% code reuse)
5. **Isolation**: Git worktrees protect main branch from experimental changes
6. **Escape Hatch**: Max iterations prevent infinite loops

---

## Module Structure

```
guardkit/
├── cli/
│   ├── main.py                    # CLI entry point, command groups
│   └── autobuild.py               # AutoBuild commands (task, feature, status, complete)
│
├── orchestrator/
│   ├── agent_invoker.py           # Claude SDK wrapper, agent lifecycle
│   │
│   ├── quality_gates/
│   │   ├── pre_loop.py            # Pre-loop design phases (optional)
│   │   ├── task_work_interface.py # task-work delegation, profile selection
│   │   └── coach_validator.py     # Quality gate evaluation (replacing LLM Coach)
│   │
│   └── features/
│       ├── feature_parser.py      # Feature YAML parsing
│       ├── wave_manager.py        # Wave-based task orchestration
│       └── state_tracker.py       # Feature/task state persistence
│
└── models/
    ├── task.py                    # Task data model
    ├── feature.py                 # Feature data model
    └── quality_report.py          # Quality gate results model
```

### Key Files

| File | Responsibility |
|------|----------------|
| [autobuild.py](../../guardkit/cli/autobuild.py) | CLI commands, argument parsing |
| [agent_invoker.py](../../guardkit/orchestrator/agent_invoker.py) | SDK integration, agent creation |
| [pre_loop.py](../../guardkit/orchestrator/quality_gates/pre_loop.py) | Design phase delegation |
| [task_work_interface.py](../../guardkit/orchestrator/quality_gates/task_work_interface.py) | Quality gate delegation |

---

## Player-Coach Pattern Implementation

### Role Definition

```python
# Player Agent Configuration
PLAYER_TOOLS = [
    "Bash",           # Full command execution
    "Read",           # File reading
    "Write",          # File creation
    "Edit",           # File modification
    "Glob",           # File pattern matching
    "Grep",           # Content search
    "TodoWrite",      # Task tracking
]

# Coach Agent Configuration (Read-Only)
COACH_TOOLS = [
    "Bash",           # Read-only (test execution only)
    "Read",           # File reading
    "Glob",           # File pattern matching
    "Grep",           # Content search
]
```

### Dialectical Loop Implementation

```python
def run_adversarial_loop(
    task_id: str,
    max_turns: int = 5,
    enable_pre_loop: bool = False
) -> AutoBuildResult:
    """
    Execute Player-Coach adversarial loop.

    Flow:
    1. Optional pre-loop design phase
    2. For each turn (up to max_turns):
       a. Player implements (task-work --implement-only)
       b. Coach validates (quality gate check)
       c. If approved, break loop
       d. If feedback, Player continues
    3. Return result (approved or blocked)
    """

    # Pre-loop design phase (optional)
    if enable_pre_loop:
        design_result = pre_loop.run_design_phases(task_id)
        if not design_result.success:
            return AutoBuildResult.blocked(design_result.error)

    # Adversarial loop
    for turn in range(1, max_turns + 1):
        # Player turn: Implement
        player_result = invoke_player(task_id, previous_feedback)

        # Coach turn: Validate
        coach_result = invoke_coach(task_id, player_result)

        if coach_result.approved:
            return AutoBuildResult.approved(turn, player_result)

        previous_feedback = coach_result.feedback

    # Max turns reached - Escape Hatch
    return AutoBuildResult.blocked_max_turns(max_turns)
```

### Agent Invocation

The `agent_invoker.py` module wraps the Claude Agent SDK:

```python
from claude_agent_sdk import Agent, create_agent

class AgentInvoker:
    """Wrapper for Claude Agent SDK with GuardKit-specific configuration."""

    def __init__(self, sdk_timeout: int = 300):
        self.sdk_timeout = sdk_timeout

    def create_player_agent(self, worktree_path: Path) -> Agent:
        """Create Player agent with full tool access."""
        return create_agent(
            name="autobuild-player",
            tools=PLAYER_TOOLS,
            working_directory=str(worktree_path),
            timeout=self.sdk_timeout,
            system_prompt=PLAYER_SYSTEM_PROMPT,
        )

    def create_coach_agent(self, worktree_path: Path) -> Agent:
        """Create Coach agent with read-only tool access."""
        return create_agent(
            name="autobuild-coach",
            tools=COACH_TOOLS,
            working_directory=str(worktree_path),
            timeout=self.sdk_timeout,
            system_prompt=COACH_SYSTEM_PROMPT,
        )
```

---

## Quality Gate Delegation (Option B)

AutoBuild implements **Option B** from the Ralph Wiggum architectural review: delegation to task-work rather than reimplementing quality gates.

### Why Delegation?

| Approach | Code Reuse | Consistency | Maintenance |
|----------|-----------|-------------|-------------|
| Option A (Reimplement) | 0% | Risk of drift | Double maintenance |
| **Option B (Delegate)** | **100%** | **Guaranteed** | **Single codebase** |

### Delegation Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PLAYER AGENT                                                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  1. Receive task with acceptance criteria                                    │
│  2. Invoke: /task-work TASK-XXX --implement-only --mode=tdd                 │
│                                                                              │
│     ┌─────────────────────────────────────────────────────────────────┐     │
│     │ TASK-WORK EXECUTION (within Player's SDK session)               │     │
│     │                                                                 │     │
│     │ Phase 3: Implementation                                         │     │
│     │   └── Stack-specific agent (python-api-specialist, etc.)       │     │
│     │                                                                 │     │
│     │ Phase 4: Testing                                                │     │
│     │   └── Test orchestrator runs pytest/vitest/etc.                │     │
│     │                                                                 │     │
│     │ Phase 4.5: Test Enforcement Loop                                │     │
│     │   └── Auto-fix (up to 3 attempts), then fail                   │     │
│     │                                                                 │     │
│     │ Phase 5: Code Review                                            │     │
│     │   └── code-reviewer agent (SOLID/DRY/YAGNI)                    │     │
│     └─────────────────────────────────────────────────────────────────┘     │
│                                                                              │
│  3. Report results to Coach                                                  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Task-Work Interface

The `task_work_interface.py` module selects appropriate quality gate profiles:

```python
# Quality Gate Profiles by task_type
QUALITY_PROFILES = {
    "scaffolding": {
        "coverage_threshold": 0,      # No coverage for scaffolding
        "require_tests": False,
        "phases": [3],                # Implementation only
    },
    "feature": {
        "coverage_threshold": 80,
        "require_tests": True,
        "phases": [3, 4, 4.5, 5],    # Full implementation + testing
    },
    "testing": {
        "coverage_threshold": 80,
        "require_tests": True,
        "phases": [4, 4.5],          # Testing phases only
    },
    "documentation": {
        "coverage_threshold": 0,
        "require_tests": False,
        "phases": [3],               # Implementation only
    },
}

def get_profile(task_type: str) -> dict:
    """Select quality gate profile based on task type."""
    return QUALITY_PROFILES.get(task_type, QUALITY_PROFILES["feature"])
```

---

## State Machine and Transitions

### Task States

```
┌────────────┐     ┌─────────────────┐     ┌───────────────┐     ┌───────────┐
│  BACKLOG   │────▶│  IN_PROGRESS    │────▶│   IN_REVIEW   │────▶│ COMPLETED │
└────────────┘     └─────────────────┘     └───────────────┘     └───────────┘
                          │                        │
                          │                        │
                          ▼                        ▼
                   ┌────────────┐          ┌────────────┐
                   │  BLOCKED   │          │  BLOCKED   │
                   └────────────┘          └────────────┘
```

### AutoBuild-Specific States

```python
class AutoBuildState(Enum):
    """AutoBuild execution states."""

    PENDING = "pending"           # Task queued, not started
    PRE_LOOP = "pre_loop"         # Running design phases
    PLAYER_TURN = "player_turn"   # Player implementing
    COACH_TURN = "coach_turn"     # Coach validating
    APPROVED = "approved"         # Coach approved, ready for review
    BLOCKED = "blocked"           # Max turns or quality gate failure
    COMPLETED = "completed"       # Merged to main
```

### State Persistence

State is persisted to `.guardkit/state/` for resume capability:

```json
{
  "task_id": "TASK-AUTH-001",
  "feature_id": "FEAT-A1B2",
  "state": "player_turn",
  "turn": 2,
  "max_turns": 5,
  "worktree_path": ".guardkit/worktrees/FEAT-A1B2",
  "branch": "autobuild/FEAT-A1B2",
  "started_at": "2026-01-24T10:30:00Z",
  "last_updated": "2026-01-24T10:45:00Z",
  "player_results": [...],
  "coach_feedback": [...]
}
```

---

## Escape Hatch Pattern

The **Escape Hatch Pattern** prevents infinite loops by enforcing a maximum iteration count.

### Implementation

```python
class EscapeHatch:
    """
    Escape Hatch Pattern implementation.

    From Anthropic research: "Escape hatches provide a controlled way
    to exit when the AI gets stuck, rather than looping forever or
    requiring manual intervention."
    """

    def __init__(self, max_turns: int = 5):
        self.max_turns = max_turns
        self.current_turn = 0

    def check(self) -> bool:
        """Check if escape hatch should trigger."""
        return self.current_turn >= self.max_turns

    def on_escape(self, task_id: str, results: list) -> AutoBuildResult:
        """
        Generate blocked report when escape hatch triggers.

        The blocked report provides:
        1. Summary of all attempts
        2. Recurring issues identified
        3. Suggested manual interventions
        """
        return AutoBuildResult(
            status="blocked",
            reason="max_turns_reached",
            turns_completed=self.current_turn,
            blocked_report=self._generate_blocked_report(results),
        )

    def _generate_blocked_report(self, results: list) -> dict:
        """Analyze attempts and generate actionable report."""
        return {
            "total_attempts": len(results),
            "recurring_issues": self._identify_recurring_issues(results),
            "last_feedback": results[-1].coach_feedback if results else None,
            "suggested_actions": self._suggest_interventions(results),
        }
```

### Blocked Report Example

```yaml
blocked_report:
  total_attempts: 5
  recurring_issues:
    - "Test coverage below 80% (consistently ~65%)"
    - "Missing edge case tests for error handling"
  last_feedback:
    - "Add tests for AuthService.refresh_token error paths"
    - "Coverage at 67%, needs 80%"
  suggested_actions:
    - "Manually add tests for edge cases"
    - "Review test coverage report at coverage/index.html"
    - "Consider simplifying AuthService implementation"
```

---

## Pre-Loop Design Phase

The pre-loop phase runs design phases (2-2.8) before the adversarial loop when tasks need upfront planning.

### When Pre-Loop Runs

| Scenario | Pre-Loop Default | Override |
|----------|-----------------|----------|
| `feature-build` from `/feature-plan` | Disabled | `--enable-pre-loop` |
| `feature-build` with minimal specs | Disabled | `--enable-pre-loop` |
| `task-build` standalone | Enabled | `--no-pre-loop` |

### Pre-Loop Implementation

```python
class PreLoopQualityGates:
    """
    Pre-loop design phases (2-2.8).

    Delegates to task-work --design-only for:
    - Phase 2: Implementation Planning
    - Phase 2.5A: Pattern Suggestion
    - Phase 2.5B: Architectural Review
    - Phase 2.7: Complexity Evaluation
    - Phase 2.8: Human Checkpoint (auto-approved)
    """

    def run(self, task_id: str) -> PreLoopResult:
        """Execute pre-loop design phases."""

        # Delegate to task-work --design-only
        result = invoke_task_work(
            task_id,
            flags=["--design-only"],
            auto_approve_checkpoint=True,
        )

        if not result.success:
            return PreLoopResult.failed(result.error)

        return PreLoopResult(
            plan=result.plan,
            complexity=result.complexity,
            patterns=result.patterns,
        )
```

---

## Feature Orchestration Engine

For features with multiple tasks, the orchestration engine manages wave-based execution.

### Wave Concept

Tasks within a feature are organized into **waves** based on dependencies:

```yaml
# .guardkit/features/FEAT-A1B2.yaml
feature:
  id: FEAT-A1B2
  name: User Authentication

tasks:
  - id: TASK-AUTH-001
    wave: 1
    parallel_group: "wave-1"
    dependencies: []

  - id: TASK-AUTH-002
    wave: 1
    parallel_group: "wave-1"
    dependencies: []

  - id: TASK-AUTH-003
    wave: 2
    parallel_group: "wave-2"
    dependencies: [TASK-AUTH-001, TASK-AUTH-002]
```

### Wave Manager Implementation

```python
class WaveManager:
    """
    Manages wave-based task orchestration.

    Waves execute sequentially; tasks within a wave
    can execute in parallel (via Conductor worktrees).
    """

    def __init__(self, feature: Feature):
        self.feature = feature
        self.waves = self._organize_waves(feature.tasks)

    def _organize_waves(self, tasks: list) -> dict[int, list]:
        """Group tasks by wave number."""
        waves = {}
        for task in tasks:
            wave = task.wave or 1
            waves.setdefault(wave, []).append(task)
        return waves

    def get_next_wave(self) -> list | None:
        """Get tasks for next incomplete wave."""
        for wave_num in sorted(self.waves.keys()):
            tasks = self.waves[wave_num]
            if not all(t.status == "completed" for t in tasks):
                return tasks
        return None

    def execute_wave(self, wave_tasks: list) -> WaveResult:
        """
        Execute all tasks in a wave.

        In Conductor mode: Tasks run in parallel
        In standard mode: Tasks run sequentially
        """
        results = []
        for task in wave_tasks:
            result = run_adversarial_loop(task.id)
            results.append(result)

            # If any task blocks, stop wave
            if result.status == "blocked":
                return WaveResult.partial(results)

        return WaveResult.complete(results)
```

---

## Worktree Management

All AutoBuild work occurs in isolated git worktrees.

### Worktree Lifecycle

```
1. CREATE
   ├── Create branch: autobuild/TASK-XXX
   ├── Create worktree: .guardkit/worktrees/TASK-XXX
   └── Copy virtual environment (if exists)

2. EXECUTE
   ├── Player/Coach loop in worktree
   ├── All changes committed to worktree branch
   └── State persisted to .guardkit/state/

3. REVIEW (Human)
   ├── Worktree preserved after completion
   ├── Human reviews: git diff main
   └── Human decides: merge or discard

4. CLEANUP (Optional)
   ├── guardkit autobuild complete TASK-XXX
   ├── Merges to main (if approved)
   └── Removes worktree
```

### Worktree Implementation

```python
class WorktreeManager:
    """Manages git worktrees for AutoBuild isolation."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.worktrees_dir = base_path / ".guardkit" / "worktrees"

    def create_worktree(self, task_id: str) -> Path:
        """Create isolated worktree for task."""
        branch_name = f"autobuild/{task_id}"
        worktree_path = self.worktrees_dir / task_id

        # Create branch from current HEAD
        subprocess.run([
            "git", "branch", branch_name
        ], check=True)

        # Create worktree
        subprocess.run([
            "git", "worktree", "add",
            str(worktree_path),
            branch_name
        ], check=True)

        return worktree_path

    def cleanup_worktree(self, task_id: str, merge: bool = True):
        """Remove worktree, optionally merging changes."""
        worktree_path = self.worktrees_dir / task_id
        branch_name = f"autobuild/{task_id}"

        if merge:
            # Merge to main
            subprocess.run([
                "git", "checkout", "main"
            ], check=True)
            subprocess.run([
                "git", "merge", branch_name
            ], check=True)

        # Remove worktree
        subprocess.run([
            "git", "worktree", "remove", str(worktree_path)
        ], check=True)

        # Delete branch
        subprocess.run([
            "git", "branch", "-d" if merge else "-D", branch_name
        ], check=True)
```

---

## Integration Points

### Claude Agent SDK

```python
# Required: pip install guardkit-py[autobuild]
from claude_agent_sdk import Agent, create_agent, run_agent

# Agent creation with GuardKit configuration
agent = create_agent(
    name="autobuild-player",
    tools=PLAYER_TOOLS,
    working_directory=str(worktree_path),
    timeout=sdk_timeout,
    system_prompt=PLAYER_SYSTEM_PROMPT,
    model="claude-sonnet-4-20250514",  # Default model
)

# Execute agent with prompt
result = run_agent(agent, prompt)
```

### Task-Work Command

```bash
# Player delegates to task-work
/task-work TASK-XXX --implement-only --mode=tdd

# Pre-loop delegates to task-work
/task-work TASK-XXX --design-only
```

### Conductor Integration

```bash
# Conductor creates worktrees automatically
conductor workspace TASK-XXX

# GuardKit detects Conductor and uses existing worktree
guardkit autobuild task TASK-XXX
```

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GUARDKIT_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `GUARDKIT_SDK_TIMEOUT` | `300` | Claude SDK timeout in seconds |
| `GUARDKIT_MAX_TURNS` | `5` | Default max iterations for adversarial loop |

### CLI Flags

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--max-turns` | int | 5 | Maximum Player-Coach iterations |
| `--sdk-timeout` | int | 300 | Claude SDK operation timeout |
| `--verbose` | bool | false | Enable detailed output |
| `--resume` | bool | false | Resume interrupted execution |
| `--enable-pre-loop` | bool | false | Enable pre-loop design phases |
| `--no-pre-loop` | bool | false | Disable pre-loop for task-build |
| `--mode` | str | "tdd" | Development mode (tdd, standard) |

---

## Further Reading

### Research

- [Block AI: Adversarial Cooperation in Code Synthesis](https://block.xyz/documents/adversarial-cooperation-in-code-synthesis.pdf) - Foundational research on dialectical autocoding
- [Hegelion (GitHub)](https://github.com/Hmbown/Hegelion) - Open-source player-coach implementation based on Block's g3 agent

### GuardKit Documentation

- [AutoBuild Workflow Guide](../guides/autobuild-workflow.md) - User-focused documentation
- [GuardKit Workflow Guide](../guides/guardkit-workflow.md) - Core task-work phases
- [CLI vs Claude Code Comparison](../guides/cli-vs-claude-code.md) - Choosing your interface
- [Ralph Wiggum Review](../../.claude/reviews/TASK-REV-RW01-review-report.md) - Architectural decision record

---

**Version**: 1.0.0 | **License**: MIT
