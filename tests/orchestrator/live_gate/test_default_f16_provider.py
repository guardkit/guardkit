"""DefaultF16ChecklistProvider — the bare-CLI F16 fix (ruled 08-15).

Before this default, the bare ``guardkit qa live-gate`` CLI hit the
``UnconfiguredF16ChecklistProvider`` stub on every repo and every run was
``environment_fail`` (proven run PILOT-HURL-local-20260814T205745Z). The
default provider performs one REAL check — a reachability GET against each
selected gate's registry ``base_url_env`` (any HTTP answer = ready) — and
records the remaining perishable prereqs declared-not-verified ``ok=True``
(the existing recorded-not-faked convention). These tests prove the verdict
follows the gate, not ``environment_fail``, once something is listening.
"""

from __future__ import annotations

import http.server
import textwrap
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest
import yaml

from guardkit.orchestrator.live_gate.preflight import (
    DefaultF16ChecklistProvider,
    SeamResult,
)
from guardkit.orchestrator.live_gate.runner import LiveGateRunner
from guardkit.qa.formats.gate_registry import GateEntry, GateTarget

_FIXED = datetime(2026, 8, 15, 12, 0, 0, tzinfo=timezone.utc)


def _gate(gate_id: str = "g1", env_var: str = "BASE") -> GateEntry:
    return GateEntry(
        id=gate_id,
        path=f"qa/gates/{gate_id}.py",
        target=GateTarget(base_url_env=env_var, environment_id="env"),
        pass_bar_ref="qa/pass-bar-T-1.yaml",
        evidence_dir_pattern="qa/gates/evidence-{date}/shots",
    )


@pytest.fixture()
def live_server():
    """A real localhost HTTP server on an ephemeral port (404s everything —
    an HTTP answer all the same)."""
    handler = http.server.SimpleHTTPRequestHandler
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join(timeout=5)


class TestChecklistShape:
    def test_env_unset_is_not_ready(self):
        provider = DefaultF16ChecklistProvider([_gate()], env={})
        results = list(provider.checklist())
        assert len(results) == 2  # reachability + declared-not-verified tail
        assert results[0].ok is False
        assert "BASE" in results[0].detail and "not set" in results[0].detail

    def test_declared_not_verified_tail_is_ok_true(self):
        provider = DefaultF16ChecklistProvider([_gate()], env={})
        tail = list(provider.checklist())[-1]
        assert tail.ok is True
        assert "declared-not-verified" in tail.detail

    def test_duplicate_env_vars_checked_once(self, live_server):
        gates = [_gate("g1"), _gate("g2")]  # both target BASE
        provider = DefaultF16ChecklistProvider(gates, env={"BASE": live_server})
        results = list(provider.checklist())
        assert len(results) == 2  # ONE reachability check + the tail

    def test_distinct_env_vars_each_checked(self):
        gates = [_gate("g1", "BASE_A"), _gate("g2", "BASE_B")]
        provider = DefaultF16ChecklistProvider(gates, env={})
        results = list(provider.checklist())
        assert len(results) == 3
        assert all(isinstance(r, SeamResult) for r in results)


class TestReachability:
    def test_http_answer_is_ready_even_when_404(self, live_server):
        # SimpleHTTPRequestHandler 404s unknown paths — an answer regardless.
        provider = DefaultF16ChecklistProvider(
            [_gate()], env={"BASE": f"{live_server}/definitely-missing"}
        )
        result = list(provider.checklist())[0]
        assert result.ok is True
        assert "reachable" in result.detail

    def test_http_200_is_ready(self, live_server):
        provider = DefaultF16ChecklistProvider([_gate()], env={"BASE": live_server})
        result = list(provider.checklist())[0]
        assert result.ok is True
        assert "HTTP" in result.detail

    def test_connection_refused_is_not_ready(self, live_server):
        # Derive a port with nothing listening from the live server's port.
        port = int(live_server.rsplit(":", 1)[1])
        dead = f"http://127.0.0.1:{port + 1 if port < 65535 else port - 1}"
        provider = DefaultF16ChecklistProvider(
            [_gate()], env={"BASE": dead}, timeout_s=2.0
        )
        result = list(provider.checklist())[0]
        assert result.ok is False
        assert "unreachable" in result.detail

    def test_garbage_url_is_not_ready_never_a_crash(self):
        provider = DefaultF16ChecklistProvider(
            [_gate()], env={"BASE": "127.0.0.1:99999-no-scheme"}
        )
        result = list(provider.checklist())[0]
        assert result.ok is False


# ---------------------------------------------------------------------------
# Runner-level: the bare runner's verdict follows the GATE once the target
# answers (the exact failure shape of PILOT-HURL-local-20260814T205745Z).
# ---------------------------------------------------------------------------

_PASS_BAR = textwrap.dedent(
    """\
    format_version: "2.0"
    task_id: T-1
    registered_at: {sha: abcd, date: "2026-07-05"}
    auth_surface_bearing: true
    preconditions: [suite_green_vs_ledger]
    criteria:
      - {id: C1, text: "answers", class: machine, evidence_kind: json}
    negative_paths: [wrong_credential, anonymous_deep_link, post_logout_401, unauthorized_403_ui, dependency_down_degradation]
    """
)


def _build_repo(tmp_path: Path, *, gate_body: str) -> Path:
    (tmp_path / "qa" / "gates").mkdir(parents=True)
    (tmp_path / "qa" / "pass-bar-T-1.yaml").write_text(_PASS_BAR)
    (tmp_path / "qa" / "gates" / "g1.py").write_text(gate_body)
    registry = {
        "format_version": "1.0",
        "gates": [
            {
                "id": "g1",
                "path": "qa/gates/g1.py",
                "target": {"base_url_env": "BASE", "environment_id": "local"},
                "pass_bar_ref": "qa/pass-bar-T-1.yaml",
                "evidence_dir_pattern": "qa/gates/evidence-{date}/shots-g1",
            }
        ],
    }
    (tmp_path / "qa" / "gates" / "registry.yaml").write_text(yaml.safe_dump(registry))
    return tmp_path


class TestBareRunnerVerdictFollowsGate:
    def test_passing_gate_with_live_target_is_pass(self, tmp_path, live_server):
        repo = _build_repo(tmp_path, gate_body="import sys; sys.exit(0)\n")
        runner = LiveGateRunner(
            repo, gate_env={"BASE": live_server}, now_fn=lambda: _FIXED
        )
        env = runner.run("PILOT", "local")
        assert env.verdict == "pass"
        f16_checks = [
            c for c in env.preflight.checks if c["name"].startswith("f16-checklist")
        ]
        assert f16_checks and all(c["ok"] for c in f16_checks)

    def test_failing_gate_with_live_target_is_fail_not_environment_fail(
        self, tmp_path, live_server
    ):
        repo = _build_repo(tmp_path, gate_body="import sys; sys.exit(1)\n")
        runner = LiveGateRunner(
            repo, gate_env={"BASE": live_server}, now_fn=lambda: _FIXED
        )
        env = runner.run("PILOT", "local")
        assert env.verdict == "fail"  # the GATE's verdict, not environment_fail

    def test_base_env_unset_is_still_honest_environment_fail(self, tmp_path):
        repo = _build_repo(tmp_path, gate_body="import sys; sys.exit(0)\n")
        runner = LiveGateRunner(repo, gate_env={}, now_fn=lambda: _FIXED)
        env = runner.run("PILOT", "local")
        assert env.verdict == "environment_fail"
        assert env.gates == []  # short-circuit: the gate never ran

    def test_injected_provider_still_wins_over_default(self, tmp_path):
        from guardkit.orchestrator.live_gate.preflight import F16ChecklistProvider

        class _RedF16(F16ChecklistProvider):
            def checklist(self):
                return [SeamResult(ok=False, detail="injected red")]

        repo = _build_repo(tmp_path, gate_body="import sys; sys.exit(0)\n")
        runner = LiveGateRunner(
            repo, f16_provider=_RedF16(), gate_env={"BASE": "http://unused"},
            now_fn=lambda: _FIXED,
        )
        env = runner.run("PILOT", "local")
        assert env.verdict == "environment_fail"
        assert any("injected red" in c["detail"] for c in env.preflight.checks)
