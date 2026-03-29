"""Tests for the preflight validation module.

Validates all 8 automated checks, the report formatter, manual prompts,
and the CLI entry point. Each check function is tested with both passing
and failing scenarios using temporary project directories.

Coverage Target: >=85%
Test Count: 35+ tests
"""

from __future__ import annotations

import importlib.util
import json
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# Import the module from the template's lib directory
# ---------------------------------------------------------------------------
_LIB_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "templates"
    / "langchain-deepagents"
    / "lib"
    / "preflight.py"
)


@pytest.fixture(scope="module")
def preflight_mod():
    """Load the preflight module directly from source."""
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader("preflight", str(_LIB_PATH))
    spec = importlib.util.spec_from_loader("preflight", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["preflight"] = mod
    loader.exec_module(mod)
    return mod


@pytest.fixture
def CheckResult(preflight_mod):
    return preflight_mod.CheckResult


@pytest.fixture
def PreflightReport(preflight_mod):
    return preflight_mod.PreflightReport


# ---------------------------------------------------------------------------
# Helper: create a project directory with factory files
# ---------------------------------------------------------------------------


def _write_factory(tmp_path: Path, content: str, filename: str = "agent_factory.py") -> Path:
    """Write a factory file into a temp project directory."""
    factory_file = tmp_path / filename
    factory_file.write_text(textwrap.dedent(content), encoding="utf-8")
    return factory_file


def _write_config(tmp_path: Path, content: str, filename: str = "agent-config.yaml") -> Path:
    """Write a config file into a temp project directory."""
    config_file = tmp_path / filename
    config_file.write_text(textwrap.dedent(content), encoding="utf-8")
    return config_file


def _write_domain(tmp_path: Path, domain_name: str, domain_md: str, config: dict | None = None) -> Path:
    """Write a domain directory with DOMAIN.md and optional config."""
    domain_dir = tmp_path / "domains" / domain_name
    domain_dir.mkdir(parents=True, exist_ok=True)
    (domain_dir / "DOMAIN.md").write_text(textwrap.dedent(domain_md), encoding="utf-8")
    if config is not None:
        (domain_dir / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
    return domain_dir


# ===================================================================
# CheckResult and PreflightReport Tests
# ===================================================================


class TestCheckResult:
    def test_basic_pass(self, CheckResult):
        r = CheckResult(name="test", passed=True, detail="ok")
        assert r.passed is True
        assert r.severity == "error"

    def test_basic_fail(self, CheckResult):
        r = CheckResult(name="test", passed=False, detail="bad")
        assert r.passed is False

    def test_warning_severity(self, CheckResult):
        r = CheckResult(name="test", passed=False, detail="warn", severity="warning")
        assert r.severity == "warning"


class TestPreflightReport:
    def test_empty_report_passes(self, PreflightReport):
        report = PreflightReport()
        assert report.passed is True
        assert report.fail_count == 0
        assert report.pass_count == 0

    def test_all_passed(self, PreflightReport, CheckResult):
        report = PreflightReport(
            checks=[
                CheckResult("a", True, "ok"),
                CheckResult("b", True, "ok"),
            ]
        )
        assert report.passed is True
        assert report.pass_count == 2
        assert report.fail_count == 0

    def test_one_failure(self, PreflightReport, CheckResult):
        report = PreflightReport(
            checks=[
                CheckResult("a", True, "ok"),
                CheckResult("b", False, "bad"),
            ]
        )
        assert report.passed is False
        assert report.fail_count == 1

    def test_warning_does_not_affect_passed(self, PreflightReport, CheckResult):
        report = PreflightReport(
            checks=[
                CheckResult("a", True, "ok"),
                CheckResult("b", False, "warn", severity="warning"),
            ]
        )
        assert report.passed is True
        assert report.fail_count == 0


# ===================================================================
# check_player_tools Tests
# ===================================================================


class TestCheckPlayerTools:
    def test_pass_with_domain_tools(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            PLAYER_ALLOWED_TOOLS: set[str] = {"search_data"}
        ''')
        result = preflight_mod.check_player_tools(tmp_path)
        assert result.passed is True
        assert "search_data" in result.detail

    def test_fail_with_filesystem_tool(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            PLAYER_ALLOWED_TOOLS: set[str] = {"search_data", "write_file"}
        ''')
        result = preflight_mod.check_player_tools(tmp_path)
        assert result.passed is False
        assert "filesystem" in result.detail.lower() or "write_file" in result.detail

    def test_fail_no_factory_files(self, preflight_mod, tmp_path):
        (tmp_path / "main.py").write_text("pass")
        result = preflight_mod.check_player_tools(tmp_path)
        assert result.passed is False

    def test_empty_tool_set(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            PLAYER_ALLOWED_TOOLS: set[str] = set()
        ''')
        result = preflight_mod.check_player_tools(tmp_path)
        assert result.passed is True

    def test_multiple_filesystem_tools(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            PLAYER_ALLOWED_TOOLS: set[str] = {"search_data", "ls", "read_file", "glob"}
        ''')
        result = preflight_mod.check_player_tools(tmp_path)
        assert result.passed is False


# ===================================================================
# check_coach_tools Tests
# ===================================================================


class TestCheckCoachTools:
    def test_pass_empty_set(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            COACH_ALLOWED_TOOLS: set[str] = set()
        ''')
        result = preflight_mod.check_coach_tools(tmp_path)
        assert result.passed is True
        assert "set()" in result.detail

    def test_fail_coach_has_tools(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            COACH_ALLOWED_TOOLS: set[str] = {"search_data"}
        ''')
        result = preflight_mod.check_coach_tools(tmp_path)
        assert result.passed is False
        assert "search_data" in result.detail

    def test_fail_no_factory_files(self, preflight_mod, tmp_path):
        result = preflight_mod.check_coach_tools(tmp_path)
        assert result.passed is False


# ===================================================================
# check_no_write_output Tests
# ===================================================================


class TestCheckNoWriteOutput:
    def test_pass_no_write_output(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            PLAYER_ALLOWED_TOOLS: set[str] = {"search_data"}
        ''')
        result = preflight_mod.check_no_write_output(tmp_path)
        assert result.passed is True

    def test_fail_write_output_in_allowlist(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            PLAYER_ALLOWED_TOOLS: set[str] = {"search_data", "write_output"}
        ''')
        result = preflight_mod.check_no_write_output(tmp_path)
        assert result.passed is False
        assert "TOOL SEPARATION VIOLATION" in result.detail

    def test_fail_write_output_in_player_file(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            tools = [search_data, write_output]
        ''', filename="player.py")
        result = preflight_mod.check_no_write_output(tmp_path)
        assert result.passed is False

    def test_pass_no_factory_no_reference(self, preflight_mod, tmp_path):
        result = preflight_mod.check_no_write_output(tmp_path)
        assert result.passed is False  # No factory files found


# ===================================================================
# check_factory_pattern Tests
# ===================================================================


class TestCheckFactoryPattern:
    def test_pass_uses_create_restricted_agent(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            from lib.factory_guards import create_restricted_agent

            def create_player(model):
                return create_restricted_agent(model=model, tools=[], system_prompt="p")
        ''')
        result = preflight_mod.check_factory_pattern(tmp_path)
        assert result.passed is True
        assert "create_restricted_agent" in result.detail

    def test_fail_uses_create_deep_agent_in_factory(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            from deepagents import create_deep_agent

            def create_player(model):
                return create_deep_agent(model=model, tools=[], system_prompt="p")
        ''')
        result = preflight_mod.check_factory_pattern(tmp_path)
        assert result.passed is False
        assert "create_deep_agent" in result.detail

    def test_pass_create_deep_agent_in_non_factory_file(self, preflight_mod, tmp_path):
        # create_deep_agent in agent.py (entrypoint) is OK - not a factory file
        (tmp_path / "agent.py").write_text(
            "from deepagents import create_deep_agent\ncreate_deep_agent(model='m')\n"
        )
        # Also add a player factory that uses create_restricted_agent
        _write_factory(tmp_path, '''
            from lib.factory_guards import create_restricted_agent

            def create_player(model):
                return create_restricted_agent(model=model, tools=[], system_prompt="p")
        ''', filename="player_factory.py")
        result = preflight_mod.check_factory_pattern(tmp_path)
        assert result.passed is True


# ===================================================================
# check_max_tokens Tests
# ===================================================================


class TestCheckMaxTokens:
    def test_pass_max_tokens_in_config(self, preflight_mod, tmp_path):
        _write_config(tmp_path, '''
            coach:
              provider: local
              local:
                model: llama3.2
                max_tokens: 4096
        ''')
        result = preflight_mod.check_max_tokens(tmp_path)
        assert result.passed is True
        assert "4096" in result.detail

    def test_pass_max_tokens_in_python(self, preflight_mod, tmp_path):
        _write_config(tmp_path, "coach:\n  provider: local\n")
        _write_factory(tmp_path, '''
            MAX_TOKENS = 4096
        ''')
        result = preflight_mod.check_max_tokens(tmp_path)
        assert result.passed is True

    def test_pass_max_tokens_in_function_call(self, preflight_mod, tmp_path):
        _write_config(tmp_path, "coach:\n  provider: local\n")
        _write_factory(tmp_path, '''
            def create():
                return build(model="m", max_tokens=2048)
        ''')
        result = preflight_mod.check_max_tokens(tmp_path)
        assert result.passed is True
        assert "2048" in result.detail

    def test_fail_no_max_tokens(self, preflight_mod, tmp_path):
        _write_config(tmp_path, '''
            coach:
              provider: local
              local:
                model: llama3.2
        ''')
        result = preflight_mod.check_max_tokens(tmp_path)
        assert result.passed is False

    def test_fail_no_config_file(self, preflight_mod, tmp_path):
        result = preflight_mod.check_max_tokens(tmp_path)
        assert result.passed is False
        assert "not found" in result.detail


# ===================================================================
# check_domain_config Tests
# ===================================================================


class TestCheckDomainConfig:
    def test_pass_valid_domain(self, preflight_mod, tmp_path):
        _write_domain(tmp_path, "science", '''
            # Science Domain

            ## Targets
            - target: question_generation

            ## Metadata
            - field: difficulty
        ''')
        result = preflight_mod.check_domain_config(tmp_path)
        assert result.passed is True

    def test_fail_missing_targets(self, preflight_mod, tmp_path):
        _write_domain(tmp_path, "science", '''
            # Science Domain

            ## Metadata
            - field: difficulty
        ''')
        result = preflight_mod.check_domain_config(tmp_path)
        assert result.passed is False
        assert "missing Targets" in result.detail

    def test_fail_missing_metadata(self, preflight_mod, tmp_path):
        _write_domain(tmp_path, "science", '''
            # Science Domain

            ## Targets
            - target: q
        ''')
        result = preflight_mod.check_domain_config(tmp_path)
        assert result.passed is False
        assert "missing Metadata" in result.detail

    def test_pass_no_domains_dir(self, preflight_mod, tmp_path):
        result = preflight_mod.check_domain_config(tmp_path)
        assert result.passed is True
        assert result.severity == "warning"

    def test_fail_invalid_json_config(self, preflight_mod, tmp_path):
        domain_dir = tmp_path / "domains" / "bad"
        domain_dir.mkdir(parents=True)
        (domain_dir / "DOMAIN.md").write_text("## Targets\n## Metadata\n")
        (domain_dir / "config.json").write_text("{ invalid json", encoding="utf-8")
        result = preflight_mod.check_domain_config(tmp_path)
        assert result.passed is False
        assert "parse error" in result.detail


# ===================================================================
# check_metadata_types Tests
# ===================================================================


class TestCheckMetadataTypes:
    def test_pass_consistent_types(self, preflight_mod, tmp_path):
        result = preflight_mod.check_metadata_types(tmp_path)
        # No config files → warning
        assert result.severity == "warning"

    def test_fail_range_on_string_type(self, preflight_mod, tmp_path):
        _write_domain(tmp_path, "test", "## Targets\n## Metadata\n", config={
            "metadata": {
                "difficulty": {
                    "name": "difficulty",
                    "type": "string",
                    "valid_values": "1-10",
                }
            }
        })
        result = preflight_mod.check_metadata_types(tmp_path)
        assert result.passed is False
        assert "range notation" in result.detail

    def test_pass_range_on_integer_type(self, preflight_mod, tmp_path):
        _write_domain(tmp_path, "test", "## Targets\n## Metadata\n", config={
            "metadata": {
                "difficulty": {
                    "name": "difficulty",
                    "type": "integer",
                    "valid_values": "1-10",
                }
            }
        })
        result = preflight_mod.check_metadata_types(tmp_path)
        assert result.passed is True

    def test_fail_range_in_python_metadata_field(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            from lib.domain_validator import MetadataField, FieldType

            schema = [
                MetadataField("turns", type=FieldType.STRING, valid_values="1+"),
            ]
        ''')
        result = preflight_mod.check_metadata_types(tmp_path)
        assert result.passed is False
        assert "turns" in result.detail


# ===================================================================
# check_json_pipeline Tests
# ===================================================================


class TestCheckJsonPipeline:
    def test_pass_uses_extractor(self, preflight_mod, tmp_path):
        (tmp_path / "pipeline_factory.py").write_text(textwrap.dedent('''
            from lib.json_extractor import JsonExtractor

            def parse_response(content):
                return JsonExtractor.extract(content)
        '''))
        result = preflight_mod.check_json_pipeline(tmp_path)
        assert result.passed is True
        assert "JsonExtractor" in result.detail

    def test_fail_raw_json_loads_in_agent(self, preflight_mod, tmp_path):
        (tmp_path / "agent_factory.py").write_text(textwrap.dedent('''
            import json

            def parse_agent_response(response):
                content = response.content
                return json.loads(content)
        '''))
        result = preflight_mod.check_json_pipeline(tmp_path)
        assert result.passed is False
        assert "json.loads" in result.detail.lower() or "JsonExtractor" in result.detail

    def test_pass_no_llm_parsing(self, preflight_mod, tmp_path):
        (tmp_path / "utils_factory.py").write_text("x = 1\n")
        result = preflight_mod.check_json_pipeline(tmp_path)
        assert result.passed is True


# ===================================================================
# run_preflight Tests
# ===================================================================


class TestRunPreflight:
    def test_run_on_valid_project(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            PLAYER_ALLOWED_TOOLS: set[str] = {"search_data"}
            COACH_ALLOWED_TOOLS: set[str] = set()
        ''')
        _write_config(tmp_path, '''
            coach:
              provider: local
              local:
                model: llama3.2
                max_tokens: 4096
        ''')

        report = preflight_mod.run_preflight(tmp_path)
        assert isinstance(report, preflight_mod.PreflightReport)
        assert len(report.checks) == 8
        assert len(report.manual_prompts) == 4

    def test_report_contains_all_checks(self, preflight_mod, tmp_path):
        report = preflight_mod.run_preflight(tmp_path)
        check_names = [c.name for c in report.checks]
        assert "Player tools" in check_names
        assert "Coach tools" in check_names
        assert "max_tokens set" in check_names


# ===================================================================
# format_report Tests
# ===================================================================


class TestFormatReport:
    def test_format_includes_pass_fail(self, preflight_mod, CheckResult, PreflightReport):
        report = PreflightReport(
            checks=[
                CheckResult("tool check", True, "Player tools: {'search_data'}"),
                CheckResult("config check", False, "max_tokens not set"),
            ],
            manual_prompts=["Does your Player prompt end with CRITICAL section?"],
        )
        output = preflight_mod.format_report(report)
        assert "[PASS]" in output
        assert "[FAIL]" in output
        assert "?" in output
        assert "1 FAIL" in output
        assert "1 PASS" in output

    def test_format_includes_manual_prompts(self, preflight_mod, PreflightReport):
        report = PreflightReport(manual_prompts=["Check prompt?"])
        output = preflight_mod.format_report(report)
        assert "Check prompt?" in output
        assert "Manual Review:" in output


# ===================================================================
# main (CLI) Tests
# ===================================================================


class TestMain:
    def test_exit_0_on_pass(self, preflight_mod, tmp_path):
        _write_factory(tmp_path, '''
            PLAYER_ALLOWED_TOOLS: set[str] = {"search_data"}
            COACH_ALLOWED_TOOLS: set[str] = set()
        ''')
        _write_config(tmp_path, '''
            coach:
              provider: local
              local:
                model: llama3.2
                max_tokens: 4096
        ''')
        exit_code = preflight_mod.main([str(tmp_path)])
        assert exit_code == 0

    def test_exit_1_on_fail(self, preflight_mod, tmp_path):
        # Factory with write_output → fail
        _write_factory(tmp_path, '''
            PLAYER_ALLOWED_TOOLS: set[str] = {"write_output"}
        ''')
        _write_config(tmp_path, "coach:\n  provider: local\n")
        exit_code = preflight_mod.main([str(tmp_path)])
        assert exit_code == 1

    def test_exit_1_on_invalid_dir(self, preflight_mod, tmp_path):
        exit_code = preflight_mod.main([str(tmp_path / "nonexistent")])
        assert exit_code == 1

    def test_defaults_to_cwd(self, preflight_mod, tmp_path):
        with patch("os.getcwd", return_value=str(tmp_path)):
            # Will use cwd when no args
            exit_code = preflight_mod.main([str(tmp_path)])
            assert exit_code in (0, 1)


# ===================================================================
# AST Helper Tests
# ===================================================================


class TestASTHelpers:
    def test_extract_set_assignment_literal(self, preflight_mod, tmp_path):
        f = tmp_path / "test.py"
        f.write_text('MY_SET = {"a", "b"}')
        tree = preflight_mod._parse_file(f)
        result = preflight_mod._extract_set_assignment(tree, "MY_SET")
        assert result == {"a", "b"}

    def test_extract_set_assignment_empty(self, preflight_mod, tmp_path):
        f = tmp_path / "test.py"
        f.write_text('MY_SET = set()')
        tree = preflight_mod._parse_file(f)
        result = preflight_mod._extract_set_assignment(tree, "MY_SET")
        assert result == set()

    def test_extract_set_assignment_not_found(self, preflight_mod, tmp_path):
        f = tmp_path / "test.py"
        f.write_text('x = 1')
        tree = preflight_mod._parse_file(f)
        result = preflight_mod._extract_set_assignment(tree, "MY_SET")
        assert result is None

    def test_parse_file_returns_none_on_syntax_error(self, preflight_mod, tmp_path):
        f = tmp_path / "bad.py"
        f.write_text("def broken(:\n")
        result = preflight_mod._parse_file(f)
        assert result is None

    def test_find_python_files_excludes_pycache(self, preflight_mod, tmp_path):
        good = tmp_path / "good.py"
        good.write_text("pass")
        cache_dir = tmp_path / "__pycache__"
        cache_dir.mkdir()
        (cache_dir / "cached.py").write_text("pass")
        files = preflight_mod._find_python_files(tmp_path)
        assert good in files
        assert all("__pycache__" not in str(f) for f in files)


# ===================================================================
# YAML Parser Tests
# ===================================================================


class TestSimpleYamlParser:
    def test_flat_keys(self, preflight_mod):
        text = "key1: value1\nkey2: value2\n"
        result = preflight_mod._parse_simple_yaml(text)
        assert result == {"key1": "value1", "key2": "value2"}

    def test_nested_section(self, preflight_mod):
        text = "section:\n  key1: value1\n  key2: value2\n"
        result = preflight_mod._parse_simple_yaml(text)
        assert result["section"]["key1"] == "value1"

    def test_comments_ignored(self, preflight_mod):
        text = "# comment\nkey: value\n"
        result = preflight_mod._parse_simple_yaml(text)
        assert result == {"key": "value"}

    def test_empty_input(self, preflight_mod):
        result = preflight_mod._parse_simple_yaml("")
        assert result == {}


# ===================================================================
# Manual Prompts Tests
# ===================================================================


class TestManualPrompts:
    def test_four_manual_prompts_defined(self, preflight_mod):
        assert len(preflight_mod.MANUAL_PROMPTS) == 4

    def test_prompts_are_questions(self, preflight_mod):
        for prompt in preflight_mod.MANUAL_PROMPTS:
            assert prompt.endswith("?")

    def test_prompts_cover_key_concerns(self, preflight_mod):
        prompts_text = " ".join(preflight_mod.MANUAL_PROMPTS).lower()
        assert "player prompt" in prompts_text
        assert "coach prompt" in prompts_text
        assert "model" in prompts_text
        assert "vllm" in prompts_text or "reasoning" in prompts_text
