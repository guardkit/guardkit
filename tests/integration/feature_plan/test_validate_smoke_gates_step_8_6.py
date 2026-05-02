"""End-to-end: ``/feature-plan`` Step 8.6 surfaces hand-injected smoke-gate path errors.

Drives the ``generate_feature_yaml.py`` script via subprocess in
``--validate-smoke-gates`` mode against a fixture workspace whose feature
YAML carries a hand-injected ``smoke_gates.command`` referencing a
non-existent test path. Asserts the same shape Step 8.6 of
``feature-plan.md`` instructs Claude to follow:

- non-zero exit
- the bad path appears on stderr
- the discovered test roots appear on stderr (so the agent can pick one)

Structural twin of ``test_generate_feature_yaml_nudges.py`` — that test
proves R3's *nudge* fires from the producer; this test proves R3's
*validator* fires from the producer when the agent acts on the nudge but
picks the wrong path. Together they close the loop: nudge → author edit
→ validator catches typos before ``/feature-build`` boots a worktree.

See TASK-FPSG-002 §Acceptance Criteria, feature-plan.md §Step 8.6, and
the parent defect TASK-REV-DEA8 (forge run, 2026-05-02).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from textwrap import dedent

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = (
    REPO_ROOT
    / "installer"
    / "core"
    / "commands"
    / "lib"
    / "generate_feature_yaml.py"
)


@pytest.fixture
def forge_shaped_repo(tmp_path: Path) -> Path:
    """tmp_path repo modelling forge's tests/ layout sans the hallucinated dir.

    ``tests/cli`` is intentionally absent — that is the path TASK-REV-DEA8
    captured a ``/feature-plan``-driven agent inventing for a forge feature.
    The validator must surface its absence and list the real roots so the
    agent can fix the YAML in one edit.
    """
    (tmp_path / "tests" / "forge").mkdir(parents=True)
    (tmp_path / "tests" / "integration").mkdir(parents=True)
    (tmp_path / "tests" / "unit").mkdir(parents=True)
    (tmp_path / "tests" / "bdd").mkdir(parents=True)
    return tmp_path


def _write_feature_yaml(repo: Path, feature_id: str, smoke_gates_block: str) -> Path:
    """Write a minimal feature YAML with the supplied smoke_gates block."""
    body = dedent(
        f"""\
        id: {feature_id}
        name: Step 8.6 fixture
        description: Fixture exercising hand-injected smoke_gates validation.
        created: 2026-05-02T15:00:00Z
        complexity: 4
        estimated_tasks: 1
        tasks:
          - id: TASK-S86-T1
            file_path: tasks/in_progress/TASK-S86-T1.md
            name: Fixture task
            complexity: 3
            implementation_mode: task-work
            estimated_minutes: 30
        orchestration:
          parallel_groups:
            - [TASK-S86-T1]
          estimated_duration_minutes: 30
          recommended_parallel: 1
        """
    )
    body += smoke_gates_block
    features_dir = repo / ".guardkit" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    path = features_dir / f"{feature_id}.yaml"
    path.write_text(body, encoding="utf-8")
    return path


def _run_validator(repo: Path, feature_id: str, *, quiet: bool = False) -> subprocess.CompletedProcess:
    """Invoke generate-feature-yaml --validate-smoke-gates as a subprocess.

    Mirrors what feature-plan.md Step 8.6 instructs Claude to execute.
    """
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--validate-smoke-gates",
        "--feature-id",
        feature_id,
        "--base-path",
        str(repo),
    ]
    if quiet:
        cmd.append("--quiet")
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        check=False,
    )


# ---------------------------------------------------------------------------
# Step 8.6 — primary contract: bad path → non-zero exit + actionable stderr
# ---------------------------------------------------------------------------


def test_step_8_6_rejects_hand_injected_bad_path(forge_shaped_repo: Path):
    """The TASK-REV-DEA8 reproduction: ``tests/cli`` in a forge-shaped repo.

    Mirrors the feature-plan.md Step 8.6 example exactly: a feature YAML
    whose smoke_gates was added after generate-feature-yaml ran (so step 8
    didn't auto-generate it) carries a path the agent invented from
    another repo's layout. The validator must catch this before
    ``/feature-build`` runs Wave 1.
    """
    smoke_gates = dedent(
        """\
        smoke_gates:
          after_wave: all
          command: |
            set -e
            pytest tests/cli tests/forge -x
          expected_exit: 0
          timeout: 120
        """
    )
    _write_feature_yaml(forge_shaped_repo, "FEAT-S86A", smoke_gates)

    result = _run_validator(forge_shaped_repo, "FEAT-S86A")

    assert result.returncode != 0, (
        f"Validator should fail for hand-injected bad path. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    # The bad path lands on stderr so feature-plan.md Step 8.6 can
    # display it inline.
    assert "tests/cli" in result.stderr
    # Discovered roots tell the agent what to substitute. All four real
    # tests/ subdirs in the fixture must surface.
    assert "tests/forge" in result.stderr
    assert "tests/integration" in result.stderr
    assert "tests/unit" in result.stderr
    assert "tests/bdd" in result.stderr
    # Repo root surfaces so the agent can disambiguate worktree-vs-main.
    assert str(forge_shaped_repo) in result.stderr


# ---------------------------------------------------------------------------
# Step 8.6 — escape hatches: don't punish features that don't need a check
# ---------------------------------------------------------------------------


def test_step_8_6_passes_when_all_paths_exist(forge_shaped_repo: Path):
    """All injected paths exist → exit 0, the OK line appears on stdout.

    The OK line is the deterministic signal feature-plan.md Step 8.6
    relies on to "continue to step 9". Without it, the step would have
    no way to distinguish "validator ran clean" from "validator no-oped".
    """
    smoke_gates = dedent(
        """\
        smoke_gates:
          after_wave: all
          command: |
            set -e
            pytest tests/forge tests/integration -x
          expected_exit: 0
          timeout: 120
        """
    )
    _write_feature_yaml(forge_shaped_repo, "FEAT-S86B", smoke_gates)

    result = _run_validator(forge_shaped_repo, "FEAT-S86B")

    assert result.returncode == 0, (
        f"Validator should pass when all paths exist. "
        f"stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "smoke_gates.command paths OK" in result.stdout
    assert result.stderr == ""


def test_step_8_6_quiet_mode_silent_on_success(forge_shaped_repo: Path):
    """``--quiet`` suppresses the OK line so CI logs stay clean.

    Honours the same suppression contract as the AC-quality / BDD-oracle
    / smoke-gates nudges (per AC: "same suppression rules").
    """
    smoke_gates = dedent(
        """\
        smoke_gates:
          after_wave: all
          command: pytest tests/forge -x
          expected_exit: 0
          timeout: 120
        """
    )
    _write_feature_yaml(forge_shaped_repo, "FEAT-S86C", smoke_gates)

    result = _run_validator(forge_shaped_repo, "FEAT-S86C", quiet=True)

    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""
