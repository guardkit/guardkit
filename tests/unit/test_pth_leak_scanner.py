"""
Tests for TASK-FIX-FF62 (FEAT-FFC6): pth-leak scanner.

Detects dangling editable ``_editable_impl_*.pth`` references in known
parent venv roots that point into a worktree about to be removed.

This is Layer 3 (defense-in-depth) on top of TASK-FIX-FF61 (Layer 1):
even though FF61 makes parent-venv leaks impossible at write time, an
independent verification at the cleanup boundary is the prescribed
remediation for the *absence-of-failure-is-not-success* class of defect.

See:
    - .claude/reviews/TASK-REV-FFC6-review-report.md (Layer 3 sequence)
    - .claude/rules/absence-of-failure-is-not-success.md
    - tasks/in_progress/autobuild-bootstrap-venv-isolation/
      TASK-FIX-FF62-feature-complete-detect-and-warn-on-pth-leak.md
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from guardkit.worktrees.pth_leak_scanner import (
    find_pth_leaks,
    warn_pth_leaks,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_venv_pth(
    repo_root: Path,
    pth_basename: str,
    line: str,
    *,
    py_version: str = "python3.13",
    venv_dirname: str = ".venv",
) -> Path:
    """
    Create ``<repo_root>/<venv_dirname>/lib/<py>/site-packages/<pth>`` and
    write the given line as the .pth file's content.
    """
    site_packages = (
        repo_root / venv_dirname / "lib" / py_version / "site-packages"
    )
    site_packages.mkdir(parents=True, exist_ok=True)
    pth = site_packages / pth_basename
    pth.write_text(line + "\n", encoding="utf-8")
    return pth


# ============================================================================
# AC-005: detection happy path
# ============================================================================


def test_find_pth_leaks_detects_worktree_reference(tmp_path: Path) -> None:
    """AC-005: scanner returns one tuple matching a leaking .pth file."""
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = (
        tmp_path / "myrepo" / ".guardkit" / "worktrees" / "FEAT-DEMO"
    )
    worktree_path.mkdir(parents=True)
    leaking_line = str(worktree_path / "src")
    pth_file = _make_venv_pth(
        repo_root, "_editable_impl_demo.pth", leaking_line
    )

    leaks = find_pth_leaks(repo_root, worktree_path)

    assert len(leaks) == 1
    found_pth, found_line = leaks[0]
    assert found_pth == pth_file
    assert str(worktree_path) in found_line


def test_find_pth_leaks_detects_in_guardkit_venv(tmp_path: Path) -> None:
    """
    AC-001 covers ``.guardkit/venv`` as a scan root in addition to ``.venv``.
    """
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-X"
    worktree_path.mkdir(parents=True)
    leaking_line = str(worktree_path / "src")
    pth_file = _make_venv_pth(
        repo_root,
        "_editable_impl_x.pth",
        leaking_line,
        venv_dirname=".guardkit/venv",
    )

    leaks = find_pth_leaks(repo_root, worktree_path)

    assert len(leaks) == 1
    assert leaks[0][0] == pth_file


# ============================================================================
# AC-006: false-positive guard (clean state)
# ============================================================================


def test_find_pth_leaks_returns_empty_when_clean(tmp_path: Path) -> None:
    """AC-006: a .pth file pointing at an unrelated path returns []."""
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-DEMO"
    worktree_path.mkdir(parents=True)
    unrelated_path = "/some/other/place/src"
    _make_venv_pth(repo_root, "_editable_impl_other.pth", unrelated_path)

    leaks = find_pth_leaks(repo_root, worktree_path)

    assert leaks == []


def test_find_pth_leaks_ignores_non_editable_pth(tmp_path: Path) -> None:
    """
    Glob ``_editable_impl_*.pth`` MUST NOT match ordinary .pth files
    (e.g. ``easy-install.pth``, distribution .pth files). Otherwise the
    scanner would warn on every site-packages registration.
    """
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-X"
    worktree_path.mkdir(parents=True)
    site_packages = repo_root / ".venv" / "lib" / "python3.13" / "site-packages"
    site_packages.mkdir(parents=True)
    # A non-editable .pth referencing the worktree — must NOT be picked up.
    (site_packages / "easy-install.pth").write_text(
        str(worktree_path / "src") + "\n"
    )

    leaks = find_pth_leaks(repo_root, worktree_path)

    assert leaks == []


# ============================================================================
# AC-007: missing-venv tolerance
# ============================================================================


def test_find_pth_leaks_handles_missing_venv_dir(tmp_path: Path) -> None:
    """AC-007: no .venv directory exists; scanner returns []."""
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-X"
    worktree_path.mkdir(parents=True)

    leaks = find_pth_leaks(repo_root, worktree_path)

    assert leaks == []


def test_find_pth_leaks_handles_missing_repo_root(tmp_path: Path) -> None:
    """AC-004: nonexistent repo_root returns [] (no exception)."""
    nonexistent = tmp_path / "does-not-exist"
    worktree_path = tmp_path / "worktree"

    leaks = find_pth_leaks(nonexistent, worktree_path)

    assert leaks == []


# ============================================================================
# AC-008: permission tolerance
# ============================================================================


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="POSIX chmod semantics required for unreadable-file simulation",
)
def test_find_pth_leaks_handles_unreadable_pth(tmp_path: Path) -> None:
    """AC-008: an unreadable .pth file is skipped; scanner returns []."""
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-X"
    worktree_path.mkdir(parents=True)
    pth_file = _make_venv_pth(
        repo_root, "_editable_impl_unreadable.pth", str(worktree_path / "src")
    )
    # Strip read permission so the scanner gets PermissionError on read.
    original_mode = pth_file.stat().st_mode
    os.chmod(pth_file, 0o000)
    try:
        # Skip the test if the test runner is running as root (root can
        # read 0o000 files; the simulation is meaningless).
        if os.geteuid() == 0:
            pytest.skip("test runner is root; cannot simulate unreadable file")

        leaks = find_pth_leaks(repo_root, worktree_path)

        assert leaks == []
    finally:
        os.chmod(pth_file, original_mode)


# ============================================================================
# AC-009: symlink containment
# ============================================================================


@pytest.mark.skipif(
    sys.platform == "win32",
    reason="Windows symlinks require admin privileges in CI",
)
def test_find_pth_leaks_does_not_follow_symlinks(tmp_path: Path) -> None:
    """
    AC-009: ``<repo_root>/.venv`` is a symlink to an unrelated venv with a
    leaking .pth; scanner must not chase the symlink (returns []).
    """
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-X"
    worktree_path.mkdir(parents=True)

    # Build an unrelated venv elsewhere with a "leaking" line.
    other_root = tmp_path / "elsewhere"
    other_root.mkdir()
    _make_venv_pth(
        other_root, "_editable_impl_leak.pth", str(worktree_path / "src")
    )

    # Symlink repo_root/.venv -> elsewhere/.venv
    (repo_root / ".venv").symlink_to(other_root / ".venv")

    leaks = find_pth_leaks(repo_root, worktree_path)

    assert leaks == []


# ============================================================================
# Multi-leak / multi-version sanity
# ============================================================================


def test_find_pth_leaks_returns_all_leaks_across_python_versions(
    tmp_path: Path,
) -> None:
    """
    The glob ``lib/python*/site-packages/`` legitimately matches multiple
    Python versions in the same venv (e.g. an upgrade left both
    python3.13 and python3.14). All leaks must be reported.
    """
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-X"
    worktree_path.mkdir(parents=True)
    leaking_line = str(worktree_path / "src")
    pth_a = _make_venv_pth(
        repo_root,
        "_editable_impl_a.pth",
        leaking_line,
        py_version="python3.13",
    )
    pth_b = _make_venv_pth(
        repo_root,
        "_editable_impl_b.pth",
        leaking_line,
        py_version="python3.14",
    )

    leaks = find_pth_leaks(repo_root, worktree_path)

    found_paths = {leak[0] for leak in leaks}
    assert found_paths == {pth_a, pth_b}


def test_find_pth_leaks_handles_unicode_decode_errors(tmp_path: Path) -> None:
    """
    A .pth file containing invalid UTF-8 must not raise UnicodeDecodeError;
    it is skipped silently (treated as 'not a leak').
    """
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-X"
    worktree_path.mkdir(parents=True)
    site_packages = repo_root / ".venv" / "lib" / "python3.13" / "site-packages"
    site_packages.mkdir(parents=True)
    bad_pth = site_packages / "_editable_impl_bad.pth"
    # Invalid UTF-8 byte sequence
    bad_pth.write_bytes(b"\xff\xfe\xff\xfe")

    leaks = find_pth_leaks(repo_root, worktree_path)

    assert leaks == []


# ============================================================================
# warn_pth_leaks: presenter behaviour
# ============================================================================


def test_warn_pth_leaks_returns_zero_when_no_leaks(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    AC-003 / AC-011: when scanner finds no leaks, presenter is silent and
    returns 0.
    """
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / "FEAT-X"
    worktree_path.mkdir()

    count = warn_pth_leaks(repo_root, worktree_path)

    captured = capsys.readouterr()
    assert count == 0
    assert captured.err == ""
    assert captured.out == ""


def test_warn_pth_leaks_emits_warning_per_leak(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """
    AC-002: warnings are emitted to stderr (when no console provided)
    with the ``Repair: ... uv pip install -e . --no-deps`` hint and the
    repo_root in the repair command.
    """
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / ".guardkit" / "worktrees" / "FEAT-DEMO"
    worktree_path.mkdir(parents=True)
    pth_file = _make_venv_pth(
        repo_root, "_editable_impl_demo.pth", str(worktree_path / "src")
    )

    count = warn_pth_leaks(repo_root, worktree_path)

    captured = capsys.readouterr()
    assert count == 1
    assert "warning" in captured.err.lower()
    assert str(pth_file) in captured.err
    assert "uv pip install -e . --no-deps" in captured.err
    assert str(repo_root) in captured.err


def test_warn_pth_leaks_never_raises_on_internal_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """
    Defence-in-depth: even if the scanner blows up, the presenter must
    return 0 and not propagate — cleanup must never be aborted by us.
    """
    def _explode(*_a: object, **_kw: object) -> list[tuple[Path, str]]:
        raise RuntimeError("scanner bug")

    monkeypatch.setattr(
        "guardkit.worktrees.pth_leak_scanner.find_pth_leaks", _explode
    )
    repo_root = tmp_path / "myrepo"
    repo_root.mkdir()
    worktree_path = repo_root / "FEAT-X"
    worktree_path.mkdir()

    # Must not raise.
    count = warn_pth_leaks(repo_root, worktree_path)

    assert count == 0
