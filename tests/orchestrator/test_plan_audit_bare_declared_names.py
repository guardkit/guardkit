"""How a task document's file sections are read, and how a bare file name
in them is resolved to the one file it names.

Build FEAT-D31F's repair (19 October 2026): a fix task declared, under
``## Files to Modify``, both the full paths of the two files to change and
their bare names. A bare name that matches exactly one repository file is now
that file; a name that matches two or more stays as written.

(27 October 2026 cull: the plan audit no longer sends work back, so the tests
that drove its verdict through the quality gate are deleted. The parsing of
the file sections and the bare-name resolution stay, and are tested here.)
Every file name here is invented. No network, no model.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardkit.orchestrator.agent_invoker import AgentInvoker
from guardkit.orchestrator.declared_paths import resolve_bare_names


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
