# GuardKit Agent Phase 1: Kickoff Document (Updated)

> **Purpose**: Focused requirements for `/feature-plan` consumption. Updated to use LangChain DeepAgents.
> **Last Updated**: December 2025

---

## Overview

**Goal**: Add autonomous feature building to GuardKit using adversarial cooperation (player/coach agents) via **LangChain DeepAgents** and LangGraph.

**Key Change**: We now use DeepAgents (5.8k ⭐) as our foundation instead of building from scratch. This saves ~4-5 days while providing battle-tested infrastructure.

**Key Constraint**: GuardKit is a mix of Python code and Claude Code slash commands. Testing strategy must account for integration seams.

---

## Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| Framework | **DeepAgents** | Agent harness with middleware |
| Orchestration | **LangGraph** | State management, checkpointing |
| Coordination | **FilesystemMiddleware** | Agent communication (blackboard) |
| Subagents | **SubAgentMiddleware** | Player/Coach isolation |
| Approval | **HumanInTheLoopMiddleware** | Tool-level gates |
| Custom | **AdversarialLoopMiddleware** | Our innovation |

---

## Feature Summary

| Feature | Description | Effort | Status |
|---------|-------------|--------|--------|
| **F1** | Enhanced feature-plan | 2-3 days | Ready |
| **F2** | DeepAgents Infrastructure | 0.5 days | Ready |
| **F3** | Player Agent (SubAgent) | 1 day | Ready |
| **F4** | Coach Agent (SubAgent) | 1 day | Ready |
| **F5** | Orchestrator + Middleware | 2-3 days | Ready |
| **F6** | gka CLI | 1-2 days | Ready |
| ~~F7~~ | ~~Blackboard~~ | ~~2 days~~ | Superseded |

**Total**: 8-11 days (down from 12-17 days)

---

## Feature 1: Enhanced feature-plan Command

### Current State
- `/feature-plan` analyzes a feature and creates tasks
- Tasks are created as markdown files in `.guardkit/tasks/`
- Human manually runs `/task-work` for each task

### Required Changes

**1.1 Output Structure Enhancement**

The feature-plan should output a structured feature file that can be consumed by the orchestrator:

```yaml
# .guardkit/features/FEAT-001.yaml
id: FEAT-001
name: "User Authentication"
description: "Add OAuth2 authentication flow"
created: 2025-01-15T10:30:00Z
status: planned  # planned | in_progress | completed | failed

complexity: 7  # 1-10 scale
estimated_tasks: 4

tasks:
  - id: TASK-001
    name: "Create auth service skeleton"
    complexity: 3
    dependencies: []
    status: pending
    
  - id: TASK-002  
    name: "Implement OAuth2 flow"
    complexity: 5
    dependencies: [TASK-001]
    status: pending

orchestration:
  parallel_groups:
    - [TASK-001]           # Must complete first
    - [TASK-002, TASK-003] # Can run in parallel
    - [TASK-004]           # Final integration
```

**1.2 Dependency Analysis**
- Analyze task descriptions to identify dependencies
- Group independent tasks for parallel execution
- Output `parallel_groups` array showing execution order

**1.3 Complexity Scoring**
- Each task gets complexity score (1-10)
- Based on files modified, integration points, test requirements

**1.4 Backward Compatibility**
- Existing `/feature-plan` behavior unchanged by default
- New `--structured` flag outputs YAML format

### Acceptance Criteria
- [ ] `/feature-plan "description" --structured` outputs YAML feature file
- [ ] Feature file includes task dependencies
- [ ] Feature file includes parallel execution groups
- [ ] Each task has complexity score
- [ ] Existing task markdown files still created

---

## Feature 2: DeepAgents Infrastructure

### Purpose

Configure DeepAgents as the foundation. This replaces the custom Agent SDK we originally planned.

### Components

**2.1 Configuration**

```python
# guardkit/orchestrator/config.py
@dataclass
class GKAConfig:
    orchestrator_model: str = "anthropic:claude-sonnet-4-5-20250929"
    player_model: str = "anthropic:claude-3-5-haiku-20241022"
    coach_model: str = "anthropic:claude-sonnet-4-5-20250929"
    max_turns: int = 5
    coordination_path: str = "/coordination/"
    use_worktrees: bool = True
```

**2.2 Filesystem Backend**

```python
# guardkit/orchestrator/backends.py
def create_coordination_backend(persistent=True):
    def backend_factory(runtime):
        return CompositeBackend(
            default=StateBackend(runtime),
            routes={
                "/coordination/": StoreBackend(runtime),
                "/artifacts/": StoreBackend(runtime),
            }
        )
    return backend_factory
```

**2.3 Git Worktree Manager**

```python
# guardkit/orchestrator/worktrees.py
class WorktreeManager:
    def create(self, task_id: str) -> Worktree: ...
    def merge(self, task_id: str) -> bool: ...
    def cleanup(self, task_id: str): ...
```

### Acceptance Criteria
- [ ] `deepagents` package installed and importable
- [ ] Coordination backend routes paths correctly
- [ ] WorktreeManager creates/merges/cleans worktrees
- [ ] Checkpointer enables resume capability

---

## Feature 3: Player Agent (SubAgent)

### Purpose

Implementation-focused agent that writes code to satisfy requirements.

### Definition

```python
# guardkit/agents/player.py
def create_player_subagent(model="anthropic:claude-3-5-haiku-20241022"):
    return {
        "name": "player",
        "description": "Implementation agent that writes code",
        "system_prompt": PLAYER_INSTRUCTIONS,
        "tools": [run_tests, check_syntax, lint_file],
        "model": model,
    }
```

### Report Format

Player writes to `/coordination/player/turn_N/report.json`:

```json
{
  "task_id": "TASK-001",
  "turn": 1,
  "files_modified": ["src/auth/oauth.py"],
  "tests_written": ["tests/test_oauth.py"],
  "implementation_notes": "...",
  "concerns": []
}
```

### Acceptance Criteria
- [ ] SubAgent configuration is valid
- [ ] Player can be invoked via DeepAgents task tool
- [ ] Player writes reports to coordination filesystem
- [ ] Player tools work (run_tests, check_syntax)

---

## Feature 4: Coach Agent (SubAgent)

### Purpose

Validation-focused agent that reviews implementation against requirements.

### Definition

```python
# guardkit/agents/coach.py
def create_coach_subagent(model="anthropic:claude-sonnet-4-5-20250929"):
    return {
        "name": "coach",
        "description": "Validation agent that reviews implementation",
        "system_prompt": COACH_INSTRUCTIONS,
        "tools": [run_all_tests, diff_changes, check_coverage],
        "model": model,
    }
```

### Decision Format

Coach writes to `/coordination/coach/turn_N/decision.json`:

```json
{
  "task_id": "TASK-001",
  "turn": 1,
  "decision": "approve",  // or "feedback"
  "rationale": "...",
  "feedback_items": [],
  "severity": "minor"
}
```

### Acceptance Criteria
- [ ] SubAgent configuration is valid
- [ ] Coach reads Player reports from filesystem
- [ ] Coach writes decisions to filesystem
- [ ] Coach uses Sonnet for better reasoning

---

## Feature 5: Adversarial Orchestrator

### Purpose

Coordinate Player↔Coach loop using DeepAgents with custom middleware.

### AdversarialLoopMiddleware

```python
# guardkit/orchestrator/middleware.py
class AdversarialLoopMiddleware(AgentMiddleware):
    def __init__(self, player_name, coach_name, max_turns, coordination_path):
        ...
    
    @property
    def tools(self):
        return [
            start_adversarial_task,
            get_loop_status,
            complete_task,  # HITL gated
            escalate_task,  # HITL gated
        ]
    
    def modify_model_request(self, request, runtime):
        # Inject adversarial loop instructions
        ...
```

### Orchestrator Factory

```python
# guardkit/orchestrator/factory.py
def create_gka_orchestrator(config=None):
    return create_deep_agent(
        model=config.orchestrator_model,
        subagents=[player_subagent, coach_subagent],
        middleware=[AdversarialLoopMiddleware(...)],
        interrupt_on={
            "complete_task": {"allowed_decisions": ["approve", "reject"]},
            "escalate_task": {"allowed_decisions": ["approve", "reject"]},
        },
    )
```

### Acceptance Criteria
- [ ] AdversarialLoopMiddleware provides required tools
- [ ] Orchestrator invokes Player and Coach correctly
- [ ] Coordination happens through filesystem
- [ ] HITL gates work for complete/escalate
- [ ] Checkpointing enables resume

---

## Feature 6: gka CLI

### Commands

```bash
# Run single task
gka task work TASK-001 [--max-turns 5]

# Run all tasks in feature
gka feature work FEAT-001 [--parallel 2]

# Resume interrupted run
gka resume FEAT-001

# Check status
gka status [TASK-ID | FEAT-ID]
```

### Implementation

```python
# guardkit/cli/gka.py
@click.group()
def gka():
    """GuardKit Agent - Autonomous feature implementation."""
    pass

@gka.command()
@click.argument("task_id")
@click.option("--max-turns", default=5)
def task(task_id: str, max_turns: int):
    """Run GuardKit Agent on a single task."""
    orchestrator = GKAOrchestrator()
    result = orchestrator.run_task_sync(task_id, ...)
    display_result(result)
```

### Acceptance Criteria
- [ ] `gka task work TASK-ID` runs single task
- [ ] `gka feature work FEAT-ID` runs all tasks
- [ ] `--parallel` controls concurrent execution
- [ ] `resume` continues interrupted runs
- [ ] Progress displayed during execution

---

## Implementation Order

```
Week 1 (5 days):
├── Day 1-2: F1 Enhanced feature-plan
│   ├── DependencyAnalyzer
│   ├── ComplexityAnalyzer
│   └── YAML output with --structured
│
├── Day 3: F2 DeepAgents Infrastructure
│   ├── Install deepagents
│   ├── Configure backends
│   └── WorktreeManager
│
└── Day 4-5: F3 + F4 Player and Coach
    ├── Player SubAgent + instructions
    ├── Coach SubAgent + instructions
    └── Test subagent invocation

Week 2 (5 days):
├── Day 1-3: F5 Orchestrator
│   ├── AdversarialLoopMiddleware
│   ├── create_gka_orchestrator
│   └── GKAOrchestrator wrapper
│
└── Day 4-5: F6 CLI + Integration
    ├── CLI commands
    ├── Progress display
    └── End-to-end testing
```

**Total: ~10 days** (2 weeks)

---

## Dependency Graph

```
F1 (feature-plan) ─────────────────────────────────────┐
                                                        ↓
F2 (DeepAgents) ──┬──→ F3 (Player) ──→ F5 (Orchestrator) ──→ F6 (CLI)
                  │                      ↑
                  └──→ F4 (Coach) ───────┘
```

---

## Testing Approach

**Remember**: Bugs live in the integration seams, not the logic.

### For Each Feature

1. **Unit tests** for Python logic
2. **Contract verification** in agent instructions
3. **Trace logging** from day one
4. **Integration smoke tests** that actually run commands

### Key Integration Tests

```python
# tests/integration/test_gka_e2e.py

@pytest.mark.integration
async def test_gka_task_completes():
    """Actually run GuardKit Agent on a test task."""
    result = await run_cli(["gka", "task", "work", "TEST-001"])
    assert result.exit_code == 0

@pytest.mark.integration  
async def test_player_coach_loop_executes():
    """Verify player and coach both run."""
    result = await run_gka_task("TEST-001")
    # Check coordination filesystem for both reports
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Task completion rate (gka) | ≥70% without human intervention |
| Average turns per task | ≤4 |
| Coach approval accuracy | No false positives |
| Integration test coverage | 100% of seams tested |
| Time to complete Phase 1 | ≤2 weeks |

---

## What DeepAgents Gives Us (Free)

| Capability | DeepAgents Component |
|------------|---------------------|
| Planning | TodoListMiddleware |
| Coordination filesystem | FilesystemMiddleware |
| Context management | SummarizationMiddleware (170K tokens) |
| Subagent spawning | SubAgentMiddleware |
| Approval gates | HumanInTheLoopMiddleware |
| Checkpointing | LangGraph integration |

---

## What We Build (Our Innovation)

| Component | Purpose |
|-----------|---------|
| **AdversarialLoopMiddleware** | Player↔Coach loop control |
| **Enhanced feature-plan** | Structured YAML with dependencies |
| **WorktreeManager** | Git isolation for parallel tasks |
| **gka CLI** | User-facing commands |
| **Agent instructions** | Player and Coach prompts |

---

## References

- [DeepAgents GitHub](https://github.com/langchain-ai/deepagents) - 5.8k ⭐
- [DeepAgents Documentation](https://docs.langchain.com/oss/python/deepagents/overview)
- Full spec: `GuardKit_Agent_Product_Specification.md`
- Integration analysis: `DeepAgents_Integration_Analysis.md`
- Adversarial cooperation: Block AI Research paper
