"""
Comprehensive Test Suite for TASK-0CE5: Codebase Analyzer Enhancement

Tests for the modifications to:
1. prompt_builder.py - Enhanced AI prompt
2. response_parser.py - Added validation + logging
3. agent_invoker.py - Enhanced fallback mechanism

Test Requirements:
- Unit tests for response validation (empty example_files raises error)
- Unit tests for fallback conversion (file_samples → example_files)
- Unit tests for helper methods (layer inference, purpose inference)
- Integration tests for end-to-end workflow
- Target: 80%+ line coverage, 75%+ branch coverage
"""

import pytest
import sys
import json
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
from typing import Dict, Any, Optional

# Add lib directories to path - must be done before imports
lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Ensure we're importing from the correct location
import codebase_analyzer.response_parser
import codebase_analyzer.agent_invoker
import codebase_analyzer.prompt_builder
import codebase_analyzer.models

ResponseParser = codebase_analyzer.response_parser.ResponseParser
FallbackResponseBuilder = codebase_analyzer.response_parser.FallbackResponseBuilder
HeuristicAnalyzer = codebase_analyzer.agent_invoker.HeuristicAnalyzer
ArchitecturalReviewerInvoker = codebase_analyzer.agent_invoker.ArchitecturalReviewerInvoker
PromptBuilder = codebase_analyzer.prompt_builder.PromptBuilder
CodebaseAnalysis = codebase_analyzer.models.CodebaseAnalysis
ExampleFile = codebase_analyzer.models.ExampleFile
ConfidenceLevel = codebase_analyzer.models.ConfidenceLevel
ParseError = codebase_analyzer.models.ParseError


class TestResponseParserValidation:
    """Test response validation with focus on example_files (TASK-0CE5)"""

    @pytest.fixture
    def parser(self):
        """Create ResponseParser instance"""
        return ResponseParser()

    @pytest.fixture
    def valid_response_json(self):
        """Valid response with example_files"""
        return {
            "technology": {
                "primary_language": "Python",
                "frameworks": ["FastAPI"],
                "testing_frameworks": ["pytest"],
                "build_tools": ["pip"],
                "databases": [],
                "infrastructure": [],
                "confidence": {
                    "level": "high",
                    "percentage": 90.0,
                    "reasoning": "Clear technology stack"
                }
            },
            "architecture": {
                "patterns": ["Repository"],
                "architectural_style": "Layered",
                "layers": [],
                "key_abstractions": [],
                "dependency_flow": "Inward",
                "confidence": {
                    "level": "medium",
                    "percentage": 75.0,
                    "reasoning": "Standard structure"
                }
            },
            "quality": {
                "overall_score": 80.0,
                "solid_compliance": 80.0,
                "dry_compliance": 85.0,
                "yagni_compliance": 80.0,
                "test_coverage": 75.0,
                "code_smells": [],
                "strengths": ["Clean code"],
                "improvements": ["Add more tests"],
                "confidence": {
                    "level": "medium",
                    "percentage": 75.0,
                    "reasoning": "Based on code inspection"
                }
            },
            "example_files": [
                {
                    "path": "src/main.py",
                    "purpose": "Main application entry point",
                    "layer": "Presentation",
                    "patterns_used": ["Factory"],
                    "key_concepts": ["Bootstrap"]
                },
                {
                    "path": "src/models/user.py",
                    "purpose": "User entity",
                    "layer": "Domain",
                    "patterns_used": ["Entity"],
                    "key_concepts": ["User", "Email"]
                }
            ]
        }

    @pytest.fixture
    def empty_example_files_response_json(self):
        """Response with empty example_files"""
        return {
            "technology": {
                "primary_language": "Python",
                "frameworks": [],
                "testing_frameworks": [],
                "build_tools": [],
                "databases": [],
                "infrastructure": [],
                "confidence": {
                    "level": "medium",
                    "percentage": 70.0,
                    "reasoning": "Limited information"
                }
            },
            "architecture": {
                "patterns": [],
                "architectural_style": "Unknown",
                "layers": [],
                "key_abstractions": [],
                "dependency_flow": "Unknown",
                "confidence": {
                    "level": "low",
                    "percentage": 50.0,
                    "reasoning": "Insufficient data"
                }
            },
            "quality": {
                "overall_score": 70.0,
                "solid_compliance": 70.0,
                "dry_compliance": 70.0,
                "yagni_compliance": 70.0,
                "test_coverage": None,
                "code_smells": [],
                "strengths": [],
                "improvements": [],
                "confidence": {
                    "level": "low",
                    "percentage": 60.0,
                    "reasoning": "Generic assessment"
                }
            },
            "example_files": []  # TASK-0CE5: Empty example_files
        }

    def test_parse_valid_response_with_example_files(self, parser, valid_response_json):
        """Test parsing valid response with example_files"""
        response_str = json.dumps(valid_response_json)

        analysis = parser.parse_analysis_response(
            response_str,
            "/test/path",
            validate_example_files=True
        )

        # Check analysis is the correct type
        assert analysis.__class__.__name__ == "CodebaseAnalysis"
        assert analysis.technology.primary_language == "Python"
        assert len(analysis.example_files) == 2
        assert analysis.example_files[0].path == "src/main.py"

    def test_parse_empty_example_files_raises_error(self, parser, empty_example_files_response_json):
        """Test that empty example_files raises ParseError when validation enabled (TASK-0CE5)"""
        response_str = json.dumps(empty_example_files_response_json)

        # Should raise ParseError due to empty example_files
        with pytest.raises(Exception):
            parser.parse_analysis_response(
                response_str,
                "/test/path",
                validate_example_files=True
            )

    def test_parse_empty_example_files_allowed_when_disabled(self, parser, empty_example_files_response_json):
        """Test that empty example_files allowed when validation disabled (TASK-0CE5)"""
        response_str = json.dumps(empty_example_files_response_json)

        # Should not raise when validation disabled
        analysis = parser.parse_analysis_response(
            response_str,
            "/test/path",
            validate_example_files=False
        )

        assert analysis.__class__.__name__ == "CodebaseAnalysis"
        assert len(analysis.example_files) == 0

    def test_parse_response_in_markdown_code_block(self, parser, valid_response_json):
        """Test parsing response wrapped in markdown code block"""
        json_str = json.dumps(valid_response_json)
        response_str = f"```json\n{json_str}\n```"

        analysis = parser.parse_analysis_response(
            response_str,
            "/test/path",
            validate_example_files=True
        )

        assert analysis.__class__.__name__ == "CodebaseAnalysis"
        assert analysis.technology.primary_language == "Python"

    def test_parse_invalid_json_raises_error(self, parser):
        """Test that invalid JSON raises ParseError"""
        response_str = "This is not JSON at all"

        # Should raise ParseError when no JSON found
        with pytest.raises(Exception):
            parser.parse_analysis_response(response_str, "/test/path")

    def test_parse_missing_required_fields_raises_error(self, parser):
        """Test that missing required fields raises ParseError"""
        incomplete_json = {
            "technology": {
                "primary_language": "Python"
                # Missing required fields, example_files will be empty
            }
        }
        response_str = json.dumps(incomplete_json)

        # Should raise ParseError due to missing/empty example_files
        with pytest.raises(Exception):
            parser.parse_analysis_response(response_str, "/test/path")


class TestResponseParserLogging:
    """Test logging functionality in ResponseParser (TASK-0CE5)"""

    @pytest.fixture
    def parser(self):
        return ResponseParser()

    def test_logs_when_example_files_missing(self, parser, caplog):
        """Test that missing example_files is logged as warning"""
        response_json = {
            "technology": {
                "primary_language": "Python",
                "frameworks": [],
                "testing_frameworks": [],
                "build_tools": [],
                "databases": [],
                "infrastructure": [],
                "confidence": {"level": "medium", "percentage": 70.0, "reasoning": "test"}
            },
            "architecture": {
                "patterns": [],
                "architectural_style": "Unknown",
                "layers": [],
                "key_abstractions": [],
                "dependency_flow": "Unknown",
                "confidence": {"level": "low", "percentage": 50.0, "reasoning": "test"}
            },
            "quality": {
                "overall_score": 70.0,
                "solid_compliance": 70.0,
                "dry_compliance": 70.0,
                "yagni_compliance": 70.0,
                "test_coverage": None,
                "code_smells": [],
                "strengths": [],
                "improvements": [],
                "confidence": {"level": "low", "percentage": 60.0, "reasoning": "test"}
            }
            # Note: example_files key missing entirely
        }
        response_str = json.dumps(response_json)

        with caplog.at_level(logging.WARNING):
            with pytest.raises(Exception):
                parser.parse_analysis_response(response_str, "/test/path")

        # Should log warning about missing example_files key
        assert any("example_files" in record.message.lower() for record in caplog.records)

    def test_logs_example_files_count_on_success(self, parser, caplog):
        """Test that successful parsing logs example_files count"""
        response_json = {
            "technology": {
                "primary_language": "Python",
                "frameworks": [],
                "testing_frameworks": [],
                "build_tools": [],
                "databases": [],
                "infrastructure": [],
                "confidence": {"level": "medium", "percentage": 70.0, "reasoning": "test"}
            },
            "architecture": {
                "patterns": [],
                "architectural_style": "Unknown",
                "layers": [],
                "key_abstractions": [],
                "dependency_flow": "Unknown",
                "confidence": {"level": "low", "percentage": 50.0, "reasoning": "test"}
            },
            "quality": {
                "overall_score": 70.0,
                "solid_compliance": 70.0,
                "dry_compliance": 70.0,
                "yagni_compliance": 70.0,
                "test_coverage": None,
                "code_smells": [],
                "strengths": [],
                "improvements": [],
                "confidence": {"level": "low", "percentage": 60.0, "reasoning": "test"}
            },
            "example_files": [
                {
                    "path": "src/main.py",
                    "purpose": "Main entry",
                    "layer": "Presentation",
                    "patterns_used": [],
                    "key_concepts": []
                }
            ]
        }
        response_str = json.dumps(response_json)

        with caplog.at_level(logging.INFO):
            parser.parse_analysis_response(response_str, "/test/path", validate_example_files=False)

        # Should log success with count
        assert any("1 example files" in record.message for record in caplog.records)


class TestFallbackConversion:
    """Test fallback conversion from file_samples to example_files (TASK-0CE5)"""

    @pytest.fixture
    def temp_codebase(self):
        """Create temporary codebase with files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create source files
            (tmppath / "src").mkdir()
            (tmppath / "src" / "main.py").write_text("def main(): pass")
            (tmppath / "src" / "models").mkdir()
            (tmppath / "src" / "models" / "user.py").write_text("class User: pass")

            # Create test files
            (tmppath / "tests").mkdir()
            (tmppath / "tests" / "test_main.py").write_text("def test_main(): pass")

            yield tmppath

    def test_fallback_with_file_samples(self, temp_codebase):
        """Test HeuristicAnalyzer converts file_samples to example_files"""
        file_samples = [
            {
                "path": "src/main.py",
                "content": "def main(): pass",
                "category": "crud_create"
            },
            {
                "path": "src/models/user.py",
                "content": "class User: pass",
                "category": "models"
            }
        ]

        analyzer = HeuristicAnalyzer(temp_codebase, file_samples=file_samples)
        result = analyzer.analyze()

        # Should have example_files from file_samples
        assert "example_files" in result
        assert len(result["example_files"]) >= 2

        # Check that file_samples were converted
        example_paths = [f["path"] for f in result["example_files"]]
        assert "src/main.py" in example_paths
        assert "src/models/user.py" in example_paths

    def test_fallback_infers_layer_from_path(self, temp_codebase):
        """Test layer inference from file path (TASK-0CE5)"""
        file_samples = [
            {"path": "src/domain/user.py", "content": "class User: pass", "category": "models"},
            {"path": "src/application/services/user_service.py", "content": "class UserService: pass", "category": "services"},
            {"path": "src/infrastructure/repositories/user_repository.py", "content": "class UserRepository: pass", "category": "repositories"},
            {"path": "src/web/api/routes/users.py", "content": "def get_users(): pass", "category": "controllers"}
        ]

        analyzer = HeuristicAnalyzer(temp_codebase, file_samples=file_samples)
        result = analyzer.analyze()

        example_files = result["example_files"]

        # Verify layer inference
        layers = {f["path"]: f["layer"] for f in example_files}

        assert layers.get("src/domain/user.py") == "Domain"
        assert layers.get("src/application/services/user_service.py") == "Application"
        assert layers.get("src/infrastructure/repositories/user_repository.py") == "Infrastructure"
        assert layers.get("src/web/api/routes/users.py") == "Presentation"

    def test_fallback_infers_purpose_from_category(self, temp_codebase):
        """Test purpose inference from category (TASK-0CE5)"""
        file_samples = [
            {"path": "src/main.py", "content": "", "category": "crud_create"},
            {"path": "src/validators.py", "content": "", "category": "validators"}
        ]

        analyzer = HeuristicAnalyzer(temp_codebase, file_samples=file_samples)
        result = analyzer.analyze()

        example_files = result["example_files"]
        purposes = {f["path"]: f["purpose"] for f in example_files}

        assert "Create operation" in purposes.get("src/main.py", "")
        assert "Validation" in purposes.get("src/validators.py", "")

    def test_fallback_limits_example_files_to_15(self, temp_codebase):
        """Test that fallback limits example_files to 15 (TASK-0CE5)"""
        file_samples = [
            {"path": f"src/file_{i}.py", "content": "", "category": "models"}
            for i in range(25)  # Create 25 samples
        ]

        analyzer = HeuristicAnalyzer(temp_codebase, file_samples=file_samples)
        result = analyzer.analyze()

        example_files = result["example_files"]
        assert len(example_files) <= 15


class TestLayerInference:
    """Test layer inference helper method (TASK-0CE5)"""

    @pytest.fixture
    def analyzer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield HeuristicAnalyzer(Path(tmpdir))

    def test_infer_domain_layer(self, analyzer):
        """Test Domain layer inference"""
        assert analyzer._infer_layer_from_path("src/domain/user.py") == "Domain"
        assert analyzer._infer_layer_from_path("src/entities/order.py") == "Domain"
        assert analyzer._infer_layer_from_path("src/models/product.py") == "Domain"

    def test_infer_application_layer(self, analyzer):
        """Test Application layer inference"""
        assert analyzer._infer_layer_from_path("src/application/services/user_service.py") == "Application"
        assert analyzer._infer_layer_from_path("src/usecases/create_user.py") == "Application"

    def test_infer_infrastructure_layer(self, analyzer):
        """Test Infrastructure layer inference"""
        assert analyzer._infer_layer_from_path("src/infrastructure/repositories/user_repo.py") == "Infrastructure"
        assert analyzer._infer_layer_from_path("src/data/user_repository.py") == "Infrastructure"

    def test_infer_presentation_layer(self, analyzer):
        """Test Presentation layer inference"""
        assert analyzer._infer_layer_from_path("src/web/api/routes/users.py") == "Presentation"
        assert analyzer._infer_layer_from_path("src/api/controllers/user_controller.py") == "Presentation"
        assert analyzer._infer_layer_from_path("src/endpoints/users.py") == "Presentation"

    def test_infer_testing_layer(self, analyzer):
        """Test Testing layer inference"""
        assert analyzer._infer_layer_from_path("tests/unit/test_user.py") == "Testing"
        assert analyzer._infer_layer_from_path("tests/specs/user_spec.py") == "Testing"

    def test_infer_shared_layer(self, analyzer):
        """Test Shared/Common layer inference"""
        assert analyzer._infer_layer_from_path("src/shared/exceptions.py") == "Shared"
        assert analyzer._infer_layer_from_path("src/common/utils.py") == "Shared"

    def test_infer_unknown_layer(self, analyzer):
        """Test unknown layer returns None"""
        assert analyzer._infer_layer_from_path("src/random_module.py") is None


class TestPurposeInference:
    """Test purpose inference helper method (TASK-0CE5)"""

    @pytest.fixture
    def analyzer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield HeuristicAnalyzer(Path(tmpdir))

    def test_infer_crud_create_purpose(self, analyzer):
        """Test CRUD create purpose inference"""
        purpose = analyzer._infer_purpose_from_category("crud_create", "src/create_user.py")
        assert "Create" in purpose

    def test_infer_crud_read_purpose(self, analyzer):
        """Test CRUD read purpose inference"""
        purpose = analyzer._infer_purpose_from_category("crud_read", "src/get_user.py")
        assert "Read" in purpose

    def test_infer_validators_purpose(self, analyzer):
        """Test validators purpose inference"""
        purpose = analyzer._infer_purpose_from_category("validators", "src/email_validator.py")
        assert "Validation" in purpose

    def test_infer_repositories_purpose(self, analyzer):
        """Test repositories purpose inference"""
        purpose = analyzer._infer_purpose_from_category("repositories", "src/user_repository.py")
        assert "Data access" in purpose or "repository" in purpose.lower()

    def test_infer_services_purpose(self, analyzer):
        """Test services purpose inference"""
        purpose = analyzer._infer_purpose_from_category("services", "src/user_service.py")
        assert "Business logic" in purpose or "service" in purpose.lower()

    def test_infer_controllers_purpose(self, analyzer):
        """Test controllers purpose inference"""
        purpose = analyzer._infer_purpose_from_category("controllers", "src/user_controller.py")
        assert "controller" in purpose.lower() or "API" in purpose

    def test_purpose_includes_filename(self, analyzer):
        """Test that purpose includes filename"""
        purpose = analyzer._infer_purpose_from_category("models", "src/user.py")
        assert "user" in purpose.lower()


class TestPromptBuilder:
    """Test PromptBuilder enhancements (TASK-0CE5)"""

    def test_build_analysis_prompt_includes_template_context(self):
        """Test that prompt includes template context when provided"""
        builder = PromptBuilder(template_context={
            "name": "fastapi-python",
            "language": "Python",
            "framework": "FastAPI",
            "description": "FastAPI backend template"
        })

        prompt = builder.build_analysis_prompt(
            Path("/test/path"),
            [{"path": "src/main.py", "content": "code"}],
            "directory structure"
        )

        assert "fastapi-python" in prompt
        assert "FastAPI" in prompt
        assert "Template Context" in prompt

    def test_build_analysis_prompt_includes_metadata_inference_guidance(self):
        """Test that prompt includes metadata inference guidance when no context (TASK-51B2)"""
        builder = PromptBuilder(template_context=None)

        prompt = builder.build_analysis_prompt(
            Path("/test/path"),
            [{"path": "src/main.py", "content": "code"}],
            "directory structure"
        )

        assert "AI-Native Metadata Inference" in prompt
        assert "Template Name" in prompt
        assert "Primary Language" in prompt
        assert "Framework" in prompt

    def test_build_analysis_prompt_includes_example_files_requirement(self):
        """Test that prompt includes critical example_files requirement (TASK-0CE5)"""
        builder = PromptBuilder()

        prompt = builder.build_analysis_prompt(
            Path("/test/path"),
            [{"path": "src/main.py", "content": "code"}],
            "directory structure"
        )

        assert "example_files" in prompt.lower()
        assert "CRITICAL REQUIREMENT" in prompt or "NON-NEGOTIABLE" in prompt
        assert "10-20" in prompt


class TestIntegration:
    """Integration tests for complete workflow (TASK-0CE5)"""

    @pytest.fixture
    def temp_python_project(self):
        """Create a temporary Python project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create project structure
            (tmppath / "src").mkdir()
            (tmppath / "src" / "domain").mkdir()
            (tmppath / "src" / "application").mkdir()
            (tmppath / "src" / "infrastructure").mkdir()
            (tmppath / "src" / "web").mkdir()

            # Create sample files
            (tmppath / "src" / "domain" / "user.py").write_text(
                "class User:\n    def __init__(self, name: str):\n        self.name = name"
            )
            (tmppath / "src" / "application" / "user_service.py").write_text(
                "class UserService:\n    def create_user(self, name: str): pass"
            )
            (tmppath / "src" / "infrastructure" / "user_repository.py").write_text(
                "class UserRepository:\n    def save(self, user): pass"
            )
            (tmppath / "src" / "web" / "routes.py").write_text(
                "@app.post('/users')\ndef create_user(): pass"
            )

            # Create project files
            (tmppath / "requirements.txt").write_text(
                "fastapi==0.95.0\npydantic==2.0.0\npytest==7.2.0"
            )
            (tmppath / "setup.py").write_text(
                "from setuptools import setup\nsetup(name='test-project')"
            )

            yield tmppath

    def test_end_to_end_heuristic_analysis(self, temp_python_project):
        """Test complete heuristic analysis workflow"""
        analyzer = HeuristicAnalyzer(temp_python_project)
        result = analyzer.analyze()

        # Verify structure
        assert "technology" in result
        assert "architecture" in result
        assert "quality" in result
        assert "example_files" in result

        # Verify technology detection
        assert result["technology"]["primary_language"] == "Python"
        assert "FastAPI" in result["technology"]["frameworks"]

        # Verify example files found
        assert len(result["example_files"]) > 0

    def test_end_to_end_with_file_samples(self, temp_python_project):
        """Test heuristic analysis with file_samples"""
        file_samples = [
            {"path": "src/domain/user.py", "content": "class User: pass", "category": "models"},
            {"path": "src/application/user_service.py", "content": "class UserService: pass", "category": "services"}
        ]

        analyzer = HeuristicAnalyzer(temp_python_project, file_samples=file_samples)
        result = analyzer.analyze()

        # Verify file_samples were converted
        example_files = result["example_files"]
        paths = [f["path"] for f in example_files]

        assert "src/domain/user.py" in paths
        assert "src/application/user_service.py" in paths

        # Verify layers were inferred
        for f in example_files:
            if f["path"] == "src/domain/user.py":
                assert f["layer"] == "Domain"
            elif f["path"] == "src/application/user_service.py":
                assert f["layer"] == "Application"

    def test_fallback_response_builder_integration(self, temp_python_project):
        """Test FallbackResponseBuilder with HeuristicAnalyzer"""
        # Get heuristic analysis
        heuristic_analyzer = HeuristicAnalyzer(temp_python_project)
        heuristic_data = heuristic_analyzer.analyze()

        # Build CodebaseAnalysis from heuristics
        builder = FallbackResponseBuilder()
        analysis = builder.build_from_heuristics(
            heuristic_data,
            str(temp_python_project),
            template_context={"name": "test-template"}
        )

        # Verify result is CodebaseAnalysis
        assert analysis.__class__.__name__ == "CodebaseAnalysis"
        assert not analysis.agent_used
        assert analysis.fallback_reason is not None
        assert len(analysis.example_files) > 0


class TestEdgeCases:
    """Test edge cases and error conditions (TASK-0CE5)"""

    def test_parse_response_with_extra_whitespace(self):
        """Test parsing response with extra whitespace"""
        parser = ResponseParser()

        response_json = {
            "technology": {
                "primary_language": "Python",
                "frameworks": [],
                "testing_frameworks": [],
                "build_tools": [],
                "databases": [],
                "infrastructure": [],
                "confidence": {"level": "medium", "percentage": 70.0, "reasoning": "test"}
            },
            "architecture": {
                "patterns": [],
                "architectural_style": "Unknown",
                "layers": [],
                "key_abstractions": [],
                "dependency_flow": "Unknown",
                "confidence": {"level": "low", "percentage": 50.0, "reasoning": "test"}
            },
            "quality": {
                "overall_score": 70.0,
                "solid_compliance": 70.0,
                "dry_compliance": 70.0,
                "yagni_compliance": 70.0,
                "test_coverage": None,
                "code_smells": [],
                "strengths": [],
                "improvements": [],
                "confidence": {"level": "low", "percentage": 60.0, "reasoning": "test"}
            },
            "example_files": [
                {
                    "path": "src/main.py",
                    "purpose": "Entry point",
                    "layer": "Presentation",
                    "patterns_used": [],
                    "key_concepts": []
                }
            ]
        }

        json_str = json.dumps(response_json)
        response_str = f"   \n\n```json\n{json_str}\n```\n\n   "

        analysis = parser.parse_analysis_response(response_str, "/test/path", validate_example_files=False)
        assert analysis.__class__.__name__ == "CodebaseAnalysis"

    def test_heuristic_analyzer_with_nonexistent_path(self):
        """Test HeuristicAnalyzer with nonexistent path raises ValueError"""
        analyzer = HeuristicAnalyzer(Path("/nonexistent/path"))
        
        # Should raise ValueError when path doesn't exist
        with pytest.raises(ValueError, match="Root directory does not exist"):
            analyzer.analyze()

    def test_layer_inference_case_insensitive(self):
        """Test that layer inference is case-insensitive"""
        with tempfile.TemporaryDirectory() as tmpdir:
            analyzer = HeuristicAnalyzer(Path(tmpdir))

            assert analyzer._infer_layer_from_path("src/DOMAIN/user.py") == "Domain"
            assert analyzer._infer_layer_from_path("src/Application/services.py") == "Application"
            assert analyzer._infer_layer_from_path("src/INFRASTRUCTURE/repo.py") == "Infrastructure"

    def test_example_file_with_missing_optional_fields(self):
        """Test parsing example file with missing optional fields"""
        parser = ResponseParser()

        response_json = {
            "technology": {
                "primary_language": "Python",
                "frameworks": [],
                "testing_frameworks": [],
                "build_tools": [],
                "databases": [],
                "infrastructure": [],
                "confidence": {"level": "medium", "percentage": 70.0, "reasoning": "test"}
            },
            "architecture": {
                "patterns": [],
                "architectural_style": "Unknown",
                "layers": [],
                "key_abstractions": [],
                "dependency_flow": "Unknown",
                "confidence": {"level": "low", "percentage": 50.0, "reasoning": "test"}
            },
            "quality": {
                "overall_score": 70.0,
                "solid_compliance": 70.0,
                "dry_compliance": 70.0,
                "yagni_compliance": 70.0,
                "test_coverage": None,
                "code_smells": [],
                "strengths": [],
                "improvements": [],
                "confidence": {"level": "low", "percentage": 60.0, "reasoning": "test"}
            },
            "example_files": [
                {
                    "path": "src/main.py"
                    # Missing: purpose, layer, patterns_used, key_concepts
                }
            ]
        }

        response_str = json.dumps(response_json)

        analysis = parser.parse_analysis_response(response_str, "/test/path", validate_example_files=False)

        assert len(analysis.example_files) == 1
        assert analysis.example_files[0].path == "src/main.py"
        assert analysis.example_files[0].purpose == "No purpose specified"  # Default value


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
