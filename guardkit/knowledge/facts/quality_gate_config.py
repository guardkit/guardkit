"""
Quality Gate Configuration Facts for task-type and complexity-based thresholds.

This module defines versioned, queryable quality gate configurations that
can be stored in Graphiti and retrieved based on task type and complexity.

Public API:
    QualityGateConfigFact: Dataclass for quality gate configurations
    QUALITY_GATE_CONFIGS: Predefined configurations for all task types
"""

from dataclasses import dataclass, field
from typing import Tuple, Optional, List
from datetime import datetime


@dataclass
class QualityGateConfigFact:
    """Versioned quality gate thresholds.

    This dataclass captures quality gate thresholds that vary based on
    task type and complexity level. It supports versioning for audit trails.

    Attributes:
        id: Unique identifier (e.g., QG-{task_type}-{complexity_range})
        name: Human-readable name
        task_type: Task category ("scaffolding" | "feature" | "testing" | "docs" | "refactoring")
        complexity_range: (min, max) complexity inclusive
        arch_review_required: Whether architectural review is needed
        arch_review_threshold: Minimum score for arch review (None if not required)
        test_pass_required: Whether tests must pass
        coverage_required: Whether coverage threshold applies
        coverage_threshold: Minimum coverage percentage (None if not required)
        lint_required: Whether linting must pass
        rationale: Why these thresholds for this profile
        version: Configuration version (default "1.0.0")
        effective_from: When this configuration became effective
        supersedes: Previous version ID (None for initial versions)
    """

    # Identity
    id: str  # QG-{task_type}-{complexity_range}
    name: str  # Human-readable name

    # Applicability
    task_type: str  # "scaffolding" | "feature" | "testing" | "refactoring" | "docs"
    complexity_range: Tuple[int, int]  # (min, max) complexity inclusive

    # Thresholds
    arch_review_required: bool
    arch_review_threshold: Optional[int]  # None if not required
    test_pass_required: bool
    coverage_required: bool
    coverage_threshold: Optional[float]  # None if not required
    lint_required: bool

    # Rationale
    rationale: str  # Why these thresholds for this profile

    # Versioning
    version: str = "1.0.0"
    effective_from: datetime = field(default_factory=datetime.now)
    supersedes: Optional[str] = None  # Previous version ID

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body.

        Returns:
            Dictionary suitable for Graphiti episode storage.
        """
        return {
            "entity_type": "quality_gate_config",
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type,
            "complexity_range": self.complexity_range,
            "arch_review_required": self.arch_review_required,
            "arch_review_threshold": self.arch_review_threshold,
            "test_pass_required": self.test_pass_required,
            "coverage_required": self.coverage_required,
            "coverage_threshold": self.coverage_threshold,
            "lint_required": self.lint_required,
            "rationale": self.rationale,
            "version": self.version,
            "effective_from": self.effective_from.isoformat(),
            "supersedes": self.supersedes
        }


# =============================================================================
# PREDEFINED QUALITY GATE CONFIGURATIONS
# =============================================================================

QUALITY_GATE_CONFIGS: List[QualityGateConfigFact] = [
    # Scaffolding tasks (complexity 1-3)
    QualityGateConfigFact(
        id="QG-SCAFFOLDING-LOW",
        name="Scaffolding (Low Complexity)",
        task_type="scaffolding",
        complexity_range=(1, 3),
        arch_review_required=False,
        arch_review_threshold=None,
        test_pass_required=True,
        coverage_required=False,
        coverage_threshold=None,
        lint_required=True,
        rationale="Scaffolding tasks create boilerplate with minimal logic. "
                  "No arch review needed; tests verify correctness; lint ensures consistency."
    ),

    # Simple feature tasks (complexity 1-3)
    QualityGateConfigFact(
        id="QG-FEATURE-LOW",
        name="Feature (Low Complexity)",
        task_type="feature",
        complexity_range=(1, 3),
        arch_review_required=False,
        arch_review_threshold=None,
        test_pass_required=True,
        coverage_required=True,
        coverage_threshold=60.0,
        lint_required=True,
        rationale="Simple features (config, utilities) need basic coverage but "
                  "don't warrant arch review. 60% coverage ensures basics are tested."
    ),

    # Medium feature tasks (complexity 4-6)
    QualityGateConfigFact(
        id="QG-FEATURE-MED",
        name="Feature (Medium Complexity)",
        task_type="feature",
        complexity_range=(4, 6),
        arch_review_required=True,
        arch_review_threshold=50,
        test_pass_required=True,
        coverage_required=True,
        coverage_threshold=75.0,
        lint_required=True,
        rationale="Medium features need light arch review (50) to catch obvious issues. "
                  "75% coverage balances thoroughness with practicality."
    ),

    # Complex feature tasks (complexity 7-10)
    QualityGateConfigFact(
        id="QG-FEATURE-HIGH",
        name="Feature (High Complexity)",
        task_type="feature",
        complexity_range=(7, 10),
        arch_review_required=True,
        arch_review_threshold=70,
        test_pass_required=True,
        coverage_required=True,
        coverage_threshold=80.0,
        lint_required=True,
        rationale="Complex features need rigorous arch review (70) to maintain system integrity. "
                  "80% coverage ensures critical paths are tested."
    ),

    # Testing tasks (any complexity)
    QualityGateConfigFact(
        id="QG-TESTING",
        name="Testing Task",
        task_type="testing",
        complexity_range=(1, 10),
        arch_review_required=False,
        arch_review_threshold=None,
        test_pass_required=True,
        coverage_required=False,  # Tests themselves don't need coverage
        coverage_threshold=None,
        lint_required=True,
        rationale="Test tasks add or improve tests. They must pass but don't need coverage metrics. "
                  "No arch review as tests follow existing patterns."
    ),

    # Documentation tasks (any complexity)
    QualityGateConfigFact(
        id="QG-DOCS",
        name="Documentation Task",
        task_type="docs",
        complexity_range=(1, 10),
        arch_review_required=False,
        arch_review_threshold=None,
        test_pass_required=False,
        coverage_required=False,
        coverage_threshold=None,
        lint_required=False,
        rationale="Documentation tasks don't involve code. No quality gates except manual review."
    )
]
