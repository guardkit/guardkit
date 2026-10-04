"""DF-011 seam guard: the packaged template BYTES must not change.

The specialist-agent Session C loader pins the two planning-command templates by
sha256 content hash (feature-spec.md 32c1b7fe… and feature-plan.md 0cf5bf85… — both bumped 2026-10-04 with the memory-search project fix, IN the same commit) and
refuses any unpinned version. DF-011's packaging change (hatch force-include
installer/core -> guardkit/_installer_core + importlib.resources resolution) is a
DISTRIBUTION change only — it must not alter a single byte of those files, or the
seam re-freezes (contract impact DF-011 §3: "none").

These pins are the same values verified in Session C §4.1 / the contract doc §0.
If this test fails, EITHER a template was legitimately edited (a coordinated
re-pin + G2b re-freeze per DF-012/ADR-D is required, NOT a pin bump here) OR the
packaging change corrupted the bytes (a DF-011 regression).
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]

# (repo-relative path, expected sha256) — the specialist-seam pins.
PINNED_TEMPLATES = {
    "installer/core/commands/feature-spec.md": (
        # 2026-09-14: corrected to the bytes the SEAM actually pins. The
        # template was edited on 2026-09-07 (d78e7ae1, "a requested
        # concurrency case is kept and proven by a repository test the plan
        # names") and specialist-agent's own pin was moved with it — but THIS
        # mirror of that pin was not, so it named bytes that no longer existed
        # and the packaging workflow went red that day and stayed red.
        #
        # THE AUTHORITY IS specialist-agent src/specialist_agent/templates/
        # pins.py. This file cannot import it (separate repo, and guardkit
        # must not depend on the specialist), so it is a MIRROR — and a second
        # statement of a rule is a future lie unless it says where the truth
        # lives and how to re-derive it. Re-derive with:
        #     sha256sum installer/core/commands/feature-spec.md
        # and check it against that pins.py before changing this line. If the
        # two DISAGREE the seam is genuinely broken and a pin bump here is the
        # wrong fix — re-pin the specialist first.
        #
        # 2026-10-04: ef5ec5bb... -> 32c1b7fe..., moved together with
        # specialist-agent's pin. Step 1c now searches design records
        # (contracts and data models) as well as decisions, names the memory
        # project, and points at the installed memory guide. Instruction text
        # only; still 957 lines.
        "32c1b7fecf14913927cd6d950edb04c332a3821b1538e48e3f5da9ab77c56aec"
    ),
    "installer/core/commands/feature-plan.md": (
        # 2026-10-04: mirror corrected to specialist-agent's current pin (pins.py, re-pinned
        # 2026-10-03 for guardkit 044b74ed). The file has not changed since; only this mirror
        # was stale (it still held the 2026-08-17 value 20a30611...).
        #
        # 2026-10-04: f83a6a9d... -> 0cf5bf85..., moved together with
        # specialist-agent's pin. The memory searches name the memory project
        # instead of "guardkit", and the guide is the installed copy.
        # Instruction text only; still 3017 lines.
        "0cf5bf8515f9cd5aa9ee620d3d95a27a7d789a2bfbf5e6fa42038e8fb596c51c"
    ),
}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.mark.parametrize("relpath,expected", sorted(PINNED_TEMPLATES.items()))
def test_authoring_source_bytes_match_pin(relpath: str, expected: str) -> None:
    """The repo authoring source (installer/core) is byte-identical to the pin."""
    path = _REPO_ROOT / relpath
    assert path.is_file(), f"pinned template missing: {relpath}"
    actual = _sha256(path.read_bytes())
    assert actual == expected, (
        f"{relpath} bytes changed (sha256 {actual} != pinned {expected}). "
        "This breaks the specialist-agent Session C content-hash pin. A "
        "legitimate template edit is a COORDINATED re-pin + G2b re-freeze "
        "(DF-012 / ADR-D), not a bump of this test."
    )


def test_bootstrap_installer_core_is_noop_in_editable_checkout() -> None:
    """DF-011 bootstrap must not shadow the repo's own installer.core.

    In this editable checkout the top-level installer package is importable, so
    guardkit._bootstrap_installer_core() must leave installer.core pointing at
    the repo, never at a packaged _installer_core alias.
    """
    import installer.core  # noqa: F401

    assert "_installer_core" not in installer.core.__file__
