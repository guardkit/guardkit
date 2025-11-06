"""
Unit Tests for Codebase Analyzer

Tests individual components of the codebase analyzer module:
- Models and validation
- Prompt building
- Response parsing
- Serialization
- Agent invocation (mocked)

Following Python testing best practices:
- Pytest framework
- Clear test names describing what is tested
- Arrange-Act-Assert pattern
- Mocking external dependencies
"""

import json
import pytest
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from lib.codebase_analyzer.models import (
    CodebaseAnalysis,
    TechnologyInfo,
    ArchitectureInfo,
    QualityInfo,
    ExampleFile,
    LayerInfo,
    ConfidenceScore,
    ConfidenceLevel,
    ParseError,
)
from lib.codebase_analyzer.prompt_builder import PromptBuilder, FileCollector
from lib.codebase_analyzer.response_parser import ResponseParser, FallbackResponseBuilder
from lib.codebase_analyzer.serializer import AnalysisSerializer
from lib.codebase_analyzer.agent_invoker import ArchitecturalReviewerInvoker, HeuristicAnalyzer
from lib.codebase_analyzer.ai_analyzer import CodebaseAnalyzer


class TestModels:
    """Test Pydantic models and validation."""

    def test_confidence_score_validation(self):
        """Test confidence score validation logic."""
        # High confidence (90%+)
        conf = ConfidenceScore(
            level=ConfidenceLevel.HIGH,
            percentage=95.0,
            reasoning="Very confident"
        )
        assert conf.level == ConfidenceLevel.HIGH
        assert conf.percentage == 95.0

        # Invalid: high percentage with low level should fail
        with pytest.raises(ValueError):
            ConfidenceScore(
                level=ConfidenceLevel.LOW,
                percentage=95.0
            )

    def test_technology_info_creation(self):
        """Test TechnologyInfo model creation."""
        conf = ConfidenceScore(
            level=ConfidenceLevel.HIGH,
            percentage=90.0
        )

        tech = TechnologyInfo(
            primary_language="Python",
            frameworks=["FastAPI", "Pydantic"],
            testing_frameworks=["pytest"],
            build_tools=["pip"],
            databases=["PostgreSQL"],
            infrastructure=["Docker"],
            confidence=conf
        )

        assert tech.primary_language == "Python"
        assert "FastAPI" in tech.frameworks
        assert tech.confidence.level == ConfidenceLevel.HIGH

    def test_codebase_analysis_overall_confidence(self):
        """Test overall confidence calculation."""
        conf_high = ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)
        conf_medium = ConfidenceScore(level=ConfidenceLevel.MEDIUM, percentage=80.0)
        conf_low = ConfidenceScore(level=ConfidenceLevel.LOW, percentage=60.0)

        tech = TechnologyInfo(
            primary_language="Python",
            frameworks=[],
            confidence=conf_high
        )

        arch = ArchitectureInfo(
            patterns=[],
            architectural_style="Layered",
            layers=[],
            key_abstractions=[],
            dependency_flow="Inward",
            confidence=conf_medium
        )

        quality = QualityInfo(
            overall_score=70.0,
            solid_compliance=70.0,
            dry_compliance=70.0,
            yagni_compliance=70.0,
            confidence=conf_low
        )

        analysis = CodebaseAnalysis(
            codebase_path="/test",
            technology=tech,
            architecture=arch,
            quality=quality
        )

        overall = analysis.overall_confidence
        # Average: (90 + 80 + 60) / 3 = 76.67 -> MEDIUM
        assert overall.level == ConfidenceLevel.MEDIUM
        assert 76.0 <= overall.percentage <= 77.0

    def test_codebase_analysis_get_summary(self):
        """Test summary generation."""
        conf = ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=95.0)

        tech = TechnologyInfo(
            primary_language="Python",
            frameworks=["FastAPI"],
            testing_frameworks=["pytest"],
            build_tools=["pip"],
            databases=[],
            infrastructure=[],
            confidence=conf
        )

        arch = ArchitectureInfo(
            patterns=["Repository"],
            architectural_style="Clean Architecture",
            layers=[],
            key_abstractions=["User"],
            dependency_flow="Inward toward domain",
            confidence=conf
        )

        quality = QualityInfo(
            overall_score=85.0,
            solid_compliance=80.0,
            dry_compliance=85.0,
            yagni_compliance=90.0,
            confidence=conf
        )

        analysis = CodebaseAnalysis(
            codebase_path="/test/project",
            technology=tech,
            architecture=arch,
            quality=quality
        )

        summary = analysis.get_summary()
        assert "Python" in summary
        assert "FastAPI" in summary
        assert "85.0/100" in summary
        assert "Repository" in summary


class TestPromptBuilder:
    """Test prompt construction."""

    def test_build_analysis_prompt_with_context(self):
        """Test prompt building with template context."""
        template_context = {
            "name": "FastAPI Template",
            "language": "Python",
            "framework": "FastAPI",
            "description": "API template"
        }

        builder = PromptBuilder(template_context=template_context)

        file_samples = [
            {"path": "src/main.py", "content": "from fastapi import FastAPI\n\napp = FastAPI()"}
        ]

        prompt = builder.build_analysis_prompt(
            codebase_path=Path("/test"),
            file_samples=file_samples,
            directory_structure="src/\n  main.py",
            max_files=10
        )

        # Check template context is included
        assert "FastAPI Template" in prompt
        assert "Python" in prompt

        # Check file sample is included
        assert "src/main.py" in prompt
        assert "from fastapi import FastAPI" in prompt

        # Check directory structure is included
        assert "Directory Structure" in prompt

        # Check analysis request is included
        assert "Analysis Request" in prompt
        assert "JSON" in prompt

    def test_build_quick_analysis_prompt(self):
        """Test quick analysis prompt building."""
        builder = PromptBuilder()

        prompt = builder.build_quick_analysis_prompt(
            codebase_path=Path("/test"),
            structure_summary="Standard Python project with src/ and tests/"
        )

        assert "Quick Analysis" in prompt
        assert "/test" in prompt


class TestFileCollector:
    """Test file collection from codebase."""

    @pytest.fixture
    def temp_codebase(self, tmp_path):
        """Create a temporary codebase for testing."""
        # Create directory structure
        src = tmp_path / "src"
        src.mkdir()
        tests = tmp_path / "tests"
        tests.mkdir()

        # Create some files
        (src / "main.py").write_text("# Main file\nprint('Hello')")
        (src / "service.py").write_text("# Service\nclass UserService:\n    pass")
        (tests / "test_main.py").write_text("# Test\ndef test_main():\n    pass")

        return tmp_path

    def test_collect_samples(self, temp_codebase):
        """Test collecting file samples."""
        collector = FileCollector(temp_codebase, max_files=10)
        samples = collector.collect_samples()

        assert len(samples) > 0
        assert any("main.py" in s["path"] for s in samples)
        assert all("content" in s for s in samples)

    def test_get_directory_tree(self, temp_codebase):
        """Test directory tree generation."""
        collector = FileCollector(temp_codebase, max_files=10)
        tree = collector.get_directory_tree(max_depth=3)

        assert "src" in tree
        assert "tests" in tree
        assert "main.py" in tree or "service.py" in tree


class TestResponseParser:
    """Test response parsing and validation."""

    def test_parse_analysis_response_with_json_block(self):
        """Test parsing response with JSON in markdown code block."""
        response = """
Here's the analysis:

```json
{
  "technology": {
    "primary_language": "Python",
    "frameworks": ["FastAPI"],
    "testing_frameworks": ["pytest"],
    "build_tools": ["pip"],
    "databases": [],
    "infrastructure": [],
    "confidence": {"level": "high", "percentage": 90.0}
  },
  "architecture": {
    "patterns": ["Repository"],
    "architectural_style": "Clean Architecture",
    "layers": [],
    "key_abstractions": ["User"],
    "dependency_flow": "Inward",
    "confidence": {"level": "medium", "percentage": 85.0}
  },
  "quality": {
    "overall_score": 80.0,
    "solid_compliance": 75.0,
    "dry_compliance": 80.0,
    "yagni_compliance": 85.0,
    "code_smells": [],
    "strengths": ["Clear structure"],
    "improvements": ["Add more tests"],
    "confidence": {"level": "medium", "percentage": 75.0}
  },
  "example_files": []
}
```
"""

        parser = ResponseParser()
        analysis = parser.parse_analysis_response(
            response=response,
            codebase_path="/test",
            template_context=None
        )

        assert analysis.technology.primary_language == "Python"
        assert "FastAPI" in analysis.technology.frameworks
        assert analysis.architecture.architectural_style == "Clean Architecture"
        assert analysis.quality.overall_score == 80.0
        assert analysis.agent_used is True

    def test_parse_analysis_response_invalid_json(self):
        """Test parsing with invalid JSON raises ParseError."""
        response = "This is not valid JSON"

        parser = ResponseParser()

        with pytest.raises(ParseError):
            parser.parse_analysis_response(
                response=response,
                codebase_path="/test",
                template_context=None
            )

    def test_validate_analysis(self):
        """Test analysis validation."""
        conf = ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)

        tech = TechnologyInfo(
            primary_language="Python",
            frameworks=["FastAPI"],
            confidence=conf
        )

        arch = ArchitectureInfo(
            patterns=["Repository"],
            architectural_style="Clean Architecture",
            layers=[],
            key_abstractions=[],
            dependency_flow="Inward",
            confidence=conf
        )

        quality = QualityInfo(
            overall_score=80.0,
            solid_compliance=75.0,
            dry_compliance=80.0,
            yagni_compliance=85.0,
            confidence=conf
        )

        analysis = CodebaseAnalysis(
            codebase_path="/test",
            technology=tech,
            architecture=arch,
            quality=quality,
            example_files=[
                ExampleFile(
                    path="src/main.py",
                    purpose="Main entry point"
                )
            ]
        )

        parser = ResponseParser()
        is_valid, issues = parser.validate_analysis(analysis)

        assert is_valid is True
        assert len(issues) == 0


class TestAnalysisSerializer:
    """Test serialization and deserialization."""

    @pytest.fixture
    def sample_analysis(self):
        """Create a sample analysis for testing."""
        conf = ConfidenceScore(level=ConfidenceLevel.HIGH, percentage=90.0)

        tech = TechnologyInfo(
            primary_language="Python",
            frameworks=["FastAPI"],
            testing_frameworks=["pytest"],
            build_tools=["pip"],
            databases=[],
            infrastructure=[],
            confidence=conf
        )

        arch = ArchitectureInfo(
            patterns=["Repository"],
            architectural_style="Clean Architecture",
            layers=[],
            key_abstractions=["User"],
            dependency_flow="Inward",
            confidence=conf
        )

        quality = QualityInfo(
            overall_score=80.0,
            solid_compliance=75.0,
            dry_compliance=80.0,
            yagni_compliance=85.0,
            confidence=conf
        )

        return CodebaseAnalysis(
            codebase_path="/test/project",
            technology=tech,
            architecture=arch,
            quality=quality
        )

    def test_save_and_load(self, tmp_path, sample_analysis):
        """Test saving and loading analysis."""
        serializer = AnalysisSerializer(cache_dir=tmp_path)

        # Save
        save_path = serializer.save(sample_analysis, filename="test_analysis.json")
        assert save_path.exists()

        # Load
        loaded = serializer.load(save_path)
        assert loaded.technology.primary_language == sample_analysis.technology.primary_language
        assert loaded.quality.overall_score == sample_analysis.quality.overall_score

    def test_find_latest(self, tmp_path, sample_analysis):
        """Test finding latest analysis."""
        serializer = AnalysisSerializer(cache_dir=tmp_path)

        # Save two analyses
        serializer.save(sample_analysis, filename="analysis_1.json")
        serializer.save(sample_analysis, filename="analysis_2.json")

        # Find latest
        latest = serializer.find_latest()
        assert latest is not None
        assert latest.name == "analysis_2.json"

    def test_export_markdown(self, tmp_path, sample_analysis):
        """Test markdown export."""
        serializer = AnalysisSerializer(cache_dir=tmp_path)

        output_path = tmp_path / "analysis.md"
        result = serializer.export_markdown(sample_analysis, output_path)

        assert result.exists()
        content = result.read_text()
        assert "Codebase Analysis Report" in content
        assert "Python" in content
        assert "FastAPI" in content


class TestHeuristicAnalyzer:
    """Test heuristic fallback analyzer."""

    @pytest.fixture
    def python_codebase(self, tmp_path):
        """Create a Python codebase for testing."""
        (tmp_path / "requirements.txt").write_text("fastapi==0.100.0\npytest==7.4.0")
        (tmp_path / "pytest.ini").write_text("[pytest]")

        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("from fastapi import FastAPI")
        (src / "repository.py").write_text("class UserRepository: pass")

        return tmp_path

    def test_detect_python_language(self, python_codebase):
        """Test Python language detection."""
        analyzer = HeuristicAnalyzer(python_codebase)
        language = analyzer._detect_language()

        assert language == "Python"

    def test_detect_fastapi_framework(self, python_codebase):
        """Test FastAPI framework detection."""
        analyzer = HeuristicAnalyzer(python_codebase)
        frameworks = analyzer._detect_frameworks("Python")

        assert "FastAPI" in frameworks

    def test_detect_pytest(self, python_codebase):
        """Test pytest detection."""
        analyzer = HeuristicAnalyzer(python_codebase)
        testing = analyzer._detect_testing_frameworks("Python")

        assert "pytest" in testing

    def test_full_heuristic_analysis(self, python_codebase):
        """Test complete heuristic analysis."""
        analyzer = HeuristicAnalyzer(python_codebase)
        result = analyzer.analyze()

        assert result["technology"]["primary_language"] == "Python"
        assert "FastAPI" in result["technology"]["frameworks"]
        assert result["agent_used"] is False


class TestCodebaseAnalyzer:
    """Test main analyzer orchestrator."""

    @pytest.fixture
    def mock_agent_invoker(self):
        """Create mock agent invoker."""
        mock = Mock(spec=ArchitecturalReviewerInvoker)
        mock.is_available.return_value = True
        mock.invoke_agent.return_value = """
```json
{
  "technology": {
    "primary_language": "Python",
    "frameworks": ["FastAPI"],
    "testing_frameworks": ["pytest"],
    "build_tools": ["pip"],
    "databases": [],
    "infrastructure": [],
    "confidence": {"level": "high", "percentage": 90.0}
  },
  "architecture": {
    "patterns": ["Repository"],
    "architectural_style": "Clean Architecture",
    "layers": [],
    "key_abstractions": ["User"],
    "dependency_flow": "Inward",
    "confidence": {"level": "medium", "percentage": 85.0}
  },
  "quality": {
    "overall_score": 80.0,
    "solid_compliance": 75.0,
    "dry_compliance": 80.0,
    "yagni_compliance": 85.0,
    "code_smells": [],
    "strengths": ["Clear structure"],
    "improvements": ["Add more tests"],
    "confidence": {"level": "medium", "percentage": 75.0}
  },
  "example_files": []
}
```
"""
        return mock

    @pytest.fixture
    def sample_codebase(self, tmp_path):
        """Create a sample codebase."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("print('Hello')")

        return tmp_path

    def test_analyze_with_agent(self, sample_codebase, mock_agent_invoker):
        """Test analysis using agent."""
        analyzer = CodebaseAnalyzer(
            agent_invoker=mock_agent_invoker,
            use_agent=True
        )

        analysis = analyzer.analyze_codebase(
            codebase_path=sample_codebase,
            template_context={"name": "Test", "language": "Python"}
        )

        assert analysis.technology.primary_language == "Python"
        assert analysis.agent_used is True
        mock_agent_invoker.invoke_agent.assert_called_once()

    def test_analyze_with_fallback(self, sample_codebase):
        """Test analysis with fallback to heuristics."""
        # Create analyzer with unavailable agent
        mock_invoker = Mock(spec=ArchitecturalReviewerInvoker)
        mock_invoker.is_available.return_value = False

        analyzer = CodebaseAnalyzer(
            agent_invoker=mock_invoker,
            use_agent=True
        )

        analysis = analyzer.analyze_codebase(
            codebase_path=sample_codebase
        )

        assert analysis.agent_used is False
        assert analysis.fallback_reason is not None

    def test_quick_analyze(self, sample_codebase):
        """Test quick analysis mode."""
        analyzer = CodebaseAnalyzer()

        analysis = analyzer.quick_analyze(
            codebase_path=sample_codebase
        )

        assert analysis is not None
        assert "Quick analysis" in analysis.fallback_reason

    def test_analyze_invalid_path(self):
        """Test analysis with invalid path."""
        analyzer = CodebaseAnalyzer()

        with pytest.raises(ValueError):
            analyzer.analyze_codebase(codebase_path="/nonexistent/path")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
