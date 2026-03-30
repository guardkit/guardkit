"""Human-in-the-loop checkpoint hooks for the adversarial orchestrator.

Provides configurable HITL checkpoints at key pipeline stages, allowing
human review of target specifications, raw output, Coach verdicts,
rejections, and retry exhaustion. Supports interactive CLI, async webhook,
and fully automated (auto-approve) modes.

Dependencies: stdlib only (aiohttp is lazy-imported for webhook mode).
"""

from __future__ import annotations

import asyncio
import enum
import json
import logging
import sys
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger("deepagents.checkpoint")


# ---------------------------------------------------------------------------
# Checkpoint stages
# ---------------------------------------------------------------------------

class CheckpointStage(str, enum.Enum):
    """Pipeline stages where checkpoints can be inserted."""

    PRE_GENERATION = "pre-generation"
    POST_GENERATION = "post-generation"
    POST_EVALUATION = "post-evaluation"
    ON_REJECTION = "on-rejection"
    ON_EXHAUSTION = "on-exhaustion"


# ---------------------------------------------------------------------------
# Checkpoint decision
# ---------------------------------------------------------------------------

class CheckpointDecision(str, enum.Enum):
    """Human decision at a checkpoint.

    - PROCEED: Continue with the current pipeline flow.
    - SKIP: Skip this target entirely and move to next.
    - OVERRIDE: Override the Coach verdict (accept despite rejection).
    - ABORT: Abort the entire pipeline run.
    """

    PROCEED = "proceed"
    SKIP = "skip"
    OVERRIDE = "override"
    ABORT = "abort"


# ---------------------------------------------------------------------------
# Checkpoint context
# ---------------------------------------------------------------------------

@dataclass
class CheckpointContext:
    """Context passed to checkpoint hooks at each stage.

    Attributes:
        stage: Which pipeline stage triggered the checkpoint.
        target: The current target specification or identifier.
        attempt: Current retry attempt number (1-based).
        max_retries: Maximum retries allowed.
        player_output: Raw Player output (if available at this stage).
        coach_verdict: Coach verdict dict (if available at this stage).
        metadata: Additional context-specific metadata.
    """

    stage: CheckpointStage
    target: str
    attempt: int = 1
    max_retries: int = 3
    player_output: Optional[str] = None
    coach_verdict: Optional[dict] = None
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Checkpoint configuration
# ---------------------------------------------------------------------------

@dataclass
class CheckpointConfig:
    """Configuration for checkpoint hooks.

    Attributes:
        enabled: Whether checkpoints are active.
        mode: Hook mode — "cli", "webhook", or "auto".
        stages: Which stages have active checkpoints.
        webhook_url: URL for webhook mode.
        webhook_timeout: Timeout in seconds for webhook responses.
    """

    enabled: bool = True
    mode: str = "auto"
    stages: list[str] = field(default_factory=lambda: ["post-evaluation"])
    webhook_url: Optional[str] = None
    webhook_timeout: float = 300.0

    def is_stage_enabled(self, stage: CheckpointStage) -> bool:
        """Check if a given stage has checkpoints enabled."""
        return self.enabled and stage.value in self.stages


# ---------------------------------------------------------------------------
# Base hook
# ---------------------------------------------------------------------------

class CheckpointHook:
    """Base class for checkpoint hooks.

    Subclass and override ``on_checkpoint`` to implement custom
    review logic at pipeline stages.
    """

    async def on_checkpoint(
        self, stage: str, context: CheckpointContext
    ) -> CheckpointDecision:
        """Called at each enabled checkpoint stage.

        Args:
            stage: The checkpoint stage name (e.g. "post-evaluation").
            context: Full context for the checkpoint including target,
                attempt number, player output, and coach verdict.

        Returns:
            A CheckpointDecision indicating how to proceed.
        """
        return CheckpointDecision.PROCEED


# ---------------------------------------------------------------------------
# CLI hook
# ---------------------------------------------------------------------------

class CLICheckpointHook(CheckpointHook):
    """Interactive CLI prompts for human review.

    Presents checkpoint context and prompts the user to make a decision
    via stdin. Supports all four decision types with stage-appropriate
    options.
    """

    # Maps stage to available decisions
    _STAGE_OPTIONS: dict[str, list[CheckpointDecision]] = {
        CheckpointStage.PRE_GENERATION.value: [
            CheckpointDecision.PROCEED,
            CheckpointDecision.SKIP,
            CheckpointDecision.ABORT,
        ],
        CheckpointStage.POST_GENERATION.value: [
            CheckpointDecision.PROCEED,
            CheckpointDecision.SKIP,
            CheckpointDecision.ABORT,
        ],
        CheckpointStage.POST_EVALUATION.value: [
            CheckpointDecision.PROCEED,
            CheckpointDecision.OVERRIDE,
            CheckpointDecision.SKIP,
            CheckpointDecision.ABORT,
        ],
        CheckpointStage.ON_REJECTION.value: [
            CheckpointDecision.PROCEED,
            CheckpointDecision.OVERRIDE,
            CheckpointDecision.SKIP,
            CheckpointDecision.ABORT,
        ],
        CheckpointStage.ON_EXHAUSTION.value: [
            CheckpointDecision.PROCEED,
            CheckpointDecision.SKIP,
            CheckpointDecision.ABORT,
        ],
    }

    _DECISION_KEYS: dict[str, CheckpointDecision] = {
        "p": CheckpointDecision.PROCEED,
        "s": CheckpointDecision.SKIP,
        "o": CheckpointDecision.OVERRIDE,
        "a": CheckpointDecision.ABORT,
    }

    def __init__(self, *, input_fn: Any = None) -> None:
        """Initialise the CLI hook.

        Args:
            input_fn: Optional callable for reading input (for testing).
                Defaults to ``input()`` builtin.
        """
        self._input_fn = input_fn or input

    async def on_checkpoint(
        self, stage: str, context: CheckpointContext
    ) -> CheckpointDecision:
        """Display checkpoint info and prompt for a decision."""
        self._display_context(stage, context)
        options = self._STAGE_OPTIONS.get(stage, list(CheckpointDecision))
        return self._prompt_decision(options)

    def _display_context(self, stage: str, context: CheckpointContext) -> None:
        """Print checkpoint context to stdout."""
        print(f"\n{'=' * 60}")
        print(f"  CHECKPOINT: {stage}")
        print(f"{'=' * 60}")
        print(f"  Target: {context.target}")
        print(f"  Attempt: {context.attempt}/{context.max_retries}")

        if context.player_output is not None:
            preview = context.player_output[:200]
            if len(context.player_output) > 200:
                preview += "..."
            print(f"  Player output: {preview}")

        if context.coach_verdict is not None:
            print(f"  Coach verdict: {json.dumps(context.coach_verdict, indent=2)}")

        if context.metadata:
            for key, value in context.metadata.items():
                print(f"  {key}: {value}")
        print(f"{'=' * 60}")

    def _prompt_decision(
        self, options: list[CheckpointDecision]
    ) -> CheckpointDecision:
        """Prompt the user for a decision from the available options."""
        option_labels = []
        for opt in options:
            key = opt.value[0].lower()
            label = f"[{key.upper()}]{opt.value[1:]}"
            option_labels.append(label)

        prompt_str = "  Decision: " + " / ".join(option_labels) + " > "

        while True:
            try:
                raw = self._input_fn(prompt_str).strip().lower()
            except (EOFError, KeyboardInterrupt):
                return CheckpointDecision.ABORT

            if raw and raw[0] in self._DECISION_KEYS:
                decision = self._DECISION_KEYS[raw[0]]
                if decision in options:
                    return decision
                print(f"  '{raw}' is not available at this stage.")
            else:
                print(f"  Invalid choice. Options: {', '.join(o.value for o in options)}")


# ---------------------------------------------------------------------------
# Webhook hook
# ---------------------------------------------------------------------------

class WebhookCheckpointHook(CheckpointHook):
    """Posts checkpoint context to a webhook URL and waits for a response.

    The webhook receives a JSON payload with the checkpoint context and
    must respond with ``{"decision": "proceed|skip|override|abort"}``.

    Requires ``aiohttp`` (lazy-imported at first use).
    """

    def __init__(
        self,
        url: str,
        *,
        timeout: float = 300.0,
        headers: Optional[dict[str, str]] = None,
    ) -> None:
        self._url = url
        self._timeout = timeout
        self._headers = headers or {}

    async def on_checkpoint(
        self, stage: str, context: CheckpointContext
    ) -> CheckpointDecision:
        """Post context to webhook and parse the response decision."""
        try:
            import aiohttp
        except ImportError:
            logger.warning(
                "aiohttp not installed; falling back to PROCEED for webhook checkpoint"
            )
            return CheckpointDecision.PROCEED

        payload = {
            "stage": stage,
            "target": context.target,
            "attempt": context.attempt,
            "max_retries": context.max_retries,
            "player_output": context.player_output,
            "coach_verdict": context.coach_verdict,
            "metadata": context.metadata,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self._url,
                    json=payload,
                    headers=self._headers,
                    timeout=aiohttp.ClientTimeout(total=self._timeout),
                ) as resp:
                    if resp.status != 200:
                        logger.error(
                            "Webhook returned status %d; defaulting to PROCEED",
                            resp.status,
                        )
                        return CheckpointDecision.PROCEED

                    body = await resp.json()
                    decision_str = body.get("decision", "proceed")
                    try:
                        return CheckpointDecision(decision_str)
                    except ValueError:
                        logger.error(
                            "Invalid decision '%s' from webhook; defaulting to PROCEED",
                            decision_str,
                        )
                        return CheckpointDecision.PROCEED

        except asyncio.TimeoutError:
            logger.error(
                "Webhook timed out after %.0fs; defaulting to PROCEED",
                self._timeout,
            )
            return CheckpointDecision.PROCEED
        except Exception as exc:
            logger.error("Webhook request failed: %s; defaulting to PROCEED", exc)
            return CheckpointDecision.PROCEED


# ---------------------------------------------------------------------------
# Auto-approve hook
# ---------------------------------------------------------------------------

class AutoApproveHook(CheckpointHook):
    """No-op hook for fully automated pipelines.

    Always returns PROCEED, allowing the pipeline to run without
    human intervention. Optionally logs each checkpoint for audit.
    """

    def __init__(self, *, log_checkpoints: bool = False) -> None:
        self._log_checkpoints = log_checkpoints

    async def on_checkpoint(
        self, stage: str, context: CheckpointContext
    ) -> CheckpointDecision:
        if self._log_checkpoints:
            logger.info(
                "Auto-approved checkpoint: stage=%s target=%s attempt=%d/%d",
                stage,
                context.target,
                context.attempt,
                context.max_retries,
            )
        return CheckpointDecision.PROCEED


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_checkpoint_hook(config: CheckpointConfig) -> CheckpointHook:
    """Create the appropriate checkpoint hook from configuration.

    Args:
        config: Checkpoint configuration specifying mode and parameters.

    Returns:
        A CheckpointHook instance matching the configured mode.

    Raises:
        ValueError: If the mode is not recognised.
    """
    if not config.enabled:
        return AutoApproveHook()

    if config.mode == "auto":
        return AutoApproveHook(log_checkpoints=True)
    elif config.mode == "cli":
        return CLICheckpointHook()
    elif config.mode == "webhook":
        if not config.webhook_url:
            raise ValueError("webhook_url is required for webhook mode")
        return WebhookCheckpointHook(
            url=config.webhook_url,
            timeout=config.webhook_timeout,
        )
    else:
        raise ValueError(f"Unknown checkpoint mode: {config.mode!r}")
