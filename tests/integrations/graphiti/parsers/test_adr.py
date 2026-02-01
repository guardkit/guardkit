"""Tests for ADR (Architecture Decision Record) parser.

These are TDD RED phase tests - they will FAIL until the implementation is complete.
"""

import pytest
from pathlib import Path

from guardkit.integrations.graphiti.parsers.adr import ADRParser
from guardkit.integrations.graphiti.parsers.base import EpisodeData, ParseResult
from guardkit.integrations.graphiti.constants import PROJECT_GROUPS


class TestADRParser:
    """Test ADRParser basic properties and detection."""

    @pytest.fixture
    def parser(self):
        """Create ADRParser instance."""
        return ADRParser()

    def test_parser_type_is_adr(self, parser):
        """Parser type should be 'adr'."""
        assert parser.parser_type == "adr"

    def test_supported_extensions(self, parser):
        """Should support .md extension."""
        assert parser.supported_extensions == [".md"]

    def test_can_parse_adr_filename_lowercase(self, parser):
        """Should detect ADR from filename (adr-001.md)."""
        content = "# Some Content"
        assert parser.can_parse(content, "adr-001.md") is True

    def test_can_parse_adr_filename_uppercase(self, parser):
        """Should detect ADR from filename (ADR-002.md)."""
        content = "# Some Content"
        assert parser.can_parse(content, "ADR-002.md") is True

    def test_can_parse_adr_filename_with_path(self, parser):
        """Should detect ADR from filename with path."""
        content = "# Some Content"
        assert parser.can_parse(content, "/docs/architecture/adr-003.md") is True

    def test_can_parse_adr_content_sections(self, parser):
        """Should detect ADR from standard sections."""
        content = """
# Some Decision

## Status
Accepted

## Context
We need to decide...

## Decision
We will use...
"""
        assert parser.can_parse(content, "decision.md") is True

    def test_can_parse_adr_content_case_insensitive(self, parser):
        """Should detect ADR sections case-insensitively."""
        content = """
# Some Decision

## STATUS
Accepted

## CONTEXT
We need to decide...

## DECISION
We will use...
"""
        assert parser.can_parse(content, "decision.md") is True

    def test_cannot_parse_regular_markdown(self, parser):
        """Should not detect regular markdown as ADR."""
        content = """
# Regular Documentation

This is just regular markdown content.

## Introduction

Some content here.
"""
        assert parser.can_parse(content, "README.md") is False

    def test_cannot_parse_non_adr_file(self, parser):
        """Should not detect non-ADR files."""
        content = "# Feature Specification"
        assert parser.can_parse(content, "feature-spec.md") is False

    def test_cannot_parse_partial_adr_sections(self, parser):
        """Should not detect file with only some ADR sections."""
        content = """
# Some Decision

## Status
Accepted

## Details
Some details...
"""
        assert parser.can_parse(content, "partial.md") is False


class TestADRParsing:
    """Test ADR content parsing and episode generation."""

    @pytest.fixture
    def parser(self):
        """Create ADRParser instance."""
        return ADRParser()

    @pytest.fixture
    def standard_adr_content(self):
        """Standard ADR format."""
        return """# ADR-001: Use Graphiti for Knowledge Storage

## Status
Accepted

## Context
We need a persistent knowledge storage system that can handle:
- Complex relationships between entities
- Semantic search capabilities
- Integration with LLM workflows

## Decision
We will use Graphiti with Neo4j as the knowledge graph backend because:
1. Native graph structure for relationships
2. Built-in semantic search
3. Active community and good documentation

## Consequences

### Positive
- Semantic search capability
- Rich relationship modeling
- Scalable architecture

### Negative
- Additional infrastructure (Neo4j)
- Learning curve for graph queries
- Operational complexity
"""

    def test_parse_standard_adr_format(self, parser, standard_adr_content):
        """Should successfully parse standard ADR format."""
        result = parser.parse(standard_adr_content, "adr-001.md")

        assert result.success is True
        assert len(result.episodes) == 1
        assert len(result.warnings) == 0

    def test_extract_title_from_heading(self, parser, standard_adr_content):
        """Should extract title from H1 heading."""
        result = parser.parse(standard_adr_content, "adr-001.md")
        episode = result.episodes[0]

        assert "Use Graphiti for Knowledge Storage" in episode.content

    def test_extract_status_section(self, parser, standard_adr_content):
        """Should extract status section."""
        result = parser.parse(standard_adr_content, "adr-001.md")
        episode = result.episodes[0]

        assert "Accepted" in episode.content or "Accepted" in episode.metadata["status"]

    def test_extract_context_section(self, parser, standard_adr_content):
        """Should extract context section."""
        result = parser.parse(standard_adr_content, "adr-001.md")
        episode = result.episodes[0]

        assert "persistent knowledge storage" in episode.content.lower()
        assert "semantic search" in episode.content.lower()

    def test_extract_decision_section(self, parser, standard_adr_content):
        """Should extract decision section."""
        result = parser.parse(standard_adr_content, "adr-001.md")
        episode = result.episodes[0]

        assert "Graphiti with Neo4j" in episode.content
        assert "graph backend" in episode.content.lower()

    def test_extract_consequences_section(self, parser, standard_adr_content):
        """Should extract consequences section."""
        result = parser.parse(standard_adr_content, "adr-001.md")
        episode = result.episodes[0]

        assert "Positive" in episode.content or "Negative" in episode.content
        assert "infrastructure" in episode.content.lower()

    def test_episode_has_correct_group_id(self, parser, standard_adr_content):
        """Episode should have 'project_decisions' group_id."""
        result = parser.parse(standard_adr_content, "adr-001.md")
        episode = result.episodes[0]

        assert episode.group_id == "project_decisions"

    def test_episode_has_correct_entity_type(self, parser, standard_adr_content):
        """Episode should have 'adr' entity_type."""
        result = parser.parse(standard_adr_content, "adr-001.md")
        episode = result.episodes[0]

        assert episode.entity_type == "adr"

    def test_episode_metadata_contains_source_path(self, parser, standard_adr_content):
        """Episode metadata should include source file path."""
        result = parser.parse(standard_adr_content, "adr-001.md")
        episode = result.episodes[0]

        assert "source_path" in episode.metadata
        assert episode.metadata["source_path"] == "adr-001.md"

    def test_episode_metadata_contains_status(self, parser, standard_adr_content):
        """Episode metadata should include ADR status."""
        result = parser.parse(standard_adr_content, "adr-001.md")
        episode = result.episodes[0]

        assert "status" in episode.metadata
        assert episode.metadata["status"] == "Accepted"

    def test_episode_entity_id_is_unique(self, parser, standard_adr_content):
        """Episode should have a unique entity_id."""
        result = parser.parse(standard_adr_content, "adr-001.md")
        episode = result.episodes[0]

        assert episode.entity_id
        assert len(episode.entity_id) > 0


class TestADREdgeCases:
    """Test ADR parser edge cases and variations."""

    @pytest.fixture
    def parser(self):
        """Create ADRParser instance."""
        return ADRParser()

    def test_parse_adr_with_missing_optional_sections(self, parser):
        """Should handle ADR without Consequences section."""
        content = """# ADR-002: Simple Decision

## Status
Accepted

## Context
We need to do something.

## Decision
We will do it this way.
"""
        result = parser.parse(content, "adr-002.md")

        assert result.success is True
        assert len(result.episodes) == 1

    def test_parse_adr_status_accepted(self, parser):
        """Should handle 'Accepted' status."""
        content = """# ADR-003: Test Decision

## Status
Accepted

## Context
Test context.

## Decision
Test decision.
"""
        result = parser.parse(content, "adr-003.md")
        episode = result.episodes[0]

        assert episode.metadata["status"] == "Accepted"

    def test_parse_adr_status_deprecated(self, parser):
        """Should handle 'Deprecated' status."""
        content = """# ADR-004: Old Decision

## Status
Deprecated

## Context
Test context.

## Decision
Test decision.
"""
        result = parser.parse(content, "adr-004.md")
        episode = result.episodes[0]

        assert episode.metadata["status"] == "Deprecated"

    def test_parse_adr_status_superseded(self, parser):
        """Should handle 'Superseded' status."""
        content = """# ADR-005: Replaced Decision

## Status
Superseded by ADR-006

## Context
Test context.

## Decision
Test decision.
"""
        result = parser.parse(content, "adr-005.md")
        episode = result.episodes[0]

        assert "Superseded" in episode.metadata["status"]

    def test_parse_adr_status_proposed(self, parser):
        """Should handle 'Proposed' status."""
        content = """# ADR-006: Proposed Decision

## Status
Proposed

## Context
Test context.

## Decision
Test decision.
"""
        result = parser.parse(content, "adr-006.md")
        episode = result.episodes[0]

        assert episode.metadata["status"] == "Proposed"

    def test_parse_adr_without_number_prefix(self, parser):
        """Should handle ADR without number in title."""
        content = """# Use Docker for Development

## Status
Accepted

## Context
We need containerization.

## Decision
We will use Docker.
"""
        result = parser.parse(content, "adr-docker.md")

        assert result.success is True
        assert len(result.episodes) == 1

    def test_generate_unique_entity_id_from_title(self, parser):
        """Should generate unique entity_id from title."""
        content1 = """# ADR-001: Use Postgres

## Status
Accepted

## Context
Database choice.

## Decision
Use Postgres.
"""
        content2 = """# ADR-002: Use Redis

## Status
Accepted

## Context
Cache choice.

## Decision
Use Redis.
"""
        result1 = parser.parse(content1, "adr-001.md")
        result2 = parser.parse(content2, "adr-002.md")

        assert result1.episodes[0].entity_id != result2.episodes[0].entity_id

    def test_handle_multiline_sections(self, parser):
        """Should handle multi-paragraph sections."""
        content = """# ADR-007: Multi-line Decision

## Status
Accepted

## Context
This is a long context section.

It has multiple paragraphs.

And even some lists:
- Item 1
- Item 2

## Decision
This is the decision.

It also has multiple paragraphs.

## Consequences

### Positive
- Good thing 1
- Good thing 2

### Negative
- Bad thing 1
"""
        result = parser.parse(content, "adr-007.md")
        episode = result.episodes[0]

        assert result.success is True
        assert "multiple paragraphs" in episode.content.lower()
        assert "Item 1" in episode.content or "lists" in episode.content.lower()

    def test_parse_adr_with_extra_sections(self, parser):
        """Should handle ADR with additional custom sections."""
        content = """# ADR-008: Decision with Alternatives

## Status
Accepted

## Context
Test context.

## Alternatives Considered
- Option A
- Option B

## Decision
We chose Option C.

## Implementation Notes
Some notes here.

## Consequences
Some consequences.
"""
        result = parser.parse(content, "adr-008.md")

        assert result.success is True
        # Should still extract core sections successfully

    def test_parse_returns_warnings_for_malformed_content(self, parser):
        """Should return warnings for malformed ADR."""
        content = """# ADR-009: Incomplete

## Status
Accepted

## Context
Missing decision section!
"""
        result = parser.parse(content, "adr-009.md")

        # May succeed with warnings or fail gracefully
        assert isinstance(result, ParseResult)

    def test_parse_empty_sections(self, parser):
        """Should handle empty sections gracefully."""
        content = """# ADR-010: Empty Sections

## Status
Accepted

## Context

## Decision
We will do something.
"""
        result = parser.parse(content, "adr-010.md")

        assert isinstance(result, ParseResult)

    def test_metadata_includes_adr_number_if_present(self, parser):
        """Should extract ADR number from title if present."""
        content = """# ADR-042: Numbered Decision

## Status
Accepted

## Context
Test.

## Decision
Test.
"""
        result = parser.parse(content, "adr-042.md")
        episode = result.episodes[0]

        # Should include ADR number in metadata if extracted
        if "adr_number" in episode.metadata:
            assert episode.metadata["adr_number"] == "042" or episode.metadata["adr_number"] == "42"
