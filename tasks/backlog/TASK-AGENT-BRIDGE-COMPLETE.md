# TASK-AGENT-BRIDGE-COMPLETE: Complete Agent Bridge Implementation

**Task ID**: TASK-AGENT-BRIDGE-COMPLETE
**Title**: Complete Agent Bridge Checkpoint-Resume Implementation
**Status**: BACKLOG
**Priority**: HIGH
**Complexity**: 6/10 (Medium)
**Estimated Hours**: 4-6
**Phase**: 2 of 8 (Template-Create Redesign)

---

## Problem Statement

### Current Issue

The agent bridge infrastructure exists but agent invocation throws "not yet implemented":

```
Agent invocation failed: Agent invocation not yet implemented.
Using fallback heuristics.
```

This prevents AI-powered analysis in Phases 1, 4, and 7.5, reducing confidence from 90%+ to 68%.

### Root Cause

The `ArchitecturalReviewerInvoker` in `agent_invoker.py` raises an exception when no bridge invoker is provided, and the orchestrator doesn't properly integrate with the `AgentBridgeInvoker` that exists.

---

## Solution Design

### Approach

Complete the agent bridge pattern with:
1. CheckpointManager for state persistence
2. Request/response file handling
3. Proper integration with orchestrator
4. Mock invoker for testing

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `installer/global/lib/agent_bridge/checkpoint_manager.py` | CREATE | State persistence |
| `installer/global/lib/agent_bridge/invoker.py` | MODIFY | Complete integration |
| `installer/global/lib/codebase_analyzer/agent_invoker.py` | MODIFY | Use bridge invoker |
| `tests/unit/agent_bridge/test_checkpoint_manager.py` | CREATE | Unit tests |
| `tests/integration/test_agent_workflow.py` | CREATE | Integration tests |

---

## Implementation Details

### 1. CheckpointManager

```python
# installer/global/lib/agent_bridge/checkpoint_manager.py

from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import logging

logger = logging.getLogger(__name__)

# Exit code for checkpoint
CHECKPOINT_EXIT_CODE = 42


@dataclass
class CompletedPhase:
    """Record of a completed phase."""
    phase: int
    phase_name: str
    completed_at: str
    result_summary: str


@dataclass
class TemplateCreateState:
    """Checkpoint state for template creation."""
    phase: int
    phase_name: str
    checkpoint_name: str
    output_path: str
    version: str = "1.0"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    project_path: Optional[str] = None
    template_name: Optional[str] = None
    phase_data: Dict[str, Any] = field(default_factory=dict)
    completed_phases: List[CompletedPhase] = field(default_factory=list)
    agent_requests: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "phase": self.phase,
            "phase_name": self.phase_name,
            "checkpoint_name": self.checkpoint_name,
            "created_at": self.created_at,
            "output_path": self.output_path,
            "project_path": self.project_path,
            "template_name": self.template_name,
            "phase_data": self.phase_data,
            "completed_phases": [
                {
                    "phase": p.phase,
                    "phase_name": p.phase_name,
                    "completed_at": p.completed_at,
                    "result_summary": p.result_summary
                }
                for p in self.completed_phases
            ],
            "agent_requests": self.agent_requests
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TemplateCreateState":
        completed = [
            CompletedPhase(
                phase=p["phase"],
                phase_name=p["phase_name"],
                completed_at=p["completed_at"],
                result_summary=p["result_summary"]
            )
            for p in data.get("completed_phases", [])
        ]
        return cls(
            version=data.get("version", "1.0"),
            phase=data["phase"],
            phase_name=data["phase_name"],
            checkpoint_name=data["checkpoint_name"],
            created_at=data["created_at"],
            output_path=data["output_path"],
            project_path=data.get("project_path"),
            template_name=data.get("template_name"),
            phase_data=data.get("phase_data", {}),
            completed_phases=completed,
            agent_requests=data.get("agent_requests", [])
        )


class CheckpointManager:
    """Manage checkpoint save/restore for template creation."""

    def __init__(
        self,
        state_file: Path = Path(".template-create-state.json"),
        request_file: Path = Path(".agent-request.json"),
        response_file: Path = Path(".agent-response.json")
    ):
        self.state_file = state_file
        self.request_file = request_file
        self.response_file = response_file

    def save_checkpoint(
        self,
        state: TemplateCreateState,
        request: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save checkpoint state and optional agent request.

        Args:
            state: Current checkpoint state
            request: Optional agent request to write
        """
        # Save state
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state.to_dict(), f, indent=2)
        logger.info(f"Saved checkpoint: phase={state.phase}, checkpoint={state.checkpoint_name}")

        # Save request if provided
        if request:
            with open(self.request_file, 'w', encoding='utf-8') as f:
                json.dump(request, f, indent=2)
            logger.info(f"Saved agent request for: {request.get('agent_name')}")

    def load_checkpoint(self) -> Optional[TemplateCreateState]:
        """
        Load checkpoint state from disk.

        Returns:
            TemplateCreateState if exists, None otherwise
        """
        if not self.state_file.exists():
            return None

        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            state = TemplateCreateState.from_dict(data)
            logger.info(f"Loaded checkpoint: phase={state.phase}")
            return state
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}")
            return None

    def has_agent_response(self) -> bool:
        """Check if agent response file exists."""
        return self.response_file.exists()

    def load_agent_response(self) -> Optional[Dict[str, Any]]:
        """
        Load agent response from disk.

        Returns:
            Response dict if exists, None otherwise
        """
        if not self.response_file.exists():
            return None

        try:
            with open(self.response_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load agent response: {e}")
            return None

    def clear_checkpoint(self) -> None:
        """Remove all checkpoint files."""
        for filepath in [self.state_file, self.request_file, self.response_file]:
            if filepath.exists():
                filepath.unlink()
                logger.debug(f"Removed: {filepath}")

    def is_resuming(self) -> bool:
        """Check if we're resuming from a checkpoint."""
        return self.state_file.exists()


class CheckpointRequested(Exception):
    """
    Raised when orchestrator should exit for external agent invocation.

    The orchestrator catches this exception and exits with code 42.
    """

    def __init__(
        self,
        agent_name: str,
        phase: int,
        phase_name: str,
        checkpoint_name: str = "before_agent_invocation"
    ):
        self.agent_name = agent_name
        self.phase = phase
        self.phase_name = phase_name
        self.checkpoint_name = checkpoint_name
        super().__init__(
            f"Checkpoint requested for {agent_name} at phase {phase} ({phase_name})"
        )
```

### 2. Update Agent Invoker Integration

```python
# In installer/global/lib/codebase_analyzer/agent_invoker.py

from installer.global.lib.agent_bridge.invoker import AgentBridgeInvoker
from installer.global.lib.agent_bridge.checkpoint_manager import (
    CheckpointManager,
    CheckpointRequested,
    TemplateCreateState
)


class ArchitecturalReviewerInvoker:
    """Invokes architectural-reviewer agent for codebase analysis."""

    def __init__(
        self,
        bridge_invoker: Optional[AgentBridgeInvoker] = None,
        checkpoint_manager: Optional[CheckpointManager] = None
    ):
        self.bridge_invoker = bridge_invoker
        self.checkpoint_manager = checkpoint_manager or CheckpointManager()
        self.logger = logging.getLogger(__name__)

    def invoke_for_analysis(
        self,
        samples: List[Dict[str, Any]],
        context: Dict[str, Any],
        phase: int = 1
    ) -> Dict[str, Any]:
        """
        Invoke architectural-reviewer for codebase analysis.

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
        if self.checkpoint_manager.has_agent_response():
            response = self.checkpoint_manager.load_agent_response()
            if response and response.get("status") == "success":
                self.logger.info("Loaded agent response from checkpoint")
                return json.loads(response.get("response", "{}"))

        # If we have a bridge invoker, use it directly
        if self.bridge_invoker:
            from docs.proposals.template_create.AI_PROMPTS_SPECIFICATION import (
                PHASE_1_ANALYSIS_PROMPT
            )
            prompt = PHASE_1_ANALYSIS_PROMPT.format(
                file_samples=json.dumps(samples, indent=2)
            )
            response = self.bridge_invoker.invoke(
                agent_name="architectural-reviewer",
                prompt=prompt,
                timeout_seconds=120
            )
            return json.loads(response)

        # No bridge invoker - request checkpoint for external invocation
        raise CheckpointRequested(
            agent_name="architectural-reviewer",
            phase=phase,
            phase_name="codebase_analysis" if phase == 1 else "agent_creation",
            checkpoint_name="before_agent_invocation"
        )
```

### 3. Mock Invoker for Testing

```python
# installer/global/lib/agent_bridge/mock_invoker.py

from typing import Dict, List, Any, Callable
import json


class AgentInvocationError(Exception):
    """Raised when agent invocation fails."""
    pass


class MockAgentInvoker:
    """Mock agent invoker for testing without real AI calls."""

    def __init__(self, responses: Dict[str, str] = None):
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
        **kwargs
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
            "kwargs": kwargs
        })

        if agent_name in self.responses:
            return self.responses[agent_name]

        raise AgentInvocationError(
            f"No mock response configured for agent: {agent_name}"
        )

    def get_invocations(self, agent_name: str = None) -> List[Dict]:
        """Get recorded invocations, optionally filtered by agent."""
        if agent_name:
            return [i for i in self.invocations if i["agent_name"] == agent_name]
        return self.invocations

    def reset(self) -> None:
        """Reset invocation history."""
        self.invocations = []
```

---

## Acceptance Criteria

### Functional

- [ ] CheckpointManager saves/loads state correctly
- [ ] Agent request file written before exit code 42
- [ ] Agent response file parsed on resume
- [ ] MockAgentInvoker works for testing
- [ ] ArchitecturalReviewerInvoker integrates with bridge

### Quality

- [ ] Test coverage >= 90%
- [ ] All tests passing
- [ ] No circular imports

### Integration

- [ ] Works with existing orchestrator
- [ ] Checkpoint files cleaned up after success

---

## Test Specifications

### Unit Tests

```python
# tests/unit/agent_bridge/test_checkpoint_manager.py

import pytest
from pathlib import Path
from installer.global.lib.agent_bridge.checkpoint_manager import (
    CheckpointManager,
    TemplateCreateState,
    CompletedPhase
)


class TestCheckpointManager:
    """Tests for CheckpointManager."""

    def test_save_and_load_state(self, tmp_path):
        """Test saving and loading checkpoint state."""
        manager = CheckpointManager(
            state_file=tmp_path / ".template-create-state.json"
        )

        state = TemplateCreateState(
            phase=5,
            phase_name="agent_creation",
            checkpoint_name="before_agent_invocation",
            output_path="/tmp/output"
        )

        manager.save_checkpoint(state)
        loaded = manager.load_checkpoint()

        assert loaded is not None
        assert loaded.phase == 5
        assert loaded.phase_name == "agent_creation"

    def test_save_with_request(self, tmp_path):
        """Test saving checkpoint with agent request."""
        manager = CheckpointManager(
            state_file=tmp_path / ".template-create-state.json",
            request_file=tmp_path / ".agent-request.json"
        )

        state = TemplateCreateState(
            phase=1,
            phase_name="codebase_analysis",
            checkpoint_name="before_agent_invocation",
            output_path="/tmp/output"
        )

        request = {
            "request_id": "test-123",
            "agent_name": "architectural-reviewer",
            "prompt": "Analyze this..."
        }

        manager.save_checkpoint(state, request)

        assert manager.request_file.exists()

    def test_load_agent_response(self, tmp_path):
        """Test loading agent response."""
        manager = CheckpointManager(
            response_file=tmp_path / ".agent-response.json"
        )

        response = {
            "request_id": "test-123",
            "status": "success",
            "response": '{"overall_confidence": 0.92}'
        }

        manager.response_file.write_text(json.dumps(response))

        loaded = manager.load_agent_response()

        assert loaded is not None
        assert loaded["status"] == "success"

    def test_clear_checkpoint(self, tmp_path):
        """Test clearing checkpoint files."""
        manager = CheckpointManager(
            state_file=tmp_path / "state.json",
            request_file=tmp_path / "request.json",
            response_file=tmp_path / "response.json"
        )

        # Create files
        for f in [manager.state_file, manager.request_file, manager.response_file]:
            f.write_text("{}")

        manager.clear_checkpoint()

        assert not manager.state_file.exists()
        assert not manager.request_file.exists()
        assert not manager.response_file.exists()
```

### Integration Tests

```python
# tests/integration/test_agent_workflow.py

import pytest
from installer.global.lib.agent_bridge.checkpoint_manager import (
    CheckpointManager,
    CheckpointRequested,
    TemplateCreateState
)
from installer.global.lib.agent_bridge.mock_invoker import MockAgentInvoker


class TestAgentWorkflow:
    """Integration tests for agent invocation workflow."""

    def test_checkpoint_resume_cycle(self, tmp_path):
        """Test complete checkpoint-resume cycle."""
        manager = CheckpointManager(
            state_file=tmp_path / "state.json",
            request_file=tmp_path / "request.json",
            response_file=tmp_path / "response.json"
        )

        # Phase 1: Save checkpoint before agent invocation
        state = TemplateCreateState(
            phase=1,
            phase_name="codebase_analysis",
            checkpoint_name="before_agent_invocation",
            output_path=str(tmp_path / "output"),
            phase_data={"samples": ["file1.py", "file2.py"]}
        )

        request = {
            "request_id": "test-123",
            "agent_name": "architectural-reviewer",
            "prompt": "Analyze..."
        }

        manager.save_checkpoint(state, request)

        # Simulate external agent invocation
        response = {
            "request_id": "test-123",
            "status": "success",
            "response": json.dumps({
                "technology_stack": {"primary_language": "Python"},
                "overall_confidence": 0.92
            })
        }
        manager.response_file.write_text(json.dumps(response))

        # Phase 2: Resume from checkpoint
        assert manager.is_resuming() is True
        assert manager.has_agent_response() is True

        loaded_state = manager.load_checkpoint()
        loaded_response = manager.load_agent_response()

        assert loaded_state.phase == 1
        assert loaded_response["status"] == "success"

        # Cleanup
        manager.clear_checkpoint()
        assert manager.is_resuming() is False

    def test_mock_invoker_workflow(self):
        """Test using mock invoker for direct invocation."""
        mock = MockAgentInvoker()
        mock.add_response_from_dict("architectural-reviewer", {
            "technology_stack": {"primary_language": "C#"},
            "overall_confidence": 0.95
        })

        response = mock.invoke(
            agent_name="architectural-reviewer",
            prompt="Analyze this codebase..."
        )

        result = json.loads(response)
        assert result["technology_stack"]["primary_language"] == "C#"
        assert result["overall_confidence"] == 0.95

        # Verify invocation recorded
        invocations = mock.get_invocations("architectural-reviewer")
        assert len(invocations) == 1
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
| Checkpoint save/load | 100% reliable | Integration tests |
| Response parsing | 100% accurate | Unit tests |
| Mock functionality | Complete | All test scenarios pass |

---

## Notes

- Exit code 42 signals checkpoint (orchestrator catches and exits)
- Files are created in project root (not output directory)
- Cleanup happens on success or explicit clear

---

**Created**: 2025-11-18
**Phase**: 2 of 8 (Template-Create Redesign)
**Related**: AGENT-BRIDGE-SCHEMAS.md, TASK-AGENT-BRIDGE-ENHANCEMENT
