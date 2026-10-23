"""A bare file name in a task document's file sections means the one file it names.

Build FEAT-D31F's repair (19 October 2026): a fix task declared, under
``## Files to Modify``, both the full paths of the two files to change and
their bare names. The fix task writer had picked up every backticked file name
in the review's recommendation. The plan audit looked for each bare name at
the top of the repository, did not find it, and refused all three turns with
"2 missing file(s)" while the builder had edited exactly the right two files.

A bare name that matches exactly one repository file is now that file. A bare
name that matches two or more files stays as written, so it is still missing
and the message says why: an ambiguous name must never pass silently.

These tests drive the normal caller - ``AgentInvoker._compute_plan_audit_verdict``
over a real git repository and a real task document - and hand the block to
``CoachValidator.verify_quality_gates``, the gate that refused the build.
Every file name and file content here is invented. No network, no model.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Dict, List

import pytest

from guardkit.models.task_types import TaskType, get_profile
from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.declared_paths import resolve_bare_names
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


TASK_ID = "TASK-LINT-002"


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
        "title: Fix the lint errors in the shelf app",
        "status: in_progress",
        "---",
        "",
        "## Acceptance Criteria",
        "",
        "- [ ] The lint check passes.",
        "",
    ]
    if create:
        lines += ["## Files to Create", "", *[f"- `{p}`" for p in create], ""]
    lines += ["## Files to Modify", "", *[f"- `{p}`" for p in modify], ""]
    return "\n".join(lines)


def _repo(tmp_path: Path, create: List[str], modify: List[str]) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "commit.gpgsign", "false")
    _write(root, "apps/shelf/src/Shelf.tsx", "export const Shelf = () => null;\n")
    _write(root, "apps/shelf/src/Shelf.test.tsx", "test('renders', () => {});\n")
    _write(root, "README.md", "# Invented app\n")
    _write(root, f"tasks/in_progress/{TASK_ID}.md", _task_document(create, modify))
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    return root


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


LIVE_MODIFY = [
    "apps/shelf/src/Shelf.test.tsx",
    "apps/shelf/src/Shelf.tsx",
    "Shelf.test.tsx",
    "Shelf.tsx",
]

FOUR_CREATED_FILES = [
    "src/catalog/index.ts",
    "src/catalog/reader.ts",
    "test/catalog.test.ts",
    "vitest.config.ts",
]


class TestNestedNoFileMarkerParsing:
    def test_exact_observed_marker_is_explicit_empty_in_both_modes(self) -> None:
        text = "## Files to Modify\n- `- _none_`\n"

        assert AgentInvoker.declared_file_sections_in_text(text) == {
            "create": None,
            "modify": [],
        }
        assert AgentInvoker.declared_file_sections_in_text(
            text, keep_every_entry=True
        ) == {"create": None, "modify": []}

        assert AgentInvoker.declared_file_sections_in_text("notes only") == {
            "create": None,
            "modify": None,
        }
        assert AgentInvoker.declared_file_sections_in_text(
            "## Files to Modify\n"
        ) == {"create": None, "modify": None}

    @pytest.mark.parametrize("marker", ["_none_", "none", "N/A", "tbd"])
    def test_existing_markers_remain_empty(self, marker: str) -> None:
        text = f"## Files to Modify\n- `{marker}`\n"

        assert AgentInvoker.declared_file_sections_in_text(text)["modify"] == []
        assert AgentInvoker.declared_file_sections_in_text(
            text, keep_every_entry=True
        )["modify"] == []

    def test_real_paths_are_returned_without_normalising_them(self) -> None:
        text = (
            "## Files to Modify\n"
            "- `-release.py`\n"
            "- `none.py`\n"
            "- `src/none`\n"
            "- `__init__.py`\n"
            "- `src/*`\n"
            "- `src/*.py`\n"
        )

        assert AgentInvoker.declared_file_sections_in_text(text)["modify"] == [
            "-release.py",
            "none.py",
            "src/none",
        ]
        assert AgentInvoker.declared_file_sections_in_text(
            text, keep_every_entry=True
        )["modify"] == [
            "-release.py",
            "none.py",
            "src/none",
            "__init__.py",
            "src/*",
            "src/*.py",
        ]


class TestNestedNoFileMarkerAudit:
    def test_four_created_files_pass_without_fake_modify_findings(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path, FOUR_CREATED_FILES, ["- _none_"])
        for path in FOUR_CREATED_FILES:
            _write(repo, path)

        verdict = _verdict(repo)

        assert verdict["status"] == "passed", verdict
        assert verdict["missing_files"] == []
        assert verdict["missing_modifications"] == []
        assert verdict["extra_modifications"] == []
        assert verdict["message"].endswith("all 4 declared file(s) are on disk")

    def test_a_genuinely_missing_created_file_still_fails(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path, FOUR_CREATED_FILES, ["- _none_"])
        for path in FOUR_CREATED_FILES[:-1]:
            _write(repo, path)

        verdict = _verdict(repo)

        assert verdict["status"] == "violation", verdict
        assert verdict["severity"] == "high"
        assert verdict["missing_files"] == [FOUR_CREATED_FILES[-1]]
        assert verdict["missing_modifications"] == []

    def test_three_unplanned_created_files_keep_the_high_severity_refusal(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path, FOUR_CREATED_FILES, ["- _none_"])
        for path in FOUR_CREATED_FILES:
            _write(repo, path)
        extras = [
            "src/sprawl/one.ts",
            "src/sprawl/two.ts",
            "test/sprawl.test.ts",
        ]
        for path in extras:
            _write(repo, path)

        verdict = _verdict(repo)

        assert verdict["status"] == "violation", verdict
        assert verdict["severity"] == "high"
        assert verdict["extra_files"] == sorted(extras)

    def test_a_real_unplanned_modification_remains_visible_without_escalation(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path, FOUR_CREATED_FILES, ["- _none_"])
        for path in FOUR_CREATED_FILES:
            _write(repo, path)
        _write(repo, "README.md", "changed invented app\n")

        verdict = _verdict(repo)

        assert verdict["status"] == "passed", verdict
        assert verdict["severity"] == "low"
        assert verdict["extra_modifications"] == ["README.md"]
        assert verdict["missing_modifications"] == []


class TestTheLiveShape:
    def test_full_paths_and_bare_names_of_the_edited_files_pass(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path, [], LIVE_MODIFY)
        _write(repo, "apps/shelf/src/Shelf.tsx", "export const Shelf = () => 1;\n")
        _write(repo, "apps/shelf/src/Shelf.test.tsx", "test('one', () => {});\n")

        verdict = _verdict(repo)

        assert verdict["status"] == "passed", verdict
        assert verdict["missing_files"] == []
        assert verdict["missing_modifications"] == []
        assert verdict["violations"] == 0
        assert verdict["bare_names_resolved"] == {
            "Shelf.test.tsx": "apps/shelf/src/Shelf.test.tsx",
            "Shelf.tsx": "apps/shelf/src/Shelf.tsx",
        }
        assert verdict["bare_names_ambiguous"] == {}
        assert _gate_passes(repo, verdict)

    def test_before_the_edit_the_files_are_unmodified_but_not_missing(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path, [], LIVE_MODIFY)

        verdict = _verdict(repo)

        # Nothing is missing from disk; the planned files are simply not yet
        # changed, which is reported as before.
        assert verdict["missing_files"] == []
        assert sorted(verdict["missing_modifications"]) == [
            "apps/shelf/src/Shelf.test.tsx",
            "apps/shelf/src/Shelf.tsx",
        ]


class TestAmbiguousNamesNeverPass:
    def test_a_name_that_matches_two_files_is_missing_and_said_so(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path, [], ["apps/shelf/src/Shelf.tsx", "index.ts"])
        _write(repo, "apps/shelf/src/index.ts", "export {};\n")
        _write(repo, "apps/api/src/index.ts", "export {};\n")
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "two files with one name")
        _write(repo, "apps/shelf/src/Shelf.tsx", "export const Shelf = () => 1;\n")
        _write(repo, "apps/shelf/src/index.ts", "export const x = 1;\n")

        verdict = _verdict(repo)

        assert verdict["status"] == "violation", verdict
        assert verdict["severity"] == "high"
        assert "index.ts" in verdict["missing_files"]
        assert verdict["bare_names_ambiguous"] == {
            "index.ts": ["apps/api/src/index.ts", "apps/shelf/src/index.ts"]
        }
        assert "index.ts is a bare file name that matches 2 files" in verdict["message"]
        assert "must give the full path" in verdict["message"]
        assert not _gate_passes(repo, verdict)

    def test_a_name_that_matches_nothing_is_still_missing(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path, [], ["apps/shelf/src/Shelf.tsx", "Nowhere.tsx"])
        _write(repo, "apps/shelf/src/Shelf.tsx", "export const Shelf = () => 1;\n")

        verdict = _verdict(repo)

        assert verdict["status"] == "violation", verdict
        assert verdict["missing_files"] == ["Nowhere.tsx"]
        assert verdict["bare_names_resolved"] == {}
        assert not _gate_passes(repo, verdict)


class TestCreatedFiles:
    def test_a_bare_name_to_create_resolves_once_the_build_makes_it(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path, ["ShelfCount.tsx"], ["apps/shelf/src/Shelf.tsx"])
        _write(repo, "apps/shelf/src/Shelf.tsx", "export const Shelf = () => 1;\n")
        _write(repo, "apps/shelf/src/ShelfCount.tsx", "export const C = 1;\n")

        verdict = _verdict(repo)

        assert verdict["status"] == "passed", verdict
        assert verdict["bare_names_resolved"] == {
            "ShelfCount.tsx": "apps/shelf/src/ShelfCount.tsx"
        }
        assert verdict["extra_files"] == []

    def test_a_bare_name_to_create_that_was_not_made_is_missing(
        self, tmp_path: Path
    ) -> None:
        repo = _repo(tmp_path, ["ShelfCount.tsx"], ["apps/shelf/src/Shelf.tsx"])
        _write(repo, "apps/shelf/src/Shelf.tsx", "export const Shelf = () => 1;\n")

        verdict = _verdict(repo)

        assert verdict["status"] == "violation", verdict
        assert "ShelfCount.tsx" in verdict["missing_files"]


class TestResolveBareNames:
    def test_absent_section_stays_absent(self, tmp_path: Path) -> None:
        assert (
            resolve_bare_names(None, worktree_path=tmp_path, candidates=["a/b.py"])
            is None
        )

    def test_full_paths_are_untouched_and_duplicates_collapse(
        self, tmp_path: Path
    ) -> None:
        outcome = resolve_bare_names(
            ["src/a/b.py", "b.py", "docs/x.md"],
            worktree_path=tmp_path,
            candidates=["src/a/b.py", "docs/x.md"],
        )
        assert outcome.paths == ["src/a/b.py", "docs/x.md"]
        assert outcome.resolved == {"b.py": "src/a/b.py"}

    def test_a_file_at_the_top_is_taken_as_written(self, tmp_path: Path) -> None:
        (tmp_path / "Makefile").write_text("all:\n")
        outcome = resolve_bare_names(
            ["Makefile"],
            worktree_path=tmp_path,
            candidates=["Makefile", "sub/Makefile"],
        )
        assert outcome.paths == ["Makefile"]
        assert outcome.resolved == {}
        assert outcome.ambiguous == {}

    def test_excluded_paths_are_not_candidates(self, tmp_path: Path) -> None:
        outcome = resolve_bare_names(
            ["state.json"],
            worktree_path=tmp_path,
            candidates=[".guardkit/autobuild/T/state.json", "src/state.json"],
            excluded=lambda p: p.startswith(".guardkit/"),
        )
        assert outcome.paths == ["src/state.json"]
