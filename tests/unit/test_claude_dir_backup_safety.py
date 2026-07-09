"""~/.claude must never be wholesale-moved by install.sh (TASK-REV-ac2e / TASK-FIX-ac2e).

install.sh's ``backup_existing()`` used to sweep ``~/.claude`` into the same
whole-directory ``mv``-to-backup treatment as the guardkit-owned install dirs,
destroying Claude Code user state (auto-memory, settings.json, transcripts) on
every re-run — a live data-loss incident on 2026-07-08. The correct handling of
the only two guardkit-owned entries (``commands``/``agents`` symlinks) lives in
``setup_claude_integration()``.

Grep-able-signature guard (test_command_anchor_hygiene.py convention), two-sided:
negative — the sweep must not reference ``.claude``; positive — the surgical
mechanism must still exist, so it can't be deleted leaving ~/.claude handled by
nothing at all.
"""
from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_INSTALL_SH = _REPO_ROOT / "installer" / "scripts" / "install.sh"


def _function_body(script: str, name: str) -> str:
    """Extract a top-level ``name() { ... }`` bash function body (brace-balanced)."""
    match = re.search(rf"^{re.escape(name)}\(\)\s*\{{", script, flags=re.MULTILINE)
    assert match, f"{name}() not found in install.sh"
    depth = 0
    for i in range(match.end() - 1, len(script)):
        if script[i] == "{":
            depth += 1
        elif script[i] == "}":
            depth -= 1
            if depth == 0:
                return script[match.start() : i + 1]
    raise AssertionError(f"unbalanced braces extracting {name}()")


def test_backup_existing_never_sweeps_claude_dir() -> None:
    """Negative guard: .claude must not re-enter the wholesale mv-backup sweep."""
    body = _function_body(_INSTALL_SH.read_text(encoding="utf-8"), "backup_existing")
    assert 'existing_dirs+=(".claude")' not in body
    # No form of adding .claude to the sweep, however quoted/spelt.
    assert not re.search(r'existing_dirs\+=\([^)]*\.claude', body)
    # The guardkit-owned dirs must still be swept (the fix is surgical, not a gut).
    for owned in (".agentecflow", ".agenticflow", ".agentic-flow"):
        assert f'existing_dirs+=("{owned}")' in body, f"{owned} missing from sweep"


def test_backup_existing_keeps_the_explanatory_note() -> None:
    """The do-not-move rationale comment must survive future edits."""
    body = _function_body(_INSTALL_SH.read_text(encoding="utf-8"), "backup_existing")
    assert "Do NOT wholesale-move ~/.claude" in body


def test_setup_claude_integration_keeps_surgical_handling() -> None:
    """Positive guard: the safe mechanism must still exist if the sweep is gone."""
    body = _function_body(
        _INSTALL_SH.read_text(encoding="utf-8"), "setup_claude_integration"
    )
    # Symlink-aware guards for both guardkit-owned entries.
    assert '-L "$HOME/.claude/commands"' in body
    assert '-L "$HOME/.claude/agents"' in body
    # Subdir-scoped (not whole-dir) backups.
    assert '"$HOME/.claude/commands.backup.' in body
    assert '"$HOME/.claude/agents.backup.' in body
    # And it never moves the whole directory either.
    assert not re.search(r'mv\s+"?\$HOME/\.claude"?\s', body)
