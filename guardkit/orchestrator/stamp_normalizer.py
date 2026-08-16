"""THE STAMP NORMALIZER — ``verifier:`` stamps minted by RULE from the parsed ``.feature``.

Design of record: ``ai-transition/docs/routing-law-stamp-normalizer-rules-2026-08-15.md``
(rules R1–R10, each with its census basis). Ruled by Rich via the factory
coordinator 2026-08-16, seam = guardkit-side (this module), with TWO BINDING
CONDITIONS:

1. **It WRITES.** The normalizer stamps the ``scenarios:`` map of the feature
   YAML on the planning branch — it is not a checker. Only titles that LACK a
   stamp are written; an existing stamp is NEVER overwritten (a human's or a
   plan-writer's stamp outranks a rule's).
2. **NO MODEL IN THE LOOP (v1).** Rules stamp what they can. Anything the
   rules cannot decide REFUSES LOUD — every undecidable title is named, with
   the closed vocabulary, in the same voice as the enforced-unstamped
   rejection in ``feature_loader._enforce_routing_law`` — and the run stops.
   Nothing is written on a refusal. There is NO fallback home; in particular
   ``operator`` is minted ONLY on an explicit human-work match (R10), never
   as the place unclassified scenarios land (that would convert every
   unclassified scenario into a hidden chore for Rich).

Why a rule and not a prompt: the first live drive under the routing-law
templates (planning run d5f2e13b) showed the plan-writer READ the closed
vocabulary and emitted ZERO stamps. Prompting harder tunes around a
small-model slip; the estate's doctrine is one rule mints the claim and the
thing claimed.

The rules (evaluated in order; first match wins)
------------------------------------------------
Inputs per scenario: the scenario's OWN title + Given/When/Then text
(lower-cased; the Background is NOT included — a shared Background line such
as "a throwaway sandboxed environment" would otherwise route every scenario in
the file), the repo's surface class (``ctx.repo_has_http_surface``), and any
test node the plan already names for the scenario (``ctx.plan_test_refs``).

R1  DB unavailable / DB down                     → ``probe:process``
R2  fresh start / restart / fresh process        → ``probe:process``
R3  runtime-smoke harness-meta (seeded directly, throwaway env, teardown,
    verdict reported, network posture …)         → ``probe:process``
R4  bus vocabulary (publish … subject/envelope, subscribe, heartbeat,
    JetStream, NATS, request-reply, inbox …)     → ``probe:bus``
R5  Flutter / device vocabulary                  → ``flutter``
R6  browser vocabulary (and NOT R5 — order)      → ``playwright``
R7  Then judges AI OUTPUT QUALITY                → ``exam``
R8  the plan names a test node for this title    → ``toolchain`` + ``test_ref``
R9  wire-shaped step text AND the repo has an HTTP surface → ``hurl``
R10 explicitly human (operator follows, by hand, physical robot, on the
    NAS, attended …)                             → ``operator`` (EXPLICIT only)
—   no rule matched                              → **REFUSE LOUD** (``None``)

Ordering rationale (from the design): infrastructure/process rules (R1–R3)
precede wire (R9) because a DB-down scenario also says "request" — the more
specific need wins. Bus (R4) precedes wire because fleet scenarios say
"reply". Exam (R7) precedes toolchain (R8) because a scenario judging Coach
output can also name a test node — the judged quality is the essential
surface. Toolchain (R8) precedes wire (R9) only when a real test node is
named — a scenario the plan already pinned to a test keeps that pin.

Honest divergences from the 2026-08-15 draft's regex families
--------------------------------------------------------------
The draft claimed R1–R10 reproduce api_test's 60 hand stamps except
users-count 7.1–7.3. Running the draft's LITERAL regexes did NOT (41/60):
R9 as drafted (``response should``, ``endpoint``, ``status code`` …) left
THIRTEEN hand-``hurl`` scenarios undecidable — their only wire vocabulary is
"I request the service X" / "the request should succeed" / "rejected as …" /
"created through the running service" / "looking up" / "not-found" (hyphen)
— and R3 as drafted left three runtime-smoke harness-meta scenarios
undecidable ("smoke run", "live deployment", "seeded directly and …"). The
families below are the draft's PLUS those idioms (each addition named in
the rule's comment); with them the reproduction is 57/60 — exact except the
one divergence the design named (7.1–7.3 → hurl by rule when the plan names
no test node). Pinned in ``tests/orchestrator/test_stamp_normalizer.py``.
"""

from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

import yaml

from guardkit.orchestrator.verifier_stamp import (
    VERIFIER_HOMES,
    _SCENARIO_LINE_RE,
    extract_scenario_titles,
    parse_scenario_stamp,
)

logger = logging.getLogger(__name__)

RULES_DOC = "ai-transition/docs/routing-law-stamp-normalizer-rules-2026-08-15.md"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class StampNormalizerError(ValueError):
    """The normalizer cannot RUN (no feature files, unreadable input, a
    write that failed verification). Loud, never a silent no-op."""


class StampNormalizerRefusal(StampNormalizerError):
    """The rules could not decide one or more titles — REFUSE LOUD.

    ``refused`` names every undecidable title; the message carries them all
    plus the closed vocabulary. Nothing was written.
    """

    def __init__(self, feature_id: str, refused: Sequence[str]):
        self.feature_id = feature_id
        self.refused = list(refused)
        super().__init__(_refusal_message(feature_id, self.refused))


def _vocabulary() -> str:
    return ", ".join(VERIFIER_HOMES)


def _refusal_message(feature_id: str, refused: Sequence[str]) -> str:
    listed = "\n".join(f"  - {t}" for t in refused)
    return (
        f"STAMP NORMALIZER: feature {feature_id} has {len(refused)} "
        f"UNDECIDABLE scenario(s) — no rule (R1–R10, {RULES_DOC}) matched "
        f"and there is NO fallback home (card Q8/A.2: a scenario silently "
        f"routed to a home it does not belong to is an unverified green). "
        f"The run stops here; nothing was written.\n"
        f"Undecidable:\n{listed}\n"
        f"FIX: stamp each title by hand in this feature's `scenarios:` map "
        f"with a `verifier:` from the closed list ({_vocabulary()}) — "
        f"`operator` ONLY for attended human work, never as a default — or "
        f"set `routing_law: off` on this feature."
    )


# ---------------------------------------------------------------------------
# The classification context and the result of one rule match
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NormalizeContext:
    """What the rules know beyond the scenario text.

    ``repo_has_http_surface`` — the declared toolchain is a web stack (a web
    framework in the repo's manifests) OR ``qa/gates/registry.yaml`` carries
    a hurl-twins gate. Gates R9.

    ``plan_test_refs`` — scenario title -> test node the plan already names
    (task-frontmatter ``test_ref`` / an in-plan ``tests/…::test_…`` reference
    whose tokens overlap the title by ≥2 significant words). Feeds R8.
    """

    repo_has_http_surface: bool = False
    plan_test_refs: Mapping[str, str] = field(default_factory=dict)
    http_surface_evidence: str = ""


def _coerce_ctx(ctx: Union[NormalizeContext, Mapping[str, Any], None]) -> NormalizeContext:
    if ctx is None:
        return NormalizeContext()
    if isinstance(ctx, NormalizeContext):
        return ctx
    return NormalizeContext(
        repo_has_http_surface=bool(ctx.get("repo_has_http_surface", False)),
        plan_test_refs=dict(ctx.get("plan_test_refs") or {}),
        http_surface_evidence=str(ctx.get("http_surface_evidence", "")),
    )


@dataclass(frozen=True)
class Home:
    """One rule's verdict for one scenario."""

    verifier: str
    rule: str
    evidence: str = ""
    test_ref: Optional[str] = None

    def to_stamp(self) -> Dict[str, Any]:
        stamp: Dict[str, Any] = {"verifier": self.verifier}
        if self.test_ref:
            stamp["test_ref"] = self.test_ref
        return stamp


# ---------------------------------------------------------------------------
# The regex families, R1–R10, in order
# ---------------------------------------------------------------------------


def _family(*patterns: str) -> List[re.Pattern[str]]:
    return [re.compile(p, re.IGNORECASE) for p in patterns]


# R1 — DB unavailable (census: the 6 DB-unavailable scenarios 2.5, 3.7, 6.4,
# 7.6, 8.6, 9.7 — needs infra control). `database is down` / `database
# unavailability` added: 9.7's title says "database is down", 6.4's title
# says "database unavailability" (their Given lines also match the draft).
R1_DB_UNAVAILABLE = _family(
    r"database (is|becomes|goes|remains) (unavailable|down|unreachable)",
    r"database unavailab",
    r"\bdb(-| )down\b",
    r"postgres\w* .* (stopped|unreachable|down|unavailable)",
)

# R2 — fresh start / restart (census: 2.3, 3.4, 3.8 — process control).
# "an app restart" (the Flutter sign-in feature's device idiom) is NOT a
# process restart — excluded here so R5 sees it.
R2_FRESH_START = _family(
    r"\b(just|freshly) started\b",
    r"(?<!\bapp )\brestart(s|ed|ing)?\b",
    r"\bafter (a )?restart\b",
    r"\bfresh (process|instance)\b",
    r"handled no other requests",
)

# R3 — runtime-smoke harness-meta (census: 5.1, 5.3–5.5, 5.9–5.12).
# Additions beyond the draft, each from a census scenario the draft's family
# missed: `seeded directly` generalized (5.5 says "seeded directly and one is
# created"), `smoke (run|verdict)` / `(fails|passes) the smoke` (5.4, 5.9,
# 5.11), `live deployment` (5.11), `before seeding` (5.5), `oracle time
# budget` (5.4).
R3_SMOKE_HARNESS = _family(
    r"seeded directly",
    r"before seeding",
    r"\bpsql\b",
    r"throwaway (environment|sandbox)",
    r"\bteardown\b",
    r"no trace .* remain",
    r"verdict .* reported",
    r"network posture",
    r"route to the outside world",
    r"\bsmoke (run|verdict)\b",
    r"\b(fails|passes|failed|passed) the smoke\b",
    r"\blive deployment\b",
    r"oracle time budget",
)

# R4 — bus vocabulary (census: 449 bus scenarios estate-wide — forge 182,
# jarvis 115, fleet-memory 65 …). `envelope`, `broker`, `acknowledg`,
# `deregister`, `publish … request/reply/message/event/fleet` added — the
# forge/jarvis lifecycle-envelope and approval-protocol scenarios say
# "publishes the approval request" / "envelope should be published" without
# the words subject/topic.
R4_BUS = _family(
    r"\b(re)?publish(es|ed|ing)?\b .* \b(subject|topic|envelope|message|event|fleet|request|reply)s?\b",
    r"\b(subject|topic|envelope|message|event)s? .* \b(re)?publish(es|ed|ing)?\b",
    r"\bsubscri",
    r"\bheartbeat",
    r"\bjetstream\b",
    r"\bnats\b",
    r"\bfleet\.register",
    r"\brequest[- ]reply\b",
    r"\binbox\b",
    r"\benvelopes?\b",
    r"\bbroker\b",
    r"\backnowledg",
    r"\bderegister",
    r"\bmessage bus\b",
)

# R5 — Flutter / device vocabulary (census: the 51 Flutter scenarios —
# sign-in 25, voice 26). Kept narrower than "the app" on purpose: the
# study-tutor http-app-access-adapter (a wire feature) says "the app
# authenticates / sends / lists" — those are hurl, not flutter. The added
# idioms are the sign-in feature's own: "reopen the app", "closed the app",
# "app restart", "browser sign-in", "home screen", "signed in on the device".
R5_FLUTTER = _family(
    r"\bflutter\b",
    r"\bthe app (shows|displays|navigates|is running|is installed|starts|"
    r"returns to the foreground|sits idle|should (not )?(crash|hang|start))",
    r"\b(re)?open(s|ed|ing)? the app\b",
    r"\bclose[sd]? the app\b",
    r"\bapp restart\b",
    r"\btap(s|ped|ping)?\b",
    r"\bmicrophone\b",
    r"\bsecure(ly)? stor",
    r"\bon the (family )?device\b",
    r"\bsign-in .* browser",
    r"\bbrowser sign-in\b",
    r"\bbrowser (opening|prompt|redirects back)",
    r"\b(home|sign-in|login|loading) screen\b",
    r"\bwidget\b",
    r"\bemulator\b",
)

# R6 — browser vocabulary (census: 2 browser scenarios estate-wide — a
# cert-trust page load; a client build-flag drift). Evaluated AFTER R5, so a
# Flutter OIDC browser-flow scenario is never mis-homed here.
R6_BROWSER = _family(
    r"\bin the browser\b",
    r"\bcertificate warning\b",
    r"\bsign-in page .{0,20}load",
    r"\b(client )?build[- ]flags?\b",
    r"\bpage renders\b",
    r"\baccount menu\b",
    r"\bmenu option\b",
)

# R7 — Then judges AI OUTPUT QUALITY (census: 208 agent-behaviour scenarios
# — specialist-agent 136, guardkit 35, LPA 16, tutor 13). The subject may be
# possessive ("the Coach's reasoning") or carry "should"; "evaluates" and
# "decision/verdict should be" added from the tutor-loop and product-owner
# conduct specs; "response … grounded" from primary-text-rag.
R7_EXAM = _family(
    r"\b(coach|player|tutor|agent)('s)? (should )?(scores?|rates?|explains?|"
    r"teaches|remembers?|grades?|marks?|judges?|assess(es)?)\b",
    r"\b(coach|player|tutor|agent) (should )?routes? .* to the expected tool",
    r"\b(coach|player|tutor|agent) evaluates\b",
    r"\b(coach|player|tutor|agent)('s)? (decision|verdict|reasoning) (should|is)\b",
    r"\b(coach|player|tutor|agent) should flag\b",
    r"\bnarration\b",
    r"\b(feedback|response|answer) (is|should be|should still be) (grounded|specific)",
    r"\binjection .* (ignored|treated as ordinary)",
    r"\bextract(s|ion)? (correctly|cleanly)",
    r"\bflag(ged)? .* (correctly|as an? .* violation)",
)

# R9 — wire-shaped step text (census: 417 HTTP scenarios; api_test's 40).
# Only fires when the repo has an HTTP surface. Additions beyond the draft,
# each from an api_test hand-`hurl` scenario the draft missed: bare
# `request(s|ed|ing)` (2.2, 3.2, 3.3, 3.5, 9.5), bare `response(s)` (3.3),
# `rejected as|with` (3.6), `through the (running) service` (5.2),
# `look(ing) up` (9.2), `route`.
R9_WIRE = _family(
    r"\b(get|post|put|patch|delete|options|head) requests?\b",
    r"\bsend(s|ing)? (a|an|two|three|the) .* requests? to\b",
    r"\bendpoints?\b",
    r"\bstatus code\b",
    r"\bresponses?\b",
    r"\bcontent[- ]type\b",
    r"\bjson\b",
    r"(?<![\w:])/[a-z][\w\-{}]*(/[\w\-{}]+)*",
    r"\bmethod[- ]not[- ]allowed\b",
    r"\bnot[- ]allowed\b",
    r"\bnot[- ]found\b",
    r"\bconflict\b",
    r"\bunauthori[sz]ed\b",
    r"\brequest(s|ed|ing)?\b",
    r"\brejected (as|with)\b",
    r"\bthrough the (running )?service\b",
    r"\blook(s|ed|ing)? up\b",
    r"\broutes?\b",
)

# R10 — EXPLICITLY human (census: the 3 unclassifiable + operator-handoff
# tagged scenarios). Explicit match ONLY — never a fallback. `robot` added:
# the two physical-Reachy scenarios say "the robot", not "physical robot";
# `the operator records/checks …` and `runbook evidence` from the
# keycloak-standup operator-handoff scenarios. `(?<!un)attended` so
# "unattended" never reads as attended.
R10_OPERATOR = _family(
    r"\ban operator follows\b",
    r"\bthe operator (records|checks|follows|walks|performs|runs|executes|confirms|reads|inspects)\b",
    r"\bby hand\b",
    r"\bphysical (robot|device)\b",
    r"\brobot\b",
    r"\bon the (real )?nas\b",
    r"(?<!un)\battended\b",
    r"\brunbook evidence\b",
    r"\bhuman[- ]operator\b",
)


_ORDERED_TEXT_RULES: Tuple[Tuple[str, str, List[re.Pattern[str]]], ...] = (
    ("R1", "probe:process", R1_DB_UNAVAILABLE),
    ("R2", "probe:process", R2_FRESH_START),
    ("R3", "probe:process", R3_SMOKE_HARNESS),
    ("R4", "probe:bus", R4_BUS),
    ("R5", "flutter", R5_FLUTTER),
    ("R6", "playwright", R6_BROWSER),
    ("R7", "exam", R7_EXAM),
)


def _first_match(family: Iterable[re.Pattern[str]], text: str) -> Optional[str]:
    for pat in family:
        m = pat.search(text)
        if m:
            return m.group(0)
    return None


def classify_scenario(
    title: str,
    steps_text: str,
    ctx: Union[NormalizeContext, Mapping[str, Any], None] = None,
) -> Optional[Home]:
    """Apply R1–R10 in order to one scenario; ``None`` = undecidable.

    Pure: no I/O, no logging. ``steps_text`` is the scenario's OWN
    Given/When/Then text (Background excluded — see the module docstring).
    ``None`` means REFUSE — the caller must never map it to a home.
    """
    context = _coerce_ctx(ctx)
    text = f"{title}\n{steps_text}".lower()

    for rule, verifier, family in _ORDERED_TEXT_RULES:
        hit = _first_match(family, text)
        if hit is not None:
            return Home(verifier=verifier, rule=rule, evidence=hit.strip())

    # R8 — the plan names a test node for this scenario (task frontmatter
    # `test_ref` or an in-plan `tests/…::test_…` reference with ≥2
    # significant-word overlap on the title). census: 1,573 internal-
    # machinery scenarios (48%) — the repo's own suite. Beats R9 ONLY when
    # a real node is named.
    node = context.plan_test_refs.get(title) if context.plan_test_refs else None
    if node:
        return Home(
            verifier="toolchain",
            rule="R8",
            evidence=f"plan names test node {node}",
            test_ref=node,
        )

    # R9 — wire-shaped AND the repo has an HTTP surface.
    if context.repo_has_http_surface:
        hit = _first_match(R9_WIRE, text)
        if hit is not None:
            why = context.http_surface_evidence or "repo has an HTTP surface"
            return Home(
                verifier="hurl", rule="R9", evidence=f"{hit.strip()} ({why})"
            )

    # R10 — explicitly human. EXPLICIT match only; never a fallback.
    hit = _first_match(R10_OPERATOR, text)
    if hit is not None:
        return Home(verifier="operator", rule="R10", evidence=hit.strip())

    return None


# ---------------------------------------------------------------------------
# Gherkin: titles + per-scenario step text (line-shaped lexing, same regex
# as `extract_scenario_titles` — no parser is added here)
# ---------------------------------------------------------------------------


_KEYWORD_LINE_RE = re.compile(
    r"^\s*(?:Feature|Background|Rule)\s*:", re.IGNORECASE
)


def extract_scenarios(feature_text: str) -> List[Tuple[str, str]]:
    """``[(title, steps_text), …]`` in file order (duplicates kept).

    Titles come from the same ``_SCENARIO_LINE_RE`` as
    ``extract_scenario_titles`` (this function's title list is asserted equal
    to it). ``steps_text`` is every non-blank, non-comment (``#``), non-tag
    (``@``) line between this scenario's title line and the next
    scenario/``Rule:`` line — the scenario's OWN steps and Examples rows,
    never the Background.
    """
    matches = list(_SCENARIO_LINE_RE.finditer(feature_text))
    scenarios: List[Tuple[str, str]] = []
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(feature_text)
        body_lines: List[str] = []
        for raw in feature_text[start:end].splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or line.startswith("@"):
                continue
            if _KEYWORD_LINE_RE.match(line):
                # A `Rule:` (or a stray Feature/Background) closes the block.
                break
            body_lines.append(line)
        scenarios.append((m.group("title"), "\n".join(body_lines)))

    titles = [t for t, _ in scenarios]
    if titles != extract_scenario_titles(feature_text):  # pragma: no cover — same regex
        raise StampNormalizerError(
            "internal: extract_scenarios and extract_scenario_titles disagree"
        )
    return scenarios


# ---------------------------------------------------------------------------
# Context builders: HTTP surface, plan test refs
# ---------------------------------------------------------------------------


_WEB_FRAMEWORKS_PY = (
    "fastapi", "flask", "django", "starlette", "aiohttp", "litestar",
    "sanic", "tornado", "quart", "falcon", "bottle", "uvicorn",
)
_WEB_FRAMEWORKS_NODE = (
    "express", "fastify", "koa", "@hapi/hapi", "hapi", "next", "@nestjs/core",
    "hono", "restify", "@sveltejs/kit", "nuxt",
)
_WEB_FRAMEWORKS_OTHER = (
    "gin-gonic", "labstack/echo", "gofiber", "net/http",  # go.mod
    "Microsoft.AspNetCore", "actix-web", "axum", "rocket",  # csproj / Cargo
)


def detect_repo_http_surface(repo_root: Path) -> Tuple[bool, str]:
    """(has_surface, evidence). Two doors, either suffices:

    * ``qa/gates/registry.yaml`` names a gate whose id or path says ``hurl``
      (the hurl-twins gate — the wire class already has a runner here);
    * a web framework in the repo's manifests (pyproject / requirements* /
      package.json / go.mod / *.csproj / Cargo.toml) — "the declared
      toolchain is a web stack".
    """
    root = Path(repo_root)
    registry = root / "qa" / "gates" / "registry.yaml"
    if registry.exists():
        try:
            data = yaml.safe_load(registry.read_text(encoding="utf-8")) or {}
            for gate in (data.get("gates") or []) if isinstance(data, dict) else []:
                if not isinstance(gate, dict):
                    continue
                gid = str(gate.get("id", ""))
                gpath = str(gate.get("path", ""))
                if "hurl" in gid.lower() or "hurl" in gpath.lower():
                    return True, f"qa/gates/registry.yaml gate '{gid}'"
        except Exception as exc:  # noqa: BLE001 — a broken registry never crashes classification
            logger.warning("stamp normalizer: could not read %s: %s", registry, exc)

    manifests: List[Path] = []
    for name in ("pyproject.toml", "package.json", "go.mod", "Cargo.toml"):
        p = root / name
        if p.exists():
            manifests.append(p)
    manifests.extend(sorted(root.glob("requirements*.txt")))
    manifests.extend(sorted((root / "requirements").glob("*.txt")) if (root / "requirements").is_dir() else [])
    manifests.extend(sorted(root.glob("*.csproj")))
    for m in manifests:
        try:
            text = m.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        low = text.lower()
        for fw in _WEB_FRAMEWORKS_PY + _WEB_FRAMEWORKS_NODE + _WEB_FRAMEWORKS_OTHER:
            if re.search(r"(?<![\w.-])" + re.escape(fw.lower()) + r"(?![\w-])", low):
                return True, f"{m.relative_to(root)} declares {fw}"
    return False, "no hurl gate in qa/gates/registry.yaml and no web framework in the manifests"


_STOPWORDS = frozenset(
    "the a an is are was were be been being of to and or with when then given "
    "should that this for its it by on in as not no from at into via than "
    "does do did has have had can will would still also any all each every "
    "their they them there these those which who what how i my me we our you "
    "your his her one two three but if so".split()
)


_SUFFIXES = ("ally", "ment", "ing", "ed", "es", "al", "s")


def _stem(word: str) -> str:
    """A deliberately tiny stemmer so "increments" and "incremental" (or
    "users" and "user", "creating" and "created") count as the same
    significant word for the R8 overlap. Nothing cleverer on purpose."""
    for suf in _SUFFIXES:
        if len(word) > len(suf) + 3 and word.endswith(suf):
            return word[: -len(suf)]
    return word


def _significant_words(text: str) -> List[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [_stem(w) for w in words if len(w) >= 3 and w not in _STOPWORDS]


def _node_tokens(node: str) -> List[str]:
    # `tests/users/test_router.py::TestCount::test_count_empty` -> the last
    # segment's words minus "test".
    leaf = node.split("::")[-1]
    return [w for w in _significant_words(leaf.replace("_", " ")) if w != "test"]


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---", re.DOTALL)
_TEST_NODE_RE = re.compile(r"tests?/[\w\-./]+\.py::(?:[A-Za-z_]\w*::)*(test_\w+)")


def _read_frontmatter(text: str) -> Dict[str, Any]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def collect_plan_test_nodes(task_paths: Iterable[Path]) -> List[str]:
    """Every test node the plan names: task-frontmatter ``test_ref`` (string
    or list) + in-body ``tests/…::test_…`` references. Order kept, deduped."""
    nodes: List[str] = []
    for path in task_paths:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = _read_frontmatter(text)
        ref = fm.get("test_ref")
        if isinstance(ref, str) and ref.strip():
            nodes.append(ref.strip())
        elif isinstance(ref, list):
            nodes.extend(str(r).strip() for r in ref if str(r).strip())
        for m in _TEST_NODE_RE.finditer(text):
            nodes.append(m.group(1))
    return list(dict.fromkeys(nodes))


def build_plan_test_refs(
    titles: Iterable[str], nodes: Iterable[str], *, min_overlap: int = 2
) -> Dict[str, str]:
    """title -> best-overlapping node (≥ ``min_overlap`` significant words)."""
    node_list = list(dict.fromkeys(nodes))
    refs: Dict[str, str] = {}
    for title in titles:
        tw = set(_significant_words(title))
        best: Optional[Tuple[int, str]] = None
        for node in node_list:
            overlap = len(tw & set(_node_tokens(node)))
            if overlap >= min_overlap and (best is None or overlap > best[0]):
                best = (overlap, node)
        if best is not None:
            refs[title] = best[1]
    return refs


# ---------------------------------------------------------------------------
# normalize_feature — classify + WRITE
# ---------------------------------------------------------------------------


@dataclass
class NormalizeResult:
    feature_id: str
    feature_yaml_path: str
    feature_files: List[str]
    stamped: Dict[str, str] = field(default_factory=dict)  # title -> verifier
    test_refs: Dict[str, str] = field(default_factory=dict)  # title -> test_ref
    rules: Dict[str, str] = field(default_factory=dict)  # title -> R-number
    reasons: Dict[str, str] = field(default_factory=dict)  # title -> evidence
    refused: List[str] = field(default_factory=list)
    already_stamped: List[str] = field(default_factory=list)
    written: bool = False
    dry_run: bool = False
    repo_has_http_surface: bool = False
    http_surface_evidence: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature_id": self.feature_id,
            "feature_yaml_path": self.feature_yaml_path,
            "feature_files": list(self.feature_files),
            "stamped": dict(self.stamped),
            "test_refs": dict(self.test_refs),
            "rules": dict(self.rules),
            "reasons": dict(self.reasons),
            "refused": list(self.refused),
            "already_stamped": list(self.already_stamped),
            "written": self.written,
            "dry_run": self.dry_run,
            "repo_has_http_surface": self.repo_has_http_surface,
            "http_surface_evidence": self.http_surface_evidence,
        }


def _load_feature_yaml(feature_yaml_path: Path) -> Dict[str, Any]:
    try:
        data = yaml.safe_load(feature_yaml_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise StampNormalizerError(
            f"stamp normalizer: cannot read feature YAML {feature_yaml_path}: {exc}"
        ) from exc
    if not isinstance(data, dict):
        raise StampNormalizerError(
            f"stamp normalizer: {feature_yaml_path} is not a YAML mapping"
        )
    return data


def normalize_feature(
    feature_yaml_path: Union[str, Path],
    feature_files: Optional[Sequence[str]] = None,
    repo_root: Optional[Union[str, Path]] = None,
    *,
    dry_run: bool = False,
    ignore_existing: bool = False,
    repo_has_http_surface: Optional[bool] = None,
) -> NormalizeResult:
    """Stamp every unstamped scenario of one feature by rule, and WRITE.

    Parameters
    ----------
    feature_yaml_path
        The feature YAML (``.guardkit/features/FEAT-X.yaml``).
    feature_files
        Repo-relative Gherkin paths. ``None`` = the YAML's own
        ``feature_files:``; the universe is explicit, never inferred — with
        neither, this raises :class:`StampNormalizerError`.
    repo_root
        Root the feature files / task docs / manifests resolve against
        (default: the YAML's grand-grandparent, i.e. ``.guardkit/features/..``).
    dry_run
        Classify and report; write nothing.
    ignore_existing
        Classify EVERY title as if unstamped (the reproduction proof).
        Allowed only with ``dry_run=True`` — an existing stamp is never
        overwritten.
    repo_has_http_surface
        Override the manifest/registry detection (CLI ``--http-surface``).

    Raises
    ------
    StampNormalizerRefusal
        One or more titles are undecidable — every one named; nothing written.
    StampNormalizerError
        The normalizer cannot run (no feature files, missing/unreadable file,
        malformed existing stamp, or a write that failed re-verification).
    """
    yaml_path = Path(feature_yaml_path)
    if repo_root is None:
        repo_root = yaml_path.resolve().parent.parent.parent
    root = Path(repo_root)
    if ignore_existing and not dry_run:
        raise StampNormalizerError(
            "stamp normalizer: ignore_existing=True is a dry-run-only mode — "
            "an existing stamp is NEVER overwritten (Rich's condition 1)."
        )

    data = _load_feature_yaml(yaml_path)
    feature_id = str(data.get("id") or yaml_path.stem)

    files: List[str] = list(feature_files) if feature_files else list(data.get("feature_files") or [])
    if not files:
        raise StampNormalizerError(
            f"stamp normalizer: feature {feature_id} declares no `feature_files:` "
            "and none were given — the scenario universe must be explicit, "
            "never inferred (routing law). FIX: list the feature's Gherkin "
            "`.feature` path(s) under `feature_files:` in the YAML."
        )
    if not isinstance(files, list) or not all(isinstance(f, str) and f.strip() for f in files):
        raise StampNormalizerError(
            f"stamp normalizer: feature {feature_id}: `feature_files:` must be a "
            f"list of non-empty repo-relative paths, got {files!r}."
        )

    # Existing stamps — validated (a bogus stamp is loud here, same voice as
    # the loader), never overwritten.
    raw_existing = data.get("scenarios") or {}
    if not isinstance(raw_existing, dict):
        raise StampNormalizerError(
            f"stamp normalizer: feature {feature_id}: `scenarios:` must be a "
            f"mapping of title -> stamp, got {type(raw_existing).__name__}."
        )
    for title, raw in raw_existing.items():
        try:
            parse_scenario_stamp(raw, scenario=str(title))
        except ValueError as exc:
            raise StampNormalizerError(
                f"stamp normalizer: feature {feature_id} carries an invalid "
                f"existing stamp — fix it before normalizing.\n{exc}"
            ) from exc
    existing_titles = set() if ignore_existing else {str(t) for t in raw_existing}

    # The scenario universe: titles + own steps, from the declared files.
    scenarios: List[Tuple[str, str]] = []
    for rel in files:
        path = root / rel
        if not path.exists():
            raise StampNormalizerError(
                f"stamp normalizer: feature {feature_id} declares feature file "
                f"{rel!r}, which does not exist under {root}."
            )
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise StampNormalizerError(
                f"stamp normalizer: feature {feature_id}: {rel!r} is unreadable ({exc})."
            ) from exc
        scenarios.extend(extract_scenarios(text))

    # Context.
    if repo_has_http_surface is None:
        has_http, http_evidence = detect_repo_http_surface(root)
    else:
        has_http, http_evidence = bool(repo_has_http_surface), "override"
    task_paths = [
        root / str(t.get("file_path"))
        for t in (data.get("tasks") or [])
        if isinstance(t, dict) and t.get("file_path")
    ]
    nodes = collect_plan_test_nodes(task_paths)
    titles_in_order = list(dict.fromkeys(t for t, _ in scenarios))
    plan_refs = build_plan_test_refs(titles_in_order, nodes)
    ctx = NormalizeContext(
        repo_has_http_surface=has_http,
        plan_test_refs=plan_refs,
        http_surface_evidence=http_evidence,
    )

    result = NormalizeResult(
        feature_id=feature_id,
        feature_yaml_path=str(yaml_path),
        feature_files=files,
        dry_run=dry_run,
        repo_has_http_surface=has_http,
        http_surface_evidence=http_evidence,
    )

    seen: set = set()
    for title, steps in scenarios:
        if title in seen:
            continue  # duplicate title in the file: first occurrence classifies
        seen.add(title)
        if title in existing_titles:
            result.already_stamped.append(title)
            continue
        home = classify_scenario(title, steps, ctx)
        if home is None:
            result.refused.append(title)
            continue
        result.stamped[title] = home.verifier
        result.rules[title] = home.rule
        result.reasons[title] = f"{home.rule} {home.verifier}: {home.evidence}"
        if home.test_ref:
            result.test_refs[title] = home.test_ref

    if result.refused:
        # REFUSE LOUD — the run stops; NOTHING is written (no partial stamping).
        raise StampNormalizerRefusal(feature_id, result.refused)

    if dry_run or not result.stamped:
        return result

    new_stamps: Dict[str, Dict[str, Any]] = {
        title: Home(
            verifier=result.stamped[title],
            rule=result.rules[title],
            test_ref=result.test_refs.get(title),
        ).to_stamp()
        for title in result.stamped
    }
    write_stamps(
        yaml_path,
        new_stamps,
        feature_files=files if not data.get("feature_files") else None,
    )
    result.written = True
    logger.info(
        "STAMP NORMALIZER: feature %s — %d scenario(s) stamped by rule, "
        "%d already stamped (untouched); wrote %s",
        feature_id,
        len(result.stamped),
        len(result.already_stamped),
        yaml_path,
    )
    return result


# ---------------------------------------------------------------------------
# The writer — a textual splice that keeps the file's comments and order,
# verified by re-parse before it replaces the original
# ---------------------------------------------------------------------------


_TOP_SCENARIOS_RE = re.compile(r"^scenarios:[ \t]*(\{\s*\}|)[ \t]*(#.*)?$", re.MULTILINE)


def _render_entries(stamps: Mapping[str, Mapping[str, Any]], indent: str) -> str:
    lines: List[str] = []
    for title, stamp in stamps.items():
        lines.append(f"{indent}{json.dumps(title, ensure_ascii=False)}:")
        for key, value in stamp.items():
            lines.append(f"{indent}  {key}: {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def _splice_scenarios(
    text: str,
    stamps: Mapping[str, Mapping[str, Any]],
    feature_files: Optional[Sequence[str]],
) -> str:
    """Return the new file text with ``stamps`` appended to the top-level
    ``scenarios:`` block (created at EOF when absent). Comments and every
    other key are left byte-for-byte alone."""
    if not text.endswith("\n"):
        text += "\n"

    if feature_files:
        # The YAML had no feature_files: — write the universe we were given
        # so the loader can enumerate it (explicit, never inferred).
        text += "feature_files:\n" + "".join(
            f"  - {json.dumps(f, ensure_ascii=False)}\n" for f in feature_files
        )

    m = _TOP_SCENARIOS_RE.search(text)
    if m is None:
        return text + "scenarios:\n" + _render_entries(stamps, "  ")

    if m.group(1):  # `scenarios: {}` — replace the flow-empty line with a block
        return (
            text[: m.start()]
            + "scenarios:\n"
            + _render_entries(stamps, "  ")
            + text[m.end():].lstrip("\n")
        )

    # Block form: the block ends at the next column-0 non-blank, non-comment
    # line; new entries go right after the block's last indented line, at
    # the block's own indent.
    lines = text[m.end():].split("\n")  # lines[0] = rest of the `scenarios:` line
    last_block_line = 0
    indent = "  "
    saw_entry = False
    for i in range(1, len(lines)):
        line = lines[i]
        if not line.strip():
            continue
        if line[0] not in (" ", "\t"):
            if line.lstrip().startswith("#"):
                continue  # a column-0 comment inside/after the block
            break
        if not saw_entry:
            indent = line[: len(line) - len(line.lstrip())]
            saw_entry = True
        last_block_line = i
    head = "\n".join(lines[: last_block_line + 1]) + "\n"
    tail = "\n".join(lines[last_block_line + 1:])
    return text[: m.end()] + head + _render_entries(stamps, indent) + tail


def write_stamps(
    feature_yaml_path: Union[str, Path],
    stamps: Mapping[str, Mapping[str, Any]],
    *,
    feature_files: Optional[Sequence[str]] = None,
) -> None:
    """Append ``stamps`` (title -> {verifier[, test_ref]}) to the YAML's
    ``scenarios:`` map. NEVER overwrites an existing title. Comments and key
    order are preserved (textual splice); the result is re-parsed and every
    new stamp verified before the original file is replaced (atomic
    ``os.replace``). A failed verification leaves the original untouched
    and raises.
    """
    yaml_path = Path(feature_yaml_path)
    original = yaml_path.read_text(encoding="utf-8")
    before = yaml.safe_load(original) or {}
    if not isinstance(before, dict):
        raise StampNormalizerError(f"stamp normalizer: {yaml_path} is not a YAML mapping")
    existing = before.get("scenarios") or {}
    collisions = [t for t in stamps if t in existing]
    if collisions:
        raise StampNormalizerError(
            "stamp normalizer: refusing to overwrite existing stamp(s) for: "
            + ", ".join(repr(t) for t in collisions)
        )
    for title, stamp in stamps.items():
        parse_scenario_stamp(dict(stamp), scenario=title)  # closed vocabulary, loud

    new_text = _splice_scenarios(original, stamps, feature_files)

    # Verify by re-parse BEFORE touching the file.
    try:
        after = yaml.safe_load(new_text)
    except yaml.YAMLError as exc:
        raise StampNormalizerError(
            f"stamp normalizer: the stamped YAML for {yaml_path} does not "
            f"re-parse ({exc}); the original file was left untouched."
        ) from exc
    after_scen = (after or {}).get("scenarios") or {}
    for title, stamp in stamps.items():
        got = after_scen.get(title)
        if isinstance(got, str):
            got = {"verifier": got}
        if got != dict(stamp):
            raise StampNormalizerError(
                f"stamp normalizer: re-parse of {yaml_path} does not carry the "
                f"stamp for {title!r} (got {got!r}); the original file was left "
                "untouched."
            )
    for title in existing:
        got = after_scen.get(title)
        if isinstance(got, str):
            got = {"verifier": got}
        want = existing[title] if isinstance(existing[title], dict) else {"verifier": existing[title]}
        if got != want:
            raise StampNormalizerError(
                f"stamp normalizer: existing stamp for {title!r} would change "
                f"({want!r} -> {got!r}); the original file was left untouched."
            )
    # Everything else must be byte-for-byte the same data.
    before_rest = {k: v for k, v in before.items() if k not in ("scenarios", "feature_files")}
    after_rest = {k: v for k, v in (after or {}).items() if k not in ("scenarios", "feature_files")}
    if before_rest != after_rest:
        raise StampNormalizerError(
            f"stamp normalizer: the splice changed data outside `scenarios:` "
            f"in {yaml_path}; the original file was left untouched."
        )

    tmp = yaml_path.with_name(yaml_path.name + ".stamp-normalizer.tmp")
    tmp.write_text(new_text, encoding="utf-8")
    os.replace(tmp, yaml_path)


__all__ = [
    "RULES_DOC",
    "Home",
    "NormalizeContext",
    "NormalizeResult",
    "StampNormalizerError",
    "StampNormalizerRefusal",
    "classify_scenario",
    "extract_scenarios",
    "detect_repo_http_surface",
    "collect_plan_test_nodes",
    "build_plan_test_refs",
    "normalize_feature",
    "write_stamps",
    "R1_DB_UNAVAILABLE",
    "R2_FRESH_START",
    "R3_SMOKE_HARNESS",
    "R4_BUS",
    "R5_FLUTTER",
    "R6_BROWSER",
    "R7_EXAM",
    "R9_WIRE",
    "R10_OPERATOR",
]
