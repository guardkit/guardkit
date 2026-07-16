"""DCL derivation tool (D2, design §2) — additive; the gherkin track never sees it.

The optional ``dcl`` spec track's derivation surface: a vendored, offline WASM
compiler (``bin/``) wrapped by :mod:`checker`, R1–R10 as code in :mod:`deriver`
over the compiler IR + the per-repo :mod:`binding` table, and one generic F4
executor in :mod:`assertion_runner`.
"""

from __future__ import annotations

from guardkit.qa.dcl.checker import CHECKER_PIN, CheckerError, check, ir
from guardkit.qa.dcl.deriver import (
    Assertion,
    AssertionSet,
    DerivationError,
    DerivationResult,
    derive,
    make_receipt,
)

__all__ = [
    "CHECKER_PIN",
    "CheckerError",
    "check",
    "ir",
    "Assertion",
    "AssertionSet",
    "DerivationError",
    "DerivationResult",
    "derive",
    "make_receipt",
]
