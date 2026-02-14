"""Tests for FullDocParser - Full markdown document capture.

TDD Phase: These tests define the expected behavior for:
- FullDocParser class (inherits from BaseParser)
- Capturing entire markdown document content
- Chunking large documents by sections
- Handling documents with and without frontmatter

Coverage Target: >=85%
Test Count: 25+ tests
"""

import pytest

from guardkit.integrations.graphiti.parsers.base import (
    BaseParser,
    EpisodeData,
    ParseResult,
)
from guardkit.integrations.graphiti.parsers.full_doc_parser import (
    FullDocParser,
    DEFAULT_CHUNK_THRESHOLD,
)


# ============================================================================
# 1. Parser Configuration Tests (5 tests)
# ============================================================================


class TestFullDocParserConfiguration:
    """Tests for parser configuration and registration."""

    def test_parser_inherits_from_base_parser(self):
        """FullDocParser should inherit from BaseParser."""
        parser = FullDocParser()
        assert isinstance(parser, BaseParser)

    def test_parser_type_property(self):
        """parser_type should return 'full_doc'."""
        parser = FullDocParser()
        assert parser.parser_type == "full_doc"

    def test_supported_extensions_empty(self):
        """supported_extensions should return [] to avoid polluting extension map."""
        parser = FullDocParser()
        assert parser.supported_extensions == []

    def test_can_parse_returns_true_for_md_files(self):
        """can_parse should return True for .md files (fallback parser)."""
        parser = FullDocParser()
        assert parser.can_parse("# Content", "README.md") is True
        assert parser.can_parse("# Content", "CLAUDE.md") is True
        assert parser.can_parse("# Content", "docs/research.md") is True

    def test_can_parse_returns_true_for_markdown_files(self):
        """can_parse should return True for .markdown files."""
        parser = FullDocParser()
        assert parser.can_parse("# Content", "any-file.markdown") is True
        assert parser.can_parse("# Content", "docs/guide.MARKDOWN") is True

    def test_can_parse_returns_false_for_non_markdown(self):
        """can_parse should return False for non-markdown files."""
        parser = FullDocParser()
        assert parser.can_parse("content", "script.py") is False
        assert parser.can_parse("content", "data.json") is False
        assert parser.can_parse("content", "style.css") is False
        assert parser.can_parse("content", "readme.txt") is False

    def test_can_parse_returns_false_for_empty_path(self):
        """can_parse should return False for empty file path."""
        parser = FullDocParser()
        assert parser.can_parse("# Content", "") is False

    def test_default_chunk_threshold(self):
        """Default chunk threshold should be 10KB."""
        assert DEFAULT_CHUNK_THRESHOLD == 10 * 1024


# ============================================================================
# 2. Basic Parsing Tests (6 tests)
# ============================================================================


class TestBasicParsing:
    """Tests for basic document parsing."""

    def test_parse_simple_document(self):
        """Should parse a simple markdown document."""
        parser = FullDocParser()
        content = """# My Document

This is a simple document with some content.

## Section 1
Content in section 1.

## Section 2
Content in section 2.
"""
        result = parser.parse(content, "docs/test.md")
        assert result.success is True
        assert len(result.episodes) >= 1

    def test_parse_captures_full_content(self):
        """Should capture the full document content."""
        parser = FullDocParser()
        content = """# Title

Some content here.
More content below.
"""
        result = parser.parse(content, "test.md")
        assert result.success is True
        assert len(result.episodes) == 1

        # Full content should be in the episode
        episode_content = result.episodes[0].content
        assert "Some content here" in episode_content
        assert "More content below" in episode_content

    def test_parse_returns_parse_result(self):
        """parse() should return a ParseResult instance."""
        parser = FullDocParser()
        content = "# Title\nContent"
        result = parser.parse(content, "test.md")
        assert isinstance(result, ParseResult)

    def test_parse_generates_episode_data(self):
        """Should generate EpisodeData instances."""
        parser = FullDocParser()
        content = "# Title\nContent"
        result = parser.parse(content, "test.md")
        assert result.success is True
        assert len(result.episodes) > 0
        assert all(isinstance(ep, EpisodeData) for ep in result.episodes)

    def test_episode_has_correct_entity_type(self):
        """Episodes should have 'full_doc' entity type."""
        parser = FullDocParser()
        content = "# Title\nContent"
        result = parser.parse(content, "test.md")
        assert result.success is True
        assert all(ep.entity_type == "full_doc" for ep in result.episodes)

    def test_episode_has_correct_group_id(self):
        """Episodes should have 'project_knowledge' group_id."""
        parser = FullDocParser()
        content = "# Title\nContent"
        result = parser.parse(content, "test.md")
        assert result.success is True
        assert all(ep.group_id == "project_knowledge" for ep in result.episodes)


# ============================================================================
# 3. Title Extraction Tests (5 tests)
# ============================================================================


class TestTitleExtraction:
    """Tests for document title extraction."""

    def test_extract_title_from_h1(self):
        """Should extract title from # heading."""
        parser = FullDocParser()
        content = """# My Document Title

Content here.
"""
        result = parser.parse(content, "test.md")
        assert result.success is True
        assert result.episodes[0].metadata.get("title") == "My Document Title"

    def test_extract_title_from_h2_if_no_h1(self):
        """Should extract title from ## heading if no # heading."""
        parser = FullDocParser()
        content = """## My Section Title

Content here.
"""
        result = parser.parse(content, "test.md")
        assert result.success is True
        assert result.episodes[0].metadata.get("title") == "My Section Title"

    def test_title_fallback_to_filename(self):
        """Should use filename as title if no heading found."""
        parser = FullDocParser()
        content = """Just plain text
with no headings.
"""
        result = parser.parse(content, "my-document.md")
        assert result.success is True
        assert result.episodes[0].metadata.get("title") == "my-document"
        # Should have a warning about missing title
        assert any("title" in w.lower() for w in result.warnings)

    def test_title_strips_whitespace(self):
        """Should strip whitespace from extracted title."""
        parser = FullDocParser()
        content = """#    Title with spaces

Content.
"""
        result = parser.parse(content, "test.md")
        assert result.success is True
        assert result.episodes[0].metadata.get("title") == "Title with spaces"

    def test_title_handles_special_characters(self):
        """Should handle special characters in title."""
        parser = FullDocParser()
        content = """# My Project: A Guide (v2.0)

Content.
"""
        result = parser.parse(content, "test.md")
        assert result.success is True
        assert "My Project: A Guide (v2.0)" in result.episodes[0].metadata.get("title")


# ============================================================================
# 4. Frontmatter Tests (5 tests)
# ============================================================================


class TestFrontmatterHandling:
    """Tests for YAML frontmatter parsing."""

    def test_parse_handles_yaml_frontmatter(self):
        """Should parse YAML frontmatter if present."""
        parser = FullDocParser()
        content = """---
title: My Project
version: 1.0.0
author: John Doe
---

# Project

Content here.
"""
        result = parser.parse(content, "test.md")
        assert result.success is True
        assert len(result.episodes) > 0

    def test_parse_extracts_frontmatter_metadata(self):
        """Should include frontmatter data in metadata."""
        parser = FullDocParser()
        content = """---
title: My Project
tags:
  - python
  - graphiti
---

# Project

Content.
"""
        result = parser.parse(content, "test.md")
        assert result.success is True
        frontmatter = result.episodes[0].metadata.get("frontmatter")
        assert frontmatter is not None
        assert frontmatter.get("title") == "My Project"
        assert "python" in frontmatter.get("tags", [])

    def test_parse_works_without_frontmatter(self):
        """Should work correctly without frontmatter."""
        parser = FullDocParser()
        content = """# Simple Document

No frontmatter here.
"""
        result = parser.parse(content, "test.md")
        assert result.success is True
        # Should not have frontmatter in metadata
        frontmatter = result.episodes[0].metadata.get("frontmatter")
        assert frontmatter is None or frontmatter == {}

    def test_frontmatter_not_included_in_content(self):
        """Frontmatter should not be included in episode content."""
        parser = FullDocParser()
        content = """---
title: My Project
---

# Actual Content

Body text.
"""
        result = parser.parse(content, "test.md")
        assert result.success is True
        episode_content = result.episodes[0].content
        # Content should not contain the frontmatter markers
        assert "---" not in episode_content or "title: My Project" not in episode_content

    def test_handles_malformed_frontmatter(self):
        """Should handle malformed frontmatter gracefully."""
        parser = FullDocParser()
        content = """---
title: Project
invalid yaml: [unclosed
---

# Project

Content.
"""
        result = parser.parse(content, "test.md")
        # Should still succeed, possibly with warnings
        assert result.success is True or len(result.warnings) > 0


# ============================================================================
# 5. Metadata Tests (4 tests)
# ============================================================================


class TestMetadataExtraction:
    """Tests for metadata extraction."""

    def test_metadata_includes_file_path(self):
        """Metadata should include the file path."""
        parser = FullDocParser()
        content = "# Title\nContent"
        file_path = "docs/research/my-doc.md"
        result = parser.parse(content, file_path)
        assert result.success is True
        assert result.episodes[0].metadata.get("file_path") == file_path

    def test_metadata_includes_file_size(self):
        """Metadata should include file size in bytes."""
        parser = FullDocParser()
        content = "# Title\nContent"
        result = parser.parse(content, "test.md")
        assert result.success is True
        file_size = result.episodes[0].metadata.get("file_size")
        assert file_size is not None
        assert file_size == len(content.encode("utf-8"))

    def test_entity_id_is_file_path(self):
        """Entity ID should be the file path."""
        parser = FullDocParser()
        content = "# Title\nContent"
        file_path = "/path/to/document.md"
        result = parser.parse(content, file_path)
        assert result.success is True
        assert result.episodes[0].entity_id == file_path

    def test_metadata_includes_title(self):
        """Metadata should include the document title."""
        parser = FullDocParser()
        content = "# My Title\nContent"
        result = parser.parse(content, "test.md")
        assert result.success is True
        assert result.episodes[0].metadata.get("title") == "My Title"


# ============================================================================
# 6. Large Document Chunking Tests (6 tests)
# ============================================================================


class TestLargeDocumentChunking:
    """Tests for chunking large documents."""

    def test_small_document_not_chunked(self):
        """Documents under chunk threshold should not be chunked."""
        parser = FullDocParser(chunk_threshold=10000)
        content = "# Title\n" + "Content " * 100  # Small document
        result = parser.parse(content, "test.md")
        assert result.success is True
        assert len(result.episodes) == 1

    def test_large_document_chunked_by_sections(self):
        """Large documents should be chunked by ## sections."""
        # Create a document larger than the threshold
        parser = FullDocParser(chunk_threshold=100)  # Very low threshold for testing
        content = """# Main Title

Introduction content here.

## Section One
Content for section one that is long enough.

## Section Two
Content for section two that is also long.

## Section Three
Content for section three to add more size.
"""
        result = parser.parse(content, "test.md")
        assert result.success is True
        # Should have multiple episodes (intro + 3 sections = 4)
        assert len(result.episodes) > 1

    def test_chunked_episodes_have_chunk_metadata(self):
        """Chunked episodes should have chunk index metadata."""
        parser = FullDocParser(chunk_threshold=100)
        content = """# Title

## Section One
Content one.

## Section Two
Content two.
"""
        result = parser.parse(content, "test.md")
        if len(result.episodes) > 1:
            # Check that chunk metadata is present
            for i, ep in enumerate(result.episodes):
                assert "chunk_index" in ep.metadata
                assert ep.metadata.get("chunk_total") == len(result.episodes)

    def test_chunk_entity_id_includes_suffix(self):
        """Chunked episode entity_ids should include chunk suffix."""
        parser = FullDocParser(chunk_threshold=100)
        content = """# Title

## Section One
Content one long enough.

## Section Two
Content two long enough.
"""
        result = parser.parse(content, "test.md")
        if len(result.episodes) > 1:
            # At least one episode should have a chunk suffix
            entity_ids = [ep.entity_id for ep in result.episodes]
            assert any("_chunk_" in eid for eid in entity_ids)

    def test_chunk_titles_include_section_name(self):
        """Chunk titles should include the section name."""
        parser = FullDocParser(chunk_threshold=100)
        content = """# Main Document

## First Section
Content here.

## Second Section
More content.
"""
        result = parser.parse(content, "test.md")
        if len(result.episodes) > 1:
            chunk_titles = [ep.metadata.get("chunk_title", "") for ep in result.episodes]
            # Should have titles that include section names
            assert any("First Section" in t for t in chunk_titles)
            assert any("Second Section" in t for t in chunk_titles)

    def test_large_document_without_sections_warning(self):
        """Large document without sections should produce warning."""
        parser = FullDocParser(chunk_threshold=50)
        content = """# Title

This is a large document without any section headers.
It just has a lot of content but no ## headers.
""" + "More content " * 50

        result = parser.parse(content, "test.md")
        assert result.success is True
        # Should have a warning about not being able to chunk
        assert any("chunk" in w.lower() for w in result.warnings)


# ============================================================================
# 7. Error Handling Tests (5 tests)
# ============================================================================


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    def test_parse_handles_empty_content(self):
        """Should handle empty content gracefully."""
        parser = FullDocParser()
        result = parser.parse("", "test.md")
        assert result.success is False
        assert len(result.warnings) > 0
        assert any("empty" in w.lower() for w in result.warnings)

    def test_parse_handles_whitespace_only(self):
        """Should handle whitespace-only content."""
        parser = FullDocParser()
        result = parser.parse("   \n\n   ", "test.md")
        assert result.success is False
        assert len(result.warnings) > 0

    def test_parse_handles_no_headers(self):
        """Should handle content with no headers."""
        parser = FullDocParser()
        content = """Just plain text
with no headers at all.
Some more content.
"""
        result = parser.parse(content, "plain.md")
        assert result.success is True
        # Should still create an episode
        assert len(result.episodes) == 1
        # Should use filename as title (with warning)
        assert any("title" in w.lower() for w in result.warnings)

    def test_parse_handles_unicode_content(self):
        """Should handle unicode content correctly."""
        parser = FullDocParser()
        content = """# Document with Unicode

こんにちは (Hello in Japanese)
Привет (Hello in Russian)
مرحبا (Hello in Arabic)
"""
        result = parser.parse(content, "unicode.md")
        assert result.success is True
        assert len(result.episodes) > 0
        # Check unicode is preserved
        assert "こんにちは" in result.episodes[0].content

    def test_parse_handles_very_long_content(self):
        """Should handle very long content without errors."""
        parser = FullDocParser(chunk_threshold=1_000_000)  # High threshold
        # Create a very long document
        sections = []
        for i in range(100):
            sections.append(f"## Section {i}\n")
            sections.append("Content " * 100 + "\n\n")
        content = "# Long Document\n\n" + "\n".join(sections)

        result = parser.parse(content, "long.md")
        assert result.success is True
        # Should not crash


# ============================================================================
# 8. Custom Chunk Threshold Tests (3 tests)
# ============================================================================


class TestCustomChunkThreshold:
    """Tests for custom chunk threshold configuration."""

    def test_custom_chunk_threshold(self):
        """Should respect custom chunk threshold."""
        parser = FullDocParser(chunk_threshold=50)
        # Content just over threshold
        content = "# Title\n\n## Section\n" + "a" * 60
        result = parser.parse(content, "test.md")
        # With such a low threshold, it should attempt chunking
        assert result.success is True

    def test_very_high_threshold_prevents_chunking(self):
        """Very high threshold should prevent chunking."""
        parser = FullDocParser(chunk_threshold=1_000_000)
        content = """# Title

## Section One
""" + "Content " * 1000 + """

## Section Two
""" + "More " * 1000

        result = parser.parse(content, "test.md")
        assert result.success is True
        # Should not chunk with such a high threshold
        assert len(result.episodes) == 1

    def test_zero_threshold_always_chunks(self):
        """Zero threshold should always attempt chunking."""
        parser = FullDocParser(chunk_threshold=0)
        content = """# Title

## Section One
A

## Section Two
B
"""
        result = parser.parse(content, "test.md")
        assert result.success is True
        # Should chunk even tiny documents
        assert len(result.episodes) > 1


# ============================================================================
# 9. Integration Tests (2 tests)
# ============================================================================


class TestIntegration:
    """Integration tests with realistic content."""

    def test_parse_realistic_research_document(self):
        """Should parse a realistic research document completely."""
        parser = FullDocParser()
        content = """---
title: Graphiti Knowledge Integration
date: 2025-02-04
author: Developer
tags:
  - graphiti
  - knowledge-graph
  - ai
---

# Graphiti Knowledge Integration Research

## Executive Summary

This document explores the integration of Graphiti knowledge
graphs with the GuardKit task workflow system.

## Background

Graphiti provides a persistent knowledge store that enables
AI assistants to maintain context across sessions.

## Key Findings

1. Episode-based storage works well for structured data
2. Chunking improves search relevance
3. Group IDs enable logical organization

## Recommendations

- Implement full document parser for flexible capture
- Add project_knowledge group to default search
- Support chunking for large documents

## References

- Graphiti Documentation
- Neo4j Graph Database
"""
        result = parser.parse(content, "research/graphiti-integration.md")

        # Should succeed
        assert result.success is True

        # Should have episodes
        assert len(result.episodes) > 0

        # Should capture key information
        all_content = " ".join(ep.content for ep in result.episodes)
        assert "Graphiti" in all_content
        assert "Episode-based" in all_content or "knowledge" in all_content

        # Should have frontmatter
        frontmatter = result.episodes[0].metadata.get("frontmatter")
        if frontmatter:
            assert frontmatter.get("title") == "Graphiti Knowledge Integration"

    def test_full_doc_different_from_project_doc(self):
        """FullDocParser should capture content ProjectDocParser misses."""
        from guardkit.integrations.graphiti.parsers.project_doc_parser import (
            ProjectDocParser,
        )

        # Content with sections that project_doc would miss
        content = """# My Research

## Core Tools

This is about tools that aren't in a standard section.

## Technology Decisions

Decisions that don't match tech_stack patterns.

## Conclusion

Final thoughts.
"""
        # ProjectDocParser wouldn't match this file and would miss these sections
        project_parser = ProjectDocParser()
        project_can_parse = project_parser.can_parse(content, "research.md")
        assert project_can_parse is False  # ProjectDocParser rejects non-CLAUDE/README

        # FullDocParser captures everything (as fallback)
        full_parser = FullDocParser()
        assert full_parser.can_parse(content, "research.md") is True
        result = full_parser.parse(content, "research.md")
        assert result.success is True

        all_content = " ".join(ep.content for ep in result.episodes)
        # Should capture all sections
        assert "Core Tools" in all_content
        assert "Technology Decisions" in all_content
        assert "Conclusion" in all_content


# ============================================================================
# 10. Fallback Behavior and Registry Priority Tests (6 tests)
# ============================================================================


class TestFallbackBehavior:
    """Tests for FullDocParser acting as lowest-priority fallback."""

    def test_registry_detects_adr_before_full_doc(self):
        """ADR parser should take precedence over FullDocParser."""
        from guardkit.integrations.graphiti.parsers.adr import ADRParser
        from guardkit.integrations.graphiti.parsers.registry import ParserRegistry

        registry = ParserRegistry()
        registry.register(ADRParser())
        registry.register(FullDocParser())  # Last = lowest priority

        content = """# ADR-001: Use Repository Pattern

## Status
Accepted

## Context
We need a data access pattern.

## Decision
Use the repository pattern.
"""
        detected = registry.detect_parser("docs/adr-001-repo-pattern.md", content)
        assert detected is not None
        assert detected.parser_type == "adr"

    def test_registry_falls_back_to_full_doc_for_generic_md(self):
        """FullDocParser should be used for generic .md files."""
        from guardkit.integrations.graphiti.parsers.adr import ADRParser
        from guardkit.integrations.graphiti.parsers.feature_spec import FeatureSpecParser
        from guardkit.integrations.graphiti.parsers.project_doc_parser import ProjectDocParser
        from guardkit.integrations.graphiti.parsers.project_overview import ProjectOverviewParser
        from guardkit.integrations.graphiti.parsers.registry import ParserRegistry

        # Register in production order (FullDocParser last)
        registry = ParserRegistry()
        registry.register(ADRParser())
        registry.register(FeatureSpecParser())
        registry.register(ProjectDocParser())
        registry.register(ProjectOverviewParser())
        registry.register(FullDocParser())

        content = """# Research Notes

## Findings
Some research findings here.

## Conclusion
Summary of the research.
"""
        detected = registry.detect_parser("docs/research-notes.md", content)
        assert detected is not None
        assert detected.parser_type == "full_doc"

    def test_registry_returns_none_for_non_markdown(self):
        """Non-markdown files should not match FullDocParser."""
        from guardkit.integrations.graphiti.parsers.registry import ParserRegistry

        registry = ParserRegistry()
        registry.register(FullDocParser())

        detected = registry.detect_parser("script.py", "print('hello')")
        assert detected is None

    def test_full_doc_does_not_pollute_extension_map(self):
        """FullDocParser should not add entries to the extension map."""
        from guardkit.integrations.graphiti.parsers.registry import ParserRegistry

        registry = ParserRegistry()
        registry.register(FullDocParser())

        # Extension map should be empty since supported_extensions is []
        assert ".md" not in registry._extension_map
        assert ".markdown" not in registry._extension_map

    def test_explicit_type_still_works(self):
        """--type full_doc should still work via get_parser()."""
        from guardkit.integrations.graphiti.parsers.registry import ParserRegistry

        registry = ParserRegistry()
        registry.register(FullDocParser())

        parser = registry.get_parser("full_doc")
        assert parser is not None
        assert parser.parser_type == "full_doc"

    def test_feature_spec_takes_precedence(self):
        """Feature spec parser should take precedence over FullDocParser."""
        from guardkit.integrations.graphiti.parsers.feature_spec import FeatureSpecParser
        from guardkit.integrations.graphiti.parsers.registry import ParserRegistry

        registry = ParserRegistry()
        registry.register(FeatureSpecParser())
        registry.register(FullDocParser())

        content = """# Feature Spec: Dark Mode

## Description
Add dark mode support.
"""
        detected = registry.detect_parser("feature-spec-dark-mode.md", content)
        assert detected is not None
        assert detected.parser_type == "feature-spec"
