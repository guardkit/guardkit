# AutoBuild Execution Protocol (Medium)

> Balanced protocol for local backends. Restores anti-stub examples and stack patterns
> while keeping the slim structure for lower-impact sections.
> Size target: ~10-11KB (between slim ~5.5KB and full ~19KB).

---

## Pre-Phase 3: Infrastructure

If task frontmatter has `requires_infrastructure`, start declared services:
- PostgreSQL: `docker run -d --name guardkit-test-pg -e POSTGRES_PASSWORD=test -p 5433:5432 postgres:16-alpine`
- Redis: `docker run -d --name guardkit-test-redis -p 6380:6379 redis:7-alpine`
- MongoDB: `docker run -d --name guardkit-test-mongo -p 27018:27017 mongo:7`

Cleanup after tests: `docker rm -f guardkit-test-pg guardkit-test-redis guardkit-test-mongo 2>/dev/null || true`

Skip if `requires_infrastructure` is absent.

---

## Phase 3: Implementation

1. Read the implementation plan from `.claude/task-plans/{task_id}-implementation-plan.md`
2. Implement all files listed in the plan
3. Follow detected stack conventions (type hints, strict mode, async patterns)
4. Create production-quality code with error handling
5. Do NOT create stubs (see Anti-Stub Rules below)

File count constraints: minimal/standard = max 2 files, comprehensive = unlimited.

Modes: Standard = implement + test together. TDD = RED → GREEN → REFACTOR.

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

1. Only import what the plan specifies — do not add unplanned dependencies
2. Use standard library first — prefer `pathlib`, `json`, `re` over third-party alternatives
3. Pin to specific versions if adding a dependency
4. Check existing dependencies before adding new ones

---

## Phases 4 and 5: Owned by the AutoBuildOrchestrator

Phases 4 (test execution) and 5 (code review) are executed by the AutoBuildOrchestrator after your Phase 3 completes. You do not need to invoke `test-orchestrator` or `code-reviewer` directly. Focus your turn on Phases 1, 2, 3, and (optionally) Phase 4.5 (test-fix loop) for your own feedback.

---

## Phase 4.5: Fix Loop

Run tests inline (e.g., `pytest`, `npm test`, `dotnet test`) for your own feedback — do not invoke `test-orchestrator`. Max 3 attempts. Fix implementation, NOT tests. Do NOT skip/comment out/ignore tests.

Loop: run tests inline → analyze failure → fix code → re-run tests inline → check results.
If all pass: finish your turn. If attempt > 3: report BLOCKED with diagnostics.

The AutoBuildOrchestrator runs `test-orchestrator` after your turn; Coach validates independently.

### Blocked State Diagnostics

If max attempts exhausted, report:
- Remaining compilation errors (file:line format)
- Remaining test failures with assertion details
- Coverage metrics
- What was attempted and why it didn't work

---

## Phase 5.5: Plan Audit

Compare actual vs planned: files, dependencies, LOC variance.
- LOW: <10% variance, no extra files
- MEDIUM: 10-30% variance, 1-2 extra files
- HIGH: >30% variance, 3+ extra files

Skip if no plan exists.

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

## Player Report

Write JSON to: `{worktree_path}/.guardkit/autobuild/{task_id}/player_turn_{turn}.json`

CRITICAL: `completion_promises` MUST have one entry per acceptance criterion. Empty array causes stalling.

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
  "files_modified": [],
  "files_created": [],
  "tests_written": [],
  "tests_run": true,
  "tests_passed": true,
  "test_output_summary": "Brief summary",
  "implementation_notes": "What and why",
  "concerns": [],
  "requirements_addressed": [],
  "requirements_remaining": []
}
```

Status values: "complete", "incomplete", "uncertain". Self-check: one entry per AC, no empty evidence.

**CRITICAL: `files_modified` / `files_created` scoping** — list only paths YOU wrote or edited this session. Do NOT sweep `git status --porcelain`; in parallel-wave runs the worktree may contain sibling tasks' in-flight writes, and the honesty auditor will flag claims for paths you did not author as fabrications. A fabrication flag aborts evidence gathering (`partial_honesty_abort`). Exclude orchestrator-managed paths (`.guardkit/`, `.claude/task-plans/`).

---

## Output Markers

Use these exact formats (parsed programmatically):
- `Phase N: Description` (e.g., `Phase 3: Implementation`)
- `✓ Phase N complete`
- `N tests passed` / `N tests failed`
- `Coverage: N.N%`
- `Quality gates: PASSED` / `Quality gates: FAILED`
- `Architectural Score: N/100`
