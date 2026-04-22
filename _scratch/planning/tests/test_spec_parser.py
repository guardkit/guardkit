"""
TDD RED PHASE: Failing tests for research template spec parser.

These tests define the expected behavior of the spec_parser module.
All tests should FAIL initially as the implementation doesn't exist yet.
"""

import pytest
from pathlib import Path
from guardkit.planning.spec_parser import (
    parse_research_template,
    Decision,
    TaskDefinition,
    ResolvedQuestion,
    Component,
    TestStrategy,
    DependencySet,
    APIContract,
    ParsedSpec,
)


# Test Fixtures - Sample Markdown Content
@pytest.fixture
def minimal_spec_content():
    """Minimal valid research template with required sections only."""
    return """# Feature Research: Minimal Example

## Problem Statement
This is a minimal problem statement for testing.

## Decision Log

| # | Decision | Rationale | Alternatives Rejected | Status |
|---|----------|-----------|----------------------|---------|
| D1 | Use JSON format | Standard and widely supported | YAML (too complex), XML (verbose) | Accepted |

## Warnings & Constraints
- Warning 1: API rate limits apply
- Warning 2: Requires authentication

## Implementation Tasks

### TASK 1: Basic Implementation
- **Complexity:** low (2/10)
- **Type:** implementation
- **Domain Tags:** [core, api]
- **Files to Create:**
  - src/parser.py
- **Files to Modify:**
  - src/main.py
- **Files NOT to Touch:**
  - config/settings.py
- **Dependencies:** None
- **Inputs:** Markdown file path
- **Outputs:** ParsedSpec object
- **Relevant Decisions:** D1
- **Acceptance Criteria:**
  1. Function exists and is callable
  2. Returns ParsedSpec object
- **Implementation Notes:** Keep it simple
- **Player Constraints:**
  - Do not modify config files
- **Coach Validation:**
  - pytest tests/unit/test_parser.py
- **Turn Budget:** 2 expected, 5 max
"""


@pytest.fixture
def full_spec_content():
    """Complete research template with all sections."""
    return """# Feature Research: Complete Example

## Problem Statement
This is a comprehensive problem statement with multiple paragraphs.

It includes detailed context and background information.

## Open Questions

1. **Question:** Should we use async or sync API?
   **Resolution:** Use async for better performance under load.

2. **Question:** What timeout value is appropriate?
   **Resolution:** 30 seconds for production, 5 seconds for development.

## Decision Log

| # | Decision | Rationale | Alternatives Rejected | Status |
|---|----------|-----------|----------------------|---------|
| D1 | Use JSON format | Standard and widely supported | YAML (too complex), XML (verbose) | Accepted |
| D2 | PostgreSQL database | ACID compliance needed | MongoDB (no transactions), SQLite (not scalable) | Accepted |
| D3 | REST API | Simple and well-understood | GraphQL (overkill), gRPC (too complex) | Proposed |

## Out of Scope
- Real-time notifications (future iteration)
- Multi-language support (deferred to v2.0)
- Advanced analytics dashboard

## Warnings & Constraints
- Warning 1: API rate limits apply (100 req/min)
- Warning 2: Requires authentication tokens
- Warning 3: Database migrations must be reversible

## Components

| Component | File Path | Purpose | Status |
|-----------|-----------|---------|--------|
| SpecParser | guardkit/planning/spec_parser.py | Parse research templates | New |
| DataModels | guardkit/planning/models.py | Define data structures | Modified |
| FileHandler | guardkit/utils/file_handler.py | File I/O operations | New |

## Data Flow
```
Input: Research Template (Markdown)
  ↓
Parser reads sections
  ↓
Validates structure
  ↓
Extracts metadata
  ↓
Output: ParsedSpec object
```

## Message Schemas

```yaml
TaskMetadata:
  name: string
  complexity: enum[low, medium, high]
  complexity_score: integer (1-10)
  task_type: string
  domain_tags: array[string]
```

## API Contracts

### Contract: parse_research_template
```python
def parse_research_template(file_path: Path) -> ParsedSpec:
    \"\"\"Parse research template into structured data.\"\"\"
    pass
```

## Test Strategy

### Unit Tests
1. **Test:** test_parse_minimal_spec
   **Expected:** All required fields populated
2. **Test:** test_parse_decision_log
   **Expected:** Decisions extracted correctly

### Integration Tests
1. **Test:** test_end_to_end_parsing
   **Expected:** Complete workflow succeeds

### Manual Verification
- Verify parsed output against original markdown
- Check for data loss or corruption

## Dependencies

### Python Packages
- markdown>=3.4.0
- pyyaml>=6.0

### System Dependencies
- None

### Environment Variables
- SPEC_TEMPLATE_PATH: Path to template directory

## Implementation Tasks

### TASK 1: Core Parser Implementation
- **Complexity:** medium (5/10)
- **Type:** implementation
- **Domain Tags:** [core, parsing, planning]
- **Files to Create:**
  - guardkit/planning/spec_parser.py
  - tests/unit/test_spec_parser.py
- **Files to Modify:**
  - guardkit/planning/__init__.py
- **Files NOT to Touch:**
  - guardkit/core/config.py
  - guardkit/cli/main.py
- **Dependencies:** TASK 2
- **Inputs:** Path to research template markdown file
- **Outputs:** ParsedSpec object with all fields populated
- **Relevant Decisions:** D1, D2
- **Acceptance Criteria:**
  1. Parser function exists and is importable
  2. Parses all sections correctly
  3. Handles missing sections gracefully
  4. Returns valid ParsedSpec object
- **Implementation Notes:** Use regex for table parsing, handle edge cases
- **Player Constraints:**
  - Must not modify existing CLI code
  - Must maintain backward compatibility
- **Coach Validation:**
  - pytest tests/unit/test_spec_parser.py -v
  - python -m guardkit.planning.spec_parser --validate
- **Turn Budget:** 3 expected, 6 max

### TASK 2: Data Model Definitions
- **Complexity:** low (2/10)
- **Type:** implementation
- **Domain Tags:** [models, data-structures]
- **Files to Create:**
  - guardkit/planning/models.py
- **Files to Modify:**
  - None
- **Files NOT to Touch:**
  - guardkit/core/models.py
- **Dependencies:** None
- **Inputs:** Specification requirements
- **Outputs:** Python dataclass definitions
- **Relevant Decisions:** D1
- **Acceptance Criteria:**
  1. All dataclasses defined with proper types
  2. Field validation included
- **Implementation Notes:** Use dataclasses with type hints
- **Player Constraints:**
  - Use Python 3.10+ syntax
- **Coach Validation:**
  - mypy guardkit/planning/models.py
- **Turn Budget:** 1 expected, 2 max
"""


@pytest.fixture
def malformed_spec_content():
    """Malformed template for error handling tests."""
    return """# Feature Research: Malformed

## Problem Statement
Valid problem statement.

## Decision Log

This is not a table - should generate parse warning.

## Implementation Tasks

### TASK 1: Incomplete Task
- **Complexity:** medium
Missing other required fields...
"""


# Test Cases

class TestParseResearchTemplateFunction:
    """Test that the main parsing function exists and has correct signature."""

    def test_function_exists_and_importable(self):
        """AC1: Function exists and is importable."""
        from guardkit.planning.spec_parser import parse_research_template
        assert callable(parse_research_template)

    def test_function_accepts_path_parameter(self, tmp_path, minimal_spec_content):
        """Function accepts Path parameter."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(minimal_spec_content)

        result = parse_research_template(spec_file)
        assert result is not None

    def test_function_returns_parsed_spec(self, tmp_path, minimal_spec_content):
        """Function returns ParsedSpec object."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(minimal_spec_content)

        result = parse_research_template(spec_file)
        assert isinstance(result, ParsedSpec)


class TestDecisionLogParsing:
    """Test parsing of Decision Log section into Decision objects."""

    def test_parses_single_decision(self, tmp_path, minimal_spec_content):
        """AC2: Parses decision log with single entry."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(minimal_spec_content)

        result = parse_research_template(spec_file)
        assert len(result.decisions) == 1
        assert result.decisions[0].number == "D1"
        assert result.decisions[0].title == "Use JSON format"
        assert result.decisions[0].rationale == "Standard and widely supported"
        assert result.decisions[0].alternatives_rejected == "YAML (too complex), XML (verbose)"
        assert result.decisions[0].adr_status == "Accepted"

    def test_parses_multiple_decisions(self, tmp_path, full_spec_content):
        """AC2: Parses decision log with multiple entries."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        assert len(result.decisions) == 3

        # Check first decision
        assert result.decisions[0].number == "D1"
        assert result.decisions[0].adr_status == "Accepted"

        # Check second decision
        assert result.decisions[1].number == "D2"
        assert result.decisions[1].title == "PostgreSQL database"

        # Check third decision
        assert result.decisions[2].number == "D3"
        assert result.decisions[2].title == "REST API"
        assert result.decisions[2].adr_status == "Proposed"

    def test_decision_fields_all_populated(self, tmp_path, full_spec_content):
        """AC2: All Decision fields are properly populated."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        decision = result.decisions[1]  # D2

        assert decision.number == "D2"
        assert decision.title == "PostgreSQL database"
        assert decision.rationale == "ACID compliance needed"
        assert decision.alternatives_rejected == "MongoDB (no transactions), SQLite (not scalable)"
        assert decision.adr_status == "Accepted"

    def test_empty_decision_log_returns_empty_list(self, tmp_path):
        """AC8: Handles missing decision log gracefully."""
        content = """# Feature Research: No Decisions

## Problem Statement
Valid problem statement without decisions.
"""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(content)

        result = parse_research_template(spec_file)
        assert result.decisions == []
        assert any("decision" in w.lower() for w in result.parse_warnings)


class TestImplementationTasksParsing:
    """Test parsing of Implementation Tasks section into TaskDefinition objects."""

    def test_parses_single_task(self, tmp_path, minimal_spec_content):
        """AC3: Parses single task definition."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(minimal_spec_content)

        result = parse_research_template(spec_file)
        assert len(result.tasks) == 1
        assert result.tasks[0].name == "TASK 1: Basic Implementation"

    def test_parses_multiple_tasks(self, tmp_path, full_spec_content):
        """AC3: Parses multiple task definitions."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        assert len(result.tasks) == 2
        assert result.tasks[0].name == "TASK 1: Core Parser Implementation"
        assert result.tasks[1].name == "TASK 2: Data Model Definitions"

    def test_task_complexity_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses task complexity with score and level."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]
        task2 = result.tasks[1]

        assert task1.complexity == "medium"
        assert task1.complexity_score == 5
        assert task2.complexity == "low"
        assert task2.complexity_score == 2

    def test_task_type_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses task type."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        assert all(task.task_type == "implementation" for task in result.tasks)

    def test_task_domain_tags_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses domain tags as list."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]

        assert isinstance(task1.domain_tags, list)
        assert "core" in task1.domain_tags
        assert "parsing" in task1.domain_tags
        assert "planning" in task1.domain_tags

    def test_task_files_to_create_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses files to create as list."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]

        assert isinstance(task1.files_to_create, list)
        assert "guardkit/planning/spec_parser.py" in task1.files_to_create
        assert "tests/unit/test_spec_parser.py" in task1.files_to_create

    def test_task_files_to_modify_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses files to modify as list."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]

        assert isinstance(task1.files_to_modify, list)
        assert "guardkit/planning/__init__.py" in task1.files_to_modify

    def test_task_files_not_to_touch_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses files NOT to touch as list."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]

        assert isinstance(task1.files_not_to_touch, list)
        assert "guardkit/core/config.py" in task1.files_not_to_touch
        assert "guardkit/cli/main.py" in task1.files_not_to_touch

    def test_task_dependencies_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses task dependencies."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]
        task2 = result.tasks[1]

        assert isinstance(task1.dependencies, list)
        assert "TASK 2" in task1.dependencies
        assert task2.dependencies == [] or task2.dependencies == ["None"]

    def test_task_inputs_outputs_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses task inputs and outputs."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]

        assert isinstance(task1.inputs, str)
        assert "Path to research template" in task1.inputs
        assert isinstance(task1.outputs, str)
        assert "ParsedSpec object" in task1.outputs

    def test_task_relevant_decisions_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses relevant decisions as list."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]

        assert isinstance(task1.relevant_decisions, list)
        assert "D1" in task1.relevant_decisions
        assert "D2" in task1.relevant_decisions

    def test_task_acceptance_criteria_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses acceptance criteria as list."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]

        assert isinstance(task1.acceptance_criteria, list)
        assert len(task1.acceptance_criteria) == 4
        assert "Parser function exists and is importable" in task1.acceptance_criteria

    def test_task_implementation_notes_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses implementation notes as string."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]

        assert isinstance(task1.implementation_notes, str)
        assert "regex" in task1.implementation_notes.lower()

    def test_task_player_constraints_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses player constraints as list."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]

        assert isinstance(task1.player_constraints, list)
        assert len(task1.player_constraints) == 2
        assert any("CLI" in c for c in task1.player_constraints)

    def test_task_coach_validation_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses coach validation commands as list."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]

        assert isinstance(task1.coach_validation_commands, list)
        assert len(task1.coach_validation_commands) == 2
        assert any("pytest" in c for c in task1.coach_validation_commands)

    def test_task_turn_budget_parsing(self, tmp_path, full_spec_content):
        """AC3: Parses turn budget with expected and max values."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        task1 = result.tasks[0]
        task2 = result.tasks[1]

        assert task1.turn_budget_expected == 3
        assert task1.turn_budget_max == 6
        assert task2.turn_budget_expected == 1
        assert task2.turn_budget_max == 2


class TestWarningsAndConstraintsParsing:
    """Test parsing of Warnings & Constraints section."""

    def test_parses_warnings_list(self, tmp_path, minimal_spec_content):
        """AC4: Parses warnings into list of strings."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(minimal_spec_content)

        result = parse_research_template(spec_file)
        assert isinstance(result.warnings, list)
        assert len(result.warnings) == 2
        assert "API rate limits apply" in result.warnings[0]
        assert "Requires authentication" in result.warnings[1]

    def test_parses_multiple_warnings(self, tmp_path, full_spec_content):
        """AC4: Parses multiple warnings correctly."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        assert len(result.warnings) == 3
        assert any("rate limits" in w for w in result.warnings)
        assert any("authentication" in w for w in result.warnings)
        assert any("migrations" in w for w in result.warnings)

    def test_empty_warnings_returns_empty_list(self, tmp_path):
        """AC8: Handles missing warnings section gracefully."""
        content = """# Feature Research: No Warnings

## Problem Statement
Valid problem statement.
"""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(content)

        result = parse_research_template(spec_file)
        assert result.warnings == []


class TestProblemStatementParsing:
    """Test parsing of Problem Statement section."""

    def test_parses_simple_problem_statement(self, tmp_path, minimal_spec_content):
        """AC5: Parses single paragraph problem statement."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(minimal_spec_content)

        result = parse_research_template(spec_file)
        assert isinstance(result.problem_statement, str)
        assert "minimal problem statement" in result.problem_statement

    def test_parses_multiline_problem_statement(self, tmp_path, full_spec_content):
        """AC5: Parses multi-paragraph problem statement."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        assert isinstance(result.problem_statement, str)
        assert "comprehensive problem statement" in result.problem_statement
        assert "detailed context" in result.problem_statement

    def test_missing_problem_statement_generates_warning(self, tmp_path):
        """AC8: Missing problem statement generates parse warning."""
        content = """# Feature Research: No Problem

## Decision Log

| # | Decision | Rationale | Alternatives Rejected | Status |
|---|----------|-----------|----------------------|---------|
| D1 | Test | Test | Test | Accepted |
"""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(content)

        result = parse_research_template(spec_file)
        assert any("problem statement" in w.lower() for w in result.parse_warnings)


class TestOutOfScopeParsing:
    """Test parsing of Out of Scope section."""

    def test_parses_out_of_scope_items(self, tmp_path, full_spec_content):
        """AC6: Parses out of scope items into list."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        assert isinstance(result.out_of_scope, list)
        assert len(result.out_of_scope) == 3
        assert any("Real-time notifications" in item for item in result.out_of_scope)
        assert any("Multi-language support" in item for item in result.out_of_scope)
        assert any("analytics dashboard" in item for item in result.out_of_scope)

    def test_empty_out_of_scope_returns_empty_list(self, tmp_path, minimal_spec_content):
        """AC8: Handles missing out of scope section gracefully."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(minimal_spec_content)

        result = parse_research_template(spec_file)
        assert result.out_of_scope == []


class TestOpenQuestionsParsing:
    """Test parsing of Open Questions section."""

    def test_parses_resolved_questions(self, tmp_path, full_spec_content):
        """AC7: Parses open questions with resolutions."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        assert isinstance(result.resolved_questions, list)
        assert len(result.resolved_questions) == 2

    def test_resolved_question_fields(self, tmp_path, full_spec_content):
        """AC7: ResolvedQuestion has question and resolution fields."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        q1 = result.resolved_questions[0]
        q2 = result.resolved_questions[1]

        assert q1.question == "Should we use async or sync API?"
        assert q1.resolution == "Use async for better performance under load."
        assert q2.question == "What timeout value is appropriate?"
        assert q2.resolution == "30 seconds for production, 5 seconds for development."

    def test_empty_questions_returns_empty_list(self, tmp_path, minimal_spec_content):
        """AC8: Handles missing questions section gracefully."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(minimal_spec_content)

        result = parse_research_template(spec_file)
        assert result.resolved_questions == []


class TestErrorHandling:
    """Test graceful handling of missing or malformed sections."""

    def test_missing_sections_generate_warnings_not_exceptions(self, tmp_path):
        """AC8: Missing sections return warnings, not exceptions."""
        content = """# Feature Research: Incomplete

## Problem Statement
This is the only section present.
"""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(content)

        # Should not raise exception
        result = parse_research_template(spec_file)

        # Should have parse warnings
        assert len(result.parse_warnings) > 0

    def test_malformed_decision_table_generates_warning(self, tmp_path, malformed_spec_content):
        """AC8: Malformed decision table generates parse warning."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(malformed_spec_content)

        result = parse_research_template(spec_file)
        assert any("decision" in w.lower() for w in result.parse_warnings)

    def test_incomplete_task_generates_warning(self, tmp_path, malformed_spec_content):
        """AC8: Incomplete task definition generates parse warning."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(malformed_spec_content)

        result = parse_research_template(spec_file)
        assert any("task" in w.lower() for w in result.parse_warnings)

    def test_nonexistent_file_raises_error(self):
        """Parser raises appropriate error for nonexistent file."""
        with pytest.raises((FileNotFoundError, IOError)):
            parse_research_template(Path("/nonexistent/file.md"))


class TestOptionalSections:
    """Test parsing of optional sections like Components, Test Strategy, etc."""

    def test_parses_components_section(self, tmp_path, full_spec_content):
        """Parses Components table into list of Component objects."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        assert isinstance(result.components, list)
        assert len(result.components) == 3

        comp = result.components[0]
        assert comp.name == "SpecParser"
        assert comp.file_path == "guardkit/planning/spec_parser.py"
        assert comp.purpose == "Parse research templates"
        assert comp.new_or_modified == "New"

    def test_parses_data_flow_section(self, tmp_path, full_spec_content):
        """Parses Data Flow section into string."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        assert isinstance(result.data_flow, str)
        assert "Input: Research Template" in result.data_flow
        assert "Output: ParsedSpec object" in result.data_flow

    def test_parses_test_strategy_section(self, tmp_path, full_spec_content):
        """Parses Test Strategy into TestStrategy object."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        assert result.test_strategy is not None
        assert isinstance(result.test_strategy.unit_tests, list)
        assert isinstance(result.test_strategy.integration_tests, list)
        assert isinstance(result.test_strategy.manual_verification, list)
        assert len(result.test_strategy.unit_tests) == 2
        assert len(result.test_strategy.integration_tests) == 1
        assert len(result.test_strategy.manual_verification) == 2

    def test_parses_dependencies_section(self, tmp_path, full_spec_content):
        """Parses Dependencies into DependencySet object."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        assert result.dependencies is not None
        assert isinstance(result.dependencies.python, list)
        assert "markdown>=3.4.0" in result.dependencies.python
        assert "pyyaml>=6.0" in result.dependencies.python
        assert isinstance(result.dependencies.environment, dict)
        assert "SPEC_TEMPLATE_PATH" in result.dependencies.environment

    def test_parses_api_contracts_section(self, tmp_path, full_spec_content):
        """Parses API Contracts into list of APIContract objects."""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(full_spec_content)

        result = parse_research_template(spec_file)
        assert isinstance(result.api_contracts, list)
        assert len(result.api_contracts) >= 1

        contract = result.api_contracts[0]
        assert contract.name == "parse_research_template"
        assert "def parse_research_template" in contract.content


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_file_generates_warnings(self, tmp_path):
        """Empty file generates appropriate warnings."""
        spec_file = tmp_path / "empty.md"
        spec_file.write_text("")

        result = parse_research_template(spec_file)
        assert len(result.parse_warnings) > 0

    def test_file_with_only_title(self, tmp_path):
        """File with only title generates warnings."""
        spec_file = tmp_path / "title_only.md"
        spec_file.write_text("# Feature Research: Title Only\n")

        result = parse_research_template(spec_file)
        assert len(result.parse_warnings) > 0

    @pytest.mark.parametrize("complexity_input,expected_level,expected_score", [
        ("low (1/10)", "low", 1),
        ("medium (5/10)", "medium", 5),
        ("high (9/10)", "high", 9),
        ("low (2/10)", "low", 2),
        ("high (10/10)", "high", 10),
    ])
    def test_complexity_parsing_variations(self, tmp_path, complexity_input, expected_level, expected_score):
        """Test various complexity format inputs."""
        content = f"""# Feature Research: Test

## Problem Statement
Test problem.

## Implementation Tasks

### TASK 1: Test Task
- **Complexity:** {complexity_input}
- **Type:** implementation
- **Domain Tags:** [test]
- **Files to Create:** []
- **Files to Modify:** []
- **Files NOT to Touch:** []
- **Dependencies:** None
- **Inputs:** Test
- **Outputs:** Test
- **Relevant Decisions:** None
- **Acceptance Criteria:**
  1. Test
- **Implementation Notes:** Test
- **Player Constraints:** []
- **Coach Validation:** []
- **Turn Budget:** 1 expected, 2 max
"""
        spec_file = tmp_path / "spec.md"
        spec_file.write_text(content)

        result = parse_research_template(spec_file)
        task = result.tasks[0]

        assert task.complexity == expected_level
        assert task.complexity_score == expected_score


class TestDataClassStructure:
    """Test that dataclasses are properly defined with correct types."""

    def test_decision_dataclass_fields(self):
        """Decision dataclass has required fields with correct types."""
        decision = Decision(
            number="D1",
            title="Test Decision",
            rationale="Test rationale",
            alternatives_rejected="Alt1, Alt2",
            adr_status="Accepted"
        )
        assert decision.number == "D1"
        assert decision.title == "Test Decision"

    def test_task_definition_dataclass_fields(self):
        """TaskDefinition dataclass has required fields with correct types."""
        task = TaskDefinition(
            name="Test Task",
            complexity="low",
            complexity_score=2,
            task_type="implementation",
            domain_tags=["test"],
            files_to_create=["file.py"],
            files_to_modify=[],
            files_not_to_touch=[],
            dependencies=[],
            inputs="Test input",
            outputs="Test output",
            relevant_decisions=["D1"],
            acceptance_criteria=["AC1"],
            implementation_notes="Notes",
            player_constraints=[],
            coach_validation_commands=["pytest"],
            turn_budget_expected=2,
            turn_budget_max=5
        )
        assert task.name == "Test Task"
        assert task.complexity_score == 2
        assert task.turn_budget_expected == 2

    def test_parsed_spec_dataclass_optional_fields(self):
        """ParsedSpec dataclass has correct optional fields."""
        spec = ParsedSpec(
            problem_statement="Test",
            decisions=[],
            warnings=[],
            components=[],
            data_flow="",
            message_schemas={},
            api_contracts=[],
            tasks=[]
        )
        # Optional fields should have defaults
        assert spec.test_strategy is None
        assert spec.dependencies is None
        assert spec.file_tree == ""
        assert spec.out_of_scope == []
        assert spec.resolved_questions == []
        assert spec.parse_warnings == []
