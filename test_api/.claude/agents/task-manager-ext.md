# task-manager - Extended Reference

This file contains detailed documentation for the `task-manager` agent.
Load this file when you need comprehensive examples and guidance.

```bash
cat agents/task-manager-ext.md
```


## Documentation Level Awareness (TASK-035)

As the **task orchestration agent**, you are responsible for passing the `documentation_level` parameter to all sub-agents throughout the task-work workflow.

### Your Role in Documentation Level System

**Input**: You receive `documentation_level` from task-work command via flags or auto-detection:
- `--docs minimal` → minimal mode
- `--docs standard` → standard mode (DEFAULT)
- `--docs comprehensive` → comprehensive mode
- No flag → auto-detect based on complexity (1-3: minimal, 4-10: standard)

**Output**: You pass this to ALL sub-agents via `<AGENT_CONTEXT>` blocks in your prompts.

### Context Block Format for Sub-Agents

When invoking any sub-agent (architectural-reviewer, test-orchestrator, code-reviewer, test-verifier, etc.), include:

```markdown
<AGENT_CONTEXT>
documentation_level: minimal|standard|comprehensive
complexity_score: 1-10
task_id: TASK-XXX
stack: python|react|maui|etc
phase: 1|2|2.5|3|4|4.5|5|5.5
</AGENT_CONTEXT>

[Your specific instructions to the agent...]
```

### Documentation Level Determination Logic

```python
def determine_documentation_level(task):
    # 1. Command-line flag takes precedence
    if task.flags.docs:
        return task.flags.docs  # minimal|standard|comprehensive

    # 2. Force triggers override auto-detection
    if has_force_triggers(task):
        return "comprehensive"

    # 3. Auto-detect based on complexity
    if task.complexity <= 3:
        return "minimal"
    elif task.complexity <= 6:
        return "standard"
    else:
        return "comprehensive"

def has_force_triggers(task):
    keywords = ["security", "authentication", "compliance", "breaking change"]
    return any(keyword in task.title.lower() or keyword in task.description.lower()
               for keyword in keywords)
```

### Sub-Agent Invocation Pattern

**Phase 1: Requirements Analysis** *(Skipped in GuardKit - Require-Kit Only)*

Phase 1 is **skipped** in GuardKit's lightweight workflow. Tasks use descriptions and acceptance criteria directly without formal requirements analysis.

For formal requirements management with EARS notation and BDD generation, use [require-kit](https://github.com/requirekit/require-kit).

**GuardKit workflow proceeds directly to Phase 2 (Implementation Planning).**

**Phase 2.5B: Architectural Review**
```markdown
Invoke architectural-reviewer agent:

<AGENT_CONTEXT>
documentation_level: {determined_level}
complexity_score: {task.complexity}
task_id: {task.id}
stack: {task.stack}
phase: 2.5B
</AGENT_CONTEXT>

Review the implementation plan for architectural compliance...
```

**Phase 4: Test Orchestration**
```markdown
Invoke test-orchestrator agent:

<AGENT_CONTEXT>
documentation_level: {determined_level}
complexity_score: {task.complexity}
task_id: {task.id}
stack: {task.stack}
phase: 4
</AGENT_CONTEXT>

Execute tests and verify quality gates...
```

**Phase 5: Code Review**
```markdown
Invoke code-reviewer agent:

<AGENT_CONTEXT>
documentation_level: {determined_level}
complexity_score: {task.complexity}
task_id: {task.id}
stack: {task.stack}
phase: 5
</AGENT_CONTEXT>

Perform code review and execute Plan Audit (Phase 5.5)...
```

### Summary Coordination by Mode

Your final task summary format also varies by documentation level:

**Minimal Mode** (complexity 1-3):
```markdown

# Task Summary - {TASK_ID}

**Status**: {status}
**Duration**: {duration}

## Quick Results
- Files: {count}
- Tests: {pass_count}/{total_count} ✅
- Coverage: {percentage}% ✅
- Quality: {score}/10

[Embed JSON results from sub-agents]

Next: /task-complete {TASK_ID}
```

**Standard Mode** (complexity 4-10, DEFAULT):
```markdown

# Implementation Summary - {TASK_ID}

[Full summary with all sections embedded]
- Architecture Review
- Implementation Details
- Test Results
- Code Review
- Plan Audit

Next: /task-complete {TASK_ID}
```

**Comprehensive Mode** (complexity 7-10 or force triggers):
```markdown

# Comprehensive Implementation Report - {TASK_ID}

[Enhanced summary with links to standalone documents]
- Implementation Summary (this file)
- Architecture Guide (docs/architecture/{task_id}-guide.md)
- Test Report (docs/testing/{task_id}-report.md)
- Code Review (docs/code-review/{task_id}-review.md)
- Plan Audit Report (docs/planning/{task_id}-audit.md)

Next: /task-complete {TASK_ID}
```

### Quality Gate Preservation

**CRITICAL**: Documentation level affects **output format** only. The following ALWAYS execute in all modes:

- All workflow phases (1, 2, 2.5, 2.7, 2.8, 3, 4, 4.5, 5, 5.5)
- All quality gates (build, tests, coverage, architecture, code review)
- All enforcement thresholds (≥80% coverage, 100% test pass rate, ≥60/100 architecture score)
- Plan Audit execution (Phase 5.5 - scope creep detection)

### Backward Compatibility

If a sub-agent doesn't recognize `<AGENT_CONTEXT>`, it will:
- Ignore the context block (treated as informational comment)
- Default to standard mode behavior
- Still execute all quality gates

This ensures graceful degradation for agents not yet updated with documentation level awareness.


## Core Operations

### 1. Create Task
- Generate next sequential task ID
- Create file in tasks/backlog/
- Link to existing requirements and BDD scenarios
- Set initial metadata

### 2. Start Task
- Move from backlog/ to in_progress/
- Update status and timestamps
- Check for blockers or dependencies

### 3. Phase 2.7: Implementation Plan Generation & Complexity Evaluation

**WHEN INVOKED** for Phase 2.7, execute the following orchestration:

#### Step 1: Parse Implementation Plan

**OBJECTIVE**: Convert Phase 2 free-form planning output into structured ImplementationPlan

**ACTIONS**:
1. Load Phase 2 planning output from task context
2. Detect technology stack from task metadata
3. Select appropriate plan parser:
   - python → PythonPlanParser
   - react → ReactPlanParser
   - typescript-api → TypeScriptPlanParser
   - maui → DotNetPlanParser
   - dotnet-fastendpoints → DotNetPlanParser
   - default → GenericPlanParser

4. Parse plan to extract:
   - **Files**: List of files to create/modify with purposes
   - **Patterns**: Design patterns mentioned (Repository, Factory, etc.)
   - **Dependencies**: External packages/libraries needed
   - **LOC Estimate**: Estimated lines of code
   - **Risks**: Identified risk areas (security, performance, etc.)
   - **Phases**: Implementation steps with time estimates
   - **Duration**: Total estimated duration

5. **ERROR HANDLING**:
   - If PlanParsingError: Fallback to GenericPlanParser
   - If still fails: Create minimal plan with raw text
   - Never block workflow on parsing failures

6. Save ImplementationPlan to:
   ```
   docs/state/{task_id}/implementation_plan.json
   ```

**OUTPUT**: ImplementationPlan object with all extracted metadata

#### Step 2: Calculate Complexity Score

**OBJECTIVE**: Evaluate implementation complexity using ComplexityCalculator

**ACTIONS**:
1. Create EvaluationContext from:
   - task_id
   - technology_stack
   - implementation_plan (from Step 1)
   - task_metadata

2. Invoke ComplexityCalculator.calculate(eval_context)

3. **Complexity Factors** (each 0-X points, total 0-10):
   - **File Complexity** (0-3 points):
     - 0-2 files: 0.5 points
     - 3-5 files: 1.5 points
     - 6-8 files: 2.5 points
     - 9+ files: 3.0 points

   - **Pattern Familiarity** (0-2 points):
     - All familiar patterns: 0 points
     - Mixed familiar/new: 1 point
     - New/complex patterns: 2 points

   - **Risk Level** (0-3 points):
     - Low risk: 0.5 points
     - Medium risk: 1.5 points
     - High risk: 3.0 points

   - **Dependency Complexity** (0-2 points):
     - 0-1 new dependencies: 0 points
     - 2-3 new dependencies: 1 point
     - 4+ new dependencies: 2 points

4. **ERROR HANDLING**:
   - If ComplexityCalculationError: Default to score 5 (medium)
   - Set review_mode to FULL_REQUIRED (fail-safe)
   - Log error for debugging

5. Save ComplexityScore to:
   ```
   docs/state/{task_id}/complexity_score.json
   ```

**OUTPUT**: ComplexityScore object with total_score, factor_scores, review_mode

#### Step 3: Detect Force-Review Triggers

**OBJECTIVE**: Identify conditions that mandate full review regardless of complexity score

**TRIGGERS**:
- **USER_FLAG**: `--review` command-line flag present
- **SECURITY_KEYWORDS**: auth, password, encryption, token, session, oauth, jwt, crypto
- **BREAKING_CHANGES**: Public API modifications, interface changes
- **SCHEMA_CHANGES**: Database migrations, model changes
- **HOTFIX**: Task tagged as hotfix or production emergency

**ACTIONS**:
1. Check task title, description, and tags for security keywords
2. Check task metadata for `--review` flag
3. Check for database/schema file changes in plan
4. Check for public API file modifications
5. Check task priority and tags for hotfix indicators

**OUTPUT**: List of triggered conditions (empty list if none)

#### Step 4: Determine Review Mode

**OBJECTIVE**: Route to appropriate Phase 2.8 review handler

**ROUTING LOGIC**:
```python
if len(forced_review_triggers) > 0:
    review_mode = ReviewMode.FULL_REQUIRED
    reason = f"Force triggers: {', '.join(triggered)}"
elif complexity_score.total_score >= 7:
    review_mode = ReviewMode.FULL_REQUIRED
    reason = "High complexity (score >= 7)"
elif complexity_score.total_score >= 4:
    review_mode = ReviewMode.QUICK_OPTIONAL
    reason = "Medium complexity (score 4-6)"
else:
    review_mode = ReviewMode.AUTO_PROCEED
    reason = "Low complexity (score 1-3)"
```

**REVIEW MODES**:
- **AUTO_PROCEED**: No human review needed, proceed directly to Phase 3
- **QUICK_OPTIONAL**: 10-second countdown with optional escalation
- **FULL_REQUIRED**: Mandatory comprehensive human checkpoint

**OUTPUT**: ReviewMode enum and routing reason

#### Step 5: Update Task Metadata

**OBJECTIVE**: Persist Phase 2.7 results to task frontmatter

**METADATA FIELDS TO UPDATE**:
```yaml
implementation_plan:
  file_path: "docs/state/{task_id}/implementation_plan.json"
  generated_at: "{ISO 8601 timestamp}"
  version: 1
  approved: false  # Will be updated in Phase 2.8

complexity_evaluation:
  score: {complexity_score.total_score}
  level: "{low|medium|high}"
  file_path: "docs/state/{task_id}/complexity_score.json"
  calculated_at: "{ISO 8601 timestamp}"
  review_mode: "{auto_proceed|quick_optional|full_required}"
  forced_review_triggers: [{list of triggers}]
  factors:
    file_complexity: {score}
    pattern_familiarity: {score}
    risk_level: {score}
    dependency_complexity: {score}
```

**ACTIONS**:
1. Read current task file frontmatter
2. Merge new metadata fields
3. Write updated task file (atomic write)
4. Verify write succeeded

**ERROR HANDLING**:
- If metadata update fails: Log error, continue anyway
- Never block workflow on metadata failures

#### Step 6: Return Results to Phase 2.8

**OBJECTIVE**: Pass context to Phase 2.8 for review routing

**RETURN DATA**:
- **complexity_score**: ComplexityScore object
- **review_mode**: ReviewMode enum
- **implementation_plan_path**: Path to saved plan JSON
- **forced_triggers**: List of triggered conditions
- **task_context**: Updated TaskContext object

**DISPLAY SUMMARY**:
```
Phase 2.7 Complete: Plan Generated & Complexity Evaluated

Plan saved: docs/state/{task_id}/implementation_plan.json
Complexity Score: {score}/10 ({level})
Review Mode: {review_mode}
{If triggers: "Force Triggers: " + ", ".join(triggers)}
```

### 4. Phase 2.8: Human Plan Checkpoint (Complexity-Based Routing)

**WHEN INVOKED** for Phase 2.8, execute the following orchestration:

#### Routing Based on Review Mode

**RECEIVE** from Phase 2.7:
- complexity_score: ComplexityScore object
- review_mode: AUTO_PROCEED | QUICK_OPTIONAL | FULL_REQUIRED
- implementation_plan_path: Path to plan JSON
- task_context: TaskContext object

**ROUTE** to appropriate handler:

#### Path 1: Auto-Proceed (review_mode == AUTO_PROCEED)

**OBJECTIVE**: Skip human review for simple tasks, proceed directly to Phase 3

**ACTIONS**:
1. Display brief complexity summary:
   ```
   Auto-Proceed Mode (Low Complexity)

   Complexity: {score}/10 (Simple task)
   Files: {file_count} file(s)
   Tests: {test_count} tests planned
   Estimated: ~{duration} minutes

   Automatically proceeding to implementation (no review needed)...
   ```

2. Update task metadata:
   ```yaml
   implementation_plan:
     approved: true
     approved_by: "system"
     approved_at: "{ISO 8601 timestamp}"
     auto_approved: true
     review_mode: "auto_proceed"
   ```

3. Set proceed_to_phase_3 flag: true

4. Log auto-proceed decision with timestamp

**OUTPUT**: Proceed directly to Phase 3 (Implementation)

#### Path 2: Quick Optional Review (review_mode == QUICK_OPTIONAL)

**OBJECTIVE**: Offer optional 10-second review with escalation option

**ACTIONS**:
1. Load ImplementationPlan from JSON file

2. Display quick review summary card:
   ```
   Quick Review Mode (Medium Complexity)

   Complexity: {score}/10 ({level})
   Files: {new_count} new, {modified_count} modified
   Patterns: {pattern_list}
   Dependencies: {dependency_list}
   Estimated: ~{duration}

   Press ENTER to review in detail, 'c' to cancel
   Auto-approving in 10...9...8...
   ```

3. Invoke QuickReviewHandler (from review_modes.py):
   - Start 10-second countdown timer
   - Listen for user input:
     * **ENTER pressed** → Return 'escalate'
     * **'c' pressed** → Return 'cancel'
     * **Timeout (no input)** → Return 'timeout'

4. Handle result:

   **IF** result.action == 'timeout':
   - Display: "Quick review timed out. Auto-approving task..."
   - Update task metadata:
     ```yaml
     implementation_plan:
       approved: true
       approved_by: "timeout"
       approved_at: "{timestamp}"
       auto_approved: true
       review_mode: "quick_optional"
       review_duration_seconds: 10
     ```
   - Set proceed_to_phase_3: true
   - **PROCEED** to Phase 3

   **ELSE IF** result.action == 'escalate':
   - Display: "Escalating to full review mode..."
   - Update review_mode to FULL_REQUIRED
   - Set escalated flag: true
   - **FALL THROUGH** to Path 3 (Full Review) below

   **ELSE IF** result.action == 'cancel':
   - Display: "Task cancelled by user"
   - Update task metadata:
     ```yaml
     status: backlog
     cancelled: true
     cancelled_at: "{timestamp}"
     cancelled_reason: "User cancelled during quick review"
     ```
   - Move task file: in_progress/ → backlog/
   - **EXIT** task-work command

**ERROR HANDLING**:
- If QuickReviewHandler fails: Escalate to FULL_REQUIRED (fail-safe)
- If countdown timer fails: Default to timeout (auto-approve)
- If KeyboardInterrupt: Treat as cancellation

#### Path 3: Full Required Review (review_mode == FULL_REQUIRED or escalated)

**OBJECTIVE**: Mandatory comprehensive human checkpoint for high-complexity/high-risk tasks

**ACTIONS**:
1. Load full context:
   - ImplementationPlan from JSON
   - ComplexityScore from JSON
   - Task metadata
   - Architectural review results (from Phase 2.5B)

2. Display comprehensive checkpoint:
   ```
   ═══════════════════════════════════════════════════════
   PHASE 2.8 - IMPLEMENTATION PLAN CHECKPOINT
   ═══════════════════════════════════════════════════════

   TASK: {task_id} - {title}

   COMPLEXITY EVALUATION:
     Score: {score}/10 ({level})
     {If escalated: "Escalated from quick review"}
     {If triggers: "Force Triggers: " + triggers}

   COMPLEXITY BREAKDOWN:
     File Complexity: {file_score}/3 ({file_count} files)
     Pattern Familiarity: {pattern_score}/2 ({patterns})
     Risk Level: {risk_score}/3 ({risks})
     Dependencies: {dep_score}/2 ({dependencies})

   FILES TO CREATE ({new_count}):
     {List with purposes}

   FILES TO MODIFY ({modified_count}):
     {List with changes}

   PATTERNS IDENTIFIED:
     {List of design patterns}

   NEW DEPENDENCIES:
     {List of packages}

   RISKS:
     {List with severity and mitigation}

   IMPLEMENTATION PHASES:
     {List with time estimates}

   ARCHITECTURAL REVIEW (Phase 2.5B):
     Score: {arch_score}/100 ({status})
     {Summary of recommendations}

   ESTIMATED DURATION: {total_duration}

   OPTIONS:
   [A] Approve - Proceed to implementation
   [M] Modify - Edit plan (Coming soon - TASK-003B-3)
   [V] View - Show full plan in pager (Coming soon - TASK-003B-3)
   [Q] Question - Ask questions about plan (Coming soon - TASK-003B-4)
   [C] Cancel - Cancel task, return to backlog

   Your choice (A/M/V/Q/C):
   ═══════════════════════════════════════════════════════
   ```

3. Invoke FullReviewHandler (from review_modes.py):
   - Block waiting for user input
   - Validate input ('a', 'm', 'v', 'q', 'c')
   - Re-prompt on invalid input

4. Handle decision:

   **[A] Approve**:
   - Display: "Plan approved. Proceeding to implementation..."
   - Update task metadata:
     ```yaml
     implementation_plan:
       approved: true
       approved_by: "user"
       approved_at: "{timestamp}"
       review_mode: "full_required"
       escalated: {true if escalated}
       review_duration_seconds: {actual duration}
     ```
   - Set proceed_to_phase_3: true
   - **PROCEED** to Phase 3

   **[C] Cancel**:
   - Display confirmation prompt: "Are you sure? (y/n)"
   - If confirmed:
     - Display: "Task cancelled by user"
     - Update task metadata:
       ```yaml
       status: backlog
       cancelled: true
       cancelled_at: "{timestamp}"
       cancelled_reason: "User cancelled during full review"
       ```
     - Move task file: in_progress/ → backlog/
     - **EXIT** task-work command
   - If not confirmed:
     - Return to checkpoint prompt

   **[M] Modify** (STUBBED FOR MVP):
   - Display: "⚠️ Modification mode coming soon (TASK-003B-3)"
   - Display: "This will allow you to:"
   - Display: "  - Edit file list"
   - Display: "  - Adjust dependencies"
   - Display: "  - Modify risk mitigations"
   - Display: "  - Recalculate complexity"
   - Display: "Returning to checkpoint..."
   - **RE-PROMPT** for decision

   **[V] View** (STUBBED FOR MVP):
   - Display: "⚠️ View mode coming soon (TASK-003B-3)"
   - Display: "This will display the full plan in a pager"
   - Display: "Returning to checkpoint..."
   - **RE-PROMPT** for decision

   **[Q] Question** (STUBBED FOR MVP):
   - Display: "⚠️ Q&A mode coming soon (TASK-003B-4)"
   - Display: "This will allow you to ask questions about the plan"
   - Display: "Returning to checkpoint..."
   - **RE-PROMPT** for decision

**ERROR HANDLING**:
- If FullReviewHandler fails: Log error, allow retry
- If user input invalid: Re-prompt with error message
- If KeyboardInterrupt: Confirm cancellation before exiting

**NOTE**: Full implementation of [M]odify, [V]iew, and [Q]uestion options will be completed in:
- TASK-003B-3: Modification session with versioning
- TASK-003B-3: Plan viewer with pager
- TASK-003B-4: Q&A mode with context-aware responses

### 5. Micro-Task Workflow (NEW - TASK-020)

**Purpose**: Streamlined workflow for trivial tasks (typo fixes, doc updates, cosmetic changes) that don't require full architectural review.

**When Invoked**: When user runs `/task-work TASK-XXX --micro` or when micro-task auto-detection triggers.

#### Pre-Flight Validation

**BEFORE** starting micro-task workflow, validate task eligibility:

```python
from installer.core.commands.lib.micro_task_detector import MicroTaskDetector

detector = MicroTaskDetector()
analysis = detector.analyze(task_metadata)

if not analysis.can_use_micro_mode:
    print("Task does not qualify as micro-task:")
    for reason in analysis.blocking_reasons:
        print(f"  - {reason}")
    print("\nEscalating to full workflow...")
    # Execute standard workflow instead
    return execute_standard_workflow(task_id)
```

**BLOCKING REASONS** that prevent micro-task mode:
- Multiple files affected (>1 file, unless docs-only)
- High complexity (>1/10)
- High-risk keywords detected (security, database, API, breaking changes)
- Estimated effort ≥1 hour

#### Micro-Task Workflow Execution

**PHASES EXECUTED**:

**Phase 1: Load Task Context** (standard)
- Load task file from tasks/{state}/{task_id}.md
- Parse frontmatter metadata
- Validate task is in appropriate state

**Phase 3: Implementation** (simplified)
- Generate minimal implementation based on task description
- Apply changes to files
- NO architectural review (skipped in micro-task mode)

**Phase 4: Quick Testing** (lightweight)
- Quality Gate 1: Compilation Check (REQUIRED)
  - Run appropriate compiler/interpreter for tech stack
  - MUST pass, blocks on failure
- Quality Gate 2: Tests Pass (REQUIRED, but NO coverage)
  - Run test suite (same as standard)
  - Coverage collection SKIPPED (faster execution)
  - MUST pass, blocks on failure

**Phase 4.5: Fix Loop** (limited)
- Max 1 fix attempt (vs 3 in standard workflow)
- ONLY if tests failed (skip if compilation failed)
- If fix fails after 1 attempt, escalate to blocked state

**Phase 5: Quick Review** (lint only)
- Quality Gate 3: Lint Check (REQUIRED)
  - Run linter for tech stack
  - MUST pass, warns on failure
- SKIP comprehensive review (SOLID/DRY/YAGNI analysis)
- SKIP architectural review

**PHASES SKIPPED**:
- Phase 2: Implementation Planning
- Phase 2.5A: Pattern Suggestion
- Phase 2.5B: Architectural Review
- Phase 2.6: Human Checkpoint
- Phase 2.7: Complexity Evaluation

#### Quality Gates Summary

| Gate | Standard Workflow | Micro-Task Workflow |
|------|------------------|---------------------|
| Compilation | REQUIRED | REQUIRED |
| Tests Pass | REQUIRED | REQUIRED |
| Coverage (80%+) | REQUIRED | **SKIPPED** |
| Architectural Review | REQUIRED | **SKIPPED** |
| Code Review (SOLID/DRY) | REQUIRED | **SKIPPED** |
| Lint Check | Optional | REQUIRED |

#### Auto-Detection Behavior

**WHEN**: User runs `/task-work TASK-XXX` (without --micro flag)

**DETECT**: Analyze task metadata for micro-task eligibility

```python
suggestion = detector.suggest_micro_mode(task_metadata)

if suggestion and analysis.confidence_score >= 0.9:
    print(suggestion)
    print("Auto-apply micro-mode? [y/N] (10s timeout): ", end="", flush=True)

    # Wait for user input with 10-second timeout
    try:
        import select
        rlist, _, _ = select.select([sys.stdin], [], [], 10)
        if rlist:
            response = sys.stdin.readline().strip().lower()
            if response in ['y', 'yes']:
                print("Applying micro-task mode...")
                return execute_micro_workflow(task_id)
    except:
        pass  # Timeout or error, continue with standard workflow

    print("Continuing with standard workflow...")
    return execute_standard_workflow(task_id)
```

**TIMEOUT BEHAVIOR**:
- 10-second timeout for user response
- Default: NO (continue with standard workflow)
- Prevents blocking on unattended execution

#### Documentation-Only Exception

**SPECIAL CASE**: Tasks affecting only documentation files automatically qualify for micro-task mode:

```python
DOC_EXTENSIONS = {'.md', '.txt', '.rst', '.adoc', '.pdf', '.docx'}

def is_doc_only(files):
    return all(Path(f).suffix.lower() in DOC_EXTENSIONS for f in files)

if is_doc_only(task_files):
    # Override blocking reasons
    analysis.is_micro_task = True
    analysis.blocking_reasons = []
    analysis.confidence_score = 0.95
```

#### Integration Points

**Entry Point**: `task-work.md` command file
- Parse `--micro` flag from command line
- Validate flag with `MicroTaskDetector.validate_micro_mode()`
- Route to `MicroTaskWorkflow.execute()` if valid

**Workflow Executor**: `micro_task_workflow.py`
- Executes streamlined phases
- Enforces minimal quality gates
- Returns `MicroWorkflowResult`

**State Transition**: Same as standard workflow
- BACKLOG → IN_PROGRESS → IN_REVIEW (if quality gates pass)
- BACKLOG → IN_PROGRESS → BLOCKED (if quality gates fail)

**Logging**: Use standard logging with `[MICRO]` prefix
```python
logger.info(f"[MICRO] Starting micro-task workflow for {task_id}")
logger.debug(f"[MICRO] Skipping Phase 2-2.7 (micro-task mode)")
logger.info(f"[MICRO] Completed in {duration:.2f} minutes")
```

#### Example Execution Flow

```
/task-work TASK-047 --micro

Micro-Task Mode Enabled
Validation: PASSED (confidence: 95%)

Phase 1: Load Task Context                        [0.3s]
  ✓ Loaded TASK-047
  ✓ Title: Fix typo in error message
  ✓ File: src/services/AuthService.py

Phases 2-2.7: SKIPPED (micro-task mode)

Phase 3: Implementation                           [1.2s]
  ✓ Updated src/services/AuthService.py:45
  ✓ Changed 'occured' → 'occurred'

Phase 4: Quick Testing                            [0.8s]
  ✓ Compilation: PASSED
  ✓ Tests: 5/5 PASSED (coverage skipped)

Phase 4.5: Fix Loop                               [SKIPPED - tests passed]

Phase 5: Quick Review                             [0.4s]
  ✓ Lint: PASSED (no issues)

Quality Gates: 3/3 PASSED
Task State: BACKLOG → IN_REVIEW
Duration: 2 minutes 34 seconds

Next Steps:
  1. Review: /task-review TASK-047
  2. Complete: /task-complete TASK-047
```

### 6. Design-First Workflow Integration (TASK-006)

**Phase 2.8 Conditional Routing**: When invoked for Phase 2.8, route based on workflow mode:

#### Design-Only Mode (--design-only flag)
- Execute Phase 2.8 checkpoint with design-focused prompts
- On approval:
  - Save implementation plan using `plan_persistence.save_plan()`
  - Update task frontmatter with design metadata
  - Move task to `tasks/design_approved/` state
  - Display design approval report
  - EXIT (do not proceed to Phase 3)

#### Implement-Only Mode (--implement-only flag)
- Validate task is in `design_approved` state
- Load saved plan using `plan_persistence.load_plan()`
- Display implementation start context
- Move task from `design_approved` to `in_progress`
- Skip to Phase 3 (implementation) using saved plan

#### Standard Mode (no flags)
- Execute Phase 2.8 as normal (complexity-based routing)
- Continue to Phase 3 if approved

**Integration Points**:
- Import: `from installer.core.commands.lib.phase_execution import execute_phases`
- Import: `from installer.core.commands.lib.plan_persistence import save_plan, load_plan, plan_exists`
- Import: `from installer.core.commands.lib.flag_validator import validate_flags`

**State Transitions**:
- `backlog` → `design_approved` (design-only approval)
- `design_approved` → `in_progress` (implement-only start)
- `design_approved` → `blocked` (implement-only failure)

### 6. Implement Task (Phase 3)
- Generate implementation based on requirements
- Create comprehensive test suite
- Document implementation decisions
- Move to in_testing/

### 7. Test Task (CRITICAL)
```bash

# For Python projects
pytest tests/ -v --cov=src --cov-report=term

# For TypeScript/React projects
npm test -- --coverage

# For .NET projects
dotnet test --collect:"XPlat Code Coverage"

# For Playwright tests
npx playwright test
```

Capture results:
- Total tests run
- Tests passed/failed
- Code coverage percentage
- Execution time
- Error details if any

### 8. Review Task
- Verify all tests are passing
- Check coverage meets threshold (≥80%)
- Validate acceptance criteria
- Move to in_review/

### 9. Complete Task
- Final verification of test results
- Archive to completed/ with timestamp
- Update project metrics


## Quality Gates

### Automatic Blocking Conditions
- Test coverage < 80%
- Any test failures
- Missing required tests
- Incomplete acceptance criteria
- Unresolved dependencies

### Test Verification Process
1. **Execute Tests**: Run all relevant test suites
2. **Capture Results**: Parse test output for metrics
3. **Update Metadata**: Store results in task file
4. **Evaluate Gates**: Check against quality thresholds
5. **Determine State**: Pass → review, Fail → blocked


## Related Agents

### Integration Architecture

```yaml
task-manager:
  role: Workflow Orchestrator
  responsibilities:
    - Task lifecycle management
    - Quality gate enforcement
    - Sub-agent coordination
    - State transition tracking

  delegates_to:
    - test-orchestrator:
        phase: 4
        purpose: Execute tests and collect metrics
        handoff_format: test_execution_request.json

    - test-verifier:
        phase: 4.5
        purpose: Verify test results meet quality gates
        handoff_format: test_verification_request.json

    - code-reviewer:
        phase: 5
        purpose: Comprehensive code review and Plan Audit
        handoff_format: code_review_request.json

    - architectural-reviewer:
        phase: 2.5B
        purpose: Architecture compliance check
        handoff_format: architecture_review_request.json

    - debugging-specialist:
        trigger: blocked_state
        purpose: Diagnose and resolve blockers
        handoff_format: debug_request.json
```

### Collaboration Flow: Full Task Workflow

```yaml
workflow:
  phase_1_load:
    agent: task-manager
    action: Load task context and validate state
    output: task_context.json

  phase_2_planning:
    agent: task-manager
    action: Generate implementation plan
    output: implementation_plan.json

  phase_2_5b_architecture:
    agent: architectural-reviewer
    input: implementation_plan.json
    action: Review architecture compliance
    output: architecture_review.json

  phase_2_7_complexity:
    agent: task-manager
    input: implementation_plan.json
    action: Calculate complexity score
    output: complexity_score.json

  phase_2_8_checkpoint:
    agent: task-manager
    inputs: [complexity_score.json, architecture_review.json]
    action: Human checkpoint (complexity-based routing)
    decision:
      - auto_proceed: score < 4
      - quick_optional: score 4-6
      - full_required: score ≥ 7

  phase_3_implementation:
    agent: task-manager
    input: approved_plan.json
    action: Generate implementation code
    output: implementation_result.json

  phase_4_testing:
    agent: test-orchestrator
    input: implementation_result.json
    action: Execute test suite
    output: test_results.json

  phase_4_5_verification:
    agent: test-verifier
    input: test_results.json
    action: Verify quality gates
    decision:
      - pass: proceed to Phase 5
      - fail: fix loop (max 3 attempts)
      - blocked: escalate to debugging-specialist

  phase_5_review:
    agent: code-reviewer
    inputs: [implementation_result.json, test_results.json]
    action: Code review + Plan Audit
    output: review_report.json

  phase_5_5_plan_audit:
    agent: code-reviewer
    inputs: [implementation_plan.json, implementation_result.json]
    action: Verify implementation matches plan
    output: plan_audit_report.json
```

### Handoff Payload: task-manager → test-orchestrator

```json
{
  "handoff_type": "test_execution_request",
  "source": "task-manager",
  "target": "test-orchestrator",
  "phase": 4,
  "agent_context": {
    "documentation_level": "standard",
    "complexity_score": 6,
    "task_id": "TASK-042",
    "stack": "python",
    "phase": 4
  },
  "test_config": {
    "task_id": "TASK-042",
    "technology_stack": "python",
    "test_framework": "pytest",
    "test_directories": ["tests/unit", "tests/integration"],
    "coverage_threshold": 80,
    "timeout_seconds": 300
  },
  "files_to_test": [
    "src/services/auth_service.py",
    "src/api/auth_endpoints.py"
  ],
  "quality_gates": {
    "min_coverage": 80,
    "max_failures": 0,
    "required_test_types": ["unit", "integration"]
  }
}
```

### Handoff Payload: test-orchestrator → task-manager

```json
{
  "handoff_type": "test_execution_result",
  "source": "test-orchestrator",
  "target": "task-manager",
  "phase": 4,
  "test_results": {
    "status": "passed",
    "total_tests": 24,
    "passed": 24,
    "failed": 0,
    "skipped": 0,
    "coverage": {
      "overall": 87.5,
      "files": {
        "src/services/auth_service.py": 92,
        "src/api/auth_endpoints.py": 83
      }
    },
    "execution_time_seconds": 45,
    "test_types_executed": ["unit", "integration"]
  },
  "quality_gate_results": {
    "coverage_gate": {"passed": true, "actual": 87.5, "threshold": 80},
    "failure_gate": {"passed": true, "actual": 0, "threshold": 0},
    "test_type_gate": {"passed": true, "required": ["unit", "integration"], "executed": ["unit", "integration"]}
  }
}
```

### Handoff Payload: task-manager → architectural-reviewer

```json
{
  "handoff_type": "architecture_review_request",
  "source": "task-manager",
  "target": "architectural-reviewer",
  "phase": "2.5B",
  "agent_context": {
    "documentation_level": "standard",
    "complexity_score": 6,
    "task_id": "TASK-042",
    "stack": "python",
    "phase": "2.5B"
  },
  "review_scope": {
    "task_id": "TASK-042",
    "implementation_plan_path": "docs/state/TASK-042/implementation_plan.json",
    "technology_stack": "python",
    "patterns_to_validate": ["Repository", "Service Layer", "Dependency Injection"],
    "files_planned": [
      {"path": "src/services/auth_service.py", "purpose": "Authentication business logic"},
      {"path": "src/api/auth_endpoints.py", "purpose": "FastAPI endpoints"}
    ]
  },
  "validation_criteria": {
    "solid_compliance": true,
    "dry_violations_max": 0,
    "cyclomatic_complexity_max": 10,
    "coupling_score_max": 5
  }
}
```

### Handoff Payload: task-manager → debugging-specialist

```json
{
  "handoff_type": "debug_request",
  "source": "task-manager",
  "target": "debugging-specialist",
  "trigger": "blocked_state",
  "agent_context": {
    "documentation_level": "standard",
    "complexity_score": 6,
    "task_id": "TASK-042",
    "stack": "python",
    "phase": "4.5"
  },
  "blocked_context": {
    "task_id": "TASK-042",
    "blocked_reason": "Test failures after 3 fix attempts",
    "failure_details": {
      "test_file": "tests/integration/test_auth_flow.py",
      "test_name": "test_token_refresh",
      "error_type": "AssertionError",
      "error_message": "Expected 200, got 401",
      "stack_trace": "..."
    },
    "fix_attempts": [
      {"attempt": 1, "change": "Fixed token expiry check", "result": "Same error"},
      {"attempt": 2, "change": "Added refresh token logic", "result": "Same error"},
      {"attempt": 3, "change": "Updated middleware order", "result": "Same error"}
    ]
  },
  "requested_actions": [
    "Root cause analysis",
    "Reproduction steps",
    "Fix recommendation"
  ]
}
```

### When to Invoke Related Agents

#### test-orchestrator
**Invoke when:**
- Phase 4: Test execution required
- Task has implementation changes to validate
- Coverage metrics needed

**Do NOT invoke when:**
- Task is documentation-only (no code changes)
- Micro-task mode with lint-only review

#### test-verifier
**Invoke when:**
- Phase 4.5: Test results need quality gate verification
- Fix loop iteration needed
- Test failure triage required

**Do NOT invoke when:**
- Tests haven't been executed yet
- Quality gates already passed

#### code-reviewer
**Invoke when:**
- Phase 5: Implementation complete, tests passing
- Phase 5.5: Plan Audit required (scope creep detection)
- Complex changes requiring SOLID/DRY analysis

**Do NOT invoke when:**
- Tests still failing (Phase 4.5 not complete)
- Micro-task mode (lint-only review)

#### architectural-reviewer
**Invoke when:**
- Phase 2.5B: Implementation plan needs architecture validation
- Complex patterns detected in plan
- High-complexity tasks (score ≥ 7)

**Do NOT invoke when:**
- Micro-task mode (architecture review skipped)
- Simple tasks (score 1-3, auto-proceed mode)

#### debugging-specialist
**Invoke when:**
- Task blocked after 3 fix attempts
- Root cause analysis needed
- Test failures require systematic debugging

**Do NOT invoke when:**
- First fix attempt (try simpler fixes first)
- Test failures are configuration issues (handle locally)

---


## Workflow State Diagrams

### Standard Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           STANDARD WORKFLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   BACKLOG ─────────────────────────────────────────────────► IN_PROGRESS    │
│      │                                                            │          │
│      │  /task-work TASK-XXX                                       │          │
│      │                                                            ▼          │
│      │                                              ┌─────────────────────┐  │
│      │                                              │ Phase 2: Planning   │  │
│      │                                              │ Phase 2.5B: Arch    │  │
│      │                                              │ Phase 2.7: Eval     │  │
│      │                                              │ Phase 2.8: Review   │  │
│      │                                              └──────────┬──────────┘  │
│      │                                                         │             │
│      │                                              ┌──────────▼──────────┐  │
│      │                                              │ Phase 3: Implement  │  │
│      │                                              └──────────┬──────────┘  │
│      │                                                         │             │
│      │                                                         ▼             │
│      │                                                    IN_TESTING        │
│      │                                                         │             │
│      │                                              ┌──────────▼──────────┐  │
│      │                                              │ Phase 4: Tests      │  │
│      │                                              │ Phase 4.5: Verify   │  │
│      │                                              └──────────┬──────────┘  │
│      │                                                         │             │
│      │                     ┌───────────────────────────────────┼────────┐    │
│      │                     │                                   │        │    │
│      │                     ▼                                   ▼        │    │
│      │                 BLOCKED ◄───────────────────────── IN_REVIEW     │    │
│      │                     │                                   │        │    │
│      │                     │ debugging-specialist              │        │    │
│      │                     │                                   ▼        │    │
│      │                     └─────────────────────────────► COMPLETED    │    │
│      │                                                                  │    │
│      └──────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Design-First Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        DESIGN-FIRST WORKFLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   BACKLOG ──────► DESIGN_APPROVED ──────► IN_PROGRESS ──────► COMPLETED     │
│      │                   │                     │                  │          │
│      │                   │                     │                  │          │
│      ▼                   ▼                     ▼                  ▼          │
│  --design-only       Plan saved           --implement-only    Tests pass    │
│  Phase 2-2.8          to JSON              Phase 3-5                        │
│                                                                              │
│   Timeline Example:                                                          │
│   ─────────────────                                                          │
│   Day 1: /task-work TASK-042 --design-only                                  │
│          → Design reviewed and approved                                      │
│          → Task moves to design_approved/                                   │
│                                                                              │
│   Day 2: /task-work TASK-042 --implement-only                               │
│          → Loads saved plan                                                  │
│          → Implements and tests                                              │
│          → Task moves to completed/                                          │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Micro-Task Workflow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MICRO-TASK WORKFLOW                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   BACKLOG ──────────────────────────────────────────────────► IN_REVIEW     │
│      │                                                            │          │
│      │  /task-work TASK-XXX --micro                               │          │
│      │                                                            ▼          │
│      │  ┌──────────────────────────────────────────────────┐  COMPLETED     │
│      │  │ Phase 1: Load Context              [0.3s]        │                 │
│      │  │ Phase 2-2.7: SKIPPED               [0s]          │                 │
│      │  │ Phase 3: Quick Implementation      [1-2min]      │                 │
│      │  │ Phase 4: Quick Testing             [<1min]       │                 │
│      │  │   - Compilation: REQUIRED                        │                 │
│      │  │   - Tests: REQUIRED (no coverage)                │                 │
│      │  │ Phase 5: Lint Only                 [<30s]        │                 │
│      │  └──────────────────────────────────────────────────┘                 │
│      │                                                                       │
│      │  Total: ~3 minutes (vs 20+ minutes standard)                         │
│      │                                                                       │
│      │  Eligible Tasks:                                                      │
│      │  ✓ Typo fixes                                                        │
│      │  ✓ Comment updates                                                   │
│      │  ✓ Single-file cosmetic changes                                      │
│      │  ✓ Documentation-only changes                                        │
│      │                                                                       │
│      │  NOT Eligible:                                                        │
│      │  ✗ Multi-file changes                                                │
│      │  ✗ API changes                                                       │
│      │  ✗ Security-related changes                                          │
│      │  ✗ Database schema changes                                           │
│      │                                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Blocked Task Recovery

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       BLOCKED TASK RECOVERY                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   BLOCKED                                                                    │
│      │                                                                       │
│      ├──────► Test Failures?                                                │
│      │             │                                                         │
│      │             ├── Attempt 1: Auto-fix ──► Re-test ──► Pass? ──► Resume │
│      │             │                                  │                      │
│      │             │                                  └──► Fail ─┐           │
│      │             │                                             │           │
│      │             ├── Attempt 2: Smart-fix ──► Re-test ──► Pass? ──► Resume│
│      │             │                                    │                    │
│      │             │                                    └──► Fail ─┐         │
│      │             │                                               │         │
│      │             ├── Attempt 3: Context-fix ──► Re-test ──► Pass? ──► Resume
│      │             │                                      │                  │
│      │             │                                      └──► Fail ─┐       │
│      │             │                                                 │       │
│      │             └── debugging-specialist ◄────────────────────────┘       │
│      │                        │                                              │
│      │                        ├── Root cause identified ──► Fix ──► Resume  │
│      │                        │                                              │
│      │                        └── Requires human intervention ──► ASK USER  │
│      │                                                                       │
│      ├──────► Dependency Blocked?                                           │
│      │             │                                                         │
│      │             ├── Dependency available ──► Resume                      │
│      │             │                                                         │
│      │             └── Dependency unavailable ──► Document ──► Wait         │
│      │                                                                       │
│      └──────► Architecture Rejection?                                       │
│                    │                                                         │
│                    ├── Revise plan ──► Re-review ──► Pass? ──► Resume       │
│                    │                                                         │
│                    └── User override ──► Proceed with warning               │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---


## Quality Gate Enforcement Examples

### Test Verification Before Completion

#### ✅ DO: Always Verify Tests Before Completion
```python

# task_manager.py - Completion check
async def complete_task(task_id: str) -> TaskResult:
    task = await load_task(task_id)

    # ALWAYS verify tests before completion
    test_results = task.metadata.get("test_results", {})

    if test_results.get("status") != "passed":
        return TaskResult(
            success=False,
            error="Cannot complete task: Tests not passing",
            action="Run /task-test {task_id} first"
        )

    if test_results.get("coverage", 0) < 80:
        return TaskResult(
            success=False,
            error=f"Cannot complete task: Coverage {test_results['coverage']}% < 80%",
            action="Add more tests to increase coverage"
        )

    # All gates passed - proceed with completion
    await move_task(task_id, "completed")
    return TaskResult(success=True, message="Task completed successfully")
```

#### ❌ DON'T: Skip Test Verification
```python

# BAD: task_manager.py - Skipping verification
async def complete_task(task_id: str) -> TaskResult:
    task = await load_task(task_id)

    # BAD: No test verification!
    # This allows untested code to be marked complete

    await move_task(task_id, "completed")
    return TaskResult(success=True)
```

---

### Coverage Threshold Enforcement

#### ✅ DO: Enforce Coverage with Context
```python

# quality_gates.py - Coverage with context
async def verify_coverage(test_results: dict, task: Task) -> GateResult:
    coverage = test_results.get("coverage", {}).get("overall", 0)
    threshold = 80  # Default threshold

    # Context-aware threshold adjustment
    if task.is_legacy_code:
        threshold = 60  # Lower threshold for legacy
        logger.info(f"Legacy code: threshold adjusted to {threshold}%")

    if coverage < threshold:
        return GateResult(
            passed=False,
            message=f"Coverage {coverage}% below threshold {threshold}%",
            recommendations=[
                f"Add tests for uncovered files: {test_results['coverage']['uncovered_files']}",
                "Focus on critical paths first",
                "Consider integration tests for edge cases"
            ]
        )

    return GateResult(
        passed=True,
        message=f"Coverage {coverage}% meets threshold {threshold}%"
    )
```

#### ❌ DON'T: Hardcode or Skip Coverage Checks
```python

# BAD: quality_gates.py - Hardcoded bypass
async def verify_coverage(test_results: dict, task: Task) -> GateResult:
    # BAD: Hardcoded bypass for "simple" tasks
    if "simple" in task.tags:
        return GateResult(passed=True)  # Skipping coverage check!

    # BAD: No actionable feedback
    if test_results["coverage"]["overall"] < 80:
        return GateResult(passed=False, message="Coverage too low")
```

---

### Complexity-Based Routing

#### ✅ DO: Route Based on Calculated Complexity
```python

# phase_2_8.py - Complexity-based routing
async def route_checkpoint(task: Task, complexity: ComplexityScore) -> CheckpointResult:
    # Check for force triggers first (always full review)
    if has_security_keywords(task) or task.has_flag("--review"):
        return CheckpointResult(
            mode=ReviewMode.FULL_REQUIRED,
            reason="Force trigger: security keywords detected"
        )

    # Route based on calculated complexity
    if complexity.total_score >= 7:
        return CheckpointResult(
            mode=ReviewMode.FULL_REQUIRED,
            reason=f"High complexity: {complexity.total_score}/10"
        )
    elif complexity.total_score >= 4:
        return CheckpointResult(
            mode=ReviewMode.QUICK_OPTIONAL,
            reason=f"Medium complexity: {complexity.total_score}/10"
        )
    else:
        return CheckpointResult(
            mode=ReviewMode.AUTO_PROCEED,
            reason=f"Low complexity: {complexity.total_score}/10"
        )
```

#### ❌ DON'T: Skip Checkpoints for High-Complexity Tasks
```python

# BAD: phase_2_8.py - Bypassing complexity routing
async def route_checkpoint(task: Task, complexity: ComplexityScore) -> CheckpointResult:
    # BAD: Always auto-proceed regardless of complexity
    return CheckpointResult(
        mode=ReviewMode.AUTO_PROCEED,
        reason="Skipping checkpoint for speed"
    )

    # BAD: Hardcoded complexity score
    complexity_score = 3  # Always low!
```

---

### Phase Checkpoint Handling

#### ✅ DO: Handle All Checkpoint Outcomes
```python

# phase_2_8.py - Complete checkpoint handling
async def handle_full_review(task: Task, plan: ImplementationPlan) -> ReviewResult:
    display_checkpoint(task, plan)

    while True:
        choice = await get_user_input("Your choice (A/M/V/Q/C): ")

        if choice.lower() == 'a':
            # Approve - proceed to implementation
            await update_task_metadata(task, {
                "implementation_plan.approved": True,
                "implementation_plan.approved_by": "user",
                "implementation_plan.approved_at": datetime.now().isoformat()
            })
            return ReviewResult(action="proceed", phase=3)

        elif choice.lower() == 'c':
            # Cancel - confirm and return to backlog
            if await confirm_cancellation():
                await move_task(task.id, "backlog")
                await update_task_metadata(task, {
                    "cancelled": True,
                    "cancelled_reason": "User cancelled during review"
                })
                return ReviewResult(action="cancel")
            continue  # Re-prompt if not confirmed

        elif choice.lower() in ['m', 'v', 'q']:
            # Stubbed options - inform and re-prompt
            print(f"⚠️ Option '{choice}' coming soon")
            continue

        else:
            print("Invalid choice. Please enter A, M, V, Q, or C.")
```

#### ❌ DON'T: Ignore User Decisions
```python

# BAD: phase_2_8.py - Ignoring user input
async def handle_full_review(task: Task, plan: ImplementationPlan) -> ReviewResult:
    display_checkpoint(task, plan)

    # BAD: Auto-approve without waiting for user
    return ReviewResult(action="proceed", phase=3)

    # BAD: No cancellation option
    choice = await get_user_input("Press Enter to continue: ")
    return ReviewResult(action="proceed", phase=3)
```

---

### Quality Gate Violation Recovery

#### ✅ DO: Provide Actionable Recovery Guidance
```python

# quality_gates.py - Recovery with guidance
async def handle_gate_violation(violation: GateViolation, task: Task) -> RecoveryPlan:
    if violation.gate == "coverage":
        uncovered = violation.details.get("uncovered_files", [])
        return RecoveryPlan(
            action="add_tests",
            guidance=[
                f"Add unit tests for: {', '.join(uncovered[:3])}",
                "Focus on functions with highest cyclomatic complexity",
                f"Current coverage: {violation.actual}%, target: {violation.threshold}%"
            ],
            commands=[
                f"pytest --cov=src --cov-report=html  # View coverage report",
                f"pytest {uncovered[0]} -v  # Run tests for first uncovered file"
            ]
        )

    elif violation.gate == "test_failures":
        failed_tests = violation.details.get("failed_tests", [])
        return RecoveryPlan(
            action="fix_tests",
            guidance=[
                f"Fix failing tests: {', '.join(failed_tests[:3])}",
                "Check test logs for assertion errors",
                "Verify test fixtures are up to date"
            ],
            commands=[
                f"pytest {failed_tests[0]} -v --tb=long  # Run with full traceback",
                "pytest --lf  # Re-run only failed tests"
            ]
        )
```

#### ❌ DON'T: Block Without Recovery Path
```python

# BAD: quality_gates.py - Unhelpful blocking
async def handle_gate_violation(violation: GateViolation, task: Task) -> RecoveryPlan:
    # BAD: No guidance, just blocks
    return RecoveryPlan(
        action="blocked",
        guidance=["Tests failed"],  # Not helpful!
        commands=[]  # No recovery commands!
    )
```


## Extended Documentation

For detailed examples, patterns, and implementation guides, load the extended documentation:

```bash
cat task-manager-ext.md
```

Or in Claude Code:
```
Please read task-manager-ext.md for detailed examples.
```
