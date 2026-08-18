"""DF-011 seam guard: the packaged template BYTES must not change.

The specialist-agent Session C loader pins the two planning-command templates by
sha256 content hash (feature-spec.md 3d956e1f…, feature-plan.md 20a30611… — bumped 2026-08-18 with the home-choosing rule, IN the same commit) and
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
        "3d956e1ffce2ba85f1aa7ddf3074b7d28af8f6094ae97c9443bc0c4d34347591"  # 2026-08-17: routing-law widening + template note (guardkit d324f255)
    ),
    "installer/core/commands/feature-plan.md": (
        "20a3061159b6a3324c0bdeea230989e81dd823a2d220db5410a46144932678e3"  # 2026-08-17: routing-law widening + template note (guardkit d324f255)
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
