"""
Implementation Mode Analyzer for Subtask Auto-Tagging

Automatically assigns implementation mode (task-work, direct) to subtasks
based on complexity and risk analysis.

Core Capabilities:
  • Keyword-based risk detection (security, auth, database, etc.)
  • Complexity scoring from multiple factors
  • File count analysis
  • Mode assignment decision matrix
  • Integration with subtask definitions

Usage:
    from lib.implementation_mode_analyzer import assign_implementation_modes

    # Process subtasks from review_parser
    subtasks = extract_subtasks_from_review(...)
    subtasks_with_modes = assign_implementation_modes(subtasks)

    # Each subtask now has implementation_mode field:
    # {
    #     "id": "TASK-FW-001",
    #     "title": "Create /feature-plan command",
    #     "implementation_mode": "direct",  # ← Added
    #     ...
    # }
"""

from typing import List, Dict
import re


class ImplementationModeAnalyzer:
    """Analyzes subtasks and assigns appropriate implementation modes."""

    # Keywords that indicate high risk/complexity
    HIGH_RISK_KEYWORDS = [
        # Security/Auth
        "security",
        "auth",
        "authentication",
        "authorization",
        "oauth",
        "jwt",
        "token",
        "permission",
        "access control",

        # Database
        "database",
        "schema",
        "migration",
        "sql",
        "query",
        "transaction",

        # Architecture
        "refactor",
        "breaking change",
        "core",
        "foundation",
        "architecture",

        # API/Integration
        "api",
        "endpoint",
        "integration",
        "webhook",
        "external service",

        # Critical Operations
        "payment",
        "billing",
        "user data",
        "encryption",
        "security audit",
    ]

    # Keywords that suggest simple/low-risk changes
    LOW_RISK_KEYWORDS = [
        "documentation",
        "readme",
        "comment",
        "typo",
        "css",
        "style",
        "formatting",
        "lint",
        "whitespace",
        "config",
        "configuration",
    ]

    def __init__(self):
        """Initialize the analyzer."""
        pass

    def analyze_complexity(self, subtask: Dict) -> int:
        """
        Analyze subtask complexity on a scale of 0-10.

        Factors considered:
        - Existing complexity score from table (if present)
        - Risk keywords in title/description
        - File count
        - File type diversity

        Args:
            subtask: Subtask dictionary with title, description, files, etc.

        Returns:
            Complexity score (0-10)
        """
        # Start with existing complexity score if present
        base_complexity = subtask.get("complexity", 5)

        # Adjust based on risk keywords
        title = subtask.get("title", "").lower()
        description = subtask.get("description", "").lower()
        combined_text = f"{title} {description}"

        # Check for low-risk keywords first (they should dominate)
        low_risk_count = sum(1 for keyword in self.LOW_RISK_KEYWORDS if keyword in combined_text)

        # Check for high-risk keywords
        risk_count = sum(1 for keyword in self.HIGH_RISK_KEYWORDS if keyword in combined_text)

        # If low-risk keywords dominate, reduce complexity
        if low_risk_count > risk_count:
            base_complexity = max(1, base_complexity - low_risk_count)
        elif risk_count > 0:
            base_complexity = min(10, base_complexity + risk_count)

        # Adjust based on file count
        files = subtask.get("files", [])
        file_count = len(files)

        if file_count > 5:
            base_complexity = min(10, base_complexity + 2)
        elif file_count > 3:
            base_complexity = min(10, base_complexity + 1)

        # Adjust based on file type diversity
        if files:
            extensions = set(f.split('.')[-1] for f in files if '.' in f)
            if len(extensions) > 3:
                base_complexity = min(10, base_complexity + 1)

        return min(10, max(1, base_complexity))

    def is_high_risk(self, subtask: Dict) -> bool:
        """
        Check if subtask involves high-risk operations.

        High-risk tasks typically need:
        - Architectural review
        - Security review
        - Quality gates
        - Comprehensive testing

        Args:
            subtask: Subtask dictionary

        Returns:
            True if task is high-risk
        """
        title = subtask.get("title", "").lower()
        description = subtask.get("description", "").lower()
        combined_text = f"{title} {description}"

        # Check for low-risk context first (documentation, config, etc.)
        # If present, don't flag as high-risk even if keywords match
        low_risk_context = any(keyword in combined_text for keyword in self.LOW_RISK_KEYWORDS)
        if low_risk_context:
            # Still flag certain critical keywords even in low-risk context
            critical_keywords = ["security", "authentication", "authorization", "encryption", "payment"]
            return any(keyword in combined_text for keyword in critical_keywords)

        return any(keyword in combined_text for keyword in self.HIGH_RISK_KEYWORDS)

    def assign_mode(self, subtask: Dict) -> str:
        """
        Assign implementation mode to a subtask.

        Decision matrix:
        1. Check complexity >= 6 or high-risk → "task-work"
        2. Check complexity <= 3 → "direct"
        3. Medium complexity (4-5):
           - >3 files → "task-work"
           - ≤3 files → "direct"

        Args:
            subtask: Subtask dictionary

        Returns:
            Implementation mode: "task-work" | "direct"
        """
        # Analyze complexity
        complexity = self.analyze_complexity(subtask)
        is_high_risk = self.is_high_risk(subtask)

        # High complexity or high risk → task-work
        if complexity >= 6 or is_high_risk:
            return "task-work"

        # Low complexity → direct
        if complexity <= 3:
            return "direct"

        # Medium complexity (4-5) → check file count
        file_count = len(subtask.get("files", []))
        if file_count > 3:
            return "task-work"
        else:
            return "direct"

    def assign_modes_to_subtasks(self, subtasks: List[Dict]) -> List[Dict]:
        """
        Assign implementation modes to all subtasks.

        Updates each subtask dict in place with:
        - implementation_mode: "task-work" | "direct"
        - complexity_analyzed: analyzed complexity score
        - risk_level: "high" | "medium" | "low"

        Args:
            subtasks: List of subtask dictionaries

        Returns:
            Updated list of subtasks with modes assigned
        """
        for subtask in subtasks:
            # Skip if mode already set (explicit override)
            if subtask.get("implementation_mode"):
                continue

            # Assign mode
            mode = self.assign_mode(subtask)
            subtask["implementation_mode"] = mode

            # Add analysis metadata
            subtask["complexity_analyzed"] = self.analyze_complexity(subtask)
            subtask["risk_level"] = "high" if self.is_high_risk(subtask) else (
                "medium" if subtask["complexity_analyzed"] >= 4 else "low"
            )

        return subtasks


def assign_implementation_modes(subtasks: List[Dict]) -> List[Dict]:
    """
    Assign implementation modes to subtasks based on complexity and risk.

    This is the main entry point for mode assignment.

    Args:
        subtasks: List of subtask dictionaries from review_parser

    Returns:
        Updated list with implementation_mode, complexity_analyzed, and risk_level

    Example:
        >>> from lib.review_parser import extract_subtasks_from_review
        >>> from lib.implementation_mode_analyzer import assign_implementation_modes
        >>>
        >>> subtasks = extract_subtasks_from_review("review.md", "feature")
        >>> subtasks_with_modes = assign_implementation_modes(subtasks)
        >>>
        >>> for subtask in subtasks_with_modes:
        ...     print(f"{subtask['id']}: {subtask['implementation_mode']}")
        TASK-FW-001: direct
        TASK-FW-002: task-work
        TASK-FW-003: task-work
    """
    analyzer = ImplementationModeAnalyzer()
    return analyzer.assign_modes_to_subtasks(subtasks)


def get_mode_summary(subtasks: List[Dict]) -> Dict[str, int]:
    """
    Get summary of implementation modes across subtasks.

    Args:
        subtasks: List of subtasks with modes assigned

    Returns:
        Dictionary with mode counts: {"task-work": 5, "direct": 3}
    """
    summary = {
        "task-work": 0,
        "direct": 0
    }

    for subtask in subtasks:
        mode = subtask.get("implementation_mode")
        if mode and mode in summary:
            summary[mode] += 1

    return summary
