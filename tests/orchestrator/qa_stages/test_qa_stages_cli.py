"""CLI tests for `guardkit qa mutate` and `guardkit qa probe-boundaries` (B6).

Advisory-by-default (exit 0 with findings filed); ``--strict`` flips to a
non-zero gate exit. These are the CLI-level proof of the two B6 gates.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from click.testing import CliRunner

from guardkit.cli.qa import qa

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "qa_stages"
sys.path.insert(0, str(FIXTURES))


def _copy_auth_fixture(tmp_path: Path) -> Path:
    dest = tmp_path / "work"
    shutil.copytree(FIXTURES / "auth_client", dest)
    return dest


# --------------------------------------------------------------------------- #
# qa mutate
# --------------------------------------------------------------------------- #
def test_qa_mutate_advisory_files_survivor_and_exits_zero(tmp_path):
    work = _copy_auth_fixture(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        qa,
        [
            "mutate",
            "--task", "TASK-XXX-YYYY",
            "--repo", str(work),
            "--files", "authclient.py",
            "--test-command", f"{sys.executable} -m pytest -q test_authclient.py",
        ],
    )
    assert result.exit_code == 0, result.output  # advisory — never blocks
    assert "SURVIVOR" in result.output
    filed = list((work / "qa" / "findings").glob("*.md"))
    assert len(filed) == 1
    assert "Blocking:** no" in filed[0].read_text()


def test_qa_mutate_strict_exits_nonzero_on_survivor(tmp_path):
    work = _copy_auth_fixture(tmp_path)
    result = CliRunner().invoke(
        qa,
        [
            "mutate", "--task", "TASK-XXX-YYYY", "--repo", str(work),
            "--files", "authclient.py", "--no-file", "--strict",
            "--test-command", f"{sys.executable} -m pytest -q test_authclient.py",
        ],
    )
    assert result.exit_code == 3, result.output  # strict gate mode


def test_qa_mutate_missing_deliverables_is_loud(tmp_path):
    work = _copy_auth_fixture(tmp_path)
    result = CliRunner().invoke(
        qa,
        ["mutate", "--task", "T", "--repo", str(work), "--files", "",
         "--test-command", "true"],
    )
    assert result.exit_code == 2
    assert "could not run" in result.output


# --------------------------------------------------------------------------- #
# qa probe-boundaries
# --------------------------------------------------------------------------- #
def test_qa_probe_boundaries_advisory_files_leak(tmp_path):
    result = CliRunner().invoke(
        qa,
        [
            "probe-boundaries",
            "--seam", "deploy-envelope",
            "--manifest", str(FIXTURES / "seam_manifest.yaml"),
            "--target", "seam_decoder:LEAKY",
            "--repo", str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.output  # advisory
    assert "raw-error leak" in result.output
    assert list((tmp_path / "qa" / "findings").glob("*.md"))


def test_qa_probe_boundaries_strict_exits_nonzero(tmp_path):
    result = CliRunner().invoke(
        qa,
        ["probe-boundaries", "--seam", "deploy-envelope",
         "--target", "seam_decoder:LEAKY", "--repo", str(tmp_path),
         "--no-file", "--strict"],
    )
    assert result.exit_code == 3, result.output


def test_qa_probe_boundaries_hardened_is_clean(tmp_path):
    result = CliRunner().invoke(
        qa,
        ["probe-boundaries", "--seam", "deploy-envelope",
         "--target", "seam_decoder:HARDENED", "--repo", str(tmp_path), "--strict"],
    )
    assert result.exit_code == 0, result.output
    assert not list((tmp_path / "qa" / "findings").glob("*.md"))


def test_qa_probe_boundaries_unconfigured_target_is_loud_not_green(tmp_path):
    result = CliRunner().invoke(
        qa, ["probe-boundaries", "--seam", "deploy-envelope", "--repo", str(tmp_path)]
    )
    # Honest "not wired" — exit 0 (non-blocking) but a loud message, never a clean pass.
    assert result.exit_code == 0
    assert "not wired" in result.output


def test_qa_probe_boundaries_unknown_seam_id_is_rejected(tmp_path):
    result = CliRunner().invoke(
        qa,
        ["probe-boundaries", "--seam", "no-such-seam",
         "--manifest", str(FIXTURES / "seam_manifest.yaml"),
         "--target", "seam_decoder:LEAKY", "--repo", str(tmp_path)],
    )
    assert result.exit_code == 2
    assert "not in manifest" in result.output
