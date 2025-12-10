"""
Unit tests for Multi-Source Agent Scanner

Tests for scanning agent definitions from multiple sources
(custom, template, global) with proper priority ordering.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
import sys

# Add lib directory to path for imports (avoiding 'global' keyword issue)
lib_path = Path(__file__).parent.parent.parent / "installer" / "core" / "lib"
sys.path.insert(0, str(lib_path))

from agent_scanner import (
    AgentDefinition,
    AgentInventory,
    MultiSourceAgentScanner
)


@pytest.fixture
def temp_dirs():
    """Create temporary directories for testing"""
    temp_root = Path(tempfile.mkdtemp())
    custom_dir = temp_root / "custom"
    template_dir = temp_root / "template"
    global_dir = temp_root / "global"

    custom_dir.mkdir(parents=True)
    template_dir.mkdir(parents=True)
    global_dir.mkdir(parents=True)

    yield {
        'root': temp_root,
        'custom': custom_dir,
        'template': template_dir,
        'global': global_dir
    }

    # Cleanup
    shutil.rmtree(temp_root)


@pytest.fixture
def sample_agent_content():
    """Sample agent markdown content"""
    return """---
name: test-agent
description: Test agent for unit testing
tools: [Read, Write, Grep]
tags: [testing, sample]
---

# Test Agent

This is a test agent used for unit testing the scanner.

## Capabilities
- Read files
- Write files
- Search code
"""


def create_agent_file(directory: Path, filename: str, content: str):
    """Helper to create agent file"""
    file_path = directory / filename
    file_path.write_text(content, encoding='utf-8')
    return file_path


class TestAgentDefinition:
    """Test AgentDefinition data class"""

    def test_agent_definition_creation(self):
        """Test creating an AgentDefinition"""
        agent = AgentDefinition(
            name="test-agent",
            description="Test description",
            tools=["Read", "Write"],
            tags=["test"],
            source="custom",
            source_path=Path("/tmp/test.md"),
            priority=3,
            full_definition="# Test"
        )

        assert agent.name == "test-agent"
        assert agent.description == "Test description"
        assert agent.tools == ["Read", "Write"]
        assert agent.tags == ["test"]
        assert agent.source == "custom"
        assert agent.priority == 3


class TestAgentInventory:
    """Test AgentInventory functionality"""

    def test_all_agents_priority_order(self):
        """Test that all_agents returns agents in priority order"""
        custom_agent = AgentDefinition(
            name="custom-1", description="Custom", tools=[], tags=[],
            source="custom", source_path=Path("/custom"), priority=3,
            full_definition=""
        )
        template_agent = AgentDefinition(
            name="template-1", description="Template", tools=[], tags=[],
            source="template", source_path=Path("/template"), priority=2,
            full_definition=""
        )
        global_agent = AgentDefinition(
            name="global-1", description="Global", tools=[], tags=[],
            source="global", source_path=Path("/global"), priority=1,
            full_definition=""
        )

        inventory = AgentInventory(
            custom_agents=[custom_agent],
            template_agents=[template_agent],
            global_agents=[global_agent]
        )

        all_agents = inventory.all_agents()
        assert len(all_agents) == 3
        assert all_agents[0].source == "custom"
        assert all_agents[1].source == "template"
        assert all_agents[2].source == "global"

    def test_find_by_name_returns_highest_priority(self):
        """Test that find_by_name returns highest priority match"""
        custom_agent = AgentDefinition(
            name="duplicate-agent", description="Custom version", tools=[], tags=[],
            source="custom", source_path=Path("/custom"), priority=3,
            full_definition=""
        )
        global_agent = AgentDefinition(
            name="duplicate-agent", description="Global version", tools=[], tags=[],
            source="global", source_path=Path("/global"), priority=1,
            full_definition=""
        )

        inventory = AgentInventory(
            custom_agents=[custom_agent],
            template_agents=[],
            global_agents=[global_agent]
        )

        found = inventory.find_by_name("duplicate-agent")
        assert found is not None
        assert found.source == "custom"
        assert found.priority == 3

    def test_find_by_name_not_found(self):
        """Test find_by_name when agent doesn't exist"""
        inventory = AgentInventory(
            custom_agents=[],
            template_agents=[],
            global_agents=[]
        )

        found = inventory.find_by_name("nonexistent-agent")
        assert found is None

    def test_has_agent(self):
        """Test has_agent method"""
        agent = AgentDefinition(
            name="test-agent", description="Test", tools=[], tags=[],
            source="custom", source_path=Path("/custom"), priority=3,
            full_definition=""
        )

        inventory = AgentInventory(
            custom_agents=[agent],
            template_agents=[],
            global_agents=[]
        )

        assert inventory.has_agent("test-agent") is True
        assert inventory.has_agent("nonexistent-agent") is False

    def test_get_by_source(self):
        """Test getting agents by source"""
        custom_agent = AgentDefinition(
            name="custom-1", description="Custom", tools=[], tags=[],
            source="custom", source_path=Path("/custom"), priority=3,
            full_definition=""
        )
        global_agent = AgentDefinition(
            name="global-1", description="Global", tools=[], tags=[],
            source="global", source_path=Path("/global"), priority=1,
            full_definition=""
        )

        inventory = AgentInventory(
            custom_agents=[custom_agent],
            template_agents=[],
            global_agents=[global_agent]
        )

        custom_agents = inventory.get_by_source("custom")
        assert len(custom_agents) == 1
        assert custom_agents[0].name == "custom-1"

        global_agents = inventory.get_by_source("global")
        assert len(global_agents) == 1
        assert global_agents[0].name == "global-1"


class TestMultiSourceAgentScanner:
    """Test MultiSourceAgentScanner functionality"""

    def test_scan_custom_agents(self, temp_dirs, sample_agent_content):
        """Test scanning user's custom agents"""
        custom_dir = temp_dirs['custom']

        # Create test agent files
        create_agent_file(custom_dir, "agent-1.md", sample_agent_content)
        create_agent_file(custom_dir, "agent-2.md", sample_agent_content.replace(
            "name: test-agent", "name: test-agent-2"
        ))

        scanner = MultiSourceAgentScanner(
            custom_path=custom_dir,
            template_path=None,
            global_path=temp_dirs['global']
        )

        inventory = scanner.scan()

        assert len(inventory.custom_agents) == 2
        assert all(agent.source == "custom" for agent in inventory.custom_agents)
        assert all(agent.priority == 3 for agent in inventory.custom_agents)

    def test_scan_template_agents(self, temp_dirs, sample_agent_content):
        """Test scanning template agents"""
        template_dir = temp_dirs['template']

        create_agent_file(template_dir, "template-agent.md", sample_agent_content.replace(
            "name: test-agent", "name: template-agent"
        ))

        scanner = MultiSourceAgentScanner(
            custom_path=temp_dirs['custom'],
            template_path=template_dir,
            global_path=temp_dirs['global']
        )

        inventory = scanner.scan()

        assert len(inventory.template_agents) == 1
        assert inventory.template_agents[0].source == "template"
        assert inventory.template_agents[0].priority == 2

    def test_scan_global_agents(self, temp_dirs, sample_agent_content):
        """Test scanning global built-in agents"""
        global_dir = temp_dirs['global']

        create_agent_file(global_dir, "global-agent.md", sample_agent_content.replace(
            "name: test-agent", "name: global-agent"
        ))

        scanner = MultiSourceAgentScanner(
            custom_path=temp_dirs['custom'],
            template_path=None,
            global_path=global_dir
        )

        inventory = scanner.scan()

        assert len(inventory.global_agents) == 1
        assert inventory.global_agents[0].source == "global"
        assert inventory.global_agents[0].priority == 1

    def test_priority_order_with_duplicates(self, temp_dirs, sample_agent_content):
        """Test that custom agents take precedence over duplicates"""
        # Create duplicate agent in custom and global
        create_agent_file(
            temp_dirs['custom'],
            "react-specialist.md",
            sample_agent_content.replace("name: test-agent", "name: react-specialist")
        )
        create_agent_file(
            temp_dirs['global'],
            "react-specialist.md",
            sample_agent_content.replace("name: test-agent", "name: react-specialist")
        )

        scanner = MultiSourceAgentScanner(
            custom_path=temp_dirs['custom'],
            template_path=None,
            global_path=temp_dirs['global']
        )

        inventory = scanner.scan()

        # Find the agent (should return custom version)
        agent = inventory.find_by_name("react-specialist")

        assert agent is not None
        assert agent.source == "custom"
        assert agent.priority == 3

    def test_missing_directories_graceful(self, temp_dirs):
        """Test graceful handling of missing directories"""
        scanner = MultiSourceAgentScanner(
            custom_path=Path("/nonexistent/custom"),
            template_path=Path("/nonexistent/template"),
            global_path=Path("/nonexistent/global")
        )

        # Should not crash
        inventory = scanner.scan()

        assert len(inventory.all_agents()) == 0
        assert len(inventory.custom_agents) == 0
        assert len(inventory.template_agents) == 0
        assert len(inventory.global_agents) == 0

    def test_invalid_agent_files(self, temp_dirs):
        """Test handling of malformed agent files"""
        custom_dir = temp_dirs['custom']

        # Create files with missing frontmatter
        (custom_dir / "no-frontmatter.md").write_text("# No Frontmatter\nJust content", encoding='utf-8')

        # Create file with missing required fields
        (custom_dir / "missing-description.md").write_text("""---
name: test-agent
---
# Agent without description""", encoding='utf-8')

        scanner = MultiSourceAgentScanner(
            custom_path=custom_dir,
            template_path=None,
            global_path=temp_dirs['global']
        )

        # Should skip invalid files and continue
        inventory = scanner.scan()

        # Should have no valid agents (both files are invalid)
        assert len(inventory.custom_agents) == 0

    def test_parse_agent_file_with_all_fields(self, temp_dirs):
        """Test parsing agent file with all metadata fields"""
        content = """---
name: full-agent
description: Agent with all fields
tools: [Read, Write, Grep, Bash]
tags: [testing, complete, sample]
---

# Full Agent

Complete agent definition with all fields.
"""

        custom_dir = temp_dirs['custom']
        file_path = create_agent_file(custom_dir, "full-agent.md", content)

        scanner = MultiSourceAgentScanner(
            custom_path=custom_dir,
            template_path=None,
            global_path=temp_dirs['global']
        )

        agent = scanner._parse_agent_file(file_path, "custom", 3)

        assert agent is not None
        assert agent.name == "full-agent"
        assert agent.description == "Agent with all fields"
        assert agent.tools == ["Read", "Write", "Grep", "Bash"]
        assert agent.tags == ["testing", "complete", "sample"]
        assert agent.source == "custom"
        assert agent.priority == 3
        assert "# Full Agent" in agent.full_definition

    def test_scan_all_three_sources(self, temp_dirs, sample_agent_content):
        """Test scanning all three sources together"""
        # Create agents in all three sources
        create_agent_file(
            temp_dirs['custom'],
            "custom-agent.md",
            sample_agent_content.replace("name: test-agent", "name: custom-agent")
        )
        create_agent_file(
            temp_dirs['template'],
            "template-agent.md",
            sample_agent_content.replace("name: test-agent", "name: template-agent")
        )
        create_agent_file(
            temp_dirs['global'],
            "global-agent.md",
            sample_agent_content.replace("name: test-agent", "name: global-agent")
        )

        scanner = MultiSourceAgentScanner(
            custom_path=temp_dirs['custom'],
            template_path=temp_dirs['template'],
            global_path=temp_dirs['global']
        )

        inventory = scanner.scan()

        assert len(inventory.custom_agents) == 1
        assert len(inventory.template_agents) == 1
        assert len(inventory.global_agents) == 1
        assert len(inventory.all_agents()) == 3


class TestPerformance:
    """Test performance requirements"""

    def test_scan_100_agents_under_1_second(self, temp_dirs, sample_agent_content):
        """Test that scanning 100 agents takes less than 1 second"""
        import time

        global_dir = temp_dirs['global']

        # Create 100 agent files
        for i in range(100):
            create_agent_file(
                global_dir,
                f"agent-{i:03d}.md",
                sample_agent_content.replace("name: test-agent", f"name: agent-{i:03d}")
            )

        scanner = MultiSourceAgentScanner(
            custom_path=temp_dirs['custom'],
            template_path=None,
            global_path=global_dir
        )

        start_time = time.time()
        inventory = scanner.scan()
        elapsed_time = time.time() - start_time

        assert len(inventory.global_agents) == 100
        assert elapsed_time < 1.0, f"Scanning took {elapsed_time:.2f}s (expected <1s)"


class TestIntegration:
    """Integration tests for scanner"""

    def test_real_world_scenario(self, temp_dirs, sample_agent_content):
        """Test a realistic scenario with duplicates and multiple sources"""
        # Create a realistic scenario:
        # - 2 custom agents (including override of global)
        # - 3 template agents
        # - 10 global agents (including one overridden by custom)

        custom_dir = temp_dirs['custom']
        template_dir = temp_dirs['template']
        global_dir = temp_dirs['global']

        # Custom agents
        create_agent_file(custom_dir, "my-custom-agent.md",
            sample_agent_content.replace("name: test-agent", "name: my-custom-agent"))
        create_agent_file(custom_dir, "react-specialist.md",  # Override global
            sample_agent_content.replace("name: test-agent", "name: react-specialist"))

        # Template agents
        for i in range(3):
            create_agent_file(template_dir, f"template-agent-{i}.md",
                sample_agent_content.replace("name: test-agent", f"name: template-agent-{i}"))

        # Global agents
        for i in range(10):
            create_agent_file(global_dir, f"global-agent-{i}.md",
                sample_agent_content.replace("name: test-agent", f"name: global-agent-{i}"))
        create_agent_file(global_dir, "react-specialist.md",  # Will be overridden by custom
            sample_agent_content.replace("name: test-agent", "name: react-specialist"))

        scanner = MultiSourceAgentScanner(
            custom_path=custom_dir,
            template_path=template_dir,
            global_path=global_dir
        )

        inventory = scanner.scan()

        # Verify counts
        assert len(inventory.custom_agents) == 2
        assert len(inventory.template_agents) == 3
        assert len(inventory.global_agents) == 11

        # Verify priority (custom override)
        react_agent = inventory.find_by_name("react-specialist")
        assert react_agent is not None
        assert react_agent.source == "custom"
        assert react_agent.priority == 3

        # Verify total unique agents (15, not 16, due to duplicate)
        # Actually it's 16 because we store all agents, but find_by_name returns highest priority
        assert len(inventory.all_agents()) == 16
