"""End-to-end test: R2/R3 activation nudges fire from generate_feature_yaml.

Exercises the imperative callsites added by TASK-FIX-RWOP1.2. Drives the
``generate_feature_yaml.py`` script via subprocess against a fixture workspace
where (a) ``features/*.feature`` exists with zero ``@task:<TASK-ID>`` tags
(should fire the R2 BDD-oracle nudge, Step 10.6) and (b) the generated
feature YAML ends up with ``>= 2`` waves and no ``smoke_gates:`` key (should
fire the R3 smoke-gates nudge, Step 10.7).

Structural twin of ``test_generate_feature_yaml_linter.py`` — that test
proves R1's AC linter fires from the producer; this test proves R2/R3 nudges
fire from the same producer. Without this test, R2/R3 activation remains a
Claude-as-runtime interpretation of prose (the runner-without-producer gap
that TASK-REV-RWOP1 identified), not a deterministic callsite.

See TASK-FIX-RWOP1.2 §Acceptance Criteria and feature-plan.md §Step 10.6 /
§Step 10.7.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "installer" / "core" / "commands" / "lib" / "generate_feature_yaml.py"


_FEATURE_FILE_WITHOUT_TASK_TAGS = """\
Feature: Example feature

  @smoke
  Scenario: User signs in with valid credentials
    Given a registered user
    When they submit valid credentials
    Then they land on the dashboard

  Scenario: User signs in with invalid credentials
    Given a registered user
    When they submit invalid credentials
    Then they see an error message
"""


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    """Temporary project root wired to trigger BOTH nudges.

    - ``features/example.feature`` exists with zero ``@task:`` tags
      → triggers Step 10.6 BDD-oracle nudge.
    - Two task files exist with a dependency between them, so the
      generated YAML has ``>= 2`` waves, and the default output
      location has no ``smoke_gates:`` key
      → triggers Step 10.7 smoke-gates nudge.
    """
    feature_dir = tmp_path / "tasks" / "backlog" / "probe"
    feature_dir.mkdir(parents=True)
    (feature_dir / "TASK-P-001-build-thing.md").write_text("# stub\n")
    (feature_dir / "TASK-P-002-add-tests.md").write_text("# stub\n")

    features_dir = tmp_path / "features"
    features_dir.mkdir()
    (features_dir / "example.feature").write_text(_FEATURE_FILE_WITHOUT_TASK_TAGS)
    return tmp_path


@pytest.fixture
def tasks_json(project_dir: Path) -> Path:
    """Two tasks, one depending on the other — guarantees >= 2 waves."""
    payload = [
        {
            "id": "TASK-P-001",
            "name": "Build thing",
            "complexity": 5,
            "acceptance_criteria": [
                "- [ ] pytest tests/ passes",
            ],
        },
        {
            "id": "TASK-P-002",
            "name": "Add tests",
            "complexity": 3,
            "dependencies": ["TASK-P-001"],
            "acceptance_criteria": [
                "- [ ] pytest tests/smoke/ passes",
            ],
        },
    ]
    path = project_dir / "tasks.json"
    path.write_text(json.dumps(payload))
    return path


def _run_script(
    project_dir: Path,
    tasks_json: Path,
    *,
    quiet: bool = False,
) -> subprocess.CompletedProcess:
    """Invoke generate_feature_yaml.py as a subprocess and capture output."""
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--name", "probe",
        "--description", "generate_feature_yaml R2/R3 nudge wiring probe",
        "--feature-slug", "probe",
        "--base-path", str(project_dir),
        "--tasks-json", str(tasks_json),
        "--lenient",
    ]
    if quiet:
        cmd.append("--quiet")
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


class TestBddOracleNudgeWiring:
    """Option B (TASK-FIX-RWOP1.2) acceptance for Step 10.6."""

    def test_bdd_oracle_nudge_header_in_stdout(
        self, project_dir: Path, tasks_json: Path
    ) -> None:
        """Non-quiet run emits the R2 BDD-oracle nudge banner to stdout."""
        result = _run_script(project_dir, tasks_json)

        assert result.returncode == 0, (
            f"Script exited non-zero.\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        assert "BDD oracle (R2) not activated" in result.stdout, (
            "Expected imperative R2 nudge callsite to emit "
            "'BDD oracle (R2) not activated' banner in stdout.\n"
            f"stdout:\n{result.stdout}"
        )

    def test_bdd_oracle_nudge_mentions_task_tag_activation(
        self, project_dir: Path, tasks_json: Path
    ) -> None:
        """Banner body explains the @task:<TASK-ID> activation route."""
        result = _run_script(project_dir, tasks_json)

        assert result.returncode == 0
        assert "@task:<TASK-ID>" in result.stdout


class TestSmokeGatesNudgeWiring:
    """Option B (TASK-FIX-RWOP1.2) acceptance for Step 10.7."""

    def test_smoke_gates_nudge_header_in_stdout(
        self, project_dir: Path, tasks_json: Path
    ) -> None:
        """Non-quiet run emits the R3 smoke-gates nudge banner to stdout."""
        result = _run_script(project_dir, tasks_json)

        assert result.returncode == 0, (
            f"Script exited non-zero.\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        assert (
            "Feature-level smoke gates (R3) not configured" in result.stdout
        ), (
            "Expected imperative R3 nudge callsite to emit "
            "'Feature-level smoke gates (R3) not configured' banner in stdout.\n"
            f"stdout:\n{result.stdout}"
        )

    def test_smoke_gates_nudge_mentions_wave_count(
        self, project_dir: Path, tasks_json: Path
    ) -> None:
        """Banner body reports the actual wave count for the fixture."""
        result = _run_script(project_dir, tasks_json)

        assert result.returncode == 0
        # Fixture has two tasks with a dependency chain → exactly 2 waves.
        assert "2 waves" in result.stdout


class TestQuietModeSuppressesBothNudges:
    """``--quiet`` must suppress BOTH banners (preserves FEAT-ID:path contract)."""

    def test_quiet_mode_suppresses_bdd_oracle_nudge(
        self, project_dir: Path, tasks_json: Path
    ) -> None:
        result = _run_script(project_dir, tasks_json, quiet=True)

        assert result.returncode == 0
        assert "BDD oracle (R2) not activated" not in result.stdout, (
            "Quiet mode must not emit the R2 nudge banner.\n"
            f"stdout:\n{result.stdout}"
        )

    def test_quiet_mode_suppresses_smoke_gates_nudge(
        self, project_dir: Path, tasks_json: Path
    ) -> None:
        result = _run_script(project_dir, tasks_json, quiet=True)

        assert result.returncode == 0
        assert (
            "Feature-level smoke gates (R3) not configured" not in result.stdout
        ), (
            "Quiet mode must not emit the R3 nudge banner.\n"
            f"stdout:\n{result.stdout}"
        )

    def test_quiet_mode_preserves_parseable_output_contract(
        self, project_dir: Path, tasks_json: Path
    ) -> None:
        """Quiet mode still emits a single ``FEAT-XXXX:path`` line on stdout."""
        result = _run_script(project_dir, tasks_json, quiet=True)

        assert result.returncode == 0
        assert result.stdout.strip().startswith("FEAT-")
