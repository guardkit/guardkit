"""Pre-flight: perishable-prereq + instrument self-check (WS2 session B3).

Scope-design §3 step 1. Pre-flight runs BEFORE any gate and decides whether the
run can proceed, or must short-circuit to an honest ``instrument_fail`` /
``environment_fail`` verdict (DF-017 — those never indict the system under
test). Four inputs:

1. **ST-11 instrument self-check** — does the gate load? The deterministic core
   is "the registered gate script exists at its registry path"; a missing script
   is an instrument fault (the tool isn't there), not a system failure. Richer
   live checks (does the login helper work, does the tool import) are an optional
   :class:`InstrumentSelfCheck` seam; unconfigured, the declared ``preflight``
   names are recorded as not-live-verified (attended / B8), never faked green.

2. **F1 negative-path readiness** — each gate's pass bar must declare the
   required negative paths the gate is expected to exercise. The required set is
   derived from the bar's ``auth_surface_bearing`` flag using the sets EXPORTED
   by ``guardkit.qa.formats`` (``AUTH_/UNIVERSAL_/REQUIRED_NEGATIVE_PATHS``) —
   imported, never re-listed (B2 house rule; PB-14 keys per-path enforcement on
   the same flag).

3. **Reservation check** — the GB10-GPU-class lease (§4). Behind the
   :class:`ReservationBroker` seam; the real lease lands with B8.

4. **F6 broker-config diff** — live stream/consumer state vs the seam manifest's
   broker section (LPA-16). Behind the :class:`BrokerDiffProvider` seam; lands
   with B7/B8.

Plus the WS5-owned **F16 perishable checklist** (broker health, tokens, channel
membership, model warm) via :class:`F16ChecklistProvider` (schema unowned by
WS2 — the consumer interface is here).

Every seam has an ``Unconfigured*`` default that RAISES (:class:`LiveGateStubError`)
if invoked — never a silent success (FEAT-DD4F). Pre-flight catches that raise
at its own boundary and records a not-ready check, so the default (nothing
wired) run is an honest ``environment_fail``, not a crash and not a false pass.
The one exception (ruled 08-15): the RUNNER wires
:class:`DefaultF16ChecklistProvider` for a bare run — a REAL reachability
check against each gate's registry ``base_url_env`` (never a silent success:
unset/unreachable is still honestly not-ready) — because the Unconfigured F16
stub made every bare ``guardkit qa live-gate`` run ``environment_fail``.
``run_preflight`` itself keeps the loud stub as its default.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence

from guardkit.qa.formats import (
    REQUIRED_NEGATIVE_PATHS,
    UNIVERSAL_NEGATIVE_PATHS,
    PassBar,
    QAFormatError,
    validate_instance,
)
from guardkit.qa.formats.gate_registry import GateEntry, PreflightResult

from guardkit.orchestrator.live_gate.errors import LiveGateStubError

# Check categories drive the readiness split.
INSTRUMENT = "instrument"
ENVIRONMENT = "environment"


@dataclass(frozen=True)
class SeamResult:
    """Uniform return shape for a pre-flight seam call."""

    ok: bool
    detail: str


# ---------------------------------------------------------------------------
# Seams (each Unconfigured default raises loudly if invoked)
# ---------------------------------------------------------------------------


class ReservationBroker(ABC):
    """Environment reservation lease check (§4; e.g. gb10-gpu)."""

    @abstractmethod
    def check(self, resource: str) -> SeamResult:
        """Is ``resource`` reserved/available for this run?"""


class UnconfiguredReservationBroker(ReservationBroker):
    def check(self, resource: str) -> SeamResult:
        raise LiveGateStubError(
            f"ReservationBroker not configured: cannot verify a lease on "
            f"{resource!r}. The reservation lease lands with the deploy stage "
            f"(B8); until then a run needing a reserved resource is "
            f"environment_fail, not pass."
        )


class BrokerDiffProvider(ABC):
    """F6 broker-config-as-contract diff (LPA-16)."""

    @abstractmethod
    def diff(self, broker_contract_ref: str) -> SeamResult:
        """Diff live stream/consumer state vs the F6 broker section."""


class UnconfiguredBrokerDiffProvider(BrokerDiffProvider):
    def diff(self, broker_contract_ref: str) -> SeamResult:
        raise LiveGateStubError(
            f"BrokerDiffProvider not configured: cannot diff the live broker "
            f"against {broker_contract_ref!r}. The F6 broker diff lands with "
            f"B7/B8; until then a broker-contract-bearing run is "
            f"environment_fail, not pass."
        )


class F16ChecklistProvider(ABC):
    """WS5-owned perishable-prereq checklist (broker health, tokens, channel
    membership, model warm). WS2 defines only this consumer interface."""

    @abstractmethod
    def checklist(self) -> Sequence[SeamResult]:
        """Return the current F16 check outcomes."""


class UnconfiguredF16ChecklistProvider(F16ChecklistProvider):
    def checklist(self) -> Sequence[SeamResult]:
        raise LiveGateStubError(
            "F16ChecklistProvider not configured: the perishable-prereq "
            "checklist (F16, WS5-owned) has no source. A run cannot confirm "
            "tokens/broker/model readiness — environment_fail, not pass."
        )


#: Default wall-clock cap for one reachability GET.
DEFAULT_REACHABILITY_TIMEOUT_S: float = 5.0


class DefaultF16ChecklistProvider(F16ChecklistProvider):
    """Minimal REAL F16 source for a bare run (no WS5 checklist wired).

    Before this default existed, the bare ``guardkit qa live-gate`` CLI hit the
    :class:`UnconfiguredF16ChecklistProvider` stub on every repo and every run
    was ``environment_fail`` — the verdict could never follow the gates.

    One real check per distinct registry target: **reachability**. For each
    distinct ``target.base_url_env`` declared by the selected gates, read that
    env var and GET the URL — ANY HTTP answer (any status code, including 4xx/
    5xx) proves something is listening, so the target is ready. An unset env
    var, or a connection-level failure (refused, DNS, timeout), is honestly
    not-ready → ``environment_fail``, never a guess and never a product
    ``fail`` misattributed to gates that could not have reached anything.

    The remaining F16 perishable prereqs (tokens, broker health, channel
    membership, model warm) have no source here and are recorded
    declared-not-verified with ``ok=True`` — the same recorded-not-faked
    convention as pre-flight's ``instrument-declared`` line.
    """

    def __init__(
        self,
        gates: Sequence[GateEntry],
        *,
        env: Optional[Mapping[str, str]] = None,
        timeout_s: float = DEFAULT_REACHABILITY_TIMEOUT_S,
    ) -> None:
        self._gates = list(gates)
        self._env: Mapping[str, str] = env if env is not None else dict(os.environ)
        self._timeout_s = timeout_s

    def checklist(self) -> Sequence[SeamResult]:
        results: List[SeamResult] = []
        seen: List[str] = []
        for gate in self._gates:
            var = gate.target.base_url_env
            if var in seen:
                continue
            seen.append(var)
            base_url = (self._env.get(var) or "").strip()
            if not base_url:
                results.append(
                    SeamResult(
                        ok=False,
                        detail=(
                            f"base_url env {var!r} is not set — no target to "
                            f"verify reachability against; the environment is "
                            f"not ready"
                        ),
                    )
                )
                continue
            results.append(self._reachability(var, base_url))
        results.append(
            SeamResult(
                ok=True,
                detail=(
                    "remaining F16 perishable prereqs (tokens, broker health, "
                    "channel membership, model warm) declared-not-verified — "
                    "no WS5 checklist source configured (attended)"
                ),
            )
        )
        return results

    def _reachability(self, var: str, base_url: str) -> SeamResult:
        """GET ``base_url``; any HTTP answer = ready, no answer = not ready."""
        try:
            request = urllib.request.Request(base_url, method="GET")
            with urllib.request.urlopen(request, timeout=self._timeout_s) as resp:
                return SeamResult(
                    ok=True,
                    detail=f"{var}={base_url} reachable (HTTP {resp.status})",
                )
        except urllib.error.HTTPError as exc:
            # An HTTP status IS an answer — something is serving at the URL.
            return SeamResult(
                ok=True,
                detail=f"{var}={base_url} reachable (HTTP {exc.code})",
            )
        except Exception as exc:  # noqa: BLE001 — any transport fault = not ready
            return SeamResult(
                ok=False,
                detail=(
                    f"{var}={base_url} unreachable: "
                    f"{exc.__class__.__name__}: {exc}"
                ),
            )


class InstrumentSelfCheck(ABC):
    """Optional live ST-11 checks (does the login helper work, does the tool
    import). The deterministic script-exists check needs no seam."""

    @abstractmethod
    def check(self, gate_id: str, preflight_names: Sequence[str]) -> Sequence[SeamResult]:
        """Run the gate's declared ``preflight`` self-checks live."""


# ---------------------------------------------------------------------------
# Outcome
# ---------------------------------------------------------------------------


@dataclass
class PreflightOutcome:
    """Aggregate pre-flight result + the readiness split.

    ``checks`` is the envelope-facing list ({name, category, ok, detail}).
    ``instrument_ok`` = every instrument-category check passed. ``environment_ok``
    = every environment-category check passed.
    """

    checks: List[Dict[str, Any]] = field(default_factory=list)

    def _ok_for(self, category: str) -> bool:
        cat = [c for c in self.checks if c["category"] == category]
        return all(c["ok"] for c in cat) if cat else True

    @property
    def instrument_ok(self) -> bool:
        return self._ok_for(INSTRUMENT)

    @property
    def environment_ok(self) -> bool:
        return self._ok_for(ENVIRONMENT)

    @property
    def classification(self) -> Optional[Literal["instrument_fail", "environment_fail"]]:
        """The short-circuit verdict, or None to proceed to gate execution.

        Instrument faults are checked first: a broken instrument makes any
        environment reading meaningless (ST-11 attribution order).
        """
        if not self.instrument_ok:
            return "instrument_fail"
        if not self.environment_ok:
            return "environment_fail"
        return None

    def to_schema(self) -> PreflightResult:
        """Project onto the F4 ``PreflightResult`` envelope shape."""
        return PreflightResult(checks=list(self.checks), instrument_ok=self.instrument_ok)

    # internal
    def _add(self, name: str, category: str, ok: bool, detail: str) -> None:
        self.checks.append({"name": name, "category": category, "ok": ok, "detail": detail})


def _run_seam(outcome: PreflightOutcome, name: str, category: str, fn) -> None:
    """Invoke a seam callable, recording a not-ready check if it raises the
    loud stub error (never swallowed into a pass)."""
    try:
        result = fn()
    except LiveGateStubError as exc:
        outcome._add(name, category, ok=False, detail=str(exc))
        return
    if isinstance(result, SeamResult):
        outcome._add(name, category, result.ok, result.detail)
    else:  # a sequence of SeamResults
        for i, r in enumerate(result):
            outcome._add(f"{name}[{i}]", category, r.ok, r.detail)


def _check_negative_path_readiness(outcome: PreflightOutcome, gate: GateEntry, repo_root: Path) -> None:
    """F1 readiness: the gate's pass bar declares the required negative paths.

    The required set is derived from ``auth_surface_bearing`` using the EXPORTED
    sets (never re-listed). A missing pass bar / invalid bar is an instrument
    config fault.
    """
    bar_path = (repo_root / gate.pass_bar_ref).resolve()
    if not bar_path.is_file():
        outcome._add(
            f"{gate.id}:pass-bar", INSTRUMENT, ok=False,
            detail=f"pass bar {gate.pass_bar_ref!r} not found at {bar_path}",
        )
        return
    try:
        bar: PassBar = validate_instance("pass-bar", bar_path)  # type: ignore[assignment]
    except QAFormatError as exc:
        outcome._add(
            f"{gate.id}:pass-bar", INSTRUMENT, ok=False,
            detail=f"pass bar {gate.pass_bar_ref!r} is invalid: {exc}",
        )
        return
    required = REQUIRED_NEGATIVE_PATHS if bar.auth_surface_bearing else UNIVERSAL_NEGATIVE_PATHS
    missing = required - set(bar.negative_paths)
    if missing:
        outcome._add(
            f"{gate.id}:negative-paths", INSTRUMENT, ok=False,
            detail=(
                f"pass bar declares negative_paths missing {sorted(missing)} "
                f"(auth_surface_bearing={bar.auth_surface_bearing})"
            ),
        )
    else:
        outcome._add(
            f"{gate.id}:negative-paths", INSTRUMENT, ok=True,
            detail=(
                f"all {len(required)} required negative path(s) declared "
                f"(auth_surface_bearing={bar.auth_surface_bearing})"
            ),
        )


def run_preflight(
    gates: Sequence[GateEntry],
    *,
    repo_root: Path,
    reservation_broker: Optional[ReservationBroker] = None,
    broker_diff: Optional[BrokerDiffProvider] = None,
    f16_provider: Optional[F16ChecklistProvider] = None,
    instrument_check: Optional[InstrumentSelfCheck] = None,
    reservation_resource: Optional[str] = None,
    broker_contract_ref: Optional[str] = None,
) -> PreflightOutcome:
    """Run pre-flight for the selected gates; return the outcome + readiness.

    With every seam left unconfigured (the v1 default — no live deploy/broker),
    the environment checks all record "not configured", so
    :attr:`PreflightOutcome.classification` is ``environment_fail`` — the honest
    "no deploy to verify against" verdict, never a false pass.
    """
    outcome = PreflightOutcome()

    # 1. ST-11 instrument self-check: the deterministic script-exists check,
    #    plus optional live checks per gate's declared preflight names.
    for gate in gates:
        script_path = (repo_root / gate.path).resolve()
        if script_path.exists():
            outcome._add(
                f"{gate.id}:script", INSTRUMENT, ok=True,
                detail=f"gate script present at {gate.path}",
            )
        else:
            outcome._add(
                f"{gate.id}:script", INSTRUMENT, ok=False,
                detail=f"gate script MISSING at {script_path} (registry path {gate.path!r})",
            )
        if gate.preflight:
            if instrument_check is not None:
                _run_seam(
                    outcome, f"{gate.id}:instrument", INSTRUMENT,
                    lambda g=gate: instrument_check.check(g.id, g.preflight),
                )
            else:
                # Declared but not live-verified — recorded, not faked green.
                outcome._add(
                    f"{gate.id}:instrument-declared", INSTRUMENT, ok=True,
                    detail=(
                        f"declared preflight {list(gate.preflight)} not live-verified "
                        f"(no InstrumentSelfCheck configured — attended / B8)"
                    ),
                )
        # 2. F1 negative-path readiness (consumes the exported sets).
        _check_negative_path_readiness(outcome, gate, repo_root)

    # 3. Reservation lease.
    if reservation_resource is not None:
        broker = reservation_broker or UnconfiguredReservationBroker()
        _run_seam(
            outcome, "reservation", ENVIRONMENT,
            lambda: broker.check(reservation_resource),
        )

    # 4. F6 broker-config diff.
    if broker_contract_ref is not None:
        provider = broker_diff or UnconfiguredBrokerDiffProvider()
        _run_seam(
            outcome, "broker-diff", ENVIRONMENT,
            lambda: provider.diff(broker_contract_ref),
        )

    # 5. F16 perishable checklist (always consulted — the environment readiness
    #    gate; unconfigured => environment_fail).
    f16 = f16_provider or UnconfiguredF16ChecklistProvider()
    _run_seam(outcome, "f16-checklist", ENVIRONMENT, f16.checklist)

    return outcome
