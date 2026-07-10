---
format_version: 1
description: Reference slices for /task-work — extended documentation, not a command. Run /task-work.
---

# Task Work — Planning Phases (Step 1 – Phase 2.9)

> **Reference file — not a command.** On-demand extension of `task-work.md`
> (K13 core/`-ext` shape, PB-13 wave 1). The core file's flag table, phase
> sequence, and state-transition rules are normative; nothing here overrides
> them. Flag semantics are defined ONCE in `task-work.md` § Available Flags (PB-9).

## Step 1 — Full File-Resolution Procedure (Phases 1.1–1.7)

#### Phase 1.1: Parse and Validate Task ID

**EXTRACT** task ID from user command:
```python
task_id = extract_task_id(user_input)  # e.g., "TASK-XXX" from "/task-work TASK-XXX"
```

**VALIDATE** task ID format:
- Must match pattern: `TASK-[A-Z0-9-]+` (e.g., TASK-001, TASK-BUG-001, TASK-003B-2)
- Reject if invalid: "Invalid task ID format: {task_id}. Expected format: TASK-XXX"

**DISPLAY**: "Loading task {task_id}..."

#### Phase 1.2: Multi-State File Search

**SEARCH** for task file across multiple states using glob patterns:

Search order (priority from highest to lowest):
1. `tasks/in_progress/{task_id}*.md` (expected location for active tasks)
2. `tasks/backlog/{task_id}*.md` (may need to transition to in_progress)
3. `tasks/blocked/{task_id}*.md` (may need to unblock and continue)
4. `tasks/in_review/{task_id}*.md` (edge case: re-work after review)

**Implementation pattern**:
```python
search_states = [
    ("in_progress", "tasks/in_progress"),
    ("backlog", "tasks/backlog"),
    ("blocked", "tasks/blocked"),
    ("in_review", "tasks/in_review")
]

matches = []
for state_name, state_dir in search_states:
    # Use Glob tool with pattern: {state_dir}/{task_id}*.md
    files = glob(f"{state_dir}/{task_id}*.md")
    for file in files:
        matches.append({
            "path": file,
            "state": state_name,
            "filename": extract_filename(file)
        })

    # Stop searching if found (priority order)
    if matches:
        break
```

**IMPORTANT**: Use Glob tool for file pattern matching, NOT bash find commands.

#### Phase 1.3: Handle Search Results

**CASE A: No matches found**
```python
if len(matches) == 0:
    # Task file not found in any state
    **DISPLAY** error report:
    ```
    ❌ Error: Task file not found

    Task ID: {task_id}
    Searched locations:
      - tasks/in_progress/{task_id}*.md
      - tasks/backlog/{task_id}*.md
      - tasks/blocked/{task_id}*.md
      - tasks/in_review/{task_id}*.md

    Possible causes:
    1. Task ID is incorrect or misspelled
    2. Task file has been deleted
    3. Task has been completed and archived

    Suggestions:
    - Verify task ID: /task-status (lists all tasks)
    - Check completed tasks: ls tasks/completed/
    - Create new task: /task-create "Task title"
    ```
    **EXIT** with error code
```

**CASE B: Single match found**
```python
if len(matches) == 1:
    task_file = matches[0]
    current_state = task_file["state"]
    file_path = task_file["path"]

    **DISPLAY**: "✅ Found: {task_file['filename']} (state: {current_state})"

    # Proceed to Phase 1.4 (automatic state transition if needed)
```

**CASE C: Multiple matches found**
```python
if len(matches) > 1:
    # Multiple files match the pattern (edge case: duplicates)
    **DISPLAY** error report:
    ```
    ⚠️  Warning: Multiple task files found

    Task ID: {task_id}
    Matches:
    {for each match:}
      {index}. {match['filename']} (state: {match['state']})

    This is unexpected and indicates duplicate task files.

    Recommendations:
    1. Review the duplicate files manually
    2. Delete or rename the incorrect file(s)
    3. Ensure only one file per task ID exists

    Locations:
    {for each match:}
      {match['path']}
    ```
    **EXIT** with error code
```

#### Phase 1.4: Automatic State Transition (if needed)

**IF** current_state != "in_progress":

```python
# Task file found in non-active state, needs transition
**DISPLAY** state transition prompt:
```
🔄 Task State Transition Required

Task: {task_id}
Current State: {current_state}
Required State: IN_PROGRESS (for task-work to execute)

File: {file_path}

Automatic transition will:
1. Move file: {current_state}/{filename} → in_progress/{filename}
2. Update task metadata (status, updated timestamp)
3. Preserve all task content and history

Proceed with state transition? [Y/n]:
```

**WAIT** for user confirmation (default: Yes after 5 seconds)

**IF** user confirms (or timeout):
    1. **READ** task file to extract frontmatter and content
    2. **UPDATE** frontmatter metadata:
       ```yaml
       status: in_progress
       updated: {current_timestamp_iso8601}
       previous_state: {current_state}
       state_transition_reason: "Automatic transition for task-work execution"
       ```
    3. **WRITE** updated file to `tasks/in_progress/{filename}`
    4. **DELETE** old file from `tasks/{current_state}/{filename}`
    5. **DISPLAY**: "✅ Transitioned {task_id} from {current_state} to IN_PROGRESS"
    6. **UPDATE** variables:
       ```python
       file_path = f"tasks/in_progress/{filename}"
       current_state = "in_progress"
       ```

**IF** user declines:
    **DISPLAY**: "❌ State transition declined. Cannot execute task-work on {current_state} tasks."
    **EXIT** with error code

**ELSE** (already in_progress):
    # No transition needed, proceed directly
    **DISPLAY**: "✅ Task is already IN_PROGRESS"

#### Phase 1.5: Load Task Context

**READ** task file from final location: `{file_path}`

**FEATURE DETECTION** - Check for require-kit:

RequireKit is considered available when `~/.agentecflow/require-kit.marker.json`
(or the legacy `require-kit.marker`) exists. Set `REQUIREMENTS_AVAILABLE`
from that check so the next step can conditionally load
requirements/BDD/epic/feature fields.

**EXTRACT** required context:
```python
task_context = {
    "task_id": task_id,
    "file_path": file_path,
    "state": current_state,

    # Core fields (always available)
    "title": frontmatter.title,
    "priority": frontmatter.priority,
    "assignee": frontmatter.assignee,
    "description": extract_description(content),
    "acceptance_criteria": extract_acceptance_criteria(content),
    "implementation_notes": extract_implementation_notes(content)
}

# Conditional fields (only if require-kit installed)
if REQUIREMENTS_AVAILABLE:
    task_context["requirements"] = frontmatter.requirements or []      # List of REQ-XXX IDs
    task_context["bdd_scenarios"] = frontmatter.bdd_scenarios or []    # List of BDD-XXX IDs
    task_context["epic"] = frontmatter.epic or None                    # EPIC-XXX
    task_context["feature"] = frontmatter.feature or None              # FEAT-XXX
else:
    # Gracefully skip requirements features if require-kit not installed
    task_context["requirements"] = []
    task_context["bdd_scenarios"] = []
    task_context["epic"] = None
    task_context["feature"] = None
```

**IF BDD MODE**: Load Gherkin scenarios from RequireKit:
```python
# Check if BDD mode is active
if mode == "bdd":
    # RequireKit already validated in Step 0 (TASK-BDD-FIX1)
    # bdd_scenarios field already loaded above

    if not task_context["bdd_scenarios"]:
        print("""
ERROR: BDD mode requires linked Gherkin scenarios

  Task frontmatter must include bdd_scenarios field:

    ---
    id: {task_id}
    title: {title}
    bdd_scenarios: [BDD-001, BDD-002]  ← Add this
    ---

  Generate scenarios in RequireKit:
    cd ~/Projects/require-kit
    /formalize-ears REQ-XXX
    /generate-bdd REQ-XXX

  Or use alternative modes:
    /task-work {task_id} --mode=tdd
    /task-work {task_id} --mode=standard
        """)
        sys.exit(1)

    # Load Gherkin scenario content from RequireKit
    scenarios = []
    requirekit_path = Path.home() / "Projects" / "require-kit"

    for scenario_id in task_context["bdd_scenarios"]:
        # Find scenario file in RequireKit
        scenario_file = requirekit_path / "docs" / "bdd" / f"{scenario_id}.feature"

        if not scenario_file.exists():
            print(f"""
ERROR: Scenario {scenario_id} not found at {scenario_file}

  Generate scenario in RequireKit:
    cd {requirekit_path}
    /generate-bdd REQ-XXX

  Verify scenarios exist:
    ls {requirekit_path}/docs/bdd/{scenario_id}.feature
            """)
            sys.exit(1)

        # Read Gherkin content
        with open(scenario_file) as f:
            scenario_content = f.read()

        scenarios.append({
            "id": scenario_id,
            "file": str(scenario_file),
            "content": scenario_content
        })

    # Add scenarios to task context
    task_context["gherkin_scenarios"] = scenarios

    # Detect BDD framework for this project using the prose rules below
    # ("BDD FRAMEWORK DETECTION") — there is no Python helper; the Player
    # inspects the project's dependency manifest qualitatively.
    task_context["bdd_framework"] = <detected framework name, see prose below>

    # Display loaded scenarios
    print(f"\n✅ Loaded {len(scenarios)} BDD scenarios from RequireKit:")
    for s in scenarios:
        print(f"   • {s['id']}")
    print(f"   Framework: {task_context['bdd_framework']}\n")
```

**BDD FRAMEWORK DETECTION**:

Detect the BDD framework from the project's package/requirements file. This is a qualitative inspection performed by the Player LLM when the task enters BDD mode — there is no deterministic Python driver backing this step.

| Marker found | Location | Framework |
|---|---|---|
| `pytest-bdd` | `pyproject.toml` or `requirements.txt` | `pytest-bdd` |
| `SpecFlow` | any `*.csproj` | `specflow` |
| `@cucumber/cucumber` | `package.json` `devDependencies` | `cucumber-js` |
| `cucumber` gem | `Gemfile` | `cucumber` |
| (no marker) | — | `pytest-bdd` (default fallback) |

Record the detected framework on `task_context["bdd_framework"]` so later phases know which test-runner prose to use.

**VALIDATE** essential fields exist:
- `title`: Must be present
- `acceptance_criteria`: At least one criterion required
- Warn if missing: `requirements`, `bdd_scenarios` (only if require-kit installed)

**DISPLAY** loaded context summary:
```
📋 Task Context Loaded

ID: {task_id}
Title: {title}
State: {state}
Priority: {priority}

{if REQUIREMENTS_AVAILABLE:}
Requirements: {len(requirements)} linked ({', '.join(requirements[:3])}{' ...' if len > 3})
BDD Scenarios: {len(bdd_scenarios)} linked
Epic: {epic or 'None'}
Feature: {feature or 'None'}
{else:}
[Requirements features not available - install require-kit for EARS/BDD/Epic support]
{endif}

Acceptance Criteria: {len(acceptance_criteria)} items
```

**PROCEED** to Phase 1.7 (Fleet-Memory Context Loading)

#### Phase 1.7: Fleet-Memory Context Loading (Knowledge Store)

**Purpose**: Load job-specific context from the fleet-memory knowledge store to enrich implementation planning with historical patterns, similar outcomes, and domain knowledge.

**Trigger**: Always execute after Phase 1.5 (fast no-op if fleet-memory unavailable)

**Skip Conditions**:
- `--implement-only` flag is set (uses saved design)
- `--no-context` flag is set

**⚠️ IMPORTANT: Prefer the MCP tool (`mcp__fleet_memory__memory_search`)
when available in the current session.** If the MCP tool is not available, fall back to the
`guardkit memory search` CLI via bash as described below. This is READ-ONLY context loading —
task-work performs no fleet-memory writes.

**Workflow**:

**STEP 0: Check for MCP Tools (Preferred Path — Zero Overhead)**

Check whether `mcp__fleet_memory__memory_search` is available in the current session
(see `docs/internals/commands-lib/memory-preamble.md` Tier 0).

**IMPORTANT — Deferred tools**: In Claude Code sessions, MCP tools are often
listed in the system reminder as "deferred" (loadable via `ToolSearch`) rather
than appearing directly in the immediate tool list. Treat deferred tools as
**available**.

If `mcp__fleet_memory__memory_search` is **not** in the immediate tool list, scan
the session's deferred-tool list (system reminder block). If present there,
load its schema first:

```
ToolSearch(query: "select:mcp__fleet_memory__memory_search")
```

Only fall through to Tier 1 if the tool is absent from BOTH the immediate
tool list AND the deferred-tool list.

**IF** the MCP tool is available (immediately or after ToolSearch load):

SET `memory_access = "mcp"`

Run a single fleet-memory search covering decisions, architecture, and prior task outcomes.
(The old two-tool node+fact graph search collapses into one `memory_search` call — the
payload-type/domain-tag filters do the group scoping.)

```
mcp__fleet_memory__memory_search(
  project="guardkit",
  query="{task_title} {key_terms_from_description}",
  payload_types=["adr", "document", "build_outcome"],
  domain_tags=["project", "architecture", "task"],
  token_budget=2000
)
```

**Query Construction**:
- Use the task title as the primary query
- Append 2-3 key terms extracted from the task description
- Keep queries concise (under 100 characters) for best match quality
- Example: title="Implement auth middleware" → query="Implement auth middleware session JWT"

**Result Formatting**:
`memory_search` returns `{context_block, coverage_score, contributing_types, tokens_used}`.
Use the returned `context_block` directly as the Phase 2 injection context:

```python
result = memory_search(...)  # dict above
if result.get("context_block"):
    memory_context = result["context_block"]
else:
    memory_context = None
```

SET `task_context["memory_context"] = memory_context`

**DISPLAY**:
```
[Fleet-Memory] Context loaded via MCP: coverage {coverage_score}, {tokens_used}/2000 tokens
```

**IF** the MCP search call fails (error or empty `context_block`):
```
DISPLAY: "[Fleet-Memory] MCP search returned no results (continuing without)"
SET task_context["memory_context"] = None
```

**PROCEED** to Step 3 (skip Steps 1-2)

**IF** the MCP tool is NOT available:
- Fall through to Steps 1-2 (CLI fallback)

**STEP 1: Check Fleet-Memory Availability via CLI (Fallback)**

Check store reachability (see `docs/internals/commands-lib/memory-preamble.md` Tier 1):

```bash
guardkit memory status
```

**IF** the output does NOT report `Status: REACHABLE` (i.e. `UNAVAILABLE`, `DISABLED`,
`DEGRADED`, or an error):
```
DISPLAY: "[Fleet-Memory] Context: unavailable via CLI (continuing without)"
         "  Reason: {status output}"
SET task_context["memory_context"] = None
PROCEED to Step 3
```

**STEP 2: Load Context from Fleet-Memory via CLI**

**IF** the store is reachable (`Status: REACHABLE` from Step 1):

SET `memory_access = "cli"`

Run the search with task details (same query as the MCP path):

```bash
guardkit memory search "{task_title} {key_terms_from_description}" \
    --payload-types adr --payload-types document --payload-types build_outcome \
    --domain-tags project --domain-tags architecture --domain-tags task \
    --token-budget 2000
```

**IF** the command returns a non-empty context block:
```
SET task_context["memory_context"] = context_from_output
DISPLAY: "[Fleet-Memory] Context loaded via CLI ({token_budget} token budget)"
```

**IF** the output is empty (no matching knowledge):
```
DISPLAY: "[Fleet-Memory] Context: no results via CLI (continuing without)"
SET task_context["memory_context"] = None
```

**STEP 3: Store for Phase 2 Injection**

Both the MCP path (Step 0) and CLI path (Steps 1-2) produce `task_context["memory_context"]`
as a text string (or None), and `task_context["memory_access"]` as `"mcp"`, `"cli"`,
or `None`. These values are injected into the Phase 2 planning prompt. See Phase 2 for the
injection template.

Store the access method alongside the context:
```python
# Already set during Step 0 or Steps 1-2:
# task_context["memory_access"] = "mcp" | "cli" | None
# task_context["memory_context"] = context_string | None
```

**ERROR HANDLING**:

All fleet-memory operations follow the graceful degradation pattern
(see `docs/internals/commands-lib/memory-preamble.md`):

1. **Tier 0 — MCP** (preferred): Direct `memory_search` call with zero CLI overhead.
   If the MCP tool is not in the session, fall through to Tier 1.
   If the call returns an error or empty `context_block`, set context to None and continue.
2. **Tier 1 — CLI** (fallback): `guardkit memory status` gates reachability, then
   `guardkit memory search` loads context. Unreachable = unavailable.
3. If both paths fail, treat as unavailable and continue without context.

Task-work NEVER blocks or fails due to fleet-memory errors.

**Example Flows**:

MCP path (preferred — when the fleet-memory MCP tool is in session):
```
/task-work TASK-a3f8

Phase 1.5: Loading context...
Phase 1.7: Fleet-Memory Context Loading

[Fleet-Memory] Context loaded via MCP: coverage 0.82, 1450/2000 tokens

Phase 2: Planning implementation with knowledge context...
```

CLI fallback path (when the MCP tool is not available):
```
/task-work TASK-a3f8

Phase 1.5: Loading context...
Phase 1.7: Fleet-Memory Context Loading

[Fleet-Memory] Context loaded via CLI (2000 token budget)

Phase 2: Planning implementation with knowledge context...
```

When unavailable (both paths fail):
```
Phase 1.7: Fleet-Memory Context Loading

[Fleet-Memory] Context: unavailable (continuing without)
  Reason: MCP tool not in session; CLI: store not reachable

Phase 2: Planning implementation...
```

**PROCEED** to Step 2 (Detect Technology Stack)

## Step 2.5 — Full Procedure (Documentation Level)


**STEP 1: Load Configuration**

```python
# Read documentation settings from .claude/settings.json
try:
    settings = read_json(".claude/settings.json")
    doc_config = settings.get("documentation", {})
    enabled = doc_config.get("enabled", True)
    default_level = doc_config.get("default_level", "auto")
    force_triggers = doc_config.get("force_comprehensive", {}).get("triggers", {})
except FileNotFoundError:
    # No settings file - use defaults
    enabled = True
    default_level = "auto"
    force_triggers = {}
```

**STEP 2: Check Force-Comprehensive Triggers**

```python
task_text = (task_context.get("title", "") + " " + task_context.get("description", "")).lower()

# Check triggers from settings or use defaults
security_keywords = force_triggers.get("security_keywords", ["auth", "password", "encryption", "security"])
compliance_keywords = force_triggers.get("compliance_keywords", ["gdpr", "hipaa", "compliance", "audit"])
breaking_keywords = force_triggers.get("breaking_changes", ["breaking", "migration", "deprecated"])

force_comprehensive = (
    any(kw in task_text for kw in security_keywords) or
    any(kw in task_text for kw in compliance_keywords) or
    any(kw in task_text for kw in breaking_keywords)
)
```

**STEP 3: Apply Configuration Hierarchy**

```python
documentation_level = None
reason = None

# Priority 1: Command-line flag (highest)
if docs_flag:
    documentation_level = docs_flag
    reason = f"explicit flag (--docs={docs_flag})"

# Priority 2: Force-comprehensive triggers
elif force_comprehensive:
    documentation_level = "comprehensive"
    reason = "force trigger (security/compliance/breaking keywords)"

# Priority 3: Settings.json default_level
elif default_level != "auto":
    documentation_level = default_level
    reason = "settings.json default"

# Priority 4: Default to minimal (lowest)
else:
    documentation_level = "minimal"
    reason = "default (use --docs=standard to lift)"
```

**STEP 4: Store in Context & Display**

```python
# Add to task_context for agent invocations
task_context["documentation_level"] = documentation_level

**DISPLAY**:
📄 Documentation Level: {documentation_level.upper()}
   Reason: {reason}
   Files: {2 if documentation_level != 'comprehensive' else '13+'} files
   Estimated: {8-12 if documentation_level == 'minimal' else 12-18 if documentation_level == 'standard' else 36+} minutes
```

**PROCEED** to Step 3 (Select Agents)


## Step 4 Phases — Planning (Phase 1 … Phase 2.9)

#### Phase 1: Requirements Analysis *(Require-Kit Only)*

**SKIPPED IN GUARDKIT**: GuardKit uses task descriptions and acceptance criteria directly without formal requirements analysis.

**Why skipped**: GuardKit is lightweight - no EARS notation or formal BDD generation needed.

**For formal requirements**: Use [require-kit](https://github.com/requirekit/require-kit) which provides:
- EARS notation requirements analysis
- BDD/Gherkin scenario generation
- Full requirements traceability

**GuardKit workflow**: Proceed to Phase 1.6 (Clarifying Questions), then Phase 2 (Implementation Planning).

#### Phase 1.6: Clarifying Questions (Complexity-Gated)

**Purpose**: Ask targeted clarifying questions before making assumptions in implementation planning.

**Trigger**: After context loading (Phase 1.5), before implementation planning (Phase 2)

**Complexity Gating**:

| Complexity | Behavior |
|------------|----------|
| 1-2 (Trivial) | Skip - proceed directly to Phase 2 |
| 3-4 (Simple) | Quick mode - 15s timeout, then use defaults |
| 5+ (Complex) | Full mode - blocking, wait for user response |

**Workflow**:

**IF** `--no-questions` flag is set:
```
DISPLAY: "⏭️  Clarification skipped (--no-questions flag)"
Skip to Phase 2
```

**ELSE IF** `--implement-only` flag is set:
```
DISPLAY: "⏭️  Clarification skipped (using saved design)"
Skip to Phase 2
```

**ELSE**:

**INVOKE** Task tool:
```
subagent_type: "clarification-questioner"
description: "Collect implementation planning clarifications for TASK-{task_id}"
prompt: "Execute clarification for TASK-{task_id}.

CONTEXT TYPE: implementation_planning

TASK CONTEXT:
  Title: {task_context.title}
  Description: {task_context.description}
  Complexity: {task_context.complexity}/10
  Acceptance Criteria: {task_context.acceptance_criteria}
  Stack: {detected_stack}

FLAGS:
  --no-questions: {flags.no_questions}
  --with-questions: {flags.with_questions}
  --defaults: {flags.defaults}
  --answers: {flags.answers}

Execute clarification based on complexity gating:
- Complexity 1-2: Skip unless --with-questions
- Complexity 3-4: Quick mode (15s timeout)
- Complexity 5+: Full mode (blocking)

Return ClarificationContext with user decisions."
```

**WAIT** for agent completion

**STORE** `clarification_context` for Phase 2 prompt

**DISPLAY**:
```
✅ Phase 1.6: Clarification complete
  Mode: {clarification_context.mode}
  Decisions: {clarification_context.answered_count}
  Defaults used: {len(clarification_context.assumed_defaults)}
```

**Command-Line Flags**: defined once in the core `## Available Flags` table
(`task-work.md`) — the single normative site (PB-9).

**Example Flow**:

```
/task-work TASK-a3f8

Phase 1.5: Loading context...
Phase 1.6: Clarifying Questions (complexity: 5)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 CLARIFYING QUESTIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Q1. Implementation Scope
    How comprehensive should this implementation be?

    [M]inimal - Core functionality only
    [S]tandard - With error handling (DEFAULT)
    [C]omplete - Production-ready with edge cases

    Your choice [M/S/C]: S

Q2. Testing Approach
    What testing strategy?

    [U]nit tests only
    [I]ntegration tests included (DEFAULT)
    [F]ull coverage (unit + integration + e2e)

    Your choice [U/I/F]: I

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Recorded 2 decisions
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 2: Planning implementation with clarifications...
```

**Quick Mode Timeout Behavior**:

For complexity 3-4 tasks (simple):
- Display questions with 15-second countdown
- If user responds within 15s: Use their answers
- If timeout expires: Automatically use default values
- Display: "⏱️ Timeout - using defaults for remaining questions"

For complexity 5+ tasks (complex):
- No timeout - blocking wait for user response
- User must answer or cancel with Ctrl+C

**Skip Conditions**:

Phase 1.6 is skipped when:
- `--no-questions` flag is present
- Task complexity is 1-2 (trivial)
- `--design-only` flag is present (design-first workflow)
- Task is in DESIGN_APPROVED state (implement-only)

**See**: [Clarifying Questions Feature](../../tasks/backlog/clarifying-questions/) for complete implementation details.

#### Phase 1.7: Pre-Implementation Architecture Check (Complexity >= 7)

**Purpose**: Inform the user about available architecture context for high-complexity tasks before implementation begins.

**Trigger**: After clarifying questions (Phase 1.6), before library context gathering (Phase 2.1)

**Complexity Gating**:

| Complexity | Behavior |
|------------|----------|
| 1-6 | Skip - no architecture check |
| 7-10 | Display available architecture context |

**Workflow**:

**IF** task complexity < 7:
```
Skip to Phase 2.1
```

**ELSE IF** task complexity >= 7 AND fleet-memory has architecture context:

**DISPLAY** (informational only):
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 PRE-IMPLEMENTATION ARCHITECTURE CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is a high-complexity task. Architecture context available:

  docs/architecture/ - review current architecture (ADRs, bounded contexts)
  guardkit memory search "<area>" --domain-tags architecture - related decisions

Proceeding with task-work...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**ELSE** (no architecture context):
```
Skip to Phase 2.1
```

**Key Characteristics**:
- Non-blocking - does not wait for user input
- Informational only - does not require action
- Graceful degradation - skips if fleet-memory unavailable
- No timeout - immediately proceeds to next phase

**Example**:

For a complexity 8 refactoring task with architecture knowledge:
```
Phase 1.6: Clarifying Questions ✓
Phase 1.7: Pre-Implementation Architecture Check

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📐 PRE-IMPLEMENTATION ARCHITECTURE CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is a high-complexity task. Architecture context available:

  docs/architecture/ - review current architecture (ADRs, bounded contexts)
  guardkit memory search "auth" --domain-tags architecture - related decisions

Proceeding with task-work...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 2.1: Library Context Gathering
...
```

For a complexity 4 task:
```
Phase 1.6: Clarifying Questions ✓
Phase 2.1: Library Context Gathering
...
(Phase 1.7 skipped - complexity < 7)
```

**Implementation Note**: This feature integrates with the coach_context_builder module (TASK-SC-009) to provide contextual architecture awareness before complex implementations begin.

#### Phase 1.8: Feature Diagram Review Prompt

**Purpose**: Surface the parent feature's data flow diagram to help the developer understand where this task fits in the broader feature architecture.

**Trigger**: After architecture check (Phase 1.7), before library context gathering (Phase 2.1). Only when task has `parent_review` or `feature_id` in frontmatter.

**Skip Conditions**:
- Task has no `parent_review` or `feature_id` field in frontmatter
- Parent feature has no IMPLEMENTATION-GUIDE.md
- IMPLEMENTATION-GUIDE.md has no data flow diagram section

**Workflow**:

**IF** task frontmatter contains `feature_id` or `parent_review`:

**SEARCH** for IMPLEMENTATION-GUIDE.md in the feature's subfolder:
```
tasks/backlog/{feature-slug}/IMPLEMENTATION-GUIDE.md
```

**IF** IMPLEMENTATION-GUIDE.md exists AND contains a data flow diagram:

**READ** the diagram section and determine this task's role (write path, read path, or both).

**DISPLAY** (informational only):
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 FEATURE DATA FLOW CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This task implements: [write path / read path / both]
Connected to: [list upstream/downstream components from diagram]

Review the full diagram: tasks/backlog/{feature-slug}/IMPLEMENTATION-GUIDE.md#data-flow

Proceeding with task-work...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**ELSE**:
```
Skip to Phase 2.1
```

**Key Characteristics**:
- Non-blocking - does not wait for user input
- Informational only - helps developer understand task's place in feature data flow
- Graceful degradation - skips silently if no parent feature or no diagram
- No timeout - immediately proceeds to next phase

**Example**:

For a task with `feature_id: FEAT-a3f8` that implements a write path:
```
Phase 1.7: Pre-Implementation Architecture Check ✓
Phase 1.8: Feature Diagram Review

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 FEATURE DATA FLOW CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This task implements: write path (AutoBuild._capture_turn_state → turn_states)
Connected to: downstream read by load_turn_continuation_context()

Review the full diagram: tasks/backlog/dark-mode/IMPLEMENTATION-GUIDE.md#data-flow

Proceeding with task-work...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 2.1: Library Context Gathering
...
```

For a task without parent feature:
```
Phase 1.7: Pre-Implementation Architecture Check ✓
Phase 2.1: Library Context Gathering
...
(Phase 1.8 skipped - no parent feature)
```

#### Phase 2.1: Library Context (Context7 MCP)

Before invoking the planning agent, Claude consults the Context7 MCP
directly for any libraries named or strongly implied by the task
description. See the "Context7 MCP Integration" section later in this
document for the call pattern (`mcp__context7__resolve-library-id` →
`mcp__context7__get-library-docs`). When Context7 is unavailable or the
library isn't registered, proceed with training data — do not block.

#### Phase 2: Implementation Planning

**DISPLAY INVOCATION MESSAGE**:
```
═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: {selected_planning_agent_from_table}
═══════════════════════════════════════════════════════
Phase: 2 (Implementation Planning)
Model: Sonnet (Deep understanding of architecture and design patterns)
Stack: {detected_stack}
Specialization:
  - Architecture design and pattern selection
  - Technology-specific implementation strategy
  - Complexity and risk assessment

Starting agent execution...
═══════════════════════════════════════════════════════
```

**INVOKE** Task tool with documentation context, clarification decisions, AND library context:
```
subagent_type: "{selected_planning_agent_from_table}"
description: "Plan implementation for TASK-XXX"
prompt: "<AGENT_CONTEXT>
documentation_level: {documentation_level}
complexity_score: {task_context.complexity}
task_id: {task_id}
stack: {stack}
phase: 2
{if clarification_context:}
clarification_context: {clarification_context}
{endif}
{if task_context.memory_context:}
memory_context: available ({task_context.memory_access or "cli"})
{endif}
</AGENT_CONTEXT>

Design {stack} implementation approach for {task_id}.
Include architecture decisions, pattern selection, and component structure.
Consider {stack}-specific best practices and testing strategies.

{if clarification_context:}
CLARIFICATION CONTEXT (from Phase 1.6):
User provided the following clarifications:
{for decision in clarification_context.explicit_decisions:}
  - {decision.question_text}: {decision.answer_display}
{endfor}

Defaults applied (user did not override):
{for decision in clarification_context.assumed_defaults:}
  - {decision.question_text}: {decision.answer_display} (default)
{endfor}

Use these clarifications to inform your implementation plan.
{endif}

{if task_context.memory_context:}
KNOWLEDGE CONTEXT (from Phase 1.7 - Fleet-Memory, source: {task_context.memory_access}):
The following context was retrieved from the project knowledge store.
Use this to inform architectural decisions, avoid known pitfalls, and
build on successful patterns from previous tasks:

{task_context.memory_context}

IMPORTANT: In your plan output, include a "Context Used" section listing
which knowledge items above influenced your plan decisions. Example:
  ## Context Used
  - Decision "AuthMiddleware": informed session management approach
  - Outcome "JWT preferred over sessions": guided token strategy
{else:}
No fleet-memory context available — planning from task description only.
{endif}

{if mode == 'bdd':}
BDD MODE CONTEXT:
- BDD Scenarios loaded: {len(task_context.get('gherkin_scenarios', []))} scenarios
- Framework: {task_context.get('bdd_framework')}
- Scenarios:
{for scenario in task_context.get('gherkin_scenarios', []):}
  • {scenario['id']}: {scenario['content'][:200]}...
{endfor}

Implementation plan should:
1. Account for step definitions matching these scenarios
2. Structure code to facilitate BDD testing
3. Map Given/When/Then steps to implementation components
{endif}

DOCUMENTATION BEHAVIOR (documentation_level={documentation_level}):
- minimal: Return plan as structured data (file list, phases, estimates). CONSTRAINT: Generate ONLY 2 files maximum.
- standard: Return plan with brief architecture notes and key decisions. CONSTRAINT: Generate ONLY 2 files maximum.
- comprehensive: Generate detailed implementation guide with ADRs and diagrams (13+ files allowed)

Output: Implementation plan matching documentation level expectations."
```

**WAIT** for agent to complete before proceeding.

**DISPLAY COMPLETION MESSAGE**:
```
═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: {selected_planning_agent_from_table}
═══════════════════════════════════════════════════════
Duration: {phase_2_duration_seconds}s
Files to create: {planned_file_count}
Architecture patterns identified: {pattern_count}
Risk factors: {risk_level}
Knowledge context: {if task_context.memory_context:}used (source: {task_context.memory_access}){else:}none{endif}
Status: Implementation plan generated successfully

Proceeding to Phase 2.5A...
═══════════════════════════════════════════════════════
```

**Phase gate validation is deferred to Step 6.5** (post-phase
`validate_agent_invocations` check, shipped in TASK-FIX-RWOP1.3.1). No
per-phase blocking check is needed here.

#### Phase 2.5A: Pattern Suggestion (Conditional - Skip for simple tasks)

**STEP 1: Evaluate Skip Conditions**

Before invoking Design Patterns MCP, evaluate whether pattern suggestions would add value:

```python
def should_invoke_design_patterns_mcp(task_context):
    """Determine if design patterns MCP adds value for this task."""

    # Get task metadata
    complexity = task_context.get("complexity", 5)
    task_type = task_context.get("task_type", "feature")
    description = task_context.get("description", "")
    title = task_context.get("title", "")

    # Combine title and description for pattern matching
    task_text = f"{title} {description}".lower()

    # Skip Condition 1: Simple tasks (complexity ≤3)
    if complexity <= 3:
        return False, f"complexity {complexity} <= 3 (simple task)"

    # Skip Condition 2: Bug fixes
    if task_type == "bugfix":
        return False, "task_type is 'bugfix' (no new architecture needed)"

    # Skip Condition 3: Task already references a known pattern
    known_patterns = [
        "singleton", "repository", "factory", "strategy", "observer",
        "adapter", "decorator", "facade", "command", "mediator",
        "builder", "prototype", "chain of responsibility", "state",
        "template method", "visitor", "memento", "iterator"
    ]

    for pattern in known_patterns:
        if pattern in task_text:
            return False, f"task references '{pattern}' pattern"

    # All checks passed - invoke MCP
    return True, None
```

**EVALUATE** skip conditions:

```python
should_invoke, skip_reason = should_invoke_design_patterns_mcp(task_context)
```

**IF** should_invoke == False:

**DISPLAY** skip message:
```
⏭️  Skipping Pattern Suggestion (Phase 2.5A)
   Reason: {skip_reason}

   Proceeding to Phase 2.5B...
```

**PROCEED** directly to Phase 2.5B (Architectural Review)

---

**STEP 2: Invoke MCP (if not skipped)**

**IF** should_invoke == True AND Design Patterns MCP is available (check for mcp__design-patterns tools):

**QUERY** Design Patterns MCP using problem description from implementation plan:
```
Use find_patterns with REQUIRED programmingLanguage parameter:

mcp__design-patterns__find_patterns(
  query: "{problem description from task} for {stack} application",
  programmingLanguage: "{map stack to language: maui->csharp, react->typescript, python->python, typescript-api->typescript, dotnet-microservice->csharp}",
  maxResults: 3  // Limit to top 3 to reduce noise
)

Example for MAUI stack:
query: "Repository pattern with error handling using ErrorOr for database write operations in C# .NET MAUI mobile application"
programmingLanguage: "csharp"
maxResults: 3

Parse MCP response to extract:
- Recommended patterns (with confidence scores)
- Pattern categories (Resilience, Performance, etc.)
- Why each pattern is recommended
- Implementation guidance for {stack}

**FILTER RESULTS**: Skip patterns that don't match detected stack (e.g., React patterns for MAUI tasks)
```

**DISPLAY** pattern recommendations (if any found):
```
🎯 Design Pattern Recommendations

Based on task requirements and constraints:

1. **Circuit Breaker Pattern** (Confidence: 95%)
   Category: Resilience
   Why: Handles external API failures, enforces timeout constraints
   Stack guidance: {stack-specific implementation notes from MCP}

2. **Retry Pattern** (Confidence: 82%)
   Category: Resilience
   Why: Handles transient failures, works with Circuit Breaker
   Stack guidance: {stack-specific implementation notes from MCP}

[Additional patterns if relevant...]
```

**IF** no Design Patterns MCP available:

**DISPLAY**:
```
⏭️  Skipping Pattern Suggestion (Phase 2.5A)
   Reason: Design Patterns MCP not available

   Proceeding to Phase 2.5B...
```

**PROCEED** to Phase 2.5B.

#### Phase 2.5B: Architectural Review (Catch design issues early)

**DISPLAY INVOCATION MESSAGE**:
```
═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: architectural-reviewer
═══════════════════════════════════════════════════════
Phase: 2.5B (Architectural Review)
Model: Sonnet (Expert-level architecture analysis)
Stack: {detected_stack}
Specialization:
  - SOLID principles verification
  - Design pattern validation
  - Risk and complexity assessment

Starting agent execution...
═══════════════════════════════════════════════════════
```

**INVOKE** Task tool with documentation context:
```
subagent_type: "architectural-reviewer"
description: "Review architecture for TASK-XXX"
prompt: "<AGENT_CONTEXT>
documentation_level: {documentation_level}
complexity_score: {task_context.complexity}
task_id: {task_id}
stack: {stack}
phase: 2.5
</AGENT_CONTEXT>

Review the implementation plan from Phase 2 for {task_id}.
Evaluate against SOLID principles, DRY principle, and YAGNI principle.
Check for: single responsibility, proper abstraction, unnecessary complexity.
Score each principle (0-100) and provide specific recommendations.

PATTERN CONTEXT (if Design Patterns MCP was queried):
{Include pattern recommendations from Phase 2.5A}
- Validate if suggested patterns are appropriate
- Check if implementation plan aligns with pattern best practices
- Identify if patterns are over-engineered for the requirements

DOCUMENTATION BEHAVIOR (documentation_level={documentation_level}):
- minimal: Return scores and critical issues only (structured data). CONSTRAINT: Generate ONLY 2 files maximum.
- standard: Return scores with brief explanations and recommendations. CONSTRAINT: Generate ONLY 2 files maximum.
- comprehensive: Generate detailed architecture review report with rationale (13+ files allowed)

Approval thresholds:
- ≥80/100: Auto-approve (proceed to Phase 3)
- 60-79/100: Approve with recommendations
- <60/100: Reject (revise design)

See installer/core/agents/architectural-reviewer.md for documentation level specifications."
```

**WAIT** for agent to complete before proceeding.

**DISPLAY COMPLETION MESSAGE**:
```
═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: architectural-reviewer
═══════════════════════════════════════════════════════
Duration: {phase_25b_duration_seconds}s
SOLID Score: {solid_score}/100
DRY Score: {dry_score}/100
YAGNI Score: {yagni_score}/100
Overall Recommendation: {recommendation}
Status: Architectural review complete

Proceeding to Phase 2.7...
═══════════════════════════════════════════════════════
```

Phase gate validation is deferred to Step 6.5 (see Phase 2 note).

#### Phase 2.7: Complexity Evaluation (NEW - Auto-proceed mode routing)

**INVOKE** Task tool:
```
subagent_type: "complexity-evaluator"
description: "Evaluate implementation complexity for TASK-XXX"
prompt: "Evaluate implementation complexity for TASK-XXX using the implementation plan from Phase 2.

         Extract and analyze:
         - File count (files to create/modify)
         - Design patterns mentioned
         - External dependencies (APIs, databases, services)
         - Risk indicators (security, schema changes, performance)

         Calculate complexity score (1-10 scale) based on:
         - File complexity factor (0-3 points)
         - Pattern familiarity factor (0-2 points)
         - Risk level factor (0-3 points)

         Detect force-review triggers:
         - User flag (--review)
         - Security keywords
         - Breaking changes
         - Schema changes
         - Hotfix

         Route to review mode:
         - Score 1-3: AUTO_PROCEED (display summary, proceed to Phase 3)
         - Score 4-6: QUICK_OPTIONAL (offer optional checkpoint)
         - Score 7-10 or triggers: FULL_REQUIRED (mandatory Phase 2.6)

         Output: ComplexityScore with routing decision and human-readable summary."
```

**WAIT** for agent to complete before proceeding.

**EVALUATE** complexity evaluation result:

```python
complexity_result = extract_complexity_result(phase_27_output)
review_mode = complexity_result.review_mode  # AUTO_PROCEED, QUICK_OPTIONAL, or FULL_REQUIRED
```

**IF** review_mode == AUTO_PROCEED:
- Display complexity summary
- Automatically proceed to Phase 3 (no human intervention)

**ELSE IF** review_mode == QUICK_OPTIONAL:
- Display complexity summary with optional checkpoint prompt
- Offer user choice: [A]pprove, [R]eview, [Enter] to auto-approve
- Default to proceed after 10 seconds timeout
- If user chooses [R]eview, proceed to Phase 2.6

**ELSE IF** review_mode == FULL_REQUIRED:
- Display detailed complexity summary
- Mandatory Phase 2.6 human checkpoint (see below)

#### Phase 2.6: Human Checkpoint (Optional - Triggered by complexity evaluation or critical tasks)

**NOTE**: This phase is now triggered by Phase 2.7 complexity evaluation:
- **Mandatory**: If complexity score 7-10 OR force-review triggers detected
- **Optional**: If complexity score 4-6 AND user chooses to review
- **Skipped**: If complexity score 1-3 (auto-proceed)

**Human checkpoint is triggered by Phase 2.7 complexity evaluation**:

```python
# Automatic triggers from Phase 2.7
if complexity_result.review_mode == FULL_REQUIRED:
    trigger_checkpoint = True
    checkpoint_reason = "Complexity score 7-10 or force-review triggers"
elif complexity_result.review_mode == QUICK_OPTIONAL and user_chose_review:
    trigger_checkpoint = True
    checkpoint_reason = "User requested review (optional)"
else:
    trigger_checkpoint = False  # AUTO_PROCEED - skip to Phase 3
```

**IF TRIGGERED**, display interactive checkpoint:

```
═══════════════════════════════════════════════════════
🔍 PHASE 2.6 - HUMAN CHECKPOINT REQUIRED
═══════════════════════════════════════════════════════

TASK: {TASK-ID} - {Title}

COMPLEXITY EVALUATION (Phase 2.7):
  Score: {complexity_score}/10 ({review_mode})
  Triggers: {List of force-review triggers}
  Reason: {checkpoint_reason}

ARCHITECTURAL REVIEW (Phase 2.5B):
  Score: {arch_score}/100 ({arch_status})
  Issues: {issue_count}
  {List of critical issues and recommendations}

ESTIMATED FIX TIME: {minutes} minutes (design adjustment)

OPTIONS:
1. [A]pprove - Proceed with current design
2. [R]evise - Apply recommendations and re-review
3. [V]iew - Show full architectural review report
4. [C]omplexity - Show detailed complexity breakdown
5. [D]iscuss - Escalate to software-architect

Your choice (A/R/V/C/D):
═══════════════════════════════════════════════════════
```

**WAIT** for human decision:
- **Approve**: Continue to Phase 3 (implementation)
- **Revise**: Loop back to Phase 2 (planning) with feedback
- **View**: Display full architectural review report, then prompt again
- **Complexity**: Display detailed complexity breakdown, then prompt again
- **Discuss**: Invoke software-architect agent for consultation

**IF NOT TRIGGERED** (auto-proceed from Phase 2.7):
- Display complexity summary (score 1-3)
- Automatically proceed to Phase 3 with no human intervention

#### Phase 2.7: Implementation Plan Generation & Complexity Evaluation (ENHANCED)

**PURPOSE**: Generate structured implementation plan and evaluate complexity to route to appropriate review mode

**ENHANCEMENTS (TASK-027 - Markdown Plans)**:
- **Dual Format Support**: Generates both Markdown (`implementation_plan.md`) and JSON (`implementation_plan.json`) formats
- **Human-Readable Plans**: Markdown format improves readability for Phase 2.8 checkpoint display
- **Backward Compatibility**: JSON format preserved for automated processing
- **Git-Friendly**: Markdown plans are easier to review in version control diffs
- **Plan Location**: Both files saved to `docs/state/{task_id}/`

**INVOKE** Task tool:
```
subagent_type: "task-manager"
description: "Generate implementation plan and evaluate complexity for TASK-XXX"
prompt: "Execute Phase 2.7 for TASK-XXX:

         STEP 1: PARSE IMPLEMENTATION PLAN
         - Parse Phase 2 planning output into structured ImplementationPlan
         - Extract: files to create/modify, patterns, dependencies, risks, phases
         - Use stack-specific parser if available, fallback to generic
         - Save to: docs/state/{task_id}/implementation_plan.json

         STEP 2: CALCULATE COMPLEXITY SCORE
         - Assign a 1-10 complexity score based on file count, pattern
           familiarity, risk level, and dependencies (reason qualitatively;
           there is no dedicated calculator module).
         - Save to: docs/state/{task_id}/complexity_score.json

         STEP 3: DETECT FORCE-REVIEW TRIGGERS
         - Security keywords (auth, password, encryption, etc.)
         - Schema changes (database migrations)
         - Breaking changes (public API modifications)
         - User flag (--review command-line option)
         - Hotfix or production tags

         STEP 4: DETERMINE REVIEW MODE
         - Score 1-3 + no triggers → AUTO_PROCEED
         - Score 4-6 + no triggers → QUICK_OPTIONAL
         - Score 7-10 OR any trigger → FULL_REQUIRED

         STEP 5: RETURN RESULTS
         - ComplexityScore with review_mode
         - ImplementationPlan path
         - Force triggers list (if any)

         Stack: {detected_stack}
         Phase 2 Output: {phase_2_planning_output}
         Task Metadata: {task_frontmatter}"
```

**WAIT** for agent to complete before proceeding.

**EXTRACT** Phase 2.7 results:
```python
complexity_score = extract_complexity_score(phase_27_output)
review_mode = complexity_score.review_mode  # AUTO_PROCEED | QUICK_OPTIONAL | FULL_REQUIRED
plan_path = f"docs/state/{task_id}/implementation_plan.json"
triggers = complexity_score.forced_review_triggers
```

**DISPLAY** Phase 2.7 summary:
```
Phase 2.7 Complete: Plan Generated & Complexity Evaluated

Plan saved: {plan_path}
Complexity Score: {complexity_score.total_score}/10 ({complexity_score.level})
Review Mode: {review_mode}
{If triggers: "Force Triggers: " + ", ".join(triggers)}
```

#### Phase 2.8: Human Plan Checkpoint (ENHANCED - Rich Display & Interactive Modification)

**PURPOSE**: Route to appropriate review based on complexity score from Phase 2.7, with rich visual display and interactive plan modification capabilities.

**ENHANCEMENTS (TASK-028, TASK-029)**:
- **Rich Visual Display**: Human-readable plan summary with file changes, dependencies, risks, effort
- **Markdown & JSON Support**: Loads plans from both `implementation_plan.md` and `implementation_plan.json`
- **Interactive Modification**: [M]odify option for adjusting plan before implementation
- **Version Management**: Automatic plan versioning with timestamped backups
- **Undo Support**: Revert to previous plan versions during modification

**ROUTE** based on review_mode from Phase 2.7:

**IF** review_mode == AUTO_PROCEED:
```
Display auto-proceed summary:

  Auto-Proceed Mode (Low Complexity)

  Complexity: {score}/10 (Simple task)
  Files: {file_count} file(s)
  Tests: {test_count} tests planned
  Estimated: ~{duration} minutes

  Automatically proceeding to implementation (no review needed)...

Update task metadata:
  auto_approved: true
  approved_by: "system"
  approved_at: {current_timestamp}
  review_mode: "auto_proceed"

Proceed immediately to Phase 3 (Implementation)
```

**ELSE IF** review_mode == QUICK_OPTIONAL:

**INVOKE** Task tool:
```
subagent_type: "task-manager"
description: "Execute quick review checkpoint for TASK-XXX"
prompt: "Execute Phase 2.8 Quick Review for TASK-XXX:

         STEP 1: LOAD CONTEXT
         - Load ImplementationPlan from {plan_path}
         - Load ComplexityScore from complexity_score.json
         - Extract summary information

         STEP 2: DISPLAY QUICK REVIEW CARD
         - Complexity score and level
         - File count summary
         - Pattern summary
         - Estimated duration
         - Brief risk summary (if any)

         STEP 3: START 10-SECOND COUNTDOWN
         - Display countdown timer (10...9...8...)
         - Listen for user input:
           * ENTER pressed → Return 'escalate' (escalate to full review)
           * 'c' pressed → Return 'cancel' (cancel task, move to backlog)
           * Timeout (no input) → Return 'timeout' (auto-approve, proceed to Phase 3)

         STEP 4: UPDATE TASK METADATA
         - Record review decision
         - Update timestamps
         - Set proceed_to_phase_3 flag accordingly

         Return result: {'action': 'timeout'|'escalate'|'cancel', 'duration': seconds}"
```

**WAIT** for result

**IF** result.action == 'timeout':
  - **DISPLAY**: "Quick review timed out. Auto-approving task..."
  - **UPDATE** task metadata: `auto_approved: true, approved_by: "timeout", review_mode: "quick_optional"`
  - **PROCEED** to Phase 3 (Implementation)

**ELSE IF** result.action == 'escalate':
  - **DISPLAY**: "Escalating to full review mode..."
  - **UPDATE** review_mode to FULL_REQUIRED
  - **SET** escalated flag: true
  - **FALL THROUGH** to FULL_REQUIRED handling below

**ELSE IF** result.action == 'cancel':
  - **DISPLAY**: "Task cancelled by user"
  - **UPDATE** task metadata: `cancelled: true, cancelled_at: {timestamp}, cancelled_reason: "User cancelled during quick review"`
  - **MOVE** task file from in_progress/ to backlog/
  - **EXIT** task-work command

**ELSE IF** review_mode == FULL_REQUIRED (OR escalated from QUICK_OPTIONAL):

**STEP 1: LOAD PLAN AND DISPLAY ENHANCED CHECKPOINT (TASK-028)**

Load implementation plan from either:
- `docs/state/{task_id}/implementation_plan.md` (Markdown format - TASK-027)
- `docs/state/{task_id}/implementation_plan.json` (JSON format - legacy)

**Display rich visual checkpoint**:

```
═══════════════════════════════════════════════════════════════
🎯 PHASE 2.8 - IMPLEMENTATION PLAN CHECKPOINT
═══════════════════════════════════════════════════════════════

TASK: TASK-042 - Implement user authentication API

COMPLEXITY: 7/10 (High - Full review required)

📁 FILES TO CREATE (5 files):
   1. src/auth/login.py           - Login endpoint handler
   2. src/auth/session.py         - Session management
   3. src/auth/validator.py       - Input validation
   4. tests/test_login.py         - Login endpoint tests
   5. tests/test_session.py       - Session management tests

📦 EXTERNAL DEPENDENCIES (3 new packages):
   • bcrypt - Password hashing
   • PyJWT - JWT token generation
   • redis - Session storage

⚠️  RISKS IDENTIFIED (2 risks):
   🟡 MEDIUM - External dependency on Redis server
   🔴 HIGH - Security: Password storage and session tokens

⏱️  ESTIMATED EFFORT:
   • Duration: 8 hours
   • Lines of Code: ~450 lines
   • Complexity: High (7/10)

🏗️  IMPLEMENTATION PHASES:
   Phase 1: Models and validation (2h)
   Phase 2: Authentication logic (3h)
   Phase 3: Session management (2h)
   Phase 4: Testing (1h)

📊 ARCHITECTURAL REVIEW:
   Overall Score: 85/100 (Approved with recommendations)
   SOLID: 88/100
   DRY: 82/100
   YAGNI: 85/100

OPTIONS:
  [A]pprove  - Proceed with current plan
  [M]odify   - Edit plan before implementation (TASK-029)
  [V]iew     - Show complete plan in pager
  [C]ancel   - Cancel task, return to backlog

Your choice [A/M/V/C]:
═══════════════════════════════════════════════════════════════
```

**STEP 2: HANDLE USER DECISION**

**IF** user selects [A]pprove:
  - **DISPLAY**: "Plan approved. Proceeding to implementation..."
  - **UPDATE** task metadata: `approved: true, approved_by: "user", approved_at: {timestamp}, review_mode: "full_required"`
  - **IF** escalated: Also update `escalated: true`
  - **PROCEED** to Phase 3 (Implementation)

**ELSE IF** user selects [M]odify (TASK-029 - Interactive Plan Modification):

  **ENTER MODIFICATION LOOP**:

  ```
  ═══════════════════════════════════════════════════════════════
  📝 PLAN MODIFICATION MODE
  ═══════════════════════════════════════════════════════════════

  Select what to modify:
    1. Files - Add/remove files to create or modify
    2. Dependencies - Add/remove/update external dependencies
    3. Risks - Add/remove/modify risks and mitigations
    4. Effort - Adjust duration or complexity estimates
    5. [U]ndo - Revert to previous version
    6. [D]one - Save changes and return to checkpoint
    7. [C]ancel - Discard changes

  Choice [1-4/U/D/C]:
  ```

  **Modification Options**:

  **1. Modify Files**:
  ```
  Current files to create (5):
    1. src/auth/login.py
    2. src/auth/session.py
    3. src/auth/validator.py
    4. tests/test_login.py
    5. tests/test_session.py

  Actions:
    [A]dd file - Add new file to plan
    [R]emove file - Remove file from plan
    [B]ack - Return to modification menu

  Choice [A/R/B]:
  ```

  **2. Modify Dependencies**:
  ```
  Current dependencies (3):
    1. bcrypt - Password hashing
    2. PyJWT - JWT token generation
    3. redis - Session storage

  Actions:
    [A]dd dependency - Add new package
    [R]emove dependency - Remove package
    [M]odify dependency - Change version or justification
    [B]ack - Return to modification menu

  Choice [A/R/M/B]:
  ```

  **3. Modify Risks**:
  ```
  Current risks (2):
    1. 🟡 MEDIUM - External dependency on Redis server
    2. 🔴 HIGH - Security: Password storage and session tokens

  Actions:
    [A]dd risk - Add new risk
    [R]emove risk - Remove risk
    [M]odify risk - Change severity or mitigation
    [B]ack - Return to modification menu

  Choice [A/R/M/B]:
  ```

  **4. Modify Effort**:
  ```
  Current estimates:
    Duration: 8 hours
    Lines of Code: ~450 lines
    Complexity: 7/10 (High)

  Enter new values (or press Enter to keep):
    Duration [8h]: 10h
    LOC [~450]: ~500
    Complexity [7]: 8

  Updated estimates:
    Duration: 10 hours (+25%)
    Lines of Code: ~500 lines (+11%)
    Complexity: 8/10 (High)

  Confirm changes? [y/n]:
  ```

  **Version Management**:
  - Automatically saves plan versions: `implementation_plan_v1.json`, `implementation_plan_v2.json`, etc.
  - Each modification creates timestamped backup
  - [U]ndo option reverts to previous version
  - Plan history tracked in task metadata

  **After Modifications Complete**:
  - Save updated plan to `implementation_plan.md` and `implementation_plan.json`
  - Recalculate complexity score based on new plan
  - Update architectural review if significant changes
  - Return to Phase 2.8 checkpoint display with updated plan
  - Prompt user again: [A]pprove / [M]odify / [V]iew / [C]ancel

  **Modification Metadata** (saved to task frontmatter):
  ```yaml
  plan_modifications:
    - version: 1
      timestamp: "2025-10-19T14:30:00Z"
      changes:
        - category: "dependencies"
          action: "added"
          detail: "Added redis-py package"
        - category: "effort"
          action: "modified"
          detail: "Increased duration from 8h to 10h"
      complexity_before: 7
      complexity_after: 8
    current_version: 1
  ```

**ELSE IF** user selects [V]iew:
  - Display complete plan in pager (less/more command)
  - Return to checkpoint prompt after viewing

**ELSE IF** user selects [C]ancel:
  - **CONFIRM**: "Are you sure you want to cancel? [y/n]:"
  - **IF** confirmed:
    - **DISPLAY**: "Task cancelled by user"
    - **UPDATE** task metadata: `cancelled: true, cancelled_at: {timestamp}, cancelled_reason: "User cancelled during full review"`
    - **MOVE** task file from in_progress/ to backlog/
    - **EXIT** task-work command

#### Phase 2.9: Workflow Routing

GuardKit supports two workflows: the standard end-to-end run (continue from
Phase 2.8 straight into Phase 3) and the **design-first split** — `--design-only`
stops at the Phase 2.8 checkpoint and saves the approved plan to
`docs/state/{task_id}/implementation_plan.md` with the task in DESIGN_APPROVED;
`--implement-only` resumes from that saved plan at Phase 3. Both flags are
normative in the core `## Available Flags` table and are exercised live above
(the `--implement-only` clarification-skip branch) and by
`feature-build.md`'s `implementation_mode: task-work` path.

> **Reconciliation (task-complete demotion scope §4, Phase 0, 2026-07-10):** an
> earlier draft here claimed these flags "were removed … only the standard
> workflow is supported." That over-claimed: TASK-FIX-RWOP1.3.3 removed the old
> *per-flag save/load modules* (`plan_persistence.save_plan` / `load_plan`,
> `execute_implementation_phases`, `StateValidationError`), but the
> `--design-only` / `--implement-only` flags themselves survive via the
> DESIGN_APPROVED state + the committed plan file below — not those deleted
> modules. The stale sentence contradicted this file's own `--implement-only`
> handling, the core flag table (SSOT), CLAUDE.md's Design-First Workflow, and
> feature-build.md:377; it is corrected here.

To run design and implementation on different days, use `--design-only` then
`--implement-only`, or commit the plan file
(`docs/state/{task_id}/implementation_plan.md`) and resume from a fresh
`/task-work` invocation — Phase 2 re-loads the plan if it's present.

