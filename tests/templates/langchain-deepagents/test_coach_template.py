"""Tests for coach.py.template D5 invariant enforcement.

Validates that the coach factory template:
- Uses create_agent() not create_deep_agent()
- Has no tools parameter in function signature
- Always passes tools=[] to create_agent()
- Uses MemoryMiddleware (not FilesystemMiddleware) for AGENTS.md
- Uses {{ProjectName}} placeholders, not hardcoded 'deepagents'

Coverage Target: >=85%
Test Count: 12+ tests
"""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Load the template file as text (cannot import due to {{ProjectName}} placeholders)
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
    / "coach.py.template"
)


@pytest.fixture(scope="module")
def template_content() -> str:
    """Read the coach.py.template content."""
    return _TEMPLATE_PATH.read_text()


@pytest.fixture(scope="module")
def template_lines(template_content) -> list[str]:
    """Split template into lines for line-by-line checks."""
    return template_content.splitlines()


@pytest.fixture(scope="module")
def parseable_source(template_content) -> str:
    """Replace {{ProjectName}} with a valid Python identifier for AST parsing."""
    return template_content.replace("{{ProjectName}}", "_project_name_")


@pytest.fixture(scope="module")
def parsed_tree(parseable_source) -> ast.Module:
    """Parse the template as a Python AST."""
    return ast.parse(parseable_source)


# ===================================================================
# D5 Invariant: Coach has NO tools
# ===================================================================


class TestD5NoToolsInvariant:
    """Verify the D5 invariant: Coach has zero tools, enforced at factory level."""

    def test_no_tools_parameter_in_create_coach_signature(self, parsed_tree):
        """create_coach() must NOT accept a tools parameter."""
        for node in ast.walk(parsed_tree):
            if isinstance(node, ast.FunctionDef) and node.name == "create_coach":
                param_names = [arg.arg for arg in node.args.args]
                assert "tools" not in param_names, (
                    "D5 violation: create_coach() must not have a 'tools' parameter. "
                    f"Found parameters: {param_names}"
                )
                return
        pytest.fail("create_coach() function not found in template")

    def test_tools_always_empty_list_in_create_agent_call(self, template_content):
        """create_agent() must always be called with tools=[]."""
        assert "tools=[]" in template_content, (
            "D5 violation: create_agent() must be called with tools=[]"
        )

    def test_no_tools_variable_assignment(self, parsed_tree):
        """No variable named 'tools' should be assigned in create_coach."""
        for node in ast.walk(parsed_tree):
            if isinstance(node, ast.FunctionDef) and node.name == "create_coach":
                for child in ast.walk(node):
                    if isinstance(child, ast.Assign):
                        for target in child.targets:
                            if isinstance(target, ast.Name) and target.id == "tools":
                                pytest.fail(
                                    "D5 violation: coach should not assign a 'tools' variable"
                                )
                return


# ===================================================================
# Factory Function: create_agent not create_deep_agent
# ===================================================================


class TestFactoryFunction:
    """Verify coach uses create_agent(), not create_deep_agent()."""

    def test_uses_create_agent(self, template_content):
        """Template must import and call create_agent."""
        assert "from langchain.agents import create_agent" in template_content
        assert "create_agent(" in template_content

    def test_does_not_use_create_deep_agent(self, template_content):
        """Template must NOT use create_deep_agent anywhere."""
        assert "create_deep_agent" not in template_content, (
            "coach.py.template must not reference create_deep_agent — "
            "use create_agent() to avoid FilesystemMiddleware injection"
        )


# ===================================================================
# Middleware Stack
# ===================================================================


class TestMiddlewareStack:
    """Verify the curated middleware stack."""

    def test_has_memory_middleware(self, template_content):
        """MemoryMiddleware must be in the middleware stack."""
        assert "MemoryMiddleware" in template_content

    def test_memory_middleware_uses_agents_md(self, template_content):
        """MemoryMiddleware must source from AGENTS.md."""
        assert 'sources=["./AGENTS.md"]' in template_content

    def test_has_patch_tool_calls_middleware(self, template_content):
        """PatchToolCallsMiddleware must be in the middleware stack."""
        assert "PatchToolCallsMiddleware" in template_content

    def test_has_anthropic_prompt_caching_middleware(self, template_content):
        """AnthropicPromptCachingMiddleware must be in the middleware stack."""
        assert "AnthropicPromptCachingMiddleware" in template_content

    def test_no_filesystem_middleware(self, template_content):
        """FilesystemMiddleware must NOT be in the middleware stack."""
        # FilesystemBackend is fine (used by MemoryMiddleware), but
        # FilesystemMiddleware is banned (it injects 9 tools)
        assert "FilesystemMiddleware" not in template_content.replace(
            "FilesystemBackend", ""
        ), "Coach must not use FilesystemMiddleware — it injects 9 tools"

    def test_middleware_passed_to_create_agent(self, template_content):
        """middleware= must be passed to create_agent()."""
        assert "middleware=middleware" in template_content


# ===================================================================
# Placeholder Usage
# ===================================================================


class TestPlaceholders:
    """Verify {{ProjectName}} placeholders are used correctly."""

    def test_uses_project_name_placeholder(self, template_content):
        """Template must use {{ProjectName}} for project-specific imports."""
        assert "{{ProjectName}}" in template_content

    def test_no_hardcoded_deepagents_import(self, template_content):
        """Must not have hardcoded 'from deepagents' imports."""
        lines = template_content.splitlines()
        for line in lines:
            if line.strip().startswith("from") and "deepagents" in line:
                if "{{ProjectName}}" not in line:
                    pytest.fail(
                        f"Hardcoded 'deepagents' import found: {line.strip()}\n"
                        "Use {{ProjectName}} placeholder instead"
                    )


# ===================================================================
# Template Structure
# ===================================================================


class TestTemplateStructure:
    """Verify overall template structure and documentation."""

    def test_has_d5_invariant_docstring(self, template_content):
        """Template must document the D5 invariant."""
        assert "D5" in template_content

    def test_has_tool_separation_contract(self, template_content):
        """Template must include the tool separation contract."""
        assert "TOOL SEPARATION CONTRACT" in template_content

    def test_function_exists(self, parsed_tree):
        """create_coach function must exist."""
        func_names = [
            node.name
            for node in ast.walk(parsed_tree)
            if isinstance(node, ast.FunctionDef)
        ]
        assert "create_coach" in func_names

    def test_function_has_model_and_domain_prompt_params(self, parsed_tree):
        """create_coach must accept model and domain_prompt parameters."""
        for node in ast.walk(parsed_tree):
            if isinstance(node, ast.FunctionDef) and node.name == "create_coach":
                param_names = [arg.arg for arg in node.args.args]
                assert "model" in param_names
                assert "domain_prompt" in param_names
                return
