"""assertion_runner.py — generic F4 executor over a derived set (D2 §2).

Drives a local ``http.server`` stub: a green case (all pass, exit 0, SKIP not
executed), a failing-assertion case (exit 1 with a LOUD envelope), and an
unreachable-port case (fails loud, never green, never silent-skip).
"""

from __future__ import annotations

import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Iterator

import pytest

from guardkit.qa.dcl import assertion_runner
from guardkit.qa.dcl.assertion_runner import RunnerError, run, run_file

GOOD_FRA = "2026-07-12T14:57:52.958536+00:00"


def _assertion_set(fra: str = GOOD_FRA) -> dict:
    return {
        "invocation": {"method": "GET", "path": "/stats"},
        "assertions": [
            {"id": "A-OUTCOME", "rule": "R2", "dcl_source": "outcome",
             "disposition": "RUN", "predicate": {"check": "status_equals", "expected": 200}},
            {"id": "A-FIELD-SVC", "rule": "R3", "dcl_source": "service",
             "disposition": "RUN",
             "predicate": {"check": "field_present_typed", "wire_key": "service", "dcl_type": "Text"}},
            {"id": "A-FIELD-REQ", "rule": "R3", "dcl_source": "requestsServed",
             "disposition": "RUN",
             "predicate": {"check": "field_present_typed", "wire_key": "requests_served", "dcl_type": "Number"}},
            {"id": "A-FIELD-FRA", "rule": "R3", "dcl_source": "firstRequestAt",
             "disposition": "RUN",
             "predicate": {"check": "field_present_typed", "wire_key": "first_request_at",
                           "dcl_type": "Text", "nullable": True}},
            {"id": "A-COUNT-MONO", "rule": "R4", "dcl_source": "count",
             "disposition": "RUN",
             "predicate": {"check": "non_decreasing", "wire_key": "requests_served"}},
            {"id": "A-DURATION", "rule": "R5", "dcl_source": "duration",
             "disposition": "RUN",
             "predicate": {"check": "latency_below", "bound_seconds": 5.0}},
            {"id": "A-LIFE-SERVING", "rule": "R6", "dcl_source": "move Fresh->Serving",
             "disposition": "RUN",
             "predicate": {"check": "field_non_null", "wire_key": "first_request_at"}},
            {"id": "A-LIFE-STABLE", "rule": "R7", "dcl_source": "end Serving",
             "disposition": "RUN",
             "predicate": {"check": "field_stable", "wire_key": "first_request_at"}},
            {"id": "A-FRA-FORMAT", "rule": "R3+J5", "dcl_source": "firstRequestAt fmt",
             "disposition": "RUN",
             "predicate": {"check": "format", "wire_key": "first_request_at", "format": "iso8601_utc"}},
            {"id": "A-AVAIL", "rule": "R8", "dcl_source": "availability policy",
             "disposition": "SKIP",
             "predicate": {"check": "availability_under_dependency_down"},
             "reason": "needs fault-injection"},
            {"id": "A-CW-POST", "rule": "R10", "dcl_source": "closed-world",
             "disposition": "RUN",
             "predicate": {"check": "status_in_range", "low": 400, "high": 499},
             "request": {"method": "POST", "path": "/stats", "body": "{}"}},
        ],
    }


def _make_handler(fra: str):
    counter = {"n": 100}

    class _Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # silence
            pass

        def do_GET(self):
            counter["n"] += 1
            body = json.dumps(
                {"service": "api", "requests_served": counter["n"], "first_request_at": fra}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _reject(self):
            self.send_response(405)
            self.send_header("Content-Length", "0")
            self.end_headers()

        do_POST = do_PUT = do_PATCH = do_DELETE = _reject

    return _Handler


@contextmanager
def _stub(fra: str = GOOD_FRA) -> Iterator[str]:
    server = HTTPServer(("127.0.0.1", 0), _make_handler(fra))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()


def test_green_case_all_pass_exit_0() -> None:
    with _stub() as base_url:
        envelope, code = run(_assertion_set(), base_url)
    assert code == 0
    ids = {a["id"] for a in envelope["assertions"]}
    # Every RUN assertion is reported; the SKIP is NOT executed.
    assert "A-AVAIL" not in ids
    assert len(envelope["assertions"]) == 10  # 10 RUN; the 1 SKIP is not executed
    assert all(a["status"] == "pass" for a in envelope["assertions"])


def test_failing_assertion_exits_1_with_loud_envelope() -> None:
    # A non-ISO first_request_at breaks A-FRA-FORMAT (only).
    with _stub(fra="not-a-timestamp") as base_url:
        envelope, code = run(_assertion_set(), base_url)
    assert code == 1
    by_id = {a["id"]: a for a in envelope["assertions"]}
    assert by_id["A-FRA-FORMAT"]["status"] == "fail"
    # Loud: the observed value + expected shape are on the record, not a bare bool.
    assert by_id["A-FRA-FORMAT"]["observed"]
    assert by_id["A-FRA-FORMAT"]["expected"] == "UTC ISO-8601"
    # Everything else stayed green — the failure is specific, not a blanket red.
    assert by_id["A-OUTCOME"]["status"] == "pass"


def test_unreachable_port_fails_loud() -> None:
    # Nothing is listening here — every dependent assertion must fail LOUD.
    envelope, code = run(_assertion_set(), "http://127.0.0.1:1")
    assert code == 1
    assert envelope["assertions"], "must enumerate failures, never silent-skip"
    assert all(a["status"] == "fail" for a in envelope["assertions"])
    assert any("A-AVAIL" != a["id"] for a in envelope["assertions"])
    # The reach failure is described, never greened.
    assert any(a["observed"] for a in envelope["assertions"])


def test_cw_verb_accepted_is_a_failure() -> None:
    """Poison drill: if a mutating verb is NOT rejected, A-CW-POST must go red."""

    class _AllOK(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            body = json.dumps(
                {"service": "api", "requests_served": 1, "first_request_at": GOOD_FRA}
            ).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_POST(self):  # WRONG: accepts the mutation
            self.send_response(200)
            self.send_header("Content-Length", "0")
            self.end_headers()

    server = HTTPServer(("127.0.0.1", 0), _AllOK)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        envelope, code = run(_assertion_set(), f"http://127.0.0.1:{server.server_port}")
    finally:
        server.shutdown()
        server.server_close()
    by_id = {a["id"]: a for a in envelope["assertions"]}
    assert code == 1
    assert by_id["A-CW-POST"]["status"] == "fail"
    assert by_id["A-CW-POST"]["observed"] == "200"


def test_run_file_reads_env_var(tmp_path, monkeypatch) -> None:
    import yaml

    aset_path = tmp_path / "derived.yaml"
    aset_path.write_text(yaml.safe_dump(_assertion_set()), encoding="utf-8")
    with _stub() as base_url:
        monkeypatch.setenv("DCL_TEST_BASE_URL", base_url)
        envelope, code = run_file(aset_path, "DCL_TEST_BASE_URL")
    assert code == 0
    assert envelope["assertions"]


def test_missing_env_var_is_loud() -> None:
    with pytest.raises(RunnerError, match="unset"):
        assertion_runner.resolve_base_url("DEFINITELY_UNSET_DCL_VAR_XYZ")


def test_hardcoded_url_is_refused() -> None:
    with pytest.raises(RunnerError):
        assertion_runner.resolve_base_url("")
