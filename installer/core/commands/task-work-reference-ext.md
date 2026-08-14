---
format_version: 1
description: Reference slices for /task-work — extended documentation, not a command. Run /task-work.
---

# Task Work — Additional Context (Reference)

> **Reference file — not a command.** On-demand extension of `task-work.md`
> (K13 core/`-ext` shape, PB-13 wave 1). The core file's flag table, phase
> sequence, and state-transition rules are normative; nothing here overrides
> them. Flag semantics are defined ONCE in `task-work.md` § Available Flags (PB-9).

## Feature Detection

This command supports **graceful degradation** based on installed packages:

### GuardKit Only (Core Workflow)
- Loads task description, acceptance criteria, implementation notes
- Executes full workflow with architectural review and quality gates
- No requirements/epic loading (require-kit features)

### GuardKit + Fleet-Memory (Knowledge-Enhanced Workflow)
- All core features PLUS:
- Loads job-specific context from the fleet-memory knowledge store during Phase 1.7
- **MCP-first**: Uses `mcp__fleet_memory__memory_search` when available (zero CLI overhead)
- **CLI fallback**: Falls back to `guardkit memory search` when MCP tools not in session
- Injects feature context, similar outcomes, relevant patterns, warnings into planning prompt
- Graceful degradation: works identically when fleet-memory is unavailable

### GuardKit + Require-Kit (Enhanced Workflow)
- All core features PLUS:
- Loads EARS requirements if linked in task frontmatter
- Loads Gherkin scenarios if linked (for BDD workflow)
- Includes epic/feature context for hierarchy
- Enables requirements-based acceptance criteria enrichment

**Note**: The workflow automatically detects require-kit availability and adjusts Phase 1 loading accordingly. No manual configuration required.

---

## ⚠️ Working Directory Requirement

**CRITICAL**: `/task-work` must be run from your **project root directory** (where code files should be created).

The command uses the current working directory to:
- Detect project technology stack (e.g., `.csproj` for .NET, `package.json` for Node.js)
- Create source files in the correct locations
- Run tests and build commands
- Generate implementation files

### Verify Your Location

Before running `/task-work`, confirm you're in the correct directory:

```bash
# ✅ Correct - Run from project root
cd ~/Projects/weather_demo
pwd  # Should show: /Users/you/Projects/weather_demo
ls   # Should show: weather_demo.csproj, Program.cs, Controllers/, tasks/, etc.
/task-work TASK-001

# ❌ Wrong - Running from RequireKit/GuardKit directory
cd ~/Projects/require-kit  # Wrong location!
/task-work TASK-001        # Will create files in wrong place, wrong stack detection
```

### What Happens If You're in the Wrong Directory?

If you run `/task-work` from the wrong directory:
- ❌ Files created in wrong location (e.g., in `require-kit/` instead of `weather_demo/`)
- ❌ Technology stack misdetected (sees RequireKit's Python files instead of your .NET project)
- ❌ Wrong test commands executed (runs `pytest` instead of `dotnet test`)
- ❌ Quality gates fail or execute against wrong codebase

### Directory Structure Example

```
~/Projects/
├── require-kit/           # RequireKit installation (don't run task-work here!)
│   ├── requirements.txt
│   └── ...
├── guardkit/            # GuardKit repo (don't run task-work here!)
│   └── ...
└── weather_demo/          # Your project (run task-work HERE ✅)
    ├── weather_demo.csproj
    ├── Program.cs
    ├── Controllers/
    └── tasks/
        └── backlog/TASK-001-*.md
```

### Integration with RequireKit

When using RequireKit for requirements management:
1. Create requirements in RequireKit directory: `/req-create`
2. **Navigate to project directory**: `cd ~/Projects/weather_demo`
3. Create task linked to requirements: `/task-create "Title" requirements:[REQ-001]`
4. Work on task **from project directory**: `/task-work TASK-001`

### Quick Directory Validation

Run this before `/task-work` to verify you're in the right place:

```bash
# Verify you're in project root (should see project files)
ls *.csproj 2>/dev/null || ls package.json 2>/dev/null || ls requirements.txt 2>/dev/null || ls *.sln 2>/dev/null

# If you see your project files, you're good to go!
```

---


## 📚 ADDITIONAL CONTEXT (Reference Only - Execute Above First)

### Development Modes

> Flag semantics (`--mode` values, defaults, conflicts) are defined ONCE in
> `task-work.md` § Available Flags (PB-9). This section is workflow narrative.

The command supports multiple development modes via `--mode` flag:

#### Standard Mode (Default)
```bash
/task-work TASK-XXX
```
- Implementation and tests together
- Fastest approach for straightforward features
- All 5 phases execute in sequence

#### TDD Mode
```bash
/task-work TASK-XXX --mode=tdd
```
- RED: Testing agent generates failing tests first
- GREEN: Implementation agent writes minimal code to pass
- REFACTOR: Implementation agent improves code quality
- Best for complex business logic

#### BDD Mode — RETIRED (R1 de-instruct, 2026-08-14)

> **`--mode=bdd` is retired per Rich's 2026-08-14 ruling**
> (`ai-transition/docs/bdd-replacement-options-card-2026-08-09.md`, Q10).
> Do not select it; use `--mode=tdd` or standard. Gherkin scenarios remain
> the KEPT specification and load into planning context as before — but no
> step definitions are generated and no BDD tests are executed. Scenario
> verification moves to frozen executable twins under the routing law
> (`verifier:` stamp). The historical workflow below is preserved for the
> R1/R2 de-wire lanes' reference only.

**Workflow (HISTORICAL — do not execute)**:
1. **Phase 1**: Validates RequireKit installation via marker file
2. **Phase 1**: Loads Gherkin scenarios from task frontmatter
3. **Phase 2**: Includes scenarios in planning context
4. **Phase 3**: Routes to RequireKit's bdd-generator agent
5. **Phase 3**: Generates step definitions for detected framework
6. **Phase 3**: Implements code to pass scenarios
7. **Phase 4**: Runs BDD tests (pytest-bdd, SpecFlow, Cucumber.js, etc.)
8. **Phase 4.5**: Fix loop for failing BDD tests (max 3 attempts)
9. **Phase 5**: Standard code review

**Error Handling**:

If RequireKit not installed:
```bash
/task-work TASK-042 --mode=bdd

ERROR: BDD mode requires RequireKit installation

  RequireKit provides EARS → Gherkin → Implementation workflow for
  formal behavior specifications.

  Repository:
    https://github.com/requirekit/require-kit

  Installation:
    cd ~/Projects/require-kit
    ./installer/scripts/install.sh

  Verification:
    ls ~/.agentecflow/require-kit.marker.json  # Should exist (or require-kit.marker for legacy)

  Alternative modes:
    /task-work TASK-042 --mode=tdd      # Test-first development
    /task-work TASK-042 --mode=standard # Default workflow

  BDD mode is designed for agentic systems, not general features.
  See: docs/guides/bdd-workflow-for-agentic-systems.md
```

If bdd_scenarios not linked:
```bash
/task-work TASK-042 --mode=bdd

ERROR: BDD mode requires linked Gherkin scenarios

  Task frontmatter must include bdd_scenarios field:

    ---
    id: TASK-042
    title: Implement complexity routing
    bdd_scenarios: [BDD-ORCH-001, BDD-ORCH-002]  ← Add this
    ---

  Generate scenarios in RequireKit:
    cd ~/Projects/require-kit
    /formalize-ears REQ-XXX
    /generate-bdd REQ-XXX

  Or use alternative modes:
    /task-work TASK-042 --mode=tdd
    /task-work TASK-042 --mode=standard
```

**BDD Framework Detection**:
- Python project → pytest-bdd
- .NET project → SpecFlow
- TypeScript/JavaScript → Cucumber.js
- Ruby → Cucumber

**See**: [BDD Workflow Guide](../../docs/guides/bdd-workflow-for-agentic-systems.md)

### Agent Discovery System

**Dynamic Metadata-Based Matching**

Agents are selected dynamically based on metadata matching, NOT from static tables. The system:

1. Analyzes task context (stack, phase, keywords from description)
2. Scans all agent sources for metadata matches
3. Returns best match based on:
   - Stack compatibility (python, react, dotnet, etc.)
   - Phase alignment (implementation, review, testing, orchestration, debugging)
   - Keyword relevance (capabilities match task requirements)

**No Hardcoded Mappings**: Agent selection is intelligent and extensible - adding new agents automatically makes them discoverable.

#### Discovery Sources and Precedence

Agents are discovered from 4 sources in priority order:

1. **Local** (`.claude/agents/`) - Highest priority
   - Template agents copied during initialization
   - Project-specific customizations
   - **Always takes precedence** over global agents with same name

2. **User** (`~/.agentecflow/agents/`)
   - Personal agent customizations
   - Available across all projects
   - Overrides global agents with same name

3. **Global** (`installer/core/agents/`)
   - Built-in GuardKit agents
   - Shared across all users
   - Overridden by local/user agents

4. **Template** (`installer/core/templates/*/agents/`) - Lowest priority
   - Template-provided agents (before initialization)
   - Only used if agent not found in higher-priority sources
   - Replaced by local agents after `guardkit init`

**Precedence Rule**: Local > User > Global > Template

#### Template Override Behavior

When you run `guardkit init <template>`:
- Template agents copied to `.claude/agents/` (local)
- Local agents now **override** global agents with same name
- Enables template customization without modifying global agents

**Example**:
```bash
# Before initialization
/task-work TASK-001  # Uses global python-api-specialist

# After initialization
guardkit init fastapi-python
# Template's python-api-specialist copied to .claude/agents/

/task-work TASK-002  # Now uses LOCAL python-api-specialist 📁 (not global 🌐)
```

#### Metadata Requirements for Discovery

For an agent to be discoverable, it must have:

| Field | Type | Required | Purpose |
|-------|------|----------|---------|
| `stack` | array | ✅ Yes | Technology stack(s) the agent supports |
| `phase` | string | ✅ Yes | Workflow phase (implementation, review, testing, etc.) |
| `capabilities` | array | ✅ Yes | Specific skills and domains |
| `keywords` | array | ✅ Yes | Searchable terms for matching |

**Agents without metadata**: Skipped during discovery (graceful degradation).

#### Fallback Behavior

If no specialist agent is found:
- System falls back to `task-manager` (cross-stack orchestrator)
- Task-manager handles the task generically
- User notified about fallback in invocation log

#### Agent Source Indicators

During task execution, the invocation log shows which agent was selected and its source:

```
═══════════════════════════════════════════════════════
AGENT INVOCATIONS LOG
═══════════════════════════════════════════════════════
✅ Phase 2 (Planning): python-api-specialist 📁 (source: local, completed in 45s)
✅ Phase 2.5B (Arch Review): architectural-reviewer 🌐 (source: global, completed in 30s)
✅ Phase 3 (Implementation): python-api-specialist 📁 (source: local, completed in 120s)
✅ Phase 4 (Testing): task-manager 🌐 (source: global, completed in 60s)
✅ Phase 5 (Review): code-reviewer 🌐 (source: global, completed in 25s)
═══════════════════════════════════════════════════════
```

**Source Icons**:
- 📁 **Local** - Agent from `.claude/agents/` (template or custom)
- 👤 **User** - Agent from `~/.agentecflow/agents/` (personal)
- 🌐 **Global** - Agent from `installer/core/agents/` (built-in)
- 📦 **Template** - Agent from `installer/core/templates/*/agents/` (before init)

**Why Source Matters**:
- **Local agents override global** - Verify template customizations working
- **Precedence debugging** - Understand which agent was selected when duplicates exist
- **Troubleshooting** - If wrong agent selected, check source and metadata

#### Agent Discovery Examples

##### Example 1: Python API Implementation

**Task Context**:
- Stack: Python
- Files: `*.py`
- Keywords: "FastAPI endpoint", "async", "Pydantic schema"

**Discovery Process**:
1. Detect stack: `python` (from file extensions)
2. Detect phase: `implementation` (Phase 3)
3. Extract keywords: `api`, `async`, `pydantic`
4. Scan agents:
   - Local `.claude/agents/python-api-specialist.md` ✅ Match
   - Metadata: `stack: [python, fastapi]`, `phase: implementation`, `keywords: [api, async, pydantic]`
5. **Selected**: `python-api-specialist 📁 (source: local)`

##### Example 2: React State Management

**Task Context**:
- Stack: React
- Files: `*.tsx`
- Keywords: "hooks", "state", "TanStack Query"

**Discovery Process**:
1. Detect stack: `react` (from file extensions)
2. Detect phase: `implementation` (Phase 3)
3. Extract keywords: `hooks`, `state`, `query`
4. Scan agents:
   - Local `.claude/agents/react-state-specialist.md` ✅ Match
   - Metadata: `stack: [react, typescript]`, `phase: implementation`, `keywords: [hooks, state, query]`
5. **Selected**: `react-state-specialist 📁 (source: local)`

##### Example 3: Architectural Review (Cross-Stack)

**Task Context**:
- Stack: Any
- Phase: Architectural Review (Phase 2.5B)

**Discovery Process**:
1. Phase: `review` (architectural)
2. Scan agents:
   - Global `installer/core/agents/architectural-reviewer.md` ✅ Match
   - Metadata: `stack: [cross-stack]`, `phase: review`, `keywords: [solid, dry, yagni, architecture]`
3. **Selected**: `architectural-reviewer 🌐 (source: global)`

##### Example 4: Fallback to Task-Manager

**Task Context**:
- Stack: Go
- Files: `*.go`
- Keywords: "service", "handler"

**Discovery Process**:
1. Detect stack: `go` (from file extensions)
2. Detect phase: `implementation` (Phase 3)
3. Scan agents:
   - No agents with `stack: [go]` found
4. **Fallback**: `task-manager 🌐 (source: global)`
5. **Note**: User notified that task-manager used (no Go specialist available)

**Fix**: Create go-specialist agent with appropriate metadata, or use cross-stack task-manager.

#### Troubleshooting Agent Discovery

**Issue**: "Expected agent not selected"

**Debug Steps**:
1. Check agent has required metadata (stack, phase, capabilities, keywords)
2. Verify stack matches task technology (check file extensions)
3. Check agent source in invocation log (📁 local, 👤 user, 🌐 global, 📦 template)
4. Verify precedence isn't causing unexpected override

**Issue**: "Task-manager used instead of specialist"

**Causes**:
- No specialist agent exists for the stack
- Agent metadata doesn't match task context
- Agent missing required metadata fields

**Fix**: Run `/agent-enhance` to add/validate discovery metadata.

### Stack-Specific Agent Details (Examples Only)

**Note**: The agents listed below are examples from global/template sources. Actual agent selection is **dynamic** based on metadata matching (see [Agent Discovery System](#agent-discovery-system)). Local agents override these examples after template initialization.

**To view available agents**: Run `/agent-list` or check:
- Local: `.claude/agents/`
- User: `~/.agentecflow/agents/`
- Global: `installer/core/agents/`

#### MAUI Stack Agents
- **maui-usecase-specialist**: UseCase pattern with Either monad
- **maui-viewmodel-specialist**: MVVM with RelayCommand
- **dotnet-testing-specialist**: xUnit with FluentAssertions

#### React Stack Agents
- **react-state-specialist**: Hooks, context, state management
- **react-testing-specialist**: React Testing Library, Vitest

#### Python Stack Agents
- **python-api-specialist**: FastAPI, Pydantic, async patterns
- **python-testing-specialist**: pytest, pytest-asyncio, fixtures

#### Python MCP Stack Agents
- **python-mcp-specialist**: MCP server architecture, tool/resource registration, LangGraph integration
- **python-testing-specialist**: pytest, pytest-asyncio, MCP client testing

#### TypeScript API Stack Agents
- **nestjs-api-specialist**: NestJS, dependency injection, decorators
- **typescript-domain-specialist**: Domain modeling, Result patterns
- **nodejs-testing-specialist**: Jest, Supertest, integration tests

#### .NET Microservice Stack Agents
- **dotnet-api-specialist**: FastEndpoints, REPR pattern, middleware
- **dotnet-domain-specialist**: DDD, Either monad, domain events
- **dotnet-testing-specialist**: xUnit, WebApplicationFactory, Testcontainers

### Usage Examples

#### Basic Usage
```bash
# Automatic stack detection and full workflow
/task-work TASK-042
```

#### With Options
```bash
# TDD mode with higher coverage threshold
/task-work TASK-042 --mode=tdd --coverage-threshold=90

# Fix only mode (for blocked tasks)
/task-work TASK-042 --fix-only

# With progress sync to epic/feature
/task-work TASK-042 --sync-progress

# Include full epic/feature context
/task-work TASK-042 --with-context
```

### Technology Detection Priority

1. **Primary**: Read `project.template` from `.claude/settings.json`
2. **Fallback**: Auto-detect from project files:
   - `*.csproj` with `Microsoft.Maui` → maui
   - `*.csproj` with `FastEndpoints` → dotnet-microservice
   - `package.json` with `react` → react
   - `package.json` with `@nestjs` → typescript-api
   - `requirements.txt` or `pyproject.toml` with `mcp` dependency → python-mcp
   - `requirements.txt` or `pyproject.toml` → python
3. **Default**: Use generic agents (software-architect, task-manager, test-verifier)

### Quality Gate Details

#### Tests Passing (Required)
- All test cases must pass
- No skipped tests allowed
- No test errors or warnings

#### Line Coverage (Required ≥ 80%)
- Percentage of code lines executed during tests
- Excludes generated code, interfaces
- Calculated by stack-specific coverage tool

#### Branch Coverage (Required ≥ 75%)
- Percentage of conditional branches tested
- Both true and false paths must be covered
- Critical for logic-heavy code

#### Performance (Warning if > 30s)
- Total test suite execution time
- Warning only, doesn't block
- Suggests optimization if exceeded

### Error Handling

#### Scenario: Task Not Found
```
❌ Error: Task TASK-XXX not found
Location checked: tasks/in_progress/TASK-XXX.md
Action: Verify task ID or check task state (backlog/blocked/completed)
```

#### Scenario: Tests Failing
```
❌ Task TASK-XXX - Tests Failed

Failed Tests:
1. test_feature_validation (line 45)
   Expected: ValidationError
   Actual: None

Action: Review implementation and run:
/task-work TASK-XXX --fix-only
```

#### Scenario: Low Coverage
```
⚠️  Task TASK-XXX - Coverage Below Threshold

Current: 72%
Required: 80%

Uncovered:
- feature_service.py lines 45-52 (error handling)
- feature_service.py lines 78-85 (edge case)

Action: Testing agent will generate additional tests automatically
```

### Advanced Options

```bash
# Dry run (show plan without executing)
/task-work TASK-XXX --dry-run

# Watch mode (continuous testing)
/task-work TASK-XXX --watch

# Parallel test execution
/task-work TASK-XXX --parallel

# Skip specific phase
/task-work TASK-XXX --skip-review

# Force specific agent
/task-work TASK-XXX --implementation-agent=custom-specialist
```

### Integration with External Tools

When task metadata includes external tool references:

```yaml
# In task frontmatter
external_tools:
  jira: PROJ-123
  linear: PROJECT-456
  github: #789
```

After successful completion, automatically sync:
- Update Jira sub-task status to "In Review"
- Update Linear issue progress to 100%
- Update GitHub issue with test results

### File Locations

```
tasks/
├── backlog/         # New tasks (BACKLOG state)
├── in_progress/     # Active work (IN_PROGRESS state)
├── in_review/       # Passed quality gates (IN_REVIEW state)
├── blocked/         # Failed quality gates (BLOCKED state)
└── completed/       # Finished tasks (COMPLETED state)
```

### Success Metrics

After running `/task-work`:
- ✅ All agents invoked automatically
- ✅ No manual intervention required
- ✅ Quality gates enforced consistently
- ✅ State transitions handled automatically
- ✅ Comprehensive report generated

### Troubleshooting

**Problem**: Agents not invoked
- **Cause**: Command reading stopped before execution protocol
- **Fix**: Ensure execution protocol is first content Claude sees

**Problem**: Wrong agents selected
- **Cause**: Stack detection failed or incorrect settings
- **Fix**: Verify `.claude/settings.json` has correct `project.template`

**Problem**: Task tool not found
- **Cause**: Claude Code version doesn't support Task tool
- **Fix**: Update Claude Code to latest version

**Problem**: Agent not found
- **Cause**: Stack-specific agent doesn't exist
- **Fix**: System falls back to default agents automatically

### Best Practices

1. **Always start with `/task-work`** - Don't manually implement
2. **Trust the agents** - They're specialized for their domains
3. **Review quality gate failures** - They indicate real issues
4. **Use appropriate mode** - TDD for logic, BDD for features
5. **Keep tasks focused** - One feature per task works best

### Migration from Previous System

If you previously used separate commands:
- ❌ `/task-implement` → Use `/task-work`
- ❌ `/task-test` → Use `/task-work`
- ❌ Manual quality checks → Automatic in `/task-work`

### Command Philosophy

**"Implementation and testing are inseparable"**

This command embodies quality-first development by:
- Combining implementation with test creation
- Automatically running tests after implementation
- Enforcing quality gates before state transitions
- Supporting multiple development methodologies

Part of the streamlined 3-command workflow:
1. `/task-create` - Define the work
2. `/task-work` - Build and verify (THIS COMMAND)
3. `/task-complete` - Ship it

---

