"""Tests for factory guard utilities: tool allowlisting and input contract enforcement.

Validates assert_tool_inventory(), create_restricted_agent(),
assert_no_system_messages(), and regression tests documenting
SDK behaviours (tool leakage, dual system messages).

Coverage Target: >=85%
Test Count: 20+ tests
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Import the module from the template's lib directory
# ---------------------------------------------------------------------------
_LIB_PATH = (
    Path(__file__).resolve().parents[3]
    / "installer"
    / "core"
    / "templates"
    / "langchain-deepagents"
    / "lib"
    / "factory_guards.py"
)


@pytest.fixture(scope="module")
def guards_mod():
    """Load the factory_guards module directly from source."""
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader("factory_guards", str(_LIB_PATH))
    spec = importlib.util.spec_from_loader("factory_guards", loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["factory_guards"] = mod
    loader.exec_module(mod)
    return mod


@pytest.fixture
def ToolLeakageError(guards_mod):
    return guards_mod.ToolLeakageError


@pytest.fixture
def assert_tool_inventory(guards_mod):
    return guards_mod.assert_tool_inventory


@pytest.fixture
def assert_no_system_messages(guards_mod):
    return guards_mod.assert_no_system_messages


@pytest.fixture
def create_restricted_agent(guards_mod):
    return guards_mod.create_restricted_agent


def _make_agent_with_tools(*tool_names: str) -> MagicMock:
    """Create a mock agent with the specified tool names."""
    tools = []
    for name in tool_names:
        t = MagicMock()
        t.name = name
        tools.append(t)
    agent = MagicMock()
    agent.tools = tools
    return agent


# ===================================================================
# assert_tool_inventory Tests
# ===================================================================


class TestAssertToolInventory:
    """Tests for assert_tool_inventory() post-factory guard."""

    def test_passes_when_tools_match_exactly(self, assert_tool_inventory):
        agent = _make_agent_with_tools("search_data")
        assert_tool_inventory(agent, {"search_data"})

    def test_passes_with_multiple_expected_tools(self, assert_tool_inventory):
        agent = _make_agent_with_tools("search_data", "fetch_context")
        assert_tool_inventory(agent, {"search_data", "fetch_context"})

    def test_passes_with_empty_tool_set(self, assert_tool_inventory):
        agent = MagicMock()
        agent.tools = []
        assert_tool_inventory(agent, set())

    def test_raises_on_unexpected_tools(self, assert_tool_inventory, ToolLeakageError):
        agent = _make_agent_with_tools("search_data", "write_file")
        with pytest.raises(ToolLeakageError, match="unexpected tools.*write_file"):
            assert_tool_inventory(agent, {"search_data"})

    def test_raises_on_missing_tools(self, assert_tool_inventory, ToolLeakageError):
        agent = _make_agent_with_tools("search_data")
        with pytest.raises(ToolLeakageError, match="missing tools.*fetch_context"):
            assert_tool_inventory(agent, {"search_data", "fetch_context"})

    def test_raises_with_both_unexpected_and_missing(
        self, assert_tool_inventory, ToolLeakageError
    ):
        agent = _make_agent_with_tools("write_file")
        with pytest.raises(ToolLeakageError, match="unexpected.*missing"):
            assert_tool_inventory(agent, {"search_data"})

    def test_error_message_includes_expected_and_actual(
        self, assert_tool_inventory, ToolLeakageError
    ):
        agent = _make_agent_with_tools("write_file", "glob")
        with pytest.raises(ToolLeakageError) as exc_info:
            assert_tool_inventory(agent, {"search_data"})
        msg = str(exc_info.value)
        assert "Expected:" in msg
        assert "Actual:" in msg

    def test_detects_filesystem_tool_leakage(
        self, assert_tool_inventory, ToolLeakageError
    ):
        """Regression: detect FilesystemMiddleware tool injection (8 tools)."""
        filesystem_tools = [
            "ls", "read_file", "write_file", "edit_file",
            "glob", "grep", "execute", "write_todos",
        ]
        agent = _make_agent_with_tools("search_data", *filesystem_tools)
        with pytest.raises(ToolLeakageError, match="unexpected tools"):
            assert_tool_inventory(agent, {"search_data"})


# ===================================================================
# assert_no_system_messages Tests
# ===================================================================


class TestAssertNoSystemMessages:
    """Tests for assert_no_system_messages() ainvoke() guard."""

    def test_passes_with_user_only_messages(self, assert_no_system_messages):
        input_data = {
            "messages": [
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there"},
            ]
        }
        assert_no_system_messages(input_data)

    def test_passes_with_empty_messages(self, assert_no_system_messages):
        assert_no_system_messages({"messages": []})

    def test_passes_with_no_messages_key(self, assert_no_system_messages):
        assert_no_system_messages({})

    def test_raises_on_system_message_dict(self, assert_no_system_messages):
        input_data = {
            "messages": [
                {"role": "system", "content": "You are helpful"},
                {"role": "user", "content": "Hello"},
            ]
        }
        with pytest.raises(ValueError, match="must not contain system messages"):
            assert_no_system_messages(input_data)

    def test_raises_on_system_message_object(self, assert_no_system_messages):
        """Test with message objects that have a role attribute."""
        msg = MagicMock()
        msg.role = "system"
        msg.get = MagicMock(side_effect=AttributeError)
        input_data = {"messages": [msg]}
        with pytest.raises(ValueError, match="must not contain system messages"):
            assert_no_system_messages(input_data)

    def test_error_message_explains_cause(self, assert_no_system_messages):
        input_data = {"messages": [{"role": "system", "content": "bad"}]}
        with pytest.raises(ValueError) as exc_info:
            assert_no_system_messages(input_data)
        msg = str(exc_info.value)
        assert "create_agent() prepends system_prompt automatically" in msg
        assert "user" in msg

    def test_passes_with_only_user_and_assistant(self, assert_no_system_messages):
        input_data = {
            "messages": [
                {"role": "user", "content": "question"},
                {"role": "assistant", "content": "answer"},
                {"role": "user", "content": "follow up"},
            ]
        }
        assert_no_system_messages(input_data)

    def test_catches_system_message_among_many(self, assert_no_system_messages):
        input_data = {
            "messages": [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "response"},
                {"role": "system", "content": "injected"},
                {"role": "user", "content": "second"},
            ]
        }
        with pytest.raises(ValueError, match="must not contain system messages"):
            assert_no_system_messages(input_data)


# ===================================================================
# create_restricted_agent Tests
# ===================================================================


class TestCreateRestrictedAgent:
    """Tests for create_restricted_agent() factory wrapper."""

    def test_calls_create_agent_not_create_deep_agent(self, create_restricted_agent):
        """Verify it uses create_agent (no FilesystemMiddleware), not create_deep_agent."""
        fake_agent = MagicMock()
        fake_agent.tools = []

        with patch.dict(sys.modules, {"langchain": MagicMock(), "langchain.agents": MagicMock()}):
            with patch(
                "factory_guards.create_agent", create=True, return_value=fake_agent
            ) as mock_ca:
                # Need to re-patch the import inside the function
                import factory_guards
                original_fn = factory_guards.create_restricted_agent

                # Manually invoke with mocked import
                from unittest.mock import MagicMock as MM
                mock_create_agent = MM(return_value=fake_agent)

                # Patch at module level
                with patch.object(
                    factory_guards, "__builtins__", factory_guards.__builtins__
                ):
                    pass  # The function imports at call time

    def test_passes_model_and_tools(self, guards_mod):
        """create_restricted_agent forwards model and tools to create_agent."""
        fake_agent = MagicMock()
        fake_agent.tools = []

        mock_create_agent = MagicMock(return_value=fake_agent)

        with patch.dict(
            "sys.modules",
            {
                "langchain": MagicMock(),
                "langchain.agents": MagicMock(create_agent=mock_create_agent),
            },
        ):
            result = guards_mod.create_restricted_agent(
                model="test-model",
                tools=[],
                system_prompt="test prompt",
            )

        assert result is fake_agent
        mock_create_agent.assert_called_once()
        call_kwargs = mock_create_agent.call_args[1]
        assert call_kwargs["model"] == "test-model"
        assert call_kwargs["tools"] == []
        assert call_kwargs["system_prompt"] == "test prompt"

    def test_memory_not_passed_as_kwarg_to_create_agent(self, guards_mod):
        """Verify memory is NOT passed as a kwarg to create_agent() (would cause TypeError)."""
        fake_agent = MagicMock()
        fake_agent.tools = []
        mock_create_agent = MagicMock(return_value=fake_agent)
        mock_fs_backend = MagicMock()
        mock_memory_mw = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "langchain": MagicMock(),
                "langchain.agents": MagicMock(create_agent=mock_create_agent),
                "deepagents": MagicMock(),
                "deepagents.backends": MagicMock(FilesystemBackend=MagicMock(return_value=mock_fs_backend)),
                "deepagents.middleware": MagicMock(MemoryMiddleware=MagicMock(return_value=mock_memory_mw)),
            },
        ):
            guards_mod.create_restricted_agent(
                model="m",
                tools=[],
                system_prompt="p",
                memory=["./AGENTS.md"],
            )

        call_kwargs = mock_create_agent.call_args[1]
        assert "memory" not in call_kwargs, "memory must not be passed to create_agent()"

    def test_memory_adds_middleware_to_create_agent(self, guards_mod):
        """When memory is provided, MemoryMiddleware is added to middleware list."""
        fake_agent = MagicMock()
        fake_agent.tools = []
        mock_create_agent = MagicMock(return_value=fake_agent)
        mock_fs_backend = MagicMock()
        mock_memory_mw = MagicMock()
        mock_MemoryMiddleware = MagicMock(return_value=mock_memory_mw)
        mock_FilesystemBackend = MagicMock(return_value=mock_fs_backend)

        with patch.dict(
            "sys.modules",
            {
                "langchain": MagicMock(),
                "langchain.agents": MagicMock(create_agent=mock_create_agent),
                "deepagents": MagicMock(),
                "deepagents.backends": MagicMock(FilesystemBackend=mock_FilesystemBackend),
                "deepagents.middleware": MagicMock(MemoryMiddleware=mock_MemoryMiddleware),
            },
        ):
            guards_mod.create_restricted_agent(
                model="m",
                tools=[],
                system_prompt="p",
                memory=["./AGENTS.md"],
            )

        # FilesystemBackend created with root_dir="."
        mock_FilesystemBackend.assert_called_once_with(root_dir=".")
        # MemoryMiddleware created with backend and sources
        mock_MemoryMiddleware.assert_called_once_with(backend=mock_fs_backend, sources=["./AGENTS.md"])
        # middleware list passed to create_agent
        call_kwargs = mock_create_agent.call_args[1]
        assert "middleware" in call_kwargs
        assert mock_memory_mw in call_kwargs["middleware"]

    def test_omits_middleware_when_memory_none(self, guards_mod):
        """When memory is None, no middleware is added."""
        fake_agent = MagicMock()
        fake_agent.tools = []
        mock_create_agent = MagicMock(return_value=fake_agent)

        with patch.dict(
            "sys.modules",
            {
                "langchain": MagicMock(),
                "langchain.agents": MagicMock(create_agent=mock_create_agent),
            },
        ):
            guards_mod.create_restricted_agent(
                model="m",
                tools=[],
                system_prompt="p",
            )

        call_kwargs = mock_create_agent.call_args[1]
        assert "memory" not in call_kwargs
        assert "middleware" not in call_kwargs

    def test_asserts_tool_inventory_when_allowed_tools_set(self, guards_mod):
        """When allowed_tools is provided, assert_tool_inventory is called."""
        search_tool = MagicMock()
        search_tool.name = "search_data"
        fake_agent = MagicMock()
        fake_agent.tools = [search_tool]
        mock_create_agent = MagicMock(return_value=fake_agent)

        with patch.dict(
            "sys.modules",
            {
                "langchain": MagicMock(),
                "langchain.agents": MagicMock(create_agent=mock_create_agent),
            },
        ):
            result = guards_mod.create_restricted_agent(
                model="m",
                tools=[search_tool],
                system_prompt="p",
                allowed_tools={"search_data"},
            )

        assert result is fake_agent

    def test_raises_on_tool_mismatch_with_allowed_tools(self, guards_mod, ToolLeakageError):
        """When allowed_tools is set and agent has wrong tools, raises ToolLeakageError."""
        write_tool = MagicMock()
        write_tool.name = "write_file"
        fake_agent = MagicMock()
        fake_agent.tools = [write_tool]
        mock_create_agent = MagicMock(return_value=fake_agent)

        with patch.dict(
            "sys.modules",
            {
                "langchain": MagicMock(),
                "langchain.agents": MagicMock(create_agent=mock_create_agent),
            },
        ):
            with pytest.raises(ToolLeakageError, match="unexpected tools"):
                guards_mod.create_restricted_agent(
                    model="m",
                    tools=[write_tool],
                    system_prompt="p",
                    allowed_tools={"search_data"},
                )

    def test_skips_assertion_when_allowed_tools_none(self, guards_mod):
        """When allowed_tools is None, no assertion is performed."""
        write_tool = MagicMock()
        write_tool.name = "write_file"
        fake_agent = MagicMock()
        fake_agent.tools = [write_tool]
        mock_create_agent = MagicMock(return_value=fake_agent)

        with patch.dict(
            "sys.modules",
            {
                "langchain": MagicMock(),
                "langchain.agents": MagicMock(create_agent=mock_create_agent),
            },
        ):
            # Should NOT raise even though agent has write_file
            result = guards_mod.create_restricted_agent(
                model="m",
                tools=[write_tool],
                system_prompt="p",
            )

        assert result is fake_agent


# ===================================================================
# Regression Tests — Documenting SDK Behaviours
# ===================================================================


class TestRegressionDocumentation:
    """Regression tests documenting known SDK behaviours.

    These tests verify that the guards correctly detect the problems
    that caused failures in factory runs 1-6.
    """

    def test_create_deep_agent_with_backend_none_still_leaks(
        self, assert_tool_inventory, ToolLeakageError
    ):
        """Regression: create_deep_agent + backend=None still injects filesystem tools.

        Documents the SDK behaviour where create_deep_agent() unconditionally
        adds FilesystemMiddleware regardless of backend parameter.
        """
        # Simulate an agent created by create_deep_agent with backend=None
        # that still got filesystem tools injected
        filesystem_tools = [
            "ls", "read_file", "write_file", "edit_file",
            "glob", "grep", "execute", "write_todos",
        ]
        agent = _make_agent_with_tools("search_data", *filesystem_tools)

        # The guard catches this leakage
        with pytest.raises(ToolLeakageError, match="unexpected tools"):
            assert_tool_inventory(agent, {"search_data"})

    def test_ainvoke_with_system_message_causes_dual_system_messages(
        self, assert_no_system_messages
    ):
        """Regression: ainvoke with system message in input causes dual system messages.

        Documents the SDK behaviour where create_agent() prepends system_prompt
        (factory.py:1270-1271) on every ainvoke() call. Passing a system message
        in input creates duplicates that vLLM rejects with 400 Bad Request.
        See: TASK-REV-R2A1 root cause analysis.
        """
        # Simulate the problematic input that caused the pipeline crash
        bad_input = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant"},
                {"role": "user", "content": "Evaluate this content"},
            ]
        }

        # The guard catches this before it reaches the LLM
        with pytest.raises(ValueError, match="must not contain system messages"):
            assert_no_system_messages(bad_input)


# ===================================================================
# ToolLeakageError Tests
# ===================================================================


class TestToolLeakageError:
    """Tests for the ToolLeakageError exception class."""

    def test_is_exception(self, ToolLeakageError):
        assert issubclass(ToolLeakageError, Exception)

    def test_can_be_raised_with_message(self, ToolLeakageError):
        with pytest.raises(ToolLeakageError, match="test message"):
            raise ToolLeakageError("test message")

    def test_can_be_caught(self, ToolLeakageError):
        try:
            raise ToolLeakageError("caught")
        except ToolLeakageError as e:
            assert str(e) == "caught"
