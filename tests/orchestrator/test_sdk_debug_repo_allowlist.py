"""Tests for sdk_debug repo allowlist and default-on behavior (TASK-OBS-396E AC-1)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING
from unittest import mock

import pytest

from guardkit.orchestrator import sdk_debug

if TYPE_CHECKING:
    from _pytest.monkeypatch import MonkeyPatch


class TestRepoAllowlist:
    """Test repo allowlist detection and default-on behavior (AC-1)."""

    def test_guardkit_repo_defaults_on_with_env_unset(
        self, monkeypatch: MonkeyPatch, tmp_path: Path
    ) -> None:
        """In a repo named 'guardkit', env var unset → capture defaults ON."""
        # ARRANGE: repo root is named guardkit
        repo_root = tmp_path / "guardkit"
        repo_root.mkdir()
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "")
        monkeypatch.delenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", raising=False)

        # Mock git remote to confirm repo identity
        def mock_git_remote(cwd: Path) -> str:
            return "origin\tgit@github.com:org/guardkit.git"

        # ACT: check if preservation should be enabled
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0, stdout="origin\tgit@github.com:org/guardkit.git"
            )
            enabled = sdk_debug.preservation_enabled_for_repo(repo_root)

        # ASSERT: defaults ON for guardkit repo
        assert enabled is True

    def test_fleet_repo_defaults_on_with_env_unset(
        self, monkeypatch: MonkeyPatch, tmp_path: Path
    ) -> None:
        """In a repo named 'fleet-*', env var unset → capture defaults ON."""
        # ARRANGE: repo root is named fleet-gateway
        repo_root = tmp_path / "fleet-gateway"
        repo_root.mkdir()
        monkeypatch.delenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", raising=False)

        # ACT
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0, stdout="origin\tgit@github.com:org/fleet-gateway.git"
            )
            enabled = sdk_debug.preservation_enabled_for_repo(repo_root)

        # ASSERT
        assert enabled is True

    def test_client_repo_defaults_off_with_env_unset(
        self, monkeypatch: MonkeyPatch, tmp_path: Path
    ) -> None:
        """In a client repo, env var unset → capture defaults OFF."""
        # ARRANGE: repo root is a client name (not in allowlist)
        repo_root = tmp_path / "finproxy-client"
        repo_root.mkdir()
        monkeypatch.delenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", raising=False)

        # ACT
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0, stdout="origin\tgit@github.com:client/finproxy-client.git"
            )
            enabled = sdk_debug.preservation_enabled_for_repo(repo_root)

        # ASSERT: defaults OFF for non-allowlisted repo
        assert enabled is False

    def test_env_var_zero_forces_off_in_allowlisted_repo(
        self, monkeypatch: MonkeyPatch, tmp_path: Path
    ) -> None:
        """Env var =0 forces OFF even in allowlisted repo."""
        # ARRANGE
        repo_root = tmp_path / "guardkit"
        repo_root.mkdir()
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "0")

        # ACT
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0, stdout="origin\tgit@github.com:org/guardkit.git"
            )
            enabled = sdk_debug.preservation_enabled_for_repo(repo_root)

        # ASSERT: forced OFF
        assert enabled is False

    def test_env_var_one_forces_on_in_client_repo(
        self, monkeypatch: MonkeyPatch, tmp_path: Path
    ) -> None:
        """Env var =1 forces ON even in client repo."""
        # ARRANGE
        repo_root = tmp_path / "finproxy-client"
        repo_root.mkdir()
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        # ACT
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0, stdout="origin\tgit@github.com:client/finproxy-client.git"
            )
            enabled = sdk_debug.preservation_enabled_for_repo(repo_root)

        # ASSERT: forced ON
        assert enabled is True


class TestSizeCappedRotation:
    """Test size-capped rotation behavior (AC-2)."""

    def test_oversized_stream_yields_truncation_marker(
        self, tmp_path: Path
    ) -> None:
        """Oversized messages.jsonl gets truncated with explicit marker."""
        # ARRANGE: mock a debug dir with growing messages.jsonl
        debug_dir = tmp_path / "sdk_debug" / "turn_1"
        debug_dir.mkdir(parents=True)
        messages_file = debug_dir / "messages.jsonl"

        # Simulate multiple events accumulating
        per_turn_cap = 100  # small cap for testing
        small_event = {"type": "test", "data": "x" * 30}

        # ACT: preserve events until cap is reached
        with mock.patch.object(sdk_debug, "PER_TURN_CAP_BYTES", per_turn_cap):
            # Write multiple events to exceed cap
            for _ in range(5):
                sdk_debug.preserve_event(debug_dir, small_event)

        # ASSERT: file contains truncation marker
        content = messages_file.read_text()
        assert "[TRUNCATED at" in content
        assert "bytes]" in content

    def test_per_task_pruning_leaves_marker(
        self, tmp_path: Path
    ) -> None:
        """Per-task total cap pruning leaves PRUNED.marker."""
        # ARRANGE: create multiple turns exceeding per-task cap
        task_dir = tmp_path / "sdk_debug"
        task_dir.mkdir()

        # Create turn_1 (oldest)
        turn1 = task_dir / "turn_1"
        turn1.mkdir()
        (turn1 / "messages.jsonl").write_text("x" * 50)

        # Create turn_2
        turn2 = task_dir / "turn_2"
        turn2.mkdir()
        (turn2 / "messages.jsonl").write_text("x" * 60)

        per_task_cap = 80  # Total cap less than turn1 + turn2

        # ACT: trigger pruning
        with mock.patch.object(sdk_debug, "PER_TASK_CAP_BYTES", per_task_cap):
            sdk_debug.prune_old_turns_if_needed(task_dir)

        # ASSERT: turn_1 is pruned and marker exists
        assert not turn1.exists()
        marker = task_dir / "PRUNED.marker"
        assert marker.exists()
        marker_content = marker.read_text()
        assert "turn_1" in marker_content

    def test_capture_never_exceeds_caps(
        self, tmp_path: Path
    ) -> None:
        """Capture respects both per-turn and per-task caps."""
        # ARRANGE
        task_dir = tmp_path / "sdk_debug"
        task_dir.mkdir()
        debug_dir = task_dir / "turn_1"
        debug_dir.mkdir()

        per_turn_cap = 50
        large_event = {"data": "x" * 100}

        # ACT: try to preserve oversized event
        with mock.patch.object(sdk_debug, "PER_TURN_CAP_BYTES", per_turn_cap):
            sdk_debug.preserve_event(debug_dir, large_event)

            # Check file size
            messages_file = debug_dir / "messages.jsonl"
            size = messages_file.stat().st_size

        # ASSERT: does not exceed cap
        assert size <= per_turn_cap + 100  # allow for marker


class TestStructuralFlipGating:
    """Test structural flip-gating (AC-2b)."""

    def test_allowlisted_repo_does_not_capture_with_invalid_caps(
        self, monkeypatch: MonkeyPatch, tmp_path: Path, caplog
    ) -> None:
        """Allowlisted repo with invalid rotation caps → no capture + WARNING."""
        # ARRANGE: guardkit repo but invalid caps
        repo_root = tmp_path / "guardkit"
        repo_root.mkdir()
        monkeypatch.delenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", raising=False)
        monkeypatch.setenv("GUARDKIT_SDK_DEBUG_PER_TURN_CAP", "invalid")

        # ACT
        with mock.patch("subprocess.run") as mock_run:
            mock_run.return_value = mock.Mock(
                returncode=0, stdout="origin\tgit@github.com:org/guardkit.git"
            )
            enabled = sdk_debug.preservation_enabled_for_repo(repo_root)

        # ASSERT: capture NOT enabled
        assert enabled is False
        # WARNING should name the failed prerequisite
        assert any("rotation cap" in rec.message.lower() for rec in caplog.records)

    def test_allowlisted_repo_does_not_capture_with_failed_gitignore_check(
        self, monkeypatch: MonkeyPatch, tmp_path: Path, caplog
    ) -> None:
        """Allowlisted repo with keep-out-of-git check failing → no capture + WARNING."""
        # ARRANGE: guardkit repo but gitignore check fails
        repo_root = tmp_path / "guardkit"
        repo_root.mkdir()
        monkeypatch.delenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", raising=False)

        # ACT: mock git check-ignore to return failure
        with mock.patch("subprocess.run") as mock_run:
            # First call: git remote
            # Second call: git check-ignore (fails)
            mock_run.side_effect = [
                mock.Mock(returncode=0, stdout="origin\tgit@github.com:org/guardkit.git"),
                mock.Mock(returncode=1, stdout=""),  # check-ignore fails
            ]
            enabled = sdk_debug.preservation_enabled_for_repo(repo_root)

        # ASSERT: capture NOT enabled
        assert enabled is False
        # WARNING should name keep-out-of-git as failed prerequisite
        assert any("gitignore" in rec.message.lower() or "keep-out-of-git" in rec.message.lower() for rec in caplog.records)

    def test_allowlisted_repo_captures_with_guards_green(
        self, monkeypatch: MonkeyPatch, tmp_path: Path
    ) -> None:
        """Allowlisted repo with both guards green → capture activates."""
        # ARRANGE
        repo_root = tmp_path / "guardkit"
        repo_root.mkdir()
        monkeypatch.delenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", raising=False)
        # Valid caps
        monkeypatch.setenv("GUARDKIT_SDK_DEBUG_PER_TURN_CAP", "20000000")
        monkeypatch.setenv("GUARDKIT_SDK_DEBUG_PER_TASK_CAP", "200000000")

        # ACT: both guards pass
        with mock.patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                mock.Mock(returncode=0, stdout="origin\tgit@github.com:org/guardkit.git"),
                mock.Mock(returncode=0, stdout=""),  # check-ignore passes
            ]
            enabled = sdk_debug.preservation_enabled_for_repo(repo_root)

        # ASSERT: capture enabled
        assert enabled is True
