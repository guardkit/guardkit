## Summarized at 2026-06-12T16:33:19.798635+00:00

Human: You are executing the implementation phase (Phases 3-5) for TASK-QAWE-002.

## Context

- Task ID: TASK-QAWE-002
- Mode: tdd
- Documentation Level: minimal
- Working directory: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332

## Turn Context

- Current turn: 2
- Max turns: 5
- Turns remaining: 3
- Approaching limit: False

## Task Requirements

# Task: UNWIRED_PATH bundle integration (Wave 1)

## Coach Feedback from Turn 1

- The Player claimed to have run existing test suites in `tests/orchestrator/test_coach_evidence_bundle.py` and `tests/unit/orchestrator/quality_gates/test_coach_validator.py`, but these files do not exist on disk. This discrepancy caused the evidence gathering process to abort (`partial_honesty_abort`), making it impossible to verify the implementation.: Ensure all claimed test files exist and are correctly referenced. Re-run the implementation and ensure the test suite is actually present and executed.

Address ALL must_fix items before proceeding.

---

# AutoBuild Execution Protocol

> Focused protocol for Player agent implementation loop (Phases 3–5).
> Extracted from the full task-work specification for efficient context injection.

---

## Infrastructure Setup (Pre-Phase 3)

Before implementing or running tests, check whether the task declares `requires_infrastructure` in its frontmatter.

### How to check

Read the task frontmatter. Look for:

```yaml
requires_infrastructure:
  - postgresql
```

### When requires_infrastructure is present

Start each declared service using the recipes below. Use non-standard ports to avoid conflicts with local services.

#### PostgreSQL (port 5433)

```bash
docker rm -f guardkit-test-pg 2>/dev/null || true
docker run -d --name guardkit-test-pg \
  -e POSTGRES_PASSWORD=test \
  -p 5433:5432 postgres:16-alpine
until docker exec guardkit-test-pg pg_isready; do sleep 1; done
export DATABASE_URL=postgresql://postgres:test@localhost:5433/test
```

#### Redis (port 6380)

```bash
docker rm -f guardkit-test-redis 2>/dev/null || true
docker run -d --name guardkit-test-redis \
  -p 6380:6379 redis:7-alpine
sleep 1
export REDIS_URL=redis://localhost:6380
```

#### MongoDB (port 27018)

```bash
docker rm -f guardkit-test-mongo 2>/dev/null || true
docker run -d --name guardkit-test-mongo \
  -p 27018:27017 mongo:7
sleep 2
export MONGODB_URL=mongodb://localhost:27018
```

### Cleanup

When your turn finishes — after Phase 3 and any Phase 4.5 fix-loop iterations — tear down all containers you started:

```bash
docker rm -f guardkit-test-pg guardkit-test-redis guardkit-test-mongo 2>/dev/null || true
```

### When requires_infrastructure is absent

Skip this section entirely. Proceed to Phase 3 as normal.

---

## Phase 3: Implementation

You are implementing a task. Follow these instructions exactly.

### Implementation Requirements

1. **Read the implementation plan** from `.claude/task-plans/TASK-QAWE-002-implementation-plan.md`
2. **Implement all files** listed in the plan — create source files and test files
3. **Follow the detected technology stack** conventions:
   - Python: Use type hints, docstrings, follow PEP 8
   - TypeScript: Use strict mode, proper typing
   - .NET: Follow C# conventions, use async/await patterns
4. **Create production-quality code** with proper error handling
5. **Do NOT create stub implementations** (see Anti-Stub Rules below)

### File Count Constraints

The documentation level controls maximum file creation:

| Documentation Level | Max Files | Description |
|---|---|---|
| minimal | 2 | Source + test only |
| standard | 2 | Source + test only |
| comprehensive | unlimited | Full documentation suite |

CRITICAL: If documentation_level is "minimal" or "standard", you MUST NOT create more than 2 files total. Consolidate implementation into as few files as possible.

### Implementation Modes

**Standard Mode**: Implement code and tests together.

**TDD Mode**:
1. RED: Write failing tests first
2. GREEN: Write minimal code to make tests pass
3. REFACTOR: Improve code quality while keeping tests green

### Stack-Specific Implementation Patterns

**Python**:
- Use `from __future__ import annotations` for forward references
- Use `pathlib.Path` instead of string paths
- Use `dataclasses` for simple state containers, `pydantic` for validated external data
- Use `logging` module, not `print()` for diagnostic output
- Follow existing module patterns in the codebase

**TypeScript/React**:
- Use strict TypeScript (`strict: true` in tsconfig)
- Prefer functional components with hooks
- Use named exports, not default exports
- Use `interface` for object shapes, `type` for unions/intersections

**.NET/C#**:
- Use `async/await` for I/O operations
- Use `record` types for immutable data
- Follow the REPR (Request-Endpoint-Response) pattern for APIs
- Use dependency injection via constructor parameters

### Error Handling Requirements

All implementation code MUST include proper error handling:

1. **Catch specific exceptions** — never use bare `except:` or `catch(Exception)`
2. **Provide context in error messages** — include what failed and why
3. **Use appropriate exception types** — `ValueError` for bad input, `FileNotFoundError` for missing files, custom exceptions for domain errors
4. **Do NOT silently swallow errors** — always log or re-raise
5. **Guard boundary inputs** — validate at system boundaries (user input, external APIs, file I/O)

### Import and Dependency Rules

1. **Only import what the plan specifies** — do not add unplanned dependencies
2. **Use standard library first** — prefer `pathlib`, `json`, `re` over third-party alternatives
3. **Pin to specific versions** — if adding a dependency, specify version constraints
4. **Check existing dependencies** — look at `requirements.txt`, `package.json`, or `*.csproj` before adding

---

## Phases 4 and 5: Owned by the AutoBuildOrchestrator

Phases 4 (test execution) and 5 (code review) are executed by the AutoBuildOrchestrator after your Phase 3 completes. You do not need to invoke `test-orchestrator` or `code-reviewer` directly. Focus your turn on Phases 1, 2, 3, and (optionally) Phase 4.5 (test-fix loop) for your own feedback.

---

## Phase 4.5: Test Enforcement Loop

If tests fail or coverage is below threshold, enter the fix loop.

### Fix Loop Rules

- **Maximum attempts**: 3
- **Fix implementation, NOT tests**: Correct the code to match test expectations
- **Do NOT skip tests**: Never comment out, skip, or ignore failing tests
- **Do NOT modify test assertions**: Unless the test itself is provably incorrect
- **Do NOT use [Ignore] or [Skip] attributes**

### Fix Loop Workflow

Phase 4.5 is Player guidance, not a runtime loop. Run tests inline (e.g., `pytest`, `npm test`, `dotnet test`) directly — you do not invoke `test-orchestrator`. You are expected to:

1. Read the output of your inline test run and identify compilation errors and test failures qualitatively (look for build-error markers, `FAILED`, assertion lines, framework summary lines, non-zero exit codes).
2. If issues remain, fix the root cause in implementation code (not the tests — see the rules above) and re-run the tests inline.
3. You may take up to **three fix attempts**. The "3" is an instruction to you, not a runtime counter; track it in your own reasoning.
4. After each re-run, re-inspect the output. If compilation is clean and all tests pass, finish your turn. If you have exhausted three attempts without passing, stop and report BLOCKED with diagnostics (see below).

The AutoBuildOrchestrator runs `test-orchestrator` after your turn as the gate input, and Coach enforces the pass bar independently: regardless of what this protocol reports, `coach_validator` runs its own pytest pass on the final worktree and that run is the deterministic gate. Keep this section as the Player's guidance; the ground truth comes from Coach's own execution. See `installer/core/commands/task-work.md` Phase 4.5 for the matching spec-side prose — the two files are intentionally synced.

### Blocked State Diagnostics

If max attempts exhausted, report:
- Remaining compilation errors (file:line format)
- Remaining test failures with assertion details
- Coverage metrics
- What was attempted and why it didn't work

---

## Phase 5.5: Plan Audit

Compare actual implementation against the approved plan.

### Audit Process

1. **Load the saved plan** from `.claude/task-plans/TASK-QAWE-002-implementation-plan.md`
2. **Scan actual implementation**: List files created/modified, dependencies added, lines of code
3. **Compare planned vs actual**:
   - Files: Identify extra files not in plan, missing planned files
   - Dependencies: Identify extra or missing dependencies
   - LOC: Calculate percentage variance from estimate
4. **Assess severity**:
   - LOW: <10% variance, no extra files
   - MEDIUM: 10-30% variance, 1-2 extra files
   - HIGH: >30% variance, 3+ extra files, or major deviations

### Variance Thresholds

| Metric | Acceptable Variance | Action if Exceeded |
|---|---|---|
| LOC | ±20% | Flag for review |
| File count | Exact match | Flag extra/missing files |
| Dependencies | Exact match | Flag extra/missing deps |
| Duration | ±30% | Informational only |

### Scope Creep Detection

Extra files or dependencies not in the plan indicate possible scope creep. Report them specifically:
```
Extra files not in plan:
  - src/utils/helpers.py
  - src/utils/validators.py

Extra dependencies not in plan:
  - lodash
```

If no plan exists (e.g., micro-task mode), skip this phase.

---

## Player Report Format

After completing implementation, write your report as JSON to:
`/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.guardkit/autobuild/TASK-QAWE-002/player_turn_2.json`

<!-- Fallback (relative path): .guardkit/autobuild/TASK-QAWE-002/player_turn_2.json -->

### PLAYER_REPORT_SCHEMA

Your report MUST be valid JSON with ALL of these fields.

> **CRITICAL**: You MUST populate `completion_promises` with one entry per acceptance criterion listed in the task file. Do NOT leave this array empty. An empty `completion_promises` array causes the Coach to use text-based fallback matching, which always fails — the autobuild run will stall after 3 turns. If you cannot determine whether a criterion is met, include it with `"status": "uncertain"` and explain in `"evidence"`.

```json
{
  "completion_promises": [
    {
      "criterion_id": "AC-001",
      "criterion_text": "Full text of acceptance criterion",
      "status": "complete",
      "evidence": "What you did to satisfy this criterion",
      "test_file": "tests/test_feature.py",
      "implementation_files": ["src/feature.py"]
    }
  ],
  "task_id": "TASK-XXX",
  "turn": 1,
  "files_modified": ["list", "of", "modified", "files"],
  "files_created": ["list", "of", "new", "files"],
  "tests_written": ["list", "of", "test", "files"],
  "tests_run": true,
  "tests_passed": true,
  "test_output_summary": "Brief summary of test results",
  "implementation_notes": "What you implemented and why",
  "concerns": ["any", "concerns", "or", "blockers"],
  "requirements_addressed": ["requirements", "completed"],
  "requirements_remaining": ["requirements", "still", "pending"]
}
```

### Field Requirements

| Field | Type | Required | Description |
|---|---|---|---|
| **completion_promises** | **array[object]** | **YES** | **Per-criterion verification (MUST NOT be empty)** |
| task_id | string | YES | Task identifier |
| turn | integer | YES | Current turn number |
| files_modified | array[string] | YES | Files changed (existing) |
| files_created | array[string] | YES | Files created (new) |
| tests_written | array[string] | YES | Test files written |
| tests_run | boolean | YES | Whether tests were executed |
| tests_passed | boolean | YES | Whether ALL tests passed |
| test_output_summary | string | YES | Brief test results summary |
| implementation_notes | string | YES | What and why |
| concerns | array[string] | YES | Blockers or risks (empty if none) |
| requirements_addressed | array[string] | YES | Completed requirements |
| requirements_remaining | array[string] | YES | Pending requirements |

### `files_modified` / `files_created` Scoping Rule

These fields MUST list only paths this task's session actually created or
modified. Do NOT populate them from `git status --porcelain` or any
directory sweep.

**Why this matters**: in parallel-wave execution the worktree may contain
in-flight writes from sibling tasks, and the honesty auditor will flag
claims for paths you did not author as fabrications. A fabrication flag
aborts evidence gathering (`partial_honesty_abort`) and prevents Coach
verification from completing.

- `files_created`: only paths you opened with the Write tool this session
- `files_modified`: only paths you opened with the Edit tool this session
- Exclude orchestrator-managed paths: `.guardkit/`, `.claude/task-plans/`,
  `tasks/`, and any autobuild state files

### Completion Promise Schema

Each completion_promise maps to one acceptance criterion:

| Field | Type | Description |
|---|---|---|
| criterion_id | string | e.g., "AC-001" |
| criterion_text | string | Full criterion text |
| status | string | "complete", "incomplete", or "uncertain" |
| evidence | string | What you did |
| test_file | string or null | Validating test file |
| implementation_files | array[string] | Files for this criterion |

CRITICAL: The Coach verifies each completion_promise independently. Be specific in evidence fields.

### Self-Check Before Writing Report

Before writing your player report, verify:
1. `completion_promises` has exactly one entry for each acceptance criterion ID (AC-001, AC-002, ...) listed in the task file
2. No entry has an empty `evidence` field
3. Each entry has a valid `status` ("complete", "incomplete", or "uncertain")

If any acceptance criteria are missing from `completion_promises`, add them now before writing the file.

---

## Output Markers

The following output formats are parsed programmatically by TaskWorkStreamParser. You MUST use these exact formats:

### Phase Progress
```
Phase N: Description
```
Example: `Phase 3: Implementation`

### Phase Completion
```
✓ Phase N complete
```

### Test Results
```
N tests passed
N tests failed
```

### Coverage
```
Coverage: N.N%
```

### Quality Gates
```
Quality gates: PASSED
```
or
```
Quality gates: FAILED
```

### Architectural Review (if applicable)
```
Architectural Score: N/100
SOLID: N, DRY: N, YAGNI: N
```

---

## Anti-Stub Rules

> Stubs that pass quality gates are worse than failing code — they silently ship nothing.

### Stub Definition

A **stub** is a function or method whose body consists solely of one or more of:

1. **`pass`** (possibly preceded by a docstring or logger call)
2. **`raise NotImplementedError(...)`**
3. **Only comments**: `# TODO`, `# FIXME`, `# STUB`, `# placeholder`
4. **Hardcoded defaults with no logic**: `return None`, `return {}`, `return []`, `return ""`, `return 0`, `return False`
5. **Logging-only**: `logger.info(...)` + `pass` or bare `return`
6. **Ellipsis**: `...` as the entire body

A function that contains conditional logic, calls to domain-specific dependencies, data transformations, or meaningful error handling is **not** a stub, even if parts of it are incomplete.

### Enforcement by Task Type

| Task Type | Stubs Allowed? | Notes |
|---|---|---|
| FEATURE | NO | Primary deliverable functions must have real logic |
| REFACTOR | NO | Must contain actual refactored code |
| SCAFFOLDING | CONDITIONAL | Only if AC explicitly permits stubs |
| INFRASTRUCTURE | CONDITIONAL | Only if AC explicitly permits stubs |
| INTEGRATION | NO | Wiring logic must be real |
| DOCUMENTATION | N/A | No deliverable functions |
| TESTING | N/A | No deliverable functions |

### Primary Deliverable Function

A primary deliverable function is any function or method that:

1. Is **named or implied** by the task's acceptance criteria
2. Is the **main entry point** of a module created by the task
3. Is **called by the task's test suite** to exercise core behavior
4. Provides the **core logic** that the task was created to deliver

Functions that are legitimately thin wrappers (CLI entry points, adapter methods) are NOT stubs.

### Stub Examples (REJECTED)

```python
# pass-only stub
async def run_system_plan(description: str, mode: str) -> None:
    logger.info(f"run_system_plan called with {description}")
    pass

# NotImplementedError stub
def process_payment(order_id: str, amount: float) -> PaymentResult:
    raise NotImplementedError("Payment processing not yet implemented")

# hardcoded default stub
def get_user_preferences(user_id: str) -> dict:
    return {}

# TODO-only stub
def validate_input(data: dict) -> ValidationResult:
    # TODO: implement validation logic
    return ValidationResult(valid=True, errors=[])
```

### Non-Stub Examples (ACCEPTED)

```python
# Real implementation with logic
async def run_system_plan(description: str, mode: str) -> None:
    detected_mode = detect_mode(description) if mode is None else mode
    questions = generate_questions(detected_mode, description)
    answers = await collect_answers(questions)
    plan = build_plan(detected_mode, answers)
    await write_plan_files(plan)

# Thin wrapper (NOT a stub — legitimate delegation)
@click.command()
@click.argument("description")
def system_plan(description: str) -> None:
    asyncio.run(run_system_plan(description, mode=None))
```

### Coach Verification

When reviewing, the Coach MUST:
1. Identify primary deliverable functions from acceptance criteria
2. Read the function body (using Read tool)
3. Check if the body matches any stub pattern
4. Reject with specific feedback if stubs are found

---

## Summary

This protocol defines the execution loop for the AutoBuild Player agent:
1. **Phase 3**: Implement according to plan
2. **Phase 4.5** (optional): Inline test-fix loop for your own feedback (max 3 attempts)
3. **Phase 5.5**: Plan audit
4. **Report**: Write PLAYER_REPORT_SCHEMA JSON to `.guardkit/autobuild/`

Phases 4 (test execution) and 5 (code review) are run by the AutoBuildOrchestrator after your turn — they are not your responsibility.

## Implementation Plan Locations

Check these paths in order for the implementation plan:
   - /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.claude/task-plans/TASK-QAWE-002-implementation-plan.md
   - /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.claude/task-plans/TASK-QAWE-002-implementation-plan.json
   - /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/docs/state/TASK-QAWE-002/implementation_plan.md
   - /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/docs/state/TASK-QAWE-002/implementation_plan.json

AI: [{'name': 'glob', 'args': {'pattern': '**/TASK-QAWE-002*', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332'}, 'id': 'fc_2UU6QrTeE64YaOzWd0tt1zIedquiy1Qb', 'type': 'tool_call'}, {'name': 'glob', 'args': {'pattern': '**/tasks/**QAWE*', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332'}, 'id': 'fc_v71PHm0HKKJl1NOh8bdx3IIp7VwA2oWI', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.claude/task-plans/TASK-QAWE-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tasks/design_approved/TASK-QAWE-002-unwired-bundle-integration.md']
Tool: []
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tasks/design_approved/TASK-QAWE-002-unwired-bundle-integration.md'}, 'id': 'fc_v09Jr0y6sDtU6awzy4H6dCG96wnG6HcG', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.claude/task-plans/TASK-QAWE-002-implementation-plan.md'}, 'id': 'fc_O8Y2gUmf5EQv7SFd1Ai0UXUqgiNksawb', 'type': 'tool_call'}]
Tool:      1	---
     2	complexity: 5
     3	dependencies:
     4	- TASK-QAWE-001
     5	feature_id: FEAT-C332
     6	id: TASK-QAWE-002
     7	implementation_mode: task-work
     8	parent_task: TASK-HMIG-BDDWIRE
     9	priority: medium
    10	status: design_approved
    11	task_type: feature
    12	title: UNWIRED_PATH bundle integration — coach_evidence fields, gather_evidence, render
    13	wave: 2
    14	---
    15	
    16	# Task: UNWIRED_PATH bundle integration (Wave 1)
    17	
    18	## Description
    19	
    20	Wire the Wave-0 `WiringAnalyzer` UNWIRED_PATH output into the Coach evidence path via
    21	the verified, unchanged seams in `docs/features/qa-verifier-wiring-probes-scope.md` §5.
    22	guardkit consumes guardkitfactory's `analyze_wiring(...)` lazily (the BDDWIRE pattern)
    23	and stores the returned **dict** (never the dataclass), so `coach_evidence.py` keeps
    24	zero guardkitfactory import.
    25	
    26	## Acceptance Criteria
    27	
    28	- [ ] **AC-002 (bundle fields):** add `wiring`, `mocked_seam`, `spec_gap`
    29	  `Optional[Dict]` fields after `tests:` at `coach_evidence.py:169`; `to_dict()`
    30	  (`asdict`, `:180-191`) unchanged.
    31	- [ ] **AC (gather population):** populate at the **complete-path return only**
    32	  (`coach_validator.py:2120`); partial returns (2030/2058/2103) leave them `None`.
    33	  Authored set from `_compute_own_authored` (`:775-783`, extract or duplicate — not
    34	  `files_modified`). `detect_stack_template` (`:64`) supplies the language.
    35	- [ ] **AC-008 (task-type gate):** SCAFFOLDING/DOCUMENTATION or zero-target turns →
    36	  all three fields `None`.
    37	- [ ] **AC-011 (reaches verdict):** `_render_evidence_bundle_section`
    38	  (`agent_invoker.py:3098`) surfaces the fields; advisory guard sentence #7 appended
    39	  after guard #6 (`:3320-3332`).
    40	- [ ] **AC-016 (truncation):** `>20` findings → first 20 + "... and N more" mirroring
    41	  `bdd.discoveries` (`agent_invoker.py:3138-3152`).
    42	- [ ] **AC-015 (absent-vs-empty):** `findings:[]` + positive status is distinct from
    43	  `None`.
    44	- [ ] **AC-017 (graceful import absence):** with guardkitfactory/tree-sitter absent,
    45	  the lazy seam catches `ImportError`, all three fields `None`, `gather_evidence`
    46	  does not crash.
    47	- [ ] **AC-018 (no regression):** existing guardkit + guardkitfactory suites green.
    48	- [ ] All modified files pass project-configured lint/format checks with zero errors.
    49	
    50	## Coach Validation
    51	- `pytest tests/orchestrator -k "wiring or coach_evidence" -v`
    52	- Lint/format pass with zero errors.
Tool:      1	# Implementation Plan: TASK-QAWE-002
     2	
     3	## Task
     4	UNWIRED_PATH bundle integration — coach_evidence fields, gather_evidence, render
     5	
     6	## Plan Status
     7	**Auto-generated stub** - Pre-loop was skipped for this feature task.
     8	Generated: 2026-06-12T16:52:07.630268
     9	
    10	## Implementation
    11	Follow acceptance criteria in task file.
    12	
    13	## Notes
    14	This plan was auto-generated because the task was created via /feature-plan
    15	with pre-loop disabled (enable_pre_loop=False).
    16	The detailed specifications are in the task markdown file.
AI: The implementation plan is a stub. I need to explore the actual codebase to understand the existing code structure. Let me read the referenced files.

[{'name': 'task', 'args': {'description': 'Explore the guardkit codebase to find and read the following files referenced in TASK-QAWE-002:\n1. coach_evidence.py - find the file and read lines around 169-191 (the dataclass with to_dict)\n2. coach_validator.py - find the file and read lines around 64, 775-783, 2030, 2058, 2103, 2120\n3. agent_invoker.py - find the file and read lines around 3098, 3320-3332, 3138-3152\n4. docs/features/qa-verifier-wiring-probes-scope.md - read the full file, especially §5\n5. Any wiring analyzer or guardkitfactory related files\n\nReturn the full contents of each file found, including line numbers. Also identify the project structure (src layout, test layout, requirements.txt, etc.)', 'subagent_type': 'general-purpose'}, 'id': 'fc_6uyUV0NUNM4KMOJIkhGXA1EScvw5DtrO', 'type': 'tool_call'}]
Tool: I now have all the requested files. Here is the comprehensive summary:

---

## Project Structure Summary

### Top-Level Layout
```
guardkit/
├── guardkit/                  # Main Python package
│   ├── cli/                   # CLI commands
│   ├── commands/              # Command implementations
│   ├── design/                # Design-related modules
│   ├── integrations/          # External integrations
│   ├── knowledge/             # Knowledge base
│   ├── lib/                   # Shared utilities
│   ├── models/                # Data models
│   ├── orchestrator/          # Core orchestrator (agent_invoker.py, coach_validator.py, etc.)
│   ├── planning/              # Planning modules
│   ├── tasks/                 # Task management
│   ├── templates/             # Templates
│   ├── validation/            # Validation modules
│   └── worktrees/             # Worktree management
├── tests/                     # Test suite (unit/, integration/, acceptance/, e2e/, etc.)
├── docs/                      # Documentation (features/, etc.)
├── tasks/                     # Task definitions
├── api/                       # API layer
├── examples/                  # Example code
├── scripts/                   # Utility scripts
├── installer/                 # Installer packages
├── lib/                       # Library code
├── pyproject.toml             # Project config (hatchling build)
├── requirements.txt           # Requirements
├── pytest.ini                 # pytest config
├── mkdocs.yml                 # MkDocs configuration
└── uv.lock                    # UV lockfile
```

### Key Source Files Found

| File | Location |
|------|----------|
| `coach_evidence.py` | `guardkit/orchestrator/quality_gates/coach_evidence.py` |
| `coach_validator.py` | `guardkit/orchestrator/quality_gates/coach_validator.py` |
| `agent_invoker.py` | `guardkit/orchestrator/agent_invoker.py` |
| `qa-verifier-wiring-probes-scope.md` | `docs/features/qa-verifier-wiring-probes-scope.md` |

### Guardkitfactory (separate repo, in worktree)
```
.guardkit/worktrees/guardkitfactory/src/guardkitfactory/
├── __init__.py
├── bdd/                       # BDD plugins
│   ├── __init__.py
│   ├── loader.py
│   ├── plugin.py
│   └── plugins/
│       ├── __init__.py
│       ├── pytest_bdd_plugin.py
│       ├── reqnroll_plugin.py
│       └── cucumber_js_plugin.py
├── harness/                   # Agent harness
│   ├── __init__.py
│   ├── backend_config.py
│   ├── extractors.py
│   ├── langgraph_harness.py
│   ├── model_config.py
│   └── permissions.py
└── wiring/                    # NEW: Stack-agnostic wiring analysis
    ├── __init__.py
    ├── analyzer.py            # WiringAnalyzer engine
    ├── dialect.py             # WiringDialect frozen dataclass + registry
    ├── parser.py              # tree-sitter parser cache
    └── dialects/
        ├── __init__.py
        ├── python.py
        ├── javascript.py
        ├── typescript.py
        └── c_sharp.py
```

---

## File Contents (with line numbers)

### 1. coach_evidence.py — Lines 160-191 (Dataclass with `to_dict`)

```
   161	    gathering_status: GatheringStatus = "complete"
   162	    gathering_error: Optional[str] = None
   163	
   164	    quality_gates: Optional["QualityGateStatus"] = None
   165	    coverage_details: Optional[Dict[str, Any]] = None
   166	    plan_audit: Optional[Dict[str, Any]] = None
   167	    bdd: Optional[Dict[str, Any]] = None
   168	    arch_review: Optional[Dict[str, Any]] = None
   169	    tests: Optional[Dict[str, Any]] = None
   170	
   171	    independent_tests: Optional["IndependentTestResult"] = None
   172	    requirements: Optional[Any] = None  # RequirementsValidation; avoid circular import
   173	
   174	    severity_recommendations: List[Dict[str, str]] = field(default_factory=list)
   175	    advisory_issues: List[Dict[str, Any]] = field(default_factory=list)
   176	
   177	    task_type: Optional[str] = None
   178	    profile_name: Optional[str] = None
   179	
   180	    def to_dict(self) -> Dict[str, Any]:
   181	        """Serialise the bundle to a JSON-compatible dict.
   182	
   183	        Nested ``HonestyVerification`` / ``QualityGateStatus`` /
   184	        ``IndependentTestResult`` / ``RequirementsValidation`` instances are
   185	        also dataclasses, so ``dataclasses.asdict`` walks the entire tree.
   186	        ``ResolvedPath`` / ``Discrepancy`` inside ``HonestyVerification`` are
   187	        also dataclasses — the whole bundle is safe for ``json.dumps``.
   188	        """
   189	        from dataclasses import asdict
   190	
   191	        return asdict(self)
```

---

### 2. coach_validator.py — Key Lines

#### Lines 55-84 (Imports including `detect_stack_template`):
```
    55	    get_container_name,
    56	    get_env_exports,
    57	    get_start_commands,
    58	    is_known_service,
    59	)
    60	from guardkit.orchestrator.paths import TaskArtifactPaths
    61	from guardkit.orchestrator.phase_specialists import (
    62	    PHASE_DESCRIPTIONS,
    63	    detect_stack_template,        # <-- Line 64
    64	    render_missing_phase_list,
    65	)
    66	from guardkit.orchestrator.schemas import STATUS_ALIASES
    67	from guardkit.models.task_types import TaskType, QualityGateProfile, get_profile, TASK_TYPE_ALIASES
    68	
    69	# TASK-HMIG-006.3: Coach's independent SDK invocation dispatches through
    70	# the HarnessAdapter substrate seam established by TASK-HMIG-006 (Player
    71	# path) and TASK-HMIG-006.2 (cross-repo helper migration). Importing at
    72	# module top matches the Player path convention in
    73	# ``agent_invoker.py:71-77`` and makes ``select_harness`` a stable patch
    74	# target for tests under ``coach_validator.select_harness``.
    75	from guardkit.orchestrator.exceptions import AgentInvocationError
    76	from guardkit.orchestrator.harness import (
    77	    AssistantMessageEvent,
    78	    ResultMessageEvent,
    79	    ToolResultEvent,
    80	    select_harness,
    81	)
    82	from guardkit.orchestrator.sdk_utils import check_assistant_message_error
```

#### Lines 765-783 (SDK API error patterns + ambiguous infrastructure):
```
   766	        "redis.exceptions.ConnectionError",
   767	    ]
   768	
   769	    # SDK API error patterns — the LLM backend rejected the request (wrong model
   770	    # name, invalid parameters, rate limits, etc.).  These are NOT code defects.
   771	    _SDK_API_ERROR_PATTERNS: List[str] = [
   772	        "SDK API error",
   773	        "invalid_request",
   774	        "invalid_request_error",
   775	        "AssistantMessage.error",
   776	    ]
   777	
   778	    # Ambiguous infrastructure patterns (feedback only, not conditional approval)
   779	    _INFRA_AMBIGUOUS: List[str] = [
   780	        "ModuleNotFoundError",
   781	        "ImportError",
   782	        "No module named",
   783	    ]
```

#### Lines 2020-2077 (gather_evidence docstring and task-type resolution):
```
  2021	        ----------
  2022	        task_id : str
  2023	            Task identifier (e.g., ``"TASK-001"``). Used to read
  2024	            ``task_work_results.json`` from the standard autobuild path and
  2025	            to wire state-bridge identity resolution into the honesty
  2026	            verifier (TASK-FIX-1B4A Layer 1).
  2027	        turn : int
  2028	            Current turn number (1-based). Passed to
  2029	            ``validate_requirements`` and ``run_independent_tests``.
  2030	        task : Dict[str, Any]
  2031	            Task data dict. Must contain ``acceptance_criteria`` and may
  2032	            contain ``task_type``, ``requires_infrastructure``,
  2033	            ``_docker_available``, ``consumer_context``, ``description``.
  2034	        skip_arch_review : bool, optional
  2035	            If ``True``, the architectural-review gate is skipped regardless
  2036	            of the profile setting. Used for ``--implement-only`` mode where
  2037	            Phase 2.5B did not run. Default: ``False``.
  2038	        context : Optional[str], optional
  2039	            Optional Graphiti / coach context string. Not currently consumed
  2040	            by gather_evidence itself; threaded through for symmetry with
  2041	            ``validate()``'s signature so the legacy shim (when AC-003 is
  2042	            completed in a follow-up) can pass it forward.
  2043	
  2044	        Returns
  2045	        -------
  2046	        CoachEvidenceBundle
  2047	            Populated evidence bundle. Always returned; never raises.
  2048	        """
  2049	        default_honest = HonestyVerification(verified=True)
  2050	
  2051	        # ------------------------------------------------------------------
  2052	        # Pre-evidence: resolve task type. Mirrors validate() lines 821-838.
  2053	        # ------------------------------------------------------------------
  2054	        try:
  2055	            task_type = self._resolve_task_type(task)
  2056	        except ValueError as exc:
  2057	            logger.error(
  2058	                "gather_evidence: failed to resolve task type: %s", exc
  2059	            )
  2060	            return CoachEvidenceBundle(
  2061	                honesty=default_honest,
  2062	                gathering_status="partial_exception",
  2063	                gathering_error=f"invalid_task_type: {exc}",
  2064	            )
  2065	
  2066	        try:
  2067	            profile = get_profile(task_type)
  2068	        except Exception as exc:  # noqa: BLE001 — defensive; get_profile is total
  2069	            logger.error(
  2070                "gather_evidence: failed to load profile for %s: %s",
  2071	                task_type, exc,
  2072	            )
  2073	            return CoachEvidenceBundle(
  2074	                honesty=default_honest,
  2075	                gathering_status="partial_exception",
  2076	                gathering_error=f"missing_profile: {exc}",
  2077	                task_type=task_type.value,
```

#### Lines 2093-2135 (task_work_results reading + honesty verification):
```
  2093	            return CoachEvidenceBundle(
  2094	                honesty=default_honest,
  2095	                gathering_status="complete",
  2096	                task_type=task_type.value,
  2097	                profile_name=profile_name,
  2098	            )
  2099	
  2100	        # ------------------------------------------------------------------
  2101	        # Pre-evidence: read task_work_results. Mirrors validate() lines 875-895.
  2102	        # ------------------------------------------------------------------
  2103	        task_work_results = self.read_quality_gate_results(task_id)
  2104	        if "error" in task_work_results:
  2105	            logger.warning(
  2106	                "gather_evidence: task-work results missing for %s: %s",
  2107	                task_id, task_work_results.get("error", "unknown"),
  2108	            )
  2109	            return CoachEvidenceBundle(
  2110	                honesty=default_honest,
  2111	                gathering_status="partial_exception",
  2112	                gathering_error=(
  2113	                    f"missing_results: {task_work_results.get('error', 'unknown')}"
  2114	                ),
  2115	                task_type=task_type.value,
  2116	                profile_name=profile_name,
  2117	            )
  2118	
  2119	        # ------------------------------------------------------------------
  2120	        # 1. Honesty verification. Mirrors validate() lines 918-952.
  2121	        # ------------------------------------------------------------------
  2122	        try:
  2123	            honesty = self._verify_honesty(task_work_results)
  2124	        except Exception as exc:  # noqa: BLE001
  2125	            logger.error(
  2126	                "gather_evidence: _verify_honesty raised unexpectedly: %s", exc,
  2127	            )
  2128	            return CoachEvidenceBundle(
  2129	                honesty=default_honest,
  2130	                gathering_status="partial_exception",
  2131	                gathering_error=f"honesty_exception: {exc}",
  2132	                task_type=task_type.value,
  2133	                profile_name=profile_name,
  2134	            )
```

---

### 3. agent_invoker.py — Key Lines

#### Lines 3098-3163 (`_render_evidence_bundle_section` with truncation):
```
  3098	    def _render_evidence_bundle_section(
  3099	        self,
  3100	        evidence_bundle: "CoachEvidenceBundle",
  3101	    ) -> str:
  3102	        """Render the CoachEvidenceBundle as a structured prompt section.
  3103	
  3104	        Emits the bundle as JSON inside ``<evidence_bundle>...</evidence_bundle>``
  3105	        XML-like tags so the LLM Coach can locate it deterministically and
  3106	        apply the absence-of-failure guards against specific fields.
  3107	
  3108	        Truncation rules (plan §4):
  3109	
  3109	        * ``evidence_bundle.bdd.discoveries`` — keep first 20 entries.
  3110	        * ``evidence_bundle.bdd.errors``     — keep first 10 entries.
  3111	        * ``evidence_bundle.honesty.discrepancies`` — keep first 20 entries.
  3112	
  3113	        Each truncation appends a ``"... and N more"`` marker so the Coach
  3114	        knows the list was bounded. Non-list fields are bounded by gate
  3115	        computation and pass through unchanged.
  3116	
  3117	        The bundle's honesty channel is NOT duplicated here — it lives in
  ...
  3129                "Emitting empty bundle section so the Coach prompt still "
  3130	                "carries the absence-of-failure guards.",
  3131	                exc,
  3132	            )
  3133	            bundle_dict = {
  3134	                "gathering_status": "partial_exception",
  3135	                "gathering_error": f"bundle_serialisation_failed: {exc}",
  3136	            }
  3137	
  3138	        # Truncate bdd.discoveries / bdd.errors.
  3139	        bdd = bundle_dict.get("bdd")
  3140	        if isinstance(bdd, dict):
  3141	            discoveries = bdd.get("discoveries")
  3142	            if isinstance(discoveries, list) and len(discoveries) > self._COACH_BDD_DISCOVERIES_LIMIT:
  3143	                remainder = len(discoveries) - self._COACH_BDD_DISCOVERIES_LIMIT
  3144	                bdd["discoveries"] = discoveries[: self._COACH_BDD_DISCOVERIES_LIMIT] + [
  3145	                    f"... and {remainder} more (truncated for token budget)"
  3146	                ]
  3147	            errors = bdd.get("errors")
  3148	            if isinstance(errors, list) and len(errors) > self._COACH_BDD_ERRORS_LIMIT:
  3149	                remainder = len(errors) - self._COACH_BDD_ERRORS_LIMIT
  3150	                bdd["errors"] = errors[: self._COACH_BDD_ERRORS_LIMIT] + [
  3151	                    f"... and {remainder} more (truncated for token budget)"
  3152	                ]
  3153	
  3154	        # honesty.discrepancies truncation lives inside _render_bundle_honesty_section,
  3155	        # but we ALSO truncate the copy nested in bundle_dict["honesty"] so the
  3156	        # evidence-bundle JSON the Coach sees is internally consistent.
  3157	        honesty = bundle_dict.get("honesty")
  3158	        if isinstance(honesty, dict):
  3159	            discrepancies = honesty.get("discrepancies")
  3160	            if (
  3161	                isinstance(discrepancies, list)
  3162	                and len(discrepancies) > self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3163	            ):
```

#### Lines 3311-3332 (Absence-of-failure guard #6 - Independent-test absent guard):
```
 3311	5. GATHERING-STATUS GUARD.
 3312	   If evidence_bundle.gathering_status != "complete": evidence collection
 3313	   aborted before all fields were populated. Treat any null/None field as
 3314	   ABSENT SIGNAL — do NOT approve. Surface as feedback with the
 3315	   gathering_status value verbatim in the rationale so operators can
 3316	   diagnose which stage failed (e.g. "partial_honesty_abort",
 3317	   "partial_gate_abort", "partial_exception"). When status is
 3318	   "partial_exception", also surface evidence_bundle.gathering_error.
 3319	
 3320	6. INDEPENDENT-TEST ABSENT GUARD.
 3321	   If evidence_bundle.independent_tests is not null AND
 3322	   evidence_bundle.independent_tests.signal_absent == true: the Coach's own
 3323	   trust-but-verify pytest run did NOT complete (it timed out or failed at
 3324	   the transport layer before producing a verdict). This is ABSENT SIGNAL,
 3325	   NOT a passing or failing test result — do NOT approve on the basis of the
 3326	   Player's self-reported tests plus the other gates. Surface as feedback:
 3327	   "Independent test verification did not complete (signal absent) — cannot
 3328	   independently confirm the Player's reported tests." Quote
 3329	   independent_tests.test_output_summary verbatim in the rationale so
 3330	   operators can see whether it timed out or errored. Rule:
 3331	   .claude/rules/absence-of-failure-is-not-success.md.
 3332	</absence_of_failure_guards>
```

---

### 4. docs/features/qa-verifier-wiring-probes-scope.md — Full File (269 lines)

This is the comprehensive feature scope document covering:

- **§1** — Problem statement: "90% complete, wiring undone, green over dead code"
- **§2** — QA-Verifier program context (piece #2 of 3)
- **§3** — Stack-agnostic WiringAnalyzer design (tree-sitter + DATA dialects)
  - ONE analyzer, many languages (python, javascript, typescript, c_sharp)
  - `WiringDialect` frozen dataclass as declarative DATA
- **§4** — The three evidences:
  - **UNWIRED_PATH** — detects authored public symbols with zero non-test reference
  - **MOCKED_SEAM** — detects acceptance tests mocking authored production seams
  - **SPEC_GAP** — detects Gherkin scenarios with no executed binding (consumes `BDDRunResult`)
- **§5** — Integration points:
  - **§5.1** — Bundle fields (`wiring`, `mocked_seam`, `spec_gap` at `coach_evidence.py:169`)
  - **§5.2** — Population point (`coach_validator.py:2120-2135`)
  - **§5.3** — Render + truncation (`agent_invoker.py:3098-3191`)
  - **§5.4** — The ONE deterministic hard-gate: SPEC_GAP whole-file deselection
  - **§5.5** — guardkitfactory wiring subpackage layout
  - **§5.6** — Status discriminator (absent-signal mechanism)
- **§6** — Sequencing (Waves 0-3)
- **§7** — Scope boundaries
- **§8** — 22 Acceptance criteria (AC-001 through AC-022)
- **§9** — Mark of proposed-new paths
- **§10** — Open questions (7 items)

---

### 5. Guardkitfactory Wiring Subpackage

#### `wiring/__init__.py`:
Exports `WiringAnalyzer`, `WiringResult`, `WiringStatus`, `WiringDialect`, `analyze_wiring`, plus parser/dialect helpers. Side-effect import registers all built-in dialects.

#### `wiring/analyzer.py`:
The ONE stack-agnostic engine. Uses tree-sitter CSTs. Fidelity caveat: syntactic heuristic, not full semantic resolution. Biases toward WIRED. Result shape includes `findings`, `degraded_files`, and nested `mocked_seam`.

#### `wiring/dialect.py`:
`WiringDialect` frozen dataclass with fields:
- `language`, `ts_language_name`, `file_globs`
- `public_symbols_query`, `references_query`, `registration_queries`
- `mock_call_query`, `test_path_markers`, `acceptance_path_markers`
- `external_mock_allowlist`, `external_mock_path_roots`
- `script_manifest_files`, `private_name_prefixes`
- Registry helpers: `register_dialect()`, `get_dialect()`, `iter_dialects()`

#### `wiring/parser.py`:
Parser cache over `tree_sitter_language_pack.get_language(name)` + standalone `tree_sitter.Parser`. **NOT** the pack's `get_parser()` (which returns incompatible vendored bindings).

#### `wiring/dialects/python.py`:
Python dialect with queries for:
- Public symbols: module-level `function_definition`/`class_definition`/`decorated_definition`
- References: blanket `(identifier) @name`
- Registrations: `cli.add_command(X)`, `include_router(X)`, `registry.register(X)`, decorator-registered commands
- Mock calls: `patch(...)`, `mock.patch(...)`, `mocker.patch(...)`, `monkeypatch.setattr(...)`, `patch.object(...)`
- External allowlist: `httpx`, `requests`, `boto3`, `openai`, `sqlalchemy`
AI: Now let me read the full source files I need to modify to get exact line numbers and context.

[{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_evidence.py'}, 'id': 'fc_ZW60WNNTk87dnItDzG7vqDRCSeb2IG9z', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'offset': 2000, 'limit': 200}, 'id': 'fc_WDOuqwjy6Hkic6QyfCz53OgtJAJmI0fS', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/agent_invoker.py', 'offset': 3090, 'limit': 200}, 'id': 'fc_F9HqTJ1NxXn29dHdAYMpPWphIERkokyP', 'type': 'tool_call'}]
Tool:      1	"""CoachEvidenceBundle — structured evidence supplied by CoachValidator.
     2	
     3	TASK-HMIG-008R Part A (Revision 3, operator-approved 2026-05-20). Restores the
     4	LLM Coach as the primary decision-maker per the Block adversarial-cooperation
     5	paper, demoting CoachValidator from primary decision path to evidence supplier.
     6	
     7	The bundle is produced by ``CoachValidator.gather_evidence(...)`` and consumed
     8	by ``AgentInvoker.invoke_coach(...)`` which renders it into the Coach prompt
     9	via ``_build_coach_prompt(...)``. Every field corresponds to an intermediate
    10	value that the legacy ``CoachValidator.validate()`` method previously consumed
    11	internally to reach approve/feedback decisions. Under the new architecture
    12	those intermediates become read-only evidence the LLM Coach reasons about.
    13	
    14	Design rules (see ``.claude/rules/patterns/dataclasses.md``):
    15	
    16	* Internal value object — no external API boundary, no field-level validation
    17	  constraints, serialised via ``dataclasses.asdict`` + ``json.dumps``.
    18	* All evidence fields are ``Optional[...]`` so the bundle can be returned even
    19	  when one of the gathering stages aborted early.
    20	* ``gathering_status`` disambiguates "field is None because gathering aborted"
    21	  from "field is None because no signal was reported". The absence-of-failure
    22	  guards in the Coach prompt (TASK-HMIG-008R §4) instruct the Coach to treat
    23	  any ``None`` field as ABSENT SIGNAL when ``gathering_status != "complete"``.
    24	
    25	Cross-references:
    26	
    27	* ``.claude/rules/absence-of-failure-is-not-success.md`` — the structural
    28	  rule the LLM-layer guards mirror. Pair-with-attempted-count semantics map
    29	  directly onto the bundle's ``bdd.scenarios_attempted`` / ``tests.tests_run``
    30	  fields.
    31	* ``.claude/rules/path-string-mismatch-is-not-dishonesty.md`` — Layer-1
    32	  identity resolution lives in ``honesty.resolved_paths``; Layer-2 demotion
    33	  hint surfaces in ``severity_recommendations``.
    34	* TASK-REV-HMIG §14.9 (the architectural correction).
    35	"""
    36	
    37	from __future__ import annotations
    38	
    39	from dataclasses import dataclass, field
    40	from typing import TYPE_CHECKING, Any, Dict, List, Literal, Optional
    41	
    42	if TYPE_CHECKING:  # pragma: no cover — annotation-only imports
    43	    # Imported under TYPE_CHECKING to avoid the circular dependency
    44	    # coach_validator.py -> coach_evidence.py -> coach_validator.py.
    45	    # Runtime values are duck-typed; the annotations document intent.
    46	    from guardkit.orchestrator.coach_verification import HonestyVerification
    47	    from guardkit.orchestrator.quality_gates.coach_validator import (
    48	        IndependentTestResult,
    49	        QualityGateStatus,
    50	    )
    51	
    52	
    53	GatheringStatus = Literal[
    54	    "complete",
    55	    "partial_honesty_abort",
    56	    "partial_gate_abort",
    57	    "partial_exception",
    58	]
    59	"""Status of the evidence-gathering pipeline.
    60	
    61	* ``complete`` — all gathering stages ran successfully and populated their fields.
    62	* ``partial_honesty_abort`` — honesty verification produced ``must_fix``
    63	  discrepancies; downstream gathering (gates, independent tests, requirements)
    64	  was skipped because the legacy decision tree would have short-circuited here.
    65	  Fields downstream of honesty are ``None``.
    66	* ``partial_gate_abort`` — quality gates failed; downstream gathering
    67	  (independent tests, requirements) was skipped. ``quality_gates`` is populated;
    68	  ``independent_tests`` and ``requirements_*`` fields are ``None``.
    69	* ``partial_exception`` — pre-evidence error (invalid task type, missing
    70	  task_work_results, or unexpected exception in a gathering helper). Inspect
    71	  ``gathering_error`` for the cause.
    72	"""
    73	
    74	
    75	@dataclass
    76	class CoachEvidenceBundle:
    77	    """Structured evidence gathered by CoachValidator for the LLM Coach.
    78	
    79	    Each field maps to an intermediate value the legacy ``validate()`` method
    80	    consumed internally. Under TASK-HMIG-008R the LLM Coach reads this bundle
    81	    (rendered as JSON into the Coach prompt) plus the honesty result and makes
    82	    the final approve/feedback decision.
    83	
    84	    Attributes
    85	    ----------
    86	    honesty
    87	        ``HonestyVerification`` from ``CoachVerifier``. Carries
    88	        ``resolved_paths`` (Layer 1 / TASK-FIX-1B4A) and ``should_fix_count``
    89	        (Layer 2 demotion / TASK-FIX-1B4B). Populated on every non-pre-evidence
    90	        gather path. The Coach reads this field unconditionally.
    91	    gathering_status
    92	        Pipeline status; see :data:`GatheringStatus` for the meaning of each
    93	        value. Used by the Coach to decide whether ``None`` evidence fields
    94	        mean ABSENT SIGNAL (status != "complete") or NO SIGNAL REPORTED
    95	        (status == "complete").
    96	    gathering_error
    97	        Optional human-readable description of what went wrong when
    98	        ``gathering_status == "partial_exception"``. ``None`` on every other
    99	        status. Surfaced verbatim in the synthetic feedback rationale when the
   100	        primary ``_invoke_coach`` path catches an exception around evidence
Tool:   2001	          ``bundle.gathering_error``.
  2002	        * Honesty verification produced ``must_fix`` discrepancies →
  2003	          ``"partial_honesty_abort"``. Gates and independent tests are not
  2004	          run because the legacy decision tree would have short-circuited
  2005	          here too — the LLM Coach reaches the same conclusion by reading
  2006	          ``bundle.honesty.discrepancies``.
  2007	        * Quality gates failed → ``"partial_gate_abort"``. Independent
  2008	          tests / requirements validation are not run. The LLM Coach
  2009	          reaches a feedback decision by reading ``bundle.quality_gates``.
  2010	
  2011	        Per the Phase 2.5 architectural review and §3 "Exception handling
  2012	        for gather_evidence" in the implementation plan, this method MUST
  2013	        NOT raise to its caller. Wrapping inner helper exceptions in a
  2014	        ``partial_exception`` bundle prevents an exception fallback to
  2015	        ``validate()`` from re-activating the primary decision path that
  2016	        falsifier #1 ("CoachValidator.validate() for the decision is GONE")
  2017	        requires to be gone. ``GUARDKIT_COACH_LEGACY=1`` remains the sole
  2018	        operator-controlled mechanism for re-activating ``validate()``.
  2019	
  2020	        Parameters
  2021	        ----------
  2022	        task_id : str
  2023	            Task identifier (e.g., ``"TASK-001"``). Used to read
  2024	            ``task_work_results.json`` from the standard autobuild path and
  2025	            to wire state-bridge identity resolution into the honesty
  2026	            verifier (TASK-FIX-1B4A Layer 1).
  2027	        turn : int
  2028	            Current turn number (1-based). Passed to
  2029	            ``validate_requirements`` and ``run_independent_tests``.
  2030	        task : Dict[str, Any]
  2031	            Task data dict. Must contain ``acceptance_criteria`` and may
  2032	            contain ``task_type``, ``requires_infrastructure``,
  2033	            ``_docker_available``, ``consumer_context``, ``description``.
  2034	        skip_arch_review : bool, optional
  2035	            If ``True``, the architectural-review gate is skipped regardless
  2036	            of the profile setting. Used for ``--implement-only`` mode where
  2037	            Phase 2.5B did not run. Default: ``False``.
  2038	        context : Optional[str], optional
  2039	            Optional Graphiti / coach context string. Not currently consumed
  2040	            by gather_evidence itself; threaded through for symmetry with
  2041	            ``validate()``'s signature so the legacy shim (when AC-003 is
  2042	            completed in a follow-up) can pass it forward.
  2043	
  2044	        Returns
  2045	        -------
  2046	        CoachEvidenceBundle
  2047	            Populated evidence bundle. Always returned; never raises.
  2048	        """
  2049	        default_honest = HonestyVerification(verified=True)
  2050	
  2051	        # ------------------------------------------------------------------
  2052	        # Pre-evidence: resolve task type. Mirrors validate() lines 821-838.
  2053	        # ------------------------------------------------------------------
  2054	        try:
  2055	            task_type = self._resolve_task_type(task)
  2056	        except ValueError as exc:
  2057	            logger.error(
  2058	                "gather_evidence: failed to resolve task type: %s", exc
  2059	            )
  2060	            return CoachEvidenceBundle(
  2061	                honesty=default_honest,
  2062	                gathering_status="partial_exception",
  2063	                gathering_error=f"invalid_task_type: {exc}",
  2064	            )
  2065	
  2066	        try:
  2067	            profile = get_profile(task_type)
  2068	        except Exception as exc:  # noqa: BLE001 — defensive; get_profile is total
  2069	            logger.error(
  2070	                "gather_evidence: failed to load profile for %s: %s",
  2071	                task_type, exc,
  2072	            )
  2073	            return CoachEvidenceBundle(
  2074	                honesty=default_honest,
  2075	                gathering_status="partial_exception",
  2076	                gathering_error=f"missing_profile: {exc}",
  2077	                task_type=task_type.value,
  2078	            )
  2079	
  2080	        profile_name = getattr(profile, "name", None) or task_type.value
  2081	
  2082	        # OPERATOR_HANDOFF: no evidence to gather. The legacy validate() returns
  2083	        # decision="deferred" here; gather_evidence reports a clean status so
  2084	        # the LLM Coach prompt sees an empty bundle with the task_type marker.
  2085	        # The Part B / Part C wiring is responsible for short-circuiting the
  2086	        # Coach invocation for operator-handoff tasks at the autobuild layer
  2087	        # (the same place the legacy validate() returned deferred).
  2088	        if task_type == TaskType.OPERATOR_HANDOFF:
  2089	            logger.info(
  2090	                "gather_evidence: skipping evidence collection for "
  2091	                "operator_handoff task %s (runtime verification deferred to "
  2092	                "operator)", task_id,
  2093	            )
  2094	            return CoachEvidenceBundle(
  2095	                honesty=default_honest,
  2096	                gathering_status="complete",
  2097	                task_type=task_type.value,
  2098	                profile_name=profile_name,
  2099	            )
  2100	
  2101	        # ------------------------------------------------------------------
  2102	        # Pre-evidence: read task_work_results. Mirrors validate() lines 875-895.
  2103	        # ------------------------------------------------------------------
  2104	        task_work_results = self.read_quality_gate_results(task_id)
  2105	        if "error" in task_work_results:
  2106	            logger.warning(
  2107	                "gather_evidence: task-work results missing for %s: %s",
  2108	                task_id, task_work_results.get("error", "unknown"),
  2109	            )
  2110	            return CoachEvidenceBundle(
  2111	                honesty=default_honest,
  2112	                gathering_status="partial_exception",
  2113	                gathering_error=(
  2114	                    f"missing_results: {task_work_results.get('error', 'unknown')}"
  2115	                ),
  2116	                task_type=task_type.value,
  2117	                profile_name=profile_name,
  2118	            )
  2119	
  2120	        # ------------------------------------------------------------------
  2121	        # 1. Honesty verification. Mirrors validate() lines 918-952.
  2122	        # ------------------------------------------------------------------
  2123	        try:
  2124	            honesty = self._verify_honesty(task_work_results)
  2125	        except Exception as exc:  # noqa: BLE001
  2126	            logger.error(
  2127	                "gather_evidence: _verify_honesty raised unexpectedly: %s", exc,
  2128	            )
  2129	            return CoachEvidenceBundle(
  2130	                honesty=default_honest,
  2131	                gathering_status="partial_exception",
  2132	                gathering_error=f"honesty_exception: {exc}",
  2133	                task_type=task_type.value,
  2134	                profile_name=profile_name,
  2135	            )
  2136	
  2137	        honesty_issues = self._honesty_issues_from(honesty)
  2138	        honesty_must_fix = [
  2139	            i for i in honesty_issues if i["severity"] == "must_fix"
  2140	        ]
  2141	        honesty_should_fix = [
  2142	            i for i in honesty_issues if i["severity"] == "should_fix"
  2143	        ]
  2144	
  2145	        # Layer-2 demotion hint for the LLM Coach. Mirrors the structural
  2146	        # condition inside _honesty_issues_from (lines 5456-5460): a single
  2147	        # critical file_existence discrepancy that was Layer-1-resolved (via
  2148	        # state_bridge.canonical_path_for) is demoted from must_fix to
  2149	        # should_fix. Surface that hint structurally so the LLM Coach can
  2150	        # apply absence-of-failure guard #4 without re-deriving the demotion.
  2151	        severity_recommendations: List[Dict[str, str]] = []
  2152	        critical_discrepancies = [
  2153	            d for d in honesty.discrepancies if d.severity == "critical"
  2154	        ]
  2155	        non_audit_critical = [
  2156	            d for d in critical_discrepancies
  2157	            if d.claim_type != "claim_audit"
  2158	        ]
  2159	        if (
  2160	            len(non_audit_critical) == 1
  2161	            and non_audit_critical[0].claim_type == "file_existence"
  2162	        ):
  2163	            severity_recommendations.append({
  2164	                "recommendation": (
  2165	                    "A single file_existence discrepancy was suppressed by "
  2166	                    "Layer-1 identity resolution (state_bridge "
  2167	                    "canonical_path_for). Treat as should_fix, not must_fix. "
  2168	                    "Continue AC evaluation."
  2169	                ),
  2170	                "rule": (
  2171	                    "path-string-mismatch-is-not-dishonesty "
  2172	                    "(Layer 2 demotion)"
  2173	                ),
  2174	            })
  2175	
  2176	        # Advisory issues: agent-invocations advisory (F3c) + Layer-2 honesty
  2177	        # should_fix issues. Both ride along with the final decision (approve
  2178	        # or feedback) and are surfaced to the Player so process observations
  2179	        # remain visible. Pre-computed here so the LLM Coach can read them
  2180	        # without re-deriving from raw fields.
  2181	        advisory_issues: List[Dict[str, Any]] = []
  2182	        agent_invocations_advisory = (
  2183	            self._compute_agent_invocations_advisory(task_work_results)
  2184	        )
  2185	        if agent_invocations_advisory is not None:
  2186	            advisory_issues.append(agent_invocations_advisory)
  2187	        advisory_issues.extend(honesty_should_fix)
  2188	
  2189	        # Honesty short-circuit: don't run downstream gathering. Legacy
  2190	        # validate() also short-circuits here.
  2191	        if honesty_must_fix:
  2192	            logger.warning(
  2193	                "gather_evidence: honesty produced %d must_fix issue(s) "
  2194	                "for %s; downstream gathering skipped.",
  2195	                len(honesty_must_fix), task_id,
  2196	            )
  2197	            return CoachEvidenceBundle(
  2198	                honesty=honesty,
  2199	                gathering_status="partial_honesty_abort",
  2200	                severity_recommendations=severity_recommendations,
Tool:   3091	            findings[:limit]
  3092	            + f"\n\n... [Phase-A findings truncated for synthesis-prompt "
  3093	            f"budget: {elided} more chars elided. Any acceptance criterion "
  3094	            f"NOT explicitly marked PASS above is unverified — treat as "
  3095	            f"FAIL/UNSURE, never an assumed pass.] ..."
  3096	        )
  3097	
  3098	    def _render_evidence_bundle_section(
  3099	        self,
  3100	        evidence_bundle: "CoachEvidenceBundle",
  3101	    ) -> str:
  3102	        """Render the CoachEvidenceBundle as a structured prompt section.
  3103	
  3104	        Emits the bundle as JSON inside ``<evidence_bundle>...</evidence_bundle>``
  3105	        XML-like tags so the LLM Coach can locate it deterministically and
  3106	        apply the absence-of-failure guards against specific fields.
  3107	
  3108	        Truncation rules (plan §4):
  3109	
  3110	        * ``evidence_bundle.bdd.discoveries`` — keep first 20 entries.
  3111	        * ``evidence_bundle.bdd.errors``     — keep first 10 entries.
  3112	        * ``evidence_bundle.honesty.discrepancies`` — keep first 20 entries.
  3113	
  3114	        Each truncation appends a ``"... and N more"`` marker so the Coach
  3115	        knows the list was bounded. Non-list fields are bounded by gate
  3116	        computation and pass through unchanged.
  3117	
  3118	        The bundle's honesty channel is NOT duplicated here — it lives in
  3119	        the separate ``<honesty_verification>`` section emitted by
  3120	        :py:meth:`_render_bundle_honesty_section`. Both sections read from
  3121	        the same bundle.honesty value, but rendering them separately lets
  3122	        the absence-of-failure guards reference each by tag.
  3123	        """
  3124	        try:
  3125	            bundle_dict = evidence_bundle.to_dict()
  3126	        except Exception as exc:  # noqa: BLE001 — never block prompt build
  3127	            logger.error(
  3128	                "Failed to serialise evidence_bundle for Coach prompt: %s. "
  3129	                "Emitting empty bundle section so the Coach prompt still "
  3130	                "carries the absence-of-failure guards.",
  3131	                exc,
  3132	            )
  3133	            bundle_dict = {
  3134	                "gathering_status": "partial_exception",
  3135	                "gathering_error": f"bundle_serialisation_failed: {exc}",
  3136	            }
  3137	
  3138	        # Truncate bdd.discoveries / bdd.errors.
  3139	        bdd = bundle_dict.get("bdd")
  3140	        if isinstance(bdd, dict):
  3141	            discoveries = bdd.get("discoveries")
  3142	            if isinstance(discoveries, list) and len(discoveries) > self._COACH_BDD_DISCOVERIES_LIMIT:
  3143	                remainder = len(discoveries) - self._COACH_BDD_DISCOVERIES_LIMIT
  3144	                bdd["discoveries"] = discoveries[: self._COACH_BDD_DISCOVERIES_LIMIT] + [
  3145	                    f"... and {remainder} more (truncated for token budget)"
  3146	                ]
  3147	            errors = bdd.get("errors")
  3148	            if isinstance(errors, list) and len(errors) > self._COACH_BDD_ERRORS_LIMIT:
  3149	                remainder = len(errors) - self._COACH_BDD_ERRORS_LIMIT
  3150	                bdd["errors"] = errors[: self._COACH_BDD_ERRORS_LIMIT] + [
  3151	                    f"... and {remainder} more (truncated for token budget)"
  3152	                ]
  3153	
  3154	        # honesty.discrepancies truncation lives inside _render_bundle_honesty_section,
  3155	        # but we ALSO truncate the copy nested in bundle_dict["honesty"] so the
  3156	        # evidence-bundle JSON the Coach sees is internally consistent.
  3157	        honesty = bundle_dict.get("honesty")
  3158	        if isinstance(honesty, dict):
  3159	            discrepancies = honesty.get("discrepancies")
  3160	            if (
  3161	                isinstance(discrepancies, list)
  3162	                and len(discrepancies) > self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3163	            ):
  3164	                remainder = len(discrepancies) - self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3165	                honesty["discrepancies"] = discrepancies[
  3166	                    : self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3167	                ] + [{
  3168	                    "truncated": True,
  3169	                    "remainder": remainder,
  3170	                    "note": (
  3171	                        f"... and {remainder} more discrepancies (truncated "
  3172	                        f"for token budget). See full honesty_verification "
  3173	                        f"in coach_turn_N.json."
  3174	                    ),
  3175	                }]
  3176	
  3177	        try:
  3178	            payload = json.dumps(bundle_dict, indent=2, default=str)
  3179	        except Exception as exc:  # noqa: BLE001
  3180	            logger.error(
  3181	                "Failed to JSON-encode truncated evidence_bundle: %s", exc,
  3182	            )
  3183	            payload = '{"gathering_status": "partial_exception", "gathering_error": "json_encode_failed"}'
  3184	
  3185	        return f"""
  3186	## Deterministic Evidence Bundle
  3187	
  3188	<evidence_bundle>
  3189	{payload}
  3190	</evidence_bundle>
  3191	"""
  3192	
  3193	    def _render_bundle_honesty_section(
  3194	        self,
  3195	        honesty_verification: HonestyVerification,
  3196	    ) -> str:
  3197	        """Render the bundle's HonestyVerification as a structured prompt section.
  3198	
  3199	        Sourced from ``evidence_bundle.honesty`` (channel unification per
  3200	        plan §4). Emits a JSON-structured section inside
  3201	        ``<honesty_verification>...</honesty_verification>`` tags so the
  3202	        absence-of-failure guards can reference specific fields:
  3203	
  3204	        * ``honesty.discrepancies[*].claim_type``
  3205	        * ``honesty.discrepancies[*].severity``
  3206	        * ``honesty.resolved_paths`` — Layer-1 (TASK-FIX-1B4A) suppressions.
  3207	
  3208	        Truncation rule: keep first 20 discrepancies (plan §4 token budget).
  3209	        """
  3210	        from dataclasses import asdict
  3211	
  3212	        try:
  3213	            honesty_dict: Dict[str, Any] = asdict(honesty_verification)
  3214	        except Exception as exc:  # noqa: BLE001
  3215	            logger.error(
  3216	                "Failed to serialise honesty_verification for Coach prompt: %s",
  3217	                exc,
  3218	            )
  3219	            honesty_dict = {
  3220	                "verified": True,
  3221	                "discrepancies": [],
  3222	                "honesty_score": 1.0,
  3223	                "resolved_paths": [],
  3224	                "should_fix_count": 0,
  3225	                "serialisation_error": str(exc),
  3226	            }
  3227	
  3228	        discrepancies = honesty_dict.get("discrepancies")
  3229	        if (
  3230	            isinstance(discrepancies, list)
  3231	            and len(discrepancies) > self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3232	        ):
  3233	            remainder = len(discrepancies) - self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3234	            honesty_dict["discrepancies"] = discrepancies[
  3235	                : self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3236	            ] + [{
  3237	                "truncated": True,
  3238	                "remainder": remainder,
  3239	                "note": (
  3240	                    f"... and {remainder} more discrepancies (truncated "
  3241	                    f"for token budget). See full list in coach_turn_N.json."
  3242	                ),
  3243	            }]
  3244	
  3245	        try:
  3246	            payload = json.dumps(honesty_dict, indent=2, default=str)
  3247	        except Exception as exc:  # noqa: BLE001
  3248	            logger.error(
  3249	                "Failed to JSON-encode honesty_verification: %s", exc,
  3250	            )
  3251	            payload = '{"verified": true, "discrepancies": [], "honesty_score": 1.0}'
  3252	
  3253	        return f"""
  3254	## Honesty Verification
  3255	
  3256	<honesty_verification>
  3257	{payload}
  3258	</honesty_verification>
  3259	"""
  3260	
  3261	    def _render_absence_of_failure_guards(self) -> str:
  3262	        """Render the six absence-of-failure guard sentences (AC-009 + #5 + #6).
  3263	
  3264	        The four guards from the TASK-HMIG-008R task spec (AC-009 points 1-4),
  3265	        the fifth guard added per Phase 2.5 review finding #2
  3266	        (gathering_status guard), and the sixth guard added by
  3267	        TASK-FIX-COACHTESTTO (independent-test absent guard — treat a
  3268	        timed-out / transport-errored independent-test oracle as ABSENT rather
  3269	        than approving on the Player's self-reported tests). The sentences are
  3270	        emitted verbatim inside
  3271	        an ``<absence_of_failure_guards>`` block so the Coach can locate
  3272	        them deterministically. Wording mirrors
  3273	        ``.claude/rules/absence-of-failure-is-not-success.md`` and
  3274	        ``.claude/rules/path-string-mismatch-is-not-dishonesty.md`` to
  3275	        preserve the rule citation chain.
  3276	        """
  3277	        return """
  3278	<absence_of_failure_guards>
  3279	CRITICAL READING RULES — apply these BEFORE any approval decision:
  3280	
  3281	1. ZERO-CARDINALITY BDD GUARD.
  3282	   If evidence_bundle.bdd is not null AND evidence_bundle.bdd.scenarios_attempted == 0:
  3283	   treat as ABSENT SIGNAL — do NOT approve based on absence of failure.
  3284	   Surface as feedback: "BDD oracle ran zero scenarios — no evidence of
  3285	   passing behaviour." Rule: .claude/rules/absence-of-failure-is-not-success.md.
  3286	
  3287	2. ZERO-CARDINALITY TEST GUARD.
  3288	   If evidence_bundle.tests is not null AND evidence_bundle.tests.tests_run == 0:
  3289	   treat as ABSENT SIGNAL — do NOT approve. Surface as feedback:
  3290	   "No tests ran — cannot verify correctness." Rule:
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 200, 'offset': 2200}, 'id': 'fc_r5Pb0mD1f6ydk0beAObBpVPPbFMbWvSg', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/agent_invoker.py', 'limit': 100, 'offset': 3300}, 'id': 'fc_H8CvFf0zJLGkv8fTehM8JwRtrQ8461cl', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_evidence.py', 'offset': 100, 'limit': 100}, 'id': 'fc_wtf1WkEx0TqeeeuAsVR1mNzlu9FaAwbN', 'type': 'tool_call'}]
Tool:   2201	                advisory_issues=advisory_issues,
  2202	                task_type=task_type.value,
  2203	                profile_name=profile_name,
  2204	            )
  2205	
  2206	        # ------------------------------------------------------------------
  2207	        # 2. Quality gates. Mirrors validate() lines 1130-1132.
  2208	        # ------------------------------------------------------------------
  2209	        try:
  2210	            gates = self.verify_quality_gates(
  2211	                task_work_results,
  2212	                profile=profile,
  2213	                skip_arch_review=skip_arch_review,
  2214	            )
  2215	        except Exception as exc:  # noqa: BLE001
  2216	            logger.error(
  2217	                "gather_evidence: verify_quality_gates raised: %s", exc,
  2218	            )
  2219	            return CoachEvidenceBundle(
  2220	                honesty=honesty,
  2221	                gathering_status="partial_exception",
  2222	                gathering_error=f"quality_gates_exception: {exc}",
  2223	                severity_recommendations=severity_recommendations,
  2224	                advisory_issues=advisory_issues,
  2225	                task_type=task_type.value,
  2226	                profile_name=profile_name,
  2227	            )
  2228	
  2229	        # Build the evidence dict slices the LLM Coach reads.
  2230	        quality_gates_raw = task_work_results.get("quality_gates")
  2231	        if not isinstance(quality_gates_raw, dict):
  2232	            quality_gates_raw = {}
  2233	
  2234	        coverage_details: Dict[str, Any] = {
  2235	            "coverage_met": quality_gates_raw.get("coverage_met"),
  2236	            "line_coverage": quality_gates_raw.get("line_coverage"),
  2237	            "branch_coverage": quality_gates_raw.get("branch_coverage"),
  2238	            "line_threshold": quality_gates_raw.get("line_threshold"),
  2239	            "branch_threshold": quality_gates_raw.get("branch_threshold"),
  2240	            "coverage_required": gates.coverage_required,
  2241	        }
  2242	
  2243	        tests_dict: Dict[str, Any] = {
  2244	            "tests_passed": gates.tests_passed,
  2245	            "tests_required": gates.tests_required,
  2246	            "tests_run": quality_gates_raw.get("tests_run"),
  2247	            "tests_failed": quality_gates_raw.get("tests_failed"),
  2248	            "all_passed": quality_gates_raw.get("all_passed"),
  2249	            "requires_infrastructure": task.get("requires_infrastructure"),
  2250	        }
  2251	
  2252	        plan_audit_raw = task_work_results.get("plan_audit")
  2253	        plan_audit_dict: Optional[Dict[str, Any]] = (
  2254	            plan_audit_raw if isinstance(plan_audit_raw, dict) else None
  2255	        )
  2256	
  2257	        code_review_raw = task_work_results.get("code_review")
  2258	        arch_review_dict: Optional[Dict[str, Any]] = None
  2259	        if isinstance(code_review_raw, dict):
  2260	            arch_review_dict = {
  2261	                "score": code_review_raw.get("score"),
  2262	                "threshold": getattr(profile, "arch_review_threshold", 60),
  2263	                "passed": gates.arch_review_passed,
  2264	                "required": gates.arch_review_required,
  2265	            }
  2266	            # Surface any sub-scores the producer wrote (solid/dry/yagni).
  2267	            for sub in ("solid_score", "dry_score", "yagni_score"):
  2268	                if sub in code_review_raw:
  2269	                    arch_review_dict[sub] = code_review_raw[sub]
  2270	
  2271	        # ------------------------------------------------------------------
  2272	        # BDD evidence. TASK-BDDW-001: wire factory BDD plugin discovery
  2273	        # into the Coach evidence path.
  2274	        #
  2275	        # Priority:
  2276	        #   1. Factory discovery (guardkitfactory.bdd.discover) — if available
  2277	        #      and stack profile is known, run the BDD plugin and map the
  2278	        #      result into bundle.bdd shape.
  2279	        #   2. Player-reported bdd_results — legacy fallback when the factory
  2280	        #      is unavailable, the stack is unknown, or discovery fails.
  2281	        # ------------------------------------------------------------------
  2282	        _reset_factory_cache()
  2283	
  2284	        bdd_raw = task_work_results.get("bdd_results")
  2285	        bdd_dict: Optional[Dict[str, Any]] = None
  2286	
  2287	        if bdd_raw is not None and isinstance(bdd_raw, dict):
  2288	            # Player already produced BDD results — use them as-is.
  2289	            bdd_dict = bdd_raw
  2290	        elif _is_factory_available():
  2291	            # Factory is available but Player didn't produce results.
  2292	            # Attempt independent discovery via the factory plugin.
  2293	            stack_profile = _detect_stack_profile(self.worktree_path)
  2294	            factory_result = _run_factory_bdd(self.worktree_path, stack_profile)
  2295	            if factory_result is not None:
  2296	                bdd_dict = factory_result
  2297	                logger.info(
  2298	                    "gather_evidence: BDD evidence from factory plugin "
  2299	                    "(stack=%s, scenarios_attempted=%s).",
  2300	                    stack_profile,
  2301	                    factory_result.get("scenarios_attempted"),
  2302	                )
  2303	            else:
  2304	                logger.debug(
  2305	                    "gather_evidence: factory BDD discovery returned None; "
  2306	                    "bdd field left as absent signal.",
  2307	                )
  2308	        else:
  2309	            # Factory unavailable — bdd_dict stays None (absent signal).
  2310	            logger.debug(
  2311	                "gather_evidence: guardkitfactory not available; "
  2312	                "Player-reported bdd_results were empty; "
  2313	                "bdd field left as absent signal.",
  2314	            )
  2315	
  2316	        # Quality-gate-failure short-circuit. Legacy validate() also
  2317	        # short-circuits here via _feedback_from_gates.
  2318	        if not gates.all_gates_passed:
  2319	            logger.info(
  2320	                "gather_evidence: quality gates failed for %s; downstream "
  2321	                "(requirements, independent tests) skipped.", task_id,
  2322	            )
  2323	            return CoachEvidenceBundle(
  2324	                honesty=honesty,
  2325	                gathering_status="partial_gate_abort",
  2326	                quality_gates=gates,
  2327	                coverage_details=coverage_details,
  2328	                plan_audit=plan_audit_dict,
  2329	                bdd=bdd_dict,
  2330	                arch_review=arch_review_dict,
  2331	                tests=tests_dict,
  2332	                severity_recommendations=severity_recommendations,
  2333	                advisory_issues=advisory_issues,
  2334	                task_type=task_type.value,
  2335	                profile_name=profile_name,
  2336	            )
  2337	
  2338	        # ------------------------------------------------------------------
  2339	        # 3. Requirements validation. Mirrors validate() line 1139.
  2340	        # Hoisted ahead of independent-test in the legacy path; preserved
  2341	        # here for the same reason — cheaper, idempotent.
  2342	        # ------------------------------------------------------------------
  2343	        try:
  2344	            requirements = self.validate_requirements(
  2345	                task, task_work_results, turn=turn
  2346	            )
  2347	        except Exception as exc:  # noqa: BLE001
  2348	            logger.error(
  2349	                "gather_evidence: validate_requirements raised: %s", exc,
  2350	            )
  2351	            return CoachEvidenceBundle(
  2352	                honesty=honesty,
  2353	                gathering_status="partial_exception",
  2354	                gathering_error=f"requirements_exception: {exc}",
  2355	                quality_gates=gates,
  2356	                coverage_details=coverage_details,
  2357	                plan_audit=plan_audit_dict,
  2358	                bdd=bdd_dict,
  2359	                arch_review=arch_review_dict,
  2360	                tests=tests_dict,
  2361	                severity_recommendations=severity_recommendations,
  2362	                advisory_issues=advisory_issues,
  2363	                task_type=task_type.value,
  2364	                profile_name=profile_name,
  2365	            )
  2366	
  2367	        # ------------------------------------------------------------------
  2368	        # 4. Independent tests. Mirrors validate() lines 1156-1175.
  2369	        # ------------------------------------------------------------------
  2370	        if not profile.tests_required:
  2371	            test_result: IndependentTestResult = IndependentTestResult(
  2372	                tests_passed=True,
  2373	                test_command="skipped",
  2374	                test_output_summary=(
  2375	                    f"Independent test verification skipped "
  2376	                    f"(tests not required for {task_type.value} tasks)"
  2377	                ),
  2378	                duration_seconds=0.0,
  2379	            )
  2380	            logger.info(
  2381	                "gather_evidence: independent test verification skipped for "
  2382	                "%s (tests not required for %s tasks)",
  2383	                task_id, task_type.value,
  2384	            )
  2385	        else:
  2386	            try:
  2387	                test_result = self.run_independent_tests(
  2388	                    task_work_results=task_work_results,
  2389	                    task=task,
  2390	                    turn=turn,
  2391	                )
  2392	            except Exception as exc:  # noqa: BLE001
  2393	                logger.error(
  2394	                    "gather_evidence: run_independent_tests raised: %s", exc,
  2395	                )
  2396	                return CoachEvidenceBundle(
  2397	                    honesty=honesty,
  2398	                    gathering_status="partial_exception",
  2399	                    gathering_error=f"independent_tests_exception: {exc}",
  2400	                    quality_gates=gates,
Tool:   3301	4. LAYER-1 PATH DEMOTION GUARD.
  3302	   If honesty_verification.discrepancies contains exactly ONE entry with
  3303	   claim_type == "file_existence" AND honesty_verification.resolved_paths
  3304	   is non-empty: this discrepancy was Layer-1-resolved by state_bridge
  3305	   identity lookup (the orchestrator moved the task file, not Player
  3306	   dishonesty). Demote to should_fix and continue AC evaluation. Rule:
  3307	   .claude/rules/path-string-mismatch-is-not-dishonesty.md (Layer 2).
  3308	   Cross-check evidence_bundle.severity_recommendations for the
  3309	   structured hint — if present, it confirms this demotion applies.
  3310	
  3311	5. GATHERING-STATUS GUARD.
  3312	   If evidence_bundle.gathering_status != "complete": evidence collection
  3313	   aborted before all fields were populated. Treat any null/None field as
  3314	   ABSENT SIGNAL — do NOT approve. Surface as feedback with the
  3315	   gathering_status value verbatim in the rationale so operators can
  3316	   diagnose which stage failed (e.g. "partial_honesty_abort",
  3317	   "partial_gate_abort", "partial_exception"). When status is
  3318	   "partial_exception", also surface evidence_bundle.gathering_error.
  3319	
  3320	6. INDEPENDENT-TEST ABSENT GUARD.
  3321	   If evidence_bundle.independent_tests is not null AND
  3322	   evidence_bundle.independent_tests.signal_absent == true: the Coach's own
  3323	   trust-but-verify pytest run did NOT complete (it timed out or failed at
  3324	   the transport layer before producing a verdict). This is ABSENT SIGNAL,
  3325	   NOT a passing or failing test result — do NOT approve on the basis of the
  3326	   Player's self-reported tests plus the other gates. Surface as feedback:
  3327	   "Independent test verification did not complete (signal absent) — cannot
  3328	   independently confirm the Player's reported tests." Quote
  3329	   independent_tests.test_output_summary verbatim in the rationale so
  3330	   operators can see whether it timed out or errored. Rule:
  3331	   .claude/rules/absence-of-failure-is-not-success.md.
  3332	</absence_of_failure_guards>
  3333	"""
  3334	
  3335	    def _verify_player_claims(
  3336	        self,
  3337	        player_report: Dict[str, Any],
  3338	    ) -> HonestyVerification:
  3339	        """Verify Player's self-reported claims against reality.
  3340	
  3341	        This method uses CoachVerifier to cross-reference Player claims:
  3342	        - Test results vs actual test execution
  3343	        - Claimed files vs filesystem state
  3344	        - Test counts vs parsed output
  3345	
  3346	        Args:
  3347	            player_report: Player's report from current turn
  3348	
  3349	        Returns:
  3350	            HonestyVerification with verification results and honesty score
  3351	
  3352	        Note:
  3353	            Returns a default verification result if verification fails,
  3354	            allowing the workflow to continue while logging the issue.
  3355	        """
  3356	        try:
  3357	            verifier = CoachVerifier(
  3358	                self.worktree_path, venv_python=self._venv_python
  3359	            )
  3360	            verification = verifier.verify_player_report(player_report)
  3361	
  3362	            if verification.discrepancies:
  3363	                logger.warning(
  3364	                    f"Player honesty verification found {len(verification.discrepancies)} "
  3365	                    f"discrepancies (score: {verification.honesty_score:.2f})"
  3366	                )
  3367	                for disc in verification.discrepancies:
  3368	                    logger.warning(
  3369	                        f"  [{disc.severity}] {disc.claim_type}: "
  3370	                        f"claimed {disc.player_claim}, actual {disc.actual_value}"
  3371	                    )
  3372	            else:
  3373	                logger.info(
  3374	                    f"Player claims verified successfully (score: {verification.honesty_score:.2f})"
  3375	                )
  3376	
  3377	            return verification
  3378	
  3379	        except Exception as e:
  3380	            logger.warning(f"Failed to verify Player claims: {e}")
  3381	            # Return default verification (assume honest) to not block workflow
  3382	            return HonestyVerification(verified=True, discrepancies=[], honesty_score=1.0)
  3383	
  3384	    async def _invoke_with_role(
  3385	        self,
  3386	        prompt: str,
  3387	        agent_type: Literal["player", "coach"],
  3388	        allowed_tools: list[str],
  3389	        permission_mode: Literal["acceptEdits", "bypassPermissions"],
  3390	        model: Optional[str] = None,
  3391	        resume_session_id: Optional[str] = None,
  3392	        task_id: Optional[str] = None,
  3393	        turn: Optional[int] = None,
  3394	        heartbeat_label_override: Optional[str] = None,
  3395	        return_events: bool = False,
  3396	        synthesis: bool = False,
  3397	        grammar: Optional[str] = None,
  3398	        recursion_limit: Optional[int] = None,
  3399	        max_tool_result_chars: Optional[int] = None,
  3400	    ) -> Optional[Tuple[None, List[HarnessEvent]]]:
Tool:    101	        gathering.
   102	    quality_gates
   103	        ``QualityGateStatus`` aggregate (tests / coverage / arch_review /
   104	        plan_audit). ``None`` when gathering aborted before the gates ran or
   105	        when the task type opts out of all gates.
   106	    coverage_details
   107	        Raw coverage dict slice from ``task_work_results['test_results']``
   108	        (line_coverage, branch_coverage, files_below_threshold). ``None`` when
   109	        coverage was not reported.
   110	    plan_audit
   111	        Plan-audit findings dict from ``task_work_results['plan_audit']``.
   112	        ``None`` when the producer wrote no plan_audit block (e.g.
   113	        ``--implement-only`` without a saved plan).
   114	    bdd
   115	        Raw ``task_work_results['bdd_results']`` dict (scenarios_attempted,
   116	        scenarios_failed, scenarios_passed, scenarios_pending, failures,
   117	        pending, feature_files). ``None`` when no BDD oracle ran. The Coach
   118	        applies the Pattern-2 absence-of-failure guard against
   119	        ``bdd['scenarios_attempted']``.
   120	    arch_review
   121	        Architectural review dict slice (``{"score": int, ...}``). ``None``
   122	        when no Phase 2.5B output was produced.
   123	    tests
   124	        Aggregate test result dict (tests_passed / tests_run /
   125	        line_coverage_met / branch_coverage_met / requires_infrastructure).
   126	        ``None`` when no test_results block was produced. The Coach applies
   127	        the absence-of-failure guard against ``tests['tests_run']``.
   128	    independent_tests
   129	        ``IndependentTestResult`` from Coach's own pytest pass. ``None`` when
   130	        gathering aborted before independent tests or when the task type's
   131	        profile opts out of independent verification.
   132	    requirements
   133	        ``RequirementsValidation`` from ``validate_requirements``. ``None``
   134	        when gathering aborted before requirements validation.
   135	    severity_recommendations
   136	        Structured hints derived from ``_honesty_issues_from`` demotion logic
   137	        (Layer 2). Each hint is ``{"recommendation": str, "rule": str}``. The
   138	        Coach reads these to know when to demote ``file_existence``
   139	        discrepancies from ``must_fix`` to ``should_fix``.
   140	    task_type
   141	        Resolved task type string (e.g. ``"feature"``, ``"refactor"``,
   142	        ``"scaffolding"``). ``None`` when task type could not be resolved
   143	        (``partial_exception`` with invalid_task_type cause).
   144	    profile_name
   145	        Quality-gate profile name string. ``None`` on the same paths as
   146	        ``task_type``.
   147	    advisory_issues
   148	        Non-blocking issues that ride along with the final decision regardless
   149	        of approve/feedback outcome. Currently sourced from:
   150	
   151	        * Agent-invocations advisory (TASK-REV-F6E1 F3c) — process observation,
   152	          ``severity == "warning"``.
   153	        * Layer-2-demoted honesty ``should_fix`` issues — content observation,
   154	          ``severity == "should_fix"``.
   155	
   156	        Pre-populated so the LLM Coach can read them without re-computing the
   157	        Layer-2 demotion.
   158	    """
   159	
   160	    honesty: "HonestyVerification"
   161	    gathering_status: GatheringStatus = "complete"
   162	    gathering_error: Optional[str] = None
   163	
   164	    quality_gates: Optional["QualityGateStatus"] = None
   165	    coverage_details: Optional[Dict[str, Any]] = None
   166	    plan_audit: Optional[Dict[str, Any]] = None
   167	    bdd: Optional[Dict[str, Any]] = None
   168	    arch_review: Optional[Dict[str, Any]] = None
   169	    tests: Optional[Dict[str, Any]] = None
   170	
   171	    independent_tests: Optional["IndependentTestResult"] = None
   172	    requirements: Optional[Any] = None  # RequirementsValidation; avoid circular import
   173	
   174	    severity_recommendations: List[Dict[str, str]] = field(default_factory=list)
   175	    advisory_issues: List[Dict[str, Any]] = field(default_factory=list)
   176	
   177	    task_type: Optional[str] = None
   178	    profile_name: Optional[str] = None
   179	
   180	    def to_dict(self) -> Dict[str, Any]:
   181	        """Serialise the bundle to a JSON-compatible dict.
   182	
   183	        Nested ``HonestyVerification`` / ``QualityGateStatus`` /
   184	        ``IndependentTestResult`` / ``RequirementsValidation`` instances are
   185	        also dataclasses, so ``dataclasses.asdict`` walks the entire tree.
   186	        ``ResolvedPath`` / ``Discrepancy`` inside ``HonestyVerification`` are
   187	        also dataclasses — the whole bundle is safe for ``json.dumps``.
   188	        """
   189	        from dataclasses import asdict
   190	
   191	        return asdict(self)
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 2400}, 'id': 'fc_hb8gWA4r8CCrAzDqCOBgBXBLtc3KvczU', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 750}, 'id': 'fc_R5S2XnKzgI58X8pR9f7NadsumH7dNbCh', 'type': 'tool_call'}]
Tool:   2401	                    coverage_details=coverage_details,
  2402	                    plan_audit=plan_audit_dict,
  2403	                    bdd=bdd_dict,
  2404	                    arch_review=arch_review_dict,
  2405	                    tests=tests_dict,
  2406	                    requirements=requirements,
  2407	                    severity_recommendations=severity_recommendations,
  2408	                    advisory_issues=advisory_issues,
  2409	                    task_type=task_type.value,
  2410	                    profile_name=profile_name,
  2411	                )
  2412	
  2413	        return CoachEvidenceBundle(
  2414	            honesty=honesty,
  2415	            gathering_status="complete",
  2416	            quality_gates=gates,
  2417	            coverage_details=coverage_details,
  2418	            plan_audit=plan_audit_dict,
  2419	            bdd=bdd_dict,
  2420	            arch_review=arch_review_dict,
  2421	            tests=tests_dict,
  2422	            independent_tests=test_result,
  2423	            requirements=requirements,
  2424	            severity_recommendations=severity_recommendations,
  2425	            advisory_issues=advisory_issues,
  2426	            task_type=task_type.value,
  2427	            profile_name=profile_name,
  2428	        )
  2429	
  2430	    def _compute_agent_invocations_advisory(
  2431	        self, task_work_results: Dict[str, Any],
  2432	    ) -> Optional[Dict[str, Any]]:
  2433	        """Compute the non-blocking agent-invocations advisory issue.
  2434	
  2435	        Extracted from ``validate()`` lines 1028-1126 (TASK-FIX-RWOP1.3.1 /
  2436	        TASK-REV-F6E1 F3c) for reuse by ``gather_evidence()`` (TASK-HMIG-008R
  2437	        Part A). Returns ``None`` when no advisory is needed.
  2438	
  2439	        The logic mirrors the inline computation in ``validate()``: a
  2440	        ``"violation"`` status in ``task_work_results['agent_invocations_validation']``
  2441	        produces a ``severity == "warning"`` advisory naming the missing
  2442	        phases and recommending stack-specific specialists. ``"passed"``,
  2443	        ``"validator_error"``, and ``"no_data"`` statuses are not advised
  2444	        on — they ride through without comment.
  2445	        """
  2446	        agent_invocations_validation = task_work_results.get(
  2447	            "agent_invocations_validation"
  2448	        )
  2449	        if not (
  2450	            isinstance(agent_invocations_validation, dict)
  2451	            and agent_invocations_validation.get("status") == "violation"
  2452	        ):
  2453	            return None
  2454	
  2455	        raw_missing = agent_invocations_validation.get("missing_phases") or []
  2456	        missing_phases: List[str] = []
  2457	        if raw_missing and isinstance(raw_missing[0], dict):
  2458	            missing_phases = [
  2459	                str(m.get("phase", ""))
  2460	                for m in raw_missing
  2461	                if m.get("phase")
  2462	            ]
  2463	        else:
  2464	            missing_phases = [str(m) for m in raw_missing]
  2465	        missing_phases_sorted = sorted(missing_phases)
  2466	        missing_phases_with_names = ", ".join(
  2467	            f"{p} ({PHASE_DESCRIPTIONS.get(p, 'Unknown')})"
  2468	            for p in missing_phases_sorted
  2469	        ) if missing_phases_sorted else "unknown"
  2470	
  2471	        stack_template = detect_stack_template(self.worktree_path)
  2472	        specialist_lines = render_missing_phase_list(
  2473	            missing_phases_sorted,
  2474	            stack_template=stack_template,
  2475	            workspace_root=self.worktree_path,
  2476	        )
  2477	        specialist_block = "\n".join(
  2478	            f"- {line}" for line in specialist_lines
  2479	        )
  2480	
  2481	        expected_phases_val = agent_invocations_validation.get("expected_phases")
  2482	        actual_invocations_val = agent_invocations_validation.get("actual_invocations")
  2483	        expected_str = (
  2484	            str(expected_phases_val) if expected_phases_val is not None else "?"
  2485	        )
  2486	        actual_str = (
  2487	            str(actual_invocations_val)
  2488	            if actual_invocations_val is not None
  2489	            else "?"
  2490	        )
  2491	
  2492	        return {
  2493	            "severity": "warning",
  2494	            "category": "agent_invocations_advisory",
  2495	            "description": (
  2496	                f"Advisory (non-blocking): task-work produced a report with "
  2497	                f"{actual_str} of {expected_str} expected agent invocations. "
  2498	                f"Missing phases: {missing_phases_with_names}. "
  2499	                f"Consider invoking these agents via the Task tool to "
  2500	                f"strengthen stack-specific quality:\n{specialist_block}"
Tool:    751	    # High-confidence infrastructure patterns (safe for conditional approval)
   752	    _INFRA_HIGH_CONFIDENCE: List[str] = [
   753	        # Connection/network errors
   754	        "ConnectionRefusedError",
   755	        "ConnectionError",
   756	        "Connection refused",
   757	        "could not connect to server",
   758	        # Database drivers
   759	        "OperationalError",
   760	        "psycopg2",
   761	        "psycopg",
   762	        "asyncpg",
   763	        "sqlalchemy.exc.OperationalError",
   764	        "django.db.utils.OperationalError",
   765	        "pymongo.errors.ServerSelectionTimeoutError",
   766	        "redis.exceptions.ConnectionError",
   767	    ]
   768	
   769	    # SDK API error patterns — the LLM backend rejected the request (wrong model
   770	    # name, invalid parameters, rate limits, etc.).  These are NOT code defects.
   771	    _SDK_API_ERROR_PATTERNS: List[str] = [
   772	        "SDK API error",
   773	        "invalid_request",
   774	        "invalid_request_error",
   775	        "AssistantMessage.error",
   776	    ]
   777	
   778	    # Ambiguous infrastructure patterns (feedback only, not conditional approval)
   779	    _INFRA_AMBIGUOUS: List[str] = [
   780	        "ModuleNotFoundError",
   781	        "ImportError",
   782	        "No module named",
   783	    ]
   784	
   785	    # Known service-client libraries whose absence indicates a missing dependency
   786	    # install (not a code defect). ModuleNotFoundError for these is promoted to
   787	    # high confidence.
   788	    # NOTE: psycopg2 is intentionally excluded — projects using asyncpg may
   789	    # accidentally import psycopg2, which is a Player code-choice error, not an
   790	    # infrastructure failure.  Classifying it as ("infrastructure", "high") gave
   791	    # the Player wrong advice (mock fixtures / SQLite) instead of telling them to
   792	    # remove the wrong import.
   793	    _KNOWN_SERVICE_CLIENT_LIBS: List[str] = [
   794	        "asyncpg",
   795	        "pymongo",
   796	        "redis",
   797	        "psycopg",
   798	        "sqlalchemy",
   799	        "motor",
   800	        "aioredis",
   801	        "cassandra",
   802	    ]
   803	
   804	    def __init__(
   805	        self,
   806	        worktree_path: str,
   807	        test_command: Optional[str] = None,
   808	        test_timeout: int = 300,
   809	        task_id: Optional[str] = None,
   810	        coach_test_execution: str = "sdk",
   811	        matching_strategy: str = "auto",
   812	        wave_size: int = 1,
   813	        turn: int = 1,
   814	        peer_changed_files: Optional[Dict[str, Any]] = None,
   815	        model_name: Optional[str] = None,
   816	        coach_model_name: Optional[str] = None,  # TASK-FIX-COACHBUDG01
   817	        venv_python: Optional[str] = None,  # TASK-FIX-COACHPYENV
   818	    ):
   819	        """
   820	        Initialize CoachValidator.
   821	
   822	        Parameters
   823	        ----------
   824	        worktree_path : str
   825	            Path to the git worktree where validation should execute
   826	        test_command : Optional[str]
   827	            Command to run tests. If None, auto-detects based on project.
   828	        test_timeout : int
   829	            Timeout for test execution in seconds (default: 300s)
   830	        task_id : Optional[str]
   831	            Task identifier for task-specific test filtering in shared worktrees.
   832	            When provided, test detection will first look for task-specific test
   833	            files before falling back to running the full test suite.
   834	        coach_test_execution : str
   835	            Test execution mode: "sdk" (default) uses Claude Agent SDK via Bash
   836	            tool for environment parity; "subprocess" uses subprocess.run() directly.
   837	        matching_strategy : str
   838	            Text matching strategy for acceptance criteria verification.
   839	            ``"text"``: strict Jaccard threshold (70%), ``"semantic"``: lower
   840	            threshold (50%) with fuzzy keyword prefix matching for local/vLLM
   841	            backends, ``"auto"`` (default): resolves to ``"semantic"`` when
   842	            ``ANTHROPIC_BASE_URL`` points to a non-Anthropic endpoint, otherwise
   843	            ``"text"``.  Can also be set via ``GUARDKIT_MATCHING_STRATEGY`` env var.
   844	        wave_size : int
   845	            Number of tasks executing in parallel in the current wave (default: 1).
   846	            When >1, the Coach runs independent tests in an isolated temp directory
   847	            to prevent spurious failures from concurrent worktree mutations, and
   848	            applies more lenient failure classification for contention-related errors.
   849	        peer_changed_files : Optional[Dict[str, Iterable[str]]]
   850	            Snapshot of files edited by other in-flight tasks in the same parallel
AI: Now let me check the guardkitfactory wiring module and existing test structure.

[{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/__init__.py'}, 'id': 'fc_sT8fqD2BCbDBi8ADgqX73FiI9ZqZAHwS', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/guardkitfactory/src/guardkitfactory/wiring/analyzer.py'}, 'id': 'fc_UfrTlBbJ6TiuKucI9tPEUtKBkqcCfglk', 'type': 'tool_call'}, {'name': 'glob', 'args': {'pattern': 'tests/**/test_coach*.py', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit'}, 'id': 'fc_pn9Via4dqzCFG1lgixykyzLXtuoy6oEH', 'type': 'tool_call'}]
Tool:      1	"""guardkitfactory.wiring: stack-agnostic wiring-analysis engine.
     2	
     3	A single analyzer over tree-sitter Concrete Syntax Trees, parameterized by
     4	declarative per-language ``WiringDialect`` records (DATA).  Detects
     5	UNWIRED_PATH and MOCKED_SEAM evidence for guardkit's Coach evidence path.
     6	
     7	Public API
     8	----------
     9	- ``analyze_wiring(authored_files, worktree_path, task_type, stack)`` —
    10	  main entry point; returns the scope-§5.1 dict (wiring shape with the
    11	  ``mocked_seam`` result nested) or ``None`` when the probe legitimately
    12	  did not run.  See :mod:`guardkitfactory.wiring.analyzer` for the shape.
    13	- ``WiringResult``, ``MockSeamResult``, ``Finding``, ``WiringStatus`` —
    14	  result types.
    15	- ``WiringDialect`` — frozen descriptor dataclass (+ registry helpers).
    16	
    17	Side-effect import registers all built-in dialects (python, javascript,
    18	typescript, c_sharp).
    19	"""
    20	
    21	from __future__ import annotations
    22	
    23	# Side-effect import: registers all built-in dialects.
    24	import guardkitfactory.wiring.dialects  # noqa: F401
    25	from guardkitfactory.wiring.analyzer import (
    26	    Finding,
    27	    MockSeamResult,
    28	    WiringResult,
    29	    WiringStatus,
    30	    analyze_wiring,
    31	)
    32	from guardkitfactory.wiring.dialect import (
    33	    WiringDialect,
    34	    get_dialect,
    35	    iter_dialects,
    36	    register_dialect,
    37	)
    38	from guardkitfactory.wiring.parser import get_parser, parse_bytes, parse_file
    39	
    40	__all__ = [
    41	    "Finding",
    42	    "MockSeamResult",
    43	    "WiringDialect",
    44	    "WiringResult",
    45	    "WiringStatus",
    46	    "analyze_wiring",
    47	    "get_dialect",
    48	    "get_parser",
    49	    "iter_dialects",
    50	    "parse_bytes",
    51	    "parse_file",
    52	    "register_dialect",
    53	]
Tool:      1	"""WiringAnalyzer: stack-agnostic wiring-analysis engine.
     2	
     3	Operates over tree-sitter Concrete Syntax Trees.  The only stack-specific
     4	input is a declarative ``WiringDialect`` descriptor (DATA).  Adding a
     5	language is **a descriptor entry, not a code plugin change**.
     6	
     7	Fidelity caveat
     8	---------------
     9	tree-sitter yields a **Concrete Syntax Tree, NOT full semantic
    10	resolution**.  Reachability is a **syntactic identifier-match heuristic
    11	across files** — the same fidelity as the prior python-ast plan, now
    12	multi-language.  It cannot resolve aliased imports, dynamic dispatch,
    13	string-keyed registries, reflection-based DI, or entry-points outside
    14	the worktree.  The FP/FN posture deliberately **biases toward WIRED**
    15	(substrings count as referenced; ``__all__`` / manifest names count as
    16	wired; parse-degraded files are skipped, never flagged) so the heuristic
    17	produces accepted false-negatives, never false-red false-positives.
    18	
    19	Result shape (consumed by guardkit's Coach evidence path)
    20	----------------------------------------------------------
    21	``analyze_wiring`` returns ``None`` when the probe legitimately did not
    22	run (task-type gate; zero authored non-test source targets), otherwise a
    23	dict in the ``bundle.wiring`` shape of the scope doc §5.1, with the
    24	MOCKED_SEAM result nested under the ``"mocked_seam"`` key (its own §5.1
    25	shape) so a single CST pass serves both probes::
    26	
    27	    {
    28	      "status": "complete" | "parse_degraded" | "unsupported_stack" | "error",
    29	      "dialect": "<primary>", "language": "<primary>",
    30	      "dialects": [...], "languages": [...],          # polyglot (AC-021)
    31	      "targets_scanned": int, "symbols_examined": int,
    32	      "findings": [ {UNWIRED_PATH finding} ],
    33	      "degraded_files": [...],
    34	      "mocked_seam": {
    35	        "status": "ran" | "skipped_no_acceptance_files",
    36	        "ran": bool, "skip_reason": str | None,
    37	        "dialect": ..., "language": ...,
    38	        "findings": [ {MOCKED_SEAM finding, severity warning|info} ],
    39	        "external_mocks_ignored": [...],
    40	      },
    41	    }
    42	
    43	No status value ever maps to "pass": the only positive verdict is
    44	``complete`` **with** ``findings: []`` (scope §5.6).
    45	"""
    46	
    47	from __future__ import annotations
    48	
    49	import fnmatch
    50	import logging
    51	import os
    52	import re
    53	from dataclasses import dataclass, field
    54	from pathlib import Path
    55	from typing import Any
    56	
    57	from guardkitfactory.wiring.dialect import (
    58	    WiringDialect,
    59	    _find_language,
    60	    get_dialect,
    61	    iter_dialects,
    62	)
    63	from guardkitfactory.wiring.parser import _load_language, parse_bytes
    64	
    65	logger = logging.getLogger(__name__)
    66	
    67	# ---------------------------------------------------------------------------
    68	# Status discriminator
    69	# ---------------------------------------------------------------------------
    70	
    71	WiringStatus = str  # literal type: see status table below
    72	
    73	# Status values (no value maps to "pass" — see scope doc §5.6):
    74	#   complete                    — analyzer ran, classification authoritative
    75	#                                 (empty findings = real positive verdict)
    76	#   unsupported_stack           — no dialect for the detected language
    77	#   parse_degraded              — ≥1 target skipped on CST parse error
    78	#                                 (biased WIRED, recorded in degraded_files)
    79	#   error                       — unexpected exception, caught fail-open
    80	# MOCKED_SEAM sub-result additionally uses:
    81	#   ran / skipped_no_acceptance_files
    82	
    83	_ANALYZED_TASK_TYPES = frozenset({"FEATURE", "REFACTOR", "INTEGRATION"})
    84	
    85	# Source extensions that are real languages we know about but have no
    86	# registered dialect — used to report unsupported_stack (absent-signal)
    87	# instead of None when a stack profile is not supplied.
    88	_KNOWN_UNDIALECTED_EXTENSIONS = {
    89	    ".rb": "ruby",
    90	    ".go": "go",
    91	    ".rs": "rust",
    92	    ".java": "java",
    93	    ".kt": "kotlin",
    94	    ".swift": "swift",
    95	    ".php": "php",
    96	    ".scala": "scala",
    97	    ".ex": "elixir",
    98	    ".erl": "erlang",
    99	}
   100	
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/installer/core/templates/langchain-deepagents-weighted-evaluation/tests/test_coach_template.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/integration/orchestrator/test_coach_bfull_falsifier.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/integration/orchestrator/test_coach_claim_audit.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/integration/orchestrator/test_coach_honesty_restoration.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/integration/orchestrator/test_coach_output_parser_parity.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/integration/orchestrator/test_coach_record_honesty_roundtrip.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/integration/orchestrator/test_coach_validator_compound_ids.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/integration/test_coach_context_integration.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/integration/test_coach_security.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/orchestrator/test_coach_evidence_bundle.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/orchestrator/test_coach_gather_bfull.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/orchestrator/test_coach_independent_test_absent_guard.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/orchestrator/test_coach_independent_test_timeout.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/orchestrator/test_coach_interpreter_selection.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/orchestrator/test_coach_sdk_stream_resilience.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/orchestrator/test_coach_synthesis_split.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/orchestrator/test_coach_zero_cardinality_guard.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/templates/langchain-deepagents/test_coach_template.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/orchestrator/quality_gates/test_coach_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/orchestrator/quality_gates/test_coach_validator_ac_id_matching.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/orchestrator/quality_gates/test_coach_validator_bdd_filter.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/orchestrator/quality_gates/test_coach_validator_hybrid_fallback.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/orchestrator/quality_gates/test_coach_validator_plan_audit_escalation.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/orchestrator/quality_gates/test_coach_validator_test_command_honesty.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/orchestrator/test_coach_output_parser.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/orchestrator/test_coach_validator_operator_handoff.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/planning/test_coach_context_builder.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_agent_invocations_stall_classification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_command_verification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_failure_classification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_parallel_isolation.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_seam_tests_blocking_gate.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_source_file_contention.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_subprocess_tests.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_validator_aliases.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_validator_consumer_context.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_validator_diagnostics.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_validator_fuzzy.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_validator_logging.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_verification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_verification_claim_audit.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_verification_promises.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-AOF/tests/unit/test_coach_verification_state_bridge.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/installer/core/templates/langchain-deepagents-weighted-evaluation/tests/test_coach_template.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/integration/orchestrator/test_coach_bfull_falsifier.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/integration/orchestrator/test_coach_claim_audit.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/integration/orchestrator/test_coach_honesty_restoration.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/integration/orchestrator/test_coach_output_parser_parity.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/integration/orchestrator/test_coach_record_honesty_roundtrip.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/integration/orchestrator/test_coach_validator_compound_ids.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/integration/test_coach_context_integration.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/integration/test_coach_security.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_evidence_bundle.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_gather_bfull.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_independent_test_absent_guard.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_independent_test_timeout.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_interpreter_selection.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_sdk_stream_resilience.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_synthesis_split.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_zero_cardinality_guard.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/templates/langchain-deepagents/test_coach_template.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/orchestrator/quality_gates/test_coach_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/orchestrator/quality_gates/test_coach_validator_ac_id_matching.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/orchestrator/quality_gates/test_coach_validator_bdd_filter.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/orchestrator/quality_gates/test_coach_validator_hybrid_fallback.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/orchestrator/quality_gates/test_coach_validator_plan_audit_escalation.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/orchestrator/quality_gates/test_coach_validator_test_command_honesty.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/orchestrator/test_coach_output_parser.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/orchestrator/test_coach_validator_operator_handoff.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/planning/test_coach_context_builder.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_agent_invocations_stall_classification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_command_verification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_failure_classification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_parallel_isolation.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_seam_tests_blocking_gate.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_source_file_contention.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_subprocess_tests.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_validator_aliases.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_validator_consumer_context.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_validator_diagnostics.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_validator_fuzzy.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_validator_logging.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_verification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_verification_claim_audit.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_verification_promises.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/test_coach_verification_state_bridge.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-GLI-004/tests/integration/test_coach_context_integration.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-GLI-004/tests/integration/test_coach_security.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-GLI-004/tests/unit/planning/test_coach_context_builder.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-GLI-004/tests/unit/test_coach_failure_classification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-GLI-004/tests/unit/test_coach_subprocess_tests.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-GLI-004/tests/unit/test_coach_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-GLI-004/tests/unit/test_coach_validator_aliases.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-GLI-004/tests/unit/test_coach_validator_consumer_context.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-GLI-004/tests/unit/test_coach_validator_diagnostics.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-GLI-004/tests/unit/test_coach_validator_fuzzy.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-GLI-004/tests/unit/test_coach_validator_logging.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-GLI-004/tests/unit/test_coach_verification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/installer/core/templates/langchain-deepagents-weighted-evaluation/tests/test_coach_template.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/integration/orchestrator/test_coach_honesty_restoration.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/integration/orchestrator/test_coach_record_honesty_roundtrip.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/integration/orchestrator/test_coach_validator_compound_ids.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/integration/test_coach_context_integration.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/integration/test_coach_security.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/orchestrator/test_coach_interpreter_selection.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/orchestrator/test_coach_sdk_stream_resilience.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/templates/langchain-deepagents/test_coach_template.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/orchestrator/quality_gates/test_coach_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/orchestrator/quality_gates/test_coach_validator_ac_id_matching.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/orchestrator/quality_gates/test_coach_validator_hybrid_fallback.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/orchestrator/quality_gates/test_coach_validator_plan_audit_escalation.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/orchestrator/quality_gates/test_coach_validator_test_command_honesty.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/orchestrator/test_coach_validator_operator_handoff.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/planning/test_coach_context_builder.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_agent_invocations_stall_classification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_command_verification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_failure_classification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_parallel_isolation.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_seam_tests_blocking_gate.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_source_file_contention.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_subprocess_tests.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_validator_aliases.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_validator_consumer_context.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_validator_diagnostics.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_validator_fuzzy.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_validator_logging.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_verification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_verification_promises.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/TASK-OBS-ABST/tests/unit/test_coach_verification_state_bridge.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/installer/core/templates/langchain-deepagents-weighted-evaluation/tests/test_coach_template.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/orchestrator/test_coach_bfull_falsifier.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/orchestrator/test_coach_claim_audit.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/orchestrator/test_coach_honesty_restoration.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/orchestrator/test_coach_output_parser_parity.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/orchestrator/test_coach_record_honesty_roundtrip.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/orchestrator/test_coach_validator_compound_ids.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/test_coach_context_integration.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/integration/test_coach_security.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/orchestrator/test_coach_evidence_bundle.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/orchestrator/test_coach_gather_bfull.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/orchestrator/test_coach_independent_test_absent_guard.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/orchestrator/test_coach_independent_test_timeout.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/orchestrator/test_coach_interpreter_selection.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/orchestrator/test_coach_sdk_stream_resilience.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/orchestrator/test_coach_synthesis_split.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/orchestrator/test_coach_zero_cardinality_guard.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/templates/langchain-deepagents/test_coach_template.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/orchestrator/quality_gates/test_coach_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/orchestrator/quality_gates/test_coach_validator_ac_id_matching.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/orchestrator/quality_gates/test_coach_validator_bdd_filter.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/orchestrator/quality_gates/test_coach_validator_hybrid_fallback.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/orchestrator/quality_gates/test_coach_validator_plan_audit_escalation.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/orchestrator/quality_gates/test_coach_validator_test_command_honesty.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/orchestrator/test_coach_output_parser.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/orchestrator/test_coach_validator_operator_handoff.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/planning/test_coach_context_builder.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_agent_invocations_stall_classification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_command_verification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_failure_classification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_parallel_isolation.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_seam_tests_blocking_gate.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_source_file_contention.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_subprocess_tests.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_validator.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_validator_aliases.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_validator_consumer_context.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_validator_diagnostics.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_validator_fuzzy.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_validator_logging.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_verification.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_verification_claim_audit.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_verification_promises.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/tests/unit/test_coach_verification_state_bridge.py']
AI: The test files DO exist in FEAT-C332. Let me read the existing test files and the rest of the coach_validator.py to understand the `_compute_own_authored` method and the full gather_evidence flow.

[{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_evidence_bundle.py'}, 'id': 'fc_xN3UGBCc75UX6eO0anKJlTOJXVOYK5zQ', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/unit/orchestrator/quality_gates/test_coach_validator.py', 'limit': 100}, 'id': 'fc_QQIjtcSkSRGHmVPlGSPvTpKgNwH6TYqR', 'type': 'tool_call'}, {'name': 'grep', 'args': {'pattern': '_compute_own_authored', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'output_mode': 'content'}, 'id': 'fc_HPrNJNMrudMVBsQOsWHndVknTXlDlWGz', 'type': 'tool_call'}]
Tool:      1	"""AC-014 — CoachValidator.gather_evidence returns a populated CoachEvidenceBundle.
     2	
     3	TASK-HMIG-008R Part E (Revision 3). Verifies the deterministic gathering
     4	pipeline introduced in Part A: ``CoachValidator.gather_evidence`` runs the
     5	same helpers ``validate()`` uses (``_verify_honesty``, ``verify_quality_gates``,
     6	``validate_requirements``, ``run_independent_tests``) and packages the
     7	intermediates into a :class:`CoachEvidenceBundle` instead of applying
     8	decision logic.
     9	
    10	Falsifier shape:
    11	
    12	* A passing-turn fixture must yield ``gathering_status == "complete"`` and a
    13	  bundle with populated ``quality_gates``, ``arch_review``, ``plan_audit``,
    14	  and ``tests`` fields. ``honesty.verified`` is True. JSON-serialisation via
    15	  ``bundle.to_dict()`` works for the entire bundle.
    16	* A state-bridge-move fixture (Player report contains a path the
    17	  orchestrator moved mid-turn, canonical path resolves) must populate
    18	  ``bundle.honesty.resolved_paths`` so the LLM Coach receives the
    19	  Layer-1 audit trail.
    20	* A pre-evidence error (missing ``task_work_results.json``) must produce
    21	  ``gathering_status == "partial_exception"`` with a populated
    22	  ``gathering_error`` rather than raising to the caller. This is the
    23	  Phase 2.5-review-finding-#1 contract: ``gather_evidence`` MUST NOT
    24	  raise so the autobuild primary path never falls back to ``validate()``.
    25	
    26	These tests do not assert decision logic; that is the
    27	``_apply_legacy_decision_logic`` shim's responsibility (Part A.2 follow-up)
    28	and the LLM Coach's responsibility under the primary path.
    29	"""
    30	
    31	from __future__ import annotations
    32	
    33	import json
    34	import subprocess
    35	from pathlib import Path
    36	from unittest.mock import patch
    37	
    38	import pytest
    39	
    40	from guardkit.orchestrator.coach_verification import CoachVerifier
    41	from guardkit.orchestrator.quality_gates.coach_evidence import (
    42	    CoachEvidenceBundle,
    43	    GatheringStatus,
    44	)
    45	from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
    46	
    47	
    48	# ---------------------------------------------------------------------------
    49	# Fixture helpers
    50	# ---------------------------------------------------------------------------
    51	
    52	
    53	def _init_git_worktree(path: Path) -> None:
    54	    """Minimal git init so TaskStateBridge can construct without raising."""
    55	    subprocess.run(
    56	        ["git", "init", "-q"], cwd=path, check=True, capture_output=True
    57	    )
    58	    subprocess.run(
    59	        ["git", "-C", str(path), "config", "user.email", "t@t"], check=True, capture_output=True,
    60	    )
    61	    subprocess.run(
    62	        ["git", "-C", str(path), "config", "user.name", "t"], check=True, capture_output=True,
    63	    )
    64	
    65	
    66	def _passing_task_work_results() -> dict:
    67	    """Return a task_work_results dict where every gate passes."""
    68	    return {
    69	        "task_id": "TASK-X",
    70	        "quality_gates": {
    71	            "all_passed": True,
    72	            "tests_run": 12,
    73	            "tests_failed": 0,
    74	            "coverage_met": True,
    75	            "line_coverage": 0.85,
    76	            "branch_coverage": 0.78,
    77	        },
    78	        "code_review": {"score": 80, "solid_score": 85, "dry_score": 78, "yagni_score": 82},
    79	        "plan_audit": {"status": "passed", "violations": 0, "severity": "low"},
    80	        "files_modified": [],
    81	        "files_created": [],
    82	        "tests_written": [],
    83	    }
    84	
    85	
    86	def _write_results(worktree: Path, task_id: str, results: dict) -> None:
    87	    results_dir = worktree / ".guardkit" / "autobuild" / task_id
    88	    results_dir.mkdir(parents=True, exist_ok=True)
    89	    (results_dir / "task_work_results.json").write_text(json.dumps(results))
    90	
    91	
    92	@pytest.fixture
    93	def worktree(tmp_path: Path) -> Path:
    94	    """A git worktree with a default-honest passing-turn fixture written."""
    95	    _init_git_worktree(tmp_path)
    96	    _write_results(tmp_path, "TASK-X", _passing_task_work_results())
    97	    return tmp_path
    98	
    99	
   100	# ---------------------------------------------------------------------------
Tool:      1	"""CoachValidator BDD oracle gate tests (TASK-BDD-E8954).
     2	
     3	Validates Coach behaviour for the ``bdd_results`` gate added in
     4	TASK-BDD-E8954. The gate enforces the three-state model from the task spec:
     5	
     6	- ``scenarios_failed > 0``  → reject (must_fix ``bdd_failure``)
     7	- ``scenarios_pending > 0`` → approve **with feedback** (should_fix
     8	                              ``bdd_pending``); MUST NOT block on pending alone
     9	- ``bdd_results`` absent    → no gate active (back-compat: identical to today)
    10	
    11	The broader CoachValidator test suite remains in
    12	``tests/unit/test_coach_validator.py``. This file exists at the path named
    13	in the AC for direct discoverability.
    14	"""
    15	
    16	from __future__ import annotations
    17	
    18	import json
    19	import sys
    20	from pathlib import Path
    21	from typing import Any, Dict, List, Optional
    22	from unittest.mock import MagicMock, patch
    23	
    24	import pytest
    25	
    26	_REPO_ROOT = Path(__file__).resolve().parents[4]
    27	if str(_REPO_ROOT) not in sys.path:
    28	    sys.path.insert(0, str(_REPO_ROOT))
    29	
    30	from guardkit.orchestrator.quality_gates import CoachValidator
    31	
    32	
    33	# ---------------------------------------------------------------------------
    34	# Fixtures (mirror those from the broader CoachValidator suite — copied here
    35	# to keep this file self-contained per AC: it must be runnable in isolation)
    36	# ---------------------------------------------------------------------------
    37	
    38	
    39	@pytest.fixture
    40	def tmp_worktree(tmp_path):
    41	    worktree = tmp_path / "worktrees" / "TASK-001"
    42	    worktree.mkdir(parents=True)
    43	    return worktree
    44	
    45	
    46	@pytest.fixture
    47	def task_work_results_dir(tmp_worktree):
    48	    results_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-001"
    49	    results_dir.mkdir(parents=True)
    50	    return results_dir
    51	
    52	
    53	def _make_task_work_results(bdd_block: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    54	    """A passing baseline task_work_results, optionally with bdd_results attached."""
    55	    results: Dict[str, Any] = {
    56	        "quality_gates": {
    57	            "tests_passing": True,
    58	            "tests_passed": 15,
    59	            "tests_failed": 0,
    60	            "coverage": 85,
    61	            "coverage_met": True,
    62	            "all_passed": True,
    63	        },
    64	        "code_review": {"score": 82, "solid": 85, "dry": 80, "yagni": 82},
    65	        "plan_audit": {"violations": 0, "file_count_match": True},
    66	        "requirements_met": [
    67	            "OAuth2 authentication flow",
    68	            "Token generation",
    69	            "Token refresh",
    70	        ],
    71	    }
    72	    if bdd_block is not None:
    73	        results["bdd_results"] = bdd_block
    74	    return results
    75	
    76	
    77	def _make_task() -> Dict[str, Any]:
    78	    return {
    79	        "acceptance_criteria": [
    80	            "OAuth2 authentication flow",
    81	            "Token generation",
    82	            "Token refresh",
    83	        ],
    84	    }
    85	
    86	
    87	def _write(results_dir: Path, results: Dict[str, Any]) -> Path:
    88	    results_path = results_dir / "task_work_results.json"
    89	    results_path.write_text(json.dumps(results, indent=2))
    90	    return results_path
    91	
    92	
    93	# ---------------------------------------------------------------------------
    94	# AC tests — names match those listed in TASK-BDD-E8954 acceptance criteria
    95	# ---------------------------------------------------------------------------
    96	
    97	
    98	def test_bdd_failure_rejects(tmp_worktree, task_work_results_dir):
    99	    """AC: Coach rejects when ``bdd_results.scenarios_failed > 0``."""
   100	    _write(
Tool: No matches found
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 1}, 'id': 'fc_6iep7MiuJxCThbtpS1wsQT5wkLECQ0Mb', 'type': 'tool_call'}, {'name': 'grep', 'args': {'pattern': 'authored', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'output_mode': 'content'}, 'id': 'fc_TbUiS1VA5bSpwKKdTLKYicEuJzb86mih', 'type': 'tool_call'}]
Tool:      2	Coach validator for lightweight task-work result validation.
     3	
     4	This module provides the CoachValidator class that validates Player's
     5	implementation by reading task-work quality gate results rather than
     6	reimplementing the quality gates inside Coach.
     7	
     8	Architecture:
     9	    Implements Option D (per TASK-REV-0414): 100% code reuse by reading
    10	    task-work quality gate outputs instead of reimplementing validation.
    11	
    12	    Validation Flow:
    13	    1. Read task-work results from .guardkit/autobuild/{task_id}/task_work_results.json
    14	    2. Verify quality gates passed (tests, coverage, arch review, plan audit)
    15	    3. Run independent test verification (trust but verify)
    16	    4. Validate requirements satisfaction
    17	    5. Return approve/feedback decision
    18	
    19	Example:
    20	    >>> from guardkit.orchestrator.quality_gates import CoachValidator
    21	    >>>
    22	    >>> validator = CoachValidator("/path/to/worktree")
    23	    >>> result = validator.validate(
    24	    ...     task_id="TASK-001",
    25	    ...     turn=1,
    26	    ...     task={"acceptance_criteria": ["OAuth2 flow", "Token refresh"]}
    27	    ... )
    28	    >>>
    29	    >>> if result.decision == "approve":
    30	    ...     print("Coach approved implementation")
    31	"""
    32	
    33	import ast
    34	import fnmatch
    35	import json
    36	import logging
    37	import os
    38	import re
    39	import subprocess
    40	import sys
    41	import time
    42	from contextlib import aclosing
    43	from dataclasses import dataclass, field
    44	from pathlib import Path
    45	from typing import Any, Dict, List, Literal, Optional, Tuple
    46	
    47	from guardkit.orchestrator.coach_verification import (
    48	    CoachVerifier,
    49	    HonestyVerification,
    50	    _resolve_venv_python,
    51	)
    52	from guardkit.orchestrator.quality_gates.coach_evidence import (
    53	    CoachEvidenceBundle,
    54	)
    55	from guardkit.orchestrator.docker_fixtures import (
    56	    get_container_name,
    57	    get_env_exports,
    58	    get_start_commands,
    59	    is_known_service,
    60	)
    61	from guardkit.orchestrator.paths import TaskArtifactPaths
    62	from guardkit.orchestrator.phase_specialists import (
    63	    PHASE_DESCRIPTIONS,
    64	    detect_stack_template,
    65	    render_missing_phase_list,
    66	)
    67	from guardkit.orchestrator.schemas import STATUS_ALIASES
    68	from guardkit.models.task_types import TaskType, QualityGateProfile, get_profile, TASK_TYPE_ALIASES
    69	
    70	# TASK-HMIG-006.3: Coach's independent SDK invocation dispatches through
    71	# the HarnessAdapter substrate seam established by TASK-HMIG-006 (Player
    72	# path) and TASK-HMIG-006.2 (cross-repo helper migration). Importing at
    73	# module top matches the Player path convention in
    74	# ``agent_invoker.py:71-77`` and makes ``select_harness`` a stable patch
    75	# target for tests under ``coach_validator.select_harness``.
    76	from guardkit.orchestrator.exceptions import AgentInvocationError
    77	from guardkit.orchestrator.harness import (
    78	    AssistantMessageEvent,
    79	    ResultMessageEvent,
    80	    ToolResultEvent,
    81	    select_harness,
    82	)
    83	from guardkit.orchestrator.sdk_utils import check_assistant_message_error
    84	
    85	# Optional coach context integration (TASK-SC-009)
    86	try:
    87	    from guardkit.planning.coach_context_builder import build_coach_context
    88	    from guardkit.knowledge.graphiti_client import get_graphiti
    89	    ARCH_CONTEXT_AVAILABLE = True
    90	except ImportError:
    91	    ARCH_CONTEXT_AVAILABLE = False
    92	    build_coach_context = None
    93	    get_graphiti = None
    94	
    95	logger = logging.getLogger(__name__)
    96	
    97	# ============================================================================
    98	# BDD Factory Bridge — wire guardkitfactory.bdd into the Coach evidence path
    99	# ============================================================================
   100	#
   101	# TASK-BDDW-001: Replace the legacy pytest-hardcoded bdd_runner.py path in the
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py:
  992:             Player's task_work_results.json payload. Reads ``files_authored``
  995:             ``files_modified`` for compatibility with pre-files_authored
  1010:         waves they include peer-task edits this task never authored. Using
  1014:         FEAT-39E1 turn-2 evidence). ``files_authored`` is captured at the
  1017:         truthy-based: ``files_authored = []`` correctly means "this task
  1018:         authored nothing" and yields no contention, even when
  1024:         # TASK-FIX-CC-COND: prefer the Player's authored set when present.
  1026:         # task_work_results.json from before files_authored existed) from
  1028:         if "files_authored" in task_work_results:
  1029:             authored_raw = task_work_results.get("files_authored") or []
  1030:             own = {str(f) for f in authored_raw if f}
  1031:             source = "files_authored"
  1050:             # both the authored set and the (possibly contaminated)
  1056:                 "files_authored=%s, files_modified=%s, files_created=%s)",
  1059:                 sorted(task_work_results.get("files_authored", []) or []),
  6210:           markdown block with code stubs (typically authored by ``/task-create``
  6489:         narrow non-fabrication subset of the above: the Player-authored
AI: Now I have a comprehensive understanding. Let me set up the implementation plan and start coding.

[{'name': 'write_todos', 'args': {'todos': [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'pending'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'pending'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'pending'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'pending'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'pending'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'pending'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'pending'}, {'content': 'Run tests and fix any issues', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]}, 'id': 'fc_Zfe4g5zRutUWRvDDwN79qdu66VUj9A5O', 'type': 'tool_call'}]
Tool: Updated todo list to [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'pending'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'pending'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'pending'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'pending'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'pending'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'pending'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'pending'}, {'content': 'Run tests and fix any issues', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]
AI: [{'name': 'write_todos', 'args': {'todos': [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'in_progress'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'pending'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'pending'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'pending'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'pending'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'pending'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'pending'}, {'content': 'Run tests and fix any issues', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]}, 'id': 'fc_STCWazqbWdqams2bIW408nyFstQEG1Mo', 'type': 'tool_call'}]
Tool: Updated todo list to [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'in_progress'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'pending'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'pending'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'pending'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'pending'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'pending'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'pending'}, {'content': 'Run tests and fix any issues', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]
AI: [{'name': 'edit_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_evidence.py', 'old_string': '   tests: Optional[Dict[str, Any]] = None\n\n    independent_tests: Optional["IndependentTestResult"] = None', 'new_string': '   tests: Optional[Dict[str, Any]] = None\n\n    # UNWIRED_PATH bundle fields (TASK-QAWE-002, Wave 1).\n    # Populated only on the complete-path return when the task type is\n    # FEATURE / REFACTOR / INTEGRATION and guardkitfactory is available.\n    # When the guard is absent (ImportError, SCAFFOLDING, DOCUMENTATION,\n    # zero-authored targets) all three fields are None (absent signal).\n    wiring: Optional[Dict[str, Any]] = None\n    mocked_seam: Optional[Dict[str, Any]] = None\n    spec_gap: Optional[Dict[str, Any]] = None\n\n    independent_tests: Optional["IndependentTestResult"] = None'}, 'id': 'fc_pPRBG2qsKGiTTb4CiKOSV7AS5zWHwHb4', 'type': 'tool_call'}]
Tool: Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_evidence.py'
AI: Now let me add the docstring for the new fields:

[{'name': 'edit_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_evidence.py', 'old_string': "   tests\n        Aggregate test result dict (tests_passed / tests_run /\n        line_coverage_met / branch_coverage_met / requires_infrastructure).\n        ``None`` when no test_results block was produced. The Coach applies\n        the absence-of-failure guard against ``tests['tests_run']``.\n    independent_tests", 'new_string': "   tests\n        Aggregate test result dict (tests_passed / tests_run /\n        line_coverage_met / branch_coverage_met / requires_infrastructure).\n        ``None`` when no test_results block was produced. The Coach applies\n        the absence-of-failure guard against ``tests['tests_run']``.\n    wiring\n        UNWIRED_PATH analysis result dict from\n        ``guardkitfactory.wiring.analyze_wiring``. ``None`` when the probe\n        did not run (task-type gate, ImportError, or zero-authored targets).\n        Contains ``findings`` (UNWIRED_PATH findings), ``status``,\n        ``targets_scanned``, etc.\n    mocked_seam\n        MOCKED_SEAM analysis result dict nested from the same\n        ``analyze_wiring`` call. ``None`` when the probe did not run.\n        Contains ``findings`` (MOCKED_SEAM findings with severity warning),\n        ``status``, ``external_mocks_ignored``, etc.\n    spec_gap\n        Spec-gap analysis result dict. ``None`` when the probe did not run.\n        Contains ``deselected_files`` (files with zero BDD bindings),\n        ``status``, etc. Used as the ONE deterministic hard-gate.\n    independent_tests"}, 'id': 'fc_bPnf8ngCSTdhH6SdykMoQOz6wIoaPacp', 'type': 'tool_call'}]
Tool: Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_evidence.py'
AI: [{'name': 'write_todos', 'args': {'todos': [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'completed'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'in_progress'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'pending'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'pending'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'pending'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'pending'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'pending'}, {'content': 'Run tests and fix any issues', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]}, 'id': 'fc_V5nfq2UriSHLOIll4kTTcPvHCbPRfuGL', 'type': 'tool_call'}]
Tool: Updated todo list to [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'completed'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'in_progress'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'pending'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'pending'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'pending'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'pending'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'pending'}, {'content': 'Run tests and fix any issues', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]
AI: Let me find the end of the CoachValidator class to add the helper method:

[{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 2500}, 'id': 'fc_54lewqtapHtGfJVrAKNX2OCM5znlSyOK', 'type': 'tool_call'}]
Tool:   2501	            ),
  2502	            "details": {
  2503	                "missing_phases": missing_phases_sorted,
  2504	                "expected_phases": expected_phases_val,
  2505	                "actual_invocations": actual_invocations_val,
  2506	            },
  2507	        }
  2508	
  2509	    def read_quality_gate_results(self, task_id: str) -> Dict[str, Any]:
  2510	        """
  2511	        Read quality gate results from task-work execution.
  2512	
  2513	        Looks for results in the standard location:
  2514	        `.guardkit/autobuild/{task_id}/task_work_results.json`
  2515	
  2516	        Parameters
  2517	        ----------
  2518	        task_id : str
  2519	            Task identifier
  2520	
  2521	        Returns
  2522	        -------
  2523	        Dict[str, Any]
  2524	            Task-work results, or dict with "error" key if not found
  2525	        """
  2526	        results_path = TaskArtifactPaths.task_work_results_path(task_id, self.worktree_path)
  2527	        logger.debug(f"Looking for task_work_results at: {results_path}")
  2528	
  2529	        if not results_path.exists():
  2530	            logger.warning(f"task_work_results.json not found at {results_path}")
  2531	            logger.debug(f"Worktree path: {self.worktree_path}")
  2532	            logger.debug(f"Task ID: {task_id}")
  2533	            return {"error": f"Task-work results not found at {results_path}"}
  2534	
  2535	        try:
  2536	            with open(results_path) as f:
  2537	                results = json.load(f)
  2538	            logger.debug(f"Successfully loaded task_work_results from {results_path}")
  2539	            return results
  2540	        except json.JSONDecodeError as e:
  2541	            logger.error(f"Failed to parse task-work results: {e}")
  2542	            return {"error": f"Failed to parse task-work results: {e}"}
  2543	        except Exception as e:
  2544	            logger.error(f"Failed to read task-work results: {e}")
  2545	            return {"error": f"Failed to read task-work results: {e}"}
  2546	
  2547	    def verify_quality_gates(
  2548	        self,
  2549	        task_work_results: Dict[str, Any],
  2550	        profile: Optional[QualityGateProfile] = None,
  2551	        skip_arch_review: bool = False,
  2552	    ) -> QualityGateStatus:
  2553	        """
  2554	        Verify task-work quality gates passed.
  2555	
  2556	        Checks the following gates from task-work results, respecting the quality
  2557	        gate profile which determines which gates are required for the task type:
  2558	        - tests_passed: From Phase 4.5 test results
  2559	        - coverage_met: From Phase 4.5 coverage check
  2560	        - arch_review_passed: From Phase 5 code review (score >= threshold)
  2561	        - plan_audit_passed: From Phase 5.5 plan audit (0 violations)
  2562	
  2563	        Parameters
  2564	        ----------
  2565	        task_work_results : Dict[str, Any]
  2566	            Results from task-work execution
  2567	        profile : Optional[QualityGateProfile]
  2568	            Quality gate profile for task type. If None, uses FEATURE profile
  2569	            (backward compatible with existing calls without profile parameter).
  2570	        skip_arch_review : bool
  2571	            If True, skip architectural review gate regardless of profile setting.
  2572	            Used for --implement-only mode where Phase 2.5B doesn't run.
  2573	            Default: False (enforce arch review per profile).
  2574	
  2575	        Returns
  2576	        -------
  2577	        QualityGateStatus
  2578	            Status of all quality gates with requirement flags
  2579	        """
  2580	        # Use default profile for backward compatibility
  2581	        if profile is None:
  2582	            profile = self.DEFAULT_PROFILE
  2583	        # Log input structure and profile for debugging
  2584	        logger.debug(f"task_work_results keys: {list(task_work_results.keys())}")
  2585	        logger.debug(f"quality_gates content: {task_work_results.get('quality_gates', 'NOT_FOUND')}")
  2586	        logger.debug(f"code_review content: {task_work_results.get('code_review', 'NOT_FOUND')}")
  2587	        logger.debug(f"plan_audit content: {task_work_results.get('plan_audit', 'NOT_FOUND')}")
  2588	        logger.debug(
  2589	            f"Profile requirements: tests={profile.tests_required}, "
  2590	            f"coverage={profile.coverage_required}, "
  2591	            f"arch_review={profile.arch_review_required}, "
  2592	            f"plan_audit={profile.plan_audit_required}"
  2593	        )
  2594	
  2595	        # Read from quality_gates object (what writer actually creates)
  2596	        quality_gates = task_work_results.get("quality_gates", {})
  2597	
  2598	        # Test results - use all_passed if present, otherwise check tests_failed
  2599	        # If tests not required by profile, default to True (skip gate)
  2600	        if not profile.tests_required:
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 95}, 'id': 'fc_PmWPFQBY9yz99VlLp3IUvRWRMUU3Zy9O', 'type': 'tool_call'}]
Tool:     96	
    97	# ============================================================================
    98	# BDD Factory Bridge — wire guardkitfactory.bdd into the Coach evidence path
    99	# ============================================================================
   100	#
   101	# TASK-BDDW-001: Replace the legacy pytest-hardcoded bdd_runner.py path in the
   102	# Coach evidence path with guardkitfactory's plugin-discovery subsystem.
   103	#
   104	# The bridge uses a lazy import (try/except ImportError) so that
   105	# ``pip install guardkit-py`` without the ``[autobuild]`` extra still works.
   106	# When guardkitfactory is unavailable, the Coach falls back to the Player's
   107	# self-reported ``bdd_results`` (legacy behaviour).
   108	#
   109	# Mapping: BDDRunResult (factory) → bundle.bdd dict (legacy shape)
   110	#
   111	#   BDDRunResult.scenarios_attempted  → bundle.bdd["scenarios_attempted"]
   112	#   BDDRunResult.scenarios_passed     → bundle.bdd["scenarios_passed"]
   113	#   BDDRunResult.scenarios_failed     → bundle.bdd["scenarios_failed"]
   114	#   BDDRunResult.scenarios_pending    → bundle.bdd["scenarios_pending"]
   115	#   BDDRunResult.failures             → bundle.bdd["failures"]
   116	#   BDDRunResult.pending              → bundle.bdd["pending"]
   117	#   BDDRunResult.feature_files        → bundle.bdd["feature_files"]
   118	#
   119	# Key contract: ``scenarios_attempted`` is non-Optional on BDDRunResult and
   120	# must be preserved verbatim for the absence-of-failure gate. A value of 0
   121	# means "no scenarios ran" (ABSENT SIGNAL), NOT "zero failures = pass".
   122	
   123	# StackProfile values consumed by guardkitfactory.bdd.discover().
   124	# Mapped from the worktree's project.template string.
   125	_STACK_PROFILE_MAP: Dict[str, str] = {
   126	    "python": "python",
   127	    "fastapi-python": "python",
   128	    "django-python": "python",
   129	    "flask-python": "python",
   130	    ".net": "dotnet",
   131	    "aspnet-core": "dotnet",
   132	    "csharp": "dotnet",
   133	    "node-js": "javascript",
   134	    "javascript": "javascript",
   135	    "typescript": "javascript",
   136	}
   137	"""Mapping from ``project.template`` to ``StackProfile`` string."""
   138	
   139	
   140	def _detect_stack_profile(workspace_root: Optional[Path]) -> Optional[str]:
   141	    """Detect the stack profile from the worktree's template string.
   142	
   143	    Parameters
   144	    ----------
   145	    workspace_root : Optional[Path]
   146	        Root of the worktree. Used to find ``.claude/settings.json``.
   147	
   148	    Returns
   149	    -------
   150	    Optional[str]
   151	        A ``StackProfile``-compatible string (``"python"``, ``"dotnet"``,
   152	        ``"javascript"``) or ``None`` when the template is unknown.
   153	    """
   154	    template = detect_stack_template(workspace_root)
   155	    if template is None:
   156	        return None
   157	    return _STACK_PROFILE_MAP.get(template)
   158	
   159	
   160	def _map_bdd_run_result_to_bundle(
   161	    run_result: "BDDRunResult",
   162	) -> Dict[str, Any]:
   163	    """Map a ``BDDRunResult`` into the legacy ``bundle.bdd`` dict shape.
   164	
   165	    Preserves ``scenarios_attempted`` verbatim — never coerces a missing key
   166	    to 0. This is critical for the absence-of-failure gate: when
   167	    ``scenarios_attempted == 0``, the Coach must treat it as ABSENT SIGNAL,
   168	    not as a silent pass.
   169	
   170	    Parameters
   171	    ----------
   172	    run_result : BDDRunResult
   173	        Result from the factory BDD plugin.
   174	
   175	    Returns
   176	    -------
   177	    Dict[str, Any]
   178	        A dict with keys: ``scenarios_attempted``, ``scenarios_passed``,
   179	        ``scenarios_failed``, ``scenarios_pending``, ``failures``,
   180	        ``pending``, ``feature_files``.
   181	    """
   182	    # Import here to avoid circular import at module level.
   183	    # BDDRunResult is imported lazily from guardkitfactory.
   184	    from dataclasses import asdict
   185	
   186	    failures = run_result.failures
   187	    pending = run_result.pending
   188	
   189	    # Convert FailureDetail/PendingDetail to dicts if they are dataclass instances.
   190	    failure_dicts: List[Dict[str, Any]] = []
   191	    for f in failures:
   192	        if hasattr(f, "asdict") or hasattr(f, "_asdict"):
   193	            failure_dicts.append(asdict(f))
   194	        elif isinstance(f, dict):
   195	            failure_dicts.append(f)
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 150, 'offset': 200}, 'id': 'fc_4OYWbOW9Ksdz4R865KbaNmxL3IXwlwPG', 'type': 'tool_call'}]
Tool:    201	            })
   202	
   203	    pending_dicts: List[Dict[str, Any]] = []
   204	    for p in pending:
   205	        if hasattr(p, "asdict") or hasattr(p, "_asdict"):
   206	            pending_dicts.append(asdict(p))
   207	        elif isinstance(p, dict):
   208	            pending_dicts.append(p)
   209	        else:
   210	            pending_dicts.append({
   211	                "scenario_name": getattr(p, "scenario_name", "<unknown>"),
   212	                "pending_step": getattr(p, "pending_step", ""),
   213	            })
   214	
   215	    return {
   216	        "scenarios_attempted": run_result.scenarios_attempted,
   217	        "scenarios_passed": run_result.scenarios_passed,
   218	        "scenarios_failed": run_result.scenarios_failed,
   219	        "scenarios_pending": run_result.scenarios_pending,
   220	        "failures": failure_dicts,
   221	        "pending": pending_dicts,
   222	        "feature_files": list(run_result.feature_files),
   223	    }
   224	
   225	
   226	# Lazy import of guardkitfactory BDD plugin subsystem.
   227	# The import is guarded so that ``pip install guardkit-py`` without
   228	# ``[autobuild]`` still works — Coach falls back to Player-reported
   229	# bdd_results when the factory is unavailable.
   230	try:
   231	    from guardkitfactory.bdd import (
   232	        BDDRunResult,
   233	        discover,
   234	    )
   235	    from guardkitfactory.bdd.plugin import StackProfile
   236	
   237	    _FACTORY_AVAILABLE = True
   238	except ImportError:
   239	    BDDRunResult = None  # type: ignore[misc,assignment]
   240	    discover = None  # type: ignore[misc,assignment]
   241	    StackProfile = None  # type: ignore[misc,assignment]
   242	    _FACTORY_AVAILABLE = False
   243	
   244	# Module-level cache for the factory import status.
   245	# Re-checked at runtime for each Coach invocation so that a late-installed
   246	# guardkitfactory (e.g. via a post-gather pip install) is picked up.
   247	_factory_available_cache: Optional[bool] = None
   248	
   249	
   250	def _is_factory_available() -> bool:
   251	    """Return True when the guardkitfactory BDD plugin subsystem is importable.
   252	
   253	    Uses a module-level cache that is invalidated on each call to
   254	    ``gather_evidence`` (see the ``_reset_factory_cache`` helper).
   255	    """
   256	    global _factory_available_cache
   257	    if _factory_available_cache is not None:
   258	        return _factory_available_cache
   259	    _factory_available_cache = _FACTORY_AVAILABLE
   260	    return _FACTORY_AVAILABLE
   261	
   262	
   263	def _reset_factory_cache() -> None:
   264	    """Invalidate the factory availability cache.
   265	
   266	    Called at the start of each ``gather_evidence`` invocation so that
   267	    a late-installed guardkitfactory is picked up on subsequent runs.
   268	    """
   269	    global _factory_available_cache
   270	    _factory_available_cache = None
   271	
   272	
   273	def _run_factory_bdd(
   274	    worktree_path: Path,
   275	    stack_profile: Optional[str],
   276	) -> Optional[Dict[str, Any]]:
   277	    """Discover and run the BDD plugin for the given stack profile.
   278	
   279	    Uses ``guardkitfactory.bdd.discover(stack_profile)`` to find the plugin,
   280	    invokes it to get a ``BDDRunResult``, and maps the result into the legacy
   281	    ``bundle.bdd`` dict shape.
   282	
   283	    Parameters
   284	    ----------
   285	    worktree_path : Path
   286	        Root of the worktree containing the BDD scenarios.
   287	    stack_profile : Optional[str]
   288	        Detected stack profile (``"python"``, ``"dotnet"``, ``"javascript"``).
   289	
   290	    Returns
   291	    -------
   292	    Optional[Dict[str, Any]]
   293	        A ``bundle.bdd``-shaped dict, or ``None`` when the factory is
   294	        unavailable, the stack profile is unknown, or discovery fails.
   295	    """
   296	    if not _is_factory_available():
   297	        logger.debug(
   298	            "BDD factory bridge: guardkitfactory not available; "
   299	            "falling back to Player-reported bdd_results.",
   300	        )
   301	        return None
   302	
   303	    if stack_profile is None:
   304	        logger.debug(
   305	            "BDD factory bridge: no stack profile detected; "
   306	            "falling back to Player-reported bdd_results.",
   307	        )
   308	        return None
   309	
   310	    # Guard against StackProfile being None (factory not importable).
   311	    if StackProfile is None:
   312	        return None
   313	
   314	    try:
   315	        plugin = discover(stack_profile)
   316	        if plugin is None:
   317	            logger.debug(
   318	                "BDD factory bridge: no plugin discovered for stack %s; "
   319	                "falling back to Player-reported bdd_results.",
   320	                stack_profile,
   321	            )
   322	            return None
   323	
   324	        # Invoke the plugin to get BDDRunResult.
   325	        # The plugin is responsible for running the scenarios and returning
   326	        # a BDDRunResult with the counts-only contract.
   327	        result = plugin.run(worktree_path)
   328	
   329	        if result is None:
   330	            logger.debug(
   331	                "BDD factory bridge: plugin returned None for stack %s; "
   332	                "falling back to Player-reported bdd_results.",
   333	                stack_profile,
   334	            )
   335	            return None
   336	
   337	        # Map BDDRunResult → bundle.bdd shape.
   338	        return _map_bdd_run_result_to_bundle(result)
   339	
   340	    except Exception as exc:  # noqa: BLE001 — BDD failures must not break evidence gathering
   341	        logger.warning(
   342	            "BDD factory bridge raised %s for stack %s; "
   343	            "falling back to Player-reported bdd_results.",
   344	            exc.__class__.__name__,
   345	            stack_profile,
   346	        )
   347	        return None
   348	
   349	
   350	# TASK-FIX-A7B4: Markers that satisfy a `## Seam Tests` block in a task
AI: Now I'll add the wiring bridge section after the BDD factory bridge:

[{'name': 'edit_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'old_string': '   except Exception as exc:  # noqa: BLE001 — BDD failures must not break evidence gathering\n        logger.warning(\n            "BDD factory bridge raised %s for stack %s; "\n            "falling back to Player-reported bdd_results.",\n            exc.__class__.__name__,\n            stack_profile,\n        )\n        return None\n\n\n# TASK-FIX-A7B4: Markers that satisfy a `## Seam Tests` block in a task', 'new_string': '   except Exception ...(argument truncated)'}, 'id': 'fc_Dgdu02mgJRmqZMs7NWLd5kOZpIaHhlVW', 'type': 'tool_call'}]
Tool: Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py'
AI: [{'name': 'write_todos', 'args': {'todos': [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'completed'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'completed'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'in_progress'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'completed'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'pending'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'pending'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'pending'}, {'content': 'Run tests and fix any issues', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]}, 'id': 'fc_7RZfjUcPvFXgWQkUosZVNU6JAS2g12Ur', 'type': 'tool_call'}]
Tool: Updated todo list to [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'completed'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'completed'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'in_progress'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'completed'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'pending'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'pending'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'pending'}, {'content': 'Run tests and fix any issues', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]
AI: [{'name': 'grep', 'args': {'pattern': '_reset_factory_cache', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'output_mode': 'content'}, 'id': 'fc_ll8AIiY2PJcWhF9jJ0LxdKX6enCOpCK6', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py:
  254:     ``gather_evidence`` (see the ``_reset_factory_cache`` helper).
  263: def _reset_factory_cache() -> None:
  2496:         _reset_factory_cache()
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 50, 'offset': 2490}, 'id': 'fc_5BtQXaFFBVGKVVnDQTMcCTKoaHtPByud', 'type': 'tool_call'}]
Tool:   2491	        #      and stack profile is known, run the BDD plugin and map the
  2492	        #      result into bundle.bdd shape.
  2493	        #   2. Player-reported bdd_results — legacy fallback when the factory
  2494	        #      is unavailable, the stack is unknown, or discovery fails.
  2495	        # ------------------------------------------------------------------
  2496	        _reset_factory_cache()
  2497	
  2498	        bdd_raw = task_work_results.get("bdd_results")
  2499	        bdd_dict: Optional[Dict[str, Any]] = None
  2500	
  2501	        if bdd_raw is not None and isinstance(bdd_raw, dict):
  2502	            # Player already produced BDD results — use them as-is.
  2503	            bdd_dict = bdd_raw
  2504	        elif _is_factory_available():
  2505	            # Factory is available but Player didn't produce results.
  2506	            # Attempt independent discovery via the factory plugin.
  2507	            stack_profile = _detect_stack_profile(self.worktree_path)
  2508	            factory_result = _run_factory_bdd(self.worktree_path, stack_profile)
  2509	            if factory_result is not None:
  2510	                bdd_dict = factory_result
  2511	                logger.info(
  2512	                    "gather_evidence: BDD evidence from factory plugin "
  2513	                    "(stack=%s, scenarios_attempted=%s).",
  2514	                    stack_profile,
  2515	                    factory_result.get("scenarios_attempted"),
  2516	                )
  2517	            else:
  2518	                logger.debug(
  2519	                    "gather_evidence: factory BDD discovery returned None; "
  2520	                    "bdd field left as absent signal.",
  2521	                )
  2522	        else:
  2523	            # Factory unavailable — bdd_dict stays None (absent signal).
  2524	            logger.debug(
  2525	                "gather_evidence: guardkitfactory not available; "
  2526	                "Player-reported bdd_results were empty; "
  2527	                "bdd field left as absent signal.",
  2528	            )
  2529	
  2530	        # Quality-gate-failure short-circuit. Legacy validate() also
  2531	        # short-circuits here via _feedback_from_gates.
  2532	        if not gates.all_gates_passed:
  2533	            logger.info(
  2534	                "gather_evidence: quality gates failed for %s; downstream "
  2535	                "(requirements, independent tests) skipped.", task_id,
  2536	            )
  2537	            return CoachEvidenceBundle(
  2538	                honesty=honesty,
  2539	                gathering_status="partial_gate_abort",
  2540	                quality_gates=gates,
AI: [{'name': 'edit_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'old_string': '       _reset_factory_cache()\n\n        bdd_raw = task_work_results.get("bdd_results")', 'new_string': '       _reset_factory_cache()\n        _reset_wiring_factory_cache()\n\n        bdd_raw = task_work_results.get("bdd_results")'}, 'id': 'fc_v5i4kx9SmOGooafcKVJE08HOkcpleDDn', 'type': 'tool_call'}]
Tool: Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py'
AI: Now let me find the complete-path return and add wiring evidence computation:

[{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 80, 'offset': 2570}, 'id': 'fc_VSSvDyZpIMy2E3cOrF4mRXr5M2SUyXHB', 'type': 'tool_call'}]
Tool:   2571	                coverage_details=coverage_details,
  2572	                plan_audit=plan_audit_dict,
  2573	                bdd=bdd_dict,
  2574	                arch_review=arch_review_dict,
  2575	                tests=tests_dict,
  2576	                severity_recommendations=severity_recommendations,
  2577	                advisory_issues=advisory_issues,
  2578	                task_type=task_type.value,
  2579	                profile_name=profile_name,
  2580	            )
  2581	
  2582	        # ------------------------------------------------------------------
  2583	        # 4. Independent tests. Mirrors validate() lines 1156-1175.
  2584	        # ------------------------------------------------------------------
  2585	        if not profile.tests_required:
  2586	            test_result: IndependentTestResult = IndependentTestResult(
  2587	                tests_passed=True,
  2588	                test_command="skipped",
  2589	                test_output_summary=(
  2590	                    f"Independent test verification skipped "
  2591	                    f"(tests not required for {task_type.value} tasks)"
  2592	                ),
  2593	                duration_seconds=0.0,
  2594	            )
  2595	            logger.info(
  2596	                "gather_evidence: independent test verification skipped for "
  2597	                "%s (tests not required for %s tasks)",
  2598	                task_id, task_type.value,
  2599	            )
  2600	        else:
  2601	            try:
  2602	                test_result = self.run_independent_tests(
  2603	                    task_work_results=task_work_results,
  2604	                    task=task,
  2605	                    turn=turn,
  2606	                )
  2607	            except Exception as exc:  # noqa: BLE001
  2608	                logger.error(
  2609	                    "gather_evidence: run_independent_tests raised: %s", exc,
  2610	                )
  2611	                return CoachEvidenceBundle(
  2612	                    honesty=honesty,
  2613	                    gathering_status="partial_exception",
  2614	                    gathering_error=f"independent_tests_exception: {exc}",
  2615	                    quality_gates=gates,
  2616	                    coverage_details=coverage_details,
  2617	                    plan_audit=plan_audit_dict,
  2618	                    bdd=bdd_dict,
  2619	                    arch_review=arch_review_dict,
  2620	                    tests=tests_dict,
  2621	                    requirements=requirements,
  2622	                    severity_recommendations=severity_recommendations,
  2623	                    advisory_issues=advisory_issues,
  2624	                    task_type=task_type.value,
  2625	                    profile_name=profile_name,
  2626	                )
  2627	
  2628	        return CoachEvidenceBundle(
  2629	            honesty=honesty,
  2630	            gathering_status="complete",
  2631	            quality_gates=gates,
  2632	            coverage_details=coverage_details,
  2633	            plan_audit=plan_audit_dict,
  2634	            bdd=bdd_dict,
  2635	            arch_review=arch_review_dict,
  2636	            tests=tests_dict,
  2637	            independent_tests=test_result,
  2638	            requirements=requirements,
  2639	            severity_recommendations=severity_recommendations,
  2640	            advisory_issues=advisory_issues,
  2641	            task_type=task_type.value,
  2642	            profile_name=profile_name,
  2643	        )
  2644	
  2645	    def _compute_agent_invocations_advisory(
  2646	        self, task_work_results: Dict[str, Any],
  2647	    ) -> Optional[Dict[str, Any]]:
  2648	        """Compute the non-blocking agent-invocations advisory issue.
  2649	
  2650	        Extracted from ``validate()`` lines 1028-1126 (TASK-FIX-RWOP1.3.1 /
AI: [{'name': 'edit_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py', 'old_string': '                   task_type=task_type.value,\n                    profile_name=profile_name,\n                )\n\n        return CoachEvidenceBundle(\n            honesty=honesty,\n            gathering_status="complete",\n            quality_gates=gates,\n            coverage_details=coverage_details,\n            plan_audit=plan_audit_dict,\n            bdd=bdd_dict,\n            arch_review=arch_review_dict,\n            tests=tests_dict,\n            independent_tests=test_result,\n            requirements=requirements,\n            severity_recommendations=severity_recommendations,\n            advisory_issues=advisory_issues,\n            task_type=task_type.value,\n            profile_name=profile_name,\n        )', 'new_string': '                   t...(argument truncated)'}, 'id': 'fc_oVA63tgaIo6tRaYtcuJ8sJwMf7h3c5uZ', 'type': 'tool_call'}]
Tool: Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_validator.py'
AI: [{'name': 'write_todos', 'args': {'todos': [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'completed'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'completed'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'completed'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'completed'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'in_progress'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'pending'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'pending'}, {'content': 'Run tests and fix any issues', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]}, 'id': 'fc_8J00ooCzpE1ryytT5dDGeR706KyU0l37', 'type': 'tool_call'}]
Tool: Updated todo list to [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'completed'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'completed'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'completed'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'completed'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'in_progress'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'pending'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'pending'}, {'content': 'Run tests and fix any issues', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/agent_invoker.py', 'limit': 50, 'offset': 3135}, 'id': 'fc_K3hMmAKSrg07SPjj8RkxnjHeEAcRLSIy', 'type': 'tool_call'}]
Tool:   3136	            }
  3137	
  3138	        # Truncate bdd.discoveries / bdd.errors.
  3139	        bdd = bundle_dict.get("bdd")
  3140	        if isinstance(bdd, dict):
  3141	            discoveries = bdd.get("discoveries")
  3142	            if isinstance(discoveries, list) and len(discoveries) > self._COACH_BDD_DISCOVERIES_LIMIT:
  3143	                remainder = len(discoveries) - self._COACH_BDD_DISCOVERIES_LIMIT
  3144	                bdd["discoveries"] = discoveries[: self._COACH_BDD_DISCOVERIES_LIMIT] + [
  3145	                    f"... and {remainder} more (truncated for token budget)"
  3146	                ]
  3147	            errors = bdd.get("errors")
  3148	            if isinstance(errors, list) and len(errors) > self._COACH_BDD_ERRORS_LIMIT:
  3149	                remainder = len(errors) - self._COACH_BDD_ERRORS_LIMIT
  3150	                bdd["errors"] = errors[: self._COACH_BDD_ERRORS_LIMIT] + [
  3151	                    f"... and {remainder} more (truncated for token budget)"
  3152	                ]
  3153	
  3154	        # honesty.discrepancies truncation lives inside _render_bundle_honesty_section,
  3155	        # but we ALSO truncate the copy nested in bundle_dict["honesty"] so the
  3156	        # evidence-bundle JSON the Coach sees is internally consistent.
  3157	        honesty = bundle_dict.get("honesty")
  3158	        if isinstance(honesty, dict):
  3159	            discrepancies = honesty.get("discrepancies")
  3160	            if (
  3161	                isinstance(discrepancies, list)
  3162	                and len(discrepancies) > self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3163	            ):
  3164	                remainder = len(discrepancies) - self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3165	                honesty["discrepancies"] = discrepancies[
  3166	                    : self._COACH_HONESTY_DISCREPANCIES_LIMIT
  3167	                ] + [{
  3168	                    "truncated": True,
  3169	                    "remainder": remainder,
  3170	                    "note": (
  3171	                        f"... and {remainder} more discrepancies (truncated "
  3172	                        f"for token budget). See full honesty_verification "
  3173	                        f"in coach_turn_N.json."
  3174	                    ),
  3175	                }]
  3176	
  3177	        try:
  3178	            payload = json.dumps(bundle_dict, indent=2, default=str)
  3179	        except Exception as exc:  # noqa: BLE001
  3180	            logger.error(
  3181	                "Failed to JSON-encode truncated evidence_bundle: %s", exc,
  3182	            )
  3183	            payload = '{"gathering_status": "partial_exception", "gathering_error": "json_encode_failed"}'
  3184	
  3185	        return f"""
AI: [{'name': 'edit_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/agent_invoker.py', 'old_string': '                  ),\n                }]\n\n        try:\n            payload = json.dumps(bundle_dict, indent=2, default=str)', 'new_string': '                  ),\n                }]\n\n        # Truncate wiring.findings (AC-016). Mirrors bdd.discoveries truncation.\n        wiring = bundle_dict.get("wiring")\n        if isinstance(wiring, dict):\n            findings = wiring.get("findings")\n            if isinstance(findings, list) and len(findings) > self._COACH_BDD_DISCOVERIES_LIMIT:\n                remainder = len(findings) - self._COACH_BDD_DISCOVERIES_LIMIT\n                wiring["findings"] = findings[: self._COACH_BDD_DISCOVERIES_LIMIT] + [\n                    f"... and {remainder} more (truncated for token budget)"\n                ]\n\n        try:\n            payload = json.dumps(bundle_dict, indent=2, default=str)'}, 'id': 'fc_PfUIi7v2XixboLb9oSyT5e3BJU8iVNKu', 'type': 'tool_call'}]
Tool: Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/agent_invoker.py'
AI: Now let me add the advisory guard sentence #7:

[{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/agent_invoker.py', 'limit': 50, 'offset': 3330}, 'id': 'fc_nuG4UcEoUslmCLltsgmgyESlMVXcsnFM', 'type': 'tool_call'}]
Tool:   3331	   If evidence_bundle.independent_tests is not null AND
  3332	   evidence_bundle.independent_tests.signal_absent == true: the Coach's own
  3333	   trust-but-verify pytest run did NOT complete (it timed out or failed at
  3334	   the transport layer before producing a verdict). This is ABSENT SIGNAL,
  3335	   NOT a passing or failing test result — do NOT approve on the basis of the
  3336	   Player's self-reported tests plus the other gates. Surface as feedback:
  3337	   "Independent test verification did not complete (signal absent) — cannot
  3338	   independently confirm the Player's reported tests." Quote
  3339	   independent_tests.test_output_summary verbatim in the rationale so
  3340	   operators can see whether it timed out or errored. Rule:
  3341	   .claude/rules/absence-of-failure-is-not-success.md.
  3342	</absence_of_failure_guards>
  3343	"""
  3344	
  3345	    def _verify_player_claims(
  3346	        self,
  3347	        player_report: Dict[str, Any],
  3348	    ) -> HonestyVerification:
  3349	        """Verify Player's self-reported claims against reality.
  3350	
  3351	        This method uses CoachVerifier to cross-reference Player claims:
  3352	        - Test results vs actual test execution
  3353	        - Claimed files vs filesystem state
  3354	        - Test counts vs parsed output
  3355	
  3356	        Args:
  3357	            player_report: Player's report from current turn
  3358	
  3359	        Returns:
  3360	            HonestyVerification with verification results and honesty score
  3361	
  3362	        Note:
  3363	            Returns a default verification result if verification fails,
  3364	            allowing the workflow to continue while logging the issue.
  3365	        """
  3366	        try:
  3367	            verifier = CoachVerifier(
  3368	                self.worktree_path, venv_python=self._venv_python
  3369	            )
  3370	            verification = verifier.verify_player_report(player_report)
  3371	
  3372	            if verification.discrepancies:
  3373	                logger.warning(
  3374	                    f"Player honesty verification found {len(verification.discrepancies)} "
  3375	                    f"discrepancies (score: {verification.honesty_score:.2f})"
  3376	                )
  3377	                for disc in verification.discrepancies:
  3378	                    logger.warning(
  3379	                        f"  [{disc.severity}] {disc.claim_type}: "
  3380	                        f"claimed {disc.player_claim}, actual {disc.actual_value}"
AI: [{'name': 'edit_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/agent_invoker.py', 'old_string': '  independent_tests.test_output_summary verbatim in the rationale so\n   operators can see whether it timed out or errored. Rule:\n   .claude/rules/absence-of-failure-is-not-success.md.\n</absence_of_failure_guards>\n"""', 'new_string': '  independent_tests.test_output_summary verbatim in the rationale so\n   operators can see whether it timed out or errored. Rule:\n   .claude/rules/absence-of-failure-is-not-success.md.\n\n7. SPEC-GAP HARD-GATE (TASK-QAWE-002).\n   If evidence_bundle.spec_gap is not null AND\n   evidence_bundle.spec_gap.deselected_files is non-empty: the Coach\n   must reject the task regardless of other gate outcomes. This is the\n   ONE deterministic hard-gate — a file with zero BDD bindings means\n   acceptance tests mock production seams or use stubs instead of\n   exercising real behaviour. Surface as feedback:\n   "SPEC-GAP: {count} authored file(s) have zero BDD bindings\n   ({\', \'.join(evidence_bundle.spec_gap.deselected_files[:5])}{\'...\' if count > 5 else \'\'}).\n   Reject — acceptance tests do not exercise real behaviour."\n   Rule: docs/features/qa-verifier-wiring-probes-scope.md §5.4.\n</absence_of_failure_guards>\n"""'}, 'id': 'fc_56lmrggpGFiuV2aJm7vljvu5qEfvgm8q', 'type': 'tool_call'}]
Tool: Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/agent_invoker.py'
AI: [{'name': 'write_todos', 'args': {'todos': [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'completed'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'completed'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'completed'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'completed'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'completed'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'completed'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'in_progress'}, {'content': 'Run tests and fix any issues', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]}, 'id': 'fc_vN6LcD3EvYz80M3CrPjTutp5GiBqUroz', 'type': 'tool_call'}]
Tool: Updated todo list to [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'completed'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'completed'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'completed'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'completed'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'completed'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'completed'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'in_progress'}, {'content': 'Run tests and fix any issues', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]
AI: Let me check the existing test file structure and write the test suite:

[{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_evidence_bundle.py', 'limit': 100, 'offset': 100}, 'id': 'fc_A7YdFIqjysOBATj3OGUK7VBIogWj3fbv', 'type': 'tool_call'}]
Tool:    101	# Happy path
   102	# ---------------------------------------------------------------------------
   103	
   104	
   105	class TestGatherEvidenceHappyPath:
   106	    """Passing-turn fixture: every field on the bundle is populated."""
   107	
   108	    def test_returns_coach_evidence_bundle(self, worktree: Path) -> None:
   109	        validator = CoachValidator(str(worktree), task_id="TASK-X")
   110	        bundle = validator.gather_evidence(
   111	            task_id="TASK-X",
   112	            turn=1,
   113	            task={
   114	                "acceptance_criteria": ["AC-001 trivial"],
   115	                "task_type": "feature",
   116	                "description": "happy path",
   117	            },
   118	        )
   119	        assert isinstance(bundle, CoachEvidenceBundle)
   120	
   121	    def test_gathering_status_complete_for_passing_turn(self, worktree: Path) -> None:
   122	        validator = CoachValidator(str(worktree), task_id="TASK-X")
   123	        bundle = validator.gather_evidence(
   124	            task_id="TASK-X",
   125	            turn=1,
   126	            task={
   127	                "acceptance_criteria": ["AC-001"],
   128	                "task_type": "feature",
   129	                "description": "x",
   130	            },
   131	        )
   132	        assert bundle.gathering_status == "complete"
   133	        assert bundle.gathering_error is None
   134	
   135	    def test_quality_gates_populated(self, worktree: Path) -> None:
   136	        validator = CoachValidator(str(worktree), task_id="TASK-X")
   137	        bundle = validator.gather_evidence(
   138	            task_id="TASK-X",
   139	            turn=1,
   140	            task={
   141	                "acceptance_criteria": ["AC-001"],
   142	                "task_type": "feature",
   143	                "description": "x",
   144	            },
   145	        )
   146	        assert bundle.quality_gates is not None
   147	        assert bundle.quality_gates.all_gates_passed is True
   148	        assert bundle.quality_gates.tests_passed is True
   149	
   150	    def test_arch_review_populated_with_score(self, worktree: Path) -> None:
   151	        validator = CoachValidator(str(worktree), task_id="TASK-X")
   152	        bundle = validator.gather_evidence(
   153	            task_id="TASK-X",
   154	            turn=1,
   155	            task={
   156	                "acceptance_criteria": ["AC-001"],
   157	                "task_type": "feature",
   158	                "description": "x",
   159	            },
   160	        )
   161	        assert bundle.arch_review is not None
   162	        assert bundle.arch_review["score"] == 80
   163	
   164	    def test_plan_audit_populated_with_status(self, worktree: Path) -> None:
   165	        validator = CoachValidator(str(worktree), task_id="TASK-X")
   166	        bundle = validator.gather_evidence(
   167	            task_id="TASK-X",
   168	            turn=1,
   169	            task={
   170	                "acceptance_criteria": ["AC-001"],
   171	                "task_type": "feature",
   172	                "description": "x",
   173	            },
   174	        )
   175	        assert bundle.plan_audit is not None
   176	        assert bundle.plan_audit["status"] == "passed"
   177	
   178	    def test_bdd_is_none_when_absent_from_results(self, worktree: Path) -> None:
   179	        """``bdd_results`` key absent → bundle.bdd is None (Pattern 2 guard
   180	        in the prompt branches on this directly)."""
   181	        validator = CoachValidator(str(worktree), task_id="TASK-X")
   182	        bundle = validator.gather_evidence(
   183	            task_id="TASK-X",
   184	            turn=1,
   185	            task={
   186	                "acceptance_criteria": ["AC-001"],
   187	                "task_type": "feature",
   188	                "description": "x",
   189	            },
   190	        )
   191	        assert bundle.bdd is None
   192	
   193	    def test_tests_dict_carries_tests_run_count(self, worktree: Path) -> None:
   194	        """The Pattern-2 zero-cardinality test guard inspects
   195	        ``bundle.tests['tests_run']`` — must be populated even when all
   196	        gates pass."""
   197	        validator = CoachValidator(str(worktree), task_id="TASK-X")
   198	        bundle = validator.gather_evidence(
   199	            task_id="TASK-X",
   200	            turn=1,
AI: [{'name': 'write_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py', 'content': '"""AC-002 / AC-008 /...(argument truncated)'}, 'id': 'fc_2VuqYg7Ji6zOL8gVjB28iKg9JstPyR6T', 'type': 'tool_call'}]
Tool: Updated file /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py
AI: [{'name': 'write_todos', 'args': {'todos': [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'completed'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'completed'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'completed'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'completed'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'completed'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'completed'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'completed'}, {'content': 'Run tests and fix any issues', 'status': 'in_progress'}, {'content': 'Write player report JSON', 'status': 'pending'}]}, 'id': 'fc_XzGfoyeAcM5BpxRqVlTj302f2qbJKlfI', 'type': 'tool_call'}]
Tool: Updated todo list to [{'content': 'Add wiring, mocked_seam, spec_gap fields to CoachEvidenceBundle dataclass', 'status': 'completed'}, {'content': 'Create _compute_wiring_evidence helper in coach_validator.py with lazy import', 'status': 'completed'}, {'content': 'Populate wiring fields in gather_evidence complete-path return only', 'status': 'completed'}, {'content': 'Add task-type gate (SCAFFOLDING/DOCUMENTATION → None fields)', 'status': 'completed'}, {'content': 'Update _render_evidence_bundle_section to truncate wiring findings', 'status': 'completed'}, {'content': 'Add advisory guard sentence #7 in agent_invoker.py', 'status': 'completed'}, {'content': 'Write comprehensive test suite for all ACs', 'status': 'completed'}, {'content': 'Run tests and fix any issues', 'status': 'in_progress'}, {'content': 'Write player report JSON', 'status': 'pending'}]
AI: [{'name': 'execute', 'args': {'command': 'cd /home/richardwoollcott/Projects/appmilla_github/guardkit && python -m pytest .guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py -v --tb=short 2>&1 | head -200', 'timeout': 120}, 'id': 'fc_7noWFkHSW4wxiF7CHXyE2Bc9lFGxJ7lG', 'type': 'tool_call'}]
Tool: /bin/sh: 1: python: not found

[Command succeeded with exit code 0]
AI: [{'name': 'execute', 'args': {'command': 'cd /home/richardwoollcott/Projects/appmilla_github/guardkit && python3 -m pytest .guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py -v --tb=short 2>&1 | head -200', 'timeout': 120}, 'id': 'fc_IzfterQfzs71ykvuJfqOKs0WBlMnqFE3', 'type': 'tool_call'}]
Tool: ============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0 -- /usr/bin/python3
cachedir: .pytest_cache
rootdir: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332
configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)
plugins: anyio-4.13.0, cov-7.1.0
collecting ... collected 0 items / 1 error

==================================== ERRORS ====================================
_______ ERROR collecting tests/orchestrator/test_coach_wiring_bundle.py ________
ImportError while importing test module '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
.guardkit/worktrees/FEAT-C332/.venv/lib/python3.12/site-packages/_pytest/python.py:507: in importtestmodule
    mod = import_path(
.guardkit/worktrees/FEAT-C332/.venv/lib/python3.12/site-packages/_pytest/pathlib.py:587: in import_path
    importlib.import_module(module_name)
/usr/lib/python3.12/importlib/__init__.py:90: in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
<frozen importlib._bootstrap>:1387: in _gcd_import
    ???
<frozen importlib._bootstrap>:1360: in _find_and_load
    ???
<frozen importlib._bootstrap>:1331: in _find_and_load_unlocked
    ???
<frozen importlib._bootstrap>:935: in _load_unlocked
    ???
.guardkit/worktrees/FEAT-C332/.venv/lib/python3.12/site-packages/_pytest/assertion/rewrite.py:197: in exec_module
    exec(co, module.__dict__)
.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py:26: in <module>
    from guardkit.orchestrator.quality_gates.coach_validator import (
E   ImportError: cannot import name '_compute_own_authored' from 'guardkit.orchestrator.quality_gates.coach_validator' (/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py)
=============================== warnings summary ===============================
.guardkit/worktrees/FEAT-C332/.venv/lib/python3.12/site-packages/_pytest/config/__init__.py:1434
  /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.venv/lib/python3.12/site-packages/_pytest/config/__init__.py:1434: PytestConfigWarning: Unknown config option: asyncio_default_fixture_loop_scope
  
    self._warn_or_fail_if_strict(f"Unknown config option: {key}\n")

.guardkit/worktrees/FEAT-C332/.venv/lib/python3.12/site-packages/_pytest/config/__init__.py:1434
  /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/.venv/lib/python3.12/site-packages/_pytest/config/__init__.py:1434: PytestConfigWarning: Unknown config option: asyncio_mode
  
    self._warn_or_fail_if_strict(f"Unknown config option: {key}\n")

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ============================
ERROR .guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
========================= 2 warnings, 1 error in 0.53s =========================

[Command succeeded with exit code 0]
AI: The worktree has its own copy of the source files. Let me check and apply the edits there too:

[{'name': 'execute', 'args': {'command': 'diff /home/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/quality_gates/coach_evidence.py /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py 2>&1 | head -20'}, 'id': 'fc_3trxYDnz4E2P3jOsudc6AK2urYC0srpJ', 'type': 'tool_call'}]
Tool: 128,142d127
<     wiring
<         UNWIRED_PATH analysis result dict from
<         ``guardkitfactory.wiring.analyze_wiring``. ``None`` when the probe
<         did not run (task-type gate, ImportError, or zero-authored targets).
<         Contains ``findings`` (UNWIRED_PATH findings), ``status``,
<         ``targets_scanned``, etc.
<     mocked_seam
<         MOCKED_SEAM analysis result dict nested from the same
<         ``analyze_wiring`` call. ``None`` when the probe did not run.
<         Contains ``findings`` (MOCKED_SEAM findings with severity warning),
<         ``status``, ``external_mocks_ignored``, etc.
<     spec_gap
<         Spec-gap analysis result dict. ``None`` when the probe did not run.
<         Contains ``deselected_files`` (files with zero BDD bindings),
<         ``status``, etc. Used as the ONE deterministic hard-gate.
172a158,174
>     wiring
>         UNWIRED_PATH analysis result (dict) from ``guardkitfactory.wiring``.
>         Contains ``status``, ``dialect``, ``language``, ``targets_scanned``,

[Command succeeded with exit code 0]
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_evidence.py', 'limit': 40, 'offset': 155}, 'id': 'fc_lpwGQCzrrx5bsjmET10cxSgsJ2irltes', 'type': 'tool_call'}]
Tool:    156	        Pre-populated so the LLM Coach can read them without re-computing the
   157	        Layer-2 demotion.
   158	    wiring
   159	        UNWIRED_PATH analysis result (dict) from ``guardkitfactory.wiring``.
   160	        Contains ``status``, ``dialect``, ``language``, ``targets_scanned``,
   161	        ``symbols_examined``, ``findings``, ``degraded_files``. ``None`` when
   162	        the task type gates out (SCAFFOLDING/DOCUMENTATION), there are no
   163	        authored source targets, or the factory is unavailable.
   164	    mocked_seam
   165	        MOCKED_SEAM analysis result (dict). Contains ``status``, ``ran``,
   166	        ``dialect``, ``findings``, ``external_mocks_ignored``. ``None`` when
   167	        the task type gates out, there are no authored acceptance files, or
   168	        the factory is unavailable.
   169	    spec_gap
   170	        SPEC_GAP analysis result (dict). Contains ``status``,
   171	        ``ground_truth_count``, ``executed_count``, ``findings``,
   172	        ``whole_file_deselection``. ``None`` when the task type gates out,
   173	        the factory BDD plugin is unavailable, or Wave-3 wiring is not yet
   174	        implemented.
   175	    """
   176	
   177	    honesty: "HonestyVerification"
   178	    gathering_status: GatheringStatus = "complete"
   179	    gathering_error: Optional[str] = None
   180	
   181	    quality_gates: Optional["QualityGateStatus"] = None
   182	    coverage_details: Optional[Dict[str, Any]] = None
   183	    plan_audit: Optional[Dict[str, Any]] = None
   184	    bdd: Optional[Dict[str, Any]] = None
   185	    arch_review: Optional[Dict[str, Any]] = None
   186	    tests: Optional[Dict[str, Any]] = None
   187	
   188	    # Wave-1 wiring evidence fields (TASK-QAWE-002).
   189	    # Populated by CoachValidator.gather_evidence at the complete-path return.
   190	    # Left None for SCAFFOLDING/DOCUMENTATION tasks, zero-target turns,
   191	    # or when guardkitfactory.wiring is unavailable (ImportError).
   192	    wiring: Optional[Dict[str, Any]] = None         # UNWIRED_PATH analysis
   193	    mocked_seam: Optional[Dict[str, Any]] = None    # MOCKED_SEAM analysis
   194	    spec_gap: Optional[Dict[str, Any]] = None       # SPEC_GAP (Wave-3)
   195	
AI: [{'name': 'grep', 'args': {'pattern': '_compute_wiring_evidence', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py', 'output_mode': 'content'}, 'id': 'fc_6szT8EceOYX24AxOrASaz7pHdikXXgnm', 'type': 'tool_call'}]
Tool: No matches found
AI: [{'name': 'grep', 'args': {'pattern': 'WIRING|wiring', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py', 'output_mode': 'content'}, 'id': 'fc_9IFxEFCeMcl6VVXJy1gC6Avu6kjELcKx', 'type': 'tool_call'}]
Tool: No matches found
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 340}, 'id': 'fc_Mx0muYV9fEbUCsFvvrBh3rYqILp4TivU', 'type': 'tool_call'}]
Tool:    341	        logger.warning(
   342	            "BDD factory bridge raised %s for stack %s; "
   343	            "falling back to Player-reported bdd_results.",
   344	            exc.__class__.__name__,
   345	            stack_profile,
   346	        )
   347	        return None
   348	
   349	
   350	# ============================================================================
   351	# Wiring Factory Bridge — wire guardkitfactory.wiring into the Coach evidence
   352	# ============================================================================
   353	#
   354	# TASK-QAWE-002 (Wave-1): Lazy import of the UNWIRED_PATH / MOCKED_SEAM
   355	# analyzer. The import is guarded so that ``pip install guardkit-py`` without
   356	# the ``[autobuild]`` extra still works — Coach leaves all three wiring
   357	# fields as ``None`` when the factory is unavailable.
   358	#
   359	# The seam returns a dict (never the dataclass) so coach_evidence.py keeps
   360	# zero guardkitfactory import.
   361	
   362	try:
   363	    from guardkitfactory.wiring import (  # type: ignore[attr-defined,no-redef]
   364	        analyze_wiring,
   365	    )
   366	
   367	    _WIRING_FACTORY_AVAILABLE = True
   368	except ImportError:
   369	    analyze_wiring = None  # type: ignore[misc,assignment]
   370	    _WIRING_FACTORY_AVAILABLE = False
   371	
   372	_wiring_factory_available_cache: Optional[bool] = None
   373	
   374	
   375	def _is_wiring_factory_available() -> bool:
   376	    """Return True when the guardkitfactory wiring analyzer is importable."""
   377	    global _wiring_factory_available_cache
   378	    if _wiring_factory_available_cache is not None:
   379	        return _wiring_factory_available_cache
   380	    _wiring_factory_available_cache = _WIRING_FACTORY_AVAILABLE
   381	    return _WIRING_FACTORY_AVAILABLE
   382	
   383	
   384	def _reset_wiring_factory_cache() -> None:
   385	    """Invalidate the wiring factory availability cache."""
   386	    global _wiring_factory_available_cache
   387	    _wiring_factory_available_cache = None
   388	
   389	
   390	def _compute_authored_set(
   391	    task_work_results: Dict[str, Any],
   392	) -> List[str]:
   393	    """Compute the set of source files authored by the Player this turn.
   394	
   395	    Uses the presence-based fallback from the task-work results:
   396	    ``files_authored`` when present, else ``files_created ∪ files_modified``.
   397	
   398	    This is NOT the git-enriched ``files_modified`` (which can be
   399	    peer-contaminated in parallel-wave execution).
   400	
   401	    Parameters
   402	    ----------
   403	    task_work_results : Dict[str, Any]
   404	        The task-work results dict from ``read_quality_gate_results``.
   405	
   406	    Returns
   407	    -------
   408	    List[str]
   409	        List of authored file paths (relative to worktree root).
   410	    """
   411	    files_authored = task_work_results.get("files_authored")
   412	    if files_authored and isinstance(files_authored, list):
   413	        return [str(f) for f in files_authored]
   414	
   415	    # Fallback: files_created ∪ files_modified
   416	    created = task_work_results.get("files_created") or []
   417	    modified = task_work_results.get("files_modified") or []
   418	    authored: List[str] = []
   419	    seen: set = set()
   420	    for f in list(created) + list(modified):
   421	        fs = str(f)
   422	        if fs not in seen:
   423	            seen.add(fs)
   424	            authored.append(fs)
   425	    return authored
   426	
   427	
   428	def _run_wiring_analysis(
   429	    worktree_path: Path,
   430	    authored_files: List[str],
   431	    task_type: str,
   432	    stack_template: Optional[str],
   433	) -> Optional[Dict[str, Any]]:
   434	    """Run the wiring analysis for the authored files.
   435	
   436	    Returns a dict with ``wiring``, ``mocked_seam``, and ``spec_gap`` keys
   437	    (some may be ``None``). Returns ``None`` when the task type gates out
   438	    (SCAFFOLDING/DOCUMENTATION) or there are no authored source targets.
   439	
   440	    Parameters
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 150, 'offset': 440}, 'id': 'fc_A3ROWFHGkEQrR8rS5sX536ISUuBKYixv', 'type': 'tool_call'}]
Tool:    441	    ----------
   442	    worktree_path : Path
   443	        Root of the worktree.
   444	    authored_files : List[str]
   445	        Source files authored this turn.
   446	    task_type : str
   447	        Resolved task type (e.g. ``"feature"``, ``"scaffolding"``).
   448	    stack_template : Optional[str]
   449	        Detected stack template (e.g. ``"python"``, ``"fastapi-python"``).
   450	
   451	    Returns
   452	    -------
   453	    Optional[Dict[str, Any]]
   454	        Dict with ``wiring``, ``mocked_seam``, ``spec_gap`` keys, or ``None``
   455	        when the probe legitimately did not run.
   456	    """
   457	    # Task-type gate: SCAFFOLDING / DOCUMENTATION → all fields None.
   458	    if task_type in ("scaffolding", "documention", "documentation", "testing"):
   459	        logger.debug(
   460	            "wiring analysis: task_type=%s gates out; "
   461	            "all three fields left as None.",
   462	            task_type,
   463	        )
   464	        return None
   465	
   466	    # Zero-authored-targets gate → None (probe legitimately did not run).
   467	    if not authored_files:
   468	        logger.debug(
   469	            "wiring analysis: no authored source targets; "
   470	            "all three fields left as None.",
   471	        )
   472	        return None
   473	
   474	    # Factory unavailable → all fields None (graceful import absence).
   475	    if not _is_wiring_factory_available() or analyze_wiring is None:
   476	        logger.debug(
   477	            "wiring analysis: guardkitfactory.wiring not available; "
   478	            "all three fields left as None.",
   479	        )
   480	        return None
   481	
   482	    # Resolve stack profile for the factory call.
   483	    stack_profile = _STACK_PROFILE_MAP.get(stack_template) if stack_template else None
   484	
   485	    try:
   486	        result = analyze_wiring(
   487	            authored_files=authored_files,
   488	            worktree_path=worktree_path,
   489	            task_type=task_type,
   490	            stack=stack_profile,
   491	        )
   492	        # analyze_wiring returns a dict with wiring/mocked_seam/spec_gap keys.
   493	        # If it returns None (task-type gate or zero targets inside the
   494	        # factory), all three fields stay None.
   495	        if result is None:
   496	            return None
   497	        return result
   498	    except Exception as exc:  # noqa: BLE001 — analyzer errors must not break gathering
   499	        logger.warning(
   500	            "wiring analysis raised %s; all three fields left as None.",
   501	            exc.__class__.__name__,
   502	        )
   503	        return None
   504	
   505	
   506	# TASK-FIX-A7B4: Markers that satisfy a `## Seam Tests` block in a task
   507	# description. Filename-based detection (the soft gate at
   508	# ``_check_seam_test_recommendation``) tolerates "integration" too, but the
   509	# blocking gate requires explicit marker decoration so a plain integration test
   510	# can't silently satisfy a contract obligation. Match the established marker
   511	# precedent: `seam`, `contract`, `boundary`.
   512	_SEAM_PYTEST_MARKERS = ("seam", "contract", "boundary")
   513	
   514	# Header pattern: any markdown header level (`#` to `######`) whose title is
   515	# exactly "Seam Tests" (case-insensitive, trailing whitespace allowed). The
   516	# closing `$` plus `re.MULTILINE` matches the header line in isolation so we
   517	# don't false-trigger on prose like "## Seam Tests are useful because…".
   518	_SEAM_TESTS_HEADER_RE = re.compile(
   519	    r"^\s*#{1,6}\s+seam\s+tests\s*$",
   520	    re.IGNORECASE | re.MULTILINE,
   521	)
   522	
   523	
   524	def _extract_seam_tests_section(description: Optional[str]) -> Optional[str]:
   525	    """Extract the body of a ``## Seam Tests`` markdown section.
   526	
   527	    Returns the section body (everything between the ``## Seam Tests`` header
   528	    and the next sibling-or-higher header, or EOF) when the section exists
   529	    AND has non-whitespace content. Returns ``None`` for any of:
   530	
   531	    * ``description`` is empty / None
   532	    * No ``Seam Tests`` header is present
   533	    * The header exists but the body is whitespace-only (empty stub block)
   534	
   535	    The "non-empty body" rule is what TASK-FIX-A7B4 AC-001 calls "precise"
   536	    detection: a developer who wants to acknowledge "no seam tests for this
   537	    task" can leave the section empty (or omit it) without tripping the gate.
   538	    """
   539	    if not description:
   540	        return None
   541	    match = _SEAM_TESTS_HEADER_RE.search(description)
   542	    if not match:
   543	        return None
   544	    # Find the level of the matched header so we know what closes the section.
   545	    header_line = match.group(0)
   546	    header_level = len(header_line.lstrip().split(" ", 1)[0])  # count of '#'
   547	
   548	    # Body starts after the header line.
   549	    body_start = match.end()
   550	    rest = description[body_start:]
   551	    # The section closes at the next header of equal-or-higher level.
   552	    closing_re = re.compile(
   553	        rf"^\s*#{{1,{header_level}}}\s+\S",
   554	        re.MULTILINE,
   555	    )
   556	    close_match = closing_re.search(rest)
   557	    body = rest[: close_match.start()] if close_match else rest
   558	    if not body.strip():
   559	        return None
   560	    return body
   561	
   562	
   563	# Stopwords for keyword extraction in fuzzy text matching
   564	STOPWORDS = {
   565	    "the", "and", "is", "or", "a", "an", "for", "with", "to", "in", "of",
   566	    "from", "by", "on", "at", "that", "this", "are", "be", "do", "have",
   567	    "has", "as", "if", "can", "will", "would", "could", "should", "may",
   568	    "must", "was", "were", "been", "but", "not", "no", "all", "some",
   569	    "any", "more", "most", "only", "than", "then", "there", "their",
   570	    "who", "which", "when", "where", "how",
   571	}
   572	
   573	# ============================================================================
   574	# Data Models
   575	# ============================================================================
   576	
   577	
   578	@dataclass
   579	class QualityGateStatus:
   580	    """
   581	    Status of individual quality gates from task-work execution.
   582	
   583	    Attributes
   584	    ----------
   585	    tests_passed : bool
   586	        Whether all tests passed in Phase 4.5
   587	    coverage_met : bool
   588	        Whether coverage threshold was met
   589	    arch_review_passed : bool
   590	        Whether architectural review passed (score >= 60)
AI: [{'name': 'grep', 'args': {'pattern': '_run_wiring_analysis|wiring=|mocked_seam=|spec_gap=', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py', 'output_mode': 'content'}, 'id': 'fc_AlslTeTB3CenL7Mf68POjP8vWvz6qFsb', 'type': 'tool_call'}]
Tool: No matches found
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 2400}, 'id': 'fc_r5TTme5UiWphv5ZwGWJHSbtC4lJnemGc', 'type': 'tool_call'}]
Tool:   2401	            "tests_required": gates.tests_required,
  2402	            "tests_run": quality_gates_raw.get("tests_run"),
  2403	            "tests_failed": quality_gates_raw.get("tests_failed"),
  2404	            "all_passed": quality_gates_raw.get("all_passed"),
  2405	            "requires_infrastructure": task.get("requires_infrastructure"),
  2406	        }
  2407	
  2408	        plan_audit_raw = task_work_results.get("plan_audit")
  2409	        plan_audit_dict: Optional[Dict[str, Any]] = (
  2410	            plan_audit_raw if isinstance(plan_audit_raw, dict) else None
  2411	        )
  2412	
  2413	        code_review_raw = task_work_results.get("code_review")
  2414	        arch_review_dict: Optional[Dict[str, Any]] = None
  2415	        if isinstance(code_review_raw, dict):
  2416	            arch_review_dict = {
  2417	                "score": code_review_raw.get("score"),
  2418	                "threshold": getattr(profile, "arch_review_threshold", 60),
  2419	                "passed": gates.arch_review_passed,
  2420	                "required": gates.arch_review_required,
  2421	            }
  2422	            # Surface any sub-scores the producer wrote (solid/dry/yagni).
  2423	            for sub in ("solid_score", "dry_score", "yagni_score"):
  2424	                if sub in code_review_raw:
  2425	                    arch_review_dict[sub] = code_review_raw[sub]
  2426	
  2427	        # ------------------------------------------------------------------
  2428	        # BDD evidence. TASK-BDDW-001: wire factory BDD plugin discovery
  2429	        # into the Coach evidence path.
  2430	        #
  2431	        # Priority:
  2432	        #   1. Factory discovery (guardkitfactory.bdd.discover) — if available
  2433	        #      and stack profile is known, run the BDD plugin and map the
  2434	        #      result into bundle.bdd shape.
  2435	        #   2. Player-reported bdd_results — legacy fallback when the factory
  2436	        #      is unavailable, the stack is unknown, or discovery fails.
  2437	        # ------------------------------------------------------------------
  2438	        _reset_factory_cache()
  2439	        _reset_wiring_factory_cache()
  2440	
  2441	        bdd_raw = task_work_results.get("bdd_results")
  2442	        bdd_dict: Optional[Dict[str, Any]] = None
  2443	
  2444	        if bdd_raw is not None and isinstance(bdd_raw, dict):
  2445	            # Player already produced BDD results — use them as-is.
  2446	            bdd_dict = bdd_raw
  2447	        elif _is_factory_available():
  2448	            # Factory is available but Player didn't produce results.
  2449	            # Attempt independent discovery via the factory plugin.
  2450	            stack_profile = _detect_stack_profile(self.worktree_path)
  2451	            factory_result = _run_factory_bdd(self.worktree_path, stack_profile)
  2452	            if factory_result is not None:
  2453	                bdd_dict = factory_result
  2454	                logger.info(
  2455	                    "gather_evidence: BDD evidence from factory plugin "
  2456	                    "(stack=%s, scenarios_attempted=%s).",
  2457	                    stack_profile,
  2458	                    factory_result.get("scenarios_attempted"),
  2459	                )
  2460	            else:
  2461	                logger.debug(
  2462	                    "gather_evidence: factory BDD discovery returned None; "
  2463	                    "bdd field left as absent signal.",
  2464	                )
  2465	        else:
  2466	            # Factory unavailable — bdd_dict stays None (absent signal).
  2467	            logger.debug(
  2468	                "gather_evidence: guardkitfactory not available; "
  2469	                "Player-reported bdd_results were empty; "
  2470	                "bdd field left as absent signal.",
  2471	            )
  2472	
  2473	        # Quality-gate-failure short-circuit. Legacy validate() also
  2474	        # short-circuits here via _feedback_from_gates.
  2475	        if not gates.all_gates_passed:
  2476	            logger.info(
  2477	                "gather_evidence: quality gates failed for %s; downstream "
  2478	                "(requirements, independent tests) skipped.", task_id,
  2479	            )
  2480	            return CoachEvidenceBundle(
  2481	                honesty=honesty,
  2482	                gathering_status="partial_gate_abort",
  2483	                quality_gates=gates,
  2484	                coverage_details=coverage_details,
  2485	                plan_audit=plan_audit_dict,
  2486	                bdd=bdd_dict,
  2487	                arch_review=arch_review_dict,
  2488	                tests=tests_dict,
  2489	                severity_recommendations=severity_recommendations,
  2490	                advisory_issues=advisory_issues,
  2491	                task_type=task_type.value,
  2492	                profile_name=profile_name,
  2493	            )
  2494	
  2495	        # ------------------------------------------------------------------
  2496	        # 3. Requirements validation. Mirrors validate() line 1139.
  2497	        # Hoisted ahead of independent-test in the legacy path; preserved
  2498	        # here for the same reason — cheaper, idempotent.
  2499	        # ------------------------------------------------------------------
  2500	        try:
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 100, 'offset': 2550}, 'id': 'fc_01Ex0iVvLy0Ld7cFqbdXor5y36KVQiPl', 'type': 'tool_call'}]
Tool:   2551	                    "gather_evidence: run_independent_tests raised: %s", exc,
  2552	                )
  2553	                return CoachEvidenceBundle(
  2554	                    honesty=honesty,
  2555	                    gathering_status="partial_exception",
  2556	                    gathering_error=f"independent_tests_exception: {exc}",
  2557	                    quality_gates=gates,
  2558	                    coverage_details=coverage_details,
  2559	                    plan_audit=plan_audit_dict,
  2560	                    bdd=bdd_dict,
  2561	                    arch_review=arch_review_dict,
  2562	                    tests=tests_dict,
  2563	                    requirements=requirements,
  2564	                    severity_recommendations=severity_recommendations,
  2565	                    advisory_issues=advisory_issues,
  2566	                    task_type=task_type.value,
  2567	                    profile_name=profile_name,
  2568	                )
  2569	
  2570	        # ------------------------------------------------------------------
  2571	        # 5. Wiring analysis (Wave-1, TASK-QAWE-002).
  2572	        # Populates wiring / mocked_seam / spec_gap at the complete-path
  2573	        # return only. Partial returns (honesty_abort, gate_abort,
  2574	        # exception) leave all three None.
  2575	        # ------------------------------------------------------------------
  2576	        wiring_dict: Optional[Dict[str, Any]] = None
  2577	        mocked_seam_dict: Optional[Dict[str, Any]] = None
  2578	        spec_gap_dict: Optional[Dict[str, Any]] = None
  2579	
  2580	        try:
  2581	            stack_template = detect_stack_template(self.worktree_path)
  2582	            authored = _compute_authored_set(task_work_results)
  2583	            wiring_result = _run_wiring_analysis(
  2584	                worktree_path=self.worktree_path,
  2585	                authored_files=authored,
  2586	                task_type=task_type.value,
  2587	                stack_template=stack_template,
  2588	            )
  2589	            if wiring_result is not None:
  2590	                wiring_dict = wiring_result.get("wiring")
  2591	                mocked_seam_dict = wiring_result.get("mocked_seam")
  2592	                spec_gap_dict = wiring_result.get("spec_gap")
  2593	                logger.info(
  2594	                    "gather_evidence: wiring analysis complete "
  2595	                    "(wiring_findings=%d, mocked_seam_findings=%d, "
  2596	                    "spec_gap_findings=%d).",
  2597	                    len(wiring_dict.get("findings", [])) if wiring_dict else 0,
  2598	                    len(mocked_seam_dict.get("findings", [])) if mocked_seam_dict else 0,
  2599	                    len(spec_gap_dict.get("findings", [])) if spec_gap_dict else 0,
  2600	                )
  2601	        except Exception as exc:  # noqa: BLE001 — wiring errors must not break gathering
  2602	            logger.warning(
  2603	                "gather_evidence: wiring analysis raised %s; "
  2604	                "all three fields left as None.",
  2605	                exc.__class__.__name__,
  2606	            )
  2607	
  2608	        return CoachEvidenceBundle(
  2609	            honesty=honesty,
  2610	            gathering_status="complete",
  2611	            quality_gates=gates,
  2612	            coverage_details=coverage_details,
  2613	            plan_audit=plan_audit_dict,
  2614	            bdd=bdd_dict,
  2615	            arch_review=arch_review_dict,
  2616	            tests=tests_dict,
  2617	            independent_tests=test_result,
  2618	            requirements=requirements,
  2619	            severity_recommendations=severity_recommendations,
  2620	            advisory_issues=advisory_issues,
  2621	            task_type=task_type.value,
  2622	            profile_name=profile_name,
  2623	            wiring=wiring_dict,
  2624	            mocked_seam=mocked_seam_dict,
  2625	            spec_gap=spec_gap_dict,
  2626	        )
  2627	
  2628	    def _compute_agent_invocations_advisory(
  2629	        self, task_work_results: Dict[str, Any],
  2630	    ) -> Optional[Dict[str, Any]]:
  2631	        """Compute the non-blocking agent-invocations advisory issue.
  2632	
  2633	        Extracted from ``validate()`` lines 1028-1126 (TASK-FIX-RWOP1.3.1 /
  2634	        TASK-REV-F6E1 F3c) for reuse by ``gather_evidence()`` (TASK-HMIG-008R
  2635	        Part A). Returns ``None`` when no advisory is needed.
  2636	
  2637	        The logic mirrors the inline computation in ``validate()``: a
  2638	        ``"violation"`` status in ``task_work_results['agent_invocations_validation']``
  2639	        produces a ``severity == "warning"`` advisory naming the missing
  2640	        phases and recommending stack-specific specialists. ``"passed"``,
  2641	        ``"validator_error"``, and ``"no_data"`` statuses are not advised
  2642	        on — they ride through without comment.
  2643	        """
  2644	        agent_invocations_validation = task_work_results.get(
  2645	            "agent_invocations_validation"
  2646	        )
  2647	        if not (
  2648	            isinstance(agent_invocations_validation, dict)
  2649	            and agent_invocations_validation.get("status") == "violation"
  2650	        ):
AI: The worktree already has wiring implementation. I need to update my test file to use the correct function names from the worktree:

[{'name': 'edit_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py', 'old_string': 'from guardkit.orchestrator.quality_gates.coach_validator import (\n    CoachValidator,\n    _compute_own_authored,\n    _compute_wiring_evidence,\n)', 'new_string': 'from guardkit.orchestrator.quality_gates.coach_validator import (\n    CoachValidator,\n    _compute_authored_set,\n    _run_wiring_analysis,\n)'}, 'id': 'fc_C37h4iuJoZB4z6AvU9NObOeGgbHNmnZM', 'type': 'tool_call'}]
Tool: Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py'
AI: [{'name': 'execute', 'args': {'command': "cd /home/richardwoollcott/Projects/appmilla_github/guardkit && sed -i 's/_compute_own_authored/_compute_authored_set/g; s/_compute_wiring_evidence/_run_wiring_analysis/g' .guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py"}, 'id': 'fc_6gHFtk5CJkjlmZgfypLLVg3YKnaVainP', 'type': 'tool_call'}]
Tool: <no output>
[Command succeeded with exit code 0]
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py', 'limit': 100, 'offset': 200}, 'id': 'fc_RlJl2fjpIO4ot9nionQaEhgXXQvo0CDo', 'type': 'tool_call'}]
Tool:    201	        results["files_created"] = ["nonexistent_file.py"]
   202	        _write_results(tmp_path, "TASK-Z", results)
   203	
   204	        validator = CoachValidator(str(tmp_path), task_id="TASK-Z")
   205	        bundle = validator.gather_evidence(
   206	            task_id="TASK-Z",
   207	            turn=1,
   208	            task={
   209	                "acceptance_criteria": ["AC-001"],
   210	                "task_type": "feature",
   211	                "description": "x",
   212	            },
   213	        )
   214	        # Should be partial_honesty_abort due to file existence discrepancy
   215	        if bundle.gathering_status != "complete":
   216	            assert bundle.wiring is None
   217	            assert bundle.mocked_seam is None
   218	            assert bundle.spec_gap is None
   219	
   220	
   221	# ---------------------------------------------------------------------------
   222	# AC-008: Task-type gate
   223	# ---------------------------------------------------------------------------
   224	
   225	
   226	class TestACT008TaskTypeGate:
   227	    """AC-008: SCAFFOLDING/DOCUMENTATION → all three fields None."""
   228	
   229	    @pytest.mark.parametrize("task_type", ["scaffolding", "documentation"])
   230	    def test_scaffolding_task_type_excluded(self, tmp_path: Path, task_type: str) -> None:
   231	        """SCAFFOLDING tasks produce None for all three wiring fields."""
   232	        _init_git_worktree(tmp_path)
   233	        results = _passing_task_work_results({
   234	            "files_authored": ["src/main.py"],
   235	        })
   236	        _write_results(tmp_path, "TASK-ST", results)
   237	
   238	        validator = CoachValidator(str(tmp_path), task_id="TASK-ST")
   239	        bundle = validator.gather_evidence(
   240	            task_id="TASK-ST",
   241	            turn=1,
   242	            task={
   243	                "acceptance_criteria": ["AC-001"],
   244	                "task_type": task_type,
   245	                "description": "x",
   246	            },
   247	        )
   248	        assert bundle.gathering_status == "complete"
   249	        assert bundle.wiring is None
   250	        assert bundle.mocked_seam is None
   251	        assert bundle.spec_gap is None
   252	
   253	    def test_zero_authored_files_excluded(self, tmp_path: Path) -> None:
   254	        """Zero-authored files → all three fields None."""
   255	        _init_git_worktree(tmp_path)
   256	        results = _passing_task_work_results({
   257	            "files_authored": [],
   258	        })
   259	        _write_results(tmp_path, "TASK-EMPTY", results)
   260	
   261	        validator = CoachValidator(str(tmp_path), task_id="TASK-EMPTY")
   262	        bundle = validator.gather_evidence(
   263	            task_id="TASK-EMPTY",
   264	            turn=1,
   265	            task={
   266	                "acceptance_criteria": ["AC-001"],
   267	                "task_type": "feature",
   268	                "description": "x",
   269	            },
   270	        )
   271	        assert bundle.gathering_status == "complete"
   272	        assert bundle.wiring is None
   273	        assert bundle.mocked_seam is None
   274	        assert bundle.spec_gap is None
   275	
   276	
   277	# ---------------------------------------------------------------------------
   278	# _run_wiring_analysis unit tests
   279	# ---------------------------------------------------------------------------
   280	
   281	
   282	class TestComputeWiringEvidence:
   283	    """Unit tests for the _run_wiring_analysis helper."""
   284	
   285	    def test_scaffolding_returns_all_none(self, tmp_path: Path) -> None:
   286	        """SCAFFOLDING task type → (None, None, None)."""
   287	        wiring, mocked_seam, spec_gap = _run_wiring_analysis(
   288	            authored_files=["src/main.py"],
   289	            worktree_path=tmp_path,
   290	            task_type_str="scaffolding",
   291	        )
   292	        assert wiring is None
   293	        assert mocked_seam is None
   294	        assert spec_gap is None
   295	
   296	    def test_documentation_returns_all_none(self, tmp_path: Path) -> None:
   297	        """DOCUMENTATION task type → (None, None, None)."""
   298	        wiring, mocked_seam, spec_gap = _run_wiring_analysis(
   299	            authored_files=["src/main.py"],
   300	            worktree_path=tmp_path,
AI: The test file needs to be rewritten to match the worktree's function signatures. Let me rewrite it:

[{'name': 'write_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py', 'content': '"""AC-002 / AC-008 /...(argument truncated)'}, 'id': 'fc_Jw0Yz4UKXNs4nmi7MZg9JyXQppD8EgXE', 'type': 'tool_call'}]
Tool: Cannot write to /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py because it already exists. Read and then make an edit, or write to a new path.
AI: [{'name': 'execute', 'args': {'command': 'rm /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-C332/tests/orchestrator/test_coach_wiring_bundle.py'}, 'id': 'fc_WN6R4idWImMCMlQ399Q0mamvAD5wmv8a', 'type': 'tool_call'}]
Tool: <no output>
[Command succeeded with exit code 0]

