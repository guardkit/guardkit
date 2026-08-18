"""THE ROUTING LAW's stamp — ``verifier:`` on planning artifacts (card Q8/A.2).

Ruled by Rich 2026-08-14 (BDD-replacement options card, Q8 = YES; the addendum
A.2 in ``ai-transition/docs/bdd-replacement-options-card-2026-08-09.md`` is the
design of record): **every approved scenario carries a ``verifier:`` stamp,
assigned at planning time, from a closed list of homes. An unstamped scenario
fails the plan load.** Coverage of every surface class stops being something a
research card argues and becomes something the machinery refuses to proceed
without.

The forcing function is copied from a pattern already live in this repo: the
``component:`` selector (``AutoBuildOrchestrator._resolve_task_component`` /
``toolchain_declaration.py``) fails the task load LOUDLY on an unknown name,
with no fallback. The stamp follows the same law: **an unknown ``verifier:``
value is a load ERROR, never a silent default** — a scenario silently routed
to the wrong home is the exact unverified-green the law exists to remove.

Where the stamp lives
---------------------
* **Feature YAML** (``.guardkit/features/FEAT-X.yaml``): a per-scenario map —

  .. code-block:: yaml

      routing_law: enforced          # optional; see "The opt-in flag" below
      feature_files:
        - features/user-auth/user-auth.feature
      scenarios:
        "User signs in with valid credentials":
          verifier: hurl
        "Rate limiter refuses the 6th attempt":
          verifier: toolchain
          test_ref: test_rate_limiter_refuses_sixth

* **Task frontmatter**: a ``verifier:`` key beside ``component:`` /
  ``behavioural_oracle:``, validated at task load with the same loud-failure
  pattern (``AutoBuildOrchestrator._resolve_task_verifier``). A task stamped
  ``verifier: toolchain`` MUST carry a ``test_ref:`` token (and optionally
  ``test_paths:``) — see "The toolchain linkage" and "The wrong-home stamp"
  below.

The closed vocabulary (A.2's home table)
----------------------------------------
``toolchain`` (the repo's own suite under its declared toolchain, 48% census
share) · ``hurl`` (frozen .hurl twins, the wire class) · ``exam`` (frozen-input
corpus + deterministic marker for agent behaviour) · ``probe:bus`` (ephemeral
NATS probe) · ``probe:process`` (Venom-grammar process/CLI/stdio-MCP probes) ·
``flutter`` (widget/integration tiers) · ``playwright`` (dormant browser home
— named so it is never silently dropped) · ``operator`` (attended
verification, listed by name, never silently dropped).

The opt-in flag (``routing_law``)
---------------------------------
Enforcement (unstamped scenario ⇒ plan-load rejection) is OPT-IN so no
existing repo breaks the day this ships:

* **Per repo**: top-level ``routing_law: enforced`` in
  ``<repo>/.guardkit/config.yaml`` (the same file, and the same reader
  precedent, as the ``toolchain:`` declaration). **api_test flips first** —
  the Hurl-pilot repo is the routing law's first enforced customer.
* **Per feature**: ``routing_law: enforced`` (or ``off``) in the feature YAML.
  The feature-level value is the escape hatch and WINS over the repo flag
  (the same precedence law as task-frontmatter ``behavioural_oracle``), so a
  flipped repo can still load a historical, pre-law feature by marking that
  one feature ``routing_law: off``.

The stamp SCHEMA is validated whenever it is present, flag or no flag — an
unknown verifier value is always a loud load error. The flag only controls
whether an *absent* stamp rejects the plan load.

The surface declaration (``surface``)
-------------------------------------
THE STAMP NORMALIZER (``stamp_normalizer.py``) mints ``hurl`` (rule R9) only
for a repo that HAS an HTTP surface, and it learns that STRUCTURALLY — never
by grepping free text (a pyproject comment saying "next" once made forge read
as a web app). Three doors, any suffices:

* a hurl-twins gate in ``qa/gates/registry.yaml`` (gate id/path says ``hurl``);
* top-level ``surface: http`` in ``<repo>/.guardkit/config.yaml`` — the
  EXPLICIT door, for a repo whose manifests are not read (requirements-only
  trees such as lpa-platform-poc) or whose web stack is not in the known list;
  a string, or a list containing ``http``:

  .. code-block:: yaml

      routing_law: enforced
      surface: http                  # or: surface: [http, bus]

* an EXACT web-framework package under pyproject ``[project] dependencies`` /
  ``[tool.poetry.dependencies]`` or package.json ``dependencies`` (fastapi,
  flask, django, starlette, aiohttp, litestar, sanic, tornado, quart, falcon,
  bottle · express, fastify, koa, hapi, next, @nestjs/core, hono, restify,
  @sveltejs/kit, nuxt). devDependencies, requirements*.txt, go.mod, Cargo.toml
  and comments never count.

The toolchain linkage (A.2's stamp-to-rule wiring)
--------------------------------------------------
For ``verifier: toolchain`` the scenario's pin into the repo's own suite must
be mechanical, not a comment: the stamp REQUIRES a ``test_ref`` token (since
2026-08-18 — a bare toolchain stamp is refused at load), and the
conformance guard (``spec_conformance.py`` — live, snapshotted pre-turn-1,
outside the builder's reach) gains a synthesized ``token_coverage`` rule
requiring that token under the declared ``test_paths`` (default
``tests/**/*``). The named test cannot silently vanish. This module only
BUILDS the rule dict; ``snapshot_task_conformance`` wires it into the
existing snapshot → evaluate → Coach-guard path. Wire, don't rebuild.

A ``test_ref`` on a non-``toolchain`` stamp is DECLARED BUT NOT CONSUMED in
this wave (future homes may claim it — e.g. a ``hurl`` stamp naming its
twin); it is logged as a WARNING at build time, mirroring
``_warn_about_unconsumed_component_installs``, never silently ignored.

The wrong-home stamp (RULED, Rich 2026-08-18 — drive 19 datum)
--------------------------------------------------------------
Planning run c585e146 stamped three plain-HTTP scenarios ``verifier:
toolchain`` with NO ``test_ref``: legal vocabulary, WRONG home. The routing
law only checked the vocabulary so it accepted; the normalizer never
overwrites an existing stamp so the wrong home rode through untouched. Two
cures, both here or in ``stamp_normalizer``:

* **(3) SCHEMA** — a ``verifier: toolchain`` stamp WITHOUT a ``test_ref`` is
  REFUSED at load (:class:`ScenarioStamp` model validator; the same rule
  and message on the task-frontmatter path, ``validate_task_verifier``).
  ``toolchain`` means "this NAMED test proves the scenario" — R8, the only
  rule that mints it, only ever mints it WITH a ``test_ref``; the schema
  now says the same thing back. This is a validity rule like an unknown
  home: it applies whenever the stamp is PRESENT, flag or no flag — an
  invalid stamp is never data.
* **(2) ADVISORY DISAGREEMENTS** — the normalizer classifies already-stamped
  titles too and RECORDS (never overwrites) where the rules would home a
  title differently (``NormalizeResult.disagreements``, a WARNING per
  title, echoed by the CLI ahead of the JSON; exit code unchanged).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

logger = logging.getLogger(__name__)


# The closed list of six live homes + the dormant home + the attended home
# (A.2). Adding a member is a RULED change to the routing law, not a code
# convenience — the closed list is what makes "all surfaces covered" a
# mechanical property instead of a promise.
VERIFIER_HOMES: Tuple[str, ...] = (
    "toolchain",
    "hurl",
    "exam",
    "probe:bus",
    "probe:process",
    "flutter",
    "playwright",
    "operator",
)

# The per-repo opt-in flag: top-level key in <repo>/.guardkit/config.yaml
# (same file as the `toolchain:` declaration; reader precedent
# `_load_coach_config` / `load_toolchain_declaration`).
ROUTING_LAW_KEY = "routing_law"
ROUTING_LAW_VALUES: Tuple[str, ...] = ("enforced", "off")

CONFIG_RELATIVE_PATH = Path(".guardkit") / "config.yaml"

# Default search space for a toolchain stamp's `test_ref` token when the
# stamp declares no `test_paths` of its own. One conventional location, not a
# guess-ladder: a repo whose tests live elsewhere declares `test_paths`.
DEFAULT_TEST_REF_PATHS: Tuple[str, ...] = ("tests/**/*",)

# Rule id for the synthesized token_coverage rule (task-frontmatter linkage).
TEST_REF_RULE_ID = "routing-law-test-ref"

# Gherkin scenario-title lines. Longest keyword first so "Scenario Outline:"
# never half-matches as "Scenario"; "Example:" (a Gherkin-6 Scenario alias)
# matches but "Examples:" (an Outline's table header) cannot — the "s" breaks
# the literal-plus-colon match.
_SCENARIO_LINE_RE = re.compile(
    r"^\s*(?:Scenario Outline|Scenario Template|Scenario|Example)\s*:\s*(?P<title>\S.*?)\s*$",
    re.MULTILINE,
)


def _vocabulary_sentence() -> str:
    """The closed list, spelled out for every loud error message."""
    return "Allowed verifier homes (closed list, card Q8/A.2): " + ", ".join(
        VERIFIER_HOMES
    )


# (3) The wrong-home rule's ONE message — the ScenarioStamp model validator
# (feature YAML) and validate_task_verifier (task frontmatter) both say it.
TOOLCHAIN_NEEDS_TEST_REF_MESSAGE = (
    "verifier: toolchain means 'this NAMED test proves the scenario' — a "
    "toolchain stamp must carry test_ref: <tests/…::test_node>; name the "
    "node, or stamp the home the scenario actually needs (hurl for an HTTP "
    "scenario, probe:process for a process/CLI scenario, probe:bus for a "
    "bus scenario, exam for judged model output, flutter / playwright for a "
    "device / browser scenario, operator for attended human work)."
)


def toolchain_stamp_needs_test_ref(verifier: Any, test_ref: Any) -> bool:
    """True when the stamp is ``toolchain`` and ``test_ref`` is absent/blank.

    The one predicate behind (3): shared by the feature-YAML schema and the
    task-frontmatter validator so the two paths can never drift.
    """
    if verifier != "toolchain":
        return False
    return not (isinstance(test_ref, str) and test_ref.strip())


class ScenarioStamp(BaseModel):
    """One scenario's ``verifier:`` stamp (feature-YAML per-scenario map).

    ``extra="forbid"`` for the same reason as every verdict-adjacent schema in
    this repo: a typo'd key in a routing declaration must be told, loudly, at
    load time — silently ignoring it would leave the scenario mis-routed with
    a green face.
    """

    model_config = ConfigDict(extra="forbid")

    verifier: str
    # `test_ref` / `test_paths` are the toolchain linkage (module docstring).
    # Accepted on any stamp (a future home may consume its own reference
    # token) but only CONSUMED for `verifier: toolchain` in this wave; the
    # unconsumed case is logged loudly at build time, never silently dropped.
    test_ref: Optional[str] = Field(default=None, min_length=1)
    test_paths: Optional[List[str]] = None

    @field_validator("verifier")
    @classmethod
    def _verifier_in_closed_vocabulary(cls, value: str) -> str:
        if value not in VERIFIER_HOMES:
            raise ValueError(
                f"unknown verifier {value!r}. {_vocabulary_sentence()}. "
                "There is NO fallback home: an unknown stamp is a load "
                "error on purpose (the component:-selector precedent)."
            )
        return value

    @field_validator("test_paths")
    @classmethod
    def _test_paths_non_empty_strings(
        cls, value: Optional[List[str]]
    ) -> Optional[List[str]]:
        if value is None:
            return value
        if not value:
            raise ValueError("test_paths must not be an empty list")
        for entry in value:
            if not isinstance(entry, str) or not entry.strip():
                raise ValueError(
                    f"test_paths entries must be non-empty strings; got {entry!r}"
                )
        return value

    @model_validator(mode="after")
    def _toolchain_carries_its_named_test(self) -> "ScenarioStamp":
        """(3) RULED 2026-08-18: ``toolchain`` WITHOUT ``test_ref`` is refused.

        A bare ``verifier: toolchain`` is legal vocabulary in the wrong home
        (drive 19: three plain-HTTP scenarios stamped toolchain, no test
        named). R8 — the only rule that mints toolchain — only ever mints it
        WITH a test_ref; the schema now holds every writer to the same
        contract. Flag or no flag: an invalid stamp is never data.
        """
        if toolchain_stamp_needs_test_ref(self.verifier, self.test_ref):
            raise ValueError(TOOLCHAIN_NEEDS_TEST_REF_MESSAGE)
        return self


def parse_scenario_stamp(raw: Any, *, scenario: str = "") -> ScenarioStamp:
    """Validate one per-scenario map entry into a :class:`ScenarioStamp`.

    Accepts the bare-string shorthand (``"toolchain"`` ≡
    ``{verifier: toolchain}``) — the same shorthand parity the
    ``behavioural_oracle`` declaration ships. Anything else malformed raises
    a plain-language, field-scoped ValueError naming the closed vocabulary.
    """
    where = f" for scenario {scenario!r}" if scenario else ""
    if isinstance(raw, str):
        raw = {"verifier": raw}
    if not isinstance(raw, dict):
        raise ValueError(
            f"Invalid verifier stamp{where}: expected a verifier name or a "
            f"mapping with a `verifier:` key, got {raw!r}. "
            f"{_vocabulary_sentence()}."
        )
    try:
        return ScenarioStamp.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(
            f"Invalid verifier stamp{where}:\n{exc}\n\n"
            f"{_vocabulary_sentence()}. "
            "Allowed keys: verifier, test_ref, test_paths. Unknown keys are "
            "rejected — check for typos."
        ) from exc


def validate_task_verifier(
    task_id: str, raw: Any, test_ref: Any = None
) -> Optional[str]:
    """ROUTING LAW: validate a task's frontmatter ``verifier:`` stamp.

    ``None``/absent is the overwhelmingly common case and means "no stamp" —
    every existing task in the estate, unchanged. A PRESENT stamp is checked
    against the closed vocabulary NOW, at task load, and an unknown value
    raises — deliberately mirroring ``_resolve_task_component``: the
    alternative to a loud failure is a scenario silently routed to no home
    (or the wrong home), which is the unverified green the law removes.

    ``test_ref`` is the frontmatter's ``test_ref:`` beside the stamp. (3)
    RULED 2026-08-18: ``verifier: toolchain`` WITHOUT a non-empty
    ``test_ref`` is refused with the same message as the feature-YAML
    schema — the token_coverage linkage downstream silently synthesized
    NOTHING for that shape (verified: it was NOT enforced before this).

    Raises
    ------
    ValueError
        If the stamp is not a non-empty string, names a verifier outside
        the closed vocabulary, or is ``toolchain`` without a ``test_ref``.
    """
    if raw is None:
        return None
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError(
            f"Invalid `verifier:` in {task_id}'s frontmatter: expected a "
            f"verifier home name, got {raw!r}. {_vocabulary_sentence()}."
        )
    name = raw.strip()
    if name not in VERIFIER_HOMES:
        raise ValueError(
            f"Task {task_id} is stamped `verifier: {name}`, which is not in "
            f"the closed vocabulary. {_vocabulary_sentence()}.\n"
            "This is a LOUD task-load failure on purpose (the routing law, "
            "card Q8/A.2): there is no fallback home, because a scenario "
            "silently routed to the wrong verifier is an unverified green.\n"
            "FIX: use one of the closed-list homes, or remove the stamp."
        )
    if toolchain_stamp_needs_test_ref(name, test_ref):
        raise ValueError(
            f"Task {task_id} is stamped `verifier: toolchain` with no "
            f"`test_ref:` beside it. {TOOLCHAIN_NEEDS_TEST_REF_MESSAGE}\n"
            "This is a LOUD task-load failure on purpose (the routing law, "
            "wrong-home ruling 2026-08-18): a bare toolchain stamp is legal "
            "vocabulary in the wrong home — the drive-19 shape."
        )
    return name


def extract_scenario_titles(feature_text: str) -> List[str]:
    """Extract scenario titles from Gherkin text (order kept, duplicates kept).

    Line-shaped lexing, not a Gherkin parser: ``Scenario:``,
    ``Scenario Outline:``, ``Scenario Template:`` and the Gherkin-6
    ``Example:`` alias all title a scenario; ``Examples:`` (an Outline's
    table header) never matches.
    """
    return [m.group("title") for m in _SCENARIO_LINE_RE.finditer(feature_text)]


def normalize_routing_law_flag(raw: Any, *, where: str) -> Optional[str]:
    """Normalize a ``routing_law`` value, absorbing the YAML-1.1 boolean trap.

    ``routing_law: off`` is a DOCUMENTED value and YAML 1.1 parses the bare
    token as boolean ``False`` — so ``False`` maps to ``"off"``. ``True``
    (``on``/``true``/``yes``) was never a documented value and raises with
    the fix spelled out (``enforced``), because a law flag guessed from a
    boolean is exactly the silent mis-read this function exists to prevent.

    Raises
    ------
    ValueError
        On any value other than ``None``, ``False``, ``"enforced"``,
        ``"off"``.
    """
    if raw is None:
        return None
    if raw is False:
        return "off"
    if raw is True:
        raise ValueError(
            f"Invalid `routing_law:` in {where}: got a YAML boolean true "
            "(`on`/`true`/`yes`). The law flag's values are "
            f"{' / '.join(ROUTING_LAW_VALUES)} — write `routing_law: "
            "enforced` to turn the law on."
        )
    if isinstance(raw, str) and raw.strip() in ROUTING_LAW_VALUES:
        return raw.strip()
    raise ValueError(
        f"Invalid `routing_law:` in {where}: got {raw!r}, expected one of "
        f"{', '.join(ROUTING_LAW_VALUES)}. A law flag must never be "
        "silently mis-read as off — fix the value."
    )


def load_repo_routing_law(repo_root: Path) -> Optional[str]:
    """Read the per-repo ``routing_law:`` flag from ``.guardkit/config.yaml``.

    Returns ``None`` when the file or key is absent (every repo that has not
    opted in behaves exactly as before), ``"enforced"`` / ``"off"`` when
    declared. An unreadable/non-mapping file degrades to ``None`` with a
    warning (the ``load_toolchain_declaration`` posture for file-level rot).

    A PRESENT key with a bad value RAISES — deliberately NOT the
    loud-degrade-to-None posture, because this key is a law flag: a typo'd
    ``routing_law: enforce`` silently meaning "off" would un-enforce the law
    while the repo owner believes it is on, which is worse than a crash.

    Raises
    ------
    ValueError
        If the key is present but not one of ``enforced`` / ``off``.
    """
    config_path = Path(repo_root) / CONFIG_RELATIVE_PATH
    if not config_path.exists():
        return None
    try:
        data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 — a broken config file never crashes here
        logger.warning("Failed to read %s: %s", config_path, exc)
        return None
    if not isinstance(data, dict):
        return None
    return normalize_routing_law_flag(
        data.get(ROUTING_LAW_KEY), where=str(config_path)
    )


def build_token_coverage_rule(
    verifier: Optional[str],
    test_ref: Optional[str],
    test_paths: Optional[List[str]] = None,
    *,
    rule_id: str = TEST_REF_RULE_ID,
) -> Optional[Dict[str, Any]]:
    """The toolchain linkage: build the ``token_coverage`` rule for a stamp.

    Returns a rule dict shaped exactly for ``spec_conformance``'s
    ``TokenCoverageRule`` (the live, snapshotted, Coach-guarded machinery —
    wire, don't rebuild) when the stamp is ``verifier: toolchain`` AND carries
    a ``test_ref``; otherwise ``None``. Pure — no I/O, no logging; the
    frontmatter wrapper below owns the loud-unconsumed warning.
    """
    if verifier != "toolchain" or not test_ref:
        return None
    return {
        "id": rule_id,
        "type": "token_coverage",
        "paths": list(test_paths) if test_paths else list(DEFAULT_TEST_REF_PATHS),
        "require_tokens": [test_ref],
    }


def build_rule_from_frontmatter(
    frontmatter: Dict[str, Any], *, task_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """Frontmatter seam for the toolchain linkage (never raises).

    Called from ``snapshot_task_conformance`` (a never-raise context), AFTER
    the orchestrate() path has already validated ``verifier:`` loudly — so
    malformed shapes here degrade to ``None`` with a warning rather than a
    second raise. A ``test_ref`` beside a non-``toolchain`` stamp is DECLARED
    BUT NOT CONSUMED in this wave and is said out loud, once, mirroring
    ``_warn_about_unconsumed_component_installs``.
    """
    verifier = frontmatter.get("verifier")
    test_ref = frontmatter.get("test_ref")
    test_paths = frontmatter.get("test_paths")

    if test_ref is not None and (
        not isinstance(test_ref, str) or not test_ref.strip()
    ):
        logger.warning(
            "ROUTING LAW: `test_ref` in %s's frontmatter is not a non-empty "
            "string (%r) — no token_coverage rule synthesized.",
            task_id or "<task>",
            test_ref,
        )
        return None

    if verifier == "toolchain" and not test_ref:
        # (3) the task-load validator REFUSES this shape before any build runs
        # (validate_task_verifier); this never-raise seam says so once rather
        # than synthesizing nothing in silence.
        logger.warning(
            "ROUTING LAW: task %s is stamped `verifier: toolchain` with no "
            "`test_ref` — no token_coverage rule can be synthesized. %s",
            task_id or "<task>",
            TOOLCHAIN_NEEDS_TEST_REF_MESSAGE,
        )
        return None

    if isinstance(verifier, str) and verifier != "toolchain" and test_ref:
        logger.warning(
            "ROUTING LAW: task %s declares `test_ref: %s` beside "
            "`verifier: %s` — test_ref is DECLARED BUT NOT CONSUMED for "
            "non-toolchain homes in this wave. The token_coverage linkage "
            "only rides `verifier: toolchain`.",
            task_id or "<task>",
            test_ref,
            verifier,
        )
        return None

    if test_paths is not None:
        if not (
            isinstance(test_paths, list)
            and test_paths
            and all(isinstance(p, str) and p.strip() for p in test_paths)
        ):
            logger.warning(
                "ROUTING LAW: `test_paths` in %s's frontmatter must be a "
                "non-empty list of strings (got %r) — falling back to the "
                "default %s.",
                task_id or "<task>",
                test_paths,
                list(DEFAULT_TEST_REF_PATHS),
            )
            test_paths = None

    rule = build_token_coverage_rule(
        verifier if isinstance(verifier, str) else None,
        test_ref.strip() if isinstance(test_ref, str) else None,
        test_paths,
    )
    if rule is not None:
        logger.info(
            "ROUTING LAW: task %s (`verifier: toolchain`, test_ref=%r) — "
            "synthesized token_coverage rule %r over %s; the named test "
            "token cannot silently vanish.",
            task_id or "<task>",
            test_ref,
            rule["id"],
            rule["paths"],
        )
    return rule


__all__ = [
    "VERIFIER_HOMES",
    "ROUTING_LAW_KEY",
    "ROUTING_LAW_VALUES",
    "normalize_routing_law_flag",
    "DEFAULT_TEST_REF_PATHS",
    "TEST_REF_RULE_ID",
    "ScenarioStamp",
    "TOOLCHAIN_NEEDS_TEST_REF_MESSAGE",
    "toolchain_stamp_needs_test_ref",
    "parse_scenario_stamp",
    "validate_task_verifier",
    "extract_scenario_titles",
    "load_repo_routing_law",
    "build_token_coverage_rule",
    "build_rule_from_frontmatter",
]
