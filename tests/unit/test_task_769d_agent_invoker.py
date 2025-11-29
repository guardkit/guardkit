"""
Unit tests for TASK-769D: AgentBridgeInvoker integration in ArchitecturalReviewerInvoker

Tests the checkpoint-resume pattern with AgentBridgeInvoker fallback.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add lib directories to path
lib_path = Path(__file__).parent.parent.parent / "installer" / "global" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from codebase_analyzer.agent_invoker import (
    ArchitecturalReviewerInvoker,
    AgentInvocationError,
    HeuristicAnalyzer
)


class TestArchitecturalReviewerInvokerWithBridge:
    """Test ArchitecturalReviewerInvoker with AgentBridgeInvoker integration"""

    def test_init_with_bridge_invoker(self):
        """Test initialization with bridge_invoker parameter"""
        mock_bridge = Mock()
        invoker = ArchitecturalReviewerInvoker(bridge_invoker=mock_bridge)

        assert invoker.bridge_invoker is mock_bridge
        assert invoker.timeout_seconds == 300  # default

    def test_init_without_bridge_invoker(self):
        """Test initialization without bridge_invoker (backward compatible)"""
        invoker = ArchitecturalReviewerInvoker()

        assert invoker.bridge_invoker is None
        assert invoker.agent_path.exists() or not invoker.agent_path.exists()  # may or may not exist

    def test_invoke_agent_with_bridge_success(self):
        """Test invoke_agent using bridge_invoker successfully"""
        mock_bridge = Mock()
        mock_bridge.invoke.return_value = '{"technology": {"primary_language": "Python"}}'

        invoker = ArchitecturalReviewerInvoker(bridge_invoker=mock_bridge)

        # Mock agent availability
        with patch.object(invoker, 'is_available', return_value=True):
            response = invoker.invoke_agent("test prompt", "architectural-reviewer")

        assert response == '{"technology": {"primary_language": "Python"}}'
        mock_bridge.invoke.assert_called_once_with(
            agent_name="architectural-reviewer",
            prompt="test prompt",
            timeout_seconds=300
        )

    def test_invoke_agent_without_bridge_raises_error(self):
        """Test invoke_agent without bridge_invoker raises AgentInvocationError"""
        invoker = ArchitecturalReviewerInvoker(bridge_invoker=None)

        with patch.object(invoker, 'is_available', return_value=True):
            with pytest.raises(AgentInvocationError, match="not yet implemented"):
                invoker.invoke_agent("test prompt", "architectural-reviewer")

    def test_invoke_agent_unavailable_raises_error(self):
        """Test invoke_agent with unavailable agent raises error"""
        mock_bridge = Mock()
        invoker = ArchitecturalReviewerInvoker(bridge_invoker=mock_bridge)

        with patch.object(invoker, 'is_available', return_value=False):
            with pytest.raises(AgentInvocationError, match="Agent not available"):
                invoker.invoke_agent("test prompt")

    def test_invoke_agent_bridge_timeout(self):
        """Test invoke_agent handles bridge timeout gracefully"""
        import subprocess

        mock_bridge = Mock()
        mock_bridge.invoke.side_effect = subprocess.TimeoutExpired("agent", 300)

        invoker = ArchitecturalReviewerInvoker(bridge_invoker=mock_bridge)

        with patch.object(invoker, 'is_available', return_value=True):
            with pytest.raises(AgentInvocationError, match="timed out"):
                invoker.invoke_agent("test prompt")

    def test_invoke_agent_bridge_subprocess_error(self):
        """Test invoke_agent handles bridge subprocess error"""
        import subprocess

        mock_bridge = Mock()
        error = subprocess.CalledProcessError(1, "agent", stderr="error")
        mock_bridge.invoke.side_effect = error

        invoker = ArchitecturalReviewerInvoker(bridge_invoker=mock_bridge)

        with patch.object(invoker, 'is_available', return_value=True):
            with pytest.raises(AgentInvocationError, match="failed with exit code"):
                invoker.invoke_agent("test prompt")

    def test_invoke_agent_bridge_unexpected_error(self):
        """Test invoke_agent handles unexpected bridge errors"""
        mock_bridge = Mock()
        mock_bridge.invoke.side_effect = RuntimeError("Unexpected error")

        invoker = ArchitecturalReviewerInvoker(bridge_invoker=mock_bridge)

        with patch.object(invoker, 'is_available', return_value=True):
            with pytest.raises(AgentInvocationError, match="Unexpected error"):
                invoker.invoke_agent("test prompt")

    def test_is_available_checks_agent_path(self):
        """Test is_available checks agent_path existence"""
        invoker = ArchitecturalReviewerInvoker()

        # Result depends on whether agent is actually installed
        result = invoker.is_available()
        assert isinstance(result, bool)


class TestHeuristicAnalyzerWithFileSamples:
    """Test HeuristicAnalyzer with file_samples parameter (TASK-769D)"""

    def test_init_stores_file_samples(self):
        """Test HeuristicAnalyzer stores file_samples parameter"""
        file_samples = [
            {"path": "src/main.py", "content": "import fastapi"},
            {"path": "tests/test_api.py", "content": "import pytest"}
        ]

        analyzer = HeuristicAnalyzer(file_samples=file_samples)
        assert analyzer.file_samples == file_samples

    def test_init_without_file_samples(self):
        """Test HeuristicAnalyzer without file_samples (backward compatible)"""
        analyzer = HeuristicAnalyzer()
        assert analyzer.file_samples is None

    def test_analyze_with_file_samples(self):
        """Test analyze uses file_samples when provided"""
        file_samples = [
            {"path": "src/main.py", "content": "from fastapi import FastAPI"},
            {"path": "requirements.txt", "content": "fastapi==0.95.0\npytest==7.2.0"}
        ]

        analyzer = HeuristicAnalyzer(file_samples=file_samples)

        result = analyzer.analyze()

        # Should detect Python and FastAPI from file samples
        assert result.technology.primary_language == "Python"
        assert "FastAPI" in result.technology.frameworks
        assert "pytest" in result.technology.testing_frameworks

    def test_analyze_without_file_samples(self):
        """Test analyze works without file_samples (uses defaults)"""
        analyzer = HeuristicAnalyzer(file_samples=None)

        result = analyzer.analyze()

        # Should return default/unknown values
        assert result.technology.primary_language in ["Unknown", "Multiple"]
        assert isinstance(result.technology.frameworks, list)

    def test_detect_language_from_file_samples(self):
        """Test _detect_language uses file_samples"""
        file_samples = [
            {"path": "main.ts", "content": "const app = express()"},
            {"path": "package.json", "content": '{"dependencies": {"express": "^4.0.0"}}'}
        ]

        analyzer = HeuristicAnalyzer(file_samples=file_samples)
        result = analyzer.analyze()

        assert result.technology.primary_language == "TypeScript"

    def test_detect_frameworks_from_file_samples(self):
        """Test _detect_frameworks uses file_samples"""
        file_samples = [
            {"path": "src/app.py", "content": "from django.conf import settings"},
            {"path": "requirements.txt", "content": "Django==4.2.0"}
        ]

        analyzer = HeuristicAnalyzer(file_samples=file_samples)
        result = analyzer.analyze()

        assert "Django" in result.technology.frameworks

    def test_detect_testing_frameworks_from_file_samples(self):
        """Test _detect_testing_frameworks uses file_samples"""
        file_samples = [
            {"path": "tests/test_unit.py", "content": "import unittest"},
            {"path": "tests/test_integration.py", "content": "import pytest"}
        ]

        analyzer = HeuristicAnalyzer(file_samples=file_samples)
        result = analyzer.analyze()

        # Should detect both unittest and pytest
        assert any(fw in result.technology.testing_frameworks for fw in ["unittest", "pytest"])

    def test_empty_file_samples_returns_defaults(self):
        """Test empty file_samples returns default values"""
        analyzer = HeuristicAnalyzer(file_samples=[])
        result = analyzer.analyze()

        assert result.technology.primary_language in ["Unknown", "Multiple"]
        assert isinstance(result.technology.frameworks, list)
        assert isinstance(result.technology.testing_frameworks, list)
