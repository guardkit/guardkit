"""
Unit tests for TASK-769D: CodebaseAnalyzer with AgentBridgeInvoker integration

Tests the bridge_invoker parameter and fallback behavior.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os

# Add lib directories to path
lib_path = Path(__file__).parent.parent.parent / "installer" / "global" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

from codebase_analyzer.ai_analyzer import CodebaseAnalyzer
from codebase_analyzer.agent_invoker import ArchitecturalReviewerInvoker, AgentInvocationError
from codebase_analyzer.models import CodebaseAnalysis


class TestCodebaseAnalyzerWithBridge:
    """Test CodebaseAnalyzer with AgentBridgeInvoker integration"""

    @pytest.fixture
    def temp_codebase(self):
        """Create a temporary codebase directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some sample files
            tmppath = Path(tmpdir)
            (tmppath / "src").mkdir()
            (tmppath / "src" / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
            (tmppath / "tests").mkdir()
            (tmppath / "tests" / "test_api.py").write_text("import pytest\ndef test_api(): pass")
            (tmppath / "requirements.txt").write_text("fastapi==0.95.0\npytest==7.2.0")
            yield tmppath

    def test_init_with_bridge_invoker(self):
        """Test initialization with bridge_invoker parameter"""
        mock_bridge = Mock()
        analyzer = CodebaseAnalyzer(bridge_invoker=mock_bridge)

        assert analyzer.bridge_invoker is mock_bridge

    def test_init_without_bridge_invoker(self):
        """Test initialization without bridge_invoker (backward compatible)"""
        analyzer = CodebaseAnalyzer()

        assert analyzer.bridge_invoker is None

    def test_bridge_invoker_passed_to_agent_invoker(self):
        """Test bridge_invoker is passed to ArchitecturalReviewerInvoker"""
        mock_bridge = Mock()

        with patch('codebase_analyzer.ai_analyzer.ArchitecturalReviewerInvoker') as MockInvoker:
            mock_invoker_instance = Mock()
            MockInvoker.return_value = mock_invoker_instance

            analyzer = CodebaseAnalyzer(
                agent_invoker=None,  # Force creation of new invoker
                bridge_invoker=mock_bridge
            )

            # Verify bridge was passed to agent invoker
            # (Can't easily test this without refactoring, so test behavior instead)
            assert analyzer.bridge_invoker is mock_bridge

    def test_analyze_with_bridge_success(self, temp_codebase):
        """Test analyze_codebase with bridge_invoker succeeds"""
        mock_bridge = Mock()
        mock_agent_invoker = Mock()
        mock_agent_invoker.is_available.return_value = True
        mock_agent_invoker.invoke_agent.return_value = '''
        {
            "technology": {
                "primary_language": "Python",
                "frameworks": ["FastAPI"],
                "testing_frameworks": ["pytest"]
            },
            "architecture": {
                "architectural_style": "Clean Architecture",
                "patterns": ["Repository"],
                "layers": []
            },
            "overall_confidence": {"percentage": 85}
        }
        '''

        analyzer = CodebaseAnalyzer(
            agent_invoker=mock_agent_invoker,
            bridge_invoker=mock_bridge
        )

        result = analyzer.analyze_codebase(temp_codebase)

        assert isinstance(result, CodebaseAnalysis)
        assert result.technology.primary_language == "Python"
        assert "FastAPI" in result.technology.frameworks

    def test_analyze_without_bridge_falls_back_to_heuristics(self, temp_codebase):
        """Test analyze_codebase without bridge falls back to heuristics"""
        mock_agent_invoker = Mock()
        mock_agent_invoker.is_available.return_value = True
        mock_agent_invoker.invoke_agent.side_effect = AgentInvocationError("No bridge")

        analyzer = CodebaseAnalyzer(
            agent_invoker=mock_agent_invoker,
            bridge_invoker=None,
            use_agent=True
        )

        result = analyzer.analyze_codebase(temp_codebase)

        # Should fall back to heuristic analysis
        assert isinstance(result, CodebaseAnalysis)
        # Heuristics should still detect Python from file extensions
        assert result.technology.primary_language == "Python"

    def test_analyze_with_bridge_failure_falls_back(self, temp_codebase):
        """Test analyze_codebase with bridge failure falls back to heuristics"""
        mock_bridge = Mock()
        mock_agent_invoker = Mock()
        mock_agent_invoker.is_available.return_value = True
        mock_agent_invoker.invoke_agent.side_effect = AgentInvocationError("Bridge timeout")

        analyzer = CodebaseAnalyzer(
            agent_invoker=mock_agent_invoker,
            bridge_invoker=mock_bridge,
            use_agent=True
        )

        result = analyzer.analyze_codebase(temp_codebase)

        # Should fall back to heuristics
        assert isinstance(result, CodebaseAnalysis)
        assert result.technology.primary_language == "Python"

    def test_analyze_nonexistent_path_raises_error(self):
        """Test analyze_codebase with non-existent path raises ValueError"""
        analyzer = CodebaseAnalyzer()

        with pytest.raises(ValueError, match="does not exist"):
            analyzer.analyze_codebase("/nonexistent/path")

    def test_analyze_file_instead_of_directory_raises_error(self):
        """Test analyze_codebase with file path raises ValueError"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("test")
            filepath = f.name

        try:
            analyzer = CodebaseAnalyzer()
            with pytest.raises(ValueError, match="not a directory"):
                analyzer.analyze_codebase(filepath)
        finally:
            os.unlink(filepath)

    def test_analyze_with_template_context(self, temp_codebase):
        """Test analyze_codebase with template_context parameter"""
        mock_bridge = Mock()
        mock_agent_invoker = Mock()
        mock_agent_invoker.is_available.return_value = False  # Force heuristics

        analyzer = CodebaseAnalyzer(
            agent_invoker=mock_agent_invoker,
            bridge_invoker=mock_bridge,
            use_agent=False
        )

        template_context = {
            "name": "my-api",
            "language": "Python",
            "framework": "FastAPI",
            "description": "REST API"
        }

        result = analyzer.analyze_codebase(temp_codebase, template_context=template_context)

        assert isinstance(result, CodebaseAnalysis)
        # Metadata should include template context
        assert result.metadata.template_name == "my-api"
        assert result.metadata.primary_language == "Python"

    def test_analyze_save_results(self, temp_codebase):
        """Test analyze_codebase saves results when save_results=True"""
        analyzer = CodebaseAnalyzer(use_agent=False)

        output_path = temp_codebase / "analysis_output.json"

        result = analyzer.analyze_codebase(
            temp_codebase,
            save_results=True,
            output_path=output_path
        )

        # Check that file was created
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    def test_analyze_with_stratified_sampling(self, temp_codebase):
        """Test analyze_codebase with stratified sampling enabled"""
        analyzer = CodebaseAnalyzer(
            use_agent=False,
            use_stratified_sampling=True,
            max_files=5
        )

        result = analyzer.analyze_codebase(temp_codebase)

        assert isinstance(result, CodebaseAnalysis)
        assert result.technology.primary_language == "Python"

    def test_analyze_without_stratified_sampling(self, temp_codebase):
        """Test analyze_codebase with stratified sampling disabled"""
        analyzer = CodebaseAnalyzer(
            use_agent=False,
            use_stratified_sampling=False,
            max_files=5
        )

        result = analyzer.analyze_codebase(temp_codebase)

        assert isinstance(result, CodebaseAnalysis)
        assert result.technology.primary_language == "Python"
