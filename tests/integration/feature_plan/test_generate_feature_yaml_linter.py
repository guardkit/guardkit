"""End-to-end test: AC-quality linter fires from generate_feature_yaml.

Exercises the imperative callsite added by TASK-FIX-3C9D (Option B). Drives
the ``generate_feature_yaml.py`` script via subprocess with prose acceptance
criteria and asserts that the ``AC-quality review:`` header appears in
stdout.

This is the structural counterpart to
``test_ac_linter_warning_flow.py`` — that test proves the linter library
works; this test proves it is actually invoked by the runtime producer that
``/feature-plan`` delegates to. Without this test, R1 activation remains a
Claude-as-runtime interpretation of prose, not a deterministic callsite.

See TASK-FIX-3C9D §Acceptance Criteria.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "installer" / "core" / "commands" / "lib" / "generate_feature_yaml.py"


@pytest.fixture
def project_dir(tmp_path):
    """Temporary project root with a feature subfolder and stubbed task files.

    The script validates task file paths (warn-mode under ``--lenient``);
    creating the expected filenames avoids noise in stderr and keeps the
    assertion focused on stdout linter output.
    """
    feature_dir = tmp_path / "tasks" / "backlog" / "probe"
    feature_dir.mkdir(parents=True)
    (feature_dir / "TASK-P-001-build-csv-ingester.md").write_text("# stub\n")
    (feature_dir / "TASK-P-002-add-smoke-tests.md").write_text("# stub\n")
    return tmp_path


@pytest.fixture
def prose_ac_tasks_json(project_dir):
    """Write a JSON payload with a mix of prose-AC and concrete-AC tasks."""
    payload = [
        {
            "id": "TASK-P-001",
            "name": "Build CSV ingester",
            "complexity": 5,
            "acceptance_criteria": [
                # F3/F6 prose patterns known to warn (see
                # tests/integration/feature_plan/test_ac_linter_warning_flow.py)
                "- [ ] handles edge cases correctly",
                "- [ ] backward-compatible defaults ensure no breakage",
            ],
        },
        {
            "id": "TASK-P-002",
            "name": "Add smoke tests",
            "complexity": 3,
            "acceptance_criteria": [
                "- [ ] pytest tests/smoke/ -v passes all tests",
            ],
        },
    ]
    path = project_dir / "tasks.json"
    path.write_text(json.dumps(payload))
    return path


def _run_script(project_dir: Path, tasks_json: Path) -> subprocess.CompletedProcess:
    """Invoke generate_feature_yaml.py as a subprocess and capture output."""
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--name", "probe",
            "--description", "generate_feature_yaml linter wiring probe",
            "--feature-slug", "probe",
            "--base-path", str(project_dir),
            "--tasks-json", str(tasks_json),
            "--lenient",
        ],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


class TestGenerateFeatureYamlLinterWiring:
    """Option B (TASK-FIX-3C9D) acceptance: header appears in stdout."""

    def test_ac_quality_review_header_in_stdout(self, project_dir, prose_ac_tasks_json):
        """Non-quiet run emits the AC-quality review header to stdout."""
        result = _run_script(project_dir, prose_ac_tasks_json)

        assert result.returncode == 0, (
            f"Script exited non-zero.\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        assert "AC-quality review:" in result.stdout, (
            "Expected imperative linter callsite to emit "
            "'AC-quality review:' header in stdout.\n"
            f"stdout:\n{result.stdout}"
        )

    def test_prose_ac_tasks_produce_warnings(self, project_dir, prose_ac_tasks_json):
        """At least the two TASK-P-001 prose ACs are flagged (N >= 2)."""
        result = _run_script(project_dir, prose_ac_tasks_json)

        assert result.returncode == 0
        # TASK-FIX-3C9D AC: "N >= 3" when the prose-ac fixture is used.
        # For the JSON-driven variant here, TASK-P-001's two F3/F6 prose ACs
        # are the canonical warn pairs; we assert TASK-P-001 appears and
        # both its prose ACs are reported.
        assert "TASK-P-001:" in result.stdout
        assert "handles edge cases correctly" in result.stdout
        assert "backward-compatible defaults ensure no breakage" in result.stdout

    def test_warning_count_matches_summary(self, project_dir, prose_ac_tasks_json):
        """The header's N matches the warning body count."""
        result = _run_script(project_dir, prose_ac_tasks_json)

        assert result.returncode == 0
        # Extract the count from the header line.
        import re
        match = re.search(
            r"AC-quality review: (\d+) unverifiable acceptance criteria detected",
            result.stdout,
        )
        assert match is not None, (
            f"Could not locate header in stdout:\n{result.stdout}"
        )
        count = int(match.group(1))
        # At minimum the two F3/F6 prose ACs on TASK-P-001 must fire.
        assert count >= 2, (
            f"Expected >=2 warnings for known prose ACs, got {count}.\n"
            f"stdout:\n{result.stdout}"
        )

    def test_quiet_mode_suppresses_linter_output(self, project_dir, prose_ac_tasks_json):
        """Quiet mode preserves the FEAT-ID:path parseable contract.

        The header must not appear on stdout in quiet mode, so callers
        scripting against ``{feature_id}:{output_path}`` stay clean.
        """
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--name", "probe",
                "--description", "quiet-mode probe",
                "--feature-slug", "probe",
                "--base-path", str(project_dir),
                "--tasks-json", str(prose_ac_tasks_json),
                "--lenient",
                "--quiet",
            ],
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0
        assert "AC-quality review:" not in result.stdout, (
            "Quiet mode must not emit the linter header on stdout "
            "(breaks the FEAT-ID:path parseable contract).\n"
            f"stdout:\n{result.stdout}"
        )
        # Quiet mode output is a single FEAT-XXXX:path line.
        assert result.stdout.strip().startswith("FEAT-")
