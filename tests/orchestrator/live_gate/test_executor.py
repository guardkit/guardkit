"""F4 gate-script contract execution (WS2 B3).

Covers both realities the executor bridges: structured JSON-envelope gates and
legacy exit-code-only gates, plus the absence-of-failure defense (a non-zero
exit can never be read green). The seam fake is signature-binding (LPA-13).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import pytest

from guardkit.orchestrator.live_gate.errors import LiveGateError
from guardkit.orchestrator.live_gate.executor import (
    GateRun,
    GateScriptRunner,
    execute_gate,
    gate_failed,
    parse_gate_result,
)
from guardkit.qa.formats.gate_registry import GateEntry, GateTarget


class FakeGateScriptRunner(GateScriptRunner):
    """Signature-binding fake: implements the exact GateScriptRunner.run
    signature but returns a canned GateRun (no subprocess)."""

    def __init__(self, run_result: GateRun):
        self._result = run_result
        self.calls: list[tuple] = []

    def run(
        self,
        script_path: Path,
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout_s: float,
    ) -> GateRun:
        self.calls.append((script_path, cwd, dict(env), timeout_s))
        return self._result


def _gate(gid="g1", path="qa/gates/g1.py") -> GateEntry:
    return GateEntry(
        id=gid,
        path=path,
        target=GateTarget(base_url_env="BASE_URL", environment_id="env"),
        pass_bar_ref="qa/pass-bar-X.yaml",
        evidence_dir_pattern="qa/gates/evidence-{date}/shots-g1",
    )


class TestParseStructured:
    def test_structured_pass(self):
        stdout = json.dumps(
            {"assertions": [{"id": "a1", "status": "pass", "observed": "o", "expected": "o"}]}
        )
        gr = parse_gate_result("g1", GateRun(0, stdout, ""))
        assert gr.exit_code == 0
        assert [a.status for a in gr.assertions] == ["pass"]
        assert not gate_failed(gr)

    def test_structured_fail_enumerated(self):
        stdout = json.dumps(
            {"assertions": [
                {"id": "a1", "status": "pass"},
                {"id": "a2", "status": "fail", "observed": "x", "expected": "y"},
            ]}
        )
        gr = parse_gate_result("g1", GateRun(1, stdout, ""))
        assert gate_failed(gr)
        assert {a.id: a.status for a in gr.assertions} == {"a1": "pass", "a2": "fail"}

    def test_json_after_human_text_is_found(self):
        stdout = "running gate...\nall good\n" + json.dumps({"assertions": [{"id": "a", "status": "pass"}]})
        gr = parse_gate_result("g1", GateRun(0, stdout, ""))
        assert [a.id for a in gr.assertions] == ["a"]

    def test_invalid_assertion_raises_loudly(self):
        stdout = json.dumps({"assertions": [{"id": "a", "status": "bogus"}]})
        with pytest.raises(LiveGateError, match="invalid assertion"):
            parse_gate_result("g1", GateRun(0, stdout, ""))


class TestParseLegacy:
    def test_legacy_pass_exit_zero(self):
        gr = parse_gate_result("g6", GateRun(0, "GATE PASSED: no leakage", ""))
        assert gr.exit_code == 0
        assert len(gr.assertions) == 1
        assert gr.assertions[0].id == "g6::exit"
        assert gr.assertions[0].status == "pass"
        assert not gate_failed(gr)

    def test_legacy_fail_exit_nonzero_carries_output_tail(self):
        gr = parse_gate_result("g6", GateRun(1, "GATE FAILED:\n  - mock identity", "boom"))
        assert gate_failed(gr)
        a = gr.assertions[0]
        assert a.status == "fail"
        assert "exit_code=1" in a.observed
        assert "boom" in a.observed  # stderr tail included


class TestAbsenceOfFailureDefense:
    def test_nonzero_exit_with_all_pass_assertions_is_forced_fail(self):
        # A contract-violating gate: exits 1 but enumerates only passes. The
        # exit code must win — a non-zero exit can never be read green.
        stdout = json.dumps({"assertions": [{"id": "a", "status": "pass"}]})
        gr = parse_gate_result("g1", GateRun(1, stdout, ""))
        assert gate_failed(gr)
        assert any(a.id == "g1::exit" and a.status == "fail" for a in gr.assertions)

    def test_timeout_is_failed(self):
        gr = parse_gate_result("g1", GateRun(124, "", "hung", timed_out=True))
        assert gate_failed(gr)
        assert "timed out" in gr.assertions[0].observed


class TestExecuteGate:
    def test_execute_gate_uses_runner_and_resolves_path(self, tmp_path):
        script = tmp_path / "qa" / "gates" / "g1.py"
        script.parent.mkdir(parents=True)
        script.write_text("print('x')")
        fake = FakeGateScriptRunner(GateRun(0, json.dumps({"assertions": [{"id": "a", "status": "pass"}]}), ""))
        gr = execute_gate(_gate(), repo_root=tmp_path, runner=fake, env={"K": "V"}, timeout_s=42)
        assert gr.gate_id == "g1"
        assert fake.calls[0][0] == script.resolve()
        assert fake.calls[0][3] == 42

    def test_missing_script_raises(self, tmp_path):
        fake = FakeGateScriptRunner(GateRun(0, "", ""))
        with pytest.raises(LiveGateError, match="script not found"):
            execute_gate(_gate(), repo_root=tmp_path, runner=fake)


class TestSubprocessRunnerReal:
    def test_real_python_gate_pass(self, tmp_path):
        from guardkit.orchestrator.live_gate.executor import SubprocessGateScriptRunner

        script = tmp_path / "gate.py"
        script.write_text(
            "import json,sys\n"
            "print(json.dumps({'assertions':[{'id':'a','status':'pass'}]}))\n"
            "sys.exit(0)\n"
        )
        run = SubprocessGateScriptRunner().run(script, cwd=tmp_path, env={}, timeout_s=30)
        assert run.exit_code == 0
        gr = parse_gate_result("g", run)
        assert not gate_failed(gr)

    def test_real_python_gate_fail_exit1(self, tmp_path):
        from guardkit.orchestrator.live_gate.executor import SubprocessGateScriptRunner

        script = tmp_path / "gate.py"
        script.write_text("import sys\nprint('GATE FAILED')\nsys.exit(1)\n")
        run = SubprocessGateScriptRunner().run(script, cwd=tmp_path, env={}, timeout_s=30)
        assert run.exit_code == 1
        assert gate_failed(parse_gate_result("g", run))
