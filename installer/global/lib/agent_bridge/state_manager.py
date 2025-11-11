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
    """
    version: str
    checkpoint: str
    phase: int
    created_at: str
    updated_at: str
    config: dict
    phase_data: dict
    agent_request_pending: Optional[dict] = None


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
        # Load existing state to preserve created_at, or create new timestamp
        if self.state_file.exists():
            try:
                existing = json.loads(self.state_file.read_text(encoding="utf-8"))
                created_at = existing.get("created_at", datetime.now(timezone.utc).isoformat())
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
            agent_request_pending=agent_request_pending
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

    def cleanup(self) -> None:
        """Delete state file (called on successful completion).

        This method is safe to call multiple times or on non-existent files.
        """
        self.state_file.unlink(missing_ok=True)
