# Architectural Review: Feature-Build Quality Gates Integration (REVISION 3)

**Task ID**: TASK-REV-B601
**Review Mode**: Architectural
**Review Depth**: Comprehensive
**Date**: 2025-12-29
**Reviewer**: Claude Code (Architectural Review Agent)
**Revision**: 3 (Hybrid: Player-Coach + Task-Work Quality Gates)

---

## Executive Summary

**REVISION 3 APPROACH**: Combine the **adversarial cooperation pattern** (Player-Coach) with **task-work quality gates** to create a hybrid system that achieves both autonomous execution AND comprehensive quality enforcement.

### Key Insight from Research

The Block AI Research paper demonstrates that adversarial cooperation (player-coach dyad) achieves **5/5 completeness** vs **1-4.5/5** for single-agent approaches. This pattern is NOT optional - the ablation study proved that without coach feedback, implementations fail despite passing tests.

**However**, the current Player-Coach implementation lacks the quality gates that task-work provides (architectural review, complexity routing, test enforcement, plan audit).

**Solution**: **Enhance** the Player-Coach loop with task-work quality gate phases, don't replace it.

---

## Research Foundation

### From Block AI Research

**Core Pattern**: Two specialized agents in bounded adversarial cooperation:

```
┌─────────────────────────────────────────────────────────────┐
│                    DIALECTICAL LOOP                         │
│                                                             │
│   PLAYER                              COACH                 │
│   • Implement                         • Review              │
│   • Create          ──feedback──►     • Test                │
│   • Execute         ◄──────────       • Critique            │
│   • Iterate                           • Approve             │
│                                                             │
│                      WORKSPACE                              │
│       Bounds: Max Turns, Fresh Context, Requirements        │
└─────────────────────────────────────────────────────────────┘
```

**Why It Works**:
1. **Requirements Contract**: Both agents use same source of truth
2. **Fresh Context Each Turn**: New agent instances prevent context pollution
3. **Adversarial Validation**: Coach's independent evaluation catches player's false successes
4. **Bounded Process**: Turn limits, approval gates, shared requirements

**Empirical Result**: g3 achieved 5/5 completeness using this pattern.

**Ablation Study**: When coach feedback withheld, player produced non-functional code despite claiming success.

### From GuardKit Task-Work

**Quality Gates**: 10-phase workflow ensures production quality:

| Phase | Description | Purpose |
|-------|-------------|---------|
| 1.6 | Clarifying Questions | Reduce rework by 15% |
| 2 | Implementation Planning | Document approach |
| 2.5A | Pattern Suggestion | MCP-based design patterns |
| 2.5B | Architectural Review | SOLID/DRY/YAGNI scoring |
| 2.7 | Complexity Evaluation | Route to appropriate review mode |
| 2.8 | Human Checkpoint | Approval for complex tasks |
| 3 | Implementation | Write code |
| 4 | Testing | Compilation + coverage |
| 4.5 | Test Enforcement Loop | Auto-fix up to 3 attempts |
| 5 | Code Review | Structural review |
| 5.5 | Plan Audit | Scope creep detection |

**Key Thresholds**:
- Compilation: 100% required
- Tests pass: 100% (auto-fix up to 3 attempts)
- Line coverage: ≥80%
- Branch coverage: ≥75%
- Architectural score: ≥60/100
- Plan variance: ≤20%

---

## The Hybrid Approach: Player-Coach + Quality Gates

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│              HYBRID FEATURE-BUILD ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Feature Orchestration (feature-build)                         │
│  ├── Load FEAT-XXX.yaml                                         │
│  ├── Create feature worktree                                    │
│  └── For each wave:                                             │
│      └── For each task in wave:                                 │
│          │                                                       │
│          └── ENHANCED PLAYER-COACH LOOP                         │
│              │                                                   │
│              ├── PRE-LOOP: Quality Gate Setup                   │
│              │   ├── Phase 1.6: Clarifying Questions            │
│              │   ├── Phase 2: Requirements Analysis             │
│              │   ├── Phase 2.5A: Pattern Suggestions            │
│              │   ├── Phase 2.5B: Architectural Review (plan)    │
│              │   ├── Phase 2.7: Complexity Evaluation           │
│              │   └── Phase 2.8: Human Checkpoint (if needed)    │
│              │                                                   │
│              ├── ADVERSARIAL LOOP (Turns 1-N)                   │
│              │   │                                               │
│              │   ├── Turn N:                                     │
│              │   │   │                                           │
│              │   │   ├─► PLAYER                                 │
│              │   │   │   ├── Fresh context (requirements + feedback) │
│              │   │   │   ├── Phase 3: Implementation            │
│              │   │   │   ├── Phase 4: Testing                   │
│              │   │   │   ├── Write report                       │
│              │   │   │   └── (no self-declaration of success)   │
│              │   │   │                                           │
│              │   │   ├─► COACH                                  │
│              │   │   │   ├── Fresh context (requirements + implementation) │
│              │   │   │   ├── Phase 4.5: Test Enforcement        │
│              │   │   │   │   ├── Independent test execution     │
│              │   │   │   │   ├── Coverage measurement           │
│              │   │   │   │   └── Auto-fix if needed (3 attempts)│
│              │   │   │   ├── Phase 5: Code Review               │
│              │   │   │   │   ├── Architectural compliance check │
│              │   │   │   │   ├── Code quality assessment        │
│              │   │   │   │   └── Edge case verification         │
│              │   │   │   ├── Write decision (APPROVE/FEEDBACK)  │
│              │   │   │   └── If FEEDBACK: Specific issues list  │
│              │   │   │                                           │
│              │   │   └── If APPROVED → Exit loop                │
│              │   │       If FEEDBACK → Continue to Turn N+1     │
│              │   │       If MAX_TURNS → Escalate to human       │
│              │   │                                               │
│              │   └── (Repeat until APPROVED or MAX_TURNS)       │
│              │                                                   │
│              └── POST-LOOP: Quality Gate Finalization           │
│                  └── Phase 5.5: Plan Audit                      │
│                      ├── Compare files created vs planned       │
│                      ├── Calculate LOC variance                 │
│                      ├── Detect scope creep                     │
│                      └── Escalate if variance > 20%             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Key Integration Points

#### 1. PRE-LOOP Quality Gates (Phases 1.6 - 2.8)

**Execute BEFORE adversarial loop starts**:

```python
def feature_build_task(task_id: str, worktree_path: str):
    """Enhanced Player-Coach with quality gates."""

    # PRE-LOOP: Setup quality gates
    print("Phase 1.6: Clarifying Questions")
    if should_ask_questions(task_id):
        clarifications = ask_clarifying_questions(task_id)
        save_clarifications(task_id, clarifications)

    print("Phase 2: Requirements Analysis")
    requirements = load_task_requirements(task_id)
    plan = create_implementation_plan(task_id, requirements)

    print("Phase 2.5A: Pattern Suggestions")
    patterns = suggest_design_patterns(task_id, requirements)
    update_plan_with_patterns(plan, patterns)

    print("Phase 2.5B: Architectural Review (Pre-Implementation)")
    arch_score = review_plan_architecture(plan)
    if arch_score < 60:
        human_checkpoint("Plan architectural score: {arch_score}/100. Approve?")

    print("Phase 2.7: Complexity Evaluation")
    complexity = evaluate_complexity(task_id)
    max_turns = determine_max_turns(complexity)  # 3 for simple, 5 for complex

    print("Phase 2.8: Human Checkpoint")
    if complexity >= 7:
        decision = human_checkpoint(
            f"Complexity: {complexity}/10. Approve autonomous execution?"
        )
        if decision != "approve":
            return abort_task(task_id, reason="Human rejected at Phase 2.8")

    # ADVERSARIAL LOOP: Player-Coach with enhanced quality gates
    return adversarial_loop(
        task_id=task_id,
        worktree_path=worktree_path,
        requirements=requirements,
        plan=plan,
        max_turns=max_turns
    )
```

#### 2. ADVERSARIAL LOOP: Enhanced Player and Coach

**Player Agent** (autobuild-player.md):

```markdown
# Player Agent - Enhanced with Quality Gates

## Your Mission
Implement code to satisfy requirements, guided by the implementation plan.

## Fresh Context Each Turn
You receive:
- Task requirements (the contract)
- Implementation plan (from Phase 2)
- Previous Coach feedback (if Turn > 1)

## Phase 3: Implementation
1. Review the implementation plan from Phase 2
2. Implement according to plan specifications
3. Follow existing project patterns
4. Write clean, maintainable code

## Phase 4: Testing
1. Write tests for your implementation
2. Run tests to verify correctness
3. DO NOT declare success yourself - Coach validates

## Your Report Format
Write to `.guardkit/autobuild/{task_id}/player_turn_{n}.json`:

{
  "task_id": "TASK-XXX",
  "turn": 1,
  "files_modified": ["src/auth.py"],
  "files_created": ["src/oauth.py"],
  "tests_written": ["tests/test_oauth.py"],
  "tests_run": true,
  "tests_passed": true,
  "test_output_summary": "12 passed",
  "implementation_notes": "Implemented OAuth2 with PKCE flow",
  "concerns": ["Token refresh edge case may need review"],
  "plan_deviations": []  # If you deviated from plan, explain why
}

## Critical Rules
- NEVER declare task complete - only Coach can approve
- Follow the implementation plan from Phase 2
- If you must deviate from plan, document in plan_deviations
- Write tests, but let Coach verify them independently
```

**Coach Agent** (autobuild-coach.md):

```markdown
# Coach Agent - Enhanced with Quality Gates

## Your Mission
Independently validate Player's implementation using rigorous quality gates.

## Fresh Context Each Turn
You receive:
- Task requirements (the contract)
- Implementation plan (from Phase 2)
- Player's report (current turn)

## Phase 4.5: Test Enforcement Loop

### Step 1: Independent Test Execution
1. Run tests yourself - DO NOT trust Player's report
2. Measure coverage (line + branch)
3. Verify all tests pass

### Step 2: Auto-Fix Loop (if needed)
If tests fail:
1. Analyze failure root cause
2. Attempt auto-fix (max 3 attempts)
3. Re-run tests after each fix
4. If 3 attempts fail → FEEDBACK (block)

### Step 3: Coverage Gates
- Require ≥80% line coverage
- Require ≥75% branch coverage
- If below threshold → FEEDBACK (request more tests)

## Phase 5: Code Review

### Architectural Compliance Check
1. Review code against implementation plan
2. Check SOLID/DRY/YAGNI principles
3. Calculate architectural score (0-100)
4. If score < 60 → FEEDBACK (architectural issues)

### Code Quality Assessment
1. Check project conventions followed
2. Verify error handling present
3. Assess edge case coverage
4. Review security implications

### Requirements Verification
1. Compare implementation against ALL requirements
2. Verify acceptance criteria met
3. Check for scope creep (extra features)

## Your Decision Format

If APPROVING:
{
  "task_id": "TASK-XXX",
  "turn": 1,
  "decision": "approve",
  "validation_results": {
    "requirements_met": ["All acceptance criteria verified"],
    "tests_run": true,
    "tests_passed": true,
    "test_command": "pytest tests/",
    "test_output_summary": "15 passed",
    "line_coverage": 85,
    "branch_coverage": 78,
    "code_quality": "Excellent - follows all conventions",
    "architectural_score": 82,
    "edge_cases_covered": ["Token expiry", "Network failure", "Invalid grant"]
  },
  "rationale": "Implementation complete. All requirements met with strong test coverage."
}

If providing FEEDBACK:
{
  "task_id": "TASK-XXX",
  "turn": 1,
  "decision": "feedback",
  "issues": [
    {
      "severity": "must_fix",
      "category": "test_failure",
      "description": "test_token_refresh fails - timeout after 5s",
      "location": "tests/test_oauth.py:45",
      "suggestion": "Check async handling in refresh flow, may need await"
    },
    {
      "severity": "must_fix",
      "category": "missing_requirement",
      "description": "HTTPS enforcement not implemented",
      "location": "src/server.py",
      "suggestion": "Add HTTPS redirect middleware before route handlers"
    },
    {
      "severity": "should_fix",
      "category": "coverage",
      "description": "Line coverage 72% (below 80% threshold)",
      "location": "src/oauth.py",
      "suggestion": "Add tests for error paths and edge cases"
    }
  ],
  "requirements_status": {
    "met": ["Basic OAuth flow", "Token generation"],
    "not_met": ["HTTPS enforcement", "Token refresh"],
    "not_tested": ["Rate limiting"]
  },
  "test_enforcement": {
    "auto_fix_attempted": true,
    "auto_fix_attempts": 2,
    "auto_fix_success": false,
    "reason": "Timeout suggests async issue, needs Player attention"
  }
}

## Critical Rules
- NEVER trust Player's self-report - verify independently
- Run tests yourself with coverage measurement
- Be specific in feedback - vague feedback wastes turns
- Apply all quality gates (tests, coverage, architecture, requirements)
- ONLY approve when ALL gates pass
```

#### 3. POST-LOOP Quality Gates (Phase 5.5)

**Execute AFTER adversarial loop completes**:

```python
def adversarial_loop(task_id, worktree_path, requirements, plan, max_turns):
    """Player-Coach loop with quality gates."""

    for turn in range(1, max_turns + 1):
        # PLAYER TURN: Phase 3 + Phase 4
        player_report = invoke_player(
            task_id=task_id,
            turn=turn,
            worktree_path=worktree_path,
            requirements=requirements,
            plan=plan,
            feedback=previous_feedback if turn > 1 else None
        )

        # COACH TURN: Phase 4.5 + Phase 5
        coach_decision = invoke_coach(
            task_id=task_id,
            turn=turn,
            worktree_path=worktree_path,
            requirements=requirements,
            plan=plan,
            player_report=player_report
        )

        # Check outcome
        if coach_decision["decision"] == "approve":
            # POST-LOOP: Phase 5.5 Plan Audit
            print("Phase 5.5: Plan Audit")
            audit_result = audit_plan(task_id, plan, worktree_path)

            if audit_result["variance"] > 0.20:  # 20% LOC variance
                human_decision = human_checkpoint(
                    f"Plan variance: {audit_result['variance']*100}%. "
                    f"Files: planned {plan.file_count} vs actual {audit_result['actual_files']}. "
                    f"Approve anyway?"
                )
                if human_decision != "approve":
                    return escalate_task(task_id, reason="Scope creep detected")

            return complete_task(task_id, turns=turn, audit=audit_result)

        # Extract feedback for next turn
        previous_feedback = coach_decision.get("issues", [])

    # MAX_TURNS reached without approval
    return escalate_task(task_id, reason=f"Max turns ({max_turns}) reached")
```

---

## Why This Hybrid Approach is Superior

### Comparison: Three Approaches

| Aspect | v1: Reimplement Gates | v2: Delegate to Task-Work | v3: Hybrid (This) |
|--------|----------------------|---------------------------|-------------------|
| **Development Time** | 2-4 weeks | 3-5 days | 1-2 weeks |
| **Adversarial Cooperation** | Yes (reimplemented) | No (sequential execution) | Yes (preserved) |
| **Quality Gate Coverage** | Partial (5 gates) | Complete (10 phases) | Complete (10 phases) |
| **Fresh Context Per Turn** | Yes | No (single task-work run) | Yes |
| **Independent Coach Validation** | Yes | No (implicit in task-work) | Yes |
| **Dialectical Feedback Loop** | Yes | No | Yes |
| **Architectural Review** | Need to build | ✅ Phase 2.5B | ✅ Phase 2.5B (pre-loop) |
| **Test Enforcement** | Need to build | ✅ Phase 4.5 | ✅ Phase 4.5 (in Coach) |
| **Plan Audit** | Need to build | ✅ Phase 5.5 | ✅ Phase 5.5 (post-loop) |
| **Complexity Routing** | Need to build | ✅ Phase 2.7 | ✅ Phase 2.7 (pre-loop) |
| **Research-Backed Pattern** | ✅ Block AI | ❌ Not adversarial | ✅ Block AI |
| **Risk** | Medium (new code) | Low (proven) | Low (proven patterns) |
| **Maintenance** | High (duplicate) | Low (single source) | Medium (integration) |

### v3 Advantages

1. **Preserves Adversarial Cooperation** - Maintains the proven Player-Coach dialectical pattern that achieved 5/5 completeness
2. **Adds Missing Quality Gates** - Integrates task-work's 10-phase workflow without losing the adversarial feedback loop
3. **Fresh Context Per Turn** - Player and Coach start fresh each turn, preventing context pollution
4. **Independent Coach Validation** - Coach runs tests independently, catches false successes
5. **Bounded Process** - Turn limits, approval gates, shared requirements contract
6. **Best of Both Worlds** - Research-backed pattern + proven quality gates

### Why Not v2 (Task-Work Delegation)?

**Problem with v2**: Task-work is a **sequential workflow**, not an adversarial cooperation pattern.

```
Task-Work (Sequential):
Planning → Implementation → Testing → Review → Complete

Player-Coach (Dialectical):
Player → Coach → Feedback → Player → Coach → Feedback → ... → Approve
```

**Key Difference**:
- Task-work: Single pass through phases, human-supervised
- Player-Coach: Iterative feedback loop, autonomous

**Research Finding**: The adversarial feedback loop is **essential** for autonomous completion. The ablation study proved that without coach feedback, implementations fail.

Therefore, we cannot simply "delegate to task-work" - we must preserve the dialectical loop while adding quality gates.

---

## Implementation Architecture

### 1. Pre-Loop Quality Gates (orchestrator/quality_gates.py)

```python
class PreLoopQualityGates:
    """Execute quality gates before Player-Coach loop."""

    def execute(self, task_id: str, options: dict) -> dict:
        """Run Phases 1.6 - 2.8."""

        results = {}

        # Phase 1.6: Clarifying Questions
        if not options.get("no_questions"):
            results["clarifications"] = self.clarifying_questions(task_id)

        # Phase 2: Requirements Analysis & Planning
        results["plan"] = self.implementation_planning(task_id)

        # Phase 2.5A: Pattern Suggestions
        results["patterns"] = self.suggest_patterns(task_id, results["plan"])

        # Phase 2.5B: Architectural Review (of plan)
        results["arch_score"] = self.review_architecture(results["plan"])
        if results["arch_score"] < 60:
            if not self.human_checkpoint(f"Plan score: {results['arch_score']}. Proceed?"):
                raise QualityGateBlocked("Architectural review failed")

        # Phase 2.7: Complexity Evaluation
        results["complexity"] = self.evaluate_complexity(task_id)
        results["max_turns"] = self.determine_max_turns(results["complexity"])

        # Phase 2.8: Human Checkpoint
        if results["complexity"] >= 7:
            if not self.human_checkpoint(f"Complexity {results['complexity']}/10. Approve?"):
                raise QualityGateBlocked("Human rejected at Phase 2.8")

        return results
```

### 2. Enhanced Player Invocation

```python
async def invoke_player(
    task_id: str,
    turn: int,
    worktree_path: str,
    requirements: str,
    plan: dict,
    feedback: list = None
) -> dict:
    """Invoke Player with fresh context for Phase 3 + 4."""

    # Construct Player prompt with fresh context
    prompt = f"""You are the Player agent (Turn {turn}).

REQUIREMENTS CONTRACT (your source of truth):
{requirements}

IMPLEMENTATION PLAN (from Phase 2):
{json.dumps(plan, indent=2)}

{"COACH FEEDBACK (from Turn " + str(turn-1) + "):" if feedback else "This is your first turn."}
{json.dumps(feedback, indent=2) if feedback else ""}

YOUR MISSION:
1. Phase 3: Implement code following the plan
2. Phase 4: Write and run tests
3. Write report to .guardkit/autobuild/{task_id}/player_turn_{turn}.json

CRITICAL: Do NOT declare success. Coach will validate independently.
"""

    # Invoke via Claude Agents SDK with fresh session
    result = await query(
        prompt=prompt,
        options=ClaudeCodeOptions(
            cwd=worktree_path,
            allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
            permission_mode="acceptEdits",
            max_turns=30,
            model="claude-sonnet-4-5-20250929",
        )
    )

    # Read Player's report
    report_path = Path(worktree_path) / ".guardkit" / "autobuild" / task_id / f"player_turn_{turn}.json"
    return json.loads(report_path.read_text())
```

### 3. Enhanced Coach Invocation

```python
async def invoke_coach(
    task_id: str,
    turn: int,
    worktree_path: str,
    requirements: str,
    plan: dict,
    player_report: dict
) -> dict:
    """Invoke Coach with fresh context for Phase 4.5 + 5."""

    # Construct Coach prompt with fresh context
    prompt = f"""You are the Coach agent (Turn {turn}).

REQUIREMENTS CONTRACT (your source of truth):
{requirements}

IMPLEMENTATION PLAN (from Phase 2):
{json.dumps(plan, indent=2)}

PLAYER'S REPORT (Turn {turn}):
{json.dumps(player_report, indent=2)}

YOUR MISSION:
1. Phase 4.5: Test Enforcement
   - Run tests INDEPENDENTLY (don't trust Player's report)
   - Measure coverage (≥80% line, ≥75% branch)
   - Auto-fix if tests fail (max 3 attempts)

2. Phase 5: Code Review
   - Check architectural compliance (≥60/100 score)
   - Verify ALL requirements met
   - Assess code quality
   - Check edge case coverage

3. Write decision to .guardkit/autobuild/{task_id}/coach_turn_{turn}.json
   - APPROVE: All gates passed
   - FEEDBACK: Specific, actionable issues

CRITICAL: Be rigorous. ONLY approve when ALL quality gates pass.
"""

    # Invoke via Claude Agents SDK with fresh session
    result = await query(
        prompt=prompt,
        options=ClaudeCodeOptions(
            cwd=worktree_path,
            allowed_tools=["Read", "Bash", "Grep", "Glob"],  # NO Write
            permission_mode="default",
            max_turns=20,
            model="claude-sonnet-4-5-20250929",
        )
    )

    # Read Coach's decision
    decision_path = Path(worktree_path) / ".guardkit" / "autobuild" / task_id / f"coach_turn_{turn}.json"
    return json.loads(decision_path.read_text())
```

### 4. Post-Loop Quality Gates

```python
class PostLoopQualityGates:
    """Execute quality gates after Player-Coach loop completes."""

    def execute(self, task_id: str, plan: dict, worktree_path: str) -> dict:
        """Run Phase 5.5: Plan Audit."""

        # Compare planned vs actual
        planned_files = set(plan["files_to_create"]) | set(plan["files_to_modify"])
        actual_files = self.get_modified_files(worktree_path)

        # Calculate variances
        file_variance = abs(len(actual_files) - len(planned_files)) / len(planned_files)

        planned_loc = plan.get("estimated_loc", 0)
        actual_loc = self.count_lines_of_code(worktree_path, actual_files)
        loc_variance = abs(actual_loc - planned_loc) / planned_loc if planned_loc > 0 else 0

        # Detect scope creep
        unplanned_files = actual_files - planned_files
        missing_files = planned_files - actual_files

        return {
            "file_variance": file_variance,
            "loc_variance": loc_variance,
            "unplanned_files": list(unplanned_files),
            "missing_files": list(missing_files),
            "variance": max(file_variance, loc_variance)  # Use worst case
        }
```

---

## Integration with Existing AutoBuild

### Current AutoBuild (Phase 1a)

**Status**: Already implemented with Player-Coach agents:
- `.claude/agents/autobuild-player.md` ✅
- `.claude/agents/autobuild-coach.md` ✅
- `guardkit/orchestrator/autobuild.py` ✅
- `guardkit/cli/autobuild.py` ✅

**Current Flow**:
```
1. Load task
2. Create worktree
3. FOR turn = 1 to max_turns:
   a. Invoke Player → implementation
   b. Invoke Coach → validation + decision
   c. IF approve → merge, ELSE → continue
4. Merge or escalate
```

**Current Gaps** (what's missing):
- No Phase 1.6 (Clarifying Questions)
- No Phase 2 (Implementation Planning)
- No Phase 2.5 (Architectural Review)
- No Phase 2.7 (Complexity Evaluation)
- No Phase 2.8 (Human Checkpoint)
- No Phase 4.5 (Test Enforcement with auto-fix in Coach)
- No Phase 5.5 (Plan Audit)

### Enhanced AutoBuild (Hybrid Approach)

**Additions Needed**:

1. **Add Pre-Loop Quality Gates** (`guardkit/orchestrator/pre_loop_gates.py`):
   - Phases 1.6, 2, 2.5A, 2.5B, 2.7, 2.8

2. **Enhance Coach Agent** (`.claude/agents/autobuild-coach.md`):
   - Add Phase 4.5: Test Enforcement Loop instructions
   - Add Phase 5: Detailed Code Review checklist
   - Add coverage measurement requirements
   - Add auto-fix loop logic

3. **Add Post-Loop Quality Gates** (`guardkit/orchestrator/post_loop_gates.py`):
   - Phase 5.5: Plan Audit

4. **Update Orchestrator** (`guardkit/orchestrator/autobuild.py`):
   - Execute pre-loop gates before adversarial loop
   - Pass plan to Player and Coach
   - Execute post-loop audit after approval

### Enhanced Flow

```python
def autobuild_task(task_id: str, options: dict):
    """Enhanced AutoBuild with quality gates."""

    # SETUP
    task = load_task(task_id)
    worktree_path = create_worktree(task_id)

    # PRE-LOOP: Quality Gate Setup
    pre_loop = PreLoopQualityGates()
    try:
        gate_results = pre_loop.execute(task_id, options)
    except QualityGateBlocked as e:
        return abort_task(task_id, reason=str(e))

    # ADVERSARIAL LOOP: Enhanced Player-Coach
    loop_result = adversarial_loop(
        task_id=task_id,
        worktree_path=worktree_path,
        requirements=task.requirements,
        plan=gate_results["plan"],
        max_turns=gate_results["max_turns"]
    )

    if loop_result.status != "approved":
        return escalate_task(task_id, reason=loop_result.reason)

    # POST-LOOP: Plan Audit
    post_loop = PostLoopQualityGates()
    audit_result = post_loop.execute(task_id, gate_results["plan"], worktree_path)

    if audit_result["variance"] > 0.20:
        decision = human_checkpoint(
            f"Plan variance: {audit_result['variance']*100:.1f}%. Approve?"
        )
        if decision != "approve":
            return escalate_task(task_id, reason="Scope creep detected")

    # FINALIZE
    merge_worktree(task_id)
    return complete_task(task_id, audit=audit_result)
```

---

## Performance Analysis

### Current Player-Coach (No Quality Gates)

| Metric | Value |
|--------|-------|
| Avg turns per task | 1-2 |
| Time per turn | 5-10 min |
| Total per task | 10-20 min |
| Quality gates | 0 |
| Architectural review | No |
| Test enforcement | Basic (Coach runs tests, no auto-fix) |
| Coverage measurement | No |
| Plan audit | No |

### Enhanced Player-Coach (With Quality Gates)

| Metric | Value |
|--------|-------|
| Pre-loop overhead | +5-8 min (Phases 1.6-2.8) |
| Avg turns per task | 1-2 (same) |
| Time per turn | 8-12 min (+3-4 min for enhanced Coach) |
| Post-loop overhead | +2-3 min (Phase 5.5) |
| **Total per task** | **17-28 min** |
| Quality gates | 10 phases |
| Architectural review | Yes (pre-loop + in-Coach) |
| Test enforcement | Yes (auto-fix in Coach) |
| Coverage measurement | Yes (80%/75% gates) |
| Plan audit | Yes (±20% variance) |

**Net Impact**: +40-70% time per task, but with **complete quality enforcement**.

**Example Feature (7 tasks)**:
- Current: 70-140 min (no quality assurance)
- Enhanced: 119-196 min (full quality assurance)

**Verdict**: Acceptable tradeoff for production quality.

---

## Implementation Roadmap

### Phase 1: Pre-Loop Quality Gates (3-5 days)

**Goal**: Add Phases 1.6 - 2.8 before adversarial loop.

**Tasks**:
1. Create `guardkit/orchestrator/pre_loop_gates.py`
2. Implement each phase:
   - Phase 1.6: Integrate clarification-questioner agent
   - Phase 2: Reuse implementation planning from task-work
   - Phase 2.5A: Integrate design-patterns MCP
   - Phase 2.5B: Reuse architectural-reviewer agent
   - Phase 2.7: Reuse complexity evaluation logic
   - Phase 2.8: Add human checkpoint for complexity ≥7
3. Update `autobuild.py` to execute pre-loop gates
4. Test with real tasks (simple, medium, complex)

**Acceptance Criteria**:
- All phases execute correctly
- Plan generated and passed to Player
- Complex tasks trigger Phase 2.8 checkpoint
- Tests pass

### Phase 2: Enhanced Coach (5-7 days)

**Goal**: Add Phase 4.5 and Phase 5 to Coach agent.

**Tasks**:
1. Update `.claude/agents/autobuild-coach.md`:
   - Add Phase 4.5: Test Enforcement Loop section
   - Add auto-fix loop instructions (max 3 attempts)
   - Add coverage measurement requirements (80%/75%)
   - Add Phase 5: Code Review checklist
   - Add architectural scoring logic
2. Implement coverage measurement tools
3. Implement auto-fix loop scaffolding (Coach attempts fixes)
4. Update Coach decision format to include:
   - Coverage metrics
   - Architectural score
   - Auto-fix results
5. Test with tasks designed to fail tests

**Acceptance Criteria**:
- Coach runs tests independently
- Coverage measured and reported
- Auto-fix loop executes (even if fixes don't work)
- Architectural score calculated
- Coach only approves when ALL gates pass

### Phase 3: Post-Loop Quality Gates (2-3 days)

**Goal**: Add Phase 5.5 after adversarial loop completes.

**Tasks**:
1. Create `guardkit/orchestrator/post_loop_gates.py`
2. Implement plan audit logic:
   - Compare files created vs planned
   - Calculate LOC variance
   - Detect unplanned files
3. Update `autobuild.py` to execute post-loop audit
4. Add human checkpoint for variance > 20%
5. Test with tasks that go off-plan

**Acceptance Criteria**:
- Plan audit executes after Coach approval
- Variance calculated correctly
- Unplanned files detected
- Human checkpoint triggered when needed

### Phase 4: Integration Testing & Documentation (3-5 days)

**Goal**: End-to-end validation and documentation.

**Tasks**:
1. Create integration test suite:
   - Simple task (complexity 1-3, 1 turn)
   - Medium task (complexity 4-6, 2 turns)
   - Complex task (complexity 7+, 3+ turns)
   - Task with test failures (trigger auto-fix)
   - Task with scope creep (trigger audit)
2. Update documentation:
   - `/feature-build` command spec
   - Quality gates explanation
   - Examples and use cases
3. Performance benchmarking
4. User acceptance testing

**Acceptance Criteria**:
- All integration tests pass
- Documentation complete
- Performance within acceptable range
- Ready for production use

**Total Timeline**: 13-20 days (~3-4 weeks)

---

## Comparison Table: All Three Approaches

| Criterion | v1: Reimplement | v2: Delegate to Task-Work | v3: Hybrid (Recommended) |
|-----------|----------------|---------------------------|--------------------------|
| **Adversarial Cooperation** | ✅ Yes | ❌ No (sequential) | ✅ Yes |
| **Fresh Context Per Turn** | ✅ Yes | ❌ No | ✅ Yes |
| **Independent Coach Validation** | ✅ Yes | ⚠️ Implicit | ✅ Yes |
| **Dialectical Feedback Loop** | ✅ Yes | ❌ No | ✅ Yes |
| **Block AI Research Pattern** | ✅ Follows | ❌ Doesn't follow | ✅ Follows |
| **Architectural Review** | ⚠️ Need to build | ✅ Phase 2.5B | ✅ Phase 2.5B (reused) |
| **Complexity Routing** | ⚠️ Need to build | ✅ Phase 2.7 | ✅ Phase 2.7 (reused) |
| **Test Auto-Fix** | ⚠️ Need to build | ✅ Phase 4.5 | ✅ Phase 4.5 (in Coach) |
| **Coverage Gates** | ⚠️ Need to build | ✅ Phase 4 | ✅ Phase 4 (in Coach) |
| **Plan Audit** | ⚠️ Need to build | ✅ Phase 5.5 | ✅ Phase 5.5 (reused) |
| **Development Time** | 2-4 weeks | 3-5 days | 3-4 weeks |
| **Quality Gate Coverage** | Partial (would need to implement 5) | Complete (10 phases) | Complete (10 phases) |
| **Code Reuse** | Low (new implementation) | High (delegates entirely) | High (reuses gate logic) |
| **Maintenance Burden** | High (duplicate code) | Low (single source) | Medium (integration points) |
| **Risk** | Medium (new untested code) | Low (proven task-work) | Low (proven patterns) |
| **Autonomous Completion** | ✅ High (dialectical) | ⚠️ Moderate (sequential) | ✅ High (dialectical) |
| **Production Readiness** | ⚠️ Unknown (new) | ✅ Proven | ✅ Proven (with research backing) |

**Winner**: **v3 (Hybrid)** - Combines research-backed adversarial cooperation with proven quality gates.

---

## Answers to Review Questions (Revised for v3)

### Quality Gate Integration

**Q1: How should Phase 2.5 (Architectural Review) work when Player is autonomous?**
- **v3 Answer**: Execute Phase 2.5B **before** adversarial loop (review the plan), then **again** in Coach Phase 5 (review the implementation).

**Q2: Should Coach validate SOLID/DRY/YAGNI compliance, or should a separate reviewer?**
- **v3 Answer**: Coach does it in Phase 5 as part of code review. Reuse architectural-reviewer scoring logic.

**Q3: Where does complexity evaluation fit in wave-based execution?**
- **v3 Answer**: Phase 2.7 runs **before** adversarial loop starts, determines max_turns for the loop.

### Test Enforcement

**Q4: Should test failures trigger Player retry or dedicated test-fixer?**
- **v3 Answer**: Coach attempts auto-fix in Phase 4.5 (max 3 attempts). If all fail, Coach provides FEEDBACK to Player for next turn.

**Q5: How many auto-fix attempts per task before escalating?**
- **v3 Answer**: 3 attempts in Coach's Phase 4.5, then escalate via FEEDBACK to Player.

**Q6: Should test coverage gates block wave progression?**
- **v3 Answer**: Yes, Coach checks coverage in Phase 4.5 and blocks approval if < 80%/75%.

### Human Oversight

**Q7: Which complexity threshold triggers mandatory human review?**
- **v3 Answer**: Complexity ≥7 triggers Phase 2.8 checkpoint before loop starts.

**Q8: Should feature-build pause at wave boundaries for approval?**
- **v3 Answer**: No, but individual complex tasks pause at Phase 2.8.

**Q9: How to surface architectural concerns for human decision?**
- **v3 Answer**: Pre-loop Phase 2.5B scores plan < 60 → human checkpoint. Coach Phase 5 scores implementation < 60 → FEEDBACK to Player.

### Scope Management

**Q10: How to detect scope creep when Player has autonomy?**
- **v3 Answer**: Post-loop Phase 5.5 Plan Audit compares actual vs planned implementation.

**Q11: Should Plan Audit run per-task or end-of-feature?**
- **v3 Answer**: Per-task (Phase 5.5 post-loop), aggregated at feature level.

**Q12: What variance thresholds should trigger alerts?**
- **v3 Answer**: >20% LOC variance or >50% file count variance → human checkpoint.

---

## Conclusion

**Problem**: Feature-build uses adversarial cooperation (Player-Coach) but lacks quality gates.

**Research**: Block AI paper proves adversarial cooperation achieves 5/5 completeness (ablation study confirms it's essential).

**Task-Work**: Provides 10-phase quality gates that prevent architectural drift, ensure coverage, detect scope creep.

**Solution (v3 - Hybrid)**: **Enhance** Player-Coach with quality gates from task-work:
- **PRE-LOOP**: Phases 1.6-2.8 (planning, architectural review, complexity routing, checkpoint)
- **ADVERSARIAL LOOP**: Phases 3-5 (Player implements, Coach validates with auto-fix + code review)
- **POST-LOOP**: Phase 5.5 (plan audit)

### Why v3 (Not v2)

**v2 Problem**: Delegating to task-work **eliminates** the adversarial cooperation pattern:
- Task-work is sequential (one pass through phases)
- No fresh context per turn (single execution)
- No independent Coach validation each turn
- No dialectical feedback loop

**Research says**: The adversarial feedback loop is **essential** for autonomous completion.

**v3 Solution**: Keep the dialectical loop, add quality gates around it.

### Implementation Path

1. **Phase 1**: Pre-loop gates (3-5 days)
2. **Phase 2**: Enhanced Coach with test enforcement + code review (5-7 days)
3. **Phase 3**: Post-loop plan audit (2-3 days)
4. **Phase 4**: Integration testing (3-5 days)

**Total**: 3-4 weeks

### Expected Outcome

- ✅ Adversarial cooperation preserved (5/5 completeness potential)
- ✅ All 10 quality gates enforced
- ✅ Fresh context per turn (prevents pollution)
- ✅ Independent Coach validation (catches false successes)
- ✅ Research-backed pattern + proven quality gates
- ✅ Production-ready autonomous feature building

**Recommendation**: Implement v3 (Hybrid approach).

---

## Appendix: Example Turn-by-Turn Flow

### Example: TASK-AUTH-001 "Implement OAuth2 Authentication"

**Complexity**: 6/10 (medium)

#### PRE-LOOP: Quality Gate Setup

```
Phase 1.6: Clarifying Questions
├── Q1: Implementation scope? → Standard (with error handling)
├── Q2: Testing approach? → Integration tests included
└── Saved to task frontmatter

Phase 2: Implementation Planning
├── Created implementation plan
├── Files to create: src/auth/oauth.py, tests/test_oauth.py
├── Files to modify: src/auth/__init__.py, src/config.py
└── Estimated LOC: ~200

Phase 2.5A: Pattern Suggestions
├── Queried design-patterns MCP
├── Suggested: Strategy Pattern (for auth providers)
└── Updated plan with pattern

Phase 2.5B: Architectural Review (of plan)
├── SOLID compliance: 78/100
├── DRY compliance: 85/100
├── YAGNI compliance: 90/100
├── Overall: 84/100 ✅ (>60 threshold)
└── Approved

Phase 2.7: Complexity Evaluation
├── Complexity: 6/10 (medium)
├── Max turns: 5
└── Quick review mode

Phase 2.8: Human Checkpoint
└── Skipped (complexity < 7)
```

#### ADVERSARIAL LOOP

**Turn 1:**

```
PLAYER:
├── Phase 3: Implementation
│   ├── Created src/auth/oauth.py (OAuth2 flow with PKCE)
│   ├── Modified src/auth/__init__.py (exported OAuth2Provider)
│   └── Modified src/config.py (added OAuth settings)
├── Phase 4: Testing
│   ├── Created tests/test_oauth.py (8 tests)
│   ├── Ran tests: 8 passed
│   └── Self-report: "Tests passing"
└── Report written to player_turn_1.json

COACH:
├── Phase 4.5: Test Enforcement
│   ├── Independent test execution: 7 passed, 1 failed ❌
│   │   └── test_token_refresh failed (timeout)
│   ├── Coverage: 72% line, 68% branch ❌ (below 80%/75%)
│   └── Auto-fix attempted:
│       ├── Attempt 1: Added await to refresh call → Still fails
│       ├── Attempt 2: Increased timeout to 10s → Still fails
│       ├── Attempt 3: Added error logging → Still fails
│       └── Auto-fix unsuccessful (needs Player attention)
├── Phase 5: Code Review
│   ├── Architectural score: 76/100 ✅
│   ├── Missing: HTTPS enforcement (requirement not met) ❌
│   ├── Edge cases incomplete (token expiry handling) ❌
│   └── Overall: Not ready for approval
└── Decision: FEEDBACK (3 must-fix issues)

FEEDBACK to Player:
[
  {
    "severity": "must_fix",
    "category": "test_failure",
    "description": "test_token_refresh fails - timeout after 10s",
    "location": "tests/test_oauth.py:45",
    "suggestion": "Check async handling in refresh flow, may need mock token endpoint"
  },
  {
    "severity": "must_fix",
    "category": "missing_requirement",
    "description": "HTTPS enforcement not implemented",
    "location": "src/server.py",
    "suggestion": "Add HTTPS redirect middleware before route handlers"
  },
  {
    "severity": "must_fix",
    "category": "coverage",
    "description": "Line coverage 72% (below 80% threshold)",
    "location": "src/auth/oauth.py",
    "suggestion": "Add tests for token expiry and edge cases"
  }
]
```

**Turn 2:**

```
PLAYER:
├── Received Coach feedback
├── Phase 3: Implementation (fixes)
│   ├── Fixed test_token_refresh (added mock endpoint)
│   ├── Added HTTPS middleware to src/server.py
│   └── Added token expiry handling
├── Phase 4: Testing
│   ├── Added 3 new tests (token expiry, HTTPS, error cases)
│   ├── Ran tests: 11 passed
│   └── Self-report: "All issues addressed"
└── Report written to player_turn_2.json

COACH:
├── Phase 4.5: Test Enforcement
│   ├── Independent test execution: 11 passed ✅
│   ├── Coverage: 88% line, 82% branch ✅
│   └── Auto-fix not needed
├── Phase 5: Code Review
│   ├── Architectural score: 84/100 ✅
│   ├── All requirements met ✅
│   ├── HTTPS enforcement present ✅
│   ├── Edge cases covered ✅
│   └── Overall: Ready for approval
└── Decision: APPROVE
```

#### POST-LOOP: Plan Audit

```
Phase 5.5: Plan Audit
├── Files planned: 4 (2 create, 2 modify)
├── Files actual: 4 (2 create, 2 modify) ✅
├── LOC planned: ~200
├── LOC actual: 247
├── Variance: 23.5% ⚠️ (above 20% threshold)
└── Human checkpoint triggered

Human Decision:
├── Prompt: "Plan variance: 23.5%. Approve?"
├── User views: player_turn_2.json, coach_turn_2.json
├── User reviews: Added error handling (justified extra LOC)
└── Decision: APPROVE

FINALIZE:
├── Merge autobuild/TASK-AUTH-001 to main
├── Archive turn reports
└── Task completed in 2 turns (17 minutes)
```

**Summary**:
- Turn 1: Coach caught 3 issues (test failure, missing requirement, low coverage)
- Turn 2: Player fixed all issues, Coach approved
- Plan audit detected 23% variance, human approved
- Total time: ~17 minutes (vs ~10 min without gates)
- Quality: All gates passed, production-ready code

---

*This revision (v3) represents the recommended approach: Combining adversarial cooperation with task-work quality gates.*
