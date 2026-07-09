"""ST-13 round-trip technique library — judge-free verification helpers.

**This is a technique LIBRARY, not a gate (v1).** Scope-design §3.8 is explicit:
"judge-free round-trips (synthesize→transcribe, render→parse, write→reload) —
technique library, not a gate, in v1." Nothing here is wired into the Coach or
any quality gate; these are documented helpers a task author (or a verifier
writing an execution probe) reaches for where output quality tempts a subjective
check. The idea (study-tutor retro §4): prefer a *second independent transform*
that closes the loop and compare programmatically, rather than a judge.

Each helper takes the two transforms and an optional comparison/normalisation
and returns a :class:`RoundTripResult` — ``matched`` is the whole verdict; the
original and round-tripped values are carried for the caller's own assertion.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

T = TypeVar("T")
U = TypeVar("U")


@dataclass
class RoundTripResult(Generic[T]):
    """Outcome of a closed round-trip loop.

    ``matched`` is the programmatic verdict (no judge). ``original`` and
    ``roundtripped`` are kept so the caller can render a precise diff on failure.
    """

    matched: bool
    original: T
    roundtripped: T
    technique: str
    detail: str = ""


def _default_compare(a: Any, b: Any) -> bool:
    return a == b


def render_parse(
    value: T,
    render: Callable[[T], U],
    parse: Callable[[U], T],
    *,
    compare: Callable[[T, T], bool] = _default_compare,
) -> RoundTripResult[T]:
    """render → parse: ``parse(render(value))`` must equal ``value``.

    The metamorphic check for serializers/formatters: a value rendered to its
    wire/text form and parsed back must be the value again.
    """
    roundtripped = parse(render(value))
    matched = compare(value, roundtripped)
    return RoundTripResult(matched, value, roundtripped, technique="render->parse")


def synthesize_transcribe(
    source: T,
    synthesize: Callable[[T], U],
    transcribe: Callable[[U], T],
    *,
    normalize: Callable[[T], T] = lambda x: x,
    compare: Callable[[T, T], bool] = _default_compare,
) -> RoundTripResult[T]:
    """synthesize → transcribe: ``transcribe(synthesize(source))`` ≈ ``source``.

    The study-tutor worked example: a phrase synthesized to audio then run
    through the live STT should transcribe back to the (normalized) phrase — a
    second independent transform closing the loop, no subjective audio judgement.
    ``normalize`` folds out benign differences (casing, punctuation) before the
    compare.
    """
    roundtripped = transcribe(synthesize(source))
    n_src, n_rt = normalize(source), normalize(roundtripped)
    matched = compare(n_src, n_rt)
    return RoundTripResult(matched, source, roundtripped, technique="synthesize->transcribe")


def write_reload(
    value: T,
    write: Callable[[T], U],
    reload: Callable[[U], T],
    *,
    compare: Callable[[T, T], bool] = _default_compare,
) -> RoundTripResult[T]:
    """write → reload: persist ``value`` then read it back; the two must agree.

    The persistence metamorphic check: a record written to disk/store and
    reloaded must reconstruct the same value (the recorder-config / edit-delta
    restart-survival pattern).
    """
    roundtripped = reload(write(value))
    matched = compare(value, roundtripped)
    return RoundTripResult(matched, value, roundtripped, technique="write->reload")


#: The public technique catalogue — advertised as helpers, not enforced.
TECHNIQUES = {
    "render->parse": render_parse,
    "synthesize->transcribe": synthesize_transcribe,
    "write->reload": write_reload,
}
