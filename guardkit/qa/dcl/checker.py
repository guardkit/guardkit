"""Subprocess wrapper around the vendored DCL WASM checker (D2, design §2).

The checker is the vendored, offline, LLM-free semantic analyzer at
``bin/dcl_check.mjs`` (+ ``dcl.wasm`` / ``wasm_exec.js``), driven through node.
This module is the Python door to it, following the fleet-evals ``_run_checker``
idiom (``spike/dcl-authoring/test/test_gate_dcl_authoring.py``):

- :func:`check` runs the compile gate and returns the JSON envelope
  (``{ok, diagnostics, errorCount, warningCount, ...}``).
- :func:`ir` runs the harness with ``--ir`` and returns the compiler's native
  IR object — the structure R1–R10 (:mod:`guardkit.qa.dcl.deriver`) consume.

node presence is checked up front and refused LOUDLY if absent — a missing
runtime must never masquerade as a clean compile (honest-gates law).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict

#: The vendored checker lives beside this module.
BIN_DIR: Path = Path(__file__).resolve().parent / "bin"
HARNESS: Path = BIN_DIR / "dcl_check.mjs"

#: Upstream pin of the vendored compiler (see bin/PROVENANCE.md).
CHECKER_PIN: str = "russelleast/Capability-Language@4f9fbe56"

#: Subprocess timeout — the WASM compile is sub-second; the ceiling is generous.
_CHECK_TIMEOUT_S: int = 120


class CheckerError(RuntimeError):
    """The DCL checker could not be run (missing node, missing blob, bad output).

    Distinct from a *compile failure* (that is a well-formed envelope with
    ``ok: false``) — this is an instrument fault and must surface loudly, never
    be read as a passing compile.
    """


def _require_node() -> str:
    node = shutil.which("node")
    if node is None:
        raise CheckerError(
            "node is required to run the vendored DCL WASM checker "
            f"({HARNESS}). Install Node.js and retry — a missing runtime is an "
            "instrument fault, never a clean compile."
        )
    if not HARNESS.is_file():
        raise CheckerError(f"vendored checker harness not found at {HARNESS}")
    if not (BIN_DIR / "dcl.wasm").is_file():
        raise CheckerError(f"vendored WASM blob not found at {BIN_DIR / 'dcl.wasm'}")
    return node


def _run(dcl_path: Path, *, include_ir: bool) -> Dict[str, Any]:
    node = _require_node()
    target = Path(dcl_path)
    if not target.is_file():
        raise CheckerError(f"DCL source not found: {target}")
    cmd = [node, str(HARNESS)]
    if include_ir:
        cmd.append("--ir")
    cmd.append(str(target))
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=_CHECK_TIMEOUT_S,
    )
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise CheckerError(
            f"checker did not emit JSON (exit {proc.returncode}) for {target}:\n"
            f"STDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
        ) from exc


def check(dcl_path: Path) -> Dict[str, Any]:
    """Compile ``dcl_path`` and return the checker envelope.

    The envelope mirrors ``dcl validate --json``:
    ``{ok, diagnostics[], diagnosticCount, errorCount, warningCount, infoCount,
    sourceCount}``. ``ok is True`` with ``errorCount == 0`` is the compile gate.

    Raises:
        CheckerError: node/blob missing or the harness produced no JSON.
    """
    return _run(Path(dcl_path), include_ir=False)


def ir(dcl_path: Path) -> Dict[str, Any]:
    """Compile ``dcl_path`` with ``--ir`` and return the compiler IR object.

    Raises:
        CheckerError: node/blob missing, the harness produced no JSON, the
        compile failed (``ok: false``), or no IR was returned — the deriver
        cannot run over a broken or IR-less compile, and that must be loud.
    """
    envelope = _run(Path(dcl_path), include_ir=True)
    if not envelope.get("ok"):
        errors = [
            d for d in envelope.get("diagnostics", []) if d.get("severity") == "error"
        ]
        raise CheckerError(
            f"cannot derive from {dcl_path}: DCL did not compile clean "
            f"(errorCount={envelope.get('errorCount')}). Errors: {errors}"
        )
    ir_obj = envelope.get("ir")
    if not isinstance(ir_obj, dict):
        raise CheckerError(
            f"checker returned no IR for {dcl_path} (got {type(ir_obj).__name__}); "
            "the --ir harness flag is required for derivation."
        )
    return ir_obj
