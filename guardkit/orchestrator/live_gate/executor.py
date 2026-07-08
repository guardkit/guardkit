"""F4 · gate-script contract execution (WS2 session B3).

Runs one registered gate script and turns its result into a ``GateResult`` for
the envelope. Deterministic (DF-015 clause 1): the runner shells a registered
script and reads its exit code + stdout — no model calls on the execution path.

The F4 gate-script CONTRACT (``gate_registry.py``): **exit 0 = pass; a non-zero
exit MUST enumerate its failures as assertion results** (id, observed, expected,
evidence_ref) in a JSON object on stdout. Two realities this executor bridges:

- **Structured gates** (the contract): emit ``{"assertions": [...]}`` on stdout.
  Those assertions are used verbatim.
- **Legacy gates** (the B0-rescued lpa pack): exit 0/1 and print human text,
  no JSON. For these the executor records a single honest ``<gate>::exit``
  assertion whose status is derived DIRECTLY from the real exit code — never a
  fabricated per-behaviour pass.

Absence-of-failure defense (``.claude/rules/absence-of-failure-is-not-success``):
a non-zero exit can NEVER be read as green. If a gate exits non-zero but emits
no failing assertion (empty, or all-pass — a contract violation), the executor
appends a synthetic ``<gate>::exit`` FAIL so the exit code wins. The verdict
layer treats a gate as failed if its exit code is non-zero OR any assertion
failed.
"""

from __future__ import annotations

import json
import subprocess
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Mapping, Optional, Sequence

from guardkit.qa.formats.gate_registry import AssertionResult, GateEntry, GateResult

from guardkit.orchestrator.live_gate.errors import LiveGateError

#: Default per-gate wall-clock cap. A gate that STARTS and then hangs past this
#: is a genuine failure (the deployed app hung) — exit code 124, gate fails.
#: "Couldn't start at all" is pre-flight's environment_fail, not this.
DEFAULT_GATE_TIMEOUT_S: float = 900.0

#: Sentinel exit code for a gate that overran its timeout (mirrors the shell
#: 128+SIGTERM convention loosely; any non-zero would do — 124 is `timeout(1)`'s).
TIMEOUT_EXIT_CODE: int = 124

_MAX_DETAIL_CHARS = 2000


@dataclass(frozen=True)
class GateRun:
    """Raw result of executing a gate script (the seam's return shape)."""

    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False


class GateScriptRunner(ABC):
    """Live seam: execute a gate script and return its raw result.

    A signature-binding fake (LPA-13) implements this exact method in tests —
    no subprocess, but the same contract shape.
    """

    @abstractmethod
    def run(
        self,
        script_path: Path,
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout_s: float,
    ) -> GateRun:
        """Run ``script_path`` and return its exit code + captured streams."""


class SubprocessGateScriptRunner(GateScriptRunner):
    """Default runner: shell the gate script as a subprocess.

    ``.py`` scripts run under ``sys.executable``; anything else is executed
    directly (shebang / executable bit) — stack-blind, per
    ``stack-plugin-architecture.md`` (the rescued pack is Python; a JS/.NET gate
    is executed by its own runner via its shebang).
    """

    def _argv(self, script_path: Path) -> List[str]:
        if script_path.suffix == ".py":
            return [sys.executable, str(script_path)]
        return [str(script_path)]

    def run(
        self,
        script_path: Path,
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout_s: float,
    ) -> GateRun:
        try:
            proc = subprocess.run(
                self._argv(script_path),
                cwd=str(cwd),
                env=dict(env),
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            def _as_str(stream) -> str:
                if stream is None:
                    return ""
                return stream if isinstance(stream, str) else stream.decode("utf-8", "replace")

            return GateRun(
                exit_code=TIMEOUT_EXIT_CODE,
                stdout=_as_str(exc.stdout),
                stderr=_as_str(exc.stderr) + f"\n[timeout after {timeout_s}s]",
                timed_out=True,
            )
        return GateRun(exit_code=proc.returncode, stdout=proc.stdout, stderr=proc.stderr)


def _tail(text: str) -> str:
    text = (text or "").strip()
    if len(text) <= _MAX_DETAIL_CHARS:
        return text
    return "…" + text[-_MAX_DETAIL_CHARS:]


def _try_parse_envelope(stdout: str) -> Optional[dict]:
    """Find a gate-emitted JSON object carrying ``assertions`` on stdout.

    Tries the whole stdout first (a gate that prints only JSON), then scans
    lines from the bottom (a gate that prints human text then a JSON line).
    Returns the first mapping that has an ``assertions`` key, else None.
    """
    text = (stdout or "").strip()
    if not text:
        return None
    candidates = [text] + [ln for ln in reversed(text.splitlines()) if ln.strip().startswith("{")]
    for candidate in candidates:
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict) and "assertions" in data:
            return data
    return None


def _exit_assertion(gate_id: str, run: GateRun, *, forced_fail: bool = False) -> AssertionResult:
    """A single honest assertion reflecting the process exit code.

    status = pass IFF the gate exited 0 (and not force-failed). observed carries
    the exit code and, on failure, the tail of stderr/stdout so the envelope is
    diagnosable without re-running.
    """
    passed = run.exit_code == 0 and not forced_fail
    detail = f"exit_code={run.exit_code}"
    if run.timed_out:
        detail += " (timed out)"
    if not passed:
        tail = _tail(run.stderr) or _tail(run.stdout)
        if tail:
            detail += f"\n{tail}"
    return AssertionResult(
        id=f"{gate_id}::exit",
        status="pass" if passed else "fail",
        observed=detail,
        expected="exit_code=0",
    )


def parse_gate_result(gate_id: str, run: GateRun) -> GateResult:
    """Turn a raw ``GateRun`` into a contract-honouring ``GateResult`` (pure)."""
    parsed = _try_parse_envelope(run.stdout)
    assertions: List[AssertionResult]
    if parsed and parsed.get("assertions"):
        assertions = []
        for raw in parsed["assertions"]:
            # Validate against the F4 assertion shape — a malformed assertion is
            # a loud config error, not silently dropped.
            try:
                assertions.append(AssertionResult.model_validate(raw))
            except Exception as exc:  # pydantic ValidationError formats itself
                raise LiveGateError(
                    f"gate {gate_id!r} emitted an invalid assertion {raw!r}: {exc}"
                ) from exc
        # Absence-of-failure: a non-zero exit that enumerated no failing
        # assertion still fails — the exit code wins.
        if run.exit_code != 0 and not any(a.status == "fail" for a in assertions):
            assertions.append(_exit_assertion(gate_id, run, forced_fail=True))
    else:
        # Legacy exit-code-only gate: one honest exit assertion.
        assertions = [_exit_assertion(gate_id, run)]
    return GateResult(gate_id=gate_id, exit_code=run.exit_code, assertions=assertions)


def gate_failed(result: GateResult) -> bool:
    """A gate failed if its exit code is non-zero OR any assertion failed."""
    return result.exit_code != 0 or any(a.status == "fail" for a in result.assertions)


def execute_gate(
    gate: GateEntry,
    *,
    repo_root: Path,
    runner: GateScriptRunner,
    env: Optional[Mapping[str, str]] = None,
    timeout_s: float = DEFAULT_GATE_TIMEOUT_S,
) -> GateResult:
    """Execute one registered gate and return its ``GateResult``.

    Raises:
        LiveGateError: the gate script does not exist at ``repo_root/gate.path``
            (an instrument fault pre-flight's self-check should have caught;
            defended here too), or the gate emitted an invalid assertion.
    """
    script_path = (repo_root / gate.path).resolve()
    if not script_path.exists():
        raise LiveGateError(
            f"gate {gate.id!r} script not found at {script_path} "
            f"(registry path {gate.path!r} relative to {repo_root})"
        )
    run = runner.run(
        script_path,
        cwd=repo_root,
        env=dict(env) if env is not None else {},
        timeout_s=timeout_s,
    )
    return parse_gate_result(gate.id, run)


def execute_gates(
    gates: Sequence[GateEntry],
    *,
    repo_root: Path,
    runner: GateScriptRunner,
    env: Optional[Mapping[str, str]] = None,
    timeout_s: float = DEFAULT_GATE_TIMEOUT_S,
) -> List[GateResult]:
    """Execute each gate in order (single run per gate — v1).

    The F9 campaign loop (probe-before-rerun, warm-up, confound disambiguation)
    is session B4's; v1 runs each selected gate once and B4's disposition/
    attempts-ledger layer snaps onto these results.
    """
    return [
        execute_gate(g, repo_root=repo_root, runner=runner, env=env, timeout_s=timeout_s)
        for g in gates
    ]
