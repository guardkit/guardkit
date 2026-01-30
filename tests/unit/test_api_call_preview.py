#!/usr/bin/env python3
"""Unit tests for api_call_preview module.

Tests cover:
- Code block extraction from markdown
- API call detection patterns
- Library API call extraction from plans
- Display formatting
- Conditional display logic

Target: ≥80% line coverage, ≥75% branch coverage
"""

import pytest
from installer.core.commands.lib.api_call_preview import (
    extract_planned_api_calls,
    is_api_call,
    format_api_preview,
    should_show_api_preview,
    _extract_code_blocks,
    _normalize_library_name,
)


class TestNormalizeLibraryName:
    """Test library name normalization."""

    def test_normalize_hyphenated_name(self):
        """Test normalization of hyphenated library names."""
        assert _normalize_library_name("graphiti-core") == "graphiti"

    def test_normalize_underscored_name(self):
        """Test normalization of underscored library names."""
        assert _normalize_library_name("fast_api") == "fast"

    def test_normalize_simple_name(self):
        """Test normalization of simple library names."""
        assert _normalize_library_name("fastapi") == "fastapi"

    def test_normalize_uppercase(self):
        """Test normalization converts to lowercase."""
        assert _normalize_library_name("FastAPI") == "fastapi"

    def test_normalize_with_whitespace(self):
        """Test normalization strips whitespace."""
        assert _normalize_library_name("  graphiti-core  ") == "graphiti"

    def test_normalize_empty_string(self):
        """Test normalization handles empty string."""
        assert _normalize_library_name("") == ""


class TestExtractCodeBlocks:
    """Test code block extraction from markdown."""

    def test_extract_python_code_block(self):
        """Test extraction of Python code block."""
        text = "Some text\n```python\ncode here\n```\nMore text"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 1
        assert "code here" in blocks[0]

    def test_extract_multiple_code_blocks(self):
        """Test extraction of multiple code blocks."""
        text = """
        ```python
        block1
        ```
        Some text
        ```python
        block2
        ```
        """
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 2
        assert "block1" in blocks[0]
        assert "block2" in blocks[1]

    def test_extract_untagged_code_block(self):
        """Test extraction of code block without language tag."""
        text = "```\ncode here\n```"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 1
        assert "code here" in blocks[0]

    def test_extract_javascript_code_block(self):
        """Test extraction of JavaScript code block."""
        text = "```javascript\nconst x = 1;\n```"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 1
        assert "const x = 1;" in blocks[0]

    def test_extract_typescript_code_block(self):
        """Test extraction of TypeScript code block."""
        text = "```typescript\ntype X = string;\n```"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 1
        assert "type X = string;" in blocks[0]

    def test_extract_no_code_blocks(self):
        """Test extraction when no code blocks present."""
        text = "Just plain text with no code blocks"
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 0

    def test_extract_empty_string(self):
        """Test extraction from empty string."""
        blocks = _extract_code_blocks("")
        assert len(blocks) == 0

    def test_extract_multiline_code_block(self):
        """Test extraction of multiline code block."""
        text = """
        ```python
        line1
        line2
        line3
        ```
        """
        blocks = _extract_code_blocks(text)
        assert len(blocks) == 1
        assert "line1" in blocks[0]
        assert "line2" in blocks[0]
        assert "line3" in blocks[0]

    def test_extract_strips_empty_blocks(self):
        """Test that empty code blocks are filtered out."""
        text = "```python\n\n\n```\n```python\ncode\n```"
        blocks = _extract_code_blocks(text)
        # Only non-empty block should be returned
        assert len(blocks) == 1
        assert "code" in blocks[0]


class TestIsApiCall:
    """Test API call detection logic."""

    def test_method_call_pattern(self):
        """Test detection of method call pattern."""
        assert is_api_call("graphiti.search(query)", "graphiti-core")
        assert is_api_call("graphiti.build_indices()", "graphiti-core")

    def test_async_method_call_pattern(self):
        """Test detection of async method call pattern."""
        assert is_api_call("await graphiti.search(query)", "graphiti-core")
        assert is_api_call("results = await graphiti.add_episode()", "graphiti-core")

    def test_assignment_pattern(self):
        """Test detection of assignment pattern."""
        assert is_api_call("graphiti = Graphiti(uri, user, pass)", "graphiti-core")
        assert is_api_call("client = graphiti(config)", "graphiti-core")

    def test_import_from_pattern(self):
        """Test detection of import from pattern."""
        assert is_api_call("from graphiti_core import Graphiti", "graphiti-core")
        assert is_api_call("from graphiti_core.models import Node", "graphiti-core")

    def test_import_pattern(self):
        """Test detection of import pattern."""
        assert is_api_call("import graphiti_core", "graphiti-core")
        assert is_api_call("import graphiti_core as graphiti", "graphiti-core")

    def test_constructor_pattern(self):
        """Test detection of constructor pattern."""
        assert is_api_call("Graphiti(uri)", "graphiti-core")
        assert is_api_call("client = Graphiti()", "graphiti-core")

    def test_not_api_call_comment(self):
        """Test that comments are not detected as API calls."""
        assert not is_api_call("# comment about graphiti", "graphiti-core")
        assert not is_api_call("// using graphiti for search", "graphiti-core")

    def test_not_api_call_different_library(self):
        """Test that calls to different libraries are not detected."""
        assert not is_api_call("fastapi.get('/endpoint')", "graphiti-core")
        assert not is_api_call("redis.set('key', 'value')", "graphiti-core")

    def test_empty_inputs(self):
        """Test handling of empty inputs."""
        assert not is_api_call("", "graphiti-core")
        assert not is_api_call("graphiti.search()", "")
        assert not is_api_call("", "")

    def test_case_insensitive_detection(self):
        """Test that detection is case-insensitive."""
        assert is_api_call("GRAPHITI.search()", "graphiti-core")
        assert is_api_call("Graphiti = Graphiti()", "graphiti-core")

    def test_whitespace_handling(self):
        """Test handling of various whitespace patterns."""
        assert is_api_call("graphiti  .  search  (  )", "graphiti-core")
        assert is_api_call("  await   graphiti.search()", "graphiti-core")


class TestExtractPlannedApiCalls:
    """Test extraction of API calls from implementation plans."""

    def test_extract_simple_plan(self):
        """Test extraction from simple plan with one library."""
        plan = """
        Implementation:
        ```python
        graphiti = Graphiti(uri, user, password)
        await graphiti.build_indices()
        results = await graphiti.search(query)
        ```
        """
        calls = extract_planned_api_calls(plan, ["graphiti-core"])

        assert "graphiti-core" in calls
        assert len(calls["graphiti-core"]) == 3
        assert any("Graphiti(uri" in call for call in calls["graphiti-core"])
        assert any("build_indices" in call for call in calls["graphiti-core"])
        assert any("search(query)" in call for call in calls["graphiti-core"])

    def test_extract_multiple_libraries(self):
        """Test extraction from plan with multiple libraries."""
        plan = """
        ```python
        graphiti = Graphiti(uri)
        await graphiti.search(query)

        redis = Redis(host)
        redis.set('key', 'value')
        ```
        """
        calls = extract_planned_api_calls(plan, ["graphiti-core", "redis"])

        assert "graphiti-core" in calls
        assert "redis" in calls
        assert len(calls["graphiti-core"]) >= 1
        assert len(calls["redis"]) >= 1

    def test_extract_multiple_code_blocks(self):
        """Test extraction from plan with multiple code blocks."""
        plan = """
        Step 1:
        ```python
        from graphiti_core import Graphiti
        ```

        Step 2:
        ```python
        graphiti = Graphiti(uri)
        await graphiti.search(query)
        ```
        """
        calls = extract_planned_api_calls(plan, ["graphiti-core"])

        assert "graphiti-core" in calls
        # Should find import and API calls
        assert len(calls["graphiti-core"]) >= 2

    def test_extract_no_code_blocks(self):
        """Test extraction when plan has no code blocks."""
        plan = "Just a textual description with no code"
        calls = extract_planned_api_calls(plan, ["graphiti-core"])

        assert len(calls) == 0

    def test_extract_no_matching_calls(self):
        """Test extraction when code exists but no matching library calls."""
        plan = """
        ```python
        redis = Redis()
        redis.get('key')
        ```
        """
        calls = extract_planned_api_calls(plan, ["graphiti-core"])

        # Should not include graphiti-core since no calls found
        assert "graphiti-core" not in calls

    def test_extract_filters_comments(self):
        """Test that comments are filtered out."""
        plan = """
        ```python
        # Initialize graphiti client
        graphiti = Graphiti(uri)
        # Search for results
        results = await graphiti.search(query)
        ```
        """
        calls = extract_planned_api_calls(plan, ["graphiti-core"])

        assert "graphiti-core" in calls
        # Should only include actual code lines, not comments
        assert all(not call.startswith('#') for call in calls["graphiti-core"])

    def test_extract_filters_empty_lines(self):
        """Test that empty lines are filtered out."""
        plan = """
        ```python
        graphiti = Graphiti(uri)

        await graphiti.search(query)
        ```
        """
        calls = extract_planned_api_calls(plan, ["graphiti-core"])

        assert "graphiti-core" in calls
        # Should only include non-empty lines
        assert all(call.strip() for call in calls["graphiti-core"])

    def test_extract_empty_plan(self):
        """Test extraction from empty plan."""
        calls = extract_planned_api_calls("", ["graphiti-core"])
        assert len(calls) == 0

    def test_extract_empty_libraries(self):
        """Test extraction with no libraries provided."""
        plan = "```python\ngraphiti.search()\n```"
        calls = extract_planned_api_calls(plan, [])
        assert len(calls) == 0

    def test_extract_none_inputs(self):
        """Test extraction handles None inputs gracefully."""
        # These should not raise exceptions
        calls = extract_planned_api_calls(None, ["lib"])
        assert len(calls) == 0

        calls = extract_planned_api_calls("plan", None)
        assert len(calls) == 0


class TestFormatApiPreview:
    """Test API preview formatting."""

    def test_format_single_library(self):
        """Test formatting with single library."""
        calls = {
            "graphiti-core": [
                "graphiti = Graphiti(uri)",
                "await graphiti.search(query)"
            ]
        }
        preview = format_api_preview(calls)

        assert "📚 PLANNED LIBRARY API CALLS" in preview
        assert "graphiti-core:" in preview
        assert "1. graphiti = Graphiti(uri)" in preview
        assert "2. await graphiti.search(query)" in preview
        assert "Do these match the library's actual API?" in preview

    def test_format_multiple_libraries(self):
        """Test formatting with multiple libraries."""
        calls = {
            "graphiti-core": ["graphiti = Graphiti(uri)"],
            "redis": ["redis = Redis()"]
        }
        preview = format_api_preview(calls)

        assert "graphiti-core:" in preview
        assert "redis:" in preview

    def test_format_truncates_long_list(self):
        """Test that long lists are truncated to 10 calls."""
        calls = {
            "library": [f"call_{i}()" for i in range(15)]
        }
        preview = format_api_preview(calls)

        assert "1. call_0()" in preview
        assert "10. call_9()" in preview
        assert "... and 5 more" in preview
        # 11th call should not appear
        assert "11. call_10()" not in preview

    def test_format_exactly_10_calls(self):
        """Test formatting with exactly 10 calls (no truncation)."""
        calls = {
            "library": [f"call_{i}()" for i in range(10)]
        }
        preview = format_api_preview(calls)

        assert "10. call_9()" in preview
        assert "... and" not in preview

    def test_format_empty_calls(self):
        """Test formatting with empty calls dict."""
        preview = format_api_preview({})
        assert preview == ""

    def test_format_alphabetically_sorted(self):
        """Test that libraries are sorted alphabetically."""
        calls = {
            "redis": ["redis.set()"],
            "graphiti-core": ["graphiti.search()"],
            "fastapi": ["FastAPI()"]
        }
        preview = format_api_preview(calls)

        # Find positions of each library name
        fastapi_pos = preview.find("fastapi:")
        graphiti_pos = preview.find("graphiti-core:")
        redis_pos = preview.find("redis:")

        # Should be in alphabetical order
        assert fastapi_pos < graphiti_pos < redis_pos

    def test_format_includes_separator_lines(self):
        """Test that separator lines are included."""
        calls = {"library": ["call()"]}
        preview = format_api_preview(calls)

        # Should have separator line (75 dashes)
        assert "─" * 75 in preview


class TestShouldShowApiPreview:
    """Test conditional display logic."""

    def test_show_with_valid_context(self):
        """Test that preview is shown with valid context."""
        context = {
            "complexity": 5,
            "library_context": {"graphiti-core": {}}
        }
        assert should_show_api_preview(context)

    def test_hide_without_library_context(self):
        """Test that preview is hidden without library context."""
        context = {"complexity": 5}
        assert not should_show_api_preview(context)

    def test_hide_when_context_skipped(self):
        """Test that preview is hidden when context was skipped."""
        context = {
            "complexity": 5,
            "library_context": {"lib": {}},
            "library_context_skipped": True
        }
        assert not should_show_api_preview(context)

    def test_hide_for_simple_tasks(self):
        """Test that preview is hidden for simple tasks."""
        context = {
            "complexity": 2,
            "library_context": {"lib": {}}
        }
        assert not should_show_api_preview(context)

    def test_show_at_complexity_threshold(self):
        """Test that preview is shown at complexity threshold (4)."""
        context = {
            "complexity": 4,
            "library_context": {"lib": {}}
        }
        assert should_show_api_preview(context)

    def test_hide_below_complexity_threshold(self):
        """Test that preview is hidden below complexity threshold."""
        context = {
            "complexity": 3,
            "library_context": {"lib": {}}
        }
        assert not should_show_api_preview(context)

    def test_default_complexity_value(self):
        """Test that default complexity is 5 if not provided."""
        context = {"library_context": {"lib": {}}}
        # Should use default complexity of 5, which is >= 4
        assert should_show_api_preview(context)

    def test_handle_invalid_context(self):
        """Test handling of invalid context types."""
        assert not should_show_api_preview(None)
        assert not should_show_api_preview("not a dict")
        assert not should_show_api_preview([])

    def test_empty_library_context_dict(self):
        """Test that empty library context dict is treated as no context."""
        context = {
            "complexity": 5,
            "library_context": {}
        }
        # Empty dict should be treated as no context
        assert not should_show_api_preview(context)


class TestIntegration:
    """Integration tests for complete workflow."""

    def test_full_workflow_with_graphiti(self):
        """Test complete workflow with graphiti-core example."""
        # Realistic implementation plan
        plan = """
        ## Implementation Steps

        ### Step 1: Initialize Graphiti Client

        ```python
        from graphiti_core import Graphiti

        graphiti = Graphiti(
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password"
        )
        ```

        ### Step 2: Build Indices

        ```python
        await graphiti.build_indices()
        ```

        ### Step 3: Search

        ```python
        results = await graphiti.search(
            query="search term",
            group_ids=["group1"],
            num_results=10
        )
        ```
        """

        # Extract calls
        calls = extract_planned_api_calls(plan, ["graphiti-core"])

        # Verify extraction
        assert "graphiti-core" in calls
        assert len(calls["graphiti-core"]) >= 3

        # Format preview
        preview = format_api_preview(calls)

        # Verify formatting
        assert "📚 PLANNED LIBRARY API CALLS" in preview
        assert "graphiti-core:" in preview
        assert "Graphiti(" in preview
        assert "build_indices" in preview
        assert "search" in preview

    def test_full_workflow_with_multiple_libraries(self):
        """Test complete workflow with multiple libraries."""
        plan = """
        ```python
        from graphiti_core import Graphiti
        from redis import Redis

        # Initialize clients
        graphiti = Graphiti(uri, user, pass)
        redis = Redis(host='localhost')

        # Use both
        await graphiti.search(query)
        redis.set('key', 'value')
        ```
        """

        # Extract calls
        calls = extract_planned_api_calls(plan, ["graphiti-core", "redis"])

        # Both libraries should be present
        assert "graphiti-core" in calls
        assert "redis" in calls

        # Format preview
        preview = format_api_preview(calls)

        # Both should appear in preview
        assert "graphiti-core:" in preview
        assert "redis:" in preview

    def test_conditional_display_simple_task(self):
        """Test that simple tasks don't show preview."""
        context = {
            "complexity": 2,
            "library_context": {"lib": {}}
        }

        # Should not show for simple tasks
        assert not should_show_api_preview(context)

    def test_conditional_display_complex_task(self):
        """Test that complex tasks show preview."""
        context = {
            "complexity": 7,
            "library_context": {"graphiti-core": {}}
        }

        # Should show for complex tasks
        assert should_show_api_preview(context)
