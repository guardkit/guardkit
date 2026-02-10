"""
Tests for task metadata enricher.

TDD RED Phase: These tests will fail until implementation is complete.
"""

import pytest
import yaml
from guardkit.planning.task_metadata import (
    EnrichedTask,
    enrich_task,
    render_task_markdown,
    TURN_BUDGETS,
    CONTEXT_BUDGETS,
)
from guardkit.planning.spec_parser import TaskDefinition
from guardkit.planning.target_mode import TargetConfig, TargetMode


# Fixtures
@pytest.fixture
def sample_task_low_complexity():
    """Low complexity task fixture."""
    return TaskDefinition(
        name="TASK 1: Simple utility function",
        complexity="low",
        complexity_score=2,
        task_type="implementation",
        domain_tags=["utils", "string-processing"],
        files_to_create=["src/utils.py"],
        files_to_modify=[],
        files_not_to_touch=["config.yaml"],
        dependencies=[],
        inputs="String value",
        outputs="Processed string",
        relevant_decisions=[],
        acceptance_criteria=[
            "Function exists in utils.py",
            "Function handles empty strings",
            "Function has 100% test coverage",
        ],
        implementation_notes="Use standard library only",
        player_constraints=["Only create files in src/"],
        coach_validation_commands=["pytest tests/", "ruff check src/"],
    )


@pytest.fixture
def sample_task_medium_complexity():
    """Medium complexity task fixture."""
    return TaskDefinition(
        name="TASK 2: API endpoint implementation",
        complexity="medium",
        complexity_score=5,
        task_type="implementation",
        domain_tags=["api", "users", "database"],
        files_to_create=["src/api/users.py", "tests/test_users.py"],
        files_to_modify=["src/api/__init__.py"],
        files_not_to_touch=["src/database/migrations/"],
        dependencies=["TASK-FP002-001"],
        inputs="User data payload",
        outputs="Created user response",
        relevant_decisions=["D1"],
        acceptance_criteria=[
            "POST /users endpoint exists",
            "Request validation works",
            "Database integration complete",
            "API tests pass",
        ],
        implementation_notes="Use existing database models",
        player_constraints=["Do not modify migration files", "Follow REST conventions"],
        coach_validation_commands=[
            "pytest tests/test_users.py -v",
            "ruff check src/api/",
        ],
    )


@pytest.fixture
def sample_task_high_complexity():
    """High complexity task fixture."""
    return TaskDefinition(
        name="TASK 3: Multi-service integration",
        complexity="high",
        complexity_score=9,
        task_type="integration",
        domain_tags=["payment", "orders", "integration"],
        files_to_create=[
            "src/payment/gateway.py",
            "src/orders/state_machine.py",
            "tests/integration/test_payment_flow.py",
        ],
        files_to_modify=["src/orders/models.py", "src/payment/__init__.py"],
        files_not_to_touch=["src/payment/config.py"],
        dependencies=["TASK-FP002-001", "TASK-FP002-002"],
        inputs="Order and payment data",
        outputs="Completed transaction",
        relevant_decisions=["D2", "D3"],
        acceptance_criteria=[
            "Payment gateway integration complete",
            "Order state machine implemented",
            "Rollback mechanism works",
            "E2E tests pass",
            "Load testing complete",
        ],
        implementation_notes="Consider idempotency and retry logic",
        player_constraints=[
            "Do not modify payment config",
            "Maintain backward compatibility",
        ],
        coach_validation_commands=[
            "pytest tests/integration/ -v",
            "ruff check src/payment/",
            "ruff check src/orders/",
        ],
    )


@pytest.fixture
def target_config_interactive():
    """Interactive (default) target configuration."""
    return TargetConfig(
        mode=TargetMode.INTERACTIVE,
        model_name=None,
        output_verbosity="standard",
        include_imports=False,
        include_type_hints=False,
        structured_coach_blocks=False,
    )


@pytest.fixture
def target_config_local_model():
    """Local model target configuration."""
    return TargetConfig(
        mode=TargetMode.LOCAL_MODEL,
        model_name="qwen2.5-coder:32b",
        output_verbosity="explicit",
        include_imports=True,
        include_type_hints=True,
        structured_coach_blocks=True,
    )


# Test: Module Constants
class TestModuleConstants:
    """Test that required constants are defined correctly."""

    def test_turn_budgets_exist(self):
        """Test TURN_BUDGETS constant exists and is correctly structured."""
        assert TURN_BUDGETS is not None
        assert isinstance(TURN_BUDGETS, dict)

    def test_turn_budgets_low_complexity(self):
        """Test turn budget for low complexity tasks."""
        assert "low" in TURN_BUDGETS
        assert TURN_BUDGETS["low"]["expected"] == 1
        assert TURN_BUDGETS["low"]["max"] == 3

    def test_turn_budgets_medium_complexity(self):
        """Test turn budget for medium complexity tasks."""
        assert "medium" in TURN_BUDGETS
        assert TURN_BUDGETS["medium"]["expected"] == 2
        assert TURN_BUDGETS["medium"]["max"] == 5

    def test_turn_budgets_high_complexity(self):
        """Test turn budget for high complexity tasks."""
        assert "high" in TURN_BUDGETS
        assert TURN_BUDGETS["high"]["expected"] == 3
        assert TURN_BUDGETS["high"]["max"] == 5

    def test_context_budgets_exist(self):
        """Test CONTEXT_BUDGETS constant exists and is correctly structured."""
        assert CONTEXT_BUDGETS is not None
        assert isinstance(CONTEXT_BUDGETS, dict)

    def test_context_budgets_low_complexity(self):
        """Test context budget for low complexity tasks."""
        assert "low" in CONTEXT_BUDGETS
        assert CONTEXT_BUDGETS["low"] == 2000

    def test_context_budgets_medium_complexity(self):
        """Test context budget for medium complexity tasks."""
        assert "medium" in CONTEXT_BUDGETS
        assert CONTEXT_BUDGETS["medium"] == 4000

    def test_context_budgets_high_complexity(self):
        """Test context budget for high complexity tasks."""
        assert "high" in CONTEXT_BUDGETS
        assert CONTEXT_BUDGETS["high"] == 6000


# Test: EnrichedTask Dataclass
class TestEnrichedTask:
    """Test EnrichedTask dataclass structure."""

    def test_enriched_task_exists(self):
        """Test that EnrichedTask class exists."""
        assert EnrichedTask is not None

    def test_enriched_task_has_required_fields(
        self, sample_task_low_complexity, target_config_interactive
    ):
        """Test EnrichedTask has all required fields."""
        enriched = EnrichedTask(
            task_definition=sample_task_low_complexity,
            feature_id="FEAT-FP-002",
            turn_budget={"expected": 1, "max": 3},
            graphiti_context_budget=2000,
            target_config=target_config_interactive,
            enriched_notes="Test notes",
        )

        assert enriched.task_definition == sample_task_low_complexity
        assert enriched.feature_id == "FEAT-FP-002"
        assert enriched.turn_budget == {"expected": 1, "max": 3}
        assert enriched.graphiti_context_budget == 2000
        assert enriched.target_config == target_config_interactive
        assert enriched.enriched_notes == "Test notes"

    def test_enriched_task_default_notes(
        self, sample_task_low_complexity, target_config_interactive
    ):
        """Test EnrichedTask has default empty enriched_notes."""
        enriched = EnrichedTask(
            task_definition=sample_task_low_complexity,
            feature_id="FEAT-FP-002",
            turn_budget={"expected": 1, "max": 3},
            graphiti_context_budget=2000,
            target_config=target_config_interactive,
        )

        assert enriched.enriched_notes == ""


# Test: enrich_task function
class TestEnrichTask:
    """Test the enrich_task function."""

    def test_enrich_task_function_exists(self):
        """Test that enrich_task function exists."""
        assert callable(enrich_task)

    def test_enrich_task_low_complexity_interactive(
        self, sample_task_low_complexity, target_config_interactive
    ):
        """Test enriching low complexity task for interactive target."""
        enriched = enrich_task(
            sample_task_low_complexity, target_config_interactive, "FEAT-FP-002"
        )

        assert isinstance(enriched, EnrichedTask)
        assert enriched.task_definition == sample_task_low_complexity
        assert enriched.feature_id == "FEAT-FP-002"
        assert enriched.turn_budget == {"expected": 1, "max": 3}
        assert enriched.graphiti_context_budget == 2000
        assert enriched.target_config == target_config_interactive

    def test_enrich_task_medium_complexity_interactive(
        self, sample_task_medium_complexity, target_config_interactive
    ):
        """Test enriching medium complexity task for interactive target."""
        enriched = enrich_task(
            sample_task_medium_complexity, target_config_interactive, "FEAT-FP-002"
        )

        assert enriched.turn_budget == {"expected": 2, "max": 5}
        assert enriched.graphiti_context_budget == 4000

    def test_enrich_task_high_complexity_interactive(
        self, sample_task_high_complexity, target_config_interactive
    ):
        """Test enriching high complexity task for interactive target."""
        enriched = enrich_task(
            sample_task_high_complexity, target_config_interactive, "FEAT-FP-002"
        )

        assert enriched.turn_budget == {"expected": 3, "max": 5}
        assert enriched.graphiti_context_budget == 6000

    def test_enrich_task_local_model_adds_guidance(
        self, sample_task_medium_complexity, target_config_local_model
    ):
        """Test that local model target adds import and type guidance."""
        enriched = enrich_task(
            sample_task_medium_complexity, target_config_local_model, "FEAT-FP-002"
        )

        assert enriched.target_config.include_imports is True
        assert enriched.target_config.include_type_hints is True
        # Enriched notes should contain additional guidance for local models
        assert len(enriched.enriched_notes) > 0

    def test_enrich_task_interactive_no_extra_guidance(
        self, sample_task_medium_complexity, target_config_interactive
    ):
        """Test that interactive target doesn't add extra implementation guidance."""
        enriched = enrich_task(
            sample_task_medium_complexity, target_config_interactive, "FEAT-FP-002"
        )

        assert enriched.target_config.include_imports is False
        assert enriched.target_config.include_type_hints is False

    @pytest.mark.parametrize(
        "complexity,expected_turns,max_turns,context_budget",
        [
            ("low", 1, 3, 2000),
            ("medium", 2, 5, 4000),
            ("high", 3, 5, 6000),
        ],
    )
    def test_enrich_task_budgets_by_complexity(
        self,
        target_config_interactive,
        complexity,
        expected_turns,
        max_turns,
        context_budget,
    ):
        """Test that budgets are correctly assigned based on complexity."""
        task = TaskDefinition(
            name="TASK-TEST-001: Test task",
            complexity=complexity,
            complexity_score=5,
            task_type="implementation",
            domain_tags=["test"],
            files_to_create=[],
            files_to_modify=[],
            files_not_to_touch=[],
            dependencies=[],
            inputs="Test input",
            outputs="Test output",
            relevant_decisions=[],
            acceptance_criteria=["Test"],
            implementation_notes="",
            player_constraints=[],
            coach_validation_commands=[],
        )

        enriched = enrich_task(task, target_config_interactive, "FEAT-TEST")

        assert enriched.turn_budget["expected"] == expected_turns
        assert enriched.turn_budget["max"] == max_turns
        assert enriched.graphiti_context_budget == context_budget


# Test: render_task_markdown function
class TestRenderTaskMarkdown:
    """Test the render_task_markdown function."""

    def test_render_task_markdown_function_exists(self):
        """Test that render_task_markdown function exists."""
        assert callable(render_task_markdown)

    def test_render_task_markdown_returns_string(
        self, sample_task_low_complexity, target_config_interactive
    ):
        """Test that render_task_markdown returns a string."""
        enriched = enrich_task(
            sample_task_low_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        assert isinstance(markdown, str)
        assert len(markdown) > 0

    def test_render_task_markdown_has_yaml_frontmatter(
        self, sample_task_low_complexity, target_config_interactive
    ):
        """Test that rendered markdown has YAML frontmatter."""
        enriched = enrich_task(
            sample_task_low_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        assert markdown.startswith("---\n")
        assert "---\n" in markdown[4:]  # Second delimiter exists

    def test_render_task_markdown_valid_yaml_frontmatter(
        self, sample_task_low_complexity, target_config_interactive
    ):
        """Test that YAML frontmatter is valid and parseable."""
        enriched = enrich_task(
            sample_task_low_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        # Extract YAML frontmatter
        parts = markdown.split("---\n", 2)
        assert len(parts) >= 3
        yaml_content = parts[1]

        # Parse YAML
        frontmatter = yaml.safe_load(yaml_content)
        assert isinstance(frontmatter, dict)

    def test_render_task_markdown_frontmatter_has_required_fields(
        self, sample_task_medium_complexity, target_config_interactive
    ):
        """Test that YAML frontmatter contains all required fields."""
        enriched = enrich_task(
            sample_task_medium_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        # Extract and parse YAML
        parts = markdown.split("---\n", 2)
        frontmatter = yaml.safe_load(parts[1])

        # Check required fields per acceptance criteria
        assert "id" in frontmatter or "task_id" in frontmatter
        assert "feature_id" in frontmatter
        assert "complexity" in frontmatter
        assert "complexity_score" in frontmatter
        assert "type" in frontmatter
        assert "domain_tags" in frontmatter
        assert "files_to_create" in frontmatter
        assert "files_to_modify" in frontmatter
        assert "files_not_to_touch" in frontmatter
        assert "dependencies" in frontmatter
        assert "relevant_decisions" in frontmatter
        assert "turn_budget" in frontmatter
        assert "graphiti_context_budget" in frontmatter

    def test_render_task_markdown_frontmatter_values_correct(
        self, sample_task_medium_complexity, target_config_interactive
    ):
        """Test that YAML frontmatter values match the enriched task."""
        enriched = enrich_task(
            sample_task_medium_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        # Extract and parse YAML
        parts = markdown.split("---\n", 2)
        frontmatter = yaml.safe_load(parts[1])

        # Verify values
        assert frontmatter["feature_id"] == "FEAT-FP-002"
        assert frontmatter["complexity"] == "medium"
        assert frontmatter["complexity_score"] == 5
        assert frontmatter["type"] == "implementation"
        assert frontmatter["domain_tags"] == ["api", "users", "database"]
        assert frontmatter["files_to_create"] == [
            "src/api/users.py",
            "tests/test_users.py",
        ]
        assert frontmatter["files_to_modify"] == ["src/api/__init__.py"]
        assert frontmatter["files_not_to_touch"] == ["src/database/migrations/"]
        assert frontmatter["dependencies"] == ["TASK-FP002-001"]
        assert frontmatter["relevant_decisions"] == ["D1"]
        assert frontmatter["turn_budget"]["expected"] == 2
        assert frontmatter["turn_budget"]["max"] == 5
        assert frontmatter["graphiti_context_budget"] == 4000

    def test_render_task_markdown_has_description_section(
        self, sample_task_low_complexity, target_config_interactive
    ):
        """Test that rendered markdown has Description section."""
        enriched = enrich_task(
            sample_task_low_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        assert "## Description" in markdown

    def test_render_task_markdown_has_acceptance_criteria_section(
        self, sample_task_medium_complexity, target_config_interactive
    ):
        """Test that rendered markdown has Acceptance Criteria section."""
        enriched = enrich_task(
            sample_task_medium_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        assert "## Acceptance Criteria" in markdown
        for criterion in sample_task_medium_complexity.acceptance_criteria:
            assert criterion in markdown

    def test_render_task_markdown_has_coach_validation_section(
        self, sample_task_low_complexity, target_config_interactive
    ):
        """Test that rendered markdown has Coach Validation Commands section."""
        enriched = enrich_task(
            sample_task_low_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        assert "## Coach Validation Commands" in markdown

    def test_render_task_markdown_has_player_constraints_section(
        self, sample_task_low_complexity, target_config_interactive
    ):
        """Test that rendered markdown has Player Constraints section."""
        enriched = enrich_task(
            sample_task_low_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        assert "## Player Constraints" in markdown

    def test_render_task_markdown_has_implementation_notes_section(
        self, sample_task_medium_complexity, target_config_interactive
    ):
        """Test that rendered markdown has Implementation Notes section."""
        enriched = enrich_task(
            sample_task_medium_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        assert "## Implementation Notes" in markdown
        assert sample_task_medium_complexity.implementation_notes in markdown

    def test_render_task_markdown_local_model_adds_guidance_to_notes(
        self, sample_task_medium_complexity, target_config_local_model
    ):
        """Test that local model target adds explicit guidance to implementation notes."""
        enriched = enrich_task(
            sample_task_medium_complexity, target_config_local_model, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        # Implementation Notes should contain extra guidance for local models
        notes_section = markdown.split("## Implementation Notes")[1]
        assert "import" in notes_section.lower() or "path" in notes_section.lower()

    def test_render_task_markdown_coach_validation_contains_commands(
        self, sample_task_high_complexity, target_config_interactive
    ):
        """Test that Coach Validation section includes coach validation commands."""
        enriched = enrich_task(
            sample_task_high_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        coach_section = markdown.split("## Coach Validation Commands")[1].split("##")[0]

        # Should contain the validation commands from the task
        for cmd in sample_task_high_complexity.coach_validation_commands:
            assert cmd in coach_section

    def test_render_task_markdown_player_constraints_mentions_forbidden_files(
        self, sample_task_high_complexity, target_config_interactive
    ):
        """Test that Player Constraints section mentions files not to touch."""
        enriched = enrich_task(
            sample_task_high_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        constraints_section = markdown.split("## Player Constraints")[1].split("##")[0]

        # Should mention files not to touch
        for file in sample_task_high_complexity.files_not_to_touch:
            assert file in constraints_section or "not modify" in constraints_section.lower()

    def test_render_task_markdown_includes_dependencies(
        self, sample_task_high_complexity, target_config_interactive
    ):
        """Test that rendered markdown mentions task dependencies."""
        enriched = enrich_task(
            sample_task_high_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        # Dependencies should be visible (either in frontmatter or body)
        for dep in sample_task_high_complexity.dependencies:
            assert dep in markdown

    def test_render_task_markdown_includes_relevant_decisions(
        self, sample_task_high_complexity, target_config_interactive
    ):
        """Test that rendered markdown mentions relevant decisions."""
        enriched = enrich_task(
            sample_task_high_complexity, target_config_interactive, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        # Decisions should be visible (either in frontmatter or body)
        for decision in sample_task_high_complexity.relevant_decisions:
            assert decision in markdown

    def test_render_task_markdown_empty_lists_handled(self, target_config_interactive):
        """Test that empty lists in task definition are handled gracefully."""
        task = TaskDefinition(
            name="TASK-EMPTY-001: Minimal task",
            complexity="low",
            complexity_score=1,
            task_type="implementation",
            domain_tags=[],
            files_to_create=[],
            files_to_modify=[],
            files_not_to_touch=[],
            dependencies=[],
            inputs="",
            outputs="",
            relevant_decisions=[],
            acceptance_criteria=["One criterion"],
            implementation_notes="",
            player_constraints=[],
            coach_validation_commands=[],
        )

        enriched = enrich_task(task, target_config_interactive, "FEAT-TEST")
        markdown = render_task_markdown(enriched)

        # Should still render valid markdown
        assert markdown.startswith("---\n")
        assert "## Description" in markdown
        assert "## Acceptance Criteria" in markdown

    def test_render_task_markdown_special_characters_escaped(
        self, target_config_interactive
    ):
        """Test that special characters in task content are properly handled."""
        task = TaskDefinition(
            name="TASK-SPECIAL-001: Task with special chars & < > \" '",
            complexity="low",
            complexity_score=1,
            task_type="implementation",
            domain_tags=["test&validation"],
            files_to_create=["src/special_file.py"],
            files_to_modify=[],
            files_not_to_touch=[],
            dependencies=[],
            inputs="Data with <brackets>",
            outputs="Output with {braces}",
            relevant_decisions=[],
            acceptance_criteria=[
                "Handle quotes: \"double\" and 'single'",
                "Handle symbols: & | $ #",
            ],
            implementation_notes="Use escaping for <html> tags",
            player_constraints=["Handle 'quoted' strings"],
            coach_validation_commands=["echo 'test'"],
        )

        enriched = enrich_task(task, target_config_interactive, "FEAT-TEST")
        markdown = render_task_markdown(enriched)

        # Should successfully render without errors
        assert isinstance(markdown, str)
        assert len(markdown) > 0
        # YAML frontmatter should be parseable
        parts = markdown.split("---\n", 2)
        frontmatter = yaml.safe_load(parts[1])
        assert "TASK-SPECIAL-001" in (
            frontmatter.get("id", "") or frontmatter.get("task_id", "")
        )

    @pytest.mark.parametrize(
        "target_mode,should_have_guidance",
        [
            (TargetMode.INTERACTIVE, False),
            (TargetMode.LOCAL_MODEL, True),
        ],
    )
    def test_render_task_markdown_target_mode_guidance(
        self, sample_task_medium_complexity, target_mode, should_have_guidance
    ):
        """Test that guidance is added/omitted based on target mode."""
        target_config = TargetConfig(
            mode=target_mode,
            model_name="test-model" if target_mode == TargetMode.LOCAL_MODEL else None,
            output_verbosity="explicit"
            if target_mode == TargetMode.LOCAL_MODEL
            else "standard",
            include_imports=(target_mode == TargetMode.LOCAL_MODEL),
            include_type_hints=(target_mode == TargetMode.LOCAL_MODEL),
            structured_coach_blocks=(target_mode == TargetMode.LOCAL_MODEL),
        )

        enriched = enrich_task(
            sample_task_medium_complexity, target_config, "FEAT-FP-002"
        )
        markdown = render_task_markdown(enriched)

        if should_have_guidance:
            # Local model should have additional guidance
            assert len(enriched.enriched_notes) > 0
        else:
            # Interactive should have minimal additional notes
            pass


# Test: Edge Cases and Error Handling
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_enrich_task_with_none_feature_id(
        self, sample_task_low_complexity, target_config_interactive
    ):
        """Test that None feature_id is handled."""
        # Implementation should accept None and store it
        enriched = enrich_task(
            sample_task_low_complexity, target_config_interactive, None
        )
        assert enriched.feature_id is None

    def test_render_task_markdown_multiline_description(self, target_config_interactive):
        """Test handling of multiline descriptions."""
        task = TaskDefinition(
            name="TASK-MULTI-001: Multiline test",
            complexity="low",
            complexity_score=1,
            task_type="implementation",
            domain_tags=["test"],
            files_to_create=[],
            files_to_modify=[],
            files_not_to_touch=[],
            dependencies=[],
            inputs="Multi\nline\ninput",
            outputs="Multi\nline\noutput",
            relevant_decisions=[],
            acceptance_criteria=["Test"],
            implementation_notes="Line 1\nLine 2\nLine 3\n\nParagraph 2",
            player_constraints=[],
            coach_validation_commands=[],
        )

        enriched = enrich_task(task, target_config_interactive, "FEAT-TEST")
        markdown = render_task_markdown(enriched)

        # Should preserve line breaks in notes
        assert "Line 1" in markdown
        assert "Line 2" in markdown
        assert "Line 3" in markdown

    def test_render_task_markdown_long_lists(self, target_config_interactive):
        """Test handling of very long lists in task definition."""
        task = TaskDefinition(
            name="TASK-LONG-001: Long lists test",
            complexity="high",
            complexity_score=9,
            task_type="implementation",
            domain_tags=[f"tag-{i}" for i in range(20)],
            files_to_create=[f"src/file{i}.py" for i in range(30)],
            files_to_modify=[f"src/modify{i}.py" for i in range(15)],
            files_not_to_touch=[f"config/file{i}.yaml" for i in range(10)],
            dependencies=[f"TASK-DEP-{i:03d}" for i in range(25)],
            inputs="Many inputs",
            outputs="Many outputs",
            relevant_decisions=[f"D{i}" for i in range(12)],
            acceptance_criteria=[f"Criterion {i}" for i in range(50)],
            implementation_notes="Test notes",
            player_constraints=[f"Constraint {i}" for i in range(10)],
            coach_validation_commands=[f"test_cmd_{i}" for i in range(5)],
        )

        enriched = enrich_task(task, target_config_interactive, "FEAT-TEST")
        markdown = render_task_markdown(enriched)

        # Should handle long lists without errors
        assert isinstance(markdown, str)
        assert len(markdown) > 0
        # Verify some items from each list are present
        assert "Criterion 0" in markdown
        assert "Criterion 49" in markdown
        assert "tag-0" in markdown
        assert "tag-19" in markdown
