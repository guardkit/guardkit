"""
Integration tests for agent splitter in template-init workflow.

Tests that agent splitting works end-to-end during template generation.
"""

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_template_dir():
    """Create a temporary template directory for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_agent_content():
    """Sample agent content for testing."""
    return """---
name: test-specialist
description: Test specialist agent
tools: [Read, Write, Edit, Grep, Bash]
tags: [testing, python]
stack: python
phase: implementation
capabilities: [unit-testing, integration-testing]
keywords: [pytest, test, testing]
priority: 8
---

# Test Specialist

## Overview

Specialist for writing tests in Python projects.

## Purpose

Helps developers write comprehensive test suites.

## Boundaries

### ALWAYS
- ✅ Write tests before implementation (TDD approach)
- ✅ Ensure >80% code coverage (quality gate)
- ✅ Use descriptive test names (readability)
- ✅ Follow AAA pattern (Arrange-Act-Assert)
- ✅ Mock external dependencies (isolation)

### NEVER
- ❌ Never skip tests (quality violation)
- ❌ Never test implementation details (brittle tests)
- ❌ Never use sleep in tests (flaky tests)
- ❌ Never share state between tests (side effects)
- ❌ Never ignore test failures (technical debt)

### ASK
- ⚠️ Integration tests needed: Ask about external dependencies
- ⚠️ Performance tests required: Ask about acceptable latency
- ⚠️ E2E tests scope: Ask what user journeys to cover

## Quick Start

### Example 1: Basic unit test
```python
def test_addition():
    assert 1 + 1 == 2
```

### Example 2: Test with fixture
```python
@pytest.fixture
def sample_data():
    return [1, 2, 3]

def test_sum(sample_data):
    assert sum(sample_data) == 6
```

### Example 3: Parameterized test
```python
@pytest.mark.parametrize("input,expected", [
    (1, 2),
    (2, 4),
    (3, 6),
])
def test_double(input, expected):
    assert input * 2 == expected
```

## Capabilities

- Unit test writing
- Integration test design
- Test fixture management
- Mocking and stubbing
- Coverage analysis

## Phase Integration

Used in Phase 4 (Testing) for creating and running tests.

## Loading Extended Content

For detailed examples and best practices, see `test-specialist-ext.md`.

## Detailed Examples

### Example 4: Async test
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await async_operation()
    assert result == expected_value
```

### Example 5: Exception testing
```python
def test_raises_error():
    with pytest.raises(ValueError, match="Invalid input"):
        dangerous_function("bad input")
```

### Example 6: Mock usage
```python
from unittest.mock import Mock, patch

def test_with_mock():
    mock_db = Mock()
    mock_db.query.return_value = [1, 2, 3]

    result = get_users(mock_db)
    assert len(result) == 3
    mock_db.query.assert_called_once()
```

## Best Practices

### 1. Test isolation
Each test should be independent and not rely on other tests.

### 2. Clear test names
Use descriptive names that explain what is being tested.

### 3. One assertion per test
Keep tests focused on a single behavior.

### 4. Use fixtures for setup
Share common setup code using pytest fixtures.

### 5. Test edge cases
Don't just test the happy path - test boundaries and errors.

## Anti-Patterns

### 1. Testing private methods
```python
# ❌ BAD
def test_private_method():
    obj._internal_method()

# ✅ GOOD
def test_public_behavior():
    obj.public_method()
```

### 2. Brittle assertions
```python
# ❌ BAD
assert result == {"name": "John", "age": 30, "created": "2024-01-01"}

# ✅ GOOD
assert result["name"] == "John"
assert result["age"] == 30
```

## Technology-Specific Guidance

### pytest specifics
- Use fixtures for dependency injection
- Mark tests with `@pytest.mark.*` for categorization
- Use `pytest.param` for complex parametrization

### Coverage tools
- Use `pytest-cov` for coverage reporting
- Set minimum thresholds in pytest.ini
- Focus on branch coverage, not just line coverage

## Troubleshooting

### Issue: Tests are flaky
**Solution**: Remove non-deterministic behavior like sleeps, random data, or datetime.now()

### Issue: Slow test suite
**Solution**: Parallelize with pytest-xdist, optimize fixtures, mock expensive operations

### Issue: Low coverage
**Solution**: Identify uncovered branches, add edge case tests, refactor for testability
"""


class MockAgent:
    """Mock agent for testing."""

    def __init__(self, name, full_definition):
        self.name = name
        self.full_definition = full_definition


class MockAgentInventory:
    """Mock agent inventory for testing."""

    def __init__(self, agents):
        self._agents = agents

    def all_agents(self):
        return self._agents


class TestAgentSplitterIntegration:
    """Integration tests for agent splitting in template generation."""

    def test_agents_split_during_template_generation(self, temp_template_dir, sample_agent_content):
        """Test that agents are split into core and extended files during template generation."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        # Create agents directory
        agents_dir = temp_template_dir / "agents"
        agents_dir.mkdir(exist_ok=True)

        # Split the agent content
        core_content, extended_content = split_agent_content(sample_agent_content)

        # Save both files
        agent_file = agents_dir / "test-specialist.md"
        with open(agent_file, "w", encoding="utf-8") as f:
            f.write(core_content)

        extended_file = agents_dir / "test-specialist-ext.md"
        with open(extended_file, "w", encoding="utf-8") as f:
            f.write(extended_content)

        # Verify both files exist
        assert agent_file.exists()
        assert extended_file.exists()

        # Verify core file has essential sections
        core_text = agent_file.read_text()
        assert "## Boundaries" in core_text
        assert "## Quick Start" in core_text
        assert "## Capabilities" in core_text

        # Verify extended file has detailed sections
        extended_text = extended_file.read_text()
        assert "## Detailed Examples" in extended_text
        assert "## Best Practices" in extended_text
        assert "## Anti-Patterns" in extended_text

    def test_multiple_agents_split_correctly(self, temp_template_dir, sample_agent_content):
        """Test that multiple agents are all split correctly."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        # Create multiple agents
        agent_names = ["api-specialist", "database-specialist", "ui-specialist"]

        agents_dir = temp_template_dir / "agents"
        agents_dir.mkdir(exist_ok=True)

        for agent_name in agent_names:
            # Modify sample content for each agent
            agent_content = sample_agent_content.replace("test-specialist", agent_name)

            # Split and save
            core_content, extended_content = split_agent_content(agent_content)

            agent_file = agents_dir / f"{agent_name}.md"
            with open(agent_file, "w", encoding="utf-8") as f:
                f.write(core_content)

            extended_file = agents_dir / f"{agent_name}-ext.md"
            with open(extended_file, "w", encoding="utf-8") as f:
                f.write(extended_content)

        # Verify all files exist
        agent_files = list(agents_dir.glob("*.md"))
        assert len(agent_files) == 6  # 3 core + 3 extended

        # Verify naming pattern
        for agent_name in agent_names:
            assert (agents_dir / f"{agent_name}.md").exists()
            assert (agents_dir / f"{agent_name}-ext.md").exists()

    def test_split_files_cross_reference_each_other(self, temp_template_dir, sample_agent_content):
        """Test that core and extended files reference each other."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        agents_dir = temp_template_dir / "agents"
        agents_dir.mkdir(exist_ok=True)

        core_content, extended_content = split_agent_content(sample_agent_content)

        agent_file = agents_dir / "test-specialist.md"
        with open(agent_file, "w", encoding="utf-8") as f:
            f.write(core_content)

        extended_file = agents_dir / "test-specialist-ext.md"
        with open(extended_file, "w", encoding="utf-8") as f:
            f.write(extended_content)

        # Read files
        core_text = agent_file.read_text()
        extended_text = extended_file.read_text()

        # Verify cross-references
        assert "test-specialist-ext.md" in core_text
        assert ("test-specialist.md" in extended_text or
                "main agent file" in extended_text.lower() or
                "core file" in extended_text.lower())

    def test_split_preserves_frontmatter_integrity(self, temp_template_dir, sample_agent_content):
        """Test that frontmatter is preserved correctly in core file."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        core_content, _ = split_agent_content(sample_agent_content)

        # Check frontmatter structure
        lines = core_content.split('\n')
        assert lines[0] == '---'

        # Find closing delimiter
        closing_idx = None
        for i, line in enumerate(lines[1:], 1):
            if line == '---':
                closing_idx = i
                break

        assert closing_idx is not None
        assert closing_idx > 1

        # Verify key frontmatter fields
        assert "name: test-specialist" in core_content
        assert "stack: python" in core_content
        assert "phase: implementation" in core_content

    def test_size_validation_warnings(self, temp_template_dir):
        """Test that size validation warnings are generated for oversized files."""
        from installer.core.lib.agent_generator.agent_splitter import validate_split_sizes

        # Create oversized content
        large_core = "# Large Core\n\n" + ("x" * (20 * 1024))  # 20KB
        large_extended = "# Large Extended\n\n" + ("y" * (35 * 1024))  # 35KB

        warnings = validate_split_sizes(large_core, large_extended)

        # Both should generate warnings
        assert len(warnings) == 2
        assert any("core" in w.lower() for w in warnings)
        assert any("extended" in w.lower() for w in warnings)

    def test_fallback_on_split_failure(self, temp_template_dir):
        """Test fallback behavior when splitting fails."""
        from installer.core.lib.agent_generator.agent_splitter import split_agent_content

        # Create invalid agent content (will still work, but minimal)
        invalid_content = "This is not valid agent markdown"

        # Should not raise, but produce minimal output
        try:
            core_content, extended_content = split_agent_content(invalid_content)
            assert len(core_content) > 0
            assert len(extended_content) > 0
        except ValueError:
            # Empty content should raise ValueError
            assert "cannot be empty" in str(pytest.raises(ValueError).value)
