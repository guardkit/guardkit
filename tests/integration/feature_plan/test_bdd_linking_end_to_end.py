"""End-to-end test: /feature-plan Step 11 fires from feature_plan_bdd_link.py.

Exercises the imperative callsite added by TASK-FIX-RWOP1.1 (Path B). Drives
the ``feature_plan_bdd_link.py`` producer script via subprocess across both
``prepare`` and ``apply`` subcommands and asserts that:

1. ``prepare`` discovers the ``.feature`` file, builds a MatchingRequest with
   the tasks loaded from the feature YAML (with acceptance criteria pulled
   from each task markdown file), and emits a ``status=ready`` envelope.
2. ``apply`` reads a matcher-response JSON file and rewrites the ``.feature``
   file with at least one ``@task:`` tag — proving the `bdd-linker` agent's
   output reaches the file system through this path.
3. Silent-skip paths (``no_feature_file``, ``no_scenarios``, ``all_tagged``)
   emit ``status=skipped`` so Step 11 prose can branch deterministically.
4. Matcher response errors surface with exit code 2 and an actionable
   stderr message, so /feature-plan can offer a retry rather than swallow
   the failure.

This is the structural counterpart to ``test_bdd_linking.py`` — that test
proves the in-process ``run_linking_phase`` orchestrator works; this test
proves the production CLI shim that /feature-plan actually invokes works.
Without this test, R2 activation would remain a Claude-as-runtime
interpretation of prose, not a deterministic callsite (TASK-REV-RWOP1
Finding #1).

See TASK-FIX-RWOP1.1 § Acceptance Criteria.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "installer" / "core" / "commands" / "lib" / "feature_plan_bdd_link.py"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


_CHECKOUT_FEATURE = """Feature: Checkout

  @smoke
  Scenario: Guest completes purchase with valid card
    Given a guest with an item in cart
    When they submit valid card details
    Then the order is confirmed

  Scenario: Declined card shows retry option
    Given a guest with an item in cart
    When the card is declined
    Then they see a retry prompt

  Scenario: Cart persists across sessions
    Given an item in cart
    When the session ends
    Then the item is still there on next login
"""


def _write_task_md(
    project_root: Path,
    feature_slug: str,
    task_id: str,
    title: str,
    description: str,
    acceptance_criteria: list,
) -> Path:
    """Write a minimal task markdown file with frontmatter and AC section."""
    task_dir = project_root / "tasks" / "backlog" / feature_slug
    task_dir.mkdir(parents=True, exist_ok=True)
    file_path = task_dir / f"{task_id}.md"
    ac_lines = "\n".join(f"- [ ] {ac}" for ac in acceptance_criteria)
    body = f"""---
id: {task_id}
title: {title}
status: backlog
---

# Task: {title}

## Description
{description}

## Acceptance Criteria
{ac_lines}
"""
    file_path.write_text(body, encoding="utf-8")
    return file_path


def _write_feature_yaml(
    project_root: Path,
    feature_id: str,
    feature_slug: str,
    tasks: list,
) -> Path:
    """Write a generate_feature_yaml.py-shaped feature YAML."""
    yaml_path = project_root / ".guardkit" / "features" / f"{feature_id}.yaml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "id": feature_id,
        "name": "Checkout",
        "description": "Cart and payment flow",
        "tasks": [
            {
                "id": t["id"],
                "name": t["name"],
                "description": t["description"],
                "file_path": str(
                    Path("tasks/backlog") / feature_slug / f"{t['id']}.md"
                ),
                "complexity": 5,
            }
            for t in tasks
        ],
    }
    try:
        import yaml
        yaml_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    except ImportError:
        # Fallback: write as JSON. load_feature_yaml accepts .json with no PyYAML.
        yaml_path = yaml_path.with_suffix(".json")
        yaml_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return yaml_path


def _write_feature_file(project_root: Path, slug: str, body: str) -> Path:
    """Write a feature file in the nested layout."""
    feature_dir = project_root / "features" / slug
    feature_dir.mkdir(parents=True, exist_ok=True)
    feature_file = feature_dir / f"{slug}.feature"
    feature_file.write_text(body, encoding="utf-8")
    return feature_file


@pytest.fixture
def checkout_project(tmp_path: Path):
    """A complete fixture project: feature file + feature YAML + task MDs."""
    feature_slug = "checkout"
    feature_id = "FEAT-CK00"

    feature_file = _write_feature_file(tmp_path, feature_slug, _CHECKOUT_FEATURE)

    tasks = [
        {
            "id": "TASK-CK-001",
            "name": "Implement card payment flow",
            "description": (
                "Accept card details, call the payment gateway, "
                "handle success and decline."
            ),
            "acceptance_criteria": [
                "Successful charges confirm the order",
                "Declined cards surface a retry prompt",
            ],
        },
        {
            "id": "TASK-CK-002",
            "name": "Persist cart state in session storage",
            "description": "Cart survives session end and is restored on next login.",
            "acceptance_criteria": ["Cart items restored on login"],
        },
    ]
    for t in tasks:
        _write_task_md(
            tmp_path,
            feature_slug,
            t["id"],
            t["name"],
            t["description"],
            t["acceptance_criteria"],
        )

    feature_yaml = _write_feature_yaml(tmp_path, feature_id, feature_slug, tasks)

    return {
        "project_root": tmp_path,
        "feature_slug": feature_slug,
        "feature_id": feature_id,
        "feature_file": feature_file,
        "feature_yaml": feature_yaml,
        "tasks": tasks,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(args: list, cwd: Path = None) -> subprocess.CompletedProcess:
    """Invoke the script as a subprocess.

    Sets PYTHONPATH to the repo root so the script's
    ``installer.core.commands.lib`` imports resolve.
    """
    import os
    env = os.environ.copy()
    pythonpath = str(REPO_ROOT)
    if env.get("PYTHONPATH"):
        pythonpath = pythonpath + os.pathsep + env["PYTHONPATH"]
    env["PYTHONPATH"] = pythonpath

    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(cwd) if cwd is not None else None,
        env=env,
    )


def _parse_status(stdout: str) -> dict:
    """Parse the single-line status JSON from prepare's stdout."""
    line = stdout.strip().splitlines()[-1]
    return json.loads(line)


# ---------------------------------------------------------------------------
# prepare: ready path
# ---------------------------------------------------------------------------


class TestPrepareReady:
    """`prepare` emits status=ready and writes a usable MatchingRequest."""

    def test_emits_ready_with_request_path(self, checkout_project, tmp_path: Path) -> None:
        out_file = tmp_path / "req.json"
        result = _run(
            [
                "prepare",
                "--project-root",
                str(checkout_project["project_root"]),
                "--feature-slug",
                checkout_project["feature_slug"],
                "--feature-yaml",
                str(checkout_project["feature_yaml"]),
                "--output",
                str(out_file),
            ]
        )

        assert result.returncode == 0, f"stderr: {result.stderr}"
        status = _parse_status(result.stdout)
        assert status["status"] == "ready"
        assert status["scenarios_to_match"] == 3
        assert status["task_count"] == 2
        assert status["request_path"] == str(out_file)
        assert status["already_tagged_count"] == 0

    def test_request_includes_acceptance_criteria_from_task_md(
        self, checkout_project, tmp_path: Path
    ) -> None:
        """The MatchingRequest payload carries ACs parsed from task markdown."""
        out_file = tmp_path / "req.json"
        result = _run(
            [
                "prepare",
                "--project-root",
                str(checkout_project["project_root"]),
                "--feature-slug",
                checkout_project["feature_slug"],
                "--feature-yaml",
                str(checkout_project["feature_yaml"]),
                "--output",
                str(out_file),
            ]
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        payload = json.loads(out_file.read_text(encoding="utf-8"))
        assert payload["feature_name"] == "Checkout"
        assert len(payload["scenarios"]) == 3
        # Task ACs surfaced in the payload — the matcher needs these.
        ck001 = next(t for t in payload["tasks"] if t["task_id"] == "TASK-CK-001")
        assert "Successful charges confirm the order" in ck001["acceptance_criteria"]
        assert "Declined cards surface a retry prompt" in ck001["acceptance_criteria"]


# ---------------------------------------------------------------------------
# prepare: silent-skip paths
# ---------------------------------------------------------------------------


class TestPrepareSkipPaths:
    """`prepare` returns status=skipped for the three idempotency paths."""

    def test_no_feature_file(self, tmp_path: Path) -> None:
        # Empty project: no features/, no feature YAML.
        # Need a feature YAML path even for the no_feature_file branch
        # — prepare exits before reading it.
        result = _run(
            [
                "prepare",
                "--project-root",
                str(tmp_path),
                "--feature-slug",
                "absent",
                "--feature-yaml",
                str(tmp_path / "irrelevant.yaml"),
            ]
        )
        assert result.returncode == 0
        status = _parse_status(result.stdout)
        assert status["status"] == "skipped"
        assert status["reason"] == "no_feature_file"

    def test_all_already_tagged(self, tmp_path: Path) -> None:
        body = """Feature: Checkout

  @task:TASK-CK-001
  Scenario: Guest completes purchase
    Given a guest with an item in cart
    When they submit valid card details
    Then the order is confirmed

  @task:TASK-CK-002
  Scenario: Cart persists
    Given an item in cart
    When the session ends
    Then the item is still there on next login
"""
        _write_feature_file(tmp_path, "checkout", body)

        # Build a minimal feature YAML so the script gets that far.
        _write_task_md(
            tmp_path, "checkout", "TASK-CK-001", "Card", "card flow", ["foo"]
        )
        _write_task_md(
            tmp_path, "checkout", "TASK-CK-002", "Cart", "cart flow", ["bar"]
        )
        feature_yaml = _write_feature_yaml(
            tmp_path,
            "FEAT-CK00",
            "checkout",
            [
                {
                    "id": "TASK-CK-001",
                    "name": "Card",
                    "description": "card flow",
                    "acceptance_criteria": ["foo"],
                },
                {
                    "id": "TASK-CK-002",
                    "name": "Cart",
                    "description": "cart flow",
                    "acceptance_criteria": ["bar"],
                },
            ],
        )

        result = _run(
            [
                "prepare",
                "--project-root",
                str(tmp_path),
                "--feature-slug",
                "checkout",
                "--feature-yaml",
                str(feature_yaml),
            ]
        )
        assert result.returncode == 0
        status = _parse_status(result.stdout)
        assert status["status"] == "skipped"
        assert status["reason"] == "all_tagged"

    def test_missing_feature_yaml_is_hard_error(self, tmp_path: Path) -> None:
        _write_feature_file(tmp_path, "checkout", _CHECKOUT_FEATURE)
        result = _run(
            [
                "prepare",
                "--project-root",
                str(tmp_path),
                "--feature-slug",
                "checkout",
                "--feature-yaml",
                str(tmp_path / "does-not-exist.yaml"),
            ]
        )
        assert result.returncode == 1
        assert "feature YAML not found" in result.stderr


# ---------------------------------------------------------------------------
# apply: end-to-end with mock matcher response
# ---------------------------------------------------------------------------


class TestApplyEndToEnd:
    """`apply` rewrites the .feature file from a matcher-response JSON file.

    This is the AC criterion for TASK-FIX-RWOP1.1: drives the chosen path
    against a fixture and asserts at least one `@task:` tag appears in
    the output `.feature` file.
    """

    def test_rewrites_feature_with_task_tags(
        self, checkout_project, tmp_path: Path
    ) -> None:
        # Simulate the bdd-linker subagent's response.
        matches = [
            {"scenario_index": 0, "task_id": "TASK-CK-001", "confidence": 0.93},
            {"scenario_index": 1, "task_id": "TASK-CK-001", "confidence": 0.88},
            {"scenario_index": 2, "task_id": "TASK-CK-002", "confidence": 0.90},
        ]
        matches_file = tmp_path / "matches.json"
        matches_file.write_text(json.dumps(matches), encoding="utf-8")

        result = _run(
            [
                "apply",
                "--project-root",
                str(checkout_project["project_root"]),
                "--feature-slug",
                checkout_project["feature_slug"],
                "--task-matches-file",
                str(matches_file),
            ]
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        # Acceptance criterion: at least one @task: tag in the output.
        content = checkout_project["feature_file"].read_text(encoding="utf-8")
        assert "@task:TASK-CK-001" in content
        assert "@task:TASK-CK-002" in content
        # The pre-existing @smoke tag must survive the rewrite.
        assert "@smoke" in content

        # The summary line is printed.
        assert "[Step 11] linked 3 scenario(s) to task(s)" in result.stdout

    def test_below_threshold_reported(self, checkout_project, tmp_path: Path) -> None:
        matches = [
            {"scenario_index": 0, "task_id": "TASK-CK-001", "confidence": 0.92},
            # Below default 0.6 threshold:
            {"scenario_index": 1, "task_id": "TASK-CK-001", "confidence": 0.40},
        ]
        matches_file = tmp_path / "matches.json"
        matches_file.write_text(json.dumps(matches), encoding="utf-8")

        result = _run(
            [
                "apply",
                "--project-root",
                str(checkout_project["project_root"]),
                "--feature-slug",
                checkout_project["feature_slug"],
                "--task-matches-file",
                str(matches_file),
            ]
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        assert "below threshold" in result.stdout

    def test_dry_run_does_not_rewrite(self, checkout_project, tmp_path: Path) -> None:
        original = checkout_project["feature_file"].read_text(encoding="utf-8")

        matches = [
            {"scenario_index": 0, "task_id": "TASK-CK-001", "confidence": 0.93},
        ]
        matches_file = tmp_path / "matches.json"
        matches_file.write_text(json.dumps(matches), encoding="utf-8")

        result = _run(
            [
                "apply",
                "--project-root",
                str(checkout_project["project_root"]),
                "--feature-slug",
                checkout_project["feature_slug"],
                "--task-matches-file",
                str(matches_file),
                "--dry-run",
            ]
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"

        # File is unchanged.
        after = checkout_project["feature_file"].read_text(encoding="utf-8")
        assert after == original


# ---------------------------------------------------------------------------
# apply: matcher response errors → exit code 2
# ---------------------------------------------------------------------------


class TestApplyMatcherErrors:
    """Malformed matcher responses surface as exit code 2.

    Distinguishing from generic input errors (exit 1) lets feature-plan.md
    branch on "agent returned garbage; offer a retry" specifically.
    """

    def test_invalid_json_returns_exit_code_2(
        self, checkout_project, tmp_path: Path
    ) -> None:
        matches_file = tmp_path / "matches.json"
        matches_file.write_text("definitely not json", encoding="utf-8")

        result = _run(
            [
                "apply",
                "--project-root",
                str(checkout_project["project_root"]),
                "--feature-slug",
                checkout_project["feature_slug"],
                "--task-matches-file",
                str(matches_file),
            ]
        )
        assert result.returncode == 2
        assert "matcher response error" in result.stderr
        assert "invalid JSON" in result.stderr

    def test_missing_field_returns_exit_code_2(
        self, checkout_project, tmp_path: Path
    ) -> None:
        # Missing 'confidence' field.
        matches = [{"scenario_index": 0, "task_id": "TASK-CK-001"}]
        matches_file = tmp_path / "matches.json"
        matches_file.write_text(json.dumps(matches), encoding="utf-8")

        result = _run(
            [
                "apply",
                "--project-root",
                str(checkout_project["project_root"]),
                "--feature-slug",
                checkout_project["feature_slug"],
                "--task-matches-file",
                str(matches_file),
            ]
        )
        assert result.returncode == 2
        assert "missing required field" in result.stderr


# ---------------------------------------------------------------------------
# Round-trip: prepare → simulate matcher → apply → re-prepare
# ---------------------------------------------------------------------------


class TestRoundTrip:
    """Full prepare → apply → re-prepare cycle proves idempotency end-to-end."""

    def test_second_prepare_after_apply_reports_all_tagged(
        self, checkout_project, tmp_path: Path
    ) -> None:
        req_file = tmp_path / "req.json"

        # 1. prepare
        prep1 = _run(
            [
                "prepare",
                "--project-root",
                str(checkout_project["project_root"]),
                "--feature-slug",
                checkout_project["feature_slug"],
                "--feature-yaml",
                str(checkout_project["feature_yaml"]),
                "--output",
                str(req_file),
            ]
        )
        assert prep1.returncode == 0
        assert _parse_status(prep1.stdout)["status"] == "ready"

        # 2. simulate the bdd-linker subagent matching (canned response).
        matches = [
            {"scenario_index": 0, "task_id": "TASK-CK-001", "confidence": 0.93},
            {"scenario_index": 1, "task_id": "TASK-CK-001", "confidence": 0.88},
            {"scenario_index": 2, "task_id": "TASK-CK-002", "confidence": 0.90},
        ]
        matches_file = tmp_path / "matches.json"
        matches_file.write_text(json.dumps(matches), encoding="utf-8")

        # 3. apply
        appl = _run(
            [
                "apply",
                "--project-root",
                str(checkout_project["project_root"]),
                "--feature-slug",
                checkout_project["feature_slug"],
                "--task-matches-file",
                str(matches_file),
            ]
        )
        assert appl.returncode == 0

        # 4. re-prepare → silent skip via all_tagged.
        prep2 = _run(
            [
                "prepare",
                "--project-root",
                str(checkout_project["project_root"]),
                "--feature-slug",
                checkout_project["feature_slug"],
                "--feature-yaml",
                str(checkout_project["feature_yaml"]),
                "--output",
                str(tmp_path / "req2.json"),
            ]
        )
        assert prep2.returncode == 0
        status2 = _parse_status(prep2.stdout)
        assert status2["status"] == "skipped"
        assert status2["reason"] == "all_tagged"
