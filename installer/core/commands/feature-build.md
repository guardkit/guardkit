# Feature Build - Autonomous Task Implementation

Execute autonomous task implementation using the Player-Coach adversarial workflow. Creates an isolated worktree, runs iterative implementation cycles, and preserves all work for human review.

Supports two modes:
- **Single Task Mode**: `/feature-build TASK-XXX` - Build one task
- **Feature Mode**: `/feature-build FEAT-XXX` - Build all tasks in a feature with dependency ordering

## Command Syntax

```bash
# Single task mode
/feature-build TASK-XXX [options]

# Feature mode (from /feature-plan output)
/feature-build FEAT-XXX [options]
```

## Available Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--max-turns N` | Maximum Player-Coach iterations per task | 5 |
| `--sdk-timeout S` | Claude SDK operation timeout in seconds | 300 |
| `--resume` | Resume from last saved state | false |
| `--verbose` | Show detailed turn-by-turn output | false |
| `--model MODEL` | Claude model to use | claude-sonnet-4-5-20250929 |
| `--parallel N` | Max parallel tasks (feature mode only) | 1 |
| `--stop-on-failure` | Stop feature execution on first task failure | true |
| `--task TASK-ID` | Run specific task within feature (feature mode) | - |
| `--enable-pre-loop` | Enable pre-loop design phases (feature mode) | false |
| `--no-pre-loop` | Disable pre-loop design phases (task mode) | false |
| `--mode MODE` | Development mode: tdd, standard | tdd |

---

## CLI Reference

The `/feature-build` slash command invokes the Python CLI. You can also use the CLI directly from shell.

### From Claude Code (Slash Command)

```bash
# Single task
/feature-build TASK-AUTH-001

# With options
/feature-build TASK-AUTH-001 --max-turns 10 --verbose

# Feature mode
/feature-build FEAT-A1B2
```

### From Shell (Python CLI)

```bash
# Equivalent single task command
guardkit autobuild task TASK-AUTH-001

# With options
guardkit autobuild task TASK-AUTH-001 --max-turns 10 --verbose

# Feature mode
guardkit autobuild feature FEAT-A1B2

# With debug logging
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-A1B2 --verbose

# Check status of running/completed builds
guardkit autobuild status FEAT-A1B2

# Complete and merge (after human review)
guardkit autobuild complete FEAT-A1B2
```

### CLI Command Reference

| Command | Description |
|---------|-------------|
| `guardkit autobuild task TASK-XXX` | Build single task autonomously |
| `guardkit autobuild feature FEAT-XXX` | Build feature with wave orchestration |
| `guardkit autobuild status [ID]` | Show build status |
| `guardkit autobuild complete ID` | Merge approved build to main |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GUARDKIT_LOG_LEVEL` | INFO | Logging verbosity (DEBUG, INFO, WARNING, ERROR) |
| `GUARDKIT_SDK_TIMEOUT` | 300 | Claude SDK timeout in seconds |
| `GUARDKIT_MAX_TURNS` | 5 | Default max iterations |

### Installation

AutoBuild requires the optional `claude-agent-sdk` dependency:

```bash
# Install with AutoBuild support
pip install guardkit-py[autobuild]

# Or add SDK separately
pip install claude-agent-sdk

# Verify installation
guardkit autobuild --help
```

**See Also**: [AutoBuild Workflow Guide](../../../docs/guides/autobuild-workflow.md) for comprehensive documentation.

## How It Works

The `/feature-build` command operates in two modes depending on the input:

### Mode Detection

```
/feature-build FEAT-A1B2    → Feature Mode (loads .guardkit/features/FEAT-A1B2.yaml)
/feature-build TASK-ABC123  → Single Task Mode (loads tasks/*/TASK-ABC123*.md)
```

---

## Single Task Mode

For individual tasks (`TASK-XXX`), the command orchestrates autonomous task implementation through a three-phase execution pattern:

### Phase 1: Setup
1. Load task file from `tasks/` directory
2. Create isolated git worktree in `.guardkit/worktrees/TASK-XXX/`
3. Initialize worktree branch: `autobuild/TASK-XXX`

### Phase 2: Dialectical Loop
Execute Player-Coach adversarial turns until approval or max turns:

```
┌─────────────────────────────────────────────────────────────┐
│                     DIALECTICAL LOOP                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐                    ┌──────────────┐      │
│  │   PLAYER     │                    │    COACH     │      │
│  │   Agent      │───────────────────▶│    Agent     │      │
│  └──────────────┘   Implementation   └──────────────┘      │
│        │            Report                  │               │
│        │                                    │               │
│        │            Feedback                │               │
│        │◀───────────────────────────────────│               │
│        │            or Approval             │               │
│        │                                    │               │
│  Tools:                              Tools:                 │
│  - Read, Write, Edit                 - Read only            │
│  - Bash (full)                       - Bash (read-only)     │
│  - Full file system                  - Validation only      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Player Agent**:
- Full file system access (Read, Write, Edit, Bash)
- Works in isolated worktree
- Implements code, writes tests, creates structured report
- Reports implementation status and concerns

**Coach Agent**:
- Read-only access (Read, Bash for running tests)
- Runs tests independently
- Validates against acceptance criteria
- Either approves or provides specific feedback

### Phase 3: Finalize
- Preserve worktree for human review (never auto-merges)
- Save final state to task frontmatter
- Display results with worktree location

---

## Feature Mode

For features (`FEAT-XXX`), the command orchestrates multiple tasks with dependency awareness:

### Feature Mode Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     FEATURE ORCHESTRATION                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  📁 Load Feature File                                           │
│     .guardkit/features/FEAT-XXX.yaml                            │
│                                                                 │
│  📋 Parse Tasks + Dependencies                                  │
│     ├── TASK-001 (complexity: 3, deps: [])                      │
│     ├── TASK-002 (complexity: 5, deps: [TASK-001])              │
│     ├── TASK-003 (complexity: 5, deps: [TASK-001])              │
│     └── TASK-004 (complexity: 4, deps: [TASK-002, TASK-003])    │
│                                                                 │
│  🔀 Execute by Parallel Groups                                  │
│     Wave 1: [TASK-001]           ──► Player-Coach Loop          │
│     Wave 2: [TASK-002, TASK-003] ──► Player-Coach Loop (×2)     │
│     Wave 3: [TASK-004]           ──► Player-Coach Loop          │
│                                                                 │
│  📊 Track Progress                                              │
│     Update FEAT-XXX.yaml status after each task                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Feature Mode Phases

#### Phase 1: Load Feature
1. Load feature file from `.guardkit/features/FEAT-XXX.yaml`
2. Parse task list with dependencies and parallel groups
3. Validate all referenced task markdown files exist
4. Create feature worktree: `.guardkit/worktrees/FEAT-XXX/`

#### Phase 2: Execute Waves
For each parallel group (wave):
1. Identify tasks ready to execute (all dependencies satisfied)
2. Execute Player-Coach loop for each task in wave
3. Update task status in feature file after completion
4. Block wave until all tasks complete (or fail)

#### Phase 3: Finalize
- Update feature status: `completed` or `failed`
- Preserve worktree for human review
- Display summary with all task results

### Feature File Structure

The feature file (generated by `/feature-plan`) contains:

```yaml
# .guardkit/features/FEAT-A1B2.yaml
id: FEAT-A1B2
name: "User Authentication"
description: "OAuth2 authentication flow"
created: 2025-12-24T10:00:00
status: planned  # planned → in_progress → completed/failed

complexity: 7
estimated_tasks: 4

tasks:
  - id: TASK-001
    name: "Create auth service interface"
    complexity: 3
    dependencies: []
    status: pending
    implementation_mode: direct
    estimated_minutes: 45

  - id: TASK-002
    name: "Implement Google OAuth provider"
    complexity: 5
    dependencies: [TASK-001]
    status: pending
    implementation_mode: task-work
    estimated_minutes: 90

  - id: TASK-003
    name: "Implement GitHub OAuth provider"
    complexity: 5
    dependencies: [TASK-001]
    status: pending
    implementation_mode: task-work
    estimated_minutes: 90

  - id: TASK-004
    name: "Add session management"
    complexity: 4
    dependencies: [TASK-002, TASK-003]
    status: pending
    implementation_mode: task-work
    estimated_minutes: 60

orchestration:
  parallel_groups:
    - [TASK-001]
    - [TASK-002, TASK-003]
    - [TASK-004]
  estimated_duration_minutes: 285
  recommended_parallel: 2
```

### Feature Mode Examples

```bash
# Execute entire feature (sequential by default)
/feature-build FEAT-A1B2

# Execute with parallel tasks (up to 2 concurrent)
/feature-build FEAT-A1B2 --parallel 2

# Resume interrupted feature
/feature-build FEAT-A1B2 --resume

# Run specific task within feature
/feature-build FEAT-A1B2 --task TASK-002

# Verbose output for all tasks
/feature-build FEAT-A1B2 --verbose
```

### Feature Mode Output

```
══════════════════════════════════════════════════════════════
FEATURE BUILD: FEAT-A1B2
══════════════════════════════════════════════════════════════

Feature: User Authentication
Tasks: 4 total
Waves: 3 parallel groups
Mode: Sequential execution

Setting up feature worktree...
  ✓ Created: .guardkit/worktrees/FEAT-A1B2
  ✓ Branch: autobuild/FEAT-A1B2

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wave 1/3: [TASK-001]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK-001: Create auth service interface
  Turn 1/5: Player implementing... Coach validating... ✓ APPROVED
  Status: COMPLETED (1 turn)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wave 2/3: [TASK-002, TASK-003]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK-002: Implement Google OAuth provider
  Turn 1/5: Player implementing... Coach validating... ⚠ FEEDBACK
  Turn 2/5: Player implementing... Coach validating... ✓ APPROVED
  Status: COMPLETED (2 turns)

TASK-003: Implement GitHub OAuth provider
  Turn 1/5: Player implementing... Coach validating... ✓ APPROVED
  Status: COMPLETED (1 turn)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Wave 3/3: [TASK-004]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TASK-004: Add session management
  Turn 1/5: Player implementing... Coach validating... ✓ APPROVED
  Status: COMPLETED (1 turn)

══════════════════════════════════════════════════════════════
FEATURE RESULT: SUCCESS
══════════════════════════════════════════════════════════════

Feature: User Authentication
Status: COMPLETED
Tasks: 4/4 completed
Total Turns: 5
Duration: ~15 minutes

Worktree: .guardkit/worktrees/FEAT-A1B2
Branch: autobuild/FEAT-A1B2

Next Steps:
  1. Review: cd .guardkit/worktrees/FEAT-A1B2 && git diff main
  2. Merge: git checkout main && git merge autobuild/FEAT-A1B2
  3. Cleanup: guardkit worktree cleanup FEAT-A1B2
```

---

## Examples

### Basic Usage
```bash
# Execute autonomous implementation
/feature-build TASK-ABC123

# Equivalent CLI command (what gets executed)
guardkit autobuild task TASK-ABC123
```

### With Options
```bash
# More iterations for complex tasks
/feature-build TASK-ABC123 --max-turns 10

# Resume interrupted session
/feature-build TASK-ABC123 --resume

# Verbose output with different model
/feature-build TASK-ABC123 --verbose --model claude-opus-4-5-20251101
```

### Resume After Interruption
```bash
# Session was interrupted (Ctrl+C or timeout)
# State automatically saved to task frontmatter

# Resume from where you left off
/feature-build TASK-ABC123 --resume
```

## Task Configuration

Enable AutoBuild in task frontmatter for configuration:

```yaml
---
id: TASK-ABC123
title: "Implement OAuth2 authentication"
status: backlog
requirements: |
  Add OAuth2 authentication with:
  - Token generation
  - Token refresh
  - Secure storage
acceptance_criteria:
  - OAuth2 flow completes successfully
  - Tokens refresh automatically before expiry
  - Token storage uses secure keychain
autobuild:
  enabled: true
  max_turns: 5
  base_branch: main
---
```

### AutoBuild Configuration Options

| Field | Description | Default |
|-------|-------------|---------|
| `enabled` | Enable AutoBuild for this task | false |
| `max_turns` | Maximum iterations | 5 |
| `base_branch` | Branch to create worktree from | main |
| `player_model` | Model for Player agent | claude-sonnet-4-5-20250929 |
| `coach_model` | Model for Coach agent | claude-sonnet-4-5-20250929 |
| `sdk_timeout` | SDK timeout in seconds | 600 |

## State Persistence

State is automatically saved to task frontmatter after each turn:

```yaml
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: .guardkit/worktrees/TASK-ABC123
  base_branch: main
  started_at: '2025-12-24T10:00:00'
  last_updated: '2025-12-24T10:10:00'
  turns:
    - turn: 1
      decision: feedback
      feedback: "Missing token refresh edge case"
      timestamp: '2025-12-24T10:05:00'
      player_summary: "Implemented OAuth flow with basic tests"
      player_success: true
      coach_success: true
    - turn: 2
      decision: approve
      feedback: null
      timestamp: '2025-12-24T10:10:00'
      player_summary: "Added refresh token handling"
      player_success: true
      coach_success: true
```

## Exit Conditions

| Condition | Status | Next Steps |
|-----------|--------|------------|
| Coach approves | SUCCESS | Review worktree, merge manually |
| Max turns exceeded | BLOCKED | Review feedback, manual intervention |
| Critical error | ERROR | Check logs, debug in worktree |

## Workflow Example

### Simple Task (1-2 turns)
```bash
/feature-build TASK-AUTH-001

Turn 1: Player Implementation
  ✓ 3 files created, 2 modified, 5 tests passing
Turn 1: Coach Validation
  ✓ Coach approved - ready for human review

Status: APPROVED
Worktree: .guardkit/worktrees/TASK-AUTH-001
Branch: autobuild/TASK-AUTH-001

Next Steps:
  cd .guardkit/worktrees/TASK-AUTH-001
  git diff main
  # If satisfied, merge to main
```

### Iterative Task (3+ turns)
```bash
/feature-build TASK-OAUTH-002 --verbose

Turn 1: Player Implementation
  ✓ 2 files created, 8 tests passing
Turn 1: Coach Validation
  ⚠ Feedback: Missing token refresh logic

Turn 2: Player Implementation
  ✓ 1 file modified, 11 tests passing
Turn 2: Coach Validation
  ⚠ Feedback: Edge case coverage incomplete

Turn 3: Player Implementation
  ✓ 2 files modified, 15 tests passing
Turn 3: Coach Validation
  ✓ Coach approved - ready for human review

Status: APPROVED
Total Turns: 3
Worktree: .guardkit/worktrees/TASK-OAUTH-002
```

## Worktree Management

All work happens in isolated git worktrees:

- **Location**: `.guardkit/worktrees/TASK-XXX/`
- **Branch**: `autobuild/TASK-XXX`
- **Preserved**: Never auto-deleted (manual cleanup required)

### Reviewing AutoBuild Output
```bash
# Navigate to worktree
cd .guardkit/worktrees/TASK-XXX

# Review changes
git diff main

# Review turn history (JSON reports)
cat .guardkit/autobuild/TASK-XXX/player_turn_*.json
cat .guardkit/autobuild/TASK-XXX/coach_turn_*.json

# If satisfied, merge
git checkout main
git merge autobuild/TASK-XXX

# Cleanup
guardkit worktree cleanup TASK-XXX
```

## Integration with GuardKit Workflow

### Single Task Workflow

```bash
# 1. Create task (standard workflow)
/task-create "Implement OAuth2 authentication"
# Created: TASK-AUTH-001

# 2. OPTION A: Manual implementation with quality gates
/task-work TASK-AUTH-001

# 2. OPTION B: Autonomous implementation (this command)
/feature-build TASK-AUTH-001
# → Creates worktree, runs Player-Coach loop
# → Preserves output for human review

# 3. Review worktree output
cd .guardkit/worktrees/TASK-AUTH-001
git diff main

# 4. Merge if approved
git checkout main && git merge autobuild/TASK-AUTH-001

# 5. Complete task
/task-complete TASK-AUTH-001
```

### Feature Workflow (Recommended)

```bash
# 1. Plan feature (generates structured YAML + task files)
/feature-plan "Implement OAuth2 authentication"
# → Creates: .guardkit/features/FEAT-A1B2.yaml
# → Creates: tasks/backlog/oauth2/TASK-001.md ... TASK-004.md

# 2. OPTION A: Manual implementation per task
/task-work TASK-001
/task-work TASK-002
# ... (respecting dependencies)

# 2. OPTION B: Autonomous implementation of entire feature
/feature-build FEAT-A1B2
# → Loads feature file with dependencies
# → Executes tasks in wave order
# → Creates single feature worktree
# → Preserves all output for human review

# 3. Review feature worktree
cd .guardkit/worktrees/FEAT-A1B2
git diff main

# 4. Merge if approved
git checkout main && git merge autobuild/FEAT-A1B2

# 5. Complete all tasks
/task-complete TASK-001 TASK-002 TASK-003 TASK-004

# 6. Cleanup
guardkit worktree cleanup FEAT-A1B2
```

## When to Use /feature-build

### Good Candidates
- Well-defined requirements with clear acceptance criteria
- Standard implementation patterns
- Good test coverage possible
- Low to medium risk changes
- Tasks that can complete in 1-5 iterations

### Use /task-work Instead
- Exploratory work
- Complex architectural decisions
- High risk changes
- Unusual or novel requirements
- Tasks requiring significant human judgment

## Troubleshooting

### "Task not found"
```bash
# Ensure task file exists
ls tasks/backlog/TASK-XXX*.md
ls tasks/in_progress/TASK-XXX*.md

# Check task ID format
/feature-build TASK-ABC123  # Correct
/feature-build ABC123        # Wrong - missing TASK- prefix
```

### "Max turns reached without approval"
1. Review Coach feedback from last turn
2. Check if requirements are too broad
3. Consider splitting into smaller tasks
4. Use `--max-turns 10` for complex tasks
5. Fall back to `/task-work` for manual implementation

### "Worktree already exists"
```bash
# Clean up existing worktree
guardkit worktree cleanup TASK-XXX

# Or manually remove
rm -rf .guardkit/worktrees/TASK-XXX
git worktree prune

# Then retry
/feature-build TASK-XXX
```

### "Resume failed - no saved state"
```bash
# Check task frontmatter for autobuild_state section
cat tasks/*/TASK-XXX*.md | grep -A 20 "autobuild_state"

# If no state exists, start fresh (without --resume)
/feature-build TASK-XXX
```

## Best Practices

1. **Clear Requirements**: Provide detailed requirements and acceptance criteria in task frontmatter
2. **Right-Sized Tasks**: Aim for tasks that complete in 1-3 turns
3. **Review Before Merge**: Always review AutoBuild output before merging
4. **Cleanup Worktrees**: Remove old worktrees after merging
5. **Monitor Progress**: Watch turn-by-turn output to catch issues early
6. **Use Resume**: If interrupted, use `--resume` instead of starting over

---

## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

### What This Command Does

This command operates in **two modes** based on the input ID:

1. **Single Task Mode** (`TASK-XXX`): Execute one task with Player-Coach loop
2. **Feature Mode** (`FEAT-XXX`): Execute all tasks in a feature with dependency ordering

### Mode Detection

```python
def detect_mode(id_arg: str) -> str:
    if id_arg.startswith("FEAT-"):
        return "feature"
    elif id_arg.startswith("TASK-"):
        return "single_task"
    else:
        raise ValueError(f"Invalid ID format: {id_arg}. Use TASK-XXX or FEAT-XXX")
```

---

### Single Task Mode Execution

When the user invokes `/feature-build TASK-XXX`:

1. **Load the task file** from `tasks/backlog/` or `tasks/in_progress/`
2. **Check if CLI is available** (required - error if not)
3. **Execute Player-Coach loop via CLI** until approval or max turns
4. **Show final results** with worktree location

#### Step 1: Check CLI Availability

```bash
# Check if guardkit autobuild command exists
guardkit autobuild --help 2>&1 || echo "CLI_NOT_AVAILABLE"
```

If CLI is not available, display this error and exit:

```
══════════════════════════════════════════════════════════════
ERROR: GuardKit CLI Required
══════════════════════════════════════════════════════════════

The /feature-build command requires the GuardKit CLI to be installed.

The CLI provides the fully-tested Player-Coach adversarial loop with:
  • Promise-based completion verification
  • Honesty verification
  • Quality gate enforcement
  • State persistence and resume

Installation:
  pip install guardkit

  Or from source:
  cd ~/Projects/guardkit
  pip install -e .

After installation, verify:
  guardkit autobuild --help

Then retry:
  /feature-build TASK-XXX
══════════════════════════════════════════════════════════════
```

#### Step 2: Execute via CLI

```bash
guardkit autobuild task TASK-XXX [options]
```

---

### Feature Mode Execution

When the user invokes `/feature-build FEAT-XXX`:

1. **Load the feature file** from `.guardkit/features/FEAT-XXX.yaml`
2. **Parse tasks and dependencies** from the YAML structure
3. **Check if CLI is available** (required - error if not)
4. **Execute tasks wave by wave via CLI** respecting parallel groups
5. **Update feature status** after each task completes
6. **Show final summary** with all task results

#### Step 1: Load Feature File

Read the feature YAML file to get tasks, dependencies, and parallel groups:

```bash
# Read feature file
cat .guardkit/features/FEAT-XXX.yaml
```

Parse the YAML to extract:
- `tasks`: List of task specs with id, name, complexity, dependencies, status
- `orchestration.parallel_groups`: Pre-computed wave execution order

#### Step 2: Check CLI Availability

```bash
# Check if guardkit autobuild command exists
guardkit autobuild --help 2>&1 || echo "CLI_NOT_AVAILABLE"
```

If CLI is not available, display the same error message as Single Task Mode (see above) and exit.

#### Step 3: Execute Tasks via CLI

Execute each task through the CLI:

```bash
for task_id in wave:
    guardkit autobuild task $task_id --max-turns 5
```

#### Step 4: Update Feature YAML

After each task completes, update the feature file:

```yaml
# In .guardkit/features/FEAT-XXX.yaml
tasks:
  - id: TASK-001
    status: completed  # was: pending
  - id: TASK-002
    status: in_progress  # currently executing
  - id: TASK-003
    status: pending  # waiting for dependencies
```

#### Step 5: Handle Stop on Failure

If `--stop-on-failure` (default: true) and a task fails:
1. Update feature status to `failed`
2. Display error with failed task details
3. Preserve worktree for debugging
4. Exit without executing remaining tasks

#### Example Feature Execution Flow

```
Wave 1/4: [TASK-OAUTH-001]
  TASK-OAUTH-001: Create auth infrastructure
    Turn 1/5: Player... Coach... ✓ APPROVED
  Status: COMPLETED

Wave 2/4: [TASK-OAUTH-002, TASK-OAUTH-003, TASK-OAUTH-006]
  TASK-OAUTH-002: Implement User models
    Turn 1/5: Player... Coach... ✓ APPROVED
  TASK-OAUTH-003: Configure JWT backend
    Turn 1/5: Player... Coach... ✓ APPROVED
  TASK-OAUTH-006: Database migrations
    Turn 1/5: Player... Coach... ✓ APPROVED
  Status: ALL COMPLETED

Wave 3/4: [TASK-OAUTH-004, TASK-OAUTH-005]
  ...

Wave 4/4: [TASK-OAUTH-007]
  ...

FEATURE RESULT: SUCCESS
```

---

**Note**: The pseudo-code below shows the logical flow. Actual execution uses the CLI orchestrator described above.

```python
# Logical flow (for reference only - actual execution via CLI)
feature_id = args[0]  # e.g., "FEAT-A1B2"
max_turns = options.get("max-turns", 5)
stop_on_failure = options.get("stop-on-failure", True)

# Load feature file (use Read tool)
feature = read_yaml(f".guardkit/features/{feature_id}.yaml")

# Execute waves in order
for wave_idx, wave in enumerate(feature["orchestration"]["parallel_groups"]):
    display(f"Wave {wave_idx + 1}/{len(waves)}: {wave}")

    for task_id in wave:
        task = find_task(feature["tasks"], task_id)
        if task["status"] == "completed":
            continue

        # Execute using CLI orchestrator
        result = execute_player_coach_loop(task, max_turns)

        # Update task status in feature YAML (use Edit tool)
        # Change task.status from "pending" to "completed" or "failed"

        if result == "failed" and stop_on_failure:
            # Update feature status to "failed"
            error(f"Task {task_id} failed. Feature execution stopped.")
            return

# Update feature status to "completed"
# Display final summary
```

### Feature Mode: Required Structure

The feature file (from `/feature-plan`) MUST have:

```yaml
id: FEAT-XXX
name: "Feature name"
status: planned
tasks:
  - id: TASK-001
    name: "Task name"
    complexity: 3
    dependencies: []
    status: pending
orchestration:
  parallel_groups:
    - [TASK-001]
    - [TASK-002, TASK-003]
```

### Feature Mode: Task Markdown Files

Each task in the feature MUST have a corresponding markdown file in `tasks/`:

```
tasks/backlog/{feature-slug}/
├── TASK-001-create-auth-service.md
├── TASK-002-implement-google-oauth.md
├── TASK-003-implement-github-oauth.md
└── TASK-004-add-session-management.md
```

These files provide the `requirements` and `acceptance_criteria` for each task.

### Required Task Structure

The task file MUST have:
- `requirements` field (string or YAML block)
- `acceptance_criteria` field (list or string)

```yaml
---
id: TASK-ABC123
title: "Task title"
status: backlog
requirements: |
  Detailed requirements here...
acceptance_criteria:
  - First criterion
  - Second criterion
---
```

### Error Handling

**Single Task Mode Errors:**

| Error | User Message | Recovery |
|-------|--------------|----------|
| Task not found | "Task TASK-XXX not found in tasks/" | Check task ID and location |
| Missing requirements | "Task missing requirements field" | Add requirements to task |
| Missing acceptance criteria | "Task missing acceptance_criteria" | Add criteria to task |
| Worktree exists | "Worktree already exists for TASK-XXX" | Use `--resume` or cleanup |
| SDK error | "AutoBuild SDK error: {details}" | Check API keys and network |

**Feature Mode Errors:**

| Error | User Message | Recovery |
|-------|--------------|----------|
| Feature not found | "Feature FEAT-XXX not found" | Check `.guardkit/features/FEAT-XXX.yaml` exists |
| Invalid feature YAML | "Failed to parse feature file" | Validate YAML syntax |
| Missing task markdown | "Task TASK-001 has no markdown file" | Create task file in `tasks/backlog/` |
| Dependency cycle | "Circular dependency detected" | Fix task dependencies in feature file |
| Task failed | "Task TASK-001 failed. Feature stopped." | Fix task, use `--resume` to continue |
| Missing parallel_groups | "Feature missing orchestration config" | Re-run `/feature-plan` |

### What NOT To Do

1. **DO NOT** implement the task directly (that's what AutoBuild does)
2. **DO NOT** create worktrees manually (AutoBuild handles this)
3. **DO NOT** modify task files (AutoBuild updates frontmatter)
4. **DO NOT** auto-merge (human review required)

### Output Format

```
══════════════════════════════════════════════════════════════
FEATURE BUILD: TASK-ABC123
══════════════════════════════════════════════════════════════

Task: Implement OAuth2 authentication
Max Turns: 5
Mode: Starting fresh

Setting up worktree...
  ✓ Created: .guardkit/worktrees/TASK-ABC123
  ✓ Branch: autobuild/TASK-ABC123

Turn 1/5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Player: Implementing...
  [Progress details]
Coach: Validating...
  Decision: FEEDBACK
  Feedback: Missing token refresh handling

Turn 2/5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Player: Implementing...
  [Progress details]
Coach: Validating...
  Decision: APPROVE

══════════════════════════════════════════════════════════════
RESULT: SUCCESS
══════════════════════════════════════════════════════════════

Status: APPROVED by Coach
Total Turns: 2
Worktree: .guardkit/worktrees/TASK-ABC123
Branch: autobuild/TASK-ABC123

Next Steps:
  1. Review: cd .guardkit/worktrees/TASK-ABC123 && git diff main
  2. Merge: git checkout main && git merge autobuild/TASK-ABC123
  3. Complete: /task-complete TASK-ABC123
  4. Cleanup: guardkit worktree cleanup TASK-ABC123
```
