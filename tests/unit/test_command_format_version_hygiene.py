"""format_version hygiene for the installer command specs (PB-10 phase 1).

Modernization review 2026-07-08 §5 [DIM3-F4]: pinned-by-hash templates have no
semantic ``format_version`` — consumers cannot distinguish an editorial edit from
a contract break. The two-phase remediation:

  * **Phase 1 (this test's invariant, NOW):** every UNPINNED command spec carries
    ``format_version: 1`` in its frontmatter — zero external impact.
  * **Phase 2 (deliberately NOT yet):** the two pinned templates
    (``feature-spec.md`` / ``feature-plan.md``) gain the field ONLY inside the
    next coordinated semantic change (the ADR-D batched re-pin), as a versioned
    migration with the full re-pin + G2b re-freeze cost stated.

So this test pins BOTH halves of the invariant:
  1. every unpinned spec HAS ``format_version``, and
  2. the two pinned templates do NOT — so phase 2 stays a conscious, coordinated
     act and cannot be smuggled in early. If a future session re-pins the two
     templates *with* the field, it must delete their entries from ``_PINNED``
     below in the same commit, which surfaces the decision in review.
"""
from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMANDS = _REPO_ROOT / "installer" / "core" / "commands"

# The two sha256-pinned templates. Phase 2 gives them the field only inside the
# ADR-D batched re-pin — until then they MUST NOT carry it.
_PINNED = {"feature-spec.md", "feature-plan.md"}


def _frontmatter(md: Path) -> str | None:
    """Return the YAML frontmatter block body, or None if the file has none."""
    text = md.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end == -1:
        return None
    return text[4:end]


def _unpinned_specs() -> list[Path]:
    return sorted(p for p in _COMMANDS.glob("*.md") if p.name not in _PINNED)


def _pinned_specs() -> list[Path]:
    return sorted(_COMMANDS / name for name in _PINNED)


# Population history (step this count DELIBERATELY, one commit per change):
#   28 files / 26 unpinned — PB-10 phase 1 baseline (M2, 1b89804d).
#   25 files / 23 unpinned — 2026-07-10: M6/PB-17 retired the design-tool trio
#     (e421eff5) without bumping this count; fixed 2026-07-10 (M5 commit C0).
#   PB-13 wave-1 (M5) adds 7 reference slices ({name}*-ext.md), stepped
#     per restructure commit — final 30.
_EXPECTED_UNPINNED = 26


def test_unpinned_spec_population_is_deliberate():
    """Guard the population size — any add/retire must step _EXPECTED_UNPINNED."""
    unpinned = _unpinned_specs()
    assert len(unpinned) == _EXPECTED_UNPINNED, (
        f"expected {_EXPECTED_UNPINNED} unpinned command specs, "
        f"found {len(unpinned)}: {[p.name for p in unpinned]}"
    )


@pytest.mark.parametrize("md", _unpinned_specs(), ids=lambda p: p.name)
def test_unpinned_spec_carries_format_version(md: Path):
    """Every UNPINNED command spec must declare ``format_version: 1``."""
    fm = _frontmatter(md)
    assert fm is not None, (
        f"{md.name} has no frontmatter block — phase 1 requires one carrying "
        f"format_version"
    )
    assert "format_version: 1" in fm, (
        f"{md.name} frontmatter is missing 'format_version: 1' (PB-10 phase 1)"
    )


@pytest.mark.parametrize("md", _pinned_specs(), ids=lambda p: p.name)
def test_pinned_template_does_not_carry_format_version(md: Path):
    """The two pinned templates must NOT carry format_version until phase 2.

    Adding it is a pinned-byte change = an ADR-D re-pin event. If this test
    fails because the field was added, that re-pin MUST also drop the template
    from ``_PINNED`` here in the same commit.
    """
    fm = _frontmatter(md)
    body = fm if fm is not None else md.read_text(encoding="utf-8")
    assert "format_version:" not in body, (
        f"{md.name} is pinned — it must not carry format_version until the "
        f"ADR-D batched re-pin (PB-10 phase 2). If this is that re-pin, remove "
        f"{md.name} from _PINNED in this test in the same commit."
    )
