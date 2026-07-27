"""Mechanical spec-conformance guard — schema, executor, and task-load snapshot.

FEAT-SCG (stage SCG-001). A deterministic, stack-agnostic conformance check
class that mechanizes the three checks a frontier coordinator re-ran by hand
on 2026-07-26 (byte-parity against a spec'd contract, AC-cited-path presence,
and stack-specific invariants via an escape-hatch command). No LLM calls; text,
path, and subprocess only — it never imports or parses the target app's
language.

This module ships the pieces SCG-001 owns; wiring into the Coach loop (the
evidence leg + the verdict-override guard) is SCG-002.

Three moving parts:

1. **Schema** (:class:`ConformanceBlock` and the rule union). A task declares
   rules under a ``conformance:`` block in its YAML frontmatter. Strict
   (``extra="forbid"``) and loud on an unknown ``type`` or a typo'd key — the
   CMIR loud-degrade lesson. Both ``ac_paths`` and ``rules`` are opt-in; an
   absent block is a byte-equivalent no-op.

2. **Executor** (:func:`evaluate` / :func:`evaluate_from_snapshot`). Pure
   functions returning ``{status, failures}`` with an actionable ``detail``
   per rule type. Absence-of-failure discipline throughout: an absent block,
   an absent authority snapshot, or an executor crash yields ``absent`` + a
   logged warning — never a fabricated pass or fail.

3. **Snapshot** (:func:`snapshot_task_conformance`). Captured BEFORE Player
   turn 1 into the task-private dir (outside the shared worktree): the parsed
   ``conformance`` block plus the BYTES of every ``byte_parity`` rule's
   authority file. All later comparisons read the snapshot, so a Player that
   edits both sides inside the worktree can no longer stay green — the CV4M
   hole closed structurally.
"""

from __future__ import annotations

import difflib
import json
import logging
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from typing_extensions import Annotated

logger = logging.getLogger(__name__)

# Tail length (characters) retained from an assert_command's combined output
# so a Player has enough context to act without the feedback ballooning.
_OUTPUT_TAIL_CHARS: int = 2000

# Default per-command timeout for assert_command (seconds), overridable per rule.
_DEFAULT_ASSERT_TIMEOUT: int = 120


# =========================================================================
# 1. Rule schema (the ``conformance:`` block)
# =========================================================================


class SubjectRegion(BaseModel):
    """A marker-delimited region of a ``byte_parity`` subject file.

    The region is the text lying strictly BETWEEN the first occurrence of
    ``start`` and the first occurrence of ``end`` that follows it (both
    markers excluded). When either marker is absent from the subject the
    rule FAILS (the expected region is not present) — it never silently
    passes.
    """

    model_config = ConfigDict(extra="forbid")

    start: str = Field(min_length=1)
    end: str = Field(min_length=1)


class UniqueToken(BaseModel):
    """Bound how many times a token may appear across matched paths.

    The CMIR-003 duplicate-resolver class: a required token must exist, but
    a *second* copy (e.g. a duplicated env-only resolver) is the defect.
    """

    model_config = ConfigDict(extra="forbid")

    token: str = Field(min_length=1)
    max_count: int = Field(default=1, ge=0)
    paths: List[str] = Field(min_length=1)


class RequireTestTokens(BaseModel):
    """Require named tokens to be present somewhere under test paths.

    The CMIR-003 "required tier-tests exist" class: an omission produces no
    failing test, so the guard asserts the tests themselves were authored.
    """

    model_config = ConfigDict(extra="forbid")

    paths: List[str] = Field(min_length=1)
    tokens: List[str] = Field(min_length=1)


class ByteParityRule(BaseModel):
    """Byte-compare a subject region against a captured authority (CV4M class).

    The ``authority`` side is snapshotted pre-build out of the Player's reach
    (see :func:`snapshot_task_conformance`); the ``subject`` side is read live
    from the worktree. When they differ the failure ``detail`` is a unified
    diff.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: Literal["byte_parity"]
    authority: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    subject_region: Optional[SubjectRegion] = None


class TokenCoverageRule(BaseModel):
    """Assert required tokens are present (and duplicates bounded) — CMIR class.

    An omission produces no failing test; the coach grades what is present.
    This rule turns "the tier simply never built" into a mechanical failure.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: Literal["token_coverage"]
    paths: List[str] = Field(min_length=1)
    require_tokens: List[str] = Field(default_factory=list)
    unique_token: Optional[UniqueToken] = None
    require_test_tokens: Optional[RequireTestTokens] = None


class AssertCommandRule(BaseModel):
    """Run a command; exit code == ``expected_exit`` is the pass (SBHO class).

    The stack-agnostic escape hatch — any invariant a byte/token check cannot
    express rides a subprocess exit code.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    type: Literal["assert_command"]
    command: str = Field(min_length=1)
    expected_exit: int = 0
    timeout: int = Field(default=_DEFAULT_ASSERT_TIMEOUT, ge=1, le=600)


# Discriminated union: an unknown ``type`` value raises a loud, precise
# validation error (the CMIR loud-degrade lesson) instead of silently
# matching the first member. The discriminator rides the union itself (not the
# enclosing list) per Pydantic v2.
ConformanceRule = Annotated[
    Union[ByteParityRule, TokenCoverageRule, AssertCommandRule],
    Field(discriminator="type"),
]


class ConformanceBlock(BaseModel):
    """The per-task ``conformance:`` frontmatter block.

    ``ac_paths`` and ``rules`` are both opt-in in v1 — flipping any default ON
    later is a separate, data-backed decision, not this lane's. An absent
    block is a byte-equivalent no-op (the whole feature does nothing).
    """

    model_config = ConfigDict(extra="forbid")

    ac_paths: bool = False
    rules: List[ConformanceRule] = Field(default_factory=list)


def parse_conformance_block(raw: Dict[str, Any]) -> ConformanceBlock:
    """Validate a raw ``conformance`` mapping into a :class:`ConformanceBlock`.

    Loud on an unknown rule ``type`` or a typo'd key (``extra="forbid"``). The
    raised error message names the offending field so a task author can fix
    the frontmatter directly.

    Parameters
    ----------
    raw : dict
        The raw ``conformance`` mapping from the task's YAML frontmatter.

    Returns
    -------
    ConformanceBlock
        The validated block.

    Raises
    ------
    ValueError
        If the block is malformed (unknown type, typo'd key, missing
        required field). The message is plain-language and field-scoped.
    """
    try:
        return ConformanceBlock.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(
            "Invalid `conformance:` block in task frontmatter:\n"
            f"{exc}\n\n"
            "Allowed rule types: byte_parity, token_coverage, assert_command. "
            "Unknown keys are rejected — check for typos."
        ) from exc


# =========================================================================
# 2. Executor (pure; reads declared paths / snapshot + runs assert_command)
# =========================================================================


def _make_absent(reason: str, *, task_id: Optional[str] = None) -> Dict[str, Any]:
    """Return an ``absent`` result and log the reason (never a fabricated verdict)."""
    logger.warning(
        "FEAT-SCG spec-conformance ABSENT%s: %s",
        f" ({task_id})" if task_id else "",
        reason,
    )
    return {"status": "absent", "failures": []}


def _read_text(path: Path) -> Optional[str]:
    """Read *path* as UTF-8 text (errors replaced), or ``None`` when unreadable."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _resolve_paths(subject_root: Path, patterns: List[str]) -> List[Path]:
    """Resolve declared glob/plain patterns to existing files under *subject_root*.

    Supports ``**`` recursive globs (pathlib semantics). A plain path that
    does not exist resolves to nothing — the caller treats that as the token
    being absent (a real failure for the omission class), never a crash.
    """
    resolved: List[Path] = []
    seen: set = set()
    for pattern in patterns:
        try:
            matches = sorted(subject_root.glob(pattern))
        except (ValueError, OSError):
            matches = []
        for match in matches:
            if match.is_file() and match not in seen:
                seen.add(match)
                resolved.append(match)
    return resolved


def _extract_region(text: str, region: SubjectRegion) -> Optional[str]:
    """Extract the text strictly between *region*'s markers.

    Returns ``None`` when either marker is absent (a real conformance failure
    — the expected region is not present in the subject).
    """
    start_idx = text.find(region.start)
    if start_idx < 0:
        return None
    region_start = start_idx + len(region.start)
    end_idx = text.find(region.end, region_start)
    if end_idx < 0:
        return None
    return text[region_start:end_idx]


def _unified_diff(authority: str, subject: str, *, rule_id: str) -> str:
    """Build a unified diff of authority (expected) vs subject (actual)."""
    diff = difflib.unified_diff(
        authority.splitlines(keepends=True),
        subject.splitlines(keepends=True),
        fromfile=f"authority (expected) [{rule_id}]",
        tofile="subject (actual)",
    )
    return "".join(diff)


def _evaluate_byte_parity(
    rule: ByteParityRule,
    authority_bytes: bytes,
    subject_root: Path,
) -> Optional[Dict[str, Any]]:
    """Evaluate one byte_parity rule. Returns a failure dict or ``None`` (pass)."""
    authority_text = authority_bytes.decode("utf-8", errors="replace")

    subject_path = subject_root / rule.subject
    subject_text = _read_text(subject_path)
    if subject_text is None:
        return {
            "rule_id": rule.id,
            "kind": "byte_parity",
            "detail": (
                f"Subject file not found or unreadable: {rule.subject}. "
                f"It must exist and byte-match the captured authority "
                f"({rule.authority})."
            ),
        }

    if rule.subject_region is not None:
        extracted = _extract_region(subject_text, rule.subject_region)
        if extracted is None:
            return {
                "rule_id": rule.id,
                "kind": "byte_parity",
                "detail": (
                    f"Region markers not found in {rule.subject}: expected the "
                    f"text between start marker {rule.subject_region.start!r} "
                    f"and end marker {rule.subject_region.end!r}. Restore the "
                    f"marker-delimited block so it can be compared to the "
                    f"authority ({rule.authority})."
                ),
            }
        subject_compare = extracted
    else:
        subject_compare = subject_text

    if subject_compare == authority_text:
        return None

    diff = _unified_diff(authority_text, subject_compare, rule_id=rule.id)
    region_note = (
        f" (region between {rule.subject_region.start!r} and "
        f"{rule.subject_region.end!r})"
        if rule.subject_region is not None
        else ""
    )
    return {
        "rule_id": rule.id,
        "kind": "byte_parity",
        "detail": (
            f"{rule.subject}{region_note} does not byte-match the captured "
            f"authority ({rule.authority}). Edit the subject to match the "
            f"authority exactly — the authority side is captured out of your "
            f"reach and cannot be changed.\n\nUnified diff (authority=expected, "
            f"subject=actual):\n{diff}"
        ),
    }


def _evaluate_token_coverage(
    rule: TokenCoverageRule,
    subject_root: Path,
) -> Optional[Dict[str, Any]]:
    """Evaluate one token_coverage rule. Returns a failure dict or ``None``."""
    problems: List[str] = []

    # --- require_tokens: each must appear in at least one matched path. ---
    if rule.require_tokens:
        files = _resolve_paths(subject_root, rule.paths)
        blobs = [t for t in (_read_text(f) for f in files) if t is not None]
        combined = "\n".join(blobs)
        missing = [tok for tok in rule.require_tokens if tok not in combined]
        if missing:
            searched = ", ".join(rule.paths)
            if files:
                problems.append(
                    f"Required token(s) not found in [{searched}]: "
                    + ", ".join(repr(t) for t in missing)
                    + ". Add the missing implementation so each token appears."
                )
            else:
                problems.append(
                    f"No files matched [{searched}], so required token(s) are "
                    f"absent: " + ", ".join(repr(t) for t in missing)
                    + ". Create the file(s) and the required content."
                )

    # --- unique_token: bound how many times a token appears. ---
    if rule.unique_token is not None:
        ut = rule.unique_token
        ut_files = _resolve_paths(subject_root, ut.paths)
        count = 0
        locations: List[str] = []
        for f in ut_files:
            text = _read_text(f)
            if text is None:
                continue
            occurrences = text.count(ut.token)
            if occurrences:
                count += occurrences
                rel = _relative_to(f, subject_root)
                locations.append(f"{rel} (x{occurrences})")
        if count > ut.max_count:
            problems.append(
                f"Token {ut.token!r} appears {count} time(s) across "
                f"[{', '.join(ut.paths)}] but at most {ut.max_count} is "
                f"allowed. Remove the duplicate(s). Found in: "
                + "; ".join(locations)
                + "."
            )

    # --- require_test_tokens: named tokens must exist under test paths. ---
    if rule.require_test_tokens is not None:
        rtt = rule.require_test_tokens
        test_files = _resolve_paths(subject_root, rtt.paths)
        test_blobs = [
            t for t in (_read_text(f) for f in test_files) if t is not None
        ]
        test_combined = "\n".join(test_blobs)
        missing_tests = [tok for tok in rtt.tokens if tok not in test_combined]
        if missing_tests:
            problems.append(
                f"Required test token(s) not found under [{', '.join(rtt.paths)}]: "
                + ", ".join(repr(t) for t in missing_tests)
                + ". Author the test(s) that exercise the required behaviour."
            )

    if not problems:
        return None
    return {
        "rule_id": rule.id,
        "kind": "token_coverage",
        "detail": "\n".join(problems),
    }


def _relative_to(path: Path, root: Path) -> str:
    """Best-effort repo-relative display path (falls back to absolute)."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _evaluate_assert_command(
    rule: AssertCommandRule,
    subject_root: Path,
) -> Optional[Dict[str, Any]]:
    """Evaluate one assert_command rule. Returns a failure dict or ``None``."""
    try:
        completed = subprocess.run(
            rule.command,
            shell=True,
            cwd=str(subject_root),
            capture_output=True,
            text=True,
            timeout=rule.timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "rule_id": rule.id,
            "kind": "assert_command",
            "detail": (
                f"Command timed out after {rule.timeout}s: {rule.command}. "
                f"A command that hangs is treated as a failure — fix the "
                f"underlying invariant so it completes and exits "
                f"{rule.expected_exit}."
            ),
        }

    if completed.returncode == rule.expected_exit:
        return None

    combined = (completed.stdout or "") + (completed.stderr or "")
    tail = combined[-_OUTPUT_TAIL_CHARS:]
    return {
        "rule_id": rule.id,
        "kind": "assert_command",
        "detail": (
            f"Command exited {completed.returncode} (expected "
            f"{rule.expected_exit}): {rule.command}\n\nOutput tail:\n"
            f"{tail or '<empty>'}"
        ),
    }


# --- ac_paths: AC-cited path presence over the structured ACs. ---
#
# The extraction generalizes ``AgentInvoker._scan_ac_for_missing_paths`` and is
# made non-Python-safe: any extension is accepted (not just ``.py``/JS/TS), and
# only fully-qualified paths (those containing ``/``) are checked — a bare
# basename is skipped (AC text routinely names a file by basename when the
# directory is established elsewhere; treating that as missing is a false
# positive, the FEAT-PEBR Wave-1 root cause).
_AC_PRIMARY_RE = r"[\w./\-]+\.\w{1,8}"
_AC_BACKTICK_RE = r"`([^`]+\.[A-Za-z0-9]+)`"
_AC_DOUBLE_Q_RE = r'"([^"]+\.[A-Za-z0-9]+)"'
_AC_SINGLE_Q_RE = r"'([^']+\.[A-Za-z0-9]+)'"


def _extract_ac_paths(acceptance_criteria: List[Dict[str, str]]) -> List[str]:
    """Extract fully-qualified, path-shaped tokens from AC text (stack-agnostic)."""
    import re

    text = "\n".join(str(ac.get("text", "")) for ac in acceptance_criteria)
    # Resolve markdown links ``[label](href)`` to the href only — a label may
    # itself be path-shaped but is a display string, not a cited file.
    text = re.sub(r"\[[^\]]*\]\(([^)]+)\)", r"\1", text)
    candidates = (
        re.findall(_AC_PRIMARY_RE, text)
        + re.findall(_AC_BACKTICK_RE, text)
        + re.findall(_AC_DOUBLE_Q_RE, text)
        + re.findall(_AC_SINGLE_Q_RE, text)
    )
    paths: List[str] = []
    seen: set = set()
    for cand in candidates:
        if "*" in cand:  # a glob, not a concrete cited path
            continue
        if "/" not in cand:  # bare basename — skip (false-positive guard)
            continue
        if cand in seen:
            continue
        seen.add(cand)
        paths.append(cand)
    return paths


def _evaluate_ac_paths(
    acceptance_criteria: Optional[List[Dict[str, str]]],
    subject_root: Path,
) -> Optional[Dict[str, Any]]:
    """Check AC-cited paths exist under *subject_root*. Failure dict or ``None``.

    No ACs (``None``/empty) or no path-shaped tokens ⇒ ``None`` (nothing to
    check — never a fabricated failure).
    """
    if not acceptance_criteria:
        return None
    cited = _extract_ac_paths(acceptance_criteria)
    if not cited:
        return None
    missing = [p for p in cited if not (subject_root / p).exists()]
    if not missing:
        return None
    return {
        "rule_id": "ac_paths",
        "kind": "ac_paths",
        "detail": (
            "Path(s) named in the acceptance criteria are missing from the "
            "worktree: " + ", ".join(missing) + ". Create each cited file "
            "(or correct the path in the AC if it was a typo)."
        ),
    }


def evaluate_ac_paths(
    acceptance_criteria: Optional[List[Dict[str, str]]],
    subject_root: Path,
) -> Optional[Dict[str, Any]]:
    """Public seam over :func:`_evaluate_ac_paths` (SCG-002).

    The opt-in ``ac_paths`` presence check is applied at Coach-turn time by
    ``AgentInvoker._apply_spec_conformance_guard`` (it needs the turn's
    structured acceptance criteria), separately from the declarative rule leg.
    This wrapper exposes the SCG-001 extractor to that guard without reaching
    into a private symbol. Returns a ``{rule_id, kind, detail}`` failure dict
    when an AC-cited, fully-qualified path is missing from *subject_root*, else
    ``None`` (no ACs, no path-shaped tokens, or every cited path present).
    """
    return _evaluate_ac_paths(acceptance_criteria, subject_root)


def evaluate(
    block: Optional[ConformanceBlock],
    authority_bytes: Dict[str, bytes],
    subject_root: Path,
    *,
    acceptance_criteria: Optional[List[Dict[str, str]]] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Evaluate a conformance block against a live subject tree (pure executor).

    Absence-of-failure discipline: returns ``absent`` (never a fabricated
    verdict) when the block is ``None``/empty, when a ``byte_parity`` rule's
    authority snapshot is missing from *authority_bytes*, or when evaluation
    crashes unexpectedly.

    Parameters
    ----------
    block : ConformanceBlock or None
        The parsed (snapshotted) conformance block.
    authority_bytes : dict[str, bytes]
        Captured authority bytes keyed by ``byte_parity`` rule id (from the
        snapshot). All comparisons read these, never a live authority path.
    subject_root : Path
        The worktree root — subjects, token paths, and assert_command all read
        from / run under here.
    acceptance_criteria : list[dict] or None
        Structured ACs (``[{"id","text"}]``) for the ``ac_paths`` check.
    task_id : str or None
        For the WARNING log on absence.

    Returns
    -------
    dict
        ``{"status": "absent"|"passed"|"failed", "failures": [...]}`` where each
        failure is ``{"rule_id", "kind", "detail"}`` with an actionable detail.
    """
    if block is None:
        return _make_absent("no conformance block declared", task_id=task_id)
    if not block.rules and not block.ac_paths:
        return _make_absent(
            "conformance block declares neither rules nor ac_paths",
            task_id=task_id,
        )

    try:
        failures: List[Dict[str, Any]] = []

        for rule in block.rules:
            if isinstance(rule, ByteParityRule):
                if rule.id not in authority_bytes:
                    # Authority snapshot missing ⇒ we cannot verify this rule.
                    # Never fabricate a verdict for the whole evaluation.
                    return _make_absent(
                        f"authority snapshot missing for byte_parity rule "
                        f"{rule.id!r} (authority {rule.authority})",
                        task_id=task_id,
                    )
                result = _evaluate_byte_parity(
                    rule, authority_bytes[rule.id], subject_root
                )
                if result is not None:
                    failures.append(result)
            elif isinstance(rule, TokenCoverageRule):
                result = _evaluate_token_coverage(rule, subject_root)
                if result is not None:
                    failures.append(result)
            elif isinstance(rule, AssertCommandRule):
                result = _evaluate_assert_command(rule, subject_root)
                if result is not None:
                    failures.append(result)

        if block.ac_paths:
            ac_result = _evaluate_ac_paths(acceptance_criteria, subject_root)
            if ac_result is not None:
                failures.append(ac_result)

    except Exception as exc:  # pragma: no cover - defensive absence-of-failure
        return _make_absent(f"executor crashed: {exc!r}", task_id=task_id)

    status = "failed" if failures else "passed"
    return {"status": status, "failures": failures}


# =========================================================================
# 3. Snapshot at task load (the CV4M bypass-resistance crux)
# =========================================================================
#
# SEAM (pinned): the snapshot fires in
# ``AutoBuildOrchestrator.orchestrate`` immediately after ``_setup_phase``
# creates the worktree and before Phase 2/3 — i.e. before any Player activity.
# CONSTRAINT: pre-turn-1 and Player-unreachable. It writes into
# ``TaskArtifactPaths.task_private_dir`` (``guardkit/orchestrator/paths.py``),
# which post-SBHO resolves OUTSIDE the shared worktree — a Player editing both
# the subject and its (live) authority inside the worktree can no longer stay
# green, because the executor reads THIS snapshot, never the live authority.

_SNAPSHOT_SUBDIR = "spec_conformance"
_SNAPSHOT_BLOCK_FILE = "conformance.json"
_SNAPSHOT_AUTHORITY_SUBDIR = "authority"


def snapshot_paths(task_id: str, worktree_path: Path) -> Dict[str, Path]:
    """Return the snapshot dir + block/authority paths for a task.

    Pure path derivation (no I/O). ``TaskArtifactPaths.task_private_dir``
    resolves outside the shared worktree post-SBHO.
    """
    from guardkit.orchestrator.paths import TaskArtifactPaths

    base = (
        TaskArtifactPaths.task_private_dir(task_id, worktree_path)
        / _SNAPSHOT_SUBDIR
    )
    return {
        "dir": base,
        "block": base / _SNAPSHOT_BLOCK_FILE,
        "authority_dir": base / _SNAPSHOT_AUTHORITY_SUBDIR,
    }


def snapshot_task_conformance(
    task_id: str,
    worktree_path: Path,
    repo_root: Path,
) -> Optional[Path]:
    """Snapshot a task's conformance block + byte_parity authority bytes.

    Called BEFORE Player turn 1 (see the SEAM comment above). Reads the task's
    ``conformance`` frontmatter and, when present and valid, writes:

    * ``<private>/spec_conformance/conformance.json`` — the validated block.
    * ``<private>/spec_conformance/authority/<rule_id>`` — the bytes of each
      ``byte_parity`` rule's authority file (read from *repo_root*, the
      canonical source, at snapshot time).

    Absence-of-failure / no-regression discipline:

    * No ``conformance`` block ⇒ returns ``None``, writes nothing (a build
      without the block is a byte-equivalent no-op).
    * A MALFORMED block ⇒ logged loudly at ERROR (the CMIR loud-degrade
      lesson), then degrades to ``None`` — a schema typo in an opt-in feature
      must never crash an existing build. (The schema itself raises for direct
      callers; whether a future load path hard-fails is SCG-002's call.)
    * A missing authority file at snapshot time ⇒ logged warning, that rule's
      authority is simply not written, so the executor later degrades to
      ``absent`` for it — never a fabricated verdict.
    * Any other error ⇒ logged warning, returns ``None``.

    Returns
    -------
    Path or None
        The snapshot directory when a block was captured, else ``None``.
    """
    try:
        from guardkit.tasks.task_loader import TaskLoader

        try:
            task_data = TaskLoader.load_task(task_id, repo_root=repo_root)
        except Exception as exc:
            logger.debug(
                "FEAT-SCG snapshot: could not load task %s (%s) — nothing to "
                "snapshot",
                task_id,
                exc,
            )
            return None

        frontmatter = task_data.get("frontmatter") or {}
        raw_block = frontmatter.get("conformance")
        if raw_block is None:
            return None  # byte-equivalent no-op for the vast majority of tasks

        try:
            block = parse_conformance_block(raw_block)
        except ValueError as exc:
            logger.error(
                "FEAT-SCG snapshot: task %s has a MALFORMED `conformance:` "
                "block — the guard will NOT run for this task until it is "
                "fixed. %s",
                task_id,
                exc,
            )
            return None

        paths = snapshot_paths(task_id, worktree_path)
        snapshot_dir: Path = paths["dir"]
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        # (a) the parsed block.
        paths["block"].write_text(
            json.dumps(block.model_dump(mode="json"), indent=2),
            encoding="utf-8",
        )

        # (b) the bytes of every byte_parity rule's authority file.
        authority_dir: Path = paths["authority_dir"]
        for rule in block.rules:
            if not isinstance(rule, ByteParityRule):
                continue
            authority_src = repo_root / rule.authority
            try:
                data = authority_src.read_bytes()
            except OSError as exc:
                logger.warning(
                    "FEAT-SCG snapshot: byte_parity rule %r authority not "
                    "readable at %s (%s) — not captured; the guard will "
                    "degrade to ABSENT for this rule",
                    rule.id,
                    rule.authority,
                    exc,
                )
                continue
            authority_dir.mkdir(parents=True, exist_ok=True)
            (authority_dir / rule.id).write_bytes(data)

        logger.info(
            "FEAT-SCG snapshot: captured conformance block for %s "
            "(%d rule(s), ac_paths=%s) at %s",
            task_id,
            len(block.rules),
            block.ac_paths,
            snapshot_dir,
        )
        return snapshot_dir

    except Exception as exc:  # pragma: no cover - defensive
        logger.warning(
            "FEAT-SCG snapshot: unexpected error snapshotting %s (%s) — "
            "guard will be absent for this task",
            task_id,
            exc,
        )
        return None


def load_snapshot(
    snapshot_dir: Path,
) -> Optional[tuple["ConformanceBlock", Dict[str, bytes]]]:
    """Load a captured snapshot: the parsed block + authority bytes by rule id.

    Returns ``None`` when the snapshot is absent or unreadable (the executor
    caller degrades to ``absent``).
    """
    block_path = snapshot_dir / _SNAPSHOT_BLOCK_FILE
    if not block_path.exists():
        return None
    try:
        raw = json.loads(block_path.read_text(encoding="utf-8"))
        block = ConformanceBlock.model_validate(raw)
    except (OSError, ValueError, ValidationError):
        return None

    authority_bytes: Dict[str, bytes] = {}
    authority_dir = snapshot_dir / _SNAPSHOT_AUTHORITY_SUBDIR
    if authority_dir.is_dir():
        for rule in block.rules:
            if not isinstance(rule, ByteParityRule):
                continue
            captured = authority_dir / rule.id
            try:
                authority_bytes[rule.id] = captured.read_bytes()
            except OSError:
                continue  # missing ⇒ executor degrades to absent for the rule
    return block, authority_bytes


def evaluate_from_snapshot(
    snapshot_dir: Path,
    subject_root: Path,
    *,
    acceptance_criteria: Optional[List[Dict[str, str]]] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Load a captured snapshot and evaluate it against the live subject tree.

    This is the orchestrator-facing entry point. Reads the SNAPSHOT block and
    authority bytes (never the live authority path) and evaluates against
    *subject_root* (the worktree). Any failure to load ⇒ ``absent``.
    """
    try:
        loaded = load_snapshot(snapshot_dir)
    except Exception as exc:  # pragma: no cover - defensive
        return _make_absent(
            f"snapshot unreadable at {snapshot_dir} ({exc!r})", task_id=task_id
        )
    if loaded is None:
        return _make_absent(
            f"no readable snapshot at {snapshot_dir}", task_id=task_id
        )
    block, authority_bytes = loaded
    return evaluate(
        block,
        authority_bytes,
        subject_root,
        acceptance_criteria=acceptance_criteria,
        task_id=task_id,
    )
