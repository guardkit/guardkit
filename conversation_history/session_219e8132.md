## Summarized at 2026-07-04T19:57:27.554610+00:00

Human: You are executing the implementation phase (Phases 3-5) for TASK-QAV-002.

## Context

- Task ID: TASK-QAV-002
- Mode: tdd
- Documentation Level: minimal
- Working directory: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC

## Turn Context

- Current turn: 1
- Max turns: 5
- Turns remaining: 4
- Approaching limit: False

## Task Requirements

# Task: Bundle fields + stub_scan seam wiring

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

1. **Read the implementation plan** from `.claude/task-plans/TASK-QAV-002-implementation-plan.md`
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

1. **Load the saved plan** from `.claude/task-plans/TASK-QAV-002-implementation-plan.md`
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
`/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.guardkit/autobuild/TASK-QAV-002/player_turn_1.json`

<!-- Fallback (relative path): .guardkit/autobuild/TASK-QAV-002/player_turn_1.json -->

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
   - /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.claude/task-plans/TASK-QAV-002-implementation-plan.md
   - /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.claude/task-plans/TASK-QAV-002-implementation-plan.json
   - /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/docs/state/TASK-QAV-002/implementation_plan.md
   - /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/docs/state/TASK-QAV-002/implementation_plan.json

AI: [{'name': 'glob', 'args': {'pattern': '**/TASK-QAV-002*', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC'}, 'id': 'fc_MxZjw1PeUNpOfHmMhgM5dKNVS0R76BRf', 'type': 'tool_call'}, {'name': 'glob', 'args': {'pattern': '**/tasks/TASK-QAV-002*', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC'}, 'id': 'fc_8u0FVPiPKlvyvsuvAiT9yww1bJAC41O1', 'type': 'tool_call'}]
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.claude/task-plans/TASK-QAV-002-implementation-plan.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/backlog/qav-behavioural-gates/TASK-QAV-002-bundle-fields-and-stub-scan-seam.md', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/design_approved/TASK-QAV-002-bundle-fields-and-stub-scan-seam.md']
Tool: []
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/backlog/qav-behavioural-gates/TASK-QAV-002-bundle-fields-and-stub-scan-seam.md'}, 'id': 'fc_bt5q2bzs2G4ndybBeJ3ZMMKcKpwgVeQp', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/.claude/task-plans/TASK-QAV-002-implementation-plan.md'}, 'id': 'fc_0MVGMCrPgX0W7ATYaxdXy3zS6WMTamE1', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tasks/design_approved/TASK-QAV-002-bundle-fields-and-stub-scan-seam.md'}, 'id': 'fc_OacfLDDxKHqBZDthMRLsYaahAz03eLrI', 'type': 'tool_call'}]
Tool:      1	---
     2	id: TASK-QAV-002
     3	title: CoachEvidenceBundle sibling fields (stub_scan, coverage, behavioural_oracle) + stub_scan seam wiring
     4	task_type: feature
     5	parent_review: TASK-REV-QAVG
     6	feature_id: FEAT-10AC
     7	wave: 2
     8	implementation_mode: task-work
     9	complexity: 5
    10	dependencies:
    11	  - TASK-QAV-001
    12	priority: high
    13	consumer_context:
    14	  - task: TASK-QAV-001
    15	    consumes: analyze_stub_scan
    16	    framework: "guardkit CoachValidator lazy-import seam"
    17	    driver: "guardkitfactory.wiring"
    18	    format_note: "dict via .to_dict() with status + findings keys; status never maps to pass; None = probe did not run"
    19	---
    20	
    21	# Task: Bundle fields + stub_scan seam wiring
    22	
    23	## Description
    24	
    25	Extend `CoachEvidenceBundle`
    26	(`guardkit/orchestrator/quality_gates/coach_evidence.py`) with THREE new
    27	sibling fields directly after the existing Wave-1 wiring fields
    28	(`wiring`/`mocked_seam`/`spec_gap`, ~L295-297):
    29	
    30	```python
    31	stub_scan: Optional[Dict[str, Any]] = None           # L2 anti-stub (this task)
    32	coverage: Optional[Dict[str, Any]] = None            # L3 (populated by TASK-QAV-003)
    33	behavioural_oracle: Optional[Dict[str, Any]] = None  # L4 (populated by TASK-QAV-004)
    34	```
    35	
    36	Wire `stub_scan` population into `CoachValidator`'s complete-path
    37	`gather_evidence` return (beside the existing `_run_wiring_analysis()` bridge,
    38	`coach_validator.py` ~L584-611) via the same **lazy import** seam
    39	(`try/except ImportError → field stays None`). Render all three fields in
    40	`_render_evidence_bundle_section` with the established findings-truncation
    41	(first 20 + count), and append an advisory guard sentence for stub findings to
    42	the absence-of-failure guards block. `coverage` and `behavioural_oracle` are
    43	declared + rendered here but populated by Waves 3-4.
    44	
    45	## Acceptance Criteria
    46	
    47	- [ ] **AC-1:** the three fields exist as `Optional[Dict[str, Any]] = None`
    48	  siblings; `to_dict()` carries them with no special-casing; docstring slots
    49	  follow the existing wiring-field pattern.
    50	- [ ] **AC-2 (absent-vs-empty):** for `stub_scan`, `findings:[]` with positive
    51	  status is asserted distinct from the field being `None`; the partial/honesty
    52	  early returns leave all three fields `None`.
    53	- [ ] **AC-3 (seam):** with guardkitfactory importable, `stub_scan` is
    54	  populated from `analyze_stub_scan` on the complete path for FEATURE /
    55	  REFACTOR / INTEGRATION tasks; with the import absent, all three fields stay
    56	  `None` and `gather_evidence` does not crash.
    57	- [ ] **AC-4 (render):** >20 stub findings render as first 20 + "... and N
    58	  more"; advisory guard sentence appears in the guards block; `coverage` /
    59	  `behavioural_oracle` render when present (fixture dicts) without code change.
    60	- [ ] **AC-5 (cross-repo seam test):** a seam test (mirroring
    61	  `tests/orchestrator/test_wiring_ctor_arity_seam.py`) asserts the REAL
    62	  installed `guardkitfactory.wiring` exposes `analyze_stub_scan` with the
    63	  documented result keys — a factory version skew fails in CI, not on a live
    64	  run.
    65	- [ ] **AC-6 (behavioural check, dogfood):** an integration test drives
    66	  `gather_evidence` end-to-end over a fixture worktree containing a stubbed
    67	  authored file and asserts the rendered Coach prompt contains the stub
    68	  finding — not a mock of the factory seam (the real dependency, per A2).
    69	- [ ] **AC-7 (advisory only):** stub findings NEVER change the Coach decision
    70	  deterministically in this task — no verdict override is added here.
    71	- [ ] **AC-8:** existing guardkit suites remain green; all modified files pass
    72	  project-configured lint/format checks with zero errors.
    73	
    74	## Seam Tests
    75	
    76	The following seam test validates the integration contract with TASK-QAV-001.
    77	
    78	```python
    79	"""Seam test: verify analyze_stub_scan contract from TASK-QAV-001."""
    80	import pytest
    81	
    82	pytest.importorskip("guardkitfactory.wiring")
    83	
    84	
    85	@pytest.mark.seam
    86	@pytest.mark.integration_contract("analyze_stub_scan")
    87	def test_analyze_stub_scan_contract():
    88	    """Verify analyze_stub_scan exists and returns the documented dict shape.
    89	
    90	    Contract: dict via .to_dict() with status + findings keys; None = probe
    91	    did not run. Producer: TASK-QAV-001.
    92	    """
    93	    from guardkitfactory.wiring import analyze_stub_scan  # real install, no mock
    94	    import inspect
    95	
    96	    params = inspect.signature(analyze_stub_scan).parameters
    97	    assert "authored_files" in params
    98	    assert "worktree_path" in params
    99	    assert "task_type" in params
   100	```
Tool:      1	# Implementation Plan: TASK-QAV-002
     2	
     3	## Task
     4	CoachEvidenceBundle sibling fields (stub_scan, coverage, behavioural_oracle) + stub_scan seam wiring
     5	
     6	## Plan Status
     7	**Auto-generated stub** - Pre-loop was skipped for this feature task.
     8	Generated: 2026-07-04T20:53:38.707484
     9	
    10	## Implementation
    11	Follow acceptance criteria in task file.
    12	
    13	## Notes
    14	This plan was auto-generated because the task was created via /feature-plan
    15	with pre-loop disabled (enable_pre_loop=False).
    16	The detailed specifications are in the task markdown file.
Tool:      1	---
     2	complexity: 5
     3	consumer_context:
     4	- consumes: analyze_stub_scan
     5	  driver: guardkitfactory.wiring
     6	  format_note: dict via .to_dict() with status + findings keys; status never maps
     7	    to pass; None = probe did not run
     8	  framework: guardkit CoachValidator lazy-import seam
     9	  task: TASK-QAV-001
    10	dependencies:
    11	- TASK-QAV-001
    12	feature_id: FEAT-10AC
    13	id: TASK-QAV-002
    14	implementation_mode: task-work
    15	parent_review: TASK-REV-QAVG
    16	priority: high
    17	status: design_approved
    18	task_type: feature
    19	title: CoachEvidenceBundle sibling fields (stub_scan, coverage, behavioural_oracle)
    20	  + stub_scan seam wiring
    21	wave: 2
    22	---
    23	
    24	# Task: Bundle fields + stub_scan seam wiring
    25	
    26	## Description
    27	
    28	Extend `CoachEvidenceBundle`
    29	(`guardkit/orchestrator/quality_gates/coach_evidence.py`) with THREE new
    30	sibling fields directly after the existing Wave-1 wiring fields
    31	(`wiring`/`mocked_seam`/`spec_gap`, ~L295-297):
    32	
    33	```python
    34	stub_scan: Optional[Dict[str, Any]] = None           # L2 anti-stub (this task)
    35	coverage: Optional[Dict[str, Any]] = None            # L3 (populated by TASK-QAV-003)
    36	behavioural_oracle: Optional[Dict[str, Any]] = None  # L4 (populated by TASK-QAV-004)
    37	```
    38	
    39	Wire `stub_scan` population into `CoachValidator`'s complete-path
    40	`gather_evidence` return (beside the existing `_run_wiring_analysis()` bridge,
    41	`coach_validator.py` ~L584-611) via the same **lazy import** seam
    42	(`try/except ImportError → field stays None`). Render all three fields in
    43	`_render_evidence_bundle_section` with the established findings-truncation
    44	(first 20 + count), and append an advisory guard sentence for stub findings to
    45	the absence-of-failure guards block. `coverage` and `behavioural_oracle` are
    46	declared + rendered here but populated by Waves 3-4.
    47	
    48	## Acceptance Criteria
    49	
    50	- [ ] **AC-1:** the three fields exist as `Optional[Dict[str, Any]] = None`
    51	  siblings; `to_dict()` carries them with no special-casing; docstring slots
    52	  follow the existing wiring-field pattern.
    53	- [ ] **AC-2 (absent-vs-empty):** for `stub_scan`, `findings:[]` with positive
    54	  status is asserted distinct from the field being `None`; the partial/honesty
    55	  early returns leave all three fields `None`.
    56	- [ ] **AC-3 (seam):** with guardkitfactory importable, `stub_scan` is
    57	  populated from `analyze_stub_scan` on the complete path for FEATURE /
    58	  REFACTOR / INTEGRATION tasks; with the import absent, all three fields stay
    59	  `None` and `gather_evidence` does not crash.
    60	- [ ] **AC-4 (render):** >20 stub findings render as first 20 + "... and N
    61	  more"; advisory guard sentence appears in the guards block; `coverage` /
    62	  `behavioural_oracle` render when present (fixture dicts) without code change.
    63	- [ ] **AC-5 (cross-repo seam test):** a seam test (mirroring
    64	  `tests/orchestrator/test_wiring_ctor_arity_seam.py`) asserts the REAL
    65	  installed `guardkitfactory.wiring` exposes `analyze_stub_scan` with the
    66	  documented result keys — a factory version skew fails in CI, not on a live
    67	  run.
    68	- [ ] **AC-6 (behavioural check, dogfood):** an integration test drives
    69	  `gather_evidence` end-to-end over a fixture worktree containing a stubbed
    70	  authored file and asserts the rendered Coach prompt contains the stub
    71	  finding — not a mock of the factory seam (the real dependency, per A2).
    72	- [ ] **AC-7 (advisory only):** stub findings NEVER change the Coach decision
    73	  deterministically in this task — no verdict override is added here.
    74	- [ ] **AC-8:** existing guardkit suites remain green; all modified files pass
    75	  project-configured lint/format checks with zero errors.
    76	
    77	## Seam Tests
    78	
    79	The following seam test validates the integration contract with TASK-QAV-001.
    80	
    81	```python
    82	"""Seam test: verify analyze_stub_scan contract from TASK-QAV-001."""
    83	import pytest
    84	
    85	pytest.importorskip("guardkitfactory.wiring")
    86	
    87	
    88	@pytest.mark.seam
    89	@pytest.mark.integration_contract("analyze_stub_scan")
    90	def test_analyze_stub_scan_contract():
    91	    """Verify analyze_stub_scan exists and returns the documented dict shape.
    92	
    93	    Contract: dict via .to_dict() with status + findings keys; None = probe
    94	    did not run. Producer: TASK-QAV-001.
    95	    """
    96	    from guardkitfactory.wiring import analyze_stub_scan  # real install, no mock
    97	    import inspect
    98	
    99	    params = inspect.signature(analyze_stub_scan).parameters
   100	    assert "authored_files" in params
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_evidence.py'}, 'id': 'fc_KGKXJwxTVAjB3uKIV5XM9QPnmtBT9xHo', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py'}, 'id': 'fc_bQVZu4NR1KmBOtis0YQCtTCd3r5GPEg0', 'type': 'tool_call'}]
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
    76	class RuntimeParityResult:
    77	    """Outcome of the per-task Coach runtime-parity check (TASK-AB-COACHRUNPARITY01, arm b).
    78	
    79	    The per-task Coach runs the feature's declared smoke command — the
    80	    deliverable's REAL runtime entry point — before approving, so a "passes
    81	    pytest but does not run" deliverable is caught pre-approval rather than
    82	    only by the post-wave smoke gate. Honours
    83	    ``absence-of-failure-is-not-success.md``: a ran-and-FAILED result blocks
    84	    approval; an ABSENT result (``ran=False`` — no command, parallel wave, or
    85	    runner error) never blocks and never counts as a pass.
    86	
    87	    Attributes
    88	    ----------
    89	    ran : bool
    90	        ``True`` only when the smoke command actually executed and produced an
    91	        exit code. ``False`` for every skip/absent case (``skipped_reason`` set).
    92	    passed : bool
    93	        ``True`` when ``ran`` and the observed exit code equals ``expected_exit``.
    94	        Always ``False`` when ``ran`` is ``False`` (absent != pass).
    95	    command : str
    96	        The smoke command that was (or would have been) run.
    97	    exit_code : Optional[int]
    98	        Observed exit code; ``None`` when the command did not run (or timed out).
    99	    expected_exit : int
   100	        The exit code that counts as success (the feature's configured value).
Tool:      1	"""
     2	Coach validator for lightweight task-work result validation.
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
    45	from types import SimpleNamespace
    46	from typing import Any, Dict, List, Literal, Optional, Tuple
    47	
    48	from guardkit.lib.pytest_argv import isolated_basetemp
    49	from guardkit.orchestrator.coach_verification import (
    50	    CoachVerifier,
    51	    HonestyVerification,
    52	    _resolve_venv_python,
    53	)
    54	from guardkit.orchestrator import evidence_repos as evidence_repos_lib
    55	from guardkit.orchestrator.evidence_repos import EvidenceRepo, EvidenceTestResult
    56	from guardkit.orchestrator.quality_gates.stack_test_execution import (
    57	    StackTestProfile,
    58	    classify_absent_for_stack,
    59	    detect_stack_profile,
    60	)
    61	from guardkit.orchestrator.quality_gates.coach_evidence import (
    62	    CoachEvidenceBundle,
    63	    IndependentTestClassification,
    64	    RuntimeParityResult,
    65	)
    66	from guardkit.orchestrator.docker_fixtures import (
    67	    get_container_name,
    68	    get_env_exports,
    69	    get_start_commands,
    70	    is_known_service,
    71	)
    72	from guardkit.orchestrator.paths import TaskArtifactPaths
    73	from guardkit.orchestrator.phase_specialists import (
    74	    PHASE_DESCRIPTIONS,
    75	    detect_stack_template,
    76	    render_missing_phase_list,
    77	)
    78	from guardkit.orchestrator.schemas import STATUS_ALIASES
    79	from guardkit.models.task_types import TaskType, QualityGateProfile, get_profile, TASK_TYPE_ALIASES
    80	
    81	# TASK-HMIG-006.3: Coach's independent SDK invocation dispatches through
    82	# the HarnessAdapter substrate seam established by TASK-HMIG-006 (Player
    83	# path) and TASK-HMIG-006.2 (cross-repo helper migration). Importing at
    84	# module top matches the Player path convention in
    85	# ``agent_invoker.py:71-77`` and makes ``select_harness`` a stable patch
    86	# target for tests under ``coach_validator.select_harness``.
    87	from guardkit.orchestrator.exceptions import AgentInvocationError
    88	from guardkit.orchestrator.harness import (
    89	    AssistantMessageEvent,
    90	    ResultMessageEvent,
    91	    ToolResultEvent,
    92	    select_harness,
    93	)
    94	from guardkit.orchestrator.harness.selector import DEFAULT_HARNESS
    95	from guardkit.orchestrator.sdk_utils import check_assistant_message_error
    96	
    97	# Coach architecture-context integration (TASK-SC-009) was retired in the
    98	# fleet-memory cutover (FEAT-MEM-09): build_coach_context was never invoked and
    99	# was built on the now-removed graphiti planning stack.
   100	
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_evidence.py', 'offset': 100, 'limit': 250}, 'id': 'fc_kWyB67fo25KvQAOY8uMUH1OUUUmnNAIO', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'offset': 550, 'limit': 200}, 'id': 'fc_vhV7z4XtmjPRMI358mrsuz4obgRmM0O0', 'type': 'tool_call'}]
Tool:    101	    timed_out : bool
   102	        ``True`` when the command exceeded its timeout before completing.
   103	    stderr_tail : str
   104	        Last lines of captured stderr (for Player-facing feedback). Empty when
   105	        ``ran`` is ``False``.
   106	    skipped_reason : Optional[str]
   107	        Why the check did not run (``"no_smoke_command"``, ``"parallel_wave"``,
   108	        ``"runner_error: ..."``). ``None`` when the check ran.
   109	    output_tail : Optional[str]
   110	        Combined stdout+stderr tail (stdout first, each stream bounded to its
   111	        last 2000 chars). Additive field (2026-07-04 code review): pytest
   112	        writes its ``FAILED <nodeid>`` short-summary lines to STDOUT, so a
   113	        stderr-only tail hides the failing-test names from
   114	        ``AgentInvoker._apply_runtime_parity_guard``'s evidence extraction —
   115	        the same stdout+stderr join ``feature_orchestrator._build_smoke_feedback``
   116	        already performs post-wave. ``None`` on older records / when the run
   117	        produced no output; consumers fall back to ``stderr_tail``.
   118	    """
   119	
   120	    ran: bool
   121	    passed: bool
   122	    command: str
   123	    exit_code: Optional[int] = None
   124	    expected_exit: int = 0
   125	    timed_out: bool = False
   126	    stderr_tail: str = ""
   127	    skipped_reason: Optional[str] = None
   128	    output_tail: Optional[str] = None
   129	
   130	
   131	@dataclass
   132	class IndependentTestClassification:
   133	    """Substrate-vs-code classification of a ran-and-failed independent test run.
   134	
   135	    TASK-ABFIX-012. Computed by ``CoachValidator.gather_evidence`` ONLY when the
   136	    Coach's own independent test run RAN and FAILED (``tests_passed is False`` AND
   137	    ``signal_absent is False``) — never for a passing run and never for an ABSENT
   138	    signal (an absent signal must never manufacture a code verdict;
   139	    ``absence-of-failure-is-not-success.md``). ``None`` on the bundle otherwise.
   140	
   141	    A ``failure_class == "code"`` result for a TESTING task deterministically
   142	    blocks the turn via
   143	    ``AgentInvoker._apply_independent_test_code_failure_guard`` — the deterministic
   144	    backstop the LLM Coach lacked when it false-approved FEAT-FMDR-004 (a 5/9-red
   145	    TESTING task whose real code bugs were reasoned away as "substrate, absent").
   146	
   147	    Attributes
   148	    ----------
   149	    failure_class : str
   150	        One of ``"code"`` / ``"infrastructure"`` / ``"parallel_contention"`` /
   151	        ``"collection_error"`` / ``"sdk_api_error"`` (see
   152	        ``CoachValidator._classify_test_failure``). Only ``"code"`` blocks; a
   153	        substrate gap classifies ``"infrastructure"`` and genuine cross-task
   154	        contention classifies ``"parallel_contention"`` — neither reaches the
   155	        blocking guard, preserving the parallel-contention amnesty for non-code
   156	        failures.
   157	    confidence : str
   158	        ``"high"`` / ``"ambiguous"`` / ``"n/a"``. The guard blocks on any
   159	        confidence (a single-wave failure with no recognised exception token is
   160	        still ``("code", "n/a")`` and IS a real failure for a TESTING task).
   161	    raw_output_excerpt : str
   162	        Last 500 chars of the independent-test raw output, for the Player-facing
   163	        feedback. Bounded so ``coach_turn_N.json`` stays small.
   164	    """
   165	
   166	    failure_class: str
   167	    confidence: str
   168	    raw_output_excerpt: str = ""
   169	
   170	
   171	@dataclass
   172	class CoachEvidenceBundle:
   173	    """Structured evidence gathered by CoachValidator for the LLM Coach.
   174	
   175	    Each field maps to an intermediate value the legacy ``validate()`` method
   176	    consumed internally. Under TASK-HMIG-008R the LLM Coach reads this bundle
   177	    (rendered as JSON into the Coach prompt) plus the honesty result and makes
   178	    the final approve/feedback decision.
   179	
   180	    Attributes
   181	    ----------
   182	    honesty
   183	        ``HonestyVerification`` from ``CoachVerifier``. Carries
   184	        ``resolved_paths`` (Layer 1 / TASK-FIX-1B4A) and ``should_fix_count``
   185	        (Layer 2 demotion / TASK-FIX-1B4B). Populated on every non-pre-evidence
   186	        gather path. The Coach reads this field unconditionally.
   187	    gathering_status
   188	        Pipeline status; see :data:`GatheringStatus` for the meaning of each
   189	        value. Used by the Coach to decide whether ``None`` evidence fields
   190	        mean ABSENT SIGNAL (status != "complete") or NO SIGNAL REPORTED
   191	        (status == "complete").
   192	    gathering_error
   193	        Optional human-readable description of what went wrong when
   194	        ``gathering_status == "partial_exception"``. ``None`` on every other
   195	        status. Surfaced verbatim in the synthetic feedback rationale when the
   196	        primary ``_invoke_coach`` path catches an exception around evidence
   197	        gathering.
   198	    quality_gates
   199	        ``QualityGateStatus`` aggregate (tests / coverage / arch_review /
   200	        plan_audit). ``None`` when gathering aborted before the gates ran or
   201	        when the task type opts out of all gates.
   202	    coverage_details
   203	        Raw coverage dict slice from ``task_work_results['test_results']``
   204	        (line_coverage, branch_coverage, files_below_threshold). ``None`` when
   205	        coverage was not reported.
   206	    plan_audit
   207	        Plan-audit findings dict from ``task_work_results['plan_audit']``.
   208	        ``None`` when the producer wrote no plan_audit block (e.g.
   209	        ``--implement-only`` without a saved plan).
   210	    bdd
   211	        Raw ``task_work_results['bdd_results']`` dict (scenarios_attempted,
   212	        scenarios_failed, scenarios_passed, scenarios_pending, failures,
   213	        pending, feature_files). ``None`` when no BDD oracle ran. The Coach
   214	        applies the Pattern-2 absence-of-failure guard against
   215	        ``bdd['scenarios_attempted']``.
   216	    arch_review
   217	        Architectural review dict slice (``{"score": int, ...}``). ``None``
   218	        when no Phase 2.5B output was produced.
   219	    tests
   220	        Aggregate test result dict (tests_passed / tests_run /
   221	        line_coverage_met / branch_coverage_met / requires_infrastructure).
   222	        ``None`` when no test_results block was produced. The Coach applies
   223	        the absence-of-failure guard against ``tests['tests_run']``.
   224	    independent_tests
   225	        ``IndependentTestResult`` from Coach's own pytest pass. ``None`` when
   226	        gathering aborted before independent tests or when the task type's
   227	        profile opts out of independent verification.
   228	    independent_test_classification
   229	        ``IndependentTestClassification`` (TASK-ABFIX-012) — substrate-vs-code
   230	        verdict for a RAN-AND-FAILED independent test run. Populated only when
   231	        ``independent_tests`` ran and failed (``tests_passed`` False AND
   232	        ``signal_absent`` False); ``None`` for passing / absent / skipped runs.
   233	        A ``("code", ...)`` result for a TESTING task deterministically blocks
   234	        the turn via ``AgentInvoker._apply_independent_test_code_failure_guard``.
   235	    requirements
   236	        ``RequirementsValidation`` from ``validate_requirements``. ``None``
   237	        when gathering aborted before requirements validation.
   238	    severity_recommendations
   239	        Structured hints derived from ``_honesty_issues_from`` demotion logic
   240	        (Layer 2). Each hint is ``{"recommendation": str, "rule": str}``. The
   241	        Coach reads these to know when to demote ``file_existence``
   242	        discrepancies from ``must_fix`` to ``should_fix``.
   243	    task_type
   244	        Resolved task type string (e.g. ``"feature"``, ``"refactor"``,
   245	        ``"scaffolding"``). ``None`` when task type could not be resolved
   246	        (``partial_exception`` with invalid_task_type cause).
   247	    profile_name
   248	        Quality-gate profile name string. ``None`` on the same paths as
   249	        ``task_type``.
   250	    advisory_issues
   251	        Non-blocking issues that ride along with the final decision regardless
   252	        of approve/feedback outcome. Currently sourced from:
   253	
   254	        * Agent-invocations advisory (TASK-REV-F6E1 F3c) — process observation,
   255	          ``severity == "warning"``.
   256	        * Layer-2-demoted honesty ``should_fix`` issues — content observation,
   257	          ``severity == "should_fix"``.
   258	
   259	        Pre-populated so the LLM Coach can read them without re-computing the
   260	        Layer-2 demotion.
   261	    wiring
   262	        UNWIRED_PATH analysis result (dict) from ``guardkitfactory.wiring``.
   263	        Contains ``status``, ``dialect``, ``language``, ``targets_scanned``,
   264	        ``symbols_examined``, ``findings``, ``degraded_files``. ``None`` when
   265	        the task type gates out (SCAFFOLDING/DOCUMENTATION), there are no
   266	        authored source targets, or the factory is unavailable.
   267	    mocked_seam
   268	        MOCKED_SEAM analysis result (dict). Contains ``status``, ``ran``,
   269	        ``dialect``, ``findings``, ``external_mocks_ignored``. ``None`` when
   270	        the task type gates out, there are no authored acceptance files, or
   271	        the factory is unavailable.
   272	    spec_gap
   273	        SPEC_GAP analysis result (dict). Contains ``status``,
   274	        ``ground_truth_count``, ``executed_count``, ``findings``,
   275	        ``whole_file_deselection``. ``None`` when the task type gates out,
   276	        the factory BDD plugin is unavailable, or Wave-3 wiring is not yet
   277	        implemented.
   278	    """
   279	
   280	    honesty: "HonestyVerification"
   281	    gathering_status: GatheringStatus = "complete"
   282	    gathering_error: Optional[str] = None
   283	
   284	    quality_gates: Optional["QualityGateStatus"] = None
   285	    coverage_details: Optional[Dict[str, Any]] = None
   286	    plan_audit: Optional[Dict[str, Any]] = None
   287	    bdd: Optional[Dict[str, Any]] = None
   288	    arch_review: Optional[Dict[str, Any]] = None
   289	    tests: Optional[Dict[str, Any]] = None
   290	
   291	    # Wave-1 wiring evidence fields (TASK-QAWE-002).
   292	    # Populated by CoachValidator.gather_evidence at the complete-path return.
   293	    # Left None for SCAFFOLDING/DOCUMENTATION tasks, zero-target turns,
   294	    # or when guardkitfactory.wiring is unavailable (ImportError).
   295	    wiring: Optional[Dict[str, Any]] = None         # UNWIRED_PATH analysis
   296	    mocked_seam: Optional[Dict[str, Any]] = None    # MOCKED_SEAM analysis
   297	    spec_gap: Optional[Dict[str, Any]] = None       # SPEC_GAP (Wave-3)
   298	
   299	    independent_tests: Optional["IndependentTestResult"] = None
   300	    # TASK-ABFIX-012: substrate-vs-code classification of a ran-and-failed
   301	    # independent test run. Populated by gather_evidence ONLY when independent
   302	    # tests RAN and FAILED (tests_passed False AND signal_absent False). A
   303	    # ("code", ...) result for a TESTING task deterministically blocks via
   304	    # AgentInvoker._apply_independent_test_code_failure_guard. ``None`` for
   305	    # passing / absent / skipped runs — an absent signal never manufactures a
   306	    # code verdict (absence-of-failure-is-not-success). Serialised automatically
   307	    # by ``to_dict``/``asdict`` (it is a dataclass), so the verdict reaches
   308	    # coach_turn_N.json with no to_dict change (the ABFIX-010 serialization
   309	    # invariant).
   310	    independent_test_classification: Optional["IndependentTestClassification"] = None
   311	    requirements: Optional[Any] = None  # RequirementsValidation; avoid circular import
   312	
   313	    # TASK-AB-COACHRUNPARITY01 (arm b): per-task runtime-parity check. The
   314	    # Coach runs the deliverable's declared runtime entry point (the feature
   315	    # smoke command) before approving, on single-task waves only. ``None`` when
   316	    # no check was attempted (no smoke command threaded / older callers).
   317	    # ``ran=False`` records an attempted-but-skipped check (parallel wave /
   318	    # runner error). A ``ran=True, passed=False`` result deterministically
   319	    # blocks the turn via ``AgentInvoker._apply_runtime_parity_guard``.
   320	    runtime_parity: Optional["RuntimeParityResult"] = None
   321	
   322	    # TASK-AB-XREPOEV01 (AC-002): Coach's independent test runs in declared
   323	    # sibling repos (``evidence_repos``). Each entry is an
   324	    # ``EvidenceTestResult.to_dict()``. Empty when no sibling repos are
   325	    # declared. These results reach ``coach_turn_N.json`` (this bundle is
   326	    # serialised verbatim) and the Coach prompt, and a ran-and-failed suite
   327	    # deterministically blocks the turn in the orchestrator.
   328	    evidence_repo_tests: List[Dict[str, Any]] = field(default_factory=list)
   329	
   330	    severity_recommendations: List[Dict[str, str]] = field(default_factory=list)
   331	    advisory_issues: List[Dict[str, Any]] = field(default_factory=list)
   332	
   333	    task_type: Optional[str] = None
   334	    profile_name: Optional[str] = None
   335	
   336	    def to_dict(self) -> Dict[str, Any]:
   337	        """Serialise the bundle to a JSON-compatible dict.
   338	
   339	        Nested ``HonestyVerification`` / ``QualityGateStatus`` /
   340	        ``IndependentTestResult`` / ``RequirementsValidation`` instances are
   341	        also dataclasses, so ``dataclasses.asdict`` walks the entire tree.
   342	        ``ResolvedPath`` / ``Discrepancy`` inside ``HonestyVerification`` are
   343	        also dataclasses — the whole bundle is safe for ``json.dumps``.
   344	        """
   345	        from dataclasses import asdict
   346	
   347	        return asdict(self)
Tool:    551	                "ABSENT SIGNAL (per-task glue not configured).",
   552	                task_id,
   553	                stack_profile,
   554	            )
   555	            return None
   556	
   557	        # scenarios=[] — pytest-bdd re-discovers from features/ internally
   558	        # (Contract C4). Pre-discovering Scenario objects for every stack is
   559	        # the remit of TASK-HMIG-BDDWIRE, not this contract fix.
   560	        result = plugin.run([], task_id, worktree_path)
   561	
   562	        if result is None:
   563	            logger.debug(
   564	                "BDD factory bridge: plugin returned None for stack %s; "
   565	                "falling back to Player-reported bdd_results.",
   566	                stack_profile,
   567	            )
   568	            return None
   569	
   570	        # Map BDDRunResult → bundle.bdd shape.
   571	        return map_bdd_run_result(result)
   572	
   573	    except Exception as exc:  # noqa: BLE001 — BDD failures must not break evidence gathering
   574	        logger.warning(
   575	            "BDD factory bridge raised %s for stack %s; "
   576	            "falling back to Player-reported bdd_results.",
   577	            exc.__class__.__name__,
   578	            stack_profile,
   579	        )
   580	        return None
   581	
   582	
   583	# ============================================================================
   584	# Wiring Factory Bridge — wire guardkitfactory.wiring into the Coach evidence
   585	# ============================================================================
   586	#
   587	# TASK-QAWE-002 (Wave-1): Lazy import of the UNWIRED_PATH / MOCKED_SEAM
   588	# analyzer. The import is guarded so that ``pip install guardkit-py`` without
   589	# the ``[autobuild]`` extra still works — Coach leaves all three wiring
   590	# fields as ``None`` when the factory is unavailable.
   591	#
   592	# The seam returns a dict (never the dataclass) so coach_evidence.py keeps
   593	# zero guardkitfactory import.
   594	
   595	try:
   596	    from guardkitfactory.wiring import (  # type: ignore[attr-defined,no-redef]
   597	        analyze_wiring,
   598	    )
   599	
   600	    _WIRING_FACTORY_AVAILABLE = True
   601	except ImportError:
   602	    analyze_wiring = None  # type: ignore[misc,assignment]
   603	    _WIRING_FACTORY_AVAILABLE = False
   604	
   605	def _is_wiring_factory_available() -> bool:
   606	    """Return True when the guardkitfactory wiring analyzer is importable.
   607	
   608	    A plain module-level check (the import happens once at module load);
   609	    kept as a function so tests can patch availability.
   610	    """
   611	    return _WIRING_FACTORY_AVAILABLE and analyze_wiring is not None
   612	
   613	
   614	def _reset_wiring_factory_cache() -> None:
   615	    """Kept for call-site compatibility; availability is no longer cached."""
   616	    return None
   617	
   618	
   619	def _compute_authored_set(
   620	    task_work_results: Dict[str, Any],
   621	) -> List[str]:
   622	    """Compute the set of source files authored by the Player this turn.
   623	
   624	    Uses the presence-based fallback from the task-work results:
   625	    ``files_authored`` when present, else ``files_created ∪ files_modified``.
   626	
   627	    This is NOT the git-enriched ``files_modified`` (which can be
   628	    peer-contaminated in parallel-wave execution).
   629	
   630	    Parameters
   631	    ----------
   632	    task_work_results : Dict[str, Any]
   633	        The task-work results dict from ``read_quality_gate_results``.
   634	
   635	    Returns
   636	    -------
   637	    List[str]
   638	        List of authored file paths (relative to worktree root).
   639	    """
   640	    if "files_authored" in task_work_results and isinstance(
   641	        task_work_results["files_authored"], list
   642	    ):
   643	        # Presence-based: an explicit empty list is authoritative (the
   644	        # Player authored nothing), NOT a trigger for the fallback union.
   645	        return [str(f) for f in task_work_results["files_authored"]]
   646	
   647	    # Fallback: files_created ∪ files_modified
   648	    created = task_work_results.get("files_created") or []
   649	    modified = task_work_results.get("files_modified") or []
   650	    authored: List[str] = []
   651	    seen: set = set()
   652	    for f in list(created) + list(modified):
   653	        fs = str(f)
   654	        if fs not in seen:
   655	            seen.add(fs)
   656	            authored.append(fs)
   657	    return authored
   658	
   659	
   660	def _compute_spec_gap(
   661	    bdd_dict: Optional[Dict[str, Any]],
   662	    worktree_path: Path,
   663	    task_id: str,
   664	) -> Dict[str, Any]:
   665	    """Compute the SPEC_GAP evidence for the given BDD run result.
   666	
   667	    Detects a ``@task:<TASK-ID>``-tagged Gherkin scenario that is ground truth
   668	    (declared in a ``features/**/*.feature`` file) but has no executed binding.
   669	
   670	    AC-011: Per-scenario gap — a named tagged scenario absent from the executed
   671	    set produces one advisory ``spec_gap`` finding.
   672	
   673	    AC-012: When ``scenarios_attempted`` is **absent** from the BDD dict,
   674	    ``whole_file_deselection`` is ``False`` and the hard gate does NOT fire.
   675	    Absent = UNKNOWN, never coerced to 0.
   676	
   677	    AC-013: When ``scenarios_attempted`` is present and zero while
   678	    ``ground_truth_count > 0``, ``whole_file_deselection`` is ``True``.
   679	
   680	    AC-022: When ``bdd.discover(stack)`` returns ``None`` (unsupported stack),
   681	    ``status`` is ``"unsupported_stack"`` and the guard does not fire.
   682	
   683	    Parameters
   684	    ----------
   685	    bdd_dict : Optional[Dict[str, Any]]
   686	        The ``bundle.bdd``-shaped dict (from factory or player-reported).
   687	        ``None`` means no BDD evidence at all.
   688	    worktree_path : Path
   689	        Root of the worktree (for scanning feature files).
   690	    task_id : str
   691	        The task identifier (e.g. ``"TASK-QAWE-004"``) used to match
   692	        ``@task:<TASK-ID>`` tags in feature files.
   693	
   694	    Returns
   695	    -------
   696	    Dict[str, Any]
   697	        A spec_gap dict with keys: ``status``, ``ground_truth_count``,
   698	        ``executed_count``, ``pending_count``, ``findings``,
   699	        ``whole_file_deselection``, ``bdd_plugin_name``,
   700	        ``executed_evidence``.
   701	    """
   702	    # --- Ground truth: scan feature files for @task:<TASK-ID> tags ---
   703	    ground_truth_count = 0
   704	    # (feature_file, scenario_name) tuples — tuples, not joined strings, so
   705	    # scenario names containing ":" never mis-split downstream.
   706	    ground_truth_scenarios: List[tuple] = []
   707	
   708	    features_dir = worktree_path / "features"
   709	    if features_dir.is_dir():
   710	        for feature_file in features_dir.rglob("*.feature"):
   711	            try:
   712	                content = feature_file.read_text(encoding="utf-8")
   713	            except OSError:
   714	                continue
   715	
   716	            # Track tag block context: tags accumulate until a Scenario line.
   717	            # After a Scenario line, reset so the next tag block is captured.
   718	            tag_block: List[str] = []
   719	
   720	            for line in content.splitlines():
   721	                stripped = line.strip()
   722	
   723	                # Tag lines start with @
   724	                if stripped.startswith("@"):
   725	                    tag_block.append(stripped)
   726	                    continue
   727	
   728	                # Scenario line ends the tag block
   729	                if re.match(r"^\s*(Scenario:|Scenario Outline:)", line):
   730	                    # Ground truth is THIS task's scenarios ONLY: an exact
   731	                    # @task:<TASK-ID> token match. Counting other tasks'
   732	                    # @task: tags would inflate ground_truth_count and
   733	                    # false-fire the whole-file hard gate for a task that
   734	                    # legitimately owns zero scenarios (parallel-wave
   735	                    # features). Tag lines may carry multiple tags
   736	                    # ("@task:X @smoke"), so match TOKENS, not whole lines.
   737	                    task_tag = f"@task:{task_id}"
   738	                    tag_tokens = {
   739	                        token
   740	                        for tag_line in tag_block
   741	                        for token in tag_line.split()
   742	                    }
   743	                    if task_tag in tag_tokens:
   744	                        match = re.search(
   745	                            r"(Scenario Outline:|Scenario:)\s+(.+)", line
   746	                        )
   747	                        if match:
   748	                            scenario_name = match.group(2).strip()
   749	                            ground_truth_count += 1
   750	                            ground_truth_scenarios.append((
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 300, 'offset': 750}, 'id': 'fc_9KmZVXQZzeH12KipCwbXtF38jrH4iM5G', 'type': 'tool_call'}, {'name': 'grep', 'args': {'pattern': 'def gather_evidence', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'output_mode': 'content'}, 'id': 'fc_8DTuDdPcnO148FcGCm9b9DDLOM5GaqBW', 'type': 'tool_call'}]
Tool:    751	                                str(feature_file.relative_to(worktree_path)),
   752	                                scenario_name,
   753	                            ))
   754	                    tag_block = []
   755	                    continue
   756	
   757	                # Any other non-empty line ends the tag block
   758	                if stripped and not stripped.startswith("#"):
   759	                    tag_block = []
   760	
   761	    # --- Executed evidence: consume from BDDRunResult ---
   762	    executed_count = 0
   763	    pending_count = 0
   764	    whole_file_deselection = False
   765	    status = "complete"
   766	    executed_evidence: str = "counts_only"
   767	    bdd_plugin_name: Optional[str] = None
   768	
   769	    if bdd_dict is not None and isinstance(bdd_dict, dict):
   770	        # AC-012: Check if scenarios_attempted key is PRESENT (not absent)
   771	        # Use "in" check, NOT .get(..., 0) — absent = UNKNOWN
   772	        if "scenarios_attempted" in bdd_dict:
   773	            executed_count = bdd_dict.get("scenarios_attempted", 0) or 0
   774	            pending_count = bdd_dict.get("scenarios_pending", 0) or 0
   775	
   776	            # AC-013: whole-file deselection when ground_truth > 0 and
   777	            # scenarios_attempted is present and zero
   778	            if ground_truth_count > 0 and executed_count == 0:
   779	                whole_file_deselection = True
   780	
   781	        # Determine executed_evidence level
   782	        if "executed_scenarios" in bdd_dict:
   783	            executed_evidence = "full"
   784	        elif "scenarios_attempted" in bdd_dict:
   785	            executed_evidence = "counts_only"
   786	        else:
   787	            executed_evidence = "partial"
   788	
   789	        bdd_plugin_name = bdd_dict.get("bdd_plugin_name")
   790	    else:
   791	        # No BDD evidence at all — unsupported_stack status
   792	        status = "unsupported_stack"
   793	        executed_evidence = "counts_only"
   794	
   795	    # --- Per-scenario findings (AC-011) ---
   796	    # When executed_evidence is "full", we can compare per-scenario
   797	    findings: List[Dict[str, Any]] = []
   798	    if executed_evidence == "full" and ground_truth_scenarios:
   799	        executed_names = set(
   800	            s.get("name", "")
   801	            for s in bdd_dict.get("executed_scenarios", [])  # type: ignore[union-attr]
   802	            if isinstance(s, dict)
   803	        )
   804	        for gt_file, scenario_name in ground_truth_scenarios:
   805	            # Substring match: name-matching carries FP risk, hence advisory.
   806	            if not any(scenario_name in en for en in executed_names):
   807	                findings.append({
   808	                    "feature_file": gt_file,
   809	                    "symbol": scenario_name,
   810	                    "severity": "warning",
   811	                    "pattern": "SPEC_GAP",
   812	                    "why": f"Tagged scenario '{scenario_name}' declared in ground truth but not found in executed set",
   813	                })
   814	
   815	    return {
   816	        "status": status,
   817	        "ground_truth_count": ground_truth_count,
   818	        "executed_count": executed_count,
   819	        "pending_count": pending_count,
   820	        "findings": findings,
   821	        "whole_file_deselection": whole_file_deselection,
   822	        "bdd_plugin_name": bdd_plugin_name,
   823	        "executed_evidence": executed_evidence,
   824	    }
   825	
   826	
   827	def _run_wiring_analysis(
   828	    worktree_path: Path,
   829	    authored_files: List[str],
   830	    task_type: str,
   831	    stack_template: Optional[str],
   832	    bdd_dict: Optional[Dict[str, Any]] = None,
   833	    task_id: str = "",
   834	) -> Optional[Dict[str, Any]]:
   835	    """Run the wiring analysis for the authored files.
   836	
   837	    Returns a dict with ``wiring``, ``mocked_seam``, and ``spec_gap`` keys
   838	    (some may be ``None``). Returns ``None`` when the task type gates out
   839	    (SCAFFOLDING/DOCUMENTATION) or there are no authored source targets.
   840	
   841	    For the MOCKED_SEAM probe specifically:
   842	    - When authored files exist but no acceptance files are present,
   843	      returns a dict with ``mocked_seam`` set to ``ran: false`` + ``skip_reason``.
   844	    - When acceptance files are present, the factory runs the scan.
   845	
   846	    Parameters
   847	    ----------
   848	    worktree_path : Path
   849	        Root of the worktree.
   850	    authored_files : List[str]
   851	        Source files authored this turn.
   852	    task_type : str
   853	        Resolved task type (e.g. ``"feature"``, ``"scaffolding"``).
   854	    stack_template : Optional[str]
   855	        Detected stack template (e.g. ``"python"``, ``"fastapi-python"``).
   856	    bdd_dict : Optional[Dict[str, Any]]
   857	        The ``bundle.bdd``-shaped dict for SPEC_GAP computation.
   858	    task_id : str
   859	        Task identifier for SPEC_GAP tag matching.
   860	
   861	    Returns
   862	    -------
   863	    Optional[Dict[str, Any]]
   864	        Dict with ``wiring``, ``mocked_seam``, ``spec_gap`` keys, or ``None``
   865	        when the probe legitimately did not run.
   866	    """
   867	    # Positive task-type gate (scope §4): only FEATURE / REFACTOR /
   868	    # INTEGRATION are analyzed. Everything else (scaffolding, documentation,
   869	    # testing, infrastructure, …) legitimately produces un-wired stubs →
   870	    # all three fields None. Case-insensitive: frontmatter uses lowercase.
   871	    if (task_type or "").upper() not in ("FEATURE", "REFACTOR", "INTEGRATION"):
   872	        logger.debug(
   873	            "wiring analysis: task_type=%s gates out; "
   874	            "all three fields left as None.",
   875	            task_type,
   876	        )
   877	        return None
   878	
   879	    # Zero-authored-targets gate → None (probe legitimately did not run).
   880	    if not authored_files:
   881	        logger.debug(
   882	            "wiring analysis: no authored source targets; "
   883	            "all three fields left as None.",
   884	        )
   885	        return None
   886	
   887	    # Factory unavailable → all fields None (graceful import absence,
   888	    # AC-017). Checked before any other work so factory-absent behaviour
   889	    # is uniform regardless of authored-file composition.
   890	    if not _is_wiring_factory_available() or analyze_wiring is None:
   891	        logger.debug(
   892	            "wiring analysis: guardkitfactory.wiring not available; "
   893	            "all three fields left as None.",
   894	        )
   895	        return None
   896	
   897	    # Resolve the stack hint. analyze_wiring reads ``stack.language``
   898	    # (scope §5.5: StackProfile | None) — a bare string would be silently
   899	    # dropped, so wrap it in a namespace object.
   900	    stack_language = (
   901	        _STACK_PROFILE_MAP.get(stack_template) if stack_template else None
   902	    )
   903	    stack_obj = (
   904	        SimpleNamespace(language=stack_language) if stack_language else None
   905	    )
   906	
   907	    try:
   908	        result = analyze_wiring(
   909	            authored_files=authored_files,
   910	            worktree_path=worktree_path,
   911	            task_type=task_type,
   912	            stack=stack_obj,
   913	        )
   914	        # analyze_wiring returns None (probe didn't run), or the §5.1
   915	        # wiring shape FLAT at top level with the MOCKED_SEAM result
   916	        # nested under "mocked_seam" (acceptance-file selection, skip
   917	        # statuses, and the UNWIRED/MOCKED probe independence all live
   918	        # in the factory — guardkit does not re-implement them).
   919	        if result is None:
   920	            return None
   921	        if not isinstance(result, dict):
   922	            logger.warning(
   923	                "wiring analysis returned unexpected type %s; "
   924	                "all three fields left as None.",
   925	                type(result).__name__,
   926	            )
   927	            return None
   928	        # Normalize into the three-field envelope gather_evidence consumes.
   929	        # pop() keeps bundle.wiring free of the nested mocked_seam copy.
   930	        mocked_seam = result.pop("mocked_seam", None)
   931	        if isinstance(mocked_seam, dict) and "external_mocks_ignored" not in mocked_seam:
   932	            # TASK-QAWE-003 AC-006: the field is always present downstream.
   933	            mocked_seam["external_mocks_ignored"] = []
   934	        # Wave-3 (TASK-QAWE-004): compute spec_gap from BDDRunResult.
   935	        spec_gap_dict = _compute_spec_gap(
   936	            bdd_dict=bdd_dict,
   937	            worktree_path=worktree_path,
   938	            task_id=task_id,
   939	        )
   940	        return {
   941	            "wiring": result,
   942	            "mocked_seam": mocked_seam,
   943	            "spec_gap": spec_gap_dict,
   944	        }
   945	    except Exception as exc:  # noqa: BLE001 — analyzer errors must not break gathering
   946	        logger.warning(
   947	            "wiring analysis raised %s; all three fields left as None.",
   948	            exc.__class__.__name__,
   949	        )
   950	        return None
   951	
   952	
   953	# TASK-FIX-A7B4: Markers that satisfy a `## Seam Tests` block in a task
   954	# description. Filename-based detection (the soft gate at
   955	# ``_check_seam_test_recommendation``) tolerates "integration" too, but the
   956	# blocking gate requires explicit marker decoration so a plain integration test
   957	# can't silently satisfy a contract obligation. Match the established marker
   958	# precedent: `seam`, `contract`, `boundary`.
   959	_SEAM_PYTEST_MARKERS = ("seam", "contract", "boundary")
   960	
   961	# Header pattern: any markdown header level (`#` to `######`) whose title is
   962	# exactly "Seam Tests" (case-insensitive, trailing whitespace allowed). The
   963	# closing `$` plus `re.MULTILINE` matches the header line in isolation so we
   964	# don't false-trigger on prose like "## Seam Tests are useful because…".
   965	_SEAM_TESTS_HEADER_RE = re.compile(
   966	    r"^\s*#{1,6}\s+seam\s+tests\s*$",
   967	    re.IGNORECASE | re.MULTILINE,
   968	)
   969	
   970	
   971	def _extract_seam_tests_section(description: Optional[str]) -> Optional[str]:
   972	    """Extract the body of a ``## Seam Tests`` markdown section.
   973	
   974	    Returns the section body (everything between the ``## Seam Tests`` header
   975	    and the next sibling-or-higher header, or EOF) when the section exists
   976	    AND has non-whitespace content. Returns ``None`` for any of:
   977	
   978	    * ``description`` is empty / None
   979	    * No ``Seam Tests`` header is present
   980	    * The header exists but the body is whitespace-only (empty stub block)
   981	
   982	    The "non-empty body" rule is what TASK-FIX-A7B4 AC-001 calls "precise"
   983	    detection: a developer who wants to acknowledge "no seam tests for this
   984	    task" can leave the section empty (or omit it) without tripping the gate.
   985	    """
   986	    if not description:
   987	        return None
   988	    match = _SEAM_TESTS_HEADER_RE.search(description)
   989	    if not match:
   990	        return None
   991	    # Find the level of the matched header so we know what closes the section.
   992	    header_line = match.group(0)
   993	    header_level = len(header_line.lstrip().split(" ", 1)[0])  # count of '#'
   994	
   995	    # Body starts after the header line.
   996	    body_start = match.end()
   997	    rest = description[body_start:]
   998	    # The section closes at the next header of equal-or-higher level.
   999	    closing_re = re.compile(
  1000	        rf"^\s*#{{1,{header_level}}}\s+\S",
  1001	        re.MULTILINE,
  1002	    )
  1003	    close_match = closing_re.search(rest)
  1004	    body = rest[: close_match.start()] if close_match else rest
  1005	    if not body.strip():
  1006	        return None
  1007	    return body
  1008	
  1009	
  1010	# Stopwords for keyword extraction in fuzzy text matching
  1011	STOPWORDS = {
  1012	    "the", "and", "is", "or", "a", "an", "for", "with", "to", "in", "of",
  1013	    "from", "by", "on", "at", "that", "this", "are", "be", "do", "have",
  1014	    "has", "as", "if", "can", "will", "would", "could", "should", "may",
  1015	    "must", "was", "were", "been", "but", "not", "no", "all", "some",
  1016	    "any", "more", "most", "only", "than", "then", "there", "their",
  1017	    "who", "which", "when", "where", "how",
  1018	}
  1019	
  1020	# ============================================================================
  1021	# Data Models
  1022	# ============================================================================
  1023	
  1024	
  1025	@dataclass
  1026	class QualityGateStatus:
  1027	    """
  1028	    Status of individual quality gates from task-work execution.
  1029	
  1030	    Attributes
  1031	    ----------
  1032	    tests_passed : bool
  1033	        Whether all tests passed in Phase 4.5
  1034	    coverage_met : bool
  1035	        Whether coverage threshold was met
  1036	    arch_review_passed : bool
  1037	        Whether architectural review passed (score >= 60)
  1038	    plan_audit_passed : bool
  1039	        Whether plan audit had zero violations
  1040	    all_gates_passed : bool
  1041	        True only if ALL gates passed (computed)
  1042	    tests_required : bool
  1043	        Whether tests were required by task type profile
  1044	    coverage_required : bool
  1045	        Whether coverage was required by task type profile
  1046	    arch_review_required : bool
  1047	        Whether architectural review was required by task type profile
  1048	    plan_audit_required : bool
  1049	        Whether plan audit was required by task type profile
  1050	    """
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py:
  2863:     def gather_evidence(
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'offset': 2863, 'limit': 200}, 'id': 'fc_EZhQsLzrhjGe9rARYLV41Vg49H3zYZL9', 'type': 'tool_call'}, {'name': 'grep', 'args': {'pattern': 'def _render_evidence_bundle_section', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'output_mode': 'content'}, 'id': 'fc_iS5edhY23iwwW6GXayCN8mliEQNRiIO9', 'type': 'tool_call'}]
Tool:   2864	        self,
  2865	        task_id: str,
  2866	        turn: int,
  2867	        task: Dict[str, Any],
  2868	        skip_arch_review: bool = False,
  2869	        context: Optional[str] = None,
  2870	    ) -> CoachEvidenceBundle:
  2871	        """Gather structured evidence for the LLM Coach (TASK-HMIG-008R Part A).
  2872	
  2873	        Runs the same deterministic gathering pipeline the legacy
  2874	        ``validate()`` method uses internally, but packages the results into a
  2875	        :class:`CoachEvidenceBundle` instead of applying decision logic. The
  2876	        LLM Coach reads this bundle (rendered as JSON into the Coach prompt by
  2877	        ``_build_coach_prompt``) plus the honesty result and makes the final
  2878	        approve/feedback decision per the Block adversarial-cooperation paper.
  2879	
  2880	        The pipeline aborts early under three conditions, leaving downstream
  2881	        fields as ``None`` and setting ``bundle.gathering_status`` so the
  2882	        Coach's absence-of-failure guards know to treat the ``None`` fields
  2883	        as ABSENT SIGNAL:
  2884	
  2885	        * Pre-evidence error (invalid task type, missing task_work_results,
  2886	          or an unexpected exception in a gathering helper) →
  2887	          ``"partial_exception"`` with a human-readable cause in
  2888	          ``bundle.gathering_error``.
  2889	        * Honesty verification produced ``must_fix`` discrepancies →
  2890	          ``"partial_honesty_abort"``. Gates and independent tests are not
  2891	          run because the legacy decision tree would have short-circuited
  2892	          here too — the LLM Coach reaches the same conclusion by reading
  2893	          ``bundle.honesty.discrepancies``.
  2894	        * Quality gates failed → ``"partial_gate_abort"``. Independent
  2895	          tests / requirements validation are not run. The LLM Coach
  2896	          reaches a feedback decision by reading ``bundle.quality_gates``.
  2897	
  2898	        Per the Phase 2.5 architectural review and §3 "Exception handling
  2899	        for gather_evidence" in the implementation plan, this method MUST
  2900	        NOT raise to its caller. Wrapping inner helper exceptions in a
  2901	        ``partial_exception`` bundle prevents an exception fallback to
  2902	        ``validate()`` from re-activating the primary decision path that
  2903	        falsifier #1 ("CoachValidator.validate() for the decision is GONE")
  2904	        requires to be gone. ``GUARDKIT_COACH_LEGACY=1`` remains the sole
  2905	        operator-controlled mechanism for re-activating ``validate()``.
  2906	
  2907	        Parameters
  2908	        ----------
  2909	        task_id : str
  2910	            Task identifier (e.g., ``"TASK-001"``). Used to read
  2911	            ``task_work_results.json`` from the standard autobuild path and
  2912	            to wire state-bridge identity resolution into the honesty
  2913	            verifier (TASK-FIX-1B4A Layer 1).
  2914	        turn : int
  2915	            Current turn number (1-based). Passed to
  2916	            ``validate_requirements`` and ``run_independent_tests``.
  2917	        task : Dict[str, Any]
  2918	            Task data dict. Must contain ``acceptance_criteria`` and may
  2919	            contain ``task_type``, ``requires_infrastructure``,
  2920	            ``_docker_available``, ``consumer_context``, ``description``.
  2921	        skip_arch_review : bool, optional
  2922	            If ``True``, the architectural-review gate is skipped regardless
  2923	            of the profile setting. Used for ``--implement-only`` mode where
  2924	            Phase 2.5B did not run. Default: ``False``.
  2925	        context : Optional[str], optional
  2926	            Optional memory / coach context string. Not currently consumed
  2927	            by gather_evidence itself; threaded through for symmetry with
  2928	            ``validate()``'s signature so the legacy shim (when AC-003 is
  2929	            completed in a follow-up) can pass it forward.
  2930	
  2931	        Returns
  2932	        -------
  2933	        CoachEvidenceBundle
  2934	            Populated evidence bundle. Always returned; never raises.
  2935	        """
  2936	        default_honest = HonestyVerification(verified=True)
  2937	
  2938	        # ------------------------------------------------------------------
  2939	        # Pre-evidence: resolve task type. Mirrors validate() lines 821-838.
  2940	        # ------------------------------------------------------------------
  2941	        try:
  2942	            task_type = self._resolve_task_type(task)
  2943	        except ValueError as exc:
  2944	            logger.error(
  2945	                "gather_evidence: failed to resolve task type: %s", exc
  2946	            )
  2947	            return CoachEvidenceBundle(
  2948	                honesty=default_honest,
  2949	                gathering_status="partial_exception",
  2950	                gathering_error=f"invalid_task_type: {exc}",
  2951	            )
  2952	
  2953	        try:
  2954	            profile = get_profile(task_type)
  2955	        except Exception as exc:  # noqa: BLE001 — defensive; get_profile is total
  2956	            logger.error(
  2957	                "gather_evidence: failed to load profile for %s: %s",
  2958	                task_type, exc,
  2959	            )
  2960	            return CoachEvidenceBundle(
  2961	                honesty=default_honest,
  2962	                gathering_status="partial_exception",
  2963	                gathering_error=f"missing_profile: {exc}",
  2964	                task_type=task_type.value,
  2965	            )
  2966	
  2967	        profile_name = getattr(profile, "name", None) or task_type.value
  2968	
  2969	        # OPERATOR_HANDOFF: no evidence to gather. The legacy validate() returns
  2970	        # decision="deferred" here; gather_evidence reports a clean status so
  2971	        # the LLM Coach prompt sees an empty bundle with the task_type marker.
  2972	        # The Part B / Part C wiring is responsible for short-circuiting the
  2973	        # Coach invocation for operator-handoff tasks at the autobuild layer
  2974	        # (the same place the legacy validate() returned deferred).
  2975	        if task_type == TaskType.OPERATOR_HANDOFF:
  2976	            logger.info(
  2977	                "gather_evidence: skipping evidence collection for "
  2978	                "operator_handoff task %s (runtime verification deferred to "
  2979	                "operator)", task_id,
  2980	            )
  2981	            return CoachEvidenceBundle(
  2982	                honesty=default_honest,
  2983	                gathering_status="complete",
  2984	                task_type=task_type.value,
  2985	                profile_name=profile_name,
  2986	            )
  2987	
  2988	        # ------------------------------------------------------------------
  2989	        # Pre-evidence: read task_work_results. Mirrors validate() lines 875-895.
  2990	        # ------------------------------------------------------------------
  2991	        task_work_results = self.read_quality_gate_results(task_id)
  2992	        if "error" in task_work_results:
  2993	            logger.warning(
  2994	                "gather_evidence: task-work results missing for %s: %s",
  2995	                task_id, task_work_results.get("error", "unknown"),
  2996	            )
  2997	            return CoachEvidenceBundle(
  2998	                honesty=default_honest,
  2999	                gathering_status="partial_exception",
  3000	                gathering_error=(
  3001	                    f"missing_results: {task_work_results.get('error', 'unknown')}"
  3002	                ),
  3003	                task_type=task_type.value,
  3004	                profile_name=profile_name,
  3005	            )
  3006	
  3007	        # ------------------------------------------------------------------
  3008	        # 1. Honesty verification. Mirrors validate() lines 918-952.
  3009	        # ------------------------------------------------------------------
  3010	        try:
  3011	            honesty = self._verify_honesty(task_work_results)
  3012	        except Exception as exc:  # noqa: BLE001
  3013	            logger.error(
  3014	                "gather_evidence: _verify_honesty raised unexpectedly: %s", exc,
  3015	            )
  3016	            return CoachEvidenceBundle(
  3017	                honesty=default_honest,
  3018	                gathering_status="partial_exception",
  3019	                gathering_error=f"honesty_exception: {exc}",
  3020	                task_type=task_type.value,
  3021	                profile_name=profile_name,
  3022	            )
  3023	
  3024	        honesty_issues = self._honesty_issues_from(honesty)
  3025	        honesty_must_fix = [
  3026	            i for i in honesty_issues if i["severity"] == "must_fix"
  3027	        ]
  3028	        honesty_should_fix = [
  3029	            i for i in honesty_issues if i["severity"] == "should_fix"
  3030	        ]
  3031	
  3032	        # Layer-2 demotion hint for the LLM Coach. Mirrors the structural
  3033	        # condition inside _honesty_issues_from (lines 5456-5460): a single
  3034	        # critical file_existence discrepancy that was Layer-1-resolved (via
  3035	        # state_bridge.canonical_path_for) is demoted from must_fix to
  3036	        # should_fix. Surface that hint structurally so the LLM Coach can
  3037	        # apply absence-of-failure guard #4 without re-deriving the demotion.
  3038	        severity_recommendations: List[Dict[str, str]] = []
  3039	        critical_discrepancies = [
  3040	            d for d in honesty.discrepancies if d.severity == "critical"
  3041	        ]
  3042	        non_audit_critical = [
  3043	            d for d in critical_discrepancies
  3044	            if d.claim_type != "claim_audit"
  3045	        ]
  3046	        if (
  3047	            len(non_audit_critical) == 1
  3048	            and non_audit_critical[0].claim_type == "file_existence"
  3049	        ):
  3050	            severity_recommendations.append({
  3051	                "recommendation": (
  3052	                    "A single file_existence discrepancy was suppressed by "
  3053	                    "Layer-1 identity resolution (state_bridge "
  3054	                    "canonical_path_for). Treat as should_fix, not must_fix. "
  3055	                    "Continue AC evaluation."
  3056	                ),
  3057	                "rule": (
  3058	                    "path-string-mismatch-is-not-dishonesty "
  3059	                    "(Layer 2 demotion)"
  3060	                ),
  3061	            })
  3062	
  3063	        # Advisory issues: agent-invocations advisory (F3c) + Layer-2 honesty
Tool: No matches found
AI: [{'name': 'grep', 'args': {'pattern': '_render_evidence_bundle', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'output_mode': 'content'}, 'id': 'fc_X26eyvXjpm2c3KCIPtISobEAYK51JY4l', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'offset': 3060, 'limit': 300}, 'id': 'fc_7m3OhwxoTjLK0oxjd3W8oy6FvBV0ERz8', 'type': 'tool_call'}]
Tool: No matches found
Tool:   3061	            })
  3062	
  3063	        # Advisory issues: agent-invocations advisory (F3c) + Layer-2 honesty
  3064	        # should_fix issues. Both ride along with the final decision (approve
  3065	        # or feedback) and are surfaced to the Player so process observations
  3066	        # remain visible. Pre-computed here so the LLM Coach can read them
  3067	        # without re-deriving from raw fields.
  3068	        advisory_issues: List[Dict[str, Any]] = []
  3069	        agent_invocations_advisory = (
  3070	            self._compute_agent_invocations_advisory(task_work_results)
  3071	        )
  3072	        if agent_invocations_advisory is not None:
  3073	            advisory_issues.append(agent_invocations_advisory)
  3074	        # TASK-FIX-SPECVIOL01 AC-002: orchestrator-injected specialist
  3075	        # failures (hang/crash) ride along as attributed advisories so the
  3076	        # substrate failure is never silently dropped — and never read as
  3077	        # a Player honesty issue.
  3078	        advisory_issues.extend(
  3079	            self._compute_specialist_failure_advisories(task_work_results)
  3080	        )
  3081	        advisory_issues.extend(honesty_should_fix)
  3082	
  3083	        # Honesty short-circuit: don't run downstream gathering. Legacy
  3084	        # validate() also short-circuits here.
  3085	        if honesty_must_fix:
  3086	            logger.warning(
  3087	                "gather_evidence: honesty produced %d must_fix issue(s) "
  3088	                "for %s; downstream gathering skipped.",
  3089	                len(honesty_must_fix), task_id,
  3090	            )
  3091	            return CoachEvidenceBundle(
  3092	                honesty=honesty,
  3093	                gathering_status="partial_honesty_abort",
  3094	                severity_recommendations=severity_recommendations,
  3095	                advisory_issues=advisory_issues,
  3096	                task_type=task_type.value,
  3097	                profile_name=profile_name,
  3098	            )
  3099	
  3100	        # ------------------------------------------------------------------
  3101	        # 2. Quality gates. Mirrors validate() lines 1130-1132.
  3102	        # ------------------------------------------------------------------
  3103	        try:
  3104	            gates = self.verify_quality_gates(
  3105	                task_work_results,
  3106	                profile=profile,
  3107	                skip_arch_review=skip_arch_review,
  3108	            )
  3109	        except Exception as exc:  # noqa: BLE001
  3110	            logger.error(
  3111	                "gather_evidence: verify_quality_gates raised: %s", exc,
  3112	            )
  3113	            return CoachEvidenceBundle(
  3114	                honesty=honesty,
  3115	                gathering_status="partial_exception",
  3116	                gathering_error=f"quality_gates_exception: {exc}",
  3117	                severity_recommendations=severity_recommendations,
  3118	                advisory_issues=advisory_issues,
  3119	                task_type=task_type.value,
  3120	                profile_name=profile_name,
  3121	            )
  3122	
  3123	        # Build the evidence dict slices the LLM Coach reads.
  3124	        quality_gates_raw = task_work_results.get("quality_gates")
  3125	        if not isinstance(quality_gates_raw, dict):
  3126	            quality_gates_raw = {}
  3127	
  3128	        coverage_details: Dict[str, Any] = {
  3129	            "coverage_met": quality_gates_raw.get("coverage_met"),
  3130	            "line_coverage": quality_gates_raw.get("line_coverage"),
  3131	            "branch_coverage": quality_gates_raw.get("branch_coverage"),
  3132	            "line_threshold": quality_gates_raw.get("line_threshold"),
  3133	            "branch_threshold": quality_gates_raw.get("branch_threshold"),
  3134	            "coverage_required": gates.coverage_required,
  3135	        }
  3136	
  3137	        tests_dict: Dict[str, Any] = {
  3138	            "tests_passed": gates.tests_passed,
  3139	            "tests_required": gates.tests_required,
  3140	            "tests_run": quality_gates_raw.get("tests_run"),
  3141	            "tests_failed": quality_gates_raw.get("tests_failed"),
  3142	            "all_passed": quality_gates_raw.get("all_passed"),
  3143	            "requires_infrastructure": task.get("requires_infrastructure"),
  3144	        }
  3145	
  3146	        plan_audit_raw = task_work_results.get("plan_audit")
  3147	        plan_audit_dict: Optional[Dict[str, Any]] = (
  3148	            plan_audit_raw if isinstance(plan_audit_raw, dict) else None
  3149	        )
  3150	
  3151	        code_review_raw = task_work_results.get("code_review")
  3152	        arch_review_dict: Optional[Dict[str, Any]] = None
  3153	        if isinstance(code_review_raw, dict):
  3154	            arch_review_dict = {
  3155	                "score": code_review_raw.get("score"),
  3156	                "threshold": getattr(profile, "arch_review_threshold", 60),
  3157	                "passed": gates.arch_review_passed,
  3158	                "required": gates.arch_review_required,
  3159	            }
  3160	            # Surface any sub-scores the producer wrote (solid/dry/yagni).
  3161	            for sub in ("solid_score", "dry_score", "yagni_score"):
  3162	                if sub in code_review_raw:
  3163	                    arch_review_dict[sub] = code_review_raw[sub]
  3164	
  3165	        # ------------------------------------------------------------------
  3166	        # BDD evidence. TASK-BDDW-001: wire factory BDD plugin discovery
  3167	        # into the Coach evidence path.
  3168	        #
  3169	        # Priority:
  3170	        #   1. Factory discovery (guardkitfactory.bdd.discover) — if available
  3171	        #      and stack profile is known, run the BDD plugin and map the
  3172	        #      result into bundle.bdd shape.
  3173	        #   2. Player-reported bdd_results — legacy fallback when the factory
  3174	        #      is unavailable, the stack is unknown, or discovery fails.
  3175	        # ------------------------------------------------------------------
  3176	        _reset_factory_cache()
  3177	        _reset_wiring_factory_cache()
  3178	
  3179	        bdd_raw = task_work_results.get("bdd_results")
  3180	        bdd_dict: Optional[Dict[str, Any]] = None
  3181	
  3182	        if bdd_raw is not None and isinstance(bdd_raw, dict):
  3183	            # Player already produced BDD results — use them as-is.
  3184	            bdd_dict = bdd_raw
  3185	        elif _is_factory_available():
  3186	            # Factory is available but Player didn't produce results.
  3187	            # Attempt independent discovery via the factory plugin.
  3188	            stack_profile = _detect_stack_profile(self.worktree_path)
  3189	            factory_result = _run_factory_bdd(
  3190	                self.worktree_path, stack_profile, task_id
  3191	            )
  3192	            if factory_result is not None:
  3193	                bdd_dict = factory_result
  3194	                logger.info(
  3195	                    "gather_evidence: BDD evidence from factory plugin "
  3196	                    "(stack=%s, scenarios_attempted=%s).",
  3197	                    stack_profile,
  3198	                    factory_result.get("scenarios_attempted"),
  3199	                )
  3200	            else:
  3201	                logger.debug(
  3202	                    "gather_evidence: factory BDD discovery returned None; "
  3203	                    "bdd field left as absent signal.",
  3204	                )
  3205	        else:
  3206	            # Factory unavailable — bdd_dict stays None (absent signal).
  3207	            logger.debug(
  3208	                "gather_evidence: guardkitfactory not available; "
  3209	                "Player-reported bdd_results were empty; "
  3210	                "bdd field left as absent signal.",
  3211	            )
  3212	
  3213	        # Quality-gate-failure short-circuit. Legacy validate() also
  3214	        # short-circuits here via _feedback_from_gates.
  3215	        if not gates.all_gates_passed:
  3216	            logger.info(
  3217	                "gather_evidence: quality gates failed for %s; downstream "
  3218	                "(requirements, independent tests) skipped.", task_id,
  3219	            )
  3220	            return CoachEvidenceBundle(
  3221	                honesty=honesty,
  3222	                gathering_status="partial_gate_abort",
  3223	                quality_gates=gates,
  3224	                coverage_details=coverage_details,
  3225	                plan_audit=plan_audit_dict,
  3226	                bdd=bdd_dict,
  3227	                arch_review=arch_review_dict,
  3228	                tests=tests_dict,
  3229	                severity_recommendations=severity_recommendations,
  3230	                advisory_issues=advisory_issues,
  3231	                task_type=task_type.value,
  3232	                profile_name=profile_name,
  3233	            )
  3234	
  3235	        # ------------------------------------------------------------------
  3236	        # 3. Requirements validation. Mirrors validate() line 1139.
  3237	        # Hoisted ahead of independent-test in the legacy path; preserved
  3238	        # here for the same reason — cheaper, idempotent.
  3239	        # ------------------------------------------------------------------
  3240	        try:
  3241	            requirements = self.validate_requirements(
  3242	                task, task_work_results, turn=turn
  3243	            )
  3244	        except Exception as exc:  # noqa: BLE001
  3245	            logger.error(
  3246	                "gather_evidence: validate_requirements raised: %s", exc,
  3247	            )
  3248	            return CoachEvidenceBundle(
  3249	                honesty=honesty,
  3250	                gathering_status="partial_exception",
  3251	                gathering_error=f"requirements_exception: {exc}",
  3252	                quality_gates=gates,
  3253	                coverage_details=coverage_details,
  3254	                plan_audit=plan_audit_dict,
  3255	                bdd=bdd_dict,
  3256	                arch_review=arch_review_dict,
  3257	                tests=tests_dict,
  3258	                severity_recommendations=severity_recommendations,
  3259	                advisory_issues=advisory_issues,
  3260	                task_type=task_type.value,
  3261	                profile_name=profile_name,
  3262	            )
  3263	
  3264	        # ------------------------------------------------------------------
  3265	        # 4. Independent tests. Mirrors validate() lines 1156-1175.
  3266	        # ------------------------------------------------------------------
  3267	        if not profile.tests_required:
  3268	            test_result: IndependentTestResult = IndependentTestResult(
  3269	                tests_passed=True,
  3270	                test_command="skipped",
  3271	                test_output_summary=(
  3272	                    f"Independent test verification skipped "
  3273	                    f"(tests not required for {task_type.value} tasks)"
  3274	                ),
  3275	                duration_seconds=0.0,
  3276	            )
  3277	            logger.info(
  3278	                "gather_evidence: independent test verification skipped for "
  3279	                "%s (tests not required for %s tasks)",
  3280	                task_id, task_type.value,
  3281	            )
  3282	        else:
  3283	            try:
  3284	                test_result = self.run_independent_tests(
  3285	                    task_work_results=task_work_results,
  3286	                    task=task,
  3287	                    turn=turn,
  3288	                )
  3289	            except Exception as exc:  # noqa: BLE001
  3290	                logger.error(
  3291	                    "gather_evidence: run_independent_tests raised: %s", exc,
  3292	                )
  3293	                return CoachEvidenceBundle(
  3294	                    honesty=honesty,
  3295	                    gathering_status="partial_exception",
  3296	                    gathering_error=f"independent_tests_exception: {exc}",
  3297	                    quality_gates=gates,
  3298	                    coverage_details=coverage_details,
  3299	                    plan_audit=plan_audit_dict,
  3300	                    bdd=bdd_dict,
  3301	                    arch_review=arch_review_dict,
  3302	                    tests=tests_dict,
  3303	                    requirements=requirements,
  3304	                    severity_recommendations=severity_recommendations,
  3305	                    advisory_issues=advisory_issues,
  3306	                    task_type=task_type.value,
  3307	                    profile_name=profile_name,
  3308	                )
  3309	
  3310	        # ------------------------------------------------------------------
  3311	        # 5. Wiring analysis (Wave-1, TASK-QAWE-002).
  3312	        # Populates wiring / mocked_seam / spec_gap at the complete-path
  3313	        # return only. Partial returns (honesty_abort, gate_abort,
  3314	        # exception) leave all three None.
  3315	        # ------------------------------------------------------------------
  3316	        wiring_dict: Optional[Dict[str, Any]] = None
  3317	        mocked_seam_dict: Optional[Dict[str, Any]] = None
  3318	        spec_gap_dict: Optional[Dict[str, Any]] = None
  3319	
  3320	        try:
  3321	            stack_template = detect_stack_template(self.worktree_path)
  3322	            authored = _compute_authored_set(task_work_results)
  3323	            wiring_result = _run_wiring_analysis(
  3324	                worktree_path=self.worktree_path,
  3325	                authored_files=authored,
  3326	                task_type=task_type.value,
  3327	                stack_template=stack_template,
  3328	                bdd_dict=bdd_dict,
  3329	                task_id=task_id,
  3330	            )
  3331	            if wiring_result is not None:
  3332	                wiring_dict = wiring_result.get("wiring")
  3333	                mocked_seam_dict = wiring_result.get("mocked_seam")
  3334	                spec_gap_dict = wiring_result.get("spec_gap")
  3335	                logger.info(
  3336	                    "gather_evidence: wiring analysis complete "
  3337	                    "(wiring_findings=%d, mocked_seam_findings=%d, "
  3338	                    "spec_gap_findings=%d).",
  3339	                    len(wiring_dict.get("findings", [])) if wiring_dict else 0,
  3340	                    len(mocked_seam_dict.get("findings", [])) if mocked_seam_dict else 0,
  3341	                    len(spec_gap_dict.get("findings", [])) if spec_gap_dict else 0,
  3342	                )
  3343	        except Exception as exc:  # noqa: BLE001 — wiring errors must not break gathering
  3344	            logger.warning(
  3345	                "gather_evidence: wiring analysis raised %s; "
  3346	                "all three fields left as None.",
  3347	                exc.__class__.__name__,
  3348	            )
  3349	
  3350	        # ------------------------------------------------------------------
  3351	        # 6. Runtime parity (TASK-AB-COACHRUNPARITY01, arm b). Run the
  3352	        # deliverable's declared runtime entry point (the feature smoke
  3353	        # command) before approving, so a "passes pytest but does not run"
  3354	        # deliverable is caught pre-approval. Guarded to single-task waves
  3355	        # (the multi-task-wave caveat: a deliverable may not run standalone
  3356	        # until peers finish). Never breaks gathering; a runner error is an
  3357	        # absent (ran=False) signal, not a pass.
  3358	        # ------------------------------------------------------------------
  3359	        runtime_parity = self._gather_runtime_parity()
  3360	
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/quality_gates/coach_validator.py', 'limit': 150, 'offset': 3360}, 'id': 'fc_trFCbjzo5pvmSJSxEjOW7AeXQ5nEAn9j', 'type': 'tool_call'}]
Tool:   3361	        # ------------------------------------------------------------------
  3362	        # 7. Independent-test substrate-vs-code classification (TASK-ABFIX-012).
  3363	        # The live gather_evidence path carries NO failure classification on the
  3364	        # bundle today (the legacy validate() path's _classify_test_failure is
  3365	        # not on this path), so a genuine independent CODE failure has no
  3366	        # deterministic blocking guard — the FMDR-004 false-approval. Compute the
  3367	        # verdict HERE (the single place where the classifier + wave-context
  3368	        # is_parallel/wave_size + task_type converge) and carry it on the bundle
  3369	        # for AgentInvoker._apply_independent_test_code_failure_guard.
  3370	        #
  3371	        # Computed ONLY for a RAN-AND-FAILED run (tests_passed False AND
  3372	        # signal_absent False). An ABSENT signal (signal_absent True — e.g. a
  3373	        # host-substrate gap) is owned by the absent guard and must NEVER
  3374	        # manufacture a code verdict (absence-of-failure-is-not-success). A
  3375	        # passing / skipped run leaves it None.
  3376	        independent_test_classification: Optional[IndependentTestClassification] = None
  3377	        if (
  3378	            test_result.tests_passed is False
  3379	            and test_result.signal_absent is False
  3380	        ):
  3381	            fc, conf = self._classify_test_failure(
  3382	                test_result.raw_output,
  3383	                requires_infrastructure=(
  3384	                    task.get("requires_infrastructure") if task else None
  3385	                ),
  3386	                task_type=task_type.value,
  3387	            )
  3388	            # TASK-ABFIX-012: for a TESTING task the parallel-wave
  3389	            # parallel_contention amnesty must not cover the task's OWN failures.
  3390	            # A recognised own-code exception token is already ('code','high').
  3391	            # A NON-token failure (e.g. ValueError / KeyError / a custom
  3392	            # exception) in a parallel wave classifies parallel_contention here;
  3393	            # reclassify it to ('code','high') so the guard blocks it — UNLESS
  3394	            # there is genuine cross-task source-file contention (this task's
  3395	            # authored files overlap a peer's edits in the same wave), the one
  3396	            # case the amnesty must keep (constraint 3). The original ABFIX-005
  3397	            # contention (import / collection races) is caught earlier in the
  3398	            # classifier and never reaches here, so this only reclassifies real
  3399	            # own-code test failures, never a genuine race. Single-task waves
  3400	            # never produce parallel_contention, so this is a no-op there.
  3401	            if task_type == TaskType.TESTING and fc == "parallel_contention":
  3402	                if not self._detect_source_file_contention(task_work_results):
  3403	                    logger.info(
  3404	                        "gather_evidence: TESTING parallel failure with no peer "
  3405	                        "source-file overlap reclassified parallel_contention -> "
  3406	                        "('code','high') for %s (own-code failure, not contention).",
  3407	                        task_id,
  3408	                    )
  3409	                    fc, conf = "code", "high"
  3410	            independent_test_classification = IndependentTestClassification(
  3411	                failure_class=fc,
  3412	                confidence=conf,
  3413	                raw_output_excerpt=(test_result.raw_output or "")[-500:],
  3414	            )
  3415	
  3416	        return CoachEvidenceBundle(
  3417	            honesty=honesty,
  3418	            gathering_status="complete",
  3419	            quality_gates=gates,
  3420	            coverage_details=coverage_details,
  3421	            plan_audit=plan_audit_dict,
  3422	            bdd=bdd_dict,
  3423	            arch_review=arch_review_dict,
  3424	            tests=tests_dict,
  3425	            independent_tests=test_result,
  3426	            independent_test_classification=independent_test_classification,
  3427	            requirements=requirements,
  3428	            severity_recommendations=severity_recommendations,
  3429	            advisory_issues=advisory_issues,
  3430	            task_type=task_type.value,
  3431	            profile_name=profile_name,
  3432	            wiring=wiring_dict,
  3433	            mocked_seam=mocked_seam_dict,
  3434	            spec_gap=spec_gap_dict,
  3435	            runtime_parity=runtime_parity,
  3436	        )
  3437	
  3438	    def _gather_runtime_parity(self) -> Optional["RuntimeParityResult"]:
  3439	        """Run the deliverable's runtime entry point (TASK-AB-COACHRUNPARITY01, arm b).
  3440	
  3441	        Returns ``None`` when no smoke command was threaded (older callers /
  3442	        feature with no smoke gate). Returns a ``RuntimeParityResult`` with
  3443	        ``ran=False`` (and a ``skipped_reason``) when the check is intentionally
  3444	        skipped (parallel wave) or the runner itself errors — an ABSENT signal
  3445	        that never blocks and never counts as a pass
  3446	        (``absence-of-failure-is-not-success.md``). Returns ``ran=True`` with
  3447	        ``passed`` reflecting a clean (exit 0) standalone run otherwise.
  3448	
  3449	        Guard: runs only on a single-task wave (``wave_size == 1``). On a
  3450	        multi-task wave the deliverable may not run standalone until peers
  3451	        finish, so a per-task smoke run would false-fail; those waves rely on
  3452	        the feature-level post-wave smoke gate instead.
  3453	        """
  3454	        if not self.smoke_command:
  3455	            return None
  3456	
  3457	        command = self.smoke_command
  3458	        if self.wave_size > 1:
  3459	            return RuntimeParityResult(
  3460	                ran=False,
  3461	                passed=False,
  3462	                command=command,
  3463	                skipped_reason="parallel_wave",
  3464	            )
  3465	
  3466	        # PATH-prepend the bootstrap venv so a bare ``python`` / ``pytest`` in
  3467	        # the smoke command resolves to the right interpreter (mirrors
  3468	        # smoke_gates.run_smoke_gate's venv handling).
  3469	        env: Optional[dict] = None
  3470	        if self._venv_python is not None:
  3471	            env = os.environ.copy()
  3472	            env["PATH"] = (
  3473	                str(Path(self._venv_python).parent)
  3474	                + os.pathsep
  3475	                + env.get("PATH", "")
  3476	            )
  3477	
  3478	        try:
  3479	            proc = subprocess.run(
  3480	                command,
  3481	                shell=True,
  3482	                cwd=str(self.worktree_path),
  3483	                capture_output=True,
  3484	                text=True,
  3485	                timeout=self.test_timeout,
  3486	                env=env,
  3487	            )
  3488	        except subprocess.TimeoutExpired as exc:
  3489	            timeout_stderr = (
  3490	                exc.stderr.decode() if isinstance(exc.stderr, bytes)
  3491	                else exc.stderr
  3492	            ) or ""
  3493	            timeout_stdout = (
  3494	                exc.stdout.decode() if isinstance(exc.stdout, bytes)
  3495	                else exc.stdout
  3496	            ) or ""
  3497	            stderr_tail = "\n".join(
  3498	                timeout_stderr.rstrip().splitlines()[-40:]
  3499	            )
  3500	            logger.warning(
  3501	                "Runtime-parity check timed out after %ss: %s",
  3502	                self.test_timeout, command,
  3503	            )
  3504	            # NOTE: ran=True on timeout is operator-pinned
  3505	            # (TASK-AB-COACHRUNPARITY01: a smoke entry point that starts and
  3506	            # hangs is a real deliverable defect). output_tail is additive
  3507	            # evidence only — verdict/timeout semantics unchanged.
  3508	            return RuntimeParityResult(
  3509	                ran=True,
  3510	                passed=False,
AI: Now let me look at the rendering and existing tests:

[{'name': 'grep', 'args': {'pattern': 'def _build_coach_prompt', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator', 'output_mode': 'content'}, 'id': 'fc_tKWrO9oHn1n7tDJwEh86iuIvrY756Eyo', 'type': 'tool_call'}, {'name': 'glob', 'args': {'pattern': 'tests/orchestrator/**/test_*coach*', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC'}, 'id': 'fc_BB1zxYhQR3lHGZTJAKxOqvOEGGVQ7ItK', 'type': 'tool_call'}, {'name': 'glob', 'args': {'pattern': 'tests/orchestrator/**/test_*wiring*', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC'}, 'id': 'fc_6trw5Gy4kuPDtgOCTvKa6yZLKCMfODkZ', 'type': 'tool_call'}]
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py:
  2947:     def _build_coach_prompt(
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/quality_gates/test_coach_validator_evidence_repos.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_evidence_bundle.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_gather_bfull.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_incomplete_evidence_guard.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_independent_test_absent_guard.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_independent_test_timeout.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_interpreter_selection.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_narrative_reconciler.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_sdk_stream_resilience.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_synthesis_split.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_wiring_bundle.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_zero_cardinality_guard.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_llm_coach_primary.py']
Tool: ['/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/instrumentation/test_cli_emitter_wiring.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_wiring_bundle.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_wiring_ctor_arity_seam.py', '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_wiring_seam_real_factory.py']
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_wiring_bundle.py'}, 'id': 'fc_X664VKekXx1wGlmtyzXJBZrCvWlNCD90', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_wiring_ctor_arity_seam.py'}, 'id': 'fc_xT4PCs3uO6PjySxyMmjYCvqDXjKqD346', 'type': 'tool_call'}, {'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/tests/orchestrator/test_coach_evidence_bundle.py'}, 'id': 'fc_dL8F58JFXPLi6fiRFjpwpaJy6O3ByNdi', 'type': 'tool_call'}]
Tool:      1	"""AC-002 / AC-008 / AC-011 / AC-015 / AC-016 / AC-017 — UNWIRED_PATH bundle integration.
     2	
     3	TASK-QAWE-002, Wave 1. Verifies that the CoachEvidenceBundle carries the
     4	three new wiring fields (``wiring``, ``mocked_seam``, ``spec_gap``), that
     5	they are populated only on the complete-path return, that the task-type
     6	gate excludes SCAFFOLDING/DOCUMENTATION, that the fields reach the Coach
     7	prompt via ``_render_evidence_bundle_section``, that truncation works for
     8	>20 findings, that absent-vs-empty is distinct, and that graceful import
     9	absence does not crash.
    10	"""
    11	
    12	from __future__ import annotations
    13	
    14	import json
    15	import subprocess
    16	from pathlib import Path
    17	from typing import Any, Dict, List, Optional
    18	from unittest.mock import MagicMock, patch
    19	
    20	import pytest
    21	
    22	from guardkit.orchestrator.quality_gates.coach_evidence import (
    23	    CoachEvidenceBundle,
    24	)
    25	from guardkit.orchestrator.quality_gates.coach_validator import (
    26	    CoachValidator,
    27	    _compute_authored_set,
    28	    _run_wiring_analysis,
    29	)
    30	
    31	
    32	# ---------------------------------------------------------------------------
    33	# Fixture helpers
    34	# ---------------------------------------------------------------------------
    35	
    36	
    37	def _init_git_worktree(path: Path) -> None:
    38	    """Minimal git init so TaskStateBridge can construct without raising."""
    39	    subprocess.run(
    40	        ["git", "init", "-q"], cwd=path, check=True, capture_output=True
    41	    )
    42	    subprocess.run(
    43	        ["git", "-C", str(path), "config", "user.email", "t@t"], check=True, capture_output=True,
    44	    )
    45	    subprocess.run(
    46	        ["git", "-C", str(path), "config", "user.name", "t"], check=True, capture_output=True,
    47	    )
    48	
    49	
    50	def _passing_task_work_results(extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    51	    """Return a task_work_results dict where every gate passes."""
    52	    results: Dict[str, Any] = {
    53	        "task_id": "TASK-X",
    54	        "quality_gates": {
    55	            "all_passed": True,
    56	            "tests_run": 12,
    57	            "tests_failed": 0,
    58	            "coverage_met": True,
    59	            "line_coverage": 0.85,
    60	            "branch_coverage": 0.78,
    61	        },
    62	        "code_review": {"score": 80, "solid_score": 85, "dry_score": 78, "yagni_score": 82},
    63	        "plan_audit": {"status": "passed", "violations": 0, "severity": "low"},
    64	        "files_modified": [],
    65	        "files_created": [],
    66	        "tests_written": [],
    67	    }
    68	    if extra:
    69	        results.update(extra)
    70	    return results
    71	
    72	
    73	def _write_results(worktree: Path, task_id: str, results: Dict[str, Any]) -> None:
    74	    results_dir = worktree / ".guardkit" / "autobuild" / task_id
    75	    results_dir.mkdir(parents=True, exist_ok=True)
    76	    (results_dir / "task_work_results.json").write_text(json.dumps(results))
    77	
    78	
    79	@pytest.fixture
    80	def worktree(tmp_path: Path) -> Path:
    81	    """A git worktree with a default-honest passing-turn fixture written."""
    82	    _init_git_worktree(tmp_path)
    83	    _write_results(tmp_path, "TASK-X", _passing_task_work_results())
    84	    return tmp_path
    85	
    86	
    87	# ---------------------------------------------------------------------------
    88	# AC-002: Bundle fields exist
    89	# ---------------------------------------------------------------------------
    90	
    91	
    92	class TestAC002BundleFields:
    93	    """AC-002: wiring, mocked_seam, spec_gap Optional[Dict] fields exist."""
    94	
    95	    def test_bundle_has_wiring_field(self, worktree: Path) -> None:
    96	        """The CoachEvidenceBundle dataclass has a ``wiring`` field."""
    97	        validator = CoachValidator(str(worktree), task_id="TASK-X")
    98	        bundle = validator.gather_evidence(
    99	            task_id="TASK-X",
   100	            turn=1,
Tool:      1	"""Cross-repo contract seam test for the guardkit↔guardkitfactory wiring gate.
     2	
     3	TASK-AB-WIREGATE01. CI enforcement for the migrated-contract-boundary meta-rule
     4	(``.claude/rules/namespace-hygiene.md`` /
     5	``.claude/rules/evidence-boundary-narrower-than-write-surface.md`` /
     6	``.claude/rules/harness-cancellation-contract.md``): the post-wave wiring gate
     7	in guardkit (``FeatureOrchestrator._run_post_wave_wiring_gate``) depends on the
     8	``guardkitfactory.wiring.analyze_wiring`` result carrying a ``ctor_arity`` key
     9	(and on ``mocked_seam[*].authored_this_turn`` for the seam half). If a
    10	guardkitfactory version skew drops the ctor-arity contract, that dependency must
    11	fail **here, in seconds, in CI** — not silently degrade to absent-signal on a
    12	live autobuild run (the false-green this whole task exists to close).
    13	
    14	Unlike the mocked unit tests in ``tests/unit/orchestrator/test_wiring_gate.py``,
    15	this module exercises the **real installed** ``guardkitfactory.wiring`` end to
    16	end over a FEAT-POC-006-shaped worktree.
    17	
    18	* ``pytest.importorskip`` makes the module skip cleanly in a dev venv without
    19	  the ``[autobuild]`` extra (no guardkitfactory) — opt-in for the seam CI job.
    20	* Fast: one ``analyze_wiring`` call over a tiny tmp worktree. No LLM, no GB10.
    21	"""
    22	
    23	from __future__ import annotations
    24	
    25	from pathlib import Path
    26	
    27	import pytest
    28	
    29	pytestmark = [pytest.mark.seam]
    30	
    31	wiring = pytest.importorskip("guardkitfactory.wiring")
    32	
    33	from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator
    34	
    35	
    36	_SERVICE = (
    37	    "class VoiceService:\n"
    38	    "    def __init__(self, transport, config):\n"
    39	    "        self.transport = transport\n"
    40	)
    41	
    42	
    43	def _write(root: Path, rel: str, content: str) -> str:
    44	    p = root / rel
    45	    p.parent.mkdir(parents=True, exist_ok=True)
    46	    p.write_text(content)
    47	    return rel
    48	
    49	
    50	class TestWiringResultContract:
    51	    """The result-dict shape guardkit's gate consumes must be present."""
    52	
    53	    def test_analyze_wiring_returns_ctor_arity_key(self, tmp_path):
    54	        svc = _write(tmp_path, "src/svc.py", _SERVICE)
    55	        result = wiring.analyze_wiring([svc], tmp_path, "feature")
    56	        assert result is not None
    57	        # The contract guardkit's gate reads. Missing key = version skew.
    58	        assert "ctor_arity" in result, (
    59	            "guardkitfactory.wiring.analyze_wiring dropped the 'ctor_arity' "
    60	            "key the post-wave wiring gate depends on"
    61	        )
    62	        assert "mocked_seam" in result
    63	        assert "status" in result["ctor_arity"]
    64	        assert "findings" in result["ctor_arity"]
    65	
    66	    def test_dialect_exposes_ctor_arity_query_fields(self):
    67	        py = wiring.get_dialect("python")
    68	        assert py is not None
    69	        for field_name in (
    70	            "composition_root_markers",
    71	            "constructor_signature_query",
    72	            "constructor_call_query",
    73	            "param_self_names",
    74	            "param_default_node_types",
    75	            "param_splat_node_types",
    76	            "param_required_node_types",
    77	            "arg_keyword_node_types",
    78	            "arg_splat_node_types",
    79	        ):
    80	            assert hasattr(py, field_name), (
    81	                f"WiringDialect dropped '{field_name}' the ctor-arity probe needs"
    82	            )
    83	        # Python populates them (day-one stack).
    84	        assert py.constructor_signature_query
    85	        assert py.composition_root_markers
    86	
    87	
    88	class TestEndToEndCtorArityThroughGate:
    89	    """The real factory output flows through guardkit's collector correctly."""
    90	
    91	    def test_feat_poc_006_shape_produces_turn_rejecting_findings(self, tmp_path):
    92	        svc = _write(tmp_path, "src/voice/service.py", _SERVICE)
    93	        main = _write(
    94	            tmp_path,
    95	            "main.py",
    96	            "from src.voice.service import VoiceService\n"
    97	            "def build():\n    return VoiceService(transport)\n",
    98	        )
    99	        test = _write(
   100	            tmp_path,
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
AI: [{'name': 'read_file', 'args': {'file_path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py', 'limit': 200, 'offset': 2947}, 'id': 'fc_XBpOYXHxLZhwEZi0wFbR94qIKlp80aW2', 'type': 'tool_call'}, {'name': 'grep', 'args': {'pattern': '_render_evidence_bundle_section', 'path': '/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC', 'output_mode': 'content'}, 'id': 'fc_cagZOALk3xOpQHo3w3RCwo5tyeidg1bt', 'type': 'tool_call'}]
Tool:   2948	        self,
  2949	        task_id: str,
  2950	        turn: int,
  2951	        requirements: str,
  2952	        player_report: Dict[str, Any],
  2953	        honesty_verification: Optional[HonestyVerification] = None,
  2954	        acceptance_criteria: Optional[List[Dict[str, str]]] = None,
  2955	        design_context: Optional["DesignContext"] = None,
  2956	        evidence_bundle: Optional["CoachEvidenceBundle"] = None,
  2957	        coach_context: Optional[str] = None,
  2958	        synthesis: bool = False,
  2959	        gather_findings: Optional[str] = None,
  2960	    ) -> str:
  2961	        """Build prompt for Coach agent invocation with promise verification.
  2962	
  2963	        Args:
  2964	            task_id: Task identifier
  2965	            turn: Turn number
  2966	            requirements: Original task requirements
  2967	            player_report: Player's report from current turn
  2968	            honesty_verification: Optional verification results for Player claims.
  2969	                When ``evidence_bundle`` is also provided, the bundle's
  2970	                ``honesty`` field is the canonical source (channel unification
  2971	                per plan §4); this parameter then serves only as a legacy
  2972	                fallback path for callers that pass it directly.
  2973	            acceptance_criteria: Optional list of acceptance criteria with id and text
  2974	            design_context: Optional design context for visual verification
  2975	            evidence_bundle: Optional ``CoachEvidenceBundle`` from
  2976	                ``CoachValidator.gather_evidence`` (TASK-HMIG-008R Part C).
  2977	                When provided, the bundle is JSON-rendered into a
  2978	                ``<evidence_bundle>...</evidence_bundle>`` section so the
  2979	                LLM Coach can read deterministic gate outputs (coverage,
  2980	                plan_audit, bdd, arch_review, tests) plus the Layer-1/
  2981	                Layer-2 severity recommendations. The five
  2982	                absence-of-failure guards (AC-009 + gathering_status guard)
  2983	                are emitted in an ``<absence_of_failure_guards>`` section
  2984	                so the Coach has explicit instructions for treating absent
  2985	                evidence as ABSENT SIGNAL rather than approving on
  2986	                absence-of-failure.
  2987	            coach_context: Optional memory / coach context string. When
  2988	                provided, surfaced in a ``## Coach Context`` section.
  2989	            synthesis: When ``True`` (TASK-ARCH-COACHSPLIT D-3), render the
  2990	                TOOLLESS synthesis variant: the Coach has NO tools and bases
  2991	                its verdict on the deterministic evidence bundle the
  2992	                orchestrator already gathered (tests, coverage, honesty,
  2993	                plan_audit, bdd, arch_review run independently in
  2994	                ``gather_evidence``) rather than re-investigating with
  2995	                Read/Bash/Grep/Glob. The "Your Responsibilities" section is
  2996	                rewritten accordingly and a toolless-framing banner is added.
  2997	                The Decision Format section is identical — the GBNF grammar
  2998	                enforces the same schema the examples describe.
  2999	            gather_findings: Optional Phase-A investigation findings text
  3000	                (TASK-ARCH-COACHBFULL B-full). When provided, rendered into a
  3001	                ``## Coach Investigation Findings (Phase A)`` section so the
  3002	                toolless synthesis grounds its per-AC verdict on what the
  3003	                tool-using gather pass actually found on disk. ``None`` (the
  3004	                default, and the B-min path) omits the section entirely.
  3005	
  3006	        Returns:
  3007	            Formatted prompt string for Coach agent
  3008	        """
  3009	        # TASK-HMIG-008R Part C: when an evidence bundle is provided, its
  3010	        # `honesty` field is the canonical honesty channel — overriding the
  3011	        # legacy honesty_verification parameter to avoid duplicate honesty
  3012	        # sections in the prompt. The bundle's honesty was computed by
  3013	        # gather_evidence with state_bridge identity resolution and carries
  3014	        # resolved_paths annotations that the legacy parameter would lack.
  3015	        if evidence_bundle is not None and evidence_bundle.honesty is not None:
  3016	            honesty_verification = evidence_bundle.honesty
  3017	
  3018	        # Build honesty verification section. Under the bundle path the
  3019	        # section is rendered as structured JSON inside an XML-like tag
  3020	        # so the LLM Coach can parse it deterministically and apply the
  3021	        # absence-of-failure guards below against specific fields. The
  3022	        # legacy free-text format is retained for back-compat callers
  3023	        # (no bundle, just honesty_verification).
  3024	        honesty_section = ""
  3025	        if evidence_bundle is not None and honesty_verification is not None:
  3026	            # Bundle path: emit structured XML-tagged JSON section.
  3027	            honesty_section = self._render_bundle_honesty_section(
  3028	                honesty_verification
  3029	            )
  3030	        elif honesty_verification:
  3031	            # Legacy path: emit prose section.
  3032	            honesty_section = f"""
  3033	## Honesty Verification (Pre-Validated)
  3034	
  3035	{format_verification_context(honesty_verification)}
  3036	
  3037	{"⚠️ CRITICAL DISCREPANCIES DETECTED - Factor this into your decision!" if honesty_verification.discrepancies else "✓ Player claims verified."}
  3038	"""
  3039	
  3040	        # Build evidence bundle section + absence-of-failure guards (Part C).
  3041	        evidence_section = ""
  3042	        guards_section = ""
  3043	        if evidence_bundle is not None:
  3044	            evidence_section = self._render_evidence_bundle_section(
  3045	                evidence_bundle
  3046	            )
  3047	            guards_section = self._render_absence_of_failure_guards()
  3048	
  3049	        # Coach context section (memory / external context).
  3050	        coach_context_section = ""
  3051	        if coach_context:
  3052	            coach_context_section = f"""
  3053	## Coach Context
  3054	
  3055	{coach_context}
  3056	"""
  3057	
  3058	        # TASK-ARCH-COACHBFULL: Phase-A investigation findings section. Rendered
  3059	        # only when the B-full gather ran and produced findings; advisory input
  3060	        # the toolless synthesis grounds its per-AC verdict on. Absent findings
  3061	        # (B-min path) omit the section — never a new false-green: the
  3062	        # synthesis banner + absence-of-failure guards still treat
  3063	        # unverifiable evidence as FEEDBACK, not approval.
  3064	        gather_findings_section = ""
  3065	        if gather_findings and gather_findings.strip():
  3066	            # TASK-PERF-COACHSYNTH (AC-4): bound the findings text injected into
  3067	            # the synthesis prompt — marked, never silently dropped.
  3068	            _bounded_findings = self._truncate_gather_findings(gather_findings.strip())
  3069	            gather_findings_section = f"""
  3070	## Coach Investigation Findings (Phase A)
  3071	
  3072	A tool-using investigation pass ran BEFORE this verdict and probed the worktree
  3073	directly (read changed files, ran focused tests, checked acceptance criteria).
  3074	Its findings — a per-criterion compliance checklist — are below. Treat them as
  3075	authoritative evidence of what is actually on disk, on equal footing with the
  3076	Deterministic Evidence Bundle. Where a finding marks a criterion FAIL or UNSURE,
  3077	that criterion is NOT satisfied for approval purposes.
  3078	
  3079	{_bounded_findings}
  3080	"""
  3081	
  3082	        # Build acceptance criteria section for verification
  3083	        criteria_section = ""
  3084	        if acceptance_criteria:
  3085	            criteria_lines = ["## Acceptance Criteria to Verify", ""]
  3086	            criteria_lines.append("Verify EACH criterion and create a criteria_verification entry:")
  3087	            criteria_lines.append("")
  3088	            for criterion in acceptance_criteria:
  3089	                criteria_lines.append(f"- **{criterion['id']}**: {criterion['text']}")
  3090	            criteria_section = "\n".join(criteria_lines) + "\n"
  3091	
  3092	        # Build criteria verification example
  3093	        verification_example = ""
  3094	        if acceptance_criteria:
  3095	            example_verifications = []
  3096	            for criterion in acceptance_criteria[:2]:  # Show first 2 as examples
  3097	                example_verifications.append(f'''    {{
  3098	      "criterion_id": "{criterion['id']}",
  3099	      "result": "verified",
  3100	      "notes": "Your reasoning for verification or rejection"
  3101	    }}''')
  3102	            verification_example = f'''
  3103	  "criteria_verification": [
  3104	{",".join(example_verifications)}
  3105	  ],'''
  3106	
  3107	        # Build visual verification section if design context provided
  3108	        visual_verification_section = ""
  3109	        if design_context:
  3110	            visual_verification_section = f"""
  3111	## Visual Verification (Design Mode)
  3112	
  3113	In addition to standard code review:
  3114	1. Render the generated component in a browser
  3115	2. Capture a screenshot
  3116	3. Compare against design reference using SSIM
  3117	4. Check prohibition checklist compliance
  3118	5. Report: visual fidelity score + any constraint violations
  3119	
  3120	**Visual Reference**: {design_context.visual_reference or "Not available"}
  3121	
  3122	Quality Gates:
  3123	- Visual fidelity: >= 95% SSIM match
  3124	- Constraint violations: Zero tolerance
  3125	- Design tokens: 100% applied (exact match)
  3126	"""
  3127	
  3128	        # TASK-ARCH-COACHSPLIT (D-3): the synthesis variant frames the turn
  3129	        # as evidence-grounded verdict synthesis with NO tools, and rewrites
  3130	        # the responsibilities so the model does not try (and fail) to invoke
  3131	        # Read/Bash/Grep/Glob — it has none. The deterministic evidence the
  3132	        # tool-using gather phase would have sought has already been produced
  3133	        # by CoachValidator.gather_evidence and is rendered above.
  3134	        if synthesis:
  3135	            # Only assert that a Deterministic Evidence Bundle was rendered when
  3136	            # one actually exists. invoke_coach gates synthesis on bundle
  3137	            # presence (synthesis ⇒ a bundle was passed), so the with-bundle
  3138	            # banner is the production path; the no-bundle branch keeps this
  3139	            # builder honest if it is ever invoked with synthesis=True and no
  3140	            # bundle directly (so the prompt never claims evidence it lacks).
  3141	            if evidence_bundle is not None:
  3142	                synthesis_banner = """\
  3143	**TOOLLESS SYNTHESIS** — You have NO tools available (no Read, Bash, Grep, or
  3144	Glob). Do not attempt to run tests or read files; you cannot. The orchestrator
  3145	has ALREADY run the tests, coverage, honesty checks, plan audit, BDD oracle,
  3146	and architectural review independently — their results are in the Deterministic
  3147	Evidence Bundle above. Base your verdict ENTIRELY on that evidence, the
Tool: /home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/docs/features/qa-verifier-wiring-probes-scope.md:
  138: `_render_evidence_bundle_section` (`agent_invoker.py:3098-3191`) JSON-dumps `bundle.to_dict()` at line 3178 — all three fields surface automatically. **Add findings-truncation** for `wiring.findings` / `mocked_seam.findings` / `spec_gap.findings` (keep first 20 + `"... and N more"`) mirroring the `bdd.discoveries` truncation at `agent_invoker.py:3138-3152` (**VERIFIED** pattern).
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/docs/state/TASK-ARCH-COACHBFULL/implementation_plan.md:
  77: `_render_evidence_bundle_section` + honesty + a structured AC checklist. Explicit
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/docs/state/TASK-FIX-COACHOUT01/implementation_plan.md:
  74: The `criteria_verification` and `honesty_verification` examples already rendered into the prompt by `_render_evidence_bundle_section` and `_build_coach_prompt` remain unchanged — only the "write to file" instruction is replaced.
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/guardkit/orchestrator/agent_invoker.py:
  2651:             evidence_section = self._render_evidence_bundle_section(
  3044:             evidence_section = self._render_evidence_bundle_section(
  3349:     def _render_evidence_bundle_section(
/home/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-10AC/ia03_cov.json:
  1: {"meta": {"format": 3, "version": "7.14.1", "timestamp": "2026-06-11T15:39:57.016285", "branch_coverage": true, "show_contexts": false}, "files": {"guardkit/orchestrator/agent_invoker.py": {"executed_lines": [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 28, 40, 41, 48, 49, 50, 51, 52, 57, 71, 87, 92, 103, 119, 126, 173, 182, 208, 210, 211, 221, 222, 223, 237, 240, 271, 273, 274, 275, 276, 277, 278, 279, 280, 284, 285, 288, 289, 290, 292, 293, 304, 305, 309, 315, 323, 400, 401, 432, 434, 436, 437, 438, 439, 440, 441, 444, 452, 455, 456, 457, 459, 460, 461, 467, 472, 476, 482, 483, 486, 498, 499, 510, 511, 513, 522, 523, 524, 533, 546, 549, 556, 557, 558, 571, 574, 596, 597, 622, 625, 642, 645, 651, 664, 680, 685, 688, 695, 696, 698, 699, 700, 701, 702, 703, 704, 706, 707, 711, 726, 734, 745, 752, 759, 760, 761, 772, 775, 802, 803, 804, 805, 806, 807, 808, 809, 810, 812, 813, 816, 818, 820, 821, 823, 828, 830, 832, 833, 834, 835, 836, 837, 838, 846, 847, 848, 849, 850, 851, 853, 867, 869, 882, 883, 885, 886, 887, 889, 890, 903, 904, 905, 907, 908, 910, 912, 925, 931, 932, 936, 938, 939, 940, 941, 943, 944, 945, 946, 947, 948, 949, 951, 962, 963, 964, 965, 966, 967, 968, 971, 972, 973, 974, 975, 977, 978, 979, 980, 981, 983, 1002, 1003, 1006, 1009, 1010, 1011, 1012, 1013, 1018, 1021, 1022, 1023, 1024, 1025, 1026, 1029, 1032, 1033, 1034, 1035, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 1053, 1054, 1057, 1058, 1059, 1060, 1061, 1064, 1065, 1066, 1067, 1070, 1071, 1072, 1073, 1074, 1075, 1078, 1079, 1080, 1081, 1082, 1084, 1085, 1086, 1087, 1088, 1091, 1092, 1093, 1094, 1095, 1099, 1100, 1101, 1102, 1103, 1104, 1105, 1109, 1125, 1127, 1128, 1130, 1131, 1133, 1134, 1136, 1137, 1139, 1140, 1142, 1143, 1145, 1146, 1153, 1154, 1156, 1157, 1159, 1160, 1161, 1162, 1163, 1164, 1165, 1166, 1167, 1169, 1171, 1177, 1178, 1179, 1180, 1181, 1182, 1183, 1184, 1185, 1186, 1187, 1188, 1189, 1192, 1193, 1206, 1207, 1208, 1209, 1210, 1211, 1212, 1213, 1214, 1215, 1216, 1219, 1248, 1250, 1295, 1296, 1297, 1298, 1299, 1300, 1304, 1308, 1309, 1316, 1317, 1319, 1321, 1323, 1325, 1334, 1345, 1347, 1359, 1368, 1374, 1384, 1412, 1424, 1425, 1426, 1427, 1429, 1435, 1450, 1464, 1477, 1478, 1480, 1481, 1482, 1484, 1485, 1486, 1538, 1544, 1546, 1547, 1580, 1586, 1587, 1588, 1589, 1590, 1593, 1595, 1602, 1603, 1604, 1605, 1606, 1607, 1608, 1609, 1610, 1611, 1612, 1616, 1617, 1620, 1621, 1625, 1626, 1631, 1635, 1642, 1644, 1645, 1647, 1651, 1652, 1655, 1657, 1662, 1663, 1664, 1668, 1669, 1670, 1671, 1674, 1675, 1676, 1680, 1682, 1683, 1684, 1685, 1686, 1687, 1691, 1692, 1700, 1701, 1705, 1706, 1710, 1711, 1716, 1720, 1774, 1784, 1785, 1789, 1790, 1794, 1795, 1796, 1799, 1802, 1804, 1806, 1809, 1810, 1814, 1815, 1829, 1830, 1836, 1838, 1849, 1851, 1856, 1859, 1860, 1863, 1864, 1865, 1866, 1869, 1875, 1888, 1900, 1904, 1911, 1922, 1923, 1925, 1928, 1933, 1943, 1944, 1945, 1986, 1988, 2048, 2051, 2052, 2053, 2055, 2064, 2067, 2090, 2104, 2105, 2127, 2141, 2179, 2188, 2192, 2203, 2206, 2207, 2219, 2220, 2233, 2242, 2248, 2250, 2259, 2260, 2261, 2270, 2281, 2282, 2283, 2294, 2296, 2420, 2520, 2545, 2546, 2547, 2556, 2557, 2565, 2566, 2589, 2590, 2591, 2592, 2593, 2594, 2595, 2596, 2599, 2600, 2601, 2602, 2603, 2611, 2616, 2667, 2668, 2670, 2672, 2697, 2710, 2728, 2796, 2805, 2806, 2811, 2813, 2822, 2823, 2824, 2831, 2832, 2845, 2846, 2864, 2865, 2866, 2867, 2868, 2869, 2870, 2871, 2874, 2875, 2876, 2877, 2878, 2883, 2889, 2890, 2915, 2964, 2965, 2979, 3059, 3066, 3067, 3068, 3079, 3083, 3084, 3098, 3193, 3261, 3335, 3356, 3357, 3360, 3362, 3363, 3367, 3368, 3377, 3384, 3488, 3500, 3501, 3502, 3509, 3514, 3518, 3519, 3525, 3528, 3529, 3530, 3535, 3555, 3570, 3575, 3578, 3580, 3586, 3623, 3655, 3667, 3675, 3677, 3678, 3679, 3680, 3684, 3704, 3713, 3720, 3723, 3731, 3751, 3752, 3753, 3754, 3758, 3769, 3778, 3816, 3822, 3823, 3824, 3825, 3857, 3858, 3859, 3861, 3869, 3879, 3880, 3883, 3895, 3932, 3934, 3936, 3961, 3962, 3965, 3968, 3971, 3974, 3976, 3992, 3994, 3995, 4003, 4004, 4005, 4018, 4021, 4023, 4120, 4145, 4146, 4147, 4150, 4170, 4171, 4172, 4173, 4176, 4177, 4183, 4189, 4190, 4191, 4192, 4193, 4198, 4199, 4207, 4208, 4209, 4210, 4215, 4220, 4221, 4222, 4229, 4230, 4231, 4234, 4235, 4240, 4244, 4245, 4251, 4252, 4253, 4254, 4255, 4257, 4258, 4261, 4262, 4273, 4274, 4276, 4279, 4305, 4308, 4313, 4314, 4315, 4316, 4322, 4323, 4326, 4327, 4330, 4331, 4333, 4334, 4335, 4336, 4337, 4338, 4339, 4340, 4344, 4345, 4346, 4347, 4348, 4351, 4361, 4362, 4363, 4370, 4371, 4418, 4419, 4420, 4421, 4423, 4427, 4428, 4432, 4433, 4434, 4439, 4446, 4475, 4476, 4485, 4486, 4488, 4493, 4494, 4495, 4496, 4498, 4501, 4502, 4503, 4505, 4506, 4507, 4510, 4515, 4516, 4517, 4527, 4528, 4533, 4536, 4537, 4538, 4546, 4547, 4548, 4549, 4563, 4564, 4570, 4571, 4572, 4573, 4576, 4577, 4579, 4594, 4602, 4603, 4617, 4623, 4624, 4629, 4645, 4653, 4655, 4656, 4657, 4664, 4665, 4666, 4667, 4668, 4669, 4670, 4672, 4684, 4686, 4688, 4689, 4691, 4692, 4699, 4700, 4705, 4712, 4713, 4717, 4718, 4719, 4720, 4722, 4724, 4752, 4754, 4755, 4756, 4757, 4759, 4760, 4761, 4762, 4763, 4766, 4767, 4773, 4774, 4779, 4780, 4782, 4797, 4807, 4816, 4817, 4818, 4820, 4821, 4823, 4825, 4834, 4835, 4836, 4843, 4867, 4903, 4925, 4928, 4929, 4930, 4934, 4939, 4940, 4941, 4942, 4943, 4944, 4952, 4954, 4982, 4983, 4985, 4986, 4987, 4988, 4989, 4990, 4991, 4995, 4996, 4999, 5001, 5017, 5019, 5028, 5029, 5031, 5032, 5033, 5034, 5035, 5040, 5041, 5042, 5043, 5044, 5045, 5046, 5048, 5057, 5058, 5060, 5061, 5063, 5070, 5071, 5075, 5076, 5077, 5079, 5080, 5081, 5083, 5133, 5134, 5135, 5136, 5196, 5220, 5223, 5225, 5226, 5227, 5229, 5230, 5232, 5250, 5261, 5262, 5265, 5268, 5269, 5276, 5277, 5279, 5283, 5284, 5286, 5288, 5302, 5304, 5305, 5306, 5308, 5309, 5310, 5311, 5312, 5313, 5314, 5315, 5317, 5327, 5335, 5361, 5363, 5380, 5381, 5382, 5384, 5388, 5390, 5402, 5404, 5405, 5406, 5408, 5409, 5410, 5411, 5412, 5413, 5414, 5415, 5417, 5443, 5444, 5446, 5473, 5475, 5477, 5478, 5480, 5482, 5484, 5535, 5560, 5561, 5565, 5567, 5569, 5570, 5572, 5581, 5582, 5586, 5587, 5590, 5591, 5596, 5598, 5601, 5605, 5606, 5609, 5612, 5620, 5622, 5646, 5648, 5649, 5653, 5655, 5656, 5658, 5662, 5663, 5667, 5669, 5670, 5676, 5677, 5679, 5685, 5687, 5721, 5723, 5724, 5730, 5733, 5742, 5755, 5761, 5762, 5763, 5803, 5811, 5814, 5819, 5820, 5822, 5825, 5830, 5926, 5951, 5952, 5955, 5956, 5957, 5961, 5962, 5963, 5965, 5995, 5996, 5997, 6000, 6001, 6005, 6008, 6009, 6011, 6013, 6042, 6043, 6048, 6068, 6069, 6073, 6074, 6077, 6078, 6079, 6081, 6084, 6085, 6087, 6089, 6163, 6195, 6198, 6210, 6218, 6219, 6225, 6226, 6227, 6234, 6235, 6236, 6237, 6246, 6247, 6248, 6260, 6263, 6264, 6266, 6267, 6268, 6271, 6274, 6275, 6283, 6294, 6296, 6310, 6311, 6314, 6317, 6318, 6319, 6322, 6323, 6324, 6326, 6327, 6328, 6329, 6330, 6332, 6333, 6334, 6335, 6336, 6339, 6340, 6342, 6344, 6364, 6367, 6370, 6371, 6377, 6384, 6385, 6386, 6393, 6394, 6402, 6509, 6511, 6551, 6563, 6564, 6565, 6566, 6585, 6590, 6599, 6603, 6615, 6616, 6617, 6621, 6622, 6623, 6624, 6625, 6629, 6636, 6637, 6638, 6639, 6640, 6641, 6642, 6643, 6644, 6646, 6647, 6648, 6652, 6653, 6654, 6655, 6656, 6657, 6658, 6659, 6660, 6670, 6707, 6718, 6719, 6727, 6736, 6737, 6742, 6745, 6750, 6751, 6752, 6777, 6779, 6780, 6781, 6782, 6792, 6797, 6798, 6799, 6837, 6865, 6866, 6874, 6875, 6881, 6882, 6883, 6886, 6888, 6889, 6894, 6905, 6911, 6915, 6916, 6921, 6922, 6925, 6927, 6928, 6936, 6937, 6938, 6939, 6940, 6943, 6944, 6946, 6960, 6961, 6965, 6966, 6969, 6972, 7016, 7031, 7040, 7041, 7044, 7045, 7046, 7047, 7049, 7050, 7051, 7054, 7055, 7057, 7059, 7084, 7085, 7091, 7110, 7112, 7114, 7115, 7116, 7118, 7119, 7120, 7123, 7124, 7125, 7126, 7129, 7130, 7131, 7137, 7138, 7139, 7140, 7143, 7144, 7150, 7162, 7164, 7167, 7173, 7174, 7178, 7184, 7185, 7186, 7187, 7189, 7191, 7215, 7216, 7218, 7242, 7243, 7245, 7292, 7311, 7312, 7313, 7325, 7377, 7396, 7397, 7399, 7411, 7412, 7413, 7416, 7421, 7423, 7432, 7433, 7437, 7438, 7443, 7456, 7457, 7460, 7461, 7470, 7471, 7478, 7479, 7480, 7481, 7482, 7483, 7485, 7486, 7488, 7490, 7495, 7497, 7523, 7524, 7525, 7527, 7528, 7537, 7538, 7539, 7552, 7553, 7554, 7555, 7557, 7565, 7566, 7570, 7571, 7579, 7580, 7586, 7615, 7620, 7805, 7849, 7851, 7852, 7853, 7927, 7981, 7983, 7984, 7985, 8051, 8131, 8132, 8135, 8136, 8137, 8169, 8192, 8193, 8219, 8228, 8229, 8277, 8278, 8296, 8428, 8473, 8475, 8478, 8479, 8480, 8481, 8485, 8492, 8493, 8494, 8508, 8538, 8539, 8540, 8551, 8555, 8556, 8557, 8560, 8561, 8576, 8577, 8583, 8587, 8592, 8598, 8618, 8619, 8624, 8626, 8638, 8648, 8649, 8659, 8662, 8667, 8668, 8670, 8672, 8709, 8711, 8714, 8740, 8741, 8743, 8745, 8763, 8766, 8767, 8768, 8771, 8772, 8773, 8776, 8777, 8778, 8781, 8782, 8783, 8784, 8785, 8787, 8789, 8819, 8822, 8823, 8828, 8831, 8833, 8835, 8836, 8837, 8849, 8859, 8867, 8868, 8869, 8870, 8871, 8872, 8874], "summary": {"covered_lines": 1490, "num_statements": 2413, "percent_covered": 58.618636498958026, "percent_covered_display": "59", "missing_lines": 923, "excluded_lines": 3, "percent_statements_covered": 61.748860339825946, "percent_statements_covered_display": "62", "num_branches": 946, "num_partial_branches": 131, "covered_branches": 479, "missing_branches": 467, "percent_branches_covered": 50.63424947145877, "percent_branches_covered_display": "51"}, "missing_lines": [209, 212, 224, 225, 226, 227, 230, 235, 281, 282, 286, 291, 294, 295, 296, 297, 298, 299, 301, 302, 303, 306, 307, 310, 362, 363, 364, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 382, 384, 386, 445, 453, 500, 501, 502, 503, 504, 512, 559, 581, 582, 583, 584, 906, 1028, 1096, 1097, 1106, 1107, 1348, 1360, 1361, 1382, 1398, 1399, 1400, 1401, 1402, 1403, 1404, 1405, 1406, 1428, 1444, 1460, 1461, 1462, 1487, 1488, 1489, 1490, 1491, 1493, 1494, 1495, 1496, 1497, 1500, 1501, 1502, 1503, 1504, 1505, 1506, 1508, 1509, 1514, 1515, 1518, 1519, 1520, 1521, 1522, 1526, 1527, 1530, 1531, 1535, 1536, 1539, 1561, 1562, 1563, 1564, 1565, 1566, 1567, 1568, 1569, 1570, 1571, 1572, 1573, 1574, 1575, 1577, 1578, 1681, 1695, 1696, 1707, 1708, 1816, 1819, 1955, 1956, 1957, 1967, 1968, 1969, 1970, 1971, 1973, 1974, 2065, 2108, 2115, 2145, 2146, 2147, 2151, 2152, 2153, 2165, 2271, 2272, 2347, 2348, 2349, 2350, 2362, 2382, 2383, 2384, 2390, 2395, 2396, 2397, 2398, 2399, 2404, 2405, 2409, 2410, 2411, 2416, 2418, 2442, 2443, 2444, 2448, 2449, 2453, 2454, 2455, 2456, 2459, 2460, 2467, 2468, 2469, 2476, 2477, 2478, 2480, 2558, 2567, 2681, 2682, 2683, 2684, 2685, 2686, 2687, 2688, 2689, 2690, 2691, 2692, 2693, 2694, 2695, 2706, 2707, 2708, 2719, 2720, 2721, 2722, 2723, 2724, 2725, 2726, 2797, 2808, 2825, 2828, 2833, 2849, 2850, 2891, 2922, 2923, 2933, 2942, 3086, 3087, 3088, 3089, 3090, 3124, 3125, 3126, 3127, 3133, 3139, 3140, 3141, 3142, 3143, 3144, 3147, 3148, 3149, 3150, 3157, 3158, 3159, 3160, 3164, 3165, 3177, 3178, 3179, 3180, 3183, 3185, 3210, 3212, 3213, 3214, 3215, 3219, 3228, 3229, 3233, 3234, 3245, 3246, 3247, 3248, 3251, 3253, 3277, 3373, 3379, 3380, 3382, 3576, 3625, 3626, 3627, 3631, 3641, 3642, 3643, 3644, 3652, 3653, 3656, 3668, 3705, 3759, 3762, 3770, 3771, 3779, 3780, 3781, 3793, 3794, 3795, 3796, 3797, 3798, 3799, 3804, 3826, 3834, 3835, 3838, 3844, 3845, 3846, 3853, 3854, 3855, 3856, 3862, 3863, 3864, 3896, 3905, 3910, 3919, 3933, 3996, 3997, 4006, 4008, 4009, 4011, 4058, 4059, 4061, 4063, 4064, 4066, 4069, 4070, 4073, 4076, 4079, 4081, 4095, 4097, 4098, 4099, 4100, 4106, 4107, 4108, 4109, 4111, 4112, 4114, 4184, 4211, 4212, 4213, 4236, 4237, 4238, 4280, 4281, 4282, 4285, 4288, 4291, 4292, 4297, 4298, 4350, 4364, 4367, 4368, 4372, 4373, 4374, 4377, 4378, 4379, 4380, 4386, 4387, 4388, 4389, 4390, 4396, 4397, 4398, 4399, 4401, 4402, 4406, 4408, 4409, 4426, 4440, 4441, 4447, 4454, 4455, 4456, 4479, 4480, 4511, 4512, 4567, 4568, 4604, 4609, 4615, 4618, 4622, 4630, 4631, 4632, 4637, 4639, 4837, 4838, 4839, 4840, 4841, 4852, 4854, 4855, 4857, 4858, 4859, 4860, 4861, 4862, 4863, 4865, 4892, 4896, 4948, 5062, 5064, 5078, 5137, 5138, 5139, 5141, 5142, 5147, 5153, 5154, 5155, 5165, 5168, 5182, 5183, 5184, 5185, 5447, 5448, 5451, 5452, 5455, 5457, 5458, 5461, 5463, 5464, 5468, 5471, 5499, 5500, 5501, 5504, 5505, 5509, 5511, 5512, 5513, 5514, 5518, 5521, 5522, 5526, 5529, 5533, 5573, 5575, 5576, 5579, 5593, 5602, 5610, 5659, 5660, 5661, 5764, 5772, 5773, 5774, 5775, 5776, 5777, 5778, 5779, 5780, 5781, 5782, 5786, 5787, 5789, 5795, 5798, 5840, 5841, 5842, 5843, 5845, 5852, 5859, 5869, 5870, 5871, 5872, 5873, 5880, 5887, 5897, 5898, 5899, 5900, 5901, 5908, 5915, 6002, 6006, 6070, 6102, 6103, 6104, 6106, 6107, 6110, 6111, 6112, 6115, 6116, 6117, 6118, 6119, 6120, 6121, 6122, 6123, 6124, 6125, 6128, 6129, 6130, 6131, 6132, 6133, 6134, 6135, 6136, 6137, 6138, 6141, 6142, 6143, 6144, 6145, 6146, 6147, 6148, 6149, 6150, 6151, 6152, 6154, 6155, 6157, 6261, 6711, 6743, 6754, 6758, 6767, 6768, 6769, 6772, 6800, 6801, 6802, 6804, 6805, 6809, 6810, 6811, 6813, 6817, 6821, 6822, 6824, 6830, 6831, 6832, 6833, 6840, 6841, 6842, 6843, 6844, 6847, 6851, 6862, 6863, 6864, 6891, 6895, 6899, 6941, 6942, 6967, 6968, 6978, 6979, 6982, 6985, 6986, 6987, 6989, 6990, 6991, 6992, 6993, 7001, 7002, 7003, 7004, 7005, 7006, 7007, 7008, 7009, 7010, 7146, 7147, 7148, 7265, 7267, 7269, 7272, 7277, 7278, 7280, 7281, 7282, 7284, 7285, 7286, 7315, 7316, 7317, 7318, 7319, 7320, 7321, 7322, 7323, 7361, 7363, 7366, 7372, 7373, 7375, 7414, 7448, 7449, 7454, 7458, 7476, 7484, 7487, 7489, 7526, 7556, 7572, 7593, 7594, 7598, 7645, 7648, 7649, 7654, 7656, 7657, 7658, 7659, 7664, 7666, 7669, 7670, 7671, 7672, 7673, 7676, 7677, 7682, 7683, 7684, 7690, 7692, 7700, 7701, 7702, 7704, 7707, 7708, 7709, 7710, 7711, 7712, 7713, 7716, 7717, 7720, 7721, 7722, 7723, 7726, 7731, 7738, 7740, 7746, 7747, 7748, 7749, 7751, 7753, 7759, 7760, 7761, 7762, 7763, 7765, 7766, 7775, 7776, 7781, 7784, 7786, 7787, 7788, 7789, 7794, 7796, 7803, 7854, 7855, 7856, 7857, 7860, 7861, 7862, 7864, 7872, 7875, 7876, 7877, 7882, 7883, 7885, 7886, 7887, 7888, 7889, 7890, 7894, 7895, 7896, 7900, 7901, 7902, 7903, 7904, 7907, 7908, 7909, 7911, 7912, 7913, 7915, 7920, 7922, 7923, 7924, 7925, 7986, 7987, 7988, 7989, 7991, 7992, 7993, 7995, 8003, 8008, 8009, 8010, 8011, 8012, 8013, 8014, 8015, 8016, 8017, 8018, 8019, 8020, 8021, 8022, 8031, 8035, 8036, 8037, 8038, 8045, 8046, 8047, 8048, 8049, 8133, 8139, 8140, 8141, 8142, 8143, 8144, 8145, 8146, 8147, 8148, 8149, 8150, 8155, 8156, 8161, 8162, 8163, 8164, 8165, 8167, 8199, 8200, 8204, 8230, 8234, 8235, 8254, 8279, 8311, 8312, 8327, 8328, 8331, 8347, 8348, 8349, 8350, 8351, 8352, 8353, 8355, 8359, 8365, 8368, 8369, 8372, 8373, 8374, 8377, 8378, 8379, 8380, 8383, 8384, 8385, 8387, 8393, 8396, 8397, 8399, 8496, 8497, 8500, 8501, 8502, 8503, 8504, 8505, 8552, 8562, 8564, 8565, 8567, 8568, 8578, 8625, 8650], "excluded_lines": [17, 18, 24], "executed_branches": [[208, 210], [211, 221], [221, 222], [223, 237], [273, 274], [273, 288], [275, 276], [275, 277], [279, 280], [279, 285], [280, 284], [285, 273], [289, 290], [289, 309], [290, 292], [293, 304], [305, 289], [309, 315], [444, 438], [452, 455], [499, 510], [511, 513], [557, 558], [695, 696], [695, 698], [702, 703], [702, 704], [759, 760], [759, 761], [882, 883], [882, 885], [903, 904], [903, 905], [905, 907], [907, 908], [907, 910], [931, 932], [931, 938], [938, 939], [938, 946], [943, -912], [943, 944], [946, -912], [946, 947], [963, 964], [963, 971], [966, 967], [971, 972], [971, 977], [973, 974], [977, -951], [977, 978], [979, 980], [1002, 1003], [1002, 1006], [1010, 1011], [1010, 1021], [1022, 1023], [1022, 1032], [1025, 1026], [1033, 1034], [1033, 1037], [1038, 1039], [1038, 1043], [1044, 1045], [1044, 1057], [1045, 1046], [1047, 1048], [1047, 1050], [1050, 1051], [1050, 1057], [1052, 1053], [1057, 1058], [1057, 1064], [1059, 1060], [1059, 1064], [1065, 1066], [1065, 1070], [1070, 1071], [1070, 1073], [1073, 1074], [1073, 1078], [1078, 1079], [1078, 1084], [1080, 1081], [1084, 1085], [1084, 1091], [1086, 1087], [1092, 1093], [1092, 1099], [1100, -983], [1100, 1101], [1127, 1128], [1127, 1130], [1130, 1131], [1130, 1133], [1133, 1134], [1133, 1136], [1136, 1137], [1136, 1139], [1139, 1140], [1139, 1142], [1142, 1143], [1142, 1145], [1145, 1146], [1145, 1153], [1153, 1154], [1153, 1156], [1156, 1157], [1156, 1159], [1159, 1160], [1159, 1169], [1161, 1162], [1161, 1163], [1163, 1164], [1163, 1165], [1165, 1166], [1165, 1167], [1347, 1359], [1359, 1368], [1427, 1429], [1480, 1481], [1480, 1484], [1486, 1538], [1538, 1544], [1605, 1606], [1605, 1625], [1608, 1609], [1608, 1610], [1625, 1626], [1625, 1631], [1651, 1652], [1651, 1657], [1663, 1664], [1663, 1674], [1668, 1663], [1668, 1669], [1669, 1663], [1669, 1670], [1670, 1671], [1674, 1675], [1674, 1710], [1680, 1682], [1683, 1684], [1683, 1685], [1710, 1711], [1710, 1716], [1784, 1785], [1784, 1789], [1789, 1790], [1809, 1810], [1809, 1814], [1815, 1829], [1829, 1830], [1829, 1900], [1851, 1856], [1851, 1888], [2064, 2067], [2105, 2127], [2141, 2179], [2546, 2547], [2546, 2556], [2557, 2565], [2566, 2589], [2590, 2591], [2590, 2599], [2594, 2595], [2594, 2596], [2600, 2601], [2600, 2616], [2602, 2603], [2602, 2611], [2667, 2668], [2667, 2670], [2796, 2805], [2806, 2811], [2811, 2813], [2811, 2822], [2824, 2831], [2832, 2845], [2846, 2864], [2865, 2866], [2865, 2874], [2869, 2870], [2869, 2871], [2875, 2876], [2875, 2889], [2877, 2878], [2877, 2883], [2890, 2915], [2915, 2964], [3362, 3363], [3367, 3368], [3367, 3377], [3570, 3575], [3570, 3580], [3575, 3578], [3655, 3667], [3667, 3675], [3684, 3704], [3684, 3861], [3704, 3713], [3720, 3723], [3720, 3861], [3723, 3731], [3723, 3861], [3751, 3752], [3758, 3769], [3769, 3778], [3778, 3816], [3816, 3822], [3825, 3857], [3861, 3869], [3932, 3934], [4170, 4171], [4170, 4251], [4183, 4189], [4190, 4191], [4190, 4198], [4208, 4209], [4208, 4215], [4210, 4208], [4221, 4222], [4221, 4229], [4230, 4231], [4230, 4234], [4235, 4240], [4253, 4254], [4253, 4330], [4279, 4305], [4315, 4316], [4315, 4322], [4322, 4323], [4322, 4330], [4330, 4331], [4330, 4361], [4333, 4334], [4333, 4336], [4336, 4337], [4336, 4339], [4339, 4340], [4339, 4361], [4344, 4345], [4344, 4346], [4346, 4347], [4363, 4370], [4370, 4371], [4370, 4418], [4371, 4370], [4418, 4419], [4418, 4475], [4433, 4434], [4439, 4446], [4446, 4475], [4493, -4120], [4493, 4494], [4501, 4502], [4501, 4505], [4505, 4506], [4505, 4510], [4510, 4515], [4515, 4516], [4515, 4527], [4536, 4537], [4547, 4548], [4564, 4570], [4570, 4571], [4617, 4623], [4623, 4624], [4664, -4645], [4664, 4665], [4699, 4700], [4699, 4705], [4712, 4713], [4712, 4722], [4761, 4762], [4773, 4774], [4773, 4782], [4816, 4817], [4816, 4823], [4817, 4818], [4817, 4820], [4820, 4821], [4835, 4836], [4928, 4929], [4928, 4939], [4929, 4930], [4929, 4934], [4943, 4944], [4985, 4986], [4985, 4999], [4990, 4985], [4990, 4991], [5031, 5032], [5031, 5040], [5032, 5033], [5032, 5034], [5034, 5031], [5034, 5035], [5040, -5019], [5040, 5041], [5042, 5043], [5042, 5044], [5044, 5045], [5044, 5046], [5060, 5061], [5060, 5070], [5061, 5063], [5063, 5060], [5070, 5071], [5070, 5075], [5075, -5048], [5075, 5076], [5077, 5079], [5079, 5080], [5133, 5134], [5133, 5135], [5135, 5136], [5261, 5262], [5261, 5283], [5268, 5269], [5268, 5286], [5276, 5277], [5276, 5279], [5304, 5305], [5304, 5308], [5404, 5405], [5404, 5408], [5477, 5478], [5477, 5480], [5560, 5561], [5560, 5567], [5590, 5591], [5601, 5605], [5609, 5612], [5648, 5649], [5648, 5655], [5763, 5803], [5819, 5820], [5962, 5963], [5962, 5965], [5995, 5996], [5995, 6000], [6001, 6005], [6005, 6008], [6069, 6073], [6073, 6074], [6073, 6077], [6077, 6078], [6077, 6081], [6218, 6219], [6218, 6225], [6226, 6227], [6226, 6234], [6235, 6236], [6235, 6246], [6247, 6248], [6247, 6260], [6260, 6263], [6310, 6311], [6310, 6314], [6318, 6319], [6318, 6322], [6326, 6327], [6326, 6332], [6328, 6329], [6328, 6332], [6332, 6333], [6332, 6339], [6334, 6335], [6334, 6339], [6339, 6340], [6339, 6342], [6385, 6386], [6385, 6393], [6393, 6394], [6393, 6402], [6624, 6625], [6624, 6629], [6647, 6648], [6707, 6718], [6727, 6736], [6727, 6888], [6736, 6737], [6736, 6888], [6742, 6745], [6745, 6750], [6745, 6865], [6750, 6751], [6750, 6777], [6752, 6777], [6779, 6780], [6781, 6782], [6781, 6792], [6797, 6736], [6797, 6798], [6799, 6837], [6837, 6797], [6865, 6866], [6874, 6875], [6874, 6881], [6888, 6889], [6894, 6905], [6940, 6943], [6966, 6969], [7040, 7041], [7040, 7044], [7046, 7047], [7046, 7049], [7050, 7051], [7050, 7054], [7054, 7055], [7054, 7057], [7114, 7115], [7114, 7118], [7123, 7124], [7125, 7126], [7130, 7131], [7130, 7137], [7139, 7140], [7139, 7143], [7173, 7174], [7173, 7189], [7184, 7185], [7184, 7189], [7186, 7187], [7311, 7312], [7412, 7413], [7412, 7416], [7413, 7412], [7456, 7457], [7471, 7478], [7480, 7481], [7480, 7495], [7481, 7482], [7481, 7483], [7483, 7485], [7486, 7488], [7488, 7490], [7523, 7524], [7525, 7527], [7537, 7538], [7537, 7552], [7553, 7554], [7553, 7565], [7555, 7557], [7852, 7853], [7984, 7985], [8132, 8135], [8136, 8137], [8219, 8228], [8229, 8277], [8278, 8296], [8494, 8508], [8551, 8555], [8556, 8557], [8556, 8560], [8561, 8576], [8577, 8583], [8624, 8626], [8649, 8659], [8767, 8768], [8767, 8771], [8772, 8773], [8772, 8776], [8777, 8778], [8777, 8781], [8782, 8783], [8782, 8784], [8784, 8785], [8784, 8787], [8822, 8823], [8822, 8828], [8833, -8789], [8833, 8835], [8868, 8869], [8868, 8874], [8870, 8868], [8870, 8871]], "missing_branches": [[208, 209], [211, 212], [221, 237], [223, 224], [280, 281], [285, 286], [290, 291], [293, 294], [296, 297], [296, 302], [297, 298], [297, 301], [302, 303], [302, 304], [305, 306], [309, 310], [366, 367], [366, 386], [368, 369], [368, 372], [370, 366], [370, 371], [372, 366], [372, 373], [376, 366], [376, 377], [378, 366], [378, 379], [444, 445], [452, 453], [499, 500], [511, 512], [557, 559], [582, 583], [582, 584], [905, 906], [966, 971], [973, 971], [979, 977], [1025, 1028], [1045, 1050], [1052, 1057], [1080, 1078], [1086, 1084], [1347, 1348], [1359, 1360], [1398, 1399], [1398, 1400], [1403, -1384], [1403, 1404], [1427, 1428], [1460, 1461], [1460, 1462], [1486, 1487], [1487, 1488], [1487, 1489], [1490, 1491], [1490, 1493], [1502, 1503], [1502, 1508], [1503, 1504], [1503, 1505], [1505, 1502], [1505, 1506], [1508, 1509], [1508, 1514], [1514, 1515], [1514, 1518], [1518, 1486], [1518, 1519], [1538, 1539], [1562, 1563], [1562, 1578], [1567, 1568], [1567, 1577], [1568, 1567], [1568, 1569], [1570, 1571], [1570, 1572], [1572, 1573], [1572, 1574], [1670, 1669], [1680, 1681], [1789, 1794], [1815, 1816], [1969, 1970], [1969, 1973], [2064, 2065], [2105, 2108], [2141, 2145], [2382, 2383], [2382, 2384], [2396, 2397], [2396, 2398], [2398, 2399], [2398, 2405], [2443, 2444], [2443, 2448], [2449, 2453], [2449, 2454], [2455, 2456], [2455, 2459], [2459, 2460], [2459, 2467], [2468, 2469], [2468, 2480], [2476, 2477], [2476, 2478], [2557, 2558], [2566, 2567], [2681, 2682], [2681, 2683], [2684, 2685], [2684, 2695], [2690, 2691], [2690, 2692], [2692, 2693], [2692, 2694], [2706, 2707], [2706, 2708], [2719, 2720], [2719, 2721], [2722, 2723], [2722, 2726], [2723, 2722], [2723, 2724], [2796, 2797], [2806, 2808], [2824, 2825], [2832, 2833], [2846, 2849], [2890, 2891], [2915, 2922], [2922, 2923], [2922, 2933], [3087, 3088], [3087, 3089], [3140, 3141], [3140, 3157], [3142, 3143], [3142, 3147], [3148, 3149], [3148, 3157], [3158, 3159], [3158, 3177], [3160, 3164], [3160, 3177], [3229, 3233], [3229, 3245], [3362, 3373], [3575, 3576], [3627, 3625], [3627, 3631], [3655, 3656], [3667, 3668], [3704, 3705], [3751, 3754], [3758, 3759], [3769, 3770], [3770, 3771], [3770, 3778], [3778, 3779], [3780, 3781], [3780, 3793], [3793, 3794], [3793, 3816], [3795, 3796], [3795, 3816], [3796, 3797], [3796, 3798], [3816, 3723], [3825, 3826], [3853, 3854], [3853, 3857], [3854, 3853], [3854, 3855], [3861, 3862], [3932, 3933], [4058, 4059], [4058, 4061], [4063, 4064], [4063, 4066], [4183, 4184], [4210, 4211], [4212, 4208], [4212, 4213], [4235, 4236], [4279, 4280], [4291, 4292], [4291, 4305], [4346, 4350], [4363, 4364], [4367, 4368], [4367, 4370], [4371, 4372], [4378, 4379], [4378, 4386], [4386, 4387], [4386, 4396], [4388, 4389], [4388, 4396], [4396, 4397], [4396, 4401], [4398, 4399], [4398, 4401], [4401, 4402], [4401, 4406], [4433, 4439], [4439, 4440], [4446, 4447], [4454, 4455], [4454, 4475], [4510, 4511], [4536, 4546], [4547, 4563], [4564, 4567], [4570, -4120], [4617, 4618], [4623, 4630], [4630, 4631], [4630, 4639], [4761, 4782], [4820, 4816], [4835, 4837], [4839, 4840], [4839, 4841], [4858, 4859], [4858, 4865], [4943, 4948], [5061, 5062], [5063, 5064], [5077, 5078], [5079, 5081], [5135, 5137], [5138, 5139], [5138, 5141], [5451, 5452], [5451, 5457], [5457, 5458], [5457, 5463], [5463, 5464], [5463, 5471], [5504, 5505], [5504, 5511], [5521, 5522], [5521, 5529], [5590, 5593], [5601, 5602], [5609, 5610], [5763, 5764], [5775, 5776], [5775, 5789], [5819, 5822], [6001, 6002], [6005, 6006], [6069, 6070], [6110, 6111], [6110, 6115], [6116, 6117], [6116, 6128], [6119, 6120], [6119, 6128], [6121, 6122], [6121, 6123], [6123, 6124], [6123, 6125], [6129, 6130], [6129, 6141], [6132, 6133], [6132, 6141], [6134, 6135], [6134, 6136], [6136, 6137], [6136, 6138], [6142, 6143], [6142, 6154], [6145, 6146], [6145, 6148], [6148, 6149], [6148, 6150], [6150, 6151], [6150, 6152], [6260, 6261], [6647, 6894], [6707, 6711], [6742, 6743], [6752, 6754], [6754, 6758], [6754, 6769], [6779, 6792], [6799, 6800], [6804, 6805], [6804, 6809], [6809, 6810], [6809, 6830], [6811, 6813], [6811, 6824], [6821, 6797], [6821, 6822], [6830, 6797], [6830, 6831], [6832, 6797], [6832, 6833], [6837, 6840], [6841, 6842], [6841, 6862], [6863, 6797], [6863, 6864], [6865, 6736], [6888, 6891], [6894, 6895], [6940, 6941], [6966, 6967], [6985, 6986], [6985, 6989], [6989, 6990], [6989, 7001], [6991, 6992], [6991, 6993], [7006, 7007], [7006, 7009], [7123, 7143], [7125, 7143], [7186, 7184], [7311, 7315], [7413, 7414], [7456, 7458], [7471, 7476], [7483, 7484], [7486, 7487], [7488, 7489], [7523, 7527], [7525, 7526], [7555, 7556], [7648, 7649], [7648, 7656], [7671, 7672], [7671, 7692], [7676, 7677], [7676, 7700], [7701, 7702], [7701, 7704], [7708, 7709], [7708, 7720], [7709, 7710], [7709, 7711], [7713, 7716], [7713, 7717], [7721, 7722], [7721, 7765], [7723, 7726], [7723, 7740], [7746, 7747], [7746, 7748], [7748, 7749], [7748, 7751], [7759, 7760], [7759, 7761], [7761, 7762], [7761, 7763], [7852, 7854], [7860, 7861], [7860, 7864], [7876, 7877], [7876, 7885], [7882, 7876], [7882, 7883], [7886, 7887], [7886, 7925], [7887, 7886], [7887, 7888], [7889, 7890], [7889, 7894], [7894, 7895], [7894, 7896], [7900, 7901], [7900, 7907], [7902, 7900], [7902, 7903], [7908, 7909], [7908, 7911], [7912, 7913], [7912, 7915], [7915, 7920], [7915, 7922], [7922, 7923], [7922, 7924], [7984, 7986], [7991, 7992], [7991, 7995], [8008, 8009], [8008, 8010], [8016, 8017], [8016, 8031], [8017, 8018], [8017, 8019], [8019, 8020], [8019, 8021], [8036, 8037], [8036, 8049], [8037, 8038], [8037, 8045], [8045, 8046], [8045, 8047], [8047, 8036], [8047, 8048], [8132, 8133], [8136, 8139], [8139, 8140], [8139, 8167], [8140, 8141], [8140, 8142], [8142, 8143], [8142, 8144], [8144, 8145], [8144, 8146], [8146, 8147], [8146, 8148], [8149, 8150], [8149, 8155], [8155, 8156], [8155, 8165], [8162, 8163], [8162, 8164], [8219, 8311], [8229, 8230], [8234, 8235], [8234, 8254], [8278, 8279], [8311, 8312], [8311, 8327], [8328, 8331], [8328, 8347], [8355, 8359], [8355, 8387], [8359, 8365], [8359, 8368], [8368, 8369], [8368, 8372], [8372, 8373], [8372, 8374], [8374, 8377], [8374, 8378], [8378, 8379], [8378, 8380], [8380, 8383], [8380, 8384], [8384, 8355], [8384, 8385], [8494, 8496], [8496, 8497], [8496, 8500], [8500, 8501], [8500, 8502], [8502, 8503], [8502, 8504], [8504, 8505], [8504, 8508], [8551, 8552], [8561, 8562], [8564, 8565], [8564, 8567], [8567, 8568], [8567, 8576], [8577, 8578], [8624, 8625], [8649, 8650]], "functions": {"_is_orchestrator_managed_path": {"executed_lines": [208, 210, 211, 221, 222, 223, 237], "summary": {"covered_lines": 7, "num_statements": 15, "percent_covered": 47.82608695652174, "percent_covered_display": "48", "missing_lines": 8, "excluded_lines": 0, "percent_statements_covered": 46.666666666666664, "percent_statements_covered_display": "47", "num_branches": 8, "num_partial_branches": 4, "covered_branches": 4, "missing_branches": 4, "percent_branches_covered": 50.0, "percent_branches_covered_display": "50"}, "missing_lines": [209, 212, 224, 225, 226, 227, 230, 235], "excluded_lines": [], "start_line": 182, "executed_branches": [[208, 210], [211, 221], [221, 222], [223, 237]], "missing_branches": [[208, 209], [211, 212], [221, 237], [223, 224]]}, "_strip_orchestrator_managed_paths": {"executed_lines": [271, 273, 274, 275, 276, 277, 278, 279, 280, 284, 285, 288, 289, 290, 292, 293, 304, 305, 309, 315], "summary": {"covered_lines": 20, "num_statements": 36, "percent_covered": 54.83870967741935, "percent_covered_display": "55", "missing_lines": 16, "excluded_lines": 0, "percent_statements_covered": 55.55555555555556, "percent_statements_covered_display": "56", "num_branches": 26, "num_partial_branches": 6, "covered_branches": 14, "missing_branches": 12, "percent_branches_covered": 53.84615384615385, "percent_branches_covered_display": "54"}, "missing_lines": [281, 282, 286, 291, 294, 295, 296, 297, 298, 299, 301, 302, 303, 306, 307, 310], "excluded_lines": [], "start_line": 240, "executed_branches": [[273, 274], [273, 288], [275, 276], [275, 277], [279, 280], [279, 285], [280, 284], [285, 273], [289, 290], [289, 309], [290, 292], [293, 304], [305, 289], [309, 315]], "missing_branches": [[280, 281], [285, 286], [290, 291], [293, 294], [296, 297], [296, 302], [297, 298], [297, 301], [302, 303], [302, 304], [305, 306], [309, 310]]}, "_extract_partial_from_messages": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 20, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 20, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 12, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 12, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [362, 363, 364, 366, 367, 368, 369, 370, 371, 372, 373, 374, 375, 376, 377, 378, 379, 382, 384, 386], "excluded_lines": [], "start_line": 323, "executed_branches": [], "missing_branches": [[366, 367], [366, 386], [368, 369], [368, 372], [370, 366], [370, 371], [372, 366], [372, 373], [376, 366], [376, 377], [378, 366], [378, 379]]}, "async_heartbeat": {"executed_lines": [432, 434, 436, 452, 455, 456, 457, 459, 460, 461], "summary": {"covered_lines": 10, "num_statements": 11, "percent_covered": 84.61538461538461, "percent_covered_display": "85", "missing_lines": 1, "excluded_lines": 0, "percent_statements_covered": 90.9090909090909, "percent_statements_covered_display": "91", "num_branches": 2, "num_partial_branches": 1, "covered_branches": 1, "missing_branches": 1, "percent_branches_covered": 50.0, "percent_branches_covered_display": "50"}, "missing_lines": [453], "excluded_lines": [], "start_line": 401, "executed_branches": [[452, 455]], "missing_branches": [[452, 453]]}, "async_heartbeat.heartbeat": {"executed_lines": [437, 438, 439, 440, 441, 444], "summary": {"covered_lines": 6, "num_statements": 7, "percent_covered": 77.77777777777777, "percent_covered_display": "78", "missing_lines": 1, "excluded_lines": 0, "percent_statements_covered": 85.71428571428571, "percent_statements_covered_display": "86", "num_branches": 2, "num_partial_branches": 1, "covered_branches": 1, "missing_branches": 1, "percent_branches_covered": 50.0, "percent_branches_covered_display": "50"}, "missing_lines": [445], "excluded_lines": [], "start_line": 436, "executed_branches": [[444, 438]], "missing_branches": [[444, 445]]}, "detect_timeout_multiplier": {"executed_lines": [498, 499, 510, 511, 513], "summary": {"covered_lines": 5, "num_statements": 11, "percent_covered": 46.666666666666664, "percent_covered_display": "47", "missing_lines": 6, "excluded_lines": 0, "percent_statements_covered": 45.45454545454545, "percent_statements_covered_display": "45", "num_branches": 4, "num_partial_branches": 2, "covered_branches": 2, "missing_branches": 2, "percent_branches_covered": 50.0, "percent_branches_covered_display": "50"}, "missing_lines": [500, 501, 502, 503, 504, 512], "excluded_lines": [], "start_line": 486, "executed_branches": [[499, 510], [511, 513]], "missing_branches": [[499, 500], [511, 512]]}, "_coach_synthesis_enabled": {"executed_lines": [556, 557, 558], "summary": {"covered_lines": 3, "num_statements": 4, "percent_covered": 66.66666666666667, "percent_covered_display": "67", "missing_lines": 1, "excluded_lines": 0, "percent_statements_covered": 75.0, "percent_statements_covered_display": "75", "num_branches": 2, "num_partial_branches": 1, "covered_branches": 1, "missing_branches": 1, "percent_branches_covered": 50.0, "percent_branches_covered_display": "50"}, "missing_lines": [559], "excluded_lines": [], "start_line": 549, "executed_branches": [[557, 558]], "missing_branches": [[557, 559]]}, "_coach_gather_enabled": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 4, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 4, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 2, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 2, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [581, 582, 583, 584], "excluded_lines": [], "start_line": 574, "executed_branches": [], "missing_branches": [[582, 583], [582, 584]]}, "_install_sdk_cleanup_handler": {"executed_lines": [695, 696, 698, 706, 707], "summary": {"covered_lines": 5, "num_statements": 5, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 2, "num_partial_branches": 0, "covered_branches": 2, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 688, "executed_branches": [[695, 696], [695, 698]], "missing_branches": []}, "_install_sdk_cleanup_handler.handler": {"executed_lines": [699, 700, 701, 702, 703, 704], "summary": {"covered_lines": 6, "num_statements": 6, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 2, "num_partial_branches": 0, "covered_branches": 2, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 698, "executed_branches": [[702, 703], [702, 704]], "missing_branches": []}, "_is_doc_level_excluded": {"executed_lines": [759, 760, 761], "summary": {"covered_lines": 3, "num_statements": 3, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 2, "num_partial_branches": 0, "covered_branches": 2, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 752, "executed_branches": [[759, 760], [759, 761]], "missing_branches": []}, "TaskWorkStreamParser.__init__": {"executed_lines": [832, 833, 834, 835, 836, 837, 838, 846, 847, 848, 849, 850, 851], "summary": {"covered_lines": 13, "num_statements": 13, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 0, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 830, "executed_branches": [], "missing_branches": []}, "TaskWorkStreamParser._match_pattern": {"executed_lines": [867], "summary": {"covered_lines": 1, "num_statements": 1, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 0, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 853, "executed_branches": [], "missing_branches": []}, "TaskWorkStreamParser._is_test_file": {"executed_lines": [882, 883, 885, 886, 887], "summary": {"covered_lines": 5, "num_statements": 5, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 2, "num_partial_branches": 0, "covered_branches": 2, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 869, "executed_branches": [[882, 883], [882, 885]], "missing_branches": []}, "TaskWorkStreamParser._is_valid_file_path": {"executed_lines": [903, 904, 905, 907, 908, 910], "summary": {"covered_lines": 6, "num_statements": 7, "percent_covered": 84.61538461538461, "percent_covered_display": "85", "missing_lines": 1, "excluded_lines": 0, "percent_statements_covered": 85.71428571428571, "percent_statements_covered_display": "86", "num_branches": 6, "num_partial_branches": 1, "covered_branches": 5, "missing_branches": 1, "percent_branches_covered": 83.33333333333333, "percent_branches_covered_display": "83"}, "missing_lines": [906], "excluded_lines": [], "start_line": 890, "executed_branches": [[903, 904], [903, 905], [905, 907], [907, 908], [907, 910]], "missing_branches": [[905, 906]]}, "TaskWorkStreamParser._track_tool_call": {"executed_lines": [925, 931, 932, 936, 938, 939, 940, 941, 943, 944, 945, 946, 947, 948, 949], "summary": {"covered_lines": 15, "num_statements": 15, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 8, "num_partial_branches": 0, "covered_branches": 8, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 912, "executed_branches": [[931, 932], [931, 938], [938, 939], [938, 946], [943, -912], [943, 944], [946, -912], [946, 947]], "missing_branches": []}, "TaskWorkStreamParser._parse_tool_invocations": {"executed_lines": [962, 963, 964, 965, 966, 967, 968, 971, 972, 973, 974, 975, 977, 978, 979, 980, 981], "summary": {"covered_lines": 17, "num_statements": 17, "percent_covered": 89.65517241379311, "percent_covered_display": "90", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 12, "num_partial_branches": 3, "covered_branches": 9, "missing_branches": 3, "percent_branches_covered": 75.0, "percent_branches_covered_display": "75"}, "missing_lines": [], "excluded_lines": [], "start_line": 951, "executed_branches": [[963, 964], [963, 971], [966, 967], [971, 972], [971, 977], [973, 974], [977, -951], [977, 978], [979, 980]], "missing_branches": [[966, 971], [973, 971], [979, 977]]}, "TaskWorkStreamParser.parse_message": {"executed_lines": [1002, 1003, 1006, 1009, 1010, 1011, 1012, 1013, 1018, 1021, 1022, 1023, 1024, 1025, 1026, 1029, 1032, 1033, 1034, 1035, 1037, 1038, 1039, 1040, 1043, 1044, 1045, 1046, 1047, 1048, 1049, 1050, 1051, 1052, 1053, 1054, 1057, 1058, 1059, 1060, 1061, 1064, 1065, 1066, 1067, 1070, 1071, 1072, 1073, 1074, 1075, 1078, 1079, 1080, 1081, 1082, 1084, 1085, 1086, 1087, 1088, 1091, 1092, 1093, 1094, 1095, 1099, 1100, 1101, 1102, 1103, 1104, 1105], "summary": {"covered_lines": 73, "num_statements": 78, "percent_covered": 91.80327868852459, "percent_covered_display": "92", "missing_lines": 5, "excluded_lines": 0, "percent_statements_covered": 93.58974358974359, "percent_statements_covered_display": "94", "num_branches": 44, "num_partial_branches": 5, "covered_branches": 39, "missing_branches": 5, "percent_branches_covered": 88.63636363636364, "percent_branches_covered_display": "89"}, "missing_lines": [1028, 1096, 1097, 1106, 1107], "excluded_lines": [], "start_line": 983, "executed_branches": [[1002, 1003], [1002, 1006], [1010, 1011], [1010, 1021], [1022, 1023], [1022, 1032], [1025, 1026], [1033, 1034], [1033, 1037], [1038, 1039], [1038, 1043], [1044, 1045], [1044, 1057], [1045, 1046], [1047, 1048], [1047, 1050], [1050, 1051], [1050, 1057], [1052, 1053], [1057, 1058], [1057, 1064], [1059, 1060], [1059, 1064], [1065, 1066], [1065, 1070], [1070, 1071], [1070, 1073], [1073, 1074], [1073, 1078], [1078, 1079], [1078, 1084], [1080, 1081], [1084, 1085], [1084, 1091], [1086, 1087], [1092, 1093], [1092, 1099], [1100, -983], [1100, 1101]], "missing_branches": [[1025, 1028], [1045, 1050], [1052, 1057], [1080, 1078], [1086, 1084]]}, "TaskWorkStreamParser.to_result": {"executed_lines": [1125, 1127, 1128, 1130, 1131, 1133, 1134, 1136, 1137, 1139, 1140, 1142, 1143, 1145, 1146, 1153, 1154, 1156, 1157, 1159, 1160, 1161, 1162, 1163, 1164, 1165, 1166, 1167, 1169], "summary": {"covered_lines": 29, "num_statements": 29, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 26, "num_partial_branches": 0, "covered_branches": 26, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 1109, "executed_branches": [[1127, 1128], [1127, 1130], [1130, 1131], [1130, 1133], [1133, 1134], [1133, 1136], [1136, 1137], [1136, 1139], [1139, 1140], [1139, 1142], [1142, 1143], [1142, 1145], [1145, 1146], [1145, 1153], [1153, 1154], [1153, 1156], [1156, 1157], [1156, 1159], [1159, 1160], [1159, 1169], [1161, 1162], [1161, 1163], [1163, 1164], [1163, 1165], [1165, 1166], [1165, 1167]], "missing_branches": []}, "TaskWorkStreamParser.reset": {"executed_lines": [1177, 1178, 1179, 1180, 1181, 1182, 1183, 1184, 1185, 1186, 1187, 1188, 1189], "summary": {"covered_lines": 13, "num_statements": 13, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 0, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 1171, "executed_branches": [], "missing_branches": []}, "AgentInvoker.__init__": {"executed_lines": [1295, 1296, 1297, 1298, 1299, 1300, 1304, 1308, 1309, 1316, 1317, 1319, 1321, 1323, 1325, 1334, 1345, 1347, 1359, 1368], "summary": {"covered_lines": 20, "num_statements": 23, "percent_covered": 81.48148148148148, "percent_covered_display": "81", "missing_lines": 3, "excluded_lines": 0, "percent_statements_covered": 86.95652173913044, "percent_statements_covered_display": "87", "num_branches": 4, "num_partial_branches": 2, "covered_branches": 2, "missing_branches": 2, "percent_branches_covered": 50.0, "percent_branches_covered_display": "50"}, "missing_lines": [1348, 1360, 1361], "excluded_lines": [], "start_line": 1250, "executed_branches": [[1347, 1359], [1359, 1368]], "missing_branches": [[1347, 1348], [1359, 1360]]}, "AgentInvoker.set_progress_logger": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 1, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 1, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 0, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [1382], "excluded_lines": [], "start_line": 1374, "executed_branches": [], "missing_branches": []}, "AgentInvoker._track_tool_use": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 9, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 9, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 4, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 4, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [1398, 1399, 1400, 1401, 1402, 1403, 1404, 1405, 1406], "excluded_lines": [], "start_line": 1384, "executed_branches": [], "missing_branches": [[1398, 1399], [1398, 1400], [1403, -1384], [1403, 1404]]}, "AgentInvoker._resolve_repo_root": {"executed_lines": [1424, 1425, 1426, 1427, 1429], "summary": {"covered_lines": 5, "num_statements": 6, "percent_covered": 75.0, "percent_covered_display": "75", "missing_lines": 1, "excluded_lines": 0, "percent_statements_covered": 83.33333333333333, "percent_statements_covered_display": "83", "num_branches": 2, "num_partial_branches": 1, "covered_branches": 1, "missing_branches": 1, "percent_branches_covered": 50.0, "percent_branches_covered_display": "50"}, "missing_lines": [1428], "excluded_lines": [], "start_line": 1412, "executed_branches": [[1427, 1429]], "missing_branches": [[1427, 1428]]}, "AgentInvoker.set_player_resume_session": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 1, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 1, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 0, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [1444], "excluded_lines": [], "start_line": 1435, "executed_branches": [], "missing_branches": []}, "AgentInvoker.cancel": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 3, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 3, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 2, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 2, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [1460, 1461, 1462], "excluded_lines": [], "start_line": 1450, "executed_branches": [], "missing_branches": [[1460, 1461], [1460, 1462]]}, "AgentInvoker._kill_child_claude_processes": {"executed_lines": [1477, 1478, 1480, 1481, 1482, 1484, 1485, 1486, 1538, 1544], "summary": {"covered_lines": 10, "num_statements": 43, "percent_covered": 21.53846153846154, "percent_covered_display": "22", "missing_lines": 33, "excluded_lines": 0, "percent_statements_covered": 23.25581395348837, "percent_statements_covered_display": "23", "num_branches": 22, "num_partial_branches": 2, "covered_branches": 4, "missing_branches": 18, "percent_branches_covered": 18.181818181818183, "percent_branches_covered_display": "18"}, "missing_lines": [1487, 1488, 1489, 1490, 1491, 1493, 1494, 1495, 1496, 1497, 1500, 1501, 1502, 1503, 1504, 1505, 1506, 1508, 1509, 1514, 1515, 1518, 1519, 1520, 1521, 1522, 1526, 1527, 1530, 1531, 1535, 1536, 1539], "excluded_lines": [], "start_line": 1464, "executed_branches": [[1480, 1481], [1480, 1484], [1486, 1538], [1538, 1544]], "missing_branches": [[1486, 1487], [1487, 1488], [1487, 1489], [1490, 1491], [1490, 1493], [1502, 1503], [1502, 1508], [1503, 1504], [1503, 1505], [1505, 1502], [1505, 1506], [1508, 1509], [1508, 1514], [1514, 1515], [1514, 1518], [1518, 1486], [1518, 1519], [1538, 1539]]}, "AgentInvoker._is_descendant_of": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 17, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 17, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 10, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 10, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [1561, 1562, 1563, 1564, 1565, 1566, 1567, 1568, 1569, 1570, 1571, 1572, 1573, 1574, 1575, 1577, 1578], "excluded_lines": [], "start_line": 1547, "executed_branches": [], "missing_branches": [[1562, 1563], [1562, 1578], [1567, 1568], [1567, 1577], [1568, 1567], [1568, 1569], [1570, 1571], [1570, 1572], [1572, 1573], [1572, 1574]]}, "AgentInvoker._kill_child_processes_fallback": {"executed_lines": [1586, 1587, 1588, 1589, 1590, 1593], "summary": {"covered_lines": 6, "num_statements": 6, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 0, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 1580, "executed_branches": [], "missing_branches": []}, "AgentInvoker._kill_child_processes_psutil": {"executed_lines": [1602, 1603, 1604, 1605, 1606, 1607, 1608, 1609, 1610, 1611, 1612, 1616, 1617, 1620, 1621, 1625, 1626, 1631], "summary": {"covered_lines": 18, "num_statements": 18, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 6, "num_partial_branches": 0, "covered_branches": 6, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 1595, "executed_branches": [[1605, 1606], [1605, 1625], [1608, 1609], [1608, 1610], [1625, 1626], [1625, 1631]], "missing_branches": []}, "AgentInvoker._kill_child_processes_pgrep": {"executed_lines": [1642, 1644, 1645, 1647, 1651, 1652, 1655, 1657, 1662, 1663, 1664, 1668, 1669, 1670, 1671, 1674, 1675, 1676, 1680, 1682, 1683, 1684, 1685, 1686, 1687, 1691, 1692, 1700, 1701, 1705, 1706, 1710, 1711, 1716], "summary": {"covered_lines": 34, "num_statements": 39, "percent_covered": 87.71929824561404, "percent_covered_display": "88", "missing_lines": 5, "excluded_lines": 0, "percent_statements_covered": 87.17948717948718, "percent_statements_covered_display": "87", "num_branches": 18, "num_partial_branches": 2, "covered_branches": 16, "missing_branches": 2, "percent_branches_covered": 88.88888888888889, "percent_branches_covered_display": "89"}, "missing_lines": [1681, 1695, 1696, 1707, 1708], "excluded_lines": [], "start_line": 1635, "executed_branches": [[1651, 1652], [1651, 1657], [1663, 1664], [1663, 1674], [1668, 1663], [1668, 1669], [1669, 1663], [1669, 1670], [1670, 1671], [1674, 1675], [1674, 1710], [1680, 1682], [1683, 1684], [1683, 1685], [1710, 1711], [1710, 1716]], "missing_branches": [[1670, 1669], [1680, 1681]]}, "AgentInvoker.invoke_player": {"executed_lines": [1774, 1784, 1785, 1789, 1790, 1794, 1795, 1796, 1799, 1802, 1804, 1806, 1809, 1810, 1814, 1815, 1829, 1830, 1836, 1838, 1849, 1851, 1856, 1859, 1860, 1863, 1864, 1865, 1866, 1869, 1875, 1888, 1900, 1904, 1911, 1922, 1923, 1925, 1928, 1933, 1943, 1944, 1945, 1986], "summary": {"covered_lines": 44, "num_statements": 56, "percent_covered": 77.14285714285714, "percent_covered_display": "77", "missing_lines": 12, "excluded_lines": 0, "percent_statements_covered": 78.57142857142857, "percent_statements_covered_display": "79", "num_branches": 14, "num_partial_branches": 2, "covered_branches": 10, "missing_branches": 4, "percent_branches_covered": 71.42857142857143, "percent_branches_covered_display": "71"}, "missing_lines": [1816, 1819, 1955, 1956, 1957, 1967, 1968, 1969, 1970, 1971, 1973, 1974], "excluded_lines": [], "start_line": 1720, "executed_branches": [[1784, 1785], [1784, 1789], [1789, 1790], [1809, 1810], [1809, 1814], [1815, 1829], [1829, 1830], [1829, 1900], [1851, 1856], [1851, 1888]], "missing_branches": [[1789, 1794], [1815, 1816], [1969, 1970], [1969, 1973]]}, "AgentInvoker.invoke_coach": {"executed_lines": [2048, 2051, 2052, 2053, 2055, 2064, 2067, 2090, 2104, 2105, 2127, 2141, 2179, 2188, 2192, 2203, 2206, 2207, 2219, 2220, 2233, 2242, 2248, 2250, 2259, 2260, 2261, 2270, 2281, 2282, 2283, 2294], "summary": {"covered_lines": 32, "num_statements": 44, "percent_covered": 70.0, "percent_covered_display": "70", "missing_lines": 12, "excluded_lines": 0, "percent_statements_covered": 72.72727272727273, "percent_statements_covered_display": "73", "num_branches": 6, "num_partial_branches": 3, "covered_branches": 3, "missing_branches": 3, "percent_branches_covered": 50.0, "percent_branches_covered_display": "50"}, "missing_lines": [2065, 2108, 2115, 2145, 2146, 2147, 2151, 2152, 2153, 2165, 2271, 2272], "excluded_lines": [], "start_line": 1988, "executed_branches": [[2064, 2067], [2105, 2127], [2141, 2179]], "missing_branches": [[2064, 2065], [2105, 2108], [2141, 2145]]}, "AgentInvoker._invoke_coach_gather": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 21, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 21, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 6, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 6, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [2347, 2348, 2349, 2350, 2362, 2382, 2383, 2384, 2390, 2395, 2396, 2397, 2398, 2399, 2404, 2405, 2409, 2410, 2411, 2416, 2418], "excluded_lines": [], "start_line": 2296, "executed_branches": [], "missing_branches": [[2382, 2383], [2382, 2384], [2396, 2397], [2396, 2398], [2398, 2399], [2398, 2405]]}, "AgentInvoker._build_coach_gather_prompt": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 18, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 18, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 12, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 12, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [2442, 2443, 2444, 2448, 2449, 2453, 2454, 2455, 2456, 2459, 2460, 2467, 2468, 2469, 2476, 2477, 2478, 2480], "excluded_lines": [], "start_line": 2420, "executed_branches": [], "missing_branches": [[2443, 2444], [2443, 2448], [2449, 2453], [2449, 2454], [2455, 2456], [2455, 2459], [2459, 2460], [2459, 2467], [2468, 2469], [2468, 2480], [2476, 2477], [2476, 2478]]}, "AgentInvoker._build_player_prompt": {"executed_lines": [2545, 2546, 2547, 2556, 2557, 2565, 2566, 2589, 2590, 2591, 2592, 2593, 2594, 2595, 2596, 2599, 2600, 2601, 2602, 2603, 2611, 2616, 2667, 2668, 2670], "summary": {"covered_lines": 25, "num_statements": 27, "percent_covered": 90.69767441860465, "percent_covered_display": "91", "missing_lines": 2, "excluded_lines": 0, "percent_statements_covered": 92.5925925925926, "percent_statements_covered_display": "93", "num_branches": 16, "num_partial_branches": 2, "covered_branches": 14, "missing_branches": 2, "percent_branches_covered": 87.5, "percent_branches_covered_display": "88"}, "missing_lines": [2558, 2567], "excluded_lines": [], "start_line": 2520, "executed_branches": [[2546, 2547], [2546, 2556], [2557, 2565], [2566, 2589], [2590, 2591], [2590, 2599], [2594, 2595], [2594, 2596], [2600, 2601], [2600, 2616], [2602, 2603], [2602, 2611], [2667, 2668], [2667, 2670]], "missing_branches": [[2557, 2558], [2566, 2567]]}, "AgentInvoker._format_design_elements": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 15, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 15, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 8, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 8, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [2681, 2682, 2683, 2684, 2685, 2686, 2687, 2688, 2689, 2690, 2691, 2692, 2693, 2694, 2695], "excluded_lines": [], "start_line": 2672, "executed_branches": [], "missing_branches": [[2681, 2682], [2681, 2683], [2684, 2685], [2684, 2695], [2690, 2691], [2690, 2692], [2692, 2693], [2692, 2694]]}, "AgentInvoker._format_design_tokens": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 3, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 3, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 2, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 2, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [2706, 2707, 2708], "excluded_lines": [], "start_line": 2697, "executed_branches": [], "missing_branches": [[2706, 2707], [2706, 2708]]}, "AgentInvoker._format_design_constraints": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 8, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 8, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 6, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 6, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [2719, 2720, 2721, 2722, 2723, 2724, 2725, 2726], "excluded_lines": [], "start_line": 2710, "executed_branches": [], "missing_branches": [[2719, 2720], [2719, 2721], [2722, 2723], [2722, 2726], [2723, 2722], [2723, 2724]]}, "AgentInvoker._build_coach_prompt": {"executed_lines": [2796, 2805, 2806, 2811, 2813, 2822, 2823, 2824, 2831, 2832, 2845, 2846, 2864, 2865, 2866, 2867, 2868, 2869, 2870, 2871, 2874, 2875, 2876, 2877, 2878, 2883, 2889, 2890, 2915, 2964, 2965, 2979, 3059], "summary": {"covered_lines": 33, "num_statements": 45, "percent_covered": 70.4225352112676, "percent_covered_display": "70", "missing_lines": 12, "excluded_lines": 0, "percent_statements_covered": 73.33333333333333, "percent_statements_covered_display": "73", "num_branches": 26, "num_partial_branches": 7, "covered_branches": 17, "missing_branches": 9, "percent_branches_covered": 65.38461538461539, "percent_branches_covered_display": "65"}, "missing_lines": [2797, 2808, 2825, 2828, 2833, 2849, 2850, 2891, 2922, 2923, 2933, 2942], "excluded_lines": [], "start_line": 2728, "executed_branches": [[2796, 2805], [2806, 2811], [2811, 2813], [2811, 2822], [2824, 2831], [2832, 2845], [2846, 2864], [2865, 2866], [2865, 2874], [2869, 2870], [2869, 2871], [2875, 2876], [2875, 2889], [2877, 2878], [2877, 2883], [2890, 2915], [2915, 2964]], "missing_branches": [[2796, 2797], [2806, 2808], [2824, 2825], [2832, 2833], [2846, 2849], [2890, 2891], [2915, 2922], [2922, 2923], [2922, 2933]]}, "AgentInvoker._truncate_gather_findings": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 5, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 5, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 2, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 2, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [3086, 3087, 3088, 3089, 3090], "excluded_lines": [], "start_line": 3084, "executed_branches": [], "missing_branches": [[3087, 3088], [3087, 3089]]}, "AgentInvoker._render_evidence_bundle_section": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 27, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 27, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 10, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 10, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [3124, 3125, 3126, 3127, 3133, 3139, 3140, 3141, 3142, 3143, 3144, 3147, 3148, 3149, 3150, 3157, 3158, 3159, 3160, 3164, 3165, 3177, 3178, 3179, 3180, 3183, 3185], "excluded_lines": [], "start_line": 3098, "executed_branches": [], "missing_branches": [[3140, 3141], [3140, 3157], [3142, 3143], [3142, 3147], [3148, 3149], [3148, 3157], [3158, 3159], [3158, 3177], [3160, 3164], [3160, 3177]]}, "AgentInvoker._render_bundle_honesty_section": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 16, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 16, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 2, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 2, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [3210, 3212, 3213, 3214, 3215, 3219, 3228, 3229, 3233, 3234, 3245, 3246, 3247, 3248, 3251, 3253], "excluded_lines": [], "start_line": 3193, "executed_branches": [], "missing_branches": [[3229, 3233], [3229, 3245]]}, "AgentInvoker._render_absence_of_failure_guards": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 1, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 1, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 0, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [3277], "excluded_lines": [], "start_line": 3261, "executed_branches": [], "missing_branches": []}, "AgentInvoker._verify_player_claims": {"executed_lines": [3356, 3357, 3360, 3362, 3363, 3367, 3368, 3377], "summary": {"covered_lines": 8, "num_statements": 12, "percent_covered": 68.75, "percent_covered_display": "69", "missing_lines": 4, "excluded_lines": 0, "percent_statements_covered": 66.66666666666667, "percent_statements_covered_display": "67", "num_branches": 4, "num_partial_branches": 1, "covered_branches": 3, "missing_branches": 1, "percent_branches_covered": 75.0, "percent_branches_covered_display": "75"}, "missing_lines": [3373, 3379, 3380, 3382], "excluded_lines": [], "start_line": 3335, "executed_branches": [[3362, 3363], [3367, 3368], [3367, 3377]], "missing_branches": [[3362, 3373]]}, "AgentInvoker._invoke_with_role": {"executed_lines": [3488, 3500, 3501, 3502, 3509, 3514, 3518, 3519, 3525, 3528, 3529, 3530, 3535, 3555, 3570, 3575, 3578, 3580, 3586, 3623, 3655, 3667, 3675, 3677, 3678, 3679, 3680, 3684, 3704, 3713, 3720, 3723, 3731, 3751, 3752, 3753, 3754, 3758, 3769, 3778, 3816, 3822, 3823, 3824, 3825, 3857, 3858, 3859, 3861, 3869, 3879, 3880, 3883, 3895, 3932, 3934], "summary": {"covered_lines": 56, "num_statements": 94, "percent_covered": 54.285714285714285, "percent_covered_display": "54", "missing_lines": 38, "excluded_lines": 0, "percent_statements_covered": 59.57446808510638, "percent_statements_covered_display": "60", "num_branches": 46, "num_partial_branches": 12, "covered_branches": 20, "missing_branches": 26, "percent_branches_covered": 43.47826086956522, "percent_branches_covered_display": "43"}, "missing_lines": [3576, 3656, 3668, 3705, 3759, 3762, 3770, 3771, 3779, 3780, 3781, 3793, 3794, 3795, 3796, 3797, 3798, 3799, 3804, 3826, 3834, 3835, 3838, 3844, 3845, 3846, 3853, 3854, 3855, 3856, 3862, 3863, 3864, 3896, 3905, 3910, 3919, 3933], "excluded_lines": [], "start_line": 3384, "executed_branches": [[3570, 3575], [3570, 3580], [3575, 3578], [3655, 3667], [3667, 3675], [3684, 3704], [3684, 3861], [3704, 3713], [3720, 3723], [3720, 3861], [3723, 3731], [3723, 3861], [3751, 3752], [3758, 3769], [3769, 3778], [3778, 3816], [3816, 3822], [3825, 3857], [3861, 3869], [3932, 3934]], "missing_branches": [[3575, 3576], [3655, 3656], [3667, 3668], [3704, 3705], [3751, 3754], [3758, 3759], [3769, 3770], [3770, 3771], [3770, 3778], [3778, 3779], [3780, 3781], [3780, 3793], [3793, 3794], [3793, 3816], [3795, 3796], [3795, 3816], [3796, 3797], [3796, 3798], [3816, 3723], [3825, 3826], [3853, 3854], [3853, 3857], [3854, 3853], [3854, 3855], [3861, 3862], [3932, 3933]]}, "AgentInvoker._invoke_with_role._cancel_monitor": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 10, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 10, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 2, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 2, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [3625, 3626, 3627, 3631, 3641, 3642, 3643, 3644, 3652, 3653], "excluded_lines": [], "start_line": 3623, "executed_branches": [], "missing_branches": [[3627, 3625], [3627, 3631]]}, "AgentInvoker._emit_llm_call_event": {"executed_lines": [3961, 3962, 3965, 3968, 3971, 3974, 3976, 3992, 4003, 4004, 4005], "summary": {"covered_lines": 11, "num_statements": 15, "percent_covered": 73.33333333333333, "percent_covered_display": "73", "missing_lines": 4, "excluded_lines": 0, "percent_statements_covered": 73.33333333333333, "percent_statements_covered_display": "73", "num_branches": 0, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [4006, 4008, 4009, 4011], "excluded_lines": [], "start_line": 3936, "executed_branches": [], "missing_branches": []}, "AgentInvoker._emit_llm_call_event._safe_emit": {"executed_lines": [3994, 3995], "summary": {"covered_lines": 2, "num_statements": 4, "percent_covered": 50.0, "percent_covered_display": "50", "missing_lines": 2, "excluded_lines": 0, "percent_statements_covered": 50.0, "percent_statements_covered_display": "50", "num_branches": 0, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [3996, 3997], "excluded_lines": [], "start_line": 3992, "executed_branches": [], "missing_branches": []}, "AgentInvoker._emit_tool_exec_event": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 20, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 20, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 4, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 4, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [4058, 4059, 4061, 4063, 4064, 4066, 4069, 4070, 4073, 4076, 4079, 4081, 4095, 4106, 4107, 4108, 4109, 4111, 4112, 4114], "excluded_lines": [], "start_line": 4023, "executed_branches": [], "missing_branches": [[4058, 4059], [4058, 4061], [4063, 4064], [4063, 4066]]}, "AgentInvoker._emit_tool_exec_event._safe_emit": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 4, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 4, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 0, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [4097, 4098, 4099, 4100], "excluded_lines": [], "start_line": 4095, "executed_branches": [], "missing_branches": []}, "AgentInvoker._create_player_report_from_task_work": {"executed_lines": [4145, 4146, 4147, 4150, 4170, 4171, 4172, 4173, 4176, 4177, 4183, 4189, 4190, 4191, 4192, 4193, 4198, 4199, 4207, 4208, 4209, 4210, 4215, 4220, 4221, 4222, 4229, 4230, 4231, 4234, 4235, 4240, 4244, 4245, 4251, 4252, 4253, 4254, 4255, 4257, 4258, 4261, 4262, 4273, 4274, 4276, 4279, 4305, 4308, 4313, 4314, 4315, 4316, 4322, 4323, 4326, 4327, 4330, 4331, 4333, 4334, 4335, 4336, 4337, 4338, 4339, 4340, 4344, 4345, 4346, 4347, 4348, 4351, 4361, 4362, 4363, 4370, 4371, 4418, 4419, 4420, 4421, 4423, 4427, 4428, 4432, 4433, 4434, 4439, 4446, 4475, 4476, 4485, 4486, 4488, 4493, 4494, 4495, 4496, 4498, 4501, 4502, 4503, 4505, 4506, 4507, 4510, 4515, 4516, 4517, 4527, 4528, 4533, 4536, 4537, 4538, 4546, 4547, 4548, 4549, 4563, 4564, 4570, 4571, 4572, 4573, 4576, 4577], "summary": {"covered_lines": 128, "num_statements": 182, "percent_covered": 67.03703703703704, "percent_covered_display": "67", "missing_lines": 54, "excluded_lines": 0, "percent_statements_covered": 70.32967032967034, "percent_statements_covered_display": "70", "num_branches": 88, "num_partial_branches": 15, "covered_branches": 53, "missing_branches": 35, "percent_branches_covered": 60.22727272727273, "percent_branches_covered_display": "60"}, "missing_lines": [4184, 4211, 4212, 4213, 4236, 4237, 4238, 4280, 4281, 4282, 4285, 4288, 4291, 4292, 4297, 4298, 4350, 4364, 4367, 4368, 4372, 4373, 4374, 4377, 4378, 4379, 4380, 4386, 4387, 4388, 4389, 4390, 4396, 4397, 4398, 4399, 4401, 4402, 4406, 4408, 4409, 4426, 4440, 4441, 4447, 4454, 4455, 4456, 4479, 4480, 4511, 4512, 4567, 4568], "excluded_lines": [], "start_line": 4120, "executed_branches": [[4170, 4171], [4170, 4251], [4183, 4189], [4190, 4191], [4190, 4198], [4208, 4209], [4208, 4215], [4210, 4208], [4221, 4222], [4221, 4229], [4230, 4231], [4230, 4234], [4235, 4240], [4253, 4254], [4253, 4330], [4279, 4305], [4315, 4316], [4315, 4322], [4322, 4323], [4322, 4330], [4330, 4331], [4330, 4361], [4333, 4334], [4333, 4336], [4336, 4337], [4336, 4339], [4339, 4340], [4339, 4361], [4344, 4345], [4344, 4346], [4346, 4347], [4363, 4370], [4370, 4371], [4370, 4418], [4371, 4370], [4418, 4419], [4418, 4475], [4433, 4434], [4439, 4446], [4446, 4475], [4493, -4120], [4493, 4494], [4501, 4502], [4501, 4505], [4505, 4506], [4505, 4510], [4510, 4515], [4515, 4516], [4515, 4527], [4536, 4537], [4547, 4548], [4564, 4570], [4570, 4571]], "missing_branches": [[4183, 4184], [4210, 4211], [4212, 4208], [4212, 4213], [4235, 4236], [4279, 4280], [4291, 4292], [4291, 4305], [4346, 4350], [4363, 4364], [4367, 4368], [4367, 4370], [4371, 4372], [4378, 4379], [4378, 4386], [4386, 4387], [4386, 4396], [4388, 4389], [4388, 4396], [4396, 4397], [4396, 4401], [4398, 4399], [4398, 4401], [4401, 4402], [4401, 4406], [4433, 4439], [4439, 4440], [4446, 4447], [4454, 4455], [4454, 4475], [4510, 4511], [4536, 4546], [4547, 4563], [4564, 4567], [4570, -4120]]}, "AgentInvoker._run_preflight_ignore_gate": {"executed_lines": [4594, 4602, 4603, 4617, 4623, 4624, 4629], "summary": {"covered_lines": 7, "num_statements": 17, "percent_covered": 39.130434782608695, "percent_covered_display": "39", "missing_lines": 10, "excluded_lines": 0, "percent_statements_covered": 41.1764705882353, "percent_statements_covered_display": "41", "num_branches": 6, "num_partial_branches": 2, "covered_branches": 2, "missing_branches": 4, "percent_branches_covered": 33.333333333333336, "percent_branches_covered_display": "33"}, "missing_lines": [4604, 4609, 4615, 4618, 4622, 4630, 4631, 4632, 4637, 4639], "excluded_lines": [], "start_line": 4579, "executed_branches": [[4617, 4623], [4623, 4624]], "missing_branches": [[4617, 4618], [4623, 4630], [4630, 4631], [4630, 4639]]}, "AgentInvoker._record_baseline": {"executed_lines": [4653, 4655, 4656, 4657, 4664, 4665, 4666, 4667, 4668, 4669, 4670], "summary": {"covered_lines": 11, "num_statements": 11, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 2, "num_partial_branches": 0, "covered_branches": 2, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 4645, "executed_branches": [[4664, -4645], [4664, 4665]], "missing_branches": []}, "AgentInvoker._detect_git_changes": {"executed_lines": [4684, 4686, 4688, 4689, 4691, 4692, 4699, 4700, 4705, 4712, 4713, 4717, 4718, 4719, 4720, 4722], "summary": {"covered_lines": 16, "num_statements": 16, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 4, "num_partial_branches": 0, "covered_branches": 4, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 4672, "executed_branches": [[4699, 4700], [4699, 4705], [4712, 4713], [4712, 4722]], "missing_branches": []}, "AgentInvoker._create_synthetic_direct_mode_report": {"executed_lines": [4752, 4754, 4755, 4756, 4757, 4759, 4760, 4761, 4762, 4763, 4766, 4767, 4773, 4774, 4779, 4780, 4782], "summary": {"covered_lines": 17, "num_statements": 17, "percent_covered": 95.23809523809524, "percent_covered_display": "95", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 4, "num_partial_branches": 1, "covered_branches": 3, "missing_branches": 1, "percent_branches_covered": 75.0, "percent_branches_covered_display": "75"}, "missing_lines": [], "excluded_lines": [], "start_line": 4724, "executed_branches": [[4761, 4762], [4773, 4774], [4773, 4782]], "missing_branches": [[4761, 4782]]}, "AgentInvoker._find_task_file": {"executed_lines": [4807, 4816, 4817, 4818, 4820, 4821, 4823], "summary": {"covered_lines": 7, "num_statements": 7, "percent_covered": 92.3076923076923, "percent_covered_display": "92", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 6, "num_partial_branches": 1, "covered_branches": 5, "missing_branches": 1, "percent_branches_covered": 83.33333333333333, "percent_branches_covered_display": "83"}, "missing_lines": [], "excluded_lines": [], "start_line": 4797, "executed_branches": [[4816, 4817], [4816, 4823], [4817, 4818], [4817, 4820], [4820, 4821]], "missing_branches": [[4820, 4816]]}, "AgentInvoker._lookup_task_type": {"executed_lines": [4834, 4835, 4836], "summary": {"covered_lines": 3, "num_statements": 8, "percent_covered": 33.333333333333336, "percent_covered_display": "33", "missing_lines": 5, "excluded_lines": 0, "percent_statements_covered": 37.5, "percent_statements_covered_display": "38", "num_branches": 4, "num_partial_branches": 1, "covered_branches": 1, "missing_branches": 3, "percent_branches_covered": 25.0, "percent_branches_covered_display": "25"}, "missing_lines": [4837, 4838, 4839, 4840, 4841], "excluded_lines": [], "start_line": 4825, "executed_branches": [[4835, 4836]], "missing_branches": [[4835, 4837], [4839, 4840], [4839, 4841]]}, "AgentInvoker._load_task_metadata": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 11, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 11, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 2, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 2, "percent_branches_covered": 0.0, "percent_branches_covered_display": "0"}, "missing_lines": [4852, 4854, 4855, 4857, 4858, 4859, 4860, 4861, 4862, 4863, 4865], "excluded_lines": [], "start_line": 4843, "executed_branches": [], "missing_branches": [[4858, 4859], [4858, 4865]]}, "AgentInvoker._generate_file_existence_promises": {"executed_lines": [], "summary": {"covered_lines": 0, "num_statements": 2, "percent_covered": 0.0, "percent_covered_display": "0", "missing_lines": 2, "excluded_lines": 0, "percent_statements_covered": 0.0, "percent_statements_covered_display": "0", "num_branches": 0, "num_partial_branches": 0, "covered_branches": 0, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [4892, 4896], "excluded_lines": [], "start_line": 4867, "executed_branches": [], "missing_branches": []}, "AgentInvoker._load_agent_report": {"executed_lines": [4925, 4928, 4929, 4930, 4934, 4939, 4940, 4941, 4942, 4943, 4944, 4952], "summary": {"covered_lines": 12, "num_statements": 13, "percent_covered": 89.47368421052632, "percent_covered_display": "89", "missing_lines": 1, "excluded_lines": 0, "percent_statements_covered": 92.3076923076923, "percent_statements_covered_display": "92", "num_branches": 6, "num_partial_branches": 1, "covered_branches": 5, "missing_branches": 1, "percent_branches_covered": 83.33333333333333, "percent_branches_covered_display": "83"}, "missing_lines": [4948], "excluded_lines": [], "start_line": 4903, "executed_branches": [[4928, 4929], [4928, 4939], [4929, 4930], [4929, 4934], [4943, 4944]], "missing_branches": [[4943, 4948]]}, "AgentInvoker._retry_with_backoff": {"executed_lines": [4982, 4983, 4985, 4986, 4987, 4988, 4989, 4990, 4991, 4995, 4996, 4999], "summary": {"covered_lines": 12, "num_statements": 12, "percent_covered": 100.0, "percent_covered_display": "100", "missing_lines": 0, "excluded_lines": 0, "percent_statements_covered": 100.0, "percent_statements_covered_display": "100", "num_branches": 4, "num_partial_branches": 0, "covered_branches": 4, "missing_branches": 0, "percent_branches_covered": 100.0, "percent_branches_covered_display": "100"}, "missing_lines": [], "excluded_lines": [], "start_line": 4954, "executed_branches": [[4985, 4986], [4985, 4999], [4990, 4985], [4990, 4991]], "missing_branches": []}, "AgentInvoker._get_report_path": {"executed_lines": [5017], "summary": {"covered_lines
... [results truncated, try being more specific with your parameters]

