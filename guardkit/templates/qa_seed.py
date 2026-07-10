"""PB-6 · the additive qa-seed harvest phase.

Sibling of :mod:`guardkit.templates.qa_scaffold`. Where ``qa_scaffold`` copies
generic stubs at ``guardkit init`` time, ``qa_seed`` emits **verification seeds**
at ``/template-create`` harvest time. It turns two facts the harvest already has
— the source repo's observable suite outcome, and its ``settings.json``
``layer_mappings`` — into tier-1 QA data:

- **E1 · F2 known-failures.yaml INSTANCE into the SOURCE repo.**
  ``expected.passed`` equals the suite count *actually observed* by running the
  source suite once; ``framework`` / ``language`` come from Phase-1 detection;
  ``owner`` + ``review_by`` are populated (what keeps a red baseline from being
  enshrined). Validates as-is, so the first autobuild suite gate diffs against a
  ledger instead of asserting "all green".
- **E2 · stack-typed qa/ STUBS into the generated TEMPLATE dir.** Placeholder
  content carrying the correct ``framework`` / ``language`` for the harvested
  stack — validate-as-is, never the source repo's instance data.
- **E3 · F3 leak-sweep.yaml deny_patterns into the SOURCE repo**, seeded from the
  source repo's REAL mock identities. Harvest fills the "strings that must never
  appear inside a claimed-real scope" data; it claims **no** surface as real
  (that is ``/feature-plan``'s exclusive step).
- **E4 · one F12 discovery-gate STUB per ``layer_mapping``.** A pre-registered
  gate scaffold for the planner to fill.

Writer-restriction discipline (scope §3): harvest records **observed truth about
the source repo** as an instance (E1 F2 baseline, E3 real mock strings). Anything
that is a **claim about a future build** (F1 bars, F3 claimed-real surfaces, F12
verified claims) is emitted only as a **stub** for the named writer to fill.
Harvest is a one-time, human-initiated authoring at template-create time — it is
NOT the Player mid-build and NOT a headless ``/feature-plan`` session, so
K15/LPA-09 and the DIM5-F3 plan-time reject-lint remain the sole authority over
who authors ledger entries at build time.

Every write is **per-file-if-absent** (K5 / DF-007): a repo's committed ``qa/``
truth always wins; harvest never clobbers. A payload the seed step cannot emit is
surfaced at WARNING with a named remediation (DF-011), never a silent skip.

No ``guardkit/qa/formats/*`` schema is touched — this is emitter/generator work.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

# How far out a fresh F2 ledger entry's review_by lands by default (a ledger
# entry is temporary by intent — review_by keeps it from rotting).
_REVIEW_BY_DAYS = 90

# Populated owner for a harvested F2 baseline. min_length=1 is all the schema
# requires; the value names who must reassign it at triage.
_HARVEST_OWNER = "template-create (reassign at triage)"

# The subprocess runner signature: (argv, cwd) -> (returncode, combined_output).
# Injectable so tests drive a synthetic suite result without shelling out.
SuiteRunner = Callable[[List[str], Path], Tuple[int, str]]

# ---------------------------------------------------------------------------
# Suite observation (E1) — pytest is adapter #1 (F2 docstring / stack-plugin
# architecture: execution is the one irreducibly stack-specific step).
# ---------------------------------------------------------------------------

_PYTEST_FRAMEWORKS = frozenset({"pytest", "pytest-bdd", "pytest_bdd"})

_PASSED_RE = re.compile(r"(\d+)\s+passed")
_FAILED_RE = re.compile(r"(\d+)\s+failed")
_ERROR_RE = re.compile(r"(\d+)\s+error(?:s|ed)?")
# pytest short-summary lines: "FAILED path::test - reason" / "ERROR path::test".
_FAIL_LINE_RE = re.compile(r"^(?:FAILED|ERROR)\s+(\S+)", re.MULTILINE)


@dataclass
class SuiteObservation:
    """The result of running the source suite once during harvest.

    ``ran`` distinguishes an *observed* outcome from an *absent* one: a suite
    that could not be run (unsupported framework, runner error, timeout) yields
    ``ran=False`` and NEVER a fabricated green baseline — the absence-of-failure
    discipline applied to harvest.
    """

    ran: bool
    passed: int = 0
    failed: int = 0
    failure_ids: List[str] = field(default_factory=list)
    detail: str = ""


def _default_suite_runner(argv: List[str], cwd: Path) -> Tuple[int, str]:
    proc = subprocess.run(
        argv,
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=_DEFAULT_OBSERVE_TIMEOUT,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


_DEFAULT_OBSERVE_TIMEOUT = 600


def observe_suite(
    source_repo: Path,
    test_framework: str,
    *,
    runner: Optional[SuiteRunner] = None,
) -> SuiteObservation:
    """Run the source suite once and parse its observed outcome (best-effort).

    Only pytest is auto-observed today (adapter #1); any other framework returns
    ``ran=False`` with a remediation detail so E1 is skipped-with-WARNING rather
    than fabricated.
    """
    fw = (test_framework or "").strip().lower()
    if fw not in _PYTEST_FRAMEWORKS:
        return SuiteObservation(
            ran=False,
            detail=(
                f"auto-observation not supported for framework {test_framework!r} "
                f"(pytest is adapter #1); add qa/known-failures.yaml manually with "
                f"this suite's observed 'expected.passed' before enabling "
                f"qa.enforce_tier1."
            ),
        )

    argv = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--no-header",
        "-rfE",
        "-p",
        "no:cacheprovider",
    ]
    run = runner or _default_suite_runner
    try:
        _rc, out = run(argv, source_repo)
    except subprocess.TimeoutExpired:
        return SuiteObservation(
            ran=False,
            detail="suite observation timed out; add qa/known-failures.yaml manually.",
        )
    except Exception as exc:  # pragma: no cover - defensive; never break harvest
        return SuiteObservation(
            ran=False,
            detail=f"suite observation failed to launch ({exc}); add the ledger manually.",
        )

    passed_m = _PASSED_RE.search(out)
    failed_m = _FAILED_RE.search(out)
    error_m = _ERROR_RE.search(out)
    if passed_m is None and failed_m is None and error_m is None:
        return SuiteObservation(
            ran=False,
            detail=(
                "suite ran but produced no parseable pytest summary "
                "(no 'N passed'/'M failed'); add qa/known-failures.yaml manually."
            ),
        )

    passed = int(passed_m.group(1)) if passed_m else 0
    failed = (int(failed_m.group(1)) if failed_m else 0) + (
        int(error_m.group(1)) if error_m else 0
    )
    failure_ids = _FAIL_LINE_RE.findall(out)
    return SuiteObservation(ran=True, passed=passed, failed=failed, failure_ids=failure_ids)


# ---------------------------------------------------------------------------
# Mock-identity detection (E3) — the F3 deny_patterns seed lineage: the
# MOCK_NAMES deny-list class gate_phase6_sweep.py hard-coded, gathered as data.
# ---------------------------------------------------------------------------

# Files worth scanning for a repo's real mock identities: test / fixture / mock
# code. Kept stack-agnostic (any extension) but path-scoped so production code
# is not swept for its ordinary string literals.
_MOCK_PATH_SIGNAL = re.compile(r"(?:^|[/\\])(?:tests?|fixtures?|mocks?|__mocks__|conftest|spec)", re.IGNORECASE)
_MOCK_FILE_SUFFIX = re.compile(r"(?:test|spec|mock|fixture|conftest)", re.IGNORECASE)

# A quoted string literal (single or double, no interpolation handling — good
# enough for identity constants).
_STRING_LITERAL_RE = re.compile(r"""(['"])(.*?)\1""")
# Context words that mark a line as a mock/fake identity assignment.
_MOCK_CONTEXT_RE = re.compile(r"\b(?:mock|fake|dummy|stub|fixture|test[_-]?user|sample)\b", re.IGNORECASE)
# Identifier names that hold an identity value.
_IDENTITY_VAR_RE = re.compile(
    r"\b\w*(?:name|user|email|identity|author|owner|persona|login)\w*\b\s*[:=]", re.IGNORECASE
)
# A URL / test-host literal.
_URL_RE = re.compile(
    r"""(?:https?://[^\s'"]+|(?:^|[\s'"])(?:example\.(?:com|org|net)|test\.\w+|localhost|127\.0\.0\.1)[^\s'"]*)""",
    re.IGNORECASE,
)
# A human-name-shaped literal ("Test User", "Jane Q. Doe").
_NAME_SHAPE_RE = re.compile(r"^[A-Z][a-z]+(?:[.\s]+[A-Z][a-z.]+){1,3}$")

# Bound the deny lists so a large repo cannot bloat the manifest.
_MAX_DENY_PER_CLASS = 40
# Bound the file scan so harvest stays fast on a large repo.
_MAX_SCAN_FILES = 600
_MAX_FILE_BYTES = 200_000


@dataclass
class MockIdentities:
    """The F3 deny_patterns harvest can seed from a repo's real mocks."""

    identity_strings: List[str] = field(default_factory=list)
    url_patterns: List[str] = field(default_factory=list)
    count_patterns: List[str] = field(default_factory=list)
    badge_patterns: List[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (
            self.identity_strings
            or self.url_patterns
            or self.count_patterns
            or self.badge_patterns
        )


def _iter_mock_files(source_repo: Path) -> Iterable[Path]:
    seen = 0
    for path in sorted(source_repo.rglob("*")):
        if seen >= _MAX_SCAN_FILES:
            return
        if not path.is_file():
            continue
        # Skip guardkit's own qa/ payload and VCS dirs.
        rel = str(path.relative_to(source_repo))
        if rel.startswith((".git/", ".git\\")) or "/qa/" in f"/{rel}":
            continue
        if not (_MOCK_PATH_SIGNAL.search(rel) or _MOCK_FILE_SUFFIX.search(path.name)):
            continue
        try:
            if path.stat().st_size > _MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        seen += 1
        yield path


def _dedup_cap(values: Iterable[str]) -> List[str]:
    out: List[str] = []
    for v in values:
        v = v.strip()
        if v and v not in out:
            out.append(v)
        if len(out) >= _MAX_DENY_PER_CLASS:
            break
    return out


def detect_mock_identities(source_repo: Path) -> MockIdentities:
    """Scan the source repo's test/fixture code for real mock identity strings.

    Conservative by design: a literal is collected as an identity only when its
    line carries a mock/fake/fixture signal OR it is assigned to an
    identity-shaped identifier, so ordinary test strings are not swept into the
    deny-list (an over-broad deny would red a claimed-real scope for nothing).
    """
    identities: List[str] = []
    urls: List[str] = []
    for path in _iter_mock_files(source_repo):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line in text.splitlines():
            for url_hit in _URL_RE.findall(line):
                cleaned = url_hit.strip().strip("'\"")
                if cleaned:
                    urls.append(cleaned)
            has_context = bool(_MOCK_CONTEXT_RE.search(line))
            has_identity_var = bool(_IDENTITY_VAR_RE.search(line))
            if not (has_context or has_identity_var):
                continue
            for _q, literal in _STRING_LITERAL_RE.findall(line):
                literal = literal.strip()
                if not literal or len(literal) > 80:
                    continue
                # Collect a literal when: it is an email, it is name-shaped, its
                # line carries a mock/fake signal, OR it is assigned to an
                # identity-shaped variable (MOCK_USER_NAME, author, email...).
                if "@" in literal or _NAME_SHAPE_RE.match(literal) or has_context or has_identity_var:
                    # An email is both an identity and a URL-ish leak; keep it
                    # as an identity string (the sweep matches substrings).
                    if literal.lower().startswith(("http://", "https://")):
                        urls.append(literal)
                    else:
                        identities.append(literal)
    return MockIdentities(
        identity_strings=_dedup_cap(identities),
        url_patterns=_dedup_cap(urls),
    )


# ---------------------------------------------------------------------------
# Renderers — pure, deterministic YAML strings (readable/diffable, comment-rich
# like the qa_scaffold stubs). No yaml.dump so the header comments survive.
# ---------------------------------------------------------------------------


def _yaml_str(value: str) -> str:
    """Render a scalar string as a safely-quoted single-line YAML value."""
    # Double-quote and escape backslashes/quotes — valid YAML for any content.
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _yaml_list(values: List[str], indent: str) -> str:
    if not values:
        return f"{indent}[]"
    return "\n".join(f"{indent}- {_yaml_str(v)}" for v in values)


def _normalise_language(language: str) -> str:
    return (language or "").strip().lower() or "unknown"


def _normalise_framework(test_framework: str, language: str) -> str:
    fw = (test_framework or "").strip().lower()
    if fw:
        return fw
    # Sensible per-language default when detection found no explicit framework.
    lang = _normalise_language(language)
    return {
        "python": "pytest",
        "csharp": "dotnet_test",
        "c#": "dotnet_test",
        "typescript": "jest",
        "javascript": "jest",
        "dart": "flutter_test",
    }.get(lang, "unknown")


@dataclass
class ObservedFailureEntry:
    """One observed red, recorded as a triageable F2 ledger entry.

    Carries the schema-mandated per-entry ``owner`` + ``review_by`` (the fields
    at ``known_failures.py:65-67``) plus an honest, triage-flagging ``reason`` —
    it is NOT a claim the failure is acceptable, it is the observed truth pending
    a human owner. ``review_by`` keeps a red baseline from being enshrined.
    """

    test_id: str
    reason: str
    since_date: str
    since_sha: str
    owner: str
    review_by: str


def render_known_failures_instance(
    *,
    suite_id: str,
    framework: str,
    language: str,
    passed: int,
    entries: Optional[List[ObservedFailureEntry]] = None,
) -> str:
    """E1 · a real F2 baseline for the SOURCE repo.

    ``entries`` are observed reds recorded with owner + review_by (§6: "each
    either ledgered with owner+review_by, or surfaced as a finding" — this seeder
    does both). The root ledger carries no owner/review_by (those are per-entry
    fields, ``known_failures.py:65-67``); a fully-green suite leaves the list
    empty and the baseline still documents ``expected.passed``.
    """
    entries = entries or []
    lines = [
        "# F2 · known-failure ledger — SEEDED by /template-create (PB-6).",
        "# expected.passed is the count OBSERVED by running this repo's suite once",
        "# at harvest time. Every later run is diffed against this ledger, never",
        "# against 'all green'. Any observed red is recorded below with owner +",
        "# review_by and a 'triage me' reason — reassign or retire it (do not just",
        "# enshrine it) before enabling qa.enforce_tier1.",
        "# Validate: guardkit qa validate known-failures qa/known-failures.yaml",
        'format_version: "1.0"',
        f"suite_id: {_yaml_str(suite_id)}",
        f"framework: {_yaml_str(framework)}",
        f"language: {_yaml_str(language)}",
        "expected:",
        f"  passed: {passed}",
    ]
    if not entries:
        lines.append("known_failures: []")
    else:
        lines.append("known_failures:")
        for e in entries:
            lines.append(f"  - test_id: {_yaml_str(e.test_id)}")
            lines.append(f"    reason: {_yaml_str(e.reason)}")
            lines.append("    since:")
            lines.append(f"      date: {_yaml_str(e.since_date)}")
            lines.append(f"      sha: {_yaml_str(e.since_sha)}")
            lines.append(f"    owner: {_yaml_str(e.owner)}")
            lines.append(f"    review_by: {_yaml_str(e.review_by)}")
    return "\n".join(lines) + "\n"


def render_leak_sweep_instance(mocks: MockIdentities) -> str:
    """E3 · a source-repo F3 manifest: real deny, NO claimed-real surface.

    The schema requires >=1 persona and >=1 surface, so a placeholder persona and
    a placeholder surface (claimed_by TASK-0000 — a non-claim) are carried; the
    deny block holds the repo's REAL mock strings. Harvest claims no surface as
    real — every surface here is the TASK-0000 placeholder for /feature-plan to
    replace (scope §3).
    """
    identity = mocks.identity_strings or ["Mock User"]
    return (
        "# F3 · leak-sweep manifest — deny_patterns SEEDED by /template-create (PB-6)\n"
        "# from this repo's real mock identities. Harvest seeds ONLY the deny block;\n"
        "# it claims NO surface as real (claimed_by TASK-0000 is a placeholder, not a\n"
        "# claim). /feature-plan is the writer that claims surfaces real.\n"
        "# Validate: guardkit qa validate leak-sweep qa/leak-sweep.yaml\n"
        'format_version: "1.0"\n'
        "personas:\n"
        "  - id: default-user             # PLACEHOLDER — a real login persona\n"
        "    login_role: user\n"
        "    credentials_ref: QA_DEFAULT_USER_CREDENTIALS\n"
        "deny:\n"
        "  identity_strings:\n"
        f"{_yaml_list(identity, '    ')}\n"
        "  count_patterns:\n"
        f"{_yaml_list(mocks.count_patterns, '    ')}\n"
        "  url_patterns:\n"
        f"{_yaml_list(mocks.url_patterns, '    ')}\n"
        "  badge_patterns:\n"
        f"{_yaml_list(mocks.badge_patterns, '    ')}\n"
        "surfaces:\n"
        "  - route: /                     # PLACEHOLDER — /feature-plan claims real surfaces\n"
        "    claimed_by: TASK-0000\n"
        "    scope: full_page\n"
        "    allowed_mock_regions: []\n"
        "    extra_deny: []\n"
    )


def render_discovery_gate_stub(layer_key: str) -> str:
    """E4 · one F12 discovery-gate STUB per layer_mapping (planner fills it)."""
    safe = re.sub(r"[^A-Za-z0-9_-]", "-", layer_key) or "layer"
    return (
        "# F12 · discovery-gate STUB — SEEDED by /template-create (PB-6), one per\n"
        f"# settings.json layer_mapping (this one: {layer_key!r}). A pre-registration\n"
        "# scaffold: /feature-plan replaces the PLACEHOLDER claim/probe/gate with the\n"
        "# feature's real external claims before the build leans on them.\n"
        "# Validate: guardkit qa validate discovery-gates qa/discovery-gates-<...>.yaml\n"
        'format_version: "1.0"\n'
        f"feature_id: {_yaml_str('PLACEHOLDER-' + safe)}\n"
        "external_claims:\n"
        f"  - claim: {_yaml_str('PLACEHOLDER — an external claim the ' + layer_key + ' layer leans on')}\n"
        "    load_bearing: false          # PLACEHOLDER — planner sets true for real load-bearing claims\n"
        "    probe:\n"
        "      cmd: \"PLACEHOLDER — the probe command (planner fills)\"\n"
        "      consumer_artifact_shape: \"PLACEHOLDER — the consumer's real artifact shape\"\n"
        "      run_against: live_system\n"
        "    result: gate\n"
        "    gate:\n"
        f"      id: {_yaml_str('PRE-REGISTRATION-' + safe)}\n"
        "      pass_criteria: \"PRE-REGISTRATION — planner fills the pass criteria\"\n"
        "      fallback: \"PRE-REGISTRATION — planner fills the pre-agreed fallback\"\n"
        "      status: open\n"
    )


def render_known_failures_stub(*, framework: str, language: str) -> str:
    """E2 · a stack-typed F2 STUB for the generated template dir (passed=0)."""
    return (
        "# F2 · known-failure ledger STUB — stack-typed by /template-create (PB-6).\n"
        "# PLACEHOLDER content: expected.passed=0 until this repo records its own\n"
        "# observed suite count. Stubs ship with the template; never the source\n"
        "# repo's instance data (K5).\n"
        "# Validate: guardkit qa validate known-failures qa/known-failures.yaml\n"
        'format_version: "1.0"\n'
        "suite_id: default-suite          # PLACEHOLDER — name this repo's suite\n"
        f"framework: {_yaml_str(framework)}\n"
        f"language: {_yaml_str(language)}\n"
        "expected:\n"
        "  passed: 0                      # PLACEHOLDER — the documented green count\n"
        "known_failures: []\n"
    )


def render_leak_sweep_stub() -> str:
    """E2 · a placeholder F3 STUB for the generated template dir."""
    return (
        "# F3 · leak-sweep manifest STUB — /template-create (PB-6) placeholder.\n"
        "# Replace the PLACEHOLDER deny strings with this repo's real mock\n"
        "# identities; /feature-plan claims real surfaces.\n"
        "# Validate: guardkit qa validate leak-sweep qa/leak-sweep.yaml\n"
        'format_version: "1.0"\n'
        "personas:\n"
        "  - id: default-user             # PLACEHOLDER — a real login persona\n"
        "    login_role: user\n"
        "    credentials_ref: QA_DEFAULT_USER_CREDENTIALS\n"
        "deny:\n"
        "  identity_strings:\n"
        '    - "Test User"                # PLACEHOLDER — this repo\'s mock identities\n'
        "  count_patterns: []\n"
        "  url_patterns:\n"
        '    - "example.com"\n'
        "  badge_patterns: []\n"
        "surfaces:\n"
        "  - route: /                     # PLACEHOLDER — a claimed-real surface\n"
        "    claimed_by: TASK-0000\n"
        "    scope: full_page\n"
        "    allowed_mock_regions: []\n"
        "    extra_deny: []\n"
    )


# ---------------------------------------------------------------------------
# Per-file-if-absent write (K5 / DF-007) — the qa_scaffold.py semantics.
# ---------------------------------------------------------------------------


def _git_head_sha(repo: Path) -> str:
    """Best-effort short HEAD sha of ``repo`` for a ledger entry's since.sha.

    Falls back to a schema-valid placeholder (>=4 chars) when git is unavailable
    or the repo is not a checkout — the ledger entry still validates.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short=8", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        sha = (proc.stdout or "").strip()
        if proc.returncode == 0 and len(sha) >= 4:
            return sha
    except Exception:  # pragma: no cover - defensive
        pass
    return "00000000"


def write_if_absent(dest: Path, content: str) -> bool:
    """Write ``content`` to ``dest`` only when ``dest`` is absent (never clobber).

    Returns True if written, False if the target already existed (K5: a repo's
    committed qa/ truth always wins).
    """
    if dest.exists():
        logger.info("qa seed: %s already exists, skipping (K5 never clobbers)", dest)
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    logger.info("qa seed: wrote %s", dest)
    return True


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


@dataclass
class QASeedResult:
    """What the qa-seed harvest phase emitted."""

    source_seeds: List[str] = field(default_factory=list)
    template_stubs: List[str] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


_TRIAGE_REASON = (
    "observed failing during /template-create harvest; not yet triaged — assign "
    "an owner and a real reason, or retire this test, before enabling "
    "qa.enforce_tier1 (a harvest-recorded observation, not an accepted failure)"
)


def _build_observed_entries(
    obs: SuiteObservation, *, since_date: str, since_sha: str, review_by: str
) -> List[ObservedFailureEntry]:
    """Turn observed reds into triageable F2 entries (owner + review_by populated)."""
    if not obs.failed:
        return []
    ids = list(obs.failure_ids)
    if not ids:
        # Failed count with no parseable ids — record one summary entry rather
        # than silently dropping the signal.
        ids = [f"observed-failures ({obs.failed} unparsed)"]
    return [
        ObservedFailureEntry(
            test_id=test_id,
            reason=_TRIAGE_REASON,
            since_date=since_date,
            since_sha=since_sha,
            owner=_HARVEST_OWNER,
            review_by=review_by,
        )
        for test_id in ids
    ]


def seed_qa_verification(
    source_repo: Path,
    template_dir: Optional[Path],
    *,
    language: str,
    test_framework: str,
    layer_mapping_keys: Iterable[str],
    today: Optional[date] = None,
    suite_runner: Optional[SuiteRunner] = None,
) -> QASeedResult:
    """Emit the four PB-6 verification seeds (E1–E4).

    Non-raising: any single-emission problem is captured as a warning so
    ``/template-create`` never fails on the seed step. All writes are
    per-file-if-absent (K5).

    Args:
        source_repo: the repo being harvested — E1/E3/E4 land in ``<repo>/qa/``.
        template_dir: the generated template dir — E2 stubs land in
            ``<template>/qa/`` (skipped with a warning if None).
        language / test_framework: from Phase-1 detection.
        layer_mapping_keys: ``settings.json`` ``layer_mappings`` keys (E4 join).
        today: base date for E1 ``review_by`` (default ``date.today()`` — injected
            in tests for determinism).
        suite_runner: injected suite runner for E1 observation (tests).
    """
    result = QASeedResult()
    lang = _normalise_language(language)
    framework = _normalise_framework(test_framework, language)
    review_by = ((today or date.today()) + timedelta(days=_REVIEW_BY_DAYS)).isoformat()

    # --- E1: F2 observed-suite baseline into the SOURCE repo -----------------
    try:
        obs = observe_suite(source_repo, framework, runner=suite_runner)
        if not obs.ran:
            result.warnings.append(
                f"qa-seed E1 (F2 baseline) skipped: {obs.detail} "
                f"(source: {source_repo}/qa/known-failures.yaml)"
            )
        else:
            suite_id = f"{source_repo.name or 'harvested'}-suite"
            since_date = (today or date.today()).isoformat()
            since_sha = _git_head_sha(source_repo)
            entries = _build_observed_entries(
                obs, since_date=since_date, since_sha=since_sha, review_by=review_by
            )
            content = render_known_failures_instance(
                suite_id=suite_id,
                framework=framework,
                language=lang,
                passed=obs.passed,
                entries=entries,
            )
            if write_if_absent(source_repo / "qa" / "known-failures.yaml", content):
                result.source_seeds.append("qa/known-failures.yaml")
            if obs.failed:
                # Observed reds are BOTH ledgered (owner+review_by, above) AND
                # surfaced here as a finding (§6) — captured, not swallowed
                # (absence-of-failure discipline), and prominent for triage.
                ids = ", ".join(obs.failure_ids[:10]) or f"{obs.failed} failing test(s)"
                result.findings.append(
                    f"qa-seed E1: observed {obs.failed} failing test(s) while seeding "
                    f"the F2 baseline (passed={obs.passed}); each recorded in "
                    f"qa/known-failures.yaml with owner+review_by for triage before "
                    f"enabling qa.enforce_tier1: {ids}"
                )
    except Exception as exc:  # pragma: no cover - defensive
        result.warnings.append(f"qa-seed E1 failed (non-fatal): {exc}")

    # --- E3: F3 deny_patterns into the SOURCE repo ---------------------------
    try:
        mocks = detect_mock_identities(source_repo)
        if mocks.is_empty():
            result.warnings.append(
                "qa-seed E3 (F3 deny_patterns) skipped: no mock identity strings "
                f"found in {source_repo}'s test/fixture code. Add qa/leak-sweep.yaml "
                "deny_patterns manually before enabling the sweep gate."
            )
        else:
            content = render_leak_sweep_instance(mocks)
            if write_if_absent(source_repo / "qa" / "leak-sweep.yaml", content):
                result.source_seeds.append("qa/leak-sweep.yaml")
    except Exception as exc:  # pragma: no cover - defensive
        result.warnings.append(f"qa-seed E3 failed (non-fatal): {exc}")

    # --- E4: one F12 discovery-gate stub per layer_mapping -------------------
    try:
        keys = [k for k in layer_mapping_keys if str(k).strip()]
        if not keys:
            result.warnings.append(
                "qa-seed E4 (F12 discovery-gate stubs) skipped: settings.json has "
                "no layer_mappings to key gates off. Add discovery gates at plan time."
            )
        for key in keys:
            safe = re.sub(r"[^A-Za-z0-9_-]", "-", str(key)) or "layer"
            rel = f"qa/discovery-gates-{safe}.yaml"
            if write_if_absent(source_repo / rel, render_discovery_gate_stub(str(key))):
                result.source_seeds.append(rel)
    except Exception as exc:  # pragma: no cover - defensive
        result.warnings.append(f"qa-seed E4 failed (non-fatal): {exc}")

    # --- E2: stack-typed qa/ stubs into the generated TEMPLATE dir -----------
    try:
        if template_dir is None:
            result.warnings.append(
                "qa-seed E2 (stack-typed template stubs) skipped: no template dir "
                "resolved (dry-run?). The generated template will not carry qa/ stubs."
            )
        else:
            e2_files = {
                "qa/known-failures.yaml": render_known_failures_stub(
                    framework=framework, language=lang
                ),
                "qa/leak-sweep.yaml": render_leak_sweep_stub(),
            }
            for rel, content in e2_files.items():
                if write_if_absent(template_dir / rel, content):
                    result.template_stubs.append(rel)
    except Exception as exc:  # pragma: no cover - defensive
        result.warnings.append(f"qa-seed E2 failed (non-fatal): {exc}")

    return result
