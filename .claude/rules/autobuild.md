---
paths: guardkit/**/*.py, .guardkit/**/*
---

# AutoBuild - Autonomous Task Implementation

AutoBuild provides fully autonomous task implementation using a Player-Coach adversarial workflow. **The Player delegates to task-work** to leverage the full subagent infrastructure, achieving 100% code reuse of quality gates.

## How It Works

AutoBuild uses a three-phase execution pattern:

1. **Setup Phase**: Creates isolated git worktree for the task
2. **Loop Phase**: Executes Player-Coach adversarial turns until approval or max turns
3. **Finalize Phase**: Preserves worktree for human review (never auto-merges)

## Task-Work Delegation Architecture

```
AutoBuild Orchestrator
         │
         ├── PreLoop: task-work --design-only
         │              ├── Clarification (Phase 1.6)
         │              ├── Planning (Phase 2)
         │              ├── Architectural Review (Phase 2.5)
         │              └── Human Checkpoint (Phase 2.8)
         │
         └── Loop: Player↔Coach
                    │
                    └── Player: task-work --implement-only --mode=tdd
                                  ├── Stack-specific specialist
                                  ├── test-orchestrator
                                  ├── code-reviewer
                                  └── Phase 4.5 fix loop
```

## Player-Coach Workflow

The adversarial loop ensures high-quality implementations:

- **Player Agent**: Delegates to task-work, monitors quality gates, creates report
  - Delegates to `task-work --implement-only` (Phases 3-5.5)
  - Works in isolated worktree
  - Reports implementation status and concerns
  - Leverages stack-specific specialists and test-orchestrator

- **Coach Agent**: Validates task-work quality gate results independently
  - Read-only access (Read, Bash only)
  - Reads task-work results from `task_work_results.json`
  - Runs tests independently (trust but verify)
  - Either approves or provides specific feedback

## Usage

Enable AutoBuild in task frontmatter:

```yaml
---
id: TASK-XXX
title: Task title
autobuild:
  enabled: true
  max_turns: 5
  base_branch: main
---
```

Then run:

```bash
guardkit autobuild task TASK-XXX
```

## Configuration

Task frontmatter options:

```yaml
autobuild:
  enabled: true              # Enable AutoBuild for this task
  max_turns: 5               # Maximum Player-Coach iterations (default: 5)
  base_branch: main          # Branch to create worktree from (default: main)
  mode: tdd                  # Development mode: tdd (default), standard, or bdd
  player_model: claude-sonnet-4-5-20250929    # Optional: specify Player model
  coach_model: claude-sonnet-4-5-20250929     # Optional: specify Coach model
  sdk_timeout: 900           # Optional: SDK timeout in seconds (default: 900)
```

## Development Modes

Specify the development mode with `--mode`:

```bash
guardkit autobuild task TASK-XXX --mode=tdd      # Test-Driven Development (default)
guardkit autobuild task TASK-XXX --mode=standard # Implementation first
guardkit autobuild task TASK-XXX --mode=bdd      # Behavior-Driven (requires RequireKit)
```

Mode can also be set in task frontmatter (`autobuild.mode`).

## Pre-Loop Configuration

The pre-loop executes `/task-work --design-only` (Phases 1.6-2.8) before the Player-Coach loop. Adds 60-90 minutes for design.

| Command | Pre-Loop Default | Override Flag | Timeout | Duration |
|---------|-----------------|---------------|---------|----------|
| `guardkit autobuild feature` | **Off** (already pre-designed) | `--enable-pre-loop` | 1800s | 15-25 min |
| `guardkit autobuild task` | **On** (needs design) | `--no-pre-loop` | 7200s | 75-105 min |

## SDK Timeout

Default: 900s. Set via `--sdk-timeout`, task frontmatter `autobuild.sdk_timeout`, or default. Range: 60-3600s.

| Complexity | Timeout | Phase Durations |
|-----------|---------|-----------------|
| 1-3 | 300s | Pre-Loop: 125-315s |
| 4-6 | 600s | Loop/turn: 180-420s |
| 7-10 | 900s | Total: 305-735s |

**Note**: For long feature builds, run from terminal (not Claude Code VS Code extension, which has a 10-min timeout). Exit code 137 = killed by timeout.

## Exit Conditions

AutoBuild exits under three conditions:

1. **Approved**: Coach approves implementation
   - Worktree preserved for human review
   - Ready for manual merge

2. **Max Turns Exceeded**: Reached iteration limit
   - Worktree preserved for inspection
   - Human intervention required

3. **Error**: Critical error occurred
   - Worktree preserved for debugging
   - Check error logs

## Worktree Management

All AutoBuild work happens in isolated git worktrees:

- **Location**: `.guardkit/worktrees/TASK-XXX/`
- **Branch**: `autobuild/TASK-XXX`
- **Preserved**: Never auto-deleted (manual cleanup required)

To review AutoBuild output:

```bash
# Navigate to worktree
cd .guardkit/worktrees/TASK-XXX

# Review changes
git diff main

# Review turn history
cat .guardkit/autobuild/TASK-XXX/player_turn_*.json
cat .guardkit/autobuild/TASK-XXX/coach_turn_*.json

# Merge if approved
git checkout main
git merge autobuild/TASK-XXX

# Cleanup worktree
guardkit worktree cleanup TASK-XXX
```

## Agent Reports

Reports stored in `.guardkit/autobuild/TASK-XXX/`:
- **Player**: `player_turn_N.json` - files changed, tests run/passed, implementation notes, concerns
- **Coach**: `coach_turn_N.json` - decision, validation results, rationale

## Best Practices

1. **Clear Requirements**: Provide detailed requirements and acceptance criteria
2. **Right-Sized Tasks**: Aim for tasks that complete in 1-3 turns
3. **Review Before Merge**: Always review AutoBuild output before merging
4. **Cleanup Worktrees**: Remove old worktrees after merging
5. **Monitor Progress**: Watch the progress display to catch issues early

