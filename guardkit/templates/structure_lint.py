"""Template-structure lint for the sliceable command specs (PB-5 / DIM2-F4).

Modernization review 2026-07-08 §5 [DIM2-F4] CONFIRMED: *nothing grades the
command-spec templates THEMSELVES, and ambiguous anchors already exist.*
``feature-plan.md`` carries FOUR near-colliding "Integration Contracts" headers
(a real ``## Integration Contracts`` at :1827, ``### 4. §4: Integration
Contracts`` at :1888, and two ``## §4: Integration Contracts`` inside ````markdown
fences at :1895/:1918). A **fence-naive header-regex slicer** — the natural first
implementation of the DIM2-F2 header-offset slicer — grabs the wrong block.

This module is that lint. It is the **prerequisite** for the slicer: it turns
template-structure drift from a live-run failure into a report-only signal.

Four checks, per the finding:

  (a) **unique normative anchors** — flag header lines whose normalized anchor
      collides with another (fence-INCLUSIVE, because the ambiguity surface a
      naive slicer sees includes fenced example headers). WARNING.
  (b) **protocol-section presence** — a sliceable orchestration template must
      carry a recognizable execution-protocol section (so the slicer has a
      stable, findable target). WARNING when absent.
  (c) **per-section token budgets** — estimate tokens per top-level section.
      **Report-only (INFO)** until WS4 commits a serving-window figure; the
      "32k" number in the review has circular provenance, so this check never
      fails a build in this session.
  (d) **non-normative example marking** — a fenced block that contains
      markdown-header-looking lines (``##``+) must be introduced by a
      non-normative marker (``**Example:**``, ``**Template:**``, "e.g.", …) so a
      reader/slicer can tell the example headers from the document's own
      normative headers. WARNING when unmarked.

**Nothing here fails a build.** Every finding is advisory: fixing the anchor
collisions in ``feature-plan.md`` is a pinned-byte change = an ADR-D re-pin
event, out of scope for the additive lint. The CLI prints findings report-only
and never changes the exit code on their account.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Tunables (DATA)
# ---------------------------------------------------------------------------

# chars-per-token heuristic. The review measured the protocol slice at
# 47,223 chars ≈ 11-12k tokens (~4 chars/token); we use 4.
_CHARS_PER_TOKEN = 4

# Soft per-section reference used ONLY to decide which sections are worth
# reporting. It is NOT a budget — the committed serving-window figure below
# is the load-bearing gate.
_SOFT_SECTION_TOKEN_REFERENCE = 4000

# Committed serving-window figure per WS4 Amendment M3 (§Amendment A-B of
# ai-transition/docs/ws4-learning-flywheel-scope-and-build-plan-2026-07-07.md).
# **32K (32768 tokens) is the worst-case serving floor; a task-generating slice
# must fit ≤ ~20k tokens against it; the 64K seat is headroom, not the gate.**
# This figure is NOT derived from the actual seat size (64K) — do not "helpfully"
# raise it to 64K. The 32K floor is the committed minimum for worst-case serving,
# and the per-slice budget is ~20k (leaving room for fixed prompt components and
# conversation history).
COMMITTED_SERVING_WINDOW_TOKENS = 32768

# A header is a "protocol section" if its normalized text contains any of these.
_PROTOCOL_MARKERS = (
    "execution",
    "protocol",
    "instruction",
    "workflow",
    "phase",
    "process",
    "methodology",
)

# A fenced example block is "marked non-normative" if one of these appears in
# the few lines immediately preceding the opening fence.
_EXAMPLE_MARKERS = (
    "example",
    "template",
    "e.g",
    "eg.",
    "for example",
    "for instance",
    "illustrative",
    "non-normative",
    "sample",
)

# The sliceable orchestration command specs this lint targets by default (PB-5:
# the 007/008 port slices these). Both are sha256-pinned — the lint READS them,
# never edits them.
DEFAULT_TARGETS = ("feature-plan.md", "feature-spec.md")

_HEADER_RE = re.compile(r"^(#{1,6})\s+(\S.*?)\s*$")
_MARKDOWN_HEADER_IN_FENCE_RE = re.compile(r"^#{2,6}\s+\S")
_FENCE_RE = re.compile(r"^\s*([`~]{3,})")


class Severity(str, Enum):
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class StructureFinding:
    """One template-structure lint finding (advisory — never fails a build)."""

    check: str
    severity: Severity
    line: int  # 1-based; 0 when file-level (no single line)
    message: str
    anchor: Optional[str] = None


# ---------------------------------------------------------------------------
# Fence-aware line classification
# ---------------------------------------------------------------------------


def _fence_flags(lines: Sequence[str]) -> List[bool]:
    """Return per-line ``inside a code fence`` flags.

    Fences are matched by run-length so a ````markdown block correctly contains
    ``` lines without being closed by them (the Integration-Contracts example
    shape). The opening/closing fence lines are themselves marked *inside*.
    """
    flags: List[bool] = []
    open_char: Optional[str] = None
    open_len = 0
    for raw in lines:
        m = _FENCE_RE.match(raw)
        if open_char is None:
            if m:
                run = m.group(1)
                open_char = run[0]
                open_len = len(run)
                flags.append(True)  # the opening fence line is inside
            else:
                flags.append(False)
        else:
            flags.append(True)  # inside a fence (incl. the closing line)
            if m:
                run = m.group(1)
                if run[0] == open_char and len(run) >= open_len:
                    open_char = None
                    open_len = 0
    return flags


def _normalize_anchor(text: str) -> str:
    """Normalize a header for collision detection.

    Strips ``§N:`` markers, leading ``N.`` enumerations, and punctuation so that
    ``Integration Contracts`` / ``4. §4: Integration Contracts`` /
    ``§4: Integration Contracts`` all collapse to one anchor.
    """
    t = text.lower()
    t = re.sub(r"\([^)]*\)", " ", t)  # drop a trailing/qualifying parenthetical
    t = re.sub(r"§\s*\d+\s*:?", " ", t)  # drop §4: markers
    t = re.sub(r"^\s*\d+[.)]\s*", "", t)  # drop a leading enumeration
    t = re.sub(r"[^a-z0-9]+", " ", t)  # drop punctuation/emoji
    return re.sub(r"\s+", " ", t).strip()


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


def _check_unique_normative_anchors(
    lines: Sequence[str], fences: Sequence[bool]
) -> List[StructureFinding]:
    # (normalized, line_no_1based, raw_text, fenced)
    headers = []
    for i, raw in enumerate(lines):
        m = _HEADER_RE.match(raw)
        if not m:
            continue
        headers.append((_normalize_anchor(m.group(2)), i + 1, m.group(2), fences[i]))

    by_anchor: Dict[str, list] = {}
    for norm, ln, raw_text, fenced in headers:
        if not norm:
            continue
        by_anchor.setdefault(norm, []).append((ln, raw_text, fenced))

    findings: List[StructureFinding] = []
    for norm, occ in by_anchor.items():
        if len(occ) < 2:
            continue
        # Only a hazard when at least one occurrence is normative (non-fenced);
        # a repeated *fenced* example header alone is not a slicer target.
        if not any(not fenced for _, _, fenced in occ):
            continue
        lns = ", ".join(str(ln) for ln, _, _ in occ)
        for ln, raw_text, fenced in occ:
            where = " (inside a code fence)" if fenced else ""
            findings.append(
                StructureFinding(
                    check="unique-normative-anchors",
                    severity=Severity.WARNING,
                    line=ln,
                    anchor=raw_text,
                    message=(
                        f"anchor {raw_text!r}{where} collides with "
                        f"{len(occ)} occurrences of {norm!r} (lines {lns}); a "
                        f"fence-naive slicer cannot disambiguate them"
                    ),
                )
            )
    return findings


def _check_protocol_section_presence(
    lines: Sequence[str], fences: Sequence[bool]
) -> List[StructureFinding]:
    for i, raw in enumerate(lines):
        if fences[i]:
            continue
        m = _HEADER_RE.match(raw)
        if not m:
            continue
        norm = _normalize_anchor(m.group(2))
        if any(marker in norm for marker in _PROTOCOL_MARKERS):
            return []  # found a protocol section
    return [
        StructureFinding(
            check="protocol-section-presence",
            severity=Severity.WARNING,
            line=0,
            message=(
                "no execution-protocol section found (a normative header naming "
                "one of: " + ", ".join(_PROTOCOL_MARKERS) + "); the slicer needs "
                "a stable target section"
            ),
        )
    ]


def _check_section_token_budgets(
    lines: Sequence[str],
    fences: Sequence[bool],
    serving_window_tokens: Optional[int],
) -> List[StructureFinding]:
    # Split into level-2 (##) normative sections.
    sections = []  # (header_text, start_line, char_count)
    cur_header: Optional[str] = None
    cur_start = 0
    cur_chars = 0
    for i, raw in enumerate(lines):
        m = _HEADER_RE.match(raw)
        is_l2 = (not fences[i]) and m is not None and len(m.group(1)) == 2
        if is_l2 and m is not None:
            if cur_header is not None:
                sections.append((cur_header, cur_start, cur_chars))
            cur_header = m.group(2)
            cur_start = i + 1
            cur_chars = len(raw) + 1
        else:
            cur_chars += len(raw) + 1
    if cur_header is not None:
        sections.append((cur_header, cur_start, cur_chars))

    # Severity depends on whether a serving-window figure is provided. When
    # provided (as of WS4 Amendment M3), findings are WARNING; without it,
    # they remain INFO/report-only.
    reference = serving_window_tokens or _SOFT_SECTION_TOKEN_REFERENCE
    report_only = serving_window_tokens is None
    note = (
        "report-only (no committed serving-window figure)"
        if report_only
        else f"committed serving-window floor {serving_window_tokens} tokens (WS4 Amendment M3)"
    )

    findings: List[StructureFinding] = []
    for header, start, chars in sections:
        tokens = chars // _CHARS_PER_TOKEN
        if tokens < reference:
            continue
        findings.append(
            StructureFinding(
                check="section-token-budget",
                # INFO when no figure provided; WARNING when committed figure is
                # passed (as of TASK-OBS-F3F5, threads COMMITTED_SERVING_WINDOW_TOKENS).
                severity=Severity.INFO if report_only else Severity.WARNING,
                line=start,
                anchor=header,
                message=(
                    f"section {header!r} ≈ {tokens} tokens "
                    f"(≥ {reference} reference) — {note}"
                ),
            )
        )
    return findings


def _check_example_blocks_marked(lines: Sequence[str]) -> List[StructureFinding]:
    findings: List[StructureFinding] = []
    n = len(lines)
    i = 0
    open_char: Optional[str] = None
    open_len = 0
    block_start = 0
    block_has_header = False
    while i < n:
        raw = lines[i]
        m = _FENCE_RE.match(raw)
        if open_char is None:
            if m:
                open_char = m.group(1)[0]
                open_len = len(m.group(1))
                block_start = i
                block_has_header = False
        else:
            if _MARKDOWN_HEADER_IN_FENCE_RE.match(raw):
                block_has_header = True
            if m and m.group(1)[0] == open_char and len(m.group(1)) >= open_len:
                # block closed at line i; evaluate marking
                if block_has_header and not _preceded_by_marker(lines, block_start):
                    findings.append(
                        StructureFinding(
                            check="example-block-marking",
                            severity=Severity.WARNING,
                            line=block_start + 1,
                            message=(
                                "fenced block contains markdown headers but is "
                                "not introduced by a non-normative marker "
                                "(e.g. **Example:** / **Template:**); a slicer "
                                "may mistake its headers for normative anchors"
                            ),
                        )
                    )
                open_char = None
                open_len = 0
        i += 1
    return findings


def _preceded_by_marker(lines: Sequence[str], fence_line_idx: int) -> bool:
    """True if a non-normative marker appears in the <=3 lines before the fence."""
    seen = 0
    j = fence_line_idx - 1
    while j >= 0 and seen < 3:
        stripped = lines[j].strip()
        if stripped:
            low = stripped.lower()
            if any(marker in low for marker in _EXAMPLE_MARKERS):
                return True
            seen += 1
        j -= 1
    return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def lint_structure(
    text: str, *, serving_window_tokens: Optional[int] = None
) -> List[StructureFinding]:
    """Run all four structure checks over a command-spec markdown ``text``.

    ``serving_window_tokens`` controls the token-budget check severity: when
    ``None``, findings are INFO/report-only; when provided (e.g.,
    ``COMMITTED_SERVING_WINDOW_TOKENS``), findings are WARNING.
    """
    lines = text.splitlines()
    fences = _fence_flags(lines)
    findings: List[StructureFinding] = []
    findings += _check_unique_normative_anchors(lines, fences)
    findings += _check_protocol_section_presence(lines, fences)
    findings += _check_section_token_budgets(lines, fences, serving_window_tokens)
    findings += _check_example_blocks_marked(lines)
    return findings


def lint_command_templates(
    commands_dir: Optional[Path] = None,
    *,
    targets: Sequence[str] = DEFAULT_TARGETS,
    serving_window_tokens: Optional[int] = None,
) -> Dict[str, List[StructureFinding]]:
    """Lint the sliceable orchestration command specs. Missing targets are skipped.

    Returns a mapping of spec filename -> findings. Advisory only — the caller
    must NOT fail on the result (fixing pinned-template anchors is an ADR-D
    re-pin event).
    """
    if commands_dir is None:
        commands_dir = (
            Path(__file__).resolve().parents[2] / "installer" / "core" / "commands"
        )
    results: Dict[str, List[StructureFinding]] = {}
    for name in targets:
        path = commands_dir / name
        if not path.is_file():
            continue
        results[name] = lint_structure(
            path.read_text(encoding="utf-8"),
            serving_window_tokens=serving_window_tokens,
        )
    return results
