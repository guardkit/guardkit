"""
Docker reachability smoke test.

Verifies that CoachValidator._is_docker_available() executes without error
and returns a boolean value. Does NOT assert True or False — Docker may or
may not be running in the test environment.

This test is skipped automatically when the `docker` binary is not found on
PATH. It is intended to be run in environments where Docker is present to
confirm the detection method works end-to-end without any mocking.
"""

import shutil

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


@pytest.mark.skipif(
    not shutil.which("docker"),
    reason="Docker binary not found on PATH — skipping Docker smoke test",
)
def test_is_docker_available_returns_boolean(tmp_path):
    """
    Smoke test: _is_docker_available() returns a boolean without mocking.

    Validates that:
    1. The method executes without raising an exception
    2. The return value is a bool (True or False)

    The actual value is not asserted because Docker may or may not be running
    in the test environment. The test only checks that the detection path is
    reachable.
    """
    validator = CoachValidator(
        worktree_path=str(tmp_path),
        coach_test_execution="subprocess",
    )
    result = validator._is_docker_available()
    assert isinstance(result, bool), (
        f"_is_docker_available() must return bool, got {type(result).__name__!r}"
    )
