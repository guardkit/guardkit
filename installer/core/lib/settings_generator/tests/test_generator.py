"""
Tests for settings_generator module.

TASK-IMP-TC-F8A3: Test suite for layer directory extraction from example files.
"""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
import importlib

# Import using importlib to avoid 'global' keyword issue
_generator_module = importlib.import_module(
    'installer.core.lib.settings_generator.generator'
)
_models_module = importlib.import_module(
    'installer.core.lib.settings_generator.models'
)

SettingsGenerator = _generator_module.SettingsGenerator
CaseStyle = _models_module.CaseStyle
TestLocation = _models_module.TestLocation
NamingConvention = _models_module.NamingConvention
FileOrganization = _models_module.FileOrganization
LayerMapping = _models_module.LayerMapping
CodeStyle = _models_module.CodeStyle
TemplateSettings = _models_module.TemplateSettings


def create_mock_analysis(
    primary_language: str = "python",
    layers: list = None,
    example_files: list = None,
    architectural_style: str = "layered"
):
    """Create a mock CodebaseAnalysis for testing."""
    analysis = MagicMock()
    
    # Technology
    analysis.technology = MagicMock()
    analysis.technology.primary_language = primary_language
    
    # Architecture
    analysis.architecture = MagicMock()
    analysis.architecture.architectural_style = architectural_style
    
    if layers is None:
        layers = []
    analysis.architecture.layers = layers
    
    if example_files is None:
        example_files = []
    analysis.example_files = example_files
    
    return analysis


def create_mock_layer(name: str, description: str = ""):
    """Create a mock LayerInfo."""
    layer = MagicMock()
    layer.name = name
    layer.description = description
    return layer


def create_mock_example_file(path: str, layer: str = None):
    """Create a mock ExampleFile."""
    example = MagicMock()
    example.path = path
    example.layer = layer
    return example


class TestExtractLayerDirectories:
    """Test _extract_layer_directories method."""

    def test_empty_example_files(self):
        """Test with no example files."""
        analysis = create_mock_analysis(example_files=[])
        generator = SettingsGenerator(analysis)
        
        result = generator._extract_layer_directories()
        assert result == {}

    def test_single_file_per_layer(self):
        """Test with single file per layer."""
        example_files = [
            create_mock_example_file('src/services/user_service.py', 'services'),
            create_mock_example_file('src/models/user.py', 'models'),
        ]
        analysis = create_mock_analysis(example_files=example_files)
        generator = SettingsGenerator(analysis)
        
        result = generator._extract_layer_directories()
        assert result['services'] == 'src/services'
        assert result['models'] == 'src/models'

    def test_multiple_files_same_layer(self):
        """Test with multiple files in same layer."""
        example_files = [
            create_mock_example_file('src/services/user_service.py', 'services'),
            create_mock_example_file('src/services/order_service.py', 'services'),
            create_mock_example_file('src/services/product_service.py', 'services'),
        ]
        analysis = create_mock_analysis(example_files=example_files)
        generator = SettingsGenerator(analysis)
        
        result = generator._extract_layer_directories()
        assert result['services'] == 'src/services'

    def test_files_without_layer(self):
        """Test files without layer assignment are ignored."""
        example_files = [
            create_mock_example_file('src/services/user_service.py', 'services'),
            create_mock_example_file('README.md', None),  # No layer
        ]
        analysis = create_mock_analysis(example_files=example_files)
        generator = SettingsGenerator(analysis)
        
        result = generator._extract_layer_directories()
        assert 'services' in result
        assert len(result) == 1

    def test_nested_directories(self):
        """Test with nested directory structures."""
        example_files = [
            create_mock_example_file('src/app/services/user_service.py', 'services'),
            create_mock_example_file('src/app/services/auth/auth_service.py', 'services'),
        ]
        analysis = create_mock_analysis(example_files=example_files)
        generator = SettingsGenerator(analysis)
        
        result = generator._extract_layer_directories()
        # Should find common parent
        assert 'services' in result
        assert 'src/app/services' in result['services']


class TestCreateLayerMappings:
    """Test _create_layer_mappings method."""

    def test_uses_actual_directories(self):
        """Test that layer mappings use actual directories from example files."""
        layers = [create_mock_layer('services')]
        example_files = [
            create_mock_example_file('lib/services/user_service.py', 'services'),
        ]
        analysis = create_mock_analysis(
            layers=layers,
            example_files=example_files
        )
        generator = SettingsGenerator(analysis)
        
        mappings = generator._create_layer_mappings()
        
        assert 'services' in mappings
        assert mappings['services'].directory == 'lib/services'

    def test_fallback_to_inferred_directory(self):
        """Test fallback when no example files for layer."""
        layers = [create_mock_layer('domain')]
        analysis = create_mock_analysis(
            layers=layers,
            example_files=[]  # No example files
        )
        generator = SettingsGenerator(analysis)
        
        mappings = generator._create_layer_mappings()
        
        assert 'domain' in mappings
        # Should fall back to src/{layer_name}
        assert mappings['domain'].directory == 'src/domain'


class TestInferFilePatterns:
    """Test _infer_file_patterns_from_examples method."""

    def test_extracts_patterns_from_examples(self):
        """Test file patterns extracted from example files."""
        layers = [create_mock_layer('services')]
        example_files = [
            create_mock_example_file('src/services/user_service.py', 'services'),
            create_mock_example_file('src/services/order_service.py', 'services'),
        ]
        analysis = create_mock_analysis(
            primary_language='python',
            layers=layers,
            example_files=example_files
        )
        generator = SettingsGenerator(analysis)
        
        layer = layers[0]
        patterns = generator._infer_file_patterns_from_examples(layer)
        
        assert '*.py' in patterns
        # Should include test exclusions
        assert '!*_test.py' in patterns or '!test_*.py' in patterns

    def test_fallback_to_language_patterns(self):
        """Test fallback to language-based patterns when no examples."""
        layers = [create_mock_layer('services')]
        analysis = create_mock_analysis(
            primary_language='typescript',
            layers=layers,
            example_files=[]
        )
        generator = SettingsGenerator(analysis)
        
        layer = layers[0]
        patterns = generator._infer_file_patterns_from_examples(layer)
        
        # Should use TypeScript patterns
        assert '*.ts' in patterns or '*.tsx' in patterns


class TestGenerate:
    """Test the generate method."""

    def test_generate_returns_template_settings(self):
        """Test that generate returns valid TemplateSettings."""
        layers = [create_mock_layer('services')]
        example_files = [
            create_mock_example_file('src/services/service.py', 'services'),
        ]
        analysis = create_mock_analysis(
            primary_language='python',
            layers=layers,
            example_files=example_files
        )
        generator = SettingsGenerator(analysis)
        
        settings = generator.generate()
        
        assert isinstance(settings, TemplateSettings)
        assert settings.schema_version == '1.0.0'
        assert 'services' in settings.layer_mappings

    def test_generate_with_different_languages(self):
        """Test generation for different primary languages."""
        for lang in ['python', 'typescript', 'csharp', 'java']:
            analysis = create_mock_analysis(primary_language=lang)
            generator = SettingsGenerator(analysis)
            
            settings = generator.generate()
            
            assert isinstance(settings, TemplateSettings)
            assert settings.naming_conventions is not None
            assert settings.code_style is not None


class TestNamingConventions:
    """Test naming convention extraction."""

    def test_python_conventions(self):
        """Test Python naming conventions."""
        analysis = create_mock_analysis(primary_language='python')
        generator = SettingsGenerator(analysis)
        
        conventions = generator._extract_naming_conventions()
        
        assert 'class' in conventions
        assert conventions['class'].case_style == CaseStyle.PASCAL_CASE
        assert 'function' in conventions
        assert conventions['function'].case_style == CaseStyle.SNAKE_CASE

    def test_typescript_conventions(self):
        """Test TypeScript naming conventions."""
        analysis = create_mock_analysis(primary_language='typescript')
        generator = SettingsGenerator(analysis)
        
        conventions = generator._extract_naming_conventions()
        
        assert 'class' in conventions
        assert conventions['class'].case_style == CaseStyle.PASCAL_CASE
        assert 'function' in conventions
        assert conventions['function'].case_style == CaseStyle.CAMEL_CASE

    def test_csharp_conventions(self):
        """Test C# naming conventions."""
        analysis = create_mock_analysis(primary_language='csharp')
        generator = SettingsGenerator(analysis)
        
        conventions = generator._extract_naming_conventions()
        
        assert 'class' in conventions
        assert 'interface' in conventions
        assert conventions['interface'].prefix == 'I'


class TestCodeStyle:
    """Test code style inference."""

    def test_python_code_style(self):
        """Test Python code style defaults."""
        analysis = create_mock_analysis(primary_language='python')
        generator = SettingsGenerator(analysis)
        
        style = generator._infer_code_style()
        
        assert style.indentation == 'spaces'
        assert style.indent_size == 4
        assert style.line_length == 88  # Black default

    def test_typescript_code_style(self):
        """Test TypeScript code style defaults."""
        analysis = create_mock_analysis(primary_language='typescript')
        generator = SettingsGenerator(analysis)
        
        style = generator._infer_code_style()
        
        assert style.indentation == 'spaces'
        assert style.indent_size == 2
        assert style.trailing_commas == True
