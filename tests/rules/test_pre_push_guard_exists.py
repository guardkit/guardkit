"""CI lint: the direct-to-main pre-push collection guard must stay in place.

Seeded by TASK-FIX-CIGUARD01. ``main`` went red on the ``Tests`` gate on
2026-06-12 because a direct push carried an import-time ``ImportError`` that
interrupted pytest *collection* for the whole tree — and nothing stopped the
broken commit landing, because ``main`` has no branch protection and the owner
pushes directly to main (a required-PR-status-check never applies to a direct
push). The remediation (Part B) is a committed pre-push guard
(``scripts/pre-push.sh``) that runs the fast collection check and aborts the
push at the source.

A git hook lives outside the suite it protects: it can be deleted, never
installed, or its guard command silently weakened, and CI would not notice —
which is exactly how the original gate became inert. This structural test keeps
the committed guard honest: if the script is removed, made non-executable, or
loses the collection-check command / the abort path, this test reds the very
``Tests`` gate the guard exists to keep green.

Scope: assert the *committed* artefacts exist and still encode the guard
contract. It does NOT run the (~2-3s) collection itself — that is the hook's
job at push time and the workflow's job in CI.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GUARD = REPO_ROOT / "scripts" / "pre-push.sh"
INSTALLER = REPO_ROOT / "scripts" / "install-git-hooks.sh"


def _is_executable(path: Path) -> bool:
    return bool(path.stat().st_mode & stat.S_IXUSR)


def test_pre_push_guard_script_exists_and_is_executable() -> None:
    assert GUARD.is_file(), (
        f"Missing direct-to-main pre-push guard: {GUARD.relative_to(REPO_ROOT)}. "
        "See TASK-FIX-CIGUARD01 Part B."
    )
    assert _is_executable(GUARD), (
        f"{GUARD.relative_to(REPO_ROOT)} must be executable (chmod +x)."
    )


def test_installer_script_exists_and_is_executable() -> None:
    assert INSTALLER.is_file(), (
        f"Missing hook installer: {INSTALLER.relative_to(REPO_ROOT)}. "
        "See CONTRIBUTING.md → Git hooks."
    )
    assert _is_executable(INSTALLER), (
        f"{INSTALLER.relative_to(REPO_ROOT)} must be executable (chmod +x)."
    )


def test_guard_runs_the_collection_check() -> None:
    """The guard must invoke the same fast collection probe CI relies on."""
    body = GUARD.read_text()
    # The CIGUARD01 defect class is a *collection* error; the guard's oracle
    # must be the collection-only pytest probe, not a no-op.
    for needle in ("pytest tests/", "--co", 'addopts=""', "no:cacheprovider"):
        assert needle in body, (
            f"pre-push guard no longer runs the collection check (missing "
            f"{needle!r}); it would not catch the CIGUARD01 defect class."
        )


def test_guard_aborts_on_collection_failure() -> None:
    """A failed collection must abort the push (non-zero exit), scoped to main."""
    body = GUARD.read_text()
    assert "refs/heads/main" in body, (
        "pre-push guard must gate refs/heads/main (the direct-to-main path)."
    )
    assert "exit 1" in body, (
        "pre-push guard must exit non-zero on collection failure to abort the push."
    )


if __name__ == "__main__":  # pragma: no cover - manual invocation aid
    test_pre_push_guard_script_exists_and_is_executable()
    test_installer_script_exists_and_is_executable()
    test_guard_runs_the_collection_check()
    test_guard_aborts_on_collection_failure()
    print("pre-push guard invariants OK")
