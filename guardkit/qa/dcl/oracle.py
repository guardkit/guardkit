"""The hermetic task-level DCL oracle (Phase D, design §1 / D1).

The ``dcl`` track's analogue of ``run_bdd_for_task``: activated by artefact
presence (a ``features/**/*.dcl`` carrying a ``@task:<TASK-ID>`` marker), it runs
the *hermetic* half of DCL verification and returns a three-field result the
Coach gates on:

    compile gate  — the vendored WASM checker returns ``ok: true`` with
                    ``errorCount == 0`` (:mod:`guardkit.qa.dcl.checker`); and
    derivation    — R1–R10 over the compiler IR + the per-repo binding table
                    produce an assertion set + a recorded receipt
                    (:mod:`guardkit.qa.dcl.deriver`).

It does NOT execute the derived assertions against a live URL — that is the
live-gate stage's job (design §3). Absence discipline (design §0.1): no tagged
``.dcl`` → :func:`run_dcl_for_task` returns ``None`` (not-applicable) and the
existing chain proceeds untouched — never a synthesized failure.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from guardkit.qa.dcl.binding import binding_path, load_binding, sha256_of
from guardkit.qa.dcl.checker import CHECKER_PIN, check, ir
from guardkit.qa.dcl.deriver import DerivationError, derive, make_receipt
from guardkit.qa.dcl.discovery import find_dcl_files_with_tag, task_tag

logger = logging.getLogger(__name__)

__all__ = ["DclOracleResult", "run_dcl_for_task"]

#: Result status values.
STATUS_PASS = "pass"
STATUS_COMPILE_ERROR = "compile_error"
STATUS_DERIVATION_ERROR = "derivation_error"


@dataclass
class DclOracleResult:
    """The hermetic DCL oracle's three-state outcome for one task."""

    task_id: str
    dcl_file: str  # repo-relative path of the tagged .dcl
    feature: str
    status: str  # pass | compile_error | derivation_error
    compile_ok: bool
    error_count: int
    warning_count: int
    errors: List[str] = field(default_factory=list)  # compile diagnostics (loud)
    derivation_error: Optional[str] = None  # message on derivation_error
    run_ids: List[str] = field(default_factory=list)
    skip_ids: List[str] = field(default_factory=list)
    rules_fired: Dict[str, int] = field(default_factory=dict)
    receipt_path: Optional[str] = None  # repo-relative
    assertion_set_path: Optional[str] = None  # repo-relative

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "task_id": self.task_id,
            "dcl_file": self.dcl_file,
            "feature": self.feature,
            "status": self.status,
            "compile_ok": self.compile_ok,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
        }
        if self.errors:
            out["errors"] = list(self.errors)
        if self.derivation_error is not None:
            out["derivation_error"] = self.derivation_error
        if self.status == STATUS_PASS:
            out["run_ids"] = list(self.run_ids)
            out["skip_ids"] = list(self.skip_ids)
            out["rules_fired"] = dict(self.rules_fired)
            out["receipt_path"] = self.receipt_path
            out["assertion_set_path"] = self.assertion_set_path
        return out


def _relpath(path: Path, repo_root: Path) -> str:
    try:
        return str(Path(path).relative_to(repo_root))
    except ValueError:
        return str(path)


def _error_messages(envelope: Dict[str, Any]) -> List[str]:
    """Human-readable compile-error lines from a checker envelope (loud gate)."""
    messages: List[str] = []
    for diag in envelope.get("diagnostics", []) or []:
        if diag.get("severity") != "error":
            continue
        loc = ""
        if diag.get("line") is not None:
            loc = f" (line {diag.get('line')})"
        messages.append(f"{diag.get('message', '<no message>')}{loc}")
    return messages


def run_dcl_for_task(
    task_id: str,
    repo_root: Path,
    *,
    capability: Optional[str] = None,
) -> Optional[DclOracleResult]:
    """Run the hermetic DCL oracle for ``task_id`` under ``repo_root``.

    Returns ``None`` when no ``features/**/*.dcl`` carries a ``@task:<TASK-ID>``
    marker (absence discipline — not-applicable, never a synthesized failure).

    When a tagged ``.dcl`` exists it is compiled and, on a clean compile, derived:

    * compile ``ok: false`` / ``errorCount > 0`` → ``status = "compile_error"``
      (the Coach blocks — a broken spec is a task failure, never green);
    * derivation raises → ``status = "derivation_error"`` (the Coach blocks);
    * clean compile + successful derivation (set + receipt written) →
      ``status = "pass"``.

    Raises:
        CheckerError: an *instrument* fault (node/WASM missing, non-JSON output,
        an IR-less compile). The caller (``AgentInvoker._run_dcl_oracle``)
        swallows it and returns ``None`` — a missing runtime is a skip, never a
        clean compile (honest-gates law); the live gate surfaces it loudly.
    """
    repo = Path(repo_root)
    features_dir = repo / "features"
    tag = task_tag(task_id)
    matches = find_dcl_files_with_tag(features_dir, tag)
    if not matches:
        return None

    src = matches[0]
    if len(matches) > 1:
        logger.info(
            "DCL oracle: %d .dcl files carry %s; using %s (first, sorted).",
            len(matches),
            tag,
            src,
        )
    feature = src.stem
    rel_src = _relpath(src, repo)

    # Compile gate (a compile failure is a well-formed envelope, not an
    # exception — only instrument faults raise CheckerError, which propagates).
    envelope = check(src)
    error_count = int(envelope.get("errorCount", 0) or 0)
    warning_count = int(envelope.get("warningCount", 0) or 0)
    compile_ok = bool(envelope.get("ok")) and error_count == 0

    if not compile_ok:
        return DclOracleResult(
            task_id=task_id,
            dcl_file=rel_src,
            feature=feature,
            status=STATUS_COMPILE_ERROR,
            compile_ok=False,
            error_count=error_count,
            warning_count=warning_count,
            errors=_error_messages(envelope) or [f"{error_count} compile error(s)"],
        )

    # Derivation over the compiler IR + the per-repo binding table.
    bpath = binding_path(repo)
    if not bpath.is_file():
        return DclOracleResult(
            task_id=task_id,
            dcl_file=rel_src,
            feature=feature,
            status=STATUS_DERIVATION_ERROR,
            compile_ok=True,
            error_count=error_count,
            warning_count=warning_count,
            derivation_error=(
                f"binding table not found at {_relpath(bpath, repo)} — the dcl "
                "track requires a per-repo J1–J3 binding to derive from."
            ),
        )

    try:
        binding = load_binding(bpath)
        ir_obj = ir(src)
        result = derive(ir_obj, binding, feature=feature, capability=capability)
    except DerivationError as exc:
        return DclOracleResult(
            task_id=task_id,
            dcl_file=rel_src,
            feature=feature,
            status=STATUS_DERIVATION_ERROR,
            compile_ok=True,
            error_count=error_count,
            warning_count=warning_count,
            derivation_error=str(exc),
        )

    # Write the assertion set + the F-format receipt (design §2 paths).
    derived_path = repo / "qa" / "dcl" / "derived" / f"{feature}.yaml"
    result.assertion_set.write_yaml(derived_path)

    receipt = make_receipt(
        result,
        feature=feature,
        source_dcl=str(src),
        source_dcl_sha256=sha256_of(src),
        binding_sha256=sha256_of(bpath),
        checker_ok=bool(envelope.get("ok")),
        error_count=error_count,
        warning_count=warning_count,
        checker_pin=CHECKER_PIN,
    )
    receipt_path = repo / "qa" / "dcl" / f"derivation-{feature}.yaml"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    import yaml

    receipt_path.write_text(
        yaml.safe_dump(receipt.model_dump(mode="json"), sort_keys=False),
        encoding="utf-8",
    )

    return DclOracleResult(
        task_id=task_id,
        dcl_file=rel_src,
        feature=feature,
        status=STATUS_PASS,
        compile_ok=True,
        error_count=error_count,
        warning_count=warning_count,
        run_ids=list(result.run_ids),
        skip_ids=list(result.skip_ids),
        rules_fired=dict(result.rules_fired),
        receipt_path=_relpath(receipt_path, repo),
        assertion_set_path=_relpath(derived_path, repo),
    )
