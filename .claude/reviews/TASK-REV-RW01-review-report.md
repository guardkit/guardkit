# Review Report: TASK-REV-RW01

## Executive Summary

This architectural review analyzes the Claude Code Ralph Wiggum plugin to identify techniques and patterns applicable to GuardKit's `/feature-build` Player-Coach adversarial cooperation workflow.

**Key Finding**: Ralph Wiggum uses a fundamentally different architecture (single-agent self-referential loop) compared to GuardKit's dual-agent adversarial cooperation pattern. However, several techniques are highly applicable:

1. **Promise-Based Completion** - Explicit completion criteria with verification
2. **Escape Hatch Pattern** - Maximum iteration limits with documented fallback
3. **Self-Referential Context** - Persistent state across iterations via file system
4. **Test-Driven Verification** - Automated quality gates as loop exit conditions

**Architecture Score**: 76/100 (Good alignment potential with modifications)

---

## Review Details

| Field | Value |
|-------|-------|
| **Mode** | Architectural Review |
| **Depth** | Standard (1-2 hours) |
| **Duration** | ~90 minutes |
| **Reviewer** | architectural-reviewer agent |

---

## Section 1: Ralph Wiggum Architecture Analysis

### 1.1 Plugin Structure

```
plugins/ralph-wiggum/
├── .claude-plugin/          # Plugin configuration
├── commands/
│   ├── ralph-loop.md        # Primary loop command
│   ├── cancel-ralph.md      # Cancellation handler
│   └── help.md              # Documentation
├── hooks/
│   └── stop-hook.sh         # Core loop mechanism
├── scripts/
│   └── setup-ralph-loop.sh  # Initialization
└── README.md
```

### 1.2 Core Mechanism: Stop Hook Pattern

Ralph Wiggum implements a **self-referential feedback loop** using Claude Code's hook system:

```
┌──────────────────────────────────────────────────────────────────────┐
│                    RALPH WIGGUM LOOP PATTERN                          │
│                                                                       │
│   User runs /ralph-loop              Claude works                    │
│        ▼                                  ▼                          │
│   ┌─────────────┐                   ┌─────────────┐                  │
│   │ Initialize  │                   │ Implement   │                  │
│   │ loop state  │──────────────────▶│ + test      │                  │
│   └─────────────┘                   └──────┬──────┘                  │
│                                            │                          │
│                                     Claude tries exit                 │
│                                            │                          │
│   ┌─────────────┐                   ┌──────▼──────┐                  │
│   │ Stop Hook   │◀──────────────────│ stop-hook.sh│                  │
│   │ intercepts  │                   └─────────────┘                  │
│   └──────┬──────┘                                                    │
│          │                                                            │
│   ┌──────▼──────┐     NO        ┌─────────────┐                      │
│   │ Promise     │──────────────▶│ Block exit  │                      │
│   │ fulfilled?  │               │ Inject same │──────┐               │
│   └──────┬──────┘               │ prompt      │      │               │
│          │ YES                  └─────────────┘      │               │
│   ┌──────▼──────┐                     ▲              │               │
│   │ Allow exit  │                     └──────────────┘               │
│   │ Loop done   │               (iteration++)                        │
│   └─────────────┘                                                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Key Characteristics:**
- **Single Agent**: One Claude instance iterates on itself
- **Same Prompt**: The prompt never changes between iterations
- **File Persistence**: Previous work persists in files and git history
- **Exit Blocking**: Hook system prevents premature termination

### 1.3 Completion Detection

Ralph Wiggum uses **exact string matching** for completion detection:

```bash
# Claude must output exactly:
<promise>COMPLETE</promise>

# The hook verifies:
# 1. Promise tag is present
# 2. Content matches --completion-promise
# 3. Promise is "completely and unequivocally TRUE"
```

**Verification Philosophy**: The system enforces intellectual honesty - Claude cannot fabricate false promises to escape, even under frustration or perceived impossibility.

### 1.4 Safety Mechanisms

| Mechanism | Implementation | Purpose |
|-----------|----------------|---------|
| Max Iterations | `--max-iterations N` | Prevent infinite loops |
| Escape Hatch | Prompt includes fallback instructions | Document blocking issues |
| Cancellation | `/cancel-ralph` command | Manual abort capability |
| File State | `.claude/ralph-loop.local.md` | Track iteration count |

---

## Section 2: Technique Catalog

### 2.1 Promise-Based Completion (HIGH APPLICABILITY)

**Pattern Description**: Define explicit, verifiable completion criteria that the agent must satisfy before loop termination.

**Ralph Implementation**:
```bash
/ralph-loop "Build REST API for todos.
When complete:
- All CRUD endpoints working
- Input validation in place
- Tests passing (coverage > 80%)
- Output: <promise>COMPLETE</promise>"
```

**Applicability to GuardKit Player-Coach**: **HIGH**

The Player agent could adopt explicit promise statements in its report that the Coach verifies:

```json
// Player Report Enhancement
{
  "completion_promise": {
    "statement": "All acceptance criteria met",
    "criteria_verified": [
      {"id": "AC-001", "status": "verified", "evidence": "test_oauth.py passes"},
      {"id": "AC-002", "status": "verified", "evidence": "token refresh works"}
    ]
  }
}
```

**Benefit**: More rigorous completion verification than current binary `decision: approve/feedback`.

---

### 2.2 Escape Hatch Pattern (HIGH APPLICABILITY)

**Pattern Description**: Define explicit fallback behavior when maximum iterations are reached without success.

**Ralph Implementation**:
```bash
/ralph-loop "Try feature X" --max-iterations 20

# In prompt:
"After 15 iterations, if not complete:
- Document what's blocking progress
- List what was attempted
- Suggest alternative approaches"
```

**Applicability to GuardKit**: **HIGH**

Current GuardKit behavior on `max_turns_exceeded`:
- Worktree preserved for inspection
- Generic "Human intervention required" message

**Enhanced Behavior** (inspired by Ralph):
```python
# If max_turns approaching (turn >= max_turns - 2):
# Player should generate structured blocked-task report:
{
  "blocked_report": {
    "blocking_issues": [
      "External service mock unavailable for integration tests"
    ],
    "attempts_made": [
      "Turn 1: Tried direct HTTP mock",
      "Turn 2: Tried httpretty library",
      "Turn 3: Created custom mock server"
    ],
    "suggested_alternatives": [
      "Manual mock server setup required",
      "Split task to unit tests only"
    ]
  }
}
```

---

### 2.3 Self-Referential Context (MEDIUM APPLICABILITY)

**Pattern Description**: Agent reads its own previous work and adapts strategy based on observed results.

**Ralph Implementation**:
- Claude's previous work persists in files
- Each iteration sees modified files and git history
- Claude autonomously improves by reading its own past work

**Applicability to GuardKit**: **MEDIUM**

GuardKit already implements partial self-reference:
- Coach feedback is passed to Player in next turn
- Turn history is maintained in orchestrator

**Enhancement Opportunity**:
```python
# Player could analyze git diff between turns:
def analyze_previous_turn_changes():
    """Read git diff to understand what changed."""
    diff = git.diff("HEAD~1", "HEAD")
    # Extract patterns: what files changed, what tests failed
    # Inform implementation strategy
```

**Caution**: This could increase token usage significantly. Current summarized feedback approach is more token-efficient.

---

### 2.4 Test-Driven Verification Loop (HIGH APPLICABILITY)

**Pattern Description**: Embed TDD workflow in the iteration loop with tests as the primary exit condition.

**Ralph Implementation**:
```bash
"Implement feature X following TDD:
1. Write failing tests
2. Implement feature
3. Run tests
4. If any fail, debug and fix
5. Refactor if needed
6. Repeat until all green
7. Output: <promise>COMPLETE</promise>"
```

**Applicability to GuardKit**: **HIGH**

Current GuardKit has test enforcement (Phase 4.5), but Player doesn't inherently follow TDD.

**Enhancement Opportunity**:
- Make TDD workflow explicit in Player agent system prompt
- Player should write tests BEFORE implementation on each turn
- Coach should verify test-first approach in addition to test-passing

---

### 2.5 Honest Failure Documentation (MEDIUM-HIGH APPLICABILITY)

**Pattern Description**: The system prevents false success claims and requires honest documentation of failures.

**Ralph Implementation**:
> "The design enforces intellectual honesty: users cannot fabricate false promises to escape, even under frustration or perceived impossibility."

**Applicability to GuardKit**: **MEDIUM-HIGH**

Current Player agent has "Be honest in your implementation report" in ALWAYS section, but no enforcement mechanism.

**Enhancement Opportunity**:
- Coach should cross-reference Player claims with actual test output
- If Player claims `tests_passed: true` but Coach finds failures, add penalty/flag
- Implement "honesty score" tracking across turns

---

### 2.6 Incremental Phased Goals (MEDIUM APPLICABILITY)

**Pattern Description**: Break complex tasks into sequential phases with explicit completion markers.

**Ralph Implementation**:
```bash
"Phase 1: User authentication (JWT, tests)
Phase 2: Product catalog (list/search, tests)
Phase 3: Shopping cart (add/remove, tests)

Output <promise>COMPLETE</promise> when all phases done."
```

**Applicability to GuardKit**: **MEDIUM**

GuardKit tasks are typically single-phase. Multi-phase work is handled at the feature level (FeatureOrchestrator).

**Consideration**: Could be useful for complex single tasks, but may add overhead for simple tasks.

---

## Section 3: Comparison Matrix

| Aspect | Ralph Wiggum | GuardKit Player-Coach | Gap Analysis |
|--------|--------------|----------------------|--------------|
| **Agent Count** | Single (self-referential) | Dual (Player + Coach) | Different paradigm - not directly comparable |
| **Iteration Trigger** | Stop hook blocks exit | Orchestrator loop | GuardKit more explicit, Ralph more seamless |
| **Completion Detection** | Promise tag exact match | Coach decision (approve/feedback) | Ralph more explicit; GuardKit could add promise verification |
| **Max Turns** | `--max-iterations` | `max_turns` in frontmatter | Equivalent |
| **Escape Hatch** | Prompt includes fallback | Basic preservation | **GAP**: GuardKit needs structured blocked-task reports |
| **Context Preservation** | Files + git history | Feedback summary | Ralph richer but more token-expensive |
| **Quality Gates** | Tests in prompt | task-work delegation (Phase 4-5.5) | GuardKit more comprehensive |
| **Test Philosophy** | TDD embedded in prompt | Tests run post-implementation | **GAP**: Pass --mode=tdd to Player or embed in prompt |
| **Honesty Enforcement** | "Intellectual honesty" design principle | No explicit mechanism | **GAP**: GuardKit could add honesty verification |
| **Cancellation** | `/cancel-ralph` command | No explicit command | Minor gap - could add cancel support |

---

## Section 4: Recommendations

### Recommendation 1: Add Promise-Based Completion Verification (Priority: HIGH)

**What**: Extend Player report to include explicit completion promises that Coach verifies.

**Why**:
- More rigorous than binary approve/feedback
- Prevents false success claims
- Aligns with Ralph's "intellectual honesty" design

**Implementation**:
```python
# Player report schema extension
class CompletionPromise:
    statement: str  # e.g., "All acceptance criteria met"
    criteria: List[CriterionVerification]

class CriterionVerification:
    criterion_id: str
    status: Literal["verified", "partial", "blocked"]
    evidence: str
```

**Effort**: Medium (2-4 hours)
**Risk**: Low

---

### Recommendation 2: Implement Escape Hatch Pattern (Priority: HIGH)

**What**: When approaching max_turns, Player should generate structured blocked-task report.

**Why**:
- Current behavior just says "Human intervention required"
- Ralph pattern provides actionable debugging information
- Reduces human investigation time

**Implementation**:
```python
# In Player agent prompt, add:
"""
If this is turn >= (max_turns - 2) and you cannot complete:
Generate a blocked_report section in your JSON with:
- blocking_issues: What's preventing completion
- attempts_made: What you tried on each turn
- suggested_alternatives: How to proceed differently
"""
```

**Effort**: Low (1-2 hours)
**Risk**: Very Low

---

### Recommendation 3: Delegate to task-work --implement-only --mode=tdd (Priority: HIGH - REVISED AFTER DEEPER ANALYSIS)

**What**: Route AutoBuild Player phase through `task-work --implement-only --mode=tdd` to leverage existing subagent infrastructure.

**Why**: After deeper analysis, this is the architecturally superior approach because:
- **Reuses proven implementation** - task-work already has working TDD, subagent selection, quality gates
- **Stack-specific subagents** - task-work selects specialized agents (python-api-specialist, react-specialist, etc.)
- **Quality gates included** - Phase 4 testing, Phase 4.5 enforcement, Phase 5 code review
- **Agent discovery system** - Metadata-based agent matching for optimal specialist selection
- **Avoids code duplication** - Why re-implement TDD logic when it exists?

---

### DEEP DIVE: Current Architecture vs task-work Delegation

#### Current Player Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CURRENT AUTOBUILD FLOW                                                      │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PreLoopQualityGates                                                        │
│       │                                                                     │
│       ▼                                                                     │
│  TaskWorkInterface.execute_design_phase()                                   │
│       │                                                                     │
│       ▼                                                                     │
│  task-work --design-only ─────────────────────────────────────────┐        │
│       │                                                            │        │
│       │  Phase 1.6: Clarification                                  │        │
│       │  Phase 2: Planning (uses selected_planning_agent)          │ ✅      │
│       │  Phase 2.5A: Pattern Suggestion (MCP)                      │ Subagent│
│       │  Phase 2.5B: Architectural Review (architectural-reviewer) │ Usage   │
│       │  Phase 2.7: Complexity Evaluation (complexity-evaluator)   │        │
│       │  Phase 2.8: Human Checkpoint                               │        │
│       └────────────────────────────────────────────────────────────┘        │
│       │                                                                     │
│       ▼ (returns plan, complexity, etc.)                                    │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│  ADVERSARIAL LOOP STARTS                                                    │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  AgentInvoker.invoke_player() ─────────────────────────────────────┐        │
│       │                                                            │        │
│       │  _build_player_prompt()                                    │ ❌      │
│       │  Sends generic prompt to SDK                               │ NO      │
│       │  Player implements directly in worktree                    │ SUBAGENT│
│       │  Player runs tests itself                                  │ USAGE   │
│       │  Creates player_turn_N.json report                         │        │
│       └────────────────────────────────────────────────────────────┘        │
│       │                                                                     │
│       ▼                                                                     │
│  AgentInvoker.invoke_coach()                                                │
│       │                                                                     │
│       ▼                                                                     │
│  (repeat until approved or max_turns)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Issue**: Player uses `claude_agent_sdk.query()` with a generic prompt. It does NOT invoke:
- Stack-specific implementation specialists (python-api-specialist, react-specialist, etc.)
- Testing specialists (test-orchestrator, qa-tester, etc.)
- Code review (code-reviewer)

#### What task-work --implement-only Provides

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ task-work --implement-only --mode=tdd FLOW                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Phase 3: Implementation ──────────────────────────────────────────┐        │
│       │                                                            │        │
│       │  INVOKE Task tool:                                         │ ✅      │
│       │    subagent_type: "{selected_implementation_agent}"        │ SUBAGENT│
│       │    - python-api-specialist                                 │ USAGE   │
│       │    - react-specialist                                      │        │
│       │    - dotnet-api-specialist                                 │        │
│       │    - (or task-manager fallback)                            │        │
│       │                                                            │        │
│       │  Agent Discovery System:                                   │        │
│       │    1. Detect stack from files                              │        │
│       │    2. Match phase: implementation                          │        │
│       │    3. Score by capabilities/keywords                       │        │
│       │    4. Select best match                                    │        │
│       └────────────────────────────────────────────────────────────┘        │
│       │                                                                     │
│       ▼                                                                     │
│  Phase 4: Testing ─────────────────────────────────────────────────┐        │
│       │                                                            │        │
│       │  INVOKE Task tool:                                         │ ✅      │
│       │    subagent_type: "{selected_testing_agent}"               │ SUBAGENT│
│       │    - test-orchestrator                                     │ USAGE   │
│       │    - qa-tester                                             │        │
│       │    - Stack-specific testing specialist                     │        │
│       │                                                            │        │
│       │  Compilation check (mandatory)                             │        │
│       │  Test execution                                            │        │
│       │  Coverage analysis (80%/75% thresholds)                    │        │
│       └────────────────────────────────────────────────────────────┘        │
│       │                                                                     │
│       ▼                                                                     │
│  Phase 4.5: Fix Loop ──────────────────────────────────────────────┐        │
│       │                                                            │        │
│       │  WHILE tests fail AND attempt <= 3:                        │ ✅      │
│       │    INVOKE Task tool:                                       │ SUBAGENT│
│       │      subagent_type: "{selected_implementation_agent}"      │ USAGE   │
│       │    Fix compilation errors                                  │        │
│       │    Fix test failures                                       │        │
│       │    Re-run tests                                            │        │
│       └────────────────────────────────────────────────────────────┘        │
│       │                                                                     │
│       ▼                                                                     │
│  Phase 5: Code Review ─────────────────────────────────────────────┐        │
│       │                                                            │        │
│       │  INVOKE Task tool:                                         │ ✅      │
│       │    subagent_type: "code-reviewer"                          │ SUBAGENT│
│       │  Quality assessment                                        │ USAGE   │
│       │  Error handling review                                     │        │
│       │  Documentation check                                       │        │
│       └────────────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**TDD Mode Specifics** (when `--mode=tdd`):
- RED: Testing agent generates failing tests first
- GREEN: Implementation agent writes minimal code to pass
- REFACTOR: Implementation agent improves code quality

---

### COMPARISON: Option A vs Option B

| Aspect | Option A (Prompt-Only) | Option B (task-work Delegation) |
|--------|------------------------|----------------------------------|
| **Subagent Usage** | ❌ None - generic prompt | ✅ Full agent discovery |
| **TDD Enforcement** | Prompt-based (honor system) | Structural (RED→GREEN→REFACTOR) |
| **Stack Specialists** | ❌ Not used | ✅ python-api, react, dotnet, etc. |
| **Test Orchestration** | Player runs tests manually | ✅ test-orchestrator agent |
| **Fix Loop** | No auto-fix | ✅ Phase 4.5 (3 attempts) |
| **Code Review** | ❌ Coach only | ✅ code-reviewer agent |
| **Coverage Enforcement** | None | ✅ 80%/75% thresholds |
| **Implementation Effort** | Low (prompt change) | Medium (integration work) |
| **Code Reuse** | 0% | 100% |
| **Architectural Debt** | Creates parallel path | Uses proven path |
| **Future Maintenance** | 2 systems to maintain | 1 system |

---

### RECOMMENDED: Option B with Hybrid Architecture

**Architecture**:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PROPOSED AUTOBUILD FLOW (OPTION B)                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  PreLoopQualityGates (unchanged)                                            │
│       │                                                                     │
│       ▼                                                                     │
│  task-work --design-only                                                    │
│       │                                                                     │
│       ▼ (returns plan, complexity)                                          │
│                                                                             │
│  ═══════════════════════════════════════════════════════════════════════    │
│  ADVERSARIAL LOOP                                                           │
│  ═══════════════════════════════════════════════════════════════════════    │
│                                                                             │
│  PLAYER TURN:                                                               │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ task-work --implement-only --mode=tdd                               │    │
│  │     │                                                               │    │
│  │     ├── Phase 3: Implementation (stack-specific agent)             │    │
│  │     ├── Phase 4: Testing (test-orchestrator)                       │    │
│  │     ├── Phase 4.5: Fix Loop (auto-fix)                             │    │
│  │     └── Phase 5: Code Review (code-reviewer)                       │    │
│  │                                                                     │    │
│  │ Output: Implementation complete, tests passing, code reviewed       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                     │
│       ▼                                                                     │
│  COACH TURN (unchanged - validates independently):                          │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │ AgentInvoker.invoke_coach()                                         │    │
│  │     │                                                               │    │
│  │     └── Read-only validation (approve/feedback)                     │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│       │                                                                     │
│       ▼                                                                     │
│  (repeat until approved or max_turns)                                       │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Implementation Changes**:

1. **AgentInvoker.invoke_player() - Modified**:
```python
async def invoke_player(
    self,
    task_id: str,
    turn: int,
    requirements: str,
    feedback: Optional[str] = None,
    mode: str = "tdd",  # NEW: development mode
) -> AgentInvocationResult:
    """Invoke Player via task-work --implement-only."""

    # Instead of generic SDK query, delegate to task-work
    result = await self._invoke_task_work_implement(
        task_id=task_id,
        mode=mode,
        feedback=feedback,
    )

    return result

async def _invoke_task_work_implement(
    self,
    task_id: str,
    mode: str,
    feedback: Optional[str],
) -> AgentInvocationResult:
    """Delegate to task-work --implement-only."""

    # Build args
    args = [task_id, "--implement-only", f"--mode={mode}"]

    # If feedback from previous turn, inject into task context
    if feedback:
        # Write feedback to .claude/task-context/coach_feedback.md
        self._write_coach_feedback(task_id, feedback)

    # Execute task-work (uses all subagents)
    proc = await asyncio.create_subprocess_exec(
        "guardkit", "task-work", *args,
        cwd=str(self.worktree_path),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    # Parse result and return
    # ...
```

2. **Task State Bridging**:
```python
# Before player turn: Ensure task is in design_approved state
# After coach feedback: Update task with feedback context
# After coach approve: Mark task complete
```

3. **Feedback Integration**:
```python
# Coach feedback written to task metadata or context file
# task-work reads feedback context during Phase 3
# Implementation agent addresses feedback points
```

---

### BENEFITS OF OPTION B

1. **Stack-Specific Quality**
   - Python tasks get `python-api-specialist` not generic implementation
   - React tasks get `react-specialist` with hook patterns
   - .NET tasks get `dotnet-api-specialist` with REPR patterns

2. **TDD Actually Enforced**
   - task-work TDD mode has structural enforcement
   - Testing agent generates tests first
   - Not just "please do TDD" in prompt

3. **Quality Gates Included**
   - Phase 4.5 auto-fix loop (3 attempts)
   - Coverage thresholds (80%/75%)
   - Code review by dedicated agent

4. **Single System to Maintain**
   - All improvements to task-work benefit AutoBuild
   - No divergent code paths
   - Consistent behavior

5. **Agent Discovery Utilized**
   - Metadata-based matching
   - Template overrides work
   - Future agents automatically available

---

### EFFORT ANALYSIS

| Component | Effort | Notes |
|-----------|--------|-------|
| Modify `AgentInvoker.invoke_player()` | 2-3 hours | Replace SDK call with task-work delegation |
| Task state bridging | 1-2 hours | Ensure design_approved state |
| Feedback integration | 2-3 hours | Write/read feedback context |
| Testing | 2-3 hours | Test all paths |
| Documentation | 1 hour | Update CLAUDE.md, agent docs |
| **Total** | **8-12 hours** | Medium effort |

**Risk**: Low-Medium (using proven task-work infrastructure)

---

### ALTERNATIVE: Option A (Prompt-Only)

If Option B is deferred, Option A can be implemented as interim solution:

```python
# In _build_player_prompt()
prompt = f"""...
DEVELOPMENT_MODE: tdd

TDD Workflow (MANDATORY):
1. RED: Write failing tests FIRST - run them, confirm they fail
2. GREEN: Write MINIMAL code to pass tests
3. REFACTOR: Improve code quality without changing behavior

You MUST commit tests before implementation code.
Coach will verify TDD compliance via git history.
...
"""
```

**But**: This loses all subagent benefits and creates technical debt.

---

### RECOMMENDATION

**Implement Option B (task-work delegation)** for these reasons:
1. You've already built the subagent system - use it
2. task-work is proven and battle-tested
3. Avoids maintaining parallel implementation paths
4. Future task-work improvements automatically benefit AutoBuild
5. Stack-specific agents provide significantly better quality

**Effort**: 8-12 hours (Medium)
**Risk**: Low-Medium
**ROI**: Very High - leverages existing investment in subagent system

---

### Recommendation 4: Add Honesty Verification (Priority: MEDIUM)

**What**: Coach cross-references Player claims with actual results.

**Why**:
- Ralph enforces "intellectual honesty" at system level
- Current Player trusts Player's self-report
- Discrepancies indicate issues worth flagging

**Implementation**:
```python
# In Coach validation:
def verify_player_honesty(player_report, actual_test_output):
    if player_report["tests_passed"] != actual_test_output.all_passed:
        return {
            "honesty_discrepancy": True,
            "claim": player_report["tests_passed"],
            "reality": actual_test_output.all_passed
        }
```

**Effort**: Low (1-2 hours)
**Risk**: Very Low

---

### Recommendation 5: Enhanced Iteration Context (Priority: LOW)

**What**: Provide Player with structured summary of previous turns, not just last feedback.

**Why**:
- Ralph relies on file/git history (rich context)
- Current GuardKit only passes last Coach feedback
- Richer context could improve convergence

**Implementation**:
- Summarize all previous turns in Player prompt
- Include: what was tried, what failed, cumulative feedback
- Balance against token budget

**Effort**: Medium (2-3 hours)
**Risk**: Medium (token cost increase)

---

## Section 5: Risk/Effort Analysis

| Recommendation | Priority | Effort | Risk | ROI |
|----------------|----------|--------|------|-----|
| **task-work Delegation (Option B)** | **HIGH** | Medium (8-12h) | Low-Medium | **Very High** |
| Escape Hatch Pattern | HIGH | Low (1-2h) | Very Low | Very High |
| Promise-Based Completion | HIGH | Medium (2-4h) | Low | High |
| Honesty Verification | MEDIUM | Low (1-2h) | Very Low | Medium |
| Enhanced Iteration Context | LOW | Medium | Medium | Low |

**Key Insight from Deeper Analysis**: The task-work delegation (Option B) should be prioritized because:
1. Reuses existing subagent infrastructure instead of creating parallel paths
2. Stack-specific agents (python-api-specialist, react-specialist, etc.) provide better quality
3. Quality gates (Phase 4.5 fix loop, code-reviewer) come free
4. Single system to maintain going forward

**Note**: Option A (prompt-only TDD) is available as fallback but creates technical debt.

---

## Section 6: Implementation Roadmap

### Wave 1 (Foundation - 8-12 hours) - RECOMMENDED PRIORITY

**1. task-work Delegation (Option B) - THE BIG WIN**

| Component | Effort | Description |
|-----------|--------|-------------|
| `AgentInvoker.invoke_player()` | 2-3h | Replace SDK call with task-work delegation |
| Task state bridging | 1-2h | Ensure design_approved state for --implement-only |
| Feedback integration | 2-3h | Write Coach feedback to task context, read in Phase 3 |
| Testing | 2-3h | Test all paths (happy path, feedback loop, max turns) |
| Documentation | 1h | Update CLAUDE.md, agent docs |

**Benefits Unlocked**:
- Stack-specific subagents (python-api-specialist, react-specialist, etc.)
- TDD mode with structural enforcement
- Phase 4.5 auto-fix loop (3 attempts)
- Code-reviewer quality gate
- Coverage thresholds (80%/75%)

### Wave 2 (Quick Wins - 3-4 hours)

2. **Escape Hatch Pattern** - Add blocked_report to Player agent
   - When turn >= max_turns - 2, generate structured blocked report
   - Effort: 1-2 hours

3. **Honesty Verification** - Add cross-reference check to Coach
   - Coach verifies Player claims against actual test output
   - Effort: 1-2 hours

### Wave 3 (Enhancement - 2-4 hours)

4. **Promise-Based Completion** - Extend Player/Coach report schemas
   - Explicit completion promises with criteria verification
   - Effort: 2-4 hours

### Wave 4 (Future consideration)

5. **Enhanced Iteration Context** - Requires token budget analysis
   - Richer context from previous turns
   - Must balance against token costs

---

## Appendix A: Key Source Files Analyzed

### Ralph Wiggum
- `plugins/ralph-wiggum/hooks/stop-hook.sh` - Core loop mechanism
- `plugins/ralph-wiggum/commands/ralph-loop.md` - Command specification
- `plugins/ralph-wiggum/README.md` - Philosophy and best practices

### GuardKit
- [guardkit/orchestrator/autobuild.py](guardkit/orchestrator/autobuild.py) - Orchestrator implementation
- [guardkit/cli/autobuild.py](guardkit/cli/autobuild.py) - CLI commands
- [.claude/agents/autobuild-player.md](.claude/agents/autobuild-player.md) - Player agent spec
- [.claude/agents/autobuild-coach.md](.claude/agents/autobuild-coach.md) - Coach agent spec

---

## Appendix B: Architecture Scores

| Principle | Score | Notes |
|-----------|-------|-------|
| SOLID - Single Responsibility | 8/10 | Player/Coach separation is clean |
| SOLID - Open/Closed | 7/10 | Could be more extensible for new patterns |
| DRY | 8/10 | Good delegation to task-work quality gates |
| YAGNI | 9/10 | Minimal over-engineering |
| **Overall** | **76/100** | Good foundation, enhancement opportunities identified |

---

*Report generated: 2025-12-31*
*Review mode: architectural*
*Review depth: standard*
