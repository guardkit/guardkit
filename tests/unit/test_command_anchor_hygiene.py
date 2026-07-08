"""Line-anchor hygiene for orchestrator references into pinned command specs.

PB-12 (guardkit modernization review 2026-07-08 §5 DIM4-F3 WEAKENED). The
orchestrator used to anchor into ``installer/core/commands/feature-spec.md`` by
LINE NUMBER (``feature-spec.md:337``). That anchor drifted 2 lines stale
(``fb37f72fd`` -> HEAD) the moment the pinned template gained content above the
rule. The zero-re-freeze remediation replaced the line numbers with HEADING-TEXT
anchors; these tests are the grep-able-signature guard that fails loud if either
(a) the anchored heading text is edited out of the pinned template, or (b) a
future code edit re-introduces a ``<template>.md:NNN`` line-number anchor.

Deliberately does NOT edit the sha256-pinned templates — it only reads them.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMANDS = _REPO_ROOT / "installer" / "core" / "commands"
_GUARDKIT_PKG = _REPO_ROOT / "guardkit"

# (anchor text that MUST exist in the pinned template, template filename).
_HEADING_ANCHORS = [
    ("Gating rule", "feature-spec.md"),   # Phase 5 "Confidence levels" gating rule
    ("Step 3.5", "task-work.md"),          # agent-invocation validation checkpoint
    ("Step 6.5", "task-work.md"),          # the "ONLY checkpoint" gate
]

# Templates whose line-number anchors PB-12 removed. A ``<name>.md:NNN`` anchor
# for any of these in guardkit/ code is the drift-prone form and must not return.
_NO_LINE_ANCHOR_TEMPLATES = ["feature-spec.md", "task-work.md"]


@pytest.mark.parametrize("anchor,template", _HEADING_ANCHORS)
def test_anchored_heading_text_exists_in_pinned_template(anchor: str, template: str) -> None:
    """The heading text the orchestrator anchors on must exist in the template."""
    path = _COMMANDS / template
    assert path.exists(), f"pinned template missing: {path}"
    text = path.read_text(encoding="utf-8")
    assert anchor in text, (
        f'anchor text "{anchor}" not found in {template}. A code comment/message '
        f"anchors on it; if the template heading was renamed, update BOTH the "
        f"template and every anchoring reference (grep the guardkit/ tree)."
    )


def test_no_line_number_anchors_into_pinned_templates() -> None:
    """No guardkit/ code may anchor into these templates by line number.

    Line-number anchors silently rot (PB-12). Anchor on heading text instead.
    """
    pattern = re.compile(
        r"(?:" + "|".join(re.escape(t) for t in _NO_LINE_ANCHOR_TEMPLATES) + r"):\d"
    )
    offenders: list[str] = []
    for py in _GUARDKIT_PKG.rglob("*.py"):
        for lineno, line in enumerate(py.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line):
                rel = py.relative_to(_REPO_ROOT)
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert not offenders, (
        "line-number anchors into pinned command specs re-introduced (PB-12). "
        "Use a heading-text anchor instead:\n  " + "\n  ".join(offenders)
    )
