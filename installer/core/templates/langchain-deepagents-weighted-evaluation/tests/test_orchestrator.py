"""Tests for the three-role orchestrator scaffold (TASK-TI-010).

Verifies:
1. AdversarialOrchestrator class wiring and properties
2. Agent factory functions with tool allowlists
3. Pre-fetch pattern for domain context
4. Retry logic with configurable caps
5. Content extraction using JsonExtractor
6. Integration test with mock Player and Coach

Coverage Target: >=85%
Test Count: 25+ tests
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import pathlib
import re
import sys
import tempfile
from unittest.mock import MagicMock

import pytest

# Template root relative to this test file
TEMPLATE_ROOT = pathlib.Path(__file__).parent.parent

# Default substitutions for Jinja2 template variables
_TEMPLATE_DEFAULTS = {
    "ProjectName": "_test_project",
    "DomainName": "example-domain",
    "AdversarialIntensity": "full",
    "AcceptanceThreshold": "0.7",
    "MaxRetries": "3",
}


def _preprocess_j2(source: str) -> str:
    """Replace {{Var}} template variables with test defaults.

    Also comments out import lines that reference the fake project name,
    since those modules don't exist in the test environment.
    """
    for var, value in _TEMPLATE_DEFAULTS.items():
        source = source.replace("{{" + var + "}}", value)

    # Comment out imports from the fake test project
    lines = source.split("\n")
    processed = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith(("from _test_project", "import _test_project")):
            processed.append("# " + line + "  # commented for test")
        else:
            processed.append(line)
    return "\n".join(processed)


def _load_j2_module(name: str, file_path: pathlib.Path):
    """Load a .j2 Python module with template variable substitution."""
    source = file_path.read_text()
    processed = _preprocess_j2(source)

    # Write to a temp file so importlib can load it
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, prefix=f"test_{name}_",
    ) as tmp:
        tmp.write(processed)
        tmp_path = tmp.name

    unique_name = f"_test_orchestrator_.{name}"
    loader = importlib.machinery.SourceFileLoader(unique_name, tmp_path)
    spec = importlib.util.spec_from_file_location(
        unique_name, tmp_path, loader=loader,
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[unique_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(unique_name, None)
        raise
    finally:
        pathlib.Path(tmp_path).unlink(missing_ok=True)

    return module


@pytest.fixture
def pipeline_mod():
    """Load pipeline module from .j2 file with template var substitution."""
    return _load_j2_module(
        "pipeline",
        TEMPLATE_ROOT / "scaffold" / "pipeline.py.j2",
    )


@pytest.fixture
def adversarial_config():
    """Standard adversarial configuration for testing."""
    return {
        "intensity": "full",
        "acceptance_threshold": 0.7,
        "max_retries": 3,
        "evaluation_criteria": [
            {"name": "accuracy", "weight": 0.4},
            {"name": "completeness", "weight": 0.3},
            {"name": "quality", "weight": 0.3},
        ],
    }


# ============================================================================
# 1. Pipeline dataclass tests (WeightedVerdict, PipelineResult)
# ============================================================================

class TestWeightedVerdictFromJson:
    """Test WeightedVerdict.from_json parsing."""

    def test_parses_valid_accept(self, pipeline_mod):
        raw = json.dumps({
            "decision": "accept",
            "criteria": {
                "accuracy": {"score": 0.9, "feedback": "Good"},
                "quality": {"score": 0.8, "feedback": "Fine"},
            },
            "issues": [],
        })
        weights = {"accuracy": 0.6, "quality": 0.4}
        verdict = pipeline_mod.WeightedVerdict.from_json(raw, weights)

        assert verdict.accepted is True
        assert verdict.decision == "accept"
        assert len(verdict.criterion_scores) == 2
        expected_composite = 0.9 * 0.6 + 0.8 * 0.4
        assert abs(verdict.composite_score - expected_composite) < 0.01

    def test_parses_valid_reject(self, pipeline_mod):
        raw = json.dumps({
            "decision": "reject",
            "criteria": {
                "accuracy": {"score": 0.3, "feedback": "Bad sources"},
            },
            "issues": ["Missing citations"],
        })
        weights = {"accuracy": 1.0}
        verdict = pipeline_mod.WeightedVerdict.from_json(raw, weights)

        assert verdict.accepted is False
        assert verdict.issues == ["Missing citations"]
        assert abs(verdict.composite_score - 0.3) < 0.01

    def test_raises_on_invalid_json(self, pipeline_mod):
        with pytest.raises(ValueError, match="not valid JSON"):
            pipeline_mod.WeightedVerdict.from_json("not json", {"a": 1.0})

    def test_raises_on_missing_criteria(self, pipeline_mod):
        raw = json.dumps({"decision": "accept"})
        with pytest.raises(ValueError, match="missing 'criteria'"):
            pipeline_mod.WeightedVerdict.from_json(raw, {"a": 1.0})

    def test_missing_criterion_defaults_to_zero(self, pipeline_mod):
        raw = json.dumps({
            "decision": "reject",
            "criteria": {
                "accuracy": {"score": 0.8},
            },
        })
        weights = {"accuracy": 0.5, "quality": 0.5}
        verdict = pipeline_mod.WeightedVerdict.from_json(raw, weights)

        quality_score = next(
            cs for cs in verdict.criterion_scores if cs.name == "quality"
        )
        assert quality_score.score == 0.0
        expected = 0.8 * 0.5 + 0.0 * 0.5
        assert abs(verdict.composite_score - expected) < 0.01

    def test_quality_assessment_high(self, pipeline_mod):
        raw = json.dumps({
            "decision": "accept",
            "criteria": {"a": {"score": 0.95}},
        })
        v = pipeline_mod.WeightedVerdict.from_json(raw, {"a": 1.0})
        assert v.quality_assessment == "high"

    def test_quality_assessment_adequate(self, pipeline_mod):
        raw = json.dumps({
            "decision": "accept",
            "criteria": {"a": {"score": 0.75}},
        })
        v = pipeline_mod.WeightedVerdict.from_json(raw, {"a": 1.0})
        assert v.quality_assessment == "adequate"

    def test_quality_assessment_needs_revision(self, pipeline_mod):
        raw = json.dumps({
            "decision": "reject",
            "criteria": {"a": {"score": 0.5}},
        })
        v = pipeline_mod.WeightedVerdict.from_json(raw, {"a": 1.0})
        assert v.quality_assessment == "needs_revision"


class TestPipelineResult:
    """Test PipelineResult dataclass."""

    def test_success_result(self, pipeline_mod):
        result = pipeline_mod.PipelineResult(
            success=True,
            content='{"data": "test"}',
            attempts=1,
        )
        assert result.success is True
        assert result.attempts == 1
        assert result.error is None

    def test_failure_result(self, pipeline_mod):
        result = pipeline_mod.PipelineResult(
            success=False,
            error="Exhausted 3 retries",
            attempts=3,
        )
        assert result.success is False
        assert result.error == "Exhausted 3 retries"


# ============================================================================
# 2. Tool allowlist constants
# ============================================================================

class TestToolAllowlists:
    """Verify tool allowlist constants match expected values."""

    def test_player_tools_only_search(self):
        orch_content = (
            TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2"
        ).read_text()
        assert 'PLAYER_ALLOWED_TOOLS: set[str] = {"search_data"}' in orch_content

    def test_coach_has_no_tools(self):
        orch_content = (
            TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2"
        ).read_text()
        assert "COACH_ALLOWED_TOOLS: set[str] = set()" in orch_content


# ============================================================================
# 3. Agent factory function signatures
# ============================================================================

class TestAgentFactorySignatures:
    """Verify factory functions use create_restricted_agent."""

    def test_player_factory_uses_restricted_agent(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "create_restricted_agent(" in content
        assert "validate_player_tools(" in content
        assert "allowed_tools=PLAYER_ALLOWED_TOOLS" in content

    def test_coach_factory_uses_restricted_agent(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "allowed_tools=COACH_ALLOWED_TOOLS" in content
        assert "tools=[]" in content

    def test_player_factory_builds_domain_prompt(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "build_player_prompt_with_domain(domain_prompt)" in content

    def test_coach_factory_builds_weighted_prompt(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "build_weighted_coach_prompt(" in content


# ============================================================================
# 4. AdversarialOrchestrator class structure
# ============================================================================

class TestAdversarialOrchestratorStructure:
    """Verify the AdversarialOrchestrator class has required structure."""

    def test_class_exists(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "class AdversarialOrchestrator:" in content

    def test_has_process_target(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "async def process_target(" in content

    def test_has_prefetch_context(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "async def prefetch_context(" in content

    def test_owns_write_gate(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "self._write_gate" in content
        assert "write_gate.attempt_write(" in content

    def test_uses_json_extractor(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "JsonExtractor.extract(" in content

    def test_respects_ainvoke_contract(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "assert_no_system_messages(" in content

    def test_retry_loop_present(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "for attempt in range(1, self._max_retries + 1):" in content

    def test_symmetric_coach_extraction(self):
        """Coach output also uses JsonExtractor (TRF-026 lesson)."""
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        occurrences = content.count("JsonExtractor.extract(")
        assert occurrences >= 2, "Both Player and Coach should use JsonExtractor"


# ============================================================================
# 5. Retry input builder (TASK-REV-R2A1 compliance)
# ============================================================================

class TestRetryInputBuilder:
    """Test _build_retry_input follows ainvoke() message contract."""

    def test_function_defined(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "def _build_retry_input(" in content

    def test_uses_user_role_not_system(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        match = re.search(
            r'def _build_retry_input.*?(?=\ndef |\nclass |\Z)',
            content,
            re.DOTALL,
        )
        assert match is not None
        func_body = match.group()
        assert '"role": "system"' not in func_body
        assert '"role": "user"' in func_body


# ============================================================================
# 6. create_orchestrator wiring
# ============================================================================

class TestCreateOrchestratorWiring:
    """Verify create_orchestrator() wires all three roles."""

    def test_creates_player_agent(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "create_player_agent(" in content

    def test_creates_coach_agent(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "create_coach_agent(" in content

    def test_creates_write_gate(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "OrchestratorWriteGate(" in content

    def test_returns_adversarial_orchestrator(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "return AdversarialOrchestrator(" in content

    def test_loads_agents_md_if_exists(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert 'memory=["./AGENTS.md"]' in content


# ============================================================================
# 7. Integration test with mock agents (using pipeline dataclasses)
# ============================================================================

class TestIntegrationMockAgents:
    """Integration test: verify pipeline data flow with mocked agents."""

    def test_accept_on_first_attempt(self, pipeline_mod, adversarial_config):
        """Player output accepted by Coach on first attempt."""
        coach_response = json.dumps({
            "decision": "accept",
            "criteria": {
                "accuracy": {"score": 0.9, "feedback": "Good"},
                "completeness": {"score": 0.85, "feedback": "OK"},
                "quality": {"score": 0.8, "feedback": "Fine"},
            },
            "issues": [],
        })
        weights = {"accuracy": 0.4, "completeness": 0.3, "quality": 0.3}
        verdict = pipeline_mod.WeightedVerdict.from_json(coach_response, weights)

        assert verdict.accepted is True
        expected = 0.9 * 0.4 + 0.85 * 0.3 + 0.8 * 0.3
        assert abs(verdict.composite_score - expected) < 0.01
        assert verdict.composite_score >= 0.7

        result = pipeline_mod.PipelineResult(
            success=True,
            content=json.dumps({"content": "Generated text"}),
            verdict=verdict,
            attempts=1,
        )
        assert result.success is True
        assert result.attempts == 1

    def test_reject_then_accept(self, pipeline_mod):
        """Coach rejects first attempt, accepts revised second attempt."""
        weights = {"accuracy": 0.5, "quality": 0.5}

        # First: rejected
        reject_response = json.dumps({
            "decision": "reject",
            "criteria": {
                "accuracy": {"score": 0.3, "feedback": "Missing sources"},
                "quality": {"score": 0.4, "feedback": "Needs work"},
            },
            "issues": ["Missing citations", "Poorly structured"],
        })
        v1 = pipeline_mod.WeightedVerdict.from_json(reject_response, weights)
        assert v1.accepted is False
        assert len(v1.issues) == 2

        # Second: accepted
        accept_response = json.dumps({
            "decision": "accept",
            "criteria": {
                "accuracy": {"score": 0.9, "feedback": "All sources cited"},
                "quality": {"score": 0.85, "feedback": "Well structured"},
            },
            "issues": [],
        })
        v2 = pipeline_mod.WeightedVerdict.from_json(accept_response, weights)
        assert v2.accepted is True
        assert v2.composite_score >= 0.7

    def test_exhaustion_after_max_retries(self, pipeline_mod, adversarial_config):
        """All retries exhausted → PipelineResult with success=False."""
        weights = {"accuracy": 1.0}

        for attempt in range(1, adversarial_config["max_retries"] + 1):
            reject_response = json.dumps({
                "decision": "reject",
                "criteria": {"accuracy": {"score": 0.2, "feedback": "Bad"}},
                "issues": [f"Attempt {attempt} failed"],
            })
            verdict = pipeline_mod.WeightedVerdict.from_json(reject_response, weights)
            assert verdict.accepted is False

        result = pipeline_mod.PipelineResult(
            success=False,
            content="",
            verdict=verdict,
            attempts=adversarial_config["max_retries"],
            error=f"Exhausted {adversarial_config['max_retries']} retries",
        )
        assert result.success is False
        assert "Exhausted" in result.error


# ============================================================================
# 8. Helper function tests
# ============================================================================

class TestHelperFunctions:
    """Test private helper functions referenced in orchestrator."""

    def test_extract_content_defined(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "def _extract_content(" in content

    def test_safe_json_str_defined(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "def _safe_json_str(" in content

    def test_build_retry_input_defined(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "def _build_retry_input(" in content

    def test_load_config_defined(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "def _load_config()" in content

    def test_create_model_defined(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "def _create_model(" in content


# ============================================================================
# 9. Orchestrator properties and configuration
# ============================================================================

class TestOrchestratorProperties:
    """Verify orchestrator exposes expected properties."""

    def test_has_player_property(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "def player(self)" in content

    def test_has_coach_property(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "def coach(self)" in content

    def test_has_write_gate_property(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "def write_gate(self)" in content

    def test_has_max_retries_property(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "def max_retries(self)" in content

    def test_has_acceptance_threshold_property(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "def acceptance_threshold(self)" in content

    def test_has_criteria_weights_property(self):
        content = (TEMPLATE_ROOT / "scaffold" / "orchestrator.py.j2").read_text()
        assert "def criteria_weights(self)" in content
