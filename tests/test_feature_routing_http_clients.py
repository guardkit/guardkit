"""Loopback wire checks for every GuardKit model HTTP client."""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from guardkit.lib.client_env import (
    FEATURE_ROUTING_HEADER,
    FEATURE_ROUTING_ID_ENV,
    FEATURE_ROUTING_REQUIRED_ENV,
    FeatureRoutingError,
)
from guardkit.orchestrator.stamp_model_fallback import ConfiguredAsker
from guardkit.qa.qav_shadow import _default_seat_call as qav_call
from guardkit.qa.review_seat import _default_seat_call as review_call


@pytest.fixture
def loopback(monkeypatch):
    state = SimpleNamespace(requests=[])

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            state.requests.append((self.path, dict(self.headers), body))
            payload = json.dumps(
                {
                    "id": "fixture",
                    "object": "chat.completion",
                    "created": 0,
                    "model": body["model"],
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": "fixture answer"},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": 1,
                        "completion_tokens": 1,
                        "total_tokens": 2,
                    },
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = server.server_address[1]
    enabled = True
    denied = []

    def audit(event, args):
        if not enabled:
            return
        if event == "socket.connect":
            address = args[1]
            if isinstance(address, tuple) and address[:2] != ("127.0.0.1", port):
                denied.append(str(address))
                raise AssertionError(f"non-fixture connection forbidden: {address}")
        elif event == "socket.getaddrinfo" and args[0] != "127.0.0.1":
            denied.append(str(args[:2]))
            raise AssertionError("non-fixture DNS forbidden")

    sys.addaudithook(audit)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    for name in list(os.environ):
        if "proxy" in name.lower():
            monkeypatch.delenv(name)
    monkeypatch.setenv(FEATURE_ROUTING_ID_ENV, "wire_route-A")
    monkeypatch.setenv(FEATURE_ROUTING_REQUIRED_ENV, "1")
    state.base_url = f"http://127.0.0.1:{port}/v1"
    try:
        yield state
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)
        enabled = False
        assert not denied, denied


def test_all_guardkit_clients_transmit_the_same_feature_header(loopback):
    qav = qav_call(loopback.base_url)
    review = review_call(loopback.base_url, timeout_s=2)
    stamp = ConfiguredAsker(loopback.base_url, "stamp-model", 2)

    assert qav("system", "user", "qav-model", 2).text == "fixture answer"
    assert review("system", "user", "review-model") == "fixture answer"
    assert stamp("prompt") == "fixture answer"

    assert len(loopback.requests) == 3
    for path, headers, body in loopback.requests:
        assert path == "/v1/chat/completions"
        normalized = {name.lower(): value for name, value in headers.items()}
        assert normalized[FEATURE_ROUTING_HEADER] == "wire_route-A"
        assert body["model"] in {"qav-model", "review-model", "stamp-model"}


@pytest.mark.parametrize("client", ["qav", "review", "stamp"])
def test_missing_required_route_makes_zero_http_requests(loopback, monkeypatch, client):
    monkeypatch.delenv(FEATURE_ROUTING_ID_ENV)
    call = {
        "qav": lambda: qav_call(loopback.base_url)("s", "u", "m", 2),
        "review": lambda: review_call(loopback.base_url, timeout_s=2)("s", "u", "m"),
        "stamp": lambda: ConfiguredAsker(loopback.base_url, "m", 2)("p"),
    }[client]
    with pytest.raises(FeatureRoutingError):
        call()
    assert loopback.requests == []
