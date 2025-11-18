# TASK-INTEGRATE-AGENT-BRIDGE: Integrate Orchestrator with Existing Agent Bridge

**Task ID**: TASK-AGENT-BRIDGE-COMPLETE
**Title**: Integrate Orchestrator with Existing AgentBridgeInvoker and StateManager
**Status**: BACKLOG
**Priority**: HIGH
**Complexity**: 4/10 (Medium-Low)
**Estimated Hours**: 2-3
**Phase**: 2 of 8 (Template-Create Redesign)

---

## Problem Statement

### Current Issue

The orchestrator doesn't properly integrate with existing `AgentBridgeInvoker` and `StateManager`:

```
Agent invocation failed: Agent invocation not yet implemented.
Using fallback heuristics.
```

### Root Cause

The `ArchitecturalReviewerInvoker` in `agent_invoker.py` raises an exception when no bridge invoker is provided, and the orchestrator isn't wired to use the existing infrastructure.

### IMPORTANT: Existing Infrastructure

The following infrastructure **already exists and works** - DO NOT RECREATE:

| Component | Location | LOC |
|-----------|----------|-----|
| `AgentBridgeInvoker` | `installer/global/lib/agent_bridge/invoker.py` | 266 |
| `StateManager` | `installer/global/lib/agent_bridge/state_manager.py` | 162 |
| `TemplateCreateState` | `state_manager.py` (lines 15-37) | 22 |
| `AgentRequest/Response` | `invoker.py` (lines 33-83) | 50 |

---

## Solution Design

### Approach

Wire the orchestrator to use existing infrastructure:
1. Add `CheckpointRequested` exception to existing `invoker.py`
2. Update orchestrator to import and use `AgentBridgeInvoker`
3. Update orchestrator to import and use `StateManager`
4. Create mock invoker for testing (only genuinely new file)

### Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `installer/global/lib/agent_bridge/invoker.py` | MODIFY | Add CheckpointRequested exception |
| `installer/global/lib/codebase_analyzer/agent_invoker.py` | MODIFY | Use existing bridge invoker |
| `installer/global/commands/lib/template_create_orchestrator.py` | MODIFY | Wire to existing infrastructure |

### Files to Create

| File | Action | Description |
|------|--------|-------------|
| `installer/global/lib/agent_bridge/mock_invoker.py` | CREATE | Mock invoker for testing |
| `tests/unit/agent_bridge/test_integration.py` | CREATE | Integration tests |

### Files NOT Being Created (Already Exist)

- ~~`checkpoint_manager.py`~~ - Use existing `StateManager`
- ~~`response_parser.py`~~ - Use existing `invoker.load_response()`
- ~~`TemplateCreateState`~~ - Already exists in `state_manager.py`

---

## Implementation Details

### 1. Add CheckpointRequested Exception to Existing invoker.py

```python
# ADD to installer/global/lib/agent_bridge/invoker.py (after line 265)

class CheckpointRequested(Exception):
    """
    Raised when orchestrator should exit for external agent invocation.

    The orchestrator catches this exception and exits with code 42.
    """

    def __init__(
        self,
        agent_name: str,
        phase: int,
        phase_name: str
    ):
        self.agent_name = agent_name
        self.phase = phase
        self.phase_name = phase_name
        super().__init__(
            f"Checkpoint requested for {agent_name} at phase {phase} ({phase_name})"
        )
```

### 2. Update __init__.py Exports

```python
# UPDATE installer/global/lib/agent_bridge/__init__.py

from .invoker import (
    AgentBridgeInvoker,
    AgentRequest,
    AgentResponse,
    AgentInvocationError,
    CheckpointRequested  # Add this export
)
from .state_manager import StateManager, TemplateCreateState
```

### 3. Update ArchitecturalReviewerInvoker to Use Existing Infrastructure

```python
# MODIFY installer/global/lib/codebase_analyzer/agent_invoker.py

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from installer.global.lib.agent_bridge.invoker import (
    AgentBridgeInvoker,
    CheckpointRequested
)
from installer.global.lib.agent_bridge.state_manager import StateManager


class ArchitecturalReviewerInvoker:
    """Invokes architectural-reviewer agent for codebase analysis."""

    def __init__(
        self,
        bridge_invoker: Optional[AgentBridgeInvoker] = None,
        state_manager: Optional[StateManager] = None
    ):
        """
        Initialize with existing infrastructure.

        Args:
            bridge_invoker: Existing AgentBridgeInvoker instance
            state_manager: Existing StateManager instance
        """
        self.bridge_invoker = bridge_invoker
        self.state_manager = state_manager or StateManager()
        self.logger = logging.getLogger(__name__)

    def invoke_for_analysis(
        self,
        samples: List[Dict[str, Any]],
        context: Dict[str, Any],
        phase: int = 1
    ) -> Dict[str, Any]:
        """
        Invoke architectural-reviewer for codebase analysis.

        Uses existing AgentBridgeInvoker if available, otherwise
        raises CheckpointRequested for external invocation.

        Args:
            samples: File samples to analyze
            context: Additional context (project_path, etc.)
            phase: Current phase number

        Returns:
            Analysis result dict

        Raises:
            CheckpointRequested: If agent invocation needs checkpoint
        """
        # Check if we're resuming with a response
        if self.bridge_invoker and self.bridge_invoker.has_response():
            response = self.bridge_invoker.load_response()
            self.logger.info("Loaded agent response from checkpoint")
            return json.loads(response)

        # If we have a bridge invoker, use it directly
        if self.bridge_invoker:
            prompt = self._build_analysis_prompt(samples)
            response = self.bridge_invoker.invoke(
                agent_name="architectural-reviewer",
                prompt=prompt,
                timeout_seconds=120,
                context=context
            )
            return json.loads(response)

        # No bridge invoker - request checkpoint for external invocation
        raise CheckpointRequested(
            agent_name="architectural-reviewer",
            phase=phase,
            phase_name="codebase_analysis" if phase == 1 else "agent_creation"
        )

    def _build_analysis_prompt(self, samples: List[Dict[str, Any]]) -> str:
        """Build analysis prompt from samples."""
        # Import prompt template (created separately)
        from installer.global.lib.template_creation.prompts import PHASE_1_ANALYSIS_PROMPT
        return PHASE_1_ANALYSIS_PROMPT.format(
            file_samples=json.dumps(samples, indent=2)
        )
```

### 4. Create Mock Invoker for Testing

```python
# CREATE installer/global/lib/agent_bridge/mock_invoker.py

"""
Mock Agent Invoker for Testing

Provides canned responses for testing without real AI calls.
"""

import json
from typing import Any, Dict, List, Optional

from .invoker import AgentInvocationError


class MockAgentInvoker:
    """Mock agent invoker for testing without real AI calls."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """
        Initialize with canned responses.

        Args:
            responses: Map of agent_name -> response content (JSON string)
        """
        self.responses = responses or {}
        self.invocations: List[Dict[str, Any]] = []

    def add_response(self, agent_name: str, response: str) -> None:
        """Add a canned response for an agent."""
        self.responses[agent_name] = response

    def add_response_from_dict(self, agent_name: str, response_dict: Dict) -> None:
        """Add a canned response from a dictionary."""
        self.responses[agent_name] = json.dumps(response_dict)

    def invoke(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 120,
        context: Optional[Dict] = None
    ) -> str:
        """
        Mock invoke an agent.

        Returns:
            Canned response for the agent

        Raises:
            AgentInvocationError: If no response configured
        """
        self.invocations.append({
            "agent_name": agent_name,
            "prompt": prompt,
            "timeout_seconds": timeout_seconds,
            "context": context or {}
        })

        if agent_name in self.responses:
            return self.responses[agent_name]

        raise AgentInvocationError(
            f"No mock response configured for agent: {agent_name}"
        )

    def get_invocations(self, agent_name: Optional[str] = None) -> List[Dict]:
        """Get recorded invocations, optionally filtered by agent."""
        if agent_name:
            return [i for i in self.invocations if i["agent_name"] == agent_name]
        return self.invocations

    def reset(self) -> None:
        """Reset invocation history."""
        self.invocations = []

    def has_response(self) -> bool:
        """Check if response file exists (always False for mock)."""
        return False

    def load_response(self) -> str:
        """Load response (not applicable for mock)."""
        raise AgentInvocationError("Mock invoker has no stored response")
```

---

## Acceptance Criteria

### Functional

- [ ] `CheckpointRequested` exception added to existing `invoker.py`
- [ ] `ArchitecturalReviewerInvoker` uses existing `AgentBridgeInvoker`
- [ ] `MockAgentInvoker` works for testing
- [ ] Existing tests still pass

### Quality

- [ ] Test coverage >= 90%
- [ ] No circular imports
- [ ] Uses existing StateManager API correctly

### Integration

- [ ] Works with existing orchestrator
- [ ] Existing checkpoint files compatible
- [ ] No duplicate infrastructure created

---

## Test Specifications

### Unit Tests

```python
# tests/unit/agent_bridge/test_integration.py

import pytest
import json
from pathlib import Path

from installer.global.lib.agent_bridge.invoker import (
    AgentBridgeInvoker,
    CheckpointRequested
)
from installer.global.lib.agent_bridge.state_manager import (
    StateManager,
    TemplateCreateState
)
from installer.global.lib.agent_bridge.mock_invoker import MockAgentInvoker


class TestCheckpointRequested:
    """Tests for CheckpointRequested exception."""

    def test_exception_attributes(self):
        """Test exception stores correct attributes."""
        exc = CheckpointRequested(
            agent_name="architectural-reviewer",
            phase=1,
            phase_name="codebase_analysis"
        )

        assert exc.agent_name == "architectural-reviewer"
        assert exc.phase == 1
        assert exc.phase_name == "codebase_analysis"

    def test_exception_message(self):
        """Test exception has descriptive message."""
        exc = CheckpointRequested(
            agent_name="architectural-reviewer",
            phase=5,
            phase_name="agent_creation"
        )

        assert "architectural-reviewer" in str(exc)
        assert "5" in str(exc)


class TestMockInvoker:
    """Tests for MockAgentInvoker."""

    def test_add_and_invoke_response(self):
        """Test adding and invoking canned response."""
        mock = MockAgentInvoker()
        mock.add_response_from_dict("architectural-reviewer", {
            "technology_stack": {"primary_language": "Python"},
            "overall_confidence": 0.92
        })

        response = mock.invoke(
            agent_name="architectural-reviewer",
            prompt="Analyze this..."
        )

        result = json.loads(response)
        assert result["overall_confidence"] == 0.92

    def test_records_invocations(self):
        """Test that invocations are recorded."""
        mock = MockAgentInvoker()
        mock.add_response("test-agent", '{"result": "ok"}')

        mock.invoke("test-agent", "test prompt", timeout_seconds=60)

        invocations = mock.get_invocations("test-agent")
        assert len(invocations) == 1
        assert invocations[0]["prompt"] == "test prompt"
        assert invocations[0]["timeout_seconds"] == 60

    def test_raises_for_unknown_agent(self):
        """Test raises error for unconfigured agent."""
        mock = MockAgentInvoker()

        with pytest.raises(Exception) as exc:
            mock.invoke("unknown-agent", "prompt")

        assert "No mock response" in str(exc.value)


class TestExistingInfrastructure:
    """Tests verifying existing infrastructure still works."""

    def test_state_manager_save_load(self, tmp_path):
        """Test StateManager save/load cycle."""
        manager = StateManager(state_file=tmp_path / "state.json")

        manager.save_state(
            checkpoint="test_checkpoint",
            phase=1,
            config={"codebase_path": "/test"},
            phase_data={"samples": []}
        )

        state = manager.load_state()

        assert state.checkpoint == "test_checkpoint"
        assert state.phase == 1
        assert state.config["codebase_path"] == "/test"

    def test_bridge_invoker_exits_with_42(self, tmp_path):
        """Test AgentBridgeInvoker exits with code 42."""
        invoker = AgentBridgeInvoker(
            request_file=tmp_path / "request.json",
            response_file=tmp_path / "response.json",
            phase=1,
            phase_name="test"
        )

        # invoke() will call sys.exit(42), so we can't test directly
        # Instead verify the request file would be written
        assert not invoker.has_response()
        assert not invoker.has_pending_request()
```

### Integration Tests

```python
# tests/integration/test_agent_workflow.py

import pytest
import json
from pathlib import Path

from installer.global.lib.agent_bridge.state_manager import StateManager
from installer.global.lib.agent_bridge.invoker import AgentBridgeInvoker
from installer.global.lib.agent_bridge.mock_invoker import MockAgentInvoker


class TestCheckpointResumeCycle:
    """Integration tests for checkpoint-resume workflow."""

    def test_complete_checkpoint_resume_cycle(self, tmp_path):
        """Test full checkpoint-resume cycle with existing infrastructure."""
        state_manager = StateManager(state_file=tmp_path / "state.json")

        # Phase 1: Save state before agent invocation
        state_manager.save_state(
            checkpoint="before_ai_analysis",
            phase=1,
            config={
                "codebase_path": "/test/project",
                "output_location": "personal"
            },
            phase_data={
                "samples": ["file1.py", "file2.py"]
            }
        )

        # Simulate external agent writing response
        response_file = tmp_path / "response.json"
        response_file.write_text(json.dumps({
            "request_id": "test-123",
            "version": "1.0",
            "status": "success",
            "response": json.dumps({
                "technology_stack": {"primary_language": "Python"},
                "overall_confidence": 0.92
            }),
            "error_message": None,
            "error_type": None,
            "created_at": "2025-11-18T12:00:00Z",
            "duration_seconds": 5.2,
            "metadata": {}
        }))

        # Phase 2: Resume from checkpoint
        invoker = AgentBridgeInvoker(
            request_file=tmp_path / "request.json",
            response_file=response_file,
            phase=1,
            phase_name="codebase_analysis"
        )

        assert state_manager.has_state()
        assert invoker.has_response()

        # Load state and response
        state = state_manager.load_state()
        response = invoker.load_response()
        result = json.loads(response)

        assert state.phase == 1
        assert result["overall_confidence"] == 0.92

        # Cleanup
        state_manager.cleanup()
        assert not state_manager.has_state()

    def test_mock_invoker_for_testing(self):
        """Test using mock invoker for direct testing."""
        mock = MockAgentInvoker()
        mock.add_response_from_dict("architectural-reviewer", {
            "technology_stack": {
                "primary_language": "C#",
                "frameworks": [
                    {"name": ".NET MAUI", "version": "8.0", "confidence": 0.95}
                ]
            },
            "overall_confidence": 0.95
        })

        # Use mock in place of real invoker
        response = mock.invoke(
            agent_name="architectural-reviewer",
            prompt="Analyze codebase...",
            timeout_seconds=120
        )

        result = json.loads(response)
        assert result["technology_stack"]["primary_language"] == "C#"
        assert result["overall_confidence"] == 0.95

        # Verify invocation was recorded
        invocations = mock.get_invocations()
        assert len(invocations) == 1
        assert "Analyze codebase" in invocations[0]["prompt"]
```

---

## Dependencies

### Depends On
- None (can proceed in parallel with Phase 1)

### Blocks
- TASK-PHASE-1-CHECKPOINT (Phase 3)
- TASK-PHASE-5-CHECKPOINT (Phase 4)
- TASK-PHASE-7-5-CHECKPOINT (Phase 5)

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Test coverage | >= 90% | pytest --cov |
| Existing tests pass | 100% | pytest |
| New code added | < 150 LOC | Line count (mock_invoker.py + exception) |
| Duplicate code | 0 LOC | Code review |

---

## Notes

### What This Task Does
- Adds `CheckpointRequested` exception (20 LOC)
- Creates `MockAgentInvoker` for testing (100 LOC)
- Wires existing infrastructure together

### What This Task Does NOT Do
- ~~Create CheckpointManager~~ - Use existing `StateManager`
- ~~Create TemplateCreateState~~ - Already exists
- ~~Create response_parser~~ - Use existing `invoker.load_response()`
- ~~Duplicate any existing infrastructure~~

### Key Principle
**REUSE existing infrastructure** that already works:
- `AgentBridgeInvoker` (266 LOC) - Complete exit code 42 protocol
- `StateManager` (162 LOC) - Complete state persistence
- `TemplateCreateState` - Complete dataclass

---

**Created**: 2025-11-18
**Updated**: 2025-11-18 (Rewritten to use existing infrastructure)
**Phase**: 2 of 8 (Template-Create Redesign)
**Related**: Uses existing installer/global/lib/agent_bridge/
