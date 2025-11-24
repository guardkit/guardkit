"""
Agent Enhancement Orchestrator

Minimal orchestrator wrapper for agent enhancement with checkpoint-resume pattern.
Follows the same pattern as template_create_orchestrator.py but simplified for
single-phase workflow.

CRITICAL: This orchestrator does NOT modify enhancer.py logic.
It only handles state persistence and resume routing.

TASK-UX-FIX-E42: Implement orchestrator loop for automatic checkpoint-resume
"""

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class OrchestrationState:
    """Minimal state for checkpoint-resume."""
    agent_file: str
    template_dir: str
    strategy: str
    dry_run: bool
    verbose: bool
    timestamp: str


class AgentEnhanceOrchestrator:
    """
    Minimal orchestrator for agent enhancement with checkpoint-resume.

    This orchestrator adds automatic resume capability to SingleAgentEnhancer
    without modifying its core logic. It follows the same pattern as
    template_create_orchestrator.py but simplified for single-phase workflow.

    Workflow:
    1. First invocation: Save state, run enhancement (may exit 42)
    2. Second invocation: Detect existing response, load and continue
    3. Success: Return result

    IMPORTANT: The checkpoint-resume logic in enhancer.py (lines 269-283)
    is correct and does not need modification. This orchestrator only
    handles the state persistence and resume routing.
    """

    def __init__(
        self,
        enhancer,  # SingleAgentEnhancer instance
        resume: bool = False,
        verbose: bool = False
    ):
        """
        Initialize orchestrator.

        Args:
            enhancer: The SingleAgentEnhancer instance
            resume: If True, attempt to resume from checkpoint
            verbose: If True, show detailed progress
        """
        self.enhancer = enhancer
        self.resume = resume
        self.verbose = verbose
        self.state_file = Path(".agent-enhance-state.json")

        # Create bridge invoker for response detection
        # This is only used for has_response() check, not for invocation
        # (invocation is handled by enhancer.py)
        try:
            import importlib
            _agent_bridge_module = importlib.import_module('installer.global.lib.agent_bridge.invoker')
            AgentBridgeInvoker = _agent_bridge_module.AgentBridgeInvoker
            self.bridge_invoker = AgentBridgeInvoker(
                phase=8,
                phase_name="agent_enhancement"
            )
        except ImportError as e:
            logger.error(f"Failed to import AgentBridgeInvoker: {e}")
            self.bridge_invoker = None

    def run(
        self,
        agent_file: Path,
        template_dir: Path
    ):
        """
        Execute enhancement with checkpoint-resume pattern.

        This method implements the orchestrator loop:
        1. Check if resuming from checkpoint
        2. If resuming: Load state and continue
        3. If not resuming: Save state and run initial
        4. Handle exit code 42 (agent needed)
        5. On second invocation, load response and continue

        Args:
            agent_file: Path to agent file to enhance
            template_dir: Path to template directory

        Returns:
            EnhancementResult with success/failure details

        Raises:
            SystemExit: With code 42 if agent invocation needed
            ValueError: If state file is corrupted
            FileNotFoundError: If paths don't exist
        """
        if self.resume:
            if self.verbose:
                logger.info("Resuming from checkpoint...")
            return self._run_with_resume(agent_file, template_dir)
        else:
            return self._run_initial(agent_file, template_dir)

    def _run_initial(
        self,
        agent_file: Path,
        template_dir: Path
    ):
        """
        Initial run - may exit with code 42.

        This method:
        1. Saves state to .agent-enhance-state.json
        2. Calls enhancer.enhance() which may exit 42
        3. If enhancer returns (response was cached), clean up state

        The enhancer.enhance() method handles the checkpoint-resume
        logic internally (lines 269-283). This orchestrator only
        manages state persistence.
        """
        # Save state before potential exit 42
        self._save_state(agent_file, template_dir)

        if self.verbose:
            logger.info(f"State saved to {self.state_file}")

        # Run enhancement (may exit with code 42)
        # If agent response is already cached, this will complete
        # If agent is needed, this will exit 42 and we'll resume later
        try:
            result = self.enhancer.enhance(agent_file, template_dir)

            # Success - clean up state file
            self._cleanup_state()
            return result

        except SystemExit as e:
            if e.code == 42:
                # Expected exit for agent invocation
                # State file remains for resume
                if self.verbose:
                    logger.info("Agent invocation needed - checkpoint saved")
                raise
            else:
                # Unexpected exit code - clean up and re-raise
                self._cleanup_state()
                raise

    def _run_with_resume(
        self,
        agent_file: Path,
        template_dir: Path
    ):
        """
        Resume run - load response and continue.

        This method:
        1. Validates that state file exists
        2. Loads and validates state
        3. Checks that agent response exists
        4. Calls enhancer.enhance() which will load the response
        5. Cleans up state file on success

        The enhancer.enhance() method will see has_response() == True
        and load the cached response (line 272), then continue with
        enhancement logic.
        """
        # Validate state file exists
        if not self.state_file.exists():
            raise ValueError(
                f"Cannot resume - no state file found at {self.state_file}\n"
                "Did you run without --resume flag first?"
            )

        # Load state
        try:
            state = self._load_state()
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(
                f"State file corrupted: {e}\n"
                f"Location: {self.state_file}\n"
                "Delete the file and re-run without --resume"
            )

        if self.verbose:
            logger.info(f"Loaded state from {self.state_file}")
            logger.info(f"  Agent: {state.agent_file}")
            logger.info(f"  Template: {state.template_dir}")

        # Check that agent response exists
        if self.bridge_invoker and not self.bridge_invoker.has_response():
            raise ValueError(
                "Cannot resume - no agent response file found\n"
                "Expected: .agent-response.json\n"
                "The agent may not have completed yet."
            )

        # Run enhancement (will load cached response)
        try:
            result = self.enhancer.enhance(agent_file, template_dir)

            # Success - clean up state file
            self._cleanup_state()
            return result

        except Exception:
            # Error during enhancement - keep state for debugging
            if self.verbose:
                logger.warning("Enhancement failed - state file preserved for debugging")
            raise

    def _save_state(
        self,
        agent_file: Path,
        template_dir: Path
    ):
        """
        Save minimal state for resume.

        Unlike template-create which saves complex phase results,
        we only need to save the paths and config. The actual
        enhancement logic is stateless - it can be re-run from
        the cached agent response.
        """
        state = OrchestrationState(
            agent_file=str(agent_file.absolute()),
            template_dir=str(template_dir.absolute()),
            strategy=self.enhancer.strategy,
            dry_run=self.enhancer.dry_run,
            verbose=self.enhancer.verbose,
            timestamp=datetime.now().isoformat()
        )

        # Write state as JSON
        self.state_file.write_text(
            json.dumps(asdict(state), indent=2)
        )

    def _load_state(self) -> OrchestrationState:
        """
        Load state from checkpoint.

        Raises:
            json.JSONDecodeError: If state file is invalid JSON
            KeyError: If required fields are missing
        """
        data = json.loads(self.state_file.read_text())
        return OrchestrationState(**data)

    def _cleanup_state(self):
        """
        Clean up state file after successful completion.

        Also cleans up agent request/response files if they exist.
        This matches the cleanup behavior in template-create.
        """
        if self.state_file.exists():
            self.state_file.unlink()
            if self.verbose:
                logger.info("Cleaned up state file")

        # Clean up agent bridge files if they exist
        request_file = Path(".agent-request.json")
        response_file = Path(".agent-response.json")

        if request_file.exists():
            request_file.unlink()
            if self.verbose:
                logger.info("Cleaned up agent request file")

        if response_file.exists():
            response_file.unlink()
            if self.verbose:
                logger.info("Cleaned up agent response file")
