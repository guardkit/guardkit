"""
Tests for design pattern detection in codebase analyzer.

This module tests the heuristic pattern detection functionality that scans
codebases for files matching known pattern conventions.
"""

import pytest
from pathlib import Path
from installer.core.lib.codebase_analyzer.agent_invoker import HeuristicAnalyzer


class TestPatternDetection:
    """Tests for design pattern detection."""

    @pytest.fixture
    def analyzer(self, tmp_path):
        """Create analyzer with temp directory."""
        return HeuristicAnalyzer(codebase_path=tmp_path)

    def test_detect_repository_pattern(self, analyzer, tmp_path):
        """Test Repository pattern detection."""
        (tmp_path / "UserRepository.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "Repository" in patterns

    def test_detect_factory_pattern(self, analyzer, tmp_path):
        """Test Factory pattern detection."""
        (tmp_path / "OrderFactory.py").touch()
        patterns = analyzer._detect_patterns()
        assert "Factory" in patterns

    def test_detect_service_pattern(self, analyzer, tmp_path):
        """Test Service Layer pattern detection."""
        (tmp_path / "PaymentService.ts").touch()
        patterns = analyzer._detect_patterns()
        assert "Service Layer" in patterns

    def test_detect_engine_pattern(self, analyzer, tmp_path):
        """Test Engine pattern detection."""
        (tmp_path / "LoadingEngine.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "Engine" in patterns

    def test_detect_mvvm_pattern(self, analyzer, tmp_path):
        """Test MVVM pattern detection."""
        (tmp_path / "OrderViewModel.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "MVVM" in patterns

    def test_detect_erroror_pattern(self, analyzer, tmp_path):
        """Test Railway-Oriented Programming pattern detection."""
        (tmp_path / "ErrorOr.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "Railway-Oriented Programming" in patterns

    def test_detect_entity_pattern(self, analyzer, tmp_path):
        """Test Entity pattern detection."""
        (tmp_path / "UserEntity.py").touch()
        patterns = analyzer._detect_patterns()
        assert "Entity" in patterns

    def test_detect_model_pattern(self, analyzer, tmp_path):
        """Test Model pattern detection."""
        models_dir = tmp_path / "src" / "models"
        models_dir.mkdir(parents=True)
        (models_dir / "user.py").touch()
        patterns = analyzer._detect_patterns()
        assert "Model" in patterns

    def test_detect_controller_pattern(self, analyzer, tmp_path):
        """Test Controller pattern detection."""
        (tmp_path / "UsersController.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "Controller" in patterns

    def test_detect_handler_pattern(self, analyzer, tmp_path):
        """Test Handler pattern detection."""
        (tmp_path / "CreateOrderHandler.py").touch()
        patterns = analyzer._detect_patterns()
        assert "Handler" in patterns

    def test_detect_validator_pattern(self, analyzer, tmp_path):
        """Test Validator pattern detection."""
        (tmp_path / "EmailValidator.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "Validator" in patterns

    def test_detect_mapper_pattern(self, analyzer, tmp_path):
        """Test Mapper pattern detection."""
        (tmp_path / "UserMapper.cs").touch()
        patterns = analyzer._detect_patterns()
        assert "Mapper" in patterns

    def test_detect_builder_pattern(self, analyzer, tmp_path):
        """Test Builder pattern detection."""
        (tmp_path / "QueryBuilder.py").touch()
        patterns = analyzer._detect_patterns()
        assert "Builder" in patterns

    def test_detect_view_pattern(self, analyzer, tmp_path):
        """Test View pattern detection."""
        views_dir = tmp_path / "src" / "views"
        views_dir.mkdir(parents=True)
        (views_dir / "index.py").touch()
        patterns = analyzer._detect_patterns()
        assert "View" in patterns

    def test_detect_multiple_patterns(self, analyzer, tmp_path):
        """Test detection of multiple patterns in one codebase."""
        (tmp_path / "UserRepository.cs").touch()
        (tmp_path / "OrderService.cs").touch()
        (tmp_path / "ProductViewModel.cs").touch()
        (tmp_path / "ConfigurationMapper.cs").touch()

        patterns = analyzer._detect_patterns()

        assert "Repository" in patterns
        assert "Service Layer" in patterns
        assert "MVVM" in patterns
        assert "Mapper" in patterns
        assert len(patterns) >= 4

    def test_no_patterns_in_empty_directory(self, analyzer):
        """Test that empty directory returns no patterns."""
        patterns = analyzer._detect_patterns()
        assert patterns == []

    def test_case_insensitive_detection(self, analyzer, tmp_path):
        """Test that detection is case-insensitive."""
        (tmp_path / "userrepository.cs").touch()  # lowercase
        patterns = analyzer._detect_patterns()
        assert "Repository" in patterns

    def test_dotnet_maui_project_patterns(self, analyzer, tmp_path):
        """Integration test: Detect patterns in .NET MAUI style project."""
        # Create typical MAUI project structure
        (tmp_path / "ViewModels").mkdir()
        (tmp_path / "ViewModels" / "MainViewModel.cs").touch()
        (tmp_path / "ViewModels" / "SettingsViewModel.cs").touch()

        (tmp_path / "Services").mkdir()
        (tmp_path / "Services" / "ApiService.cs").touch()
        (tmp_path / "Services" / "NavigationService.cs").touch()

        (tmp_path / "Repositories").mkdir()
        (tmp_path / "Repositories" / "UserRepository.cs").touch()

        (tmp_path / "Engines").mkdir()
        (tmp_path / "Engines" / "LoadingEngine.cs").touch()

        (tmp_path / "Mappers").mkdir()
        (tmp_path / "Mappers" / "UserMapper.cs").touch()

        patterns = analyzer._detect_patterns()

        expected = ["MVVM", "Service Layer", "Repository", "Engine", "Mapper"]
        for pattern in expected:
            assert pattern in patterns, f"Expected {pattern} to be detected"

    def test_python_pattern_files(self, analyzer, tmp_path):
        """Test detection across Python files."""
        (tmp_path / "database_repository.py").touch()
        (tmp_path / "user_factory.py").touch()
        (tmp_path / "auth_service.py").touch()
        (tmp_path / "validation_engine.py").touch()

        patterns = analyzer._detect_patterns()

        assert "Repository" in patterns
        assert "Factory" in patterns
        assert "Service Layer" in patterns
        assert "Engine" in patterns

    def test_typescript_pattern_files(self, analyzer, tmp_path):
        """Test detection across TypeScript files."""
        (tmp_path / "UserRepository.ts").touch()
        (tmp_path / "OrderFactory.ts").touch()
        (tmp_path / "PaymentService.ts").touch()
        (tmp_path / "ValidationHandler.ts").touch()

        patterns = analyzer._detect_patterns()

        assert "Repository" in patterns
        assert "Factory" in patterns
        assert "Service Layer" in patterns
        assert "Handler" in patterns

    def test_java_pattern_files(self, analyzer, tmp_path):
        """Test detection across Java files."""
        (tmp_path / "UserRepository.java").touch()
        (tmp_path / "OrderFactory.java").touch()
        (tmp_path / "PaymentService.java").touch()
        (tmp_path / "ProductController.java").touch()

        patterns = analyzer._detect_patterns()

        assert "Repository" in patterns
        assert "Factory" in patterns
        assert "Service Layer" in patterns
        assert "Controller" in patterns

    def test_mixed_language_project(self, analyzer, tmp_path):
        """Test detection in project with multiple languages."""
        (tmp_path / "backend").mkdir()
        (tmp_path / "backend" / "UserRepository.py").touch()
        (tmp_path / "backend" / "OrderService.py").touch()

        (tmp_path / "frontend").mkdir()
        (tmp_path / "frontend" / "ProductViewModel.ts").touch()
        (tmp_path / "frontend" / "CartMapper.ts").touch()

        patterns = analyzer._detect_patterns()

        assert "Repository" in patterns
        assert "Service Layer" in patterns
        assert "MVVM" in patterns
        assert "Mapper" in patterns
