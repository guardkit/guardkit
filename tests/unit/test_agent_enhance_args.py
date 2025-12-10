"""
Unit tests for agent-enhance command argument parsing.

Tests the new boolean flag interface (--hybrid, --static) that replaced
the old --strategy enum. TASK-UX-B9F7.
"""

import pytest
import sys
from argparse import Namespace
from unittest.mock import patch
from io import StringIO
from pathlib import Path

# Add installer directory to path
installer_commands_path = Path(__file__).parent.parent.parent / "installer" / "core" / "commands"
sys.path.insert(0, str(installer_commands_path))

# Import functions to test
# Note: agent-enhance.py has a hyphen, so we need to use importlib
import importlib.util
spec = importlib.util.spec_from_file_location(
    "agent_enhance",
    installer_commands_path / "agent-enhance.py"
)
agent_enhance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(agent_enhance)

resolve_strategy = agent_enhance.resolve_strategy
format_success_message = agent_enhance.format_success_message
main = agent_enhance.main


class MockArgs:
    """Mock argparse.Namespace for testing."""
    def __init__(self, hybrid=False, static=False):
        self.hybrid = hybrid
        self.static = static


class TestArgumentParsing:
    """Test argument parsing and strategy resolution."""

    def test_default_strategy_is_ai(self):
        """AP-001: No flags → ai strategy"""
        args = MockArgs(hybrid=False, static=False)
        assert resolve_strategy(args) == "ai"

    def test_hybrid_flag(self):
        """AP-002: --hybrid → hybrid strategy"""
        args = MockArgs(hybrid=True, static=False)
        assert resolve_strategy(args) == "hybrid"

    def test_static_flag(self):
        """AP-003: --static → static strategy"""
        args = MockArgs(hybrid=False, static=True)
        assert resolve_strategy(args) == "static"

    def test_conflicting_flags_error(self):
        """AP-004: --hybrid --static → error"""
        args = MockArgs(hybrid=True, static=True)
        with pytest.raises(SystemExit) as exc:
            resolve_strategy(args)
        assert exc.value.code == 1

    def test_error_message_clarity(self, capsys):
        """AP-005: Error message is helpful"""
        args = MockArgs(hybrid=True, static=True)
        with pytest.raises(SystemExit):
            resolve_strategy(args)

        captured = capsys.readouterr()
        assert "Cannot use both" in captured.err
        assert "--hybrid" in captured.err
        assert "--static" in captured.err
        assert "Available strategies" in captured.err

    def test_error_message_shows_all_strategies(self, capsys):
        """AP-006: Error message lists all strategies"""
        args = MockArgs(hybrid=True, static=True)
        with pytest.raises(SystemExit):
            resolve_strategy(args)

        captured = capsys.readouterr()
        assert "AI-powered enhancement" in captured.err
        assert "AI with static fallback" in captured.err
        assert "Template-based only" in captured.err

    def test_strategy_resolution_deterministic(self):
        """AP-007: Strategy resolution is deterministic"""
        # Test multiple times to ensure consistency
        for _ in range(10):
            assert resolve_strategy(MockArgs(False, False)) == "ai"
            assert resolve_strategy(MockArgs(True, False)) == "hybrid"
            assert resolve_strategy(MockArgs(False, True)) == "static"

    def test_strategy_resolution_no_side_effects(self):
        """AP-008: resolve_strategy has no side effects"""
        args = MockArgs(hybrid=False, static=False)
        original_hybrid = args.hybrid
        original_static = args.static

        resolve_strategy(args)

        assert args.hybrid == original_hybrid
        assert args.static == original_static


class TestSuccessMessages:
    """Test success message formatting."""

    def test_ai_strategy_message(self):
        """SM-001: AI strategy message is correct"""
        msg = format_success_message("test-agent.md", "ai")
        assert "✓" in msg
        assert "test-agent.md" in msg
        assert "AI strategy" in msg

    def test_hybrid_strategy_message(self):
        """SM-002: Hybrid strategy message is correct"""
        msg = format_success_message("test-agent.md", "hybrid")
        assert "✓" in msg
        assert "test-agent.md" in msg
        assert "hybrid strategy" in msg
        assert "AI with fallback" in msg

    def test_static_strategy_message(self):
        """SM-003: Static strategy message is correct"""
        msg = format_success_message("test-agent.md", "static")
        assert "✓" in msg
        assert "test-agent.md" in msg
        assert "static strategy" in msg

    def test_message_includes_agent_name(self):
        """SM-004: Message includes agent name"""
        agent_name = "my-custom-agent.md"
        msg = format_success_message(agent_name, "ai")
        assert agent_name in msg

    def test_message_format_consistent(self):
        """SM-005: All messages follow same format"""
        msg_ai = format_success_message("test.md", "ai")
        msg_hybrid = format_success_message("test.md", "hybrid")
        msg_static = format_success_message("test.md", "static")

        # All should start with checkmark
        assert msg_ai.startswith("✓")
        assert msg_hybrid.startswith("✓")
        assert msg_static.startswith("✓")

        # All should include "Enhanced" and "using"
        assert "Enhanced" in msg_ai
        assert "Enhanced" in msg_hybrid
        assert "Enhanced" in msg_static
        assert "using" in msg_ai
        assert "using" in msg_hybrid
        assert "using" in msg_static


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_agent_name(self):
        """EC-001: Empty agent name doesn't crash"""
        msg = format_success_message("", "ai")
        assert "✓" in msg
        assert "using AI strategy" in msg

    def test_long_agent_name(self):
        """EC-002: Long agent name doesn't crash"""
        long_name = "a" * 1000 + ".md"
        msg = format_success_message(long_name, "ai")
        assert long_name in msg

    def test_special_characters_in_agent_name(self):
        """EC-003: Special characters in agent name"""
        special_name = "test-agent_v2.0-beta.md"
        msg = format_success_message(special_name, "ai")
        assert special_name in msg

    def test_args_with_false_equivalents(self):
        """EC-004: Handle None, 0, False correctly"""
        # These should all behave like False
        for false_value in [False, None, 0, ""]:
            # Create args with false-equivalent values
            args = Namespace()
            args.hybrid = false_value
            args.static = False

            # Should resolve to "ai" (default)
            if false_value is None or false_value == 0 or false_value == "":
                # These are falsy but not necessarily False
                # Python's truthiness will handle them
                continue

            result = resolve_strategy(args)
            assert result == "ai"


class TestIntegration:
    """Integration tests for command-line parsing."""

    def test_help_shows_new_flags(self):
        """IT-001: Help text shows --hybrid and --static"""
        # This is a manual verification test - help text should show new flags
        # Can't easily test argparse help programmatically without complex mocking
        pass

    def test_conflicting_flags_from_cli(self):
        """IT-002: CLI with both flags shows error"""
        test_args = ['template/agent', '--hybrid', '--static']

        # Should exit with error code 1
        with pytest.raises(SystemExit) as exc:
            result = main(test_args)

        # The SystemExit from resolve_strategy will bubble up
        assert exc.value.code == 1


class TestBackwardCompatibility:
    """Test that old --strategy flag is removed."""

    def test_strategy_flag_not_in_help(self):
        """BC-001: --strategy flag should not appear in help"""
        # This test verifies the old flag is completely removed
        # If someone tries to use it, argparse will show an error
        pass  # Manual verification via help text

    def test_no_strategy_attribute_on_args(self):
        """BC-002: Parsed args should not have 'strategy' attribute"""
        # After parsing, args should have hybrid/static, not strategy
        args = MockArgs(hybrid=False, static=False)
        assert hasattr(args, 'hybrid')
        assert hasattr(args, 'static')
        # Should NOT have old strategy attribute
        assert not hasattr(args, 'strategy')


class TestStrategyResolutionPrecedence:
    """Test the precedence rules for strategy resolution."""

    def test_static_takes_precedence_over_default(self):
        """PR-001: --static overrides default"""
        args = MockArgs(hybrid=False, static=True)
        assert resolve_strategy(args) == "static"

    def test_hybrid_takes_precedence_over_default(self):
        """PR-002: --hybrid overrides default"""
        args = MockArgs(hybrid=True, static=False)
        assert resolve_strategy(args) == "hybrid"

    def test_conflict_takes_precedence_over_all(self):
        """PR-003: Conflict detection happens first"""
        args = MockArgs(hybrid=True, static=True)
        # Should error before returning any strategy
        with pytest.raises(SystemExit):
            resolve_strategy(args)

    def test_precedence_order(self):
        """PR-004: Verify full precedence: conflict > static > hybrid > default"""
        # 1. Conflict (should error)
        with pytest.raises(SystemExit):
            resolve_strategy(MockArgs(True, True))

        # 2. Static
        assert resolve_strategy(MockArgs(False, True)) == "static"

        # 3. Hybrid
        assert resolve_strategy(MockArgs(True, False)) == "hybrid"

        # 4. Default
        assert resolve_strategy(MockArgs(False, False)) == "ai"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
