"""
Unit tests for manifest_generator.py import fixes (TASK-BRIDGE-006).

Tests the standard import pattern.
"""

import pytest
from pathlib import Path


class TestManifestGeneratorImports:
    """Test import fixes in manifest_generator.py"""

    def test_standard_imports_work(self):
        """Test that standard imports work for codebase_analyzer.models"""
        from installer.core.lib.codebase_analyzer.models import (
            CodebaseAnalysis,
            LayerInfo
        )

        assert CodebaseAnalysis is not None
        assert LayerInfo is not None

    def test_manifest_generator_module_loads(self):
        """Test that manifest_generator module loads without errors"""
        from installer.core.lib.template_creation.manifest_generator import ManifestGenerator

        assert ManifestGenerator is not None

    def test_codebase_analysis_model_accessible(self):
        """Test that CodebaseAnalysis model is accessible"""
        from installer.core.lib.codebase_analyzer.models import CodebaseAnalysis

        # Verify it's a class
        assert isinstance(CodebaseAnalysis, type)

    def test_layer_info_model_accessible(self):
        """Test that LayerInfo model is accessible"""
        from installer.core.lib.codebase_analyzer.models import LayerInfo

        # Verify it's a class
        assert isinstance(LayerInfo, type)

    def test_manifest_generator_uses_standard_imports(self):
        """Test that manifest_generator.py uses standard imports"""
        manifest_path = Path('installer/core/lib/template_creation/manifest_generator.py')
        content = manifest_path.read_text()

        # Should use standard import pattern
        assert 'from installer.core.lib.codebase_analyzer.models import' in content

        # Should NOT have broken import pattern
        assert 'from codebase_analyzer.models import' not in content

    def test_manifest_generator_imports_classes(self):
        """Test that classes are imported correctly"""
        manifest_path = Path('installer/core/lib/template_creation/manifest_generator.py')
        content = manifest_path.read_text()

        # Should import classes directly
        assert 'CodebaseAnalysis' in content
        assert 'LayerInfo' in content


class TestManifestGeneratorFunctionality:
    """Test basic manifest_generator functionality"""

    def test_manifest_generator_class_exists(self):
        """Test that ManifestGenerator class can be imported"""
        from installer.core.lib.template_creation.manifest_generator import ManifestGenerator

        assert ManifestGenerator is not None
        assert hasattr(ManifestGenerator, '__init__')
        assert hasattr(ManifestGenerator, 'generate')

    def test_manifest_generator_uses_codebase_analysis(self):
        """Test that ManifestGenerator accepts CodebaseAnalysis in __init__"""
        from installer.core.lib.template_creation.manifest_generator import ManifestGenerator
        from installer.core.lib.codebase_analyzer.models import CodebaseAnalysis

        # Verify __init__ signature accepts CodebaseAnalysis
        import inspect
        sig = inspect.signature(ManifestGenerator.__init__)
        params = list(sig.parameters.keys())

        assert 'analysis' in params
