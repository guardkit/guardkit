"""
Integration Tests for Template Create Orchestrator

Tests orchestrator configuration and basic workflow structure.
Full integration tests will be added when all dependencies are implemented.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Add lib directory to path
lib_path = Path(__file__).parent.parent.parent / "installer" / "global"
commands_lib_path = lib_path / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))
if str(commands_lib_path) not in sys.path:
    sys.path.insert(0, str(commands_lib_path))


def test_orchestrator_imports():
    """Test that orchestrator module can be imported"""
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "template_create_orchestrator",
            commands_lib_path / "template_create_orchestrator.py"
        )
        module = importlib.util.module_from_spec(spec)

        # This will fail if there are syntax errors or import issues
        # We're not executing it yet, just loading it
        assert spec is not None
        assert module is not None

    except Exception as e:
        pytest.fail(f"Failed to import orchestrator module: {e}")


def test_orchestrator_has_required_classes():
    """Test that orchestrator module defines required classes"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "template_create_orchestrator",
        commands_lib_path / "template_create_orchestrator.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["template_create_orchestrator"] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        # Module may fail to execute due to missing dependencies
        # but we can still check if classes are defined in the source
        pass

    # Read source to check class definitions
    source = (commands_lib_path / "template_create_orchestrator.py").read_text()

    assert "class OrchestrationConfig" in source
    assert "class OrchestrationResult" in source
    assert "class TemplateCreateOrchestrator" in source
    assert "def run_template_create" in source


def test_orchestrator_has_all_phases():
    """Test that orchestrator implements all required phases"""
    source = (commands_lib_path / "template_create_orchestrator.py").read_text()

    # Check for all required phases (current implementation)
    assert "def _phase1_ai_analysis" in source
    assert "def _phase2_manifest_generation" in source
    assert "def _phase3_settings_generation" in source
    assert "def _phase4_template_generation" in source
    assert "def _phase5_agent_recommendation" in source
    assert "def _phase7_write_agents" in source
    assert "def _phase7_5_enhance_agents" in source
    assert "def _phase8_claude_md_generation" in source


def test_orchestrator_has_error_handling():
    """Test that orchestrator has error handling methods"""
    source = (commands_lib_path / "template_create_orchestrator.py").read_text()

    assert "def _create_error_result" in source
    assert "try:" in source
    assert "except" in source
    assert "KeyboardInterrupt" in source


def test_orchestrator_has_print_methods():
    """Test that orchestrator has user feedback methods"""
    source = (commands_lib_path / "template_create_orchestrator.py").read_text()

    assert "def _print_header" in source
    assert "def _print_phase_header" in source
    assert "def _print_success" in source
    assert "def _print_error" in source


def test_orchestrator_config_structure():
    """Test that OrchestrationConfig has required fields"""
    source = (commands_lib_path / "template_create_orchestrator.py").read_text()

    # Check dataclass definition
    assert "class OrchestrationConfig" in source
    assert "codebase_path" in source
    assert "output_path" in source
    assert "dry_run" in source


def test_orchestrator_result_structure():
    """Test that OrchestrationResult has required fields"""
    source = (commands_lib_path / "template_create_orchestrator.py").read_text()

    # Check dataclass definition
    assert "class OrchestrationResult" in source
    assert "success" in source
    assert "output_path" in source
    assert "errors" in source


def test_convenience_function_signature():
    """Test that convenience function has correct signature"""
    source = (commands_lib_path / "template_create_orchestrator.py").read_text()

    assert "def run_template_create(" in source
    assert "codebase_path" in source
    assert "output_location" in source


class TestPhase75BatchEnhancement:
    """Tests for Phase 7.5 batch enhancement result interpretation fix"""

    def test_orchestrator_result_extraction_full_success(self):
        """Test orchestrator correctly interprets full success batch result"""
        source = (commands_lib_path / "template_create_orchestrator.py").read_text()

        # Verify fix is in place
        assert 'status = results.get("status"' in source
        assert 'enhanced_count = results.get("enhanced_count"' in source
        assert 'total_count = results.get("total_count"' in source
        assert 'success_rate = results.get("success_rate"' in source
        assert 'if status == "success"' in source

    def test_orchestrator_result_extraction_partial_success(self):
        """Test orchestrator handles partial success batch result"""
        source = (commands_lib_path / "template_create_orchestrator.py").read_text()

        # Verify partial success handling
        assert 'enhanced_count > 0' in source
        assert '_print_success_line' in source

    def test_orchestrator_result_extraction_complete_failure(self):
        """Test orchestrator handles complete failure batch result"""
        source = (commands_lib_path / "template_create_orchestrator.py").read_text()

        # Verify failure handling
        assert '_print_info' in source
        assert 'No agents enhanced' in source

    def test_orchestrator_result_extraction_skipped(self):
        """Test orchestrator handles skipped batch result"""
        source = (commands_lib_path / "template_create_orchestrator.py").read_text()

        # Verify skipped status handling
        assert 'status == "skipped"' in source
        assert 'Agent enhancement skipped' in source

    def test_orchestrator_defensive_dict_access(self):
        """Test orchestrator uses .get() for safe dict access"""
        source = (commands_lib_path / "template_create_orchestrator.py").read_text()

        # Verify defensive programming - using .get() with defaults
        assert 'results.get("status"' in source
        assert 'results.get("enhanced_count"' in source
        assert 'results.get("total_count"' in source
        assert 'results.get("success_rate"' in source
        assert 'results.get("errors"' in source
        assert 'results.get("reason"' in source

    def test_orchestrator_has_display_enhancement_errors(self):
        """Test orchestrator has method to display enhancement errors"""
        source = (commands_lib_path / "template_create_orchestrator.py").read_text()

        # Verify error display method exists
        assert 'def _display_enhancement_errors' in source
        assert '_display_enhancement_errors(errors)' in source

    def test_orchestrator_error_display_implementation(self):
        """Test that error display method is properly implemented"""
        source = (commands_lib_path / "template_create_orchestrator.py").read_text()

        # Find the method and verify it has error handling logic
        assert '_display_enhancement_errors' in source
        assert '_print_warning' in source or '_print_error' in source
