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

Condition 2 as it now stands — THE MODEL FALLBACK (RULED, Rich 2026-08-31,
repair item 11). Condition 2's "no model in the loop" was a v1 condition and
Rich has now ruled the v2 the design always described ("What the model is
asked, when asked", ``RULES_DOC``). The rules still decide everything they
can, and a title a rule decided NEVER goes near a model. Only the titles the
rules REFUSED are handed to one — with the closed list and the rules' own
summary — to answer one word each; the answer is checked against the closed
list and a single bad word rejects the whole answer. Everything else is
unchanged, and every failure (no model configured, unreachable endpoint,
timeout, HTTP error, malformed reply, bogus answer) leaves the titles refused
exactly as before, plus one plain line saying the model could not be asked. A
stamp is never invented. A model-decided stamp is marked as model-decided
everywhere it is recorded (``NormalizeResult.model_stamped``, ``rules[title]
= "model"``, and a comment line above the stamp in the feature YAML) so
nobody can mistake it for a rule-decided one; ``operator`` from the model is
named on the card like any other operator stamp — never silent. The datum for
the ruling: clause (h) was widened for concurrency phrasings on 2026-08-28
and the very next runs still refused "Concurrent requests return the same
7-day data" and "Concurrent deactivation requests are handled idempotently" —
the spec seat's vocabulary outruns a hand-maintained synonym list. The
machinery lives in ``stamp_model_fallback.py``; it attaches at ONE place, the
refusal point in :func:`normalize_feature`.

Condition 1's shadow — ADVISORY DISAGREEMENTS (RULED, Rich 2026-08-18,
drive-19 datum): planning run c585e146 stamped three plain-HTTP scenarios
``verifier: toolchain`` with no ``test_ref`` — legal vocabulary, WRONG home;
the law accepted the vocabulary and, by condition 1, the normalizer skipped
the stamped titles, so the wrong home rode through untouched. Now the
normalizer classifies EVERY title, stamped or not: for an already-stamped
title whose rule-home DIFFERS from the stamp it RECORDS a disagreement
(``NormalizeResult.disagreements`` — title, stamped, rule_home, rule,
evidence), logs a WARNING per title, and the CLI echoes each on stderr ahead
of the JSON. It NEVER overwrites, and the exit code is UNCHANGED (a
disagreement is advisory). A title the rules cannot decide has nothing to
compare — no disagreement. The other half of the same ruling — (3) a bare
``verifier: toolchain`` is REFUSED at load — lives in ``verifier_stamp``.

Why a rule and not a prompt: the first live drive under the routing-law
templates (planning run d5f2e13b) showed the plan-writer READ the closed
vocabulary and emitted ZERO stamps. Prompting harder tunes around a
small-model slip; the estate's doctrine is one rule mints the claim and the
thing claimed.

The rules (evaluated in the order listed under "Ordering" below; first
match wins)
-------------------------------------------------------------------
Inputs per scenario: the scenario's OWN title + Given/When/Then text
(lower-cased; the Background is NOT included — a shared Background line such
as "a throwaway sandboxed environment" would otherwise route every scenario in
the file), the scenario's OWN tags/comments (R10 only), the repo's surface
class (``ctx.repo_has_http_surface`` — STRUCTURAL: a hurl gate, an explicit
``surface: http`` in ``.guardkit/config.yaml``, or an exact web-framework
dependency in pyproject/package.json; never free text — H2), and any test
node the plan already names for the scenario (``ctx.plan_test_refs``).

The 2026-08-16 tightening (verifier findings H1/H2/M1–M4/L1–L3)
----------------------------------------------------------------
An adversarial verifier ran the 08-16 rules over every primary-tree
``.feature`` in the estate and found the two binding conditions HOLD but
several families minted WRONG homes SILENTLY on real prose — exactly what
the law forbids. Each family's comment names its fix; the whole estate is
now pinned as a NEGATIVE CORPUS regression test
(``tests/fixtures/stamp_normalizer/estate_corpus/`` + ``EXPECTED.json``,
``tests/orchestrator/test_stamp_normalizer_estate_corpus.py``): the
per-repo histogram of homes AND the honest refused count are committed, so
any future rule change shows its delta; ``operator`` must equal the
enumerated explicit-human scenarios; hurl must be 0 in every repo without a
hurl gate / declared surface.

R1  DB unavailable / DB down                     → ``probe:process``
R2  fresh start / restart / fresh process — a token NEGATED within three
    words (without | never | no | not | instead of) does not count
                                                 → ``probe:process``
R3  runtime-smoke harness-meta (seeded directly, throwaway env, teardown,
    network posture …; "verdict … reported" only with `smoke` in the same
    scenario, "oracle time budget" only with `smoke|sandbox`)
                                                 → ``probe:process``
R7  the THEN clause judges the MODEL'S OUTPUT (a response | answer |
    narration | extraction | summary judged; the Coach's report | flag |
    detect | penalise verbs; an output score against a bar) — and the
    Given/When does NOT supply the score as data; a bare "decision" never
                                                 → ``exam``
R4  bus PROTOCOL ACTS — a bus VERB + NOUN pair (publish(es|ed) to/on a
    subject | topic | stream, subscribe(s|d) to, heartbeat | registration |
    manifest is sent | published | received, consumer acks | redelivers,
    request-reply on / the reply inbox, a NATS | JetStream connection |
    transport | broker that is opened | lost | unreachable, an envelope
    that is published | delivered | consumed, a message (un)acknowledged,
    deregister); quoted spans are DATA (blanked — a quoted subject literal
    is kept); `nats`/`jetstream` inside a hyphenated / dotted identifier
    (nats-core, nats-py, nats_fleet_pipe.py) never count; a negated act
    ("no … should be published") never counts   → ``probe:bus``
R5  Flutter / device vocabulary                  → ``flutter``
R6  browser vocabulary (and NOT R5 — order)      → ``playwright``
R8  the plan names a test node for this title    → ``toolchain`` + ``test_ref``
R9  STRONG wire markers AND the repo has an HTTP surface → ``hurl``
    (an HTTP verb + "request to" | a /path | "endpoint" in the same step;
    "send(s) a(n) (http) request to"; "status code should be NNN";
    "response body|status|header should" beside a verb or /path;
    "method not allowed"; "content type" — a bare request | response |
    endpoint | json | route | conflict | not-found | rejected NEVER
    suffices alone; a bare path literal never suffices — M1)
    **R9 WIDENING (RULED, Rich 2026-08-17) — THE MACHINE IDIOM**, same
    gate, evaluated after the strong markers: verb+noun pairings in the
    machine's own voice — (a) "the endpoint returns | responds with |
    rejects | reports | serves | answers" · (b) "returns zero | one | N |
    an empty X | the count … when" · (c) "unauthenticated | invalid |
    malformed request(s) … rejected" · (d) "I request the …" / "request(s)
    the (service) uptime | statistics | count | version | time | health |
    user by email | users count" · (e) "the request should succeed | fail |
    be rejected" · (f) "rejected | reported as (a) conflict | invalid |
    not-found | unsupported | not allowed" (only beside a wire noun) ·
    (g) "looking up … should find nothing | not found". Datum: planning
    run 52606651 — the plan-writer's prose IS this idiom; strict R9
    refused 5/6. Still never a bare noun.
R10 explicitly human (an operator follows, done by hand, physical robot,
    runbook evidence, human-executed, human operator, "on the real NAS"
    with NO automation subject in the When/Then, or the @operator-handoff
    tag / `# operator_handoff:` comment)         → ``operator`` (EXPLICIT only)
—   no rule matched                              → **REFUSE LOUD** (``None``)

Ordering (second tightening, 2026-08-16): R1 · R2 · R3 · **R7** · R4 · R5 ·
R6 · R8 · R9 · R10. Rationale (from the design): infrastructure/process
rules (R1–R3) precede wire (R9) because a DB-down scenario also says
"request" — the more specific need wins. Bus (R4) precedes wire because
fleet scenarios say "reply". Exam (R7) precedes toolchain (R8) because a
scenario judging Coach output can also name a test node — the judged quality
is the essential surface. Toolchain (R8) precedes wire (R9) only when a real
test node is named. **Honest change against the 08-15 design doc**
(``RULES_DOC``, which had R4 < R5 < R6 < R7): R7 now runs BEFORE R4 (and so
before R5/R6). The re-verifier found two specialist-agent Coach EXAM
scenarios whose Given quotes "NATS JetStream" landing in probe:bus because
R4 ran first; the same argument the design made for R7-over-R8 applies —
the judged output is the essential surface. On the estate corpus the
R7-before-R5/R6 part moves nothing (no flutter/playwright scenario judges
model output in its Then); it is stated here so nobody has to discover it.

The 2026-08-16 SECOND tightening (re-verifier findings 1–6)
------------------------------------------------------------
A second adversarial pass over the tightened rules found ~40 of 496 minted
stamps still silently mis-homed (8%): (1) R4's bare `\bnats\b`/`\bjetstream\b`
matched package/repo names and quoted data literals, and R4 ran before R7;
(2) R9's LOOSE family minted hurl on ~23 non-wire study-tutor scenarios
('conflict' from a poetry anthology, 'requests' from "serving requests",
'rejected with' in NATS-command titles, 'route' from a port-forward,
'endpoint' from "the embeddings endpoint"); (3) R2 ignored negation
("without restarting"); (4) R3's `verdict .* reported` / `oracle time budget`
were generic; (5) R7's `coach decision should` fired when the score was an
Outline INPUT; (6) forge "The executor stands fleet-memory up on the real
NAS" is done BY THE EXECUTOR. Each fix is named at its rule above and pinned
on the REAL scenario the re-verifier read; the estate corpus was
re-baselined DELIBERATELY (``EXPECTED.json`` + README carry the per-title
"changes vs 8dd28830" list).

Honest divergences from the 2026-08-15 draft's regex families
--------------------------------------------------------------
The draft claimed R1–R10 reproduce api_test's 60 hand stamps except
users-count 7.1–7.3. Running the draft's LITERAL regexes did NOT (41/60);
the first tightening ADDED api_test's loose idioms ("I request the service
X", "the request should succeed", "rejected as …", "created through the
running service", "looking up", "not-found") and reached 57/60. The second
tightening REMOVES them again on the re-verifier's evidence: the same bare
nouns minted hurl on non-wire prose in a real starlette repo, and a rule
that mints on a poetry anthology cannot be the rule that mints on api_test.
After the second tightening the honest number was **32/60** (28 refused, 0
silent). The R9 WIDENING (RULED, Rich 2026-08-17) brings the idiom back as
VERB+NOUN PAIRINGS and THE HONEST NUMBER NOW: **55/60** hand stamps
reproduce, **2 REFUSE** ("created through the running service" and "the
SECOND request should fail" — neither is a ruled phrase), and the **3
users-count hand-toolchain scenarios are the design's NAMED divergence
again** (rule = hurl by the same (d)/(e) idiom that mints hurl on their
hand-hurl neighbour "Requesting a user by id still works alongside the count
route" — indistinguishable by text; R8 wins whenever the plan names the
node; live, an existing stamp is never overwritten). Nothing else diverges.
B70F/FD8D/AE43/D450/TIME/UBEM reproduce whole; 8737/UDBE come back partial
with the one title named. Pinned in
``tests/orchestrator/test_stamp_normalizer.py``; the estate corpus was
re-baselined DELIBERATELY (57 stamps moved, all REFUSED → hurl on the two
surface repos, every one listed by title and phrase in the fixture README).
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

from guardkit.orchestrator.stamp_model_fallback import (
    MODEL_RULE,
    MODEL_STAMP_COMMENT,
    ModelAsker,
    decide_refused_titles,
)
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
    # R9 WIDENING (RULED, Rich 2026-08-17), the one line OUTSIDE R9: the
    # datum feature (planning run 52606651, "Today's User Count Endpoint")
    # writes its DB-down scenario as "Given the user DATA STORE is
    # unavailable" — without this synonym the machine-idiom phrase (a) "the
    # endpoint reports" would mint HURL on a DB-down scenario, exactly the
    # silent divergence the ordering law (R1 before R9) exists to prevent
    # and exactly what api_test's hand stamps call probe:process. "data
    # store" only — a bare "store" (the memory store / the runbook store /
    # the Postgres store's own R1 line above) is NOT widened; the estate
    # corpus moves by zero on this line.
    r"\bdata ?store (is|becomes|goes|remains) (unavailable|down|unreachable)",
    r"\bdb(-| )down\b",
    r"postgres\w* .* (stopped|unreachable|down|unavailable)",
)

# ---------------------------------------------------------------------------
# Negation (2026-08-16 second tightening, re-verifier findings 1 and 3): a
# rule's token that is NEGATED within the same step line is not evidence.
# "resumes at the failed step WITHOUT restarting" is not a restart (R2);
# "NO build-queued request should be published to Forge" is not a publish
# (R4). R2 looks back THREE words (the re-verifier's law: without | never |
# no | not | instead of); R4's act patterns look back over the whole step
# line, because the negation heads the clause ("no command envelope should
# be published"). Other lines of the same scenario can still match.
# ---------------------------------------------------------------------------

_NEGATION_WORD_RE = re.compile(r"\b(?:without|never|no|not|nor|instead of|neither)\b|\bn't\b", re.IGNORECASE)


def _line_of(text: str, pos: int) -> Tuple[str, int]:
    """(the line containing ``pos``, the offset of ``pos`` inside it)."""
    start = text.rfind("\n", 0, pos) + 1
    end = text.find("\n", pos)
    if end == -1:
        end = len(text)
    return text[start:end], pos - start


def _negated_within(text: str, pos: int, words: Optional[int]) -> bool:
    """Is the token at ``pos`` preceded, on its own step line, by a negation
    word — within ``words`` words (``None`` = anywhere earlier on the line)?"""
    line, off = _line_of(text, pos)
    before = line[:off]
    if words is not None:
        tail = re.findall(r"\S+", before)[-words:]
        before = " ".join(tail)
    return bool(_NEGATION_WORD_RE.search(before))


def _first_unnegated_match(
    family: Iterable[re.Pattern[str]], text: str, *, words: Optional[int]
) -> Optional[str]:
    """First match of the family whose token is not negated on its line
    (a negated hit is skipped; the search continues)."""
    for pat in family:
        for m in pat.finditer(text):
            if not _negated_within(text, m.start(), words):
                return m.group(0)
    return None


# R2 — fresh start / restart (census: 2.3, 3.4, 3.8 — process control).
# "an app restart" (the Flutter sign-in feature's device idiom) is NOT a
# process restart — excluded here so R5 sees it. SECOND TIGHTENING (finding
# 3): a restart/start token NEGATED within three words (without | never | no
# | not | instead of) is not a restart — forge runbook-executor "resumes at
# the failed step without restarting" is in-process executor logic (pinned
# negative).
R2_FRESH_START = _family(
    r"\b(just|freshly) started\b",
    r"(?<!\bapp )\brestart(s|ed|ing)?\b",
    r"\bafter (a )?restart\b",
    r"\bfresh (process|instance)\b",
    r"handled no other requests",
)
_R2_NEGATION_WINDOW_WORDS = 3

# R3 — runtime-smoke harness-meta (census: 5.1, 5.3–5.5, 5.9–5.12).
# Additions beyond the draft, each from a census scenario the draft's family
# missed: `seeded directly` generalized (5.5 says "seeded directly and one is
# created"), `smoke (run|verdict)` / `(fails|passes) the smoke` (5.4, 5.9,
# 5.11), `live deployment` (5.11), `before seeding` (5.5), `oracle time
# budget` (5.4). SECOND TIGHTENING (finding 4): `verdict .* reported` is a
# generic idiom (specialist-agent finproxy "the verdict reflects…", guardkit
# "reported as timed out") — it now REQUIRES the word `smoke` in the same
# scenario, and `oracle time budget` requires `smoke` or `sandbox`. Both are
# pinned on the real negatives.
R3_SMOKE_HARNESS = _family(
    r"seeded directly",
    r"before seeding",
    r"\bpsql\b",
    r"throwaway (environment|sandbox)",
    r"\bteardown\b",
    r"no trace .* remain",
    r"network posture",
    r"route to the outside world",
    r"\bsmoke (run|verdict)\b",
    r"\b(fails|passes|failed|passed) the smoke\b",
    r"\blive deployment\b",
)
# The two idioms that need a harness word elsewhere in the scenario.
R3_SMOKE_QUALIFIED = (
    (re.compile(r"verdict .* reported", re.IGNORECASE), re.compile(r"\bsmoke\b", re.IGNORECASE)),
    (re.compile(r"oracle time budget", re.IGNORECASE), re.compile(r"\b(smoke|sandbox\w*)\b", re.IGNORECASE)),
)


def _r3_match(text: str) -> Optional[str]:
    hit = _first_match(R3_SMOKE_HARNESS, text)
    if hit is not None:
        return hit
    for idiom, needs in R3_SMOKE_QUALIFIED:
        m = idiom.search(text)
        if m and needs.search(text):
            return m.group(0)
    return None


# R4 — bus vocabulary (census: 449 bus scenarios estate-wide — forge 182,
# jarvis 115, fleet-memory 65 …). TIGHTENED 2026-08-16 (M4: a bus NOUN was
# required — never bare "acknowledged"/"subscription"; school subjects and
# curriculum topics excluded). SECOND TIGHTENING (re-verifier finding 1):
# the bare nouns `\bnats\b` / `\bjetstream\b` fired on PACKAGE and REPO
# NAMES (nats-core, nats-py, nats_fleet_pipe.py) and on QUOTED DATA
# LITERALS ("NATS JetStream" as a Coach scope input; "Via message broker
# (NATS)" as a user's answer) — so docker-build, stub, MCP-resource and two
# EXAM scenarios landed in probe:bus. The law now:
#   * a bus noun counts only as part of a PROTOCOL ACT — a bus VERB + NOUN
#     pair (publish(es|ed) to/on a subject|topic|stream…, subscribe(s|d) to,
#     heartbeat|registration|manifest is sent|published|received, consumer
#     acks|redelivers, request-reply on, the reply inbox, a NATS|JetStream
#     connection|transport|broker that is opened|lost|unreachable, an
#     envelope that is published|delivered|consumed, a message that is
#     (un)acknowledged, deregister); a NAME alone never does;
#   * quoted spans ("...") are DATA and are blanked before matching — except
#     a quoted NATS subject literal (`fleet.deregister`, `agents.command.x`),
#     which is protocol, not data;
#   * `nats` / `jetstream` inside a hyphenated / dotted / path identifier
#     (nats-core, nats-py, nats_fleet_pipe.py, NATS-unavailable) never count;
#   * an act NEGATED on its step line ("no … should be published") is not
#     an act (see `_negated_within`).
# Every retained pair is backed by a real forge/jarvis/fleet-*/study-tutor
# scenario; every named false positive is a pinned negative.

_ID_L = r"(?<![\w.\-/])"  # not the tail of an identifier / path
_ID_R = r"(?![\w.\-])"  # not the head of one
_NATS = rf"{_ID_L}(?:nats|jetstream){_ID_R}"
_SUBJECT_LITERAL = (
    r"(?:agents|fleet|pipeline|memory|jarvis|forge|topics|tutor|study)"
    r"\.[a-z][a-z0-9_-]*(?:\.[a-z0-9_.*>-]+)*"
)
_SUBJECT_LITERAL_RE = re.compile(rf"^{_SUBJECT_LITERAL}$", re.IGNORECASE)
_R4_QUOTED_RE = re.compile(r'"([^"\n]*)"')
_ARTICLES = (
    r"(?:(?:the|a|an|its|that|this|each|every|their|any|only one|exactly one|a single|no|one|two|three|all|both|"
    r"such|own|same|real|live|local|configured|documented|canonical|wrong|plural-form|singular|terminal|correct|"
    r"expected|wildcard|offending|paused|inbound|queued|published|un-published|corresponding|next|fresh|new|second|"
    r"another|daemon's|default|reachable|running|missed|different|other|first|last|shared|single) )*"
)
# A subject/topic/stream/channel qualified by a bus adjective (never the
# school subject / curriculum topic / stderr stream — M4).
_QUALIFIED_SUBJECT = (
    r"(?:command|reply|dead-letter|lifecycle|pipeline|registration|deregistration|"
    r"heartbeat|fleet|status|approval|manifest|wildcard|documented|dispatch|flat|nats|"
    r"jetstream|bus|chat|gateway|fanout|command-fanout|publish\w*|jarvis|forge|tutor|"
    r"build-queued|build-\w+|results?|inbound|outbound|singular|canonical|plural-form|"
    r"durable|memory|lifecycle event|event|correlation-keyed|escalation|work|planning)"
    r"[- ](?:subjects?|topics?|streams?|channels?|queues?)"
)
# The DESTINATION of a publish (bare subject/topic/stream are fine here —
# nobody "publishes to the school subject").
_PUBLISH_DEST = (
    rf"(?:{_ID_L}(?:subjects?|topics?|streams?|inbox|brokers?|nats|jetstream|fleet|"
    rf"fleet bus|message bus|event bus|fleet registry|wire|bus){_ID_R}|{_QUALIFIED_SUBJECT}|{_SUBJECT_LITERAL})"
)
# The destination/carrier of any other transport act (qualified nouns only —
# "sends a tutoring turn for subject X" is a school subject, pinned negative).
_ACT_DEST = (
    rf"(?:{_ID_L}(?:inbox|brokers?|nats|jetstream|fleet(?! scope)|fleet bus|message bus|event bus|"
    rf"fleet registry){_ID_R}|{_QUALIFIED_SUBJECT}|{_SUBJECT_LITERAL})"
)
_ENVELOPE = r"(?<!verdict )(?<!result )(?<!json )(?<!response )(?<!error )(?<!http )\benvelopes?\b"
_ACK_NOUN = r"(?:message|envelope|payload|dispatch|brief|command|episode|delivery|publish)s?"

R4_BUS = _family(
    # publish / republish TO|ON a bus destination (or a subject literal)
    rf"\b(?:re)?publish(?:es|ed|ing)?\b[^\n]{{0,50}}?\b(?:to|on|onto|over|via|through)\b[^\n]{{0,45}}?{_PUBLISH_DEST}",
    # send / deliver / listen / reply / connect … TO|ON|FROM a bus carrier
    rf"\b(?:sent|sends?|sending|deliver\w*|emits?|emitted|emitting|forward\w*|dispatch\w*|arriv\w*|"
    rf"lands?|landed|listen\w*|receiv\w*|observes?|observed|park\w*|pending|consum\w*|drain\w*|"
    rf"reply|replies|replied|respond\w*|answer\w*|connect\w*|discoverable|routed|redeliver\w*|"
    rf"subscrib\w*|advertis\w*)\b[^\n]{{0,30}}?\b(?:to|on|from|over|via|through|onto|across)\b "
    rf"{_ARTICLES}(?:[\w-]+ )?{_ACT_DEST}",
    # a qualified subject / channel / queue as the object or subject of an act
    rf"\b(?:on|to|from|via|over|onto|of|at|against|into) {_ARTICLES}(?:[\w-]+ )?{_QUALIFIED_SUBJECT}\b",
    rf"\b{_QUALIFIED_SUBJECT} (?:should|is|are|was|were|receives?|carries|carry|pattern|name|names|exists?|the)\b",
    r"\bsubjects? (?:pattern|hierarchy|prefix)\b|\bsubject (?:name|prefix|hierarchy)\b",
    rf"\b(?:{_NATS}|durable|memory|lifecycle event|event) streams? (?:is|are|should be|was|were|exists?|provisioned)\b|"
    r"\bstreams? (?:is|are) provisioned\b",
    # subscribe / subscription / subscriber acts
    r"\bsubscri(?:bes?|bed|bing) (?:to|on|against|for)\b",
    r"\b(?:remains?|stays?|is|are|still|be|been) subscribed\b",
    r"\b(?:attempt\w*|establish\w*|re-establish\w*|open\w*|drop\w*|dropped|restor\w*|hold\w*|keep\w*|"
    r"los\w*|lost|creat\w*|maintain\w*|start\w*|has|have|had|with|without|before|after) "
    r"(?:its |a |the |an |their |own |live |a live |its own )*(?:jetstream |nats |reply |durable |wildcard |"
    r"command |correlation-keyed |one-shot |live |pull |push |single )subscriptions?\b",
    r"\b(?:jetstream|nats|reply|durable|wildcard|command|correlation-keyed|one-shot|live) subscriptions? "
    r"(?:is|are|was|were|should|drops?|dropped|in|against|remains?|stays?|state|poll|to|on)\b",
    r"\b(?:late|early|new|another|a second) subscribers?\b|\bbefore the subscriber started\b|"
    r"\ba subscriber (?:is )?listening\b|\bobserved by a subscriber\b|"
    r"\bthe subscriber should (?:observe|receive|see|remain|continue|stay)\b",
    # heartbeat / registration / deregistration acts (wide verbs — these nouns
    # have no other sense in the estate)
    r"\b(?:heartbeats?|registrations?|deregistrations?) (?:events? |messages? |payloads? )?"
    r"(?:is |are |was |were |should be |should still be |should have been |gets? |get |being |will be |must be |should )?"
    r"(?:sent|published|republished|re-published|received|emitted|delivered|observed|discoverable|missed|"
    r"missing|arrives?|arrived|stops?|stopped|expires?|expired|lapses?|elapses?|replayed|re-emitted)\b",
    r"\b(?:sends?|sent|sending|publish\w*|emit\w*|receiv\w*|miss\w*|expect\w*|stops? sending|observ\w*|"
    r"republish\w*|re-emits?|re-emitted|replays?|replayed) "
    r"(?:a |an |its |the |their |periodic |no |every |each |two |three |one |another |the next |a fresh |"
    r"a new |its own |the same |the missed |any )*(?:fleet |own |agent |periodic |missed )?"
    r"(?:heartbeats?|registrations?|deregistrations?)\b",
    r"\bheartbeat (?:interval|timeout|cadence|period|misses|expir\w*|elapses|is due)\b|\bas a heartbeat\b|"
    r"\bheartbeat[- ]driven\b|\bmissed heartbeats?\b",
    r"\bderegister(?:s|ed|ing)?\b",
    r"\bfleet\.(?:register|deregister|heartbeat|manifest|status)\b",
    r"\b(?:registers?|registered|registering|re-registers?) (?:on|with|itself on|itself with|again on) the fleet\b|"
    r"\b(?:joins?|leaves?|joined|left) the fleet\b|"
    r"\b(?:reachable|available|advertised|discoverable|registered|published|republished|dispatched|dispatch|"
    r"sent|delivered|forwarded|manifests?|heartbeats?|deregisters?|deregistered) (?:on|to|over|through|across|from|with) the fleet\b(?! scope)",
    # the capability MANIFEST — only as published / republished / discoverable
    # (a "context manifest" that is missing is not the fleet — pinned negative)
    r"\b(?:fleet |capability |agent |own |its |its own |jarvis's |the )*manifests? "
    r"(?:is |are |was |were |should be |should still be |should have been |gets? |get |will be |must be |should )?"
    r"(?:published|republished|re-published|discoverable|advertised|received)\b",
    r"\b(?:publish\w*|republish\w*|re-publish\w*|advertis\w*|receiv\w*) (?:a |an |its |the |their |its own |a fresh |a new |the same )*"
    r"(?:fleet |capability |agent |own )?manifests?\b",
    # lifecycle / build / approval traffic — only as TRANSPORTED (published /
    # delivered / received / replayed / arrives …; a guardkit "event emitted"
    # is instrumentation, not the bus — pinned negative)
    r"\b(?:lifecycle events?|build-\w+ events?|runbook-\w+ events?|step-\w+ events?|approval requests?|"
    r"approval repl(?:y|ies)|approval responses?|paused events?|build-queued requests?|planning requests?) "
    r"(?:is |are |was |were |should be |should still be |should have been |gets? |get |being |will be |must be |should |for [\w-]+ )?"
    r"(?:sent|published|republished|re-published|received|delivered|observed|replayed|re-emitted|re-issued|"
    r"arrives?|arrived|missed|redelivered)\b",
    r"\b(?:sends?|sent|sending|publish\w*|receiv\w*|observ\w*|republish\w*|re-emits?|re-emitted|"
    r"re-issues?|re-issued|replays?|replayed|deliver\w*|redeliver\w*|miss\w*|expect\w*) "
    r"(?:a |an |its |the |their |no |every |each |two |three |one |another |the next |a fresh |a new |its own |"
    r"the same |the paused |the missed |any |that |this )*(?:paused |missed |fresh |same |own |runbook-\w+ |step-\w+ |build-\w+ )?"
    r"(?:lifecycle events?|approval requests?|approval repl(?:y|ies)|approval responses?|paused events?|"
    r"build-\w+ events?|build-queued requests?|planning requests?)\b",
    r"\bpublished lifecycle events?\b",
    # consumer / acknowledgement / redelivery acts
    r"\b(?:durable |pull |push |jetstream |nats |queue |relay |the |a |its )?consumers? "
    r"(?:acks?|acknowledg\w*|redeliver\w*|attach\w*|park\w*|pull\w*|poll\w*|keeps? processing|is attached)\b",
    r"\bdurable consumers?\b|\bconsumer[- ]side (?:ack\w*|dedup\w*|redeliver\w*)",
    r"\b(?:pending|parked|remains?|remain|held|redelivered|delivered) (?:on|to|by|for) the "
    r"(?:jetstream |nats |durable |same |next )?consumers?\b",
    rf"\b{_ACK_NOUN} (?:should |is |was |are |were |remain |remains |should remain |gets? |get |must |will |never |not |be |never be |not be |being |been )*"
    r"(?:un)?(?:acknowledged|acked)\b",
    rf"\backnowledg\w* (?:the |its |each |every |that |this )?(?:inbound |queued |same |offending |redelivered )?{_ACK_NOUN}\b",
    r"\bunacknowledged\b|\backed\b|\backs the\b|\backnowledged so the queue\b|\backnowledged on the queue\b|"
    r"\backnowledg\w*[^\n]{0,20}\b(?:jetstream|redeliver\w*)",
    r"\bredeliver(?:y|ed|s|ing|able)?\b[^\n]{0,30}\b(?:message|payload|envelope|consumer|jetstream|nats|build|episode)|"
    r"\b(?:message|payload|envelope|brief|command|build|episode|build-queued \w+)s?\b[^\n]{0,60}\bredeliver",
    r"\b(?:delivery|redelivery) limit\b|\bwithout being acknowledged\b|\bdelivered \w+ times\b",
    # request-reply / inbox
    r"\brequest[- ]reply (?:on|over|via|pattern|round[- ]?trip|exchange|semantics|timeout|call|to|with)\b|"
    r"\b(?:a|the|via|over|using|through|by) request[- ]reply\b",
    r"\breply inbox\b|\b(?:requester|caller|sender)'s inbox\b|\bon (?:the|its|his|her|their|an|a) (?:reply )?inbox\b|"
    r"\binbox subject\b|\bto (?:the|its|their) inbox\b",
    # NATS / JetStream / broker as a protocol OBJECT in an act (never a name)
    rf"\b{_NATS} (?:connections?|transports?|servers?|endpoints?|bus|event bus|brokers?|urls?|"
    rf"subscriptions?|messages?|publish\w*|consumers?|results? topics?|queues?|work queues?|streams?|"
    rf"subjects?|topics?|payloads?|links?|delivery|deliveries|round[- ]?trips?|acknowledg\w*|acks?|acked|"
    rf"credentials?|auth\w*|max message size|message size|size limits?|kv|kv buckets?|buckets?)\b",
    rf"\b{_NATS} (?:will |should |must |would |can )?(?:reject|refuse|accept)s?\b",
    r"\b(?:kv|key-value|agent-registry(?: kv)?) buckets?\b",
    rf"\b(?:{_NATS} |jetstream |message |the |a |an |its |their |each |every |the same |the local |the configured |"
    rf"the documented |the default |a reachable |a real |the real |a live |a running |a single |own |its own )*"
    rf"brokers? (?:is|are|was|were|becomes?|became|remains?|stays?|fails?|failed|acknowledg\w*|refus\w*|goes|went|"
    rf"drops?|dropped|comes|came|restarts?|restarted|should|cannot|can't|could not|has|have|url|urls|"
    rf"unreachable|unavailable|reachable|briefly|being)\b",
    rf"\b(?:reachable|unreachable|real|live|running|available|unavailable|configured|same|shared|local|"
    rf"remote|default|documented|single|briefly unavailable) (?:{_NATS} |jetstream |message )?brokers?\b",
    rf"\b(?:against|to|from|on|via|over|through|with|without) (?:the |a |an |its |their |the same |a real |the real |"
    rf"a live |the live |the local |the configured |the documented |the default )*(?:{_NATS} |jetstream |message )?brokers?\b",
    rf"\b{_NATS} (?:is|are|was|were|becomes?|became|remains?|stays?|goes|went|drops?|dropped|comes back|"
    rf"disconnect\w*|reconnect\w*|fails?|failed|acknowledg\w*|acks?)\b",
    rf"\b(?:published|publish\w*|received|receiv\w*|sent|send\w*|emit\w*|deliver\w*|consum\w*|subscrib\w*|"
    rf"connect\w*|listen\w*|dispatch\w*|forward\w*|arriv\w*|routed|routes?|served|serve\w*|reach\w*|"
    rf"talk\w*|speak\w*|carried|carr\w*|flow\w*|transport\w*|integrat\w*|register\w*|discoverable|"
    rf"round[- ]?trips?|round[- ]?tripped) "
    rf"(?:\w+ ){{0,3}}?(?:to|from|on|over|via|through|onto|across|by|against|with) (?:the |a |an |its |their )?{_NATS}\b",
    rf"\b(?:over|via|through|across|by|on) (?:the |a |an |its |their |the same |a real |the real |a live |the live |"
    rf"the local |the configured )*(?:{_NATS} |fleet |message |event )bus\b",
    r"\b(?:fleet |message |nats |event )?bus (?:acknowledges?|acks?|delivers?|drops?|is unavailable|is unreachable|"
    r"is down|is not configured|becomes? unavailable|goes down|comes back)\b",
    # envelopes ON THE WIRE — published / delivered / consumed / replayed …
    # (never a verdict/result/JSON/response/error/HTTP envelope; never mere
    # construction — fleet-gateway "Building a command envelope from a user
    # message" declares fields and is a pinned negative)
    rf"\b(?:published|delivered|received|consumed|replayed|redelivered|inbound|outbound|queued|missed|"
    rf"in-flight|dispatched|forwarded|emitted) {_ENVELOPE}",
    rf"{_ENVELOPE}[^\n]{{0,25}}?\b(?:should be |is |was |are |were |gets? |get |has been |have been |"
    rf"should have been |will be |must be |should still be |should never be |should not be |should |still |also |never |not |be )*"
    rf"(?:published|delivered|received|consumed|arriv\w*|acknowledged|acked|routed|emitted|forwarded|replayed|"
    rf"produced|observed|dispatched|sent|missed|lands?|landed|lost|dropped|re-published|re-emitted|"
    rf"pending|redelivered|redeliverable|resent|re-sent|in flight|in-flight|reaches?|reached|"
    rf"on the wire|on the bus)\b",
    rf"\b(?:publish\w*|consum\w*|deliver\w*|receiv\w*|emit\w*|forward\w*|route\w*|acknowledg\w*|replay\w*|"
    rf"observ\w*|dispatch\w*|send\w*|sent|miss\w*|produc\w*|drop\w*|dropped|los\w*|lost|resent|re-sent|"
    rf"re-publish\w*|re-emit\w*|redeliver\w*|acks?|acked|await\w*|expect\w*|see|sees|saw|watch\w*) "
    rf"{_ARTICLES}(?:[\w-]+ )?{_ENVELOPE}",
)
_R4_NEGATION_WINDOW_WORDS: Optional[int] = None  # the whole step line before the token


def _r4_view(text: str) -> str:
    """The text R4 reads: quoted DATA literals blanked (a quoted NATS subject
    literal is kept — it is protocol, not data)."""

    def _keep_or_blank(m: re.Match) -> str:
        inner = m.group(1).strip()
        return m.group(0) if _SUBJECT_LITERAL_RE.match(inner) else '"…"'

    return _R4_QUOTED_RE.sub(_keep_or_blank, text)


def _r4_match(text: str) -> Optional[str]:
    return _first_unnegated_match(R4_BUS, _r4_view(text), words=_R4_NEGATION_WINDOW_WORDS)



# R5 — Flutter / device vocabulary (census: the 51 Flutter scenarios —
# sign-in 25, voice 26). TIGHTENED 2026-08-16 (verifier finding M2): "the app
# starts" is GONE (study-tutor's http-app-access-adapter — a wire feature —
# says "the app starts a session on that subject"), "securely stored" is
# GONE (only the noun phrase "secure store/storage" counts), and the
# unexercised widget/emulator additions are GONE ("browser opening" stays:
# the sign-in feature really says "signed in without the browser opening").
# Every pattern kept below is backed by a REAL flutter-keycloak-sign-in /
# flutter-voice-client scenario, read from the estate corpus by title
# (pinned in the tests, one case per pattern). Kept narrower than
# "the app" on purpose: the http adapter says "the app authenticates /
# sends / lists / starts" — those are hurl, not flutter.
R5_FLUTTER = _family(
    r"\bflutter\b",
    r"\bthe app (tells me|returns to the foreground|sits idle|should not crash|"
    r"stops the recording|degrades to text|explains why)\b",
    r"\b(re)?open(s|ed|ing)? the app\b",
    r"\bclose[sd]? the app\b",
    r"\bapp restart\b",
    r"(?<![\w-])tap(s|ped|ping)?\b",  # never "wire-tap"
    r"\bmicrophone (access|permission)\b|\bfrom the microphone\b|\bthe app .* microphone\b",
    r"\bmic button\b",
    r"\b(platform )?secure stor(e|age)\b",
    r"\bon the (family )?device\b",
    r"\bsign-in .* browser",
    r"\bbrowser sign-in\b",
    r"\bbrowser (opening|prompt|redirects back)\b",
    r"\b(home|sign-in) screen\b",
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

# R7 — the THEN-CLAUSE judges the MODEL'S OUTPUT (census: 208 agent-behaviour
# scenarios — specialist-agent 136, guardkit 35, LPA 16, tutor 13).
# TIGHTENED 2026-08-16 (M3): R7 is matched against the scenario's THEN clause
# ONLY and the family is JUDGEMENT-shaped; the "coach score" NOUN and bare
# "narration" never qualify. SECOND TIGHTENING (re-verifier finding 5):
# `coach decision should` fired when the score was a Scenario Outline INPUT
# (study-tutor "Scores at and around the acceptance threshold drive the
# accept-or-revise decision" — deterministic threshold logic). The law now:
#   * the JUDGED SUBJECT must be the model's OUTPUT — a response | answer |
#     explanation | narration | extraction | summary | output judged for
#     quality; the Coach's/Player's own verdict as a judgement VERB (should
#     report | flag | detect | penalise | reject | accept | explain | grade …
#     — never "score", which is scoring plumbing); the Coach's feedback /
#     verdict / reasoning judged (should indicate | be grounded | specific |
#     correct | fair | calibrated); an output score judged against a bar;
#   * a bare (coach|player) `decision` is NOT a judged output — the
#     accept/revise decision is threshold logic;
#   * a scenario whose GIVEN/WHEN supplies the score AS DATA ("Given .*
#     score(s)? (of|at|is) \d", "scores <score>", "the weighted Coach score
#     meets or exceeds the threshold", an Outline with a `score` column)
#     never qualifies — the score is an input, not a judgement of output.
R7_EXAM = _family(
    # the Coach's/Player's judgement, as a VERB about the output — "report /
    # flag / detect / penalise / reject / accept" are Coach/Player verbs only;
    # "the agent should report that it cannot infer a mode" (adaptive-mode-
    # inference) is a CLI reporting an error, not a judgement. "score" is
    # GONE from this list (finproxy "the Coach should score every criterion"
    # is scoring plumbing — pinned negative).
    r"\b(coach|player|tutor|agent) should (not )?(rate|explain|teach|remember|recall|"
    r"grade|mark|judge|assess)\b",
    r"\b(coach|player) should (not )?(report|flag|detect|penali[sz]e|reject|accept|indicate|correct|prefer)\b",
    r"\b(coach|player|tutor|agent) (explains|teaches|recalls|remembers|grades|marks|judges|assesses|rates)\b",
    r"\b(coach|player|tutor|agent) (should )?routes? .* to the expected tool",
    # the Coach's feedback / verdict / reasoning JUDGED (never a bare decision)
    r"\b(coach|player|tutor|agent)('s)? (feedback|verdict|reasoning) (should|is|are|was) "
    r"(not )?(indicate|explain|reference|name|justify|mention|cite|be grounded|be specific|be correct|be fair|"
    r"be calibrated|be helpful|be accurate|grounded|specific|correct|fair|calibrated|helpful|accurate)\b",
    # an OUTPUT score judged against a bar (never a score merely rendered/stored)
    r"\bscores? .* (correctly|as expected|at least 0\.|at most 0\.|below (the )?(acceptance )?threshold|"
    r"above (the )?(acceptance )?threshold)",
    # the output's quality
    r"\b(feedback|response|answer|explanation|narration|output|reply|transcript|summary|extraction)s? "
    r"(is|should be|should still be|remains?|stays?) (grounded|specific|correct|helpful|coherent|accurate|faithful|fair|calibrated)\b",
    r"\bnarration (is|should be|should) (grounded|accurate|reuses?|convey|reflect|explain)",
    r"\bnarration should not (suppress|fabricate)\b",
    r"\btreated as ordinary (spoken )?(question|input|tutoring input|content|text)\b",
    r"\binjection .* (ignored|treated as ordinary)",
    r"\bextract(s|ed|ion)? (correctly|cleanly)\b",
    r"\bflag(ged|s)? .* (correctly|as an? (\w+ )?violation)\b",
)
# The score-as-INPUT exclusion (finding 5): matched against the Given/When
# clause (everything before the first `Then`) and the Examples header.
_R7_SCORE_INPUT_RE = re.compile(
    r"\bscore(s|d)?\b[^\n]{0,40}?(\d\.\d+|\d+(\.\d+)?%|<\w*score\w*>|<\w+>)"  # a numeral / outline placeholder
    r"|\bscores? (of|at|is|meets|exceeds|equals|reaches|falls|stays|remains) (or exceeds |below |above |under |over |at or above |at or below )?"
    r"(the |a |an |its )?(acceptance |coach |weighted |accept |revise |revision )?(threshold|bar|maximum|minimum|floor|ceiling|\d)"
    r"|\bscores <\w+>",
    re.IGNORECASE,
)
_R7_EXAMPLES_SCORE_COLUMN_RE = re.compile(r"^\s*\|[^\n]*\bscores?\b[^\n]*\|", re.IGNORECASE | re.MULTILINE)


def given_when_clause(steps_text: str) -> str:
    """Everything BEFORE the first ``Then`` line — the scenario's Given/When
    (its inputs). Whole text when there is no ``Then``."""
    lines = steps_text.splitlines()
    for i, line in enumerate(lines):
        if _THEN_LINE_RE.match(line):
            return "\n".join(lines[:i])
    return steps_text


def _r7_score_is_an_input(steps_text: str) -> bool:
    """Finding 5: the score is DATA the scenario supplies (a Given/When
    numeral or placeholder, a threshold comparison, an Examples column named
    score) — the Then's 'decision' is threshold logic, not a judged output."""
    gw = given_when_clause(steps_text)
    if _R7_SCORE_INPUT_RE.search(gw):
        return True
    return bool(_R7_EXAMPLES_SCORE_COLUMN_RE.search(steps_text))


def _r7_match(steps_text: str) -> Optional[str]:
    then_text = then_clause(steps_text).lower()
    if not then_text:
        return None
    hit = _first_match(R7_EXAM, then_text)
    if hit is None:
        return None
    if _r7_score_is_an_input(steps_text.lower()):
        return None
    return hit


# R9 — wire-shaped step text (census: 417 HTTP scenarios; api_test's 40).
# Only fires when the repo has an HTTP surface. TIGHTENED 2026-08-16 (M1: a
# path literal counts only beside an HTTP token on the same step line).
# SECOND TIGHTENING (re-verifier finding 2): the LOOSE family (bare request /
# response / endpoint / json / route / conflict / not-found / rejected as|
# with / look up / through the service) is GONE — it minted hurl on ~23
# non-wire study-tutor scenarios ('conflict' from "Power and Conflict
# poetry", 'requests' from "should not begin serving requests", 'rejected
# with' in NATS-command titles, 'route' from "port-forward … route to it",
# 'endpoint' from "the embeddings endpoint"). R9 is now STRONG markers ONLY:
#   * an HTTP verb + "request(s) to" | a /path | "endpoint" in the SAME step;
#   * "send(s) a(n) (http) request to";
#   * "status code (should be|is) NNN" / "NNN status";
#   * "response (status|body|header) (should|is)" — ONLY when the same
#     scenario also names an HTTP verb or a /path;
#   * "method not allowed"; "content type".
# A bare noun (request, response, endpoint, json, route, conflict, not-found,
# rejected) NEVER suffices alone. api_test's hand-hurl idiom "I request the
# service X / the request should succeed" is exactly that bare noun — under
# the law those scenarios REFUSE (loud) rather than mint by a rule that also
# mints on a poetry anthology; the reproduction number is reported honestly
# in the tests, not tuned.
_HTTP_VERB = r"(?:get|post|put|patch|delete|head|options)"
_PATH_LITERAL = r"(?<![\w:])/[a-z][\w\-{}]*(?:/[\w\-{}]+)*"
R9_WIRE_STRONG = _family(
    rf"\b{_HTTP_VERB}\b[^\n]{{0,40}}?\brequests? (?:to|for|against|at)\b",
    rf"\b(?:non-{_HTTP_VERB}|{_HTTP_VERB}) requests?\b",
    rf"\b{_HTTP_VERB}\b[^\n]{{0,60}}?(?:{_PATH_LITERAL}|\bendpoints?\b)",
    r"\bsend(?:s|ing)? (?:a|an|two|three|the|another|each|every|one) (?:\w+ ){0,3}?(?:http )?requests? to\b",
    r"\bstatus code (?:should be|is|of|was|equals?|should equal) \d{3}\b|\b\d{3} status\b|\bstatus \d{3}\b",
    r"\bmethod[- ]not[- ]allowed\b",
    r"\bcontent[- ]type\b",
)
# "response (status|body|header) (should|is)" — a strong marker only when the
# same scenario also names an HTTP verb or a /path.
_R9_RESPONSE_PART_RE = re.compile(
    r"\bresponse (?:status|body|header|headers|code|status code) (?:should|is|are|was|were|must|contains?|includes?)\b",
    re.IGNORECASE,
)
_R9_VERB_OR_PATH_RE = re.compile(rf"\b{_HTTP_VERB} requests?\b|\b{_HTTP_VERB}\b[^\n]{{0,40}}?{_PATH_LITERAL}|{_PATH_LITERAL}", re.IGNORECASE)


# ---------------------------------------------------------------------------
# R9 WIDENING (RULED, Rich 2026-08-17) — THE MACHINE IDIOM sub-family.
#
# This is a WIDENING of R9, not a return of the loose family. Datum: planning
# run 52606651 (api_test, "Today's User Count Endpoint") — the plan-writer's
# spec prose IS the machine idiom and strict R9 refused 5/6 of its
# scenarios ("The endpoint returns the count of users created today" · "The
# endpoint returns zero when no users were created today" · "The endpoint
# returns one when exactly one user was created today" · "Unauthenticated
# requests to the endpoint are rejected" · "The endpoint reports an error
# when the data store is unavailable"); the api_test estate fixture carried
# 28 refusals in the same voice ("I request the service X / the request
# should succeed / rejected as X / not-found / looking up").
#
# The difference from the loose family the second tightening removed: every
# phrase here is a VERB+NOUN PAIRING in the machine's own voice — "the
# endpoint returns", "I request the …", "the request should succeed",
# "rejected as not-found" — never a bare noun. 'conflict' from a poetry
# anthology, 'requests' from "serving requests", 'endpoint' from "the
# embeddings endpoint", 'route' from a port-forward do NOT match any of
# these (pinned on the same real study-tutor scenarios the re-verifier
# read; the estate corpus stays hurl=0 on every non-surface repo — the
# surface gate is unchanged — and study-tutor's movers are listed by title
# in the corpus README).
#
# Same gate as R9 (ctx.repo_has_http_surface), matched over the WHOLE
# scenario text (title + steps, lower-cased), evaluated AFTER the strong
# markers so the evidence string names the strong marker when one exists.
# Rule label: "R9" — the sub-family is R9's, not a new rule; the evidence
# string says "machine idiom (x)" so a reader can tell which phrase minted.
#
# The phrases, each with its letter (the letters are the ruling's):
#   (a) "the endpoint returns | responds with | rejects | reports | serves | answers"
#   (b) "returns zero | one | two | N | an empty/non-empty X | the count/total/
#       number/list/record | no X … when"
#   (c) "unauthenticated | unauthorised | anonymous | invalid | malformed
#       request(s) | submission(s) | call(s) … are | is | should be | gets rejected"
#   (d) "I request the/a/an (service) X" · "request(s|ed|ing) the (service |
#       user(s) ) uptime | statistics | stats | count | version | time | health |
#       user by email | user(s) count"
#   (e) "the request should succeed | fail | be rejected"
#   (f) "rejected | reported as (a) conflict | invalid (input) | not-found |
#       unsupported | not allowed | method not allowed"
#   (g) "looking up | look up | lookup of … should | is find nothing | not
#       found | reported as not found"
# ---------------------------------------------------------------------------
R9_MACHINE_IDIOM: List[Tuple[str, re.Pattern[str]]] = [
    (letter, re.compile(pattern, re.IGNORECASE))
    for letter, pattern in (
        ("a", r"\bthe endpoint (?:returns|responds with|rejects|reports|serves|answers)\b"),
        ("b", r"\breturns? (?:zero|one|two|\d+|an? (?:empty|non-empty) \w+|the (?:count|total|number|list|record)|no \w+) when\b"),
        ("c", r"\b(?:unauthenticated|unauthori[sz]ed|anonymous|invalid|malformed) (?:requests?|submissions?|calls?) [^\n]*(?:are|is|should be|gets?) rejected\b"),
        ("d", r"\bI request (?:the|a|an) (?:service )?\w+"),
        ("d", r"\brequest(?:s|ed|ing)? the (?:service |users? )?(?:uptime|statistics|stats|count|version|time|health|user by email|users? count)\b"),
        ("e", r"\bthe request should (?:succeed|fail|be rejected)\b"),
        ("f", r"\b(?:rejected|reported) as (?:a )?(?:conflict|invalid(?: input)?|not[- ]found|unsupported|not allowed|method not allowed)\b"),
        ("g", r"\b(?:looking up|look up|lookup of) [^\n]*(?:should|is) (?:find nothing|not found|reported as not found)\b"),
        # (h) CONCURRENCY IDIOM (RULED, Rich 2026-08-28, option A): three real
        # refusals across exam sentences 4 and 5 ("Concurrent requests return
        # consistent domain lists", "Concurrent requests to the domains
        # endpoint return consistent results", "Concurrent deactivation
        # requests are handled gracefully") — the spec seat reliably emits one
        # concurrent-X scenario per endpoint and no rule decided them. The
        # wire noun (requests/calls) is part of the phrase itself; a
        # concurrent scenario about files, jobs or writes does not match and
        # still refuses loud. Hurl approximates concurrency with repeated
        # requests — the ruled, stated limitation.
        ("h", r"\bconcurrent (?:\w+ )?(?:requests?|calls?)\b[^\n]*(?:consistent|handled (?:gracefully|safely|correctly|atomically)|succeed|identical|all succeed|exactly one succeeds)"),
        ("h", r"\b(?:simultaneous|parallel) (?:\w+ )?(?:requests?|calls?)\b[^\n]*(?:consistent|handled (?:gracefully|safely|correctly|atomically)|succeed|identical)"),
        # (i) PARAMETER-FILTERING IDIOM (RULED, Rich 2026-08-28, second widening
        # of the day): five real refusals on exam sentence 7 — the spec seat's
        # filtering voice ("returns only/all/no X", "includes/excludes X",
        # "omitting the X parameter", "a minimum count of N") sat outside the
        # 08-16 census. Fires ONLY when a parameter/count/query/wire noun
        # co-occurs in the scenario (see _R9_I_PARAM_NOUN_RE) so a non-wire
        # filtering sentence still refuses loud.
        ("i", r"\b(?:filtering|filtered) \w+[^\n]*(?:returns? (?:only|all|no)\b|meeting the threshold)"),
        ("i", r"\bomitting the \w+ parameter\b[^\n]*returns?"),
        ("i", r"\ba (?:minimum|maximum) \w+ of \d+\b[^\n]*(?:includes?|excludes?|returns?)"),
        ("i", r"\ba very (?:large|small|high|low) (?:minimum|maximum) \w+\b[^\n]*returns?"),
    )
]

_R9_I_PARAM_NOUN_RE = re.compile(
    r"\b(?:parameters?|param|query|count|endpoints?|requests?)\b", re.IGNORECASE
)


# (f) NARROWED on the estate corpus (same sitting): "rejected as invalid" is
# also how a Postgres store refuses an out-of-range write (study-tutor
# "A confidence update outside the valid percentage range is rejected" —
# "the update should be rejected as invalid", no wire in sight). Phrase (f)
# therefore fires ONLY when a wire NOUN co-occurs somewhere in the scenario:
# request(s) | endpoint(s) | submission(s) | user(s) | look(ing) up | lookup.
# api_test's (f) positives all carry one ("Looking up a USER … reported as
# not found", "Creating a USER … rejected as a conflict", "A malformed USER
# SUBMISSION is rejected as invalid"); the store scenario carries none and
# refuses (loud) as before. study-tutor's "A session identifier that does
# not exist is reported as not found" (an http-app-access-adapter scenario)
# also carries none and stays REFUSED — a refusal is never wrong.
_R9_F_WIRE_NOUN_RE = re.compile(
    r"\b(?:requests?|endpoints?|submissions?|users?|looking up|look up|lookup)\b",
    re.IGNORECASE,
)


def _r9_machine_idiom_match(text: str) -> Optional[Tuple[str, str]]:
    """(letter, matched span) of the first machine-idiom phrase that fires,
    else None. Whole-scenario text (title + steps); same-line spans only.
    Phrase (f) additionally needs a wire noun somewhere in the scenario."""
    for letter, pat in R9_MACHINE_IDIOM:
        m = pat.search(text)
        if m:
            if letter == "f" and not _R9_F_WIRE_NOUN_RE.search(text):
                continue
            if letter == "i" and not _R9_I_PARAM_NOUN_RE.search(text):
                continue
            return letter, m.group(0)
    return None


def _r9_match(text: str) -> Optional[str]:
    hit = _first_match(R9_WIRE_STRONG, text)
    if hit is not None:
        return hit
    m = _R9_RESPONSE_PART_RE.search(text)
    if m and _R9_VERB_OR_PATH_RE.search(text):
        return m.group(0)
    return None


# The path-literal marker (M1): counts ONLY on a step line that also carries
# one of these HTTP-shaped tokens.
_R9_PATH_LITERAL_RE = re.compile(r"(?<![\w:])/[a-z][\w\-{}]*(/[\w\-{}]+)*", re.IGNORECASE)
_R9_HTTP_TOKEN_RE = re.compile(
    r"\b(request|requests|response|responses|status|endpoint|endpoints|method|"
    r"get|post|put|delete|patch|options|head|json body|json)\b",
    re.IGNORECASE,
)


def _r9_path_with_http_token(text: str) -> Optional[str]:
    """M1: a path literal is wire-shaped only beside an HTTP token on the
    same step line. Returns the evidence string or None."""
    for line in text.splitlines():
        pm = _R9_PATH_LITERAL_RE.search(line)
        if pm and _R9_HTTP_TOKEN_RE.search(line):
            return pm.group(0)
    return None



# R10 — EXPLICITLY human (census: the 3 unclassifiable + operator-handoff
# tagged scenarios). Explicit match ONLY — never a fallback.
# TIGHTENED 2026-08-16 (verifier finding H1): the 08-15 family fired on
# `attended` (a MODE word — jarvis/forge say "attended session/tools/
# profile/build"), on "the operator runs|reads|inspects|checks" (CLI-persona
# prose in specialist-agent/forge) and on bare "robot" (the reachy voice
# scenarios: software behaviour, not human work) — 115 estate hits, none
# genuinely human. Those are GONE. What remains is human WORK, explicitly:
# "an operator follows", an act done "by hand" (a work verb — "traced by
# hand" is a rationale, not work), "physical robot|device", "on the real
# NAS", "runbook evidence", "human-executed", "human operator" — plus the
# @operator-handoff TAG / `# operator_handoff:` comment, matched against the
# scenario's ANNOTATIONS (tags + comments), which are fed to R10 and to no
# other rule.
# SECOND TIGHTENING (re-verifier finding 6): "on the real NAS" is human work
# only when NO AUTOMATION SUBJECT does the work in the When/Then — forge
# "The executor stands fleet-memory up on the real NAS" asserts the stand-up
# was "performed by the executor rather than a manual deploy script"; that
# scenario is undecidable by rule and now REFUSES (pinned negative).
R10_OPERATOR = _family(
    r"\ban operator follows\b",
    r"\b(performed|executed|done|run|verified|checked|proven|confirmed|applied|deployed|"
    r"installed|configured|provisioned|completed|walked|rotated|carried out|stood up|driven|"
    r"signed off|inspected|recorded) by hand\b",
    r"\bphysical (robot|device)\b",
    r"\brunbook evidence\b",
    r"\bhuman[- ]executed\b",
    r"\bhuman[- ]operator\b",
)
_R10_REAL_NAS_RE = re.compile(r"\bon the real nas\b", re.IGNORECASE)
_R10_AUTOMATION_SUBJECT_RE = re.compile(
    r"\b(the executor|an executor|runbook run|runbook executor|script|scripts|forge|the daemon|the pipeline|"
    r"the runner|automation|automated|automatically|the agent|the bot|jarvis)\b",
    re.IGNORECASE,
)

# R10's annotation channel: the @operator-handoff tag or a
# `# operator_handoff:` comment on the scenario.
R10_OPERATOR_ANNOTATIONS = _family(
    r"(?<![\w-])@operator[-_]handoff\b",
    r"^\s*#\s*operator[-_]handoff\s*:",
)


def when_then_clause(steps_text: str) -> str:
    """The first ``When`` line and everything after it (the acts and the
    assertions); the whole text when there is no ``When``."""
    lines = steps_text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r"^\s*when\b", line, re.IGNORECASE):
            return "\n".join(lines[i:])
    return steps_text


def _r10_match(text: str, steps_text: str, annotations: str) -> Optional[str]:
    hit = _first_match(R10_OPERATOR, text)
    if hit is not None:
        return hit
    m = _R10_REAL_NAS_RE.search(text)
    if m and not _R10_AUTOMATION_SUBJECT_RE.search(when_then_clause(steps_text)):
        return m.group(0)
    if annotations:
        hit = _first_match(R10_OPERATOR_ANNOTATIONS, annotations.lower())
        if hit is not None:
            return hit
    return None


def _first_match(family: Iterable[re.Pattern[str]], text: str) -> Optional[str]:
    for pat in family:
        m = pat.search(text)
        if m:
            return m.group(0)
    return None


_THEN_LINE_RE = re.compile(r"^\s*then\b", re.IGNORECASE)


def then_clause(steps_text: str) -> str:
    """The scenario's THEN clause: the first ``Then`` line and every line
    after it (its ``And``/``But`` continuations, Examples rows). Empty when
    the scenario has no ``Then``. R7 reads ONLY this (finding M3)."""
    lines = steps_text.splitlines()
    for i, line in enumerate(lines):
        if _THEN_LINE_RE.match(line):
            return "\n".join(lines[i:])
    return ""


def classify_scenario(
    title: str,
    steps_text: str,
    ctx: Union[NormalizeContext, Mapping[str, Any], None] = None,
    *,
    annotations: str = "",
) -> Optional[Home]:
    """Apply the rules in order to one scenario; ``None`` = undecidable.

    Order (second tightening, 2026-08-16): R1 · R2 · R3 · **R7** · R4 · R5 ·
    R6 · R8 · R9 · R10. R7 (the Then judges the model's output) now runs
    BEFORE R4 (bus): a Coach EXAM scenario that names a bus product in its
    Given ("a scope input naming … NATS JetStream") is an exam, not a bus
    probe — the judged output is the essential surface, exactly as the design
    already argued for R7-over-R8. This is an honest ordering change against
    the 08-15 design doc (which had R4 < R5 < R6 < R7); it is documented in
    the module docstring.

    Pure: no I/O, no logging. ``steps_text`` is the scenario's OWN
    Given/When/Then text (Background excluded — see the module docstring).
    ``annotations`` is the scenario's OWN tag + comment lines (the
    ``@…`` lines and ``# …`` lines directly above the title and inside its
    body) — read by R10 ONLY (the ``@operator-handoff`` tag /
    ``# operator_handoff:`` comment); no other rule sees them.
    ``None`` means REFUSE — the caller must never map it to a home.
    """
    context = _coerce_ctx(ctx)
    text = f"{title}\n{steps_text}".lower()

    # R1 — DB unavailable.
    hit = _first_match(R1_DB_UNAVAILABLE, text)
    if hit is not None:
        return Home(verifier="probe:process", rule="R1", evidence=hit.strip())

    # R2 — fresh start / restart (negation within three words rejects — finding 3).
    hit = _first_unnegated_match(R2_FRESH_START, text, words=_R2_NEGATION_WINDOW_WORDS)
    if hit is not None:
        return Home(verifier="probe:process", rule="R2", evidence=hit.strip())

    # R3 — runtime-smoke harness-meta (the two generic idioms need `smoke`).
    hit = _r3_match(text)
    if hit is not None:
        return Home(verifier="probe:process", rule="R3", evidence=hit.strip())

    # R7 — the THEN clause judges the model's OUTPUT (M3: Then-clause only;
    # finding 5: a score supplied as Given/When data never qualifies).
    # BEFORE R4 (finding 1: an exam that names a bus product is an exam).
    hit = _r7_match(steps_text)
    if hit is not None:
        return Home(verifier="exam", rule="R7", evidence=hit.strip())

    # R4 — bus PROTOCOL ACTS (verb+noun pairs; quotes blanked; identifiers
    # and negated acts excluded — finding 1).
    hit = _r4_match(text)
    if hit is not None:
        return Home(verifier="probe:bus", rule="R4", evidence=hit.strip())

    # R5 / R6 — device / browser vocabulary (R5 before R6, unchanged).
    for rule, verifier, family in (("R5", "flutter", R5_FLUTTER), ("R6", "playwright", R6_BROWSER)):
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

    # R9 — STRONG wire markers AND the repo has an HTTP surface (finding 2).
    if context.repo_has_http_surface:
        why = context.http_surface_evidence or "repo has an HTTP surface"
        hit = _r9_match(text) or _r9_path_with_http_token(text)
        if hit is not None:
            return Home(
                verifier="hurl", rule="R9", evidence=f"{hit.strip()} ({why})"
            )
        # R9 WIDENING (RULED, Rich 2026-08-17): the machine idiom — verb+noun
        # pairings in the machine's own voice, after the strong markers.
        idiom = _r9_machine_idiom_match(text)
        if idiom is not None:
            letter, span = idiom
            return Home(
                verifier="hurl", rule="R9",
                evidence=f"{span.strip()} (machine idiom ({letter}); {why})",
            )

    # R10 — explicitly human. EXPLICIT match only; never a fallback. The
    # annotations (tags/comments) are R10's second channel (H1); "on the
    # real NAS" needs no automation subject in the When/Then (finding 6).
    hit = _r10_match(text, steps_text.lower(), annotations)
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


@dataclass(frozen=True)
class ScenarioBlock:
    """One scenario as the rules see it: its title, its OWN steps, and its
    OWN annotations (tags + comments — fed to R10 only)."""

    title: str
    steps_text: str
    annotations: str = ""


def _is_annotation(line: str) -> bool:
    return line.startswith("#") or line.startswith("@")


def extract_scenario_blocks(feature_text: str) -> List[ScenarioBlock]:
    """``[ScenarioBlock, …]`` in file order (duplicates kept).

    Titles come from the same ``_SCENARIO_LINE_RE`` as
    ``extract_scenario_titles`` (asserted equal). ``steps_text`` is every
    non-blank, non-comment (``#``), non-tag (``@``) line between this
    scenario's title line and the next scenario/``Rule:`` line — the
    scenario's OWN steps and Examples rows, never the Background.
    ``annotations`` is the contiguous run of tag/comment lines directly
    ABOVE the title (Gherkin's own tag placement) plus any comment/tag lines
    INSIDE the body — R10's tag channel (``@operator-handoff`` /
    ``# operator_handoff:``); no other rule reads them.
    """
    matches = list(_SCENARIO_LINE_RE.finditer(feature_text))
    blocks: List[ScenarioBlock] = []
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(feature_text)
        body_lines: List[str] = []
        body_annotations: List[str] = []
        pending_annotations: List[str] = []
        for raw in feature_text[start:end].splitlines():
            line = raw.strip()
            if not line:
                continue
            if _is_annotation(line):
                # Held until a step follows it: the trailing run of tag/
                # comment lines before the NEXT title is that scenario's
                # preamble, not this scenario's body.
                pending_annotations.append(line)
                continue
            if _KEYWORD_LINE_RE.match(line):
                # A `Rule:` (or a stray Feature/Background) closes the block.
                break
            body_annotations.extend(pending_annotations)
            pending_annotations = []
            body_lines.append(line)
        # The preamble: the contiguous tag/comment lines directly above the
        # title (blank lines allowed inside the run).
        preamble: List[str] = []
        for raw in reversed(feature_text[: m.start()].splitlines()):
            line = raw.strip()
            if not line:
                continue
            if _is_annotation(line):
                preamble.append(line)
                continue
            break
        preamble.reverse()
        blocks.append(
            ScenarioBlock(
                title=m.group("title"),
                steps_text="\n".join(body_lines),
                annotations="\n".join(preamble + body_annotations),
            )
        )

    titles = [b.title for b in blocks]
    if titles != extract_scenario_titles(feature_text):  # pragma: no cover — same regex
        raise StampNormalizerError(
            "internal: extract_scenario_blocks and extract_scenario_titles disagree"
        )
    return blocks


def extract_scenarios(feature_text: str) -> List[Tuple[str, str]]:
    """``[(title, steps_text), …]`` — :func:`extract_scenario_blocks` minus
    the annotations (kept for callers that need only text)."""
    return [(b.title, b.steps_text) for b in extract_scenario_blocks(feature_text)]


# ---------------------------------------------------------------------------
# Context builders: HTTP surface, plan test refs
# ---------------------------------------------------------------------------


# H2 (2026-08-16): the surface flag comes from STRUCTURE, never free text.
# The 08-15 detector word-matched framework names anywhere in a manifest's
# text — comments included — so forge/jarvis (a pyproject comment saying
# "next") read as HTTP and R9 minted hurl on hundreds of machinery scenarios.
# Three doors now, each structural:
#   (a) a hurl-twins gate in qa/gates/registry.yaml (id or path says "hurl");
#   (b) an explicit `surface: http` key in .guardkit/config.yaml (documented
#       below — a string, or a list containing "http");
#   (c) an EXACT package name under pyproject `[project] dependencies` /
#       `[tool.poetry.dependencies]` or package.json `dependencies` — parsed
#       as TOML/JSON, never grepped. Comments never count. requirements*.txt,
#       go.mod, Cargo.toml and *.csproj are NOT read (guardkit's own
#       requirements.txt carries a legacy fastapi pin for a demo tree, and
#       lpa-platform-poc's requirements.poc.txt is its only manifest — that
#       repo declares `surface: http` (door b) or grows a hurl gate (door a)).
_WEB_FRAMEWORKS_PY = frozenset({
    "fastapi", "flask", "django", "starlette", "aiohttp", "litestar",
    "sanic", "tornado", "quart", "falcon", "bottle",
})
_WEB_FRAMEWORKS_NODE = frozenset({
    "express", "fastify", "koa", "@hapi/hapi", "hapi", "next", "@nestjs/core",
    "hono", "restify", "@sveltejs/kit", "nuxt",
})

SURFACE_CONFIG_KEY = "surface"
SURFACE_HTTP = "http"

_PEP508_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def _normalize_py_dep(spec: str) -> str:
    """'FastAPI[all]>=0.100 ; python_version>"3.9"' -> 'fastapi'."""
    m = _PEP508_NAME_RE.match(spec)
    return m.group(1).lower().replace("_", "-") if m else ""


def _read_toml(path: Path) -> Dict[str, Any]:
    try:
        import tomllib  # py311+
    except ModuleNotFoundError:  # pragma: no cover
        import tomli as tomllib  # type: ignore
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001 — a broken manifest never crashes classification
        logger.warning("stamp normalizer: could not parse %s: %s", path, exc)
        return {}
    return data if isinstance(data, dict) else {}


def _pyproject_web_framework(root: Path) -> Optional[str]:
    """Door (c), Python: an exact web-framework name under
    ``[project] dependencies`` or ``[tool.poetry.dependencies]``."""
    path = root / "pyproject.toml"
    if not path.exists():
        return None
    data = _read_toml(path)
    names: List[str] = []
    project_deps = (data.get("project") or {}).get("dependencies") or []
    if isinstance(project_deps, list):
        names.extend(_normalize_py_dep(str(d)) for d in project_deps)
    poetry_deps = ((data.get("tool") or {}).get("poetry") or {}).get("dependencies") or {}
    if isinstance(poetry_deps, dict):
        names.extend(str(k).lower().replace("_", "-") for k in poetry_deps)
    for name in names:
        if name in _WEB_FRAMEWORKS_PY:
            return name
    return None


def _package_json_web_framework(root: Path) -> Optional[str]:
    """Door (c), Node: an exact package name under package.json
    ``dependencies`` (not devDependencies)."""
    path = root / "package.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as exc:  # noqa: BLE001
        logger.warning("stamp normalizer: could not parse %s: %s", path, exc)
        return None
    deps = data.get("dependencies") if isinstance(data, dict) else None
    if not isinstance(deps, dict):
        return None
    for name in deps:
        if str(name).lower() in _WEB_FRAMEWORKS_NODE:
            return str(name)
    return None


def _config_declares_http_surface(root: Path) -> bool:
    """Door (b): ``surface: http`` (string, or a list containing ``http``)
    at the top level of ``.guardkit/config.yaml``."""
    path = root / ".guardkit" / "config.yaml"
    if not path.exists():
        return False
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning("stamp normalizer: could not read %s: %s", path, exc)
        return False
    if not isinstance(data, dict):
        return False
    value = data.get(SURFACE_CONFIG_KEY)
    if isinstance(value, str):
        return value.strip().lower() == SURFACE_HTTP
    if isinstance(value, (list, tuple)):
        return any(isinstance(v, str) and v.strip().lower() == SURFACE_HTTP for v in value)
    return False


def detect_repo_http_surface(repo_root: Path) -> Tuple[bool, str]:
    """(has_surface, evidence). Three STRUCTURAL doors, any suffices:

    * ``qa/gates/registry.yaml`` names a gate whose id or path says ``hurl``
      (the hurl-twins gate — the wire class already has a runner here);
    * ``.guardkit/config.yaml`` declares ``surface: http`` (explicit — the
      door for a repo whose manifests are not read, e.g. requirements-only);
    * an EXACT web-framework package name under pyproject
      ``[project] dependencies`` / ``[tool.poetry.dependencies]`` or
      package.json ``dependencies`` — structural parse, never free text.
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

    if _config_declares_http_surface(root):
        return True, ".guardkit/config.yaml declares surface: http"

    fw = _pyproject_web_framework(root)
    if fw:
        return True, f"pyproject.toml [project]/[tool.poetry] dependencies declare {fw}"
    fw = _package_json_web_framework(root)
    if fw:
        return True, f"package.json dependencies declare {fw}"
    return False, (
        "no hurl gate in qa/gates/registry.yaml, no `surface: http` in "
        ".guardkit/config.yaml, and no web framework in pyproject/package.json dependencies"
    )


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
        except OSError as exc:
            # L2: never swallowed silently — a missing task doc means R8 has
            # one fewer node to pin, which is a fact the operator should see.
            logger.warning(
                "stamp normalizer: plan task doc %s could not be read (%s) — "
                "its test_ref / test nodes are NOT available to R8",
                path,
                exc,
            )
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
    # L3: every RULE-MINTED operator stamp, named — never silent (a rule
    # that mints `operator` hands Rich a chore; the JSON and the human echo
    # both say so).
    operator_stamped: List[str] = field(default_factory=list)
    # THE MODEL FALLBACK (RULED 2026-08-31): every title the MODEL decided
    # after the rules refused it — provenance, so a model-decided stamp is
    # never mistaken for a rule-decided one. `rules[title]` for these titles
    # is "model", never an R-number, and the YAML carries a comment above
    # the stamp saying the same thing.
    model_stamped: List[str] = field(default_factory=list)
    # (2) RULED 2026-08-18: ADVISORY disagreements — already-stamped titles
    # the rules would home DIFFERENTLY. Each entry: {title, stamped,
    # rule_home, rule, evidence}. Recorded, warned, echoed — NEVER written
    # (condition 1 stands) and never an exit code (advisory).
    disagreements: List[Dict[str, str]] = field(default_factory=list)
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
            "operator_stamped": list(self.operator_stamped),
            "model_stamped": list(self.model_stamped),
            "disagreements": [dict(d) for d in self.disagreements],
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
    ask_model: Optional[ModelAsker] = None,
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
    ask_model
        THE MODEL FALLBACK's call — ``(prompt) -> answer text``. Default
        ``None`` builds it from the environment (``GUARDKIT_STAMP_MODEL_URL``
        / ``OPENAI_BASE_URL``; see ``stamp_model_fallback``), and with no
        endpoint configured the model is never asked and the refusal stands.
        Tests inject a fake so nothing reaches the network.

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
    existing_stamps: Dict[str, str] = {}  # title -> stamped verifier
    for title, raw in raw_existing.items():
        try:
            existing_stamps[str(title)] = parse_scenario_stamp(
                raw, scenario=str(title)
            ).verifier
        except ValueError as exc:
            raise StampNormalizerError(
                f"stamp normalizer: feature {feature_id} carries an invalid "
                f"existing stamp — fix it before normalizing.\n{exc}"
            ) from exc
    existing_titles = set() if ignore_existing else set(existing_stamps)

    # The scenario universe: titles + own steps + own annotations, from the
    # declared files.
    scenarios: List[ScenarioBlock] = []
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
        scenarios.extend(extract_scenario_blocks(text))

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
    titles_in_order = list(dict.fromkeys(b.title for b in scenarios))
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
    for block in scenarios:
        title = block.title
        if title in seen:
            continue  # duplicate title in the file: first occurrence classifies
        seen.add(title)
        if title in existing_titles:
            result.already_stamped.append(title)
            # (2) RULED 2026-08-18: still CLASSIFY the stamped title; a
            # rule-home that DIFFERS is recorded as an ADVISORY disagreement.
            # Never overwritten (condition 1); undecidable = nothing to
            # compare = no disagreement.
            rule_home = classify_scenario(
                title, block.steps_text, ctx, annotations=block.annotations
            )
            stamped = existing_stamps[title]
            if rule_home is not None and rule_home.verifier != stamped:
                result.disagreements.append(
                    {
                        "title": title,
                        "stamped": stamped,
                        "rule_home": rule_home.verifier,
                        "rule": rule_home.rule,
                        "evidence": rule_home.evidence,
                    }
                )
                logger.warning(
                    "STAMP NORMALIZER: feature %s — stamp DISAGREEMENT "
                    "(advisory, not overwritten): %r is stamped %s but the "
                    "rules say %s (%s: %s)",
                    feature_id,
                    title,
                    stamped,
                    rule_home.verifier,
                    rule_home.rule,
                    rule_home.evidence,
                )
            continue
        home = classify_scenario(title, block.steps_text, ctx, annotations=block.annotations)
        if home is None:
            result.refused.append(title)
            continue
        result.stamped[title] = home.verifier
        result.rules[title] = home.rule
        result.reasons[title] = f"{home.rule} {home.verifier}: {home.evidence}"
        if home.test_ref:
            result.test_refs[title] = home.test_ref
        if home.verifier == "operator":
            result.operator_stamped.append(title)

    # THE MODEL FALLBACK (RULED, Rich 2026-08-31 — repair item 11). THE ONLY
    # place a model touches the routing law, and it attaches HERE, at the
    # refusal point: exactly the titles no rule could decide are handed to a
    # model with the closed list and the rules' own summary; a title a rule
    # decided never goes near it. The answer is checked against the closed
    # list, all or nothing. Every failure — no model configured, unreachable,
    # timed out, an HTTP error, a malformed reply, a bogus answer — returns
    # nothing here, which leaves the refusal exactly as the rules left it,
    # plus one plain line saying the model could not be asked. A stamp is
    # never invented.
    if result.refused:
        decided_by_model = decide_refused_titles(
            result.refused, ask_model=ask_model, feature_id=feature_id
        )
        for title in list(result.refused):
            verifier = decided_by_model.get(title)
            if verifier is None:
                continue
            result.refused.remove(title)
            result.stamped[title] = verifier
            result.rules[title] = MODEL_RULE
            result.reasons[title] = (
                f"{MODEL_RULE} {verifier}: no rule (R1-R10) matched this title, "
                "so the model decided it"
            )
            result.model_stamped.append(title)
            if verifier == "operator":
                result.operator_stamped.append(title)
        if result.model_stamped:
            # Never silent: the model's decisions are named, with the word it
            # chose, in the same voice as every other line here.
            logger.warning(
                "STAMP NORMALIZER: feature %s — the model decided %d scenario(s) "
                "no rule could decide: %s",
                feature_id,
                len(result.model_stamped),
                "; ".join(
                    f"{title} -> {result.stamped[title]}"
                    for title in result.model_stamped
                ),
            )

    if result.operator_stamped:
        # L3: an operator stamp is NEVER silent — by rule (R10) or, since
        # 2026-08-31, from the model. Each title says which decided it.
        logger.warning(
            "STAMP NORMALIZER: feature %s — `operator` (attended human work) "
            "was stamped for %d scenario(s): %s",
            feature_id,
            len(result.operator_stamped),
            "; ".join(
                f"{title} (decided by the model)"
                if title in result.model_stamped
                else f"{title} (R10)"
                for title in result.operator_stamped
            ),
        )

    # Coordinator review 2026-08-16 (pairs with the forge hook's condition 5):
    # the normalizer's law is ONLY "never invent a home, never overwrite,
    # refuse the undecidable BY NAME". It WRITES every DECIDED stamp (a
    # correctly stamped subset is strictly more truth than an empty map; each
    # written stamp carries its rule in the receipt, so nothing is silent) and
    # RETURNS the refused list. The DECISION to stop or proceed on a partial
    # result belongs to the CALLER (forge hook: enforced → stop with the card;
    # not enforced → proceed with a plain line). Refusals are still LOUD:
    # logged here by name, and surfaced by the CLI as a distinct exit code.
    if result.refused:
        logger.warning(
            "STAMP NORMALIZER: feature %s — %d scenario(s) UNDECIDABLE by rule "
            "(no home invented, none written for these): %s",
            feature_id,
            len(result.refused),
            "; ".join(result.refused),
        )

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
        # Provenance in the file itself: a model-decided stamp carries a
        # comment saying so; a rule-decided stamp keeps exactly today's shape.
        comments={title: MODEL_STAMP_COMMENT for title in result.model_stamped},
    )
    result.written = True
    logger.info(
        "STAMP NORMALIZER: feature %s — %d scenario(s) stamped by rule, "
        "%d already stamped (untouched; %d advisory disagreement(s)); wrote %s",
        feature_id,
        len(result.stamped),
        len(result.already_stamped),
        len(result.disagreements),
        yaml_path,
    )
    return result


# ---------------------------------------------------------------------------
# The writer — a textual splice that keeps the file's comments and order,
# verified by re-parse before it replaces the original
# ---------------------------------------------------------------------------


# L1: `scenarios:` bare, or with an EMPTY value in any YAML spelling —
# `{}`, `[]`, `null`, `~` — is the block to fill; never a second key.
_TOP_SCENARIOS_RE = re.compile(
    r"^scenarios:[ \t]*(\{\s*\}|\[\s*\]|null|~|)[ \t]*(#.*)?$", re.MULTILINE | re.IGNORECASE
)


def _render_entries(
    stamps: Mapping[str, Mapping[str, Any]],
    indent: str,
    comments: Optional[Mapping[str, str]] = None,
) -> str:
    lines: List[str] = []
    for title, stamp in stamps.items():
        note = (comments or {}).get(title)
        if note:
            # One comment line above the entry (YAML data is untouched — this
            # is how a model-decided stamp says so in the file itself).
            lines.append(f"{indent}{note}")
        lines.append(f"{indent}{json.dumps(title, ensure_ascii=False)}:")
        for key, value in stamp.items():
            lines.append(f"{indent}  {key}: {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def _splice_scenarios(
    text: str,
    stamps: Mapping[str, Mapping[str, Any]],
    feature_files: Optional[Sequence[str]],
    comments: Optional[Mapping[str, str]] = None,
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
        return text + "scenarios:\n" + _render_entries(stamps, "  ", comments)

    if m.group(1):  # `scenarios: {}` / `[]` / `null` / `~` — replace the empty-value line with a block
        return (
            text[: m.start()]
            + "scenarios:\n"
            + _render_entries(stamps, "  ", comments)
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
    return text[: m.end()] + head + _render_entries(stamps, indent, comments) + tail


def write_stamps(
    feature_yaml_path: Union[str, Path],
    stamps: Mapping[str, Mapping[str, Any]],
    *,
    feature_files: Optional[Sequence[str]] = None,
    comments: Optional[Mapping[str, str]] = None,
) -> None:
    """Append ``stamps`` (title -> {verifier[, test_ref]}) to the YAML's
    ``scenarios:`` map. NEVER overwrites an existing title. Comments and key
    order are preserved (textual splice); the result is re-parsed and every
    new stamp verified before the original file is replaced (atomic
    ``os.replace``). A failed verification leaves the original untouched
    and raises.

    ``comments`` (title -> one comment line) writes that line above the
    title's entry — how a model-decided stamp says so in the file itself. It
    is a comment, so the YAML data is identical either way, and a
    rule-decided stamp (no comment) keeps exactly the shape it has today.
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
        try:
            parse_scenario_stamp(dict(stamp), scenario=title)  # closed vocabulary, loud
        except ValueError as exc:
            raise StampNormalizerError(
                f"stamp normalizer: refusing to write an invalid stamp for "
                f"{title!r} — nothing written.\n{exc}"
            ) from exc

    new_text = _splice_scenarios(original, stamps, feature_files, comments)

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
    "MODEL_RULE",
    "MODEL_STAMP_COMMENT",
    "ModelAsker",
    "decide_refused_titles",
    "Home",
    "NormalizeContext",
    "NormalizeResult",
    "StampNormalizerError",
    "StampNormalizerRefusal",
    "classify_scenario",
    "then_clause",
    "given_when_clause",
    "when_then_clause",
    "ScenarioBlock",
    "extract_scenario_blocks",
    "extract_scenarios",
    "detect_repo_http_surface",
    "SURFACE_CONFIG_KEY",
    "SURFACE_HTTP",
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
    "R9_WIRE_STRONG",
    "R9_MACHINE_IDIOM",
    "R10_OPERATOR",
    "R10_OPERATOR_ANNOTATIONS",
]
