---
id: TASK-REV-FB01
title: "Plan: Implement /feature-build command with dialectical autocoding"
status: review_complete
task_type: review
created: 2025-12-24T00:00:00Z
updated: 2025-12-26T00:00:00Z
priority: high
tags: [autobuild, dialectical-autocoding, player-coach, adversarial-cooperation, feature-build, claude-agent-sdk]
complexity: 8
decision_required: false
review_results:
  mode: architectural
  depth: standard
  score: 78
  findings_count: 5
  recommendations_count: 6
  decision: implement
  report_path: .claude/reviews/TASK-REV-FB01-review-report.md
  completed_at: 2025-12-26T00:00:00Z
implementation_tasks:
  - tasks/backlog/feature-build/TASK-AB-CLI-implement-autobuild-command.md
  - tasks/backlog/feature-build/TASK-FB-W4-testing-docs.md
related_research:
  - "Block AI Research: Adversarial Cooperation in Code Synthesis (December 2025)"
  - "g3 implementation: https://github.com/dhanji/g3"
  - "Claude Agent SDK documentation: https://platform.claude.com/docs/en/agent-sdk/overview"
  - "Claude Agent SDK Python reference: https://platform.claude.com/docs/en/agent-sdk/python"
  - "Claude Agent SDK Subagents: https://platform.claude.com/docs/en/agent-sdk/subagents"
revision_history:
  - version: 1.0
    date: 2025-12-24
    change: "Initial design using Task tool"
  - version: 2.0
    date: 2025-12-24
    change: "Revised to use Claude Agent SDK for true fresh context per turn"
---

# Plan: Implement /feature-build command with dialectical autocoding

## Overview

Design and implement a `/feature-build` command that implements **dialectical autocoding** (Player-Coach adversarial cooperation pattern) using the **Claude Agent SDK** for true fresh context per turn, integrated with GuardKit's proven `/task-work` quality gates.

**Key Architectural Decision (v2.0)**: Use Claude Agent SDK's `query()` function instead of Task tool. Each `query()` call creates a genuinely fresh session, providing the context isolation required for dialectical autocoding.

## Background Context

### The Problem with Current AI Coding

From the Block AI Research paper "Adversarial Cooperation in Code Synthesis":

> "Today's AI coding assistants primarily operate in what we term the 'vibe coding' model—chat-style interactions that provide code suggestions, explanations, or simple fixes based on immediate context."

Key limitations:
- **Anchoring**: Limited ability to maintain coherency on larger tasks
- **Refinement**: Systematic improvement is patchy, edge-case handling uneven
- **Completion**: Success states are open-ended, require human instruction
- **Complexity**: Weak ability to systematically approach multi-faceted problems

### The Dialectical Autocoding Solution

The g3 paper introduces a structured dialogue between two specialized agents:

```
┌─────────────────────────────────────────────────────────────┐
│                    DIALECTICAL LOOP                         │
│                                                             │
│   PLAYER                              COACH                 │
│   • Implement                         • Review              │
│   • Create          ──your work──►    • Test                │
│   • Execute         ◄──feedback───    • Critique            │
│   • Iterate                           • Approve             │
│                                                             │
│                      WORKSPACE                              │
│         Bounds: Max Turns, Context Windows, Requirements    │
└─────────────────────────────────────────────────────────────┘
```

**Key Innovation**: Fresh context per turn prevents context pollution while Coach feedback provides focused guidance.

### Why This Matters for GuardKit

GuardKit already has:
- ✅ Proven quality gates (Phase 2.5 Architectural Review, Phase 4.5 Test Enforcement)
- ✅ `autobuild-player` and `autobuild-coach` agent definitions
- ✅ Worktree isolation infrastructure
- ✅ AutoBuildOrchestrator with AgentInvoker pattern (ready for SDK integration)

**Gap**: The existing orchestrator has a `NotImplementedError` placeholder for SDK integration. We need to:
1. Replace placeholder with actual Claude Agent SDK calls
2. Create `/feature-build` command to expose this capability

## Requirements

### Functional Requirements

1. **FR-1**: Single command to execute full dialectical autocoding loop
   ```bash
   /feature-build TASK-XXX [--max-turns=5] [--model=sonnet]
   ```

2. **FR-2**: Fresh agent context per turn via Task tool invocation
   - Each Player turn = new Task tool invocation with fresh context
   - Each Coach turn = new Task tool invocation with fresh context (read-only)

3. **FR-3**: Player agent integrates `/task-work` quality gates
   - Phase 2: Implementation Planning
   - Phase 2.5: Architectural Review (SOLID/DRY/YAGNI)
   - Phase 3: Implementation
   - Phase 4: Testing with coverage enforcement

4. **FR-4**: Coach agent performs independent validation
   - Runs tests independently (doesn't trust Player's claims)
   - Validates requirements compliance
   - Provides specific, actionable feedback or approves

5. **FR-5**: Worktree isolation for safe experimentation
   - Creates git worktree for task
   - All changes isolated until approval
   - Preserves worktree for human review on failure

6. **FR-6**: Bounded execution
   - Maximum turns (default: 5, configurable)
   - Clear termination conditions (approval, max turns, error)

7. **FR-7**: Human checkpoint integration
   - Respects complexity-based checkpoints from `/task-work`
   - Can pause for human review if complexity ≥ 7

### Non-Functional Requirements

1. **NFR-1**: Uses Claude Agent SDK (`pip install claude-agent-sdk`) for true fresh context
2. **NFR-2**: Testable via Python unit tests with SDK mocks
3. **NFR-3**: Progress visibility via structured output and streaming messages
4. **NFR-4**: State persistence for resume capability
5. **NFR-5**: Hooks for permission control (Coach read-only, Player full access)

## Technical Design

### Architecture: Claude Agent SDK with Python Orchestrator

```
guardkit feature-build TASK-XXX --max-turns=5
    │
    ├─→ Phase 0: Setup (Python CLI)
    │     ├─→ Load task requirements from tasks/*/TASK-XXX.md
    │     ├─→ Create worktree: .guardkit/worktrees/TASK-XXX/
    │     └─→ Initialize state in task frontmatter
    │
    └─→ Dialectical Loop (Python orchestrator):
          │
          ├─→ PLAYER TURN (SDK query() - FRESH CONTEXT)
          │     │
          │     ├─→ query(prompt=requirements + feedback, options=player_options)
          │     ├─→ Each query() = NEW session, no context pollution
          │     ├─→ Player executes quality gates:
          │     │     ├─→ Phase 2: Planning
          │     │     ├─→ Phase 2.5: Architectural Review
          │     │     ├─→ Phase 3: Implementation
          │     │     └─→ Phase 4: Testing
          │     └─→ Streams progress via async iterator
          │
          └─→ COACH TURN (SDK query() - FRESH CONTEXT, READ-ONLY)
                │
                ├─→ query(prompt=requirements + player_output, options=coach_options)
                ├─→ Coach options restrict tools: ["Read", "Bash", "Grep", "Glob"]
                ├─→ Coach validates independently:
                │     ├─→ Runs tests (doesn't trust Player)
                │     ├─→ Checks requirements compliance
                │     └─→ Reviews code quality
                └─→ Decision (structured JSON output):
                      │
                      ├─→ {"decision": "approve"} → Exit loop, SUCCESS
                      │     └─→ Merge worktree to main branch
                      │
                      └─→ {"decision": "feedback", "issues": [...]} → Next Player turn
```

### Why Claude Agent SDK = True Fresh Context

From the official documentation:

> "When you start a new query, the SDK automatically creates a session... Each call to `query()` starts fresh with no memory of previous interactions."

**Key SDK features for dialectical autocoding:**

| Feature | Benefit for Player-Coach |
|---------|-------------------------|
| `query()` fresh sessions | Each turn is isolated, no context pollution |
| `allowed_tools` restriction | Coach is read-only (no Write/Edit) |
| `cwd` option | Both agents work in worktree directory |
| `permission_mode` | Control tool execution permissions |
| Streaming output | Real-time progress visibility |
| `output_format` | Structured JSON for Coach decisions |

### Python Implementation

```python
# guardkit/orchestrator/sdk_orchestrator.py
import asyncio
from claude_agent_sdk import query, ClaudeAgentOptions

class DialecticalOrchestrator:
    """Orchestrates Player-Coach dialectical loop using Claude Agent SDK."""

    def __init__(self, task_id: str, max_turns: int = 5):
        self.task_id = task_id
        self.max_turns = max_turns
        self.worktree_path = None

    async def orchestrate(self, requirements: str, acceptance_criteria: list[str]) -> OrchestrationResult:
        """Run the full dialectical loop."""

        # Setup worktree
        self.worktree_path = await self._create_worktree()

        feedback = None
        for turn in range(1, self.max_turns + 1):
            # PLAYER TURN - Fresh context via query()
            player_result = await self._player_turn(
                requirements=requirements,
                acceptance_criteria=acceptance_criteria,
                feedback=feedback,
                turn=turn
            )

            # COACH TURN - Fresh context, read-only
            coach_result = await self._coach_turn(
                requirements=requirements,
                acceptance_criteria=acceptance_criteria,
                player_output=player_result,
                turn=turn
            )

            if coach_result.decision == "approve":
                return OrchestrationResult(success=True, turns=turn)

            feedback = coach_result.feedback

        return OrchestrationResult(success=False, reason="max_turns_exceeded")

    async def _player_turn(self, requirements: str, acceptance_criteria: list[str],
                           feedback: str | None, turn: int) -> PlayerResult:
        """Execute Player turn with fresh context."""

        prompt = self._build_player_prompt(requirements, acceptance_criteria, feedback)

        player_options = ClaudeAgentOptions(
            allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
            cwd=self.worktree_path,
            permission_mode="acceptEdits",  # Player can modify files
            system_prompt=PLAYER_SYSTEM_PROMPT,
            setting_sources=["project"],  # Load CLAUDE.md for quality gates
        )

        result_text = ""
        async for message in query(prompt=prompt, options=player_options):
            if hasattr(message, "result"):
                result_text = message.result
            # Stream progress to console
            self._display_progress(message, "Player", turn)

        return PlayerResult(output=result_text, turn=turn)

    async def _coach_turn(self, requirements: str, acceptance_criteria: list[str],
                          player_output: PlayerResult, turn: int) -> CoachResult:
        """Execute Coach turn with fresh context, read-only."""

        prompt = self._build_coach_prompt(requirements, acceptance_criteria, player_output)

        coach_options = ClaudeAgentOptions(
            allowed_tools=["Read", "Bash", "Glob", "Grep"],  # NO Write/Edit
            cwd=self.worktree_path,
            permission_mode="bypassPermissions",  # Read-only, no prompts
            system_prompt=COACH_SYSTEM_PROMPT,
            output_format={  # Structured JSON output
                "type": "json_schema",
                "schema": COACH_DECISION_SCHEMA
            }
        )

        result_json = None
        async for message in query(prompt=prompt, options=coach_options):
            if hasattr(message, "result"):
                result_json = json.loads(message.result)
            self._display_progress(message, "Coach", turn)

        return CoachResult(
            decision=result_json["decision"],
            feedback=result_json.get("feedback"),
            issues=result_json.get("issues", [])
        )
```

### Coach Decision Schema (Structured Output)

```python
COACH_DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["approve", "feedback"]
        },
        "summary": {
            "type": "string",
            "description": "Brief summary of validation result"
        },
        "test_results": {
            "type": "object",
            "properties": {
                "passed": {"type": "boolean"},
                "coverage": {"type": "number"},
                "failures": {"type": "array", "items": {"type": "string"}}
            }
        },
        "issues": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "severity": {"type": "string", "enum": ["must_fix", "should_fix", "nice_to_have"]},
                    "category": {"type": "string"},
                    "description": {"type": "string"},
                    "file": {"type": "string"},
                    "suggestion": {"type": "string"}
                }
            }
        },
        "feedback": {
            "type": "string",
            "description": "Detailed feedback for Player (if decision=feedback)"
        }
    },
    "required": ["decision", "summary"]
}
```

### State Management (Simplified)

Per architectural review, use **task frontmatter as single source of truth**:

```yaml
# tasks/in_progress/TASK-XXX.md
---
id: TASK-XXX
status: in_progress
feature_build:
  current_turn: 2
  max_turns: 5
  worktree_path: .guardkit/worktrees/TASK-XXX
  started_at: 2025-12-24T10:00:00Z
  turns:
    - turn: 1
      player_summary: "Implemented OAuth flow with tests"
      coach_decision: feedback
      feedback: "Missing token refresh edge case"
      timestamp: 2025-12-24T10:05:00Z
    - turn: 2
      player_summary: "Added refresh token handling"
      coach_decision: approve
      timestamp: 2025-12-24T10:12:00Z
---
```

**Benefits over separate state.json:**
- Single source of truth (no sync issues)
- Git-trackable state
- Human-readable in task file
- Resume via frontmatter parsing

### Integration with Existing Components

| Component | Role in /feature-build |
|-----------|------------------------|
| `DialecticalOrchestrator` | **NEW** - Python class using Claude Agent SDK |
| `claude-agent-sdk` | **NEW** - `query()` for fresh context per turn |
| `WorktreeManager` | Creates/manages isolated git worktrees |
| `TaskLoader` | Loads task requirements and acceptance criteria |
| Quality gates | Embedded in Player system prompt |
| `autobuild-player.md` | Player behavior instructions (loaded as system prompt) |
| `autobuild-coach.md` | Coach behavior instructions (loaded as system prompt) |

### CLI Command

```python
# guardkit/cli/feature_build.py
import click
from guardkit.orchestrator.sdk_orchestrator import DialecticalOrchestrator

@click.command()
@click.argument("task_id")
@click.option("--max-turns", default=5, type=int, help="Maximum dialectical turns")
@click.option("--model", default="claude-sonnet-4-5", help="Claude model to use")
@click.option("--verbose", is_flag=True, help="Show detailed turn output")
def feature_build(task_id: str, max_turns: int, model: str, verbose: bool):
    """
    Execute dialectical autocoding for a task.

    Uses Player-Coach adversarial cooperation pattern with fresh context
    per turn via Claude Agent SDK.

    Examples:
        guardkit feature-build TASK-A3F8
        guardkit feature-build TASK-A3F8 --max-turns=10 --verbose
    """
    import asyncio

    orchestrator = DialecticalOrchestrator(
        task_id=task_id,
        max_turns=max_turns,
        model=model,
        verbose=verbose
    )

    # Load task
    task_data = TaskLoader.load_task(task_id)

    # Run orchestration
    result = asyncio.run(orchestrator.orchestrate(
        requirements=task_data["requirements"],
        acceptance_criteria=task_data["acceptance_criteria"]
    ))

    # Display result
    if result.success:
        click.echo(f"✅ Task completed in {result.turns} turn(s)")
        click.echo(f"   Worktree: {result.worktree_path}")
    else:
        click.echo(f"❌ Task failed: {result.reason}")
        click.echo(f"   Worktree preserved for review: {result.worktree_path}")
```

## Acceptance Criteria

- [ ] `guardkit feature-build TASK-XXX` executes complete Player-Coach loop
- [ ] Each turn uses Claude Agent SDK `query()` for true fresh context
- [ ] Player agent implements with quality gates (via system prompt)
- [ ] Coach agent validates independently (read-only tools, runs tests)
- [ ] Coach returns structured JSON decision (approve/feedback)
- [ ] Loop terminates on: approval, max turns, or error
- [ ] Worktree created and isolated from main branch
- [ ] State persisted in task frontmatter for resume capability
- [ ] Progress output streams turn-by-turn status
- [ ] Human checkpoint respected for complexity ≥ 7 tasks
- [ ] Unit tests with mocked SDK validate orchestration logic
- [ ] Integration tests validate full workflow

## Implementation Approach

### Files to Create/Modify

1. **NEW**: `guardkit/orchestrator/sdk_orchestrator.py`
   - `DialecticalOrchestrator` class using Claude Agent SDK
   - `query()` calls for Player and Coach turns
   - Streaming progress display
   - State persistence to frontmatter

2. **NEW**: `guardkit/cli/feature_build.py`
   - Click command for `guardkit feature-build`
   - CLI argument parsing
   - Rich console output

3. **MODIFY**: `guardkit/cli/main.py`
   - Register `feature_build` command

4. **MODIFY**: `.claude/agents/autobuild-player.md`
   - Enhance with quality gate instructions
   - Define structured output format

5. **MODIFY**: `.claude/agents/autobuild-coach.md`
   - Clarify read-only permissions
   - Define JSON decision schema

6. **NEW**: `guardkit/orchestrator/prompts.py`
   - `PLAYER_SYSTEM_PROMPT` with quality gates
   - `COACH_SYSTEM_PROMPT` with validation criteria
   - `COACH_DECISION_SCHEMA` for structured output

7. **NEW**: `tests/unit/test_sdk_orchestrator.py`
   - Unit tests with mocked `query()` calls
   - Test turn loop logic
   - Test state persistence

8. **NEW**: `tests/integration/test_feature_build_e2e.py`
   - End-to-end tests
   - Scenarios: single-turn approval, multi-turn feedback, max turns

9. **MODIFY**: `pyproject.toml`
   - Add `claude-agent-sdk` dependency

10. **MODIFY**: `CLAUDE.md`
    - Document `guardkit feature-build` command
    - Usage examples and troubleshooting

### Estimated Complexity: 7/10 (reduced from 8)

**Factors**:
- SDK provides clean abstraction (simpler than custom orchestration)
- Structured output eliminates parsing complexity
- Single state file simplifies persistence
- Existing WorktreeManager/TaskLoader reusable

**Wave Breakdown**:

| Wave | Scope | Hours | Dependencies |
|------|-------|-------|--------------|
| 1 | SDK orchestrator + basic loop | 4-5h | claude-agent-sdk |
| 2 | CLI command + progress display | 2-3h | Wave 1 |
| 3 | State persistence + resume | 2-3h | Wave 2 |
| 4 | Testing + documentation | 3-4h | Wave 3 |
| **Total** | | **11-15h** | |

## Related Work

- **g3 implementation**: https://github.com/dhanji/g3 (Rust-based, uses external SDK)
- **TASK-AB-2D16**: AutoBuild integration tests (completed)
- **TASK-AB-BD2E**: CLI commands for AutoBuild (completed)
- **TASK-AB-9869**: AutoBuildOrchestrator (completed, but uses external SDK pattern)

## Decision Points (Resolved)

### Decision 1: How does Player execute quality gates?
**Resolution**: Via system prompt instructions (not direct `/task-work` invocation)

**Rationale**:
- `/task-work` is a slash command, not a programmatic API
- System prompt embeds quality gate requirements
- Player follows instructions naturally
- Simpler than trying to invoke slash commands programmatically

### Decision 2: How to handle human checkpoints mid-loop?
**Resolution**: Remove from MVP (YAGNI)

**Rationale**:
- Upfront complexity checkpoint exists in `/task-work`
- Adds state complexity without proven need
- Worktree preservation enables post-hoc review
- Can add later if user feedback demands it

### Decision 3: Should Coach provide structured feedback?
**Resolution**: Yes, via `output_format` JSON schema

**Rationale**:
- SDK supports structured JSON output natively
- Enables reliable parsing of Coach decisions
- Provides actionable feedback (must_fix, should_fix, nice_to_have)
- Already designed in `COACH_DECISION_SCHEMA`

## Prerequisites

Before implementation:

1. **Install Claude Agent SDK**:
   ```bash
   pip install claude-agent-sdk
   ```

2. **Set API key**:
   ```bash
   export ANTHROPIC_API_KEY=your-api-key
   ```

3. **Verify Claude Code is installed** (SDK runtime dependency):
   ```bash
   which claude
   ```

## Next Steps

After review approval:
1. Add `claude-agent-sdk` to `pyproject.toml`
2. Implement Wave 1: SDK orchestrator + basic loop
3. Implement Wave 2: CLI command + progress display
4. Implement Wave 3: State persistence + resume
5. Implement Wave 4: Testing + documentation

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SDK API changes | Pin version in pyproject.toml |
| Rate limiting | Add exponential backoff |
| Long-running tasks | Support `--resume` flag |
| Coach doesn't approve | Max turns limit + worktree preservation |
| Network failures | Retry logic with state persistence |
