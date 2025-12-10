"""
Unit tests for template_create_orchestrator.py entry point (TASK-BRIDGE-006).

Tests the __main__ block and argument parser.
"""

import importlib
import pytest
import subprocess
import sys
from pathlib import Path


class TestOrchestratorEntryPoint:
    """Test __main__ entry point in template_create_orchestrator.py"""

    def test_orchestrator_module_has_main_block(self):
        """Test that orchestrator module has __main__ block"""
        orchestrator_path = Path('installer/core/commands/lib/template_create_orchestrator.py')
        content = orchestrator_path.read_text()

        assert 'if __name__ == "__main__":' in content

    def test_orchestrator_has_argument_parser(self):
        """Test that orchestrator has argument parser setup"""
        orchestrator_path = Path('installer/core/commands/lib/template_create_orchestrator.py')
        content = orchestrator_path.read_text()

        assert 'import argparse' in content
        assert 'parser = argparse.ArgumentParser' in content

    def test_orchestrator_argument_parser_has_all_flags(self):
        """Test that all required flags are in argument parser"""
        orchestrator_path = Path('installer/core/commands/lib/template_create_orchestrator.py')
        content = orchestrator_path.read_text()

        # All flags from acceptance criteria
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
            assert flag in content, f"Flag {flag} not found in argument parser"

    def test_orchestrator_module_executable(self):
        """Test that orchestrator module is executable with -m flag"""
        result = subprocess.run(
            [sys.executable, '-m', 'installer.core.commands.lib.template_create_orchestrator', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0
        assert 'usage:' in result.stdout.lower()

    def test_orchestrator_help_shows_all_flags(self):
        """Test that --help output shows all flags"""
        result = subprocess.run(
            [sys.executable, '-m', 'installer.core.commands.lib.template_create_orchestrator', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0

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

    def test_orchestrator_calls_run_template_create(self):
        """Test that __main__ block calls run_template_create"""
        orchestrator_path = Path('installer/core/commands/lib/template_create_orchestrator.py')
        content = orchestrator_path.read_text()

        # Find __main__ block
        main_block_start = content.find('if __name__ == "__main__":')
        assert main_block_start != -1

        main_block = content[main_block_start:]

        assert 'result = run_template_create(' in main_block
        assert 'sys.exit(' in main_block

    def test_orchestrator_passes_args_to_run_template_create(self):
        """Test that parsed args are passed to run_template_create"""
        orchestrator_path = Path('installer/core/commands/lib/template_create_orchestrator.py')
        content = orchestrator_path.read_text()

        # Find __main__ block
        main_block_start = content.find('if __name__ == "__main__":')
        main_block = content[main_block_start:]

        # Check all args are passed
        required_params = [
            'codebase_path',
            'output_location',
            'skip_qa',
            'dry_run',
            'validate',
            'max_templates',
            'no_agents',
            'resume',
            'verbose'
        ]

        for param in required_params:
            assert param in main_block, f"Parameter {param} not passed to run_template_create"

    def test_orchestrator_returns_proper_exit_code(self):
        """Test that orchestrator returns exit code based on result"""
        orchestrator_path = Path('installer/core/commands/lib/template_create_orchestrator.py')
        content = orchestrator_path.read_text()

        main_block_start = content.find('if __name__ == "__main__":')
        main_block = content[main_block_start:]

        # Should exit with result.exit_code or 0
        assert 'sys.exit(result.exit_code if not result.success else 0)' in main_block


class TestOrchestratorModuleImports:
    """Test import patterns in template_create_orchestrator.py"""

    def test_orchestrator_uses_importlib_for_all_imports(self):
        """Test that orchestrator uses importlib pattern for all module imports"""
        orchestrator_path = Path('installer/core/commands/lib/template_create_orchestrator.py')
        content = orchestrator_path.read_text()

        # Should use importlib pattern
        assert 'import importlib' in content
        assert '_template_qa_module = importlib.import_module' in content
        assert '_codebase_analyzer_module = importlib.import_module' in content
        assert '_manifest_gen_module = importlib.import_module' in content

    def test_orchestrator_module_loads_without_errors(self):
        """Test that orchestrator module loads successfully"""
        orchestrator_module = importlib.import_module(
            'installer.core.commands.lib.template_create_orchestrator'
        )

        assert orchestrator_module is not None
        assert hasattr(orchestrator_module, 'TemplateCreateOrchestrator')
        assert hasattr(orchestrator_module, 'run_template_create')

    def test_orchestrator_does_not_use_global_keyword(self):
        """Test that orchestrator doesn't use 'global' as identifier in imports"""
        orchestrator_path = Path('installer/core/commands/lib/template_create_orchestrator.py')
        content = orchestrator_path.read_text()

        # Should NOT have broken import pattern
        assert 'from installer.core.' not in content.split('import importlib')[0]


class TestOrchestratorPathAgnostic:
    """Test that orchestrator works from any directory"""

    def test_orchestrator_works_from_project_root(self, tmp_path, monkeypatch):
        """Test running from project root"""
        # Change to project root
        project_root = Path(__file__).parent.parent.parent.parent
        monkeypatch.chdir(project_root)

        result = subprocess.run(
            [sys.executable, '-m', 'installer.core.commands.lib.template_create_orchestrator', '--help'],
            capture_output=True,
            text=True,
            timeout=10
        )

        assert result.returncode == 0

    def test_orchestrator_works_from_temp_directory(self, tmp_path, monkeypatch):
        """Test running from temporary directory (should fail gracefully or work with PYTHONPATH)"""
        # This test verifies the module is path-independent when PYTHONPATH is set
        monkeypatch.chdir(tmp_path)

        project_root = Path(__file__).parent.parent.parent.parent

        result = subprocess.run(
            [sys.executable, '-m', 'installer.core.commands.lib.template_create_orchestrator', '--help'],
            capture_output=True,
            text=True,
            timeout=10,
            env={'PYTHONPATH': str(project_root)}
        )

        # Should work when PYTHONPATH is set
        assert result.returncode == 0


class TestOrchestratorArguments:
    """Test argument validation"""

    def test_orchestrator_output_location_choices(self):
        """Test that output-location has correct choices"""
        orchestrator_path = Path('installer/core/commands/lib/template_create_orchestrator.py')
        content = orchestrator_path.read_text()

        # Find output-location argument
        assert "choices=['global', 'repo']" in content

    def test_orchestrator_boolean_flags_are_store_true(self):
        """Test that boolean flags use store_true action"""
        orchestrator_path = Path('installer/core/commands/lib/template_create_orchestrator.py')
        content = orchestrator_path.read_text()

        boolean_flags = ['skip-qa', 'dry-run', 'validate', 'no-agents', 'resume', 'verbose']

        # Find __main__ block where parser is defined
        main_block_start = content.find('if __name__ == "__main__":')
        assert main_block_start != -1
        parser_section = content[main_block_start:]

        for flag in boolean_flags:
            # Find parser.add_argument for this specific flag
            flag_pattern = f'parser.add_argument("--{flag}"'
            assert flag_pattern in parser_section, f"Flag --{flag} not found in parser"

            # Find the section containing this specific argument
            flag_start = parser_section.find(flag_pattern)
            # Get next 200 characters (enough for one argument definition)
            flag_def = parser_section[flag_start:flag_start + 200]

            # Should have action=store_true (with either single or double quotes)
            assert 'action="store_true"' in flag_def or "action='store_true'" in flag_def, \
                f"Flag --{flag} should have action=store_true"

    def test_orchestrator_max_templates_is_integer(self):
        """Test that max-templates accepts integer"""
        orchestrator_path = Path('installer/core/commands/lib/template_create_orchestrator.py')
        content = orchestrator_path.read_text()

        # Find __main__ block
        main_block_start = content.find('if __name__ == "__main__":')
        parser_section = content[main_block_start:]

        # Find max-templates argument
        flag_pattern = 'parser.add_argument("--max-templates"'
        assert flag_pattern in parser_section

        flag_start = parser_section.find(flag_pattern)
        flag_def = parser_section[flag_start:flag_start + 200]

        assert 'type=int' in flag_def
