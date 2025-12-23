# Review Report: TASK-REV-47D2

## Executive Summary

**Task**: Plan: Implement AutoBuild Phase 1a Python orchestrator for adversarial cooperation

**Review Mode**: Decision Analysis
**Review Depth**: Standard
**Completed**: 2025-12-23T07:20:00Z
**Reviewer**: Claude Sonnet 4.5

**Key Finding**: The AutoBuild Phase 1a feature is architecturally sound and ready for implementation with minor agent definition updates. The existing agent definitions (`autobuild-player.md` and `autobuild-coach.md`) require frontmatter compliance to match GuardKit template standards, but their content is well-designed and aligns with the Block AI research pattern.

**Recommendation**: Proceed with implementation using **Option 2: Modular Architecture with Phases** (recommended). This provides the best balance of maintainability, testability, and alignment with GuardKit's existing phase-based workflow.

---

## Review Details

**Mode**: Decision Analysis (architectural review + implementation planning)
**Depth**: Standard (1-2 hours)
**Duration**: 45 minutes
**Reviewer**: architectural-reviewer + software-architect agents

---

## 1. Agent Definition Review

### 1.1 Template Compliance Analysis

**Standard GuardKit Agent Template** (from `code-reviewer.md`):

```yaml
---
name: {agent-name}
description: {one-line description}
stack: [cross-stack | python | typescript | react]
phase: {phase-name}
capabilities: [cap1, cap2, cap3]
keywords: [keyword1, keyword2, keyword3]
model: sonnet | opus | haiku
tools: Read, Write, Edit, Bash, Grep, Glob
---
```

**Required Sections**:
1. Frontmatter with metadata
2. Role description
3. Boundaries (ALWAYS/NEVER/ASK)
4. Responsibilities/Capabilities
5. Process/Workflow
6. Examples and patterns
7. Language-specific guidelines (if applicable)

### 1.2 autobuild-player.md Analysis

**Current State**:
- ✅ Clear role description and responsibilities
- ✅ Well-defined output format (JSON report structure)
- ✅ Explicit guidelines for code quality and testing
- ✅ Clear boundaries (Player cannot declare success)
- ❌ **Missing frontmatter** with required metadata
- ❌ Missing "Boundaries" section (ALWAYS/NEVER/ASK format)
- ⚠️ Good content but needs restructuring to match template

**Required Updates**:

```yaml
---
name: autobuild-player
description: Implementation-focused agent for autonomous code generation in adversarial cooperation workflow
stack: [cross-stack]
phase: autobuild-implementation
capabilities: [code-generation, test-writing, requirement-implementation, feedback-response]
keywords: [autobuild, player, implementation, adversarial-cooperation, autonomous]
model: sonnet
tools: Read, Write, Edit, Bash, Grep, Glob
---
```

**Recommended Restructuring**:
1. Add frontmatter (above)
2. Restructure into Boundaries section:
   - **ALWAYS**: Write tests alongside implementation, run tests before reporting, be honest in reports, address all Coach feedback, work in isolated worktree
   - **NEVER**: Declare task complete (only Coach can approve), skip tests, write tests without running them, ignore Coach feedback, claim false success
   - **ASK**: When requirements are ambiguous, when implementation approach is unclear, when blocked on external dependencies

### 1.3 autobuild-coach.md Analysis

**Current State**:
- ✅ Clear validation-focused role
- ✅ Well-defined decision format (approve/feedback)
- ✅ Explicit read-only enforcement
- ✅ Comprehensive validation checklist
- ❌ **Missing frontmatter** with required metadata
- ❌ Missing "Boundaries" section (ALWAYS/NEVER/ASK format)
- ⚠️ Good content but needs restructuring to match template

**Required Updates**:

```yaml
---
name: autobuild-coach
description: Validation-focused agent for code review and approval in adversarial cooperation workflow
stack: [cross-stack]
phase: autobuild-validation
capabilities: [code-review, test-execution, requirement-validation, feedback-generation]
keywords: [autobuild, coach, validation, adversarial-cooperation, quality-gates]
model: sonnet
tools: Read, Bash, Grep, Glob
---
```

**Recommended Restructuring**:
1. Add frontmatter (above)
2. Restructure into Boundaries section:
   - **ALWAYS**: Run tests independently (don't trust Player's report), validate against every requirement, be specific in feedback (file paths, line numbers, exact issues), check for common Player mistakes (false success, skipped HTTPS, missing edge cases)
   - **NEVER**: Write code (read-only enforcement), approve incomplete work, skip requirements validation, accept false test claims, provide vague feedback
   - **ASK**: When requirements are ambiguous and Player didn't ask for clarification, when trade-offs between options are unclear, when quality standards should be relaxed for specific reasons

### 1.4 Progressive Disclosure

**Current State**: Both agents are standalone files with no `-ext.md` split.

**Recommendation**: For AutoBuild Phase 1a, keep agents as single files. Progressive disclosure not needed because:
- Agents are invoked programmatically (not loaded in Claude context)
- Agent content is consumed by SDK, not by human readers in chat
- Total size (~6KB + ~9KB = 15KB) is reasonable for SDK consumption

**Future Consideration**: If agents grow beyond 20KB each, consider splitting into core + extended for SDK optimization.

---

## 2. Orchestration Architecture Options

### Option 1: Monolithic Orchestrator (Simple)

**Architecture**:
```python
# guardkit/cli/autobuild.py
class AutoBuildOrchestrator:
    def __init__(self, task_id, max_turns=5):
        self.task_id = task_id
        self.max_turns = max_turns
        self.task = self.load_task()
        self.worktree = self.create_worktree()

    async def run(self):
        """Execute complete autobuild loop"""
        for turn in range(1, self.max_turns + 1):
            # Invoke Player
            player_report = await self.invoke_player(turn)

            # Invoke Coach
            coach_decision = await self.invoke_coach(turn, player_report)

            # Handle decision
            if coach_decision["decision"] == "approve":
                return await self.handle_approval()
            else:
                feedback = coach_decision["issues"]
                continue

        return await self.handle_max_turns_exceeded()
```

**Pros**:
- ✅ Simple to implement (~300 lines)
- ✅ Easy to understand
- ✅ Single class, single responsibility

**Cons**:
- ❌ Difficult to test in isolation
- ❌ Hard to extend with new features
- ❌ Mixes concerns (SDK invocation, worktree management, progress display)
- ❌ Not aligned with GuardKit's phase-based architecture

**Complexity**: Low (3/10)
**Effort**: 4-6 hours
**Maintainability**: Medium

---

### Option 2: Modular Architecture with Phases (Recommended)

**Architecture**:
```python
# guardkit/orchestrator/autobuild.py
class AutoBuildOrchestrator:
    def __init__(self, task_id, options: AutoBuildOptions):
        self.task_id = task_id
        self.options = options
        self.task_manager = TaskManager()
        self.worktree_manager = WorktreeManager()
        self.agent_invoker = AgentInvoker()
        self.progress_display = ProgressDisplay()

    async def run(self):
        """Execute autobuild with phase-based orchestration"""
        # Phase 1: Setup
        task = await self.phase_1_setup()

        # Phase 2: Adversarial Loop
        result = await self.phase_2_loop(task)

        # Phase 3: Finalization
        return await self.phase_3_finalize(result)

    async def phase_2_loop(self, task):
        """Adversarial cooperation loop"""
        for turn in range(1, self.options.max_turns + 1):
            # Turn A: Player implementation
            player_result = await self.execute_player_turn(turn, task)

            # Turn B: Coach validation
            coach_result = await self.execute_coach_turn(turn, player_result)

            # Decision point
            if coach_result.approved:
                return coach_result

            # Update feedback for next turn
            task.feedback = coach_result.feedback

        return self.create_max_turns_result()

# guardkit/orchestrator/worktrees.py
class WorktreeManager:
    """Manages git worktree lifecycle"""
    def create(self, task_id: str) -> Worktree: ...
    def merge(self, worktree: Worktree) -> None: ...
    def cleanup(self, worktree: Worktree) -> None: ...
    def preserve_on_failure(self, worktree: Worktree) -> None: ...

# guardkit/orchestrator/agent_invoker.py
class AgentInvoker:
    """Handles Claude Agents SDK invocation"""
    async def invoke_player(self, context: PlayerContext) -> PlayerReport: ...
    async def invoke_coach(self, context: CoachContext) -> CoachDecision: ...

# guardkit/orchestrator/progress.py
class ProgressDisplay:
    """Rich-based progress visualization"""
    def show_turn_start(self, turn: int, max_turns: int): ...
    def show_player_working(self): ...
    def show_coach_validating(self): ...
    def show_turn_result(self, result: TurnResult): ...
```

**Pros**:
- ✅ Separation of concerns (orchestration, worktree, SDK, display)
- ✅ Easy to test each component independently
- ✅ Easy to extend (add new turn types, validation modes)
- ✅ Aligns with GuardKit's phase-based architecture
- ✅ Reusable components (WorktreeManager can be used elsewhere)

**Cons**:
- ⚠️ More files to manage (~5 files vs 1)
- ⚠️ Slightly more complex initial setup

**Complexity**: Medium (6/10)
**Effort**: 8-12 hours
**Maintainability**: High

---

### Option 3: Event-Driven Architecture (Over-engineered)

**Architecture**:
```python
from dataclasses import dataclass
from typing import Protocol
from enum import Enum

class AutoBuildEvent(Enum):
    TURN_STARTED = "turn_started"
    PLAYER_COMPLETED = "player_completed"
    COACH_COMPLETED = "coach_completed"
    APPROVED = "approved"
    MAX_TURNS = "max_turns"

@dataclass
class Event:
    type: AutoBuildEvent
    data: dict

class EventHandler(Protocol):
    async def handle(self, event: Event) -> Event: ...

class AutoBuildOrchestrator:
    def __init__(self):
        self.handlers = {
            AutoBuildEvent.TURN_STARTED: TurnStartHandler(),
            AutoBuildEvent.PLAYER_COMPLETED: PlayerCompleteHandler(),
            AutoBuildEvent.COACH_COMPLETED: CoachCompleteHandler(),
            AutoBuildEvent.APPROVED: ApprovalHandler(),
            AutoBuildEvent.MAX_TURNS: MaxTurnsHandler(),
        }

    async def run(self, task_id: str):
        event = Event(AutoBuildEvent.TURN_STARTED, {"task_id": task_id, "turn": 1})

        while event.type != AutoBuildEvent.APPROVED:
            handler = self.handlers[event.type]
            event = await handler.handle(event)
```

**Pros**:
- ✅ Highly extensible (add handlers without modifying orchestrator)
- ✅ Event log for debugging
- ✅ Easy to add hooks (logging, metrics, notifications)

**Cons**:
- ❌ Over-engineered for Phase 1a scope
- ❌ Harder to understand control flow
- ❌ More boilerplate code
- ❌ Not necessary for single workflow

**Complexity**: High (8/10)
**Effort**: 16-20 hours
**Maintainability**: Medium (complexity vs extensibility trade-off)

---

## 3. Decision Matrix

| Criteria | Option 1: Monolithic | Option 2: Modular (✅ Recommended) | Option 3: Event-Driven |
|----------|---------------------|-----------------------------------|----------------------|
| **Complexity** | 3/10 (Simple) | 6/10 (Medium) | 8/10 (High) |
| **Effort** | 4-6 hours | 8-12 hours | 16-20 hours |
| **Testability** | Low | High | Very High |
| **Maintainability** | Medium | High | Medium |
| **Extensibility** | Low | High | Very High |
| **GuardKit Alignment** | Medium | High | Low |
| **Risk** | Low | Low | Medium (over-engineering) |
| **Time to First Working Version** | 1-2 days | 2-3 days | 4-5 days |

---

## 4. Recommended Approach (Option 2)

### 4.1 Implementation Breakdown

**Subtask 1**: Update agent definitions to match GuardKit template standards
- Add frontmatter to `autobuild-player.md`
- Add frontmatter to `autobuild-coach.md`
- Restructure into Boundaries sections (ALWAYS/NEVER/ASK)
- Complexity: 3/10
- Effort: 1-2 hours
- Method: Direct edit (no /task-work needed)

**Subtask 2**: Implement WorktreeManager class
- Create `guardkit/orchestrator/worktrees.py`
- Implement worktree creation (`git worktree add`)
- Implement branch management
- Implement merge and cleanup logic
- Implement failure preservation
- Add unit tests
- Complexity: 5/10
- Effort: 3-4 hours
- Method: /task-work (requires testing)

**Subtask 3**: Implement AgentInvoker class
- Create `guardkit/orchestrator/agent_invoker.py`
- Implement Player invocation via Claude Agents SDK
- Implement Coach invocation via Claude Agents SDK
- Handle SDK message streaming
- Parse JSON reports from agents
- Add error handling for SDK failures
- Add unit tests (mock SDK)
- Complexity: 6/10
- Effort: 4-5 hours
- Method: /task-work (requires testing)

**Subtask 4**: Implement ProgressDisplay class
- Create `guardkit/orchestrator/progress.py`
- Use Rich library for formatted output
- Implement turn-by-turn progress display
- Implement real-time status updates
- Add color coding (green=success, red=issues, yellow=in-progress)
- Complexity: 4/10
- Effort: 2-3 hours
- Method: /task-work (visual testing)

**Subtask 5**: Implement AutoBuildOrchestrator class
- Create `guardkit/orchestrator/autobuild.py`
- Implement phase-based orchestration (Setup, Loop, Finalize)
- Integrate WorktreeManager, AgentInvoker, ProgressDisplay
- Implement adversarial loop with turn management
- Implement approval handling (merge worktree)
- Implement failure handling (preserve worktree, escalate)
- Add integration tests
- Complexity: 7/10
- Effort: 5-6 hours
- Method: /task-work (requires integration testing)

**Subtask 6**: Implement CLI commands
- Update `guardkit/cli/main.py` to add autobuild group
- Create `guardkit/cli/autobuild.py` with Click commands
- Implement `guardkit autobuild task TASK-XXX` command
- Implement `--max-turns`, `--auto-merge`, `--model` options
- Implement `guardkit autobuild status TASK-XXX` command
- Add CLI help text and examples
- Complexity: 4/10
- Effort: 2-3 hours
- Method: /task-work (CLI testing)

**Subtask 7**: Integration testing and documentation
- Create end-to-end integration tests
- Test with simple task (TEST-SIMPLE: should complete in 1 turn)
- Test with iteration task (TEST-ITERATION: requires 2+ turns)
- Test max turns exceeded scenario
- Update CLAUDE.md with AutoBuild documentation
- Create usage examples
- Complexity: 5/10
- Effort: 3-4 hours
- Method: /task-work (comprehensive testing)

### 4.2 Dependency Graph

```
Subtask 1 (Agent Definitions) ─┐
                                ├─► Subtask 2 (WorktreeManager) ─┐
                                │                                 │
                                ├─► Subtask 3 (AgentInvoker) ────┤
                                │                                 │
                                └─► Subtask 4 (ProgressDisplay) ─┴─► Subtask 5 (Orchestrator) ─► Subtask 6 (CLI) ─► Subtask 7 (Testing)
```

**Parallel Execution Opportunities**:
- **Wave 1** (parallel): Subtask 1, Subtask 2, Subtask 3, Subtask 4 (4 tasks, no dependencies)
- **Wave 2** (sequential): Subtask 5 (requires Wave 1 completion)
- **Wave 3** (sequential): Subtask 6 (requires Subtask 5)
- **Wave 4** (sequential): Subtask 7 (requires Subtask 6)

**Conductor Recommendation**: Use Conductor for Wave 1 parallelization to complete 4 tasks simultaneously, reducing total time from ~12 hours to ~6 hours.

### 4.3 Total Effort Estimate

| Wave | Tasks | Effort (Sequential) | Effort (Parallel with Conductor) |
|------|-------|--------------------|---------------------------------|
| Wave 1 | Subtasks 1-4 | 10-14 hours | 4-5 hours |
| Wave 2 | Subtask 5 | 5-6 hours | 5-6 hours |
| Wave 3 | Subtask 6 | 2-3 hours | 2-3 hours |
| Wave 4 | Subtask 7 | 3-4 hours | 3-4 hours |
| **Total** | 7 subtasks | **20-27 hours** | **14-18 hours** (33% faster) |

---

## 5. Technical Risks and Mitigations

### Risk 1: Claude Agents SDK API Changes

**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Pin SDK version in `pyproject.toml`: `claude-code-sdk = "~=0.1.0"`
- Wrap SDK in adapter pattern (`AgentInvoker` serves this purpose)
- If SDK changes, only `AgentInvoker` needs updates

### Risk 2: Player Declares False Success

**Likelihood**: High (per Block AI research)
**Impact**: Medium
**Mitigation**:
- Coach validates independently (by design)
- Coach runs tests independently (mandatory)
- Coach checks every requirement explicitly

### Risk 3: Coach Too Strict, Never Approves

**Likelihood**: Medium
**Impact**: High
**Mitigation**:
- Tune Coach prompts during testing
- Add `--coach-strictness` option (strict/balanced/lenient)
- Monitor approval rates in metrics
- Human escalation after max turns (by design)

### Risk 4: Context Pollution Between Turns

**Likelihood**: Medium
**Impact**: Medium
**Mitigation**:
- Fresh SDK session each turn (explicitly enforced in `AgentInvoker`)
- No shared state between turns except explicit feedback JSON
- Verified by NFR-1 in spec

### Risk 5: Long-Running Turns Timeout

**Likelihood**: Medium
**Impact**: Low
**Mitigation**:
- Configurable timeouts in `AutoBuildOptions`
- Progress updates streamed from SDK
- Turn timeout warnings before hard failure
- Preserve worktree on timeout for manual inspection

### Risk 6: Worktree Conflicts

**Likelihood**: Low
**Impact**: Medium
**Mitigation**:
- Unique branch names: `autobuild/{task_id}` (deterministic, no collisions)
- Cleanup on completion (by design)
- Preserve on failure (by design)
- Test cleanup logic thoroughly

---

## 6. Architecture Diagrams

### 6.1 Component Interaction

```
┌─────────────────────────────────────────────────────────────────┐
│                    CLI Layer (Click)                             │
│  guardkit autobuild task TASK-XXX [--max-turns 5] [--auto-merge]│
└─────────────────┬───────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────┐
│           AutoBuildOrchestrator (orchestrator/autobuild.py)      │
│                                                                  │
│  Phase 1: Setup                                                  │
│    ├─ Load task from tasks/                                      │
│    └─ Create isolated git worktree                               │
│                                                                  │
│  Phase 2: Adversarial Loop (turns 1 to max_turns)                │
│    ├─ Invoke Player (implementation)                             │
│    ├─ Invoke Coach (validation)                                  │
│    └─ IF approved: RETURN success                                │
│        ELSE: feedback → next turn                                 │
│                                                                  │
│  Phase 3: Finalization                                           │
│    ├─ IF approved: Merge worktree → main                         │
│    └─ IF failed: Preserve worktree, escalate                     │
└──────┬────────────────┬────────────────┬─────────────────────────┘
       │                │                │
       ▼                ▼                ▼
┌────────────┐  ┌──────────────┐  ┌────────────────┐
│ Worktree   │  │ Agent        │  │ Progress       │
│ Manager    │  │ Invoker      │  │ Display        │
│            │  │              │  │                │
│ • create() │  │ • invoke_    │  │ • show_turn_   │
│ • merge()  │  │   player()   │  │   start()      │
│ • cleanup()│  │ • invoke_    │  │ • show_player_ │
│ • preserve │  │   coach()    │  │   working()    │
│   _on_     │  │ • parse_     │  │ • show_coach_  │
│   failure()│  │   report()   │  │   validating() │
└────────────┘  └──────┬───────┘  └────────────────┘
                       │
                       ▼
                ┌──────────────────┐
                │ Claude Agents SDK │
                │                   │
                │ query(prompt,     │
                │       options)    │
                └──────────────────┘
```

### 6.2 Turn-Based Workflow

```
Turn 1:
  ┌───────────────────────────────────────────────────────────┐
  │ Player (fresh context)                                     │
  │ • Read requirements                                        │
  │ • Implement solution                                       │
  │ • Write tests                                              │
  │ • Run tests                                                │
  │ • Write report → .guardkit/autobuild/TASK-XXX/player_1.json│
  └────────────────────────┬──────────────────────────────────┘
                           │ player_report
                           ▼
  ┌───────────────────────────────────────────────────────────┐
  │ Coach (fresh context)                                      │
  │ • Read requirements                                        │
  │ • Read player_report                                       │
  │ • Validate independently                                   │
  │ • Run tests independently                                  │
  │ • Write decision → .guardkit/autobuild/TASK-XXX/coach_1.json│
  └────────────────────────┬──────────────────────────────────┘
                           │ decision
                           ▼
                   ┌──────────────┐
                   │ IF approve:  │───► Merge → Success
                   │ ELSE:        │───► feedback → Turn 2
                   └──────────────┘

Turn 2 (with feedback):
  ┌───────────────────────────────────────────────────────────┐
  │ Player (fresh context + feedback from Turn 1)              │
  │ • Read requirements                                        │
  │ • Read Coach feedback                                      │
  │ • Address issues systematically                            │
  │ • Re-run ALL tests                                         │
  │ • Write report → .guardkit/autobuild/TASK-XXX/player_2.json│
  └────────────────────────┬──────────────────────────────────┘
                           │ player_report
                           ▼
  ┌───────────────────────────────────────────────────────────┐
  │ Coach (fresh context)                                      │
  │ • Validate against requirements                            │
  │ • Check Player addressed all feedback                      │
  │ • Run tests                                                │
  │ • Write decision → .guardkit/autobuild/TASK-XXX/coach_2.json│
  └────────────────────────┬──────────────────────────────────┘
                           │ decision
                           ▼
                   ┌──────────────┐
                   │ IF approve:  │───► Merge → Success
                   │ ELSE:        │───► feedback → Turn 3
                   └──────────────┘
```

---

## 7. Quality Gates Integration

AutoBuild integrates with GuardKit's existing quality gates:

**Pre-AutoBuild** (human creates task):
- `/task-create` generates task with requirements

**During AutoBuild** (autonomous):
- Player implements with tests
- Coach validates:
  - ✅ Compilation (100% - blocks approval)
  - ✅ Tests pass (100% - blocks approval)
  - ✅ Requirements met (100% - blocks approval)
  - ✅ Code quality (subjective - Coach discretion)

**Post-AutoBuild** (human reviews merge):
- Human reviews Coach's approval decision
- Human decides whether to merge worktree
- If approved: merge to main, cleanup worktree
- If rejected: preserve worktree, escalate to manual `/task-work`

**Benefits**:
- Maintains human oversight (merge approval)
- Leverages autonomous iteration (Player/Coach loop)
- Quality gates enforced by Coach (no bypassing)

---

## 8. Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Agent template compliance | 100% | Frontmatter validation, section structure check |
| Architecture clarity | 9/10 | Peer review of class structure, responsibilities |
| Implementation breakdown | 7 subtasks, 14-18 hours total | Detailed effort estimates provided |
| Integration risk | Low | Clear interfaces, mocked dependencies, testable components |
| Documentation quality | Complete | Implementation guide, architecture diagrams, decision rationale |
| Task completion rate (after implementation) | ≥50% | Tasks approved without human intervention |
| Average turns to completion (after implementation) | ≤4 | Mean turns for approved tasks |
| Coach catch rate (after implementation) | >80% | Intentional bugs caught by Coach |
| False approval rate (after implementation) | 0% | Approved tasks that don't meet requirements |

---

## 9. Recommendations

### 9.1 Immediate Actions (Subtask 1)

1. **Update `autobuild-player.md`**:
   - Add frontmatter with metadata
   - Restructure into Boundaries section
   - Preserve existing content quality
   - Estimated time: 30 minutes

2. **Update `autobuild-coach.md`**:
   - Add frontmatter with metadata
   - Restructure into Boundaries section
   - Preserve existing content quality
   - Estimated time: 30 minutes

### 9.2 Implementation Strategy (Subtasks 2-7)

**Recommended Approach**: **Option 2 - Modular Architecture with Phases**

**Rationale**:
- ✅ Aligns with GuardKit's phase-based architecture
- ✅ High testability (each component tests independently)
- ✅ High maintainability (clear separation of concerns)
- ✅ Reasonable complexity (6/10) for team skillset
- ✅ Moderate effort (14-18 hours with Conductor parallelization)
- ✅ Extensible for future phases (multi-model, parallel tasks, memory/context)

**Execution**:
- **Wave 1** (parallel): Subtasks 1-4 (use Conductor for 4 simultaneous worktrees)
- **Wave 2** (sequential): Subtask 5 (orchestrator integration)
- **Wave 3** (sequential): Subtask 6 (CLI implementation)
- **Wave 4** (sequential): Subtask 7 (integration testing)

### 9.3 Risk Mitigation

1. **Pin Claude Agents SDK version** to prevent breaking changes
2. **Extensive Coach prompt tuning** during testing phase to balance strictness
3. **Fresh context enforcement** at SDK invocation layer (no shared state)
4. **Comprehensive timeout handling** with progress streaming
5. **Unique worktree branch naming** to prevent collisions

### 9.4 Future Enhancements (Out of Scope for Phase 1a)

- **Multi-model support**: Different models for Player vs Coach
- **Parallel tasks**: Run multiple tasks simultaneously
- **Feature-level orchestration**: Auto-run all tasks in a feature
- **Memory/context**: Persistent learning across tasks
- **Custom validation tools**: MCP-based validation extensions
- **Web UI**: Visual progress tracking and intervention
- **Metrics dashboard**: Completion rates, average turns, Coach effectiveness

---

## 10. Appendix

### A. File Structure After Implementation

```
guardkit/
├── cli/
│   ├── __init__.py
│   ├── main.py              # ✅ Updated (add autobuild group)
│   └── autobuild.py         # ✅ NEW (Subtask 6)
├── orchestrator/
│   ├── __init__.py          # ✅ NEW
│   ├── autobuild.py         # ✅ NEW (Subtask 5)
│   ├── worktrees.py         # ✅ NEW (Subtask 2)
│   ├── agent_invoker.py     # ✅ NEW (Subtask 3)
│   └── progress.py          # ✅ NEW (Subtask 4)
└── ...

.claude/
├── agents/
│   ├── autobuild-player.md  # ✅ Updated (Subtask 1)
│   └── autobuild-coach.md   # ✅ Updated (Subtask 1)
└── commands/
    └── autobuild.md         # ⚠️ Optional (slash command wrapper)

.guardkit/
├── tasks/                   # Existing task files
├── autobuild/               # ✅ NEW (created by orchestrator)
│   └── TASK-XXX/
│       ├── player_turn_1.json
│       ├── coach_turn_1.json
│       └── ...
└── worktrees/               # ✅ NEW (created by WorktreeManager)
    └── TASK-XXX/            # Isolated worktree

tests/
├── unit/
│   ├── test_worktree_manager.py  # ✅ NEW (Subtask 2)
│   ├── test_agent_invoker.py     # ✅ NEW (Subtask 3)
│   └── test_progress_display.py  # ✅ NEW (Subtask 4)
├── integration/
│   └── test_autobuild_e2e.py     # ✅ NEW (Subtask 7)
└── fixtures/
    ├── TEST-SIMPLE.md            # ✅ NEW (Subtask 7)
    └── TEST-ITERATION.md         # ✅ NEW (Subtask 7)
```

### B. Example Usage (After Implementation)

```bash
# Basic usage
guardkit autobuild task TASK-042

# With options
guardkit autobuild task TASK-042 --max-turns 3 --auto-merge

# Check status
guardkit autobuild status TASK-042

# Resume interrupted run
guardkit autobuild resume TASK-042
```

**Expected Output**:
```
╭─ AutoBuild: TASK-042 ────────────────────────────────────────╮
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

### C. Test Strategy

**Unit Tests** (Subtasks 2-4):
```python
# tests/unit/test_worktree_manager.py
def test_worktree_creates_branch():
    manager = WorktreeManager()
    worktree = manager.create("TASK-042")
    assert worktree.branch == "autobuild/TASK-042"
    assert worktree.path.exists()

def test_worktree_cleanup_removes_directory():
    manager = WorktreeManager()
    worktree = manager.create("TASK-042")
    manager.cleanup(worktree)
    assert not worktree.path.exists()
```

**Integration Tests** (Subtask 7):
```python
# tests/integration/test_autobuild_e2e.py
@pytest.mark.integration
async def test_autobuild_simple_task():
    """End-to-end test with a simple task that should complete in 1-2 turns"""
    result = await run_autobuild("TEST-SIMPLE")
    assert result.status == "approved"
    assert result.turns <= 3
    assert result.tests_passed == True

@pytest.mark.integration
async def test_autobuild_requires_iteration():
    """Task that needs feedback loop to complete"""
    result = await run_autobuild("TEST-ITERATION")
    assert result.status == "approved"
    assert result.turns > 1  # Required iteration
```

### D. Block AI Research Alignment

**Research Claims** (from https://github.com/dhanji/g3):
1. ✅ Fresh context each turn (NFR-1: enforced by `AgentInvoker`)
2. ✅ Requirements as single source of truth (NFR-2: loaded from task file)
3. ✅ Coach cannot write code (NFR-3: read-only tools in `AgentInvoker`)
4. ✅ Bounded execution (NFR-4: max turns enforced by orchestrator)
5. ✅ Adversarial validation (FR-2: Coach validates independently)

**Expected Results** (per research):
- ✅ 5/5 completeness (vs 1-4.5 for single-agent)
- ✅ Player declares false success, Coach catches it
- ✅ Iterative refinement produces working code
- ✅ Comprehensive test coverage enforced by Coach

---

## Review Conclusion

**Status**: ✅ **READY FOR IMPLEMENTATION**

**Decision**: Approve architecture with **Option 2: Modular Architecture with Phases**

**Next Steps**:
1. User reviews findings and recommendations
2. User chooses decision at checkpoint ([A]ccept/[I]mplement/[R]evise/[C]ancel)
3. If [I]mplement chosen, auto-generate 7 subtasks based on this review
4. Execute implementation in 4 waves (Wave 1 with Conductor parallelization)

**Total Estimated Effort**: 14-18 hours (with Conductor) or 20-27 hours (sequential)

**Risk Level**: Low (clear interfaces, testable components, proven pattern from research)

**Quality Confidence**: High (aligns with GuardKit architecture, follows proven adversarial cooperation pattern)

---

**Reviewer**: Claude Sonnet 4.5
**Review Completed**: 2025-12-23T07:20:00Z
**Report Version**: 1.0
