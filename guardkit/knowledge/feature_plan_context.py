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

        # 8. Implementation modes (AutoBuild support)
        if self.implementation_modes:
            modes_text = self._format_implementation_modes()
            sections.append(f"## Implementation Modes\n\n{modes_text}")

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

        Uses emoji markers:
        - ✓ for must_do items
        - ✗ for must_not_do items
        - ❓ for ask_before items (TASK-GR6-007)

        Returns:
            Formatted role constraints
        """
        lines = []
        for constraint in self.role_constraints[:2]:  # Player and Coach
            role = constraint.get('role', 'unknown')
            must_do = constraint.get('must_do', [])
            must_not_do = constraint.get('must_not_do', [])
            ask_before = constraint.get('ask_before', [])
            lines.append(f"**{role.title()}**:")
            for item in must_do[:3]:
                lines.append(f"  ✓ {item}")
            for item in must_not_do[:3]:
                lines.append(f"  ✗ {item}")
            for item in ask_before[:3]:
                lines.append(f"  ❓ {item}")
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

    def _format_implementation_modes(self) -> str:
        """Format implementation modes for prompt (AutoBuild support).

        Formats implementation mode guidance to clarify direct vs task-work
        patterns and prevent file location errors.

        Returns:
            Formatted implementation modes
        """
        lines = []
        for mode_config in self.implementation_modes[:3]:  # Limit to 3 modes
            mode = mode_config.get('mode', 'unknown')
            pattern = mode_config.get('pattern', '')
            description = mode_config.get('description', '')
            if description:
                lines.append(f"**{mode}**: {pattern} ({description})")
            else:
                lines.append(f"**{mode}**: {pattern}")
        return '\n'.join(lines)


# =============================================================================
# FeaturePlanContextBuilder - Builds rich context for feature planning
# =============================================================================

from pathlib import Path
from typing import List, Optional


class FeaturePlanContextBuilder:
    """Builds rich context for feature planning.

    This class gathers comprehensive context from Graphiti and local feature
    specifications to support feature planning. It provides graceful degradation
    when Graphiti is unavailable or queries fail.

    Attributes:
        project_root: Path to the project root directory
        feature_detector: FeatureDetector instance for finding feature specs
        graphiti_client: GraphitiClient instance for knowledge queries

    Example:
        builder = FeaturePlanContextBuilder(project_root=Path("/path/to/project"))
        context = await builder.build_context(
            description="Implement FEAT-GR-003 for enhanced context",
            context_files=[],
            tech_stack="python"
        )
    """

    def __init__(self, project_root: Path):
        """Initialize the builder.

        Args:
            project_root: Path to the project root directory

        Raises:
            TypeError: If project_root is None
        """
        if project_root is None:
            raise TypeError("project_root cannot be None")
        self.project_root = project_root

        # Import here to avoid circular imports
        from .feature_detector import FeatureDetector
        from .graphiti_client import get_graphiti

        self.feature_detector = FeatureDetector(project_root)
        self.graphiti_client = get_graphiti()

    async def build_context(
        self,
        description: str,
        context_files: Optional[List[Path]] = None,
        tech_stack: str = "python"
    ) -> FeaturePlanContext:
        """Build comprehensive context for feature planning.

        Gathers context from:
        - Feature specification files (via FeatureDetector)
        - Related features from Graphiti
        - Relevant patterns for the tech stack
        - Warnings from past failed approaches
        - Role constraints (AutoBuild support)
        - Quality gate configs (AutoBuild support)
        - Implementation modes (AutoBuild support)
        - Project architecture context
        - Similar implementations

        Args:
            description: Feature description (may contain FEAT-XXX-NNN ID)
            context_files: Optional list of context files to include
            tech_stack: Technology stack for pattern queries (default: python)

        Returns:
            FeaturePlanContext with all gathered context
        """
        # Initialize with empty/default values
        feature_spec: Dict[str, Any] = {}
        related_features: List[Dict[str, Any]] = []
        relevant_patterns: List[Dict[str, Any]] = []
        similar_implementations: List[Dict[str, Any]] = []
        project_architecture: Dict[str, Any] = {}
        warnings: List[Dict[str, Any]] = []
        role_constraints: List[Dict[str, Any]] = []
        quality_gate_configs: List[Dict[str, Any]] = []
        implementation_modes: List[Dict[str, Any]] = []

        # Handle None context_files
        if context_files is None:
            context_files = []

        # Step 1: Detect feature ID from description
        feature_id = self.feature_detector.detect_feature_id(description)

        # Step 2: Find feature spec file if feature ID detected
        if feature_id:
            feature_spec_path = self.feature_detector.find_feature_spec(feature_id)
            if feature_spec_path and feature_spec_path.exists():
                feature_spec = self._parse_feature_spec(feature_spec_path)
                if not feature_spec.get("id"):
                    feature_spec["id"] = feature_id

        # Step 3: Query Graphiti for enrichment (with graceful degradation)
        if self.graphiti_client is not None and self.graphiti_client.enabled:
            # Query related features
            related_features = await self._safe_search(
                query=f"features related to {description}",
                group_ids=["feature_specs"]
            )

            # Query relevant patterns (tech-stack specific)
            relevant_patterns = await self._safe_search(
                query=f"patterns for {description}",
                group_ids=[f"patterns_{tech_stack}", "patterns"]
            )

            # Query warnings from past failed approaches
            warnings = await self._safe_search(
                query=f"warnings failure patterns for {description}",
                group_ids=["failure_patterns", "failed_approaches"]
            )

            # Query role constraints (AutoBuild support)
            role_constraints = await self._safe_search(
                query=f"role constraints for implementation",
                group_ids=["role_constraints"]
            )

            # Query quality gate configs (AutoBuild support)
            quality_gate_configs = await self._safe_search(
                query=f"quality gate thresholds configuration",
                group_ids=["quality_gate_configs"]
            )

            # Query implementation modes (AutoBuild support)
            implementation_modes = await self._safe_search(
                query=f"implementation modes for {description}",
                group_ids=["implementation_modes"]
            )

            # Query project architecture
            arch_results = await self._safe_search(
                query=f"project architecture overview",
                group_ids=["project_overview", "project_architecture"]
            )
            if arch_results:
                project_architecture = arch_results[0] if arch_results else {}

            # Query similar implementations
            similar_implementations = await self._safe_search(
                query=f"similar implementations to {description}",
                group_ids=["task_outcomes", "feature_completions"]
            )

        return FeaturePlanContext(
            feature_spec=feature_spec,
            related_features=related_features,
            relevant_patterns=relevant_patterns,
            similar_implementations=similar_implementations,
            project_architecture=project_architecture,
            warnings=warnings,
            role_constraints=role_constraints,
            quality_gate_configs=quality_gate_configs,
            implementation_modes=implementation_modes,
        )

    async def _safe_search(
        self,
        query: str,
        group_ids: List[str],
        num_results: int = 10
    ) -> List[Dict[str, Any]]:
        """Safely search Graphiti with error handling.

        Wraps Graphiti search with try/except to ensure graceful degradation.

        Args:
            query: Search query string
            group_ids: Group IDs to search in
            num_results: Maximum number of results

        Returns:
            List of search results, empty list on any error
        """
        if self.graphiti_client is None:
            return []

        try:
            results = await self.graphiti_client.search(
                query=query,
                group_ids=group_ids,
                num_results=num_results
            )
            return results if results else []
        except Exception:
            # Log would go here in production
            return []

    def _parse_feature_spec(self, spec_path: Path) -> Dict[str, Any]:
        """Parse a feature specification file.

        Reads the feature spec markdown file and extracts frontmatter
        and content into a dictionary.

        Args:
            spec_path: Path to the feature specification file

        Returns:
            Dictionary with feature spec data
        """
        try:
            if not spec_path.exists():
                return {}

            content = spec_path.read_text()

            # Parse YAML frontmatter if present
            spec: Dict[str, Any] = {}
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    import yaml
                    try:
                        frontmatter = yaml.safe_load(parts[1])
                        if isinstance(frontmatter, dict):
                            spec.update(frontmatter)
                        spec["content"] = parts[2].strip()
                    except Exception:
                        spec["content"] = content
                else:
                    spec["content"] = content
            else:
                spec["content"] = content

            return spec
        except Exception:
            return {}
