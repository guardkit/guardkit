"""DF-011 seam guard: the packaged template BYTES must not change.

The specialist-agent Session C loader pins the two planning-command templates by
sha256 content hash (feature-spec.md 3c758966… — bumped 2026-09-07 with the concurrency-as-one-caller rule, IN the same commit; feature-plan.md 20a30611… — bumped 2026-08-18 with the home-choosing rule, IN the same commit) and
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
        "ef5ec5bb8b50cdd663236a4115f1778ab5542750fad13ceabc6bb54ca847ed65"
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
