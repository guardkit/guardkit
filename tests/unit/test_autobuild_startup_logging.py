"""
Startup-logging tests for AutoBuildOrchestrator (TASK-FIX-7A01).

Validates that AutoBuildOrchestrator.__init__ emits exactly one INFO-level
`claude-agent-sdk version: ...` line at startup, which is the diagnostic
anchor for SDK-skew incidents (e.g. Run 2 of FEAT-FORGE-002 where the
installed SDK could not parse `rate_limit_event`).
"""

import logging
import re
from pathlib import Path
from unittest.mock import patch

import pytest

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator


# Matches either:
#   claude-agent-sdk version: 0.1.49
#   claude-agent-sdk version: 0.1.66.dev0+g1234
#   claude-agent-sdk version: unknown (SDK not importable: ...)
SDK_VERSION_LINE = re.compile(
    r"claude-agent-sdk version: "
    r"(?:unknown \(SDK not importable: .+\)|\d+\.\d+\.\d+[^\s]*)"
)

# Narrower matcher used by the "known-good environment" test — must be a
# resolved semver, not the fallback sentinel.
SDK_SEMVER_LINE = re.compile(r"^claude-agent-sdk version: \d+\.\d+\.\d+[^\s]*$")


def _init_orchestrator() -> None:
    """Construct an orchestrator with checkpoints disabled (no git touch)."""
    AutoBuildOrchestrator(
        repo_root=Path.cwd(),
        max_turns=5,
        enable_checkpoints=False,
    )


class TestStartupSdkVersionLog:
    """AutoBuildOrchestrator.__init__ must log the claude-agent-sdk version."""

    def test_version_line_emitted_on_known_good_env(self, caplog):
        """
        AC: a test that parses the startup log produced by the orchestrator
        on a known-good environment finds a line matching
        `claude-agent-sdk version: <semver>`.
        """
        with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.autobuild"):
            _init_orchestrator()

        semver_lines = [
            record.getMessage()
            for record in caplog.records
            if SDK_SEMVER_LINE.match(record.getMessage())
        ]
        assert len(semver_lines) == 1, (
            f"Expected exactly one semver SDK version line, got {len(semver_lines)}. "
            f"All captured messages: {[r.getMessage() for r in caplog.records]}"
        )

    def test_version_line_emitted_exactly_once(self, caplog):
        """Two init calls must emit two (one-per-init) version lines, not zero or one."""
        with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.autobuild"):
            _init_orchestrator()
            _init_orchestrator()

        matches = [
            record.getMessage()
            for record in caplog.records
            if SDK_VERSION_LINE.search(record.getMessage())
        ]
        assert len(matches) == 2, (
            f"Expected 2 version lines across 2 inits, got {len(matches)}: {matches}"
        )

    def test_fallback_line_emitted_when_metadata_missing(self, caplog):
        """
        If importlib.metadata.version raises (package not importable / metadata
        missing), the orchestrator must still emit the single version line
        in its fallback form so the diagnostic anchor is always present.
        """
        with patch(
            "importlib.metadata.version",
            side_effect=Exception("simulated: No package metadata was found for claude-agent-sdk"),
        ):
            with caplog.at_level(logging.INFO, logger="guardkit.orchestrator.autobuild"):
                _init_orchestrator()

        fallback_lines = [
            record.getMessage()
            for record in caplog.records
            if record.getMessage().startswith("claude-agent-sdk version: unknown")
        ]
        assert len(fallback_lines) == 1, (
            f"Expected exactly one fallback line, got {len(fallback_lines)}. "
            f"All captured messages: {[r.getMessage() for r in caplog.records]}"
        )
        assert "SDK not importable:" in fallback_lines[0], (
            f"Fallback line should mention 'SDK not importable:': {fallback_lines[0]}"
        )
