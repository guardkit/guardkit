"""Sprint contract negotiation hooks for weighted adversarial cooperation.

Enables iterative refinement through sprint-style contracts between the
Orchestrator and the Player/Coach agents. Each sprint has a focus area
(specific criteria to improve) and a target score.

Populated by: TASK-TI-016 (Sprint Contract Negotiation)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SprintContract:
    """A sprint contract defining the focus for the next revision cycle.

    Attributes:
        sprint_number: Sequential sprint identifier.
        focus_criteria: Criteria to prioritize in this sprint.
        target_scores: Target scores per focus criterion.
        max_attempts: Maximum attempts for this sprint.
        notes: Additional context for the Player.
    """

    sprint_number: int
    focus_criteria: list[str] = field(default_factory=list)
    target_scores: dict[str, float] = field(default_factory=dict)
    max_attempts: int = 1
    notes: str = ""


class SprintNegotiator:
    """Negotiates sprint contracts based on Coach feedback.

    After a rejection, the SprintNegotiator analyzes which criteria
    scored lowest and creates a focused sprint contract for the Player.

    Args:
        max_sprints: Maximum number of sprint cycles before exhaustion.
        improvement_threshold: Minimum score improvement required per sprint.
    """

    def __init__(
        self,
        max_sprints: int = 3,
        improvement_threshold: float = 0.1,
    ) -> None:
        self._max_sprints = max_sprints
        self._improvement_threshold = improvement_threshold
        self._sprint_history: list[SprintContract] = []

    @property
    def sprint_count(self) -> int:
        return len(self._sprint_history)

    @property
    def max_sprints(self) -> int:
        return self._max_sprints

    def negotiate(
        self,
        criterion_scores: dict[str, float],
        criteria_weights: dict[str, float],
        acceptance_threshold: float,
    ) -> SprintContract | None:
        """Create a sprint contract focusing on the weakest criteria.

        Args:
            criterion_scores: Current per-criterion scores.
            criteria_weights: Criterion weights.
            acceptance_threshold: Target acceptance threshold.

        Returns:
            SprintContract for the next revision, or None if sprints exhausted.
        """
        if self.sprint_count >= self._max_sprints:
            logger.warning(
                "Sprint exhaustion: %d/%d sprints used",
                self.sprint_count,
                self._max_sprints,
            )
            return None

        # Find criteria below acceptable threshold, sorted by weighted impact
        weak_criteria = []
        for name, score in criterion_scores.items():
            weight = criteria_weights.get(name, 0.0)
            if score < acceptance_threshold:
                weak_criteria.append((name, score, weight))

        # Sort by weighted impact (highest weight * deficit first)
        weak_criteria.sort(key=lambda x: x[2] * (acceptance_threshold - x[1]), reverse=True)

        if not weak_criteria:
            return None

        focus = [name for name, _, _ in weak_criteria[:2]]  # Focus on top 2
        targets = {
            name: min(score + self._improvement_threshold, 1.0)
            for name, score, _ in weak_criteria[:2]
        }

        contract = SprintContract(
            sprint_number=self.sprint_count + 1,
            focus_criteria=focus,
            target_scores=targets,
            max_attempts=1,
            notes=f"Focus on improving: {', '.join(focus)}",
        )

        self._sprint_history.append(contract)
        logger.info(
            "Sprint %d contract: focus=%s, targets=%s",
            contract.sprint_number,
            focus,
            targets,
        )
        return contract
