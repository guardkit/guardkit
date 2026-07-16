"""R1–R10 derivation: compiled DCL IR + binding table -> outside-in assertions.

Design source of record: ``api_test/qa/dcl-spike/derivation-rules.md`` (read in
full — the rules spec). This module is that spec as code, ONCE (rules-level
discipline: no per-feature branch, ever). The feature facts live in the ``.dcl``
(consumed as the compiler IR); the repo/judgment facts live in the binding
table (:mod:`guardkit.qa.formats.dcl_binding`).

Each rule turns a block of the IR into one or more assertion records:

    R1  intent            -> the shared HTTP invocation surface (verb + path)
    R2  reachable outcome -> success-status assertion              (A-OUTCOME)
    R3  emitted-event field -> presence+type assertion            (A-FIELD-<ABBR>)
        + a J5-flagged format assertion when the binding opts the field in
                                                                   (A-<ABBR>-FORMAT)
    R4  count observation -> non-decreasing assertion              (A-COUNT-MONO)
    R5  duration observation -> bounded-latency probe              (A-DURATION)
    R6  lifecycle transition -> post-transition state observable   (A-LIFE-<TO>)
    R7  terminal state -> stability across observation             (A-LIFE-STABLE)
    R8  availability policy -> degraded-dependency assertion  SKIP (A-AVAIL)
    R9  rule block -> positive + negative assertions (none in the spike capability)
    R10 closed-world over declared verbs -> rejection assertions   (A-CW-<VERB>)

The output is DATA — an :class:`AssertionSet` written to
``qa/dcl/derived/<FEATURE>.yaml`` — executed later by
:mod:`guardkit.qa.dcl.assertion_runner`. The mutating-verb list
(``POST/PUT/PATCH/DELETE``) is fixed here in code (R10).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from guardkit.qa.formats.dcl_binding import CapabilityBinding, DclBinding
from guardkit.qa.formats.dcl_derivation import (
    AssertionsByDisposition,
    CheckerSummary,
    DclDerivation,
    ToolIdentity,
)

#: R10 · the fixed mutating-verb list (closed-world convention).
MUTATING_VERBS = ("POST", "PUT", "PATCH", "DELETE")

#: DCL type -> the predicate's ``dcl_type`` (the runner's presence+type check).
_TYPE_JUDGMENTS = {"Number": "J4"}  # integer narrowing is beyond DCL v1.0 (J4)


class DerivationError(RuntimeError):
    """The IR + binding could not be derived into an assertion set (loud)."""


# ---------------------------------------------------------------------------
# Assertion-set data model (written as YAML, read by the assertion runner)
# ---------------------------------------------------------------------------


@dataclass
class Assertion:
    """One derived assertion (a record, not executable code)."""

    id: str
    rule: str
    dcl_source: str
    flags: List[str]
    disposition: str  # RUN | SKIP
    predicate: Dict[str, Any]
    request: Optional[Dict[str, Any]] = None  # None => uses the invocation surface
    reason: Optional[str] = None  # set for SKIP


@dataclass
class AssertionSet:
    """The derived set for one feature — the deriver's product."""

    feature: str
    capability: str
    invocation: Dict[str, str]  # {method, path} — R1 shared surface
    assertions: List[Assertion] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "feature": self.feature,
            "capability": self.capability,
            "invocation": self.invocation,
            "assertions": [
                {k: v for k, v in asdict(a).items() if v is not None}
                for a in self.assertions
            ],
        }

    def write_yaml(self, path: Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(self.to_dict(), sort_keys=False), encoding="utf-8"
        )
        return path


@dataclass
class DerivationResult:
    """Assertion set + the receipt facts (rules fired, flags, ids by disposition)."""

    assertion_set: AssertionSet
    rules_fired: Dict[str, int]
    judgment_flags: List[str]
    run_ids: List[str]
    skip_ids: List[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def camel_to_snake(name: str) -> str:
    """DCL identifier (camelCase) -> wire key (snake_case) — the J3 convention."""
    s1 = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _abbrev(camel_name: str, cap_binding: CapabilityBinding) -> str:
    """The assertion-id label for a field — binding ``abbrev`` or wire-key default."""
    fb = cap_binding.fields.get(camel_name)
    if fb and fb.abbrev:
        return fb.abbrev.upper()
    return camel_to_snake(camel_name).upper()


def _pick_capability(ir: Dict[str, Any], capability: Optional[str]) -> Dict[str, Any]:
    caps = ir.get("capabilities") or []
    if not caps:
        raise DerivationError("IR carries no capabilities to derive from")
    if capability is None:
        if len(caps) != 1:
            names = [c.get("name") for c in caps]
            raise DerivationError(
                f"IR has {len(caps)} capabilities {names}; name one with --capability"
            )
        return caps[0]
    for cap in caps:
        if cap.get("name") == capability:
            return cap
    raise DerivationError(
        f"capability {capability!r} not in IR (have "
        f"{[c.get('name') for c in caps]})"
    )


def _event_by_name(ir: Dict[str, Any], name: str) -> Optional[Dict[str, Any]]:
    for ev in ir.get("events") or []:
        if ev.get("name") == name:
            return ev
    return None


# ---------------------------------------------------------------------------
# The deriver
# ---------------------------------------------------------------------------


def derive(
    ir: Dict[str, Any],
    binding: DclBinding,
    feature: str,
    capability: Optional[str] = None,
) -> DerivationResult:
    """Apply R1–R10 to ``ir`` under ``binding`` — return the assertion set + receipt."""
    cap = _pick_capability(ir, capability)
    cap_name = cap.get("name")
    if cap_name not in binding.capabilities:
        raise DerivationError(
            f"capability {cap_name!r} has no binding entry (have "
            f"{list(binding.capabilities)}); J1–J3 facts are required to derive."
        )
    cb: CapabilityBinding = binding.capabilities[cap_name]

    # R1 · the invocation surface. Match a declared IR intent to a bound intent.
    ir_intents = [i.get("name") for i in cap.get("intents") or []]
    bound = {n: b for n, b in cb.intents.items() if n in ir_intents}
    if not bound:
        raise DerivationError(
            f"no binding intent matches a declared intent {ir_intents} for "
            f"{cap_name!r}"
        )
    primary_name = next(iter(bound))
    primary = bound[primary_name]
    invocation = {"method": primary.method.upper(), "path": primary.path}

    assertions: List[Assertion] = []
    rules_fired: Dict[str, int] = {}
    flags_used: set[str] = set()

    def _emit(a: Assertion) -> None:
        assertions.append(a)
        rules_fired[a.rule] = rules_fired.get(a.rule, 0) + 1
        flags_used.update(a.flags)

    # R2 · reachable outcome -> success-status assertion.
    reachable = (cap.get("analysis") or {}).get("reachable_outcomes")
    if not reachable:
        reachable = [o.get("name") for o in cap.get("outcomes") or []]
    for outcome in reachable:
        oid = "A-OUTCOME" if len(reachable) == 1 else f"A-OUTCOME-{outcome.upper()}"
        _emit(
            Assertion(
                id=oid,
                rule="R2",
                dcl_source=f"outcome {outcome}; when always {outcome}",
                flags=["J1", "J2"],
                disposition="RUN",
                predicate={"check": "status_equals", "expected": cb.success_status},
            )
        )

    # R3 · emitted-event fields -> presence+type (+ J5 format opt-in).
    # Order fields by the binding's declared order first (repo intent), then any
    # remaining IR fields — a stable, repo-controlled ordering.
    format_assertions: List[Assertion] = []
    emitted = [e.get("event") for e in cap.get("emitted_events") or []]
    for ev_name in emitted:
        ev = _event_by_name(ir, ev_name)
        if ev is None:
            continue
        ir_fields = {f["name"]: f for f in (ev.get("payload") or {}).get("fields", [])}
        ordered = [n for n in cb.fields if n in ir_fields] + [
            n for n in ir_fields if n not in cb.fields
        ]
        for fname in ordered:
            fld = ir_fields[fname]
            wire_key = camel_to_snake(fname)
            dcl_type = fld.get("type", "Text")
            abbr = _abbrev(fname, cb)
            fb = cb.fields.get(fname)
            f_flags = ["J1", "J3"]
            if dcl_type in _TYPE_JUDGMENTS:
                f_flags.append(_TYPE_JUDGMENTS[dcl_type])
            nullable = bool(fb and fb.state)
            if nullable:  # nullable-until-state -> presence, not non-null (J6)
                f_flags.append("J6")
            predicate: Dict[str, Any] = {
                "check": "field_present_typed",
                "wire_key": wire_key,
                "dcl_type": dcl_type,
            }
            if nullable:
                predicate["nullable"] = True
            _emit(
                Assertion(
                    id=f"A-FIELD-{abbr}",
                    rule="R3",
                    dcl_source=f"event {ev_name} field {fname}: {dcl_type} required",
                    flags=f_flags,
                    disposition="RUN",
                    predicate=predicate,
                )
            )
            # J5 · format opt-in -> an extra, flagged assertion (recorded as judgment).
            if fb and fb.format:
                format_assertions.append(
                    Assertion(
                        id=f"A-{abbr}-FORMAT",
                        rule="R3+J5",
                        dcl_source=(
                            f"event {ev_name} field {fname}: Text required "
                            "(format is judgment-sourced, not DCL)"
                        ),
                        flags=["J1", "J3", "J5"],
                        disposition="RUN",
                        predicate={
                            "check": "format",
                            "wire_key": wire_key,
                            "format": fb.format,
                        },
                    )
                )

    # Identify the single numeric event field (backs count monotonicity — J7).
    numeric_wire_keys: List[str] = []
    for ev_name in emitted:
        ev = _event_by_name(ir, ev_name)
        if ev is None:
            continue
        for fld in (ev.get("payload") or {}).get("fields", []):
            if fld.get("type") == "Number":
                numeric_wire_keys.append(camel_to_snake(fld["name"]))

    observations = ir.get("observations") or []

    # R4 · count observation -> one non-decreasing assertion on the numeric field.
    count_obs = [o for o in observations if o.get("observation_type") == "count"]
    if count_obs:
        if len(numeric_wire_keys) == 1:
            _emit(
                Assertion(
                    id="A-COUNT-MONO",
                    rule="R4",
                    dcl_source="observe event/outcome count",
                    flags=["J1", "J7"],
                    disposition="RUN",
                    predicate={
                        "check": "non_decreasing",
                        "wire_key": numeric_wire_keys[0],
                    },
                )
            )
        else:
            _emit(
                Assertion(
                    id="A-COUNT-MONO",
                    rule="R4",
                    dcl_source="observe count (no single numeric field to bind)",
                    flags=["J1", "J7"],
                    disposition="SKIP",
                    predicate={"check": "non_decreasing"},
                    reason=(
                        f"count observation present but {len(numeric_wire_keys)} "
                        "numeric fields — cannot mechanically pick the backing wire "
                        "field (J7). Recorded, not run."
                    ),
                )
            )

    # R5 · duration observation -> bounded-latency probe.
    duration_obs = [o for o in observations if o.get("observation_type") == "duration"]
    for idx, obs in enumerate(duration_obs):
        did = "A-DURATION" if len(duration_obs) == 1 else f"A-DURATION-{idx + 1}"
        _emit(
            Assertion(
                id=did,
                rule="R5",
                dcl_source=f"observe capability duration as {obs.get('metric_name')}",
                flags=["J1", "J7"],
                disposition="RUN",
                predicate={"check": "latency_below", "bound_seconds": 5.0},
            )
        )

    lifecycle = cap.get("lifecycle") or {}

    def _field_for_state(state: str) -> Optional[str]:
        for camel, fb in cb.fields.items():
            if fb.state == state:
                return camel_to_snake(camel)
        return None

    # R6 · lifecycle transition -> post-transition state observable.
    for tr in lifecycle.get("transitions") or []:
        to_state = tr.get("to")
        wire_key = _field_for_state(to_state)
        if wire_key is not None:
            predicate = {"check": "field_non_null", "wire_key": wire_key}
            flags = ["J1", "J6"]
        else:  # no bound observable -> the generic destination signal (success holds)
            predicate = {"check": "status_equals", "expected": cb.success_status}
            flags = ["J1"]
        _emit(
            Assertion(
                id=f"A-LIFE-{to_state.upper()}",
                rule="R6",
                dcl_source=(
                    f"lifecycle move {tr.get('from')} to {to_state} on "
                    f"{tr.get('trigger_kind')} {tr.get('trigger_name')}"
                ),
                flags=flags,
                disposition="RUN",
                predicate=predicate,
            )
        )

    # R7 · terminal state -> stability of its observable across observation.
    terminals = lifecycle.get("terminal_states") or []
    for term in terminals:
        wire_key = _field_for_state(term)
        tid = "A-LIFE-STABLE" if len(terminals) == 1 else f"A-LIFE-STABLE-{term.upper()}"
        if wire_key is not None:
            _emit(
                Assertion(
                    id=tid,
                    rule="R7",
                    dcl_source=f"lifecycle end {term}",
                    flags=["J1", "J9"],
                    disposition="RUN",
                    predicate={"check": "field_stable", "wire_key": wire_key},
                )
            )
        else:
            _emit(
                Assertion(
                    id=tid,
                    rule="R7",
                    dcl_source=f"lifecycle end {term} (no bound observable)",
                    flags=["J1", "J9"],
                    disposition="SKIP",
                    predicate={"check": "field_stable"},
                    reason=(
                        f"terminal state {term} has no field bound to it (binding "
                        "'state') — no wire fact to assert stable. Recorded, not run."
                    ),
                )
            )

    # R3+J5 format assertions (emitted after lifecycle, matching the spike order).
    for fa in format_assertions:
        _emit(fa)

    # R8 · availability policy -> degraded-dependency assertion (SKIP: out of venue).
    cap_policy_names = {p.get("policy") for p in cap.get("policies") or []}
    for pol in ir.get("policies") or []:
        if pol.get("name") not in cap_policy_names:
            continue
        families = pol.get("families") or [pol.get("family")]
        if "availability" not in families:
            continue
        tolerated = any(
            c.get("name") == "dependency_tolerance"
            and any(
                "allowed" in (p.get("values") or [])
                for p in c.get("parameters") or []
            )
            for c in pol.get("concerns") or []
        )
        if not tolerated:
            continue
        _emit(
            Assertion(
                id="A-AVAIL",
                rule="R8",
                dcl_source=f"policy {pol.get('name')} governs capability",
                flags=["J1", "J8"],
                disposition="SKIP",
                predicate={"check": "availability_under_dependency_down"},
                reason=(
                    "derivable in shape (with the dependency down, the intent still "
                    "yields its success signal) but NOT runnable in the read-only "
                    "HTTP venue: needs dependency fault-injection (J8). Recorded, "
                    "not executed."
                ),
            )
        )

    # R9 · rule blocks -> positive + negative (the spike capability declares none).
    for rule_block in (cap.get("rules") or []) + (ir.get("rules") or []):
        rname = rule_block.get("name", "rule")
        _emit(
            Assertion(
                id=f"A-RULE-{rname.upper()}-POS",
                rule="R9",
                dcl_source=f"rule {rname} (conforming request accepted)",
                flags=["J1"],
                disposition="RUN",
                predicate={"check": "status_equals", "expected": cb.success_status},
            )
        )
        _emit(
            Assertion(
                id=f"A-RULE-{rname.upper()}-NEG",
                rule="R9",
                dcl_source=f"rule {rname} (violating request rejected)",
                flags=["J1"],
                disposition="RUN",
                predicate={"check": "status_in_range", "low": 400, "high": 499},
                request={"method": invocation["method"], "path": invocation["path"]},
            )
        )

    # R10 · closed-world over the declared verb set -> rejection assertions.
    paths_verbs: Dict[str, set[str]] = {}
    for b in bound.values():
        paths_verbs.setdefault(b.path, set()).add(b.method.upper())
    single_path = len(paths_verbs) == 1
    for path, declared_verbs in paths_verbs.items():
        for verb in MUTATING_VERBS:
            if verb in declared_verbs:
                continue
            slug = "" if single_path else "-" + re.sub(r"[^A-Z0-9]+", "", path.upper())
            _emit(
                Assertion(
                    id=f"A-CW-{verb}{slug}",
                    rule="R10",
                    dcl_source=(
                        "closed-world over the intent set: only "
                        f"{sorted(declared_verbs)} declared on {path}"
                    ),
                    flags=["J1"],
                    disposition="RUN",
                    predicate={"check": "status_in_range", "low": 400, "high": 499},
                    request={"method": verb, "path": path, "body": "{}"},
                )
            )

    aset = AssertionSet(
        feature=feature,
        capability=cap_name,
        invocation=invocation,
        assertions=assertions,
    )
    run_ids = [a.id for a in assertions if a.disposition == "RUN"]
    skip_ids = [a.id for a in assertions if a.disposition == "SKIP"]
    return DerivationResult(
        assertion_set=aset,
        rules_fired=rules_fired,
        judgment_flags=sorted(flags_used, key=lambda f: int(f[1:])),
        run_ids=run_ids,
        skip_ids=skip_ids,
    )


def make_receipt(
    result: DerivationResult,
    *,
    feature: str,
    source_dcl: str,
    source_dcl_sha256: str,
    binding_sha256: str,
    checker_ok: bool,
    error_count: int,
    warning_count: int,
    tool_name: str = "guardkit-dcl-deriver",
    checker_pin: str,
) -> DclDerivation:
    """Build the F-format dcl-derivation receipt for a derivation run."""
    return DclDerivation(
        format_version=DclDerivation.CURRENT_FORMAT_VERSION,
        feature=feature,
        capability=result.assertion_set.capability,
        source_dcl=source_dcl,
        source_dcl_sha256=source_dcl_sha256,
        checker=CheckerSummary(
            ok=checker_ok, error_count=error_count, warning_count=warning_count
        ),
        binding_sha256=binding_sha256,
        rules_fired=result.rules_fired,
        judgment_flags=result.judgment_flags,
        assertions=AssertionsByDisposition(run=result.run_ids, skip=result.skip_ids),
        tool=ToolIdentity(name=tool_name, checker_pin=checker_pin),
    )
