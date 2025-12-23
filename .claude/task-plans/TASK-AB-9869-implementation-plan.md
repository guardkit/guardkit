# Implementation Plan: TASK-AB-9869 - AutoBuildOrchestrator

**Task ID**: TASK-AB-9869
**Complexity**: 7/10
**Estimated Duration**: 5-6 hours
**Wave**: 2 (Integration Phase)

---

## Executive Summary

Implement the AutoBuildOrchestrator class that coordinates the adversarial Player↔Coach loop using WorktreeManager, AgentInvoker, and ProgressDisplay. This is the central orchestration component that implements the three-phase execution pattern (Setup → Loop → Finalize) from Block AI Research.

### Key Design Decisions

1. **Pattern**: Three-phase orchestration (Setup, Loop, Finalize) with adversarial turn management
2. **Integration Strategy**: Dependency injection for all Wave 1 components (testability)
3. **State Management**: Immutable turn records with persistent history
4. **Error Handling**: Graceful degradation with worktree preservation on failure
5. **Quality Gates**: Coach approval required for merge, max turns enforced

---

## Architecture Overview

### Class Structure

```python
@dataclass(frozen=True)
class TurnRecord:
    """Immutable record of a Player↔Coach turn."""
    turn: int
    player_result: AgentInvocationResult
    coach_result: Optional[AgentInvocationResult]
    decision: Literal["approve", "feedback", "error"]
    feedback: Optional[str]
    timestamp: str

@dataclass
class OrchestrationResult:
    """Result of complete orchestration run."""
    task_id: str
    success: bool
    total_turns: int
    final_decision: Literal["approved", "max_turns_exceeded", "error"]
    turn_history: List[TurnRecord]
    worktree: Worktree
    error: Optional[str] = None

class AutoBuildOrchestrator:
    """
    Phase-based orchestration for adversarial Player↔Coach workflow.

    Three-Phase Execution:
    1. Setup: Create worktree, initialize display
    2. Loop: Player implements → Coach validates (max 5 turns)
    3. Finalize: Merge on approval OR preserve on failure

    Dependencies (Wave 1):
    - WorktreeManager: Isolated workspace management
    - AgentInvoker: SDK invocation for Player/Coach
    - ProgressDisplay: Real-time turn progress
    """
```

### Integration Pattern

```
┌──────────────────────────────────────────────────────────┐
│              AutoBuildOrchestrator                       │
│                                                          │
│  Phase 1: Setup                                         │
│  ├─ WorktreeManager.create() → Isolated workspace      │
│  ├─ ProgressDisplay.__enter__() → UI ready             │
│  └─ Initialize turn state (turn=1, history=[])         │
│                                                          │
│  Phase 2: Loop (max 5 turns)                           │
│  ├─ Turn N:                                             │
│  │   ├─ Display.start_turn(N, "Player Implementation") │
│  │   ├─ AgentInvoker.invoke_player() → Report         │
│  │   ├─ Display.complete_turn()                        │
│  │   │                                                  │
│  │   ├─ Display.start_turn(N, "Coach Validation")     │
│  │   ├─ AgentInvoker.invoke_coach() → Decision        │
│  │   ├─ Display.complete_turn()                        │
│  │   │                                                  │
│  │   └─ If approved: Exit loop                         │
│  │       If feedback: Continue to Turn N+1             │
│  │       If error: Handle gracefully                   │
│  │                                                      │
│  └─ Exit when: approved OR max_turns OR error          │
│                                                          │
│  Phase 3: Finalize                                      │
│  ├─ If approved:                                        │
│  │   ├─ WorktreeManager.merge() → Integrate work      │
│  │   └─ WorktreeManager.cleanup() → Remove worktree   │
│  │                                                      │
│  └─ If max_turns/error:                                │
│      └─ WorktreeManager.preserve_on_failure()          │
│                                                          │
│  ├─ Display.render_summary() → Final report            │
│  └─ Return OrchestrationResult                         │
└──────────────────────────────────────────────────────────┘
```

---

## Detailed Design

### 1. Constructor & Initialization

```python
def __init__(
    self,
    repo_root: Path,
    max_turns: int = 5,
    auto_merge: bool = False,
    worktree_manager: Optional[WorktreeManager] = None,
    agent_invoker: Optional[AgentInvoker] = None,
    progress_display: Optional[ProgressDisplay] = None,
):
    """
    Initialize orchestrator with dependencies.

    Args:
        repo_root: Repository root directory
        max_turns: Maximum adversarial turns (default: 5)
        auto_merge: Auto-merge on approval without human confirmation
        worktree_manager: Optional WorktreeManager (for DI/testing)
        agent_invoker: Optional AgentInvoker (for DI/testing)
        progress_display: Optional ProgressDisplay (for DI/testing)

    Design Notes:
    - Dependency injection enables unit testing with mocks
    - Default instances created if None provided (production path)
    - auto_merge flag for CI/CD automation
    """
```

**Rationale**: Constructor follows Dependency Inversion Principle from architectural review. Optional dependencies enable both production use and comprehensive testing.

### 2. Main Orchestration Method

```python
async def orchestrate(
    self,
    task_id: str,
    requirements: str,
    acceptance_criteria: List[str],
    base_branch: str = "main",
) -> OrchestrationResult:
    """
    Execute complete adversarial orchestration workflow.

    Three-Phase Execution:
    1. Setup Phase: Create worktree, initialize progress
    2. Loop Phase: Player↔Coach adversarial turns
    3. Finalize Phase: Merge or preserve, cleanup

    Args:
        task_id: Task identifier (e.g., "TASK-AB-001")
        requirements: Task requirements description
        acceptance_criteria: List of acceptance criteria
        base_branch: Branch to create worktree from

    Returns:
        OrchestrationResult with complete turn history

    Raises:
        OrchestrationError: If critical setup fails
    """
```

**Flow**:
1. Call `_setup_phase()` → Create worktree, initialize display
2. Call `_loop_phase()` → Execute Player↔Coach turns
3. Call `_finalize_phase()` → Merge or preserve, cleanup
4. Return `OrchestrationResult`

### 3. Phase 1: Setup

```python
def _setup_phase(
    self,
    task_id: str,
    base_branch: str,
) -> Worktree:
    """
    Phase 1: Create isolated workspace and initialize progress.

    Steps:
    1. Create worktree via WorktreeManager
    2. Initialize ProgressDisplay context manager
    3. Display setup confirmation

    Args:
        task_id: Task identifier
        base_branch: Branch to create from

    Returns:
        Created Worktree instance

    Raises:
        WorktreeCreationError: If worktree creation fails
    """
```

**Implementation Notes**:
- Use `WorktreeManager.create()` to get isolated workspace
- Enter `ProgressDisplay` context manager for cleanup guarantee
- Log setup completion with worktree path

### 4. Phase 2: Adversarial Loop

```python
async def _loop_phase(
    self,
    task_id: str,
    requirements: str,
    acceptance_criteria: List[str],
    worktree: Worktree,
) -> Tuple[List[TurnRecord], Literal["approved", "max_turns_exceeded", "error"]]:
    """
    Phase 2: Execute Player↔Coach adversarial loop.

    Loop Structure:
    - Turn 1: Player implements from scratch
    - Turn 2+: Player addresses Coach feedback
    - Exit: Coach approves OR max_turns OR critical error

    Args:
        task_id: Task identifier
        requirements: Task requirements
        acceptance_criteria: Acceptance criteria
        worktree: Isolated workspace

    Returns:
        Tuple of (turn_history, final_decision)

    Decision Logic:
    - "approved": Coach approved, ready to merge
    - "max_turns_exceeded": Loop limit reached
    - "error": Critical error, preserve worktree
    """
```

**Turn Execution**:

```python
async def _execute_turn(
    self,
    turn: int,
    task_id: str,
    requirements: str,
    worktree: Worktree,
    previous_feedback: Optional[str],
) -> TurnRecord:
    """
    Execute single Player→Coach turn.

    Steps:
    1. Display: start_turn(turn, "Player Implementation")
    2. Invoke: Player agent with requirements + feedback
    3. Display: complete_turn(status, summary)
    4. Display: start_turn(turn, "Coach Validation")
    5. Invoke: Coach agent with Player report
    6. Display: complete_turn(status, summary)
    7. Parse: Coach decision (approve/feedback)
    8. Return: TurnRecord

    Args:
        turn: Current turn number (1-indexed)
        task_id: Task identifier
        requirements: Task requirements
        worktree: Worktree path for agent invocation
        previous_feedback: Optional feedback from previous turn

    Returns:
        Immutable TurnRecord with complete turn data
    """
```

**Error Handling Strategy**:
- Player errors: Record in TurnRecord, continue to Coach for guidance
- Coach errors: Mark turn as error, exit loop (can't proceed without Coach)
- SDK timeouts: Treat as errors, preserve worktree for inspection

### 5. Phase 3: Finalize

```python
def _finalize_phase(
    self,
    worktree: Worktree,
    final_decision: Literal["approved", "max_turns_exceeded", "error"],
    turn_history: List[TurnRecord],
    target_branch: str = "main",
) -> None:
    """
    Phase 3: Merge approved work or preserve on failure.

    Decision Tree:
    - approved + auto_merge=True: Merge and cleanup
    - approved + auto_merge=False: Preserve for human review
    - max_turns_exceeded: Preserve for inspection
    - error: Preserve for debugging

    Args:
        worktree: Worktree to finalize
        final_decision: Loop exit reason
        turn_history: Complete turn history
        target_branch: Branch to merge into

    Side Effects:
    - May merge worktree and delete branch (approved path)
    - May preserve worktree (failure/review path)
    - Renders final summary via ProgressDisplay
    """
```

**Merge Logic**:
```python
if final_decision == "approved" and self.auto_merge:
    try:
        self._worktree_manager.merge(worktree, target_branch)
        self._worktree_manager.cleanup(worktree)
    except WorktreeMergeError as e:
        # Merge conflict - preserve for manual resolution
        self._worktree_manager.preserve_on_failure(worktree)
        raise
else:
    # Preserve for human review
    self._worktree_manager.preserve_on_failure(worktree)
```

**Summary Rendering**:
```python
self._progress_display.render_summary(
    total_turns=len(turn_history),
    final_status=final_decision,
    details=self._build_summary_details(turn_history, final_decision)
)
```

---

## Implementation Phases

### Phase A: Core Structure (1.5 hours)

**Files**:
- `guardkit/orchestrator/autobuild.py`

**Deliverables**:
1. Data classes: `TurnRecord`, `OrchestrationResult`
2. Class skeleton: `AutoBuildOrchestrator` with constructor
3. Exception: `OrchestrationError` in `exceptions.py`
4. Imports and type hints
5. Module docstring with examples

**Testing Strategy**:
- Import validation test
- Constructor test with defaults
- Constructor test with dependency injection

### Phase B: Setup Phase (1 hour)

**Deliverables**:
1. `_setup_phase()` implementation
2. Worktree creation error handling
3. ProgressDisplay initialization

**Testing Strategy**:
- Test successful setup
- Test WorktreeCreationError propagation
- Verify worktree path correct

### Phase C: Loop Phase (2 hours)

**Deliverables**:
1. `_loop_phase()` implementation
2. `_execute_turn()` implementation
3. Turn state management
4. Decision parsing logic

**Testing Strategy**:
- Test single turn (Player → Coach → approve)
- Test multi-turn (feedback loop)
- Test max turns exceeded
- Test error handling (Player error, Coach error, SDK timeout)

### Phase D: Finalize Phase (0.5 hours)

**Deliverables**:
1. `_finalize_phase()` implementation
2. Merge decision logic
3. Summary rendering

**Testing Strategy**:
- Test auto-merge on approval
- Test preserve on max_turns
- Test preserve on error
- Test merge conflict handling

### Phase E: Main Orchestration (0.5 hours)

**Deliverables**:
1. `orchestrate()` implementation
2. Phase coordination
3. Result building

**Testing Strategy**:
- End-to-end orchestration test
- Integration test with all dependencies

### Phase F: Documentation & Examples (0.5 hours)

**Deliverables**:
1. Comprehensive docstrings (NumPy style)
2. Usage examples in module docstring
3. `__all__` exports
4. Type hints validation

---

## Testing Strategy

### Unit Tests (guardkit/tests/unit/test_autobuild_orchestrator.py)

**Test Structure**:
```python
import pytest
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    TurnRecord,
    OrchestrationResult,
)
from guardkit.orchestrator.agent_invoker import AgentInvocationResult
from guardkit.orchestrator.exceptions import OrchestrationError

# Mock fixtures
@pytest.fixture
def mock_worktree_manager():
    """Mock WorktreeManager."""

@pytest.fixture
def mock_agent_invoker():
    """Mock AgentInvoker with async methods."""

@pytest.fixture
def mock_progress_display():
    """Mock ProgressDisplay."""

@pytest.fixture
def orchestrator(mock_worktree_manager, mock_agent_invoker, mock_progress_display):
    """Create orchestrator with mocked dependencies."""
    return AutoBuildOrchestrator(
        repo_root=Path("/fake/repo"),
        max_turns=3,
        worktree_manager=mock_worktree_manager,
        agent_invoker=mock_agent_invoker,
        progress_display=mock_progress_display,
    )
```

**Test Coverage**:

1. **Constructor Tests** (5 tests):
   - Default dependencies created
   - Custom dependencies injected
   - max_turns validation
   - auto_merge flag handling

2. **Setup Phase Tests** (3 tests):
   - Successful worktree creation
   - WorktreeCreationError propagation
   - Progress display initialization

3. **Loop Phase Tests** (8 tests):
   - Single turn approval
   - Multi-turn feedback loop
   - Max turns exceeded
   - Player error handling
   - Coach error handling
   - SDK timeout handling
   - Turn record immutability
   - Feedback accumulation

4. **Finalize Phase Tests** (5 tests):
   - Auto-merge on approval
   - Preserve on manual review
   - Preserve on max_turns
   - Preserve on error
   - Merge conflict handling

5. **Integration Tests** (3 tests):
   - End-to-end approval path
   - End-to-end max_turns path
   - End-to-end error path

**Target Coverage**: ≥85%

### Test Data Fixtures

```python
# Mock Player report (success)
MOCK_PLAYER_REPORT = {
    "task_id": "TASK-TEST-001",
    "turn": 1,
    "files_modified": ["src/auth.py"],
    "files_created": ["tests/test_auth.py"],
    "tests_written": ["tests/test_auth.py"],
    "tests_run": True,
    "tests_passed": True,
    "implementation_notes": "Implemented OAuth2 flow",
    "concerns": [],
    "requirements_addressed": ["OAuth2 authentication"],
    "requirements_remaining": [],
}

# Mock Coach decision (approval)
MOCK_COACH_APPROVAL = {
    "task_id": "TASK-TEST-001",
    "turn": 1,
    "decision": "approve",
    "validation_results": {
        "requirements_met": ["OAuth2 authentication"],
        "tests_run": True,
        "tests_passed": True,
    },
    "rationale": "All requirements met",
}

# Mock Coach decision (feedback)
MOCK_COACH_FEEDBACK = {
    "task_id": "TASK-TEST-001",
    "turn": 1,
    "decision": "feedback",
    "issues": [
        {
            "type": "test_failure",
            "severity": "major",
            "description": "Token refresh test failing",
            "suggestion": "Add mock for token endpoint",
        }
    ],
    "rationale": "Tests need improvement",
}
```

---

## Dependencies

### Wave 1 Components (Must Be Complete)

1. **WorktreeManager** (TASK-AB-F55D):
   - `create()` - Create isolated workspace
   - `merge()` - Integrate approved work
   - `cleanup()` - Remove worktree
   - `preserve_on_failure()` - Keep for inspection

2. **AgentInvoker** (TASK-AB-A76A):
   - `invoke_player()` - Execute Player agent
   - `invoke_coach()` - Execute Coach agent
   - Returns: `AgentInvocationResult`

3. **ProgressDisplay** (TASK-AB-584A):
   - `start_turn()` - Begin turn progress
   - `update_turn()` - Update status
   - `complete_turn()` - Finish turn
   - `render_summary()` - Final report
   - Context manager support

### External Dependencies

```python
# Standard library
import asyncio
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional, Tuple

# GuardKit internal
from guardkit.orchestrator.worktrees import WorktreeManager, Worktree
from guardkit.orchestrator.agent_invoker import AgentInvoker, AgentInvocationResult
from guardkit.orchestrator.progress import ProgressDisplay
from guardkit.orchestrator.exceptions import (
    OrchestrationError,
    WorktreeCreationError,
    WorktreeMergeError,
    AgentInvocationError,
)
```

---

## Error Handling Strategy

### Exception Hierarchy

```python
# New exception for orchestration
class OrchestrationError(Exception):
    """Base exception for orchestration errors."""
    pass

class SetupPhaseError(OrchestrationError):
    """Raised when setup phase fails."""
    pass

class LoopPhaseError(OrchestrationError):
    """Raised when loop phase encounters critical error."""
    pass

class FinalizePhaseError(OrchestrationError):
    """Raised when finalize phase fails."""
    pass
```

### Error Recovery

| Error Type | Phase | Recovery Strategy |
|------------|-------|-------------------|
| `WorktreeCreationError` | Setup | Raise `SetupPhaseError`, abort |
| `PlayerReportNotFoundError` | Loop | Record in TurnRecord, continue to Coach |
| `CoachDecisionInvalidError` | Loop | Exit loop, preserve worktree |
| `SDKTimeoutError` | Loop | Exit loop, preserve worktree |
| `WorktreeMergeError` | Finalize | Preserve worktree, raise `FinalizePhaseError` |

### Logging Strategy

```python
import logging

logger = logging.getLogger(__name__)

# Log levels:
# INFO: Phase transitions, turn completion
# DEBUG: Detailed turn data, agent responses
# WARNING: Non-critical errors (Player errors)
# ERROR: Critical errors (Coach errors, merge failures)
```

---

## Quality Gates

### Pre-Implementation Checklist

- [ ] WorktreeManager tests passing (TASK-AB-F55D)
- [ ] AgentInvoker tests passing (TASK-AB-A76A)
- [ ] ProgressDisplay tests passing (TASK-AB-584A)
- [ ] All Wave 1 branches merged to main

### Implementation Quality Gates

- [ ] Type hints on all public methods
- [ ] NumPy-style docstrings with examples
- [ ] `__all__` exports defined
- [ ] No cyclic imports
- [ ] Logging at appropriate levels

### Testing Quality Gates

- [ ] ≥85% line coverage
- [ ] ≥80% branch coverage
- [ ] All edge cases covered (max_turns, errors, timeouts)
- [ ] Integration test with real dependencies
- [ ] Mock isolation (no actual git operations in unit tests)

### Code Review Quality Gates

- [ ] Follows Python library patterns from .claude/rules/python-library.md
- [ ] Immutable data classes used for turn records
- [ ] Dependency injection for testability
- [ ] Context managers used appropriately
- [ ] Error messages actionable

---

## File Modifications Summary

### New Files

1. **guardkit/orchestrator/autobuild.py** (~400-500 lines)
   - AutoBuildOrchestrator class
   - TurnRecord dataclass
   - OrchestrationResult dataclass
   - Helper methods for phase execution

2. **tests/unit/test_autobuild_orchestrator.py** (~600-800 lines)
   - 24+ unit tests
   - Mock fixtures for dependencies
   - Integration tests
   - Test data fixtures

### Modified Files

1. **guardkit/orchestrator/exceptions.py**
   - Add `OrchestrationError` base class
   - Add phase-specific exceptions

2. **guardkit/orchestrator/__init__.py**
   - Add exports for `AutoBuildOrchestrator`
   - Add exports for `OrchestrationResult`

---

## Acceptance Criteria

### Functional Requirements

- [ ] Setup phase creates worktree successfully
- [ ] Loop phase executes Player→Coach turns
- [ ] Coach approval exits loop immediately
- [ ] Max turns limit enforced
- [ ] Finalize phase merges on approval (auto_merge=True)
- [ ] Finalize phase preserves on failure
- [ ] Progress display shows real-time updates
- [ ] Summary table rendered at completion

### Non-Functional Requirements

- [ ] ≥85% test coverage
- [ ] All tests passing
- [ ] Type hints complete
- [ ] Documentation comprehensive
- [ ] Error messages actionable
- [ ] Logging at appropriate levels

### Integration Requirements

- [ ] Works with WorktreeManager from Wave 1
- [ ] Works with AgentInvoker from Wave 1
- [ ] Works with ProgressDisplay from Wave 1
- [ ] No breaking changes to Wave 1 APIs

---

## Risk Assessment

### Medium Risks

1. **Async/Await Coordination**
   - Mitigation: Use pytest-asyncio, test async flows thoroughly

2. **Mock Complexity**
   - Mitigation: Create reusable fixtures, document mock behavior

3. **Error Handling Edge Cases**
   - Mitigation: Comprehensive error scenario tests

### Low Risks

1. **Worktree State Management**
   - Mitigation: WorktreeManager handles this (Wave 1)

2. **Progress Display Errors**
   - Mitigation: ProgressDisplay has warn strategy (Wave 1)

---

## Post-Implementation Tasks

### Documentation Updates

- [ ] Update main CLAUDE.md with AutoBuild workflow
- [ ] Add usage examples to orchestrator module
- [ ] Document error recovery strategies

### Integration Testing (Wave 4)

- [ ] End-to-end test with real task
- [ ] CLI integration (Wave 3)
- [ ] Performance benchmarking

---

## Appendix: Example Usage

```python
# Production usage
from pathlib import Path
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

async def main():
    orchestrator = AutoBuildOrchestrator(
        repo_root=Path.cwd(),
        max_turns=5,
        auto_merge=False,  # Require human approval
    )

    result = await orchestrator.orchestrate(
        task_id="TASK-AB-001",
        requirements="Implement OAuth2 authentication",
        acceptance_criteria=[
            "Support authorization code flow",
            "Handle token refresh",
            "Include comprehensive tests",
        ],
        base_branch="main",
    )

    print(f"Status: {result.final_decision}")
    print(f"Turns: {result.total_turns}")
    print(f"Worktree: {result.worktree.path}")

# Test usage
async def test_orchestration():
    mock_wm = Mock()
    mock_ai = AsyncMock()
    mock_pd = Mock()

    orchestrator = AutoBuildOrchestrator(
        repo_root=Path("/test"),
        worktree_manager=mock_wm,
        agent_invoker=mock_ai,
        progress_display=mock_pd,
    )

    # Test with controlled mocks
    result = await orchestrator.orchestrate(...)

    # Assertions on mock calls
    mock_wm.create.assert_called_once()
    mock_ai.invoke_player.assert_called()
    mock_ai.invoke_coach.assert_called()
```

---

## Summary

This implementation plan provides:

1. **Clear Architecture**: Three-phase pattern with dependency injection
2. **Comprehensive Design**: Detailed method signatures and flows
3. **Testing Strategy**: 24+ tests with ≥85% coverage target
4. **Error Handling**: Graceful degradation with worktree preservation
5. **Quality Gates**: Multiple checkpoints for implementation quality
6. **Integration Focus**: Coordinates all Wave 1 components seamlessly

Estimated total effort: **5-6 hours** (2h design, 3-4h implementation/testing)

The orchestrator serves as the central coordinator for AutoBuild Phase 1a, integrating WorktreeManager, AgentInvoker, and ProgressDisplay into a cohesive adversarial workflow system.
