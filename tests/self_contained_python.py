"""This test session's interpreter, with its packages, that does not need HOME.

Since 13 October 2026 the merge runs a project's install and check with a
private ``HOME`` (the merge design's item 2a): a merge check may not read ``~/.docker/config.json``,
``~/.git-credentials``, ``~/.netrc`` and the like. The merge tests' fake
projects run "this test session's own interpreter" with pytest (the intent of
``f78ec033``, 6 September 2026). When that interpreter finds pytest only
through the real ``HOME``'s user site (``~/.local/lib/pythonX.Y``), it can no
longer find it under the private ``HOME``.

:func:`self_contained_python` keeps the intent and drops the dependence on
``HOME``. When pytest does not come from the user site it is simply
``sys.executable``. Otherwise it is a throwaway virtual environment made once
per test process from ``sys.executable`` (no pip, no network) whose OWN
``site-packages`` holds a ``.pth`` file naming the folder this session's
pytest comes from, so the same packages are found whatever ``HOME`` says.
"""

from __future__ import annotations

import atexit
import functools
import shutil
import site
import subprocess
import sys
import tempfile
from pathlib import Path

__all__ = ["self_contained_python"]


def _packages_folder_of_pytest() -> Path:
    import pytest

    return Path(pytest.__file__).resolve().parent.parent


def _under_user_site(folder: Path) -> bool:
    try:
        user_site = Path(site.getusersitepackages()).resolve()
    except Exception:  # noqa: BLE001 - no user site means nothing to avoid
        return False
    return folder == user_site or folder.is_relative_to(user_site)


@functools.lru_cache(maxsize=None)
def self_contained_python() -> str:
    """An interpreter path whose own packages include this session's pytest."""
    folder = _packages_folder_of_pytest()
    if not _under_user_site(folder):
        return sys.executable
    base = Path(tempfile.mkdtemp(prefix="guardkit-self-contained-python-"))
    atexit.register(shutil.rmtree, base, True)
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", "--system-site-packages", str(base)],
        check=True,
        capture_output=True,
    )
    candidates = sorted((base / "lib").glob("python*/site-packages"))
    if not candidates:
        raise RuntimeError(f"the throwaway environment at {base} has no site-packages")
    (candidates[0] / "_this_test_sessions_packages.pth").write_text(
        f"{folder}\n", encoding="utf-8"
    )
    return str(base / "bin" / "python")
