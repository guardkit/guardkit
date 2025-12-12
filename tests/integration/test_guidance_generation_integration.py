"""
Integration tests for guidance generation during template-init workflow.

Tests the complete flow from agent files to guidance files in .claude/rules/guidance/
"""

import pytest
from pathlib import Path
import tempfile
import shutil

from installer.core.lib.guidance_generator import (
    generate_guidance_from_agent,
    save_guidance,
)


@pytest.fixture
def temp_template_dir():
    """Create a temporary template directory structure."""
    temp_dir = tempfile.mkdtemp(prefix="test_template_")

    # Create directory structure
    agents_dir = Path(temp_dir) / "agents"
    agents_dir.mkdir(parents=True)

    guidance_dir = Path(temp_dir) / ".claude" / "rules" / "guidance"
    guidance_dir.mkdir(parents=True)

    yield Path(temp_dir)

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_agent_files(temp_template_dir):
    """Create sample agent files for testing."""
    agents_dir = temp_template_dir / "agents"

    # Create a Python API specialist agent
    api_agent = """---
stack: [python, fastapi]
phase: implementation
capabilities: [api, async-patterns, pydantic]
priority: 9
keywords: [fastapi, api, endpoints, pydantic]
---

# FastAPI API Specialist

Expert in building RESTful APIs with FastAPI, async patterns, and Pydantic validation.

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
    # Implementation
    pass
```

## Boundaries

### ALWAYS
- ✅ Use Pydantic models for validation (type safety)
- ✅ Implement async route handlers (non-blocking I/O)
- ✅ Return appropriate HTTP status codes (REST conventions)
- ✅ Add dependency injection for DB connections (testability)
- ✅ Include proper error handling with HTTPException (clear errors)

### NEVER
- ❌ Never use blocking I/O in async routes (deadlock risk)
- ❌ Never skip request validation (security vulnerability)
- ❌ Never hardcode configuration values (environment issues)
- ❌ Never expose internal errors to clients (security leak)
- ❌ Never ignore type hints in models (runtime errors)

### ASK
- ⚠️ Authentication strategy: Ask if OAuth2, JWT, or API keys
- ⚠️ Database ORM choice: Ask if SQLAlchemy, Tortoise, or raw SQL
- ⚠️ Caching layer needed: Ask if Redis, in-memory, or none

## Capabilities

This agent specializes in:
- Building RESTful API endpoints with FastAPI
- Async/await patterns for non-blocking operations
- Pydantic schema validation and serialization

## Integration with GuardKit

- **Phase**: Implementation (Phase 3)
- **When invoked**: Automatically selected for Python API tasks
- **Fallback**: task-manager for general Python tasks
"""

    (agents_dir / "fastapi-api-specialist.md").write_text(api_agent)

    # Create a React testing specialist agent
    testing_agent = """---
stack: [react, typescript]
phase: testing
capabilities: [testing, vitest, playwright]
priority: 8
keywords: [testing, vitest, playwright, react]
---

# React Testing Specialist

Expert in testing React components with Vitest and Playwright.

## Boundaries

### ALWAYS
- ✅ Write unit tests for all components (quality)
- ✅ Use React Testing Library (best practices)
- ✅ Test user interactions (real-world scenarios)
- ✅ Mock external dependencies (isolation)
- ✅ Verify accessibility (inclusive design)

### NEVER
- ❌ Never test implementation details (brittle tests)
- ❌ Never skip edge cases (incomplete coverage)
- ❌ Never use shallow rendering (false confidence)
- ❌ Never ignore console warnings (hidden bugs)
- ❌ Never hardcode test data (maintenance burden)

### ASK
- ⚠️ E2E vs unit tests: Ask which to prioritize
- ⚠️ Coverage threshold: Ask target percentage
- ⚠️ Visual regression: Ask if needed

## Capabilities

This agent specializes in:
- Unit testing React components
- Integration testing with Vitest
- E2E testing with Playwright
"""

    (agents_dir / "react-testing-specialist.md").write_text(testing_agent)

    return {
        "api": agents_dir / "fastapi-api-specialist.md",
        "testing": agents_dir / "react-testing-specialist.md"
    }


def test_full_guidance_generation_flow(temp_template_dir, sample_agent_files):
    """
    Test complete guidance generation during template-init.

    This verifies the entire flow:
    1. Agent files exist in agents/
    2. Guidance files are generated in .claude/rules/guidance/
    3. Guidance files have correct structure
    4. Guidance files are under size limits
    """
    guidance_dir = temp_template_dir / ".claude" / "rules" / "guidance"

    # Generate guidance for each agent
    generated_files = []
    for agent_name, agent_file in sample_agent_files.items():
        # Read agent content
        agent_content = agent_file.read_text()

        # Generate guidance
        guidance_content = generate_guidance_from_agent(
            agent_content,
            agent_file.stem  # Use filename without extension
        )

        # Save guidance
        guidance_file = save_guidance(
            guidance_content,
            str(guidance_dir),
            agent_file.stem
        )

        generated_files.append(guidance_file)

    # Verify guidance files were created
    assert len(list(guidance_dir.glob("*.md"))) >= 2

    # Verify each generated file
    for guidance_file in generated_files:
        assert guidance_file.exists(), f"Guidance file not created: {guidance_file}"

        content = guidance_file.read_text()

        # Check structure
        assert content.startswith("---"), "Missing frontmatter"
        assert "paths:" in content or "agent:" in content, "Missing frontmatter fields"
        assert "## Boundaries" in content, "Missing Boundaries section"
        assert "### ALWAYS" in content, "Missing ALWAYS section"
        assert "### NEVER" in content, "Missing NEVER section"
        assert "### ASK" in content, "Missing ASK section"
        assert "## When to Use" in content, "Missing When to Use section"
        assert "## Full Documentation" in content, "Missing Full Documentation section"

        # Check size
        size_bytes = len(content.encode('utf-8'))
        assert size_bytes < 5 * 1024, f"Guidance file exceeds 5KB: {size_bytes} bytes"


def test_guidance_naming_convention(temp_template_dir, sample_agent_files):
    """
    Test that guidance files follow correct naming convention.

    Verifies that agent 'fastapi-api-specialist' creates guidance file
    with appropriate slug (e.g., 'fastapi-api.md' or similar).
    """
    guidance_dir = temp_template_dir / ".claude" / "rules" / "guidance"

    # Process API specialist
    agent_file = sample_agent_files["api"]
    agent_content = agent_file.read_text()

    guidance_content = generate_guidance_from_agent(
        agent_content,
        agent_file.stem
    )

    guidance_file = save_guidance(
        guidance_content,
        str(guidance_dir),
        agent_file.stem
    )

    # Check filename
    assert guidance_file.name.endswith(".md")
    # Filename should be derived from agent name (specialist removed)
    assert "fastapi-api" in guidance_file.name or "api" in guidance_file.name


def test_guidance_cross_references_agent_files(temp_template_dir, sample_agent_files):
    """
    Test that guidance files correctly reference agent files.

    Verifies that guidance files include links to both:
    - agents/{name}.md
    - agents/{name}-ext.md
    """
    guidance_dir = temp_template_dir / ".claude" / "rules" / "guidance"

    agent_file = sample_agent_files["api"]
    agent_content = agent_file.read_text()
    agent_name = agent_file.stem

    guidance_content = generate_guidance_from_agent(
        agent_content,
        agent_name
    )

    # Check references
    assert f"agents/{agent_name}.md" in guidance_content
    assert f"agents/{agent_name}-ext.md" in guidance_content


def test_guidance_path_patterns_match_agent_stack(temp_template_dir, sample_agent_files):
    """
    Test that path patterns in guidance match agent's stack metadata.

    Verifies:
    - Python/FastAPI agent → **/api/**/*.py or **/*.py patterns
    - React/TypeScript testing agent → **/tests/** or **/*.test.* patterns
    """
    guidance_dir = temp_template_dir / ".claude" / "rules" / "guidance"

    # Test API specialist
    api_agent_file = sample_agent_files["api"]
    api_content = api_agent_file.read_text()
    api_guidance = generate_guidance_from_agent(api_content, api_agent_file.stem)

    # Should have Python/API patterns
    assert "paths:" in api_guidance
    assert "*.py" in api_guidance or "api" in api_guidance.lower()

    # Test testing specialist
    testing_agent_file = sample_agent_files["testing"]
    testing_content = testing_agent_file.read_text()
    testing_guidance = generate_guidance_from_agent(testing_content, testing_agent_file.stem)

    # Should have testing patterns
    assert "paths:" in testing_guidance
    assert "test" in testing_guidance.lower()


def test_guidance_preserves_boundary_rationale(temp_template_dir, sample_agent_files):
    """
    Test that boundary rules preserve rationale in parentheses.

    Verifies that rationale like "(type safety)" is preserved in guidance.
    """
    agent_file = sample_agent_files["api"]
    agent_content = agent_file.read_text()

    guidance_content = generate_guidance_from_agent(
        agent_content,
        agent_file.stem
    )

    # Check that rationale is preserved
    assert "(type safety)" in guidance_content or "type safety" in guidance_content
    assert "(non-blocking I/O)" in guidance_content or "non-blocking" in guidance_content


def test_multiple_agents_no_conflicts(temp_template_dir, sample_agent_files):
    """
    Test that generating guidance for multiple agents doesn't cause conflicts.

    Verifies that each agent gets its own guidance file with no overwrites.
    """
    guidance_dir = temp_template_dir / ".claude" / "rules" / "guidance"

    generated = []
    for agent_name, agent_file in sample_agent_files.items():
        agent_content = agent_file.read_text()
        guidance_content = generate_guidance_from_agent(agent_content, agent_file.stem)
        guidance_file = save_guidance(guidance_content, str(guidance_dir), agent_file.stem)
        generated.append(guidance_file)

    # All files should be unique
    assert len(generated) == len(set(generated))

    # All files should exist
    for gf in generated:
        assert gf.exists()
