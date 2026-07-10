"""PB-9 single-source oracle + PB-13 core-budget guard.

Modernization review 2026-07-08 [DIM2-F3] / backlog row PB-9: task-work.md
defined every flag's semantics THREE times (declarative table, ~100-line
imperative pseudocode parser, reference re-documentation) — a drift surface
measured at ~41k tokens per attended invocation. The PB-13 wave-1 restructure
(design of record: ai-transition
``docs/pb13-wave1-skills-restructure-design-2026-07-09.md`` §4) collapsed the
three sites into ONE: the ``## Available Flags`` table in the task-work.md core.

These tests are the grep-count CI oracle that design §4.3 specifies:

  1. every canonical flag has EXACTLY ONE normative table row across the whole
     ``task-work*.md`` file set, and that row lives in the core;
  2. the retired imperative parser signature (``... in user_input``) never
     returns to any file in the set;
  3. exactly one ``## Available Flags`` heading exists across the set;
  4. (R1 budget half) every restructured command CORE stays ≤ 20,480 bytes
     (~5k tokens at the B/4 estimate M3's serving-window figure prices in) —
     the size regression guard for the 32K-floor serving budget.

Anchors are heading-text/grep-signature only — never line numbers (PB-12).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_COMMANDS = _REPO_ROOT / "installer" / "core" / "commands"

_CORE = _COMMANDS / "task-work.md"
_TASK_WORK_SET = sorted(_COMMANDS.glob("task-work*.md"))

# Canonical flag registry — mirrors the core's ## Available Flags table.
# Prefixes are matched at table-row start: `| `--<flag>` so a flag mentioned in
# prose, headings, or code fences does NOT count as a definition site.
_FLAGS = [
    "--mode=",
    "--intensity=",
    "--micro",
    "--design-only",
    "--implement-only",
    "--docs=",
    "--no-questions",
    "--with-questions",
    "--defaults",
    "--answers=",
    "--reclarify",
    "--no-library-context",
    "--autobuild-mode",
    "--auto-approve-checkpoint",
    "--skip-arch-review",
    "--complete",
    "--pause",
]

# The four PB-13 wave-1 cores and the R1 ceiling (bytes; ~5k tokens at B/4).
_CORE_BUDGET_BYTES = 20_480
_RESTRUCTURED_CORES = [
    "task-work.md",
    "task-review.md",
    "agent-validate.md",
    "template-create.md",
]


def _row_pattern(flag: str) -> re.Pattern[str]:
    # A normative definition row starts the line as a table cell holding the
    # backticked flag: | `--flag...   (word-ish boundary so --complete does not
    # also match a hypothetical --complete-foo row).
    return re.compile(r"^\|\s*`" + re.escape(flag), re.MULTILINE)


def test_task_work_file_set_present() -> None:
    """Core + the four wave-1 slices exist (design §3.1)."""
    names = {p.name for p in _TASK_WORK_SET}
    assert names == {
        "task-work.md",
        "task-work-flags-ext.md",
        "task-work-phases-plan-ext.md",
        "task-work-phases-build-ext.md",
        "task-work-reference-ext.md",
    }, f"unexpected task-work file set: {sorted(names)}"


@pytest.mark.parametrize("flag", _FLAGS)
def test_each_flag_has_exactly_one_definition_row(flag: str) -> None:
    """One normative table row per flag across ALL task-work*.md — in the core."""
    pat = _row_pattern(flag)
    counts = {p.name: len(pat.findall(p.read_text(encoding="utf-8"))) for p in _TASK_WORK_SET}
    total = sum(counts.values())
    assert total == 1, (
        f"flag {flag!r} must have exactly ONE definition table row across the "
        f"task-work set (PB-9); found {total}: "
        f"{ {k: v for k, v in counts.items() if v} }"
    )
    assert counts["task-work.md"] == 1, (
        f"flag {flag!r}'s single definition row must live in the CORE "
        f"(task-work.md), not a slice: { {k: v for k, v in counts.items() if v} }"
    )


def test_pause_alias_no_complete_documented_in_same_row() -> None:
    """--no-complete is an alias documented inside the --pause row, not its own."""
    core = _CORE.read_text(encoding="utf-8")
    row = next(
        (l for l in core.splitlines() if _row_pattern("--pause").match(l)), ""
    )
    assert "--no-complete" in row, (
        "--pause's table row must document the --no-complete alias (design §5)"
    )


def test_imperative_parser_signature_retired() -> None:
    """The Step-0 pseudocode parser (`... in user_input`) must not return."""
    offenders = [
        p.name for p in _TASK_WORK_SET if "in user_input" in p.read_text(encoding="utf-8")
    ]
    assert not offenders, (
        f"retired imperative flag parser re-introduced (PB-9/DIM2-F3) in: {offenders}. "
        "Flag semantics are defined ONCE in the core's ## Available Flags table."
    )


def test_exactly_one_available_flags_heading() -> None:
    total = sum(
        len(re.findall(r"^## Available Flags$", p.read_text(encoding="utf-8"), re.M))
        for p in _TASK_WORK_SET
    )
    assert total == 1, (
        f"expected exactly one '## Available Flags' heading across the task-work "
        f"set (the core's normative site), found {total}"
    )


@pytest.mark.parametrize("name", _RESTRUCTURED_CORES)
def test_command_core_within_serving_budget(name: str) -> None:
    """R1: each wave-1 core ≤ 20,480 bytes (~5k tokens, 32K-floor headroom)."""
    size = (_COMMANDS / name).stat().st_size
    assert size <= _CORE_BUDGET_BYTES, (
        f"{name} core is {size}B > {_CORE_BUDGET_BYTES}B (design R1). Move the "
        f"overflow into that command's -ext slice(s); never delete (K12)."
    )
