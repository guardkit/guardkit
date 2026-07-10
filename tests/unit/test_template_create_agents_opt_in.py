"""Tests for template-create's agent-generation opt-in (PB-7 §5).

Precedence under test:
  1. ``--no-agents`` (explicit opt-out) always wins.
  2. ``--agents`` / ``agents_opt_in=True`` (explicit opt-in).
  3. Interactive TTY, neither flag given -> prompt once, default N.
  4. Headless/non-interactive, neither flag given -> skip (new default).

Also covers: the decision is cached (no double-prompt across repeated calls),
and the CLI wiring (argparse flag + run_template_create signature + config
threading) is present.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from installer.core.commands.lib.template_create_orchestrator import (
    OrchestrationConfig,
    TemplateCreateOrchestrator,
)

# Repo-root-relative, not cwd-relative — some earlier test in a full-suite run
# may chdir without restoring, so a bare relative Path() is not reliable here.
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ORCHESTRATOR_PATH = (
    _REPO_ROOT / "installer" / "core" / "commands" / "lib" / "template_create_orchestrator.py"
)


def _make_orchestrator(tmp_path: Path, **config_kwargs) -> TemplateCreateOrchestrator:
    config = OrchestrationConfig(codebase_path=tmp_path, **config_kwargs)
    return TemplateCreateOrchestrator(config)


class TestPrecedence:
    def test_no_agents_wins_even_with_opt_in(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path, no_agents=True, agents_opt_in=True)
        assert orch._should_generate_agents() is False

    def test_explicit_opt_in_generates(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path, agents_opt_in=True)
        assert orch._should_generate_agents() is True

    def test_headless_default_is_skip(self, tmp_path: Path) -> None:
        """Neither flag given, non-interactive -> skip (the flipped default)."""
        orch = _make_orchestrator(tmp_path, interactive_validation=False)
        assert orch._should_generate_agents() is False

    def test_interactive_prompt_default_no(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path, interactive_validation=True)
        with patch("builtins.input", return_value=""):
            assert orch._should_generate_agents() is False

    def test_interactive_prompt_yes(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path, interactive_validation=True)
        with patch("builtins.input", return_value="y"):
            assert orch._should_generate_agents() is True

    def test_interactive_prompt_yes_full_word(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path, interactive_validation=True)
        with patch("builtins.input", return_value="Yes"):
            assert orch._should_generate_agents() is True

    def test_interactive_prompt_garbage_defaults_no(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path, interactive_validation=True)
        with patch("builtins.input", return_value="sure why not"):
            assert orch._should_generate_agents() is False

    def test_auto_detect_tty_used_when_interactive_validation_unset(
        self, tmp_path: Path
    ) -> None:
        orch = _make_orchestrator(tmp_path)  # interactive_validation=None (default)
        with patch("sys.stdin.isatty", return_value=False):
            assert orch._should_generate_agents() is False

    def test_eof_during_prompt_defaults_no(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path, interactive_validation=True)
        with patch("builtins.input", side_effect=EOFError):
            assert orch._should_generate_agents() is False


class TestCaching:
    def test_decision_cached_no_reprompt(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path, interactive_validation=True)
        with patch("builtins.input", return_value="y") as mock_input:
            first = orch._should_generate_agents()
            second = orch._should_generate_agents()
        assert first is True
        assert second is True
        mock_input.assert_called_once()

    def test_flag_based_decision_also_cached(self, tmp_path: Path) -> None:
        orch = _make_orchestrator(tmp_path, agents_opt_in=True)
        orch._should_generate_agents()
        orch._generate_agents_decision = False  # simulate external mutation
        # cached value wins — no re-resolution
        assert orch._should_generate_agents() is False


class TestCoverageMatrixClosingStep:
    """PB-7 §5: the coverage-matrix report as harvest's closing artifact."""

    def test_reports_covered_and_gap_layers(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        import json

        output_dir = tmp_path / "harvested-template"
        output_dir.mkdir()
        (output_dir / "settings.json").write_text(
            json.dumps(
                {
                    "layer_mappings": {
                        "api": {"directory": "src/api"},
                        "services": {"directory": "src/services"},
                    }
                }
            )
        )
        (output_dir / "templates" / "api").mkdir(parents=True)
        (output_dir / "templates" / "api" / "router.py.template").write_text("x = 1\n")

        orch = _make_orchestrator(tmp_path)
        orch._phase_coverage_matrix_report(output_dir)

        captured = capsys.readouterr()
        assert "1/2 layers covered" in captured.out
        assert "services" in captured.out

    def test_no_layer_mappings_reports_nothing_to_report(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        import json

        output_dir = tmp_path / "harvested-template"
        output_dir.mkdir()
        (output_dir / "settings.json").write_text(json.dumps({}))

        orch = _make_orchestrator(tmp_path)
        orch._phase_coverage_matrix_report(output_dir)

        captured = capsys.readouterr()
        assert "nothing to report" in captured.out

    def test_never_raises_on_broken_settings_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ) -> None:
        output_dir = tmp_path / "harvested-template"
        output_dir.mkdir()
        (output_dir / "settings.json").write_text("{ not valid json")

        orch = _make_orchestrator(tmp_path)
        orch._phase_coverage_matrix_report(output_dir)  # must not raise

        captured = capsys.readouterr()
        assert "nothing to report" in captured.out  # malformed settings -> no rows


class TestConfigDefaults:
    def test_agents_opt_in_defaults_false(self) -> None:
        config = OrchestrationConfig()
        assert config.agents_opt_in is False

    def test_no_agents_still_defaults_false_backward_compat(self) -> None:
        """no_agents itself is untouched — it's the RESOLVED decision that
        flips default, not this flag's own default."""
        config = OrchestrationConfig()
        assert config.no_agents is False


class TestCLIWiring:
    def test_agents_flag_registered_in_argparse(self) -> None:
        source = _ORCHESTRATOR_PATH.read_text()
        assert '"--agents"' in source
        assert 'dest="agents_opt_in"' in source

    def test_agents_opt_in_threaded_to_run_template_create(self) -> None:
        source = _ORCHESTRATOR_PATH.read_text()
        assert "agents_opt_in: bool = False" in source
        assert "agents_opt_in=agents_opt_in" in source
        assert "agents_opt_in=args.agents_opt_in" in source

    def test_no_agents_flag_still_present_backward_compat(self) -> None:
        source = _ORCHESTRATOR_PATH.read_text()
        assert '"--no-agents"' in source
