"""
Test Suite for Feature Spec Command Module

Tests stack detection, codebase scanning, file output, Graphiti seeding,
and FeatureSpecCommand orchestration.

Coverage Target: >=85%
Test Count: 30+ tests
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
import yaml

from guardkit.commands.feature_spec import (
    SUPPORTED_EXTENSIONS,
    FeatureSpecCommand,
    FeatureSpecResult,
    _count_scenarios,
    _extract_feature_name,
    _parse_scenarios,
    _read_input_files,
    detect_stack,
    scan_codebase,
    seed_to_graphiti,
    write_outputs,
)


# ============================================================================
# Fixtures
# ============================================================================


SAMPLE_FEATURE = """Feature: User Authentication
  As a user
  I want to log in
  So that I can access my account

  Scenario: Successful login
    Given a registered user
    When the user submits valid credentials
    Then the user is authenticated

  Scenario: Failed login with wrong password
    Given a registered user
    When the user submits wrong password
    Then an error message is displayed
"""

SAMPLE_ASSUMPTIONS = [
    {"id": "A1", "text": "Users have unique email addresses"},
    {"id": "A2", "text": "Passwords are hashed with bcrypt"},
]


@pytest.fixture
def project_root(tmp_path):
    """Create temporary project root directory."""
    root = tmp_path / "project"
    root.mkdir()
    return root


@pytest.fixture
def python_project(project_root):
    """Create a Python project (pyproject.toml present)."""
    (project_root / "pyproject.toml").write_text("[build-system]\n")
    return project_root


@pytest.fixture
def ts_project(project_root):
    """Create a TypeScript project (package.json only)."""
    (project_root / "package.json").write_text("{}\n")
    return project_root


@pytest.fixture
def go_project(project_root):
    """Create a Go project (go.mod present)."""
    (project_root / "go.mod").write_text("module example.com/app\n")
    return project_root


@pytest.fixture
def rust_project(project_root):
    """Create a Rust project (Cargo.toml present)."""
    (project_root / "Cargo.toml").write_text("[package]\nname = \"app\"\n")
    return project_root


@pytest.fixture
def output_dir(tmp_path):
    """Provide a temp output directory."""
    out = tmp_path / "features_out"
    out.mkdir()
    return out


# ============================================================================
# 1. detect_stack() Tests
# ============================================================================


class TestDetectStack:
    """Tests for detect_stack() priority-based detection."""

    def test_detects_python_from_pyproject_toml(self, python_project):
        """pyproject.toml -> Python stack."""
        result = detect_stack(python_project)
        assert result["stack"] == "python"
        assert result["bdd_runner"] == "pytest-bdd"
        assert result["step_extension"] == ".py"

    def test_detects_python_from_requirements_txt(self, project_root):
        """requirements.txt -> Python stack."""
        (project_root / "requirements.txt").write_text("flask\n")
        result = detect_stack(project_root)
        assert result["stack"] == "python"
        assert result["bdd_runner"] == "pytest-bdd"

    def test_detects_python_from_setup_py(self, project_root):
        """setup.py -> Python stack."""
        (project_root / "setup.py").write_text("from setuptools import setup\n")
        result = detect_stack(project_root)
        assert result["stack"] == "python"
        assert result["step_extension"] == ".py"

    def test_detects_go_from_go_mod(self, go_project):
        """go.mod -> Go stack."""
        result = detect_stack(go_project)
        assert result["stack"] == "go"
        assert result["bdd_runner"] == "godog"
        assert result["step_extension"] == ".go"

    def test_detects_rust_from_cargo_toml(self, rust_project):
        """Cargo.toml -> Rust stack."""
        result = detect_stack(rust_project)
        assert result["stack"] == "rust"
        assert result["bdd_runner"] == "cucumber-rs"
        assert result["step_extension"] == ".rs"

    def test_detects_typescript_from_package_json(self, ts_project):
        """package.json only -> TypeScript stack."""
        result = detect_stack(ts_project)
        assert result["stack"] == "typescript"
        assert result["bdd_runner"] == "cucumber-js"
        assert result["step_extension"] == ".ts"

    def test_generic_when_no_signals(self, project_root):
        """No signals -> generic stack."""
        result = detect_stack(project_root)
        assert result["stack"] == "generic"
        assert result["bdd_runner"] is None
        assert result["step_extension"] is None

    def test_python_priority_over_typescript(self, project_root):
        """Python signals take priority over package.json."""
        # Both pyproject.toml and package.json exist
        (project_root / "pyproject.toml").write_text("[build-system]\n")
        (project_root / "package.json").write_text("{}\n")
        result = detect_stack(project_root)
        assert result["stack"] == "python"

    def test_requirements_txt_priority_over_package_json(self, project_root):
        """requirements.txt takes priority over package.json."""
        (project_root / "requirements.txt").write_text("flask\n")
        (project_root / "package.json").write_text("{}\n")
        result = detect_stack(project_root)
        assert result["stack"] == "python"

    def test_returns_dict_with_required_keys(self, project_root):
        """detect_stack always returns a dict with stack, bdd_runner, step_extension."""
        result = detect_stack(project_root)
        assert "stack" in result
        assert "bdd_runner" in result
        assert "step_extension" in result


# ============================================================================
# 2. scan_codebase() Tests
# ============================================================================


class TestScanCodebase:
    """Tests for scan_codebase() context extraction."""

    def test_extracts_python_modules(self, project_root):
        """scan_codebase finds Python packages via __init__.py."""
        (project_root / "myapp").mkdir()
        (project_root / "myapp" / "__init__.py").write_text("")
        (project_root / "myapp" / "services").mkdir()
        (project_root / "myapp" / "services" / "__init__.py").write_text("")
        stack = {"stack": "python", "bdd_runner": "pytest-bdd", "step_extension": ".py"}

        result = scan_codebase(project_root, stack)

        assert "myapp" in result["modules"]
        assert "myapp.services" in result["modules"]

    def test_finds_existing_feature_files(self, project_root):
        """scan_codebase finds existing .feature files."""
        features_dir = project_root / "features"
        features_dir.mkdir()
        (features_dir / "login.feature").write_text("Feature: Login\n")
        (features_dir / "signup.feature").write_text("Feature: Signup\n")
        stack = {"stack": "generic", "bdd_runner": None, "step_extension": None}

        result = scan_codebase(project_root, stack)

        feature_names = [p.name for p in result["existing_features"]]
        assert "login.feature" in feature_names
        assert "signup.feature" in feature_names

    def test_detects_service_pattern(self, project_root):
        """scan_codebase detects 'services' pattern from file names."""
        (project_root / "user_service.py").write_text("")
        stack = {"stack": "python", "bdd_runner": "pytest-bdd", "step_extension": ".py"}

        result = scan_codebase(project_root, stack)

        assert "services" in result["patterns"]

    def test_detects_repository_pattern(self, project_root):
        """scan_codebase detects 'repositories' pattern from file names."""
        (project_root / "user_repository.py").write_text("")
        stack = {"stack": "python", "bdd_runner": "pytest-bdd", "step_extension": ".py"}

        result = scan_codebase(project_root, stack)

        assert "repositories" in result["patterns"]

    def test_detects_routes_pattern(self, project_root):
        """scan_codebase detects 'routes' pattern from file names."""
        (project_root / "api_routes.py").write_text("")
        stack = {"stack": "python", "bdd_runner": "pytest-bdd", "step_extension": ".py"}

        result = scan_codebase(project_root, stack)

        assert "routes" in result["patterns"]

    def test_returns_expected_keys(self, project_root):
        """scan_codebase returns dict with modules, existing_features, patterns."""
        stack = {"stack": "generic", "bdd_runner": None, "step_extension": None}
        result = scan_codebase(project_root, stack)
        assert "modules" in result
        assert "existing_features" in result
        assert "patterns" in result

    def test_empty_project_returns_empty_collections(self, project_root):
        """scan_codebase returns empty collections for an empty project."""
        stack = {"stack": "generic", "bdd_runner": None, "step_extension": None}
        result = scan_codebase(project_root, stack)
        assert result["modules"] == []
        assert result["existing_features"] == []
        assert result["patterns"] == []


# ============================================================================
# 3. Helper Function Tests
# ============================================================================


class TestExtractFeatureName:
    """Tests for _extract_feature_name()."""

    def test_extracts_feature_name_and_slugifies(self):
        """Extracts and kebab-cases the Feature: name."""
        content = "Feature: User Authentication\n  Scenario: Login\n"
        assert _extract_feature_name(content) == "user-authentication"

    def test_returns_unnamed_feature_when_no_feature_line(self):
        """Returns 'unnamed-feature' when no Feature: line present."""
        content = "Scenario: Some scenario\n  Given something\n"
        assert _extract_feature_name(content) == "unnamed-feature"

    def test_handles_special_characters(self):
        """Replaces special characters with hyphens."""
        content = "Feature: My Feature/Spec (2024)\n"
        result = _extract_feature_name(content)
        assert result == "my-feature-spec-2024"

    def test_handles_multiple_spaces(self):
        """Multiple spaces collapse to single hyphen."""
        content = "Feature:  Multi   Word  Name\n"
        result = _extract_feature_name(content)
        assert "-" in result
        assert result.islower()


class TestCountScenarios:
    """Tests for _count_scenarios()."""

    def test_counts_scenario_declarations(self):
        """Counts Scenario: lines correctly."""
        assert _count_scenarios(SAMPLE_FEATURE) == 2

    def test_counts_scenario_outline(self):
        """Counts Scenario Outline: lines."""
        content = "Feature: X\n  Scenario Outline: Test\n    Given <a>\n"
        assert _count_scenarios(content) == 1

    def test_zero_for_no_scenarios(self):
        """Returns 0 when no scenario declarations."""
        content = "Feature: Empty feature\n  Background:\n    Given setup\n"
        assert _count_scenarios(content) == 0

    def test_counts_mixed_scenario_types(self):
        """Counts both Scenario: and Scenario Outline: together."""
        content = (
            "Feature: X\n"
            "  Scenario: One\n    Given a\n"
            "  Scenario Outline: Two\n    Given <b>\n"
        )
        assert _count_scenarios(content) == 2


class TestParseScenarios:
    """Tests for _parse_scenarios()."""

    def test_returns_list_of_scenario_blocks(self):
        """Parses into correct number of scenario blocks."""
        scenarios = _parse_scenarios(SAMPLE_FEATURE)
        assert len(scenarios) == 2

    def test_each_block_starts_with_scenario_keyword(self):
        """Each parsed block starts with Scenario: or Scenario Outline:."""
        scenarios = _parse_scenarios(SAMPLE_FEATURE)
        for s in scenarios:
            stripped = s.strip().splitlines()[0].strip()
            assert stripped.startswith("Scenario:") or stripped.startswith("Scenario Outline:")

    def test_returns_empty_list_for_no_scenarios(self):
        """Returns [] when no scenarios present."""
        content = "Feature: Empty\n  Background:\n    Given setup\n"
        assert _parse_scenarios(content) == []

    def test_scenario_blocks_contain_steps(self):
        """Each block contains the steps belonging to that scenario."""
        scenarios = _parse_scenarios(SAMPLE_FEATURE)
        assert "valid credentials" in scenarios[0]
        assert "wrong password" in scenarios[1]


# ============================================================================
# 4. write_outputs() Tests
# ============================================================================


class TestWriteOutputs:
    """Tests for write_outputs() file creation."""

    def test_creates_feature_directory(self, output_dir):
        """write_outputs creates a subdirectory named after the feature."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "test", output_dir)
        feature_dir = paths["feature"].parent
        assert feature_dir.exists()
        assert feature_dir.is_dir()

    def test_creates_feature_file(self, output_dir):
        """write_outputs creates the .feature file."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "test", output_dir)
        assert paths["feature"].exists()
        assert paths["feature"].suffix == ".feature"

    def test_creates_assumptions_yaml(self, output_dir):
        """write_outputs creates the _assumptions.yaml file."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "test-source", output_dir)
        assert paths["assumptions"].exists()
        assert paths["assumptions"].suffix == ".yaml"

    def test_creates_summary_md(self, output_dir):
        """write_outputs creates the _summary.md file."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "test", output_dir)
        assert paths["summary"].exists()
        assert paths["summary"].suffix == ".md"

    def test_feature_file_contains_original_content(self, output_dir):
        """The .feature file contains the original Gherkin content."""
        paths = write_outputs(SAMPLE_FEATURE, [], "test", output_dir)
        content = paths["feature"].read_text()
        assert "Feature: User Authentication" in content

    def test_assumptions_yaml_contains_source(self, output_dir):
        """Assumptions YAML contains the source field."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "my-source", output_dir)
        data = yaml.safe_load(paths["assumptions"].read_text())
        assert data["source"] == "my-source"

    def test_assumptions_yaml_contains_assumptions(self, output_dir):
        """Assumptions YAML contains the assumption entries."""
        paths = write_outputs(SAMPLE_FEATURE, SAMPLE_ASSUMPTIONS, "test", output_dir)
        data = yaml.safe_load(paths["assumptions"].read_text())
        assert len(data["assumptions"]) == 2
        assert data["assumptions"][0]["id"] == "A1"

    def test_summary_md_contains_feature_name(self, output_dir):
        """Summary markdown contains the feature name."""
        paths = write_outputs(SAMPLE_FEATURE, [], "test", output_dir)
        content = paths["summary"].read_text()
        assert "user-authentication" in content

    def test_summary_md_contains_scenario_count(self, output_dir):
        """Summary markdown contains the scenario count."""
        paths = write_outputs(SAMPLE_FEATURE, [], "test", output_dir)
        content = paths["summary"].read_text()
        assert "2" in content  # two scenarios

    def test_returns_dict_with_three_paths(self, output_dir):
        """write_outputs returns dict with feature, assumptions, summary keys."""
        paths = write_outputs(SAMPLE_FEATURE, [], "test", output_dir)
        assert "feature" in paths
        assert "assumptions" in paths
        assert "summary" in paths

    def test_empty_assumptions_writes_valid_yaml(self, output_dir):
        """write_outputs handles empty assumptions without error."""
        paths = write_outputs(SAMPLE_FEATURE, [], "test", output_dir)
        data = yaml.safe_load(paths["assumptions"].read_text())
        assert data["assumptions"] == []

    def test_creates_parent_dirs_if_not_exist(self, tmp_path):
        """write_outputs creates nested output directories if they don't exist."""
        nested_output = tmp_path / "deep" / "nested" / "features"
        paths = write_outputs(SAMPLE_FEATURE, [], "test", nested_output)
        assert paths["feature"].exists()

    def test_summary_uses_provided_stack(self, output_dir):
        """write_outputs passes provided stack to summary generator."""
        stack = {"stack": "python", "bdd_runner": "pytest-bdd", "step_extension": ".py"}
        paths = write_outputs(SAMPLE_FEATURE, [], "test", output_dir, stack=stack)
        content = paths["summary"].read_text()
        assert "**Stack:** python" in content
        assert "**BDD Runner:** pytest-bdd" in content

    def test_summary_defaults_to_generic_when_no_stack(self, output_dir):
        """write_outputs defaults to generic stack when stack not provided."""
        paths = write_outputs(SAMPLE_FEATURE, [], "test", output_dir)
        content = paths["summary"].read_text()
        assert "**Stack:** generic" in content
        assert "**BDD Runner:** N/A" in content


# ============================================================================
# 5. seed_to_graphiti() Tests
# ============================================================================


class TestSeedToGraphiti:
    """Tests for seed_to_graphiti() non-blocking Graphiti seeding."""

    async def test_seeds_individual_scenarios_not_whole_file(self):
        """seed_to_graphiti seeds each scenario separately (not whole file)."""
        mock_client = Mock()
        mock_client.enabled = True
        call_args_list = []

        async def capture_add(*args, **kwargs):
            call_args_list.append(kwargs)
            return "uuid-123"

        mock_client.add_episode = capture_add

        with patch(
            "guardkit.commands.feature_spec.get_graphiti", return_value=mock_client
        ):
            await seed_to_graphiti(
                feature_id="auth-feature",
                feature_content=SAMPLE_FEATURE,
                assumptions=[],
                output_paths={},
            )

        # Two scenarios should produce two separate calls to add_episode
        scenario_calls = [c for c in call_args_list if c.get("group_id") == "feature_specs"]
        assert len(scenario_calls) == 2

    async def test_seeds_assumptions_to_domain_knowledge(self):
        """seed_to_graphiti seeds assumptions to domain_knowledge group."""
        mock_client = Mock()
        mock_client.enabled = True
        call_args_list = []

        async def capture_add(*args, **kwargs):
            call_args_list.append(kwargs)
            return "uuid-456"

        mock_client.add_episode = capture_add

        with patch(
            "guardkit.commands.feature_spec.get_graphiti", return_value=mock_client
        ):
            await seed_to_graphiti(
                feature_id="auth-feature",
                feature_content=SAMPLE_FEATURE,
                assumptions=SAMPLE_ASSUMPTIONS,
                output_paths={},
            )

        assumption_calls = [c for c in call_args_list if c.get("group_id") == "domain_knowledge"]
        assert len(assumption_calls) == 2

    async def test_non_blocking_when_graphiti_unavailable(self):
        """seed_to_graphiti completes without raising when Graphiti is None."""
        with patch("guardkit.commands.feature_spec.get_graphiti", return_value=None):
            # Should NOT raise
            await seed_to_graphiti(
                feature_id="test",
                feature_content=SAMPLE_FEATURE,
                assumptions=[],
                output_paths={},
            )

    async def test_non_blocking_when_graphiti_disabled(self):
        """seed_to_graphiti completes without raising when client.enabled is False."""
        mock_client = Mock()
        mock_client.enabled = False

        with patch(
            "guardkit.commands.feature_spec.get_graphiti", return_value=mock_client
        ):
            # Should NOT raise
            await seed_to_graphiti(
                feature_id="test",
                feature_content=SAMPLE_FEATURE,
                assumptions=[],
                output_paths={},
            )

    async def test_non_blocking_when_get_graphiti_is_none(self):
        """seed_to_graphiti completes without raising when get_graphiti module attr is None."""
        # Simulate the case where graphiti_client was not importable at module load
        import guardkit.commands.feature_spec as fs_module

        original = fs_module.get_graphiti
        try:
            fs_module.get_graphiti = None  # type: ignore[assignment]
            # Should not raise
            await seed_to_graphiti(
                feature_id="test",
                feature_content=SAMPLE_FEATURE,
                assumptions=[],
                output_paths={},
            )
        except Exception:
            pytest.fail("seed_to_graphiti raised an exception unexpectedly")
        finally:
            fs_module.get_graphiti = original

    async def test_continues_when_individual_episode_fails(self):
        """seed_to_graphiti continues seeding other scenarios if one fails."""
        mock_client = Mock()
        mock_client.enabled = True
        successful_calls = []

        call_count = 0

        async def flaky_add(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("First call fails")
            successful_calls.append(kwargs)
            return "uuid"

        mock_client.add_episode = flaky_add

        with patch(
            "guardkit.commands.feature_spec.get_graphiti", return_value=mock_client
        ):
            # Should not raise even if first episode fails
            await seed_to_graphiti(
                feature_id="auth-feature",
                feature_content=SAMPLE_FEATURE,
                assumptions=[],
                output_paths={},
            )

        # Second scenario should still have been seeded
        assert len(successful_calls) >= 1

    async def test_episode_body_contains_feature_id(self):
        """Each seeded episode body contains the feature_id."""
        mock_client = Mock()
        mock_client.enabled = True
        episode_bodies = []

        async def capture_add(*args, **kwargs):
            episode_bodies.append(kwargs.get("episode_body", ""))
            return "uuid"

        mock_client.add_episode = capture_add

        with patch(
            "guardkit.commands.feature_spec.get_graphiti", return_value=mock_client
        ):
            await seed_to_graphiti(
                feature_id="user-auth",
                feature_content=SAMPLE_FEATURE,
                assumptions=[],
                output_paths={},
            )

        for body in episode_bodies:
            parsed = json.loads(body)
            assert parsed.get("feature_id") == "user-auth"


# ============================================================================
# 6. _read_input_files() Tests
# ============================================================================


class TestReadInputFiles:
    """Tests for _read_input_files() file reading helper."""

    def test_reads_md_files(self, tmp_path):
        """Reads and returns content from .md files."""
        md_file = tmp_path / "notes.md"
        md_file.write_text("# Notes\nSome content")
        result = _read_input_files([md_file])
        assert "Some content" in result

    def test_reads_txt_files(self, tmp_path):
        """Reads and returns content from .txt files."""
        txt_file = tmp_path / "requirements.txt"
        txt_file.write_text("Feature requirement 1\n")
        result = _read_input_files([txt_file])
        assert "Feature requirement 1" in result

    def test_concatenates_multiple_files(self, tmp_path):
        """Concatenates content from multiple files with newline separator."""
        f1 = tmp_path / "a.md"
        f1.write_text("Content A")
        f2 = tmp_path / "b.txt"
        f2.write_text("Content B")
        result = _read_input_files([f1, f2])
        assert "Content A" in result
        assert "Content B" in result

    def test_skips_missing_files_with_warning(self, tmp_path, caplog):
        """Skips non-existent files and logs a warning."""
        missing = tmp_path / "does_not_exist.md"
        with caplog.at_level("WARNING"):
            result = _read_input_files([missing])
        assert result == ""
        assert any("not found" in msg.lower() for msg in caplog.messages)

    def test_skips_unsupported_extensions(self, tmp_path, caplog):
        """Skips files with unsupported extensions (.py, .csv, etc.)."""
        py_file = tmp_path / "script.py"
        py_file.write_text("print('hello')")
        with caplog.at_level("WARNING"):
            result = _read_input_files([py_file])
        assert result == ""

    def test_returns_empty_string_for_empty_list(self):
        """Returns empty string for empty file list."""
        result = _read_input_files([])
        assert result == ""

    def test_reads_yaml_files(self, tmp_path):
        """Reads and returns content from .yaml files."""
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text("key: value\n")
        result = _read_input_files([yaml_file])
        assert "key: value" in result

    def test_reads_yml_files(self, tmp_path):
        """Reads and returns content from .yml files."""
        yml_file = tmp_path / "config.yml"
        yml_file.write_text("name: test\n")
        result = _read_input_files([yml_file])
        assert "name: test" in result

    def test_reads_rst_files(self, tmp_path):
        """Reads and returns content from .rst files."""
        rst_file = tmp_path / "readme.rst"
        rst_file.write_text("Title\n=====\nSome content\n")
        result = _read_input_files([rst_file])
        assert "Some content" in result

    def test_reads_json_files(self, tmp_path):
        """Reads and returns content from .json files."""
        json_file = tmp_path / "data.json"
        json_file.write_text('{"key": "value"}')
        result = _read_input_files([json_file])
        assert '"key": "value"' in result

    def test_warning_includes_supported_extensions(self, tmp_path, caplog):
        """Warning message for unsupported files lists supported extensions."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("a,b,c\n")
        with caplog.at_level("WARNING"):
            _read_input_files([csv_file])
        warning_msg = caplog.messages[0]
        assert "Unsupported file extension" in warning_msg
        assert ".csv" in warning_msg
        assert "Supported extensions:" in warning_msg
        # Verify at least some supported extensions are listed
        for ext in (".md", ".txt", ".yaml", ".json"):
            assert ext in warning_msg

    def test_warning_distinguishes_missing_from_unsupported(self, tmp_path, caplog):
        """Missing files get 'not found' warning, unsupported get 'Unsupported' warning."""
        missing = tmp_path / "missing.md"
        unsupported = tmp_path / "data.csv"
        unsupported.write_text("a,b\n")
        with caplog.at_level("WARNING"):
            _read_input_files([missing, unsupported])
        assert any("not found" in msg for msg in caplog.messages)
        assert any("Unsupported" in msg for msg in caplog.messages)

    def test_supported_extensions_constant(self):
        """SUPPORTED_EXTENSIONS contains all expected extensions."""
        assert SUPPORTED_EXTENSIONS == {".md", ".txt", ".yaml", ".yml", ".rst", ".json"}


# ============================================================================
# 7. FeatureSpecResult Dataclass Tests
# ============================================================================


class TestFeatureSpecResult:
    """Tests for FeatureSpecResult dataclass."""

    def test_creates_with_required_fields(self, tmp_path):
        """FeatureSpecResult can be created with required fields."""
        result = FeatureSpecResult(
            feature_file=tmp_path / "test.feature",
            assumptions_file=tmp_path / "test_assumptions.yaml",
            summary_file=tmp_path / "test_summary.md",
        )
        assert result.scenarios_count == 0
        assert result.assumptions_count == 0
        assert result.stack == "generic"
        assert result.scaffolding_files == {}

    def test_stores_all_fields(self, tmp_path):
        """FeatureSpecResult stores all provided fields."""
        result = FeatureSpecResult(
            feature_file=tmp_path / "f.feature",
            assumptions_file=tmp_path / "f_assumptions.yaml",
            summary_file=tmp_path / "f_summary.md",
            scenarios_count=3,
            assumptions_count=2,
            stack="python",
        )
        assert result.scenarios_count == 3
        assert result.assumptions_count == 2
        assert result.stack == "python"

    def test_new_fields_default_to_empty_lists(self, tmp_path):
        """modules, existing_features, and patterns default to empty lists."""
        result = FeatureSpecResult(
            feature_file=tmp_path / "test.feature",
            assumptions_file=tmp_path / "test_assumptions.yaml",
            summary_file=tmp_path / "test_summary.md",
        )
        assert result.modules == []
        assert result.existing_features == []
        assert result.patterns == []

    def test_new_fields_can_be_set(self, tmp_path):
        """modules, existing_features, and patterns can be set explicitly."""
        feature_path = tmp_path / "login.feature"
        result = FeatureSpecResult(
            feature_file=tmp_path / "test.feature",
            assumptions_file=tmp_path / "test_assumptions.yaml",
            summary_file=tmp_path / "test_summary.md",
            modules=["myapp", "myapp.services"],
            existing_features=[feature_path],
            patterns=["services", "repositories"],
        )
        assert result.modules == ["myapp", "myapp.services"]
        assert result.existing_features == [feature_path]
        assert result.patterns == ["services", "repositories"]


# ============================================================================
# 8. FeatureSpecCommand.execute() Tests
# ============================================================================


class TestFeatureSpecCommandExecute:
    """Tests for FeatureSpecCommand.execute() orchestration."""

    async def test_execute_returns_feature_spec_result(self, project_root, output_dir):
        """execute() returns a FeatureSpecResult instance."""
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=project_root)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )
        assert isinstance(result, FeatureSpecResult)

    async def test_execute_creates_output_files(self, project_root, output_dir):
        """execute() creates feature, assumptions, and summary files."""
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=project_root)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )
        assert result.feature_file.exists()
        assert result.assumptions_file.exists()
        assert result.summary_file.exists()

    async def test_execute_counts_scenarios_correctly(self, project_root, output_dir):
        """execute() counts scenarios in the feature content."""
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=project_root)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )
        assert result.scenarios_count == 2

    async def test_execute_counts_assumptions_correctly(self, project_root, output_dir):
        """execute() counts assumptions from options."""
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=project_root)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir, "assumptions": SAMPLE_ASSUMPTIONS},
            )
        assert result.assumptions_count == 2

    async def test_execute_detects_stack(self, project_root, output_dir):
        """execute() detects the project stack."""
        # Python project
        (project_root / "pyproject.toml").write_text("[build-system]\n")
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=project_root)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )
        assert result.stack == "python"

    async def test_execute_reads_from_files(self, project_root, output_dir, tmp_path):
        """execute() merges content from from_files into input_text."""
        context_file = tmp_path / "context.md"
        context_file.write_text("Additional context from file")

        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=project_root)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir, "from_files": [context_file]},
            )
        # The feature file should contain original content plus file content
        content = result.feature_file.read_text()
        assert "User Authentication" in content

    async def test_execute_uses_default_output_dir(self, project_root):
        """execute() defaults output to project_root/features."""
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=project_root)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={},
            )
        # Should have created files inside project_root/features/
        assert str(project_root / "features") in str(result.feature_file)

    async def test_execute_calls_seed_to_graphiti(self, project_root, output_dir):
        """execute() calls seed_to_graphiti as part of the pipeline."""
        mock_seed = AsyncMock()
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=mock_seed):
            cmd = FeatureSpecCommand(project_root=project_root)
            await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )
        mock_seed.assert_called_once()

    async def test_execute_scaffolding_files_empty_in_v1(self, project_root, output_dir):
        """execute() returns empty scaffolding_files dict in v1."""
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=project_root)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )
        assert result.scaffolding_files == {}

    async def test_execute_stores_project_root(self, project_root):
        """FeatureSpecCommand stores project_root."""
        cmd = FeatureSpecCommand(project_root=project_root)
        assert cmd.project_root == project_root

    async def test_execute_passes_detected_stack_to_summary(self, project_root, output_dir):
        """execute() passes detected stack to write_outputs so summary shows correct stack."""
        # Create Python project signals
        (project_root / "pyproject.toml").write_text("[build-system]\n")
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=project_root)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )
        summary_content = result.summary_file.read_text()
        assert "**Stack:** python" in summary_content
        assert "**BDD Runner:** pytest-bdd" in summary_content

    async def test_execute_populates_modules_from_scan_codebase(self, project_root, output_dir):
        """execute() populates result.modules from scan_codebase output."""
        # Create a Python package so scan_codebase finds a module
        pkg = project_root / "myapp"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=project_root)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )
        assert "myapp" in result.modules

    async def test_execute_populates_existing_features_from_scan_codebase(
        self, project_root, output_dir
    ):
        """execute() populates result.existing_features from scan_codebase output."""
        # Create a pre-existing feature file in the project root
        pre_existing = project_root / "login.feature"
        pre_existing.write_text("Feature: Login\n")
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=project_root)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )
        feature_names = [p.name for p in result.existing_features]
        assert "login.feature" in feature_names

    async def test_execute_populates_patterns_from_scan_codebase(self, project_root, output_dir):
        """execute() populates result.patterns from scan_codebase output."""
        # Create a file with a name that triggers pattern detection
        (project_root / "user_service.py").write_text("")
        with patch("guardkit.commands.feature_spec.seed_to_graphiti", new=AsyncMock()):
            cmd = FeatureSpecCommand(project_root=project_root)
            result = await cmd.execute(
                input_text=SAMPLE_FEATURE,
                options={"output_dir": output_dir},
            )
        assert "services" in result.patterns


# ============================================================================
# 9. Import Check Tests
# ============================================================================


class TestImports:
    """Verify all public symbols are importable."""

    def test_import_feature_spec_command(self):
        """FeatureSpecCommand is importable from guardkit.commands.feature_spec."""
        from guardkit.commands.feature_spec import FeatureSpecCommand

        assert FeatureSpecCommand is not None

    def test_import_feature_spec_result(self):
        """FeatureSpecResult is importable from guardkit.commands.feature_spec."""
        from guardkit.commands.feature_spec import FeatureSpecResult

        assert FeatureSpecResult is not None

    def test_import_detect_stack(self):
        """detect_stack is importable from guardkit.commands.feature_spec."""
        from guardkit.commands.feature_spec import detect_stack

        assert detect_stack is not None

    def test_import_scan_codebase(self):
        """scan_codebase is importable from guardkit.commands.feature_spec."""
        from guardkit.commands.feature_spec import scan_codebase

        assert scan_codebase is not None

    def test_import_write_outputs(self):
        """write_outputs is importable from guardkit.commands.feature_spec."""
        from guardkit.commands.feature_spec import write_outputs

        assert write_outputs is not None

    def test_import_seed_to_graphiti(self):
        """seed_to_graphiti is importable from guardkit.commands.feature_spec."""
        from guardkit.commands.feature_spec import seed_to_graphiti

        assert seed_to_graphiti is not None
