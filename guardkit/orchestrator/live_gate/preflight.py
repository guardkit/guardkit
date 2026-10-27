"""Pre-flight: is the deployed app there to check? (WS2 session B3).

Scope-design §3 step 1. Pre-flight runs BEFORE any gate and decides whether the
run can proceed, or must short-circuit to an honest ``environment_fail``
verdict (DF-017 — that never indicts the system under test).

Since the cull (27 October 2026) pre-flight is one thing: a reachability check
against each selected gate's address (:class:`DefaultF16ChecklistProvider`).
An address that is not set, or that nothing answers at, means the gates
could not have reached anything, so the run is ``environment_fail`` rather
than a feature ``fail``. A caller may hand in its own
:class:`F16ChecklistProvider` instead.
"""

from __future__ import annotations

import os
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence

from guardkit.qa.formats.gate_registry import GateEntry, PreflightResult

#: The one check category pre-flight records.
ENVIRONMENT = "environment"


@dataclass(frozen=True)
class SeamResult:
    """Uniform return shape for one pre-flight check."""

    ok: bool
    detail: str


class F16ChecklistProvider(ABC):
    """The environment readiness checklist a run consults before any gate."""

    @abstractmethod
    def checklist(self) -> Sequence[SeamResult]:
        """Return the current check outcomes."""


def gate_address_refusal(name: str, value: str) -> Optional[str]:
    """Why the gate address ``value`` (read from setting ``name``) may not be
    used, or ``None`` (13 October 2026). The sentence names the setting and
    never shows the value.

    Any ``@`` anywhere is refused, however the value parses: it is how a user
    name and password ride in an address (``user:secret@host`` even parses
    with ``user`` as the scheme and nothing as the host), and the factory
    does not pass credentials to project commands.
    """
    if "@" in value:
        return (
            f"could not run: the gate address setting {name} carries a user name "
            f"and password, and the factory does not pass credentials to project "
            f"commands"
        )
    return None


#: Default wall-clock cap for one reachability GET.
DEFAULT_REACHABILITY_TIMEOUT_S: float = 5.0


class DefaultF16ChecklistProvider(F16ChecklistProvider):
    """The reachability check every bare run uses.

    For each distinct ``target.base_url_env`` declared by the selected gates,
    read that setting and GET the URL — ANY HTTP answer (any status code,
    including 4xx/5xx) proves something is listening, so the target is ready.
    An unset setting, or a connection-level failure (refused, DNS, timeout),
    is not ready → ``environment_fail``, never a product ``fail`` charged to
    gates that could not have reached anything.
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
            refusal = gate_address_refusal(var, base_url)
            if refusal is not None:
                # Never reached and never echoed: the sentence names the
                # setting only (the runner refuses these before pre-flight).
                results.append(SeamResult(ok=False, detail=refusal))
                continue
            results.append(self._reachability(var, base_url))
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


@dataclass
class PreflightOutcome:
    """Aggregate pre-flight result.

    ``checks`` is the envelope-facing list ({name, category, ok, detail}).
    """

    checks: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def environment_ok(self) -> bool:
        return all(c["ok"] for c in self.checks)

    @property
    def classification(self) -> Optional[Literal["environment_fail"]]:
        """The short-circuit verdict, or None to proceed to gate execution."""
        if not self.environment_ok:
            return "environment_fail"
        return None

    def to_schema(self) -> PreflightResult:
        """Project onto the F4 ``PreflightResult`` envelope shape."""
        return PreflightResult(checks=list(self.checks), instrument_ok=True)

    # internal
    def _add(self, name: str, category: str, ok: bool, detail: str) -> None:
        self.checks.append({"name": name, "category": category, "ok": ok, "detail": detail})


def run_preflight(
    gates: Sequence[GateEntry],
    *,
    f16_provider: Optional[F16ChecklistProvider] = None,
) -> PreflightOutcome:
    """Run pre-flight for the selected gates; return the outcome.

    ``f16_provider`` defaults to :class:`DefaultF16ChecklistProvider` over
    ``gates`` and this process's environment.
    """
    outcome = PreflightOutcome()
    provider = f16_provider or DefaultF16ChecklistProvider(gates)
    for i, result in enumerate(provider.checklist()):
        outcome._add(f"f16-checklist[{i}]", ENVIRONMENT, result.ok, result.detail)
    return outcome
