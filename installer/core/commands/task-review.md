# Task Review - Structured Analysis and Decision-Making

Execute structured review and analysis workflows for tasks that require assessment, evaluation, or decision-making rather than implementation.

## Command Syntax

```bash
# ID form — review an existing task
/task-review TASK-XXX [--mode=MODE] [--depth=DEPTH] [--output=FORMAT] [--capture-knowledge]

# Description form (ad-hoc) — self-creates the review task, then reviews it
/task-review "free-text description of what to review" [--mode=MODE] [--depth=DEPTH] [--output=FORMAT] [--capture-knowledge]
```

**Argument detection**: if the first argument matches the task-id pattern
`^TASK(-[A-Z0-9]{2,4})?-[A-Fa-f0-9]{4,6}$` it is treated as a task reference (ID form);
anything else is treated as a description (ad-hoc form, see Phase 0). An argument that
matches the id pattern but has no matching task file on disk is an error, exactly as today —
there is NO silent fallback from a missing ID to description mode.

## Available Flags

| Flag | Description |
|------|-------------|
| `--mode=MODE` | Review mode (architectural, code-quality, decision, technical-debt, security) |
| `--depth=DEPTH` | Review depth (quick, standard, comprehensive) |
| `--output=FORMAT` | Output format (markdown, json, both) |
| `--no-questions` | Skip review scope clarification |
| `--with-questions` | Force clarification even for simple reviews |
| `--defaults` | Use clarification defaults without prompting |
| `--capture-knowledge` | Trigger knowledge capture session after review completion (3-5 context-specific questions) |

## Overview

The `/task-review` command provides a dedicated workflow for analysis and decision-making tasks, separate from the implementation-focused `/task-work` command.

**Use `/task-review` for**:
- Architectural reviews and assessments
- Code quality evaluations
- Technical decision analysis
- Technical debt assessment
- Security audits
- Root cause analysis

**Use `/task-work` for**:
- Feature implementation
- Bug fixes
- Refactoring
- Test creation

## Ad-Hoc Review (Description Form)

Passing a free-text description instead of a task ID removes the two-step friction of
`/task-create "..." task_type:review` → wait → copy the TASK-REV id → `/task-review TASK-REV-XXXX`.
The command self-creates the review task (Phase 0) and proceeds directly into the review.

```bash
/task-review "auth redirect loops after logout" --mode=code-quality
```

Properties of the ad-hoc form:

- **Same durable record**: a real `TASK-REV-{hash}` task file is created in `tasks/backlog/`
  BEFORE analysis starts, so provenance, fleet-memory writes, and downstream joins on
  TASK-REV ids are identical to the two-step flow. Nothing about the report, frontmatter,
  or decision checkpoint changes.
- **Deterministic creation**: Phase 0 shells out to `guardkit task create "{description}"
  --prefix REV --task-type review` (guardkit/cli/task.py) — the same collision-checked
  hash-ID machinery, not ad-hoc file writing.
- **All flags apply unchanged**: `--mode`, `--depth`, `--output`, clarification flags, and
  `--capture-knowledge` behave exactly as in the ID form.
- **The two-step flow remains valid**: `/task-create ... task_type:review` followed by
  `/task-review TASK-REV-XXXX` is unchanged (it is what `/feature-plan` uses internally).

## Automatic Review Task Detection

When creating tasks with `/task-create`, the system automatically detects review/analysis tasks and suggests using `/task-review` instead of `/task-work`.

### Detection Criteria

A task is detected as a review task if **any** of the following conditions are met:

1. **Explicit task_type field**: `task_type:review` parameter
2. **Decision required flag**: `decision_required:true` parameter
3. **Review-related tags**: `architecture-review`, `code-review`, `decision-point`, `assessment`
4. **Title keywords**: `review`, `analyze`, `evaluate`, `assess`, `audit`, `investigation`

### Suggestion Behavior

When a review task is detected during `/task-create`, you'll see:

```
=========================================================================
REVIEW TASK DETECTED
=========================================================================

Task: Review authentication architecture

This appears to be a review/analysis task.

Suggested workflow:
  1. Create task: /task-create (current command)
  2. Execute review: /task-review TASK-XXX
  3. (Optional) Implement findings: /task-work TASK-YYY

Shortcut: /task-review "description" does both steps in one command
(self-creates the review task, then runs the review).

Note: /task-work is for implementation, /task-review is for analysis.
=========================================================================

Create task? [Y/n]:
```

**Important**: The suggestion is **informational only** and doesn't block task creation. You can still create the task and use `/task-work` if desired, though `/task-review` is recommended for analysis tasks.

### Detection Examples

**Example 1: Explicit task_type**
```bash
/task-create "Architectural review of authentication system" task_type:review
# ✅ Detected: Explicit task_type field
```

**Example 2: Decision required flag**
```bash
/task-create "Should we migrate to microservices?" decision_required:true
# ✅ Detected: Decision flag indicates review/analysis needed
```

**Example 3: Review tags**
```bash
/task-create "Code quality assessment" tags:[code-review,assessment]
# ✅ Detected: Tags indicate review task
```

**Example 4: Title keywords**
```bash
/task-create "Evaluate caching strategy options"
# ✅ Detected: "Evaluate" keyword in title
```

**Example 5: Not a review task**
```bash
/task-create "Implement user authentication"
# ❌ Not detected: Implementation task, no review indicators
# Suggestion not shown, proceeds normally
```

### Why Detection Helps

1. **Command Selection**: Helps you choose `/task-review` vs `/task-work`
2. **Workflow Efficiency**: Review tasks skip implementation phases
3. **Better Reports**: Review mode generates structured analysis reports
4. **Decision Support**: Review tasks include decision checkpoints ([A]ccept/[R]evise/[I]mplement/[C]ancel)

### Overriding Detection

If you want to use `/task-work` for a task that was detected as review:

```bash
# Task detected as review, but you want implementation workflow
/task-create "Review authentication architecture"
# [Suggestion shown]
# Choose Y to create task

# Use /task-work instead of /task-review
/task-work TASK-XXX
# Works fine, detection is only a suggestion
```

### See Also

- [task-create.md - Review Task Detection](./task-create.md#review-task-detection)
- [CLAUDE.md - Review Workflow](../../CLAUDE.md#review-vs-implementation-workflows)

## Examples

```bash
# Basic architectural review (default mode)
/task-review TASK-042

# Code quality review with comprehensive depth
/task-review TASK-043 --mode=code-quality --depth=comprehensive

# Quick decision analysis with summary output
/task-review TASK-044 --mode=decision --depth=quick --output=summary

# Security audit with detailed report
/task-review TASK-045 --mode=security --output=detailed

# Ad-hoc (description form): self-creates the review task, then reviews
/task-review "auth redirect loops after logout" --mode=code-quality

# Ad-hoc decision analysis
/task-review "should the exporter batch or stream?" --mode=decision --depth=quick
```

## Clarification Integration

The `/task-review` command uses the `clarification-questioner` subagent to collect review scope preferences before analysis begins.

### Context A: Review Scope Clarification (Phase 1)

**Purpose**: Clarify what the review should focus on and what trade-offs to prioritize before analysis begins.

**When Triggered**:
- Decision mode tasks (always, unless --no-questions)
- Complexity ≥4 (unless quick depth or --no-questions)
- User specifies --with-questions flag

**When Skipped**:
- User specifies --no-questions flag
- Quick depth reviews (complexity <4)
- Review scope already well-defined in task description

**Example Flow**:

```bash
/task-review TASK-b2c4 --mode=decision --depth=standard

Phase 1: Loading context...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 REVIEW SCOPE CLARIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Review Focus
    What aspects should this analysis focus on?

    [A]ll aspects - Comprehensive analysis
    [T]echnical only - Focus on technical feasibility
    [R]chitecture - Architecture and design patterns
    [P]erformance - Performance and scalability
    [S]ecurity - Security considerations

    Default: [A]ll aspects
    Your choice [A/T/R/P/S]: A

Q2. Analysis Depth
    How deep should the analysis go?

    [Q]uick (surface-level) - 15-30 minutes
    [S]tandard (recommended) - 1-2 hours
    [D]eep (comprehensive) - 4-6 hours

    Default: [S]tandard (recommended)
    Your choice [Q/S/D]: S

Q3. Trade-off Priority
    What trade-offs are you optimizing for?

    [S]peed of delivery
    [Q]uality/reliability
    [C]ost
    [M]aintainability
    [B]alanced

    Default: [B]alanced
    Your choice [S/Q/C/M/B]: Q

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Recorded 3 decisions - proceeding with review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 2: Analyzing with focus: All aspects, Quality/reliability priority...
```

**Questions Asked** (Context A):
1. **Review Focus** - What aspects to analyze (all/technical/architecture/performance/security)
2. **Analysis Depth** - How thorough to be (quick/standard/deep)
3. **Trade-off Priority** - What to optimize for (speed/quality/cost/maintainability/balanced)
4. **Specific Concerns** - Any particular areas of concern (free-form, optional)
5. **Extensibility** - Consider future extensibility? (yes/no/default based on complexity)

**Benefits**:
- Focuses analysis on what matters most
- Sets appropriate depth expectations
- Captures user priorities for decision-making
- Reduces back-and-forth clarification during review

### Context B: Implementation Preferences ([I]mplement Handler)

**Purpose**: Clarify how subtasks should be created and executed when user chooses to implement review findings.

**When Triggered**:
- User selects [I]mplement at decision checkpoint
- Multiple subtasks will be created (≥2)
- Unless --no-questions flag specified

**When Skipped**:
- User specifies --no-questions flag
- Single subtask only
- User selects [A]ccept, [R]evise, or [C]ancel instead

**Example Flow**:

```bash
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DECISION CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Review Results:
  Architecture Score: 72/100
  Findings: 8
  Recommendations: 5

Key Recommendations:
  1. Migrate to JWT-based authentication (Recommended)
  2. Implement Argon2 password hashing
  3. Add rate limiting middleware
  4. Update session management logic
  5. Add integration tests for auth flow

Decision Options:
  [A]ccept - Approve findings
  [R]evise - Request deeper analysis
  [I]mplement - Create implementation tasks
  [C]ancel - Discard review

Your choice: I

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 IMPLEMENTATION PREFERENCES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Approach Selection
    The review identified 3 approaches. Recommended: JWT with refresh tokens.
    Which should subtasks follow?

    [1] JWT with refresh tokens (Recommended)
    [2] Session-based auth
    [3] OAuth 2.0 integration
    [R]ecommend for me

    Default: [R]ecommend for me
    Your choice [1/2/3/R]: 1

Q2. Execution Preference
    How should 5 subtasks be executed?

    [M]aximize parallel - Use Conductor workspaces
    [S]equential - Simpler execution
    [D]etect automatically (recommended)

    Default: [D]etect automatically (recommended)
    Your choice [M/S/D]: M

Q3. Testing Depth
    What testing depth for subtasks?

    [F]ull TDD (test-first for all subtasks)
    [S]tandard (quality gates only)
    [M]inimal (compilation only)
    [D]efault (based on complexity)

    Default: [D]efault (based on complexity)
    Your choice [F/S/M/D]: S

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Creating 5 subtasks with preferences:
  - Approach: JWT with refresh tokens
  - Execution: Parallel (3 Conductor workspaces)
  - Testing: Standard (quality gates)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Questions Asked** (Context B):
1. **Approach Selection** - Which recommended approach to follow (from review options)
2. **Execution Preference** - Parallel vs sequential execution (Conductor integration)
3. **Testing Depth** - Testing rigor for subtasks (TDD/standard/minimal/default)
4. **Constraints** - Any implementation constraints (time/resource/scope/none)
5. **Workspace Naming** - Conductor workspace naming preference (auto/custom/none)

**Benefits**:
- Eliminates ambiguity about which approach to implement
- Optimizes for Conductor parallel execution when beneficial
- Sets appropriate testing expectations for all subtasks
- Captures constraints upfront to avoid rework

### Complexity-Based Gating

The `clarification-questioner` subagent uses task complexity to determine when clarification is needed.

**Gating Rules**:

| Complexity | Review Mode | Behavior |
|------------|-------------|----------|
| 0-3 | Any | Skip (unless --with-questions) |
| 4-6 | decision, architectural | Ask |
| 4-6 | code-quality, technical-debt, security | Skip (unless --with-questions) |
| 7-10 | Any | Always ask (unless --no-questions) |

**Flags**:
- `--no-questions`: Skip clarification entirely
- `--with-questions`: Force clarification
- `--defaults`: Apply defaults without prompting
- `--answers="..."`: Inline answers for automation

**Examples**:

```bash
# Complexity 3, code-quality → No clarification
/task-review TASK-XXX --mode=code-quality
# Phase 1: Loads context (no questions)
# Phase 5: [I]mplement → Uses auto-detection

# Complexity 5, decision → Context A questions
/task-review TASK-XXX --mode=decision
# Phase 1: Asks focus, depth, tradeoffs
# Phase 5: [I]mplement → Context B questions (if 2+ subtasks)

# Complexity 8, architectural → Both contexts
/task-review TASK-XXX --mode=architectural
# Phase 1: Asks all Context A questions
# Phase 5: [I]mplement → Asks all Context B questions

# Override gating with --with-questions
/task-review TASK-XXX --mode=code-quality --with-questions
# Phase 1: Forces Context A questions
# Phase 5: [I]mplement → Forces Context B questions

# Disable all clarification
/task-review TASK-XXX --mode=decision --no-questions
# Phase 1: Skips Context A
# Phase 5: [I]mplement → Skips Context B
```

**Why Complexity Gating?**

1. **Simple reviews** (0-3): Scope is clear, defaults work fine
2. **Medium reviews** (4-6): Clarification valuable for decision/architectural modes
3. **Complex reviews** (7-10): Clarification essential to focus effort correctly

This ensures clarification adds value without creating unnecessary friction.

## Flags

### --mode=MODE

Specifies the type of review to perform.

**Values**:
- `architectural` (default) - Architecture and design review
- `code-quality` - Code quality and maintainability assessment
- `decision` - Technical decision analysis
- `technical-debt` - Technical debt inventory and prioritization
- `security` - Security audit and vulnerability assessment

**Examples**:
```bash
/task-review TASK-XXX --mode=architectural
/task-review TASK-XXX --mode=code-quality
/task-review TASK-XXX --mode=decision
```

### --depth=DEPTH

Controls the thoroughness of the review.

**Values**:
- `quick` - Surface-level review (15-30 minutes)
- `standard` (default) - Thorough review (1-2 hours)
- `comprehensive` - Exhaustive analysis (4-6 hours)

**Examples**:
```bash
/task-review TASK-XXX --depth=quick
/task-review TASK-XXX --depth=standard
/task-review TASK-XXX --depth=comprehensive
```

### --output=FORMAT

Specifies the output format for the review report.

**Values**:
- `summary` - Executive summary only
- `detailed` (default) - Full analysis report
- `presentation` - Presentation/slide deck format

**Examples**:
```bash
/task-review TASK-XXX --output=summary
/task-review TASK-XXX --output=detailed
/task-review TASK-XXX --output=presentation
```

### --no-questions

Disables all clarification questions (Context A and Context B).

**When to Use**:
- Automated/CI workflows where user input not available
- Well-defined reviews where defaults are acceptable
- Quick iterations where minimal friction desired

**Behavior**:
- Context A: Skipped, uses review mode defaults
- Context B: Skipped, uses auto-detection for all preferences
- No prompts shown during review or [I]mplement

**Examples**:
```bash
# CI/CD pipeline - no user interaction
/task-review TASK-XXX --mode=security --no-questions

# Quick review with defaults
/task-review TASK-XXX --depth=quick --no-questions
```

### --with-questions

Forces clarification questions to be presented, even for simple reviews.

**When to Use**:
- Want explicit control over review scope
- Complex decisions requiring human judgment
- Learning/exploration mode

**Behavior**:
- Context A: Always presented (Phase 1)
- Context B: Always presented (if [I]mplement chosen)
- Overrides complexity-based gating

**Examples**:
```bash
# Force questions for simple review
/task-review TASK-XXX --mode=code-quality --with-questions

# Explicit control over scope
/task-review TASK-XXX --mode=architectural --with-questions
```

### --defaults

Uses default answers for all clarification questions without prompting.

**When to Use**:
- Testing/validation scenarios
- Standard workflows where defaults are well-calibrated
- Batch processing of multiple reviews

**Behavior**:
- Context A: Default values auto-applied (no prompts)
- Context B: Default values auto-applied (no prompts)
- Equivalent to pressing Enter for all questions

**Examples**:
```bash
# Use defaults for all questions
/task-review TASK-XXX --defaults

# Combine with specific mode
/task-review TASK-XXX --mode=decision --defaults
```

### --capture-knowledge

Triggers a knowledge capture session after review completion. This captures insights and decisions from the review for future reference.

**When to Use**:
- Reviews with significant findings worth documenting
- Decision reviews where rationale should be preserved
- Architectural reviews with important patterns identified
- Security reviews with lessons learned

**Behavior**:
- Triggered after review completion, before decision checkpoint
- Generates 3-5 context-specific questions based on review findings
- Questions tailored to review mode (architectural, security, decision, etc.)
- Captured knowledge linked to task context for searchability
- Works with all review modes

**Context-Specific Questions**:
Questions are generated based on review mode and findings:
- *Architectural*: "What architectural patterns were identified?" "Which SOLID violations should be addressed?"
- *Security*: "What security concerns were identified?" "Which vulnerabilities should be addressed immediately?"
- *Decision*: "What decision was made?" "What alternatives were considered?"
- *Code-quality*: "What code quality issues were most significant?" "What refactoring opportunities were identified?"
- *Technical-debt*: "What technical debt items were identified?" "How can similar debt be prevented?"

**Examples**:
```bash
# Capture knowledge after architectural review
/task-review TASK-XXX --mode=architectural --capture-knowledge

# Capture knowledge after security audit
/task-review TASK-XXX --mode=security --depth=comprehensive --capture-knowledge

# Combine with decision mode for important decisions
/task-review TASK-XXX --mode=decision --capture-knowledge
```

**Short Flag**: `-ck` is equivalent to `--capture-knowledge`

```bash
# Using short flag
/task-review TASK-XXX --mode=architectural -ck
```

### Flag Combinations

**Common Patterns**:

```bash
# Interactive review with full clarification
/task-review TASK-XXX --mode=architectural --with-questions

# Silent automation (no questions, use defaults)
/task-review TASK-XXX --no-questions

# Semi-automated (apply defaults without prompts)
/task-review TASK-XXX --defaults

# Review with knowledge capture
/task-review TASK-XXX --mode=architectural --capture-knowledge

# Invalid: contradictory flags (--no-questions wins)
/task-review TASK-XXX --no-questions --with-questions
```

**Flag Priority**:
1. `--no-questions` (highest priority - disables all clarification)
2. `--defaults` (auto-applies defaults without prompts)
3. `--with-questions` (forces clarification to be presented)
4. `--capture-knowledge` (independent - can combine with any other flags)
5. Complexity-based gating (default behavior if no flags)

## Workflow Phases

The `/task-review` command executes these phases automatically:

### Phase 0: Ad-Hoc Task Creation (Description Form Only)

Runs ONLY when the first argument is a description (does not match the task-id pattern
`^TASK(-[A-Z0-9]{2,4})?-[A-Fa-f0-9]{4,6}$`). ID-form invocations skip straight to Phase 1.

**GUARD**: if the argument DOES match the id pattern but no task file exists in any
`tasks/{state}/` directory, fail with the standard "Task TASK-XXX not found" error.
Never reinterpret a missing ID as a description.

**EXECUTE** (Bash):
```bash
guardkit task create "{description}" --prefix REV --task-type review
```

**BINARY FALLBACK**: the installed `guardkit` shell wrapper may not dispatch the `task`
subcommand ("Unknown command: task") — the subcommand lives in the Python CLI. If the first
form fails that way, retry with the Python entry point: `guardkit-py task create ...`, or the
repo venv's `.venv/bin/guardkit-py` when working inside the guardkit repo itself.

**PARSE** the created task id and path from the command output
(`Created task: TASK-REV-{hash}-{slug}.md` / `Location: {path}`). The created file carries
`task_type: review` frontmatter and a `## Review Scope` section seeded with the description,
so it satisfies this command's Execution Protocol prerequisites without editing.

**ON FAILURE** (non-zero exit after the binary fallback, or unparseable output): STOP with
the error and suggest the two-step fallback (`/task-create "..." task_type:review` then
`/task-review TASK-REV-XXXX`). Do NOT hand-write a task file.

**DISPLAY**:
```
Phase 0: Ad-hoc review task created
  Task: {task_id} — {description}
  File: tasks/backlog/{filename}
  Proceeding to review (mode: {mode}, depth: {depth})
```

**Continue to Phase 1 with {task_id}** — from this point the ad-hoc form is
indistinguishable from the ID form.

### Phase 1: Load Review Context (with Optional Clarification)

**READ** task file from: tasks/{state}/TASK-{id}-*.md

**PARSE** task metadata:
- Task ID: {task_id}
- Title: {task_title}
- Complexity: {task_complexity}
- Review mode: {review_mode} (from --mode flag or task frontmatter)

**IF** --no-questions flag is NOT set:

  **INVOKE** Task tool:
  ```
  subagent_type: "clarification-questioner"
  description: "Collect review scope clarifications for {task_id}"
  prompt: "Execute clarification for task review.

  CONTEXT TYPE: review_scope

  TASK CONTEXT:
    Task ID: {task_id}
    Title: {task_title}
    Description: {task_description}
    Review Mode: {review_mode}
    Complexity: {task_complexity}/10

  FLAGS:
    --no-questions: {flags.no_questions}
    --with-questions: {flags.with_questions}
    --defaults: {flags.defaults}
    --answers: {flags.answers}

  Ask about:
  1. Review focus (all/technical/architecture/performance/security)
  2. Analysis depth (quick/standard/deep)
  3. Trade-off priority (speed/quality/cost/maintainability/balanced)
  4. Specific concerns (optional, free-form)
  5. Extensibility consideration (yes/no/default)

  Apply complexity gating:
  - Complexity 0-3: Skip unless --with-questions
  - Complexity 4-6 + decision/architectural mode: Ask
  - Complexity 7+: Always ask

  Return ClarificationContext with review preferences."
  ```

  **WAIT** for agent completion

  **STORE** clarification_context for review analysis

  **DISPLAY**:
  ```
  Phase 1: Review context loaded
    Clarification mode: {clarification_context.mode}
    Focus: {clarification_context.get_decision('focus', 'all')}
    Depth: {clarification_context.get_decision('depth', 'standard')}
    Trade-off Priority: {clarification_context.get_decision('tradeoff', 'balanced')}
  ```

**ELSE**:
  **DISPLAY**: "Review scope clarification skipped (--no-questions)"
  **SET** clarification_context = None

**Continue with context loading**:
- Identify review scope and objectives (using clarification if provided)
- Load relevant codebase files/modules
- Load related design documents and ADRs

### Phase 1.5: Fleet-Memory Review Context Loading (Knowledge Store)

**Purpose**: Load review-relevant context from the fleet-memory knowledge store to enrich review analysis with historical patterns, past review findings, and ADR rationale.

**Trigger**: Always execute after Phase 1 context loading (fast no-op if fleet-memory unavailable)

**Skip Conditions**:
- `--no-context` flag is set

**Reference**: See `docs/internals/commands-lib/memory-preamble.md` for the shared availability check pattern.

**STEP 1: Check Fleet-Memory Availability (Tier 0 → Tier 1 Fallback)**

Follow the tiered availability check from `docs/internals/commands-lib/memory-preamble.md`:

**Tier 0 — MCP Tools (Preferred)**:

Check whether `mcp__fleet_memory__memory_search` is available in the current session.

**IMPORTANT — Deferred tools**: In Claude Code sessions, MCP tools are often
listed in the system reminder as "deferred" (loadable via `ToolSearch`) rather
than appearing directly in the immediate tool list. Treat deferred tools as
**available**.

If `mcp__fleet_memory__memory_search` is **not** in the immediate tool list, scan
the session's deferred-tool list (system reminder block). If present there,
load schemas first:

```
ToolSearch(query: "select:mcp__fleet_memory__memory_search,mcp__fleet_memory__memory_write_payload")
```

- **IF** available (immediately or after ToolSearch load):
  - SET `memory_available = true`
  - SET `memory_access = "mcp"`
  - Skip to Step 2 (MCP Query)

- **IF** absent from BOTH the immediate AND deferred-tool lists:
  - Fall through to Tier 1

**Tier 1 — CLI Availability Check (Bash Fallback)**:

Run via the Bash tool:

```bash
guardkit memory status
```

- **IF** the output reports `Status: REACHABLE`:
  - SET `memory_available = true`
  - SET `memory_access = "cli"`

- **IF** the output reports `UNAVAILABLE`, `DISABLED`, `DEGRADED`, or errors:
  - SET `memory_available = false`
  - DISPLAY: `[Fleet-Memory] Review context: unavailable (continuing without)`
  - SET `review_memory_context = None`
  - PROCEED to Phase 2

**STEP 2: Load Review Context from Fleet-Memory**

Fleet-memory collapses the old paired node+fact searches into a single
`memory_search` call per concern. The old group_ids map to `payload_types` /
`domain_tags` (see `docs/internals/commands-lib/memory-preamble.md`):
`project_decisions` → `adr` / `["project"]`, `task_outcomes` → `build_outcome` /
`["task"]`.

**IF** `memory_access == "mcp"` (Tier 0):

Execute three `memory_search` calls to gather review-relevant context:

```
# Query 1: Architecture / project decisions related to review scope
mcp__fleet_memory__memory_search(
  project="guardkit",
  query="architecture decisions related to {task_title} {review_mode}",
  payload_types=["adr", "document"],
  domain_tags=["architecture", "project"],
  token_budget=2000
)

# Query 2: Past failure patterns and outcomes
mcp__fleet_memory__memory_search(
  project="guardkit",
  query="past failures patterns issues related to {task_description_keywords}",
  payload_types=["build_outcome"],
  domain_tags=["task"],
  token_budget=2000
)

# Query 3: Similar past reviews and findings
mcp__fleet_memory__memory_search(
  project="guardkit",
  query="previous review findings recommendations for {review_scope_keywords}",
  payload_types=["review_report", "build_outcome"],
  domain_tags=["review", "task"],
  token_budget=2000
)
```

Each call returns `{context_block, coverage_score, contributing_types, tokens_used}`.
A non-empty `context_block` (or `coverage_score > 0`) means matching knowledge exists.

Parse results and assemble context:

```python
review_memory_context = {
    "architecture_decisions": "",  # context_block from Query 1 (ADRs / project decisions)
    "past_failures": "",           # context_block from Query 2 (failure patterns to check)
    "similar_reviews": "",         # context_block from Query 3 (previous review findings)
    "total_items": 0               # count of non-empty context blocks loaded
}

# Populate from memory_search results (each result carries a context_block)
if query_1_results.get("context_block"):
    review_memory_context["architecture_decisions"] = query_1_results["context_block"]

if query_2_results.get("context_block"):
    review_memory_context["past_failures"] = query_2_results["context_block"]

if query_3_results.get("context_block"):
    review_memory_context["similar_reviews"] = query_3_results["context_block"]

review_memory_context["total_items"] = sum(
    1 for key in ("architecture_decisions", "past_failures", "similar_reviews")
    if review_memory_context[key]
)
```

**ELSE IF** `memory_access == "cli"` (Tier 1 fallback):

Run the same three searches via the Bash tool (writes still require the MCP tool,
but search works over the CLI):

```bash
guardkit memory search "architecture decisions related to {task_title} {review_mode}" \
    --payload-types adr --payload-types document \
    --domain-tags architecture --domain-tags project --token-budget 2000

guardkit memory search "past failures patterns issues related to {task_description_keywords}" \
    --payload-types build_outcome --domain-tags task --token-budget 2000

guardkit memory search "previous review findings recommendations for {review_scope_keywords}" \
    --payload-types review_report --payload-types build_outcome \
    --domain-tags review --domain-tags task --token-budget 2000
```

- **IF** any search returns a non-empty context block:
  - SET the corresponding `review_memory_context` field to that block
- **IF** all searches return empty:
  - SET `review_memory_context = None`
  - DISPLAY: `[Fleet-Memory] Review context: loading failed (continuing without)`

**STEP 3: Display and Store Context**

**IF** `review_memory_context` is not None and has items:

```
DISPLAY:
[Fleet-Memory] Review context loaded via {memory_access}: {total_items} context blocks
  - Architecture / project decisions: {"present" if architecture_decisions else "none"}
  - Past failure patterns: {"present" if past_failures else "none"}
  - Similar past reviews: {"present" if similar_reviews else "none"}
```

Store `review_memory_context` and `memory_access` for injection into Phase 2 agent prompts.

**ELSE**:

```
DISPLAY:
[Fleet-Memory] Review context: unavailable (continuing without)
```

SET `review_memory_context = None`
SET `memory_access = None`

**ERROR HANDLING**:

All fleet-memory operations follow the graceful degradation pattern:
1. MCP tools handle errors internally and return empty results
2. The CLI reports `UNAVAILABLE`/`DEGRADED`/errors via `guardkit memory status`
3. Any exception → treat as unavailable, continue without blocking

Task-review NEVER blocks or fails due to fleet-memory errors.

### Phase 2: Execute Review Analysis

**INVOKE** appropriate review agent based on --mode flag:

{if clarification_context:}
**REVIEW SCOPE** (from clarification):
  Focus: {clarification_context.get_decision('focus', 'all')}
  Depth: {clarification_context.get_decision('depth', 'standard')}
  Trade-off Priority: {clarification_context.get_decision('tradeoff', 'balanced')}
  Specific Concerns: {clarification_context.get_decision('concerns', 'none')}
  Extensibility: {clarification_context.get_decision('extensibility', 'default')}

Prioritize analysis based on these preferences.
{endif}

{if review_memory_context:}
**KNOWLEDGE CONTEXT** (from Phase 1.5 — Fleet-Memory, source: {memory_access}):
The following context was retrieved from the project knowledge store.
Use this to inform review criteria, check for recurrence of known issues,
and validate against existing architectural decisions:

{if review_memory_context.architecture_decisions:}
**Architecture / Project Decisions (ADRs)**:
{review_memory_context.architecture_decisions}
Validate that the code under review conforms to these decisions.
{endif}

{if review_memory_context.past_failures:}
**Past Failure Patterns**:
{review_memory_context.past_failures}
Check for recurrence of these known issues in the current review scope.
{endif}

{if review_memory_context.similar_reviews:}
**Similar Past Reviews**:
{review_memory_context.similar_reviews}
Consider whether previous review findings still apply or have been addressed.
{endif}

IMPORTANT: In your review output, include a "Context Used" section listing
which knowledge items above influenced your findings. Example:
  ## Context Used
  - ADR "Use repository pattern": validated compliance in data access layer
  - Past failure "N+1 queries in UserService": checked for recurrence
{else:}
No knowledge context available — reviewing from codebase analysis only.
{endif}

- Perform analysis using specialized prompts
- Generate findings with supporting evidence
- Score/rate based on review criteria

### Phase 3: Synthesize Recommendations
- Aggregate findings from multiple agents (if applicable)
- Generate actionable recommendations
- Identify decision options (for decision-making tasks)
- Prioritize recommendations by impact

### Phase 4: Generate Review Report
- Create structured markdown report
- Include executive summary
- Document findings with evidence
- Provide recommendations with rationale
- Attach supporting artifacts (diagrams, metrics)

### Phase 4.5: Knowledge Capture (Optional - `--capture-knowledge` flag)

**IF** `--capture-knowledge` flag is set:

**INVOKE** review knowledge capture session:
```python
from guardkit.knowledge.review_knowledge_capture import run_review_capture

result = await run_review_capture(
    task_context=task_context,
    review_findings=review_findings,
    capture_knowledge=True
)
```

**DISPLAY** knowledge capture prompt:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 KNOWLEDGE CAPTURE SESSION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Based on this {review_mode} review, let me capture any insights.

[1/3] ARCHITECTURAL PATTERN
Context: Helps remember patterns identified during reviews

What architectural patterns were identified during this review?
Your answer: _

[2/3] DECISIONS
Context: Captures decisions for future reference

Were there any decisions made that should be remembered?
Your answer: _

[3/3] WARNINGS
Context: Helps avoid similar issues in future tasks

Are there any warnings for similar future tasks?
Your answer: _

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Knowledge captured and linked to {task_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Features**:
- Questions are context-specific based on review mode
- Abbreviated session (3-5 questions max)
- Captured knowledge linked to task_id for searchability
- Supports all review modes (architectural, security, decision, code-quality, technical-debt)
- Graceful degradation if fleet-memory unavailable

**STEP 2: Write captured knowledge to Fleet-Memory**

After the interactive capture session completes, persist the captured knowledge to the fleet-memory knowledge store. This step is non-blocking — capture session success is not affected by the fleet-memory write outcome.

**Check fleet-memory availability** (see `docs/internals/commands-lib/memory-preamble.md` Tier 0 → Tier 1). Writes require the `mcp__fleet_memory__memory_write_payload` tool (there is no `guardkit memory` write CLI other than `capture-outcome`).

**IF** `mcp__fleet_memory__memory_write_payload` tool is available in the current session:

Write captured knowledge as two typed payloads. Sanitise `{task_id}` to underscores only for the `identifier` (e.g. `TASK-REV-A3F2` → `TASK_REV_A3F2`):

1. **Review findings → `review_report` payload** (`domain_tags=["review"]`):

Use `mcp__fleet_memory__memory_write_payload` with:
```
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "review_report",
  "project": "guardkit",
  "identifier": "REVIEW_{task_id}",
  "verdict": "Task {task_id} ({title}) - {review_mode} review. Score: {score}/100.\n\nKey findings:\n{findings_summary}\n\nCaptured insights:\n{captured_answers_summary}",
  "domain_tags": ["review"],
  "source_ref": ".claude/reviews/{task_id}-review-report.md"
})
```

2. **Review outcome → `build_outcome` payload** (`domain_tags=["task"]`):

Prefer the real CLI (writes a `build_outcome` payload directly) via the Bash tool:
```bash
guardkit memory capture-outcome \
  --task-id "{task_id}" \
  --task-title "{title}" \
  --summary "Review {task_id} completed. Mode: {review_mode}. Score: {score}/100. Recommendations: {recommendations_summary}" \
  --success
```

If the CLI is not reachable but the MCP tool is, write the outcome via `mcp__fleet_memory__memory_write_payload` instead:
```
mcp__fleet_memory__memory_write_payload(payload={
  "payload_type": "build_outcome",
  "project": "guardkit",
  "identifier": "REVIEW_OUTCOME_{task_id}",
  "status": "accepted",
  "duration_seconds": 0,
  "domain_tags": ["task"],
  "source_ref": "{task_id}",
  "lessons": "Mode: {review_mode}. Score: {score}/100.\n\nRecommendations:\n{recommendations_summary}"
})
```

**DISPLAY** on success:
```
[Fleet-Memory] ✅ Knowledge captured (review_report + build_outcome payloads)
```

**ELSE IF** MCP write tool not available, **fall through to the CLI outcome write**:

```bash
guardkit memory status
```

If `Status: REACHABLE`, write the review outcome via `guardkit memory capture-outcome`
(as shown above). Note the `review_report` findings payload requires the MCP write
tool — if `memory_access = "cli"`, offer it for review but note it can only be
persisted when the fleet-memory MCP tools are connected, and skip it.

**IF** both the MCP write tool and the CLI are unavailable:

```
[Fleet-Memory] ⚠️ Write failed — continuing without knowledge persistence
  Reason: {error}
```

**Non-blocking** — Phase 4.5 succeeds regardless of the fleet-memory write outcome.

### Phase 5: Human Decision Checkpoint (with Optional Implementation Preferences)
Present findings to user with decision options:
- **[A]ccept** - Approve findings, mark task as `REVIEW_COMPLETE`
- **[R]evise** - Request deeper analysis on specific areas
- **[I]mplement** - Create implementation task based on recommendation
  - **[NEW]** Presents implementation preferences questions (Context B)
  - Triggered if: user chooses [I]mplement and --no-questions not set
  - Questions help clarify: approach selection, parallelization, testing depth, constraints
- **[C]ancel** - Discard review, return task to backlog

## Model Selection Strategy

The `/task-review` command automatically selects the optimal Claude model based on review mode and depth, balancing cost efficiency with quality requirements.

### When Opus 4.5 Is Used

**Opus 4.5** provides superior reasoning for high-value scenarios:

1. **Security reviews** (all depths) - Security breaches cost $100K-$10M, model costs $1-5
2. **Decision analysis** (standard/comprehensive) - Complex trade-offs require deep reasoning
3. **Comprehensive architectural reviews** - Thorough SOLID/DRY/YAGNI analysis
4. **Comprehensive technical debt** - Nuanced effort vs impact prioritization

**Cost**: $0.45-$1.65 per review (67% premium vs Sonnet)

### When Sonnet 4.5 Is Used

**Sonnet 4.5** provides excellent quality for most scenarios:

1. **Quick reviews** (except security) - Speed matters
2. **Code quality reviews** (all depths) - Metrics are objective
3. **Standard architectural reviews** - Pattern-based analysis sufficient
4. **Standard technical debt** - Straightforward prioritization

**Cost**: $0.09-$0.68 per review

### Cost Transparency

Before each review, you'll see:
```
======================================================================
📊 Review Cost Estimate
======================================================================
Model: claude-opus-4-20250514
Estimated tokens: 150,000
Estimated cost: $1.13
Rationale: comprehensive depth requires deep analysis,
           security reviews always use Opus 4.5
======================================================================
```

This ensures you always know which model will be used and why.

## Review Modes (Detailed)

### Architectural Review Mode

**Purpose**: Evaluate system design against SOLID/DRY/YAGNI principles

**Agents Used**:
- `architectural-reviewer` (primary)
- `pattern-advisor` (if Design Patterns MCP available)
- `software-architect` (for recommendations)

**Output Sections**:
1. Architecture Assessment (scored 0-100)
   - SOLID Compliance (0-10 per principle)
   - DRY Adherence (0-10)
   - YAGNI Compliance (0-10)
2. Design Patterns Analysis
3. Technical Debt Inventory
4. Recommendations (Keep/Refactor/Rewrite)

### Code Quality Review Mode

**Purpose**: Assess code maintainability, complexity, test coverage

**Agents Used**:
- `code-reviewer` (primary)
- `test-orchestrator` (for coverage analysis)

**Output Sections**:
1. Code Metrics (complexity, LOC, duplication, coverage)
2. Quality Issues (code smells, anti-patterns)
3. Maintainability Score (0-10)
4. Refactoring Recommendations

### Decision Analysis Mode

**Purpose**: Evaluate options and provide decision recommendation

**Agents Used**:
- `software-architect` (primary)
- `architectural-reviewer` (for technical assessment)
- Stack-specific specialists (for implementation details)

**Output Sections**:
1. Current Situation Assessment
2. Root Cause Analysis (if applicable)
3. Option Evaluation Matrix
4. Recommended Decision with Rationale

### Technical Debt Mode

**Purpose**: Inventory and prioritize technical debt

**Agents Used**:
- `code-reviewer` (primary)
- `architectural-reviewer` (for architectural debt)

**Output Sections**:
1. Technical Debt Inventory
2. Priority Matrix (effort vs impact)
3. Remediation Roadmap
4. Quick Wins vs Strategic Improvements

### Security Audit Mode

**Purpose**: Security vulnerability assessment

**Agents Used**:
- `security-specialist` (primary)
- `code-reviewer` (for code-level issues)

**Output Sections**:
1. Security Findings (OWASP Top 10 mapping)
2. Vulnerability Severity Ratings
3. Remediation Recommendations
4. Compliance Assessment (if applicable)

## Integration with /task-work

The `/task-review` command integrates seamlessly with `/task-work` to support a complete review → implementation → verification workflow.

### Review → Implementation Workflow

**Step 1: Create Review Task**
```bash
/task-create "Review authentication architecture" task_type:review
# Output: Created TASK-REV-A3F2
```

**Step 2: Execute Review**
```bash
/task-review TASK-REV-A3F2 --mode=architectural --depth=standard
# Review runs, generates report at .claude/reviews/TASK-REV-A3F2-review-report.md
# Task status: BACKLOG → IN_PROGRESS → REVIEW_COMPLETE
```

**Step 3: Decision Checkpoint**

After review completion, you'll see:

```
=========================================================================
REVIEW COMPLETE: TASK-REV-A3F2
=========================================================================

Review Results:
  Architecture Score: 72/100
  Findings: 8
  Recommendations: 5

Key Findings:
  - Authentication uses outdated session management
  - Password hashing needs upgrade to Argon2
  - Missing rate limiting on login endpoint

Recommendations:
  1. Migrate to JWT-based authentication
  2. Implement Argon2 password hashing
  3. Add rate limiting middleware
  4. Update session management logic
  5. Add integration tests for auth flow

Decision Options:
  [A]ccept - Archive review (no implementation needed)
  [R]evise - Request deeper analysis
  [I]mplement - Create implementation task based on recommendations
  [C]ancel - Discard review

Your choice:
```

**Step 4a: Choose [I]mplement**

System executes the enhanced auto-detection pipeline:

```bash
================================================================================
🔄 Enhanced [I]mplement Flow - Auto-Detection Pipeline
================================================================================

Step 1/10: Extracting feature slug...
   ✓ Feature slug: authentication-refactor
   ✓ Feature name: Authentication Architecture

Step 2/10: Parsing subtasks from review recommendations...
   ✓ Found 5 subtasks

Step 3/10: Assigning implementation modes...
   ✓ /task-work: 3, Direct: 2, Manual: 0

Step 4/10: Detecting parallel execution groups...
   ✓ Organized into 2 waves

Step 5/10: Generating Conductor workspace names...
   ✓ Assigned 3 workspace names

Step 6/10: Displaying auto-detected configuration...

================================================================================
✅ Auto-detected Configuration:
================================================================================
   Feature slug: authentication-refactor
   Feature name: Authentication Architecture
   Subtasks: 5 (from review recommendations)
   Parallel groups: 2 waves

   Implementation modes:
     • /task-work: 3 tasks
     • Direct: 2 tasks
     • Manual: 0 tasks
================================================================================

Step 7/10: Creating subfolder structure...
   ✓ Created tasks/backlog/authentication-refactor/

Step 8/10: Generating subtask files...
   ✓ Generated 5 task files

Step 9/10: Generating IMPLEMENTATION-GUIDE.md...
   ✓ Guide generated

Step 10/10: Generating README.md...
   ✓ README generated

================================================================================
✅ Feature Implementation Structure Created
================================================================================

Created: tasks/backlog/authentication-refactor/
  ├── README.md
  ├── IMPLEMENTATION-GUIDE.md
  ├── TASK-AR-001-migrate-jwt-auth.md
  ├── TASK-AR-002-implement-argon2.md
  ├── TASK-AR-003-rate-limiting.md
  ├── TASK-AR-004-update-session-mgmt.md
  └── TASK-AR-005-add-integration-tests.md

--------------------------------------------------------------------------------
📋 Execution Strategy:
--------------------------------------------------------------------------------

Wave 1: 3 tasks
  ⚡ Parallel execution (Conductor recommended)
     • TASK-AR-001: Migrate to JWT-based authentication
       Workspace: authentication-refactor-wave1-1
       Method: task-work
     • TASK-AR-002: Implement Argon2 password hashing
       Workspace: authentication-refactor-wave1-2
       Method: task-work
     • TASK-AR-003: Add rate limiting middleware
       Workspace: authentication-refactor-wave1-3
       Method: direct

Wave 2: 2 tasks
  ⚡ Parallel execution (Conductor recommended)
     • TASK-AR-004: Update session management logic
       Workspace: authentication-refactor-wave2-1
       Method: task-work
     • TASK-AR-005: Add integration tests for auth flow
       Workspace: authentication-refactor-wave2-2
       Method: direct

================================================================================
🚀 Next Steps:
================================================================================
1. Review: tasks/backlog/authentication-refactor/IMPLEMENTATION-GUIDE.md
2. Review: tasks/backlog/authentication-refactor/README.md
3. Start with Wave 1 tasks
4. Use Conductor for parallel Wave 1 execution
================================================================================
```

### What [I]mplement Does

When you choose [I]mplement, the system automatically:

1. **Extracts feature slug** from review title (e.g., "Authentication Refactor" → "authentication-refactor")
2. **Parses subtasks** from review recommendations section
3. **Assigns implementation modes** (task-work/direct) based on complexity and risk
4. **Detects parallel groups** by analyzing file conflicts between tasks
5. **Generates workspace names** for Conductor parallel execution
6. **Creates subfolder** at `tasks/backlog/{feature-slug}/`
7. **Generates task files** with complete frontmatter and metadata, including:
   - `parent_review`: Set to the review task ID (format: TASK-REV-{hash})
   - `feature_id`: Set to generated feature ID (format: FEAT-{hash})
   - All standard task fields (wave, implementation_mode, dependencies, etc.)
   - When creating fix tasks that involve cross-component boundaries (e.g. integration tests, environment variable consumers, API contracts between services), include the expected interface format in the task description.
8. **Generates IMPLEMENTATION-GUIDE.md** with wave breakdowns and execution strategy
9. **Generates README.md** with problem statement, solution approach, and subtask summary
10. **Displays execution plan** with next steps

**Provenance tracking**: The `parent_review` and `feature_id` fields enable complete traceability from feature planning through review to implementation. See `.claude/rules/task-workflow.md` for detailed provenance documentation and TASK-INT-e5f6 for the design rationale.

### Enhanced [I]mplement Benefits

**Before (Manual)**:
- Manually create each implementation task
- Guess at implementation modes
- No parallel execution strategy
- No documentation generated

**After (Auto-Detection)**:
- Zero manual task creation
- Smart mode assignment (task-work/direct)
- Automatic parallel group detection
- Complete documentation generated
- Conductor-ready workspace names

**Step 5: Implement Changes**
```bash
/task-work TASK-IMP-B4D1
# Executes implementation with all quality gates:
# - Phase 2: Planning
# - Phase 2.5: Architectural Review
# - Phase 3: Implementation
# - Phase 4: Testing
# - Phase 4.5: Test Enforcement
# - Phase 5: Code Review
```

**Step 6: Verification Review (Optional)**

After implementation, create verification review:

```bash
/task-create "Verify authentication refactoring from TASK-IMP-B4D1" task_type:review
# Output: Created TASK-VER-C5E3

/task-review TASK-VER-C5E3 --mode=code-quality --depth=quick
# Quick verification that changes meet original recommendations
```

### Task State Flow

```
Review Task:
  BACKLOG → IN_PROGRESS → REVIEW_COMPLETE → COMPLETED

Implementation Task (created from [I]mplement):
  BACKLOG → IN_PROGRESS → IN_REVIEW → COMPLETED

Verification Task (optional):
  BACKLOG → IN_PROGRESS → REVIEW_COMPLETE → COMPLETED
```

### Real-World Example: Security Audit

```bash
# 1. Security audit review
/task-create "Security audit of payment processing" task_type:review
/task-review TASK-SEC-D7E2 --mode=security --depth=comprehensive

# 2. Review identifies 12 vulnerabilities
# Decision: [I]mplement

# 3. System creates implementation task
# TASK-IMP-E8F3: Fix security vulnerabilities from TASK-SEC-D7E2

# 4. Implement fixes
/task-work TASK-IMP-E8F3

# 5. Verification review
/task-create "Verify security fixes from TASK-IMP-E8F3" task_type:review
/task-review TASK-VER-F9G4 --mode=security --depth=standard

# 6. Verification passes, close all tasks
/task-complete TASK-VER-F9G4
/task-complete TASK-IMP-E8F3
/task-complete TASK-SEC-D7E2
```

### Benefits of Integration

1. **Traceability**: Implementation tasks linked to review findings
2. **Context Preservation**: Review report available during implementation
3. **Consistent Quality**: Implementation goes through all quality gates
4. **Verification Loop**: Optional verification review closes the cycle
5. **Automated Task Creation**: [I]mplement option eliminates manual task creation

### See Also

- [CLAUDE.md Review Workflow](../../CLAUDE.md#review-vs-implementation-workflows)
- [Task Review Workflow Guide](../../docs/workflows/task-review-workflow.md)
- [task-create.md](./task-create.md#review-task-detection)

## Task States and Transitions

```
BACKLOG → IN_PROGRESS → REVIEW_COMPLETE → Completed/Implemented
              ↓
           BLOCKED
```

**States**:
- `BACKLOG`: Review task not started
- `IN_PROGRESS`: Review in progress
- `REVIEW_COMPLETE`: Review finished, awaiting human decision
- `BLOCKED`: Review cannot proceed (missing context, access issues)

**After Review**:
- Accept findings → Task archived as completed
- Create implementation task → New task in backlog linked to review

## Task Metadata

Review tasks use extended metadata fields:

```yaml
---
id: TASK-XXX
title: Review authentication architecture
status: in_progress
task_type: review                    # NEW: review | implementation | research | docs | declarative
review_mode: architectural           # NEW: architectural | code-quality | decision | etc.
review_depth: standard               # NEW: quick | standard | comprehensive
priority: high
tags: [architecture, security]
---
```

After review completion:

```yaml
---
id: TASK-XXX
status: review_complete
review_results:                      # NEW: Added after review
  score: 72
  findings_count: 8
  recommendations_count: 5
  decision: refactor
  report_path: .claude/reviews/TASK-XXX-review-report.md
---
```

## Integration with Task States

### Creating Review Tasks

```bash
# Create review task
/task-create "Review authentication architecture" task_type:review

# Task created with task_type=review in frontmatter
```

### Executing Review

```bash
# Execute review (automatically detects task_type=review)
/task-review TASK-XXX --mode=architectural

# Review runs, generates report, updates task metadata
```

### Post-Review Actions

**Option 1: Accept findings (archive task)**
```bash
# User chooses [A]ccept at checkpoint
# Task moved to completed, report archived
```

**Option 2: Create implementation task**
```bash
# User chooses [I]mplement at checkpoint
# New task created in backlog:
# /task-create "Refactor authentication based on TASK-XXX findings" related_to:TASK-XXX
```

**Option 3: Revise review**
```bash
# User chooses [R]evise at checkpoint
# Review re-runs with additional focus areas
/task-review TASK-XXX --mode=architectural --depth=comprehensive
```

## Execution Protocol

### Prerequisites
1. Task must exist in `tasks/` directory (ID form) — the description form satisfies this
   itself via Phase 0's `guardkit task create --task-type review`
2. Task must have `task_type: review` in frontmatter (optional, defaults to review)
3. Review scope must be defined in task description (Phase 0 seeds it from the ad-hoc
   description)

### Validation
- Validates `--mode` against allowed values
- Validates `--depth` against allowed values
- Validates `--output` against allowed values
- Checks task exists and is accessible

### Error Handling

**Common Errors**:

```bash
# Invalid review mode
❌ Error: Invalid review mode 'invalid-mode'
   Allowed: architectural, code-quality, decision, technical-debt, security

# Task not found (an id-shaped argument NEVER falls back to description mode)
❌ Error: Task TASK-XXX not found in any task directory

# Ad-hoc creation failed (description form)
❌ Error: guardkit task create failed — {stderr}
   Fallback: /task-create "..." task_type:review, then /task-review TASK-REV-XXXX

# Missing review scope
❌ Error: Task TASK-XXX missing review scope in description
   Add "Review Scope" section to task description

# Insufficient context
⚠️  Warning: Review scope references non-existent files
   Proceeding with available context
```

## Output Files

### Review Report
**Location**: `.claude/reviews/TASK-XXX-review-report.md`

**Format**:
```markdown
# Review Report: TASK-XXX

## Executive Summary
[Brief overview of findings and recommendations]

## Review Details
- **Mode**: Architectural Review
- **Depth**: Standard
- **Duration**: 1.5 hours
- **Reviewer**: architectural-reviewer agent

## Findings
1. [Finding 1 with evidence]
2. [Finding 2 with evidence]
...

## Recommendations
1. [Recommendation 1 with rationale]
2. [Recommendation 2 with rationale]
...

## Decision Matrix
| Option | Score | Effort | Risk | Recommendation |
|--------|-------|--------|------|----------------|
| ... | ... | ... | ... | ... |

## Appendix
- Supporting diagrams
- Code samples
- Metrics
```

### Task Metadata Update
**Location**: Task file frontmatter

**Added Fields**:
```yaml
review_results:
  mode: architectural
  depth: standard
  score: 72
  findings_count: 8
  recommendations_count: 5
  decision: refactor
  report_path: .claude/reviews/TASK-XXX-review-report.md
  completed_at: 2025-01-20T16:30:00Z
```

## Best Practices

### When to Use `/task-review`

**Use for**:
- ✅ "Should we implement X?" (decision analysis)
- ✅ "Review the architecture of X" (architectural review)
- ✅ "Assess code quality of X" (code quality review)
- ✅ "Identify technical debt in X" (technical debt assessment)
- ✅ "Audit security of X" (security audit)

**Don't use for**:
- ❌ "Implement feature X" (use `/task-work`)
- ❌ "Fix bug in X" (use `/task-work`)
- ❌ "Refactor X" (use `/task-work`)

### Review Depth Selection

**Quick** (15-30 min):
- Initial assessment
- Sanity check before major work
- High-level overview for stakeholders

**Standard** (1-2 hours):
- Regular code reviews
- Architecture assessments
- Decision analysis for medium complexity

**Comprehensive** (4-6 hours):
- Security audits
- Critical architectural decisions
- Large-scale refactoring planning
- Compliance assessments

### Output Format Selection

**Summary**:
- Executive presentations
- Quick decision-making
- Stakeholder communication

**Detailed**:
- Technical team consumption
- Implementation planning
- Audit trail

**Presentation**:
- Architecture reviews with stakeholders
- Decision presentations
- Training materials

## Advanced Usage

### Chaining Reviews and Implementation

```bash
# 1. Architectural review
/task-review TASK-001 --mode=architectural

# 2. Based on findings, create implementation task
/task-create "Refactor auth based on TASK-001" related_to:TASK-001

# 3. Implement refactoring
/task-work TASK-002

# 4. Post-implementation review
/task-review TASK-003 --mode=code-quality
```

### Iterative Review Refinement

```bash
# 1. Quick initial assessment
/task-review TASK-XXX --depth=quick

# 2. Based on findings, go deeper
/task-review TASK-XXX --depth=comprehensive --focus="authentication layer"
```

## Implementation Notes

### Clarification Integration Code (TASK-CLQ-008)

The clarification module integrates at two points in the `/task-review` workflow.

**Phase 1: Review Scope Clarification (Context A)**

```python
from lib.clarification import (
    generate_review_questions,
    display_questions_full,
)
from lib.clarification.core import ClarificationContext

def execute_phase_1(task_id: str, mode: str, depth: str, flags: dict):
    """Phase 1: Load context with optional clarification."""
    # Load task
    task = load_task(task_id)
    complexity = task.get("complexity", 5)

    # Determine if clarification needed
    review_clarification = None
    should_clarify = (
        not flags.get("no_questions") and (
            flags.get("with_questions") or
            (mode in ["decision", "architectural"] and complexity >= 4) or
            complexity >= 7
        )
    )

    if should_clarify:
        # Generate questions based on mode and complexity
        questions = generate_review_questions(
            task_context=task,
            review_mode=mode,
            complexity=complexity
        )

        if flags.get("defaults"):
            # Auto-apply defaults without prompting
            review_clarification = apply_defaults(questions)
        else:
            # Display questions and collect answers
            review_clarification = display_questions_full(
                questions,
                context_name="REVIEW SCOPE CLARIFICATION"
            )

    # Continue with context loading using clarification (if provided)
    return load_review_context(task, mode, depth, review_clarification)
```

**Phase 5: Implementation Preferences (Context B)**

```python
from lib.clarification.generators.implement_generator import (
    generate_implement_questions,
)

def handle_decision_checkpoint(findings: dict, task: dict, flags: dict):
    """Phase 5: Decision checkpoint with optional implementation preferences."""
    # Display review results
    decision = present_decision_checkpoint(findings)

    if decision == "implement":
        # Determine if clarification needed
        num_subtasks = len(findings.get("recommendations", []))
        complexity = task.get("complexity", 5)

        impl_clarification = None
        should_clarify = (
            not flags.get("no_questions") and
            num_subtasks >= 2
        )

        if should_clarify:
            # Generate implementation preference questions
            questions = generate_implement_questions(
                review_findings=findings,
                num_subtasks=num_subtasks,
                complexity=complexity
            )

            if flags.get("defaults"):
                # Auto-apply defaults
                impl_clarification = apply_defaults(questions)
            else:
                # Display questions and collect answers
                impl_clarification = display_questions_full(
                    questions,
                    context_name="IMPLEMENTATION PREFERENCES"
                )

        # Create implementation subtasks with preferences
        from lib.implement_orchestrator import handle_implement_option
        await handle_implement_option(
            review_task=task,
            review_report_path=findings["report_path"],
            preferences=impl_clarification
        )

    elif decision == "accept":
        # Write review findings to the fleet-memory knowledge store (non-blocking)
        await capture_review_to_memory(task, findings)
        complete_review_task(task)

    elif decision == "revise":
        request_deeper_analysis(task, findings)

    elif decision == "cancel":
        cancel_review(task)
```

**Phase 5 Fleet-Memory Write: `capture_review_to_memory`**

```python
async def capture_review_to_memory(task: dict, findings: dict):
    """Write review findings and outcome to the fleet-memory knowledge store.

    Called automatically on [A]ccept at Phase 5 decision checkpoint.
    Non-blocking — review acceptance succeeds even if the fleet-memory write fails.

    Writes two typed payloads:
    1. Review findings → review_report payload (verdict, domain_tags=["review"])
    2. Review outcome → build_outcome payload (via `guardkit memory capture-outcome`,
       domain_tags=["task"])

    Access method priority:
    - Tier 0: MCP write tool (mcp__fleet_memory__memory_write_payload) — preferred
    - Tier 1: CLI fallback (guardkit memory capture-outcome) — outcome only; the
      review_report findings payload requires the MCP write tool
    - Tier 2: Skip silently — if both unavailable
    """
    task_id = task.get("task_id", task.get("id", "unknown"))
    # Sanitise the task id for the payload identifier (underscores only)
    safe_id = task_id.replace("-", "_").replace(":", "_").lstrip("@")
    title = task.get("title", "")
    review_mode = findings.get("mode", findings.get("review_mode", "unknown"))
    score = findings.get("score", "N/A")

    # Build findings summary
    finding_items = findings.get("findings", [])
    findings_lines = []
    for f in finding_items:
        if isinstance(f, dict):
            desc = f.get("description", str(f))
            severity = f.get("severity", "")
            prefix = f"[{severity.upper()}] " if severity else ""
            findings_lines.append(f"- {prefix}{desc}")
        else:
            findings_lines.append(f"- {f}")
    findings_summary = "\n".join(findings_lines) if findings_lines else "No specific findings."

    # Build recommendations summary
    recommendations = findings.get("recommendations", [])
    rec_lines = []
    for i, r in enumerate(recommendations, 1):
        rec_text = r.get("text", str(r)) if isinstance(r, dict) else str(r)
        rec_lines.append(f"{i}. {rec_text}")
    rec_summary = "\n".join(rec_lines) if rec_lines else "No recommendations."

    # Payload 1: Review findings → review_report (verdict field)
    findings_verdict = (
        f"Task {task_id} ({title}) - {review_mode} review.\n\n"
        f"Key findings:\n{findings_summary}\n\n"
        f"Score: {score}/100"
    )

    # Payload 2: Review outcome → build_outcome (summary/lessons)
    outcome_summary = (
        f"Review {task_id} completed. Mode: {review_mode}. "
        f"Score: {score}/100.\n\nRecommendations:\n{rec_summary}"
    )

    try:
        # Tier 0: Try the MCP write tool (preferred)
        # Check if mcp__fleet_memory__memory_write_payload is available; IF available:
        mcp__fleet_memory__memory_write_payload(payload={
            "payload_type": "review_report",
            "project": "guardkit",
            "identifier": f"REVIEW_{safe_id}",
            "verdict": findings_verdict,
            "domain_tags": ["review"],
            "source_ref": f".claude/reviews/{task_id}-review-report.md",
        })
        mcp__fleet_memory__memory_write_payload(payload={
            "payload_type": "build_outcome",
            "project": "guardkit",
            "identifier": f"REVIEW_OUTCOME_{safe_id}",
            "status": "accepted",
            "duration_seconds": 0,
            "domain_tags": ["task"],
            "source_ref": task_id,
            "lessons": f"Mode: {review_mode}. Score: {score}/100.\n\nRecommendations:\n{rec_summary}",
        })
        print(f"[Fleet-Memory] ✅ Review captured "
              f"(review_report + build_outcome payloads)")

    except Exception:
        # Tier 1: Fall back to the outcome CLI (build_outcome only)
        try:
            import subprocess
            subprocess.run([
                "guardkit", "memory", "capture-outcome",
                "--task-id", task_id,
                "--task-title", title,
                "--summary", outcome_summary,
                "--success",
            ], timeout=30, capture_output=True)
            print(f"[Fleet-Memory] ✅ Review outcome captured via CLI "
                  f"(build_outcome; review_report payload needs the MCP write tool)")
        except Exception as e:
            # Tier 2: Both failed — continue without blocking
            print(f"[Fleet-Memory] ⚠️ Write failed — continuing without knowledge capture")
            print(f"  Reason: {e}")
```

**LLM Execution Instructions for Phase 5 [A]ccept Fleet-Memory Write**:

When the user selects **[A]ccept** at the Phase 5 decision checkpoint, the LLM must:

1. **Check if `mcp__fleet_memory__memory_write_payload` tool is available** in the current session's tool list (sanitise `{task_id}` to underscores only for the `identifier`)

2. **IF the MCP write tool is available** — execute two `mcp__fleet_memory__memory_write_payload` calls:

   **Call 1 — Review findings (`review_report`)**:
   ```
   mcp__fleet_memory__memory_write_payload(payload={
     "payload_type": "review_report",
     "project": "guardkit",
     "identifier": "REVIEW_{safe_task_id}",
     "verdict": "{findings_verdict built from review data}",
     "domain_tags": ["review"],
     "source_ref": ".claude/reviews/{task_id}-review-report.md"
   })
   ```

   **Call 2 — Review outcome (`build_outcome`)**:
   ```
   mcp__fleet_memory__memory_write_payload(payload={
     "payload_type": "build_outcome",
     "project": "guardkit",
     "identifier": "REVIEW_OUTCOME_{safe_task_id}",
     "status": "accepted",
     "duration_seconds": 0,
     "domain_tags": ["task"],
     "source_ref": "{task_id}",
     "lessons": "Mode: {review_mode}. Score: {score}/100. Recommendations: {rec_summary}"
   })
   ```

   **Display**: `[Fleet-Memory] ✅ Review captured (review_report + build_outcome payloads)`

3. **IF the MCP write tool is not available** — check CLI availability via Bash:
   ```bash
   guardkit memory status
   ```
   If `Status: REACHABLE`, write the review outcome via `guardkit memory capture-outcome`
   (`--task-id`, `--task-title`, `--summary`, `--success`). The `review_report` findings
   payload needs the MCP write tool — skip it if only the CLI is reachable. If neither is
   reachable, display the warning and continue.

4. **IF both fail** — display warning and continue:
   ```
   [Fleet-Memory] ⚠️ Write failed — continuing without knowledge capture
     Reason: {error}
   ```

5. **Non-blocking** — proceed to `complete_review_task(task)` regardless of write outcome

**Complete Integration Example**

```python
def execute_task_review(task_id: str, mode: str, depth: str, flags: dict):
    """Complete task-review workflow with clarification integration."""

    # Phase 1: Load Context (with Context A clarification)
    context = execute_phase_1(task_id, mode, depth, flags)

    # Phase 2: Execute Review Analysis
    analysis = execute_review_analysis(context, mode, depth)

    # Phase 3: Synthesize Recommendations
    recommendations = synthesize_recommendations(analysis)

    # Phase 4: Generate Review Report
    report_path = generate_review_report(
        task_id=task_id,
        analysis=analysis,
        recommendations=recommendations
    )

    # Phase 5: Decision Checkpoint (with Context B clarification)
    findings = {
        "analysis": analysis,
        "recommendations": recommendations,
        "report_path": report_path,
    }

    handle_decision_checkpoint(
        findings=findings,
        task=context["task"],
        flags=flags
    )
```

**See**:
- `lib/clarification/core.py` - Core Question/Answer data structures
- `lib/clarification/display.py` - Display and input handling
- `lib/clarification/generators/review_generator.py` - Context A generation
- `lib/clarification/generators/implement_generator.py` - Context B generation
- `lib/clarification/templates/review_scope.py` - Context A question templates
- `lib/clarification/templates/implementation_prefs.py` - Context B question templates

### Enhanced [I]mplement Flow (TASK-FW-008)

The enhanced [I]mplement option requires integration with `lib.implement_orchestrator`:

```python
from lib.implement_orchestrator import handle_implement_option

# When user chooses [I]mplement at decision checkpoint
await handle_implement_option(
    review_task=review_task_dict,
    review_report_path=".claude/reviews/TASK-XXX-review-report.md"
)
```

**Dependencies** (from Wave 2 tasks):
- FW-002: Feature slug extraction (`lib.id_generator`)
- FW-003: Subtask extraction (`lib.review_parser`)
- FW-004: Implementation mode assignment (`lib.implementation_mode_analyzer`)
- FW-005: Parallel group detection (`lib.parallel_analyzer`)
- FW-006: Guide generation (`lib.guide_generator`)
- FW-007: README generation (`lib.readme_generator`)

**See**: `installer/core/lib/implement_orchestrator.py` for orchestration logic

### Development Phases

**Phase 1 Implementation** (Current):
- Core orchestrator structure (Phases 1-5 skeleton)
- Command specification (this file)
- State management (`REVIEW_COMPLETE` state)
- Metadata schema (task_type, review_mode, review_depth)

**Phase 2 Implementation** (TASK-FW-008 - Complete):
- Enhanced [I]mplement flow with auto-detection pipeline
- Feature slug extraction
- Subtask parsing from recommendations
- Implementation mode assignment
- Parallel group detection
- Workspace name generation
- Subfolder structure creation
- Task file generation
- IMPLEMENTATION-GUIDE.md generation
- README.md generation

**Future Phases** (Upcoming):
- Phase 3: Review mode implementations
- Phase 4: Report generation templates
- Phase 5: Integration with task-create
- Phase 6: Comprehensive testing
