---
format_version: 1
description: Reference slices for /task-work — extended documentation, not a command. Run /task-work.
---

# Task Work — Build Phases (Phase 3 – Phase 6, Steps 6.5–7 detail)

> **Reference file — not a command.** On-demand extension of `task-work.md`
> (K13 core/`-ext` shape, PB-13 wave 1). The core file's flag table, phase
> sequence, and state-transition rules are normative; nothing here overrides
> them. Flag semantics are defined ONCE in `task-work.md` § Available Flags (PB-9).

## Step 4 Phases — Build (Phase 3-BDD … Phase 5.5)

#### Phase 3-BDD: BDD Test Generation (BDD Mode Only)

**IF mode == 'bdd'**:

**DISPLAY INVOCATION MESSAGE**:
```
═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: bdd-generator
═══════════════════════════════════════════════════════
Phase: 3-BDD (BDD Test Generation)
Model: Sonnet (Gherkin parsing and test mapping require reasoning)
Mode: BDD (Scenario-driven development)
Specialization:
  - Gherkin scenario parsing (Feature/Scenario/Given/When/Then)
  - BDD framework-specific step definitions
  - Test code generation from scenarios
  - {bdd_framework} integration

Starting agent execution...
═══════════════════════════════════════════════════════
```

**INVOKE** Task tool:
```
subagent_type: "bdd-generator"
description: "Generate BDD tests for TASK-XXX from Gherkin scenarios"
prompt: "Generate BDD acceptance tests for TASK-{task_id}.

LOADED SCENARIOS:
{for scenario in task_context['gherkin_scenarios']:}
Scenario ID: {scenario['id']}
File: {scenario['file']}
Content:
{scenario['content']}

{endfor}

BDD FRAMEWORK: {task_context['bdd_framework']}
PROJECT STACK: {detected_stack}

REQUIREMENTS:
1. Parse all Gherkin scenarios (Feature/Scenario/Given/When/Then)
2. Generate step definitions for {task_context['bdd_framework']}
   - Python: pytest-bdd step definitions in tests/step_defs/
   - JavaScript/TypeScript: Cucumber.js step definitions
   - .NET: SpecFlow step definitions with C# bindings
   - Ruby: Cucumber step definitions
3. Create test files that execute scenarios
4. Map Given/When/Then steps to test implementation
5. Generate FAILING tests initially (BDD RED phase)
6. Set up BDD test configuration (if needed)

OUTPUT:
- Step definition files matching {task_context['bdd_framework']} conventions
- Test runner configuration (pytest.ini, cucumber.js config, etc.)
- Feature file integration (if copying to project)
- Test data/fixtures as needed
- Documentation showing scenario → step → code mapping

The implementation in next phase (Phase 3) will make these tests pass."
```

**WAIT** for agent to complete before proceeding.

**DISPLAY COMPLETION MESSAGE**:
```
═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: bdd-generator
═══════════════════════════════════════════════════════
Duration: {phase_3_bdd_duration_seconds}s
Step definitions created: {step_def_count}
Scenarios mapped: {len(task_context['gherkin_scenarios'])}
Framework: {task_context['bdd_framework']}
Status: BDD tests generated (RED phase) - ready for implementation

Proceeding to Phase 3...
═══════════════════════════════════════════════════════
```

Phase gate validation is deferred to Step 6.5 (see Phase 2 note).

**ELSE** (standard or TDD mode):
Skip Phase 3-BDD, proceed directly to Phase 3

#### Phase 3: Implementation

**DISPLAY INVOCATION MESSAGE**:
```
═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: {selected_implementation_agent_from_table}
═══════════════════════════════════════════════════════
Phase: 3 (Implementation)
Model: Haiku (Fast implementation, Sonnet for complexity ≥7)
Stack: {detected_stack}
Specialization:
  - Production-quality code generation
  - {stack}-specific patterns and conventions
  - Test-driven development support

Starting agent execution...
═══════════════════════════════════════════════════════
```

**INVOKE** Task tool:
```
subagent_type: "{selected_implementation_agent_from_table}"
description: "Implement TASK-XXX"
prompt: "Implement TASK-XXX following {stack} best practices and planned architecture.
         Use patterns identified in planning phase.
         Create production-quality code with proper error handling.
         Follow {stack}-specific conventions and patterns.
         {if mode == 'bdd':}
         BDD MODE: Implement code to make BDD test step definitions PASS.
         - Focus on making Given/When/Then scenarios pass
         - Follow scenario requirements precisely
         - Implement step definition logic
         - The BDD tests were generated in Phase 3-BDD
         {endif}
         Prepare codebase for comprehensive testing."
```

**WAIT** for agent to complete before proceeding.

**DISPLAY COMPLETION MESSAGE**:
```
═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: {selected_implementation_agent_from_table}
═══════════════════════════════════════════════════════
Duration: {phase_3_duration_seconds}s
Files created/modified: {implementation_file_count}
Lines of code: {loc_added}
Error handling: {error_handling_status}
Status: Implementation complete - ready for testing

Proceeding to Phase 4...
═══════════════════════════════════════════════════════
```

Phase gate validation is deferred to Step 6.5 (see Phase 2 note).

#### Phase 4: Testing

**CRITICAL**: Refer to test-orchestrator.md for mandatory compilation verification before testing.

**DISPLAY INVOCATION MESSAGE**:
```
═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: {selected_testing_agent_from_table}
═══════════════════════════════════════════════════════
Phase: 4 (Testing)
Model: Haiku (Fast test execution)
Stack: {detected_stack}
Specialization:
  - Comprehensive test suite generation
  - Coverage analysis and reporting
  - {stack}-specific testing frameworks

Starting agent execution...
═══════════════════════════════════════════════════════
```

**INVOKE** Task tool with documentation context:
```
subagent_type: "{selected_testing_agent_from_table}"
description: "Generate and execute tests for TASK-XXX"
prompt: "<AGENT_CONTEXT>
documentation_level: {documentation_level}
complexity_score: {task_context.complexity}
task_id: {task_id}
stack: {stack}
phase: 4
</AGENT_CONTEXT>

Create comprehensive test suite for {task_id} implementation.
Include: unit tests, integration tests, edge cases.
Target: 80%+ line coverage, 75%+ branch coverage.
Use {stack}-specific testing frameworks and patterns.

{if mode == 'bdd':}
BDD MODE: Execute BDD tests generated in Phase 3-BDD
- Run BDD scenarios using {task_context.get('bdd_framework')}
- Test commands:
  * Python: pytest tests/ -v --gherkin-terminal-reporter (pytest-bdd)
  * TypeScript/JS: npm run test:bdd or npx cucumber-js (Cucumber.js)
  * .NET: dotnet test --filter Category=BDD (SpecFlow)
  * Ruby: cucumber features/ (Cucumber)
- BDD tests MUST pass 100% (part of Phase 4.5 enforcement)
- Also run standard unit tests for complete coverage
{endif}

🚨 MANDATORY COMPILATION CHECK (See test-orchestrator.md):
1. MUST verify code COMPILES/BUILDS successfully BEFORE running tests
2. If compilation fails, report errors immediately with file:line details
3. ONLY proceed to test execution if compilation succeeds with zero errors
4. Use stack-specific build commands (see test-orchestrator.md for details)

EXECUTE the test suite and report detailed results:
- Build/compilation status (MUST be success before tests run)
- Test execution results (passed/failed counts)
- Coverage metrics (line and branch percentages)
- Detailed failure information for any failing tests

DOCUMENTATION BEHAVIOR (documentation_level={documentation_level}):
- minimal: Return test results as structured data (counts, coverage, failures). CONSTRAINT: Generate ONLY 2 files maximum.
- standard: Return results with brief test descriptions. CONSTRAINT: Generate ONLY 2 files maximum.
- comprehensive: Generate detailed test report with rationale for each test (13+ files allowed)

See installer/core/agents/test-orchestrator.md for the testing-agent prompt style. The authoritative compilation/test pass bar is enforced by Coach's independent pytest run in `coach_validator`, not by this prompt."
```

**WAIT** for agent to complete before proceeding.

**DISPLAY COMPLETION MESSAGE**:
```
═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: {selected_testing_agent_from_table}
═══════════════════════════════════════════════════════
Duration: {phase_4_duration_seconds}s
Tests executed: {test_count}
Line coverage: {line_coverage}%
Branch coverage: {branch_coverage}%
Test status: {test_status}
Status: Test suite ready for verification

Proceeding to Phase 4.5...
═══════════════════════════════════════════════════════
```

Phase gate validation is deferred to Step 6.5 (see Phase 2 note).

#### Phase 4.5: Fix Loop (Ensure All Tests Pass)

**Phase 4.5 is LLM-driven guidance, not a deterministic runtime loop.** The Player is expected to read the testing agent's output qualitatively, decide whether another fix cycle is warranted, and re-invoke the implementation + testing agents up to three times. The `max_attempts = 3` bound is an instruction to the Player, not a counter evaluated by a Python driver. The deterministic pass bar is enforced independently by Coach via its own `coach_validator` pytest run on the final worktree — the retry-loop prose below is guidance for the Player, not a gate.

**EVALUATE** test results from Phase 4:

Inspect the testing agent's reply qualitatively and look for:

- **Compilation errors** — common patterns include `error:`, `error TS\d+`, `.cs(\d+,\d+):`, `Traceback`, or a non-zero exit code on the stack-specific build command.
- **Test failures** — markers like `FAILED`, `AssertionError`, `Test.*failed`, or the framework summary line reporting one or more failures.
- **Coverage percentages** — line coverage and branch coverage reported by the coverage tool (if the stack emits coverage; some stacks/modes skip this).

If the reply reports clean compilation **and** zero test failures, exit the guidance and proceed to Phase 5. Otherwise the Player may take up to three fix attempts (after that, escalate to BLOCKED per the guidance below). Coach's independent run remains the source of truth for the pass bar.

**FIX-ATTEMPT GUIDANCE** (up to 3 attempts):

1. **DISPLAY** Failure Report:
   ```
   ⚠️  TESTS FAILING - Entering Fix Loop (Attempt {attempt}/3)

   Compilation Errors: {count}
   {List of compilation errors with file:line}

   Test Failures: {count}
   {List of failing tests with assertion details}

   Initiating automatic fix cycle...
   ```

2. **INVOKE** Task tool to fix issues:
   ```
   subagent_type: "{selected_implementation_agent_from_table}"
   description: "Fix test failures for TASK-XXX (Attempt {attempt})"
   prompt: "Fix the failing tests for TASK-XXX.

            COMPILATION ERRORS ({count}):
            {list_of_compilation_errors_with_file_line}

            TEST FAILURES ({count}):
            {list_of_test_failures_with_details}

            CRITICAL INSTRUCTIONS:
            1. Fix ALL compilation errors FIRST - code must build
            2. Run the build command to verify compilation succeeds
            3. Fix failing test assertions by correcting the implementation
            4. Ensure code behavior matches test expectations
            5. Do NOT modify tests unless they're provably incorrect
            6. Do NOT skip, comment out, or ignore failing tests
            7. Do NOT mark tests with [Ignore] or skip attributes

            SUCCESS CRITERIA:
            - Zero compilation errors
            - All tests pass (100%)
            - No tests skipped or ignored

            You MUST achieve passing tests before completing."
   ```

3. **WAIT** for fix to complete

4. **RE-INVOKE** Phase 4 Testing:
   ```
   subagent_type: "{selected_testing_agent_from_table}"
   description: "Re-run tests for TASK-XXX after fixes (Attempt {attempt})"
   prompt: "Re-execute the complete test suite for TASK-XXX after fixes.

            VERIFY:
            1. Code compiles/builds successfully (no errors)
            2. All tests execute without errors
            3. All tests pass (no failures)
            4. Coverage meets thresholds (≥80% line, ≥75% branch)

            Report detailed results including:
            - Build/compilation status
            - Test pass/fail counts
            - Coverage percentages
            - Any remaining failures"
   ```

5. **WAIT** for test execution to complete

6. **RE-INSPECT** the new testing-agent output: look again for compilation errors and test failures using the same qualitative markers from the EVALUATE step above. Increment the attempt counter the Player is tracking in its own reasoning.

7. **IF** the latest output reports clean compilation **and** zero test failures:
   ```
   ✅ All tests passing! Proceeding to code review.
   ```
   Exit the guidance → Proceed to Phase 5.

8. **ELSE IF** three fix attempts have already been made:
   ```
   ❌ CRITICAL: Unable to achieve passing tests after 3 attempts

   Final Status:
   - Compilation Errors: {count}
   - Test Failures: {count}
   - Coverage: {percentage}%

   Task moved to BLOCKED state with detailed diagnostics.
   Manual intervention required.

   Diagnostics have been saved to task file.
   ```
   Exit the guidance → Move to BLOCKED state.

9. **ELSE**:
   Continue with the next fix attempt.

**Result of Phase 4.5**:
- ✅ **SUCCESS**: All tests passing → Proceed to Phase 5. Coach re-verifies independently.
- ❌ **BLOCKED**: Three attempts exhausted without passing → Move to BLOCKED, skip Phase 5. Coach confirms blockage via its own run.

#### Phase 5: Code Review

**ONLY EXECUTE IF Phase 4.5 succeeded (all tests passing)**

**DISPLAY INVOCATION MESSAGE**:
```
═══════════════════════════════════════════════════════
🤖 INVOKING AGENT: code-reviewer
═══════════════════════════════════════════════════════
Phase: 5 (Code Review)
Model: Sonnet (Expert code quality assessment)
Stack: {detected_stack}
Specialization:
  - Code quality and best practices verification
  - Test coverage validation
  - Documentation and error handling review

Starting agent execution...
═══════════════════════════════════════════════════════
```

**INVOKE** Task tool with documentation context:
```
subagent_type: "code-reviewer"
description: "Review TASK-XXX implementation"
prompt: "<AGENT_CONTEXT>
documentation_level: {documentation_level}
complexity_score: {task_context.complexity}
task_id: {task_id}
stack: {stack}
phase: 5
</AGENT_CONTEXT>

Review {task_id} implementation for quality and best practices.
Check: code quality, test coverage, error handling, documentation.
Verify {stack}-specific patterns are correctly applied.
Provide actionable feedback if improvements needed.
Confirm readiness for IN_REVIEW state or identify blockers.

DOCUMENTATION BEHAVIOR (documentation_level={documentation_level}):
- minimal: Return approval status and critical issues only. CONSTRAINT: Generate ONLY 2 files maximum.
- standard: Return review with brief feedback on key areas. CONSTRAINT: Generate ONLY 2 files maximum.
- comprehensive: Generate detailed code review report with recommendations (13+ files allowed)

See installer/core/agents/code-reviewer.md for documentation level specifications."
```

**WAIT** for agent to complete before proceeding.

**DISPLAY COMPLETION MESSAGE**:
```
═══════════════════════════════════════════════════════
✅ AGENT COMPLETED: code-reviewer
═══════════════════════════════════════════════════════
Duration: {phase_5_duration_seconds}s
Code quality score: {code_quality_score}/100
Issues found: {issues_found_count}
Recommendations: {recommendations_count}
Status: Code review complete - quality approved

Proceeding to Phase 5.5...
═══════════════════════════════════════════════════════
```

Phase gate validation is deferred to Step 6.5 (see Phase 2 note).

#### Phase 5.5: Plan Audit (Hubbard's Step 6)

Implements John Hubbard's Step 6 (Audit) from his proven 6-step workflow. Closes a critical gap in AI-Engineer Lite (ThoughtWorks: "Agents frequently don't follow all instructions").

**Two execution paths** — the same deterministic auditor feeds both:

- **Interactive `/task-work`** (human at terminal): Claude invokes the auditor, displays the report, and prompts the developer for an A/R/E/C decision with a 30-second timeout (auto-approve on timeout).
- **Autobuild producer** (Player ↔ Coach): The auditor runs **non-interactively** inside `AgentInvoker._write_task_work_results` (TASK-FIX-RWOP1.3.2). Its verdict is written to `task_work_results.json plan_audit` and **overrides** any Player-supplied block. Coach reads the deterministic verdict, not the Player's self-report. No prompt fires; severity drives Coach's decision.

**When to execute:**
- Always after Phase 5 (Code Review) in standard and `--implement-only` workflows
- Skip if no implementation plan exists (auditor writes `status: "skipped"`)
- NOT executed in `--micro` mode (no plan generated)

**Objective:**
Verify that actual implementation matches the approved architectural plan. Catch scope creep, validate complexity estimates, and ensure the Player followed the plan — without trusting the Player's self-report.

**Why the autobuild fold matters:** `guardkit/orchestrator/quality_gates/coach_validator.py` reads `task_work_results["plan_audit"]` to gate turn approval. Before TASK-FIX-RWOP1.3.2 the producer of that field was the Player LLM's prose output — the Player could trivially emit `"violations": []` regardless of whether the actual implementation deviated from the plan. Folding `execute_phase_5_5_plan_audit(..., non_interactive=True, workspace_root=self.worktree_path)` into the producer path makes Coach see the deterministic auditor's verdict.

**Process (both paths share steps 1-4):**
1. **Load saved implementation plan** from `docs/state/{task_id}/implementation_plan.md` (falls back to `.json` for legacy plans). The loader is workspace-root-aware, so the autobuild path resolves plans relative to the worktree, not the orchestrator's cwd.
2. **Analyze actual implementation by scanning the filesystem:**
   - Scan for files matching `src/**/*.py`, `installer/**/*.py`, `src/**/*.ts`, `src/**/*.tsx`, `*.cs`, etc.
   - Count lines of code (LOC) for planned files
   - Extract dependencies from package files (`requirements.txt`, `pyproject.toml`, `package.json`, `*.csproj`)
   - Calculate implementation duration (if available in task metadata)
3. **Compare planned vs actual:**
   - **Files**: list extra files, missing files
   - **Dependencies**: list extra deps, missing deps
   - **LOC**: calculate % variance
   - **Duration**: calculate % variance
4. **Generate audit report** with severity (low/medium/high) using the thresholds below.
5. **Route by path:**
   - Interactive: display report, prompt `[A]pprove/[R]evise/[E]scalate/[C]ancel` with 30 s timeout.
   - Autobuild: skip prompt, stdout print, and metadata mutation. Write the verdict block to `task_work_results.plan_audit` (overriding any Player-supplied block); Coach rejects the turn when `severity == "high"`.

**Severity Calculation:**
- **Low**: <10% variance, 0 extra files, all metrics within acceptable range
- **Medium**: 10-30% variance, 1-2 extra files, or 1-2 extra dependencies
- **High**: >30% variance, 3+ extra files, 3+ extra dependencies, or major deviations

**Human Decision Options (interactive `/task-work` only):**
- **[A]pprove**: Accept implementation as-is, proceed to IN_REVIEW
  - Updates task metadata with audit results
  - Non-blocking default (allows unattended operation)
- **[R]evise**: Request removal of scope creep, transition to BLOCKED
  - Requires manual intervention to remove extra files/dependencies
  - Task cannot proceed until revised
- **[E]scalate**: Create follow-up task, proceed to IN_REVIEW with warning
  - Acknowledges complexity underestimation
  - Creates tracking task for scope creep investigation
  - Current task completes but flagged for analysis
- **[C]ancel**: Block task completion, transition to BLOCKED
  - Complete rejection of implementation
  - Requires full rework

**Autobuild Coach Decision (no prompt):**
- `severity == "high"` → Coach rejects the turn with a `must_fix` `plan_audit` issue naming the extras. The Player's next turn has actionable feedback to correct course.
- `severity in {low, medium}` with non-zero legacy `violations` → Coach rejects with `should_fix` (back-compat with pre-severity fixtures).
- `status == "skipped"` or `status == "auditor_error"` → non-blocking (the auditor not running is not evidence of a task failing, and the agent_invocations gate covers the "Player skipped phases entirely" case).
- `status == "passed"` → gate clears; Coach evaluates remaining quality gates.

**Interactive Timeout Behavior:**
- 30-second timeout for human response
- **Auto-approves if no input** (non-blocking default)
- Allows unattended operation while preserving human control option
- Audit report saved to `docs/state/{task_id}/plan_audit_report.json`

**Metrics Tracking:**
Audit outcomes are tracked in `docs/state/plan_audit_metrics.json` for:
- **Complexity model improvement**: Use LOC/duration variances to refine estimates
- **Scope creep pattern detection**: Identify common sources of extra files/deps
- **Estimation accuracy refinement**: Create feedback loop for better planning

**Example Output:**
```
======================================================================
PLAN AUDIT - TASK-042
======================================================================

PLANNED IMPLEMENTATION:
  Files: 5 files (245 lines)
  Dependencies: 2 (axios, bcrypt)
  Duration: 4 hours

ACTUAL IMPLEMENTATION:
  Files: 7 files (380 lines)
  Dependencies: 3 (axios, bcrypt, lodash)
  Duration: 6 hours

DISCREPANCIES:
  🔴 2 extra file(s) not in plan
      - src/utils/helpers.ts
      - src/utils/validators.ts

  🟡 1 extra dependenc(ies) not in plan
      - lodash

  🔴 LOC variance: +55.1% (245 → 380 lines)

  🟡 Duration variance: +50.0% (4.0h → 6.0h)

SEVERITY: 🔴 HIGH

RECOMMENDATIONS:
  1. Review extra files for scope creep: src/utils/helpers.ts, src/utils/validators.ts
  2. Justify extra dependencies: lodash
  3. Understand why LOC exceeded estimate by 55%

OPTIONS:
  [A]pprove - Accept implementation as-is, update plan retroactively
  [R]evise - Request removal of scope creep items
  [E]scalate - Mark as complex, create follow-up task
  [C]ancel - Block task completion

Choice [A]pprove/[R]evise/[E]scalate/[C]ancel (30s timeout = auto-approve): _
```

**Implementation:**
- Interactive entry point: `execute_phase_5_5_plan_audit(task_id, task_context)` in `installer/core/commands/lib/phase_execution.py`
- Non-interactive producer entry point (autobuild): `execute_phase_5_5_plan_audit(task_id, task_context, non_interactive=True, workspace_root=...)`
- Core auditor: `installer/core/commands/lib/plan_audit.py` (workspace-root-aware plan loading)
- Producer wire: `AgentInvoker._compute_plan_audit_verdict()` and the fold in `_write_task_work_results` (TASK-FIX-RWOP1.3.2)
- Coach consumer: `verify_quality_gates` and `_feedback_from_gates` in `guardkit/orchestrator/quality_gates/coach_validator.py`
- Metrics tracking (interactive path only): `installer/core/commands/lib/metrics/plan_audit_metrics.py`

**Skip Behavior:**
If no implementation plan exists on disk, Phase 5.5 emits `status: "skipped"` and the gate passes without review. Interactive path prints a `⚠️  No implementation plan found - skipping audit` message; autobuild path silently writes the skipped block to `task_work_results.plan_audit`.

**Success Criteria:**
- Audit completes in < 5 seconds
- Discrepancies accurately detected (files, dependencies, LOC, duration)
- Interactive: human decision properly handled, task metadata updated, metrics tracked
- Autobuild: deterministic verdict written to `task_work_results.plan_audit`, Player self-report overridden

**Error Handling (never blocks artefact emission):**
- Plan doesn't exist: `status: "skipped"`, gate passes
- Auditor crashes: `status: "auditor_error"` with exception message, gate passes (non-blocking — matches the `validator_error` invariant on the agent_invocations gate)
- Interactive decision timeout: auto-approve with warning

**Benefits:**
- ✅ Catches scope creep automatically (saves review time)
- ✅ Deterministic — the Player can't self-certify a clean audit when the worktree has extras
- ✅ Validates complexity estimates (improves future planning)
- ✅ Ensures AI follows plan (detects hallucinations and scope creep)
- ✅ Closes Hubbard's Step 6 gap (100% workflow alignment)
- ✅ Creates feedback loop for estimation improvement


## Step 6.5 — Full Validation Mechanics

Continues the core's Step 6.5 (purpose + ONLY-checkpoint framing live there):


**Producer-side wire (TASK-FIX-RWOP1.3.1)**. The gate is folded into `AgentInvoker._write_task_work_results` in `guardkit/orchestrator/agent_invoker.py`. Every write path into `.guardkit/autobuild/{task_id}/task_work_results.json` runs this sequence before the file hits disk:

1. Read the `agent_invocations` list the Player emitted (or reconstruct it from the stream parser's `phases` dict as a fallback).
2. Build a throwaway `AgentInvocationTracker` from that list.
3. Call `validate_agent_invocations(tracker, workflow_mode)` from `installer/core/commands/lib/agent_invocation_validator.py`.
4. Write the verdict into `task_work_results["agent_invocations_validation"]` with shape:

```json
{
  "status": "passed" | "violation" | "validator_error" | "no_data",
  "expected_phases": 5,
  "actual_invocations": 3,
  "missing_phases": ["4", "5"],
  "violation_message": "PROTOCOL VIOLATION: ..."
}
```

The gate never blocks artefact emission — a validator crash records `validator_error` and the results file is still written. That keeps the validator a gate, not a blocker.

**Status meanings**:

- `passed` — all expected phases have completed invocations; Coach proceeds to quality-gate evaluation.
- `violation` — at least one expected phase is missing; Coach rejects the turn.
- `validator_error` — the validator itself raised; informational, Coach does *not* reject on this status alone.
- `no_data` — neither an explicit `agent_invocations` list nor parser-captured phase markers were present on the input. Typical for synthetic fixture writes or pre-phase pipeline failures; Coach does not reject. Real-world Player misbehaviour is caught earlier by the SDK stream-parse path.

**Coach-side enforcement**. `guardkit/orchestrator/quality_gates/coach_validator.py` treats `status == "violation"` as a task-blocking finding. The turn is rejected with a `must_fix` issue in the `agent_invocations_violation` category whose feedback names the missing phases, so the Player's next turn knows which phases to actually invoke. `validator_error` and `no_data` are deliberately *not* blockers — the validator's own failure (or missing input) shouldn't stop Coach from evaluating everything else.

**Workflow Mode Phase Counts** (enforced by `get_expected_phases` in `agent_invocation_validator.py`):

- `standard`: 5 phases (Planning, Arch Review, Implementation, Testing, Code Review)
- `micro`: 3 phases (Implementation, Testing, Quick Review)
- `design-only`: 3 phases (Planning, Arch Review, Complexity)
- `implement-only`: 3 phases (Implementation, Testing, Code Review) — the autobuild Player default

**Example violation block** on disk after a Player emits `task_work_results.json` claiming implement-only completion but only actually running Phase 3:

```json
{
  "task_id": "TASK-XXX",
  "quality_gates": { "...": "..." },
  "agent_invocations_validation": {
    "status": "violation",
    "expected_phases": 3,
    "actual_invocations": 1,
    "missing_phases": ["4", "5"],
    "violation_message": "❌ PROTOCOL VIOLATION: Agent invocation incomplete\nExpected: 3 agent invocations\nActual: 1 completed invocations\nMissing phases:\n  - Phase 4 (Testing)\n  - Phase 5 (Code Review)"
  }
}
```

Coach reads that block and returns a feedback decision with rationale `"Agent-invocations protocol violation: missing phases 4, 5"`.

**Re-run surface**. The enrichment block at `agent_invoker.py:_create_player_report_from_task_work` re-runs the gate against the enriched `task_work_data` before the final on-disk rewrite, so the last version Coach reads always carries the freshest verdict.

**Canonical fix shape**: this is the same producer-runs-gate pattern as [TASK-FIX-3C9D](../../tasks/completed/TASK-FIX-3C9D/TASK-FIX-3C9D-wire-ac-linter-into-feature-plan.md) (AC linter folded into `generate_feature_yaml.py`). Both close the "runner without producer" gap by moving the check from aspirational prose into the script that actually writes the artefact.

**What happens if this step is skipped**: the Python runtime never raises; `task_work_results.json` lacks `agent_invocations_validation`; Coach's gate short-circuits to "no violation" and the Player's claims go unverified. Do not remove the hook in `_write_task_work_results` without moving the gate to another producer.


## Step 7 — Report Templates

#### Success Report (All Tests Passing)

```
✅ Task Work Complete - TASK-XXX

🔍 Stack: {detected_stack}
🤖 Agents Used: {list_of_agents}
⏱️  Duration: {total_duration}

📊 Test Results:
- Compilation: ✅ Success
- Total Tests: {total_tests}
- Passed: {passed_tests} ✅ (100%)
- Failed: 0
- Skipped: 0
- Coverage: {coverage_percentage}% (line), {branch_percentage}% (branch)

🔧 Fix Loop Summary:
- Initial test run: {initial_failures} failures
- Fix attempts: {fix_attempts_made}
- Final result: All tests passing ✅

📈 Quality Gates:
✅ Code compiles
✅ All tests passing (100%)
✅ Line coverage ({coverage}% ≥ 80%)
✅ Branch coverage ({branch}% ≥ 75%)
{performance_status} Test execution time ({time}s)

🔄 State Transition:
From: IN_PROGRESS
To: IN_REVIEW
Reason: All quality gates passed

📋 Next Steps:
- Human review of implementation
- Merge to main branch if approved
- Deploy to staging environment
```

#### Blocked Report (Tests Still Failing)

```
❌ Task Work Blocked - TASK-XXX

🔍 Stack: {detected_stack}
🤖 Agents Used: {list_of_agents}
⏱️  Duration: {total_duration}

📊 Final Test Results:
- Compilation: {compilation_status}
- Total Tests: {total_tests}
- Passed: {passed_tests}
- Failed: {failed_tests} ❌
- Skipped: {skipped_tests}
- Coverage: {coverage_percentage}%

🔧 Fix Loop Summary:
- Initial failures: {initial_failures}
- Fix attempts made: 3/3 (max reached)
- Remaining issues: {remaining_issues}

❌ Remaining Compilation Errors ({count}):
{list_of_compilation_errors}

❌ Remaining Test Failures ({count}):
{list_of_test_failures}

📈 Quality Gates:
{compile_status} Code compiles
❌ Tests passing ({failed} failures)
{coverage_status} Coverage thresholds

🔄 State Transition:
From: IN_PROGRESS
To: BLOCKED
Reason: Unable to achieve passing tests after 3 fix attempts

📋 Required Actions:
1. Review compilation errors (if any) and fix manually
2. Review test failure details and diagnose root cause
3. Check for missing dependencies or configuration issues
4. Verify test specifications are correct
5. Consider if architectural changes are needed
6. Re-run /task-work once issues are manually resolved

💡 Recommendations:
{specific_recommendations_based_on_error_patterns}
```


## Phase 6 — Finalize Detail (DF-018)

The trigger matrix and tri-state routing are normative in the core
(`task-work.md` § Phase 6). This section carries the display + rollout detail.

### Verify-then-record banner (Green path)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ Phase 6: Task finalized — {task_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Verdict: GREEN (auto-complete; human notified — not gated)
Evidence (not authored by the implementer):
  Plan audit: {plan_audit.verdict} ({violation_count} violations)
  Tests: {passed}/{total} passing · Coverage: {line_pct}% line / {branch_pct}% branch
  Code review: {review_status}
Completion routine (shared atomic routine — guardkit task complete):
  Pre-completion gates: 6/6 passed
  Moved: tasks/in_review/ → tasks/completed/{task_id}/ (atomic flip+move)
  Archived: {n} related files
  Rollup: feature {feature_id} → epic → portfolio; PM sync {sync_status}
  fleet-memory: capture-outcome recorded ({capture_status} — loud on failure)
  Git: conductor state commit {sha}
Pause here instead next time: --pause (alias --no-complete)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Amber pause

Stay at IN_REVIEW and list the specific non-clean evidence (audit violations,
review concerns, coverage gaps). The human completes later via
`guardkit task complete {task_id}` after addressing or accepting them.

### Rollout mechanics (demotion scope §7)

- **Phase 2 (current)**: `--complete` is opt-in; the autobuild and
  operator_handoff carve-outs are enforced unconditionally; the demotion scope
  §6 baseline metric is read for 1–2 weeks before any default change.
- **Later**: the default flips to auto-complete-on-green with `--pause` opt-out —
  a one-line edit to the core's Phase 6 trigger matrix + flag-table row.
- The `/task-complete` slash surface retires only in the demotion scope's final
  phase (PB-2/PB-3 tombstone path), after the CLI + Phase 6 have soaked.
