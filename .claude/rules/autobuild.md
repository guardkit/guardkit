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

The pre-loop executes `/task-work --design-only` (Phases 1.6-2.8) before the Player-Coach loop to establish architectural design and generate an implementation plan. This adds 60-90 minutes for comprehensive design.

**Default Behavior**:
- **Feature-build** (`guardkit autobuild feature`): Pre-loop **disabled** by default
  - Tasks from `/feature-plan` already have detailed specs
  - Use `--enable-pre-loop` to force design phase

- **Task-build** (`guardkit autobuild task`): Pre-loop **enabled** by default
  - Standalone tasks benefit from design phase
  - Use `--no-pre-loop` to skip for well-defined tasks

**Why Feature-Build Defaults to Pre-Loop Disabled**:

Tasks created via `/feature-plan` are already "pre-designed":
- Detailed requirements extracted from review analysis
- Acceptance criteria generated from recommendations
- Implementation mode assignments (task-work/direct/manual)
- Wave groupings for parallel execution

Running pre-loop (Phases 1.6-2.8) would duplicate this design work, adding 60-90 minutes per task without additional value.

**Why Task-Build Defaults to Pre-Loop Enabled**:

Standalone tasks (`guardkit autobuild task`) may lack detailed specifications. The pre-loop design phases ensure:
- Requirements are clarified (Phase 1.6)
- Implementation is planned (Phase 2)
- Architecture is reviewed (Phase 2.5)
- Human checkpoint for complex tasks (Phase 2.8)

**CLI Flags**:
```bash
# Feature-build (default: pre-loop OFF)
guardkit autobuild feature FEAT-XXX                    # Pre-loop disabled
guardkit autobuild feature FEAT-XXX --enable-pre-loop # Force pre-loop

# Task-build (default: pre-loop ON)
guardkit autobuild task TASK-XXX                       # Pre-loop enabled
guardkit autobuild task TASK-XXX --no-pre-loop        # Skip pre-loop
```

**Timeout Recommendations by Pre-Loop Setting**:

| Mode | Pre-Loop | Recommended Timeout | Typical Duration |
|------|----------|---------------------|------------------|
| Feature-build | Off (default) | 1800s (30 min) | 15-25 min |
| Feature-build | On (`--enable-pre-loop`) | 7200s (2 hours) | 75-105 min |
| Task-build | On (default) | 7200s (2 hours) | 75-105 min |
| Task-build | Off (`--no-pre-loop`) | 1800s (30 min) | 15-25 min |

**When to Enable Pre-Loop for Feature-Build**:
- Task has unclear acceptance criteria
- Task requires significant architectural decisions
- First task in a new feature area
- You want explicit human checkpoint before implementation

Command: `guardkit autobuild feature FEAT-XXX --enable-pre-loop`

**When to Disable Pre-Loop for Task-Build**:
- Task has detailed implementation notes in markdown
- Follow-up task where design is already established
- Simple bug fix or documentation update
- You want faster execution

Command: `guardkit autobuild task TASK-XXX --no-pre-loop`

## SDK Timeout Configuration

The `--sdk-timeout` flag controls how long to wait for agent invocations (default: 900 seconds).

**CLI Usage**:
```bash
guardkit autobuild task TASK-XXX --sdk-timeout 600    # 10 minutes
guardkit autobuild feature FEAT-XXX --sdk-timeout 900 # 15 minutes
```

**Configuration Cascade** (highest priority first):
1. CLI flag: `--sdk-timeout 600`
2. Task frontmatter: `autobuild.sdk_timeout: 900`
3. Default: 900 seconds

**Valid Range**: 60-3600 seconds (1 minute to 1 hour)

**When to Increase Timeout**:
- Complex tasks with Phase 4.5 test enforcement loop (3 iterations × 60-90s)
- Large codebases requiring extensive code analysis
- Tasks with many acceptance criteria

## Recommended Timeout Values

| Task Complexity | Recommended Timeout | Use Case |
|-----------------|---------------------|----------|
| 1-3 (Simple) | 300s (5 min) | Quick fixes, single-file changes |
| 4-6 (Medium) | 600s (10 min) | Standard features, multiple files |
| 7-10 (Complex) | 900s (15 min) | Large features, architectural changes |

**Phase Duration Reference**:
- Pre-Loop (Phases 2-2.8): 125-315 seconds
- Loop (Phases 3-5.5): 180-420 seconds per turn
- Total typical range: 305-735 seconds

## Running Feature-Build from Claude Code

**Important**: Claude Code's VS Code extension has a 10-minute bash command timeout. For long-running feature builds, run from terminal instead:

```bash
# From terminal (recommended for feature builds)
cd /path/to/project
guardkit autobuild feature FEAT-XXX --sdk-timeout 900

# NOT from Claude Code for long builds
```

If you see exit code 137 (SIGKILL), this indicates the bash command was killed by the external timeout.

## Workflow Example

**Simple Task (1-2 turns)**:
```
Turn 1: Player (task-work --implement-only --mode=tdd)
  ✓ Delegated to stack-specific specialist
  ✓ 3 files created, 2 modified, 5 tests passing
  ✓ Quality gates: Phase 3-5.5 complete
Turn 1: Coach Validation
  ✓ Read task_work_results.json
  ✓ Verified all quality gates passed
  ✓ Coach approved - ready for human review

Status: APPROVED
Worktree: .guardkit/worktrees/TASK-XXX
```

**Iterative Task (3+ turns)**:
```
Turn 1: Player (task-work --implement-only --mode=tdd)
  ✓ 2 files created, 8 tests passing
Turn 1: Coach Validation
  ⚠ Feedback: Missing token refresh logic

Turn 2: Player (task-work --implement-only --mode=tdd)
  ✓ 1 file modified, 11 tests passing
Turn 2: Coach Validation
  ⚠ Feedback: Edge case coverage incomplete

Turn 3: Player (task-work --implement-only --mode=tdd)
  ✓ 2 files modified, 15 tests passing
Turn 3: Coach Validation
  ✓ Coach approved - ready for human review

Status: APPROVED
Worktree: .guardkit/worktrees/TASK-XXX
```

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

Player and Coach create structured JSON reports:

**Player Report** (`.guardkit/autobuild/TASK-XXX/player_turn_N.json`):
Fields: `task_id`, `turn`, `files_modified`, `files_created`, `tests_written`, `tests_run`, `tests_passed`, `test_output_summary`, `implementation_notes`, `concerns`, `requirements_addressed`, `requirements_remaining`

**Coach Decision** (`.guardkit/autobuild/TASK-XXX/coach_turn_N.json`):
Fields: `task_id`, `turn`, `decision`, `validation_results` (requirements_met, tests_run, tests_passed, test_command, test_output_summary, code_quality, edge_cases_covered), `rationale`

## Troubleshooting

**AutoBuild not available?**
- Check Claude Agents SDK installation
- Verify API keys configured
- Run `guardkit doctor` for diagnostics

**Player/Coach not responding?**
- Check SDK timeout configuration
- Review error logs in `.guardkit/logs/`
- Verify worktree permissions

**Max turns reached without approval?**
- Review Coach feedback from last turn
- Check if requirements are too broad
- Consider splitting into smaller tasks
- Manual implementation may be needed

**Worktree conflicts?**
- Ensure base branch is up to date
- Check for existing worktree with same name
- Run `guardkit worktree cleanup` if needed

**Timeout errors?**

Error: `SDK timeout after Xs: Agent invocation exceeded Xs timeout`

Solutions:
1. Increase timeout: `guardkit autobuild task TASK-XXX --sdk-timeout 900`
2. Or set in task frontmatter:
   ```yaml
   autobuild:
     sdk_timeout: 900
   ```
3. For feature builds, run from terminal instead of Claude Code (see [Running Feature-Build from Claude Code](#running-feature-build-from-claude-code))

## Best Practices

1. **Clear Requirements**: Provide detailed requirements and acceptance criteria
2. **Right-Sized Tasks**: Aim for tasks that complete in 1-3 turns
3. **Review Before Merge**: Always review AutoBuild output before merging
4. **Cleanup Worktrees**: Remove old worktrees after merging
5. **Monitor Progress**: Watch the progress display to catch issues early

## Integration with GuardKit Workflow

AutoBuild integrates seamlessly with GuardKit task workflow by delegating to task-work:

```bash
# Standard workflow (manual, human-in-the-loop)
/task-create "Implement OAuth2 authentication"
/task-work TASK-XXX  # Manual execution with quality gates

# AutoBuild workflow (autonomous, Player-Coach)
/task-create "Implement OAuth2 authentication" autobuild:enabled=true
guardkit autobuild task TASK-XXX --mode=tdd  # Autonomous via task-work delegation
# Review worktree output
# Merge manually
/task-complete TASK-XXX
```

**Both workflows use the SAME quality gates** (100% code reuse):
- Phase 2.5B: Architectural Review (SOLID/DRY/YAGNI)
- Phase 4.5: Test Enforcement Loop (100% pass rate)
- Phase 5: Code Review
- Phase 5.5: Plan Audit (scope creep detection)

**When to Use AutoBuild**:
- Well-defined requirements
- Standard implementation patterns
- Good test coverage possible
- Low risk changes
- Want autonomous iteration

**When to Use Manual /task-work**:
- Exploratory work
- Complex architectural decisions
- High risk changes
- Unusual requirements
- Want human checkpoints during execution
