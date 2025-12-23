# Phase 1a: GuardKit Extension with Adversarial Cooperation

> **Purpose**: Quick path to autonomous feature building within Claude Code ecosystem
> **Approach**: Extend GuardKit with Claude Agents SDK + Player/Coach pattern
> **Effort**: 1-2 weeks
> **Dependency**: Claude Max subscription (existing)

---

## Strategic Context

### Two-Phase Approach

```
Phase 1a (THIS DOCUMENT) - 1-2 weeks
├── Extend GuardKit with /feature-build command
├── Use Claude Agents SDK directly
├── Prototype Player/Coach adversarial loop
├── Validate pattern before larger investment
└── Immediate value with existing subscription

Phase 1b/2 (DeepAgents docs) - 3-4 weeks
├── Standalone LangGraph/DeepAgents product (gka CLI)
├── Replicate GuardKit functionality
├── Add Memory MCP, job-specific context
├── Build UI, break vendor lock-in
└── Informed by Phase 1a learnings
```

### Why Phase 1a First?

1. **Faster validation** - Test adversarial pattern in ~1-2 weeks vs 3-4 weeks
2. **Lower risk** - If pattern doesn't work, minimal investment lost
3. **Leverage existing work** - GuardKit's template-create, agent-enhance already working
4. **Immediate value** - Use it while building standalone product
5. **Informed design** - Real usage shapes Phase 1b architecture

---

## What We're Building

### New Capability

A `/feature-build` command that:

1. Takes a task from `/feature-plan` output
2. Runs Player agent to implement
3. Runs Coach agent to validate
4. Iterates until approved or max turns
5. Merges approved changes

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GuardKit (Existing)                          │
├─────────────────────────────────────────────────────────────────┤
│  .claude/commands/           .claude/agents/                    │
│  ├── feature-plan.md         ├── *.md (existing agents)        │
│  ├── task-work.md            ├── gka-player.md (NEW)           │
│  ├── task-create.md          └── gka-coach.md (NEW)            │
│  └── feature-build.md (NEW)                                     │
├─────────────────────────────────────────────────────────────────┤
│                 NEW: Python Orchestrator                        │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  guardkit/cli/feature_build.py                            │ │
│  │  ├── Loads task from .guardkit/tasks/                     │ │
│  │  ├── Creates git worktree for isolation                   │ │
│  │  ├── Invokes Player via Claude Agent SDK                  │ │
│  │  ├── Invokes Coach via Claude Agent SDK                   │ │
│  │  ├── Loops until approved or max turns                    │ │
│  │  └── Merges on approval                                   │ │
│  └───────────────────────────────────────────────────────────┘ │
├─────────────────────────────────────────────────────────────────┤
│                    Claude Agent SDK                             │
│  ├── query(prompt="/gka-player ...", options)                  │
│  └── query(prompt="/gka-coach ...", options)                   │
└─────────────────────────────────────────────────────────────────┘
```

### Key Insight: Separate Agent Invocations

Each turn uses **fresh Claude Agent SDK sessions**:

```python
# Turn 1: Player implements
player_result = await query(
    prompt=f"/gka-player {task_id}",
    options=player_options
)

# Turn 1: Coach validates
coach_result = await query(
    prompt=f"/gka-coach {task_id} --turn 1",
    options=coach_options
)

# If feedback, Turn 2: Player iterates
if coach_result.decision == "feedback":
    player_result = await query(
        prompt=f"/gka-player {task_id} --feedback '{coach_result.feedback}'",
        options=player_options
    )
```

This gives us:
- **Fresh context** each turn (no pollution)
- **Separate models** possible (Haiku for Player, Sonnet for Coach)
- **Clear boundaries** between implementation and validation

---

## Components to Build

### 1. Player Agent Definition

**File**: `.claude/agents/gka-player.md`

```markdown
# GuardKit Agent Player

You are the Player agent in an adversarial cooperation system. Your role is to 
implement code that satisfies the given task requirements.

## Your Focus
- Write clean, working code
- Create tests that verify functionality
- Follow existing project conventions
- Document your changes

## Output Format
After implementing, create a report file at:
`.guardkit/gka/{task_id}/player_turn_{n}.json`

{
  "files_modified": ["path/to/file.py"],
  "tests_written": ["tests/test_feature.py"],
  "implementation_notes": "What you did and why",
  "concerns": ["Any uncertainties"]
}

## Guidelines
- Read the task requirements carefully
- Check existing code patterns before implementing
- Write tests alongside implementation
- If stuck, document what you tried in concerns
```

### 2. Coach Agent Definition

**File**: `.claude/agents/gka-coach.md`

```markdown
# GuardKit Agent Coach

You are the Coach agent in an adversarial cooperation system. Your role is to 
critically validate the Player's implementation against requirements.

## Your Focus
- Verify all requirements are met
- Run tests and check they pass
- Review code quality
- Identify gaps or issues

## Validation Checklist
Before deciding, verify:
- [ ] All acceptance criteria met
- [ ] Tests exist and pass
- [ ] Code follows project conventions
- [ ] No obvious bugs or security issues

## Decision
Write your decision to:
`.guardkit/gka/{task_id}/coach_turn_{n}.json`

If APPROVING:
{
  "decision": "approve",
  "rationale": "Why this implementation is complete",
  "quality_notes": "Optional observations"
}

If providing FEEDBACK:
{
  "decision": "feedback",
  "issues": [
    {
      "severity": "must_fix",
      "description": "What's wrong",
      "suggestion": "How to fix"
    }
  ]
}

## Critical Rules
- NEVER approve incomplete implementations
- Be specific in feedback - vague feedback wastes iterations
- Run the tests yourself, don't trust the Player's report
```

### 3. Python Orchestrator

**File**: `guardkit/cli/feature_build.py`

```python
"""
Feature Build CLI - Adversarial cooperation for autonomous feature building.

Uses Claude Agent SDK to orchestrate Player/Coach loop within GuardKit.
"""
import click
import asyncio
import json
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from claude_code_sdk import query, ClaudeCodeOptions

@dataclass
class FeatureBuildConfig:
    max_turns: int = 5
    player_model: str = "claude-sonnet-4-5-20250929"  # or haiku for cost
    coach_model: str = "claude-sonnet-4-5-20250929"
    use_worktree: bool = True
    auto_merge: bool = False  # Require confirmation

@dataclass
class TurnResult:
    turn: int
    player_report: dict
    coach_decision: dict
    
    @property
    def approved(self) -> bool:
        return self.coach_decision.get("decision") == "approve"
    
    @property
    def feedback(self) -> Optional[str]:
        if self.coach_decision.get("decision") == "feedback":
            return json.dumps(self.coach_decision.get("issues", []))
        return None


class FeatureBuildOrchestrator:
    """Orchestrates Player/Coach adversarial loop."""
    
    def __init__(self, project_path: str, config: FeatureBuildConfig = None):
        self.project_path = Path(project_path)
        self.config = config or FeatureBuildConfig()
        self.gka_dir = self.project_path / ".guardkit" / "gka"
        
    async def run_task(self, task_id: str) -> dict:
        """Run adversarial loop on a single task."""
        
        # Setup
        task_dir = self.gka_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Create worktree if enabled
        worktree_path = self._create_worktree(task_id) if self.config.use_worktree else self.project_path
        
        turns = []
        current_feedback = None
        
        for turn in range(1, self.config.max_turns + 1):
            click.echo(f"\n{'='*60}")
            click.echo(f"Turn {turn}/{self.config.max_turns}")
            click.echo(f"{'='*60}")
            
            # Player turn
            click.echo("\n🎮 Player implementing...")
            player_report = await self._run_player(
                task_id, 
                turn, 
                worktree_path,
                feedback=current_feedback
            )
            
            # Coach turn
            click.echo("\n🏀 Coach validating...")
            coach_decision = await self._run_coach(
                task_id,
                turn,
                worktree_path
            )
            
            result = TurnResult(
                turn=turn,
                player_report=player_report,
                coach_decision=coach_decision
            )
            turns.append(result)
            
            # Check outcome
            if result.approved:
                click.echo("\n✅ Coach APPROVED!")
                if self.config.auto_merge or click.confirm("Merge changes?"):
                    self._merge_worktree(task_id)
                    click.echo("🎉 Changes merged!")
                return {"status": "approved", "turns": turn, "results": turns}
            
            # Prepare feedback for next turn
            current_feedback = result.feedback
            click.echo(f"\n📝 Coach provided feedback, iterating...")
        
        # Max turns reached
        click.echo(f"\n⚠️ Max turns ({self.config.max_turns}) reached without approval")
        return {"status": "max_turns", "turns": self.config.max_turns, "results": turns}
    
    async def _run_player(
        self, 
        task_id: str, 
        turn: int, 
        working_dir: Path,
        feedback: Optional[str] = None
    ) -> dict:
        """Execute Player agent via Claude Agent SDK."""
        
        prompt = f"/gka-player {task_id} --turn {turn}"
        if feedback:
            prompt += f" --feedback '{feedback}'"
        
        options = ClaudeCodeOptions(
            cwd=str(working_dir),
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            permission_mode="acceptEdits",
            max_turns=30,
            model=self.config.player_model,
        )
        
        async for message in query(prompt=prompt, options=options):
            if message.type == "assistant":
                # Could stream output here
                pass
        
        # Read player report
        report_path = working_dir / ".guardkit" / "gka" / task_id / f"player_turn_{turn}.json"
        if report_path.exists():
            return json.loads(report_path.read_text())
        return {"error": "No player report found"}
    
    async def _run_coach(
        self,
        task_id: str,
        turn: int,
        working_dir: Path
    ) -> dict:
        """Execute Coach agent via Claude Agent SDK."""
        
        prompt = f"/gka-coach {task_id} --turn {turn}"
        
        options = ClaudeCodeOptions(
            cwd=str(working_dir),
            allowed_tools=["Read", "Bash", "Grep", "Glob"],  # No Write - read-only validation
            permission_mode="default",
            max_turns=20,
            model=self.config.coach_model,
        )
        
        async for message in query(prompt=prompt, options=options):
            if message.type == "assistant":
                pass
        
        # Read coach decision
        decision_path = working_dir / ".guardkit" / "gka" / task_id / f"coach_turn_{turn}.json"
        if decision_path.exists():
            return json.loads(decision_path.read_text())
        return {"error": "No coach decision found", "decision": "feedback"}
    
    def _create_worktree(self, task_id: str) -> Path:
        """Create isolated git worktree for task."""
        import subprocess
        
        worktree_base = self.project_path / ".guardkit" / "worktrees"
        worktree_path = worktree_base / task_id
        branch_name = f"gka/{task_id}"
        
        if not worktree_path.exists():
            worktree_base.mkdir(parents=True, exist_ok=True)
            subprocess.run(["git", "branch", branch_name], cwd=self.project_path, capture_output=True)
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path), branch_name],
                cwd=self.project_path,
                check=True
            )
        
        return worktree_path
    
    def _merge_worktree(self, task_id: str):
        """Merge worktree changes back to main."""
        import subprocess
        
        branch_name = f"gka/{task_id}"
        subprocess.run(["git", "checkout", "main"], cwd=self.project_path, check=True)
        subprocess.run(["git", "merge", branch_name], cwd=self.project_path, check=True)


# CLI Commands
@click.group()
def feature_build():
    """Autonomous feature building with adversarial cooperation."""
    pass

@feature_build.command()
@click.argument("task_id")
@click.option("--max-turns", default=5, help="Maximum Player/Coach iterations")
@click.option("--auto-merge", is_flag=True, help="Auto-merge on approval")
def task(task_id: str, max_turns: int, auto_merge: bool):
    """Run feature-build on a single task."""
    config = FeatureBuildConfig(max_turns=max_turns, auto_merge=auto_merge)
    orchestrator = FeatureBuildOrchestrator(os.getcwd(), config)
    
    result = asyncio.run(orchestrator.run_task(task_id))
    
    if result["status"] == "approved":
        click.echo(f"\n✅ Task {task_id} completed in {result['turns']} turns")
    else:
        click.echo(f"\n❌ Task {task_id} did not complete")

@feature_build.command()
@click.argument("feature_id")
def feature(feature_id: str):
    """Run feature-build on all tasks in a feature."""
    # Load feature YAML, run tasks in dependency order
    click.echo(f"Running feature-build on feature {feature_id}...")
    # TODO: Implement
```

### 4. Slash Commands

**File**: `.claude/commands/feature-build.md`

```markdown
# /feature-build - Run Autonomous Feature Building

Run the feature-build orchestrator on a task or feature.

## Usage

/feature-build TASK-XXX [--max-turns N]
/feature-build FEAT-XXX

## What It Does

1. Creates isolated git worktree
2. Runs Player agent to implement
3. Runs Coach agent to validate
4. Iterates until approved (max N turns)
5. Prompts to merge on approval

## Example

/feature-build TASK-001 --max-turns 3
```

---

## Implementation Plan

### Week 1: Core Loop

```
Day 1-2: Setup + Player Agent
├── Create gka-player.md agent definition
├── Create basic Python orchestrator structure
├── Test Player invocation via Claude Agent SDK
└── Verify report generation

Day 3-4: Coach Agent + Loop
├── Create gka-coach.md agent definition
├── Implement Coach invocation
├── Wire up Player → Coach → feedback loop
└── Test single task completion

Day 5: Git Integration
├── Worktree creation/management
├── Merge on approval
├── Cleanup on failure
└── Basic CLI commands
```

### Week 2: Polish + Integration

```
Day 1-2: Feature Support
├── Load feature YAML from /feature-plan
├── Run tasks in dependency order
├── Track feature-level status
└── Handle partial completion

Day 3-4: UX Polish
├── Progress display (Rich)
├── Better error messages
├── Resume interrupted runs
├── Configuration options

Day 5: Testing + Documentation
├── Integration tests
├── Update GuardKit docs
├── Demo preparation
└── Feedback collection
```

---

## Success Criteria

| Metric | Target |
|--------|--------|
| Single task completes autonomously | ≥50% of test tasks |
| Average turns to completion | ≤4 |
| Coach catches real issues | >80% of intentional bugs |
| Time to working prototype | ≤2 weeks |

---

## What This Enables

After Phase 1a, you'll have:

1. **Validated pattern** - Know if adversarial cooperation works for your use cases
2. **Working tool** - Can use immediately for real features
3. **Informed design** - Better understanding for Phase 1b LangGraph build
4. **Reusable agents** - Player/Coach prompts can port to DeepAgents

---

## Relationship to Phase 1b/2

| Aspect | Phase 1a (This) | Phase 1b/2 (GuardKit Agent CLI) |
|--------|-----------------|--------------------------------|
| Framework | Claude Agent SDK | LangGraph + DeepAgents |
| Infrastructure | GuardKit existing | Replicate from scratch |
| Vendor lock-in | Claude only | Multi-model |
| Memory/Context | None (fresh each turn) | Memory MCP + job-specific |
| UI | CLI only | Potential web UI |
| Effort | 1-2 weeks | 3-4+ weeks |
| Command | `/feature-build` | `gka` |

Phase 1a learnings directly inform Phase 1b:
- Which prompts work best for Player/Coach
- Optimal turn limits
- What context Player needs from Coach feedback
- Where job-specific context would help

---

## Next Steps

1. **Confirm approach** - Does this align with your vision?
2. **Create agent files** - gka-player.md, gka-coach.md
3. **Build orchestrator** - Python CLI with Claude Agent SDK
4. **Test on real task** - Pick a simple task from existing features
5. **Iterate** - Refine prompts based on results

---

*Last Updated: December 22, 2025 - Updated naming: /feature-build for Phase 1a, gka for Phase 1b/2*
