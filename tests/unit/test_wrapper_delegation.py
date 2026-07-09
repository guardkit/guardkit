"""The installed `guardkit` shell wrapper must delegate unknown commands to guardkit-py.

Incident (2026-07-09): /task-review's Phase 0 ad-hoc entry runs
``guardkit task create …``; the wrapper's ``*)`` catch-all rejected every
Python-CLI group it didn't enumerate ("Unknown command: task"), so the review
ran without its durable TASK-REV record. TASK-FPSG-004 had already solved this
for ``feature`` with an explicit delegation block; the fix generalizes that
into ``find_guardkit_py()`` + delegation in the catch-all, so new Python CLI
groups (task, memory, qa, template, review, …) never need wrapper re-enumeration.

Grep-able-signature guard over the wrapper heredoc inside install.sh
(test_command_anchor_hygiene.py convention).
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_INSTALL_SH = _REPO_ROOT / "installer" / "scripts" / "install.sh"


def _wrapper_heredoc(script: str) -> str:
    """Extract the bin/guardkit heredoc body from install.sh."""
    match = re.search(
        r'cat > "\$INSTALL_DIR/bin/guardkit" << \'EOF\'\n(.*?)\nEOF\n',
        script,
        flags=re.DOTALL,
    )
    assert match, "bin/guardkit heredoc not found in install.sh"
    return match.group(1)


def test_wrapper_defines_find_guardkit_py() -> None:
    body = _wrapper_heredoc(_INSTALL_SH.read_text(encoding="utf-8"))
    assert "find_guardkit_py()" in body


def test_wrapper_catch_all_delegates_to_guardkit_py() -> None:
    body = _wrapper_heredoc(_INSTALL_SH.read_text(encoding="utf-8"))
    # The catch-all arm must attempt delegation before erroring.
    catch_all = body.rsplit("    *)", 1)[1]
    assert 'exec "$GUARDKIT_PY" "$@"' in catch_all
    # The not-found branch stays informative (names the pip install path).
    assert "guardkit-py Python package" in catch_all


def test_wrapper_help_mentions_delegation() -> None:
    body = _wrapper_heredoc(_INSTALL_SH.read_text(encoding="utf-8"))
    assert "delegated to the guardkit-py Python CLI" in body
