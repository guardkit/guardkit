"""Tests for the start-up-check gate wrapper (``boot_smoke_gate``).

In plain words: these tests check the piece that decides WHICH copy of the
repository's ``.guardkit/seam-checks.yaml`` is used, runs the checks in it, and
decides whether a failure is allowed to stop the build (by default it is not).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from guardkit.orchestrator import boot_smoke_gate as gate


DECLARATION = """
version: 1
boot_smoke:
  - id: composition-root-constructs
    kind: construct
    target: app.main:create_service
    expect_type: app.service:VoiceService
"""


def _write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _write_broken_composition(root: Path) -> None:
    """A composition root that forgets a required argument (the POC-006 shape)."""
    _write(root, "app/__init__.py", "")
    _write(
        root,
        "app/service.py",
        "class VoiceService:\n"
        "    def __init__(self, audio_client, cache=None):\n"
        "        self.audio_client = audio_client\n",
    )
    _write(
        root,
        "app/main.py",
        "from app.service import VoiceService\n"
        "def create_service():\n"
        "    return VoiceService(cache=None)\n",  # audio_client missing
    )


def _write_working_composition(root: Path) -> None:
    _write(root, "app/__init__.py", "")
    _write(
        root,
        "app/service.py",
        "class VoiceService:\n"
        "    def __init__(self, audio_client=None):\n"
        "        self.audio_client = audio_client\n",
    )
    _write(
        root,
        "app/main.py",
        "from app.service import VoiceService\n"
        "def create_service():\n"
        "    return VoiceService()\n",
    )


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=str(root), check=True, capture_output=True)


def _init_repo_with_declaration(root: Path) -> None:
    """A git repo whose ``main`` branch already carries the declaration."""
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _write(root, ".guardkit/seam-checks.yaml", DECLARATION)
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "declare start-up checks")


# --- the blocking flag ------------------------------------------------------


def test_blocking_is_off_unless_asked_for() -> None:
    assert gate.blocking_requested({}) is False
    assert gate.blocking_requested({gate.BLOCKING_ENV_VAR: ""}) is False
    assert gate.blocking_requested({gate.BLOCKING_ENV_VAR: "0"}) is False
    assert gate.blocking_requested({gate.BLOCKING_ENV_VAR: "maybe"}) is False


def test_blocking_accepts_the_documented_values() -> None:
    for value in ("1", "true", "TRUE", "yes", "on"):
        assert gate.blocking_requested({gate.BLOCKING_ENV_VAR: value}) is True


# --- which copy of the declaration governs ---------------------------------


def test_no_declaration_anywhere_is_reported_as_none(tmp_path: Path) -> None:
    config, source = gate.resolve_governing_config(tmp_path)
    assert source == gate.SOURCE_NONE
    assert config.has_boot_smoke is False


def test_declaration_only_in_the_working_tree_is_marked_as_such(tmp_path: Path) -> None:
    _write(tmp_path, ".guardkit/seam-checks.yaml", DECLARATION)
    config, source = gate.resolve_governing_config(tmp_path)
    assert source == gate.SOURCE_WORKING_TREE
    assert config.has_boot_smoke is True


def test_committed_declaration_governs(tmp_path: Path) -> None:
    _init_repo_with_declaration(tmp_path)
    config, source = gate.resolve_governing_config(tmp_path)
    assert source == gate.SOURCE_FEATURE_BASE
    assert config.has_boot_smoke is True


# --- running the checks -----------------------------------------------------


def test_a_broken_composition_root_is_reported(tmp_path: Path) -> None:
    """The declared seam is broken: the report must say so, in words."""
    _write(tmp_path, ".guardkit/seam-checks.yaml", DECLARATION)
    _write_broken_composition(tmp_path)

    outcome = gate.run_final_wave_boot_smoke(tmp_path, env={})

    assert outcome.declared is True
    assert outcome.failed is True, [e.to_dict() for e in outcome.result.entries]
    detail = outcome.result.entries[0].detail
    assert "TypeError" in detail or "argument" in detail

    report = "\n".join(gate.render_report(outcome))
    assert "composition-root-constructs" in report
    assert "FAILED" in report

    summary = gate.failure_summary(outcome)
    assert "composition-root-constructs" in summary


def test_a_working_composition_root_passes(tmp_path: Path) -> None:
    _write(tmp_path, ".guardkit/seam-checks.yaml", DECLARATION)
    _write_working_composition(tmp_path)

    outcome = gate.run_final_wave_boot_smoke(tmp_path, env={})

    assert outcome.failed is False
    assert outcome.blocks_build is False


# --- advisory first ---------------------------------------------------------


def test_failure_does_not_block_by_default(tmp_path: Path) -> None:
    _init_repo_with_declaration(tmp_path)
    _write_broken_composition(tmp_path)

    outcome = gate.run_final_wave_boot_smoke(tmp_path, env={})

    assert outcome.failed is True
    assert outcome.blocks_build is False
    assert gate.BLOCKING_ENV_VAR in "\n".join(gate.render_report(outcome))


def test_failure_blocks_when_the_flag_is_set(tmp_path: Path) -> None:
    _init_repo_with_declaration(tmp_path)
    _write_broken_composition(tmp_path)

    outcome = gate.run_final_wave_boot_smoke(
        tmp_path, env={gate.BLOCKING_ENV_VAR: "1"}
    )

    assert outcome.failed is True
    assert outcome.blocks_build is True


def test_a_declaration_added_during_the_build_can_never_block(tmp_path: Path) -> None:
    """Anti-tamper: only the copy committed before the build may stop it."""
    _write(tmp_path, ".guardkit/seam-checks.yaml", DECLARATION)
    _write_broken_composition(tmp_path)

    outcome = gate.run_final_wave_boot_smoke(
        tmp_path, env={gate.BLOCKING_ENV_VAR: "1"}
    )

    assert outcome.config_source == gate.SOURCE_WORKING_TREE
    assert outcome.failed is True
    assert outcome.blocks_build is False


def test_repo_without_a_declaration_gets_a_nudge(tmp_path: Path) -> None:
    outcome = gate.run_final_wave_boot_smoke(tmp_path, env={})
    assert outcome.declared is False
    assert outcome.result.ran is False
    assert "seam-checks.yaml" in "\n".join(gate.render_report(outcome))
