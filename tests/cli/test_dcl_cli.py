"""``guardkit dcl`` CLI smoke tests (D2 §2) — check / derive / run via CliRunner."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from guardkit.cli.dcl import dcl

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "dcl"
requires_node = pytest.mark.skipif(
    shutil.which("node") is None, reason="node required for the vendored WASM checker"
)


@requires_node
def test_check_valid_exits_0() -> None:
    result = CliRunner().invoke(dcl, ["check", str(FIXTURES / "capability.dcl")])
    assert result.exit_code == 0, result.output
    assert "COMPILE OK" in result.output


@requires_node
def test_check_broken_exits_1() -> None:
    result = CliRunner().invoke(dcl, ["check", str(FIXTURES / "broken.dcl")])
    assert result.exit_code == 1
    assert "COMPILE FAILED" in result.output


@requires_node
def test_derive_writes_set_and_receipt(tmp_path) -> None:
    # Assemble a target repo: features/<f>/<f>.dcl + qa/dcl/binding.yaml.
    repo = tmp_path / "repo"
    (repo / "features" / "stats-endpoint").mkdir(parents=True)
    shutil.copy(FIXTURES / "capability.dcl", repo / "features" / "stats-endpoint" / "stats-endpoint.dcl")
    (repo / "qa" / "dcl").mkdir(parents=True)
    shutil.copy(FIXTURES / "binding.yaml", repo / "qa" / "dcl" / "binding.yaml")

    result = CliRunner().invoke(
        dcl, ["derive", "--feature", "stats-endpoint", "--repo", str(repo)]
    )
    assert result.exit_code == 0, result.output
    assert "13 RUN / 1 SKIP" in result.output

    derived = repo / "qa" / "dcl" / "derived" / "stats-endpoint.yaml"
    receipt = repo / "qa" / "dcl" / "derivation-stats-endpoint.yaml"
    assert derived.is_file()
    assert receipt.is_file()
    # The receipt validates as its registered kind via the qa CLI.
    from guardkit.cli.qa import qa

    v = CliRunner().invoke(qa, ["validate", "dcl-derivation", str(receipt)])
    assert v.exit_code == 0, v.output


def test_run_missing_env_exits_2(tmp_path) -> None:
    import yaml

    from guardkit.qa.dcl.assertion_runner import load_assertion_set  # noqa: F401

    aset = {
        "invocation": {"method": "GET", "path": "/stats"},
        "assertions": [
            {"id": "A-OUTCOME", "rule": "R2", "dcl_source": "o", "disposition": "RUN",
             "predicate": {"check": "status_equals", "expected": 200}}
        ],
    }
    p = tmp_path / "derived.yaml"
    p.write_text(yaml.safe_dump(aset), encoding="utf-8")
    result = CliRunner().invoke(
        dcl, ["run", "--assertions", str(p), "--base-url-env", "UNSET_DCL_ENV_XYZ"]
    )
    assert result.exit_code == 2
    assert "unset" in result.output


def test_run_emits_f4_envelope(tmp_path, monkeypatch) -> None:
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    import yaml

    class _H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            body = b'{"service":"api","requests_served":5,"first_request_at":null}'
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = HTTPServer(("127.0.0.1", 0), _H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        aset = {
            "invocation": {"method": "GET", "path": "/stats"},
            "assertions": [
                {"id": "A-OUTCOME", "rule": "R2", "dcl_source": "o", "disposition": "RUN",
                 "predicate": {"check": "status_equals", "expected": 200}}
            ],
        }
        p = tmp_path / "derived.yaml"
        p.write_text(yaml.safe_dump(aset), encoding="utf-8")
        monkeypatch.setenv("DCL_CLI_BASE_URL", f"http://127.0.0.1:{server.server_port}")
        result = CliRunner().invoke(
            dcl, ["run", "--assertions", str(p), "--base-url-env", "DCL_CLI_BASE_URL"]
        )
    finally:
        server.shutdown()
        server.server_close()
    assert result.exit_code == 0, result.output
    envelope = json.loads(result.output)
    assert envelope["assertions"][0]["id"] == "A-OUTCOME"
    assert envelope["assertions"][0]["status"] == "pass"
