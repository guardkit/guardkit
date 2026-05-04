"""
Tests for TASK-FIX-AB61: pre-create worktree symlinks for
``[tool.uv.sources]`` path entries.

Covers the gap left by TASK-FIX-F09A2 AC #4: F09A2 selected the right
install command and AB60 ensured a venv exists, but neither addressed
the asymmetry between how uv resolves a path-typed source from the
source repo vs. from a worktree at a different filesystem location.
AB61 closes that gap by parsing the source pyproject's
``[tool.uv.sources]`` table and pre-creating the bridging symlinks.

Coverage Target: >=85%

Resolver helper cases (AC #1-7):
1. ``path = "../sibling"`` from worktree at
   ``<source>/.guardkit/worktrees/<feat>/`` → emits
   ``(<source>/.guardkit/worktrees/sibling, <source>/../sibling)``.
2. ``path = "../../far-sibling"`` → emits
   ``(<source>/.guardkit/far-sibling, <source>/../../far-sibling)``.
3. ``path = "./vendor/foo"`` → emits nothing (worktree-internal).
4. No ``[tool.uv.sources]`` table → emits nothing.
5. ``[tool.uv.sources]`` with ``git = "..."`` only → emits nothing.
6. ``path = "../missing"`` where target doesn't exist → emits nothing
   + warning logged.
7. Multiple uv-sources entries → emits one tuple per external path.

Creator helper cases (AC #8-12):
8. Empty list → no-op.
9. Single (symlink, target), neither exists → symlink created.
10. Pre-existing symlink at the same path pointing elsewhere →
    replaced with new target.
11. Pre-existing symlink already pointing at correct target →
    left alone (no error).
12. Pre-existing **non-symlink** (real directory) at symlink path →
    warning logged, no overwrite.

Integration cases (AC #13-14):
13. uv-sources with sibling path → resolver + creator chain produces a
    valid symlink at the expected worktree-relative path.
14. Project with no uv-sources → no symlinks attempted (clean log).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Tuple

import pytest

from guardkit.orchestrator.environment_bootstrap import (
    _create_worktree_uv_sources_symlinks,
    _resolve_uv_sources_symlinks,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _portfolio_layout(tmp_path: Path) -> Tuple[Path, Path, Path]:
    """
    Build a minimal portfolio layout::

        tmp_path/
            source_repo/
                pyproject.toml
                .guardkit/worktrees/<feat>/
                    pyproject.toml          <- worktree checkout
            sibling/
                pyproject.toml              <- the sibling source

    Returns ``(source_pyproject, worktree_pyproject, sibling_dir)``.
    """
    source_repo = tmp_path / "source_repo"
    source_repo.mkdir()
    source_pyproject = source_repo / "pyproject.toml"
    source_pyproject.write_text(
        '[project]\nname = "x"\nversion = "0.1.0"\n', encoding="utf-8"
    )

    worktree_dir = source_repo / ".guardkit" / "worktrees" / "FEAT-TEST"
    worktree_dir.mkdir(parents=True)
    worktree_pyproject = worktree_dir / "pyproject.toml"
    worktree_pyproject.write_text(
        '[project]\nname = "x"\nversion = "0.1.0"\n', encoding="utf-8"
    )

    sibling = tmp_path / "sibling"
    sibling.mkdir()
    (sibling / "pyproject.toml").write_text(
        '[project]\nname = "sibling"\nversion = "0.1.0"\n', encoding="utf-8"
    )

    return source_pyproject, worktree_pyproject, sibling


def _write_uv_sources(pyproject_path: Path, body: str) -> None:
    """Append a ``[tool.uv.sources]`` body to a pyproject."""
    pyproject_path.write_text(
        '[project]\nname = "x"\nversion = "0.1.0"\n' + body,
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# TestResolveUvSourcesSymlinks (AC #1-7)
# ---------------------------------------------------------------------------


class TestResolveUvSourcesSymlinks:
    """Resolver helper algorithm — pyproject parse + path bridging."""

    def test_sibling_path_emits_bridging_pair(self, tmp_path):
        """AC #1: ``path = "../sibling"`` emits worktree → source pair."""
        source_pyproject, worktree_pyproject, sibling = _portfolio_layout(tmp_path)
        # Worktree is at <source>/.guardkit/worktrees/FEAT-TEST/.
        # Sibling lives at <tmp_path>/sibling. Choose the path string that
        # makes the source-repo perspective resolve to the sibling.
        rel_from_source = os.path.relpath(sibling, source_pyproject.parent)
        _write_uv_sources(
            source_pyproject,
            f'[tool.uv.sources]\nsibling = {{ path = "{rel_from_source}" }}\n',
        )
        _write_uv_sources(
            worktree_pyproject,
            f'[tool.uv.sources]\nsibling = {{ path = "{rel_from_source}" }}\n',
        )

        symlinks = _resolve_uv_sources_symlinks(
            source_pyproject, worktree_pyproject
        )

        assert len(symlinks) == 1
        symlink_path, target_path = symlinks[0]
        # Worktree resolves the rel path from its own dir → wrong location.
        assert symlink_path == (worktree_pyproject.parent / rel_from_source).resolve()
        # Source resolves the same string from its dir → real sibling.
        assert target_path == sibling.resolve()
        assert symlink_path != target_path

    def test_far_sibling_path_emits_bridging_pair(self, tmp_path):
        """AC #2: deeper ``../../...`` traversal still bridges correctly."""
        # Build: tmp/source_repo/, tmp/far/sibling/.
        # From source_repo's pyproject, "../far/sibling" resolves to
        # tmp/far/sibling. From the worktree, the same string resolves
        # somewhere bogus inside the .guardkit tree.
        source_repo = tmp_path / "source_repo"
        source_repo.mkdir()
        source_pyproject = source_repo / "pyproject.toml"

        worktree_dir = source_repo / ".guardkit" / "worktrees" / "FEAT-TEST"
        worktree_dir.mkdir(parents=True)
        worktree_pyproject = worktree_dir / "pyproject.toml"

        far_sibling = tmp_path / "far" / "sibling"
        far_sibling.mkdir(parents=True)

        rel = "../far/sibling"
        _write_uv_sources(
            source_pyproject,
            f'[tool.uv.sources]\nfar = {{ path = "{rel}" }}\n',
        )
        _write_uv_sources(
            worktree_pyproject,
            f'[tool.uv.sources]\nfar = {{ path = "{rel}" }}\n',
        )

        symlinks = _resolve_uv_sources_symlinks(
            source_pyproject, worktree_pyproject
        )

        assert len(symlinks) == 1
        symlink_path, target_path = symlinks[0]
        assert target_path == far_sibling.resolve()
        assert symlink_path == (worktree_pyproject.parent / rel).resolve()

    def test_worktree_internal_path_emits_nothing(self, tmp_path):
        """AC #3: ``./vendor/foo`` lives inside worktree → no symlink."""
        source_pyproject, worktree_pyproject, _ = _portfolio_layout(tmp_path)
        # Create the vendor dir on the source side so source_resolved exists.
        # But because the path is relative-to-pyproject, both sides resolve
        # the SAME way relative to their own pyproject parents — except
        # source's side will resolve to a nonexistent location relative
        # to source_repo. Use a string that yields equal absolute paths
        # only when the target lives inside the worktree's checkout.
        # The cleanest way is a path that, relative to BOTH pyprojects,
        # points inside the worktree itself. That requires the source
        # pyproject's path to use a deep traversal that just happens to
        # land at the same absolute as the worktree-relative one — not
        # something users do in practice.
        #
        # Instead, exercise the equivalence branch directly: write a
        # `path` whose source-side and worktree-side resolutions are
        # equal. Easiest: same absolute path on both sides, achieved by
        # making source and worktree pyprojects share the same parent
        # (degenerate case the helper still handles correctly).
        shared_dir = tmp_path / "shared"
        shared_dir.mkdir()
        shared_py = shared_dir / "pyproject.toml"
        vendor = shared_dir / "vendor" / "foo"
        vendor.mkdir(parents=True)
        _write_uv_sources(
            shared_py,
            '[tool.uv.sources]\nfoo = { path = "./vendor/foo" }\n',
        )

        symlinks = _resolve_uv_sources_symlinks(shared_py, shared_py)

        assert symlinks == []

    def test_no_uv_sources_table_emits_nothing(self, tmp_path):
        """AC #4: pyproject without ``[tool.uv.sources]`` → empty list."""
        source_pyproject, worktree_pyproject, _ = _portfolio_layout(tmp_path)
        # Both pyprojects already have just [project], no sources.

        symlinks = _resolve_uv_sources_symlinks(
            source_pyproject, worktree_pyproject
        )

        assert symlinks == []

    def test_git_only_uv_sources_emits_nothing(self, tmp_path):
        """AC #5: only non-path entries (git/index/workspace/url) → empty."""
        source_pyproject, worktree_pyproject, _ = _portfolio_layout(tmp_path)
        body = (
            "[tool.uv.sources]\n"
            'foo = { git = "https://example.com/foo.git" }\n'
            'bar = { index = "private" }\n'
            "baz = { workspace = true }\n"
            'qux = { url = "https://example.com/qux.tar.gz" }\n'
        )
        _write_uv_sources(source_pyproject, body)
        _write_uv_sources(worktree_pyproject, body)

        symlinks = _resolve_uv_sources_symlinks(
            source_pyproject, worktree_pyproject
        )

        assert symlinks == []

    def test_missing_target_emits_nothing_with_warning(self, tmp_path, caplog):
        """AC #6: source-side path doesn't exist → skip + warn."""
        source_repo = tmp_path / "source_repo"
        source_repo.mkdir()
        source_pyproject = source_repo / "pyproject.toml"
        worktree_dir = source_repo / ".guardkit" / "worktrees" / "FEAT-TEST"
        worktree_dir.mkdir(parents=True)
        worktree_pyproject = worktree_dir / "pyproject.toml"

        # Reference a sibling that doesn't exist on disk.
        body = '[tool.uv.sources]\nmissing = { path = "../missing-sibling" }\n'
        _write_uv_sources(source_pyproject, body)
        _write_uv_sources(worktree_pyproject, body)

        with caplog.at_level(logging.WARNING):
            symlinks = _resolve_uv_sources_symlinks(
                source_pyproject, worktree_pyproject
            )

        assert symlinks == []
        assert any(
            "missing" in r.getMessage() and "does not exist" in r.getMessage()
            for r in caplog.records
        )

    def test_multiple_external_path_entries_each_emit_a_pair(self, tmp_path):
        """AC #7: N path-typed entries → N tuples (each independent)."""
        source_repo = tmp_path / "source_repo"
        source_repo.mkdir()
        source_pyproject = source_repo / "pyproject.toml"
        worktree_dir = source_repo / ".guardkit" / "worktrees" / "FEAT-TEST"
        worktree_dir.mkdir(parents=True)
        worktree_pyproject = worktree_dir / "pyproject.toml"

        # Two distinct external siblings.
        sibling_a = tmp_path / "a"
        sibling_a.mkdir()
        sibling_b = tmp_path / "b"
        sibling_b.mkdir()

        rel_a = os.path.relpath(sibling_a, source_repo)
        rel_b = os.path.relpath(sibling_b, source_repo)
        body = (
            "[tool.uv.sources]\n"
            f'a = {{ path = "{rel_a}" }}\n'
            f'b = {{ path = "{rel_b}" }}\n'
        )
        _write_uv_sources(source_pyproject, body)
        _write_uv_sources(worktree_pyproject, body)

        symlinks = _resolve_uv_sources_symlinks(
            source_pyproject, worktree_pyproject
        )

        assert len(symlinks) == 2
        targets = {target for (_, target) in symlinks}
        assert targets == {sibling_a.resolve(), sibling_b.resolve()}


# ---------------------------------------------------------------------------
# TestCreateWorktreeUvSourcesSymlinks (AC #8-12)
# ---------------------------------------------------------------------------


class TestCreateWorktreeUvSourcesSymlinks:
    """Creator helper — idempotent symlink writes with safety guards."""

    def test_empty_list_is_noop(self, tmp_path):
        """AC #8: empty input → no exceptions, no filesystem changes."""
        # Just confirm it returns without raising.
        _create_worktree_uv_sources_symlinks([])
        assert list(tmp_path.iterdir()) == []

    def test_creates_new_symlink(self, tmp_path):
        """AC #9: neither symlink nor target-path-conflict → create."""
        target = tmp_path / "target"
        target.mkdir()
        symlink_path = tmp_path / "subdir" / "link"
        # Parent doesn't exist yet — creator must mkdir it.

        _create_worktree_uv_sources_symlinks([(symlink_path, target)])

        assert symlink_path.is_symlink()
        assert symlink_path.resolve() == target.resolve()

    def test_replaces_symlink_pointing_elsewhere(self, tmp_path):
        """AC #10: pre-existing symlink to wrong target → replaced."""
        old_target = tmp_path / "old"
        old_target.mkdir()
        new_target = tmp_path / "new"
        new_target.mkdir()
        symlink_path = tmp_path / "link"
        os.symlink(old_target, symlink_path)
        assert symlink_path.resolve() == old_target.resolve()

        _create_worktree_uv_sources_symlinks([(symlink_path, new_target)])

        assert symlink_path.is_symlink()
        assert symlink_path.resolve() == new_target.resolve()

    def test_preserves_symlink_pointing_at_correct_target(self, tmp_path):
        """AC #11: pre-existing symlink already correct → leave alone."""
        target = tmp_path / "target"
        target.mkdir()
        symlink_path = tmp_path / "link"
        os.symlink(target, symlink_path)
        original_inode = os.lstat(symlink_path).st_ino

        _create_worktree_uv_sources_symlinks([(symlink_path, target)])

        assert symlink_path.is_symlink()
        assert symlink_path.resolve() == target.resolve()
        # Inode unchanged → symlink was not recreated.
        assert os.lstat(symlink_path).st_ino == original_inode

    def test_skips_non_symlink_at_path_with_warning(self, tmp_path, caplog):
        """AC #12: existing real directory → warn + skip (no overwrite)."""
        target = tmp_path / "target"
        target.mkdir()
        # Real directory, NOT a symlink, at the symlink path.
        real_dir = tmp_path / "would-be-link"
        real_dir.mkdir()
        sentinel = real_dir / "sentinel.txt"
        sentinel.write_text("preserve me", encoding="utf-8")

        with caplog.at_level(logging.WARNING):
            _create_worktree_uv_sources_symlinks([(real_dir, target)])

        # Real dir untouched.
        assert real_dir.exists()
        assert not real_dir.is_symlink()
        assert sentinel.read_text(encoding="utf-8") == "preserve me"
        assert any(
            "not a symlink" in r.getMessage() for r in caplog.records
        )


# ---------------------------------------------------------------------------
# TestEndToEnd (AC #13-14)
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """Resolver + creator together against realistic portfolio shapes."""

    def test_sibling_path_resolves_then_creates_correct_symlink(self, tmp_path):
        """AC #13: full chain produces a usable symlink for uv."""
        source_pyproject, worktree_pyproject, sibling = _portfolio_layout(tmp_path)
        rel = os.path.relpath(sibling, source_pyproject.parent)
        body = f'[tool.uv.sources]\nsibling = {{ path = "{rel}" }}\n'
        _write_uv_sources(source_pyproject, body)
        _write_uv_sources(worktree_pyproject, body)

        symlinks = _resolve_uv_sources_symlinks(
            source_pyproject, worktree_pyproject
        )
        _create_worktree_uv_sources_symlinks(symlinks)

        # The path uv WILL look at from the worktree now resolves to the
        # real sibling source.
        worktree_view = (worktree_pyproject.parent / rel).resolve()
        assert worktree_view.exists()
        # And it really is the same directory the source repo sees.
        assert worktree_view == sibling.resolve()

    def test_no_uv_sources_means_no_symlinks_attempted(self, tmp_path):
        """AC #14: vanilla project → resolver returns [], creator no-ops."""
        source_pyproject, worktree_pyproject, _ = _portfolio_layout(tmp_path)
        # Pyprojects have no [tool.uv.sources] (default _portfolio_layout).

        symlinks = _resolve_uv_sources_symlinks(
            source_pyproject, worktree_pyproject
        )
        _create_worktree_uv_sources_symlinks(symlinks)

        assert symlinks == []
        # Nothing under the worktree's parent except the worktree itself.
        guardkit_dir = source_pyproject.parent / ".guardkit"
        # The only thing inside .guardkit/worktrees/ should be FEAT-TEST.
        worktrees_dir = guardkit_dir / "worktrees"
        assert sorted(p.name for p in worktrees_dir.iterdir()) == ["FEAT-TEST"]
