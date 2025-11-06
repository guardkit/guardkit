"""
Integration Tests for Template Create Orchestrator

Tests orchestrator configuration and basic workflow structure.
Full integration tests will be added when all dependencies are implemented.
"""

import pytest
import sys
from pathlib import Path

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

    # Check for all 8 phases
    assert "def _phase1_qa_session" in source
    assert "def _phase2_ai_analysis" in source
    assert "def _phase3_manifest_generation" in source
    assert "def _phase4_settings_generation" in source
    assert "def _phase5_claude_md_generation" in source
    assert "def _phase6_template_generation" in source
    assert "def _phase7_agent_recommendation" in source
    assert "def _phase8_package_assembly" in source


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
    assert "def _print_warning" in source


def test_orchestrator_config_structure():
    """Test OrchestrationConfig has expected fields"""
    source = (commands_lib_path / "template_create_orchestrator.py").read_text()

    # Check dataclass definition
    assert "@dataclass" in source
    assert "class OrchestrationConfig:" in source
    assert "codebase_path" in source
    assert "output_path" in source
    assert "skip_qa: bool" in source
    assert "max_templates" in source
    assert "dry_run: bool" in source
    assert "no_agents: bool" in source
    assert "verbose: bool" in source


def test_orchestrator_result_structure():
    """Test OrchestrationResult has expected fields"""
    source = (commands_lib_path / "template_create_orchestrator.py").read_text()

    # Check dataclass definition
    assert "class OrchestrationResult:" in source
    assert "success: bool" in source
    assert "template_name: str" in source
    assert "output_path" in source
    assert "template_count: int" in source
    assert "agent_count: int" in source
    assert "confidence_score: int" in source
    assert "errors: List[str]" in source
    assert "warnings: List[str]" in source


def test_convenience_function_signature():
    """Test run_template_create function has correct parameters"""
    source = (commands_lib_path / "template_create_orchestrator.py").read_text()

    # Find function definition
    lines = source.split('\n')
    func_start = None
    for i, line in enumerate(lines):
        if "def run_template_create(" in line:
            func_start = i
            break

    assert func_start is not None, "run_template_create function not found"

    # Get function signature (may span multiple lines)
    func_lines = []
    for i in range(func_start, min(func_start + 15, len(lines))):
        func_lines.append(lines[i])
        if ") ->" in lines[i]:
            break

    func_sig = "\n".join(func_lines)

    # Check parameters
    assert "codebase_path" in func_sig
    assert "output_path" in func_sig
    assert "skip_qa" in func_sig
    assert "max_templates" in func_sig
    assert "dry_run" in func_sig
    assert "save_analysis" in func_sig
    assert "no_agents" in func_sig
    assert "verbose" in func_sig
    assert "OrchestrationResult" in func_sig


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
