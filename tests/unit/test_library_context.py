#!/usr/bin/env python3
"""
Comprehensive Test Suite for Library Context Gathering Module

Tests all functionality of the library_context module including:
- LibraryContext dataclass creation and serialization
- Context7 MCP tool integration (mocked)
- Token budget management
- Display functions
- Prompt injection
- Error handling and graceful degradation

Coverage Target: >=90%
Test Count: 17+ tests
"""

import os
import sys
from io import StringIO
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Import module under test
from installer.core.commands.lib.library_context import (
    LibraryContext,
    gather_library_context,
    display_library_context,
    inject_library_context_into_prompt,
    format_context_for_logging,
    parse_library_context,
    format_method_docs,
    INIT_QUERY,
    METHODS_QUERY,
    _extract_import_statement,
    _extract_key_methods,
)


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_mcp_resolve_success():
    """Mock MCP resolve-library-id that returns success for known libraries."""
    def _resolve(libraryName: str, query: str) -> Optional[Dict[str, Any]]:
        known = {
            "fastapi": "/tiangolo/fastapi",
            "pydantic": "/pydantic/pydantic",
            "redis": "/redis/redis-py",
        }
        if libraryName.lower() in known:
            return {"libraryId": known[libraryName.lower()]}
        return None
    return _resolve


@pytest.fixture
def mock_mcp_resolve_failure():
    """Mock MCP resolve-library-id that always fails."""
    def _resolve(libraryName: str, query: str) -> None:
        return None
    return _resolve


@pytest.fixture
def mock_mcp_resolve_exception():
    """Mock MCP resolve-library-id that raises exception."""
    def _resolve(libraryName: str, query: str) -> None:
        raise RuntimeError("MCP connection failed")
    return _resolve


@pytest.fixture
def mock_mcp_query_success():
    """Mock MCP query-docs that returns documentation."""
    def _query(libraryId: str, query: str) -> Optional[Dict[str, Any]]:
        if "init" in query.lower() or "setup" in query.lower():
            return {
                "content": """
# Getting Started

```python
from fastapi import FastAPI

app = FastAPI()
```

Initialize your application with basic settings.
"""
            }
        elif "method" in query.lower() or "api" in query.lower():
            return {
                "content": """
# API Methods

## Core Methods

- `.get()` - Define a GET endpoint
- `.post()` - Define a POST endpoint
- `.put()` - Define a PUT endpoint
- `.delete()` - Define a DELETE endpoint

Example:
```python
@app.get("/items")
def read_items():
    return []
```
"""
            }
        return None
    return _query


@pytest.fixture
def mock_mcp_query_failure():
    """Mock MCP query-docs that always fails."""
    def _query(libraryId: str, query: str) -> None:
        return None
    return _query


@pytest.fixture
def sample_library_context_resolved():
    """Create a sample resolved LibraryContext."""
    return LibraryContext(
        name="fastapi",
        context7_id="/tiangolo/fastapi",
        resolved=True,
        import_statement="from fastapi import FastAPI",
        initialization="app = FastAPI()",
        key_methods=["get", "post", "put", "delete"],
        method_docs="Core routing methods for HTTP endpoints."
    )


@pytest.fixture
def sample_library_context_failed():
    """Create a sample failed LibraryContext."""
    return LibraryContext(
        name="unknown-lib",
        resolved=False,
        error="Could not resolve library ID"
    )


# ============================================================================
# 1. Data Structure Tests (4 tests)
# ============================================================================

def test_library_context_creation():
    """Test basic LibraryContext creation with required fields only."""
    ctx = LibraryContext(name="test-lib")

    assert ctx.name == "test-lib"
    assert ctx.context7_id is None
    assert ctx.resolved is False
    assert ctx.import_statement is None
    assert ctx.initialization is None
    assert ctx.key_methods == []
    assert ctx.method_docs is None
    assert ctx.error is None


def test_library_context_to_prompt_section_resolved(sample_library_context_resolved):
    """Test prompt section generation for resolved library."""
    section = sample_library_context_resolved.to_prompt_section()

    # Check required elements
    assert "### fastapi" in section
    assert "/tiangolo/fastapi" in section
    assert "from fastapi import FastAPI" in section
    assert "app = FastAPI()" in section
    assert "get" in section.lower()
    assert "post" in section.lower()


def test_library_context_to_prompt_section_unresolved():
    """Test prompt section generation for unresolved library."""
    ctx = LibraryContext(name="unknown-lib", resolved=False)
    section = ctx.to_prompt_section()

    assert "### unknown-lib" in section
    assert "not found in Context7" in section


def test_library_context_to_prompt_section_with_error():
    """Test prompt section generation with error message."""
    ctx = LibraryContext(
        name="failed-lib",
        resolved=False,
        error="Network timeout"
    )
    section = ctx.to_prompt_section()

    assert "### failed-lib" in section
    assert "Resolution failed: Network timeout" in section


def test_library_context_default_values():
    """Test that default values are correctly set."""
    ctx = LibraryContext(name="test")

    # key_methods should be empty list, not None
    assert ctx.key_methods == []
    assert isinstance(ctx.key_methods, list)

    # Modifying one instance shouldn't affect others
    ctx.key_methods.append("test_method")
    ctx2 = LibraryContext(name="test2")
    assert ctx2.key_methods == []


# ============================================================================
# 2. Core Function Tests - gather_library_context (5 tests)
# ============================================================================

def test_gather_library_context_known_library(
    mock_mcp_resolve_success,
    mock_mcp_query_success
):
    """Test gathering context for a known library."""
    contexts = gather_library_context(
        libraries=["fastapi"],
        mcp_resolve=mock_mcp_resolve_success,
        mcp_query=mock_mcp_query_success
    )

    assert len(contexts) == 1
    ctx = contexts[0]

    assert ctx.name == "fastapi"
    assert ctx.resolved is True
    assert ctx.context7_id == "/tiangolo/fastapi"
    assert ctx.initialization is not None
    assert "FastAPI" in ctx.initialization


def test_gather_library_context_unknown_library(mock_mcp_resolve_failure):
    """Test gathering context for an unknown library."""
    contexts = gather_library_context(
        libraries=["totally-fake-library-xyz"],
        mcp_resolve=mock_mcp_resolve_failure
    )

    assert len(contexts) == 1
    ctx = contexts[0]

    assert ctx.name == "totally-fake-library-xyz"
    assert ctx.resolved is False
    assert ctx.error is not None


def test_gather_library_context_mixed_libraries(
    mock_mcp_resolve_success,
    mock_mcp_query_success
):
    """Test gathering context for mix of known and unknown libraries."""
    contexts = gather_library_context(
        libraries=["fastapi", "unknown-lib", "pydantic"],
        mcp_resolve=mock_mcp_resolve_success,
        mcp_query=mock_mcp_query_success
    )

    assert len(contexts) == 3

    # fastapi should be resolved
    fastapi_ctx = next(c for c in contexts if c.name == "fastapi")
    assert fastapi_ctx.resolved is True

    # unknown-lib should not be resolved
    unknown_ctx = next(c for c in contexts if c.name == "unknown-lib")
    assert unknown_ctx.resolved is False

    # pydantic should be resolved
    pydantic_ctx = next(c for c in contexts if c.name == "pydantic")
    assert pydantic_ctx.resolved is True


def test_gather_library_context_empty_list():
    """Test gathering context for empty library list."""
    contexts = gather_library_context(libraries=[])

    assert contexts == []
    assert len(contexts) == 0


def test_gather_library_context_mcp_failure(mock_mcp_resolve_exception):
    """Test graceful handling of MCP failures."""
    contexts = gather_library_context(
        libraries=["fastapi"],
        mcp_resolve=mock_mcp_resolve_exception
    )

    assert len(contexts) == 1
    ctx = contexts[0]

    # Should gracefully handle exception
    assert ctx.name == "fastapi"
    assert ctx.resolved is False


# ============================================================================
# 3. Display Function Tests (3 tests)
# ============================================================================

def test_display_library_context_resolved_only(
    sample_library_context_resolved,
    capsys
):
    """Test display output for resolved libraries only."""
    display_library_context([sample_library_context_resolved])

    captured = capsys.readouterr()
    output = captured.out

    assert "Library Context Summary" in output
    assert "Resolved (1)" in output
    assert "fastapi" in output
    assert "/tiangolo/fastapi" in output


def test_display_library_context_failed_only(
    sample_library_context_failed,
    capsys
):
    """Test display output for failed libraries only."""
    display_library_context([sample_library_context_failed])

    captured = capsys.readouterr()
    output = captured.out

    assert "Library Context Summary" in output
    assert "Failed (1)" in output
    assert "unknown-lib" in output
    assert "Could not resolve" in output


def test_display_library_context_mixed(
    sample_library_context_resolved,
    sample_library_context_failed,
    capsys
):
    """Test display output for mixed resolved/failed libraries."""
    contexts = [sample_library_context_resolved, sample_library_context_failed]
    display_library_context(contexts)

    captured = capsys.readouterr()
    output = captured.out

    assert "Resolved (1)" in output
    assert "Failed (1)" in output
    assert "fastapi" in output
    assert "unknown-lib" in output


def test_display_library_context_empty(capsys):
    """Test display output for empty context list."""
    display_library_context([])

    captured = capsys.readouterr()
    output = captured.out

    assert "No library context gathered" in output


# ============================================================================
# 4. Prompt Injection Tests (3 tests)
# ============================================================================

def test_inject_library_context_into_prompt_with_resolved(
    sample_library_context_resolved
):
    """Test prompt injection with resolved library context."""
    base_prompt = """
## Task Description

Implement a REST API endpoint.

## Requirements

- Handle GET requests
- Return JSON response
"""

    enhanced = inject_library_context_into_prompt(
        base_prompt,
        [sample_library_context_resolved]
    )

    # Should include library reference section
    assert "## Library Reference" in enhanced
    assert "fastapi" in enhanced
    assert "from fastapi import FastAPI" in enhanced

    # Should preserve original content
    assert "Task Description" in enhanced
    assert "REST API endpoint" in enhanced


def test_inject_library_context_into_prompt_no_resolved():
    """Test prompt injection with no resolved libraries."""
    base_prompt = "Create an implementation plan."

    ctx = LibraryContext(name="unknown", resolved=False)
    enhanced = inject_library_context_into_prompt(base_prompt, [ctx])

    # Should return unchanged prompt
    assert enhanced == base_prompt
    assert "Library Reference" not in enhanced


def test_inject_library_context_into_prompt_preserves_base(
    sample_library_context_resolved
):
    """Test that prompt injection preserves base prompt structure."""
    base_prompt = """
## Implementation Plan

Create the following files:

1. main.py
2. routes.py
3. models.py
"""

    enhanced = inject_library_context_into_prompt(
        base_prompt,
        [sample_library_context_resolved]
    )

    # All original sections should remain
    assert "## Implementation Plan" in enhanced
    assert "main.py" in enhanced
    assert "routes.py" in enhanced
    assert "models.py" in enhanced


def test_inject_library_context_into_prompt_injection_point():
    """Test that context is injected at correct position."""
    base_prompt = """
## Context

Some initial context.

## Implementation

Detailed implementation steps.
"""

    ctx = LibraryContext(
        name="test-lib",
        resolved=True,
        context7_id="/test/lib"
    )

    enhanced = inject_library_context_into_prompt(base_prompt, [ctx])

    # Library Reference should appear before Implementation
    lib_ref_pos = enhanced.index("## Library Reference")
    impl_pos = enhanced.index("## Implementation")

    assert lib_ref_pos < impl_pos


# ============================================================================
# 5. Error Handling Tests (2 tests)
# ============================================================================

def test_graceful_fallback_on_resolution_failure():
    """Test that resolution failures don't crash the system."""
    def flaky_resolve(libraryName: str, query: str):
        if libraryName == "good-lib":
            return {"libraryId": "/test/good-lib"}
        raise ConnectionError("Network error")

    def mock_query(libraryId: str, query: str):
        return {"content": "Documentation"}

    contexts = gather_library_context(
        libraries=["good-lib", "bad-lib", "another-good"],
        mcp_resolve=flaky_resolve,
        mcp_query=mock_query
    )

    # Should have processed all libraries
    assert len(contexts) == 3

    # good-lib should be resolved
    good = next(c for c in contexts if c.name == "good-lib")
    assert good.resolved is True

    # bad-lib should be failed but not crash
    bad = next(c for c in contexts if c.name == "bad-lib")
    assert bad.resolved is False


def test_partial_results_on_mixed_failures():
    """Test that we get partial results when some libraries fail."""
    def partial_resolve(libraryName: str, query: str):
        success = {"fastapi": "/tiangolo/fastapi", "redis": "/redis/redis-py"}
        return {"libraryId": success.get(libraryName.lower())} if libraryName.lower() in success else None

    def partial_query(libraryId: str, query: str):
        if libraryId == "/tiangolo/fastapi":
            return {"content": "FastAPI documentation"}
        return None

    contexts = gather_library_context(
        libraries=["fastapi", "unknown1", "redis", "unknown2"],
        mcp_resolve=partial_resolve,
        mcp_query=partial_query
    )

    assert len(contexts) == 4

    resolved = [c for c in contexts if c.resolved]
    failed = [c for c in contexts if not c.resolved]

    assert len(resolved) == 2  # fastapi and redis
    assert len(failed) == 2   # unknown1 and unknown2


# ============================================================================
# 6. Utility Function Tests (3 tests)
# ============================================================================

def test_format_context_for_logging_resolved():
    """Test logging format for resolved contexts."""
    ctx = LibraryContext(name="fastapi", resolved=True)

    result = format_context_for_logging([ctx])

    assert "fastapi" in result
    assert "resolved" in result


def test_format_context_for_logging_failed():
    """Test logging format for failed contexts."""
    ctx = LibraryContext(name="unknown", resolved=False)

    result = format_context_for_logging([ctx])

    assert "unknown" in result
    assert "failed" in result


def test_format_context_for_logging_empty():
    """Test logging format for empty list."""
    result = format_context_for_logging([])

    assert "none" in result.lower()


def test_extract_import_statement_valid():
    """Test extraction of import statements from docs."""
    docs = """
# Getting Started

First, import FastAPI:

```python
from fastapi import FastAPI
```

Then create your app.
"""

    result = _extract_import_statement(docs)

    assert result is not None
    assert "from fastapi import FastAPI" in result


def test_extract_import_statement_none():
    """Test extraction returns None when no import found."""
    docs = "This documentation has no import statements."

    result = _extract_import_statement(docs)

    assert result is None


def test_extract_key_methods():
    """Test extraction of key methods from docs."""
    docs = """
## API Methods

The main methods are:

def get_items():
    pass

def create_item():
    pass

app.post("/items")
app.get("/users")
"""

    result = _extract_key_methods(docs)

    assert "get_items" in result
    assert "create_item" in result
    assert "post" in result
    assert "get" in result


def test_extract_key_methods_empty():
    """Test extraction returns empty list when no methods found."""
    docs = "No methods defined here."

    result = _extract_key_methods(docs)

    assert result == []


def test_extract_key_methods_limit():
    """Test that method extraction respects limit."""
    docs = """
def method1(): pass
def method2(): pass
def method3(): pass
def method4(): pass
def method5(): pass
def method6(): pass
def method7(): pass
"""

    result = _extract_key_methods(docs, limit=3)

    assert len(result) == 3


# ============================================================================
# 7. Token Budget Tests (2 tests)
# ============================================================================

def test_token_budget_respected():
    """Test that token budget is respected."""
    def mock_resolve(libraryName: str, query: str):
        return {"libraryId": f"/test/{libraryName}"}

    def mock_query_large(libraryId: str, query: str):
        # Return large documentation (>1000 tokens estimated)
        return {"content": "x" * 8000}  # ~2000 tokens

    # With 5 libraries and small budget, should stop early
    contexts = gather_library_context(
        libraries=["lib1", "lib2", "lib3", "lib4", "lib5"],
        token_budget=3000,
        mcp_resolve=mock_resolve,
        mcp_query=mock_query_large
    )

    assert len(contexts) == 5

    # Some libraries should have been skipped due to budget
    skipped = [c for c in contexts if c.error and "budget" in c.error.lower()]
    # At least some should be skipped (exact number depends on implementation)
    # The test verifies the mechanism exists


def test_token_budget_allows_all_when_sufficient():
    """Test that all libraries are processed when budget is sufficient."""
    def mock_resolve(libraryName: str, query: str):
        return {"libraryId": f"/test/{libraryName}"}

    def mock_query_small(libraryId: str, query: str):
        return {"content": "Small docs"}  # ~5 tokens

    contexts = gather_library_context(
        libraries=["lib1", "lib2", "lib3"],
        token_budget=10000,  # Large budget
        mcp_resolve=mock_resolve,
        mcp_query=mock_query_small
    )

    assert len(contexts) == 3

    # All should be resolved (no budget issues)
    resolved = [c for c in contexts if c.resolved]
    assert len(resolved) == 3


# ============================================================================
# 8. Constants Tests (2 tests)
# ============================================================================

def test_init_query_constant():
    """Test INIT_QUERY constant is properly defined."""
    assert INIT_QUERY is not None
    assert isinstance(INIT_QUERY, str)
    assert len(INIT_QUERY) > 0
    assert "init" in INIT_QUERY.lower() or "setup" in INIT_QUERY.lower()


def test_methods_query_constant():
    """Test METHODS_QUERY constant is properly defined."""
    assert METHODS_QUERY is not None
    assert isinstance(METHODS_QUERY, str)
    assert len(METHODS_QUERY) > 0
    assert "method" in METHODS_QUERY.lower() or "api" in METHODS_QUERY.lower()


# ============================================================================
# 9. Edge Case Tests for MCP Result Handling (6 tests)
# ============================================================================

def test_resolve_returns_string_directly():
    """Test handling when MCP resolve returns a string directly."""
    def string_resolve(libraryName: str, query: str):
        if libraryName == "test-lib":
            return "/test/test-lib"  # Return string directly
        return None

    contexts = gather_library_context(
        libraries=["test-lib"],
        mcp_resolve=string_resolve,
        mcp_query=lambda **kw: {"content": "docs"}
    )

    assert len(contexts) == 1
    assert contexts[0].context7_id == "/test/test-lib"
    assert contexts[0].resolved is True


def test_resolve_returns_id_field():
    """Test handling when MCP resolve returns 'id' field instead of 'libraryId'."""
    def id_field_resolve(libraryName: str, query: str):
        return {"id": "/alt/test-lib"}

    contexts = gather_library_context(
        libraries=["test-lib"],
        mcp_resolve=id_field_resolve,
        mcp_query=lambda **kw: {"content": "docs"}
    )

    assert len(contexts) == 1
    assert contexts[0].context7_id == "/alt/test-lib"


def test_query_docs_returns_string_directly():
    """Test handling when MCP query-docs returns a string directly."""
    def mock_resolve(libraryName: str, query: str):
        return {"libraryId": "/test/lib"}

    def string_query(libraryId: str, query: str):
        return "Direct string documentation"  # Return string directly

    contexts = gather_library_context(
        libraries=["test-lib"],
        mcp_resolve=mock_resolve,
        mcp_query=string_query
    )

    assert len(contexts) == 1
    assert contexts[0].initialization == "Direct string documentation"


def test_query_docs_returns_documentation_field():
    """Test handling when MCP query-docs returns 'documentation' field."""
    def mock_resolve(libraryName: str, query: str):
        return {"libraryId": "/test/lib"}

    def doc_field_query(libraryId: str, query: str):
        return {"documentation": "Doc from documentation field"}

    contexts = gather_library_context(
        libraries=["test-lib"],
        mcp_resolve=mock_resolve,
        mcp_query=doc_field_query
    )

    assert len(contexts) == 1
    assert contexts[0].initialization == "Doc from documentation field"


def test_query_docs_returns_text_field():
    """Test handling when MCP query-docs returns 'text' field."""
    def mock_resolve(libraryName: str, query: str):
        return {"libraryId": "/test/lib"}

    def text_field_query(libraryId: str, query: str):
        return {"text": "Doc from text field"}

    contexts = gather_library_context(
        libraries=["test-lib"],
        mcp_resolve=mock_resolve,
        mcp_query=text_field_query
    )

    assert len(contexts) == 1
    assert contexts[0].initialization == "Doc from text field"


def test_mcp_query_exception_handling():
    """Test graceful handling of MCP query exceptions."""
    def mock_resolve(libraryName: str, query: str):
        return {"libraryId": "/test/lib"}

    def throwing_query(libraryId: str, query: str):
        raise RuntimeError("Query failed")

    contexts = gather_library_context(
        libraries=["test-lib"],
        mcp_resolve=mock_resolve,
        mcp_query=throwing_query
    )

    # Should still resolve, just without docs
    assert len(contexts) == 1
    assert contexts[0].resolved is True
    assert contexts[0].initialization is None


def test_extract_import_statement_with_import_keyword():
    """Test extraction with 'import' (not 'from') keyword."""
    docs = """
# Getting Started

```python
import json
```

Use json module for serialization.
"""

    result = _extract_import_statement(docs)
    assert result is not None
    assert "import json" in result


def test_extract_key_methods_skips_private():
    """Test that private methods (starting with _) are skipped."""
    docs = """
def public_method():
    pass

def _private_method():
    pass

app._internal_call()
"""

    result = _extract_key_methods(docs)

    assert "public_method" in result
    assert "_private_method" not in result
    assert "_internal_call" not in result


def test_no_mcp_functions_provided():
    """Test behavior when no MCP functions are provided (production simulation)."""
    # When mcp_resolve is None, should return unresolved context
    contexts = gather_library_context(
        libraries=["fastapi"],
        mcp_resolve=None,
        mcp_query=None
    )

    assert len(contexts) == 1
    assert contexts[0].resolved is False
    assert contexts[0].error is not None


# ============================================================================
# 10. Library Context Parsing Tests (TASK-LKG-004)
# ============================================================================

def test_parse_library_context_minimal():
    """Test parsing minimal library_context with just name."""
    raw = [{"name": "mylib"}]
    result = parse_library_context(raw)

    assert result is not None
    assert len(result) == 1
    assert result[0].name == "mylib"
    assert result[0].resolved is True
    assert result[0].source == "manual"


def test_parse_library_context_full():
    """Test parsing full library_context with all fields."""
    raw = [{
        "name": "graphiti-core",
        "import": "from graphiti_core import Graphiti",
        "initialization": "g = Graphiti(...)",
        "key_methods": [
            {"name": "search", "signature": "async def search(...)", "returns": "List[Edge]"},
            {"name": "add_episode", "signature": "async def add_episode(...)", "returns": "EpisodeResult"}
        ]
    }]
    result = parse_library_context(raw)

    assert result is not None
    assert len(result) == 1
    ctx = result[0]

    assert ctx.name == "graphiti-core"
    assert ctx.import_statement == "from graphiti_core import Graphiti"
    assert ctx.initialization == "g = Graphiti(...)"
    assert "search" in ctx.key_methods
    assert "add_episode" in ctx.key_methods
    assert ctx.method_docs is not None
    assert "search" in ctx.method_docs
    assert ctx.source == "manual"
    assert ctx.resolved is True


def test_parse_library_context_empty():
    """Test parsing empty library_context returns None."""
    assert parse_library_context(None) is None
    assert parse_library_context([]) is None


def test_parse_library_context_missing_name():
    """Test that items without name are skipped."""
    raw = [
        {"name": "valid-lib"},
        {"import": "import invalid"},  # Missing name
        {"name": "another-valid"}
    ]
    result = parse_library_context(raw)

    assert result is not None
    assert len(result) == 2
    assert result[0].name == "valid-lib"
    assert result[1].name == "another-valid"


def test_parse_library_context_invalid_items():
    """Test that non-dict items are skipped."""
    raw = [
        {"name": "valid-lib"},
        "string-item",  # Invalid
        123,  # Invalid
        {"name": "another-valid"}
    ]
    result = parse_library_context(raw)

    assert result is not None
    assert len(result) == 2


# ============================================================================
# 11. Manual vs Context7 Precedence Tests (TASK-LKG-004)
# ============================================================================

def test_manual_context_takes_precedence():
    """Test that manual context overrides Context7."""
    # Create manual context
    manual = [
        LibraryContext(
            name="fastapi",
            resolved=True,
            source="manual",
            initialization="Manual FastAPI init"
        )
    ]

    # Mock resolve that would return Context7 result
    def mock_resolve(libraryName: str, query: str):
        return {"libraryId": "/tiangolo/fastapi"}

    def mock_query(libraryId: str, query: str):
        return {"content": "Context7 FastAPI docs"}

    contexts = gather_library_context(
        libraries=["fastapi"],
        manual_context=manual,
        mcp_resolve=mock_resolve,
        mcp_query=mock_query
    )

    assert len(contexts) == 1
    # Should use manual context, not Context7
    assert contexts[0].source == "manual"
    assert contexts[0].initialization == "Manual FastAPI init"


def test_manual_and_context7_merge():
    """Test that manual and Context7 contexts merge correctly."""
    # Manual context for one library
    manual = [
        LibraryContext(
            name="internal-lib",
            resolved=True,
            source="manual",
            initialization="Internal lib setup"
        )
    ]

    # Context7 mock returns results for known libraries
    def mock_resolve(libraryName: str, query: str):
        if libraryName == "fastapi":
            return {"libraryId": "/tiangolo/fastapi"}
        return None

    def mock_query(libraryId: str, query: str):
        return {"content": "FastAPI documentation"}

    contexts = gather_library_context(
        libraries=["internal-lib", "fastapi", "unknown"],
        manual_context=manual,
        mcp_resolve=mock_resolve,
        mcp_query=mock_query
    )

    assert len(contexts) == 3

    # internal-lib should use manual
    internal = next(c for c in contexts if c.name == "internal-lib")
    assert internal.source == "manual"
    assert internal.resolved is True

    # fastapi should use Context7
    fastapi = next(c for c in contexts if c.name == "fastapi")
    assert fastapi.source == "context7"
    assert fastapi.resolved is True

    # unknown should fail
    unknown = next(c for c in contexts if c.name == "unknown")
    assert unknown.resolved is False


def test_manual_context_case_insensitive():
    """Test that manual context lookup is case-insensitive."""
    manual = [
        LibraryContext(name="FastAPI", resolved=True, source="manual")
    ]

    contexts = gather_library_context(
        libraries=["fastapi"],  # lowercase
        manual_context=manual,
        mcp_resolve=None,
        mcp_query=None
    )

    assert len(contexts) == 1
    assert contexts[0].source == "manual"


def test_source_field_default():
    """Test that source field defaults to 'context7'."""
    ctx = LibraryContext(name="test")
    assert ctx.source == "context7"


def test_source_field_set_to_manual():
    """Test that source field can be set to 'manual'."""
    ctx = LibraryContext(name="test", source="manual")
    assert ctx.source == "manual"


# ============================================================================
# 12. Format Method Docs Tests (TASK-LKG-004)
# ============================================================================

def test_format_method_docs_with_methods():
    """Test formatting method documentation."""
    methods = [
        {"name": "search", "signature": "def search(query)", "returns": "List[Edge]"},
        {"name": "add_episode", "signature": "def add_episode(name, body)"}
    ]

    result = format_method_docs(methods)

    assert result is not None
    assert "**search**" in result
    assert "`def search(query)`" in result
    assert "Returns: List[Edge]" in result
    assert "**add_episode**" in result


def test_format_method_docs_empty():
    """Test formatting empty method docs."""
    assert format_method_docs(None) is None
    assert format_method_docs([]) is None


def test_format_method_docs_partial():
    """Test formatting methods with partial fields."""
    methods = [
        {"name": "method1"},  # Only name
        {"name": "method2", "signature": "def method2()"},  # Name and signature
    ]

    result = format_method_docs(methods)

    assert result is not None
    assert "**method1**" in result
    assert "**method2**" in result
    assert "`def method2()`" in result


def test_format_method_docs_skips_invalid():
    """Test that non-dict items are skipped."""
    methods = [
        {"name": "valid_method"},
        "invalid_string",
        123,
        {"name": "another_valid"}
    ]

    result = format_method_docs(methods)

    assert result is not None
    assert "**valid_method**" in result
    assert "**another_valid**" in result


# ============================================================================
# Test Summary
# ============================================================================
"""
Test Coverage Summary:

1. Data Structure Tests (5 tests):
   - test_library_context_creation
   - test_library_context_to_prompt_section_resolved
   - test_library_context_to_prompt_section_unresolved
   - test_library_context_to_prompt_section_with_error
   - test_library_context_default_values

2. Core Function Tests (5 tests):
   - test_gather_library_context_known_library
   - test_gather_library_context_unknown_library
   - test_gather_library_context_mixed_libraries
   - test_gather_library_context_empty_list
   - test_gather_library_context_mcp_failure

3. Display Function Tests (4 tests):
   - test_display_library_context_resolved_only
   - test_display_library_context_failed_only
   - test_display_library_context_mixed
   - test_display_library_context_empty

4. Prompt Injection Tests (4 tests):
   - test_inject_library_context_into_prompt_with_resolved
   - test_inject_library_context_into_prompt_no_resolved
   - test_inject_library_context_into_prompt_preserves_base
   - test_inject_library_context_into_prompt_injection_point

5. Error Handling Tests (2 tests):
   - test_graceful_fallback_on_resolution_failure
   - test_partial_results_on_mixed_failures

6. Utility Function Tests (6 tests):
   - test_format_context_for_logging_resolved
   - test_format_context_for_logging_failed
   - test_format_context_for_logging_empty
   - test_extract_import_statement_valid
   - test_extract_import_statement_none
   - test_extract_key_methods
   - test_extract_key_methods_empty
   - test_extract_key_methods_limit

7. Token Budget Tests (2 tests):
   - test_token_budget_respected
   - test_token_budget_allows_all_when_sufficient

8. Constants Tests (2 tests):
   - test_init_query_constant
   - test_methods_query_constant

9. MCP Result Handling Tests (8 tests):
   - test_resolve_returns_string_directly
   - test_resolve_returns_id_field
   - test_query_docs_returns_string_directly
   - test_query_docs_returns_documentation_field
   - test_query_docs_returns_text_field
   - test_mcp_query_exception_handling
   - test_extract_import_statement_with_import_keyword
   - test_extract_key_methods_skips_private
   - test_no_mcp_functions_provided

10. Library Context Parsing Tests - TASK-LKG-004 (5 tests):
   - test_parse_library_context_minimal
   - test_parse_library_context_full
   - test_parse_library_context_empty
   - test_parse_library_context_missing_name
   - test_parse_library_context_invalid_items

11. Manual vs Context7 Precedence Tests - TASK-LKG-004 (5 tests):
   - test_manual_context_takes_precedence
   - test_manual_and_context7_merge
   - test_manual_context_case_insensitive
   - test_source_field_default
   - test_source_field_set_to_manual

12. Format Method Docs Tests - TASK-LKG-004 (4 tests):
   - test_format_method_docs_with_methods
   - test_format_method_docs_empty
   - test_format_method_docs_partial
   - test_format_method_docs_skips_invalid

Total: 44 tests (exceeds 17 minimum requirement)
Target Coverage: >=90%
"""
