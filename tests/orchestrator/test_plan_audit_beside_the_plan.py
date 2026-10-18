"""The plan audit does not call a planned file's own test or stylesheet
"high" - and still calls real scope creep high.

Build FEAT-86FD (18 October 2026) stalled after three turns: the task document
planned a page screen and its components, the build also wrote the page's
test, a stylesheet for a planned component and a small test helper, and
changed an existing test. The audit counted three extra files, called that
high, and the Coach refused every turn although the tests passed.

An extra file whose name up to its first dot is the name of a file the plan
names (and which is not a protected type) is now recorded as low and does not
count towards the three-is-high line. The helper still counts.

These tests drive the normal caller - ``AgentInvoker._compute_plan_audit_verdict``
over a real git repository and a real task document - and hand its block to
``CoachValidator.verify_quality_gates``, the gate that refused the build.
Every file name and file content here is invented.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, List

import pytest

from guardkit.models.task_types import TaskType, get_profile
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


TASK_ID = "TASK-PAGE-001"

PLANNED_CREATE = [
    "web/src/pages/ShelfPage.tsx",
    "web/src/pages/ShelfPage.module.css",
    "web/src/components/EmptyShelf.tsx",
    "web/src/components/BookCard.tsx",
    "web/src/components/BookCard.module.css",
    "web/src/lib/bookFormatting.ts",
]
PLANNED_MODIFY = ["web/src/App.tsx"]


def _git(root: Path, *args: str) -> None:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, env=env
    )


def _write(root: Path, rel: str, text: str = "invented\n") -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def _task_document(create: List[str], modify: List[str]) -> str:
    lines = [
        "---",
        f"id: {TASK_ID}",
        "title: Build the shelf page screen",
        "status: in_progress",
        "---",
        "",
        "## Files to Create",
        "",
        *[f"- `{p}`" for p in create],
        "",
        "## Files to Modify",
        "",
        *[f"- `{p}`" for p in modify],
        "",
        "## Acceptance Criteria",
        "",
        "- [ ] The shelf page lists books.",
        "",
    ]
    return "\n".join(lines)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A repository with an existing app, an existing test and a task document."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "commit.gpgsign", "false")
    _write(root, "web/src/App.tsx", "export const App = () => null;\n")
    _write(root, "web/src/App.test.tsx", "test('renders', () => {});\n")
    _write(root, "web/Dockerfile", "FROM scratch\n")
    _write(root, "compose.yaml", "services: {}\n")
    _write(root, "README.md", "# Invented app\n")
    _write(
        root,
        f"tasks/in_progress/{TASK_ID}.md",
        _task_document(PLANNED_CREATE, PLANNED_MODIFY),
    )
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    return root


def _build_the_planned_work(root: Path) -> None:
    for path in PLANNED_CREATE:
        _write(root, path)
    _write(root, "web/src/App.tsx", "export const App = () => 'shelf';\n")


def _verdict(root: Path) -> Dict:
    invoker = AgentInvoker(
        worktree_path=root, max_turns_per_agent=1, sdk_timeout_seconds=10
    )
    return invoker._compute_plan_audit_verdict(TASK_ID)


def _gate_passes(root: Path, plan_audit: Dict) -> bool:
    validator = CoachValidator(str(root), task_id=TASK_ID)
    gates = validator.verify_quality_gates(
        {
            "task_id": TASK_ID,
            "quality_gates": {
                "all_passed": True,
                "tests_failed": 0,
                "coverage_met": True,
            },
            "code_review": {"score": 95},
            "plan_audit": plan_audit,
        },
        profile=get_profile(TaskType.FEATURE),
    )
    return bool(gates.plan_audit_passed)


class TestTheLiveShape:
    def test_page_test_and_component_stylesheet_are_low_the_helper_counts(
        self, repo: Path
    ) -> None:
        _build_the_planned_work(repo)
        # The by-products of building exactly what was planned.
        _write(repo, "web/src/ShelfPage.test.tsx", "test('lists', () => {});\n")
        _write(repo, "web/src/components/EmptyShelf.module.css", ".x {}\n")
        _write(repo, "web/src/test-harness.tsx", "export const wrap = 1;\n")
        _write(repo, "web/src/App.test.tsx", "test('renders shelf', () => {});\n")

        verdict = _verdict(repo)

        # One counted extra file (the helper) is medium, and medium passes.
        assert verdict["severity"] == "medium", verdict
        assert verdict["status"] == "passed", verdict
        assert verdict["violations"] == 0
        # Recorded and shown, never hidden.
        assert verdict["extra_files"] == [
            "web/src/ShelfPage.test.tsx",
            "web/src/components/EmptyShelf.module.css",
            "web/src/test-harness.tsx",
        ]
        assert verdict["extra_files_beside_the_plan"] == [
            "web/src/ShelfPage.test.tsx",
            "web/src/components/EmptyShelf.module.css",
        ]
        assert verdict["extra_modifications"] == ["web/src/App.test.tsx"]
        assert _gate_passes(repo, verdict)


class TestScopeCreepStillHigh:
    def test_new_container_compose_and_readme_files_are_high(
        self, repo: Path
    ) -> None:
        _build_the_planned_work(repo)
        _write(repo, "api/Dockerfile", "FROM scratch\n")
        _write(repo, "deploy/compose.yaml", "services: {}\n")
        _write(repo, "deploy/README.md", "# How to deploy\n")
        # A planned component's own test rides along; it does not hide the rest.
        _write(repo, "web/src/pages/ShelfPage.test.tsx", "test('x', () => {});\n")

        verdict = _verdict(repo)

        assert verdict["status"] == "violation", verdict
        assert verdict["severity"] == "high"
        assert verdict["violations"] >= 1
        for path in ("api/Dockerfile", "deploy/compose.yaml", "deploy/README.md"):
            assert path in verdict["extra_files"]
            assert path not in verdict["extra_files_beside_the_plan"]
        assert verdict["extra_files_beside_the_plan"] == [
            "web/src/pages/ShelfPage.test.tsx"
        ]
        assert not _gate_passes(repo, verdict)

    def test_a_test_of_something_nobody_planned_still_counts(
        self, repo: Path
    ) -> None:
        _build_the_planned_work(repo)
        _write(repo, "web/src/billing/invoice.ts", "export const i = 1;\n")
        _write(repo, "web/src/billing/invoice.test.ts", "test('i', () => {});\n")
        _write(repo, "web/src/billing/fixtures.ts", "export const f = 1;\n")

        verdict = _verdict(repo)

        assert verdict["severity"] == "high", verdict
        assert verdict["extra_files_beside_the_plan"] == []
        assert not _gate_passes(repo, verdict)

    def test_unrelated_test_helper_and_asset_in_a_planned_folder_count(
        self, repo: Path
    ) -> None:
        _build_the_planned_work(repo)
        _write(repo, "web/src/components/OtherThing.test.tsx", "test('o', () => {});\n")
        _write(repo, "web/src/components/renderHelpers.tsx", "export const r = 1;\n")
        _write(repo, "web/src/components/logo.svg", "<svg/>\n")

        verdict = _verdict(repo)

        assert verdict["severity"] == "high", verdict
        assert verdict["extra_files_beside_the_plan"] == []
        assert not _gate_passes(repo, verdict)

    def test_protected_files_named_after_a_planned_file_still_count(
        self, repo: Path
    ) -> None:
        _build_the_planned_work(repo)
        _write(repo, "web/src/pages/ShelfPage.test.tsx", "test('x', () => {});\n")
        _write(repo, "web/src/pages/ShelfPage.Dockerfile", "FROM scratch\n")
        _write(repo, "web/src/pages/ShelfPage.README.md", "# Shelf\n")
        _write(repo, "web/src/pages/compose.yaml", "services: {}\n")
        _write(repo, "web/src/pages/migrations/ShelfPage.sql", "SELECT 1;\n")

        verdict = _verdict(repo)

        assert verdict["severity"] == "high", verdict
        assert verdict["extra_files_beside_the_plan"] == [
            "web/src/pages/ShelfPage.test.tsx"
        ]
        assert not _gate_passes(repo, verdict)

    def test_changed_dockerfile_compose_and_readme_are_named(
        self, repo: Path
    ) -> None:
        """Changes to existing files the plan did not name are reported as
        unplanned modifications. Their severity is unchanged by this fix
        (low, as before); the audit names them so the Coach and the merge
        card can see them."""
        _build_the_planned_work(repo)
        _write(repo, "web/Dockerfile", "FROM scratch\nEXPOSE 1\n")
        _write(repo, "compose.yaml", "services: {web: {}}\n")
        _write(repo, "README.md", "# Invented app, changed\n")

        verdict = _verdict(repo)

        assert verdict["extra_modifications"] == [
            "README.md",
            "compose.yaml",
            "web/Dockerfile",
        ]


class TestTheCoachFeedbackWording:
    def test_feedback_counts_the_scope_creep_and_names_the_tests_apart(
        self, repo: Path
    ) -> None:
        _build_the_planned_work(repo)
        _write(repo, "api/Dockerfile", "FROM scratch\n")
        _write(repo, "deploy/compose.yaml", "services: {}\n")
        _write(repo, "deploy/README.md", "# How to deploy\n")
        _write(repo, "web/src/pages/ShelfPage.test.tsx", "test('x', () => {});\n")
        verdict = _verdict(repo)

        validator = CoachValidator(str(repo), task_id=TASK_ID)
        results = {
            "task_id": TASK_ID,
            "quality_gates": {
                "all_passed": True, "tests_failed": 0, "coverage_met": True,
            },
            "code_review": {"score": 95},
            "plan_audit": verdict,
        }
        gates = validator.verify_quality_gates(
            results, profile=get_profile(TaskType.FEATURE)
        )
        result = validator._feedback_from_gates(
            TASK_ID, 1, gates, results, task_type="feature"
        )
        issue = next(i for i in result.issues if i["category"] == "plan_audit")

        assert issue["severity"] == "must_fix"
        text = issue["description"]
        assert "high-severity" in text
        assert (
            "3 extra file(s): api/Dockerfile, deploy/README.md, "
            "deploy/compose.yaml" in text
        )
        assert "1 file(s) named after a planned file" in text
        assert "ShelfPage.test.tsx" not in text.split("— and")[0]
