"""Stage 1 · MACHINE-VERIFY STAGE — mechanize the coordinator's by-hand VERIFY.

H-A RETIRE-THE-COORDINATOR, Stage 1 (see
``docs/ways-of-working/retire-the-coordinator-build-handoff-2026-07-17.md`` §3).

Today one feature reaches "merged" only after a human coordinator runs the
round-21 checklist by hand: re-run the suite in a throwaway worktree, prove any
red also failed on the pre-build base (so it is pre-existing, not introduced),
sweep the committed diff for build-state junk, and drive the registered live
gate. This module turns that checklist into code and emits **one** receipt-
bearing signal — ``clean`` or ``catch`` — at merge time.

**Report-only.** The stage does NOT merge, gate, or re-add auto-merge (that is
Stage 3). It surfaces ``disposition_required`` so a human still dispositions the
merge; it is safe and useful the day it lands.

The three checks (each lifted from an existing, tested primitive — never a
re-implementation):

* **A2 charged-failures at merge (the CATCH signal).** Lift
  ``baseline.compute_charged_failures`` (``observed - (baseline ∪ ledger)``) from
  the Coach loop to merge time. Empty ⇒ every red is pre-existing on base ⇒
  clean. Non-empty ⇒ the branch introduced a regression ⇒ CATCH, naming the
  charged node IDs. The branch scope is fixed by
  ``seam_checks.resolve_feature_base`` (the recorded feature base, else
  ``git merge-base HEAD <base_branch>``).
* **A4 junk tripwire over the COMMITTED diff (the 96FC lesson).** The existing
  ``preflight_ignore_gate`` guards *planned* targets pre-turn-1 — it never sees
  the committed diff. Here we sweep the actual committed diff: a path that is
  git-ignored yet committed (rode in via a selective merge) OR lives under a
  build-state fossil prefix (``.guardkit/worktrees/`` / ``.guardkit/autobuild/``)
  trips the wire. Feature specs and QA (``.guardkit/features/`` / ``qa/``) are
  kept. A tripped wire is also a CATCH — it is exactly the junk the coordinator
  removed by hand (api_test ``e2b6d54``: 164 fossils).
* **A5 registered-gate live drive.** Re-run the target's REGISTERED gates (F4
  registry — never an ad-hoc command) against the running service. Honest
  caveat: with no service up this is an ``environment_fail`` (or ``skipped`` when
  no registry is configured), **not** a product fail — recorded as such, and it
  NEVER flips the branch signal.

The CATCH signal is deterministic and receipt-bearing: ``charged_failures``
non-empty OR the junk wire tripped. The live-drive verdict is informational — an
environment problem is never a branch failure (spec §3, A5).
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Sequence, Set

from guardkit.orchestrator.baseline import (
    BaselineResult,
    compute_charged_failures,
)
from guardkit.orchestrator.preflight_ignore_gate import check_ignore_one

logger = logging.getLogger(__name__)

# --- signal constants (module-level so callers compare without the dataclass) -
SIGNAL_CLEAN = "clean"
SIGNAL_CATCH = "catch"

# --- junk-sweep verdicts -----------------------------------------------------
JUNK_HELD = "held"
JUNK_TRIPPED = "tripped"

# --- live-drive verdicts -----------------------------------------------------
LIVE_PASS = "pass"
LIVE_PRODUCT_FAIL = "product_fail"
LIVE_ENVIRONMENT_FAIL = "environment_fail"
LIVE_SKIPPED = "skipped"

#: Build-state fossil prefixes — a committed path under these is junk that rode
#: in via a selective merge (96FC lesson: api_test ``e2b6d54`` removed 164
#: ``.guardkit/autobuild/**`` fossils; the pinned ``.gitignore`` blocks both).
FOSSIL_PREFIXES = (".guardkit/worktrees/", ".guardkit/autobuild/")

#: Kept-on-purpose prefixes — feature specs and QA are tracked deliberately and
#: MUST NOT trip the wire even though they live under ``.guardkit`` / are broad.
KEEP_PREFIXES = (".guardkit/features/", "qa/")

_GIT_TIMEOUT_SECONDS = 60


# ---------------------------------------------------------------------------
# Report shape
# ---------------------------------------------------------------------------


@dataclass
class MachineVerifyReport:
    """The one signal + receipt the machine-verify stage emits (report-only)."""

    signal: str  # SIGNAL_CLEAN | SIGNAL_CATCH
    charged_failures: List[str] = field(default_factory=list)
    junk_verdict: str = JUNK_HELD  # JUNK_HELD | JUNK_TRIPPED
    junk_paths: List[str] = field(default_factory=list)
    live_verdict: str = LIVE_SKIPPED  # LIVE_PASS | LIVE_ENVIRONMENT_FAIL | ...
    live_detail: str = ""
    feature_base: Optional[str] = None
    observed_available: bool = True

    @property
    def disposition_required(self) -> bool:
        """A human must disposition when the stage caught anything (report-only).

        CATCH ⇒ True. Also True when the suite's observed reds could not be
        obtained (we cannot prove clean-on-base, so we fail toward attention —
        the honest direction, mirroring the baseline diff's fail-closed rule).
        """
        return self.signal == SIGNAL_CATCH or not self.observed_available

    def to_dict(self) -> dict:
        return {
            "signal": self.signal,
            "charged_failures": list(self.charged_failures),
            "junk_verdict": self.junk_verdict,
            "junk_paths": list(self.junk_paths),
            "live_verdict": self.live_verdict,
            "live_detail": self.live_detail,
            "feature_base": self.feature_base,
            "observed_available": self.observed_available,
            "disposition_required": self.disposition_required,
        }

    def receipt_lines(self) -> List[str]:
        """Human-readable receipt naming the three verdicts (spec §3 done-test)."""
        head = (
            "MACHINE-VERIFY: CLEAN"
            if self.signal == SIGNAL_CLEAN
            else "MACHINE-VERIFY: CATCH — regression / junk introduced by this branch"
        )
        lines = [head]
        if self.charged_failures:
            lines.append(
                f"  charged_failures={len(self.charged_failures)} "
                f"(new reds not present on the feature base):"
            )
            lines.extend(f"    - {nid}" for nid in self.charged_failures)
        else:
            avail = "0" if self.observed_available else "0 (suite reds UNAVAILABLE)"
            lines.append(f"  charged_failures={avail}")
        if self.junk_verdict == JUNK_TRIPPED:
            lines.append(f"  junk={JUNK_TRIPPED} (build-state fossils in the committed diff):")
            lines.extend(f"    - {p}" for p in self.junk_paths)
        else:
            lines.append(f"  junk={JUNK_HELD}")
        detail = f" ({self.live_detail})" if self.live_detail else ""
        lines.append(f"  live={self.live_verdict}{detail}")
        if self.feature_base:
            lines.append(f"  feature_base={self.feature_base}")
        return lines


# ---------------------------------------------------------------------------
# A2 · charged failures, lifted to merge time
# ---------------------------------------------------------------------------


def charged_failures_at_merge(
    observed_node_ids: Sequence[str],
    baseline_result: Optional[BaselineResult],
    ledger_ids: Optional[Set[str]] = None,
    authored_test_files: Sequence[str] = (),
) -> List[str]:
    """The reds this branch introduced (``observed - (baseline ∪ ledger)``).

    A thin merge-time wrapper over ``baseline.compute_charged_failures`` — the
    identical computation the Coach loop runs per-feature (``coach_validator.
    _apply_baseline_diff``), lifted so it runs once at the merge boundary. The
    diff only ever REMOVES excused charges (the honest direction); an empty
    result means every observed red is pre-existing on the feature base.
    """
    baseline_ids = baseline_result.failing_node_ids if baseline_result else []
    return compute_charged_failures(
        observed_node_ids=observed_node_ids,
        baseline_node_ids=baseline_ids,
        ledger_ids=set(ledger_ids or set()),
        authored_test_files=authored_test_files,
    )


# ---------------------------------------------------------------------------
# A4 · junk tripwire over the committed diff
# ---------------------------------------------------------------------------


def _normalise(path: str) -> str:
    """Repo-relative posix path — strips a leading ``./`` (never a leading dot).

    ``str.lstrip("./")`` would eat the leading dot of ``.guardkit`` — a real
    footgun for exactly the fossil paths this stage exists to catch. Strip only
    an explicit ``./`` prefix.
    """
    p = path.strip().replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def _is_kept(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in KEEP_PREFIXES)


def _is_fossil_prefix(path: str) -> bool:
    return any(path.startswith(prefix) for prefix in FOSSIL_PREFIXES)


def sweep_committed_junk(
    worktree_path: Path, committed_paths: Sequence[str]
) -> tuple[str, List[str]]:
    """Sweep the committed diff for build-state fossils (96FC lesson).

    A committed path trips the wire when it is NOT under a kept prefix
    (``.guardkit/features/`` / ``qa/``) AND either:

    * lives under a fossil prefix (``.guardkit/worktrees/`` /
      ``.guardkit/autobuild/``) — the api_test ``e2b6d54`` class of junk; or
    * is git-ignored yet committed anyway (``check_ignore_one`` returns a rule)
      — a fossil that rode in via a selective merge.

    Returns ``(verdict, junk_paths)`` where ``verdict`` is ``JUNK_TRIPPED`` when
    ``junk_paths`` is non-empty, else ``JUNK_HELD``. ``junk_paths`` preserves
    first-seen order and is deduplicated.
    """
    junk: List[str] = []
    seen: Set[str] = set()
    for raw in committed_paths:
        norm = _normalise(raw)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        if _is_kept(norm):
            continue
        if _is_fossil_prefix(norm):
            junk.append(norm)
            continue
        # Ignored-but-committed = a fossil that laundered in via a selective
        # merge. ``check_ignore_one`` returns the matched rule (or None).
        if check_ignore_one(worktree_path, norm) is not None:
            junk.append(norm)
    verdict = JUNK_TRIPPED if junk else JUNK_HELD
    return verdict, junk


def committed_diff_paths(
    worktree_path: Path, feature_base: Optional[str]
) -> List[str]:
    """Committed paths on this branch since the feature base (deterministic).

    ``git diff --name-only --no-renames <feature_base>..HEAD`` — the ACTUAL
    committed state (not the working tree; not planned targets). Sorted for a
    deterministic sweep (the ``a58bf31`` footgun: never depend on unstaged /
    ordering artifacts). Fails open to ``[]`` — an unavailable diff leaves the
    junk verdict ``held``, never a false CATCH.
    """
    if not feature_base:
        return []
    try:
        proc = subprocess.run(
            ["git", "diff", "--name-only", "--no-renames", f"{feature_base}..HEAD"],
            cwd=str(worktree_path),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("machine-verify: committed diff unavailable (%s)", exc)
        return []
    if proc.returncode != 0:
        logger.debug(
            "machine-verify: `git diff` returned %d: %s",
            proc.returncode,
            proc.stderr.strip(),
        )
        return []
    return sorted(ln for ln in proc.stdout.splitlines() if ln.strip())


# ---------------------------------------------------------------------------
# A5 · registered-gate live drive (report-only; env problems never fail)
# ---------------------------------------------------------------------------


def drive_registered_gates(
    repo_root: Path,
    *,
    service_ready: bool = False,
    runner=None,
) -> tuple[str, str]:
    """Drive the target's REGISTERED gates (F4 registry) against the service.

    Order (spec §3, A5):

    * no ``qa/gates/registry.yaml`` ⇒ ``LIVE_SKIPPED`` (no target configured);
    * registry present but no reachable service (``service_ready`` False, the
      in-window default — no service is brought up, no seats, no docker) ⇒
      ``LIVE_ENVIRONMENT_FAIL``, naming the gates that WOULD run. **This never
      fails the branch** — an environment problem is not a product fail;
    * ``service_ready`` with a ``runner`` ⇒ execute the selected gates once and
      return ``LIVE_PASS`` / ``LIVE_PRODUCT_FAIL``.

    Returns ``(verdict, detail)``. Any error resolves to ``LIVE_ENVIRONMENT_FAIL``
    — the honest, non-branch-failing direction.
    """
    # Imported lazily so this report-only stage never hard-depends on the live
    # gate package loading (fail-open on any import problem).
    try:
        from guardkit.orchestrator.live_gate.registry import (
            load_registry,
            registry_path_for,
            select_gates,
        )
    except Exception as exc:  # noqa: BLE001 — fail open to environment_fail
        return LIVE_ENVIRONMENT_FAIL, f"live-gate package unavailable: {exc}"

    registry_path = registry_path_for(Path(repo_root))
    if not registry_path.exists():
        return LIVE_SKIPPED, "no qa/gates/registry.yaml configured"

    try:
        registry = load_registry(registry_path)
        gates = select_gates(registry)
    except Exception as exc:  # noqa: BLE001 — malformed registry is an env fault
        return LIVE_ENVIRONMENT_FAIL, f"registry load/select failed: {exc}"

    if not gates:
        return LIVE_SKIPPED, "registry present but selects no gates"

    gate_ids = ", ".join(g.id for g in gates)
    if not service_ready or runner is None:
        return (
            LIVE_ENVIRONMENT_FAIL,
            f"no running service — {len(gates)} registered gate(s) not driven "
            f"({gate_ids}); environment_fail, not a product fail",
        )

    try:
        from guardkit.orchestrator.live_gate.executor import (
            execute_gates,
            gate_failed,
        )

        results = execute_gates(gates, repo_root=Path(repo_root), runner=runner)
    except Exception as exc:  # noqa: BLE001 — drive fault is environmental
        return LIVE_ENVIRONMENT_FAIL, f"gate drive failed: {exc}"

    failed = [r.gate_id for r in results if gate_failed(r)]
    if failed:
        return LIVE_PRODUCT_FAIL, f"registered gate(s) failed: {', '.join(failed)}"
    return LIVE_PASS, f"{len(results)} registered gate(s) green ({gate_ids})"


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------


def assemble_report(
    charged_failures: Sequence[str],
    junk_verdict: str,
    junk_paths: Sequence[str],
    live_verdict: str,
    live_detail: str = "",
    feature_base: Optional[str] = None,
    observed_available: bool = True,
) -> MachineVerifyReport:
    """Assemble the final signal from the three verdicts (pure).

    CATCH iff the branch introduced a regression (``charged_failures`` non-empty)
    OR the junk wire tripped. The live-drive verdict is informational and NEVER
    flips the signal — an environment problem is not a branch failure (spec §3,
    A5). When the suite's observed reds are unavailable the signal stays clean
    but ``disposition_required`` is forced True (the report property).
    """
    caught = bool(charged_failures) or junk_verdict == JUNK_TRIPPED
    return MachineVerifyReport(
        signal=SIGNAL_CATCH if caught else SIGNAL_CLEAN,
        charged_failures=list(charged_failures),
        junk_verdict=junk_verdict,
        junk_paths=list(junk_paths),
        live_verdict=live_verdict,
        live_detail=live_detail,
        feature_base=feature_base,
        observed_available=observed_available,
    )


def run_machine_verify(
    worktree_path: Path,
    *,
    observed_node_ids: Optional[Sequence[str]],
    baseline_result: Optional[BaselineResult],
    ledger_ids: Optional[Set[str]] = None,
    feature_base: Optional[str] = None,
    authored_test_files: Sequence[str] = (),
    service_ready: bool = False,
    gate_runner=None,
) -> MachineVerifyReport:
    """Run the three merge-time checks and assemble one clean/CATCH report.

    Pure orchestration over the three seams — every input is explicit so the
    stage is hermetic (fixture worktrees, no network, no seats). The
    ``_finalize_phase`` wiring gathers the inputs (feature base, baseline,
    observed reds) and calls this.

    ``observed_node_ids=None`` means the suite's reds could not be obtained; the
    charged computation is skipped and ``observed_available`` is recorded False
    (forces ``disposition_required`` — we cannot prove clean-on-base).
    """
    if observed_node_ids is None:
        charged: List[str] = []
        observed_available = False
    else:
        charged = charged_failures_at_merge(
            observed_node_ids=observed_node_ids,
            baseline_result=baseline_result,
            ledger_ids=ledger_ids,
            authored_test_files=authored_test_files,
        )
        observed_available = True

    committed = committed_diff_paths(worktree_path, feature_base)
    junk_verdict, junk_paths = sweep_committed_junk(worktree_path, committed)

    live_verdict, live_detail = drive_registered_gates(
        worktree_path, service_ready=service_ready, runner=gate_runner
    )

    return assemble_report(
        charged_failures=charged,
        junk_verdict=junk_verdict,
        junk_paths=junk_paths,
        live_verdict=live_verdict,
        live_detail=live_detail,
        feature_base=feature_base,
        observed_available=observed_available,
    )


__all__ = [
    "SIGNAL_CLEAN",
    "SIGNAL_CATCH",
    "JUNK_HELD",
    "JUNK_TRIPPED",
    "LIVE_PASS",
    "LIVE_PRODUCT_FAIL",
    "LIVE_ENVIRONMENT_FAIL",
    "LIVE_SKIPPED",
    "FOSSIL_PREFIXES",
    "KEEP_PREFIXES",
    "MachineVerifyReport",
    "charged_failures_at_merge",
    "sweep_committed_junk",
    "committed_diff_paths",
    "drive_registered_gates",
    "assemble_report",
    "run_machine_verify",
]
