"""Tests for secret redaction in sdk_debug message streams (TASK-OBS-C440).

Validates that SecretRedactor is applied to all sdk_debug write paths:
- preserve_prompt (prompt.txt, options.json)
- preserve_event (messages.jsonl)
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from unittest import mock

import pytest

from guardkit.orchestrator.sdk_debug import (
    _REDACTION_FAILED_MARKER,
    preserve_event,
    preserve_prompt,
)


class TestPromptRedaction:
    """Test redaction in preserve_prompt (prompt.txt, options.json)."""

    def test_planted_secrets_redacted_in_prompt_txt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-1: Planted secrets in prompt.txt are redacted."""
        # Enable preservation
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        # Plant secrets in prompt
        prompt_with_secrets = """
        You are a helpful assistant.
        Use this API key: sk-abc123456789012345
        And this token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
        Password: PASSWORD=secret123
        """

        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="player",
            prompt=prompt_with_secrets,
            options=None,
        )

        assert debug_dir is not None
        prompt_file = debug_dir / "prompt.txt"
        assert prompt_file.exists()

        content = prompt_file.read_text()

        # All secrets must be redacted
        assert "sk-abc123456789012345" not in content
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in content
        assert "secret123" not in content
        assert "[REDACTED]" in content

    def test_planted_secrets_redacted_in_options_json(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-1: Planted secrets in options.json are redacted."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        # Plant secrets in options
        options_with_secrets = {
            "api_key": "sk-xyz987654321098765",
            "aws_key": "AKIAIOSFODNN7EXAMPLE",
            "token": "Bearer my_secret_token_12345",
            "password": "PASS=my_password",
        }

        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="player",
            prompt="normal prompt",
            options=options_with_secrets,
        )

        assert debug_dir is not None
        options_file = debug_dir / "options.json"
        assert options_file.exists()

        content = options_file.read_text()

        # All secrets must be redacted
        assert "sk-xyz987654321098765" not in content
        assert "AKIAIOSFODNN7EXAMPLE" not in content
        assert "my_secret_token_12345" not in content
        assert "my_password" not in content
        assert "[REDACTED]" in content

    def test_non_secret_content_preserved_in_prompt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-2: Non-secret content is preserved byte-for-byte."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        # Clean prompt with no secrets
        clean_prompt = """
        You are a helpful assistant.
        Process this data: {"name": "test", "value": 42}
        Use this function: process_data(input)
        """

        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="player",
            prompt=clean_prompt,
            options=None,
        )

        assert debug_dir is not None
        prompt_file = debug_dir / "prompt.txt"

        # Content should be identical (redactor passes through non-secrets)
        assert prompt_file.read_text() == clean_prompt

    def test_redaction_failure_yields_marker_in_prompt(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-3: Forced redaction failure yields [REDACTION-FAILED] marker."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        # Mock redactor to raise exception
        with mock.patch(
            "guardkit.orchestrator.sdk_debug._get_redactor"
        ) as mock_get_redactor:
            mock_redactor = mock.Mock()
            mock_redactor.redact.side_effect = RuntimeError("Redaction failed")
            mock_get_redactor.return_value = mock_redactor

            debug_dir = preserve_prompt(
                workspace_root=tmp_path,
                task_id="TASK-TEST",
                turn=1,
                role="player",
                prompt="test prompt with sk-secret123",
                options={"key": "value"},
            )

        assert debug_dir is not None
        prompt_file = debug_dir / "prompt.txt"
        options_file = debug_dir / "options.json"

        # Both files should contain the failure marker, NOT the raw content
        assert prompt_file.read_text() == _REDACTION_FAILED_MARKER
        assert options_file.read_text() == _REDACTION_FAILED_MARKER
        assert "sk-secret123" not in prompt_file.read_text()
        assert "value" not in options_file.read_text()


class TestEventRedaction:
    """Test redaction in preserve_event (messages.jsonl)."""

    def test_planted_secrets_redacted_in_messages_jsonl(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-1: Planted secrets in messages.jsonl are redacted."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        # First preserve prompt to create debug_dir
        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="player",
            prompt="test",
            options=None,
        )

        # Create event with planted secrets
        event_with_secrets = {
            "type": "ToolUseBlock",
            "cmd": "export API_KEY=sk-planted_secret_abc123",
            "output": "AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE",
            "token": "Bearer token_xyz_987654",
        }

        preserve_event(debug_dir, event_with_secrets)

        messages_file = debug_dir / "messages.jsonl"  # type: ignore
        assert messages_file.exists()

        content = messages_file.read_text()

        # All secrets must be redacted
        assert "sk-planted_secret_abc123" not in content
        assert "AKIAIOSFODNN7EXAMPLE" not in content
        assert "token_xyz_987654" not in content
        assert "[REDACTED]" in content

    def test_non_secret_content_preserved_in_messages(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-2: Non-secret event content is preserved in messages."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="player",
            prompt="test",
            options=None,
        )

        # Clean event with no secrets - use specific strings to verify preservation
        clean_event = {
            "tool_name": "Read",
            "result": "File content here with special chars: @#$%",
            "count": 42,
        }

        preserve_event(debug_dir, clean_event)

        messages_file = debug_dir / "messages.jsonl"  # type: ignore
        content = messages_file.read_text()

        # Non-secret content should be preserved exactly
        assert "Read" in content
        assert "File content here with special chars: @#$%" in content
        assert "42" in content
        # Should not contain redaction marker when there are no secrets
        assert "[REDACTED]" not in content

    def test_redaction_failure_yields_marker_in_messages(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-3: Forced redaction failure yields [REDACTION-FAILED] marker."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="player",
            prompt="test",
            options=None,
        )

        # Mock redactor to raise exception
        with mock.patch(
            "guardkit.orchestrator.sdk_debug._get_redactor"
        ) as mock_get_redactor:
            mock_redactor = mock.Mock()
            mock_redactor.redact.side_effect = RuntimeError("Redaction failed")
            mock_get_redactor.return_value = mock_redactor

            event = {"type": "Test", "secret": "sk-secret123"}
            preserve_event(debug_dir, event)

        messages_file = debug_dir / "messages.jsonl"  # type: ignore
        content = messages_file.read_text()

        # Should contain the failure marker, NOT the raw secret
        assert content.strip() == _REDACTION_FAILED_MARKER.rstrip("\n")
        assert "sk-secret123" not in content


class TestCoachEvidenceUntouched:
    """Test that Coach-facing evidence files are untouched (AC-4)."""

    def test_player_turn_json_not_redacted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-4: player_turn_N.json is NOT redacted by this task."""
        # This is a pin test - sdk_debug redaction should not touch these files
        # The files are in .guardkit/autobuild/<task_id>/ not sdk_debug/

        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        # Create a mock player_turn file with a secret
        autobuild_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-TEST"
        autobuild_dir.mkdir(parents=True, exist_ok=True)

        player_turn_file = autobuild_dir / "player_turn_1.json"
        player_turn_data = {
            "task_id": "TASK-TEST",
            "turn": 1,
            "secret_in_output": "sk-should_stay_raw",
        }
        player_turn_file.write_text(json.dumps(player_turn_data, indent=2))

        # Now trigger sdk_debug preservation
        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="player",
            prompt="test",
            options=None,
        )

        # Verify sdk_debug files exist
        assert debug_dir is not None

        # Verify player_turn_1.json is untouched (still has the raw secret)
        content = player_turn_file.read_text()
        assert "sk-should_stay_raw" in content
        assert "[REDACTED]" not in content

    def test_task_work_results_json_not_redacted(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-4: task_work_results.json is NOT redacted by this task."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        # Create a mock task_work_results file
        autobuild_dir = tmp_path / ".guardkit" / "autobuild" / "TASK-TEST"
        autobuild_dir.mkdir(parents=True, exist_ok=True)

        results_file = autobuild_dir / "task_work_results.json"
        results_data = {
            "tests_passed": True,
            "secret_in_evidence": "Bearer raw_token_12345",
        }
        results_file.write_text(json.dumps(results_data, indent=2))

        # Trigger sdk_debug preservation
        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="player",
            prompt="test",
            options=None,
        )

        assert debug_dir is not None

        # Verify task_work_results.json is untouched
        content = results_file.read_text()
        assert "Bearer raw_token_12345" in content
        assert "[REDACTED]" not in content


class TestAllWritePathsCovered:
    """Test that all sdk_debug write paths apply redaction (AC-5)."""

    def test_player_prompt_write_path_redacts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-5: Player prompt preservation path applies redaction."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="player",
            prompt="sk-player_secret",
            options=None,
        )

        assert debug_dir is not None
        content = (debug_dir / "prompt.txt").read_text()
        assert "sk-player_secret" not in content
        assert "[REDACTED]" in content

    def test_coach_prompt_write_path_redacts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-5: Coach prompt preservation path applies redaction."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="coach",
            prompt="sk-coach_secret",
            options=None,
        )

        assert debug_dir is not None
        content = (debug_dir / "prompt.txt").read_text()
        assert "sk-coach_secret" not in content
        assert "[REDACTED]" in content

    def test_coach_test_write_path_redacts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-5: Coach independent test stream preservation applies redaction."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="coach_test",
            prompt="sk-test_secret",
            options=None,
        )

        assert debug_dir is not None
        content = (debug_dir / "prompt.txt").read_text()
        assert "sk-test_secret" not in content
        assert "[REDACTED]" in content

    def test_event_stream_write_path_redacts(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AC-5: Event stream preservation path applies redaction."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="player",
            prompt="test",
            options=None,
        )

        preserve_event(debug_dir, {"secret": "sk-event_secret"})

        content = (debug_dir / "messages.jsonl").read_text()  # type: ignore
        assert "sk-event_secret" not in content
        assert "[REDACTED]" in content


class TestNoRaiseIntoHotPath:
    """Test that redaction failures never raise into the hot path."""

    def test_preserve_prompt_never_raises_on_redaction_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Preservation continues even when redaction fails."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        with mock.patch(
            "guardkit.orchestrator.sdk_debug._get_redactor"
        ) as mock_get_redactor:
            mock_redactor = mock.Mock()
            mock_redactor.redact.side_effect = RuntimeError("Boom")
            mock_get_redactor.return_value = mock_redactor

            # Should not raise
            debug_dir = preserve_prompt(
                workspace_root=tmp_path,
                task_id="TASK-TEST",
                turn=1,
                role="player",
                prompt="test",
                options=None,
            )

        # Still returns a valid debug_dir (degraded but functional)
        assert debug_dir is not None

    def test_preserve_event_never_raises_on_redaction_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Event preservation continues even when redaction fails."""
        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        debug_dir = preserve_prompt(
            workspace_root=tmp_path,
            task_id="TASK-TEST",
            turn=1,
            role="player",
            prompt="test",
            options=None,
        )

        with mock.patch(
            "guardkit.orchestrator.sdk_debug._get_redactor"
        ) as mock_get_redactor:
            mock_redactor = mock.Mock()
            mock_redactor.redact.side_effect = RuntimeError("Boom")
            mock_get_redactor.return_value = mock_redactor

            # Should not raise
            preserve_event(debug_dir, {"test": "data"})

        # File should exist with marker
        messages_file = debug_dir / "messages.jsonl"  # type: ignore
        assert messages_file.exists()


class TestRedactionPerformance:
    """Test that redactor is a cached singleton for performance."""

    def test_redactor_is_cached_singleton(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Redactor instance is reused across calls (not recreated each time)."""
        import guardkit.orchestrator.sdk_debug as sdk_debug_module

        # Reset the global redactor to ensure clean state
        sdk_debug_module._redactor = None

        monkeypatch.setenv("GUARDKIT_AUTOBUILD_PRESERVE_DEBUG", "1")

        with mock.patch(
            "guardkit.orchestrator.sdk_debug.SecretRedactor"
        ) as mock_constructor:
            mock_instance = mock.Mock()
            mock_instance.redact = lambda x: x
            mock_constructor.return_value = mock_instance

            # Make multiple calls
            preserve_prompt(
                workspace_root=tmp_path,
                task_id="TASK-1",
                turn=1,
                role="player",
                prompt="test1",
                options=None,
            )

            preserve_prompt(
                workspace_root=tmp_path,
                task_id="TASK-2",
                turn=1,
                role="player",
                prompt="test2",
                options=None,
            )

        # SecretRedactor should only be constructed once
        assert mock_constructor.call_count == 1
