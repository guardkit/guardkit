"""Sprint contract negotiation for the adversarial cooperation orchestrator.

Before generation begins, the Orchestrator and Player negotiate scope
(what to generate, quality expectations, constraints) to reduce revision
cycles.  The agreed contract is used by both Player (generation targets)
and Coach (evaluation criteria).

Integrates with HITL checkpoint hooks for the ``escalate`` policy.

Dependencies: stdlib only; checkpoint_hooks (same lib) for escalation.
"""

from __future__ import annotations

import enum
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Optional, Sequence

from .checkpoint_hooks import (
    CheckpointConfig,
    CheckpointContext,
    CheckpointDecision,
    CheckpointHook,
    CheckpointStage,
    create_checkpoint_hook,
)

logger = logging.getLogger("deepagents.sprint")


# ---------------------------------------------------------------------------
# Escalation policy
# ---------------------------------------------------------------------------


class EscalationPolicy(str, enum.Enum):
    """What happens when the Coach repeatedly rejects Player output.

    - RETRY: Feed rejection issues back to Player for another attempt (default).
    - ESCALATE: After N rejections, escalate to human via HITL hooks.
    - SKIP: After N rejections, skip the target and log.
    - ABORT: After N rejections, abort the entire sprint.
    """

    RETRY = "retry"
    ESCALATE = "escalate"
    SKIP = "skip"
    ABORT = "abort"


# ---------------------------------------------------------------------------
# Quality threshold
# ---------------------------------------------------------------------------


@dataclass
class QualityThreshold:
    """Minimum acceptance criteria for Coach evaluation.

    Attributes:
        min_score: Minimum Coach score to accept (1-5 scale).
        required_criteria: Criteria names that must all pass.
        allow_partial: If True, accept when min_score met even if
            some non-required criteria fail.
    """

    min_score: int = 4
    required_criteria: list[str] = field(default_factory=list)
    allow_partial: bool = False


# ---------------------------------------------------------------------------
# Target
# ---------------------------------------------------------------------------


@dataclass
class Target:
    """A single generation target within a sprint.

    Attributes:
        name: Human-readable identifier for the target.
        description: What the Player should generate.
        context: Additional context the Player may need.
        metadata: Arbitrary key-value pairs for domain use.
    """

    name: str
    description: str
    context: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Sprint contract
# ---------------------------------------------------------------------------


@dataclass
class SprintContract:
    """Structured agreement between Orchestrator and Player before generation.

    Created via negotiation: Orchestrator proposes, Player reviews and
    counter-proposes, Orchestrator accepts or adjusts.

    Attributes:
        targets: What to generate.
        quality_bar: Minimum acceptance criteria.
        constraints: Budget, format, domain rules, etc.
        max_turns: Maximum Player-Coach revision cycles per target.
        escalation_policy: What happens on repeated rejection.
        negotiation_log: Ordered record of proposals and counter-proposals.
        agreed: Whether both sides have agreed to this contract.
        agreed_at: ISO-8601 timestamp when agreement was reached.
    """

    targets: list[Target] = field(default_factory=list)
    quality_bar: QualityThreshold = field(default_factory=QualityThreshold)
    constraints: list[str] = field(default_factory=list)
    max_turns: int = 3
    escalation_policy: EscalationPolicy = EscalationPolicy.RETRY
    negotiation_log: list[dict[str, Any]] = field(default_factory=list)
    agreed: bool = False
    agreed_at: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a JSON-compatible dict for audit logging."""
        d = asdict(self)
        d["escalation_policy"] = self.escalation_policy.value
        return d


# ---------------------------------------------------------------------------
# Feasibility result
# ---------------------------------------------------------------------------


@dataclass
class FeasibilityResult:
    """Player's assessment of whether the proposed contract is feasible.

    Attributes:
        feasible: True if the Player can fulfil the contract as-is.
        adjustments: Suggested changes (e.g. reduce targets, add context).
        dropped_targets: Target names the Player cannot handle.
        requested_context: Additional context the Player needs.
    """

    feasible: bool = True
    adjustments: list[str] = field(default_factory=list)
    dropped_targets: list[str] = field(default_factory=list)
    requested_context: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Negotiation result
# ---------------------------------------------------------------------------


@dataclass
class NegotiationResult:
    """Outcome of the negotiate() call.

    Attributes:
        success: True if an agreed contract was reached.
        contract: The final (possibly adjusted) contract.
        rounds: How many negotiation rounds were needed.
        error: Reason for failure, if any.
    """

    success: bool
    contract: SprintContract
    rounds: int = 0
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Escalation result
# ---------------------------------------------------------------------------


@dataclass
class EscalationResult:
    """Outcome of applying an escalation policy.

    Attributes:
        action: The concrete action taken ("retry", "skip", "abort",
            "escalate_proceed", "escalate_skip", "escalate_abort").
        reason: Human-readable explanation.
        checkpoint_decision: The HITL decision, if escalation involved one.
    """

    action: str
    reason: str
    checkpoint_decision: Optional[CheckpointDecision] = None


# ---------------------------------------------------------------------------
# Sprint negotiator
# ---------------------------------------------------------------------------


class SprintNegotiator:
    """Orchestrates contract negotiation between Orchestrator and Player.

    The negotiation flow is:
    1. Orchestrator proposes an initial contract.
    2. Player checks feasibility.
    3. If infeasible, Player counter-proposes adjustments.
    4. Orchestrator accepts or adjusts.
    5. Steps 2-4 repeat up to ``max_rounds``.

    Args:
        feasibility_fn: Callable that evaluates a SprintContract and
            returns a FeasibilityResult.  This is typically the Player
            agent's feasibility check.
        max_rounds: Maximum negotiation rounds before giving up.
        checkpoint_hook: Optional HITL hook for escalation policy.
        on_contract_agreed: Optional callback when a contract is agreed.
    """

    def __init__(
        self,
        feasibility_fn: Callable[[SprintContract], FeasibilityResult],
        *,
        max_rounds: int = 3,
        checkpoint_hook: Optional[CheckpointHook] = None,
        on_contract_agreed: Optional[Callable[[SprintContract], None]] = None,
    ) -> None:
        self._feasibility_fn = feasibility_fn
        self._max_rounds = max_rounds
        self._checkpoint_hook = checkpoint_hook
        self._on_contract_agreed = on_contract_agreed

    # ------------------------------------------------------------------
    # Negotiation
    # ------------------------------------------------------------------

    def negotiate(self, proposal: SprintContract) -> NegotiationResult:
        """Run the negotiation loop.

        Args:
            proposal: Initial contract proposed by the Orchestrator.

        Returns:
            NegotiationResult indicating success/failure and the final contract.
        """
        contract = proposal
        contract.negotiation_log.append({
            "round": 0,
            "role": "orchestrator",
            "action": "propose",
            "targets": len(contract.targets),
            "max_turns": contract.max_turns,
            "escalation_policy": contract.escalation_policy.value,
        })

        for round_num in range(1, self._max_rounds + 1):
            result = self._feasibility_fn(contract)

            contract.negotiation_log.append({
                "round": round_num,
                "role": "player",
                "action": "review",
                "feasible": result.feasible,
                "adjustments": result.adjustments,
                "dropped_targets": result.dropped_targets,
                "requested_context": result.requested_context,
            })

            if result.feasible:
                contract.agreed = True
                contract.agreed_at = _iso_now()
                contract.negotiation_log.append({
                    "round": round_num,
                    "role": "orchestrator",
                    "action": "accept",
                })
                logger.info(
                    "Contract agreed after %d round(s): %d targets",
                    round_num,
                    len(contract.targets),
                )
                if self._on_contract_agreed:
                    self._on_contract_agreed(contract)
                return NegotiationResult(
                    success=True, contract=contract, rounds=round_num
                )

            # Apply Player's counter-proposal
            contract = self._apply_adjustments(contract, result)
            contract.negotiation_log.append({
                "round": round_num,
                "role": "orchestrator",
                "action": "adjust",
                "remaining_targets": len(contract.targets),
            })

        # Max rounds exhausted
        logger.warning(
            "Negotiation failed after %d rounds", self._max_rounds
        )
        return NegotiationResult(
            success=False,
            contract=contract,
            rounds=self._max_rounds,
            error=f"No agreement after {self._max_rounds} rounds",
        )

    # ------------------------------------------------------------------
    # Escalation
    # ------------------------------------------------------------------

    def apply_escalation(
        self,
        contract: SprintContract,
        target: Target,
        attempt: int,
        coach_issues: list[str],
    ) -> EscalationResult:
        """Apply the contract's escalation policy after a Coach rejection.

        Args:
            contract: The active sprint contract.
            target: The target that was rejected.
            attempt: Current attempt number (1-based).
            coach_issues: Issues raised by the Coach.

        Returns:
            EscalationResult describing the action taken.
        """
        policy = contract.escalation_policy

        if policy == EscalationPolicy.RETRY:
            if attempt < contract.max_turns:
                return EscalationResult(
                    action="retry",
                    reason=f"Retrying target {target.name!r} "
                    f"(attempt {attempt + 1}/{contract.max_turns})",
                )
            return EscalationResult(
                action="skip",
                reason=f"Max turns exhausted for {target.name!r} under retry policy",
            )

        if policy == EscalationPolicy.SKIP:
            return EscalationResult(
                action="skip",
                reason=f"Skipping target {target.name!r} per skip policy "
                f"(rejected on attempt {attempt})",
            )

        if policy == EscalationPolicy.ABORT:
            return EscalationResult(
                action="abort",
                reason=f"Aborting sprint: target {target.name!r} rejected "
                f"on attempt {attempt}",
            )

        if policy == EscalationPolicy.ESCALATE:
            return self._escalate_to_human(contract, target, attempt, coach_issues)

        # Unreachable with current enum, but defensive
        return EscalationResult(
            action="skip",
            reason=f"Unknown policy {policy!r}; defaulting to skip",
        )

    def _escalate_to_human(
        self,
        contract: SprintContract,
        target: Target,
        attempt: int,
        coach_issues: list[str],
    ) -> EscalationResult:
        """Escalate to human via HITL checkpoint hook."""
        if self._checkpoint_hook is None:
            logger.warning(
                "Escalation requested but no checkpoint hook configured; "
                "defaulting to skip"
            )
            return EscalationResult(
                action="skip",
                reason="No checkpoint hook for escalation; skipping",
            )

        context = CheckpointContext(
            stage=CheckpointStage.ON_REJECTION,
            target=target.name,
            attempt=attempt,
            max_retries=contract.max_turns,
            coach_verdict={"issues": coach_issues},
            metadata={
                "escalation_policy": "escalate",
                "contract_constraints": contract.constraints,
            },
        )

        import asyncio

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # Already in an async context — create a task
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as pool:
                decision = pool.submit(
                    asyncio.run,
                    self._checkpoint_hook.on_checkpoint(
                        CheckpointStage.ON_REJECTION.value, context
                    ),
                ).result()
        else:
            decision = asyncio.run(
                self._checkpoint_hook.on_checkpoint(
                    CheckpointStage.ON_REJECTION.value, context
                )
            )

        action_map = {
            CheckpointDecision.PROCEED: "retry",
            CheckpointDecision.SKIP: "skip",
            CheckpointDecision.OVERRIDE: "retry",
            CheckpointDecision.ABORT: "abort",
        }

        action = action_map.get(decision, "skip")
        return EscalationResult(
            action=action,
            reason=f"Human decided {decision.value!r} for target {target.name!r}",
            checkpoint_decision=decision,
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_adjustments(
        contract: SprintContract, result: FeasibilityResult
    ) -> SprintContract:
        """Apply Player's feasibility adjustments to the contract."""
        # Remove dropped targets
        if result.dropped_targets:
            contract.targets = [
                t
                for t in contract.targets
                if t.name not in result.dropped_targets
            ]

        # Append requested context to remaining targets
        if result.requested_context:
            for t in contract.targets:
                extra = "; ".join(result.requested_context)
                if t.context:
                    t.context += f"\n{extra}"
                else:
                    t.context = extra

        return contract


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso_now() -> str:
    """Return current UTC time as ISO-8601 string."""
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).isoformat()
