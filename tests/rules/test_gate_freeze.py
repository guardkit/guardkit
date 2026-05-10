"""Gate-stack freeze guard (TASK-FREEZE-ABST).

Skip-on-out-of-window: outside the inclusive window
[2026-05-11, 2026-05-17] this guard short-circuits with ``pytest.skip``.
Inside the window, it inspects ``git log`` against the frozen paths
listed in ``.claude/state/gate-freeze-2026-05-17.md`` and fails the
test run if any forbidden-class commit landed without an explicit
override entry in that file.

Seeded by: TASK-FREEZE-ABST (Narrow recommendation from TASK-REV-ABST).

The companion record is the source of truth for the rules; this module
is the executable enforcement of those rules. If the two ever diverge,
trust the record and update this module.
"""

from __future__ import annotations

import datetime as _dt
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
FREEZE_RECORD = REPO_ROOT / ".claude" / "state" / "gate-freeze-2026-05-17.md"

FREEZE_START = _dt.date(2026, 5, 11)
FREEZE_END = _dt.date(2026, 5, 17)  # inclusive

FROZEN_PATHS: tuple[str, ...] = (
    "guardkit/orchestrator/agent_invoker.py",
    "guardkit/orchestrator/quality_gates/coach_validator.py",
    "guardkit/orchestrator/quality_gates/coach_verification.py",
    "guardkit/orchestrator/quality_gates/bdd_runner.py",
    "guardkit/orchestrator/quality_gates/honesty.py",
    "guardkit/tasks/state_bridge.py",
    "installer/core/templates/common/features/conftest.py.template",
)

REVERT_SUBJECT_RE = re.compile(r"^revert[(:]", re.IGNORECASE)
OVERRIDE_LINE_RE = re.compile(
    r"^- (\d{4}-\d{2}-\d{2}): .*?(TASK-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*(?:\.\d+)?)"
)
TASK_ID_RE = re.compile(r"TASK-[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*(?:\.\d+)?")


def _today() -> _dt.date:
    return _dt.date.today()


def _in_window(day: _dt.date) -> bool:
    return FREEZE_START <= day <= FREEZE_END


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=str(REPO_ROOT), text=True
    )


def _commits_in_window() -> list[tuple[str, str, list[str]]]:
    """Return commits authored inside ``[FREEZE_START, FREEZE_END]``.

    Each entry is ``(sha, subject, modified_paths)``. ``--until`` is
    bumped one day past ``FREEZE_END`` because git's ``--until`` is
    exclusive at midnight.
    """
    since = FREEZE_START.isoformat()
    until = (FREEZE_END + _dt.timedelta(days=1)).isoformat()
    log = _git(
        "log",
        f"--since={since}",
        f"--until={until}",
        "--pretty=format:%H%x00%s",
        "--name-only",
    )
    if not log.strip():
        return []
    blocks = re.split(r"\n\n+", log.strip())
    out: list[tuple[str, str, list[str]]] = []
    for block in blocks:
        lines = block.splitlines()
        if not lines or "\x00" not in lines[0]:
            continue
        sha, subject = lines[0].split("\x00", 1)
        paths = [p.strip() for p in lines[1:] if p.strip()]
        out.append((sha, subject, paths))
    return out


def _read_overrides() -> set[str]:
    """Parse the ``## Granted overrides`` section of the freeze record."""
    if not FREEZE_RECORD.exists():
        return set()
    text = FREEZE_RECORD.read_text(encoding="utf-8")
    in_section = False
    overrides: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            in_section = "Granted overrides" in line
            continue
        if not in_section:
            continue
        match = OVERRIDE_LINE_RE.match(line)
        if match:
            overrides.add(match.group(2))
    return overrides


def _touches_frozen(paths: list[str]) -> list[str]:
    return [p for p in paths if p in FROZEN_PATHS]


def _is_revert(subject: str) -> bool:
    return bool(REVERT_SUBJECT_RE.match(subject.strip()))


def _is_doc_or_test_only(paths: list[str]) -> bool:
    if not paths:
        return False
    doc_suffixes = (".md", ".rst", ".txt")
    for path in paths:
        if path.endswith(doc_suffixes):
            continue
        if path.startswith("docs/"):
            continue
        if path.startswith("tests/"):
            continue
        name = Path(path).name
        if name.startswith("test_") or name.endswith("_test.py"):
            continue
        return False
    return True


def _is_single_line_guard(sha: str, frozen_hits: list[str]) -> bool:
    """≤3 added lines on frozen paths AND no new ``def``/``class`` line."""
    diff = _git("show", "--no-color", "--unified=0", sha, "--", *frozen_hits)
    added = 0
    for line in diff.splitlines():
        if line.startswith(("@@", "+++", "---")):
            continue
        if line.startswith("+"):
            added += 1
            body = line[1:].lstrip()
            if body.startswith(("def ", "class ", "async def ")):
                return False
    return added <= 3


def test_freeze_record_present_and_parseable() -> None:
    """Always runs (in or out of window): the record must exist with the
    canonical structure so future operators can read the rules."""
    assert FREEZE_RECORD.exists(), (
        f"Freeze record missing at {FREEZE_RECORD.relative_to(REPO_ROOT)}. "
        "TASK-FREEZE-ABST AC-001 requires it."
    )
    text = FREEZE_RECORD.read_text(encoding="utf-8")
    for needle in (
        "2026-05-11",
        "2026-05-17",
        "## Granted overrides",
        "TASK-REV-ABST-review-report.md",
    ):
        assert needle in text, (
            f"Freeze record is missing required marker {needle!r}. "
            "Update the record or this guard, but keep them in sync."
        )


@pytest.mark.skipif(
    not _in_window(_today()),
    reason=(
        f"Gate-stack freeze window is {FREEZE_START}..{FREEZE_END} (inclusive); "
        f"today is {_today()} — guard is a no-op outside the window."
    ),
)
def test_gate_freeze_no_forbidden_commits() -> None:
    overrides = _read_overrides()
    offenders: list[str] = []
    for sha, subject, paths in _commits_in_window():
        frozen_hits = _touches_frozen(paths)
        if not frozen_hits:
            continue
        if _is_revert(subject):
            continue
        if _is_doc_or_test_only(paths):
            continue
        if _is_single_line_guard(sha, frozen_hits):
            continue
        match = TASK_ID_RE.search(subject)
        if match and match.group(0) in overrides:
            continue
        offenders.append(
            f"  {sha[:12]}  {subject!r}  → frozen paths touched: {frozen_hits}"
        )
    assert not offenders, (
        f"\nGate-stack freeze ({FREEZE_START}..{FREEZE_END}) violated by "
        f"{len(offenders)} commit(s) touching frozen paths without override.\n"
        f"See {FREEZE_RECORD.relative_to(REPO_ROOT)} for the freeze rules "
        "and exception protocol.\n" + "\n".join(offenders)
    )
