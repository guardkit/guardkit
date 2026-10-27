"""Live-gate runner orchestration + results-envelope emission (WS2 session B3).

Composes pre-flight → registry → executor → evidence into one run that emits
the scope-design §3 results envelope (an F4 ``ResultsEnvelope``), writes it
under ``qa/gates/history/<run_id>.json``, and returns it (also printed on
stdout by the CLI for the forge adapter).

Deterministic (DF-015 clause 1): no model calls anywhere on this path. The only
non-pure inputs are the wall clock (injected via ``now_fn`` so runs are
reproducible in tests) and the gate subprocess (behind the executor's seam).

Verdict (DF-017): the envelope carries ``pass``, ``fail`` or
``environment_fail``. ``environment_fail`` comes from the pre-flight
reachability check and never indicts the system under test. Since the cull
(27 October 2026) the verdict is the gates' own result: any gate that exited
non-zero or reported a failing assertion is ``fail``. The leak sweep, the
disposition and campaign layers and the attempts ledger are gone, so
``sweep``, ``dispositions_ref`` and ``attempts_ledger_ref`` are always null.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Literal, Mapping, Optional, Sequence

from guardkit.qa.formats.gate_registry import (
    GateEntry,
    GateResult,
    ResultsEnvelope,
)

from guardkit.orchestrator.live_gate.errors import LiveGateError
from guardkit.orchestrator.project_command_env import main_checkout_environment
from guardkit.orchestrator.live_gate.evidence import (
    EvidenceCollector,
    ensure_evidence_dir,
)
from guardkit.orchestrator.live_gate.executor import (
    DEFAULT_GATE_TIMEOUT_S,
    GateScriptRunner,
    SubprocessGateScriptRunner,
    execute_gates,
    gate_failed,
)
from guardkit.orchestrator.live_gate.preflight import (
    DefaultF16ChecklistProvider,
    F16ChecklistProvider,
    run_preflight,
)
from guardkit.orchestrator.live_gate.registry import (
    load_registry,
    registry_path_for,
    select_gates,
)

Verdict = Literal["pass", "fail", "instrument_fail", "environment_fail"]

#: History dir (relative to the target repo root) — the F4 envelope home.
HISTORY_DIRNAME = ("qa", "gates", "history")
#: Evidence base dir (relative to the target repo root).
EVIDENCE_DIRNAME = ("qa", "gates", "evidence")


def derive_verdict(
    preflight_classification: Optional[Literal["instrument_fail", "environment_fail"]],
    gate_results: Sequence[GateResult],
) -> Verdict:
    """The run's verdict (DF-017 enum). Pure.

    - A pre-flight short-circuit wins outright — the system was never
      exercised.
    - Otherwise any failed gate is ``fail``.
    - Otherwise: ``pass``.
    """
    if preflight_classification is not None:
        return preflight_classification
    if any(gate_failed(g) for g in gate_results):
        return "fail"
    return "pass"


def _gate_scripts_env(repo_root: Path, addresses: Mapping[str, str]) -> dict:
    """The gate scripts' environment, built from nothing, plus the gates'
    checked addresses. A module-level function, so the process-launch guard
    can rely on it (a method could be overridden)."""
    return main_checkout_environment(repo_root, additions=dict(addresses))


class LiveGateRunner:
    """Deterministic live-gate runner. The gate runner and the pre-flight
    checklist may be injected; the defaults are the real subprocess runner
    and :class:`DefaultF16ChecklistProvider` (a real reachability check
    against each gate's registry ``base_url_env``, ruled 08-15)."""

    def __init__(
        self,
        repo_root: Path,
        *,
        gate_runner: Optional[GateScriptRunner] = None,
        f16_provider: Optional[F16ChecklistProvider] = None,
        gate_env: Optional[dict] = None,
        gate_timeout_s: float = DEFAULT_GATE_TIMEOUT_S,
        now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.repo_root = Path(repo_root)
        self.gate_runner = gate_runner or SubprocessGateScriptRunner()
        self.f16_provider = f16_provider
        # The gate scripts' environment is always built from nothing
        # (:meth:`_gate_script_env`), never a copy of this process's, which
        # holds the factory's credentials. ``gate_env``, when a caller hands
        # one in, is where the reachability check and the gates' declared
        # base URLs are read from instead of this process's environment.
        self.gate_env = gate_env
        self.gate_timeout_s = gate_timeout_s
        self.now_fn = now_fn

    def _gate_addresses(self, gates: Sequence[GateEntry]) -> Dict[str, str]:
        """Each selected gate's address, checked BEFORE anything reads it.

        13 October 2026. The registry names, per gate, the setting its
        address is read from (``base_url_env``). That name must be one a
        project may declare (not one of the factory's own, not
        credential-shaped), and its value, read from ``gate_env`` when a
        caller handed one in or else this process, must contain no ``@``
        anywhere (no user name or password, however it parses). Any refusal
        names the setting and never shows a value, and happens before the
        pre-flight reachability check, which records the address in the
        run's history. Only these checked values
        reach the reachability check and the gate scripts. An address that
        is not set is left out (the reachability check says so).
        """
        from guardkit.orchestrator.launch_declaration import declared_setting_refusal
        from guardkit.orchestrator.live_gate.preflight import gate_address_refusal

        source = self.gate_env if self.gate_env is not None else os.environ
        addresses: Dict[str, str] = {}
        for gate in gates:
            name = gate.target.base_url_env
            refusal = declared_setting_refusal(name)
            if refusal is not None:
                raise LiveGateError(
                    f"could not run: gate {gate.id!r} reads its address from a "
                    f"setting the factory does not pass to project commands: "
                    f"{refusal}"
                )
            value = source.get(name)
            if value is None:
                continue
            # Any "@" anywhere is refused by the setting's name; the value is
            # never shown.
            refusal = gate_address_refusal(name, value)
            if refusal is not None:
                raise LiveGateError(refusal)
            addresses[name] = value
        return addresses

    def _gate_script_env(self, addresses: Mapping[str, str]) -> dict:
        """The gate scripts' environment, built from nothing (13 October 2026).

        ``project_command_env`` with the repository's ``launch:`` block, plus
        the gates' checked addresses (:meth:`_gate_addresses`): the registry
        is the project's own statement that its gates read them.
        """
        return _gate_scripts_env(self.repo_root, addresses)

    def _history_dir(self) -> Path:
        return self.repo_root.joinpath(*HISTORY_DIRNAME)

    def _evidence_base(self) -> Path:
        return self.repo_root.joinpath(*EVIDENCE_DIRNAME)

    def _make_run_id(self, feature_id: str, target_env: str, started: datetime) -> str:
        stamp = started.strftime("%Y%m%dT%H%M%SZ")
        return f"{feature_id}-{target_env}-{stamp}"

    def _rel(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.repo_root))
        except ValueError:
            return str(path)

    def run(
        self,
        feature_id: str,
        target_env: str,
        *,
        requested_gate_ids: Optional[Sequence[str]] = None,
        registry_path: Optional[Path] = None,
    ) -> ResultsEnvelope:
        started = self.now_fn()
        run_id = self._make_run_id(feature_id, target_env, started)

        reg_path = registry_path or registry_path_for(self.repo_root)
        registry = load_registry(reg_path)  # raises QAFormatError loudly
        gates = select_gates(registry, requested_gate_ids)
        # Checked before anything reads or records them (raises by name).
        addresses = self._gate_addresses(gates)

        # Evidence dir is created up front — "evidence dirs produced
        # automatically" (may stay empty on a short-circuit; that is honest).
        evidence_dir = ensure_evidence_dir(self._evidence_base(), run_id)
        collector = EvidenceCollector()

        # A bare runner (no provider injected — the `guardkit qa live-gate`
        # CLI path) gets the reachability check against each selected gate's
        # registry base_url env (ruled 08-15). It reads only the checked
        # addresses, never this process's own environment (13 October 2026).
        f16 = self.f16_provider or DefaultF16ChecklistProvider(
            gates, env=addresses
        )

        preflight = run_preflight(gates, f16_provider=f16)
        classification = preflight.classification

        gate_results: List[GateResult] = []

        if classification is None:
            # Pre-flight green: exercise the deployed app.
            try:
                env = _gate_scripts_env(self.repo_root, addresses)
            except OSError as exc:
                raise LiveGateError(
                    f"the gate scripts could not be given their environment: {exc}"
                ) from exc
            gate_results = execute_gates(
                gates,
                repo_root=self.repo_root,
                runner=self.gate_runner,
                env=env,
                timeout_s=self.gate_timeout_s,
            )
            collector.add_from_gate_results(gate_results)

        verdict = derive_verdict(classification, gate_results)

        index_path = collector.write_index(evidence_dir)
        finished = self.now_fn()

        envelope = ResultsEnvelope(
            format_version=ResultsEnvelope.CURRENT_FORMAT_VERSION,
            run_id=run_id,
            feature_id=feature_id,
            target_env=target_env,
            started=started.isoformat(),
            finished=finished.isoformat(),
            preflight=preflight.to_schema(),
            gates=gate_results,
            evidence_index_ref=self._rel(index_path) if index_path else None,
            verdict=verdict,
        )
        self._write_envelope(envelope, run_id)
        return envelope

    def _write_envelope(self, envelope: ResultsEnvelope, run_id: str) -> Path:
        history = self._history_dir()
        history.mkdir(parents=True, exist_ok=True)
        out = history / f"{run_id}.json"
        out.write_text(
            json.dumps(envelope.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        return out
