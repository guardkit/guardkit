"""
Unit tests for agent_enhancer.py module.

Tests the AI-powered agent enhancement system that connects agents
to relevant templates without hard-coded mappings.

TASK-ENHANCE-AGENT-FILES
"""

import json
import pytest
import importlib
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# Use importlib to avoid 'global' keyword issue
_agent_enhancer_module = importlib.import_module('installer.global.lib.template_creation.agent_enhancer')
AgentEnhancer = _agent_enhancer_module.AgentEnhancer
AgentMetadata = _agent_enhancer_module.AgentMetadata
TemplateRelevance = _agent_enhancer_module.TemplateRelevance


class TestAgentEnhancer:
    """Test AgentEnhancer class"""

    @pytest.fixture
    def mock_bridge_invoker(self):
        """Create mock agent bridge invoker"""
        invoker = Mock()
        invoker.invoke = Mock()
        return invoker

    @pytest.fixture
    def enhancer(self, mock_bridge_invoker):
        """Create AgentEnhancer instance"""
        return AgentEnhancer(mock_bridge_invoker)

    @pytest.fixture
    def enhancer_no_bridge(self):
        """Create AgentEnhancer instance without bridge (graceful degradation)"""
        return AgentEnhancer(bridge_invoker=None)

    @pytest.fixture
    def sample_agent_metadata(self):
        """Create sample agent metadata"""
        return AgentMetadata(
            name='repository-pattern-specialist',
            description='Repository pattern with Realm database',
            priority=10,
            technologies=['C#', 'Repository Pattern', 'Realm'],
            file_path=Path('/tmp/test-agent.md')
        )

    @pytest.fixture
    def sample_templates(self):
        """Create sample template paths (absolute paths under /tmp)"""
        return [
            Path('/tmp/templates/other/ConfigurationRepository.cs.template'),
            Path('/tmp/templates/other/DriverRepository.cs.template'),
            Path('/tmp/templates/other/DomainCameraView.cs.template')
        ]

    def test_find_relevant_templates_success(self, enhancer, sample_agent_metadata, sample_templates):
        """Test successful template discovery"""
        # Mock bridge invoker response
        enhancer.template_root = Path('/tmp')
        ai_response = json.dumps({
            "templates": [
                {
                    "path": "templates/other/ConfigurationRepository.cs.template",
                    "relevance": "Demonstrates repository pattern with Realm",
                    "priority": "primary"
                },
                {
                    "path": "templates/other/DriverRepository.cs.template",
                    "relevance": "Shows entity-specific repository implementation",
                    "priority": "primary"
                }
            ]
        })
        enhancer.bridge_invoker.invoke.return_value = ai_response

        # Execute
        result = enhancer.find_relevant_templates(sample_agent_metadata, sample_templates)

        # Verify
        assert len(result) == 2
        assert all(isinstance(t, TemplateRelevance) for t in result)
        assert result[0].path == "templates/other/ConfigurationRepository.cs.template"
        assert result[0].priority == "primary"
        assert result[1].path == "templates/other/DriverRepository.cs.template"

    def test_find_relevant_templates_filters_irrelevant(self, enhancer, sample_agent_metadata, sample_templates):
        """Test that irrelevant templates are not included"""
        enhancer.template_root = Path('/tmp')
        ai_response = json.dumps({
            "templates": [
                {
                    "path": "templates/other/ConfigurationRepository.cs.template",
                    "relevance": "Demonstrates repository pattern",
                    "priority": "primary"
                }
            ]
        })
        enhancer.bridge_invoker.invoke.return_value = ai_response

        result = enhancer.find_relevant_templates(sample_agent_metadata, sample_templates)

        # Should NOT include DomainCameraView.cs.template
        paths = [t.path for t in result]
        assert 'templates/other/DomainCameraView.cs.template' not in paths

    def test_find_relevant_templates_empty_list(self, enhancer, sample_agent_metadata):
        """Test handling of empty template list"""
        enhancer.template_root = Path('/tmp')
        result = enhancer.find_relevant_templates(sample_agent_metadata, [])
        assert result == []

    def test_find_relevant_templates_ai_failure(self, enhancer, sample_agent_metadata, sample_templates):
        """Test graceful handling of AI failure"""
        enhancer.template_root = Path('/tmp')
        enhancer.bridge_invoker.invoke.side_effect = Exception("AI service unavailable")

        result = enhancer.find_relevant_templates(sample_agent_metadata, sample_templates)

        assert result == []  # Should return empty list, not crash

    def test_find_relevant_templates_no_bridge(self, enhancer_no_bridge, sample_agent_metadata, sample_templates):
        """Test graceful degradation when no bridge invoker available"""
        enhancer_no_bridge.template_root = Path('/tmp')

        result = enhancer_no_bridge.find_relevant_templates(sample_agent_metadata, sample_templates)

        assert result == []  # Should return empty list gracefully

    def test_generate_enhanced_content_success(self, enhancer, sample_agent_metadata):
        """Test successful content generation"""
        relevant_templates = [
            TemplateRelevance(
                path='templates/other/ConfigurationRepository.cs.template',
                relevance_reason='Repository pattern example',
                priority='primary'
            )
        ]

        # Mock bridge invoker response with markdown content
        ai_response = """## Purpose

Implements repository pattern with Realm database.

## When to Use This Agent

1. **Creating Data Access Layers** - Implementing new repositories
2. **Working with Realm Database** - Building offline-first architectures

## Related Templates

**templates/other/ConfigurationRepository.cs.template**
- Demonstrates: Repository interface pattern
- Use for: Application configuration

## Best Practices

1. **Interface Segregation** - Always define repository interfaces"""

        enhancer.bridge_invoker.invoke.return_value = ai_response
        enhancer.template_root = Path('/tmp')

        # Mock template reading
        with patch.object(enhancer, '_read_template_contents', return_value='template contents'):
            result = enhancer.generate_enhanced_content(sample_agent_metadata, relevant_templates)

        # Verify
        assert "## Purpose" in result
        assert "## When to Use This Agent" in result
        assert "## Related Templates" in result
        assert "ConfigurationRepository.cs.template" in result

    def test_generate_enhanced_content_ai_failure(self, enhancer, sample_agent_metadata):
        """Test fallback content when AI fails"""
        relevant_templates = []
        enhancer.bridge_invoker.invoke.side_effect = Exception("AI service down")
        enhancer.template_root = Path('/tmp')

        with patch.object(enhancer, '_read_template_contents', return_value=''):
            result = enhancer.generate_enhanced_content(sample_agent_metadata, relevant_templates)

        # Should return minimal content
        assert "## Purpose" in result
        assert sample_agent_metadata.description in result

    def test_generate_enhanced_content_no_bridge(self, enhancer_no_bridge, sample_agent_metadata):
        """Test graceful degradation when no bridge invoker available"""
        relevant_templates = []
        enhancer_no_bridge.template_root = Path('/tmp')

        result = enhancer_no_bridge.generate_enhanced_content(sample_agent_metadata, relevant_templates)

        # Should return minimal fallback content
        assert "## Purpose" in result
        assert sample_agent_metadata.description in result
        assert "## When to Use This Agent" in result

    def test_parse_template_discovery_response_valid_json(self, enhancer):
        """Test parsing valid JSON response"""
        response = json.dumps({
            "templates": [
                {
                    "path": "templates/test.template",
                    "relevance": "Test template",
                    "priority": "primary"
                }
            ]
        })

        result = enhancer._parse_template_discovery_response(response)

        assert len(result) == 1
        assert result[0].path == "templates/test.template"
        assert result[0].priority == "primary"

    def test_parse_template_discovery_response_markdown_wrapped(self, enhancer):
        """Test parsing JSON wrapped in markdown"""
        response = """```json
{
  "templates": [
    {
      "path": "templates/test.template",
      "relevance": "Test",
      "priority": "primary"
    }
  ]
}
```"""

        result = enhancer._parse_template_discovery_response(response)

        assert len(result) == 1
        assert result[0].path == "templates/test.template"

    def test_parse_template_discovery_response_invalid_json(self, enhancer):
        """Test handling invalid JSON"""
        response = "Not valid JSON at all"

        result = enhancer._parse_template_discovery_response(response)

        assert result == []  # Should return empty list, not crash

    def test_assemble_agent_file(self, enhancer, sample_agent_metadata):
        """Test agent file assembly"""
        enhanced_content = """## Purpose

Test content

## When to Use

Test scenarios"""

        result = enhancer._assemble_agent_file(sample_agent_metadata, enhanced_content)

        # Verify frontmatter
        assert result.startswith('---')
        assert f'name: {sample_agent_metadata.name}' in result
        assert f'description: {sample_agent_metadata.description}' in result
        assert f'priority: {sample_agent_metadata.priority}' in result

        # Verify technologies
        for tech in sample_agent_metadata.technologies:
            assert tech in result

        # Verify content
        assert enhanced_content in result
        assert "## Technologies" in result
        assert "## Usage in Taskwright" in result

    def test_format_title(self, enhancer):
        """Test title formatting"""
        result = enhancer._format_title('repository-pattern-specialist')
        assert result == 'Repository Pattern Specialist'

    def test_format_bullet_list(self, enhancer):
        """Test bullet list formatting"""
        items = ['C#', 'Repository Pattern', 'Realm']
        result = enhancer._format_bullet_list(items)

        assert '- C#' in result
        assert '- Repository Pattern' in result
        assert '- Realm' in result
        assert result.count('\n') == 2  # 3 items = 2 newlines

    def test_read_frontmatter(self, enhancer):
        """Test reading frontmatter from agent file"""
        agent_content = """---
name: test-agent
description: Test agent description
priority: 5
technologies:
  - Python
  - Django
---

# Test Agent Content"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write(agent_content)
            f.flush()
            agent_file = Path(f.name)

        try:
            result = enhancer._read_frontmatter(agent_file)

            assert result.name == 'test-agent'
            assert result.description == 'Test agent description'
            assert result.priority == 5
            assert 'Python' in result.technologies
            assert 'Django' in result.technologies
        finally:
            agent_file.unlink()

    def test_get_fallback_content(self, enhancer, sample_agent_metadata):
        """Test fallback content generation"""
        result = enhancer._get_fallback_content(sample_agent_metadata)

        assert "## Purpose" in result
        assert sample_agent_metadata.description in result
        assert "## When to Use This Agent" in result
        assert "## Technologies" in result
        assert "## Usage in Taskwright" in result


class TestIntegrationScenarios:
    """Integration tests for complete enhancement workflows"""

    @pytest.fixture
    def mock_bridge_invoker(self):
        """Create mock agent bridge invoker"""
        invoker = Mock()
        invoker.invoke = Mock()
        return invoker

    @pytest.fixture
    def temp_template_dir(self):
        """Create temporary template directory structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            # Create agents directory
            agents_dir = temp_path / 'agents'
            agents_dir.mkdir()

            # Create templates directory
            templates_dir = temp_path / 'templates'
            templates_dir.mkdir()

            # Create sample agent file
            agent_file = agents_dir / 'test-agent.md'
            agent_file.write_text("""---
name: test-agent
description: Test agent for enhancement
priority: 8
technologies:
  - Python
  - Testing
---

# Test Agent

Original content.""")

            # Create sample template
            template_file = templates_dir / 'sample.template'
            template_file.write_text("""def test_function():
    '''Sample test function'''
    assert True""")

            yield temp_path

    def test_enhance_agent_file_with_templates(self, mock_bridge_invoker, temp_template_dir):
        """Test enhancing an agent file with discovered templates"""
        enhancer = AgentEnhancer(mock_bridge_invoker)

        agent_file = temp_template_dir / 'agents' / 'test-agent.md'
        template_file = temp_template_dir / 'templates' / 'sample.template'

        # Mock template discovery response
        discovery_response = json.dumps({
            "templates": [
                {
                    "path": "templates/sample.template",
                    "relevance": "Sample test template",
                    "priority": "primary"
                }
            ]
        })

        # Mock content generation response
        content_response = """## Purpose
Testing framework integration for Python projects.

## Related Templates
**templates/sample.template** - Sample test implementation"""

        # Configure mock to return different values on successive calls
        mock_bridge_invoker.invoke.side_effect = [
            discovery_response,
            content_response
        ]

        enhancer.template_root = temp_template_dir

        # Execute enhancement
        result = enhancer.enhance_agent_file(agent_file, [template_file])

        assert result is True

        # Verify file was updated
        updated_content = agent_file.read_text()
        assert '## Purpose' in updated_content
        assert 'Testing framework' in updated_content

    def test_enhance_all_agents_integration(self, mock_bridge_invoker, temp_template_dir):
        """Test enhancing all agents in a template directory"""
        enhancer = AgentEnhancer(mock_bridge_invoker)

        # Create second agent file
        agents_dir = temp_template_dir / 'agents'
        agent_file2 = agents_dir / 'second-agent.md'
        agent_file2.write_text("""---
name: second-agent
description: Another test agent
priority: 5
technologies:
  - Go
---

# Second Agent""")

        # Mock responses
        template_response = json.dumps({
            "templates": [
                {
                    "path": "templates/sample.template",
                    "relevance": "Relevant template",
                    "priority": "primary"
                }
            ]
        })

        content_response = """## Purpose
Agent for Go development."""

        # Configure mock to respond to multiple calls
        mock_bridge_invoker.invoke.side_effect = [
            template_response,  # First agent template discovery
            content_response,    # First agent content generation
            template_response,  # Second agent template discovery
            content_response,    # Second agent content generation
        ]

        # Execute
        results = enhancer.enhance_all_agents(temp_template_dir)

        # Verify results
        assert 'test-agent' in results
        assert 'second-agent' in results

    def test_enhance_with_missing_agents_directory(self, mock_bridge_invoker):
        """Test handling of missing agents directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_path = Path(tmpdir)

            enhancer = AgentEnhancer(mock_bridge_invoker)
            results = enhancer.enhance_all_agents(temp_path)

            assert results == {}


class TestNoHardCoding:
    """Test to ensure no hard-coded agent→template mappings exist"""

    def test_no_hard_coded_mappings(self):
        """Verify agent_enhancer.py contains no hard-coded mappings"""
        source_path = Path(__file__).parent.parent.parent.parent.parent / \
                      'installer/global/lib/template_creation/agent_enhancer.py'

        source_code = source_path.read_text()

        # Check for forbidden patterns
        forbidden_patterns = [
            'agent_templates = {',  # Hard-coded dictionary
            'if "repository" in agent_name',  # Pattern matching on agent name
            'if "mvvm" in agent_name',  # Pattern matching on agent name
            'template_name.lower() in agent_name',  # Template name matching
        ]

        for pattern in forbidden_patterns:
            assert pattern not in source_code, \
                f"FORBIDDEN: Hard-coded pattern detected: {pattern}"

        # Verify bridge invoker methods are used
        assert 'bridge_invoker.invoke(' in source_code, \
            "Missing bridge invocation - should use agent bridge for discovery/content"
        assert 'find_relevant_templates' in source_code, \
            "Missing find_relevant_templates method"

    def test_bridge_invoker_dependency_injection(self):
        """Verify bridge invoker uses dependency injection"""
        source_path = Path(__file__).parent.parent.parent.parent.parent / \
                      'installer/global/lib/template_creation/agent_enhancer.py'

        source_code = source_path.read_text()

        # Check __init__ signature
        assert 'def __init__(self, bridge_invoker' in source_code, \
            "Bridge invoker should be injected via constructor"
        assert 'self.bridge_invoker = bridge_invoker' in source_code, \
            "Bridge invoker should be stored as instance variable"
