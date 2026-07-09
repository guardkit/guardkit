"""`guardkit qa live-gate` CLI (WS2 B3): stdout envelope + verdict exit codes."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import yaml
from click.testing import CliRunner

from guardkit.cli.qa import qa

_PASS_BAR = textwrap.dedent(
    """\
    format_version: "2.0"
    task_id: T-1
    registered_at: {sha: abcd, date: "2026-07-05"}
    auth_surface_bearing: true
    preconditions: [suite_green_vs_ledger]
    criteria:
      - {id: C1, text: "shows real name", class: machine, evidence_kind: screenshot}
    negative_paths: [wrong_credential, anonymous_deep_link, post_logout_401, unauthorized_403_ui, dependency_down_degradation]
    """
)


def _build_repo(tmp_path: Path) -> Path:
    (tmp_path / "qa" / "gates").mkdir(parents=True)
    (tmp_path / "qa" / "pass-bar-T-1.yaml").write_text(_PASS_BAR)
    (tmp_path / "qa" / "gates" / "g1.py").write_text("print('x')")
    registry = {
        "format_version": "1.0",
        "gates": [
            {
                "id": "g1",
                "path": "qa/gates/g1.py",
                "target": {"base_url_env": "BASE", "environment_id": "env"},
                "pass_bar_ref": "qa/pass-bar-T-1.yaml",
                "evidence_dir_pattern": "qa/gates/evidence-{date}/shots-g1",
            }
        ],
    }
    (tmp_path / "qa" / "gates" / "registry.yaml").write_text(yaml.safe_dump(registry))
    return tmp_path


def test_live_gate_emits_envelope_and_environment_fail_exit_code(tmp_path):
    repo = _build_repo(tmp_path)
    result = CliRunner().invoke(
        qa,
        ["live-gate", "--feature", "FEAT-X", "--target", "gb10", "--repo", str(repo)],
    )
    # unconfigured seams → environment_fail → exit 4
    assert result.exit_code == 4, result.output
    envelope = json.loads(result.output)
    assert envelope["verdict"] == "environment_fail"
    assert envelope["feature_id"] == "FEAT-X"
    assert envelope["format_version"] == "1.0"


def test_live_gate_missing_registry_is_loud_exit_2(tmp_path):
    result = CliRunner().invoke(
        qa,
        ["live-gate", "--feature", "FEAT-X", "--target", "gb10", "--repo", str(tmp_path)],
    )
    assert result.exit_code == 2
    assert "could not run" in result.output


def test_live_gate_unknown_gate_id_is_loud_exit_2(tmp_path):
    repo = _build_repo(tmp_path)
    result = CliRunner().invoke(
        qa,
        ["live-gate", "--feature", "F", "--target", "gb10", "--repo", str(repo), "--gates", "nope"],
    )
    assert result.exit_code == 2
    assert "unknown gate id" in result.output


def test_live_gate_campaign_writes_ledger_and_stamps_ref(tmp_path):
    # A single (unattended) run under --campaign is recorded as attempt 1 of an
    # F9 ledger, and the envelope's attempts_ledger_ref is stamped. Here the run
    # is a pre-flight environment_fail (no reds) → closes trivially, verdict
    # preserved, exit 4.
    repo = _build_repo(tmp_path)
    result = CliRunner().invoke(
        qa,
        ["live-gate", "--feature", "FEAT-X", "--target", "gb10", "--repo", str(repo), "--campaign"],
    )
    assert result.exit_code == 4, result.output
    envelope = json.loads(result.output)
    assert envelope["verdict"] == "environment_fail"
    assert envelope["attempts_ledger_ref"] == "qa/attempts-FEAT-X.yaml"
    ledger = tmp_path / "qa" / "attempts-FEAT-X.yaml"
    assert ledger.is_file()
    parsed = yaml.safe_load(ledger.read_text())
    assert parsed["campaign"] == "FEAT-X"
    assert len(parsed["attempts"]) == 1
    assert parsed["attempts"][0]["n"] == 1
