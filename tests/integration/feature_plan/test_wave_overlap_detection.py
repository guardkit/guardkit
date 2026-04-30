"""End-to-end test: wave-overlap detector fires from generate_feature_yaml.

Exercises the imperative callsite added by TASK-FIX-A7B3. Drives the
``generate_feature_yaml.py`` script via subprocess against a fixture workspace
where two tasks in the same parallel wave both edit the same shared BDD glue
file. The default run must emit a warning (AC-004 default mode), and the
``--auto-serialise-overlap`` run must split the offending parallel group into
a sequential follow-on entry (AC-004 auto-serialise mode).

Structural twin of ``test_generate_feature_yaml_nudges.py`` (R2/R3 nudges)
and ``test_generate_feature_yaml_linter.py`` (R1 AC linter) — those tests
prove the pre-existing producer-runs-check banners fire from the producer;
this test proves the wave-overlap banner does the same. Without this test,
the overlap detection remains a Claude-as-runtime interpretation of prose.

See TASK-FIX-A7B3 §Acceptance Criteria AC-004.
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
def project_dir(tmp_path: Path) -> Path:
    """Temporary project root with two task files for the same feature.

    The files are stubs — the real signal lives in the JSON payload, which
    carries the task descriptions/ACs the detector reads. We ship empty .md
    files so ``--strict`` path validation passes.
    """
    feature_dir = tmp_path / "tasks" / "backlog" / "foo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "TASK-FOO-001-add-step-defs.md").write_text("# stub\n")
    (feature_dir / "TASK-FOO-002-add-more-step-defs.md").write_text("# stub\n")
    return tmp_path


@pytest.fixture
def overlapping_tasks_json(project_dir: Path) -> Path:
    """Two independent tasks (no dependency edge) both editing ``features/foo/test_foo.py``.

    With no dependency between them, ``build_parallel_groups`` schedules them
    into the same wave — exactly the FEAT-70A4 collision shape from the
    sibling study-tutor repo.
    """
    payload = [
        {
            "id": "TASK-FOO-001",
            "name": "Add login step defs",
            "complexity": 5,
            "description": (
                "Implement step definitions in `features/foo/test_foo.py` "
                "for the new login flow. Uses pytest-bdd."
            ),
            "acceptance_criteria": [
                "- [ ] Step definitions cover all Given/When/Then in features/foo/login.feature",
            ],
        },
        {
            "id": "TASK-FOO-002",
            "name": "Add signup step defs",
            "complexity": 5,
            "description": (
                "Implement step definitions in `features/foo/test_foo.py` "
                "for the new signup flow. Uses pytest-bdd."
            ),
            "acceptance_criteria": [
                "- [ ] Step definitions cover all Given/When/Then in features/foo/signup.feature",
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
    auto_serialise: bool = False,
    quiet: bool = False,
) -> subprocess.CompletedProcess:
    """Invoke generate_feature_yaml.py as a subprocess and capture output."""
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--name", "foo",
        "--description", "wave-overlap detection probe",
        "--feature-slug", "foo",
        "--base-path", str(project_dir),
        "--tasks-json", str(tasks_json),
        "--lenient",
    ]
    if auto_serialise:
        cmd.append("--auto-serialise-overlap")
    if quiet:
        cmd.append("--quiet")
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


class TestDefaultModeEmitsWarning:
    """AC-004: default mode emits a planner warning naming overlapping tasks/files."""

    def test_default_run_emits_overlap_warning_banner(
        self, project_dir: Path, overlapping_tasks_json: Path
    ) -> None:
        result = _run_script(project_dir, overlapping_tasks_json)

        assert result.returncode == 0, (
            f"Script exited non-zero.\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        assert "Wave overlap (plan-time) check" in result.stdout, (
            "Expected imperative wave-overlap callsite to emit the banner header.\n"
            f"stdout:\n{result.stdout}"
        )

    def test_warning_names_overlapping_tasks(
        self, project_dir: Path, overlapping_tasks_json: Path
    ) -> None:
        result = _run_script(project_dir, overlapping_tasks_json)

        assert result.returncode == 0
        assert "TASK-FOO-001" in result.stdout
        assert "TASK-FOO-002" in result.stdout

    def test_warning_names_shared_file(
        self, project_dir: Path, overlapping_tasks_json: Path
    ) -> None:
        result = _run_script(project_dir, overlapping_tasks_json)

        assert result.returncode == 0
        assert "features/foo/test_foo.py" in result.stdout

    def test_default_run_suggests_auto_serialise_flag(
        self, project_dir: Path, overlapping_tasks_json: Path
    ) -> None:
        result = _run_script(project_dir, overlapping_tasks_json)

        assert result.returncode == 0
        assert "--auto-serialise-overlap" in result.stdout

    def test_default_run_does_not_split_parallel_groups(
        self, project_dir: Path, overlapping_tasks_json: Path
    ) -> None:
        """Default mode is warn-only; the YAML still schedules both tasks in wave 1."""
        result = _run_script(project_dir, overlapping_tasks_json)

        assert result.returncode == 0
        # Both task IDs should land on the same Wave 1 line.
        wave_lines = [
            line for line in result.stdout.splitlines()
            if line.lstrip().startswith("Wave 1:")
        ]
        assert wave_lines, f"No 'Wave 1:' line found.\nstdout:\n{result.stdout}"
        assert "TASK-FOO-001" in wave_lines[0]
        assert "TASK-FOO-002" in wave_lines[0]


class TestAutoSerialiseSplitsPlan:
    """AC-004: --auto-serialise-overlap splits the offending wave."""

    def test_auto_serialise_emits_split_note(
        self, project_dir: Path, overlapping_tasks_json: Path
    ) -> None:
        result = _run_script(
            project_dir, overlapping_tasks_json, auto_serialise=True
        )

        assert result.returncode == 0, (
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert "follow-on sequential wave" in result.stdout

    def test_auto_serialise_produces_two_sequential_waves(
        self, project_dir: Path, overlapping_tasks_json: Path
    ) -> None:
        """AC-003: split produces two sequential entries — one task per wave."""
        result = _run_script(
            project_dir, overlapping_tasks_json, auto_serialise=True
        )

        assert result.returncode == 0
        # Summary reports 2 waves after split.
        assert "Parallel execution groups: 2 waves" in result.stdout, (
            f"Expected 2 waves after split; got:\n{result.stdout}"
        )
        # Each wave holds exactly one offender, in original order.
        wave_1_lines = [
            line for line in result.stdout.splitlines()
            if line.lstrip().startswith("Wave 1:")
        ]
        wave_2_lines = [
            line for line in result.stdout.splitlines()
            if line.lstrip().startswith("Wave 2:")
        ]
        assert wave_1_lines and wave_2_lines, (
            f"Expected both 'Wave 1:' and 'Wave 2:' lines.\nstdout:\n{result.stdout}"
        )
        assert "TASK-FOO-001" in wave_1_lines[0]
        assert "TASK-FOO-002" not in wave_1_lines[0]
        assert "TASK-FOO-002" in wave_2_lines[0]
        assert "TASK-FOO-001" not in wave_2_lines[0]


class TestDisjointPlanProducesNoWarning:
    """AC-005: existing zero-overlap plans are unchanged. No spurious warnings."""

    def test_disjoint_plan_emits_no_overlap_banner(
        self, project_dir: Path
    ) -> None:
        # Two tasks editing different files — no overlap.
        payload = [
            {
                "id": "TASK-FOO-001",
                "name": "Add login endpoint",
                "complexity": 5,
                "description": "Edit `src/auth/login.py` to add the new endpoint.",
                "acceptance_criteria": [
                    "- [ ] Test in tests/unit/test_login.py passes",
                ],
            },
            {
                "id": "TASK-FOO-002",
                "name": "Add signup endpoint",
                "complexity": 5,
                "description": "Edit `src/auth/signup.py` to add the new endpoint.",
                "acceptance_criteria": [
                    "- [ ] Test in tests/unit/test_signup.py passes",
                ],
            },
        ]
        tasks_json_path = project_dir / "disjoint.json"
        tasks_json_path.write_text(json.dumps(payload))

        result = _run_script(project_dir, tasks_json_path)
        assert result.returncode == 0
        assert "Wave overlap (plan-time) check" not in result.stdout, (
            f"Spurious wave-overlap banner on disjoint plan.\nstdout:\n{result.stdout}"
        )


class TestQuietModeSuppressesBanner:
    """``--quiet`` must suppress the banner, mirroring the AC-linter / nudge contract."""

    def test_quiet_mode_suppresses_overlap_banner(
        self, project_dir: Path, overlapping_tasks_json: Path
    ) -> None:
        result = _run_script(project_dir, overlapping_tasks_json, quiet=True)

        assert result.returncode == 0
        assert "Wave overlap (plan-time) check" not in result.stdout, (
            f"Quiet mode must not emit the overlap banner.\nstdout:\n{result.stdout}"
        )

    def test_quiet_mode_preserves_parseable_output_contract(
        self, project_dir: Path, overlapping_tasks_json: Path
    ) -> None:
        """Quiet mode still emits a single ``FEAT-XXXX:path`` line on stdout."""
        result = _run_script(project_dir, overlapping_tasks_json, quiet=True)

        assert result.returncode == 0
        assert result.stdout.strip().startswith("FEAT-")
