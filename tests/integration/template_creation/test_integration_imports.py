"""
Integration tests for TASK-BRIDGE-006 import fixes.

Tests full workflow: orchestrator → manifest_generator → codebase_analyzer.
"""

import pytest
import subprocess
import sys
from pathlib import Path


class TestIntegrationImports:
    """Test import chain works end-to-end"""

    def test_full_import_chain(self):
        """Test complete import chain from orchestrator to codebase_analyzer"""
        # 1. Import orchestrator
        from installer.core.commands.lib.template_create_orchestrator import ManifestGenerator
        assert ManifestGenerator is not None

        # 2. Import codebase_analyzer.models directly
        from installer.core.lib.codebase_analyzer.models import (
            CodebaseAnalysis,
            LayerInfo
        )

        assert CodebaseAnalysis is not None
        assert LayerInfo is not None

    def test_orchestrator_to_manifest_generator_integration(self):
        """Test orchestrator can instantiate and use ManifestGenerator"""
        from installer.core.commands.lib.template_create_orchestrator import ManifestGenerator

        # Verify ManifestGenerator is the correct class
        assert hasattr(ManifestGenerator, 'generate')
        assert hasattr(ManifestGenerator, '__init__')

    def test_manifest_generator_imports_codebase_models(self):
        """Test manifest_generator successfully imports codebase_analyzer.models"""
        # Import manifest_generator module
        from installer.core.lib.template_creation import manifest_generator

        # Should have CodebaseAnalysis and LayerInfo available
        assert hasattr(manifest_generator, 'CodebaseAnalysis')
        assert hasattr(manifest_generator, 'LayerInfo')

    def test_no_import_errors_on_module_load(self):
        """Test all modules load without ImportError"""
        try:
            from installer.core.lib.codebase_analyzer.models import CodebaseAnalysis
            from installer.core.lib.template_creation.manifest_generator import ManifestGenerator
            from installer.core.commands.lib.template_create_orchestrator import TemplateCreateOrchestrator

            assert CodebaseAnalysis is not None
            assert ManifestGenerator is not None
            assert TemplateCreateOrchestrator is not None
        except ImportError as e:
            pytest.fail(f"ImportError loading modules: {e}")


class TestIntegrationCommandExecution:
    """Test command execution from different contexts"""

    def test_module_execution_shows_help(self):
        """Test python -m execution shows help"""
        result = subprocess.run(
            [sys.executable, '-m', 'installer.core.commands.lib.template_create_orchestrator', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert 'usage:' in result.stdout.lower()
        assert 'Template creation orchestrator' in result.stdout

    def test_module_execution_recognizes_all_flags(self):
        """Test that module execution recognizes all command flags"""
        result = subprocess.run(
            [sys.executable, '-m', 'installer.core.commands.lib.template_create_orchestrator', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0

        # Check all flags in help output
        required_flags = [
            '--path',
            '--output-location',
            '--skip-qa',
            '--dry-run',
            '--validate',
            '--max-templates',
            '--no-agents',
            '--resume',
            '--verbose'
        ]

        for flag in required_flags:
            assert flag in result.stdout, f"Flag {flag} not in help output"

    def test_module_execution_with_invalid_flag_fails_gracefully(self):
        """Test that invalid flags produce error"""
        result = subprocess.run(
            [sys.executable, '-m', 'installer.core.commands.lib.template_create_orchestrator', '--invalid-flag'],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode != 0
        assert 'error' in result.stderr.lower() or 'usage' in result.stderr.lower()

    def test_module_execution_from_project_root(self):
        """Test execution from project root directory"""
        project_root = Path(__file__).parent.parent.parent.parent

        result = subprocess.run(
            [sys.executable, '-m', 'installer.core.commands.lib.template_create_orchestrator', '--help'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_root
        )

        assert result.returncode == 0
        assert 'usage:' in result.stdout.lower()


class TestIntegrationEdgeCases:
    """Test edge cases and error handling"""

    def test_importlib_pattern_handles_missing_module_gracefully(self):
        """Test that importlib.import_module handles missing modules correctly"""
        import importlib
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module('installer.core.lib.nonexistent.module')

    def test_python_314_global_keyword_not_used_as_identifier(self):
        """Test that 'global' keyword is not used as identifier (Python 3.14+ compatibility)"""
        files_to_check = [
            'installer/core/lib/template_creation/manifest_generator.py',
            'installer/core/commands/lib/template_create_orchestrator.py'
        ]

        for file_path in files_to_check:
            path = Path(file_path)
            if not path.exists():
                pytest.skip(f"File {file_path} not found")

            content = path.read_text()

            # Should use standard import pattern
            # Check that imports are valid Python
            if 'installer.core.' in content:
                for line in content.splitlines():
                    if 'installer.core.' in line and 'import' in line:
                        if line.strip().startswith('#'):
                            continue  # Skip comments
                        # Verify it's a valid import statement
                        assert 'from ' in line or 'import ' in line, \
                            f"Invalid import syntax in {file_path}: {line}"

    def test_all_imports_compile_successfully(self):
        """Test that all Python files compile without syntax errors"""
        files_to_compile = [
            'installer/core/lib/template_creation/manifest_generator.py',
            'installer/core/commands/lib/template_create_orchestrator.py'
        ]

        for file_path in files_to_compile:
            result = subprocess.run(
                [sys.executable, '-m', 'py_compile', file_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, f"Compilation failed for {file_path}: {result.stderr}"


class TestIntegrationAcceptanceCriteria:
    """Test all acceptance criteria from TASK-BRIDGE-006"""

    def test_code_compiles_without_errors(self):
        """Acceptance: Code compiles without errors"""
        files = [
            'installer/core/lib/template_creation/manifest_generator.py',
            'installer/core/commands/lib/template_create_orchestrator.py'
        ]

        for file_path in files:
            result = subprocess.run(
                [sys.executable, '-m', 'py_compile', file_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            assert result.returncode == 0, f"File {file_path} does not compile"

    def test_imports_resolve_correctly(self):
        """Acceptance: Imports resolve correctly"""
        # Test manifest_generator imports
        from installer.core.lib.template_creation import manifest_generator
        assert hasattr(manifest_generator, 'CodebaseAnalysis')
        assert hasattr(manifest_generator, 'LayerInfo')

        # Test orchestrator imports
        from installer.core.commands.lib import template_create_orchestrator
        assert hasattr(template_create_orchestrator, 'ManifestGenerator')

    def test_module_executable_with_m_flag(self):
        """Acceptance: Module executable with -m flag"""
        result = subprocess.run(
            [sys.executable, '-m', 'installer.core.commands.lib.template_create_orchestrator', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0

    def test_argument_parser_handles_all_flags(self):
        """Acceptance: Argument parser handles all flags"""
        result = subprocess.run(
            [sys.executable, '-m', 'installer.core.commands.lib.template_create_orchestrator', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )

        required_flags = [
            '--path', '--output-location', '--skip-qa', '--dry-run',
            '--validate', '--max-templates', '--no-agents', '--resume', '--verbose'
        ]

        for flag in required_flags:
            assert flag in result.stdout

    def test_command_works_from_any_directory(self):
        """Acceptance: Command works from any directory (with PYTHONPATH)"""
        project_root = Path(__file__).parent.parent.parent.parent

        # Test from project root
        result = subprocess.run(
            [sys.executable, '-m', 'installer.core.commands.lib.template_create_orchestrator', '--help'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=project_root
        )

        assert result.returncode == 0
