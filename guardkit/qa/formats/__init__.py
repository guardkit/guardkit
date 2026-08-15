"""QA format schemas — tier-1 (B1, F1–F5), tier-2/3 (B10, F6–F15) + deploy-profile.

Design source (binding): ai-transition/docs/ws2-qa-verifier-and-last-mile-
scope-design-2026-07-07.md §2 (F1–F15) + §4 (deploy-profile). Field lists are
pinned there; additions require a dated note in that doc, never silent
invention (the B1 rule).

Kinds and their canonical instance paths (INSTANCES live in the app repo —
DF-007: gates travel with the agent):

    Tier 1 (B1 — enforced from v1):
    F1  pass-bar          qa/pass-bar-<TASK-ID>.yaml
    F2  known-failures    qa/known-failures.yaml
    F3  leak-sweep        qa/leak-sweep.yaml
    F4  gate-registry     qa/gates/registry.yaml
    F4  results-envelope  qa/gates/history/<run>.json   (runner-emitted, B3)
    F5  evidence-index    <evidence-dir>/EVIDENCE.yaml

    Tier 2 (B10 — enforced as deploy + live stages land):
    F6  seam-manifest     contracts/manifest.yaml
    F7  deploy-record     docs/state/<task>/deploy-record-<date>.md (structured)
    F8  disposition-record qa/dispositions-<run>.yaml   (runner-written, B4)
    F9  attempts-ledger   qa/attempts-<campaign>.yaml   (campaign-written, B4)
    F10 live-matrix       qa/live-matrix-<feature>.yaml
        deploy-profile    deploy/profile.yaml           (forge is the consumer)

    Tier 3 (B10 — schema published now, enforcement follows):
    F11 runbook           docs/runbooks/RUNBOOK-<topic>.md  (MARKDOWN convention)
    F12 discovery-gates   qa/discovery-gates-<feature>.yaml
    F13 kickoff-prompt    qa/kickoff-<session>.yaml
    F14 review-findings   qa/review-<id>.yaml
    F15 walk-checkpoints  qa/walk-<feature>.yaml

F8/F9 were defined minimally by B4 ahead of B10; B10 RATIFIED them as-is (no
fields moved — see the dated notes in disposition_record.py / attempts_ledger.py
and the WS2 build-plan §B10 STATUS). F16 stays a consumer interface only (the
register schema is WS5's) — no format model here. F11 is validated as a set of
markdown conventions (the binding "markdown first" guardrail), all others as
pydantic YAML models.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Type, Union

from guardkit.qa.formats.attempts_ledger import (
    Attempt,
    AttemptsLedger,
    DeploymentState,
    HarnessSetting,
    Probe,
)
from guardkit.qa.formats.base import (
    MarkdownFormat,
    MarkdownValidation,
    QAFormatError,
    QAFormatModel,
    check_format_version_window,
    export_json_schema,
    load_yaml_or_json,
    validate_file,
    validate_markdown_file,
)
from guardkit.qa.formats.deploy_profile import (
    ComposeSpec,
    DeployHost,
    DeployProfile,
    HealthCheck,
    ModelRequirement,
    Reservation,
    SeedFixture,
)
from guardkit.qa.formats.deploy_record import (
    DeployAddendum,
    DeployClaim,
    DeployHeader,
    DeployRecord,
)
from guardkit.qa.formats.discovery_gate import (
    DiscoveryGates,
    DiscoveryGateSpec,
    ExternalClaim,
)
from guardkit.qa.formats.disposition_record import (
    Attribution,
    AttributionRevision,
    Disposition,
    DispositionRecord,
    FailureDisposition,
)
from guardkit.qa.formats.evidence_index import EvidenceEntry, EvidenceIndex
from guardkit.qa.formats.gate_registry import (
    AssertionResult,
    GateEntry,
    GateRegistry,
    GateResult,
    ResultsEnvelope,
)
from guardkit.qa.formats.kickoff_prompt import KickoffDeliverable, KickoffPrompt
from guardkit.qa.formats.known_failures import KnownFailureEntry, KnownFailureLedger
from guardkit.qa.formats.leak_sweep import LeakSweepManifest, Surface
from guardkit.qa.formats.live_matrix import Hop, LiveMatrix, Scenario, ValidationDebt
from guardkit.qa.formats.pass_bar import (
    AUTH_NEGATIVE_PATHS,
    REQUIRED_NEGATIVE_PATHS,
    UNIVERSAL_NEGATIVE_PATHS,
    PassBar,
    PassBarCriterion,
)
from guardkit.qa.formats.review_findings import (
    Finding,
    ReviewFindings,
    ReviewStats,
    ReviewSubject,
)
from guardkit.qa.formats.runbook import Runbook
from guardkit.qa.formats.seam_manifest import (
    ArbiterDoc,
    BrokerStream,
    Seam,
    SeamManifest,
)
from guardkit.qa.formats.walk_checkpoints import (
    WalkArtifact,
    WalkCheckpoint,
    WalkCheckpoints,
)

#: A format handler is either a pydantic YAML model or a markdown-convention class.
FormatHandler = Union[Type[QAFormatModel], Type[MarkdownFormat]]

#: Canonical pydantic (YAML) kinds → model.
FORMAT_KINDS: Dict[str, Type[QAFormatModel]] = {
    # Tier 1 (B1)
    "pass-bar": PassBar,
    "known-failures": KnownFailureLedger,
    "leak-sweep": LeakSweepManifest,
    "gate-registry": GateRegistry,
    "results-envelope": ResultsEnvelope,
    "evidence-index": EvidenceIndex,
    # Tier 2 (B10) + B4's F8/F9
    "seam-manifest": SeamManifest,
    "deploy-record": DeployRecord,
    "disposition-record": DispositionRecord,
    "attempts-ledger": AttemptsLedger,
    "live-matrix": LiveMatrix,
    "deploy-profile": DeployProfile,
    # Tier 3 (B10)
    "discovery-gates": DiscoveryGates,
    "kickoff-prompt": KickoffPrompt,
    "review-findings": ReviewFindings,
    "walk-checkpoints": WalkCheckpoints,
}

#: Markdown-convention kinds → format class (validated as conventions, not YAML).
MARKDOWN_KINDS: Dict[str, Type[MarkdownFormat]] = {
    "runbook": Runbook,
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
    "f6": "seam-manifest",
    "f7": "deploy-record",
    "f8": "disposition-record",
    "f9": "attempts-ledger",
    "f10": "live-matrix",
    "f11": "runbook",
    "f12": "discovery-gates",
    "f13": "kickoff-prompt",
    "f14": "review-findings",
    "f15": "walk-checkpoints",
    # f16 is reserved as the WS5-owned register consumer interface (no model
    # here — see the module docstring).
}


def _all_handlers() -> Dict[str, FormatHandler]:
    """Every resolvable canonical kind → its handler (pydantic or markdown)."""
    handlers: Dict[str, FormatHandler] = dict(FORMAT_KINDS)
    handlers.update(MARKDOWN_KINDS)
    return handlers


def resolve_kind(kind: str) -> FormatHandler:
    """Resolve a CLI kind string (canonical or alias) to its handler.

    Returns a :class:`QAFormatModel` subclass (YAML) or a
    :class:`MarkdownFormat` subclass (markdown-convention).

    Raises:
        QAFormatError: unknown kind, with the full known-kind list in the
        message (loud, actionable).
    """
    canonical = KIND_ALIASES.get(kind.lower(), kind.lower())
    handler = _all_handlers().get(canonical)
    if handler is None:
        known = sorted(set(FORMAT_KINDS) | set(MARKDOWN_KINDS) | set(KIND_ALIASES))
        raise QAFormatError(
            f"unknown QA format kind {kind!r}. Known kinds: {', '.join(known)}"
        )
    return handler


def is_markdown_kind(kind: str) -> bool:
    """True if ``kind`` (canonical or alias) is a markdown-convention format."""
    handler = resolve_kind(kind)
    return isinstance(handler, type) and issubclass(handler, MarkdownFormat)


def validate_instance(
    kind: str, path: Path
) -> Union[QAFormatModel, MarkdownValidation]:
    """Validate the instance at ``path`` as ``kind``. Raises QAFormatError.

    Dispatches to the YAML validator or the markdown-convention validator
    depending on the resolved handler.
    """
    handler = resolve_kind(kind)
    if isinstance(handler, type) and issubclass(handler, MarkdownFormat):
        return validate_markdown_file(handler, path)
    return validate_file(handler, path)


__all__ = [
    "FORMAT_KINDS",
    "MARKDOWN_KINDS",
    "KIND_ALIASES",
    "FormatHandler",
    "QAFormatError",
    "QAFormatModel",
    "MarkdownFormat",
    "MarkdownValidation",
    "AUTH_NEGATIVE_PATHS",
    "REQUIRED_NEGATIVE_PATHS",
    "UNIVERSAL_NEGATIVE_PATHS",
    # Tier 1
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
    # F8/F9 (B4)
    "Attempt",
    "AttemptsLedger",
    "Attribution",
    "AttributionRevision",
    "DeploymentState",
    "Disposition",
    "DispositionRecord",
    "FailureDisposition",
    "HarnessSetting",
    "Probe",
    # Tier 2 (B10)
    "ArbiterDoc",
    "BrokerStream",
    "Seam",
    "SeamManifest",
    "DeployAddendum",
    "DeployClaim",
    "DeployHeader",
    "DeployRecord",
    "Hop",
    "LiveMatrix",
    "Scenario",
    "ValidationDebt",
    "ComposeSpec",
    "DeployHost",
    "DeployProfile",
    "HealthCheck",
    "ModelRequirement",
    "Reservation",
    "SeedFixture",
    # Tier 3 (B10)
    "Runbook",
    "DiscoveryGates",
    "DiscoveryGateSpec",
    "ExternalClaim",
    "KickoffDeliverable",
    "KickoffPrompt",
    "Finding",
    "ReviewFindings",
    "ReviewStats",
    "ReviewSubject",
    "WalkArtifact",
    "WalkCheckpoint",
    "WalkCheckpoints",
    # helpers
    "check_format_version_window",
    "export_json_schema",
    "is_markdown_kind",
    "load_yaml_or_json",
    "resolve_kind",
    "validate_file",
    "validate_markdown_file",
    "validate_instance",
]
