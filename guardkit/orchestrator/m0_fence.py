"""The M0 fence — one statement of "is this seat a frontier seat?".

M0 — *zero frontier on the routine critical path* — is the estate's outranking
measurable. Before stage 2 the only thing standing between an unattended leg and
a frontier vendor was a missing ``ANTHROPIC_API_KEY``: the review leg's CLI
fence judged a **supplied** ``--model`` alias, and the pipeline never supplies
one, so the live path always recorded ``NOT-EVALUATED`` and the model rode
``None`` into ``deepagents`` where ``ChatAnthropic(model_name="claude-sonnet-4-6")``
is the default (``deepagents/graph.py:145-153``).

This module is the single source of the rule (stage-2 design §3). It carries:

* :data:`FRONTIER_PROVIDER_PREFIXES` — the provider names that mean "a frontier
  vendor's API" (moved verbatim from ``orchestrator/review_runner.py``);
* :data:`FRONTIER_ESCAPE_ENV` — the ONE escape hatch, ``GUARDKIT_ALLOW_FRONTIER``
  (moved verbatim from ``cli/task_review.py``);
* :func:`resolve_m0_violation` — the CLI-level predicate over a *supplied* alias
  (moved verbatim from ``cli/task_review.py``; both names are re-exported from
  there so existing importers are unchanged);
* :func:`judge_effective_seat` / :func:`enforce_effective_seat` — the
  **chokepoint** rule that ``select_harness`` applies to the *effective* seat,
  which is the rule the design's three parts describe. It is built ON TOP of
  :func:`resolve_m0_violation`, never beside it: the frontier-prefix test and
  the ``OPENAI_BASE_URL`` route test each exist exactly once in this file.

The verdict the chokepoint reaches is recorded here (:func:`last_verdict`) so a
leg's receipt can **report** it rather than re-derive it (design §3.3). The
record keeps the **worst** verdict seen in the process, never the most recent —
otherwise a local PASS late in a leg erases a frontier construction earlier in
the same leg, which is precisely the event the receipt line exists to expose.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import sys
import threading
from dataclasses import dataclass
from typing import Any, FrozenSet, Optional, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Set (to any non-empty value) when the FACTORY launched this GuardKit. Forge's
#: ``build_launch_env`` (``forge/src/forge/launch_environment.py``) sets it to
#: ``1`` on every launch it makes and never inherits it, and every harness in a
#: factory build runs inside that one process. The fence applies to factory
#: launches only (Rich, 19 October 2026): a person's own run of GuardKit is not
#: fenced. The same setting decides the memory rule
#: (``guardkit.knowledge.memory_project.FACTORY_LAUNCH_ENV``).
FACTORY_LAUNCH_ENV = "GUARDKIT_FACTORY_LAUNCH"

#: Set to ``1`` to run on a frontier seat deliberately. Anything else (including
#: unset) leaves the fence armed. ONE escape hatch, one env var — a second would
#: be a future lie.
FRONTIER_ESCAPE_ENV = "GUARDKIT_ALLOW_FRONTIER"

#: Extra hosts that count as local seats, comma-separated. The escape valve for
#: a DOTTED internal name (``gb10.lan``, ``workhorse.internal``) that the
#: structural rules below cannot recognise. Exact host match, no wildcards — a
#: suffix rule would re-open the very hole the allowlist closes.
LOCAL_SEAT_HOSTS_ENV = "GUARDKIT_LOCAL_SEAT_HOSTS"

#: The IP ranges a local seat may live on. Stated as networks rather than as
#: ``ipaddress.is_private`` so the rule of record is READABLE and exactly the
#: ratified one (design §3c as corrected 2026-08-02): loopback, the three
#: RFC1918 v4 ranges, link-local, and the IPv6 ULA block. ``is_private`` would
#: silently also admit CGNAT/benchmark/reserved space nobody ruled on.
LOCAL_SEAT_NETWORKS: Tuple[Any, ...] = (
    ipaddress.ip_network("127.0.0.0/8"),  # loopback (v4)
    ipaddress.ip_network("::1/128"),  # loopback (v6)
    ipaddress.ip_network("10.0.0.0/8"),  # RFC1918
    ipaddress.ip_network("172.16.0.0/12"),  # RFC1918
    ipaddress.ip_network("192.168.0.0/16"),  # RFC1918 — the fleet's own LAN
    ipaddress.ip_network("169.254.0.0/16"),  # link-local (v4)
    ipaddress.ip_network("fe80::/10"),  # link-local (v6) — the same rule
    ipaddress.ip_network("fc00::/7"),  # unique local addresses (v6)
)

#: Provider prefixes that mean "a frontier vendor's API" for the M0 fence.
#: ``openai`` is handled separately: the fleet's own route *is*
#: ``init_chat_model("openai:<alias>")`` against a local ``OPENAI_BASE_URL``, so
#: the prefix alone proves nothing — see :func:`resolve_m0_violation`.
FRONTIER_PROVIDER_PREFIXES: Tuple[str, ...] = (
    "anthropic",
    "azure_openai",
    "azure-openai",
    "bedrock",
    "bedrock_converse",
    "cohere",
    "deepseek",
    "fireworks",
    "google",
    "google_genai",
    "google_vertexai",
    "gemini",
    "groq",
    "mistralai",
    "openrouter",
    "perplexity",
    "together",
    "vertexai",
    "xai",
)

#: The concrete model ``model=None`` falls to on the **langgraph** branch.
#: ``LangGraphHarness`` forwards ``model=None`` into
#: :func:`deepagents.create_deep_agent`, which calls ``_build_default_model()``
#: → ``ChatAnthropic(model_name="claude-sonnet-4-6")``
#: (``deepagents/graph.py:145-153``, re-verified 2026-08-02). Naming it is the
#: whole point of design §3 part (a): the refusal must say what would actually
#: have been called, not "some default".
LANGGRAPH_DEFAULT_SEAT = "anthropic:claude-sonnet-4-6"

#: The seat ``model=None`` falls to on the **sdk** branch. ``ClaudeSDKHarness``
#: omits the ``model`` key from ``ClaudeAgentOptions`` entirely when it is
#: ``None`` (``harness/sdk_harness.py:279-280``), so the bundled
#: ``claude-agent-sdk`` CLI picks its own default — an Anthropic frontier model
#: whose exact id is chosen by the installed CLI, not by this repo.
SDK_DEFAULT_SEAT = "the bundled claude-agent-sdk CLI default (an Anthropic seat)"

#: Verdict statuses recorded on :class:`M0Verdict`.
VERDICT_PASS = "PASS"
VERDICT_REFUSED = "REFUSED"
VERDICT_ALLOWED_BY_ESCAPE = "ALLOWED-BY-ESCAPE"
VERDICT_NOT_JUDGED = "NOT-JUDGED"
#: A person's own run (not a factory launch) on a seat the factory rule would
#: refuse. Judged and recorded, never refused (Rich, 19 October 2026).
VERDICT_PERSONAL_RUN = "PERSONAL-RUN"


def is_factory_launch(env: Optional[Any] = None) -> bool:
    """Did the factory launch this GuardKit? (:data:`FACTORY_LAUNCH_ENV`)

    Read fresh on every call, like the escape hatch, so a test or a launcher
    that sets it takes effect in the same process.

    **Any value at all is a factory launch,** whitespace and ``0``/``false``
    included: only unset or exactly empty is a person's own run. The fence
    fails safe — a value nobody can read as "on" must never switch it off
    (Codex review round 3: a stripped ``" "`` used to). This is the ONE
    predicate; the selector's second ``sdk`` check and the memory rule
    (``guardkit.knowledge.memory_project``) both call it.
    """
    settings = os.environ if env is None else env
    value = settings.get(FACTORY_LAUNCH_ENV)
    return value is not None and str(value) != ""


# ---------------------------------------------------------------------------
# The supplied-alias predicate (moved verbatim from cli/task_review.py)
# ---------------------------------------------------------------------------


def _split_provider_prefix(model: str) -> Tuple[Optional[str], str]:
    """Split ``provider:alias`` / ``provider/alias`` into its two halves."""
    for separator in (":", "/"):
        if separator in model:
            provider, _, alias = model.partition(separator)
            provider = provider.strip().lower()
            if provider:
                return provider, alias.strip()
    return None, model.strip()


def local_seat_hosts() -> FrozenSet[str]:
    """The operator-declared extra local-seat hosts, read fresh on every call.

    Read from the environment on every call (never cached at import) so a test
    or an operator can set :data:`LOCAL_SEAT_HOSTS_ENV` and have it take effect
    in the same process, exactly like the escape hatch.
    """
    raw = os.environ.get(LOCAL_SEAT_HOSTS_ENV, "")
    return frozenset(part.strip().lower() for part in raw.split(",") if part.strip())


def is_local_seat_host(host: str) -> bool:
    """Is ``host`` on the LOCAL-SEAT ALLOWLIST? (design §3c, corrected 2026-08-02)

    The rule is an **allowlist**, and that correction is the whole point. The
    shipped-then-corrected rule was a one-vendor DENYLIST (``openai.com``), and
    a denylist of one vendor is not an M0 fence: ``openrouter.ai``,
    ``api.deepseek.com``, ``api.groq.com``, ``api.together.xyz`` and
    ``generativelanguage.googleapis.com`` all sailed through it, and a
    scheme-less base URL parsed to no host at all and PASSED. Under an allowlist
    every one of those refuses, and so does the unparseable case.

    A host is local when it is:

    * ``localhost``;
    * an IP literal inside :data:`LOCAL_SEAT_NETWORKS` (loopback, RFC1918,
      link-local, IPv6 ULA);
    * a **single-label** hostname — no dot — which is what a LAN name looks like
      (``some-workhorse``, a box on the same network). A dotted name is a
      public DNS name shape and is NOT admitted structurally;
    * listed verbatim in :data:`LOCAL_SEAT_HOSTS_ENV` (exact match), which is
      how a dotted INTERNAL name gets in.

    Anything else is not local. That includes the empty string: a base URL that
    parses to no host is unreadable, and an unreadable route fails closed.
    """
    host = (host or "").strip().lower()
    if not host:
        return False
    if host in local_seat_hosts():
        return True
    if host == "localhost":
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        # Not an IP literal. A single-label name is a LAN name; a dotted name is
        # a public DNS shape and needs the explicit allowlist to get in.
        return "." not in host
    return any(address in network for network in LOCAL_SEAT_NETWORKS)


def _openai_base_url_violation(model: str, *, route_note: str) -> Optional[str]:
    """The ``OPENAI_BASE_URL`` route test — stated ONCE, used twice.

    Both the ``openai:``-prefixed case (:func:`resolve_m0_violation`) and the
    bare-alias case (design §3 part (c), :func:`judge_effective_seat`) reduce to
    the same question: does ``OPENAI_BASE_URL`` name a host on the LOCAL-SEAT
    ALLOWLIST (:func:`is_local_seat_host`)? The base URL is the load-bearing
    half — the alias is nearly decorative, because the langgraph translator's
    auto-prefixer (``harness/selector.py:162-176``) turns almost every bare
    alias into an ``openai:`` ChatOpenAI call.

    Returns the violation message, or ``None`` when the route is a local one.
    """
    base_url = os.environ.get("OPENAI_BASE_URL", "").strip()
    if not base_url:
        return (
            f"M0 fence: model {model!r} resolves to the OpenAI vendor API "
            f"(OPENAI_BASE_URL is unset, so {route_note})."
        )
    host = (urlparse(base_url).hostname or "").lower()
    if not host:
        # A scheme-less or otherwise unparseable base URL ("api.openai.com/v1")
        # yields hostname None. Under the old denylist that PASSED — the fence
        # could not name a vendor, so it allowed the call. Fail closed instead.
        return (
            f"M0 fence: model {model!r} routes to OPENAI_BASE_URL "
            f"{base_url!r}, which names no host — a scheme-less or unparseable "
            "base URL. The seat rule is an allowlist, so a route the fence "
            "cannot read is refused, never waved through (add the scheme)."
        )
    if not is_local_seat_host(host):
        return (
            f"M0 fence: model {model!r} routes to OPENAI_BASE_URL host "
            f"{host!r}, which is not a local seat. Local means loopback, an "
            "RFC1918/link-local/IPv6-ULA address, a single-label LAN hostname, "
            f"or a host named in {LOCAL_SEAT_HOSTS_ENV}."
        )
    return None


def resolve_m0_violation(model: Optional[str]) -> Optional[str]:
    """The **M0 fence**: refuse a frontier seat unless explicitly allowed.

    M0 — *zero frontier on the routine critical path* — is the estate's
    outranking measurable, and the design's whole M0 exposure moves into this
    leg (the pipeline side stays provably model-free). So the fence is a
    mechanism, not a promise: a resolved model alias carrying a frontier
    provider prefix makes the leg **exit 2 naming the model**, unless
    ``GUARDKIT_ALLOW_FRONTIER=1`` is set explicitly.

    Returns the violation message, or ``None`` when the model is allowed.

    Two rules:

    1. a provider prefix in :data:`FRONTIER_PROVIDER_PREFIXES` is a violation
       outright;
    2. ``openai:`` is judged by its route, not its name — the fleet's own
       harness path *is* ``init_chat_model("openai:<alias>")`` against a local
       ``OPENAI_BASE_URL``, so ``openai:`` passes only when ``OPENAI_BASE_URL``
       is set to a host on the LOCAL-SEAT ALLOWLIST
       (:func:`is_local_seat_host`). Unset, unreadable, or any other host —
       vendor or not — refuses.

    **The named hole this predicate does not cover** — a *bare* alias with no
    provider prefix, and ``model=None`` itself — is closed one level down, at
    the harness chokepoint: see :func:`judge_effective_seat`. This function is
    deliberately left as the *supplied-alias* judgement (the CLI's job, exit 2
    before any work happens); the chokepoint is the *effective-seat* judgement
    (the one every real model call passes through).
    """
    if not model:
        return None

    provider, alias = _split_provider_prefix(model)
    if provider is None:
        return None

    if provider == "openai":
        return _openai_base_url_violation(
            model,
            route_note="the 'openai:' prefix is not a local-fleet route",
        )

    if provider in FRONTIER_PROVIDER_PREFIXES:
        return (
            f"M0 fence: model {model!r} carries the frontier provider prefix "
            f"{provider!r} (alias {alias!r}). This call is on the routine "
            "critical path and M0 means zero frontier there."
        )
    return None


# ---------------------------------------------------------------------------
# The chokepoint verdict
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class M0Verdict:
    """What the chokepoint decided about the seat a harness was built on."""

    status: str
    harness: str
    effective_model: str
    detail: str
    #: ``False`` for a refusal that :data:`FRONTIER_ESCAPE_ENV` must NOT lift:
    #: the ``sdk`` harness on a factory launch. Before 19 October 2026 that
    #: refusal lived in the selector, after the fence, where the escape hatch
    #: never reached it; it moved into the fence so the recorded verdict says
    #: REFUSED instead of PASS, and this flag keeps it unescapable.
    escapable: bool = True

    @property
    def refused(self) -> bool:
        return self.status == VERDICT_REFUSED

    def as_receipt_line(self) -> str:
        """The one-line form a leg receipt carries (design §3.3)."""
        return (
            f"{self.status} (chokepoint select_harness/{self.harness}; "
            f"effective seat {self.effective_model}) — {self.detail}"
        )


#: How bad each verdict is. The recorded verdict keeps the WORST seen in the
#: process, never the latest — see :func:`record_verdict`.
_VERDICT_SEVERITY = {
    VERDICT_PASS: 0,
    VERDICT_NOT_JUDGED: 1,
    # Above NOT-JUDGED: a person's run on a seat the factory would refuse (a
    # hosted model, usually) must stay on the record when a later seat in the
    # same process could not be judged (coach review, 19 October 2026).
    VERDICT_PERSONAL_RUN: 2,
    VERDICT_ALLOWED_BY_ESCAPE: 3,
    VERDICT_REFUSED: 4,
}

_verdict_lock = threading.Lock()
_last_verdict: Optional[M0Verdict] = None


def _severity(verdict: M0Verdict) -> int:
    # An unknown status is treated as the worst: a verdict the record cannot
    # rank must never be the one a later PASS quietly displaces.
    return _VERDICT_SEVERITY.get(verdict.status, max(_VERDICT_SEVERITY.values()))


def record_verdict(verdict: M0Verdict) -> M0Verdict:
    """Record the chokepoint's verdict for the receipt writers to REPORT.

    **Worst-wins, not last-write-wins.** A leg builds more than one harness, and
    the receipt carries exactly one ``m0_fence`` line. Under last-write-wins a
    frontier construction early in the leg — refused, or allowed only by the
    escape hatch — was silently overwritten by any later local PASS, and the
    receipt then said PASS about a process that had already called a frontier
    seat. That is the one thing this receipt line exists to prevent, so the
    record keeps the worst verdict seen: REFUSED > ALLOWED-BY-ESCAPE >
    PERSONAL-RUN > NOT-JUDGED > PASS. A later verdict of EQUAL severity does replace the
    earlier one (same story, fresher detail).

    Returns the verdict passed in — the caller's own verdict, not the record —
    so the enforcement path is unchanged by the record's ranking.
    """
    global _last_verdict
    with _verdict_lock:
        if _last_verdict is None or _severity(verdict) >= _severity(_last_verdict):
            _last_verdict = verdict
    return verdict


def last_verdict() -> Optional[M0Verdict]:
    """The WORST chokepoint verdict so far, or ``None`` if the fence never ran.

    ``None`` is the honest "the fence did not run" signal: a receipt must keep
    saying NOT-EVALUATED in that case rather than invent a pass. See
    :func:`record_verdict` for why "worst" rather than "most recent".
    """
    with _verdict_lock:
        return _last_verdict


def reset_verdict() -> None:
    """Clear the recorded verdict (test isolation; also a fresh-process no-op).

    Worst-wins makes the record STICKY, so any test that drives more than one
    seat must start from a clean record — every test module touching the fence
    resets in an autouse fixture.
    """
    global _last_verdict
    with _verdict_lock:
        _last_verdict = None
        _personal_run_logged.clear()


# ---------------------------------------------------------------------------
# The chokepoint rule (design §3 part 2)
# ---------------------------------------------------------------------------


def default_seat_for(harness: str) -> Optional[str]:
    """The concrete seat ``model=None`` falls to on ``harness``.

    ``None`` means "this branch constructs no real model call", i.e. the branch
    is exempt from the fence.
    """
    if harness == "langgraph":
        return LANGGRAPH_DEFAULT_SEAT
    if harness == "sdk":
        return SDK_DEFAULT_SEAT
    return None


def judge_effective_seat(model: Any, *, harness: str) -> M0Verdict:
    """Judge the **effective** seat a harness branch is about to be built on.

    **The fence applies to factory launches only** (Rich, 19 October 2026). The
    factory must never reach a hosted model; a person running GuardKit by hand
    may choose one on purpose (some of Rich's own projects are built on the
    ``sdk`` harness with Claude). So:

    * **a factory launch** (:func:`is_factory_launch`) gets the factory rule,
      :func:`_judge_by_factory_rule`, unchanged — plus the ``sdk`` harness
      refused outright, unescapably, because a factory build never uses it;
    * **a person's own run** is judged by the same rule, so the record still
      says what the factory would have decided, but a refusal becomes
      :data:`VERDICT_PERSONAL_RUN` and nothing is refused. That includes
      langgraph with no model, which falls to the deepagents Anthropic default:
      a person may point their own run anywhere.

    A seat the factory rule passes is recorded PASS on either kind of run.
    """
    verdict = _judge_by_factory_rule(model, harness=harness)
    if not verdict.refused or is_factory_launch():
        return verdict
    return M0Verdict(
        status=VERDICT_PERSONAL_RUN,
        harness=verdict.harness,
        effective_model=verdict.effective_model,
        detail=(
            f"not a factory launch ({FACTORY_LAUNCH_ENV} is not set), so the "
            "fence does not apply: a person's own run is not fenced. On a "
            f"factory launch this seat would be refused — {verdict.detail}"
        ),
    )


def _judge_by_factory_rule(model: Any, *, harness: str) -> M0Verdict:
    """The factory's rule for the **effective** seat (see :func:`judge_effective_seat`).

    This is design §3's three-part rule, and it is the rule that actually
    protects M0 because it sits at the one chokepoint every production model
    call passes through (``select_harness``).

    Part (a) — ``model is None`` **is itself the violation.** The old fence
    judged only a supplied alias and recorded NOT-EVALUATED otherwise, which on
    the live path meant *always*: the pipeline emits no ``--model`` (zero hits
    in ``forge/src``), so the seat fell to the harness default. The refusal
    names the concrete default per branch — :data:`LANGGRAPH_DEFAULT_SEAT` /
    :data:`SDK_DEFAULT_SEAT` — so the reader learns what would have been called.

    Part (b) — a frontier provider prefix refuses outright. Delegated to
    :func:`resolve_m0_violation`; not restated here.

    Part (c) — a bare alias, or an ``openai:`` prefix, requires
    ``OPENAI_BASE_URL`` SET and pointing at a host on the **local-seat
    allowlist** (:func:`is_local_seat_host`; the rule was corrected from a
    one-vendor denylist on 2026-08-02 and the allowlist is the ratified form).
    The base URL is the load-bearing half: the langgraph translator
    auto-prefixes almost every bare alias to ``openai:``
    (``harness/selector.py:162-176``), so a bare alias with no base URL is an
    OpenAI-vendor call wearing a local-sounding name.
    The ``openai:``-prefixed half of part (c) is already inside
    :func:`resolve_m0_violation`; only the bare-alias half is added here, and it
    reuses the same :func:`_openai_base_url_violation` predicate.

    **Branch inventory** (``harness/selector.py``, re-read 2026-08-02) —
    ``select_harness`` has exactly two construction branches and one error
    branch:

    * ``"sdk"`` → ``ClaudeSDKHarness``: a REAL call to Anthropic's hosted
      models, whatever the model name. Refused outright, unescapably.
    * ``"langgraph"`` → ``LangGraphHarness``: a REAL model call. Fenced.
    * anything else → ``AgentInvocationError`` before any construction.

    There is **no** test/fake/no-op harness branch in the selector, so the
    design's "a branch that constructs no real model call is exempt" clause has
    no members today. :func:`default_seat_for` returning ``None`` is the seam
    that would exempt one if a future branch qualified.

    **The named hole, honestly:** a *non-string* ``model`` (a pre-constructed
    ``BaseChatModel`` instance — what ``deepagents`` calls an explicit model) is
    recorded :data:`VERDICT_NOT_JUDGED`, not refused. The fence judges seat
    *names*; it does not introspect model objects. No production caller passes
    one — ``agent_invoker``, ``coach_validator`` and ``task_work_interface`` all
    thread a ``str | None`` off the CLI — so this is a test-shape allowance, and
    the verdict says so out loud rather than reporting a pass.
    """
    default_seat = default_seat_for(harness)
    if default_seat is None:
        return M0Verdict(
            status=VERDICT_NOT_JUDGED,
            harness=harness,
            effective_model="<none — branch constructs no model call>",
            detail=(
                f"harness branch {harness!r} constructs no real model call, so "
                "there is no seat to fence."
            ),
        )

    if harness == "sdk":
        # The ``sdk`` harness runs the Claude program, which sends every call
        # to Anthropic's hosted models and never reads OPENAI_BASE_URL, so the
        # route test below says nothing about it. A factory build never uses
        # it (design ``factory-project-commands-without-factory-credentials``,
        # 13 October 2026). Refused whatever model it names, and the escape
        # hatch does not lift it.
        if model is None or (isinstance(model, str) and not model.strip()):
            seat = default_seat
        elif isinstance(model, str):
            seat = model.strip()
        else:
            seat = f"<{type(model).__name__} instance>"
        return M0Verdict(
            status=VERDICT_REFUSED,
            harness=harness,
            effective_model=seat,
            detail=(
                "M0 fence: the 'sdk' harness runs the Claude program, which "
                f"sends every call to Anthropic's hosted models (seat: {seat}). "
                "A factory build never uses it, whatever model it names."
            ),
            escapable=False,
        )

    # Part (a): model=None IS the violation — name the concrete default.
    if model is None:
        return M0Verdict(
            status=VERDICT_REFUSED,
            harness=harness,
            effective_model=default_seat,
            detail=(
                f"M0 fence: no model was supplied, so the {harness!r} harness "
                f"falls to {default_seat} — a frontier seat. M0 means zero "
                "frontier on the routine critical path, so an unnamed seat is "
                "refused: pass an explicit local-fleet --model."
            ),
        )

    if not isinstance(model, str):
        return M0Verdict(
            status=VERDICT_NOT_JUDGED,
            harness=harness,
            effective_model=f"<{type(model).__name__} instance>",
            detail=(
                "a pre-constructed model object was supplied; the M0 fence "
                "judges seat names, not model instances. No production caller "
                "passes one."
            ),
        )

    effective = model.strip()
    if not effective:
        # An empty string is the same absence as None, wearing a string's coat.
        return M0Verdict(
            status=VERDICT_REFUSED,
            harness=harness,
            effective_model=default_seat,
            detail=(
                f"M0 fence: model {model!r} is empty, so the {harness!r} "
                f"harness falls to {default_seat} — a frontier seat."
            ),
        )

    # Part (b): the frontier-prefix rule, stated once, in resolve_m0_violation.
    violation = resolve_m0_violation(effective)
    if violation is not None:
        return M0Verdict(
            status=VERDICT_REFUSED,
            harness=harness,
            effective_model=effective,
            detail=violation,
        )

    # Part (c): a bare alias is an openai: call in waiting — judge its route.
    provider, _alias = _split_provider_prefix(effective)
    if provider is None:
        bare_violation = _openai_base_url_violation(
            effective,
            route_note=(
                "a bare alias is auto-prefixed to 'openai:' by the langgraph "
                "translator and therefore routes to the vendor"
            ),
        )
        if bare_violation is not None:
            return M0Verdict(
                status=VERDICT_REFUSED,
                harness=harness,
                effective_model=effective,
                detail=(
                    f"{bare_violation} A bare alias proves nothing about where "
                    "the call goes; OPENAI_BASE_URL is the load-bearing half."
                ),
            )

    return M0Verdict(
        status=VERDICT_PASS,
        harness=harness,
        effective_model=effective,
        detail="seat resolves to a non-frontier route.",
    )


def receipt_line_when_chokepoint_did_not_run(model: Optional[str]) -> str:
    """The ``m0_fence`` receipt line for a leg that built no harness.

    Stated ONCE here because both legs' receipts say it (design §3.3), and a
    second copy of a sentence about what was and was not judged is exactly the
    kind of drift this line exists to expose.

    Two cases, and the first one is the honest half of a claim that used to be
    over-stated. The old wording was ``"evaluated (--model supplied; CLI fence
    only …)"``, which reads as "the seat was checked". It was not, in general:
    :func:`resolve_m0_violation` judges a PROVIDER PREFIX, and a bare alias —
    ``qwen36-workhorse``, the shape the fleet actually passes — carries none, so
    the function returns ``None`` without ever looking at ``OPENAI_BASE_URL``.
    Only the chokepoint route-judges a bare alias. The line now says which
    judgement happened rather than implying the strong one.

    A person's own run (not a factory launch) gets a third wording: neither
    fence applies to it, so nothing was judged and the line says so instead of
    claiming the CLI fence passed the alias.
    """
    if not is_factory_launch():
        supplied = f"--model {model!r} supplied" if model else "no --model supplied"
        return (
            f"NOT-FENCED (a person's own run: {FACTORY_LAUNCH_ENV} is not set, "
            f"so the fence does not apply; {supplied}, and no harness was "
            "constructed in this process)"
        )
    if model:
        provider, _alias = _split_provider_prefix(model)
        judged = (
            "its provider prefix was judged"
            if provider is not None
            else (
                "it is a BARE alias, which the CLI fence does not route-judge — "
                "only the chokepoint reads OPENAI_BASE_URL"
            )
        )
        return (
            f"PARTIALLY-EVALUATED (--model {model!r} supplied and passed the CLI "
            f"fence: {judged}. No harness was built in this process, so the "
            "effective-seat chokepoint — the one that judges the route — never "
            "ran; CLI fence only)"
        )
    return (
        "NOT-EVALUATED (no --model supplied and no harness was constructed in "
        "this process; the effective-seat chokepoint never ran)"
    )


def enforce_effective_seat(model: Any, *, harness: str) -> M0Verdict:
    """Apply :func:`judge_effective_seat`, record the verdict, refuse or return.

    Raises :class:`~guardkit.orchestrator.exceptions.AgentInvocationError`
    naming the effective model when the seat is refused. The never-raises
    invocation chain above ``select_harness`` already turns that into exit 2 on
    stderr, so no new plumbing is needed.

    ``GUARDKIT_ALLOW_FRONTIER=1`` (:data:`FRONTIER_ESCAPE_ENV`) proceeds — but
    **loudly**, with the same stderr echo the CLI-level fence uses. A deliberate
    frontier run is allowed; a silent one is not.

    Two things it does NOT do. It never refuses a person's own run: that
    verdict is :data:`VERDICT_PERSONAL_RUN`, recorded and logged once at INFO.
    And the escape hatch never lifts an unescapable refusal (the ``sdk``
    harness on a factory launch).
    """
    verdict = judge_effective_seat(model, harness=harness)

    if not verdict.refused:
        record_verdict(verdict)
        if verdict.status == VERDICT_PERSONAL_RUN:
            _log_personal_run_once(verdict)
        return verdict

    if verdict.escapable and os.environ.get(FRONTIER_ESCAPE_ENV) == "1":
        allowed = M0Verdict(
            status=VERDICT_ALLOWED_BY_ESCAPE,
            harness=verdict.harness,
            effective_model=verdict.effective_model,
            detail=f"{verdict.detail} Proceeding because {FRONTIER_ESCAPE_ENV}=1.",
        )
        record_verdict(allowed)
        message = (
            f"{verdict.detail} Proceeding because {FRONTIER_ESCAPE_ENV}=1 "
            f"(effective seat: {verdict.effective_model})."
        )
        print(message, file=sys.stderr, flush=True)
        logger.warning("%s", message)
        return allowed

    record_verdict(verdict)
    # Imported here so this module stays importable from the CLI layer without
    # dragging the orchestrator's exception module into every consumer.
    from guardkit.orchestrator.exceptions import AgentInvocationError

    if not verdict.escapable:
        raise AgentInvocationError(
            f"{verdict.detail} Effective seat: {verdict.effective_model}. "
            f"{FRONTIER_ESCAPE_ENV} does not override this."
        )
    raise AgentInvocationError(
        f"{verdict.detail} Effective seat: {verdict.effective_model}. "
        f"Set {FRONTIER_ESCAPE_ENV}=1 to override deliberately."
    )


_personal_run_logged: set = set()


def _log_personal_run_once(verdict: M0Verdict) -> None:
    """One INFO line per harness and seat per process; no stderr noise."""
    key = (verdict.harness, verdict.effective_model)
    with _verdict_lock:
        if key in _personal_run_logged:
            return
        _personal_run_logged.add(key)
    logger.info(
        "M0 fence: %s on the %r harness, seat %s — %s",
        VERDICT_PERSONAL_RUN,
        verdict.harness,
        verdict.effective_model,
        verdict.detail,
    )


def cli_m0_violation(model: Optional[str]) -> Optional[str]:
    """The command-line fence (a SUPPLIED ``--model``) under the launch rule.

    On a factory launch this is exactly :func:`resolve_m0_violation`. On a
    person's own run it is ``None``: the fence does not apply there (Rich,
    19 October 2026), the same rule the chokepoint follows.
    """
    if not is_factory_launch():
        return None
    return resolve_m0_violation(model)


__all__ = [
    "FACTORY_LAUNCH_ENV",
    "FRONTIER_ESCAPE_ENV",
    "FRONTIER_PROVIDER_PREFIXES",
    "LANGGRAPH_DEFAULT_SEAT",
    "LOCAL_SEAT_HOSTS_ENV",
    "LOCAL_SEAT_NETWORKS",
    "SDK_DEFAULT_SEAT",
    "is_local_seat_host",
    "local_seat_hosts",
    "M0Verdict",
    "VERDICT_ALLOWED_BY_ESCAPE",
    "VERDICT_NOT_JUDGED",
    "VERDICT_PASS",
    "VERDICT_PERSONAL_RUN",
    "VERDICT_REFUSED",
    "cli_m0_violation",
    "default_seat_for",
    "enforce_effective_seat",
    "is_factory_launch",
    "judge_effective_seat",
    "last_verdict",
    "receipt_line_when_chokepoint_did_not_run",
    "record_verdict",
    "reset_verdict",
    "resolve_m0_violation",
]
