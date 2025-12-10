# Feature Plan - Single Command Feature Planning

Orchestrates the feature planning workflow in a single user-facing command by automatically creating a review task and executing the decision-making analysis.

## Command Syntax

```bash
/feature-plan "feature description" [flags]
```

### Flags

| Flag | Description |
|------|-------------|
| `--no-questions` | Skip all clarification questions (use defaults) |
| `--with-questions` | Force clarification even for simple features |
| `--defaults` | Use defaults without prompting |
| `--answers="..."` | Provide inline answers for automation |

## Overview

The `/feature-plan` command streamlines feature planning by combining task creation and review analysis into a single workflow. It automatically:

1. Creates a review task with `task_type:review` flag
2. Executes `/task-review` with decision-making analysis
3. Presents decision options based on findings
4. Optionally creates implementation tasks from recommendations

This is a **quick win** command that provides a superior user experience by eliminating manual orchestration.

## Examples

```bash
# Basic feature planning
/feature-plan "implement dark mode"

# Plan a complex feature
/feature-plan "add real-time notifications with WebSocket support"

# Plan infrastructure change
/feature-plan "migrate from REST to GraphQL API"

# Plan security enhancement
/feature-plan "implement OAuth2 authentication"

# Skip clarification questions (use defaults)
/feature-plan "add user profile page" --no-questions

# Force clarification for simple features
/feature-plan "fix typo in homepage" --with-questions

# Automation with inline answers
/feature-plan "add caching layer" --answers="A,1,M,S"
```

## Execution Flow

When you run `/feature-plan "implement dark mode"`, the system automatically performs:

### Step 1: Create Review Task

Internally executes:
```bash
/task-create "Plan: implement dark mode" task_type:review priority:high
```

The system captures the generated task ID (e.g., `TASK-REV-A3F2`) from the output.

**Output**:
```
✅ Feature planning task created: TASK-REV-A3F2
📋 Title: Plan: implement dark mode
📁 Location: tasks/backlog/TASK-REV-A3F2-plan-implement-dark-mode.md

Proceeding to review analysis...
```

### Step 2: Execute Decision Review

Internally executes:
```bash
/task-review TASK-REV-A3F2 --mode=decision --depth=standard
```

The review analyzes:
- **Technical options** for implementing the feature
- **Architecture implications** and design patterns
- **Effort estimation** and complexity assessment
- **Risk analysis** and potential blockers
- **Dependencies** and prerequisites
- **Recommended approach** with justification

**Output**:
```
🔍 Analyzing feature: implement dark mode

TECHNICAL OPTIONS ANALYSIS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Option 1: CSS Variables + Theme Context (Recommended)
  Complexity: Medium (6/10)
  Effort: 4-6 hours
  Pros:
    ✅ Standard React pattern for theme management
    ✅ CSS variables provide browser-native performance
    ✅ Easy to extend with additional themes later
    ✅ SSR-compatible (Next.js, Remix)
  Cons:
    ⚠️ Requires context setup and provider wrapping
    ⚠️ Manual theme persistence (localStorage/cookies)
  Dependencies:
    - React Context API (built-in)
    - CSS custom properties (browser support: 98%+)

Option 2: Tailwind Dark Mode + Local Storage
  Complexity: Low (3/10)
  Effort: 2-3 hours
  Pros:
    ✅ Minimal setup if using Tailwind already
    ✅ Automatic class switching
    ✅ Built-in dark mode utilities
  Cons:
    ⚠️ Tightly coupled to Tailwind
    ⚠️ Less flexible for complex theming needs
  Dependencies:
    - Tailwind CSS v3+ (project dependency)

Option 3: Styled-components ThemeProvider
  Complexity: Medium (5/10)
  Effort: 3-5 hours
  Pros:
    ✅ Type-safe theme definitions
    ✅ Scoped styling with theme access
    ✅ SSR support built-in
  Cons:
    ⚠️ Adds CSS-in-JS runtime overhead
    ⚠️ Requires styled-components setup if not using
  Dependencies:
    - styled-components v5+

RECOMMENDED APPROACH:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ Option 1: CSS Variables + Theme Context

RATIONALE:
  - Standard pattern with broad framework support
  - Performance-efficient with native CSS
  - Easy to test and maintain
  - Aligns with modern React best practices

IMPLEMENTATION BREAKDOWN:
1. Create ThemeContext and provider (1-2 hours)
2. Define CSS variables for light/dark themes (1-2 hours)
3. Implement theme toggle component (1 hour)
4. Add theme persistence with localStorage (30 min)
5. Update existing components to use theme variables (1-2 hours)

ESTIMATED EFFORT: 4-6 hours
COMPLEXITY: 6/10 (Medium)
RISK LEVEL: Low
```

### Step 3: Decision Checkpoint

The review presents decision options:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DECISION CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Review complete for: Plan: implement dark mode

What would you like to do?

[A]ccept  - Approve the recommended approach (Option 1)
            Review findings saved, ready for reference

[R]evise  - Request deeper analysis or explore alternatives
            Re-run review with different focus areas

[I]mplement - Create implementation tasks based on recommendation
              Automatically generates:
              - Subtask breakdown (5 tasks)
              - Implementation guide
              - Architecture notes

[C]ancel  - Discard this feature plan
            Review task moved to cancelled state

Your choice [A/R/I/C]:
```

### Step 4a: If [A]ccept

```
✅ Feature plan approved

The review findings have been saved to:
  tasks/in_review/TASK-REV-A3F2-plan-implement-dark-mode.md

You can reference this plan when ready to implement.

To create implementation tasks:
  /feature-plan TASK-REV-A3F2  (run again with task ID)

Or manually:
  /task-create "Implement dark mode" requirements:[TASK-REV-A3F2]
```

### Step 4b: If [R]evise

```
🔄 Re-analyzing with additional focus...

What aspect would you like to explore further?

1. Performance implications
2. Accessibility considerations
3. Alternative technical approaches
4. Integration with existing systems
5. Testing strategy
6. Migration path from current state

Enter choice [1-6]:
```

### Step 4c: If [I]mplement (Enhanced with Auto-Detection - TASK-FW-008)

The enhanced [I]mplement option uses the auto-detection pipeline from TASK-FW-008 to automatically generate the complete feature structure with zero manual input:

```
🚀 Enhanced [I]mplement Flow - Auto-Detection Pipeline

Step 1/10: Extracting feature slug...
   ✓ Feature slug: dark-mode
   ✓ Feature name: implement dark mode

Step 2/10: Parsing subtasks from review recommendations...
   ✓ Found 5 subtasks

Step 3/10: Assigning implementation modes...
   ✓ /task-work: 2, Direct: 3, Manual: 0

Step 4/10: Detecting parallel execution groups...
   ✓ Organized into 2 waves

Step 5/10: Generating Conductor workspace names...
   ✓ Assigned 3 workspace names

Step 6/10: Displaying auto-detected configuration...

================================================================================
✅ Auto-detected Configuration:
================================================================================
   Feature slug: dark-mode
   Feature name: implement dark mode
   Subtasks: 5 (from review recommendations)
   Parallel groups: 2 waves

   Implementation modes:
     • /task-work: 2 tasks
     • Direct: 3 tasks
     • Manual: 0 tasks
================================================================================

Step 7/10: Creating subfolder structure...
   ✓ Created tasks/backlog/dark-mode/

Step 8/10: Generating subtask files...
   ✓ Generated 5 task files

Step 9/10: Generating IMPLEMENTATION-GUIDE.md...
   ✓ Guide generated

Step 10/10: Generating README.md...
   ✓ README generated

================================================================================
✅ Feature Implementation Structure Created
================================================================================

Created: tasks/backlog/dark-mode/
  ├── README.md
  ├── IMPLEMENTATION-GUIDE.md
  ├── TASK-DM-001-add-css-variables.md
  ├── TASK-DM-002-create-theme-context.md
  ├── TASK-DM-003-implement-toggle.md
  ├── TASK-DM-004-add-persistence.md
  └── TASK-DM-005-update-components.md

--------------------------------------------------------------------------------
📋 Execution Strategy:
--------------------------------------------------------------------------------

Wave 1: 3 tasks (parallel execution)
  ⚡ Conductor recommended
     • TASK-DM-001: Add CSS variables (direct, wave1-1)
     • TASK-DM-002: Create theme context (task-work, wave1-2)
     • TASK-DM-003: Implement toggle (direct, wave1-3)

Wave 2: 2 tasks (parallel execution)
  ⚡ Conductor recommended
     • TASK-DM-004: Add persistence (direct, wave2-1)
     • TASK-DM-005: Update components (task-work, wave2-2)

================================================================================
🚀 Next Steps:
================================================================================
1. Review: tasks/backlog/dark-mode/IMPLEMENTATION-GUIDE.md
2. Review: tasks/backlog/dark-mode/README.md
3. Start with Wave 1 tasks
4. Use Conductor for parallel Wave 1 execution
================================================================================

Original review: TASK-REV-A3F2 (marked completed)
```

**What Makes This Enhanced**:
- ✅ **Zero manual prompts** - Everything auto-detected
- ✅ **Smart mode assignment** - Complexity-based task-work/direct/manual
- ✅ **Parallel group detection** - File conflict analysis for waves
- ✅ **Conductor integration** - Workspace names for parallel execution
- ✅ **Complete documentation** - README + Implementation Guide auto-generated
- ✅ **95% time savings** - <1 minute vs 15-30 minutes manual

**See**: `installer/global/lib/implement_orchestrator.py` for orchestration logic

### Step 4d: If [C]ancel

```
❌ Feature plan cancelled

TASK-REV-A3F2 has been moved to cancelled state.

The review findings are preserved for future reference at:
  tasks/cancelled/TASK-REV-A3F2-plan-implement-dark-mode.md
```

## What This Provides

### User Experience Benefits

✅ **Single command** instead of 2-3 manual steps
✅ **Automatic orchestration** of task creation + review
✅ **Clear decision options** with full context
✅ **Enhanced [I]mplement** creates subtasks + guide + folder
✅ **Quick planning** for any feature idea

### Technical Benefits

✅ **Structured analysis** of technical options
✅ **Effort estimation** before commitment
✅ **Risk identification** early in planning
✅ **Architecture guidance** for implementation
✅ **Task breakdown** from single feature description

## Advanced Usage

### Planning with Context

```bash
# Include priority in feature description
/feature-plan "URGENT: implement rate limiting for API endpoints"

# The system will:
# - Set priority:critical on review task
# - Flag as high-risk change
# - Recommend comprehensive depth analysis
```

### Re-planning Existing Review

```bash
# Re-run analysis on existing review task
/feature-plan TASK-REV-A3F2

# Useful when:
# - Initial review needs refinement
# - Requirements changed
# - Want to explore different options
```

### Planning Complex Features

```bash
# Complex feature triggers comprehensive review automatically
/feature-plan "migrate monolith to microservices architecture"

# System detects complexity and:
# - Uses --depth=comprehensive
# - Extends time estimates
# - Recommends multi-phase breakdown
```

## Clarification Integration

`/feature-plan` orchestrates `/task-review` under the hood, so clarification questions flow automatically through two key phases:

### Phase Flow

```
/feature-plan "add authentication"
        │
        ▼
┌─────────────────────────────┐
│ 1. Create Review Task       │
│    (auto-generated)         │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ 2. Execute Task Review      │◀── Context A: Review Scope
│    with --mode=decision     │    (What to analyze?)
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ 3. Decision Checkpoint      │
│    [A]ccept/[R]evise/       │
│    [I]mplement/[C]ancel     │
└─────────────────────────────┘
        │
        ▼ (if [I]mplement)
┌─────────────────────────────┐
│ 4. Implementation Prefs     │◀── Context B: Implementation
│    (approach, parallel,     │    (How to implement?)
│    testing depth)           │
└─────────────────────────────┘
        │
        ▼
┌─────────────────────────────┐
│ 5. Generate Feature         │
│    Structure with subtasks  │
│    (uses clarification)     │
└─────────────────────────────┘
```

### Command-Line Flags

Control clarification behavior with these flags:

| Flag | Effect |
|------|--------|
| `--no-questions` | Skip all clarification (propagates to task-review) |
| `--with-questions` | Force clarification even for simple features |
| `--defaults` | Use defaults without prompting |
| `--answers="..."` | Inline answers for automation |

### Example: Full Clarification Flow

```bash
/feature-plan "add user authentication"

Creating review task: TASK-REV-a3f8
Executing review...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 REVIEW SCOPE CLARIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Review Focus
    What aspects should this review focus on?

    [A]ll aspects
    [S]pecific area (DEFAULT)
    [R]isks only

    Your choice [A/S/R]: A

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[Review executes with clarified scope...]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DECISION CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Review complete. Found 3 approaches:
1. JWT with refresh tokens (Recommended)
2. Session-based auth
3. OAuth 2.0 integration

Options:
  [A]ccept - Approve findings only
  [R]evise - Request deeper analysis
  [I]mplement - Create feature structure
  [C]ancel - Discard review

Your choice: I

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 IMPLEMENTATION PREFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Which approach should subtasks follow?
    [1] JWT with refresh tokens (Recommended)
    [2] Session-based auth
    [3] OAuth 2.0 integration
    [R]ecommend for me

    Your choice: 1

Q2. Parallelization preference?
    [M]aximize parallel
    [S]equential
    [D]etect (DEFAULT)

    Your choice: M

Q3. Testing depth?
    [F]ull TDD
    [S]tandard (DEFAULT)
    [M]inimal
    [D]efault based on complexity

    Your choice: S

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Generating feature structure...

✅ Created: tasks/backlog/user-authentication/
├── README.md
├── IMPLEMENTATION-GUIDE.md (3 parallel waves)
├── TASK-AUTH-001-setup-jwt-middleware.md
├── TASK-AUTH-002-create-user-model.md
├── TASK-AUTH-003-implement-login-endpoint.md
├── TASK-AUTH-004-implement-refresh-tokens.md
└── TASK-AUTH-005-add-auth-tests.md

Subtasks configured with:
  - Approach: JWT with refresh tokens
  - Execution: Parallel (Conductor workspaces assigned)
  - Testing: Standard mode
```

### Example: Skip Clarification

```bash
/feature-plan "add dark mode" --no-questions

Creating review task: TASK-REV-b4c5
Executing review... (skipping clarification)

[Review executes with defaults...]

Decision: [I]mplement (skipping preferences)

Generating feature structure with defaults...

✅ Created: tasks/backlog/dark-mode/
```

### Clarification Propagation

When `/feature-plan` calls `/task-review`, clarification flags are propagated:

```python
# Pseudo-code for feature-plan orchestration
def execute_feature_plan(description: str, flags: dict):
    # Create review task
    task_id = create_review_task(description)

    # Execute task-review with propagated flags
    review_flags = {
        'no_questions': flags.get('no_questions'),
        'with_questions': flags.get('with_questions'),
        'defaults': flags.get('defaults'),
        'answers': flags.get('answers'),
    }

    # Task-review handles Context A and Context B clarification
    result = execute_task_review(
        task_id,
        mode='decision',
        depth='standard',
        flags=review_flags
    )

    # Generate feature structure using clarification context
    if result.decision == 'implement':
        generate_feature_structure(
            result.findings,
            result.clarification  # Contains both Context A & B decisions
        )
```

### Benefits of Clarification in Feature Planning

✅ **Scope clarity** - Understand what to analyze before spending time
✅ **Approach alignment** - Choose implementation direction early
✅ **Parallel efficiency** - Optimize task execution strategy
✅ **Testing coverage** - Set appropriate test depth upfront
✅ **Automation support** - `--answers` flag enables CI/CD workflows

## Integration with Workflow

### Complete Feature Planning Flow

```bash
# 1. Plan the feature
/feature-plan "add user notifications"
# System creates TASK-REV-B4C2, runs analysis, presents options

# 2. Choose [I]mplement at decision checkpoint
# System creates:
#   - Feature subfolder: tasks/backlog/feature-user-notifications/
#   - Subtasks: TASK-B4C2.1 through TASK-B4C2.5
#   - Implementation guide with architecture notes

# 3. Work through implementation tasks
/task-work TASK-B4C2.1  # Implement notification data model
/task-complete TASK-B4C2.1

/task-work TASK-B4C2.2  # Create notification service
/task-complete TASK-B4C2.2

# ... continue through all subtasks ...

# 4. Verify feature complete
/task-status --filter=feature:user-notifications
# Shows all subtasks and completion status
```

### Quick Evaluation Flow

```bash
# 1. Quick feature evaluation (don't commit yet)
/feature-plan "add GraphQL API alongside REST"

# 2. Review findings at decision checkpoint
# Choose [A]ccept to save analysis for later

# 3. Reference saved plan when ready
# Plan saved in tasks/in_review/TASK-REV-XXX.md
# Use /task-create to link implementation to review
```

## Error Handling

### Empty Feature Description

```bash
/feature-plan ""

❌ ERROR: Feature description required

Usage:
  /feature-plan "feature description"

Examples:
  /feature-plan "implement dark mode"
  /feature-plan "add WebSocket support for real-time updates"
```

### Task Creation Failed

```bash
/feature-plan "duplicate feature that already exists"

❌ ERROR: Task creation failed

A review task with similar title already exists:
- TASK-REV-A1B2: Plan: duplicate feature (backlog)

Suggestions:
- Use a more specific feature description
- Review existing plan: /task-review TASK-REV-A1B2
- Cancel existing plan if no longer needed
```

### Review Execution Failed

```bash
/feature-plan "implement new feature"

✅ Feature planning task created: TASK-REV-C3D4

❌ ERROR: Review execution failed

The review task was created but analysis failed.

You can:
1. Retry analysis: /task-review TASK-REV-C3D4
2. Review task manually: Read tasks/backlog/TASK-REV-C3D4.md
3. Cancel plan: /task-cancel TASK-REV-C3D4
```

## Implementation Notes

### Markdown Orchestration (No SDK Required)

This command uses **markdown instruction expansion** - the slash command file contains instructions that Claude Code interprets and executes. No Python/SDK code is required.

**How It Works**:
1. User runs `/feature-plan "description"`
2. Claude Code reads this markdown file
3. Instructions in "Execution Flow" section guide Claude's actions
4. Claude executes internal commands as described
5. Output follows the format specified in examples

**Key Insight**: Slash commands are just markdown files with instructions for Claude. This makes `/feature-plan` trivial to implement - no code changes needed!

### Task ID Capture

The command must parse task ID from `/task-create` output:

```
✅ Task Created: TASK-REV-A3F2
```

Pattern to extract: `TASK-[A-Z0-9-]+` after "Task Created:"

### Decision Checkpoint Integration

The `/task-review` command with `--mode=decision` automatically presents the decision checkpoint. This command doesn't need to implement the checkpoint logic - it's inherited from `/task-review`.

### Enhanced [I]mplement Option

When user chooses [I]mplement, the system should:
1. Create feature subfolder: `tasks/backlog/feature-{slugified-name}/`
2. Generate subtasks based on implementation breakdown
3. Create `IMPLEMENTATION_GUIDE.md` with architecture notes
4. Move original review task to completed state

## Best Practices

### Feature Description Guidelines

**Good descriptions** (specific, actionable):
```bash
/feature-plan "implement OAuth2 authentication with Google provider"
/feature-plan "add real-time collaboration using WebSockets"
/feature-plan "migrate PostgreSQL database to Aurora Serverless"
```

**Poor descriptions** (too vague):
```bash
/feature-plan "make app better"           # Too vague
/feature-plan "fix stuff"                  # Not a feature
/feature-plan "users want notifications"   # Incomplete context
```

### When to Use `/feature-plan`

✅ **Use for**:
- New feature ideas needing evaluation
- Architecture decisions requiring analysis
- Complex changes needing breakdown
- Features with multiple implementation approaches

❌ **Don't use for**:
- Simple bug fixes (use `/task-create` + `/task-work`)
- Obvious implementations (use `/task-create` directly)
- Features already planned (use `/task-work` on existing tasks)

### Iteration and Refinement

```bash
# Initial plan
/feature-plan "add caching layer"
# [Choose [A]ccept to save initial analysis]

# Later: Revisit with more context
/feature-plan TASK-REV-A3F2
# [Review re-analyzes with updated project state]
# [Choose [R]evise to explore alternatives]
# [Choose [I]mplement when ready to execute]
```

## Related Commands

- `/task-create` - Create tasks directly (when planning not needed)
- `/task-review` - Run review analysis on existing tasks
- `/task-work` - Implement tasks (used after planning)
- `/task-status` - Check status of feature tasks

## Output Format

### Success (Complete Flow)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE PLANNING: implement dark mode
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Step 1: Creating review task...
✅ Task created: TASK-REV-A3F2

Step 2: Analyzing technical options...
🔍 Review mode: decision
📊 Analysis depth: standard

[Full analysis output from /task-review]

Step 3: Decision checkpoint
[Decision options: A/R/I/C]

Your choice: I

Step 4: Creating implementation structure...
✅ Feature folder created
✅ 5 subtasks generated
✅ Implementation guide created
✅ Review task completed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE PLANNING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Feature: feature-dark-mode
📋 Implementation guide: tasks/backlog/feature-dark-mode/IMPLEMENTATION_GUIDE.md

Subtasks ready:
  1. TASK-A3F2.1 - Create ThemeContext and provider
  2. TASK-A3F2.2 - Define CSS variables for themes
  3. TASK-A3F2.3 - Implement theme toggle component
  4. TASK-A3F2.4 - Add theme persistence
  5. TASK-A3F2.5 - Update existing components

Next steps:
  Start implementation: /task-work TASK-A3F2.1
  Check progress: /task-status --filter=feature:dark-mode
```

---

## CRITICAL EXECUTION INSTRUCTIONS FOR CLAUDE

When the user runs `/feature-plan "description"`, you MUST:

### Execution Steps

1. ✅ **Parse feature description and flags** from command arguments
   - Extract: description, --no-questions, --with-questions, --defaults, --answers
2. ✅ **Execute `/task-create`** with:
   - Title: "Plan: {description}"
   - Flags: `task_type:review priority:high`
3. ✅ **Capture task ID** from output (regex: `TASK-[A-Z0-9-]+`)
4. ✅ **Execute `/task-review`** with captured task ID:
   - Flags: `--mode=decision --depth=standard`
   - **Propagate clarification flags**: `--no-questions`, `--with-questions`, `--defaults`, `--answers`
5. ✅ **Present decision checkpoint** (inherited from `/task-review`)
   - Context A clarification handled by `/task-review` (review scope)
   - Context B clarification handled at [I]mplement (implementation preferences)
6. ✅ **Handle user decision**:
   - [A]ccept: Save review, show reference message
   - [R]evise: Re-run review with additional focus
   - [I]mplement: Present Context B clarification, then create subfolder + subtasks + guide
   - [C]ancel: Move to cancelled state

### What NOT to Do

❌ **DO NOT** skip task creation step
❌ **DO NOT** skip review execution step
❌ **DO NOT** implement the feature directly
❌ **DO NOT** bypass decision checkpoint
❌ **DO NOT** create implementation files without [I]mplement choice

### Error Handling

If `/task-create` fails:
- Show clear error message
- Provide suggestions (duplicate check, etc.)
- Stop execution (don't proceed to review)

If `/task-review` fails:
- Show task was created successfully
- Provide retry instructions
- Preserve review task for manual execution

### Example Execution Trace

```
User: /feature-plan "implement dark mode"

Claude executes internally:
  1. /task-create "Plan: implement dark mode" task_type:review priority:high
     → Captures: TASK-REV-A3F2
  2. /task-review TASK-REV-A3F2 --mode=decision --depth=standard
     → Presents Context A clarification (review scope)
     → Runs analysis with clarified scope
     → Presents decision options
  3. User chooses: I
  4. Presents Context B clarification (implementation preferences):
     → Approach selection
     → Parallelization strategy
     → Testing depth
  5. Creates structure with clarification context:
     - Feature folder
     - Subtasks (configured per clarification)
     - Implementation guide
  6. Shows completion summary

User: /feature-plan "add caching" --no-questions

Claude executes internally:
  1. /task-create "Plan: add caching" task_type:review priority:high
     → Captures: TASK-REV-B4C5
  2. /task-review TASK-REV-B4C5 --mode=decision --depth=standard --no-questions
     → Skips Context A clarification (uses defaults)
     → Runs analysis with default scope
     → Presents decision options
  3. User chooses: I
  4. Skips Context B clarification (uses defaults)
  5. Creates structure with default configuration
  6. Shows completion summary
```

This is a **coordination command** - it orchestrates existing commands rather than implementing new logic. Follow the execution flow exactly as specified.
