# Pytest Agent Testing Specialist - Extended Documentation

This file contains detailed examples, best practices, and in-depth guidance for the **pytest-agent-testing-specialist** agent.

**Core documentation**: See [pytest-agent-testing-specialist.md](./pytest-agent-testing-specialist.md)

---

## Related Templates

### Primary References

- **`templates/other/agents/agents.py.template`** — Defines `implementer_subagent()`, `evaluator_subagent()`, `builder_async_subagent()`, and `create_orchestrator()`. Each factory validates its `model` argument and raises `ValueError` for empty or non-string inputs. Tests for this module should cover: valid model strings, empty strings, non-string types, and the wiring of subagents into `create_deep_agent()`.

- **`templates/other/other/agent.py.template`** — The module-level entrypoint that calls `_load_config()`, `_load_domain_prompt()`, and `_build_agent()` at import time, with `yaml.safe_load` and argparse integration. This is the primary target for patching `yaml.safe_load` and `create_orchestrator` during tests, and for subprocess-based CLI `--domain` flag validation.

- **`templates/other/tools/orchestrator_tools.py.template`** — Implements `analyse_context`, `plan_pipeline`, `execute_command`, and `verify_output` with `@tool(parse_docstring=True)`. All tools return strings and catch all exceptions internally. Tests should confirm no-raise behaviour on bad inputs and correct string structure on happy-path inputs.

### Supporting References

- **`templates/other/prompts/orchestrator_prompts.py.template`** — Defines `ORCHESTRATOR_SYSTEM_PROMPT` with `{date}` and `{domain_prompt}` format placeholders. Tests should confirm that `.format(date=..., domain_prompt=...)` succeeds and that both values appear in the output.

- **`templates/other/prompts/evaluator_prompts.py.template`** — Defines `EVALUATOR_SYSTEM_PROMPT` built via a two-phase escaping strategy. Tests should confirm `{date}` formats cleanly and that the JSON verdict schema fields (`decision`, `score`, `issues`, `criteria_met`, `quality_assessment`) are present in the rendered prompt.

- **`templates/other/prompts/implementer_prompts.py.template`** — Defines `IMPLEMENTER_SYSTEM_PROMPT` with a single `{date}` placeholder. Tests confirm formatting succeeds and the rendered string contains date injection.

## Code Examples

### Example 1: Patching `create_deep_agent` and `create_orchestrator` in class-based tests

Derived from `templates/other/agents/agents.py.template` and `templates/other/other/agent.py.template`. The key pattern is patching at the call site (the module that imports the function), not at the definition site.

**DO — patch at the call site, use class-based organisation**

```python
# test_agents.py
from unittest.mock import MagicMock, patch

import pytest


class TestCreateOrchestrator:
    """Tests for the create_orchestrator factory function."""

    def test_returns_compiled_graph_for_valid_models(
        self, mock_create_deep_agent: MagicMock
    ) -> None:
        """create_orchestrator returns the graph produced by create_deep_agent."""
        from agents import create_orchestrator

        result = create_orchestrator(
            reasoning_model="anthropic:claude-sonnet-4-6",
            implementation_model="anthropic:claude-haiku-4-5",
            domain_prompt="Test domain guidelines.",
        )

        mock_create_deep_agent.assert_called_once()
        assert result is mock_create_deep_agent.return_value

    @pytest.mark.parametrize(
        "reasoning_model,implementation_model",
        [
            ("", "anthropic:claude-haiku-4-5"),
            ("anthropic:claude-sonnet-4-6", ""),
            (None, "anthropic:claude-haiku-4-5"),
            (42, "anthropic:claude-haiku-4-5"),
        ],
    )
    def test_raises_value_error_for_invalid_model(
        self,
        reasoning_model: object,
        implementation_model: object,
        mock_create_deep_agent: MagicMock,
    ) -> None:
        """create_orchestrator raises ValueError for empty or non-string models."""
        from agents import create_orchestrator

        with pytest.raises(ValueError):
            create_orchestrator(
                reasoning_model=reasoning_model,
                implementation_model=implementation_model,
                domain_prompt="irrelevant",
            )

    @pytest.fixture(autouse=True)
    def mock_create_deep_agent(self) -> MagicMock:
        with patch("agents.create_deep_agent") as mock:
            mock.return_value = MagicMock(name="compiled_graph")
            yield mock
```

**DON'T — patch at the wrong site or use module-level state in tests**

```python
# WRONG: patching the definition module, not the call site
with patch("deepagents.create_deep_agent") as mock:  # won't intercept agents.py imports
    ...

# WRONG: sharing mock state across test methods without autouse fixture
class TestBad:
    mock = patch("agents.create_deep_agent")  # class-level patch leaks between tests
```

---

### Example 2: Using `tmp_path` for config YAML and domain file I/O

Derived from `templates/other/other/agent.py.template`. The `_load_config()` function uses `yaml.safe_load` and falls back to `_DEFAULT_CONFIG` on `FileNotFoundError` or `yaml.YAMLError`. The `_load_domain_prompt()` function reads `domains/{domain}/DOMAIN.md` relative to a project root.

**DO — use `tmp_path` to write real files, test fallback behaviour**

```python
# test_agent.py
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


class TestLoadConfig:
    """Tests for _load_config() YAML parsing and fallback logic."""

    def test_parses_valid_yaml(self, tmp_path: Path) -> None:
        """_load_config returns parsed dict when YAML is valid."""
        config_data = {
            "orchestrator": {
                "reasoning_model": "anthropic:claude-sonnet-4-6",
                "implementation_model": "anthropic:claude-haiku-4-5",
            }
        }
        config_file = tmp_path / "orchestrator-config.yaml"
        config_file.write_text(yaml.dump(config_data), encoding="utf-8")

        from agent import _load_config

        result = _load_config(config_file)

        assert result["orchestrator"]["reasoning_model"] == "anthropic:claude-sonnet-4-6"

    def test_returns_defaults_when_file_missing(self, tmp_path: Path) -> None:
        """_load_config returns defaults when config file does not exist."""
        from agent import _DEFAULT_CONFIG, _load_config

        result = _load_config(tmp_path / "nonexistent.yaml")

        assert result == _DEFAULT_CONFIG

    def test_returns_defaults_for_invalid_yaml(self, tmp_path: Path) -> None:
        """_load_config returns defaults when YAML is malformed."""
        config_file = tmp_path / "orchestrator-config.yaml"
        config_file.write_text(": invalid: yaml: [", encoding="utf-8")

        from agent import _DEFAULT_CONFIG, _load_config

        result = _load_config(config_file)

        assert result == _DEFAULT_CONFIG


class TestLoadDomainPrompt:
    """Tests for _load_domain_prompt() file reading and fallback logic."""

    def test_reads_domain_md_when_present(self, tmp_path: Path) -> None:
        """_load_domain_prompt returns file content when DOMAIN.md exists."""
        domain_dir = tmp_path / "domains" / "my-domain"
        domain_dir.mkdir(parents=True)
        domain_file = domain_dir / "DOMAIN.md"
        domain_file.write_text("# My Domain\n\nCustom guidelines.", encoding="utf-8")

        from agent import _load_domain_prompt

        result = _load_domain_prompt(tmp_path, "my-domain")

        assert "Custom guidelines." in result

    def test_returns_default_when_domain_missing(self, tmp_path: Path) -> None:
        """_load_domain_prompt returns default prompt when directory absent."""
        from agent import _DEFAULT_DOMAIN_PROMPT, _load_domain_prompt

        result = _load_domain_prompt(tmp_path, "no-such-domain")

        assert result == _DEFAULT_DOMAIN_PROMPT
```

---

### Example 3: Subprocess CLI testing for `--domain` flag

Derived from `templates/other/other/agent.py.template`. The argparse block uses `parse_known_args()` so unknown flags do not raise `SystemExit`. Subprocess tests validate argument acceptance without importing the module (which triggers side effects).

**DO — use subprocess to test CLI arguments in isolation**

```python
# test_agent_cli.py
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestCLIArguments:
    """Subprocess-level tests for agent.py CLI argument parsing."""

    def test_accepts_known_domain_flag(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """agent.py --domain <name> exits cleanly when dependencies are mocked."""
        config_file = tmp_path / "orchestrator-config.yaml"
        config_file.write_text(
            "orchestrator:\n  reasoning_model: anthropic:claude-sonnet-4-6\n"
            "  implementation_model: anthropic:claude-haiku-4-5\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.argv = ['agent.py', '--domain', 'test-domain']; "
             "from unittest.mock import patch, MagicMock; "
             "with patch('agents.create_deep_agent', return_value=MagicMock()): "
             "    import agent"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0

    def test_unknown_flags_do_not_cause_system_exit(self) -> None:
        """parse_known_args() silently ignores flags injected by LangGraph server."""
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.argv = ['agent.py', '--unknown-flag', 'value']; "
             "from unittest.mock import patch, MagicMock; "
             "with patch('agents.create_deep_agent', return_value=MagicMock()): "
             "    import agent"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
```

---

### Example 4: Testing tool functions — no-raise contract and return types

Derived from `templates/other/tools/orchestrator_tools.py.template`. All four tools catch every exception internally and return strings, so tests must confirm the no-raise contract and assert on return type and content structure.

**DO — test happy-path return content and error-path no-raise contract**

```python
# test_tools.py
import pytest


class TestAnalyseContext:
    """Tests for the analyse_context tool."""

    def test_returns_string_for_free_text_query(self) -> None:
        from tools import analyse_context

        result = analyse_context(query="what is the architecture?", domain="software")

        assert isinstance(result, str)
        assert "software" in result

    def test_returns_file_content_when_query_is_valid_path(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        from tools import analyse_context

        test_file = tmp_path / "context.txt"
        test_file.write_text("important context", encoding="utf-8")

        result = analyse_context(query=str(test_file), domain="testing")

        assert "important context" in result

    def test_does_not_raise_on_empty_inputs(self) -> None:
        from tools import analyse_context

        result = analyse_context(query="", domain="")
        assert isinstance(result, str)


class TestPlanPipeline:
    """Tests for the plan_pipeline tool."""

    def test_returns_valid_json_string(self) -> None:
        import json
        from tools import plan_pipeline

        result = plan_pipeline(task="build feature X", context="Python project")

        parsed = json.loads(result)
        assert "steps" in parsed
        assert len(parsed["steps"]) == 3
```

---

### Example 5: Testing prompt string formatting

Derived from `templates/other/prompts/orchestrator_prompts.py.template` and `templates/other/prompts/evaluator_prompts.py.template`.

**DO — verify format placeholders resolve without KeyError**

```python
# test_prompts.py
import pytest


class TestOrchestratorSystemPrompt:
    """Tests for ORCHESTRATOR_SYSTEM_PROMPT formatting."""

    def test_formats_without_error(self) -> None:
        from prompts import ORCHESTRATOR_SYSTEM_PROMPT

        result = ORCHESTRATOR_SYSTEM_PROMPT.format(
            date="2026-03-30",
            domain_prompt="Custom domain instructions.",
        )

        assert "2026-03-30" in result
        assert "Custom domain instructions." in result


class TestEvaluatorSystemPrompt:
    """Tests for EVALUATOR_SYSTEM_PROMPT — validates two-phase escaping strategy."""

    def test_date_placeholder_resolves(self) -> None:
        from prompts import EVALUATOR_SYSTEM_PROMPT

        result = EVALUATOR_SYSTEM_PROMPT.format(date="2026-03-30")

        assert "2026-03-30" in result

    def test_verdict_schema_fields_present_in_prompt(self) -> None:
        from prompts import EVALUATOR_SYSTEM_PROMPT

        rendered = EVALUATOR_SYSTEM_PROMPT.format(date="2026-03-30")

        for field in ("decision", "score", "issues", "criteria_met", "quality_assessment"):
            assert field in rendered, f"Expected verdict field '{field}' in evaluator prompt"
```

---

## conftest.py Example

Complete shared fixture file for the orchestrator test suite:

```python
# tests/conftest.py
from unittest.mock import MagicMock, patch
from pathlib import Path
import pytest
import yaml

@pytest.fixture
def project_root(tmp_path: Path) -> Path:
    """Create a minimal project structure in tmp_path."""
    (tmp_path / "domains" / "test-domain").mkdir(parents=True)
    (tmp_path / "domains" / "test-domain" / "DOMAIN.md").write_text(
        "# Test\n\nTest domain guidelines.", encoding="utf-8"
    )
    (tmp_path / "AGENTS.md").write_text(
        "# Agent Rules\n\n- Follow coding standards.", encoding="utf-8"
    )
    config = {"orchestrator": {
        "reasoning_model": "anthropic:claude-sonnet-4-6",
        "implementation_model": "anthropic:claude-haiku-4-5",
    }}
    (tmp_path / "orchestrator-config.yaml").write_text(
        yaml.dump(config), encoding="utf-8"
    )
    return tmp_path

@pytest.fixture
def mock_create_deep_agent():
    """Patch create_deep_agent at the agents module call site."""
    with patch("agents.create_deep_agent") as mock:
        mock.return_value = MagicMock(name="compiled_graph")
        yield mock
```

## Parametrize Patterns

Test model validation edge cases across all factory functions:

```python
import pytest
from agents import create_orchestrator

class TestModelValidation:
    @pytest.mark.parametrize("bad_model", [
        "",            # empty string
        None,          # None type
        42,            # wrong type
        "no-provider", # missing provider: prefix
    ])
    def test_create_orchestrator_rejects_bad_reasoning_model(
        self, bad_model, mock_create_deep_agent
    ):
        with pytest.raises(ValueError):
            create_orchestrator(
                reasoning_model=bad_model,
                implementation_model="anthropic:claude-haiku-4-5",
                domain_prompt="test",
            )

    @pytest.mark.parametrize("bad_model", ["", None, 42])
    def test_create_orchestrator_rejects_bad_implementation_model(
        self, bad_model, mock_create_deep_agent
    ):
        with pytest.raises(ValueError):
            create_orchestrator(
                reasoning_model="anthropic:claude-sonnet-4-6",
                implementation_model=bad_model,
                domain_prompt="test",
            )
```

---

*This extended documentation is part of GuardKit's progressive disclosure system.*
