"""
Agent Bridge Invoker

Implements file-based IPC for Python→Claude agent invocation.
Uses exit code 42 to signal agent request, enabling checkpoint-resume pattern.
"""

import json
import logging
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Protocol, Union

# TASK-FIX-STATE03: Use relative import for proper Python package structure
# This works in both dev (installer/core/lib/) and prod (~/.agentecflow/commands/lib/)
from ..state_paths import get_phase_request_file, get_phase_response_file

logger = logging.getLogger(__name__)


class AgentInvoker(Protocol):
    """Protocol for agent invocation (Dependency Inversion Principle)."""

    def invoke(self, agent_name: str, prompt: str) -> str:
        """Invoke an agent with a prompt.

        Args:
            agent_name: Name of the agent to invoke
            prompt: Complete prompt text for the agent

        Returns:
            Agent response text
        """
        ...


@dataclass
class AgentRequest:
    """Agent invocation request.

    Attributes:
        request_id: Unique identifier for this request (UUID v4)
        version: Protocol version (semantic versioning)
        phase: Current phase number (1-8)
        phase_name: Human-readable phase name
        agent_name: Name of agent to invoke
        prompt: Complete prompt text for the agent
        timeout_seconds: Maximum wait time for agent response
        created_at: Request timestamp (ISO 8601 format)
        context: Additional context for debugging
        model: Optional Claude model ID to use (e.g., "claude-opus-4-20250514")
    """
    request_id: str
    version: str
    phase: int
    phase_name: str
    agent_name: str
    prompt: str
    timeout_seconds: int
    created_at: str
    context: dict
    model: Optional[str] = None


@dataclass
class AgentResponse:
    """Agent invocation response.

    Attributes:
        request_id: Unique identifier matching the request
        version: Protocol version (semantic versioning)
        status: Response status (success | error | timeout)
        response: Agent response text (None if error/timeout)
        error_message: Error description (None if success)
        error_type: Error type identifier (None if success)
        created_at: Response timestamp (ISO 8601 format)
        duration_seconds: Time taken for agent invocation
        metadata: Additional metadata (model, tokens, etc.)
    """
    request_id: str
    version: str
    status: str
    response: Optional[str]
    error_message: Optional[str]
    error_type: Optional[str]
    created_at: str
    duration_seconds: float
    metadata: dict


class AgentBridgeInvoker:
    """Bridge invoker using file-based IPC with checkpoint-resume pattern.

    When agent invocation is needed:
    1. Write request to .agent-request.json
    2. Save orchestrator state to .template-create-state.json (caller's responsibility)
    3. Exit with code 42 (NEED_AGENT)
    4. Claude detects exit code, invokes agent, writes response
    5. Claude re-runs Python with --resume flag
    6. Python loads state and response, continues execution

    Example:
        >>> invoker = AgentBridgeInvoker(phase=6, phase_name="agent_generation")
        >>>
        >>> # First run: Request agent invocation
        >>> response = invoker.invoke("architectural-reviewer", "Analyze this...")
        >>> # → Writes .agent-request.json and exits with code 42
        >>>
        >>> # After resume: Load response
        >>> invoker.load_response()
        >>> response = invoker.invoke("architectural-reviewer", "Analyze this...")
        >>> # → Returns cached response immediately
    """

    def __init__(
        self,
        request_file: Optional[Union[Path, str]] = None,
        response_file: Optional[Union[Path, str]] = None,
        phase: int = 6,
        phase_name: str = "agent_generation"
    ):
        """Initialize bridge invoker.

        Args:
            request_file: Path to write request. If None, uses
                          ~/.agentecflow/state/.agent-request-phase{phase}.json
                          for CWD independence (TASK-FIX-STATE02)
            response_file: Path to read response. If None, uses
                           ~/.agentecflow/state/.agent-response-phase{phase}.json
                           for CWD independence (TASK-FIX-STATE02)
            phase: Current phase number
            phase_name: Human-readable phase name
        """
        # TASK-FIX-STATE02: Use centralized state path helpers
        if request_file is None:
            self.request_file = get_phase_request_file(phase)
        else:
            self.request_file = Path(request_file) if isinstance(request_file, str) else request_file

        if response_file is None:
            self.response_file = get_phase_response_file(phase)
        else:
            self.response_file = Path(response_file) if isinstance(response_file, str) else response_file

        self.phase = phase
        self.phase_name = phase_name
        self._cached_response: Optional[str] = None

    def invoke(
        self,
        agent_name: str,
        prompt: str,
        timeout_seconds: int = 120,
        context: Optional[dict] = None,
        model: Optional[str] = None
    ) -> str:
        """Request agent invocation via checkpoint-resume pattern.

        If response already cached (from --resume run), return it immediately.
        Otherwise, write request and exit with code 42.

        NOTE: Caller MUST save orchestrator state before calling this method,
        as it will exit the process with code 42.

        Args:
            agent_name: Agent to invoke (e.g., "architectural-reviewer")
            prompt: Complete prompt text
            timeout_seconds: Maximum wait time for agent response
            context: Optional context for debugging
            model: Optional Claude model ID (e.g., "claude-opus-4-20250514")

        Returns:
            Agent response text (if cached from previous invocation)

        Raises:
            AgentInvocationError: If response indicates error (when loading cached response)
            SystemExit: Exits with code 42 if no cached response (checkpoint-resume)
        """
        # If we already have a cached response (from --resume), use it
        if self._cached_response is not None:
            return self._cached_response

        # Create request
        request = AgentRequest(
            request_id=str(uuid.uuid4()),
            version="1.0",
            phase=self.phase,
            phase_name=self.phase_name,
            agent_name=agent_name,
            prompt=prompt,
            timeout_seconds=timeout_seconds,
            created_at=datetime.now(timezone.utc).isoformat(),
            context=context or {},
            model=model
        )

        # Write request file
        self.request_file.write_text(
            json.dumps(request.__dict__, indent=2),
            encoding="utf-8"
        )

        print(f"  ⏸️  Requesting agent invocation: {agent_name}")
        print(f"  📝 Request written to: {self.request_file}")
        print(f"  🔄 Checkpoint: Orchestrator will resume after agent responds")

        # Exit with code 42 to signal NEED_AGENT
        # NOTE: Orchestrator must save state before calling invoke()
        sys.exit(42)

    def load_response(self) -> str:
        """Load agent response from file (called during --resume).

        Returns:
            Agent response text (guaranteed to be str per contract)

        Raises:
            FileNotFoundError: If response file doesn't exist
            AgentInvocationError: If response indicates error or timeout
            ValueError: If response file contains malformed JSON or invalid type
        """
        if not self.response_file.exists():
            raise FileNotFoundError(
                f"Agent response file not found: {self.response_file.absolute()}\n"
                "Cannot resume - agent invocation may not have completed."
            )

        # Parse response
        try:
            response_data = json.loads(self.response_file.read_text(encoding="utf-8"))

            # TASK-FIX-AGENTRESPONSE-FORMAT: Detect raw enhancement content without envelope
            # This handles the case where Claude writes the agent output directly
            # instead of wrapping it in the AgentResponse envelope format
            if "sections" in response_data and "request_id" not in response_data:
                logger.warning(
                    "Response file contains raw enhancement content, not AgentResponse envelope. "
                    "Auto-wrapping for backward compatibility. "
                    "Please update command spec to use proper envelope format."
                )
                # Wrap raw content in proper envelope
                response_data = {
                    "request_id": "auto-wrapped",
                    "version": "1.0",
                    "status": "success",
                    "response": json.dumps(response_data),  # JSON-encode the raw content
                    "error_message": None,
                    "error_type": None,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "duration_seconds": 0.0,
                    "metadata": {"auto_wrapped": True}
                }

            # TASK-FIX-AGENT-RESPONSE-FORMAT: Validate response field type (defensive)
            if "response" in response_data and response_data["response"] is not None:
                response_value = response_data["response"]

                # If response is dict, serialize to string (fix contract violation)
                if isinstance(response_value, dict):
                    logger.warning(
                        "Agent returned dict response, expected string. "
                        "Serializing to markdown-wrapped JSON for parser compatibility. "
                        "(AgentResponse contract: response field must be str)"
                    )
                    # Serialize to markdown-wrapped JSON
                    json_str = json.dumps(response_value, indent=2)
                    markdown_wrapped = f"```json\n{json_str}\n```"
                    response_data["response"] = markdown_wrapped

                elif not isinstance(response_value, str):
                    raise ValueError(
                        f"Invalid response type: expected str or dict, "
                        f"got {type(response_value).__name__}. "
                        f"AgentResponse contract requires response field to be str."
                    )

            response = AgentResponse(**response_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed response file: {e}")
        except TypeError as e:
            raise ValueError(f"Invalid response format: {e}")

        # Check status
        if response.status == "success":
            self._cached_response = response.response
            print(f"  ✓ Agent response loaded ({response.duration_seconds:.1f}s)")

            # Cleanup response file
            self.response_file.unlink(missing_ok=True)

            return response.response

        elif response.status == "timeout":
            # Cleanup response file even on error
            self.response_file.unlink(missing_ok=True)
            raise AgentInvocationError(
                f"Agent invocation timed out after {response.duration_seconds:.1f}s"
            )

        else:  # error
            # Cleanup response file even on error
            self.response_file.unlink(missing_ok=True)
            raise AgentInvocationError(
                f"Agent invocation failed: {response.error_message}\n"
                f"Error type: {response.error_type}"
            )

    def has_pending_request(self) -> bool:
        """Check if agent request file exists.

        Returns:
            True if request file exists, False otherwise
        """
        return self.request_file.exists()

    def has_response(self) -> bool:
        """Check if agent response file exists.

        Returns:
            True if response file exists, False otherwise
        """
        return self.response_file.exists()

    def clear_cache(self) -> None:
        """Clear cached response AND delete cache files.

        Use this when multiple phases need separate AI invocations.
        After clearing, the next invoke() call will write a new request
        and exit with code 42 for agent invocation.

        With phase-specific files, this prevents stale data from being
        loaded by a different phase's invoker.

        TASK-FIX-29C1: Enables multi-phase AI invocation pattern.
        TASK-FIX-7B74: Also delete cache files to prevent stale data.
        """
        self._cached_response = None
        # Delete cache files to prevent stale data from different phases
        self.request_file.unlink(missing_ok=True)
        self.response_file.unlink(missing_ok=True)


class AgentInvocationError(Exception):
    """Raised when agent invocation fails.

    This exception is raised when:
    - Agent returns error status
    - Agent invocation times out
    - Response file is malformed
    """
    pass
