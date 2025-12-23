# Implementation Plan: TASK-AB-A76A - Implement AgentInvoker Class

**Task ID**: TASK-AB-A76A
**Title**: Implement AgentInvoker class
**Complexity**: 6/10
**Priority**: high
**Wave**: 1 (Parallel execution ready)
**Estimated Duration**: 4-5 hours
**Parent Review**: TASK-REV-47D2

---

## 1. Overview

Create `guardkit/orchestrator/agent_invoker.py` with the `AgentInvoker` class responsible for invoking Player and Coach agents via the Claude Agents SDK. This component is the bridge between the orchestration layer and the AI agents, managing agent sessions, context preparation, and response handling.

### Key Responsibilities

1. Invoke Player and Coach agents via Claude Agents SDK
2. Manage fresh context per turn (no context pollution)
3. Handle SDK integration with appropriate permissions per agent type
4. Parse and validate agent responses (JSON reports)
5. Provide error handling and timeout management
6. Support async/await pattern for concurrent operations

---

## 2. Architecture Design

### 2.1 Class Structure

```python
# guardkit/orchestrator/agent_invoker.py

from typing import Dict, Any, Optional, AsyncGenerator
from dataclasses import dataclass
from pathlib import Path
import json
import asyncio

@dataclass
class AgentInvocationResult:
    """Result of an agent invocation."""
    task_id: str
    turn: int
    agent_type: str  # "player" or "coach"
    success: bool
    report: Dict[str, Any]  # Parsed JSON from agent
    duration_seconds: float
    error: Optional[str] = None


class AgentInvoker:
    """Handles Claude Agents SDK invocation for Player and Coach agents."""

    def __init__(
        self,
        worktree_path: Path,
        max_turns_per_agent: int = 30,
        player_model: str = "claude-sonnet-4-5-20250929",
        coach_model: str = "claude-sonnet-4-5-20250929",
    ):
        """
        Initialize AgentInvoker.

        Args:
            worktree_path: Path to the isolated git worktree
            max_turns_per_agent: Maximum turns per agent invocation
            player_model: Model to use for Player agent
            coach_model: Model to use for Coach agent
        """
        self.worktree_path = worktree_path
        self.max_turns_per_agent = max_turns_per_agent
        self.player_model = player_model
        self.coach_model = coach_model

    async def invoke_player(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        feedback: Optional[str] = None,
    ) -> AgentInvocationResult:
        """
        Invoke Player agent via Claude Agents SDK.

        Args:
            task_id: Task identifier (e.g., "TASK-001")
            turn: Current turn number (1-based)
            requirements: Task requirements (from task markdown)
            feedback: Optional Coach feedback from previous turn

        Returns:
            AgentInvocationResult with Player's report

        Raises:
            AgentInvocationError: If invocation fails
            PlayerReportNotFoundError: If Player doesn't create report
            PlayerReportInvalidError: If report JSON is malformed
        """

    async def invoke_coach(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        player_report: Dict[str, Any],
    ) -> AgentInvocationResult:
        """
        Invoke Coach agent via Claude Agents SDK.

        Args:
            task_id: Task identifier
            turn: Current turn number
            requirements: Original task requirements
            player_report: Player's report from current turn

        Returns:
            AgentInvocationResult with Coach's decision

        Raises:
            AgentInvocationError: If invocation fails
            CoachDecisionNotFoundError: If Coach doesn't create decision
            CoachDecisionInvalidError: If decision JSON is malformed
        """

    def _build_player_prompt(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        feedback: Optional[str],
    ) -> str:
        """Build prompt for Player agent invocation."""

    def _build_coach_prompt(
        self,
        task_id: str,
        turn: int,
        requirements: str,
        player_report: Dict[str, Any],
    ) -> str:
        """Build prompt for Coach agent invocation."""

    async def _invoke_sdk(
        self,
        prompt: str,
        agent_type: str,
        allowed_tools: list[str],
        permission_mode: str,
        model: str,
    ) -> AsyncGenerator[Any, None]:
        """
        Low-level SDK invocation.

        Args:
            prompt: Formatted prompt for agent
            agent_type: "player" or "coach"
            allowed_tools: List of allowed SDK tools
            permission_mode: "acceptEdits" or "default"
            model: Model identifier

        Yields:
            SDK message objects (for progress tracking)
        """

    def _load_agent_report(
        self,
        task_id: str,
        turn: int,
        agent_type: str,
    ) -> Dict[str, Any]:
        """
        Load and validate agent report JSON.

        Args:
            task_id: Task identifier
            turn: Turn number
            agent_type: "player" or "coach"

        Returns:
            Parsed JSON report

        Raises:
            ReportNotFoundError: If report file doesn't exist
            ReportInvalidError: If JSON is malformed
        """

    def _validate_player_report(self, report: Dict[str, Any]) -> None:
        """Validate Player report has required fields."""

    def _validate_coach_decision(self, decision: Dict[str, Any]) -> None:
        """Validate Coach decision has required fields."""
```

### 2.2 Custom Exceptions

```python
# guardkit/orchestrator/exceptions.py

class AgentInvokerError(Exception):
    """Base exception for AgentInvoker errors."""
    pass

class AgentInvocationError(AgentInvokerError):
    """Raised when SDK invocation fails."""
    pass

class PlayerReportNotFoundError(AgentInvokerError):
    """Raised when Player doesn't create report."""
    pass

class PlayerReportInvalidError(AgentInvokerError):
    """Raised when Player report JSON is malformed."""
    pass

class CoachDecisionNotFoundError(AgentInvokerError):
    """Raised when Coach doesn't create decision."""
    pass

class CoachDecisionInvalidError(AgentInvokerError):
    """Raised when Coach decision JSON is malformed."""
    pass

class SDKTimeoutError(AgentInvokerError):
    """Raised when SDK invocation times out."""
    pass
```

---

## 3. Dependencies and Imports

### 3.1 External Dependencies

```python
# Will need to add to pyproject.toml (or similar)
claude-code-sdk = "~=0.1.0"  # Pin to prevent breaking changes during Wave 1
```

### 3.2 Standard Library Imports

```python
import asyncio
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional, AsyncGenerator, Literal
```

### 3.3 Claude Agents SDK Imports

```python
from claude_code_sdk import query, ClaudeCodeOptions
```

**Note**: The exact SDK import path needs verification. Based on the feature spec pseudocode, this is the expected pattern, but actual SDK may differ slightly.

### 3.4 Internal Imports

```python
from guardkit.orchestrator.exceptions import (
    AgentInvocationError,
    PlayerReportNotFoundError,
    PlayerReportInvalidError,
    CoachDecisionNotFoundError,
    CoachDecisionInvalidError,
    SDKTimeoutError,
)
```

---

## 4. Implementation Details

### 4.1 Player Agent Invocation

**Prompt Template**:
```python
def _build_player_prompt(self, task_id, turn, requirements, feedback):
    return f"""You are the Player agent. Implement the following task.

Task ID: {task_id}
Turn: {turn}

Requirements:
{requirements}

{self._format_feedback_section(feedback, turn)}

After implementing, write your report to:
.guardkit/autobuild/{task_id}/player_turn_{turn}.json

Follow the report format specified in your agent definition.
"""
```

**SDK Options for Player**:
```python
options = ClaudeCodeOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
    permission_mode="acceptEdits",
    max_turns=self.max_turns_per_agent,
    model=self.player_model,
)
```

**Key Behaviors**:
- Full file system access (Read, Write, Edit)
- Permission mode: `acceptEdits` (autonomous editing)
- Working directory: Isolated worktree
- Fresh context each turn (new SDK session)

### 4.2 Coach Agent Invocation

**Prompt Template**:
```python
def _build_coach_prompt(self, task_id, turn, requirements, player_report):
    return f"""You are the Coach agent. Validate the Player's implementation.

Task ID: {task_id}
Turn: {turn}

Original Requirements:
{requirements}

Player's Report:
{json.dumps(player_report, indent=2)}

Your job:
1. Independently verify the Player's claims
2. Run the tests yourself
3. Check all requirements are met
4. Either APPROVE or provide specific FEEDBACK

Write your decision to:
.guardkit/autobuild/{task_id}/coach_turn_{turn}.json

Follow the decision format specified in your agent definition.
"""
```

**SDK Options for Coach**:
```python
options = ClaudeCodeOptions(
    cwd=str(self.worktree_path),
    allowed_tools=["Read", "Bash", "Grep", "Glob"],  # NO Write/Edit
    permission_mode="default",
    max_turns=self.max_turns_per_agent,
    model=self.coach_model,
)
```

**Key Behaviors**:
- Read-only file system (no Write/Edit)
- Bash access for running tests
- Same worktree as Player (validation)
- Fresh context (no Player context pollution)

### 4.3 Report Validation

**Player Report Required Fields**:
```python
PLAYER_REPORT_SCHEMA = {
    "task_id": str,
    "turn": int,
    "files_modified": list,
    "files_created": list,
    "tests_written": list,
    "tests_run": bool,
    "tests_passed": bool,
    "implementation_notes": str,
    "concerns": list,
    "requirements_addressed": list,
    "requirements_remaining": list,
}
```

**Coach Decision Required Fields**:
```python
COACH_DECISION_SCHEMA = {
    "task_id": str,
    "turn": int,
    "decision": str,  # "approve" or "feedback"
    # Additional fields vary by decision type
}
```

### 4.4 Error Handling Strategy

**Timeout Handling**:
```python
async def _invoke_with_timeout(self, coro, timeout_seconds=300):
    """Wrap SDK invocation with timeout."""
    try:
        return await asyncio.wait_for(coro, timeout=timeout_seconds)
    except asyncio.TimeoutError:
        raise SDKTimeoutError(
            f"Agent invocation exceeded {timeout_seconds}s timeout"
        )
```

**SDK Error Handling**:
```python
try:
    async for message in query(prompt=prompt, options=options):
        # Process message
        yield message
except Exception as e:
    raise AgentInvocationError(
        f"SDK invocation failed: {str(e)}"
    ) from e
```

**Report Missing/Invalid Handling**:
```python
def _load_agent_report(self, task_id, turn, agent_type):
    report_path = self._get_report_path(task_id, turn, agent_type)

    if not report_path.exists():
        raise PlayerReportNotFoundError(
            f"Report not found: {report_path}"
        )

    try:
        with open(report_path) as f:
            report = json.load(f)
    except json.JSONDecodeError as e:
        raise PlayerReportInvalidError(
            f"Invalid JSON in report: {str(e)}"
        ) from e

    # Validate schema
    if agent_type == "player":
        self._validate_player_report(report)
    else:
        self._validate_coach_decision(report)

    return report
```

---

## 5. Testing Strategy

### 5.1 Unit Tests Structure

```python
# tests/unit/test_agent_invoker.py

import pytest
from unittest.mock import AsyncMock, Mock, patch
from pathlib import Path

from guardkit.orchestrator.agent_invoker import (
    AgentInvoker,
    AgentInvocationResult,
)
from guardkit.orchestrator.exceptions import (
    PlayerReportNotFoundError,
    PlayerReportInvalidError,
    CoachDecisionNotFoundError,
    CoachDecisionInvalidError,
    SDKTimeoutError,
)


class TestAgentInvokerInit:
    """Test AgentInvoker initialization."""

    def test_init_with_defaults(self):
        """AgentInvoker initializes with default values."""

    def test_init_with_custom_models(self):
        """AgentInvoker accepts custom models."""


class TestPlayerInvocation:
    """Test Player agent invocation."""

    @pytest.mark.asyncio
    async def test_invoke_player_success(self, mock_sdk):
        """Player invocation succeeds and returns report."""

    @pytest.mark.asyncio
    async def test_invoke_player_with_feedback(self, mock_sdk):
        """Player receives feedback from previous turn."""

    @pytest.mark.asyncio
    async def test_invoke_player_timeout(self, mock_sdk):
        """Player invocation times out after threshold."""

    @pytest.mark.asyncio
    async def test_invoke_player_report_not_found(self, mock_sdk):
        """Raises error if Player doesn't create report."""

    @pytest.mark.asyncio
    async def test_invoke_player_report_invalid_json(self, mock_sdk):
        """Raises error if Player report is malformed JSON."""


class TestCoachInvocation:
    """Test Coach agent invocation."""

    @pytest.mark.asyncio
    async def test_invoke_coach_success(self, mock_sdk):
        """Coach invocation succeeds and returns decision."""

    @pytest.mark.asyncio
    async def test_invoke_coach_approval(self, mock_sdk):
        """Coach approves implementation."""

    @pytest.mark.asyncio
    async def test_invoke_coach_feedback(self, mock_sdk):
        """Coach provides feedback."""

    @pytest.mark.asyncio
    async def test_invoke_coach_decision_not_found(self, mock_sdk):
        """Raises error if Coach doesn't create decision."""


class TestPromptBuilding:
    """Test prompt construction."""

    def test_build_player_prompt_first_turn(self):
        """Player prompt for turn 1 has no feedback section."""

    def test_build_player_prompt_with_feedback(self):
        """Player prompt includes feedback from previous turn."""

    def test_build_coach_prompt(self):
        """Coach prompt includes requirements and Player report."""


class TestReportValidation:
    """Test report validation."""

    def test_validate_player_report_valid(self):
        """Valid Player report passes validation."""

    def test_validate_player_report_missing_field(self):
        """Raises error if required field missing."""

    def test_validate_coach_decision_approve(self):
        """Valid Coach approval passes validation."""

    def test_validate_coach_decision_feedback(self):
        """Valid Coach feedback passes validation."""


class TestSDKIntegration:
    """Test SDK integration patterns."""

    @pytest.mark.asyncio
    async def test_sdk_options_for_player(self, mock_sdk):
        """Player gets correct SDK options (Read/Write/Edit)."""

    @pytest.mark.asyncio
    async def test_sdk_options_for_coach(self, mock_sdk):
        """Coach gets correct SDK options (Read-only)."""

    @pytest.mark.asyncio
    async def test_fresh_context_per_turn(self, mock_sdk):
        """Each invocation creates new SDK session."""
```

### 5.2 Test Fixtures

```python
@pytest.fixture
def worktree_path(tmp_path):
    """Create temporary worktree directory."""
    return tmp_path / "worktree"

@pytest.fixture
def agent_invoker(worktree_path):
    """Create AgentInvoker instance."""
    return AgentInvoker(
        worktree_path=worktree_path,
        max_turns_per_agent=30,
    )

@pytest.fixture
def mock_sdk():
    """Mock Claude Agents SDK."""
    with patch("guardkit.orchestrator.agent_invoker.query") as mock:
        # Configure mock to yield sample messages
        yield mock

@pytest.fixture
def sample_player_report():
    """Sample Player report JSON."""
    return {
        "task_id": "TASK-001",
        "turn": 1,
        "files_modified": ["src/auth.py"],
        "files_created": ["tests/test_auth.py"],
        "tests_written": ["tests/test_auth.py"],
        "tests_run": True,
        "tests_passed": True,
        "test_output_summary": "5 passed in 0.23s",
        "implementation_notes": "Implemented OAuth2 flow",
        "concerns": [],
        "requirements_addressed": ["OAuth2 authentication"],
        "requirements_remaining": [],
    }

@pytest.fixture
def sample_coach_approval():
    """Sample Coach approval decision."""
    return {
        "task_id": "TASK-001",
        "turn": 1,
        "decision": "approve",
        "validation_results": {
            "requirements_met": ["All acceptance criteria verified"],
            "tests_run": True,
            "tests_passed": True,
            "test_command": "pytest tests/ -v",
            "test_output_summary": "12 passed in 1.45s",
            "code_quality": "Good",
            "edge_cases_covered": ["Token refresh", "Auth failure"],
        },
        "rationale": "Implementation complete",
    }
```

### 5.3 Mocking Strategy

**Mock SDK Invocation**:
```python
@pytest.fixture
def mock_sdk_success():
    """Mock successful SDK invocation."""
    async def mock_query(*args, **kwargs):
        # Simulate SDK messages
        yield {"type": "progress", "message": "Starting..."}
        yield {"type": "progress", "message": "Writing files..."}
        yield {"type": "complete", "success": True}

    with patch("guardkit.orchestrator.agent_invoker.query", side_effect=mock_query):
        yield
```

**Mock Report Files**:
```python
@pytest.fixture
def mock_player_report_file(tmp_path, sample_player_report):
    """Create mock Player report file."""
    report_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-001"
    report_dir.mkdir(parents=True)
    report_path = report_dir / "player_turn_1.json"
    report_path.write_text(json.dumps(sample_player_report))
    return report_path
```

---

## 6. Quality Gates

### 6.1 Test Coverage Requirements

- **Line coverage**: ≥80%
- **Branch coverage**: ≥75%
- **Critical paths**: 100% (SDK invocation, report validation, error handling)

### 6.2 Code Quality Checks

- All public methods have docstrings
- Type hints on all function signatures
- No hardcoded values (use constants/config)
- Error messages are actionable
- No nested try/except blocks (>2 levels)

### 6.3 Integration Verification

- Mock SDK behaves like real SDK (async generator pattern)
- Report validation matches Player/Coach agent formats
- Error handling covers SDK exceptions
- Timeout handling tested

---

## 7. Files to Create/Modify

### 7.1 New Files

```
guardkit/orchestrator/
├── __init__.py                  # Package initialization
├── agent_invoker.py             # AgentInvoker class (PRIMARY)
└── exceptions.py                # Custom exceptions

tests/unit/
└── test_agent_invoker.py        # Unit tests (PRIMARY)

.guardkit/autobuild/
└── .gitkeep                     # Ensure directory exists
```

### 7.2 Files to Modify

None in this task (Wave 1 isolation).

---

## 8. Estimated Lines of Code

### 8.1 Implementation

```
guardkit/orchestrator/agent_invoker.py:   ~250 LOC
  - AgentInvoker class:                   ~180 LOC
  - Helper functions:                      ~50 LOC
  - Constants/schemas:                     ~20 LOC

guardkit/orchestrator/exceptions.py:       ~30 LOC
  - 6 custom exceptions:                   ~30 LOC

guardkit/orchestrator/__init__.py:         ~10 LOC
  - Package exports:                       ~10 LOC

Total Implementation:                     ~290 LOC
```

### 8.2 Tests

```
tests/unit/test_agent_invoker.py:        ~400 LOC
  - Test classes (5):                    ~300 LOC
  - Fixtures (8):                        ~100 LOC

Total Tests:                             ~400 LOC
```

### 8.3 Total Effort

```
Implementation:    290 LOC × 2 min/LOC = ~580 minutes (9.7 hours)
Tests:             400 LOC × 1.5 min/LOC = ~600 minutes (10 hours)
Debugging:         20% buffer = ~3.5 hours

Adjusted Total (with parallelism, familiarity):  4-5 hours
```

**Note**: Estimate assumes familiarity with async/await patterns and SDK documentation available. First-time SDK integration may take longer.

---

## 9. Risks and Mitigations

### 9.1 Risk: SDK API Changes

**Likelihood**: Medium
**Impact**: High (breaks invocation)
**Mitigation**: Pin SDK version (`claude-code-sdk = "~=0.1.0"`) in Wave 1. Create adapter layer if needed.

### 9.2 Risk: Async/Await Complexity

**Likelihood**: Low
**Impact**: Medium (harder to debug)
**Mitigation**: Comprehensive async unit tests. Use `pytest-asyncio` for async test support.

### 9.3 Risk: Report Validation Too Strict

**Likelihood**: Medium
**Impact**: Low (agents blocked unnecessarily)
**Mitigation**: Validate only required fields. Log warnings for optional fields. Iterate based on real agent behavior.

### 9.4 Risk: Timeout Thresholds Too Low

**Likelihood**: Medium
**Impact**: Medium (premature failures)
**Mitigation**: Make timeout configurable. Start with generous defaults (5 minutes/agent). Tune based on metrics.

---

## 10. Integration Points

### 10.1 Dependencies (Wave 1)

None. This task is independent and can run in parallel with other Wave 1 tasks.

### 10.2 Dependents (Wave 2)

- **TASK-AB-9869** (AutoBuildOrchestrator): Will import and use `AgentInvoker`
- Expected interface:
  ```python
  from guardkit.orchestrator.agent_invoker import AgentInvoker

  invoker = AgentInvoker(worktree_path=worktree_path)
  result = await invoker.invoke_player(task_id, turn, requirements, feedback)
  ```

---

## 11. Success Criteria

### 11.1 Functional

- [ ] `AgentInvoker` can invoke Player agent via SDK
- [ ] `AgentInvoker` can invoke Coach agent via SDK
- [ ] Player gets Read/Write/Edit/Bash permissions
- [ ] Coach gets Read/Bash permissions only
- [ ] Reports are validated and parsed correctly
- [ ] Fresh context per invocation (no context pollution)

### 11.2 Quality

- [ ] ≥80% line coverage
- [ ] ≥75% branch coverage
- [ ] All tests passing
- [ ] No linting errors
- [ ] Type hints on all public methods
- [ ] Comprehensive error handling

### 11.3 Documentation

- [ ] All public methods have docstrings
- [ ] Exceptions documented with examples
- [ ] README.md updated (if applicable)
- [ ] Implementation plan reviewed

---

## 12. Next Steps After Implementation

1. **Code Review**: Self-review against plan
2. **Test Execution**: Run pytest with coverage
3. **Quality Gates**: Verify ≥80% coverage
4. **Documentation**: Update any missing docstrings
5. **Commit**: Prepare for Wave 1 merge
6. **Handoff**: Ready for Wave 2 integration (TASK-AB-9869)

---

## 13. Open Questions

1. **SDK Import Path**: Verify exact import path for `claude_code_sdk.query` (may differ from feature spec pseudocode)
2. **SDK Message Format**: Confirm SDK message structure for progress tracking
3. **SDK Error Types**: Document SDK-specific exceptions for error handling
4. **Report Path Convention**: Confirm `.guardkit/autobuild/{task_id}/` is correct location

**Resolution Strategy**: Review Claude Agents SDK documentation during implementation. Create adapter layer if API differs significantly from spec.

---

**Plan Created**: 2025-12-23
**Plan Version**: 1.0
**Estimated Completion**: 4-5 hours
**Confidence**: High (well-defined requirements, clear interfaces)
