"""Feature plan context dataclass for rich feature planning.

This module provides the FeaturePlanContext dataclass that holds rich context
for feature planning, including AutoBuild support fields for role constraints,
quality gates, and implementation modes.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class FeaturePlanContext:
    """Rich context for feature planning.

    This dataclass holds comprehensive context gathered from Graphiti during
    feature planning, including the feature specification, related features,
    patterns, and AutoBuild support context.

    Attributes:
        feature_spec: Primary feature specification
        related_features: Related features from Graphiti
        relevant_patterns: Recommended patterns for this feature
        similar_implementations: Past implementations of similar features
        project_architecture: Project architecture context
        warnings: Warnings from past failed approaches
        role_constraints: Player/Coach role boundaries (AutoBuild)
        quality_gate_configs: Task-type specific quality thresholds (AutoBuild)
        implementation_modes: Implementation mode guidance (AutoBuild)
    """

    # Primary feature
    feature_spec: Dict[str, Any]

    # Enrichment from Graphiti
    related_features: List[Dict[str, Any]]
    relevant_patterns: List[Dict[str, Any]]
    similar_implementations: List[Dict[str, Any]]
    project_architecture: Dict[str, Any]
    warnings: List[Dict[str, Any]]

    # AutoBuild support context (from TASK-REV-1505)
    role_constraints: List[Dict[str, Any]] = field(default_factory=list)
    quality_gate_configs: List[Dict[str, Any]] = field(default_factory=list)
    implementation_modes: List[Dict[str, Any]] = field(default_factory=list)

    def to_prompt_context(self, budget_tokens: int = 4000) -> str:
        """Format as context string for prompt injection.

        Formats the context as a markdown string suitable for inclusion in
        a feature planning prompt. Respects the token budget by prioritizing
        sections and truncating if necessary.

        Args:
            budget_tokens: Maximum number of tokens to use for context

        Returns:
            Formatted markdown string with feature context
        """
        sections = []
        budget_remaining = budget_tokens

        # 1. Feature spec (highest priority - 40%)
        spec_text = self._format_feature_spec()
        spec_tokens = len(spec_text.split())
        if spec_text and spec_tokens < budget_remaining * 0.4:
            sections.append(f"## Feature Specification\n\n{spec_text}")
            budget_remaining -= spec_tokens

        # 2. Project architecture context (20%)
        if self.project_architecture:
            arch_text = self._format_architecture()
            arch_tokens = len(arch_text.split())
            if arch_tokens < budget_remaining * 0.2:
                sections.append(f"## Project Architecture\n\n{arch_text}")
                budget_remaining -= arch_tokens

        # 3. Related features (15%)
        if self.related_features:
            related_text = self._format_related()
            related_tokens = len(related_text.split())
            if related_tokens < budget_remaining * 0.15:
                sections.append(f"## Related Features\n\n{related_text}")
                budget_remaining -= related_tokens

        # 4. Relevant patterns (15%)
        if self.relevant_patterns:
            patterns_text = self._format_patterns()
            patterns_tokens = len(patterns_text.split())
            if patterns_tokens < budget_remaining * 0.15:
                sections.append(f"## Recommended Patterns\n\n{patterns_text}")
                budget_remaining -= patterns_tokens

        # 5. Warnings (10%)
        if self.warnings:
            warnings_text = self._format_warnings()
            sections.append(f"## Warnings from Past Implementations\n\n{warnings_text}")

        # 6. Role constraints (AutoBuild support)
        if self.role_constraints:
            role_text = self._format_role_constraints()
            sections.append(f"## Role Constraints (Player/Coach)\n\n{role_text}")

        # 7. Quality gate configs (AutoBuild support)
        if self.quality_gate_configs:
            gate_text = self._format_quality_gates()
            sections.append(f"## Quality Gate Thresholds\n\n{gate_text}")

        return "\n\n".join(sections)

    def _format_feature_spec(self) -> str:
        """Format feature spec for prompt.

        Returns:
            Formatted feature specification
        """
        spec = self.feature_spec
        lines = [
            f"**ID**: {spec.get('id', 'N/A')}",
            f"**Title**: {spec.get('title', 'N/A')}",
            f"**Description**: {spec.get('description', 'N/A')}"
        ]

        if spec.get('success_criteria'):
            lines.append("\n**Success Criteria**:")
            for criterion in spec['success_criteria']:
                lines.append(f"- {criterion}")

        if spec.get('technical_requirements'):
            lines.append("\n**Technical Requirements**:")
            for req in spec['technical_requirements']:
                lines.append(f"- {req}")

        return '\n'.join(lines)

    def _format_architecture(self) -> str:
        """Format architecture context.

        Returns:
            Formatted architecture context
        """
        arch = self.project_architecture
        return f"""Architecture: {arch.get('architecture_style', 'N/A')}
Key Components: {', '.join(arch.get('key_components', []))}
Entry Points: {', '.join(arch.get('entry_points', []))}"""

    def _format_related(self) -> str:
        """Format related features.

        Returns:
            Formatted related features list
        """
        lines = []
        for feature in self.related_features[:3]:  # Limit to 3
            lines.append(f"- **{feature.get('id')}**: {feature.get('title')}")
        return '\n'.join(lines)

    def _format_patterns(self) -> str:
        """Format recommended patterns.

        Returns:
            Formatted patterns list
        """
        lines = []
        for pattern in self.relevant_patterns[:3]:  # Limit to 3
            when_to_use = pattern.get('when_to_use', pattern.get('description', ''))
            lines.append(f"- **{pattern.get('name')}**: {when_to_use[:100]}")
        return '\n'.join(lines)

    def _format_warnings(self) -> str:
        """Format warnings.

        Returns:
            Formatted warnings list
        """
        lines = []
        for warning in self.warnings[:3]:  # Limit to 3
            fact = warning.get('fact', str(warning))[:150]
            lines.append(f"⚠️ {fact}")
        return '\n'.join(lines)

    def _format_role_constraints(self) -> str:
        """Format role constraints for prompt (AutoBuild support).

        Formats Player and Coach role constraints to prevent role reversal
        where Player makes decisions or Coach implements.

        Returns:
            Formatted role constraints
        """
        lines = []
        for constraint in self.role_constraints[:2]:  # Player and Coach
            role = constraint.get('role', 'unknown')
            must_do = constraint.get('must_do', [])
            must_not_do = constraint.get('must_not_do', [])
            lines.append(f"**{role.title()}**:")
            for item in must_do[:3]:
                lines.append(f"  ✓ {item}")
            for item in must_not_do[:3]:
                lines.append(f"  ✗ {item}")
        return '\n'.join(lines)

    def _format_quality_gates(self) -> str:
        """Format quality gate configs for prompt (AutoBuild support).

        Formats task-type specific quality gate thresholds to prevent
        threshold drift where acceptable scores change mid-session.

        Returns:
            Formatted quality gate thresholds
        """
        lines = []
        for config in self.quality_gate_configs[:4]:  # Max 4 task types
            task_type = config.get('task_type', 'unknown')
            coverage = config.get('coverage_threshold', 0.8)
            arch_threshold = config.get('arch_review_threshold', 60)
            lines.append(f"**{task_type}**: coverage≥{coverage*100:.0f}%, arch≥{arch_threshold}")
        return '\n'.join(lines)
