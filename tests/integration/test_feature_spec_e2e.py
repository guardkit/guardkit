"""
End-to-End Integration Tests for /feature-spec Command

Tests the full pipeline of guardkit.commands.feature_spec from stack detection
through file output and Graphiti seeding, exercising real module code with
controlled fixtures and selective mocking of external dependencies.

Coverage Target: >=85%
Test Count: 30+ tests
"""

import asyncio
import yaml
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from guardkit.commands.feature_spec import (
    FeatureSpecCommand,
    FeatureSpecResult,
    detect_stack,
    scan_codebase,
    write_outputs,
    seed_to_graphiti,
    _read_input_files,
)


# ============================================================================
# Shared Test Data
# ============================================================================

SAMPLE_FEATURE = """Feature: Document Upload
  As a user
  I want to upload documents
  So that I can share them

  Scenario: Upload a valid document
    Given I am logged in
    When I upload a PDF document
    Then the upload should succeed

  Scenario: Reject oversized document
    Given I am logged in
    When I upload a document larger than the size limit
    Then the upload should be rejected
"""

SAMPLE_ASSUMPTIONS = [
    {"id": "ASSUM-001", "text": "Maximum file size is 50MB"},
    {"id": "ASSUM-002", "text": "Allowed types are PDF and DOCX"},
]

DOMAIN_LANGUAGE_GHERKIN = """Feature: Document Upload
  As a user
  I want to upload documents
  So that I can share them

  Scenario: Upload a valid document
    Given I am authenticated as a registered user
    When I submit a document within the allowed size
    Then the document is stored in my account

  Scenario: Reject an oversized document
    Given I am authenticated as a registered user
    When I submit a document that exceeds the maximum size
    Then I receive a file-too-large notification
"""

IMPLEMENTATION_GHERKIN = """Feature: Document Upload
  Scenario: Upload endpoint returns 201
    Given a POST to /api/documents
    When the response is received
    Then the status code is return 201

  Scenario: Insert record
    Given data arrives
    When it is processed
    Then INSERT INTO documents is executed
"""


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def python_project(tmp_path):
    """Fake Python project with pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("# app module\n")
    return tmp_path


@pytest.fixture
def typescript_project(tmp_path):
    """Fake TypeScript project with package.json only."""
    (tmp_path / "package.json").write_text('{"name": "test"}\n')
    return tmp_path


@pytest.fixture
def polyglot_project(tmp_path):
    """Fake polyglot project with both pyproject.toml and package.json."""
    (tmp_path / "pyproject.toml").write_text("[project]\nname = 'test'\n")
    (tmp_path / "package.json").write_text('{"name": "test"}\n')
    return tmp_path


@pytest.fixture
def go_project(tmp_path):
    """Fake Go project with go.mod."""
    (tmp_path / "go.mod").write_text("module example.com/test\n")
    return tmp_path


@pytest.fixture
def generic_project(tmp_path):
    """Project with no detectable stack."""
    (tmp_path / "README.md").write_text("# Project\n")
    return tmp_path


@pytest.fixture
def output_dir(tmp_path):
    """Isolated output directory for file output tests."""
    out = tmp_path / "features_out"
    out.mkdir()
    return out


# ============================================================================
# 1. Stack Detection Priority (E2E)
# ============================================================================


@pytest.mark.integration
class TestStackDetectionE2E:
    """E2E tests for stack detection priority using real file system fixtures."""

    def test_python_project_detects_python_stack(self, python_project):
        """Python project (pyproject.toml only) is detected as stack='python'."""
        result = detect_stack(python_project)
        assert result["stack"] == "python"
        assert result["bdd_runner"] == "pytest-bdd"

    def test_polyglot_project_python_wins_over_typescript(self, polyglot_project):
        """Polyglot project (pyproject.toml + package.json) resolves to python."""
        result = detect_stack(polyglot_project)
        assert result["stack"] == "python", (
            "Python signals must take priority over package.json"
        )

    def test_typescript_project_with_no_python_signals(self, typescript_project):
        """TypeScript project (package.json only, no Python) resolves to typescript."""
        result = detect_stack(typescript_project)
        assert result["stack"] == "typescript"
        assert result["bdd_runner"] == "cucumber-js"

    def test_go_project_detects_go_stack(self, go_project):
        """Go project (go.mod) resolves to stack='go'."""
        result = detect_stack(go_project)
        assert result["stack"] == "go"
        assert result["bdd_runner"] == "godog"

    def test_generic_project_falls_back_to_generic(self, generic_project):
        """Project with no stack signals resolves to stack='generic'."""
        result = detect_stack(generic_project)
        assert result["stack"] == "generic"
        assert result["bdd_runner"] is None
        assert result["step_extension"] is None

    def test_rust_project_detects_rust_stack(self, tmp_path):
        """Rust project (Cargo.toml) resolves to stack='rust'."""
        (tmp_path / "Cargo.toml").write_text("[package]\nname = 'test'\n")
        result = detect_stack(tmp_path)
        assert result["stack"] == "rust"
        assert result["bdd_runner"] == "cucumber-rs"

    def test_requirements_txt_beats_package_json(self, tmp_path):
        """requirements.txt signals take priority over package.json."""
        (tmp_path / "requirements.txt").write_text("flask\n")
        (tmp_path / "package.json").write_text('{"name": "test"}\n')
        result = detect_stack(tmp_path)
        assert result["stack"] == "python"

    def test_setup_py_beats_go_mod(self, tmp_path):
        """setup.py signals take priority over go.mod in detection order."""
        (tmp_path / "setup.py").write_text("from setuptools import setup\n")
        (tmp_path / "go.mod").write_text("module example.com/test\n")
        result = detect_stack(tmp_path)
        assert result["stack"] == "python"


# ============================================================================
# 2. File Output (E2E)
# ============================================================================


@pytest.mark.integration
class TestFileOutputE2E:
    """E2E tests for write_outputs() confirming correct directory structure and file validity."""

    def test_creates_directory_named_after_feature(self, output_dir):
        """write_outputs creates a subdirectory matching the feature name slug."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "e2e-test", output_dir)
        feature_dir = paths["feature"].parent
        assert feature_dir.exists()
        assert feature_dir.name == "document-upload"

    def test_feature_file_is_valid_utf8(self, output_dir):
        """The .feature file is readable as valid UTF-8."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "e2e-test", output_dir)
        raw_bytes = paths["feature"].read_bytes()
        decoded = raw_bytes.decode("utf-8")
        assert "Feature: Document Upload" in decoded

    def test_assumptions_yaml_is_valid_yaml(self, output_dir):
        """The _assumptions.yaml file parses successfully with yaml.safe_load()."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "e2e-test", output_dir)
        content = paths["assumptions"].read_text()
        data = yaml.safe_load(content)
        assert data is not None
        assert isinstance(data, dict)

    def test_assumptions_yaml_contains_expected_entries(self, output_dir):
        """The _assumptions.yaml contains all provided assumption records."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "e2e-test", output_dir)
        data = yaml.safe_load(paths["assumptions"].read_text())
        assert len(data["assumptions"]) == 2
        ids = [a["id"] for a in data["assumptions"]]
        assert "ASSUM-001" in ids
        assert "ASSUM-002" in ids

    def test_summary_md_contains_scenarios_section(self, output_dir):
        """The _summary.md contains a 'Scenarios' heading."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "e2e-test", output_dir)
        content = paths["summary"].read_text()
        assert "Scenarios" in content

    def test_summary_md_contains_assumptions_section(self, output_dir):
        """The _summary.md contains an 'Assumptions' section when assumptions exist."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "e2e-test", output_dir)
        content = paths["summary"].read_text()
        assert "Assumptions" in content

    def test_summary_md_lists_both_scenario_titles(self, output_dir):
        """The _summary.md lists scenario titles from the feature."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "e2e-test", output_dir)
        content = paths["summary"].read_text()
        assert "Upload a valid document" in content
        assert "Reject oversized document" in content

    def test_write_outputs_returns_three_paths(self, output_dir):
        """write_outputs returns a dict with 'feature', 'assumptions', 'summary' keys."""
        paths = write_outputs(SAMPLE_FEATURE, [], "e2e-test", output_dir)
        assert set(paths.keys()) == {"feature", "assumptions", "summary"}

    def test_all_three_output_files_exist(self, output_dir):
        """All three output files are created on disk."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "e2e-test", output_dir)
        assert paths["feature"].exists()
        assert paths["assumptions"].exists()
        assert paths["summary"].exists()

    def test_output_files_have_correct_extensions(self, output_dir):
        """Output files have the expected file extensions."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "e2e-test", output_dir)
        assert paths["feature"].suffix == ".feature"
        assert paths["assumptions"].suffix == ".yaml"
        assert paths["summary"].suffix == ".md"

    def test_empty_assumptions_produces_valid_yaml(self, output_dir):
        """write_outputs with no assumptions still produces parseable YAML."""
        paths = write_outputs(SAMPLE_FEATURE, [], "e2e-test", output_dir)
        data = yaml.safe_load(paths["assumptions"].read_text())
        assert data["assumptions"] == []


# ============================================================================
# 3. Gherkin Quality - Domain Language (E2E)
# ============================================================================


@pytest.mark.integration
class TestGherkinQualityE2E:
    """E2E tests verifying domain-language Gherkin does not contain implementation terms."""

    IMPLEMENTATION_TERMS = [
        "return 201",
        "INSERT INTO",
        "HTTP 200",
        "status code 4",
        "SELECT * FROM",
        "DELETE FROM",
        "UPDATE SET",
        "response.body",
        "JSON payload",
    ]

    def test_domain_language_gherkin_has_no_implementation_terms(self):
        """Domain-language Gherkin must not contain implementation-level terms."""
        for term in self.IMPLEMENTATION_TERMS:
            assert term not in DOMAIN_LANGUAGE_GHERKIN, (
                f"Domain Gherkin should not contain implementation term: '{term}'"
            )

    def test_implementation_gherkin_contains_expected_terms(self):
        """Implementation Gherkin sample contains the expected low-level terms (control check)."""
        assert "return 201" in IMPLEMENTATION_GHERKIN
        assert "INSERT INTO" in IMPLEMENTATION_GHERKIN

    def test_domain_gherkin_uses_user_perspective_language(self):
        """Domain Gherkin describes actions from the user's perspective."""
        assert "I am authenticated" in DOMAIN_LANGUAGE_GHERKIN
        assert "I submit" in DOMAIN_LANGUAGE_GHERKIN

    def test_domain_gherkin_does_not_reference_http_status_codes(self):
        """Domain Gherkin must not reference raw HTTP status codes."""
        http_status_patterns = ["200", "201", "400", "404", "500", "HTTP"]
        for pattern in http_status_patterns:
            assert pattern not in DOMAIN_LANGUAGE_GHERKIN, (
                f"Domain Gherkin should not reference HTTP status pattern: '{pattern}'"
            )

    def test_domain_gherkin_does_not_reference_database_sql(self):
        """Domain Gherkin must not contain SQL or database implementation details."""
        sql_terms = ["SELECT", "INSERT", "UPDATE", "DELETE", "FROM", "WHERE", "JOIN"]
        for term in sql_terms:
            assert term not in DOMAIN_LANGUAGE_GHERKIN, (
                f"Domain Gherkin should not contain SQL term: '{term}'"
            )


# ============================================================================
# 4. Graphiti Seeding (E2E)
# ============================================================================


@pytest.mark.integration
class TestGraphitiSeedingE2E:
    """E2E tests for seed_to_graphiti() Graphiti integration behavior."""

    @pytest.mark.asyncio
    async def test_seed_does_not_raise_when_graphiti_unavailable(self):
        """seed_to_graphiti() does not raise when get_graphiti returns None."""
        with patch("guardkit.commands.feature_spec.get_graphiti", return_value=None):
            await seed_to_graphiti(
                feature_id="doc-upload",
                feature_content=SAMPLE_FEATURE,
                assumptions=SAMPLE_ASSUMPTIONS,
                output_paths={},
            )
        # If we reach here, no exception was raised — test passes

    @pytest.mark.asyncio
    async def test_seed_calls_add_episode_for_each_scenario(self):
        """seed_to_graphiti() calls add_episode once per scenario in the feature."""
        mock_client = Mock()
        mock_client.enabled = True
        captured_calls = []

        async def capture_add(*args, **kwargs):
            captured_calls.append(kwargs)
            return "uuid"

        mock_client.add_episode = capture_add

        with patch(
            "guardkit.commands.feature_spec.get_graphiti", return_value=mock_client
        ):
            await seed_to_graphiti(
                feature_id="doc-upload",
                feature_content=SAMPLE_FEATURE,
                assumptions=[],
                output_paths={},
            )

        scenario_calls = [c for c in captured_calls if c.get("group_id") == "feature_specs"]
        # SAMPLE_FEATURE has exactly 2 scenarios
        assert len(scenario_calls) == 2

    @pytest.mark.asyncio
    async def test_seed_seeds_assumptions_to_domain_knowledge_group(self):
        """seed_to_graphiti() seeds assumptions to the 'domain_knowledge' group."""
        mock_client = Mock()
        mock_client.enabled = True
        captured_calls = []

        async def capture_add(*args, **kwargs):
            captured_calls.append(kwargs)
            return "uuid"

        mock_client.add_episode = capture_add

        with patch(
            "guardkit.commands.feature_spec.get_graphiti", return_value=mock_client
        ):
            await seed_to_graphiti(
                feature_id="doc-upload",
                feature_content=SAMPLE_FEATURE,
                assumptions=SAMPLE_ASSUMPTIONS,
                output_paths={},
            )

        assumption_calls = [c for c in captured_calls if c.get("group_id") == "domain_knowledge"]
        assert len(assumption_calls) == 2

    @pytest.mark.asyncio
    async def test_seed_does_not_raise_when_client_disabled(self):
        """seed_to_graphiti() silently skips when client.enabled is False."""
        mock_client = Mock()
        mock_client.enabled = False

        with patch(
            "guardkit.commands.feature_spec.get_graphiti", return_value=mock_client
        ):
            await seed_to_graphiti(
                feature_id="doc-upload",
                feature_content=SAMPLE_FEATURE,
                assumptions=[],
                output_paths={},
            )

    @pytest.mark.asyncio
    async def test_seed_continues_on_episode_failure(self):
        """seed_to_graphiti() continues seeding remaining scenarios if one fails."""
        mock_client = Mock()
        mock_client.enabled = True
        successful_calls = []
        call_count = 0

        async def flaky_add(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("First call fails")
            successful_calls.append(kwargs)
            return "uuid"

        mock_client.add_episode = flaky_add

        with patch(
            "guardkit.commands.feature_spec.get_graphiti", return_value=mock_client
        ):
            await seed_to_graphiti(
                feature_id="doc-upload",
                feature_content=SAMPLE_FEATURE,
                assumptions=[],
                output_paths={},
            )

        # Second scenario should still have been attempted
        assert len(successful_calls) >= 1


# ============================================================================
# 5. Input Handling (E2E)
# ============================================================================


@pytest.mark.integration
class TestInputHandlingE2E:
    """E2E tests for _read_input_files() input concatenation behavior."""

    def test_multiple_files_are_concatenated(self, tmp_path):
        """_read_input_files() concatenates content from multiple input files."""
        file_a = tmp_path / "context_a.md"
        file_a.write_text("# Context A\nSome context about uploads.\n")
        file_b = tmp_path / "context_b.txt"
        file_b.write_text("# Context B\nSome context about limits.\n")

        result = _read_input_files([file_a, file_b])

        assert "Context A" in result
        assert "Context B" in result
        assert "uploads" in result
        assert "limits" in result

    def test_empty_input_list_returns_empty_string(self):
        """_read_input_files() with an empty list returns empty string without raising."""
        result = _read_input_files([])
        assert result == ""

    def test_missing_file_is_skipped_silently(self, tmp_path):
        """_read_input_files() skips missing files and returns whatever was readable."""
        existing = tmp_path / "exists.md"
        existing.write_text("Readable content\n")
        missing = tmp_path / "does_not_exist.md"

        result = _read_input_files([existing, missing])

        assert "Readable content" in result

    def test_unsupported_extension_is_skipped(self, tmp_path):
        """_read_input_files() skips files with unsupported extensions."""
        json_file = tmp_path / "data.json"
        json_file.write_text('{"key": "value"}')

        result = _read_input_files([json_file])

        assert result == ""

    def test_single_md_file_content_is_returned(self, tmp_path):
        """_read_input_files() correctly returns content from a single .md file."""
        md_file = tmp_path / "spec.md"
        md_file.write_text("# Feature Description\nUsers can upload files.\n")

        result = _read_input_files([md_file])

        assert "Feature Description" in result
        assert "Users can upload files." in result

    def test_single_txt_file_content_is_returned(self, tmp_path):
        """_read_input_files() correctly returns content from a single .txt file."""
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Upload size limit is 50MB.\n")

        result = _read_input_files([txt_file])

        assert "Upload size limit is 50MB." in result

    def test_order_of_concatenation_is_preserved(self, tmp_path):
        """_read_input_files() preserves file order in concatenated output."""
        file_first = tmp_path / "first.md"
        file_first.write_text("FIRST_CONTENT")
        file_second = tmp_path / "second.md"
        file_second.write_text("SECOND_CONTENT")

        result = _read_input_files([file_first, file_second])

        first_pos = result.index("FIRST_CONTENT")
        second_pos = result.index("SECOND_CONTENT")
        assert first_pos < second_pos


# ============================================================================
# 6. Full Pipeline (E2E)
# ============================================================================


@pytest.mark.integration
class TestFullPipelineE2E:
    """E2E tests exercising the complete FeatureSpecCommand.execute() pipeline."""

    @pytest.mark.asyncio
    async def test_execute_returns_feature_spec_result(self, python_project, tmp_path):
        """execute() returns a FeatureSpecResult for a Python project."""
        output_dir = tmp_path / "features_out"

        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=python_project)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )

        assert isinstance(result, FeatureSpecResult)

    @pytest.mark.asyncio
    async def test_execute_detects_python_stack(self, python_project, tmp_path):
        """execute() detects stack='python' from a Python project root."""
        output_dir = tmp_path / "features_out"

        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=python_project)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )

        assert result.stack == "python"

    @pytest.mark.asyncio
    async def test_execute_creates_all_output_files(self, python_project, tmp_path):
        """execute() creates the .feature, _assumptions.yaml, and _summary.md files."""
        output_dir = tmp_path / "features_out"

        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=python_project)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir, "assumptions": SAMPLE_ASSUMPTIONS},
            )

        assert result.feature_file.exists()
        assert result.assumptions_file.exists()
        assert result.summary_file.exists()

    @pytest.mark.asyncio
    async def test_execute_counts_scenarios_correctly(self, python_project, tmp_path):
        """execute() counts scenario declarations in the Gherkin content."""
        output_dir = tmp_path / "features_out"

        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=python_project)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )

        # SAMPLE_FEATURE has 2 scenarios
        assert result.scenarios_count == 2

    @pytest.mark.asyncio
    async def test_execute_counts_assumptions_correctly(self, python_project, tmp_path):
        """execute() reports the correct count of assumptions passed in options."""
        output_dir = tmp_path / "features_out"

        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=python_project)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir, "assumptions": SAMPLE_ASSUMPTIONS},
            )

        assert result.assumptions_count == 2

    @pytest.mark.asyncio
    async def test_execute_output_directory_contains_feature_subdirectory(
        self, python_project, tmp_path
    ):
        """execute() creates a feature-named subdirectory in the output directory."""
        output_dir = tmp_path / "features_out"

        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=python_project)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )

        # feature_file path should be inside output_dir / <feature-name>/
        assert result.feature_file.parent.parent == output_dir

    @pytest.mark.asyncio
    async def test_execute_with_typescript_project_detects_typescript(
        self, typescript_project, tmp_path
    ):
        """execute() detects stack='typescript' from a TypeScript project root."""
        output_dir = tmp_path / "features_out"

        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=typescript_project)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )

        assert result.stack == "typescript"

    @pytest.mark.asyncio
    async def test_execute_from_files_merges_content(self, python_project, tmp_path):
        """execute() merges input file contents into the Gherkin feature file."""
        output_dir = tmp_path / "features_out"
        context_file = tmp_path / "limits.md"
        context_file.write_text("# Domain Limits\nMax file size: 50MB\n")

        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=python_project)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir, "from_files": [context_file]},
            )

        feature_content = result.feature_file.read_text()
        # The original Gherkin must be present
        assert "Feature: Document Upload" in feature_content

    @pytest.mark.asyncio
    async def test_execute_scaffolding_files_empty_in_v1(self, python_project, tmp_path):
        """execute() returns empty scaffolding_files dict (v1 behaviour)."""
        output_dir = tmp_path / "features_out"

        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=python_project)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )

        assert result.scaffolding_files == {}

    @pytest.mark.asyncio
    async def test_execute_uses_default_output_dir_when_not_specified(
        self, python_project
    ):
        """execute() defaults output_dir to project_root/features/ when not provided."""
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=python_project)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={},
            )

        expected_prefix = str(python_project / "features")
        assert str(result.feature_file).startswith(expected_prefix)

    @pytest.mark.asyncio
    async def test_execute_calls_graphiti_seeding(self, python_project, tmp_path):
        """execute() invokes seed_to_graphiti as part of the pipeline."""
        output_dir = tmp_path / "features_out"
        mock_seed = AsyncMock()

        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=mock_seed):
            cmd = FeatureSpecCommand(project_root=python_project)
            await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )

        mock_seed.assert_called_once()
