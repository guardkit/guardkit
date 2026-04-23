"""End-to-end test: lint-AC compliance and no-standalone-QG-task properties
for the live ``generate_feature_yaml.py`` path.

Follow-up to TASK-FIX-RWOP1.5, which quarantined
``tests/planning/test_lint_ac_compliance.py`` alongside the dead
``--from-spec`` research-template parser (``parse_research_template`` and
``generate_quality_gates`` are now in ``_scratch/planning/``). Two of that
test's three assertions are still live policy against **every**
``/feature-plan`` invocation, regardless of mode:

1. Implementation-class tasks must carry at least one lint-compliance AC.
2. No standalone ``verify-quality-gates``/equivalent tasks should appear in
   the generated feature YAML.

The live producer is ``generate_feature_yaml.py`` (post-RWOP1.2), which
consumes ``--tasks-json`` and writes feature YAML. Its current
``TaskSpec.to_dict()`` serialiser **does not emit** ``acceptance_criteria``
into the YAML — ACs enter via ``--tasks-json`` and are consumed in-process
by the AC linter (``lint_plan_warnings``), whose summary goes to stdout.

Given that schema reality, this test asserts the two properties at the
boundaries where they are observable:

- **no-standalone-QG-task** is asserted on the OUTPUT YAML (task ``name``
  and ``implementation_mode`` are both serialised there, which is
  sufficient for detection).
- **lint-AC presence** is asserted on the INPUT ``--tasks-json`` that the
  test feeds the producer, paired with the invariant that the producer
  preserves tasks by id in the output YAML. This is a round-trip
  regression guard: if ``/feature-plan`` ever stops generating lint ACs
  for its implementation-class tasks, or the producer ever drops those
  tasks by id, this test will flip.

Both properties include positive AND negative-control cases to prove the
assertion logic is not vacuously true.

Structural cousin of ``test_generate_feature_yaml_linter.py`` (R1 AC-linter
wiring) and ``test_generate_feature_yaml_nudges.py`` (R2/R3 nudges) — same
subprocess-based end-to-end shape against the same producer.

See TASK-FIX-RWOP1.6 §Scope and
``.claude/reviews/TASK-FIX-RWOP1.5-from-spec-decision.md`` §"Known,
accepted outcomes" → "Coverage gap for live lint-ac policy".
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

import pytest
import yaml

from installer.core.lib.slug_utils import slugify_task_name

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "installer" / "core" / "commands" / "lib" / "generate_feature_yaml.py"


# ---------------------------------------------------------------------------
# Fixture payloads
# ---------------------------------------------------------------------------

# Compliant payload: both implementation-class tasks carry a lint AC, and
# no task exists solely to verify quality gates.
_COMPLIANT_TASKS: List[dict] = [
    {
        "id": "TASK-LAC-001",
        "name": "Build CSV ingester",
        "complexity": 5,
        "acceptance_criteria": [
            "- [ ] `parse_csv` returns a list of dicts keyed by column header",
            "- [ ] All modified files pass project-configured lint/format "
            "checks with zero errors",
        ],
    },
    {
        "id": "TASK-LAC-002",
        "name": "Wire ingester into CLI",
        "complexity": 4,
        "dependencies": ["TASK-LAC-001"],
        "acceptance_criteria": [
            "- [ ] `guardkit ingest <path>` succeeds end-to-end",
            "- [ ] All modified files pass project-configured lint/format "
            "checks with zero errors",
        ],
    },
]


# Negative control for lint-AC presence: identical task shape but with
# the lint AC stripped from both tasks.
_NO_LINT_AC_TASKS: List[dict] = [
    {
        "id": "TASK-LAC-001",
        "name": "Build CSV ingester",
        "complexity": 5,
        "acceptance_criteria": [
            "- [ ] `parse_csv` returns a list of dicts keyed by column header",
        ],
    },
    {
        "id": "TASK-LAC-002",
        "name": "Wire ingester into CLI",
        "complexity": 4,
        "dependencies": ["TASK-LAC-001"],
        "acceptance_criteria": [
            "- [ ] `guardkit ingest <path>` succeeds end-to-end",
        ],
    },
]


# Negative control for no-standalone-QG-task: compliant implementation task
# plus an explicit standalone "Verify quality gates" task.
_WITH_STANDALONE_QG_TASKS: List[dict] = [
    {
        "id": "TASK-LAC-001",
        "name": "Build CSV ingester",
        "complexity": 5,
        "acceptance_criteria": [
            "- [ ] `parse_csv` returns a list of dicts keyed by column header",
            "- [ ] All modified files pass project-configured lint/format "
            "checks with zero errors",
        ],
    },
    {
        "id": "TASK-LAC-QG1",
        "name": "Verify quality gates",
        "complexity": 1,
        "dependencies": ["TASK-LAC-001"],
        "acceptance_criteria": [
            "- [ ] ruff check passes with zero errors",
        ],
    },
]


# ---------------------------------------------------------------------------
# Workspace + subprocess helpers
# ---------------------------------------------------------------------------


def _make_workspace(tmp_path: Path, tasks: List[dict]) -> Tuple[Path, Path]:
    """Set up a throwaway project workspace under ``tmp_path``.

    Creates stub task markdown files at the paths the producer will derive
    from ``--feature-slug=probe`` + task name. ``--lenient`` would downgrade
    path mismatches to stderr warnings, but creating the files keeps stderr
    clean and focuses subsequent failures on the property under test.
    """
    feature_dir = tmp_path / "tasks" / "backlog" / "probe"
    feature_dir.mkdir(parents=True)
    for task in tasks:
        slug = slugify_task_name(task["name"])
        (feature_dir / f"{task['id']}-{slug}.md").write_text("# stub\n")

    tasks_path = tmp_path / "tasks.json"
    tasks_path.write_text(json.dumps(tasks))
    return tmp_path, tasks_path


def _run_script(
    project_dir: Path, tasks_json: Path
) -> subprocess.CompletedProcess:
    """Invoke ``generate_feature_yaml.py`` as a subprocess, lenient mode."""
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--name", "probe",
        "--description", "lint-ac compliance wiring probe",
        "--feature-slug", "probe",
        "--base-path", str(project_dir),
        "--tasks-json", str(tasks_json),
        "--lenient",
    ]
    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def _load_generated_yaml(project_dir: Path) -> dict:
    """Locate + parse the feature YAML written under the default path."""
    features_dir = project_dir / ".guardkit" / "features"
    yamls = list(features_dir.glob("FEAT-*.yaml"))
    assert len(yamls) == 1, (
        f"Expected exactly one generated feature YAML under {features_dir}, "
        f"found: {[str(p) for p in yamls]}"
    )
    return yaml.safe_load(yamls[0].read_text())


# ---------------------------------------------------------------------------
# Property helpers
# ---------------------------------------------------------------------------


def _has_lint_ac(acceptance_criteria: List[str]) -> bool:
    """True if any AC mentions ``lint`` (case-insensitive substring)."""
    return any("lint" in ac.lower() for ac in acceptance_criteria)


# Words whose presence in a task name signals the task produces real
# code/artifacts and therefore is not a standalone quality-gate task.
_IMPLEMENTATION_SIGNALS: Tuple[str, ...] = (
    "implement",
    "build",
    "create",
    "add",
    "generate",
    "refactor",
    "wire",
    "write",
    "design",
)

# Lowercase substrings whose presence in an implementation-signal-free
# task name indicates the task's sole purpose is running verification
# checks. Mirrors the intent of the quarantined helper in
# ``_scratch/planning/tests/test_lint_ac_compliance.py`` without sharing
# code (the quarantined helper operated on ``TaskDefinition``, not the
# YAML schema).
_STANDALONE_QG_PATTERNS: Tuple[str, ...] = (
    "verify quality gate",
    "run linting",
    "run lint",
    "format check",
    "type check only",
    "run type check",
    "quality gate verification",
    "quality gate check",
)


def _is_standalone_qg_task(task_dict: dict) -> bool:
    """Detect a standalone quality-gate-verification task in YAML output.

    A task whose name contains an implementation signal (``Implement``,
    ``Build``, etc.) is never standalone — those tasks produce real
    code even if the name mentions "quality gate". A task whose name is
    purely verification-oriented (``Verify quality gates``,
    ``Run linting``) is flagged.
    """
    name_lower = task_dict.get("name", "").lower()
    if any(signal in name_lower for signal in _IMPLEMENTATION_SIGNALS):
        return False
    return any(pat in name_lower for pat in _STANDALONE_QG_PATTERNS)


# ---------------------------------------------------------------------------
# Tests: lint-AC presence
# ---------------------------------------------------------------------------


class TestLintACPresenceRoundTrip:
    """Implementation-class tasks must have at least one lint AC.

    Asserted as a round-trip between INPUT ``--tasks-json`` (which carries
    ACs) and OUTPUT YAML (which does not — see module docstring). The
    positive test proves the property holds for a compliant fixture; the
    negative control proves the assertion logic is not vacuous.
    """

    def test_compliant_fixture_every_impl_task_has_lint_ac(
        self, tmp_path: Path
    ) -> None:
        project_dir, tasks_json = _make_workspace(tmp_path, _COMPLIANT_TASKS)
        result = _run_script(project_dir, tasks_json)

        assert result.returncode == 0, (
            f"Producer failed.\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

        input_tasks = json.loads(tasks_json.read_text())
        id_to_acs = {
            t["id"]: t.get("acceptance_criteria", []) or [] for t in input_tasks
        }

        feature_yaml = _load_generated_yaml(project_dir)
        impl_tasks = [
            t for t in feature_yaml["tasks"]
            if t.get("implementation_mode") == "task-work"
        ]
        assert impl_tasks, (
            "Expected at least one implementation-class ('task-work') task "
            f"in the generated YAML. Tasks: {feature_yaml['tasks']}"
        )

        missing = [
            t for t in impl_tasks
            if not _has_lint_ac(id_to_acs.get(t["id"], []))
        ]
        assert not missing, (
            "Implementation-class tasks without a lint-compliance AC in "
            "their source payload:\n"
            + "\n".join(
                f"  {t['id']} ({t['name']}): "
                f"ACs = {id_to_acs.get(t['id'], [])}"
                for t in missing
            )
        )

    def test_negative_control_missing_lint_ac_is_detected(
        self, tmp_path: Path
    ) -> None:
        """The assertion logic catches tasks whose ACs omit lint references."""
        project_dir, tasks_json = _make_workspace(tmp_path, _NO_LINT_AC_TASKS)
        result = _run_script(project_dir, tasks_json)

        assert result.returncode == 0, (
            f"Producer failed.\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

        input_tasks = json.loads(tasks_json.read_text())
        id_to_acs = {
            t["id"]: t.get("acceptance_criteria", []) or [] for t in input_tasks
        }

        feature_yaml = _load_generated_yaml(project_dir)
        impl_tasks = [
            t for t in feature_yaml["tasks"]
            if t.get("implementation_mode") == "task-work"
        ]

        missing = [
            t for t in impl_tasks
            if not _has_lint_ac(id_to_acs.get(t["id"], []))
        ]
        assert missing, (
            "Negative-control fixture strips lint ACs from every task, yet "
            "_has_lint_ac passed for all implementation-class tasks. The "
            "positive assertion above is therefore vacuously true and needs "
            "a tighter detector."
        )


# ---------------------------------------------------------------------------
# Tests: no standalone quality-gate tasks
# ---------------------------------------------------------------------------


class TestNoStandaloneQualityGateTask:
    """The generated YAML should not contain standalone QG-verification tasks.

    Asserted directly against the OUTPUT YAML; ``name`` and
    ``implementation_mode`` are both serialised there, which is sufficient
    for detection.
    """

    def test_compliant_fixture_has_no_standalone_qg_task(
        self, tmp_path: Path
    ) -> None:
        project_dir, tasks_json = _make_workspace(tmp_path, _COMPLIANT_TASKS)
        result = _run_script(project_dir, tasks_json)

        assert result.returncode == 0, (
            f"Producer failed.\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

        feature_yaml = _load_generated_yaml(project_dir)
        flagged = [
            t["name"]
            for t in feature_yaml["tasks"]
            if _is_standalone_qg_task(t)
        ]
        assert not flagged, (
            "Compliant fixture produced standalone quality-gate tasks in "
            f"the generated YAML: {flagged}. Implementation tasks should "
            "inline their gate commands in coach validation rather than "
            "spawn verification-only tasks."
        )

    def test_negative_control_standalone_qg_task_is_detected(
        self, tmp_path: Path
    ) -> None:
        """The detector flags a deliberately-added 'Verify quality gates' task."""
        project_dir, tasks_json = _make_workspace(
            tmp_path, _WITH_STANDALONE_QG_TASKS
        )
        result = _run_script(project_dir, tasks_json)

        assert result.returncode == 0, (
            f"Producer failed.\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

        feature_yaml = _load_generated_yaml(project_dir)
        flagged = [
            t["name"]
            for t in feature_yaml["tasks"]
            if _is_standalone_qg_task(t)
        ]
        assert flagged, (
            "Negative-control fixture inserts a 'Verify quality gates' task, "
            "yet _is_standalone_qg_task flagged nothing. The positive "
            "assertion above is therefore vacuously true and needs a "
            "tighter detector."
        )
        assert any(
            "verify quality gate" in name.lower() for name in flagged
        ), (
            f"Expected the 'Verify quality gates' task to be the one "
            f"flagged. Flagged set: {flagged}"
        )
