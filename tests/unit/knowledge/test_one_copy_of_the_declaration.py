"""Everything a project declares about its memory is read from ONE copy.

The stage-1 review's two-copies question (2026-09-21). The orchestrator settled
the memory name from ``repo_root`` — the build's own working folder — while the
neighbouring pattern-sources reader read ``worktree_path``, the per-task
worktree. Two copies of one file, able to disagree with each other for a whole
build.

Now both read the build's working folder, and the name handed over on purpose
still wins over both.

Nothing here contacts a memory service, a database, an embedder, a door or any
broker: everything is a folder in a temporary directory and a settings file.
"""

from __future__ import annotations

from pathlib import Path

from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader
from guardkit.knowledge.memory_project import resolve_memory_project

DECLARES = """\
memory:
  project: widget_shop
  fleet:
    context_sources:
      relevant_patterns:
        document_tags:
          - the_builds_own_folder
"""

DECLARES_SOMETHING_ELSE = """\
memory:
  project: a_stale_worktrees_idea
  fleet:
    context_sources:
      relevant_patterns:
        document_tags:
          - a_stale_worktrees_idea
"""


def _declare(folder: Path, text: str) -> Path:
    (folder / ".guardkit").mkdir(parents=True, exist_ok=True)
    (folder / ".guardkit" / "config.yaml").write_text(text, encoding="utf-8")
    return folder


def _tags(loader: AutoBuildContextLoader) -> tuple[str, ...]:
    """The pattern-source tags this loader would use, without a memory client."""
    from guardkit.knowledge.autobuild_context_loader import (
        _load_relevant_pattern_document_tags,
    )

    return _load_relevant_pattern_document_tags(loader.declaration_root)


def test_both_readers_read_the_builds_own_folder(tmp_path: Path) -> None:
    """The build's folder and the per-task worktree declare different things.
    The build's folder is what both readers use."""
    build_folder = _declare(tmp_path / "build", DECLARES)
    per_task_worktree = _declare(tmp_path / "worktree", DECLARES_SOMETHING_ELSE)

    loader = AutoBuildContextLoader(
        graphiti=None,
        worktree_path=per_task_worktree,
        declaration_root=build_folder,
    )

    assert resolve_memory_project(build_folder, env={}).project == "widget_shop"
    assert _tags(loader) == ("the_builds_own_folder",)
    # The per-task worktree is still what local file reads use — turn state,
    # planned targets, the template manifest all belong to the task.
    assert loader.worktree_path == per_task_worktree


def test_the_declaration_root_falls_back_to_the_worktree(tmp_path: Path) -> None:
    """A caller that knows only a worktree behaves exactly as it always has."""
    folder = _declare(tmp_path / "only", DECLARES)

    loader = AutoBuildContextLoader(graphiti=None, worktree_path=folder)

    assert loader.declaration_root == folder
    assert _tags(loader) == ("the_builds_own_folder",)


def test_neither_reader_is_given_a_folder_at_all(tmp_path: Path) -> None:
    loader = AutoBuildContextLoader(graphiti=None)

    assert loader.declaration_root is None
    assert _tags(loader) == ()
    assert resolve_memory_project(None, env={}).project is None


def test_the_handed_over_name_still_wins_over_the_folders_declaration(
    tmp_path: Path,
) -> None:
    """Forge reads the declaration at the commit the work started from and hands
    the name over. A working copy — however stale — must not overrule it."""
    build_folder = _declare(tmp_path / "build", DECLARES)

    handed = resolve_memory_project(
        build_folder, env={"GUARDKIT_MEMORY_PROJECT": "the_name_forge_read"}
    )

    assert handed.project == "the_name_forge_read"
    assert handed.source == "handover"


def test_the_pattern_sources_and_the_name_come_out_of_the_same_file(
    tmp_path: Path,
) -> None:
    """The point of the change, said once: one file answers both questions, so
    they cannot disagree."""
    build_folder = _declare(tmp_path / "build", DECLARES)
    loader = AutoBuildContextLoader(
        graphiti=None,
        worktree_path=_declare(tmp_path / "worktree", DECLARES_SOMETHING_ELSE),
        declaration_root=build_folder,
    )

    name = resolve_memory_project(loader.declaration_root, env={}).project

    assert name == "widget_shop"
    assert _tags(loader) == ("the_builds_own_folder",)
    assert "a_stale_worktrees_idea" not in (name or "")
