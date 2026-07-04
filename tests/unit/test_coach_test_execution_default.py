"""
Test suite for TASK-AB-COACHSUBPROC01: Coach test_execution subprocess default.

The Coach's SDK-based "environment parity" independent test execution failed
with an opaque exit-1 ("Fatal error in message reader") on essentially 100% of
invocations across the 2026 retro corpus; every verdict actually came from the
subprocess fallback. This flips the default to "subprocess" and keeps "sdk"
selectable via config (``autobuild.coach.test_execution``) and env
(``GUARDKIT_COACH_TEST_EXECUTION``), with env > config > default precedence
(mirroring the TASK-AB-PERTASKFG01 ``GUARDKIT_PHASE4_TEST_EXECUTION`` pattern).

Tests cover:
    - TestResolveCoachTestExecution: precedence + invalid-value degradation
    - TestResolutionLogging: INFO provenance log (default/config/env)
    - TestCoachValidatorDefault: constructor resolution (None / explicit / env)
    - TestModeWiring: subprocess default never attempts the SDK entry point;
      explicit sdk still routes through the SDK bridge (with fallback intact)
    - TestConfigFileResolution: .guardkit/config.yaml -> _load_coach_config ->
      resolve_coach_test_execution round trip

Coverage Target: >=85%
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import (
    COACH_TEST_EXECUTION_ENV,
    DEFAULT_COACH_TEST_EXECUTION,
    CoachValidator,
    IndependentTestResult,
    resolve_coach_test_execution,
)


@pytest.fixture(autouse=True)
def _clear_coach_test_execution_env(monkeypatch):
    """Isolate every test from an ambient GUARDKIT_COACH_TEST_EXECUTION."""
    monkeypatch.delenv(COACH_TEST_EXECUTION_ENV, raising=False)


# ============================================================================
# 1. TestResolveCoachTestExecution (precedence + invalid values)
# ============================================================================


class TestResolveCoachTestExecution:
    """resolve_coach_test_execution: env > config > default (subprocess)."""

    def test_default_is_subprocess(self):
        """No env, no config -> subprocess (the TASK-AB-COACHSUBPROC01 flip)."""
        assert resolve_coach_test_execution() == "subprocess"
        assert DEFAULT_COACH_TEST_EXECUTION == "subprocess"

    def test_config_sdk_selects_sdk(self):
        """Config 'sdk' still selects the SDK opt-in path (AC-002)."""
        assert resolve_coach_test_execution("sdk") == "sdk"

    def test_config_subprocess_selects_subprocess(self):
        assert resolve_coach_test_execution("subprocess") == "subprocess"

    def test_env_overrides_config_sdk(self, monkeypatch):
        """Env 'subprocess' beats config 'sdk'."""
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "subprocess")
        assert resolve_coach_test_execution("sdk") == "subprocess"

    def test_env_sdk_overrides_config_subprocess(self, monkeypatch):
        """Env 'sdk' beats config 'subprocess' (revert lever for diagnosis)."""
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "sdk")
        assert resolve_coach_test_execution("subprocess") == "sdk"

    def test_env_is_case_insensitive_and_stripped(self, monkeypatch):
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "  SDK  ")
        assert resolve_coach_test_execution() == "sdk"

    def test_invalid_env_no_config_degrades_to_default_with_warning(
        self, monkeypatch, caplog
    ):
        """Invalid env value -> safe default (subprocess) with WARNING."""
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "bogus")
        with caplog.at_level(logging.WARNING):
            assert resolve_coach_test_execution() == "subprocess"
        assert any(
            COACH_TEST_EXECUTION_ENV in r.getMessage()
            for r in caplog.records
            if r.levelno == logging.WARNING
        )

    def test_invalid_env_falls_through_to_valid_config(self, monkeypatch, caplog):
        """An invalid env tier is ignored; a valid config tier still applies."""
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "bogus")
        with caplog.at_level(logging.WARNING):
            assert resolve_coach_test_execution("sdk") == "sdk"
        assert any(r.levelno == logging.WARNING for r in caplog.records)

    def test_invalid_config_degrades_to_default_with_warning(self, caplog):
        """Invalid config value -> safe default (subprocess) with WARNING."""
        with caplog.at_level(logging.WARNING):
            assert resolve_coach_test_execution("llm-magic") == "subprocess"
        assert any(
            "autobuild.coach.test_execution" in r.getMessage()
            for r in caplog.records
            if r.levelno == logging.WARNING
        )

    def test_empty_env_and_config_are_treated_as_unset(self, monkeypatch):
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "   ")
        assert resolve_coach_test_execution("") == "subprocess"


# ============================================================================
# 2. TestResolutionLogging (INFO provenance, display-must-derive honesty)
# ============================================================================


class TestResolutionLogging:
    """The resolver logs the active mode and its source at INFO."""

    def _provenance_records(self, caplog):
        return [
            r
            for r in caplog.records
            if r.levelno == logging.INFO
            and "Coach test execution mode" in r.getMessage()
        ]

    def test_logs_source_default(self, caplog):
        with caplog.at_level(logging.INFO):
            resolve_coach_test_execution()
        records = self._provenance_records(caplog)
        assert len(records) == 1
        msg = records[0].getMessage()
        assert "subprocess" in msg
        assert "source: default" in msg

    def test_logs_source_config(self, caplog):
        with caplog.at_level(logging.INFO):
            resolve_coach_test_execution("sdk")
        msg = self._provenance_records(caplog)[0].getMessage()
        assert "sdk" in msg
        assert "source: config" in msg

    def test_logs_source_env(self, monkeypatch, caplog):
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "sdk")
        with caplog.at_level(logging.INFO):
            resolve_coach_test_execution("subprocess")
        msg = self._provenance_records(caplog)[0].getMessage()
        assert "sdk" in msg
        assert "source: env" in msg

    def test_default_validator_init_logs_provenance_once(self, tmp_path, caplog):
        """A default-constructed validator logs the provenance line once."""
        with caplog.at_level(logging.INFO):
            CoachValidator(str(tmp_path))
        assert len(self._provenance_records(caplog)) == 1


# ============================================================================
# 3. TestCoachValidatorDefault (constructor resolution)
# ============================================================================


class TestCoachValidatorDefault:
    """CoachValidator.__init__ resolves None via env > default."""

    def test_default_construction_is_subprocess(self, tmp_path):
        validator = CoachValidator(str(tmp_path))
        assert validator._coach_test_execution == "subprocess"

    def test_default_construction_honours_env_sdk(self, tmp_path, monkeypatch):
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "sdk")
        validator = CoachValidator(str(tmp_path))
        assert validator._coach_test_execution == "sdk"

    def test_explicit_sdk_is_stored(self, tmp_path):
        validator = CoachValidator(str(tmp_path), coach_test_execution="sdk")
        assert validator._coach_test_execution == "sdk"

    def test_explicit_value_is_authoritative_over_env(self, tmp_path, monkeypatch):
        """An explicit caller pin is never env-overridden (protects the
        deterministic Phase-4 runner's pinned 'subprocess')."""
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "sdk")
        validator = CoachValidator(
            str(tmp_path), coach_test_execution="subprocess"
        )
        assert validator._coach_test_execution == "subprocess"

    def test_explicit_invalid_degrades_to_default_with_warning(
        self, tmp_path, caplog
    ):
        with caplog.at_level(logging.WARNING):
            validator = CoachValidator(
                str(tmp_path), coach_test_execution="bogus"
            )
        assert validator._coach_test_execution == "subprocess"
        assert any(
            "coach_test_execution" in r.getMessage()
            for r in caplog.records
            if r.levelno == logging.WARNING
        )

    def test_explicit_invalid_delegates_to_env_tier(
        self, tmp_path, monkeypatch, caplog
    ):
        """2026-07-04 code review: an INVALID explicit value is not a pin —
        it must delegate to env > default resolution, so a valid
        GUARDKIT_COACH_TEST_EXECUTION=sdk override still applies (previously
        it fell straight to the default, bypassing the env tier)."""
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "sdk")
        with caplog.at_level(logging.WARNING):
            validator = CoachValidator(
                str(tmp_path), coach_test_execution="bogus"
            )
        assert validator._coach_test_execution == "sdk"
        assert any(
            "coach_test_execution" in r.getMessage()
            for r in caplog.records
            if r.levelno == logging.WARNING
        )

    def test_explicit_invalid_with_invalid_env_still_lands_on_default(
        self, tmp_path, monkeypatch
    ):
        """Invalid explicit + invalid env → the resolver's own invalid-tier
        fall-through lands on the default (never selects a mode by accident)."""
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "also-bogus")
        validator = CoachValidator(str(tmp_path), coach_test_execution="bogus")
        assert validator._coach_test_execution == "subprocess"


# ============================================================================
# 4. TestModeWiring (subprocess never attempts SDK; sdk still routes via SDK)
# ============================================================================


class TestModeWiring:
    """run_independent_tests dispatch under the new default."""

    def _mock_proc(self, stdout="5 passed"):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = stdout
        proc.stderr = ""
        return proc

    def test_default_mode_never_attempts_sdk(self, tmp_path):
        """Default (subprocess) never calls the SDK entry point."""
        validator = CoachValidator(str(tmp_path), test_command="pytest tests/")
        assert validator._coach_test_execution == "subprocess"

        with patch.object(validator, "_run_tests_via_sdk") as mock_sdk:
            with patch(
                "subprocess.run", return_value=self._mock_proc()
            ) as mock_subprocess:
                result = validator.run_independent_tests()

        mock_sdk.assert_not_called()
        mock_subprocess.assert_called_once()
        assert result.tests_passed is True

    def test_default_mode_with_requires_infra_stays_subprocess(
        self, tmp_path, monkeypatch
    ):
        """AC-004: the requires_infra branch under the new default is the
        plain subprocess path — it never re-selects the SDK, and the
        infra-forces-subprocess pin (TASK-REV-CB30 R5) is a no-op because
        subprocess is already the mode."""
        validator = CoachValidator(str(tmp_path), test_command="pytest tests/")
        # Docker unavailable -> no container lifecycle; classification handles it.
        monkeypatch.setattr(
            validator, "_is_docker_available", lambda: False, raising=False
        )

        with patch.object(validator, "_run_tests_via_sdk") as mock_sdk:
            with patch(
                "subprocess.run", return_value=self._mock_proc()
            ) as mock_subprocess:
                result = validator.run_independent_tests(
                    task={"requires_infrastructure": ["postgresql"]}
                )

        mock_sdk.assert_not_called()
        mock_subprocess.assert_called_once()
        assert result.tests_passed is True

    def test_env_sdk_opt_in_routes_through_sdk_with_fallback(
        self, tmp_path, monkeypatch
    ):
        """GUARDKIT_COACH_TEST_EXECUTION=sdk restores the SDK-with-fallback
        path (opt-in for TASK-REV-COSE / TASK-FIX-A7B7 diagnosis)."""
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "sdk")
        # The SDK dispatch is additionally gated on the SDK harness
        # (TASK-FIX-COACHTESTTO forces subprocess under LangGraph).
        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
        validator = CoachValidator(str(tmp_path), test_command="pytest tests/")
        assert validator._coach_test_execution == "sdk"

        sdk_result = IndependentTestResult(
            tests_passed=True,
            test_command="pytest tests/",
            test_output_summary="5 passed",
            duration_seconds=1.0,
        )

        with patch.object(validator, "_run_tests_via_sdk", return_value=sdk_result):
            with patch("asyncio.get_event_loop") as mock_get_loop:
                mock_loop = MagicMock()
                mock_loop.run_until_complete.return_value = sdk_result
                mock_get_loop.return_value = mock_loop

                result = validator.run_independent_tests()

        mock_loop.run_until_complete.assert_called_once()
        assert result.tests_passed is True

    def test_env_sdk_opt_in_falls_back_to_subprocess_on_sdk_error(
        self, tmp_path, monkeypatch
    ):
        """The SDK opt-in keeps its subprocess fallback machinery intact."""
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "sdk")
        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
        validator = CoachValidator(str(tmp_path), test_command="pytest tests/")

        with patch("asyncio.get_event_loop") as mock_get_loop:
            mock_loop = MagicMock()
            mock_loop.run_until_complete.side_effect = RuntimeError(
                "Fatal error in message reader"
            )
            mock_get_loop.return_value = mock_loop

            with patch(
                "subprocess.run", return_value=self._mock_proc("3 passed")
            ) as mock_subprocess:
                result = validator.run_independent_tests()

        mock_subprocess.assert_called_once()
        assert result.tests_passed is True


# ============================================================================
# 5. TestConfigFileResolution (.guardkit/config.yaml round trip)
# ============================================================================


class TestConfigFileResolution:
    """_load_coach_config -> resolve_coach_test_execution round trip."""

    def _make_orchestrator(self, repo_root: Path):
        from guardkit.orchestrator.autobuild import AutoBuildOrchestrator

        orch = AutoBuildOrchestrator.__new__(AutoBuildOrchestrator)
        orch.repo_root = repo_root
        return orch

    def _write_config(self, repo_root: Path, test_execution: str) -> None:
        config_dir = repo_root / ".guardkit"
        config_dir.mkdir(parents=True, exist_ok=True)
        (config_dir / "config.yaml").write_text(
            f"autobuild:\n  coach:\n    test_execution: {test_execution}\n"
        )

    def test_no_config_file_resolves_subprocess(self, tmp_path):
        orch = self._make_orchestrator(tmp_path)
        coach_cfg = orch._load_coach_config()
        assert (
            resolve_coach_test_execution(coach_cfg.get("test_execution"))
            == "subprocess"
        )

    def test_config_sdk_resolves_sdk(self, tmp_path):
        orch = self._make_orchestrator(tmp_path)
        self._write_config(tmp_path, "sdk")
        coach_cfg = orch._load_coach_config()
        assert (
            resolve_coach_test_execution(coach_cfg.get("test_execution"))
            == "sdk"
        )

    def test_env_beats_config_file(self, tmp_path, monkeypatch):
        monkeypatch.setenv(COACH_TEST_EXECUTION_ENV, "subprocess")
        orch = self._make_orchestrator(tmp_path)
        self._write_config(tmp_path, "sdk")
        coach_cfg = orch._load_coach_config()
        assert (
            resolve_coach_test_execution(coach_cfg.get("test_execution"))
            == "subprocess"
        )
