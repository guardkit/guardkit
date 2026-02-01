"""Tests for FeaturePlanContext dataclass."""

import pytest
from guardkit.knowledge.feature_plan_context import FeaturePlanContext


class TestFeaturePlanContext:
    """Test suite for FeaturePlanContext dataclass."""

    @pytest.fixture
    def minimal_context(self):
        """Minimal valid context for testing."""
        return FeaturePlanContext(
            feature_spec={"id": "FEAT-001", "title": "Test Feature"},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[]
        )

    @pytest.fixture
    def full_context(self):
        """Full context with all fields populated."""
        return FeaturePlanContext(
            feature_spec={
                "id": "FEAT-SKEL-001",
                "title": "Walking Skeleton",
                "description": "Basic MCP server structure",
                "success_criteria": [
                    "Server responds to ping",
                    "Returns pong with timestamp"
                ],
                "technical_requirements": [
                    "FastMCP framework",
                    "Docker container"
                ]
            },
            related_features=[
                {"id": "FEAT-SKEL-002", "title": "Add logging"},
                {"id": "FEAT-SKEL-003", "title": "Add metrics"}
            ],
            relevant_patterns=[
                {
                    "name": "MCP Tool Pattern",
                    "when_to_use": "When creating MCP server tools",
                    "description": "Standard pattern for MCP tools"
                },
                {
                    "name": "Docker Setup",
                    "description": "Container configuration pattern"
                }
            ],
            similar_implementations=[
                {"task": "TASK-001", "outcome": "success"}
            ],
            project_architecture={
                "architecture_style": "Microservices",
                "key_components": ["API", "Worker", "Database"],
                "entry_points": ["main.py", "cli.py"]
            },
            warnings=[
                {"fact": "Avoid using deprecated MCP v1 API"},
                {"fact": "Docker networking can be tricky in dev"}
            ],
            role_constraints=[
                {
                    "role": "player",
                    "must_do": ["Implement code", "Write tests", "Run tests"],
                    "must_not_do": ["Make architectural decisions", "Skip testing"]
                },
                {
                    "role": "coach",
                    "must_do": ["Review quality", "Provide feedback", "Validate tests"],
                    "must_not_do": ["Implement code", "Write production code"]
                }
            ],
            quality_gate_configs=[
                {
                    "task_type": "scaffolding",
                    "coverage_threshold": 0.6,
                    "arch_review_threshold": 50
                },
                {
                    "task_type": "feature",
                    "coverage_threshold": 0.8,
                    "arch_review_threshold": 60
                }
            ],
            implementation_modes=[
                {"mode": "direct", "pattern": "inline"},
                {"mode": "task-work", "pattern": "worktree"}
            ]
        )

    def test_dataclass_initialization_minimal(self, minimal_context):
        """Test dataclass can be initialized with minimal required fields."""
        assert minimal_context.feature_spec == {"id": "FEAT-001", "title": "Test Feature"}
        assert minimal_context.related_features == []
        assert minimal_context.role_constraints == []
        assert minimal_context.quality_gate_configs == []
        assert minimal_context.implementation_modes == []

    def test_dataclass_initialization_full(self, full_context):
        """Test dataclass can be initialized with all fields."""
        assert full_context.feature_spec["id"] == "FEAT-SKEL-001"
        assert len(full_context.related_features) == 2
        assert len(full_context.relevant_patterns) == 2
        assert len(full_context.role_constraints) == 2
        assert len(full_context.quality_gate_configs) == 2

    def test_to_prompt_context_minimal(self, minimal_context):
        """Test to_prompt_context with minimal context."""
        result = minimal_context.to_prompt_context()

        assert "## Feature Specification" in result
        assert "FEAT-001" in result
        assert "Test Feature" in result

    def test_to_prompt_context_full(self, full_context):
        """Test to_prompt_context with full context."""
        result = full_context.to_prompt_context(budget_tokens=4000)

        # Check all major sections are present
        assert "## Feature Specification" in result
        assert "## Project Architecture" in result
        assert "## Related Features" in result
        assert "## Recommended Patterns" in result
        assert "## Warnings from Past Implementations" in result
        assert "## Role Constraints (Player/Coach)" in result
        assert "## Quality Gate Thresholds" in result

    def test_to_prompt_context_budget_aware(self, full_context):
        """Test that to_prompt_context respects token budget."""
        # With small budget, should still include feature spec (highest priority)
        result = full_context.to_prompt_context(budget_tokens=100)

        assert "## Feature Specification" in result
        assert "FEAT-SKEL-001" in result

    def test_format_feature_spec_with_criteria(self, full_context):
        """Test feature spec formatting includes success criteria."""
        result = full_context._format_feature_spec()

        assert "**ID**: FEAT-SKEL-001" in result
        assert "**Title**: Walking Skeleton" in result
        assert "**Description**: Basic MCP server structure" in result
        assert "**Success Criteria**:" in result
        assert "Server responds to ping" in result
        assert "**Technical Requirements**:" in result
        assert "FastMCP framework" in result

    def test_format_feature_spec_minimal(self, minimal_context):
        """Test feature spec formatting with minimal data."""
        result = minimal_context._format_feature_spec()

        assert "**ID**: FEAT-001" in result
        assert "**Title**: Test Feature" in result
        assert "**Description**: N/A" in result

    def test_format_architecture(self, full_context):
        """Test architecture formatting."""
        result = full_context._format_architecture()

        assert "Architecture: Microservices" in result
        assert "Key Components: API, Worker, Database" in result
        assert "Entry Points: main.py, cli.py" in result

    def test_format_architecture_empty(self, minimal_context):
        """Test architecture formatting with empty data."""
        result = minimal_context._format_architecture()

        assert "Architecture: N/A" in result
        assert "Key Components:" in result
        assert "Entry Points:" in result

    def test_format_related_features(self, full_context):
        """Test related features formatting."""
        result = full_context._format_related()

        assert "**FEAT-SKEL-002**: Add logging" in result
        assert "**FEAT-SKEL-003**: Add metrics" in result

    def test_format_related_features_limit(self):
        """Test related features are limited to 3."""
        context = FeaturePlanContext(
            feature_spec={},
            related_features=[
                {"id": f"FEAT-{i}", "title": f"Feature {i}"}
                for i in range(5)
            ],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[]
        )

        result = context._format_related()
        lines = result.split('\n')
        assert len(lines) == 3

    def test_format_patterns(self, full_context):
        """Test patterns formatting."""
        result = full_context._format_patterns()

        assert "**MCP Tool Pattern**:" in result
        assert "When creating MCP server tools" in result

    def test_format_patterns_with_description_fallback(self, full_context):
        """Test patterns formatting falls back to description."""
        result = full_context._format_patterns()

        # Second pattern has no when_to_use, should use description
        assert "**Docker Setup**:" in result
        assert "Container configuration pattern" in result

    def test_format_patterns_truncates_long_text(self):
        """Test patterns formatting truncates long descriptions."""
        context = FeaturePlanContext(
            feature_spec={},
            related_features=[],
            relevant_patterns=[
                {
                    "name": "Long Pattern",
                    "when_to_use": "x" * 200  # Very long text
                }
            ],
            similar_implementations=[],
            project_architecture={},
            warnings=[]
        )

        result = context._format_patterns()
        # Should be truncated to 100 chars
        assert len(result.split(': ')[1]) <= 100

    def test_format_warnings(self, full_context):
        """Test warnings formatting."""
        result = full_context._format_warnings()

        assert "⚠️ Avoid using deprecated MCP v1 API" in result
        assert "⚠️ Docker networking can be tricky in dev" in result

    def test_format_warnings_limit(self):
        """Test warnings are limited to 3."""
        context = FeaturePlanContext(
            feature_spec={},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[
                {"fact": f"Warning {i}"}
                for i in range(5)
            ]
        )

        result = context._format_warnings()
        lines = result.split('\n')
        assert len(lines) == 3

    def test_format_warnings_truncates_long_text(self):
        """Test warnings formatting truncates long text."""
        context = FeaturePlanContext(
            feature_spec={},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[
                {"fact": "x" * 200}  # Very long warning
            ]
        )

        result = context._format_warnings()
        # Should be truncated to 150 chars (plus emoji and space)
        assert len(result) <= 154

    def test_format_role_constraints(self, full_context):
        """Test role constraints formatting (AutoBuild support)."""
        result = full_context._format_role_constraints()

        assert "**Player**:" in result
        assert "✓ Implement code" in result
        assert "✓ Write tests" in result
        assert "✗ Make architectural decisions" in result

        assert "**Coach**:" in result
        assert "✓ Review quality" in result
        assert "✗ Implement code" in result

    def test_format_role_constraints_limit(self):
        """Test role constraints are limited to 2 roles."""
        context = FeaturePlanContext(
            feature_spec={},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[],
            role_constraints=[
                {
                    "role": f"role{i}",
                    "must_do": ["task"],
                    "must_not_do": ["avoid"]
                }
                for i in range(5)
            ]
        )

        result = context._format_role_constraints()
        # Should only have 2 roles
        assert result.count("**Role") == 2

    def test_format_role_constraints_limits_items(self):
        """Test role constraints limit must_do and must_not_do to 3 each."""
        context = FeaturePlanContext(
            feature_spec={},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[],
            role_constraints=[
                {
                    "role": "player",
                    "must_do": [f"task{i}" for i in range(10)],
                    "must_not_do": [f"avoid{i}" for i in range(10)]
                }
            ]
        )

        result = context._format_role_constraints()
        # Should have max 3 of each
        assert result.count("✓") == 3
        assert result.count("✗") == 3

    def test_format_quality_gates(self, full_context):
        """Test quality gate configs formatting (AutoBuild support)."""
        result = full_context._format_quality_gates()

        assert "**scaffolding**: coverage≥60%, arch≥50" in result
        assert "**feature**: coverage≥80%, arch≥60" in result

    def test_format_quality_gates_limit(self):
        """Test quality gates are limited to 4 task types."""
        context = FeaturePlanContext(
            feature_spec={},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[],
            quality_gate_configs=[
                {
                    "task_type": f"type{i}",
                    "coverage_threshold": 0.8,
                    "arch_review_threshold": 60
                }
                for i in range(6)
            ]
        )

        result = context._format_quality_gates()
        lines = result.split('\n')
        assert len(lines) == 4

    def test_format_quality_gates_default_values(self):
        """Test quality gates use default values for missing fields."""
        context = FeaturePlanContext(
            feature_spec={},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[],
            quality_gate_configs=[
                {"task_type": "custom"}  # Missing thresholds
            ]
        )

        result = context._format_quality_gates()
        # Should use defaults: coverage=0.8 (80%), arch=60
        assert "coverage≥80%" in result
        assert "arch≥60" in result

    def test_autobuild_fields_default_to_empty_lists(self):
        """Test AutoBuild fields default to empty lists."""
        context = FeaturePlanContext(
            feature_spec={},
            related_features=[],
            relevant_patterns=[],
            similar_implementations=[],
            project_architecture={},
            warnings=[]
        )

        assert context.role_constraints == []
        assert context.quality_gate_configs == []
        assert context.implementation_modes == []

    def test_to_prompt_context_excludes_empty_autobuild_sections(self, minimal_context):
        """Test empty AutoBuild sections are excluded from prompt."""
        result = minimal_context.to_prompt_context()

        # Should not include AutoBuild sections if empty
        assert "## Role Constraints" not in result
        assert "## Quality Gate Thresholds" not in result

    def test_to_prompt_context_includes_autobuild_sections(self, full_context):
        """Test AutoBuild sections are included when populated."""
        result = full_context.to_prompt_context()

        # Should include AutoBuild sections
        assert "## Role Constraints (Player/Coach)" in result
        assert "## Quality Gate Thresholds" in result
