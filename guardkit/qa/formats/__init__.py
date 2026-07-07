"""Tier-1 QA format schemas (F1–F5) — session B1, 2026-07-07.

Design source (binding): ai-transition/docs/ws2-qa-verifier-and-last-mile-
scope-design-2026-07-07.md §2. Field lists are pinned there; additions require
a dated note in that doc, never silent invention.

Kinds and their canonical instance paths (INSTANCES live in the app repo —
DF-007: gates travel with the agent):

    F1  pass-bar          qa/pass-bar-<TASK-ID>.yaml
    F2  known-failures    qa/known-failures.yaml
    F3  leak-sweep        qa/leak-sweep.yaml
    F4  gate-registry     qa/gates/registry.yaml
    F4  results-envelope  qa/gates/history/<run>.json   (runner-emitted, B3)
    F5  evidence-index    <evidence-dir>/EVIDENCE.yaml
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Type

from guardkit.qa.formats.base import (
    QAFormatError,
    QAFormatModel,
    export_json_schema,
    load_yaml_or_json,
    validate_file,
)
from guardkit.qa.formats.evidence_index import EvidenceEntry, EvidenceIndex
from guardkit.qa.formats.gate_registry import (
    AssertionResult,
    GateEntry,
    GateRegistry,
    GateResult,
    ResultsEnvelope,
)
from guardkit.qa.formats.known_failures import KnownFailureEntry, KnownFailureLedger
from guardkit.qa.formats.leak_sweep import LeakSweepManifest, Surface
from guardkit.qa.formats.pass_bar import (
    REQUIRED_NEGATIVE_PATHS,
    PassBar,
    PassBarCriterion,
)

#: Canonical kind → model. The CLI accepts these names and the f1..f5 aliases.
FORMAT_KINDS: Dict[str, Type[QAFormatModel]] = {
    "pass-bar": PassBar,
    "known-failures": KnownFailureLedger,
    "leak-sweep": LeakSweepManifest,
    "gate-registry": GateRegistry,
    "results-envelope": ResultsEnvelope,
    "evidence-index": EvidenceIndex,
}

#: F-number aliases (scope-design §2 numbering). F4 covers both the registry
#: and the envelope; the bare alias resolves to the registry (the committed
#: instance), the envelope keeps its full name.
KIND_ALIASES: Dict[str, str] = {
    "f1": "pass-bar",
    "f2": "known-failures",
    "f3": "leak-sweep",
    "f4": "gate-registry",
    "f5": "evidence-index",
}


def resolve_kind(kind: str) -> Type[QAFormatModel]:
    """Resolve a CLI kind string (canonical or alias) to its model.

    Raises:
        QAFormatError: unknown kind, with the full known-kind list in the
        message (loud, actionable).
    """
    canonical = KIND_ALIASES.get(kind.lower(), kind.lower())
    model = FORMAT_KINDS.get(canonical)
    if model is None:
        known = sorted(set(FORMAT_KINDS) | set(KIND_ALIASES))
        raise QAFormatError(
            f"unknown QA format kind {kind!r}. Known kinds: {', '.join(known)}"
        )
    return model


def validate_instance(kind: str, path: Path) -> QAFormatModel:
    """Validate the instance at ``path`` as ``kind``. Raises QAFormatError."""
    return validate_file(resolve_kind(kind), path)


__all__ = [
    "FORMAT_KINDS",
    "KIND_ALIASES",
    "QAFormatError",
    "QAFormatModel",
    "REQUIRED_NEGATIVE_PATHS",
    "AssertionResult",
    "EvidenceEntry",
    "EvidenceIndex",
    "GateEntry",
    "GateRegistry",
    "GateResult",
    "KnownFailureEntry",
    "KnownFailureLedger",
    "LeakSweepManifest",
    "PassBar",
    "PassBarCriterion",
    "ResultsEnvelope",
    "Surface",
    "export_json_schema",
    "load_yaml_or_json",
    "resolve_kind",
    "validate_file",
    "validate_instance",
]
