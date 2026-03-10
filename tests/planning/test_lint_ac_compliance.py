"""
Integration tests for lint compliance in feature plan acceptance criteria.

Verifies that:
1. Generated feature plans include lint compliance in implementation task ACs
2. No standalone quality gate verification tasks are present
3. quality_gate_generator continues to work correctly with tasks that have lint
   commands in their coach_validation_commands

Coverage Target: >=85%
"""

import pytest
from pathlib import Path

from guardkit.planning.spec_parser import parse_research_template, TaskDefinition
from guardkit.planning.quality_gate_generator import generate_quality_gates


# ---------------------------------------------------------------------------
# Test research spec with lint compliance ACs and no standalone QG tasks
# ---------------------------------------------------------------------------

LINT_COMPLIANT_SPEC = """\
# Research Spec: Lint Compliance Test Feature

## Problem Statement

A sample feature used to verify that lint compliance acceptance criteria
are present in implementation tasks and that no standalone quality gate
tasks exist.

## Decision Log

| # | Decision | Rationale | Alternatives Rejected | Status |
|---|----------|-----------|----------------------|---------|
| D1 | Use Python dataclasses | Type safety without external deps | Pydantic (too heavy) | Accepted |
| D2 | Regex-based parsing | Simple and dependency-free | markdown-it (overkill) | Accepted |

## Warnings & Constraints

- W1: Do not break existing API surface
- W2: All generated files must be deterministic

## Architecture

### Component Design

| Component | File Path | Purpose | Status |
|-----------|-----------|---------|--------|
| Parser | guardkit/planning/spec_parser.py | Parses research templates | Modified |

### Data Flow

```
research-spec.md -> parse_research_template() -> ParsedSpec
```

## API Contracts

### parse_research_template

```python
def parse_research_template(path: Path) -> ParsedSpec:
    ...
```

## Out of Scope

- Database integration
- Web UI components

## Open Questions

| Question | Resolution |
|----------|-----------|
| Format for output? | Use YAML for readability |

## Test Strategy

### Unit Tests

1. **Test:** parse with valid input
   **Expected:** Returns ParsedSpec

### Integration Tests

1. **Test:** Full pipeline
   **Expected:** All artifacts created

### Manual Verification

- Verify generated files are valid

## Dependencies

### Python Packages

- pyyaml>=6.0

### System Dependencies

- None required

### Environment Variables

- GUARDKIT_OUTPUT_DIR: Optional output directory override

## File Tree

```
guardkit/planning/
├── spec_parser.py
└── quality_gate_generator.py
```

## Implementation Tasks

### TASK 1: Implement Core Parser

- **Complexity:** medium (5/10)
- **Type:** implementation
- **Domain Tags:** [parsing, dataclasses]
- **Files to Create:** [guardkit/planning/spec_parser.py]
- **Files to Modify:** []
- **Files NOT to Touch:** [tests/unit/]
- **Dependencies:** None
- **Inputs:** Path to research template markdown file
- **Outputs:** ParsedSpec dataclass
- **Relevant Decisions:** D1, D2
- **Acceptance Criteria:**
  1. Parses Decision Log table into Decision objects
  2. Extracts warnings from Warnings section
  3. Returns ParsedSpec with all fields populated
  4. All modified files pass project-configured lint/format checks with zero errors
- **Implementation Notes:** Use regex-based parsing
- **Player Constraints:**
  - Do not add external markdown parsing libraries
- **Coach Validation:**
  - pytest tests/unit/planning/test_spec_parser.py -v
  - lint check guardkit/planning/spec_parser.py
- **Turn Budget:** 2 expected, 4 max

### TASK 2: Implement Quality Gate Generator

- **Complexity:** medium (4/10)
- **Type:** implementation
- **Domain Tags:** [quality-gates, yaml]
- **Files to Create:** [guardkit/planning/quality_gate_generator.py]
- **Files to Modify:** []
- **Files NOT to Touch:** [guardkit/planning/spec_parser.py]
- **Dependencies:** TASK 1
- **Inputs:** Feature ID, list of TaskDefinition objects
- **Outputs:** Path to generated quality gates YAML file
- **Relevant Decisions:** D2
- **Acceptance Criteria:**
  1. Extracts coach_validation_commands from all tasks
  2. Generates valid YAML with feature_id and gates
  3. Deduplicates identical commands
  4. All modified files pass project-configured lint/format checks with zero errors
- **Implementation Notes:** Use pyyaml for YAML generation
- **Player Constraints:**
  - Output must be valid YAML
- **Coach Validation:**
  - pytest tests/unit/planning/test_quality_gate_generator.py -v
  - lint check guardkit/planning/quality_gate_generator.py
- **Turn Budget:** 2 expected, 4 max
"""


SPEC_WITH_STANDALONE_QG_TASK = """\
# Research Spec: Spec With Standalone Quality Gate Task

## Problem Statement

A sample spec that contains a standalone quality gate verification task.
Used to verify that such tasks are detected and flagged.

## Decision Log

| # | Decision | Rationale | Alternatives Rejected | Status |
|---|----------|-----------|----------------------|---------|
| D1 | Use Python | General purpose | Ruby (unfamiliar) | Accepted |

## Warnings & Constraints

- W1: Keep backward compatibility

## Architecture

### Component Design

| Component | File Path | Purpose | Status |
|-----------|-----------|---------|--------|
| Worker | guardkit/worker.py | Core worker | New |

### Data Flow

```
input -> Worker -> output
```

## API Contracts

### worker_run

```python
def worker_run(data: dict) -> dict:
    ...
```

## Out of Scope

- Authentication

## Open Questions

| Question | Resolution |
|----------|-----------|
| Sync or async? | Sync for simplicity |

## Test Strategy

### Unit Tests

1. **Test:** worker processes data
   **Expected:** Returns result dict

### Integration Tests

1. **Test:** end-to-end worker flow
   **Expected:** Output correct

### Manual Verification

- Run worker, check output

## Dependencies

### Python Packages

- None required

### System Dependencies

- None required

### Environment Variables

- LOG_LEVEL: Log verbosity

## File Tree

```
guardkit/
└── worker.py
```

## Implementation Tasks

### TASK 1: Implement Worker

- **Complexity:** low (2/10)
- **Type:** implementation
- **Domain Tags:** [worker, core]
- **Files to Create:** [guardkit/worker.py]
- **Files to Modify:** []
- **Files NOT to Touch:** []
- **Dependencies:** None
- **Inputs:** Input dict
- **Outputs:** Result dict
- **Relevant Decisions:** D1
- **Acceptance Criteria:**
  1. Worker processes input and returns result
  2. Handles empty input gracefully
- **Implementation Notes:** Keep implementation simple
- **Player Constraints:**
  - Do not add unnecessary dependencies
- **Coach Validation:**
  - pytest tests/unit/test_worker.py -v
- **Turn Budget:** 1 expected, 3 max

### TASK 2: Verify Quality Gate Checks

- **Complexity:** low (1/10)
- **Type:** implementation
- **Domain Tags:** [quality-gates]
- **Files to Create:** []
- **Files to Modify:** []
- **Files NOT to Touch:** []
- **Dependencies:** TASK 1
- **Inputs:** Completed implementation from TASK 1
- **Outputs:** Passing lint and type checks
- **Relevant Decisions:** None
- **Acceptance Criteria:**
  1. ruff check passes with zero errors
  2. mypy reports no type errors
- **Implementation Notes:** Run quality gate commands
- **Player Constraints:**
  - Only run checks, do not modify code
- **Coach Validation:**
  - ruff check guardkit/
  - mypy guardkit/
- **Turn Budget:** 1 expected, 2 max
"""


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def lint_compliant_spec_file(tmp_path: Path) -> Path:
    """Write the lint-compliant spec to a temporary file."""
    spec_file = tmp_path / "lint-compliant-spec.md"
    spec_file.write_text(LINT_COMPLIANT_SPEC)
    return spec_file


@pytest.fixture
def standalone_qg_spec_file(tmp_path: Path) -> Path:
    """Write the spec containing a standalone quality gate task to a temp file."""
    spec_file = tmp_path / "standalone-qg-spec.md"
    spec_file.write_text(SPEC_WITH_STANDALONE_QG_TASK)
    return spec_file


def _has_lint_ac(task: TaskDefinition) -> bool:
    """Return True if any of the task's acceptance criteria mentions lint compliance."""
    for criterion in task.acceptance_criteria:
        if "lint" in criterion.lower():
            return True
    return False


def _is_standalone_qg_task(task: TaskDefinition) -> bool:
    """
    Return True if the task appears to be a standalone quality gate task.

    Detects tasks whose name contains quality gate / verify quality patterns
    AND whose purpose is purely to run verification checks (not to implement
    something). Tasks named "Implement Quality Gate Generator" are not
    standalone QG tasks — they produce production code.

    The distinguishing characteristic is presence of "verify", "run", or
    "check" keywords combined with quality gate terminology, without an
    "implement" or "generator" qualifier indicating real code is produced.
    """
    name_lower = task.name.lower()

    # Patterns that clearly indicate implementation work — never standalone QG tasks
    implementation_signals = ["implement", "generator", "create", "build", "add"]
    if any(signal in name_lower for signal in implementation_signals):
        return False

    # Patterns that indicate a verification-only task
    verification_patterns = [
        "verify quality gate",
        "run linting",
        "run lint",
        "type check only",
        "run type check",
        "format check",
        "quality gate verification",
        "quality gate check",
    ]
    return any(pattern in name_lower for pattern in verification_patterns)


# ---------------------------------------------------------------------------
# Tests: lint compliance in task ACs
# ---------------------------------------------------------------------------


class TestLintComplianceInACs:
    """Verify that parsed implementation tasks include lint compliance ACs."""

    def test_implementation_tasks_have_lint_ac(self, lint_compliant_spec_file: Path) -> None:
        """Each implementation task must include at least one lint-related AC."""
        parsed = parse_research_template(lint_compliant_spec_file)

        implementation_tasks = [
            t for t in parsed.tasks
            if t.task_type.lower() in ("implementation", "refactor", "feature")
        ]

        assert len(implementation_tasks) > 0, "Spec must contain at least one implementation task"

        for task in implementation_tasks:
            assert _has_lint_ac(task), (
                f"Task '{task.name}' has no lint compliance AC. "
                f"Acceptance criteria: {task.acceptance_criteria}"
            )

    def test_lint_ac_text_is_stack_agnostic(self, lint_compliant_spec_file: Path) -> None:
        """Lint compliance ACs must not reference specific tools like ruff or eslint."""
        parsed = parse_research_template(lint_compliant_spec_file)

        tool_specific_terms = ["ruff", "eslint", "biome", "pylint", "flake8", "prettier"]

        for task in parsed.tasks:
            for criterion in task.acceptance_criteria:
                if "lint" in criterion.lower():
                    for tool in tool_specific_terms:
                        assert tool not in criterion.lower(), (
                            f"Task '{task.name}' AC references specific tool '{tool}': "
                            f"'{criterion}'. Use 'project-configured lint/format checks' instead."
                        )

    def test_spec_has_expected_tasks(self, lint_compliant_spec_file: Path) -> None:
        """The compliant spec must parse exactly 2 tasks."""
        parsed = parse_research_template(lint_compliant_spec_file)
        assert len(parsed.tasks) == 2

    def test_all_tasks_have_acceptance_criteria(self, lint_compliant_spec_file: Path) -> None:
        """All tasks must have at least one acceptance criterion."""
        parsed = parse_research_template(lint_compliant_spec_file)
        for task in parsed.tasks:
            assert len(task.acceptance_criteria) > 0, (
                f"Task '{task.name}' has no acceptance criteria"
            )


# ---------------------------------------------------------------------------
# Tests: no standalone quality gate tasks
# ---------------------------------------------------------------------------


class TestNoStandaloneQualityGateTasks:
    """Verify detection of standalone quality gate tasks."""

    def test_compliant_spec_has_no_standalone_qg_tasks(
        self, lint_compliant_spec_file: Path
    ) -> None:
        """The compliant spec must not contain any standalone QG tasks."""
        parsed = parse_research_template(lint_compliant_spec_file)

        standalone_tasks = [t for t in parsed.tasks if _is_standalone_qg_task(t)]
        assert standalone_tasks == [], (
            f"Found standalone quality gate tasks in compliant spec: "
            f"{[t.name for t in standalone_tasks]}"
        )

    def test_standalone_qg_task_is_detected(self, standalone_qg_spec_file: Path) -> None:
        """The spec with a standalone QG task must parse and the task must be detectable."""
        parsed = parse_research_template(standalone_qg_spec_file)

        standalone_tasks = [t for t in parsed.tasks if _is_standalone_qg_task(t)]
        assert len(standalone_tasks) >= 1, (
            "Expected at least one standalone quality gate task to be detected "
            f"in the test spec. Tasks found: {[t.name for t in parsed.tasks]}"
        )

    def test_task_name_quality_gate_pattern_matches(self) -> None:
        """Verify the helper function correctly detects quality gate task names."""
        from guardkit.planning.spec_parser import TaskDefinition

        def make_task_with_name(name: str) -> TaskDefinition:
            return TaskDefinition(
                name=name,
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
                acceptance_criteria=[],
                implementation_notes="",
                player_constraints=[],
                coach_validation_commands=[],
            )

        assert _is_standalone_qg_task(make_task_with_name("Verify Quality Gate Checks"))
        assert _is_standalone_qg_task(make_task_with_name("Run Linting and Type Checks"))
        assert _is_standalone_qg_task(make_task_with_name("Quality Gate Verification"))
        assert not _is_standalone_qg_task(make_task_with_name("Implement Core Parser"))
        assert not _is_standalone_qg_task(make_task_with_name("Add Lint Compliance to API Module"))
        assert not _is_standalone_qg_task(make_task_with_name("Implement Quality Gate Generator"))


# ---------------------------------------------------------------------------
# Tests: quality_gate_generator still works correctly
# ---------------------------------------------------------------------------


class TestQualityGateGeneratorWithLintCommands:
    """
    Verify quality_gate_generator continues to work correctly when tasks
    include lint commands in their coach_validation_commands.
    """

    def test_generate_quality_gates_with_lint_commands(self, tmp_path: Path) -> None:
        """generate_quality_gates aggregates lint commands from task coach validation."""
        tasks = [
            TaskDefinition(
                name="Implement Core Parser",
                complexity="medium",
                complexity_score=5,
                task_type="implementation",
                domain_tags=["parsing"],
                files_to_create=["guardkit/planning/spec_parser.py"],
                files_to_modify=[],
                files_not_to_touch=[],
                dependencies=[],
                inputs="Markdown file path",
                outputs="ParsedSpec object",
                relevant_decisions=["D1"],
                acceptance_criteria=[
                    "Parses Decision Log table into Decision objects",
                    "All modified files pass project-configured lint/format checks with zero errors",
                ],
                implementation_notes="Use regex-based parsing",
                player_constraints=[],
                coach_validation_commands=[
                    "pytest tests/unit/planning/test_spec_parser.py -v",
                    "ruff check guardkit/planning/spec_parser.py",
                ],
            ),
            TaskDefinition(
                name="Implement Quality Gate Generator",
                complexity="medium",
                complexity_score=4,
                task_type="implementation",
                domain_tags=["quality-gates"],
                files_to_create=["guardkit/planning/quality_gate_generator.py"],
                files_to_modify=[],
                files_not_to_touch=[],
                dependencies=["TASK 1"],
                inputs="Feature ID and task list",
                outputs="YAML quality gates file",
                relevant_decisions=["D2"],
                acceptance_criteria=[
                    "Generates valid YAML with feature_id and gates",
                    "All modified files pass project-configured lint/format checks with zero errors",
                ],
                implementation_notes="Use pyyaml",
                player_constraints=[],
                coach_validation_commands=[
                    "pytest tests/unit/planning/test_quality_gate_generator.py -v",
                    "ruff check guardkit/planning/quality_gate_generator.py",
                ],
            ),
        ]

        output_path = tmp_path / "quality-gates.yaml"
        result_path = generate_quality_gates(
            feature_id="FEAT-LINT-TEST",
            tasks=tasks,
            output_path=output_path,
        )

        assert result_path == output_path
        assert output_path.exists()

    def test_quality_gates_yaml_contains_lint_gate(self, tmp_path: Path) -> None:
        """The generated YAML must contain a lint gate when lint commands are present."""
        import yaml

        task = TaskDefinition(
            name="Implement Feature",
            complexity="low",
            complexity_score=3,
            task_type="implementation",
            domain_tags=["feature"],
            files_to_create=["src/feature.py"],
            files_to_modify=[],
            files_not_to_touch=[],
            dependencies=[],
            inputs="Input data",
            outputs="Feature output",
            relevant_decisions=[],
            acceptance_criteria=[
                "Feature works correctly",
                "All modified files pass project-configured lint/format checks with zero errors",
            ],
            implementation_notes="",
            player_constraints=[],
            coach_validation_commands=[
                "pytest tests/test_feature.py -v",
                "ruff check src/feature.py",
            ],
        )

        output_path = tmp_path / "quality-gates-lint.yaml"
        generate_quality_gates(
            feature_id="FEAT-LINT-001",
            tasks=[task],
            output_path=output_path,
        )

        content = yaml.safe_load(output_path.read_text())
        assert content["feature_id"] == "FEAT-LINT-001"
        assert "quality_gates" in content
        assert "lint" in content["quality_gates"], (
            "Expected a 'lint' gate in generated YAML. "
            f"Got gates: {list(content['quality_gates'].keys())}"
        )

    def test_quality_gates_deduplicates_lint_commands(self, tmp_path: Path) -> None:
        """Identical lint commands from multiple tasks must be deduplicated."""
        import yaml

        shared_lint_command = "ruff check guardkit/"
        tasks = [
            TaskDefinition(
                name=f"Task {i}",
                complexity="low",
                complexity_score=2,
                task_type="implementation",
                domain_tags=[],
                files_to_create=[],
                files_to_modify=[],
                files_not_to_touch=[],
                dependencies=[],
                inputs="",
                outputs="",
                relevant_decisions=[],
                acceptance_criteria=[
                    "All modified files pass project-configured lint/format checks with zero errors",
                ],
                implementation_notes="",
                player_constraints=[],
                coach_validation_commands=[shared_lint_command],
            )
            for i in range(3)
        ]

        output_path = tmp_path / "quality-gates-dedup.yaml"
        generate_quality_gates(
            feature_id="FEAT-DEDUP-001",
            tasks=tasks,
            output_path=output_path,
        )

        content = yaml.safe_load(output_path.read_text())
        lint_command = content["quality_gates"]["lint"]["command"]
        # Command should not contain the same lint command three times
        assert lint_command.count(shared_lint_command) == 1, (
            f"Expected deduplicated lint command. Got: '{lint_command}'"
        )

    def test_quality_gate_generator_handles_empty_tasks(self, tmp_path: Path) -> None:
        """generate_quality_gates must handle an empty task list gracefully."""
        output_path = tmp_path / "quality-gates-empty.yaml"
        result_path = generate_quality_gates(
            feature_id="FEAT-EMPTY",
            tasks=[],
            output_path=output_path,
        )
        assert result_path == output_path
        assert output_path.exists()
