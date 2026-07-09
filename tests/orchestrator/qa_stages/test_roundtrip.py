"""ST-13 round-trip library tests — helpers, NOT a gate."""

from __future__ import annotations

import json

from guardkit.orchestrator.qa_stages import (
    render_parse,
    synthesize_transcribe,
    write_reload,
)
from guardkit.orchestrator.qa_stages.roundtrip import TECHNIQUES


def test_render_parse_matches():
    value = {"a": 1, "b": [2, 3]}
    r = render_parse(value, json.dumps, json.loads)
    assert r.matched is True
    assert r.roundtripped == value
    assert r.technique == "render->parse"


def test_render_parse_detects_lossy_transform():
    # A lossy render (drops a key) is caught programmatically.
    r = render_parse({"a": 1, "b": 2}, lambda v: json.dumps({"a": v["a"]}), json.loads)
    assert r.matched is False


def test_synthesize_transcribe_with_normalize():
    r = synthesize_transcribe(
        "Hello World",
        synthesize=lambda s: s.encode("utf-8"),
        transcribe=lambda b: b.decode("utf-8").upper(),
        normalize=str.upper,
    )
    assert r.matched is True
    assert r.technique == "synthesize->transcribe"


def test_write_reload():
    store: dict[str, str] = {}

    def write(v):
        store["k"] = json.dumps(v)
        return "k"

    def reload(k):
        return json.loads(store[k])

    r = write_reload({"x": 1}, write, reload)
    assert r.matched is True


def test_techniques_catalogue_advertised():
    assert set(TECHNIQUES) == {"render->parse", "synthesize->transcribe", "write->reload"}


def test_roundtrip_is_not_a_gate():
    """ST-13 ships as a library — it must not import or wire any quality gate."""
    import guardkit.orchestrator.qa_stages.roundtrip as rt

    src = rt.__file__
    text = open(src, encoding="utf-8").read()
    # No coupling to the Coach / gate machinery (advisory-library discipline).
    assert "coach_validator" not in text
    assert "quality_gates" not in text
