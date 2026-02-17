"""
Unit tests for TASK-INFR-5922: Docker test fixtures for Player and Coach.

Tests cover:
1. docker_fixtures module functions (DOCKER_FIXTURES dict, get_start_commands,
   get_container_name, get_env_exports, is_known_service)
2. CoachValidator Docker methods (_is_docker_available, _start_infrastructure_containers,
   _stop_infrastructure_containers)
3. Integration of infrastructure lifecycle with run_independent_tests

Coverage Target: >=85%
Test Count: 33 tests
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from guardkit.orchestrator.docker_fixtures import (
    DOCKER_FIXTURES,
    get_container_name,
    get_env_exports,
    get_start_commands,
    is_known_service,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)


# ============================================================================
# Helpers
# ============================================================================


def make_validator(worktree_path: Optional[Path] = None, **kwargs) -> CoachValidator:
    """Create a CoachValidator instance for testing."""
    if worktree_path is None:
        worktree_path = Path(tempfile.mkdtemp())
    return CoachValidator(
        worktree_path=str(worktree_path),
        coach_test_execution="subprocess",
        **kwargs,
    )


# ============================================================================
# 1. TestDockerFixturesModule
# ============================================================================


class TestDockerFixturesModule:
    """Tests for docker_fixtures.py module-level functions."""

    # ------------------------------------------------------------------
    # get_start_commands
    # ------------------------------------------------------------------

    def test_get_start_commands_postgresql_returns_three_commands(self) -> None:
        """get_start_commands('postgresql') returns exactly 3 shell commands."""
        cmds = get_start_commands("postgresql")
        assert len(cmds) == 3

    def test_get_start_commands_redis_returns_three_commands(self) -> None:
        """get_start_commands('redis') returns exactly 3 shell commands."""
        cmds = get_start_commands("redis")
        assert len(cmds) == 3

    def test_get_start_commands_mongodb_returns_three_commands(self) -> None:
        """get_start_commands('mongodb') returns exactly 3 shell commands."""
        cmds = get_start_commands("mongodb")
        assert len(cmds) == 3

    def test_get_start_commands_unknown_service_raises_key_error(self) -> None:
        """get_start_commands with unknown service raises KeyError."""
        with pytest.raises(KeyError):
            get_start_commands("mysql")

    def test_get_start_commands_case_insensitive(self) -> None:
        """get_start_commands is case-insensitive: 'PostgreSQL' works same as 'postgresql'."""
        lower_cmds = get_start_commands("postgresql")
        upper_cmds = get_start_commands("PostgreSQL")
        assert lower_cmds == upper_cmds

    def test_get_start_commands_postgresql_first_cmd_removes_existing_container(
        self,
    ) -> None:
        """First command for postgresql removes any existing container."""
        cmds = get_start_commands("postgresql")
        assert "docker rm -f" in cmds[0]
        assert "guardkit-test-pg" in cmds[0]

    def test_get_start_commands_postgresql_second_cmd_is_docker_run(self) -> None:
        """Second command for postgresql is docker run with expected options."""
        cmds = get_start_commands("postgresql")
        assert cmds[1].startswith("docker run -d --name guardkit-test-pg")

    def test_get_start_commands_postgresql_readiness_uses_command_loop(self) -> None:
        """PostgreSQL readiness check uses 'until' loop (command type)."""
        cmds = get_start_commands("postgresql")
        assert cmds[2].startswith("until ")
        assert "pg_isready" in cmds[2]

    def test_get_start_commands_redis_readiness_uses_sleep(self) -> None:
        """Redis readiness check uses sleep (fixed wait type)."""
        cmds = get_start_commands("redis")
        assert cmds[2].startswith("sleep ")

    def test_get_start_commands_mongodb_readiness_uses_sleep(self) -> None:
        """MongoDB readiness check uses sleep (fixed wait type)."""
        cmds = get_start_commands("mongodb")
        assert cmds[2].startswith("sleep ")

    # ------------------------------------------------------------------
    # get_container_name
    # ------------------------------------------------------------------

    def test_get_container_name_postgresql(self) -> None:
        """get_container_name('postgresql') returns 'guardkit-test-pg'."""
        assert get_container_name("postgresql") == "guardkit-test-pg"

    def test_get_container_name_redis(self) -> None:
        """get_container_name('redis') returns 'guardkit-test-redis'."""
        assert get_container_name("redis") == "guardkit-test-redis"

    def test_get_container_name_mongodb(self) -> None:
        """get_container_name('mongodb') returns 'guardkit-test-mongo'."""
        assert get_container_name("mongodb") == "guardkit-test-mongo"

    # ------------------------------------------------------------------
    # get_env_exports
    # ------------------------------------------------------------------

    def test_get_env_exports_postgresql_contains_database_url(self) -> None:
        """get_env_exports('postgresql') returns dict with DATABASE_URL key."""
        exports = get_env_exports("postgresql")
        assert "DATABASE_URL" in exports
        assert exports["DATABASE_URL"].startswith("postgresql://")

    def test_get_env_exports_redis_contains_redis_url(self) -> None:
        """get_env_exports('redis') returns dict with REDIS_URL key."""
        exports = get_env_exports("redis")
        assert "REDIS_URL" in exports
        assert exports["REDIS_URL"].startswith("redis://")

    def test_get_env_exports_mongodb_contains_mongodb_url(self) -> None:
        """get_env_exports('mongodb') returns dict with MONGODB_URL key."""
        exports = get_env_exports("mongodb")
        assert "MONGODB_URL" in exports
        assert exports["MONGODB_URL"].startswith("mongodb://")

    def test_get_env_exports_returns_copy(self) -> None:
        """get_env_exports returns a new dict (not a reference to the fixture)."""
        exports1 = get_env_exports("redis")
        exports2 = get_env_exports("redis")
        assert exports1 is not exports2

    # ------------------------------------------------------------------
    # is_known_service
    # ------------------------------------------------------------------

    def test_is_known_service_postgresql_is_known(self) -> None:
        """is_known_service returns True for 'postgresql'."""
        assert is_known_service("postgresql") is True

    def test_is_known_service_redis_is_known(self) -> None:
        """is_known_service returns True for 'redis'."""
        assert is_known_service("redis") is True

    def test_is_known_service_mongodb_is_known(self) -> None:
        """is_known_service returns True for 'mongodb'."""
        assert is_known_service("mongodb") is True

    def test_is_known_service_mysql_is_unknown(self) -> None:
        """is_known_service returns False for 'mysql'."""
        assert is_known_service("mysql") is False

    def test_is_known_service_elasticsearch_is_unknown(self) -> None:
        """is_known_service returns False for 'elasticsearch'."""
        assert is_known_service("elasticsearch") is False

    def test_is_known_service_case_insensitive_postgresql(self) -> None:
        """is_known_service is case-insensitive: 'PostgreSQL' returns True."""
        assert is_known_service("PostgreSQL") is True

    # ------------------------------------------------------------------
    # Non-standard port verification
    # ------------------------------------------------------------------

    def test_postgresql_uses_non_standard_port_5433(self) -> None:
        """PostgreSQL docker run command uses port 5433 (not standard 5432)."""
        cmds = get_start_commands("postgresql")
        run_cmd = cmds[1]
        assert "5433" in run_cmd

    def test_redis_uses_non_standard_port_6380(self) -> None:
        """Redis docker run command uses port 6380 (not standard 6379)."""
        cmds = get_start_commands("redis")
        run_cmd = cmds[1]
        assert "6380" in run_cmd

    def test_mongodb_uses_non_standard_port_27018(self) -> None:
        """MongoDB docker run command uses port 27018 (not standard 27017)."""
        cmds = get_start_commands("mongodb")
        run_cmd = cmds[1]
        assert "27018" in run_cmd


# ============================================================================
# 2. TestCoachValidatorDockerMethods
# ============================================================================


class TestCoachValidatorDockerMethods:
    """Tests for CoachValidator Docker-related methods."""

    # ------------------------------------------------------------------
    # _is_docker_available
    # ------------------------------------------------------------------

    def test_is_docker_available_success(self, tmp_path: Path) -> None:
        """_is_docker_available returns True when docker info exits 0."""
        validator = make_validator(tmp_path)
        mock_result = Mock()
        mock_result.returncode = 0
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            assert validator._is_docker_available() is True
        mock_run.assert_called_once_with(
            ["docker", "info"], capture_output=True, timeout=5
        )

    def test_is_docker_available_failure_nonzero_exit(self, tmp_path: Path) -> None:
        """_is_docker_available returns False when docker info exits non-zero."""
        validator = make_validator(tmp_path)
        mock_result = Mock()
        mock_result.returncode = 1
        with patch("subprocess.run", return_value=mock_result):
            assert validator._is_docker_available() is False

    def test_is_docker_available_file_not_found(self, tmp_path: Path) -> None:
        """_is_docker_available returns False when docker binary not found."""
        validator = make_validator(tmp_path)
        with patch("subprocess.run", side_effect=FileNotFoundError):
            assert validator._is_docker_available() is False

    def test_is_docker_available_timeout(self, tmp_path: Path) -> None:
        """_is_docker_available returns False when docker info times out."""
        validator = make_validator(tmp_path)
        with patch(
            "subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="docker info", timeout=5)
        ):
            assert validator._is_docker_available() is False

    # ------------------------------------------------------------------
    # _start_infrastructure_containers
    # ------------------------------------------------------------------

    def test_start_infrastructure_containers_postgresql_runs_commands(
        self, tmp_path: Path
    ) -> None:
        """_start_infrastructure_containers runs subprocess.run for each command."""
        validator = make_validator(tmp_path)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result) as mock_run:
            validator._start_infrastructure_containers(["postgresql"])
        # 3 shell commands expected
        expected_call_count = 3
        actual_shell_calls = [c for c in mock_run.call_args_list if c.kwargs.get("shell")]
        assert len(actual_shell_calls) == expected_call_count

    def test_start_infrastructure_containers_unknown_service_no_subprocess(
        self, tmp_path: Path
    ) -> None:
        """_start_infrastructure_containers skips unknown service without calling subprocess."""
        validator = make_validator(tmp_path)
        with patch("subprocess.run") as mock_run:
            validator._start_infrastructure_containers(["mysql"])
        # subprocess.run should not be called for unknown service
        mock_run.assert_not_called()

    def test_start_infrastructure_containers_sets_env_vars(
        self, tmp_path: Path
    ) -> None:
        """_start_infrastructure_containers sets env vars in os.environ."""
        validator = make_validator(tmp_path)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            with patch.dict(os.environ, {}, clear=False):
                # Remove key first to ensure clean state
                os.environ.pop("DATABASE_URL", None)
                validator._start_infrastructure_containers(["postgresql"])
                assert "DATABASE_URL" in os.environ
                assert os.environ["DATABASE_URL"].startswith("postgresql://")
                # Clean up
                os.environ.pop("DATABASE_URL", None)

    def test_start_infrastructure_containers_redis_sets_redis_url(
        self, tmp_path: Path
    ) -> None:
        """_start_infrastructure_containers sets REDIS_URL for redis service."""
        validator = make_validator(tmp_path)
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stderr = ""
        with patch("subprocess.run", return_value=mock_result):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("REDIS_URL", None)
                validator._start_infrastructure_containers(["redis"])
                assert "REDIS_URL" in os.environ
                assert os.environ["REDIS_URL"].startswith("redis://")
                os.environ.pop("REDIS_URL", None)

    # ------------------------------------------------------------------
    # _stop_infrastructure_containers
    # ------------------------------------------------------------------

    def test_stop_infrastructure_containers_postgresql_calls_docker_rm(
        self, tmp_path: Path
    ) -> None:
        """_stop_infrastructure_containers calls docker rm -f for postgresql."""
        validator = make_validator(tmp_path)
        with patch("subprocess.run") as mock_run:
            validator._stop_infrastructure_containers(["postgresql"])
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        cmd = call_args.args[0]
        assert cmd == ["docker", "rm", "-f", "guardkit-test-pg"]

    def test_stop_infrastructure_containers_unknown_service_no_subprocess(
        self, tmp_path: Path
    ) -> None:
        """_stop_infrastructure_containers does nothing for unknown service."""
        validator = make_validator(tmp_path)
        with patch("subprocess.run") as mock_run:
            validator._stop_infrastructure_containers(["elasticsearch"])
        mock_run.assert_not_called()

    def test_stop_infrastructure_containers_cleans_env_vars(
        self, tmp_path: Path
    ) -> None:
        """_stop_infrastructure_containers removes env vars from os.environ."""
        validator = make_validator(tmp_path)
        with patch("subprocess.run"):
            with patch.dict(os.environ, {"DATABASE_URL": "postgresql://placeholder"}, clear=False):
                validator._stop_infrastructure_containers(["postgresql"])
                assert "DATABASE_URL" not in os.environ

    def test_stop_infrastructure_containers_exception_handled_no_raise(
        self, tmp_path: Path
    ) -> None:
        """_stop_infrastructure_containers does not raise if docker rm fails."""
        validator = make_validator(tmp_path)
        with patch("subprocess.run", side_effect=Exception("docker not available")):
            # Should not raise
            validator._stop_infrastructure_containers(["postgresql"])

    def test_stop_infrastructure_containers_redis_calls_docker_rm(
        self, tmp_path: Path
    ) -> None:
        """_stop_infrastructure_containers calls docker rm -f guardkit-test-redis for redis."""
        validator = make_validator(tmp_path)
        with patch("subprocess.run") as mock_run:
            validator._stop_infrastructure_containers(["redis"])
        call_args = mock_run.call_args
        cmd = call_args.args[0]
        assert cmd == ["docker", "rm", "-f", "guardkit-test-redis"]


# ============================================================================
# 3. TestRunIndependentTestsInfrastructure
# ============================================================================


class TestRunIndependentTestsInfrastructure:
    """Integration tests for infrastructure lifecycle in run_independent_tests."""

    def _make_passing_test_result(self) -> IndependentTestResult:
        return IndependentTestResult(
            tests_passed=True,
            test_command="pytest",
            test_output_summary="1 passed",
            duration_seconds=0.1,
        )

    def _make_failing_test_result(self) -> IndependentTestResult:
        return IndependentTestResult(
            tests_passed=False,
            test_command="pytest",
            test_output_summary="1 failed",
            duration_seconds=0.1,
            raw_output="AssertionError: assert 1 == 2",
        )

    def test_with_infrastructure_docker_available_start_and_stop_called(
        self, tmp_path: Path
    ) -> None:
        """When requires_infrastructure set and Docker available, start+stop are called."""
        validator = make_validator(tmp_path, test_command="pytest")
        task = {"requires_infrastructure": ["postgresql"]}

        with patch.object(
            validator, "_is_docker_available", return_value=True
        ) as mock_docker_check:
            with patch.object(
                validator, "_start_infrastructure_containers"
            ) as mock_start:
                with patch.object(
                    validator, "_stop_infrastructure_containers"
                ) as mock_stop:
                    with patch(
                        "subprocess.run",
                        return_value=Mock(returncode=0, stdout="1 passed", stderr=""),
                    ):
                        result = validator.run_independent_tests(
                            task_work_results={}, task=task
                        )

        mock_docker_check.assert_called_once()
        mock_start.assert_called_once_with(["postgresql"])
        mock_stop.assert_called_once_with(["postgresql"])

    def test_with_infrastructure_docker_unavailable_warning_logged_no_start(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """When Docker unavailable, warning is logged and containers are not started."""
        import logging
        validator = make_validator(tmp_path, test_command="pytest")
        task = {"requires_infrastructure": ["postgresql"]}

        with patch.object(validator, "_is_docker_available", return_value=False):
            with patch.object(
                validator, "_start_infrastructure_containers"
            ) as mock_start:
                with patch.object(validator, "_stop_infrastructure_containers") as mock_stop:
                    with patch(
                        "subprocess.run",
                        return_value=Mock(returncode=0, stdout="1 passed", stderr=""),
                    ):
                        with caplog.at_level(logging.WARNING):
                            validator.run_independent_tests(
                                task_work_results={}, task=task
                            )

        mock_start.assert_not_called()
        mock_stop.assert_not_called()
        assert any("Docker is unavailable" in r.message for r in caplog.records)

    def test_without_infrastructure_docker_never_checked(self, tmp_path: Path) -> None:
        """When no requires_infrastructure, _is_docker_available is never called."""
        validator = make_validator(tmp_path, test_command="pytest")
        task = {}  # No requires_infrastructure key

        with patch.object(validator, "_is_docker_available") as mock_docker_check:
            with patch(
                "subprocess.run",
                return_value=Mock(returncode=0, stdout="1 passed", stderr=""),
            ):
                validator.run_independent_tests(task_work_results={}, task=task)

        mock_docker_check.assert_not_called()

    def test_task_none_backward_compat_no_infrastructure_lifecycle(
        self, tmp_path: Path
    ) -> None:
        """When task=None, no infrastructure lifecycle methods are called."""
        validator = make_validator(tmp_path, test_command="pytest")

        with patch.object(validator, "_is_docker_available") as mock_docker_check:
            with patch.object(
                validator, "_start_infrastructure_containers"
            ) as mock_start:
                with patch.object(
                    validator, "_stop_infrastructure_containers"
                ) as mock_stop:
                    with patch(
                        "subprocess.run",
                        return_value=Mock(returncode=0, stdout="1 passed", stderr=""),
                    ):
                        validator.run_independent_tests(task_work_results={}, task=None)

        mock_docker_check.assert_not_called()
        mock_start.assert_not_called()
        mock_stop.assert_not_called()

    def test_teardown_called_even_when_tests_fail(self, tmp_path: Path) -> None:
        """_stop_infrastructure_containers is called in finally block even if tests fail."""
        validator = make_validator(tmp_path, test_command="pytest")
        task = {"requires_infrastructure": ["redis"]}

        with patch.object(validator, "_is_docker_available", return_value=True):
            with patch.object(validator, "_start_infrastructure_containers"):
                with patch.object(
                    validator, "_stop_infrastructure_containers"
                ) as mock_stop:
                    with patch(
                        "subprocess.run",
                        return_value=Mock(
                            returncode=1,
                            stdout="",
                            stderr="FAILED test_foo.py::test_bar",
                        ),
                    ):
                        result = validator.run_independent_tests(
                            task_work_results={}, task=task
                        )

        # stop must still be called even though tests failed
        mock_stop.assert_called_once_with(["redis"])
        assert result.tests_passed is False

    def test_empty_requires_infrastructure_no_lifecycle(self, tmp_path: Path) -> None:
        """Empty requires_infrastructure list triggers no infrastructure lifecycle."""
        validator = make_validator(tmp_path, test_command="pytest")
        task = {"requires_infrastructure": []}

        with patch.object(validator, "_is_docker_available") as mock_docker_check:
            with patch.object(
                validator, "_start_infrastructure_containers"
            ) as mock_start:
                with patch.object(
                    validator, "_stop_infrastructure_containers"
                ) as mock_stop:
                    with patch(
                        "subprocess.run",
                        return_value=Mock(returncode=0, stdout="1 passed", stderr=""),
                    ):
                        validator.run_independent_tests(
                            task_work_results={}, task=task
                        )

        mock_docker_check.assert_not_called()
        mock_start.assert_not_called()
        mock_stop.assert_not_called()
