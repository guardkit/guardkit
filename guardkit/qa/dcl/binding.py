"""Loader for the per-repo dcl-binding table (D2, design §2).

Thin door onto the :class:`~guardkit.qa.formats.dcl_binding.DclBinding`
F-format model: reads ``qa/dcl/binding.yaml`` (the J1–J3 + opt-in table the
deriver consumes) and validates it loudly. The schema lives in
``guardkit/qa/formats/dcl_binding.py``; this module is the convenience the
deriver and the CLI import.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from guardkit.qa.formats.base import validate_file
from guardkit.qa.formats.dcl_binding import DclBinding

#: Canonical repo-relative location of the binding table.
BINDING_RELPATH = Path("qa/dcl/binding.yaml")


def load_binding(path: Path) -> DclBinding:
    """Load + validate a dcl-binding instance, raising ``QAFormatError`` loud."""
    return validate_file(DclBinding, Path(path))


def binding_path(repo_root: Path) -> Path:
    """The canonical binding path under ``repo_root``."""
    return Path(repo_root) / BINDING_RELPATH


def sha256_of(path: Path) -> str:
    """SHA-256 of a file's bytes (recorded in the derivation receipt)."""
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
