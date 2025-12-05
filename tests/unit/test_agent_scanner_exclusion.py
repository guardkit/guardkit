"""
Unit Tests for Agent Scanner Extended File Exclusion

TASK-PD-004: Tests for -ext.md file exclusion from agent discovery
"""

import pytest
from pathlib import Path
import sys
import os

# Add lib directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../installer/global/lib/agent_scanner'))

from agent_scanner import is_extended_file, MultiSourceAgentScanner


class TestIsExtendedFile:
    """Test is_extended_file() helper function."""

    def test_extended_file_detected(self):
        """Test that -ext.md files are correctly identified."""
        assert is_extended_file(Path("task-manager-ext.md")) is True
        assert is_extended_file(Path("code-reviewer-ext.md")) is True
        assert is_extended_file(Path("agent-ext.md")) is True
        assert is_extended_file(Path("my-very-long-agent-name-ext.md")) is True

    def test_core_file_not_extended(self):
        """Test that regular .md files are not identified as extended."""
        assert is_extended_file(Path("task-manager.md")) is False
        assert is_extended_file(Path("code-reviewer.md")) is False
        assert is_extended_file(Path("agent.md")) is False

    def test_ext_not_at_end_of_stem(self):
        """Test that 'ext' not at end of stem is not identified as extended."""
        assert is_extended_file(Path("my-ext-agent.md")) is False
        assert is_extended_file(Path("external-service.md")) is False
        assert is_extended_file(Path("extension-handler.md")) is False

    def test_no_extension(self):
        """Test files without .md extension."""
        assert is_extended_file(Path("task-manager-ext")) is True  # stem still ends with -ext
        assert is_extended_file(Path("task-manager-ext.txt")) is True  # stem still ends with -ext
        assert is_extended_file(Path("task-manager")) is False

    def test_complex_names(self):
        """Test complex agent names with hyphens."""
        assert is_extended_file(Path("react-state-specialist-ext.md")) is True
        assert is_extended_file(Path("fastapi-database-specialist-ext.md")) is True
        assert is_extended_file(Path("react-state-specialist.md")) is False
        assert is_extended_file(Path("fastapi-database-specialist.md")) is False


class TestAgentScannerExclusion:
    """Test MultiSourceAgentScanner exclusion logic."""

    def test_extended_files_excluded_from_scan(self, tmp_path):
        """Test that -ext.md files are excluded from agent discovery."""
        # Create test agent directory
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        # Create core agent file
        core_agent = agent_dir / "task-manager.md"
        core_agent.write_text("""---
name: task-manager
description: Task management agent
tools: []
tags: [orchestration]
---

# Task Manager Agent

This is the core agent file.
""")

        # Create extended agent file
        ext_agent = agent_dir / "task-manager-ext.md"
        ext_agent.write_text("""# Extended Documentation

This is extended content that should not appear in discovery.
""")

        # Create second core agent
        core_agent2 = agent_dir / "code-reviewer.md"
        core_agent2.write_text("""---
name: code-reviewer
description: Code review agent
tools: []
tags: [review]
---

# Code Reviewer Agent

This is another core agent file.
""")

        # Create second extended file
        ext_agent2 = agent_dir / "code-reviewer-ext.md"
        ext_agent2.write_text("""# Extended Documentation

More extended content.
""")

        # Scan directory
        scanner = MultiSourceAgentScanner(
            custom_path=agent_dir,
            template_path=None,
            global_path=tmp_path / "nonexistent"  # Don't scan global
        )

        # Manually call _scan_directory to test the method directly
        agents = scanner._scan_directory(agent_dir, source="custom", priority=3)

        # Verify only core agents are discovered
        assert len(agents) == 2
        agent_names = [a.name for a in agents]
        assert "task-manager" in agent_names
        assert "code-reviewer" in agent_names

        # Verify extended files are NOT discovered
        assert not any("-ext" in a.name for a in agents)
        assert not any("task-manager-ext" in str(a.source_path) for a in agents)
        assert not any("code-reviewer-ext" in str(a.source_path) for a in agents)

    def test_scan_with_only_extended_files(self, tmp_path):
        """Test scanning directory with only extended files returns empty list."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        # Create only extended files
        (agent_dir / "agent1-ext.md").write_text("# Extended content")
        (agent_dir / "agent2-ext.md").write_text("# More extended content")

        scanner = MultiSourceAgentScanner(
            custom_path=agent_dir,
            template_path=None,
            global_path=tmp_path / "nonexistent"
        )

        agents = scanner._scan_directory(agent_dir, source="custom", priority=3)

        # Should return empty list
        assert len(agents) == 0

    def test_scan_with_no_extended_files(self, tmp_path):
        """Test scanning directory with no extended files works normally."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        # Create only core files
        (agent_dir / "agent1.md").write_text("""---
name: agent1
description: First agent
---
# Agent 1
""")
        (agent_dir / "agent2.md").write_text("""---
name: agent2
description: Second agent
---
# Agent 2
""")

        scanner = MultiSourceAgentScanner(
            custom_path=agent_dir,
            template_path=None,
            global_path=tmp_path / "nonexistent"
        )

        agents = scanner._scan_directory(agent_dir, source="custom", priority=3)

        # Should return both agents
        assert len(agents) == 2
        assert "agent1" in [a.name for a in agents]
        assert "agent2" in [a.name for a in agents]

    def test_mixed_directory_with_various_files(self, tmp_path):
        """Test directory with mix of core, extended, and other files."""
        agent_dir = tmp_path / "agents"
        agent_dir.mkdir()

        # Core agent files
        (agent_dir / "agent1.md").write_text("""---
name: agent1
description: Agent 1
---
# Agent 1
""")
        (agent_dir / "agent2.md").write_text("""---
name: agent2
description: Agent 2
---
# Agent 2
""")

        # Extended files (should be excluded)
        (agent_dir / "agent1-ext.md").write_text("# Extended for agent1")
        (agent_dir / "agent2-ext.md").write_text("# Extended for agent2")

        # Files with 'ext' in name but not at end (should be included)
        (agent_dir / "external-service.md").write_text("""---
name: external-service
description: External service agent
---
# External Service
""")

        # Non-.md files (should be ignored by glob)
        (agent_dir / "readme.txt").write_text("Not an agent")

        scanner = MultiSourceAgentScanner(
            custom_path=agent_dir,
            template_path=None,
            global_path=tmp_path / "nonexistent"
        )

        agents = scanner._scan_directory(agent_dir, source="custom", priority=3)

        # Should return 3 agents: agent1, agent2, external-service
        assert len(agents) == 3
        agent_names = [a.name for a in agents]
        assert "agent1" in agent_names
        assert "agent2" in agent_names
        assert "external-service" in agent_names

        # Extended files should not be in results
        assert not any("-ext" in a.name for a in agents)
