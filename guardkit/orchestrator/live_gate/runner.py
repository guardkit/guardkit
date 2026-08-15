"""Live-gate runner orchestration + results-envelope emission (WS2 session B3).

Composes the six B3 modules — pre-flight → registry → executor → sweep →
poller (utility) → evidence — into one run that emits the scope-design §3
results envelope (an F4 ``ResultsEnvelope``), writes it under
``qa/gates/history/<run_id>.json``, and returns it (also printed on stdout by
the CLI for the forge adapter).

Deterministic (DF-015 clause 1): no model calls anywhere on this path. The only
non-pure inputs are the wall clock (injected via ``now_fn`` so runs are
reproducible in tests) and the gate subprocess (behind the executor's seam).

Verdict (DF-017): the envelope carries one of ``pass | fail | instrument_fail |
environment_fail``. ``instrument_fail`` / ``environment_fail`` come from
pre-flight short-circuits and never indict the system under test. B3 derives a
DETERMINISTIC v1 verdict (:func:`derive_verdict`); the richer disposition layer
— an undispositioned red is an unclosed run, revision entries, the F9 attempts
ledger — is session B4's ``disposition.py`` / ``verdict.py``, which enrich this
same envelope (``dispositions_ref`` / ``attempts_ledger_ref`` are left null
here for B4 to populate).
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Literal, Optional, Sequence

from guardkit.qa.formats import QAFormatError, validate_instance
from guardkit.qa.formats.gate_registry import (
    GateResult,
    ResultsEnvelope,
    SweepResult,
)
from guardkit.qa.formats.leak_sweep import LeakSweepManifest

from guardkit.orchestrator.live_gate.errors import LiveGateStubError
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
    BrokerDiffProvider,
    DefaultF16ChecklistProvider,
    F16ChecklistProvider,
    InstrumentSelfCheck,
    ReservationBroker,
    run_preflight,
)
from guardkit.orchestrator.live_gate.registry import (
    load_registry,
    registry_path_for,
    select_gates,
)
from guardkit.orchestrator.live_gate.sweep import (
    PageTextFetcher,
    UnconfiguredPageTextFetcher,
    run_sweep,
)

Verdict = Literal["pass", "fail", "instrument_fail", "environment_fail"]

#: History dir (relative to the target repo root) — the F4 envelope home.
HISTORY_DIRNAME = ("qa", "gates", "history")
#: Evidence base dir (relative to the target repo root).
EVIDENCE_DIRNAME = ("qa", "gates", "evidence")


def derive_verdict(
    preflight_classification: Optional[Literal["instrument_fail", "environment_fail"]],
    gate_results: Sequence[GateResult],
    sweep_result: Optional[SweepResult],
    *,
    sweep_unavailable: bool = False,
) -> Verdict:
    """Deterministic v1 verdict (DF-017 enum). Pure.

    - A pre-flight short-circuit (``instrument_fail`` / ``environment_fail``)
      wins outright — the system was never exercised.
    - Otherwise an OBSERVED red wins: any failed gate, or any sweep leak, is
      ``fail`` (a gate that ran and failed is a definite result; B4's
      disposition layer may later re-attribute it, but B3's deterministic
      verdict does not mask a real red behind an un-runnable sweep).
    - Otherwise a surface-bearing sweep that could not run is
      ``environment_fail`` — only downgrades an otherwise-passing run (we
      cannot claim clean surfaces we never swept).
    - Otherwise: ``pass``.
    """
    if preflight_classification is not None:
        return preflight_classification
    if any(gate_failed(g) for g in gate_results):
        return "fail"
    if sweep_result is not None and sweep_result.leaks:
        return "fail"
    if sweep_unavailable:
        return "environment_fail"
    return "pass"


class LiveGateRunner:
    """Deterministic live-gate runner. Seams are injected; the defaults are
    the loud ``Unconfigured*`` stubs / real subprocess runner — except F16,
    whose bare default is :class:`DefaultF16ChecklistProvider` (a real
    reachability check against each gate's registry ``base_url_env``, ruled
    08-15) so an unattended CLI run's verdict can follow the gates."""

    def __init__(
        self,
        repo_root: Path,
        *,
        gate_runner: Optional[GateScriptRunner] = None,
        page_text_fetcher: Optional[PageTextFetcher] = None,
        reservation_broker: Optional[ReservationBroker] = None,
        broker_diff: Optional[BrokerDiffProvider] = None,
        f16_provider: Optional[F16ChecklistProvider] = None,
        instrument_check: Optional[InstrumentSelfCheck] = None,
        reservation_resource: Optional[str] = None,
        broker_contract_ref: Optional[str] = None,
        gate_env: Optional[dict] = None,
        gate_timeout_s: float = DEFAULT_GATE_TIMEOUT_S,
        now_fn: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ) -> None:
        self.repo_root = Path(repo_root)
        self.gate_runner = gate_runner or SubprocessGateScriptRunner()
        self.page_text_fetcher = page_text_fetcher
        self.reservation_broker = reservation_broker
        self.broker_diff = broker_diff
        self.f16_provider = f16_provider
        self.instrument_check = instrument_check
        self.reservation_resource = reservation_resource
        self.broker_contract_ref = broker_contract_ref
        self.gate_env = gate_env if gate_env is not None else dict(os.environ)
        self.gate_timeout_s = gate_timeout_s
        self.now_fn = now_fn

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
        campaign: bool = False,  # v1: accepted; the F9 campaign loop is B4
    ) -> ResultsEnvelope:
        started = self.now_fn()
        run_id = self._make_run_id(feature_id, target_env, started)

        reg_path = registry_path or registry_path_for(self.repo_root)
        registry = load_registry(reg_path)  # raises QAFormatError loudly
        gates = select_gates(registry, requested_gate_ids)

        # Evidence dir is created up front — "evidence dirs produced
        # automatically" (may stay empty on a short-circuit; that is honest).
        evidence_dir = ensure_evidence_dir(self._evidence_base(), run_id)
        collector = EvidenceCollector()

        # F16 default wiring (ruled 08-15): a bare runner (no provider injected
        # — the `guardkit qa live-gate` CLI path) gets the minimal REAL
        # provider: reachability GET against each selected gate's registry
        # base_url env, remaining perishable prereqs recorded
        # declared-not-verified. Before this, every bare run short-circuited
        # to environment_fail on the Unconfigured stub (proven run
        # PILOT-HURL-local-20260814T205745Z) and the verdict could never
        # follow the gates.
        f16 = self.f16_provider or DefaultF16ChecklistProvider(
            gates, env=self.gate_env
        )

        preflight = run_preflight(
            gates,
            repo_root=self.repo_root,
            reservation_broker=self.reservation_broker,
            broker_diff=self.broker_diff,
            f16_provider=f16,
            instrument_check=self.instrument_check,
            reservation_resource=self.reservation_resource,
            broker_contract_ref=self.broker_contract_ref,
        )
        classification = preflight.classification

        gate_results: List[GateResult] = []
        sweep_result: Optional[SweepResult] = None
        sweep_unavailable = False

        if classification is None:
            # Pre-flight green: exercise the deployed app.
            gate_results = execute_gates(
                gates,
                repo_root=self.repo_root,
                runner=self.gate_runner,
                env=self.gate_env,
                timeout_s=self.gate_timeout_s,
            )
            collector.add_from_gate_results(gate_results)
            sweep_result, sweep_unavailable = self._maybe_sweep(gates)

        verdict = derive_verdict(
            classification, gate_results, sweep_result, sweep_unavailable=sweep_unavailable
        )

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
            sweep=sweep_result,
            poller_outcomes=[],  # populated by callers that watch async ops
            evidence_index_ref=self._rel(index_path) if index_path else None,
            dispositions_ref=None,  # B4
            attempts_ledger_ref=None,  # B4
            verdict=verdict,
        )
        self._write_envelope(envelope, run_id)
        return envelope

    def _maybe_sweep(self, gates) -> tuple[Optional[SweepResult], bool]:
        """Run the F3 sweep if a selected gate is surface-bearing.

        Returns ``(sweep_result, sweep_unavailable)``. A surface-bearing gate
        with no live page-text source makes the sweep un-runnable →
        ``sweep_unavailable=True`` (verdict environment_fail), never a vacuous
        pass.
        """
        sweep_gate = next((g for g in gates if g.leak_sweep_manifest_ref), None)
        if sweep_gate is None:
            return None, False
        manifest_path = (self.repo_root / sweep_gate.leak_sweep_manifest_ref).resolve()
        try:
            manifest: LeakSweepManifest = validate_instance("leak-sweep", manifest_path)  # type: ignore[assignment]
        except QAFormatError:
            # A malformed/missing manifest for a surface-bearing gate = cannot
            # sweep = environment/config not ready.
            return None, True
        fetcher = self.page_text_fetcher or UnconfiguredPageTextFetcher()
        try:
            return run_sweep(manifest, fetcher), False
        except LiveGateStubError:
            return None, True

    def _write_envelope(self, envelope: ResultsEnvelope, run_id: str) -> Path:
        history = self._history_dir()
        history.mkdir(parents=True, exist_ok=True)
        out = history / f"{run_id}.json"
        out.write_text(
            json.dumps(envelope.model_dump(mode="json"), indent=2) + "\n",
            encoding="utf-8",
        )
        return out
