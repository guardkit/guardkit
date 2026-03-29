"""Tests for player.py.template factory pattern.

Validates that the Player factory uses create_agent() (not create_deep_agent()),
wires MemoryMiddleware for AGENTS.md loading, and does not inject filesystem tools.

Coverage Target: >=85%
Test Count: 12+ tests
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Path to the template file
# ---------------------------------------------------------------------------
_TEMPLATE_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "templates"
    / "langchain-deepagents"
    / "templates"
    / "other"
    / "agents"
    / "player.py.template"
)


@pytest.fixture(scope="module")
def template_source() -> str:
    """Read the raw template source."""
    return _TEMPLATE_PATH.read_text()


@pytest.fixture(scope="module")
def python_source(template_source) -> str:
    """Replace placeholders so the template is valid Python for AST parsing."""
    return template_source.replace("{{ProjectName}}", "myproject")


@pytest.fixture(scope="module")
def tree(python_source) -> ast.Module:
    """Parse the template as an AST."""
    return ast.parse(python_source)


# ===================================================================
# Factory Function: create_agent vs create_deep_agent
# ===================================================================


class TestFactorySelection:
    """Verify the template uses create_agent, not create_deep_agent."""

    def test_imports_create_agent(self, template_source):
        """Template imports create_agent from langchain.agents."""
        assert "from langchain.agents import create_agent" in template_source

    def test_does_not_import_create_deep_agent(self, python_source):
        """Template must NOT import create_deep_agent as a callable."""
        tree = ast.parse(python_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    assert alias.name != "create_deep_agent", (
                        "Template must NOT import create_deep_agent"
                    )

    def test_calls_create_agent(self, template_source):
        """Factory function calls create_agent()."""
        assert "return create_agent(" in template_source

    def test_does_not_call_create_deep_agent(self, python_source):
        """Factory function must NOT call create_deep_agent()."""
        tree = ast.parse(python_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "create_deep_agent":
                    pytest.fail("Template must NOT call create_deep_agent()")


# ===================================================================
# MemoryMiddleware: AGENTS.md injection
# ===================================================================


class TestMemoryMiddleware:
    """Verify memory is handled via MemoryMiddleware, not kwarg."""

    def test_imports_memory_middleware(self, template_source):
        """Template imports MemoryMiddleware from deepagents."""
        assert "from deepagents.middleware import MemoryMiddleware" in template_source

    def test_imports_filesystem_backend(self, template_source):
        """Template imports FilesystemBackend for memory backend."""
        assert "from deepagents.backends import FilesystemBackend" in template_source

    def test_memory_middleware_in_middleware_list(self, template_source):
        """MemoryMiddleware is included in the middleware list."""
        assert "MemoryMiddleware(backend=backend, sources=" in template_source

    def test_agents_md_is_memory_source(self, template_source):
        """AGENTS.md is specified as a memory source."""
        assert '"./AGENTS.md"' in template_source

    def test_no_memory_kwarg_to_create_agent(self, python_source):
        """create_agent() must NOT receive a memory= keyword argument."""
        # Find the create_agent call and verify no memory= kwarg
        tree = ast.parse(python_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                # Check if this is a call to create_agent
                if isinstance(func, ast.Name) and func.id == "create_agent":
                    kwarg_names = [kw.arg for kw in node.keywords]
                    assert "memory" not in kwarg_names, (
                        "create_agent() must NOT receive memory= kwarg. "
                        "Use MemoryMiddleware instead."
                    )

    def test_middleware_kwarg_passed_to_create_agent(self, python_source):
        """create_agent() receives middleware= keyword argument."""
        tree = ast.parse(python_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "create_agent":
                    kwarg_names = [kw.arg for kw in node.keywords]
                    assert "middleware" in kwarg_names, (
                        "create_agent() must receive middleware= kwarg "
                        "containing MemoryMiddleware."
                    )


# ===================================================================
# No FilesystemMiddleware injection
# ===================================================================


class TestNoFilesystemMiddleware:
    """Verify FilesystemMiddleware is NOT in the middleware stack."""

    def test_no_filesystem_middleware_import(self, python_source):
        """Template must NOT import FilesystemMiddleware as a callable."""
        tree = ast.parse(python_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    assert alias.name != "FilesystemMiddleware", (
                        "Template must NOT import FilesystemMiddleware"
                    )

    def test_no_subagent_middleware_import(self, template_source):
        """Template must NOT import SubAgentMiddleware."""
        assert "SubAgentMiddleware" not in template_source

    def test_no_todolist_middleware_import(self, template_source):
        """Template must NOT import TodoListMiddleware."""
        assert "TodoListMiddleware" not in template_source


# ===================================================================
# Tool separation enforcement
# ===================================================================


class TestToolSeparation:
    """Verify validate_player_tools() is called for safety."""

    def test_validate_player_tools_imported(self, template_source):
        """validate_player_tools is imported from orchestrator_pattern."""
        assert "validate_player_tools" in template_source

    def test_validate_player_tools_called(self, python_source):
        """validate_player_tools() is called in the factory function."""
        tree = ast.parse(python_source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name) and func.id == "validate_player_tools":
                    return  # Found the call
        pytest.fail("validate_player_tools() not called in factory function")

    def test_search_data_is_only_tool(self, template_source):
        """Player tools list contains only search_data."""
        assert "tools = [search_data]" in template_source


# ===================================================================
# Docstring and contract documentation
# ===================================================================


class TestDocumentation:
    """Verify the template documents the tool separation contract."""

    def test_module_docstring_mentions_tool_separation(self, template_source):
        """Module docstring documents the tool separation contract."""
        assert "TOOL SEPARATION CONTRACT" in template_source

    def test_module_docstring_mentions_create_agent(self, template_source):
        """Module docstring explains why create_agent is used."""
        assert "create_agent()" in template_source
        assert "create_deep_agent()" in template_source

    def test_function_docstring_mentions_filesystem(self, template_source):
        """Function docstring explains FilesystemMiddleware avoidance."""
        assert "FilesystemMiddleware" in template_source


# ===================================================================
# PatchToolCallsMiddleware
# ===================================================================


class TestPatchToolCallsMiddleware:
    """Verify PatchToolCallsMiddleware is included (proven pattern)."""

    def test_imports_patch_tool_calls(self, template_source):
        """Template imports PatchToolCallsMiddleware."""
        assert "PatchToolCallsMiddleware" in template_source

    def test_patch_tool_calls_in_middleware_list(self, template_source):
        """PatchToolCallsMiddleware() is in the middleware list."""
        assert "PatchToolCallsMiddleware()" in template_source
