"""Tests for the start-up-check gate wrapper (``boot_smoke_gate``).

In plain words: these tests check the piece that decides WHICH copy of the
repository's ``.guardkit/seam-checks.yaml`` is used, runs the checks in it, and
decides whether a failure is allowed to stop the build (by default it is not).

The rule that matters most here: only the copy committed BEFORE the build
started is ever read or run. A build agent writes to the working files, and one
of the kinds a declaration may contain (``kind: command``) names a command line
that gets executed — so a declaration the build itself wrote must stay inert.
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

#: A declaration whose only check runs a command line.
MARKER_FILENAME = "the-build-made-guardkit-run-this.txt"
COMMAND_DECLARATION = f"""
version: 1
boot_smoke:
  - id: runs-a-command-line
    kind: command
    target: touch {MARKER_FILENAME}
    expected_exit: 0
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


def _init_repo(root: Path) -> None:
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")


def _init_repo_with_declaration(root: Path) -> None:
    """A git repo whose ``main`` branch already carries the declaration."""
    _init_repo(root)
    _write(root, ".guardkit/seam-checks.yaml", DECLARATION)
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "declare start-up checks")


def _init_repo_without_declaration(root: Path) -> None:
    """A git repo that declares nothing — the state before a build adds a file."""
    _init_repo(root)
    _write(root, "README.md", "a repository with no start-up checks\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-m", "no start-up checks declared")


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


def test_a_declaration_only_in_the_working_files_governs_nothing(
    tmp_path: Path,
) -> None:
    """The build can write the file; it must not thereby arm the gate."""
    _init_repo_without_declaration(tmp_path)
    _write(tmp_path, ".guardkit/seam-checks.yaml", DECLARATION)

    config, source = gate.resolve_governing_config(tmp_path)

    assert source == gate.SOURCE_ADDED_DURING_BUILD
    assert config.has_boot_smoke is False, "nothing from that copy may be run"


def test_committed_declaration_governs(tmp_path: Path) -> None:
    _init_repo_with_declaration(tmp_path)
    config, source = gate.resolve_governing_config(tmp_path)
    assert source == gate.SOURCE_FEATURE_BASE
    assert config.has_boot_smoke is True


def test_the_committed_copy_wins_over_an_edited_working_copy(tmp_path: Path) -> None:
    """An edit made during the build is ignored, and the edit is reported."""
    _init_repo_with_declaration(tmp_path)
    _write_broken_composition(tmp_path)
    # The build blanks the declaration to disarm the gate.
    _write(tmp_path, ".guardkit/seam-checks.yaml", "version: 1\nboot_smoke: []\n")

    outcome = gate.run_final_wave_boot_smoke(tmp_path, env={})

    assert outcome.config_source == gate.SOURCE_FEATURE_BASE
    assert outcome.failed is True, "the committed check still ran, and still failed"
    report = "\n".join(gate.render_report(outcome))
    assert "has been changed in the working files" in report


# --- running the checks -----------------------------------------------------


def test_a_broken_composition_root_is_reported(tmp_path: Path) -> None:
    """The declared check is broken: the report must say so, in words."""
    _init_repo_with_declaration(tmp_path)
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
    _init_repo_with_declaration(tmp_path)
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


# --- the tamper hole: a declaration the build wrote must stay inert ---------


def test_a_declaration_added_during_the_build_runs_nothing_at_all(
    tmp_path: Path,
) -> None:
    """Not "runs but cannot block" — runs NOTHING. Spec §1.3.

    ``kind: command`` executes the command line it names. The command declared
    here creates a file; the proof it never ran is that the file is absent.
    """
    _init_repo_without_declaration(tmp_path)
    _write(tmp_path, ".guardkit/seam-checks.yaml", COMMAND_DECLARATION)

    outcome = gate.run_final_wave_boot_smoke(
        tmp_path, env={gate.BLOCKING_ENV_VAR: "1"}
    )

    assert not (tmp_path / MARKER_FILENAME).exists()
    assert outcome.config_source == gate.SOURCE_ADDED_DURING_BUILD
    assert outcome.result.ran is False
    assert outcome.result.entries == []
    assert outcome.failed is False
    assert outcome.blocks_build is False


def test_a_declaration_added_during_the_build_is_reported_to_the_operator(
    tmp_path: Path,
) -> None:
    _init_repo_without_declaration(tmp_path)
    _write(tmp_path, ".guardkit/seam-checks.yaml", DECLARATION)

    outcome = gate.run_final_wave_boot_smoke(tmp_path, env={})
    report = "\n".join(gate.render_report(outcome))

    assert "NOTHING in it was run" in report
    assert "next build" in report
    # The difference from the committed copy is named in plain words, not
    # in the internal label ("working_tree").
    assert "in the working files" in report
    assert "working_tree" not in report


def test_repo_without_a_declaration_gets_a_nudge(tmp_path: Path) -> None:
    outcome = gate.run_final_wave_boot_smoke(tmp_path, env={})
    assert outcome.declared is False
    assert outcome.result.ran is False
    assert "seam-checks.yaml" in "\n".join(gate.render_report(outcome))


def test_the_report_never_shows_an_internal_label_to_a_person(
    tmp_path: Path,
) -> None:
    """Every line an operator reads is plain English, with no snake_case names."""
    _init_repo_with_declaration(tmp_path)
    _write_broken_composition(tmp_path)
    _write(tmp_path, ".guardkit/seam-checks.yaml", DECLARATION + "\n# edited\n")

    report = gate.render_report(gate.run_final_wave_boot_smoke(tmp_path, env={}))

    for label in ("working_tree", "committed_wave", "feature_base", "CONFIG_TAMPER"):
        assert label not in "\n".join(report), label
