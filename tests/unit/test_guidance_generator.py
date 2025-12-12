"""
Unit tests for the guidance_generator module.

Following TDD approach - tests written first, then implementation.
"""

import pytest
from pathlib import Path
from installer.core.lib.guidance_generator import (
    extract_boundaries,
    extract_capability_summary,
    generate_path_patterns,
    validate_guidance_size,
    generate_guidance_from_agent,
)


# Test Fixtures - Sample Agent Content
@pytest.fixture
def sample_agent_content():
    """Sample agent markdown content for testing."""
    return """---
stack: [python, fastapi]
phase: implementation
capabilities: [api, async-patterns, pydantic]
priority: 9
---

# FastAPI Specialist

Expert in building FastAPI endpoints with async patterns and Pydantic validation.

## Quick Start

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    id: int
    name: str
    email: str

@app.get("/users/{user_id}")
async def get_user(user_id: int) -> User:
    # Fetch user from database
    pass
```

## Boundaries

### ALWAYS
- ✅ Use Pydantic models for request/response validation (type safety)
- ✅ Implement async route handlers with async/await (non-blocking I/O)
- ✅ Return appropriate HTTP status codes (REST conventions)
- ✅ Add dependency injection for database connections (testability)
- ✅ Include proper error handling with HTTPException (clear errors)

### NEVER
- ❌ Never use blocking I/O in async routes (deadlock risk)
- ❌ Never skip request validation (security vulnerability)
- ❌ Never hardcode configuration values (environment-specific issues)
- ❌ Never expose internal errors to clients (security leak)
- ❌ Never ignore type hints in Pydantic models (runtime errors)

### ASK
- ⚠️ Authentication strategy: Ask if OAuth2, JWT, or API keys preferred
- ⚠️ Database ORM choice: Ask if SQLAlchemy, Tortoise, or raw SQL
- ⚠️ Caching layer needed: Ask if Redis, in-memory, or none

## Capabilities

This agent specializes in:
- Building RESTful API endpoints with FastAPI
- Async/await patterns for non-blocking operations
- Pydantic schema validation and serialization
- Dependency injection patterns
- Error handling and HTTP status codes

## Integration with GuardKit

- **Phase**: Implementation (Phase 3)
- **When invoked**: Automatically selected for Python API tasks
- **Fallback**: task-manager for general Python tasks
"""


@pytest.fixture
def minimal_agent_content():
    """Minimal agent content for edge case testing."""
    return """---
stack: [typescript]
phase: testing
---

# Test Agent

Simple test agent.

## Boundaries

### ALWAYS
- ✅ Write tests (quality)
- ✅ Run coverage (metrics)
- ✅ Fix failures (reliability)
- ✅ Document edge cases (clarity)
- ✅ Use mocks wisely (isolation)

### NEVER
- ❌ Skip tests (quality loss)
- ❌ Ignore failures (technical debt)
- ❌ Hardcode values (brittleness)
- ❌ Test implementation (coupling)
- ❌ Mock everything (false confidence)

### ASK
- ⚠️ Test framework: Ask which to use
- ⚠️ Coverage threshold: Ask target percentage
- ⚠️ E2E vs unit: Ask test strategy
"""


class TestBoundaryExtraction:
    """Test boundary extraction from agent content."""

    def test_extract_boundaries_complete(self, sample_agent_content):
        """Test extracting all boundary sections."""
        boundaries = extract_boundaries(sample_agent_content)

        assert "### ALWAYS" in boundaries
        assert "### NEVER" in boundaries
        assert "### ASK" in boundaries

    def test_extract_boundaries_count_always_rules(self, sample_agent_content):
        """Test ALWAYS rules are extracted (expect 5)."""
        boundaries = extract_boundaries(sample_agent_content)
        assert boundaries.count("✅") >= 5

    def test_extract_boundaries_count_never_rules(self, sample_agent_content):
        """Test NEVER rules are extracted (expect 5)."""
        boundaries = extract_boundaries(sample_agent_content)
        assert boundaries.count("❌") >= 5

    def test_extract_boundaries_count_ask_scenarios(self, sample_agent_content):
        """Test ASK scenarios are extracted (expect 3)."""
        boundaries = extract_boundaries(sample_agent_content)
        assert boundaries.count("⚠️") >= 3

    def test_extract_boundaries_preserves_rationale(self, sample_agent_content):
        """Test that rationale in parentheses is preserved."""
        boundaries = extract_boundaries(sample_agent_content)
        assert "(type safety)" in boundaries
        assert "(non-blocking I/O)" in boundaries

    def test_extract_boundaries_minimal_content(self, minimal_agent_content):
        """Test extraction works with minimal content."""
        boundaries = extract_boundaries(minimal_agent_content)
        assert "### ALWAYS" in boundaries
        assert "### NEVER" in boundaries
        assert "### ASK" in boundaries

    def test_extract_boundaries_missing_section(self):
        """Test handling of missing boundary sections."""
        content = """# Agent

Some content without boundaries."""

        boundaries = extract_boundaries(content)
        # Should return empty or placeholder
        assert boundaries == "" or "No boundaries found" in boundaries


class TestCapabilitySummaryExtraction:
    """Test capability summary extraction."""

    def test_extract_capability_summary_from_capabilities_section(self, sample_agent_content):
        """Test extracting summary from Capabilities section."""
        summary = extract_capability_summary(sample_agent_content)

        assert len(summary) > 0
        assert "FastAPI" in summary or "API" in summary

    def test_extract_capability_summary_length_constraint(self, sample_agent_content):
        """Test summary is brief (2-3 sentences)."""
        summary = extract_capability_summary(sample_agent_content)

        # Summary should be non-empty and reasonable length
        assert len(summary) > 0
        # Should be less than 500 characters for brevity
        assert len(summary) < 500

    def test_extract_capability_summary_from_description(self, minimal_agent_content):
        """Test fallback to description if no Capabilities section."""
        summary = extract_capability_summary(minimal_agent_content)

        assert len(summary) > 0


class TestPathPatternGeneration:
    """Test path pattern generation from agent metadata."""

    def test_generate_path_patterns_python_fastapi(self):
        """Test pattern generation for Python/FastAPI stack."""
        metadata = {
            "stack": ["python", "fastapi"],
            "phase": "implementation"
        }
        patterns = generate_path_patterns(metadata)

        # Should generate API-specific patterns
        assert "**/api/**/*.py" in patterns or "**/*.py" in patterns

    def test_generate_path_patterns_typescript_react(self):
        """Test pattern generation for TypeScript/React stack."""
        metadata = {
            "stack": ["typescript", "react"],
            "phase": "implementation"
        }
        patterns = generate_path_patterns(metadata)

        assert "**/*.{ts,tsx}" in patterns or "**/*.tsx" in patterns

    def test_generate_path_patterns_testing_phase(self):
        """Test pattern generation for testing phase."""
        metadata = {
            "stack": ["python"],
            "phase": "testing"
        }
        patterns = generate_path_patterns(metadata)

        assert "**/tests/**" in patterns or "**/test_*.py" in patterns

    def test_generate_path_patterns_database_specialist(self):
        """Test pattern generation for database specialist."""
        metadata = {
            "stack": ["python"],
            "phase": "implementation",
            "capabilities": ["database", "orm"]
        }
        patterns = generate_path_patterns(metadata)

        # Should include model/repository patterns
        assert "**/models/**" in patterns or "**/repositories/**" in patterns

    def test_generate_path_patterns_multiple_stacks(self):
        """Test pattern generation with multiple stacks."""
        metadata = {
            "stack": ["python", "typescript", "react"],
            "phase": "implementation"
        }
        patterns = generate_path_patterns(metadata)

        # Should generate patterns for all stacks
        assert "**/*.py" in patterns or "**/api/**/*.py" in patterns
        assert "**/*.{ts,tsx}" in patterns or "**/*.tsx" in patterns

    def test_generate_path_patterns_cross_stack(self):
        """Test pattern generation for cross-stack agents."""
        metadata = {
            "stack": ["cross-stack"],
            "phase": "orchestration"
        }
        patterns = generate_path_patterns(metadata)

        # Should generate generic patterns (all files or none)
        assert patterns == "" or "**/*" in patterns

    # Tests for technology-agnostic path patterns (TASK-PDI-001)
    def test_generate_path_patterns_explicit_paths_passthrough(self):
        """Test that explicit 'paths' field in metadata takes highest priority."""
        metadata = {
            "stack": ["dotnet"],
            "phase": "implementation",
            "paths": "**/Repositories/**/*.cs, **/*Repository.cs"
        }
        patterns = generate_path_patterns(metadata)

        # Explicit paths should be returned as-is (passthrough)
        assert patterns == "**/Repositories/**/*.cs, **/*Repository.cs"

    def test_generate_path_patterns_explicit_paths_override_stack(self):
        """Test that explicit paths override stack-based patterns."""
        metadata = {
            "stack": ["python"],
            "phase": "testing",
            "capabilities": ["database"],
            "paths": "**/custom/path/**/*.py"
        }
        patterns = generate_path_patterns(metadata)

        # Explicit paths take priority over everything else
        assert patterns == "**/custom/path/**/*.py"
        assert "**/*.py" not in patterns or patterns == "**/custom/path/**/*.py"

    def test_generate_path_patterns_api_phase(self):
        """Test pattern generation for API development phase."""
        metadata = {
            "stack": ["python"],
            "phase": "api"
        }
        patterns = generate_path_patterns(metadata)

        # Should include API-related patterns
        assert "**/api/**" in patterns or "**/routes/**" in patterns

    def test_generate_path_patterns_ui_phase(self):
        """Test pattern generation for UI development phase."""
        metadata = {
            "stack": ["typescript"],
            "phase": "ui"
        }
        patterns = generate_path_patterns(metadata)

        # Should include UI-related patterns
        assert "**/components/**" in patterns or "**/views/**" in patterns

    def test_generate_path_patterns_services_capability(self):
        """Test pattern generation for services capability."""
        metadata = {
            "stack": ["python"],
            "capabilities": ["services"]
        }
        patterns = generate_path_patterns(metadata)

        # Should include services pattern
        assert "**/services/**" in patterns

    def test_generate_path_patterns_controllers_capability(self):
        """Test pattern generation for controllers capability."""
        metadata = {
            "stack": ["java"],
            "capabilities": ["controllers"]
        }
        patterns = generate_path_patterns(metadata)

        # Should include controllers pattern
        assert "**/controllers/**" in patterns

    def test_generate_path_patterns_go_stack(self):
        """Test pattern generation for Go stack."""
        metadata = {
            "stack": ["go"]
        }
        patterns = generate_path_patterns(metadata)

        assert "**/*.go" in patterns

    def test_generate_path_patterns_rust_stack(self):
        """Test pattern generation for Rust stack."""
        metadata = {
            "stack": ["rust"]
        }
        patterns = generate_path_patterns(metadata)

        assert "**/*.rs" in patterns

    def test_generate_path_patterns_java_stack(self):
        """Test pattern generation for Java stack."""
        metadata = {
            "stack": ["java"]
        }
        patterns = generate_path_patterns(metadata)

        assert "**/*.java" in patterns

    def test_generate_path_patterns_capability_case_insensitive(self):
        """Test that capability matching is case-insensitive."""
        metadata = {
            "stack": ["python"],
            "capabilities": ["DATABASE", "Api"]  # Mixed case
        }
        patterns = generate_path_patterns(metadata)

        # Should match despite case differences
        assert "**/models/**" in patterns or "**/repositories/**" in patterns
        assert "**/api/**" in patterns


class TestGuidanceSizeValidation:
    """Test guidance file size validation."""

    def test_validate_guidance_size_under_3kb(self):
        """Test validation passes for content under 3KB."""
        content = "x" * (2 * 1024)  # 2KB
        warnings = validate_guidance_size(content, "test-agent")

        assert len(warnings) == 0

    def test_validate_guidance_size_warning_3kb_to_5kb(self):
        """Test warning for content between 3KB and 5KB."""
        content = "x" * (4 * 1024)  # 4KB
        warnings = validate_guidance_size(content, "test-agent")

        assert len(warnings) == 1
        assert "exceeds target 3KB" in warnings[0]
        assert "4.0KB" in warnings[0]

    def test_validate_guidance_size_error_over_5kb(self):
        """Test error for content over 5KB."""
        content = "x" * (6 * 1024)  # 6KB
        warnings = validate_guidance_size(content, "test-agent")

        assert len(warnings) == 1
        assert "exceeds 5KB" in warnings[0]
        assert "6.0KB" in warnings[0]

    def test_validate_guidance_size_exact_3kb(self):
        """Test edge case: exactly 3KB."""
        content = "x" * (3 * 1024)
        warnings = validate_guidance_size(content, "test-agent")

        # At exactly 3KB, should not warn (threshold is >3KB)
        assert len(warnings) == 0

    def test_validate_guidance_size_exact_5kb(self):
        """Test edge case: exactly 5KB."""
        content = "x" * (5 * 1024)
        warnings = validate_guidance_size(content, "test-agent")

        # At exactly 5KB, should warn about exceeding target (but not error)
        assert len(warnings) == 1
        assert "target 3KB" in warnings[0]
        assert "5.0KB" in warnings[0]


class TestCompleteGuidanceGeneration:
    """Test complete guidance file generation."""

    def test_generate_guidance_has_frontmatter(self, sample_agent_content):
        """Test generated guidance includes frontmatter."""
        guidance = generate_guidance_from_agent(sample_agent_content, "api-specialist")

        assert guidance.startswith("---")
        assert "paths:" in guidance
        assert "agent:" in guidance

    def test_generate_guidance_has_boundaries(self, sample_agent_content):
        """Test generated guidance includes boundaries."""
        guidance = generate_guidance_from_agent(sample_agent_content, "api-specialist")

        assert "## Boundaries" in guidance
        assert "### ALWAYS" in guidance
        assert "### NEVER" in guidance
        assert "### ASK" in guidance

    def test_generate_guidance_has_reference_links(self, sample_agent_content):
        """Test generated guidance includes reference links."""
        guidance = generate_guidance_from_agent(sample_agent_content, "api-specialist")

        assert "## Full Documentation" in guidance
        assert "agents/api-specialist.md" in guidance
        assert "agents/api-specialist-ext.md" in guidance

    def test_generate_guidance_size_under_5kb(self, sample_agent_content):
        """Test generated guidance is under 5KB."""
        guidance = generate_guidance_from_agent(sample_agent_content, "api-specialist")

        size_bytes = len(guidance.encode('utf-8'))
        assert size_bytes < 5 * 1024, f"Guidance file is {size_bytes} bytes, exceeds 5KB limit"

    def test_generate_guidance_includes_when_to_use(self, sample_agent_content):
        """Test guidance includes 'When to Use' section."""
        guidance = generate_guidance_from_agent(sample_agent_content, "api-specialist")

        assert "## When to Use" in guidance

    def test_generate_guidance_path_patterns_from_metadata(self, sample_agent_content):
        """Test path patterns are generated from metadata."""
        guidance = generate_guidance_from_agent(sample_agent_content, "api-specialist")

        # Extract frontmatter paths
        lines = guidance.split('\n')
        frontmatter_end = 0
        for i, line in enumerate(lines[1:], 1):  # Skip first ---
            if line.strip() == '---':
                frontmatter_end = i
                break

        frontmatter = '\n'.join(lines[1:frontmatter_end])
        assert "paths:" in frontmatter
        # Should have API-related patterns
        assert "*.py" in frontmatter or "api" in frontmatter.lower()

    def test_generate_guidance_agent_name_in_frontmatter(self, sample_agent_content):
        """Test agent name is included in frontmatter."""
        guidance = generate_guidance_from_agent(sample_agent_content, "api-specialist")

        assert "agent: api-specialist" in guidance or "agent: fastapi-specialist" in guidance

    def test_generate_guidance_minimal_content(self, minimal_agent_content):
        """Test guidance generation with minimal agent content."""
        guidance = generate_guidance_from_agent(minimal_agent_content, "test-agent")

        assert "---" in guidance
        assert "## Boundaries" in guidance
        assert "## Full Documentation" in guidance


class TestGuidanceGeneratorEdgeCases:
    """Test edge cases and error handling."""

    def test_extract_boundaries_no_markdown_headers(self):
        """Test handling of content without markdown headers."""
        content = "Just some plain text without any structure."
        boundaries = extract_boundaries(content)

        # Should handle gracefully
        assert isinstance(boundaries, str)

    def test_generate_path_patterns_empty_metadata(self):
        """Test path pattern generation with empty metadata."""
        metadata = {}
        patterns = generate_path_patterns(metadata)

        # Should return empty or generic pattern
        assert isinstance(patterns, str)

    def test_generate_path_patterns_unknown_stack(self):
        """Test handling of unknown stack."""
        metadata = {"stack": ["unknown-stack-xyz"]}
        patterns = generate_path_patterns(metadata)

        # Should handle gracefully, maybe return generic pattern
        assert isinstance(patterns, str)

    def test_validate_guidance_size_empty_content(self):
        """Test size validation with empty content."""
        warnings = validate_guidance_size("", "empty-agent")

        # Should pass (0 KB)
        assert len(warnings) == 0

    def test_generate_guidance_malformed_frontmatter(self):
        """Test handling of agent with malformed frontmatter."""
        content = """---
this is not valid yaml: [unclosed
---

# Agent Content
"""
        # Should handle gracefully
        try:
            guidance = generate_guidance_from_agent(content, "malformed-agent")
            # If it doesn't raise, check it returns something
            assert isinstance(guidance, str)
        except Exception as e:
            # Or it should raise a clear error
            assert "frontmatter" in str(e).lower() or "yaml" in str(e).lower()
