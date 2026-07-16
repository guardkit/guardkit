"""checker.py — the vendored WASM checker wrapper (D2 §2).

Runs the real vendored bin against a valid capability + the fleet-evals broken
fixture (byte-copied into tests/fixtures/dcl). The false-green guard: the broken
file MUST fail the compile gate — a checker that greens everything is worthless.
"""

from __future__ import annotations

import hashlib

from guardkit.qa.dcl import checker
from guardkit.qa.dcl.checker import CheckerError

from .conftest import requires_node


def test_vendored_bin_is_byte_identical_to_fleet_evals() -> None:
    """The vendored blobs match the fleet-evals source (SHA256SUMS integrity)."""
    from pathlib import Path

    fleet = Path(
        "/home/richardwoollcott/Projects/appmilla_github/fleet-evals/"
        "spike/dcl-authoring/bin"
    )
    if not fleet.is_dir():  # coordinator re-verifies; skip if the sibling is absent
        return
    for name in ("dcl.wasm", "wasm_exec.js", "LICENSE", "NOTICE"):
        ours = (checker.BIN_DIR / name).read_bytes()
        theirs = (fleet / name).read_bytes()
        assert hashlib.sha256(ours).hexdigest() == hashlib.sha256(theirs).hexdigest(), name


@requires_node
def test_valid_capability_compiles_clean(capability_dcl) -> None:
    envelope = checker.check(capability_dcl)
    assert envelope["ok"] is True
    assert envelope["errorCount"] == 0


@requires_node
def test_broken_fixture_fails_compile_gate(broken_dcl) -> None:
    """False-green guard: the deliberately-broken fixture must NOT compile clean."""
    envelope = checker.check(broken_dcl)
    assert envelope["ok"] is False
    assert envelope["errorCount"] > 0


@requires_node
def test_ir_returns_the_compiler_ir(capability_dcl) -> None:
    ir_obj = checker.ir(capability_dcl)
    assert ir_obj["capabilities"][0]["name"] == "ReportServiceStatistics"
    # The IR carries typed event fields with `required` — what R3 consumes.
    fields = ir_obj["events"][0]["payload"]["fields"]
    names = {f["name"] for f in fields}
    assert {"service", "requestsServed", "firstRequestAt"} <= names


@requires_node
def test_ir_refuses_a_broken_compile(broken_dcl) -> None:
    """ir() must fail LOUD on a non-compiling source, never return a half IR."""
    try:
        checker.ir(broken_dcl)
    except CheckerError as exc:
        assert "did not compile clean" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("ir() returned for a broken compile")
