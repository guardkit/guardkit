"""Question templates for AutoBuild workflow customization (Context D).

Used to capture user preferences for AutoBuild (feature-build) workflow,
addressing TASK-REV-7549 findings about role reversal and threshold drift.

Categories:
- ROLE_CUSTOMIZATION_QUESTIONS: Player/Coach boundary rules
- QUALITY_GATE_QUESTIONS: Coverage and architectural review thresholds
- WORKFLOW_PREFERENCE_QUESTIONS: Implementation mode and iteration limits

Based on findings:
- Player-Coach role reversal (Player started validating, Coach started implementing)
- Quality gate threshold drift (acceptable scores changed mid-session)
- Success criteria drift (focus shifted from acceptance criteria)

Reference: TASK-REV-7549-review-report.md, Recommendations 3, 4, 12-15
"""

from typing import Dict, List
from ..core import Question


# =============================================================================
# ROLE CUSTOMIZATION QUESTIONS (Player/Coach Boundaries)
# =============================================================================

ROLE_CUSTOMIZATION_QUESTIONS: List[Question] = [
    Question(
        id="player_ask_before",
        category="role_customization",
        text="What tasks should the AI Player ALWAYS ask about before implementing?",
        options=[
            "[A]rchitecture changes (modify system structure)",
            "[S]ecurity changes (auth, encryption, permissions)",
            "[D]atabase changes (schema, migrations)",
            "[B]reaking changes (API, config format)",
            "[N]one - Player can decide autonomously",
            "[C]ustom: ___",
        ],
        default="[A]rchitecture changes (modify system structure)",
        rationale="Architecture changes have system-wide impact and benefit from human oversight",
    ),
    Question(
        id="coach_escalate_when",
        category="role_customization",
        text="What decisions should the AI Coach escalate to humans?",
        options=[
            "[F]ailed quality gates (tests, coverage, arch review)",
            "[U]nclear requirements (ambiguous acceptance criteria)",
            "[C]onflicting patterns (existing code vs best practice)",
            "[R]isk detected (security, performance, reliability)",
            "[A]ll significant decisions",
            "[N]one - Coach can approve/reject autonomously",
        ],
        default="[F]ailed quality gates (tests, coverage, arch review)",
        rationale="Failed quality gates are objective blockers that need human resolution",
    ),
    Question(
        id="autonomous_restriction",
        category="role_customization",
        text="Are there areas where AI should NEVER make changes autonomously?",
        options=[
            "[S]ecurity code (auth, crypto, permissions)",
            "[P]roduction config (env vars, secrets)",
            "[D]atabase schema (migrations, foreign keys)",
            "[E]xternal integrations (API endpoints, webhooks)",
            "[N]one - AI can change anything if tests pass",
            "[C]ustom: ___",
        ],
        default="[S]ecurity code (auth, crypto, permissions)",
        rationale="Security-sensitive code requires human review regardless of test results",
    ),
]


# =============================================================================
# QUALITY GATE QUESTIONS (Thresholds and Standards)
# =============================================================================

QUALITY_GATE_QUESTIONS: List[Question] = [
    Question(
        id="coverage_threshold",
        category="quality_gates",
        text="What test coverage threshold is acceptable for AutoBuild tasks?",
        options=[
            "[9]0%+ (strict - production critical)",
            "[8]0% (standard - recommended)",
            "[7]0% (relaxed - prototyping)",
            "[6]0% (minimal - scaffolding only)",
            "[A]uto (based on task complexity)",
        ],
        default="[8]0% (standard - recommended)",
        rationale="80% coverage provides good confidence without excessive test burden",
    ),
    Question(
        id="arch_review_threshold",
        category="quality_gates",
        text="What architectural review score should block implementation?",
        options=[
            "[7]0+ (strict - high quality bar)",
            "[6]0+ (standard - balanced)",
            "[5]0+ (relaxed - focus on functionality)",
            "[S]kip for simple tasks (complexity <= 3)",
            "[A]lways require review",
        ],
        default="[6]0+ (standard - balanced)",
        rationale="Score 60+ catches major issues while allowing pragmatic implementation",
    ),
    Question(
        id="test_failure_handling",
        category="quality_gates",
        text="How should AutoBuild handle test failures?",
        options=[
            "[A]uto-fix up to 3 attempts, then block",
            "[A]uto-fix up to 5 attempts, then block",
            "[I]mmediate block (no auto-fix attempts)",
            "[W]arn only (continue with failing tests)",
        ],
        default="[A]uto-fix up to 3 attempts, then block",
        rationale="3 attempts balances automation with avoiding infinite fix loops",
    ),
]


# =============================================================================
# WORKFLOW PREFERENCE QUESTIONS (Mode and Iterations)
# =============================================================================

WORKFLOW_PREFERENCE_QUESTIONS: List[Question] = [
    Question(
        id="implementation_mode",
        category="workflow_prefs",
        text="What implementation mode should AutoBuild prefer?",
        options=[
            "[T]DD (test-driven: write tests first)",
            "[S]tandard (implement then test)",
            "[A]uto-detect (based on task characteristics)",
            "[B]DD (behavior-driven, requires RequireKit)",
        ],
        default="[A]uto-detect (based on task characteristics)",
        rationale="Auto-detect selects optimal mode based on task complexity and type",
    ),
    Question(
        id="max_auto_turns",
        category="workflow_prefs",
        text="How many Player-Coach iterations before requiring human intervention?",
        options=[
            "[3] turns (quick feedback)",
            "[5] turns (balanced - default)",
            "[1]0 turns (more autonomy)",
            "[U]nlimited (run until success or explicit block)",
        ],
        default="[5] turns (balanced - default)",
        rationale="5 turns provides enough iterations for complex tasks without runaway loops",
    ),
    Question(
        id="state_recovery_preference",
        category="workflow_prefs",
        text="How should AutoBuild handle state after errors?",
        options=[
            "[R]ecover (continue from last good state)",
            "[F]resh (start over on errors)",
            "[A]sk (prompt for recovery vs fresh start)",
        ],
        default="[R]ecover (continue from last good state)",
        rationale="Recovery preserves work and is more efficient than starting fresh",
    ),
]


# =============================================================================
# GROUP ID MAPPING (for Graphiti integration)
# =============================================================================

CATEGORY_TO_GROUP_ID: Dict[str, str] = {
    "role_customization": "role_constraints",
    "quality_gates": "quality_gate_configs",
    "workflow_prefs": "implementation_modes",
}


def get_group_id_for_category(category: str) -> str:
    """Get the Graphiti group_id for a question category.

    Args:
        category: Question category name

    Returns:
        Graphiti group_id for storing related decisions

    Examples:
        >>> get_group_id_for_category("role_customization")
        'role_constraints'
        >>> get_group_id_for_category("quality_gates")
        'quality_gate_configs'
    """
    return CATEGORY_TO_GROUP_ID.get(category, category)


# =============================================================================
# EXPORTS
# =============================================================================

__all__ = [
    "ROLE_CUSTOMIZATION_QUESTIONS",
    "QUALITY_GATE_QUESTIONS",
    "WORKFLOW_PREFERENCE_QUESTIONS",
    "CATEGORY_TO_GROUP_ID",
    "get_group_id_for_category",
]
