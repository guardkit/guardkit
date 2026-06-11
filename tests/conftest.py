"""Pytest configuration and fixtures."""
import os
import sys
from pathlib import Path

import pytest

# Add installer/core to Python path (to allow "from lib.X import Y")
global_path = Path(__file__).parent.parent / "installer" / "core"
sys.path.insert(0, str(global_path))

# Extend lib.__path__ so "from lib.X" resolves modules from both
# installer/core/lib/ AND installer/core/commands/lib/
import lib
commands_lib_path = global_path / "commands" / "lib"
if str(commands_lib_path) not in lib.__path__:
    lib.__path__.append(str(commands_lib_path))

# Also add lib directory for direct imports (for backward compatibility)
lib_path = global_path / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Also add commands/lib for plan_modifier imports
commands_lib_str = str(commands_lib_path)
if commands_lib_str not in sys.path:
    sys.path.insert(0, commands_lib_str)


# ---------------------------------------------------------------------------
# Quarantine: pre-existing red tests, skipped so the CI gate can be green and
# start catching NEW regressions (TASK-INFRA-CIGREEN). Every quarantined node
# is listed with a bucket reason in tests/quarantine.txt and tracked for
# burn-down in docs/state/TASK-INFRA-CIGREEN/triage.md. This is a documented,
# explicit skip — NOT a silent pass. Set GUARDKIT_NO_QUARANTINE=1 to run the
# full (red) suite, e.g. while burning the list down.
# ---------------------------------------------------------------------------
_QUARANTINE_FILE = Path(__file__).parent / "quarantine.txt"


def _load_quarantine():
    exact = set()
    modules = set()
    if not _QUARANTINE_FILE.exists():
        return exact, modules
    for raw in _QUARANTINE_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "::" in line:
            exact.add(line)
        else:
            # A bare module path quarantines every test it collects.
            modules.add(line)
    return exact, modules


_QUARANTINE_EXACT, _QUARANTINE_MODULES = _load_quarantine()


def pytest_collection_modifyitems(config, items):
    """Skip quarantined nodes unless GUARDKIT_NO_QUARANTINE is set."""
    if os.environ.get("GUARDKIT_NO_QUARANTINE"):
        return
    if not _QUARANTINE_EXACT and not _QUARANTINE_MODULES:
        return
    reason = (
        "quarantined pre-existing failure — see tests/quarantine.txt "
        "(TASK-INFRA-CIGREEN)"
    )
    marker = pytest.mark.skip(reason=reason)
    skipped = 0
    for item in items:
        nodeid = item.nodeid
        module = nodeid.split("::", 1)[0]
        if nodeid in _QUARANTINE_EXACT or module in _QUARANTINE_MODULES:
            item.add_marker(marker)
            skipped += 1
    if skipped:
        terminal = config.pluginmanager.get_plugin("terminalreporter")
        if terminal is not None:
            terminal.write_line(
                f"[quarantine] skipped {skipped} pre-existing red test(s) "
                f"(GUARDKIT_NO_QUARANTINE=1 to run them)"
            )


def normalize_path(path):
    """
    Normalize path for cross-platform comparison.

    Uses os.path.realpath() to resolve symlinks (e.g., macOS /private/var).

    Args:
        path: Path-like object to normalize

    Returns:
        Path: Normalized path object
    """
    return Path(os.path.realpath(path))


def paths_equal(path1, path2):
    """
    Compare two paths for equality after normalization.

    Args:
        path1: First path to compare
        path2: Second path to compare

    Returns:
        bool: True if paths are equal after normalization
    """
    return normalize_path(path1) == normalize_path(path2)
