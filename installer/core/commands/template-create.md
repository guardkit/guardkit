---
format_version: 1
description: AI-powered template generation from an existing codebase (brownfield harvest).
---

# Template Create - AI-Powered Template Generation from Existing Codebase

Orchestrates complete template creation from existing codebases using AI-powered analysis and generation.

**Status**: IMPLEMENTED (TASK-010)

## Purpose

Automate template creation from brownfield (existing) codebases by:
1. AI-native codebase analysis (TASK-51B2) - AI infers language, framework, architecture directly
2. Generating manifest.json (TASK-005)
3. Generating settings.json (TASK-006)
4. Generating .template files (TASK-008)
5. Generating CLAUDE.md (TASK-007)
6. Recommending specialized agents (TASK-009)
7. Saving complete template package

**Note**: As of TASK-51B2, the command uses AI-native analysis. No Q&A sessions, no detector code - AI analyzes codebases directly and infers all metadata. Use `--name` flag to override AI-generated template names if needed.

## Usage

```bash
/template-create                          # AI-native analysis of the current directory
/template-create --name my-api-template   # override the AI-generated template name
/template-create --output-location repo   # team distribution (requires install.sh)
/template-create --path /path/to/codebase # analyze a specific codebase
/template-create --validate               # extended validation + quality report
/template-create --dry-run                # analyze only, don't save
```

Every flag is defined once in `## Command Options` below. Full walk-throughs:
`template-create-ext.md` § Examples (original usage listing preserved verbatim).

## Complete Workflow

The command orchestrates all template creation phases:

```
Phase 1: AI-Native Codebase Analysis (TASK-51B2)
├─ File collection (stratified sampling, max 20 samples)
├─ Directory tree generation
├─ AI infers ALL metadata from codebase:
│  ├─ Primary language (from file extensions, config files)
│  ├─ Framework (from dependencies: package.json, requirements.txt, *.csproj)
│  ├─ Architecture pattern (from folder structure)
│  ├─ Testing framework (from test files)
│  └─ Template name (suggested from project)
├─ Architecture analysis (patterns, layers, abstractions)
└─ Quality assessment (SOLID, DRY, YAGNI)

Phase 2: Manifest Generation (TASK-005)
├─ Template identity (name, version, author)
├─ Technology stack detection
├─ Framework version inference
├─ Placeholder extraction
└─ Complexity scoring

Phase 3: Settings Generation (TASK-006)
├─ Naming conventions extraction
├─ File organization patterns
├─ Layer mappings
├─ Code style inference
└─ Generation options

Phase 3.5: QA Verification Seeds (PB-6, additive — see template-create-ext.md)
├─ E1/E3 F2+F3 INSTANCES into SOURCE repo; E2 stack-typed qa/ stubs into template dir
└─ E4 F12 stub per layer_mapping; every write per-file-if-absent (K5)

Phase 4: Template File Generation (TASK-008)
├─ AI-powered placeholder extraction
├─ Template content generation
├─ Pattern identification
├─ Quality scoring
└─ Validation

Phase 4.5: Completeness Validation (TASK-040)
├─ CRUD operation completeness checks
├─ Layer symmetry validation
├─ False negative detection
├─ Auto-fix recommendations
└─ Quality gate enforcement

Phase 5: Agent Recommendation (TASK-009)
├─ Capability needs identification
├─ Gap analysis vs existing agents
├─ AI-powered agent generation
└─ Reusability assessment

Phase 5.5: Agent Formatting (Automatic)
├─ Runs /agent-format on all generated agents
├─ Adds boundary section templates (ALWAYS/NEVER/ASK)
├─ Ensures structural consistency
├─ Quality: 6/10 (structural, not domain-specific)
└─ Sets foundation for Phase 8 enhancement

Phase 6: CLAUDE.md Generation (TASK-007)
├─ Template documentation
├─ Usage instructions
├─ Best practices
├─ Agent integration guide
└─ **[DEFAULT] Rules structure generation (use --no-rules-structure to opt out)**
    ├─ Core CLAUDE.md (~5KB)
    ├─ rules/code-style.md
    ├─ rules/testing.md
    ├─ rules/patterns/*.md
    └─ rules/guidance/*.md (with paths: frontmatter)

Phase 7: Package Assembly
├─ Directory structure creation
├─ File writing (manifest, settings, CLAUDE.md)
├─ Template files organization
├─ Agent files (if generated)
└─ Validation summary

Phase 7.5: Extended Validation (TASK-043) [OPTIONAL - only with --validate]
└─ Placeholder/pattern/docs/agent/manifest checks → quality score (0-10),
   validation-report.md, exit 0/1/2 (detail: ext)

Phase 8: Agent Task Creation (TASK-PHASE-8-INCREMENTAL, TASK-UX-2F95, TASK-UX-3A8D, TASK-DOC-1C5A) [DEFAULT - skip with --no-create-agent-tasks]
├─ Creates one task per agent file
├─ Task metadata includes agent_file, template_dir, template_name, agent_name
├─ Tasks created in backlog with priority: medium
├─ Displays boundary sections announcement (TASK-DOC-1C5A):
│  ├─ Explains ALWAYS (5-7), NEVER (5-7), ASK (3-5) format
│  ├─ Shows emoji prefixes (✅/❌/⚠️)
│  └─ Expected validation output
├─ Displays two enhancement options:
│  ├─ Option A (Recommended): /agent-enhance template-name/agent-name --hybrid (2-5 minutes per agent)
│  └─ Option B (Optional): /task-work TASK-AGENT-XXX (30-60 minutes per agent - full workflow)
└─ Both approaches use the same AI enhancement logic with boundary validation

**Boundary Sections**: Enhanced agents automatically include:
- ALWAYS (5-7 rules): Non-negotiable actions
- NEVER (5-7 rules): Prohibited actions
- ASK (3-5 scenarios): Escalation situations

See [Understanding Boundary Sections](#understanding-boundary-sections) for details.
```

## Command Options

### Required Options
None - all options have defaults

### Optional Options

```bash
--name NAME              Custom template name (overrides AI-generated name)
                         Pattern: lowercase, numbers, hyphens only (^[a-z0-9-]+$)
                         Length: 3-50 characters
                         Examples: my-api-template, react-admin, dotnet-api
                         Default: AI-generated from codebase analysis

--output-location LOC    Where to save template package (TASK-068)
  -o LOC                 'global' = ~/.agentecflow/templates/ (default, immediate use)
                         'repo' = installer/core/templates/ (distribution, requires install.sh)
                         Default: global

--path PATH              Path to codebase to analyze
                         Default: current directory

--output PATH            DEPRECATED - Output directory for template package
                         Use --output-location instead
                         Default: determined by --output-location

--max-templates N        Maximum template files to generate
                         Default: unlimited (all eligible files)

--dry-run                Analyze and show plan without saving
                         Default: false

--save-analysis          Save analysis JSON for debugging
                         Default: false

--no-agents              Skip agent generation phase
                         Default: false (agents are generated)

--create-agent-tasks     Create individual enhancement tasks for each agent (default: enabled)
                         DEPRECATED: Use --no-create-agent-tasks to disable

--no-create-agent-tasks  Skip agent task creation (TASK-UX-3A8D)
                         Default: false (tasks ARE created by default)

                         By default (when not specified):
                         - Runs Phase 8: Task Creation
                         - Creates one task per agent file
                         - Displays two enhancement options:
                           - Option A (Recommended): /agent-enhance for fast enhancement (2-5 minutes per agent)
                           - Option B (Optional): /task-work for full workflow with quality gates (30-60 minutes)
                         - Both approaches use the same AI enhancement logic
                         - Provides control over which agents to enhance and when

                         Use --no-create-agent-tasks to skip task creation when:
                         - You don't plan to enhance agents immediately
                         - You prefer manual task creation later
                         - You're creating templates for evaluation only

--validate               Run extended validation and generate quality report (TASK-043)
                         Default: false (only Phase 5.5 validation runs)

                         When enabled:
                         - Runs all Phase 5.5 completeness checks
                         - Adds extended validation checks (Phase 5.7)
                         - Generates validation-report.md in template directory
                         - Exit code based on quality score:
                           0 = Score ≥8/10 (production ready)
                           1 = Score 6.0-7.9/10 (needs improvement)
                           2 = Score <6/10 (not ready)

                         Extended checks include:
                         - Placeholder consistency validation
                         - Pattern fidelity spot-checks (5 random files)
                         - Documentation completeness verification
                         - Agent reference validation
                         - Manifest accuracy checks

--verbose                Show detailed progress and debugging info
                         Default: false

--use-rules-structure    Generate modular .claude/rules/ structure (default: enabled)
                         Default: true (TASK-TC-DEFAULT-FLAGS)

                         By default:
                         - Creates .claude/rules/ directory
                         - Generates rule files with path frontmatter
                         - Groups patterns and agents in subdirectories
                         - Core CLAUDE.md reduced to ~5KB
                         - 60-70% context window reduction

                         Benefits:
                         - Better organization for complex templates
                         - Path-specific rule loading
                         - Improved maintainability

--no-rules-structure     Use single CLAUDE.md + progressive disclosure instead
                         of modular rules/ directory structure

                         Use when:
                         - Simple templates (<15KB)
                         - Universal rules only (no path-specific patterns)
                         - Backward compatibility needed

--claude-md-size-limit SIZE  Maximum size for core CLAUDE.md content
                         Format: NUMBER[KB|MB] (e.g., 100KB, 1MB)
                         Default: 50KB (TASK-TC-DEFAULT-FLAGS)
                         Use for complex codebases that exceed default limit
                         Example: /template-create --claude-md-size-limit 100KB
```

## Exit Codes

- `0` - Template created successfully
- `1` - User cancelled during Q&A
- `2` - Codebase not found or inaccessible
- `3` - AI analysis failed (and no fallback available)
- `4` - Component generation failed
- `5` - Validation failed
- `6` - Save failed (permissions, disk space)
- `130` - Interrupted with Ctrl+C (session saved)


## Reference Slices (load on demand)

Extended documentation: `template-create-ext.md` (same directory — K13 core/`-ext`
shape). Read the section you need:

| Need | Ext section |
|---|---|
| Package layout, size targets | Output Structure |
| Phase 1 analysis + output JSON | AI-Native Codebase Analysis · AI Analysis Output |
| Phase 3-7 generation detail | Component Generation |
| ALWAYS/NEVER/ASK boundary format | Understanding Boundary Sections |
| Common errors | Error Handling |
| Example walk-throughs | Examples |
| Related-command integration | Integration Points |
| Module map, testing, performance | Implementation Details … Performance Considerations |
| Related commands, dependencies | Related Commands … See Also |

## Command Execution

Execute this command using a checkpoint-resume loop that handles Python-Claude agent bridge communication.

### Execution Loop

When the user invokes `/template-create`, execute this loop:

```
LOOP (max 5 iterations to prevent infinite loops):
  1. Run Python orchestrator
  2. Capture exit code
  3. IF exit code == 0: SUCCESS - display results and exit loop
  4. IF exit code == 42: AGENT NEEDED - handle bridge protocol (see below)
  5. IF exit code == other: ERROR - display error and exit loop
  6. After handling exit code 42, add --resume flag and continue loop
```

### Step 1: Run Python Orchestrator

**IMPORTANT**: This script requires Python 3.10+ (uses `|` union type syntax).

```bash
python3 ~/.agentecflow/bin/template-create-orchestrator "$@"
```

If Python version error occurs (`TypeError: unsupported operand type(s) for |`), the user needs Python 3.10+.

Capture the exit code from this command.

### Phase-Specific Agent Invocations

The `/template-create` command may require **two separate agent invocations** during execution:

| Phase | Request File | Response File | Purpose |
|-------|--------------|---------------|---------|
| Phase 1 | `.agent-request-phase1.json` | `.agent-response-phase1.json` | AI Codebase Analysis |
| Phase 5 | `.agent-request-phase5.json` | `.agent-response-phase5.json` | Agent Recommendation |

**Workflow**:
```
Run 1: Orchestrator → Exit 42 (Phase 1 request)
       Claude → Invoke agent via Task tool
       Claude → Write phase1 response
       Claude → Resume orchestrator

Run 2: Orchestrator → Exit 42 (Phase 5 request)
       Claude → Invoke agent via Task tool
       Claude → Write phase5 response
       Claude → Resume orchestrator

Run 3: Orchestrator → Exit 0 (Success)
       Claude → Display results, cleanup
```

**IMPORTANT**: Each phase has its own request/response file pair. Do NOT confuse Phase 1 responses with Phase 5 requests.

### Step 2: Handle Exit Code 42 (NEED_AGENT)

When exit code is 42, Python has written a request file and needs Claude to invoke an agent.

**2a. Read the agent request file:**

The request file is **phase-specific**. Check which phase file exists:

```bash
# Phase 1 (AI Codebase Analysis)
cat .agent-request-phase1.json

# Phase 5 (Agent Recommendation)
cat .agent-request-phase5.json
```

The file has this structure:
```json
{
  "request_id": "uuid-string",
  "version": "1.0",
  "phase": 1,
  "phase_name": "ai_analysis",
  "agent_name": "architectural-reviewer",
  "prompt": "Full prompt text for the agent...",
  "timeout_seconds": 120,
  "created_at": "ISO-8601-timestamp",
  "context": {},
  "model": null
}
```

**NOTE**: The `phase` field indicates which phase requested the agent:
- `phase: 1` = AI Codebase Analysis (Phase 1)
- `phase: 5` = Agent Recommendation (Phase 5)

**2b. Invoke the agent using Task tool:**

**CRITICAL**: You MUST use the Task tool to invoke the agent. Do NOT write the response directly.

Use the Task tool to invoke the agent specified in `agent_name` with the `prompt` from the request file:

```
Task tool invocation:
  subagent_type: The agent_name from the request (e.g., "architectural-reviewer")
  prompt: The full prompt text from the request file
  description: "Analyze codebase architecture" (or similar based on phase)
```

**Why Task tool is required**:
1. Ensures consistent agent behavior across invocations
2. Provides proper model selection for the agent
3. Maintains separation between orchestration and analysis
4. Enables proper timeout handling and error recovery

**DO NOT** write the response file directly based on your own analysis. The bridge protocol requires actual agent subprocess invocation.

Capture the agent's complete response text.

**2c. Write the agent response file:**

Create the **phase-specific** response file matching the request phase:

- If request was `.agent-request-phase1.json` → write `.agent-response-phase1.json`
- If request was `.agent-request-phase5.json` → write `.agent-response-phase5.json`

Use this exact structure:
```json
{
  "request_id": "<copy from request>",
  "version": "1.0",
  "status": "success",
  "response": "<agent's complete response text as a string>",
  "error_message": null,
  "error_type": null,
  "created_at": "<current ISO-8601 timestamp>",
  "duration_seconds": <time taken in seconds>,
  "metadata": {
    "agent_name": "<copy from request>",
    "model": "claude-sonnet-4"
  }
}
```

**CRITICAL**: The `response` field MUST be a string, not an object. If the agent returns JSON, serialize it to a string.

**2d. Delete the request file:**

Delete the phase-specific request file that was processed:

```bash
# If processing Phase 1 request:
rm .agent-request-phase1.json

# If processing Phase 5 request:
rm .agent-request-phase5.json
```

**2e. Re-run orchestrator with --resume flag:**

Add `--resume` to the original arguments and continue the loop:

```bash
python3 ~/.agentecflow/bin/template-create-orchestrator "$@" --resume
```

### Step 3: Handle Success (Exit Code 0)

When exit code is 0:
1. Display the success message from Python's output
2. Clean up any remaining bridge files:
   ```bash
   rm -f .agent-request-phase*.json .agent-response-phase*.json .template-create-state.json
   ```
3. Exit the loop

### Step 4: Handle Errors (Other Exit Codes)

| Exit Code | Meaning | Action |
|-----------|---------|--------|
| 0 | SUCCESS | Display results, cleanup, exit |
| 1 | USER_CANCELLED | Display cancellation message |
| 2 | CODEBASE_NOT_FOUND | Display error with path |
| 3 | ANALYSIS_FAILED | Display error, suggest --verbose |
| 4 | GENERATION_FAILED | Display error |
| 5 | VALIDATION_FAILED | Display validation errors |
| 6 | SAVE_FAILED | Display file I/O error |
| 42 | NEED_AGENT | Handle bridge protocol (loop) |
| 130 | INTERRUPTED | Display interruption message |

### Error Handling for Bridge Protocol

**If no `.agent-request-phase*.json` file exists when exit code is 42:**
```
ERROR: Exit code 42 received but no .agent-request-phase*.json found.
This indicates a bug in the orchestrator. Please report this issue.
```

**If agent invocation fails:**
Write an error response to the phase-specific response file (e.g., `.agent-response-phase1.json` or `.agent-response-phase5.json`):
```json
{
  "request_id": "<from request>",
  "version": "1.0",
  "status": "error",
  "response": null,
  "error_message": "<error description>",
  "error_type": "AgentInvocationError",
  "created_at": "<timestamp>",
  "duration_seconds": 0,
  "metadata": {}
}
```
Then continue with `--resume` to let Python handle the fallback.

**If JSON parsing fails:**
Display error and suggest re-running without --resume:
```
ERROR: Failed to parse bridge protocol files.
Try: rm -f .agent-request-phase*.json .agent-response-phase*.json .template-create-state.json
Then re-run: /template-create [original args]
```

### Example Execution Flow

```
User: /template-create --path /my/project

[Iteration 1 - Phase 1: AI Codebase Analysis]
  Run: python3 ~/.agentecflow/bin/template-create-orchestrator --path /my/project
  Exit code: 42

  Read: .agent-request-phase1.json
  Agent: architectural-reviewer
  Invoke agent via Task tool...
  Write: .agent-response-phase1.json
  Delete: .agent-request-phase1.json

[Iteration 2 - Phase 5: Agent Recommendation]
  Run: python3 ~/.agentecflow/bin/template-create-orchestrator --path /my/project --resume
  Exit code: 42

  Read: .agent-request-phase5.json
  Agent: architectural-reviewer
  Invoke agent via Task tool...
  Write: .agent-response-phase5.json
  Delete: .agent-request-phase5.json

[Iteration 3 - Completion]
  Run: python3 ~/.agentecflow/bin/template-create-orchestrator --path /my/project --resume
  Exit code: 0

  SUCCESS: Template created at ~/.agentecflow/templates/my-project/
  Cleanup bridge files (rm -f .agent-*-phase*.json .template-create-state.json)
  Exit loop
```

**Note**: This command uses the orchestrator pattern with checkpoint-resume. The Python orchestrator handles state persistence in `.template-create-state.json`, and the bridge protocol enables AI-powered agent generation that produces 7-8 agents at 90%+ confidence (vs 3 agents at 68% with heuristic fallback).
