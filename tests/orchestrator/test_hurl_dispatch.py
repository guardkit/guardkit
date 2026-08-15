"""THE ROUTING LAW — hurl dispatch (card Q8/A.2, the FIRST home routed).

Before this lane the ``verifier:`` stamp VALIDATED at plan load
(``test_verifier_stamp_routing_law.py``) but no home CONSUMED it. This is the
smallest honest consumer for ``hurl``:

* ``FeatureOrchestrator._hurl_scenarios_for`` — the titles a feature stamps
  ``verifier: hurl`` (``Feature.scenarios`` via feature_loader), threaded to
  ``AutoBuildOrchestrator(hurl_scenarios=...)`` and on to ``CoachValidator``.
* ``CoachValidator._produce_hurl_twins`` — the Coach's independent-verification
  leg ALSO drives the repo's registered ``hurl-twins`` gate
  (``qa/gates/registry.yaml``) against the deployed target named by the entry's
  ``base_url_env``. Env unset -> ``absent`` with reason
  ``"no deployed target — twins run at the close"`` (NOT a failure).
* ``AgentInvoker._apply_hurl_twins_guard`` — ran-and-failed -> must_fix
  (mirrors ``_apply_behavioural_oracle_guard``); absent -> no-op.

The four ruled cases: stamped+registered+env (runs) · stamped+no env
(absent, non-blocking) · unstamped (no-op) · stamped+unregistered
(absent + reason). Plus: unreachable target = absent (environment, never a
red), the ran-and-failed override, and the threading seams.
"""

from __future__ import annotations

import json
import os
import socket
import textwrap
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Iterator, List, Optional
from unittest.mock import MagicMock

import pytest
import yaml

os.environ.setdefault("GUARDKIT_HARNESS", "sdk")

from guardkit.orchestrator.agent_invoker import AgentInvoker  # noqa: E402
from guardkit.orchestrator.autobuild import AutoBuildOrchestrator  # noqa: E402
from guardkit.orchestrator.feature_loader import Feature, FeatureLoader  # noqa: E402
from guardkit.orchestrator.feature_orchestrator import (  # noqa: E402
    FeatureOrchestrator,
)
from guardkit.orchestrator.quality_gates.coach_evidence import (  # noqa: E402
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import (  # noqa: E402
    CoachValidator,
)
from guardkit.orchestrator.verifier_stamp import ScenarioStamp  # noqa: E402


ENV_NAME = "HURL_DISPATCH_TEST_BASE_URL"
TITLE_A = "User signs in with valid credentials"
TITLE_B = "Rate limiter refuses the 6th attempt"
NO_TARGET_REASON = "no deployed target — twins run at the close"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _write_registry(repo: Path, *, gate_ids: List[str], env_name: str = ENV_NAME) -> None:
    gates = []
    for gid in gate_ids:
        gates.append(
            {
                "id": gid,
                "path": f"qa/gates/{gid.replace('-', '_')}_gate.py",
                "target": {"base_url_env": env_name, "environment_id": "local"},
                "preflight": ["tool_imports", "base_url_reachable"],
                "pass_bar_ref": f"qa/pass-bar-{gid.upper()}.yaml",
                "evidence_dir_pattern": "qa/gates/evidence/{run_id}",
            }
        )
    reg = repo / "qa" / "gates" / "registry.yaml"
    reg.parent.mkdir(parents=True, exist_ok=True)
    reg.write_text(yaml.dump({"format_version": "1.0", "gates": gates}), encoding="utf-8")


def _write_gate_script(repo: Path, *, failing: bool, exit_code: Optional[int] = None) -> Path:
    """A stand-in for api_test's hurl_twin_gate.py honouring the F4 envelope."""
    path = repo / "qa" / "gates" / "hurl_twins_gate.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    if failing:
        assertions = [
            {"id": "hurl-twins::update-persists::12", "status": "pass",
             "observed": "200", "expected": "200", "evidence_ref": "e"},
            {"id": "hurl-twins::update-persists::31", "status": "fail",
             "observed": "full_name=OLD NAME", "expected": "full_name=NEW NAME",
             "evidence_ref": "e"},
        ]
        code = 1 if exit_code is None else exit_code
    else:
        assertions = [
            {"id": "hurl-twins::update-persists::12", "status": "pass",
             "observed": "200", "expected": "200", "evidence_ref": "e"},
        ]
        code = 0 if exit_code is None else exit_code
    path.write_text(
        textwrap.dedent(
            f"""\
            import json, os, sys
            # The gate reads the SAME env var the registry names (never a URL).
            assert os.environ.get({ENV_NAME!r}), "base_url env not threaded"
            print(json.dumps({{"assertions": {json.dumps(assertions)}}}))
            sys.exit({code})
            """
        ),
        encoding="utf-8",
    )
    return path


class _Quiet(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *_a, **_k):  # silence
        return


@pytest.fixture
def live_target() -> Iterator[str]:
    """A tiny HTTP listener standing in for the deployed candidate."""
    srv = HTTPServer(("127.0.0.1", 0), _Quiet)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        yield f"http://127.0.0.1:{srv.server_port}"
    finally:
        srv.shutdown()
        srv.server_close()


def _dead_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _validator(repo: Path, hurl_scenarios: Optional[List[str]]) -> CoachValidator:
    return CoachValidator(
        str(repo),
        task_id="TASK-HD-001",
        hurl_scenarios=hurl_scenarios,
        test_timeout=60,
    )


# ---------------------------------------------------------------------------
# 1. The producer — CoachValidator._produce_hurl_twins
# ---------------------------------------------------------------------------


class TestProducerNoOp:
    def test_unstamped_feature_is_a_no_op(self, tmp_path: Path, monkeypatch) -> None:
        """Ruled case: unstamped -> no-op. Field stays None even when a
        registry + target exist (the stamp is the only activator)."""
        monkeypatch.setenv(ENV_NAME, "http://127.0.0.1:1")
        _write_registry(tmp_path, gate_ids=["hurl-twins"])
        _write_gate_script(tmp_path, failing=True)
        assert _validator(tmp_path, None)._produce_hurl_twins() is None
        assert _validator(tmp_path, [])._produce_hurl_twins() is None

    def test_default_ctor_has_no_hurl_leg(self, tmp_path: Path) -> None:
        v = CoachValidator(str(tmp_path), task_id="TASK-HD-001")
        assert v.hurl_scenarios == []
        assert v._produce_hurl_twins() is None


class TestProducerAbsent:
    def test_stamped_no_registry_is_absent_with_reason(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv(ENV_NAME, "http://127.0.0.1:1")
        out = _validator(tmp_path, [TITLE_A])._produce_hurl_twins()
        assert out is not None
        assert out["status"] == "absent"
        assert out["passed"] is None
        assert "not registered" in out["reason"]
        assert "registry.yaml" in out["reason"]
        assert out["scenarios"] == [TITLE_A]

    def test_stamped_unregistered_is_absent_naming_registered_gates(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Ruled case: stamped + unregistered -> absent + reason."""
        monkeypatch.setenv(ENV_NAME, "http://127.0.0.1:1")
        _write_registry(tmp_path, gate_ids=["health", "stats"])
        out = _validator(tmp_path, [TITLE_A])._produce_hurl_twins()
        assert out["status"] == "absent"
        assert "hurl-twins gate not registered" in out["reason"]
        assert "health" in out["reason"] and "stats" in out["reason"]

    def test_stamped_registered_env_unset_is_absent_no_target(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """Ruled case: stamped + no env -> absent, the exact no-target sentence."""
        monkeypatch.delenv(ENV_NAME, raising=False)
        _write_registry(tmp_path, gate_ids=["hurl-twins"])
        _write_gate_script(tmp_path, failing=True)  # would fail IF it ran — it must not
        out = _validator(tmp_path, [TITLE_A, TITLE_B])._produce_hurl_twins()
        assert out["status"] == "absent"
        assert out["reason"] == NO_TARGET_REASON
        assert out["base_url_env"] == ENV_NAME
        assert out["passed"] is None
        assert out["scenario_count"] == 2
        assert "exit_code" not in out  # nothing ran

    def test_stamped_registered_env_set_but_unreachable_is_absent(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """A dead target is environment, never a red twin (ST-11 attribution).
        The base_url VALUE is never echoed into the bundle."""
        url = f"http://127.0.0.1:{_dead_port()}"
        monkeypatch.setenv(ENV_NAME, url)
        _write_registry(tmp_path, gate_ids=["hurl-twins"])
        _write_gate_script(tmp_path, failing=True)
        out = _validator(tmp_path, [TITLE_A])._produce_hurl_twins()
        assert out["status"] == "absent"
        assert "not reachable" in out["reason"]
        assert url not in json.dumps(out)

    def test_registered_but_script_missing_is_absent_undrivable(
        self, tmp_path: Path, monkeypatch, live_target: str
    ) -> None:
        monkeypatch.setenv(ENV_NAME, live_target)
        _write_registry(tmp_path, gate_ids=["hurl-twins"])
        out = _validator(tmp_path, [TITLE_A])._produce_hurl_twins()
        assert out["status"] == "absent"
        assert "could not be driven" in out["reason"]

    def test_malformed_registry_is_absent(self, tmp_path: Path, monkeypatch) -> None:
        monkeypatch.setenv(ENV_NAME, "http://127.0.0.1:1")
        reg = tmp_path / "qa" / "gates" / "registry.yaml"
        reg.parent.mkdir(parents=True)
        reg.write_text("format_version: '1.0'\ngates: []\n")  # min_length=1 violated
        out = _validator(tmp_path, [TITLE_A])._produce_hurl_twins()
        assert out["status"] == "absent"
        assert "failed to load" in out["reason"]


class TestProducerRuns:
    def test_stamped_registered_env_reachable_runs_and_passes(
        self, tmp_path: Path, monkeypatch, live_target: str
    ) -> None:
        """Ruled case: stamped + registered + env -> RUNS."""
        monkeypatch.setenv(ENV_NAME, live_target)
        _write_registry(tmp_path, gate_ids=["hurl-twins"])
        _write_gate_script(tmp_path, failing=False)
        out = _validator(tmp_path, [TITLE_A])._produce_hurl_twins()
        assert out["status"] == "ran"
        assert out["passed"] is True
        assert out["exit_code"] == 0
        assert out["assertions_total"] == 1
        assert out["assertions_failed"] == []
        assert out["timed_out"] is False
        assert out["gate_path"] == "qa/gates/hurl_twins_gate.py"
        assert live_target not in json.dumps(out)

    def test_stamped_registered_env_reachable_runs_and_fails(
        self, tmp_path: Path, monkeypatch, live_target: str
    ) -> None:
        monkeypatch.setenv(ENV_NAME, live_target)
        _write_registry(tmp_path, gate_ids=["hurl-twins"])
        _write_gate_script(tmp_path, failing=True)
        out = _validator(tmp_path, [TITLE_A])._produce_hurl_twins()
        assert out["status"] == "ran"
        assert out["passed"] is False
        assert out["exit_code"] == 1
        assert [f["id"] for f in out["assertions_failed"]] == [
            "hurl-twins::update-persists::31"
        ]
        assert "OLD NAME" in out["output_tail"]

    def test_exit_nonzero_with_no_failing_assertion_still_fails(
        self, tmp_path: Path, monkeypatch, live_target: str
    ) -> None:
        """Absence-of-failure: the executor's synthetic ::exit assertion wins."""
        monkeypatch.setenv(ENV_NAME, live_target)
        _write_registry(tmp_path, gate_ids=["hurl-twins"])
        _write_gate_script(tmp_path, failing=False, exit_code=3)
        out = _validator(tmp_path, [TITLE_A])._produce_hurl_twins()
        assert out["status"] == "ran"
        assert out["passed"] is False
        assert any(f["id"].endswith("::exit") for f in out["assertions_failed"])

    def test_gather_evidence_carries_the_leg_into_the_bundle(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """The bundle field is populated on the complete path (env unset ->
        absent) and serialises via to_dict like every other leg."""
        monkeypatch.delenv(ENV_NAME, raising=False)
        _write_registry(tmp_path, gate_ids=["hurl-twins"])
        v = _validator(tmp_path, [TITLE_A])
        out = v._produce_hurl_twins()
        bundle = CoachEvidenceBundle(honesty=None, hurl_twins=out)
        d = bundle.to_dict()
        assert d["hurl_twins"]["status"] == "absent"
        assert d["hurl_twins"]["reason"] == NO_TARGET_REASON
        assert CoachEvidenceBundle(honesty=None).hurl_twins is None


# ---------------------------------------------------------------------------
# 2. The guard — AgentInvoker._apply_hurl_twins_guard
# ---------------------------------------------------------------------------


def _guard(decision: Dict[str, Any], hurl_twins: Optional[Dict[str, Any]], tmp_path: Path) -> Dict[str, Any]:
    inv = AgentInvoker.__new__(AgentInvoker)
    bundle = CoachEvidenceBundle(honesty=None, hurl_twins=hurl_twins)
    coach_path = tmp_path / "coach_turn_1.json"
    coach_path.write_text(json.dumps(decision))
    inv._apply_hurl_twins_guard(
        decision=decision,
        evidence_bundle=bundle,
        task_id="TASK-HD-001",
        turn=1,
        coach_output_path=coach_path,
    )
    return decision


def _ran_failed() -> Dict[str, Any]:
    return {
        "gate_id": "hurl-twins",
        "base_url_env": ENV_NAME,
        "scenarios": [TITLE_A],
        "scenario_count": 1,
        "status": "ran",
        "passed": False,
        "exit_code": 1,
        "timed_out": False,
        "duration": 1.2,
        "assertions_total": 2,
        "assertions_failed": [
            {"id": "hurl-twins::update-persists::31",
             "observed": "full_name=OLD NAME", "expected": "full_name=NEW NAME"}
        ],
        "output_tail": "hurl-twins::update-persists::31: observed='full_name=OLD NAME' expected='full_name=NEW NAME'",
    }


class TestGuard:
    def test_ran_and_failed_overrides_approve_to_feedback_must_fix(self, tmp_path: Path) -> None:
        decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
        out = _guard(decision, _ran_failed(), tmp_path)
        assert out["decision"] == "feedback"
        issue = out["issues"][0]
        assert issue["severity"] == "must_fix"
        assert issue["category"] == "hurl_twins_failure"
        assert "hurl-twins::update-persists::31" in issue["description"]
        assert "OLD NAME" in issue["test_output"]
        assert issue["details"]["base_url_env"] == ENV_NAME
        persisted = json.loads((tmp_path / "coach_turn_1.json").read_text())
        assert persisted["decision"] == "feedback"

    def test_timed_out_is_ran_and_failed(self, tmp_path: Path) -> None:
        twins = {**_ran_failed(), "timed_out": True, "exit_code": 124, "assertions_failed": []}
        out = _guard({"decision": "approve", "issues": [], "rationale": "x"}, twins, tmp_path)
        assert out["decision"] == "feedback"
        assert "timed out" in out["rationale"]

    def test_absent_no_target_is_non_blocking(self, tmp_path: Path) -> None:
        """Ruled case: stamped + no env -> absent, NON-blocking."""
        twins = {
            "gate_id": "hurl-twins", "scenarios": [TITLE_A], "scenario_count": 1,
            "status": "absent", "passed": None, "reason": NO_TARGET_REASON,
            "base_url_env": ENV_NAME,
        }
        out = _guard({"decision": "approve", "issues": [], "rationale": "lgtm"}, twins, tmp_path)
        assert out["decision"] == "approve"
        assert out["issues"] == []

    def test_absent_unregistered_is_non_blocking(self, tmp_path: Path) -> None:
        twins = {"gate_id": "hurl-twins", "scenarios": [TITLE_A], "status": "absent",
                 "passed": None, "reason": "hurl-twins gate not registered in qa/gates/registry.yaml"}
        out = _guard({"decision": "approve", "issues": [], "rationale": "lgtm"}, twins, tmp_path)
        assert out["decision"] == "approve"

    def test_ran_and_passed_is_noop(self, tmp_path: Path) -> None:
        twins = {**_ran_failed(), "passed": True, "exit_code": 0, "assertions_failed": []}
        out = _guard({"decision": "approve", "issues": [], "rationale": "lgtm"}, twins, tmp_path)
        assert out["decision"] == "approve"

    def test_none_field_is_noop(self, tmp_path: Path) -> None:
        out = _guard({"decision": "approve", "issues": [], "rationale": "lgtm"}, None, tmp_path)
        assert out["decision"] == "approve"

    def test_none_bundle_is_noop(self, tmp_path: Path) -> None:
        inv = AgentInvoker.__new__(AgentInvoker)
        decision = {"decision": "approve", "issues": [], "rationale": "lgtm"}
        inv._apply_hurl_twins_guard(
            decision=decision, evidence_bundle=None, task_id="T", turn=1,
            coach_output_path=tmp_path / "c.json",
        )
        assert decision["decision"] == "approve"

    def test_feedback_verdict_untouched(self, tmp_path: Path) -> None:
        decision = {"decision": "feedback", "issues": [{"x": 1}], "rationale": "already"}
        out = _guard(decision, _ran_failed(), tmp_path)
        assert out == {"decision": "feedback", "issues": [{"x": 1}], "rationale": "already"}

    def test_end_to_end_gather_then_guard(self, tmp_path: Path, monkeypatch, live_target: str) -> None:
        """Real gate script, real listener, real registry: leg -> bundle -> guard."""
        monkeypatch.setenv(ENV_NAME, live_target)
        _write_registry(tmp_path, gate_ids=["hurl-twins"])
        _write_gate_script(tmp_path, failing=True)
        twins = _validator(tmp_path, [TITLE_A])._produce_hurl_twins()
        out = _guard({"decision": "approve", "issues": [], "rationale": "lgtm"}, twins, tmp_path)
        assert out["decision"] == "feedback"
        assert out["issues"][0]["category"] == "hurl_twins_failure"


# ---------------------------------------------------------------------------
# 3. The threading seams — feature -> AutoBuildOrchestrator -> CoachValidator
# ---------------------------------------------------------------------------


class TestThreading:
    def test_hurl_scenarios_for_picks_only_hurl_stamps(self, tmp_path: Path) -> None:
        fdir = tmp_path / ".guardkit" / "features"
        fdir.mkdir(parents=True)
        (fdir / "FEAT-HD01.yaml").write_text(
            yaml.dump(
                {
                    "id": "FEAT-HD01",
                    "name": "hurl dispatch",
                    "tasks": [],
                    "scenarios": {
                        TITLE_A: {"verifier": "hurl"},
                        TITLE_B: {"verifier": "toolchain", "test_ref": "test_rate_limiter"},
                        "Operator checks the dashboard": "operator",
                        "Second wire scenario": "hurl",
                    },
                },
                sort_keys=False,
            )
        )
        feature = FeatureLoader.load_feature("FEAT-HD01", repo_root=tmp_path)
        assert isinstance(feature, Feature)
        assert isinstance(feature.scenarios[TITLE_A], ScenarioStamp)
        assert FeatureOrchestrator._hurl_scenarios_for(feature) == [
            TITLE_A,
            "Second wire scenario",
        ]

    def test_hurl_scenarios_for_unstamped_feature_is_empty(self) -> None:
        assert FeatureOrchestrator._hurl_scenarios_for(SimpleNamespace()) == []
        assert FeatureOrchestrator._hurl_scenarios_for(SimpleNamespace(scenarios={})) == []
        assert FeatureOrchestrator._hurl_scenarios_for(
            SimpleNamespace(scenarios={TITLE_B: ScenarioStamp(verifier="toolchain")})
        ) == []

    def test_autobuild_orchestrator_stores_and_defaults(self, tmp_path: Path) -> None:
        wm = MagicMock()
        wm.worktrees_dir = tmp_path / "worktrees"
        orch = AutoBuildOrchestrator(
            repo_root=tmp_path, worktree_manager=wm, hurl_scenarios=[TITLE_A]
        )
        assert orch._hurl_scenarios == [TITLE_A]
        assert (
            AutoBuildOrchestrator(repo_root=tmp_path, worktree_manager=wm)._hurl_scenarios
            == []
        )

    def test_coach_validator_receives_the_titles(self, tmp_path: Path) -> None:
        v = CoachValidator(str(tmp_path), task_id="TASK-HD-001", hurl_scenarios=[TITLE_A, TITLE_B])
        assert v.hurl_scenarios == [TITLE_A, TITLE_B]
