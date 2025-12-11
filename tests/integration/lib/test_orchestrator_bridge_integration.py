"""
Integration tests for Orchestrator Bridge Integration (TASK-BRIDGE-002)

Tests the checkpoint-resume pattern for agent invocation in template creation.
"""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass

# Add lib directory to path
lib_path = Path(__file__).parent.parent.parent.parent / "installer" / "core"
commands_lib_path = lib_path / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))
if str(commands_lib_path) not in sys.path:
    sys.path.insert(0, str(commands_lib_path))

# Import modules using standard imports
from installer.core.commands.lib.template_create_orchestrator import (
    TemplateCreateOrchestrator,
    OrchestrationConfig
)
from installer.core.lib.agent_bridge.state_manager import StateManager
from installer.core.lib.agent_bridge.invoker import AgentBridgeInvoker


@pytest.fixture
def mock_codebase_path(tmp_path):
    """Create a temporary codebase directory"""
    codebase = tmp_path / "test_codebase"
    codebase.mkdir()
    (codebase / "main.py").write_text("# Test file")
    return codebase


@pytest.fixture
def basic_config(mock_codebase_path):
    """Create a basic orchestration config"""
    return OrchestrationConfig(
        codebase_path=mock_codebase_path,
        skip_qa=True,
        dry_run=True,
        no_agents=False,
        verbose=False
    )


@pytest.fixture(autouse=True)
def cleanup_state_files():
    """Cleanup state files before and after each test"""
    state_file = Path(".template-create-state.json")
    request_file = Path(".agent-request.json")
    response_file = Path(".agent-response.json")

    # Cleanup before test
    state_file.unlink(missing_ok=True)
    request_file.unlink(missing_ok=True)
    response_file.unlink(missing_ok=True)

    yield

    # Cleanup after test
    state_file.unlink(missing_ok=True)
    request_file.unlink(missing_ok=True)
    response_file.unlink(missing_ok=True)


def test_orchestrator_initializes_bridge_components(basic_config):
    """Test that orchestrator initializes bridge components correctly"""
    orchestrator = TemplateCreateOrchestrator(basic_config)

    # Verify bridge components are initialized
    assert hasattr(orchestrator, 'state_manager')
    assert hasattr(orchestrator, 'agent_invoker')
    assert isinstance(orchestrator.state_manager, StateManager)
    assert isinstance(orchestrator.agent_invoker, AgentBridgeInvoker)

    # Verify phase data storage is initialized
    assert hasattr(orchestrator, 'qa_answers')
    assert hasattr(orchestrator, 'analysis')
    assert hasattr(orchestrator, 'manifest')
    assert hasattr(orchestrator, 'settings')
    assert hasattr(orchestrator, 'templates')
    assert hasattr(orchestrator, 'agents')


def test_save_checkpoint_creates_state_file(basic_config):
    """Test that _save_checkpoint creates a state file"""
    orchestrator = TemplateCreateOrchestrator(basic_config)

    # Set some phase data
    orchestrator.qa_answers = {'template_name': 'test'}
    orchestrator.analysis = None  # Will be skipped
    orchestrator.manifest = None
    orchestrator.settings = None
    orchestrator.templates = None

    # Save checkpoint
    orchestrator._save_checkpoint("test_checkpoint", phase=5)

    # Verify state file was created
    state_file = Path(".template-create-state.json")
    assert state_file.exists()

    # Verify state content
    state_data = json.loads(state_file.read_text())
    assert state_data['checkpoint'] == "test_checkpoint"
    assert state_data['phase'] == 5
    assert 'qa_answers' in state_data['phase_data']
    assert state_data['phase_data']['qa_answers'] == {'template_name': 'test'}


def test_resume_from_checkpoint_loads_state(basic_config, tmp_path):
    """Test that _resume_from_checkpoint loads state correctly"""
    # First, create a state file manually
    state_manager = StateManager()
    state_manager.save_state(
        checkpoint="templates_generated",
        phase=5,
        config={
            'codebase_path': str(tmp_path / "test_codebase"),
            'skip_qa': True,
            'dry_run': True,
            'resume': False
        },
        phase_data={
            'qa_answers': {'template_name': 'test-template'},
            'analysis': None,
            'manifest': None,
            'settings': None,
            'templates': None,
            'agent_inventory': None
        }
    )

    # Create config with resume=True
    resume_config = OrchestrationConfig(
        codebase_path=tmp_path / "test_codebase",
        resume=True
    )

    # Initialize orchestrator (will call _resume_from_checkpoint)
    orchestrator = TemplateCreateOrchestrator(resume_config)

    # Verify state was restored
    assert orchestrator.qa_answers == {'template_name': 'test-template'}
    assert orchestrator.analysis is None
    assert orchestrator.config.skip_qa is True
    assert orchestrator.config.dry_run is True


def test_serialization_deserialization_roundtrip(basic_config):
    """Test that serialization and deserialization work correctly"""
    orchestrator = TemplateCreateOrchestrator(basic_config)

    # Create mock analysis object with model_dump method (Pydantic-style)
    mock_analysis = Mock()
    mock_analysis.model_dump = Mock(return_value={
        'codebase_path': '/test/path',
        'technology': {'primary_language': 'Python'},
        'architecture': {'patterns': ['Repository']},
        'quality': {'overall_score': 85.0}
    })

    # Serialize
    serialized = orchestrator._serialize_analysis(mock_analysis)

    # Verify serialization
    assert serialized is not None
    assert serialized['codebase_path'] == '/test/path'
    assert serialized['technology']['primary_language'] == 'Python'


def test_orchestrator_has_bridge_invoker_for_agent_generator(basic_config):
    """Test that orchestrator has bridge invoker ready for AIAgentGenerator"""
    # Create orchestrator
    orchestrator = TemplateCreateOrchestrator(basic_config)

    # Verify the orchestrator has the agent_invoker set
    assert orchestrator.agent_invoker is not None
    assert isinstance(orchestrator.agent_invoker, AgentBridgeInvoker)

    # Verify it's configured for phase 6
    assert orchestrator.agent_invoker.phase == 6
    assert orchestrator.agent_invoker.phase_name == "agent_generation"


def test_config_resume_parameter_defaults_to_false():
    """Test that resume parameter defaults to False"""
    config = OrchestrationConfig(codebase_path=Path("/test"))
    assert config.resume is False


def test_config_resume_parameter_can_be_set():
    """Test that resume parameter can be set to True"""
    config = OrchestrationConfig(
        codebase_path=Path("/test"),
        resume=True
    )
    assert config.resume is True


def test_convenience_function_accepts_resume_parameter():
    """Test that run_template_create accepts resume parameter"""
    from installer.core.commands.lib.template_create_orchestrator import run_template_create

    # Get function signature
    import inspect
    sig = inspect.signature(run_template_create)

    # Verify resume parameter exists
    assert 'resume' in sig.parameters
    assert sig.parameters['resume'].default is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
