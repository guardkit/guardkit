"""ST-06 boundary probes — feed non-conforming inputs at a seam, watch the error posture.

The worked example (study-tutor retro L5): a proxy-style nested ``error`` object
threw a raw ``TypeError`` past the sealed exception hierarchy; out-of-enum wire
values threw raw ``ArgumentError``. Both are crashes a conforming-fixtures-only
suite can never see. The rule: **the error posture must degrade, never leak raw
errors** — a garbage envelope should raise the seam's own sealed error (or be
rejected gracefully), never an un-typed ``TypeError`` / ``KeyError`` escape.

This stage consumes the **F6 seam manifest** (B10's real format,
:class:`~guardkit.qa.formats.seam_manifest.SeamManifest`): ``--seam <id>``
selects the seam whose decode/handler is probed. The decode target is a
configured :class:`ProbeTarget`; an :class:`UnconfiguredProbeTarget` **raises
loudly** the moment it is invoked (FEAT-DD4F — no silent no-op), so an
un-wired seam is an honest "not configured", never a vacuous green.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, List, Protocol, Sequence, Tuple, Type, runtime_checkable

from guardkit.orchestrator.qa_stages.errors import QAStageStubError


@runtime_checkable
class ProbeTarget(Protocol):
    """The seam decode/handler under probe, plus its declared sealed error set.

    ``sealed_errors`` is the seam's own contract exception hierarchy (the "closed
    set" the retro names). An exception raised OUTSIDE this set on a garbage
    input is a raw-error leak — a finding. ``decode`` is the boundary function
    (envelope parse, wire-value coerce, request handler entry).
    """

    sealed_errors: Tuple[Type[BaseException], ...]

    def decode(self, raw: Any) -> Any: ...


class UnconfiguredProbeTarget:
    """Default probe target for a seam with no wired decoder — raises loudly."""

    sealed_errors: Tuple[Type[BaseException], ...] = ()

    def decode(self, raw: Any) -> Any:
        raise QAStageStubError(
            "boundary probe target is not configured for this seam. Wire a "
            "ProbeTarget (its `decode` + `sealed_errors`) before probing — an "
            "un-wired seam must not silently report a clean posture."
        )


@dataclass(frozen=True)
class ProbeInput:
    """One adversarial input plus a human label and whether it is 'garbage'.

    ``is_garbage`` marks inputs that a well-behaved seam should REJECT (so a
    seam that *accepts* one is itself a finding); non-garbage inputs (e.g. a
    valid-shape but out-of-enum value) may legitimately be accepted or rejected —
    only a raw-error leak on them is a finding.
    """

    label: str
    value: Any
    is_garbage: bool = True


def default_input_battery(*, enum_field: str | None = None) -> List[ProbeInput]:
    """The generic non-conforming-input battery (garbage / wrong-type / out-of-enum).

    Reproduces the retro's two escape triggers: a proxy-style nested ``error``
    object (the raw-``TypeError`` trigger) and an out-of-enum discriminator
    value (the raw-``ArgumentError`` trigger). ``enum_field`` names the seam's
    discriminator key when known, so the out-of-enum probe targets it.
    """
    field_key = enum_field or "type"
    battery: List[ProbeInput] = [
        ProbeInput("empty-bytes", b""),
        ProbeInput("not-json", b"this is not json at all"),
        ProbeInput("truncated-json", b'{"a":'),
        ProbeInput("top-level-null", "null"),
        ProbeInput("top-level-list", [1, 2, 3]),
        ProbeInput("empty-object", {}),
        ProbeInput("wrong-type-field", {field_key: 12345}),
        ProbeInput(
            "out-of-enum", {field_key: "__nonexistent_enum_value__"}, is_garbage=True
        ),
        # Proxy-style nested error object — the retro's raw-TypeError trigger.
        ProbeInput("proxy-nested-error", {field_key: "a", "error": "boom-as-string"}),
        ProbeInput("deeply-nested-garbage", {field_key: "a", "error": {"detail": {"x": [None]}}}),
    ]
    return battery


#: How a single probe input was handled.
#: - "handled":  raised a sealed error, or returned/handled gracefully (good)
#: - "leak":     raised an exception OUTSIDE the sealed set (raw-error leak = finding)
#: - "accepted": returned a value for a GARBAGE input (silently accepted junk = finding)
Classification = str


@dataclass
class ProbeOutcome:
    """One probe input's outcome at a seam."""

    input_label: str
    classification: Classification
    exception_type: str | None = None
    is_finding: bool = False
    detail: str = ""


@dataclass
class BoundaryProbeResult:
    """The full probe sweep of one seam. Findings are the raw-escape / junk-accept cases."""

    seam_id: str
    outcomes: List[ProbeOutcome] = field(default_factory=list)

    @property
    def findings(self) -> List[ProbeOutcome]:
        return [o for o in self.outcomes if o.is_finding]

    @property
    def leaks(self) -> List[ProbeOutcome]:
        return [o for o in self.outcomes if o.classification == "leak"]


def _coerce(value: Any) -> Any:
    """Present bytes/str envelopes as the decoder would receive them.

    Non-bytes/str inputs (a list, a dict, ``None``) are passed through as-is so
    the probe can also hit decoders that accept already-parsed payloads.
    """
    return value


def run_boundary_probes(
    seam_id: str,
    target: ProbeTarget,
    inputs: Sequence[ProbeInput] | None = None,
) -> BoundaryProbeResult:
    """Probe ``target`` with the non-conforming battery; classify each outcome.

    A raw-error leak (an exception outside ``target.sealed_errors``) is a
    finding; a garbage input that ``decode`` *accepts* (returns a value for) is
    also a finding. Sealed-error rejections and graceful handling are clean.
    """
    battery = list(inputs) if inputs is not None else default_input_battery()
    sealed = tuple(getattr(target, "sealed_errors", ()) or ())
    result = BoundaryProbeResult(seam_id=seam_id)

    for probe in battery:
        try:
            returned = target.decode(_coerce(probe.value))
        except QAStageStubError:
            # An unconfigured target must surface loudly, not be swallowed here.
            raise
        except BaseException as exc:  # noqa: BLE001 — probing error posture is the point
            if sealed and isinstance(exc, sealed):
                result.outcomes.append(
                    ProbeOutcome(probe.label, "handled", type(exc).__name__)
                )
            else:
                result.outcomes.append(
                    ProbeOutcome(
                        probe.label,
                        "leak",
                        type(exc).__name__,
                        is_finding=True,
                        detail=f"raw {type(exc).__name__} escaped the sealed error set: {exc}",
                    )
                )
            continue
        # No exception — decode returned a value.
        if probe.is_garbage:
            result.outcomes.append(
                ProbeOutcome(
                    probe.label,
                    "accepted",
                    None,
                    is_finding=True,
                    detail=f"garbage input silently accepted (returned {returned!r})",
                )
            )
        else:
            result.outcomes.append(ProbeOutcome(probe.label, "handled", None))
    return result


def load_seam_ids(manifest_path: Any) -> List[str]:
    """Return the seam ids declared in an F6 seam-manifest file (read-only)."""
    from pathlib import Path
    from typing import cast

    from guardkit.qa.formats import validate_instance
    from guardkit.qa.formats.seam_manifest import SeamManifest

    manifest = cast(SeamManifest, validate_instance("seam-manifest", Path(manifest_path)))
    return [s.id for s in manifest.seams]


def envelope_from_bytes_or_obj(raw: Any) -> Any:
    """Helper for ProbeTarget authors: JSON-decode bytes/str, pass objects through.

    A decoder built on this gets the retro's exact surface — a non-object
    top-level payload becomes a Python ``None``/``list``, and truncated JSON
    raises ``json.JSONDecodeError`` (which the author should fold into their
    sealed set, or the probe reports it as a leak).
    """
    if isinstance(raw, (bytes, bytearray, str)):
        return json.loads(raw)
    return raw
