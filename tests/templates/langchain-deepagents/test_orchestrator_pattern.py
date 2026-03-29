"""Tests for the orchestrator-gated writes scaffold pattern.

Validates the OrchestratorWriteGate class, CoachVerdict parsing,
tool separation enforcement, and the full Player->Coach->Write flow.

Coverage Target: >=85%
Test Count: 20+ tests
"""

from __future__ import annotations

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Import the template module (it's a .template file but pure Python)
# ---------------------------------------------------------------------------
_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "templates"
    / "langchain-deepagents"
    / "templates"
    / "other"
    / "scaffold"
    / "orchestrator_pattern.py.template"
)


@pytest.fixture(scope="module")
def orch_mod():
    """Load the orchestrator pattern module from the .template file."""
    import sys

    loader = SourceFileLoader("orchestrator_pattern", str(_TEMPLATE_PATH))
    spec = importlib.util.spec_from_loader("orchestrator_pattern", loader)
    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules so @dataclass can resolve the module namespace
    sys.modules["orchestrator_pattern"] = mod
    loader.exec_module(mod)
    return mod


@pytest.fixture
def CoachVerdict(orch_mod):
    return orch_mod.CoachVerdict


@pytest.fixture
def OrchestratorWriteGate(orch_mod):
    return orch_mod.OrchestratorWriteGate


@pytest.fixture
def WriteResult(orch_mod):
    return orch_mod.WriteResult


@pytest.fixture
def validate_player_tools(orch_mod):
    return orch_mod.validate_player_tools


@pytest.fixture
def acceptance_verdict(CoachVerdict):
    return CoachVerdict(
        decision="accept",
        score=5,
        issues=[],
        criteria_met=True,
        quality_assessment="high",
    )


@pytest.fixture
def rejection_verdict(CoachVerdict):
    return CoachVerdict(
        decision="reject",
        score=2,
        issues=["Missing citations", "Incorrect facts"],
        criteria_met=False,
        quality_assessment="needs_revision",
    )


@pytest.fixture
def mock_write_fn():
    """Mock write function that simulates write_output."""
    fn = MagicMock(return_value="written to output/results.jsonl")
    fn.__name__ = "write_output"
    return fn


@pytest.fixture
def gate(OrchestratorWriteGate, mock_write_fn):
    """Create a write gate with a mock write function."""
    return OrchestratorWriteGate(write_fn=mock_write_fn, max_retries=3)


# ===================================================================
# CoachVerdict Tests
# ===================================================================


class TestCoachVerdict:
    """Tests for CoachVerdict dataclass and parsing."""

    def test_accepted_property_true(self, CoachVerdict):
        verdict = CoachVerdict(decision="accept", score=5)
        assert verdict.accepted is True

    def test_accepted_property_false(self, CoachVerdict):
        verdict = CoachVerdict(decision="reject", score=2)
        assert verdict.accepted is False

    def test_from_json_accept(self, CoachVerdict):
        raw = json.dumps({
            "decision": "accept",
            "score": 5,
            "issues": [],
            "criteria_met": True,
            "quality_assessment": "high",
        })
        verdict = CoachVerdict.from_json(raw)
        assert verdict.accepted is True
        assert verdict.score == 5
        assert verdict.issues == []
        assert verdict.criteria_met is True

    def test_from_json_reject(self, CoachVerdict):
        raw = json.dumps({
            "decision": "reject",
            "score": 2,
            "issues": ["Bad quality"],
            "criteria_met": False,
            "quality_assessment": "needs_revision",
        })
        verdict = CoachVerdict.from_json(raw)
        assert verdict.accepted is False
        assert verdict.score == 2
        assert verdict.issues == ["Bad quality"]

    def test_from_json_invalid_json(self, CoachVerdict):
        with pytest.raises(ValueError, match="not valid JSON"):
            CoachVerdict.from_json("not json at all")

    def test_from_json_missing_required_fields(self, CoachVerdict):
        raw = json.dumps({"score": 5})  # missing 'decision'
        with pytest.raises(ValueError, match="missing required fields"):
            CoachVerdict.from_json(raw)

    def test_from_json_missing_score(self, CoachVerdict):
        raw = json.dumps({"decision": "accept"})  # missing 'score'
        with pytest.raises(ValueError, match="missing required fields"):
            CoachVerdict.from_json(raw)

    def test_from_json_optional_fields_default(self, CoachVerdict):
        raw = json.dumps({"decision": "accept", "score": 4})
        verdict = CoachVerdict.from_json(raw)
        assert verdict.issues == []
        assert verdict.criteria_met is False
        assert verdict.quality_assessment == "needs_revision"

    def test_default_values(self, CoachVerdict):
        verdict = CoachVerdict(decision="reject", score=1)
        assert verdict.issues == []
        assert verdict.criteria_met is False
        assert verdict.quality_assessment == "needs_revision"


# ===================================================================
# OrchestratorWriteGate — Acceptance Tests
# ===================================================================


class TestWriteGateAcceptance:
    """Tests for write gate on Coach acceptance."""

    def test_attempt_write_on_acceptance(self, gate, mock_write_fn, acceptance_verdict):
        content = json.dumps({"content": "Hello world"})
        result = gate.attempt_write(content, "output/results.jsonl", acceptance_verdict)

        assert result.success is True
        assert result.attempts == 1
        mock_write_fn.assert_called_once_with(content, "output/results.jsonl")

    def test_on_acceptance_returns_content(self, gate, acceptance_verdict):
        content = json.dumps({"content": "test"})
        result = gate.on_acceptance(acceptance_verdict, content)
        assert result == content

    def test_on_acceptance_rejects_non_accept(self, gate, rejection_verdict):
        with pytest.raises(ValueError, match="rejection verdict"):
            gate.on_acceptance(rejection_verdict, '{"content": "test"}')

    def test_on_acceptance_validates_json(self, gate, acceptance_verdict):
        with pytest.raises(ValueError, match="not valid JSON"):
            gate.on_acceptance(acceptance_verdict, "not json")


# ===================================================================
# OrchestratorWriteGate — Rejection Tests
# ===================================================================


class TestWriteGateRejection:
    """Tests for write gate on Coach rejection."""

    def test_attempt_write_on_rejection(self, gate, mock_write_fn, rejection_verdict):
        content = json.dumps({"content": "bad"})
        result = gate.attempt_write(content, "output/results.jsonl", rejection_verdict)

        assert result.success is False
        assert "Coach rejected" in result.error
        mock_write_fn.assert_not_called()

    def test_on_rejection_returns_issues(self, gate, rejection_verdict):
        issues = gate.on_rejection(rejection_verdict, '{"content": "bad"}')
        assert issues == ["Missing citations", "Incorrect facts"]

    def test_rejection_callback_invoked(self, OrchestratorWriteGate, rejection_verdict):
        callback = MagicMock()
        write_fn = MagicMock()
        g = OrchestratorWriteGate(write_fn=write_fn, on_rejection=callback)

        g.attempt_write('{"x": 1}', "output/test.jsonl", rejection_verdict)

        callback.assert_called_once_with(rejection_verdict, '{"x": 1}')


# ===================================================================
# OrchestratorWriteGate — Exhaustion Tests
# ===================================================================


class TestWriteGateExhaustion:
    """Tests for write gate retry exhaustion."""

    def test_attempt_write_exhaustion(self, gate, mock_write_fn, rejection_verdict):
        result = gate.attempt_write(
            '{"x": 1}', "output/test.jsonl", rejection_verdict, attempt=4
        )

        assert result.success is False
        assert "Retry exhaustion" in result.error
        assert result.attempts == 3
        mock_write_fn.assert_not_called()

    def test_on_exhaustion_method(self, gate):
        result = gate.on_exhaustion("output/test.jsonl", 3)

        assert result.success is False
        assert result.target == "output/test.jsonl"
        assert result.attempts == 3
        assert "Exhausted 3/3" in result.error

    def test_exhaustion_callback_invoked(self, OrchestratorWriteGate, rejection_verdict):
        callback = MagicMock()
        write_fn = MagicMock()
        g = OrchestratorWriteGate(write_fn=write_fn, max_retries=2, on_exhaustion=callback)

        g.attempt_write('{"x": 1}', "output/test.jsonl", rejection_verdict, attempt=3)

        callback.assert_called_once_with("output/test.jsonl", 2)

    def test_no_infinite_loop(self, OrchestratorWriteGate):
        """Verify retry cap prevents infinite loops (TRF-006)."""
        write_fn = MagicMock()
        g = OrchestratorWriteGate(write_fn=write_fn, max_retries=1)

        reject = MagicMock()
        reject.accepted = False
        reject.issues = ["bad"]

        # Attempt 1: rejected
        r1 = g.attempt_write('{"x":1}', "output/t.jsonl", reject, attempt=1)
        assert r1.success is False

        # Attempt 2: exhausted (max_retries=1)
        r2 = g.attempt_write('{"x":1}', "output/t.jsonl", reject, attempt=2)
        assert r2.success is False
        assert "Retry exhaustion" in r2.error

        # write_fn never called
        write_fn.assert_not_called()


# ===================================================================
# OrchestratorWriteGate — Configuration Tests
# ===================================================================


class TestWriteGateConfiguration:
    """Tests for write gate configuration."""

    def test_custom_max_retries(self, OrchestratorWriteGate):
        write_fn = MagicMock()
        g = OrchestratorWriteGate(write_fn=write_fn, max_retries=5)
        assert g.max_retries == 5

    def test_invalid_max_retries(self, OrchestratorWriteGate):
        with pytest.raises(ValueError, match="max_retries must be >= 1"):
            OrchestratorWriteGate(write_fn=MagicMock(), max_retries=0)

    def test_write_fn_error_handling(self, OrchestratorWriteGate, acceptance_verdict):
        write_fn = MagicMock(return_value="error: disk full")
        g = OrchestratorWriteGate(write_fn=write_fn)

        result = g.attempt_write(
            '{"x":1}', "output/test.jsonl", acceptance_verdict
        )
        assert result.success is False
        assert "error: disk full" in result.error


# ===================================================================
# Tool Separation Enforcement Tests
# ===================================================================


class TestToolSeparation:
    """Tests for factory-level tool separation enforcement."""

    def test_validate_player_tools_passes_without_write(self, validate_player_tools):
        """Player with domain-only tools should pass validation."""
        mock_search = MagicMock()
        mock_search.name = "search_data"
        validate_player_tools([mock_search])

    def test_validate_player_tools_fails_with_write(self, validate_player_tools):
        """Player with write_output should fail validation."""
        mock_write = MagicMock()
        mock_write.name = "write_output"
        mock_search = MagicMock()
        mock_search.name = "search_data"

        with pytest.raises(AssertionError, match="TOOL SEPARATION VIOLATION"):
            validate_player_tools([mock_search, mock_write])

    def test_validate_player_tools_empty_list(self, validate_player_tools):
        """Empty tool list should pass (no write_output)."""
        validate_player_tools([])

    def test_validate_player_tools_multiple_domain_tools(self, validate_player_tools):
        """Multiple domain tools without write should pass."""
        tools = []
        for name in ["search_data", "rag_retrieval", "fetch_context"]:
            t = MagicMock()
            t.name = name
            tools.append(t)
        validate_player_tools(tools)


# ===================================================================
# Integration Test — Full Player -> Coach -> Write Flow
# ===================================================================


class TestIntegrationFlow:
    """Integration test: full adversarial cooperation write flow."""

    def test_full_accept_flow(self, OrchestratorWriteGate, CoachVerdict):
        """Simulate: Player generates → Coach accepts → Orchestrator writes."""
        written_items = []

        def mock_write(content: str, path: str) -> str:
            written_items.append((content, path))
            return f"written to {path}"

        gate = OrchestratorWriteGate(write_fn=mock_write, max_retries=3)

        # Player generates content
        player_output = json.dumps({"content": "High-quality content"})

        # Coach evaluates and accepts
        coach_response = json.dumps({
            "decision": "accept",
            "score": 5,
            "issues": [],
            "criteria_met": True,
            "quality_assessment": "high",
        })
        verdict = CoachVerdict.from_json(coach_response)

        # Orchestrator validates acceptance
        validated = gate.on_acceptance(verdict, player_output)

        # Orchestrator writes (only after acceptance)
        result = gate.attempt_write(validated, "output/results.jsonl", verdict)

        assert result.success is True
        assert result.attempts == 1
        assert len(written_items) == 1
        assert written_items[0] == (player_output, "output/results.jsonl")

    def test_reject_then_accept_flow(self, OrchestratorWriteGate, CoachVerdict):
        """Simulate: Player generates → Coach rejects → Player revises → Coach accepts → Write."""
        written_items = []

        def mock_write(content: str, path: str) -> str:
            written_items.append((content, path))
            return f"written to {path}"

        gate = OrchestratorWriteGate(write_fn=mock_write, max_retries=3)

        # Attempt 1: Player generates, Coach rejects
        player_v1 = json.dumps({"content": "Draft content"})
        reject_verdict = CoachVerdict(
            decision="reject",
            score=2,
            issues=["Missing sources"],
            criteria_met=False,
            quality_assessment="needs_revision",
        )

        r1 = gate.attempt_write(player_v1, "output/results.jsonl", reject_verdict, attempt=1)
        assert r1.success is False
        assert len(written_items) == 0

        # Get revision feedback
        issues = gate.on_rejection(reject_verdict, player_v1)
        assert "Missing sources" in issues

        # Attempt 2: Player revises, Coach accepts
        player_v2 = json.dumps({"content": "Revised content with sources"})
        accept_verdict = CoachVerdict(
            decision="accept",
            score=4,
            issues=[],
            criteria_met=True,
            quality_assessment="adequate",
        )

        validated = gate.on_acceptance(accept_verdict, player_v2)
        r2 = gate.attempt_write(validated, "output/results.jsonl", accept_verdict, attempt=2)

        assert r2.success is True
        assert r2.attempts == 2
        assert len(written_items) == 1
        assert json.loads(written_items[0][0])["content"] == "Revised content with sources"

    def test_full_exhaustion_flow(self, OrchestratorWriteGate, CoachVerdict):
        """Simulate: Player fails all retries → exhaustion → no write."""
        written_items = []
        exhaustion_events = []

        def mock_write(content: str, path: str) -> str:
            written_items.append((content, path))
            return f"written to {path}"

        def on_exhaust(target: str, attempts: int):
            exhaustion_events.append((target, attempts))

        gate = OrchestratorWriteGate(
            write_fn=mock_write, max_retries=2, on_exhaustion=on_exhaust
        )

        reject = CoachVerdict(
            decision="reject", score=1, issues=["Terrible"],
            criteria_met=False, quality_assessment="needs_revision",
        )

        # Attempt 1: rejected
        r1 = gate.attempt_write('{"x":1}', "output/t.jsonl", reject, attempt=1)
        assert r1.success is False

        # Attempt 2: rejected again
        r2 = gate.attempt_write('{"x":2}', "output/t.jsonl", reject, attempt=2)
        assert r2.success is False

        # Attempt 3: exhaustion (max_retries=2)
        r3 = gate.attempt_write('{"x":3}', "output/t.jsonl", reject, attempt=3)
        assert r3.success is False
        assert "Retry exhaustion" in r3.error

        # Verify: nothing written, exhaustion callback fired
        assert len(written_items) == 0
        assert len(exhaustion_events) == 1
        assert exhaustion_events[0] == ("output/t.jsonl", 2)
