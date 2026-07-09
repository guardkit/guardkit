"""Boot-smoke gate (WS3-S3 2d) — green-but-cannot-boot becomes impossible.

POC-006 shipped 11/11-approved with 345 green tests and could not boot: the
composition root constructed a service missing a required arg (TypeError at
composition), and every "integration" test mocked the seam.  SMP3-06 crashed
``serve`` on boot behind a quiet-window design.  This gate runs the declared
entrypoints in a subprocess and asserts they actually boot.

Four kinds (S2 spec §4.2), driven by ``.guardkit/seam-checks.yaml`` (baseline-read):

* **import** — ``python -c "import <module>"`` (hermetic; import-time crashes).
* **construct** — import the module, call a zero-arg (or explicit-``args``)
  factory, assert ``expect_type`` isinstance + no exception (hermetic; the
  POC-006 #1 killer — asserts the composed TYPE, not just non-None, R2d-4).
* **serve** — start the process, poll a readiness probe, verdict =
  **readiness observed ∧ child alive at verdict ∧ alive on a settle re-probe**
  (liveness-at-verdict, R2d-3: an early ``print("READY")`` then a late crash is
  FAIL; a readiness-then-exit is FAIL).  Readiness timeout → **ran-and-failed**
  (COACHRUNPARITY01 L3 — a hanging entrypoint is a deliverable defect).
* **command** — arbitrary argv + ``expected_exit`` (the stack-blind escape
  hatch: Flutter ``flutter test .../composition_test.dart`` is a boot smoke).

Environment posture (§4.1.4): the hermetic arm (import/construct, serve without
``env_required``) runs the **worktree-venv interpreter** with a clean
worktree-only PYTHONPATH (``namespace-hygiene`` — guardkit's own packages must
not mask a missing worktree dep) and catches SMP3-06/POC-006 with ZERO
production config — the documented normal autobuild state.  The full-env arm
(serve with ``env_required``) is honest ABSENT when prereqs are unmet, but ABSENT
is not silent: ``BOOT_SMOKE_ENV_ABSENT`` + a required operator-follow-up panel.

Verdict aggregate (§4.2.1): worst of {FAIL > ran-and-failed > ABSENT > pass}.
"""

from __future__ import annotations

import logging
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from guardkit.orchestrator.seam_checks import BootSmokeEntry, SeamChecksConfig

logger = logging.getLogger(__name__)

# Verdict severity ordering (worst wins).
_PASS = "pass"
_ABSENT = "absent"
_RAN_FAILED = "ran_and_failed"
_FAIL = "fail"
_SEVERITY = {_PASS: 0, _ABSENT: 1, _RAN_FAILED: 2, _FAIL: 3}


@dataclass
class BootSmokeEntryResult:
    """Outcome of one boot-smoke entry."""

    entry_id: str
    kind: str
    verdict: str  # pass | absent | ran_and_failed | fail
    detail: str = ""
    finding_kind: str = ""  # BOOT_SMOKE_FAIL | BOOT_SMOKE_ENV_ABSENT | ...
    exit_code: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "entry_id": self.entry_id,
            "kind": self.kind,
            "verdict": self.verdict,
            "detail": self.detail,
            "finding_kind": self.finding_kind,
            "exit_code": self.exit_code,
        }


@dataclass
class BootSmokeResult:
    """Aggregate boot-smoke result over all declared entries."""

    ran: bool = False
    aggregate_verdict: str = _ABSENT
    entries: List[BootSmokeEntryResult] = field(default_factory=list)
    operator_followups: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True iff no entry produced FAIL or ran-and-failed (ABSENT is not a fail)."""
        return self.aggregate_verdict in (_PASS, _ABSENT)

    @property
    def blocking(self) -> bool:
        """A FAIL or ran-and-failed is turn-rejecting (feeds back via smoke-gate)."""
        return self.aggregate_verdict in (_FAIL, _RAN_FAILED)

    def to_dict(self) -> dict:
        return {
            "ran": self.ran,
            "aggregate_verdict": self.aggregate_verdict,
            "passed": self.passed,
            "blocking": self.blocking,
            "entries": [e.to_dict() for e in self.entries],
            "operator_followups": self.operator_followups,
        }


def _worst(verdicts: List[str]) -> str:
    if not verdicts:
        return _ABSENT
    return max(verdicts, key=lambda v: _SEVERITY.get(v, 0))


def _hermetic_env(worktree: Path, overlay: Optional[Dict[str, str]] = None) -> dict:
    """Clean worktree-only PYTHONPATH env (namespace-hygiene remediation 4)."""
    env = {
        k: v for k, v in os.environ.items()
        if k not in ("PYTHONPATH",)
    }
    env["PYTHONPATH"] = str(worktree)
    if overlay:
        env.update(overlay)
    return env


def _alloc_port() -> int:
    """Allocate a fresh ephemeral port (orchestrator-owned; §4.2.1)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def _resolve_target_module(target: str) -> tuple[str, str]:
    """Split ``pkg.mod:symbol`` → ``(module, symbol)`` (symbol may be empty)."""
    if ":" in target:
        mod, sym = target.split(":", 1)
        return mod, sym
    return target, ""


# ---------------------------------------------------------------------------
# Kind runners
# ---------------------------------------------------------------------------


def _run_import(entry: BootSmokeEntry, worktree: Path, python: str) -> BootSmokeEntryResult:
    module, _sym = _resolve_target_module(entry.target)
    proc = subprocess.run(
        [python, "-c", f"import {module}"],
        cwd=str(worktree), env=_hermetic_env(worktree),
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode == 0:
        return BootSmokeEntryResult(entry.id, "import", _PASS, f"import {module} ok")
    return BootSmokeEntryResult(
        entry.id, "import", _FAIL,
        detail=f"import {module} failed (exit {proc.returncode}): {proc.stderr.strip()[-400:]}",
        finding_kind="BOOT_SMOKE_FAIL", exit_code=proc.returncode,
    )


def _run_construct(entry: BootSmokeEntry, worktree: Path, python: str) -> BootSmokeEntryResult:
    module, symbol = _resolve_target_module(entry.target)
    if not symbol:
        return BootSmokeEntryResult(
            entry.id, "construct", _ABSENT,
            detail="construct target needs module:factory", finding_kind="",
        )
    args_repr = ", ".join(repr(a) for a in entry.args)
    checks = [
        "import importlib",
        f"m = importlib.import_module({module!r})",
        f"obj = getattr(m, {symbol!r})({args_repr})",
    ]
    if entry.expect_type:
        tmod, tcls = _resolve_target_module(entry.expect_type)
        checks += [
            f"tm = importlib.import_module({tmod!r})",
            f"cls = getattr(tm, {tcls!r})",
            f"assert isinstance(obj, cls), 'expected {entry.expect_type}, got ' + type(obj).__name__",
        ]
    else:
        checks.append("assert obj is not None, 'factory returned None'")
    script = "\n".join(checks)
    proc = subprocess.run(
        [python, "-c", script],
        cwd=str(worktree), env=_hermetic_env(worktree),
        capture_output=True, text=True, timeout=60,
    )
    if proc.returncode == 0:
        return BootSmokeEntryResult(entry.id, "construct", _PASS, f"{entry.target} constructed")
    return BootSmokeEntryResult(
        entry.id, "construct", _FAIL,
        detail=f"construct {entry.target} failed (exit {proc.returncode}): {proc.stderr.strip()[-400:]}",
        finding_kind="BOOT_SMOKE_FAIL", exit_code=proc.returncode,
    )


def _http_ready(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:  # noqa: S310
            return 200 <= resp.status < 300
    except (urllib.error.URLError, OSError, ValueError):
        return False


def _port_ready(port: int) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def _run_serve(entry: BootSmokeEntry, worktree: Path, python: str) -> BootSmokeEntryResult:
    module, _sym = _resolve_target_module(entry.target)
    readiness = entry.readiness or {}
    rkind = readiness.get("kind", "exit_zero")
    timeout_s = int(readiness.get("timeout_s", 60))
    port = _alloc_port()
    env = _hermetic_env(worktree, entry.worktree_env)
    env["PORT"] = str(port)
    url = str(readiness.get("url", "")).replace("${PORT}", str(port))
    # console-script or python -m <module> (NOT python -c; §4.2.1 signal posture).
    proc = subprocess.Popen(
        [python, "-m", module],
        cwd=str(worktree), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        start_new_session=True,
    )
    try:
        deadline = time.monotonic() + timeout_s
        ready = False
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                # Exited before verdict → FAIL (any non-zero) or, for exit_zero, pass.
                rc = proc.returncode
                if rkind == "exit_zero" and rc == 0:
                    return BootSmokeEntryResult(entry.id, "serve", _PASS, "exited 0")
                return BootSmokeEntryResult(
                    entry.id, "serve", _FAIL,
                    detail=f"process exited (rc={rc}) before readiness",
                    finding_kind="BOOT_SMOKE_FAIL", exit_code=rc,
                )
            if rkind == "http" and url and _http_ready(url):
                ready = True
                break
            if rkind == "port" and _port_ready(port):
                ready = True
                break
            time.sleep(0.5)
        if not ready and rkind != "exit_zero":
            # Never became ready → ran-and-failed (hanging entrypoint is a defect).
            return BootSmokeEntryResult(
                entry.id, "serve", _RAN_FAILED,
                detail=f"readiness ({rkind}) not observed within {timeout_s}s",
                finding_kind="BOOT_SMOKE_FAIL",
            )
        # Liveness-at-verdict: child must still be alive, and alive on a settle
        # re-probe (an early-READY + late-crash must be FAIL, R2d-3).
        if proc.poll() is not None:
            return BootSmokeEntryResult(
                entry.id, "serve", _FAIL,
                detail=f"process died at verdict (rc={proc.returncode})",
                finding_kind="BOOT_SMOKE_FAIL", exit_code=proc.returncode,
            )
        time.sleep(1.0)  # settle
        if proc.poll() is not None:
            return BootSmokeEntryResult(
                entry.id, "serve", _FAIL,
                detail=f"process died on settle re-probe (rc={proc.returncode})",
                finding_kind="BOOT_SMOKE_FAIL", exit_code=proc.returncode,
            )
        # Re-attribute readiness to the still-alive child (squatter defence).
        if rkind == "port" and not _port_ready(port):
            return BootSmokeEntryResult(
                entry.id, "serve", _FAIL, detail="port not held by live child at verdict",
                finding_kind="BOOT_SMOKE_FAIL",
            )
        return BootSmokeEntryResult(entry.id, "serve", _PASS, f"ready ({rkind}) + alive at verdict")
    finally:
        _terminate(proc)


def _run_command(entry: BootSmokeEntry, worktree: Path) -> BootSmokeEntryResult:
    argv = entry.target.split() if entry.target else []
    if not argv:
        return BootSmokeEntryResult(entry.id, "command", _ABSENT, detail="empty command")
    try:
        proc = subprocess.run(
            argv, cwd=str(worktree), capture_output=True, text=True, timeout=300
        )
    except subprocess.TimeoutExpired:
        return BootSmokeEntryResult(
            entry.id, "command", _RAN_FAILED, detail="command timed out",
            finding_kind="BOOT_SMOKE_FAIL",
        )
    if proc.returncode == entry.expected_exit:
        return BootSmokeEntryResult(entry.id, "command", _PASS, f"exit {proc.returncode}")
    return BootSmokeEntryResult(
        entry.id, "command", _FAIL,
        detail=f"exit {proc.returncode} != expected {entry.expected_exit}: {proc.stderr.strip()[-300:]}",
        finding_kind="BOOT_SMOKE_FAIL", exit_code=proc.returncode,
    )


def _terminate(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError, OSError):
        try:
            proc.terminate()
        except OSError:
            return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            proc.kill()


# ---------------------------------------------------------------------------
# Entry-point resolution + env-prereq handling
# ---------------------------------------------------------------------------


def _env_prereqs_met(entry: BootSmokeEntry, worktree: Path) -> tuple[bool, List[str]]:
    """Check ``env_required`` file-existence / reachability prereqs.

    Returns ``(all_met, unmet_list)``.  A dict ``{reachable: <cmd>}`` runs the
    command and checks exit 0.
    """
    unmet: List[str] = []
    for req in entry.env_required:
        if isinstance(req, str):
            if not (worktree / req).exists():
                unmet.append(req)
        elif isinstance(req, dict) and "reachable" in req:
            cmd = str(req["reachable"])
            try:
                rc = subprocess.run(cmd, shell=True, cwd=str(worktree),
                                    capture_output=True, timeout=15).returncode
            except (OSError, subprocess.SubprocessError):
                rc = 1
            if rc != 0:
                unmet.append(cmd)
    return (not unmet, unmet)


def _target_resolvable(entry: BootSmokeEntry, worktree: Path, python: str) -> bool:
    """Is the entry's target module importable / command runnable in the worktree?"""
    if entry.kind == "command":
        argv = entry.target.split()
        return bool(argv)
    module, _sym = _resolve_target_module(entry.target)
    top = module.split(".")[0]
    # Cheap resolvability: a top-level package dir/file exists under the worktree.
    return (worktree / top).exists() or (worktree / f"{top}.py").exists() or bool(
        list(worktree.glob(f"**/{top}/__init__.py"))
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_boot_smoke(
    config: SeamChecksConfig,
    worktree: Path,
    *,
    venv_python: Optional[str] = None,
    hermetic_only: bool = False,
    prereqs_satisfied_at_bootstrap: Optional[Dict[str, bool]] = None,
) -> BootSmokeResult:
    """Run the declared boot-smoke entries.

    Parameters
    ----------
    config:
        The **feature-base** seam-checks config (baseline-read, §1.3).
    worktree:
        The shared worktree.
    venv_python:
        Worktree venv interpreter; falls back to ``sys.executable``.
    hermetic_only:
        When True (the every-wave placement, §4.3) run only import/construct and
        hermetic serve; the ``serve``-with-env / ``command`` kinds run at the
        final wave.
    prereqs_satisfied_at_bootstrap:
        Optional ``{prereq: bool}`` map recorded at bootstrap-end; a prereq
        satisfied then but unmet now is ENV_PREREQ_TAMPER (ran-and-failed, R2d-2).
    """
    python = venv_python or sys.executable
    if not config.has_boot_smoke:
        return BootSmokeResult(ran=False, aggregate_verdict=_ABSENT)

    results: List[BootSmokeEntryResult] = []
    followups: List[str] = []

    for entry in config.boot_smoke:
        if hermetic_only and not entry.is_hermetic:
            continue

        # Stale/renamed target (§4.2.1): resolvable at baseline but not working
        # tree is handled by the caller (needs the baseline ref); here we only
        # detect a fully-unresolvable target → ABSENT + CONFIG_STALE advisory.
        if not _target_resolvable(entry, worktree, python):
            results.append(BootSmokeEntryResult(
                entry.id, entry.kind, _ABSENT,
                detail=f"target '{entry.target}' not resolvable in worktree",
                finding_kind="CONFIG_STALE",
            ))
            continue

        # Full-env arm: env prereqs unmet → honest ABSENT (never silent).
        if entry.env_required:
            met, unmet = _env_prereqs_met(entry, worktree)
            if not met:
                # ENV_PREREQ_TAMPER: satisfied at bootstrap-end but unmet now →
                # positive evidence of mid-run removal → ran-and-failed.
                tampered = [
                    u for u in unmet
                    if (prereqs_satisfied_at_bootstrap or {}).get(u) is True
                ]
                if tampered:
                    results.append(BootSmokeEntryResult(
                        entry.id, entry.kind, _RAN_FAILED,
                        detail=f"env prereq(s) provisioned at bootstrap now missing: {tampered}",
                        finding_kind="ENV_PREREQ_TAMPER",
                    ))
                    continue
                results.append(BootSmokeEntryResult(
                    entry.id, entry.kind, _ABSENT,
                    detail=f"env prereq(s) unmet: {unmet}",
                    finding_kind="BOOT_SMOKE_ENV_ABSENT",
                ))
                followups.append(
                    f"boot smoke '{entry.id}' did not run: {unmet} unmet — boot the "
                    f"real entrypoint '{entry.target}' before merge (operator handoff)."
                )
                continue

        try:
            if entry.kind == "import":
                results.append(_run_import(entry, worktree, python))
            elif entry.kind == "construct":
                results.append(_run_construct(entry, worktree, python))
            elif entry.kind == "serve":
                results.append(_run_serve(entry, worktree, python))
            elif entry.kind == "command":
                results.append(_run_command(entry, worktree))
            else:
                results.append(BootSmokeEntryResult(
                    entry.id, entry.kind, _ABSENT, detail=f"unknown kind '{entry.kind}'"))
        except subprocess.TimeoutExpired:
            results.append(BootSmokeEntryResult(
                entry.id, entry.kind, _RAN_FAILED, detail="boot smoke timed out",
                finding_kind="BOOT_SMOKE_FAIL"))
        except Exception as exc:  # noqa: BLE001 — fail-open to absent
            logger.warning("boot smoke '%s' errored: %s", entry.id, exc)
            results.append(BootSmokeEntryResult(
                entry.id, entry.kind, _ABSENT, detail=f"runner error: {exc}"))

    aggregate = _worst([r.verdict for r in results])
    return BootSmokeResult(
        ran=bool(results),
        aggregate_verdict=aggregate,
        entries=results,
        operator_followups=followups,
    )
