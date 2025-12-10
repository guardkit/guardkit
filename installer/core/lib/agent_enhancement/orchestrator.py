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

# TASK-FIX-STATE03: Use relative import for proper Python package structure
# This works in both dev (installer/core/lib/) and prod (~/.agentecflow/commands/lib/)
from ..state_paths import get_state_file, AGENT_ENHANCE_STATE

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

    TASK-FIX-DBFA: Added post-AI split detection and application.
    When AI writes monolithic file directly, orchestrator applies split post-hoc.
    """

    def __init__(
        self,
        enhancer,  # SingleAgentEnhancer instance
        resume: bool = False,
        verbose: bool = False,
        split_output: bool = True  # TASK-FIX-DBFA: Control split behavior
    ):
        """
        Initialize orchestrator.

        Args:
            enhancer: The SingleAgentEnhancer instance
            resume: If True, attempt to resume from checkpoint
            verbose: If True, show detailed progress
            split_output: If True, apply progressive disclosure split (default: True)
        """
        self.enhancer = enhancer
        self.resume = resume
        self.verbose = verbose
        self.split_output = split_output  # TASK-FIX-DBFA

        # TASK-FIX-STATE02: Use centralized state path helper
        self.state_file = get_state_file(AGENT_ENHANCE_STATE)

        # Create bridge invoker for response detection
        # This is only used for has_response() check, not for invocation
        # (invocation is handled by enhancer.py)
        try:
            import importlib
            _agent_bridge_module = importlib.import_module('installer.core.lib.agent_bridge.invoker')
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
        4. TASK-FIX-DBFA: Apply post-AI split if monolithic file detected

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
            # TASK-FIX-PD03: Pass split_output to enhancer
            # The enhancer now handles split correctly when AI returns JSON
            result = self.enhancer.enhance(
                agent_file,
                template_dir,
                split_output=self.split_output
            )

            # TASK-FIX-DBFA: Post-AI split detection and application
            # This is now a safety net - should rarely trigger after TASK-FIX-PD03
            # because enhancer.enhance() now correctly calls apply_with_split()
            if self._should_apply_split(result):
                if self.verbose:
                    logger.info("Detected monolithic file from AI (fallback), applying split...")
                result = self._apply_post_ai_split(agent_file, result)

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
        6. TASK-FIX-DBFA: Apply post-AI split if monolithic file detected

        The enhancer.enhance() method will see has_response() == True
        and load the cached response (line 272), then continue with
        enhancement logic.
        """
        # Validate state file exists
        if not self.state_file.exists():
            raise ValueError(
                f"Cannot resume - no state file found at {self.state_file.absolute()}\n"
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
                f"Expected: {self.bridge_invoker.response_file}\n"
                "The agent may not have completed yet."
            )

        # Run enhancement (will load cached response)
        try:
            # TASK-FIX-PD03: Pass split_output to enhancer
            result = self.enhancer.enhance(
                agent_file,
                template_dir,
                split_output=self.split_output
            )

            # TASK-FIX-DBFA: Post-AI split detection and application
            # Safety net - should rarely trigger after TASK-FIX-PD03
            if self._should_apply_split(result):
                if self.verbose:
                    logger.info("Detected monolithic file from AI (fallback), applying split...")
                result = self._apply_post_ai_split(agent_file, result)

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
        if self.bridge_invoker:
            request_file = self.bridge_invoker.request_file
            response_file = self.bridge_invoker.response_file

            if request_file.exists():
                request_file.unlink()
                if self.verbose:
                    logger.info("Cleaned up agent request file")

            if response_file.exists():
                response_file.unlink()
                if self.verbose:
                    logger.info("Cleaned up agent response file")

    # ========================================================================
    # TASK-FIX-DBFA: Post-AI Split Detection and Application
    # ========================================================================

    def _should_apply_split(self, result) -> bool:
        """
        Detect if post-AI split is needed.

        Returns True if:
        - split_output is enabled (not --no-split flag)
        - Result indicates success
        - No extended file was created (monolithic file written by AI)
        - Not in dry-run mode

        Args:
            result: EnhancementResult from enhancement

        Returns:
            True if split should be applied post-hoc
        """
        return (
            self.split_output and
            result.success and
            not result.extended_file and
            not self.enhancer.dry_run
        )

    def _apply_post_ai_split(self, agent_file: Path, result):
        """
        Apply progressive disclosure split after AI wrote monolithic file.

        This method is called when AI agent writes a single enhanced file
        instead of split files. It re-parses the enhanced content and
        applies splitting post-hoc.

        TASK-FIX-DBFA: Core fix for progressive disclosure regression.

        Args:
            agent_file: Path to enhanced agent file (monolithic)
            result: EnhancementResult from initial enhancement

        Returns:
            Updated EnhancementResult with split file paths

        Raises:
            ValueError: If re-parsing fails (caught and logged, returns original)
            PermissionError: If files cannot be written (caught and logged)
        """
        try:
            # Step 1: Re-parse enhanced file content
            enhancement = self.enhancer.reparse_enhanced_file(agent_file)

            if self.verbose:
                logger.info(f"Re-parsed {len(enhancement.get('sections', []))} sections")

            # Step 2: Apply split using the applier
            split_result = self.enhancer.applier.apply_with_split(
                agent_file,
                enhancement
            )

            if self.verbose:
                ext_name = split_result.extended_path.name if split_result.extended_path else "None"
                logger.info(f"Split applied: {split_result.core_path.name}, {ext_name}")

            # Step 3: Update result metadata
            result.core_file = split_result.core_path
            result.extended_file = split_result.extended_path
            result.split_output = True

            logger.info(f"✓ Progressive disclosure split applied successfully")
            if split_result.extended_path:
                logger.info(f"  Core: {split_result.core_path.name}")
                logger.info(f"  Extended: {split_result.extended_path.name}")

            return result

        except Exception as e:
            logger.warning(f"Post-AI split failed: {e}")
            logger.warning("Keeping original monolithic file")
            # Keep original monolithic file - graceful degradation
            result.split_output = False
            return result
