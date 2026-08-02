"""Machine-derived F1 pass bars for producer-minted fix tasks.

**Rich's ruling, 2026-08-02.** The work leg refuses to start a task when
``qa.enforce_tier1`` is armed and no pinned F1 pass bar exists::

    no pinned F1 pass bar for <task>: expected <repo>/qa/pass-bar-<task_id>.yaml
    (the pass bar must be committed BEFORE implementation — qa.enforce_tier1 is on)

That refusal is the *bar-before-implementation* law, and it is checked by
:func:`guardkit.qa.enforcement.check_pass_bar_precondition` (``guardkit/qa/
enforcement.py:363``), armed by :func:`guardkit.qa.enforcement.is_tier1_enforced`
(``:124``) and read into the build by
``AutoBuildOrchestrator._check_qa_pass_bar_precondition``
(``guardkit/orchestrator/autobuild.py:2162``, consumed at ``:1971``). The
schema it validates against is the REAL :class:`guardkit.qa.formats.PassBar`
(``guardkit/qa/formats/pass_bar.py:123``).

A producer-minted fix task has no human author standing between the review leg
and the work leg, so nobody was ever going to write that bar — every fix task
would either refuse at task start or (worse) run in a repo that had quietly
switched enforcement off. So **the review leg's producer mints the bar**, at the
moment it writes the fix-task file: the bar exists BEFORE any work leg can run,
which preserves the law *mechanically* rather than by convention.

Three properties this module is built to hold:

1. **Named machine-derived.** ``PassBar`` is ``extra="forbid"`` — there is no
   field to hang provenance on, so the provenance rides as a leading YAML
   comment block (:data:`PASS_BAR_PROVENANCE_MARKER`) naming the review leg, the
   parent review id, the fix task, and the basis of every judgement the
   derivation had to make. A reader must never mistake one of these for a
   human-authored bar.
2. **Validated before it is written.** The derived mapping is put through
   ``PassBar.model_validate`` — the same call
   :func:`guardkit.qa.formats.base.validate_file` makes — and then the
   *serialised YAML text* is round-tripped back through ``yaml.safe_load`` +
   ``model_validate`` before a single byte reaches disk. An invalid derivation
   is a loud producer error and **no file**; a malformed pass bar on disk would
   be worse than none at all (the checker would fail it, and the reason would
   look like a schema bug rather than a missing derivation).
3. **Nothing is minted when enforcement is not armed.** ``is_tier1_enforced``
   is the one reader; when it says OFF, this module writes nothing at all —
   a repo that never opted in does not grow a ``qa/`` tree because a review ran.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

#: The machine marker every minted bar carries in its leading comment block.
#: ``PassBar`` forbids extra fields, so this is the form the schema admits.
#: Tests (and any human reader) key on this exact string.
PASS_BAR_PROVENANCE_MARKER = "MACHINE-DERIVED PASS BAR"

#: The one-line provenance note the leg receipt repeats under ``pass_bars``.
PASS_BAR_PROVENANCE_NOTE = (
    "machine-derived: minted by the review leg (guardkit task-review) from each "
    "fix task's '## Acceptance Criteria' section at production time, so the F1 "
    "bar exists BEFORE any work leg runs (qa.enforce_tier1's "
    "bar-before-implementation law, held mechanically). Not human-authored — "
    "widening a bar is a human/Coach act."
)

#: Format version written into every minted bar — the model's own current
#: version, read off the class so a schema major bump cannot leave this behind.
_PASS_BAR_FORMAT_VERSION_FALLBACK = "2.0"


# ---------------------------------------------------------------------------
# Derivation inputs
# ---------------------------------------------------------------------------

#: ``## Acceptance Criteria`` checkbox lines, e.g. ``- [ ] Tests passing``.
_CRITERION_RE = re.compile(r"^\s*[-*]\s*\[[ xX]?\]\s*(?P<text>\S.*?)\s*$")

#: A criterion that names its own id (``AC-ANTISTUB-1: All primary …``) keeps
#: it — the producer's anti-stub criteria are referenced by that id elsewhere.
_CRITERION_ID_RE = re.compile(r"^(?P<id>[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)\s*:\s*(?P<text>\S.*)$")

#: Markdown section heading, any level.
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(?P<title>.+?)\s*$")

#: Tokens that evidence an auth surface in the fix task's own text. PB-14 made
#: ``auth_surface_bearing`` required with NO default precisely so an emitter
#: cannot guess it silently: this derivation therefore judges it from the fix
#: task's words and FILES, and writes the basis of the judgement into the
#: provenance block so a reader can see (and correct) what it saw. It must be
#: genuinely narrow, because a false positive is NOT harmless: beyond widening
#: the declared negative-path set (fabricating auth paths an authless fix has
#: no surface for — the QAV-corpus poison PB-14 names), ``auth_surface_bearing
#: = true`` also flips ``enforcement._pass_bar_is_runtime_surface``, which arms
#: the feature-complete runtime-surface gate — the same fabricated-gate hazard
#: this module refuses the live evidence kinds to avoid. Matching is therefore
#: WORD-BOUNDED (the review-leg coach drove ``author`` → "auth", ``SQLAlchemy
#: session`` → "session", and a line number 4013 → "401" through the old bare
#: substring test), and the noisiest generic words (``session``,
#: ``permission``, bare status codes) are out — a real auth fix names auth by
#: name.
_AUTH_SURFACE_TOKENS: Tuple[str, ...] = (
    "auth",
    "authn",
    "authz",
    "authentication",
    "authorization",
    "login",
    "logout",
    "signin",
    "sign-in",
    "credential",
    "password",
    "oauth",
    "jwt",
    "bearer token",
    "unauthorized",
)

#: Word-bounded matcher over the token list — ``author``/``authoritative`` must
#: not fire "auth", and a line number containing 401 is not a status code.
#: Hyphenated tokens get their hyphen treated literally.
_AUTH_TOKEN_RE = re.compile(
    r"(?<![a-z0-9])(?:" + "|".join(re.escape(t) for t in _AUTH_SURFACE_TOKENS) + r")(?![a-z0-9])"
)

#: The tier-1 precondition every code fix can honestly declare: the suite runs
#: green against the F2 known-failure ledger. ``analyze_clean`` and
#: ``build_artifact`` are repo-shaped claims a machine derivation cannot make
#: from a fix-task file, so they are NOT declared (an undeclared precondition is
#: honest; a fabricated one poisons the bar).
_DERIVED_PRECONDITIONS: Tuple[str, ...] = ("suite_green_vs_ledger",)

#: Evidence kind for a derived criterion. ``screenshot`` / ``operator_signoff``
#: are the two LIVE kinds (``enforcement._LIVE_EVIDENCE_KINDS``) and declaring
#: either would make every derived bar runtime-surface-bearing at
#: feature-complete — a fabricated gate. ``log`` is what a checker loop actually
#: produces for a fix task.
_DERIVED_EVIDENCE_KIND = "log"

#: The negative path mandatory for EVERY bar (PB-14).
_UNIVERSAL_NEGATIVE_PATH = "dependency_down_degradation"

#: The four auth-shaped paths, declared only when the fix task evidences an
#: auth surface.
_AUTH_NEGATIVE_PATHS: Tuple[str, ...] = (
    "wrong_credential",
    "anonymous_deep_link",
    "post_logout_401",
    "unauthorized_403_ui",
)


class PassBarDerivationError(Exception):
    """A fix task could not be derived into a schema-valid pass bar.

    Raised loudly by :func:`derive_pass_bar` and converted by
    :func:`mint_pass_bars` into a recorded, stderr-echoed producer error with
    **no file on disk**.
    """


@dataclass
class MintedPassBar:
    """One bar's outcome — receipt row for the leg's ``pass_bars`` key."""

    fix_task_id: str
    fix_task_path: str
    status: str  # "written" | "exists" | "error"
    pass_bar_path: Optional[str] = None
    provenance: str = "machine-derived"
    detail: Optional[str] = None

    def as_receipt_entry(self) -> Dict[str, Any]:
        entry: Dict[str, Any] = {
            "fix_task_id": self.fix_task_id,
            "fix_task_path": self.fix_task_path,
            "status": self.status,
            "provenance": self.provenance,
        }
        if self.pass_bar_path:
            entry["pass_bar_path"] = self.pass_bar_path
        if self.detail:
            entry["detail"] = self.detail
        return entry


@dataclass
class MintReport:
    """What the minting pass did — the whole ``pass_bars`` receipt block."""

    enforcement: str  # "armed" | "off"
    bars: List[MintedPassBar] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def written_paths(self) -> List[str]:
        return [b.pass_bar_path for b in self.bars if b.status == "written" and b.pass_bar_path]

    def as_receipt_block(self) -> Dict[str, Any]:
        block: Dict[str, Any] = {
            "enforcement": self.enforcement,
            "provenance": PASS_BAR_PROVENANCE_NOTE,
            "bars": [b.as_receipt_entry() for b in self.bars],
        }
        if self.error:
            block["error"] = self.error
        return block


# ---------------------------------------------------------------------------
# Reading the fix task
# ---------------------------------------------------------------------------


def _section_lines(text: str, heading: str) -> List[str]:
    """Return the body lines of the ``## <heading>`` section (case-folded match)."""
    wanted = heading.strip().lower()
    out: List[str] = []
    inside = False
    for line in text.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            if inside:
                break
            inside = match.group("title").strip().lower() == wanted
            continue
        if inside:
            out.append(line)
    return out


def read_acceptance_criteria(fix_task_text: str) -> List[str]:
    """Extract the ``## Acceptance Criteria`` checkbox items, in order.

    The producer writes them at ``installer/core/lib/implement_orchestrator.py:
    267-281`` (four base items, plus the two ``AC-ANTISTUB-*`` items for
    feature/refactor/integration task types).
    """
    items: List[str] = []
    for line in _section_lines(fix_task_text, "Acceptance Criteria"):
        match = _CRITERION_RE.match(line)
        if match:
            items.append(match.group("text"))
    return items


def _frontmatter_value(fix_task_text: str, key: str) -> Optional[str]:
    """Read one scalar out of the fix task's YAML frontmatter, tolerantly.

    Deliberately a line scan rather than a YAML parse: this runs on files a
    model's prose fed into, and a frontmatter that does not parse must not take
    the mint down — the value is provenance decoration, not a gate.
    """
    lines = fix_task_text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        name, _, value = line.partition(":")
        if name.strip() == key:
            cleaned = value.strip().strip('"').strip("'")
            return cleaned or None
    return None


def _criterion_id(raw: str, ordinal: int, used: set) -> Tuple[str, str]:
    """Split ``AC-X: text`` into (id, text); otherwise mint ``AC-<n>``."""
    match = _CRITERION_ID_RE.match(raw)
    if match:
        candidate, text = match.group("id"), match.group("text")
    else:
        candidate, text = f"AC-{ordinal}", raw
    unique = candidate
    suffix = 2
    while unique in used:
        unique = f"{candidate}-{suffix}"
        suffix += 1
    used.add(unique)
    return unique, text


def _auth_surface_basis(fix_task_text: str) -> Tuple[bool, str]:
    """Judge ``auth_surface_bearing`` from the fix task, and say why.

    Returns ``(bearing, basis_sentence)``. The sentence goes into the
    provenance block verbatim — PB-14's whole point is that this flag is
    *declared*, never guessed in silence.
    """
    lowered = fix_task_text.lower()
    hits = sorted(set(_AUTH_TOKEN_RE.findall(lowered)))
    if hits:
        return True, (
            "true — the fix task's own text/files name auth-surface token(s) "
            f"{hits}; all five negative paths are declared (PB-14)."
        )
    return False, (
        "false — no auth-surface token matched the fix task's text/files, so "
        "only the universal negative path is declared (PB-14: an authless fix "
        "must not fabricate four auth paths it has no surface for). If this fix "
        "does touch an auth surface, widen the bar by hand."
    )


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------


def _pass_bar_format_version() -> str:
    try:
        from guardkit.qa.formats import PassBar  # noqa: PLC0415

        return str(PassBar.CURRENT_FORMAT_VERSION)
    except Exception:  # pragma: no cover — defensive
        return _PASS_BAR_FORMAT_VERSION_FALLBACK


def derive_pass_bar(
    *,
    fix_task_path: Path,
    task_id: str,
    registered_sha: str,
    registered_date: Optional[str] = None,
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """Derive a schema-valid pass-bar mapping from one fix-task file.

    ``task_id`` is the file **stem** — the id the pipeline extracts from the
    printed artefact line and hands to the work leg as ``--task-id``, and
    therefore the id ``check_pass_bar_precondition`` looks the bar up by
    (``qa/pass-bar-<stem>.yaml``) *and* matches against the bar's own
    ``task_id`` field.

    Returns ``(mapping, provenance_facts)``. Raises
    :class:`PassBarDerivationError` when the fix task carries nothing a bar can
    be built from — the caller turns that into a loud error and writes NOTHING.
    """
    try:
        text = fix_task_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        raise PassBarDerivationError(
            f"cannot read fix task {fix_task_path}: {exc}"
        ) from exc

    raw_criteria = read_acceptance_criteria(text)
    if not raw_criteria:
        raise PassBarDerivationError(
            f"{fix_task_path.name} has no usable '## Acceptance Criteria' items — "
            f"a pass bar with no criteria cannot be derived (PassBar.criteria "
            f"requires at least one). Refusing to write a bar; the work leg's "
            f"qa.enforce_tier1 precondition will name the missing bar loudly "
            f"rather than start against a fabricated one."
        )

    used: set = set()
    criteria: List[Dict[str, str]] = []
    for ordinal, raw in enumerate(raw_criteria, start=1):
        cid, ctext = _criterion_id(raw, ordinal, used)
        criteria.append(
            {
                "id": cid,
                "text": ctext,
                # The YAML key is `class:` (PassBarCriterion's alias). Written
                # in the alias form so the bytes validated below are the bytes
                # that land on disk.
                "class": "machine",
                "evidence_kind": _DERIVED_EVIDENCE_KIND,
            }
        )

    auth_bearing, auth_basis = _auth_surface_basis(text)
    negative_paths = [_UNIVERSAL_NEGATIVE_PATH]
    if auth_bearing:
        negative_paths = list(_AUTH_NEGATIVE_PATHS) + [_UNIVERSAL_NEGATIVE_PATH]

    mapping: Dict[str, Any] = {
        "format_version": _pass_bar_format_version(),
        "task_id": task_id,
        "registered_at": {
            "sha": registered_sha,
            "date": registered_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        },
        "auth_surface_bearing": auth_bearing,
        "preconditions": list(_DERIVED_PRECONDITIONS),
        "criteria": criteria,
        "negative_paths": negative_paths,
    }

    facts = {
        "parent_review": _frontmatter_value(text, "parent_review") or "",
        "auth_basis": auth_basis,
        "criteria_count": str(len(criteria)),
    }
    return mapping, facts


def _validate_mapping(mapping: Dict[str, Any], fix_task_path: Path) -> None:
    """Put the derived mapping through the REAL ``PassBar`` model.

    Same call ``guardkit.qa.formats.base.validate_file`` makes — so a mapping
    that survives here is a mapping the task-start checker will accept.
    """
    from guardkit.qa.formats import PassBar  # noqa: PLC0415

    try:
        PassBar.model_validate(mapping)
    except Exception as exc:  # pydantic formats itself well
        raise PassBarDerivationError(
            f"derived pass bar for {fix_task_path.name} is NOT a valid "
            f"pass-bar instance: {exc}"
        ) from exc


def render_pass_bar_text(
    mapping: Dict[str, Any],
    *,
    fix_task_path: Path,
    parent_review_id: str,
    facts: Dict[str, str],
) -> str:
    """Serialise the bar with its leading machine-derived provenance block.

    ``PassBar`` is ``extra="forbid"``: there is no field to carry provenance,
    so the schema's own admitted form is a YAML comment — invisible to the
    validator, unmissable to a reader, and stable enough for a test to key on
    :data:`PASS_BAR_PROVENANCE_MARKER`.
    """
    import yaml  # noqa: PLC0415

    rule = "# " + "-" * 74
    parent = facts.get("parent_review") or parent_review_id or "(unknown)"
    header = [
        rule,
        f"# {PASS_BAR_PROVENANCE_MARKER} — not human-authored.",
        "#",
        "# Minted by:     the review leg (guardkit task-review),",
        "#                guardkit/orchestrator/pass_bar_mint.py",
        f"# Parent review: {parent}",
        f"# Fix task:      {fix_task_path.name}",
        "# Derived from:  that fix task's '## Acceptance Criteria' section, at the",
        "#                moment the fix task was written — so this bar exists",
        "#                BEFORE any work leg runs (qa.enforce_tier1's",
        "#                bar-before-implementation law, held mechanically).",
        "#",
        "# Judgements this derivation had to make, stated so they can be corrected:",
        f"#  - auth_surface_bearing: {facts.get('auth_basis', '(not recorded)')}",
        "#  - every criterion is classed `machine`: a machine derivation has no",
        "#    operator runbook to route an operator criterion to (F1/ST-12), and a",
        "#    criterion with nowhere to route is a silently-dropped criterion.",
        f"#  - evidence_kind `{_DERIVED_EVIDENCE_KIND}`: what a checker loop actually",
        "#    produces for a fix task. The two live kinds (screenshot,",
        "#    operator_signoff) would make every derived bar runtime-surface-bearing",
        "#    at feature-complete — a fabricated gate.",
        f"#  - preconditions {list(_DERIVED_PRECONDITIONS)}: analyze_clean /",
        "#    build_artifact are repo-shaped claims a fix-task file cannot evidence.",
        "#",
        "# This is a MINIMAL bar. Widening it — operator criteria, live evidence,",
        "# extra negative paths — is a human/Coach act, not this minter's.",
        rule,
    ]
    body = yaml.safe_dump(mapping, sort_keys=False, default_flow_style=False, allow_unicode=True)
    return "\n".join(header) + "\n" + body


def _round_trip_check(text: str, fix_task_path: Path) -> None:
    """Validate the SERIALISED bytes, before any of them reach disk.

    ``PassBar.model_validate`` on the mapping proves the derivation; this proves
    the *file* — the same two steps ``validate_file`` performs (``yaml.safe_load``
    then ``model_validate``), just without a malformed file ever existing.
    """
    import yaml  # noqa: PLC0415

    from guardkit.qa.formats import PassBar  # noqa: PLC0415

    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise PassBarDerivationError(
            f"derived pass bar for {fix_task_path.name} does not serialise to "
            f"valid YAML: {exc}"
        ) from exc
    if not isinstance(loaded, dict):
        raise PassBarDerivationError(
            f"derived pass bar for {fix_task_path.name} did not serialise to a "
            f"mapping (got {type(loaded).__name__})"
        )
    try:
        PassBar.model_validate(loaded)
    except Exception as exc:
        raise PassBarDerivationError(
            f"derived pass bar for {fix_task_path.name} does not survive its own "
            f"YAML round-trip: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# The mint
# ---------------------------------------------------------------------------


def head_sha(repo_root: Path) -> Optional[str]:
    """``git rev-parse HEAD`` for ``repo_root``; ``None`` when unavailable.

    The commit the bar pins as ``registered_at.sha`` is the tree's HEAD at
    *production* time — which is, by construction, an ancestor of whatever HEAD
    the work leg later runs against, which is exactly what
    ``check_pass_bar_precondition``'s ``merge-base --is-ancestor`` proves.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning("pass-bar mint: git unavailable in %s (%s)", repo_root, exc)
        return None
    if proc.returncode != 0:
        return None
    sha = proc.stdout.strip()
    return sha or None


def pass_bar_path_for_fix_task(repo_root: Path, task_id: str) -> Path:
    """The canonical bar path — resolved through the ENFORCER's own function.

    Never re-spelled here: one rule mints the claim and the thing claimed, so
    the minter and the checker read the same path function
    (``guardkit/qa/enforcement.py:150``).
    """
    from guardkit.qa.enforcement import pass_bar_path_for  # noqa: PLC0415

    return pass_bar_path_for(repo_root, task_id)


def _loud(message: str) -> None:
    """A producer error the operator must see, on stderr and in the log.

    The leg's stdout is the pipeline's control surface, so stderr is the only
    honest channel (the producer's own narration is redirected the same way).
    """
    logger.warning("%s", message)
    try:
        print(f"pass-bar mint: {message}", file=sys.stderr)
    except Exception:  # pragma: no cover — defensive
        pass


def mint_pass_bars(
    fix_task_paths: Sequence[Path],
    *,
    repo_root: Path,
    parent_review_id: str,
    enforced: Optional[bool] = None,
) -> MintReport:
    """Mint one machine-derived F1 pass bar per fix task. Never raises.

    When ``qa.enforce_tier1`` is not armed for ``repo_root``, **nothing is
    written** and the report says so (``enforcement: "off"``). The flag is read
    through :func:`guardkit.qa.enforcement.is_tier1_enforced` — the one reader,
    honoured verbatim, env override included.

    An existing bar is never overwritten: a human/Coach bar outranks a derived
    one, and clobbering it would silently narrow a widened bar.
    """
    if enforced is None:
        try:
            from guardkit.qa.enforcement import is_tier1_enforced  # noqa: PLC0415

            enforced = bool(is_tier1_enforced(repo_root))
        except Exception as exc:  # noqa: BLE001 — never fail a leg on the mint
            _loud(f"could not read qa.enforce_tier1 for {repo_root}: {exc}")
            return MintReport(enforcement="unknown", error=f"{type(exc).__name__}: {exc}")

    if not enforced:
        return MintReport(enforcement="off")

    report = MintReport(enforcement="armed")
    if not fix_task_paths:
        return report

    sha = head_sha(repo_root)
    if not sha:
        message = (
            f"qa.enforce_tier1 is armed for {repo_root} but HEAD could not be "
            f"resolved, so no bar can pin a registered_at.sha that predates "
            f"implementation — minting NOTHING for "
            f"{len(fix_task_paths)} fix task(s). The work leg will refuse and "
            f"name the missing bar."
        )
        _loud(message)
        report.error = message
        for path in fix_task_paths:
            report.bars.append(
                MintedPassBar(
                    fix_task_id=path.stem,
                    fix_task_path=str(path),
                    status="error",
                    detail="no resolvable HEAD sha for registered_at",
                )
            )
        return report

    for fix_task_path in fix_task_paths:
        task_id = fix_task_path.stem
        bar_path = pass_bar_path_for_fix_task(repo_root, task_id)
        if bar_path.exists():
            report.bars.append(
                MintedPassBar(
                    fix_task_id=task_id,
                    fix_task_path=str(fix_task_path),
                    status="exists",
                    pass_bar_path=str(bar_path),
                    provenance="pre-existing — left untouched",
                    detail=(
                        "a bar already exists at this path; a human/Coach bar "
                        "outranks a derived one and is never overwritten"
                    ),
                )
            )
            continue

        try:
            mapping, facts = derive_pass_bar(
                fix_task_path=fix_task_path, task_id=task_id, registered_sha=sha
            )
            _validate_mapping(mapping, fix_task_path)
            text = render_pass_bar_text(
                mapping,
                fix_task_path=fix_task_path,
                parent_review_id=parent_review_id,
                facts=facts,
            )
            _round_trip_check(text, fix_task_path)
        except PassBarDerivationError as exc:
            _loud(str(exc))
            report.bars.append(
                MintedPassBar(
                    fix_task_id=task_id,
                    fix_task_path=str(fix_task_path),
                    status="error",
                    detail=str(exc),
                )
            )
            continue

        try:
            bar_path.parent.mkdir(parents=True, exist_ok=True)
            bar_path.write_text(text, encoding="utf-8")
        except OSError as exc:
            message = f"could not write {bar_path}: {exc}"
            _loud(message)
            report.bars.append(
                MintedPassBar(
                    fix_task_id=task_id,
                    fix_task_path=str(fix_task_path),
                    status="error",
                    detail=message,
                )
            )
            continue

        report.bars.append(
            MintedPassBar(
                fix_task_id=task_id,
                fix_task_path=str(fix_task_path),
                status="written",
                pass_bar_path=str(bar_path),
            )
        )

    return report


__all__ = [
    "PASS_BAR_PROVENANCE_MARKER",
    "PASS_BAR_PROVENANCE_NOTE",
    "MintReport",
    "MintedPassBar",
    "PassBarDerivationError",
    "derive_pass_bar",
    "head_sha",
    "mint_pass_bars",
    "pass_bar_path_for_fix_task",
    "read_acceptance_criteria",
    "render_pass_bar_text",
]
