"""The two QA seat clients read the key and the address from the shared rule.

``guardkit/qa/qav_shadow.py`` and ``guardkit/qa/review_seat.py`` both build an
OpenAI-compatible client. Both used to send the literal placeholder key, and the
review seat had ``http://localhost:9000/v1`` written into the code. These tests
pin what each one now sends:

* the key is ``OPENAI_API_KEY`` when that variable is set, and the old
  placeholder when it is not (a machine without the variable behaves exactly as
  it did before);
* the address follows the precedence the modules' docstrings name.

No key value is ever logged or printed here — the dummies are obvious
non-secrets, compared and discarded.
"""

import sys
import types

import pytest

import guardkit.qa.qav_shadow as qs
import guardkit.qa.review_seat as rs
from guardkit.lib.client_env import API_KEY_ENV, BASE_URL_ENV
from guardkit.lib.client_env import (
    FEATURE_ROUTING_HEADER,
    FEATURE_ROUTING_ID_ENV,
    FEATURE_ROUTING_REQUIRED_ENV,
    FeatureRoutingError,
    resolve_feature_routing_headers,
)

DUMMY_KEY = "dummy-key-for-tests"
PLACEHOLDER = "not-needed"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Every test starts from a machine with none of these variables set."""
    for name in (
        API_KEY_ENV,
        BASE_URL_ENV,
        qs.QAV_SHADOW_URL_ENV,
        rs.REVIEW_SEAT_URL_ENV,
        FEATURE_ROUTING_ID_ENV,
        FEATURE_ROUTING_REQUIRED_ENV,
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def captured_client(monkeypatch):
    """A fake ``openai.OpenAI`` that records what it was handed and stops there."""
    seen = {}

    class _FakeClient:
        def __init__(self, base_url=None, api_key=None, timeout=None, **kwargs):
            seen["base_url"] = base_url
            seen["api_key"] = api_key
            seen["default_headers"] = kwargs.pop("default_headers", None)
            # the QAV client also passes max_retries=0 (2026-09-05) — recorded
            # here so this fake stays a faithful stand-in for every seat client.
            seen.update(kwargs)
            raise RuntimeError("stop before any network")

    fake_openai = types.ModuleType("openai")
    fake_openai.OpenAI = _FakeClient
    monkeypatch.setitem(sys.modules, "openai", fake_openai)
    return seen


def _drive_qav(endpoint):
    call = qs._default_seat_call(endpoint)
    with pytest.raises(RuntimeError):
        call("s", "u", "m", 1.0)


def _drive_review(base_url=None):
    call = rs._default_seat_call(base_url)
    with pytest.raises(RuntimeError):
        call("s", "u", "m")


# ===========================================================================
# The QAV shadow
# ===========================================================================


def test_qav_sends_the_key_from_the_environment(captured_client, monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, DUMMY_KEY)
    _drive_qav(qs.DEFAULT_ENDPOINT)
    assert captured_client["api_key"] == DUMMY_KEY


def test_qav_falls_back_to_the_placeholder_key(captured_client):
    _drive_qav(qs.DEFAULT_ENDPOINT)
    assert captured_client["api_key"] == PLACEHOLDER


def test_qav_carries_the_validated_feature_route(captured_client, monkeypatch):
    monkeypatch.setenv(FEATURE_ROUTING_ID_ENV, "feature_A-12")
    monkeypatch.setenv(FEATURE_ROUTING_REQUIRED_ENV, "1")
    _drive_qav(qs.DEFAULT_ENDPOINT)
    assert captured_client["default_headers"] == {
        FEATURE_ROUTING_HEADER: "feature_A-12"
    }


def test_qav_address_default_when_nothing_is_configured():
    assert qs._endpoint({}) == qs.DEFAULT_ENDPOINT
    assert qs.DEFAULT_ENDPOINT == "http://localhost:9000/v1"


def test_qav_address_openai_base_url_beats_the_default(monkeypatch):
    monkeypatch.setenv(BASE_URL_ENV, "http://shared:4000/v1")
    assert qs._endpoint({}) == "http://shared:4000/v1"


def test_qav_address_own_variable_beats_openai_base_url(monkeypatch):
    monkeypatch.setenv(BASE_URL_ENV, "http://shared:4000/v1")
    monkeypatch.setenv(qs.QAV_SHADOW_URL_ENV, "http://mine:4100/v1")
    assert qs._endpoint({}) == "http://mine:4100/v1"


def test_qav_dedicated_runtime_variable_beats_config(monkeypatch):
    monkeypatch.setenv(BASE_URL_ENV, "http://shared:4000/v1")
    monkeypatch.setenv(qs.QAV_SHADOW_URL_ENV, "http://mine:4100/v1")
    assert qs._endpoint({"endpoint": "http://config:4200/v1"}) == "http://mine:4100/v1"


def test_qav_config_block_beats_shared_openai_variable(monkeypatch):
    monkeypatch.setenv(BASE_URL_ENV, "http://shared:4000/v1")
    assert qs._endpoint({"endpoint": "http://config:4200/v1"}) == "http://config:4200/v1"


def test_qav_clean_env_behaves_exactly_as_before(captured_client):
    """Byte-for-byte regression: with none of these variables set the shadow
    sends the placeholder key to llama-swap, as it always has."""
    endpoint = qs._endpoint({})
    _drive_qav(endpoint)
    assert endpoint == "http://localhost:9000/v1"
    assert captured_client["base_url"] == "http://localhost:9000/v1"
    assert captured_client["api_key"] == "not-needed"


# ===========================================================================
# The code-review seat
# ===========================================================================


def test_review_seat_sends_the_key_from_the_environment(captured_client, monkeypatch):
    monkeypatch.setenv(API_KEY_ENV, DUMMY_KEY)
    _drive_review()
    assert captured_client["api_key"] == DUMMY_KEY


def test_review_seat_falls_back_to_the_placeholder_key(captured_client):
    _drive_review()
    assert captured_client["api_key"] == PLACEHOLDER


def test_review_seat_carries_the_validated_feature_route(captured_client, monkeypatch):
    monkeypatch.setenv(FEATURE_ROUTING_ID_ENV, "feature_B-34")
    monkeypatch.setenv(FEATURE_ROUTING_REQUIRED_ENV, "1")
    _drive_review()
    assert captured_client["default_headers"] == {
        FEATURE_ROUTING_HEADER: "feature_B-34"
    }


@pytest.mark.parametrize(
    "routing_id",
    ["", " padded", "dotted.id", "unicode-\N{SNOWMAN}", "a" * 257],
)
def test_invalid_feature_route_is_never_coerced(routing_id):
    with pytest.raises(FeatureRoutingError):
        resolve_feature_routing_headers(environ={FEATURE_ROUTING_ID_ENV: routing_id})


def test_required_feature_route_must_be_present():
    with pytest.raises(FeatureRoutingError):
        resolve_feature_routing_headers(environ={FEATURE_ROUTING_REQUIRED_ENV: "1"})


def test_feature_route_accepts_the_256_byte_ascii_boundary():
    routing_id = "a" * 256
    assert resolve_feature_routing_headers(
        environ={FEATURE_ROUTING_ID_ENV: routing_id}
    ) == {FEATURE_ROUTING_HEADER: routing_id}


@pytest.mark.parametrize("required", ["", "true", " 1", "2"])
def test_required_flag_is_not_trimmed_or_coerced(required):
    with pytest.raises(FeatureRoutingError):
        resolve_feature_routing_headers(
            environ={FEATURE_ROUTING_REQUIRED_ENV: required}
        )


def test_feature_route_preserves_unrelated_headers_without_mutation():
    original = {"X-Trace": "trace", "X-Feature-ID": "route_A"}
    resolved = resolve_feature_routing_headers(
        original,
        environ={
            FEATURE_ROUTING_ID_ENV: "route_A",
            FEATURE_ROUTING_REQUIRED_ENV: "1",
        },
    )
    assert resolved == original
    assert resolved is not original
    assert original == {"X-Trace": "trace", "X-Feature-ID": "route_A"}


@pytest.mark.parametrize(
    "headers",
    [
        {"X-Feature-ID": "other"},
        {"x-feature-id": "route_A", "X-Feature-Id": "route_A"},
    ],
)
def test_conflicting_or_duplicate_caller_route_is_refused(headers):
    with pytest.raises(FeatureRoutingError):
        resolve_feature_routing_headers(
            headers,
            environ={FEATURE_ROUTING_ID_ENV: "route_A"},
        )


def test_review_seat_address_default_when_nothing_is_configured():
    assert rs.resolve_seat_base_url() == rs.DEFAULT_BASE_URL
    assert rs.DEFAULT_BASE_URL == "http://localhost:9000/v1"


def test_review_seat_address_openai_base_url_beats_the_default(monkeypatch):
    monkeypatch.setenv(BASE_URL_ENV, "http://shared:4000/v1")
    assert rs.resolve_seat_base_url() == "http://shared:4000/v1"


def test_review_seat_address_own_variable_beats_openai_base_url(monkeypatch):
    monkeypatch.setenv(BASE_URL_ENV, "http://shared:4000/v1")
    monkeypatch.setenv(rs.REVIEW_SEAT_URL_ENV, "http://mine:4100/v1")
    assert rs.resolve_seat_base_url() == "http://mine:4100/v1"


def test_review_seat_address_an_explicit_value_beats_every_variable(monkeypatch):
    monkeypatch.setenv(BASE_URL_ENV, "http://shared:4000/v1")
    monkeypatch.setenv(rs.REVIEW_SEAT_URL_ENV, "http://mine:4100/v1")
    assert rs.resolve_seat_base_url("http://caller:4200/v1") == "http://caller:4200/v1"


def test_review_seat_call_follows_the_resolved_address(captured_client, monkeypatch):
    monkeypatch.setenv(rs.REVIEW_SEAT_URL_ENV, "http://mine:4100/v1")
    _drive_review()
    assert captured_client["base_url"] == "http://mine:4100/v1"


def test_review_seat_clean_env_behaves_exactly_as_before(captured_client):
    """Byte-for-byte regression: with none of these variables set the seat call
    goes to llama-swap with the placeholder key, as it always has."""
    _drive_review()
    assert captured_client["base_url"] == "http://localhost:9000/v1"
    assert captured_client["api_key"] == "not-needed"
