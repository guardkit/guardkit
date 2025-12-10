"""
Review modes package for /task-review command.

Provides 5 specialized review modes:
- architectural: SOLID/DRY/YAGNI compliance
- code-quality: Complexity, coverage, code smells
- decision: Multi-option analysis with scoring
- technical-debt: Debt inventory and prioritization
- security: OWASP Top 10, CVE analysis, auth/authz review
"""

from typing import Dict, Any, Protocol


class ReviewMode(Protocol):
    """Interface for review modes."""

    def execute(
        self,
        task_context: Dict[str, Any],
        depth: str
    ) -> Dict[str, Any]:
        """
        Execute review analysis.

        Args:
            task_context: Task metadata and review scope
            depth: Analysis depth (quick, standard, comprehensive)

        Returns:
            Structured review results
        """
        ...


__all__ = [
    "ReviewMode",
    "architectural_review",
    "code_quality_review",
    "decision_analysis",
    "technical_debt_assessment",
    "security_audit"
]
