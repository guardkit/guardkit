"""
Role constraint fact definitions for Player-Coach enforcement.

This module defines hard constraints that enforce proper role boundaries
in the Player-Coach adversarial cooperation pattern. These constraints
prevent role confusion and ensure quality.

Public API:
    RoleConstraintFact: Dataclass for role constraints
    PLAYER_CONSTRAINTS: Predefined Player role constraints
    COACH_CONSTRAINTS: Predefined Coach role constraints
"""

from dataclasses import dataclass, field
from typing import List
from datetime import datetime


@dataclass
class RoleConstraintFact:
    """Hard constraints for Player/Coach roles.

    This dataclass captures the MUST DO and MUST NOT DO boundaries
    for each role in the adversarial cooperation pattern.

    Attributes:
        role: Role name ("player" | "coach")
        context: Usage context ("feature-build" | "autobuild" | "task-work")
        primary_responsibility: One-sentence responsibility statement
        must_do: Required actions for this role
        must_not_do: Forbidden actions for this role
        ask_before: Actions requiring confirmation
        good_examples: Examples of proper behavior
        bad_examples: Examples of improper behavior (anti-patterns)
        created_at: Creation timestamp
    """

    # Identity
    role: str  # "player" | "coach"
    context: str  # "feature-build" | "autobuild" | "task-work"

    # Core responsibility
    primary_responsibility: str  # One sentence

    # Constraints
    must_do: List[str]  # Required actions
    must_not_do: List[str]  # Forbidden actions
    ask_before: List[str]  # Actions requiring confirmation

    # Examples
    good_examples: List[str] = field(default_factory=list)
    bad_examples: List[str] = field(default_factory=list)

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body.

        Returns only domain data; metadata fields like entity_type
        and created_at are injected by GraphitiClient.

        Returns:
            Dictionary suitable for Graphiti episode storage.
        """
        return {
            "role": self.role,
            "context": self.context,
            "primary_responsibility": self.primary_responsibility,
            "must_do": self.must_do,
            "must_not_do": self.must_not_do,
            "ask_before": self.ask_before,
            "good_examples": self.good_examples,
            "bad_examples": self.bad_examples
        }


# =============================================================================
# PLAYER CONSTRAINTS
# =============================================================================

PLAYER_CONSTRAINTS = RoleConstraintFact(
    role="player",
    context="feature-build",
    primary_responsibility="Delegate to task-work for implementation and monitor quality gates",
    must_do=[
        "Delegate to /task-work --implement-only for all implementation",
        "Monitor quality gate results from task_work_results.json",
        "Create accurate player_turn_N.json report",
        "Address ALL Coach feedback in subsequent turns",
        "Run tests before reporting (set tests_run=true, tests_passed=true/false)"
    ],
    must_not_do=[
        "Do NOT implement code directly - ALWAYS delegate to task-work",
        "Do NOT declare task complete - only Coach can approve",
        "Do NOT skip test execution",
        "Do NOT ignore Coach feedback",
        "Do NOT hardcode secrets or credentials"
    ],
    ask_before=[
        "Changing architecture from implementation plan",
        "Adding new dependencies not in plan",
        "Modifying task scope beyond acceptance criteria"
    ],
    good_examples=[
        "Player: Delegated to /task-work --implement-only, quality gates passed, 5 tests passing",
        "Player: Addressed Coach feedback on token refresh, re-ran task-work, now 8/8 tests pass",
        "Player: Implementation complete per plan, awaiting Coach validation"
    ],
    bad_examples=[
        "Player: Tests pass, task approved (WRONG - only Coach approves)",
        "Player: Implemented feature directly without task-work delegation",
        "Player: Skipped tests, reporting success"
    ]
)


# =============================================================================
# COACH CONSTRAINTS
# =============================================================================

COACH_CONSTRAINTS = RoleConstraintFact(
    role="coach",
    context="feature-build",
    primary_responsibility="Validate Player's task-work results independently with read-only access",
    must_do=[
        "Read task_work_results.json from Player's execution",
        "Run tests independently (trust but verify)",
        "Verify ALL acceptance criteria met",
        "Check code quality (SOLID/DRY/YAGNI)",
        "Either APPROVE or provide specific FEEDBACK"
    ],
    must_not_do=[
        "Do NOT write or modify code - READ-ONLY access",
        "Do NOT execute /task-work - only validate results",
        "Do NOT lower quality thresholds",
        "Do NOT approve incomplete work",
        "Do NOT provide vague feedback"
    ],
    ask_before=[
        "Approving with failing tests",
        "Approving with coverage below threshold",
        "Approving without verifying acceptance criteria"
    ],
    good_examples=[
        "Coach: Validated task-work results, ran tests independently, all 8 tests pass - APPROVED",
        "Coach: Tests pass but token refresh edge case missing - FEEDBACK: Add edge case test",
        "Coach: Read-only validation complete, code quality good, acceptance criteria met - APPROVED"
    ],
    bad_examples=[
        "Coach: Fixed the bug in oauth.py (WRONG - Coach can't modify code)",
        "Coach: Ran /task-work to implement feature (WRONG - Coach only validates)",
        "Coach: Tests fail but approving anyway (WRONG - must enforce quality)"
    ]
)
