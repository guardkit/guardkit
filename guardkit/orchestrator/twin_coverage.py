"""Build-completion check: every scenario stamped ``verifier: hurl`` must
have a twin file.

WHY THIS EXISTS (the FEAT-0E07 hole, 2026-08-26)
------------------------------------------------
Two sibling api_test builds proved the gap. Both plans stamped their
scenarios ``verifier: hurl`` in ``.guardkit/features/FEAT-*.yaml``. The
FEAT-B8E3 build wrote its twin at
``qa/twins/user-deletion/user-deletion-acceptance.hurl``; the FEAT-0E07
build shipped ZERO ``.hurl`` files and still completed 5/5 — nothing
between plan approval and build completion checked that the promised twin
artifacts actually exist. A stamp is a routing promise ("this scenario is
proven over the wire by a frozen Hurl twin"); a build that ends with the
promise and no artifact is an unverified green.

THE MAPPING RULE THIS CHECK IMPLEMENTS (derived from the estate, not guessed)
-----------------------------------------------------------------------------
A scenario stamped ``verifier: hurl`` counts as covered when EITHER door
matches, checked in this order:

1. **Named file** — the stamp carries ``test_ref: <path>.hurl`` and that
   repo-relative file exists in the built tree. This is the explicit
   convention already present in api_test (e.g. FEAT-TIME:
   ``test_ref: qa/twins/time-endpoint/reading-current-server-time.hurl``;
   FEAT-UDBE names its twins the same way). ``verifier_stamp.py`` declared
   this reference "not consumed in this wave — a future home may claim it
   (e.g. a hurl stamp naming its twin)"; this check is that claim.

2. **Scenario title carried in a twin's comments** — some ``.hurl`` file
   under ``qa/twins/`` has a comment line (a line starting ``#``) reading
   ``Scenario: <the stamped title>``. Every twin layout observed in
   api_test carries this: per-scenario twins embed the verbatim approved
   Gherkin (``# Scenario: <title>`` header and ``#   Scenario: <title>``
   inside the quoted feature text), the FEAT-B8E3 multi-scenario
   acceptance file lists each scenario as ``# Gherkin:`` /
   ``#   Scenario: <title>``, and the ``gherkin_to_hurl.py`` compiler
   emits ``# --- Scenario: <title> ---`` per block. The title must match
   exactly; trailing decoration is tolerated only when set off by
   whitespace and starting ``(`` (approval annotations like
   ``(APPROVED AS PROPOSED by Rich 2026-07-31)``), ``-`` (the compiler's
   ``---`` rule-off) or ``=``. A longer title never satisfies a shorter
   stamp (prefix collisions are refused).

Directory and file NAMES are deliberately NOT part of the rule: observed
names do not mechanically derive from titles
(``qa/twins/users-delete-by-email/delete-existing-user.hurl`` twins the
scenario "An existing user is deleted by their email"), so any name-based
rule would be a guess.

ADVISORY FIRST (house practice — the boot-smoke / zero-test-gate posture)
-------------------------------------------------------------------------
By default the check writes a plain receipt
(``.guardkit/autobuild-private/twin_coverage.json`` in the build's
worktree, one entry per stamped scenario, found or missing) and a WARNING
in the build report, and changes nothing else. One config key flips it to
build-failing::

    # <repo>/.guardkit/config.yaml
    qa:
      enforce_twin_coverage: true

Environment override ``GUARDKIT_QA_ENFORCE_TWIN_COVERAGE`` (truthy/falsy)
wins over the file, mirroring ``qa.enforce_tier1``. The flag is read from
the MAIN checkout's config, never the build worktree's copy, so a build
cannot switch its own gate off mid-run (the toolchain-declaration
snapshot precedent).

The check runs once, after the final task, and only for a build that
finished clean — a build that already failed has its own answer, and
piling a twin-coverage warning onto it would only add noise (the
boot-smoke skip posture).
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)

#: Env override for the enforcement flag. Truthy wins ON, falsy wins OFF,
#: anything else is ignored with a warning (the ``qa.enforce_tier1`` sets).
ENFORCE_ENV = "GUARDKIT_QA_ENFORCE_TWIN_COVERAGE"

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_FALSY = frozenset({"0", "false", "no", "off", ""})

#: Where twins live, relative to the built tree (the layout of record —
#: api_test's hurl-twin pilot, ruled 2026-08-14).
TWINS_RELATIVE_DIR = Path("qa") / "twins"

#: Where the receipt lands, relative to the built tree. autobuild-private is
#: the orchestrator's own receipt home (coach verdicts live there too) and is
#: excluded from build checkpoints.
RECEIPT_RELATIVE_PATH = (
    Path(".guardkit") / "autobuild-private" / "twin_coverage.json"
)

# A twin's comment lines carry the scenario title after a Gherkin scenario
# keyword. Longest keyword first so "Scenario Outline:" never half-matches
# as "Scenario:".
_TWIN_TITLE_RE = re.compile(
    r"(?:Scenario Outline|Scenario Template|Scenario|Example)\s*:\s*(?P<rest>\S.*?)\s*$"
)


@dataclass(frozen=True)
class ScenarioTwinStatus:
    """One stamped scenario's answer: found (and how) or missing."""

    scenario: str
    found: bool
    #: Repo-relative path of the matching twin file, when found.
    twin: Optional[str] = None
    #: "named file" (the stamp's test_ref exists) or "scenario title"
    #: (a twin's comments carry the title). None when missing.
    matched_by: Optional[str] = None


@dataclass(frozen=True)
class TwinCoverageReport:
    """The whole check's outcome for one feature."""

    feature_id: str
    enforced: bool
    #: How many .hurl files were scanned under qa/twins/.
    twins_scanned: int
    statuses: Tuple[ScenarioTwinStatus, ...]

    @property
    def missing(self) -> List[str]:
        """The stamped scenarios with no twin, by name."""
        return [s.scenario for s in self.statuses if not s.found]

    @property
    def checked(self) -> int:
        """How many scenarios were stamped ``verifier: hurl``."""
        return len(self.statuses)

    @property
    def blocks_build(self) -> bool:
        """True only when enforcement is on AND at least one twin is missing."""
        return self.enforced and bool(self.missing)


def is_twin_coverage_enforced(repo_root: Path) -> bool:
    """Whether missing twins fail the build for ``repo_root``.

    Precedence: ``GUARDKIT_QA_ENFORCE_TWIN_COVERAGE`` env (truthy/falsy) >
    ``.guardkit/config.yaml`` ``qa.enforce_twin_coverage`` > ``False``
    (advisory). Default off everywhere — a repo opts in explicitly.
    """
    env = os.environ.get(ENFORCE_ENV)
    if env is not None:
        token = env.strip().lower()
        if token in _TRUTHY:
            return True
        if token in _FALSY:
            return False
        logger.warning(
            "%s=%r is not a recognised boolean — treating as advisory",
            ENFORCE_ENV,
            env,
        )
        return False
    config_path = Path(repo_root) / ".guardkit" / "config.yaml"
    if not config_path.is_file():
        return False
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, OSError) as exc:
        logger.warning(
            "twin coverage: could not read %s (%s) — treating as advisory",
            config_path,
            exc,
        )
        return False
    if not isinstance(data, dict):
        return False
    qa = data.get("qa")
    if not isinstance(qa, dict):
        return False
    return bool(qa.get("enforce_twin_coverage", False))


def _stamp_field(stamp: Any, name: str) -> Any:
    """Read a field off a ScenarioStamp object or a plain mapping."""
    if isinstance(stamp, dict):
        return stamp.get(name)
    return getattr(stamp, name, None)


def _extract_twin_titles(text: str) -> List[str]:
    """Title candidates from one twin file's COMMENT lines only.

    Only lines starting ``#`` are read — a scenario title quoted inside a
    request body is not a claim of coverage.
    """
    candidates: List[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith("#"):
            continue
        m = _TWIN_TITLE_RE.search(stripped)
        if m:
            candidates.append(m.group("rest"))
    return candidates


def _candidate_matches_title(candidate: str, title: str) -> bool:
    """Exact title match, tolerating only set-off trailing decoration.

    ``<title>`` alone matches. ``<title> (APPROVED ...)`` and
    ``<title> ---`` match (whitespace then ``(`` / ``-`` / ``=``).
    ``<title>ish`` and ``<title> quickly`` never match — a longer scenario
    title must not satisfy a shorter stamp.
    """
    if candidate == title:
        return True
    if candidate.startswith(title):
        rest = candidate[len(title):]
        if rest[:1] in (" ", "\t"):
            return rest.strip().startswith(("(", "-", "="))
    return False


def check_twin_coverage(
    feature_id: str,
    scenarios: Dict[str, Any],
    root: Path,
    *,
    enforced: bool,
) -> TwinCoverageReport:
    """Check every ``verifier: hurl`` stamp in ``scenarios`` against ``root``.

    Parameters
    ----------
    feature_id : str
        The feature being built (for the receipt).
    scenarios : Dict[str, Any]
        The feature YAML's per-scenario stamp map (title -> ScenarioStamp
        or plain mapping). Non-hurl stamps are ignored.
    root : Path
        The built tree to scan (the build worktree).
    enforced : bool
        Whether a miss should fail the build (resolve it with
        :func:`is_twin_coverage_enforced` against the MAIN checkout).
    """
    root = Path(root)
    twins_dir = root / TWINS_RELATIVE_DIR

    # Scan qa/twins/ once: path -> the titles its comments claim.
    twin_titles: List[Tuple[str, List[str]]] = []
    if twins_dir.is_dir():
        for path in sorted(twins_dir.rglob("*.hurl")):
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError as exc:
                logger.warning("twin coverage: could not read %s: %s", path, exc)
                continue
            twin_titles.append(
                (str(path.relative_to(root)), _extract_twin_titles(text))
            )

    statuses: List[ScenarioTwinStatus] = []
    for title, stamp in scenarios.items():
        if _stamp_field(stamp, "verifier") != "hurl":
            continue

        # Door 1: the stamp names its twin outright.
        test_ref = _stamp_field(stamp, "test_ref")
        if (
            isinstance(test_ref, str)
            and test_ref.strip().endswith(".hurl")
            and (root / test_ref.strip()).is_file()
        ):
            statuses.append(
                ScenarioTwinStatus(
                    scenario=title,
                    found=True,
                    twin=test_ref.strip(),
                    matched_by="named file",
                )
            )
            continue

        # Door 2: some twin's comments carry the scenario title.
        matched: Optional[str] = None
        for rel_path, candidates in twin_titles:
            if any(_candidate_matches_title(c, title) for c in candidates):
                matched = rel_path
                break
        if matched is not None:
            statuses.append(
                ScenarioTwinStatus(
                    scenario=title,
                    found=True,
                    twin=matched,
                    matched_by="scenario title",
                )
            )
        else:
            statuses.append(ScenarioTwinStatus(scenario=title, found=False))

    return TwinCoverageReport(
        feature_id=feature_id,
        enforced=enforced,
        twins_scanned=len(twin_titles),
        statuses=tuple(statuses),
    )


def write_twin_coverage_receipt(report: TwinCoverageReport, root: Path) -> Path:
    """Write the plain receipt into the built tree; return its path."""
    receipt_path = Path(root) / RECEIPT_RELATIVE_PATH
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "feature": report.feature_id,
        "what": (
            "One entry per scenario this feature's plan marked for a Hurl "
            "twin (verifier: hurl in the feature YAML): whether a twin file "
            "exists in the built tree, and which file matched. A scenario "
            "counts as covered when its stamp names an existing .hurl file "
            "(test_ref), or when a .hurl file under qa/twins/ carries the "
            "scenario title in its comments."
        ),
        "generated_at": datetime.now().isoformat(),
        "enforcement": "on" if report.enforced else "off (advisory)",
        "twin_files_scanned": report.twins_scanned,
        "scenarios": [
            {
                "scenario": s.scenario,
                "twin_found": s.found,
                "twin_file": s.twin,
                "matched_by": s.matched_by,
            }
            for s in report.statuses
        ],
        "missing": report.missing,
    }
    receipt_path.write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )
    return receipt_path


def render_twin_coverage_lines(
    report: TwinCoverageReport, receipt_path: Optional[Path] = None
) -> List[str]:
    """Plain-English report lines for the build summary.

    Empty when nothing was stamped ``verifier: hurl`` — a feature with no
    hurl scenarios gets no twin-coverage noise at all.
    """
    if not report.statuses:
        return []
    lines: List[str] = []
    missing = report.missing
    if not missing:
        lines.append(
            f"Twin coverage: all {report.checked} scenario(s) marked for a "
            "Hurl twin have a twin file."
        )
    else:
        lines.append(
            f"WARNING: this feature's plan marks {report.checked} "
            f"scenario(s) for a Hurl twin, but {len(missing)} of them have "
            f"no twin file under {TWINS_RELATIVE_DIR}/:"
        )
        for name in missing:
            lines.append(f"  - {name}")
        if report.enforced:
            lines.append(
                "Twin coverage enforcement is on for this repo "
                "(qa.enforce_twin_coverage), so this build is marked failed."
            )
        else:
            lines.append(
                "This is advisory: the build is NOT failed by it. To make a "
                "missing twin fail the build, set qa.enforce_twin_coverage: "
                "true in .guardkit/config.yaml."
            )
    if receipt_path is not None:
        lines.append(f"Twin coverage receipt: {receipt_path}")
    return lines


__all__ = [
    "ENFORCE_ENV",
    "TWINS_RELATIVE_DIR",
    "RECEIPT_RELATIVE_PATH",
    "ScenarioTwinStatus",
    "TwinCoverageReport",
    "is_twin_coverage_enforced",
    "check_twin_coverage",
    "write_twin_coverage_receipt",
    "render_twin_coverage_lines",
]
