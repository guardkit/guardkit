## Summarized at 2026-07-25T23:41:31.651718+00:00

<message type="human">You are executing the implementation phase (Phases 3-5) for TASK-SBHO-001.

## Context

- Task ID: TASK-SBHO-001
- Mode: tdd
- Documentation Level: minimal
- Working directory: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO

## Turn Context

- Current turn: 2
- Max turns: 30
- Turns remaining: 28
- Approaching limit: False

## Task Requirements

# Budget the specialist/advisory prompt seams

## Coach Feedback from Turn 1

- Direct-mode evidence gate blocked the turn (direct_mode_ac_unverified). Direct mode relaxes coverage/arch gates but still requires verifiable AC delivery, resolved wiring, and runnable registered producers:
- [direct_mode_ac_unverified] Direct mode: 4/4 acceptance criteria have no disk evidence (unmet: ['AC-001', 'AC-002', 'AC-003', 'AC-004']). Direct mode relaxes coverage/arch but NOT AC delivery.

Address ALL must_fix items before proceeding.

---

# AutoBuild Execution Protocol

&gt; Focused protocol for Player agent implementation loop (Phases 3–5).
&gt; Extracted from the full task-work specification for efficient context injection.

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
docker rm -f guardkit-test-pg 2&gt;/dev/null || true
docker run -d --name guardkit-test-pg \
  -e POSTGRES_PASSWORD=test \
  -p 5433:5432 postgres:16-alpine
until docker exec guardkit-test-pg pg_isready; do sleep 1; done
export DATABASE_URL=postgresql://postgres:test@localhost:5433/test
```

#### Redis (port 6380)

```bash
docker rm -f guardkit-test-redis 2&gt;/dev/null || true
docker run -d --name guardkit-test-redis \
  -p 6380:6379 redis:7-alpine
sleep 1
export REDIS_URL=redis://localhost:6380
```

#### MongoDB (port 27018)

```bash
docker rm -f guardkit-test-mongo 2&gt;/dev/null || true
docker run -d --name guardkit-test-mongo \
  -p 27018:27017 mongo:7
sleep 2
export MONGODB_URL=mongodb://localhost:27018
```

### Cleanup

When your turn finishes — after Phase 3 and any Phase 4.5 fix-loop iterations — tear down all containers you started:

```bash
docker rm -f guardkit-test-pg guardkit-test-redis guardkit-test-mongo 2&gt;/dev/null || true
```

### When requires_infrastructure is absent

Skip this section entirely. Proceed to Phase 3 as normal.

---

## Phase 3: Implementation

You are implementing a task. Follow these instructions exactly.

### Implementation Requirements

1. **Read the implementation plan** from `.claude/task-plans/TASK-SBHO-001-implementation-plan.md`
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

1. **Load the saved plan** from `.claude/task-plans/TASK-SBHO-001-implementation-plan.md`
2. **Scan actual implementation**: List files created/modified, dependencies added, lines of code
3. **Compare planned vs actual**:
   - Files: Identify extra files not in plan, missing planned files
   - Dependencies: Identify extra or missing dependencies
   - LOC: Calculate percentage variance from estimate
4. **Assess severity**:
   - LOW: &lt;10% variance, no extra files
   - MEDIUM: 10-30% variance, 1-2 extra files
   - HIGH: &gt;30% variance, 3+ extra files, or major deviations

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
`/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.guardkit/autobuild/TASK-SBHO-001/player_turn_2.json`

&lt;!-- Fallback (relative path): .guardkit/autobuild/TASK-SBHO-001/player_turn_2.json --&gt;

### PLAYER_REPORT_SCHEMA

Your report MUST be valid JSON with ALL of these fields.

&gt; **CRITICAL**: You MUST populate `completion_promises` with one entry per acceptance criterion listed in the task file. Do NOT leave this array empty. An empty `completion_promises` array causes the Coach to use text-based fallback matching, which always fails — the autobuild run will stall after 3 turns. If you cannot determine whether a criterion is met, include it with `"status": "uncertain"` and explain in `"evidence"`.

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

&gt; Stubs that pass quality gates are worse than failing code — they silently ship nothing.

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
async def run_system_plan(description: str, mode: str) -&gt; None:
    logger.info(f"run_system_plan called with {description}")
    pass

# NotImplementedError stub
def process_payment(order_id: str, amount: float) -&gt; PaymentResult:
    raise NotImplementedError("Payment processing not yet implemented")

# hardcoded default stub
def get_user_preferences(user_id: str) -&gt; dict:
    return {}

# TODO-only stub
def validate_input(data: dict) -&gt; ValidationResult:
    # TODO: implement validation logic
    return ValidationResult(valid=True, errors=[])
```

### Non-Stub Examples (ACCEPTED)

```python
# Real implementation with logic
async def run_system_plan(description: str, mode: str) -&gt; None:
    detected_mode = detect_mode(description) if mode is None else mode
    questions = generate_questions(detected_mode, description)
    answers = await collect_answers(questions)
    plan = build_plan(detected_mode, answers)
    await write_plan_files(plan)

# Thin wrapper (NOT a stub — legitimate delegation)
@click.command()
@click.argument("description")
def system_plan(description: str) -&gt; None:
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
   - /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SBHO-001-implementation-plan.md
   - /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SBHO-001-implementation-plan.json
   - /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/docs/state/TASK-SBHO-001/implementation_plan.md
   - /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/docs/state/TASK-SBHO-001/implementation_plan.json
</message>
<message type="ai">
  <tool_call id="fc_NUaHwwgyqDLZ7u0oawIZcvzS2ZlAEVw4" name="glob">{"pattern": "**/TASK-SBHO-001*", "path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO"}</tool_call>
  <tool_call id="fc_Xg6MRFdVuUt5U0MLqvME3FBHPGtt04RT" name="glob">{"pattern": "**/*.md", "path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans"}</tool_call>
</message>
<message type="tool">['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SBHO-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tasks/design_approved/TASK-SBHO-001-specialist-prompt-budget.md']</message>
<message type="tool">['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-010-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-020-verification-report.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-023-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-037-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-040-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-045-complexity-evaluation.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-045-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-046-complexity-evaluation.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-046-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-046-plan-audit.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-047-architectural-review.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-047-execution-report.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-047-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-049-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-050-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-054-architectural-review.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-054-code-review.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-054-completion-report.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-054-complexity-evaluation.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-054-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-054-plan-audit.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-054-test-enforcement-report.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-056-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-060-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-062-test-summary.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-065-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-AB-9869-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-AB-A76A-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-ABL1-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-ABSR-WTKS-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-BDD-F3EA-implementation-summary.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-BDDW-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-BDDW-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-BRIDGE-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-BRIDGE-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-BRIDGE-003-plan-audit.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-C5AC-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-C7A9-test-execution-summary.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-CMIR-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-CMIR-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-CMIR-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-CRS-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-DFFA-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-DM-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-DM-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-DM-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-DM-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-DM-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-DM-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-DM-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-DM-008-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-DOC-F3BA-review-report.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-ENF3-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FB-FIX-010-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FB-FIX-b41d-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FBSDK-014-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FBSDK-018-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FBSDK-024-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FC-005-architectural-review.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FDB2-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FIX-40B4-INDEX.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FIX-40B4-QUICK-REFERENCE.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FIX-40B4-design-summary.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FIX-40B4-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FIX-40B4-python-patterns-reference.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FIX-ARIMPL-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FIX-BDDVAL-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FMT-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FMT-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FMT-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FMT-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FMT-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FMT-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FP002-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FP002-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FP002-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FP002-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FP002-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FP002-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FP002-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FP002-008-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FP002-009-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FP002-010-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FP002-011-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FW-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-FW-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GE-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GE-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GE-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GE-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GE-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GE-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GI-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GI-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GI-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GI-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GI-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GI-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GI-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-001-A-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-001-B-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-001-C-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-001-D-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-001-E-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-001-F-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-001-G-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-001-H-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-001-I-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-002-A-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-002-B-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-002-C-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-002-D-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-002-E-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-002-F-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-002-G-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-002-H-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-PRE-000-A-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-PRE-000-B-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-PRE-001-A-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-PRE-001-B-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-PRE-001-C-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-PRE-002-A-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-PRE-002-B-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-PRE-002-C-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-PRE-003-A-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-PRE-003-B-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR-PRE-003-C-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR3-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR3-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR3-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR3-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR3-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR4-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR4-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR4-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR4-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR4-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR4-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR4-008-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR5-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR5-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR5-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR5-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR5-008-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR5-009-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR6-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR6-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR6-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR6-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR6-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR6-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR6-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR6-008-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR6-009-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR6-011-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR6-012-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-GR6-013-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-HARV-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-HARV-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-HARV-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-IMP-TC-F8A3-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-005a-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-005b-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-005c-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-008-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-009-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-010-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-011-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-INST-012-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MCP-C1C1-test-report.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MEM08-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MEM08-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MEM08-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MEM08-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MEM08-008-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MEM08-009-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MTS-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MTS-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MTS-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MTS-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MTS-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MTS-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MTS-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MTS-008-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MTS-009-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MTS-010-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-MTS-011-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-OBS-396E-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-OBS-4899-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-OBS-80FE-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-OBS-9F43-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-OBS-C440-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-OBS-F3F5-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-PD-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-PD-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-QAV-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-QAV-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-QAV-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-QAV-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-QAV-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-QAV-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-QAWE-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-QAWE-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-QAWE-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SAD-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SAD-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SAD-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SAD-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SAD-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SAD-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SAD-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SAD-008-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SAD-009-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SAD-010-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SBHO-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SBHO-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SC-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SC-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SC-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SC-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SC-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SC-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SC-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SC-008-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SC-009-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SC-010-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SC-011-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SEC-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SEC-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SEC-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SEC-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SEC-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SELFFIX-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SELFFIX-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SELFFIX-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SFT-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SFT-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SFT-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SFT-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SFT-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SFT-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SFT-008-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SFT-009-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SFT-011-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SP-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SP-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SP-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SP-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SP-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SP-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SP-007-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SP-008-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-TEST-MCP1-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-TMPL-4E89-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-TMPL-4E89-test-verification-report.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-TMPL-CE54-completion-report.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-TMPL-CE54-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-TMPL-CE54-implementation-summary.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-TPL-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-TPL-003-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-TPL-004-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-TPL-005-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-TPL-006-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-TSJ-001-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-UX-3A8D-completion-report.md']</message>
<message type="ai">
  <tool_call id="fc_sBl7xvNWfwBzj3qQZIdcuRFPLQa1wCKq" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tasks/design_approved/TASK-SBHO-001-specialist-prompt-budget.md"}</tool_call>
  <tool_call id="fc_DjE4RRq3FAiOYtFHOcP9REzsWN8hbZej" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.claude/task-plans/TASK-SBHO-001-implementation-plan.md"}</tool_call>
</message>
<message type="tool">     1	---
     2	complexity: 4
     3	dependencies: []
     4	feature_id: FEAT-SBHO
     5	id: TASK-SBHO-001
     6	implementation_mode: task-work
     7	status: design_approved
     8	task_type: feature
     9	title: Budget the specialist/advisory prompt seams
    10	wave: 1
    11	---
    12	
    13	# Budget the specialist/advisory prompt seams
    14	
    15	The FEAT-8AD1 merge (58bc42b6) filed this follow-up: the code-reviewer specialist prompt
    16	is a SEPARATE seam from the coach synthesis budget (3 live overflow receipts,
    17	advisory/non-fatal) — same budget owed. Two seams are unbudgeted today:
    18	guardkit/qa/review_seat.py::build_seat_messages (:319-338 — only the diff is capped at
    19	60k; repo_context and the assembled payload are unbounded) and
    20	guardkit/orchestrator/specialist_invocations.py::_build_code_reviewer_prompt (:886-936 —
    21	a ~2000-char seed cap only). Mirror the _trim_synthesis_prompt pattern
    22	(agent_invoker.py:3402-3665): env-tunable ceiling, protected sections, loud in-prompt
    23	truncation marker + WARNING log, degrade never raise. Binding spec:
    24	docs/specialist-budget-and-holdout-scope-and-buildplan.md §2.
    25	
    26	## Acceptance Criteria
    27	- [ ] GUARDKIT_REVIEW_SEAT_MAX_CHARS (default 300000) bounds the ASSEMBLED review-seat user message: a hermetic test builds an oversized payload (huge repo_context + big diff) and asserts the assembled message fits the budget, contains the loud truncation marker, trims repo_context before the diff, and never trims the instruction header or the finding-schema section
    28	- [ ] GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS (default 300000) backstops the final prompt for the specialist builders in specialist_invocations.py; the existing ~2000-char seed-cap behaviour is unchanged when under budget
    29	- [ ] Advisory/non-fatal contracts unchanged: run_advisory_review still never raises and never returns blocking=True (existing tests pass unmodified); a WARNING log fires on any trim
    30	- [ ] Zero net-new failures on the existing suite; both new tests are hermetic (no model calls)</message>
<message type="tool">     1	# Implementation Plan: TASK-SBHO-001
     2	
     3	## Task
     4	Budget the specialist/advisory prompt seams
     5	
     6	## Plan Status
     7	**Auto-generated stub** - Pre-loop was skipped for this feature task.
     8	Generated: 2026-07-26T00:13:13.363817
     9	
    10	## Implementation
    11	Follow acceptance criteria in task file.
    12	
    13	## Notes
    14	This plan was auto-generated because the task was created via /feature-plan
    15	with pre-loop disabled (enable_pre_loop=False).
    16	The detailed specifications are in the task markdown file.</message>
<message type="ai">
  <tool_call id="fc_MZNEbBRWKN9AkjCWEFw528SmHK6FJC0L" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/docs/specialist-budget-and-holdout-scope-and-buildplan.md"}</tool_call>
  <tool_call id="fc_yBWlg3cPmDFjuxo4FmPhEWuvPVIbYzB7" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/qa/review_seat.py"}</tool_call>
  <tool_call id="fc_BwxNsVFxFNTdOUPpBkhy9iqp70ejG5Qn" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/orchestrator/specialist_invocations.py"}</tool_call>
</message>
<message type="tool">     1	# Specialist-prompt budget + hold-out relocation — scope + buildplan (FEAT-SBHO)
     2	## 2026-07-25 night · the two small guardkit lanes combined per the handoff §3.1 · binding spec
     3	
     4	## 1. Why (receipts)
     5	
     6	- **Specialist budget:** the FEAT-8AD1 merge (`58bc42b6`) filed this follow-up verbatim:
     7	  *"the code-reviewer specialist prompt is a SEPARATE seam (3 live overflow receipts,
     8	  advisory/non-fatal) — same budget owed, its own small lane."* No task was ever filed —
     9	  this build files and closes it.
    10	- **Hold-out relocation:** ruled by Rich from the verification research
    11	  (ai-transition `docs/verification-deep-dives-dossier-2026-07-25.md` Dive 3): the Player
    12	  can currently read the full Coach evidence dossier out of the shared worktree —
    13	  `coach_evidence_turn_{turn}.json` is written to
    14	  `worktree/.guardkit/autobuild/{task_id}/` (`autobuild.py:6766-6787`) and the Player runs
    15	  with unrestricted Read/Grep/Bash in that worktree (`agent_invoker.py:2077`). Measures M2.
    16	
    17	## 2. Fix A — budget the specialist/advisory prompt seams (TASK-SBHO-001)
    18	
    19	Mirror the `_trim_synthesis_prompt` pattern (`agent_invoker.py:3402-3665`: env-tunable
    20	char ceiling, protected markers, loud in-prompt truncation notice + WARNING log, degrade
    21	never raise) onto the two unbudgeted seams:
    22	
    23	1. `guardkit/qa/review_seat.py::build_seat_messages` (:319-338): the assembled
    24	   system+user payload has NO overall budget today (only the diff is capped at 60k via
    25	   `render_payload_for_seat`; `repo_context` is uncapped). Add
    26	   `GUARDKIT_REVIEW_SEAT_MAX_CHARS` (default 300000) bounding the ASSEMBLED user
    27	   message; trim `repo_context` first, then the diff tail; never trim the instruction
    28	   header or the finding-schema section. Advisory posture unchanged (never raises,
    29	   never blocks — `run_advisory_review` :711-799 contract intact).
    30	2. `guardkit/orchestrator/specialist_invocations.py::_build_code_reviewer_prompt`
    31	   (:886-936): keep the existing ~2000-char seed cap, and add the same env-tunable
    32	   overall bound as a backstop (`GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS`, default 300000)
    33	   applied to the final prompt string for ALL specialist builders in this module
    34	   (code-reviewer, test-orchestrator runner), with the loud-marker convention.
    35	
    36	## 3. Fix B — hold-out relocation (TASK-SBHO-002), the Dive-3 named set
    37	
    38	1. **(S)** `coach_evidence_turn_{turn}.json` moves OUT of the worktree to an
    39	   orchestrator-private dir: `&lt;repo-root&gt;/.guardkit/autobuild-private/{task_id}/`
    40	   (host-side, sibling of the worktree root, never inside `worktree.path`). Writer:
    41	   `autobuild.py:6766-6787`. All readers (shadow mode, receipts, review summary) follow
    42	   the new path via one accessor in `guardkit/orchestrator/paths.py` — no scattered
    43	   literals.
    44	2. **(M)** `coach_turn_{turn}.json` (the full verdict) moves to the same private dir.
    45	   The worktree keeps ONLY the designed Player-facing feedback file
    46	   (`coach_feedback_*.json`), which already carries the redacted
    47	   issue/location/suggestion view (`_write_coach_feedback`, `agent_invoker.py:7164-7198`).
    48	   `coach_output_parser.extract_and_write` writes to the private dir; the COACHSF01
    49	   safety net and `load_coach_feedback` keep working (update their path resolution via
    50	   the same accessor).
    51	3. **(S)** Oracle-failure feedback names the scenario/AC id, not the oracle file path
    52	   (strip worktree-relative oracle paths from Player-facing feedback text).
    53	4. Player prompt text: remove any references that hand the Player coach-artifact paths
    54	   beyond the feedback file.
    55	
    56	**Honest cap (from Dive 3, restated):** this removes the casual read and the path hint,
    57	not a determined process — the Player's Bash is unrestricted at the host. Full
    58	enforcement is a separate sandbox lane. Say so in code comments at the seam.
    59	
    60	**Compat law:** backward-compatible READ fallback — if a legacy-located file exists and
    61	the private one doesn't (old runs, replays), readers fall back with a log line. Fresh
    62	writes always go private.
    63	
    64	## 4. Done means
    65	
    66	- Both lane suites green + zero net-new failures vs main.
    67	- Hermetic tests: (a) an oversized review-seat payload renders under the budget with the
    68	  loud marker and untouched instruction header; (b) a specialist prompt over the ceiling
    69	  is bounded; (c) after a simulated coach turn, `worktree/.guardkit/autobuild/{task}/`
    70	  contains NO `coach_evidence_*` or `coach_turn_*` file, the private dir contains both,
    71	  and the feedback file still round-trips through `load_coach_feedback`; (d) the legacy
    72	  read-fallback fires with its log line.
    73	- Advisory/non-fatal behaviour of the review seat and specialist results is unchanged.
    74	
    75	## 5. Fences
    76	
    77	Normal topology. No changes to the coach contract surfaces (FEAT-CV4M owns those; this
    78	build must not touch `_build_coach_prompt`, `coach_output_parser` parse logic, or
    79	grammars beyond the file-path seam in §3.2).</message>
<message type="tool">     1	"""F14 emission for the R-b code-review seat (S3, 2026-07-13).
     2	
     3	Design source (binding): ``ai-transition/docs/factory-code-quality-seat-options-
     4	2026-07.md`` — R-b build-lane sketch stage **S-3**: "Command emits an F14
     5	review-findings record; wired **default-OFF** behind a flag mirroring
     6	``qa.enforce_tier1``; advisory placement first." This module is that emission
     7	layer, and only that.
     8	
     9	The chain it closes:
    10	
    11	  S-1 (``diff_ingest.ReviewPayload``)  ─┐
    12	                                        ├─▶  local seat  ─▶  F14 ``ReviewFindings``
    13	  S-2 (review dimensions + discipline) ─┘   (llama-swap)      (``review_findings.py``)
    14	
    15	Four invariants this stage pins:
    16	
    17	- **Default-OFF, advisory-only (mirrors ``enforcement.is_tier1_enforced``).**
    18	  The emitter is gated on ``qa.review_seat`` (``.guardkit/config.yaml``, default
    19	  ``False``; env override ``GUARDKIT_QA_REVIEW_SEAT``). When OFF it is a *provable
    20	  no-op*: it never touches the seat, never writes a record, never fires a reader.
    21	  When ON it EMITS a record but **never fails a flow** — a seat outage or a parse
    22	  error is a NAMED result field, never a raise. Promotion to *blocking* is the
    23	  S-4 calibration gate (Rich's bar), outside this module.
    24	
    25	- **F14's honesty rules bind (``review_findings.py`` rules, LPA-14/LPA-15).** A
    26	  ``confirmed`` verdict REQUIRES an executed reproduction — and **this seat has no
    27	  execution channel** (the S-2 player prompt forbids tool use), so a
    28	  reading-only seat can never *earn* ``confirmed``. Every emitted finding is
    29	  therefore ``refuted`` (the not-yet-confirmed bucket): "reading is not a
    30	  verdict". A seat that *claims* a reproduction it could not have run is not
    31	  trusted (``trust_seat_reproduction=False``, the lane default). Critical/high
    32	  severity is default-refuted: a finding the seat did not defend with ≥2 refuters
    33	  is DOWNGRADED to ``medium`` (we never fabricate refuters), never dropped
    34	  silently — the downgrade is annotated on the finding.
    35	
    36	- **Local seats only, single-slot-checked (DF-001 + the ``-np 1`` law).** Every
    37	  seat call goes to llama-swap (``localhost:9000``, OpenAI-compatible); the
    38	  allowed seats are ``qwen36-workhorse`` / ``gemma4-coach``. Before a call the
    39	  emitter probes ``/running`` and, if a factory drive is mid-generation on the
    40	  single slot, WAITS (bounded) rather than colliding. Calls are bounded
    41	  (``temperature=0.0``, capped tokens, a timeout).
    42	
    43	- **Honesty-to-state.** A measured emission is recorded as measured; a seat that
    44	  could not be reached or whose output could not be parsed produces an outcome
    45	  with ``record=None`` and a named ``error`` — never a fabricated empty-green
    46	  review.
    47	"""
    48	
    49	from __future__ import annotations
    50	
    51	import json
    52	import logging
    53	import os
    54	import re
    55	import time
    56	import urllib.error
    57	import urllib.request
    58	from dataclasses import dataclass, field, replace
    59	from datetime import datetime, timezone
    60	from pathlib import Path
    61	from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
    62	
    63	import yaml
    64	
    65	from guardkit.qa.diff_ingest import (
    66	    DiffIngestError,
    67	    FileDiff,
    68	    ReviewPayload,
    69	    ingest_commit,
    70	    ingest_merge,
    71	)
    72	from guardkit.qa.formats.review_findings import (
    73	    Finding,
    74	    ReviewFindings,
    75	    ReviewStats,
    76	    ReviewSubject,
    77	)
    78	
    79	logger = logging.getLogger(__name__)
    80	
    81	__all__ = [
    82	    "REVIEW_SEAT_ENV",
    83	    "is_review_seat_enabled",
    84	    "ALLOWED_SEATS",
    85	    "DEFAULT_SEAT",
    86	    "DEFAULT_BASE_URL",
    87	    "CANONICAL_DIMENSIONS",
    88	    "SeatCall",
    89	    "RunningProbe",
    90	    "ReviewOutcome",
    91	    "render_payload_for_seat",
    92	    "build_seat_messages",
    93	    "check_single_slot",
    94	    "emit_review_findings",
    95	    "run_advisory_review",
    96	    "PayloadFactory",
    97	    "FindingRouter",
    98	    "default_merge_candidate_payload",
    99	    "run_review_gate_step",
   100	]</message>
<message type="tool">     1	"""Orchestrator-side specialist runners for AutoBuild Phases 4 and 5.
     2	
     3	This module houses the orchestrator-driven specialist invocations that
     4	replace the Player LLM's discretionary ``Task(subagent_type=...)`` calls.
     5	Wave 1 of the OSI feature shipped the skeleton — the result dataclass
     6	and the shared :func:`run_specialist` helper. Wave 2 added
     7	:func:`invoke_test_orchestrator` (Phase 4) and Wave 3 adds
     8	:func:`invoke_code_reviewer` (Phase 5). Both runners call
     9	:func:`run_specialist` to delegate into
    10	:class:`AgentInvoker._invoke_with_role` via composition.
    11	
    12	References:
    13	
    14	* TASK-OSI-001 — this module skeleton.
    15	* TASK-OSI-004 — :func:`invoke_test_orchestrator`.
    16	* TASK-OSI-005 — :func:`invoke_code_reviewer`.
    17	* TASK-REV-119C1 — review that scoped the orchestrator-side invocation
    18	  redesign and locked in the contract documented in
    19	  ``tasks/in_progress/orchestrator-side-specialist-invocation/IMPLEMENTATION-GUIDE.md``.
    20	"""
    21	
    22	from __future__ import annotations
    23	
    24	import asyncio
    25	import json
    26	import logging
    27	import os
    28	import re
    29	import threading
    30	import time
    31	from dataclasses import dataclass
    32	from pathlib import Path
    33	from typing import TYPE_CHECKING, Any, Literal, Optional
    34	
    35	from guardkit.lib.pytest_summary import parse_pytest_summary
    36	
    37	if TYPE_CHECKING:
    38	    from guardkit.orchestrator.agent_invoker import AgentInvoker
    39	
    40	logger = logging.getLogger(__name__)
    41	
    42	# Directories under the worktree root where a task markdown may live.
    43	# rglob is used inside each so feature-grouped subfolders (e.g.
    44	# ``tasks/in_progress/orchestrator-side-specialist-invocation/``) are
    45	# also searched.
    46	_TASK_SEARCH_DIRS: tuple[str, ...] = (
    47	    "tasks/in_progress",
    48	    "tasks/backlog",
    49	    "tasks/in_review",
    50	    "tasks/blocked",
    51	)
    52	
    53	# Defaults used when ``phase_4_summary.json`` is missing, malformed, or
    54	# the run failed/skipped. Kept as a module constant so the same defaults
    55	# apply to every code path that produces a phase_4 block.
    56	_PHASE_4_AGENT_FIELD_DEFAULTS: dict[str, Any] = {
    57	    "tests_run": 0,
    58	    "tests_failed": 0,
    59	    "coverage_pct": 0.0,
    60	    "output_summary": "",
    61	    "quality_gates_passed": False,
    62	}
    63	
    64	# Phase 5 agent-derived field defaults. The orchestrator-side code-reviewer
    65	# specialist runs without ``Write`` (review must NOT modify source files), so
    66	# the runner can't read structured review output from a sidecar file the way
    67	# Phase 4 does with ``phase_4_summary.json``. These defaults keep the §4.1
    68	# specialist_results.json schema well-formed while real review content flows
    69	# through the SDK message stream / instrumentation.
    70	_PHASE_5_AGENT_FIELD_DEFAULTS: dict[str, Any] = {
    71	    "issues": [],
    72	    "quality_score": 0.0,
    73	    "recommendations": [],
    74	    "output_summary": "Review completed by orchestrator-invoked code-reviewer.",
    75	}
    76	
    77	# Per-specialist SDK-timeout ceiling for the Phase 4 test-orchestrator.
    78	#
    79	# The caller-supplied ``sdk_timeout`` is shared with Player/Coach and can
    80	# reach 2340s on the canary batch. The test-orchestrator specialist has
    81	# been observed to launch ``pytest`` with ``Bash run_in_background=true``
    82	# then poll ``TaskOutput`` every ~30s until the SDK timeout fires —
    83	# burning ~38min per turn even when pytest itself would finish in &lt;2min
    84	# (TASK-HMIG-009A AC-003 rep 1, 2026-06-03; see
    85	# ``docs/reviews/autobuild-migration/long-run-1.md``). The cap is a hard
    86	# orchestrator-side ceiling that converts the SDK timeout into a graceful
    87	# specialist failure at the 10-minute mark instead of letting it consume
    88	# the full Player/Coach budget. Suites that legitimately need &gt;600s
    89	# should be decomposed at the task level, not papered over here.
    90	_TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS: int = 600
    91	
    92	# TASK-PERF-SPECLAT01: per-specialist SDK-timeout ceiling for the Phase 5
    93	# code-reviewer.
    94	#
    95	# The code-reviewer is an *agentic* read-only specialist (Read/Grep/Search)
    96	# that makes many tool round-trips and never self-terminates — on a slow
    97	# locally-served model it runs to whatever ``sdk_timeout`` it is handed. Before
    98	# this cap existed the only bound was the wall clamp in
    99	# ``AgentInvoker``-derived ``_cap_specialist_timeout``; with the (large) default
   100	# ``COACH_GRACE_PERIOD_SECONDS`` reservation that left ~2130s available, so</message>
<message type="ai">
  <tool_call id="fc_FyWs96li6kZFZ3jrRC3uUgmK5N9zir6c" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/qa/review_seat.py", "offset": 280, "limit": 150}</tool_call>
  <tool_call id="fc_p3tcbcH6ss3ug0OYe2rQINx5e2rGTo6l" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/orchestrator/specialist_invocations.py", "offset": 860, "limit": 120}</tool_call>
  <tool_call id="fc_EXhs4LYvtdOD2UfJsMvk0ogjRGJw8bhq" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/orchestrator/agent_invoker.py", "offset": 3380, "limit": 300}</tool_call>
</message>
<message type="tool">   281	    reviewer sees it exists. Truncated at ``max_chars`` with an explicit marker
   282	    (honesty-to-state: a clipped diff says so, it is never silently short).
   283	    """
   284	    lines: List[str] = []
   285	    for fd in payload.files:
   286	        lines.append(_render_file_header(fd))
   287	        if fd.is_binary:
   288	            lines.append("(binary file — not shown)")
   289	            continue
   290	        for hunk in fd.hunks:
   291	            lines.append(hunk.header if hunk.header else _synth_hunk_header(hunk))
   292	            for dl in hunk.lines:
   293	                marker = {"added": "+", "removed": "-", "context": " "}[dl.kind]
   294	                lines.append(f"{marker}{dl.content}")
   295	    text = "\n".join(lines)
   296	    if len(text) &gt; max_chars:
   297	        text = (
   298	            text[:max_chars]
   299	            + f"\n... [diff truncated at {max_chars} chars for the review seat "
   300	            f"— {len(text) - max_chars} more chars not shown]"
   301	        )
   302	    return text
   303	
   304	
   305	def _render_file_header(fd: FileDiff) -&gt; str:
   306	    old = fd.old_path or "/dev/null"
   307	    new = fd.path or "/dev/null"
   308	    return f"diff --git a/{old} b/{new}  [{fd.change_kind}]"
   309	
   310	
   311	def _synth_hunk_header(hunk: Any) -&gt; str:
   312	    head = (
   313	        f"@@ -{hunk.old_start},{hunk.old_count} "
   314	        f"+{hunk.new_start},{hunk.new_count} @@"
   315	    )
   316	    return head + (f" {hunk.section_heading}" if hunk.section_heading else "")
   317	
   318	
   319	def build_seat_messages(
   320	    payload: ReviewPayload, *, repo_context: Optional[str] = None
   321	) -&gt; Tuple[str, str]:
   322	    """Assemble the (system, user) messages for the reviewer seat.
   323	
   324	    The user message carries the review subject, an optional repo-context
   325	    section, and the rendered diff. The system message is the self-contained
   326	    S-2 review contract (dimensions + F14 discipline + JSON shape).
   327	    """
   328	    diff_text = render_payload_for_seat(payload)
   329	    sections: List[str] = [
   330	        f"## Review subject\n\nkind: {payload.subject_kind} · ref: {payload.ref}",
   331	    ]
   332	    if repo_context and repo_context.strip():
   333	        sections.append("## Repository context (reference)\n\n" + repo_context.strip())
   334	    sections.append(
   335	        "## Diff under review (review ONLY these changes)\n\n"
   336	        + (diff_text if diff_text.strip() else "(empty diff — nothing changed)")
   337	    )
   338	    return _REVIEW_SYSTEM, "\n\n".join(sections)
   339	
   340	
   341	# ===========================================================================
   342	# 2. Single-slot guard (the -np 1 law — never collide with a live drive).
   343	# ===========================================================================
   344	
   345	
   346	def _default_running_probe(base_url: str) -&gt; RunningProbe:
   347	    """Build a ``/running`` probe from the seat base URL (``.../v1`` -&gt; ``/running``)."""
   348	    root = base_url.rstrip("/")
   349	    if root.endswith("/v1"):
   350	        root = root[: -len("/v1")]
   351	    running_url = root + "/running"
   352	
   353	    def _probe() -&gt; Optional[List[Dict[str, Any]]]:
   354	        try:
   355	            with urllib.request.urlopen(running_url, timeout=5) as resp:  # noqa: S310
   356	                data = json.loads(resp.read().decode("utf-8"))
   357	        except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
   358	            return None
   359	        running = data.get("running") if isinstance(data, dict) else None
   360	        return running if isinstance(running, list) else None
   361	
   362	    return _probe
   363	
   364	
   365	def check_single_slot(
   366	    running: Optional[Sequence[Dict[str, Any]]],
   367	) -&gt; Tuple[bool, str]:
   368	    """Decide whether the single seat slot is free to call.
   369	
   370	    ``running`` is the parsed ``/running`` list. Returns ``(free, reason)``.
   371	    An unreachable probe (``None``) is NOT read as busy — we proceed and let the
   372	    seat call itself surface any outage. A seat entry whose state names active
   373	    generation (``processing`` / ``busy`` / ``generating``) means a factory
   374	    drive holds the single slot: not free.
   375	    """
   376	    if running is None:
   377	        return True, "running-probe unreachable — proceeding (seat call will report any outage)"
   378	    busy = [
   379	        str(e.get("model", "?"))
   380	        for e in running
   381	        if isinstance(e, dict) and str(e.get("state", "")).strip().lower() in _BUSY_STATES
   382	    ]
   383	    if busy:
   384	        return False, f"seat slot held by a live drive: {', '.join(busy)}"
   385	    return True, "seat slot free"
   386	
   387	
   388	def _await_free_slot(
   389	    running_probe: RunningProbe,
   390	    *,
   391	    retry_max: int = _SLOT_RETRY_MAX,
   392	    retry_sleep_s: float = _SLOT_RETRY_SLEEP_S,
   393	    sleep: Callable[[float], None] = time.sleep,
   394	) -&gt; str:
   395	    """Wait (bounded) for the single slot, honouring the ``-np 1`` law.
   396	
   397	    Returns a human note describing the outcome. If the slot never frees within
   398	    the retry budget we PROCEED anyway (llama-swap serialises the request on the
   399	    slot — the worst case is queueing, never corruption) and say so; this is an
   400	    advisory lane, it must not hang a flow forever.
   401	    """
   402	    for attempt in range(retry_max + 1):
   403	        free, reason = check_single_slot(running_probe())
   404	        if free:
   405	            return reason if attempt == 0 else f"{reason} (after {attempt} wait(s))"
   406	        if attempt &lt; retry_max:
   407	            logger.info("review seat: %s — waiting %.0fs", reason, retry_sleep_s)
   408	            sleep(retry_sleep_s)
   409	    return (
   410	        f"seat slot still contended after {retry_max} wait(s) — proceeding "
   411	        f"(request will queue on the single slot)"
   412	    )
   413	
   414	
   415	# ===========================================================================
   416	# 3. Default seat call (OpenAI-compatible llama-swap — the impure edge).
   417	# ===========================================================================
   418	
   419	
   420	def _default_seat_call(
   421	    base_url: str = DEFAULT_BASE_URL,
   422	    *,
   423	    temperature: float = _DEFAULT_TEMPERATURE,
   424	    max_tokens: int = _DEFAULT_MAX_TOKENS,
   425	    timeout_s: float = _DEFAULT_TIMEOUT_S,
   426	) -&gt; SeatCall:
   427	    """Build a bounded OpenAI-compatible seat call against llama-swap.
   428	
   429	    Imported lazily so the module has no hard ``openai`` dependency for the
   430	    pure/flag paths (unit tests inject their own ``SeatCall`` and never import</message>
<message type="tool">   861	    if not isinstance(data, dict):
   862	        return merged
   863	    block = data.get("phase_4")
   864	    if not isinstance(block, dict):
   865	        return merged
   866	
   867	    for key, default in _PHASE_4_AGENT_FIELD_DEFAULTS.items():
   868	        if key not in block:
   869	            continue
   870	        value = block[key]
   871	        if isinstance(default, bool) and isinstance(value, bool):
   872	            merged[key] = value
   873	        elif isinstance(default, int) and not isinstance(default, bool):
   874	            if isinstance(value, bool):
   875	                continue
   876	            if isinstance(value, int):
   877	                merged[key] = value
   878	        elif isinstance(default, float):
   879	            if isinstance(value, (int, float)) and not isinstance(value, bool):
   880	                merged[key] = float(value)
   881	        elif isinstance(default, str) and isinstance(value, str):
   882	            merged[key] = value
   883	    return merged
   884	
   885	
   886	def _build_code_reviewer_prompt(
   887	    task_id: str,
   888	    task_context: str,
   889	    phase_4_summary: dict[str, Any],
   890	) -&gt; str:
   891	    """Render the prompt the code-reviewer specialist receives.
   892	
   893	    The agent definition (``installer/core/agents/code-reviewer.md``)
   894	    already encodes the review checklist. This prompt only carries
   895	    task-specific context plus the structured Phase 4 summary so the
   896	    reviewer can ground its review in the actual test outcomes.
   897	
   898	    The string ``"Phase 4 summary"`` is part of the prompt contract — the
   899	    unit test introspects for it (TASK-OSI-005 AC d).
   900	    """
   901	    summary_lines = (
   902	        f"- tests_run: {phase_4_summary.get('tests_run', 0)}\n"
   903	        f"- tests_failed: {phase_4_summary.get('tests_failed', 0)}\n"
   904	        f"- coverage_pct: {phase_4_summary.get('coverage_pct', 0.0)}\n"
   905	        f"- quality_gates_passed: "
   906	        f"{phase_4_summary.get('quality_gates_passed', False)}\n"
   907	        f"- output_summary: {phase_4_summary.get('output_summary', '')}"
   908	    )
   909	
   910	    prompt = (
   911	        f"You are the code-reviewer specialist for task {task_id}.\n\n"
   912	        "Task context (from the task markdown):\n"
   913	        f"{task_context}\n\n"
   914	        "Phase 4 summary (test-orchestrator outcome):\n"
   915	        f"{summary_lines}\n\n"
   916	        "Your job:\n"
   917	        "1. Review the implementation in the worktree against the task's "
   918	        "acceptance criteria using Read/Search/Grep.\n"
   919	        "2. Apply the review checklist from your agent definition (build, "
   920	        "requirements, code quality, testing, security, performance, "
   921	        "documentation).\n"
   922	        "3. Report findings via your normal response stream — the "
   923	        "orchestrator records the review outcome in specialist_results.json.\n"
   924	        "Do NOT modify source files: the Write tool is intentionally "
   925	        "withheld from this invocation."
   926	    )
   927	
   928	    # Keep the prompt under ~2000 chars to match the test-orchestrator runner's
   929	    # cap. Trim the variable-length task_context first.
   930	    if len(prompt) &gt; 2000:
   931	        overflow = len(prompt) - 2000
   932	        trimmed_context = task_context[: max(0, len(task_context) - overflow - 32)]
   933	        prompt = prompt.replace(
   934	            task_context, trimmed_context + "\n[...truncated]"
   935	        )
   936	    return prompt
   937	
   938	
   939	def _parse_pytest_counts(
   940	    output: Optional[str],
   941	) -&gt; tuple[int, int, Optional[int]]:
   942	    """Parse ``(tests_run, tests_failed, tests_skipped)`` from pytest output.
   943	
   944	    ``tests_run`` = passed + failed + errors + xpassed + xfailed (skipped
   945	    excluded — a skipped test executed no assertions). Best-effort: returns
   946	    ``(0, 0, None)`` when no recognisable summary token is present. Counts are
   947	    metadata only — the authoritative pass/fail signal is the subprocess
   948	    return code (carried by :attr:`IndependentTestResult.tests_passed`), so a
   949	    parse miss never changes the gate verdict. ``max`` per class tolerates
   950	    pytest reprinting the summary.
   951	
   952	    TASK-AB-SKIPVIS01: ``tests_skipped`` is a separate ADVISORY count, never
   953	    folded into ``tests_run`` / ``tests_failed`` and never read by any verdict
   954	    logic. Tri-state: ``None`` = unparseable output (unknown, never 0-coerced),
   955	    ``0`` = summary parsed cleanly with no ``skipped`` token, ``N`` = N tests
   956	    skipped (e.g. a worktree venv missing an optional extra silently turning
   957	    tests into skips).
   958	
   959	    TASK-AB-REVIEWCLEAN01 (item 1): count extraction is delegated to the
   960	    shared ``guardkit.lib.pytest_summary`` parser. This one-shot count
   961	    consumer keeps its historic ``(0, 0, None)`` shape on a parse miss —
   962	    ``tests_run``/``tests_failed`` are 0-coerced here (metadata only; the
   963	    return code is authoritative) while ``tests_skipped`` stays ``None``.
   964	    """
   965	    summary = parse_pytest_summary(output)
   966	    return (summary.tests_run or 0, summary.tests_failed or 0, summary.skipped)
   967	
   968	
   969	def _load_task_work_results(
   970	    worktree_path: Path, task_id: str
   971	) -&gt; Optional[dict[str, Any]]:
   972	    """Load the Player's ``task_work_results.json`` for test-command detection.
   973	
   974	    The deterministic Phase-4 runner passes this to the Coach's
   975	    ``run_independent_tests`` so it detects the same task-specific test files
   976	    the Coach will. Best-effort: returns ``None`` (degrade to glob/diff
   977	    detection) on any read/parse failure. Never raises.
   978	    """
   979	    path = (
   980	        Path(worktree_path)</message>
<message type="tool">  3381	    "code_quality": "assessment",
  3382	    "edge_cases_covered": ["list", "of", "edge", "cases"]
  3383	  }},{verification_example}
  3384	  "rationale": "Why you approved"
  3385	}}
  3386	```
  3387	
  3388	For FEEDBACK, the JSON block must contain:
  3389	```json
  3390	{{
  3391	  "task_id": "{task_id}",
  3392	  "turn": {turn},
  3393	  "decision": "feedback",
  3394	  "issues": [
  3395	    {{
  3396	      "type": "missing_requirement" | "test_failure" | "code_quality" | "edge_case",
  3397	      "severity": "critical" | "major" | "minor",
  3398	      "description": "Specific issue with file paths and line numbers",
  3399	      "requirement": "Which requirement is affected",
  3400	      "suggestion": "How to fix it"
  3401	    }}
  3402	  ],{verification_example}
  3403	  "rationale": "Why you're providing feedback"
  3404	}}
  3405	```
  3406	
  3407	**IMPORTANT**: For each acceptance criterion, create a criteria_verification with:
  3408	- criterion_id: The ID (e.g., "AC-001") matching the Player's completion_promise
  3409	- result: "verified" if criterion is satisfied, "rejected" if not
  3410	- notes: Your reasoning - what you checked and found
  3411	
  3412	**CRITICAL**: The fenced ```json block MUST be the last thing in your response.
  3413	Do not write any prose after the closing ``` fence. If you emit exploratory JSON
  3414	blocks earlier in your response (e.g. while sketching alternatives), the
  3415	orchestrator takes only the **last** fenced block.
  3416	"""
  3417	
  3418	        prompt = f"""You are the Coach agent. Validate the Player's implementation.
  3419	
  3420	Task ID: {task_id}
  3421	Turn: {turn}
  3422	
  3423	{synthesis_banner}## Original Requirements
  3424	
  3425	{requirements}
  3426	{criteria_section}
  3427	## Player's Report
  3428	
  3429	{json.dumps(player_report, indent=2)}
  3430	{evidence_section}{honesty_section}{guards_section}{gather_findings_section}{coach_context_section}{visual_verification_section}
  3431	{responsibilities}
  3432	{decision_format_block}
  3433	"""
  3434	        # TASK-SELFFIX-003: enforce the overall synthesis-prompt budget.
  3435	        # Only applies to the synthesis path (toolless Coach verdict).
  3436	        if synthesis:
  3437	            prompt = self._trim_synthesis_prompt(prompt)
  3438	
  3439	        return prompt
  3440	
  3441	    # ------------------------------------------------------------------
  3442	    # TASK-HMIG-008R Part C — Coach prompt rendering helpers.
  3443	    # ------------------------------------------------------------------
  3444	
  3445	    # Token-budget truncation thresholds (plan §4 "Token budget"):
  3446	    _COACH_BDD_DISCOVERIES_LIMIT = 20
  3447	    _COACH_BDD_ERRORS_LIMIT = 10
  3448	    _COACH_HONESTY_DISCREPANCIES_LIMIT = 20
  3449	    # Wave-1 (TASK-QAWE-002): wiring / mocked_seam / spec_gap findings limit.
  3450	    _COACH_WIRING_FINDINGS_LIMIT = 20
  3451	
  3452	    # TASK-PERF-COACHSYNTH (AC-4 / Lever C): cap the Phase-A gather findings
  3453	    # text rendered into the Phase-B synthesis prompt. The gather is already
  3454	    # bounded at the source (recursion_limit + per-tool-result truncation),
  3455	    # but the findings the model *produces* can still be large; this is the
  3456	    # final belt so the synthesis prompt size does not grow unbounded with
  3457	    # gather volume (the run-20 latency creep). Truncation is MARKED, never
  3458	    # silent — respecting absence-of-failure-is-not-success.md: a silently
  3459	    # dropped tail would let the synthesis treat a partial checklist as
  3460	    # complete. ~16 k chars ≈ ~4 k tokens of findings.
  3461	    _COACH_GATHER_FINDINGS_LIMIT_CHARS = int(
  3462	        os.environ.get("GUARDKIT_COACH_GATHER_FINDINGS_LIMIT_CHARS", "16000")
  3463	    )
  3464	
  3465	    @classmethod
  3466	    def _truncate_gather_findings(cls, findings: str) -&gt; str:
  3467	        """Cap findings at the char budget with a visible truncation marker."""
  3468	        limit = cls._COACH_GATHER_FINDINGS_LIMIT_CHARS
  3469	        if limit &lt;= 0 or len(findings) &lt;= limit:
  3470	            return findings
  3471	        elided = len(findings) - limit
  3472	        return (
  3473	            findings[:limit]
  3474	            + f"\n\n... [Phase-A findings truncated for synthesis-prompt "
  3475	            f"budget: {elided} more chars elided. Any acceptance criterion "
  3476	            f"NOT explicitly marked PASS above is unverified — treat as "
  3477	            f"FAIL/UNSURE, never an assumed pass.] ..."
  3478	        )
  3479	
  3480	    # TASK-SELFFIX-003: overall synthesis-prompt budget.
  3481	    # The per-tool-result gather cap (GUARDKIT_COACH_GATHER_MAX_TOOL_RESULT_CHARS)
  3482	    # bounds individual tool results, but nothing bounded the RENDERED synthesis
  3483	    # prompt itself. Task-work coach bundles reached 109,634 tokens and overflowed
  3484	    # the crash-tested 98,304 window (FEAT-8737 TASK-SMOKE-002 turn 1). This
  3485	    # budget enforces a hard ceiling on the full rendered prompt.
  3486	    #
  3487	    # Investigation note — fields dominating the oversized bundle shape:
  3488	    # Analysis of the 109,634-token receipt (FEAT-8737 TASK-SMOKE-002 turn 1)
  3489	    # identified the following as the primary contributors to the oversized
  3490	    # bundle size:
  3491	    #   1. ``completion_promises`` in the player report JSON — a large array
  3492	    #      of per-AC verification objects (each with criterion_text, evidence,
  3493	    #      implementation_files) can easily exceed 50k chars with 200+ items.
  3494	    #   2. ``raw_output`` and ``output_tail`` in the evidence bundle — the
  3495	    #      untrimmed test runner output and BDD runner output can each carry
  3496	    #      tens of thousands of characters of raw terminal output.
  3497	    #   3. ``discoveries`` and ``errors`` lists in the BDD section — when
  3498	    #      many scenarios run, these arrays add significant JSON overhead.
  3499	    # The trimming strategy in _trim_synthesis_prompt targets these fields
  3500	    # first (player report JSON, then evidence bundle string values) before
  3501	    # resorting to aggressive bundle truncation.
  3502	    _COACH_SYNTHESIS_MAX_CHARS = int(
  3503	        os.environ.get("GUARDKIT_COACH_SYNTHESIS_MAX_CHARS", "300000")
  3504	    )
  3505	
  3506	    # Fields that carry verdict-bearing content — NEVER trimmed.
  3507	    _VERDICT_BEARING_MARKERS = (
  3508	        "## Original Requirements",
  3509	        "## Acceptance Criteria to Verify",
  3510	        "## Honesty Verification",
  3511	        "&lt;honesty_verification&gt;",
  3512	        "stub_scan",
  3513	        "behavioural_oracle",
  3514	        "&lt;evidence_bundle&gt;",
  3515	        "## Deterministic Evidence Bundle",
  3516	        "&lt;absence_of_failure_guards&gt;",
  3517	    )
  3518	
  3519	    @classmethod
  3520	    def _trim_synthesis_prompt(cls, prompt: str) -&gt; str:
  3521	        """Enforce the overall synthesis-prompt character budget.
  3522	
  3523	        When ``synthesis=True`` the Coach receives the full rendered prompt
  3524	        (requirements, acceptance criteria, player report, evidence bundle,
  3525	        honesty verification, absence-of-failure guards, etc.). Individual
  3526	        fields have per-list truncation (discoveries: 20, errors: 10,
  3527	        discrepancies: 20) but the *total* rendered prompt can still exceed
  3528	        the model's crash-tested window.
  3529	
  3530	        This method enforces a hard ceiling at
  3531	        ``GUARDKIT_COACH_SYNTHESIS_MAX_CHARS`` (default 300,000 chars ≈ 85k
  3532	        tokens). If the prompt is within budget it returns unchanged. If it
  3533	        exceeds the budget it trims low-signal content first — raw output
  3534	        tails, large JSON sections — and NEVER the verdict-bearing fields
  3535	        (requirements, acceptance criteria, honesty, stub_scan,
  3536	        behavioural_oracle).
  3537	
  3538	        Truncation is **loud**: a visible notice is inserted inside the
  3539	        prompt naming what was cut and by how much, and a WARNING is logged.
  3540	
  3541	        Parameters
  3542	        ----------
  3543	        prompt : str
  3544	            The fully-rendered synthesis prompt string.
  3545	
  3546	        Returns
  3547	        -------
  3548	        str
  3549	            The prompt, trimmed to budget if necessary.
  3550	        """
  3551	        budget = cls._COACH_SYNTHESIS_MAX_CHARS
  3552	        prompt_len = len(prompt)
  3553	
  3554	        if prompt_len &lt;= budget:
  3555	            return prompt
  3556	
  3557	        # We need to trim. Strategy: identify low-signal sections and shrink
  3558	        # them, preserving all verdict-bearing content.
  3559	        trimmed = prompt
  3560	        total_elided = 0
  3561	
  3562	        # --- 1. Trim player_report JSON (can be very large with completion_promises) ---
  3563	        # Look for the player_report JSON section and truncate it if oversized.
  3564	        # The player report is rendered as ``json.dumps(player_report, indent=2)``
  3565	        # between "## Player's Report" and the next section header.
  3566	        player_report_marker = "## Player's Report"
  3567	        player_start = trimmed.find(player_report_marker)
  3568	        if player_start != -1:
  3569	            # Find the next section header after player report
  3570	            rest = trimmed[player_start + len(player_report_marker):]
  3571	            next_section = rest.find("\n## ")
  3572	            if next_section == -1:
  3573	                # Player report is the last section before responsibilities
  3574	                next_section = rest.find("\n## Decision Format")
  3575	            if next_section != -1:
  3576	                player_section_start = player_start + len(player_report_marker)
  3577	                player_section_end = player_start + len(player_report_marker) + next_section
  3578	                player_section = trimmed[player_section_start:player_section_end]
  3579	
  3580	                # Try to extract and shrink the JSON portion
  3581	                json_start = player_section.find("{")
  3582	                if json_start != -1:
  3583	                    # Count the JSON chars
  3584	                    json_len = len(player_section) - json_start
  3585	                    if json_len &gt; 50000:  # If player report JSON is &gt; 50k chars, trim it
  3586	                        # Keep the first 5000 chars of JSON and elide the rest
  3587	                        keep = 5000
  3588	                        elided = json_len - keep
  3589	                        total_elided += elided
  3590	                        trimmed = (
  3591	                            trimmed[:player_section_start + json_start]
  3592	                            + player_section[json_start:json_start + keep]
  3593	                            + "\n  ... [player_report truncated: "
  3594	                            f"{elided} chars elided from completion_promises and file lists. "
  3595	                            "Full report available in player_turn_N.json.] ..."
  3596	                            + trimmed[player_section_end:]
  3597	                        )
  3598	
  3599	        # --- 2. Trim evidence_bundle JSON sections (large findings lists) ---
  3600	        # The evidence bundle is rendered as JSON inside &lt;evidence_bundle&gt; tags.
  3601	        # We look for large string values (raw_output, output_tail, test_output_summary)
  3602	        # and truncate them.
  3603	        bundle_start = trimmed.find("&lt;evidence_bundle&gt;")
  3604	        bundle_end = trimmed.find("&lt;/evidence_bundle&gt;")
  3605	        if bundle_start != -1 and bundle_end != -1:
  3606	            bundle_content_start = bundle_start + len("&lt;evidence_bundle&gt;")
  3607	            bundle_content_end = bundle_end
  3608	            bundle_inner = trimmed[bundle_content_start:bundle_content_end]
  3609	
  3610	            # Truncate large string values in the JSON bundle
  3611	            # Look for raw_output, output_tail, test_output_summary fields
  3612	            for field_name in ("raw_output", "output_tail", "test_output_summary"):
  3613	                # Find all occurrences of this field in the JSON
  3614	                search_start = 0
  3615	                while True:
  3616	                    pattern = f'"{field_name}": "'
  3617	                    idx = bundle_inner.find(pattern, search_start)
  3618	                    if idx == -1:
  3619	                        break
  3620	                    # Find the end of this string value
  3621	                    value_start = idx + len(pattern)
  3622	                    # Find the closing quote (handling escaped quotes)
  3623	                    j = value_start
  3624	                    while j &lt; len(bundle_inner):
  3625	                        if bundle_inner[j] == '\\' and j + 1 &lt; len(bundle_inner):
  3626	                            j += 2  # Skip escaped character
  3627	                            continue
  3628	                        if bundle_inner[j] == '"':
  3629	                            break
  3630	                        j += 1
  3631	                    value_end = j
  3632	                    value = bundle_inner[value_start:value_end]
  3633	
  3634	                    if len(value) &gt; 5000:  # Truncate if &gt; 5k chars
  3635	                        elided = len(value) - 5000
  3636	                        total_elided += elided
  3637	                        replacement = value[:5000]
  3638	                        trimmed = (
  3639	                            trimmed[:bundle_content_start + idx + len(pattern)]
  3640	                            + replacement
  3641	                            + "... [truncated: "
  3642	                            f"{elided} chars elided from {field_name}]"
  3643	                            + trimmed[bundle_content_start + value_end:]
  3644	                        )
  3645	                        # Update bundle_inner after modification
  3646	                        bundle_inner = trimmed[bundle_content_start:bundle_end]
  3647	                    search_start = value_end
  3648	
  3649	        # --- 3. Trim gather_findings if present and oversized ---
  3650	        findings_marker = "## Coach Investigation Findings (Phase A)"
  3651	        findings_start = trimmed.find(findings_marker)
  3652	        if findings_start != -1:
  3653	            rest = trimmed[findings_start + len(findings_marker):]
  3654	            next_section = rest.find("\n## ")
  3655	            if next_section != -1:
  3656	                findings_section_start = findings_start + len(findings_marker)
  3657	                findings_section_end = findings_start + len(findings_marker) + next_section
  3658	                findings_text = trimmed[findings_section_start:findings_section_end]
  3659	                if len(findings_text) &gt; 20000:
  3660	                    elided = len(findings_text) - 20000
  3661	                    total_elided += elided
  3662	                    trimmed = (
  3663	                        trimmed[:findings_section_start]
  3664	                        + findings_text[:20000]
  3665	                        + "\n\n... [investigation findings truncated: "
  3666	                        f"{elided} more chars elided.] ..."
  3667	                        + trimmed[findings_section_end:]
  3668	                    )
  3669	
  3670	        # --- 4. If still over budget, trim the evidence bundle further ---
  3671	        # This is the last resort: truncate the bundle JSON more aggressively
  3672	        if len(trimmed) &gt; budget:
  3673	            bundle_start = trimmed.find("&lt;evidence_bundle&gt;")
  3674	            bundle_end = trimmed.find("&lt;/evidence_bundle&gt;")
  3675	            if bundle_start != -1 and bundle_end != -1:
  3676	                bundle_content_start = bundle_start + len("&lt;evidence_bundle&gt;")
  3677	                bundle_content_end = bundle_end
  3678	                bundle_inner = trimmed[bundle_content_start:bundle_content_end]
  3679	
  3680	                # Truncate any string value &gt; 2000 chars</message>
<message type="ai">
  <tool_call id="fc_J1REfGaUWXJorYoIh1iGOQBSA6YeM5D4" name="glob">{"pattern": "**/test_review_seat*", "path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO"}</tool_call>
  <tool_call id="fc_BiT078PLWfjtl6b7gmQLvEd3zAOe5Muy" name="glob">{"pattern": "**/test_specialist_invocations*", "path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO"}</tool_call>
</message>
<message type="tool">['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/__pycache__/test_review_seat.cpython-312-pytest-9.1.1.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py']</message>
<message type="tool">['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/__pycache__/test_specialist_invocations.cpython-312-pytest-9.1.1.pyc', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py']</message>
<message type="ai">
  <tool_call id="fc_fI63ysftjhGSzyYJh3IZWyRTnJOnc9S7" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py"}</tool_call>
  <tool_call id="fc_kpccwD9ndsE6HblpTODQfyckq6WgGmji" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py"}</tool_call>
</message>
<message type="tool">     1	"""S3 gate — F14 emission for the R-b code-review seat (2026-07-13).
     2	
     3	Spec of record: ``ai-transition/docs/factory-code-quality-seat-options-2026-07.md``
     4	R-b build-lane stage **S-3**. Layers exercised:
     5	
     6	1. The flag (``is_review_seat_enabled``) — default OFF, env/config precedence,
     7	   mirroring ``enforcement.is_tier1_enforced``.
     8	2. The advisory entrypoint as a PROVABLE NO-OP when the flag is OFF: neither the
     9	   seat nor the running-probe is ever invoked.
    10	3. Schema-valid F14 emission on a fixture diff with a STUBBED seat.
    11	4. The F14 honesty rules (rule 2): a reading-only seat never earns ``confirmed``;
    12	   critical/high with &lt;2 refuters is downgraded, never fabricated.
    13	5. The single-slot guard (never collide with a live drive).
    14	6. Advisory never-raises: a seat outage / parse failure is a named outcome error.
    15	7. ONE real-seat integration smoke (seat-law-checked, auto-skips if the seat is
    16	   busy or unreachable).
    17	"""
    18	
    19	from __future__ import annotations
    20	
    21	import json
    22	import os
    23	from pathlib import Path
    24	
    25	import pytest
    26	
    27	from guardkit.qa.diff_ingest import ReviewPayload, parse_unified_diff
    28	from guardkit.qa.formats import validate_instance
    29	from guardkit.qa.formats.review_findings import ReviewFindings
    30	from guardkit.qa.review_seat import (
    31	    ALLOWED_SEATS,
    32	    DEFAULT_BASE_URL,
    33	    DEFAULT_SEAT,
    34	    REVIEW_SEAT_ENV,
    35	    ReviewOutcome,
    36	    ReviewSeatError,
    37	    _await_free_slot,
    38	    _default_running_probe,
    39	    build_seat_messages,
    40	    check_single_slot,
    41	    emit_review_findings,
    42	    is_review_seat_enabled,
    43	    render_payload_for_seat,
    44	    run_advisory_review,
    45	)
    46	
    47	
    48	# ---------------------------------------------------------------------------
    49	# Fixtures
    50	# ---------------------------------------------------------------------------
    51	
    52	SAMPLE_DIFF = """\
    53	diff --git a/pkg/calc.py b/pkg/calc.py
    54	index 1111111..2222222 100644
    55	--- a/pkg/calc.py
    56	+++ b/pkg/calc.py
    57	@@ -1,4 +1,6 @@
    58	 def average(xs):
    59	-    return sum(xs) / len(xs)
    60	+    total = 0
    61	+    for x in xs:
    62	+        total += x
    63	+    return total / len(xs)
    64	"""
    65	
    66	
    67	@pytest.fixture(autouse=True)
    68	def _clear_flag_env(monkeypatch: pytest.MonkeyPatch):
    69	    """Every test starts with the flag env unset — the flag defaults OFF."""
    70	    monkeypatch.delenv(REVIEW_SEAT_ENV, raising=False)
    71	
    72	
    73	@pytest.fixture
    74	def payload() -&gt; ReviewPayload:
    75	    return ReviewPayload(
    76	        subject_kind="commit",
    77	        ref="abc1234",
    78	        context_lines=3,
    79	        files=parse_unified_diff(SAMPLE_DIFF),
    80	    )
    81	
    82	
    83	def _config(repo_root: Path, review_seat: bool) -&gt; None:
    84	    cfg = repo_root / ".guardkit"
    85	    cfg.mkdir(parents=True, exist_ok=True)
    86	    (cfg / "config.yaml").write_text(
    87	        f"qa:\n  review_seat: {'true' if review_seat else 'false'}\n",
    88	        encoding="utf-8",
    89	    )
    90	
    91	
    92	def _seat_json(findings: list) -&gt; str:
    93	    return json.dumps({"summary": "changes average() to a loop", "findings": findings})
    94	
    95	
    96	class _SpySeat:
    97	    def __init__(self, output: str):
    98	        self.output = output
    99	        self.calls = 0
   100	</message>
<message type="tool">     1	"""Skeleton tests for guardkit.orchestrator.specialist_invocations.
     2	
     3	Pins the contract that TASK-OSI-004 / TASK-OSI-005 build on:
     4	
     5	* :func:`run_specialist` delegates to ``AgentInvoker._invoke_with_role``
     6	  with the right agent_type / permission_mode for each specialist.
     7	* The runner restores ``sdk_timeout_seconds`` and ``_cancellation_event``
     8	  on the AgentInvoker after the call, even when the call raises.
     9	* On exception, the runner returns ``status="failed"`` with ``error``
    10	  populated and reaps child claude processes — it never propagates the
    11	  exception.
    12	"""
    13	
    14	from __future__ import annotations
    15	
    16	import json
    17	import threading
    18	from pathlib import Path
    19	from unittest.mock import AsyncMock, MagicMock
    20	
    21	import pytest
    22	
    23	import asyncio
    24	import time
    25	
    26	from guardkit.orchestrator import specialist_invocations
    27	from guardkit.orchestrator.specialist_invocations import (
    28	    SpecialistInvocationResult,
    29	    _no_activity_watchdog_exceeded,
    30	    invoke_code_reviewer,
    31	    invoke_test_orchestrator,
    32	    run_specialist,
    33	)
    34	
    35	
    36	def _make_fake_agent_invoker(
    37	    *,
    38	    invoke_side_effect=None,
    39	    sdk_timeout_seconds: int = 1200,
    40	    cancellation_event: threading.Event | None = None,
    41	) -&gt; MagicMock:
    42	    """Return a MagicMock that mimics the AgentInvoker surface we touch.
    43	
    44	    Only the attributes/methods :func:`run_specialist` reads or writes are
    45	    populated. Pulling in the real AgentInvoker would require the SDK and
    46	    a real worktree, neither of which this skeleton-level test needs.
    47	    """
    48	    invoker = MagicMock(name="AgentInvoker")
    49	    invoker.sdk_timeout_seconds = sdk_timeout_seconds
    50	    invoker._cancellation_event = cancellation_event
    51	    invoker._invoke_with_role = AsyncMock(side_effect=invoke_side_effect)
    52	    invoker._kill_child_claude_processes = MagicMock()
    53	    # TASK-AB-PERTASKFG01 AC-004: real value (not a child MagicMock) so the
    54	    # deterministic Phase-4 runner's getattr(..., "_venv_python", None) yields
    55	    # None — no venv pinned, CoachValidator resolves the interpreter itself.
    56	    invoker._venv_python = None
    57	    return invoker
    58	
    59	
    60	@pytest.fixture(autouse=True)
    61	def _default_phase4_execution_to_sdk(monkeypatch):
    62	    """Pin Phase-4 execution to the legacy LLM-specialist path by default.
    63	
    64	    TASK-AB-PERTASKFG01 AC-004 flipped the runtime DEFAULT of
    65	    ``invoke_test_orchestrator`` to a deterministic subprocess pytest run, so
    66	    on the default it no longer calls ``_invoke_with_role``. The pre-existing
    67	    ``invoke_test_orchestrator`` tests in this module assert on the SDK
    68	    boundary (``_invoke_with_role``), so they exercise the legacy path — pin it
    69	    here so they are env-independent. The deterministic-path tests below opt
    70	    back in with ``monkeypatch.setenv(..., "subprocess")``.
    71	    """
    72	    monkeypatch.setenv("GUARDKIT_PHASE4_TEST_EXECUTION", "sdk")
    73	
    74	
    75	@pytest.mark.asyncio
    76	async def test_run_specialist_happy_path_returns_passed(tmp_path: Path) -&gt; None:
    77	    """Successful delegation produces a passed result with phase derived
    78	    from specialist_name and the conventional result_file path filled in.
    79	    """
    80	    invoker = _make_fake_agent_invoker()
    81	
    82	    result = await run_specialist(
    83	        specialist_name="test-orchestrator",
    84	        worktree_path=tmp_path,
    85	        task_id="TASK-OSI-001",
    86	        sdk_timeout=42,
    87	        prompt="run the tests",
    88	        allowed_tools=["Read", "Bash", "Write"],
    89	        agent_invoker=invoker,
    90	    )
    91	
    92	    assert isinstance(result, SpecialistInvocationResult)
    93	    assert result.specialist_name == "test-orchestrator"
    94	    assert result.phase == "4"
    95	    assert result.status == "passed"
    96	    assert result.error is None
    97	    assert result.result_file == (
    98	        tmp_path / ".guardkit" / "autobuild" / "TASK-OSI-001" / "specialist_results.json"
    99	    )
   100	    assert result.duration_seconds &gt;= 0</message>
<message type="ai">
  <tool_call id="fc_dSAGarwZerQy7RNNeXzPCNucaCrE4Pvk" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py", "offset": 100}</tool_call>
</message>
<message type="tool">   101	
   102	    invoker._invoke_with_role.assert_awaited_once()
   103	    kwargs = invoker._invoke_with_role.await_args.kwargs
   104	    assert kwargs["prompt"] == "run the tests"
   105	    assert kwargs["agent_type"] == "player"
   106	    assert kwargs["permission_mode"] == "acceptEdits"
   107	    assert kwargs["allowed_tools"] == ["Read", "Bash", "Write"]
   108	    assert kwargs["task_id"] == "TASK-OSI-001"
   109	
   110	    invoker._kill_child_claude_processes.assert_not_called()
   111	
   112	
   113	@pytest.mark.asyncio
   114	async def test_run_specialist_code_reviewer_runs_as_coach(tmp_path: Path) -&gt; None:
   115	    """code-reviewer must run as agent_type=coach with bypassPermissions
   116	    so the existing read-only invariant the gate enforces holds.
   117	    """
   118	    invoker = _make_fake_agent_invoker()
   119	
   120	    result = await run_specialist(
   121	        specialist_name="code-reviewer",
   122	        worktree_path=tmp_path,
   123	        task_id="TASK-OSI-001",
   124	        sdk_timeout=42,
   125	        prompt="review the diff",
   126	        allowed_tools=["Read", "Grep"],
   127	        agent_invoker=invoker,
   128	    )
   129	
   130	    assert result.phase == "5"
   131	    assert result.status == "passed"
   132	
   133	    kwargs = invoker._invoke_with_role.await_args.kwargs
   134	    assert kwargs["agent_type"] == "coach"
   135	    assert kwargs["permission_mode"] == "bypassPermissions"
   136	
   137	
   138	@pytest.mark.asyncio
   139	async def test_run_specialist_failure_returns_failed_and_reaps(tmp_path: Path) -&gt; None:
   140	    """When ``_invoke_with_role`` raises, the runner must return a failed
   141	    result, populate ``error``, and reap child claude processes — never
   142	    propagate.
   143	    """
   144	    boom = RuntimeError("SDK exploded")
   145	    invoker = _make_fake_agent_invoker(invoke_side_effect=boom)
   146	
   147	    result = await run_specialist(
   148	        specialist_name="test-orchestrator",
   149	        worktree_path=tmp_path,
   150	        task_id="TASK-OSI-001",
   151	        sdk_timeout=42,
   152	        prompt="run the tests",
   153	        allowed_tools=["Read", "Bash", "Write"],
   154	        agent_invoker=invoker,
   155	    )
   156	
   157	    assert result.status == "failed"
   158	    assert result.error is not None
   159	    assert "RuntimeError" in result.error
   160	    assert "SDK exploded" in result.error
   161	    # On failure we leave result_file unset so callers cannot assume the
   162	    # specialist actually wrote the conventional file.
   163	    assert result.result_file is None
   164	    invoker._kill_child_claude_processes.assert_called_once()
   165	
   166	
   167	@pytest.mark.asyncio
   168	async def test_run_specialist_restores_state_after_call(tmp_path: Path) -&gt; None:
   169	    """The runner must restore ``sdk_timeout_seconds`` and
   170	    ``_cancellation_event`` on the AgentInvoker on both the success and
   171	    the failure paths so subsequent invocations see the original state.
   172	    """
   173	    original_timeout = 1234
   174	    original_event = threading.Event()
   175	    invoker = _make_fake_agent_invoker(
   176	        sdk_timeout_seconds=original_timeout,
   177	        cancellation_event=original_event,
   178	    )
   179	    override_event = threading.Event()
   180	
   181	    # Inside the call, sdk_timeout_seconds must reflect the override.
   182	    captured: dict[str, object] = {}
   183	
   184	    async def _capture(**_: object) -&gt; None:
   185	        captured["timeout"] = invoker.sdk_timeout_seconds
   186	        captured["cancellation"] = invoker._cancellation_event
   187	
   188	    invoker._invoke_with_role = AsyncMock(side_effect=_capture)
   189	
   190	    await run_specialist(
   191	        specialist_name="test-orchestrator",
   192	        worktree_path=tmp_path,
   193	        task_id="TASK-OSI-001",
   194	        sdk_timeout=99,
   195	        prompt="run the tests",
   196	        allowed_tools=["Read", "Bash", "Write"],
   197	        agent_invoker=invoker,
   198	        cancellation_event=override_event,
   199	    )
   200	</message>
<message type="ai">
  <tool_call id="fc_mcQTnHJe6fm9v8Lu8Ua9k0uTrArwzt23" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py", "offset": 200}</tool_call>
</message>
<message type="tool">   201	    assert captured["timeout"] == 99
   202	    assert captured["cancellation"] is override_event
   203	    # State must be restored after the call, regardless of success.
   204	    assert invoker.sdk_timeout_seconds == original_timeout
   205	    assert invoker._cancellation_event is original_event
   206	
   207	
   208	@pytest.mark.asyncio
   209	async def test_run_specialist_restores_state_on_failure(tmp_path: Path) -&gt; None:
   210	    """Same restore invariant on the failure path."""
   211	    original_timeout = 1234
   212	    original_event = threading.Event()
   213	    invoker = _make_fake_agent_invoker(
   214	        invoke_side_effect=RuntimeError("boom"),
   215	        sdk_timeout_seconds=original_timeout,
   216	        cancellation_event=original_event,
   217	    )
   218	
   219	    result = await run_specialist(
   220	        specialist_name="code-reviewer",
   221	        worktree_path=tmp_path,
   222	        task_id="TASK-OSI-001",
   223	        sdk_timeout=77,
   224	        prompt="review",
   225	        allowed_tools=["Read"],
   226	        agent_invoker=invoker,
   227	        cancellation_event=threading.Event(),
   228	    )
   229	
   230	    assert result.status == "failed"
   231	    assert invoker.sdk_timeout_seconds == original_timeout
   232	    assert invoker._cancellation_event is original_event
   233	
   234	
   235	@pytest.mark.asyncio
   236	@pytest.mark.parametrize(
   237	    "specialist_name",
   238	    ["test-orchestrator", "code-reviewer"],
   239	)
   240	async def test_run_specialist_heartbeat_label_includes_specialist_name(
   241	    tmp_path: Path, specialist_name: str
   242	) -&gt; None:
   243	    """run_specialist must thread a ``heartbeat_label_override`` kwarg
   244	    containing ``"specialist:{name}"`` into ``_invoke_with_role`` so
   245	    orchestrator-driven specialists are visually distinct from the
   246	    actual task-work Player in heartbeat logs (TASK-ABSR-DIAG).
   247	    """
   248	    invoker = _make_fake_agent_invoker()
   249	
   250	    await run_specialist(
   251	        specialist_name=specialist_name,
   252	        worktree_path=tmp_path,
   253	        task_id="TASK-ABSR-DIAG",
   254	        sdk_timeout=42,
   255	        prompt="do the thing",
   256	        allowed_tools=["Read"],
   257	        agent_invoker=invoker,
   258	    )
   259	
   260	    invoker._invoke_with_role.assert_awaited_once()
   261	    kwargs = invoker._invoke_with_role.await_args.kwargs
   262	    assert "heartbeat_label_override" in kwargs, (
   263	        "run_specialist must pass heartbeat_label_override to _invoke_with_role"
   264	    )
   265	    override = kwargs["heartbeat_label_override"]
   266	    assert isinstance(override, str)
   267	    assert f"specialist:{specialist_name}" in override
   268	    assert "invocation" in override
   269	
   270	
   271	# =============================================================================
   272	# invoke_test_orchestrator (TASK-OSI-004)
   273	# =============================================================================
   274	#
   275	# These tests exercise the orchestrator-side Phase 4 runner. The SDK
   276	# boundary is the AgentInvoker._invoke_with_role mock — when the run is
   277	# "successful" we simulate the real test-orchestrator agent by writing
   278	# phase_4_summary.json from the side-effect callable. When the run
   279	# "fails" we raise from the side-effect to mimic an SDK exception.
   280	
   281	
   282	_TASK_ID_OSI_004 = "TASK-OSI-004-FAKE"
   283	
   284	
   285	def _seed_task_markdown(worktree: Path, task_id: str) -&gt; Path:
   286	    """Place a minimal task markdown the runner can parse."""
   287	    task_dir = worktree / "tasks" / "in_progress" / "fake-feature"
   288	    task_dir.mkdir(parents=True, exist_ok=True)
   289	    task_file = task_dir / f"{task_id}-fake.md"
   290	    task_file.write_text(
   291	        "---\n"
   292	        f"id: {task_id}\n"
   293	        "status: in_progress\n"
   294	        "---\n\n"
   295	        "# Task: Fake task\n\n"
   296	        "## Description\n\n"
   297	        "Make the fake thing work.\n\n"
   298	        "## Acceptance Criteria\n\n"
   299	        "- [ ] Fake AC 1\n"
   300	        "- [ ] Fake AC 2\n\n"</message>
<message type="ai">
  <tool_call id="fc_uBTtFCooQ0iDR7fUr1E5ewoJGPgFVrve" name="execute">{"command": "grep -n \"_build_code_reviewer_prompt\\|_build_seat_messages\\|build_seat_messages\" /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py 2&gt;/dev/null || true"}</tool_call>
</message>
<message type="tool">/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py:39:    build_seat_messages,
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py:537:        system, user = build_seat_messages(payload)

[Command succeeded with exit code 0]</message>
<message type="ai">
  <tool_call id="fc_HNwMjD8pLKAnPYHntxMRApNG6uNb5xp9" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py", "offset": 520}</tool_call>
</message>
<message type="tool">   521	        assert "not an allowed local seat" in outcome.error
   522	
   523	
   524	# ===========================================================================
   525	# 8. Prompt assembly sanity
   526	# ===========================================================================
   527	
   528	
   529	class TestPrompt:
   530	    def test_render_includes_diff_markers(self, payload):
   531	        text = render_payload_for_seat(payload)
   532	        assert "pkg/calc.py" in text
   533	        assert "+    total = 0" in text
   534	        assert "-    return sum(xs) / len(xs)" in text
   535	
   536	    def test_messages_carry_subject_and_diff(self, payload):
   537	        system, user = build_seat_messages(payload)
   538	        assert "INSPECTOR" in system
   539	        assert "JSON object" in system
   540	        assert "kind: commit" in user
   541	        assert "pkg/calc.py" in user
   542	
   543	
   544	# ===========================================================================
   545	# 9. ONE real-seat integration smoke (seat-law-checked; auto-skips)
   546	# ===========================================================================
   547	
   548	
   549	@pytest.mark.integration
   550	def test_real_seat_smoke(tmp_path: Path, payload, monkeypatch: pytest.MonkeyPatch):
   551	    """Drive the REAL local seat once, honesty-to-state.
   552	
   553	    Seat-law-checked: probes ``/running`` first and SKIPS (never collides) if the
   554	    seat is unreachable or a live drive holds the single slot. Asserts the
   555	    advisory contract holds against a real model — either a schema-valid F14
   556	    record OR a NAMED error (an unrunnable/unparseable seat is a finding, never a
   557	    faked green). It never asserts specific findings (model output varies).
   558	    """
   559	    probe = _default_running_probe(DEFAULT_BASE_URL)
   560	    running = probe()
   561	    if running is None:
   562	        pytest.skip("llama-swap /running unreachable — seat not available")
   563	    free, reason = check_single_slot(running)
   564	    if not free:
   565	        pytest.skip(f"seat busy, refusing to collide: {reason}")
   566	
   567	    monkeypatch.setenv(REVIEW_SEAT_ENV, "1")
   568	    outcome = run_advisory_review(
   569	        tmp_path, payload, model=DEFAULT_SEAT, write=True
   570	    )
   571	
   572	    assert outcome.enabled is True
   573	    assert outcome.blocking is False
   574	    if outcome.record is not None:
   575	        # A real emission must be schema-valid through the canonical loader.
   576	        ReviewFindings.model_validate(outcome.record.model_dump())
   577	        assert outcome.record.stats.confirmed == 0  # reading-only seat never confirms
   578	        if outcome.emitted_path is not None:
   579	            validate_instance("review-findings", Path(outcome.emitted_path))
   580	    else:
   581	        # Honesty-to-state: no record =&gt; a named error, never a silent green.
   582	        assert outcome.error, "no record and no error is a faked green"</message>
<message type="ai">
  <tool_call id="fc_0VdRDiSKmficCnIbeOOaGfFERteYq4lc" name="write_todos">{"todos": [{"content": "Add GUARDKIT_REVIEW_SEAT_MAX_CHARS budget to build_seat_messages in review_seat.py", "status": "in_progress"}, {"content": "Add GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS budget to _build_code_reviewer_prompt in specialist_invocations.py", "status": "pending"}, {"content": "Add test for review-seat budget bounding", "status": "pending"}, {"content": "Add test for specialist prompt budget bounding", "status": "pending"}, {"content": "Run tests and verify", "status": "pending"}, {"content": "Write player report JSON", "status": "pending"}]}</tool_call>
</message>
<message type="tool">Updated todo list to [{'content': 'Add GUARDKIT_REVIEW_SEAT_MAX_CHARS budget to build_seat_messages in review_seat.py', 'status': 'in_progress'}, {'content': 'Add GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS budget to _build_code_reviewer_prompt in specialist_invocations.py', 'status': 'pending'}, {'content': 'Add test for review-seat budget bounding', 'status': 'pending'}, {'content': 'Add test for specialist prompt budget bounding', 'status': 'pending'}, {'content': 'Run tests and verify', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]</message>
<message type="ai">
  <tool_call id="fc_s4BE6PW7aBZWc4thnLjCZmKe5ex7BksZ" name="grep">{"pattern": "_REVIEW_SYSTEM", "path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/qa/review_seat.py", "output_mode": "content"}</tool_call>
</message>
<message type="tool">/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/qa/review_seat.py:
  220: _REVIEW_SYSTEM = """\
  338:     return _REVIEW_SYSTEM, "\n\n".join(sections)</message>
<message type="ai">
  <tool_call id="fc_PwZkVVZpYvphFnUm60im4P1knExejXhJ" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/qa/review_seat.py", "offset": 215, "limit": 100}</tool_call>
</message>
<message type="tool">   216	# ===========================================================================
   217	# 1. Prompt assembly (the S-2 review contract, self-contained in guardkit).
   218	# ===========================================================================
   219	
   220	_REVIEW_SYSTEM = """\
   221	You are the factory's INSPECTOR: a senior code reviewer who reads a finished \
   222	change and writes up what is wrong, with reasons. You are advisory — you do NOT \
   223	gate the build; you emit findings. Review ONLY the supplied diff; never invent \
   224	defects on code the diff does not touch.
   225	
   226	Score against exactly these four dimensions:
   227	1. correctness    — real defects the change introduces (logic errors, broken \
   228	contracts, unhandled edge cases, races, security holes).
   229	2. simplification — genuine reuse / dead-code / over-abstraction / duplication \
   230	the change could have avoided, with the simpler alternative named.
   231	3. efficiency     — avoidable cost the change introduces (needless O(n^2), \
   232	repeated I/O in a loop, unbounded allocation), with the observable impact.
   233	4. test_coverage  — new branches / error paths / boundaries in the diff that no \
   234	test exercises; name the uncovered behaviour and the test that would cover it.
   235	
   236	Finding discipline (the F14 finding record):
   237	- Anchor every finding to a concrete file:line INSIDE the diff and state a \
   238	failing-input -&gt; wrong-output scenario. A finding with no anchor and no scenario \
   239	is not a finding.
   240	- You CANNOT run code. You have no tools and no execution channel. Therefore \
   241	you must NEVER claim a reproduction you did not run: leave "executed_reproduction" \
   242	null. Reading is not a verdict.
   243	- For critical or high severity, supply at least TWO refuters — concrete reasons \
   244	the finding might be wrong — each with your answer. Severity is default-refuted: \
   245	a finding you cannot defend with two refuters is medium at most.
   246	- Do not over-flag. A cosmetic or stylistic nit (naming taste, import order, \
   247	formatting a linter would catch) is "low" severity or omitted — never a blocker.
   248	- Propose-never-elicit: never address a question to a human.
   249	
   250	OUTPUT: a single JSON object and nothing else (no prose, no markdown fences). \
   251	Shape:
   252	{
   253	  "summary": "&lt;plain-English summary of what the change does&gt;",
   254	  "findings": [
   255	    {
   256	      "id": "F1",
   257	      "dimension": "correctness|simplification|efficiency|test_coverage",
   258	      "severity": "critical|high|medium|low",
   259	      "file": "path/from/the/diff",
   260	      "line": 123,
   261	      "summary": "&lt;one-sentence defect statement&gt;",
   262	      "failing_scenario": "&lt;failing-input -&gt; wrong-output&gt;",
   263	      "executed_reproduction": null,
   264	      "refuters": [
   265	        {"who": "refuter-1", "verdict": "refuted|not_refuted", "note": "&lt;why&gt;"}
   266	      ]
   267	    }
   268	  ]
   269	}
   270	If the change is clean, emit {"summary": "...", "findings": []}. Never \
   271	manufacture a nit to fill the list.
   272	"""
   273	
   274	
   275	def render_payload_for_seat(payload: ReviewPayload, *, max_chars: int = 60000) -&gt; str:
   276	    """Render an S-1 ``ReviewPayload`` as the unified diff text the seat reads.
   277	
   278	    Deterministic and lossless within budget: reconstructs each file's header
   279	    line, change kind, and hunks (with ``@@`` headers + ``+``/``-``/context
   280	    markers). A binary or hunk-less file is named with its change kind so the
   281	    reviewer sees it exists. Truncated at ``max_chars`` with an explicit marker
   282	    (honesty-to-state: a clipped diff says so, it is never silently short).
   283	    """
   284	    lines: List[str] = []
   285	    for fd in payload.files:
   286	        lines.append(_render_file_header(fd))
   287	        if fd.is_binary:
   288	            lines.append("(binary file — not shown)")
   289	            continue
   290	        for hunk in fd.hunks:
   291	            lines.append(hunk.header if hunk.header else _synth_hunk_header(hunk))
   292	            for dl in hunk.lines:
   293	                marker = {"added": "+", "removed": "-", "context": " "}[dl.kind]
   294	                lines.append(f"{marker}{dl.content}")
   295	    text = "\n".join(lines)
   296	    if len(text) &gt; max_chars:
   297	        text = (
   298	            text[:max_chars]
   299	            + f"\n... [diff truncated at {max_chars} chars for the review seat "
   300	            f"— {len(text) - max_chars} more chars not shown]"
   301	        )
   302	    return text
   303	
   304	
   305	def _render_file_header(fd: FileDiff) -&gt; str:
   306	    old = fd.old_path or "/dev/null"
   307	    new = fd.path or "/dev/null"
   308	    return f"diff --git a/{old} b/{new}  [{fd.change_kind}]"
   309	
   310	
   311	def _synth_hunk_header(hunk: Any) -&gt; str:
   312	    head = (
   313	        f"@@ -{hunk.old_start},{hunk.old_count} "
   314	        f"+{hunk.new_start},{hunk.new_count} @@"
   315	    )</message>
<message type="ai">
  <content>Now I'll implement the changes. Starting with `review_seat.py`:

</content>
  <tool_call id="fc_65s5QMe4brg22FtH4kRCbaAdkTKj7P00" name="edit_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/qa/review_seat.py", "old_string": "logger = logging.getLogger(__name__)\n\n__all__ = [", "new_string": "logger = logging.getLogger(__name__)\n\n# TASK-SBHO-001: env-tunable ceiling for the ASSEMBLED review-seat user message.\n# Mirrors the _trim_synthesis_prompt pattern: loud truncation marker, WARNING log,\n# degrade-never-raise. Default 300k chars ≈ 85k tokens.\nREVIEW_SEAT_MAX_CHARS_ENV = \"GUARDKIT_REVIEW_SEAT_MAX_CHARS\"\nREVIEW_SEAT_MAX_CHARS: int = int(\n    os.environ.get(REVIEW_SEAT_MAX_CHARS_ENV, \"300000\")\n)\n\n# Protected section markers that must NEVER be trimmed.\n_REVIEW_INSTRUCTION_HEADER = \"## Review subject\"\n_REVIEW_FINDING_SCHEMA = \"## Diff under review\"\n\n__all__ = ["}</tool_call>
</message>
<message type="tool">Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/qa/review_seat.py'</message>
<message type="ai">
  <tool_call id="fc_hZZNzxX7MXVIVLRy7zGcgG4IziZ5SmRs" name="edit_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/qa/review_seat.py", "old_string": "__all__ = [\n    \"REVIEW_SEAT_ENV\",\n    \"is_review_seat_enabled\",\n    \"ALLOWED_SEATS\",\n    \"DEFAULT_SEAT\",\n    \"DEFAULT_BASE_URL\",\n    \"CANONICAL_DIMENSIONS\",\n    \"SeatCall\",\n    \"RunningProbe\",\n    \"ReviewOutcome\",\n    \"render_payload_for_seat\",\n    \"build_seat_messages\",\n    \"check_single_slot\",\n    \"emit_review_findings\",\n    \"run_advisory_review\",\n    \"PayloadFactory\",\n    \"FindingRouter\",\n    \"default_merge_candidate_payload\",\n    \"run_review_gate_step\",\n]", "new_string": "__all__ = [\n    \"REVIEW_SEAT_ENV\",\n    \"REVIEW_SEAT_MAX_CHARS_ENV\",\n    \"REVIEW_SEAT_MAX_CHARS\",\n    \"is_review_seat_enabled\",\n    \"ALLOWED_SEATS\",\n    \"DEFAULT_SEAT\",\n    \"DEFAULT_BASE_URL\",\n    \"CANONICAL_DIMENSIONS\",\n    \"SeatCall\",\n    \"RunningProbe\",\n    \"ReviewOutcome\",\n    \"render_payload_for_seat\",\n    \"build_seat_messages\",\n    \"check_single_slot\",\n    \"emit_review_findings\",\n    \"run_advisory_review\",\n    \"PayloadFactory\",\n    \"FindingRouter\",\n    \"default_merge_candidate_payload\",\n    \"run_review_gate_step\",\n]"}</tool_call>
</message>
<message type="tool">Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/qa/review_seat.py'</message>
<message type="ai">
  <tool_call id="fc_a9EPNi81kGkHOMONHg5MnRXIKmsYh5mi" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/qa/review_seat.py", "limit": 30, "offset": 325}</tool_call>
</message>
<message type="tool">   326	    head = (
   327	        f"@@ -{hunk.old_start},{hunk.old_count} "
   328	        f"+{hunk.new_start},{hunk.new_count} @@"
   329	    )
   330	    return head + (f" {hunk.section_heading}" if hunk.section_heading else "")
   331	
   332	
   333	def build_seat_messages(
   334	    payload: ReviewPayload, *, repo_context: Optional[str] = None
   335	) -&gt; Tuple[str, str]:
   336	    """Assemble the (system, user) messages for the reviewer seat.
   337	
   338	    The user message carries the review subject, an optional repo-context
   339	    section, and the rendered diff. The system message is the self-contained
   340	    S-2 review contract (dimensions + F14 discipline + JSON shape).
   341	    """
   342	    diff_text = render_payload_for_seat(payload)
   343	    sections: List[str] = [
   344	        f"## Review subject\n\nkind: {payload.subject_kind} · ref: {payload.ref}",
   345	    ]
   346	    if repo_context and repo_context.strip():
   347	        sections.append("## Repository context (reference)\n\n" + repo_context.strip())
   348	    sections.append(
   349	        "## Diff under review (review ONLY these changes)\n\n"
   350	        + (diff_text if diff_text.strip() else "(empty diff — nothing changed)")
   351	    )
   352	    return _REVIEW_SYSTEM, "\n\n".join(sections)
   353	
   354	
   355	# ===========================================================================</message>
<message type="ai">
  <tool_call id="fc_TdqI9ylZUegBrz5AZxcNsidSatU2yHkt" name="edit_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/qa/review_seat.py", "old_string": "def build_seat_messages(\n    payload: ReviewPayload, *, repo_context: Optional[str] = None\n) -&gt; Tuple[str, str]:\n    \"\"\"Assemble the (system, user) messages for the reviewer seat.\n\n    The user message carries the review subject, an optional repo-context\n    section, and the rendered diff. The system message is the self-contained\n    S-2 review contract (dimensions + F14 discipline + JSON shape).\n    \"\"\"\n    diff_text = render_payload_for_seat(payload)\n    sections: List[str] = [\n        f\"## Review subject\\n\\nkind: {payload.subject_kind} · ref: {payload.ref}\",\n    ]\n    if repo_context and repo_context.strip():\n        sections.append(\"## Repository context (reference)\\n\\n\" + repo_context.strip())\n    sections.append(\n        \"## Diff under review (review ONLY these changes)\\n\\n\"\n        + (diff_text if diff_text.strip() else \"(empty diff — nothing changed)\")\n    )\n    return _REVIEW_SYSTEM, \"\\n\\n\".join(sections)", "new_string": "def build_seat_messages(\n    payload: ReviewPayload,\n    *,\n    repo_context: Optional[str] = None,\n    max_chars: int | None = None,\n) -&gt; Tuple[str, str]:\n    \"\"\"Assemble the (system, user) messages for the reviewer seat.\n\n    The user message carries the review subject, an optional repo-context\n    section, and the rendered diff. The system message is the self-contained\n    S-2 review contract (dimensions + F14 discipline + JSON shape).\n\n    When *max_chars* is set (default from ``REVIEW_SEAT_MAX_CHARS``), the\n    assembled user message is bounded: ``repo_context`` is trimmed first,\n    then the diff tail. The instruction header (review subject) and the\n    diff section itself are never trimmed — only the content within\n    ``repo_context`` and the tail of the diff are eligible.\n\n    Truncation is **loud**: a visible notice is inserted inside the prompt\n    naming what was cut and by how much, and a WARNING is logged.\n    \"\"\"\n    if max_chars is None:\n        max_chars = REVIEW_SEAT_MAX_CHARS\n\n    diff_text = render_payload_for_seat(payload)\n    subject_section = (\n        f\"## Review subject\\n\\nkind: {payload.subject_kind} · ref: {payload.ref}\"\n    )\n    repo_section: str | None = None\n    if repo_context and repo_context.strip():\n        repo_section = \"## Repository context (reference)\\n\\n\" + repo_context.strip()\n\n    diff_section = (\n        \"## Diff under review (review ONLY these changes)\\n\\n\"\n        + (diff_text if diff_text.strip() else \"(empty diff — nothing changed)\")\n    )\n\n    user_message = _trim_review_seat_user(\n        subject_section,\n        repo_section,\n        diff_section,\n        max_chars=max_chars,\n    )\n    return _REVIEW_SYSTEM, user_message\n\n\ndef _trim_review_seat_user(\n    subject_section: str,\n    repo_section: str | None,\n    diff_section: str,\n    *,\n    max_chars: int,\n) -&gt; str:\n    \"\"\"Trim the assembled user message to *max_chars*.\n\n    Priority: never trim the subject (instruction header) or the diff\n    section header. Trim ``repo_context`` first, then the diff tail.\n\n    Returns the assembled user message, possibly truncated with a loud\n    truncation marker.\n    \"\"\"\n    # Build the full message to check if it's over budget.\n    parts: List[str] = [subject_section]\n    if repo_section:\n        parts.append(repo_section)\n    parts.append(diff_section)\n    full = \"\\n\\n\".join(parts)\n\n    if len(full) &lt;= max_chars:\n        return full\n\n    # We need to trim. Strategy:\n    # 1. Trim repo_context first (lowest signal for the review).\n    # 2. If still over, trim the diff tail.\n    # Never trim the subject or the diff section header.\n    trimmed = full\n    total_elided = 0\n\n    # Step 1: Trim repo_context if present.\n    if repo_section:\n        repo_len = len(repo_section)\n        # Reserve space for subject + diff_section + separators\n        reserved = len(subject_section) + len(diff_section) + 4  # 2x \"\\n\\n\"\n        available_for_repo = max(0, max_chars - reserved)\n        if available_for_repo &lt; 100:\n            # Not enough room for even a minimal repo section — drop it.\n            elided = repo_len\n            total_elided += elided\n            trimmed = subject_section + \"\\n\\n\" + diff_section\n            logger.warning(\n                \"review seat: repo_context truncated (%d chars elided) \"\n                \"to fit within %d-char budget\",\n                elided,\n                max_chars,\n            )\n        else:\n            # Trim the repo_context content (keep the section header).\n            header_end = repo_section.find(\"\\n\\n\")\n            if header_end == -1:\n                header_end = len(repo_section)\n            header = repo_section[:header_end]\n            content = repo_section[header_end:]\n            max_repo_content = max(0, available_for_repo - len(header))\n            if len(content) &gt; max_repo_content:\n                elided = len(content) - max_repo_content\n                total_elided += elided\n                repo_section_trimmed = header + content[:max_repo_content]\n                trimmed = (\n                    subject_section\n                    + \"\\n\\n\"\n                    + repo_section_trimmed\n                    + \"\\n\\n... [repository context truncated: \"\n                    f\"{elided} more chars elided to fit budget.] ...\"\n                    + \"\\n\\n\"\n                    + diff_section\n                )\n                logger.warning(\n                    \"review seat: repo_context truncated (%d chars elided) \"\n                    \"to fit within %d-char budget\",\n                    elided,\n                    max_chars,\n                )\n            else:\n                trimmed = repo_section\n\n    # Step 2: If still over budget, trim the diff tail.\n    if len(trimmed) &gt; max_chars:\n        # Find the diff section and trim its content.\n        diff_header = \"## Diff under review (review ONLY these changes)\\n\\n\"\n        diff_start = trimmed.find(diff_header)\n        if diff_start != -1:\n            diff_content_start = diff_start + len(diff_header)\n            diff_content = trimmed[diff_content_start:]\n            max_diff_tail = max(0, max_chars - diff_content_start)\n            if len(diff_content) &gt; max_diff_tail:\n                elided = len(diff_content) - max_diff_tail\n                total_elided += elided\n                trimmed = (\n                    trimmed[:diff_content_start]\n                    + diff_content[:max_diff_tail]\n                    + f\"\\n... [diff truncated: {elided} more chars elided \"\n                    f\"to fit within {max_chars}-char budget.] ...\"\n                )\n                logger.warning(\n                    \"review seat: diff tail truncated (%d chars elided) \"\n                    \"to fit within %d-char budget\",\n                    elided,\n                    max_chars,\n                )\n        else:\n            # Fallback: hard trim at budget.\n            trimmed = (\n                trimmed[:max_chars]\n                + f\"\\n... [review-seat user message truncated at \"\n                f\"{max_chars} chars — {len(trimmed) - max_chars} more chars not shown.]\"\n            )\n            logger.warning(\n                \"review seat: user message hard-trimmed at %d chars \"\n                \"(%d chars elided)\",\n                max_chars,\n                len(trimmed) - max_chars,\n            )\n\n    return trimmed"}</tool_call>
</message>
<message type="tool">Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/qa/review_seat.py'</message>
<message type="ai">
  <tool_call id="fc_9SS5YsICWf0PcRQfi5ySzF05BqZqD7UQ" name="write_todos">{"todos": [{"content": "Add GUARDKIT_REVIEW_SEAT_MAX_CHARS budget to build_seat_messages in review_seat.py", "status": "completed"}, {"content": "Add GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS budget to _build_code_reviewer_prompt in specialist_invocations.py", "status": "in_progress"}, {"content": "Add test for review-seat budget bounding", "status": "pending"}, {"content": "Add test for specialist prompt budget bounding", "status": "pending"}, {"content": "Run tests and verify", "status": "pending"}, {"content": "Write player report JSON", "status": "pending"}]}</tool_call>
</message>
<message type="tool">Updated todo list to [{'content': 'Add GUARDKIT_REVIEW_SEAT_MAX_CHARS budget to build_seat_messages in review_seat.py', 'status': 'completed'}, {'content': 'Add GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS budget to _build_code_reviewer_prompt in specialist_invocations.py', 'status': 'in_progress'}, {'content': 'Add test for review-seat budget bounding', 'status': 'pending'}, {'content': 'Add test for specialist prompt budget bounding', 'status': 'pending'}, {'content': 'Run tests and verify', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]</message>
<message type="ai">
  <tool_call id="fc_wU3vTLqWljupv5V1oGZ82J6s1dsQFnVI" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/orchestrator/specialist_invocations.py", "limit": 100, "offset": 75}</tool_call>
</message>
<message type="tool">    76	
    77	# Per-specialist SDK-timeout ceiling for the Phase 4 test-orchestrator.
    78	#
    79	# The caller-supplied ``sdk_timeout`` is shared with Player/Coach and can
    80	# reach 2340s on the canary batch. The test-orchestrator specialist has
    81	# been observed to launch ``pytest`` with ``Bash run_in_background=true``
    82	# then poll ``TaskOutput`` every ~30s until the SDK timeout fires —
    83	# burning ~38min per turn even when pytest itself would finish in &lt;2min
    84	# (TASK-HMIG-009A AC-003 rep 1, 2026-06-03; see
    85	# ``docs/reviews/autobuild-migration/long-run-1.md``). The cap is a hard
    86	# orchestrator-side ceiling that converts the SDK timeout into a graceful
    87	# specialist failure at the 10-minute mark instead of letting it consume
    88	# the full Player/Coach budget. Suites that legitimately need &gt;600s
    89	# should be decomposed at the task level, not papered over here.
    90	_TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS: int = 600
    91	
    92	# TASK-PERF-SPECLAT01: per-specialist SDK-timeout ceiling for the Phase 5
    93	# code-reviewer.
    94	#
    95	# The code-reviewer is an *agentic* read-only specialist (Read/Grep/Search)
    96	# that makes many tool round-trips and never self-terminates — on a slow
    97	# locally-served model it runs to whatever ``sdk_timeout`` it is handed. Before
    98	# this cap existed the only bound was the wall clamp in
    99	# ``AgentInvoker``-derived ``_cap_specialist_timeout``; with the (large) default
   100	# ``COACH_GRACE_PERIOD_SECONDS`` reservation that left ~2130s available, so
   101	# FEAT-9DDE run-6 turn-2's code-reviewer ran **35.6 min (2138s)** to its
   102	# ``SDKTimeoutError`` and consumed &gt;½ the 80-min task budget in one turn,
   103	# foreclosing convergence with ``timeout_budget_exhausted``. This is the exact
   104	# symmetric counterpart of ``_TEST_ORCHESTRATOR_SDK_TIMEOUT_CAP_SECONDS``:
   105	# convert the SDK timeout into a graceful bounded specialist failure at the
   106	# 10-minute mark instead of letting it eat the whole Player/Coach budget.
   107	# Operator-tunable via ``GUARDKIT_CODE_REVIEWER_TIMEOUT_CAP``.
   108	_CODE_REVIEWER_SDK_TIMEOUT_CAP_SECONDS: int = int(
   109	    os.environ.get("GUARDKIT_CODE_REVIEWER_TIMEOUT_CAP", "600")
   110	)
   111	
   112	# TASK-FIX-SPECHANG2: per-specialist no-model-activity watchdog ceiling.
   113	#
   114	# The 600s duration cap above bounds a hang but does not *eliminate* it.
   115	# Run-9 turn-2 (2026-06-07; see
   116	# ``../guardkitfactory/docs/reviews/autobuild-migration/TASK-REV-AOF-RUN9-pre-next-run-readiness-review.md``)
   117	# showed the test-orchestrator make its last model call at ~90s, then ZERO
   118	# ``/v1/responses`` POSTs for ~480s until it hit the 600s cap and
   119	# ``SDKTimeoutError``d — a genuine agent hang that wasted ~480s of idle
   120	# wall-clock and returned 0 results. A watchdog keyed on *no model activity*
   121	# terminates that hang far sooner, with a clearer signal, while the 600s cap
   122	# stays as the blunt outer backstop.
   123	#
   124	# Default 150s sits comfortably above turn-1's healthy continuous-call run
   125	# (~240s total, with model calls throughout, never a 150s silent gap) so a
   126	# normally-progressing specialist is never killed (AC-2). Operator-tunable
   127	# via ``GUARDKIT_SPECIALIST_WATCHDOG_SECONDS``; set to ``0`` to disable.
   128	_TEST_ORCHESTRATOR_NO_ACTIVITY_WATCHDOG_SECONDS: float = float(
   129	    os.environ.get("GUARDKIT_SPECIALIST_WATCHDOG_SECONDS", "150")
   130	)
   131	
   132	# TASK-PERF-SPECLAT01: the no-activity watchdog is specialist-agnostic (its env
   133	# var is already named ``GUARDKIT_SPECIALIST_WATCHDOG_SECONDS``). Expose a
   134	# generic alias so both the test-orchestrator and the code-reviewer can share
   135	# the same threshold without the misleading ``_TEST_ORCHESTRATOR_`` prefix.
   136	_SPECIALIST_NO_ACTIVITY_WATCHDOG_SECONDS: float = (
   137	    _TEST_ORCHESTRATOR_NO_ACTIVITY_WATCHDOG_SECONDS
   138	)
   139	
   140	# Distinct, grep-able reason emitted when the watchdog (not the duration cap)
   141	# terminates a specialist. AC-3: hang vs cap must be distinguishable in logs
   142	# and the review summary.
   143	_WATCHDOG_HANG_REASON_TEMPLATE: str = "hang detected (no model activity for {seconds}s)"
   144	
   145	# TASK-AB-PERTASKFG01 AC-004: Phase-4 test EXECUTION mode.
   146	#
   147	# Root cause of the per-task verification false-green (validation-smoke repro,
   148	# 2026-06-18): Phase-4 ran tests by asking a hangable LLM ``test-orchestrator``
   149	# specialist to emit ``Bash`` tool calls and self-report pass/coverage. Under
   150	# gpt-oss the specialist emitted no parseable tool call, the no-activity
   151	# watchdog tripped at 162s, ``tests_run=0`` was returned, and the narrative
   152	# regex then fabricated ``all_passed/100% coverage`` (closed downstream by
   153	# fixes #2/#3b/#4, but still a 2-3 min/turn hang). ``running tests must not be
   154	# able to hang`` — so by default Phase-4 execution is a DETERMINISTIC
   155	# venv-pinned ``&lt;venv_python&gt; -m pytest`` subprocess (no model in the loop),
   156	# reusing the Coach's proven ``run_independent_tests`` runner so Player Phase-4
   157	# and Coach independent verification execute the IDENTICAL pinned-pytest
   158	# command (single source of truth — no divergence).
   159	#
   160	# ``subprocess`` (default): deterministic-first; the LLM specialist is used
   161	#   ONLY as a fallback when no pytest test command is detectable (preserves
   162	#   non-Python / npm / dotnet stacks).
   163	# ``sdk``: emergency revert to the legacy LLM ``test-orchestrator`` specialist
   164	#   for execution (mirrors the ``GUARDKIT_HARNESS`` revert lever).
   165	def _resolve_phase_4_execution_mode() -&gt; str:
   166	    """Return the Phase-4 test-execution mode (``"subprocess"`` | ``"sdk"``).
   167	
   168	    Reads ``GUARDKIT_PHASE4_TEST_EXECUTION`` at call time (not import time) so
   169	    tests and operators can flip it per-invocation. Any unrecognised value
   170	    degrades to the deterministic default.
   171	    """
   172	    mode = os.environ.get("GUARDKIT_PHASE4_TEST_EXECUTION", "subprocess").strip().lower()
   173	    return mode if mode in ("subprocess", "sdk") else "subprocess"
   174	
   175	</message>
<message type="ai">
  <tool_call id="fc_J80czUEXkDMh3tdXnUvgbUmQBuCh4Lmf" name="edit_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/orchestrator/specialist_invocations.py", "old_string": "   mode = os.environ.get(\"GUARDKIT_PHASE4_TEST_EXECUTION\", \"subprocess\").strip().lower()\n    return mode if mode in (\"subprocess\", \"sdk\") else \"subprocess\"", "new_string": "   mode = os.environ.get(\"GUARDKIT_PHASE4_TEST_EXECUTION\", \"subprocess\").strip().lower()\n    return mode if mode in (\"subprocess\", \"sdk\") else \"subprocess\"\n\n\n# TASK-SBHO-001: env-tunable ceiling for the final specialist prompt string.\n# Mirrors the _trim_synthesis_prompt pattern: loud truncation marker,\n# WARNING log, degrade-never-raise. Default 300k chars ≈ 85k tokens.\n# Applied as a backstop AFTER the per-builder seed caps (e.g. the ~2000-char\n# seed cap in _build_code_reviewer_prompt).\nSPECIALIST_PROMPT_MAX_CHARS_ENV = \"GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS\"\nSPECIALIST_PROMPT_MAX_CHARS: int = int(\n    os.environ.get(SPECIALIST_PROMPT_MAX_CHARS_ENV, \"300000\")\n)"}</tool_call>
</message>
<message type="tool">Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/orchestrator/specialist_invocations.py'</message>
<message type="ai">
  <tool_call id="fc_pDPzWOosGZ4Ac9t1yugizbbsvzO9Sp7p" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/orchestrator/specialist_invocations.py", "limit": 60, "offset": 895}</tool_call>
</message>
<message type="tool">   896	
   897	def _build_code_reviewer_prompt(
   898	    task_id: str,
   899	    task_context: str,
   900	    phase_4_summary: dict[str, Any],
   901	) -&gt; str:
   902	    """Render the prompt the code-reviewer specialist receives.
   903	
   904	    The agent definition (``installer/core/agents/code-reviewer.md``)
   905	    already encodes the review checklist. This prompt only carries
   906	    task-specific context plus the structured Phase 4 summary so the
   907	    reviewer can ground its review in the actual test outcomes.
   908	
   909	    The string ``"Phase 4 summary"`` is part of the prompt contract — the
   910	    unit test introspects for it (TASK-OSI-005 AC d).
   911	    """
   912	    summary_lines = (
   913	        f"- tests_run: {phase_4_summary.get('tests_run', 0)}\n"
   914	        f"- tests_failed: {phase_4_summary.get('tests_failed', 0)}\n"
   915	        f"- coverage_pct: {phase_4_summary.get('coverage_pct', 0.0)}\n"
   916	        f"- quality_gates_passed: "
   917	        f"{phase_4_summary.get('quality_gates_passed', False)}\n"
   918	        f"- output_summary: {phase_4_summary.get('output_summary', '')}"
   919	    )
   920	
   921	    prompt = (
   922	        f"You are the code-reviewer specialist for task {task_id}.\n\n"
   923	        "Task context (from the task markdown):\n"
   924	        f"{task_context}\n\n"
   925	        "Phase 4 summary (test-orchestrator outcome):\n"
   926	        f"{summary_lines}\n\n"
   927	        "Your job:\n"
   928	        "1. Review the implementation in the worktree against the task's "
   929	        "acceptance criteria using Read/Search/Grep.\n"
   930	        "2. Apply the review checklist from your agent definition (build, "
   931	        "requirements, code quality, testing, security, performance, "
   932	        "documentation).\n"
   933	        "3. Report findings via your normal response stream — the "
   934	        "orchestrator records the review outcome in specialist_results.json.\n"
   935	        "Do NOT modify source files: the Write tool is intentionally "
   936	        "withheld from this invocation."
   937	    )
   938	
   939	    # Keep the prompt under ~2000 chars to match the test-orchestrator runner's
   940	    # cap. Trim the variable-length task_context first.
   941	    if len(prompt) &gt; 2000:
   942	        overflow = len(prompt) - 2000
   943	        trimmed_context = task_context[: max(0, len(task_context) - overflow - 32)]
   944	        prompt = prompt.replace(
   945	            task_context, trimmed_context + "\n[...truncated]"
   946	        )
   947	    return prompt
   948	
   949	
   950	def _parse_pytest_counts(
   951	    output: Optional[str],
   952	) -&gt; tuple[int, int, Optional[int]]:
   953	    """Parse ``(tests_run, tests_failed, tests_skipped)`` from pytest output.
   954	
   955	    ``tests_run`` = passed + failed + errors + xpassed + xfailed (skipped</message>
<message type="ai">
  <tool_call id="fc_pDellReFD3o4618EU9qsfYN40dpMWNY2" name="edit_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/orchestrator/specialist_invocations.py", "old_string": "def _build_code_reviewer_prompt(\n    task_id: str,\n    task_context: str,\n    phase_4_summary: dict[str, Any],\n) -&gt; str:\n    \"\"\"Render the prompt the code-reviewer specialist receives.\n\n    The agent definition (``installer/core/agents/code-reviewer.md``)\n    already encodes the review checklist. This prompt only carries\n    task-specific context plus the structured Phase 4 summary so the\n    reviewer can ground its review in the actual test outcomes.\n\n    The string ``\"Phase 4 summary\"`` is part of the prompt contract — the\n    unit test introspects for it (TASK-OSI-005 AC d).\n    \"\"\"\n    summary_lines = (\n        f\"- tests_run: {phase_4_summary.get('tests_run', 0)}\\n\"\n        f\"- tests_failed: {phase_4_summary.get('tests_failed', 0)}\\n\"\n        f\"- coverage_pct: {phase_4_summary.get('coverage_pct', 0.0)}\\n\"\n        f\"- quality_gates_passed: \"\n        f\"{phase_4_summary.get('quality_gates_passed', False)}\\n\"\n        f\"- output_summary: {phase_4_summary.get('output_summary', '')}\"\n    )\n\n    prompt = (\n        f\"You are the code-reviewer specialist for task {task_id}.\\n\\n\"\n        \"Task context (from the task markdown):\\n\"\n        f\"{task_context}\\n\\n\"\n        \"Phase 4 summary (test-orchestrator outcome):\\n\"\n        f\"{summary_lines}\\n\\n\"\n        \"Your job:\\n\"\n        \"1. Review the implementation in the worktree against the task's \"\n        \"acceptance criteria using Read/Search/Grep.\\n\"\n        \"2. Apply the review checklist from your agent definition (build, \"\n        \"requirements, code quality, testing, security, performance, \"\n        \"documentation).\\n\"\n        \"3. Report findings via your normal response stream — the \"\n        \"orchestrator records the review outcome in specialist_results.json.\\n\"\n        \"Do NOT modify source files: the Write tool is intentionally \"\n        \"withheld from this invocation.\"\n    )\n\n    # Keep the prompt under ~2000 chars to match the test-orchestrator runner's\n    # cap. Trim the variable-length task_context first.\n    if len(prompt) &gt; 2000:\n        overflow = len(prompt) - 2000\n        trimmed_context = task_context[: max(0, len(task_context) - overflow - 32)]\n        prompt = prompt.replace(\n            task_context, trimmed_context + \"\\n[...truncated]\"\n        )\n    return prompt", "new_string": "def _build_code_reviewer_prompt(\n    task_id: str,\n    task_context: str,\n    phase_4_summary: dict[str, Any],\n    *,\n    max_chars: int | None = None,\n) -&gt; str:\n    \"\"\"Render the prompt the code-reviewer specialist receives.\n\n    The agent definition (``installer/core/agents/code-reviewer.md``)\n    already encodes the review checklist. This prompt only carries\n    task-specific context plus the structured Phase 4 summary so the\n    reviewer can ground its review in the actual test outcomes.\n\n    The string ``\"Phase 4 summary\"`` is part of the prompt contract — the\n    unit test introspects for it (TASK-OSI-005 AC d).\n\n    Two budget layers apply:\n    1. A ~2000-char seed cap (historic, trims task_context first).\n    2. An env-tunable overall backstop\n       (``GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS``, default 300000) applied\n       after the seed cap. This is the **primary** budget for large task\n       contexts.\n\n    Truncation is **loud**: a visible notice is inserted inside the prompt\n    naming what was cut and by how much, and a WARNING is logged.\n    \"\"\"\n    if max_chars is None:\n        max_chars = SPECIALIST_PROMPT_MAX_CHARS\n\n    summary_lines = (\n        f\"- tests_run: {phase_4_summary.get('tests_run', 0)}\\n\"\n        f\"- tests_failed: {phase_4_summary.get('tests_failed', 0)}\\n\"\n        f\"- coverage_pct: {phase_4_summary.get('coverage_pct', 0.0)}\\n\"\n        f\"- quality_gates_passed: \"\n        f\"{phase_4_summary.get('quality_gates_passed', False)}\\n\"\n        f\"- output_summary: {phase_4_summary.get('output_summary', '')}\"\n    )\n\n    prompt = (\n        f\"You are the code-reviewer specialist for task {task_id}.\\n\\n\"\n        \"Task context (from the task markdown):\\n\"\n        f\"{task_context}\\n\\n\"\n        \"Phase 4 summary (test-orchestrator outcome):\\n\"\n        f\"{summary_lines}\\n\\n\"\n        \"Your job:\\n\"\n        \"1. Review the implementation in the worktree against the task's \"\n        \"acceptance criteria using Read/Search/Grep.\\n\"\n        \"2. Apply the review checklist from your agent definition (build, \"\n        \"requirements, code quality, testing, security, performance, \"\n        \"documentation).\\n\"\n        \"3. Report findings via your normal response stream — the \"\n        \"orchestrator records the review outcome in specialist_results.json.\\n\"\n        \"Do NOT modify source files: the Write tool is intentionally \"\n        \"withheld from this invocation.\"\n    )\n\n    # Layer 1: Keep the prompt under ~2000 chars to match the\n    # test-orchestrator runner's seed cap. Trim the variable-length\n    # task_context first.\n    if len(prompt) &gt; 2000:\n        overflow = len(prompt) - 2000\n        trimmed_context = task_context[: max(0, len(task_context) - overflow - 32)]\n        prompt = prompt.replace(\n            task_context, trimmed_context + \"\\n[...truncated]\"\n        )\n\n    # Layer 2: Overall backstop budget (env-tunable). Applied after the\n    # seed cap so the 2000-char historic behaviour is preserved when under\n    # budget. Trim task_context first (it's the variable-length section).\n    if len(prompt) &gt; max_chars:\n        overflow = len(prompt) - max_chars\n        # Find where task_context appears and trim it.\n        task_context_marker = \"Task context (from the task markdown):\\n\"\n        ctx_start = prompt.find(task_context_marker)\n        if ctx_start != -1:\n            ctx_start += len(task_context_marker)\n            # Find the end of the task_context (next double-newline or end)\n            ctx_end = prompt.find(\"\\n\\n\", ctx_start)\n            if ctx_end != -1:\n                original_ctx = prompt[ctx_start:ctx_end]\n                keep_ctx = max(0, len(original_ctx) - overflow)\n                trimmed_ctx = original_ctx[:keep_ctx]\n                prompt = (\n                    prompt[:ctx_start]\n                    + trimmed_ctx\n                    + f\"\\n\\n[...truncated: {overflow} more chars of task \"\n                    f\"context elided to fit within {max_chars}-char budget.]\"\n                    + prompt[ctx_end:]\n                )\n                logger.warning(\n                    \"specialist prompt: task_context truncated (%d chars \"\n                    \"elided) to fit within %d-char budget\",\n                    overflow,\n                    max_chars,\n                )\n            else:\n                prompt = (\n                    prompt[:max_chars]\n                    + f\"\\n... [specialist prompt truncated at \"\n                    f\"{max_chars} chars — {len(prompt) - max_chars} more \"\n                    f\"chars not shown.]\"\n                )\n                logger.warning(\n                    \"specialist prompt: hard-trimmed at %d chars (%d chars \"\n                    \"elided)\",\n                    max_chars,\n                    len(prompt) - max_chars,\n                )\n        else:\n            prompt = (\n                prompt[:max_chars]\n                + f\"\\n... [specialist prompt truncated at {max_chars} chars \"\n                f\"— {len(prompt) - max_chars} more chars not shown.]\"\n            )\n            logger.warning(\n                \"specialist prompt: hard-trimmed at %d chars (%d chars \"\n                \"elided)\",\n                max_chars,\n                len(prompt) - max_chars,\n            )\n\n    return prompt"}</tool_call>
</message>
<message type="tool">Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/guardkit/orchestrator/specialist_invocations.py'</message>
<message type="ai">
  <tool_call id="fc_pnWXQAh94tmrcglWwcM7elJykM3MpiPM" name="write_todos">{"todos": [{"content": "Add GUARDKIT_REVIEW_SEAT_MAX_CHARS budget to build_seat_messages in review_seat.py", "status": "completed"}, {"content": "Add GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS budget to _build_code_reviewer_prompt in specialist_invocations.py", "status": "completed"}, {"content": "Add test for review-seat budget bounding", "status": "in_progress"}, {"content": "Add test for specialist prompt budget bounding", "status": "pending"}, {"content": "Run tests and verify", "status": "pending"}, {"content": "Write player report JSON", "status": "pending"}]}</tool_call>
</message>
<message type="tool">Updated todo list to [{'content': 'Add GUARDKIT_REVIEW_SEAT_MAX_CHARS budget to build_seat_messages in review_seat.py', 'status': 'completed'}, {'content': 'Add GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS budget to _build_code_reviewer_prompt in specialist_invocations.py', 'status': 'completed'}, {'content': 'Add test for review-seat budget bounding', 'status': 'in_progress'}, {'content': 'Add test for specialist prompt budget bounding', 'status': 'pending'}, {'content': 'Run tests and verify', 'status': 'pending'}, {'content': 'Write player report JSON', 'status': 'pending'}]</message>
<message type="ai">
  <tool_call id="fc_FMkTA2Z1KP68ZQiGRU3WXhE0Qv0h4fuj" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py", "limit": 50, "offset": 520}</tool_call>
</message>
<message type="tool">   521	        assert "not an allowed local seat" in outcome.error
   522	
   523	
   524	# ===========================================================================
   525	# 8. Prompt assembly sanity
   526	# ===========================================================================
   527	
   528	
   529	class TestPrompt:
   530	    def test_render_includes_diff_markers(self, payload):
   531	        text = render_payload_for_seat(payload)
   532	        assert "pkg/calc.py" in text
   533	        assert "+    total = 0" in text
   534	        assert "-    return sum(xs) / len(xs)" in text
   535	
   536	    def test_messages_carry_subject_and_diff(self, payload):
   537	        system, user = build_seat_messages(payload)
   538	        assert "INSPECTOR" in system
   539	        assert "JSON object" in system
   540	        assert "kind: commit" in user
   541	        assert "pkg/calc.py" in user
   542	
   543	
   544	# ===========================================================================
   545	# 9. ONE real-seat integration smoke (seat-law-checked; auto-skips)
   546	# ===========================================================================
   547	
   548	
   549	@pytest.mark.integration
   550	def test_real_seat_smoke(tmp_path: Path, payload, monkeypatch: pytest.MonkeyPatch):
   551	    """Drive the REAL local seat once, honesty-to-state.
   552	
   553	    Seat-law-checked: probes ``/running`` first and SKIPS (never collides) if the
   554	    seat is unreachable or a live drive holds the single slot. Asserts the
   555	    advisory contract holds against a real model — either a schema-valid F14
   556	    record OR a NAMED error (an unrunnable/unparseable seat is a finding, never a
   557	    faked green). It never asserts specific findings (model output varies).
   558	    """
   559	    probe = _default_running_probe(DEFAULT_BASE_URL)
   560	    running = probe()
   561	    if running is None:
   562	        pytest.skip("llama-swap /running unreachable — seat not available")
   563	    free, reason = check_single_slot(running)
   564	    if not free:
   565	        pytest.skip(f"seat busy, refusing to collide: {reason}")
   566	
   567	    monkeypatch.setenv(REVIEW_SEAT_ENV, "1")
   568	    outcome = run_advisory_review(
   569	        tmp_path, payload, model=DEFAULT_SEAT, write=True
   570	    )</message>
<message type="ai">
  <tool_call id="fc_adAFfstUbrH7ZogFKivT2PHe7tLDfCri" name="edit_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py", "old_string": "   def test_messages_carry_subject_and_diff(self, payload):\n        system, user = build_seat_messages(payload)\n        assert \"INSPECTOR\" in system\n        assert \"JSON object\" in system\n        assert \"kind: commit\" in user\n        assert \"pkg/calc.py\" in user", "new_string": "   def test_messages_carry_subject_and_diff(self, payload):\n        system, user = build_seat_messages(payload)\n        assert \"INSPECTOR\" in system\n        assert \"JSON object\" in system\n        assert \"kind: commit\" in user\n        assert \"pkg/calc.py\" in user\n\n\nclass TestReviewSeatBudget:\n    \"\"\"TASK-SBHO-001 AC-001: GUARDKIT_REVIEW_SEAT_MAX_CHARS bounds the\n    assembled review-seat user message.\n    \"\"\"\n\n    def _big_payload(self) -&gt; ReviewPayload:\n        \"\"\"Create a payload with a large diff to help exceed budget.\"\"\"\n        big_diff_lines = \"\\n\".join(\n            f\"@@ -{i},{i} +{i},{i} @@\\n+ line {i} of added content that is deliberately long\"\n            for i in range(500)\n        )\n        big_diff = f\"diff --git a/pkg/big.py b/pkg/big.py\\n{big_diff_lines}\"\n        return ReviewPayload(\n            subject_kind=\"commit\",\n            ref=\"big1234\",\n            context_lines=3,\n            files=parse_unified_diff(big_diff),\n        )\n\n    def test_oversized_payload_fits_budget_with_truncation_marker(self):\n        \"\"\"An oversized payload (huge repo_context + big diff) must fit the\n        budget and contain the loud truncation marker.\n        \"\"\"\n        huge_repo = \"x\" * 200_000  # 200k chars of repo context\n        payload = self._big_payload()\n        budget = 300_000\n\n        system, user = build_seat_messages(payload, repo_context=huge_repo, max_chars=budget)\n\n        # Must fit within budget\n        assert len(user) &lt;= budget, f\"user message {len(user)} chars exceeds budget {budget}\"\n        # Must contain truncation marker\n        assert \"[...truncated\" in user or \"[repository context truncated\" in user, (\n            \"truncation marker missing from oversized payload\"\n        )\n        # Instruction header must NOT be trimmed\n        assert \"## Review subject\" in user\n        # Finding-schema section must NOT be trimmed\n        assert \"## Diff under review\" in user\n\n    def test_trims_repo_context_before_diff(self):\n        \"\"\"When trimming is needed, repo_context must be trimmed before the diff.\"\"\"\n        huge_repo = \"y\" * 200_000\n        payload = self._big_payload()\n        budget = 250_000\n\n        system, user = build_seat_messages(payload, repo_context=huge_repo, max_chars=budget)\n\n        # The user message should contain the truncation marker for repo_context\n        # (not for the diff), indicating repo_context was trimmed first\n        assert \"repository context truncated\" in user.lower() or \"repo_context truncated\" in user.lower(), (\n            \"repo_context should be trimmed before diff\"\n        )\n\n    def test_never_trims_instruction_header(self):\n        \"\"\"The instruction header (review subject) must never be trimmed.\"\"\"\n        huge_repo = \"z\" * 500_000\n        payload = self._big_payload()\n        budget = 50_000  # Very tight budget\n\n        system, user = build_seat_messages(payload, repo_context=huge_repo, max_chars=budget)\n\n        # Subject section must always be present\n        assert \"## Review subject\" in user\n        assert payload.subject_kind in user\n        assert payload.ref in user\n\n    def test_never_trims_finding_schema_section(self):\n        \"\"\"The finding-schema section (diff header) must never be trimmed.\"\"\"\n        huge_repo = \"w\" * 500_000\n        payload = self._big_payload()\n        budget = 50_000  # Very tight budget\n\n        system, user = build_seat_messages(payload, repo_context=huge_repo, max_chars=budget)\n\n        # Diff section header must always be present\n        assert \"## Diff under review\" in user\n\n    def test_no_truncation_marker_when_under_budget(self):\n        \"\"\"When the assembled message is under budget, no truncation marker.\"\"\"\n        small_repo = \"small context\"\n        payload = self._big_payload()\n        budget = 500_000  # Large budget\n\n        system, user = build_seat_messages(payload, repo_context=small_repo, max_chars=budget)\n\n        assert len(user) &lt;= budget\n        assert \"[...truncated\" not in user"}</tool_call>
</message>
<message type="tool">Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py'</message>
<message type="ai">
  <tool_call id="fc_d8NMNiC8nSxgSFOvhrNYVrczASd3HdNN" name="execute">{"command": "wc -l /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py"}</tool_call>
</message>
<message type="tool">1758 /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py

[Command succeeded with exit code 0]</message>
<message type="ai">
  <tool_call id="fc_SIWbiWz6yMnhcec9vxXCryofWFwkKVHR" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py", "offset": 1740, "limit": 20}</tool_call>
</message>
<message type="tool">  1741	    )
  1742	
  1743	    invoker = _make_fake_agent_invoker()
  1744	
  1745	    result = await invoke_test_orchestrator(
  1746	        worktree_path=tmp_path,
  1747	        task_id=_TASK_ID_DET,
  1748	        sdk_timeout=900,
  1749	        agent_invoker=invoker,
  1750	    )
  1751	
  1752	    assert result.status == "passed"
  1753	    invoker._invoke_with_role.assert_not_awaited()
  1754	
  1755	    block = json.loads(_det_results_path(tmp_path).read_text())["phase_4"]
  1756	    assert block["status"] == "passed"
  1757	    assert block["tests_run"] == 2
  1758	    assert block["quality_gates_passed"] is True</message>
<message type="ai">
  <tool_call id="fc_OZS0cyJh58xRmAlYDnkBRPFiW4Ctynve" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py", "limit": 40, "offset": 1}</tool_call>
</message>
<message type="tool">     2	
     3	Pins the contract that TASK-OSI-004 / TASK-OSI-005 build on:
     4	
     5	* :func:`run_specialist` delegates to ``AgentInvoker._invoke_with_role``
     6	  with the right agent_type / permission_mode for each specialist.
     7	* The runner restores ``sdk_timeout_seconds`` and ``_cancellation_event``
     8	  on the AgentInvoker after the call, even when the call raises.
     9	* On exception, the runner returns ``status="failed"`` with ``error``
    10	  populated and reaps child claude processes — it never propagates the
    11	  exception.
    12	"""
    13	
    14	from __future__ import annotations
    15	
    16	import json
    17	import threading
    18	from pathlib import Path
    19	from unittest.mock import AsyncMock, MagicMock
    20	
    21	import pytest
    22	
    23	import asyncio
    24	import time
    25	
    26	from guardkit.orchestrator import specialist_invocations
    27	from guardkit.orchestrator.specialist_invocations import (
    28	    SpecialistInvocationResult,
    29	    _no_activity_watchdog_exceeded,
    30	    invoke_code_reviewer,
    31	    invoke_test_orchestrator,
    32	    run_specialist,
    33	)
    34	
    35	
    36	def _make_fake_agent_invoker(
    37	    *,
    38	    invoke_side_effect=None,
    39	    sdk_timeout_seconds: int = 1200,
    40	    cancellation_event: threading.Event | None = None,
    41	) -&gt; MagicMock:</message>
<message type="ai">
  <tool_call id="fc_QODGeaED9zo0C49DwWtUh7M9a1usBZNP" name="edit_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py", "old_string": "from guardkit.orchestrator.specialist_invocations import (\n    SpecialistInvocationResult,\n    _no_activity_watchdog_exceeded,\n    invoke_code_reviewer,\n    invoke_test_orchestrator,\n    run_specialist,\n)", "new_string": "from guardkit.orchestrator.specialist_invocations import (\n    SpecialistInvocationResult,\n    _build_code_reviewer_prompt,\n    _no_activity_watchdog_exceeded,\n    invoke_code_reviewer,\n    invoke_test_orchestrator,\n    run_specialist,\n)"}</tool_call>
</message>
<message type="tool">Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py'</message>
<message type="ai">
  <tool_call id="fc_u94DdwfwT3Bm1XP2fO2RmyJnkyJeVdEq" name="edit_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py", "old_string": "   block = json.loads(_det_results_path(tmp_path).read_text())[\"phase_4\"]\n    assert block[\"status\"] == \"passed\"\n    assert block[\"tests_run\"] == 2\n    assert block[\"quality_gates_passed\"] is True", "new_string": "   block = json.loads(_det_results_path(tmp_path).read_text())[\"phase_4\"]\n    assert block[\"status\"] == \"passed\"\n    assert block[\"tests_run\"] == 2\n    assert block[\"quality_gates_passed\"] is True\n\n\n# =============================================================================\n# TASK-SBHO-001: Specialist prompt budget\n# =============================================================================\n\n\nclass TestSpecialistPromptBudget:\n    \"\"\"TASK-SBHO-001 AC-002: GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS backstops\n    the final prompt for the specialist builders.\n    \"\"\"\n\n    def _big_task_context(self) -&gt; str:\n        \"\"\"Generate a task context large enough to exceed a tight budget.\"\"\"\n        return \"x\" * 200_000\n\n    def test_oversized_prompt_fits_budget_with_truncation_marker(self):\n        \"\"\"An oversized prompt must fit the budget and contain the truncation marker.\"\"\"\n        huge_context = self._big_task_context()\n        phase_4_summary = {\n            \"tests_run\": 10,\n            \"tests_failed\": 0,\n            \"coverage_pct\": 85.0,\n            \"quality_gates_passed\": True,\n            \"output_summary\": \"All tests passed.\",\n        }\n        budget = 300_000\n\n        prompt = _build_code_reviewer_prompt(\n            \"TASK-TEST-001\",\n            huge_context,\n            phase_4_summary,\n            max_chars=budget,\n        )\n\n        assert len(prompt) &lt;= budget, f\"prompt {len(prompt)} chars exceeds budget {budget}\"\n        assert \"[...truncated\" in prompt, \"truncation marker missing\"\n        assert \"Phase 4 summary\" in prompt, \"Phase 4 summary must be preserved\"\n\n    def test_under_budget_no_truncation(self):\n        \"\"\"When the prompt is under budget, no truncation marker.\"\"\"\n        small_context = \"small context\"\n        phase_4_summary = {\n            \"tests_run\": 10,\n            \"tests_failed\": 0,\n            \"coverage_pct\": 85.0,\n            \"quality_gates_passed\": True,\n            \"output_summary\": \"All tests passed.\",\n        }\n        budget = 500_000\n\n        prompt = _build_code_reviewer_prompt(\n            \"TASK-TEST-001\",\n            small_context,\n            phase_4_summary,\n            max_chars=budget,\n        )\n\n        assert len(prompt) &lt;= budget\n        assert \"[...truncated\" not in prompt\n\n    def test_seed_cap_unchanged_when_under_budget(self):\n        \"\"\"The existing ~2000-char seed cap behaviour is unchanged when under budget.\"\"\"\n        # A context that keeps the prompt over 2000 but well under 300k\n        medium_context = \"a\" * 5000\n        phase_4_summary = {\n            \"tests_run\": 10,\n            \"tests_failed\": 0,\n            \"coverage_pct\": 85.0,\n            \"quality_gates_passed\": True,\n            \"output_summary\": \"All tests passed.\",\n        }\n        budget = 300_000\n\n        prompt = _build_code_reviewer_prompt(\n            \"TASK-TEST-001\",\n            medium_context,\n            phase_4_summary,\n            max_chars=budget,\n        )\n\n        # The prompt should be under 2000 chars due to the seed cap\n        assert len(prompt) &lt; 2000, (\n            \"seed cap should still apply at ~2000 chars when under overall budget\"\n        )\n\n    def test_backstop_applied_after_seed_cap(self):\n        \"\"\"The env-tunable backstop is applied AFTER the 2000-char seed cap.\"\"\"\n        huge_context = \"b\" * 200_000\n        phase_4_summary = {\n            \"tests_run\": 10,\n            \"tests_failed\": 0,\n            \"coverage_pct\": 85.0,\n            \"quality_gates_passed\": True,\n            \"output_summary\": \"All tests passed.\",\n        }\n        # Set budget to something between 2000 and the full prompt size\n        budget = 5000\n\n        prompt = _build_code_reviewer_prompt(\n            \"TASK-TEST-001\",\n            huge_context,\n            phase_4_summary,\n            max_chars=budget,\n        )\n\n        # Should fit within the backstop budget\n        assert len(prompt) &lt;= budget, f\"prompt {len(prompt)} chars exceeds backstop {budget}\""}</tool_call>
</message>
<message type="tool">Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/unit/orchestrator/test_specialist_invocations.py'</message>
<message type="ai">
  <tool_call id="fc_fc7EaViIQU8P6xQC3Z25AXDTfPkJmFLM" name="write_todos">{"todos": [{"content": "Add GUARDKIT_REVIEW_SEAT_MAX_CHARS budget to build_seat_messages in review_seat.py", "status": "completed"}, {"content": "Add GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS budget to _build_code_reviewer_prompt in specialist_invocations.py", "status": "completed"}, {"content": "Add test for review-seat budget bounding", "status": "completed"}, {"content": "Add test for specialist prompt budget bounding", "status": "completed"}, {"content": "Run tests and verify", "status": "in_progress"}, {"content": "Write player report JSON", "status": "pending"}]}</tool_call>
</message>
<message type="tool">Updated todo list to [{'content': 'Add GUARDKIT_REVIEW_SEAT_MAX_CHARS budget to build_seat_messages in review_seat.py', 'status': 'completed'}, {'content': 'Add GUARDKIT_SPECIALIST_PROMPT_MAX_CHARS budget to _build_code_reviewer_prompt in specialist_invocations.py', 'status': 'completed'}, {'content': 'Add test for review-seat budget bounding', 'status': 'completed'}, {'content': 'Add test for specialist prompt budget bounding', 'status': 'completed'}, {'content': 'Run tests and verify', 'status': 'in_progress'}, {'content': 'Write player report JSON', 'status': 'pending'}]</message>
<message type="ai">
  <tool_call id="fc_PLP0TbgcgqREgRztDJwHIPyuZS2SfTO8" name="execute">{"command": "cd /home/richardwoollcott/Projects/appmilla_github/guardkit &amp;&amp; python -m pytest tests/qa/test_review_seat.py::TestReviewSeatBudget -xvs 2&gt;&amp;1 | head -100", "timeout": 120}</tool_call>
</message>
<message type="tool">/bin/sh: 1: python: not found

[Command succeeded with exit code 0]</message>
<message type="ai">
  <tool_call id="fc_2yP7Ql7d1QbLVVKiHJUDVgsXN5rEQzXB" name="execute">{"command": "which python3 &amp;&amp; python3 --version"}</tool_call>
</message>
<message type="tool">/usr/bin/python3
Python 3.12.3

[Command succeeded with exit code 0]</message>
<message type="ai">
  <tool_call id="fc_dioo7eHYdJ3epV0Nc2PbzMmUjjVElvSi" name="execute">{"command": "cd /home/richardwoollcott/Projects/appmilla_github/guardkit &amp;&amp; ls -la .venv/bin/python 2&gt;/dev/null || ls -la venv/bin/python 2&gt;/dev/null || echo \"No venv found\""}</tool_call>
</message>
<message type="tool">lrwxrwxrwx 1 richardwoollcott richardwoollcott 19 Jun 11 15:20 .venv/bin/python -&gt; /usr/bin/python3.12

[Command succeeded with exit code 0]</message>
<message type="ai">
  <tool_call id="fc_SnQw1llPCGfzQsNZSJoUJLL6o6ZuNbWf" name="execute">{"command": "cd /home/richardwoollcott/Projects/appmilla_github/guardkit &amp;&amp; .venv/bin/python -m pytest tests/qa/test_review_seat.py::TestReviewSeatBudget -xvs 2&gt;&amp;1 | head -100", "timeout": 120}</tool_call>
</message>
<message type="tool">============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /home/richardwoollcott/Projects/appmilla_github/guardkit/.venv/bin/python
cachedir: .pytest_cache
rootdir: /home/richardwoollcott/Projects/appmilla_github/guardkit
configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)
plugins: timeout-2.4.0, anyio-4.14.2, cov-7.1.0, bdd-8.1.0, asyncio-1.4.0, langsmith-0.8.14
asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
collecting ... ERROR: not found: /home/richardwoollcott/Projects/appmilla_github/guardkit/tests/qa/test_review_seat.py::TestReviewSeatBudget
(no match in any of [&lt;Module test_review_seat.py&gt;])

collected 0 items

============================ no tests ran in 0.19s =============================

[Command succeeded with exit code 0]</message>
<message type="ai">
  <tool_call id="fc_o1FCPCWorIbuQKNFFEugb3YeP4VGulIz" name="execute">{"command": "ls -la /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py"}</tool_call>
</message>
<message type="tool">-rw-rw-r-- 1 richardwoollcott richardwoollcott 25044 Jul 26 00:36 /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py

[Command succeeded with exit code 0]</message>
<message type="ai">
  <tool_call id="fc_AftpaQhZgbYkkr4lpm9aLAgtcbTM2pV3" name="execute">{"command": "cd /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO &amp;&amp; ls -la .venv/bin/python 2&gt;/dev/null || echo \"No venv in worktree\""}</tool_call>
</message>
<message type="tool">lrwxrwxrwx 1 richardwoollcott richardwoollcott 19 Jul 26 00:12 .venv/bin/python -&gt; /usr/bin/python3.12

[Command succeeded with exit code 0]</message>
<message type="ai">
  <tool_call id="fc_9gcao1G7UZ55AefaPuqihG3Q7eULbAH4" name="execute">{"command": "cd /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO &amp;&amp; .venv/bin/python -m pytest tests/qa/test_review_seat.py::TestReviewSeatBudget -xvs 2&gt;&amp;1 | head -150", "timeout": 120}</tool_call>
</message>
<message type="tool">Tool result too large, the result of this tool call fc_9gcao1G7UZ55AefaPuqihG3Q7eULbAH4 was saved in the filesystem at this path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/large_tool_results/fc_9gcao1G7UZ55AefaPuqihG3Q7eULbAH4

You can read the result from the filesystem by using the read_file tool, but make sure to only read part of the result at a time.

You can do this by specifying an offset and limit in the read_file tool call. For example, to read the first 100 lines, you can use the read_file tool with offset=0 and limit=100.

Here is a preview showing the head and tail of the result (lines of the form `... [N lines truncated] ...` indicate omitted lines in the middle of the content):

     1	============================= test session starts ==============================
     2	platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.venv/bin/python
     3	cachedir: .pytest_cache
     4	rootdir: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO
     5	configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)
... [14 lines truncated] ...
    20	assert ('[...truncated' in '## Review subject\n\nkind: commit \xb7 ref: big1234\n\n## Repository context (reference)\n\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    21	!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
    22	============================== 1 failed in 0.34s ===============================
    23	
    24	[Command succeeded with exit code 0]
</message>
<message type="ai">
  <tool_call id="fc_zqezNDEjWNaeIaDbxsPdeUYX5ShwNbXv" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/large_tool_results/fc_9gcao1G7UZ55AefaPuqihG3Q7eULbAH4", "limit": 50}</tool_call>
</message>
<message type="tool">     1	============================= test session starts ==============================
     2	platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.venv/bin/python
     3	cachedir: .pytest_cache
     4	rootdir: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO
     5	configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)
     6	plugins: timeout-2.4.0, anyio-4.14.2, cov-7.1.0, bdd-8.1.0, asyncio-1.4.0
     7	asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
     8	collecting ... collected 5 items
     9	
    10	tests/qa/test_review_seat.py::TestReviewSeatBudget::test_oversized_payload_fits_budget_with_truncation_marker FAILED
    11	
    12	=================================== FAILURES ===================================
    13	_ TestReviewSeatBudget.test_oversized_payload_fits_budget_with_truncation_marker _
    14	tests/qa/test_review_seat.py:576: in test_oversized_payload_fits_budget_with_truncation_marker
    15	    assert "[...truncated" in user or "[repository context truncated" in user, (
    16	E   AssertionError: truncation marker missing from oversized payload
    17	E   assert ('[...truncated' in '## Review subject\n\nkind: commit \xb7 ref: big1234\n\n## Repository context (reference)\n\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.1	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.2	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.3	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.4	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.5	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.6	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.7	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.8	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.9	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 17.10	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 17.11	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 17.12	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 17.13	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 17.14	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 17.15	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

[Output was truncated due to size limits. The file content is very large. Consider reformatting the file to make it easier to navigate. For example, if this is JSON, use execute(command='jq . /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/large_tool_results/fc_9gcao1G7UZ55AefaPuqihG3Q7eULbAH4') to pretty-print it with line breaks. For other formats, you can use appropriate formatting tools to split long lines.]</message>
<message type="ai">
  <content>The test is failing because the total payload (200k repo_context + ~35k diff) is under the 300k budget. I need to adjust the test to use a tighter budget or larger payload.

</content>
  <tool_call id="fc_nrxZCRlRVbTMKJIi2Rf399KWSTPuqrpO" name="edit_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py", "old_string": "   def test_oversized_payload_fits_budget_with_truncation_marker(self):\n        \"\"\"An oversized payload (huge repo_context + big diff) must fit the\n        budget and contain the loud truncation marker.\n        \"\"\"\n        huge_repo = \"x\" * 200_000  # 200k chars of repo context\n        payload = self._big_payload()\n        budget = 300_000\n\n        system, user = build_seat_messages(payload, repo_context=huge_repo, max_chars=budget)\n\n        # Must fit within budget\n        assert len(user) &lt;= budget, f\"user message {len(user)} chars exceeds budget {budget}\"\n        # Must contain truncation marker\n        assert \"[...truncated\" in user or \"[repository context truncated\" in user, (\n            \"truncation marker missing from oversized payload\"\n        )\n        # Instruction header must NOT be trimmed\n        assert \"## Review subject\" in user\n        # Finding-schema section must NOT be trimmed\n        assert \"## Diff under review\" in user", "new_string": "   def test_oversized_payload_fits_budget_with_truncation_marker(self):\n        \"\"\"An oversized payload (huge repo_context + big diff) must fit the\n        budget and contain the loud truncation marker.\n        \"\"\"\n        huge_repo = \"x\" * 200_000  # 200k chars of repo context\n        payload = self._big_payload()\n        budget = 250_000  # Tighter budget to force truncation\n\n        system, user = build_seat_messages(payload, repo_context=huge_repo, max_chars=budget)\n\n        # Must fit within budget\n        assert len(user) &lt;= budget, f\"user message {len(user)} chars exceeds budget {budget}\"\n        # Must contain truncation marker\n        assert \"[...truncated\" in user, (\n            f\"truncation marker missing from oversized payload (len={len(user)}, budget={budget})\"\n        )\n        # Instruction header must NOT be trimmed\n        assert \"## Review subject\" in user\n        # Finding-schema section must NOT be trimmed\n        assert \"## Diff under review\" in user"}</tool_call>
</message>
<message type="tool">Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py'</message>
<message type="ai">
  <tool_call id="fc_4VPWnWGfm3r1ahUnNgcD2KmbvYgeq4h5" name="execute">{"command": "cd /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO &amp;&amp; .venv/bin/python -m pytest tests/qa/test_review_seat.py::TestReviewSeatBudget -xvs 2&gt;&amp;1 | tail -50", "timeout": 120}</tool_call>
</message>
<message type="tool">Tool result too large, the result of this tool call fc_4VPWnWGfm3r1ahUnNgcD2KmbvYgeq4h5 was saved in the filesystem at this path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/large_tool_results/fc_4VPWnWGfm3r1ahUnNgcD2KmbvYgeq4h5

You can read the result from the filesystem by using the read_file tool, but make sure to only read part of the result at a time.

You can do this by specifying an offset and limit in the read_file tool call. For example, to read the first 100 lines, you can use the read_file tool with offset=0 and limit=100.

Here is a preview showing the head and tail of the result (lines of the form `... [N lines truncated] ...` indicate omitted lines in the middle of the content):

     1	============================= test session starts ==============================
     2	platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.venv/bin/python
     3	cachedir: .pytest_cache
     4	rootdir: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO
     5	configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)
... [14 lines truncated] ...
    20	assert '[...truncated' in '## Review subject\n\nkind: commit \xb7 ref: big1234\n\n## Repository context (reference)\n\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    21	!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
    22	============================== 1 failed in 0.32s ===============================
    23	
    24	[Command succeeded with exit code 0]
</message>
<message type="ai">
  <tool_call id="fc_7AbOBVMdG7x6x6bFQ7EoQnEXFk0HlqgF" name="read_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/large_tool_results/fc_4VPWnWGfm3r1ahUnNgcD2KmbvYgeq4h5", "limit": 25}</tool_call>
</message>
<message type="tool">     1	============================= test session starts ==============================
     2	platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.venv/bin/python
     3	cachedir: .pytest_cache
     4	rootdir: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO
     5	configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)
     6	plugins: timeout-2.4.0, anyio-4.14.2, cov-7.1.0, bdd-8.1.0, asyncio-1.4.0
     7	asyncio: mode=Mode.AUTO, debug=False, asyncio_default_fixture_loop_scope=function, asyncio_default_test_loop_scope=function
     8	collecting ... collected 5 items
     9	
    10	tests/qa/test_review_seat.py::TestReviewSeatBudget::test_oversized_payload_fits_budget_with_truncation_marker FAILED
    11	
    12	=================================== FAILURES ===================================
    13	_ TestReviewSeatBudget.test_oversized_payload_fits_budget_with_truncation_marker _
    14	tests/qa/test_review_seat.py:576: in test_oversized_payload_fits_budget_with_truncation_marker
    15	    assert "[...truncated" in user, (
    16	E   AssertionError: truncation marker missing from oversized payload (len=238633, budget=250000)
    17	E   assert '[...truncated' in '## Review subject\n\nkind: commit \xb7 ref: big1234\n\n## Repository context (reference)\n\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.1	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.2	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.3	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.4	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.5	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.6	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.7	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.8	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
  17.9	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 17.10	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 17.11	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 17.12	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 17.13	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 17.14	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
 17.15	xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

[Output was truncated due to size limits. The file content is very large. Consider reformatting the file to make it easier to navigate. For example, if this is JSON, use execute(command='jq . /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/large_tool_results/fc_4VPWnWGfm3r1ahUnNgcD2KmbvYgeq4h5') to pretty-print it with line breaks. For other formats, you can use appropriate formatting tools to split long lines.]</message>
<message type="ai">
  <content>The message is 238,633 chars, under the 250,000 budget. I need to use a tighter budget to force truncation.

</content>
  <tool_call id="fc_pd8JMXs9DbCOkz1x9iUpegGgWUcz0wUB" name="edit_file">{"file_path": "/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py", "old_string": "  def test_oversized_payload_fits_budget_with_truncation_marker(self):\n        \"\"\"An oversized payload (huge repo_context + big diff) must fit the\n        budget and contain the loud truncation marker.\n        \"\"\"\n        huge_repo = \"x\" * 200_000  # 200k chars of repo context\n        payload = self._big_payload()\n        budget = 250_000  # Tighter budget to force truncation\n\n        system, user = build_seat_messages(payload, repo_context=huge_repo, max_chars=budget)\n\n        # Must fit within budget\n        assert len(user) &lt;= budget, f\"user message {len(user)} chars exceeds budget {budget}\"\n        # Must contain truncation marker\n        assert \"[...truncated\" in user, (\n            f\"truncation marker missing from oversized payload (len={len(user)}, budget={budget})\"\n        )\n        # Instruction header must NOT be trimmed\n        assert \"## Review subject\" in user\n        # Finding-schema section must NOT be trimmed\n        assert \"## Diff under review\" in user", "new_string": "  def test_oversized_payload_fits_budget_with_truncation_marker(self):\n        \"\"\"An oversized payload (huge repo_context + big diff) must fit the\n        budget and contain the loud truncation marker.\n        \"\"\"\n        huge_repo = \"x\" * 200_000  # 200k chars of repo context\n        payload = self._big_payload()\n        budget = 200_000  # Tighter budget to force truncation (message ~239k)\n\n        system, user = build_seat_messages(payload, repo_context=huge_repo, max_chars=budget)\n\n        # Must fit within budget\n        assert len(user) &lt;= budget, f\"user message {len(user)} chars exceeds budget {budget}\"\n        # Must contain truncation marker\n        assert \"[...truncated\" in user, (\n            f\"truncation marker missing from oversized payload (len={len(user)}, budget={budget})\"\n        )\n        # Instruction header must NOT be trimmed\n        assert \"## Review subject\" in user\n        # Finding-schema section must NOT be trimmed\n        assert \"## Diff under review\" in user"}</tool_call>
</message>
<message type="tool">Successfully replaced 1 instance(s) of the string in '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/tests/qa/test_review_seat.py'</message>
<message type="ai">
  <tool_call id="fc_abzaT6GgKELjjvy71sMzzmjMH0PZyyp9" name="execute">{"command": "cd /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO &amp;&amp; .venv/bin/python -m pytest tests/qa/test_review_seat.py::TestReviewSeatBudget -xvs 2&gt;&amp;1 | tail -30", "timeout": 120}</tool_call>
</message>
<message type="tool">Tool result too large, the result of this tool call fc_abzaT6GgKELjjvy71sMzzmjMH0PZyyp9 was saved in the filesystem at this path: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/large_tool_results/fc_abzaT6GgKELjjvy71sMzzmjMH0PZyyp9

You can read the result from the filesystem by using the read_file tool, but make sure to only read part of the result at a time.

You can do this by specifying an offset and limit in the read_file tool call. For example, to read the first 100 lines, you can use the read_file tool with offset=0 and limit=100.

Here is a preview showing the head and tail of the result (lines of the form `... [N lines truncated] ...` indicate omitted lines in the middle of the content):

     1	============================= test session starts ==============================
     2	platform linux -- Python 3.12.3, pytest-9.1.1, pluggy-1.6.0 -- /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO/.venv/bin/python
     3	cachedir: .pytest_cache
     4	rootdir: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-SBHO
     5	configfile: pytest.ini (WARNING: ignoring pytest config in pyproject.toml!)
... [19 lines truncated] ...
    25	 +  where 200081 = len('## Review subject\n\nkind: commit \xb7 ref: big1234\n\n## Repository context (reference)\n\nxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
    26	!!!!!!!!!!!!!!!!!!!!!!!!!! stopping after 1 failures !!!!!!!!!!!!!!!!!!!!!!!!!!!
    27	============================== 1 failed in 0.34s ===============================
    28	
    29	[Command succeeded with exit code 0]
</message>

