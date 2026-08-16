"""THE NEGATIVE CORPUS — every primary-tree ``.feature`` in the estate, run
through the stamp normalizer's rules, with the per-repo histogram COMMITTED.

Why this exists (2026-08-16): an adversarial verifier ran the 08-16 rules
over the estate and found several families minting WRONG homes SILENTLY on
real prose (H1 silent operator · H2 false HTTP surface · M1 path literals ·
M2 "the app starts" · M3 the Coach-score noun · M4 "acknowledged"/
"subscription"). The rules were tightened; this test is the safety net that
keeps them honest: it pins, per repo, how many scenarios land in each home
AND how many are REFUSED (the honest number), so any future rule change
shows its delta in a committed file instead of silently re-homing scenarios.

The corpus (``tests/fixtures/stamp_normalizer/estate_corpus/``) is a
READ-ONLY copy of every tracked ``features/**/*.feature`` (lpa: ``docs/poc/
features/``) across forge, jarvis, fleet-memory, fleet-gateway,
specialist-agent, study-tutor, guardkit, lpa-platform-poc,
agentic-dataset-factory and api_test at the SHAs in ``MANIFEST.tsv`` —
worktrees, archives and test fixtures excluded — plus each repo's surface
evidence (``qa/gates/registry.yaml``, ``.guardkit/config.yaml``,
``pyproject.toml``, ``package.json``) so the HTTP surface is detected
STRUCTURALLY from the fixture itself.

What is asserted
----------------
(a) ``operator`` == exactly the enumerated explicit-human scenarios
    (``EXPLICIT_HUMAN``, 4 estate-wide, ≤ 5): the two lpa scenarios carrying
    the ``@operator-handoff`` tag, forge's "on the real NAS" runbook leg and
    the keycloak-standup scenario whose evidence is "runbook evidence".
    Anything else minted operator = a hidden chore for Rich = a failure.
(b) ``hurl`` == 0 in every repo WITHOUT a hurl gate / declared surface — in
    particular forge, jarvis, fleet-memory, specialist-agent and
    agentic-dataset-factory (none has a hurl gate; the 08-16 detector read
    forge/jarvis as HTTP from a pyproject COMMENT and minted hurl on hundreds
    of machinery scenarios).
(c) the full per-repo histogram (every home + REFUSED + total) equals the
    committed ``EXPECTED.json``. To re-baseline after a DELIBERATE rule
    change: ``STAMP_CORPUS_REBASELINE=1 pytest tests/orchestrator/
    test_stamp_normalizer_estate_corpus.py`` — then commit the diff and say
    why in the commit.

The committed histogram (2026-08-16, after the tightening)
----------------------------------------------------------
See ``EXPECTED.json`` for the numbers of record; the table below is a
human echo of the same file at the time of writing.

    repo                      http  total  refused  bus  process  exam  flutter  playwright  hurl  operator
    forge                     no      535      413   92       29     0        0           0     0         1
    jarvis                    no      279      233   40        6     0        0           0     0         0
    fleet-memory              no      233      215   13        5     0        0           0     0         0
    fleet-gateway             no       33       18   15        0     0        0           0     0         0
    specialist-agent          no      796      731   27        3    35        0           0     0         0
    study-tutor               YES     501      366   14       10     5       28           1    76         1
    guardkit                  no      168      159    8        1     0        0           0     0         0
    lpa-platform-poc          no      205      195    0        0     4        0           4     0         2
    agentic-dataset-factory   no      253      251    0        2     0        0           0     0         0
    api_test                  YES      74        0    0       17     0        0           0    57         0
    ------------------------------------------------------------------------------------------------------
    TOTAL                            3077     2581  209       73    44       28           5   133         4

Refused is the HONEST number: under Rich's condition 2 (no model in the
loop, no fallback home) an undecidable scenario refuses loud rather than
landing somewhere it does not belong. 2,581 of 3,077 (84%) refuse today —
the rules stamp only what they can prove; the rest is the model's (or a
human's) turn, by design.
"""

from __future__ import annotations

import csv
import json
import os
from collections import Counter
from pathlib import Path
from typing import Dict, List, Tuple

import pytest

from guardkit.orchestrator.stamp_normalizer import (
    NormalizeContext,
    classify_scenario,
    detect_repo_http_surface,
    extract_scenario_blocks,
)
from guardkit.orchestrator.verifier_stamp import VERIFIER_HOMES

CORPUS_ROOT = Path(__file__).parent.parent / "fixtures" / "stamp_normalizer" / "estate_corpus"
EXPECTED_PATH = CORPUS_ROOT / "EXPECTED.json"
MANIFEST_PATH = CORPUS_ROOT / "MANIFEST.tsv"

REPOS: Tuple[str, ...] = (
    "forge",
    "jarvis",
    "fleet-memory",
    "fleet-gateway",
    "specialist-agent",
    "study-tutor",
    "guardkit",
    "lpa-platform-poc",
    "agentic-dataset-factory",
    "api_test",
)

# The repos the verifier named: NO hurl gate exists in any of them.
NO_HURL_GATE_REPOS: Tuple[str, ...] = (
    "forge", "jarvis", "fleet-memory", "specialist-agent", "agentic-dataset-factory",
)

# (a) the enumerated explicit-human scenarios — the ONLY operator stamps
# the rules may mint across the estate. Each is genuinely attended work:
EXPLICIT_HUMAN: Dict[str, List[str]] = {
    "lpa-platform-poc": [
        # @operator-handoff tag + `# operator_handoff:` comment — the real
        # provider revoke is proven against the live Moneyhub sandbox.
        "Only active bank connections are revoked at the provider",
        "A provider revocation failure does not prevent the local data wipe",
    ],
    "forge": [
        # "on the real NAS" — the runbook executor's real-hardware leg.
        "The executor stands fleet-memory up on the real NAS",
    ],
    "study-tutor": [
        # "captured in the runbook evidence" — the operator's readings.
        "NAS memory is recorded before and after standup and headroom stays positive",
    ],
}
assert sum(len(v) for v in EXPLICIT_HUMAN.values()) <= 5

REFUSED = "REFUSED"
COLUMNS = ("total", REFUSED) + tuple(VERIFIER_HOMES)


def _feature_files(repo: str) -> List[Path]:
    root = CORPUS_ROOT / repo
    return sorted(root.rglob("*.feature"))


def classify_repo(repo: str) -> Tuple[Dict[str, int], Dict[str, List[str]], bool, str]:
    """(histogram, titles-by-home, has_http_surface, evidence) for one repo."""
    root = CORPUS_ROOT / repo
    has_http, evidence = detect_repo_http_surface(root)
    ctx = NormalizeContext(repo_has_http_surface=has_http, http_surface_evidence=evidence)
    counts: Counter = Counter()
    by_home: Dict[str, List[str]] = {}
    for path in _feature_files(repo):
        text = path.read_text(encoding="utf-8", errors="replace")
        for block in extract_scenario_blocks(text):
            home = classify_scenario(block.title, block.steps_text, ctx, annotations=block.annotations)
            key = home.verifier if home is not None else REFUSED
            counts[key] += 1
            counts["total"] += 1
            by_home.setdefault(key, []).append(block.title)
    histogram = {col: int(counts.get(col, 0)) for col in COLUMNS}
    return histogram, by_home, has_http, evidence


def build_estate_histogram() -> Dict[str, Dict[str, object]]:
    out: Dict[str, Dict[str, object]] = {}
    for repo in REPOS:
        histogram, _, has_http, evidence = classify_repo(repo)
        out[repo] = {"http_surface": has_http, "http_surface_evidence": evidence, **histogram}
    return out


def _load_expected() -> Dict[str, Dict[str, object]]:
    return json.loads(EXPECTED_PATH.read_text(encoding="utf-8"))


def _render(hist: Dict[str, Dict[str, object]]) -> str:
    cols = ("total", REFUSED, "probe:bus", "probe:process", "exam", "flutter", "playwright", "hurl", "operator", "toolchain")
    lines = [f"{'repo':26s} http " + " ".join(f"{c[:8]:>8s}" for c in cols)]
    for repo, row in hist.items():
        lines.append(
            f"{repo:26s} {'YES' if row['http_surface'] else 'no ':4s} "
            + " ".join(f"{int(row.get(c, 0)):>8d}" for c in cols)
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The corpus itself
# ---------------------------------------------------------------------------


def test_the_corpus_manifest_matches_the_files_on_disk():
    """Every file the manifest names is present and every .feature present
    is in the manifest — the corpus is a whole, read-only, pinned copy."""
    with MANIFEST_PATH.open(encoding="utf-8") as fh:
        rows = [r for r in csv.reader(fh, delimiter="\t") if r]
    manifest_features = {(r[0], r[2]) for r in rows if r[2].endswith(".feature")}
    on_disk = {
        (repo, str(p.relative_to(CORPUS_ROOT / repo)))
        for repo in REPOS
        for p in _feature_files(repo)
    }
    assert manifest_features == on_disk
    assert len(on_disk) == 115
    for r in rows:
        assert (CORPUS_ROOT / r[0] / r[2]).exists(), r


# ---------------------------------------------------------------------------
# (a) operator == the enumerated explicit-human scenarios
# ---------------------------------------------------------------------------


def test_a_operator_is_minted_only_for_the_enumerated_explicit_human_scenarios():
    minted: Dict[str, List[str]] = {}
    for repo in REPOS:
        _, by_home, _, _ = classify_repo(repo)
        if by_home.get("operator"):
            minted[repo] = sorted(by_home["operator"])
    expected = {repo: sorted(titles) for repo, titles in EXPLICIT_HUMAN.items()}
    assert minted == expected, (
        "R10 minted `operator` outside the enumerated explicit-human list — a "
        f"hidden chore for Rich.\nminted={json.dumps(minted, indent=2)}\nexpected={json.dumps(expected, indent=2)}"
    )
    assert sum(len(v) for v in minted.values()) == 4


# ---------------------------------------------------------------------------
# (b) hurl == 0 wherever there is no hurl gate / declared surface
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("repo", NO_HURL_GATE_REPOS)
def test_b_named_repos_have_no_hurl_gate_and_mint_zero_hurl(repo):
    histogram, by_home, has_http, evidence = classify_repo(repo)
    assert has_http is False, f"{repo} read as HTTP: {evidence}"
    assert histogram["hurl"] == 0, by_home.get("hurl")


@pytest.mark.parametrize("repo", REPOS)
def test_b_no_surface_means_no_hurl_anywhere(repo):
    histogram, by_home, has_http, _ = classify_repo(repo)
    if not has_http:
        assert histogram["hurl"] == 0, by_home.get("hurl")


def test_b_only_api_test_and_study_tutor_have_an_http_surface_and_each_structurally():
    surfaces = {repo: detect_repo_http_surface(CORPUS_ROOT / repo) for repo in REPOS}
    with_surface = {r for r, (has, _) in surfaces.items() if has}
    assert with_surface == {"api_test", "study-tutor"}, surfaces
    assert "hurl-twins" in surfaces["api_test"][1]
    assert "starlette" in surfaces["study-tutor"][1]


# ---------------------------------------------------------------------------
# (c) the committed histogram — the honest baseline
# ---------------------------------------------------------------------------


def test_c_the_per_repo_histogram_equals_the_committed_baseline():
    actual = build_estate_histogram()
    if os.environ.get("STAMP_CORPUS_REBASELINE") == "1":
        EXPECTED_PATH.write_text(json.dumps(actual, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    expected = _load_expected()
    if actual != expected:
        deltas = []
        for repo in REPOS:
            for col in ("http_surface",) + COLUMNS:
                a, e = actual[repo].get(col), expected.get(repo, {}).get(col)
                if a != e:
                    deltas.append(f"  {repo}.{col}: expected {e!r}, got {a!r}")
        pytest.fail(
            "The estate histogram MOVED — a rule change re-homed scenarios. Review the "
            "delta below; if deliberate, re-baseline with STAMP_CORPUS_REBASELINE=1 and "
            "say why in the commit.\n" + "\n".join(deltas) + "\n\nactual:\n" + _render(actual)
        )
    total = sum(int(r["total"]) for r in actual.values())
    refused = sum(int(r[REFUSED]) for r in actual.values())
    assert total == 3077
    assert refused == 2581


def test_c_the_docstring_table_matches_the_baseline_totals():
    """The human echo in this module's docstring is derived from EXPECTED.json —
    keep the two together (this pins the TOTAL row)."""
    expected = _load_expected()
    totals = Counter()
    for row in expected.values():
        for col in COLUMNS:
            totals[col] += int(row[col])
    doc = __doc__ or ""
    total_line = next(line for line in doc.splitlines() if line.strip().startswith("TOTAL"))
    nums = [int(x) for x in total_line.split()[1:]]
    assert nums == [
        totals["total"], totals[REFUSED], totals["probe:bus"], totals["probe:process"],
        totals["exam"], totals["flutter"], totals["playwright"], totals["hurl"], totals["operator"],
    ], (nums, dict(totals))
