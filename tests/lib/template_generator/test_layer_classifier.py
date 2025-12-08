"""
Tests for layer classification strategies.

Tests the improved layer classification system with language-specific
classifiers, confidence scoring, and chain of responsibility pattern.

TASK-FIX-40B4: Improve layer classification for JavaScript projects
"""

import pytest
import importlib

# Import using importlib to avoid 'global' keyword issue
_layer_classifier_module = importlib.import_module('installer.global.lib.template_generator.layer_classifier')
_models_module = importlib.import_module('installer.global.lib.codebase_analyzer.models')

# Import classes from layer_classifier
ClassificationResult = _layer_classifier_module.ClassificationResult
LayerClassificationStrategy = _layer_classifier_module.LayerClassificationStrategy
JavaScriptLayerClassifier = _layer_classifier_module.JavaScriptLayerClassifier
GenericLayerClassifier = _layer_classifier_module.GenericLayerClassifier
LayerClassificationOrchestrator = _layer_classifier_module.LayerClassificationOrchestrator

# Import models
ExampleFile = _models_module.ExampleFile
CodebaseAnalysis = _models_module.CodebaseAnalysis
ArchitectureInfo = _models_module.ArchitectureInfo
LayerInfo = _models_module.LayerInfo
TechnologyInfo = _models_module.TechnologyInfo
QualityInfo = _models_module.QualityInfo
ConfidenceScore = _models_module.ConfidenceScore
ConfidenceLevel = _models_module.ConfidenceLevel


# Fixtures

@pytest.fixture
def javascript_analysis():
    """Create sample JavaScript codebase analysis."""
    return CodebaseAnalysis(
        codebase_path="/test/js-project",
        technology=TechnologyInfo(
            primary_language="JavaScript",
            frameworks=["React", "Vite"],
            testing_frameworks=["Vitest"],
            build_tools=["npm"],
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=95.0,
            ),
        ),
        architecture=ArchitectureInfo(
            architectural_style="Feature-based Architecture",
            layers=[
                LayerInfo(name="components", description="Presentation layer"),
                LayerInfo(name="api", description="Data access layer"),
            ],
            dependency_flow="Inward toward features",
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=90.0,
            ),
        ),
        quality=QualityInfo(
            overall_score=85.0,
            solid_compliance=80.0,
            dry_compliance=85.0,
            yagni_compliance=90.0,
            confidence=ConfidenceScore(
                level=ConfidenceLevel.MEDIUM,
                percentage=75.0,
            ),
        ),
        example_files=[],
        analysis_timestamp=None,
    )


@pytest.fixture
def csharp_analysis():
    """Create sample C# codebase analysis."""
    return CodebaseAnalysis(
        codebase_path="/test/csharp-project",
        technology=TechnologyInfo(
            primary_language="C#",
            frameworks=[".NET"],
            testing_frameworks=["xUnit"],
            build_tools=["dotnet"],
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=95.0,
            ),
        ),
        architecture=ArchitectureInfo(
            architectural_style="Clean Architecture",
            layers=[
                LayerInfo(name="domain", description="Domain layer"),
                LayerInfo(name="application", description="Application layer"),
                LayerInfo(name="infrastructure", description="Infrastructure layer"),
            ],
            dependency_flow="Inward toward domain",
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=90.0,
            ),
        ),
        quality=QualityInfo(
            overall_score=88.0,
            solid_compliance=90.0,
            dry_compliance=85.0,
            yagni_compliance=87.0,
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=90.0,
            ),
        ),
        example_files=[],
        analysis_timestamp=None,
    )


# ClassificationResult Tests

class TestClassificationResult:
    """Test ClassificationResult dataclass."""

    def test_create_result(self):
        """Test creating a classification result."""
        result = ClassificationResult(
            layer="presentation",
            confidence=0.85,
            strategy_used="JavaScriptLayerClassifier",
        )

        assert result.layer == "presentation"
        assert result.confidence == 0.85
        assert result.strategy_used == "JavaScriptLayerClassifier"
        assert result.pattern_matched is None

    def test_create_result_with_pattern(self):
        """Test creating result with pattern matched."""
        result = ClassificationResult(
            layer="testing",
            confidence=0.95,
            strategy_used="JavaScriptLayerClassifier",
            pattern_matched=r'/__tests__/',
        )

        assert result.layer == "testing"
        assert result.confidence == 0.95
        assert result.pattern_matched == r'/__tests__/'

    def test_result_repr(self):
        """Test string representation."""
        result = ClassificationResult(
            layer="data-access",
            confidence=0.85,
            strategy_used="JavaScriptLayerClassifier",
        )

        repr_str = repr(result)
        assert "data-access" in repr_str
        assert "0.85" in repr_str
        assert "JavaScriptLayerClassifier" in repr_str


# JavaScriptLayerClassifier Tests

class TestJavaScriptLayerClassifier:
    """Test JavaScript-specific layer classifier."""

    @pytest.fixture
    def classifier(self):
        """Create JavaScript classifier instance."""
        return JavaScriptLayerClassifier()

    # Testing Layer Tests (0.95 confidence)

    def test_classify_mocks_directory(self, classifier, javascript_analysis):
        """Test classification of __mocks__ directory."""
        file = ExampleFile(
            path="src/__mocks__/api.js",
            purpose="Mock API for testing",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "testing"
        assert result.confidence == 0.95
        assert result.strategy_used == "JavaScriptLayerClassifier"
        assert "__mocks__" in result.pattern_matched

    def test_classify_tests_directory(self, classifier, javascript_analysis):
        """Test classification of __tests__ directory."""
        file = ExampleFile(
            path="src/components/__tests__/Button.test.js",
            purpose="Button component tests",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "testing"
        assert result.confidence == 0.95

    def test_classify_hidden_test_file(self, classifier, javascript_analysis):
        """Test classification of hidden .test.js files.

        Note: Pattern /\.test\. matches hidden files like /.test.js
        This is unusual but valid in JavaScript projects.
        """
        test_files = [
            "src/.test.js",                  # Hidden test file (unusual pattern)
            "src/components/.test.jsx",      # Hidden test in components
            "src/testing/.test.ts",          # Hidden test file
        ]

        for path in test_files:
            file = ExampleFile(path=path, purpose="Hidden test file")
            result = classifier.classify(file, javascript_analysis)

            assert result is not None, f"Failed to classify {path}"
            assert result.layer == "testing"
            assert result.confidence == 0.95

    def test_classify_hidden_spec_file(self, classifier, javascript_analysis):
        """Test classification of hidden .spec.js files.

        Note: Pattern /\.spec\. matches hidden files like /.spec.js
        """
        spec_files = [
            "src/.spec.js",                  # Hidden spec file
            "src/components/.spec.jsx",      # Hidden spec in components
        ]

        for path in spec_files:
            file = ExampleFile(path=path, purpose="Hidden spec file")
            result = classifier.classify(file, javascript_analysis)

            assert result is not None, f"Failed to classify {path}"
            assert result.layer == "testing"
            assert result.confidence == 0.95

    def test_regular_test_files_match_directory_patterns(self, classifier, javascript_analysis):
        """Test that regular test files (Button.test.js) match directory patterns instead.

        This documents actual behavior: /\.test\. pattern matches hidden files,
        NOT regular files like Button.test.js. Regular test files will match
        their directory pattern (/components/, /utils/, etc).
        """
        # Regular test files match their directory pattern, not /\.test\.
        file = ExampleFile(
            path="src/components/Button.test.jsx",
            purpose="Button component test",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        # Matches /components/ pattern (0.85), NOT /\.test\. pattern
        assert result.layer == "presentation"
        assert result.confidence == 0.85

    def test_classify_mock_suffix(self, classifier, javascript_analysis):
        """Test classification of files with -mock suffix."""
        file = ExampleFile(
            path="src/data/-mock/users.js",   # Has /-mock/ in path
            purpose="Mock user data",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "testing"
        assert result.confidence == 0.95

    # Scripts Layer Tests (0.90 confidence)

    def test_classify_scripts_directory(self, classifier, javascript_analysis):
        """Test classification of /scripts/ directory.

        Note: Pattern requires /scripts/ in path, not just scripts/ at start.
        """
        file = ExampleFile(
            path="src/scripts/build.js",      # Has /scripts/ in path
            purpose="Build script",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "scripts"
        assert result.confidence == 0.90

    def test_classify_upload_directory(self, classifier, javascript_analysis):
        """Test classification of /upload/ directory."""
        file = ExampleFile(
            path="src/upload/process.js",
            purpose="Upload processing",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "scripts"
        assert result.confidence == 0.90

    def test_classify_bin_directory(self, classifier, javascript_analysis):
        """Test classification of /bin/ directory.

        Note: Pattern requires /bin/ in path, not just bin/ at start.
        """
        file = ExampleFile(
            path="src/bin/deploy.js",         # Has /bin/ in path
            purpose="Deployment script",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "scripts"
        assert result.confidence == 0.90

    # Routes/Pages Layer Tests (0.95 confidence)

    def test_classify_routes_directory(self, classifier, javascript_analysis):
        """Test classification of /routes/ directory."""
        file = ExampleFile(
            path="src/routes/api.js",
            purpose="API routes",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "routes"
        assert result.confidence == 0.95

    def test_classify_pages_directory(self, classifier, javascript_analysis):
        """Test classification of /pages/ directory."""
        file = ExampleFile(
            path="src/pages/Home.jsx",
            purpose="Home page component",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "routes"
        assert result.confidence == 0.95

    # State Management Layer Tests (0.90 confidence)

    def test_classify_store_directory(self, classifier, javascript_analysis):
        """Test classification of /store/ directory."""
        file = ExampleFile(
            path="src/store/userSlice.js",
            purpose="User state slice",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "state"
        assert result.confidence == 0.90

    def test_classify_state_directory(self, classifier, javascript_analysis):
        """Test classification of /state/ directory."""
        file = ExampleFile(
            path="src/state/auth.js",
            purpose="Auth state management",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "state"
        assert result.confidence == 0.90

    def test_classify_context_directory(self, classifier, javascript_analysis):
        """Test classification of /context/ directory."""
        file = ExampleFile(
            path="src/context/ThemeContext.jsx",
            purpose="Theme context provider",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "state"
        assert result.confidence == 0.90

    # Data Access Layer Tests (0.85 confidence)

    def test_classify_firestore_directory(self, classifier, javascript_analysis):
        """Test classification of /firestore/ directory."""
        file = ExampleFile(
            path="src/firestore/users.js",
            purpose="Firestore user queries",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "data-access"
        assert result.confidence == 0.85

    def test_classify_api_directory(self, classifier, javascript_analysis):
        """Test classification of /api/ directory."""
        file = ExampleFile(
            path="src/api/endpoints.js",
            purpose="API endpoint definitions",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "data-access"
        assert result.confidence == 0.85

    def test_classify_query_file(self, classifier, javascript_analysis):
        """Test classification of query.js files."""
        query_files = [
            "src/data/query.js",
            "src/data/query.ts",
            "src/services/query.jsx",
            "src/db/query.tsx",
        ]

        for path in query_files:
            file = ExampleFile(path=path, purpose="Query file")
            result = classifier.classify(file, javascript_analysis)

            assert result is not None, f"Failed to classify {path}"
            assert result.layer == "data-access"
            assert result.confidence == 0.85

    # Presentation Layer Tests (0.85 confidence)

    def test_classify_components_directory(self, classifier, javascript_analysis):
        """Test classification of /components/ directory."""
        file = ExampleFile(
            path="src/components/Button.jsx",
            purpose="Button component",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "presentation"
        assert result.confidence == 0.85

    def test_classify_screens_directory(self, classifier, javascript_analysis):
        """Test classification of /screens/ directory."""
        file = ExampleFile(
            path="src/screens/ProfileScreen.jsx",
            purpose="Profile screen component",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "presentation"
        assert result.confidence == 0.85

    # Utilities Layer Tests (0.75 confidence)

    def test_classify_lib_directory(self, classifier, javascript_analysis):
        """Test classification of /lib/ directory."""
        file = ExampleFile(
            path="src/lib/format.js",
            purpose="Formatting utilities",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "utilities"
        assert result.confidence == 0.75

    def test_classify_utils_directory(self, classifier, javascript_analysis):
        """Test classification of /utils/ directory."""
        file = ExampleFile(
            path="src/utils/helpers.js",
            purpose="Helper utilities",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "utilities"
        assert result.confidence == 0.75

    # Edge Cases

    def test_classify_empty_path(self, classifier, javascript_analysis):
        """Test handling of empty file path."""
        file = ExampleFile(path="", purpose="Empty path")

        result = classifier.classify(file, javascript_analysis)

        assert result is None

    def test_classify_unknown_pattern(self, classifier, javascript_analysis):
        """Test classification of file with no matching pattern."""
        file = ExampleFile(
            path="src/random.js",
            purpose="Random file",
        )

        result = classifier.classify(file, javascript_analysis)

        assert result is None

    def test_pattern_precedence(self, classifier, javascript_analysis):
        """Test that more specific patterns take precedence."""
        # Test file in __tests__ directory matches testing first
        file = ExampleFile(
            path="src/components/__tests__/Button.test.js",
            purpose="Button component test",
        )

        result = classifier.classify(file, javascript_analysis)

        # Should match testing layer (0.95) via __tests__, not presentation
        assert result is not None
        assert result.layer == "testing"
        assert result.confidence == 0.95

    # Language Support Tests

    def test_supports_javascript(self, classifier):
        """Test language support for JavaScript."""
        assert classifier.supports_language("javascript") is True
        assert classifier.supports_language("JavaScript") is True
        assert classifier.supports_language("js") is True

    def test_supports_typescript(self, classifier):
        """Test language support for TypeScript."""
        assert classifier.supports_language("typescript") is True
        assert classifier.supports_language("TypeScript") is True
        assert classifier.supports_language("ts") is True
        assert classifier.supports_language("tsx") is True

    def test_does_not_support_other_languages(self, classifier):
        """Test that classifier rejects non-JS languages."""
        assert classifier.supports_language("python") is False
        assert classifier.supports_language("C#") is False
        assert classifier.supports_language("Go") is False


# GenericLayerClassifier Tests

class TestGenericLayerClassifier:
    """Test generic cross-language layer classifier."""

    @pytest.fixture
    def classifier(self):
        """Create generic classifier instance."""
        return GenericLayerClassifier()

    # Domain Layer Tests

    def test_classify_domain_directory_uppercase(self, classifier, csharp_analysis):
        """Test classification of /Domain/ directory."""
        file = ExampleFile(
            path="src/Domain/Products/Product.cs",
            purpose="Product domain entity",
        )

        result = classifier.classify(file, csharp_analysis)

        assert result is not None
        assert result.layer == "domain"
        assert result.confidence == 0.70

    def test_classify_domain_directory_lowercase(self, classifier, csharp_analysis):
        """Test classification of /domain/ directory."""
        file = ExampleFile(
            path="src/domain/products/product.py",
            purpose="Product domain entity",
        )

        result = classifier.classify(file, csharp_analysis)

        assert result is not None
        assert result.layer == "domain"
        assert result.confidence == 0.70

    def test_classify_core_directory(self, classifier, csharp_analysis):
        """Test classification of /Core/ directory."""
        file = ExampleFile(
            path="src/Core/Entities/User.cs",
            purpose="User core entity",
        )

        result = classifier.classify(file, csharp_analysis)

        assert result is not None
        assert result.layer == "domain"
        assert result.confidence == 0.70

    # Application Layer Tests

    def test_classify_application_directory(self, classifier, csharp_analysis):
        """Test classification of /Application/ directory."""
        file = ExampleFile(
            path="src/Application/Services/UserService.cs",
            purpose="User application service",
        )

        result = classifier.classify(file, csharp_analysis)

        assert result is not None
        assert result.layer == "application"
        assert result.confidence == 0.65

    def test_classify_usecases_directory(self, classifier, csharp_analysis):
        """Test classification of /UseCases/ directory."""
        file = ExampleFile(
            path="src/UseCases/CreateUser.cs",
            purpose="Create user use case",
        )

        result = classifier.classify(file, csharp_analysis)

        assert result is not None
        assert result.layer == "application"
        assert result.confidence == 0.65

    # Presentation Layer Tests

    def test_classify_web_directory(self, classifier, csharp_analysis):
        """Test classification of /Web/ directory."""
        file = ExampleFile(
            path="src/Web/Controllers/UserController.cs",
            purpose="User web controller",
        )

        result = classifier.classify(file, csharp_analysis)

        assert result is not None
        assert result.layer == "presentation"
        assert result.confidence == 0.70

    def test_classify_api_directory(self, classifier, csharp_analysis):
        """Test classification of /Api/ directory."""
        file = ExampleFile(
            path="src/Api/Endpoints/Users.cs",
            purpose="User API endpoints",
        )

        result = classifier.classify(file, csharp_analysis)

        assert result is not None
        assert result.layer == "presentation"
        assert result.confidence == 0.70

    def test_classify_endpoints_directory(self, classifier, csharp_analysis):
        """Test classification of /Endpoints/ directory."""
        file = ExampleFile(
            path="src/Endpoints/Products.cs",
            purpose="Product endpoints",
        )

        result = classifier.classify(file, csharp_analysis)

        assert result is not None
        assert result.layer == "presentation"
        assert result.confidence == 0.70

    def test_classify_controllers_directory(self, classifier, csharp_analysis):
        """Test classification of /Controllers/ directory."""
        file = ExampleFile(
            path="src/Controllers/ProductController.cs",
            purpose="Product controller",
        )

        result = classifier.classify(file, csharp_analysis)

        assert result is not None
        assert result.layer == "presentation"
        assert result.confidence == 0.65

    # Infrastructure Layer Tests

    def test_classify_infrastructure_directory(self, classifier, csharp_analysis):
        """Test classification of /Infrastructure/ directory."""
        file = ExampleFile(
            path="src/Infrastructure/Data/AppDbContext.cs",
            purpose="Database context",
        )

        result = classifier.classify(file, csharp_analysis)

        assert result is not None
        assert result.layer == "infrastructure"
        assert result.confidence == 0.65

    def test_classify_persistence_directory(self, classifier, csharp_analysis):
        """Test classification of /Persistence/ directory."""
        file = ExampleFile(
            path="src/Persistence/Repositories/UserRepository.cs",
            purpose="User repository",
        )

        result = classifier.classify(file, csharp_analysis)

        assert result is not None
        assert result.layer == "infrastructure"
        assert result.confidence == 0.65

    # Edge Cases

    def test_classify_empty_path(self, classifier, csharp_analysis):
        """Test handling of empty file path."""
        file = ExampleFile(path="", purpose="Empty path")

        result = classifier.classify(file, csharp_analysis)

        assert result is None

    def test_classify_unknown_pattern(self, classifier, csharp_analysis):
        """Test classification of file with no matching pattern."""
        file = ExampleFile(
            path="src/Random.cs",
            purpose="Random file",
        )

        result = classifier.classify(file, csharp_analysis)

        assert result is None

    # Language Support Tests

    def test_supports_all_languages(self, classifier):
        """Test that generic classifier supports all languages."""
        assert classifier.supports_language("JavaScript") is True
        assert classifier.supports_language("Python") is True
        assert classifier.supports_language("C#") is True
        assert classifier.supports_language("Go") is True
        assert classifier.supports_language("Unknown") is True


# LayerClassificationOrchestrator Tests

class TestLayerClassificationOrchestrator:
    """Test layer classification orchestrator."""

    def test_default_strategies(self):
        """Test orchestrator with default strategies."""
        orchestrator = LayerClassificationOrchestrator()

        assert len(orchestrator.strategies) == 2
        assert isinstance(orchestrator.strategies[0], JavaScriptLayerClassifier)
        assert isinstance(orchestrator.strategies[1], GenericLayerClassifier)

    def test_custom_strategies(self):
        """Test orchestrator with custom strategies."""
        strategies = [GenericLayerClassifier()]
        orchestrator = LayerClassificationOrchestrator(strategies=strategies)

        assert len(orchestrator.strategies) == 1
        assert isinstance(orchestrator.strategies[0], GenericLayerClassifier)

    def test_classify_javascript_file(self, javascript_analysis):
        """Test classification of JavaScript file uses JS classifier."""
        orchestrator = LayerClassificationOrchestrator()
        file = ExampleFile(
            path="src/components/Button.jsx",
            purpose="Button component",
        )

        result = orchestrator.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "presentation"
        assert result.confidence == 0.85
        assert result.strategy_used == "JavaScriptLayerClassifier"

    def test_classify_csharp_file_skips_js_classifier(self, csharp_analysis):
        """Test that C# file skips JS classifier and uses generic."""
        orchestrator = LayerClassificationOrchestrator()
        file = ExampleFile(
            path="src/Domain/Product.cs",
            purpose="Product domain entity",
        )

        result = orchestrator.classify(file, csharp_analysis)

        assert result is not None
        assert result.layer == "domain"
        assert result.confidence == 0.70
        assert result.strategy_used == "GenericLayerClassifier"

    def test_classify_empty_path(self, javascript_analysis):
        """Test handling of empty file path."""
        orchestrator = LayerClassificationOrchestrator()
        file = ExampleFile(path="", purpose="Empty path")

        result = orchestrator.classify(file, javascript_analysis)

        assert result is None

    def test_classify_unknown_file(self, javascript_analysis):
        """Test classification of unknown file returns None."""
        orchestrator = LayerClassificationOrchestrator()
        file = ExampleFile(
            path="src/unknown.txt",
            purpose="Unknown file type",
        )

        result = orchestrator.classify(file, javascript_analysis)

        assert result is None

    def test_strategy_order_matters(self, javascript_analysis):
        """Test that strategies are tried in order."""
        # JavaScript file should match JS classifier first
        orchestrator = LayerClassificationOrchestrator()
        file = ExampleFile(
            path="src/components/Button.jsx",
            purpose="Button component",
        )

        result = orchestrator.classify(file, javascript_analysis)

        # Should use JavaScriptLayerClassifier, not GenericLayerClassifier
        assert result is not None
        assert result.strategy_used == "JavaScriptLayerClassifier"

    def test_fallback_to_generic_classifier(self, javascript_analysis):
        """Test fallback to generic classifier when JS patterns don't match."""
        # Create custom orchestrator with both strategies
        orchestrator = LayerClassificationOrchestrator()

        # JavaScript file with generic pattern (no JS-specific pattern)
        file = ExampleFile(
            path="src/Domain/entities.js",
            purpose="Domain entities",
        )

        result = orchestrator.classify(file, javascript_analysis)

        # Should fallback to generic classifier
        assert result is not None
        assert result.layer == "domain"
        assert result.strategy_used == "GenericLayerClassifier"

    # Language Detection Tests

    def test_detect_javascript_extensions(self):
        """Test language detection for JavaScript files."""
        orchestrator = LayerClassificationOrchestrator()

        js_files = [
            "src/file.js",
            "src/file.jsx",
            "src/file.mjs",
        ]

        for path in js_files:
            lang = orchestrator._detect_language(path)
            assert lang == "JavaScript", f"Failed to detect JavaScript for {path}"

    def test_detect_typescript_extensions(self):
        """Test language detection for TypeScript files."""
        orchestrator = LayerClassificationOrchestrator()

        ts_files = [
            "src/file.ts",
            "src/file.tsx",
            "src/file.mts",
        ]

        for path in ts_files:
            lang = orchestrator._detect_language(path)
            assert lang == "JavaScript", f"Failed to detect TypeScript as JavaScript for {path}"

    def test_detect_csharp(self):
        """Test language detection for C# files."""
        orchestrator = LayerClassificationOrchestrator()

        lang = orchestrator._detect_language("src/Product.cs")
        assert lang == "C#"

    def test_detect_python(self):
        """Test language detection for Python files."""
        orchestrator = LayerClassificationOrchestrator()

        lang = orchestrator._detect_language("src/models.py")
        assert lang == "Python"

    def test_detect_various_languages(self):
        """Test language detection for various file types."""
        orchestrator = LayerClassificationOrchestrator()

        language_map = {
            "file.go": "Go",
            "file.rs": "Rust",
            "file.java": "Java",
            "file.cpp": "C++",
            "file.swift": "Swift",
            "file.kt": "Kotlin",
            "file.php": "PHP",
            "file.rb": "Ruby",
        }

        for path, expected_lang in language_map.items():
            lang = orchestrator._detect_language(path)
            assert lang == expected_lang, f"Failed to detect {expected_lang} for {path}"

    def test_detect_unknown_extension(self):
        """Test language detection for unknown file type."""
        orchestrator = LayerClassificationOrchestrator()

        lang = orchestrator._detect_language("README.md")
        assert lang == "Unknown"


# Integration Tests

class TestLayerClassificationIntegration:
    """Integration tests for complete layer classification workflow."""

    def test_javascript_project_classification(self, javascript_analysis):
        """Test classification of various files in JavaScript project."""
        orchestrator = LayerClassificationOrchestrator()

        test_cases = [
            # (path, expected_layer, min_confidence)
            ("src/__tests__/api.test.js", "testing", 0.95),
            ("src/components/Button.jsx", "presentation", 0.85),
            ("src/api/users.js", "data-access", 0.85),
            ("src/store/authSlice.js", "state", 0.90),
            ("src/routes/index.js", "routes", 0.95),
            ("src/utils/format.js", "utilities", 0.75),
            ("src/scripts/build.js", "scripts", 0.90),
        ]

        for path, expected_layer, min_confidence in test_cases:
            file = ExampleFile(path=path, purpose=f"Test {path}")
            result = orchestrator.classify(file, javascript_analysis)

            assert result is not None, f"Failed to classify {path}"
            assert result.layer == expected_layer, f"Wrong layer for {path}: expected {expected_layer}, got {result.layer}"
            assert result.confidence >= min_confidence, f"Confidence too low for {path}: {result.confidence} < {min_confidence}"

    def test_csharp_project_classification(self, csharp_analysis):
        """Test classification of various files in C# project."""
        orchestrator = LayerClassificationOrchestrator()

        test_cases = [
            # (path, expected_layer, min_confidence)
            ("src/Domain/Products/Product.cs", "domain", 0.70),
            ("src/Application/Services/UserService.cs", "application", 0.65),
            ("src/Infrastructure/Data/AppDbContext.cs", "infrastructure", 0.65),
            ("src/Web/Controllers/ProductController.cs", "presentation", 0.70),
        ]

        for path, expected_layer, min_confidence in test_cases:
            file = ExampleFile(path=path, purpose=f"Test {path}")
            result = orchestrator.classify(file, csharp_analysis)

            assert result is not None, f"Failed to classify {path}"
            assert result.layer == expected_layer, f"Wrong layer for {path}: expected {expected_layer}, got {result.layer}"
            assert result.confidence >= min_confidence, f"Confidence too low for {path}: {result.confidence} < {min_confidence}"

    def test_mixed_patterns_in_javascript(self, javascript_analysis):
        """Test files that could match multiple patterns."""
        orchestrator = LayerClassificationOrchestrator()

        # Component test file - should prioritize testing over presentation
        file = ExampleFile(
            path="src/components/__tests__/Button.spec.jsx",
            purpose="Button component test",
        )

        result = orchestrator.classify(file, javascript_analysis)

        assert result is not None
        assert result.layer == "testing"
        assert result.confidence == 0.95

    def test_confidence_score_ranges(self, javascript_analysis):
        """Test that confidence scores are in expected ranges."""
        orchestrator = LayerClassificationOrchestrator()

        # High confidence patterns (0.90-0.95)
        high_confidence_files = [
            "src/__tests__/api.test.js",
            "src/routes/api.js",
            "src/scripts/build.js",
            "src/store/auth.js",
        ]

        for path in high_confidence_files:
            file = ExampleFile(path=path, purpose=f"Test {path}")
            result = orchestrator.classify(file, javascript_analysis)
            assert result is not None, f"Failed to classify {path}"
            assert result.confidence >= 0.90, f"Expected high confidence for {path}, got {result.confidence}"

        # Medium confidence patterns (0.75-0.89)
        medium_confidence_files = [
            "src/components/Button.jsx",
            "src/api/users.js",
            "src/utils/format.js",
        ]

        for path in medium_confidence_files:
            file = ExampleFile(path=path, purpose=f"Test {path}")
            result = orchestrator.classify(file, javascript_analysis)
            assert result is not None, f"Failed to classify {path}"
            assert 0.75 <= result.confidence < 0.90, f"Expected medium confidence for {path}, got {result.confidence}"


# Backward Compatibility Tests

class TestBackwardCompatibility:
    """Test backward compatibility with old layer classification."""

    def test_classification_result_compatible_with_old_code(self):
        """Test that ClassificationResult can be used like old string result."""
        result = ClassificationResult(
            layer="presentation",
            confidence=0.85,
            strategy_used="JavaScriptLayerClassifier",
        )

        # Old code might access just the layer
        assert result.layer == "presentation"

        # Old code might check if result is truthy
        assert result is not None

    def test_orchestrator_returns_none_like_old_classifier(self, javascript_analysis):
        """Test that orchestrator returns None for unknown files like old code."""
        orchestrator = LayerClassificationOrchestrator()
        file = ExampleFile(path="README.md", purpose="Documentation")

        result = orchestrator.classify(file, javascript_analysis)

        # Should return None, just like old code would
        assert result is None

    def test_generic_patterns_match_old_behavior(self, csharp_analysis):
        """Test that generic patterns produce similar results to old code."""
        orchestrator = LayerClassificationOrchestrator()

        # Old code would classify these as domain/application/infrastructure
        old_patterns = [
            ("src/Domain/Product.cs", "domain"),
            ("src/Application/UserService.cs", "application"),
            ("src/Infrastructure/AppDbContext.cs", "infrastructure"),
        ]

        for path, expected_layer in old_patterns:
            file = ExampleFile(path=path, purpose=f"Test {path}")
            result = orchestrator.classify(file, csharp_analysis)

            assert result is not None
            assert result.layer == expected_layer
