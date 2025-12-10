"""
Unit tests for manifest_generator.py import fixes (TASK-BRIDGE-006).

Tests the importlib pattern used to avoid 'global' keyword issue in Python 3.14+.
"""

import importlib
import pytest
from pathlib import Path


class TestManifestGeneratorImports:
    """Test import fixes in manifest_generator.py"""

    def test_importlib_pattern_works(self):
        """Test that importlib.import_module works for codebase_analyzer.models"""
        # This is the pattern used in manifest_generator.py
        _codebase_models = importlib.import_module('installer.core.lib.codebase_analyzer.models')

        assert _codebase_models is not None
        assert hasattr(_codebase_models, 'CodebaseAnalysis')
        assert hasattr(_codebase_models, 'LayerInfo')

    def test_manifest_generator_module_loads(self):
        """Test that manifest_generator module loads without errors"""
        manifest_gen_module = importlib.import_module(
            'installer.core.lib.template_creation.manifest_generator'
        )

        assert manifest_gen_module is not None
        assert hasattr(manifest_gen_module, 'ManifestGenerator')

    def test_codebase_analysis_model_accessible(self):
        """Test that CodebaseAnalysis model is accessible via importlib pattern"""
        _codebase_models = importlib.import_module('installer.core.lib.codebase_analyzer.models')
        CodebaseAnalysis = _codebase_models.CodebaseAnalysis

        # Verify it's a class
        assert isinstance(CodebaseAnalysis, type)

    def test_layer_info_model_accessible(self):
        """Test that LayerInfo model is accessible via importlib pattern"""
        _codebase_models = importlib.import_module('installer.core.lib.codebase_analyzer.models')
        LayerInfo = _codebase_models.LayerInfo

        # Verify it's a class
        assert isinstance(LayerInfo, type)

    def test_manifest_generator_imports_do_not_use_global_keyword(self):
        """Test that manifest_generator.py doesn't use 'global' as identifier"""
        manifest_path = Path('installer/core/lib/template_creation/manifest_generator.py')
        content = manifest_path.read_text()

        # Should use importlib pattern instead of direct import
        assert 'importlib.import_module' in content
        assert '_codebase_models = importlib.import_module' in content

        # Should NOT have broken import pattern
        assert 'from codebase_analyzer.models import' not in content
        assert 'from installer.core.lib.codebase_analyzer.models import' not in content

    def test_manifest_generator_assigns_classes_correctly(self):
        """Test that classes are assigned from importlib module"""
        manifest_path = Path('installer/core/lib/template_creation/manifest_generator.py')
        content = manifest_path.read_text()

        # Should assign classes from imported module
        assert 'CodebaseAnalysis = _codebase_models.CodebaseAnalysis' in content
        assert 'LayerInfo = _codebase_models.LayerInfo' in content


class TestManifestGeneratorFunctionality:
    """Test basic manifest_generator functionality"""

    def test_manifest_generator_class_exists(self):
        """Test that ManifestGenerator class can be imported"""
        # Use importlib pattern to avoid Python 3.14 'global' keyword issue
        manifest_gen_module = importlib.import_module(
            'installer.core.lib.template_creation.manifest_generator'
        )
        ManifestGenerator = manifest_gen_module.ManifestGenerator

        assert ManifestGenerator is not None
        assert hasattr(ManifestGenerator, '__init__')
        assert hasattr(ManifestGenerator, 'generate')

    def test_manifest_generator_uses_codebase_analysis(self):
        """Test that ManifestGenerator accepts CodebaseAnalysis in __init__"""
        # Use importlib pattern
        manifest_gen_module = importlib.import_module(
            'installer.core.lib.template_creation.manifest_generator'
        )
        ManifestGenerator = manifest_gen_module.ManifestGenerator

        _codebase_models = importlib.import_module('installer.core.lib.codebase_analyzer.models')
        CodebaseAnalysis = _codebase_models.CodebaseAnalysis

        # Verify __init__ signature accepts CodebaseAnalysis
        import inspect
        sig = inspect.signature(ManifestGenerator.__init__)
        params = list(sig.parameters.keys())

        assert 'analysis' in params
