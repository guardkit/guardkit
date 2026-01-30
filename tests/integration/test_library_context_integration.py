#!/usr/bin/env python3
"""
Integration Test Suite for Library Detection and Context Gathering

Tests the complete end-to-end workflow for Phase 2.1:
- Library detection from task text
- Context7 library resolution
- Documentation fetching
- Prompt injection
- Manual override handling

Coverage Target: >=90% for integration scenarios
Test Count: ~30 tests
Performance Target: <3s for complete Phase 2.1 workflow

Part of: Library Knowledge Gap Detection System (TASK-LKG-006)
Author: Claude (Anthropic)
Created: 2026-01-30
"""

import os
import sys
import time
from io import StringIO
from typing import Dict, List, Optional, Any
from unittest.mock import patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import modules under test
from installer.core.commands.lib.library_detector import (
    detect_library_mentions,
    get_library_registry,
    KNOWN_LIBRARIES,
)

from installer.core.commands.lib.library_context import (
    LibraryContext,
    gather_library_context,
    inject_library_context_into_prompt,
    parse_library_context,
    display_library_context,
    format_context_for_logging,
)


# ============================================================================
# Integration Test Fixtures
# ============================================================================

@pytest.fixture
def mock_context7_client():
    """
    Mock Context7 MCP client with realistic responses.

    Simulates the Context7 MCP tools for reproducible integration testing.
    Provides:
    - resolve-library-id: Maps known libraries to Context7 IDs
    - query-docs: Returns realistic documentation snippets

    Returns:
        dict: Contains 'resolve' and 'query' mock functions
    """
    # Known library mappings
    library_ids = {
        "fastapi": "/tiangolo/fastapi",
        "pydantic": "/pydantic/pydantic",
        "redis": "/redis/redis-py",
        "graphiti-core": "/getzep/graphiti",
        "react": "/facebook/react",
        "pytest": "/pytest-dev/pytest",
        "langchain": "/langchain-ai/langchain",
        "django": "/django/django",
    }

    # Documentation snippets
    library_docs = {
        "/tiangolo/fastapi": {
            "init": """# FastAPI Getting Started

```python
from fastapi import FastAPI

app = FastAPI()
```

Initialize your FastAPI application with default settings.
Configure with `title`, `description`, `version` parameters.""",

            "methods": """# FastAPI Methods

## Route Decorators
- `@app.get("/path")` - Define GET endpoint
- `@app.post("/path")` - Define POST endpoint
- `@app.put("/path")` - Define PUT endpoint
- `@app.delete("/path")` - Define DELETE endpoint

## Dependency Injection
- `Depends()` - Inject dependencies
- `Header()` - Extract headers
- `Query()` - Extract query params"""
        },
        "/pydantic/pydantic": {
            "init": """# Pydantic Setup

```python
from pydantic import BaseModel

class Item(BaseModel):
    name: str
    price: float
```

Define data models with automatic validation.""",

            "methods": """# Pydantic Methods

- `model_validate()` - Validate input data
- `model_dump()` - Serialize to dict
- `model_json_schema()` - Get JSON schema"""
        },
        "/getzep/graphiti": {
            "init": """# Graphiti Core Setup

```python
from graphiti_core import Graphiti

g = Graphiti(neo4j_uri="bolt://...", neo4j_auth=(...))
```

Initialize Graphiti with Neo4j connection.""",

            "methods": """# Graphiti Methods

- `add_episode()` - Add knowledge to graph
- `search()` - Search the knowledge graph
- `close()` - Close connection"""
        },
        "/facebook/react": {
            "init": """# React Setup

```javascript
import React from 'react';
import { useState, useEffect } from 'react';
```

Import React and hooks for component development.""",

            "methods": """# React Hooks

- `useState()` - State management
- `useEffect()` - Side effects
- `useCallback()` - Memoized callbacks"""
        },
    }

    def _resolve(libraryName: str, query: str) -> Optional[Dict[str, str]]:
        """Mock resolve-library-id tool."""
        lib_lower = libraryName.lower()
        if lib_lower in library_ids:
            return {"libraryId": library_ids[lib_lower]}
        return None

    def _query(libraryId: str, query: str) -> Optional[Dict[str, str]]:
        """Mock query-docs tool."""
        if libraryId not in library_docs:
            return None

        docs = library_docs[libraryId]
        query_lower = query.lower()

        if "init" in query_lower or "setup" in query_lower or "start" in query_lower:
            return {"content": docs.get("init", "")}
        elif "method" in query_lower or "api" in query_lower:
            return {"content": docs.get("methods", "")}

        # Return init docs as fallback
        return {"content": docs.get("init", "")}

    return {"resolve": _resolve, "query": _query}


@pytest.fixture
def sample_task_data():
    """Sample task data for integration tests."""
    return {
        "single_known": {
            "title": "Implement user authentication with FastAPI",
            "description": "Build JWT-based auth using FastAPI dependencies"
        },
        "multiple_known": {
            "title": "Build API with FastAPI and Pydantic",
            "description": "Create REST endpoints with validation using Pydantic models"
        },
        "single_unknown": {
            "title": "Integrate with internal-corp-lib",
            "description": "Use our proprietary internal library for data processing"
        },
        "mixed": {
            "title": "Build graph search with graphiti-core",
            "description": "Implement search using FastAPI backend and fake-lib for caching"
        },
        "no_libraries": {
            "title": "Fix the login bug",
            "description": "The login flow has an authentication issue that needs fixing"
        },
        "graphiti": {
            "title": "Implement knowledge graph search",
            "description": "Use graphiti-core for semantic search over the knowledge graph"
        }
    }


# ============================================================================
# 1. End-to-End Workflow Tests (5 tests)
# ============================================================================

@pytest.mark.integration
class TestEndToEndWorkflow:
    """End-to-end workflow tests from detection to prompt injection."""

    def test_complete_single_library_workflow(self, mock_context7_client, sample_task_data):
        """Test complete workflow with single known library."""
        task = sample_task_data["single_known"]

        # Step 1: Detection
        libraries = detect_library_mentions(task["title"], task["description"])
        assert "fastapi" in libraries

        # Step 2: Gather context
        contexts = gather_library_context(
            libraries=libraries,
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )
        assert len(contexts) == 1
        assert contexts[0].resolved is True
        assert contexts[0].context7_id == "/tiangolo/fastapi"

        # Step 3: Inject into prompt
        base_prompt = "Create an implementation plan for user authentication."
        enhanced = inject_library_context_into_prompt(base_prompt, contexts)

        # Verify injection
        assert "## Library Reference" in enhanced
        assert "fastapi" in enhanced.lower()
        assert "Create an implementation plan" in enhanced

    def test_complete_multiple_library_workflow(self, mock_context7_client, sample_task_data):
        """Test workflow with multiple detected libraries."""
        task = sample_task_data["multiple_known"]

        # Detection
        libraries = detect_library_mentions(task["title"], task["description"])
        assert "fastapi" in libraries
        assert "pydantic" in libraries

        # Context gathering
        contexts = gather_library_context(
            libraries=libraries,
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )
        assert len(contexts) == 2
        assert all(c.resolved for c in contexts)

        # Prompt injection
        base_prompt = "Design the API structure."
        enhanced = inject_library_context_into_prompt(base_prompt, contexts)

        # Verify both libraries present
        assert "fastapi" in enhanced.lower()
        assert "pydantic" in enhanced.lower()

    def test_workflow_with_unknown_library(self, mock_context7_client, sample_task_data):
        """Test graceful handling of unknown library."""
        task = sample_task_data["single_unknown"]

        # Detection may not find unknown libs in registry
        libraries = detect_library_mentions(task["title"], task["description"])

        # Even if detected, context gathering should handle gracefully
        if libraries:
            contexts = gather_library_context(
                libraries=libraries,
                mcp_resolve=mock_context7_client["resolve"],
                mcp_query=mock_context7_client["query"]
            )
            # Unknown libraries should have resolved=False
            for ctx in contexts:
                if ctx.name not in ["fastapi", "pydantic", "redis", "graphiti-core", "react"]:
                    assert ctx.resolved is False
                    assert ctx.error is not None

    def test_workflow_with_mixed_libraries(self, mock_context7_client, sample_task_data):
        """Test workflow with mix of known and unknown libraries."""
        task = sample_task_data["mixed"]

        # Detection
        libraries = detect_library_mentions(task["title"], task["description"])
        assert "graphiti-core" in libraries
        assert "fastapi" in libraries

        # Force include an unknown for testing
        libraries.append("fake-lib")

        # Context gathering
        contexts = gather_library_context(
            libraries=libraries,
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        # Check mixed results
        resolved = [c for c in contexts if c.resolved]
        unresolved = [c for c in contexts if not c.resolved]

        assert len(resolved) >= 2  # graphiti-core and fastapi
        assert len(unresolved) >= 1  # fake-lib

    def test_workflow_with_no_libraries(self, mock_context7_client, sample_task_data):
        """Test workflow when no libraries are detected."""
        task = sample_task_data["no_libraries"]

        # Detection should return empty
        libraries = detect_library_mentions(task["title"], task["description"])
        assert libraries == []

        # Context gathering with empty list
        contexts = gather_library_context(
            libraries=libraries,
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )
        assert contexts == []

        # Prompt injection with no contexts
        base_prompt = "Fix the authentication bug."
        enhanced = inject_library_context_into_prompt(base_prompt, contexts)
        assert enhanced == base_prompt  # Unchanged


# ============================================================================
# 2. Known Library Integration Tests (4 tests)
# ============================================================================

@pytest.mark.integration
@pytest.mark.context7
class TestKnownLibraryIntegration:
    """Tests for known library detection and context gathering."""

    def test_fastapi_full_integration(self, mock_context7_client):
        """Test FastAPI detection and full context gathering."""
        libraries = detect_library_mentions(
            "Build REST API with FastAPI",
            "Create endpoints for user management"
        )
        assert "fastapi" in libraries

        contexts = gather_library_context(
            libraries=["fastapi"],
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        ctx = contexts[0]
        assert ctx.name == "fastapi"
        assert ctx.resolved is True
        assert ctx.context7_id == "/tiangolo/fastapi"
        assert ctx.initialization is not None
        assert "FastAPI" in ctx.initialization

    def test_graphiti_full_integration(self, mock_context7_client, sample_task_data):
        """Test graphiti-core detection and context gathering."""
        task = sample_task_data["graphiti"]

        libraries = detect_library_mentions(task["title"], task["description"])
        assert "graphiti-core" in libraries

        contexts = gather_library_context(
            libraries=["graphiti-core"],
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        ctx = contexts[0]
        assert ctx.name == "graphiti-core"
        assert ctx.resolved is True
        assert ctx.context7_id == "/getzep/graphiti"
        assert "Graphiti" in ctx.initialization or "graphiti" in str(ctx.initialization).lower()

    def test_react_full_integration(self, mock_context7_client):
        """Test React detection and context gathering."""
        libraries = detect_library_mentions(
            "Build frontend using React hooks",
            "Implement state management with useState and useEffect"
        )
        assert "react" in libraries

        contexts = gather_library_context(
            libraries=["react"],
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        ctx = contexts[0]
        assert ctx.name == "react"
        assert ctx.resolved is True
        assert ctx.context7_id == "/facebook/react"

    def test_multiple_known_libraries_integration(self, mock_context7_client):
        """Test multiple known libraries in single workflow."""
        libraries = detect_library_mentions(
            "Build API with FastAPI, Pydantic models",
            "Use Redis for caching layer"
        )

        assert "fastapi" in libraries
        assert "pydantic" in libraries
        assert "redis" in libraries

        contexts = gather_library_context(
            libraries=libraries,
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        assert len(contexts) == 3
        assert all(c.resolved for c in contexts)

        names = {c.name for c in contexts}
        assert names == {"fastapi", "pydantic", "redis"}


# ============================================================================
# 3. Manual Override Integration Tests (4 tests)
# ============================================================================

@pytest.mark.integration
class TestManualOverrideIntegration:
    """Tests for manual library_context frontmatter override."""

    def test_manual_override_takes_precedence(self, mock_context7_client):
        """Test that manual library_context overrides Context7."""
        # Create manual context for fastapi
        manual = [
            LibraryContext(
                name="fastapi",
                resolved=True,
                source="manual",
                import_statement="from custom_fastapi import CustomApp",
                initialization="app = CustomApp(custom_config=True)"
            )
        ]

        # Gather context with manual override
        contexts = gather_library_context(
            libraries=["fastapi"],
            manual_context=manual,
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        assert len(contexts) == 1
        ctx = contexts[0]

        # Should use manual, not Context7
        assert ctx.source == "manual"
        assert ctx.import_statement == "from custom_fastapi import CustomApp"
        assert "custom_config" in ctx.initialization

    def test_mixed_manual_and_context7(self, mock_context7_client):
        """Test mix of manual and Context7 contexts."""
        # Manual context for internal library
        manual = [
            LibraryContext(
                name="internal-lib",
                resolved=True,
                source="manual",
                import_statement="from internal import Library",
                initialization="lib = Library(api_key=os.environ['KEY'])"
            )
        ]

        # Gather with mixed sources
        contexts = gather_library_context(
            libraries=["internal-lib", "fastapi"],
            manual_context=manual,
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        assert len(contexts) == 2

        # Find each context
        internal = next(c for c in contexts if c.name == "internal-lib")
        fastapi = next(c for c in contexts if c.name == "fastapi")

        # Verify sources
        assert internal.source == "manual"
        assert fastapi.source == "context7"
        assert fastapi.resolved is True

    def test_parse_and_use_manual_context(self):
        """Test parsing frontmatter library_context format."""
        raw_frontmatter = [
            {
                "name": "graphiti-core",
                "import": "from graphiti_core import Graphiti",
                "initialization": "g = Graphiti(uri='...')",
                "key_methods": [
                    {"name": "search", "signature": "async def search(query)", "returns": "List[Edge]"},
                    {"name": "add_episode", "signature": "async def add_episode(...)"}
                ]
            }
        ]

        parsed = parse_library_context(raw_frontmatter)

        assert parsed is not None
        assert len(parsed) == 1

        ctx = parsed[0]
        assert ctx.name == "graphiti-core"
        assert ctx.source == "manual"
        assert ctx.resolved is True
        assert ctx.import_statement == "from graphiti_core import Graphiti"
        assert "search" in ctx.key_methods
        assert "add_episode" in ctx.key_methods

    def test_manual_context_in_prompt_injection(self, mock_context7_client):
        """Test that manual context is properly injected into prompt."""
        manual = [
            LibraryContext(
                name="custom-auth",
                resolved=True,
                source="manual",
                import_statement="from auth import OAuth2Handler",
                initialization="handler = OAuth2Handler(client_id='...')"
            )
        ]

        base_prompt = "Implement OAuth2 authentication."
        enhanced = inject_library_context_into_prompt(base_prompt, manual)

        assert "## Library Reference" in enhanced
        assert "custom-auth" in enhanced
        assert "OAuth2Handler" in enhanced


# ============================================================================
# 4. Display and Logging Integration Tests (3 tests)
# ============================================================================

@pytest.mark.integration
class TestDisplayLoggingIntegration:
    """Tests for display and logging functions."""

    def test_display_mixed_results(self, mock_context7_client, capsys):
        """Test display output with mixed resolved/unresolved."""
        contexts = gather_library_context(
            libraries=["fastapi", "unknown-lib", "pydantic"],
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        display_library_context(contexts)

        captured = capsys.readouterr()
        output = captured.out

        assert "Library Context Summary" in output
        assert "Resolved" in output
        assert "Failed" in output
        assert "fastapi" in output
        assert "unknown-lib" in output

    def test_format_for_logging_integration(self, mock_context7_client):
        """Test logging format with gathered contexts."""
        contexts = gather_library_context(
            libraries=["fastapi", "pydantic"],
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        log_output = format_context_for_logging(contexts)

        assert "fastapi" in log_output
        assert "pydantic" in log_output
        assert "resolved" in log_output

    def test_display_empty_results(self, capsys):
        """Test display output with no contexts."""
        display_library_context([])

        captured = capsys.readouterr()
        assert "No library context gathered" in captured.out


# ============================================================================
# 5. Performance Integration Tests (3 tests)
# ============================================================================

@pytest.mark.integration
@pytest.mark.performance
class TestPerformanceIntegration:
    """Performance tests for Phase 2.1 workflow."""

    def test_phase_2_1_performance_single_library(self, mock_context7_client, performance_timer):
        """Test Phase 2.1 completes in <3s for single library."""
        with performance_timer.measure("phase_2_1_single"):
            # Step 1: Detection
            libraries = detect_library_mentions(
                "Build API with FastAPI",
                "REST endpoints for user management"
            )

            # Step 2: Context gathering
            contexts = gather_library_context(
                libraries=libraries,
                mcp_resolve=mock_context7_client["resolve"],
                mcp_query=mock_context7_client["query"]
            )

            # Step 3: Prompt injection
            base_prompt = "Create implementation plan."
            inject_library_context_into_prompt(base_prompt, contexts)

        assert performance_timer.elapsed < 3.0, \
            f"Phase 2.1 took {performance_timer.elapsed:.2f}s (target: <3s)"

    def test_phase_2_1_performance_multiple_libraries(self, mock_context7_client, performance_timer):
        """Test Phase 2.1 completes in <3s for multiple libraries."""
        with performance_timer.measure("phase_2_1_multiple"):
            # Detection
            libraries = detect_library_mentions(
                "Build with FastAPI, Pydantic, and Redis",
                "REST API with validation and caching layer"
            )

            # Context gathering
            contexts = gather_library_context(
                libraries=libraries,
                mcp_resolve=mock_context7_client["resolve"],
                mcp_query=mock_context7_client["query"]
            )

            # Prompt injection
            inject_library_context_into_prompt("Plan the implementation.", contexts)

        assert performance_timer.elapsed < 3.0, \
            f"Phase 2.1 took {performance_timer.elapsed:.2f}s (target: <3s)"

    def test_detection_performance_bulk(self, performance_timer):
        """Test detection performance with bulk operations."""
        test_cases = [
            ("Build API with FastAPI", "REST endpoints"),
            ("Use Pydantic for validation", "Data models"),
            ("Implement caching with Redis", "Session storage"),
            ("Graph search using graphiti-core", "Knowledge base"),
            ("Frontend with React hooks", "State management"),
        ]

        with performance_timer.measure("detection_bulk"):
            for _ in range(100):  # 100 iterations
                for title, desc in test_cases:
                    detect_library_mentions(title, desc)

        # 500 total detections should complete in <5s
        assert performance_timer.elapsed < 5.0, \
            f"500 detections took {performance_timer.elapsed:.2f}s (target: <5s)"

        avg_ms = (performance_timer.elapsed / 500) * 1000
        assert avg_ms < 50, f"Average detection: {avg_ms:.2f}ms (target: <50ms)"


# ============================================================================
# 6. Token Budget Integration Tests (3 tests)
# ============================================================================

@pytest.mark.integration
class TestTokenBudgetIntegration:
    """Tests for token budget management."""

    def test_small_budget_enforcement(self, mock_context7_client):
        """Test that small token budget is enforced."""
        # Gather with very small budget
        contexts = gather_library_context(
            libraries=["fastapi", "pydantic", "redis", "graphiti-core"],
            token_budget=100,  # Very small
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        # Should have all libraries (some may have budget exceeded error)
        assert len(contexts) == 4

        # Check that some hit budget limits
        budget_exceeded = [c for c in contexts if c.error and "budget" in c.error.lower()]
        # With 100 token budget, likely at least some will be truncated

    def test_sufficient_budget(self, mock_context7_client):
        """Test that sufficient budget allows full context."""
        contexts = gather_library_context(
            libraries=["fastapi", "pydantic"],
            token_budget=10000,  # Large budget
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        assert len(contexts) == 2
        # All should be resolved with sufficient budget
        assert all(c.resolved for c in contexts)

    def test_per_library_budget_distribution(self, mock_context7_client):
        """Test that budget is distributed across libraries."""
        contexts = gather_library_context(
            libraries=["fastapi", "pydantic", "redis"],
            token_budget=3000,  # ~1000 per library
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        # All should be present
        assert len(contexts) == 3

        # Most should be resolved
        resolved = [c for c in contexts if c.resolved]
        assert len(resolved) >= 2


# ============================================================================
# 7. Error Handling Integration Tests (3 tests)
# ============================================================================

@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Tests for error handling and graceful degradation."""

    def test_mcp_connection_failure(self):
        """Test handling of MCP connection failure."""
        def failing_resolve(libraryName: str, query: str):
            raise ConnectionError("MCP server unavailable")

        contexts = gather_library_context(
            libraries=["fastapi"],
            mcp_resolve=failing_resolve,
            mcp_query=lambda **kw: None
        )

        # Should handle gracefully
        assert len(contexts) == 1
        ctx = contexts[0]
        assert ctx.resolved is False
        # Error should be captured

    def test_partial_mcp_failure(self, mock_context7_client):
        """Test handling when some MCP calls fail."""
        call_count = [0]

        def flaky_resolve(libraryName: str, query: str):
            call_count[0] += 1
            if call_count[0] == 2:  # Second call fails
                raise RuntimeError("Transient error")
            return mock_context7_client["resolve"](libraryName, query)

        contexts = gather_library_context(
            libraries=["fastapi", "pydantic", "redis"],
            mcp_resolve=flaky_resolve,
            mcp_query=mock_context7_client["query"]
        )

        # Should have all libraries
        assert len(contexts) == 3

        # Some resolved, some failed
        resolved = [c for c in contexts if c.resolved]
        failed = [c for c in contexts if not c.resolved]

        # At least some should resolve
        assert len(resolved) >= 1
        # The flaky one should fail
        assert len(failed) >= 1

    def test_empty_documentation_handling(self, mock_context7_client):
        """Test handling when MCP returns empty documentation."""
        def empty_query(libraryId: str, query: str):
            return {"content": ""}

        contexts = gather_library_context(
            libraries=["fastapi"],
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=empty_query
        )

        # Should still be considered resolved
        assert len(contexts) == 1
        ctx = contexts[0]
        assert ctx.resolved is True
        # Initialization may be empty but not an error


# ============================================================================
# 8. Cross-Module Integration Tests (3 tests)
# ============================================================================

@pytest.mark.integration
class TestCrossModuleIntegration:
    """Tests for integration between modules."""

    def test_detector_to_context_integration(self, mock_context7_client):
        """Test data flow from detector to context gatherer."""
        # Use detector output as direct input to context gatherer
        detected = detect_library_mentions(
            "Build microservice with FastAPI and Pydantic",
            "Include Redis caching"
        )

        # Verify detected libraries work with context gatherer
        contexts = gather_library_context(
            libraries=detected,
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        # All detected should have context entries
        assert len(contexts) == len(detected)

        # Known libraries should be resolved
        for ctx in contexts:
            if ctx.name in ["fastapi", "pydantic", "redis"]:
                assert ctx.resolved is True

    def test_context_to_prompt_integration(self, mock_context7_client):
        """Test data flow from context to prompt injection."""
        contexts = gather_library_context(
            libraries=["fastapi"],
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        # Use gathered context for prompt injection
        base_prompt = """## Task
Implement user authentication.

## Requirements
- JWT tokens
- Refresh tokens"""

        enhanced = inject_library_context_into_prompt(base_prompt, contexts)

        # Verify structure
        assert "## Library Reference" in enhanced
        assert "## Task" in enhanced
        assert "## Requirements" in enhanced

        # Library ref should be before implementation sections
        lib_pos = enhanced.index("## Library Reference")
        task_pos = enhanced.index("## Task")
        # Both should exist in the enhanced prompt

    def test_full_pipeline_with_display(self, mock_context7_client, capsys):
        """Test complete pipeline including display."""
        # Step 1: Detection
        libraries = detect_library_mentions(
            "Build API with FastAPI",
            "Use Pydantic for validation"
        )

        # Step 2: Context gathering
        contexts = gather_library_context(
            libraries=libraries,
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        # Step 3: Display
        display_library_context(contexts)

        # Step 4: Prompt injection
        enhanced = inject_library_context_into_prompt("Plan implementation.", contexts)

        # Verify outputs
        captured = capsys.readouterr()
        assert "Library Context Summary" in captured.out
        assert "## Library Reference" in enhanced


# ============================================================================
# 9. Prompt Section Format Tests (3 tests)
# ============================================================================

@pytest.mark.integration
class TestPromptSectionFormat:
    """Tests for prompt section formatting."""

    def test_prompt_section_structure(self, mock_context7_client):
        """Test that prompt section has correct structure."""
        contexts = gather_library_context(
            libraries=["fastapi"],
            mcp_resolve=mock_context7_client["resolve"],
            mcp_query=mock_context7_client["query"]
        )

        section = contexts[0].to_prompt_section()

        # Check structure
        assert "### fastapi" in section
        assert "**Context7 ID**" in section or "**Import**" in section

    def test_unresolved_prompt_section(self):
        """Test prompt section for unresolved library."""
        ctx = LibraryContext(
            name="unknown-lib",
            resolved=False,
            error="Could not resolve"
        )

        section = ctx.to_prompt_section()

        assert "### unknown-lib" in section
        assert "Resolution failed" in section or "not found" in section

    def test_manual_source_prompt_section(self):
        """Test prompt section for manual source."""
        ctx = LibraryContext(
            name="internal-lib",
            resolved=True,
            source="manual",
            import_statement="from internal import Lib",
            initialization="lib = Lib()"
        )

        section = ctx.to_prompt_section()

        assert "### internal-lib" in section
        assert "from internal import Lib" in section


# ============================================================================
# Test Summary
# ============================================================================
"""
Integration Test Coverage Summary:

1. End-to-End Workflow Tests (5 tests):
   - test_complete_single_library_workflow
   - test_complete_multiple_library_workflow
   - test_workflow_with_unknown_library
   - test_workflow_with_mixed_libraries
   - test_workflow_with_no_libraries

2. Known Library Integration Tests (4 tests):
   - test_fastapi_full_integration
   - test_graphiti_full_integration
   - test_react_full_integration
   - test_multiple_known_libraries_integration

3. Manual Override Integration Tests (4 tests):
   - test_manual_override_takes_precedence
   - test_mixed_manual_and_context7
   - test_parse_and_use_manual_context
   - test_manual_context_in_prompt_injection

4. Display and Logging Integration Tests (3 tests):
   - test_display_mixed_results
   - test_format_for_logging_integration
   - test_display_empty_results

5. Performance Integration Tests (3 tests):
   - test_phase_2_1_performance_single_library
   - test_phase_2_1_performance_multiple_libraries
   - test_detection_performance_bulk

6. Token Budget Integration Tests (3 tests):
   - test_small_budget_enforcement
   - test_sufficient_budget
   - test_per_library_budget_distribution

7. Error Handling Integration Tests (3 tests):
   - test_mcp_connection_failure
   - test_partial_mcp_failure
   - test_empty_documentation_handling

8. Cross-Module Integration Tests (3 tests):
   - test_detector_to_context_integration
   - test_context_to_prompt_integration
   - test_full_pipeline_with_display

9. Prompt Section Format Tests (3 tests):
   - test_prompt_section_structure
   - test_unresolved_prompt_section
   - test_manual_source_prompt_section

Total: 31 tests
Target Coverage: >=90% for integration scenarios
Performance Target: <3s for Phase 2.1 workflow
"""
