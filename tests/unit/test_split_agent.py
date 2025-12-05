"""
Unit tests for scripts/split-agent.py (TASK-PD-008)

Tests the AgentSplitter class and its methods for splitting agent markdown files
into core and extended files for progressive disclosure.
"""

import pytest
import sys
from pathlib import Path

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))

from split_agent import (
    AgentSplitter,
    SplitResult,
    find_agents
)


class TestAgentSplitter:
    """Test AgentSplitter class"""

    def test_parse_sections_with_frontmatter(self):
        """Test parsing markdown with frontmatter"""
        content = """---
id: test-agent
name: Test Agent
---

# Test Agent

## Quick Start

Some quick start content.

## Examples

Example content here.
"""
        splitter = AgentSplitter(dry_run=True)
        sections = splitter._parse_sections(content)

        assert len(sections) == 4
        assert sections[0]['title'] == 'frontmatter'
        assert sections[1]['title'] == 'Test Agent'
        assert sections[2]['title'] == 'Quick Start'
        assert sections[3]['title'] == 'Examples'

    def test_parse_sections_without_frontmatter(self):
        """Test parsing markdown without frontmatter"""
        content = """# Test Agent

## Capabilities

Some capabilities.

## Best Practices

Best practices content.
"""
        splitter = AgentSplitter(dry_run=True)
        sections = splitter._parse_sections(content)

        assert len(sections) == 3
        assert sections[0]['title'] == 'Test Agent'
        assert sections[1]['title'] == 'Capabilities'
        assert sections[2]['title'] == 'Best Practices'

    def test_is_core_section_frontmatter(self):
        """Test that frontmatter is identified as core"""
        splitter = AgentSplitter(dry_run=True)
        section = {'title': 'frontmatter', 'content': '---\ntest\n---', 'level': 0}

        assert splitter._is_core_section(section) is True

    def test_is_core_section_quick_start(self):
        """Test that Quick Start is identified as core"""
        splitter = AgentSplitter(dry_run=True)
        section = {'title': 'Quick Start', 'content': 'Quick start content', 'level': 2}

        assert splitter._is_core_section(section) is True

    def test_is_core_section_examples(self):
        """Test that Examples is identified as extended"""
        splitter = AgentSplitter(dry_run=True)
        section = {'title': 'Examples', 'content': 'Example content', 'level': 2}

        assert splitter._is_core_section(section) is False

    def test_is_core_section_best_practices(self):
        """Test that Best Practices is identified as extended"""
        splitter = AgentSplitter(dry_run=True)
        section = {'title': 'Best Practices', 'content': 'Best practices content', 'level': 2}

        assert splitter._is_core_section(section) is False

    def test_categorize_sections(self):
        """Test categorizing sections into core and extended"""
        splitter = AgentSplitter(dry_run=True)
        sections = [
            {'title': 'frontmatter', 'content': '---\ntest\n---', 'level': 0},
            {'title': 'Test Agent', 'content': '# Test Agent', 'level': 1},
            {'title': 'Quick Start', 'content': '## Quick Start', 'level': 2},
            {'title': 'Examples', 'content': '## Examples', 'level': 2},
            {'title': 'Capabilities', 'content': '## Capabilities', 'level': 2},
            {'title': 'Best Practices', 'content': '## Best Practices', 'level': 2},
        ]

        core, extended = splitter._categorize_sections(sections, agent_name='test-agent')

        core_titles = [s['title'] for s in core]
        extended_titles = [s['title'] for s in extended]

        assert 'frontmatter' in core_titles
        assert 'Quick Start' in core_titles
        assert 'Capabilities' in core_titles
        assert 'Examples' in extended_titles
        assert 'Best Practices' in extended_titles

    def test_agent_specific_overrides(self):
        """Test agent-specific overrides for categorization (TASK-PD-009)"""
        splitter = AgentSplitter(dry_run=True)

        # Test task-manager overrides
        task_manager_sections = [
            {'title': 'Phase 2.5', 'content': '## Phase 2.5', 'level': 2},
            {'title': 'Quality Gates', 'content': '## Quality Gates', 'level': 2},
            {'title': 'Detailed Workflow', 'content': '## Detailed Workflow', 'level': 2},
        ]

        core, extended = splitter._categorize_sections(task_manager_sections, agent_name='task-manager')

        core_titles = [s['title'] for s in core]
        extended_titles = [s['title'] for s in extended]

        # Phase 2.5 and Quality Gates should be in core (override)
        assert 'Phase 2.5' in core_titles
        assert 'Quality Gates' in core_titles
        # Detailed Workflow should be in extended (override)
        assert 'Detailed Workflow' in extended_titles

        # Test architectural-reviewer overrides
        arch_reviewer_sections = [
            {'title': 'SOLID Principles', 'content': '## SOLID Principles', 'level': 2},
            {'title': 'SOLID Examples', 'content': '## SOLID Examples', 'level': 2},
        ]

        core, extended = splitter._categorize_sections(arch_reviewer_sections, agent_name='architectural-reviewer')

        core_titles = [s['title'] for s in core]
        extended_titles = [s['title'] for s in extended]

        # SOLID Principles should be in core (override)
        assert 'SOLID Principles' in core_titles
        # SOLID Examples should be in extended (override)
        assert 'SOLID Examples' in extended_titles

    def test_generate_loading_instruction(self):
        """Test generating loading instruction"""
        splitter = AgentSplitter(dry_run=True)
        instruction = splitter._generate_loading_instruction('test-agent-ext.md')

        assert 'Extended Documentation' in instruction
        assert 'test-agent-ext.md' in instruction
        assert '```bash' in instruction
        assert 'cat test-agent-ext.md' in instruction

    def test_build_core_content(self):
        """Test building core content with loading instructions"""
        splitter = AgentSplitter(dry_run=True)
        sections = [
            {'title': 'frontmatter', 'content': '---\nid: test\n---', 'level': 0},
            {'title': 'Test Agent', 'content': '# Test Agent', 'level': 1},
            {'title': 'Quick Start', 'content': '## Quick Start\n\nQuick start content.', 'level': 2},
        ]
        agent_path = Path('test-agent.md')

        core = splitter._build_core_content(sections, agent_path)

        assert '---\nid: test\n---' in core
        assert '# Test Agent' in core
        assert '## Quick Start' in core
        assert 'Extended Documentation' in core
        assert 'test-agent-ext.md' in core

    def test_build_extended_content(self):
        """Test building extended content with header"""
        splitter = AgentSplitter(dry_run=True)
        sections = [
            {'title': 'Examples', 'content': '## Examples\n\nExample content.', 'level': 2},
            {'title': 'Best Practices', 'content': '## Best Practices\n\nBest practices content.', 'level': 2},
        ]
        agent_path = Path('test-agent.md')

        extended = splitter._build_extended_content(sections, agent_path)

        assert '# test-agent - Extended Documentation' in extended
        assert 'Load this file when' in extended
        assert '## Examples' in extended
        assert '## Best Practices' in extended

    def test_split_result_success(self):
        """Test SplitResult success property"""
        result = SplitResult(
            agent_path=Path('test.md'),
            core_content='core',
            extended_content='extended',
            core_size=100,
            extended_size=200,
            original_size=300,
            reduction_percent=66.67,
            sections_moved=['Examples', 'Best Practices']
        )

        assert result.success is True

    def test_split_result_no_reduction(self):
        """Test SplitResult with no reduction"""
        result = SplitResult(
            agent_path=Path('test.md'),
            core_content='all content',
            extended_content='',
            core_size=300,
            extended_size=0,
            original_size=300,
            reduction_percent=0.0,
            sections_moved=[]
        )

        assert result.success is False


class TestFindAgents:
    """Test find_agents function"""

    def test_find_agents_all_global(self):
        """Test finding all global agents"""
        agents = find_agents('all-global')

        assert len(agents) > 0
        assert all(a.suffix == '.md' for a in agents)
        assert all('global/agents' in str(a) for a in agents)

    def test_find_agents_template_react_typescript(self):
        """Test finding agents in react-typescript template"""
        agents = find_agents('template:react-typescript')

        # May or may not have agents depending on template structure
        assert isinstance(agents, list)
        if agents:
            assert all(a.suffix == '.md' for a in agents)
            assert all('react-typescript/agents' in str(a) for a in agents)

    def test_find_agents_nonexistent_template(self):
        """Test finding agents in nonexistent template"""
        agents = find_agents('template:nonexistent-template-xyz')

        assert agents == []

    def test_find_agents_single_path(self):
        """Test finding single agent by path"""
        # Use a known global agent
        agents = find_agents('installer/global/agents/task-manager.md')

        if agents:  # Only check if file exists
            assert len(agents) == 1
            assert agents[0].name == 'task-manager.md'


class TestAgentSplitterIntegration:
    """Integration tests for AgentSplitter"""

    def test_split_agent_full_workflow_dry_run(self, tmp_path):
        """Test complete split workflow in dry-run mode"""
        # Create test agent file
        agent_path = tmp_path / 'test-agent.md'
        agent_content = """---
id: test-agent
name: Test Agent
priority: 10
---

# Test Agent

Description of the agent.

## Quick Start

Quick start instructions.

## Capabilities

Agent capabilities.

## Examples

Detailed examples here.

## Best Practices

Best practices content.
"""
        agent_path.write_text(agent_content, encoding='utf-8')

        # Split in dry-run mode
        splitter = AgentSplitter(dry_run=True)
        result = splitter.split_agent(agent_path)

        # Verify result (small test files may have negative reduction due to headers)
        assert 'Examples' in result.sections_moved
        assert 'Best Practices' in result.sections_moved
        # For small files, the overhead of headers/instructions may exceed savings
        assert isinstance(result.reduction_percent, float)

        # Verify core content
        assert '---\nid: test-agent' in result.core_content
        assert '## Quick Start' in result.core_content
        assert '## Capabilities' in result.core_content
        assert 'Extended Documentation' in result.core_content
        assert 'test-agent-ext.md' in result.core_content

        # Verify extended content
        assert '# test-agent - Extended Documentation' in result.extended_content
        assert '## Examples' in result.extended_content
        assert '## Best Practices' in result.extended_content

        # Verify files not written in dry-run
        assert agent_path.exists()
        assert not (tmp_path / 'test-agent-ext.md').exists()
        assert not (tmp_path / 'test-agent.md.bak').exists()

    def test_split_agent_with_write(self, tmp_path):
        """Test complete split workflow with file writing"""
        # Create test agent file
        agent_path = tmp_path / 'test-agent.md'
        agent_content = """---
id: test-agent
---

# Test Agent

## Quick Start

Quick start.

## Examples

Examples here.
"""
        agent_path.write_text(agent_content, encoding='utf-8')

        # Split with writing
        splitter = AgentSplitter(dry_run=False)
        result = splitter.split_agent(agent_path)

        # Verify result (small files may have negative reduction due to headers)
        assert 'Examples' in result.sections_moved

        # Verify backup created
        backup_path = tmp_path / 'test-agent.md.bak'
        assert backup_path.exists()
        assert backup_path.read_text(encoding='utf-8') == agent_content

        # Verify core file written
        assert agent_path.exists()
        core_content = agent_path.read_text(encoding='utf-8')
        assert '## Quick Start' in core_content
        assert 'Extended Documentation' in core_content
        assert '## Examples' not in core_content  # Moved to extended

        # Verify extended file written
        ext_path = tmp_path / 'test-agent-ext.md'
        assert ext_path.exists()
        extended_content = ext_path.read_text(encoding='utf-8')
        assert '# test-agent - Extended Documentation' in extended_content
        assert '## Examples' in extended_content

    def test_split_agent_nonexistent_file(self):
        """Test splitting nonexistent file raises error"""
        splitter = AgentSplitter(dry_run=True)

        with pytest.raises(FileNotFoundError):
            splitter.split_agent(Path('/nonexistent/agent.md'))

    def test_split_agent_no_extended_sections(self, tmp_path):
        """Test splitting agent with only core sections"""
        agent_path = tmp_path / 'core-only.md'
        agent_content = """# Core Only Agent

## Quick Start

Quick start content.

## Capabilities

Capabilities content.
"""
        agent_path.write_text(agent_content, encoding='utf-8')

        splitter = AgentSplitter(dry_run=True)
        result = splitter.split_agent(agent_path)

        # Should have no sections moved (small file overhead may result in negative reduction)
        assert len(result.sections_moved) == 0
        assert isinstance(result.reduction_percent, float)
        assert 'Extended Documentation' in result.core_content
        assert '# core-only - Extended Documentation' in result.extended_content
