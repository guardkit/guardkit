"""
Unit tests for task ID generation in Template Create Orchestrator

Tests for TASK-FIX-9E1A: Fix task ID uniqueness and collision risk
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import Mock, patch

# Add lib directory to path
lib_path = Path(__file__).parent.parent.parent / "installer" / "global"
commands_lib_path = lib_path / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))
if str(commands_lib_path) not in sys.path:
    sys.path.insert(0, str(commands_lib_path))

# Import the orchestrator module directly
def import_module_from_path(module_name, file_path):
    """Import a module directly from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

orchestrator_module = import_module_from_path(
    "template_create_orchestrator",
    commands_lib_path / "template_create_orchestrator.py"
)

TemplateCreateOrchestrator = orchestrator_module.TemplateCreateOrchestrator
OrchestrationConfig = orchestrator_module.OrchestrationConfig


@pytest.fixture
def mock_config():
    """Create a minimal mock configuration for testing."""
    return OrchestrationConfig(
        codebase_path=Path("/tmp/test"),
        output_location='global'
    )


class TestTaskIDGeneration:
    """Tests for _generate_task_id method."""

    def test_task_id_uniqueness_different_agents(self, mock_config):
        """Test that task IDs are unique for different agents."""
        orchestrator = TemplateCreateOrchestrator(mock_config)

        id1 = orchestrator._generate_task_id("repository-pattern-specialist")
        id2 = orchestrator._generate_task_id("repository-domain-specialist")

        assert id1 != id2, "Task IDs should be unique for different agents"
        assert id1.startswith("TASK-REPOSITORY-"), f"ID1 should start with TASK-REPOSITORY-, got {id1}"
        assert id2.startswith("TASK-REPOSITORY-"), f"ID2 should start with TASK-REPOSITORY-, got {id2}"

    def test_task_id_uniqueness_same_agent(self, mock_config):
        """Test that task IDs are unique even for the same agent name."""
        orchestrator = TemplateCreateOrchestrator(mock_config)
        agent_name = "test-agent-specialist"

        id1 = orchestrator._generate_task_id(agent_name)
        id2 = orchestrator._generate_task_id(agent_name)

        assert id1 != id2, "Task IDs should be unique even for same agent name"

    def test_task_id_rapid_generation(self, mock_config):
        """Test uniqueness with rapid ID generation (collision resistance)."""
        orchestrator = TemplateCreateOrchestrator(mock_config)
        agent_name = "test-agent"

        # Generate 1000 IDs rapidly
        ids = [orchestrator._generate_task_id(agent_name) for _ in range(1000)]

        # All IDs should be unique
        unique_ids = set(ids)
        assert len(ids) == len(unique_ids), f"Expected 1000 unique IDs, got {len(unique_ids)}"

    def test_task_id_format(self, mock_config):
        """Test task ID follows expected format."""
        orchestrator = TemplateCreateOrchestrator(mock_config)

        task_id = orchestrator._generate_task_id("my-test-agent-specialist")

        # Should start with TASK-
        assert task_id.startswith("TASK-"), f"Task ID should start with TASK-, got {task_id}"

        # Should have at least 3 parts separated by hyphens
        parts = task_id.split("-")
        assert len(parts) >= 3, f"Task ID should have at least 3 parts, got {len(parts)}: {task_id}"

        # First part should be TASK
        assert parts[0] == "TASK", f"First part should be TASK, got {parts[0]}"

        # Last part should be 8-character UUID hex
        uuid_part = parts[-1]
        assert len(uuid_part) == 8, f"UUID part should be 8 chars, got {len(uuid_part)}: {uuid_part}"
        assert uuid_part.isupper(), f"UUID part should be uppercase, got {uuid_part}"
        assert all(c in "0123456789ABCDEF" for c in uuid_part), \
            f"UUID part should be hex, got {uuid_part}"

    def test_task_id_long_agent_name(self, mock_config):
        """Test handling of very long agent names."""
        orchestrator = TemplateCreateOrchestrator(mock_config)

        long_name = "very-long-agent-name-that-exceeds-fifteen-characters-significantly"
        task_id = orchestrator._generate_task_id(long_name)

        # Should start with TASK-
        assert task_id.startswith("TASK-"), f"Task ID should start with TASK-, got {task_id}"

        # Extract prefix (everything between TASK- and final UUID)
        parts = task_id.split("-")
        # Remove "TASK" at start and UUID at end
        prefix_parts = parts[1:-1]
        prefix = "-".join(prefix_parts)

        # Prefix should be truncated to max 15 chars
        assert len(prefix) <= 15, \
            f"Prefix should be max 15 chars, got {len(prefix)}: {prefix}"

    def test_task_id_short_agent_name(self, mock_config):
        """Test handling of short agent names."""
        orchestrator = TemplateCreateOrchestrator(mock_config)

        short_name = "api"
        task_id = orchestrator._generate_task_id(short_name)

        # Should work fine with short names
        assert task_id.startswith("TASK-API-"), f"Task ID should start with TASK-API-, got {task_id}"

        parts = task_id.split("-")
        uuid_part = parts[-1]
        assert len(uuid_part) == 8, f"UUID part should be 8 chars, got {len(uuid_part)}"

    def test_task_id_collision_probability(self, mock_config):
        """Statistical test for collision resistance."""
        orchestrator = TemplateCreateOrchestrator(mock_config)

        # Generate 10,000 IDs - should have zero collisions
        ids = {orchestrator._generate_task_id("agent") for _ in range(10000)}

        assert len(ids) == 10000, f"Expected 10,000 unique IDs, got {len(ids)}"

    def test_task_id_special_characters_in_name(self, mock_config):
        """Test handling of agent names with hyphens and underscores."""
        orchestrator = TemplateCreateOrchestrator(mock_config)

        # Hyphens should be preserved
        task_id = orchestrator._generate_task_id("domain-api-specialist")
        assert "DOMAIN-API" in task_id, f"Hyphens should be preserved, got {task_id}"

    def test_task_id_uppercase_conversion(self, mock_config):
        """Test that prefix is converted to uppercase."""
        orchestrator = TemplateCreateOrchestrator(mock_config)

        task_id = orchestrator._generate_task_id("lowercase-agent")

        # Everything before the UUID should be uppercase
        parts = task_id.split("-")
        for part in parts[:-1]:  # All parts except UUID
            assert part.isupper(), f"Part {part} should be uppercase in {task_id}"

    def test_task_id_examples_from_spec(self, mock_config):
        """Test examples from the task specification."""
        orchestrator = TemplateCreateOrchestrator(mock_config)

        # Test repository-pattern-specialist
        id1 = orchestrator._generate_task_id("repository-pattern-specialist")
        assert id1.startswith("TASK-REPOSITORY-"), \
            f"Should start with TASK-REPOSITORY-, got {id1}"

        # Test repository-domain-specialist
        id2 = orchestrator._generate_task_id("repository-domain-specialist")
        assert id2.startswith("TASK-REPOSITORY-"), \
            f"Should start with TASK-REPOSITORY-, got {id2}"

        # IDs should be different despite similar prefixes
        assert id1 != id2, "IDs should be different for similar agent names"

        # Test realm-thread-safety-specialist
        id3 = orchestrator._generate_task_id("realm-thread-safety-specialist")
        assert id3.startswith("TASK-REALM-THREAD-"), \
            f"Should start with TASK-REALM-THREAD-, got {id3}"

    def test_task_id_consistency_with_multiple_instances(self, mock_config):
        """Test that different orchestrator instances generate unique IDs."""
        config1 = OrchestrationConfig(codebase_path=Path("/tmp/test1"), output_location='global')
        config2 = OrchestrationConfig(codebase_path=Path("/tmp/test2"), output_location='global')
        orchestrator1 = TemplateCreateOrchestrator(config1)
        orchestrator2 = TemplateCreateOrchestrator(config2)

        agent_name = "test-agent"

        id1 = orchestrator1._generate_task_id(agent_name)
        id2 = orchestrator2._generate_task_id(agent_name)

        # IDs should be different even from different instances
        assert id1 != id2, "IDs from different instances should be unique"

    def test_task_id_length_reasonable(self, mock_config):
        """Test that generated IDs have reasonable length."""
        orchestrator = TemplateCreateOrchestrator(mock_config)

        task_id = orchestrator._generate_task_id("domain-api-specialist")

        # ID should be reasonable length (not too long)
        # Format: TASK-{up to 15 chars}-{8 chars UUID}
        # Minimum: TASK-A-12345678 = 16 chars
        # Maximum: TASK-123456789012345-12345678 = 34 chars
        assert 16 <= len(task_id) <= 40, \
            f"Task ID length should be reasonable, got {len(task_id)}: {task_id}"

    def test_task_id_no_timestamp_dependency(self, mock_config):
        """Test that IDs don't depend on timestamps (no collision in same second)."""
        orchestrator = TemplateCreateOrchestrator(mock_config)

        # Generate multiple IDs in rapid succession (same second)
        ids = []
        for i in range(100):
            ids.append(orchestrator._generate_task_id("agent"))

        # All should be unique
        unique_ids = set(ids)
        assert len(ids) == len(unique_ids), \
            "IDs generated in same second should all be unique"


class TestTaskIDGenerationIntegration:
    """Integration tests for task ID generation in context."""

    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.write_text')
    def test_agent_tasks_use_unique_ids(self, mock_write, mock_mkdir, mock_config):
        """Test that _create_agent_tasks_simplified uses unique IDs."""
        orchestrator = TemplateCreateOrchestrator(mock_config)

        # Create mock agent files with similar names
        from pathlib import Path
        agent_files = [
            Path("repository-pattern-specialist.md"),
            Path("repository-domain-specialist.md"),
            Path("repository-cache-specialist.md")
        ]

        # Mock template directory
        template_dir = Path("test-template")

        # Call the method
        with patch.object(Path, 'exists', return_value=True):
            task_ids = orchestrator._create_agent_tasks_simplified(agent_files, template_dir)

        # Should have 3 unique task IDs
        assert len(task_ids) == 3, f"Should create 3 tasks, got {len(task_ids)}"
        assert len(set(task_ids)) == 3, f"All task IDs should be unique, got {task_ids}"

        # All should start with TASK-REPOSITORY-
        for task_id in task_ids:
            assert task_id.startswith("TASK-REPOSITORY-"), \
                f"Task ID should start with TASK-REPOSITORY-, got {task_id}"

        # All should be different
        assert task_ids[0] != task_ids[1], "First two IDs should differ"
        assert task_ids[0] != task_ids[2], "First and third IDs should differ"
        assert task_ids[1] != task_ids[2], "Second and third IDs should differ"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
