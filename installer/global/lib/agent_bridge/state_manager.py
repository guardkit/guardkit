"""
Template Create State Manager

Handles state persistence for checkpoint-resume pattern.
Enables Python orchestrator to save/restore state across agent invocation cycles.
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


@dataclass
class TemplateCreateState:
    """Complete orchestrator state for checkpoint-resume.

    Attributes:
        version: Protocol version (semantic versioning)
        checkpoint: Current checkpoint name (e.g., "templates_generated")
        phase: Current phase number (1-8)
        created_at: Initial state creation timestamp (ISO 8601)
        updated_at: Last state update timestamp (ISO 8601)
        config: Orchestrator configuration (codebase_path, output_location, etc.)
        phase_data: Results from completed phases (qa_answers, analysis, etc.)
        agent_request_pending: Agent request metadata if waiting for response
        resume_count: Number of resume attempts (prevents infinite loops)
    """
    version: str
    checkpoint: str
    phase: int
    created_at: str
    updated_at: str
    config: dict
    phase_data: dict
    agent_request_pending: Optional[dict] = None
    resume_count: int = 0


class StateManager:
    """Manages orchestrator state for checkpoint-resume pattern.

    Handles saving and loading complete orchestrator state to enable resumption
    after agent invocations. Preserves created_at timestamp across updates.

    Example:
        >>> manager = StateManager()
        >>>
        >>> # Save state before agent invocation
        >>> manager.save_state(
        ...     checkpoint="templates_generated",
        ...     phase=5,
        ...     config={"codebase_path": "/path/to/code"},
        ...     phase_data={"analysis": {...}, "templates": [...]}
        ... )
        >>>
        >>> # After resume: Load state
        >>> state = manager.load_state()
        >>> print(state.checkpoint)  # "templates_generated"
        >>>
        >>> # On successful completion: Cleanup
        >>> manager.cleanup()
    """

    def __init__(self, state_file: Path = Path(".template-create-state.json")):
        """Initialize state manager.

        Args:
            state_file: Path to state file (default: ./.template-create-state.json)
        """
        self.state_file = state_file

    def save_state(
        self,
        checkpoint: str,
        phase: int,
        config: dict,
        phase_data: dict,
        agent_request_pending: Optional[dict] = None
    ) -> None:
        """Save orchestrator state to file.

        Preserves created_at timestamp if updating existing state.
        Sets updated_at to current timestamp.

        Args:
            checkpoint: Current checkpoint name (e.g., "templates_generated")
            phase: Current phase number (1-8)
            config: Orchestrator configuration
            phase_data: Results from completed phases
            agent_request_pending: Agent request metadata (if waiting for response)

        Raises:
            OSError: If unable to write state file
        """
        # Load existing state to preserve created_at and resume_count
        resume_count = 0
        if self.state_file.exists():
            try:
                existing = json.loads(self.state_file.read_text(encoding="utf-8"))
                created_at = existing.get("created_at", datetime.now(timezone.utc).isoformat())
                resume_count = existing.get("resume_count", 0)
            except (json.JSONDecodeError, OSError):
                # If existing state is corrupted, create new timestamp
                created_at = datetime.now(timezone.utc).isoformat()
        else:
            created_at = datetime.now(timezone.utc).isoformat()

        # Create state object
        state = TemplateCreateState(
            version="1.0",
            checkpoint=checkpoint,
            phase=phase,
            created_at=created_at,
            updated_at=datetime.now(timezone.utc).isoformat(),
            config=config,
            phase_data=phase_data,
            agent_request_pending=agent_request_pending,
            resume_count=resume_count
        )

        # Write to file with proper formatting
        self.state_file.write_text(
            json.dumps(asdict(state), indent=2),
            encoding="utf-8"
        )

    def load_state(self) -> TemplateCreateState:
        """Load orchestrator state from file.

        Returns:
            TemplateCreateState object with complete orchestrator state

        Raises:
            FileNotFoundError: If state file doesn't exist
            ValueError: If state file contains malformed JSON or invalid format
        """
        if not self.state_file.exists():
            raise FileNotFoundError(
                f"State file not found: {self.state_file}\n"
                "Cannot resume - no saved state exists."
            )

        try:
            data = json.loads(self.state_file.read_text(encoding="utf-8"))
            return TemplateCreateState(**data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Malformed state file: {e}")
        except TypeError as e:
            raise ValueError(f"Invalid state format: {e}")

    def has_state(self) -> bool:
        """Check if state file exists.

        Returns:
            True if state file exists, False otherwise
        """
        return self.state_file.exists()

    def increment_resume_count(self) -> int:
        """Increment and return the resume count.

        Called when resuming to track number of resume attempts.
        Prevents infinite loops by enabling callers to check count.

        Returns:
            New resume count after increment

        Raises:
            FileNotFoundError: If state file doesn't exist
            ValueError: If state file is malformed
        """
        state = self.load_state()
        new_count = state.resume_count + 1

        # Update state with new count
        self.save_state(
            checkpoint=state.checkpoint,
            phase=state.phase,
            config=state.config,
            phase_data=state.phase_data,
            agent_request_pending=state.agent_request_pending
        )

        # Manually update resume_count (save_state preserves existing)
        # We need to reload and explicitly set it
        data = json.loads(self.state_file.read_text(encoding="utf-8"))
        data["resume_count"] = new_count
        self.state_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )

        return new_count

    def reset_resume_count(self) -> None:
        """Reset the resume count to 0.

        Called after successful phase completion to allow new phases to have
        a fresh retry budget. Prevents exhausted resume counts from one phase
        affecting subsequent phases.

        TASK-FIX-D8F2: Counter should reset between phases to allow
        each phase its own retry budget.

        Raises:
            FileNotFoundError: If state file doesn't exist
            ValueError: If state file is malformed
        """
        if not self.state_file.exists():
            return  # No state to reset

        data = json.loads(self.state_file.read_text(encoding="utf-8"))
        data["resume_count"] = 0
        self.state_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )

    def cleanup(self) -> None:
        """Delete state file (called on successful completion).

        This method is safe to call multiple times or on non-existent files.
        """
        self.state_file.unlink(missing_ok=True)
