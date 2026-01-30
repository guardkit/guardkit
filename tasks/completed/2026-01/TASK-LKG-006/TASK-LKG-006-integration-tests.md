---
id: TASK-LKG-006
title: Integration tests for library detection and context gathering
status: completed
created: 2026-01-30
updated: 2026-01-30
completed: 2026-01-30
priority: medium
complexity: 4
tags: [testing, integration, quality-gate]
parent_review: TASK-REV-668B
feature_id: library-knowledge-gap
implementation_mode: task-work
wave: 3
conductor_workspace: library-knowledge-gap-wave3-tests
depends_on:
  - TASK-LKG-001
  - TASK-LKG-002
  - TASK-LKG-003
---

# TASK-LKG-006: Integration Tests for Library Detection

## Description

Create comprehensive integration tests that verify the end-to-end library detection and Context7 fetching workflow. These tests ensure the Phase 2.1 implementation works correctly in real-world scenarios.

## Acceptance Criteria

- [x] End-to-end test for detection → resolution → fetching
- [x] Tests for known libraries (fastapi, react, graphiti-core)
- [x] Tests for unknown libraries (graceful failure)
- [x] Tests for mixed scenarios (some resolve, some don't)
- [x] Tests for manual library_context override
- [x] Tests for prompt injection format
- [x] Performance tests (<3s for Phase 2.1)
- [x] CI/CD integration (pytest markers)

## Implementation Notes

### File Location

```
tests/integration/test_library_context.py
```

### Test Categories

#### 1. Detection Tests

```python
import pytest
from installer.core.commands.lib.library_detector import detect_library_mentions

class TestLibraryDetection:
    """Test library name detection from task text."""

    def test_detect_known_library_in_title(self):
        """Detect library mentioned directly in title."""
        result = detect_library_mentions(
            "Implement search with graphiti-core",
            ""
        )
        assert "graphiti-core" in result

    def test_detect_using_pattern(self):
        """Detect 'using X' pattern."""
        result = detect_library_mentions(
            "Add caching using Redis",
            ""
        )
        assert "redis" in result

    def test_detect_with_pattern(self):
        """Detect 'with X' pattern."""
        result = detect_library_mentions(
            "Build authentication with PyJWT",
            ""
        )
        assert "pyjwt" in result

    def test_detect_multiple_libraries(self):
        """Detect multiple libraries."""
        result = detect_library_mentions(
            "Create API with FastAPI and Pydantic validation",
            ""
        )
        assert "fastapi" in result
        assert "pydantic" in result

    def test_no_false_positives_common_words(self):
        """Don't detect common words as libraries."""
        result = detect_library_mentions(
            "Fix the login bug and add tests",
            ""
        )
        assert result == []

    def test_no_false_positives_task_actions(self):
        """Don't detect task action words."""
        result = detect_library_mentions(
            "Update the service and refactor the code",
            ""
        )
        assert result == []

    def test_case_insensitive(self):
        """Detection is case insensitive."""
        result = detect_library_mentions(
            "Using FASTAPI for the API",
            ""
        )
        assert "fastapi" in result

    def test_detect_in_description(self):
        """Detect libraries in description, not just title."""
        result = detect_library_mentions(
            "Add search feature",
            "This should use the graphiti-core library for knowledge graph search."
        )
        assert "graphiti-core" in result
```

#### 2. Context7 Integration Tests

```python
@pytest.mark.integration
@pytest.mark.context7
class TestContext7Integration:
    """Test Context7 MCP integration (requires Context7 to be available)."""

    def test_resolve_known_library(self):
        """Resolve a known library to Context7 ID."""
        from installer.core.commands.lib.library_context import resolve_library

        lib_id = resolve_library("fastapi")
        assert lib_id is not None
        assert "fastapi" in lib_id.lower()

    def test_resolve_unknown_library(self):
        """Graceful handling of unknown library."""
        from installer.core.commands.lib.library_context import resolve_library

        lib_id = resolve_library("nonexistent-library-xyz-12345")
        assert lib_id is None

    def test_fetch_library_docs(self):
        """Fetch documentation for a resolved library."""
        from installer.core.commands.lib.library_context import gather_library_context

        contexts = gather_library_context(["fastapi"])

        assert "fastapi" in contexts
        assert contexts["fastapi"].resolved
        assert contexts["fastapi"].import_statement is not None

    def test_fetch_with_specific_topic(self):
        """Fetch documentation with topic filter."""
        from installer.core.commands.lib.library_context import gather_library_context

        # This would use query_docs with topic parameter
        contexts = gather_library_context(["pytest"], topic="fixtures")

        assert "pytest" in contexts
        assert contexts["pytest"].resolved
```

#### 3. End-to-End Tests

```python
@pytest.mark.integration
class TestEndToEnd:
    """End-to-end tests for the complete workflow."""

    def test_full_workflow_known_library(self):
        """Complete workflow: detect → resolve → fetch → inject."""
        from installer.core.commands.lib.library_detector import detect_library_mentions
        from installer.core.commands.lib.library_context import (
            gather_library_context,
            inject_library_context_into_prompt
        )

        # Step 1: Detection
        task_title = "Implement search with graphiti-core"
        task_description = "Create a search interface using the graphiti-core library"

        libraries = detect_library_mentions(task_title, task_description)
        assert "graphiti-core" in libraries

        # Step 2: Gather context
        contexts = gather_library_context(libraries)
        assert "graphiti-core" in contexts

        # Step 3: Inject into prompt
        base_prompt = "Design implementation approach for TASK-001."
        enhanced_prompt = inject_library_context_into_prompt(base_prompt, contexts)

        assert "LIBRARY CONTEXT" in enhanced_prompt
        assert "graphiti-core" in enhanced_prompt

    def test_full_workflow_unknown_library(self):
        """Workflow continues gracefully with unknown library."""
        from installer.core.commands.lib.library_detector import detect_library_mentions
        from installer.core.commands.lib.library_context import gather_library_context

        libraries = detect_library_mentions(
            "Integrate with internal-corp-lib",
            "Use our internal library"
        )

        # May or may not detect depending on patterns
        contexts = gather_library_context(libraries)

        # Workflow should not fail
        # Unresolved libraries should have error message
        for name, ctx in contexts.items():
            if not ctx.resolved:
                assert ctx.error is not None

    def test_full_workflow_mixed_libraries(self):
        """Mix of known and unknown libraries."""
        libraries = ["fastapi", "internal-unknown-lib"]
        contexts = gather_library_context(libraries)

        assert contexts["fastapi"].resolved
        assert not contexts["internal-unknown-lib"].resolved
```

#### 4. Manual Override Tests

```python
class TestManualOverride:
    """Test manual library_context frontmatter override."""

    def test_manual_context_takes_precedence(self):
        """Manual library_context overrides Context7."""
        from installer.core.commands.lib.library_context import (
            gather_library_context,
            LibraryContext
        )

        manual = {
            "fastapi": LibraryContext(
                name="fastapi",
                context7_id=None,
                resolved=True,
                import_statement="from custom_fastapi import CustomApp",
                source="manual"
            )
        }

        contexts = gather_library_context(["fastapi"], manual_context=manual)

        assert contexts["fastapi"].import_statement == "from custom_fastapi import CustomApp"
        assert contexts["fastapi"].source == "manual"

    def test_mixed_manual_and_context7(self):
        """Some libraries manual, some from Context7."""
        from installer.core.commands.lib.library_context import (
            gather_library_context,
            LibraryContext
        )

        manual = {
            "internal-lib": LibraryContext(
                name="internal-lib",
                context7_id=None,
                resolved=True,
                import_statement="from internal import Lib",
                source="manual"
            )
        }

        contexts = gather_library_context(
            ["internal-lib", "fastapi"],
            manual_context=manual
        )

        assert contexts["internal-lib"].source == "manual"
        # fastapi should come from Context7 (if available)
```

#### 5. Performance Tests

```python
@pytest.mark.performance
class TestPerformance:
    """Performance tests for Phase 2.1."""

    def test_detection_performance(self):
        """Detection should complete in <50ms."""
        import time

        start = time.perf_counter()
        for _ in range(100):
            detect_library_mentions(
                "Implement feature with FastAPI and Pydantic",
                "Description with Redis and PyJWT mentions"
            )
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / 100) * 1000
        assert avg_ms < 50, f"Detection took {avg_ms:.2f}ms (threshold: 50ms)"

    @pytest.mark.integration
    def test_context_gathering_performance(self):
        """Context gathering should complete in <3s for 2 libraries."""
        import time

        start = time.perf_counter()
        gather_library_context(["fastapi", "pydantic"])
        elapsed = time.perf_counter() - start

        assert elapsed < 3.0, f"Context gathering took {elapsed:.2f}s (threshold: 3s)"
```

### Pytest Configuration

```python
# conftest.py additions

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "context7: marks tests requiring Context7 MCP"
    )
    config.addinivalue_line(
        "markers", "performance: marks performance tests"
    )

@pytest.fixture
def mock_context7():
    """Mock Context7 for unit tests that shouldn't hit real MCP."""
    with patch('installer.core.commands.lib.library_context.mcp__context7__resolve_library_id') as mock_resolve:
        with patch('installer.core.commands.lib.library_context.mcp__context7__query_docs') as mock_docs:
            mock_resolve.return_value = "/mock/library"
            mock_docs.return_value = "Mock documentation"
            yield {"resolve": mock_resolve, "docs": mock_docs}
```

### CI/CD Configuration

```yaml
# In GitHub Actions or similar
- name: Run unit tests
  run: pytest tests/ -m "not integration" --cov

- name: Run integration tests
  run: pytest tests/ -m "integration" --cov
  env:
    CONTEXT7_AVAILABLE: "true"

- name: Run performance tests
  run: pytest tests/ -m "performance"
```

## Notes

- Integration tests require Context7 MCP to be available
- Use mocks for unit tests that shouldn't hit real services
- Performance tests ensure Phase 2.1 doesn't slow down workflow
- CI/CD should run integration tests separately from unit tests
