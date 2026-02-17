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

After Phase 4 (test execution) completes — whether tests pass or fail — tear down all containers you started:

```bash
docker rm -f guardkit-test-pg guardkit-test-redis guardkit-test-mongo 2>/dev/null || true
```

### When requires_infrastructure is absent

Skip this section entirely. Proceed to Phase 3 as normal.

---

## Phase 3: Implementation

You are implementing a task. Follow these instructions exactly.

### Implementation Requirements

1. **Read the implementation plan** from `.claude/task-plans/{task_id}-implementation-plan.md`
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

## Phase 4: Testing

After implementation, verify your code works.

### Mandatory Compilation Check

You MUST verify code compiles/builds BEFORE running tests:

**Python**:
```bash
python -m py_compile <file.py>
```

**TypeScript**:
```bash
npx tsc --noEmit
```

**.NET**:
```bash
dotnet build --no-restore
```

If compilation fails, fix errors BEFORE proceeding to test execution.

### Test Execution

Run the full test suite:

**Python**:
```bash
pytest tests/ -v --cov=src --cov-report=term --cov-report=json
```

**TypeScript/JavaScript**:
```bash
npm test -- --coverage
```

**.NET**:
```bash
dotnet test --collect:"XPlat Code Coverage" --logger:"json"
```

### Quality Gate Thresholds

| Gate | Threshold | Action if Failed |
|---|---|---|
| Compilation | 100% (zero errors) | Fix immediately |
| Tests Pass | 100% (all must pass) | Enter fix loop |
| Line Coverage | >= 80% | Add more tests |
| Branch Coverage | >= 75% | Add more tests |

ALL gates must pass. There is ZERO TOLERANCE for test failures.

### Test Result Reporting

After running tests, report results in this exact format (parsed programmatically):

```
N tests passed
N tests failed
Coverage: N.N%
```

Where N is replaced with actual numbers.

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

```
WHILE (compilation_errors > 0 OR test_failures > 0) AND attempt <= 3:
    1. Analyze failure details
    2. Fix the root cause in implementation code
    3. Re-run compilation check
    4. Re-run test suite
    5. Check results

    IF all tests pass AND coverage >= thresholds:
        BREAK → Proceed to Phase 5
    ELSE:
        attempt += 1

IF attempt > 3:
    REPORT as BLOCKED with diagnostics
```

### Blocked State Diagnostics

If max attempts exhausted, report:
- Remaining compilation errors (file:line format)
- Remaining test failures with assertion details
- Coverage metrics
- What was attempted and why it didn't work

---

## Phase 5: Code Review

Review implementation for quality and correctness.

### Review Checklist

1. **Code Quality**: Clean, readable, well-structured
2. **Error Handling**: Proper exception handling, no silent failures
3. **Test Quality**: Meaningful assertions, edge cases covered
4. **Architecture**: Follows SOLID/DRY/YAGNI principles
5. **Stack Conventions**: Follows language-specific best practices

### SOLID Principles Check

Verify the implementation follows SOLID principles:

- **S - Single Responsibility**: Each module/class has one reason to change. A module that handles both data validation AND database writes violates SRP.
- **O - Open/Closed**: Code is open for extension, closed for modification. Use strategy patterns, plugins, or configuration instead of modifying existing code.
- **L - Liskov Substitution**: If the code uses inheritance, subtypes must be substitutable for base types without breaking behavior.
- **I - Interface Segregation**: Interfaces (protocols/ABCs) should be small and focused. No client should depend on methods it doesn't use.
- **D - Dependency Inversion**: High-level modules should depend on abstractions, not concretions. Use dependency injection.

### DRY Check

Verify no logic duplication:
- No copy-pasted code blocks with minor variations
- Shared logic extracted into helper functions or base classes
- Constants defined once (not magic numbers repeated)
- Configuration centralized (not scattered across files)

### YAGNI Check

Verify no over-engineering:
- No features beyond what acceptance criteria require
- No "just in case" abstractions or configuration points
- No premature optimization
- No generic frameworks where specific implementations suffice

### Quality Assessment

After review, output:
```
Quality gates: PASSED
```
or
```
Quality gates: FAILED
```

---

## Phase 5.5: Plan Audit

Compare actual implementation against the approved plan.

### Audit Process

1. **Load the saved plan** from `.claude/task-plans/{task_id}-implementation-plan.md`
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
`.guardkit/autobuild/{task_id}/player_turn_{turn}.json`

### PLAYER_REPORT_SCHEMA

Your report MUST be valid JSON with ALL of these fields:

```json
{
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
  "requirements_remaining": ["requirements", "still", "pending"],
  "completion_promises": [
    {
      "criterion_id": "AC-001",
      "criterion_text": "Full text of acceptance criterion",
      "status": "complete",
      "evidence": "What you did to satisfy this criterion",
      "test_file": "tests/test_feature.py",
      "implementation_files": ["src/feature.py"]
    }
  ]
}
```

### Field Requirements

| Field | Type | Required | Description |
|---|---|---|---|
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
| completion_promises | array[object] | YES | Per-criterion verification |

### Completion Promise Schema

Each completion_promise maps to one acceptance criterion:

| Field | Type | Description |
|---|---|---|
| criterion_id | string | e.g., "AC-001" |
| criterion_text | string | Full criterion text |
| status | string | "complete" or "incomplete" |
| evidence | string | What you did |
| test_file | string or null | Validating test file |
| implementation_files | array[string] | Files for this criterion |

CRITICAL: The Coach verifies each completion_promise independently. Be specific in evidence fields.

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

This protocol defines the complete execution loop for the AutoBuild Player agent:
1. **Phase 3**: Implement according to plan
2. **Phase 4**: Run tests, verify quality gates
3. **Phase 4.5**: Fix loop if tests fail (max 3 attempts)
4. **Phase 5**: Code review
5. **Report**: Write PLAYER_REPORT_SCHEMA JSON to `.guardkit/autobuild/`
