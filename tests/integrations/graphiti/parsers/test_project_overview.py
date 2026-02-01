"""Tests for ProjectOverviewParser.

TDD RED Phase - Tests written BEFORE implementation.
All tests will FAIL until ProjectOverviewParser is implemented.

Tests cover:
1. Parser instantiation and properties
2. can_parse() method behavior
3. parse() method behavior for CLAUDE.md
4. parse() method behavior for README.md
5. Edge cases and error handling
"""

import pytest

from guardkit.integrations.graphiti.parsers.base import EpisodeData, ParseResult
from guardkit.integrations.graphiti.parsers.project_overview import ProjectOverviewParser


class TestProjectOverviewParserInstantiation:
    """Test parser instantiation and basic properties."""

    def test_parser_type_property(self):
        """Parser type should be 'project_overview'."""
        parser = ProjectOverviewParser()
        assert parser.parser_type == "project_overview"

    def test_supported_extensions_property(self):
        """Parser should support .md extension."""
        parser = ProjectOverviewParser()
        assert parser.supported_extensions == [".md"]


class TestCanParse:
    """Test can_parse() method for file detection."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return ProjectOverviewParser()

    def test_can_parse_claude_md_uppercase(self, parser):
        """Should recognize CLAUDE.md (uppercase)."""
        assert parser.can_parse("", "CLAUDE.md") is True

    def test_can_parse_claude_md_lowercase(self, parser):
        """Should recognize claude.md (lowercase)."""
        assert parser.can_parse("", "claude.md") is True

    def test_can_parse_claude_md_mixed_case(self, parser):
        """Should recognize Claude.md (mixed case)."""
        assert parser.can_parse("", "Claude.md") is True

    def test_can_parse_readme_md_uppercase(self, parser):
        """Should recognize README.md (uppercase)."""
        assert parser.can_parse("", "README.md") is True

    def test_can_parse_readme_md_lowercase(self, parser):
        """Should recognize readme.md (lowercase)."""
        assert parser.can_parse("", "readme.md") is True

    def test_can_parse_readme_md_mixed_case(self, parser):
        """Should recognize Readme.md (mixed case)."""
        assert parser.can_parse("", "Readme.md") is True

    def test_can_parse_claude_md_with_path(self, parser):
        """Should recognize CLAUDE.md with directory path."""
        assert parser.can_parse("", "/path/to/project/CLAUDE.md") is True
        assert parser.can_parse("", ".claude/CLAUDE.md") is True

    def test_can_parse_readme_md_with_path(self, parser):
        """Should recognize README.md with directory path."""
        assert parser.can_parse("", "/path/to/project/README.md") is True
        assert parser.can_parse("", "docs/README.md") is True

    def test_cannot_parse_other_md_files(self, parser):
        """Should not recognize other .md files."""
        assert parser.can_parse("", "CONTRIBUTING.md") is False
        assert parser.can_parse("", "CHANGELOG.md") is False
        assert parser.can_parse("", "doc.md") is False
        assert parser.can_parse("", "feature.md") is False

    def test_cannot_parse_non_md_files(self, parser):
        """Should not recognize non-.md files."""
        assert parser.can_parse("", "CLAUDE.txt") is False
        assert parser.can_parse("", "README.rst") is False
        assert parser.can_parse("", "file.py") is False
        assert parser.can_parse("", "config.json") is False

    def test_can_parse_empty_filename(self, parser):
        """Should handle empty filename gracefully."""
        assert parser.can_parse("", "") is False

    def test_can_parse_none_filename(self, parser):
        """Should handle None filename gracefully."""
        assert parser.can_parse("", None) is False


class TestParseClaudeMd:
    """Test parse() method for CLAUDE.md files."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return ProjectOverviewParser()

    def test_parse_basic_claude_md(self, parser):
        """Should parse basic CLAUDE.md with all sections."""
        content = """# GuardKit - Lightweight Task Workflow

This is an AI-powered task workflow system.

## Core Principles

1. Quality First
2. Pragmatic Approach

## Technology Stack

- Python 3.11+
- pytest for testing
- FastAPI for API

## Architecture

The system uses a modular architecture with:
- Core workflow engine
- Plugin system for extensibility
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) == 1
        assert len(result.warnings) == 0

        episode = result.episodes[0]
        assert episode.group_id == "project_overview"
        assert episode.entity_type == "project"
        assert episode.entity_id == "guardkit"
        assert "AI-powered task workflow" in episode.content
        assert "Quality First" in episode.content
        assert "Python 3.11+" in episode.content
        assert "modular architecture" in episode.content

        # Check metadata
        assert episode.metadata["file_path"] == "CLAUDE.md"
        assert episode.metadata["parser_type"] == "project_overview"
        assert "purpose" in episode.metadata
        assert "tech_stack" in episode.metadata
        assert "architecture" in episode.metadata

    def test_parse_claude_md_with_rich_architecture(self, parser):
        """Should create separate architecture episode when content is rich (>500 chars)."""
        architecture_content = """
The system uses a sophisticated multi-layered architecture designed for scalability:

1. Presentation Layer: React-based UI with TypeScript
2. API Layer: FastAPI with async endpoints
3. Business Logic Layer: Domain-driven design with CQRS
4. Data Layer: PostgreSQL with SQLAlchemy ORM
5. Message Queue: RabbitMQ for async processing
6. Cache Layer: Redis for session and query caching
7. Monitoring: Prometheus + Grafana for observability

The architecture follows microservices principles with:
- Service discovery via Consul
- API Gateway using Kong
- Circuit breakers with Resilience4j
- Distributed tracing with Jaeger
"""
        content = f"""# Project Name

Project description.

## Architecture

{architecture_content}
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) == 2
        assert len(result.warnings) == 0

        # First episode: project overview
        overview = result.episodes[0]
        assert overview.group_id == "project_overview"

        # Second episode: architecture details
        arch_episode = result.episodes[1]
        assert arch_episode.group_id == "project_architecture"
        assert arch_episode.entity_type == "architecture"
        assert "multi-layered architecture" in arch_episode.content
        assert "microservices principles" in arch_episode.content

    def test_parse_claude_md_missing_purpose(self, parser):
        """Should handle CLAUDE.md missing purpose section."""
        content = """# Project Title

## Technology Stack

- Python 3.11+
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1
        assert any("Missing 'purpose' section" in w for w in result.warnings)

    def test_parse_claude_md_missing_tech_stack(self, parser):
        """Should handle CLAUDE.md missing tech stack section."""
        content = """# Project Title

This is a project description.

## Architecture

Simple architecture.
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1
        assert any("Missing 'tech_stack' section" in w for w in result.warnings)

    def test_parse_claude_md_missing_architecture(self, parser):
        """Should handle CLAUDE.md missing architecture section."""
        content = """# Project Title

This is a project description.

## Technology Stack

- Python 3.11+
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1
        assert any("Missing 'architecture' section" in w for w in result.warnings)

    def test_parse_claude_md_all_sections_missing(self, parser):
        """Should handle CLAUDE.md with all sections missing."""
        content = """# Just a Title

Some random content that doesn't match expected sections.
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        # Should still create episode with available content
        assert len(result.episodes) >= 1
        # Should have warnings for missing sections
        assert len(result.warnings) >= 3

    def test_parse_claude_md_empty_content(self, parser):
        """Should handle empty CLAUDE.md file."""
        result = parser.parse("", "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) == 0
        assert any("Empty content" in w for w in result.warnings)

    def test_parse_claude_md_whitespace_only(self, parser):
        """Should handle CLAUDE.md with only whitespace."""
        result = parser.parse("   \n\n   \t  ", "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) == 0
        assert any("Empty content" in w for w in result.warnings)


class TestParseReadmeMd:
    """Test parse() method for README.md files."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return ProjectOverviewParser()

    def test_parse_basic_readme_md(self, parser):
        """Should parse basic README.md with common sections."""
        content = """# My Awesome Project

A tool for managing tasks efficiently.

## Features

- Task creation
- Task tracking
- Collaboration

## Installation

pip install my-project

## Technology

Built with Python and FastAPI.

## Architecture

Simple client-server architecture.
"""
        result = parser.parse(content, "README.md")

        assert result.success is True
        assert len(result.episodes) == 1
        assert len(result.warnings) == 0

        episode = result.episodes[0]
        assert episode.group_id == "project_overview"
        assert episode.entity_type == "project"
        assert "managing tasks efficiently" in episode.content
        assert "Python and FastAPI" in episode.content

    def test_parse_readme_md_with_installation_only(self, parser):
        """Should parse README.md with minimal sections."""
        content = """# Simple Project

## Installation

npm install
"""
        result = parser.parse(content, "README.md")

        assert result.success is True
        assert len(result.episodes) >= 1
        # Warnings expected for missing purpose/tech/architecture
        assert len(result.warnings) > 0

    def test_parse_readme_md_empty_content(self, parser):
        """Should handle empty README.md file."""
        result = parser.parse("", "README.md")

        assert result.success is True
        assert len(result.episodes) == 0
        assert any("Empty content" in w for w in result.warnings)


class TestParseMetadata:
    """Test episode metadata generation."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return ProjectOverviewParser()

    def test_metadata_contains_file_path(self, parser):
        """Episode metadata should contain file_path."""
        content = "# Project\n\nDescription here."
        result = parser.parse(content, "/path/to/CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1
        assert result.episodes[0].metadata["file_path"] == "/path/to/CLAUDE.md"

    def test_metadata_contains_parser_type(self, parser):
        """Episode metadata should contain parser_type."""
        content = "# Project\n\nDescription here."
        result = parser.parse(content, "README.md")

        assert result.success is True
        assert len(result.episodes) >= 1
        assert result.episodes[0].metadata["parser_type"] == "project_overview"

    def test_metadata_contains_extracted_sections(self, parser):
        """Episode metadata should contain extracted section content."""
        content = """# Project

This is the purpose.

## Tech Stack

- Python
- FastAPI

## Architecture

Modular design.
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1

        metadata = result.episodes[0].metadata
        assert "purpose" in metadata
        assert "tech_stack" in metadata
        assert "architecture" in metadata
        assert "Python" in metadata["tech_stack"]


class TestEntityIdentification:
    """Test entity_type and entity_id extraction."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return ProjectOverviewParser()

    def test_entity_id_from_claude_md_title(self, parser):
        """Should extract entity_id from CLAUDE.md title."""
        content = "# GuardKit - Task Workflow\n\nProject description."
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1
        assert result.episodes[0].entity_id == "guardkit"

    def test_entity_id_from_readme_md_title(self, parser):
        """Should extract entity_id from README.md title."""
        content = "# My-Awesome-Project\n\nProject description."
        result = parser.parse(content, "README.md")

        assert result.success is True
        assert len(result.episodes) >= 1
        assert result.episodes[0].entity_id == "my-awesome-project"

    def test_entity_id_fallback_to_filename(self, parser):
        """Should fallback to filename if title cannot be extracted."""
        content = "Some content without a title heading."
        result = parser.parse(content, "CLAUDE.md")

        # Should use filename as fallback
        assert result.success is True
        if len(result.episodes) > 0:
            assert result.episodes[0].entity_id is not None

    def test_entity_type_is_project(self, parser):
        """Entity type should be 'project' for overview episodes."""
        content = "# Project\n\nDescription."
        result = parser.parse(content, "README.md")

        assert result.success is True
        assert len(result.episodes) >= 1
        assert result.episodes[0].entity_type == "project"

    def test_entity_type_is_architecture_for_arch_episode(self, parser):
        """Entity type should be 'architecture' for architecture episodes."""
        # Create content with rich architecture (>500 chars)
        rich_arch = """
Architecture section with lots of details about the system design,
including multiple layers, components, patterns, and integration points.
This should be long enough to trigger creation of a separate architecture
episode. """ + ("Additional content. " * 50)  # Ensure >500 chars

        content = f"""# Project

Description.

## Architecture

{rich_arch}
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) == 2

        # Check architecture episode has correct entity_type
        arch_episode = [e for e in result.episodes if e.group_id == "project_architecture"][0]
        assert arch_episode.entity_type == "architecture"


class TestEdgeCases:
    """Test edge cases and error handling."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return ProjectOverviewParser()

    def test_parse_non_project_overview_file_returns_empty(self, parser):
        """Parsing non-CLAUDE/README files should return empty result."""
        content = "# Some Document\n\nContent here."
        result = parser.parse(content, "other.md")

        # Parser should still work but might return different result
        # or empty episodes depending on implementation
        assert result.success is True

    def test_parse_malformed_markdown(self, parser):
        """Should handle malformed markdown gracefully."""
        content = """# Project

####### Too Many Hashes

## Section

Unclosed [link

`Unclosed code block
"""
        result = parser.parse(content, "CLAUDE.md")

        # Should not crash, but may generate warnings
        assert result.success is True

    def test_parse_unicode_content(self, parser):
        """Should handle unicode characters in content."""
        content = """# Проект - Project

This is a project with 中文 characters and émojis 🚀.

## Tech Stack

- Python 🐍
- FastAPI ⚡
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1
        assert "中文" in result.episodes[0].content or "🚀" in result.episodes[0].content

    def test_parse_very_large_content(self, parser):
        """Should handle very large content files."""
        # Create large content (10KB+)
        large_section = "This is a line of content.\n" * 1000
        content = f"""# Large Project

{large_section}

## Tech Stack

- Python

## Architecture

{large_section}
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        # Should create episodes successfully
        assert len(result.episodes) >= 1

    def test_parse_content_with_special_characters(self, parser):
        """Should handle special characters in content."""
        content = """# Project & Co. <Inc>

Description with special chars: @#$%^&*()

## Tech Stack

- C++ (modern)
- .NET Core
- <xml> tags
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1

    def test_parse_null_content(self, parser):
        """Should handle None content gracefully."""
        result = parser.parse(None, "CLAUDE.md")

        # Should not crash - either return empty or handle gracefully
        assert result.success is True or result.success is False
        assert isinstance(result.episodes, list)
        assert isinstance(result.warnings, list)

    def test_parse_content_with_only_headers(self, parser):
        """Should handle content with only section headers."""
        content = """# Project

## Purpose

## Tech Stack

## Architecture
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        # Should warn about empty sections
        assert len(result.warnings) > 0


class TestContentExtraction:
    """Test extraction of specific content sections."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return ProjectOverviewParser()

    def test_extract_purpose_from_first_paragraph(self, parser):
        """Should extract purpose from first paragraph after title."""
        content = """# Project Name

This is the main purpose of the project.
It continues here.

## Other Section

Content.
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1

        # Purpose should be in metadata or content
        episode = result.episodes[0]
        assert "main purpose" in episode.content or "main purpose" in str(episode.metadata)

    def test_extract_tech_stack_from_bullet_list(self, parser):
        """Should extract tech stack from bulleted lists."""
        content = """# Project

Description.

## Technology Stack

- Python 3.11+
- pytest for testing
- SQLAlchemy for ORM
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1

        episode = result.episodes[0]
        # Check that tech stack items are captured
        assert "Python 3.11+" in episode.content or "Python 3.11+" in str(episode.metadata)

    def test_extract_architecture_patterns(self, parser):
        """Should extract architecture patterns from content."""
        content = """# Project

Description.

## Architecture

The system follows microservices architecture with:
- API Gateway pattern
- Event-driven communication
- CQRS for data operations
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1

        episode = result.episodes[0]
        # Architecture details should be captured
        assert "microservices" in episode.content or "microservices" in str(episode.metadata)


class TestGroupIdAssignment:
    """Test correct group_id assignment for episodes."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return ProjectOverviewParser()

    def test_overview_episode_has_project_overview_group_id(self, parser):
        """Main episode should have 'project_overview' group_id."""
        content = """# Project

This is a project description.
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1
        assert result.episodes[0].group_id == "project_overview"

    def test_architecture_episode_has_project_architecture_group_id(self, parser):
        """Separate architecture episode should have 'project_architecture' group_id."""
        # Create rich architecture content (>500 chars)
        rich_arch = "Architecture details. " * 50

        content = f"""# Project

Description.

## Architecture

{rich_arch}
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) == 2

        # Find architecture episode
        arch_episodes = [e for e in result.episodes if e.group_id == "project_architecture"]
        assert len(arch_episodes) == 1
        assert arch_episodes[0].group_id == "project_architecture"


class TestWarningGeneration:
    """Test warning message generation."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return ProjectOverviewParser()

    def test_warning_for_missing_purpose(self, parser):
        """Should warn when purpose section is missing."""
        content = """# Project

## Tech Stack

- Python
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert any("purpose" in w.lower() for w in result.warnings)

    def test_warning_for_missing_tech_stack(self, parser):
        """Should warn when tech stack section is missing."""
        content = """# Project

This is a project description.
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert any("tech" in w.lower() for w in result.warnings)

    def test_warning_for_missing_architecture(self, parser):
        """Should warn when architecture section is missing."""
        content = """# Project

This is a project description.

## Tech Stack

- Python
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert any("architecture" in w.lower() for w in result.warnings)

    def test_no_warnings_for_complete_document(self, parser):
        """Should not generate warnings for complete document."""
        content = """# Project

This is the project purpose.

## Tech Stack

- Python 3.11+

## Architecture

Modular architecture with plugins.
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.warnings) == 0


class TestParseResultStructure:
    """Test ParseResult structure and fields."""

    @pytest.fixture
    def parser(self):
        """Create parser instance for tests."""
        return ProjectOverviewParser()

    def test_parse_result_has_episodes_list(self, parser):
        """ParseResult should have episodes as list."""
        content = "# Project\n\nDescription."
        result = parser.parse(content, "CLAUDE.md")

        assert isinstance(result.episodes, list)

    def test_parse_result_has_warnings_list(self, parser):
        """ParseResult should have warnings as list."""
        content = "# Project\n\nDescription."
        result = parser.parse(content, "CLAUDE.md")

        assert isinstance(result.warnings, list)

    def test_parse_result_has_success_boolean(self, parser):
        """ParseResult should have success as boolean."""
        content = "# Project\n\nDescription."
        result = parser.parse(content, "CLAUDE.md")

        assert isinstance(result.success, bool)

    def test_parse_result_episodes_are_episode_data(self, parser):
        """Episodes in result should be EpisodeData instances."""
        content = """# Project

Purpose here.

## Tech Stack

- Python
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        if len(result.episodes) > 0:
            assert all(isinstance(e, EpisodeData) for e in result.episodes)

    def test_episode_data_has_required_fields(self, parser):
        """EpisodeData should have all required fields."""
        content = """# Project

Purpose here.
"""
        result = parser.parse(content, "CLAUDE.md")

        assert result.success is True
        assert len(result.episodes) >= 1

        episode = result.episodes[0]
        assert hasattr(episode, "content")
        assert hasattr(episode, "group_id")
        assert hasattr(episode, "entity_type")
        assert hasattr(episode, "entity_id")
        assert hasattr(episode, "metadata")

        # Fields should have correct types
        assert isinstance(episode.content, str)
        assert isinstance(episode.group_id, str)
        assert isinstance(episode.entity_type, str)
        assert isinstance(episode.entity_id, str)
        assert isinstance(episode.metadata, dict)
