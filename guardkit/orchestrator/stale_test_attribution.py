"""Stale-test attribution for parity/smoke-gate feedback (TASK-AB-STALEATTRIB01).

When the per-task runtime-parity guard
(``agent_invoker._apply_runtime_parity_guard``) or the post-wave smoke gate
(``feature_orchestrator._build_smoke_feedback``) fails on a test authored by an
EARLIER task, the current Player's feedback must (a) name the failing test and
(b) — when the authorship join resolves unambiguously — grant a narrowly-scoped
permission to amend the stale assertion the current task otherwise cannot touch
(by scope). The 2026-07-03 study-tutor retro showed the cost of the gap: a
task burned five turns (max_turns_exceeded) on a stale
``NotImplementedError``-boundary test authored by its predecessor task that
its feedback never named.

Every helper here fails OPEN: unparseable output, no match, multiple matches,
missing records, or any exception leave the caller's existing framing unchanged
(``path-string-mismatch-is-not-dishonesty.md``). Nothing here suppresses or
reclassifies the red signal — the verdict flip and ``must_fix`` severity are
owned by the callers and untouched.
"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path, PurePosixPath
from typing import Collection, Iterable, List, Optional, Union

logger = logging.getLogger(__name__)

# Substring heuristic for "the smoke command is a test-runner invocation".
# ``python -m pytest`` is covered by the bare ``pytest`` marker.
_TEST_RUNNER_MARKERS = ("pytest", "npm test", "dotnet test", "go test")

# pytest short-summary lines: ``FAILED tests/x.py::test_y - reason`` /
# ``ERROR tests/x.py`` (optionally with a `` - <reason>`` suffix).
_FAILING_LINE_RE = re.compile(r"^\s*(FAILED|ERROR)\s+(\S+)", re.MULTILINE)

# One-shot sentinel so a bug in the extraction loop is LOUD exactly once per
# process instead of silently blanking every failing-test name across the
# parity / smoke / stall surfaces (2026-07-04 review, FIX 3a).
_extract_warn_emitted = False


def is_test_runner_command(command: Optional[str]) -> bool:
    """True when ``command`` recognisably invokes a test runner."""
    if not command:
        return False
    return any(marker in command for marker in _TEST_RUNNER_MARKERS)


def extract_failing_test_lines(output: Optional[str]) -> List[str]:
    """Extract pytest failing-test node-ID lines from runner output.

    Returns deduplicated ``"FAILED <path>::<test>"`` / ``"ERROR <path>"``
    strings (the `` - <reason>`` suffix is dropped) in first-seen order.
    Unparseable / empty output yields ``[]`` (fail open).
    """
    global _extract_warn_emitted
    if not output:
        return []
    lines: List[str] = []
    seen: set = set()
    try:
        for match in _FAILING_LINE_RE.finditer(output):
            entry = f"{match.group(1)} {match.group(2)}"
            if entry not in seen:
                seen.add(entry)
                lines.append(entry)
    except Exception as exc:  # noqa: BLE001 — fail OPEN, never raise
        if not _extract_warn_emitted:
            _extract_warn_emitted = True
            logger.warning(
                "TASK-AB-STALEATTRIB01: failing-test line extraction raised "
                "%s: %s — returning [] (fail open). Failing-test names will "
                "be ABSENT from parity/smoke/stall feedback until this is "
                "fixed (logged once per process).",
                type(exc).__name__,
                exc,
            )
        return []
    return lines


def failing_test_files(failing_lines: Iterable[str]) -> List[str]:
    """Map failing node-ID lines to their distinct test-file paths (in order)."""
    files: List[str] = []
    seen: set = set()
    for line in failing_lines:
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        path = parts[1].split("::", 1)[0]
        if path and path not in seen:
            seen.add(path)
            files.append(path)
    return files


def _normalise_relpath(
    path_str: str, worktree_root: Union[str, Path]
) -> Optional[str]:
    """Normalise a path string to a worktree-relative posix form, or ``None``."""
    try:
        s = str(path_str).strip()
        if not s:
            return None
        p = PurePosixPath(s.replace("\\", "/"))
        if p.is_absolute():
            root = PurePosixPath(str(worktree_root).replace("\\", "/"))
            try:
                p = p.relative_to(root)
            except ValueError:
                return str(p)
        return "/".join(part for part in p.parts if part != ".")
    except Exception:  # noqa: BLE001 — fail OPEN, never raise
        return None


def _authored_files(data: dict) -> List[str]:
    """The authorship-based file set for one task's results record.

    Uses ``files_authored`` (the Write/Edit-captured record) when present,
    falling back to ``files_created`` ONLY — **never** ``files_modified``.
    ``files_modified`` is union-merged with the post-turn ``git diff`` paths
    (``agent_invoker`` merges ``git_modified`` into the report), so it names
    files a task merely *touched*: a pre-existing regression test that task A
    trivially edited would be attributed to A, and a later task B that breaks
    the tested behaviour would then be told it "may amend or delete that
    specific stale assertion" — licensing deletion of a genuine regression
    guard (a false-green enabler). Narrower is safe here because every miss
    fails OPEN: no match → no note → the caller's default red framing stands
    unchanged. (Deliberately NARROWER than
    ``feature_orchestrator._wave_authored_files``, whose write-surface
    aperture wants the touched union.)
    """
    if isinstance(data.get("files_authored"), list):
        return [str(f) for f in data["files_authored"]]
    return [str(f) for f in list(data.get("files_created") or [])]


def _build_authorship_map(
    worktree_root: Union[str, Path],
) -> dict:
    """One scan of ``.guardkit/autobuild/*/task_work_results.json``.

    Returns ``{normalised_relpath: {task_ids}}`` built from a SINGLE pass over
    the per-task records, so a batch of failing files is answered without
    re-reading every record per file (previously O(files × tasks) JSON loads
    inside the per-turn verdict seam). Missing / unreadable / malformed
    records contribute nothing (fail open); may raise only for filesystem
    iteration errors, which callers catch.
    """
    authorship: dict = {}
    autobuild_root = Path(worktree_root) / ".guardkit" / "autobuild"
    if not autobuild_root.is_dir():
        return authorship
    for task_dir in sorted(autobuild_root.iterdir()):
        if not task_dir.is_dir():
            continue
        results_path = task_dir / "task_work_results.json"
        if not results_path.exists():
            continue
        try:
            data = json.loads(results_path.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        for f in _authored_files(data):
            normalised = _normalise_relpath(f, worktree_root)
            if normalised:
                authorship.setdefault(normalised, set()).add(task_dir.name)
    return authorship


def _resolve_authoring_task(
    failing_file: str,
    worktree_root: Union[str, Path],
    current_task_ids: Collection[str],
    authorship: dict,
) -> Optional[str]:
    """Resolve one failing file against a pre-built authorship map."""
    target = _normalise_relpath(failing_file, worktree_root)
    if not target:
        return None
    authors = authorship.get(target) or set()
    current = {str(t) for t in (current_task_ids or ())}
    if authors & current:
        # The current task authored the file itself — not a stale
        # earlier-task assertion; the default framing stands.
        return None
    if len(authors) == 1:
        return next(iter(authors))
    return None  # unmatched (0) or ambiguous (>1) → fail open


def find_authoring_task(
    failing_file: str,
    worktree_root: Union[str, Path],
    current_task_ids: Collection[str],
) -> Optional[str]:
    """Return the single OTHER task whose authored-files record names ``failing_file``.

    Single-file convenience over ``_build_authorship_map`` — one scan of every
    ``.guardkit/autobuild/<task_id>/task_work_results.json`` under
    ``worktree_root`` (batch callers like ``stale_test_notes`` build the map
    once and resolve all files from it). Authorship is the narrow
    Write/Edit-captured set (see ``_authored_files``), across ALL task dirs,
    not just one wave. Fail-OPEN contract
    (``path-string-mismatch-is-not-dishonesty.md``): returns ``None`` when the
    file is unmatched, matched by multiple tasks, matched by a current task,
    records are missing/unreadable, or anything raises.
    """
    try:
        return _resolve_authoring_task(
            failing_file,
            worktree_root,
            current_task_ids,
            _build_authorship_map(worktree_root),
        )
    except Exception as exc:  # noqa: BLE001 — fail OPEN, never raise
        logger.debug(
            "TASK-AB-STALEATTRIB01: authorship join skipped for %s: %s",
            failing_file,
            exc,
        )
        return None


def build_stale_test_note(
    failing_file: str,
    authoring_task_id: str,
    failing_lines: Iterable[str] = (),
) -> str:
    """Compose the Player-facing stale-test attribution note.

    Names the specific failing test(s) and the authoring task. The
    amend/delete permission is CONDITIONAL: it applies only when the
    assertion pins transient scaffold state from the named task — a genuine
    regression guard for behaviour the current change broke must be fixed in
    the implementation, never deleted (2026-07-04 review, FIX 1b). The
    permission never extends beyond that one assertion — not the whole file
    or suite.
    """
    named = "; ".join(failing_lines) or failing_file
    return (
        f"STALE-TEST ATTRIBUTION: the failing test(s) — {named} — live in "
        f"{failing_file}, which was authored by {authoring_task_id}, not this "
        f"task. You may amend or delete that specific stale assertion in "
        f"{failing_file} ONLY if it pins transient point-in-time scaffold "
        f"state from {authoring_task_id} that this task's changes "
        f"legitimately superseded — change nothing else in that file. If it "
        f"is a genuine regression guard for behaviour your change broke, fix "
        f"your implementation instead — do not delete it."
    )


def stale_test_notes(
    failing_lines: Iterable[str],
    worktree_root: Optional[Union[str, Path]],
    current_task_ids: Collection[str],
) -> List[str]:
    """Attribution notes for every failing file authored by exactly one OTHER task.

    Builds the authorship map with ONE scan of the per-task records
    (``_build_authorship_map``) and answers every failing file from it.
    Fail-OPEN: no worktree root, no attributable file, or any exception yields
    ``[]`` — the caller's existing framing is then emitted unchanged.
    """
    if worktree_root is None:
        return []
    try:
        lines = list(failing_lines)
        files = failing_test_files(lines)
        if not files:
            return []
        authorship = _build_authorship_map(worktree_root)
        notes: List[str] = []
        for failing_file in files:
            authoring = _resolve_authoring_task(
                failing_file, worktree_root, current_task_ids, authorship
            )
            if authoring is None:
                continue
            file_lines = [
                ln
                for ln in lines
                if ln.split(None, 1)[-1].split("::", 1)[0] == failing_file
            ]
            notes.append(
                build_stale_test_note(failing_file, authoring, file_lines)
            )
        return notes
    except Exception as exc:  # noqa: BLE001 — fail OPEN, never raise
        logger.debug("TASK-AB-STALEATTRIB01: stale-test notes skipped: %s", exc)
        return []
