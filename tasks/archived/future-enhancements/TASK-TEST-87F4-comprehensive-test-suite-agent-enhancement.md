# TASK-TEST-87F4: Comprehensive Test Suite for Agent Enhancement & Validation

**Task ID**: TASK-TEST-87F4
**Priority**: HIGH
**Complexity**: 8/10 (Complex - expanded scope)
**Estimated Duration**: 4-5 days (increased from 2-3 days)
**Status**: BACKLOG (Ready for Implementation)
**Created**: 2025-11-20
**Updated**: 2025-11-21 (expanded to include validation testing)
**Dependencies**:
- TASK-AI-2B37 (AI Integration - should complete first)
- TASK-PHASE-8-INCREMENTAL (✅ completed)

---

## Overview

Define and implement a comprehensive testing and integration strategy for:
1. **agent-content-enhancer.md enhancement** - GitHub best practices integration
2. **/agent-enhance command** - Single agent enhancement tool
3. **/agent-validate command** - Agent quality validation tool
4. **Agent enhancement workflow** - End-to-end enhancement process

**EXPANDED SCOPE**: This task now covers testing for BOTH enhancement AND validation workflows, providing comprehensive quality assurance for the entire agent ecosystem.

**Scope**:
- Unit test specifications and implementation (30+ tests)
- Integration test scenarios (10+ tests)
- Regression test baselines (15 existing agents)
- Quality validation methodology
- CI/CD integration specifications
- Test fixtures and mock strategies
- Performance benchmarks
- Documentation for testing practices

**Out of Scope**:
- Actual agent enhancement implementation (covered by other tasks)
- Production agent content updates (done separately)
- Template creation testing (separate suite)

---

## Test Strategy Overview

### 1. Test Plan Summary

**Testing Phases**:

| Phase | Duration | Focus | Coverage Target |
|-------|----------|-------|----------------|
| **Week 1: Unit Tests** | 2-3 days | Component-level validation | ≥90% |
| **Week 2: Integration Tests** | 2-3 days | End-to-end workflows | Critical paths 100% |
| **Week 2: Regression Tests** | 1 day | Backward compatibility | Baseline validation |
| **Week 3: Quality Validation** | 1-2 days | Improvement metrics | Before/after comparison |

**Timeline**:
- **Day 1-2**: Unit tests for enhancement (enhancer, parser, applier, prompt builder)
- **Day 3-4**: Unit tests for validation (validator, metrics, scoring, recommendations)
- **Day 5-6**: Integration tests (workflows, batch operations, CI/CD)
- **Day 7**: Regression tests and baseline establishment
- **Day 8-9**: Quality validation and documentation
- **Day 10**: Buffer for bug fixes and refinement

**Resources Needed**:
- Test fixtures: 15 agent files (5 excellent, 5 good, 5 poor)
- Mock AI responses: 10 pre-generated enhancement examples
- Template directories: 3 template sets (react-typescript, fastapi-python, default)
- Test data generator: Script to create synthetic agents
- Coverage tools: pytest-cov, coverage.py, pytest-benchmark

---

## 2. Unit Test Specification

### 2.1 File Structure

```
tests/
├── unit/
│   ├── lib/
│   │   ├── agent_enhancement/
│   │   │   ├── __init__.py
│   │   │   ├── test_enhancer.py              # SingleAgentEnhancer tests (20+ tests)
│   │   │   ├── test_prompt_builder.py        # Prompt generation tests (5 tests)
│   │   │   ├── test_parser.py                # Response parsing tests (5 tests)
│   │   │   ├── test_applier.py               # File modification tests (5 tests)
│   │   │   └── test_validation.py            # Enhancement validation tests (3 tests)
│   │   └── agent_validation/
│   │       ├── __init__.py
│   │       ├── test_validator.py             # AgentValidator tests (15 tests)
│   │       ├── test_metrics.py               # Metric calculation tests (8 tests)
│   │       ├── test_scoring.py               # Scoring algorithm tests (8 tests)
│   │       ├── test_recommendations.py       # Recommendation engine tests (5 tests)
│   │       └── test_boundary_detection.py    # Boundary format detection tests (4 tests)
│   └── commands/
│       ├── test_agent_enhance.py             # /agent-enhance command tests (10 tests)
│       └── test_agent_validate.py            # /agent-validate command tests (10 tests)
├── integration/
│   ├── test_enhancement_workflow.py          # Full enhancement workflow (8 tests)
│   ├── test_validation_workflow.py           # Full validation workflow (6 tests)
│   ├── test_batch_operations.py              # Batch enhance/validate (5 tests)
│   └── test_ci_cd_integration.py             # CI/CD pipeline tests (6 tests)
├── regression/
│   ├── test_existing_agents.py               # Existing 15 agents still work (5 tests)
│   ├── test_backward_compatibility.py        # API compatibility (5 tests)
│   └── test_baseline_scores.py               # Quality score baselines (3 tests)
├── quality/
│   ├── test_improvement_metrics.py           # Before/after comparison (5 tests)
│   └── test_enhancement_quality.py           # Enhanced agent quality (4 tests)
└── fixtures/
    ├── agents/                               # Test agent files
    ├── templates/                            # Test template directories
    ├── responses/                            # Mock AI responses
    └── factories.py                          # Test data factories
```

**Total Test Count**: 135+ tests

### 2.2 Agent Enhancement Tests (38 tests)

**See detailed implementation in Section 2.3 below**

Key test categories:
- **AI Enhancement** (8 tests): Task API integration, timeout handling, error scenarios
- **Retry Logic** (5 tests): Exponential backoff, max attempts, transient vs permanent failures
- **Hybrid Strategy** (5 tests): Fallback behavior, always-succeeds guarantee
- **Validation** (5 tests): Response format, missing keys, partial content
- **Static Strategy** (3 tests): Keyword matching, performance
- **Prompt Building** (5 tests): Template context, edge cases
- **Response Parsing** (5 tests): JSON extraction, error handling
- **File Operations** (5 tests): Apply changes, generate diffs, permissions

### 2.3 Agent Validation Tests (45 tests)

**File**: `tests/unit/lib/agent_validation/test_validator.py`

```python
"""Unit tests for AgentValidator class."""

import pytest
from pathlib import Path
from installer.core.lib.agent_validation.validator import (
    AgentValidator,
    ValidationResult,
    AgentMetrics
)


class TestAgentValidator:
    """Test suite for AgentValidator."""

    @pytest.fixture
    def excellent_agent(self, tmp_path):
        """Create an excellent agent (8-10/10)."""
        agent_file = tmp_path / "excellent-agent.md"
        content = """---
name: excellent-agent
description: High-quality agent
tools: [Read, Write, Edit]
---

# Excellent Agent

## Purpose
Clear, specific purpose with measurable goals.

## When to Use
1. Scenario A with specific conditions
2. Scenario B with use cases
3. Scenario C with examples

## Capabilities
- Capability 1 (detailed)
- Capability 2 (with benefits)
- Capability 3 (with context)

## Boundaries

### ALWAYS
1. Validate all inputs
2. Use type hints
3. Write comprehensive tests
4. Log important operations
5. Handle errors gracefully

### NEVER
1. Hardcode credentials
2. Skip validation
3. Ignore errors
4. Use global state
5. Bypass security

### ASK HUMAN
1. Major architecture changes
2. Breaking API changes
3. Security modifications
4. Performance trade-offs

## Code Examples

### Example 1: Basic Usage
```python
def process(data: List[str]) -> Result:
    if not data:
        return Error("No data")
    return Success(processed)
```

### Example 2: Error Handling
```python
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Failed: {e}")
    return Error(str(e))
```

### Example 3: Integration
```python
service = ServiceClient(config)
result = await service.call()
```

## Best Practices

### DO
- Use dependency injection
- Write self-documenting code
- Test edge cases

### DON'T
- Use magic numbers
- Duplicate code
- Ignore warnings
"""
        agent_file.write_text(content)
        return agent_file

    @pytest.fixture
    def poor_agent(self, tmp_path):
        """Create a poor agent (<6/10)."""
        agent_file = tmp_path / "poor-agent.md"
        content = """---
name: poor-agent
description: Minimal agent
tools: [Read]
---

# Poor Agent

Minimal content.
"""
        agent_file.write_text(content)
        return agent_file

    # ============================================================
    # Example Density Tests (5 tests)
    # ============================================================

    def test_example_density_calculation(self, excellent_agent):
        """Test example density calculation algorithm."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent)

        # Excellent agent should have ≥40% example density
        assert result.metrics.example_density >= 40.0
        assert result.scores.examples >= 8.0

    def test_example_density_low(self, poor_agent):
        """Test example density for low-quality agent."""
        validator = AgentValidator()
        result = validator.validate(poor_agent)

        # Poor agent should have <30% example density
        assert result.metrics.example_density < 30.0
        assert result.scores.examples < 7.0

    def test_time_to_first_example(self, excellent_agent):
        """Test time-to-first-example metric (<50 lines target)."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent)

        # Excellent agent has first example within 50 lines
        assert result.metrics.time_to_first_example < 50

    def test_example_density_edge_case_no_examples(self, poor_agent):
        """Test handling of agents with zero examples."""
        validator = AgentValidator()
        result = validator.validate(poor_agent)

        assert result.metrics.example_density == 0.0
        assert result.scores.examples == 0.0

    def test_example_density_calculation_accuracy(self, excellent_agent):
        """Test accuracy of example density calculation."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent)

        # Manually verify calculation
        content = excellent_agent.read_text()
        code_blocks = content.count("```")
        total_lines = len(content.split("\n"))

        # Should have meaningful code content
        assert code_blocks >= 6  # 3 examples × 2 delimiters

    # ============================================================
    # Boundary Detection Tests (8 tests)
    # ============================================================

    def test_boundary_detection_complete(self, excellent_agent):
        """Test boundary detection for complete ALWAYS/NEVER/ASK sections."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent)

        # Should detect all three boundary sections
        assert result.metrics.boundary_sections["always"] >= 5
        assert result.metrics.boundary_sections["never"] >= 5
        assert result.metrics.boundary_sections["ask"] >= 4

        # Should score well on boundaries
        assert result.scores.boundaries >= 8.0

    def test_boundary_detection_missing(self, poor_agent):
        """Test boundary detection for missing sections."""
        validator = AgentValidator()
        result = validator.validate(poor_agent)

        # Should detect no boundary sections
        assert result.metrics.boundary_sections["always"] == 0
        assert result.metrics.boundary_sections["never"] == 0
        assert result.metrics.boundary_sections["ask"] == 0

        # Should score poorly on boundaries
        assert result.scores.boundaries < 5.0

    def test_boundary_format_always_section(self, excellent_agent):
        """Test ALWAYS section detection and counting."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent)

        # Verify ALWAYS items detected correctly
        assert result.metrics.boundary_sections["always"] == 5

    def test_boundary_format_never_section(self, excellent_agent):
        """Test NEVER section detection and counting."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent)

        # Verify NEVER items detected correctly
        assert result.metrics.boundary_sections["never"] == 5

    def test_boundary_format_ask_section(self, excellent_agent):
        """Test ASK HUMAN section detection and counting."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent)

        # Verify ASK HUMAN items detected correctly
        assert result.metrics.boundary_sections["ask"] == 4

    def test_boundary_partial_sections(self, tmp_path):
        """Test agent with only some boundary sections."""
        agent_file = tmp_path / "partial-boundaries.md"
        content = """---
name: partial
---

## Boundaries

### ALWAYS
1. Do this

### NEVER
1. Don't do this
"""
        agent_file.write_text(content)

        validator = AgentValidator()
        result = validator.validate(agent_file)

        assert result.metrics.boundary_sections["always"] == 1
        assert result.metrics.boundary_sections["never"] == 1
        assert result.metrics.boundary_sections["ask"] == 0

    def test_boundary_scoring_weights(self, tmp_path):
        """Test that all three boundary sections contribute to score."""
        # Agent with only ALWAYS
        agent_always = tmp_path / "always-only.md"
        agent_always.write_text("""---
name: always
---

### ALWAYS
1. Item
""")

        # Agent with all three
        agent_all = tmp_path / "all-boundaries.md"
        agent_all.write_text("""---
name: all
---

### ALWAYS
1. Item

### NEVER
1. Item

### ASK HUMAN
1. Item
""")

        validator = AgentValidator()
        result_always = validator.validate(agent_always)
        result_all = validator.validate(agent_all)

        # All three should score higher than just one
        assert result_all.scores.boundaries > result_always.scores.boundaries

    def test_boundary_case_insensitive_detection(self, tmp_path):
        """Test boundary detection is case-insensitive."""
        agent_file = tmp_path / "case-test.md"
        content = """---
name: case-test
---

### Always
1. Item

### never
1. Item

### Ask Human
1. Item
"""
        agent_file.write_text(content)

        validator = AgentValidator()
        result = validator.validate(agent_file)

        # Should still detect all sections
        assert result.metrics.boundary_sections["always"] == 1
        assert result.metrics.boundary_sections["never"] == 1
        assert result.metrics.boundary_sections["ask"] == 1

    # ============================================================
    # Scoring Algorithm Tests (10 tests)
    # ============================================================

    def test_scoring_excellent_range(self, excellent_agent):
        """Test scoring for excellent agent (8-10/10)."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent)

        assert result.overall_score >= 8.0
        assert result.overall_score <= 10.0
        assert result.status == "excellent"

    def test_scoring_good_range(self, tmp_path):
        """Test scoring for good agent (7-8/10)."""
        # Create good agent (40% density, has boundaries, good structure)
        agent_file = tmp_path / "good-agent.md"
        content = """---
name: good
---

# Good Agent

## Purpose
Clear purpose.

## Boundaries

### ALWAYS
1. Item

### NEVER
1. Item

### ASK HUMAN
1. Item

## Example
```python
code()
```
"""
        agent_file.write_text(content)

        validator = AgentValidator()
        result = validator.validate(agent_file)

        assert 7.0 <= result.overall_score < 8.0
        assert result.status == "good"

    def test_scoring_needs_improvement_range(self, poor_agent):
        """Test scoring for poor agent (<6/10)."""
        validator = AgentValidator()
        result = validator.validate(poor_agent)

        assert result.overall_score < 6.0
        assert result.status == "needs_improvement"

    def test_scoring_breakdown_components(self, excellent_agent):
        """Test detailed score breakdown."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent)

        # Verify all score components exist
        assert hasattr(result.scores, 'examples')
        assert hasattr(result.scores, 'boundaries')
        assert hasattr(result.scores, 'structure')
        assert hasattr(result.scores, 'clarity')

        # Verify scores are in valid range
        assert 0 <= result.scores.examples <= 10
        assert 0 <= result.scores.boundaries <= 10
        assert 0 <= result.scores.structure <= 10
        assert 0 <= result.scores.clarity <= 10

    def test_scoring_weights_balanced(self, excellent_agent):
        """Test that scoring weights are balanced (no single factor dominates)."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent)

        # No single component should be >40% of total
        max_weight = max(
            result.scores.examples,
            result.scores.boundaries,
            result.scores.structure,
            result.scores.clarity
        ) / result.overall_score

        assert max_weight <= 0.4

    def test_scoring_example_density_40_50_target(self, tmp_path):
        """Test that 40-50% example density yields high scores."""
        # Create agent with exactly 45% density (target)
        agent_file = tmp_path / "target-density.md"

        # Calculate content to hit 45% density
        code_lines = 45
        text_lines = 55
        total = code_lines + text_lines

        content = "---\nname: test\n---\n\n"
        content += "Text line\n" * text_lines
        content += "```python\n"
        content += "code()\n" * code_lines
        content += "```\n"

        agent_file.write_text(content)

        validator = AgentValidator()
        result = validator.validate(agent_file)

        # Should score ≥8/10 for examples
        assert result.scores.examples >= 8.0

    def test_scoring_boundary_completeness(self, excellent_agent):
        """Test that complete boundaries (all 3 sections) yield high scores."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent)

        # Complete boundaries should score ≥8/10
        assert result.scores.boundaries >= 8.0

    def test_scoring_edge_case_empty_agent(self, tmp_path):
        """Test scoring of completely empty agent."""
        agent_file = tmp_path / "empty.md"
        agent_file.write_text("---\nname: empty\n---\n")

        validator = AgentValidator()
        result = validator.validate(agent_file)

        # Should score 0/10
        assert result.overall_score == 0.0
        assert result.status == "needs_improvement"

    def test_scoring_consistency(self, excellent_agent):
        """Test that repeated validation yields consistent scores."""
        validator = AgentValidator()

        # Validate same agent 5 times
        scores = []
        for _ in range(5):
            result = validator.validate(excellent_agent)
            scores.append(result.overall_score)

        # All scores should be identical
        assert len(set(scores)) == 1

    def test_scoring_thresholds_exact_boundaries(self, tmp_path):
        """Test scoring thresholds at exact boundary values."""
        # Create agents at score boundaries
        test_cases = [
            (8.0, "excellent"),
            (7.0, "good"),
            (6.0, "adequate"),
            (5.9, "needs_improvement")
        ]

        # Note: Actual implementation needed to create agents
        # with specific target scores. This is a placeholder.

    # ============================================================
    # Recommendation Engine Tests (7 tests)
    # ============================================================

    def test_recommendations_for_low_example_density(self, poor_agent):
        """Test recommendations generated for low example density."""
        validator = AgentValidator()
        result = validator.validate(poor_agent)

        # Should recommend adding examples
        recommendations = [r.lower() for r in result.recommendations]
        assert any("example" in r for r in recommendations)

    def test_recommendations_for_missing_boundaries(self, poor_agent):
        """Test recommendations generated for missing boundaries."""
        validator = AgentValidator()
        result = validator.validate(poor_agent)

        # Should recommend adding boundary sections
        recommendations = [r.lower() for r in result.recommendations]
        assert any(
            "always" in r or "never" in r or "boundaries" in r
            for r in recommendations
        )

    def test_no_recommendations_for_excellent_agent(self, excellent_agent):
        """Test that excellent agents get minimal recommendations."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent)

        # Excellent agents should have 0-2 recommendations (minor only)
        assert len(result.recommendations) <= 2

    def test_recommendations_prioritized_by_impact(self, poor_agent):
        """Test that recommendations are prioritized by impact."""
        validator = AgentValidator()
        result = validator.validate(poor_agent)

        # First recommendation should address biggest gap
        # (typically examples or boundaries for poor agents)
        if result.recommendations:
            first = result.recommendations[0].lower()
            assert "example" in first or "boundary" in first

    def test_recommendations_specific_actionable(self, poor_agent):
        """Test that recommendations are specific and actionable."""
        validator = AgentValidator()
        result = validator.validate(poor_agent)

        # Each recommendation should have actionable guidance
        for rec in result.recommendations:
            # Should not be generic ("improve quality")
            assert "improve" not in rec.lower() or "add" in rec.lower()

    def test_recommendations_for_time_to_first_example(self, tmp_path):
        """Test recommendation for late first example."""
        # Agent with first example at line 60 (>50 line threshold)
        agent_file = tmp_path / "late-example.md"
        content = "---\nname: late\n---\n\n"
        content += "Text line\n" * 60  # Push example past threshold
        content += "```python\ncode()\n```\n"
        agent_file.write_text(content)

        validator = AgentValidator()
        result = validator.validate(agent_file)

        # Should recommend moving examples earlier
        recommendations = [r.lower() for r in result.recommendations]
        assert any("first example" in r or "earlier" in r for r in recommendations)

    def test_recommendations_limited_count(self, poor_agent):
        """Test that recommendations are limited to prevent overwhelming user."""
        validator = AgentValidator()
        result = validator.validate(poor_agent)

        # Should not exceed reasonable count (e.g., 10 recommendations max)
        assert len(result.recommendations) <= 10

    # ============================================================
    # JSON Output Format Tests (3 tests)
    # ============================================================

    def test_json_output_format(self, excellent_agent):
        """Test JSON output format matches specification."""
        validator = AgentValidator()
        result = validator.validate(excellent_agent, format="json")

        # Verify required keys
        required_keys = [
            "overall_score",
            "status",
            "scores",
            "metrics",
            "checks",
            "issues",
            "recommendations"
        ]

        for key in required_keys:
            assert hasattr(result, key) or key in result.__dict__, \
                f"Missing required key: {key}"

    def test_json_serializable(self, excellent_agent):
        """Test that result is JSON serializable."""
        import json

        validator = AgentValidator()
        result = validator.validate(excellent_agent, format="json")

        # Should be able to serialize to JSON
        json_str = json.dumps(result.to_dict())
        assert len(json_str) > 0

        # Should be able to deserialize back
        data = json.loads(json_str)
        assert data["overall_score"] == result.overall_score

    def test_json_nested_structure(self, excellent_agent):
        """Test JSON output has correct nested structure."""
        import json

        validator = AgentValidator()
        result = validator.validate(excellent_agent, format="json")

        data = result.to_dict()

        # Verify nested structures
        assert "examples" in data["scores"]
        assert "boundaries" in data["scores"]
        assert "example_density" in data["metrics"]
        assert "boundary_sections" in data["metrics"]

# More tests continue...
```

### 2.4 Coverage Targets

| Component | Line Coverage | Branch Coverage | Function Coverage |
|-----------|---------------|-----------------|-------------------|
| **agent_enhancement/** | ≥90% | ≥85% | 100% |
| **agent_validation/** | ≥90% | ≥85% | 100% |
| **commands/** | ≥85% | ≥80% | 100% |
| **Overall Target** | ≥90% | ≥85% | 100% |

**Coverage Commands**:
```bash
# Run with coverage
pytest tests/unit/ --cov=installer/core/lib --cov-report=term --cov-report=html

# View HTML report
open htmlcov/index.html

# Fail if coverage below threshold
pytest tests/unit/ --cov=installer/core/lib --cov-fail-under=90
```

---

## 3. Integration Test Specification

### 3.1 End-to-End Enhancement Workflow

**File**: `tests/integration/test_enhancement_workflow.py`

```python
"""Integration tests for end-to-end agent enhancement workflow."""

import pytest
from pathlib import Path
from installer.core.commands.agent_enhance import main as agent_enhance
from installer.core.lib.agent_enhancement.enhancer import SingleAgentEnhancer


@pytest.mark.integration
class TestEnhancementWorkflow:
    """Test complete enhancement workflow."""

    def test_full_enhancement_workflow_ai_strategy(self, test_template):
        """Test full enhancement workflow with AI strategy."""
        # Given: A basic agent stub
        agent_file = test_template / "agents" / "api-specialist.md"

        # When: Enhancement is requested via AI
        enhancer = SingleAgentEnhancer(strategy="ai", verbose=True)
        result = enhancer.enhance(agent_file, test_template)

        # Then: Agent is enhanced with AI-generated content
        assert result.success is True
        assert result.strategy_used == "ai"
        assert len(result.sections) >= 3
        assert len(result.templates) > 0

        # And: Enhanced file exists and is valid
        assert agent_file.exists()
        enhanced_content = agent_file.read_text()
        assert "## Related Templates" in enhanced_content
        assert "## Code Examples" in enhanced_content

    def test_full_enhancement_workflow_hybrid_strategy(self, test_template):
        """Test full enhancement workflow with hybrid strategy (recommended)."""
        agent_file = test_template / "agents" / "testing-specialist.md"

        enhancer = SingleAgentEnhancer(strategy="hybrid", verbose=True)
        result = enhancer.enhance(agent_file, test_template)

        # Hybrid MUST always succeed (either AI or static fallback)
        assert result.success is True
        assert result.strategy_used in ["ai", "static"]

    def test_command_line_interface(self, test_template):
        """Test /agent-enhance command line interface."""
        import sys

        agent_path = f"{test_template.name}/api-specialist"

        # Mock command line arguments
        sys.argv = [
            "agent-enhance",
            agent_path,
            "--verbose"
        ]

        # Execute command
        exit_code = agent_enhance()

        # Verify success
        assert exit_code == 0

    def test_dry_run_does_not_modify_file(self, test_template):
        """Test --dry-run flag does not modify agent file."""
        agent_file = test_template / "agents" / "domain-specialist.md"

        # Record original content
        original_content = agent_file.read_text()
        original_mtime = agent_file.stat().st_mtime

        # Run enhancement in dry-run mode
        import sys
        sys.argv = [
            "agent-enhance",
            f"{test_template.name}/domain-specialist",
            "--dry-run"
        ]

        exit_code = agent_enhance()
        assert exit_code == 0

        # Verify file was NOT modified
        assert agent_file.read_text() == original_content
        assert agent_file.stat().st_mtime == original_mtime


@pytest.mark.integration
class TestValidationWorkflow:
    """Test complete validation workflow."""

    def test_full_validation_workflow(self, existing_agents):
        """Test full validation workflow on existing agents."""
        from installer.core.commands.agent_validate import main as agent_validate
        import sys

        for agent_file in existing_agents:
            sys.argv = ["agent-validate", str(agent_file)]
            exit_code = agent_validate()

            # Should succeed for all agents
            assert exit_code == 0

    def test_batch_validation(self, global_agents_dir):
        """Test batch validation of all agents."""
        from installer.core.commands.agent_validate import validate_batch

        results = validate_batch(global_agents_dir)

        # Should validate all 15 agents
        assert len(results) == 15

        # All should have scores
        for result in results:
            assert 0 <= result.overall_score <= 10
```

**Total Integration Tests**: 25+ tests across all workflow files

---

## 4. Regression Test Specification

**File**: `tests/regression/test_existing_agents.py`

```python
"""Regression tests to ensure existing agents still work."""

import pytest
from pathlib import Path


@pytest.fixture
def global_agents():
    """Load all 15 global agents."""
    agents_dir = Path("installer/core/agents")
    return list(agents_dir.glob("*.md"))


class TestExistingAgentsCompatibility:
    """Ensure existing agents still load and work after enhancements."""

    def test_all_agents_have_valid_frontmatter(self, global_agents):
        """Test all agents have valid YAML frontmatter."""
        import frontmatter

        for agent_file in global_agents:
            agent = frontmatter.load(agent_file)

            # Verify required metadata
            assert "name" in agent.metadata, f"{agent_file.name} missing 'name'"
            assert "description" in agent.metadata, \
                f"{agent_file.name} missing 'description'"

    def test_enhancement_preserves_frontmatter(self, global_agents):
        """Test that enhancement doesn't corrupt YAML frontmatter."""
        import frontmatter

        for agent_file in global_agents:
            # Load original
            original = frontmatter.load(agent_file)

            # Simulate enhancement (in-memory)
            enhancer = SingleAgentEnhancer(strategy="static", verbose=False)

            # Verify metadata is preserved
            # (actual enhancement logic should preserve frontmatter)
            assert original.metadata["name"] is not None

    def test_all_agents_load_without_errors(self, global_agents):
        """Test that all agents can be loaded without errors."""
        import frontmatter

        errors = []

        for agent_file in global_agents:
            try:
                agent = frontmatter.load(agent_file)
                assert len(agent.content) > 0
            except Exception as e:
                errors.append(f"{agent_file.name}: {str(e)}")

        assert len(errors) == 0, f"Failed to load agents: {errors}"


class TestBaselineValidationScores:
    """Establish and verify baseline validation scores."""

    BASELINE_SCORES = {
        "architectural-reviewer": 8.5,
        "code-reviewer": 7.2,
        "task-manager": 6.0,
        "test-orchestrator": 7.5,
        "test-verifier": 7.3,
        # ... add baseline scores for all 15 agents
    }

    def test_validation_scores_within_variance(self, global_agents):
        """Test that validation scores are within ±0.5 of baseline."""
        from installer.core.lib.agent_validation.validator import AgentValidator

        validator = AgentValidator()

        for agent_file in global_agents:
            agent_name = agent_file.stem

            if agent_name not in self.BASELINE_SCORES:
                continue

            result = validator.validate(agent_file)
            expected = self.BASELINE_SCORES[agent_name]

            # Allow ±0.5 variance
            assert abs(result.overall_score - expected) <= 0.5, \
                f"{agent_name}: score {result.overall_score} differs from " \
                f"baseline {expected} by more than 0.5"
```

**Total Regression Tests**: 13+ tests

---

## 5. Quality Validation Specification

**File**: `tests/quality/test_improvement_metrics.py`

```python
"""Test that enhancements actually improve agent quality."""

import pytest
from pathlib import Path
from installer.core.lib.agent_enhancement.enhancer import SingleAgentEnhancer
from installer.core.lib.agent_validation.validator import AgentValidator


class TestImprovementMetrics:
    """Test quality improvement from enhancement."""

    def test_enhancement_improves_score(self, low_quality_agent, template_dir):
        """Test that enhancement improves overall quality score."""
        validator = AgentValidator()

        # Measure before enhancement
        before = validator.validate(low_quality_agent)
        assert before.overall_score < 7.0  # Confirm it's low quality

        # Enhance agent
        enhancer = SingleAgentEnhancer(strategy="ai", verbose=False)
        result = enhancer.enhance(low_quality_agent, template_dir)
        assert result.success is True

        # Measure after enhancement
        after = validator.validate(low_quality_agent)

        # Score MUST improve
        assert after.overall_score > before.overall_score, \
            f"Enhancement did not improve score: {before.overall_score} → " \
            f"{after.overall_score}"

        # Should reach ≥8.0 target
        assert after.overall_score >= 8.0

    def test_example_density_increases(self, low_quality_agent, template_dir):
        """Test that enhancement increases example density."""
        validator = AgentValidator()

        before = validator.validate(low_quality_agent)

        # Enhance with focus on examples
        enhancer = SingleAgentEnhancer(strategy="ai", verbose=False)
        enhancer.enhance(low_quality_agent, template_dir)

        after = validator.validate(low_quality_agent)

        # Example density MUST increase
        assert after.metrics.example_density > before.metrics.example_density

        # Should reach 40%+ target
        assert after.metrics.example_density >= 40.0

    def test_boundary_sections_added(self, agent_without_boundaries, template_dir):
        """Test that enhancement adds missing boundary sections."""
        validator = AgentValidator()

        before = validator.validate(agent_without_boundaries)
        assert before.metrics.boundary_sections["always"] == 0

        # Enhance agent
        enhancer = SingleAgentEnhancer(strategy="ai", verbose=False)
        enhancer.enhance(agent_without_boundaries, template_dir)

        after = validator.validate(agent_without_boundaries)

        # Boundaries MUST be added
        assert after.metrics.boundary_sections["always"] > 0
        assert after.metrics.boundary_sections["never"] > 0
        assert after.metrics.boundary_sections["ask"] > 0
```

**Total Quality Tests**: 9+ tests

---

## 6. CI/CD Integration Specification

### 6.1 GitHub Actions Workflow

**File**: `.github/workflows/agent-quality-checks.yml`

```yaml
name: Agent Quality Checks

on:
  pull_request:
    paths:
      - 'installer/core/agents/**'
      - 'installer/core/lib/agent_enhancement/**'
      - 'installer/core/lib/agent_validation/**'
  push:
    branches:
      - main
    paths:
      - 'installer/core/agents/**'

jobs:
  validate-agents:
    name: Validate All Agents
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pytest-cov frontmatter

      - name: Run unit tests
        run: |
          pytest tests/unit/ \
            --cov=installer/core/lib \
            --cov-report=term \
            --cov-report=json \
            --cov-fail-under=90

      - name: Validate all global agents
        run: |
          python installer/core/commands/agent_validate.py \
            --batch installer/core/agents/ \
            --threshold 7.0 \
            --format json \
            --output validation-report.json

      - name: Upload validation report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: validation-report
          path: validation-report.json

      - name: Check quality threshold
        run: |
          # Fail if any agent scores <7.0
          python -c "
          import json
          with open('validation-report.json') as f:
              report = json.load(f)

          failing = [a for a in report['agents'] if a['score'] < 7.0]

          if failing:
              print(f'❌ {len(failing)} agents below threshold:')
              for agent in failing:
                  print(f'  - {agent["name"]}: {agent["score"]}/10')
              exit(1)
          else:
              print('✅ All agents meet quality threshold')
          "
```

### 6.2 Quality Gates

| Gate | Threshold | Action if Failed |
|------|-----------|-----------------|
| **Unit Test Coverage** | ≥90% lines, ≥85% branches | ❌ Block PR |
| **Agent Validation** | All agents ≥7.0/10 | ❌ Block PR |
| **Regression Tests** | 100% pass | ❌ Block PR |
| **Integration Tests** | 100% pass | ❌ Block PR |
| **Example Density** | ≥40% for new/enhanced agents | ⚠️ Warn |
| **Boundary Sections** | All 3 sections present | ⚠️ Warn |
| **Enhancement Success** | ≥80% for AI strategy | ⚠️ Warn |
| **Hybrid Fallback** | <10% | ⚠️ Warn |

---

## 7. Documentation Integration

### 7.1 User Documentation Updates

**CLAUDE.md additions**:
```markdown
## Agent Quality Assurance

Taskwright includes comprehensive agent validation:

### Validate Single Agent
```bash
/agent-validate installer/core/agents/code-reviewer.md
```

### Validate All Agents
```bash
/agent-validate-batch installer/core/agents/ --threshold 7.0
```

### Quality Metrics

Agents are scored on:
- **Example Density**: 40-50% code examples (target)
- **Boundary Clarity**: ALWAYS/NEVER/ASK sections present
- **Structure**: Complete sections (purpose, capabilities, etc.)
- **Clarity**: Clear descriptions and use cases

**Quality Levels**:
- 8-10/10: Excellent (production-ready)
- 7-8/10: Good (minor improvements)
- 6-7/10: Adequate (needs work)
- <6/10: Poor (requires enhancement)
```

---

## 8. Success Metrics

### 8.1 Test Coverage Metrics

**Target State**:
- Unit test coverage: ≥90% lines
- Integration test coverage: Critical paths 100%
- Regression test baseline: 15 agents validated
- Quality validation: Before/after improvement tracked

### 8.2 Quality Improvement Metrics

**Baseline (Current State)**:
| Agent | Current Score | Target Score | Status |
|-------|--------------|--------------|--------|
| architectural-reviewer | 8.5/10 | ✅ 8.5 | Excellent |
| code-reviewer | 7.2/10 | 8.0+ | Needs improvement |
| task-manager | 6.0/10 | 8.0+ | Critical |

**Success Criteria**:
- All agents score ≥8.0/10 after enhancement
- Average improvement: ≥1.5 points per agent
- Example density: All agents ≥40%
- Boundary sections: 100% have ALWAYS/NEVER/ASK

---

## 9. Acceptance Criteria

### AC1: Unit Test Suite Complete
- [ ] ≥90% line coverage for agent_enhancement module
- [ ] ≥90% line coverage for agent_validation module
- [ ] 100% function coverage
- [ ] All critical paths tested (AI enhancement, retry, hybrid fallback, validation)
- [ ] Mock strategies working for AI responses

### AC2: Integration Test Suite Complete
- [ ] End-to-end enhancement workflow tested
- [ ] End-to-end validation workflow tested
- [ ] Batch operations tested
- [ ] CI/CD integration tested
- [ ] Performance benchmarks established

### AC3: Regression Test Suite Complete
- [ ] All 15 existing agents validated
- [ ] API backward compatibility verified
- [ ] Baseline validation scores established
- [ ] Enhancement doesn't break existing functionality

### AC4: Quality Validation Complete
- [ ] Before/after comparison working
- [ ] Improvement metrics tracked
- [ ] Enhancement quality verified
- [ ] All agents can reach ≥8.0/10 target

### AC5: CI/CD Integration Complete
- [ ] GitHub Actions workflow configured
- [ ] Quality gates enforced
- [ ] Pre-commit hooks installed
- [ ] Automated reports generated
- [ ] PR comments working

### AC6: Documentation Complete
- [ ] CLAUDE.md updated with agent QA section
- [ ] Command specifications complete
- [ ] Developer testing guide written
- [ ] Workflow guides created
- [ ] CI/CD integration documented

---

## 10. Implementation Timeline

### Week 1: Unit Tests (2-3 days)

**Day 1-2**: Core component tests
- agent_enhancement module (enhancer, parser, applier)
- agent_validation module (validator, metrics, scoring)
- Test fixtures and mock factories

**Day 3**: Command tests
- /agent-enhance command
- /agent-validate command
- Error handling and edge cases

**Deliverables**:
- 90%+ coverage for core modules
- All fixtures in place
- Mock AI responses working

### Week 2: Integration & Regression Tests (2-3 days)

**Day 4-5**: Integration tests
- End-to-end enhancement workflow
- End-to-end validation workflow
- Batch operations
- CI/CD integration tests

**Day 6**: Regression tests
- Existing agent compatibility
- API backward compatibility
- Baseline validation scores

**Deliverables**:
- Critical path tests 100% coverage
- Regression baseline established
- Integration test suite complete

### Week 3: Quality Validation & Documentation (1-2 days)

**Day 7**: Quality validation
- Before/after comparison tests
- Improvement metrics tracking
- Batch enhancement quality tests

**Day 8**: Documentation and cleanup
- User documentation updates
- Developer testing guide
- CI/CD configuration
- Buffer for bug fixes

**Deliverables**:
- Complete test suite (unit + integration + regression + quality)
- CI/CD pipeline configured
- Documentation complete

---

## 11. Dependencies

**Blocks**:
- Future agent enhancement workflow improvements

**Depends On**:
- TASK-AI-2B37 (AI Integration) - Should complete first for realistic testing
- TASK-PHASE-8-INCREMENTAL (✅ completed)

**Related**:
- TASK-DOC-F3A3 (Documentation suite)
- TASK-E2E-97EB (End-to-end validation)

---

## 12. Next Steps

After task creation:

```bash
# Review task details
cat tasks/backlog/TASK-TEST-87F4-comprehensive-test-suite-agent-enhancement.md

# When ready to implement
/task-work TASK-TEST-87F4

# Track progress
/task-status TASK-TEST-87F4

# Complete after all acceptance criteria met
/task-complete TASK-TEST-87F4
```

---

**Created**: 2025-11-20
**Updated**: 2025-11-21 (expanded to include agent validation testing)
**Status**: BACKLOG (Ready for Implementation)
**Priority**: HIGH
**Complexity**: 8/10 (Complex)
**Estimated Duration**: 4-5 days

---

## 13. Quick Reference

### Test Counts by Category

| Category | Test Count | Coverage Target |
|----------|-----------|----------------|
| **Unit: Enhancement** | 38 tests | ≥90% |
| **Unit: Validation** | 45 tests | ≥90% |
| **Unit: Commands** | 20 tests | ≥85% |
| **Integration: Workflows** | 14 tests | 100% critical paths |
| **Integration: Batch** | 5 tests | 100% |
| **Integration: CI/CD** | 6 tests | 100% |
| **Regression** | 13 tests | 100% |
| **Quality** | 9 tests | 100% |
| **TOTAL** | **150+ tests** | **≥90% overall** |

### Command Reference

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/unit/ --cov=installer/core/lib --cov-report=html

# Run integration tests only
pytest tests/integration/ -v --timeout=600

# Run regression tests only
pytest tests/regression/ -v

# Check coverage threshold
pytest tests/unit/ --cov-fail-under=90
```

---

**This specification provides implementation-ready details for comprehensive testing of the agent enhancement and validation system with 150+ tests covering all aspects of the workflow.**
