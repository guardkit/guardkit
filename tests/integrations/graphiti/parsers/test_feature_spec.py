"""Tests for FeatureSpecParser.

TDD RED Phase: These tests define the expected behavior for:
- FeatureSpecParser class that parses feature specification files
- Extraction of feature metadata from frontmatter and content
- Episode generation for feature overview and individual tasks
- Handling of various feature spec formats

Coverage Target: >=85%
Test Count: 25+ tests
"""

import pytest

# These imports will fail until implementation is complete (TDD RED)
from guardkit.integrations.graphiti.parsers.feature_spec import FeatureSpecParser
from guardkit.integrations.graphiti.parsers.base import (
    EpisodeData,
    ParseResult,
    BaseParser,
)


# Sample feature spec content for testing
VALID_FEATURE_SPEC = """# Feature Specification: Graphiti Refinement MVP

> **For**: `/feature-plan` command
> **Status**: Ready for Implementation
> **Reviewed**: TASK-REV-1505 (2026-01-30)
> **Architecture Score**: 78/100

---

## Feature Overview

Enhance Graphiti integration to support project-scoped knowledge graphs with configurable entity prefixing.

### Phase 1: Foundation (27h)

| Task | Description | Estimate |
|------|-------------|----------|
| PRE-001-A | Add project_id | 2h |
| PRE-001-B | Implement prefixing | 3h |
| PRE-001-C | Update schema | 4h |

### Phase 2: Integration (18h)

| Task | Description | Estimate |
|------|-------------|----------|
| INT-002-A | CLI integration | 5h |
| INT-002-B | Parser updates | 6h |
"""

FEATURE_SPEC_WITH_YAML_FRONTMATTER = """---
feature_name: Dark Mode Support
status: Ready for Implementation
reviewed: TASK-REV-1234
architecture_score: 85
---

# Feature Specification: Dark Mode Support

> **For**: UI Enhancement
> **Status**: Ready for Implementation

## Feature Overview

Add dark mode support to the application with user preferences and automatic theme switching.

### Phase 1: Theme System (12h)

| Task | Description | Estimate |
|------|-------------|----------|
| THEME-001 | CSS variables | 3h |
| THEME-002 | Theme toggle | 4h |
"""

FEATURE_SPEC_WITHOUT_PHASES = """# Feature Specification: Quick Fix

> **For**: Bug fix
> **Status**: Ready

## Feature Overview

Simple bug fix for authentication timeout issue.
"""

FEATURE_SPEC_WITH_MISSING_SECTIONS = """# Feature Specification: Incomplete Feature

> **Status**: Draft

Some description here but missing feature overview section.
"""

MALFORMED_FEATURE_SPEC = """This is not a valid feature spec at all.
It's just random text without any structure.
"""

NON_FEATURE_SPEC_MARKDOWN = """# Regular Documentation

This is just a regular markdown file, not a feature spec.

## Section 1

Some content here.
"""


# ============================================================================
# 1. Parser Interface Tests (4 tests)
# ============================================================================


class TestFeatureSpecParserInterface:
    """Tests for FeatureSpecParser interface compliance."""

    def test_feature_spec_parser_inherits_base_parser(self):
        """FeatureSpecParser should inherit from BaseParser."""
        assert issubclass(FeatureSpecParser, BaseParser)

    def test_parser_type_property(self):
        """parser_type should return 'feature-spec'."""
        parser = FeatureSpecParser()
        assert parser.parser_type == "feature-spec"

    def test_supported_extensions_property(self):
        """supported_extensions should return ['.md']."""
        parser = FeatureSpecParser()
        assert parser.supported_extensions == [".md"]

    def test_parser_can_be_instantiated(self):
        """FeatureSpecParser should be instantiatable."""
        parser = FeatureSpecParser()
        assert parser is not None


# ============================================================================
# 2. Can Parse Tests (6 tests)
# ============================================================================


class TestFeatureSpecCanParse:
    """Tests for can_parse method."""

    @pytest.fixture
    def parser(self):
        """Create a FeatureSpecParser instance."""
        return FeatureSpecParser()

    def test_can_parse_feature_spec_uppercase(self, parser):
        """can_parse returns True for files starting with 'FEATURE-SPEC'."""
        assert (
            parser.can_parse(
                VALID_FEATURE_SPEC,
                "FEATURE-SPEC-graphiti-refinement.md",
            )
            is True
        )

    def test_can_parse_feature_spec_lowercase(self, parser):
        """can_parse returns True for files starting with 'feature-spec'."""
        assert (
            parser.can_parse(
                VALID_FEATURE_SPEC,
                "feature-spec-dark-mode.md",
            )
            is True
        )

    def test_can_parse_feature_spec_mixed_case(self, parser):
        """can_parse returns True for files with mixed case 'Feature-Spec'."""
        assert (
            parser.can_parse(
                VALID_FEATURE_SPEC,
                "Feature-Spec-authentication.md",
            )
            is True
        )

    def test_can_parse_rejects_non_feature_spec_file(self, parser):
        """can_parse returns False for non-feature-spec markdown files."""
        assert (
            parser.can_parse(
                NON_FEATURE_SPEC_MARKDOWN,
                "README.md",
            )
            is False
        )

    def test_can_parse_rejects_regular_task_file(self, parser):
        """can_parse returns False for regular task files."""
        assert (
            parser.can_parse(
                VALID_FEATURE_SPEC,
                "TASK-GR-001-A.md",
            )
            is False
        )

    def test_can_parse_rejects_non_markdown_extension(self, parser):
        """can_parse returns False for non-markdown files."""
        assert (
            parser.can_parse(
                VALID_FEATURE_SPEC,
                "FEATURE-SPEC-test.txt",
            )
            is False
        )


# ============================================================================
# 3. Feature Name Extraction Tests (5 tests)
# ============================================================================


class TestFeatureNameExtraction:
    """Tests for extracting feature name from various sources."""

    @pytest.fixture
    def parser(self):
        """Create a FeatureSpecParser instance."""
        return FeatureSpecParser()

    def test_extract_feature_name_from_title(self, parser):
        """parse extracts feature name from title."""
        result = parser.parse(
            VALID_FEATURE_SPEC,
            "FEATURE-SPEC-graphiti-refinement.md",
        )
        assert result.success is True
        assert len(result.episodes) > 0
        overview_episode = result.episodes[0]
        assert "Graphiti Refinement MVP" in overview_episode.content

    def test_extract_feature_name_from_yaml_frontmatter(self, parser):
        """parse extracts feature name from YAML frontmatter if present."""
        result = parser.parse(
            FEATURE_SPEC_WITH_YAML_FRONTMATTER,
            "FEATURE-SPEC-dark-mode.md",
        )
        assert result.success is True
        assert len(result.episodes) > 0
        # Check metadata contains feature_name from frontmatter
        overview_episode = result.episodes[0]
        assert overview_episode.metadata.get("feature_name") == "Dark Mode Support"

    def test_feature_name_title_fallback(self, parser):
        """parse uses title if frontmatter feature_name is missing."""
        result = parser.parse(
            VALID_FEATURE_SPEC,
            "FEATURE-SPEC-test.md",
        )
        assert result.success is True
        overview_episode = result.episodes[0]
        # Should extract from "# Feature Specification: Graphiti Refinement MVP"
        assert "Graphiti Refinement MVP" in overview_episode.content

    def test_entity_id_uses_slugified_feature_name(self, parser):
        """parse creates entity_id using slugified feature name."""
        result = parser.parse(
            VALID_FEATURE_SPEC,
            "FEATURE-SPEC-graphiti-refinement.md",
        )
        assert result.success is True
        overview_episode = result.episodes[0]
        # Should be slugified: "graphiti-refinement-mvp"
        assert "graphiti-refinement-mvp" in overview_episode.entity_id

    def test_entity_type_is_feature_spec(self, parser):
        """parse sets entity_type to 'feature-spec'."""
        result = parser.parse(
            VALID_FEATURE_SPEC,
            "FEATURE-SPEC-test.md",
        )
        assert result.success is True
        for episode in result.episodes:
            assert episode.entity_type == "feature-spec"


# ============================================================================
# 4. Episode Generation Tests (8 tests)
# ============================================================================


class TestEpisodeGeneration:
    """Tests for episode generation from feature specs."""

    @pytest.fixture
    def parser(self):
        """Create a FeatureSpecParser instance."""
        return FeatureSpecParser()

    def test_creates_overview_episode(self, parser):
        """parse creates an overview episode for the feature."""
        result = parser.parse(
            VALID_FEATURE_SPEC,
            "FEATURE-SPEC-test.md",
        )
        assert result.success is True
        assert len(result.episodes) >= 1
        overview_episode = result.episodes[0]
        assert "Feature Overview" in overview_episode.content

    def test_overview_episode_has_correct_group_id(self, parser):
        """Overview episode uses feature slug as group_id."""
        result = parser.parse(
            VALID_FEATURE_SPEC,
            "FEATURE-SPEC-graphiti-refinement.md",
        )
        assert result.success is True
        overview_episode = result.episodes[0]
        assert "graphiti-refinement-mvp" in overview_episode.group_id

    def test_extracts_tasks_from_phase_tables(self, parser):
        """parse extracts individual tasks from phase tables."""
        result = parser.parse(
            VALID_FEATURE_SPEC,
            "FEATURE-SPEC-test.md",
        )
        assert result.success is True
        # Should have overview + 5 tasks (3 from Phase 1, 2 from Phase 2)
        assert len(result.episodes) == 6

    def test_task_episodes_have_task_content(self, parser):
        """Task episodes contain task ID and description."""
        result = parser.parse(
            VALID_FEATURE_SPEC,
            "FEATURE-SPEC-test.md",
        )
        assert result.success is True
        task_episodes = result.episodes[1:]  # Skip overview
        # Check first task
        first_task = task_episodes[0]
        assert "PRE-001-A" in first_task.content
        assert "Add project_id" in first_task.content

    def test_task_episodes_share_group_id_with_overview(self, parser):
        """All episodes share the same group_id."""
        result = parser.parse(
            VALID_FEATURE_SPEC,
            "FEATURE-SPEC-test.md",
        )
        assert result.success is True
        group_ids = [episode.group_id for episode in result.episodes]
        assert len(set(group_ids)) == 1  # All same group_id

    def test_task_episodes_have_unique_entity_ids(self, parser):
        """Each task episode has a unique entity_id."""
        result = parser.parse(
            VALID_FEATURE_SPEC,
            "FEATURE-SPEC-test.md",
        )
        assert result.success is True
        entity_ids = [episode.entity_id for episode in result.episodes]
        assert len(entity_ids) == len(set(entity_ids))  # All unique

    def test_metadata_includes_source_path(self, parser):
        """All episodes include source_path in metadata."""
        file_path = "FEATURE-SPEC-test.md"
        result = parser.parse(VALID_FEATURE_SPEC, file_path)
        assert result.success is True
        for episode in result.episodes:
            assert "source_path" in episode.metadata
            assert episode.metadata["source_path"] == file_path

    def test_metadata_includes_phase_info_for_tasks(self, parser):
        """Task episodes include phase information in metadata."""
        result = parser.parse(
            VALID_FEATURE_SPEC,
            "FEATURE-SPEC-test.md",
        )
        assert result.success is True
        task_episodes = result.episodes[1:]  # Skip overview
        first_task = task_episodes[0]
        assert "phase" in first_task.metadata
        assert "Phase 1" in first_task.metadata["phase"]


# ============================================================================
# 5. Error Handling Tests (6 tests)
# ============================================================================


class TestErrorHandling:
    """Tests for error handling and edge cases."""

    @pytest.fixture
    def parser(self):
        """Create a FeatureSpecParser instance."""
        return FeatureSpecParser()

    def test_handles_missing_feature_overview_with_warning(self, parser):
        """parse handles missing feature overview section with warning."""
        result = parser.parse(
            FEATURE_SPEC_WITH_MISSING_SECTIONS,
            "FEATURE-SPEC-incomplete.md",
        )
        # Should still succeed but with warnings
        assert len(result.warnings) > 0
        assert any("overview" in w.lower() for w in result.warnings)

    def test_handles_missing_phases_gracefully(self, parser):
        """parse handles feature specs without phase tables."""
        result = parser.parse(
            FEATURE_SPEC_WITHOUT_PHASES,
            "FEATURE-SPEC-no-phases.md",
        )
        assert result.success is True
        # Should create at least overview episode
        assert len(result.episodes) >= 1
        # May have warning about missing phases
        assert any("phase" in w.lower() for w in result.warnings) or len(
            result.warnings
        ) == 0

    def test_returns_failure_for_malformed_content(self, parser):
        """parse returns success=False for completely malformed content."""
        result = parser.parse(
            MALFORMED_FEATURE_SPEC,
            "FEATURE-SPEC-malformed.md",
        )
        assert result.success is False
        assert len(result.warnings) > 0

    def test_returns_failure_for_non_feature_spec_content(self, parser):
        """parse returns success=False for non-feature-spec content."""
        result = parser.parse(
            NON_FEATURE_SPEC_MARKDOWN,
            "README.md",
        )
        assert result.success is False

    def test_handles_empty_phase_tables(self, parser):
        """parse handles phase tables with no tasks."""
        content = """# Feature Specification: Empty Phases

## Feature Overview

This feature has empty phase tables.

### Phase 1: Empty (0h)

| Task | Description | Estimate |
|------|-------------|----------|
"""
        result = parser.parse(content, "FEATURE-SPEC-empty-phases.md")
        assert result.success is True
        # Should have overview but no task episodes
        assert len(result.episodes) == 1

    def test_handles_malformed_phase_tables(self, parser):
        """parse handles malformed phase tables with warning."""
        content = """# Feature Specification: Bad Tables

## Feature Overview

Feature with malformed tables.

### Phase 1: Bad (10h)

| Task | Description |
|------|
| TASK-001 | Missing cells
"""
        result = parser.parse(content, "FEATURE-SPEC-bad-tables.md")
        # Should complete with warnings
        assert len(result.warnings) > 0
        assert any("table" in w.lower() or "parse" in w.lower() for w in result.warnings)
