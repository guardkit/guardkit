# AutoBuild Phase 1a: Adversarial Cooperation Extension for GuardKit

## Feature Overview

**Name**: AutoBuild - Autonomous Feature Implementation with Adversarial Cooperation  
**Type**: GuardKit Extension (Claude Agents SDK)  
**Priority**: P0  
**Estimated Complexity**: Medium-High

### Implementation Files

The following agent definitions have been created and are ready for use:

| File | Description |
|------|-------------|
| [`.claude/agents/autobuild-player.md`](../../../.claude/agents/autobuild-player.md) | Player agent definition - implementation focus |
| [`.claude/agents/autobuild-coach.md`](../../../.claude/agents/autobuild-coach.md) | Coach agent definition - validation focus |

### Implementation Files

The following agent definitions have been created and are ready for use:

| File | Description |
|------|-------------|
| [`.claude/agents/autobuild-player.md`](../../../.claude/agents/autobuild-player.md) | Player agent definition - implementation focus |
| [`.claude/agents/autobuild-coach.md`](../../../.claude/agents/autobuild-coach.md) | Coach agent definition - validation focus |  

### Summary

Extend GuardKit with an `/autobuild` capability that implements the **dialectical autocoding** pattern from Block AI Research. This enables autonomous feature implementation through a structured coach-player feedback loop, achieving higher completion rates than single-agent "vibe coding" approaches.

### Business Value

- **Autonomous execution**: Tasks complete without constant human supervision
- **Higher quality**: Coach validation catches issues human reviewers miss
- **Faster iteration**: 30-60 minute autonomous runs vs 5-minute human-supervised turns
- **Better testing**: Adversarial review ensures edge cases are covered
- **Nights & weekends**: Agents can work while humans are unavailable

---

## Research Foundation

### Block AI Research: Adversarial Cooperation in Code Synthesis (December 8, 2025)

**Source**: https://github.com/dhanji/g3

**Key Finding**: Dialectical autocoding achieves **5/5 completeness** vs **1-4.5/5** for single-agent approaches in comparative study.

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
│       Bounds: Max Turns, Context Windows, Requirements      │
└─────────────────────────────────────────────────────────────┘
```

**Why It Works**:

1. **Requirements Contract**: Both agents begin with the same goal requirements document - this provides consistent evaluation criteria and prevents drift.

2. **Fresh Context Each Turn**: Each turn starts with fresh agent instances to prevent context pollution. This maintains focus, objectivity, and clarity.

3. **Adversarial Validation**: The implementing agent often declares success prematurely. The coach performs independent evaluation, catching gaps the player missed.

4. **Bounded Process**: Turn limits (typically 5-10), explicit approval gates, and shared requirements create a structured, terminable process.

**Empirical Results** (from paper):

| Platform | Completeness | Notes |
|----------|--------------|-------|
| g3 (adversarial) | 5/5 | Meets all requirements, no crashes |
| Goose | 4.5/5 | Functional, occasional crashes |
| Antigravity | 3/5 | Crashes occasionally |
| OpenHands | 2/5 | Incomplete |
| VSCode Codex | 1/5 | Crashes on start |
| Cursor Pro | 1.5/5 | Unable to load repo |

**Ablation Study**: When coach feedback was withheld, the player went 4 rounds but produced non-functional code - "plausible code was written, tests were written, claimed to have implemented and tested everything, but was basically not functioning."

---

## Functional Requirements

### FR-1: Player Agent

The Player agent focuses on **implementation, creativity, and problem-solving**.

**Responsibilities**:
- Read task requirements and implement a solution
- Write code, create test harnesses, execute commands
- Respond to specific feedback with targeted improvements
- Optimized for code production and execution

**Behavior**:
- Works in isolated git worktree (no impact on main branch)
- Has full file system access (Read, Write, Edit, Bash)
- Produces structured report after each turn
- Does NOT declare task complete - only Coach can approve

**Report Format** (written to `.guardkit/autobuild/{task_id}/player_turn_{n}.json`):
```json
{
  "task_id": "TASK-XXX",
  "turn": 1,
  "files_modified": ["src/auth/oauth.py", "src/auth/tokens.py"],
  "files_created": ["src/auth/__init__.py"],
  "tests_written": ["tests/test_oauth.py"],
  "tests_passed": true,
  "implementation_notes": "Implemented OAuth2 flow with PKCE...",
  "concerns": ["Token refresh edge case needs verification"]
}
```

### FR-2: Coach Agent

The Coach agent focuses on **analysis, critique, and validation**.

**Responsibilities**:
- Validate implementations against original requirements
- Test compilation and functionality (actually run tests)
- Provide specific, actionable feedback
- Optimized for evaluation and guidance
- **Only the Coach can approve task completion**

**Behavior**:
- Read-only file system access (Read, Bash for running tests, no Write)
- Reads Player's report and independently verifies claims
- Compares implementation against requirements checklist
- Either APPROVES (terminates loop) or provides FEEDBACK (continues loop)

**Decision Format** (written to `.guardkit/autobuild/{task_id}/coach_turn_{n}.json`):

If APPROVING:
```json
{
  "task_id": "TASK-XXX",
  "turn": 1,
  "decision": "approve",
  "validation_results": {
    "requirements_met": ["All acceptance criteria verified"],
    "tests_passed": true,
    "code_quality": "Follows project conventions",
    "edge_cases_covered": ["Division by zero", "Empty input", "Auth failure"]
  },
  "rationale": "Implementation complete. All requirements verified..."
}
```

If providing FEEDBACK:
```json
{
  "task_id": "TASK-XXX",
  "turn": 1,
  "decision": "feedback",
  "issues": [
    {
      "severity": "must_fix",
      "category": "missing_requirement",
      "description": "HTTPS enforcement not implemented",
      "location": "src/server.py",
      "suggestion": "Add HTTPS redirect middleware before route handlers"
    },
    {
      "severity": "must_fix",
      "category": "test_failure",
      "description": "test_token_refresh fails with timeout",
      "location": "tests/test_oauth.py:45",
      "suggestion": "Check async handling in refresh flow"
    }
  ],
  "requirements_status": {
    "met": ["Basic OAuth flow", "Token generation"],
    "not_met": ["HTTPS enforcement", "Token refresh"],
    "not_tested": ["Rate limiting"]
  }
}
```

### FR-3: Orchestrator

The Python orchestrator manages the adversarial loop.

**Responsibilities**:
- Load task from `.guardkit/tasks/` (existing GuardKit format)
- Create isolated git worktree for the task
- Invoke Player via Claude Agents SDK
- Invoke Coach via Claude Agents SDK
- Pass Coach feedback to next Player turn
- Track turn count, enforce max turns
- Handle approval (merge) or failure (escalate)

**Loop Logic**:
```
1. Load task requirements
2. Create git worktree (branch: autobuild/{task_id})
3. FOR turn = 1 to max_turns:
   a. Invoke Player with requirements + previous feedback
   b. Wait for Player report
   c. Invoke Coach with requirements + Player report
   d. Read Coach decision
   e. IF decision == "approve":
        - Prompt user to merge
        - Merge worktree to main
        - RETURN success
   f. ELSE:
        - Extract feedback for next turn
        - CONTINUE
4. IF max_turns reached without approval:
   - RETURN failure (escalate to human)
```

### FR-4: Git Worktree Isolation

Each task runs in an isolated git worktree to prevent conflicts with main branch.

**Behavior**:
- Create branch: `autobuild/{task_id}`
- Create worktree: `.guardkit/worktrees/{task_id}/`
- All Player modifications happen in worktree
- Coach validates in same worktree
- On approval: merge branch to main, remove worktree
- On failure: preserve worktree for human review

### FR-5: CLI Commands

**Primary Command**:
```bash
guardkit autobuild task TASK-001 [options]
```

**Options**:
- `--max-turns N` - Maximum Player/Coach iterations (default: 5)
- `--auto-merge` - Merge on approval without confirmation
- `--player-model MODEL` - Model for Player (default: claude-sonnet-4-5-20250929)
- `--coach-model MODEL` - Model for Coach (default: claude-sonnet-4-5-20250929)
- `--dry-run` - Show what would be executed without running
- `--verbose` - Show detailed turn-by-turn output

**Additional Commands**:
```bash
guardkit autobuild feature FEAT-001  # Run all tasks in a feature
guardkit autobuild status TASK-001   # Show current autobuild status
guardkit autobuild resume TASK-001   # Resume interrupted run
```

### FR-6: Progress Display

Real-time feedback during execution using Rich library.

**Display**:
```
╭─ AutoBuild: TASK-001 ────────────────────────────────────────╮
│ Task: Implement OAuth2 authentication flow                   │
│ Status: Turn 2/5 - Coach validating...                       │
├──────────────────────────────────────────────────────────────┤
│ Turn 1:                                                      │
│   Player: ✓ Implemented (3 files, 2 tests)                   │
│   Coach:  ✗ Feedback (2 issues: HTTPS, token refresh)        │
│                                                              │
│ Turn 2:                                                      │
│   Player: ✓ Implemented (1 file modified)                    │
│   Coach:  ⏳ Validating...                                   │
╰──────────────────────────────────────────────────────────────╯
```

---

## Non-Functional Requirements

### NFR-1: Fresh Context Per Turn

Each agent invocation MUST use a fresh Claude Agents SDK session. This prevents context pollution and ensures each turn starts with clear focus.

```python
# Each turn creates NEW sessions
player_result = await query(prompt=player_prompt, options=player_options)
coach_result = await query(prompt=coach_prompt, options=coach_options)
```

### NFR-2: Requirements as Single Source of Truth

The original task requirements (from `.guardkit/tasks/TASK-XXX.md`) are the authoritative source. Both agents receive identical requirements. Neither agent can modify requirements.

### NFR-3: Coach Cannot Write Code

The Coach agent must be read-only to maintain adversarial integrity. Coach can:
- Read files
- Run tests (via Bash)
- Grep/search codebase

Coach cannot:
- Write or edit files
- Create new files
- Modify the implementation

### NFR-4: Bounded Execution

- Default max turns: 5
- Configurable up to 10
- Each turn should complete within 5 minutes (soft limit)
- Total execution should not exceed 60 minutes for typical tasks

### NFR-5: Graceful Failure

If max turns reached without approval:
- Preserve worktree for human inspection
- Save all turn reports
- Provide summary of what was attempted
- Exit with non-zero code

---

## Technical Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                    GuardKit (Existing)                          │
├─────────────────────────────────────────────────────────────────┤
│  .claude/commands/           .claude/agents/                    │
│  ├── feature-plan.md         ├── (existing agents)             │
│  ├── task-work.md            ├── autobuild-player.md  [NEW]    │
│  ├── task-create.md          └── autobuild-coach.md   [NEW]    │
│  └── autobuild.md [NEW]                                         │
├─────────────────────────────────────────────────────────────────┤
│                    Python Orchestrator [NEW]                    │
│  guardkit/cli/autobuild.py                                      │
│  ├── AutoBuildOrchestrator class                                │
│  ├── WorktreeManager class                                      │
│  └── CLI commands (Click)                                       │
├─────────────────────────────────────────────────────────────────┤
│                    Claude Agents SDK                            │
│  ├── query(prompt, options) → async generator                   │
│  └── ClaudeCodeOptions (cwd, allowed_tools, model, etc.)       │
└─────────────────────────────────────────────────────────────────┘
```

### File Structure

```
guardkit/
├── cli/
│   ├── __init__.py
│   ├── main.py              # Add autobuild group
│   └── autobuild.py         # [NEW] AutoBuild CLI commands
├── orchestrator/
│   ├── __init__.py          # [NEW]
│   ├── autobuild.py         # [NEW] AutoBuildOrchestrator
│   └── worktrees.py         # [NEW] WorktreeManager
└── ...

.claude/
├── agents/
│   ├── autobuild-player.md  # ✅ CREATED - Player agent definition
│   └── autobuild-coach.md   # ✅ CREATED - Coach agent definition
└── commands/
    └── autobuild.md         # [NEW] Optional slash command

.guardkit/
├── tasks/                   # Existing task files
│   └── TASK-001.md
├── autobuild/               # [NEW] AutoBuild working directory
│   └── TASK-001/
│       ├── player_turn_1.json
│       ├── coach_turn_1.json
│       ├── player_turn_2.json
│       └── coach_turn_2.json
└── worktrees/               # [NEW] Git worktrees
    └── TASK-001/            # Isolated worktree
```

### Claude Agents SDK Integration

```python
from claude_code_sdk import query, ClaudeCodeOptions

async def invoke_player(task_id: str, turn: int, feedback: str = None) -> dict:
    """Invoke Player agent via Claude Agents SDK."""
    
    prompt = f"""You are the Player agent. Implement the following task.

Task ID: {task_id}
Turn: {turn}

Requirements:
{load_task_requirements(task_id)}

{"Previous Coach Feedback:" + feedback if feedback else "This is your first turn."}

After implementing, write your report to:
.guardkit/autobuild/{task_id}/player_turn_{turn}.json
"""
    
    options = ClaudeCodeOptions(
        cwd=get_worktree_path(task_id),
        allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        permission_mode="acceptEdits",
        max_turns=30,
        model="claude-sonnet-4-5-20250929",
    )
    
    async for message in query(prompt=prompt, options=options):
        handle_message(message)
    
    return load_player_report(task_id, turn)


async def invoke_coach(task_id: str, turn: int) -> dict:
    """Invoke Coach agent via Claude Agents SDK."""
    
    player_report = load_player_report(task_id, turn)
    
    prompt = f"""You are the Coach agent. Validate the Player's implementation.

Task ID: {task_id}
Turn: {turn}

Original Requirements:
{load_task_requirements(task_id)}

Player's Report:
{json.dumps(player_report, indent=2)}

Your job:
1. Independently verify the Player's claims
2. Run the tests yourself
3. Check all requirements are met
4. Either APPROVE or provide specific FEEDBACK

Write your decision to:
.guardkit/autobuild/{task_id}/coach_turn_{turn}.json
"""
    
    options = ClaudeCodeOptions(
        cwd=get_worktree_path(task_id),
        allowed_tools=["Read", "Bash", "Grep", "Glob"],  # NO Write
        permission_mode="default",
        max_turns=20,
        model="claude-sonnet-4-5-20250929",
    )
    
    async for message in query(prompt=prompt, options=options):
        handle_message(message)
    
    return load_coach_decision(task_id, turn)
```

---

## Acceptance Criteria

### AC-1: Single Task Execution
- [ ] `guardkit autobuild task TASK-001` executes Player/Coach loop
- [ ] Player creates implementation in isolated worktree
- [ ] Coach validates and provides decision
- [ ] Loop continues until approval or max turns
- [ ] On approval, prompts user to merge

### AC-2: Player Agent Behavior
- [ ] Player reads task requirements from `.guardkit/tasks/`
- [ ] Player works in isolated worktree
- [ ] Player writes structured JSON report after each turn
- [ ] Player receives Coach feedback on subsequent turns
- [ ] Player has Read/Write/Edit/Bash permissions

### AC-3: Coach Agent Behavior
- [ ] Coach reads Player report and validates independently
- [ ] Coach runs tests (not just trusts Player's report)
- [ ] Coach compares implementation against requirements
- [ ] Coach writes JSON decision (approve/feedback)
- [ ] Coach is read-only (cannot modify files)

### AC-4: Git Worktree Management
- [ ] Worktree created at `.guardkit/worktrees/{task_id}/`
- [ ] Branch created as `autobuild/{task_id}`
- [ ] Worktree merged to main on approval
- [ ] Worktree preserved on failure for human review
- [ ] Worktree cleaned up after successful merge

### AC-5: Fresh Context Per Turn
- [ ] Each Player invocation uses new SDK session
- [ ] Each Coach invocation uses new SDK session
- [ ] No context carried between turns
- [ ] Feedback passed explicitly via prompt

### AC-6: CLI Interface
- [ ] `guardkit autobuild task TASK-ID` works
- [ ] `--max-turns` option configurable
- [ ] `--auto-merge` skips confirmation
- [ ] Progress displayed during execution
- [ ] Exit code reflects success/failure

### AC-7: Error Handling
- [ ] Graceful handling of SDK errors
- [ ] Timeout handling for long-running turns
- [ ] Clear error messages on failure
- [ ] State preserved for resume capability

---

## Test Strategy

### Unit Tests

```python
# tests/unit/test_autobuild_orchestrator.py

def test_orchestrator_loads_task():
    """Orchestrator correctly loads task from .guardkit/tasks/"""
    
def test_orchestrator_creates_worktree():
    """Worktree created with correct branch name"""
    
def test_orchestrator_respects_max_turns():
    """Loop terminates at max_turns if not approved"""
    
def test_coach_approval_terminates_loop():
    """Loop terminates immediately on coach approval"""
    
def test_feedback_passed_to_next_turn():
    """Coach feedback included in next Player prompt"""
```

### Integration Tests

```python
# tests/integration/test_autobuild_e2e.py

@pytest.mark.integration
async def test_autobuild_simple_task():
    """End-to-end test with a simple task that should complete in 1-2 turns"""
    result = await run_autobuild("TEST-SIMPLE")
    assert result.status == "approved"
    assert result.turns <= 3

@pytest.mark.integration
async def test_autobuild_requires_iteration():
    """Task that needs feedback loop to complete"""
    result = await run_autobuild("TEST-ITERATION")
    assert result.status == "approved"
    assert result.turns > 1  # Required iteration

@pytest.mark.integration
async def test_player_receives_feedback():
    """Verify Player's second turn includes Coach feedback"""
    # Use a task designed to fail first validation
    result = await run_autobuild("TEST-NEEDS-FIX", max_turns=3)
    
    turn_2_prompt = load_player_prompt("TEST-NEEDS-FIX", 2)
    assert "feedback" in turn_2_prompt.lower()
```

### Test Fixtures

Create test tasks in `.guardkit/tasks/`:

**TEST-SIMPLE.md** - Should complete in 1 turn:
```markdown
# Task: Add greeting function

Add a `greeting(name: str) -> str` function to `src/utils.py` that returns "Hello, {name}!".

## Acceptance Criteria
- [ ] Function exists at src/utils.py:greeting
- [ ] Returns "Hello, {name}!" format
- [ ] Has unit test in tests/test_utils.py
```

**TEST-ITERATION.md** - Requires 2+ turns (intentionally incomplete spec):
```markdown
# Task: Add user validation

Add input validation to the user registration endpoint.

## Acceptance Criteria
- [ ] Email format validated
- [ ] Password minimum length enforced
- [ ] Username uniqueness checked
- [ ] Appropriate error messages returned
```

---

## Dependencies

### Python Packages

```toml
# pyproject.toml additions
[project.dependencies]
claude-code-sdk = ">=0.1.0"
rich = ">=13.0"
click = ">=8.0"
```

### External Requirements

- Python 3.10+
- Git 2.20+ (for worktree support)
- Claude Code CLI 2.0.0+: `npm install -g @anthropic-ai/claude-code`
- Valid Claude API key (via Claude Max subscription or API)

---

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Player declares false success | High | Medium | Coach validates independently, runs tests |
| Coach too strict, never approves | Medium | High | Tune Coach prompts, configurable strictness |
| Context pollution between turns | Medium | Medium | Fresh SDK session each turn (by design) |
| Long-running turns timeout | Medium | Low | Configurable timeouts, progress updates |
| Worktree conflicts | Low | Medium | Unique branch names, cleanup on completion |
| SDK API changes | Low | Medium | Pin SDK version, wrap in adapter |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Task completion rate | ≥50% | Tasks approved without human intervention |
| Average turns to completion | ≤4 | Mean turns for approved tasks |
| Coach catch rate | >80% | Intentional bugs caught by Coach |
| Time to working prototype | ≤2 weeks | Calendar time to first working version |
| False approval rate | 0% | Approved tasks that don't meet requirements |

---

## Future Enhancements (Out of Scope for Phase 1a)

- **Multi-model**: Different models for Player vs Coach
- **Parallel tasks**: Run multiple tasks simultaneously
- **Feature-level orchestration**: Auto-run all tasks in a feature
- **Memory/context**: Persistent learning across tasks
- **Custom validation tools**: MCP-based validation extensions
- **Web UI**: Visual progress tracking and intervention

---

## References

1. Block AI Research. "Adversarial Cooperation in Code Synthesis." December 8, 2025. https://github.com/dhanji/g3
2. Claude Agents SDK Documentation. https://docs.anthropic.com/en/docs/claude-code/sdk
3. Git Worktrees. https://git-scm.com/docs/git-worktree
4. GuardKit Documentation. Internal.

---

## Appendix A: Example Coach Feedback (from Block AI paper)

```
**REQUIREMENTS COMPLIANCE:**
- ✅ Rust backend with Actix-web framework
- ✅ TypeScript frontend structure exists
- ✅ SQLite database with proper schema
- ✅ JWT authentication framework
- ✅ Email protocol support (IMAP/SMTP)
- ✅ REST API endpoints defined
- ❌ Frontend build system not functional
- ❌ Missing critical model definitions
- ❌ Incomplete authentication middleware

**IMMEDIATE ACTIONS NEEDED:**
1. Implement missing User model and other core models
2. Complete authentication middleware implementation
3. Resolve frontend dependency installation
4. Implement missing service methods
5. Add proper error handling for database operations
```

## Appendix B: Example Coach Approval (from Block AI paper)

```
📊 Validation Results

Error Handling
✅ Division by zero: {"error":{"code":"DIVISION_BY_ZERO"}}
✅ Negative sqrt: {"error":{"code":"NEGATIVE_SQRT"}}
✅ Unauthorized access: {"error":{"code":"UNAUTHORIZED"}}

Authentication Testing
✅ Correct Bearer token: Authentication successful
✅ Wrong Bearer token: Properly rejected (401 Unauthorized)
✅ Missing Authorization header: Properly rejected
✅ Malformed Authorization header: Properly rejected

Advanced Features
✅ Batch operations: Mixed success/error handling
✅ Expression evaluation: {"result":"14.00"} (2 + 3 * 4)
✅ Health endpoint: {"status":"ok"}
✅ TLS configuration: Certificate validation working

🎯 Final Status: COACH APPROVED
```
