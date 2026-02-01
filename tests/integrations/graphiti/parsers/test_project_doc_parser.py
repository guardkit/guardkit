"""Tests for ProjectDocParser - CLAUDE.md and README.md parsing.

TDD RED Phase: These tests define the expected behavior for:
- ProjectDocParser class (inherits from BaseParser)
- Parsing CLAUDE.md and README.md files
- Extracting project overview, tech stack, and architecture patterns
- Handling various markdown formats and missing sections

Coverage Target: >=85%
Test Count: 25+ tests
"""

import pytest
from pathlib import Path

# These imports will fail until implementation is complete (TDD RED)
from guardkit.integrations.graphiti.parsers.base import (
    BaseParser,
    EpisodeData,
    ParseResult,
)
from guardkit.integrations.graphiti.parsers.project_doc_parser import (
    ProjectDocParser,
    PURPOSE_HEADERS,
    TECH_HEADERS,
    ARCH_HEADERS,
)


# ============================================================================
# 1. Parser Configuration Tests (5 tests)
# ============================================================================

class TestProjectDocParserConfiguration:
    """Tests for parser configuration and registration."""

    def test_parser_inherits_from_base_parser(self):
        """ProjectDocParser should inherit from BaseParser."""
        parser = ProjectDocParser()
        assert isinstance(parser, BaseParser)

    def test_parser_type_property(self):
        """parser_type should return 'project_doc'."""
        parser = ProjectDocParser()
        assert parser.parser_type == "project_doc"

    def test_supported_extensions(self):
        """supported_extensions should return ['.md', '.markdown']."""
        parser = ProjectDocParser()
        assert parser.supported_extensions == [".md", ".markdown"]

    def test_can_parse_identifies_claude_md(self):
        """can_parse should return True for CLAUDE.md files."""
        parser = ProjectDocParser()
        assert parser.can_parse("# Content", "CLAUDE.md") is True
        assert parser.can_parse("# Content", "/path/to/CLAUDE.md") is True
        assert parser.can_parse("# Content", "./docs/CLAUDE.md") is True

    def test_can_parse_identifies_readme_md(self):
        """can_parse should return True for README.md files."""
        parser = ProjectDocParser()
        assert parser.can_parse("# Content", "README.md") is True
        assert parser.can_parse("# Content", "/path/to/README.md") is True
        assert parser.can_parse("# Content", "./docs/README.md") is True


# ============================================================================
# 2. File Detection Tests (5 tests)
# ============================================================================

class TestFileDetection:
    """Tests for file type detection."""

    def test_can_parse_case_insensitive(self):
        """can_parse should be case-insensitive for filenames."""
        parser = ProjectDocParser()
        assert parser.can_parse("# Content", "claude.md") is True
        assert parser.can_parse("# Content", "CLAUDE.MD") is True
        assert parser.can_parse("# Content", "readme.md") is True
        assert parser.can_parse("# Content", "README.MD") is True

    def test_can_parse_rejects_other_markdown(self):
        """can_parse should reject non-project markdown files."""
        parser = ProjectDocParser()
        assert parser.can_parse("# Content", "CHANGELOG.md") is False
        assert parser.can_parse("# Content", "CONTRIBUTING.md") is False
        assert parser.can_parse("# Content", "docs.md") is False
        assert parser.can_parse("# Content", "notes.md") is False

    def test_can_parse_supports_markdown_extension(self):
        """can_parse should support .markdown extension."""
        parser = ProjectDocParser()
        assert parser.can_parse("# Content", "CLAUDE.markdown") is True
        assert parser.can_parse("# Content", "README.markdown") is True

    def test_can_parse_rejects_non_markdown(self):
        """can_parse should reject non-markdown files."""
        parser = ProjectDocParser()
        assert parser.can_parse("# Content", "CLAUDE.txt") is False
        assert parser.can_parse("# Content", "README.rst") is False
        assert parser.can_parse("# Content", "config.yaml") is False

    def test_can_parse_handles_path_objects(self):
        """can_parse should work with Path objects converted to strings."""
        parser = ProjectDocParser()
        path = str(Path("docs") / "CLAUDE.md")
        assert parser.can_parse("# Content", path) is True


# ============================================================================
# 3. Purpose Extraction Tests (6 tests)
# ============================================================================

class TestPurposeExtraction:
    """Tests for extracting project purpose from various headers."""

    def test_extract_purpose_from_overview_header(self):
        """Should extract purpose from '## Overview' section."""
        parser = ProjectDocParser()
        content = """
# Project Name

## Overview
This is a project for doing X.
It helps users accomplish Y.

## Other Section
Content here.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        assert len(result.episodes) > 0

        # Check that overview content is in one of the episodes
        overview_found = any(
            "project for doing X" in episode.content
            for episode in result.episodes
        )
        assert overview_found

    def test_extract_purpose_from_purpose_header(self):
        """Should extract purpose from '## Purpose' section."""
        parser = ProjectDocParser()
        content = """
# Project

## Purpose
The purpose of this project is to solve problem Z.

## Details
More content.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        overview_found = any(
            "solve problem Z" in episode.content
            for episode in result.episodes
        )
        assert overview_found

    def test_extract_purpose_from_about_header(self):
        """Should extract purpose from '## About' section."""
        parser = ProjectDocParser()
        content = """
# Project

## About
About this project: it does amazing things.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        overview_found = any(
            "amazing things" in episode.content
            for episode in result.episodes
        )
        assert overview_found

    def test_extract_purpose_case_insensitive(self):
        """Purpose extraction should be case-insensitive."""
        parser = ProjectDocParser()
        content = """
# Project

## OVERVIEW
This is the overview.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        overview_found = any(
            "overview" in episode.content.lower()
            for episode in result.episodes
        )
        assert overview_found

    def test_extract_purpose_multi_word_headers(self):
        """Should handle multi-word purpose headers."""
        parser = ProjectDocParser()
        content = """
# Project

## What is this
This is a description of what the project does.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        overview_found = any(
            "what the project does" in episode.content
            for episode in result.episodes
        )
        assert overview_found

    def test_extract_purpose_handles_missing_section(self):
        """Should handle missing purpose section gracefully."""
        parser = ProjectDocParser()
        content = """
# Project

## Installation
Steps to install.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        # Should have warnings about missing purpose
        assert any("purpose" in warning.lower() for warning in result.warnings)


# ============================================================================
# 4. Tech Stack Extraction Tests (5 tests)
# ============================================================================

class TestTechStackExtraction:
    """Tests for extracting technology stack."""

    def test_extract_tech_stack_from_list(self):
        """Should extract tech stack from bulleted list."""
        parser = ProjectDocParser()
        content = """
# Project

## Tech Stack
- Python 3.11
- FastAPI
- PostgreSQL
- Redis
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True

        # Check that tech stack items are captured
        tech_found = any(
            "Python 3.11" in episode.content and "FastAPI" in episode.content
            for episode in result.episodes
        )
        assert tech_found

    def test_extract_tech_stack_from_technologies_header(self):
        """Should extract from '## Technologies' header."""
        parser = ProjectDocParser()
        content = """
# Project

## Technologies
- TypeScript
- React
- Node.js
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        tech_found = any(
            "TypeScript" in episode.content
            for episode in result.episodes
        )
        assert tech_found

    def test_extract_tech_stack_from_built_with_header(self):
        """Should extract from '## Built With' header."""
        parser = ProjectDocParser()
        content = """
# Project

## Built With
This project is built with:
- Django
- Celery
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        tech_found = any(
            "Django" in episode.content
            for episode in result.episodes
        )
        assert tech_found

    def test_extract_tech_stack_handles_markdown_formatting(self):
        """Should handle various markdown formatting in tech stack."""
        parser = ProjectDocParser()
        content = """
# Project

## Stack
- **Python 3.11** - Backend
- *FastAPI* (API framework)
- `PostgreSQL` - Database
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        tech_found = any(
            "Python 3.11" in episode.content or "FastAPI" in episode.content
            for episode in result.episodes
        )
        assert tech_found

    def test_extract_tech_stack_handles_missing_section(self):
        """Should handle missing tech stack section gracefully."""
        parser = ProjectDocParser()
        content = """
# Project

## Overview
Project description.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        # Should have warnings about missing tech stack
        assert any("tech" in warning.lower() or "stack" in warning.lower()
                   for warning in result.warnings)


# ============================================================================
# 5. Architecture Pattern Extraction Tests (4 tests)
# ============================================================================

class TestArchitecturePatternExtraction:
    """Tests for extracting architecture patterns."""

    def test_extract_patterns_from_architecture_header(self):
        """Should extract patterns from '## Architecture' section."""
        parser = ProjectDocParser()
        content = """
# Project

## Architecture
- Clean architecture pattern
- Repository pattern
- CQRS
- Event sourcing
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True

        patterns_found = any(
            "Clean architecture" in episode.content and "Repository pattern" in episode.content
            for episode in result.episodes
        )
        assert patterns_found

    def test_extract_patterns_from_patterns_header(self):
        """Should extract from '## Patterns' header."""
        parser = ProjectDocParser()
        content = """
# Project

## Patterns
We use the following design patterns:
- Factory pattern
- Strategy pattern
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        patterns_found = any(
            "Factory pattern" in episode.content
            for episode in result.episodes
        )
        assert patterns_found

    def test_extract_patterns_from_structure_header(self):
        """Should extract from '## Structure' header."""
        parser = ProjectDocParser()
        content = """
# Project

## Structure
The project follows a layered architecture:
- Presentation layer
- Business logic layer
- Data access layer
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        patterns_found = any(
            "layered architecture" in episode.content
            for episode in result.episodes
        )
        assert patterns_found

    def test_extract_patterns_handles_missing_section(self):
        """Should handle missing architecture section gracefully."""
        parser = ProjectDocParser()
        content = """
# Project

## Overview
Simple project description.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        # Should have warnings about missing architecture
        assert any("architecture" in warning.lower() or "pattern" in warning.lower()
                   for warning in result.warnings)


# ============================================================================
# 6. YAML Frontmatter Tests (3 tests)
# ============================================================================

class TestYAMLFrontmatter:
    """Tests for YAML frontmatter parsing."""

    def test_parse_handles_yaml_frontmatter(self):
        """Should parse YAML frontmatter if present."""
        parser = ProjectDocParser()
        content = """---
title: My Project
version: 1.0.0
author: John Doe
---

# Project

## Overview
Project description.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        # Frontmatter metadata should be captured
        assert len(result.episodes) > 0

    def test_parse_extracts_frontmatter_metadata(self):
        """Should include frontmatter data in metadata."""
        parser = ProjectDocParser()
        content = """---
title: My Project
stack: Python
---

# Project

## Overview
Description.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        # Check that frontmatter is in metadata
        has_frontmatter = any(
            episode.metadata.get("frontmatter") is not None
            for episode in result.episodes
        )
        assert has_frontmatter

    def test_parse_works_without_frontmatter(self):
        """Should work correctly without frontmatter."""
        parser = ProjectDocParser()
        content = """
# Project

## Overview
Simple description.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        assert len(result.episodes) > 0


# ============================================================================
# 7. Episode Generation Tests (4 tests)
# ============================================================================

class TestEpisodeGeneration:
    """Tests for EpisodeData generation."""

    def test_parse_generates_episode_data(self):
        """Should generate EpisodeData instances."""
        parser = ProjectDocParser()
        content = """
# Project

## Overview
Project overview.

## Tech Stack
- Python
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        assert len(result.episodes) > 0
        assert all(isinstance(ep, EpisodeData) for ep in result.episodes)

    def test_episode_has_correct_entity_type(self):
        """Episodes should have 'project_doc' entity type."""
        parser = ProjectDocParser()
        content = """
# Project

## Overview
Description.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        assert all(ep.entity_type == "project_doc" for ep in result.episodes)

    def test_episode_has_file_path_as_entity_id(self):
        """Episode entity_id should be the file path."""
        parser = ProjectDocParser()
        content = """
# Project

## Overview
Description.
"""
        file_path = "/path/to/CLAUDE.md"
        result = parser.parse(content, file_path)
        assert result.success is True
        assert any(ep.entity_id == file_path for ep in result.episodes)

    def test_episode_has_appropriate_group_id(self):
        """Episodes should have a meaningful group_id."""
        parser = ProjectDocParser()
        content = """
# Project

## Overview
Description.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True
        assert all(ep.group_id is not None for ep in result.episodes)
        assert all(len(ep.group_id) > 0 for ep in result.episodes)


# ============================================================================
# 8. Error Handling and Edge Cases (5 tests)
# ============================================================================

class TestErrorHandlingAndEdgeCases:
    """Tests for error handling and edge cases."""

    def test_parse_handles_empty_content(self):
        """Should handle empty content gracefully."""
        parser = ProjectDocParser()
        result = parser.parse("", "CLAUDE.md")
        assert result.success is False
        assert len(result.warnings) > 0
        assert any("empty" in warning.lower() for warning in result.warnings)

    def test_parse_handles_only_whitespace(self):
        """Should handle whitespace-only content."""
        parser = ProjectDocParser()
        result = parser.parse("   \n\n   ", "CLAUDE.md")
        assert result.success is False
        assert len(result.warnings) > 0

    def test_parse_handles_no_headers(self):
        """Should handle content with no section headers."""
        parser = ProjectDocParser()
        content = """
This is just plain text
with no headers at all.
"""
        result = parser.parse(content, "CLAUDE.md")
        # May succeed with warnings, or fail - implementation decides
        assert result.success is True or result.success is False
        if result.success:
            assert len(result.warnings) > 0

    def test_parse_provides_helpful_error_for_malformed_frontmatter(self):
        """Should provide helpful error for malformed YAML frontmatter."""
        parser = ProjectDocParser()
        content = """---
title: Project
invalid yaml: [unclosed
---

# Project
"""
        result = parser.parse(content, "CLAUDE.md")
        # Should either succeed with warnings or fail with helpful error
        if not result.success:
            assert len(result.warnings) > 0
            assert any("frontmatter" in warning.lower() or "yaml" in warning.lower()
                       for warning in result.warnings)
        else:
            # If it succeeds, should have warnings about frontmatter issues
            assert len(result.warnings) > 0

    def test_parse_handles_very_long_content(self):
        """Should handle very long content without errors."""
        parser = ProjectDocParser()
        # Create a long document
        sections = []
        for i in range(100):
            sections.append(f"## Section {i}\n")
            sections.append("Content " * 100 + "\n\n")
        content = "\n".join(sections)

        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True or result.success is False
        # Should not crash


# ============================================================================
# 9. Integration with ParseResult (3 tests)
# ============================================================================

class TestParseResultIntegration:
    """Tests for integration with ParseResult dataclass."""

    def test_parse_returns_parse_result(self):
        """parse() should return a ParseResult instance."""
        parser = ProjectDocParser()
        content = """
# Project

## Overview
Description.
"""
        result = parser.parse(content, "CLAUDE.md")
        assert isinstance(result, ParseResult)

    def test_successful_parse_has_success_true(self):
        """Successful parse should have success=True."""
        parser = ProjectDocParser()
        content = """
# Project

## Overview
This is a project.

## Tech Stack
- Python
"""
        result = parser.parse(content, "CLAUDE.md")
        assert result.success is True

    def test_failed_parse_has_success_false(self):
        """Failed parse should have success=False."""
        parser = ProjectDocParser()
        result = parser.parse("", "CLAUDE.md")
        assert result.success is False


# ============================================================================
# 10. Header Pattern Constants Tests (3 tests)
# ============================================================================

class TestHeaderPatternConstants:
    """Tests for header pattern constants."""

    def test_purpose_headers_constant_exists(self):
        """PURPOSE_HEADERS constant should exist."""
        assert PURPOSE_HEADERS is not None
        assert isinstance(PURPOSE_HEADERS, (list, tuple))
        assert len(PURPOSE_HEADERS) > 0

    def test_tech_headers_constant_exists(self):
        """TECH_HEADERS constant should exist."""
        assert TECH_HEADERS is not None
        assert isinstance(TECH_HEADERS, (list, tuple))
        assert len(TECH_HEADERS) > 0

    def test_arch_headers_constant_exists(self):
        """ARCH_HEADERS constant should exist."""
        assert ARCH_HEADERS is not None
        assert isinstance(ARCH_HEADERS, (list, tuple))
        assert len(ARCH_HEADERS) > 0


# ============================================================================
# 11. Comprehensive Integration Test (1 test)
# ============================================================================

class TestComprehensiveIntegration:
    """End-to-end integration test with realistic content."""

    def test_parse_realistic_claude_md(self):
        """Should parse a realistic CLAUDE.md file completely."""
        parser = ProjectDocParser()
        content = """---
title: GuardKit
version: 1.0.0
---

# GuardKit - Lightweight Task Workflow System

## Project Overview
GuardKit is an AI-powered task workflow system with built-in quality gates
that prevents broken code from reaching production. The system is
technology-agnostic with stack-specific plugins.

## Tech Stack
- **Python 3.11** - Core implementation
- **FastAPI** - API framework
- **PostgreSQL** - Database
- **Redis** - Caching
- **Docker** - Containerization

## Architecture
The system follows these architectural patterns:
- Clean architecture pattern
- Repository pattern for data access
- CQRS for command/query separation
- Event-driven architecture for task state changes
- Plugin architecture for stack-specific extensions

## Core Principles
1. Quality First
2. Pragmatic Approach
3. AI/Human Collaboration
"""
        result = parser.parse(content, "CLAUDE.md")

        # Should succeed
        assert result.success is True

        # Should have episodes
        assert len(result.episodes) > 0

        # Should capture key information
        all_content = " ".join(ep.content for ep in result.episodes)
        assert "GuardKit" in all_content
        assert "Python" in all_content or "FastAPI" in all_content
        assert "Clean architecture" in all_content or "Repository pattern" in all_content

        # Should have minimal warnings (or none)
        assert len(result.warnings) <= 2  # Allow some minor warnings
